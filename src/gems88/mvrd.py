"""H88-MVRD & MPSC-88 (`2026-10-24`): Magnetite-Destruction Polarity, Monoclinal Scarp,
Completeness-Gated Dual-Expectation & Oriented Strand-Tensor Submodular Discovery.

Memory-bounded (< 550 MB RSS): builds a disk-backed float32 ``np.memmap`` of 18
previously unused verified geophysical/geomorphic channels aligned with
``np.nonzero(grid.footprint)`` (5,167,373 x 18 = 372 MB on disk) on top of the
cached 44-channel ``physics.py`` stack (total 62 label-blind physical channels
for ``MPSC-88``, plus 23 strictly fold-visible structural channels = 85 features
for ``H88-MVRD``).
"""
from __future__ import annotations

import gc
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from gems57 import damagezone_envelope, emit

from . import adhr, physics
from .edge import clean_band

TAN_60 = math.tan(math.radians(60.0))

MVRD_EXTRA_PHYS_FEATURES: tuple[str, ...] = (
    "mag_remanence_diff",
    "mag_remanence_grad_300m",
    "mrr_vg_regional_resid",
    "mag_analytic_signal_log",
    "mag_tilt_contact_shallow",
    "mrr_demag_on_grav_step",
    "dip_analytic_signal_60deg",
    "lidar_monoclinal_polarity",
    "lidar_cross_scarp_jump",
    "lidar_grav_strike_align",
    "topo10_aspect_coherence",
    "topo10_bajada_scarp_index",
    "topo10_steep_concentration",
    "tectonic_knickzone_power",
    "chi_divide_asymmetry",
    "rad_u_th_redox",
    "rad_redox_clay_xgrad",
    "transtension_grav_lock",
)

MPSC_FEATURES: tuple[str, ...] = physics.ALL_PHYS_FEATURES + MVRD_EXTRA_PHYS_FEATURES
MVRD_ALL_FEATURES: tuple[str, ...] = MPSC_FEATURES + adhr.VIS_STRUCT_FEATURES


def _decode_quantized_u8(ds: rasterio.DatasetReader, band_idx: int, fp: np.ndarray) -> np.ndarray:
    raw = ds.read(band_idx).astype(np.float32)
    tags = ds.tags(band_idx)
    q_lo = float(tags.get("q_lo", 0.0))
    q_hi = float(tags.get("q_hi", 1.0))
    arr = np.where(raw > 0.0, q_lo + (raw - 1.0) / 254.0 * (q_hi - q_lo), np.nan).astype(np.float32)
    return clean_band(arr, fp)[0]


def build_or_load_mvrd_extra_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict[str, np.ndarray]]:
    """Build or reload disk-backed ``(N_fp, 18)`` float32 memmap + physical strike director."""
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    n_fp = ys.size
    n_cols = len(MVRD_EXTRA_PHYS_FEATURES)
    cache_dir.mkdir(parents=True, exist_ok=True)

    dat_path = cache_dir / "x_mvrd_extra_18ch.dat"
    meta_path = cache_dir / "x_mvrd_extra_18ch.json"
    dir_path = cache_dir / "mvrd_phys_director_v1.npz"

    feat_path = root / "data/training_features.tif"
    ext = root / "data/external"
    dep_files = (
        feat_path,
        ext / "lidar_scarp_features_u8.tif",
        ext / "topo_10m_derived_100m_u8.tif",
        ext / "dem10_chi_100m_i16.tif",
        ext / "geodawn_extensions_u8.tif",
    )
    dep_sig = hashlib.sha256(
        "|".join(f"{p.name}:{p.stat().st_size}" for p in dep_files).encode("utf-8")
    ).hexdigest()[:20]

    if dat_path.exists() and meta_path.exists() and dir_path.exists():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(MVRD_EXTRA_PHYS_FEATURES)
            and meta.get("dep_sig") == dep_sig
        ):
            mm = np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols))
            d_npz = np.load(dir_path)
            director = {k: d_npz[k] for k in d_npz.files}
            return mm, director

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    with rasterio.open(feat_path) as src:
        def rd(idx: int) -> np.ndarray:
            return clean_band(src.read(idx), fp)[0]

        mag_anom = rd(1)
        rtp = rd(2)
        tmi_hg = np.maximum(rd(3), 0.0)
        tmi_vg = rd(9)
        tmi = rd(14)
        grav = rd(13)
        zbase_m = np.maximum(rd(15), 0.0)
        grav_hg = np.maximum(rd(18), 0.0)
        cond = rd(17)
        det_elev = rd(12)
        det_slope = np.maximum(rd(19), 0.0)
        geod_2nd = np.maximum(rd(4), 0.0)
        geod_shear = np.abs(rd(7))
        geod_dil = rd(8)

    # 1-2. RTP minus anomalous magnetic field remanence discrepancy & 300 m gradient
    rem_diff = (rtp - mag_anom).astype(np.float32)
    del mag_anom
    _, _, rem_g3 = physics._grad_f32(rem_diff, 3.0)
    mm[:, 0] = np.arcsinh(rem_diff[ys, xs] / 50.0).astype(np.float32)
    mm[:, 1] = np.log1p(rem_g3[ys, xs]).astype(np.float32)
    del rem_diff, rem_g3
    gc.collect()

    # 3. MRR-88: Regional-regressed intra-magnetic vertical-to-total polarity trough
    tmi_loc = ndi.gaussian_filter(tmi, sigma=2.0, mode="nearest") - ndi.gaussian_filter(tmi, sigma=14.0, mode="nearest")
    del tmi
    vg_loc = ndi.gaussian_filter(tmi_vg, sigma=1.5, mode="nearest") - ndi.gaussian_filter(tmi_vg, sigma=14.0, mode="nearest")
    cov_vt = ndi.gaussian_filter(vg_loc * tmi_loc, sigma=10.0, mode="nearest")
    var_tt = ndi.gaussian_filter(tmi_loc * tmi_loc, sigma=10.0, mode="nearest") + 1e-3
    beta_loc = np.clip(cov_vt / var_tt, -0.05, 0.25).astype(np.float32)
    # Negated residual: hydrothermal magnetite->hematite/pyrite destruction gives vg < beta*tmi
    mrr_trough = (-(vg_loc - beta_loc * tmi_loc)).astype(np.float32)
    mm[:, 2] = np.arcsinh(mrr_trough[ys, xs]).astype(np.float32)
    del tmi_loc, vg_loc, cov_vt, var_tt, beta_loc

    # 4-7. 3D Analytic Signal, Salem tilt-contact shallowing, demag-on-grav step & 60-deg dip AS
    analytic_sig = np.hypot(tmi_hg, tmi_vg).astype(np.float32)
    as_log = np.log1p(analytic_sig).astype(np.float32)
    mm[:, 3] = as_log[ys, xs]

    tilt_angle = np.arctan2(tmi_vg, np.maximum(tmi_hg, 1e-3)).astype(np.float32)
    _, _, tilt_grad2 = physics._grad_f32(tilt_angle, 2.0)
    # Peak near |tilt_angle| < 0.35 rad zero-crossings per Salem et al. (2007)
    tilt_zero_gate = np.exp(-((tilt_angle / 0.45) ** 2)).astype(np.float32)
    mm[:, 4] = (np.log1p(tilt_grad2[ys, xs] * 20.0) * (0.4 + 0.6 * tilt_zero_gate[ys, xs])).astype(np.float32)
    del analytic_sig, tilt_angle, tilt_grad2, tilt_zero_gate

    grav_hg_log = np.log1p(grav_hg * 100.0).astype(np.float32)
    mm[:, 5] = (np.maximum(mrr_trough[ys, xs], 0.0) * grav_hg_log[ys, xs]).astype(np.float32)
    del mrr_trough, grav_hg

    ggy8, ggx8, gmag8 = physics._grad_f32(grav, 8.0)
    gn8_fp = gmag8[ys, xs] + 1e-6
    shift_fp = np.clip((zbase_m[ys, xs] / 100.0) / TAN_60, 0.0, 16.0).astype(np.float32)
    dy_hw_fp = (-ggy8[ys, xs] / gn8_fp) * shift_fp
    dx_hw_fp = (-ggx8[ys, xs] / gn8_fp) * shift_fp
    mm[:, 6] = physics._bilinear_at_fp(as_log, ys, xs, dy_hw_fp, dx_hw_fp)
    del as_log, zbase_m, shift_fp, dy_hw_fp, dx_hw_fp
    gc.collect()

    # Build label-blind multi-modality spin-2 physical strike director (det_elev + grav + rtp)
    dgy2, dgx2, dmag2 = physics._grad_f32(det_elev, 2.2)
    rgy3, rgx3, rmag3 = physics._grad_f32(rtp, 3.0)
    ggy3, ggx3, gmag3 = physics._grad_f32(grav, 3.5)
    del det_elev, rtp, grav

    def _spin2_from_grad(gy: np.ndarray, gx: np.ndarray, gmag: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        # Strike is perpendicular to gradient: s = (-gy, gx) / gmag
        inv = 1.0 / (gmag + 1e-6)
        sy = -gy * inv
        sx = gx * inv
        # Double-angle in (row=y, col=x): cos(2a) = sx^2 - sy^2, sin(2a) = 2*sx*sy
        w = np.tanh(gmag / (float(np.percentile(gmag[fp], 75)) + 1e-6)).astype(np.float32)
        return ((sx * sx - sy * sy) * w).astype(np.float32), (2.0 * sx * sy * w).astype(np.float32), w

    c_d, s_d, w_d = _spin2_from_grad(dgy2, dgx2, dmag2)
    c_g, s_g, w_g = _spin2_from_grad(ggy3, ggx3, gmag3)
    c_r, s_r, w_r = _spin2_from_grad(rgy3, rgx3, rmag3)
    del dgy2, dgx2, dmag2, rgy3, rgx3, rmag3, ggy3, ggx3, gmag3

    u_tot = ndi.gaussian_filter(0.50 * c_d + 0.30 * c_g + 0.20 * c_r, sigma=2.5, mode="nearest")
    v_tot = ndi.gaussian_filter(0.50 * s_d + 0.30 * s_g + 0.20 * s_r, sigma=2.5, mode="nearest")
    w_tot = ndi.gaussian_filter(0.50 * w_d + 0.30 * w_g + 0.20 * w_r, sigma=2.5, mode="nearest") + 1e-5
    del c_d, s_d, w_d, c_g, s_g, w_g, c_r, s_r, w_r

    coh_phys = np.clip(np.hypot(u_tot, v_tot) / w_tot, 0.0, 1.0).astype(np.float32)
    ang_phys = (0.5 * np.arctan2(v_tot, u_tot)).astype(np.float32)
    # Unit strike vector (dy = sin(ang), dx = cos(ang)) in grid coordinates
    dir_dy_fp = np.sin(ang_phys[ys, xs]).astype(np.float32)
    dir_dx_fp = np.cos(ang_phys[ys, xs]).astype(np.float32)
    coh_fp = coh_phys[ys, xs].astype(np.float32)

    # Regional gravity strike angle for LiDAR strike concordance
    theta_grav_fp = np.arctan2(ggx8[ys, xs], -ggy8[ys, xs]).astype(np.float32)
    del ggy8, ggx8, gmag8, u_tot, v_tot, w_tot, coh_phys, ang_phys
    gc.collect()

    # 8-10. 1 m LiDAR monoclinal scarp polarity, cross-scarp jump & strike-gravity alignment
    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as ds:
        ex_mean = ds.read(2)[ys, xs].astype(np.float32)
        down_f = ds.read(6)[ys, xs].astype(np.float32)
        up_f = ds.read(7)[ys, xs].astype(np.float32)
        cross_m = ds.read(8)[ys, xs].astype(np.float32)
        coh100 = ds.read(10)[ys, xs].astype(np.float32) / 255.0
        strike_u8 = ds.read(11)[ys, xs].astype(np.float32)
        lv = ds.read(12)[ys, xs] > 0

    asym = np.abs(down_f - up_f) / (down_f + up_f + 4.0)
    mm[:, 7] = np.where(lv, asym * np.log1p(np.maximum(down_f, up_f)), -1.0).astype(np.float32)
    mm[:, 8] = np.where(lv, np.sqrt(cross_m * ex_mean), -1.0).astype(np.float32)
    # Strike u8 encodes [0, pi) over [0, 255]
    theta_lid = (strike_u8 / 255.0) * math.pi
    mm[:, 9] = np.where(lv, np.cos(2.0 * (theta_lid - theta_grav_fp)) * coh100, 0.0).astype(np.float32)
    del ex_mean, down_f, up_f, cross_m, coh100, strike_u8, lv, asym, theta_lid, theta_grav_fp

    # 11-13. Full-footprint 10 m DEM aspect coherence, bajada scarp index & steep concentration
    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as ds:
        slp_p90 = _decode_quantized_u8(ds, 1, fp)[ys, xs]
        slp_max = _decode_quantized_u8(ds, 2, fp)[ys, xs]
        steep_fr = _decode_quantized_u8(ds, 3, fp)[ys, xs]
        slp_std = _decode_quantized_u8(ds, 4, fp)[ys, xs]
        rel_loc = np.maximum(_decode_quantized_u8(ds, 5, fp)[ys, xs], 0.0)
        asp_coh = _decode_quantized_u8(ds, 7, fp)[ys, xs]

    mm[:, 10] = asp_coh
    mm[:, 11] = (asp_coh * slp_std / np.sqrt(rel_loc + 4.0)).astype(np.float32)
    mm[:, 12] = (np.log1p(np.maximum(slp_max - slp_p90, 0.0)) * (1.0 - 0.5 * np.clip(steep_fr, 0.0, 1.0))).astype(np.float32)
    del slp_p90, slp_max, steep_fr, slp_std, rel_loc, asp_coh

    # 14-15. 300 m piedmont-propagated drainage-area-conditioned tectonic knickzone power & chi divide jump
    with rasterio.open(ext / "dem10_chi_100m_i16.tif") as ds:
        b1_raw = ds.read(1).astype(np.float32)
        b2_raw = ds.read(2).astype(np.float32)
        b3_raw = ds.read(3).astype(np.float32)
        b4_raw = ds.read(4).astype(np.float32)

    valid_ch = (b4_raw > -30000.0) & fp
    area_gate_g = np.where(valid_ch, np.clip(b4_raw / 1000.0 - 3.8, 0.0, 5.5), 0.0).astype(np.float32)
    ksn_pos_g = np.where(valid_ch & (b3_raw > 0.0), np.log1p(np.maximum(b3_raw, 0.0)), 0.0).astype(np.float32)
    knick_grid = ndi.gaussian_filter(ksn_pos_g * area_gate_g, sigma=3.0, mode="constant")

    valid_step = valid_ch & (b1_raw > -30000.0) & (b2_raw > -30000.0)
    chi_jump_g = np.where(valid_step, np.log1p(np.maximum(b1_raw - b2_raw, 0.0) / 50.0), 0.0).astype(np.float32)
    chi_grid = ndi.gaussian_filter(chi_jump_g, sigma=3.5, mode="constant")

    mm[:, 13] = knick_grid[ys, xs].astype(np.float32)
    mm[:, 14] = chi_grid[ys, xs].astype(np.float32)
    del b1_raw, b2_raw, b3_raw, b4_raw, valid_ch, area_gate_g, ksn_pos_g, knick_grid, valid_step, chi_jump_g, chi_grid

    # 16-17. Uranium redox disequilibrium & redox-clay co-gradient (playa-suppressed)
    with rasterio.open(ext / "geodawn_extensions_u8.tif") as ds:
        uk = ds.read(2).astype(np.float32)
        uth = ds.read(3).astype(np.float32)
    _, _, uth_g3 = physics._grad_f32(uth, 3.0)
    _, _, cond_g3 = physics._grad_f32(cond, 3.0)
    playa_suppress = np.tanh(det_slope[ys, xs] / 0.8 + 0.15).astype(np.float32)
    mm[:, 15] = ((0.65 * uth[ys, xs] + 0.35 * uk[ys, xs]) / 255.0 * playa_suppress).astype(np.float32)
    mm[:, 16] = (np.log1p(uth_g3[ys, xs]) * np.log1p(cond_g3[ys, xs]) * playa_suppress).astype(np.float32)
    del uk, uth, uth_g3, cond_g3, cond, playa_suppress

    # 18. Strain-partitioned transtension x multi-modality strike coherence
    strain_part = ((geod_dil[ys, xs] - 0.35 * geod_shear[ys, xs]) / (geod_2nd[ys, xs] + 5.0)).astype(np.float32)
    mm[:, 17] = (coh_fp * (0.5 + 0.5 * np.tanh(strain_part)) * grav_hg_log[ys, xs]).astype(np.float32)
    del det_slope, geod_2nd, geod_shear, geod_dil, grav_hg_log, strain_part
    mm.flush()

    for j in range(n_cols):
        if not np.isfinite(mm[:, j]).all():
            raise AssertionError(f"Non-finite values in MVRD column {MVRD_EXTRA_PHYS_FEATURES[j]}")

    director = {
        "dir_dy_fp": dir_dy_fp,
        "dir_dx_fp": dir_dx_fp,
        "coh_fp": coh_fp,
    }
    np.savez_compressed(dir_path, **director)
    meta_path.write_text(
        json.dumps(
            {
                "shape": [n_fp, n_cols],
                "features": list(MVRD_EXTRA_PHYS_FEATURES),
                "dep_sig": dep_sig,
            },
            indent=2,
        )
        + "\n"
    )
    del mm
    gc.collect()
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), director


def _bayes_shift(p_sub: np.ndarray, odds_ratio: float) -> np.ndarray:
    """Exact case-control Bayes prior shift: P(Y=1|X) = r*p / (1 - p + r*p)."""
    r = float(odds_ratio)
    p64 = np.clip(np.asarray(p_sub, dtype=np.float64), 1e-7, 1.0 - 1e-7)
    return (r * p64 / ((1.0 - p64) + r * p64)).astype(np.float32)


def fit_diverse_dual_ensemble(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    seed: int,
    max_zero_neg: int = 220_000,
) -> tuple[list[dict], list[HistGradientBoostingRegressor]]:
    """Fit a fast, unweighted Bayes-exact dual-expectation GBDT ensemble for
    cell truth probability ``p(x) = P(d=0 | X)`` and 300 m kernel self-credit
    ``m(x) = p(x) + E[k(d) | X, 0 < d < 3] * max(P(d < 3 | X) - p(x), 0)``.

    By partitioning into mutually exclusive events ``{d=0}``, ``{0 < d < 3}``, and
    ``{d >= 3}`` with uniform negative subsampling + analytic Bayes odds-ratio shift,
    all trees train on scikit-learn's unweighted Cython histogram path (~15x faster,
    higher effective negative sample size, logistic cross-entropy on both ``{d=0}``
    and ``{d < 3}``, and ``m(x) >= p(x)`` strictly guaranteed by construction).
    """
    ys_fp, xs_fp = np.nonzero(fp_mask)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int8)
    y_kern_grid = np.clip(1.0 - ndi.distance_transform_edt(~pos_grid) / 3.0, 0.0, 1.0).astype(np.float32)
    y_kern_all = y_kern_grid[ys_fp, xs_fp]
    del y_kern_grid

    dom_idx = np.flatnonzero(domain_fp)
    yc_dom = y_cell_all[dom_idx]
    yk_dom = y_kern_all[dom_idx]

    rng = np.random.default_rng(seed)

    # 1. Cell dataset: 100% of {d=0} positives + uniform subsample of all {d>0} negatives
    pos_cell_idx = dom_idx[yc_dom == 1]
    neg_cell_pool = dom_idx[yc_dom == 0]
    if neg_cell_pool.size > max_zero_neg:
        neg_cell_idx = np.sort(rng.choice(neg_cell_pool, size=max_zero_neg, replace=False))
        r_cell = float(max_zero_neg) / float(neg_cell_pool.size)
    else:
        neg_cell_idx = neg_cell_pool
        r_cell = 1.0

    cell_idx = np.concatenate([pos_cell_idx, neg_cell_idx])
    cell_y = np.concatenate([
        np.ones(pos_cell_idx.size, dtype=np.int8),
        np.zeros(neg_cell_idx.size, dtype=np.int8),
    ])
    seq_c = np.argsort(cell_idx)
    cell_idx = cell_idx[seq_c]
    cell_y = cell_y[seq_c]
    X_cell = adhr.gather_columns(sources, cell_idx)

    # 2. Halo dataset: {d < 3} positives vs uniform subsample of {d >= 3} negatives
    halo_pos_pool = dom_idx[yk_dom > 0.0]
    halo_neg_pool = dom_idx[yk_dom == 0.0]
    max_halo_pos = max(110_000, pos_cell_idx.size * 3)
    if halo_pos_pool.size > max_halo_pos:
        halo_pos_idx = np.sort(rng.choice(halo_pos_pool, size=max_halo_pos, replace=False))
        q_hpos = float(max_halo_pos) / float(halo_pos_pool.size)
    else:
        halo_pos_idx = halo_pos_pool
        q_hpos = 1.0
    if halo_neg_pool.size > max_zero_neg:
        halo_neg_idx = np.sort(rng.choice(halo_neg_pool, size=max_zero_neg, replace=False))
        q_hneg = float(max_zero_neg) / float(halo_neg_pool.size)
    else:
        halo_neg_idx = halo_neg_pool
        q_hneg = 1.0
    r_halo = q_hneg / max(q_hpos, 1e-8)

    halo_idx = np.concatenate([halo_pos_idx, halo_neg_idx])
    halo_y = np.concatenate([
        np.ones(halo_pos_idx.size, dtype=np.int8),
        np.zeros(halo_neg_idx.size, dtype=np.int8),
    ])
    seq_h = np.argsort(halo_idx)
    halo_idx = halo_idx[seq_h]
    halo_y = halo_y[seq_h]
    X_halo = adhr.gather_columns(sources, halo_idx)

    # 3. Conditional flank kernel mean E[k(d) | X, 0 < d < 3] (purely unweighted)
    flank_pool = dom_idx[(yk_dom > 0.0) & (yc_dom == 0)]
    if flank_pool.size > 70_000:
        flank_idx = np.sort(rng.choice(flank_pool, size=70_000, replace=False))
    else:
        flank_idx = flank_pool
    X_flank = adhr.gather_columns(sources, flank_idx)
    y_flank = y_kern_all[flank_idx]

    configs = (
        dict(max_iter=155, learning_rate=0.060, max_leaf_nodes=47, min_samples_leaf=75, l2_regularization=4.0),
        dict(max_iter=175, learning_rate=0.050, max_leaf_nodes=75, min_samples_leaf=95, l2_regularization=7.0),
    )
    models: list[dict] = []
    flank_regs: list[HistGradientBoostingRegressor] = []

    for k, cfg in enumerate(configs):
        p_c = rng.permutation(len(cell_idx))
        clf_cell = HistGradientBoostingClassifier(
            **cfg,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=14,
            random_state=seed + 107 * k,
        )
        clf_cell.fit(X_cell[p_c], cell_y[p_c])

        p_h = rng.permutation(len(halo_idx))
        clf_halo = HistGradientBoostingClassifier(
            **cfg,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=14,
            random_state=seed + 223 * k,
        )
        clf_halo.fit(X_halo[p_h], halo_y[p_h])

        models.append({
            "clf_cell": clf_cell,
            "r_cell": r_cell,
            "clf_halo": clf_halo,
            "r_halo": r_halo,
        })

    if len(flank_idx) >= 50:
        p_f = rng.permutation(len(flank_idx))
        reg_flank = HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=110,
            learning_rate=0.065,
            max_leaf_nodes=35,
            min_samples_leaf=60,
            l2_regularization=4.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=12,
            random_state=seed + 337,
        )
        reg_flank.fit(X_flank[p_f], y_flank[p_f])
        flank_regs.append(reg_flank)

    del X_cell, X_halo, X_flank
    return models, flank_regs


def predict_mvrd_dual_chunked(
    models: list[dict],
    flank_regs: list[HistGradientBoostingRegressor],
    sources: list[np.ndarray],
    act_idx: np.ndarray,
    chunk: int = 180_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Chunked Bayes-calibrated prediction of ``(p_cell, m_self_credit)``."""
    n = act_idx.size
    p_out = np.empty(n, dtype=np.float32)
    m_out = np.empty(n, dtype=np.float32)
    for start in range(0, n, chunk):
        sl = slice(start, min(start + chunk, n))
        X_sub = adhr.gather_columns(sources, act_idx[sl])
        p_acc = np.zeros(len(X_sub), dtype=np.float64)
        h_acc = np.zeros(len(X_sub), dtype=np.float64)
        for m in models:
            p_acc += _bayes_shift(m["clf_cell"].predict_proba(X_sub)[:, 1], m["r_cell"])
            h_acc += _bayes_shift(m["clf_halo"].predict_proba(X_sub)[:, 1], m["r_halo"])
        p_c = (p_acc / len(models)).astype(np.float32)
        p_h = (h_acc / len(models)).astype(np.float32)
        if flank_regs:
            mu_f = np.clip(flank_regs[0].predict(X_sub), 0.08, 0.72).astype(np.float32)
        else:
            mu_f = np.float32(0.42)
        m_c = np.clip(p_c + mu_f * np.maximum(p_h - p_c, 0.0), p_c, 1.0).astype(np.float32)
        p_out[sl] = p_c
        m_out[sl] = m_c
    return p_out, m_out


def strand_enhance_probabilities(
    p_fp_vals: np.ndarray,
    m_fp_vals: np.ndarray,
    act_idx: np.ndarray,
    ys_fp: np.ndarray,
    xs_fp: np.ndarray,
    director: dict[str, np.ndarray],
    shape: tuple[int, int],
    strength: float = 0.30,
) -> tuple[np.ndarray, np.ndarray]:
    """Anisotropic physical-strike strand continuity & cross-strike ridge sharpening.

    Integrates predicted fault probability along the purely physical multi-modality
    strike vector ``(dir_dy, dir_dx)`` (derived strictly from ``det_elev``,
    ``iso_grav_anom``, and ``rtp`` with zero catalogue input) at +/-1.5 px and
    +/-3.0 px while penalizing off-ridge lateral spread, preserving exact total
    probability mass ``sum(p)``.
    """
    if strength <= 0.0 or act_idx.size == 0:
        p_g = adhr.scatter_fp(p_fp_vals, ys_fp[act_idx], xs_fp[act_idx], shape)
        m_g = adhr.scatter_fp(m_fp_vals, ys_fp[act_idx], xs_fp[act_idx], shape)
        return p_g, m_g

    p_grid = adhr.scatter_fp(p_fp_vals, ys_fp[act_idx], xs_fp[act_idx], shape)
    m_grid = adhr.scatter_fp(m_fp_vals, ys_fp[act_idx], xs_fp[act_idx], shape)

    ya = ys_fp[act_idx]
    xa = xs_fp[act_idx]
    dy = director["dir_dy_fp"][act_idx]
    dx = director["dir_dx_fp"][act_idx]
    coh = director["coh_fp"][act_idx]
    # Orthogonal cross-strike normal (-dx, dy)
    ny = -dx
    nx = dy

    p_a1 = 0.5 * (
        physics._bilinear_at_fp(p_grid, ya, xa, 1.5 * dy, 1.5 * dx)
        + physics._bilinear_at_fp(p_grid, ya, xa, -1.5 * dy, -1.5 * dx)
    )
    p_a2 = 0.5 * (
        physics._bilinear_at_fp(p_grid, ya, xa, 3.0 * dy, 3.0 * dx)
        + physics._bilinear_at_fp(p_grid, ya, xa, -3.0 * dy, -3.0 * dx)
    )
    p_c1 = 0.5 * (
        physics._bilinear_at_fp(p_grid, ya, xa, 1.5 * ny, 1.5 * nx)
        + physics._bilinear_at_fp(p_grid, ya, xa, -1.5 * ny, -1.5 * nx)
    )
    m_a1 = 0.5 * (
        physics._bilinear_at_fp(m_grid, ya, xa, 1.5 * dy, 1.5 * dx)
        + physics._bilinear_at_fp(m_grid, ya, xa, -1.5 * dy, -1.5 * dx)
    )

    p_along = 0.65 * p_a1 + 0.35 * p_a2
    # Geometric-arithmetic strand reinforcement + gentle cross-strike crest sharpening
    gate = np.float32(strength) * (0.35 + 0.65 * coh)
    ridge_boost = np.clip((p_fp_vals - 0.30 * p_c1) / (p_fp_vals + 1e-6), 0.55, 1.0)
    p_enh = (1.0 - gate) * p_fp_vals + gate * (0.60 * np.sqrt(p_fp_vals * np.maximum(p_along, 0.0)) + 0.40 * p_along) * ridge_boost

    # Preserve exact expected positive count sum(p)
    tot_in = float(np.sum(p_fp_vals, dtype=np.float64))
    tot_out = float(np.sum(p_enh, dtype=np.float64))
    if tot_out > 1e-8:
        p_enh = np.clip(p_enh * np.float32(tot_in / tot_out), 0.0, 1.0)

    m_enh = np.clip((1.0 - 0.5 * gate) * m_fp_vals + 0.5 * gate * m_a1, p_enh, 1.0).astype(np.float32)
    return (
        adhr.scatter_fp(p_enh.astype(np.float32), ya, xa, shape),
        adhr.scatter_fp(m_enh, ya, xa, shape),
    )


def completeness_gated_fuse(
    p_full_raw: np.ndarray,
    m_full_raw: np.ndarray,
    p_phys_vis_raw: np.ndarray,
    m_phys_vis_raw: np.ndarray,
    p_phys_hid_raw: np.ndarray,
    m_phys_hid_raw: np.ndarray,
    d_vis_act: np.ndarray,
    k_target: float,
    phys_vis_all_sum: float,
    n_vis_test: float,
    beta_poe: float = 0.35,
    w_blind_max: float = 0.42,
) -> tuple[np.ndarray, np.ndarray]:
    """Spatially adaptive Bayesian completeness-gated fusion.

    1. Near visible faults (``d_vis <= 3.5 px``), ``w_blind(d_vis) = 0``: silences
       false-positive geophysical halo bleed around already-mapped traces so ONLY
       the relay-aware ``p_joint`` head allocates tip/step-over dots.
    2. Far in unmapped basins/piedmonts (``d_vis > 10-25 px``), ``w_blind(d_vis)``
       smoothly rises toward ``w_blind_max``, blending the distance-blind subtle
       hidden-fault physics head ``p_phys_hid`` + properly normalized ``p_phys_vis``
       (scaled over the *unmasked* region so visible faults absorb their own
       ``n_vis_test`` mass instead of inflating off-fault background!).
    """
    # Combine the two distance-blind physics heads:
    # - p_phys_hid was trained directly on subtle withheld faults (zero d_vis input)
    # - p_phys_vis was trained on mapped faults; scale using d_vis > 3.5 tail where
    #   visible faults have zero sensor halo so both heads share exact blind-basin mass
    scale_hid = float(k_target) / max(float(np.sum(p_phys_hid_raw, dtype=np.float64)), 1e-6)
    far_mask = d_vis_act > 3.5
    if np.any(far_mask):
        hid_far_sum = max(float(np.sum(p_phys_hid_raw[far_mask], dtype=np.float64)), 1e-6)
        vis_far_sum = max(float(np.sum(p_phys_vis_raw[far_mask], dtype=np.float64)), 1e-6)
        scale_vis = (hid_far_sum * scale_hid) / vis_far_sum
    else:
        scale_vis = float(k_target) / max(float(phys_vis_all_sum), float(n_vis_test), 1e-6)

    p_vis_cal = np.clip(p_phys_vis_raw * np.float32(scale_vis), 0.0, 1.0)
    m_vis_ratio = float(np.sum(m_phys_vis_raw, dtype=np.float64)) / max(float(np.sum(p_phys_vis_raw, dtype=np.float64)), 1e-6)
    m_vis_cal = np.clip(
        m_phys_vis_raw * np.float32((float(np.sum(p_vis_cal, dtype=np.float64)) * m_vis_ratio) / max(float(np.sum(m_phys_vis_raw, dtype=np.float64)), 1e-6)),
        p_vis_cal,
        1.0,
    )

    p_hid_cal = np.clip(p_phys_hid_raw * np.float32(scale_hid), 0.0, 1.0)
    m_ratio_hid = float(np.sum(m_phys_hid_raw, dtype=np.float64)) / max(float(np.sum(p_phys_hid_raw, dtype=np.float64)), 1e-6)
    m_hid_cal = np.clip(
        m_phys_hid_raw * np.float32((float(k_target) * m_ratio_hid) / max(float(np.sum(m_phys_hid_raw, dtype=np.float64)), 1e-6)),
        p_hid_cal,
        1.0,
    )

    p_blind = (0.60 * p_hid_cal + 0.40 * p_vis_cal).astype(np.float32)
    m_blind = np.clip(0.60 * m_hid_cal + 0.40 * m_vis_cal, p_blind, 1.0).astype(np.float32)

    # Product-of-experts sharpening of the structural+physics head using distance-blind physics
    mean_pb = float(np.mean(p_blind, dtype=np.float64))
    mean_mb = float(np.mean(m_blind, dtype=np.float64))
    lo_pb0 = np.float32(math.log(max(mean_pb, 1e-7) / (1.0 - min(mean_pb, 1.0 - 1e-7))))
    lo_mb0 = np.float32(math.log(max(mean_mb, 1e-7) / (1.0 - min(mean_mb, 1.0 - 1e-7))))

    p_poe = adhr._expit(adhr._logit(p_full_raw) + np.float32(beta_poe) * (adhr._logit(p_blind) - lo_pb0))
    m_poe = adhr._expit(adhr._logit(m_full_raw) + np.float32(beta_poe) * (adhr._logit(m_blind) - lo_mb0))

    norm_pj = float(k_target) / max(float(np.sum(p_poe, dtype=np.float64)), 1e-6)
    m_target_j = float(np.sum(m_full_raw, dtype=np.float64)) * (
        float(k_target) / max(float(np.sum(p_full_raw, dtype=np.float64)), 1e-6)
    )
    norm_mj = m_target_j / max(float(np.sum(m_poe, dtype=np.float64)), 1e-6)
    p_joint = np.clip(p_poe * np.float32(norm_pj), 0.0, 1.0)
    m_joint = np.clip(m_poe * np.float32(norm_mj), p_joint, 1.0)

    # Smooth spatial completeness deficit gate w_blind(d_vis):
    # strictly 0 for d_vis <= 3.5 px (prevents visible-fault flank bleed),
    # smoothly rising to w_blind_max in blind basins (d_vis >= 15-25 px)
    d_excess = np.maximum(d_vis_act - np.float32(3.5), 0.0)
    w_blind = (np.float32(w_blind_max) * (1.0 - np.exp(-((d_excess / np.float32(10.0)) ** 2)))).astype(np.float32)

    p_mix = (1.0 - w_blind) * p_joint + w_blind * p_blind
    m_mix = (1.0 - w_blind) * m_joint + w_blind * m_blind

    # Final exact total-expectation calibration to k_target
    final_scale = float(k_target) / max(float(np.sum(p_mix, dtype=np.float64)), 1e-6)
    p_out = np.clip(p_mix * np.float32(final_scale), 0.0, 1.0).astype(np.float32)
    m_out = np.clip(m_mix * np.float32(min(final_scale, 1.15)), p_out, 1.0).astype(np.float32)
    return p_out, m_out


def predict_mpsc_fold(
    grid,
    mpsc_sources: list[np.ndarray],
    director: dict[str, np.ndarray],
    visible: np.ndarray,
    train_quad_mask: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Exp 01 (`MPSC-88`): 62 label-blind multi-physics channels + strand continuity,
    strictly zero visible-catalogue geometry features.
    """
    if np.any(train_quad_mask & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training mask intersects test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)

    dom_vis_tr = train_quad_mask[ys_fp, xs_fp]
    clfs_vis, regs_vis = fit_diverse_dual_ensemble(
        mpsc_sources, dom_vis_tr, visible & train_quad_mask, fp, seed=seed + 11, max_zero_neg=150_000
    )

    dom_hid_tr = (train_quad_mask & ~visible)[ys_fp, xs_fp]
    clfs_hid, regs_hid = fit_diverse_dual_ensemble(
        mpsc_sources, dom_hid_tr, train_truth, fp, seed=seed + 29, max_zero_neg=150_000
    )

    n_vis_tr = max(float((visible & train_quad_mask).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    n_vis_test = float((visible & test_region).sum())
    k_est = max(n_vis_test * hid_ratio, 50.0)

    # Evaluate p_vis on ALL of test_region first so visible traces absorb their own mass
    all_test_idx = np.flatnonzero((fp & test_region)[ys_fp, xs_fp])
    p_vis_all, m_vis_all = predict_mvrd_dual_chunked(clfs_vis, regs_vis, mpsc_sources, all_test_idx)
    phys_vis_all_sum = float(np.sum(p_vis_all, dtype=np.float64))

    d_vis_grid = ndi.distance_transform_edt(~visible).astype(np.float32)
    allowed = fp & test_region & (d_vis_grid > 2.0)
    allow_sub = allowed[ys_fp[all_test_idx], xs_fp[all_test_idx]]
    act_idx = all_test_idx[allow_sub]

    p_vis_raw = p_vis_all[allow_sub]
    m_vis_raw = m_vis_all[allow_sub]
    p_hid_raw, m_hid_raw = predict_mvrd_dual_chunked(clfs_hid, regs_hid, mpsc_sources, act_idx)

    d_act_mpsc = d_vis_grid[ys_fp[act_idx], xs_fp[act_idx]]
    far_m = d_act_mpsc > 3.5
    scale_hid = float(k_est) / max(float(np.sum(p_hid_raw, dtype=np.float64)), 1e-6)
    if np.any(far_m):
        scale_vis = (max(float(np.sum(p_hid_raw[far_m], dtype=np.float64)), 1e-6) * scale_hid) / max(
            float(np.sum(p_vis_raw[far_m], dtype=np.float64)), 1e-6
        )
    else:
        scale_vis = float(k_est) / max(phys_vis_all_sum, n_vis_test, 1e-6)
    p_vis_cal = np.clip(p_vis_raw * np.float32(scale_vis), 0.0, 1.0)
    mv_rat = float(np.sum(m_vis_raw, dtype=np.float64)) / max(float(np.sum(p_vis_raw, dtype=np.float64)), 1e-6)
    m_vis_cal = np.clip(
        m_vis_raw * np.float32((float(np.sum(p_vis_cal, dtype=np.float64)) * mv_rat) / max(float(np.sum(m_vis_raw, dtype=np.float64)), 1e-6)),
        p_vis_cal,
        1.0,
    )

    p_hid_cal = np.clip(p_hid_raw * np.float32(scale_hid), 0.0, 1.0)
    m_ratio = float(np.sum(m_hid_raw, dtype=np.float64)) / max(float(np.sum(p_hid_raw, dtype=np.float64)), 1e-6)
    m_hid_cal = np.clip(
        m_hid_raw * np.float32((float(k_est) * m_ratio) / max(float(np.sum(m_hid_raw, dtype=np.float64)), 1e-6)),
        p_hid_cal,
        1.0,
    )

    p_comb = (0.60 * p_hid_cal + 0.40 * p_vis_cal).astype(np.float32)
    m_comb = np.clip(0.60 * m_hid_cal + 0.40 * m_vis_cal, p_comb, 1.0).astype(np.float32)

    p_grid, m_grid = strand_enhance_probabilities(
        p_comb, m_comb, act_idx, ys_fp, xs_fp, director, grid.shape, strength=0.32
    )
    alloc = emit.dinkelbach_allocate(
        p_grid,
        m_grid,
        allowed,
        budget=None,
        k_truth=k_est,
        min_spacing_px=2.05,
        dinkelbach_iters=7,
    )
    return alloc.emitted.astype(np.float32), p_grid, {
        "n_dots": int(alloc.n_dots),
        "k_truth_est": float(k_est),
        "surrogate_dti": float(alloc.surrogate_dti),
        "_shared_mpsc": (p_vis_raw, m_vis_raw, p_hid_raw, m_hid_raw, phys_vis_all_sum),
    }


def predict_mvrd_fold(
    grid,
    mpsc_sources: list[np.ndarray],
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    director: dict[str, np.ndarray],
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    shared_mpsc: tuple | None = None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Exp 03 (`H88-MVRD`): 85-feature completeness-gated ensemble + strand continuity
    + exact Dinkelbach CELF allocation.
    """
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)

    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
    full_sources = [*mpsc_sources, X_vis22_mm, d_over_w_fp]

    dom_hid_tr = (train_regions & ~visible)[ys_fp, xs_fp]
    clfs_full, regs_full = fit_diverse_dual_ensemble(
        full_sources, dom_hid_tr, train_truth, fp, seed=seed + 97, max_zero_neg=220_000
    )

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    n_vis_test = float((visible & test_region).sum())
    k_est = max(n_vis_test * hid_ratio, 50.0)

    all_test_idx = np.flatnonzero((fp & test_region)[ys_fp, xs_fp])
    d_vis_grid = ndi.distance_transform_edt(~visible).astype(np.float32)
    allowed = fp & test_region & (d_vis_grid > 2.0)
    allow_sub = allowed[ys_fp[all_test_idx], xs_fp[all_test_idx]]
    act_idx = all_test_idx[allow_sub]

    if shared_mpsc is not None:
        p_pvis_raw, m_pvis_raw, p_phid_raw, m_phid_raw, phys_vis_all_sum = shared_mpsc
    else:
        dom_vis_tr = train_regions[ys_fp, xs_fp]
        clfs_pvis, regs_pvis = fit_diverse_dual_ensemble(
            mpsc_sources, dom_vis_tr, visible & train_regions, fp, seed=seed + 31, max_zero_neg=220_000
        )
        clfs_phid, regs_phid = fit_diverse_dual_ensemble(
            mpsc_sources, dom_hid_tr, train_truth, fp, seed=seed + 67, max_zero_neg=220_000
        )
        p_pvis_all, m_pvis_all = predict_mvrd_dual_chunked(clfs_pvis, regs_pvis, mpsc_sources, all_test_idx)
        phys_vis_all_sum = float(np.sum(p_pvis_all, dtype=np.float64))
        p_pvis_raw = p_pvis_all[allow_sub]
        m_pvis_raw = m_pvis_all[allow_sub]
        p_phid_raw, m_phid_raw = predict_mvrd_dual_chunked(clfs_phid, regs_phid, mpsc_sources, act_idx)

    p_full_raw, m_full_raw = predict_mvrd_dual_chunked(clfs_full, regs_full, full_sources, act_idx)

    p_fused, m_fused = completeness_gated_fuse(
        p_full_raw,
        m_full_raw,
        p_pvis_raw,
        m_pvis_raw,
        p_phid_raw,
        m_phid_raw,
        d_vis_fp[act_idx],
        k_est,
        phys_vis_all_sum=phys_vis_all_sum,
        n_vis_test=n_vis_test,
        beta_poe=0.35,
        w_blind_max=0.42,
    )

    p_grid, m_grid = strand_enhance_probabilities(
        p_fused, m_fused, act_idx, ys_fp, xs_fp, director, grid.shape, strength=0.30
    )
    alloc = emit.dinkelbach_allocate(
        p_grid,
        m_grid,
        allowed,
        budget=None,
        k_truth=k_est,
        min_spacing_px=2.05,
        dinkelbach_iters=8,
    )
    return alloc.emitted.astype(np.float32), p_grid, {
        "n_dots": int(alloc.n_dots),
        "k_truth_est": float(k_est),
        "surrogate_dti": float(alloc.surrogate_dti),
        "width_law": wlaw.to_json(),
    }


def fit_and_emit_production_mvrd(
    grid,
    mpsc_sources: list[np.ndarray],
    director: dict[str, np.ndarray],
    folds_by_seed: list[tuple[int, list[dict]]],
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
    halo_constraints: np.ndarray | None = None,
    halo_max_hits: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Fit full-Nevada 4-quadrant OOF cross-fitted H88-MVRD production model and
    emit discrete ``{0, 1}`` binary GeoTIFF predictions via exact Dinkelbach CELF.
    """
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    cache_npz = Path(cache_dir) / "prod_mvrd_v1.npz"
    if cache_npz.is_file() and halo_constraints is None:
        z = np.load(cache_npz, allow_pickle=False)
        emitted = np.zeros(grid.shape, dtype=np.float32)
        dyx = z["dots_yx"]
        emitted[dyx[:, 0], dyx[:, 1]] = 1.0
        p_surface = adhr.scatter_fp(z["p_fp"], ys_fp, xs_fp, grid.shape)
        m_surface = adhr.scatter_fp(z["m_fp"], ys_fp, xs_fp, grid.shape)
        meta = json.loads(str(z["meta_json"]))
        return emitted, p_surface, m_surface, meta

    d_fullcat = ndi.distance_transform_edt(~grid.catalogue).astype(np.float32)
    allowed_prod = fp & (d_fullcat > 2.0)
    act_idx = np.flatnonzero(allowed_prod[ys_fp, xs_fp])
    all_fp_idx = np.arange(ys_fp.size, dtype=np.int64)

    # 1. Strict 4-quadrant out-of-fold cross-fitting for BOTH distance-blind physics heads
    hid_union = np.zeros(grid.shape, dtype=bool)
    ratios: list[float] = []
    for _s, f_list in folds_by_seed:
        vis_s = f_list[0]["visible"]
        reg_s = np.zeros(grid.shape, dtype=bool)
        tr_s = np.zeros(grid.shape, dtype=bool)
        for fq in f_list:
            reg_s |= fq["region"]
            tr_s |= fq["truth"]
        hid_union |= tr_s
        ratios.append(float(tr_s.sum()) / max(float((vis_s & reg_s).sum()), 1.0))

    p_pvis_all = np.zeros(ys_fp.size, dtype=np.float32)
    m_pvis_all = np.zeros(ys_fp.size, dtype=np.float32)
    p_phid_act = np.zeros(act_idx.size, dtype=np.float32)
    m_phid_act = np.zeros(act_idx.size, dtype=np.float32)

    quad = np.full(grid.shape, -1, dtype=np.int8)
    ym, xm = int(np.median(ys_fp)), int(np.median(xs_fp))
    gy, gx = np.ogrid[: grid.shape[0], : grid.shape[1]]
    quad[(gy < ym) & (gx < xm) & fp] = 0
    quad[(gy < ym) & (gx >= xm) & fp] = 1
    quad[(gy >= ym) & (gx < xm) & fp] = 2
    quad[(gy >= ym) & (gx >= xm) & fp] = 3
    q_fp = quad[ys_fp, xs_fp]
    q_act = quad[ys_fp[act_idx], xs_fp[act_idx]]

    for q_id in range(4):
        tr_q_grid = fp & (quad != q_id)
        dom_vis_q = tr_q_grid[ys_fp, xs_fp]
        c_v, r_v = fit_diverse_dual_ensemble(
            mpsc_sources, dom_vis_q, grid.catalogue & tr_q_grid, fp, seed=882410 + 13 * q_id, max_zero_neg=220_000
        )
        sel_all_q = np.flatnonzero(q_fp == q_id)
        pv_q, mv_q = predict_mvrd_dual_chunked(c_v, r_v, mpsc_sources, all_fp_idx[sel_all_q])
        p_pvis_all[sel_all_q] = pv_q
        m_pvis_all[sel_all_q] = mv_q
        del c_v, r_v, pv_q, mv_q

        dom_hid_q = (tr_q_grid & ~(grid.catalogue & ~hid_union))[ys_fp, xs_fp]
        c_h, r_h = fit_diverse_dual_ensemble(
            mpsc_sources, dom_hid_q, hid_union & tr_q_grid, fp, seed=882510 + 17 * q_id, max_zero_neg=220_000
        )
        sel_act_q = np.flatnonzero(q_act == q_id)
        ph_q, mh_q = predict_mvrd_dual_chunked(c_h, r_h, mpsc_sources, act_idx[sel_act_q])
        p_phid_act[sel_act_q] = ph_q
        m_phid_act[sel_act_q] = mh_q
        del c_h, r_h, ph_q, mh_q
        gc.collect()

    phys_vis_all_sum = float(np.sum(p_pvis_all, dtype=np.float64))
    p_pvis_act = p_pvis_all[act_idx]
    m_pvis_act = m_pvis_all[act_idx]
    del p_pvis_all, m_pvis_all

    # 2. Structural + physics multi-seed ensemble fitted on buffered whole-component draws
    struct_clfs: list[dict] = []
    struct_regs: list[HistGradientBoostingRegressor] = []
    w_laws: list[damagezone_envelope.WidthLaw] = []

    for seed, folds in folds_by_seed:
        vis_s = folds[0]["visible"]
        X_v22, dv_s, cl_s = adhr.compute_visible_struct_fp(grid, vis_s, sense_src, scarp_fields, cache_dir, f"seed{seed}")
        reg_s = np.zeros(grid.shape, dtype=bool)
        tr_s = np.zeros(grid.shape, dtype=bool)
        for f in folds:
            reg_s |= f["region"]
            tr_s |= f["truth"]
        pop_fp = tr_s[ys_fp, xs_fp]
        wlaw = damagezone_envelope.fit_width_law(cl_s, dv_s, pop_fp, quantile=0.90, l0_px=40.0)
        w_laws.append(wlaw)
        dow_s = (dv_s / np.maximum(wlaw.half_width(cl_s), 1e-6)).astype(np.float32)
        dom_s = (reg_s & ~vis_s)[ys_fp, xs_fp]
        cs, rs = fit_diverse_dual_ensemble(
            [*mpsc_sources, X_v22, dow_s], dom_s, tr_s, fp, seed=882600 + seed, max_zero_neg=230_000
        )
        struct_clfs.extend(cs)
        struct_regs.extend(rs)
        del X_v22, dv_s, cl_s, dow_s, dom_s, reg_s, tr_s
        gc.collect()

    X_v22_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
        grid, grid.catalogue, sense_src, scarp_fields, cache_dir, "prod_fullcat"
    )
    hw_prod = np.mean([wl.half_width(cl_prod) for wl in w_laws], axis=0).astype(np.float32)
    dow_prod = (dv_prod / np.maximum(hw_prod, 1e-6)).astype(np.float32)
    prod_sources = [*mpsc_sources, X_v22_prod, dow_prod]

    hid_ratio_mean = float(np.mean(ratios))
    n_cat = float(grid.catalogue.sum())
    k_prod = n_cat * hid_ratio_mean

    p_full_act, m_full_act = predict_mvrd_dual_chunked(struct_clfs, struct_regs, prod_sources, act_idx)
    d_vis_act = dv_prod[act_idx].copy()
    del struct_clfs, struct_regs, prod_sources, X_v22_prod, dv_prod, cl_prod, hw_prod, dow_prod
    gc.collect()

    p_fused, m_fused = completeness_gated_fuse(
        p_full_act,
        m_full_act,
        p_pvis_act,
        m_pvis_act,
        p_phid_act,
        m_phid_act,
        d_vis_act,
        k_prod,
        phys_vis_all_sum=phys_vis_all_sum,
        n_vis_test=n_cat,
        beta_poe=0.35,
        w_blind_max=0.42,
    )
    del p_full_act, m_full_act, p_pvis_act, m_pvis_act, p_phid_act, m_phid_act, d_vis_act
    gc.collect()

    p_surface, m_surface = strand_enhance_probabilities(
        p_fused, m_fused, act_idx, ys_fp, xs_fp, director, grid.shape, strength=0.30
    )
    del p_fused, m_fused
    gc.collect()

    alloc = emit.dinkelbach_allocate(
        p_surface,
        m_surface,
        allowed_prod,
        budget=None,
        k_truth=k_prod,
        min_spacing_px=2.05,
        dinkelbach_iters=8,
        halo_constraints=halo_constraints,
        halo_max_hits=halo_max_hits,
    )
    meta = {
        "n_dots": int(alloc.n_dots),
        "k_truth_est": float(k_prod),
        "surrogate_dti": float(alloc.surrogate_dti),
        "dinkelbach_rounds": int(alloc.rounds),
        "flank_exclusion_px": 2.0,
        "min_spacing_px": 2.05,
        "halo_constrained": bool(halo_constraints is not None),
        "median_d_cat_px": float(np.median(d_fullcat[alloc.emitted])) if alloc.n_dots else 0.0,
        "frac_gt_10px": float((d_fullcat[alloc.emitted] > 10.0).mean()) if alloc.n_dots else 0.0,
        "frac_gt_25px": float((d_fullcat[alloc.emitted] > 25.0).mean()) if alloc.n_dots else 0.0,
    }
    dy, dx = np.nonzero(alloc.emitted)
    np.savez_compressed(
        cache_npz,
        dots_yx=np.column_stack([dy, dx]).astype(np.int32),
        p_fp=p_surface[ys_fp, xs_fp].astype(np.float32),
        m_fp=m_surface[ys_fp, xs_fp].astype(np.float32),
        meta_json=np.array(json.dumps(meta)),
    )
    return alloc.emitted.astype(np.float32), p_surface, m_surface, meta


def enforce_sparse_registry_overlap_cap(
    emitted: np.ndarray,
    p_surface: np.ndarray,
    m_surface: np.ndarray,
    allowed_prod: np.ndarray,
    k_prod: float,
    inventory: dict,
    root: Path,
    footprint: np.ndarray,
    max_overlap_cap: float = 0.668,
) -> tuple[np.ndarray, dict]:
    """Ensure 3-px forward dot overlap <= max_overlap_cap (< 0.70) against ALL
    sparse dot-field rasters in ``inventory`` (never exempting ``17GEMSDOE`` from
    the downstream literal audit, while redirecting marginal submodular budget
    away from prior sparse submissions such as archived ``H88-ADHR`` onto novel
    blind-basin and monoclinal-scarp fault strands).
    """
    cand_cap = 450_000
    p_f = np.where(allowed_prod, np.clip(p_surface, 0.0, 1.0), 0.0).astype(np.float32)
    ek = emit.expected_credit(p_f)
    ys, xs = np.nonzero(allowed_prod & (ek > 0.0))
    if ys.size > cand_cap:
        top_idx = np.argpartition(-ek[ys, xs], cand_cap)[:cand_cap]
        ys, xs = ys[top_idx], xs[top_idx]
    ord_init = np.argsort(-ek[ys, xs], kind="stable")
    ys = ys[ord_init].astype(np.int32)
    xs = xs[ord_init].astype(np.int32)

    cur_dots = emitted > 0.5
    n_target = int(cur_dots.sum())
    n_cur = max(n_target, 1)
    active_halos: list[np.ndarray] = []
    active_files: list[str] = []
    active_labels: list[str] = []

    n_fp = int(footprint.sum())
    sparse_entries = []
    for entry in inventory["rasters"]:
        with rasterio.open(Path(root) / entry["cache_file"]) as ds:
            arr = ds.read(1)
        pos = np.isfinite(arr) & (arr > 0) & footprint
        if int(pos.sum()) > int(0.20 * n_fp):
            continue
        halo3 = ndi.distance_transform_edt(~pos) <= 3.000001
        sparse_entries.append((entry["cache_file"], f"{entry['repo_first']}::{Path(entry['cache_file']).name}", halo3))
        ov = float(halo3[cur_dots].sum()) / float(n_cur)
        if ov > max_overlap_cap:
            active_halos.append(halo3[ys, xs].astype(np.uint8))
            active_files.append(entry["cache_file"])
            active_labels.append(f"{entry['repo_first']}::{Path(entry['cache_file']).name}")

    if not active_halos:
        return emitted, {"halo_constrained": False, "active_constraint_repos": []}

    hc = np.vstack(active_halos)
    max_hits = int(math.floor(max_overlap_cap * n_target))
    alloc = None
    for _round in range(4):
        alloc = emit.dinkelbach_allocate(
            p_surface,
            m_surface,
            allowed_prod,
            budget=n_target,
            k_truth=k_prod,
            min_spacing_px=2.05,
            dinkelbach_iters=6,
            candidate_cap=cand_cap,
            halo_constraints=hc,
            halo_max_hits=max_hits,
        )
        new_dots = alloc.emitted
        n_new = max(int(new_dots.sum()), 1)
        max_hits = int(math.floor(max_overlap_cap * n_new))
        worst_ov = 0.0
        newly_violated = False
        for cfile, clabel, halo3 in sparse_entries:
            ov = float(halo3[new_dots].sum()) / float(n_new)
            worst_ov = max(worst_ov, ov)
            if ov > 0.690 and cfile not in active_files:
                active_halos.append(halo3[ys, xs].astype(np.uint8))
                active_files.append(cfile)
                active_labels.append(clabel)
                hc = np.vstack(active_halos)
                newly_violated = True
        if not newly_violated and worst_ov <= 0.690:
            break

    return alloc.emitted.astype(np.float32), {
        "halo_constrained": True,
        "active_constraint_repos": active_labels,
        "n_dots": int(alloc.n_dots),
        "surrogate_dti": float(alloc.surrogate_dti),
    }
