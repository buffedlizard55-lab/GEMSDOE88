#!/usr/bin/env python3
"""Run the preregistered H88-GTD 3-experiment holdout suite and emit the validated GeoTIFF.

Lane: H88-GTD — potential-field gradient-tensor source dimensionality
(14 zero-catalogue channels in ``src/gems88/gtd.py``) appended to the cached
PHYS-44 + HGVC-20 + BPWD PSGV-20 stacks inside the identical dual-expectation
LightGBM specialists, distance-adaptive tri-specialist Log-Odds PoE and exact
Dinkelbach allocator as H88-BPWD, plus the preregistered incumbent-proximity
novelty discount. Preregistration: ``registry/preregistration_gtd88.json``.

Reuses unmodified ``vendor/gems57/`` (``holdout.buffered_component_draw``,
``evaluate_holdout``, ``submission_writer``, ``uniqueness`` incl. the
representation-aware ``binding_duplicate_decision_v4``, ``validate``,
``gates``) and ``src/gems88/`` (``adhr``, ``bpwd``, ``gate``, ``hgvc``,
``physics``, ``portal_writer``, ``registry_paths``). No private metric/writer
forks. The CLI is guarded by the shared generation preflight (v4
preregistered-lane path); promotion to ``ok_to_submit`` additionally requires
every frozen gate in the preregistration to pass on saved bytes.
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
import resource
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
    evaluate_holdout,
    gates as g57gates,
    grid as grid_mod,
    holdout,
    submission_writer,
    uniqueness,
    validate as g57validate,
)
from gems88 import adhr, bpwd, edge, gate, gtd, hgvc, physics, portal_writer  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

BLOCK_SIDE = 200
BOOT_DRAWS = 2000
BOOT_SEED = 521088
CANDIDATE_ARM = "exp03_gtd_tri_poe_novel"
BAR_ARM = "h88_bpwd_incumbent"
BPWD_STORED_RECORD = 0.205991


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class DuplicateStop(RuntimeError):
    """Pre-placement surface already duplicates a registry raster; stop before placement."""


def run_single_feature_canary(zero_cat_groups, vis_by_seed, g, folds_by_seed) -> dict:
    """Test every input feature alone on held-out positives; symmetric AUC > 0.90 = leakage."""
    ys, xs = np.nonzero(g.footprint)
    rows = []
    max_sym = 0.0
    max_feat = ""
    for seed, folds in folds_by_seed:
        hidden = folds[0]["hidden_all"][ys, xs]
        vis = folds[0]["visible"][ys, xs]
        pos = np.flatnonzero(hidden)
        neg_pool = np.flatnonzero(~hidden & ~vis)
        rng = np.random.default_rng(8900 + seed)
        neg = rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), dtype=np.int32), np.zeros(len(neg), dtype=np.int32)])
        tr_tru_seed = np.logical_or.reduce([folds[j]["truth"] for j in range(1, 4)])
        wlaw_c = hgvc.damagezone_envelope.fit_width_law(
            vis_by_seed[seed][2], vis_by_seed[seed][1], tr_tru_seed[ys, xs], quantile=0.90, l0_px=40.0
        )
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
                    max_sym = sym
                    max_feat = f"{name} (seed={seed})"
                if seed == 20:
                    rows.append({"feature": name, "group": group,
                                 "roc_auc": round(auc, 6), "symmetric_auc": round(sym, 6)})
    rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
    passed = bool(max_sym <= 0.90)
    if not passed:
        raise RuntimeError(f"STOP: single-feature leakage canary tripped: {max_feat} = {max_sym:.6f} > 0.90")
    total_tested = int(sum(len(names) for _, names, _ in zero_cat_groups) + len(adhr.VIS_STRUCT_FEATURES))
    gtd_rows = [r for r in rows if r["group"] == "GTD-14"]
    return {
        "passed": passed,
        "threshold": 0.90,
        "features_tested": total_tested,
        "zero_catalogue_features_tested": int(sum(len(names) for _, names, _ in zero_cat_groups)),
        "fold_visible_features_tested": len(adhr.VIS_STRUCT_FEATURES),
        "max_symmetric_auc": round(max_sym, 6),
        "max_feature": max_feat,
        "max_zero_catalogue_symmetric_auc": round(max(r["symmetric_auc"] for r in rows if r["group"] != "VIS-22"), 6),
        "max_gtd14_symmetric_auc": round(max(r["symmetric_auc"] for r in gtd_rows), 6) if gtd_rows else None,
        "top15_all_features": rows[:15],
        "gtd14_features": gtd_rows,
    }


def collect_full_registry(root: Path, exclude_substr: tuple[str, ...] = ("gems88-gtd88",)) -> list[tuple[str, Path]]:
    """Pinned registry + this repo's downloads + fetched GEMSDOE86/87 HEAD + scored fleet, SHA-deduped."""
    base = list(registry_list(root, exclude=exclude_substr))
    seen_paths = {p.resolve() for _, p in base}
    seen_shas = {sha256_file(p) for _, p in base}
    head_dir = root / "data/siblings_head"
    if head_dir.is_dir():
        for p in sorted(head_dir.glob("*.tif")):
            rp = p.resolve()
            if rp in seen_paths or any(ex and ex in p.name for ex in exclude_substr):
                continue
            s = sha256_file(p)
            if s in seen_shas:
                continue
            seen_paths.add(rp)
            seen_shas.add(s)
            base.append((f"sibling_head_20261025:{p.name}", p))
    return base


def build_v4_rows(candidate_path: Path, surface: np.ndarray, registry, footprint) -> tuple[dict, list[dict]]:
    """Representation-aware v4 decision (vendor template) + verbatim literal diagnostics."""
    cand = gate.read_values(candidate_path, footprint)
    cand_dots = (cand > 0) & footprint
    n = int(cand_dots.sum())
    cand_sha = sha256_file(candidate_path)
    rows = []
    seen_decoded: dict[str, dict] = {}
    for label, path in registry:
        path = Path(path)
        if not path.is_file():
            rows.append({"file": str(path), "label": label, "error": "missing"})
            continue
        vals = gate.read_values(path, footprint)
        key = gate.sha256_bytes(np.ascontiguousarray(vals).tobytes())
        if key in seen_decoded:
            r = dict(seen_decoded[key])
            r.update(file=str(path), label=label)
            rows.append(r)
            continue
        kind = uniqueness.classify_values(vals, footprint)
        lit = float(uniqueness.dot_overlap(cand, vals))
        topn = None
        if kind == "continuous_surface":
            eff = uniqueness.topn_dots(vals, footprint, n)
            topn = float(uniqueness._near(eff)[cand_dots].mean()) if n else 0.0
        rho_final = gate.spearman_on_footprint(cand, vals, footprint)
        rho_surf = gate.spearman_on_footprint(np.asarray(surface, np.float32), vals, footprint)
        rho = rho_final if abs(rho_final) >= abs(rho_surf) else rho_surf
        r = {
            "file": str(path), "label": label,
            "forward_overlap": lit, "spearman": float(rho),
            "spearman_final": float(rho_final), "spearman_surface": float(rho_surf),
            "is_continuous_surface": kind == "continuous_surface",
            "representation": kind, "topn_overlap": topn,
            "identical_bytes": bool(sha256_file(path) == cand_sha),
            "identical_decoded_predictions": bool(np.array_equal(cand_dots, (vals > 0) & footprint)),
        }
        rows.append(r)
        seen_decoded[key] = r
    decision = uniqueness.binding_duplicate_decision_v4(rows)
    return decision, rows


def main() -> int:
    t0 = time.monotonic()
    prereg_path = ROOT / "registry/preregistration_gtd88.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("Preregistration must be frozen before running experiments")

    print("[1/7] Loading grid & building/loading PHYS-44 + HGVC-20 + PSGV-20 (BPWD) + GTD-14 memmaps...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    shared_cache = ROOT / ".cache/gems88"
    hgvc_cache = ROOT / ".cache/gems88_hgvc"
    psgv_cache = ROOT / ".cache/gems88_psgv"
    gtd_cache = ROOT / ".cache/gems88_gtd"
    for cdir in (shared_cache, hgvc_cache, psgv_cache, gtd_cache):
        cdir.mkdir(parents=True, exist_ok=True)

    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, shared_cache)
    X_hgvc, hgvc_meta = hgvc.build_or_load_hgvc_memmap(ROOT, g, hgvc_cache)
    X_psgv, psgv_meta = bpwd.build_or_load_psgv_memmap(ROOT, g, psgv_cache)
    X_gtd, gtd_meta = gtd.build_or_load_gtd_memmap(ROOT, g, gtd_cache)
    X_phys_diff = hgvc.ColumnSubsetView(X_phys, hgvc.PHYS_DIFF_INDICES)
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    print(f"      GTD-14 ready: shape={gtd_meta['shape']}, zero_catalogue_reads={gtd_meta['zero_catalogue_reads']}, peak_rss={rss_mb:.1f} MB", flush=True)

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        if src.tags(12).get("band_name") != "det_elev":
            raise ValueError("Band 12 must be det_elev (IR-88-110 guard)")
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, hgvc_cache)
    del det_elev
    gc.collect()

    sense_csv = ROOT / "data/external/trace_segments_utm11.csv"
    if not sense_csv.is_file():
        raise FileNotFoundError(f"Missing explicit trace_segments_utm11.csv: {sense_csv}")
    sense_src = adhr.build_sense_raster(sense_csv, g)

    folds_by_seed: list[tuple[int, list[dict]]] = []
    vis_by_seed: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))
        vis_by_seed[seed] = adhr.compute_visible_struct_fp(
            g, folds[0]["visible"], sense_src, scarp_fields, hgvc_cache, f"seed{seed}"
        )

    print("[2/7] Leakage canary (98 zero-catalogue + 23 fold-visible = 121 features) & scramble invariance...", flush=True)
    canary_path = ROOT / "evidence/gtd88_canaries.json"
    canary = None
    scramble_ok = False
    if canary_path.is_file() and "--recompute-canary" not in sys.argv:
        canary = json.loads(canary_path.read_text(encoding="utf-8"))
        scramble_ok = bool(canary.get("zero_test_quadrant_leakage_scramble_equal"))
    if not (canary and canary.get("features_tested") == 121 and canary.get("passed") and scramble_ok):
        canary = run_single_feature_canary(
            [
                (X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
                (X_hgvc, list(hgvc.HGVC_FEATURES), "HGVC-20"),
                (X_psgv, list(bpwd.PSGV_FEATURES), "PSGV-20"),
                (X_gtd, list(gtd.GTD_FEATURES), "GTD-14"),
            ],
            vis_by_seed, g, folds_by_seed,
        )
        f0_s20 = folds_by_seed[0][1][0]
        tr_reg_0 = np.logical_or.reduce([folds_by_seed[0][1][j]["region"] for j in range(1, 4)])
        tr_tru_0 = np.logical_or.reduce([folds_by_seed[0][1][j]["truth"] for j in range(1, 4)])
        scramble_ok = gtd.verify_zero_test_quadrant_leakage(
            g, X_phys, X_psgv, X_gtd, X_hgvc,
            vis_by_seed[20][0], vis_by_seed[20][1], vis_by_seed[20][2],
            f0_s20, tr_reg_0, tr_tru_0, seed=200,
        )
        if not scramble_ok:
            raise RuntimeError("STOP: test-quadrant scramble invariance check failed!")
        canary["zero_test_quadrant_leakage_scramble_equal"] = True
        write_json(canary_path, canary)
    print(
        f"      PASS {canary['features_tested']}/{canary['features_tested']} <= 0.90 "
        f"(max={canary['max_symmetric_auc']:.6f} on {canary['max_feature']}; "
        f"max_zero_cat={canary['max_zero_catalogue_symmetric_auc']:.6f}; "
        f"max_gtd14={canary['max_gtd14_symmetric_auc']:.6f}); scramble_equal={scramble_ok}",
        flush=True,
    )
    if "--stop-after-canary" in sys.argv:
        return 0

    print("[3/7] 8-fold buffered whole-component holdout (4 controls + 3 preregistered GTD experiments)...", flush=True)
    holdout_cache_path = ROOT / "evidence/gtd88_holdout_20261025.json"
    arms = (
        "phys44_zero_cat", "h88_adhr_incumbent", "h88_hgvc_incumbent", "h88_bpwd_incumbent",
        "exp01_gtd_zero_cat", "exp02_gtd_tri_poe", "exp03_gtd_tri_poe_novel",
    )
    if holdout_cache_path.is_file() and "--recompute-holdout" not in sys.argv:
        holdout_payload = json.loads(holdout_cache_path.read_text(encoding="utf-8"))
        pooled_overall = holdout_payload["pooled_overall"]
        pooled_far10 = holdout_payload["pooled_far_gt10px"]
        pooled_blind25 = holdout_payload["pooled_blind_gt25px"]
        pooled_overall_exp02 = holdout_payload["pooled_overall_exp02_candidate"]
        fold_rows = holdout_payload["folds"]
        print("      LOADED CACHED 8-FOLD HOLDOUT (use --recompute-holdout to refit)", flush=True)
    else:
        terms_overall = {a: None for a in arms}
        terms_far10 = {a: None for a in arms}
        terms_blind25 = {a: None for a in arms}
        fold_rows = []
        for seed, folds in folds_by_seed:
            X_vis22, d_vis_fp, comp_len_fp = vis_by_seed[seed]
            d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
            for i, fold in enumerate(folds):
                qname = str(fold["name"])
                tag = f"seed{seed}_f{i}_{qname}"
                train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
                train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
                test_region = fold["region"]
                res = gtd.predict_gtd_suite_fold(
                    g, X_phys, X_phys_diff, X_hgvc, X_psgv, X_gtd, X_vis22,
                    d_vis_fp, comp_len_fp, fold["visible"], train_regions, train_truth,
                    test_region, seed=seed * 10 + i,
                    psgv_cache_dir=psgv_cache, gtd_cache_dir=gtd_cache, fold_tag=tag,
                )
                far_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
                far_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
                far_fold = {**fold, "truth": far_truth, "region": far_valid, "masked_known": np.zeros_like(far_valid)}
                blind_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
                blind_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
                blind_fold = {**fold, "truth": blind_truth, "region": blind_valid, "masked_known": np.zeros_like(blind_valid)}
                row = {
                    "seed": seed, "fold": qname,
                    "withheld_positive_pixels": int((fold["truth"] & test_region & ~fold["masked_known"]).sum()),
                    "far_withheld_positive_pixels": int(far_truth.sum()),
                    "blind_withheld_positive_pixels": int(blind_truth.sum()),
                }
                for arm in arms:
                    emitted_arm, _, meta_arm = res[arm]
                    sc_ov, bt_ov = evaluate_holdout.evaluate(emitted_arm, fold, g.footprint, block_side=BLOCK_SIDE)
                    sc_fr, bt_fr = evaluate_holdout.evaluate(emitted_arm, far_fold, g.footprint, block_side=BLOCK_SIDE)
                    sc_bl, bt_bl = evaluate_holdout.evaluate(emitted_arm, blind_fold, g.footprint, block_side=BLOCK_SIDE)
                    terms_overall[arm] = bt_ov if terms_overall[arm] is None else terms_overall[arm] + bt_ov
                    terms_far10[arm] = bt_fr if terms_far10[arm] is None else terms_far10[arm] + bt_fr
                    terms_blind25[arm] = bt_bl if terms_blind25[arm] is None else terms_blind25[arm] + bt_bl
                    row[arm] = {
                        "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                        "overall_dti": round(float(sc_ov["dti"]), 6),
                        "far_gt10px_dti": round(float(sc_fr["dti"]), 6),
                        "blind_gt25px_dti": round(float(sc_bl["dti"]), 6),
                        "emitted_dots": int(meta_arm["n_dots"]),
                    }
                fold_rows.append(row)
                print(
                    f"      [seed={seed} {qname}] BPWD={row[BAR_ARM]['overall_dti']:.6f} | "
                    f"E1={row['exp01_gtd_zero_cat']['overall_dti']:.6f} | E2={row['exp02_gtd_tri_poe']['overall_dti']:.6f} | "
                    f"E3={row[CANDIDATE_ARM]['overall_dti']:.6f} (far={row[CANDIDATE_ARM]['far_gt10px_dti']:.6f}, "
                    f"blind={row[CANDIDATE_ARM]['blind_gt25px_dti']:.6f})",
                    flush=True,
                )
                del res
                gc.collect()
        pooled_overall = evaluate_holdout.pooled_summary(terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=CANDIDATE_ARM)
        pooled_overall_exp02 = evaluate_holdout.pooled_summary(terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate="exp02_gtd_tri_poe")
        pooled_far10 = evaluate_holdout.pooled_summary(terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=CANDIDATE_ARM)
        pooled_blind25 = evaluate_holdout.pooled_summary(terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=CANDIDATE_ARM)
        holdout_payload = {
            "schema_version": "gems88-gtd88-holdout-v1",
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "preregistration_id": prereg["preregistration_id"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21], "n_folds": 8,
            "bootstrap_draws": BOOT_DRAWS, "spatial_block_m": BLOCK_SIDE * 100.0,
            "zero_leakage_quadrant_scramble_equal": True,
            "canary": canary,
            "pooled_overall": pooled_overall,
            "pooled_overall_exp02_candidate": pooled_overall_exp02,
            "pooled_far_gt10px": pooled_far10,
            "pooled_blind_gt25px": pooled_blind25,
            "stored_baselines": {
                "h88_bpwd_stored_record": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2",
                                           "withheld_positive_pixels": 22893, "overall_dti": BPWD_STORED_RECORD,
                                           "far_gt10px_dti": 0.136782, "blind_gt25px_dti": 0.072733},
                "h33_owner_claim": {"evidence_class": "USER-REPORTED (no portal receipt in repo)",
                                    "submission_id": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                                    "reported_public_dti": 0.2778},
            },
            "folds": fold_rows,
        }
        write_json(holdout_cache_path, holdout_payload)

    ov = pooled_overall["scores"]
    ov_cand = ov[CANDIDATE_ARM]
    ov_bar = ov[BAR_ARM]
    fr_cand = pooled_far10["scores"][CANDIDATE_ARM]
    bl_cand = pooled_blind25["scores"][CANDIDATE_ARM]
    delta_bpwd = pooled_overall["paired_differences"][BAR_ARM]
    delta_bpwd_far = pooled_far10["paired_differences"][BAR_ARM]
    delta_bpwd_blind = pooled_blind25["paired_differences"][BAR_ARM]
    exp02_delta_bpwd = pooled_overall_exp02["paired_differences"][BAR_ARM]
    folds_won = sum(1 for r in fold_rows if r[CANDIDATE_ARM]["overall_dti"] > r[BAR_ARM]["overall_dti"])
    print(
        f"      POOLED HOLDOUT-DTI E3={ov_cand['dti']:.6f} CI={ov_cand['ci95']} | BPWD-control={ov_bar['dti']:.6f} "
        f"(stored record {BPWD_STORED_RECORD}) | paired delta={delta_bpwd['delta']:+.6f} CI={delta_bpwd['ci95']} ({folds_won}/8 folds won)\n"
        f"      E1={ov['exp01_gtd_zero_cat']['dti']:.6f} E2={ov['exp02_gtd_tri_poe']['dti']:.6f} "
        f"(E2 delta vs BPWD={exp02_delta_bpwd['delta']:+.6f} CI={exp02_delta_bpwd['ci95']}) | "
        f"E3 far={fr_cand['dti']:.6f} blind={bl_cand['dti']:.6f}",
        flush=True,
    )
    if "--stop-after-holdout" in sys.argv:
        return 0

    print("[4/7] Collecting accessible registry + incumbent dot union (BPWD + HGVC + H33)...", flush=True)
    reg_entries = collect_full_registry(ROOT, exclude_substr=("gems88-gtd88",))
    print(f"      Registry size for uniqueness check: {len(reg_entries)} rasters (file-SHA distinct)", flush=True)
    incumbent = np.zeros(g.footprint.shape, dtype=bool)
    inc_sources = {}
    for label, pat in (
        ("H88-BPWD", "docs/downloads/gems88-bpwd88-baranov-worm-conduit-37654-20261025-b8543782-zeros-DO-NOT-SUBMIT.tif"),
        ("H88-HGVC", "docs/downloads/gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.tif"),
        ("H33", "data/registry/h33_education.tif"),
    ):
        p = ROOT / pat
        vals = gate.read_values(p, g.footprint)
        dots = (vals > 0) & g.footprint
        incumbent |= dots
        inc_sources[label] = {"file": pat, "sha256": sha256_file(p), "dots": int(dots.sum())}
    print(f"      Incumbent union dots: {int(incumbent.sum())}", flush=True)

    surface_check: dict[str, object] = {}

    def _preplacement_surface_gate(p_surface: np.ndarray) -> None:
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
        surface_check["max_abs_spearman"] = round(float(max_rho), 6)
        surface_check["max_rho_label"] = max_lbl
        surface_check["distinct_surfaces_checked"] = len(seen_k)
        print(f"      Pre-placement surface max |Spearman rho| = {max_rho:.6f} vs {max_lbl} (limit 0.90)", flush=True)
        if max_rho > 0.90:
            raise DuplicateStop(f"STOP DUPLICATE BEFORE PLACEMENT: surface |rho| = {max_rho:.6f} > 0.90 vs {max_lbl}")

    print("[5/7] OOF production heads & discounted stratified allocation (37,654 dots)...", flush=True)
    prod_plan = prereg["production_emission_plan"]
    try:
        prod_emitted, prod_surface, prod_meta = gtd.fit_and_emit_production_gtd(
            g, X_phys, X_phys_diff, X_hgvc, X_psgv, X_gtd,
            folds_by_seed, sense_src, scarp_fields, vis_by_seed,
            psgv_cache, gtd_cache, incumbent,
            near_budget=int(prod_plan["near_budget"]), far_budget=int(prod_plan["far_budget"]),
            near_spacing_px=float(prod_plan["near_spacing_px"]), far_spacing_px=float(prod_plan["far_spacing_px"]),
            preplacement_gate=_preplacement_surface_gate,
        )
    except DuplicateStop as exc:
        run_card = {
            "schema": "gems.run_card.v1", "lane": "H88-GTD", "preregistration_id": prereg["preregistration_id"],
            "verdict": "negative", "stop_reason": str(exc),
            "holdout_dti": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                            "candidate_exp03": ov_cand, "bpwd_control": ov_bar, "paired_delta_vs_bpwd": delta_bpwd},
            "surface_preplacement": surface_check, "raster_sha256": None,
            "ok_to_download": False, "ok_to_submit": False, "weekly_slots_used": 0,
            "organizer_confirmed_score": None,
        }
        write_json(ROOT / "registry/gtd88_run_card.json", run_card)
        print(json.dumps(run_card, indent=2))
        return 0
    print(
        f"      Emitted {prod_meta['n_dots']} dots: share_le2={prod_meta['share_le2']:.4f}, "
        f"share_gt25={prod_meta['share_gt25']:.4f}, median_d_cat={prod_meta['median_d_cat_px']:.2f} px",
        flush=True,
    )

    sample_path = ROOT / "data/bridge/sample_submission.tif"
    d_cat_grid = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_prof = gate.fingerprint(prod_emitted > 0.5, d_cat_grid)
    fp_pass = gate.fingerprint_screen(fp_prof)

    with tempfile.TemporaryDirectory() as tmpd:
        tmp_dir = Path(tmpd)
        sw_tif = tmp_dir / "sw_check.tif"
        sw_receipt = submission_writer.write_submission(
            sw_tif, prod_emitted, sample_path, g.footprint,
            name="GEMSDOE88-GTD88-SWCHECK", note="GTD88 shared submission_writer preflight check",
            catalogue=g.catalogue,
        )
        if not sw_receipt["validator"]["all_checks_passed"]:
            raise RuntimeError(f"Shared submission_writer validator failed: {sw_receipt['validator']}")
        lzw_tmp = tmp_dir / "portal_lzw.tif"
        portal_writer.write_portal_tif(lzw_tmp, prod_emitted, sample_path, g.footprint)
        prelim_sha = sha256_file(lzw_tmp)
        hash8 = prelim_sha[:8]

        print("[6/7] Final uniqueness gate (gate like-for-like + vendor v4 + literal v3 verbatim)...", flush=True)
        uq = gate.uniqueness_report(lzw_tmp, reg_entries, g.footprint, surface=prod_surface)
        v4_decision, v4_rows = build_v4_rows(lzw_tmp, prod_surface, reg_entries, g.footprint)
        witness_path = ROOT / "data/registry/dense_17gemdoe.tif"
        with rasterio.open(witness_path) as w_ds:
            witness_arr = w_ds.read(1)
        literal_witness_overlap = float(
            uniqueness.dot_overlap(prod_emitted, (np.isfinite(witness_arr) & (witness_arr > 0)) & g.footprint, 3)
        )
        print(
            f"      gate like-for-like unique={uq['unique_like_for_like']} worst={uq['worst_like_for_like_overlap']} "
            f"|rho|={uq['worst_abs_rho']} | vendor v4 duplicate={v4_decision['duplicate']} "
            f"worst_eff_overlap={v4_decision['worst_effective_dot_overlap']} worst|rho|={v4_decision['worst_abs_spearman']} | "
            f"literal witness={literal_witness_overlap:.4f} (v3={v4_decision['literal_v3']['verdict']})",
            flush=True,
        )

        # Frozen promotion rule (preregistration): every gate must pass.
        beats_bpwd = bool(ov_cand["dti"] > ov_bar["dti"] and delta_bpwd["ci95"][0] > 0.0)
        v4_unique = bool(not v4_decision["duplicate"] and not v4_decision["invalid_measurements"]
                         and not v4_decision["stop_required"] and uq["missing"] == 0)
        surface_pass = bool(surface_check.get("max_abs_spearman", 1.0) <= 0.90)
        sub_name = f"GEMSDOE88-GTD88-{hash8.upper()}"
        sub_note = (
            f"GTD88 tensor-dim 121ch tri-PoE novel {prod_meta['n_dots']}d; "
            f"HOLDOUT-DTI {ov_cand['dti']:.4f} far {fr_cand['dti']:.4f} blind {bl_cand['dti']:.4f}; UNSCORED"
        )
        if not (0 < len(sub_name) <= 140 and 0 < len(sub_note) <= 140):
            raise RuntimeError(f"Submission name/note length invalid: {len(sub_name)}, {len(sub_note)}")
        used_names: set[str] = set()
        for p_rc in (ROOT / "registry").glob("*.json"):
            if "gtd88" in p_rc.name:
                continue
            try:
                d = json.loads(p_rc.read_text(encoding="utf-8"))
                if isinstance(d, dict) and isinstance(d.get("submission_name"), str):
                    used_names.add(d["submission_name"])
            except Exception:
                pass
        name_unique = sub_name not in used_names

        # Saved-byte format audit must pass regardless of scientific verdict.
        stem_base = f"gems88-gtd88-tensor-dim-{prod_meta['n_dots']}-20261025-{hash8}-zeros"
        # Portal check on the temp LZW file first (bytes are final).
        portal_tmp = gate.portal_validate(lzw_tmp, sample_path, g.footprint)
        if not (portal_tmp["ok"] and portal_tmp["layout_parity_with_sample"]):
            raise RuntimeError(f"Portal format audit failed on final bytes: {portal_tmp['problems']}")

        promote = bool(
            portal_tmp["ok"] and portal_tmp["layout_parity_with_sample"]
            and canary["passed"] and scramble_ok and fp_pass and surface_pass
            and v4_unique and beats_bpwd and name_unique
        )
        stem = stem_base if promote else f"{stem_base}-DO-NOT-SUBMIT"
        dl_tif = ROOT / "docs/downloads" / f"{stem}.tif"
        dl_zip = ROOT / "docs/downloads" / f"{stem}.zip"
        sub_tif = ROOT / "submissions" / f"{stem}.tif"
        sub_zip = ROOT / "submissions" / f"{stem}.zip"
        for old in list((ROOT / "docs/downloads").glob("gems88-gtd88-*")) + list((ROOT / "submissions").glob("gems88-gtd88-*")):
            old.unlink(missing_ok=True)
        shutil.copy2(lzw_tmp, dl_tif)
        portal_writer.write_single_member_zip(dl_zip, dl_tif)
        os.chmod(dl_tif, 0o644)
        os.chmod(dl_zip, 0o644)
        shutil.copy2(dl_tif, sub_tif)
        shutil.copy2(dl_zip, sub_zip)
        os.chmod(sub_tif, 0o644)
        os.chmod(sub_zip, 0o644)

    print("[7/7] Re-opening on-disk .tif/.zip for independent multi-decoder audit...", flush=True)
    portal_tif = gate.portal_validate(dl_tif, sample_path, g.footprint)
    portal_zip = gate.portal_validate(dl_zip, sample_path, g.footprint)
    indep_audit = validate_artifact(dl_tif, sample_path)
    g57_fmt = g57gates.format_report(dl_tif, sample_path, footprint=g.footprint)
    g57_val = g57validate.validate(dl_tif, g.footprint, g.catalogue)
    g57validate.assert_submittable(g57_val)
    format_ok = bool(
        portal_tif["ok"] and portal_zip["ok"] and portal_tif["layout_parity_with_sample"]
        and indep_audit["ok"] and g57_fmt["ok"] and g57_val["all_checks_passed"]
        and portal_tif["array_sha256"] == portal_zip["array_sha256"]
    )
    if not format_ok:
        raise RuntimeError(f"Saved format audit failed: tif={portal_tif['problems']} zip={portal_zip['problems']}")
    # A format failure discovered only now would invalidate a promote decision.
    promote = bool(promote and format_ok)
    if promote != (not stem.endswith("DO-NOT-SUBMIT")):
        raise RuntimeError("Filename/verdict mismatch after saved-byte audit; refusing to publish an ambiguous label")

    tif_sha = sha256_file(dl_tif)
    zip_sha = sha256_file(dl_zip)
    elapsed = time.monotonic() - t0

    blocking: list[str] = []
    if not canary["passed"] or not scramble_ok:
        blocking.append("CANARY: leakage canary or scramble invariance failed")
    if not fp_pass:
        blocking.append(f"FINGERPRINT: share_le2={fp_prof['share_le2']:.4f}, share_gt25={fp_prof['share_gt25']:.4f} (need 0 and >=0.35)")
    if not surface_pass:
        blocking.append(f"SURFACE: pre-placement |rho|={surface_check.get('max_abs_spearman')} > 0.90 vs {surface_check.get('max_rho_label')}")
    if not v4_unique:
        blocking.append(
            f"UNIQUENESS-V4: duplicate={v4_decision['duplicate']} worst_eff_overlap={v4_decision['worst_effective_dot_overlap']} "
            f"({v4_decision['worst_effective_dot_overlap_file']}) worst|rho|={v4_decision['worst_abs_spearman']} "
            f"({v4_decision['worst_abs_spearman_file']}) invalid={v4_decision['invalid_measurements']}"
        )
    if not beats_bpwd:
        blocking.append(
            f"HOLDOUT: exp03 {ov_cand['dti']:.6f} vs BPWD-control {ov_bar['dti']:.6f}, "
            f"paired delta {delta_bpwd['delta']:+.6f} CI={delta_bpwd['ci95']} (need point>bar and CI>0)"
        )
    if not name_unique:
        blocking.append(f"NAME: {sub_name} already used")

    run_card = {
        "schema": "gems.run_card.v1",
        "run_id": f"GEMSDOE88-GTD88-20261025-{hash8}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-GTD",
        "preregistration_id": prereg["preregistration_id"],
        "hypothesis": prereg["single_method_lane"]["title"],
        "mechanism": prereg["single_method_lane"]["mechanism"],
        "named_non_fault_mimic": "; ".join(prereg["single_method_lane"]["named_non_fault_mimics"]),
        "experiments_executed": 3,
        "experiment_budget_max": 3,
        "elapsed_seconds": round(elapsed, 2),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21], "n_folds": 8,
            "withheld_positive_pixels": int(sum(r["withheld_positive_pixels"] for r in fold_rows)),
            "candidate_exp03_production_procedure": ov_cand,
            "exp01_gtd_zero_cat": ov["exp01_gtd_zero_cat"],
            "exp02_gtd_tri_poe": ov["exp02_gtd_tri_poe"],
            "control_phys44_zero_cat": ov["phys44_zero_cat"],
            "control_h88_adhr": ov["h88_adhr_incumbent"],
            "control_h88_hgvc": ov["h88_hgvc_incumbent"],
            "control_h88_bpwd_recomputed": ov_bar,
            "bpwd_stored_record": BPWD_STORED_RECORD,
            "far_gt10px_candidate": fr_cand,
            "blind_gt25px_candidate": bl_cand,
            "paired_delta_exp03_vs_bpwd_overall": delta_bpwd,
            "paired_delta_exp03_vs_bpwd_far": delta_bpwd_far,
            "paired_delta_exp03_vs_bpwd_blind": delta_bpwd_blind,
            "paired_delta_exp02_vs_bpwd_overall": exp02_delta_bpwd,
            "folds_won_exp03_vs_bpwd": folds_won,
            "beats_bpwd_with_positive_ci95": beats_bpwd,
        },
        "leakage_canary": {
            "passed": bool(canary["passed"] and scramble_ok), "threshold": 0.90,
            "features_tested": canary["features_tested"],
            "max_symmetric_auc": canary["max_symmetric_auc"], "max_feature": canary["max_feature"],
            "max_gtd14_symmetric_auc": canary["max_gtd14_symmetric_auc"],
            "scramble_invariance": bool(scramble_ok),
        },
        "uniqueness": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "binding_policy": "vendor/gems57/uniqueness.py::binding_duplicate_decision_v4 (representation-aware, IR-88-249E-01), adopted in PREREG-20261025-GTD88 under the owner's parallel-run protocol",
            "registry_rasters_checked": len(reg_entries),
            "surface_preplacement_max_abs_spearman": surface_check.get("max_abs_spearman"),
            "surface_preplacement_worst": surface_check.get("max_rho_label"),
            "v4_duplicate": v4_decision["duplicate"],
            "v4_worst_effective_dot_overlap": v4_decision["worst_effective_dot_overlap"],
            "v4_worst_effective_dot_overlap_file": v4_decision["worst_effective_dot_overlap_file"],
            "v4_worst_abs_spearman": v4_decision["worst_abs_spearman"],
            "v4_worst_abs_spearman_file": v4_decision["worst_abs_spearman_file"],
            "v4_continuous_surfaces": v4_decision["continuous_surfaces"],
            "v4_dot_emission_rasters": v4_decision["dot_emission_rasters"],
            "gate_worst_like_for_like_overlap": uq["worst_like_for_like_overlap"],
            "gate_unique_like_for_like": uq["unique_like_for_like"],
            "literal_v3_verbatim": {
                "verdict": v4_decision["literal_v3"]["verdict"],
                "worst_literal_forward_overlap": v4_decision["worst_literal_forward_overlap"],
                "worst_literal_forward_overlap_file": v4_decision["worst_literal_forward_overlap_file"],
                "dense_17gemdoe_witness_overlap": literal_witness_overlap,
                "note": "Literal >0 overlap vs continuous surfaces positive on 81-100% of footprint cells is ~1.0 for every nonempty raster including random dots; reported verbatim, not hidden. v4 binds the dot test against dot emissions / top-N surface emissions and rho against every raster.",
            },
            "unique_v4": v4_unique,
        },
        "fingerprint": fp_prof,
        "fingerprint_screen_pass": fp_pass,
        "production": {**prod_meta, "incumbent_discount_sources": inc_sources},
        "validator": {
            "format_ok_on_saved_bytes": format_ok,
            "no_nan_inside_footprint": True,
            "all_finite_entire_raster": True,
            "values_in_0_1": True,
            "values_binary_0_1": True,
            "crs_shape_transform_match_sample": bool(portal_tif["layout_parity_with_sample"]),
            "portal_tif_ok": bool(portal_tif["ok"]), "portal_zip_ok": bool(portal_zip["ok"]),
            "g57_validate_all_checks_passed": bool(g57_val["all_checks_passed"]),
            "note": "Binary {0.0,1.0} float32, nodata=None, zero outside footprint and on catalogue: the portal 'Predicted values must be in range [0, 1]' error (caused by NaN/out-of-range values in earlier files) cannot fire on these bytes. Local validity is not organizer acceptance.",
        },
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "file": str(dl_tif.relative_to(ROOT)),
        "zip_file": str(dl_zip.relative_to(ROOT)),
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "ok_to_download": True,
        "ok_to_submit": bool(promote),
        "approved_for_weekly_slot": bool(promote),
        "verdict": "promote" if promote else "negative",
        "blocking_reasons": blocking,
        "organizer_confirmed_score": None,
        "weekly_slots_used": 0,
        "slot_note": "This lane spends no slot. If verdict=promote, the file above is the single download-and-submit candidate; uploading it on the DrivenData portal is the owner's action and only the portal receipt can create an ORGANIZER-CONFIRMED score.",
    }
    write_json(ROOT / "registry/gtd88_run_card.json", run_card)
    write_json(ROOT / "docs/data/gtd88_run_card.json", run_card)
    write_json(ROOT / "registry/gtd88_gate_v4.json", {
        "schema": "gems88.gtd88.gate_v4.v1", "run_id": run_card["run_id"],
        "ok_to_download": True, "ok_to_submit": bool(promote), "verdict": run_card["verdict"],
        "blocking_reasons": blocking, "candidate": {"tif": run_card["file"], "zip": run_card["zip_file"],
                                                     "sha256": tif_sha, "zip_sha256": zip_sha, "dots": prod_meta["n_dots"]},
        "submission_name": sub_name, "submission_note": sub_note,
        "holdout_comparison": run_card["holdout_dti"], "uniqueness": run_card["uniqueness"],
        "fingerprint": fp_prof, "fingerprint_screen_pass": fp_pass,
        "leakage_canary_pass": run_card["leakage_canary"]["passed"],
        "portal_format_ok": format_ok, "weekly_slots_spent": 0, "organizer_confirmed_score": None,
    })
    write_json(ROOT / "evidence/gtd88_uniqueness_20261025.json", {
        "schema": "gems88.gtd88.uniqueness.v1", "candidate_sha256": tif_sha,
        "gate_report": {k: v for k, v in uq.items() if k != "rows"},
        "vendor_v4_decision": {k: v for k, v in v4_decision.items() if k != "rows"},
        "vendor_v4_rows": v4_decision["rows"],
        "surface_preplacement": surface_check,
    })
    receipt = {
        "schema": "gems88.gtd88.receipt.v1", "run_id": run_card["run_id"],
        "tif": run_card["file"], "zip": run_card["zip_file"], "sha256": tif_sha, "zip_sha256": zip_sha,
        "submission_name": sub_name, "submission_note": sub_note,
        "ok_to_submit": bool(promote), "verdict": run_card["verdict"], "blocking_reasons": blocking,
        "holdout_dti_evidence": "HOLDOUT-DTI (gems57-pooled-hide-v2) — see registry/gtd88_run_card.json; no organizer score exists for this file",
    }
    write_json(ROOT / "docs/downloads" / f"{stem}.json", receipt)
    write_json(ROOT / "docs/downloads" / f"{stem}.format-audit.json", {
        "portal_tif": portal_tif, "portal_zip": portal_zip, "independent": indep_audit,
        "g57_format": g57_fmt, "g57_validate": g57_val,
    })
    write_json(ROOT / "submissions" / f"{stem}.json", receipt)

    print("=" * 80)
    print(f"H88-GTD verdict: {run_card['verdict'].upper()} | ok_to_download=True ok_to_submit={promote}")
    print(f"TIFF: {run_card['file']} sha256={tif_sha}")
    print(f"Name: {sub_name} | Note ({len(sub_note)}/140): {sub_note}")
    for b in blocking:
        print(f"  BLOCK: {b}")
    print(json.dumps({k: run_card[k] for k in ("verdict", "ok_to_submit", "raster_sha256", "submission_name", "submission_note")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
