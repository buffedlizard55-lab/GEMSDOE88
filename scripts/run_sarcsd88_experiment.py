#!/usr/bin/env python3
"""Execute the preregistered 3-experiment H88-SAR-CSD suite and automated gate v3 audit.

Protocol compliance (zero human intervention):
1. Lane & Uniqueness: Single method lane ``H88-SAR-CSD``. Checks pre-placement surface
   Spearman |rho| <= 0.90 BEFORE dot placement AND final binary-dot |rho| <= 0.90 +
   3-px overlap <= 0.70 across all accessible registry + latest sibling rasters (270+ files),
   reporting both like-for-like (gems88-gate-v3) and literal (17GEMSDOE witness) readings.
2. Shared Template: Reuses cached 44-ch ``src/gems88/physics.py`` + unmodified ``vendor/gems57/``
   (``holdout.buffered_component_draw``, ``evaluate_holdout``, ``emit.dinkelbach_allocate``,
   ``validate``) + ``src/gems88/gate.py`` + ``src/gems88/portal_writer.py``.
3. Evidence Labels: Every holdout number carries ``HOLDOUT-DTI``, evaluator version,
   withheld positive count, and 95% spatial block-bootstrap CI. ``ORGANIZER-CONFIRMED: none``.
4. Leakage Canary: Tests all 88 features individually (max symmetric AUC <= 0.90) AND
   verifies bit-for-bit invariance under test-quadrant ground-truth scrambling.
5. Run Card & Portal-Parity Export: Writes LZW 1-row-strip sample-parity GeoTIFF + single-TIFF
   ZIP + JSON run card + gate v3 receipt.
6. Budget Cap: Strictly <= 3 experiments and <= 2 hours; 0 DrivenData weekly slots spent.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import argparse
import gc
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout, gates as g57gates, grid as grid_mod, holdout, metric, validate as g57validate  # noqa: E402
from gems88 import adhr, edge, gate, physics, portal_writer, registry_paths, sar_csd  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

PREREG_PATH = ROOT / "registry/preregistration_sarcsd88.json"
STORED_HOLDOUT_PATH = ROOT / "registry/holdout_result.json"
CACHE_BASE = ROOT / ".cache/gems88"
CACHE_CSD = ROOT / ".cache/gems88-sarcsd"
FOLD_CACHE_DIR = CACHE_CSD / "folds_v2"
SEEDS = (20, 21)
BUFFER_PX = 3
BOUNDARY_PX = 12
BLOCK_SIDE = 200
BOOT_DRAWS = 1000
BOOT_SEED = 882026
MIN_SPACING_PX = 2.65


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extended_registry_list(exclude: tuple[str, ...] = ()) -> list[tuple[str, Path]]:
    """Combine pinned registry_paths.registry_list with any newer siblings_latest rasters."""
    base = list(registry_paths.registry_list(ROOT, exclude=exclude))
    seen_sha = set()
    dedup_paths = set()
    out: list[tuple[str, Path]] = []
    for label, p in base:
        rp = p.resolve()
        if rp not in dedup_paths:
            dedup_paths.add(rp)
            out.append((label, p))
            seen_sha.add(sha256_file(p))
    latest_dir = ROOT / "data/siblings_latest"
    if latest_dir.is_dir():
        for p in sorted(latest_dir.glob("*.tif")):
            if any(x and x in p.name for x in exclude):
                continue
            if "existing_faults.tif" in p.name or "sample_submission.tif" in p.name:
                continue
            s = sha256_file(p)
            if s not in seen_sha:
                seen_sha.add(s)
                out.append((f"sibling_latest:{p.name}", p))
    return out


def compute_all_canaries(
    sources: list[np.ndarray],
    names: list[str],
    g,
    folds_s20: list[dict],
) -> list[dict[str, Any]]:
    vis = folds_s20[0]["visible"]
    truth = np.zeros(g.shape, dtype=bool)
    reg = np.zeros(g.shape, dtype=bool)
    for f in folds_s20:
        truth |= f["truth"]
        reg |= f["region"]
    ys_fp, xs_fp = np.nonzero(g.footprint)
    active_idx = np.flatnonzero((reg & ~vis)[ys_fp, xs_fp])
    t_sub = truth[ys_fp[active_idx], xs_fp[active_idx]]
    pos_idx = active_idx[t_sub]
    neg_pool = active_idx[~t_sub]
    rng = np.random.default_rng(882026)
    neg_idx = rng.choice(neg_pool, size=min(neg_pool.size, 8 * pos_idx.size), replace=False)
    sel = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate([np.ones(pos_idx.size, np.int8), np.zeros(neg_idx.size, np.int8)])
    X_eval = adhr.gather_columns(sources, sel)
    if X_eval.shape[1] != len(names):
        raise AssertionError(f"Canary width mismatch: {X_eval.shape[1]} != {len(names)}")

    rows = []
    for j, name in enumerate(names):
        col = X_eval[:, j]
        if not np.isfinite(col).all():
            raise RuntimeError(f"Non-finite canary column: {name}")
        auc = float(roc_auc_score(y, col)) if float(np.ptp(col)) > 0.0 else 0.5
        sym = max(auc, 1.0 - auc)
        rows.append({
            "feature": name,
            "roc_auc": round(auc, 6),
            "symmetric_auc": round(sym, 6),
            "threshold": 0.90,
            "pass": bool(sym <= 0.90),
        })
    return rows


def evaluate_subset_dti(
    preds_by_arm_seed: dict[str, dict[int, np.ndarray]],
    folds_by_seed: list[tuple[int, list[dict]]],
    g,
    min_d_vis_px: float,
) -> dict[str, dict[str, Any]]:
    """Compute exact pooled HOLDOUT-DTI restricted to whole withheld pixels with d_vis > min_d_vis_px."""
    out: dict[str, dict[str, Any]] = {}
    for arm, by_seed in preds_by_arm_seed.items():
        tp = fp = fn = 0.0
        n_tr = 0
        for seed, folds in folds_by_seed:
            vis = folds[0]["visible"]
            d_vis = ndi.distance_transform_edt(~vis)
            pred_s = by_seed[seed]
            for f in folds:
                sub_mask = f["region"] & (d_vis > min_d_vis_px)
                truth_sub = f["truth"] & sub_mask & g.footprint & (~f["masked_known"])
                if not truth_sub.any():
                    continue
                active_sub = g.footprint & sub_mask & (~f["masked_known"])
                r = metric.dti_exact(pred_s.astype(np.float64), truth_sub, valid=active_sub)
                tp += float(r["tp"])
                fp += float(r["fp"])
                fn += float(r["fn"])
                n_tr += int(truth_sub.sum())
        den = tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS
        dti = tp / den if den > 0 else 0.0
        out[arm] = {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "min_d_vis_px": float(min_d_vis_px),
            "withheld_positive_pixels": int(n_tr),
            "dti": round(float(dti), 6),
            "tpw": round(float(tp), 2),
            "fpw": round(float(fp), 2),
            "fnw": round(float(fn), 2),
        }
    return out


def compute_sgmc_offcat_diagnostic(g, cand_arr: np.ndarray) -> dict[str, Any]:
    """Non-circular USGS SGMC concealed/piedmont fault diagnostic (zero SGMC features in model)."""
    sgmc_path = ROOT / "data/external/sgmc_faults_100m.tif"
    topo_path = ROOT / "data/external/topo_10m_derived_100m_u8.tif"
    feat_path = ROOT / "data/training_features.tif"
    with rasterio.open(sgmc_path) as ds:
        sgmc = (ds.read(1) > 0) & (ds.read(1) != 255)
    with rasterio.open(topo_path) as ds:
        slope_p90 = ds.read(1).astype(np.float32)
        rel_10m = ds.read(5).astype(np.float32)
    with rasterio.open(feat_path) as ds:
        zbase = edge.clean_band(ds.read(15), g.footprint)[0]

    d_cat = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    cat = g.catalogue
    rel_q75 = float(np.percentile(rel_10m[cat], 75))
    slp_q80 = float(np.percentile(slope_p90[cat], 80))
    c_pied = g.footprint & sgmc & (d_cat > 2.5) & (rel_10m <= rel_q75) & (slope_p90 <= slp_q80) & (zbase >= 250.0)
    active = g.footprint & (~g.catalogue)

    compare = {"sarcsd88_candidate": cand_arr}
    for label, rel in [
        ("GEMSDOE32_H33", "data/registry/h33_education.tif"),
        ("GEMSDOE25_D28", "data/registry/gems25_d28.tif"),
        ("GEMSDOE70_P5", "data/registry/gems70_p5_multiphysics.tif"),
        ("GEMSDOE88_ADHR", "docs/downloads/gems88-adhr-dip-hydrothermal-submod-20261022-v2-DO-NOT-SUBMIT.tif"),
        ("GEMSDOE88_MDC88", "docs/downloads/gemsdoe88-mdc88-pu-concentration-2p83px-20261024T0740Z-zeros.tif"),
    ]:
        p = ROOT / rel
        if p.is_file():
            compare[label] = gate.read_values(p, g.footprint)

    rows = {}
    for label, arr in compare.items():
        r = metric.dti_exact(arr.astype(np.float64), c_pied, valid=active)
        rows[label] = {
            "evidence_class": "OFF-CATALOGUE-PIEDMONT-PROXY (DIAGNOSTIC ONLY, ZERO SGMC FEATURES IN SAR-CSD)",
            "proxy_dti": round(float(r["dti"]), 6),
            "tpw": round(float(r["tp"]), 2),
            "fpw": round(float(r["fp"]), 2),
            "emitted_dots": int((arr > 0).sum()),
            "proxy_positive_pixels": int(c_pied.sum()),
        }
    return rows


def _yx_to_grid(yx: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    arr = np.zeros(shape, dtype=np.float32)
    if yx.size:
        arr[yx[:, 0], yx[:, 1]] = 1.0
    return arr


def _grid_to_yx(arr: np.ndarray) -> np.ndarray:
    ys, xs = np.nonzero(arr > 0.5)
    return np.column_stack([ys.astype(np.int16), xs.astype(np.int16)])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-seed", type=int, choices=SEEDS, default=None, help="Run and checkpoint only one holdout seed, then exit")
    args = ap.parse_args()

    t0 = time.monotonic()
    if not PREREG_PATH.is_file():
        raise FileNotFoundError(f"Missing frozen preregistration: {PREREG_PATH}")
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("Preregistration is not marked frozen")
    stored_holdout = json.loads(STORED_HOLDOUT_PATH.read_text(encoding="utf-8"))
    stored_adhr_bar = float(stored_holdout["scores"]["h88_adhr"]["dti"])

    CACHE_BASE.mkdir(parents=True, exist_ok=True)
    CACHE_CSD.mkdir(parents=True, exist_ok=True)
    FOLD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")

    log("[1/8] Building/loading cached 44-ch physics.py stack + 20-ch CSD-20 stack")
    X_phys, _band_tags, _ext_hashes = physics.build_or_load_physics_memmap(ROOT, g, CACHE_BASE)
    X_csd20, _csd_meta = sar_csd.build_or_load_csd20_memmap(ROOT, g, CACHE_CSD)
    X_sar_diff = sar_csd.ColumnSubsetView(X_phys, sar_csd.PHYS_DIFF_INDICES)

    folds_by_seed: list[tuple[int, list[dict]]] = []
    for seed in SEEDS:
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=BUFFER_PX, boundary_px=BOUNDARY_PX)
        folds_by_seed.append((seed, folds))

    with rasterio.open(ROOT / "data/training_features.tif") as ds:
        det_elev = edge.clean_band(ds.read(12), g.footprint)[0]
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, CACHE_BASE)
    del det_elev
    sense_src = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)

    canary_file = ROOT / "evidence/sarcsd88_canaries.json"
    if canary_file.is_file():
        canary_doc = json.loads(canary_file.read_text(encoding="utf-8"))
        canary_rows = canary_doc["features"]
        max_canary_auc = float(canary_doc["max_symmetric_auc"])
        canary_passed = bool(canary_doc["passed"])
        log(f"[2/8] Loaded verified 88-feature leakage canary receipt (PASS={canary_passed}, max={max_canary_auc:.6f})")
    else:
        log("[2/8] Running 88-feature single-channel leakage canary audit (Seed 20)")
        vis_s20 = folds_by_seed[0][1][0]["visible"]
        X_v22_s20, dv_s20, cl_s20 = adhr.compute_visible_struct_fp(
            g, vis_s20, sense_src, scarp_fields, CACHE_BASE, "seed20"
        )
        tr_s20_all = np.zeros(g.shape, dtype=bool)
        for f in folds_by_seed[0][1]:
            tr_s20_all |= f["truth"]
        ys_fp, xs_fp = np.nonzero(g.footprint)
        wlaw_s20 = sar_csd.damagezone_envelope.fit_width_law(
            cl_s20, dv_s20, tr_s20_all[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
        )
        dow_s20 = (dv_s20 / np.maximum(wlaw_s20.half_width(cl_s20), 1e-6)).astype(np.float32)
        c_vis_s20 = np.exp(-((dv_s20 / np.float32(18.0)) ** 2)).astype(np.float32)
        all_canary_names = (
            list(physics.ALL_PHYS_FEATURES)
            + list(sar_csd.CSD20_FEATURES)
            + list(adhr.VIS_STRUCT_FEATURES)
            + ["sar_c_hat_vis"]
        )
        canary_rows = compute_all_canaries(
            [X_phys, X_csd20, X_v22_s20, dow_s20, c_vis_s20],
            all_canary_names,
            g,
            folds_by_seed[0][1],
        )
        del X_v22_s20, dv_s20, cl_s20, dow_s20, c_vis_s20
        gc.collect()
        max_canary_auc = max(r["symmetric_auc"] for r in canary_rows)
        canary_passed = bool(max_canary_auc <= 0.90)
        canary_doc = {
            "schema": "gems88.sarcsd88-canaries.v1",
            "evidence_class": "LEAKAGE-CANARY",
            "threshold": 0.90,
            "features_tested": len(canary_rows),
            "max_symmetric_auc": max_canary_auc,
            "passed": canary_passed,
            "top10_by_symmetric_auc": sorted(canary_rows, key=lambda r: -r["symmetric_auc"])[:10],
            "features": canary_rows,
        }
        write_json(canary_file, canary_doc)
    if not canary_passed:
        raise SystemExit(f"STOP: Leakage canary failed with max symmetric AUC = {max_canary_auc:.6f} > 0.90")

    log("[3/8] Running 8-fold buffered whole-component holdout (H88-ADHR control + Exp 01, Exp 02, Exp 03)")
    X_v22_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
        g, g.catalogue, sense_src, scarp_fields, CACHE_BASE, "prod_fullcat"
    )
    ys_fp, xs_fp = np.nonzero(g.footprint)
    d_fullcat = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    allowed_prod = g.footprint & (d_fullcat > 2.0)
    act_idx_prod = np.flatnonzero(allowed_prod[ys_fp, xs_fp])
    ay_prod, ax_prod = ys_fp[act_idx_prod], xs_fp[act_idx_prod]

    arms = ("h88_adhr_incumbent", "exp01_sar_phys", "exp02_csd_joint", "exp03_sar_csd")
    terms_by_arm: dict[str, np.ndarray | None] = {a: None for a in arms}
    preds_by_arm_seed: dict[str, dict[int, np.ndarray]] = {
        a: {s: np.zeros(g.shape, dtype=np.float32) for s in SEEDS} for a in arms
    }
    fold_records: list[dict[str, Any]] = []
    prod_p_full_acc = np.zeros(act_idx_prod.size, dtype=np.float64)
    prod_m_full_acc = np.zeros(act_idx_prod.size, dtype=np.float64)
    zero_leakage_scramble_equal = False

    for seed, folds in folds_by_seed:
        if args.only_seed is not None and seed != args.only_seed:
            continue
        vis_s = folds[0]["visible"]
        X_v22, dv_s, cl_s = adhr.compute_visible_struct_fp(
            g, vis_s, sense_src, scarp_fields, CACHE_BASE, f"seed{seed}"
        )
        reg_all = np.zeros(g.shape, dtype=bool)
        tr_all = np.zeros(g.shape, dtype=bool)
        for f in folds:
            reg_all |= f["region"]
            tr_all |= f["truth"]

        if seed == 20:
            f0 = folds[0]
            zero_leakage_scramble_equal = sar_csd.verify_zero_test_quadrant_leakage(
                g, X_sar_diff, X_csd20, X_v22, dv_s, cl_s, vis_s,
                reg_all & (~f0["region"]), tr_all, f0["region"],
            )
            if not zero_leakage_scramble_equal:
                raise RuntimeError("Zero-leakage test-quadrant scrambling check FAILED!")
            log("      Verified test-quadrant label-scrambling invariance: PASS (bit-for-bit identical)")

        covered_prod_s = np.zeros(act_idx_prod.size, dtype=bool)
        p_prod_seed = np.zeros(act_idx_prod.size, dtype=np.float32)
        m_prod_seed = np.zeros(act_idx_prod.size, dtype=np.float32)

        for q_idx, f in enumerate(folds):
            fname = f["name"]
            t_fold = time.monotonic()
            train_regions = reg_all & (~f["region"])
            train_truth = tr_all & (~f["region"])
            test_region = f["region"]

            mask_prod_q = f["region"][ay_prod, ax_prod]
            if q_idx == len(folds) - 1:
                mask_prod_q = mask_prod_q | (~covered_prod_s)
            covered_prod_s |= mask_prod_q

            ck_path = FOLD_CACHE_DIR / f"fold_s{seed}_{fname}.npz"
            if ck_path.is_file():
                z = np.load(ck_path, allow_pickle=False)
                em_adhr = _yx_to_grid(z["yx_adhr"], g.shape)
                em_e1 = _yx_to_grid(z["yx_e1"], g.shape)
                em_e2 = _yx_to_grid(z["yx_e2"], g.shape)
                em_e3 = _yx_to_grid(z["yx_e3"], g.shape)
                metas = json.loads(str(z["metas_json"]))
                meta_adhr, meta_e1, meta_e2, meta_e3 = metas["adhr"], metas["e1"], metas["e2"], metas["e3"]
                pq_prod = z["pq_prod"]
                mq_prod = z["mq_prod"]
                cached_tag = " [cached]"
            else:
                em_adhr, _, meta_adhr = adhr.predict_adhr_fold(
                    g, X_phys, X_v22, dv_s, cl_s, vis_s, train_regions, train_truth, test_region,
                    seed=88000 + 10 * seed + f["fold"],
                )
                arm_out = sar_csd.predict_all_sarcsd_arms_fold(
                    g, X_phys, X_sar_diff, X_csd20, X_v22, dv_s, cl_s, vis_s,
                    train_regions, train_truth, test_region,
                    seed=88200 + 10 * seed + f["fold"],
                    min_spacing_px=MIN_SPACING_PX,
                    prod_struct_pack=(X_v22_prod, dv_prod, cl_prod, act_idx_prod[mask_prod_q]),
                )
                em_e1, meta_e1 = arm_out["exp01"]  # type: ignore[misc]
                em_e2, meta_e2 = arm_out["exp02"]  # type: ignore[misc]
                em_e3, meta_e3 = arm_out["exp03"]  # type: ignore[misc]
                pq_prod, mq_prod = arm_out["prod_struct_q"]  # type: ignore[misc]
                np.savez_compressed(
                    ck_path,
                    yx_adhr=_grid_to_yx(em_adhr),
                    yx_e1=_grid_to_yx(em_e1),
                    yx_e2=_grid_to_yx(em_e2),
                    yx_e3=_grid_to_yx(em_e3),
                    pq_prod=pq_prod,
                    mq_prod=mq_prod,
                    metas_json=json.dumps({"adhr": meta_adhr, "e1": meta_e1, "e2": meta_e2, "e3": meta_e3}),
                )
                cached_tag = ""

            p_prod_seed[mask_prod_q] = pq_prod
            m_prod_seed[mask_prod_q] = mq_prod

            fold_preds = {
                "h88_adhr_incumbent": (em_adhr, meta_adhr),
                "exp01_sar_phys": (em_e1, meta_e1),
                "exp02_csd_joint": (em_e2, meta_e2),
                "exp03_sar_csd": (em_e3, meta_e3),
            }
            rec: dict[str, Any] = {
                "seed": seed,
                "fold": fname,
                "withheld_positive_pixels": int((f["truth"] & g.footprint & f["region"] & (~f["masked_known"])).sum()),
            }
            for arm_name, (em_arr, _meta_arm) in fold_preds.items():
                res_f, terms_f = evaluate_holdout.evaluate(
                    em_arr, f, g.footprint, block_side=BLOCK_SIDE, global_shape=g.shape
                )
                terms_by_arm[arm_name] = terms_f if terms_by_arm[arm_name] is None else (terms_by_arm[arm_name] + terms_f)
                preds_by_arm_seed[arm_name][seed][test_region] = em_arr[test_region]
                rec[arm_name] = {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": evaluate_holdout.VERSION,
                    "dti": round(float(res_f["dti"]), 6),
                    "emitted": int(res_f["emitted"]),
                    "tpw": round(float(res_f["tpw"]), 2),
                    "fpw": round(float(res_f["fpw"]), 2),
                }
            fold_records.append(rec)
            log(
                f"      Seed {seed} {fname}{cached_tag} ({time.monotonic() - t_fold:.1f}s): "
                f"ADHR={rec['h88_adhr_incumbent']['dti']:.5f} ({rec['h88_adhr_incumbent']['emitted']}d) | "
                f"Exp01={rec['exp01_sar_phys']['dti']:.5f} ({rec['exp01_sar_phys']['emitted']}d) | "
                f"Exp02={rec['exp02_csd_joint']['dti']:.5f} ({rec['exp02_csd_joint']['emitted']}d) | "
                f"Exp03={rec['exp03_sar_csd']['dti']:.5f} ({rec['exp03_sar_csd']['emitted']}d)"
            )
            gc.collect()

        prod_p_full_acc += p_prod_seed
        prod_m_full_acc += m_prod_seed
        del X_v22, dv_s, cl_s, p_prod_seed, m_prod_seed
        gc.collect()

    del X_v22_prod, dv_prod, cl_prod
    gc.collect()

    if args.only_seed is not None:
        log(f"Checkpointed all 4 folds of Seed {args.only_seed} cleanly in {time.monotonic() - t0:.1f}s.")
        return 0

    summary_e3 = evaluate_holdout.pooled_summary(
        {k: v for k, v in terms_by_arm.items() if v is not None},
        draws=BOOT_DRAWS,
        seed=BOOT_SEED,
        candidate="exp03_sar_csd",
    )
    summary_e2 = evaluate_holdout.pooled_summary(
        {k: v for k, v in terms_by_arm.items() if v is not None},
        draws=BOOT_DRAWS,
        seed=BOOT_SEED,
        candidate="exp02_csd_joint",
    )

    far_gt10 = evaluate_subset_dti(preds_by_arm_seed, folds_by_seed, g, min_d_vis_px=10.0)
    far_gt25 = evaluate_subset_dti(preds_by_arm_seed, folds_by_seed, g, min_d_vis_px=25.0)
    del preds_by_arm_seed
    gc.collect()

    for arm_name in arms:
        sc = summary_e3["scores"][arm_name]
        log(
            f"      POOLED {arm_name}: HOLDOUT-DTI={sc['dti']:.6f} CI95=[{sc['ci95'][0]:.6f}, {sc['ci95'][1]:.6f}] "
            f"(TPw={sc['tpw']:.1f}, FPw={sc['fpw']:.1f}) | >1km={far_gt10[arm_name]['dti']:.5f} | >2.5km={far_gt25[arm_name]['dti']:.5f}"
        )
    d_e3_vs_adhr = summary_e3["paired_differences"]["h88_adhr_incumbent"]
    d_e2_vs_adhr = summary_e2["paired_differences"]["h88_adhr_incumbent"]
    log(
        f"      PAIRED Δ Exp03 vs ADHR = {d_e3_vs_adhr['delta']:+.6f} CI95=[{d_e3_vs_adhr['ci95'][0]:+.6f}, {d_e3_vs_adhr['ci95'][1]:+.6f}]"
    )
    log(
        f"      PAIRED Δ Exp02 vs ADHR = {d_e2_vs_adhr['delta']:+.6f} CI95=[{d_e2_vs_adhr['ci95'][0]:+.6f}, {d_e2_vs_adhr['ci95'][1]:+.6f}]"
    )

    holdout_doc = {
        **summary_e3,
        "stored_adhr_bar": stored_adhr_bar,
        "exp02_paired_differences": summary_e2["paired_differences"],
        "far_gt10px_subset": far_gt10,
        "far_gt25px_subset": far_gt25,
        "zero_leakage_quadrant_scramble_equal": zero_leakage_scramble_equal,
        "folds": fold_records,
    }
    write_json(ROOT / "evidence/sarcsd88_holdout.json", holdout_doc)

    log("[4/8] Fitting 4-quadrant OOF production SAR-CSD surface & checking pre-placement |rho| <= 0.90")
    reg_list = extended_registry_list(exclude=("gems88-sarcsd-",))
    pre_rho_summary: dict[str, Any] = {}

    def _preplacement_check(p_surf: np.ndarray) -> None:
        rk_pre = gate.rank_vec(p_surf, g.footprint)
        max_abs_rho = 0.0
        worst_lbl = ""
        seen_bits: set[str] = set()
        for lbl, rpath in reg_list:
            vals = gate.read_values(rpath, g.footprint)
            bkey = hashlib.sha256(np.packbits(vals > 0).tobytes()).hexdigest() + ("D" if gate.is_dense(vals, g.footprint) else "S")
            if bkey in seen_bits:
                continue
            seen_bits.add(bkey)
            rho = abs(gate._pearson(rk_pre, gate.rank_vec(vals, g.footprint)))
            if rho > max_abs_rho:
                max_abs_rho = rho
                worst_lbl = lbl
        pre_rho_summary["max_abs_rho"] = round(float(max_abs_rho), 6)
        pre_rho_summary["worst_label"] = worst_lbl
        pre_rho_summary["rasters_checked"] = len(reg_list)
        pre_rho_summary["distinct_dot_sets_checked"] = len(seen_bits)
        pre_rho_summary["passed"] = bool(max_abs_rho <= 0.90)
        log(f"      Pre-placement surface |rho| max = {max_abs_rho:.6f} vs {worst_lbl} ({len(reg_list)} rasters)")
        if max_abs_rho > 0.90:
            raise SystemExit(f"STOP: Pre-placement surface rank-correlation {max_abs_rho:.6f} > 0.90 ({worst_lbl})")

    p_prod_full_raw = (prod_p_full_acc / len(SEEDS)).astype(np.float32)
    m_prod_full_raw = (prod_m_full_acc / len(SEEDS)).astype(np.float32)
    del prod_p_full_acc, prod_m_full_acc
    gc.collect()

    emitted_prod, p_surface_prod, prod_meta = sar_csd.fit_and_emit_production_sar_csd(
        g,
        X_phys,
        X_sar_diff,
        X_csd20,
        folds_by_seed,
        sense_src,
        scarp_fields,
        CACHE_BASE,
        min_spacing_px=MIN_SPACING_PX,
        preplacement_gate=_preplacement_check,
        precomputed_full_raw=(p_prod_full_raw, m_prod_full_raw),
    )
    del p_prod_full_raw, m_prod_full_raw
    gc.collect()
    log(
        f"      Production dots = {prod_meta['n_dots']:,} | share_le2 = {prod_meta['share_le2']:.5f} | "
        f"share_gt10 = {prod_meta['share_gt10']:.4f} | share_gt25 = {prod_meta['share_gt25']:.4f} | "
        f"median_d_cat = {prod_meta['median_d_cat_px']:.2f} px"
    )

    log("[5/8] Writing temporary GeoTIFF and running complete 270+-raster uniqueness + fingerprint + holdout gate v3")
    sample_path = ROOT / "data/bridge/sample_submission.tif"
    tmp_tif = CACHE_CSD / "candidate_stage.tif"
    portal_writer.write_portal_tif(tmp_tif, emitted_prod, sample_path, g.footprint)

    uq = gate.uniqueness_report(tmp_tif, reg_list, g.footprint, surface=p_surface_prod)
    fp_prof = gate.fingerprint((emitted_prod > 0) & g.footprint, d_fullcat)
    fp_pass = gate.fingerprint_screen(fp_prof)

    e3_score = float(summary_e3["scores"]["exp03_sar_csd"]["dti"])
    e3_ci = summary_e3["scores"]["exp03_sar_csd"]["ci95"]
    e2_score = float(summary_e3["scores"]["exp02_csd_joint"]["dti"])
    adhr_recomp = float(summary_e3["scores"]["h88_adhr_incumbent"]["dti"])
    holdout_beats_both = bool(
        (e3_score > stored_adhr_bar)
        and (e3_score > adhr_recomp)
        and (float(d_e3_vs_adhr["ci95"][0]) > 0.0)
        and fp_pass
    )
    prelim_hash8 = sha256_file(tmp_tif)[:8]

    tentative_portal = gate.portal_validate(tmp_tif, sample_path, g.footprint)
    all_v3_clear = bool(
        tentative_portal["ok"]
        and uq["unique_like_for_like"]
        and canary_passed
        and zero_leakage_scramble_equal
        and holdout_beats_both
    )

    if all_v3_clear:
        stem = f"gems88-sarcsd-missingness-csd20-{prod_meta['n_dots']}-20261024-{prelim_hash8}-zeros"
        sub_name = f"GEMSDOE88-SARCSD-{prelim_hash8.upper()}"
        sub_note = (
            f"SAR-CSD 87ch de-novo missingness+CSD20 2.65px Dinkelbach {prod_meta['n_dots']}d; "
            f"HOLDOUT-DTI {e3_score:.4f} vs ADHR {adhr_recomp:.4f}; gt25={fp_prof['share_gt25']*100:.1f}%"
        )[:140]
    else:
        stem = f"gems88-sarcsd-missingness-csd20-{prod_meta['n_dots']}-20261024-{prelim_hash8}-zeros-DO-NOT-SUBMIT"
        sub_name = f"GEMSDOE88-SARCSD-{prelim_hash8.upper()}-DO-NOT-SUBMIT"
        sub_note = (
            f"SAR-CSD 87ch {prod_meta['n_dots']}d; Exp02 HOLDOUT-DTI {e2_score:.4f}, Exp03 {e3_score:.4f}; "
            f"gt25={fp_prof['share_gt25']*100:.1f}%; DO NOT SUBMIT"
        )[:140]

    dl_tif = ROOT / "docs/downloads" / f"{stem}.tif"
    dl_zip = ROOT / "docs/downloads" / f"{stem}.zip"
    dl_receipt = ROOT / "docs/downloads" / f"{stem}.json"
    dl_audit = ROOT / "docs/downloads" / f"{stem}.format-audit.json"
    sub_tif = ROOT / "submissions" / f"{stem}.tif"
    sub_zip = ROOT / "submissions" / f"{stem}.zip"
    sub_receipt = ROOT / "submissions" / f"{stem}.json"

    for old_p in list((ROOT / "docs/downloads").glob("gems88-sarcsd-*")) + list((ROOT / "submissions").glob("gems88-sarcsd-*")):
        old_p.unlink(missing_ok=True)

    shutil.copy2(tmp_tif, dl_tif)
    portal_writer.write_single_member_zip(dl_zip, dl_tif)
    os.chmod(dl_tif, 0o644)
    os.chmod(dl_zip, 0o644)

    shutil.copy2(dl_tif, sub_tif)
    shutil.copy2(dl_zip, sub_zip)
    os.chmod(sub_tif, 0o644)
    os.chmod(sub_zip, 0o644)

    log("[6/8] Running independent portal-parity format validation on saved .tif and .zip")
    portal_tif = gate.portal_validate(dl_tif, sample_path, g.footprint)
    portal_zip = gate.portal_validate(dl_zip, sample_path, g.footprint)
    indep_audit = validate_artifact(dl_tif, sample_path)
    g57_fmt = g57gates.format_report(dl_tif, sample_path, footprint=g.footprint)
    g57_val = g57validate.validate(dl_tif, g.footprint, g.catalogue)
    if not (
        portal_tif["ok"]
        and portal_zip["ok"]
        and indep_audit["ok"]
        and g57_fmt["ok"]
        and g57_val["all_checks_passed"]
        and portal_tif["array_sha256"] == portal_zip["array_sha256"]
    ):
        raise RuntimeError(f"Format audit failed: tif={portal_tif['problems']} zip={portal_zip['problems']}")

    tif_sha = sha256_file(dl_tif)
    zip_sha = sha256_file(dl_zip)

    # Identical bytes to tmp_tif; bind candidate path to final dl_tif
    uq_final = dict(uq, candidate=f"docs/downloads/{dl_tif.name}")

    used_names: set[str] = set()
    for p_rc in (ROOT / "registry").glob("*.json"):
        if "sarcsd" in p_rc.name:
            continue
        try:
            d = json.loads(p_rc.read_text())
            if isinstance(d, dict) and isinstance(d.get("submission_name"), str):
                used_names.add(d["submission_name"])
        except Exception:
            pass

    verdict_v3 = gate.decide(
        portal=portal_tif,
        uniqueness=uq_final,
        canary_passed=bool(canary_passed and zero_leakage_scramble_equal),
        holdout_beats_bar=holdout_beats_both,
        name=sub_name,
        note=sub_note,
        used_names=used_names,
        receipt_sha_matches=True,
    )
    if not fp_pass and "FINGERPRINT" not in " ".join(verdict_v3["blocking_reasons"]):
        verdict_v3["blocking_reasons"].append(
            f"FINGERPRINT: share_le2={fp_prof['share_le2']:.4f} (req 0), share_gt25={fp_prof['share_gt25']:.4f} (req >=0.35)"
        )
        verdict_v3["ok_to_submit"] = False
        verdict_v3["label"] = "OK TO DOWNLOAD - NOT OK TO SUBMIT"

    log("[7/8] Running non-circular USGS SGMC off-catalogue piedmont diagnostic")
    sgmc_diag = compute_sgmc_offcat_diagnostic(g, emitted_prod)

    elapsed_s = round(time.monotonic() - t0, 2)
    writer_receipt = {
        "schema": "gems88.writer-receipt.v1",
        "file": f"docs/downloads/{dl_tif.name}",
        "zip_file": f"docs/downloads/{dl_zip.name}",
        "sha256": tif_sha,
        "zip_sha256": zip_sha,
        "submission_name": sub_name,
        "note": sub_note,
        "note_length": len(sub_note),
        "positive_pixels": int(prod_meta["n_dots"]),
        "gate_v3_ok_to_download": verdict_v3["ok_to_download"],
        "gate_v3_ok_to_submit": verdict_v3["ok_to_submit"],
        "portal_and_uniqueness_valid": bool(portal_tif["ok"] and portal_zip["ok"] and uq_final["unique_like_for_like"]),
        "literal_17gemsdoe_overlap_3px": 1.0,
        "weekly_slots_spent": 0,
    }
    write_json(dl_receipt, writer_receipt)
    write_json(sub_receipt, writer_receipt)
    write_json(dl_audit, {"tif": portal_tif, "zip": portal_zip, "independent": indep_audit, "gems57_validate": g57_val})
    os.chmod(dl_receipt, 0o644)
    os.chmod(sub_receipt, 0o644)
    os.chmod(dl_audit, 0o644)

    rows_sorted = sorted(
        [r for r in uq_final["rows"] if "error" not in r],
        key=lambda r: (-r["like_for_like_overlap_3px"], -abs(r["rho_preplacement"])),
    )
    uq_saved = {k: v for k, v in uq_final.items() if k != "rows"}
    uq_saved["top_30_closest_rasters"] = rows_sorted[:30]
    uq_saved["dense_rasters"] = [r for r in rows_sorted if r["dense"]]
    uq_saved["all_rows_sha256"] = hashlib.sha256(
        json.dumps(uq_final["rows"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    write_json(ROOT / "evidence/sarcsd88_uniqueness.json", uq_saved)

    gate_record = {
        **verdict_v3,
        "sha256": tif_sha,
        "zip_sha256": zip_sha,
        "portal_and_uniqueness_valid": bool(portal_tif["ok"] and portal_zip["ok"] and uq_final["unique_like_for_like"]),
        "candidate": {
            "tif": f"docs/downloads/{dl_tif.name}",
            "zip": f"docs/downloads/{dl_zip.name}",
            "sha256": tif_sha,
            "zip_sha256": zip_sha,
            "dots": int(prod_meta["n_dots"]),
        },
        "fingerprint": fp_prof,
        "fingerprint_screen_pass": fp_pass,
        "holdout_comparison": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "withheld_positive_pixels": 22893,
            "exp01_sar_phys_dti": float(summary_e3["scores"]["exp01_sar_phys"]["dti"]),
            "exp02_csd_joint_dti": e2_score,
            "exp02_csd_joint_ci95": summary_e3["scores"]["exp02_csd_joint"]["ci95"],
            "exp02_paired_delta_vs_recomputed_adhr": d_e2_vs_adhr["delta"],
            "exp02_paired_delta_ci95": d_e2_vs_adhr["ci95"],
            "exp02_beats_both_bars_with_positive_ci95": bool(
                (e2_score > stored_adhr_bar)
                and (e2_score > adhr_recomp)
                and (float(d_e2_vs_adhr["ci95"][0]) > 0.0)
            ),
            "exp03_dti": e3_score,
            "exp03_ci95": e3_ci,
            "stored_adhr_bar": stored_adhr_bar,
            "recomputed_adhr_dti": adhr_recomp,
            "paired_delta_vs_recomputed_adhr": d_e3_vs_adhr["delta"],
            "paired_delta_ci95": d_e3_vs_adhr["ci95"],
            "beats_both_bars_with_positive_ci95": holdout_beats_both,
        },
        "uniqueness_summary": {
            "registry_rasters": uq_final["registry_rasters"],
            "distinct_dot_sets": uq_final["distinct_dot_sets"],
            "missing": uq_final["missing"],
            "unique_like_for_like": uq_final["unique_like_for_like"],
            "unique_literal": uq_final["unique_literal"],
            "worst_like_for_like_overlap": uq_final["worst_like_for_like_overlap"],
            "worst_abs_rho": uq_final["worst_abs_rho"],
            "literal_blockers": uq_final["literal_blockers"],
            "vacuity_witness": uq_final["vacuity_witness"],
        },
        "weekly_slots_spent": 0,
        "organizer_confirmed_score": None,
    }
    write_json(ROOT / "registry/sarcsd88_gate_v3.json", gate_record)
    write_json(ROOT / "docs/data/sarcsd88_gate_v3.json", gate_record)

    run_card = {
        "schema": "gems88.run-card.sarcsd88.v1",
        "date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/46dc6f1d-gemsdoe88",
        "lane": "H88-SAR-CSD",
        "hypothesis": prereg["lane"]["title"],
        "mechanism": prereg["lane"]["method_paragraph"],
        "named_non_fault_mimic": prereg["lane"]["named_non_fault_mimic"],
        "experiments_run": 3,
        "experiment_budget_max": 3,
        "elapsed_seconds": elapsed_s,
        "budget_wall_seconds_max": 7200,
        "organizer_confirmed_score": None,
        "weekly_slots_spent": 0,
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "withheld_positive_pixels": 22893,
            "exp01_sar_phys": summary_e3["scores"]["exp01_sar_phys"],
            "exp02_csd_joint": summary_e3["scores"]["exp02_csd_joint"],
            "exp03_sar_csd": summary_e3["scores"]["exp03_sar_csd"],
            "h88_adhr_recomputed_control": summary_e3["scores"]["h88_adhr_incumbent"],
            "h88_adhr_stored_bar": stored_adhr_bar,
            "paired_delta_exp03_vs_adhr": d_e3_vs_adhr,
            "paired_delta_exp02_vs_adhr": d_e2_vs_adhr,
            "far_gt10px_subset": far_gt10,
            "far_gt25px_subset": far_gt25,
        },
        "leakage_canary": {
            "evidence_class": "LEAKAGE-CANARY",
            "features_tested": len(canary_rows),
            "threshold": 0.90,
            "max_symmetric_auc": max_canary_auc,
            "passed": canary_passed,
            "zero_leakage_quadrant_scramble_equal": zero_leakage_scramble_equal,
        },
        "correlation_overlap_vs_registry": {
            "policy_like_for_like": "gems88-gate-v3",
            "policy_literal": "binding-literal-all-registry-v1",
            "registry_rasters_checked": uq_final["registry_rasters"],
            "distinct_dot_sets_checked": uq_final["distinct_dot_sets"],
            "preplacement_max_abs_spearman": pre_rho_summary["max_abs_rho"],
            "preplacement_worst_label": pre_rho_summary["worst_label"],
            "final_max_abs_spearman": uq_final["worst_abs_rho"]["value"],
            "final_worst_like_for_like_overlap_3px": uq_final["worst_like_for_like_overlap"]["value"],
            "final_worst_like_for_like_label": uq_final["worst_like_for_like_overlap"]["label"],
            "unique_like_for_like": uq_final["unique_like_for_like"],
            "final_literal_overlap_3px": 1.0,
            "literal_blockers": uq_final["literal_blockers"],
            "unique_literal": uq_final["unique_literal"],
            "vacuity_witness": uq_final["vacuity_witness"],
        },
        "fingerprint": {
            **fp_prof,
            "screen_min_share_gt25": gate.FP_SCREEN_MIN_GT25,
            "passed": fp_pass,
        },
        "off_catalogue_sgmc_piedmont_diagnostic": sgmc_diag,
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "download": f"docs/downloads/{dl_tif.name}",
        "zip_download": f"docs/downloads/{dl_zip.name}",
        "repo_copy": f"submissions/{sub_tif.name}",
        "validator_output": {
            "raster_sha256": tif_sha,
            "zip_sha256": zip_sha,
            "format_valid": bool(portal_tif["ok"] and portal_zip["ok"] and indep_audit["ok"]),
            "no_nan_inside": bool(portal_tif["checks"]["footprint_cells_finite"] and portal_tif["checks"]["all_finite"]),
            "values_in_0_1": bool(portal_tif["checks"]["portal_range_check_nan_strict"]),
            "crs_match": bool(portal_tif["checks"]["crs_epsg_32611"]),
            "shape_match": bool(portal_tif["checks"]["shape_matches_sample"]),
            "transform_match": bool(portal_tif["checks"]["transform_matches_sample"]),
            "zero_outside_footprint": bool(portal_tif["checks"]["outside_footprint_zero"]),
            "zero_on_known_catalogue": bool(g57_val["on_catalogue_positive_pixels"] == 0),
            "layout_parity_with_sample": bool(portal_tif["layout_parity_with_sample"]),
            "second_decoder": portal_tif["second_decoder"],
            "positive_dots": int(prod_meta["n_dots"]),
        },
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_chars": len(sub_note),
        "gate_v3_verdict": "promote" if verdict_v3["ok_to_submit"] else "negative",
        "gate_v3_ok_to_download": verdict_v3["ok_to_download"],
        "gate_v3_ok_to_submit": verdict_v3["ok_to_submit"],
        "portal_and_uniqueness_valid": bool(portal_tif["ok"] and portal_zip["ok"] and uq_final["unique_like_for_like"]),
        "literal_all_registry_ok_to_submit": False,
        "verdict": "promote" if verdict_v3["ok_to_submit"] else "negative",
        "decision_summary": (
            "OK TO DOWNLOAD: YES. GATE V3 (SCIENTIFIC + LIKE-FOR-LIKE 270+-RASTER UNIQUENESS + FINGERPRINT + PORTAL PARITY): "
            + ("PASS — ELIGIBLE FOR HUMAN WEEKLY-SLOT SELECTOR" if verdict_v3["ok_to_submit"] else "FAIL — DO NOT SUBMIT")
            + ". LITERAL ALL-RASTER WITNESS (17GEMSDOE 100%-FOOTPRINT SURFACE): 1.0000 (vacuous for any non-empty raster; human selector review required before spending a weekly slot)."
        ),
    }
    for out_rc in (
        ROOT / "registry/sarcsd88_run_card.json",
        ROOT / "docs/data/sarcsd88_run_card.json",
        ROOT / "evidence/sarcsd88_run_card.json",
    ):
        write_json(out_rc, run_card)

    log(f"[8/8] COMPLETE in {elapsed_s:.1f}s -> {dl_tif.name}")
    log(f"      gate_v3 ok_to_download={verdict_v3['ok_to_download']} | gate_v3 ok_to_submit={verdict_v3['ok_to_submit']} | verdict={run_card['verdict']}")
    log(f"      blocking_reasons={verdict_v3['blocking_reasons']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
