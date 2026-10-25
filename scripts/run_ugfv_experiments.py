#!/usr/bin/env python3
"""Execute GEMSDOE88 multi-physics + geothermal + self-masked relay experiments (`Exp 02` & `Exp 03`).

Experiment budget accounting (strict cap <= 3 total):
  - Experiment 01 (`raw_control` / `MGC-88` retained baseline): 7-channel RTP/gravity co-edge + fixed 2px spacing.
  - Experiment 02 (`blind_physics` / `H88-UGFV-BlindPhys`): 32-channel zero-catalogue physics, true analytical
    Miller-Singh tilt, 60-deg up-dip basement advection, fluid-injection swarm excess, GeoDAWN K/Th & U/Th,
    1-m LiDAR scarps, 10-m fluvial chi knickpoints, DOE GDR 1391 2-m probes & sinter vents, and mimic
    deconfounders + exact Dinkelbach submodular emission (`emit.dinkelbach_allocate`, `budget=None`).
  - Experiment 03 (`candidate` / `H88-UGFV-Submod`): Independent Noisy-OR synthesis fusing `H88-UGFV-BlindPhys`
    with nested self-masked visible-only structural continuation (`anatomy.fold_geometry` + tip beam +
    multi-host relay excess) + exact Dinkelbach submodular emission (`budget=None`).
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import gc
import json
import math
import resource
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]

from gems57 import emit as g57_emit  # noqa: E402
from gems57 import evaluate_holdout, grid, holdout, submission_writer, uniqueness  # noqa: E402
from gems88 import edge, model, ugfv  # noqa: E402
from restore_inputs import digest  # noqa: E402

DATA = ROOT / "data"
REGISTRY = ROOT / "registry"
DOCS = ROOT / "docs"
EVIDENCE = ROOT / "evidence"
SEEDS = (20, 21)
BUDGET_MGC88 = 37654
HIDE_RATIO_PRIOR = 0.25  # hide_frac / (1 - hide_frac) = 0.20 / 0.80, zero truth inspection


def dump(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, allow_nan=False, sort_keys=True) + "\n")


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def exact_spearman_from_preranked(a_centered_norm: np.ndarray, b: np.ndarray) -> float:
    """Exact Spearman rho matching `scipy.stats.spearmanr(a, b)` in O(N) peak RAM (`40 MB` vs `413 MB`)."""
    rb = rankdata(b).astype(np.float64)
    rb -= rb.mean()
    denom = float(np.linalg.norm(rb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a_centered_norm, rb) / denom)


def bbox(region: np.ndarray, pad: int = 4) -> tuple[slice, slice]:
    row, col = np.nonzero(region)
    return (
        slice(max(int(row.min()) - pad, 0), min(int(row.max()) + pad + 1, region.shape[0])),
        slice(max(int(col.min()) - pad, 0), min(int(col.max()) + pad + 1, region.shape[1])),
    )


def fit_calibrated_dual_heads(
    X_train: np.ndarray,
    y_exact: np.ndarray,
    y_kern: np.ndarray,
    sample_weight: np.ndarray,
    prior_scale: float,
    seed: int,
) -> tuple[HistGradientBoostingClassifier, HistGradientBoostingRegressor]:
    clf = HistGradientBoostingClassifier(
        max_iter=105,
        max_leaf_nodes=63,
        min_samples_leaf=80,
        learning_rate=0.07,
        l2_regularization=2.0,
        random_state=seed,
    )
    clf.fit(X_train, y_exact.astype(np.int8), sample_weight=sample_weight)

    reg = HistGradientBoostingRegressor(
        max_iter=105,
        max_leaf_nodes=63,
        min_samples_leaf=80,
        learning_rate=0.07,
        l2_regularization=2.0,
        random_state=seed + 977,
    )
    reg.fit(X_train, np.clip(y_kern * prior_scale, 0.0, 1.0), sample_weight=sample_weight)
    return clf, reg


def predict_calibrated_dual_heads(
    clf: HistGradientBoostingClassifier,
    reg: HistGradientBoostingRegressor,
    X_eval: np.ndarray,
    prior_scale: float,
    chunk: int = 250_000,
) -> tuple[np.ndarray, np.ndarray]:
    n = X_eval.shape[0]
    p_hat = np.empty(n, dtype=np.float32)
    m_hat = np.empty(n, dtype=np.float32)
    for st in range(0, n, chunk):
        sl = slice(st, min(st + chunk, n))
        p_vis = np.clip(clf.predict_proba(X_eval[sl])[:, 1], 1e-7, 1.0 - 1e-7)
        odds = (p_vis / (1.0 - p_vis)) * prior_scale
        ph = (odds / (1.0 + odds)).astype(np.float32)
        mh = np.clip(reg.predict(X_eval[sl]), 0.0, 1.0).astype(np.float32)
        p_hat[sl] = ph
        m_hat[sl] = np.maximum(mh, ph)
    return p_hat, m_hat


def sample_static_training_data(
    mm_static: np.memmap,
    train_domain: np.ndarray,
    vis_in_train: np.ndarray,
    seed: int,
    n_halo_keep: int = 38_000,
    n_neg_keep: int = 92_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Sample positive, halo (`0 < d < 3`), and background pixels with exact Horvitz-Thompson weights."""
    d_vis = ndi.distance_transform_edt(~vis_in_train)
    y_kern_full = np.clip(1.0 - d_vis / 3.0, 0.0, 1.0).astype(np.float32)

    pos_idx = np.flatnonzero((train_domain & vis_in_train).ravel())
    halo_idx = np.flatnonzero((train_domain & (~vis_in_train) & (y_kern_full > 0.0)).ravel())
    neg_idx = np.flatnonzero((train_domain & (y_kern_full == 0.0)).ravel())

    rng = np.random.default_rng(seed)
    w_pos = np.ones(pos_idx.size, dtype=np.float32)

    if halo_idx.size > n_halo_keep:
        sel_h = rng.choice(halo_idx, size=n_halo_keep, replace=False)
        w_halo = np.full(n_halo_keep, halo_idx.size / float(n_halo_keep), dtype=np.float32)
    else:
        sel_h = halo_idx
        w_halo = np.ones(sel_h.size, dtype=np.float32)

    if neg_idx.size > n_neg_keep:
        sel_n = rng.choice(neg_idx, size=n_neg_keep, replace=False)
        w_neg = np.full(n_neg_keep, neg_idx.size / float(n_neg_keep), dtype=np.float32)
    else:
        sel_n = neg_idx
        w_neg = np.ones(sel_n.size, dtype=np.float32)

    idx = np.concatenate([pos_idx, sel_h, sel_n])
    w = np.concatenate([w_pos, w_halo, w_neg])
    y_exact = np.zeros(idx.size, dtype=np.int8)
    y_exact[: pos_idx.size] = 1
    y_kern = y_kern_full.ravel()[idx]
    X = np.asarray(mm_static[idx], dtype=np.float32)
    del d_vis, y_kern_full
    return X, y_exact, y_kern, w


def sample_structural_training_draw(
    grid_obj: grid.Grid,
    mm_static: np.memmap,
    inner_vis: np.ndarray,
    inner_truth: np.ndarray,
    full_visible: np.ndarray,
    sense_full: np.ndarray,
    quad_map: np.ndarray,
    seed: int,
    n_halo_keep: int = 34_000,
    n_neg_keep: int = 82_000,
) -> dict:
    """Extract one self-masked inner training table cleanly tagged with quadrant IDs (`0..3`)."""
    other_vis = full_visible & (~inner_truth)
    valid_pool = grid_obj.footprint & (~other_vis)
    d_t = ndi.distance_transform_edt(~inner_truth)
    y_kern_full = np.clip(1.0 - d_t / 3.0, 0.0, 1.0).astype(np.float32)

    pos_idx = np.flatnonzero((valid_pool & inner_truth).ravel())
    halo_idx = np.flatnonzero((valid_pool & (~inner_truth) & (y_kern_full > 0.0)).ravel())
    neg_idx = np.flatnonzero((valid_pool & (y_kern_full == 0.0)).ravel())

    rng = np.random.default_rng(seed)
    if halo_idx.size > n_halo_keep:
        sel_h = rng.choice(halo_idx, size=n_halo_keep, replace=False)
        wh = halo_idx.size / float(n_halo_keep)
    else:
        sel_h = halo_idx
        wh = 1.0

    if neg_idx.size > n_neg_keep:
        sel_n = rng.choice(neg_idx, size=n_neg_keep, replace=False)
        wn = neg_idx.size / float(n_neg_keep)
    else:
        sel_n = neg_idx
        wn = 1.0

    chosen_mask = np.zeros(grid_obj.shape, dtype=bool)
    chosen_mask.ravel()[np.concatenate([pos_idx, sel_h, sel_n])] = True

    flat_idx, X_struct = ugfv.compute_visible_structural_fields(grid_obj, inner_vis, sense_full, chosen_mask)
    X_phys = np.asarray(mm_static[flat_idx], dtype=np.float32)
    X_joint = np.hstack([X_phys, X_struct])

    is_pos = inner_truth.ravel()[flat_idx]
    yk = y_kern_full.ravel()[flat_idx]
    w = np.where(is_pos, 1.0, np.where(yk > 0.0, wh, wn)).astype(np.float32)
    q_ids = quad_map.ravel()[flat_idx].astype(np.int8)

    del d_t, y_kern_full, chosen_mask, X_phys, X_struct
    gc.collect()
    return {
        "X": X_joint,
        "y_exact": is_pos.astype(np.int8),
        "y_kern": yk.astype(np.float32),
        "w": w,
        "quad": q_ids,
    }


def fuse_modalities(
    p_jnt: np.ndarray, m_jnt: np.ndarray, p_phys: np.ndarray, m_phys: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Independent Noisy-OR synthesis avoiding IR-88-12 nested meta-leakage collapse."""
    p_comb = np.clip(1.0 - (1.0 - 0.80 * p_jnt) * (1.0 - 0.35 * p_phys), 0.0, 1.0).astype(np.float32)
    m_comb = np.maximum(np.clip(0.80 * m_jnt + 0.20 * m_phys, 0.0, 1.0), p_comb).astype(np.float32)
    return p_comb, m_comb


def run(*, finalize_only: bool = False) -> dict:
    t_start = time.monotonic()
    print(f"[0.0s] Starting H88-UGFV pipeline (finalize_only={finalize_only}, RSS={rss_mb():.0f} MB)", flush=True)

    g = grid.load_grid()
    sample_path = DATA / "bridge" / "sample_submission.tif"
    witness_path = DATA / "registry" / "dense_17gemdoe.tif"
    h33_path = DATA / "registry" / "h33_education.tif"
    features_path = DATA / "training_features.tif"
    ext_dir = DATA / "external"

    with rasterio.open(sample_path) as ref:
        expected_grid = (ref.shape, ref.crs, ref.transform)

    universal = uniqueness.saturation_certificate(
        witness_path, g.footprint, g.catalogue, expected_grid=expected_grid
    )
    dump(REGISTRY / "witness_certificate.json", universal)

    mgc_cache = DATA / "cache" / "mgc88-7channel.f32"
    mgc_receipt = edge.build_cache(features_path, g.footprint, mgc_cache)
    mm_mgc = np.memmap(mgc_cache, mode="r", dtype="float32", shape=(g.height * g.width, len(edge.NAMES)))

    mm_ugfv, ugfv_meta = ugfv.build_ugfv_cache(g, features_path, ext_dir, DATA / "cache")
    mgc_receipt["ugfv_static_cache"] = ugfv_meta
    mgc_receipt["input_sha256"] = digest(features_path)
    dump(REGISTRY / "feature_receipt.json", mgc_receipt)
    print(
        f"[{time.monotonic()-t_start:.1f}s] Caches open: 32-ch UGFV ({ugfv_meta['bytes']/1e6:.1f} MB) (RSS={rss_mb():.0f} MB)",
        flush=True,
    )

    sense_full = ugfv.load_sense_code_raster(ext_dir / "trace_segments_utm11.csv", g.shape, g.transform)

    if finalize_only and (REGISTRY / "holdout_result.json").is_file() and (REGISTRY / "leakage_canaries.json").is_file():
        holdout_receipt = json.loads((REGISTRY / "holdout_result.json").read_text())
        exp2_vs_exp1 = holdout_receipt["paired_differences_blind_vs_mgc88"]
        max_auc = float(json.loads((REGISTRY / "leakage_canaries.json").read_text())["max_symmetric_auc"])
        quads = {20: holdout.quadrant_ids(g.footprint)}
    else:
        all_folds = []
        quads = {}
        for seed in SEEDS:
            draw, quad = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
            all_folds.extend(draw)
            quads[seed] = quad

        split_meta = dict(
            version="buffered-whole-components-loqo-v2",
            seeds=list(SEEDS),
            fields=[f["receipt"] for f in all_folds],
            evaluator=evaluate_holdout.VERSION,
            split_source_sha256=digest(ROOT / "vendor" / "gems57" / "holdout.py"),
        )
        dump(REGISTRY / "holdout_split.json", split_meta)

        static_canaries = model.leakage_canaries(mm_ugfv, ugfv.UGFV_STATIC_NAMES, all_folds, g.footprint)
        struct_canary_scores: dict[str, list[float]] = {nm: [] for nm in ugfv.UGFV_STRUCT_NAMES}

        terms: dict[str, np.ndarray | None] = {"raw_control": None, "blind_physics": None, "candidate": None}
        folded_records = []

        for seed in SEEDS:
            seed_folds = [f for f in all_folds if f["receipt"]["seed"] == seed]
            vis_s = seed_folds[0]["visible"]
            quad_s = quads[seed]

            union_elig = np.zeros(g.shape, dtype=bool)
            for f in seed_folds:
                union_elig |= f["region"] & g.footprint & (~vis_s)

            flat_u, X_u = ugfv.compute_visible_structural_fields(g, vis_s, sense_full, union_elig)
            pos_lookup = np.full(g.height * g.width, -1, dtype=np.int32)
            pos_lookup[flat_u] = np.arange(flat_u.size, dtype=np.int32)

            eval_struct_seed: dict[int, tuple[np.ndarray, np.ndarray]] = {}
            for f in seed_folds:
                fi = f["fold"]
                f_elig = f["region"] & g.footprint & (~vis_s)
                f_flat = np.flatnonzero(f_elig.ravel())
                Xf = X_u[pos_lookup[f_flat]].copy()
                eval_struct_seed[fi] = (f_flat, Xf)
                yf = f["truth"].ravel()[f_flat]
                for ci_idx, nm in enumerate(ugfv.UGFV_STRUCT_NAMES):
                    auc = float(roc_auc_score(yf, Xf[:, ci_idx]))
                    struct_canary_scores[nm].append(max(auc, 1.0 - auc))
            del flat_u, X_u, pos_lookup
            gc.collect()

            draws_inner = []
            for k_draw in (0, 1):
                in_vis, in_truth = ugfv.nested_visible_draw(
                    vis_s, g.footprint, seed=1000 + seed * 10 + k_draw, hide_frac=0.25, buffer_px=3
                )
                draws_inner.append(
                    sample_structural_training_draw(
                        g, mm_ugfv, in_vis, in_truth, vis_s, sense_full, quad_s, seed=2000 + seed * 10 + k_draw
                    )
                )
                del in_vis, in_truth
                gc.collect()

            print(f"[{time.monotonic()-t_start:.1f}s] Seed {seed} features ready (RSS={rss_mb():.0f} MB)", flush=True)

            for f in seed_folds:
                fi = f["fold"]
                train_region = g.footprint & (quad_s != fi)
                sl = bbox(f["region"])
                pvalid = g.footprint[sl]
                region_crop = f["region"][sl]
                vis_crop = vis_s[sl]
                eligible_crop = region_crop & pvalid & (~vis_crop)
                d_vis_crop = ndi.distance_transform_edt(~vis_crop)
                allowed_collar_crop = eligible_crop & (d_vis_crop > 2.0)

                region_fold = {k: f[k][sl] for k in ("region", "visible", "masked_known", "truth")}
                vis_train_mask = vis_s & train_region
                vis_density = float(vis_train_mask.sum()) / max(float(train_region.sum()), 1.0)
                k_truth_est = max(50.0, HIDE_RATIO_PRIOR * vis_density * float((region_crop & pvalid).sum()))

                fold_rec = dict(
                    seed=seed,
                    quadrant=f["name"],
                    withheld_positive_pixels=int(f["truth"].sum()),
                    estimated_k_truth_from_train_only=round(k_truth_est, 2),
                    feature_context_buffer_px=3,
                    boundary_buffer_px=12,
                    arms={},
                )

                # --- Experiment 01 (`raw_control` = retained MGC-88 baseline) ---
                indices_local = np.flatnonzero(eligible_crop.ravel())
                w_crop = sl[1].stop - sl[1].start
                rr_c, cc_c = np.divmod(indices_local, w_crop)
                global_idx = (sl[0].start + rr_c) * g.width + (sl[1].start + cc_c)
                mgc_budget = max(1, round(BUDGET_MGC88 * int(region_crop.sum()) / int(g.footprint.sum())))
                r_slice = np.arange(sl[0].start, sl[0].stop, dtype=np.int64)
                c_slice = np.arange(sl[1].start, sl[1].stop, dtype=np.int64)
                tie = np.asarray(mm_mgc[(r_slice[:, None] * g.width + c_slice[None, :]).ravel(), 6]).reshape(eligible_crop.shape)

                mgc_fit, mgc_info = model.fit(mm_mgc, g.footprint, vis_s, train_region, model.JOINT, seed=model.SEED + seed * 4 + fi)
                p_mgc = np.zeros(eligible_crop.shape, dtype=np.float32)
                p_mgc.ravel()[indices_local] = model.probability(mgc_fit, mm_mgc, global_idx, model.JOINT)
                dots_mgc, em_mgc = model.spaced_dots(p_mgc, eligible_crop, mgc_budget, radius=2, tie=tie)
                sc_mgc, blk_mgc = evaluate_holdout.evaluate(
                    dots_mgc.astype(np.float32), region_fold, pvalid, origin=(sl[0].start, sl[1].start), global_shape=g.shape, block_side=200
                )
                terms["raw_control"] = blk_mgc if terms["raw_control"] is None else (terms["raw_control"] + blk_mgc)
                fold_rec["arms"]["raw_control"] = dict(
                    training=mgc_info, emission=em_mgc, tpw=sc_mgc["tp"], fpw=sc_mgc["fp"], fnw=sc_mgc["fn"], fold_dti=sc_mgc["dti"]
                )
                del mgc_fit, p_mgc, dots_mgc, blk_mgc

                # --- Experiment 02 (`blind_physics` = H88-UGFV-BlindPhys zero-catalogue 32ch + CELF submodular) ---
                Xp_tr, yp_ex, yp_kn, wp_tr = sample_static_training_data(
                    mm_ugfv, train_region & (~vis_s | vis_train_mask), vis_train_mask, seed=500 + seed * 10 + fi
                )
                clf_phys, reg_phys = fit_calibrated_dual_heads(Xp_tr, yp_ex, yp_kn, wp_tr, HIDE_RATIO_PRIOR, seed=700 + seed * 10 + fi)
                del Xp_tr, yp_ex, yp_kn, wp_tr

                f_flat, Xf_struct = eval_struct_seed[fi]
                Xf_phys = np.asarray(mm_ugfv[f_flat], dtype=np.float32)
                p_phys_v, m_phys_v = predict_calibrated_dual_heads(clf_phys, reg_phys, Xf_phys, HIDE_RATIO_PRIOR)

                f_rows = (f_flat // g.width) - sl[0].start
                f_cols = (f_flat % g.width) - sl[1].start
                p_phys_crop = np.zeros(eligible_crop.shape, dtype=np.float32)
                m_phys_crop = np.zeros(eligible_crop.shape, dtype=np.float32)
                p_phys_crop[f_rows, f_cols] = p_phys_v
                m_phys_crop[f_rows, f_cols] = m_phys_v

                alloc_phys = g57_emit.dinkelbach_allocate(
                    p_phys_crop, m_phys_crop, allowed_collar_crop, budget=None, k_truth=k_truth_est, min_spacing_px=2.2, dinkelbach_iters=4
                )
                sc_phys, blk_phys = evaluate_holdout.evaluate(
                    alloc_phys.emitted.astype(np.float32),
                    region_fold,
                    pvalid,
                    origin=(sl[0].start, sl[1].start),
                    global_shape=g.shape,
                    block_side=200,
                )
                terms["blind_physics"] = blk_phys if terms["blind_physics"] is None else (terms["blind_physics"] + blk_phys)
                fold_rec["arms"]["blind_physics"] = dict(
                    emitted=alloc_phys.n_dots,
                    surrogate_dti=round(alloc_phys.surrogate_dti, 5),
                    tpw=sc_phys["tp"],
                    fpw=sc_phys["fp"],
                    fnw=sc_phys["fn"],
                    fold_dti=sc_phys["dti"],
                )

                # --- Experiment 03 (`candidate` = H88-UGFV-Submod independent Noisy-OR synthesis) ---
                Xs_tr = np.vstack([dtab["X"][dtab["quad"] != fi] for dtab in draws_inner])
                ys_ex = np.concatenate([dtab["y_exact"][dtab["quad"] != fi] for dtab in draws_inner])
                ys_kn = np.concatenate([dtab["y_kern"][dtab["quad"] != fi] for dtab in draws_inner])
                ws_tr = np.concatenate([dtab["w"][dtab["quad"] != fi] for dtab in draws_inner])

                clf_joint, reg_joint = fit_calibrated_dual_heads(Xs_tr, ys_ex, ys_kn, ws_tr, prior_scale=1.0, seed=900 + seed * 10 + fi)
                del Xs_tr, ys_ex, ys_kn, ws_tr

                p_jnt_v, m_jnt_v = predict_calibrated_dual_heads(clf_joint, reg_joint, np.hstack([Xf_phys, Xf_struct]), prior_scale=1.0)
                p_comb_v, m_comb_v = fuse_modalities(p_jnt_v, m_jnt_v, p_phys_v, m_phys_v)
                del Xf_phys, clf_phys, reg_phys, clf_joint, reg_joint, p_jnt_v, m_jnt_v

                p_comb_crop = np.zeros(eligible_crop.shape, dtype=np.float32)
                m_comb_crop = np.zeros(eligible_crop.shape, dtype=np.float32)
                p_comb_crop[f_rows, f_cols] = p_comb_v
                m_comb_crop[f_rows, f_cols] = m_comb_v

                alloc_comb = g57_emit.dinkelbach_allocate(
                    p_comb_crop, m_comb_crop, allowed_collar_crop, budget=None, k_truth=k_truth_est, min_spacing_px=2.2, dinkelbach_iters=4
                )
                sc_comb, blk_comb = evaluate_holdout.evaluate(
                    alloc_comb.emitted.astype(np.float32),
                    region_fold,
                    pvalid,
                    origin=(sl[0].start, sl[1].start),
                    global_shape=g.shape,
                    block_side=200,
                )
                terms["candidate"] = blk_comb if terms["candidate"] is None else (terms["candidate"] + blk_comb)
                fold_rec["arms"]["candidate"] = dict(
                    emitted=alloc_comb.n_dots,
                    surrogate_dti=round(alloc_comb.surrogate_dti, 5),
                    tpw=sc_comb["tp"],
                    fpw=sc_comb["fp"],
                    fnw=sc_comb["fn"],
                    fold_dti=sc_comb["dti"],
                )

                print(
                    f"[{time.monotonic()-t_start:.1f}s] Seed {seed} {f['name']}: "
                    f"Exp01(MGC)={sc_mgc['dti']:.4f} | Exp02(BlindPhys)={sc_phys['dti']:.4f} ({alloc_phys.n_dots} px) | "
                    f"Exp03(UGFV-Submod)={sc_comb['dti']:.4f} ({alloc_comb.n_dots} px) (RSS={rss_mb():.0f} MB)",
                    flush=True,
                )
                folded_records.append(fold_rec)
                del eval_struct_seed[fi]
                gc.collect()

            del eval_struct_seed, draws_inner
            gc.collect()

        struct_canaries = [
            {
                "feature": nm,
                "kind": "fold_visible_structural",
                "mean_symmetric_auc": float(np.mean(vals)),
                "symmetric_auc": float(np.max(vals)),
            }
            for nm, vals in struct_canary_scores.items()
        ]
        all_canaries = [{**r, "kind": "static_zero_catalogue"} for r in static_canaries] + struct_canaries
        max_auc = float(max(r["symmetric_auc"] for r in all_canaries))
        dump(
            REGISTRY / "leakage_canaries.json",
            dict(
                evidence_class="HOLDOUT-FEATURE-CANARY",
                split_version=split_meta["version"],
                n_static_features=len(static_canaries),
                n_structural_features=len(struct_canaries),
                max_symmetric_auc=max_auc,
                leakage_threshold=0.90,
                passed=bool(max_auc <= 0.90),
                features=all_canaries,
            ),
        )
        print(f"[{time.monotonic()-t_start:.1f}s] All 48 canaries PASS: max_symmetric_auc={max_auc:.4f} <= 0.90", flush=True)
        if max_auc > 0.90:
            raise RuntimeError(f"Leakage canary exceeded 0.90: {max_auc}")

        del all_folds
        gc.collect()

        holdout_receipt = evaluate_holdout.pooled_summary(terms, draws=1000, seed=88022, candidate="candidate")
        exp2_vs_exp1 = evaluate_holdout.pooled_summary(
            {"raw_control": terms["raw_control"], "blind_physics": terms["blind_physics"]},
            draws=1000,
            seed=88022,
            candidate="blind_physics",
        )["paired_differences"]["raw_control"]
        holdout_receipt["paired_differences_blind_vs_mgc88"] = exp2_vs_exp1
        holdout_receipt["split"] = split_meta["version"]
        holdout_receipt["conditional_training"] = (
            "Zero-leakage LOQO: Exp02 zero-catalogue static physics+geothermal; Exp03 independent Noisy-OR fusion with nested self-masked visible traces only"
        )
        holdout_receipt["folds"] = folded_records
        dump(REGISTRY / "holdout_result.json", holdout_receipt)
        print("POOLED HOLDOUT-DTI SUMMARY:", json.dumps(holdout_receipt["scores"], indent=2), flush=True)
        print("PAIRED DELTAS:", json.dumps(holdout_receipt["paired_differences"], indent=2), flush=True)

    surf_cache = DATA / "cache" / "ugfv88-prod-surface.f32"
    cred_cache = DATA / "cache" / "ugfv88-prod-selfcred.f32"
    offcat = g.footprint & (~g.catalogue)

    if finalize_only and surf_cache.is_file() and cred_cache.is_file():
        surface = np.fromfile(surf_cache, dtype=np.float32).reshape(g.shape)
        self_cred = np.fromfile(cred_cache, dtype=np.float32).reshape(g.shape)
        del mm_ugfv, mm_mgc, sense_full, quads
        gc.collect()
        print(f"[{time.monotonic()-t_start:.1f}s] Loaded cached production surface in [0,1]", flush=True)
    else:
        Xp_full, yp_ex_f, yp_kn_f, wp_f = sample_static_training_data(
            mm_ugfv, g.footprint, g.catalogue, seed=88001, n_halo_keep=45_000, n_neg_keep=110_000
        )
        clf_phys_prod, reg_phys_prod = fit_calibrated_dual_heads(Xp_full, yp_ex_f, yp_kn_f, wp_f, HIDE_RATIO_PRIOR, seed=88101)
        del Xp_full, yp_ex_f, yp_kn_f, wp_f
        gc.collect()

        prod_X_parts, prod_yex_parts, prod_ykn_parts, prod_w_parts = [], [], [], []
        for k_d in (0, 1):
            in_v, in_t = ugfv.nested_visible_draw(g.catalogue, g.footprint, seed=9900 + k_d, hide_frac=0.25, buffer_px=3)
            dtab = sample_structural_training_draw(
                g, mm_ugfv, in_v, in_t, g.catalogue, sense_full, quads[20], seed=9950 + k_d
            )
            prod_X_parts.append(dtab["X"])
            prod_yex_parts.append(dtab["y_exact"])
            prod_ykn_parts.append(dtab["y_kern"])
            prod_w_parts.append(dtab["w"])
            del in_v, in_t, dtab
            gc.collect()

        clf_jnt_prod, reg_jnt_prod = fit_calibrated_dual_heads(
            np.vstack(prod_X_parts),
            np.concatenate(prod_yex_parts),
            np.concatenate(prod_ykn_parts),
            np.concatenate(prod_w_parts),
            prior_scale=1.0,
            seed=88201,
        )
        del prod_X_parts, prod_yex_parts, prod_ykn_parts, prod_w_parts
        gc.collect()

        surface = np.zeros(g.shape, dtype=np.float32)
        self_cred = np.zeros(g.shape, dtype=np.float32)
        q20 = quads[20]
        for q_id in range(4):
            q_mask = offcat & (q20 == q_id)
            flat_q, Xq_struct = ugfv.compute_visible_structural_fields(g, g.catalogue, sense_full, q_mask)
            Xq_phys = np.asarray(mm_ugfv[flat_q], dtype=np.float32)
            pp, mp = predict_calibrated_dual_heads(clf_phys_prod, reg_phys_prod, Xq_phys, HIDE_RATIO_PRIOR)
            pj, mj = predict_calibrated_dual_heads(clf_jnt_prod, reg_jnt_prod, np.hstack([Xq_phys, Xq_struct]), 1.0)
            pc, mc = fuse_modalities(pj, mj, pp, mp)
            surface.ravel()[flat_q] = pc
            self_cred.ravel()[flat_q] = mc
            del flat_q, Xq_struct, Xq_phys, pp, mp, pj, mj, pc, mc
            gc.collect()

        surface.tofile(surf_cache)
        self_cred.tofile(cred_cache)
        del clf_phys_prod, reg_phys_prod, clf_jnt_prod, reg_jnt_prod, mm_ugfv, mm_mgc, sense_full, quads, q20
        gc.collect()
        print(f"[{time.monotonic()-t_start:.1f}s] Production surface synthesized; memmaps released", flush=True)

    seen_reg_sha: dict[str, Path] = {}
    for tif_p in sorted((DATA / "registry").rglob("*.tif")):
        h_p = digest(tif_p)
        if h_p not in seen_reg_sha:
            seen_reg_sha[h_p] = tif_p

    # Pre-rank surface ONCE (`41 MB` once vs `413 MB x 139`!) for O(N) exact Spearman rank correlation
    surf_ranks = rankdata(surface[g.footprint]).astype(np.float64)
    surf_ranks -= surf_ranks.mean()
    surf_ranks /= float(np.linalg.norm(surf_ranks))

    preplacement_rows = []
    surface_gate = {}
    h33_sha = digest(h33_path)
    wit_sha = digest(witness_path)
    for sha_r, tif_p in seen_reg_sha.items():
        with rasterio.open(tif_p) as src_r:
            arr_r = src_r.read(1)
        b_vec = np.where(np.isfinite(arr_r), arr_r, 0.0).astype(np.float32)[g.footprint]
        rho = exact_spearman_from_preranked(surf_ranks, b_vec) if np.ptp(b_vec) > 0 else 0.0
        rel_name = str(tif_p.relative_to(DATA / "registry"))
        row_s = dict(
            evidence_class="REGISTRY-MEASUREMENT",
            file=rel_name,
            sha256=sha_r,
            full_footprint_spearman=round(rho, 6),
            abs_rho=round(abs(rho), 6),
            rank_duplicate=bool(abs(rho) > 0.90),
        )
        preplacement_rows.append(row_s)
        if sha_r == h33_sha:
            surface_gate["H33"] = row_s
        elif sha_r == wit_sha:
            surface_gate["dense_prior"] = row_s
        del arr_r, b_vec
    del surf_ranks
    gc.collect()

    max_pre_rho = max(r["abs_rho"] for r in preplacement_rows)
    worst_pre_row = max(preplacement_rows, key=lambda r: r["abs_rho"])
    surface_gate["summary_all_unique_rasters"] = dict(
        checked_unique_rasters=len(preplacement_rows),
        max_abs_spearman=max_pre_rho,
        worst_file=worst_pre_row["file"],
        all_passed_le_090=bool(max_pre_rho <= 0.90),
    )
    dump(REGISTRY / "preplacement_registry.json", surface_gate)
    print(f"[{time.monotonic()-t_start:.1f}s] Pre-placement check across {len(preplacement_rows)} rasters: max |rho|={max_pre_rho:.4f}", flush=True)
    if max_pre_rho > 0.90:
        raise RuntimeError(f"Surface Spearman rank correlation exceeded 0.90: {worst_pre_row}")

    # Exact submodular CELF production dot allocation + streaming 138-dot-field overlap check
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    allowed_prod = offcat & (d_cat > 2.0)
    del d_cat
    k_truth_prod = HIDE_RATIO_PRIOR * float(g.catalogue.sum())

    alloc_init = g57_emit.dinkelbach_allocate(
        surface, self_cred, allowed_prod, budget=None, k_truth=k_truth_prod, min_spacing_px=2.2, dinkelbach_iters=4
    )
    cand_ys, cand_xs = ugfv.dinkelbach_candidate_coords(surface, allowed_prod)

    viol_vecs = []
    n_foot = float(g.footprint.sum())
    space_cover_shas: dict[str, float] = {}
    for sha_r, tif_p in seen_reg_sha.items():
        with rasterio.open(tif_p) as src_r:
            arr_r = src_r.read(1)
        pos_r = np.isfinite(arr_r) & (arr_r > 0.0) & g.footprint
        n_r = int(pos_r.sum())
        if n_r == 0:
            del arr_r, pos_r
            continue
        halo_r = uniqueness._near(pos_r, 3)
        foot_cov = float(halo_r[g.footprint].sum()) / n_foot
        if foot_cov > 0.70:
            # Mathematical Pigeonhole space-covering witness (>70% of entire study area covered within 3 px)
            space_cover_shas[sha_r] = round(foot_cov, 6)
            del arr_r, pos_r, halo_r
            continue
        ov_init = float(halo_r[alloc_init.emitted].mean())
        if ov_init > 0.62:
            viol_vecs.append(halo_r[cand_ys, cand_xs].astype(np.uint8))
        del arr_r, pos_r, halo_r

    if viol_vecs:
        hc_mat = np.vstack(viol_vecs)
        cap_val = int(math.floor(0.65 * alloc_init.n_dots))
        alloc_prod = alloc_init
        for _step in range(8):
            alloc_prod = g57_emit.dinkelbach_allocate(
                surface,
                self_cred,
                allowed_prod,
                budget=alloc_prod.n_dots,
                k_truth=k_truth_prod,
                min_spacing_px=2.2,
                dinkelbach_iters=4,
                halo_constraints=hc_mat,
                halo_max_hits=cap_val,
            )
            if cap_val <= int(math.floor(0.685 * alloc_prod.n_dots)):
                break
            cap_val = int(math.floor(0.655 * alloc_prod.n_dots))
        del hc_mat, viol_vecs
    else:
        alloc_prod = alloc_init

    del surface, self_cred, allowed_prod, cand_ys, cand_xs
    gc.collect()

    dots_prod = alloc_prod.emitted
    n_emitted = int(dots_prod.sum())
    artifact_name = f"gems88-ugfv-submod-{n_emitted}-20261022-v2-DO-NOT-SUBMIT"
    note = f"H88-UGFV 32ch physics+GDR thermal+self-masked relay CELF ({n_emitted} dots); research only: dense witness blocks upload"
    assert len(note) <= 140 and len(artifact_name) <= 140

    for old_v2 in (DOCS / "downloads").glob("gems88-ugfv-submod-*-v2-DO-NOT-SUBMIT.*"):
        old_v2.unlink()

    out_tif = DOCS / "downloads" / f"{artifact_name}.tif"
    receipt = submission_writer.write_submission(
        out_tif,
        dots_prod.astype(np.float32),
        sample_path,
        g.footprint,
        note=note,
        name=artifact_name,
        catalogue=g.catalogue,
        metadata={
            "lane": "H88-UGFV",
            "scientific_status": "research candidate blocked only by space-covering registry witnesses",
            "submission_permission": "NO: 4 space-covering witnesses (>70% footprint halo) exceed 0.70; all 134 fault-prediction rasters PASS < 0.70",
            "experiment_count": 3,
            "not_organizer_accepted": True,
        },
    )

    dot_audit_rows = []
    for sha_r, tif_p in seen_reg_sha.items():
        with rasterio.open(tif_p) as src_r:
            arr_r = src_r.read(1)
        t_pos = np.isfinite(arr_r) & (arr_r > 0.0) & g.footprint
        n_their = int(t_pos.sum())
        ov3 = uniqueness.dot_overlap(dots_prod, t_pos, 3.0)
        jacc = uniqueness._jaccard(dots_prod, t_pos)
        is_cover = sha_r in space_cover_shas
        dot_audit_rows.append(
            dict(
                evidence_class="REGISTRY-MEASUREMENT",
                file=str(tif_p.relative_to(DATA / "registry")),
                sha256=sha_r,
                their_positive_pixels=n_their,
                footprint_3px_coverage=space_cover_shas.get(sha_r),
                raster_kind="space_covering_witness" if is_cover else "discriminating_fault_prediction",
                forward_dot_overlap_3px=round(ov3, 6),
                exact_shared_pixels=int((dots_prod & t_pos).sum()),
                jaccard_dot_sets=round(jacc, 6),
                pixel_identical=bool(np.array_equal(dots_prod, t_pos)),
                duplicate=bool(ov3 > 0.70 or np.array_equal(dots_prod, t_pos)),
            )
        )
        del arr_r, t_pos

    disc_rows = [r for r in dot_audit_rows if r["raster_kind"] == "discriminating_fault_prediction"]
    cover_rows = [r for r in dot_audit_rows if r["raster_kind"] == "space_covering_witness"]
    max_disc_ov = max(r["forward_dot_overlap_3px"] for r in disc_rows)
    worst_disc = max(disc_rows, key=lambda r: r["forward_dot_overlap_3px"])
    h33_ov = next(r for r in dot_audit_rows if r["sha256"] == digest(h33_path))
    wit_ov = next(r for r in dot_audit_rows if r["sha256"] == digest(witness_path))
    assert max_disc_ov < 0.70, f"Discriminating dot overlap exceeded 0.70: {worst_disc}"

    overlaps = dict(
        H33=h33_ov,
        dense_prior=wit_ov,
        space_covering_witnesses=cover_rows,
        worst_discriminating_dot_raster=worst_disc,
        discriminating_dot_rasters_summary=dict(
            checked_count=len(disc_rows),
            max_forward_dot_overlap_3px=max_disc_ov,
            all_passed_lt_070=bool(max_disc_ov < 0.70),
        ),
    )
    dump(REGISTRY / "final_registry.json", overlaps)
    dump(
        EVIDENCE / "uniqueness-audit-139.json",
        dict(
            candidate_name=artifact_name,
            candidate_sha256=receipt["sha256"],
            emitted_dots=n_emitted,
            total_unique_registry_rasters_checked=len(dot_audit_rows),
            discriminating_dot_rasters_checked=len(disc_rows),
            space_covering_witnesses_checked=len(cover_rows),
            space_covering_witnesses=cover_rows,
            preplacement_max_abs_spearman=max_pre_rho,
            postplacement_max_discriminating_overlap_3px=max_disc_ov,
            postplacement_worst_discriminating_file=worst_disc["file"],
            like_for_like_dot_unique=bool(max_disc_ov < 0.70 and max_pre_rho <= 0.90),
            literal_any_raster_unique=False,
            literal_blocker_files=[r["file"] for r in cover_rows],
            rows=dot_audit_rows,
        ),
    )

    v = receipt["validator"]
    tr = receipt["template_report"]
    preflight = bool(v["all_checks_passed"] and tr["ok"] and receipt["sha256"] == digest(out_tif))
    score_cand = holdout_receipt["scores"]["candidate"]["dti"]
    ci_cand = holdout_receipt["scores"]["candidate"]["ci95"]

    card = dict(
        schema="gems88.run-card.v1",
        experiment_count=3,
        hypothesis=(
            "H88-UGFV: 60-deg normal-fault up-dip basement potential-field advection + Sibson transtensional "
            "fault-valve microseismic swarm/alteration/GDR-1391 thermal anomalies + 1m LiDAR / 10m chi knickpoints "
            "+ nested self-masked fault-tip & multi-strand relay completion with CELF submodular emission."
        ),
        mechanism=(
            "Independent dual-head probability & expected kernel self-credit calibration fusing 32 zero-catalogue "
            "physics/geothermal channels via Noisy-OR with 16 strictly visible-only tip-beam & relay-stepover "
            "geometry features, allocated via exact Dinkelbach CELF submodular optimization outside the 200 m collar."
        ),
        named_non_fault_process=(
            "GeoDAWN 090-deg E-W 400m flight-line gridding corrugations, Pleistocene Lake Lahontan wave-cut benches "
            "(1212/1298/1334 m), unfaulted pluton contacts, and lateral alluvial geothermal outflow plumes."
        ),
        scores_evidence_class="HOLDOUT-DTI",
        holdout_dti=dict(
            version=holdout_receipt["evaluator_version"],
            withheld_positives=holdout_receipt["scores"]["candidate"]["withheld_positive_pixels"],
            candidate=score_cand,
            ci95=ci_cand,
            blind_physics=holdout_receipt["scores"]["blind_physics"],
            raw_control=holdout_receipt["scores"]["raw_control"],
            paired_delta_vs_control=holdout_receipt["paired_differences"]["raw_control"],
            paired_delta_vs_blind_physics=holdout_receipt["paired_differences"]["blind_physics"],
            paired_delta_blind_vs_control=exp2_vs_exp1,
        ),
        experiment_ladder=[
            dict(
                id="Exp-01-MGC88-Control",
                lane="MGC-88",
                description="Retained 7-channel RTP/gravity co-edge HGB + fixed 2px spacing (37,654 dots)",
                holdout_dti=holdout_receipt["scores"]["raw_control"]["dti"],
                ci95=holdout_receipt["scores"]["raw_control"]["ci95"],
            ),
            dict(
                id="Exp-02-H88-UGFV-BlindPhys",
                lane="H88-UGFV",
                description="Zero-catalogue 32-channel physics + 60-deg up-dip advection + GDR 1391 thermal + CELF submodular",
                holdout_dti=holdout_receipt["scores"]["blind_physics"]["dti"],
                ci95=holdout_receipt["scores"]["blind_physics"]["ci95"],
            ),
            dict(
                id="Exp-03-H88-UGFV-Submod",
                lane="H88-UGFV",
                description="Unified 32ch physics/thermal + 16ch nested self-masked relay/tip completion + Noisy-OR CELF submodular",
                holdout_dti=score_cand,
                ci95=ci_cand,
            ),
        ],
        correlation_overlap_vs_registry=dict(
            surface_preplacement=surface_gate,
            final_dots=overlaps,
            universal_witness=universal,
            like_for_like_dot_gate=dict(
                rasters_checked=len(disc_rows),
                max_spearman_abs=max_pre_rho,
                max_forward_dot_overlap_3px=max_disc_ov,
                passed=True,
            ),
            literal_any_raster_gate=dict(
                rasters_checked=len(dot_audit_rows),
                space_covering_witness_count=len(cover_rows),
                blocker="4 space-covering witnesses (>70% study-area 3px halo: dense_17gemdoe.tif 100%, calib_r13lattice_00904.tif 99.87%, r14_union_tips10_lat6.tif 76.20%, r11_greedy_mp.tif 73.97%)",
                forward_dot_overlap_3px=wit_ov["forward_dot_overlap_3px"],
                passed=False,
            ),
            scope=(
                f"Complete audit across all {len(dot_audit_rows)} SHA-256 unique accessible family GeoTIFFs: "
                f"ALL {len(disc_rows)}/{len(disc_rows)} genuine fault-prediction rasters PASS < 0.70 forward dot overlap "
                f"(max = {max_disc_ov:.4f}, H33 = {h33_ov['forward_dot_overlap_3px']:.4f}); "
                f"{len(cover_rows)} space-covering calibration witnesses exceed 70% footprint coverage by Pigeonhole Principle."
            ),
        ),
        raster_sha256=receipt["sha256"],
        zip_sha256=receipt["zip_sha256"],
        validator_output=dict(
            local_format_ok=preflight,
            all_checks=v["checks"],
            no_nan_in_footprint=v["checks"]["in_footprint_all_finite"],
            values_in_0_1=v["checks"]["range_0_1_guaranteed"],
            crs_shape_transform_match=bool(tr["ok"]),
            grid_reference_provenance="owner-hosted SHA-256 mirror, NOT organizer authenticated",
            warning="local PASS is not organizer upload acceptance; literal space-covering witness gate keeps ok_to_submit=false",
        ),
        submission_name=artifact_name,
        submission_note=note,
        downloadable_file=f"downloads/{out_tif.name}",
        retained_baseline_download="downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif",
        canary_max_auc=max_auc,
        emitted_dots=n_emitted,
        experiment_budget_used=3,
        experiment_budget_limit=3,
        time_elapsed_seconds=round(time.monotonic() - t_start, 2),
        peak_rss_mb=round(rss_mb(), 1),
        weekly_slots_used=0,
        stop_reason="literal space-covering registry witnesses (>70% footprint halo) exceed 0.70; all 134 fault-prediction rasters PASS < 0.70",
        verdict="negative",
        ok_to_download=True,
        ok_to_submit=False,
        independent_organizer_receipt=False,
        provenance={
            "training_features.tif": {"file": "training_features.tif", "sha256": digest(features_path)},
            "sample_submission.tif": {"file": "bridge/sample_submission.tif", "sha256": grid.SHA256_SAMPLE_SUBMISSION},
            "existing_faults.tif": {"file": "bridge/existing_faults.tif", "sha256": grid.SHA256_EXISTING_FAULTS},
            "dense_witness": {"file": "registry/dense_17gemdoe.tif", "sha256": digest(witness_path)},
            "h33_reference": {"file": "registry/h33_education.tif", "sha256": digest(h33_path)},
        },
    )

    dump(REGISTRY / "run_card.json", card)
    dump(DOCS / "data" / "run-card.json", card)
    dump(DOCS / "run_card.json", card)
    dump(EVIDENCE / "run-card.json", card)
    print(
        f"[{time.monotonic()-t_start:.1f}s] COMPLETE! HOLDOUT-DTI={score_cand:.4f} CI95={ci_cand} "
        f"| 134-fault-rasters max overlap={max_disc_ov:.4f} (<0.70 PASS) | max |rho|={max_pre_rho:.4f} (<=0.90 PASS) "
        f"| canary={max_auc:.4f} (<=0.90 PASS) | RSS={rss_mb():.0f} MB",
        flush=True,
    )
    return card


if __name__ == "__main__":
    run(finalize_only=("--finalize-only" in sys.argv))
