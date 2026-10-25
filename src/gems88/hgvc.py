"""H88-HGVC: Hydrothermal Geochemical-Outflow Up-Dip Advection, Pluvial-Tufa-Decontaminated
Sinter & Perched Clay-Cap Conduit Tensor (HGVC-20).

Extracts 20 strictly label-blind (zero-catalogue) hydrothermal, geochemical, shallow-probe,
potential-field, basement-decoupling, and 1m/10m 3DEP structural-conduit channels from
SHA-pinned official competition + DOE GDR #1391 + USGS GeoDAWN + USGS 3DEP inputs:
  * ``data/training_features.tif`` (19 bands, verified tags, -FLT_MAX nodata cleaned)
  * ``data/external/gdr_wellspring_in_footprint.csv`` (quartz, chalcedony, Na-K-Ca geothermometers;
    ``dist_known_fault_px`` explicitly stripped on read and never accessed)
  * ``data/external/paleo_geothermal_regional.zip`` (opaline sinter / silica-cemented sand /
    travertine separated from Pleistocene pluvial lake tufa shoreline mimics)
  * ``data/external/2m_temperature_probe_INGENIOUS_regional_data.zip`` (vertical 1m->2m
    conductive thermal gradient + F2mDAB)
  * ``data/external/geodawn_rad_u8.tif`` & ``geodawn_extensions_u8.tif``
  * ``data/external/lidar_scarp_features_u8.tif``, ``topo_10m_derived_100m_u8.tif``,
    ``dem10_chi_100m_u8.tif``, ``dem10_chi_100m_i16.tif``, ``data/geodawn_dem_a2_100m.tif``

Strictly zero catalogue access in feature construction: ``existing_faults.tif`` is never
opened or read by ``build_or_load_hgvc_memmap``. Memory-bounded (< 500 MB RSS on 3.8 GiB
sandbox) via disk-backed float32 ``np.memmap``.
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
from typing import Sequence

import numpy as np
import rasterio
from rasterio.warp import transform as crs_transform
from scipy import ndimage as ndi

from gems57 import damagezone_envelope, emit

from . import adhr, edge, physics

TAN_60 = math.tan(math.radians(60.0))
HGVC_SCHEMA_VERSION = "hgvc88-20ch-v1"

HGVC_FEATURES: tuple[str, ...] = (
    "hgvc_diseq_outflow_s8",
    "hgvc_spring_vent_s6",
    "hgvc_sinter_decontam",
    "hgvc_probe_vert_grad",
    "hgvc_updip_feeder_1p5km",
    "hgvc_updip_feeder_3p0km",
    "hgvc_claycap_perched_resid",
    "hgvc_demag_grav_conduit",
    "hgvc_redox_uth_kth_grad",
    "hgvc_zbase_slope_decouple",
    "hgvc_zbase_antithetic_step",
    "hgvc_updip60_hessian_crest",
    "hgvc_kostrov_dilat_conduit",
    "hgvc_lidar_bajada_polarity",
    "hgvc_lidar_crest_asymmetry",
    "hgvc_topo10_shorefree_crest",
    "hgvc_chi_strike_knick_bridge",
    "hgvc_multiphys_vessel_s2p5",
    "hgvc_axial_strike_coherence",
    "hgvc_mimic_playa_tufa_shore",
)

# Regional smooth DC / province-level channels excluded from the translation-invariant
# blind-basin specialist so GBDTs learn local fault-conduit physics rather than quadrangle coordinates.
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


class ColumnSubsetView:
    """Zero-copy column selector over an ``(N_fp, C)`` disk memmap."""

    def __init__(self, mm: np.ndarray, cols: Sequence[int]):
        self._mm = mm
        self._cols = np.asarray(cols, dtype=np.int32)
        self.shape = (mm.shape[0], int(self._cols.size))

    def __getitem__(self, rows) -> np.ndarray:
        sub = np.asarray(self._mm[rows], dtype=np.float32)
        if sub.ndim == 1:
            return sub[self._cols]
        return sub[:, self._cols]


def _hessian_crest(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Scale-normalized principal Hessian bright-ridge crest curvature."""
    a = np.asarray(arr, dtype=np.float32)
    s2 = np.float32(sigma * sigma)
    gxx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 2), mode="nearest") * s2
    gyy = ndi.gaussian_filter(a, sigma=sigma, order=(2, 0), mode="nearest") * s2
    gxy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 1), mode="nearest") * s2
    tr = gxx + gyy
    rad = np.hypot(gxx - gyy, 2.0 * gxy)
    return np.maximum(0.0, 0.5 * (-tr + rad)).astype(np.float32)


def _frangi_line_2d(arr: np.ndarray, sigma: float, beta: float = 0.5) -> np.ndarray:
    """2D Frangi bright-ridge vesselness on a positive gradient-magnitude field."""
    a = np.asarray(arr, dtype=np.float32)
    s2 = np.float32(sigma * sigma)
    hxx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 2), mode="nearest") * s2
    hyy = ndi.gaussian_filter(a, sigma=sigma, order=(2, 0), mode="nearest") * s2
    hxy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 1), mode="nearest") * s2
    tr = hxx + hyy
    disc = np.hypot(hxx - hyy, 2.0 * hxy)
    la = 0.5 * (tr + disc)
    lb = 0.5 * (tr - disc)
    swap = np.abs(la) > np.abs(lb)
    l1 = np.where(swap, lb, la)
    l2 = np.where(swap, la, lb)
    del hxx, hyy, hxy, tr, disc, la, lb, swap
    rb2 = (l1 / (np.abs(l2) + np.float32(1e-6))) ** 2
    s_norm2 = l1 * l1 + l2 * l2
    c_scale = float(np.percentile(np.sqrt(s_norm2[::8, ::8]), 90.0)) * 0.5 + 1e-6
    v = np.where(
        l2 < 0.0,
        np.exp(-rb2 / np.float32(2.0 * beta * beta)) * (1.0 - np.exp(-s_norm2 / np.float32(2.0 * c_scale * c_scale))),
        0.0,
    )
    return v.astype(np.float32)


def _structure_tensor_2theta(gy: np.ndarray, gx: np.ndarray, sigma_int: float = 3.0) -> tuple[np.ndarray, np.ndarray]:
    """Unit axial orientation vector ``(cos 2*theta, sin 2*theta)`` of a gradient field.

    If gradient points in direction ``phi`` (normal to fault strike ``theta = phi + pi/2``),
    then ``(cos 2*phi, sin 2*phi) = (-cos 2*theta, -sin 2*theta)``; using ``(-cos 2*phi, -sin 2*phi)``
    aligns all modalities to fault-strike double-angle ``2*theta``.
    """
    jxx = ndi.gaussian_filter((gx * gx).astype(np.float32), sigma=sigma_int, mode="nearest")
    jyy = ndi.gaussian_filter((gy * gy).astype(np.float32), sigma=sigma_int, mode="nearest")
    jxy = ndi.gaussian_filter((gx * gy).astype(np.float32), sigma=sigma_int, mode="nearest")
    u = jyy - jxx  # = -(jxx - jyy) -> cos(2 * strike)
    v = -2.0 * jxy  # -> sin(2 * strike)
    norm = np.hypot(u, v) + np.float32(1e-6)
    return (u / norm).astype(np.float32), (v / norm).astype(np.float32)


def build_or_load_hgvc_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict]:
    """Stream 20 label-blind Hydrothermal Geochemical-Vent & Conduit channels into disk memmap."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    n_fp = int(ys_fp.size)
    n_cols = len(HGVC_FEATURES)

    dat_path = cache_dir / "x_hgvc_20ch_v1.dat"
    meta_path = cache_dir / "x_hgvc_20ch_v1.json"

    ext = root / "data/external"
    req_files = {
        "training_features.tif": root / "data/training_features.tif",
        "geodawn_dem_a2_100m.tif": root / "data/geodawn_dem_a2_100m.tif",
        "gdr_wellspring_in_footprint.csv": ext / "gdr_wellspring_in_footprint.csv",
        "paleo_geothermal_regional.zip": ext / "paleo_geothermal_regional.zip",
        "2m_temperature_probe_INGENIOUS_regional_data.zip": ext / "2m_temperature_probe_INGENIOUS_regional_data.zip",
        "geodawn_rad_u8.tif": ext / "geodawn_rad_u8.tif",
        "geodawn_extensions_u8.tif": ext / "geodawn_extensions_u8.tif",
        "lidar_scarp_features_u8.tif": ext / "lidar_scarp_features_u8.tif",
        "topo_10m_derived_100m_u8.tif": ext / "topo_10m_derived_100m_u8.tif",
        "dem10_chi_100m_u8.tif": ext / "dem10_chi_100m_u8.tif",
        "dem10_chi_100m_i16.tif": ext / "dem10_chi_100m_i16.tif",
    }
    hashes = {
        k: (
            hashlib.sha256(p.read_bytes()).hexdigest()
            if k != "training_features.tif"
            else f"size_{p.stat().st_size}"
        )
        for k, p in req_files.items()
    }

    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("schema") == HGVC_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(HGVC_FEATURES)
            and meta.get("hashes") == hashes
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    tmp_path = cache_dir / "x_hgvc_20ch_v1.tmp"
    mm = np.memmap(tmp_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    def write_col(col_idx: int, name: str, arr_fp: np.ndarray, allow_sentinel_neg1: bool = False) -> None:
        if HGVC_FEATURES[col_idx] != name:
            raise AssertionError(f"Column mismatch at {col_idx}: {name} != {HGVC_FEATURES[col_idx]}")
        v = np.nan_to_num(np.asarray(arr_fp, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        if allow_sentinel_neg1:
            valid_m = v > -0.999
            if np.any(valid_m):
                lo, hi = np.percentile(v[valid_m], [0.05, 99.95])
                v = np.where(valid_m, np.clip(v, lo, hi), -1.0).astype(np.float32)
        else:
            lo, hi = np.percentile(v, [0.05, 99.95])
            v = np.clip(v, lo, hi).astype(np.float32)
        mm[:, col_idx] = v

    shape = grid.shape
    inv_tf = ~grid.transform

    # ------------------------------------------------------------------
    # Block A: DEM shoreline bands, 10 m 3DEP hydraulic upslope vector, and planar scarp crest
    # ------------------------------------------------------------------
    with rasterio.open(req_files["geodawn_dem_a2_100m.tif"]) as ds:
        dem_a2 = edge.clean_band(ds.read(1), fp)[0]
    shore_pen_2d = np.clip(
        np.exp(-0.5 * ((dem_a2 - 1330.0) / 22.0) ** 2) + np.exp(-0.5 * ((dem_a2 - 1555.0) / 22.0) ** 2),
        0.0,
        1.0,
    ).astype(np.float32)
    del dem_a2

    with rasterio.open(req_files["topo_10m_derived_100m_u8.tif"]) as ds:
        slp_p90_2d = ds.read(1).astype(np.float32)
        slp_max_2d = ds.read(2).astype(np.float32)
        steep_2d = ds.read(3).astype(np.float32) / 255.0
        rel10_2d = ds.read(5).astype(np.float32)
        asp_coh_2d = ds.read(7).astype(np.float32) / 255.0
        dem_q = ds.read(9).astype(np.float32)
        t9 = ds.tags(9)
        q_lo, q_hi = float(t9["q_lo"]), float(t9["q_hi"])
        dem10_m = edge.clean_band(
            np.where(dem_q > 0, q_lo + (dem_q - 1.0) / 254.0 * (q_hi - q_lo), np.nan).astype(np.float32),
            fp,
        )[0]
        del dem_q

    playa_flat_fp = (np.exp(-slp_p90_2d[ys_fp, xs_fp] / 8.0) * np.exp(-rel10_2d[ys_fp, xs_fp] / 8.0)).astype(np.float32)
    breakline_2d = (
        np.maximum(slp_max_2d - slp_p90_2d, 0.0)
        / (rel10_2d + 8.0)
        * asp_coh_2d
        * (0.35 + 0.65 * steep_2d)
        * (1.0 - 0.85 * shore_pen_2d)
    ).astype(np.float32)
    write_col(15, "hgvc_topo10_shorefree_crest", _hessian_crest(breakline_2d, sigma=2.0)[ys_fp, xs_fp])
    del slp_p90_2d, slp_max_2d, steep_2d, rel10_2d, asp_coh_2d, breakline_2d

    dgy6, dgx6, dmag6 = physics._grad_f32(dem10_m, 6.0)
    dgy3, dgx3, _ = physics._grad_f32(dem10_m, 3.0)
    c2_topo_fp, s2_topo_fp = (arr[ys_fp, xs_fp] for arr in _structure_tensor_2theta(dgy3, dgx3, sigma_int=3.0))
    del dgy3, dgx3, dem10_m
    # Unit upslope vector (+grad z): -u_upslope points downslope toward outflow basin
    upslope_y_fp = (dgy6[ys_fp, xs_fp] / (dmag6[ys_fp, xs_fp] + 1e-4)).astype(np.float32)
    upslope_x_fp = (dgx6[ys_fp, xs_fp] / (dmag6[ys_fp, xs_fp] + 1e-4)).astype(np.float32)
    uflow_y_fp = (-upslope_y_fp).astype(np.float32)
    uflow_x_fp = (-upslope_x_fp).astype(np.float32)
    del dgy6, dgx6, dmag6
    gc.collect()

    # ------------------------------------------------------------------
    # Block B: Competition 19-band subsurface, potential-field & strain conduits
    # ------------------------------------------------------------------
    with rasterio.open(req_files["training_features.tif"]) as src:
        if (src.height, src.width) != shape or src.crs != grid.crs or src.transform != grid.transform:
            raise ValueError("training_features.tif grid mismatch")
        for idx, want_tag in physics.EXPECTED_TRAINING_BANDS.items():
            got = src.tags(idx).get("band_name", "")
            if got != want_tag:
                raise ValueError(f"band {idx}: expected {want_tag!r}, got {got!r}")

        def rd(b: int) -> np.ndarray:
            return edge.clean_band(src.read(b), fp)[0]

        rtp = rd(2)
        tmi_hg = np.maximum(rd(3), 0.0)
        geod_2nd = np.maximum(rd(4), 0.0)
        shearrate = np.maximum(rd(7), 0.0)
        dilaterate = rd(8)
        tmi_vg = rd(9)
        det_elev = rd(12)
        iso_grav = rd(13)
        zbase_m = np.maximum(rd(15), 0.0)
        cond_surf = np.maximum(rd(17), 0.0)
        iso_grav_hg = np.maximum(rd(18), 0.0)
        det_slope = np.maximum(rd(19), 0.0)

    # Basement shoaling up-dip vector (-grad z_base points from deep basin up onto fault footwall)
    zb_gy6, zb_gx6, zb_mag6 = physics._grad_f32(zbase_m, 6.0)
    upbase_y_fp = (-zb_gy6[ys_fp, xs_fp] / (zb_mag6[ys_fp, xs_fp] + 1e-4)).astype(np.float32)
    upbase_x_fp = (-zb_gx6[ys_fp, xs_fp] / (zb_mag6[ys_fp, xs_fp] + 1e-4)).astype(np.float32)
    del zb_gy6, zb_gx6, zb_mag6

    # Cover-thickness vs surface-slope decoupling (channels 9 & 10)
    zb_gy3, zb_gx3, zb_mag3 = physics._grad_f32(zbase_m, 3.0)
    de_gy3, de_gx3, de_mag3 = physics._grad_f32(det_elev, 3.0)
    c2_zb_fp, s2_zb_fp = (arr[ys_fp, xs_fp] for arr in _structure_tensor_2theta(zb_gy3, zb_gx3, sigma_int=3.0))
    # Fault normal for normal faults: basement deepens (+grad z_base) while surface drops (-grad det_elev),
    # so synthetic normal fault has grad(z_base) anti-parallel to grad(det_elev) (cos_align < 0).
    # Wait: decouple measures when basement steps strongly while surface is flat OR oblique/antithetic!
    cos_zb_de = (
        zb_gx3[ys_fp, xs_fp] * (-de_gx3[ys_fp, xs_fp]) + zb_gy3[ys_fp, xs_fp] * (-de_gy3[ys_fp, xs_fp])
    ) / (zb_mag3[ys_fp, xs_fp] * de_mag3[ys_fp, xs_fp] + 1e-5)
    zb_step_fp = np.log1p(zb_mag3[ys_fp, xs_fp] / 8.0).astype(np.float32)
    slope_suppress = 1.0 / (1.0 + det_slope[ys_fp, xs_fp] / 5.0)
    write_col(9, "hgvc_zbase_slope_decouple", zb_step_fp * (1.0 - cos_zb_de) * slope_suppress)
    write_col(10, "hgvc_zbase_antithetic_step", zb_step_fp * (1.0 + cos_zb_de) * (1.0 - 0.6 * playa_flat_fp))
    del zb_gy3, zb_gx3, de_gy3, de_gx3, de_mag3, cos_zb_de, det_elev, det_slope

    # Gravity & RTP orientations + multi-physics vesselness (channels 17 & 18)
    g_gy3, g_gx3, g_mag3 = physics._grad_f32(iso_grav, 3.0)
    r_gy3, r_gx3, _ = physics._grad_f32(rtp, 3.0)
    c2_grav_fp, s2_grav_fp = (arr[ys_fp, xs_fp] for arr in _structure_tensor_2theta(g_gy3, g_gx3, sigma_int=3.0))
    c2_rtp_fp, s2_rtp_fp = (arr[ys_fp, xs_fp] for arr in _structure_tensor_2theta(r_gy3, r_gx3, sigma_int=3.0))
    theta_grav_fp = (0.5 * np.arctan2(s2_grav_fp, c2_grav_fp)).astype(np.float32)
    del g_gy3, g_gx3, r_gy3, r_gx3, iso_grav

    v_grav = _frangi_line_2d(np.log1p(iso_grav_hg * 10.0), sigma=2.5)
    v_zbase = _frangi_line_2d(np.log1p(zb_mag3 / 8.0), sigma=2.5)
    write_col(17, "hgvc_multiphys_vessel_s2p5", np.sqrt(v_grav[ys_fp, xs_fp] * v_zbase[ys_fp, xs_fp]))
    del v_grav, v_zbase

    kappa_c = 0.25 * (c2_grav_fp + c2_rtp_fp + c2_zb_fp + c2_topo_fp)
    kappa_s = 0.25 * (s2_grav_fp + s2_rtp_fp + s2_zb_fp + s2_topo_fp)
    write_col(18, "hgvc_axial_strike_coherence", np.hypot(kappa_c, kappa_s) * np.sqrt(zb_step_fp + 0.2))
    del c2_rtp_fp, s2_rtp_fp, c2_zb_fp, s2_zb_fp, c2_topo_fp, s2_topo_fp, kappa_c, kappa_s

    # 60-degree up-dip back-projected composite step Hessian crest (channel 11)
    # Shift hanging-wall geophysical gradients UP basement dip (+upbase) to the surface fault trace,
    # i.e. at trace pixel x we sample hanging-wall anomaly down-dip (-upbase) by z_base / tan(60)!
    shift_hw = np.clip((zbase_m[ys_fp, xs_fp] / 100.0) / TAN_60, 0.0, 15.0).astype(np.float32)
    dy_downdip = (-upbase_y_fp * shift_hw).astype(np.float32)
    dx_downdip = (-upbase_x_fp * shift_hw).astype(np.float32)
    comp_hw_fp = (
        0.45 * np.log1p(physics._bilinear_at_fp(iso_grav_hg, ys_fp, xs_fp, dy_downdip, dx_downdip) * 10.0)
        + 0.30 * np.log1p(physics._bilinear_at_fp(tmi_hg, ys_fp, xs_fp, dy_downdip, dx_downdip) / 20.0)
        + 0.25 * np.log1p(physics._bilinear_at_fp(zb_mag3, ys_fp, xs_fp, dy_downdip, dx_downdip) / 8.0)
    ).astype(np.float32)
    comp_hw_2d = adhr.scatter_fp(comp_hw_fp, ys_fp, xs_fp, shape)
    write_col(11, "hgvc_updip60_hessian_crest", _hessian_crest(comp_hw_2d, sigma=2.2)[ys_fp, xs_fp])
    del shift_hw, dy_downdip, dx_downdip, comp_hw_fp, comp_hw_2d, tmi_hg, zbase_m, zb_mag3, g_mag3

    # Perched argillic smectite clay-cap residual (channel 6) & Kostrov dilatational conduit (channel 12)
    log_cond = np.log1p(cond_surf * 5.0).astype(np.float32)
    cond_bg = ndi.gaussian_filter(log_cond, sigma=24.0, mode="nearest")
    cond_loc = ndi.gaussian_filter(log_cond, sigma=2.5, mode="nearest")
    cond_resid_fp = (cond_loc[ys_fp, xs_fp] - cond_bg[ys_fp, xs_fp]) * (1.0 - 0.80 * playa_flat_fp)
    write_col(6, "hgvc_claycap_perched_resid", cond_resid_fp)
    playa_brine_fp = (playa_flat_fp * np.clip(log_cond[ys_fp, xs_fp], 0.0, 4.0) * np.exp(-iso_grav_hg[ys_fp, xs_fp] * 2.0)).astype(np.float32)
    del cond_surf, log_cond, cond_bg, cond_loc, cond_resid_fp

    grav_gate_fp = np.log1p(iso_grav_hg[ys_fp, xs_fp] * 10.0).astype(np.float32)
    kostrov_fp = (
        np.log1p(shearrate[ys_fp, xs_fp] * np.maximum(dilaterate[ys_fp, xs_fp], 0.0) + 0.35 * geod_2nd[ys_fp, xs_fp])
        * (0.35 + 0.65 * grav_gate_fp)
    ).astype(np.float32)
    write_col(12, "hgvc_kostrov_dilat_conduit", kostrov_fp)
    del shearrate, dilaterate, geod_2nd, kostrov_fp
    gc.collect()

    # ------------------------------------------------------------------
    # Block C: GeoDAWN upward-continued demagnetization & radiometric redox conduit
    # ------------------------------------------------------------------
    with rasterio.open(req_files["geodawn_extensions_u8.tif"]) as ds:
        thk_2d = ds.read(1).astype(np.float32) / 255.0
        uth_2d = ds.read(3).astype(np.float32) / 255.0
        tmi150_2d = ds.read(4).astype(np.float32) / 255.0
        gd_val = (ds.read(4) > 0).astype(np.float32)

    # Short-wavelength hydrothermal magnetite-destruction trough on density-stepping faults (channel 7)
    rtp_lo, rtp_hi = np.percentile(rtp[ys_fp, xs_fp][::17], [2.0, 98.0])
    rtp_norm_2d = np.clip((rtp - rtp_lo) / max(rtp_hi - rtp_lo, 1.0), 0.0, 1.0).astype(np.float32)
    rtp_short = rtp_norm_2d - ndi.gaussian_filter(rtp_norm_2d, sigma=10.0, mode="nearest")
    tmi150_short = tmi150_2d - ndi.gaussian_filter(tmi150_2d, sigma=10.0, mode="nearest")
    demag_trough_fp = (
        gd_val[ys_fp, xs_fp] * np.maximum(tmi150_short[ys_fp, xs_fp] - rtp_short[ys_fp, xs_fp], 0.0)
        + 0.35 * np.log1p(np.maximum(-tmi_vg[ys_fp, xs_fp], 0.0))
    ) * grav_gate_fp
    write_col(7, "hgvc_demag_grav_conduit", demag_trough_fp)
    del rtp, rtp_norm_2d, rtp_short, tmi150_2d, tmi150_short, tmi_vg, iso_grav_hg, demag_trough_fp

    # Flight-line-decontaminated strike-aligned U/Th and K/Th alteration gradient (channel 8)
    uth_hp = uth_2d - ndi.gaussian_filter(uth_2d, sigma=14.0, mode="nearest")
    kth_hp = (1.0 - thk_2d) - ndi.gaussian_filter(1.0 - thk_2d, sigma=14.0, mode="nearest")
    ugy, ugx, umag = physics._grad_f32(uth_hp + 0.7 * kth_hp, 2.5)
    # Gradient normal to fault strike -> strike of radiometric boundary is atan2(-ugy, ugx)
    theta_rad_fp = np.arctan2(-ugy[ys_fp, xs_fp], ugx[ys_fp, xs_fp] + 1e-8).astype(np.float32)
    align_rad_grav = np.cos(theta_rad_fp - theta_grav_fp) ** 2
    write_col(8, "hgvc_redox_uth_kth_grad", gd_val[ys_fp, xs_fp] * umag[ys_fp, xs_fp] * align_rad_grav)
    del thk_2d, uth_2d, gd_val, uth_hp, kth_hp, ugy, ugx, umag, theta_rad_fp, align_rad_grav
    gc.collect()

    # ------------------------------------------------------------------
    # Block D: DOE GDR #1391 Geochemical Disequilibrium, Springs, Sinter/Tufa & 2m Probes
    # ------------------------------------------------------------------
    w_rows_d, w_cols_d, w_diseq = [], [], []
    s_rows, s_cols, s_wt = [], [], []
    n_cold_rejected = 0
    with req_files["gdr_wellspring_in_footprint.csv"].open("r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            # Explicit zero-leakage guard: drop dist_known_fault_px immediately on read
            r.pop("dist_known_fault_px", None)
            try:
                rr, cc = int(float(r["row"])), int(float(r["col"]))
            except (KeyError, ValueError):
                continue
            tclass = (r.get("thermalclass") or "").strip().lower()
            layer_nm = (r.get("layer") or "").strip().lower()
            t_meas = np.nan
            try:
                if r.get("temp_c", "") not in ("", "nan", "NaN", "NULL"):
                    t_meas = float(r["temp_c"])
            except ValueError:
                pass
            geos = []
            for gk, floor_c in (("geothermquartz_c", 75.0), ("geothermcat_c", 70.0), ("geothermchalc_c", 60.0)):
                try:
                    gv = float(r.get(gk, ""))
                    if np.isfinite(gv) and gv > floor_c:
                        geos.append(gv)
                except ValueError:
                    pass
            t_geo_max = max(geos) if geos else 0.0
            if tclass == "cold" or (np.isfinite(t_meas) and 0.0 < t_meas < 18.0 and t_geo_max < 85.0):
                n_cold_rejected += 1
                continue
            t_surf_eff = max(t_meas, 18.0) if np.isfinite(t_meas) else 25.0
            diseq = max(t_geo_max - t_surf_eff, 0.0) if t_geo_max > 80.0 else 0.0
            warm_excess = max((t_meas if np.isfinite(t_meas) else 0.0) - 22.0, 0.0)
            score_pt = math.log1p(0.08 * diseq + 0.04 * warm_excess)
            if score_pt > 0.02:
                w_rows_d.append(rr)
                w_cols_d.append(cc)
                w_diseq.append(score_pt)
            if layer_nm.startswith("spring") and (tclass in ("hot", "warm") or warm_excess > 5.0 or t_geo_max > 85.0):
                s_rows.append(rr)
                s_cols.append(cc)
                s_wt.append(1.0 + 0.03 * warm_excess + 0.02 * diseq)

    diseq_2d = physics._splat_points(
        shape,
        np.asarray(w_rows_d, np.float32),
        np.asarray(w_cols_d, np.float32),
        np.asarray(w_diseq, np.float32),
        sigma_px=8.0,
        normalize_density=True,
    )
    spring_2d = np.log1p(
        18.0
        * physics._splat_points(
            shape,
            np.asarray(s_rows, np.float32),
            np.asarray(s_cols, np.float32),
            np.asarray(s_wt, np.float32),
            sigma_px=6.0,
            normalize_density=False,
        )
    ).astype(np.float32)
    write_col(0, "hgvc_diseq_outflow_s8", diseq_2d[ys_fp, xs_fp])
    write_col(1, "hgvc_spring_vent_s6", spring_2d[ys_fp, xs_fp])

    # Paleo-geothermal sinter/silica/travertine vs Pleistocene pluvial tufa (channel 2 & mimic)
    with zipfile.ZipFile(req_files["paleo_geothermal_regional.zip"]) as z:
        p_csv = list(csv.DictReader(io.StringIO(z.read("Paleo_geothermal_final.csv").decode("utf-8-sig", "replace"))))
    sin_lons, sin_lats, sin_w = [], [], []
    tuf_lons, tuf_lats, tuf_w = [], [], []
    for r in p_csv:
        try:
            lon, lat = float(r["Long_deg_NAD83"]), float(r["Lat_deg_NAD83"])
        except (KeyError, ValueError):
            continue
        dt = (r.get("Deposit_type") or "").strip().lower()
        if "tufa" in dt:
            tuf_lons.append(lon)
            tuf_lats.append(lat)
            tuf_w.append(1.0)
        else:
            wt = 2.5 if "sinter" in dt else (2.0 if "silic" in dt else (1.4 if "travertine" in dt else 0.8))
            sin_lons.append(lon)
            sin_lats.append(lat)
            sin_w.append(wt)
    sx_u, sy_u = crs_transform("EPSG:4269", grid.crs, sin_lons, sin_lats)
    scols, srows = inv_tf * (np.asarray(sx_u), np.asarray(sy_u))
    sinter_2d = np.log1p(
        22.0 * physics._splat_points(shape, np.floor(srows), np.floor(scols), np.asarray(sin_w, np.float32), sigma_px=10.0)
    ).astype(np.float32)

    tx_u, ty_u = crs_transform("EPSG:4269", grid.crs, tuf_lons, tuf_lats)
    tcols, trows = inv_tf * (np.asarray(tx_u), np.asarray(ty_u))
    tufa_2d = np.log1p(
        22.0 * physics._splat_points(shape, np.floor(trows), np.floor(tcols), np.asarray(tuf_w, np.float32), sigma_px=10.0)
    ).astype(np.float32)
    write_col(2, "hgvc_sinter_decontam", sinter_2d[ys_fp, xs_fp] - 0.85 * tufa_2d[ys_fp, xs_fp])

    # 2 m temperature probe vertical conductive thermal gradient T2m - T1m (channel 3)
    with zipfile.ZipFile(req_files["2m_temperature_probe_INGENIOUS_regional_data.zip"]) as z:
        dbf_rows = physics._read_dbf_records(
            z.read("2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf")
        )
    plons, plats, pgrad = [], [], []
    for r in dbf_rows:
        try:
            lon, lat = float(r["LongDegree"]), float(r["LatDegreeN"])
            t2m = float(r["T2m"])
            dab = float(r["F2mDAB"])
        except (KeyError, ValueError):
            continue
        if not (-125.0 < lon < -110.0 and 34.0 < lat < 44.0):
            continue
        dz_t = 0.0
        for k1, mult in (("T1m", 1.0), ("T15m", 2.0)):
            try:
                v1 = float(r.get(k1, ""))
                if v1 > 0.5 and t2m > 0.5:
                    dz_t = max(t2m - v1, 0.0) * mult
                    break
            except ValueError:
                pass
        val_p = dz_t + 0.5 * max(dab, 0.0)
        if val_p > 0.01 or t2m > 18.0:
            plons.append(lon)
            plats.append(lat)
            pgrad.append(val_p)
    px_u, py_u = crs_transform("EPSG:4269", grid.crs, plons, plats)
    pcols, prows = inv_tf * (np.asarray(px_u), np.asarray(py_u))
    probe_2d = physics._splat_points(
        shape, np.floor(prows), np.floor(pcols), np.asarray(pgrad, np.float32), sigma_px=7.0, normalize_density=True
    )
    write_col(3, "hgvc_probe_vert_grad", probe_2d[ys_fp, xs_fp])

    # Hydraulic + basement up-dip feeder back-projection at 1.5 km and 3.0 km (channels 4 & 5)
    # Combined down-gradient outflow plume sampled at (y, x) - delta * u_up (downslope / down-basement-dip)
    outflow_2d = (diseq_2d + 0.45 * probe_2d + 0.35 * spring_2d + 0.25 * np.maximum(sinter_2d - tufa_2d, 0.0)).astype(np.float32)
    u_hy_y = 0.60 * upslope_y_fp + 0.40 * upbase_y_fp
    u_hy_x = 0.60 * upslope_x_fp + 0.40 * upbase_x_fp
    u_norm = np.hypot(u_hy_y, u_hy_x) + np.float32(1e-5)
    u_hy_y = (u_hy_y / u_norm).astype(np.float32)
    u_hy_x = (u_hy_x / u_norm).astype(np.float32)
    conduit_gate = (0.4 + 0.6 * np.tanh(0.5 * (zb_step_fp + grav_gate_fp))).astype(np.float32)

    feed_15 = physics._bilinear_at_fp(outflow_2d, ys_fp, xs_fp, -15.0 * u_hy_y, -15.0 * u_hy_x) * conduit_gate
    feed_30 = physics._bilinear_at_fp(outflow_2d, ys_fp, xs_fp, -30.0 * u_hy_y, -30.0 * u_hy_x) * conduit_gate
    write_col(4, "hgvc_updip_feeder_1p5km", feed_15)
    write_col(5, "hgvc_updip_feeder_3p0km", feed_30)

    # Explicit Non-Fault Mimic Control Index (channel 19): shoreline + pluvial tufa + playa evaporite brine
    mimic_fp = (0.45 * shore_pen_2d[ys_fp, xs_fp] + 0.30 * np.tanh(tufa_2d[ys_fp, xs_fp]) + 0.25 * np.tanh(playa_brine_fp)).astype(np.float32)
    write_col(19, "hgvc_mimic_playa_tufa_shore", mimic_fp)
    del (
        diseq_2d,
        spring_2d,
        sinter_2d,
        tufa_2d,
        probe_2d,
        outflow_2d,
        upslope_y_fp,
        upslope_x_fp,
        upbase_y_fp,
        upbase_x_fp,
        u_hy_y,
        u_hy_x,
        u_norm,
        conduit_gate,
        feed_15,
        feed_30,
        mimic_fp,
        shore_pen_2d,
        playa_flat_fp,
        playa_brine_fp,
        zb_step_fp,
        grav_gate_fp,
    )
    gc.collect()

    # ------------------------------------------------------------------
    # Block E: 1 m 3DEP LiDAR bajada polarity & crest/toe asymmetry (channels 13 & 14)
    # ------------------------------------------------------------------
    with rasterio.open(req_files["lidar_scarp_features_u8.tif"]) as ds:
        ex_max = ds.read(1)[ys_fp, xs_fp].astype(np.float32) / 255.0
        step_max = ds.read(3)[ys_fp, xs_fp].astype(np.float32) / 255.0
        lapneg = ds.read(4)[ys_fp, xs_fp].astype(np.float32)
        lappos = ds.read(5)[ys_fp, xs_fp].astype(np.float32)
        downf = ds.read(6)[ys_fp, xs_fp].astype(np.float32)
        upf = ds.read(7)[ys_fp, xs_fp].astype(np.float32)
        crossm = ds.read(8)[ys_fp, xs_fp].astype(np.float32)
        coh100 = ds.read(10)[ys_fp, xs_fp].astype(np.float32) / 255.0
        lid_valid = ds.read(12)[ys_fp, xs_fp] > 0

    lid_pol = np.where(
        lid_valid,
        (np.abs(downf - upf) / (crossm + 8.0)) * step_max * coh100,
        -1.0,
    ).astype(np.float32)
    lid_asym = np.where(
        lid_valid,
        ((lapneg - lappos) / (lapneg + lappos + 6.0)) * ex_max,
        -1.0,
    ).astype(np.float32)
    write_col(13, "hgvc_lidar_bajada_polarity", lid_pol, allow_sentinel_neg1=True)
    write_col(14, "hgvc_lidar_crest_asymmetry", lid_asym, allow_sentinel_neg1=True)
    del ex_max, step_max, lapneg, lappos, downf, upf, crossm, coh100, lid_valid, lid_pol, lid_asym
    gc.collect()

    # ------------------------------------------------------------------
    # Block F: Channel-normalized 10 m fluvial chi/ksn bridged along basement gravity strike (channel 16)
    # ------------------------------------------------------------------
    with rasterio.open(req_files["dem10_chi_100m_u8.tif"]) as ds:
        chan_n = ds.read(1).astype(np.float32)
        knick_n = ds.read(2).astype(np.float32)
        valid_chi = ds.read(4) > 0
    with rasterio.open(req_files["dem10_chi_100m_i16.tif"]) as ds:
        smax_raw = ds.read(1).astype(np.float32)
        smin_raw = ds.read(2).astype(np.float32)
        ksn_raw = ds.read(3).astype(np.float32)
        area_raw = ds.read(4).astype(np.float32)

    chan_mask = (chan_n > 0) & (ksn_raw > -1000) & valid_chi
    chi_step = np.where(smax_raw > -1000, np.maximum(smax_raw - np.maximum(smin_raw, 0.0), 0.0), 0.0).astype(np.float32)
    ksn = np.where(ksn_raw > -1000, np.maximum(ksn_raw, 0.0), 0.0).astype(np.float32)
    area = np.where(area_raw > -1000, np.maximum(area_raw, 0.0), 0.0).astype(np.float32)
    del smax_raw, smin_raw, ksn_raw, area_raw, chan_n

    w_ch = ndi.gaussian_filter(chan_mask.astype(np.float32), sigma=4.0, mode="constant") + np.float32(1e-5)
    ksn_res = np.where(chan_mask, np.maximum(np.log1p(ksn) - 0.25 * np.log1p(area / 1000.0), 0.0), 0.0).astype(np.float32)
    knick_e = (
        ndi.gaussian_filter((np.log1p(knick_n) * (0.5 + ksn_res) + 0.3 * np.log1p(chi_step / 60.0)).astype(np.float32), sigma=4.0, mode="constant")
        / w_ch
    ).astype(np.float32)
    del chan_mask, chi_step, ksn, area, w_ch, ksn_res, knick_n

    # Bridge knickzone energy along basement gravity strike (cos(theta_grav), sin(theta_grav))
    gs_x = np.cos(theta_grav_fp).astype(np.float32)
    gs_y = np.sin(theta_grav_fp).astype(np.float32)
    ke_c = knick_e[ys_fp, xs_fp]
    ke_s = 0.25 * (
        physics._bilinear_at_fp(knick_e, ys_fp, xs_fp, 3.5 * gs_y, 3.5 * gs_x)
        + physics._bilinear_at_fp(knick_e, ys_fp, xs_fp, -3.5 * gs_y, -3.5 * gs_x)
        + physics._bilinear_at_fp(knick_e, ys_fp, xs_fp, 7.0 * gs_y, 7.0 * gs_x)
        + physics._bilinear_at_fp(knick_e, ys_fp, xs_fp, -7.0 * gs_y, -7.0 * gs_x)
    )
    ke_f = 0.50 * (
        physics._bilinear_at_fp(knick_e, ys_fp, xs_fp, 4.5 * uflow_y_fp, 4.5 * uflow_x_fp)
        + physics._bilinear_at_fp(knick_e, ys_fp, xs_fp, -4.5 * uflow_y_fp, -4.5 * uflow_x_fp)
    )
    chi_bridge_fp = np.where(valid_chi[ys_fp, xs_fp], 0.55 * (ke_c + ke_s) - 0.40 * ke_f, -1.0).astype(np.float32)
    write_col(16, "hgvc_chi_strike_knick_bridge", chi_bridge_fp, allow_sentinel_neg1=True)
    del valid_chi, knick_e, gs_x, gs_y, ke_c, ke_s, ke_f, chi_bridge_fp, theta_grav_fp, uflow_y_fp, uflow_x_fp, c2_grav_fp, s2_grav_fp
    gc.collect()

    mm.flush()
    del mm
    tmp_path.replace(dat_path)

    meta_out = {
        "schema": HGVC_SCHEMA_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(HGVC_FEATURES),
        "hashes": hashes,
        "zero_catalogue_verified": True,
        "dist_known_fault_px_dropped_on_read": True,
        "cold_wells_rejected": int(n_cold_rejected),
        "hydrothermal_sinter_travertine_points": int(len(sin_w)),
        "pluvial_tufa_mimic_points_separated": int(len(tuf_w)),
        "probe2m_vertical_grad_points": int(len(pgrad)),
    }
    meta_path.write_text(json.dumps(meta_out, indent=2) + "\n")
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta_out


def poe_pool_hgvc(
    p_base: np.ndarray,
    m_base: np.ndarray,
    p_hgvc: np.ndarray,
    m_hgvc: np.ndarray,
    d_vis_act: np.ndarray,
    w_near: float = 0.68,
    w_far_boost: float = 0.18,
) -> tuple[np.ndarray, np.ndarray]:
    """Distance-adaptive Log-Odds Product-of-Experts pooling with blind-basin tail preservation."""
    far_gate = 1.0 / (1.0 + np.exp(-np.clip((d_vis_act - 20.0) / 5.0, -15.0, 15.0)))
    w_h = np.clip(np.float32(w_near) + np.float32(w_far_boost) * far_gate.astype(np.float32), 0.0, 0.92)
    w_b = np.float32(1.0) - w_h
    lp = w_b * adhr._logit(p_base) + w_h * adhr._logit(p_hgvc)
    lm = w_b * adhr._logit(m_base) + w_h * adhr._logit(m_hgvc)
    p_poe = adhr._expit(lp)
    m_poe = np.maximum(adhr._expit(lm), p_poe).astype(np.float32)
    return p_poe, m_poe


def verify_zero_test_quadrant_leakage(
    grid,
    X_phys_diff: ColumnSubsetView,
    X_hgvc_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int = 88501,
) -> bool:
    """Prove bit-for-bit prediction invariance when held-out test_region truth is scrambled."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    rng = np.random.default_rng(20261024)
    truth_orig = train_truth.copy()
    truth_scram = train_truth.copy()
    truth_scram[test_region] = rng.random(int(test_region.sum())) < 0.20

    sub_idx = np.flatnonzero((fp & test_region & ~visible)[ys_fp, xs_fp])[:4096]
    preds = []
    for t_cand in (truth_orig & train_regions, truth_scram & train_regions):
        wlaw = damagezone_envelope.fit_width_law(
            comp_len_fp, d_vis_fp, t_cand[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
        )
        dow = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
        clfs, regs = adhr._fit_dual_expectation_models(
            [X_phys_diff, X_hgvc_mm, X_vis22_mm, dow],
            (train_regions & ~visible)[ys_fp, xs_fp],
            t_cand,
            fp,
            seed=seed,
            max_zero_neg=15_000,
            n_ensemble=1,
        )
        preds.append(adhr._predict_dual_chunked(clfs, regs, [X_phys_diff, X_hgvc_mm, X_vis22_mm, dow], sub_idx))
    return bool(np.array_equal(preds[0][0], preds[1][0]) and np.array_equal(preds[0][1], preds[1][1]))


def predict_hgvc_all_arms_fold(
    grid,
    X_phys_mm: np.ndarray,
    X_phys_diff: ColumnSubsetView,
    X_hgvc_mm: np.ndarray,
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
) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    """Fit/load per-fold posteriors and return exact allocations for 2 controls + 3 preregistered arms."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    d_vis_act = d_vis_fp[act_idx]

    post_path = Path(cache_dir) / f"hgvc_fold_post_{fold_tag}_{HGVC_SCHEMA_VERSION}.npz"
    if post_path.is_file():
        z = np.load(post_path, allow_pickle=False)
        p_phys_44, m_phys_44 = z["p_phys_44"], z["m_phys_44"]
        p_full_67, m_full_67 = z["p_full_67"], z["m_full_67"]
        p_hgvc_phys, m_hgvc_phys = z["p_hgvc_phys"], z["m_hgvc_phys"]
        p_hgvc_full, m_hgvc_full = z["p_hgvc_full"], z["m_hgvc_full"]
    else:
        pop_tr_fp = train_truth[ys_fp, xs_fp]
        wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
        d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

        dom_phys_tr = train_regions[ys_fp, xs_fp]
        dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]

        # Base controls (exact H88-ADHR reproduction)
        c_p44, r_p44 = adhr._fit_dual_expectation_models(
            [X_phys_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 17, n_ensemble=1
        )
        p_phys_44, m_phys_44 = adhr._predict_dual_chunked(c_p44, r_p44, [X_phys_mm], act_idx)
        del c_p44, r_p44
        gc.collect()

        c_f67, r_f67 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 53, n_ensemble=1
        )
        p_full_67, m_full_67 = adhr._predict_dual_chunked(
            c_f67, r_f67, [X_phys_mm, X_vis22_mm, d_over_w_fp], act_idx
        )
        del c_f67, r_f67
        gc.collect()

        # HGVC zero-catalogue decontaminated hydrothermal conduit specialist (36 + 20 = 56 ch, 2-seed ensemble)
        c_hp, r_hp = adhr._fit_dual_expectation_models(
            [X_phys_diff, X_hgvc_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 117, n_ensemble=2
        )
        p_hgvc_phys, m_hgvc_phys = adhr._predict_dual_chunked(c_hp, r_hp, [X_phys_diff, X_hgvc_mm], act_idx)
        del c_hp, r_hp
        gc.collect()

        # HGVC joint hydrothermal + structural specialist (44 + 20 + 23 = 87 ch, 2-seed ensemble)
        c_hf, r_hf = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp],
            dom_struct_tr,
            train_truth,
            fp,
            seed=seed + 153,
            n_ensemble=2,
        )
        p_hgvc_full, m_hgvc_full = adhr._predict_dual_chunked(
            c_hf, r_hf, [X_phys_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp], act_idx
        )
        del c_hf, r_hf, d_over_w_fp
        gc.collect()

        np.savez_compressed(
            post_path,
            p_phys_44=p_phys_44,
            m_phys_44=m_phys_44,
            p_full_67=p_full_67,
            m_full_67=m_full_67,
            p_hgvc_phys=p_hgvc_phys,
            m_hgvc_phys=m_hgvc_phys,
            p_hgvc_full=p_hgvc_full,
            m_hgvc_full=m_hgvc_full,
        )

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]

    def _emit_arm(p_vec: np.ndarray, m_vec: np.ndarray, spacing: float = 2.05) -> tuple[np.ndarray, np.ndarray, dict]:
        pg = adhr.scatter_fp(p_vec, ay, ax, grid.shape)
        mg = adhr.scatter_fp(m_vec, ay, ax, grid.shape)
        alloc = emit.dinkelbach_allocate(
            pg, mg, allowed, budget=None, k_truth=k_est, min_spacing_px=spacing, dinkelbach_iters=6
        )
        return (
            alloc.emitted.astype(np.float32),
            pg,
            {"n_dots": int(alloc.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc.surrogate_dti)},
        )

    # Control 1: phys44_zero_cat
    sc_c1 = float(k_est) / max(float(p_phys_44.sum()), 1e-6)
    p_c1 = np.clip(p_phys_44 * np.float32(sc_c1), 0.0, 1.0).astype(np.float32)
    m_c1 = np.clip(m_phys_44 * np.float32(hid_ratio), p_c1, 1.0).astype(np.float32)

    # Control 2: h88_adhr_incumbent
    p_inc, m_inc = adhr._fuse_log_odds(p_full_67, m_full_67, p_phys_44, m_phys_44, k_est, beta_phys=0.35)

    # Exp 01: hgvc_zero_cat (56-ch decontaminated physics + HGVC-20, 0 catalogue features)
    sc_e1 = float(k_est) / max(float(p_hgvc_phys.sum()), 1e-6)
    p_e1 = np.clip(p_hgvc_phys * np.float32(sc_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_hgvc_phys * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)

    # Exp 02: hgvc_single_joint (87-ch HGVC joint + completeness fusion)
    p_e2, m_e2 = adhr._fuse_log_odds(p_hgvc_full, m_hgvc_full, p_hgvc_phys, m_hgvc_phys, k_est, beta_phys=0.38)

    # Exp 03: hgvc_poe_conduit (Distance-adaptive Log-Odds PoE + blind-basin tail preservation)
    p_phys_poe, m_phys_poe = poe_pool_hgvc(p_phys_44, m_phys_44, p_hgvc_phys, m_hgvc_phys, d_vis_act)
    p_full_poe, m_full_poe = poe_pool_hgvc(p_full_67, m_full_67, p_hgvc_full, m_hgvc_full, d_vis_act)
    p_e3, m_e3 = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_est, beta_phys=0.38)

    return {
        "phys44_zero_cat": _emit_arm(p_c1, m_c1),
        "h88_adhr_incumbent": _emit_arm(p_inc, m_inc),
        "exp01_hgvc_zero_cat": _emit_arm(p_e1, m_e1),
        "exp02_hgvc_single_joint": _emit_arm(p_e2, m_e2),
        "exp03_hgvc_poe_conduit": _emit_arm(p_e3, m_e3),
    }


def fit_and_emit_production_hgvc(
    grid,
    X_phys_mm: np.ndarray,
    X_phys_diff: ColumnSubsetView,
    X_hgvc_mm: np.ndarray,
    folds_by_seed: list[tuple[int, list[dict]]],
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    vis_by_seed: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]],
    cache_dir: Path,
    *,
    near_budget: int = 21_500,
    far_budget: int = 16_154,
    near_spacing_px: float = 2.85,
    far_spacing_px: float = 3.05,
    preplacement_gate=None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Strictly 4-quadrant out-of-fold production cross-fitting + H33-parity kernel-spaced allocation."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    d_fullcat = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    d_full_fp = d_fullcat[ys_fp, xs_fp]

    # Strict off-catalogue collar d_cat > 2.5 px (0 pixels at d_cat <= 2 px -> share_le2 == 0.0)
    act_mask_fp = d_full_fp > 2.5
    act_idx = np.flatnonzero(act_mask_fp)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]
    d_act = d_full_fp[act_idx]

    oof_cache = Path(cache_dir) / f"hgvc_prod_oof_{HGVC_SCHEMA_VERSION}.npz"
    if oof_cache.is_file():
        z = np.load(oof_cache, allow_pickle=False)
        p_phys_oof = z["p_phys_oof"]
        m_phys_oof = z["m_phys_oof"]
        p_full_oof = z["p_full_oof"]
        m_full_oof = z["m_full_oof"]
    else:
        # 1. 4-Quadrant out-of-fold cross-fitting for zero-catalogue HGVC hydrothermal specialist
        phys_oof_cache = Path(cache_dir) / f"hgvc_prod_phys_oof_{HGVC_SCHEMA_VERSION}.npz"
        if phys_oof_cache.is_file():
            zp = np.load(phys_oof_cache, allow_pickle=False)
            p_phys_oof, m_phys_oof = zp["p_phys_oof"], zp["m_phys_oof"]
        else:
            folds_q4 = folds_by_seed[0][1]
            p_phys_oof = np.zeros(act_idx.size, dtype=np.float32)
            m_phys_oof = np.zeros(act_idx.size, dtype=np.float32)
            covered_p = np.zeros(act_idx.size, dtype=bool)
            for q_idx, f_q in enumerate(folds_q4):
                tr_dom_q = (~f_q["region"])[ys_fp, xs_fp]
                c_q, r_q = adhr._fit_dual_expectation_models(
                    [X_phys_diff, X_hgvc_mm],
                    tr_dom_q,
                    full_cat & (~f_q["region"]),
                    fp,
                    seed=88610 + q_idx,
                    n_ensemble=2,
                )
                mask_q = f_q["region"][ay, ax]
                if q_idx == len(folds_q4) - 1:
                    mask_q = mask_q | (~covered_p)
                covered_p |= mask_q
                pq, mq = adhr._predict_dual_chunked(c_q, r_q, [X_phys_diff, X_hgvc_mm], act_idx[mask_q])
                p_phys_oof[mask_q] = pq
                m_phys_oof[mask_q] = mq
                del c_q, r_q, pq, mq
                gc.collect()
            np.savez_compressed(phys_oof_cache, p_phys_oof=p_phys_oof, m_phys_oof=m_phys_oof)

        # 2. 8-Fold (seeds 20+21 x 4 quadrants) out-of-fold cross-fitting for joint HGVC + structural head
        X_vis_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
            grid, full_cat, sense_src, scarp_fields, cache_dir, "prod_fullcat"
        )
        p_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        m_full_acc = np.zeros(act_idx.size, dtype=np.float64)

        for seed, folds in folds_by_seed:
            seed_oof_cache = Path(cache_dir) / f"hgvc_prod_struct_s{seed}_{HGVC_SCHEMA_VERSION}.npz"
            if seed_oof_cache.is_file():
                zs = np.load(seed_oof_cache, allow_pickle=False)
                p_seed, m_seed = zs["p_seed"], zs["m_seed"]
            else:
                vis_s = folds[0]["visible"]
                X_vis_s, dv_s, cl_s = vis_by_seed[seed]
                reg_all = np.zeros(grid.shape, dtype=bool)
                tr_all = np.zeros(grid.shape, dtype=bool)
                for f in folds:
                    reg_all |= f["region"]
                    tr_all |= f["truth"]
                p_seed = np.zeros(act_idx.size, dtype=np.float32)
                m_seed = np.zeros(act_idx.size, dtype=np.float32)
                covered_s = np.zeros(act_idx.size, dtype=bool)
                for q_idx, f_q in enumerate(folds):
                    tr_reg_q = reg_all & (~f_q["region"])
                    tr_tru_q = tr_all & (~f_q["region"])
                    wlaw_q = damagezone_envelope.fit_width_law(
                        cl_s, dv_s, tr_tru_q[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
                    )
                    dow_s_q = (dv_s / np.maximum(wlaw_q.half_width(cl_s), 1e-6)).astype(np.float32)
                    dom_s_q = (tr_reg_q & ~vis_s)[ys_fp, xs_fp]
                    cs_q, rs_q = adhr._fit_dual_expectation_models(
                        [X_phys_mm, X_hgvc_mm, X_vis_s, dow_s_q],
                        dom_s_q,
                        tr_tru_q,
                        fp,
                        seed=88700 + 10 * seed + q_idx,
                        n_ensemble=1,
                    )
                    mask_q = f_q["region"][ay, ax]
                    if q_idx == len(folds) - 1:
                        mask_q = mask_q | (~covered_s)
                    covered_s |= mask_q
                    dow_prod_q = (dv_prod / np.maximum(wlaw_q.half_width(cl_prod), 1e-6)).astype(np.float32)
                    pq, mq = adhr._predict_dual_chunked(
                        cs_q, rs_q, [X_phys_mm, X_hgvc_mm, X_vis_prod, dow_prod_q], act_idx[mask_q]
                    )
                    p_seed[mask_q] = pq
                    m_seed[mask_q] = mq
                    del cs_q, rs_q, dow_s_q, dow_prod_q, pq, mq
                    gc.collect()
                np.savez_compressed(seed_oof_cache, p_seed=p_seed, m_seed=m_seed)
            p_full_acc += p_seed
            m_full_acc += m_seed
            del p_seed, m_seed
            gc.collect()

        p_full_oof = (p_full_acc / len(folds_by_seed)).astype(np.float32)
        m_full_oof = (m_full_acc / len(folds_by_seed)).astype(np.float32)
        del X_vis_prod, dv_prod, cl_prod, p_full_acc, m_full_acc
        gc.collect()
        np.savez_compressed(
            oof_cache,
            p_phys_oof=p_phys_oof,
            m_phys_oof=m_phys_oof,
            p_full_oof=p_full_oof,
            m_full_oof=m_full_oof,
        )

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(
        p_full_oof, m_full_oof, p_phys_oof, m_phys_oof, k_prod, beta_phys=0.52, pi_unmapped=0.60
    )

    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0
    k_near = k_prod * (float(near_budget) / float(near_budget + far_budget))
    k_far = k_prod * (float(far_budget) / float(near_budget + far_budget))

    # Near stratum (2.5 < d_cat <= 25 px): hydrothermal conduit + OOF structural relay blend
    p_near_raw = 0.55 * p_fused[near_sel] + 0.45 * p_phys_oof[near_sel]
    m_near_raw = 0.55 * m_fused[near_sel] + 0.45 * m_phys_oof[near_sel]
    sc_near = float(k_near) / max(float(p_near_raw.sum()), 1e-6)
    p_near = np.clip(p_near_raw * np.float32(sc_near), 0.0, 1.0).astype(np.float32)
    m_near = np.clip(m_near_raw * np.float32(min(max(sc_near, 0.85), 1.20)), p_near, 1.0).astype(np.float32)

    # Blind-basin stratum (d_cat > 25 px): dominated by decontaminated HGVC-20 hydrothermal conduit physics
    p_far_raw = 0.15 * p_fused[far_sel] + 0.85 * p_phys_oof[far_sel]
    m_far_raw = 0.15 * m_fused[far_sel] + 0.85 * m_phys_oof[far_sel]
    sc_far = float(k_far) / max(float(p_far_raw.sum()), 1e-6)
    p_far = np.clip(p_far_raw * np.float32(sc_far), 0.0, 1.0).astype(np.float32)
    m_far = np.clip(m_far_raw * np.float32(min(max(sc_far, 0.85), 1.25)), p_far, 1.0).astype(np.float32)

    p_comb = np.empty_like(p_fused)
    m_comb = np.empty_like(m_fused)
    p_comb[near_sel] = p_near
    m_comb[near_sel] = m_near
    p_comb[far_sel] = p_far
    m_comb[far_sel] = m_far
    del p_fused, m_fused, p_near_raw, m_near_raw, p_far_raw, m_far_raw, p_near, m_near, p_far, m_far

    p_surface = adhr.scatter_fp(p_comb, ay, ax, grid.shape)
    m_surface = adhr.scatter_fp(m_comb, ay, ax, grid.shape)
    del p_comb, m_comb
    gc.collect()

    if preplacement_gate is not None:
        preplacement_gate(p_surface)

    allowed_near = np.zeros(grid.shape, dtype=bool)
    allowed_near[ay[near_sel], ax[near_sel]] = True
    allowed_far = np.zeros(grid.shape, dtype=bool)
    allowed_far[ay[far_sel], ax[far_sel]] = True

    alloc_near = emit.dinkelbach_allocate(
        p_surface, m_surface, allowed_near, budget=near_budget, k_truth=k_near, min_spacing_px=near_spacing_px, dinkelbach_iters=8
    )
    alloc_far = emit.dinkelbach_allocate(
        p_surface, m_surface, allowed_far, budget=far_budget, k_truth=k_far, min_spacing_px=far_spacing_px, dinkelbach_iters=8
    )
    emitted = np.clip(alloc_near.emitted.astype(np.float32) + alloc_far.emitted.astype(np.float32), 0.0, 1.0).astype(np.float32)
    dc_dots = d_fullcat[emitted > 0.5]
    n_dots = int((emitted > 0.5).sum())

    meta = {
        "n_dots": n_dots,
        "n_near_dots": int(alloc_near.n_dots),
        "n_far_dots": int(alloc_far.n_dots),
        "near_spacing_px": float(near_spacing_px),
        "far_spacing_px": float(far_spacing_px),
        "collar_min_d_cat_px": float(dc_dots.min()) if dc_dots.size else 0.0,
        "median_d_cat_px": float(np.median(dc_dots)) if dc_dots.size else 0.0,
        "share_le2": float((dc_dots <= 2.0).mean()) if dc_dots.size else 0.0,
        "share_gt10": float((dc_dots > 10.0).mean()) if dc_dots.size else 0.0,
        "share_gt25": float((dc_dots > 25.0).mean()) if dc_dots.size else 0.0,
        "k_truth_est": float(k_prod),
        "surrogate_dti_near": float(alloc_near.surrogate_dti),
        "surrogate_dti_far": float(alloc_far.surrogate_dti),
        "strictly_out_of_fold_both_heads": True,
    }
    return emitted, p_surface, meta
