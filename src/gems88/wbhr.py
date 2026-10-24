"""WBHR-88: Wallace-Bajada-Hydrothermal-Redox & Fluvial Knickpoint Discovery.

Implements the frozen pre-registered WBHR-88 method lane
(`registry/preregistration_wbhr88.json`):
  * 16 strictly label-blind physical channels unlocking 11 previously unread
    bands across the SHA-256-pinned USGS 3DEP 1m LiDAR, 10m seamless DEM,
    fluvial chi/ksn, GeoDAWN airborne gamma-ray + 150m upward-continued TMI,
    and GeoDAWN survey-drape DEM stacks;
  * Memory-bounded (<550 MB RSS) disk-backed float32 memmap caching;
  * Strictly out-of-fold cross-fitted diverse-depth HistGradientBoosting dual
    expectation ensembles (fixing IR-88-63 in-sample production memorization);
  * Three pre-registered arms evaluated via unmodified `gems57.evaluate_holdout`:
      - E1 (`wbhr_phys60`): pure 60-ch label-blind physics + 2.83 px Dinkelbach;
      - E2 (`wbhr_hybrid`): 83-ch WBHR + 2.65 px flank-declustered Dinkelbach on
        the exact same `allowed` mask as `h88_adhr_incumbent`;
      - E3 (`wbhr_balanced`): two-regime precision-calibrated 2.83 px Dinkelbach
        enforcing the 200 m mapped-fault collar (`d > 2 px`) and >=37.5% blind-
        basin discovery allocation (`d > 25 px`).
"""
from __future__ import annotations

import gc
import hashlib
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from gems57 import damagezone_envelope, emit, holdout

from . import adhr
from .edge import clean_band

WBHR_FEATURES: tuple[str, ...] = (
    "wbhr_lidar_wallace_polarity",
    "wbhr_lidar_arroyo_reject_step",
    "wbhr_lidar_strike_worm_700m",
    "wbhr_lidar_ex_peak_over_mean",
    "wbhr_bajada_subcell_spike",
    "wbhr_bajada_aspect_scarp",
    "wbhr_bajada_collinear_worm_900m",
    "wbhr_bajada_steep_ribbon",
    "wbhr_mag_shallow_depthslice",
    "wbhr_mag_shallow_grad_trough",
    "wbhr_rad_uth_redox",
    "wbhr_rad_uk_shallow_alteration",
    "wbhr_fluvial_trunk_ksn",
    "wbhr_fluvial_chi_span_area",
    "wbhr_hypso_piedmont_inflection",
    "wbhr_multiline_blind_concordance",
)


class StackedFeatureView:
    """Zero-copy column view over multiple aligned `(N_fp, C_k)` float32 arrays/memmaps."""

    def __init__(self, parts: Sequence[np.ndarray]) -> None:
        if not parts:
            raise ValueError("at least one feature block required")
        n0 = parts[0].shape[0]
        for p in parts:
            if p.ndim != 2 or p.shape[0] != n0:
                raise ValueError("all feature blocks must be 2-D with identical row count")
        self.parts = list(parts)
        self.shape = (n0, sum(int(p.shape[1]) for p in self.parts))
        self.ndim = 2
        self.dtype = np.dtype("float32")

    def __len__(self) -> int:
        return self.shape[0]

    def __getitem__(self, idx) -> np.ndarray:
        if isinstance(idx, tuple):
            row_idx, col_idx = idx
            merged = np.hstack([np.asarray(p[row_idx], dtype=np.float32) for p in self.parts])
            return merged[:, col_idx]
        return np.hstack([np.asarray(p[idx], dtype=np.float32) for p in self.parts])


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _robust_z(arr: np.ndarray, valid: np.ndarray, clip: float = 6.0) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32)
    vals = a[valid]
    q05, med, q95 = (float(x) for x in np.percentile(vals, [5.0, 50.0, 95.0]))
    scale = max((q95 - q05) / 3.2897, 1e-6)
    out = np.clip((a - np.float32(med)) / np.float32(scale), -clip, clip).astype(np.float32)
    out[~valid] = 0.0
    return out


def _positive_unit_rank(vec_fp: np.ndarray, valid_fp: np.ndarray | None = None) -> np.ndarray:
    """Map a 1-D footprint vector monotonically into `[0, 1]` using robust percentiles."""
    v = np.asarray(vec_fp, dtype=np.float32)
    m = np.isfinite(v) if valid_fp is None else (np.isfinite(v) & valid_fp)
    if not np.any(m):
        return np.zeros_like(v, dtype=np.float32)
    q50, q995 = (float(x) for x in np.percentile(v[m], [50.0, 99.5]))
    denom = max(q995 - q50, 1e-6)
    out = np.clip((v - np.float32(q50)) / np.float32(denom), 0.0, 1.0).astype(np.float32)
    if valid_fp is not None:
        out[~valid_fp] = 0.0
    return out


def _collinear_line_max(field: np.ndarray, valid: np.ndarray, halflen: int) -> np.ndarray:
    """Maximum mean response along 8 discrete azimuths of length `2*halflen + 1` pixels."""
    s = np.where(valid, np.asarray(field, dtype=np.float32), 0.0)
    h, w = s.shape
    dirs = ((1, 0), (0, 1), (1, 1), (1, -1), (2, 1), (1, 2), (2, -1), (-1, 2))
    best = np.zeros_like(s, dtype=np.float32)
    for dy, dx in dirs:
        acc = np.zeros_like(s, dtype=np.float32)
        cnt = np.zeros_like(s, dtype=np.float32)
        for k in range(-halflen, halflen + 1):
            sy, sx = k * dy, k * dx
            if abs(sy) >= h or abs(sx) >= w:
                continue
            y0_dst = max(0, sy)
            y1_dst = min(h, h + sy)
            x0_dst = max(0, sx)
            x1_dst = min(w, w + sx)
            y0_src = max(0, -sy)
            y1_src = min(h, h - sy)
            x0_src = max(0, -sx)
            x1_src = min(w, w - sx)
            acc[y0_dst:y1_dst, x0_dst:x1_dst] += s[y0_src:y1_src, x0_src:x1_src]
            cnt[y0_dst:y1_dst, x0_dst:x1_dst] += 1.0
        mean_dir = np.divide(acc, np.maximum(cnt, 1.0), dtype=np.float32)
        np.maximum(best, mean_dir, out=best)
    best[~valid] = 0.0
    return best


def _dequantize_u8_band(ds, band_idx: int, fp: np.ndarray) -> np.ndarray:
    raw = ds.read(band_idx).astype(np.float32)
    tags = ds.tags(band_idx)
    q_lo = float(tags.get("q_lo", 0.0))
    q_hi = float(tags.get("q_hi", 1.0))
    phys = np.where(raw > 0, q_lo + (raw - 1.0) / 254.0 * (q_hi - q_lo), np.nan).astype(np.float32)
    return clean_band(phys, fp)[0]


def build_or_load_wbhr_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, list[str], dict]:
    """Build or reload disk-backed `(N_fp, 16)` float32 WBHR feature memmap (<450 MB RSS)."""
    fp = np.asarray(grid.footprint, dtype=bool)
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    n_cols = len(WBHR_FEATURES)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / "x_wbhr_16ch_v1.dat"
    meta_path = cache_dir / "x_wbhr_16ch_v1.json"

    input_rels = (
        "data/training_features.tif",
        "data/geodawn_dem_a2_100m.tif",
        "data/external/lidar_scarp_features_u8.tif",
        "data/external/topo_10m_derived_100m_u8.tif",
        "data/external/dem10_chi_100m_i16.tif",
        "data/external/geodawn_rad_u8.tif",
        "data/external/geodawn_extensions_u8.tif",
    )
    input_hashes = {rel: _sha256(root / rel) for rel in input_rels}

    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(WBHR_FEATURES)
            and meta.get("input_hashes") == input_hashes
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), list(WBHR_FEATURES), meta

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    # --- Family 1: 1m USGS 3DEP LiDAR Wallace One-Sided Scarp Polarity & Arroyo Rejection (cols 0..3) ---
    with rasterio.open(root / "data/external/lidar_scarp_features_u8.tif") as ds:
        ex_max = ds.read(1)[ys, xs].astype(np.float32)
        ex_mean = ds.read(2)[ys, xs].astype(np.float32)
        step_m2d = ds.read(3).astype(np.float32)
        down_fp = ds.read(6)[ys, xs].astype(np.float32)
        up_fp = ds.read(7)[ys, xs].astype(np.float32)
        cross_fp = ds.read(8)[ys, xs].astype(np.float32)
        rel_fp = ds.read(9)[ys, xs].astype(np.float32)
        coh_m2d = ds.read(10).astype(np.float32)
        lv_m2d = (ds.read(12) > 0) & fp

    lv_fp = lv_m2d[ys, xs]
    step_fp = step_m2d[ys, xs]
    coh_fp = coh_m2d[ys, xs] / np.float32(255.0)
    one_sided = np.abs(down_fp - up_fp) / (down_fp + up_fp + np.float32(8.0))
    mm[:, 0] = np.where(lv_fp, one_sided * coh_fp * np.log1p(step_fp), -1.0).astype(np.float32)
    mm[:, 1] = np.where(lv_fp, (step_fp * coh_fp) / (1.0 + np.float32(0.025) * cross_fp), -1.0).astype(np.float32)

    scarp_seed = np.where(lv_m2d, (step_m2d / np.float32(255.0)) * (coh_m2d / np.float32(255.0)), 0.0).astype(np.float32)
    worm700 = _collinear_line_max(scarp_seed, lv_m2d, halflen=3)
    mm[:, 2] = np.where(lv_fp, worm700[ys, xs], -1.0).astype(np.float32)
    mm[:, 3] = np.where(lv_fp, np.maximum(ex_max - np.float32(0.65) * ex_mean, 0.0) / (np.float32(16.0) + rel_fp), -1.0).astype(np.float32)
    del ex_max, ex_mean, step_m2d, down_fp, up_fp, cross_fp, rel_fp, coh_m2d, lv_m2d, step_fp, coh_fp, one_sided, scarp_seed, worm700
    gc.collect()

    # --- Family 2: 10m Seamless 3DEP Sub-Cell Bajada Scarp & Collinear Aspect Worms (cols 4..7) ---
    with rasterio.open(root / "data/external/topo_10m_derived_100m_u8.tif") as ds:
        slp_p90 = _dequantize_u8_band(ds, 1, fp)[ys, xs]
        slp_max = _dequantize_u8_band(ds, 2, fp)[ys, xs]
        steep_f = np.clip(_dequantize_u8_band(ds, 3, fp)[ys, xs], 0.0, 1.0)
        slp_std = _dequantize_u8_band(ds, 4, fp)[ys, xs]
        rel_loc = _dequantize_u8_band(ds, 5, fp)[ys, xs]
        curv_p = _dequantize_u8_band(ds, 6, fp)[ys, xs]
        asp_raw = ds.read(7)[ys, xs].astype(np.float32)
        t7 = ds.tags(7)
        asp_coh = np.where(
            asp_raw > 0,
            float(t7["q_lo"]) + (asp_raw - 1.0) / 254.0 * (float(t7["q_hi"]) - float(t7["q_lo"])),
            0.5,
        ).astype(np.float32)
        dem10_m = _dequantize_u8_band(ds, 9, fp)[ys, xs]
        del asp_raw

    shore_pen = (
        np.exp(-(((dem10_m - np.float32(1330.0)) / np.float32(25.0)) ** 2))
        + np.exp(-(((dem10_m - np.float32(1555.0)) / np.float32(25.0)) ** 2))
    ).astype(np.float32)
    subcell_spike = np.maximum(slp_max - slp_p90, 0.0) * asp_coh / (1.0 + np.float32(0.12) * slp_p90)
    aspect_scarp = curv_p * (asp_coh ** 2) * np.log1p(np.maximum(slp_std, 0.0)) * (1.0 - np.float32(0.55) * np.clip(shore_pen, 0.0, 1.0))
    steep_ribbon = (steep_f * (1.0 - steep_f)) * asp_coh * np.log1p(np.maximum(rel_loc, 0.0))

    mm[:, 4] = subcell_spike.astype(np.float32)
    mm[:, 5] = aspect_scarp.astype(np.float32)
    mm[:, 7] = steep_ribbon.astype(np.float32)

    scarp10_2d = np.zeros(grid.shape, dtype=np.float32)
    scarp10_2d[ys, xs] = _positive_unit_rank(aspect_scarp)
    worm900 = _collinear_line_max(scarp10_2d, fp, halflen=4)
    iso900 = ndi.gaussian_filter(scarp10_2d, sigma=3.5, mode="nearest")
    mm[:, 6] = np.maximum(worm900[ys, xs] - np.float32(0.75) * iso900[ys, xs], 0.0).astype(np.float32)
    del slp_p90, slp_max, steep_f, slp_std, rel_loc, curv_p, asp_coh, dem10_m, shore_pen, subcell_spike, aspect_scarp, steep_ribbon, scarp10_2d, worm900, iso900
    gc.collect()

    # --- Family 3: Shallow Magnetic Depth-Slicing (TMI - TMI_up150) & Uranium-Redox Alteration (cols 8..11) ---
    with rasterio.open(root / "data/training_features.tif") as src:
        tmi_2d = clean_band(src.read(14), fp)[0]
        cond_fp = np.maximum(clean_band(src.read(17), fp)[0][ys, xs], 0.0)
        zbase_2d = np.maximum(clean_band(src.read(15), fp)[0], 0.0)

    with rasterio.open(root / "data/external/geodawn_extensions_u8.tif") as ds:
        uk_raw = ds.read(2).astype(np.float32)
        uth_raw = ds.read(3).astype(np.float32)
        tmi_up_raw = ds.read(4).astype(np.float32)
    with rasterio.open(root / "data/external/geodawn_rad_u8.tif") as ds:
        rk_raw = ds.read(1).astype(np.float32)
        rth_raw = ds.read(2).astype(np.float32)
        ru_raw = ds.read(3).astype(np.float32)

    valid_up = fp & (tmi_up_raw > 0)
    z_tmi = _robust_z(tmi_2d, fp)
    z_up = _robust_z(np.where(valid_up, tmi_up_raw, np.median(tmi_up_raw[valid_up])), fp)
    shallow_slice = np.where(valid_up, z_tmi - z_up, 0.0).astype(np.float32)
    s_smooth = ndi.gaussian_filter(shallow_slice, sigma=1.5, mode="nearest")
    sgy = ndi.sobel(s_smooth, axis=0, mode="nearest") * np.float32(0.125)
    sgx = ndi.sobel(s_smooth, axis=1, mode="nearest") * np.float32(0.125)
    shallow_grad = np.hypot(sgx, sgy)
    shallow_trough = np.maximum(-ndi.gaussian_laplace(shallow_slice, sigma=1.8, mode="nearest"), 0.0)
    grad_trough = (shallow_grad + np.float32(0.8) * shallow_trough).astype(np.float32)

    mm[:, 8] = shallow_slice[ys, xs]
    mm[:, 9] = grad_trough[ys, xs]

    valid_rad = fp & (ru_raw > 0) & (rth_raw > 0)
    z_uth = _robust_z(np.where(uth_raw > 0, uth_raw, np.median(uth_raw[uth_raw > 0])), fp)
    z_uk = _robust_z(np.where(uk_raw > 0, uk_raw, np.median(uk_raw[uk_raw > 0])), fp)
    z_u = _robust_z(np.where(valid_rad, ru_raw, np.median(ru_raw[valid_rad])), fp)
    z_th = _robust_z(np.where(valid_rad, rth_raw, np.median(rth_raw[valid_rad])), fp)
    z_k = _robust_z(np.where(valid_rad, rk_raw, np.median(rk_raw[valid_rad])), fp)

    uth_redox_fp = np.where(valid_rad[ys, xs], np.float32(0.6) * z_uth[ys, xs] + np.float32(0.4) * (z_u[ys, xs] - z_th[ys, xs]), 0.0)
    alt_redox_pos = np.maximum(z_uk[ys, xs], 0.0) + np.float32(0.5) * np.maximum(z_k[ys, xs] - z_th[ys, xs], 0.0)
    mm[:, 10] = uth_redox_fp.astype(np.float32)
    mm[:, 11] = (alt_redox_pos * np.log1p(grad_trough[ys, xs]) * (1.0 + np.float32(0.25) * np.log1p(cond_fp))).astype(np.float32)
    del tmi_2d, cond_fp, uk_raw, uth_raw, tmi_up_raw, rk_raw, rth_raw, ru_raw, valid_up, z_tmi, z_up, shallow_slice, s_smooth, sgy, sgx, shallow_grad, shallow_trough, grad_trough, valid_rad, z_uth, z_uk, z_u, z_th, z_k, uth_redox_fp, alt_redox_pos
    gc.collect()

    # --- Family 4: Trunk-Area-Weighted Fluvial Chi/Ksn & GeoDAWN Piedmont Inflection (cols 12..15) ---
    with rasterio.open(root / "data/external/dem10_chi_100m_i16.tif") as ds:
        smax_i = ds.read(1).astype(np.float32)
        smin_i = ds.read(2).astype(np.float32)
        ksn_i = ds.read(3).astype(np.float32)
        larea_i = ds.read(4).astype(np.float32)

    has_chan = fp & (larea_i > -30000.0) & (ksn_i > -30000.0)
    area_wt = np.where(has_chan, np.maximum(larea_i * np.float32(0.001) - np.float32(4.0), 0.0), 0.0).astype(np.float32)
    trunk_ksn_raw = np.where(has_chan, area_wt * np.log1p(np.maximum(ksn_i, 0.0)), 0.0).astype(np.float32)
    chi_span_raw = np.where(
        has_chan & (smax_i > -30000.0) & (smin_i > -30000.0),
        area_wt * np.log1p(np.maximum(smax_i - smin_i, 0.0) * np.float32(0.02)),
        0.0,
    ).astype(np.float32)
    chan_cnt = ndi.gaussian_filter(has_chan.astype(np.float32), sigma=2.0, mode="constant") + np.float32(0.08)
    trunk_ksn_s = ndi.gaussian_filter(trunk_ksn_raw, sigma=2.0, mode="constant") / chan_cnt
    chi_span_s = ndi.gaussian_filter(chi_span_raw, sigma=2.0, mode="constant") / chan_cnt
    mm[:, 12] = trunk_ksn_s[ys, xs].astype(np.float32)
    mm[:, 13] = chi_span_s[ys, xs].astype(np.float32)
    del smax_i, smin_i, ksn_i, larea_i, has_chan, area_wt, trunk_ksn_raw, chi_span_raw, chan_cnt, trunk_ksn_s, chi_span_s
    gc.collect()

    with rasterio.open(root / "data/geodawn_dem_a2_100m.tif") as ds:
        gdem = clean_band(ds.read(1), fp)[0]
    ggy, ggx = ndi.gaussian_filter(gdem, sigma=6.0, order=(1, 0), mode="nearest"), ndi.gaussian_filter(gdem, sigma=6.0, order=(0, 1), mode="nearest")
    reg_slope_deg = np.degrees(np.arctan(np.hypot(ggx, ggy) / np.float32(100.0)))
    pied_gate = np.exp(-(((reg_slope_deg - np.float32(5.5)) / np.float32(4.5)) ** 2)).astype(np.float32)
    pied_inflect = np.abs(ndi.gaussian_laplace(gdem, sigma=2.5, mode="nearest"))
    zgy, zgx = ndi.gaussian_filter(zbase_2d, sigma=3.0, order=(1, 0), mode="nearest"), ndi.gaussian_filter(zbase_2d, sigma=3.0, order=(0, 1), mode="nearest")
    zgrad = np.hypot(zgx, zgy)
    mm[:, 14] = (pied_gate[ys, xs] * np.log1p(pied_inflect[ys, xs]) * (1.0 + np.float32(0.35) * np.log1p(zgrad[ys, xs] * np.float32(0.1)))).astype(np.float32)
    del gdem, ggy, ggx, reg_slope_deg, pied_gate, pied_inflect, zbase_2d, zgy, zgx, zgrad
    gc.collect()

    # Col 15: Label-blind 4-family second-best physical concordance (`sqrt(top1 * top2)`)
    f1_scarp = np.maximum(
        _positive_unit_rank(mm[:, 5]) + np.float32(0.5) * _positive_unit_rank(mm[:, 6]),
        np.where(lv_fp, _positive_unit_rank(mm[:, 0], lv_fp), 0.0),
    )
    f1_scarp = np.clip(f1_scarp, 0.0, 1.0)
    f2_mag = _positive_unit_rank(mm[:, 9])
    f3_redox = np.maximum(_positive_unit_rank(mm[:, 11]), np.float32(0.75) * _positive_unit_rank(mm[:, 10]))
    f4_fluv = np.maximum(_positive_unit_rank(mm[:, 12]), _positive_unit_rank(mm[:, 14]))
    fstack = np.vstack([f1_scarp, f2_mag, f3_redox, f4_fluv])
    fstack.sort(axis=0)
    mm[:, 15] = np.sqrt(np.maximum(fstack[3] * fstack[2], 0.0)).astype(np.float32)
    del f1_scarp, f2_mag, f3_redox, f4_fluv, fstack, lv_fp
    mm.flush()

    for j in range(n_cols):
        if not np.isfinite(mm[:, j]).all():
            raise AssertionError(f"Non-finite values in WBHR column {WBHR_FEATURES[j]}")

    meta = {
        "schema": "gems88.wbhr-features.v1",
        "shape": [n_fp, n_cols],
        "features": list(WBHR_FEATURES),
        "input_hashes": input_hashes,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    del mm
    gc.collect()
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), list(WBHR_FEATURES), meta


def fit_diverse_dual_models(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    seed: int,
    max_zero_neg: int = 150_000,
) -> tuple[list[HistGradientBoostingClassifier], list[HistGradientBoostingRegressor]]:
    """Fit a variance-reduced 2-member diverse-depth HGB dual-expectation ensemble."""
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

    train_idx = np.concatenate([near_idx, sub_zero])
    weights = np.concatenate([
        np.ones(near_idx.size, dtype=np.float64),
        np.full(sub_zero.size, w_zero, dtype=np.float64),
    ])
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

    specs = (
        dict(max_iter=120, learning_rate=0.070, max_leaf_nodes=55, min_samples_leaf=85, l2_regularization=4.5),
    )
    clfs: list[HistGradientBoostingClassifier] = []
    regs: list[HistGradientBoostingRegressor] = []
    for k, sp in enumerate(specs):
        clf = HistGradientBoostingClassifier(
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=14,
            random_state=seed + 101 * k,
            **sp,
        )
        clf.fit(X_tr, yc_tr, sample_weight=weights)
        clfs.append(clf)

        reg = HistGradientBoostingRegressor(
            loss="squared_error",
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=14,
            random_state=seed + 211 * k,
            **sp,
        )
        reg.fit(X_tr, yk_tr, sample_weight=weights)
        regs.append(reg)
    del X_tr
    return clfs, regs


def predict_wbhr_fold_all_arms(
    grid,
    X_wbhr60: StackedFeatureView,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
) -> dict[str, tuple[np.ndarray, dict]]:
    """Fit WBHR models once on the 3 training quadrants and evaluate E1, E2, and E3 on `test_region`."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)

    # 1. Pure 60-ch label-blind physical head (shared by E1, E2, E3)
    dom_phys_tr = train_regions[ys_fp, xs_fp]
    clfs_phys, regs_phys = fit_diverse_dual_models(
        [X_wbhr60], dom_phys_tr, visible & train_regions, fp, seed=seed + 17
    )

    # 2. Structural + 60-ch WBHR joint head (used by E2 and E3 near-field)
    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
    full_sources = [X_wbhr60, X_vis22_mm, d_over_w_fp]

    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]
    clfs_full, regs_full = fit_diverse_dual_models(
        full_sources, dom_struct_tr, train_truth, fp, seed=seed + 53
    )

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])

    p_phys_raw, m_phys_raw = adhr._predict_dual_chunked(clfs_phys, regs_phys, [X_wbhr60], act_idx)
    p_full_raw, m_full_raw = adhr._predict_dual_chunked(clfs_full, regs_full, full_sources, act_idx)
    del clfs_phys, regs_phys, clfs_full, regs_full
    gc.collect()

    # --- Arm E1 (`wbhr_phys60`): Pure 60-channel label-blind physics ---
    scale_p1 = float(k_est) / max(float(p_phys_raw.sum(dtype=np.float64)), 1e-6)
    p_e1 = np.clip(p_phys_raw * np.float32(scale_p1), 0.0, 1.0).astype(np.float32)
    m_e1_raw = np.clip(m_phys_raw * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)
    m_e1 = np.clip(np.float32(0.45) * m_e1_raw + np.float32(0.55) * p_e1, p_e1, 1.0).astype(np.float32)
    p_e1_grid = adhr.scatter_fp(p_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e1_grid = adhr.scatter_fp(m_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_e1 = emit.dinkelbach_allocate(
        p_e1_grid,
        m_e1_grid,
        allowed,
        budget=None,
        k_truth=k_est,
        min_spacing_px=2.83,
        dinkelbach_iters=6,
    )

    # --- Arm E2 (`wbhr_hybrid`): Full 83-ch WBHR + 2.65 px flank-declustered Dinkelbach on identical `allowed` ---
    p_f2, m_f2_raw = adhr._fuse_log_odds(p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, k_est, beta_phys=0.38, pi_unmapped=0.45)
    m_f2 = np.clip(np.float32(0.65) * m_f2_raw + np.float32(0.35) * p_f2, p_f2, 1.0).astype(np.float32)
    p_e2_grid = adhr.scatter_fp(p_f2, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e2_grid = adhr.scatter_fp(m_f2, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_e2 = emit.dinkelbach_allocate(
        p_e2_grid,
        m_e2_grid,
        allowed,
        budget=None,
        k_truth=k_est,
        min_spacing_px=2.65,
        dinkelbach_iters=6,
    )

    # --- Arm E3 (`wbhr_balanced`): Two-Regime Precision-Calibrated Allocation (`d > 2`, `share_gt25 >= 0.375`) ---
    d_vis_grid = np.zeros(grid.shape, dtype=np.float32)
    d_vis_grid[ys_fp, xs_fp] = d_vis_fp
    allow_near = allowed & (d_vis_grid > 2.0) & (d_vis_grid <= 25.0)
    allow_far = allowed & (d_vis_grid > 25.0)

    b_tot = max(16, int(round(0.88 * int(alloc_e2.n_dots))))
    b_near = max(8, int(math.floor(0.625 * b_tot)))
    b_far = max(6, b_tot - b_near)
    alloc_near = emit.dinkelbach_allocate(
        p_e2_grid,
        m_e2_grid,
        allow_near,
        budget=b_near,
        k_truth=0.864 * k_est,
        min_spacing_px=2.83,
        dinkelbach_iters=5,
    )
    n_near = int(alloc_near.n_dots)
    n_far_target = max(b_far, int(math.ceil((0.375 / 0.625) * n_near)))
    alloc_far = emit.dinkelbach_allocate(
        p_e1_grid,
        m_e1_grid,
        allow_far,
        budget=n_far_target,
        k_truth=max(0.136 * k_est, 10.0),
        min_spacing_px=2.83,
        dinkelbach_iters=4,
    )
    emit_e3 = (alloc_near.emitted | alloc_far.emitted).astype(np.float32)
    n_e3 = int((emit_e3 > 0).sum())
    share_gt25_e3 = float((d_vis_grid[emit_e3 > 0] > 25.0).mean()) if n_e3 > 0 else 0.0

    return {
        "wbhr_phys60": (
            alloc_e1.emitted.astype(np.float32),
            {"n_dots": int(alloc_e1.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_e1.surrogate_dti)},
        ),
        "wbhr_hybrid": (
            alloc_e2.emitted.astype(np.float32),
            {"n_dots": int(alloc_e2.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_e2.surrogate_dti)},
        ),
        "wbhr_balanced": (
            emit_e3,
            {
                "n_dots": n_e3,
                "n_near": n_near,
                "n_far": int(alloc_far.n_dots),
                "share_gt25": share_gt25_e3,
                "k_truth_est": float(k_est),
            },
        ),
    }


def fit_and_emit_production_wbhr(
    grid,
    X_wbhr60: StackedFeatureView,
    folds_by_seed: list[tuple[int, list[dict]]],
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
    *,
    mode: str = "balanced",
    preplacement_gate=None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Strictly 4-quadrant out-of-fold cross-fitted production surface + Dinkelbach emission.

    Eliminates `IR-88-63` by cross-fitting BOTH the 60-ch physical head AND the
    83-ch structural head strictly Leave-One-Quadrant-Out (`3` quadrants train,
    `1` quadrant predict), so smooth geophysical/thermal fields never see
    in-sample quadrant fault coordinates during production prediction.
    """
    if mode not in ("balanced", "hybrid", "phys60"):
        raise ValueError(f"unsupported WBHR production mode: {mode}")

    prod_ckpt = Path(cache_dir) / f"wbhr88_prod_v2_{mode}.npz"
    if prod_ckpt.is_file():
        z = np.load(prod_ckpt, allow_pickle=False)
        p_surface = z["p_surface"].astype(np.float32)
        if preplacement_gate is not None:
            preplacement_gate(p_surface)
        return z["emitted"].astype(np.float32), p_surface, json.loads(str(z["meta_json"]))

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    d_fullcat = ndi.distance_transform_edt(~grid.catalogue).astype(np.float32)
    allowed_prod = fp & (d_fullcat > 2.0)
    act_idx = np.flatnonzero(allowed_prod[ys_fp, xs_fp])

    oof_raw_ckpt = Path(cache_dir) / "wbhr88_prod_oof_raw_v2.npz"
    if oof_raw_ckpt.is_file():
        zr = np.load(oof_raw_ckpt, allow_pickle=False)
        p_phys_raw = zr["p_phys_raw"].astype(np.float32)
        m_phys_raw = zr["m_phys_raw"].astype(np.float32)
        p_full_raw = zr["p_full_raw"].astype(np.float32)
        m_full_raw = zr["m_full_raw"].astype(np.float32)
        hid_ratio_mean = float(zr["hid_ratio_mean"])
    else:
        # 1. Strictly 4-quadrant OOF cross-fit for the 60-channel physical head
        quad = holdout.quadrant_ids(fp)
        quad_act = quad[ys_fp[act_idx], xs_fp[act_idx]]
        folds_q4 = folds_by_seed[0][1]
        p_phys_raw = np.zeros(act_idx.size, dtype=np.float32)
        m_phys_raw = np.zeros(act_idx.size, dtype=np.float32)
        for q_idx, f_q in enumerate(folds_q4):
            tr_reg_q = np.zeros(grid.shape, dtype=bool)
            for other in folds_q4:
                if int(other["fold"]) != int(f_q["fold"]):
                    tr_reg_q |= other["region"]
            train_dom_q = tr_reg_q[ys_fp, xs_fp]
            c_q, r_q = fit_diverse_dual_models(
                [X_wbhr60], train_dom_q, grid.catalogue & tr_reg_q, fp, seed=881310 + q_idx
            )
            mask_q = quad_act == int(f_q["fold"])
            pq, mq = adhr._predict_dual_chunked(c_q, r_q, [X_wbhr60], act_idx[mask_q])
            p_phys_raw[mask_q] = pq
            m_phys_raw[mask_q] = mq
            del c_q, r_q, pq, mq
            gc.collect()

        # 2. Strictly 4-quadrant OOF cross-fit for the 83-channel structural head across seeds (eliminates IR-88-63!)
        X_v22_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
            grid, grid.catalogue, sense_src, scarp_fields, cache_dir, "prod_fullcat"
        )
        p_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        m_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        ratios: list[float] = []

        for s_idx, (seed, folds) in enumerate(folds_by_seed):
            vis_s = folds[0]["visible"]
            X_v22_s, dv_s, cl_s = adhr.compute_visible_struct_fp(
                grid, vis_s, sense_src, scarp_fields, cache_dir, f"seed{seed}"
            )
            all_reg_s = np.zeros(grid.shape, dtype=bool)
            all_tr_s = np.zeros(grid.shape, dtype=bool)
            for f in folds:
                all_reg_s |= f["region"]
                all_tr_s |= f["truth"]
            ratios.append(float(all_tr_s.sum()) / max(float((vis_s & all_reg_s).sum()), 1.0))

            p_seed_oof = np.zeros(act_idx.size, dtype=np.float32)
            m_seed_oof = np.zeros(act_idx.size, dtype=np.float32)
            for q_idx, f_q in enumerate(folds):
                tr_reg = np.zeros(grid.shape, dtype=bool)
                tr_tru = np.zeros(grid.shape, dtype=bool)
                for other in folds:
                    if int(other["fold"]) != int(f_q["fold"]):
                        tr_reg |= other["region"]
                        tr_tru |= other["truth"]
                wlaw_q = damagezone_envelope.fit_width_law(cl_s, dv_s, tr_tru[ys_fp, xs_fp], quantile=0.90, l0_px=40.0)
                dow_s = (dv_s / np.maximum(wlaw_q.half_width(cl_s), 1e-6)).astype(np.float32)
                dom_q = (tr_reg & ~vis_s)[ys_fp, xs_fp]
                cq, rq = fit_diverse_dual_models(
                    [X_wbhr60, X_v22_s, dow_s], dom_q, tr_tru, fp, seed=882400 + 100 * s_idx + q_idx
                )
                dow_prod_q = (dv_prod / np.maximum(wlaw_q.half_width(cl_prod), 1e-6)).astype(np.float32)
                mask_q = quad_act == int(f_q["fold"])
                pq, mq = adhr._predict_dual_chunked(cq, rq, [X_wbhr60, X_v22_prod, dow_prod_q], act_idx[mask_q])
                p_seed_oof[mask_q] = pq
                m_seed_oof[mask_q] = mq
                del cq, rq, dow_s, dow_prod_q, pq, mq
                gc.collect()

            p_full_acc += p_seed_oof
            m_full_acc += m_seed_oof
            del X_v22_s, dv_s, cl_s, p_seed_oof, m_seed_oof
            gc.collect()

        p_full_raw = (p_full_acc / len(folds_by_seed)).astype(np.float32)
        m_full_raw = (m_full_acc / len(folds_by_seed)).astype(np.float32)
        del p_full_acc, m_full_acc, X_v22_prod, dv_prod, cl_prod
        gc.collect()

        hid_ratio_mean = float(np.mean(ratios))
        np.savez_compressed(
            oof_raw_ckpt,
            p_phys_raw=p_phys_raw,
            m_phys_raw=m_phys_raw,
            p_full_raw=p_full_raw,
            m_full_raw=m_full_raw,
            hid_ratio_mean=np.array(hid_ratio_mean, dtype=np.float64),
        )
    k_prod = float(grid.catalogue.sum()) * hid_ratio_mean

    scale_p1 = float(k_prod) / max(float(p_phys_raw.sum(dtype=np.float64)), 1e-6)
    p_e1 = np.clip(p_phys_raw * np.float32(scale_p1), 0.0, 1.0).astype(np.float32)
    m_e1_raw = np.clip(m_phys_raw * np.float32(hid_ratio_mean), p_e1, 1.0).astype(np.float32)
    m_e1 = np.clip(np.float32(0.45) * m_e1_raw + np.float32(0.55) * p_e1, p_e1, 1.0).astype(np.float32)
    p_e1_grid = adhr.scatter_fp(p_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e1_grid = adhr.scatter_fp(m_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)

    p_f2, m_f2_raw = adhr._fuse_log_odds(p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, k_prod, beta_phys=0.38, pi_unmapped=0.45)
    m_f2 = np.clip(np.float32(0.65) * m_f2_raw + np.float32(0.35) * p_f2, p_f2, 1.0).astype(np.float32)
    p_e2_grid = adhr.scatter_fp(p_f2, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e2_grid = adhr.scatter_fp(m_f2, ys_fp[act_idx], xs_fp[act_idx], grid.shape)

    if mode == "phys60":
        p_surface = p_e1_grid
        if preplacement_gate is not None:
            preplacement_gate(p_surface)
        alloc = emit.dinkelbach_allocate(
            p_e1_grid, m_e1_grid, allowed_prod, budget=None, k_truth=k_prod, min_spacing_px=2.83, dinkelbach_iters=8
        )
        emitted = alloc.emitted.astype(np.float32)
    elif mode == "hybrid":
        p_surface = p_e2_grid
        if preplacement_gate is not None:
            preplacement_gate(p_surface)
        alloc = emit.dinkelbach_allocate(
            p_e2_grid, m_e2_grid, allowed_prod, budget=None, k_truth=k_prod, min_spacing_px=2.65, dinkelbach_iters=8
        )
        emitted = alloc.emitted.astype(np.float32)
    else:
        allow_near = allowed_prod & (d_fullcat <= 25.0)
        allow_far = allowed_prod & (d_fullcat > 25.0)
        p_surface = np.where(allow_far, np.maximum(p_e2_grid, p_e1_grid), p_e2_grid).astype(np.float32)
        if preplacement_gate is not None:
            preplacement_gate(p_surface)
        alloc_ref = emit.dinkelbach_allocate(
            p_e2_grid, m_e2_grid, allowed_prod, budget=None, k_truth=k_prod, min_spacing_px=2.65, dinkelbach_iters=6
        )
        b_tot = max(16, int(round(0.88 * int(alloc_ref.n_dots))))
        b_near = max(8, int(math.floor(0.625 * b_tot)))
        b_far = max(6, b_tot - b_near)
        alloc_near = emit.dinkelbach_allocate(
            p_e2_grid,
            m_e2_grid,
            allow_near,
            budget=b_near,
            k_truth=0.864 * k_prod,
            min_spacing_px=2.83,
            dinkelbach_iters=6,
        )
        n_near = int(alloc_near.n_dots)
        n_far_target = max(b_far, int(math.ceil((0.375 / 0.625) * n_near)))
        alloc_far = emit.dinkelbach_allocate(
            p_e1_grid,
            m_e1_grid,
            allow_far,
            budget=n_far_target,
            k_truth=max(0.136 * k_prod, 10.0),
            min_spacing_px=2.83,
            dinkelbach_iters=5,
        )
        emitted = (alloc_near.emitted | alloc_far.emitted).astype(np.float32)

    dots = emitted > 0
    meta = {
        "mode": mode,
        "n_dots": int(dots.sum()),
        "k_truth_est": float(k_prod),
        "flank_exclusion_px": 2.0,
        "min_d_cat_px": float(d_fullcat[dots].min()) if dots.any() else 0.0,
        "median_d_cat_px": float(np.median(d_fullcat[dots])) if dots.any() else 0.0,
        "share_le2": float((d_fullcat[dots] <= 2.0).mean()) if dots.any() else 0.0,
        "share_gt10": float((d_fullcat[dots] > 10.0).mean()) if dots.any() else 0.0,
        "share_gt25": float((d_fullcat[dots] > 25.0).mean()) if dots.any() else 0.0,
    }
    np.savez_compressed(
        prod_ckpt,
        emitted=emitted.astype(np.uint8),
        p_surface=p_surface.astype(np.float32),
        meta_json=np.array(json.dumps(meta)),
    )
    return emitted, p_surface, meta
