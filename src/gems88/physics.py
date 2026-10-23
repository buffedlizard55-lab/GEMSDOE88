"""Memory-bounded (<500 MB RSS), label-blind geophysical, hydrothermal & 3DEP features.

Writes directly into a disk-backed float32 ``np.memmap`` aligned with
``np.nonzero(grid.footprint)`` (5,167,373 rows x 44 columns = 909 MB on disk,
~0 MB anonymous RSS) using pure float32 bilinear footprint sampling.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import io
import json
import math
import struct
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as crs_transform
from scipy import ndimage as ndi

from .edge import clean_band

TAN_60 = math.tan(math.radians(60.0))

EXPECTED_TRAINING_BANDS: dict[int, str] = {
    1: "mag_anom",
    2: "rtp",
    3: "tmi_hg",
    4: "geod_2ndinv",
    5: "iso_grav_anom_slope",
    6: "tc",
    7: "geod_shearrate",
    8: "geod_dilaterate",
    9: "tmi_vg",
    10: "deq_n100a15",
    11: "iso_grav_anom_vg",
    12: "det_elev",
    13: "iso_grav_anom",
    14: "tmi",
    15: "depth_to_base_surf",
    16: "ieq_n100a15",
    17: "cond_surf",
    18: "iso_grav_anom_hg",
    19: "det_elev_slope",
}

CGO_FEATURES: tuple[str, ...] = (
    "rtp_grad_200m",
    "rtp_grad_800m",
    "grav_grad_200m",
    "grav_grad_800m",
    "aligned_dip_edge_300m",
    "aligned_dip_edge_1000m",
    "dip_grav_step_60deg",
    "dip_mag_step_60deg",
    "dip_grav_vg_60deg",
    "dip_cond_edge_60deg",
    "cond_surf_raw",
    "cond_edge_300m",
    "cond_grav_xgrad",
    "iso_grav_hg_signed",
    "iso_grav_vg",
    "tmi_hg_log",
    "tmi_vg",
    "mag_tc",
    "depth_to_base_log",
    "piedmont_transition",
    "det_elev",
    "det_elev_slope",
    "det_elev_curv",
    "geod_strain_2ndinv",
    "geod_transtension",
    "seismic_prox",
)

EXT_PHYS_FEATURES: tuple[str, ...] = (
    "probe2m_dab_local",
    "probe2m_dab_reg",
    "paleo_sinter_prox",
    "well_temp_anom",
    "well_geotherm_qtz",
    "hydro_upslope_feeder",
    "volcanic_vent_prox",
    "rad_k_over_th",
    "mag_demag_trough",
    "lidar_has_cov",
    "lidar_scarp_dipole",
    "lidar_scarp_coh",
    "topo10_slope_p90",
    "topo10_curv_prof",
    "topo10_hs_lineament",
    "chi_step_max",
    "ksn_jump_norm",
    "pluvial_shoreline_pen",
)

ALL_PHYS_FEATURES: tuple[str, ...] = CGO_FEATURES + EXT_PHYS_FEATURES


def _grad_f32(arr: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    a = np.asarray(arr, dtype=np.float32)
    gy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 0), mode="nearest")
    gx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 1), mode="nearest")
    mag = np.hypot(gx, gy)
    return gy, gx, mag


def _bilinear_at_fp(
    field: np.ndarray,
    ys_fp: np.ndarray,
    xs_fp: np.ndarray,
    dy_fp: np.ndarray,
    dx_fp: np.ndarray,
) -> np.ndarray:
    """Zero-overhead float32 bilinear sampling directly at footprint coordinates."""
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


def _read_dbf_records(dbf_bytes: bytes) -> list[dict[str, str]]:
    num_rec, hdr_len, rec_len = struct.unpack("<IHH", dbf_bytes[4:12])
    fields: list[tuple[str, int]] = []
    pos = 32
    while pos < hdr_len - 1 and dbf_bytes[pos] != 0x0D:
        fname = dbf_bytes[pos : pos + 11].split(b"\x00", 1)[0].decode("ascii", "replace")
        flen = dbf_bytes[pos + 16]
        fields.append((fname, flen))
        pos += 32
    records: list[dict[str, str]] = []
    offset = hdr_len
    for _ in range(num_rec):
        if offset >= len(dbf_bytes):
            break
        flag = dbf_bytes[offset]
        offset += 1
        row: dict[str, str] = {}
        cur = offset
        for fn, fl in fields:
            row[fn] = dbf_bytes[cur : cur + fl].decode("latin1", "replace").strip()
            cur += fl
        offset += rec_len - 1
        if flag != 0x2A:
            records.append(row)
    return records


def _splat_points(
    shape: tuple[int, int],
    rows: np.ndarray,
    cols: np.ndarray,
    weights: np.ndarray,
    sigma_px: float,
    normalize_density: bool = False,
) -> np.ndarray:
    h, w = shape
    ok = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w) & np.isfinite(weights)
    num = np.zeros(shape, dtype=np.float32)
    cnt = np.zeros(shape, dtype=np.float32)
    if np.any(ok):
        rr = rows[ok].astype(np.int32)
        cc = cols[ok].astype(np.int32)
        ww = weights[ok].astype(np.float32)
        np.add.at(num, (rr, cc), ww)
        np.add.at(cnt, (rr, cc), 1.0)
    num_s = ndi.gaussian_filter(num, sigma=sigma_px, mode="constant")
    cnt_s = ndi.gaussian_filter(cnt, sigma=sigma_px, mode="constant")
    if normalize_density:
        support = cnt_s / (cnt_s + np.float32(0.02 / (sigma_px * sigma_px + 1.0)))
        return (np.divide(num_s, cnt_s, out=np.zeros_like(num_s), where=cnt_s > 1e-8) * support).astype(np.float32)
    return num_s.astype(np.float32)


def build_or_load_physics_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict[str, str], dict[str, str]]:
    """Build or reload disk-backed ``(N_fp, 44)`` float32 memmap with < 420 MB RSS."""
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    n_fp = ys.size
    n_cols = len(ALL_PHYS_FEATURES)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / "x_phys_44ch.dat"
    meta_path = cache_dir / "x_phys_44ch.json"

    feat_path = root / "data/training_features.tif"
    ext = root / "data/external"
    ext_names = (
        "2m_temperature_probe_INGENIOUS_regional_data.zip",
        "paleo_geothermal_regional.zip",
        "gdr_wellspring_in_footprint.csv",
        "gdr_volcanic_vents_in_footprint.csv",
        "trace_segments_utm11.csv",
        "lidar_scarp_features_u8.tif",
        "geodawn_rad_u8.tif",
        "geodawn_extensions_u8.tif",
        "topo_10m_derived_100m_u8.tif",
        "dem10_chi_100m_i16.tif",
    )
    ext_hashes = {nm: hashlib.sha256((ext / nm).read_bytes()).hexdigest() for nm in ext_names}

    if dat_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(ALL_PHYS_FEATURES)
            and meta.get("ext_hashes") == ext_hashes
        ):
            mm = np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols))
            return mm, meta["band_tags"], ext_hashes

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    band_tags: dict[str, str] = {}

    with rasterio.open(feat_path) as src:
        if (src.height, src.width) != grid.shape or src.crs != grid.crs or src.transform != grid.transform:
            raise ValueError("training_features.tif grid mismatch")
        if src.count != 19:
            raise ValueError(f"expected 19 bands, got {src.count}")
        for idx, want_tag in EXPECTED_TRAINING_BANDS.items():
            got = src.tags(idx).get("band_name", "")
            if got != want_tag:
                raise ValueError(f"band {idx}: expected {want_tag!r}, got {got!r}")
            band_tags[str(idx)] = got

        def rd(idx: int) -> np.ndarray:
            return clean_band(src.read(idx), fp)[0]

        rtp = rd(2)
        grav = rd(13)
        zbase_m = np.maximum(rd(15), 0.0)

        rgy2, rgx2, rmag2 = _grad_f32(rtp, 2.0)
        rgy8, rgx8, rmag8 = _grad_f32(rtp, 8.0)
        del rtp
        ggy2, ggx2, gmag2 = _grad_f32(grav, 2.0)
        ggy8, ggx8, gmag8 = _grad_f32(grav, 8.0)
        del grav

        mm[:, 0] = np.log1p(rmag2[ys, xs])
        mm[:, 1] = np.log1p(rmag8[ys, xs])
        mm[:, 2] = np.log1p(gmag2[ys, xs] * 100.0)
        mm[:, 3] = np.log1p(gmag8[ys, xs] * 100.0)

        cos3 = np.abs(rgx2[ys, xs] * ggx2[ys, xs] + rgy2[ys, xs] * ggy2[ys, xs]) / (rmag2[ys, xs] * gmag2[ys, xs] + 1e-6)
        cos10 = np.abs(rgx8[ys, xs] * ggx8[ys, xs] + rgy8[ys, xs] * ggy8[ys, xs]) / (rmag8[ys, xs] * gmag8[ys, xs] + 1e-6)
        mm[:, 4] = cos3 * np.sqrt(mm[:, 0] * mm[:, 2])
        mm[:, 5] = cos10 * np.sqrt(mm[:, 1] * mm[:, 3])
        del rgy2, rgx2, rmag2, rgy8, rgx8, rmag8, ggy2, ggx2, gmag2

        # 60-degree hanging-wall shift directly at footprint coordinates
        gn8_fp = gmag8[ys, xs] + 1e-6
        shift_fp = np.clip((zbase_m[ys, xs] / 100.0) / TAN_60, 0.0, 16.0).astype(np.float32)
        dy_hw_fp = (-ggy8[ys, xs] / gn8_fp) * shift_fp
        dx_hw_fp = (-ggx8[ys, xs] / gn8_fp) * shift_fp

        b5 = rd(5)
        mm[:, 6] = _bilinear_at_fp(b5, ys, xs, dy_hw_fp, dx_hw_fp)
        del b5

        b3 = rd(3)
        mm[:, 7] = np.log1p(np.maximum(_bilinear_at_fp(b3, ys, xs, dy_hw_fp, dx_hw_fp), 0.0))
        mm[:, 15] = np.log1p(np.maximum(b3[ys, xs], 0.0))
        del b3

        b11 = rd(11)
        mm[:, 8] = _bilinear_at_fp(b11, ys, xs, dy_hw_fp, dx_hw_fp)
        mm[:, 14] = b11[ys, xs]
        del b11

        cond = rd(17)
        cgy3, cgx3, cmag3 = _grad_f32(cond, 3.0)
        mm[:, 9] = _bilinear_at_fp(cmag3, ys, xs, 0.5 * dy_hw_fp, 0.5 * dx_hw_fp)
        mm[:, 10] = cond[ys, xs]
        mm[:, 11] = cmag3[ys, xs]
        mm[:, 12] = (cgx3[ys, xs] * ggx8[ys, xs] + cgy3[ys, xs] * ggy8[ys, xs]) / gn8_fp
        del cond, cgy3, cgx3, cmag3, ggy8, ggx8, gmag8, dy_hw_fp, dx_hw_fp
        gc.collect()

        mm[:, 13] = rd(18)[ys, xs]
        mm[:, 16] = rd(9)[ys, xs]
        mm[:, 17] = rd(6)[ys, xs]

        _, _, zmag = _grad_f32(zbase_m, 3.0)
        zb_fp = zbase_m[ys, xs]
        mm[:, 18] = np.log1p(zb_fp)
        mm[:, 19] = np.exp(-(((zb_fp - 350.0) / 350.0) ** 2)).astype(np.float32) * np.log1p(zmag[ys, xs] / 10.0)
        del zbase_m, zmag, zb_fp

        det = rd(12)
        det_lap = ndi.gaussian_laplace(det, sigma=2.0, mode="nearest")
        mm[:, 20] = det[ys, xs]
        mm[:, 22] = np.abs(det_lap[ys, xs])
        del det, det_lap
        mm[:, 21] = rd(19)[ys, xs]
        mm[:, 23] = rd(4)[ys, xs]
        mm[:, 24] = (rd(7)[ys, xs] * np.maximum(rd(8)[ys, xs], 0.0)).astype(np.float32)
        mm[:, 25] = (
            -np.log1p(np.maximum(rd(10)[ys, xs], 0.0) / 100.0)
            - 0.5 * np.log1p(np.maximum(rd(16)[ys, xs], 0.0) / 100.0)
        ).astype(np.float32)
        gc.collect()

    # External official datasets (columns 26..43)
    o = len(CGO_FEATURES)
    shape = grid.shape
    inv_tf = ~grid.transform

    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as ds:
        mm[:, o + 12] = ds.read(1)[ys, xs].astype(np.float32)
        mm[:, o + 13] = ds.read(6)[ys, xs].astype(np.float32)
        mm[:, o + 14] = ds.read(8)[ys, xs].astype(np.float32)
        dem_q = ds.read(9).astype(np.float32)
        t9 = ds.tags(9)
        q_lo, q_hi = float(t9["q_lo"]), float(t9["q_hi"])
        dem_m = clean_band(
            np.where(dem_q > 0, q_lo + (dem_q - 1.0) / 254.0 * (q_hi - q_lo), np.nan).astype(np.float32),
            fp,
        )[0]
        del dem_q

    dgy, dgx, dmag = _grad_f32(dem_m, 6.0)
    udown_y_fp = (-dgy[ys, xs] / (dmag[ys, xs] + 1e-4)).astype(np.float32)
    udown_x_fp = (-dgx[ys, xs] / (dmag[ys, xs] + 1e-4)).astype(np.float32)
    slope_gate_fp = np.tanh(dmag[ys, xs] / 2.5).astype(np.float32)
    del dgy, dgx, dmag

    with zipfile.ZipFile(ext / "2m_temperature_probe_INGENIOUS_regional_data.zip") as z:
        dbf_rows = _read_dbf_records(
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
            pdabs.append(max(dab, 0.0) + 0.15 * max(t2m - 20.0, 0.0))
    px_u, py_u = crs_transform("EPSG:4269", grid.crs, plons, plats)
    pcols, prows = inv_tf * (np.asarray(px_u), np.asarray(py_u))
    pw = np.asarray(pdabs, dtype=np.float32)
    probe_loc = _splat_points(shape, np.floor(prows), np.floor(pcols), pw, sigma_px=6.0, normalize_density=True)
    probe_reg = _splat_points(shape, np.floor(prows), np.floor(pcols), pw, sigma_px=22.0, normalize_density=True)
    mm[:, o + 0] = probe_loc[ys, xs]
    mm[:, o + 1] = probe_reg[ys, xs]
    del probe_reg

    with zipfile.ZipFile(ext / "paleo_geothermal_regional.zip") as z:
        p_csv = list(csv.DictReader(io.StringIO(z.read("Paleo_geothermal_final.csv").decode("utf-8-sig", "replace"))))
    slons, slats, swts = [], [], []
    for r in p_csv:
        try:
            lon, lat = float(r["Long_deg_NAD83"]), float(r["Lat_deg_NAD83"])
        except (KeyError, ValueError):
            continue
        dt = (r.get("Deposit_type") or "").lower()
        swts.append(2.0 if ("sinter" in dt or "silic" in dt) else (1.5 if "travertine" in dt else 1.0))
        slons.append(lon)
        slats.append(lat)
    sx_u, sy_u = crs_transform("EPSG:4269", grid.crs, slons, slats)
    scols, srows = inv_tf * (np.asarray(sx_u), np.asarray(sy_u))
    paleo_sinter = np.log1p(
        25.0 * _splat_points(shape, np.floor(srows), np.floor(scols), np.asarray(swts, np.float32), sigma_px=12.0)
    )
    mm[:, o + 2] = paleo_sinter[ys, xs]

    wrows, wcols, wtemp, wqtz = [], [], [], []
    with (ext / "gdr_wellspring_in_footprint.csv").open("r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                rr, cc = int(float(r["row"])), int(float(r["col"]))
            except (KeyError, ValueError):
                continue
            tc = qtz = 0.0
            try:
                if r.get("temp_c", "") not in ("", "nan", "NaN"):
                    tc = max(float(r["temp_c"]) - 20.0, 0.0)
            except ValueError:
                pass
            try:
                if r.get("geothermquartz_c", "") not in ("", "nan", "NaN"):
                    qtz = max(float(r["geothermquartz_c"]) - 90.0, 0.0)
            except ValueError:
                pass
            if tc > 0.0 or qtz > 0.0:
                wrows.append(rr)
                wcols.append(cc)
                wtemp.append(tc)
                wqtz.append(qtz)
    well_temp = np.log1p(
        _splat_points(shape, np.asarray(wrows), np.asarray(wcols), np.asarray(wtemp, np.float32), sigma_px=10.0, normalize_density=True)
    )
    well_qtz = np.log1p(
        _splat_points(shape, np.asarray(wrows), np.asarray(wcols), np.asarray(wqtz, np.float32), sigma_px=16.0, normalize_density=True)
    )
    mm[:, o + 3] = well_temp[ys, xs]
    mm[:, o + 4] = well_qtz[ys, xs]

    plume = (probe_loc + 1.5 * paleo_sinter + well_temp + 0.5 * well_qtz).astype(np.float32)
    del probe_loc, paleo_sinter, well_temp, well_qtz
    mm[:, o + 5] = slope_gate_fp * (
        0.55 * _bilinear_at_fp(plume, ys, xs, 6.0 * udown_y_fp, 6.0 * udown_x_fp)
        + 0.45 * _bilinear_at_fp(plume, ys, xs, 15.0 * udown_y_fp, 15.0 * udown_x_fp)
    )
    del plume, udown_y_fp, udown_x_fp, slope_gate_fp
    gc.collect()

    vrows, vcols = [], []
    with (ext / "gdr_volcanic_vents_in_footprint.csv").open("r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                vrows.append(int(float(r["row"])))
                vcols.append(int(float(r["col"])))
            except (KeyError, ValueError):
                continue
    mm[:, o + 6] = np.log1p(
        100.0 * _splat_points(shape, np.asarray(vrows), np.asarray(vcols), np.ones(len(vrows), np.float32), sigma_px=25.0)[ys, xs]
    )

    with rasterio.open(ext / "geodawn_rad_u8.tif") as ds:
        rk = ds.read(1)[ys, xs].astype(np.float32)
        rth = ds.read(2)[ys, xs].astype(np.float32)
    with rasterio.open(ext / "geodawn_extensions_u8.tif") as ds:
        rthk = ds.read(1)[ys, xs].astype(np.float32)
        tmi_up = ds.read(4).astype(np.float32)
    mm[:, o + 7] = (rk + 8.0) / (rth + 16.0) - 0.004 * rthk
    mm[:, o + 8] = (-ndi.gaussian_laplace(tmi_up, sigma=2.0, mode="nearest"))[ys, xs]
    del rk, rth, rthk, tmi_up

    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as ds:
        ex_m = ds.read(1)[ys, xs].astype(np.float32)
        st_m = ds.read(3)[ys, xs].astype(np.float32)
        ln_m = ds.read(4)[ys, xs].astype(np.float32)
        lp_m = ds.read(5)[ys, xs].astype(np.float32)
        rel_m = ds.read(9)[ys, xs].astype(np.float32)
        coh_m = ds.read(10)[ys, xs].astype(np.float32)
        lv = ds.read(12)[ys, xs] > 0
    mm[:, o + 9] = lv.astype(np.float32)
    mm[:, o + 10] = np.where(lv, np.sqrt(ex_m * st_m) + 0.5 * np.sqrt(ln_m * lp_m), -1.0).astype(np.float32)
    mm[:, o + 11] = np.where(lv, coh_m * np.log1p(rel_m), -1.0).astype(np.float32)
    del ex_m, st_m, ln_m, lp_m, rel_m, coh_m, lv

    with rasterio.open(ext / "dem10_chi_100m_i16.tif") as ds:
        chi_s = np.log1p(np.maximum(ds.read(1)[ys, xs].astype(np.float32), 0.0))
        ksn_s = np.log1p(np.maximum(ds.read(3)[ys, xs].astype(np.float32), 0.0))
        zm = ds.read(5)[ys, xs].astype(np.float32)
    z_use = np.where(zm > 100.0, zm, dem_m[ys, xs])
    del dem_m, zm
    shore = np.exp(-(((z_use - 1330.0) / 25.0) ** 2)) + np.exp(-(((z_use - 1555.0) / 25.0) ** 2))
    mm[:, o + 15] = chi_s
    mm[:, o + 16] = ksn_s
    mm[:, o + 17] = (shore / (1.0 + 0.35 * ksn_s)).astype(np.float32)
    del chi_s, ksn_s, z_use, shore
    mm.flush()

    for j in range(n_cols):
        if not np.isfinite(mm[:, j]).all():
            raise AssertionError(f"Non-finite values in column {ALL_PHYS_FEATURES[j]}")

    meta_path.write_text(
        json.dumps(
            {
                "shape": [n_fp, n_cols],
                "features": list(ALL_PHYS_FEATURES),
                "band_tags": band_tags,
                "ext_hashes": ext_hashes,
            },
            indent=2,
        )
        + "\n"
    )
    del mm
    gc.collect()
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), band_tags, ext_hashes
