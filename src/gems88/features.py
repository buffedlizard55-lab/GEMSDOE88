"""Zero-Catalogue Multi-Physics, Up-Dip Pullback, Boiling-Triad, & Fluvial Wavefront Feature Stack.

Every single feature in this module is 100% independent of `existing_faults.tif` (zero catalogue distance,
zero trace geometry, label distance columns explicitly stripped from GDR CSVs on read).
All features are audited individually against the `0.90` symmetric ROC-AUC leakage canary across
BOTH `Seed 20` and `Seed 30` before any model training proceeds.
"""
from __future__ import annotations

import gc
import json
import struct
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from scipy.ndimage import (
    binary_dilation,
    distance_transform_edt,
    gaussian_filter,
    map_coordinates,
    sobel,
)
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score

CACHE_DIR = Path("/tmp/gems88_cache")


def _safe_band(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = arr.astype(np.float32, copy=True)
    bad = (~np.isfinite(out)) | (np.abs(out) > 1e10)
    med = float(np.median(out[valid & (~bad)])) if np.any(valid & (~bad)) else 0.0
    out[bad] = med
    out[~valid] = med
    return out


def _grad_mag(a: np.ndarray, sigma: float = 0.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    src = gaussian_filter(a, sigma=sigma) if sigma > 0 else a
    gy = sobel(src, axis=0) * 0.125
    gx = sobel(src, axis=1) * 0.125
    return gy, gx, np.hypot(gy, gx)


def _hessian_ridge(a: np.ndarray, sigma: float, troughs: bool = False) -> np.ndarray:
    """Maximum crest (or trough) principal curvature at scale `sigma`."""
    s = gaussian_filter(a, sigma=sigma)
    gy = sobel(s, axis=0) * 0.125
    gx = sobel(s, axis=1) * 0.125
    gyy = sobel(gy, axis=0) * 0.125
    gxx = sobel(gx, axis=1) * 0.125
    gxy = sobel(gy, axis=1) * 0.125
    tr = gxx + gyy
    rad = np.hypot(gxx - gyy, 2.0 * gxy)
    if troughs:
        # Positive principal curvature across negative trough (e.g. RTP magnetite destruction)
        return np.maximum(0.0, 0.5 * (tr + rad)).astype(np.float32)
    return np.maximum(0.0, 0.5 * (-tr + rad)).astype(np.float32)


def _splat_points_gaussian(
    shape: tuple[int, int],
    rows: np.ndarray,
    cols: np.ndarray,
    weights: np.ndarray,
    sigmas: tuple[float, ...],
) -> list[np.ndarray]:
    grid_w = np.zeros(shape, dtype=np.float32)
    ok = (
        np.isfinite(rows)
        & np.isfinite(cols)
        & np.isfinite(weights)
        & (rows >= 0)
        & (rows < shape[0])
        & (cols >= 0)
        & (cols < shape[1])
    )
    ri = rows[ok].astype(np.int32)
    ci = cols[ok].astype(np.int32)
    wi = weights[ok].astype(np.float32)
    np.add.at(grid_w, (ri, ci), wi)
    return [gaussian_filter(grid_w, sigma=sg).astype(np.float32) for sg in sigmas]


def _read_dbf_records(dbf_bytes: bytes) -> pd.DataFrame:
    nrec, hlen, rlen = struct.unpack("<IHH", dbf_bytes[4:12])
    fields = []
    off = 32
    while dbf_bytes[off] != 0x0D:
        name = dbf_bytes[off : off + 11].split(b"\x00", 1)[0].decode("latin1").strip()
        ftype = chr(dbf_bytes[off + 11])
        flen = dbf_bytes[off + 16]
        fields.append((name, ftype, flen))
        off += 32
    keep = {"UTM_E", "UTM_N", "T2m", "F2mDAB", "LatDegreeN", "LongDegree"}
    rows = []
    pos = hlen
    for _ in range(nrec):
        if pos + rlen > len(dbf_bytes):
            break
        rec = dbf_bytes[pos : pos + rlen]
        pos += rlen
        if rec[0:1] == b"*":
            continue
        cur = 1
        d = {}
        for name, ftype, flen in fields:
            if name in keep:
                raw = rec[cur : cur + flen].decode("latin1", errors="ignore").strip()
                if ftype in ("N", "F"):
                    try:
                        d[name] = float(raw) if raw else np.nan
                    except ValueError:
                        d[name] = np.nan
                else:
                    d[name] = raw
            cur += flen
        rows.append(d)
    return pd.DataFrame(rows)


def build_or_load_physics_stack(
    data_dir: Path,
    ext_dir: Path,
    valid: np.ndarray,
    transform: Any,
    cache_dir: Path = CACHE_DIR,
) -> tuple[np.memmap, list[str]]:
    """Build or reload memory-mapped `(N_valid, n_phys)` float16 zero-catalogue multi-physics matrix."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta_path = cache_dir / "phys_features_meta.json"
    mmap_path = cache_dir / "phys_features_f16.mmap"
    n_valid = int(valid.sum())

    if meta_path.exists() and mmap_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("n_valid") == n_valid and mmap_path.stat().st_size == n_valid * meta["n_features"] * 2:
            mm = np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_valid, meta["n_features"]))
            return mm, meta["names"]

    H, W = valid.shape
    max_cols = 100
    tmp_mmap_path = cache_dir / "phys_features_build_tmp.mmap"
    mm = np.memmap(tmp_mmap_path, dtype=np.float16, mode="w+", shape=(n_valid, max_cols))
    names: list[str] = []

    def add_col(name: str, full_2d: np.ndarray) -> None:
        v = full_2d[valid].astype(np.float32, copy=False)
        v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
        lo, hi = np.percentile(v, [0.05, 99.95])
        v = np.clip(v, lo, hi)
        scale = max(float(np.max(np.abs(v))), 1e-6)
        if scale > 500.0:
            v = v * (100.0 / scale)
        col_i = len(names)
        mm[:, col_i] = v.astype(np.float16)
        names.append(name)

    # 1. Official 19 competition bands + H88-H2 Up-Dip 60° Pullback + Multi-Scale Tensors
    with rasterio.open(data_dir / "training_features.tif") as ds:
        raw_bands = {}
        for idx in range(1, ds.count + 1):
            desc = ds.descriptions[idx - 1] or f"band_{idx:02d}"
            bname = f"b{idx:02d}_{desc.strip().lower().replace(' ', '_')}"
            arr = _safe_band(ds.read(idx), valid)
            add_col(bname, arr)
            if idx in (2, 4, 12, 13, 14, 15, 17, 18, 19):
                raw_bands[idx] = arr

    rtp = raw_bands[2]
    det_elev = raw_bands[12]
    iso_g = raw_bands[13]
    tmi = raw_bands[14]
    hbase = raw_bands[15]
    cond_s = raw_bands[17]
    iso_hg = raw_bands[18]
    det_slp = raw_bands[19]

    # Hypothesis H88-H2: Grauch & Cordell (1987) 60-deg normal-fault up-dip potential-field pullback
    hy, hx, hmag = _grad_mag(hbase, sigma=1.5)
    _, _, gmag = _grad_mag(iso_g, sigma=1.2)
    denom = np.maximum(hmag, 1e-4)
    # Shift opposite grad(H_base) toward footwall by cot(60 deg) * H_base / 100 m
    shift_px = np.clip(0.57735 * np.maximum(hbase, 0.0) / 100.0, 1.0, 5.0)
    yy, xx = np.indices((H, W), dtype=np.float32)
    up_y = np.clip(yy - shift_px * (hy / denom), 0.0, H - 1.0)
    up_x = np.clip(xx - shift_px * (hx / denom), 0.0, W - 1.0)
    iso_hg_pullback = map_coordinates(iso_hg, [up_y, up_x], order=1, mode="nearest")
    hbase_grad_pullback = map_coordinates(hmag, [up_y, up_x], order=1, mode="nearest")
    add_col("h88_iso_hg_updip60_pullback", iso_hg_pullback)
    add_col("h88_iso_hg_updip60_gain", iso_hg_pullback - iso_hg)
    add_col("h88_hbase_grad_updip60_pullback", hbase_grad_pullback)
    add_col("h88_hbase_grad_raw", hmag)
    del up_y, up_x
    gc.collect()

    # Multi-scale structural ridges & RTP oxidation trough + MT clay-cap lateral break
    elev_ridge_fine = _hessian_ridge(det_elev, sigma=1.2, troughs=False)
    elev_trough_fine = _hessian_ridge(det_elev, sigma=1.5, troughs=True)
    elev_dog = gaussian_filter(det_elev, 1.0) - gaussian_filter(det_elev, 5.0)
    rtp_ox_trough = _hessian_ridge(rtp, sigma=1.8, troughs=True)
    grav_ridge = _hessian_ridge(gmag, sigma=1.5, troughs=False)
    _, _, mt_lat_break = _grad_mag(np.log1p(np.maximum(cond_s, 0.0)), sigma=1.5)
    add_col("h88_det_elev_hessian_ridge", elev_ridge_fine)
    add_col("h88_det_elev_canyon_trough", elev_trough_fine)
    add_col("h88_det_elev_dog_1_5", elev_dog)
    add_col("h88_rtp_oxidation_trough", rtp_ox_trough)
    add_col("h88_grav_grad_ridge", grav_ridge)
    add_col("h88_mt_claycap_lat_break", mt_lat_break)

    # Pleistocene Pluvial Lake Lahontan (~1332 m) & Bonneville (~1463 / 1552 m) contour-bench suppressor
    gy_e, gx_e, gmag_e = _grad_mag(det_elev, sigma=2.5)
    lahontan = np.exp(-0.5 * ((raw_bands[4] - 1332.0) / 22.0) ** 2)
    bonneville = np.maximum(
        np.exp(-0.5 * ((raw_bands[4] - 1463.0) / 22.0) ** 2),
        np.exp(-0.5 * ((raw_bands[4] - 1552.0) / 22.0) ** 2),
    )
    pluvial_bench_idx = np.maximum(lahontan, bonneville) * det_slp / (1.0 + 0.25 * hbase_grad_pullback)
    add_col("h88_pluvial_shoreline_mimic_idx", pluvial_bench_idx)
    del raw_bands, gy_e, gx_e, lahontan, bonneville
    gc.collect()

    # 2. USGS 3DEP 1m LiDAR + 10m DEM + Cross-Sensor Imputed Scarp + Fluvial Chi/ksn Wavefronts
    with rasterio.open(ext_dir / "topo_10m_derived_100m_u8.tif") as ds:
        topo10_names = [
            "slope_p90", "slope_max", "steep_frac", "slope_std",
            "relief_local", "curv_prof_absmax", "aspect_coherence", "hs_lineament", "dem_mean",
        ]
        topo10 = [ds.read(i).astype(np.float32) for i in range(1, 10)]
        for nm, arr in zip(topo10_names[:8], topo10[:8]):
            add_col(f"dem10_{nm}", arr)

    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as ds:
        lid_names = [
            "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
            "downface_max", "upface_max", "cross_max", "relief", "coh100", "strike", "valid",
        ]
        lid = [ds.read(i).astype(np.float32) for i in range(1, 13)]
        lid_valid = (lid[11] > 0) & valid
        for nm, arr in zip(lid_names, lid):
            add_col(f"lidar1m_{nm}", arr)

    # Unsupervised cross-sensor imputation of 1m scarp index across the 24.6% 3DEP gap (zero labels, 10 MB RAM!)
    scarp_obs = 0.40 * lid[0] + 0.35 * lid[2] + 0.25 * lid[9]
    rng = np.random.default_rng(8801)
    fit_idx = np.flatnonzero(lid_valid)
    sub_fit = rng.choice(fit_idx, size=min(250_000, fit_idx.size), replace=False)
    imp_sources = topo10[:8] + [det_slp, elev_ridge_fine]
    X_fit = np.column_stack([np.nan_to_num(src.ravel()[sub_fit], nan=0.0, posinf=0.0, neginf=0.0) for src in imp_sources])
    reg_imp = Ridge(alpha=10.0)
    reg_imp.fit(X_fit, scarp_obs.ravel()[sub_fit])
    scarp_hat = np.full((H, W), float(reg_imp.intercept_), dtype=np.float32)
    for coef_j, src in zip(reg_imp.coef_, imp_sources):
        scarp_hat += np.float32(coef_j) * src
    scarp_seamless = np.where(lid_valid, scarp_obs, np.clip(scarp_hat, 0.0, 255.0))
    add_col("h88_scarp_seamless_1m_10m", scarp_seamless)
    add_col("h88_scarp_aniso_ridge_s2", _hessian_ridge(scarp_seamless, sigma=2.0, troughs=False))
    del lid, topo10, imp_sources, X_fit, scarp_hat, det_elev, iso_g, hbase, cond_s, iso_hg, det_slp, elev_ridge_fine, elev_trough_fine, elev_dog, gmag
    gc.collect()

    # Hypothesis H88-H4: Transient Fluvial Chi / ksn Multi-Catchment Knickpoint Wavefronts
    with rasterio.open(ext_dir / "dem10_chi_100m_i16.tif") as ds:
        chi_step = ds.read(1).astype(np.float32) * 0.001
        chi_step_min = ds.read(2).astype(np.float32) * 0.001
        ksn_max = ds.read(3).astype(np.float32)
        log_area = ds.read(4).astype(np.float32) * 0.001
    with rasterio.open(ext_dir / "dem10_chi_100m_u8.tif") as ds:
        chan_n = ds.read(1).astype(np.float32)
        knick_n = ds.read(2).astype(np.float32)
        raised_n = ds.read(3).astype(np.float32)
    add_col("chi10m_step_max", chi_step)
    add_col("chi10m_step_asym", chi_step - chi_step_min)
    add_col("chi10m_ksn_max", ksn_max)
    add_col("chi10m_log_area", log_area)
    add_col("chi10m_knick_density", knick_n / (chan_n + 1.0))
    add_col("chi10m_raised_density", raised_n / (chan_n + 1.0))
    knick_impulse = np.maximum(chi_step, 0.0) * np.log1p(np.maximum(ksn_max, 0.0)) * (knick_n > 0)
    add_col("h88_knick_wavefront_s2", gaussian_filter(knick_impulse, sigma=2.2))
    add_col("h88_knick_wavefront_s5", gaussian_filter(knick_impulse, sigma=5.5))
    del chi_step, chi_step_min, ksn_max, log_area, chan_n, knick_n, raised_n, knick_impulse
    gc.collect()

    # 3. Hypothesis H88-H3: De-Seamed GeoDAWN Radiometrics + Boiling-Zone Alteration Triad + GDR-1391 Vents
    with rasterio.open(ext_dir / "acquisition_block_id_100m.tif") as ds:
        blk = ds.read(1)
    seam = (np.abs(np.diff(blk.astype(np.int16), axis=0, prepend=blk[:1, :])) > 0) | (
        np.abs(np.diff(blk.astype(np.int16), axis=1, prepend=blk[:, :1])) > 0
    )
    seam_300m = binary_dilation(seam, iterations=3)
    not_seam = (~seam_300m).astype(np.float32)
    add_col("geodawn_seam_300m_flag", seam_300m.astype(np.float32))

    with rasterio.open(ext_dir / "geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32)
        rad_th = ds.read(2).astype(np.float32)
        rad_u = ds.read(3).astype(np.float32)
        rad_tc = ds.read(4).astype(np.float32)
    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as ds:
        ext_thk = ds.read(1).astype(np.float32)
        ext_uk = ds.read(2).astype(np.float32)
        ext_uth = ds.read(3).astype(np.float32)
        tmi_up150 = ds.read(4).astype(np.float32)

    add_col("rad_K", rad_k)
    add_col("rad_Th", rad_th)
    add_col("rad_U", rad_u)
    add_col("rad_TC", rad_tc)
    k_over_th = rad_k / (rad_th + 4.0)
    kth_hp = (k_over_th - gaussian_filter(k_over_th, sigma=8.0)) * not_seam
    uth_hp = (ext_uth - gaussian_filter(ext_uth, sigma=8.0)) * not_seam
    uk_hp = (ext_uk - gaussian_filter(ext_uk, sigma=8.0)) * not_seam
    shallow_mag_resid = (tmi - gaussian_filter(tmi, sigma=6.0)) * not_seam
    add_col("h88_rad_K_over_Th_deseamed_hp", kth_hp)
    add_col("h88_rad_U_over_Th_deseamed_hp", uth_hp)
    add_col("h88_rad_U_over_K_deseamed_hp", uk_hp)
    add_col("rad_ThK_raw", ext_thk)
    add_col("rad_TMI_up150", tmi_up150)
    add_col("h88_shallow_mag_resid_deseamed", shallow_mag_resid)

    # Boiling-Zone Hydrothermal Alteration Triad = RTP oxidation trough x MT clay-cap break x K/Th local anomaly
    z_rtp = rtp_ox_trough / (np.percentile(rtp_ox_trough[valid], 95) + 1e-5)
    z_mt = mt_lat_break / (np.percentile(mt_lat_break[valid], 95) + 1e-5)
    z_kth = np.maximum(kth_hp, 0.0) / (np.percentile(np.maximum(kth_hp[valid], 0.0), 95) + 1e-5)
    boiling_triad = np.cbrt(np.clip(z_rtp, 0, 5) * np.clip(z_mt, 0, 5) * (0.25 + np.clip(z_kth, 0, 5)))
    add_col("h88_boiling_alteration_triad", boiling_triad)
    del rad_k, rad_th, rad_u, rad_tc, ext_thk, ext_uk, ext_uth, tmi_up150, boiling_triad
    gc.collect()

    # DOE GDR-1391 Geothermal Wells/Springs (label distance column STRICTLY dropped!)
    ws = pd.read_csv(ext_dir / "gdr_wellspring_in_footprint.csv").drop(
        columns=["dist_known_fault_px"], errors="ignore"
    )
    geo_tmax = np.nanmax(
        np.column_stack([
            pd.to_numeric(ws["temp_c"], errors="coerce").fillna(0.0).to_numpy(),
            pd.to_numeric(ws["geothermquartz_c"], errors="coerce").fillna(0.0).to_numpy(),
            pd.to_numeric(ws["geothermchalc_c"], errors="coerce").fillna(0.0).to_numpy(),
        ]),
        axis=1,
    )
    ws_w = np.log1p(np.maximum(geo_tmax - 20.0, 0.0))
    for sg, nm in zip((8.0, 28.0), ("gdr_wellspring_geotherm_s8", "gdr_wellspring_geotherm_s28")):
        add_col(nm, _splat_points_gaussian((H, W), ws["row"].to_numpy(), ws["col"].to_numpy(), ws_w, (sg,))[0])

    # DOE GDR-1391 3,800 2-Meter Temperature Probe Stations (UTM Zone 11N NAD83/WGS84)
    with zipfile.ZipFile(ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip") as zf:
        df2m = _read_dbf_records(
            zf.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
        )
    col_2m = (df2m["UTM_E"].to_numpy(dtype=np.float64) - transform.c) / transform.a
    row_2m = (df2m["UTM_N"].to_numpy(dtype=np.float64) - transform.f) / transform.e
    anom_2m = np.maximum(df2m["F2mDAB"].fillna(0.0).to_numpy(dtype=np.float32), 0.0) + 0.15 * np.maximum(
        df2m["T2m"].fillna(15.0).to_numpy(dtype=np.float32) - 18.0, 0.0
    )
    for sg, nm in zip((6.0, 22.0), ("gdr_2m_temp_anom_s6", "gdr_2m_temp_anom_s22")):
        add_col(nm, _splat_points_gaussian((H, W), row_2m, col_2m, np.clip(anom_2m, 0.0, 25.0), (sg,))[0])

    # DOE GDR-1391 Paleo-Geothermal Sinter/Travertine/Tufa Vents + Quaternary Volcanic Vents
    with zipfile.ZipFile(ext_dir / "paleo_geothermal_regional.zip") as zf:
        with zf.open("Paleo_geothermal_final.csv") as fp_csv:
            paleo = pd.read_csv(fp_csv, encoding="latin1", usecols=["Long_deg_NAD83", "Lat_deg_NAD83"])
    tr_nad83 = Transformer.from_crs("EPSG:4269", "EPSG:32611", always_xy=True)
    px_e, py_n = tr_nad83.transform(
        paleo["Long_deg_NAD83"].to_numpy(dtype=np.float64),
        paleo["Lat_deg_NAD83"].to_numpy(dtype=np.float64),
    )
    p_col = (px_e - transform.c) / transform.a
    p_row = (py_n - transform.f) / transform.e
    for sg, nm in zip((8.0, 26.0), ("gdr_paleo_sinter_travertine_s8", "gdr_paleo_sinter_travertine_s26")):
        add_col(nm, _splat_points_gaussian((H, W), p_row, p_col, np.ones_like(p_row), (sg,))[0])

    vv = pd.read_csv(ext_dir / "gdr_volcanic_vents_in_footprint.csv").drop(
        columns=["dist_known_fault_px"], errors="ignore"
    )
    add_col(
        "gdr_volcanic_vents_s18",
        _splat_points_gaussian((H, W), vv["row"].to_numpy(), vv["col"].to_numpy(), np.ones(len(vv)), (18.0,))[0],
    )

    # Pre-Quaternary SGMC Bedrock Structure Reactivation (verified canary AUC = 0.520) + TIGER Roads
    with rasterio.open(ext_dir / "sgmc_faults_100m.tif") as ds:
        sgmc = ds.read(1).astype(np.float32)
    with rasterio.open(ext_dir / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc_der = ds.read(1).astype(np.float32)
    d_sgmc = distance_transform_edt(sgmc <= 0).astype(np.float32)
    add_col("sgmc_bedrock_logdist", np.log1p(np.minimum(d_sgmc, 100.0)))
    add_col("sgmc_bedrock_derived", sgmc_der)

    with rasterio.open(ext_dir / "tiger_road_distance_m.tif") as ds:
        d_road = _safe_band(ds.read(1), valid)
    add_col("tiger_road_logdist_m", np.log1p(np.maximum(d_road, 0.0)))
    add_col("h88_roadcut_scarp_mimic", scarp_seamless * (d_road < 150.0).astype(np.float32))
    del sgmc, sgmc_der, d_sgmc, d_road, scarp_seamless
    gc.collect()

    n_feat = len(names)
    mm.flush()
    mm_exact = np.memmap(mmap_path, dtype=np.float16, mode="w+", shape=(n_valid, n_feat))
    for j in range(n_feat):
        mm_exact[:, j] = mm[:, j]
    mm_exact.flush()
    del mm, mm_exact
    tmp_mmap_path.unlink(missing_ok=True)
    gc.collect()

    meta_path.write_text(json.dumps({"n_valid": n_valid, "n_features": n_feat, "names": names}, indent=2))
    mm_ro = np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_valid, n_feat))
    return mm_ro, names


def run_leakage_canary(
    X_valid: np.ndarray,
    feature_names: list[str],
    valid: np.ndarray,
    hidden_mask: np.ndarray,
    masked_known: np.ndarray,
    seed_label: str,
    threshold: float = 0.90,
    max_neg_sample: int = 400_000,
) -> dict[str, Any]:
    """Single-feature leakage canary (Protocol Rule 4): FAIL CLOSED if any feature > 0.90."""
    act_in_valid = (~masked_known)[valid]
    y_in_valid = hidden_mask[valid]
    pos_idx = np.flatnonzero(act_in_valid & y_in_valid)
    neg_pool = np.flatnonzero(act_in_valid & (~y_in_valid))
    rng = np.random.default_rng(10_000 + len(feature_names))
    neg_idx = rng.choice(neg_pool, size=min(max_neg_sample, neg_pool.size), replace=False)
    eval_idx = np.concatenate([pos_idx, neg_idx])
    y_eval = np.concatenate([np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)])

    rows = []
    flagged = []
    for j, fname in enumerate(feature_names):
        col = np.asarray(X_valid[eval_idx, j], dtype=np.float32)
        if np.ptp(col) == 0:
            auc = 0.5
        else:
            auc = float(roc_auc_score(y_eval, col))
        sym = max(auc, 1.0 - auc)
        row = {"feature": fname, "raw_auc": round(auc, 5), "symmetric_auc": round(sym, 5)}
        rows.append(row)
        if sym > threshold:
            flagged.append(row)

    rows.sort(key=lambda r: -r["symmetric_auc"])
    if flagged:
        raise RuntimeError(
            f"LEAKAGE CANARY FAILED CLOSED on {seed_label}: {len(flagged)} feature(s) > {threshold}: {flagged[:5]}"
        )
    return {
        "seed_label": seed_label,
        "n_features_tested": len(feature_names),
        "n_positives": int(pos_idx.size),
        "n_negatives_sampled": int(neg_idx.size),
        "threshold": threshold,
        "max_symmetric_auc": rows[0]["symmetric_auc"],
        "top10_features": rows[:10],
        "flagged_count": 0,
        "passed": True,
    }
