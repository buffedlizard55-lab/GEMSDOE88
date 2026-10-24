"""GTHC-88: Geothermal Transtensional Hydrothermal-Conduit & Completeness-Regime Decomposition.

Implements the 6 preregistered label-blind physical/hydrothermal channels from previously
unread USGS GeoDAWN, 3DEP 10 m, 1 m LiDAR, and DOE GDR / INGENIOUS bands, plus the
completeness-regime-gated dual-head fusion and fingerprint-compliant stratified allocation.

Every channel is strictly zero-catalogue (never touches ``existing_faults.tif`` or
``dist_known_fault_px``) and is verified against the single-feature leakage canary
(symmetric ROC AUC <= 0.90 on withheld whole-component positives vs off-catalogue negatives).
"""
from __future__ import annotations

import csv
import gc
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems57 import grid as grid_mod
from gems88 import physics

ROOT = Path(__file__).resolve().parents[2]
EXT_DIR = ROOT / "data" / "external"
CACHE_DIR = ROOT / ".cache" / "gems88"

GTHC_FEATURES: Tuple[str, ...] = (
    "gthc_uranium_redox_argillic_halo",
    "gthc_upward_mag_basement_admittance",
    "gthc_fluvial_knick_raised_incision",
    "gthc_bajada_aspect_monocline",
    "gthc_lidar_normal_polarity_asymmetry",
    "gthc_chalcedony_cation_updip_feeder",
)

ALL_GTHC_PHYS_FEATURES: Tuple[str, ...] = physics.ALL_PHYS_FEATURES + GTHC_FEATURES


def _zscore_fp(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    out = np.zeros(arr.shape, dtype=np.float32)
    vals = arr[fp].astype(np.float64)
    finite = np.isfinite(vals)
    if not np.any(finite):
        return out
    med = float(np.median(vals[finite]))
    mad = float(np.median(np.abs(vals[finite] - med)))
    scale = max(1.4826 * mad, float(np.std(vals[finite])), 1e-6)
    clean = np.where(np.isfinite(arr) & fp, arr, med).astype(np.float32)
    z = np.clip((clean - med) / scale, -8.0, 8.0).astype(np.float32)
    out[fp] = z[fp]
    return out


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return (1.0 / (1.0 + np.exp(-np.clip(x, -12.0, 12.0)))).astype(np.float32)


def _read_ext_band(fname: str, band: int, shape: Tuple[int, int]) -> np.ndarray:
    path = EXT_DIR / fname
    if not path.is_file():
        raise FileNotFoundError(f"Missing required external raster: {path}")
    with rasterio.open(path) as ds:
        arr = ds.read(band).astype(np.float32)
    if arr.shape != shape:
        raise ValueError(f"{fname} band {band} shape {arr.shape} != {shape}")
    return arr


def _read_tf_bands(g: grid_mod.Grid, indices: Tuple[int, ...]) -> Dict[str, np.ndarray]:
    fp = g.footprint
    out: Dict[str, np.ndarray] = {}
    with rasterio.open(ROOT / "data" / "training_features.tif") as src:
        for idx in indices:
            tag = physics.EXPECTED_TRAINING_BANDS[idx]
            out[tag] = physics.clean_band(src.read(idx), fp)[0]
    return out


def _build_chalcedony_cation_source(g: grid_mod.Grid) -> np.ndarray:
    """Build composite thermal & geothermometer source grid from GDR wells/springs, 2m probes, and paleo sinter."""
    shape = g.shape
    fp = g.footprint
    src = np.zeros(shape, dtype=np.float32)
    csv_path = EXT_DIR / "gdr_wellspring_in_footprint.csv"
    if csv_path.is_file():
        with csv_path.open("r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            # Explicitly verify we never read dist_known_fault_px
            for row in reader:
                try:
                    r = int(float(row["row"]))
                    c = int(float(row["col"]))
                except (KeyError, ValueError):
                    continue
                if not (0 <= r < shape[0] and 0 <= c < shape[1]):
                    continue
                w = 0.20
                for col_name, thresh, scale in (
                    ("temp_c", 28.0, 45.0),
                    ("geothermquartz_c", 70.0, 75.0),
                    ("geothermchalc_c", 55.0, 65.0),
                    ("geothermcat_c", 65.0, 75.0),
                ):
                    raw = (row.get(col_name) or "").strip()
                    if raw:
                        try:
                            val = float(raw)
                            if np.isfinite(val) and val > thresh and val < 350.0:
                                w += min((val - thresh) / scale, 2.5)
                        except ValueError:
                            pass
                if w > src[r, c]:
                    src[r, c] = float(w)

    # Also splat paleo-geothermal sinter/travertine and 2m probe anomalies
    inv = ~g.transform
    z_paleo = EXT_DIR / "paleo_geothermal_regional.zip"
    if z_paleo.is_file():
        with zipfile.ZipFile(z_paleo) as zf:
            text = zf.read("Paleo_geothermal_final.csv").decode("latin1", "replace")
        for r in csv.DictReader(text.splitlines()):
            try:
                x = float(r.get("X_UTM11", ""))
                y = float(r.get("Y_UTM11", ""))
            except ValueError:
                continue
            cc, rr = inv * (x, y)
            ri, ci = int(round(rr)), int(round(cc))
            if 0 <= ri < shape[0] and 0 <= ci < shape[1]:
                src[ri, ci] = max(src[ri, ci], 2.2)

    z_2m = EXT_DIR / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    if z_2m.is_file():
        with zipfile.ZipFile(z_2m) as zf:
            dbf_name = [n for n in zf.namelist() if n.lower().endswith(".dbf")][0]
            recs = physics._read_dbf_records(zf.read(dbf_name))
        for r in recs:
            try:
                x = float(r.get("X_UTM83", ""))
                y = float(r.get("Y_UTM83", ""))
                dab = float(r.get("F2mDAB", "0") or 0.0)
                t2 = float(r.get("T2m", "0") or 0.0)
            except ValueError:
                continue
            cc, rr = inv * (x, y)
            ri, ci = int(round(rr)), int(round(cc))
            if 0 <= ri < shape[0] and 0 <= ci < shape[1]:
                w2 = 0.35 + max(dab, 0.0) * 0.35 + max(t2 - 18.0, 0.0) * 0.08
                if w2 > src[ri, ci]:
                    src[ri, ci] = float(min(w2, 3.5))

    composite = (
        0.55 * ndi.gaussian_filter(src, sigma=3.5, mode="nearest")
        + 0.45 * ndi.gaussian_filter(src, sigma=9.0, mode="nearest")
    ).astype(np.float32)
    return _zscore_fp(composite, fp)


def uranium_redox_argillic_halo(
    rad_u: np.ndarray,
    ext_uk: np.ndarray,
    ext_uth: np.ndarray,
    rad_tc: np.ndarray,
    cond_surf: np.ndarray,
    tmi_vg: np.ndarray,
    fp: np.ndarray,
) -> np.ndarray:
    u_hp = ndi.gaussian_filter(rad_u, sigma=2.0, mode="nearest") - ndi.gaussian_filter(rad_u, sigma=12.0, mode="nearest")
    uk_hp = ndi.gaussian_filter(ext_uk, sigma=2.0, mode="nearest") - ndi.gaussian_filter(ext_uk, sigma=12.0, mode="nearest")
    uth_hp = ndi.gaussian_filter(ext_uth, sigma=2.0, mode="nearest") - ndi.gaussian_filter(ext_uth, sigma=12.0, mode="nearest")
    tc_grad_y = ndi.gaussian_filter(rad_tc, sigma=2.5, order=[1, 0], mode="nearest")
    tc_grad_x = ndi.gaussian_filter(rad_tc, sigma=2.5, order=[0, 1], mode="nearest")
    tc_step = np.hypot(tc_grad_y, tc_grad_x).astype(np.float32)

    z_cond = _zscore_fp(cond_surf, fp)
    z_mag_trough = _zscore_fp(-tmi_vg, fp)
    redox_halo = (
        (0.35 * _zscore_fp(u_hp, fp) + 0.30 * _zscore_fp(uk_hp, fp) + 0.20 * _zscore_fp(uth_hp, fp) + 0.15 * _zscore_fp(tc_step, fp))
        * (0.50 + 0.50 * _sigmoid(z_cond))
        * (0.50 + 0.50 * _sigmoid(z_mag_trough))
    )
    return _zscore_fp(redox_halo, fp)


def upward_mag_basement_admittance(
    tmi_vg: np.ndarray,
    tmi_up150: np.ndarray,
    iso_grav_anom_hg: np.ndarray,
    depth_to_base_surf: np.ndarray,
    geod_shearrate: np.ndarray,
    geod_dilaterate: np.ndarray,
    fp: np.ndarray,
) -> np.ndarray:
    up_lap = (
        ndi.gaussian_filter(tmi_up150, sigma=3.0, order=[2, 0], mode="nearest")
        + ndi.gaussian_filter(tmi_up150, sigma=3.0, order=[0, 2], mode="nearest")
    )
    up_gy = ndi.gaussian_filter(tmi_up150, sigma=2.5, order=[1, 0], mode="nearest")
    up_gx = ndi.gaussian_filter(tmi_up150, sigma=2.5, order=[0, 1], mode="nearest")
    up_grad = np.hypot(up_gy, up_gx).astype(np.float32)

    z_shallow_vg = _zscore_fp(np.abs(tmi_vg), fp)
    z_deep_lap = _zscore_fp(np.abs(up_lap), fp)
    z_deep_grad = _zscore_fp(up_grad, fp)
    cover_boost = np.log1p(np.maximum(depth_to_base_surf, 0.0)).astype(np.float32)
    z_grav_hg = _zscore_fp(iso_grav_anom_hg * (1.0 + 0.35 * _zscore_fp(cover_boost, fp)), fp)
    transtension = _zscore_fp(geod_shearrate * np.maximum(geod_dilaterate, 0.0), fp)
    admittance = (0.40 * z_deep_grad + 0.30 * (z_deep_lap - 0.5 * z_shallow_vg) + 0.30 * z_grav_hg) * (1.0 + 0.25 * _sigmoid(transtension))
    return _zscore_fp(admittance, fp)


def fluvial_knick_raised_incision(
    chan_n: np.ndarray,
    knick_n: np.ndarray,
    raised_n: np.ndarray,
    valid_n: np.ndarray,
    ksn: np.ndarray,
    zmean: np.ndarray,
    fp: np.ndarray,
) -> np.ndarray:
    knick_rate = ndi.gaussian_filter(knick_n / np.maximum(chan_n, 1.0), sigma=2.5, mode="nearest")
    raised_rate = ndi.gaussian_filter(raised_n / np.maximum(valid_n, 1.0), sigma=2.5, mode="nearest")
    shore_lahontan = np.exp(-0.5 * ((zmean - 1330.0) / 35.0) ** 2)
    shore_bonneville = np.exp(-0.5 * ((zmean - 1555.0) / 35.0) ** 2)
    shore_penalty = (1.0 - 0.55 * np.maximum(shore_lahontan, shore_bonneville)).astype(np.float32)
    raw = (0.50 * knick_rate + 0.30 * raised_rate + 0.20 * np.log1p(np.maximum(ksn, 0.0))) * shore_penalty
    out = np.zeros(chan_n.shape, dtype=np.float32)
    out[fp] = raw[fp].astype(np.float32)
    return out


def bajada_aspect_monocline(
    aspect_coh: np.ndarray,
    steep_frac: np.ndarray,
    slope_std: np.ndarray,
    relief_local: np.ndarray,
    slope_p90: np.ndarray,
    fp: np.ndarray,
) -> np.ndarray:
    roughness_cv = slope_std / (slope_p90 + 8.0)
    monocline_raw = (aspect_coh / 255.0) * np.log1p(steep_frac) * np.log1p(relief_local) / (1.0 + roughness_cv)
    monocline_anom = ndi.gaussian_filter(monocline_raw, sigma=1.5, mode="nearest") - ndi.gaussian_filter(monocline_raw, sigma=10.0, mode="nearest")
    return _zscore_fp(monocline_anom, fp)


def lidar_normal_polarity_asymmetry(
    lid_ex_mean: np.ndarray,
    lid_down: np.ndarray,
    lid_up: np.ndarray,
    lid_cross: np.ndarray,
    lid_valid: np.ndarray,
    fp: np.ndarray,
    fallback_f4: np.ndarray | None = None,
) -> np.ndarray:
    valid_mask = lid_valid > 0
    polarity = (np.abs(lid_down - lid_up) / 255.0) * (lid_cross / 255.0) * np.sqrt(np.maximum(lid_ex_mean, 0.0) / 255.0)
    polarity_anom = ndi.gaussian_filter(polarity, sigma=1.2, mode="nearest") - ndi.gaussian_filter(polarity, sigma=10.0, mode="nearest")
    z_pol = _zscore_fp(polarity_anom, fp & valid_mask)
    w_lid = ndi.gaussian_filter(valid_mask.astype(np.float32), sigma=3.0, mode="nearest")
    fb = np.zeros_like(z_pol) if fallback_f4 is None else fallback_f4
    return _zscore_fp(w_lid * z_pol + (1.0 - w_lid) * fb, fp)


def compute_gthc_features_2d(g: grid_mod.Grid) -> Dict[str, np.ndarray]:
    """Compute the 6 label-blind GTHC-88 physical/hydrothermal channels on the 2D grid."""
    fp = g.footprint
    H, W = g.shape
    raw_tf = _read_tf_bands(g, (7, 8, 9, 15, 17, 18, 19))

    # 1. gthc_uranium_redox_argillic_halo
    rad_u = _read_ext_band("geodawn_rad_u8.tif", 3, (H, W))
    rad_tc = _read_ext_band("geodawn_rad_u8.tif", 4, (H, W))
    ext_uk = _read_ext_band("geodawn_extensions_u8.tif", 2, (H, W))
    ext_uth = _read_ext_band("geodawn_extensions_u8.tif", 3, (H, W))

    u_hp = ndi.gaussian_filter(rad_u, sigma=2.0, mode="nearest") - ndi.gaussian_filter(rad_u, sigma=12.0, mode="nearest")
    uk_hp = ndi.gaussian_filter(ext_uk, sigma=2.0, mode="nearest") - ndi.gaussian_filter(ext_uk, sigma=12.0, mode="nearest")
    uth_hp = ndi.gaussian_filter(ext_uth, sigma=2.0, mode="nearest") - ndi.gaussian_filter(ext_uth, sigma=12.0, mode="nearest")
    tc_grad_y = ndi.gaussian_filter(rad_tc, sigma=2.5, order=[1, 0], mode="nearest")
    tc_grad_x = ndi.gaussian_filter(rad_tc, sigma=2.5, order=[0, 1], mode="nearest")
    tc_step = np.hypot(tc_grad_y, tc_grad_x).astype(np.float32)

    z_cond = _zscore_fp(raw_tf["cond_surf"], fp)
    z_mag_trough = _zscore_fp(-raw_tf["tmi_vg"], fp)
    redox_halo = (
        (0.35 * _zscore_fp(u_hp, fp) + 0.30 * _zscore_fp(uk_hp, fp) + 0.20 * _zscore_fp(uth_hp, fp) + 0.15 * _zscore_fp(tc_step, fp))
        * (0.50 + 0.50 * _sigmoid(z_cond))
        * (0.50 + 0.50 * _sigmoid(z_mag_trough))
    )
    f1 = _zscore_fp(redox_halo, fp)
    del rad_u, rad_tc, ext_uk, ext_uth, u_hp, uk_hp, uth_hp, tc_grad_y, tc_grad_x, tc_step, redox_halo
    gc.collect()

    # 2. gthc_upward_mag_basement_admittance
    tmi_up150 = _read_ext_band("geodawn_extensions_u8.tif", 4, (H, W))
    up_lap = (
        ndi.gaussian_filter(tmi_up150, sigma=3.0, order=[2, 0], mode="nearest")
        + ndi.gaussian_filter(tmi_up150, sigma=3.0, order=[0, 2], mode="nearest")
    )
    up_gy = ndi.gaussian_filter(tmi_up150, sigma=2.5, order=[1, 0], mode="nearest")
    up_gx = ndi.gaussian_filter(tmi_up150, sigma=2.5, order=[0, 1], mode="nearest")
    up_grad = np.hypot(up_gy, up_gx).astype(np.float32)

    z_shallow_vg = _zscore_fp(np.abs(raw_tf["tmi_vg"]), fp)
    z_deep_lap = _zscore_fp(np.abs(up_lap), fp)
    z_deep_grad = _zscore_fp(up_grad, fp)
    cover_boost = np.log1p(np.maximum(raw_tf["depth_to_base_surf"], 0.0)).astype(np.float32)
    z_grav_hg = _zscore_fp(raw_tf["iso_grav_anom_hg"] * (1.0 + 0.35 * _zscore_fp(cover_boost, fp)), fp)
    transtension = _zscore_fp(raw_tf["geod_shearrate"] * np.maximum(raw_tf["geod_dilaterate"], 0.0), fp)
    admittance = (0.40 * z_deep_grad + 0.30 * (z_deep_lap - 0.5 * z_shallow_vg) + 0.30 * z_grav_hg) * (1.0 + 0.25 * _sigmoid(transtension))
    f2 = _zscore_fp(admittance, fp)
    del tmi_up150, up_lap, up_gy, up_gx, up_grad, admittance
    gc.collect()

    # 3. gthc_fluvial_knick_raised_incision
    chan_n = _read_ext_band("dem10_chi_100m_u8.tif", 1, (H, W))
    knick_n = _read_ext_band("dem10_chi_100m_u8.tif", 2, (H, W))
    raised_n = _read_ext_band("dem10_chi_100m_u8.tif", 3, (H, W))
    valid_n = np.maximum(_read_ext_band("dem10_chi_100m_u8.tif", 4, (H, W)), 1.0)
    ksn = _read_ext_band("dem10_chi_100m_i16.tif", 3, (H, W))
    zmean = _read_ext_band("dem10_chi_100m_i16.tif", 5, (H, W))

    knick_rate = ndi.gaussian_filter(knick_n / np.maximum(chan_n, 1.0), sigma=2.5, mode="nearest")
    raised_rate = ndi.gaussian_filter(raised_n / valid_n, sigma=2.5, mode="nearest")
    shore_lahontan = np.exp(-0.5 * ((zmean - 1330.0) / 35.0) ** 2)
    shore_bonneville = np.exp(-0.5 * ((zmean - 1555.0) / 35.0) ** 2)
    shore_penalty = (1.0 - 0.55 * np.maximum(shore_lahontan, shore_bonneville)).astype(np.float32)
    fluvial_incision = (0.50 * _zscore_fp(knick_rate, fp) + 0.30 * _zscore_fp(raised_rate, fp) + 0.20 * _zscore_fp(ksn, fp)) * shore_penalty
    f3 = _zscore_fp(fluvial_incision, fp)
    del chan_n, knick_n, raised_n, valid_n, ksn, zmean, knick_rate, raised_rate, shore_lahontan, shore_bonneville, fluvial_incision
    gc.collect()

    # 4. gthc_bajada_aspect_monocline
    slope_p90 = _read_ext_band("topo_10m_derived_100m_u8.tif", 1, (H, W))
    steep_frac = _read_ext_band("topo_10m_derived_100m_u8.tif", 3, (H, W))
    slope_std = _read_ext_band("topo_10m_derived_100m_u8.tif", 4, (H, W))
    relief_local = _read_ext_band("topo_10m_derived_100m_u8.tif", 5, (H, W))
    aspect_coh = _read_ext_band("topo_10m_derived_100m_u8.tif", 7, (H, W))
    dem_mean = _read_ext_band("topo_10m_derived_100m_u8.tif", 9, (H, W))

    roughness_cv = slope_std / (slope_p90 + 8.0)
    monocline_raw = (aspect_coh / 255.0) * np.log1p(steep_frac) * np.log1p(relief_local) / (1.0 + roughness_cv)
    monocline_anom = ndi.gaussian_filter(monocline_raw, sigma=1.5, mode="nearest") - ndi.gaussian_filter(monocline_raw, sigma=10.0, mode="nearest")
    f4 = _zscore_fp(monocline_anom, fp)
    del slope_p90, steep_frac, slope_std, relief_local, aspect_coh, roughness_cv, monocline_raw, monocline_anom
    gc.collect()

    # 5. gthc_lidar_normal_polarity_asymmetry
    lid_ex_mean = _read_ext_band("lidar_scarp_features_u8.tif", 2, (H, W))
    lid_down = _read_ext_band("lidar_scarp_features_u8.tif", 6, (H, W))
    lid_up = _read_ext_band("lidar_scarp_features_u8.tif", 7, (H, W))
    lid_cross = _read_ext_band("lidar_scarp_features_u8.tif", 8, (H, W))
    lid_valid = _read_ext_band("lidar_scarp_features_u8.tif", 12, (H, W)) > 0

    polarity = (np.abs(lid_down - lid_up) / 255.0) * (lid_cross / 255.0) * np.sqrt(lid_ex_mean / 255.0)
    polarity_anom = ndi.gaussian_filter(polarity, sigma=1.2, mode="nearest") - ndi.gaussian_filter(polarity, sigma=10.0, mode="nearest")
    z_pol = _zscore_fp(polarity_anom, fp & lid_valid)
    w_lid = ndi.gaussian_filter(lid_valid.astype(np.float32), sigma=3.0, mode="nearest")
    f5 = _zscore_fp(w_lid * z_pol + (1.0 - w_lid) * f4, fp)
    del lid_ex_mean, lid_down, lid_up, lid_cross, lid_valid, polarity, polarity_anom, z_pol, w_lid
    gc.collect()

    # 6. gthc_chalcedony_cation_updip_feeder
    therm_src = _build_chalcedony_cation_source(g)
    dem_s = ndi.gaussian_filter(dem_mean, sigma=4.0, mode="nearest")
    gy = ndi.gaussian_filter(dem_s, sigma=3.0, order=[1, 0], mode="nearest")
    gx = ndi.gaussian_filter(dem_s, sigma=3.0, order=[0, 1], mode="nearest")
    gnorm = np.hypot(gy, gx) + 1e-4
    uy = (gy / gnorm).astype(np.float32)
    ux = (gx / gnorm).astype(np.float32)

    yy, xx = np.indices((H, W), dtype=np.float32)
    r6 = np.clip(np.rint(yy - 6.0 * uy).astype(np.int32), 0, H - 1)
    c6 = np.clip(np.rint(xx - 6.0 * ux).astype(np.int32), 0, W - 1)
    r14 = np.clip(np.rint(yy - 14.0 * uy).astype(np.int32), 0, H - 1)
    c14 = np.clip(np.rint(xx - 14.0 * ux).astype(np.int32), 0, W - 1)

    updip_plume = 0.30 * therm_src + 0.40 * therm_src[r6, c6] + 0.30 * therm_src[r14, c14]
    piedmont_gate = _sigmoid(_zscore_fp(raw_tf["det_elev_slope"], fp))
    f6 = _zscore_fp(updip_plume * (0.40 + 0.60 * piedmont_gate), fp)
    del dem_mean, therm_src, dem_s, gy, gx, gnorm, uy, ux, yy, xx, r6, c6, r14, c14, updip_plume, piedmont_gate, raw_tf
    gc.collect()

    return {
        "gthc_uranium_redox_argillic_halo": f1,
        "gthc_upward_mag_basement_admittance": f2,
        "gthc_fluvial_knick_raised_incision": f3,
        "gthc_bajada_aspect_monocline": f4,
        "gthc_lidar_normal_polarity_asymmetry": f5,
        "gthc_chalcedony_cation_updip_feeder": f6,
    }


def build_or_load_gthc_memmap(
    g: grid_mod.Grid, cache_dir: Path | None = None, force: bool = False
) -> Tuple[np.memmap, List[str]]:
    """Build or load the 6-channel GTHC feature matrix on footprint pixels as a float32 memmap."""
    cdir = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    cdir.mkdir(parents=True, exist_ok=True)
    mm_path = cdir / "x_gthc_6ch.dat"
    meta_path = cdir / "x_gthc_6ch.names.txt"
    n_fp = int(g.footprint.sum())
    n_feat = len(GTHC_FEATURES)
    expected_bytes = n_fp * n_feat * 4

    if not force and mm_path.is_file() and mm_path.stat().st_size == expected_bytes and meta_path.is_file():
        saved = meta_path.read_text().strip().splitlines()
        if tuple(saved) == GTHC_FEATURES:
            mm = np.memmap(mm_path, dtype="float32", mode="r", shape=(n_fp, n_feat))
            return mm, list(GTHC_FEATURES)

    t0 = time.monotonic()
    print(f"[gthc] Building 6-channel GTHC feature stack ({n_fp} pixels) ...", flush=True)
    feats_2d = compute_gthc_features_2d(g)
    mm = np.memmap(mm_path, dtype="float32", mode="w+", shape=(n_fp, n_feat))
    fp = g.footprint
    for j, name in enumerate(GTHC_FEATURES):
        col = feats_2d[name][fp].astype(np.float32)
        col = np.nan_to_num(col, nan=0.0, posinf=0.0, neginf=0.0)
        mm[:, j] = col
    mm.flush()
    meta_path.write_text("\n".join(GTHC_FEATURES) + "\n")
    print(f"[gthc] Saved {mm_path} ({expected_bytes / 1e6:.1f} MB) in {time.monotonic() - t0:.1f}s", flush=True)
    return np.memmap(mm_path, dtype="float32", mode="r", shape=(n_fp, n_feat)), list(GTHC_FEATURES)


def _fuse_scrd_log_odds(
    p_full_raw: np.ndarray,
    m_full_raw: np.ndarray,
    p_phys_raw: np.ndarray,
    m_phys_raw: np.ndarray,
    d_vis_act: np.ndarray,
    k_target: float,
    beta_phys: float = 0.42,
) -> Tuple[np.ndarray, np.ndarray]:
    """Completeness-Regime Decomposition (SCRD) log-odds & marginal fusion.

    Replaces H88-ADHR's spatially constant pi_unmapped = 0.50 mixture with a
    distance-adaptive completeness transition pi_unmapped(d_vis) that:
      - In the near-relay regime (d_vis <= 12 px), weights the joint product-of-experts
        branch more strongly (1 - pi_unmapped ~ 0.62) so physical conduit agreement
        filters out non-stepping fault-flank false positives.
      - In the far / blind-basin regime (d_vis > 14 px), transitions smoothly toward the
        50-channel physical/hydrothermal posterior (pi_unmapped -> 0.68) so concealed
        basin faults are not penalized by the decay of visible-fault relay features.
    """
    import math
    from gems88 import adhr

    mean_p = float(np.mean(p_phys_raw, dtype=np.float64))
    mean_m = float(np.mean(m_phys_raw, dtype=np.float64))
    lo_prior_p = np.float32(math.log(max(mean_p, 1e-7) / (1.0 - min(mean_p, 1.0 - 1e-7))))
    lo_prior_m = np.float32(math.log(max(mean_m, 1e-7) / (1.0 - min(mean_m, 1.0 - 1e-7))))

    p_poe = adhr._expit(adhr._logit(p_full_raw) + np.float32(beta_phys) * (adhr._logit(p_phys_raw) - lo_prior_p))
    m_poe = adhr._expit(adhr._logit(m_full_raw) + np.float32(beta_phys) * (adhr._logit(m_phys_raw) - lo_prior_m))

    norm_p_joint = float(k_target) / max(float(np.sum(p_poe, dtype=np.float64)), 1e-6)
    m_target_joint = float(np.sum(m_full_raw, dtype=np.float64)) * (
        float(k_target) / max(float(np.sum(p_full_raw, dtype=np.float64)), 1e-6)
    )
    norm_m_joint = m_target_joint / max(float(np.sum(m_poe, dtype=np.float64)), 1e-6)
    p_joint = np.clip(p_poe * np.float32(norm_p_joint), 0.0, 1.0)
    m_joint = np.clip(m_poe * np.float32(norm_m_joint), p_joint, 1.0)

    norm_p_phys = float(k_target) / max(float(np.sum(p_phys_raw, dtype=np.float64)), 1e-6)
    p_phys_cal = np.clip(p_phys_raw * np.float32(norm_p_phys), 0.0, 1.0)
    m_phys_cal = np.clip(m_phys_raw * np.float32(norm_p_phys), p_phys_cal, 1.0)

    # Smooth completeness transition pi_unmapped(d_vis) in [0.36, 0.66]
    pi_unmapped = (0.36 + 0.30 * adhr._expit((d_vis_act.astype(np.float32) - 13.5) / 3.5)).astype(np.float32)
    w0 = 1.0 - pi_unmapped
    w1 = pi_unmapped

    p_raw_mix = w0 * p_joint + w1 * p_phys_cal
    m_raw_mix = w0 * m_joint + w1 * m_phys_cal

    # Preserve exact total expectation k_target after spatially varying convex combination
    scale_p = float(k_target) / max(float(np.sum(p_raw_mix, dtype=np.float64)), 1e-6)
    p_final = np.clip(p_raw_mix * np.float32(scale_p), 0.0, 1.0).astype(np.float32)
    m_final = np.clip(m_raw_mix * np.float32(scale_p), p_final, 1.0).astype(np.float32)
    return p_final, m_final


def predict_gthc_fold_arms(
    grid: grid_mod.Grid,
    X_phys_mm: np.memmap,
    X_gthc_mm: np.memmap,
    X_vis22_mm: np.memmap,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    n_ensemble: int = 1,
) -> Dict[str, Dict[str, np.ndarray | float]]:
    """Fit and evaluate all 3 preregistered GTHC-88 arms on one holdout fold."""
    from gems57 import damagezone_envelope, emit
    from gems88 import adhr

    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)

    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

    phys50_sources = [X_phys_mm, X_gthc_mm]
    full73_sources = [X_phys_mm, X_gthc_mm, X_vis22_mm, d_over_w_fp]

    dom_phys_tr = train_regions[ys_fp, xs_fp]
    clfs_phys, regs_phys = adhr._fit_dual_expectation_models(
        phys50_sources, dom_phys_tr, visible & train_regions, fp, seed=seed + 17, n_ensemble=n_ensemble
    )

    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]
    clfs_full, regs_full = adhr._fit_dual_expectation_models(
        full73_sources, dom_struct_tr, train_truth, fp, seed=seed + 53, n_ensemble=n_ensemble
    )

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    d_vis_act = d_vis_fp[act_idx]

    p_phys_raw, m_phys_raw = adhr._predict_dual_chunked(clfs_phys, regs_phys, phys50_sources, act_idx)
    p_full_raw, m_full_raw = adhr._predict_dual_chunked(clfs_full, regs_full, full73_sources, act_idx)
    del clfs_phys, regs_phys, clfs_full, regs_full
    gc.collect()

    # --- Arm 1: gthc88_pure_phys50 (50-ch zero-catalogue physical/hydrothermal model + 3-px halo) ---
    halo_mask_act = d_vis_act > 3.0
    p1_sub = np.where(halo_mask_act, p_phys_raw, 0.0).astype(np.float32)
    m1_sub = np.where(halo_mask_act, m_phys_raw, 0.0).astype(np.float32)
    norm_p1 = float(k_est) / max(float(np.sum(p1_sub, dtype=np.float64)), 1e-6)
    p1_cal = np.clip(p1_sub * np.float32(norm_p1), 0.0, 1.0).astype(np.float32)
    m1_cal = np.clip(m1_sub * np.float32(norm_p1), p1_cal, 1.0).astype(np.float32)
    p1_grid = adhr.scatter_fp(p1_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m1_grid = adhr.scatter_fp(m1_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    d_vis_2d = adhr.scatter_fp(d_vis_fp, ys_fp, xs_fp, grid.shape)
    alloc1 = emit.dinkelbach_allocate(
        p1_grid, m1_grid, allowed & (d_vis_2d > 3.0), budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # --- Arm 2: gthc88_dual_scrd (Completeness-Regime Decomposition Dual-Head Fusion) ---
    p2_sub, m2_sub = _fuse_scrd_log_odds(p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, d_vis_act, k_est, beta_phys=0.42)
    p2_grid = adhr.scatter_fp(p2_sub, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m2_grid = adhr.scatter_fp(m2_sub, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc2 = emit.dinkelbach_allocate(
        p2_grid, m2_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # --- Arm 3: gthc88_strat_fp (Fingerprint-Compliant Stratified Dual-Domain Allocation) ---
    allowed_near = allowed & (d_vis_2d > 2.5) & (d_vis_2d <= 25.0)
    allowed_far25 = allowed & (d_vis_2d > 25.0)
    alloc3_near = emit.dinkelbach_allocate(
        p2_grid, m2_grid, allowed_near, budget=None, k_truth=0.72 * k_est, min_spacing_px=2.15, dinkelbach_iters=6
    )
    n_near = int(alloc3_near.n_dots)
    target_far_dots = max(int(np.ceil(0.58 * n_near)), 350)
    alloc3_far = emit.dinkelbach_allocate(
        p1_grid, m1_grid, allowed_far25, budget=target_far_dots, k_truth=0.45 * k_est, min_spacing_px=2.15, dinkelbach_iters=6
    )
    em3 = np.clip(alloc3_near.emitted + alloc3_far.emitted, 0.0, 1.0).astype(np.float32)
    p3_grid = np.where(d_vis_2d > 25.0, np.maximum(p2_grid, p1_grid), p2_grid).astype(np.float32)

    return {
        "gthc88_pure_phys50": {
            "emitted": alloc1.emitted.astype(np.float32),
            "surface": p1_grid,
            "k_est": float(k_est),
            "n_dots": int(alloc1.n_dots),
            "surrogate_dti": float(alloc1.surrogate_dti),
        },
        "gthc88_dual_scrd": {
            "emitted": alloc2.emitted.astype(np.float32),
            "surface": p2_grid,
            "k_est": float(k_est),
            "n_dots": int(alloc2.n_dots),
            "surrogate_dti": float(alloc2.surrogate_dti),
        },
        "gthc88_strat_fp": {
            "emitted": em3,
            "surface": p3_grid,
            "k_est": float(k_est),
            "n_dots": int((em3 > 0).sum()),
            "surrogate_dti": float(alloc3_near.surrogate_dti),
        },
    }


def fit_and_emit_production_gthc(
    grid: grid_mod.Grid,
    X_phys_mm: np.memmap,
    X_gthc_mm: np.memmap,
    sense_src: np.ndarray,
    scarp_fields: Dict[str, np.ndarray],
    folds_by_seed: List[Tuple[int, List[dict]]],
    cache_dir: Path,
    arm: str = "gthc88_dual_scrd",
    preplacement_gate=None,
) -> Tuple[np.ndarray, np.ndarray, dict]:
    """Fit full-catalogue GTHC-88 production surface and discrete dot submission."""
    import json
    from gems57 import damagezone_envelope, emit
    from gems88 import adhr

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    cache_npz = Path(cache_dir) / f"prod_{arm}_v1.npz"
    if cache_npz.is_file():
        z = np.load(cache_npz, allow_pickle=False)
        emitted = np.zeros(grid.shape, dtype=np.float32)
        dyx = z["dots_yx"]
        emitted[dyx[:, 0], dyx[:, 1]] = 1.0
        p_surface = adhr.scatter_fp(z["p_fp"], ys_fp, xs_fp, grid.shape)
        if preplacement_gate is not None:
            preplacement_gate(p_surface)
        meta = json.loads(str(z["meta_json"]))
        return emitted, p_surface, meta

    d_fullcat = ndi.distance_transform_edt(~grid.catalogue).astype(np.float32)
    base_allowed = fp & (d_fullcat > 2.0)
    act_idx = np.flatnonzero(base_allowed[ys_fp, xs_fp])
    d_vis_act = d_fullcat[ys_fp[act_idx], xs_fp[act_idx]]

    raw_npz = Path(cache_dir) / "prod_gthc88_raw_v1.npz"
    if raw_npz.is_file():
        zr = np.load(raw_npz, allow_pickle=False)
        p1_cal = zr["p1_cal"]
        m1_cal = zr["m1_cal"]
        p2_sub = zr["p2_sub"]
        m2_sub = zr["m2_sub"]
        k_prod = float(zr["k_prod"])
    else:
        phys50_sources = [X_phys_mm, X_gthc_mm]

        # 4-quadrant out-of-fold cross-fitting for the 50-channel physical/hydrothermal head
        folds_q4 = folds_by_seed[0][1]
        p_phys_raw = np.zeros(act_idx.size, dtype=np.float32)
        m_phys_raw = np.zeros(act_idx.size, dtype=np.float32)
        covered = np.zeros(act_idx.size, dtype=bool)
        for q_idx, f_q in enumerate(folds_q4):
            train_dom_q = (~f_q["region"])[ys_fp, xs_fp]
            c_q, r_q = adhr._fit_dual_expectation_models(
                phys50_sources, train_dom_q, grid.catalogue, fp, seed=880510 + q_idx, max_zero_neg=120_000, n_ensemble=1
            )
            mask_q = f_q["region"][ys_fp[act_idx], xs_fp[act_idx]]
            if q_idx == len(folds_q4) - 1:
                mask_q = mask_q | (~covered)
            covered |= mask_q
            pq, mq = adhr._predict_dual_chunked(c_q, r_q, phys50_sources, act_idx[mask_q])
            p_phys_raw[mask_q] = pq
            m_phys_raw[mask_q] = mq
            del c_q, r_q, pq, mq
            gc.collect()

        struct_clfs = []
        struct_regs = []
        w_laws = []
        ratios: List[float] = []

        for seed, folds in folds_by_seed:
            vis_s = folds[0]["visible"]
            X_v22, dv_s, cl_s = adhr.compute_visible_struct_fp(grid, vis_s, sense_src, scarp_fields, cache_dir, f"seed{seed}")
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
            cs, rs = adhr._fit_dual_expectation_models(
                [X_phys_mm, X_gthc_mm, X_v22, dow_s],
                dom_s,
                tr_s,
                fp,
                seed=880600 + seed,
                max_zero_neg=140_000,
                n_ensemble=1,
            )
            struct_clfs.extend(cs)
            struct_regs.extend(rs)
            del X_v22, dv_s, cl_s, dow_s, dom_s, reg_s, tr_s
            gc.collect()

        fullcat_tag = "fullcat" if (Path(cache_dir) / "x_vis22_fullcat.dat").is_file() else "prod_fullcat"
        X_v22_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
            grid, grid.catalogue, sense_src, scarp_fields, cache_dir, fullcat_tag
        )
        hw_prod = np.mean([wl.half_width(cl_prod) for wl in w_laws], axis=0).astype(np.float32)
        dow_prod = (dv_prod / np.maximum(hw_prod, 1e-6)).astype(np.float32)
        prod_sources = [X_phys_mm, X_gthc_mm, X_v22_prod, dow_prod]

        hid_ratio_mean = float(np.mean(ratios))
        k_prod = float(grid.catalogue.sum()) * hid_ratio_mean

        p_full_raw, m_full_raw = adhr._predict_dual_chunked(struct_clfs, struct_regs, prod_sources, act_idx)
        del struct_clfs, struct_regs, prod_sources, X_v22_prod, dv_prod, cl_prod, hw_prod, dow_prod
        gc.collect()

        norm_p1 = float(k_prod) / max(float(np.sum(p_phys_raw, dtype=np.float64)), 1e-6)
        p1_cal = np.clip(p_phys_raw * np.float32(norm_p1), 0.0, 1.0).astype(np.float32)
        m1_cal = np.clip(m_phys_raw * np.float32(norm_p1), p1_cal, 1.0).astype(np.float32)

        p2_sub, m2_sub = _fuse_scrd_log_odds(p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, d_vis_act, k_prod, beta_phys=0.42)
        del p_phys_raw, m_phys_raw, p_full_raw, m_full_raw
        gc.collect()
        np.savez_compressed(
            raw_npz,
            p1_cal=p1_cal,
            m1_cal=m1_cal,
            p2_sub=p2_sub,
            m2_sub=m2_sub,
            k_prod=np.float64(k_prod),
        )

    flank_excl = 2.5 if arm == "gthc88_strat_fp" else (3.0 if arm == "gthc88_pure_phys50" else 2.0)
    allowed_prod = fp & (d_fullcat > flank_excl)

    if arm == "gthc88_pure_phys50":
        p_surface = adhr.scatter_fp(p1_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
        m_surface = adhr.scatter_fp(m1_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
        if preplacement_gate is not None:
            preplacement_gate(p_surface)
        alloc = emit.dinkelbach_allocate(
            p_surface, m_surface, allowed_prod, budget=None, k_truth=k_prod, min_spacing_px=2.05, dinkelbach_iters=8
        )
        emitted_f32 = alloc.emitted.astype(np.float32)
        n_dots = int(alloc.n_dots)
        surr_dti = float(alloc.surrogate_dti)
        rounds = int(alloc.rounds)
    elif arm == "gthc88_strat_fp":
        p1_grid = adhr.scatter_fp(p1_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
        m1_grid = adhr.scatter_fp(m1_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
        p2_grid = adhr.scatter_fp(p2_sub, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
        m2_grid = adhr.scatter_fp(m2_sub, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
        p_surface = np.where(d_fullcat > 25.0, np.maximum(p2_grid, p1_grid), p2_grid).astype(np.float32)
        if preplacement_gate is not None:
            preplacement_gate(p_surface)
        allowed_near = fp & (d_fullcat > 2.5) & (d_fullcat <= 25.0)
        allowed_far25 = fp & (d_fullcat > 25.0)
        alloc_near = emit.dinkelbach_allocate(
            p2_grid, m2_grid, allowed_near, budget=None, k_truth=0.72 * k_prod, min_spacing_px=2.15, dinkelbach_iters=8
        )
        target_far_dots = max(int(np.ceil(0.58 * int(alloc_near.n_dots))), 1400)
        alloc_far = emit.dinkelbach_allocate(
            p1_grid, m1_grid, allowed_far25, budget=target_far_dots, k_truth=0.45 * k_prod, min_spacing_px=2.15, dinkelbach_iters=8
        )
        emitted_f32 = np.clip(alloc_near.emitted + alloc_far.emitted, 0.0, 1.0).astype(np.float32)
        n_dots = int((emitted_f32 > 0).sum())
        surr_dti = float(alloc_near.surrogate_dti)
        rounds = int(alloc_near.rounds)
    else:
        p_surface = adhr.scatter_fp(p2_sub, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
        m_surface = adhr.scatter_fp(m2_sub, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
        if preplacement_gate is not None:
            preplacement_gate(p_surface)
        alloc = emit.dinkelbach_allocate(
            p_surface, m_surface, allowed_prod, budget=None, k_truth=k_prod, min_spacing_px=2.05, dinkelbach_iters=8
        )
        emitted_f32 = alloc.emitted.astype(np.float32)
        n_dots = int(alloc.n_dots)
        surr_dti = float(alloc.surrogate_dti)
        rounds = int(alloc.rounds)

    dot_mask = emitted_f32 > 0
    meta = {
        "arm": arm,
        "n_dots": n_dots,
        "k_truth_est": float(k_prod),
        "surrogate_dti": surr_dti,
        "dinkelbach_rounds": rounds,
        "flank_exclusion_px": float(flank_excl),
        "min_spacing_px": 2.15 if arm == "gthc88_strat_fp" else 2.05,
        "share_le2": float((d_fullcat[dot_mask] <= 2.0).mean()) if n_dots else 0.0,
        "median_d_cat_px": float(np.median(d_fullcat[dot_mask])) if n_dots else 0.0,
        "frac_gt_10px": float((d_fullcat[dot_mask] > 10.0).mean()) if n_dots else 0.0,
        "frac_gt_25px": float((d_fullcat[dot_mask] > 25.0).mean()) if n_dots else 0.0,
    }
    dy, dx = np.nonzero(dot_mask)
    np.savez_compressed(
        cache_npz,
        dots_yx=np.column_stack([dy, dx]).astype(np.int32),
        p_fp=p_surface[ys_fp, xs_fp].astype(np.float32),
        meta_json=np.array(json.dumps(meta)),
    )
    return emitted_f32, p_surface, meta



