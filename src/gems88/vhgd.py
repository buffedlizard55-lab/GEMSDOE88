"""H88-VHGD: Vertical Heat-Flux Gradient, Geothermometer Kinetic Disequilibrium
& Depth-Compensated Basement Admittance (`PREREG-20261025-VHGD88`).

16 strictly zero-catalogue physical & hydrothermal channels (`VHGD_FEATURES`):
  0. vhgd_probe_dtdz_loc        : 600 m shallow vertical heat-flux gradient (T2m-T1m, 2*(T2m-T15m)) area-demeaned
  1. vhgd_probe_dtdz_reg        : 2.0 km regional conductive heat-flux plume from multi-depth 2-m probes
  2. vhgd_probe_multiepoch_pers : Multi-season positive thermal anomaly persistence across T2m..T2m_7 epochs
  3. vhgd_probe_upslope_pullback: Hydraulic-head up-slope (+grad DEM) 0.8-1.8 km pullback of probe dT/dz
  4. vhgd_cat_chalc_diseq       : Na-K-Ca vs chalcedony kinetic geothermometer disequilibrium (T_cat - T_chalc)
  5. vhgd_deep_cooling_deficit  : Ascensional conductive/mixing cooling deficit max(T_geotherm) - T_outflow
  6. vhgd_hydro_upslope_feeder  : Up-slope (+grad DEM) 1.0-2.2 km feeder pullback of disequilibrium + paleo-sinter
  7. vhgd_grav_salem_contact    : Depth-compensated Salem gravity tilt zero-crossing x local wavenumber ||grad theta_g||
  8. vhgd_dual_tilt_grad_lock   : Coincident gravity & magnetic tilt zero-crossings x |grad theta_g . grad theta_m|
  9. vhgd_mag_euler_persist_150m: 150-m upward-continued magnetic gradient persistence (deep sheet vs clast noise)
 10. vhgd_remanence_demag_step  : Local 1.5 km RTP magnetite-destruction trough locked to basement gravity HG
 11. vhgd_basement_compact_hinge: Differential-compaction surface monoclinal warp over buried basement-depth step
 12. vhgd_piedmont_rough_break  : 10-m DEM slope_std x aspect_coherence / relief_local bajada scarp breakline
 13. vhgd_coulomb_release_align : Great Basin N30E critically stressed transtensional strike x strain x seismicity
 14. vhgd_mimic_volcanic_lobe   : Named mimic #1 suppressor (shallow volcanic flow/cinder lobe without grav contact)
 15. vhgd_mimic_playa_evaporite : Named mimic #2 suppressor (playa evaporite / pluvial shoreline flat without contact)

Zero-catalogue & anti-leakage guarantees:
- ``existing_faults.tif``, ``sgmc_faults_100m.tif``, and ``derived_sgmc_faults_100m_u8.tif`` are NEVER read.
- ``dist_known_fault_px`` is explicitly quarantined and stripped before reading GDR CSV rows.
- Exact raster tags and CSV/DBF headers are programmatically asserted (preventing IR-88-116/117/118).
"""
from __future__ import annotations

import csv
import gc
import hashlib
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from lightgbm import LGBMClassifier, LGBMRegressor
from rasterio.warp import transform as crs_transform
from scipy import ndimage as ndi

from gems57 import emit
from . import adhr, physics
from .edge import clean_band

VHGD_SCHEMA_VERSION = "vhgd88-16ch-v1"

VHGD_FEATURES: tuple[str, ...] = (
    "vhgd_probe_dtdz_loc",
    "vhgd_probe_dtdz_reg",
    "vhgd_probe_multiepoch_pers",
    "vhgd_probe_upslope_pullback",
    "vhgd_cat_chalc_diseq",
    "vhgd_deep_cooling_deficit",
    "vhgd_hydro_upslope_feeder",
    "vhgd_grav_salem_contact",
    "vhgd_dual_tilt_grad_lock",
    "vhgd_mag_euler_persist_150m",
    "vhgd_remanence_demag_step",
    "vhgd_basement_compact_hinge",
    "vhgd_piedmont_rough_break",
    "vhgd_coulomb_release_align",
    "vhgd_mimic_volcanic_lobe",
    "vhgd_mimic_playa_evaporite",
)

FORBIDDEN_CSV_COLUMNS: frozenset[str] = frozenset({
    "dist_known_fault_px",
    "dist_fault",
    "fault_dist",
    "d_cat",
})


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _robust_z_masked(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    vals = np.asarray(arr, dtype=np.float32)[valid]
    if vals.size == 0:
        return np.zeros_like(arr, dtype=np.float32)
    q10, med, q90 = (float(v) for v in np.percentile(vals, [10.0, 50.0, 90.0]))
    scale = max((q90 - q10) / 2.5631, float(np.std(vals)) * 0.5, 1e-6)
    out = np.zeros_like(arr, dtype=np.float32)
    out[valid] = np.clip((arr[valid] - med) / scale, -8.0, 8.0).astype(np.float32)
    return out


def _decode_topo10_band(ds: rasterio.DatasetReader, band_idx: int, want_name: str, fp: np.ndarray) -> np.ndarray:
    tags = ds.tags(band_idx)
    got_name = tags.get("band_name") or (ds.descriptions[band_idx - 1] or "")
    if got_name != want_name:
        raise ValueError(f"topo_10m_derived_100m_u8 B{band_idx}: expected {want_name!r}, got {got_name!r}")
    q_lo = float(tags["q_lo"])
    q_hi = float(tags["q_hi"])
    q = ds.read(band_idx).astype(np.float32)
    phys = np.where(q > 0.0, q_lo + (q - 1.0) / 254.0 * (q_hi - q_lo), np.nan).astype(np.float32)
    return clean_band(phys, fp)[0]


def _disk_offsets(radius_px: float) -> tuple[np.ndarray, np.ndarray]:
    r = int(math.ceil(radius_px))
    r2 = float(radius_px) * float(radius_px)
    dys, dxs = [], []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx < r2:
                dys.append(dy)
                dxs.append(dx)
    return np.asarray(dys, dtype=np.int32), np.asarray(dxs, dtype=np.int32)


def _dilate_spacing_mask(dots_bool: np.ndarray, min_spacing_px: float) -> np.ndarray:
    ys, xs = np.nonzero(dots_bool)
    if ys.size == 0:
        return np.zeros_like(dots_bool, dtype=bool)
    H, W = dots_bool.shape
    dys, dxs = _disk_offsets(min_spacing_px)
    out = np.zeros_like(dots_bool, dtype=bool)
    for dy, dx in zip(dys, dxs):
        ry = ys + int(dy)
        rx = xs + int(dx)
        ok = (ry >= 0) & (ry < H) & (rx >= 0) & (rx < W)
        out[ry[ok], rx[ok]] = True
    return out


def build_or_load_vhgd_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict]:
    """Build or reload disk-backed ``(N_fp, 16)`` float32 memmap with < 500 MB peak RSS."""
    fp = np.asarray(grid.footprint, dtype=bool)
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    n_cols = len(VHGD_FEATURES)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / f"x_{VHGD_SCHEMA_VERSION}.dat"
    meta_path = cache_dir / f"x_{VHGD_SCHEMA_VERSION}.json"

    feat_path = root / "data/training_features.tif"
    ext = root / "data/external"
    dep_rels = (
        "data/training_features.tif",
        "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip",
        "data/external/gdr_wellspring_in_footprint.csv",
        "data/external/gdr_volcanic_vents_in_footprint.csv",
        "data/external/paleo_geothermal_regional.zip",
        "data/external/geodawn_extensions_u8.tif",
        "data/external/topo_10m_derived_100m_u8.tif",
    )
    dep_hashes = {rel: _sha256_file(root / rel) for rel in dep_rels}

    if dat_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("schema") == VHGD_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(VHGD_FEATURES)
            and meta.get("dep_hashes") == dep_hashes
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    shape = grid.shape
    H, W = shape
    inv_tf = ~grid.transform

    # ------------------------------------------------------------------
    # 1. Topographic DEM + hydraulic-head down-slope vector + 10-m breakline
    # ------------------------------------------------------------------
    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as ds:
        slope_std = _decode_topo10_band(ds, 4, "slope_std", fp)
        relief_loc = _decode_topo10_band(ds, 5, "relief_local", fp)
        aspect_coh = _decode_topo10_band(ds, 7, "aspect_coherence", fp)
        dem_m = _decode_topo10_band(ds, 9, "dem_mean", fp)

    # Channel 12: 10-m sub-pixel roughness-coherence piedmont breakline
    mm[:, 12] = (
        (slope_std[ys, xs] * np.power(np.clip(aspect_coh[ys, xs], 0.0, 1.0), 1.5))
        / (1.0 + 0.12 * np.maximum(relief_loc[ys, xs], 0.0))
    ).astype(np.float32)
    del slope_std, relief_loc, aspect_coh

    dgy, dgx, dmag = physics._grad_f32(dem_m, 6.0)
    udown_y_fp = (-dgy[ys, xs] / (dmag[ys, xs] + 1e-4)).astype(np.float32)
    udown_x_fp = (-dgx[ys, xs] / (dmag[ys, xs] + 1e-4)).astype(np.float32)
    slope_gate_fp = np.tanh(dmag[ys, xs] / 2.0).astype(np.float32)
    dem_fp = dem_m[ys, xs].copy()
    del dem_m, dgy, dgx, dmag
    gc.collect()

    # ------------------------------------------------------------------
    # 2. Never-read 2-m probe vertical temperature gradients (T1m, T15m, T2m..T2m_7)
    # ------------------------------------------------------------------
    with zipfile.ZipFile(ext / "2m_temperature_probe_INGENIOUS_regional_data.zip") as zf:
        dbf_bytes = zf.read(
            "2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf"
        )
    probe_rows = physics._read_dbf_records(dbf_bytes)
    del dbf_bytes

    def _fval(v: object) -> float:
        if v is None:
            return float("nan")
        s = str(v).strip()
        if not s or s.lower() == "nan":
            return float("nan")
        try:
            return float(s)
        except ValueError:
            return float("nan")

    epoch_cols = ("T2m", "T2m_2", "T2m_3", "T2m_4", "T2m_5", "T2m_6", "T2m_7")
    area_grads: dict[str, list[float]] = defaultdict(list)
    area_epoch_temps: dict[tuple[str, str], list[float]] = defaultdict(list)
    parsed_probes: list[tuple[float, float, str, float, dict[str, float]]] = []

    for r in probe_rows:
        lon, lat = _fval(r.get("LongDegree")), _fval(r.get("LatDegreeN"))
        if not (math.isfinite(lon) and math.isfinite(lat) and -125.0 < lon < -110.0 and 34.0 < lat < 44.0):
            continue
        area = (r.get("Area") or "UNKNOWN").strip() or "UNKNOWN"
        t2 = _fval(r.get("T2m"))
        t1 = _fval(r.get("T1m"))
        t15 = _fval(r.get("T15m"))

        grads = []
        if math.isfinite(t2) and t2 > 0.5 and math.isfinite(t1) and t1 > 0.5:
            grads.append(float(np.clip(t2 - t1, -15.0, 25.0)))
        if math.isfinite(t2) and t2 > 0.5 and math.isfinite(t15) and t15 > 0.5:
            grads.append(float(np.clip(2.0 * (t2 - t15), -15.0, 25.0)))
        g_val = float(np.mean(grads)) if grads else float("nan")
        if math.isfinite(g_val):
            area_grads[area].append(g_val)

        ep_map: dict[str, float] = {}
        for ec in epoch_cols:
            tv = _fval(r.get(ec))
            if math.isfinite(tv) and 1.0 < tv < 98.0:
                ep_map[ec] = tv
                area_epoch_temps[(area, ec)].append(tv)
        parsed_probes.append((lon, lat, area, g_val, ep_map))

    area_grad_med = {a: float(np.median(vs)) for a, vs in area_grads.items() if vs}
    area_ep_med = {k: float(np.median(vs)) for k, vs in area_epoch_temps.items() if vs}

    g_lons, g_lats, g_excess = [], [], []
    p_lons, p_lats, p_persist = [], [], []
    for lon, lat, area, g_val, ep_map in parsed_probes:
        if math.isfinite(g_val):
            ex_g = max(g_val - area_grad_med.get(area, 0.0), 0.0)
            g_lons.append(lon)
            g_lats.append(lat)
            g_excess.append(ex_g)
        if ep_map:
            pos_excesses = []
            for ec, tv in ep_map.items():
                med_t = area_ep_med.get((area, ec), tv)
                if tv > med_t:
                    pos_excesses.append(min(tv - med_t, 25.0))
            if pos_excesses:
                score = float(np.mean(pos_excesses)) * (1.0 + 0.45 * (len(pos_excesses) - 1))
                p_lons.append(lon)
                p_lats.append(lat)
                p_persist.append(score)

    if len(g_lons) < 1000:
        raise AssertionError(f"Expected >= 1000 multi-depth 2-m probe gradient stations, got {len(g_lons)}")

    gx_u, gy_u = crs_transform("EPSG:4269", grid.crs, g_lons, g_lats)
    g_cols, g_rows = inv_tf * (np.asarray(gx_u), np.asarray(gy_u))
    g_wt = np.asarray(g_excess, dtype=np.float32)
    dtdz_loc = np.log1p(
        physics._splat_points(shape, np.floor(g_rows), np.floor(g_cols), g_wt, sigma_px=6.0, normalize_density=True)
    )
    dtdz_reg = np.log1p(
        physics._splat_points(shape, np.floor(g_rows), np.floor(g_cols), g_wt, sigma_px=20.0, normalize_density=True)
    )

    px_u, py_u = crs_transform("EPSG:4269", grid.crs, p_lons, p_lats)
    p_cols, p_rows = inv_tf * (np.asarray(px_u), np.asarray(py_u))
    persist_grid = np.log1p(
        physics._splat_points(
            shape,
            np.floor(p_rows),
            np.floor(p_cols),
            np.asarray(p_persist, dtype=np.float32),
            sigma_px=8.0,
            normalize_density=True,
        )
    )

    mm[:, 0] = dtdz_loc[ys, xs]
    mm[:, 1] = dtdz_reg[ys, xs]
    mm[:, 2] = persist_grid[ys, xs]
    probe_plume = (dtdz_loc + 0.65 * persist_grid).astype(np.float32)
    mm[:, 3] = slope_gate_fp * (
        0.55 * physics._bilinear_at_fp(probe_plume, ys, xs, 8.0 * udown_y_fp, 8.0 * udown_x_fp)
        + 0.45 * physics._bilinear_at_fp(probe_plume, ys, xs, 18.0 * udown_y_fp, 18.0 * udown_x_fp)
    )
    n_probe_dtdz = len(g_lons)
    n_probe_persist = len(p_lons)
    del dtdz_loc, dtdz_reg, persist_grid, probe_plume, probe_rows, parsed_probes
    gc.collect()

    # ------------------------------------------------------------------
    # 3. Geochemical kinetic disequilibrium (T_cat, T_chalc, T_qtz, T_out) + Paleo-sinter
    # ------------------------------------------------------------------
    ws_path = ext / "gdr_wellspring_in_footprint.csv"
    kin_rows, kin_cols, kin_vals = [], [], []
    cool_rows, cool_cols, cool_vals = [], [], []
    n_cat_valid = 0
    with ws_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for req_col in ("row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
            if req_col not in fieldnames:
                raise ValueError(f"Missing required column {req_col!r} in {ws_path}")
        safe_cols = [c for c in fieldnames if c not in FORBIDDEN_CSV_COLUMNS]
        assert "dist_known_fault_px" not in safe_cols
        for raw in reader:
            row = {c: raw[c] for c in safe_cols}
            rr, cc = _fval(row.get("row")), _fval(row.get("col"))
            if not (math.isfinite(rr) and math.isfinite(cc)):
                continue
            ri, ci = int(rr), int(cc)
            if not (0 <= ri < H and 0 <= ci < W):
                continue
            t_out = _fval(row.get("temp_c"))
            t_qtz = _fval(row.get("geothermquartz_c"))
            t_cha = _fval(row.get("geothermchalc_c"))
            t_cat = _fval(row.get("geothermcat_c"))

            if math.isfinite(t_cat) and 25.0 < t_cat < 360.0:
                n_cat_valid += 1
                if math.isfinite(t_cha) and 10.0 < t_cha < 360.0:
                    dk = max(t_cat - t_cha, 0.0)
                else:
                    dk = 0.6 * max(t_cat - 75.0, 0.0)
                if dk > 0.0:
                    kin_rows.append(ri)
                    kin_cols.append(ci)
                    kin_vals.append(min(dk, 180.0))

            geotherms = [t for t in (t_cat, t_qtz, t_cha) if math.isfinite(t) and 60.0 < t < 360.0]
            if geotherms:
                t_res = max(geotherms)
                t_ref = max(t_out, 15.0) if (math.isfinite(t_out) and 0.0 < t_out < 250.0) else 20.0
                dcool = max(t_res - t_ref, 0.0)
                if dcool > 0.0:
                    cool_rows.append(ri)
                    cool_cols.append(ci)
                    cool_vals.append(min(dcool, 220.0))

    if n_cat_valid < 800:
        raise AssertionError(f"Expected >= 800 valid geothermcat_c records, got {n_cat_valid}")

    kin_grid = np.log1p(
        physics._splat_points(
            shape,
            np.asarray(kin_rows, np.int32),
            np.asarray(kin_cols, np.int32),
            np.asarray(kin_vals, np.float32),
            sigma_px=14.0,
            normalize_density=True,
        )
    )
    cool_grid = np.log1p(
        physics._splat_points(
            shape,
            np.asarray(cool_rows, np.int32),
            np.asarray(cool_cols, np.int32),
            np.asarray(cool_vals, np.float32),
            sigma_px=12.0,
            normalize_density=True,
        )
    )

    with zipfile.ZipFile(ext / "paleo_geothermal_regional.zip") as zf:
        paleo_rows = list(
            csv.DictReader(io.StringIO(zf.read("Paleo_geothermal_final.csv").decode("utf-8-sig", "replace")))
        )
    s_lons, s_lats, s_wts = [], [], []
    for r in paleo_rows:
        lon, lat = _fval(r.get("Long_deg_NAD83")), _fval(r.get("Lat_deg_NAD83"))
        if not (math.isfinite(lon) and math.isfinite(lat)):
            continue
        dt = (r.get("Deposit_type") or "").lower()
        w = 2.4 if ("sinter" in dt or "silic" in dt) else (1.6 if "travertine" in dt else 1.0)
        s_lons.append(lon)
        s_lats.append(lat)
        s_wts.append(w)
    sx_u, sy_u = crs_transform("EPSG:4269", grid.crs, s_lons, s_lats)
    s_cols, s_rows = inv_tf * (np.asarray(sx_u), np.asarray(sy_u))
    in_b = (s_rows >= 0) & (s_rows < H) & (s_cols >= 0) & (s_cols < W)
    if int(in_b.sum()) < 50:
        raise AssertionError(f"Expected >= 50 in-bounds paleo-geothermal deposits, got {int(in_b.sum())}")
    sinter_grid = np.log1p(
        20.0 * physics._splat_points(shape, np.floor(s_rows), np.floor(s_cols), np.asarray(s_wts, np.float32), sigma_px=11.0)
    )

    mm[:, 4] = kin_grid[ys, xs]
    mm[:, 5] = cool_grid[ys, xs]
    hydro_plume = (kin_grid + 0.85 * cool_grid + 1.25 * sinter_grid).astype(np.float32)
    mm[:, 6] = slope_gate_fp * (
        0.55 * physics._bilinear_at_fp(hydro_plume, ys, xs, 10.0 * udown_y_fp, 10.0 * udown_x_fp)
        + 0.45 * physics._bilinear_at_fp(hydro_plume, ys, xs, 22.0 * udown_y_fp, 22.0 * udown_x_fp)
    )
    del kin_grid, cool_grid, sinter_grid, hydro_plume, udown_y_fp, udown_x_fp, slope_gate_fp
    gc.collect()

    # Volcanic vent proximity (strictly stripping dist_known_fault_px)
    v_rows, v_cols = [], []
    with (ext / "gdr_volcanic_vents_in_footprint.csv").open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        safe_vcols = [c for c in (reader.fieldnames or []) if c not in FORBIDDEN_CSV_COLUMNS]
        assert "dist_known_fault_px" not in safe_vcols
        for raw in reader:
            row = {c: raw[c] for c in safe_vcols}
            rr, cc = _fval(row.get("row")), _fval(row.get("col"))
            if math.isfinite(rr) and math.isfinite(cc):
                v_rows.append(int(rr))
                v_cols.append(int(cc))
    vent_prox_fp = np.log1p(
        80.0
        * physics._splat_points(
            shape, np.asarray(v_rows, np.int32), np.asarray(v_cols, np.int32), np.ones(len(v_rows), np.float32), sigma_px=20.0
        )[ys, xs]
    ).astype(np.float32)

    # ------------------------------------------------------------------
    # 4. 3D Potential-Field Salem Tilt-Contact, Euler 150-m Persistence & Mimics
    # ------------------------------------------------------------------
    with rasterio.open(ext / "geodawn_extensions_u8.tif") as ds:
        if (ds.descriptions[3] or "") != "TMI_up150":
            raise ValueError(f"Expected geodawn_extensions_u8 B4='TMI_up150', got {ds.descriptions[3]!r}")
        raw_up150 = ds.read(4).astype(np.float32)
        up150_valid = fp & (raw_up150 > 0.0)
        tmi_up150 = clean_band(np.where(raw_up150 > 0.0, raw_up150, np.nan).astype(np.float32), fp)[0]
        del raw_up150
    _, _, hg_up150 = physics._grad_f32(tmi_up150, 1.5)
    del tmi_up150

    with rasterio.open(feat_path) as src:
        for idx, want_tag in physics.EXPECTED_TRAINING_BANDS.items():
            got = src.tags(idx).get("band_name", "")
            if got != want_tag:
                raise ValueError(f"training_features.tif B{idx}: expected {want_tag!r}, got {got!r}")

        def rd(idx: int) -> np.ndarray:
            return clean_band(src.read(idx), fp)[0]

        b3_tmi_hg = np.maximum(rd(3), 0.0)
        b9_tmi_vg = rd(9)
        b11_grav_vg = rd(11)
        b18_grav_hg = np.maximum(rd(18), 0.0)
        zbase_m = np.maximum(rd(15), 0.0)

        theta_g = np.arctan2(b11_grav_vg, b18_grav_hg + 1e-6).astype(np.float32)
        as_grav = np.hypot(b18_grav_hg, b11_grav_vg).astype(np.float32)
        del b11_grav_vg

        tgy, tgx, kappa_g = physics._grad_f32(theta_g, 1.2)
        theta_g_fp = theta_g[ys, xs]
        kappa_g_fp = kappa_g[ys, xs]
        grav_zero_fp = np.exp(-((theta_g_fp / 0.24) ** 2)).astype(np.float32)
        depth_mult_fp = 1.0 + np.clip(zbase_m[ys, xs] / 400.0, 0.0, 5.0)

        # Channel 7: Depth-compensated Salem gravity tilt-wavenumber contact
        mm[:, 7] = (
            grav_zero_fp
            * np.log1p(80.0 * kappa_g_fp)
            * np.log1p(50.0 * as_grav[ys, xs] * depth_mult_fp)
        ).astype(np.float32)
        del as_grav, depth_mult_fp

        theta_m = np.arctan2(b9_tmi_vg, b3_tmi_hg + 1e-6).astype(np.float32)
        del b9_tmi_vg
        tmy, tmx, kappa_m = physics._grad_f32(theta_m, 1.2)
        align_gm_fp = np.abs(tgx[ys, xs] * tmx[ys, xs] + tgy[ys, xs] * tmy[ys, xs]) / (
            kappa_g_fp * kappa_m[ys, xs] + 1e-6
        )

        # Channel 8: Dual gravity-magnetic tilt zero-crossing & gradient phase lock
        mm[:, 8] = (
            np.exp(-((theta_g_fp * theta_g_fp + theta_m[ys, xs] ** 2) / (2.0 * 0.32 * 0.32)))
            * align_gm_fp
            * np.sqrt(np.log1p(60.0 * kappa_g_fp) * np.log1p(60.0 * kappa_m[ys, xs]))
        ).astype(np.float32)
        del theta_m, tmy, tmx, kappa_m, align_gm_fp, theta_g, kappa_g

        # Keep strike vector from gravity tilt gradient before freeing tgy, tgx
        sx_fp = (tgy[ys, xs] / (kappa_g_fp + 1e-6)).astype(np.float32)
        sy_fp = (-tgx[ys, xs] / (kappa_g_fp + 1e-6)).astype(np.float32)
        del tgy, tgx

        # Channel 9: 150-m upward-continued magnetic structural-index persistence
        z_hg0 = _robust_z_masked(np.log1p(b3_tmi_hg), up150_valid)
        z_hg150 = _robust_z_masked(np.log1p(hg_up150), up150_valid)
        decay_excess_fp = np.maximum(z_hg0[ys, xs] - z_hg150[ys, xs], 0.0).astype(np.float32)
        up_pers = np.where(up150_valid[ys, xs], z_hg150[ys, xs] - 0.45 * decay_excess_fp, 0.0).astype(np.float32)
        mm[:, 9] = up_pers
        del b3_tmi_hg, hg_up150, z_hg0, z_hg150, up150_valid, up_pers

        # Channel 10: Hydrothermal magnetite-destruction RTP trough on basement gravity HG
        b2_rtp = rd(2)
        rtp_trough = np.maximum(
            ndi.gaussian_filter(b2_rtp, sigma=10.0, mode="nearest")
            - ndi.gaussian_filter(b2_rtp, sigma=1.8, mode="nearest"),
            0.0,
        ).astype(np.float32)
        del b2_rtp
        mm[:, 10] = (np.log1p(rtp_trough[ys, xs]) * np.log1p(100.0 * b18_grav_hg[ys, xs])).astype(np.float32)
        del rtp_trough, b18_grav_hg

        # Channel 11: Differential-compaction monoclinal warp over buried basement step
        b12_det = rd(12)
        b19_slope = np.maximum(rd(19), 0.0)
        det_lap = ndi.gaussian_laplace(b12_det, sigma=2.5, mode="nearest").astype(np.float32)
        _, _, zbase_grad = physics._grad_f32(zbase_m, 3.0)
        mm[:, 11] = (
            np.log1p(np.abs(det_lap[ys, xs]))
            * np.log1p(zbase_grad[ys, xs] / 8.0)
            / (1.0 + 0.25 * b19_slope[ys, xs])
        ).astype(np.float32)
        del det_lap, zbase_m, zbase_grad

        # Channel 13: Critically stressed N30E transtensional releasing-strike permeability
        b7_shear = rd(7)[ys, xs]
        b8_dil = rd(8)[ys, xs]
        b16_ieq = np.log1p(np.maximum(rd(16)[ys, xs], 0.0) / 50.0).astype(np.float32)
        sin30, cos30 = 0.5, 0.8660254
        nne_align = (sx_fp * sin30 + sy_fp * cos30) ** 2
        strain_drive = np.log1p(np.maximum(b7_shear, 0.0) * 20.0) * (1.0 + np.maximum(b8_dil, 0.0) * 10.0)
        mm[:, 13] = (nne_align * strain_drive * (1.0 + 0.35 * b16_ieq) * np.log1p(40.0 * kappa_g_fp)).astype(
            np.float32
        )
        del sx_fp, sy_fp, b7_shear, b8_dil, b16_ieq, kappa_g_fp

        # Channel 14: Named Mimic #1 — Volcanic flow/cinder lobe without basement gravity contact
        mm[:, 14] = (vent_prox_fp * (0.5 + decay_excess_fp) * (1.0 - grav_zero_fp)).astype(np.float32)
        del vent_prox_fp, decay_excess_fp

        # Channel 15: Named Mimic #2 — Evaporitic playa brine / pluvial shoreline bench without contact
        b17_cond = np.maximum(rd(17)[ys, xs], 0.0)
        playa_low = (1.0 / (1.0 + np.exp(np.clip(b12_det[ys, xs] / 15.0, -20.0, 20.0)))).astype(np.float32)
        shore_ring = (
            np.exp(-(((dem_fp - 1330.0) / 25.0) ** 2)) + np.exp(-(((dem_fp - 1555.0) / 25.0) ** 2))
        ).astype(np.float32)
        mm[:, 15] = (
            np.log1p(b17_cond)
            * playa_low
            * (1.0 + shore_ring)
            * (1.0 - grav_zero_fp)
            / (1.0 + b19_slope[ys, xs])
        ).astype(np.float32)
        del b17_cond, b12_det, b19_slope, playa_low, shore_ring, dem_fp, grav_zero_fp
        gc.collect()

    mm.flush()
    for j in range(n_cols):
        col = mm[:, j]
        if not np.isfinite(col).all():
            raise AssertionError(f"Non-finite values in {VHGD_FEATURES[j]}")
        if float(np.std(col)) <= 1e-8:
            raise AssertionError(f"Degenerate constant feature {VHGD_FEATURES[j]}")

    meta = {
        "schema": VHGD_SCHEMA_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(VHGD_FEATURES),
        "dep_hashes": dep_hashes,
        "station_counts": {
            "probe_dtdz_stations": int(n_probe_dtdz),
            "probe_multiepoch_hot_stations": int(n_probe_persist),
            "wellspring_cation_valid": int(n_cat_valid),
            "paleo_in_bounds": int(in_b.sum()),
        },
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    del mm
    gc.collect()
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta


def fit_calibrated_lgbm_dual(
    sources: Sequence[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    seed: int,
    max_zero_neg: int = 140_000,
    dejitter_collar_px: float = 1.5,
) -> tuple[LGBMClassifier, LGBMRegressor]:
    """Fit inverse-probability sample-weighted LightGBM pixel + 300 m kernel models (< 400 MB RSS)."""
    ys_fp, xs_fp = np.nonzero(fp_mask)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int8)
    d_pos_grid = ndi.distance_transform_edt(~pos_grid).astype(np.float32)
    d_pos_fp = d_pos_grid[ys_fp, xs_fp]
    del d_pos_grid
    y_kern_all = np.clip(1.0 - d_pos_fp / 3.0, 0.0, 1.0).astype(np.float32)

    dom_idx = np.flatnonzero(domain_fp)
    d_dom = d_pos_fp[dom_idx]
    near_sel = d_dom <= 3.0
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
    w_reg = np.concatenate([
        np.ones(near_idx.size, dtype=np.float64),
        np.full(sub_zero.size, w_zero, dtype=np.float64),
    ])
    seq = np.argsort(train_idx)
    train_idx = train_idx[seq]
    w_reg = w_reg[seq]

    X_tr = adhr.gather_columns(list(sources), train_idx)
    yc_tr = y_cell_all[train_idx]
    yk_tr = y_kern_all[train_idx]
    d_tr = d_pos_fp[train_idx]
    del d_pos_fp, y_cell_all, y_kern_all

    # Classifier excludes ambiguous 0 < d <= dejitter_collar_px cartographic flank pixels
    cls_keep = (yc_tr == 1) | (d_tr > dejitter_collar_px)
    perm = rng.permutation(len(train_idx))
    X_tr = X_tr[perm]
    yc_tr = yc_tr[perm]
    yk_tr = yk_tr[perm]
    w_reg = w_reg[perm]
    cls_keep = cls_keep[perm]

    clf = LGBMClassifier(
        n_estimators=180,
        learning_rate=0.06,
        num_leaves=47,
        min_child_samples=80,
        subsample=0.85,
        subsample_freq=1,
        colsample_bytree=0.78,
        reg_alpha=1.5,
        reg_lambda=6.0,
        random_state=seed + 13,
        n_jobs=2,
        verbose=-1,
    )
    clf.fit(X_tr[cls_keep], yc_tr[cls_keep], sample_weight=w_reg[cls_keep])

    reg = LGBMRegressor(
        n_estimators=180,
        learning_rate=0.06,
        num_leaves=47,
        min_child_samples=80,
        subsample=0.85,
        subsample_freq=1,
        colsample_bytree=0.78,
        reg_alpha=1.5,
        reg_lambda=6.0,
        random_state=seed + 97,
        n_jobs=2,
        verbose=-1,
    )
    reg.fit(X_tr, yk_tr, sample_weight=w_reg)
    del X_tr, yc_tr, yk_tr, w_reg, cls_keep
    gc.collect()
    return clf, reg


def predict_lgbm_dual_chunked(
    clf: LGBMClassifier,
    reg: LGBMRegressor,
    sources: Sequence[np.ndarray],
    row_idx: np.ndarray,
    chunk_size: int = 120_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Chunked float32 prediction (< 60 MB transient buffer)."""
    n = int(row_idx.size)
    p_out = np.empty(n, dtype=np.float32)
    m_out = np.empty(n, dtype=np.float32)
    src_list = list(sources)
    for start in range(0, n, chunk_size):
        sl = slice(start, min(start + chunk_size, n))
        X_ch = adhr.gather_columns(src_list, row_idx[sl])
        p_ch = clf.predict_proba(X_ch)[:, 1].astype(np.float32)
        m_ch = np.clip(reg.predict(X_ch).astype(np.float32), p_ch, 1.0)
        p_out[sl] = np.clip(p_ch, 1e-6, 1.0 - 1e-6)
        m_out[sl] = m_ch
        del X_ch
    return p_out, m_out


def allocate_h33_three_stratum(
    p_near_grid: np.ndarray,
    m_near_grid: np.ndarray,
    p_pied_grid: np.ndarray,
    m_pied_grid: np.ndarray,
    p_blind_grid: np.ndarray,
    m_blind_grid: np.ndarray,
    allowed_base: np.ndarray,
    d_ref_grid: np.ndarray,
    total_budget: int,
    k_truth_est: float,
    min_spacing_px: float = 2.85,
    shares: tuple[float, float, float] = (0.18, 0.36, 0.46),
    dinkelbach_iters: int = 5,
    candidate_cap: int = 90_000,
) -> tuple[np.ndarray, dict]:
    """Allocate dots across H33-forensic 3 completeness strata with seam-safe spacing.

    Strata:
      1. Near-tip relay extension : ``2.0 < d <= 9.0 px``  (default 18%)
      2. Outboard piedmont/bajada : ``9.0 < d <= 25.0 px`` (default 36%)
      3. Blind basin interior     : ``d > 25.0 px``        (default 46%, >= 35% gate)
    """
    f1, f2, f3 = shares
    assert abs((f1 + f2 + f3) - 1.0) < 1e-6
    b1 = int(round(total_budget * f1))
    b2 = int(round(total_budget * f2))
    b3 = int(total_budget - b1 - b2)

    m1 = allowed_base & (d_ref_grid > 2.0) & (d_ref_grid <= 9.0)
    a1 = emit.dinkelbach_allocate(
        p_near_grid,
        m_near_grid,
        m1,
        budget=b1,
        k_truth=max(k_truth_est * f1, 20.0),
        min_spacing_px=min_spacing_px,
        candidate_cap=min(candidate_cap, 55_000),
        dinkelbach_iters=dinkelbach_iters,
    )
    dots = a1.emitted > 0

    lock1 = _dilate_spacing_mask(dots, min_spacing_px)
    m2 = allowed_base & (d_ref_grid > 9.0) & (d_ref_grid <= 25.0) & (~lock1)
    a2 = emit.dinkelbach_allocate(
        p_pied_grid,
        m_pied_grid,
        m2,
        budget=b2,
        k_truth=max(k_truth_est * f2, 20.0),
        min_spacing_px=min_spacing_px,
        candidate_cap=candidate_cap,
        dinkelbach_iters=dinkelbach_iters,
    )
    dots |= a2.emitted > 0

    lock12 = _dilate_spacing_mask(dots, min_spacing_px)
    # Any shortfall in S1/S2 rolls into blind basin so share_gt25 only increases
    b3_eff = max(b3, int(total_budget - int(dots.sum())))
    m3 = allowed_base & (d_ref_grid > 25.0) & (~lock12)
    a3 = emit.dinkelbach_allocate(
        p_blind_grid,
        m_blind_grid,
        m3,
        budget=b3_eff,
        k_truth=max(k_truth_est * f3, 20.0),
        min_spacing_px=min_spacing_px,
        candidate_cap=candidate_cap,
        dinkelbach_iters=dinkelbach_iters,
    )
    dots |= a3.emitted > 0

    emitted = dots.astype(np.float32)
    n_tot = int(dots.sum())
    n_s1 = int((dots & (d_ref_grid <= 9.0)).sum())
    n_s2 = int((dots & (d_ref_grid > 9.0) & (d_ref_grid <= 25.0)).sum())
    n_s3 = int((dots & (d_ref_grid > 25.0)).sum())
    return emitted, {
        "n_dots": n_tot,
        "n_stratum1_2to9px": n_s1,
        "n_stratum2_9to25px": n_s2,
        "n_stratum3_gt25px": n_s3,
        "share_le2": float((dots & (d_ref_grid <= 2.0)).sum() / max(n_tot, 1)),
        "share_gt25": float(n_s3 / max(n_tot, 1)),
    }
