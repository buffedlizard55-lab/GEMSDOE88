"""H88-BGCD: Blind-Geothermal Geochemical-Disequilibrium, Tufa-Decontaminated
Outflow Back-Projection, GeoDAWN 400 m Flight-Line-Notched Upward-Continuation &
Active Slip-Deficit Structural Conduit Synthesis.

Scientific summary
------------------
Roughly 75% of Great Basin geothermal systems are blind (lack Quaternary surface
fault scarps due to rapid alluvial-fan aggradation; Faulds et al., 2016, 2021).
However, deep thermal fluids leaking into shallow alluvial aquifers preserve
high Na-K-Ca cation (`geothermcat_c`) and chalcedony/quartz silica
(`geothermchalc_c`, `geothermquartz_c`) equilibration temperatures (120-265 C)
inside cool or warm valley wells and springs (`temp_c` 15-45 C). Prior lanes in
`GEMSDOE88` (`physics.py`) omitted `geothermcat_c` and `geothermchalc_c`
entirely, conflated 158 Pleistocene Lake Lahontan wave-agitated shoreline `Tufa`
records in `Paleo_geothermal_final.csv` with true hydrothermal sinter, and did
not notch the 400 m (4 px) N90E traverse-line levelling corrugation documented
in USGS GeoDAWN Contract G16PC00016 (`GeoDAWN_report.txt`) or exploit Quaternary
fault slip rates (`slip_mm_yr` in `trace_segments_utm11.csv`).

Memory & Leakage Discipline
---------------------------
* Strictly disk-backed `float32` memmaps (`< 550 MB` RSS, safe on 0-swap hosts).
* Scrubs `-FLT_MAX` (`abs(x) > 1e20`) boundary sentinels (`IR-88-94`).
* Never reads `dist_known_fault_px` from `gdr_wellspring_in_footprint.csv`.
* Masks `slip_mm_yr` strictly to `visible` faults inside every holdout fold.
* Uses Band 12 (`det_elev`) for scarp geometry (`IR-88-110` fix).
"""
from __future__ import annotations

import csv
import gc
import hashlib
import io
import json
import zipfile
from pathlib import Path

import lightgbm as lgb
import numpy as np
import rasterio
from rasterio.warp import transform as crs_transform
from scipy import ndimage as ndi

from gems57 import damagezone_envelope, emit

from . import adhr, physics

BGCD_SCHEMA_VERSION = "gems88-bgcd-v1"

BGCD_BLIND_FEATURES: tuple[str, ...] = (
    "bgcd_diseq_local",            # 0: sigma=9 px density-norm blind Delta_T = max(T_cat,T_chalc,0.85*T_qtz)-max(T_meas,15)
    "bgcd_diseq_regional",         # 1: sigma=24 px regional blind geochemical outflow anomaly
    "bgcd_upgrad_backproj",        # 2: 1.0/2.2/3.6 km up-piezometric-gradient back-projection onto buried piedmont steps
    "bgcd_sinter_pure_vs_tufa",    # 3: pure silica sinter/explosion/travertine minus Lahontan shoreline tufa mimic
    "bgcd_rad_redox_asymmetry",    # 4: cross-strike U/Th + K/Th epithermal alteration step vs felsic tuff background
    "bgcd_clay_cap_conduit_conj",  # 5: high-pass MT cond_surf x |grad depth_to_base_surf| x thermal support (anti-playa)
    "bgcd_rtp_notched_grad",       # 6: GeoDAWN 400 m (4 px) E-W traverse-notched RTP horizontal gradient
    "bgcd_up150_decay_index",      # 7: TMI_up150 vs notched RTP upward-continuation persistence (basement vs float)
    "bgcd_det_elev_frangi_max",    # 8: multi-scale Frangi 1D ridgeness on corrected B12 det_elev + LiDAR coh100
    "bgcd_grav_mt_frangi_joint",   # 9: strike-aligned Frangi vesselness of B5 gravity slope and |grad B17 cond_surf|
    "bgcd_transtension_dilat_shear",  # 10: B7 shear * B8 dilatation * B4 2ndinv gated by basement-conduit linearity
    "bgcd_piedmont_chi_raised_step",  # 11: dem10_chi raised/knick channel step coupled to |grad B15| (anti-avulsion)
    "bgcd_lahontan_playa_suppressor", # 12: explicit non-fault mimic index (Lahontan shorelines + flat deep playa + 4px E-W ripple)
)

BGCD_VIS_FEATURES: tuple[str, ...] = (
    "vis_slip_tip_propagation",    # 0: along-strike elastic tip propagation of fold-visible slip_mm_yr
    "vis_slip_stress_shadow",      # 1: broadside elastic stress-drop shadow of fold-visible slip_mm_yr
    "vis_slip_relay_transfer",     # 2: stepover relay transfer weighted by fold-visible slip_mm_yr
)


def _frangi_2d(field: np.ndarray, sigmas: tuple[float, ...], beta: float = 0.5) -> np.ndarray:
    """Memory-bounded pure-float32 multi-scale 2D Frangi ridge/vesselness filter in [0, 1]."""
    f = np.asarray(field, dtype=np.float32)
    best = np.zeros(f.shape, dtype=np.float32)
    inv_2b2 = np.float32(1.0 / (2.0 * beta * beta))
    half = np.float32(0.5)
    two = np.float32(2.0)
    one = np.float32(1.0)
    zero = np.float32(0.0)
    for s in sigmas:
        s2 = np.float32(s * s)
        hyy = ndi.gaussian_filter(f, sigma=s, order=(2, 0), mode="nearest") * s2
        hxx = ndi.gaussian_filter(f, sigma=s, order=(0, 2), mode="nearest") * s2
        hyx = ndi.gaussian_filter(f, sigma=s, order=(1, 1), mode="nearest") * s2
        tr = hyy + hxx
        disc = np.hypot(hyy - hxx, two * hyx)
        del hyy, hxx, hyx
        l1 = half * (tr + disc)
        l2 = half * (tr - disc)
        del tr, disc
        swap = np.abs(l1) > np.abs(l2)
        lam1 = np.where(swap, l2, l1)
        lam2 = np.where(swap, l1, l2)
        del l1, l2, swap

        denom = np.where(np.abs(lam2) > np.float32(1e-6), lam2, one)
        rb2 = (lam1 / denom) ** 2
        s_norm2 = lam1 * lam1 + lam2 * lam2
        neg = lam2 < zero
        del lam1, lam2, denom
        pos_s = s_norm2[neg]
        c2 = np.float32(max(float(np.percentile(pos_s, 75)) if pos_s.size else 1.0, 1e-6))
        del pos_s
        v = np.where(
            neg,
            np.exp(-rb2 * inv_2b2) * (one - np.exp(-s_norm2 / (two * c2))),
            zero,
        ).astype(np.float32)
        np.maximum(best, v, out=best)
        del rb2, s_norm2, neg, v
        gc.collect()
    return best


def _structure_strike_cos2(
    gy_a: np.ndarray, gx_a: np.ndarray, gy_b: np.ndarray, gx_b: np.ndarray
) -> np.ndarray:
    """Spin-2 gradient/strike alignment cos(2*(theta_a - theta_b)) in [0, 1]."""
    na = np.hypot(gy_a, gx_a) + 1e-6
    nb = np.hypot(gy_b, gx_b) + 1e-6
    dot = (gy_a * gy_b + gx_a * gx_b) / (na * nb)
    return (dot * dot).astype(np.float32)


def build_or_load_bgcd_blind_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict[str, str]]:
    """Build or reload disk-backed ``(N_fp, 13)`` float32 label-blind BGCD memmap."""
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    n_fp = ys.size
    n_cols = len(BGCD_BLIND_FEATURES)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / "x_bgcd_13ch.dat"
    meta_path = cache_dir / "x_bgcd_13ch.json"

    feat_path = root / "data/training_features.tif"
    ext = root / "data/external"
    ext_files = (
        "gdr_wellspring_in_footprint.csv",
        "paleo_geothermal_regional.zip",
        "2m_temperature_probe_INGENIOUS_regional_data.zip",
        "geodawn_rad_u8.tif",
        "geodawn_extensions_u8.tif",
        "lidar_scarp_features_u8.tif",
        "topo_10m_derived_100m_u8.tif",
        "dem10_chi_100m_i16.tif",
        "dem10_chi_100m_u8.tif",
    )
    hashes = {nm: hashlib.sha256((ext / nm).read_bytes()).hexdigest() for nm in ext_files}

    if dat_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("schema") == BGCD_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(BGCD_BLIND_FEATURES)
            and meta.get("ext_hashes") == hashes
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), hashes

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    shape = grid.shape
    inv_tf = ~grid.transform

    # --- 1. Elevation, basement depth, and piezometric/topographic gradient ---
    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as ds:
        slope_p90_u8 = ds.read(1).astype(np.float32)
        dem_q = ds.read(9).astype(np.float32)
        t9 = ds.tags(9)
        q_lo, q_hi = float(t9["q_lo"]), float(t9["q_hi"])
        dem_m = physics.clean_band(
            np.where(dem_q > 0, q_lo + (dem_q - 1.0) / 254.0 * (q_hi - q_lo), np.nan).astype(np.float32),
            fp,
        )[0]
        del dem_q

    with rasterio.open(ext / "dem10_chi_100m_i16.tif") as ds:
        step_max = np.maximum(ds.read(1).astype(np.float32), 0.0)
        ksn_max = np.maximum(ds.read(3).astype(np.float32), 0.0)
        area_log = ds.read(4).astype(np.float32)
        zm = ds.read(5).astype(np.float32)
    z_m = np.where(zm > 100.0, zm, dem_m).astype(np.float32)
    del dem_m, zm

    with rasterio.open(feat_path) as src:
        for idx, want_tag in physics.EXPECTED_TRAINING_BANDS.items():
            got = src.tags(idx).get("band_name", "")
            if got != want_tag:
                raise ValueError(f"training_features band {idx}: expected {want_tag!r}, got {got!r}")
        zbase_m = np.maximum(physics.clean_band(src.read(15), fp)[0], 0.0)
        cond_surf = physics.clean_band(src.read(17), fp)[0]

    _, _, zbase_grad = physics._grad_f32(zbase_m, 3.0)
    dgy, dgx, dmag = physics._grad_f32(z_m, 8.0)
    udown_y_fp = (-dgy[ys, xs] / (dmag[ys, xs] + 1e-4)).astype(np.float32)
    udown_x_fp = (-dgx[ys, xs] / (dmag[ys, xs] + 1e-4)).astype(np.float32)
    piedmont_gate_fp = (
        np.tanh(dmag[ys, xs] / 2.0)
        * np.exp(-(((zbase_m[ys, xs] - 420.0) / 550.0) ** 2))
    ).astype(np.float32)
    del dgy, dgx, dmag

    # --- 2. Blind-Geothermal Geochemical Disequilibrium (never reading dist_known_fault_px) ---
    ALLOWED_WELL_COLS = {
        "row", "col", "layer", "thermalclass",
        "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c",
    }
    w_r, w_c, w_diseq, w_reg, w_hot = [], [], [], [], []
    with (ext / "gdr_wellspring_in_footprint.csv").open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            rec = {k: raw_row[k] for k in ALLOWED_WELL_COLS if k in raw_row}
            assert "dist_known_fault_px" not in rec
            try:
                rr, cc = int(float(rec["row"])), int(float(rec["col"]))
            except (KeyError, ValueError):
                continue

            def _num(key: str) -> float | None:
                val = rec.get(key, "")
                if val in ("", "nan", "NaN", "NULL", None):
                    return None
                try:
                    v = float(val)
                    return v if np.isfinite(v) else None
                except ValueError:
                    return None

            t_meas = _num("temp_c")
            t_qtz = _num("geothermquartz_c")
            t_chl = _num("geothermchalc_c")
            t_cat = _num("geothermcat_c")

            eq_candidates = [0.0]
            if t_cat is not None and t_cat > 50.0:
                eq_candidates.append(t_cat)
            if t_chl is not None and t_chl > 50.0:
                eq_candidates.append(t_chl)
            if t_qtz is not None and t_qtz > 60.0:
                eq_candidates.append(0.85 * t_qtz)
            t_eq = max(eq_candidates)
            t_surf = max(t_meas, 15.0) if t_meas is not None else 22.0
            diseq = max(t_eq - t_surf, 0.0) if t_eq >= 80.0 else 0.0

            tclass = (rec.get("thermalclass") or "").strip().lower()
            hot_w = 25.0 if tclass == "hot" else (10.0 if tclass == "warm" else 0.0)
            if t_meas is not None and t_meas > 30.0:
                hot_w = max(hot_w, min(t_meas - 25.0, 120.0))

            reg_w = diseq + 0.45 * max((t_cat or 0.0) - 90.0, 0.0) + 0.35 * hot_w
            if diseq > 0.0 or reg_w > 0.0:
                w_r.append(rr)
                w_c.append(cc)
                w_diseq.append(diseq)
                w_reg.append(reg_w)
                w_hot.append(diseq + 0.6 * hot_w)

    wr_arr = np.asarray(w_r, dtype=np.float32)
    wc_arr = np.asarray(w_c, dtype=np.float32)
    diseq_loc = np.log1p(
        physics._splat_points(shape, wr_arr, wc_arr, np.asarray(w_diseq, np.float32), sigma_px=9.0, normalize_density=True)
    )
    diseq_reg = np.log1p(
        physics._splat_points(shape, wr_arr, wc_arr, np.asarray(w_reg, np.float32), sigma_px=24.0, normalize_density=True)
    )
    outflow_src = np.log1p(
        physics._splat_points(shape, wr_arr, wc_arr, np.asarray(w_hot, np.float32), sigma_px=11.0, normalize_density=True)
    )
    mm[:, 0] = diseq_loc[ys, xs]
    mm[:, 1] = diseq_reg[ys, xs]
    del diseq_loc, wr_arr, wc_arr, w_r, w_c, w_diseq, w_reg, w_hot

    # --- 3. Tufa-Decontaminated Paleo-Geothermal Deposits & Hydraulic Back-Projection ---
    with zipfile.ZipFile(ext / "paleo_geothermal_regional.zip") as z:
        p_rows = list(csv.DictReader(io.StringIO(z.read("Paleo_geothermal_final.csv").decode("utf-8-sig", "replace"))))
    h_lons, h_lats, h_wts = [], [], []
    t_lons, t_lats, t_wts = [], [], []
    for r in p_rows:
        try:
            lon, lat = float(r["Long_deg_NAD83"]), float(r["Lat_deg_NAD83"])
        except (KeyError, ValueError):
            continue
        dt = (r.get("Deposit_type") or "").strip().lower()
        if "tufa" in dt:
            t_lons.append(lon)
            t_lats.append(lat)
            t_wts.append(2.0 if dt == "tufa" else 1.2)
        else:
            w = (
                2.5 if ("sinter" in dt or "explosion" in dt or "sulfur" in dt)
                else (1.5 if ("silic" in dt or "alteration" in dt) else 1.2)
            )
            h_lons.append(lon)
            h_lats.append(lat)
            h_wts.append(w)

    hx, hy = crs_transform("EPSG:4269", grid.crs, h_lons, h_lats)
    hc, hr = inv_tf * (np.asarray(hx), np.asarray(hy))
    sinter_pure = np.log1p(
        25.0 * physics._splat_points(shape, np.floor(hr), np.floor(hc), np.asarray(h_wts, np.float32), sigma_px=10.0)
    )

    tx, ty = crs_transform("EPSG:4269", grid.crs, t_lons, t_lats)
    tc_px, tr_px = inv_tf * (np.asarray(tx), np.asarray(ty))
    tufa_mimic = np.log1p(
        25.0 * physics._splat_points(shape, np.floor(tr_px), np.floor(tc_px), np.asarray(t_wts, np.float32), sigma_px=10.0)
    )

    shore_band = (
        np.exp(-(((z_m - 1330.0) / 35.0) ** 2))
        + np.exp(-(((z_m - 1555.0) / 35.0) ** 2))
    ).astype(np.float32)

    mm[:, 3] = (sinter_pure[ys, xs] - 0.85 * tufa_mimic[ys, xs] * (0.35 + 0.65 * shore_band[ys, xs])).astype(np.float32)

    combined_outflow = (outflow_src + 1.25 * sinter_pure).astype(np.float32)
    mm[:, 2] = piedmont_gate_fp * (
        0.40 * physics._bilinear_at_fp(combined_outflow, ys, xs, 10.0 * udown_y_fp, 10.0 * udown_x_fp)
        + 0.35 * physics._bilinear_at_fp(combined_outflow, ys, xs, 22.0 * udown_y_fp, 22.0 * udown_x_fp)
        + 0.25 * physics._bilinear_at_fp(combined_outflow, ys, xs, 36.0 * udown_y_fp, 36.0 * udown_x_fp)
    )
    del outflow_src, sinter_pure, combined_outflow, udown_y_fp, udown_x_fp, piedmont_gate_fp

    # --- 4. Radiometric Redox/Potassic Alteration Step & Anti-Playa Clay-Cap Conduit ---
    with rasterio.open(ext / "geodawn_rad_u8.tif") as ds:
        rad_k = ds.read(1).astype(np.float32)
        rad_th = ds.read(2).astype(np.float32)
        rad_tc = ds.read(4).astype(np.float32)
    with rasterio.open(ext / "geodawn_extensions_u8.tif") as ds:
        rad_uk = ds.read(2).astype(np.float32)
        rad_uth = ds.read(3).astype(np.float32)
        tmi_up150 = physics.clean_band(ds.read(4).astype(np.float32), fp)[0]

    alt_potassic_redox = (
        (rad_k + 8.0) / (rad_th + 16.0)
        + 0.008 * rad_uth
        + 0.004 * rad_uk
        - 0.00012 * (rad_th * rad_tc)
    ).astype(np.float32)
    del rad_k, rad_th, rad_tc, rad_uk, rad_uth
    _, _, alt_grad = physics._grad_f32(alt_potassic_redox, 2.5)
    mm[:, 4] = np.log1p(alt_grad[ys, xs] * 10.0).astype(np.float32)
    del alt_potassic_redox, alt_grad

    # High-pass shallow MT conductivity (suppresses regional flat playa salt pans)
    cond_log = np.log1p(np.maximum(cond_surf, 0.0)).astype(np.float32)
    cond_hp = np.maximum(cond_log - ndi.gaussian_filter(cond_log, sigma=28.0, mode="nearest"), 0.0)
    mm[:, 5] = (
        cond_hp[ys, xs]
        * np.log1p(zbase_grad[ys, xs] / 8.0)
        * (0.35 + 0.65 * np.tanh(0.45 * diseq_reg[ys, xs]))
    ).astype(np.float32)
    del cond_log, cond_hp, diseq_reg
    gc.collect()

    # --- 5. GeoDAWN 400 m (4 px) E-W Traverse-Line Notch & TMI_up150 Persistence ---
    with rasterio.open(feat_path) as src:
        rtp = physics.clean_band(src.read(2), fp)[0]
        geod_2nd = physics.clean_band(src.read(4), fp)[0]
        grav_slope = physics.clean_band(src.read(5), fp)[0]
        geod_shear = physics.clean_band(src.read(7), fp)[0]
        geod_dilat = physics.clean_band(src.read(8), fp)[0]
        det_elev = physics.clean_band(src.read(12), fp)[0]
        det_slope = physics.clean_band(src.read(19), fp)[0]

    # Isolate 4-px N-S oscillation along E-W flight traverses (sigma_y=1.1 vs sigma_y=3.2 smoothed along x)
    ew_ripple = ndi.gaussian_filter(
        ndi.gaussian_filter(rtp, sigma=(1.0, 8.0), mode="nearest")
        - ndi.gaussian_filter(rtp, sigma=(3.2, 8.0), mode="nearest"),
        sigma=(0.8, 4.0),
        mode="nearest",
    )
    rtp_notched = (rtp - ew_ripple).astype(np.float32)
    ripple_energy = np.log1p(np.abs(ew_ripple)).astype(np.float32)
    del rtp, ew_ripple

    _, _, rtp_n_g2 = physics._grad_f32(rtp_notched, 2.0)
    del rtp_notched
    _, _, up150_g2 = physics._grad_f32(tmi_up150, 2.5)
    del tmi_up150

    log_rtp_g = np.log1p(rtp_n_g2)
    log_up_g = np.log1p(up150_g2 * 2.5)
    mm[:, 6] = log_rtp_g[ys, xs]
    # Upward-continuation persistence weighted by basement depth (high over deep steep faults, low over float)
    mm[:, 7] = (
        (log_up_g - 0.45 * np.maximum(log_rtp_g - log_up_g, 0.0))
        * np.tanh((zbase_m + 80.0) / 300.0)
    )[ys, xs].astype(np.float32)
    del rtp_n_g2, up150_g2, log_rtp_g, log_up_g
    gc.collect()

    # --- 6. Corrected B12 det_elev Ridgeness & Co-Aligned Gravity-MT Frangi Vesselness ---
    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as ds:
        lidar_coh = (ds.read(10).astype(np.float32) / 255.0) * (ds.read(12) > 0).astype(np.float32)

    scarp_mag = np.log1p(np.maximum(det_slope, 0.0) * 10.0) + 0.5 * np.abs(
        ndi.gaussian_laplace(det_elev, sigma=1.8, mode="nearest")
    )
    del det_elev, det_slope
    det_frangi = _frangi_2d(scarp_mag, sigmas=(1.5, 3.0, 6.0))
    mm[:, 8] = (det_frangi[ys, xs] * (1.0 + 0.35 * lidar_coh[ys, xs])).astype(np.float32)
    del scarp_mag, det_frangi, lidar_coh

    cgy, cgx, cmag = physics._grad_f32(cond_surf, 3.0)
    del cond_surf
    ggy, ggx, _ = physics._grad_f32(grav_slope, 2.5)
    align_gm = _structure_strike_cos2(ggy, ggx, cgy, cgx)
    del ggy, ggx, cgy, cgx

    grav_frangi = _frangi_2d(np.log1p(np.maximum(grav_slope, 0.0) * 100.0), sigmas=(2.0, 4.5, 8.0))
    cond_frangi = _frangi_2d(np.log1p(cmag * 20.0), sigmas=(3.0, 6.0))
    del cmag
    joint_vess = (np.sqrt(grav_frangi * cond_frangi + 1e-6) * (0.35 + 0.65 * align_gm) + 0.35 * grav_frangi).astype(np.float32)
    mm[:, 9] = joint_vess[ys, xs]
    del grav_frangi, cond_frangi, align_gm

    # Transtensional dilatation + shear strain coupled to basement structural conduit linearity
    strain_transtens = (
        np.maximum(geod_shear, 0.0) * (0.4 + np.maximum(geod_dilat, 0.0)) + 0.3 * np.maximum(geod_2nd, 0.0)
    ).astype(np.float32)
    mm[:, 10] = ( np.log1p(strain_transtens[ys, xs] * 25.0) * (0.25 + joint_vess[ys, xs]) ).astype(np.float32)
    del geod_2nd, geod_shear, geod_dilat, strain_transtens, joint_vess
    gc.collect()

    # --- 7. Piedmont Chi Raised-Channel Basement-Admittance & Explicit Mimic Suppressor ---
    with rasterio.open(ext / "dem10_chi_100m_u8.tif") as ds:
        chan_n = ds.read(1).astype(np.float32)
        knick_n = ds.read(2).astype(np.float32)
        raised_n = ds.read(3).astype(np.float32)

    area_gate = np.clip((area_log - 3800.0) / 2500.0, 0.0, 1.0).astype(np.float32)
    knick_ratio = (knick_n + 1.5 * raised_n) / (chan_n + 2.0)
    mm[:, 11] = (
        np.log1p(step_max[ys, xs] * 0.02)
        * knick_ratio[ys, xs]
        * area_gate[ys, xs]
        * np.tanh(zbase_grad[ys, xs] / 12.0)
    ).astype(np.float32)
    del chan_n, knick_n, raised_n, step_max, area_log, area_gate, knick_ratio

    # Explicit non-fault mimic index: Lahontan shoreline benches + flat deep playa pans + E-W flight ripple
    playa_flat = (
        np.exp(-((slope_p90_u8 / 18.0) ** 2))
        * np.clip((zbase_m - 900.0) / 900.0, 0.0, 1.0)
        * np.exp(-((np.maximum(grav_slope, 0.0) * 120.0) ** 2))
    ).astype(np.float32)
    lahontan_mimic = (shore_band * np.exp(-((np.log1p(ksn_max) / 2.2) ** 2)) * (0.5 + 0.5 * tufa_mimic)).astype(np.float32)
    mm[:, 12] = (lahontan_mimic[ys, xs] + playa_flat[ys, xs] + 0.35 * ripple_energy[ys, xs]).astype(np.float32)
    del slope_p90_u8, zbase_m, zbase_grad, grav_slope, z_m, ksn_max, shore_band, tufa_mimic, playa_flat, lahontan_mimic, ripple_energy
    mm.flush()

    for j in range(n_cols):
        if not np.isfinite(mm[:, j]).all():
            raise AssertionError(f"Non-finite values in BGCD column {BGCD_BLIND_FEATURES[j]}")

    meta_path.write_text(
        json.dumps(
            {
                "schema": BGCD_SCHEMA_VERSION,
                "shape": [n_fp, n_cols],
                "features": list(BGCD_BLIND_FEATURES),
                "ext_hashes": hashes,
            },
            indent=2,
        )
        + "\n"
    )
    del mm
    gc.collect()
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), hashes


def build_slip_rate_raster(trace_csv: Path, grid, cache_dir: Path) -> np.ndarray:
    """Rasterize Quaternary slip rate (mm/yr) onto catalogue cells (masked inside each fold!)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(trace_csv.read_bytes()).hexdigest()[:16]
    cpath = cache_dir / f"slip_src_{digest}.npy"
    if cpath.exists():
        return np.load(cpath)

    h, w = grid.shape
    out = np.zeros((h, w), dtype=np.float32)
    inv_tf = ~grid.transform
    with trace_csv.open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                slip = max(float(row["slip_mm_yr"]), 0.0)
                x0, y0 = float(row["x0"]), float(row["y0"])
                x1, y1 = float(row["x1"]), float(row["y1"])
            except (KeyError, ValueError):
                continue
            if not np.isfinite(slip) or slip <= 0.0:
                continue
            c0, r0 = inv_tf * (x0, y0)
            c1, r1 = inv_tf * (x1, y1)
            nsteps = max(2, int(np.hypot(c1 - c0, r1 - r0) * 1.5) + 1)
            cs = np.floor(np.linspace(c0, c1, nsteps)).astype(np.int32)
            rs = np.floor(np.linspace(r0, r1, nsteps)).astype(np.int32)
            ok = (rs >= 0) & (rs < h) & (cs >= 0) & (cs < w)
            np.maximum.at(out, (rs[ok], cs[ok]), np.float32(slip))

    out = ndi.maximum_filter(out, size=3).astype(np.float32)
    out[~grid.catalogue] = 0.0
    np.save(cpath, out)
    return out


def compute_visible_slip_fp(
    grid,
    visible: np.ndarray,
    slip_src: np.ndarray,
    X_vis22_mm: np.ndarray,
    cache_dir: Path,
    tag: str,
) -> np.memmap:
    """Compute fold-safe ``(N_fp, 3)`` float32 memmap strictly from ``visible`` slip rates."""
    vis = np.asarray(visible, dtype=bool)
    if not vis.any():
        raise ValueError("visible mask must be non-empty")
    slip_vis = np.where(vis, slip_src, 0.0).astype(np.float32)
    if np.any(slip_vis[~vis] > 0.0):
        raise AssertionError("Leakage guard triggered: non-visible slip_vis detected")

    vis_hash = hashlib.sha256(np.packbits(vis).tobytes() + slip_vis[vis].tobytes()).hexdigest()[:16]
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / f"vis_slip3_{tag}_{vis_hash}.dat"
    n_fp = int(grid.footprint.sum())
    if dat_path.exists() and dat_path.stat().st_size == n_fp * 3 * 4:
        return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, 3))

    ys, xs = np.nonzero(grid.footprint)
    inds = ndi.distance_transform_edt(~vis, return_distances=False, return_indices=True)
    s_near = np.log1p(10.0 * slip_vis[inds[0, ys, xs], inds[1, ys, xs]]).astype(np.float32)
    del inds, slip_vis
    gc.collect()

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, 3))
    for s in range(0, n_fp, 250_000):
        e = min(s + 250_000, n_fp)
        d1 = np.asarray(X_vis22_mm[s:e, 0], dtype=np.float32)
        d_perp = np.abs(np.asarray(X_vis22_mm[s:e, 1], dtype=np.float32))
        d_par = np.asarray(X_vis22_mm[s:e, 2], dtype=np.float32)
        d2 = np.asarray(X_vis22_mm[s:e, 16], dtype=np.float32)
        rf = np.asarray(X_vis22_mm[s:e, 18], dtype=np.float32)
        sn = s_near[s:e]

        mm[s:e, 0] = sn * (d_par / (d1 + 1.0)) * np.exp(-d1 / 20.0)
        mm[s:e, 1] = sn * (d_perp / (d1 + 1.0)) * np.exp(-d1 / 12.0) * np.maximum(-rf, 0.0)
        mm[s:e, 2] = sn * np.maximum(rf, 0.0) * np.exp(-0.5 * (d1 + d2) / 24.0)
    mm.flush()
    del mm, s_near
    gc.collect()
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, 3))


def fit_dual_lgbm(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    seed: int,
    max_zero_neg: int = 150_000,
) -> tuple[lgb.LGBMClassifier, lgb.LGBMRegressor]:
    """Memory-bounded Horvitz-Thompson dual (p_cell, m_kernel) LightGBM fitter."""
    ys_fp, xs_fp = np.nonzero(fp_mask)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int8)
    y_kern_grid = np.clip(1.0 - ndi.distance_transform_edt(~pos_grid) / 3.0, 0.0, 1.0).astype(np.float32)
    y_kern_all = y_kern_grid[ys_fp, xs_fp]
    del y_kern_grid

    dom_idx = np.flatnonzero(domain_fp)
    y_k = y_kern_all[dom_idx]
    near_idx = dom_idx[y_k > 0.0]
    zero_idx = dom_idx[y_k <= 0.0]

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
    del y_cell_all, y_kern_all

    perm = rng.permutation(len(train_idx))
    X_tr = X_tr[perm]
    yc_tr = yc_tr[perm]
    yk_tr = yk_tr[perm]
    weights = weights[perm]

    common = dict(
        n_estimators=220,
        num_leaves=55,
        learning_rate=0.055,
        min_child_samples=80,
        subsample=0.85,
        subsample_freq=1,
        colsample_bytree=0.80,
        reg_lambda=4.0,
        n_jobs=2,
        random_state=seed,
        verbose=-1,
    )
    clf = lgb.LGBMClassifier(objective="binary", **common)
    clf.fit(X_tr, yc_tr, sample_weight=weights)

    reg = lgb.LGBMRegressor(objective="regression", **{**common, "random_state": seed + 137})
    reg.fit(X_tr, yk_tr, sample_weight=weights)
    del X_tr, yc_tr, yk_tr, weights
    gc.collect()
    return clf, reg


def predict_dual_lgbm(
    clf: lgb.LGBMClassifier,
    reg: lgb.LGBMRegressor,
    sources: list[np.ndarray],
    act_idx: np.ndarray,
    chunk: int = 160_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Chunked dual prediction keeping peak RAM bounded."""
    n = act_idx.size
    p_out = np.empty(n, dtype=np.float32)
    m_out = np.empty(n, dtype=np.float32)
    for start in range(0, n, chunk):
        sl = slice(start, min(start + chunk, n))
        X_sub = adhr.gather_columns(sources, act_idx[sl])
        p_c = clf.predict_proba(X_sub)[:, 1].astype(np.float32)
        m_c = np.clip(reg.predict(X_sub).astype(np.float32), p_c, 1.0)
        p_out[sl] = p_c
        m_out[sl] = m_c
        del X_sub
    return p_out, m_out


def _adaptive_poe_pool(
    p_base: np.ndarray,
    m_base: np.ndarray,
    p_spec: np.ndarray,
    m_spec: np.ndarray,
    d_vis_act: np.ndarray,
    w_near: float = 0.65,
    w_far: float = 0.82,
) -> tuple[np.ndarray, np.ndarray]:
    """Distance-adaptive log-odds Product-of-Experts weighting BGCD heavier in blind basins."""
    ramp = np.clip((d_vis_act - 8.0) / 22.0, 0.0, 1.0).astype(np.float32)
    w = (np.float32(w_near) + np.float32(w_far - w_near) * ramp).astype(np.float32)
    w0 = np.float32(1.0) - w
    p_pool = adhr._expit(w0 * adhr._logit(p_base) + w * adhr._logit(p_spec))
    m_pool = np.maximum(p_pool, adhr._expit(w0 * adhr._logit(m_base) + w * adhr._logit(m_spec)))
    return p_pool, m_pool


def evaluate_bgcd_fold_arms(
    grid,
    X_phys_mm: np.ndarray,
    X_bgcd_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    X_slip3_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    cache_dir: Path,
    fold_tag: str,
) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    """Run Control (`h88_adhr_b12_ctrl`), Exp01 (`bgcd_blind_phys57`),
    Exp02 (`bgcd_slip_joint83`), and Exp03 (`h88_bgcd`, plus `h88_bgcd_strat35` diagnostic)."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: train_regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    d_vis_act = d_vis_fp[act_idx]

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    cache_npz = cache_dir / f"bgcd_post_{fold_tag}_s{seed}_{BGCD_SCHEMA_VERSION}.npz"
    if cache_npz.exists():
        post = np.load(cache_npz)
        p_p44, m_p44 = post["p_p44"], post["m_p44"]
        p_f67, m_f67 = post["p_f67"], post["m_f67"]
        p_p57, m_p57 = post["p_p57"], post["m_p57"]
        p_f83, m_f83 = post["p_f83"], post["m_f83"]
    else:
        pop_tr_fp = train_truth[ys_fp, xs_fp]
        wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
        d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

        dom_phys_tr = train_regions[ys_fp, xs_fp]
        dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]

        c44, r44 = fit_dual_lgbm([X_phys_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 11)
        p_p44, m_p44 = predict_dual_lgbm(c44, r44, [X_phys_mm], act_idx)
        del c44, r44

        c67, r67 = fit_dual_lgbm([X_phys_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 37)
        p_f67, m_f67 = predict_dual_lgbm(c67, r67, [X_phys_mm, X_vis22_mm, d_over_w_fp], act_idx)
        del c67, r67

        c57, r57 = fit_dual_lgbm([X_phys_mm, X_bgcd_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 71)
        p_p57, m_p57 = predict_dual_lgbm(c57, r57, [X_phys_mm, X_bgcd_mm], act_idx)
        del c57, r57

        c83, r83 = fit_dual_lgbm(
            [X_phys_mm, X_bgcd_mm, X_vis22_mm, X_slip3_mm, d_over_w_fp],
            dom_struct_tr,
            train_truth,
            fp,
            seed=seed + 109,
        )
        p_f83, m_f83 = predict_dual_lgbm(
            c83, r83, [X_phys_mm, X_bgcd_mm, X_vis22_mm, X_slip3_mm, d_over_w_fp], act_idx
        )
        del c83, r83, d_over_w_fp
        gc.collect()
        np.savez(
            cache_npz,
            p_p44=p_p44, m_p44=m_p44,
            p_f67=p_f67, m_f67=m_f67,
            p_p57=p_p57, m_p57=m_p57,
            p_f83=p_f83, m_f83=m_f83,
        )

    # Control: h88_adhr_b12_ctrl (44 phys + 23 vis, corrected B12 scarp)
    p_ctrl, m_ctrl = adhr._fuse_log_odds(p_f67, m_f67, p_p44, m_p44, k_est, beta_phys=0.35)
    p_ctrl_g = adhr.scatter_fp(p_ctrl, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_ctrl_g = adhr.scatter_fp(m_ctrl, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_ctrl = emit.dinkelbach_allocate(
        p_ctrl_g, m_ctrl_g, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # Exp01: bgcd_blind_phys57 (pure zero-catalogue 57-ch physical + hydrothermal BGCD)
    sc_e1 = float(k_est) / max(float(p_p57.sum()), 1e-6)
    p_e1 = np.clip(p_p57 * np.float32(sc_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_p57 * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)
    p_e1_g = adhr.scatter_fp(p_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e1_g = adhr.scatter_fp(m_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_e1 = emit.dinkelbach_allocate(
        p_e1_g, m_e1_g, allowed, budget=None, k_truth=k_est, min_spacing_px=2.35, dinkelbach_iters=6
    )

    # Exp02: bgcd_slip_joint83 (single 83-ch joint slip-structural + BGCD model)
    p_e2, m_e2 = adhr._fuse_log_odds(p_f83, m_f83, p_p57, m_p57, k_est, beta_phys=0.38)
    p_e2_g = adhr.scatter_fp(p_e2, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e2_g = adhr.scatter_fp(m_e2, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_e2 = emit.dinkelbach_allocate(
        p_e2_g, m_e2_g, allowed, budget=None, k_truth=k_est, min_spacing_px=2.35, dinkelbach_iters=6
    )

    # Exp03: h88_bgcd (distance-adaptive Log-Odds PoE pooling + ridge Dinkelbach spacing)
    p_phys_poe, m_phys_poe = _adaptive_poe_pool(p_p44, m_p44, p_p57, m_p57, d_vis_act, w_near=0.68, w_far=0.85)
    p_full_poe, m_full_poe = _adaptive_poe_pool(p_f67, m_f67, p_f83, m_f83, d_vis_act, w_near=0.68, w_far=0.85)
    p_e3, m_e3 = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_est, beta_phys=0.38)
    p_e3_g = adhr.scatter_fp(p_e3, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e3_g = adhr.scatter_fp(m_e3, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_e3 = emit.dinkelbach_allocate(
        p_e3_g, m_e3_g, allowed, budget=None, k_truth=k_est, min_spacing_px=2.35, dinkelbach_iters=6
    )

    return {
        "h88_adhr_b12_ctrl": (alloc_ctrl.emitted.astype(np.float32), p_ctrl_g, {"n_dots": alloc_ctrl.n_dots, "k_est": k_est}),
        "bgcd_blind_phys57": (alloc_e1.emitted.astype(np.float32), p_e1_g, {"n_dots": alloc_e1.n_dots, "k_est": k_est}),
        "bgcd_slip_joint83": (alloc_e2.emitted.astype(np.float32), p_e2_g, {"n_dots": alloc_e2.n_dots, "k_est": k_est}),
        "h88_bgcd": (alloc_e3.emitted.astype(np.float32), p_e3_g, {"n_dots": alloc_e3.n_dots, "k_est": k_est}),
    }


def fit_and_emit_production_bgcd(
    grid,
    X_phys_mm: np.ndarray,
    X_bgcd_mm: np.ndarray,
    sense_src: np.ndarray,
    slip_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
    seed: int = 8825,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Fit full-catalogue H88-BGCD specialists and emit a 3-regime ridge-spaced
    discrete candidate satisfying H33 basin parity (`share_le2=0`, `share_gt25>=0.35`)
    and independent multi-regime spatial support (`min_spacing_px=3.20`)."""
    fp = grid.footprint
    cat = grid.catalogue
    ys_fp, xs_fp = np.nonzero(fp)

    d_cat_grid = ndi.distance_transform_edt(~cat).astype(np.float32)
    allowed_emit = fp & ~cat & (d_cat_grid > 2.25)

    # Hold out 4 spatial tiles of known faults internally to supervise relay/slip weights cleanly
    h, w = grid.shape
    tile_r = (np.arange(h)[:, None] // 260) % 4
    tile_c = (np.arange(w)[None, :] // 260) % 4
    pseudo_hid_zone = ((tile_r + 2 * tile_c) % 7) == 0
    vis_sub = cat & ~pseudo_hid_zone
    hid_sub = cat & pseudo_hid_zone

    X_vis_sub, d_sub_fp, len_sub_fp = adhr.compute_visible_struct_fp(
        grid, vis_sub, sense_src, scarp_fields, cache_dir, "prod_bgcd_sub"
    )
    X_slip_sub = compute_visible_slip_fp(grid, vis_sub, slip_src, X_vis_sub, cache_dir, "prod_bgcd_sub")
    wlaw = damagezone_envelope.fit_width_law(len_sub_fp, d_sub_fp, hid_sub[ys_fp, xs_fp], quantile=0.90, l0_px=40.0)
    d_over_w_sub = (d_sub_fp / np.maximum(wlaw.half_width(len_sub_fp), 1e-6)).astype(np.float32)

    X_vis_full, d_full_fp, len_full_fp = adhr.compute_visible_struct_fp(
        grid, cat, sense_src, scarp_fields, cache_dir, "prod_bgcd_full"
    )
    X_slip_full = compute_visible_slip_fp(grid, cat, slip_src, X_vis_full, cache_dir, "prod_bgcd_full")
    d_over_w_full = (d_full_fp / np.maximum(wlaw.half_width(len_full_fp), 1e-6)).astype(np.float32)

    dom_all_fp = np.ones(len(ys_fp), dtype=bool)
    dom_struct_sub = (~vis_sub)[ys_fp, xs_fp]
    act_idx = np.flatnonzero((fp & ~cat)[ys_fp, xs_fp])
    d_cat_act = d_full_fp[act_idx]

    # Fit physical (44 and 57 ch) and structural (67 and 83 ch) specialists
    c44, r44 = fit_dual_lgbm([X_phys_mm], dom_all_fp, cat, fp, seed=seed + 11, max_zero_neg=180_000)
    p_p44, m_p44 = predict_dual_lgbm(c44, r44, [X_phys_mm], act_idx)
    del c44, r44

    c57, r57 = fit_dual_lgbm([X_phys_mm, X_bgcd_mm], dom_all_fp, cat, fp, seed=seed + 29, max_zero_neg=180_000)
    p_p57, m_p57 = predict_dual_lgbm(c57, r57, [X_phys_mm, X_bgcd_mm], act_idx)
    del c57, r57

    # Pure BGCD-13 hydrothermal+basement-conduit specialist (decontaminated from 44-ch base dominance)
    c13, r13 = fit_dual_lgbm([X_bgcd_mm], dom_all_fp, cat, fp, seed=seed + 47, max_zero_neg=180_000)
    p_p13, m_p13 = predict_dual_lgbm(c13, r13, [X_bgcd_mm], act_idx)
    del c13, r13

    c67, r67 = fit_dual_lgbm(
        [X_phys_mm, X_vis_sub, d_over_w_sub], dom_struct_sub, hid_sub, fp, seed=seed + 61, max_zero_neg=180_000
    )
    p_f67, m_f67 = predict_dual_lgbm(c67, r67, [X_phys_mm, X_vis_full, d_over_w_full], act_idx)
    del c67, r67

    c83, r83 = fit_dual_lgbm(
        [X_phys_mm, X_bgcd_mm, X_vis_sub, X_slip_sub, d_over_w_sub],
        dom_struct_sub,
        hid_sub,
        fp,
        seed=seed + 83,
        max_zero_neg=180_000,
    )
    del X_vis_sub, X_slip_sub, d_over_w_sub
    gc.collect()
    p_f83, m_f83 = predict_dual_lgbm(
        c83, r83, [X_phys_mm, X_bgcd_mm, X_vis_full, X_slip_full, d_over_w_full], act_idx
    )
    del c83, r83, X_vis_full, X_slip_full, d_over_w_full
    gc.collect()

    # Pool with strong BGCD specialist authority in piedmont & blind basin regimes
    p_blind_mix = adhr._expit(
        0.15 * adhr._logit(p_p44) + 0.45 * adhr._logit(p_p57) + 0.40 * adhr._logit(p_p13)
    )
    m_blind_mix = np.maximum(
        p_blind_mix,
        adhr._expit(0.15 * adhr._logit(m_p44) + 0.45 * adhr._logit(m_p57) + 0.40 * adhr._logit(m_p13)),
    )
    p_struct_mix, m_struct_mix = _adaptive_poe_pool(p_f67, m_f67, p_f83, m_f83, d_cat_act, w_near=0.72, w_far=0.88)

    k_hidden_est = 22_000.0
    p_surf_act, m_surf_act = adhr._fuse_log_odds(
        p_struct_mix, m_struct_mix, p_blind_mix, m_blind_mix, k_hidden_est, beta_phys=0.45, pi_unmapped=0.55
    )

    p_surf_grid = adhr.scatter_fp(p_surf_act, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_surf_grid = adhr.scatter_fp(m_surf_act, ys_fp[act_idx], xs_fp[act_idx], grid.shape)

    sc_b = float(k_hidden_est) / max(float(p_blind_mix.sum()), 1e-6)
    p_blind_act = np.clip(p_blind_mix * np.float32(sc_b), 0.0, 1.0).astype(np.float32)
    m_blind_act = np.clip(m_blind_mix * np.float32(0.36), p_blind_act, 1.0).astype(np.float32)
    p_blind_grid = adhr.scatter_fp(p_blind_act, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_blind_grid = adhr.scatter_fp(m_blind_act, ys_fp[act_idx], xs_fp[act_idx], grid.shape)

    # Three-regime kernel-non-overlapping (min_spacing >= 3.20 px) axial allocation:
    #   Regime I   (2.25 < d_cat <= 10.0 px): slip-tip & relay stepover continuations
    #   Regime II  (10.0 < d_cat <= 25.0 px): piedmont/pediment up-gradient outflow back-projection
    #   Regime III (d_cat > 25.0 px):         blind intrabasin hydrothermal & TMI_up150 basement faults
    mask_r1 = allowed_emit & (d_cat_grid <= 10.0)
    mask_r2 = allowed_emit & (d_cat_grid > 10.0) & (d_cat_grid <= 25.0)
    mask_r3 = allowed_emit & (d_cat_grid > 25.0)

    p_r2_grid = (0.45 * p_surf_grid + 0.55 * p_blind_grid).astype(np.float32)
    m_r2_grid = np.maximum(p_r2_grid, 0.45 * m_surf_grid + 0.55 * m_blind_grid).astype(np.float32)

    alloc_r1 = emit.dinkelbach_allocate(
        p_surf_grid, m_surf_grid, mask_r1, budget=8_500, k_truth=7_500.0, min_spacing_px=3.20, dinkelbach_iters=5
    )
    alloc_r2 = emit.dinkelbach_allocate(
        p_r2_grid, m_r2_grid, mask_r2, budget=8_500, k_truth=6_500.0, min_spacing_px=3.20, dinkelbach_iters=5
    )
    alloc_r3 = emit.dinkelbach_allocate(
        p_blind_grid, m_blind_grid, mask_r3, budget=18_000, k_truth=11_000.0, min_spacing_px=3.20, dinkelbach_iters=5
    )

    emitted_bool = (alloc_r1.emitted | alloc_r2.emitted | alloc_r3.emitted) & allowed_emit
    emitted = emitted_bool.astype(np.float32)
    d_emit = d_cat_grid[emitted_bool]

    meta = {
        "n_dots": int(emitted_bool.sum()),
        "n_regime1_tip_relay_le10px": int(alloc_r1.n_dots),
        "n_regime2_piedmont_10_25px": int(alloc_r2.n_dots),
        "n_regime3_blind_basin_gt25px": int(alloc_r3.n_dots),
        "min_d_cat_px": round(float(d_emit.min()), 4) if d_emit.size else None,
        "share_le2": round(float((d_emit <= 2.0).mean()), 6) if d_emit.size else 0.0,
        "share_gt10": round(float((d_emit > 10.0).mean()), 6) if d_emit.size else 0.0,
        "share_gt25": round(float((d_emit > 25.0).mean()), 6) if d_emit.size else 0.0,
        "min_spacing_px": 3.20,
    }
    return emitted, p_surf_grid, meta
