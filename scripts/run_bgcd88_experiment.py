#!/usr/bin/env python3
"""Execute the preregistered H88-BGCD experiment lane (<=3 experiments, <=2 hours).

Reuses:
  * ``vendor/gems57/evaluate_holdout.py`` (``gems57-pooled-hide-v2``, 8 buffered folds,
    seeds=(20, 21), 20 km spatial block bootstrap)
  * ``vendor/gems57/submission_writer.py`` (portal-parity zeros-outside GeoTIFF + flat ZIP)
  * ``src/gems88/gate.py`` (``gems88-gate-v3`` format, fingerprint, literal & like-for-like uniqueness)

Enforces:
  * Preregistration precedes execution (``registry/preregistration_bgcd88_20261025.json``)
  * Single-feature symmetric AUC canary <= 0.90 across all 60 features (44 PHYS + 13 BGCD + 3 VIS-SLIP)
  * Pre-placement continuous surface |Spearman rho| <= 0.90 across all pinned + live sibling rasters
  * Final discrete 3-px like-for-like overlap <= 0.70 across all sparse registry + live sibling + GEMSDOE88 rasters
  * Fail-closed literal dense-witness policy (`17GEMSDOE` overlap = 1.0 > 0.70 -> DO-NOT-SUBMIT, verdict="negative")
"""
from __future__ import annotations

# No model/feature work may precede the shared literal duplicate-stop gate.
if __name__ == "__main__":
    from pathlib import Path as _GuardPath
    import sys as _guard_sys
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
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import emit, evaluate_holdout, grid as grid_mod, holdout, submission_writer, validate  # noqa: E402
from gems88 import adhr, bgcd, edge, gate, physics  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402
from scripts.readiness import verify_template  # noqa: E402

DATE = "20261025"
CANDIDATE = "h88_bgcd"
BLOCK_SIDE = 200
BOOT_DRAWS = 1000
BOOT_SEED = 8825


def _rss_mb() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def run_60_feature_canary(
    X_phys: np.ndarray,
    X_bgcd: np.ndarray,
    g,
    folds_by_seed: list,
    sense_src: np.ndarray,
    slip_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
) -> dict:
    """Single-feature symmetric AUC canary across 44 PHYS + 13 BGCD + 3 fold-safe VIS-SLIP = 60 features."""
    ys_fp, xs_fp = np.nonzero(g.footprint)
    rng = np.random.default_rng(8825)

    vis_slip_vals = [[], [], []]
    y_vis_all = []
    fold_slices = []
    for seed, folds in folds_by_seed:
        for i, fold in enumerate(folds):
            qname = str(fold["name"])
            tag = f"seed{seed}_f{i}_{qname}"
            active = g.footprint & fold["region"] & ~fold["masked_known"]
            truth = fold["truth"] & active
            act_fp = active[ys_fp, xs_fp]
            tru_fp = truth[ys_fp, xs_fp]
            p_idx = np.flatnonzero(act_fp & tru_fp)
            n_pool = np.flatnonzero(act_fp & ~tru_fp)
            n_idx = np.sort(rng.choice(n_pool, size=min(25_000, n_pool.size), replace=False))
            sel = np.concatenate([p_idx, n_idx])
            y_sel = np.concatenate([np.ones(p_idx.size, np.int8), np.zeros(n_idx.size, np.int8)])
            fold_slices.append((sel, y_sel))

            X_vis22, _, _ = adhr.compute_visible_struct_fp(g, fold["visible"], sense_src, scarp_fields, cache_dir, tag)
            X_slip3 = bgcd.compute_visible_slip_fp(g, fold["visible"], slip_src, X_vis22, cache_dir, tag)
            for j in range(3):
                vis_slip_vals[j].append(np.asarray(X_slip3[sel, j], dtype=np.float32))
            y_vis_all.append(y_sel)
            del X_vis22, X_slip3

    all_sel = np.concatenate([s for s, _ in fold_slices])
    all_y = np.concatenate([y for _, y in fold_slices])

    rows = []
    for X_mm, names, group in (
        (X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
        (X_bgcd, list(bgcd.BGCD_BLIND_FEATURES), "BGCD-BLIND-13"),
    ):
        for j, name in enumerate(names):
            vals = np.asarray(X_mm[all_sel, j], dtype=np.float32)
            auc = 0.5 if float(np.std(vals)) < 1e-12 else float(roc_auc_score(all_y, vals))
            sym = max(auc, 1.0 - auc)
            rows.append({
                "feature": name,
                "group": group,
                "auc": round(auc, 6),
                "symmetric_auc": round(sym, 6),
                "passed": bool(sym <= 0.90),
            })

    y_v = np.concatenate(y_vis_all)
    for j, name in enumerate(bgcd.BGCD_VIS_FEATURES):
        vals = np.concatenate(vis_slip_vals[j])
        auc = 0.5 if float(np.std(vals)) < 1e-12 else float(roc_auc_score(y_v, vals))
        sym = max(auc, 1.0 - auc)
        rows.append({
            "feature": name,
            "group": "BGCD-VIS-SLIP-3",
            "auc": round(auc, 6),
            "symmetric_auc": round(sym, 6),
            "passed": bool(sym <= 0.90),
        })

    worst = max(rows, key=lambda r: r["symmetric_auc"])
    passed_all = all(r["passed"] for r in rows)
    if not passed_all:
        raise RuntimeError(f"LEAKAGE CANARY FAILED: {worst}")
    return {
        "threshold_symmetric_auc": 0.90,
        "features_tested": len(rows),
        "withheld_positive_pixels": int(all_y.sum()),
        "max_symmetric_auc": worst["symmetric_auc"],
        "max_feature": worst["feature"],
        "passed": passed_all,
        "per_feature": rows,
    }


def _evaluate_stratified_regime_diagnostic(g, folds_by_seed: list, cache_dir: Path) -> dict:
    """Measure the exact 3-regime production-parity allocator (min_spacing=3.20, share_gt25>=0.45,
    fold-scaled k_est budgets) on the cached 8-fold posteriors so zero eval-to-emit gap goes unmeasured."""
    fp = g.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    terms_ov, terms_fr, terms_bl = None, None, None
    shares_gt25 = []
    dots_per_fold = []

    for seed, folds in folds_by_seed:
        d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
        for i, fold in enumerate(folds):
            qname = str(fold["name"])
            tag = f"seed{seed}_f{i}_{qname}"
            fseed = seed * 10 + i
            cache_npz = cache_dir / f"bgcd_post_{tag}_s{fseed}_{bgcd.BGCD_SCHEMA_VERSION}.npz"
            if not cache_npz.exists():
                return {}
            post = np.load(cache_npz)
            train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
            train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
            test_region = fold["region"]
            visible = fold["visible"]
            allowed = fp & test_region & ~visible
            act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
            d_vis_act = d_vis_grid[ys_fp[act_idx], xs_fp[act_idx]]

            n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
            hid_ratio = float(train_truth.sum()) / n_vis_tr
            k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

            p_phys_poe, m_phys_poe = bgcd._adaptive_poe_pool(
                post["p_p44"], post["m_p44"], post["p_p57"], post["m_p57"], d_vis_act, w_near=0.68, w_far=0.85
            )
            p_full_poe, m_full_poe = bgcd._adaptive_poe_pool(
                post["p_f67"], post["m_f67"], post["p_f83"], post["m_f83"], d_vis_act, w_near=0.68, w_far=0.85
            )
            p_surf, m_surf = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_est, beta_phys=0.42, pi_unmapped=0.52)
            p_s_g = adhr.scatter_fp(p_surf, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            m_s_g = adhr.scatter_fp(m_surf, ys_fp[act_idx], xs_fp[act_idx], g.shape)

            sc_b = float(k_est) / max(float(p_phys_poe.sum()), 1e-6)
            p_b = np.clip(p_phys_poe * np.float32(sc_b), 0.0, 1.0).astype(np.float32)
            m_b = np.clip(m_phys_poe * np.float32(hid_ratio), p_b, 1.0).astype(np.float32)
            p_b_g = adhr.scatter_fp(p_b, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            m_b_g = adhr.scatter_fp(m_b, ys_fp[act_idx], xs_fp[act_idx], g.shape)

            emit_allow = allowed & (d_vis_grid > 2.25)
            b_tot = max(int(round(1.60 * k_est)), 600)
            b1 = int(round(0.26 * b_tot))
            b2 = int(round(0.24 * b_tot))
            b3 = b_tot - b1 - b2
            a1 = emit.dinkelbach_allocate(p_s_g, m_s_g, emit_allow & (d_vis_grid <= 10.0), budget=b1, k_truth=0.35 * k_est, min_spacing_px=3.20, dinkelbach_iters=4)
            a2 = emit.dinkelbach_allocate(0.45 * p_s_g + 0.55 * p_b_g, np.maximum(0.45 * p_s_g + 0.55 * p_b_g, 0.45 * m_s_g + 0.55 * m_b_g), emit_allow & (d_vis_grid > 10.0) & (d_vis_grid <= 25.0), budget=b2, k_truth=0.25 * k_est, min_spacing_px=3.20, dinkelbach_iters=4)
            a3 = emit.dinkelbach_allocate(p_b_g, m_b_g, emit_allow & (d_vis_grid > 25.0), budget=b3, k_truth=0.40 * k_est, min_spacing_px=3.20, dinkelbach_iters=4)
            em_bool = (a1.emitted | a2.emitted | a3.emitted) & emit_allow
            em = em_bool.astype(np.float32)
            shares_gt25.append(float((d_vis_grid[em_bool] > 25.0).mean()) if em_bool.any() else 0.0)
            dots_per_fold.append(int(em_bool.sum()))

            far_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
            far_valid = fp & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
            far_fold = {**fold, "truth": far_truth, "region": far_valid, "masked_known": np.zeros_like(far_valid)}
            blind_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
            blind_valid = fp & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
            blind_fold = {**fold, "truth": blind_truth, "region": blind_valid, "masked_known": np.zeros_like(blind_valid)}

            _, bt_ov = evaluate_holdout.evaluate(em, fold, fp, block_side=BLOCK_SIDE)
            _, bt_fr = evaluate_holdout.evaluate(em, far_fold, fp, block_side=BLOCK_SIDE)
            _, bt_bl = evaluate_holdout.evaluate(em, blind_fold, fp, block_side=BLOCK_SIDE)
            terms_ov = bt_ov if terms_ov is None else terms_ov + bt_ov
            terms_fr = bt_fr if terms_fr is None else terms_fr + bt_fr
            terms_bl = bt_bl if terms_bl is None else terms_bl + bt_bl
        del d_vis_grid

    s_ov = evaluate_holdout.pooled_summary({"strat_3regime": terms_ov}, draws=BOOT_DRAWS, seed=BOOT_SEED + 10, candidate="strat_3regime")["scores"]["strat_3regime"]
    s_fr = evaluate_holdout.pooled_summary({"strat_3regime": terms_fr}, draws=BOOT_DRAWS, seed=BOOT_SEED + 11, candidate="strat_3regime")["scores"]["strat_3regime"]
    s_bl = evaluate_holdout.pooled_summary({"strat_3regime": terms_bl}, draws=BOOT_DRAWS, seed=BOOT_SEED + 12, candidate="strat_3regime")["scores"]["strat_3regime"]
    return {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "description": "Fold-scaled 3-regime stratified allocator sensitivity (min_spacing=3.20, d_vis>2.25, ~50% share_gt25)",
        "mean_fold_dots": round(float(np.mean(dots_per_fold)), 1),
        "mean_fold_share_gt25": round(float(np.mean(shares_gt25)), 4),
        "overall": s_ov,
        "far_gt10px": s_fr,
        "blind_gt25px": s_bl,
    }


def _all_comparison_pairs(root: Path, exclude: tuple[str, ...] = ("bgcd88",)) -> tuple[list[tuple[str, Path]], list[tuple[str, Path]]]:
    """Return (pinned_registry_pairs, extended_with_live_siblings_pairs)."""
    pinned = registry_list(root, exclude=exclude)
    seen_shas = {_sha256(p) for _, p in pinned}
    extended = list(pinned)
    live_dir = root / "data/siblings_live"
    if live_dir.is_dir():
        for p in sorted(live_dir.glob("*.tif")):
            if any(x and x in p.name for x in exclude):
                continue
            s = _sha256(p)
            if s not in seen_shas:
                seen_shas.add(s)
                extended.append((f"sibling_live:{p.name}", p))
    return pinned, extended


def _subset_uniqueness_summary(full_rep: dict, allowed_labels: set[str]) -> dict:
    sub_rows = [r for r in full_rep["rows"] if r["label"] in allowed_labels and "error" not in r]
    worst = max(sub_rows, key=lambda r: r["like_for_like_overlap_3px"], default=None)
    worst_rho = max(sub_rows, key=lambda r: max(abs(r["rho_final"]), abs(r["rho_preplacement"])), default=None)
    return {
        "registry_rasters": len(sub_rows),
        "unique_like_for_like": bool(sub_rows and not any(r["blocks_like_for_like"] for r in sub_rows)),
        "unique_literal": bool(sub_rows and not any(r["blocks_literal"] for r in sub_rows)),
        "worst_like_for_like_overlap": None if worst is None else {"label": worst["label"], "value": worst["like_for_like_overlap_3px"]},
        "worst_abs_rho": None if worst_rho is None else {"label": worst_rho["label"], "value": max(abs(worst_rho["rho_final"]), abs(worst_rho["rho_preplacement"]))},
        "literal_blockers": [r["label"] for r in sub_rows if r["blocks_literal"]],
    }


def main() -> None:
    t0 = time.monotonic()
    recompute_holdout = "--recompute-holdout" in sys.argv
    verify_template(ROOT)

    prereg_path = ROOT / "registry/preregistration_bgcd88_20261025.json"
    prereg = json.loads(prereg_path.read_text())
    if not prereg.get("written_before_results"):
        raise RuntimeError("Preregistration missing or not marked written_before_results")

    g = grid_mod.load_grid(ROOT / "data/bridge")
    phys_cache = ROOT / ".cache/gems88"
    bgcd_cache = ROOT / ".cache/bgcd88"
    phys_cache.mkdir(parents=True, exist_ok=True)
    bgcd_cache.mkdir(parents=True, exist_ok=True)

    print(f"[1/6] Loading PHYS-44 + BGCD-13 memmaps (RSS={_rss_mb()} MB)...", flush=True)
    X_phys, band_tags, _ = physics.build_or_load_physics_memmap(ROOT, g, phys_cache)
    X_bgcd, bgcd_ext_hashes = bgcd.build_or_load_bgcd_blind_memmap(ROOT, g, bgcd_cache)

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)  # Band 12 det_elev (IR-88-110 fix)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, bgcd_cache)
    del det_elev
    gc.collect()

    trace_csv = ROOT / "data/external/trace_segments_utm11.csv"
    sense_src = adhr.build_sense_raster(trace_csv, g)
    slip_src = bgcd.build_slip_rate_raster(trace_csv, g, bgcd_cache)

    folds_by_seed = []
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))

    holdout_file = ROOT / "evidence/bgcd88_holdout_20261025.json"
    if holdout_file.is_file() and not recompute_holdout:
        holdout_payload = json.loads(holdout_file.read_text())
        assert holdout_payload["preregistration_id"] == prereg["preregistration_id"]
        assert len(holdout_payload["folds"]) == 8
        assert holdout_payload["canary"]["features_tested"] == 60 and holdout_payload["canary"]["passed"] is True
        canary = holdout_payload["canary"]
        pooled_overall = holdout_payload["pooled_overall"]
        pooled_far10 = holdout_payload["pooled_far_gt10px"]
        pooled_blind25 = holdout_payload["pooled_blind_gt25px"]
        print(
            f"[2-3/6] Verified cached 8-fold holdout & 60-feature canary ({holdout_file.name}, RSS={_rss_mb()} MB)",
            flush=True,
        )
    else:
        print(f"[2/6] Running 60-feature single-feature AUC leakage canary (RSS={_rss_mb()} MB)...", flush=True)
        canary = run_60_feature_canary(X_phys, X_bgcd, g, folds_by_seed, sense_src, slip_src, scarp_fields, bgcd_cache)
        print(f"      CANARY PASS: max symmetric AUC = {canary['max_symmetric_auc']:.5f} ({canary['max_feature']})", flush=True)

        print("[3/6] Running 8-fold gems57-pooled-hide-v2 holdout...", flush=True)
        arms = ("h88_adhr_b12_ctrl", "bgcd_blind_phys57", "bgcd_slip_joint83", CANDIDATE)
        terms_overall = {a: None for a in arms}
        terms_far10 = {a: None for a in arms}
        terms_blind25 = {a: None for a in arms}
        fold_rows = []
        for seed, folds in folds_by_seed:
            d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
            for i, fold in enumerate(folds):
                qname = str(fold["name"])
                tag = f"seed{seed}_f{i}_{qname}"
                train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
                train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
                test_region = fold["region"]
                X_vis22, d_vis_fp, comp_len_fp = adhr.compute_visible_struct_fp(g, fold["visible"], sense_src, scarp_fields, bgcd_cache, tag)
                X_slip3 = bgcd.compute_visible_slip_fp(g, fold["visible"], slip_src, X_vis22, bgcd_cache, tag)
                res = bgcd.evaluate_bgcd_fold_arms(
                    g, X_phys, X_bgcd, X_vis22, X_slip3, d_vis_fp, comp_len_fp,
                    fold["visible"], train_regions, train_truth, test_region,
                    seed=seed * 10 + i, cache_dir=bgcd_cache, fold_tag=tag,
                )
                del X_vis22, X_slip3
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
            del d_vis_grid
            gc.collect()
        pooled_overall = evaluate_holdout.pooled_summary(terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=CANDIDATE)
        pooled_far10 = evaluate_holdout.pooled_summary(terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=CANDIDATE)
        pooled_blind25 = evaluate_holdout.pooled_summary(terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=CANDIDATE)
        holdout_payload = {
            "schema_version": "gems88-bgcd88-holdout-v1",
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "preregistration_id": prereg["preregistration_id"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21], "n_folds": 8, "bootstrap_draws": BOOT_DRAWS,
            "spatial_block_m": BLOCK_SIDE * 100.0,
            "whole_segments": True, "buffered": True, "visible_only_features": True, "pixel_exact_mask": True,
            "canary": canary,
            "pooled_overall": pooled_overall, "pooled_far_gt10px": pooled_far10, "pooled_blind_gt25px": pooled_blind25,
            "folds": fold_rows, "elapsed_seconds": round(time.monotonic() - t0, 2),
        }

    print(f"[3b/6] Measuring 8-fold 3-regime production-parity sensitivity diagnostic (RSS={_rss_mb()} MB)...", flush=True)
    strat_diag = _evaluate_stratified_regime_diagnostic(g, folds_by_seed, bgcd_cache)
    holdout_payload["stratified_3regime_sensitivity"] = strat_diag
    for p in (ROOT / "evidence/bgcd88_holdout_20261025.json", ROOT / "docs/evidence/bgcd88_holdout_20261025.json"):
        _write_json(p, holdout_payload)
    if strat_diag:
        print(
            f"       3-regime stratified diag: overall={strat_diag['overall']['dti']:.6f} "
            f"far={strat_diag['far_gt10px']['dti']:.6f} blind={strat_diag['blind_gt25px']['dti']:.6f} "
            f"(mean share_gt25={strat_diag['mean_fold_share_gt25']:.4f})",
            flush=True,
        )

    ov = pooled_overall["scores"][CANDIDATE]
    fr = pooled_far10["scores"][CANDIDATE]
    bl = pooled_blind25["scores"][CANDIDATE]
    paired_ctrl = pooled_overall["paired_differences"]["h88_adhr_b12_ctrl"]

    print(f"[4/6] Fitting production H88-BGCD + 3-regime ridge allocation (RSS={_rss_mb()} MB)...", flush=True)
    prod_emitted, prod_surface, prod_meta = bgcd.fit_and_emit_production_bgcd(
        g, X_phys, X_bgcd, sense_src, slip_src, scarp_fields, bgcd_cache, seed=8825
    )
    print(f"      Production emitted: {prod_meta} (RSS={_rss_mb()} MB)", flush=True)

    sub_name = "GEMSDOE88-BGCD88-HYDRO-SLIP-20261025"
    sub_note = (
        f"H88-BGCD blind geotherm diseq+slip PoE ({prod_meta['n_dots']}d); "
        f"HOLDOUT-DTI {ov['dti']:.4f} far {fr['dti']:.4f} blind {bl['dti']:.4f}; UNSCORED"
    )
    assert 1 <= len(sub_name) <= 140 and 1 <= len(sub_note) <= 140, (len(sub_name), len(sub_note))

    prov_stem = f"gems88-bgcd88-hydro-slip-{prod_meta['n_dots']}d-{DATE}-zeros"
    prov_tif = ROOT / "docs/downloads" / f"{prov_stem}.tif"
    for ext in (".tif", ".zip", ".json"):
        prov_tif.with_suffix(ext).unlink(missing_ok=True)
    submission_writer.write_submission(
        prov_tif, prod_emitted, ROOT / "data/bridge/sample_submission.tif", g.footprint,
        note=sub_note, name=sub_name, catalogue=g.catalogue,
        metadata={
            "lane": "H88-BGCD",
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "holdout_dti_overall": ov["dti"],
            "holdout_dti_far_gt10px": fr["dti"],
            "holdout_dti_blind_gt25px": bl["dti"],
            "organizer_confirmed_score": None,
        },
    )

    pinned_pairs, extended_pairs = _all_comparison_pairs(ROOT, exclude=("bgcd88",))
    print(
        f"[5/6] Auditing single-pass pre-placement surface & final dots vs {len(pinned_pairs)} pinned "
        f"+ {len(extended_pairs) - len(pinned_pairs)} live HEAD sibling = {len(extended_pairs)} rasters...",
        flush=True,
    )
    d_cat_grid = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_profile = gate.fingerprint(prod_emitted > 0, d_cat_grid)
    fp_ok = gate.fingerprint_screen(fp_profile)
    portal_rep = gate.portal_validate(prov_tif, ROOT / "data/bridge/sample_submission.tif", g.footprint)
    uniq_extended = gate.uniqueness_report(prov_tif, extended_pairs, g.footprint, surface=prod_surface)
    pinned_labels = {lbl for lbl, _ in pinned_pairs}
    uniq_pinned = _subset_uniqueness_summary(uniq_extended, pinned_labels)

    max_surface_rho = max(
        abs(float(r["rho_preplacement"]))
        for r in uniq_extended["rows"]
        if "error" not in r and r.get("rho_preplacement") is not None
    )
    print(f"      Pre-placement surface max |Spearman rho| = {max_surface_rho:.6f} (limit 0.90)", flush=True)
    if max_surface_rho > 0.90:
        raise RuntimeError(f"STOP duplicate: pre-placement surface |rho| {max_surface_rho:.4f} > 0.90")

    print(
        f"      Pinned ({uniq_pinned['registry_rasters']}) worst like-for-like 3px overlap = "
        f"{uniq_pinned['worst_like_for_like_overlap']['value']:.5f} "
        f"({uniq_pinned['worst_like_for_like_overlap']['label']})",
        flush=True,
    )
    print(
        f"      Extended w/ live HEAD siblings ({uniq_extended['registry_rasters']}) worst like-for-like 3px overlap = "
        f"{uniq_extended['worst_like_for_like_overlap']['value']:.5f} "
        f"({uniq_extended['worst_like_for_like_overlap']['label']}), "
        f"worst |rho| = {uniq_extended['worst_abs_rho']['value']:.5f}",
        flush=True,
    )

    beats_adhr_stored = bool(ov["dti"] > 0.189634)
    beats_vess_bar = bool(ov["dti"] > 0.200941 and paired_ctrl["ci95"][0] > 0 and fp_ok)
    gv = gate.decide(
        portal=portal_rep,
        uniqueness=uniq_extended,
        canary_passed=bool(canary["passed"]),
        holdout_beats_bar=beats_vess_bar,
        name=sub_name,
        note=sub_note,
        used_names=[],
        receipt_sha_matches=True,
    )
    literal_block = not uniq_extended["unique_literal"]
    ok_submit_final = bool(gv["ok_to_submit"] and not literal_block)
    gv["ok_to_submit"] = ok_submit_final
    if literal_block:
        gv["blocking_reasons"] = list(gv.get("blocking_reasons", [])) + [
            "UNIQUENESS (literal rule): forward 3px overlap vs dense/full-footprint registry raster(s): "
            + ", ".join(uniq_extended["literal_blockers"][:4])
        ]
    gv["label"] = "OK TO DOWNLOAD - OK TO SUBMIT" if ok_submit_final else "OK TO DOWNLOAD - NOT OK TO SUBMIT"
    gv["fingerprint"] = fp_profile
    gv["fingerprint_screen_passed"] = fp_ok
    gv["uniqueness_summary"] = {
        "pinned_registry_rasters": uniq_pinned["registry_rasters"],
        "extended_registry_rasters": uniq_extended["registry_rasters"],
        "worst_like_for_like_overlap_pinned": uniq_pinned["worst_like_for_like_overlap"],
        "worst_like_for_like_overlap_extended": uniq_extended["worst_like_for_like_overlap"],
        "worst_abs_rho_extended": uniq_extended["worst_abs_rho"],
        "unique_like_for_like_pinned": uniq_pinned["unique_like_for_like"],
        "unique_like_for_like_extended": uniq_extended["unique_like_for_like"],
        "unique_literal": uniq_extended["unique_literal"],
    }
    gv["paired_delta_vs_adhr_b12_ctrl"] = paired_ctrl
    gv["beats_adhr_stored_bar"] = beats_adhr_stored
    gv["beats_vess_stored_bar"] = beats_vess_bar

    suffix = "GATE-PASS" if ok_submit_final else "DO-NOT-SUBMIT"
    final_stem = f"{prov_stem}-{suffix}"
    final_tif = ROOT / "docs/downloads" / f"{final_stem}.tif"
    final_zip = ROOT / "docs/downloads" / f"{final_stem}.zip"
    for ext in (".tif", ".zip", ".json"):
        prov_tif.with_suffix(ext).unlink(missing_ok=True)
        final_tif.with_suffix(ext).unlink(missing_ok=True)

    submission_writer.write_submission(
        final_tif, prod_emitted, ROOT / "data/bridge/sample_submission.tif", g.footprint,
        note=sub_note, name=sub_name, catalogue=g.catalogue,
        metadata={
            "lane": "H88-BGCD",
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "holdout_dti_overall": ov["dti"],
            "holdout_dti_far_gt10px": fr["dti"],
            "holdout_dti_blind_gt25px": bl["dti"],
            "organizer_confirmed_score": None,
            "gate_policy": gate.POLICY_VERSION,
            "ok_to_download": gv["ok_to_download"],
            "ok_to_submit": ok_submit_final,
        },
    )
    local_val = validate.validate(final_tif, g.footprint, g.catalogue)
    portal_final = gate.portal_validate(final_tif, ROOT / "data/bridge/sample_submission.tif", g.footprint)
    for p in (final_tif, final_zip, final_tif.with_suffix(".json")):
        if p.exists():
            os.chmod(p, 0o644)
    sub_dir = ROOT / "submissions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_tif, sub_dir / final_tif.name)
    shutil.copy2(final_zip, sub_dir / final_zip.name)

    print(f"[6/6] Writing run card, gate verdict & uniqueness evidence (RSS={_rss_mb()} MB)...", flush=True)
    uniqueness_payload = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_placement_surface": {
            "max_abs_spearman_rho": round(max_surface_rho, 6),
            "threshold": 0.90,
            "rasters_checked": len(extended_pairs),
            "passed": bool(max_surface_rho <= 0.90),
        },
        "post_placement_dots_pinned": uniq_pinned,
        "post_placement_dots_extended_live_siblings": {
            "registry_rasters": uniq_extended["registry_rasters"],
            "distinct_dot_sets": uniq_extended["distinct_dot_sets"],
            "missing": uniq_extended["missing"],
            "unique_like_for_like": uniq_extended["unique_like_for_like"],
            "unique_literal": uniq_extended["unique_literal"],
            "worst_like_for_like_overlap": uniq_extended["worst_like_for_like_overlap"],
            "worst_abs_rho": uniq_extended["worst_abs_rho"],
            "literal_blockers": uniq_extended["literal_blockers"],
            "like_for_like_blockers": uniq_extended["like_for_like_blockers"],
            "vacuity_witness": uniq_extended["vacuity_witness"],
            "top20_by_like_for_like_overlap": sorted(
                [
                    {
                        "label": r["label"],
                        "registry_dots": r["registry_dots"],
                        "like_for_like_overlap_3px": round(float(r["like_for_like_overlap_3px"]), 6),
                        "literal_overlap_3px": round(float(r["literal_overlap_3px"]), 6),
                        "rho_preplacement": round(float(r["rho_preplacement"]), 6),
                        "rho_final": round(float(r["rho_final"]), 6),
                    }
                    for r in uniq_extended["rows"]
                    if "error" not in r and "duplicate_of" not in r
                ],
                key=lambda x: x["like_for_like_overlap_3px"],
                reverse=True,
            )[:20],
        },
        "fingerprint": fp_profile,
        "fingerprint_screen_passed": fp_ok,
    }
    for p in (ROOT / "evidence/bgcd88_uniqueness_20261025.json", ROOT / "docs/evidence/bgcd88_uniqueness_20261025.json"):
        _write_json(p, uniqueness_payload)

    verdict = "promote" if ok_submit_final else "negative"
    total_elapsed = round(float(holdout_payload.get("elapsed_seconds", 0.0)) + (time.monotonic() - t0), 2)
    run_card = {
        "schema": "gems88.bgcd88.run_card.v1",
        "run_id": f"GEMSDOE88-BGCD88-{DATE}-{_sha256(final_tif)[:8]}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration_id": prereg["preregistration_id"],
        "lane": "H88-BGCD",
        "hypothesis": prereg["title"],
        "mechanism": prereg["physical_mechanism"],
        "named_non_fault_mimic": prereg["named_non_fault_mimics"],
        "experiments_executed": 3,
        "experiment_budget_max": 3,
        "elapsed_seconds": total_elapsed,
        "peak_rss_mb": _rss_mb(),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21],
            "n_folds": 8,
            "withheld_positive_pixels_overall": ov["withheld_positive_pixels"],
            "withheld_positive_pixels_far_gt10px": fr["withheld_positive_pixels"],
            "withheld_positive_pixels_blind_gt25px": bl["withheld_positive_pixels"],
            "overall": ov,
            "far_gt10px": fr,
            "blind_gt25px": bl,
            "paired_delta_vs_adhr_b12_ctrl": paired_ctrl,
            "paired_delta_far_gt10px_vs_ctrl": pooled_far10["paired_differences"]["h88_adhr_b12_ctrl"],
            "paired_delta_blind_gt25px_vs_ctrl": pooled_blind25["paired_differences"]["h88_adhr_b12_ctrl"],
            "stratified_3regime_sensitivity": strat_diag,
            "experiments": {
                "Control_h88_adhr_b12_ctrl": {
                    "overall": pooled_overall["scores"]["h88_adhr_b12_ctrl"],
                    "far_gt10px": pooled_far10["scores"]["h88_adhr_b12_ctrl"],
                    "blind_gt25px": pooled_blind25["scores"]["h88_adhr_b12_ctrl"],
                },
                "Exp01_bgcd_blind_phys57": {
                    "overall": pooled_overall["scores"]["bgcd_blind_phys57"],
                    "far_gt10px": pooled_far10["scores"]["bgcd_blind_phys57"],
                    "blind_gt25px": pooled_blind25["scores"]["bgcd_blind_phys57"],
                },
                "Exp02_bgcd_slip_joint83": {
                    "overall": pooled_overall["scores"]["bgcd_slip_joint83"],
                    "far_gt10px": pooled_far10["scores"]["bgcd_slip_joint83"],
                    "blind_gt25px": pooled_blind25["scores"]["bgcd_slip_joint83"],
                },
                "Exp03_h88_bgcd_primary": {
                    "overall": ov,
                    "far_gt10px": fr,
                    "blind_gt25px": bl,
                },
            },
        },
        "leakage_canary": {
            "passed": canary["passed"],
            "threshold_symmetric_auc": canary["threshold_symmetric_auc"],
            "features_tested": canary["features_tested"],
            "withheld_positive_pixels": canary["withheld_positive_pixels"],
            "max_symmetric_auc": canary["max_symmetric_auc"],
            "max_feature": canary["max_feature"],
        },
        "correlation_overlap_vs_registry": {
            "surface_preplacement_max_abs_spearman": round(max_surface_rho, 6),
            "pinned_registry_rasters_checked": uniq_pinned["registry_rasters"],
            "extended_live_sibling_rasters_checked": uniq_extended["registry_rasters"],
            "final_worst_like_for_like_overlap_3px_pinned": uniq_pinned["worst_like_for_like_overlap"],
            "final_worst_like_for_like_overlap_3px_extended": uniq_extended["worst_like_for_like_overlap"],
            "final_worst_abs_rho_extended": uniq_extended["worst_abs_rho"],
            "unique_like_for_like_pinned": uniq_pinned["unique_like_for_like"],
            "unique_like_for_like_extended": uniq_extended["unique_like_for_like"],
            "unique_literal": uniq_extended["unique_literal"],
            "literal_blockers": uniq_extended["literal_blockers"],
        },
        "validator_output": {
            "all_checks_passed": local_val["all_checks_passed"],
            "portal_ok": portal_final["ok"],
            "second_decoder": portal_final["second_decoder"],
            "no_nan_inside": local_val["checks"]["in_footprint_all_finite"],
            "no_nan_anywhere": local_val["checks"]["no_nan_anywhere"],
            "values_in_0_1": local_val["checks"]["range_0_1_guaranteed"],
            "portal_range_check_nan_strict": portal_final["checks"]["portal_range_check_nan_strict"],
            "crs_match": portal_final["checks"]["crs_epsg_32611"],
            "shape_match": portal_final["checks"]["shape_matches_sample"],
            "transform_match": portal_final["checks"]["transform_matches_sample"],
            "zero_outside_footprint": portal_final["checks"]["outside_footprint_zero"],
            "catalogue_masked_zero": local_val["checks"]["zero_dots_on_mapped_catalogue"],
            "raster_sha256": _sha256(final_tif),
        },
        "raster_sha256": _sha256(final_tif),
        "zip_sha256": _sha256(final_zip),
        "submission": {
            "file": f"docs/downloads/{final_tif.name}",
            "zip_file": f"docs/downloads/{final_zip.name}",
            "submission_name": sub_name,
            "submission_note": sub_note,
            "submission_note_chars": len(sub_note),
            "positive_pixels": int(prod_meta["n_dots"]),
            "regime_counts": {
                "tip_relay_le10px": prod_meta["n_regime1_tip_relay_le10px"],
                "piedmont_10_25px": prod_meta["n_regime2_piedmont_10_25px"],
                "blind_basin_gt25px": prod_meta["n_regime3_blind_basin_gt25px"],
            },
            "share_le2": fp_profile["share_le2"],
            "share_gt10": fp_profile["share_gt10"],
            "share_gt25": fp_profile["share_gt25"],
            "median_d_cat_px": fp_profile["median_d_cat_px"],
            "min_d_cat_px": prod_meta["min_d_cat_px"],
            "min_spacing_px": prod_meta["min_spacing_px"],
        },
        "ok_to_download": bool(gv["ok_to_download"]),
        "ok_to_submit": ok_submit_final,
        "gate_verdict": gv,
        "verdict": verdict,
        "organizer_confirmed_score": None,
        "weekly_slots_used": 0,
        "band_tags_verified": band_tags,
        "external_sha256_verified": bgcd_ext_hashes,
    }
    for p in (ROOT / "registry/bgcd88_run_card.json", ROOT / "docs/data/bgcd88_run_card.json"):
        _write_json(p, run_card)

    gv_out = dict(gv)
    gv_out.update({
        "name": final_stem,
        "file": f"docs/downloads/{final_tif.name}",
        "zip_file": f"docs/downloads/{final_zip.name}",
        "sha256": run_card["raster_sha256"],
        "zip_sha256": run_card["zip_sha256"],
        "candidate": {
            "tif": f"docs/downloads/{final_tif.name}",
            "zip": f"docs/downloads/{final_zip.name}",
            "tif_sha256": run_card["raster_sha256"],
            "zip_sha256": run_card["zip_sha256"],
        },
    })
    for p in (ROOT / "registry/bgcd88_gate_verdict.json", ROOT / "docs/data/bgcd88_gate_verdict.json"):
        _write_json(p, gv_out)

    print(
        json.dumps(
            {
                "candidate": CANDIDATE,
                "holdout_dti_overall": ov["dti"],
                "holdout_ci95_overall": ov["ci95"],
                "holdout_dti_far_gt10px": fr["dti"],
                "holdout_dti_blind_gt25px": bl["dti"],
                "paired_delta_vs_ctrl": paired_ctrl,
                "dots": prod_meta["n_dots"],
                "share_gt25": fp_profile["share_gt25"],
                "worst_like_for_like_overlap_3px_pinned": uniq_pinned["worst_like_for_like_overlap"],
                "worst_like_for_like_overlap_3px_extended": uniq_extended["worst_like_for_like_overlap"],
                "file": str(final_tif),
                "sha256": run_card["raster_sha256"],
                "ok_to_download": gv["ok_to_download"],
                "ok_to_submit": ok_submit_final,
                "verdict": verdict,
                "elapsed_seconds": total_elapsed,
                "peak_rss_mb": _rss_mb(),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
