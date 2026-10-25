#!/usr/bin/env python3
"""Run the preregistered H88-PSGV 3-experiment holdout suite and emit the validated GeoTIFF.

Lane: H88-PSGV — wavenumber-domain Baranov pseudogravity discordance (``src/gems88/psgv.py``,
8 zero-catalogue channels) appended to the validated H88-HGVC specialist heads.
Reuses unmodified ``vendor/gems57/`` (holdout, evaluate_holdout, submission_writer,
uniqueness, validate, gates) and ``src/gems88/`` (adhr, edge, gate, hgvc, physics,
portal_writer, psgv, registry_paths).  Preregistration: registry/preregistration_psgv88.json.
Kill rule: pooled HOLDOUT-DTI must exceed the stored HGVC record 0.202947 to be
selector-eligible; the agent spends 0 submission slots under every outcome.
"""
from __future__ import annotations

# The shared duplicate-stop gate precedes all feature/model imports.
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
from gems88 import adhr, edge, gate, hgvc, physics, portal_writer, psgv  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

BLOCK_SIDE = 200
BOOT_DRAWS = 2000
BOOT_SEED = 520888
CANDIDATE_ARM = "exp03_psgv_poe_conduit"
HGVC_BAR = 0.2029470713394289
HGVC_MARGIN_VS_ADHR = 0.008071257981559443


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_single_feature_canary(zero_cat_groups, vis_by_seed, g, folds_by_seed) -> dict:
    """Every feature alone vs withheld positives; symmetric AUC > 0.90 = leakage (protocol #4)."""
    ys, xs = np.nonzero(g.footprint)
    rows, max_sym, max_feat = [], 0.0, ""
    for seed, folds in folds_by_seed:
        hidden = folds[0]["hidden_all"][ys, xs]
        vis = folds[0]["visible"][ys, xs]
        pos = np.flatnonzero(hidden)
        neg_pool = np.flatnonzero(~hidden & ~vis)
        rng = np.random.default_rng(8800 + seed)
        neg = rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), dtype=np.int32), np.zeros(len(neg), dtype=np.int32)])
        tr_tru_seed = np.logical_or.reduce([folds[j]["truth"] for j in range(1, 4)])
        wlaw_c = damagezone_envelope.fit_width_law(
            vis_by_seed[seed][2], vis_by_seed[seed][1], tr_tru_seed[ys, xs], quantile=0.90, l0_px=40.0)
        dow_c = (vis_by_seed[seed][1] / np.maximum(wlaw_c.half_width(vis_by_seed[seed][2]), 1e-6)).astype(np.float32)[:, None]
        seed_groups = list(zero_cat_groups) + [
            (vis_by_seed[seed][0], list(adhr.VIS_STRUCT_FEATURES[:22]), "VIS-22"),
            (dow_c, [adhr.VIS_STRUCT_FEATURES[22]], "VIS-22"),
        ]
        for X, names, group in seed_groups:
            for j, name in enumerate(names):
                vals = np.asarray(X[sel, j], dtype=np.float64)
                auc = float(roc_auc_score(y, vals))
                sym = max(auc, 1.0 - auc)
                if sym > max_sym:
                    max_sym, max_feat = sym, f"{name} (seed={seed})"
                if seed == 20:
                    rows.append({"feature": name, "group": group,
                                 "roc_auc": round(auc, 6), "symmetric_auc": round(sym, 6)})
    rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
    passed = bool(max_sym <= 0.90)
    if not passed:
        raise RuntimeError(f"STOP: leakage canary tripped: {max_feat} = {max_sym:.6f} > 0.90")
    total = int(sum(len(n) for _, n, _ in zero_cat_groups) + len(adhr.VIS_STRUCT_FEATURES))
    psgv_rows = [r for r in rows if r["feature"].startswith("psgv_")]
    return {"passed": passed, "threshold": 0.90, "features_tested": total,
            "max_symmetric_auc": round(float(max_sym), 6), "max_feature": max_feat,
            "psgv_max_symmetric_auc": round(max((r["symmetric_auc"] for r in psgv_rows), default=0.0), 6),
            "psgv_features": psgv_rows, "top15_all_features": rows[:15],
            "all_features_seed20": rows}


def main() -> int:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_psgv88.json").read_text(encoding="utf-8"))
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("Preregistration must be frozen before running experiments")

    print("[1/7] Grid + PHYS-44 / HGVC-20 / PSGV-8 memmaps...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    shared_cache = ROOT / ".cache/gems88"; shared_cache.mkdir(parents=True, exist_ok=True)
    hgvc_cache = ROOT / ".cache/gems88_hgvc"; hgvc_cache.mkdir(parents=True, exist_ok=True)
    psgv_cache = ROOT / ".cache/gems88_psgv"; psgv_cache.mkdir(parents=True, exist_ok=True)
    X_phys, band_tags, _ = physics.build_or_load_physics_memmap(ROOT, g, shared_cache)
    X_hgvc, hgvc_meta = hgvc.build_or_load_hgvc_memmap(ROOT, g, hgvc_cache)
    X_psgv, psgv_meta = psgv.build_or_load_psgv_memmap(ROOT, g, psgv_cache)
    X_phys_diff = hgvc.ColumnSubsetView(X_phys, hgvc.PHYS_DIFF_INDICES)
    print(f"      PSGV slope a={psgv_meta['global_regression_slope_grav_on_psg_z']:.4f}; "
          f"HGVC cold rejected={hgvc_meta['cold_wells_rejected']}", flush=True)

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        if src.tags(12).get("band_name") != "det_elev":
            raise ValueError("Band 12 must be det_elev (IR-88-110 guard)")
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, psgv_cache)
    del det_elev; gc.collect()
    sense_csv = ROOT / "data/external/trace_segments_utm11.csv"
    sense_src = adhr.build_sense_raster(sense_csv, g)

    folds_by_seed, vis_by_seed = [], {}
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))
        vis_by_seed[seed] = adhr.compute_visible_struct_fp(
            g, folds[0]["visible"], sense_src, scarp_fields, psgv_cache, f"seed{seed}")

    print("[2/7] Leakage canary (95 features alone)...", flush=True)
    canary_path = ROOT / "evidence/psgv88_canaries.json"
    canary = json.loads(canary_path.read_text()) if canary_path.is_file() else None
    if not (canary and canary.get("features_tested") == 95 and canary.get("passed")):
        canary = run_single_feature_canary(
            [(X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
             (X_hgvc, list(hgvc.HGVC_FEATURES), "HGVC-20"),
             (X_psgv, list(psgv.PSGV_FEATURES), "PSGV-8")],
            vis_by_seed, g, folds_by_seed)
        # PSGV-8 are deterministic FFT functions of B02/B13/B15 only; the builder
        # never opens existing_faults.tif (grep-verifiable in src/gems88/psgv.py).
        canary["psgv_zero_catalogue_by_construction"] = True
        write_json(canary_path, canary)
    print(f"      PASS {canary['features_tested']}/95 <= 0.90 (max={canary['max_symmetric_auc']:.6f} "
          f"{canary['max_feature']}; PSGV max={canary['psgv_max_symmetric_auc']:.6f})", flush=True)

    print("[3/7] 8-fold buffered holdout (2 controls + 3 PSGV experiments)...", flush=True)
    holdout_path = ROOT / "evidence/psgv88_holdout_20261025.json"
    if holdout_path.is_file() and "--recompute-holdout" not in sys.argv:
        hp = json.loads(holdout_path.read_text())
        pooled_overall, pooled_far10, pooled_blind25 = hp["pooled_overall"], hp["pooled_far_gt10px"], hp["pooled_blind_gt25px"]
        fold_rows, folds_won = hp["folds"], int(hp["folds_won_vs_adhr"])
    else:
        arms = ("phys44_zero_cat", "h88_adhr_incumbent", "exp01_psgv_zero_cat",
                "exp02_psgv_single_joint", "exp03_psgv_poe_conduit")
        terms_o = {a: None for a in arms}; terms_f = {a: None for a in arms}; terms_b = {a: None for a in arms}
        fold_rows = []
        for seed, folds in folds_by_seed:
            X_vis22, d_vis_fp, comp_len_fp = vis_by_seed[seed]
            d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
            for i, fold in enumerate(folds):
                tag = f"seed{seed}_f{i}_{fold['name']}"
                train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
                train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
                res = psgv.predict_psgv_all_arms_fold(
                    g, X_phys, X_phys_diff, X_hgvc, X_psgv, X_vis22, d_vis_fp, comp_len_fp,
                    fold["visible"], train_regions, train_truth, fold["region"],
                    seed=seed * 10 + i, cache_dir=psgv_cache, fold_tag=tag)
                def _sub(thr):
                    t = fold["truth"] & fold["region"] & ~fold["masked_known"] & (d_vis_grid > thr)
                    v = g.footprint & fold["region"] & ~fold["masked_known"] & (d_vis_grid > thr)
                    return {**fold, "truth": t, "region": v, "masked_known": np.zeros_like(v)}, int(t.sum())
                far_fold, n_far = _sub(10.0)
                blind_fold, n_blind = _sub(25.0)
                row = {"seed": seed, "fold": str(fold["name"]),
                       "withheld_positive_pixels": int((fold["truth"] & fold["region"] & ~fold["masked_known"]).sum()),
                       "far_withheld_positive_pixels": n_far, "blind_withheld_positive_pixels": n_blind}
                for arm in arms:
                    em, _, meta = res[arm]
                    so, bo = evaluate_holdout.evaluate(em, fold, g.footprint, block_side=BLOCK_SIDE)
                    sf, bf = evaluate_holdout.evaluate(em, far_fold, g.footprint, block_side=BLOCK_SIDE)
                    sb, bb = evaluate_holdout.evaluate(em, blind_fold, g.footprint, block_side=BLOCK_SIDE)
                    terms_o[arm] = bo if terms_o[arm] is None else terms_o[arm] + bo
                    terms_f[arm] = bf if terms_f[arm] is None else terms_f[arm] + bf
                    terms_b[arm] = bb if terms_b[arm] is None else terms_b[arm] + bb
                    row[arm] = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                                "overall_dti": round(float(so["dti"]), 6),
                                "far_gt10px_dti": round(float(sf["dti"]), 6),
                                "blind_gt25px_dti": round(float(sb["dti"]), 6),
                                "emitted_dots": int(meta["n_dots"])}
                fold_rows.append(row)
                print(f"      [seed={seed} {fold['name']}] ADHR={row['h88_adhr_incumbent']['overall_dti']:.6f} | "
                      f"E1={row['exp01_psgv_zero_cat']['overall_dti']:.6f} | E2={row['exp02_psgv_single_joint']['overall_dti']:.6f} | "
                      f"E3={row[CANDIDATE_ARM]['overall_dti']:.6f} (far={row[CANDIDATE_ARM]['far_gt10px_dti']:.6f}, "
                      f"blind={row[CANDIDATE_ARM]['blind_gt25px_dti']:.6f})", flush=True)
        pooled_overall = evaluate_holdout.pooled_summary(terms_o, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=CANDIDATE_ARM)
        pooled_far10 = evaluate_holdout.pooled_summary(terms_f, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=CANDIDATE_ARM)
        pooled_blind25 = evaluate_holdout.pooled_summary(terms_b, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=CANDIDATE_ARM)
        folds_won = sum(1 for r in fold_rows if r[CANDIDATE_ARM]["overall_dti"] > r["h88_adhr_incumbent"]["overall_dti"])
        hp = {"schema_version": "gems88-psgv88-holdout-v1",
              "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "preregistration_id": prereg["preregistration_id"], "evidence_class": "HOLDOUT-DTI",
              "evaluator_version": evaluate_holdout.VERSION, "seeds": [20, 21], "n_folds": 8,
              "bootstrap_draws": BOOT_DRAWS, "spatial_block_m": BLOCK_SIDE * 100.0,
              "folds_won_vs_adhr": folds_won, "canary_max_symmetric_auc": canary["max_symmetric_auc"],
              "psgv_canary_max_symmetric_auc": canary["psgv_max_symmetric_auc"],
              "pooled_overall": pooled_overall, "pooled_far_gt10px": pooled_far10,
              "pooled_blind_gt25px": pooled_blind25,
              "stored_baselines": {
                  "h88_hgvc_exp03_stored_bar": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2",
                      "withheld_positive_pixels": 22893, "overall_dti": HGVC_BAR, "ci95": [0.185869, 0.21979],
                      "far_gt10px_dti": 0.1328, "blind_gt25px_dti": 0.078959,
                      "source": "registry/hgvc88_run_card.json + evidence/hgvc88_holdout_20261024.json"},
                  "h88_hgvc_exp01_stored": 0.113767, "h88_hgvc_exp02_stored": 0.197582,
                  "h33_owner_claim": {"evidence_class": "USER-REPORTED (no portal receipt in repo)",
                      "submission_id": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", "reported_public_dti": 0.2778,
                      "leaderboard_top_live_20261025": 0.4413}},
              "folds": fold_rows}
        write_json(holdout_path, hp)
        write_json(ROOT / "docs/evidence/psgv88_holdout_20261025.json", hp)
    ov = pooled_overall["scores"][CANDIDATE_ARM]; fr = pooled_far10["scores"][CANDIDATE_ARM]; bl = pooled_blind25["scores"][CANDIDATE_ARM]
    d_ov = pooled_overall["paired_differences"]["h88_adhr_incumbent"]
    d_fr = pooled_far10["paired_differences"]["h88_adhr_incumbent"]
    d_bl = pooled_blind25["paired_differences"]["h88_adhr_incumbent"]
    adhr_inrun = float(pooled_overall["scores"]["h88_adhr_incumbent"]["dti"])
    beats_hgvc_bar = bool(ov["dti"] > HGVC_BAR)
    beats_adhr_paired = bool(d_ov["ci95"][0] > 0.0)
    print(f"      POOLED {CANDIDATE_ARM}: {ov['dti']:.6f} CI={ov['ci95']} (HGVC bar {HGVC_BAR:.6f}, beats={beats_hgvc_bar}; "
          f"ADHR in-run {adhr_inrun:.6f}, paired delta {d_ov['delta']:+.6f} CI={d_ov['ci95']}, {folds_won}/8 won); "
          f"far={fr['dti']:.6f} blind={bl['dti']:.6f}", flush=True)
    if "--stop-after-holdout" in sys.argv:
        print("      Holdout stage complete (--stop-after-holdout).", flush=True)
        return 0

    print("[4/7] Registry for uniqueness (pinned inventory + fleet + siblings + GEMSDOE88 downloads)...", flush=True)
    for old in list((ROOT / "docs/downloads").glob("gems88-psgv88-*")) + list((ROOT / "submissions").glob("gems88-psgv88-*")):
        old.unlink(missing_ok=True)
    reg_entries = registry_list(ROOT, exclude=("gems88-psgv88",))
    print(f"      Registry size: {len(reg_entries)} rasters", flush=True)
    surface_holder: dict = {}

    def _pre_gate(p_surface):
        rk = gate.rank_vec(p_surface, g.footprint)
        mx, lbl, seen = 0.0, "", set()
        for lab, rp in reg_entries:
            vals = gate.read_values(rp, g.footprint)
            key = gate.sha256_bytes(np.packbits(vals > 0).tobytes()) + ("D" if gate.is_dense(vals, g.footprint) else "S")
            if key in seen:
                continue
            seen.add(key)
            rho = abs(gate._pearson(rk, gate.rank_vec(vals, g.footprint)))
            if rho > mx:
                mx, lbl = rho, lab
        surface_holder["max_abs_spearman"] = round(float(mx), 6)
        surface_holder["max_rho_label"] = lbl
        print(f"      Pre-placement max |rho| = {mx:.6f} vs {lbl} (limit 0.90)", flush=True)
        if mx > 0.90:
            raise RuntimeError(f"STOP DUPLICATE BEFORE PLACEMENT: |rho|={mx:.6f} > 0.90 vs {lbl}")

    print("[5/7] OOF production heads + H33-parity allocation (37,654 dots)...", flush=True)
    prod_emitted, prod_surface, prod_meta = psgv.fit_and_emit_production_psgv(
        g, X_phys, X_phys_diff, X_hgvc, X_psgv, folds_by_seed, sense_src, scarp_fields,
        vis_by_seed, psgv_cache, preplacement_gate=_pre_gate)
    print(f"      Emitted {prod_meta['n_dots']} dots: share_le2={prod_meta['share_le2']:.4f} "
          f"share_gt25={prod_meta['share_gt25']:.4f} median_d={prod_meta['median_d_cat_px']:.2f}px", flush=True)
    sample_path = ROOT / "data/bridge/sample_submission.tif"
    d_cat_grid = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_prof = gate.fingerprint(prod_emitted > 0.5, d_cat_grid)
    fp_pass = gate.fingerprint_screen(fp_prof)

    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        sw = submission_writer.write_submission(
            tmp / "sw_check.tif", prod_emitted, sample_path, g.footprint,
            name="GEMSDOE88-PSGV88-SWCHECK", note="PSGV88 shared submission_writer preflight", catalogue=g.catalogue)
        assert sw["validator"]["all_checks_passed"] is True
        lzw_tmp = tmp / "portal_lzw.tif"
        portal_writer.write_portal_tif(lzw_tmp, prod_emitted, sample_path, g.footprint)
        hash8 = sha256_file(lzw_tmp)[:8]
        print("[6/7] Final uniqueness gate (literal + like-for-like)...", flush=True)
        uq = gate.uniqueness_report(lzw_tmp, reg_entries, g.footprint, surface=prod_surface)
        witness_path = ROOT / "data/registry/dense_17gemdoe.tif"
        with rasterio.open(sample_path) as ref:
            expected_grid = (ref.shape, ref.crs, ref.transform)
        sat = uniqueness.saturation_certificate(witness_path, g.footprint, g.catalogue, expected_grid=expected_grid)
        with rasterio.open(witness_path) as wds:
            warr = wds.read(1)
        lit_wit = float(uniqueness.dot_overlap(prod_emitted, (np.isfinite(warr) & (warr > 0)) & g.footprint, 3))
        print(f"      like-for-like unique={uq['unique_like_for_like']} worst={uq['worst_like_for_like_overlap']} "
              f"worst|rho|={uq['worst_abs_rho']}; literal witness={lit_wit:.4f}", flush=True)
        stem = f"gems88-psgv88-pseudograv-discordance-{prod_meta['n_dots']}-20261025-{hash8}-zeros-DO-NOT-SUBMIT"
        sub_name = f"GEMSDOE88-PSGV88-{hash8.upper()}"
        sub_note = (f"PSGV88 FFT pseudogravity discordance+HGVC PoE {prod_meta['n_dots']}d; "
                    f"HOLDOUT-DTI {ov['dti']:.4f} far {fr['dti']:.4f} blind {bl['dti']:.4f}; UNSCORED")
        assert 0 < len(sub_name) <= 140 and 0 < len(sub_note) <= 140
        dl_tif = ROOT / "docs/downloads" / f"{stem}.tif"
        dl_zip = ROOT / "docs/downloads" / f"{stem}.zip"
        dl_receipt = ROOT / "docs/downloads" / f"{stem}.json"
        dl_audit = ROOT / "docs/downloads" / f"{stem}.format-audit.json"
        sub_tif = ROOT / "submissions" / f"{stem}.tif"
        sub_zip = ROOT / "submissions" / f"{stem}.zip"
        sub_receipt = ROOT / "submissions" / f"{stem}.json"
        shutil.copy2(lzw_tmp, dl_tif)
        portal_writer.write_single_member_zip(dl_zip, dl_tif)
        for p in (dl_tif, dl_zip):
            os.chmod(p, 0o644)
        shutil.copy2(dl_tif, sub_tif); shutil.copy2(dl_zip, sub_zip)
        for p in (sub_tif, sub_zip):
            os.chmod(p, 0o644)

    print("[7/7] Independent re-open audit (.tif + .zip, second decoder)...", flush=True)
    p_tif = gate.portal_validate(dl_tif, sample_path, g.footprint)
    p_zip = gate.portal_validate(dl_zip, sample_path, g.footprint)
    indep = validate_artifact(dl_tif, sample_path)
    fmt = g57gates.format_report(dl_tif, sample_path, footprint=g.footprint)
    val = g57validate.validate(dl_tif, g.footprint, g.catalogue)
    g57validate.assert_submittable(val)
    if not (p_tif["ok"] and p_zip["ok"] and p_tif["layout_parity_with_sample"] and indep["ok"]
            and fmt["ok"] and val["all_checks_passed"] and p_tif["array_sha256"] == p_zip["array_sha256"]):
        raise RuntimeError(f"Saved format audit failed: tif={p_tif['problems']} zip={p_zip['problems']}")
    tif_sha, zip_sha = sha256_file(dl_tif), sha256_file(dl_zip)

    beats_bar = bool(beats_hgvc_bar and beats_adhr_paired)
    used_names = set()
    for rc in (ROOT / "registry").glob("*.json"):
        if "psgv" in rc.name:
            continue
        try:
            d = json.loads(rc.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("submission_name"), str):
                used_names.add(d["submission_name"])
        except Exception:
            pass
    uq_dec = {**uq, "registry_complete": bool(uq["missing"] == 0 and uq["registry_rasters"] >= 200),
              "surface_checked": True}
    v3 = gate.decide(portal=p_tif, uniqueness=uq_dec, canary_passed=bool(canary["passed"]),
                     holdout_beats_bar=bool(beats_bar and fp_pass), name=sub_name, note=sub_note,
                     used_names=used_names, receipt_sha_matches=True)
    discriminating = bool(p_tif["ok"] and p_tif["layout_parity_with_sample"] and canary["passed"]
                          and beats_bar and fp_pass and uq["unique_like_for_like"]
                          and uq["worst_like_for_like_overlap"]["value"] <= 0.70
                          and uq["worst_abs_rho"]["value"] <= 0.90
                          and surface_holder["max_abs_spearman"] <= 0.90)
    blocking = list(v3["blocking_reasons"])
    if lit_wit > 0.70 and not any("literal" in r.lower() for r in blocking):
        blocking.append(f"UNIQUENESS (binding literal rule, IR-88-86): forward 3-px overlap = {lit_wit:.4f} > 0.70 "
                        "against full-footprint continuous 17GEMSDOE witness (see IR-88-118 category defect)")
    if not beats_hgvc_bar:
        blocking.append(f"HOLDOUT: candidate {ov['dti']:.6f} did not exceed stored HGVC bar {HGVC_BAR:.6f} "
                        "(pre-registered kill rule; no slot spent on an unproven idea)")
    ok_submit = bool(discriminating and uq["unique_literal"] and lit_wit <= 0.70)
    verdict = "promote-to-selector-only" if (discriminating and not ok_submit) else ("promote" if ok_submit else "negative")
    if not discriminating:
        verdict = "negative"

    okrows = [r for r in uq["rows"] if "error" not in r and "duplicate_of" not in r]
    top10 = sorted(okrows, key=lambda r: r["like_for_like_overlap_3px"], reverse=True)[:10]
    vs_h33 = next((r for r in uq["rows"] if "h33" in str(r.get("label", "")).lower()), None)
    vs_hgvc = next((r for r in uq["rows"] if "hgvc88" in str(r.get("label", "")).lower()), None)
    uq_slim = {"policy": uq["policy"], "candidate": f"docs/downloads/{dl_tif.name}", "candidate_sha256": tif_sha,
               "candidate_dots": uq["candidate_dots"], "registry_rasters_checked": uq["registry_rasters"],
               "distinct_dot_sets_checked": uq["distinct_dot_sets"], "missing": uq["missing"],
               "surface_preplacement_max_abs_spearman": surface_holder["max_abs_spearman"],
               "surface_preplacement_max_label": surface_holder["max_rho_label"],
               "worst_like_for_like_overlap": uq["worst_like_for_like_overlap"], "worst_abs_rho": uq["worst_abs_rho"],
               "like_for_like_blockers": uq["like_for_like_blockers"], "unique_like_for_like": uq["unique_like_for_like"],
               "literal_all_positive_witness_overlap_3px": lit_wit, "saturation_certificate": sat,
               "unique_literal": uq["unique_literal"], "vacuity_witness": uq["vacuity_witness"],
               "overlap_vs_h33_row": vs_h33, "overlap_vs_hgvc88_row": vs_hgvc,
               "top10_like_for_like_overlaps": top10}
    write_json(ROOT / "evidence/psgv88_uniqueness.json", uq_slim)
    write_json(dl_audit, {"portal_tif": p_tif, "portal_zip": p_zip, "independent_validate_artifact": indep,
                          "shared_gates_format_report": fmt, "shared_validate": val})
    wm = {"file": dl_tif.name, "zip_file": dl_zip.name, "sha256": tif_sha, "zip_sha256": zip_sha,
          "submission_name": sub_name, "submission_note": sub_note, "note_length": len(sub_note),
          "positive_pixels": int(prod_meta["n_dots"]), "ok_to_download": True, "ok_to_submit": ok_submit,
          "discriminating_gates_pass": discriminating, "verdict": verdict, "weekly_slots_spent": 0,
          "organizer_confirmed_score": None}
    write_json(dl_receipt, wm); write_json(sub_receipt, wm)
    elapsed = round(time.monotonic() - t0, 2)
    gate_doc = {"schema": "gems88.psgv88.gate_v3.v1", "policy": gate.POLICY_VERSION,
                "binding_literal_policy": "IR-88-86-literal-all-registry-v1", "name": stem,
                "submission_name": sub_name, "submission_note": sub_note,
                "candidate": {"tif": f"docs/downloads/{dl_tif.name}", "zip": f"docs/downloads/{dl_zip.name}",
                              "sha256": tif_sha, "zip_sha256": zip_sha, "dots": int(prod_meta["n_dots"])},
                "sha256": tif_sha, "zip_sha256": zip_sha, "ok_to_download": True, "ok_to_submit": ok_submit,
                "eligible_for_selector": bool(v3["eligible_for_selector"] and discriminating),
                "discriminating_gates_pass": discriminating, "verdict": verdict,
                "label": ("OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT" if not ok_submit else v3["label"]),
                "blocking_reasons": blocking, "portal_values_and_grid_ok": bool(p_tif["ok"] and p_zip["ok"]),
                "portal_layout_parity_with_sample": bool(p_tif["layout_parity_with_sample"]),
                "leakage_canary_pass": bool(canary["passed"]), "fingerprint": fp_prof,
                "fingerprint_screen_pass": fp_pass,
                "holdout_comparison": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                    "withheld_positives": int(ov["withheld_positive_pixels"]), "candidate_dti": float(ov["dti"]),
                    "candidate_ci95": ov["ci95"], "far_gt10px_dti": float(fr["dti"]), "far_gt10px_ci95": fr["ci95"],
                    "blind_gt25px_dti": float(bl["dti"]), "blind_gt25px_ci95": bl["ci95"],
                    "adhr_inrun_dti": adhr_inrun, "paired_delta_vs_adhr": d_ov, "folds_won_vs_adhr": folds_won,
                    "hgvc_stored_bar": HGVC_BAR, "beats_hgvc_bar_point": beats_hgvc_bar,
                    "hgvc_margin_vs_adhr_stored": HGVC_MARGIN_VS_ADHR},
                "uniqueness": {"registry_rasters_checked": uq["registry_rasters"],
                    "distinct_dot_sets_checked": uq["distinct_dot_sets"],
                    "surface_preplacement_max_abs_spearman": surface_holder["max_abs_spearman"],
                    "worst_like_for_like_overlap": uq["worst_like_for_like_overlap"], "worst_abs_rho": uq["worst_abs_rho"],
                    "unique_like_for_like": uq["unique_like_for_like"],
                    "literal_all_positive_witness_overlap_3px": lit_wit, "unique_literal": uq["unique_literal"]},
                "weekly_slots_spent": 0, "organizer_confirmed_score": None, "elapsed_seconds": elapsed}
    write_json(ROOT / "registry/psgv88_gate_v3.json", gate_doc)
    write_json(ROOT / "docs/data/psgv88_gate_v3.json", gate_doc)

    run_card = {"schema": "gems88.psgv88.run_card.v1", "run_id": f"GEMSDOE88-PSGV88-20261025-{hash8}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "lane": "H88-PSGV",
        "preregistration_id": prereg["preregistration_id"], "hypothesis": prereg["hypothesis"],
        "mechanism": prereg["mechanism"], "named_non_fault_mimic": prereg["named_non_fault_mimic"],
        "experiments_executed": 3, "experiment_budget_max": 3, "elapsed_seconds": elapsed,
        "wallclock_budget_seconds_max": 7200,
        "holdout_dti": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21], "n_folds": 8, "withheld_positive_pixels": int(ov["withheld_positive_pixels"]),
            "folds_won_vs_adhr": folds_won, "candidate_exp03": ov,
            "exp01_zero_cat": pooled_overall["scores"]["exp01_psgv_zero_cat"],
            "exp02_single_joint": pooled_overall["scores"]["exp02_psgv_single_joint"],
            "control_phys44_zero_cat": pooled_overall["scores"]["phys44_zero_cat"],
            "control_h88_adhr_incumbent": pooled_overall["scores"]["h88_adhr_incumbent"],
            "far_gt10px": fr, "blind_gt25px": bl, "paired_delta_vs_adhr_overall": d_ov,
            "paired_delta_vs_adhr_far_gt10px": d_fr, "paired_delta_vs_adhr_blind_gt25px": d_bl,
            "hgvc_stored_bar_unpaired": {"dti": HGVC_BAR, "ci95": [0.185869, 0.21979], "beats_point": beats_hgvc_bar,
                "note": "Stored-bar comparison is unpaired; in-run paired contrast is vs ADHR. HGVC Exp03 was not refit in this lane (budget); identical folds/seeds/evaluator make the point comparison informative but not a paired CI."}},
        "leakage_canary": {k: canary[k] for k in ("passed", "threshold", "features_tested", "max_symmetric_auc",
            "max_feature", "psgv_max_symmetric_auc", "psgv_features", "top15_all_features")},
        "correlation_overlap_vs_registry": {"evidence_class": "REGISTRY-MEASUREMENT",
            "registry_rasters_checked": uq["registry_rasters"], "distinct_dot_sets_checked": uq["distinct_dot_sets"],
            "surface_preplacement_max_abs_spearman": surface_holder["max_abs_spearman"],
            "surface_preplacement_max_label": surface_holder["max_rho_label"],
            "final_max_abs_spearman": uq["worst_abs_rho"]["value"], "final_max_rho_label": uq["worst_abs_rho"]["label"],
            "final_worst_like_for_like_overlap_3px": uq["worst_like_for_like_overlap"],
            "unique_like_for_like": uq["unique_like_for_like"],
            "literal_all_positive_witness_overlap_3px": lit_wit, "unique_literal": uq["unique_literal"]},
        "raster_sha256": tif_sha, "zip_sha256": zip_sha,
        "download": f"docs/downloads/{dl_tif.name}", "zip_download": f"docs/downloads/{dl_zip.name}",
        "repo_copy": f"submissions/{sub_tif.name}",
        "validator_output": {"portal_ok": bool(p_tif["ok"] and p_zip["ok"]),
            "layout_parity_with_sample": bool(p_tif["layout_parity_with_sample"]),
            "no_nan_inside_footprint": bool(p_tif["checks"]["footprint_cells_finite"]),
            "no_nan_anywhere": bool(p_tif["checks"]["all_finite"]),
            "values_in_0_1": bool(p_tif["checks"]["portal_range_check_nan_strict"]),
            "crs_match": bool(p_tif["checks"]["crs_epsg_32611"]),
            "shape_match": bool(p_tif["checks"]["shape_matches_sample"]),
            "transform_match": bool(p_tif["checks"]["transform_matches_sample"]),
            "nodata_undeclared": bool(p_tif["checks"]["nodata_undeclared"]),
            "outside_footprint_zero": bool(p_tif["checks"]["outside_footprint_zero"]),
            "zero_on_mapped_catalogue": bool(val["checks"]["zero_dots_on_mapped_catalogue"]),
            "second_decoder": p_tif["second_decoder"], "positive_dots": int(prod_meta["n_dots"]),
            "fingerprint": fp_prof, "fingerprint_screen_pass": fp_pass,
            "raster_sha256": tif_sha, "zip_sha256": zip_sha},
        "submission_name": sub_name, "submission_name_length": len(sub_name),
        "submission_note": sub_note, "submission_note_length": len(sub_note),
        "discriminating_gates_pass": discriminating, "ok_to_download": True, "ok_to_submit": ok_submit,
        "verdict": verdict, "blocking_reasons": blocking, "organizer_confirmed_score": None,
        "weekly_slots_spent": 0,
        "leaderboard_live_check": {"evidence_class": "OFFICIAL-PUBLIC-LEADERBOARD-SNAPSHOT",
            "source_url": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
            "checked_utc": "2026-10-25", "top_public_dti": 0.4413, "rank5_cut_dti": 0.3539,
            "note": "Read live this session; H33 0.2778 remains USER-REPORTED with no receipt in repo."}}
    write_json(ROOT / "registry/psgv88_run_card.json", run_card)
    write_json(ROOT / "docs/data/psgv88_run_card.json", run_card)
    write_json(ROOT / "evidence/psgv88_run_card.json", run_card)
    print(f"\nDONE in {elapsed:.1f}s docs/downloads/{dl_tif.name} sha={tif_sha}\n"
          f"  discriminating={discriminating} ok_download=True ok_submit={ok_submit} verdict={verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
