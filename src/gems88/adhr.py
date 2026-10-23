"""Memory-bounded (<550 MB RSS) ADHR-88 & CGO-88 training, inference & emission.

Never materializes a full 5.17M x 67 in-memory array: stores visible structural
planes as disk-backed float32 ``np.memmap`` files, gathers only sampled training
rows (~245k rows = 64 MB), and evaluates test regions in 150k-row chunks (40 MB).
"""
from __future__ import annotations

import csv
import gc
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from gems57 import damagezone_envelope, emit, relay_bend_anatomy
from gems57.strand_orientation import magnetic_geometry

VIS_STRUCT_FEATURES: tuple[str, ...] = tuple(relay_bend_anatomy.ALL_RELAY_BEND_FEATURES) + ("d_over_w",)


def build_sense_raster(segments_csv: Path, grid) -> np.ndarray:
    cache_dir = segments_csv.parents[2] / ".cache/gems88"
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(segments_csv.read_bytes()).hexdigest()[:16]
    cpath = cache_dir / f"sense_raster_{digest}.npy"
    if cpath.exists():
        return np.load(cpath)

    sense_map = {"N": 1, "RL": 2, "LL": 3}
    out = np.zeros(grid.shape, dtype=np.int8)
    inv_tf = ~grid.transform
    h, w = grid.shape
    with segments_csv.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = sense_map.get((row.get("sense") or "").strip(), 0)
            if code == 0:
                continue
            try:
                x0, y0 = float(row["x0"]), float(row["y0"])
                x1, y1 = float(row["x1"]), float(row["y1"])
            except (KeyError, ValueError):
                continue
            c0, r0 = inv_tf * (x0, y0)
            c1, r1 = inv_tf * (x1, y1)
            nsteps = max(2, int(np.hypot(c1 - c0, r1 - r0) * 1.5) + 1)
            cs = np.floor(np.linspace(c0, c1, nsteps)).astype(np.int32)
            rs = np.floor(np.linspace(r0, r1, nsteps)).astype(np.int32)
            ok = (rs >= 0) & (rs < h) & (cs >= 0) & (cs < w)
            out[rs[ok], cs[ok]] = code
    out = ndi.maximum_filter(out, size=3)
    out[~grid.catalogue] = 0
    np.save(cpath, out)
    return out


def compute_scarp_fields(det_elev_band: np.ndarray, footprint: np.ndarray, cache_dir: Path) -> dict[str, np.ndarray]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(np.ascontiguousarray(det_elev_band).tobytes()).hexdigest()[:16]
    cpath = cache_dir / f"scarp_fields_{digest}.npz"
    if cpath.exists():
        data = np.load(cpath)
        return {k: data[k] for k in data.files}
    fields = magnetic_geometry(det_elev_band, footprint)
    np.savez(cpath, **fields)
    return fields


def compute_visible_struct_fp(
    grid,
    visible: np.ndarray,
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
    tag: str,
) -> tuple[np.memmap, np.ndarray, np.ndarray]:
    """Compute disk-backed ``(N_fp, 22)`` float32 memmap of visible-only anatomy."""
    vis = np.asarray(visible, dtype=bool)
    sense_vis = np.where(vis, sense_src, 0).astype(np.int8)
    vis_hash = hashlib.sha256(np.packbits(vis).tobytes() + sense_vis[vis].tobytes()).hexdigest()[:16]
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / f"vis_struct_{tag}_{vis_hash}.dat"
    aux_path = cache_dir / f"vis_struct_{tag}_{vis_hash}.npz"
    n_fp = int(grid.footprint.sum())
    n_cols = len(relay_bend_anatomy.ALL_RELAY_BEND_FEATURES)

    if dat_path.exists() and aux_path.exists():
        aux = np.load(aux_path)
        return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), aux["d_vis"], aux["comp_len"]

    dummy_hidden = np.zeros(grid.shape, dtype=bool)
    rb = relay_bend_anatomy.build_relay_bend_geometry(
        grid,
        vis,
        dummy_hidden,
        grid.footprint,
        sense_vis,
        scarp_fields,
        cache_dir,
        key=f"{tag}_{vis_hash}",
    )
    ys_fp, xs_fp = np.nonzero(grid.footprint)
    idx_map = np.full(grid.shape, -1, dtype=np.int32)
    idx_map[ys_fp, xs_fp] = np.arange(n_fp, dtype=np.int32)

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    mm[:] = 0.0
    for start in range(0, len(rb.rows), 250_000):
        sl = slice(start, min(start + 250_000, len(rb.rows)))
        dest = idx_map[rb.rows[sl], rb.cols[sl]]
        mm[dest] = np.asarray(rb.X[sl], dtype=np.float32)
    mm.flush()

    d_vis_fp = np.asarray(mm[:, 0], dtype=np.float32).copy()
    comp_len_fp = np.expm1(np.maximum(np.asarray(mm[:, 4], dtype=np.float32), 0.0)).astype(np.float32)
    del rb, mm, idx_map
    (cache_dir / f"relay_bend_{tag}_{vis_hash}.npy").unlink(missing_ok=True)
    gc.collect()
    np.savez(aux_path, d_vis=d_vis_fp, comp_len=comp_len_fp)
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), d_vis_fp, comp_len_fp


def gather_columns(sources: list[np.ndarray], idx: np.ndarray) -> np.ndarray:
    """Gather rows ``idx`` from multiple memmaps/arrays without materializing 5.17M rows."""
    parts = []
    for src in sources:
        arr = np.asarray(src[idx], dtype=np.float32)
        if arr.ndim == 1:
            arr = arr[:, None]
        parts.append(arr)
    return np.hstack(parts) if len(parts) > 1 else parts[0]


def _fit_dual_expectation_models(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    seed: int,
    max_zero_neg: int = 140_000,
    n_ensemble: int = 1,
) -> tuple[list[HistGradientBoostingClassifier], list[HistGradientBoostingRegressor]]:
    ys_fp, xs_fp = np.nonzero(fp_mask)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int8)
    y_kern_grid = np.clip(1.0 - ndi.distance_transform_edt(~pos_grid) / 3.0, 0.0, 1.0).astype(np.float32)
    y_kern_all = y_kern_grid[ys_fp, xs_fp]
    del y_kern_grid

    dom_idx = np.flatnonzero(domain_fp)
    y_k = y_kern_all[dom_idx]
    near_sel = y_k > 0.0
    near_idx = dom_idx[near_sel]
    zero_idx = dom_idx[~near_sel]

    rng = np.random.default_rng(seed)
    if zero_idx.size > max_zero_neg:
        sub_zero = np.sort(rng.choice(zero_idx, size=max_zero_neg, replace=False))
        w_zero = float(zero_idx.size) / float(max_zero_neg)
    else:
        sub_zero = zero_idx
        w_zero = 1.0

    # Merge in ascending row order for sequential disk streaming, then permute in RAM
    train_idx = np.concatenate([near_idx, sub_zero])
    weights = np.concatenate([
        np.ones(near_idx.size, dtype=np.float64),
        np.full(sub_zero.size, w_zero, dtype=np.float64),
    ])
    seq = np.argsort(train_idx)
    train_idx = train_idx[seq]
    weights = weights[seq]
    X_tr = gather_columns(sources, train_idx)
    yc_tr = y_cell_all[train_idx]
    yk_tr = y_kern_all[train_idx]

    perm = rng.permutation(len(train_idx))
    X_tr = X_tr[perm]
    yc_tr = yc_tr[perm]
    yk_tr = yk_tr[perm]
    weights = weights[perm]

    clfs: list[HistGradientBoostingClassifier] = []
    regs: list[HistGradientBoostingRegressor] = []
    for k in range(n_ensemble):
        clf = HistGradientBoostingClassifier(
            max_iter=115,
            learning_rate=0.075,
            max_leaf_nodes=47,
            min_samples_leaf=80,
            l2_regularization=4.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=12,
            random_state=seed + 101 * k,
        )
        clf.fit(X_tr, yc_tr, sample_weight=weights)
        clfs.append(clf)

        reg = HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=115,
            learning_rate=0.075,
            max_leaf_nodes=47,
            min_samples_leaf=80,
            l2_regularization=4.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=12,
            random_state=seed + 211 * k,
        )
        reg.fit(X_tr, yk_tr, sample_weight=weights)
        regs.append(reg)
    del X_tr
    return clfs, regs


def _predict_dual_chunked(
    clfs: list[HistGradientBoostingClassifier],
    regs: list[HistGradientBoostingRegressor],
    sources: list[np.ndarray],
    act_idx: np.ndarray,
    chunk: int = 160_000,
) -> tuple[np.ndarray, np.ndarray]:
    n = act_idx.size
    p_out = np.empty(n, dtype=np.float32)
    m_out = np.empty(n, dtype=np.float32)
    for start in range(0, n, chunk):
        sl = slice(start, min(start + chunk, n))
        X_sub = gather_columns(sources, act_idx[sl])
        p_acc = np.zeros(len(X_sub), dtype=np.float64)
        m_acc = np.zeros(len(X_sub), dtype=np.float64)
        for clf, reg in zip(clfs, regs):
            p_acc += clf.predict_proba(X_sub)[:, 1]
            m_acc += np.clip(reg.predict(X_sub), 0.0, 1.0)
        p_c = (p_acc / len(clfs)).astype(np.float32)
        p_out[sl] = p_c
        m_out[sl] = np.clip(m_acc / len(regs), p_c, 1.0).astype(np.float32)
    return p_out, m_out


def _logit(p: np.ndarray) -> np.ndarray:
    c = np.clip(np.asarray(p, dtype=np.float32), 1e-6, 1.0 - 1e-6)
    return np.log(c / (1.0 - c))


def _expit(z: np.ndarray) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-np.clip(z, -20.0, 20.0)))).astype(np.float32)


def _fuse_log_odds(
    p_full_raw: np.ndarray,
    m_full_raw: np.ndarray,
    p_phys_raw: np.ndarray,
    m_phys_raw: np.ndarray,
    k_target: float,
    beta_phys: float = 0.35,
    pi_unmapped: float = 0.50,
) -> tuple[np.ndarray, np.ndarray]:
    """Marginalize over latent mapping completeness M in {0 (unmapped basin), 1 (mapped relay)}:
    P(F=1 | X) = (1 - pi_unmapped) * P_poe(F=1 | X_phys, X_vis) + pi_unmapped * P(F=1 | X_phys).
    Preserves exact total expectation k_target and pointwise self-credit m* >= p*.
    """
    mean_p = float(np.mean(p_phys_raw, dtype=np.float64))
    mean_m = float(np.mean(m_phys_raw, dtype=np.float64))
    p_poe = _expit(_logit(p_full_raw) + np.float32(beta_phys) * (_logit(p_phys_raw) - np.float32(math.log(max(mean_p, 1e-7) / (1.0 - min(mean_p, 1.0 - 1e-7))))))
    m_poe = _expit(_logit(m_full_raw) + np.float32(beta_phys) * (_logit(m_phys_raw) - np.float32(math.log(max(mean_m, 1e-7) / (1.0 - min(mean_m, 1.0 - 1e-7))))))

    # Calibrate both branches to the same total expectation k_target before convex mixing
    norm_p_joint = float(k_target) / max(float(np.sum(p_poe, dtype=np.float64)), 1e-6)
    m_target_joint = float(np.sum(m_full_raw, dtype=np.float64)) * (float(k_target) / max(float(np.sum(p_full_raw, dtype=np.float64)), 1e-6))
    norm_m_joint = m_target_joint / max(float(np.sum(m_poe, dtype=np.float64)), 1e-6)
    p_joint = np.clip(p_poe * np.float32(norm_p_joint), 0.0, 1.0)
    m_joint = np.clip(m_poe * np.float32(norm_m_joint), p_joint, 1.0)

    norm_p_phys = float(k_target) / max(float(np.sum(p_phys_raw, dtype=np.float64)), 1e-6)
    p_phys_cal = np.clip(p_phys_raw * np.float32(norm_p_phys), 0.0, 1.0)
    m_phys_cal = np.clip(m_phys_raw * np.float32(norm_p_phys), p_phys_cal, 1.0)

    w0 = np.float32(1.0 - pi_unmapped)
    w1 = np.float32(pi_unmapped)
    p_final = np.clip(w0 * p_joint + w1 * p_phys_cal, 0.0, 1.0).astype(np.float32)
    m_final = np.clip(w0 * m_joint + w1 * m_phys_cal, p_final, 1.0).astype(np.float32)
    return p_final, m_final


def scatter_fp(values_sub: np.ndarray, ys: np.ndarray, xs: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    out = np.zeros(shape, dtype=np.float32)
    out[ys, xs] = values_sub
    return out


def predict_cgo_fold(
    grid,
    X_cgo_view: np.ndarray,
    visible: np.ndarray,
    train_quad_mask: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, dict]:
    if np.any(train_quad_mask & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training mask intersects test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    dom_train_fp = train_quad_mask[ys_fp, xs_fp]
    clfs, regs = _fit_dual_expectation_models(
        [X_cgo_view], dom_train_fp, visible & train_quad_mask, fp, seed=seed, n_ensemble=1
    )

    n_vis_tr = max(float((visible & train_quad_mask).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    p_raw, m_raw = _predict_dual_chunked(clfs, regs, [X_cgo_view], act_idx)

    scale_p = float(k_est) / max(float(p_raw.sum()), 1e-6)
    p_cal = np.clip(p_raw * scale_p, 0.0, 1.0).astype(np.float32)
    m_cal = np.clip(m_raw * hid_ratio, p_cal, 1.0).astype(np.float32)

    p_grid = scatter_fp(p_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_grid = scatter_fp(m_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc = emit.dinkelbach_allocate(
        p_grid,
        m_grid,
        allowed,
        budget=None,
        k_truth=k_est,
        min_spacing_px=2.05,
        dinkelbach_iters=6,
    )
    return alloc.emitted.astype(np.float32), p_grid, {
        "n_dots": int(alloc.n_dots),
        "k_truth_est": float(k_est),
        "surrogate_dti": float(alloc.surrogate_dti),
    }


def predict_adhr_fold(
    grid,
    X_phys_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, dict]:
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)

    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
    full_sources = [X_phys_mm, X_vis22_mm, d_over_w_fp]

    dom_phys_tr = train_regions[ys_fp, xs_fp]
    clfs_phys, regs_phys = _fit_dual_expectation_models(
        [X_phys_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 17, n_ensemble=1
    )

    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]
    clfs_full, regs_full = _fit_dual_expectation_models(
        full_sources, dom_struct_tr, train_truth, fp, seed=seed + 53, n_ensemble=1
    )

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])

    p_phys_raw, m_phys_raw = _predict_dual_chunked(clfs_phys, regs_phys, [X_phys_mm], act_idx)
    p_full_raw, m_full_raw = _predict_dual_chunked(clfs_full, regs_full, full_sources, act_idx)
    p_final, m_final = _fuse_log_odds(p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, k_est, beta_phys=0.35)

    p_grid = scatter_fp(p_final, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_grid = scatter_fp(m_final, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc = emit.dinkelbach_allocate(
        p_grid,
        m_grid,
        allowed,
        budget=None,
        k_truth=k_est,
        min_spacing_px=2.05,
        dinkelbach_iters=6,
    )
    return alloc.emitted.astype(np.float32), p_grid, {
        "n_dots": int(alloc.n_dots),
        "k_truth_est": float(k_est),
        "surrogate_dti": float(alloc.surrogate_dti),
        "width_law": wlaw.to_json(),
    }


def fit_and_emit_production_adhr(
    grid,
    X_phys_mm: np.ndarray,
    folds_by_seed: list[tuple[int, list[dict]]],
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    cache_npz = Path(cache_dir) / "prod_adhr_v2.npz"
    if cache_npz.is_file():
        z = np.load(cache_npz, allow_pickle=False)
        emitted = np.zeros(grid.shape, dtype=np.float32)
        dyx = z["dots_yx"]
        emitted[dyx[:, 0], dyx[:, 1]] = 1.0
        p_surface = scatter_fp(z["p_fp"], ys_fp, xs_fp, grid.shape)
        meta = json.loads(str(z["meta_json"]))
        return emitted, p_surface, np.zeros((1, 1), dtype=np.float32), meta

    d_fullcat = ndi.distance_transform_edt(~grid.catalogue).astype(np.float32)
    allowed_prod = fp & (d_fullcat > 2.0)
    act_idx = np.flatnonzero(allowed_prod[ys_fp, xs_fp])

    # Strictly 4-quadrant out-of-fold cross-fitting for the physical head,
    # matching predict_fold_adhr's 3-quadrant-train / 1-quadrant-predict split
    # so smooth geophysical covariates cannot overfit in-sample fault flanks.
    folds_q4 = folds_by_seed[0][1]
    p_phys_raw = np.zeros(act_idx.size, dtype=np.float32)
    m_phys_raw = np.zeros(act_idx.size, dtype=np.float32)
    covered = np.zeros(act_idx.size, dtype=bool)
    for q_idx, f_q in enumerate(folds_q4):
        train_dom_q = (~f_q["region"])[ys_fp, xs_fp]
        c_q, r_q = _fit_dual_expectation_models(
            [X_phys_mm], train_dom_q, grid.catalogue, fp, seed=880310 + q_idx, max_zero_neg=120_000, n_ensemble=1
        )
        mask_q = f_q["region"][ys_fp[act_idx], xs_fp[act_idx]]
        if q_idx == len(folds_q4) - 1:
            mask_q = mask_q | (~covered)
        covered |= mask_q
        pq, mq = _predict_dual_chunked(c_q, r_q, [X_phys_mm], act_idx[mask_q])
        p_phys_raw[mask_q] = pq
        m_phys_raw[mask_q] = mq
        del c_q, r_q, pq, mq
        gc.collect()

    struct_clfs: list[HistGradientBoostingClassifier] = []
    struct_regs: list[HistGradientBoostingRegressor] = []
    w_laws: list[damagezone_envelope.WidthLaw] = []
    ratios: list[float] = []

    for seed, folds in folds_by_seed:
        vis_s = folds[0]["visible"]
        X_v22, dv_s, cl_s = compute_visible_struct_fp(grid, vis_s, sense_src, scarp_fields, cache_dir, f"seed{seed}")
        reg_s = np.zeros(grid.shape, dtype=bool)
        tr_s = np.zeros(grid.shape, dtype=bool)
        for f in folds:
            reg_s |= f["region"]
            tr_s |= f["truth"]
        ratios.append(float(tr_s.sum()) / max(float((vis_s & reg_s).sum()), 1.0))
        pop_fp = tr_s[ys_fp, xs_fp]
        wlaw = damagezone_envelope.fit_width_law(cl_s, dv_s, pop_fp, quantile=0.90, l0_px=40.0)
        w_laws.append(wlaw)
        dow_s = (dv_s / np.maximum(wlaw.half_width(cl_s), 1e-6)).astype(np.float32)
        dom_s = (reg_s & ~vis_s)[ys_fp, xs_fp]
        cs, rs = _fit_dual_expectation_models(
            [X_phys_mm, X_v22, dow_s], dom_s, tr_s, fp, seed=880400 + seed, max_zero_neg=140_000, n_ensemble=1
        )
        struct_clfs.extend(cs)
        struct_regs.extend(rs)
        del X_v22, dv_s, cl_s, dow_s, dom_s, reg_s, tr_s
        gc.collect()

    X_v22_prod, dv_prod, cl_prod = compute_visible_struct_fp(
        grid, grid.catalogue, sense_src, scarp_fields, cache_dir, "prod_fullcat"
    )
    hw_prod = np.mean([wl.half_width(cl_prod) for wl in w_laws], axis=0).astype(np.float32)
    dow_prod = (dv_prod / np.maximum(hw_prod, 1e-6)).astype(np.float32)
    prod_sources = [X_phys_mm, X_v22_prod, dow_prod]

    hid_ratio_mean = float(np.mean(ratios))
    k_prod = float(grid.catalogue.sum()) * hid_ratio_mean

    p_full_raw, m_full_raw = _predict_dual_chunked(struct_clfs, struct_regs, prod_sources, act_idx)
    del struct_clfs, struct_regs, prod_sources, X_v22_prod, dv_prod, cl_prod, hw_prod, dow_prod
    gc.collect()

    p_final, m_final = _fuse_log_odds(p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, k_prod, beta_phys=0.35)
    del p_phys_raw, m_phys_raw, p_full_raw, m_full_raw
    gc.collect()

    p_surface = scatter_fp(p_final, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_surface = scatter_fp(m_final, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    del p_final, m_final
    gc.collect()

    alloc = emit.dinkelbach_allocate(
        p_surface,
        m_surface,
        allowed_prod,
        budget=None,
        k_truth=k_prod,
        min_spacing_px=2.05,
        dinkelbach_iters=8,
    )
    meta = {
        "n_dots": int(alloc.n_dots),
        "k_truth_est": float(k_prod),
        "surrogate_dti": float(alloc.surrogate_dti),
        "dinkelbach_rounds": int(alloc.rounds),
        "flank_exclusion_px": 2.0,
        "min_spacing_px": 2.05,
        "median_d_cat_px": float(np.median(d_fullcat[alloc.emitted])) if alloc.n_dots else 0.0,
        "frac_gt_10px": float((d_fullcat[alloc.emitted] > 10.0).mean()) if alloc.n_dots else 0.0,
        "frac_gt_25px": float((d_fullcat[alloc.emitted] > 25.0).mean()) if alloc.n_dots else 0.0,
    }
    dy, dx = np.nonzero(alloc.emitted)
    np.savez_compressed(
        cache_npz,
        dots_yx=np.column_stack([dy, dx]).astype(np.int32),
        p_fp=p_surface[ys_fp, xs_fp].astype(np.float32),
        meta_json=np.array(json.dumps(meta)),
    )
    return alloc.emitted.astype(np.float32), p_surface, m_surface, meta
