"""TDKL-88: Transverse-Drainage Knickpoint-Lineament, Multi-Scale Scarp Polarity & Log-Odds PoE Completeness Fusion.

Extracts 12 label-blind geomorphic, 1 m LiDAR scarp-polarity, 10 m sub-pixel planar
breakline, upward-continued magnetic dipole, and radiometric redox-mobility channels
from the SHA-pinned competition + official external datasets (`dem10_chi_100m_u8.tif`,
`dem10_chi_100m_i16.tif`, `lidar_scarp_features_u8.tif`, `topo_10m_derived_100m_u8.tif`,
`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`, `training_features.tif`).

Strictly zero catalogue access in feature construction: `existing_faults.tif` is never
read by `build_or_load_tdkl_memmap`. Memory-bounded (< 450 MB RSS) via disk-backed
float32 `np.memmap`.
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

from gems57 import damagezone_envelope, emit, holdout

from . import adhr, edge, physics

TDKL_FEATURES: tuple[str, ...] = (
    "tdkl_knick_per_chan",
    "tdkl_raised_reach_frac",
    "tdkl_chi_divide_asym",
    "tdkl_ksn_area_resid",
    "tdkl_transverse_knick_coh",
    "tdkl_lidar_down_up_polarity",
    "tdkl_lidar_cross_scarp",
    "tdkl_lidar_grav_strike_cos2",
    "tdkl_topo10_planar_break",
    "tdkl_topo10_slope_conc",
    "tdkl_mag_up150_dipole",
    "tdkl_rad_redox_mobility",
)

TDKL_SCHEMA_VERSION = "tdkl88-12ch-v2"


def _zscore_fp(arr_fp: np.ndarray) -> np.ndarray:
    x = np.asarray(arr_fp, dtype=np.float32)
    q05, med, q95 = (float(v) for v in np.percentile(x[::19], [5.0, 50.0, 95.0]))
    scale = max((q95 - q05) / 3.2897, 1e-6)
    return np.clip((x - np.float32(med)) / np.float32(scale), -6.0, 6.0).astype(np.float32)


def build_or_load_tdkl_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict[str, str]]:
    """Build or reload disk-backed ``(N_fp, 12)`` float32 memmap of label-blind TDKL features."""
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    n_cols = len(TDKL_FEATURES)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / "x_tdkl_12ch_v2.dat"
    meta_path = cache_dir / "x_tdkl_12ch_v2.json"

    ext = root / "data/external"
    req_files = {
        "training_features.tif": root / "data/training_features.tif",
        "dem10_chi_100m_u8.tif": ext / "dem10_chi_100m_u8.tif",
        "dem10_chi_100m_i16.tif": ext / "dem10_chi_100m_i16.tif",
        "lidar_scarp_features_u8.tif": ext / "lidar_scarp_features_u8.tif",
        "topo_10m_derived_100m_u8.tif": ext / "topo_10m_derived_100m_u8.tif",
        "geodawn_rad_u8.tif": ext / "geodawn_rad_u8.tif",
        "geodawn_extensions_u8.tif": ext / "geodawn_extensions_u8.tif",
    }
    hashes = {
        k: hashlib.sha256(p.read_bytes()).hexdigest() if k != "training_features.tif" else "pinned_19band"
        for k, p in req_files.items()
    }

    if dat_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("schema") == TDKL_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(TDKL_FEATURES)
            and meta.get("hashes") == hashes
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), hashes

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    # 1. Fluvial chi & knickpoint channels with interfluve channel-normalized interpolation
    with rasterio.open(req_files["dem10_chi_100m_u8.tif"]) as ds:
        chan_n = ds.read(1).astype(np.float32)
        knick_n = ds.read(2).astype(np.float32)
        raised_n = ds.read(3).astype(np.float32)
        valid_chi = ds.read(4) > 0

    with rasterio.open(req_files["dem10_chi_100m_i16.tif"]) as ds:
        smax_raw = ds.read(1).astype(np.float32)
        smin_raw = ds.read(2).astype(np.float32)
        ksn_raw = ds.read(3).astype(np.float32)
        area_raw = ds.read(4).astype(np.float32)

    chan_mask = (chan_n > 0) & (ksn_raw > -1000) & valid_chi
    smax = np.where(smax_raw > -1000, np.maximum(smax_raw, 0.0), 0.0).astype(np.float32)
    smin = np.where(smin_raw > -1000, np.maximum(smin_raw, 0.0), 0.0).astype(np.float32)
    ksn = np.where(ksn_raw > -1000, np.maximum(ksn_raw, 0.0), 0.0).astype(np.float32)
    area = np.where(area_raw > -1000, np.maximum(area_raw, 0.0), 0.0).astype(np.float32)
    del smax_raw, smin_raw, ksn_raw, area_raw

    w_chan = ndi.gaussian_filter(chan_mask.astype(np.float32), sigma=4.0, mode="constant") + np.float32(1e-5)
    knick_interp = ndi.gaussian_filter(np.log1p(knick_n).astype(np.float32), sigma=4.0, mode="constant") / w_chan
    raised_interp = ndi.gaussian_filter((raised_n / (chan_n + 1.0)).astype(np.float32), sigma=4.0, mode="constant") / w_chan
    chi_asym_interp = (
        ndi.gaussian_filter(np.log1p(np.maximum(smax - smin, 0.0) / 50.0).astype(np.float32), sigma=4.0, mode="constant")
        / w_chan
    )
    ksn_resid_raw = np.where(chan_mask, np.log1p(ksn) - 0.25 * np.log1p(area / 1000.0), 0.0).astype(np.float32)
    ksn_resid_interp = ndi.gaussian_filter(ksn_resid_raw, sigma=4.0, mode="constant") / w_chan

    v_chi_fp = valid_chi[ys, xs]
    mm[:, 0] = np.where(v_chi_fp, knick_interp[ys, xs], -1.0).astype(np.float32)
    mm[:, 1] = np.where(v_chi_fp, raised_interp[ys, xs], -1.0).astype(np.float32)
    mm[:, 2] = np.where(v_chi_fp, chi_asym_interp[ys, xs], -1.0).astype(np.float32)
    mm[:, 3] = np.where(v_chi_fp, ksn_resid_interp[ys, xs], -1.0).astype(np.float32)
    del chan_n, raised_n, smax, smin, area, chan_mask, w_chan, raised_interp, chi_asym_interp, ksn_resid_raw

    # 2. Transverse-to-drainage knickpoint coherence + 10 m DEM sub-pixel scarp channels
    with rasterio.open(req_files["topo_10m_derived_100m_u8.tif"]) as ds:
        slope_p90 = ds.read(1)[ys, xs].astype(np.float32)
        slope_max = ds.read(2)[ys, xs].astype(np.float32)
        steep_frac = (ds.read(3)[ys, xs].astype(np.float32)) / 255.0
        slope_std = ds.read(4)[ys, xs].astype(np.float32)
        relief_loc = ds.read(5)[ys, xs].astype(np.float32)
        aspect_coh = (ds.read(7)[ys, xs].astype(np.float32)) / 255.0
        dem_q = ds.read(9).astype(np.float32)
        t9 = ds.tags(9)
        q_lo, q_hi = float(t9["q_lo"]), float(t9["q_hi"])
        dem_m = edge.clean_band(
            np.where(dem_q > 0, q_lo + (dem_q - 1.0) / 254.0 * (q_hi - q_lo), np.nan).astype(np.float32),
            fp,
        )[0]
        del dem_q

    mm[:, 8] = (aspect_coh * steep_frac * np.log1p(slope_std)).astype(np.float32)
    mm[:, 9] = ((slope_max - slope_p90) / (relief_loc + 5.0)).astype(np.float32)
    del slope_p90, slope_max, steep_frac, slope_std, relief_loc, aspect_coh

    dgy, dgx, dmag = physics._grad_f32(dem_m, 6.0)
    del dem_m
    inv_dmag = 1.0 / (dmag[ys, xs] + 1e-4)
    uflow_y = (-dgy[ys, xs] * inv_dmag).astype(np.float32)
    uflow_x = (-dgx[ys, xs] * inv_dmag).astype(np.float32)
    ustrike_y = (-uflow_x).astype(np.float32)
    ustrike_x = uflow_y.astype(np.float32)
    del dgy, dgx, dmag, inv_dmag

    knick_energy = (knick_interp * np.maximum(ksn_resid_interp, 0.0)).astype(np.float32)
    del knick_n, ksn, knick_interp, ksn_resid_interp, valid_chi
    k_s_pos3 = physics._bilinear_at_fp(knick_energy, ys, xs, 3.0 * ustrike_y, 3.0 * ustrike_x)
    k_s_neg3 = physics._bilinear_at_fp(knick_energy, ys, xs, -3.0 * ustrike_y, -3.0 * ustrike_x)
    k_s_pos6 = physics._bilinear_at_fp(knick_energy, ys, xs, 6.0 * ustrike_y, 6.0 * ustrike_x)
    k_s_neg6 = physics._bilinear_at_fp(knick_energy, ys, xs, -6.0 * ustrike_y, -6.0 * ustrike_x)
    k_f_pos4 = physics._bilinear_at_fp(knick_energy, ys, xs, 4.0 * uflow_y, 4.0 * uflow_x)
    k_f_neg4 = physics._bilinear_at_fp(knick_energy, ys, xs, -4.0 * uflow_y, -4.0 * uflow_x)
    k_center = knick_energy[ys, xs]
    strike_mean = 0.25 * (k_s_pos3 + k_s_neg3 + k_s_pos6 + k_s_neg6)
    flow_mean = 0.50 * (k_f_pos4 + k_f_neg4)
    mm[:, 4] = np.where(v_chi_fp, 0.5 * (k_center + strike_mean) - 0.4 * flow_mean, -1.0).astype(np.float32)
    del (
        knick_energy,
        v_chi_fp,
        uflow_y,
        uflow_x,
        ustrike_y,
        ustrike_x,
        k_s_pos3,
        k_s_neg3,
        k_s_pos6,
        k_s_neg6,
        k_f_pos4,
        k_f_neg4,
        k_center,
        strike_mean,
        flow_mean,
    )
    gc.collect()

    # 3. 1 m LiDAR scarp polarity, cross-scarp inflection & basement gravity strike concordance
    with rasterio.open(req_files["training_features.tif"]) as src:
        tmi_vg_fp = edge.clean_band(src.read(9), fp)[0][ys, xs]
        iso_grav = edge.clean_band(src.read(13), fp)[0]
    ggy6, ggx6, gmag6 = physics._grad_f32(iso_grav, 6.0)
    del iso_grav
    theta_grav = np.arctan2(-ggy6[ys, xs], ggx6[ys, xs] + 1e-8).astype(np.float32)
    del ggy6, ggx6, gmag6

    with rasterio.open(req_files["lidar_scarp_features_u8.tif"]) as ds:
        ex_mean = ds.read(2)[ys, xs].astype(np.float32)
        down_m = ds.read(6)[ys, xs].astype(np.float32)
        up_m = ds.read(7)[ys, xs].astype(np.float32)
        cross_m = ds.read(8)[ys, xs].astype(np.float32)
        coh100 = (ds.read(10)[ys, xs].astype(np.float32)) / 255.0
        strike_u8 = ds.read(11)[ys, xs].astype(np.float32)
        lv = ds.read(12)[ys, xs] > 0

    mm[:, 5] = np.where(
        lv, (down_m - up_m) / (down_m + up_m + 10.0), -2.0
    ).astype(np.float32)
    mm[:, 6] = np.where(
        lv, np.log1p(cross_m * ex_mean / 10.0), -1.0
    ).astype(np.float32)
    theta_lidar = ((strike_u8 - 1.0) / 254.0 * math.pi).astype(np.float32)
    mm[:, 7] = np.where(
        lv & (strike_u8 > 0), coh100 * np.cos(2.0 * (theta_lidar - theta_grav)), 0.0
    ).astype(np.float32)
    del ex_mean, down_m, up_m, cross_m, coh100, strike_u8, lv, theta_lidar, theta_grav
    gc.collect()

    # 4. Upward-continued magnetic depth-attenuation dipole & radiometric redox mobility
    with rasterio.open(req_files["geodawn_extensions_u8.tif"]) as ds:
        thk = ds.read(1)[ys, xs].astype(np.float32)
        uk = ds.read(2)[ys, xs].astype(np.float32)
        uth = ds.read(3)[ys, xs].astype(np.float32)
        tmi_up150 = ds.read(4).astype(np.float32)
    with rasterio.open(req_files["geodawn_rad_u8.tif"]) as ds:
        rad_u = ds.read(3)[ys, xs].astype(np.float32)
        rad_tc = ds.read(4)[ys, xs].astype(np.float32)

    up_lap_fp = (-ndi.gaussian_laplace(tmi_up150, sigma=2.5, mode="nearest"))[ys, xs].astype(np.float32)
    del tmi_up150
    mm[:, 10] = (_zscore_fp(tmi_vg_fp) - _zscore_fp(up_lap_fp)).astype(np.float32)
    del tmi_vg_fp, up_lap_fp

    rad_valid = rad_tc > 0
    redox_raw = 0.5 * (uk + uth) - 0.7 * thk + 0.3 * rad_u
    mm[:, 11] = np.where(rad_valid, redox_raw / 100.0, 0.0).astype(np.float32)
    del thk, uk, uth, rad_u, rad_tc, rad_valid, redox_raw
    mm.flush()

    for j, cname in enumerate(TDKL_FEATURES):
        if not np.isfinite(mm[:, j]).all():
            raise AssertionError(f"Non-finite values in TDKL column {cname}")

    meta_path.write_text(
        json.dumps(
            {
                "schema": TDKL_SCHEMA_VERSION,
                "shape": [n_fp, n_cols],
                "features": list(TDKL_FEATURES),
                "hashes": hashes,
            },
            indent=2,
        )
        + "\n"
    )
    del mm
    gc.collect()
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), hashes


def _poe_pool(
    p_base: np.ndarray,
    m_base: np.ndarray,
    p_tdkl: np.ndarray,
    m_tdkl: np.ndarray,
    w_tdkl: float = 0.65,
    d_vis_act: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Log-Odds Product-of-Experts pooling with blind-basin tail preservation (`d_vis > 22 px`).

    In the relay and piedmont corridor (`d_vis <= 22 px`), log-odds pooling allows negative
    geomorphic/scarp-polarity evidence in the TDKL specialist to veto false-positive volcanic
    caprock ledges and pluvial shorelines. In the deep blind-basin interior (`d_vis > 22 px`),
    where catalogue-conditioned probabilities decay toward zero, blending with disjunctive
    linear pooling preserves blind-basin fault discovery.
    """
    w0 = np.float32(1.0 - w_tdkl)
    w1 = np.float32(w_tdkl)
    p_lo = adhr._expit(w0 * adhr._logit(p_base) + w1 * adhr._logit(p_tdkl))
    m_lo = np.clip(adhr._expit(w0 * adhr._logit(m_base) + w1 * adhr._logit(m_tdkl)), p_lo, 1.0)
    if d_vis_act is not None:
        p_lin = (w0 * p_base + w1 * p_tdkl).astype(np.float32)
        m_lin = np.clip(w0 * m_base + w1 * m_tdkl, p_lin, 1.0).astype(np.float32)
        blind = d_vis_act > 22.0
        p_lo = np.where(blind, 1.18 * (0.35 * p_lo + 0.65 * p_lin), p_lo).astype(np.float32)
        m_lo = np.clip(np.where(blind, 1.18 * (0.35 * m_lo + 0.65 * m_lin), m_lo), p_lo, 1.0).astype(np.float32)
    return p_lo.astype(np.float32), m_lo.astype(np.float32)


def _fit_or_load_fold_posteriors(
    grid,
    X_phys_mm: np.ndarray,
    X_tdkl_mm: np.ndarray,
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
) -> dict[str, np.ndarray]:
    """Fit or load raw active-pixel posteriors for one holdout fold."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    cache_path = cache_dir / f"tdkl_posteriors_{fold_tag}_s{seed}_{TDKL_SCHEMA_VERSION}.npz"
    if cache_path.exists():
        data = np.load(cache_path)
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

    # 1. Exact H88-ADHR incumbent models (44 physics + 23 visible structure)
    clfs_phys_44, regs_phys_44 = adhr._fit_dual_expectation_models(
        [X_phys_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 17, n_ensemble=1
    )
    p_phys_44, m_phys_44 = adhr._predict_dual_chunked(clfs_phys_44, regs_phys_44, [X_phys_mm], act_idx)
    del clfs_phys_44, regs_phys_44

    clfs_full_67, regs_full_67 = adhr._fit_dual_expectation_models(
        [X_phys_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 53, n_ensemble=1
    )
    p_full_67, m_full_67 = adhr._predict_dual_chunked(
        clfs_full_67, regs_full_67, [X_phys_mm, X_vis22_mm, d_over_w_fp], act_idx
    )
    del clfs_full_67, regs_full_67
    gc.collect()

    # 2. TDKL-augmented 56-channel physical & 79-channel structural specialists
    clfs_phys_56, regs_phys_56 = adhr._fit_dual_expectation_models(
        [X_phys_mm, X_tdkl_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 117, n_ensemble=1
    )
    p_phys_56, m_phys_56 = adhr._predict_dual_chunked(
        clfs_phys_56, regs_phys_56, [X_phys_mm, X_tdkl_mm], act_idx
    )
    del clfs_phys_56, regs_phys_56

    clfs_full_79, regs_full_79 = adhr._fit_dual_expectation_models(
        [X_phys_mm, X_tdkl_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 153, n_ensemble=1
    )
    p_full_79, m_full_79 = adhr._predict_dual_chunked(
        clfs_full_79, regs_full_79, [X_phys_mm, X_tdkl_mm, X_vis22_mm, d_over_w_fp], act_idx
    )
    del clfs_full_79, regs_full_79, d_over_w_fp
    gc.collect()

    out = {
        "act_idx": act_idx.astype(np.int32),
        "p_phys_44": p_phys_44,
        "m_phys_44": m_phys_44,
        "p_full_67": p_full_67,
        "m_full_67": m_full_67,
        "p_phys_56": p_phys_56,
        "m_phys_56": m_phys_56,
        "p_full_79": p_full_79,
        "m_full_79": m_full_79,
    }
    np.savez(cache_path, **out)
    return out


def predict_tdkl_all_arms_fold(
    grid,
    X_phys_mm: np.ndarray,
    X_tdkl_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    cache_dir: Path | None = None,
    fold_tag: str = "fold",
) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    """Run Control 1 (`phys44_zero_cat`), Control 2 (`h88_adhr_incumbent`), `Exp 01` (`tdkl_phys_only`),
    `Exp 02` (`tdkl_single_79`), and `Exp 03` (`h88_tdkl`) on one fold."""
    if cache_dir is None:
        cache_dir = Path(".cache/gems88")

    post = _fit_or_load_fold_posteriors(
        grid, X_phys_mm, X_tdkl_mm, X_vis22_mm, d_vis_fp, comp_len_fp,
        visible, train_regions, train_truth, test_region, seed, cache_dir, fold_tag
    )
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = post["act_idx"]
    d_vis_act = d_vis_fp[act_idx]

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    p_phys_44, m_phys_44 = post["p_phys_44"], post["m_phys_44"]
    p_full_67, m_full_67 = post["p_full_67"], post["m_full_67"]
    p_phys_56, m_phys_56 = post["p_phys_56"], post["m_phys_56"]
    p_full_79, m_full_79 = post["p_full_79"], post["m_full_79"]

    # Log-Odds Product-of-Experts specialist pooling (35% 44/67-ch base + 65% 56/79-ch TDKL)
    p_phys_poe, m_phys_poe = _poe_pool(p_phys_44, m_phys_44, p_phys_56, m_phys_56, w_tdkl=0.65, d_vis_act=d_vis_act)
    p_full_poe, m_full_poe = _poe_pool(p_full_67, m_full_67, p_full_79, m_full_79, w_tdkl=0.65, d_vis_act=d_vis_act)

    # --- Control 1: phys44_zero_cat (zero-catalogue 44-channel physics control)
    scale_p_c1 = float(k_est) / max(float(p_phys_44.sum()), 1e-6)
    p_c1 = np.clip(p_phys_44 * np.float32(scale_p_c1), 0.0, 1.0).astype(np.float32)
    m_c1 = np.clip(m_phys_44 * np.float32(hid_ratio), p_c1, 1.0).astype(np.float32)
    p_c1_grid = adhr.scatter_fp(p_c1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_c1_grid = adhr.scatter_fp(m_c1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_c1 = emit.dinkelbach_allocate(
        p_c1_grid, m_c1_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # --- Control 2: h88_adhr_incumbent (exact reproduction)
    p_inc, m_inc = adhr._fuse_log_odds(p_full_67, m_full_67, p_phys_44, m_phys_44, k_est, beta_phys=0.35)
    p_inc_grid = adhr.scatter_fp(p_inc, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_inc_grid = adhr.scatter_fp(m_inc, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_inc = emit.dinkelbach_allocate(
        p_inc_grid, m_inc_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # --- Exp 01: tdkl_phys_only (zero-catalogue 56-channel physical + TDKL PoE specialist)
    scale_p_e1 = float(k_est) / max(float(p_phys_poe.sum()), 1e-6)
    p_e1 = np.clip(p_phys_poe * np.float32(scale_p_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_phys_poe * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)
    p_e1_grid = adhr.scatter_fp(p_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_e1_grid = adhr.scatter_fp(m_e1, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_e1 = emit.dinkelbach_allocate(
        p_e1_grid, m_e1_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # --- Exp 02: tdkl_single_79 (single 56/79-channel TDKL model + completeness fusion)
    p_s79, m_s79 = adhr._fuse_log_odds(p_full_79, m_full_79, p_phys_56, m_phys_56, k_est, beta_phys=0.35)
    p_s79_grid = adhr.scatter_fp(p_s79, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_s79_grid = adhr.scatter_fp(m_s79, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_s79 = emit.dinkelbach_allocate(
        p_s79_grid, m_s79_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # --- Exp 03: h88_tdkl (Log-Odds PoE Specialist Ensemble + Bayesian Completeness Fusion)
    p_tdkl, m_tdkl = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_est, beta_phys=0.35)
    p_tdkl_grid = adhr.scatter_fp(p_tdkl, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_tdkl_grid = adhr.scatter_fp(m_tdkl, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    alloc_tdkl = emit.dinkelbach_allocate(
        p_tdkl_grid, m_tdkl_grid, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
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
        "tdkl_phys_only": (
            alloc_e1.emitted.astype(np.float32),
            p_e1_grid,
            {"n_dots": int(alloc_e1.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_e1.surrogate_dti)},
        ),
        "tdkl_single_79": (
            alloc_s79.emitted.astype(np.float32),
            p_s79_grid,
            {"n_dots": int(alloc_s79.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_s79.surrogate_dti)},
        ),
        "h88_tdkl": (
            alloc_tdkl.emitted.astype(np.float32),
            p_tdkl_grid,
            {"n_dots": int(alloc_tdkl.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc_tdkl.surrogate_dti)},
        ),
    }


def fit_and_emit_production_tdkl(
    grid,
    X_phys_mm: np.ndarray,
    X_tdkl_mm: np.ndarray,
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    cache_dir: Path,
    seed: int = 8803,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Fit full-catalogue H88-TDKL Log-Odds PoE Specialist Ensemble and emit gate-compliant production raster.

    Memory-bounded (< 600 MB RSS): reuses pre-cached `seed20_f0_NW`, `seed21_f0_NW`, and
    `prod_fullcat` visible-structure memmaps from `.cache/gems88/`.
    """
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    n_fp = int(ys_fp.size)

    cache_post = cache_dir / f"tdkl_prod_posteriors_s{seed}_{TDKL_SCHEMA_VERSION}.npz"
    X_vis_full, d_full_fp, comp_len_full_fp = adhr.compute_visible_struct_fp(
        grid, full_cat, sense_src, scarp_fields, cache_dir, tag="prod_fullcat"
    )
    act_mask_fp = d_full_fp > 2.0
    act_idx = np.flatnonzero(act_mask_fp)
    d_act = d_full_fp[act_idx]

    if cache_post.exists():
        data = np.load(cache_post)
        p_phys_poe = data["p_phys_poe"]
        m_phys_poe = data["m_phys_poe"]
        p_full_poe = data["p_full_poe"]
        m_full_poe = data["m_full_poe"]
    else:
        dom_all = np.ones(n_fp, dtype=bool)
        # 1. Full-catalogue 44-ch and 56-ch zero-catalogue physical specialists
        clfs_p44, regs_p44 = adhr._fit_dual_expectation_models(
            [X_phys_mm], dom_all, full_cat, fp, seed=seed + 7, n_ensemble=1
        )
        p_phys_44, m_phys_44 = adhr._predict_dual_chunked(clfs_p44, regs_p44, [X_phys_mm], act_idx)
        del clfs_p44, regs_p44
        gc.collect()

        clfs_p56, regs_p56 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_tdkl_mm], dom_all, full_cat, fp, seed=seed + 107, n_ensemble=1
        )
        p_phys_56, m_phys_56 = adhr._predict_dual_chunked(clfs_p56, regs_p56, [X_phys_mm, X_tdkl_mm], act_idx)
        del clfs_p56, regs_p56
        gc.collect()

        p_phys_poe, m_phys_poe = _poe_pool(p_phys_44, m_phys_44, p_phys_56, m_phys_56, w_tdkl=0.65, d_vis_act=d_act)
        del p_phys_44, m_phys_44, p_phys_56, m_phys_56
        gc.collect()

        # 2. Structural + TDKL specialists trained on pre-cached synthetic whole-component draw (seed 20)
        syn_folds, _ = holdout.buffered_component_draw(
            grid, seed=20, hide_frac=0.20, buffer_px=3, boundary_px=12
        )
        syn_vis = syn_folds[0]["visible"]
        syn_hid = syn_folds[0]["hidden_all"]
        X_vis_syn, d_syn_fp, comp_len_syn_fp = adhr.compute_visible_struct_fp(
            grid, syn_vis, sense_src, scarp_fields, cache_dir, tag="seed20_f0_NW"
        )
        wlaw_syn = damagezone_envelope.fit_width_law(
            comp_len_syn_fp, d_syn_fp, syn_hid[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
        )
        d_over_w_syn = (d_syn_fp / np.maximum(wlaw_syn.half_width(comp_len_syn_fp), 1e-6)).astype(np.float32)
        dom_syn = (~syn_vis)[ys_fp, xs_fp]
        d_over_w_full = (d_full_fp / np.maximum(wlaw_syn.half_width(comp_len_full_fp), 1e-6)).astype(np.float32)

        c67, r67 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_vis_syn, d_over_w_syn], dom_syn, syn_hid, fp, seed=seed + 41, n_ensemble=1
        )
        p67, m67 = adhr._predict_dual_chunked(c67, r67, [X_phys_mm, X_vis_full, d_over_w_full], act_idx)
        del c67, r67
        gc.collect()

        c79, r79 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_tdkl_mm, X_vis_syn, d_over_w_syn], dom_syn, syn_hid, fp, seed=seed + 141, n_ensemble=1
        )
        del X_vis_syn, d_syn_fp, comp_len_syn_fp, d_over_w_syn
        p79, m79 = adhr._predict_dual_chunked(c79, r79, [X_phys_mm, X_tdkl_mm, X_vis_full, d_over_w_full], act_idx)
        del c79, r79, d_over_w_full
        gc.collect()

        p_full_poe, m_full_poe = _poe_pool(p67, m67, p79, m79, w_tdkl=0.65, d_vis_act=d_act)
        del p67, m67, p79, m79
        gc.collect()
        np.savez(
            cache_post,
            p_phys_poe=p_phys_poe,
            m_phys_poe=m_phys_poe,
            p_full_poe=p_full_poe,
            m_full_poe=m_full_poe,
        )

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(
        p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_prod, beta_phys=0.40, pi_unmapped=0.55
    )

    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0

    k_near = k_prod * 0.58
    k_far = k_prod * 0.42

    scale_near = float(k_near) / max(float(p_fused[near_sel].sum()), 1e-6)
    p_near = np.clip(p_fused[near_sel] * np.float32(scale_near), 0.0, 1.0).astype(np.float32)
    m_near = np.clip(m_fused[near_sel] * np.float32(min(max(scale_near, 0.85), 1.15)), p_near, 1.0).astype(np.float32)

    p_far_raw = 0.30 * p_fused[far_sel] + 0.70 * p_phys_poe[far_sel]
    m_far_raw = 0.30 * m_fused[far_sel] + 0.70 * m_phys_poe[far_sel]
    scale_far = float(k_far) / max(float(p_far_raw.sum()), 1e-6)
    p_far = np.clip(p_far_raw * np.float32(scale_far), 0.0, 1.0).astype(np.float32)
    m_far = np.clip(m_far_raw * np.float32(min(max(scale_far, 0.85), 1.25)), p_far, 1.0).astype(np.float32)

    p_comb = np.empty_like(p_fused)
    m_comb = np.empty_like(m_fused)
    p_comb[near_sel] = p_near
    m_comb[near_sel] = m_near
    p_comb[far_sel] = p_far
    m_comb[far_sel] = m_far
    del p_fused, m_fused, p_near, m_near, p_far, m_far, p_far_raw, m_far_raw

    p_grid = adhr.scatter_fp(p_comb, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_grid = adhr.scatter_fp(m_comb, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    del p_comb, m_comb
    gc.collect()

    allowed_near = np.zeros(grid.shape, dtype=bool)
    allowed_near[ys_fp[act_idx[near_sel]], xs_fp[act_idx[near_sel]]] = True
    allowed_far = np.zeros(grid.shape, dtype=bool)
    allowed_far[ys_fp[act_idx[far_sel]], xs_fp[act_idx[far_sel]]] = True

    alloc_near = emit.dinkelbach_allocate(
        p_grid, m_grid, allowed_near, budget=14_500, k_truth=k_near, min_spacing_px=2.10, dinkelbach_iters=8
    )
    alloc_far = emit.dinkelbach_allocate(
        p_grid, m_grid, allowed_far, budget=10_500, k_truth=k_far, min_spacing_px=2.25, dinkelbach_iters=8
    )
    emitted = np.clip(alloc_near.emitted + alloc_far.emitted, 0.0, 1.0).astype(np.float32)
    n_dots = int((emitted > 0).sum())
    n_far_dots = int((alloc_far.emitted > 0).sum())

    return emitted, p_grid, {
        "n_dots": n_dots,
        "n_near_dots": int(alloc_near.n_dots),
        "n_far_dots": n_far_dots,
        "share_gt25": float(n_far_dots / max(n_dots, 1)),
        "k_truth_est": float(k_prod),
        "surrogate_dti_near": float(alloc_near.surrogate_dti),
        "surrogate_dti_far": float(alloc_far.surrogate_dti),
    }
