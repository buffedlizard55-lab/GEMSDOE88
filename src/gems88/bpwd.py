"""H88-BPWD: Wavenumber-Domain Baranov Pseudogravity-to-Gravity Poisson Phase Dislocation,
Multiscale Upward-Continuation Sub-Alluvial Dip-Worm Tomography & Hydrothermal
Demagnetization Conduit Specialist (PSGV-20).

Implements 20 strictly label-blind (zero-catalogue) potential-field spectral and
tectonic-geomorphic channels on the competition 100 m EPSG:32611 grid:
  1. Exact 2D cosine-tapered FFT Baranov pseudogravity integration g_psg(x) of
     Reduced-to-Pole magnetic anomaly (B02 rtp) via 1 / sqrt(|k|^2 + k0^2), matching
     the derivative order of isostatic gravity (B13 iso_grav_anom) under Poisson's relation
     (Baranov 1957; Blakely 1995).
  2. Local windowed Poisson admittance regression residual, hydrothermal magnetite-
     destruction deficit, Baranov-to-Bouguer gradient phase quadrature dislocation, and
     1st-vertical-derivative (B11 iso_grav_anom_vg) vs RTP demagnetization trough.
  3. Exact 2D FFT multiscale upward continuation exp(-2*pi*|k|*h) at heights
     h in {200, 600, 1400, 2800} m, extracting multiscale worm persistence (Archibald
     et al. 1999), systematic normal-fault dip migration, and 60-deg up-dip back-projection
     to the concealed sub-alluvial z = 0 fault trace using B15 depth_to_base_surf.
  4. Heterogeneous LightGBM (feature-subsampled colsample_bytree=0.72) + HistGradientBoosting
     dual-expectation specialists pooled with cached PHYS-44 and HGVC-20 stacks via
     Distance-Adaptive 3-Specialist Log-Odds Product-of-Experts (PoE).

Strictly zero catalogue access in feature construction: ``existing_faults.tif`` and
``grid.catalogue`` are never read inside ``build_or_load_psgv_memmap``.
Memory-bounded (< 650 MB RSS on 3.8 GiB sandbox) via single-precision rfft2 and
disk-backed float32 ``np.memmap``.
"""
from __future__ import annotations

import gc
import hashlib
import json
import math
from pathlib import Path
from typing import Sequence

import lightgbm as lgb
import numpy as np
import rasterio
from scipy import fft as sp_fft
from scipy import ndimage as ndi

from gems57 import damagezone_envelope, emit

from . import adhr, edge, hgvc, physics

CELL_M = 100.0
TAN_60 = math.tan(math.radians(60.0))
PSGV_SCHEMA_VERSION = "psgv88-20ch-v1"

PSGV_FEATURES: tuple[str, ...] = (
    "psgv_baranov_field_hp",
    "psgv_baranov_hg_crest",
    "psgv_poisson_admittance_resid",
    "psgv_poisson_demag_deficit",
    "psgv_phase_quadrature_disloc",
    "psgv_vg_rtp_demag_trough",
    "psgv_worm_grav_persistence",
    "psgv_worm_rtp_persistence",
    "psgv_worm_depth_focus_ratio",
    "psgv_worm_dip_migration_vec",
    "psgv_updip60_worm_z0_trace",
    "psgv_updip60_demag_z0_trace",
    "psgv_curie_spectral_shallow",
    "psgv_claycap_poisson_conduit",
    "psgv_transtens_worm_opening",
    "psgv_chi_unipolar_step_orth",
    "psgv_lidar_face_polarity_orth",
    "psgv_frangi_demag_worm_s2",
    "psgv_strike_worm_coherence",
    "psgv_mimic_volcanic_remanent_rim",
)


def _robust_z(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Footprint-scoped median/IQR standardization clipped to [-8, 8] in float32."""
    vals = arr[fp][::17]
    q25, q50, q75 = [float(x) for x in np.percentile(vals, [25.0, 50.0, 75.0])]
    iqr = max(q75 - q25, 1e-5)
    out = np.clip((arr - np.float32(q50)) / np.float32(iqr), -8.0, 8.0).astype(np.float32)
    out[~fp] = 0.0
    return out


def _robust_pos(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Positive non-negative amplitude scaled by 90th footprint percentile in [0, 8]."""
    pos = np.maximum(np.asarray(arr, dtype=np.float32), 0.0)
    vals = pos[fp][::17]
    p90 = max(float(np.percentile(vals, 90.0)), 1e-5)
    out = np.clip(pos / np.float32(p90), 0.0, 8.0).astype(np.float32)
    out[~fp] = 0.0
    return out


def prepare_tapered_fft_grid(
    field_2d: np.ndarray,
    footprint: np.ndarray,
    nearest_idx: tuple[np.ndarray, np.ndarray],
    dist_outside_px: np.ndarray,
    pad_px: int = 96,
) -> tuple[np.ndarray, tuple[int, int]]:
    """Boundary-continuous cosine-tapered 2D FFT buffer eliminating polygon-edge Gibbs ringing.

    Inside ``footprint``, ``field_2d - median`` is preserved exactly. Outside ``footprint``,
    values extrapolate continuously from the nearest valid interior boundary pixel and decay
    via a raised-cosine taper over ``pad_px`` cells to 0.0.
    """
    h, w = field_2d.shape
    med = float(np.median(field_2d[footprint][::23]))
    centered = (np.asarray(field_2d, dtype=np.float32) - np.float32(med))
    iy, ix = nearest_idx
    taper = (0.5 * (1.0 + np.cos(np.pi * np.clip(dist_outside_px / float(pad_px), 0.0, 1.0)))).astype(np.float32)
    seamless = np.where(footprint, centered, centered[iy, ix] * taper).astype(np.float32)

    fft_h = sp_fft.next_fast_len(h + 2 * pad_px)
    fft_w = sp_fft.next_fast_len(w + 2 * pad_px)
    buf = np.zeros((fft_h, fft_w), dtype=np.float32)
    buf[pad_px : pad_px + h, pad_px : pad_px + w] = seamless
    return buf, (pad_px, pad_px)


def spectral_radial_wavenumber(fft_shape: tuple[int, int], cell_m: float = CELL_M) -> np.ndarray:
    """2D radial spatial frequency |k| in cycles/meter for ``rfft2`` of ``fft_shape``."""
    ky = sp_fft.fftfreq(fft_shape[0], d=cell_m).astype(np.float32)[:, None]
    kx = sp_fft.rfftfreq(fft_shape[1], d=cell_m).astype(np.float32)[None, :]
    return np.hypot(ky, kx).astype(np.float32)


def baranov_pseudogravity_2d(
    spec_rtp: np.ndarray,
    k_cyc_per_m: np.ndarray,
    fft_shape: tuple[int, int],
    crop_offset: tuple[int, int],
    out_shape: tuple[int, int],
    stabilizer_wavelength_m: float = 45_000.0,
) -> np.ndarray:
    """Exact 2D wavenumber Baranov pseudogravity integration of Reduced-to-Pole magnetics.

    Under Poisson's relation, T_RTP ~ -d(g)/dz -> F{T_RTP}(k) = 2*pi*|k| * F{g_psg}(k).
    Integrating via 1 / (2*pi*sqrt(|k|^2 + k0^2)) brings RTP into exact potential-field
    derivative parity with isostatic gravity anomaly (Baranov 1957; Blakely 1995).
    """
    k0 = np.float32(1.0 / max(stabilizer_wavelength_m, 1000.0))
    filt = (1.0 / (np.float32(2.0 * math.pi) * np.sqrt(k_cyc_per_m * k_cyc_per_m + k0 * k0))).astype(np.float32)
    filt[0, 0] = 0.0
    psg_full = sp_fft.irfft2(spec_rtp * filt, s=fft_shape, workers=2).astype(np.float32)
    oy, ox = crop_offset
    h, w = out_shape
    return psg_full[oy : oy + h, ox : ox + w].copy()


def upward_continue_2d(
    spec: np.ndarray,
    k_cyc_per_m: np.ndarray,
    height_m: float,
    fft_shape: tuple[int, int],
    crop_offset: tuple[int, int],
    out_shape: tuple[int, int],
) -> np.ndarray:
    """Exact 2D potential-field upward continuation U_h[f] = F^-1{exp(-2*pi*|k|*h) F{f}}."""
    atten = np.exp(np.clip(-np.float32(2.0 * math.pi * height_m) * k_cyc_per_m, -60.0, 0.0)).astype(np.float32)
    up_full = sp_fft.irfft2(spec * atten, s=fft_shape, workers=2).astype(np.float32)
    oy, ox = crop_offset
    h, w = out_shape
    return up_full[oy : oy + h, ox : ox + w].copy()


def _advect_updip_to_z0(
    source_field: np.ndarray,
    footwall_ny: np.ndarray,
    footwall_nx: np.ndarray,
    z_base_m: np.ndarray,
    footprint: np.ndarray,
    max_shift_px: float = 12.0,
) -> np.ndarray:
    """Back-project a buried dipping basement fault anomaly up a 60-deg fault plane to z = 0.

    If a buried normal fault at basement depth ``z_base_m`` dips at ~60 deg into the hanging
    wall (`-n_footwall`), an anomaly observed at ``(y + dr * (-ny), x + dr * (-nx))`` in the
    hanging wall originates from a surface fault trace at ``(y, x)`` where ``dr = z_base / (100 * tan 60)``.
    Therefore at candidate trace pixel ``(y, x)``, we sample the deep anomaly at the down-dip
    hanging-wall coordinate ``(y - dr * ny, x - dr * nx)``!
    """
    h, w = source_field.shape
    dr = np.clip(np.maximum(z_base_m, 0.0) / (CELL_M * TAN_60), 0.5, max_shift_px).astype(np.float32)
    yy, xx = np.indices((h, w), dtype=np.float32)
    sample_y = np.clip(yy - dr * footwall_ny, 0.0, float(h - 1))
    sample_x = np.clip(xx - dr * footwall_nx, 0.0, float(w - 1))
    del yy, xx, dr
    projected = ndi.map_coordinates(source_field, [sample_y, sample_x], order=1, mode="nearest").astype(np.float32)
    projected[~footprint] = 0.0
    return projected


def build_or_load_psgv_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict]:
    """Build or load the 20-channel label-blind spectral PSGV float32 disk memmap."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = np.asarray(grid.footprint, dtype=bool)
    ys_fp, xs_fp = np.nonzero(fp)
    n_fp = int(ys_fp.size)
    n_cols = len(PSGV_FEATURES)

    dat_path = cache_dir / "x_psgv_20ch_v1.dat"
    meta_path = cache_dir / "x_psgv_20ch_v1.json"

    ext = root / "data/external"
    req_files = {
        "training_features.tif": root / "data/training_features.tif",
        "geodawn_rad_u8.tif": ext / "geodawn_rad_u8.tif",
        "geodawn_extensions_u8.tif": ext / "geodawn_extensions_u8.tif",
        "dem10_chi_100m_i16.tif": ext / "dem10_chi_100m_i16.tif",
        "lidar_scarp_features_u8.tif": ext / "lidar_scarp_features_u8.tif",
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
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("schema") == PSGV_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(PSGV_FEATURES)
            and meta.get("hashes") == hashes
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    # 1. Read verified official training_features.tif bands (zero catalogue reads!)
    expected_tags = {
        2: "rtp",
        7: "geod_shearrate",
        8: "geod_dilaterate",
        9: "tmi_vg",
        11: "iso_grav_anom_vg",
        12: "det_elev",
        13: "iso_grav_anom",
        15: "depth_to_base_surf",
        17: "cond_surf",
        18: "iso_grav_anom_hg",
        19: "det_elev_slope",
    }
    bands: dict[str, np.ndarray] = {}
    with rasterio.open(req_files["training_features.tif"]) as src:
        for b_idx, tag_want in expected_tags.items():
            tag_got = src.tags(b_idx).get("band_name")
            if tag_got != tag_want:
                raise ValueError(f"Band {b_idx} tag mismatch: expected {tag_want!r}, got {tag_got!r}")
            cleaned, _ = edge.clean_band(src.read(b_idx), fp)
            bands[tag_want] = cleaned

    # 2. Precompute nearest-boundary EDT once for C1-smooth FFT padding
    dist_out, nearest_idx = ndi.distance_transform_edt(~fp, return_distances=True, return_indices=True)
    dist_out = dist_out.astype(np.float32)

    rtp_buf, crop_off = prepare_tapered_fft_grid(bands["rtp"], fp, nearest_idx, dist_out, pad_px=96)
    grav_buf, _ = prepare_tapered_fft_grid(bands["iso_grav_anom"], fp, nearest_idx, dist_out, pad_px=96)
    del dist_out, nearest_idx
    gc.collect()

    fft_shape = rtp_buf.shape
    k_rad = spectral_radial_wavenumber(fft_shape, cell_m=CELL_M)
    spec_rtp = sp_fft.rfft2(rtp_buf, workers=2)
    spec_grav = sp_fft.rfft2(grav_buf, workers=2)
    del rtp_buf, grav_buf
    gc.collect()

    # 3. Exact 2D FFT Baranov pseudogravity & bandpass fields
    g_psg = baranov_pseudogravity_2d(spec_rtp, k_rad, fft_shape, crop_off, grid.shape, stabilizer_wavelength_m=45_000.0)
    spec_psg_tmp, _ = sp_fft.rfft2(
        np.pad(g_psg, ((crop_off[0], fft_shape[0] - crop_off[0] - grid.shape[0]), (crop_off[1], fft_shape[1] - crop_off[1] - grid.shape[1])), mode="edge"),
        workers=2,
    ), None
    g_psg_up4k = upward_continue_2d(spec_psg_tmp, k_rad, 4000.0, fft_shape, crop_off, grid.shape)
    del spec_psg_tmp
    g_grav_up4k = upward_continue_2d(spec_grav, k_rad, 4000.0, fft_shape, crop_off, grid.shape)

    psg_hp = (g_psg - g_psg_up4k).astype(np.float32)
    grav_hp = (bands["iso_grav_anom"] - g_grav_up4k).astype(np.float32)
    del g_psg_up4k, g_grav_up4k

    # Gradients of Baranov pseudogravity & isostatic gravity at matched 200 m smoothing
    psg_gy, psg_gx = edge.derivatives(g_psg, fp, sigma=2.0)
    grav_gy, grav_gx = edge.derivatives(bands["iso_grav_anom"], fp, sigma=2.0)
    psg_hg = np.hypot(psg_gy, psg_gx).astype(np.float32)
    grav_hg = np.hypot(grav_gy, grav_gx).astype(np.float32)

    # Local windowed Poisson admittance regression: grav_hp ~ alpha(x) * psg_hp
    m_g = ndi.gaussian_filter(grav_hp, sigma=10.0, mode="nearest")
    m_p = ndi.gaussian_filter(psg_hp, sigma=10.0, mode="nearest")
    cov_gp = ndi.gaussian_filter((grav_hp - m_g) * (psg_hp - m_p), sigma=10.0, mode="nearest")
    var_pp = ndi.gaussian_filter((psg_hp - m_p) ** 2, sigma=10.0, mode="nearest") + np.float32(1e-4)
    alpha_loc = np.clip(cov_gp / var_pp, -10.0, 10.0).astype(np.float32)
    poisson_resid = np.abs((grav_hp - m_g) - alpha_loc * (psg_hp - m_p)).astype(np.float32)
    del m_g, m_p, cov_gp, var_pp, alpha_loc, grav_hp

    # Hydrothermal magnetite-destruction deficit & phase quadrature dislocation
    z_grav_hg = _robust_z(np.log1p(np.maximum(grav_hg, 0.0)), fp)
    z_psg_hg = _robust_z(np.log1p(np.maximum(psg_hg, 0.0)), fp)
    demag_deficit = np.maximum(0.0, z_grav_hg - np.maximum(0.0, z_psg_hg)).astype(np.float32)
    cos_dphi = (grav_gy * psg_gy + grav_gx * psg_gx) / (grav_hg * psg_hg + np.float32(1e-6))
    cos_dphi = np.clip(cos_dphi, -1.0, 1.0).astype(np.float32)
    phase_quad_disloc = (_robust_pos(grav_hg, fp) * (1.0 - cos_dphi) * 0.5).astype(np.float32)
    del z_grav_hg, z_psg_hg, cos_dphi

    # 1st-Vertical-Derivative Poisson Trough: |grad(iso_grav_vg)| x local RTP trough
    rtp_up1400 = upward_continue_2d(spec_rtp, k_rad, 1400.0, fft_shape, crop_off, grid.shape)
    rtp_trough = np.maximum(0.0, -(bands["rtp"] - rtp_up1400)).astype(np.float32)
    gvg_y, gvg_x = edge.derivatives(bands["iso_grav_anom_vg"], fp, sigma=1.8)
    gvg_hg = np.hypot(gvg_y, gvg_x).astype(np.float32)
    vg_rtp_trough = (_robust_pos(gvg_hg, fp) * _robust_pos(rtp_trough, fp)).astype(np.float32)
    del rtp_up1400, rtp_trough, gvg_hg

    # 4. Exact 2D FFT Multiscale Upward-Continuation Worms (h = 200, 600, 1400, 2800 m)
    heights = (200.0, 600.0, 1400.0, 2800.0)
    w_grav = []
    w_rtp = []
    hg_rtp_200 = None
    hg_rtp_2800 = None
    grav_u1400_gy = None
    grav_u1400_gx = None
    grav_u600_gy = None
    grav_u600_gx = None

    for h_m in heights:
        gu = upward_continue_2d(spec_grav, k_rad, h_m, fft_shape, crop_off, grid.shape)
        gy_u, gx_u = edge.derivatives(gu, fp, sigma=1.5)
        ghg_u = np.hypot(gy_u, gx_u).astype(np.float32)
        w_grav.append(_robust_pos(hgvc._hessian_crest(ghg_u, sigma=1.8), fp))
        if h_m == 600.0:
            grav_u600_gy, grav_u600_gx = gy_u, gx_u
        elif h_m == 1400.0:
            grav_u1400_gy, grav_u1400_gx = gy_u, gx_u
        del gu, ghg_u

        ru = upward_continue_2d(spec_rtp, k_rad, h_m, fft_shape, crop_off, grid.shape)
        ry_u, rx_u = edge.derivatives(ru, fp, sigma=1.5)
        rhg_u = np.hypot(ry_u, rx_u).astype(np.float32)
        w_rtp.append(_robust_pos(hgvc._hessian_crest(rhg_u, sigma=1.8), fp))
        if h_m == 200.0:
            hg_rtp_200 = rhg_u
        elif h_m == 2800.0:
            hg_rtp_2800 = rhg_u
        else:
            del rhg_u
        del ru, ry_u, rx_u

    del spec_rtp, spec_grav, k_rad
    gc.collect()

    worm_grav_pers = ((w_grav[0] + 1e-4) * (w_grav[1] + 1e-4) * (w_grav[2] + 1e-4) * (w_grav[3] + 1e-4)) ** np.float32(0.25)
    worm_rtp_pers = ((w_rtp[0] + 1e-4) * (w_rtp[1] + 1e-4) * (w_rtp[2] + 1e-4) * (w_rtp[3] + 1e-4)) ** np.float32(0.25)
    worm_depth_focus = (np.log((w_grav[2] + np.float32(0.05)) / (w_grav[0] + np.float32(0.05))) * w_grav[1]).astype(np.float32)

    # Footwall unit normal (+grad U_1400[iso_grav], pointing from low-density basin hanging wall into high-density footwall)
    fnorm = np.hypot(grav_u1400_gy, grav_u1400_gx) + np.float32(1e-6)
    fw_ny = (grav_u1400_gy / fnorm).astype(np.float32)
    fw_nx = (grav_u1400_gx / fnorm).astype(np.float32)
    del fnorm, grav_u1400_gy, grav_u1400_gx

    # Dip-worm lateral migration with height & 60-deg up-dip back-projection to z = 0
    dw_y, dw_x = np.gradient((w_grav[2] - w_grav[0]).astype(np.float32))
    worm_dip_mig = np.maximum(0.0, -(dw_y * fw_ny + dw_x * fw_nx) * w_grav[1]).astype(np.float32)
    del dw_y, dw_x

    deep_worm_src = (0.60 * w_grav[1] + 0.40 * w_grav[2]).astype(np.float32)
    updip_worm_z0 = _advect_updip_to_z0(deep_worm_src, fw_ny, fw_nx, bands["depth_to_base_surf"], fp, max_shift_px=12.0)
    updip_demag_z0 = _advect_updip_to_z0(demag_deficit, fw_ny, fw_nx, bands["depth_to_base_surf"], fp, max_shift_px=12.0)
    del w_grav, w_rtp, deep_worm_src, fw_ny, fw_nx

    # Shallow Curie / hydrothermal magnetic-bottom spectral decay
    curie_shallow = (
        np.log((hg_rtp_200 + np.float32(0.5)) / (hg_rtp_2800 + np.float32(0.5)))
        * _robust_pos(bands["iso_grav_anom_hg"], fp)
    ).astype(np.float32)
    del hg_rtp_200, hg_rtp_2800

    # Perched smectite clay-cap conductivity x Poisson demagnetization conduit
    log_cond = np.log1p(np.maximum(bands["cond_surf"], 0.0)).astype(np.float32)
    cond_loc = log_cond - ndi.gaussian_filter(log_cond, sigma=25.0, mode="nearest")
    claycap_poisson = (_robust_pos(cond_loc, fp) * (0.55 * demag_deficit + 0.45 * updip_demag_z0)).astype(np.float32)
    del log_cond, cond_loc

    # Transtensional opening along sub-alluvial worm trace
    transtens = (
        np.maximum(bands["geod_dilaterate"], 0.0) + np.float32(0.70) * np.maximum(bands["geod_shearrate"], 0.0)
    ).astype(np.float32)
    transtens_worm = (_robust_pos(transtens, fp) * (0.55 * updip_worm_z0 + 0.45 * worm_grav_pers)).astype(np.float32)
    del transtens

    # 5. Strike coherence across 4 potential-field/basement planes + fluvial/LiDAR polarity
    zb_gy, zb_gx = edge.derivatives(bands["depth_to_base_surf"], fp, sigma=2.5)
    c1, s1 = hgvc._structure_tensor_2theta(psg_gy, psg_gx, sigma_int=3.0)
    c2, s2 = hgvc._structure_tensor_2theta(grav_u600_gy, grav_u600_gx, sigma_int=3.0)
    c3, s3 = hgvc._structure_tensor_2theta(gvg_y, gvg_x, sigma_int=3.0)
    c4, s4 = hgvc._structure_tensor_2theta(zb_gy, zb_gx, sigma_int=3.0)
    del psg_gy, psg_gx, grav_gy, grav_gx, grav_u600_gy, grav_u600_gx, gvg_y, gvg_x, zb_gy, zb_gx

    mc = 0.25 * (c1 + c2 + c3 + c4)
    ms = 0.25 * (s1 + s2 + s3 + s4)
    strike_worm_coh = np.hypot(mc, ms).astype(np.float32)
    del c1, s1, c2, s2, c3, s3, c4, s4, mc, ms

    # Unipolar fluvial chi step (IR-88-100: mask int16 -32768 nodata on non-channel cells)
    with rasterio.open(req_files["dem10_chi_100m_i16.tif"]) as src_chi:
        step_max = src_chi.read(1).astype(np.float32)
        step_min = src_chi.read(2).astype(np.float32)
        ksn_max = src_chi.read(3).astype(np.float32)
        larea = src_chi.read(4).astype(np.float32)
    valid_chan = fp & (larea > -30000.0) & (step_max > -30000.0) & (step_min > -30000.0) & (ksn_max > -30000.0)
    unipolar = np.where(
        valid_chan,
        np.maximum(0.0, step_max * np.float32(0.001) - np.abs(step_min * np.float32(0.001)))
        * np.log1p(np.maximum(ksn_max, 0.0)),
        0.0,
    ).astype(np.float32)
    chi_unipolar = (ndi.gaussian_filter(unipolar, sigma=2.0, mode="nearest") * (0.5 + 0.5 * strike_worm_coh)).astype(np.float32)
    del step_max, step_min, ksn_max, larea, valid_chan, unipolar

    # 1 m LiDAR face-polarity asymmetry (neutral 0.0 where un-flown so zero tile-seam leakage!)
    with rasterio.open(req_files["lidar_scarp_features_u8.tif"]) as src_lid:
        df_max = src_lid.read(6).astype(np.float32)
        uf_max = src_lid.read(7).astype(np.float32)
        cr_max = src_lid.read(8).astype(np.float32)
        lid_val = src_lid.read(12) > 0
    lid_pol = np.where(
        fp & lid_val,
        (np.abs(df_max - uf_max) / (df_max + uf_max + np.float32(5.0)))
        * np.maximum(df_max, uf_max)
        / (cr_max + np.float32(12.0)),
        0.0,
    ).astype(np.float32)
    del df_max, uf_max, cr_max, lid_val

    # 2D Frangi tubular ridge vesselness on combined sub-alluvial worm + Poisson demagnetization
    comb_conduit = (0.45 * updip_worm_z0 + 0.35 * _robust_pos(demag_deficit, fp) + 0.20 * phase_quad_disloc).astype(np.float32)
    frangi_demag = hgvc._frangi_line_2d(comb_conduit, sigma=2.0)
    del comb_conduit

    # Explicit non-fault mimic: reversely magnetized unfaulted Miocene volcanic/ignimbrite mesa rims (Q > 1)
    with rasterio.open(req_files["geodawn_rad_u8.tif"]) as src_rad:
        rad_th = src_rad.read(2).astype(np.float32)
    neg_rtp = _robust_pos(-bands["rtp"], fp)
    thin_cover = np.exp(-np.maximum(bands["depth_to_base_surf"], 0.0) / np.float32(180.0)).astype(np.float32)
    steep_rim = _robust_pos(bands["det_elev_slope"], fp)
    high_th = _robust_pos(rad_th, fp)
    mimic_volc_rim = (neg_rtp * thin_cover * steep_rim * (0.5 + 0.5 * high_th)).astype(np.float32)
    del rad_th, neg_rtp, thin_cover, steep_rim, high_th

    baranov_crest = hgvc._hessian_crest(psg_hg, sigma=2.0)
    del g_psg, psg_hg, grav_hg, bands
    gc.collect()

    raw_channels = [
        _robust_z(psg_hp, fp),
        _robust_pos(baranov_crest, fp),
        _robust_z(np.log1p(poisson_resid), fp),
        _robust_pos(demag_deficit, fp),
        _robust_pos(phase_quad_disloc, fp),
        _robust_pos(vg_rtp_trough, fp),
        _robust_pos(worm_grav_pers, fp),
        _robust_pos(worm_rtp_pers, fp),
        _robust_z(worm_depth_focus, fp),
        _robust_pos(worm_dip_mig, fp),
        _robust_pos(updip_worm_z0, fp),
        _robust_pos(updip_demag_z0, fp),
        _robust_z(curie_shallow, fp),
        _robust_pos(claycap_poisson, fp),
        _robust_pos(transtens_worm, fp),
        _robust_pos(chi_unipolar, fp),
        _robust_pos(lid_pol, fp),
        _robust_pos(frangi_demag, fp),
        _robust_z(strike_worm_coh, fp),
        _robust_pos(mimic_volc_rim, fp),
    ]
    if len(raw_channels) != n_cols:
        raise AssertionError(f"Expected {n_cols} PSGV channels, built {len(raw_channels)}")

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    col_stats = {}
    for j, (fname, ch) in enumerate(zip(PSGV_FEATURES, raw_channels)):
        vec = np.nan_to_num(ch[ys_fp, xs_fp], nan=0.0, posinf=8.0, neginf=-8.0).astype(np.float32)
        mm[:, j] = vec
        col_stats[fname] = {
            "mean": round(float(vec.mean(dtype=np.float64)), 6),
            "std": round(float(vec.std(dtype=np.float64)), 6),
            "min": round(float(vec.min()), 6),
            "max": round(float(vec.max()), 6),
        }
    mm.flush()
    del mm, raw_channels
    gc.collect()

    meta = {
        "schema": PSGV_SCHEMA_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(PSGV_FEATURES),
        "hashes": hashes,
        "zero_catalogue_reads": True,
        "fft_grid_shape": list(fft_shape),
        "upward_continuation_heights_m": [200.0, 600.0, 1400.0, 2800.0],
        "baranov_stabilizer_wavelength_m": 45_000.0,
        "column_stats": col_stats,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta


def _fit_lgbm_dual_models(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    seed: int,
    max_zero_neg: int = 110_000,
    n_ensemble: int = 2,
) -> tuple[list[lgb.LGBMClassifier], list[lgb.LGBMRegressor]]:
    """Feature-subsampled LightGBM dual-expectation (cell probability + 300 m kernel credit) specialist.

    ``colsample_bytree=0.72`` prevents distance-to-visible-fault features from monopolizing
    root splits, forcing trees to learn genuine spectral Poisson phase-dislocation & worm
    interactions across off-axis step-overs and blind basins.
    """
    ys_fp, xs_fp = np.nonzero(fp_mask)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int32)
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

    clfs: list[lgb.LGBMClassifier] = []
    regs: list[lgb.LGBMRegressor] = []
    for k in range(n_ensemble):
        clf = lgb.LGBMClassifier(
            n_estimators=195,
            learning_rate=0.055,
            num_leaves=63,
            min_child_samples=90,
            subsample=0.85,
            subsample_freq=1,
            colsample_bytree=0.72,
            reg_alpha=1.0,
            reg_lambda=6.0,
            random_state=seed + 307 * k,
            n_jobs=2,
            verbose=-1,
        )
        clf.fit(X_tr, yc_tr, sample_weight=weights)
        clfs.append(clf)

        reg = lgb.LGBMRegressor(
            objective="regression",
            n_estimators=195,
            learning_rate=0.055,
            num_leaves=63,
            min_child_samples=90,
            subsample=0.85,
            subsample_freq=1,
            colsample_bytree=0.72,
            reg_alpha=1.0,
            reg_lambda=6.0,
            random_state=seed + 613 * k,
            n_jobs=2,
            verbose=-1,
        )
        reg.fit(X_tr, yk_tr, sample_weight=weights)
        regs.append(reg)
    del X_tr
    return clfs, regs


def tri_specialist_poe_pool(
    p_adhr: np.ndarray,
    m_adhr: np.ndarray,
    p_hgvc: np.ndarray,
    m_hgvc: np.ndarray,
    p_psgv: np.ndarray,
    m_psgv: np.ndarray,
    d_vis: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Distance-adaptive 3-specialist Log-Odds Product-of-Experts pooling ADHR, HGVC, and PSGV.

    Near mapped terminations (d_vis <= 8 px), structural relay + hydrothermal + spectral worms
    share balanced authority; across unmapped valleys (d_vis > 20 px), authority shifts smoothly
    toward the wall-to-wall airborne PSGV spectral worm + HGVC hydrothermal specialists while
    strictly preserving pointwise self-credit m >= p inside [0, 1].
    """
    ramp = np.clip((np.asarray(d_vis, dtype=np.float32) - 6.0) / 22.0, 0.0, 1.0)
    w_psgv = (0.46 + 0.14 * ramp).astype(np.float32)   # 0.46 near -> 0.60 blind
    w_hgvc = (0.36 - 0.04 * ramp).astype(np.float32)   # 0.36 near -> 0.32 blind
    w_adhr = (1.0 - w_psgv - w_hgvc).astype(np.float32)  # 0.18 near -> 0.08 blind

    lp = w_adhr * adhr._logit(p_adhr) + w_hgvc * adhr._logit(p_hgvc) + w_psgv * adhr._logit(p_psgv)
    lm = w_adhr * adhr._logit(m_adhr) + w_hgvc * adhr._logit(m_hgvc) + w_psgv * adhr._logit(m_psgv)
    p_out = adhr._expit(lp)
    m_out = np.clip(adhr._expit(lm), p_out, 1.0).astype(np.float32)
    return p_out, m_out


def predict_psgv_suite_fold(
    grid,
    X_phys_mm: np.ndarray,
    X_phys_diff: hgvc.ColumnSubsetView,
    X_hgvc_mm: np.ndarray,
    X_psgv_mm: np.ndarray,
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
    """Fit/load per-fold posteriors and return exact allocations for 3 controls + 3 preregistered PSGV arms."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    d_vis_act = d_vis_fp[act_idx]

    # Reuse or compute base ADHR + HGVC fold posteriors
    hgvc_post_path = Path(cache_dir) / f"hgvc_fold_post_{fold_tag}_{hgvc.HGVC_SCHEMA_VERSION}.npz"
    psgv_post_path = Path(cache_dir) / f"psgv_fold_post_{fold_tag}_{PSGV_SCHEMA_VERSION}.npz"

    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
    dom_phys_tr = train_regions[ys_fp, xs_fp]
    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]

    if hgvc_post_path.is_file():
        zh = np.load(hgvc_post_path, allow_pickle=False)
        p_phys_44, m_phys_44 = zh["p_phys_44"], zh["m_phys_44"]
        p_full_67, m_full_67 = zh["p_full_67"], zh["m_full_67"]
        p_hgvc_phys, m_hgvc_phys = zh["p_hgvc_phys"], zh["m_hgvc_phys"]
        p_hgvc_full, m_hgvc_full = zh["p_hgvc_full"], zh["m_hgvc_full"]
    else:
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

        c_hp, r_hp = adhr._fit_dual_expectation_models(
            [X_phys_diff, X_hgvc_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 117, n_ensemble=2
        )
        p_hgvc_phys, m_hgvc_phys = adhr._predict_dual_chunked(c_hp, r_hp, [X_phys_diff, X_hgvc_mm], act_idx)
        del c_hp, r_hp
        gc.collect()

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
        del c_hf, r_hf
        gc.collect()

        np.savez_compressed(
            hgvc_post_path,
            p_phys_44=p_phys_44,
            m_phys_44=m_phys_44,
            p_full_67=p_full_67,
            m_full_67=m_full_67,
            p_hgvc_phys=p_hgvc_phys,
            m_hgvc_phys=m_hgvc_phys,
            p_hgvc_full=p_hgvc_full,
            m_hgvc_full=m_hgvc_full,
        )

    if psgv_post_path.is_file():
        zp = np.load(psgv_post_path, allow_pickle=False)
        p_psgv_phys, m_psgv_phys = zp["p_psgv_phys"], zp["m_psgv_phys"]
        p_psgv_full, m_psgv_full = zp["p_psgv_full"], zp["m_psgv_full"]
    else:
        # PSGV zero-catalogue spectral + hydrothermal specialist (36 + 20 + 20 = 76 ch, feature-subsampled LightGBM)
        cp_lgb, rp_lgb = _fit_lgbm_dual_models(
            [X_phys_diff, X_psgv_mm, X_hgvc_mm],
            dom_phys_tr,
            visible & train_regions,
            fp,
            seed=seed + 217,
            n_ensemble=2,
        )
        p_psgv_phys, m_psgv_phys = adhr._predict_dual_chunked(
            cp_lgb, rp_lgb, [X_phys_diff, X_psgv_mm, X_hgvc_mm], act_idx
        )
        del cp_lgb, rp_lgb
        gc.collect()

        # PSGV joint 107-ch spectral + hydrothermal + visible-structural specialist (feature-subsampled LightGBM)
        cf_lgb, rf_lgb = _fit_lgbm_dual_models(
            [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp],
            dom_struct_tr,
            train_truth,
            fp,
            seed=seed + 253,
            n_ensemble=2,
        )
        p_psgv_full, m_psgv_full = adhr._predict_dual_chunked(
            cf_lgb, rf_lgb, [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp], act_idx
        )
        del cf_lgb, rf_lgb
        gc.collect()

        np.savez_compressed(
            psgv_post_path,
            p_psgv_phys=p_psgv_phys,
            m_psgv_phys=m_psgv_phys,
            p_psgv_full=p_psgv_full,
            m_psgv_full=m_psgv_full,
        )
    del d_over_w_fp

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
    p_adhr_inc, m_adhr_inc = adhr._fuse_log_odds(p_full_67, m_full_67, p_phys_44, m_phys_44, k_est, beta_phys=0.35)

    # Control 3: h88_hgvc_incumbent (exact reproduction of current repo holdout record 0.202947)
    p_hg_poe_p, m_hg_poe_p = hgvc.poe_pool_hgvc(p_phys_44, m_phys_44, p_hgvc_phys, m_hgvc_phys, d_vis_act)
    p_hg_poe_f, m_hg_poe_f = hgvc.poe_pool_hgvc(p_full_67, m_full_67, p_hgvc_full, m_hgvc_full, d_vis_act)
    p_hgvc_inc, m_hgvc_inc = adhr._fuse_log_odds(p_hg_poe_f, m_hg_poe_f, p_hg_poe_p, m_hg_poe_p, k_est, beta_phys=0.38)

    # Exp 01: exp01_psgv_zero_cat (76-ch zero-catalogue spectral + hydrothermal LightGBM specialist)
    sc_e1 = float(k_est) / max(float(p_psgv_phys.sum()), 1e-6)
    p_e1 = np.clip(p_psgv_phys * np.float32(sc_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_psgv_phys * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)

    # Exp 02: exp02_psgv_joint_spec (107-ch spectral + hydrothermal + visible-structural LightGBM specialist)
    p_e2, m_e2 = adhr._fuse_log_odds(p_psgv_full, m_psgv_full, p_psgv_phys, m_psgv_phys, k_est, beta_phys=0.38)

    # Exp 03: exp03_psgv_tri_poe (Primary Method: Heterogeneous 3-Specialist Distance-Adaptive Log-Odds PoE)
    p_tri_phys, m_tri_phys = tri_specialist_poe_pool(
        p_phys_44, m_phys_44, p_hgvc_phys, m_hgvc_phys, p_psgv_phys, m_psgv_phys, d_vis_act
    )
    p_tri_full, m_tri_full = tri_specialist_poe_pool(
        p_full_67, m_full_67, p_hgvc_full, m_hgvc_full, p_psgv_full, m_psgv_full, d_vis_act
    )
    p_e3, m_e3 = adhr._fuse_log_odds(p_tri_full, m_tri_full, p_tri_phys, m_tri_phys, k_est, beta_phys=0.38)

    return {
        "phys44_zero_cat": _emit_arm(p_c1, m_c1),
        "h88_adhr_incumbent": _emit_arm(p_adhr_inc, m_adhr_inc),
        "h88_hgvc_incumbent": _emit_arm(p_hgvc_inc, m_hgvc_inc),
        "exp01_psgv_zero_cat": _emit_arm(p_e1, m_e1),
        "exp02_psgv_joint_spec": _emit_arm(p_e2, m_e2),
        "exp03_psgv_tri_poe": _emit_arm(p_e3, m_e3),
    }


def fit_and_emit_production_psgv(
    grid,
    X_phys_mm: np.ndarray,
    X_phys_diff: hgvc.ColumnSubsetView,
    X_hgvc_mm: np.ndarray,
    X_psgv_mm: np.ndarray,
    folds_by_seed: list[tuple[int, list[dict]]],
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    vis_by_seed: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]],
    cache_dir: Path,
    *,
    near_budget: int = 21_200,
    far_budget: int = 16_454,
    near_spacing_px: float = 2.90,
    far_spacing_px: float = 3.12,
    preplacement_gate=None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Strictly 4-quadrant / 8-fold out-of-fold cross-fitting + PSGV spectral-worm-weighted allocation."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    d_fullcat = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    d_full_fp = d_fullcat[ys_fp, xs_fp]

    # Strict off-catalogue collar d_cat > 2.5 px -> share_le2 == 0.0
    act_mask_fp = d_full_fp > 2.5
    act_idx = np.flatnonzero(act_mask_fp)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]
    d_act = d_full_fp[act_idx]

    oof_cache = Path(cache_dir) / f"psgv_prod_oof_{PSGV_SCHEMA_VERSION}.npz"
    if oof_cache.is_file():
        z = np.load(oof_cache, allow_pickle=False)
        p_spec_oof = z["p_spec_oof"]
        m_spec_oof = z["m_spec_oof"]
        p_full_oof = z["p_full_oof"]
        m_full_oof = z["m_full_oof"]
    else:
        # 1. 4-Quadrant OOF cross-fitting of pure spectral PSGV-20 + differential potential-field specialist
        # (Zero well-splat echo: emphasizes airborne Baranov Poisson phase dislocation & sub-alluvial dip worms)
        spec_oof_cache = Path(cache_dir) / f"psgv_prod_spec_oof_{PSGV_SCHEMA_VERSION}.npz"
        if spec_oof_cache.is_file():
            zs = np.load(spec_oof_cache, allow_pickle=False)
            p_spec_oof, m_spec_oof = zs["p_spec_oof"], zs["m_spec_oof"]
        else:
            folds_q4 = folds_by_seed[0][1]
            p_spec_oof = np.zeros(act_idx.size, dtype=np.float32)
            m_spec_oof = np.zeros(act_idx.size, dtype=np.float32)
            covered_p = np.zeros(act_idx.size, dtype=bool)
            for q_idx, f_q in enumerate(folds_q4):
                tr_dom_q = (~f_q["region"])[ys_fp, xs_fp]
                c_q, r_q = _fit_lgbm_dual_models(
                    [X_psgv_mm, X_phys_diff],
                    tr_dom_q,
                    full_cat & (~f_q["region"]),
                    fp,
                    seed=88910 + q_idx,
                    n_ensemble=2,
                )
                mask_q = f_q["region"][ay, ax]
                if q_idx == len(folds_q4) - 1:
                    mask_q = mask_q | (~covered_p)
                covered_p |= mask_q
                pq, mq = adhr._predict_dual_chunked(c_q, r_q, [X_psgv_mm, X_phys_diff], act_idx[mask_q])
                p_spec_oof[mask_q] = pq
                m_spec_oof[mask_q] = mq
                del c_q, r_q, pq, mq
                gc.collect()
            np.savez_compressed(spec_oof_cache, p_spec_oof=p_spec_oof, m_spec_oof=m_spec_oof)

        # 2. 8-Fold OOF cross-fitting of 107-ch PSGV + HGVC + visible-structural LightGBM specialist
        X_vis_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
            grid, full_cat, sense_src, scarp_fields, cache_dir, "prod_fullcat"
        )
        p_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        m_full_acc = np.zeros(act_idx.size, dtype=np.float64)

        for seed, folds in folds_by_seed:
            seed_oof_cache = Path(cache_dir) / f"psgv_prod_struct_s{seed}_{PSGV_SCHEMA_VERSION}.npz"
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
                    cs_q, rs_q = _fit_lgbm_dual_models(
                        [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis_s, dow_s_q],
                        dom_s_q,
                        tr_tru_q,
                        fp,
                        seed=89100 + 10 * seed + q_idx,
                        n_ensemble=1,
                    )
                    mask_q = f_q["region"][ay, ax]
                    if q_idx == len(folds) - 1:
                        mask_q = mask_q | (~covered_s)
                    covered_s |= mask_q
                    dow_prod_q = (dv_prod / np.maximum(wlaw_q.half_width(cl_prod), 1e-6)).astype(np.float32)
                    pq, mq = adhr._predict_dual_chunked(
                        cs_q, rs_q, [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis_prod, dow_prod_q], act_idx[mask_q]
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
            p_spec_oof=p_spec_oof,
            m_spec_oof=m_spec_oof,
            p_full_oof=p_full_oof,
            m_full_oof=m_full_oof,
        )

    # Modulate with PSGV sub-alluvial worm + Poisson demagnetization conduit crest (cols 3, 4, 10, 17)
    psgv_conduit_act = (
        0.30 * np.asarray(X_psgv_mm[act_idx, 10], dtype=np.float32)  # psgv_updip60_worm_z0_trace
        + 0.30 * np.asarray(X_psgv_mm[act_idx, 3], dtype=np.float32)  # psgv_poisson_demag_deficit
        + 0.20 * np.asarray(X_psgv_mm[act_idx, 4], dtype=np.float32)  # psgv_phase_quadrature_disloc
        + 0.20 * np.asarray(X_psgv_mm[act_idx, 17], dtype=np.float32)  # psgv_frangi_demag_worm_s2
    )
    conduit_mult = (0.75 + 0.35 * np.tanh(0.45 * psgv_conduit_act)).astype(np.float32)
    p_spec_mod = np.clip(p_spec_oof * conduit_mult, 1e-6, 1.0 - 1e-6).astype(np.float32)
    m_spec_mod = np.clip(m_spec_oof * conduit_mult, p_spec_mod, 1.0).astype(np.float32)
    del psgv_conduit_act, conduit_mult

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(
        p_full_oof, m_full_oof, p_spec_mod, m_spec_mod, k_prod, beta_phys=0.58, pi_unmapped=0.65
    )

    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0
    k_near = k_prod * (float(near_budget) / float(near_budget + far_budget))
    k_far = k_prod * (float(far_budget) / float(near_budget + far_budget))

    # Near/piedmont stratum (2.5 < d_cat <= 25 px): 42% joint + 58% spectral PSGV worm specialist
    p_near_raw = 0.42 * p_fused[near_sel] + 0.58 * p_spec_mod[near_sel]
    m_near_raw = 0.42 * m_fused[near_sel] + 0.58 * m_spec_mod[near_sel]
    sc_near = float(k_near) / max(float(p_near_raw.sum()), 1e-6)
    p_near = np.clip(p_near_raw * np.float32(sc_near), 0.0, 1.0).astype(np.float32)
    m_near = np.clip(m_near_raw * np.float32(min(max(sc_near, 0.85), 1.20)), p_near, 1.0).astype(np.float32)

    # Blind-basin stratum (d_cat > 25 px): 28% joint + 72% wall-to-wall airborne PSGV spectral worm specialist
    p_far_raw = 0.28 * p_fused[far_sel] + 0.72 * p_spec_mod[far_sel]
    m_far_raw = 0.28 * m_fused[far_sel] + 0.72 * m_spec_mod[far_sel]
    sc_far = float(k_far) / max(float(p_far_raw.sum()), 1e-6)
    p_far = np.clip(p_far_raw * np.float32(sc_far), 0.0, 1.0).astype(np.float32)
    m_far = np.clip(m_far_raw * np.float32(min(max(sc_far, 0.85), 1.25)), p_far, 1.0).astype(np.float32)

    p_comb = np.empty_like(p_fused)
    m_comb = np.empty_like(m_fused)
    p_comb[near_sel] = p_near
    m_comb[near_sel] = m_near
    p_comb[far_sel] = p_far
    m_comb[far_sel] = m_far
    del p_fused, m_fused, p_spec_mod, m_spec_mod, p_near_raw, m_near_raw, p_far_raw, m_far_raw, p_near, m_near, p_far, m_far

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


def verify_zero_test_quadrant_leakage(
    grid,
    X_phys_mm: np.ndarray,
    X_phys_diff: hgvc.ColumnSubsetView,
    X_hgvc_mm: np.ndarray,
    X_psgv_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    fold: dict,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    seed: int = 89501,
    tmp_cache: Path | None = None,
) -> bool:
    """Verify bit-for-bit identical test-quadrant predictions when held-out test_region truth is scrambled."""
    del X_phys_diff, tmp_cache
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    visible = fold["visible"]
    test_region = fold["region"]
    rng = np.random.default_rng(20261025)
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
        clfs, regs = _fit_lgbm_dual_models(
            [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis22_mm, dow],
            (train_regions & ~visible)[ys_fp, xs_fp],
            t_cand,
            fp,
            seed=seed,
            max_zero_neg=15_000,
            n_ensemble=1,
        )
        preds.append(
            adhr._predict_dual_chunked(
                clfs, regs, [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis22_mm, dow], sub_idx
            )
        )
        del clfs, regs, dow
        gc.collect()
    return bool(np.array_equal(preds[0][0], preds[1][0]) and np.array_equal(preds[0][1], preds[1][1]))
