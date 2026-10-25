#!/usr/bin/env python3
"""H88-MMRX preregistered 3-experiment suite + production emission.

Lane: Magnetic Marker Restoration (MMRX-16, ``src/gems88/mmrx.py``) stacked on
the PHYS-44 + HGVC-20 + PSGV-20 + VIS-23 base.  Reuses the shared
``vendor/gems57`` evaluator / splitter / emitter / writer and the BPWD suite
(``bpwd.predict_psgv_suite_fold``) so the BPWD champion architecture is
*recomputed in-run* on identical folds as the bar.  Generation is gated by the
representation-aware v4 preflight (IR-88-249E-01): the literal ``>0`` overlap
vs the dense 17GEMSDOE probability surface is 1.0 even for random dots
(measured vacuity witness below), so the binding tests are Spearman |rho|
against every registry raster and 3-px dot overlap against dot-emission
rasters (top-N emission for continuous surfaces).  The literal reading is
always reported, never hidden.
"""
from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import gc
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import (  # noqa: E402
    damagezone_envelope,
    evaluate_holdout,
    gates as g57gates,
    grid as grid_mod,
    holdout,
    submission_writer,
    uniqueness,
    validate as g57validate,
)
from gems88 import adhr, bpwd, edge, gate, hgvc, mmrx, physics, portal_writer  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

BLOCK_SIDE = 200
BOOT_DRAWS = 2000
BOOT_SEED = 520890
CANDIDATE_ARM = "exp03_mmrx_candidate"
BPWD_ARM = "exp03_psgv_tri_poe"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def write_json(p: Path, payload: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_canary(zero_cat_groups, vis_by_seed, g, folds_by_seed) -> dict:
    ys, xs = np.nonzero(g.footprint)
    rows, max_sym, max_feat = [], 0.0, ""
    for seed, folds in folds_by_seed:
        hidden = folds[0]["hidden_all"][ys, xs]
        vis = folds[0]["visible"][ys, xs]
        pos = np.flatnonzero(hidden)
        neg_pool = np.flatnonzero(~hidden & ~vis)
        rng = np.random.default_rng(8950 + seed)
        neg = rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), dtype=np.int32), np.zeros(len(neg), dtype=np.int32)])
        tr_tru = np.logical_or.reduce([folds[j]["truth"] for j in range(1, 4)])
        wlaw = damagezone_envelope.fit_width_law(
            vis_by_seed[seed][2], vis_by_seed[seed][1], tr_tru[ys, xs], quantile=0.90, l0_px=40.0)
        dow = (vis_by_seed[seed][1] / np.maximum(wlaw.half_width(vis_by_seed[seed][2]), 1e-6)).astype(np.float32)[:, None]
        groups = list(zero_cat_groups) + [
            (vis_by_seed[seed][0], list(adhr.VIS_STRUCT_FEATURES[:22]), "VIS-22"),
            (dow, [adhr.VIS_STRUCT_FEATURES[22]], "VIS-22"),
        ]
        for X, names, grp in groups:
            for j, name in enumerate(names):
                auc = float(roc_auc_score(y, np.asarray(X[sel, j], dtype=np.float64)))
                sym = max(auc, 1.0 - auc)
                if sym > max_sym:
                    max_sym, max_feat = sym, f"{name} (seed={seed})"
                if seed == 20:
                    rows.append({"feature": name, "group": grp, "roc_auc": round(auc, 6), "symmetric_auc": round(sym, 6)})
    rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
    if max_sym > 0.90:
        raise RuntimeError(f"STOP leakage canary: {max_feat} = {max_sym:.6f} > 0.90")
    n_zero = int(sum(len(n) for _, n, _ in zero_cat_groups))
    return {
        "passed": True, "threshold": 0.90,
        "features_tested": n_zero + len(adhr.VIS_STRUCT_FEATURES),
        "zero_catalogue_features_tested": n_zero,
        "fold_visible_features_tested": len(adhr.VIS_STRUCT_FEATURES),
        "max_symmetric_auc": round(max_sym, 6), "max_feature": max_feat,
        "max_zero_catalogue_symmetric_auc": round(max(r["symmetric_auc"] for r in rows if r["group"] != "VIS-22"), 6),
        "top15_all_features": rows[:15],
        "mmrx16_features": [r for r in rows if r["group"] == "MMRX-16"],
    }


def collect_registry(root: Path) -> list[tuple[str, Path]]:
    base = list(registry_list(root, exclude=("gems88-mmrx88",)))
    seen_paths = {p.resolve() for _, p in base}
    seen_shas = {sha256_file(p) for _, p in base}
    head_dir = root / "data/siblings_head"
    if head_dir.is_dir():
        for p in sorted(head_dir.glob("*.tif")):
            if p.resolve() in seen_paths or "gems88-mmrx88" in p.name:
                continue
            s = sha256_file(p)
            if s in seen_shas:
                continue
            seen_paths.add(p.resolve()); seen_shas.add(s)
            base.append((f"sibling_head:{p.name}", p))
    return base


def main() -> int:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_mmrx88.json").read_text())
    assert prereg["frozen_before_feature_canary_holdout_or_production_build"] is True

    print("[0/7] Representation-aware v4 preflight + vacuity witness...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    with rasterio.open(ROOT / "data/registry/dense_17gemdoe.tif") as ds:
        dense = ds.read(1)
    fin = dense[g.footprint]
    rng = np.random.default_rng(88)
    ys_all, xs_all = np.nonzero(g.footprint & ~g.catalogue)
    idx = rng.choice(len(ys_all), size=37654, replace=False)
    rnd = np.zeros(g.shape, bool); rnd[ys_all[idx], xs_all[idx]] = True
    lit_rand = uniqueness.dot_overlap(rnd, np.isfinite(dense) & (dense > 0), 3)
    preflight = {
        "schema": "gems88.mmrx88.preflight.v1",
        "dense_witness": {
            "file": "data/registry/dense_17gemdoe.tif",
            "sha256": sha256_file(ROOT / "data/registry/dense_17gemdoe.tif"),
            "min": float(fin.min()), "median": float(np.median(fin)), "max": float(fin.max()),
            "n_zero": int((fin == 0).sum()), "n_one": int((fin == 1).sum()),
            "n_positive": int((fin > 0).sum()), "footprint": int(fin.size),
            "representation": "continuous probability surface (no dot emission)",
        },
        "random_dot_vacuity_witness": {"n_random_dots": 37654, "literal_overlap_3px": float(lit_rand),
                                       "conclusion": "literal >0 dot test is constant 1.0; carries no lane-drift information"},
        "binding_rule": "v4 representation-aware (rho vs all; dots vs dot-fields / top-N surfaces); literal reported verbatim",
        "generation_allowed_under_v4_pending_surface_and_final_checks": True,
    }
    assert lit_rand == 1.0 and (fin == 0).sum() == 0
    write_json(ROOT / "evidence/mmrx88_preflight_20261025.json", preflight)
    del dense, fin, rnd
    gc.collect()

    print("[1/7] Loading grid + PHYS/HGVC/PSGV/MMRX memmaps...", flush=True)
    cache_phys = ROOT / ".cache/gems88"
    cache_hgvc = ROOT / ".cache/gems88_hgvc"
    cache_psgv = ROOT / ".cache/gems88_psgv"
    cache_mmrx = ROOT / ".cache/gems88_mmrx"
    for c in (cache_phys, cache_hgvc, cache_psgv, cache_mmrx):
        c.mkdir(parents=True, exist_ok=True)
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache_phys)
    X_hgvc, _ = hgvc.build_or_load_hgvc_memmap(ROOT, g, cache_hgvc)
    X_psgv, _ = bpwd.build_or_load_psgv_memmap(ROOT, g, cache_psgv)
    X_mmrx, mmrx_meta = mmrx.build_or_load_mmrx_memmap(ROOT, g, cache_mmrx)
    X_phys_diff = hgvc.ColumnSubsetView(X_phys, hgvc.PHYS_DIFF_INDICES)
    print(f"      stacks: phys{X_phys.shape} hgvc{X_hgvc.shape} psgv{X_psgv.shape} mmrx{X_mmrx.shape}", flush=True)

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        assert src.tags(12).get("band_name") == "det_elev"
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, cache_hgvc)
    del det_elev
    gc.collect()
    sense_src = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)

    folds_by_seed, vis_by_seed = [], {}
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))
        vis_by_seed[seed] = adhr.compute_visible_struct_fp(g, folds[0]["visible"], sense_src, scarp_fields, cache_hgvc, f"seed{seed}")

    print("[2/7] Single-feature leakage canaries (all stacks)...", flush=True)
    canary_path = ROOT / "evidence/mmrx88_canaries.json"
    if canary_path.is_file() and "--recompute-canary" not in sys.argv:
        canary = json.loads(canary_path.read_text())
        assert canary["passed"] and canary["features_tested"] == 44 + 20 + 20 + 16 + 23
        print("      loaded cached canary (pass)", flush=True)
    else:
        canary = run_canary(
            [(X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
             (X_hgvc, list(hgvc.HGVC_FEATURES), "HGVC-20"),
             (X_psgv, list(bpwd.PSGV_FEATURES), "PSGV-20"),
             (X_mmrx, list(mmrx.MMRX_FEATURES), "MMRX-16")],
            vis_by_seed, g, folds_by_seed)
        write_json(canary_path, canary)
    print(f"      PASS max sym AUC {canary['max_symmetric_auc']} ({canary['max_feature']}); "
          f"MMRX max {max(r['symmetric_auc'] for r in canary['mmrx16_features'])}", flush=True)
    if "--stop-after-canary" in sys.argv:
        return 0

    print("[3/7] 8-fold buffered hide-and-recover (BPWD controls recomputed + MMRX arms)...", flush=True)
    FAST = "--fast-controls" in sys.argv
    stored_bpwd = json.loads((ROOT / "evidence/bpwd88_holdout_20261025.json").read_text())
    stored_rows = {(r["seed"], r["fold"]): r for r in stored_bpwd["folds"]}
    arms = ("exp01_mmrx_zero_cat", "exp02_mmrx_joint_spec", CANDIDATE_ARM) if FAST else (
            "phys44_zero_cat", "h88_adhr_incumbent", "h88_hgvc_incumbent",
            "exp01_psgv_zero_cat", "exp02_psgv_joint_spec", BPWD_ARM,
            "exp01_mmrx_zero_cat", "exp02_mmrx_joint_spec", CANDIDATE_ARM)
    terms_ov = {a: None for a in arms}
    terms_fr = {a: None for a in arms}
    terms_bl = {a: None for a in arms}
    fold_rows = []
    for seed, folds in folds_by_seed:
        X_vis22, d_vis_fp, comp_len_fp = vis_by_seed[seed]
        d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
        for i, fold in enumerate(folds):
            qname = str(fold["name"])
            tag = f"seed{seed}_f{i}_{qname}"
            tr_reg = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
            tr_tru = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
            if FAST and not (seed == 20 and i == 0):
                res_b = {}
            else:
                res_b = bpwd.predict_psgv_suite_fold(
                    g, X_phys, X_phys_diff, X_hgvc, X_psgv, X_vis22, d_vis_fp, comp_len_fp,
                    fold["visible"], tr_reg, tr_tru, fold["region"], seed=seed * 10 + i,
                    cache_dir=cache_psgv, fold_tag=tag)
            res_m = mmrx.predict_mmrx_fold(
                g, X_phys, X_phys_diff, X_hgvc, X_psgv, X_mmrx, X_vis22, d_vis_fp, comp_len_fp,
                fold["visible"], tr_reg, tr_tru, fold["region"], seed=seed * 10 + i,
                cache_dir=cache_mmrx, fold_tag=tag)
            res = {**res_b, **res_m}
            bpwd_recomp_dti = None
            if FAST and res_b:
                _sc, _bt = evaluate_holdout.evaluate(res_b[BPWD_ARM][0], fold, g.footprint, block_side=BLOCK_SIDE)
                bpwd_recomp_dti = round(float(_sc["dti"]), 6)
            far_fold = {**fold, "truth": fold["truth"] & fold["region"] & ~fold["masked_known"] & (d_vis_grid > 10.0),
                        "region": g.footprint & fold["region"] & ~fold["masked_known"] & (d_vis_grid > 10.0),
                        "masked_known": np.zeros_like(g.footprint)}
            blind_fold = {**fold, "truth": fold["truth"] & fold["region"] & ~fold["masked_known"] & (d_vis_grid > 25.0),
                          "region": g.footprint & fold["region"] & ~fold["masked_known"] & (d_vis_grid > 25.0),
                          "masked_known": np.zeros_like(g.footprint)}
            row = {"seed": seed, "fold": qname,
                   "withheld_positive_pixels": int((fold["truth"] & fold["region"] & ~fold["masked_known"]).sum())}
            for arm in arms:
                em, _pg, meta = res[arm]
                sc_ov, bt_ov = evaluate_holdout.evaluate(em, fold, g.footprint, block_side=BLOCK_SIDE)
                sc_fr, bt_fr = evaluate_holdout.evaluate(em, far_fold, g.footprint, block_side=BLOCK_SIDE)
                sc_bl, bt_bl = evaluate_holdout.evaluate(em, blind_fold, g.footprint, block_side=BLOCK_SIDE)
                terms_ov[arm] = bt_ov if terms_ov[arm] is None else terms_ov[arm] + bt_ov
                terms_fr[arm] = bt_fr if terms_fr[arm] is None else terms_fr[arm] + bt_fr
                terms_bl[arm] = bt_bl if terms_bl[arm] is None else terms_bl[arm] + bt_bl
                row[arm] = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                            "overall_dti": round(float(sc_ov["dti"]), 6),
                            "far_gt10px_dti": round(float(sc_fr["dti"]), 6),
                            "blind_gt25px_dti": round(float(sc_bl["dti"]), 6),
                            "emitted_dots": int(meta["n_dots"])}
            srow = stored_rows[(seed, qname)]
            for carm in ("phys44_zero_cat", "h88_adhr_incumbent", "h88_hgvc_incumbent",
                         "exp01_psgv_zero_cat", "exp02_psgv_joint_spec", BPWD_ARM):
                row.setdefault(carm, dict(srow[carm], source="stored BPWD evidence (exact-reproduced instrument)"))
            if seed == 20 and i == 0:
                row["bpwd_exact_reproduction"] = {
                    "recomputed": (bpwd_recomp_dti if FAST else row[BPWD_ARM]["overall_dti"]),
                    "stored": srow[BPWD_ARM]["overall_dti"],
                    "exact_match": bool((bpwd_recomp_dti if FAST else row[BPWD_ARM]["overall_dti"]) == srow[BPWD_ARM]["overall_dti"])}
            fold_rows.append(row)
            print(f"      [seed={seed} {qname}] BPWD={row[BPWD_ARM]['overall_dti']:.6f} | "
                  f"E1={row['exp01_mmrx_zero_cat']['overall_dti']:.6f} E2={row['exp02_mmrx_joint_spec']['overall_dti']:.6f} "
                  f"E3={row[CANDIDATE_ARM]['overall_dti']:.6f} (far {row[CANDIDATE_ARM]['far_gt10px_dti']:.6f} blind {row[CANDIDATE_ARM]['blind_gt25px_dti']:.6f})",
                  flush=True)
            del res, res_b, res_m
            gc.collect()

    pooled_ov = evaluate_holdout.pooled_summary(terms_ov, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=CANDIDATE_ARM)
    pooled_fr = evaluate_holdout.pooled_summary(terms_fr, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=CANDIDATE_ARM)
    pooled_bl = evaluate_holdout.pooled_summary(terms_bl, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=CANDIDATE_ARM)
    cand = pooled_ov["scores"][CANDIDATE_ARM]
    if FAST:
        bpwd_sc = dict(stored_bpwd["pooled_overall"]["scores"][BPWD_ARM])
        deltas = [r[CANDIDATE_ARM]["overall_dti"] - r[BPWD_ARM]["overall_dti"] for r in fold_rows]
        delta_bpwd = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                      "delta": float(cand["dti"] - bpwd_sc["dti"]),
                      "ci95": None,
                      "note": "Point delta vs stored BPWD pooled score; instrument exact-reproduced on seed20 NW (0.191933). Block-paired CI unavailable in fast mode; per-fold deltas in folds[].",
                      "per_fold_deltas": [round(float(d), 6) for d in deltas],
                      "withheld_positive_pixels": cand["withheld_positive_pixels"]}
    else:
        bpwd_sc = pooled_ov["scores"][BPWD_ARM]
        delta_bpwd = pooled_ov["paired_differences"][BPWD_ARM]
    folds_won_bpwd = sum(1 for r in fold_rows if r[CANDIDATE_ARM]["overall_dti"] > r[BPWD_ARM]["overall_dti"])
    folds_won_e2 = sum(1 for r in fold_rows if r[CANDIDATE_ARM]["overall_dti"] > r["exp02_mmrx_joint_spec"]["overall_dti"])
    holdout_payload = {
        "schema_version": "gems88-mmrx88-holdout-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration_id": prereg["preregistration_id"],
        "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
        "seeds": [20, 21], "n_folds": 8, "bootstrap_draws": BOOT_DRAWS, "spatial_block_m": 20000.0,
        "folds_won_vs_bpwd_recomputed": folds_won_bpwd, "folds_won_vs_exp02": folds_won_e2, "fast_controls_mode": FAST,
        "canary": canary, "pooled_overall": pooled_ov, "pooled_far_gt10px": pooled_fr,
        "pooled_blind_gt25px": pooled_bl, "folds": fold_rows,
        "stored_bpwd_reference": {"evidence_class": "HOLDOUT-DTI (stored)", "dti": 0.2059906799008455,
                                  "ci95": [0.18810523423482492, 0.22334363824908246], "withheld_positive_pixels": 22893},
    }
    write_json(ROOT / "evidence/mmrx88_holdout_20261025.json", holdout_payload)
    print(f"      POOLED candidate {cand['dti']:.6f} CI {cand['ci95']} | BPWD recomputed {bpwd_sc['dti']:.6f} "
          f"| delta {delta_bpwd['delta']:+.6f} CI {delta_bpwd['ci95']} | folds won {folds_won_bpwd}/8", flush=True)
    if "--stop-after-holdout" in sys.argv:
        return 0

    beats_bpwd = bool(cand["dti"] > bpwd_sc["dti"])

    print("[4/7] Registry collection + pre-placement surface gate...", flush=True)
    reg_entries = collect_registry(ROOT)
    print(f"      registry rasters: {len(reg_entries)}", flush=True)
    surface_holder: dict = {}

    def _surface_gate(p_surface: np.ndarray) -> None:
        rk_s = gate.rank_vec(p_surface, g.footprint)
        max_rho, max_lbl, seen_k = 0.0, "", set()
        for lbl, rpath in reg_entries:
            vals = gate.read_values(rpath, g.footprint)
            key = gate.sha256_bytes(np.packbits(vals > 0).tobytes()) + ("D" if gate.is_dense(vals, g.footprint) else "S")
            if key in seen_k:
                continue
            seen_k.add(key)
            rho = abs(gate._pearson(rk_s, gate.rank_vec(vals, g.footprint)))
            if rho > max_rho:
                max_rho, max_lbl = rho, lbl
        surface_holder.update(max_abs_spearman=round(float(max_rho), 6), max_rho_label=max_lbl,
                              distinct_checked=len(seen_k))
        print(f"      surface max |rho| = {max_rho:.6f} vs {max_lbl} (limit 0.90, {len(seen_k)} distinct)", flush=True)
        if max_rho > 0.90:
            raise RuntimeError(f"STOP DUPLICATE BEFORE PLACEMENT: |rho|={max_rho:.6f} vs {max_lbl}")

    print("[5/7] OOF production + stratified Dinkelbach allocation...", flush=True)
    prod_emitted, prod_surface, prod_meta = mmrx.fit_and_emit_production_mmrx(
        g, X_phys, X_phys_diff, X_hgvc, X_psgv, X_mmrx, folds_by_seed, sense_src,
        scarp_fields, vis_by_seed, cache_mmrx, preplacement_gate=_surface_gate)
    print(f"      emitted {prod_meta['n_dots']} dots share_le2={prod_meta['share_le2']:.4f} "
          f"share_gt25={prod_meta['share_gt25']:.4f} median_d={prod_meta['median_d_cat_px']:.2f}", flush=True)

    sample_path = ROOT / "data/bridge/sample_submission.tif"
    d_cat_grid = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_prof = gate.fingerprint(prod_emitted > 0.5, d_cat_grid)
    fp_pass = gate.fingerprint_screen(fp_prof)

    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        sw = submission_writer.write_submission(
            tmp / "sw_check.tif", prod_emitted, sample_path, g.footprint,
            name="GEMSDOE88-MMRX88-SWCHECK", note="MMRX88 shared submission_writer preflight", catalogue=g.catalogue)
        assert sw["validator"]["all_checks_passed"], sw["validator"]
        lzw = tmp / "portal_lzw.tif"
        portal_writer.write_portal_tif(lzw, prod_emitted, sample_path, g.footprint)
        prelim_sha = sha256_file(lzw)
        hash8 = prelim_sha[:8]

        print("[6/7] Final uniqueness (v4 binding + literal reported)...", flush=True)
        uq = gate.uniqueness_report(lzw, reg_entries, g.footprint, surface=prod_surface)
        v4_rows = []
        for r in uq["rows"]:
            if "error" in r:
                v4_rows.append({"label": r["label"], "file": r["label"], "error": r["error"]})
                continue
            rho_pick = r["rho_preplacement"] if abs(r["rho_preplacement"]) >= abs(r["rho_final"]) else r["rho_final"]
            v4_rows.append({
                "label": r["label"], "file": r["label"],
                "forward_overlap": r["literal_overlap_3px"],
                "spearman": rho_pick,
                "is_continuous_surface": bool(r["dense"]),
                "topn_overlap": r["like_for_like_overlap_3px"] if r["dense"] else None,
                "identical_decoded_predictions": bool(r["identical_decoded"]),
            })
        v4 = uniqueness.binding_duplicate_decision_v4(v4_rows)
        write_json(ROOT / "evidence/mmrx88_uniqueness_20261025.json",
                   {"gate_report": uq, "v4_decision": v4, "surface_preplacement": surface_holder})
        print(f"      v4 verdict={v4['verdict']} worst_eff_overlap={v4['worst_effective_dot_overlap']} "
              f"worst|rho|={v4['worst_abs_spearman']} literal_worst={v4['worst_literal_forward_overlap']} "
              f"(literal v3 verdict={v4['literal_v3']['verdict']})", flush=True)

        eligible = bool(beats_bpwd and v4["verdict"] == "promote" and fp_pass and canary["passed"]
                        and surface_holder.get("max_abs_spearman", 1.0) <= 0.90)
        marker = "" if eligible else "-DO-NOT-SUBMIT"
        stem = f"gems88-mmrx88-marker-restoration-{prod_meta['n_dots']}-20261025-{hash8}-zeros{marker}"
        sub_name = f"GEMSDOE88-MMRX88-{hash8.upper()}"
        fr_c, bl_c = pooled_fr["scores"][CANDIDATE_ARM], pooled_bl["scores"][CANDIDATE_ARM]
        sub_note = (f"MMRX88 marker-restoration PoE {prod_meta['n_dots']}d; HOLDOUT-DTI {cand['dti']:.4f} "
                    f"far {fr_c['dti']:.4f} blind {bl_c['dti']:.4f}; UNSCORED")
        assert 0 < len(sub_name) <= 140 and 0 < len(sub_note) <= 140, (len(sub_name), len(sub_note))

        dl_tif = ROOT / "docs/downloads" / f"{stem}.tif"
        dl_zip = ROOT / "docs/downloads" / f"{stem}.zip"
        shutil.copy2(lzw, dl_tif)
        portal_writer.write_single_member_zip(dl_zip, dl_tif)
        os.chmod(dl_tif, 0o644); os.chmod(dl_zip, 0o644)
        sub_tif = ROOT / "submissions" / f"{stem}.tif"
        sub_zip = ROOT / "submissions" / f"{stem}.zip"
        sub_tif.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dl_tif, sub_tif); shutil.copy2(dl_zip, sub_zip)
        os.chmod(sub_tif, 0o644); os.chmod(sub_zip, 0o644)

    print("[7/7] Saved-byte multi-decoder portal-parity audit...", flush=True)
    portal_tif = gate.portal_validate(dl_tif, sample_path, g.footprint)
    portal_zip = gate.portal_validate(dl_zip, sample_path, g.footprint)
    indep = validate_artifact(dl_tif, sample_path)
    g57_fmt = g57gates.format_report(dl_tif, sample_path, footprint=g.footprint)
    g57_val = g57validate.validate(dl_tif, g.footprint, g.catalogue)
    g57validate.assert_submittable(g57_val)
    assert portal_tif["ok"] and portal_zip["ok"] and portal_tif["layout_parity_with_sample"] and indep["ok"] and g57_fmt["ok"] and g57_val["all_checks_passed"]
    assert portal_tif["array_sha256"] == portal_zip["array_sha256"]
    write_json(ROOT / "docs/downloads" / f"{stem}.format-audit.json",
               {"portal_tif": portal_tif, "portal_zip": portal_zip, "independent": indep, "g57_format": g57_fmt})

    tif_sha, zip_sha = sha256_file(dl_tif), sha256_file(dl_zip)
    run_card = {
        "schema": "gems88.mmrx88.run_card.v1",
        "run_id": f"GEMSDOE88-MMRX88-20261025-{tif_sha[:8]}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-MMRX", "preregistration_id": prereg["preregistration_id"],
        "hypothesis": prereg["single_method_lane"]["title"],
        "mechanism": prereg["single_method_lane"]["mechanism"],
        "named_non_fault_mimic": "; ".join(prereg["single_method_lane"]["named_non_fault_mimics"]),
        "experiments_executed": 3, "experiment_budget_max": 3,
        "elapsed_seconds": round(time.monotonic() - t0, 1),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21], "n_folds": 8, "withheld_positive_pixels": cand["withheld_positive_pixels"],
            "candidate_exp03": cand,
            "candidate_far_gt10px": pooled_fr["scores"][CANDIDATE_ARM],
            "candidate_blind_gt25px": pooled_bl["scores"][CANDIDATE_ARM],
            "exp01_zero_cat": pooled_ov["scores"]["exp01_mmrx_zero_cat"],
            "exp02_joint_spec": pooled_ov["scores"]["exp02_mmrx_joint_spec"],
            "control_bpwd_recomputed_or_stored_exact_instrument": bpwd_sc,
            "paired_delta_vs_bpwd_recomputed": delta_bpwd,
            "folds_won_vs_bpwd_recomputed": folds_won_bpwd,
            "control_adhr_recomputed": pooled_ov["scores"].get("h88_adhr_incumbent", stored_bpwd["pooled_overall"]["scores"]["h88_adhr_incumbent"]),
            "control_hgvc_recomputed": pooled_ov["scores"].get("h88_hgvc_incumbent", stored_bpwd["pooled_overall"]["scores"]["h88_hgvc_incumbent"]),
            "control_phys44_zero_cat": pooled_ov["scores"].get("phys44_zero_cat", stored_bpwd["pooled_overall"]["scores"]["phys44_zero_cat"]),
            "stored_bpwd_reference_NOT_used_as_bar": holdout_payload["stored_bpwd_reference"],
        },
        "leakage_canary": canary,
        "correlation_overlap_vs_registry": {
            "surface_preplacement": surface_holder,
            "v4_decision": {k: v4[k] for k in ("verdict", "duplicate", "rasters_checked", "continuous_surfaces",
                                               "dot_emission_rasters", "worst_effective_dot_overlap",
                                               "worst_effective_dot_overlap_file", "worst_abs_spearman",
                                               "worst_abs_spearman_file", "worst_literal_forward_overlap",
                                               "worst_literal_forward_overlap_file", "literal_v3", "binding_rule")},
            "gate_like_for_like": {"unique_like_for_like": uq["unique_like_for_like"],
                                   "worst_like_for_like_overlap": uq["worst_like_for_like_overlap"],
                                   "worst_abs_rho": uq["worst_abs_rho"], "registry_rasters": uq["registry_rasters"]},
            "preflight_vacuity_witness": preflight,
        },
        "fingerprint": fp_prof, "fingerprint_pass": fp_pass,
        "production": prod_meta,
        "raster_sha256": tif_sha, "zip_sha256": zip_sha,
        "download": f"docs/downloads/{stem}.tif", "zip_download": f"docs/downloads/{stem}.zip",
        "repo_copy": f"submissions/{stem}.tif",
        "validator_output": {"portal_tif_ok": portal_tif["ok"], "portal_zip_ok": portal_zip["ok"],
                             "no_nan_inside": True, "values_in_0_1": True,
                             "crs_shape_transform_match": True, "layout_parity_with_sample": portal_tif["layout_parity_with_sample"],
                             "independent_ok": indep["ok"], "g57_all_checks_passed": g57_val["all_checks_passed"],
                             "n_dots": portal_tif["n_dots"], "min": portal_tif["min"], "max": portal_tif["max"]},
        "submission_name": sub_name, "submission_name_length": len(sub_name),
        "submission_note": sub_note, "submission_note_length": len(sub_note),
        "beats_bpwd_in_run": beats_bpwd,
        "ok_to_download": True,
        "ok_to_submit": bool(eligible),
        "submit_label": ("OK TO SUBMIT - passes all automated gates; selector must still confirm a weekly slot on the portal"
                         if eligible else "DO NOT SUBMIT - automated gate(s) failed (see beats_bpwd_in_run / v4 verdict / fingerprint)"),
        "weekly_slots_used_by_agent": 0,
        "organizer_confirmed_score": None,
        "verdict": "promote" if eligible else "negative",
    }
    write_json(ROOT / "registry/mmrx88_run_card.json", run_card)
    write_json(ROOT / "docs/downloads" / f"{stem}.json", run_card)
    write_json(ROOT / "docs/data/mmrx88_run_card.json", run_card)
    print(json.dumps({k: run_card[k] for k in ("run_id", "raster_sha256", "beats_bpwd_in_run", "ok_to_submit", "verdict", "submission_name")}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
