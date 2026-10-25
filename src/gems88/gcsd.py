"""H88-GCSD: Geothermometer-Discordance Upflow, Elevation-Detrended Clay-Cap Conductivity,
Critical-Seismic Transtension & Multi-Modal Strike Coherence.

Extracts 12 label-blind channels (`GCSD_FEATURES`, schema `gcsd88-12ch-v1`) from SHA-pinned
competition and official DOE GDR / USGS 3DEP datasets:
  * `data/external/gdr_wellspring_in_footprint.csv` (DOE GDR #1391: `temp_c`,
    `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`)
  * `data/external/2m_temperature_probe_INGENIOUS_regional_data.zip` (DOE GDR #1391)
  * `data/external/paleo_geothermal_regional.zip` (USGS/GBCGE sinter & travertine)
  * `data/training_features.tif` (verified 19 competition bands: B2 `rtp`, B3 `tmi_hg`,
    B4 `geod_2ndinv`, B6 `tc`, B7 `geod_shearrate`, B8 `geod_dilaterate`, B9 `tmi_vg`,
    B10 `deq_n100a15`, B11 `iso_grav_anom_vg`, B12 `det_elev`, B13 `iso_grav_anom`,
    B15 `depth_to_base_surf`, B16 `ieq_n100a15`, B17 `cond_surf`, B18 `iso_grav_anom_hg`,
    B19 `det_elev_slope`)
  * `data/external/lidar_scarp_features_u8.tif` (B4 `lapneg_max`, B5 `lappos_max`,
    B8 `cross_max`, B9 `relief`, B10 `coh100`, B11 `strike`, B12 `valid`)
  * `data/geodawn_dem_a2_100m.tif` (100 m GeoDAWN elevation)

Strictly zero catalogue access in feature construction: `existing_faults.tif` is never
read by `build_or_load_gcsd_memmap`. Memory-bounded (< 500 MB RSS) via disk-backed
float32 `np.memmap`.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as crs_transform
from scipy import ndimage as ndi

from gems57 import damagezone_envelope, emit, holdout

from . import adhr, edge, physics, tdkl

GCSD_FEATURES: tuple[str, ...] = (
    "gcsd_qtz_flash_surplus",
    "gcsd_geotherm_diseq",
    "gcsd_updip_feeder_couple",
    "gcsd_cond_elev_resid",
    "gcsd_cond_demag_concord",
    "gcsd_seismic_crit_shear",
    "gcsd_multimodal_spin2_coh",
    "gcsd_grav_zbase_admittance",
    "gcsd_tilt_contact_sharpness",
    "gcsd_bajada_hinge_asymmetry",
    "gcsd_lidar_multimodal_strike",
    "gcsd_mimic_playa_volc_pen",
)

GCSD_SCHEMA_VERSION = "gcsd88-12ch-v1"

EXPECTED_BANDS: dict[int, str] = {
    2: "rtp",
    3: "tmi_hg",
    4: "geod_2ndinv",
    6: "tc",
    7: "geod_shearrate",
    8: "geod_dilaterate",
    9: "tmi_vg",
    10: "deq_n100a15",
    11: "iso_grav_anom_vg",
    12: "det_elev",
    13: "iso_grav_anom",
    15: "depth_to_base_surf",
    16: "ieq_n100a15",
    17: "cond_surf",
    18: "iso_grav_anom_hg",
    19: "det_elev_slope",
}


def _robust_z_fp(arr_fp: np.ndarray) -> np.ndarray:
    x = np.nan_to_num(np.asarray(arr_fp, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    sample = x[::23] if x.size > 100 else x
    q05, med, q95 = (float(v) for v in np.percentile(sample, [5.0, 50.0, 95.0]))
    scale = max((q95 - q05) / 3.2897, 1e-6)
    return np.clip((x - np.float32(med)) / np.float32(scale), -6.0, 6.0).astype(np.float32)


def _hessian_trough_2d(arr: np.ndarray, sigma: float) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32)
    gxx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 2), mode="nearest")
    gyy = ndi.gaussian_filter(a, sigma=sigma, order=(2, 0), mode="nearest")
    gxy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 1), mode="nearest")
    tr = gxx + gyy
    rad = np.hypot(gxx - gyy, 2.0 * gxy)
    return np.maximum(0.0, 0.5 * (tr + rad)).astype(np.float32)


def _hessian_crest_2d(arr: np.ndarray, sigma: float) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32)
    gxx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 2), mode="nearest")
    gyy = ndi.gaussian_filter(a, sigma=sigma, order=(2, 0), mode="nearest")
    gxy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 1), mode="nearest")
    tr = gxx + gyy
    rad = np.hypot(gxx - gyy, 2.0 * gxy)
    return np.maximum(0.0, 0.5 * (-tr + rad)).astype(np.float32)


def build_or_load_gcsd_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict]:
    """Build or reload disk-backed ``(N_fp, 12)`` float32 memmap of label-blind GCSD features."""
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    n_cols = len(GCSD_FEATURES)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / "x_gcsd_12ch_v1.dat"
    meta_path = cache_dir / "x_gcsd_12ch_v1.json"

    ext = root / "data/external"
    req_files = {
        "training_features.tif": root / "data/training_features.tif",
        "geodawn_dem_a2_100m.tif": root / "data/geodawn_dem_a2_100m.tif",
        "gdr_wellspring_in_footprint.csv": ext / "gdr_wellspring_in_footprint.csv",
        "2m_temperature_probe_INGENIOUS_regional_data.zip": ext / "2m_temperature_probe_INGENIOUS_regional_data.zip",
        "paleo_geothermal_regional.zip": ext / "paleo_geothermal_regional.zip",
        "lidar_scarp_features_u8.tif": ext / "lidar_scarp_features_u8.tif",
        "gdr_volcanic_vents_in_footprint.csv": ext / "gdr_volcanic_vents_in_footprint.csv",
    }
    hashes = {
        k: (
            hashlib.sha256(p.read_bytes()).hexdigest()
            if k not in ("training_features.tif", "geodawn_dem_a2_100m.tif")
            else f"pinned_{p.stat().st_size}"
        )
        for k, p in req_files.items()
    }

    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("schema") == GCSD_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(GCSD_FEATURES)
            and meta.get("hashes") == hashes
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    tmp_path = cache_dir / "x_gcsd_12ch_v1.tmp"
    mm = np.memmap(tmp_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    shape = grid.shape
    inv_tf = ~grid.transform

    # --- 1. Geothermometer Discordance & Flash/Conductive Cooling Surplus (Cols 0, 1, 2)
    flash_r, flash_c, flash_w = [], [], []
    diseq_r, diseq_c, diseq_w = [], [], []
    with req_files["gdr_wellspring_in_footprint.csv"].open("r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                rr, cc = int(float(r["row"])), int(float(r["col"]))
            except (KeyError, ValueError):
                continue

            def _parse_temp(key: str) -> float:
                raw = r.get(key, "")
                if raw in ("", "nan", "NaN", "None"):
                    return float("nan")
                try:
                    val = float(raw)
                    return val if (-20.0 < val < 450.0) else float("nan")
                except ValueError:
                    return float("nan")

            t_surf = _parse_temp("temp_c")
            t_qtz = _parse_temp("geothermquartz_c")
            t_chalc = _parse_temp("geothermchalc_c")
            t_cat = _parse_temp("geothermcat_c")

            deep_candidates = [v for v in (t_qtz, t_cat) if math.isfinite(v)]
            if deep_candidates:
                t_deep = max(deep_candidates)
                t_ref = t_surf if math.isfinite(t_surf) else 18.0
                surplus = max(t_deep - t_ref - 35.0, 0.0)
                if surplus > 0.0:
                    flash_r.append(rr)
                    flash_c.append(cc)
                    flash_w.append(surplus)

            dq = 0.0
            if math.isfinite(t_qtz) and math.isfinite(t_chalc):
                dq += max(t_qtz - t_chalc - 24.0, 0.0)
            if math.isfinite(t_cat) and math.isfinite(t_qtz):
                dq += 0.6 * min(abs(t_cat - t_qtz), 90.0)
            if dq > 0.0:
                diseq_r.append(rr)
                diseq_c.append(cc)
                diseq_w.append(dq)

    flash_2d = np.log1p(
        physics._splat_points(
            shape,
            np.asarray(flash_r, np.int32),
            np.asarray(flash_c, np.int32),
            np.asarray(flash_w, np.float32),
            sigma_px=12.0,
            normalize_density=True,
        )
    )
    diseq_2d = np.log1p(
        physics._splat_points(
            shape,
            np.asarray(diseq_r, np.int32),
            np.asarray(diseq_c, np.int32),
            np.asarray(diseq_w, np.float32),
            sigma_px=14.0,
            normalize_density=True,
        )
    )
    mm[:, 0] = _robust_z_fp(flash_2d[ys, xs])
    mm[:, 1] = _robust_z_fp(diseq_2d[ys, xs])

    # Include 2m temperature probe and paleo-sinter in the up-dip feeder back-projection
    with zipfile.ZipFile(req_files["2m_temperature_probe_INGENIOUS_regional_data.zip"]) as z:
        dbf_rows = physics._read_dbf_records(
            z.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
        )
    plons, plats, pdabs = [], [], []
    for r in dbf_rows:
        try:
            lon, lat = float(r["LongDegree"]), float(r["LatDegreeN"])
            dab, t2m = float(r["F2mDAB"]), float(r["T2m"])
        except (KeyError, ValueError):
            continue
        if -125.0 < lon < -110.0 and 34.0 < lat < 44.0 and (dab != 0.0 or t2m > 0.0):
            plons.append(lon)
            plats.append(lat)
            pdabs.append(max(dab, 0.0) + 0.20 * max(t2m - 19.0, 0.0))
    px_u, py_u = crs_transform("EPSG:4269", grid.crs, plons, plats)
    pcols, prows = inv_tf * (np.asarray(px_u), np.asarray(py_u))
    probe_2d = physics._splat_points(
        shape, np.floor(prows), np.floor(pcols), np.asarray(pdabs, np.float32), sigma_px=8.0, normalize_density=True
    )

    with zipfile.ZipFile(req_files["paleo_geothermal_regional.zip"]) as z:
        p_csv = list(csv.DictReader(io.StringIO(z.read("Paleo_geothermal_final.csv").decode("utf-8-sig", "replace"))))
    slons, slats, swts = [], [], []
    for r in p_csv:
        try:
            lon, lat = float(r["Long_deg_NAD83"]), float(r["Lat_deg_NAD83"])
        except (KeyError, ValueError):
            continue
        dt = (r.get("Deposit_type") or "").lower()
        swts.append(2.2 if ("sinter" in dt or "silic" in dt) else (1.5 if "travertine" in dt else 1.0))
        slons.append(lon)
        slats.append(lat)
    sx_u, sy_u = crs_transform("EPSG:4269", grid.crs, slons, slats)
    scols, srows = inv_tf * (np.asarray(sx_u), np.asarray(sy_u))
    sinter_2d = np.log1p(
        25.0 * physics._splat_points(shape, np.floor(srows), np.floor(scols), np.asarray(swts, np.float32), sigma_px=10.0)
    )

    hydro_plume_2d = (0.40 * flash_2d + 0.35 * diseq_2d + 0.35 * probe_2d + 0.50 * sinter_2d).astype(np.float32)
    del flash_2d, diseq_2d, probe_2d, sinter_2d
    gc.collect()

    # --- 2. Read verified 19-band competition layers and verify tags
    with rasterio.open(req_files["training_features.tif"]) as src:
        if (src.height, src.width) != shape:
            raise ValueError("training_features.tif grid mismatch")
        for b_idx, want_name in EXPECTED_BANDS.items():
            got_name = src.tags(b_idx).get("band_name", "")
            if got_name != want_name:
                raise ValueError(f"Band {b_idx} mismatch: expected {want_name!r}, got {got_name!r}")

        rtp_2d = edge.clean_band(src.read(2), fp)[0]
        tmi_hg_fp = np.maximum(edge.clean_band(src.read(3), fp)[0][ys, xs], 0.0)
        tc_fp = edge.clean_band(src.read(6), fp)[0][ys, xs]
        shear_fp = np.maximum(edge.clean_band(src.read(7), fp)[0][ys, xs], 0.0)
        dilat_fp = edge.clean_band(src.read(8), fp)[0][ys, xs]
        tmi_vg_fp = edge.clean_band(src.read(9), fp)[0][ys, xs]
        deq_fp = edge.clean_band(src.read(10), fp)[0][ys, xs]
        grav_vg_fp = edge.clean_band(src.read(11), fp)[0][ys, xs]
        det_elev_2d = edge.clean_band(src.read(12), fp)[0]
        iso_grav_2d = edge.clean_band(src.read(13), fp)[0]
        zbase_2d = np.maximum(edge.clean_band(src.read(15), fp)[0], 0.0)
        ieq_fp = np.maximum(edge.clean_band(src.read(16), fp)[0][ys, xs], 0.0)
        cond_2d = np.maximum(edge.clean_band(src.read(17), fp)[0], 0.0)
        det_slope_fp = np.maximum(edge.clean_band(src.read(19), fp)[0][ys, xs], 0.0)

    # Up-dip & up-slope feeder coupling onto basement steps (Col 2)
    zgy, zgx, zmag = physics._grad_f32(zbase_2d, 3.0)
    znorm = zmag[ys, xs] + np.float32(1e-5)
    # +grad(zbase) points from shallow bedrock toward deeper basin fill (down-dip);
    # therefore at a range-front/piedmont fault trace (y, x), the basinward thermal plume sits at (+uy*s, +ux*s).
    uy_dip = (zgy[ys, xs] / znorm).astype(np.float32)
    ux_dip = (zgx[ys, xs] / znorm).astype(np.float32)
    plume_down6 = physics._bilinear_at_fp(hydro_plume_2d, ys, xs, 6.0 * uy_dip, 6.0 * ux_dip)
    plume_down14 = physics._bilinear_at_fp(hydro_plume_2d, ys, xs, 14.0 * uy_dip, 14.0 * ux_dip)
    plume_here = hydro_plume_2d[ys, xs]
    zstep_gate = np.log1p(zmag[ys, xs] / 8.0).astype(np.float32)
    mm[:, 2] = _robust_z_fp(zstep_gate * (0.30 * plume_here + 0.40 * plume_down6 + 0.30 * plume_down14))
    del hydro_plume_2d, uy_dip, ux_dip, plume_down6, plume_down14, plume_here, zstep_gate

    # --- 3. Elevation- & Playa-Detrended Electrical Conductivity Residual & Clay-Demag Concordance (Cols 3, 4)
    cond_log_2d = np.log1p(cond_2d).astype(np.float32)
    del cond_2d
    cond_local_2d = ndi.gaussian_filter(cond_log_2d, sigma=1.5, mode="nearest")
    cond_reg_2d = ndi.gaussian_filter(cond_log_2d, sigma=18.0, mode="nearest")
    slp_med = max(float(np.median(det_slope_fp[::17])), 1e-4)
    playa_flat_fp = (np.exp(-det_slope_fp / (0.35 * slp_med)) * np.exp(-np.maximum(det_elev_2d[ys, xs], 0.0) / 25.0)).astype(np.float32)
    cond_resid_fp = (cond_local_2d[ys, xs] - cond_reg_2d[ys, xs]) * (1.0 - 0.80 * playa_flat_fp)
    mm[:, 3] = _robust_z_fp(cond_resid_fp)
    del cond_local_2d, cond_reg_2d, cond_resid_fp

    _, _, cond_grad_2d = physics._grad_f32(cond_log_2d, 2.0)
    rtp_trough_2d = _hessian_trough_2d(rtp_2d, sigma=2.5)
    mm[:, 4] = _robust_z_fp(cond_grad_2d[ys, xs] * np.log1p(rtp_trough_2d[ys, xs]) * (1.0 - 0.70 * playa_flat_fp))
    del cond_grad_2d, rtp_trough_2d

    # --- 4. Sentinel-Cleaned Microseismic Density x Transtensional Shear-Dilatation Coupling (Col 5)
    # Mask fill values (~4.96e6) in deq_n100a15 (IR-88-82)
    deq_valid = (deq_fp >= 0.0) & (deq_fp < 1.2e5)
    seis_prox = np.where(deq_valid, np.exp(-np.clip(deq_fp, 0.0, 1.2e5) / 15000.0), 0.0).astype(np.float32)
    seis_energy = (seis_prox + 0.35 * np.log1p(ieq_fp / 50.0)).astype(np.float32)
    dil_iqr = max(float(np.percentile(dilat_fp[::19], 75) - np.percentile(dilat_fp[::19], 25)), 1e-5)
    dil_med = float(np.median(dilat_fp[::19]))
    transtens = np.log1p(shear_fp) * (1.0 / (1.0 + np.exp(-np.clip((dilat_fp - dil_med) / dil_iqr, -8.0, 8.0))))
    mm[:, 5] = _robust_z_fp(seis_energy * transtens)
    del deq_fp, ieq_fp, deq_valid, seis_prox, seis_energy, shear_fp, dilat_fp, transtens

    # --- 5. 4-Modality Spin-2 Axial Strike Coherence & Gravity-Basement Admittance (Cols 6, 7)
    ggy, ggx, gmag = physics._grad_f32(iso_grav_2d, 3.0)
    rgy, rgx, rmag = physics._grad_f32(rtp_2d, 3.0)
    egy, egx, emag = physics._grad_f32(det_elev_2d, 3.0)
    del rtp_2d, det_elev_2d

    c2_sum = np.zeros(n_fp, dtype=np.float32)
    s2_sum = np.zeros(n_fp, dtype=np.float32)
    w_sum = np.zeros(n_fp, dtype=np.float32)
    for gy_m, gx_m, mag_m in ((ggy, ggx, gmag), (rgy, rgx, rmag), (zgy, zgx, zmag), (egy, egx, emag)):
        gy_f = gy_m[ys, xs]
        gx_f = gx_m[ys, xs]
        m2 = gy_f * gy_f + gx_f * gx_f + np.float32(1e-10)
        # Double-angle unit vector of strike (normal to gradient has same spin-2 up to sign)
        c2 = (gx_f * gx_f - gy_f * gy_f) / m2
        s2 = (2.0 * gx_f * gy_f) / m2
        med_m = max(float(np.median(mag_m[ys, xs][::29])), 1e-5)
        wm = np.tanh(mag_m[ys, xs] / (1.5 * med_m)).astype(np.float32)
        c2_sum += wm * c2
        s2_sum += wm * s2
        w_sum += wm + np.float32(1e-5)
    del rgy, rgx, rmag, egy, egx, emag

    spin2_coh = np.hypot(c2_sum, s2_sum) / w_sum
    mm[:, 6] = _robust_z_fp(spin2_coh)

    # Crustal reference strike angle from gravity + basement depth
    theta_crustal = (0.5 * np.arctan2(s2_sum, c2_sum + np.float32(1e-8))).astype(np.float32)
    del c2_sum, s2_sum, w_sum, spin2_coh

    # Gravity-Basement cross-gradient admittance (hanging-wall basin low = -grad(iso_grav) aligned with +grad(zbase))
    cos_gz = (-ggy[ys, xs] * zgy[ys, xs] - ggx[ys, xs] * zgx[ys, xs]) / (
        gmag[ys, xs] * zmag[ys, xs] + np.float32(1e-6)
    )
    admittance = cos_gz * np.log1p(gmag[ys, xs]) * np.log1p(zmag[ys, xs] / 10.0) * np.tanh( np.abs(grav_vg_fp) / (float(np.median(np.abs(grav_vg_fp[::23]))) + 1e-5) )
    mm[:, 7] = _robust_z_fp(admittance)
    del ggy, ggx, gmag, zgy, zgx, zmag, cos_gz, admittance, grav_vg_fp, iso_grav_2d
    gc.collect()

    # --- 6. Salem Tilt-Derivative Contact Sharpness (Col 8)
    tc_med = float(np.median(tc_fp[::19]))
    tc_iqr = max(float(np.percentile(tc_fp[::19], 75) - np.percentile(tc_fp[::19], 25)), 1e-5)
    z_tc = (tc_fp - tc_med) / tc_iqr
    tilt_contact = np.exp(-0.5 * z_tc * z_tc) * np.log1p(np.abs(tmi_vg_fp)) * np.log1p(tmi_hg_fp)
    mm[:, 8] = _robust_z_fp(tilt_contact)
    del tc_fp, tmi_vg_fp, tmi_hg_fp, z_tc, tilt_contact

    # --- 7. Piedmont Bajada Hinge Asymmetry & 1 m LiDAR Multi-Modal Strike Alignment (Cols 9, 10)
    with rasterio.open(req_files["geodawn_dem_a2_100m.tif"]) as ds:
        dem_100m = edge.clean_band(ds.read(1), fp)[0][ys, xs]
    shore_pen_fp = np.clip(
        np.exp(-0.5 * ((dem_100m - 1330.0) / 22.0) ** 2) + np.exp(-0.5 * ((dem_100m - 1555.0) / 22.0) ** 2),
        0.0,
        1.0,
    ).astype(np.float32)
    del dem_100m

    with rasterio.open(req_files["lidar_scarp_features_u8.tif"]) as ds:
        lapneg = ds.read(4)[ys, xs].astype(np.float32)
        lappos = ds.read(5)[ys, xs].astype(np.float32)
        cross_m = ds.read(8)[ys, xs].astype(np.float32)
        relief_l = ds.read(9)[ys, xs].astype(np.float32)
        coh100 = (ds.read(10)[ys, xs].astype(np.float32)) / 255.0
        strike_u8 = ds.read(11)[ys, xs].astype(np.float32)
        lv = ds.read(12)[ys, xs] > 0

    zbase_fp = zbase_2d[ys, xs]
    del zbase_2d
    bajada_gate = np.exp(-(((zbase_fp - 320.0) / 360.0) ** 2)).astype(np.float32)
    lap_dipole = np.where(lv, np.abs(lapneg - lappos) / (lapneg + lappos + 6.0), 0.0).astype(np.float32)
    bajada_hinge = bajada_gate * (0.60 * lap_dipole + 0.40 * np.exp(-relief_l / 110.0) * coh100) * (1.0 - 0.80 * shore_pen_fp)
    mm[:, 9] = _robust_z_fp(bajada_hinge)

    # LiDAR strike azimuth in [0, pi) vs crustal strike azimuth
    theta_lid = ((strike_u8 - 1.0) / 254.0 * math.pi).astype(np.float32)
    lid_align = np.where(
        lv & (strike_u8 > 0),
        coh100 * np.cos(2.0 * (theta_lid - theta_crustal)) * np.log1p(cross_m / 8.0),
        0.0,
    ).astype(np.float32)
    mm[:, 10] = _robust_z_fp(lid_align)
    del lapneg, lappos, cross_m, relief_l, coh100, strike_u8, lv, bajada_gate, lap_dipole, bajada_hinge, theta_lid, theta_crustal, lid_align

    # --- 8. Explicit Non-Fault Mimic Penalty Channel: Playa Brines + Circular Volcanic Edifices + Shorelines (Col 11)
    vrows, vcols = [], []
    with req_files["gdr_volcanic_vents_in_footprint.csv"].open("r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                vrows.append(int(float(r["row"])))
                vcols.append(int(float(r["col"])))
            except (KeyError, ValueError):
                continue
    volc_2d = physics._splat_points(
        shape, np.asarray(vrows, np.int32), np.asarray(vcols, np.int32), np.ones(len(vrows), np.float32), sigma_px=18.0
    )
    playa_brine_pen = playa_flat_fp * cond_log_2d[ys, xs] * np.tanh(zbase_fp / 400.0)
    mimic_pen = (0.50 * playa_brine_pen + 0.30 * shore_pen_fp + 0.20 * np.log1p(80.0 * volc_2d[ys, xs])).astype(np.float32)
    mm[:, 11] = _robust_z_fp(mimic_pen)
    del cond_log_2d, zbase_fp, volc_2d, playa_flat_fp, shore_pen_fp, playa_brine_pen, mimic_pen, det_slope_fp
    gc.collect()

    mm.flush()
    for j, cname in enumerate(GCSD_FEATURES):
        if not np.isfinite(mm[:, j]).all():
            raise AssertionError(f"Non-finite values in GCSD column {cname}")

    col_means = {
        cname: round(float(np.mean(mm[:, j], dtype=np.float64)), 6)
        for j, cname in enumerate(GCSD_FEATURES)
    }
    del mm
    tmp_path.replace(dat_path)

    meta = {
        "schema": GCSD_SCHEMA_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(GCSD_FEATURES),
        "hashes": hashes,
        "column_means": col_means,
        "verified_bands": {str(k): v for k, v in EXPECTED_BANDS.items()},
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta


def tri_poe_pool(
    p_base: np.ndarray,
    m_base: np.ndarray,
    p_gv: np.ndarray,
    m_gv: np.ndarray,
    p_gcsd: np.ndarray,
    m_gcsd: np.ndarray,
    *,
    w_base: float = 0.23,
    w_gv: float = 0.42,
    w_gcsd: float = 0.35,
    d_vis_act: np.ndarray | None = None,
    x_gcsd_act: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Reliability-Weighted Tri-Specialist Log-Odds Product-of-Experts pooling.

    Modulates the GCSD specialist weight `w_gcsd` by the label-blind seismic-coverage
    gate `seis_cov = sigmoid(6 * (gcsd_seismic_crit_shear + 0.45))` so that inside the
    NE sentinel fill zone of B10 (`deq_n100a15 ~ 4.96e6`, IR-88-82) the ensemble smoothly
    shifts weight toward the 68/91-channel TDKL+VESS specialist, while in the piedmont
    step-over corridor (`10 < d_vis <= 25 px`) hydrothermal upflow, clay-cap conductivity
    residual, gravity-basement admittance, and 4-modality spin-2 coherence amplify
    concealed feeder traces and suppress playa/volcanic mimics.
    """
    wb_f = np.float32(w_base)
    if x_gcsd_act is not None:
        seis_cov = (1.0 / (1.0 + np.exp(-6.0 * (x_gcsd_act[:, 5] + 0.45)))).astype(np.float32)
        wc_pix = (np.float32(w_gcsd) * (0.12 + 0.95 * seis_cov)).astype(np.float32)
        wg_pix = (1.0 - wb_f - wc_pix).astype(np.float32)
    else:
        wc_pix = np.float32(w_gcsd)
        wg_pix = np.float32(w_gv)

    p_lo = adhr._expit(wb_f * adhr._logit(p_base) + wg_pix * adhr._logit(p_gv) + wc_pix * adhr._logit(p_gcsd))
    m_lo = np.clip(
        adhr._expit(wb_f * adhr._logit(m_base) + wg_pix * adhr._logit(m_gv) + wc_pix * adhr._logit(m_gcsd)),
        p_lo,
        1.0,
    )
    if d_vis_act is not None:
        p_lin = (wb_f * p_base + wg_pix * p_gv + wc_pix * p_gcsd).astype(np.float32)
        m_lin = np.clip(wb_f * m_base + wg_pix * m_gv + wc_pix * m_gcsd, p_lin, 1.0).astype(np.float32)
        blind = d_vis_act > 22.0
        p_lo = np.where(blind, 1.18 * (0.35 * p_lo + 0.65 * p_lin), p_lo).astype(np.float32)
        m_lo = np.clip(np.where(blind, 1.18 * (0.35 * m_lo + 0.65 * m_lin), m_lo), p_lo, 1.0).astype(np.float32)
        if x_gcsd_act is not None:
            g_score = np.clip(
                0.28 * x_gcsd_act[:, 7]
                + 0.22 * x_gcsd_act[:, 3]
                + 0.20 * x_gcsd_act[:, 2]
                + 0.18 * x_gcsd_act[:, 6]
                - 0.22 * x_gcsd_act[:, 11],
                -2.0,
                2.0,
            )
            pied = (d_vis_act > 10.0) & (d_vis_act <= 25.0)
            mult = np.where(pied, np.exp(0.035 * g_score), 1.0).astype(np.float32)
            p_lo = np.clip(p_lo * mult, 1e-6, 1.0 - 1e-6).astype(np.float32)
            m_lo = np.clip(m_lo, p_lo, 1.0).astype(np.float32)
    return p_lo.astype(np.float32), m_lo.astype(np.float32)


def _fit_or_load_gcsd_fold_posteriors(
    grid,
    X_phys_mm: np.ndarray,
    X_tv_mm: np.ndarray,
    X_gcsd_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    cache_dir: Path,
    fold_tag: str,
    prod_oof_inputs: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    """Fit or load active-pixel posteriors for the 3 specialists on one holdout fold."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    cache_path = cache_dir / f"gcsd_posteriors_{fold_tag}_s{seed}_{GCSD_SCHEMA_VERSION}.npz"
    if cache_path.is_file():
        data = np.load(cache_path)
        if (
            "p_phys_68" in data.files
            and "p_full_91" in data.files
            and (prod_oof_inputs is None or "p_prod_phys_80" in data.files)
        ):
            return {k: data[k] for k in data.files}

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

    dom_phys_tr = train_regions[ys_fp, xs_fp]
    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]

    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])

    clfs_p44, regs_p44 = adhr._fit_dual_expectation_models(
        [X_phys_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 17, n_ensemble=1
    )
    p_phys_44, m_phys_44 = adhr._predict_dual_chunked(clfs_p44, regs_p44, [X_phys_mm], act_idx)
    del clfs_p44, regs_p44

    clfs_f67, regs_f67 = adhr._fit_dual_expectation_models(
        [X_phys_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 53, n_ensemble=1
    )
    p_full_67, m_full_67 = adhr._predict_dual_chunked(
        clfs_f67, regs_f67, [X_phys_mm, X_vis22_mm, d_over_w_fp], act_idx
    )
    del clfs_f67, regs_f67
    gc.collect()

    clfs_p68, regs_p68 = adhr._fit_dual_expectation_models(
        [X_phys_mm, X_tv_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 117, n_ensemble=1
    )
    p_phys_68, m_phys_68 = adhr._predict_dual_chunked(clfs_p68, regs_p68, [X_phys_mm, X_tv_mm], act_idx)
    del clfs_p68, regs_p68

    clfs_f91, regs_f91 = adhr._fit_dual_expectation_models(
        [X_phys_mm, X_tv_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 153, n_ensemble=1
    )
    p_full_91, m_full_91 = adhr._predict_dual_chunked(
        clfs_f91, regs_f91, [X_phys_mm, X_tv_mm, X_vis22_mm, d_over_w_fp], act_idx
    )
    del clfs_f91, regs_f91
    gc.collect()

    clfs_p80, regs_p80 = adhr._fit_dual_expectation_models(
        [X_phys_mm, X_tv_mm, X_gcsd_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 117, n_ensemble=1
    )
    p_phys_80, m_phys_80 = adhr._predict_dual_chunked(
        clfs_p80, regs_p80, [X_phys_mm, X_tv_mm, X_gcsd_mm], act_idx
    )
    if prod_oof_inputs is not None:
        _, _, _, prod_q_idx = prod_oof_inputs
        p_prod_phys_80, m_prod_phys_80 = adhr._predict_dual_chunked(
            clfs_p80, regs_p80, [X_phys_mm, X_tv_mm, X_gcsd_mm], prod_q_idx
        )
    del clfs_p80, regs_p80

    clfs_f103, regs_f103 = adhr._fit_dual_expectation_models(
        [X_phys_mm, X_tv_mm, X_gcsd_mm, X_vis22_mm, d_over_w_fp],
        dom_struct_tr,
        train_truth,
        fp,
        seed=seed + 153,
        n_ensemble=1,
    )
    p_full_103, m_full_103 = adhr._predict_dual_chunked(
        clfs_f103, regs_f103, [X_phys_mm, X_tv_mm, X_gcsd_mm, X_vis22_mm, d_over_w_fp], act_idx
    )
    if prod_oof_inputs is not None:
        X_vis_full_mm, d_full_fp, comp_len_full_fp, prod_q_idx = prod_oof_inputs
        dow_prod = (d_full_fp / np.maximum(wlaw.half_width(comp_len_full_fp), 1e-6)).astype(np.float32)
        p_prod_full_103, m_prod_full_103 = adhr._predict_dual_chunked(
            clfs_f103, regs_f103, [X_phys_mm, X_tv_mm, X_gcsd_mm, X_vis_full_mm, dow_prod], prod_q_idx
        )
        del dow_prod
    del clfs_f103, regs_f103, d_over_w_fp
    gc.collect()

    out = {
        "act_idx": act_idx.astype(np.int32),
        "p_phys_44": p_phys_44,
        "m_phys_44": m_phys_44,
        "p_full_67": p_full_67,
        "m_full_67": m_full_67,
        "p_phys_68": p_phys_68,
        "m_phys_68": m_phys_68,
        "p_full_91": p_full_91,
        "m_full_91": m_full_91,
        "p_phys_80": p_phys_80,
        "m_phys_80": m_phys_80,
        "p_full_103": p_full_103,
        "m_full_103": m_full_103,
    }
    if prod_oof_inputs is not None:
        out["prod_q_idx"] = prod_oof_inputs[3].astype(np.int32)
        out["p_prod_phys_80"] = p_prod_phys_80
        out["m_prod_phys_80"] = m_prod_phys_80
        out["p_prod_full_103"] = p_prod_full_103
        out["m_prod_full_103"] = m_prod_full_103
    np.savez(cache_path, **out)
    return out


def predict_gcsd_all_arms_fold(
    grid,
    X_phys_mm: np.ndarray,
    X_tv_mm: np.ndarray,
    X_gcsd_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    cache_dir: Path,
    fold_tag: str = "fold",
    prod_oof_inputs: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    """Evaluate Control 1 (`phys44_zero_cat`), Control 2 (`h88_adhr_incumbent`),
    Exp 01 (`gcsd_phys_only`), Exp 02 (`gcsd_single_103`), and Exp 03 (`h88_gcsd`) on one fold."""
    post = _fit_or_load_gcsd_fold_posteriors(
        grid,
        X_phys_mm,
        X_tv_mm,
        X_gcsd_mm,
        X_vis22_mm,
        d_vis_fp,
        comp_len_fp,
        visible,
        train_regions,
        train_truth,
        test_region,
        seed,
        cache_dir,
        fold_tag,
        prod_oof_inputs=prod_oof_inputs,
    )
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = post["act_idx"]
    d_vis_act = d_vis_fp[act_idx]
    x_gcsd_act = np.asarray(X_gcsd_mm[act_idx], dtype=np.float32)

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    p_phys_44, m_phys_44 = post["p_phys_44"], post["m_phys_44"]
    p_full_67, m_full_67 = post["p_full_67"], post["m_full_67"]
    p_phys_68, m_phys_68 = post["p_phys_68"], post["m_phys_68"]
    p_full_91, m_full_91 = post["p_full_91"], post["m_full_91"]
    p_phys_80, m_phys_80 = post["p_phys_80"], post["m_phys_80"]
    p_full_103, m_full_103 = post["p_full_103"], post["m_full_103"]

    # Reliability-Weighted Tri-Specialist Log-Odds PoE pooling
    p_phys_poe, m_phys_poe = tri_poe_pool(
        p_phys_44,
        m_phys_44,
        p_phys_68,
        m_phys_68,
        p_phys_80,
        m_phys_80,
        w_base=0.23,
        w_gv=0.42,
        w_gcsd=0.35,
        d_vis_act=d_vis_act,
        x_gcsd_act=x_gcsd_act,
    )
    p_full_poe, m_full_poe = tri_poe_pool(
        p_full_67,
        m_full_67,
        p_full_91,
        m_full_91,
        p_full_103,
        m_full_103,
        w_base=0.23,
        w_gv=0.42,
        w_gcsd=0.35,
        d_vis_act=d_vis_act,
        x_gcsd_act=x_gcsd_act,
    )

    # Control 1: phys44_zero_cat
    scale_c1 = float(k_est) / max(float(p_phys_44.sum()), 1e-6)
    p_c1 = np.clip(p_phys_44 * np.float32(scale_c1), 0.0, 1.0).astype(np.float32)
    m_c1 = np.clip(m_phys_44 * np.float32(hid_ratio), p_c1, 1.0).astype(np.float32)
    p_c1_grid = adhr.scatter_fp(p_c1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_c1_grid = adhr.scatter_fp(m_c1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_c1 = emit.dinkelbach_allocate(
        p_c1_grid, m_c1_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # Control 2: h88_adhr_incumbent
    p_inc, m_inc = adhr._fuse_log_odds(p_full_67, m_full_67, p_phys_44, m_phys_44, k_est, beta_phys=0.35)
    p_inc_grid = adhr.scatter_fp(p_inc, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_inc_grid = adhr.scatter_fp(m_inc, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_inc = emit.dinkelbach_allocate(
        p_inc_grid, m_inc_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # Exp 01: gcsd_phys_only (80-ch zero-catalogue PoE specialist)
    scale_e1 = float(k_est) / max(float(p_phys_poe.sum()), 1e-6)
    p_e1 = np.clip(p_phys_poe * np.float32(scale_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_phys_poe * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)
    p_e1_grid = adhr.scatter_fp(p_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e1_grid = adhr.scatter_fp(m_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_e1 = emit.dinkelbach_allocate(
        p_e1_grid, m_e1_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # Exp 02: gcsd_single_103 (single 80/103-ch combined GCSD model + completeness fusion)
    p_s103, m_s103 = adhr._fuse_log_odds(p_full_103, m_full_103, p_phys_80, m_phys_80, k_est, beta_phys=0.35)
    p_s103_grid = adhr.scatter_fp(p_s103, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_s103_grid = adhr.scatter_fp(m_s103, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_s103 = emit.dinkelbach_allocate(
        p_s103_grid, m_s103_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # Exp 03: h88_gcsd (Log-Odds PoE Specialist Ensemble + Bayesian completeness fusion)
    p_gcsd, m_gcsd = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_est, beta_phys=0.35)
    p_gcsd_grid = adhr.scatter_fp(p_gcsd, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_gcsd_grid = adhr.scatter_fp(m_gcsd, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_gcsd = emit.dinkelbach_allocate(
        p_gcsd_grid, m_gcsd_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    return {
        "phys44_zero_cat": (
            alloc_c1.emitted.astype(np.float32),
            p_c1_grid,
            {"n_dots": int(alloc_c1.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_c1.surrogate_dti)},
        ),
        "h88_adhr_incumbent": (
            alloc_inc.emitted.astype(np.float32),
            p_inc_grid,
            {"n_dots": int(alloc_inc.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_inc.surrogate_dti)},
        ),
        "gcsd_phys_only": (
            alloc_e1.emitted.astype(np.float32),
            p_e1_grid,
            {"n_dots": int(alloc_e1.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_e1.surrogate_dti)},
        ),
        "gcsd_single_103": (
            alloc_s103.emitted.astype(np.float32),
            p_s103_grid,
            {"n_dots": int(alloc_s103.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_s103.surrogate_dti)},
        ),
        "h88_gcsd": (
            alloc_gcsd.emitted.astype(np.float32),
            p_gcsd_grid,
            {"n_dots": int(alloc_gcsd.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_gcsd.surrogate_dti)},
        ),
    }


def fit_and_emit_production_gcsd(
    grid,
    X_phys_mm: np.ndarray,
    X_tv_mm: np.ndarray,
    X_gcsd_mm: np.ndarray,
    folds_q4: list[dict],
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
    *,
    seed: int = 8824,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """4-Quadrant Out-Of-Fold (`OOF`) cross-fitted GCSD surface + Three-Stratum
    Hydrothermal-Axial Crest Dinkelbach Allocator.

    Resolves IR-88-63 (no in-sample full-catalogue memorization) and IR-88-112
    (eliminates near-ribbon 3-px dot crowding against H88-TDKL, H88-VESS, GTHC-88,
    and QTSK-88 while preserving H33-parity basin fingerprint share_gt25 >= 0.40).
    """
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    n_fp = int(ys_fp.size)

    X_vis_full, d_full_fp, comp_len_full_fp = adhr.compute_visible_struct_fp(
        grid, full_cat, sense_src, scarp_fields, cache_dir, tag="prod_fullcat"
    )
    # Enforce > 3.0 px (> 300 m) off-catalogue collar so 0 dots sit inside existing_faults' 300 m kernel
    act_mask_fp = d_full_fp > 3.0
    act_idx = np.flatnonzero(act_mask_fp)
    d_act = d_full_fp[act_idx]
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]

    oof_cache = cache_dir / f"gcsd_prod_oof_s{seed}_{GCSD_SCHEMA_VERSION}.npz"
    q_tags = [("seed21_f0_NW", 210), ("seed21_f1_NE", 211), ("seed21_f2_SW", 212), ("seed21_f3_SE", 213)]
    q_files = [cache_dir / f"gcsd_posteriors_{qt}_s{qs}_{GCSD_SCHEMA_VERSION}.npz" for qt, qs in q_tags]
    if oof_cache.is_file():
        zd = np.load(oof_cache)
        p_phys_oof = zd["p_phys_oof"]
        m_phys_oof = zd["m_phys_oof"]
        p_struct_oof = zd["p_struct_oof"]
        m_struct_oof = zd["m_struct_oof"]
    elif all(qf.is_file() for qf in q_files):
        p_phys_fp = np.zeros(n_fp, dtype=np.float32)
        m_phys_fp = np.zeros(n_fp, dtype=np.float32)
        p_struct_fp = np.zeros(n_fp, dtype=np.float32)
        m_struct_fp = np.zeros(n_fp, dtype=np.float32)
        for qf in q_files:
            qd = np.load(qf)
            if "prod_q_idx" not in qd.files:
                break
            q_idx_arr = qd["prod_q_idx"]
            p_phys_fp[q_idx_arr] = qd["p_prod_phys_80"]
            m_phys_fp[q_idx_arr] = qd["m_prod_phys_80"]
            p_struct_fp[q_idx_arr] = qd["p_prod_full_103"]
            m_struct_fp[q_idx_arr] = qd["m_prod_full_103"]
        p_phys_oof = p_phys_fp[act_idx]
        m_phys_oof = m_phys_fp[act_idx]
        p_struct_oof = p_struct_fp[act_idx]
        m_struct_oof = m_struct_fp[act_idx]
        del p_phys_fp, m_phys_fp, p_struct_fp, m_struct_fp
        np.savez_compressed(
            oof_cache,
            p_phys_oof=p_phys_oof,
            m_phys_oof=m_phys_oof,
            p_struct_oof=p_struct_oof,
            m_struct_oof=m_struct_oof,
        )
    else:
        # 1. 4-Quadrant Out-Of-Fold cross-fitting of the 80-channel zero-catalogue physical specialist
        p_phys_oof = np.zeros(act_idx.size, dtype=np.float32)
        m_phys_oof = np.zeros(act_idx.size, dtype=np.float32)
        covered = np.zeros(act_idx.size, dtype=bool)
        phys_sources = [X_phys_mm, X_tv_mm, X_gcsd_mm]

        for q_idx, f_q in enumerate(folds_q4):
            train_dom_q = (~f_q["region"])[ys_fp, xs_fp]
            train_pos_q = full_cat & (~f_q["region"])
            c_q, r_q = adhr._fit_dual_expectation_models(
                phys_sources, train_dom_q, train_pos_q, fp, seed=seed + 31 * q_idx, n_ensemble=1
            )
            mask_q = f_q["region"][ay, ax]
            if q_idx == len(folds_q4) - 1:
                mask_q = mask_q | (~covered)
            covered |= mask_q
            pq, mq = adhr._predict_dual_chunked(c_q, r_q, phys_sources, act_idx[mask_q])
            p_phys_oof[mask_q] = pq
            m_phys_oof[mask_q] = mq
            del c_q, r_q, pq, mq
            gc.collect()

        # 2. 4-Quadrant Out-Of-Fold structural + GCSD specialist across the 4 folds of seed 20
        vis_s = folds_q4[0]["visible"]
        X_vis_s, d_s_fp, comp_len_s_fp = adhr.compute_visible_struct_fp(
            grid, vis_s, sense_src, scarp_fields, cache_dir, tag="seed20_f0_NW"
        )
        reg_all = np.zeros(grid.shape, dtype=bool)
        tr_all = np.zeros(grid.shape, dtype=bool)
        for f_q in folds_q4:
            reg_all |= f_q["region"]
            tr_all |= f_q["truth"]

        p_struct_oof = np.zeros(act_idx.size, dtype=np.float32)
        m_struct_oof = np.zeros(act_idx.size, dtype=np.float32)
        covered_s = np.zeros(act_idx.size, dtype=bool)
        for q_idx, f_q in enumerate(folds_q4):
            tr_regions_q = reg_all & (~f_q["region"])
            tr_truth_q = tr_all & (~f_q["region"])
            wlaw_q = damagezone_envelope.fit_width_law(
                comp_len_s_fp, d_s_fp, tr_truth_q[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
            )
            dow_s_q = (d_s_fp / np.maximum(wlaw_q.half_width(comp_len_s_fp), 1e-6)).astype(np.float32)
            dom_s_q = (tr_regions_q & ~vis_s)[ys_fp, xs_fp]
            cs_q, rs_q = adhr._fit_dual_expectation_models(
                [X_phys_mm, X_tv_mm, X_gcsd_mm, X_vis_s, dow_s_q],
                dom_s_q,
                tr_truth_q,
                fp,
                seed=seed + 101 + 43 * q_idx,
                n_ensemble=1,
            )
            mask_q = f_q["region"][ay, ax]
            if q_idx == len(folds_q4) - 1:
                mask_q = mask_q | (~covered_s)
            covered_s |= mask_q
            dow_prod_q = (d_full_fp / np.maximum(wlaw_q.half_width(comp_len_full_fp), 1e-6)).astype(np.float32)
            pq, mq = adhr._predict_dual_chunked(
                cs_q,
                rs_q,
                [X_phys_mm, X_tv_mm, X_gcsd_mm, X_vis_full, dow_prod_q],
                act_idx[mask_q],
            )
            p_struct_oof[mask_q] = pq
            m_struct_oof[mask_q] = mq
            del cs_q, rs_q, dow_s_q, dow_prod_q, pq, mq
            gc.collect()
        del X_vis_s, d_s_fp, comp_len_s_fp
        np.savez_compressed(
            oof_cache,
            p_phys_oof=p_phys_oof,
            m_phys_oof=m_phys_oof,
            p_struct_oof=p_struct_oof,
            m_struct_oof=m_struct_oof,
        )

    del X_vis_full, comp_len_full_fp
    gc.collect()

    # Compute the intrinsic GCSD hydrothermal-upflow & multi-modal strike-coherence potential on active pixels
    gcsd_act = np.asarray(X_gcsd_mm[act_idx], dtype=np.float32)
    hydro_strike_score = (
        0.22 * gcsd_act[:, 0]   # qtz_flash_surplus
        + 0.18 * gcsd_act[:, 1] # geotherm_diseq
        + 0.22 * gcsd_act[:, 2] # updip_feeder_couple
        + 0.16 * gcsd_act[:, 3] # cond_elev_resid
        + 0.16 * gcsd_act[:, 4] # cond_demag_concord
        + 0.14 * gcsd_act[:, 5] # seismic_crit_shear
        + 0.20 * gcsd_act[:, 6] # multimodal_spin2_coh
        + 0.16 * gcsd_act[:, 7] # grav_zbase_admittance
        + 0.14 * gcsd_act[:, 8] # tilt_contact_sharpness
        + 0.14 * gcsd_act[:, 9] # bajada_hinge_asymmetry
        + 0.14 * gcsd_act[:, 10] # lidar_multimodal_strike
        - 0.25 * gcsd_act[:, 11] # mimic_playa_volc_pen
    ).astype(np.float32)
    del gcsd_act
    hs_2d = adhr.scatter_fp(hydro_strike_score, ay, ax, grid.shape)
    hs_crest_2d = _hessian_crest_2d(hs_2d, sigma=2.2)
    hs_gate_act = (1.0 / (1.0 + np.exp(-np.clip(_robust_z_fp(hydro_strike_score + 0.8 * hs_crest_2d[ay, ax]), -6.0, 6.0)))).astype(np.float32)
    del hydro_strike_score, hs_2d, hs_crest_2d

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(
        p_struct_oof, m_struct_oof, p_phys_oof, m_phys_oof, k_prod, beta_phys=0.45, pi_unmapped=0.60
    )

    # Modulate with GCSD hydrothermal-strike gate so the surface reflects the GCSD physical mechanism
    p_mod_phys = (p_phys_oof * (0.45 + 1.10 * hs_gate_act)).astype(np.float32)
    m_mod_phys = np.clip(m_phys_oof * (0.55 + 0.90 * hs_gate_act), p_mod_phys, 1.0).astype(np.float32)
    p_mod_fused = (p_fused * (0.50 + 1.00 * hs_gate_act)).astype(np.float32)
    m_mod_fused = np.clip(m_fused * (0.60 + 0.80 * hs_gate_act), p_mod_fused, 1.0).astype(np.float32)
    del p_fused, m_fused, p_phys_oof, m_phys_oof, p_struct_oof, m_struct_oof, hs_gate_act

    # Three-Stratum Hydrothermal-Axial Allocation (30,000 dots total at H33-parity spacing >= 2.85 px):
    #   Stratum 1 (relay: 3 < d_cat <= 10 px):   7,200 dots (24%)
    #   Stratum 2 (piedmont: 10 < d_cat <= 25 px): 9,300 dots (31%)
    #   Stratum 3 (blind basin: d_cat > 25 px): 13,500 dots (45%, share_gt25 = 0.45 >= 0.35)
    s1_sel = (d_act > 3.0) & (d_act <= 10.0)
    s2_sel = (d_act > 10.0) & (d_act <= 25.0)
    s3_sel = d_act > 25.0

    k_s1 = k_prod * 0.28
    k_s2 = k_prod * 0.32
    k_s3 = k_prod * 0.40

    def _norm_stratum(p_raw: np.ndarray, m_raw: np.ndarray, k_s: float) -> tuple[np.ndarray, np.ndarray]:
        sc = float(k_s) / max(float(p_raw.sum()), 1e-6)
        p_s = np.clip(p_raw * np.float32(sc), 0.0, 1.0).astype(np.float32)
        m_s = np.clip(m_raw * np.float32(min(max(sc, 0.85), 1.25)), p_s, 1.0).astype(np.float32)
        return p_s, m_s

    p_s1, m_s1 = _norm_stratum(0.65 * p_mod_fused[s1_sel] + 0.35 * p_mod_phys[s1_sel],
                               0.65 * m_mod_fused[s1_sel] + 0.35 * m_mod_phys[s1_sel], k_s1)
    p_s2, m_s2 = _norm_stratum(0.35 * p_mod_fused[s2_sel] + 0.65 * p_mod_phys[s2_sel],
                               0.35 * m_mod_fused[s2_sel] + 0.65 * m_mod_phys[s2_sel], k_s2)
    p_s3, m_s3 = _norm_stratum(0.15 * p_mod_fused[s3_sel] + 0.85 * p_mod_phys[s3_sel],
                               0.15 * m_mod_fused[s3_sel] + 0.85 * m_mod_phys[s3_sel], k_s3)

    p_comb = np.zeros_like(p_mod_fused)
    m_comb = np.zeros_like(m_mod_fused)
    p_comb[s1_sel], m_comb[s1_sel] = p_s1, m_s1
    p_comb[s2_sel], m_comb[s2_sel] = p_s2, m_s2
    p_comb[s3_sel], m_comb[s3_sel] = p_s3, m_s3
    del p_mod_fused, m_mod_fused, p_mod_phys, m_mod_phys, p_s1, m_s1, p_s2, m_s2, p_s3, m_s3

    p_grid = adhr.scatter_fp(p_comb, ay, ax, grid.shape)
    m_grid = adhr.scatter_fp(m_comb, ay, ax, grid.shape)
    del p_comb, m_comb
    gc.collect()

    allowed_s1 = np.zeros(grid.shape, dtype=bool)
    allowed_s1[ay[s1_sel], ax[s1_sel]] = True
    allowed_s2 = np.zeros(grid.shape, dtype=bool)
    allowed_s2[ay[s2_sel], ax[s2_sel]] = True
    allowed_s3 = np.zeros(grid.shape, dtype=bool)
    allowed_s3[ay[s3_sel], ax[s3_sel]] = True

    alloc_s1 = emit.dinkelbach_allocate(
        p_grid, m_grid, allowed_s1, budget=7_200, k_truth=k_s1, min_spacing_px=2.85, dinkelbach_iters=8
    )
    alloc_s2 = emit.dinkelbach_allocate(
        p_grid, m_grid, allowed_s2, budget=9_300, k_truth=k_s2, min_spacing_px=2.85, dinkelbach_iters=8
    )
    alloc_s3 = emit.dinkelbach_allocate(
        p_grid, m_grid, allowed_s3, budget=13_500, k_truth=k_s3, min_spacing_px=2.85, dinkelbach_iters=8
    )

    emitted = np.clip(alloc_s1.emitted + alloc_s2.emitted + alloc_s3.emitted, 0.0, 1.0).astype(np.float32)
    n_dots = int((emitted > 0).sum())
    n_s1 = int((alloc_s1.emitted > 0).sum())
    n_s2 = int((alloc_s2.emitted > 0).sum())
    n_s3 = int((alloc_s3.emitted > 0).sum())

    return emitted, p_grid, {
        "n_dots": n_dots,
        "n_relay_3_to_10px": n_s1,
        "n_piedmont_10_to_25px": n_s2,
        "n_blind_gt25px": n_s3,
        "share_gt25": float(n_s3 / max(n_dots, 1)),
        "share_gt10": float((n_s2 + n_s3) / max(n_dots, 1)),
        "share_le2": 0.0,
        "min_spacing_px": 2.85,
        "collar_px": 3.0,
        "oof_cross_fitted": True,
        "k_truth_est": float(k_prod),
    }
