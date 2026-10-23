"""Unified Geothermal Fault-Valve, 60-deg Up-Dip Advection & Self-Masked Relay Submodular Model (`H88-UGFV`).

Strictly honors:
  1. Zero modification to `vendor/gems57/*.py`.
  2. Memory discipline (`< 1.5 GiB` peak RSS on 3.8 GiB no-swap CPU hosts via disk-backed `float16` memmap).
  3. Zero data leakage:
     - Public fault labels (`bridge/existing_faults.tif`) are completely excluded from all 32 static channels (`Band 14` in `training_features.tif` is `tmi`).
     - `sgmc_faults_100m` and `gdr_qfaults_traces` are completely excluded.
     - `dist_known_fault_px` in external GDR CSVs is explicitly quarantined and never read.
     - Structural features (`anatomy.fold_geometry` + tip continuation beam + multi-strand excess)
       and slip sense (`trace_segments_utm11.csv`) are masked strictly to fold-visible traces
       (`visible`) and trained exclusively on nested whole-component self-masked splits inside `train_region`.
"""
from __future__ import annotations

import csv
import gc
import io
import json
import math
import struct
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from gems57 import anatomy, emit, grid as g57_grid, holdout, uniqueness

FORBIDDEN_EXTERNAL_COLUMNS = frozenset({"dist_known_fault_px"})
FORBIDDEN_EXTERNAL_FILES = frozenset({"sgmc_faults_100m.tif", "gdr_qfaults_traces.tif"})

UGFV_STATIC_NAMES: tuple[str, ...] = (
    # Group A: Core potential fields, true analytical Miller-Singh tilt & 60-deg up-dip advection (11)
    "rtp_z",
    "iso_grav_z",
    "basement_depth_km",
    "tmi_hg_log",
    "grav_slope_log",
    "grav_hg_abs",
    "mag_tilt",
    "mag_tilt_hgm",
    "grav_tilt_hgm",
    "coedge_joint",
    "updip_tilt_60deg",
    # Group B: Structural rollover, geodetic transtension & microseismic swarm valve (9)
    "det_elev_z",
    "scarp_slope_log",
    "basement_flexure",
    "strain_2ndinv_z",
    "transtension_valve",
    "seism_swarm_excess",
    "seism_grad_log",
    "mt_claycap_edge",
    "rad_tc_z",
    # Group C: USGS GeoDAWN alteration, 1-m LiDAR scarps, 10-m chi knickpoints & DOE GDR 1391 thermal (8)
    "mag_destruct_trough",
    "rad_k_th_local",
    "rad_u_th_redox",
    "lidar_scarp_norm",
    "lidar_cross_coh",
    "dem10_chi_knick",
    "gdr_probe2m_anom",
    "gdr_sinter_geotherm",
    # Group D: Explicit non-fault mimic deconfounders & subsurface-surface fault coupling (4)
    "deconf_flight_seam_ew",
    "deconf_lahontan_bench",
    "deconf_local_relief",
    "updip_lidar_coupled",
)

UGFV_STRUCT_NAMES: tuple[str, ...] = (
    "host_dist",
    "host_d_perp",
    "host_abs_d_par",
    "host_side",
    "host_log1p_len",
    "host_sin2th",
    "host_cos2th",
    "host_coherence",
    "host_density",
    "host_sin2th_d",
    "host_cos2th_d",
    "host_sense",
    "host_releasing",
    "vis_tip_dist_log",
    "vis_tip_beam",
    "vis_multihost_excess",
)

COT_60_DEG = float(1.0 / math.sqrt(3.0))  # 0.577350269...


def _clean_band(raw: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    x = np.asarray(raw, dtype=np.float32)
    bad = (~np.isfinite(x)) | (np.abs(x) > 1e8)
    valid = footprint & (~bad)
    med = float(np.median(x[valid])) if valid.any() else 0.0
    out = np.where(valid, x, med).astype(np.float32, copy=False)
    return out


def _robust_z(x: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    vals = x[footprint]
    med = float(np.median(vals))
    iqr = float(np.percentile(vals, 75.0) - np.percentile(vals, 25.0))
    scale = max(iqr / 1.3489795, float(np.std(vals)) * 0.5, 1e-6)
    z = (x - np.float32(med)) / np.float32(scale)
    return np.where(footprint, np.clip(np.nan_to_num(z, nan=0.0, posinf=32.0, neginf=-32.0), -32.0, 32.0), 0.0).astype(
        np.float32, copy=False
    )


def _grad_mag(x: np.ndarray, sigma: float) -> np.ndarray:
    gy = ndi.gaussian_filter(x, sigma=sigma, order=(1, 0), mode="nearest")
    gx = ndi.gaussian_filter(x, sigma=sigma, order=(0, 1), mode="nearest")
    return np.hypot(gy, gx).astype(np.float32, copy=False)


def _write_slot(mm: np.memmap, idx: int, arr: np.ndarray, footprint: np.ndarray) -> None:
    z = _robust_z(arr.astype(np.float32, copy=False), footprint)
    mm[:, idx] = z.ravel().astype(np.float16)


def parse_dbf_records(dbf_bytes: bytes) -> list[dict[str, str]]:
    """Pure-Python DBF reader (zero GDAL/fiona/pyshp dependency)."""
    num_records, header_len, record_len = struct.unpack("<IHH", dbf_bytes[4:12])
    fields: list[tuple[str, str, int]] = []
    pos = 32
    while pos < header_len - 1 and dbf_bytes[pos] != 0x0D:
        name = dbf_bytes[pos : pos + 11].split(b"\x00", 1)[0].decode("latin1").strip()
        ftype = chr(dbf_bytes[pos + 11])
        flen = dbf_bytes[pos + 16]
        fields.append((name, ftype, flen))
        pos += 32
    rows: list[dict[str, str]] = []
    offset = header_len
    for _ in range(num_records):
        rec = dbf_bytes[offset : offset + record_len]
        offset += record_len
        if not rec or rec[0:1] == b"*":
            continue
        cur = 1
        d: dict[str, str] = {}
        for name, _ft, flen in fields:
            d[name] = rec[cur : cur + flen].decode("latin1").strip()
            cur += flen
        rows.append(d)
    return rows


def _utm11_from_lonlat(lon_deg: np.ndarray, lat_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact WGS84/NAD83 Transverse Mercator projection to EPSG:32611 (UTM Zone 11N, meters)."""
    a = 6378137.0
    f = 1.0 / 298.257223563
    e2 = f * (2.0 - f)
    ep2 = e2 / (1.0 - e2)
    k0 = 0.9996
    lon0 = math.radians(-117.0)

    lat = np.deg2rad(lat_deg.astype(np.float64))
    lon = np.deg2rad(lon_deg.astype(np.float64))
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    tan_lat = np.tan(lat)

    N = a / np.sqrt(1.0 - e2 * sin_lat * sin_lat)
    T = tan_lat * tan_lat
    C = ep2 * cos_lat * cos_lat
    A = cos_lat * (lon - lon0)
    M = a * (
        (1.0 - e2 / 4.0 - 3.0 * e2**2 / 64.0 - 5.0 * e2**3 / 256.0) * lat
        - (3.0 * e2 / 8.0 + 3.0 * e2**2 / 32.0 + 45.0 * e2**3 / 1024.0) * np.sin(2.0 * lat)
        + (15.0 * e2**2 / 256.0 + 45.0 * e2**3 / 1024.0) * np.sin(4.0 * lat)
        - (35.0 * e2**3 / 3072.0) * np.sin(6.0 * lat)
    )
    easting = 500000.0 + k0 * N * (
        A + (1.0 - T + C) * A**3 / 6.0 + (5.0 - 18.0 * T + T**2 + 72.0 * C - 58.0 * ep2) * A**5 / 120.0
    )
    northing = k0 * (
        M
        + N
        * tan_lat
        * (A**2 / 2.0 + (5.0 - T + 9.0 * C + 4.0 * C**2) * A**4 / 24.0 + (61.0 - 58.0 * T + T**2 + 600.0 * C - 330.0 * ep2) * A**6 / 720.0)
    )
    return easting, northing


def build_gdr_geothermal_channels(
    ext_dir: Path, shape: tuple[int, int], transform: rasterio.Affine, footprint: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Rasterize verified DOE GDR 1391 2-m probes, paleogeothermal sinter/travertine, and springs.

    Explicitly enforces anti-leakage quarantine (`IR-88-11`): `dist_known_fault_px` is never read.
    """
    H, W = shape
    ox, oy = float(transform.c), float(transform.f)
    sx, sy = float(transform.a), float(-transform.e)

    # 1. 3,800-station 2-m temperature probe database (Coolbaugh et al., DOE GDR 1391)
    probe_pos = np.zeros(shape, dtype=np.float32)
    probe_cnt = np.zeros(shape, dtype=np.float32)
    zpath = ext_dir / "2m_temperature_probe_INGENIOUS_regional_data.zip"
    n_probes_in = 0
    with zipfile.ZipFile(zpath, "r") as zf:
        dbf_name = [n for n in zf.namelist() if n.lower().endswith(".dbf")][0]
        records = parse_dbf_records(zf.read(dbf_name))
    lons, lats, anoms = [], [], []
    for r in records:
        try:
            lo = float(r["LongDegree"])
            la = float(r["LatDegreeN"])
            dab = float(r["F2mDAB"])
            t2m = float(r["T2m"])
        except (KeyError, ValueError):
            continue
        if not (math.isfinite(lo) and math.isfinite(la)):
            continue
        val = max(dab, 0.0) if (math.isfinite(dab) and abs(dab) < 80.0) else max(t2m - 15.0, 0.0)
        lons.append(lo)
        lats.append(la)
        anoms.append(min(val, 40.0))
    if lons:
        ex, ny = _utm11_from_lonlat(np.asarray(lons), np.asarray(lats))
        cols = np.floor((ex - ox) / sx).astype(np.int32)
        rows = np.floor((oy - ny) / sy).astype(np.int32)
        ok = (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W)
        n_probes_in = int(ok.sum())
        np.add.at(probe_pos, (rows[ok], cols[ok]), np.asarray(anoms, dtype=np.float32)[ok])
        np.add.at(probe_cnt, (rows[ok], cols[ok]), 1.0)

    probe_field = (
        0.65 * ndi.gaussian_filter(probe_pos, sigma=6.0, mode="constant")
        + 0.35 * ndi.gaussian_filter(probe_pos, sigma=18.0, mode="constant")
    ) / (
        0.65 * ndi.gaussian_filter(probe_cnt, sigma=6.0, mode="constant")
        + 0.35 * ndi.gaussian_filter(probe_cnt, sigma=18.0, mode="constant")
        + 0.02
    )

    # 2. Paleogeothermal sinter/travertine/tufa vents (Ayling 2020, GDR 1391) + wells/springs + Quaternary vents
    paleo_imp = np.zeros(shape, dtype=np.float32)
    pzpath = ext_dir / "paleo_geothermal_regional.zip"
    n_paleo_in = 0
    with zipfile.ZipFile(pzpath, "r") as zf:
        csv_name = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
        txt = zf.read(csv_name).decode("utf-8-sig", errors="replace")
    plons, plats, pwts = [], [], []
    for row in csv.DictReader(io.StringIO(txt)):
        if any(k in FORBIDDEN_EXTERNAL_COLUMNS for k in row):
            pass  # Paleo CSV has no fault distance column; guard kept uniform
        try:
            lo = float(row["Long_deg_NAD83"])
            la = float(row["Lat_deg_NAD83"])
        except (KeyError, ValueError):
            continue
        dtype_s = row.get("Deposit_type", "").lower()
        w = 2.0 if ("sinter" in dtype_s or "travertine" in dtype_s) else 1.2
        plons.append(lo)
        plats.append(la)
        pwts.append(w)
    if plons:
        ex, ny = _utm11_from_lonlat(np.asarray(plons), np.asarray(plats))
        cols = np.floor((ex - ox) / sx).astype(np.int32)
        rows = np.floor((oy - ny) / sy).astype(np.int32)
        ok = (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W)
        n_paleo_in = int(ok.sum())
        np.add.at(paleo_imp, (rows[ok], cols[ok]), np.asarray(pwts, dtype=np.float32)[ok])

    # Wells/springs thermal + geothermometer excess (STRICTLY quarantine dist_known_fault_px!)
    ws_path = ext_dir / "gdr_wellspring_in_footprint.csv"
    n_ws_hot = 0
    blocked_cols_seen: set[str] = set()
    with ws_path.open(newline="") as f:
        reader = csv.DictReader(f)
        allowed_headers = [h for h in (reader.fieldnames or []) if h not in FORBIDDEN_EXTERNAL_COLUMNS]
        blocked_cols_seen.update(set(reader.fieldnames or ()) & FORBIDDEN_EXTERNAL_COLUMNS)
        assert "dist_known_fault_px" not in allowed_headers
        for raw_row in reader:
            row = {k: raw_row[k] for k in allowed_headers}
            try:
                rr = int(float(row["row"]))
                cc = int(float(row["col"]))
            except (KeyError, ValueError):
                continue
            if not (0 <= rr < H and 0 <= cc < W):
                continue
            temps = []
            for tk in ("temp_c", "qtz_c", "na_k_ca_c"):
                v = row.get(tk, "")
                if v:
                    try:
                        fv = float(v)
                        if math.isfinite(fv) and 25.0 < fv < 350.0:
                            temps.append(fv)
                    except ValueError:
                        pass
            if temps:
                n_ws_hot += 1
                paleo_imp[rr, cc] += np.float32(math.log1p(max(temps) - 25.0) * 0.5)

    # Quaternary volcanic vents (STRICTLY quarantine dist_known_fault_px!)
    vv_path = ext_dir / "gdr_volcanic_vents_in_footprint.csv"
    n_vents = 0
    with vv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        allowed_headers = [h for h in (reader.fieldnames or []) if h not in FORBIDDEN_EXTERNAL_COLUMNS]
        blocked_cols_seen.update(set(reader.fieldnames or ()) & FORBIDDEN_EXTERNAL_COLUMNS)
        assert "dist_known_fault_px" not in allowed_headers
        for raw_row in reader:
            row = {k: raw_row[k] for k in allowed_headers}
            try:
                rr = int(float(row["row"]))
                cc = int(float(row["col"]))
            except (KeyError, ValueError):
                continue
            if 0 <= rr < H and 0 <= cc < W:
                n_vents += 1
                paleo_imp[rr, cc] += np.float32(0.75)

    sinter_field = (
        0.60 * ndi.gaussian_filter(paleo_imp, sigma=4.5, mode="constant")
        + 0.40 * ndi.gaussian_filter(paleo_imp, sigma=14.0, mode="constant")
    ).astype(np.float32)

    meta = {
        "probes_in_grid": n_probes_in,
        "paleo_deposits_in_grid": n_paleo_in,
        "thermal_wells_springs_used": n_ws_hot,
        "volcanic_vents_used": n_vents,
        "quarantined_columns_blocked": sorted(blocked_cols_seen),
    }
    return probe_field.astype(np.float32), sinter_field, meta


def build_ugfv_cache(
    grid: g57_grid.Grid,
    features_tif: Path,
    ext_dir: Path,
    cache_dir: Path,
) -> tuple[np.memmap, dict]:
    """Stream 32 zero-catalogue static physics/geothermal channels into `float16` memmap."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    f16_path = cache_dir / "ugfv88-static-32ch.f16"
    meta_path = cache_dir / "ugfv88-static-32ch.json"
    n_cells = grid.height * grid.width
    n_ch = len(UGFV_STATIC_NAMES)

    if f16_path.is_file() and meta_path.is_file() and f16_path.stat().st_size == n_cells * n_ch * 2:
        meta = json.loads(meta_path.read_text())
        if meta.get("channel_names") == list(UGFV_STATIC_NAMES) and meta.get("version") == "ugfv88-v1":
            mm = np.memmap(f16_path, dtype=np.float16, mode="r", shape=(n_cells, n_ch))
            return mm, meta

    t0 = time.monotonic()
    fp = grid.footprint
    mm = np.memmap(f16_path, dtype=np.float16, mode="w+", shape=(n_cells, n_ch))

    with rasterio.open(features_tif) as src:
        expected_bands = [
            "mag_anom", "rtp", "tmi_hg", "geod_2ndinv", "iso_grav_anom_slope",
            "tc", "geod_shearrate", "geod_dilaterate", "tmi_vg", "deq_n100a15",
            "iso_grav_anom_vg", "det_elev", "iso_grav_anom", "tmi", "depth_to_base_surf",
            "ieq_n100a15", "cond_surf", "iso_grav_anom_hg", "det_elev_slope",
        ]
        actual_bands = [src.tags(b).get("band_name") for b in range(1, 20)]
        assert actual_bands == expected_bands, f"Unexpected band layout: {actual_bands}"

        mag_anom = _clean_band(src.read(1), fp)
        rtp = _clean_band(src.read(2), fp)
        tmi_hg = np.maximum(_clean_band(src.read(3), fp), 0.0)
        tmi_vg = _clean_band(src.read(9), fp)
        tmi = _clean_band(src.read(14), fp)
        grav_slope = np.maximum(_clean_band(src.read(5), fp), 0.0)
        grav_vg = _clean_band(src.read(11), fp)
        grav = _clean_band(src.read(13), fp)
        grav_hg_abs = np.abs(_clean_band(src.read(18), fp))
        zb = np.maximum(_clean_band(src.read(15), fp), 0.0)

        _write_slot(mm, 0, rtp, fp)
        _write_slot(mm, 1, grav, fp)
        _write_slot(mm, 2, zb * np.float32(0.001), fp)
        _write_slot(mm, 3, np.log1p(tmi_hg), fp)
        _write_slot(mm, 4, np.log1p(grav_slope * np.float32(100.0)), fp)
        _write_slot(mm, 5, np.log1p(grav_hg_abs * np.float32(100.0)), fp)

        mag_tilt = np.arctan2(tmi_vg, np.maximum(tmi_hg, np.float32(1e-3))).astype(np.float32)
        mag_tilt_hgm = _grad_mag(mag_tilt, 1.5)
        grav_tilt = np.arctan2(grav_vg * np.float32(1000.0), np.maximum(grav_slope * np.float32(10.0), np.float32(1e-4))).astype(np.float32)
        grav_tilt_hgm = _grad_mag(grav_tilt, 2.0)

        # Signed RTP / Gravity gradient alignment
        ry = ndi.gaussian_filter(rtp, 2.0, order=(1, 0), mode="nearest")
        rx = ndi.gaussian_filter(rtp, 2.0, order=(0, 1), mode="nearest")
        gy = ndi.gaussian_filter(grav, 2.0, order=(1, 0), mode="nearest")
        gx = ndi.gaussian_filter(grav, 2.0, order=(0, 1), mode="nearest")
        rn = np.hypot(ry, rx) + np.float32(1e-5)
        gn = np.hypot(gy, gx) + np.float32(1e-5)
        cos_rg = np.abs(ry * gy + rx * gx) / (rn * gn)
        coedge = np.sqrt(rn * gn) * cos_rg

        # 60-degree normal-fault up-dip advection of basement potential-field edges onto surface trace
        zby = ndi.gaussian_filter(zb, 4.0, order=(1, 0), mode="nearest")
        zbx = ndi.gaussian_filter(zb, 4.0, order=(0, 1), mode="nearest")
        zbn = np.hypot(zby, zbx) + np.float32(1e-4)
        shift_px = np.clip(zb * np.float32(COT_60_DEG / 100.0), 0.0, 12.0)
        joint_tilt_hgm = _robust_z(mag_tilt_hgm, fp) + _robust_z(grav_tilt_hgm, fp)
        yy, xx = np.indices(grid.shape, dtype=np.float32)
        sy_coord = np.clip(yy + shift_px * (zby / zbn), 0.0, grid.height - 1.0)
        sx_coord = np.clip(xx + shift_px * (zbx / zbn), 0.0, grid.width - 1.0)
        updip_tilt = ndi.map_coordinates(joint_tilt_hgm, [sy_coord, sx_coord], order=1, mode="nearest").astype(np.float32)

        _write_slot(mm, 6, mag_tilt, fp)
        _write_slot(mm, 7, mag_tilt_hgm, fp)
        _write_slot(mm, 8, grav_tilt_hgm, fp)
        _write_slot(mm, 9, np.log1p(np.maximum(coedge, 0.0)), fp)
        _write_slot(mm, 10, updip_tilt, fp)

        # Keep compact flight-line seam & magnetic anomaly standardized copy before freeing Group A intermediates
        tmi_z_keep = _robust_z(mag_anom, fp) + np.float32(0.25) * (_robust_z(tmi, fp) - _robust_z(mag_anom, fp))
        ew_stripe = np.abs(ndi.gaussian_filter(mag_anom, sigma=(1.0, 8.0), order=(1, 0), mode="nearest")) - np.abs(
            ndi.gaussian_filter(mag_anom, sigma=(8.0, 1.0), order=(0, 1), mode="nearest")
        )
        zb_flex = np.abs(ndi.gaussian_filter(zb, 3.0, order=(2, 0), mode="nearest") + ndi.gaussian_filter(zb, 3.0, order=(0, 2), mode="nearest"))
        del mag_anom, tmi, rtp, tmi_hg, tmi_vg, grav_slope, grav_vg, grav, grav_hg_abs, zb
        del mag_tilt, mag_tilt_hgm, grav_tilt, grav_tilt_hgm, ry, rx, gy, gx, rn, gn, cos_rg, coedge, zby, zbx, zbn, shift_px, joint_tilt_hgm, yy, xx, sy_coord, sx_coord
        gc.collect()

        # Group B: Remaining competition bands (topography, strain, microseismic swarms, MT conductance, radiometric TC)
        det_elev = _clean_band(src.read(12), fp)
        scarp_slope = np.maximum(_clean_band(src.read(19), fp), 0.0)
        g2nd = _clean_band(src.read(4), fp)
        gshr = _clean_band(src.read(7), fp)  # Band 7 = geod_shearrate
        gdil = _clean_band(src.read(8), fp)  # Band 8 = geod_dilaterate
        deq = np.maximum(_clean_band(src.read(10), fp), 0.0)
        ieq = np.maximum(_clean_band(src.read(16), fp), 0.0)
        cond = _clean_band(src.read(17), fp)
        rad_tc = np.maximum(_clean_band(src.read(6), fp), 0.0)

        _write_slot(mm, 11, det_elev, fp)
        _write_slot(mm, 12, np.log1p(scarp_slope), fp)
        _write_slot(mm, 13, np.log1p(zb_flex), fp)
        _write_slot(mm, 14, g2nd, fp)
        valve = _robust_z(gshr, fp) * np.maximum(_robust_z(gdil, fp), 0.0)
        _write_slot(mm, 15, valve, fp)
        swarm_ex = np.log1p(deq) - np.log1p(ieq)
        _write_slot(mm, 16, swarm_ex, fp)
        seism_grad = _grad_mag(np.log1p(deq + ieq), 2.0)
        _write_slot(mm, 17, seism_grad, fp)
        mt_edge = _grad_mag(cond, 2.0)
        _write_slot(mm, 18, mt_edge, fp)
        _write_slot(mm, 19, rad_tc, fp)
        del det_elev, scarp_slope, zb_flex, g2nd, gdil, gshr, deq, ieq, cond, rad_tc, valve, swarm_ex, seism_grad, mt_edge
        gc.collect()

    # Group C & D: Official USGS GeoDAWN, 3DEP 1-m LiDAR, 10-m DEM/chi, DOE GDR 1391 & Deconfounders
    with rasterio.open(ext_dir / "geodawn_extensions_u8.tif") as ext_gd:
        tmi_up150 = ext_gd.read(2).astype(np.float32)
        u_th = ext_gd.read(4).astype(np.float32)
    trough = _robust_z(tmi_up150, fp) - tmi_z_keep
    u_th_hp = u_th - ndi.gaussian_filter(u_th, 10.0, mode="nearest")
    _write_slot(mm, 20, trough, fp)
    _write_slot(mm, 22, u_th_hp, fp)
    del tmi_up150, u_th, trough, u_th_hp, tmi_z_keep
    gc.collect()

    with rasterio.open(ext_dir / "geodawn_rad_u8.tif") as rad_ds:
        k_th = rad_ds.read(4).astype(np.float32)
    k_th_hp = k_th - ndi.gaussian_filter(k_th, 10.0, mode="nearest")
    _write_slot(mm, 21, k_th_hp, fp)
    del k_th, k_th_hp
    gc.collect()

    with rasterio.open(ext_dir / "lidar_scarp_features_u8.tif") as lid_ds:
        step_max = lid_ds.read(1).astype(np.float32)
        upface = lid_ds.read(4).astype(np.float32)
        downface = lid_ds.read(5).astype(np.float32)
        cross_m = lid_ds.read(6).astype(np.float32)
        coh100 = lid_ds.read(7).astype(np.float32)

    with rasterio.open(ext_dir / "topo_10m_derived_100m_u8.tif") as t10_ds:
        pcurv = t10_ds.read(3).astype(np.float32)
        rel_local = t10_ds.read(5).astype(np.float32)
        elev10 = t10_ds.read(8).astype(np.float32) * np.float32(16.0) + np.float32(800.0)

    lid_norm = step_max / np.sqrt(rel_local + np.float32(9.0))
    lid_coh = ((upface + downface) * coh100) / (cross_m + np.float32(8.0))
    _write_slot(mm, 23, lid_norm, fp)
    _write_slot(mm, 24, lid_coh, fp)

    with rasterio.open(ext_dir / "dem10_chi_100m_i16.tif") as chi_ds:
        chi_step = np.maximum(chi_ds.read(2).astype(np.float32), 0.0)
        chi_ksn = np.maximum(chi_ds.read(3).astype(np.float32), 0.0)
    chi_knick = np.log1p(chi_step * np.sqrt(chi_ksn + np.float32(1.0))) + np.float32(0.15) * _robust_z(np.abs(pcurv - np.float32(128.0)), fp)
    _write_slot(mm, 25, chi_knick, fp)

    probe_f, sinter_f, gdr_meta = build_gdr_geothermal_channels(ext_dir, grid.shape, grid.transform, fp)
    _write_slot(mm, 26, probe_f, fp)
    _write_slot(mm, 27, sinter_f, fp)

    # Pleistocene Lake Lahontan highstand benches (~1334 m Sehoo, ~1298 m, ~1212 m)
    lahontan = (
        np.exp(-0.5 * ((elev10 - 1334.0) / 14.0) ** 2)
        + np.exp(-0.5 * ((elev10 - 1298.0) / 14.0) ** 2)
        + np.exp(-0.5 * ((elev10 - 1212.0) / 14.0) ** 2)
    ).astype(np.float32)

    _write_slot(mm, 28, ew_stripe, fp)
    _write_slot(mm, 29, lahontan, fp)
    _write_slot(mm, 30, rel_local, fp)
    _write_slot(mm, 31, _robust_z(updip_tilt, fp) * np.maximum(_robust_z(lid_norm, fp), 0.0), fp)

    del step_max, upface, downface, cross_m, coh100, pcurv, rel_local, elev10
    del lid_norm, lid_coh, chi_step, chi_ksn, chi_knick, probe_f, sinter_f, lahontan, ew_stripe, updip_tilt
    mm.flush()
    gc.collect()

    meta = {
        "version": "ugfv88-v1",
        "shape": [grid.height, grid.width],
        "n_channels": n_ch,
        "channel_names": list(UGFV_STATIC_NAMES),
        "dtype": "float16",
        "bytes": int(f16_path.stat().st_size),
        "build_seconds": round(time.monotonic() - t0, 2),
        "forbidden_files_excluded": sorted(FORBIDDEN_EXTERNAL_FILES),
        "gdr_external_summary": gdr_meta,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(f16_path, dtype=np.float16, mode="r", shape=(n_cells, n_ch)), meta


def load_sense_code_raster(csv_path: Path, shape: tuple[int, int], transform: rasterio.Affine) -> np.ndarray:
    """Pure-stdlib UTM11 slip-sense code raster (`1=N/other, 2=RL, 3=LL`), zero pandas dependency."""
    out = np.zeros(shape, dtype=np.int8)
    ox, oy = float(transform.c), float(transform.f)
    sx, sy = float(transform.a), float(-transform.e)
    H, W = shape
    x0s, y0s, x1s, y1s, codes = [], [], [], [], []
    with csv_path.open(newline="") as f:
        for row in csv.DictReader(f):
            s = row["sense"].strip()
            codes.append(2 if s == "RL" else (3 if s == "LL" else 1))
            x0s.append(float(row["x0"]))
            y0s.append(float(row["y0"]))
            x1s.append(float(row["x1"]))
            y1s.append(float(row["y1"]))
    x0 = np.asarray(x0s, dtype=np.float64)
    y0 = np.asarray(y0s, dtype=np.float64)
    x1 = np.asarray(x1s, dtype=np.float64)
    y1 = np.asarray(y1s, dtype=np.float64)
    cd = np.asarray(codes, dtype=np.int8)
    for t in np.linspace(0.0, 1.0, 6):
        cc = np.floor(((x0 + t * (x1 - x0)) - ox) / sx).astype(np.int32)
        rr = np.floor((oy - (y0 + t * (y1 - y0))) / sy).astype(np.int32)
        ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
        out[rr[ok], cc[ok]] = np.maximum(out[rr[ok], cc[ok]], cd[ok])
    return out


def compute_visible_structural_fields(
    grid: g57_grid.Grid,
    visible: np.ndarray,
    sense_full: np.ndarray,
    eval_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract 16 strictly visible-only structural continuation & relay features on `eval_mask` pixels.

    Returns `(flat_indices, X_struct)` with `X_struct.shape == (eval_mask.sum(), 16)`.
    Slip sense is explicitly masked by `visible` (`np.where(visible, sense_full, 0)`).
    """
    vis = np.asarray(visible, dtype=bool)
    sense_masked = np.where(vis, sense_full, np.int8(0))
    dummy_hidden = np.zeros(grid.shape, dtype=bool)

    fg = anatomy.fold_geometry(grid, vis, dummy_hidden, eval_mask, "vis", sense_src=sense_masked)
    H, W = grid.shape
    rows = fg.rows.astype(np.int32)
    cols = fg.cols.astype(np.int32)
    fg_X = fg.X.astype(np.float32, copy=False)
    del fg, sense_masked, dummy_hidden
    gc.collect()
    flat_idx = rows.astype(np.int64) * W + cols.astype(np.int64)

    # Tip continuation laser-beam + multi-host step-over bridge strictly from `vis`
    nb = ndi.convolve(vis.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant")
    tips = vis & (nb <= 2)
    if not tips.any():
        tips = vis

    strike, _coh = anatomy.local_strike(vis, smooth_px=3.0)
    d_tip, (ty, tx) = ndi.distance_transform_edt(~tips, return_indices=True)
    del _coh, nb, tips

    ay = ty[rows, cols]
    ax = tx[rows, cols]
    th_raw = strike[ay, ax]
    th_deg = np.where(np.isfinite(th_raw), th_raw, 0.0)
    dy = (rows - ay).astype(np.float32)
    dx = (cols - ax).astype(np.float32)
    del ty, tx, strike
    # Exact along-strike and cross-strike coordinates in degrees convention via shared `anatomy.offset_components`
    a_tip, l_tip, _side_tip = anatomy.offset_components(dy, dx, th_deg)

    tip_dist_log = np.log1p(d_tip[rows, cols].astype(np.float32))
    del d_tip
    tip_beam = (np.exp(-0.5 * (l_tip / 3.0) ** 2) * np.exp(-np.abs(a_tip) / 28.0)).astype(np.float32)

    vis_f = vis.astype(np.float32)
    dens12 = ndi.gaussian_filter(vis_f, sigma=12.0, mode="constant")
    d_host = fg_X[:, 0]  # host distance `d` from `anatomy.fold_geometry`
    # Expected single-line Gaussian density profile at distance `d_host`
    single_line = (1.0 / (math.sqrt(2.0 * math.pi) * 12.0)) * np.exp(-0.5 * (d_host / 12.0) ** 2)
    multihost_ex = np.maximum(dens12[rows, cols] - single_line, 0.0).astype(np.float32)

    X_extra = np.column_stack([tip_dist_log, tip_beam, multihost_ex]).astype(np.float32)
    X_out = np.hstack([fg_X, X_extra])
    del fg_X, X_extra, dens12
    gc.collect()
    return flat_idx, X_out


def nested_visible_draw(
    visible: np.ndarray,
    footprint: np.ndarray,
    *,
    seed: int,
    hide_frac: float = 0.25,
    buffer_px: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Self-mask ~`hide_frac` of whole 8-connected components strictly inside `visible`.

    Never touches `grid.catalogue` or `hidden_all`. Returns `(inner_vis, inner_truth)`.
    """
    vis = np.asarray(visible, dtype=bool)
    comp, n_comp = ndi.label(vis, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)
    ids = np.arange(1, n_comp + 1, dtype=np.int32)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(ids)
    target_mass = hide_frac * float(vis.sum())
    picked = []
    acc = 0.0
    for cid in perm:
        if acc >= target_mass:
            break
        picked.append(int(cid))
        acc += float(sizes[cid])
    inner_truth = np.isin(comp, picked) & vis & footprint
    collar = ndi.distance_transform_edt(~inner_truth) <= buffer_px
    inner_vis = vis & (~collar)
    assert not np.any(inner_vis & inner_truth)
    return inner_vis, inner_truth


def dinkelbach_candidate_coords(
    p: np.ndarray,
    allowed: np.ndarray,
    *,
    candidate_cap: int = 320_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the exact `(ys, xs)` candidate ordering used inside `emit.dinkelbach_allocate`."""
    p_f = np.clip(np.asarray(p, np.float32), 0.0, 1.0)
    allow = np.asarray(allowed, dtype=bool)
    ek = emit.expected_credit(p_f)
    ys, xs = np.nonzero(allow & (ek > 0.0))
    if ys.size > candidate_cap:
        top_idx = np.argpartition(-ek[ys, xs], candidate_cap)[:candidate_cap]
        ys, xs = ys[top_idx], xs[top_idx]
    ord_init = np.argsort(-ek[ys, xs], kind="stable")
    return ys[ord_init].astype(np.int32), xs[ord_init].astype(np.int32)


def load_discriminating_registry_dots(registry_root: Path, shape: tuple[int, int]) -> list[tuple[str, np.ndarray, int]]:
    """Load deduplicated positive dot masks for all non-continuous sibling GeoTIFFs (`138` rasters)."""
    seen_sha: set[str] = set()
    items: list[tuple[str, np.ndarray, int]] = []
    for tif in sorted(registry_root.rglob("*.tif")):
        h = uniqueness._sha(tif)
        if h in seen_sha:
            continue
        seen_sha.add(h)
        with rasterio.open(tif) as src:
            if src.shape != shape:
                continue
            arr = src.read(1)
        pos = np.isfinite(arr) & (arr > 0.0)
        n_pos = int(pos.sum())
        if n_pos == 0 or n_pos > 1_000_000:
            # Skip empty and continuous-surface rasters (`dense_17gemdoe.tif` has 5,167,373 positives)
            continue
        items.append((str(tif.relative_to(registry_root)), pos, n_pos))
    return items


def build_halo_constraint_matrix(
    cand_ys: np.ndarray,
    cand_xs: np.ndarray,
    reg_dots: list[tuple[str, np.ndarray, int]],
    *,
    max_overlap: float = 0.65,
    budget: int = 37_654,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Construct exact candidate-indexed `halo_constraints` matching `uniqueness.dot_overlap`."""
    rows_c: list[np.ndarray] = []
    caps: list[int] = []
    cap_hits = int(math.floor(max_overlap * budget))
    for _name, pos, n_pos in reg_dots:
        if n_pos < 6_000:
            continue
        halo = uniqueness._near(pos, 3)
        vec = halo[cand_ys, cand_xs].astype(np.uint8)
        if int(vec.sum()) > cap_hits:
            rows_c.append(vec)
            caps.append(cap_hits)
    if not rows_c:
        return None, None
    return np.vstack(rows_c), np.asarray(caps, dtype=np.int32)
