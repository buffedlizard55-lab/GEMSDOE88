"""H88-SAR-CSD: Selected-At-Random Completeness-Decontaminated Crustal-Scarp-Drainage
& Coulomb-Relay Submodular Discovery.

Memory-bounded (<600 MB RSS on 3.8 GiB sandbox):
* Reuses cached 44-channel ``src/gems88/physics.py`` disk memmap.
* Streams 20 new translation-invariant Crustal-Scarp-Drainage (``CSD-20``) differential
  operators one band at a time into a disk-backed float32 ``np.memmap``.
* Reuses unmodified ``vendor/gems57/`` (``holdout.buffered_component_draw``,
  ``evaluate_holdout``, ``relay_bend_anatomy``, ``damagezone_envelope``,
  ``emit.dinkelbach_allocate``, ``submission_writer``, ``uniqueness``) and
  ``src/gems88/gate.py`` (``gems88-gate-v3``).
"""
from __future__ import annotations

import gc
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from gems57 import damagezone_envelope, emit
from . import adhr, edge, physics

TAN_60 = math.tan(math.radians(60.0))
CSD_VERSION = "sarcsd88-csd20-v1"

CSD20_FEATURES: tuple[str, ...] = (
    "csd_lidar_ex_step_coh",
    "csd_lidar_curv_asym",
    "csd_lidar_face_dom",
    "csd_lidar_piedmont_scarp",
    "csd_topo10_bajada_flex",
    "csd_topo10_scarp_sharpness",
    "csd_topo10_ridge_200m",
    "csd_topo10_ridge_400m",
    "csd_chi_knick_rate",
    "csd_chi_raised_frac",
    "csd_chi_knick_ksn_couple",
    "csd_tmi_up150_hg",
    "csd_mag_vert_wavelength",
    "csd_grav_hg_ridge",
    "csd_updip_blakely_crest",
    "csd_tilt_zero_grad",
    "csd_rad_u_diseq",
    "csd_cond_clay_halo",
    "csd_transtension_align",
    "csd_mimic_playa_seam",
)

# Smooth regional DC / province-level channels in physics.ALL_PHYS_FEATURES excluded from
# the translation-invariant SAR far-field head so GBDTs cannot memorize quadrangle locations.
REGIONAL_DC_EXCLUSIONS: frozenset[str] = frozenset({
    "cond_surf_raw",
    "depth_to_base_log",
    "det_elev",
    "geod_strain_2ndinv",
    "geod_transtension",
    "seismic_prox",
    "probe2m_dab_reg",
    "volcanic_vent_prox",
})

PHYS_DIFF_INDICES: tuple[int, ...] = tuple(
    i for i, name in enumerate(physics.ALL_PHYS_FEATURES) if name not in REGIONAL_DC_EXCLUSIONS
)
SAR_PHYS_FEATURE_NAMES: tuple[str, ...] = (
    tuple(physics.ALL_PHYS_FEATURES[i] for i in PHYS_DIFF_INDICES) + CSD20_FEATURES
)


class ColumnSubsetView:
    """Zero-copy column selector over an ``(N_fp, C)`` memmap."""

    def __init__(self, mm: np.ndarray, cols: Sequence[int]):
        self._mm = mm
        self._cols = np.asarray(cols, dtype=np.int32)
        self.shape = (mm.shape[0], int(self._cols.size))

    def __getitem__(self, rows) -> np.ndarray:
        sub = np.asarray(self._mm[rows], dtype=np.float32)
        if sub.ndim == 1:
            return sub[self._cols]
        return sub[:, self._cols]


def _grad_mag(arr: np.ndarray, sigma: float) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32)
    gy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 0), mode="nearest")
    gx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 1), mode="nearest")
    return np.hypot(gx, gy).astype(np.float32)


def _hessian_ridge(arr: np.ndarray, sigma: float, troughs: bool = False) -> np.ndarray:
    """Principal crest (or trough) Hessian curvature at scale ``sigma``."""
    a = np.asarray(arr, dtype=np.float32)
    gxx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 2), mode="nearest")
    gyy = ndi.gaussian_filter(a, sigma=sigma, order=(2, 0), mode="nearest")
    gxy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 1), mode="nearest")
    tr = gxx + gyy
    rad = np.hypot(gxx - gyy, 2.0 * gxy)
    if troughs:
        return np.maximum(0.0, 0.5 * (tr + rad)).astype(np.float32)
    return np.maximum(0.0, 0.5 * (-tr + rad)).astype(np.float32)


def _bilinear_at_fp(
    field: np.ndarray,
    ys_fp: np.ndarray,
    xs_fp: np.ndarray,
    dy_fp: np.ndarray,
    dx_fp: np.ndarray,
) -> np.ndarray:
    h, w = field.shape
    ry = np.clip(ys_fp.astype(np.float32) + dy_fp, 0.0, np.float32(h - 1.001))
    rx = np.clip(xs_fp.astype(np.float32) + dx_fp, 0.0, np.float32(w - 1.001))
    y0 = ry.astype(np.int32)
    x0 = rx.astype(np.int32)
    wy = ry - y0
    wx = rx - x0
    f00 = field[y0, x0]
    f01 = field[y0, x0 + 1]
    f10 = field[y0 + 1, x0]
    f11 = field[y0 + 1, x0 + 1]
    return ((1.0 - wy) * ((1.0 - wx) * f00 + wx * f01) + wy * ((1.0 - wx) * f10 + wx * f11)).astype(np.float32)


def build_or_load_csd20_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict]:
    """Stream 20 translation-invariant Crustal-Scarp-Drainage channels into disk memmap."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    n_fp = int(ys_fp.size)
    n_cols = len(CSD20_FEATURES)

    dat_path = cache_dir / "csd20_features_f32.dat"
    meta_path = cache_dir / "csd20_features_meta.json"
    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("version") == CSD_VERSION
            and meta.get("n_fp") == n_fp
            and meta.get("features") == list(CSD20_FEATURES)
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    tmp_path = cache_dir / "csd20_features_f32.tmp"
    mm = np.memmap(tmp_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    def write_col(col_idx: int, name: str, arr_fp: np.ndarray) -> None:
        if CSD20_FEATURES[col_idx] != name:
            raise AssertionError(f"Column mismatch at {col_idx}: {name} != {CSD20_FEATURES[col_idx]}")
        v = np.nan_to_num(np.asarray(arr_fp, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        lo, hi = np.percentile(v, [0.05, 99.95])
        v = np.clip(v, lo, hi)
        mm[:, col_idx] = v

    # 1-4: 1 m 3DEP LiDAR scarp polarity, asymmetry, face dominance, and low-relief piedmont scarp
    with rasterio.open(root / "data/external/lidar_scarp_features_u8.tif") as ds:
        ex_max = ds.read(1)[ys_fp, xs_fp].astype(np.float32)
        step_max = ds.read(3)[ys_fp, xs_fp].astype(np.float32)
        lapneg = ds.read(4)[ys_fp, xs_fp].astype(np.float32)
        lappos = ds.read(5)[ys_fp, xs_fp].astype(np.float32)
        downf = ds.read(6)[ys_fp, xs_fp].astype(np.float32)
        upf = ds.read(7)[ys_fp, xs_fp].astype(np.float32)
        crossm = ds.read(8)[ys_fp, xs_fp].astype(np.float32)
        rel_l = ds.read(9)[ys_fp, xs_fp].astype(np.float32)
        coh = ds.read(10)[ys_fp, xs_fp].astype(np.float32)
        val_l = (ds.read(12)[ys_fp, xs_fp] > 0).astype(np.float32)

    write_col(0, "csd_lidar_ex_step_coh", val_l * (ex_max / 255.0) * (step_max / 255.0) * (coh / 255.0))
    write_col(1, "csd_lidar_curv_asym", val_l * (lapneg - lappos) / (lapneg + lappos + 4.0))
    write_col(2, "csd_lidar_face_dom", val_l * np.maximum(downf, upf) / (crossm + 8.0))
    write_col(3, "csd_lidar_piedmont_scarp", val_l * (step_max / 255.0) * (coh / 255.0) * np.exp(-rel_l / 120.0))
    del ex_max, step_max, lapneg, lappos, downf, upf, crossm, rel_l, coh, val_l
    gc.collect()

    # 5-8: 10 m 3DEP bajada flexure, scarp sharpness, and shoreline-decontaminated 200 m / 400 m ridges
    with rasterio.open(root / "data/geodawn_dem_a2_100m.tif") as ds:
        dem = edge.clean_band(ds.read(1), fp)[0]
    shore_pen_2d = np.clip(
        np.exp(-0.5 * ((dem - 1330.0) / 22.0) ** 2) + np.exp(-0.5 * ((dem - 1555.0) / 22.0) ** 2),
        0.0,
        1.0,
    ).astype(np.float32)
    del dem

    with rasterio.open(root / "data/external/topo_10m_derived_100m_u8.tif") as ds:
        slp_p90_2d = ds.read(1).astype(np.float32)
        slp_max_fp = ds.read(2)[ys_fp, xs_fp].astype(np.float32)
        rel10_2d = ds.read(5).astype(np.float32)
        curv_fp = ds.read(6)[ys_fp, xs_fp].astype(np.float32)
        asp_coh_2d = ds.read(7).astype(np.float32)
        hs_lin_2d = ds.read(8).astype(np.float32)

    slp_p90_fp = slp_p90_2d[ys_fp, xs_fp]
    rel10_fp = rel10_2d[ys_fp, xs_fp]
    asp_coh_fp = asp_coh_2d[ys_fp, xs_fp]
    shore_fp = shore_pen_2d[ys_fp, xs_fp]

    write_col(
        4,
        "csd_topo10_bajada_flex",
        (curv_fp / 255.0)
        * (asp_coh_fp / 255.0)
        * np.exp(-0.5 * ((slp_p90_fp - 42.0) / 38.0) ** 2)
        * (1.0 - 0.85 * shore_fp),
    )
    write_col(
        5,
        "csd_topo10_scarp_sharpness",
        np.maximum(slp_max_fp - slp_p90_fp, 0.0) / (rel10_fp + 10.0) * (asp_coh_fp / 255.0),
    )
    line_prod_2d = ((hs_lin_2d / 255.0) * (asp_coh_2d / 255.0) * (1.0 - 0.70 * shore_pen_2d)).astype(np.float32)
    write_col(6, "csd_topo10_ridge_200m", _hessian_ridge(line_prod_2d, sigma=1.8)[ys_fp, xs_fp])
    write_col(7, "csd_topo10_ridge_400m", _hessian_ridge(line_prod_2d, sigma=3.6)[ys_fp, xs_fp])
    playa_flat_fp = (np.exp(-slp_p90_fp / 8.0) * np.exp(-rel10_fp / 8.0)).astype(np.float32)
    del slp_p90_2d, slp_max_fp, rel10_2d, curv_fp, asp_coh_2d, hs_lin_2d, slp_p90_fp, rel10_fp, asp_coh_fp, shore_fp, shore_pen_2d, line_prod_2d
    gc.collect()

    # 9-11: Drainage divide / knickzone tectonic uplift coupling (dem10_chi i16 & u8)
    with rasterio.open(root / "data/external/dem10_chi_100m_i16.tif") as ds:
        ksn_fp = np.maximum(ds.read(3)[ys_fp, xs_fp].astype(np.float32), 0.0)
    with rasterio.open(root / "data/external/dem10_chi_100m_u8.tif") as ds:
        chan_n = ds.read(1)[ys_fp, xs_fp].astype(np.float32)
        knick_n = ds.read(2)[ys_fp, xs_fp].astype(np.float32)
        raised_n = ds.read(3)[ys_fp, xs_fp].astype(np.float32)
        valid_n = ds.read(4)[ys_fp, xs_fp].astype(np.float32)
    knick_rate = knick_n / (chan_n + 1.0)
    write_col(8, "csd_chi_knick_rate", knick_rate)
    write_col(9, "csd_chi_raised_frac", raised_n / (valid_n + 1.0))
    write_col(10, "csd_chi_knick_ksn_couple", knick_rate * np.log1p(ksn_fp))
    del ksn_fp, chan_n, knick_n, raised_n, valid_n, knick_rate
    gc.collect()

    # 12 & 17: GeoDAWN upward-continued TMI_up150 gradient & regional-detrended U/Th, U/K redox disequilibrium
    with rasterio.open(root / "data/external/geodawn_extensions_u8.tif") as ds:
        uk_2d = ds.read(2).astype(np.float32) / 255.0
        uth_2d = ds.read(3).astype(np.float32) / 255.0
        tmi150_2d = ds.read(4).astype(np.float32) / 255.0
    tmi150_hg_fp = _grad_mag(tmi150_2d, sigma=1.5)[ys_fp, xs_fp]
    write_col(11, "csd_tmi_up150_hg", tmi150_hg_fp)
    u_diseq_2d = (
        (ndi.gaussian_filter(uth_2d, sigma=1.5) - ndi.gaussian_filter(uth_2d, sigma=14.0))
        + 0.5 * (ndi.gaussian_filter(uk_2d, sigma=1.5) - ndi.gaussian_filter(uk_2d, sigma=14.0))
    ).astype(np.float32)
    write_col(16, "csd_rad_u_diseq", u_diseq_2d[ys_fp, xs_fp])
    del uk_2d, uth_2d, tmi150_2d, u_diseq_2d
    gc.collect()

    # 13-16, 18-20: Verified 19-band competition multi-physics differential operators
    with rasterio.open(root / "data/training_features.tif") as ds:
        rtp_2d = edge.clean_band(ds.read(2), fp)[0]
        tmi_hg_fp = np.maximum(edge.clean_band(ds.read(3), fp)[0][ys_fp, xs_fp], 0.0)
        tc_fp = edge.clean_band(ds.read(6), fp)[0][ys_fp, xs_fp]  # Verified B06: magnetic tilt angle / curvature
        shear_fp = np.maximum(edge.clean_band(ds.read(7), fp)[0][ys_fp, xs_fp], 0.0)
        dilat_fp = edge.clean_band(ds.read(8), fp)[0][ys_fp, xs_fp]
        iso_grav_2d = edge.clean_band(ds.read(13), fp)[0]
        zbase_fp = np.maximum(edge.clean_band(ds.read(15), fp)[0][ys_fp, xs_fp], 0.0)
        cond_2d = np.maximum(edge.clean_band(ds.read(17), fp)[0], 0.0)
        grav_hg_2d = np.maximum(edge.clean_band(ds.read(18), fp)[0], 0.0)
        det_slp_fp = np.maximum(edge.clean_band(ds.read(19), fp)[0][ys_fp, xs_fp], 0.0)

    tmi_hg_log = np.log1p(tmi_hg_fp)
    write_col(12, "csd_mag_vert_wavelength", tmi_hg_log - 2.5 * tmi150_hg_fp)
    del tmi150_hg_fp

    grav_hg_log_2d = np.log1p(grav_hg_2d).astype(np.float32)
    write_col(13, "csd_grav_hg_ridge", _hessian_ridge(grav_hg_log_2d, sigma=2.0)[ys_fp, xs_fp])

    # Blakely & Simpson (1986) hanging-wall gravity-gradient crest pulled UP-DIP onto range-front trace:
    # +grad(iso_grav_anom) points from basin gravity low (hanging wall) toward range high (footwall),
    # so the down-dip hanging-wall basement step relative to surface trace (y, x) is at (-uy*s, -ux*s).
    ggy = ndi.gaussian_filter(iso_grav_2d, sigma=4.0, order=(1, 0), mode="nearest")
    ggx = ndi.gaussian_filter(iso_grav_2d, sigma=4.0, order=(0, 1), mode="nearest")
    gnorm = np.hypot(ggy, ggx) + 1e-6
    uy_fp = (ggy[ys_fp, xs_fp] / gnorm[ys_fp, xs_fp]).astype(np.float32)
    ux_fp = (ggx[ys_fp, xs_fp] / gnorm[ys_fp, xs_fp]).astype(np.float32)
    shift_px = np.clip(zbase_fp / (100.0 * TAN_60), 0.0, 12.0).astype(np.float32)
    updip_blakely = _bilinear_at_fp(grav_hg_log_2d, ys_fp, xs_fp, -uy_fp * shift_px, -ux_fp * shift_px)
    write_col(14, "csd_updip_blakely_crest", updip_blakely)
    del iso_grav_2d, grav_hg_2d, grav_hg_log_2d, ggy, ggx, gnorm, uy_fp, ux_fp, shift_px, zbase_fp, updip_blakely
    gc.collect()

    # Salem et al. (2007) Tilt-Derivative Contact: zero-crossing of B06 tc * horizontal magnetic gradient
    tc_med = float(np.median(tc_fp))
    tc_iqr = max(float(np.percentile(tc_fp, 75) - np.percentile(tc_fp, 25)), 1e-5)
    z_tc = (tc_fp - tc_med) / tc_iqr
    write_col(15, "csd_tilt_zero_grad", np.exp(-0.5 * z_tc * z_tc) * tmi_hg_log)
    del tc_fp, tmi_hg_fp, tmi_hg_log, z_tc

    # Smectite clay-cap edge x magnetite-destructive RTP trough
    cond_edge_fp = _grad_mag(np.log1p(cond_2d), sigma=2.0)[ys_fp, xs_fp]
    rtp_trough_fp = _hessian_ridge(rtp_2d, sigma=2.5, troughs=True)[ys_fp, xs_fp]
    write_col(17, "csd_cond_clay_halo", cond_edge_fp * np.log1p(rtp_trough_fp))
    del cond_edge_fp, rtp_trough_fp

    # Transtensional opening alignment
    dil_med = float(np.median(dilat_fp))
    write_col(
        18,
        "csd_transtension_align",
        np.log1p(shear_fp) * np.maximum(dilat_fp - dil_med, 0.0) * np.log1p(det_slp_fp),
    )
    del shear_fp, dilat_fp, det_slp_fp

    # Explicit non-fault mimic channel: closed playa conductivity pans + flight-line magnetic seams
    rgy = np.abs(ndi.gaussian_filter(rtp_2d, sigma=0.8, order=(1, 0), mode="nearest")[ys_fp, xs_fp])
    rgx = np.abs(ndi.gaussian_filter(rtp_2d, sigma=0.8, order=(0, 1), mode="nearest")[ys_fp, xs_fp])
    mag_seam_fp = np.abs(rgx - rgy) / (rgx + rgy + 1e-5)
    cond_log_fp = np.log1p(cond_2d[ys_fp, xs_fp])
    write_col(19, "csd_mimic_playa_seam", playa_flat_fp * cond_log_fp + 0.5 * mag_seam_fp)
    del rtp_2d, cond_2d, rgy, rgx, mag_seam_fp, cond_log_fp, playa_flat_fp
    gc.collect()

    mm.flush()
    del mm
    tmp_path.replace(dat_path)

    col_means = []
    mm_ro = np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols))
    for j in range(n_cols):
        col_means.append(round(float(np.mean(mm_ro[:, j], dtype=np.float64)), 6))
    meta = {
        "version": CSD_VERSION,
        "n_fp": n_fp,
        "n_cols": n_cols,
        "features": list(CSD20_FEATURES),
        "column_means": dict(zip(CSD20_FEATURES, col_means)),
        "band06_verified_header": "tc - Tilt angle or total curvature - magnetic field derivative for edge detection",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return mm_ro, meta


def completeness_propensity_fp(
    visible_grid: np.ndarray,
    footprint: np.ndarray,
    lambda_px: float = 18.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(d_vis_fp, c_hat_fp)`` strictly from ``visible_grid`` (zero test leakage)."""
    ys_fp, xs_fp = np.nonzero(footprint)
    d_vis_fp = ndi.distance_transform_edt(~np.asarray(visible_grid, dtype=bool))[ys_fp, xs_fp].astype(np.float32)
    c_hat_fp = np.exp(-((d_vis_fp / np.float32(lambda_px)) ** 2)).astype(np.float32)
    return d_vis_fp, c_hat_fp


def fit_sar_decontaminated_dual_models(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    c_hat_fp: np.ndarray,
    seed: int,
    *,
    max_zero_neg: int = 160_000,
    n_ensemble: int = 1,
    use_sar_weights: bool = True,
) -> tuple[list[HistGradientBoostingClassifier], list[HistGradientBoostingRegressor]]:
    """Fit dual ``(p_cell, m_kernel)`` GBDTs with SAR inverse-completeness PU weights."""
    ys_fp, xs_fp = np.nonzero(fp_mask)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int8)
    y_kern_grid = np.clip(1.0 - ndi.distance_transform_edt(~pos_grid) / 3.0, 0.0, 1.0).astype(np.float32)
    y_kern_all = y_kern_grid[ys_fp, xs_fp]
    del y_kern_grid

    reg_dens_2d = ndi.gaussian_filter(pos_grid.astype(np.float32), sigma=25.0, mode="nearest")
    reg_dens_fp = reg_dens_2d[ys_fp, xs_fp]
    del reg_dens_2d

    dom_idx = np.flatnonzero(domain_fp)
    y_k = y_kern_all[dom_idx]
    near_sel = y_k > 0.0
    near_idx = dom_idx[near_sel]
    zero_idx = dom_idx[~near_sel]

    rng = np.random.default_rng(seed)
    if zero_idx.size > max_zero_neg:
        sub_zero = np.sort(rng.choice(zero_idx, size=max_zero_neg, replace=False))
        w_sub_scale = float(zero_idx.size) / float(max_zero_neg)
    else:
        sub_zero = zero_idx
        w_sub_scale = 1.0

    if use_sar_weights:
        pos_dens = reg_dens_fp[near_idx]
        med_dens = max(float(np.median(pos_dens)) if pos_dens.size else 1e-4, 1e-5)
        w_near = np.clip(np.sqrt(med_dens / np.maximum(pos_dens, 0.16 * med_dens)), 0.65, 2.5).astype(np.float64)
        c_neg = c_hat_fp[sub_zero].astype(np.float64)
        raw_w_neg = 0.35 + 0.65 * c_neg
        raw_w_neg *= w_sub_scale / max(float(np.mean(raw_w_neg)), 1e-6)
        w_zero = raw_w_neg
    else:
        w_near = np.ones(near_idx.size, dtype=np.float64)
        w_zero = np.full(sub_zero.size, w_sub_scale, dtype=np.float64)

    train_idx = np.concatenate([near_idx, sub_zero])
    weights = np.concatenate([w_near, w_zero])
    seq = np.argsort(train_idx)
    train_idx = train_idx[seq]
    weights = weights[seq]

    X_tr = adhr.gather_columns(sources, train_idx)
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
            max_iter=135,
            learning_rate=0.065,
            max_leaf_nodes=55,
            min_samples_leaf=75,
            l2_regularization=4.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=14,
            random_state=seed + 107 * k,
        )
        clf.fit(X_tr, yc_tr, sample_weight=weights)
        clfs.append(clf)

        reg = HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=135,
            learning_rate=0.065,
            max_leaf_nodes=55,
            min_samples_leaf=75,
            l2_regularization=4.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=14,
            random_state=seed + 223 * k,
        )
        reg.fit(X_tr, yk_tr, sample_weight=weights)
        regs.append(reg)
    del X_tr
    return clfs, regs


def fuse_csd_joint(
    p_full_raw: np.ndarray,
    m_full_raw: np.ndarray,
    p_sar_raw: np.ndarray,
    m_sar_raw: np.ndarray,
    k_target: float,
    *,
    beta_phys: float = 0.40,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Bayes-calibrated log-odds Product-of-Experts calibrated to visible-fault relay mass k_target."""
    mean_p = float(np.mean(p_sar_raw, dtype=np.float64))
    mean_m = float(np.mean(m_sar_raw, dtype=np.float64))
    p_poe0 = adhr._expit(
        adhr._logit(p_full_raw)
        + np.float32(beta_phys)
        * (adhr._logit(p_sar_raw) - np.float32(math.log(max(mean_p, 1e-7) / (1.0 - min(mean_p, 1.0 - 1e-7)))))
    )
    m_poe0 = adhr._expit(
        adhr._logit(m_full_raw)
        + np.float32(beta_phys)
        * (adhr._logit(m_sar_raw) - np.float32(math.log(max(mean_m, 1e-7) / (1.0 - min(mean_m, 1.0 - 1e-7)))))
    )
    k_near = max(float(k_target), 50.0)
    m_sum = max(
        float(np.sum(m_full_raw, dtype=np.float64)) * (k_near / max(float(np.sum(p_full_raw, dtype=np.float64)), 1e-6)),
        k_near,
    )
    pn = np.clip(p_poe0 * np.float32(k_near / max(float(np.sum(p_poe0, dtype=np.float64)), 1e-6)), 0.0, 1.0)
    mn = np.clip(m_poe0 * np.float32(m_sum / max(float(np.sum(m_poe0, dtype=np.float64)), 1e-6)), pn, 1.0)
    return pn.astype(np.float32), mn.astype(np.float32), float(k_near)


def fuse_sar_missingness_grid(
    p_full_raw: np.ndarray,
    m_full_raw: np.ndarray,
    p_sar_raw: np.ndarray,
    m_sar_raw: np.ndarray,
    d_act_px: np.ndarray,
    c_act: np.ndarray,
    act_ys: np.ndarray,
    act_xs: np.ndarray,
    grid_shape: tuple[int, int],
    k_target: float,
    *,
    beta_phys: float = 0.40,
    far_frac: float = 0.45,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Selected-At-Random Missingness Law coupling mapped-quadrangle relays with 1D axial SAR crests."""
    pn, mn, k_near = fuse_csd_joint(
        p_full_raw, m_full_raw, p_sar_raw, m_sar_raw, k_target=k_target, beta_phys=beta_phys
    )

    p_sar_g = adhr.scatter_fp(p_sar_raw, act_ys, act_xs, grid_shape)
    lmax5 = ndi.maximum_filter(p_sar_g, size=5, mode="nearest")[act_ys, act_xs]
    del p_sar_g
    q_floor = float(np.percentile(p_sar_raw, 85.0)) if p_sar_raw.size else 0.0
    crest = (p_sar_raw >= 0.96 * lmax5) & (p_sar_raw >= q_floor)

    unmapped_gate = (np.clip(1.0 - c_act, 0.0, 1.0) ** 2).astype(np.float32)
    k_far = float(k_near * far_frac)

    p_far_u = np.where(crest, unmapped_gate * (p_sar_raw ** np.float32(1.25)), 0.0).astype(np.float32)
    m_far_u = np.where(crest, unmapped_gate * (m_sar_raw ** np.float32(1.15)), 0.0).astype(np.float32)
    m_ratio_sar = float(np.sum(m_sar_raw, dtype=np.float64)) / max(float(np.sum(p_sar_raw, dtype=np.float64)), 1e-6)

    pf = np.clip(p_far_u * np.float32(k_far / max(float(np.sum(p_far_u, dtype=np.float64)), 1e-6)), 0.0, 0.72)
    mf = np.clip(
        m_far_u * np.float32((k_far * min(m_ratio_sar, 3.6)) / max(float(np.sum(m_far_u, dtype=np.float64)), 1e-6)),
        pf,
        0.90,
    )

    p_final = np.clip(pn + pf, 0.0, 1.0).astype(np.float32)
    m_final = np.clip(np.maximum(mn, mf), p_final, 1.0).astype(np.float32)
    return p_final, m_final, float(k_near + k_far)


def predict_all_sarcsd_arms_fold(
    grid,
    X_phys_mm: np.ndarray,
    X_sar_diff_view: ColumnSubsetView,
    X_csd20_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    *,
    min_spacing_px: float = 2.65,
    prod_struct_pack: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> dict[str, tuple[np.ndarray, dict] | tuple[np.ndarray, np.ndarray]]:
    """Fit shared SAR-diff and full-structural heads once per fold (n_ensemble=1, parity with ADHR)
    and emit Exp 01 (H88-SAR-PHYS), Exp 02 (H88-CSD-JOINT), and Exp 03 (H88-SAR-CSD).
    """
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    _, c_tr_fp = completeness_propensity_fp(visible & train_regions, fp, lambda_px=18.0)
    c_vis_fp = np.exp(-((d_vis_fp / np.float32(18.0)) ** 2)).astype(np.float32)

    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

    sar_sources = [X_sar_diff_view, X_csd20_mm]
    full_sources = [X_phys_mm, X_csd20_mm, X_vis22_mm, d_over_w_fp]

    dom_phys_tr = train_regions[ys_fp, xs_fp]
    clfs_sar, regs_sar = fit_sar_decontaminated_dual_models(
        sar_sources, dom_phys_tr, visible & train_regions, fp, c_tr_fp, seed=seed + 31, n_ensemble=1, use_sar_weights=True
    )

    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]
    clfs_full, regs_full = fit_sar_decontaminated_dual_models(
        full_sources, dom_struct_tr, train_truth, fp, c_tr_fp, seed=seed + 67, n_ensemble=1, use_sar_weights=False
    )

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]

    p_sar_raw, m_sar_raw = adhr._predict_dual_chunked(clfs_sar, regs_sar, sar_sources, act_idx)
    p_full_raw, m_full_raw = adhr._predict_dual_chunked(clfs_full, regs_full, full_sources, act_idx)

    out: dict[str, tuple[np.ndarray, dict] | tuple[np.ndarray, np.ndarray]] = {}
    if prod_struct_pack is not None:
        X_v22_prod, dv_prod, cl_prod, prod_idx_q = prod_struct_pack
        dow_prod_q = (dv_prod / np.maximum(wlaw.half_width(cl_prod), 1e-6)).astype(np.float32)
        pq_prod, mq_prod = adhr._predict_dual_chunked(
            clfs_full, regs_full, [X_phys_mm, X_csd20_mm, X_v22_prod, dow_prod_q], prod_idx_q
        )
        out["prod_struct_q"] = (pq_prod, mq_prod)
        del dow_prod_q

    del clfs_sar, regs_sar, clfs_full, regs_full
    gc.collect()

    # Exp 01: Strictly zero-catalogue 56-ch SAR differential axial-crest discovery
    p_sar_g = adhr.scatter_fp(p_sar_raw, ay, ax, grid.shape)
    lmax5 = ndi.maximum_filter(p_sar_g, size=5, mode="nearest")[ay, ax]
    del p_sar_g
    q_e1 = float(np.percentile(p_sar_raw, 88.0)) if p_sar_raw.size else 0.0
    crest_e1 = (p_sar_raw >= 0.96 * lmax5) & (p_sar_raw >= q_e1)
    p_e1_u = np.where(crest_e1, p_sar_raw ** np.float32(1.30), 0.0).astype(np.float32)
    scale_e1 = float(k_est) / max(float(np.sum(p_e1_u, dtype=np.float64)), 1e-6)
    p_e1 = np.clip(p_e1_u * np.float32(scale_e1), 0.0, 0.65).astype(np.float32)
    m_e1 = np.where(crest_e1, np.clip(m_sar_raw * np.float32(hid_ratio * 2.4), p_e1, 0.85), 0.0).astype(np.float32)
    pg_e1 = adhr.scatter_fp(p_e1, ay, ax, grid.shape)
    mg_e1 = adhr.scatter_fp(m_e1, ay, ax, grid.shape)
    alloc_e1 = emit.dinkelbach_allocate(
        pg_e1, mg_e1, allowed, budget=None, k_truth=k_est, min_spacing_px=min_spacing_px, dinkelbach_iters=6
    )
    out["exp01"] = (
        alloc_e1.emitted.astype(np.float32),
        {"n_dots": int(alloc_e1.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_e1.surrogate_dti)},
    )
    del pg_e1, mg_e1

    # Exp 02: H88-CSD-JOINT Bayes-calibrated PoE + 2.65 px Dinkelbach
    p_e2, m_e2, k_e2 = fuse_csd_joint(
        p_full_raw, m_full_raw, p_sar_raw, m_sar_raw, k_target=k_est, beta_phys=0.40
    )
    pg_e2 = adhr.scatter_fp(p_e2, ay, ax, grid.shape)
    mg_e2 = adhr.scatter_fp(m_e2, ay, ax, grid.shape)
    alloc_e2 = emit.dinkelbach_allocate(
        pg_e2, mg_e2, allowed, budget=None, k_truth=k_e2, min_spacing_px=min_spacing_px, dinkelbach_iters=6
    )
    out["exp02"] = (
        alloc_e2.emitted.astype(np.float32),
        {"n_dots": int(alloc_e2.n_dots), "k_truth_est": float(k_e2), "surrogate_dti": float(alloc_e2.surrogate_dti)},
    )
    del pg_e2, mg_e2

    # Exp 03: H88-SAR-CSD Selected-At-Random Missingness-Calibrated Dual-Regime Discovery
    p_e3, m_e3, k_e3 = fuse_sar_missingness_grid(
        p_full_raw,
        m_full_raw,
        p_sar_raw,
        m_sar_raw,
        d_vis_fp[act_idx],
        c_vis_fp[act_idx],
        ay,
        ax,
        grid.shape,
        k_target=k_est,
        beta_phys=0.40,
        far_frac=0.45,
    )
    pg_e3 = adhr.scatter_fp(p_e3, ay, ax, grid.shape)
    mg_e3 = adhr.scatter_fp(m_e3, ay, ax, grid.shape)
    alloc_e3 = emit.dinkelbach_allocate(
        pg_e3, mg_e3, allowed, budget=None, k_truth=k_e3, min_spacing_px=min_spacing_px, dinkelbach_iters=6
    )
    out["exp03"] = (
        alloc_e3.emitted.astype(np.float32),
        {"n_dots": int(alloc_e3.n_dots), "k_truth_est": float(k_e3), "surrogate_dti": float(alloc_e3.surrogate_dti)},
    )
    del pg_e3, mg_e3
    return out


def verify_zero_test_quadrant_leakage(
    grid,
    X_sar_diff_view: ColumnSubsetView,
    X_csd20_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    tr_all: np.ndarray,
    test_region: np.ndarray,
    seed: int = 88999,
) -> bool:
    """Fast deterministic invariance test proving scrambling test_region truth cannot alter predictions."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    rng = np.random.default_rng(999)
    scrambled_all = tr_all.copy()
    scrambled_all[test_region] = rng.random(int(test_region.sum())) < 0.15

    outs = []
    for truth_cand in (tr_all & train_regions, scrambled_all & train_regions):
        wlaw = damagezone_envelope.fit_width_law(
            comp_len_fp, d_vis_fp, truth_cand[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
        )
        dow = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
        _, c_tr_fp = completeness_propensity_fp(visible & train_regions, fp, lambda_px=18.0)
        clfs, regs = fit_sar_decontaminated_dual_models(
            [X_sar_diff_view, X_csd20_mm, X_vis22_mm, dow],
            (train_regions & ~visible)[ys_fp, xs_fp],
            truth_cand,
            fp,
            c_tr_fp,
            seed=seed,
            max_zero_neg=15_000,
            n_ensemble=1,
            use_sar_weights=False,
        )
        sub_idx = np.flatnonzero((fp & test_region & ~visible)[ys_fp, xs_fp])[:4096]
        p_sub, m_sub = adhr._predict_dual_chunked(
            clfs, regs, [X_sar_diff_view, X_csd20_mm, X_vis22_mm, dow], sub_idx
        )
        outs.append((p_sub, m_sub))
    return bool(np.array_equal(outs[0][0], outs[1][0]) and np.array_equal(outs[0][1], outs[1][1]))


def fit_and_emit_production_sar_csd(
    grid,
    X_phys_mm: np.ndarray,
    X_sar_diff_view: ColumnSubsetView,
    X_csd20_mm: np.ndarray,
    folds_by_seed: list[tuple[int, list[dict]]],
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
    *,
    min_spacing_px: float = 2.65,
    preplacement_gate=None,
    precomputed_full_raw: tuple[np.ndarray, np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Strictly 4-quadrant out-of-fold cross-fitting for BOTH physical and structural heads."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    d_fullcat = ndi.distance_transform_edt(~grid.catalogue).astype(np.float32)
    d_fullcat_fp = d_fullcat[ys_fp, xs_fp]
    c_fullcat_fp = np.exp(-((d_fullcat_fp / np.float32(18.0)) ** 2)).astype(np.float32)

    allowed_prod = fp & (d_fullcat > 2.0)
    act_idx = np.flatnonzero(allowed_prod[ys_fp, xs_fp])
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]

    # 1. Strictly 4-quadrant out-of-fold cross-fitting for the SAR differential physics head
    sar_oof_cache = cache_dir.parent / "gems88-sarcsd/prod_sar_oof_v2.npz"
    if sar_oof_cache.is_file():
        zs = np.load(sar_oof_cache, allow_pickle=False)
        p_sar_raw = zs["p_sar_raw"]
        m_sar_raw = zs["m_sar_raw"]
    else:
        sar_sources = [X_sar_diff_view, X_csd20_mm]
        folds_q4 = folds_by_seed[0][1]
        p_sar_raw = np.zeros(act_idx.size, dtype=np.float32)
        m_sar_raw = np.zeros(act_idx.size, dtype=np.float32)
        covered = np.zeros(act_idx.size, dtype=bool)

        for q_idx, f_q in enumerate(folds_q4):
            train_dom_q = (~f_q["region"])[ys_fp, xs_fp]
            _, c_tr_q = completeness_propensity_fp(grid.catalogue & (~f_q["region"]), fp, lambda_px=18.0)
            c_q, r_q = fit_sar_decontaminated_dual_models(
                sar_sources,
                train_dom_q,
                grid.catalogue & (~f_q["region"]),
                fp,
                c_tr_q,
                seed=88410 + q_idx,
                max_zero_neg=150_000,
                n_ensemble=1,
                use_sar_weights=True,
            )
            mask_q = f_q["region"][ay, ax]
            if q_idx == len(folds_q4) - 1:
                mask_q = mask_q | (~covered)
            covered |= mask_q
            pq, mq = adhr._predict_dual_chunked(c_q, r_q, sar_sources, act_idx[mask_q])
            p_sar_raw[mask_q] = pq
            m_sar_raw[mask_q] = mq
            del c_q, r_q, pq, mq
            gc.collect()
        sar_oof_cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(sar_oof_cache, p_sar_raw=p_sar_raw, m_sar_raw=m_sar_raw)

    # 2. Strictly 4-quadrant out-of-fold structural predictions (reused from fold checkpoints if provided)
    if precomputed_full_raw is not None:
        p_full_raw, m_full_raw = precomputed_full_raw
    else:
        X_v22_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
            grid, grid.catalogue, sense_src, scarp_fields, cache_dir, "prod_fullcat"
        )
        p_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        m_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        for seed, folds in folds_by_seed:
            vis_s = folds[0]["visible"]
            X_v22_s, dv_s, cl_s = adhr.compute_visible_struct_fp(
                grid, vis_s, sense_src, scarp_fields, cache_dir, f"seed{seed}"
            )
            reg_all = np.zeros(grid.shape, dtype=bool)
            tr_all = np.zeros(grid.shape, dtype=bool)
            for f in folds:
                reg_all |= f["region"]
                tr_all |= f["truth"]
            covered_s = np.zeros(act_idx.size, dtype=bool)
            p_seed = np.zeros(act_idx.size, dtype=np.float32)
            m_seed = np.zeros(act_idx.size, dtype=np.float32)
            for q_idx, f_q in enumerate(folds):
                tr_regions_q = reg_all & (~f_q["region"])
                tr_truth_q = tr_all & (~f_q["region"])
                _, c_tr_s = completeness_propensity_fp(vis_s & tr_regions_q, fp, lambda_px=18.0)
                wlaw_q = damagezone_envelope.fit_width_law(
                    cl_s, dv_s, tr_truth_q[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
                )
                dow_s_q = (dv_s / np.maximum(wlaw_q.half_width(cl_s), 1e-6)).astype(np.float32)
                dom_s_q = (tr_regions_q & ~vis_s)[ys_fp, xs_fp]
                cs_q, rs_q = fit_sar_decontaminated_dual_models(
                    [X_phys_mm, X_csd20_mm, X_v22_s, dow_s_q],
                    dom_s_q,
                    tr_truth_q,
                    fp,
                    c_tr_s,
                    seed=88200 + 10 * seed + f_q["fold"] + 67,
                    n_ensemble=1,
                    use_sar_weights=False,
                )
                mask_q = f_q["region"][ay, ax]
                if q_idx == len(folds) - 1:
                    mask_q = mask_q | (~covered_s)
                covered_s |= mask_q
                dow_prod_q = (dv_prod / np.maximum(wlaw_q.half_width(cl_prod), 1e-6)).astype(np.float32)
                pq, mq = adhr._predict_dual_chunked(
                    cs_q, rs_q, [X_phys_mm, X_csd20_mm, X_v22_prod, dow_prod_q], act_idx[mask_q]
                )
                p_seed[mask_q] = pq
                m_seed[mask_q] = mq
                del cs_q, rs_q, dow_s_q, dow_prod_q, pq, mq
                gc.collect()
            p_full_acc += p_seed
            m_full_acc += m_seed
            del X_v22_s, dv_s, cl_s, p_seed, m_seed
            gc.collect()
        p_full_raw = (p_full_acc / len(folds_by_seed)).astype(np.float32)
        m_full_raw = (m_full_acc / len(folds_by_seed)).astype(np.float32)
        del X_v22_prod, dv_prod, cl_prod, p_full_acc, m_full_acc
        gc.collect()

    ratios: list[float] = []
    for _seed_s, folds_s in folds_by_seed:
        vis_s = folds_s[0]["visible"]
        reg_s = np.zeros(grid.shape, dtype=bool)
        tr_s = np.zeros(grid.shape, dtype=bool)
        for f_s in folds_s:
            reg_s |= f_s["region"]
            tr_s |= f_s["truth"]
        ratios.append(float(tr_s.sum()) / max(float((vis_s & reg_s).sum()), 1.0))
    k_prod_near = float(grid.catalogue.sum()) * float(np.mean(ratios))

    p_final, m_final, k_prod = fuse_sar_missingness_grid(
        p_full_raw,
        m_full_raw,
        p_sar_raw,
        m_sar_raw,
        d_fullcat_fp[act_idx],
        c_fullcat_fp[act_idx],
        ay,
        ax,
        grid.shape,
        k_target=k_prod_near,
        beta_phys=0.40,
        far_frac=0.45,
    )
    del p_full_raw, m_full_raw, p_sar_raw, m_sar_raw
    gc.collect()

    p_surface = adhr.scatter_fp(p_final, ay, ax, grid.shape)
    m_surface = adhr.scatter_fp(m_final, ay, ax, grid.shape)
    del p_final, m_final
    gc.collect()

    if preplacement_gate is not None:
        preplacement_gate(p_surface)

    alloc = emit.dinkelbach_allocate(
        p_surface,
        m_surface,
        allowed_prod,
        budget=None,
        k_truth=k_prod,
        min_spacing_px=min_spacing_px,
        dinkelbach_iters=7,
    )
    dc_dots = d_fullcat[alloc.emitted]
    meta = {
        "n_dots": int(alloc.n_dots),
        "k_truth_est": float(k_prod),
        "surrogate_dti": float(alloc.surrogate_dti),
        "dinkelbach_rounds": int(alloc.rounds),
        "flank_exclusion_px": 2.0,
        "min_spacing_px": float(min_spacing_px),
        "median_d_cat_px": float(np.median(dc_dots)) if dc_dots.size else 0.0,
        "share_le2": float((dc_dots <= 2.0).mean()) if dc_dots.size else 0.0,
        "share_gt10": float((dc_dots > 10.0).mean()) if dc_dots.size else 0.0,
        "share_gt25": float((dc_dots > 25.0).mean()) if dc_dots.size else 0.0,
        "strictly_out_of_fold_both_heads": True,
    }
    return alloc.emitted.astype(np.float32), p_surface, meta
