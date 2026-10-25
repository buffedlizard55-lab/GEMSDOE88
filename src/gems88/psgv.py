"""H88-PSGV: 2D FFT Wavenumber-Domain Baranov Pseudogravity-to-Bouguer Analytic
Phase Dislocation, Multi-Depth Spectral Upward Continuation & 3-Specialist
Hydrothermal Conduit Product-of-Experts (PSGV-20).

Physical Motivation & Literature Basis
--------------------------------------
1. Baranov Wavenumber Pseudogravity Transformation (Baranov 1957, *Geophysics*
   22(2), 359-382; Blakely 1995, *Potential Theory in Gravity and Magnetic
   Applications*, Cambridge Univ. Press):
   By Poisson's relation, for a subsurface contact where density contrast
   Delta_rho(x) and magnetization contrast Delta_M(x) share the same geometry
   (an unfaulted granitic pluton boundary or unaltered volcanic-sedimentary
   lithologic contact), the vertical gravity anomaly g_z and the Reduced-to-Pole
   magnetic anomaly RTP satisfy in the 2D wavenumber domain k = (k_x, k_y),
   |k| = sqrt(k_x^2 + k_y^2) > 0:
       g_psg_hat(k) = C * RTP_hat(k) / (|k| + k_0)
   Consequently, across an unfaulted lithologic contact, the horizontal gradient
   of observed isostatic gravity grad_H(g_obs) and the horizontal gradient of
   Baranov pseudogravity grad_H(g_psg) are collinear and in-phase.
   Conversely, along a concealed geothermal fault conduit beneath Quaternary
   alluvial fill (Faulds & Hinz 2015; Ponce & Glen 2002), ascending 120-250 C
   hydrothermal fluids alter ferrimagnetic titanomagnetite (Fe3O4) into
   paramagnetic/antiferromagnetic hematite, pyrite, and smectite clay
   (Delta_M -> 0) while preserving or silica-sealing the basement density step
   (Delta_rho != 0). This produces a sharp wavenumber Baranov pseudogravity
   deficit (z(grad_H g_obs) - z(grad_H g_psg) > 0) and a 2D Riesz/Hilbert
   monogenic phase dislocation along the concealed fault trace.

2. Multi-Depth Spectral Upward Continuation & Miller-Singh Tilt-Angle Zero
   Crossing (Miller & Singh 1994, *J. Appl. Geophys.*; Salem et al. 2007,
   *Leading Edge*):
   Using exact 2D real FFT upward continuation exp(-|k| * z) at depths
   z in {200 m, 800 m, 2500 m, 4000 m} on a cosine-tapered reflectively padded
   grid, we separate shallow fault-damage zones from mid-basin horst-bounding
   master faults, compute the difference between gravity and pseudogravity
   tilt angles theta_grav - theta_psg, isolate the steep-contact tilt zero
   contour exp(-|theta_grav| / 0.22) * |grad_H g_obs|, and back-project deep
   spectral steps up a 60-degree normal-fault dip to their surface rupture locus.

3. Named Non-Fault Mimic Suppression (`psgv_mimic_rev_volc_mesa_playa`):
   Explicitly isolates:
   - Reversely magnetized Tertiary volcanic mesa rims and basalt flows (high
     Koenigsberger ratio Q > 1, where extreme negative RTP coincides with high
     topographic mesa-rim slope and low geodetic strain),
   - Pleistocene Lake Lahontan (~1330 m) and Lake Bonneville (~1555 m) shoreline
     carbonate tufa benches, and
   - Flat closed-basin playa evaporite brine pans.

Zero-Leakage Guarantee
----------------------
`build_or_load_psgv_memmap` NEVER reads `existing_faults.tif` or any distance-
to-catalogue column. Every channel is computed strictly from potential-field,
topographic, electromagnetic, and temperature/geochemical layers.
"""
from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.fft import fftfreq, irfft2, rfft2, rfftfreq
from scipy.ndimage import distance_transform_edt, gaussian_filter

from gems57 import damagezone_envelope, emit, grid as grid_mod
from . import adhr, hgvc, physics
import sklearn.ensemble._hist_gradient_boosting.binning as _sk_binning

_ORIG_FIND_BINNING_THRESHOLDS = _sk_binning._find_binning_thresholds


def _vectorized_find_binning_thresholds(col_data, max_bins, sample_weight=None):
    """Bit-identical vectorized replacement for scikit-learn's 254-call loop over _weighted_percentile."""
    if sample_weight is None:
        return _ORIG_FIND_BINNING_THRESHOLDS(col_data, max_bins, None)
    missing_mask = np.isnan(col_data)
    if missing_mask.any():
        col_data = col_data[~missing_mask]
        sample_weight = sample_weight[~missing_mask]
    nnz_sw = sample_weight != 0
    col_data = col_data[nnz_sw]
    sample_weight = sample_weight[nnz_sw]
    sort_idx = np.argsort(col_data)
    col_data = col_data[sort_idx]
    sample_weight = sample_weight[sort_idx]
    distinct_values = np.unique(col_data).astype(_sk_binning.X_DTYPE)
    if len(distinct_values) <= 1:
        return np.asarray([])
    if len(distinct_values) <= max_bins:
        bin_thresholds = _sk_binning.sliding_window_view(distinct_values, 2).mean(axis=1)
    else:
        percentiles = np.linspace(0, 100, num=max_bins + 1)[1:-1]
        bin_thresholds = np.asarray(
            _sk_binning._weighted_percentile(col_data, sample_weight, percentiles, average=True)
        )
    unique_bin_values = np.unique(bin_thresholds)
    if unique_bin_values.shape[0] != bin_thresholds.shape[0]:
        bin_thresholds = unique_bin_values
    np.clip(bin_thresholds, a_min=None, a_max=_sk_binning.ALMOST_INF, out=bin_thresholds)
    return bin_thresholds


_sk_binning._find_binning_thresholds = _vectorized_find_binning_thresholds

PSGV_SCHEMA_VERSION = "psgv88-20ch-v1"

# Reflective padding to 5-smooth FFT dimensions:
# H = 3730 + 2*55 = 3840 = 2^8 * 3 * 5
# W = 3292 + 2*82 = 3456 = 2^7 * 3^3
PAD_Y = 55
PAD_X = 82

PSGV_FEATURE_NAMES: tuple[str, ...] = (
    "psgv_baranov_field_z200",         # 00: 2D FFT Baranov pseudogravity anomaly (z=200m - z=4000m)
    "psgv_baranov_hgrad_z200",         # 01: Horizontal gradient magnitude of Baranov pseudogravity at z=200m
    "psgv_grav_minus_psg_deficit",     # 02: z(iso_grav_hg) - z(baranov_hgrad_z200) magnetite-destruction deficit
    "psgv_monogenic_phase_disloc",     # 03: |grad_H g_obs| * (1 - cos_angle(grad_H g_obs, grad_H g_psg))
    "psgv_spectral_depth_slice_shallow",  # 04: 2D FFT shallow (200-800m) gravity + RTP vertical-derivative crest
    "psgv_spectral_depth_slice_mid",   # 05: 2D FFT mid-basin (800-2500m) gravity + pseudogravity vertical-derivative crest
    "psgv_upcont_tilt_angle_diff",     # 06: Miller-Singh tilt angle difference atan(dz_g/|grad_g|) - atan(dz_psg/|grad_psg|)
    "psgv_tilt_zero_distance_decay",   # 07: Salem et al. tilt zero-crossing steep fault contact indicator
    "psgv_parker_admittance_resid",    # 08: Wavenumber-bandpass basement-relief gravity admittance residual
    "psgv_updip60_spectral_conduit",   # 09: 60-deg up-dip projection of mid-basin Baranov deficit + gravity step
    "psgv_riesz_congruency_crest",     # 10: Multi-scale 2D Riesz transform phase congruency across k-space octaves
    "psgv_demag_clay_psg_conduit",     # 11: Triple hydrothermal conduit: Baranov deficit * clay-cap resid * TMI demag
    "psgv_updip_geotherm_psg_focus",   # 12: Up-dip advected geothermometer/2m-probe heat focused on Baranov deficit
    "psgv_sinter_on_psg_step",         # 13: Tufa-decontaminated opaline sinter coupled with Baranov pseudogravity step
    "psgv_kostrov_coulomb_psg_shear",  # 14: Kostrov geodetic dilation+shear projected onto spectral gravity-psg strike
    "psgv_zbase_psg_orthog_relay",     # 15: Orthogonal relay transfer |grad_H g_obs x grad_H g_psg| across stepovers
    "psgv_lidar_bajada_psg_align",     # 16: 1m LiDAR bajada scarp polarity aligned with Baranov deficit strike (-1 sentinel)
    "psgv_chi_knick_psg_bridge",       # 17: 10m chi/ksn knickzone bridged along spectral gravity-psg strike (-1 sentinel)
    "psgv_spectral_vesselness_s3",     # 18: 2D Frangi vesselness (sigma=3 px) of composite spectral conduit field
    "psgv_mimic_rev_volc_mesa_playa",  # 19: Named non-fault mimic: reversely magnetized volcanic mesa rims + tufa + playa
)
PSGV_FEATURES = PSGV_FEATURE_NAMES


def _robust_z_fp(arr2d: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Footprint-standardized robust z-score clipped to [-6, 6]."""
    v = np.asarray(arr2d[fp], dtype=np.float64)
    v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    scale = max(1.4826 * mad, float(np.std(v, dtype=np.float64)), 1e-6)
    out = np.zeros_like(arr2d, dtype=np.float32)
    out[fp] = np.clip((v - med) / scale, -6.0, 6.0).astype(np.float32)
    return out


def _positive_norm_fp(arr2d: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Map footprint distribution to [0, 1.5] via robust P50..P98 scaling."""
    v = np.asarray(arr2d[fp], dtype=np.float64)
    v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
    p50 = float(np.percentile(v, 50.0))
    p98 = float(np.percentile(v, 98.0))
    span = max(p98 - p50, 1e-6)
    out = np.zeros_like(arr2d, dtype=np.float32)
    out[fp] = np.clip((v - p50) / span, 0.0, 1.5).astype(np.float32)
    return out


def _read_inpainted_band(
    src: rasterio.DatasetReader,
    band: int,
    fp: np.ndarray,
    fp_edt_inds: np.ndarray,
    *,
    zero_mean: bool = True,
) -> np.ndarray:
    """Read a band and fill outside-footprint/nodata cells using precomputed EDT indices."""
    raw = src.read(band).astype(np.float32)
    valid = fp & np.isfinite(raw) & (np.abs(raw) < 1e15)
    if not np.all(valid[fp]):
        fp_med = float(np.median(raw[valid])) if np.any(valid) else 0.0
        raw[fp & (~valid)] = fp_med
    out = raw[fp_edt_inds[0], fp_edt_inds[1]].astype(np.float32, copy=False)
    if zero_mean:
        med = float(np.median(out[fp]))
        out -= med
    return out


def _make_cosine_taper(h: int, w: int, pad_y: int, pad_x: int) -> np.ndarray:
    """2D separable Hann cosine taper over the reflective padding border."""
    wy = np.ones(h + 2 * pad_y, dtype=np.float32)
    wx = np.ones(w + 2 * pad_x, dtype=np.float32)
    if pad_y > 0:
        t = 0.5 * (1.0 - np.cos(np.pi * np.arange(pad_y, dtype=np.float32) / float(pad_y)))
        wy[:pad_y] = t
        wy[-pad_y:] = t[::-1]
    if pad_x > 0:
        t = 0.5 * (1.0 - np.cos(np.pi * np.arange(pad_x, dtype=np.float32) / float(pad_x)))
        wx[:pad_x] = t
        wx[-pad_x:] = t[::-1]
    return wy[:, None] * wx[None, :]


def _pad_taper_rfft2(arr2d: np.ndarray, taper: np.ndarray) -> np.ndarray:
    """Reflect-pad, apply cosine edge taper, and compute 2D real FFT."""
    padded = np.pad(arr2d, ((PAD_Y, PAD_Y), (PAD_X, PAD_X)), mode="reflect")
    padded *= taper
    return rfft2(padded, workers=2)


def _irfft2_unpad(spec: np.ndarray, h: int, w: int) -> np.ndarray:
    """Invert 2D real FFT and crop reflective padding back to (h, w)."""
    hp = h + 2 * PAD_Y
    wp = w + 2 * PAD_X
    full = irfft2(spec, s=(hp, wp), workers=2)
    return full[PAD_Y : PAD_Y + h, PAD_X : PAD_X + w].astype(np.float32, copy=False)


def _frangi_vesselness_2d(
    field: np.ndarray, sigma: float, fp: np.ndarray, fp_edt_inds: np.ndarray
) -> np.ndarray:
    """2D Frangi tubular ridge filter on a positive scalar field."""
    f = field[fp_edt_inds[0], fp_edt_inds[1]].astype(np.float32, copy=False)
    hxx = gaussian_filter(f, sigma=sigma, order=(0, 2), mode="nearest") * (sigma ** 2)
    hyy = gaussian_filter(f, sigma=sigma, order=(2, 0), mode="nearest") * (sigma ** 2)
    hxy = gaussian_filter(f, sigma=sigma, order=(1, 1), mode="nearest") * (sigma ** 2)
    tr = hxx + hyy
    det = hxx * hyy - hxy * hxy
    disc = np.sqrt(np.maximum(0.25 * tr * tr - det, 0.0))
    l1 = 0.5 * tr - disc
    l2 = 0.5 * tr + disc
    swap = np.abs(l1) > np.abs(l2)
    lam1 = np.where(swap, l2, l1)
    lam2 = np.where(swap, l1, l2)
    rb = lam1 / (lam2 + np.where(lam2 >= 0, 1e-6, -1e-6))
    s2 = lam1 * lam1 + lam2 * lam2
    c2 = max(float(np.percentile(s2[fp], 75.0)), 1e-6)
    v = np.where(
        lam2 < 0.0,
        np.exp(-(rb * rb) / (2.0 * 0.5 * 0.5)) * (1.0 - np.exp(-s2 / (2.0 * c2))),
        0.0,
    ).astype(np.float32)
    v[~fp] = 0.0
    return v


def build_or_load_psgv_memmap(
    root: Path,
    grid: grid_mod.Grid,
    cache_dir: Path | None = None,
) -> tuple[np.memmap, dict[str, Any]]:
    """Build or load the 20-channel PSGV-20 feature matrix on active footprint pixels."""
    cdir = Path(cache_dir) if cache_dir is not None else (root / ".cache" / "gems88_psgv")
    cdir.mkdir(parents=True, exist_ok=True)
    mm_path = cdir / f"X_psgv20_{PSGV_SCHEMA_VERSION}.f32.mmap"
    meta_path = cdir / f"X_psgv20_{PSGV_SCHEMA_VERSION}.meta.json"

    fp = grid.footprint
    h, w = grid.shape
    n_fp = int(fp.sum())
    n_ch = len(PSGV_FEATURE_NAMES)

    if mm_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("version") == PSGV_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_ch]
            and meta.get("feature_names") == list(PSGV_FEATURE_NAMES)
        ):
            mm = np.memmap(mm_path, dtype=np.float32, mode="r", shape=(n_fp, n_ch))
            return mm, meta

    X_hgvc, _ = hgvc.build_or_load_hgvc_memmap(root, grid, root / ".cache" / "gems88_hgvc")
    hgvc_idx = {name: i for i, name in enumerate(hgvc.HGVC_FEATURES)}

    def _unpack_hgvc(col_name: str) -> np.ndarray:
        out = np.zeros((h, w), dtype=np.float32)
        out[fp] = np.asarray(X_hgvc[:, hgvc_idx[col_name]], dtype=np.float32)
        return out

    # Precompute nearest-footprint EDT indices once (int32 to minimize RAM)
    _, edt_inds_i64 = distance_transform_edt(~fp, return_indices=True)
    fp_edt_inds = edt_inds_i64.astype(np.int32)
    del edt_inds_i64
    gc.collect()

    tmp_path = cdir / f"X_psgv20_{PSGV_SCHEMA_VERSION}.tmp.mmap"
    mm = np.memmap(tmp_path, dtype=np.float32, mode="w+", shape=(n_fp, n_ch))

    def _write_ch(j: int, ch2d: np.ndarray) -> None:
        col = np.asarray(ch2d[fp], dtype=np.float32)
        col = np.nan_to_num(col, nan=0.0, posinf=6.0, neginf=-6.0)
        mm[:, j] = col

    tf_path = root / "data" / "training_features.tif"
    with rasterio.open(tf_path) as src:
        rtp = _read_inpainted_band(src, 2, fp, fp_edt_inds, zero_mean=True)
        geod_shear = _read_inpainted_band(src, 7, fp, fp_edt_inds, zero_mean=False)
        geod_dilat = _read_inpainted_band(src, 8, fp, fp_edt_inds, zero_mean=False)
        grav = _read_inpainted_band(src, 13, fp, fp_edt_inds, zero_mean=True)
        zbase = np.maximum(_read_inpainted_band(src, 15, fp, fp_edt_inds, zero_mean=False), 0.0)
        grav_hg = _read_inpainted_band(src, 18, fp, fp_edt_inds, zero_mean=False)
        slope = _read_inpainted_band(src, 19, fp, fp_edt_inds, zero_mean=False)

    # Construct 2D wavenumber grid on reflectively padded (3840 x 3456) domain
    hp = h + 2 * PAD_Y
    wp = w + 2 * PAD_X
    taper = _make_cosine_taper(h, w, PAD_Y, PAD_X)
    ky = (2.0 * np.pi * fftfreq(hp, d=1.0)).astype(np.float32)[:, None]
    kx = (2.0 * np.pi * rfftfreq(wp, d=1.0)).astype(np.float32)[None, :]
    K = np.hypot(ky, kx).astype(np.float32)
    k0 = float(2.0 * np.pi / 600.0)

    rtp_std_val = max(float(np.std(rtp[fp], dtype=np.float64)), 1e-6)
    grav_std_val = max(float(np.std(grav[fp], dtype=np.float64)), 1e-6)
    F_rtp = _pad_taper_rfft2((rtp / rtp_std_val).astype(np.float32), taper)
    F_grav = _pad_taper_rfft2((grav / grav_std_val).astype(np.float32), taper)

    up_z2 = np.exp(-2.0 * K).astype(np.float32)
    up_z8 = np.exp(-8.0 * K).astype(np.float32)
    up_z25 = np.exp(-25.0 * K).astype(np.float32)
    up_z40 = np.exp(-40.0 * K).astype(np.float32)

    inv_K = (1.0 / (K + k0)).astype(np.float32)
    inv_K[0, 0] = 0.0
    F_psg_z2 = (F_rtp * inv_K * (up_z2 - up_z40)).astype(np.complex64)
    F_grav_z2 = (F_grav * (up_z2 - up_z40)).astype(np.complex64)

    # Channel 00: Baranov pseudogravity field at z=200m (band-passed vs 4000m)
    psg_z2 = _irfft2_unpad(F_psg_z2, h, w)
    ch00_baranov_field = _robust_z_fp(psg_z2, fp)
    _write_ch(0, ch00_baranov_field)
    del psg_z2, ch00_baranov_field

    # Spectral horizontal and vertical derivatives of Baranov pseudogravity & Bouguer/isostatic gravity
    psg_gx = _irfft2_unpad(1j * kx * F_psg_z2, h, w)
    psg_gy = _irfft2_unpad(1j * ky * F_psg_z2, h, w)
    psg_gz = _irfft2_unpad(K * F_psg_z2, h, w)
    psg_hgrad = np.hypot(psg_gx, psg_gy).astype(np.float32)

    grav_gx = _irfft2_unpad(1j * kx * F_grav_z2, h, w)
    grav_gy = _irfft2_unpad(1j * ky * F_grav_z2, h, w)
    grav_gz = _irfft2_unpad(K * F_grav_z2, h, w)
    grav_hgrad_spec = np.hypot(grav_gx, grav_gy).astype(np.float32)

    # Channel 01: Horizontal gradient magnitude of Baranov pseudogravity at z=200m
    ch01_baranov_hgrad = _robust_z_fp(psg_hgrad, fp)
    _write_ch(1, ch01_baranov_hgrad)

    # Channel 02: Hydrothermal magnetite-destruction Baranov pseudogravity deficit
    z_grav_step = _robust_z_fp(0.5 * _robust_z_fp(grav_hg, fp) + 0.5 * _robust_z_fp(grav_hgrad_spec, fp), fp)
    ch02_grav_minus_psg = _robust_z_fp(z_grav_step - 0.80 * ch01_baranov_hgrad, fp)
    _write_ch(2, ch02_grav_minus_psg)
    del z_grav_step, ch01_baranov_hgrad, grav_hg

    # Channel 03: Monogenic / gradient-orientation phase dislocation between gravity and pseudogravity
    denom_dot = (grav_hgrad_spec * psg_hgrad) + 1e-6
    cos_ang = np.clip((grav_gx * psg_gx + grav_gy * psg_gy) / denom_dot, -1.0, 1.0)
    ch03_phase_disloc = _robust_z_fp(_positive_norm_fp(grav_hgrad_spec, fp) * (1.0 - cos_ang), fp)
    _write_ch(3, ch03_phase_disloc)
    del cos_ang, ch03_phase_disloc

    # Channel 15: Orthogonal relay-ramp transfer |grad_H g_obs x grad_H g_psg| across stepovers
    cross_mag = np.abs(grav_gx * psg_gy - grav_gy * psg_gx) / denom_dot
    orthog_relay = cross_mag * np.sqrt(_positive_norm_fp(grav_hgrad_spec, fp) * _positive_norm_fp(psg_hgrad, fp))
    _write_ch(15, _robust_z_fp(orthog_relay, fp))
    del psg_gx, psg_gy, denom_dot, cross_mag, orthog_relay
    gc.collect()

    # Channel 04: 2D FFT shallow-crustal (200m - 800m) vertical-derivative spectral slice
    shallow_grav_vd = _irfft2_unpad(K * F_grav * (up_z2 - up_z8), h, w)
    shallow_rtp_vd = _irfft2_unpad(K * F_rtp * (up_z2 - up_z8), h, w)
    ch04_shallow_slice = _robust_z_fp(
        np.hypot(_positive_norm_fp(np.abs(shallow_grav_vd), fp), _positive_norm_fp(np.abs(shallow_rtp_vd), fp)),
        fp,
    )
    _write_ch(4, ch04_shallow_slice)
    del shallow_grav_vd, shallow_rtp_vd, ch04_shallow_slice

    # Channel 05: 2D FFT mid-basin (800m - 2500m) vertical-derivative spectral slice
    mid_grav_vd = _irfft2_unpad(K * F_grav * (up_z8 - up_z25), h, w)
    mid_psg_vd = _irfft2_unpad(K * F_rtp * inv_K * (up_z8 - up_z25), h, w)
    mid_grav_hg = np.hypot(
        _irfft2_unpad(1j * kx * F_grav * (up_z8 - up_z25), h, w),
        _irfft2_unpad(1j * ky * F_grav * (up_z8 - up_z25), h, w),
    )
    ch05_mid_slice = _robust_z_fp(
        0.65 * _robust_z_fp(mid_grav_hg, fp) + 0.35 * _robust_z_fp(np.abs(mid_grav_vd) + np.abs(mid_psg_vd), fp),
        fp,
    )
    _write_ch(5, ch05_mid_slice)
    del mid_grav_vd, mid_psg_vd, mid_grav_hg, F_rtp, inv_K, up_z40
    gc.collect()

    # Channel 06: Upward-continued Miller-Singh (1994) tilt-angle difference (theta_grav - theta_psg)
    theta_grav = np.arctan2(grav_gz, grav_hgrad_spec + 1e-5).astype(np.float32)
    theta_psg = np.arctan2(psg_gz, psg_hgrad + 1e-5).astype(np.float32)
    ch06_tilt_diff = _robust_z_fp(np.abs(theta_grav - theta_psg) * _positive_norm_fp(grav_hgrad_spec, fp), fp)
    _write_ch(6, ch06_tilt_diff)
    del psg_gz, psg_hgrad, theta_psg, ch06_tilt_diff

    # Channel 07: Salem et al. (2007) tilt-angle zero-crossing steep-fault contact indicator
    tilt_zero_prox = np.exp(-np.abs(theta_grav) / 0.22).astype(np.float32) * _positive_norm_fp(grav_hgrad_spec, fp)
    ch07_tilt_zero = _robust_z_fp(tilt_zero_prox, fp)
    _write_ch(7, ch07_tilt_zero)
    del grav_gz, theta_grav, tilt_zero_prox

    # Channel 08: Wavenumber-bandpass Parker-style basement-relief gravity admittance residual
    zbase_zero_mean = zbase - float(np.median(zbase[fp]))
    zbase_std_val = max(float(np.std(zbase_zero_mean[fp], dtype=np.float64)), 1e-6)
    F_zbase = _pad_taper_rfft2((zbase_zero_mean / zbase_std_val).astype(np.float32), taper)
    del zbase_zero_mean
    zbase_band = _irfft2_unpad(F_zbase * (up_z2 - up_z25), h, w)
    del F_zbase
    grav_band = _irfft2_unpad(F_grav * (up_z2 - up_z25), h, w)
    del F_grav, up_z2, up_z8, up_z25
    cov_gz = float(np.mean(grav_band[fp].astype(np.float64) * zbase_band[fp].astype(np.float64)))
    var_zz = max(float(np.mean(zbase_band[fp].astype(np.float64) ** 2)), 1e-6)
    admittance_alpha = cov_gz / var_zz
    parker_resid = np.abs(grav_band - admittance_alpha * zbase_band) * _positive_norm_fp(grav_hgrad_spec, fp)
    _write_ch(8, _robust_z_fp(parker_resid, fp))
    del zbase_band, grav_band, parker_resid, grav, grav_hgrad_spec
    gc.collect()

    # Channel 10: Multi-scale 2D Riesz transform phase congruency across k-space octaves
    F_comp = (F_grav_z2 - 0.55 * F_psg_z2).astype(np.complex64)
    del F_grav_z2, F_psg_z2, taper
    rx_kernel = (1j * kx / (K + 1e-6)).astype(np.complex64)
    ry_kernel = (1j * ky / (K + 1e-6)).astype(np.complex64)
    sum_even = np.zeros((h, w), dtype=np.float32)
    sum_odd = np.zeros((h, w), dtype=np.float32)
    sum_amp = np.zeros((h, w), dtype=np.float32)
    for lam_px in (3.5, 8.0, 18.0):
        k_center = float(2.0 * np.pi / lam_px)
        band = np.exp(-0.5 * (np.log((K + 1e-5) / k_center) / 0.55) ** 2).astype(np.float32)
        band[0, 0] = 0.0
        even = _irfft2_unpad(F_comp * band, h, w)
        odd_x = _irfft2_unpad(F_comp * band * rx_kernel, h, w)
        odd_y = _irfft2_unpad(F_comp * band * ry_kernel, h, w)
        odd = np.hypot(odd_x, odd_y)
        amp = np.hypot(even, odd) + 1e-5
        sum_even += even
        sum_odd += odd
        sum_amp += amp
    riesz_pc = np.hypot(sum_even, sum_odd) / (sum_amp + 0.05 * float(np.median(sum_amp[fp])))
    ch10_riesz_pc = _robust_z_fp(riesz_pc, fp)
    _write_ch(10, ch10_riesz_pc)
    del F_comp, rx_kernel, ry_kernel, K, kx, ky, sum_even, sum_odd, sum_amp, riesz_pc
    gc.collect()

    # Channel 09: 60-degree normal-fault up-dip back-projection of mid-basin spectral step + Baranov deficit
    deep_step_source = np.maximum(0.0, 0.55 * ch02_grav_minus_psg + 0.45 * ch05_mid_slice)
    del ch05_mid_slice
    gy_zb, gx_zb = np.gradient(gaussian_filter(zbase, sigma=3.0, mode="nearest"))
    gnorm_zb = np.hypot(gx_zb, gy_zb) + 1e-6
    ux_up = (-gx_zb / gnorm_zb).astype(np.float32)
    uy_up = (-gy_zb / gnorm_zb).astype(np.float32)
    del gx_zb, gy_zb, gnorm_zb
    zbase_m = np.where(zbase > 50.0, zbase, zbase * 1000.0)
    shift_px = np.clip(zbase_m / (100.0 * np.sqrt(3.0)), 0.0, 12.0).astype(np.float32)
    del zbase_m
    yy, xx = np.indices((h, w), dtype=np.int32)
    src_y = np.clip(np.rint(yy - uy_up * shift_px), 0, h - 1).astype(np.int32)
    src_x = np.clip(np.rint(xx - ux_up * shift_px), 0, w - 1).astype(np.int32)
    del yy, xx, ux_up, uy_up, shift_px
    shifted_src = deep_step_source[src_y, src_x]
    del src_y, src_x, deep_step_source
    updip60 = 0.65 * shifted_src + 0.35 * gaussian_filter(shifted_src, sigma=2.0)
    del shifted_src
    ch09_updip60_conduit = _robust_z_fp(updip60, fp)
    _write_ch(9, ch09_updip60_conduit)
    del updip60
    gc.collect()

    # Channel 11: Triple hydrothermal conduit (Baranov deficit * clay-cap residual * shallow TMI demag)
    clay_cap = _unpack_hgvc("hgvc_claycap_perched_resid")
    mag_demag = _unpack_hgvc("hgvc_demag_grav_conduit")
    triple_conduit = (
        _positive_norm_fp(ch02_grav_minus_psg, fp)
        * (0.50 + 0.50 * _positive_norm_fp(clay_cap, fp))
        * (0.50 + 0.50 * _positive_norm_fp(mag_demag, fp))
    )
    _write_ch(11, _robust_z_fp(triple_conduit, fp))
    del clay_cap, mag_demag, triple_conduit

    # Channel 12: Up-dip advected geothermometer & 2m probe heat focused on Baranov pseudogravity deficit
    updip_geo = _unpack_hgvc("hgvc_updip_feeder_1p5km")
    updip_2m = _unpack_hgvc("hgvc_updip_feeder_3p0km")
    geotherm_focus = (
        (0.60 * _positive_norm_fp(updip_geo, fp) + 0.40 * _positive_norm_fp(updip_2m, fp))
        * (0.45 + 0.55 * _positive_norm_fp(ch02_grav_minus_psg + 0.5 * ch09_updip60_conduit, fp))
    )
    _write_ch(12, _robust_z_fp(geotherm_focus, fp))
    del updip_geo, updip_2m, geotherm_focus

    # Channel 13: Tufa-decontaminated opaline sinter coupled with Baranov pseudogravity step
    sinter = _unpack_hgvc("hgvc_sinter_decontam")
    sinter_psg = _positive_norm_fp(sinter, fp) * (
        0.40 + 0.60 * _positive_norm_fp(ch02_grav_minus_psg + 0.5 * ch07_tilt_zero, fp)
    )
    _write_ch(13, _robust_z_fp(sinter_psg, fp))
    del sinter, sinter_psg

    # Channel 14: Kostrov geodetic tensile-dilation + shear projected onto spectral gravity-psg strike
    strike_angle = np.arctan2(grav_gx, -grav_gy + 1e-6).astype(np.float32)
    del grav_gx, grav_gy
    ext_align = 0.55 * np.abs(np.cos(strike_angle - np.deg2rad(22.0))) + 0.45 * np.abs(
        np.cos(strike_angle - np.deg2rad(-35.0))
    )
    del strike_angle
    kostrov_rate = 0.55 * _positive_norm_fp(geod_shear, fp) + 0.45 * _positive_norm_fp(geod_dilat, fp)
    del geod_shear, geod_dilat
    _write_ch(
        14,
        _robust_z_fp(
            kostrov_rate * ext_align * (0.45 + 0.55 * _positive_norm_fp(ch02_grav_minus_psg + ch07_tilt_zero, fp)),
            fp,
        ),
    )
    del ext_align

    # Channel 16: 1m 3DEP LiDAR bajada scarp polarity aligned with Baranov deficit strike (-1 sentinel)
    lidar_raw = _unpack_hgvc("hgvc_lidar_bajada_polarity")
    has_lidar = fp & (lidar_raw > -0.95)
    ch16_lidar_psg = np.full((h, w), -1.0, dtype=np.float32)
    if np.any(has_lidar):
        coupled_lidar = lidar_raw * (0.50 + 0.50 * _positive_norm_fp(ch02_grav_minus_psg + ch09_updip60_conduit, fp))
        v = coupled_lidar[has_lidar]
        med = float(np.median(v))
        scale = max(float(np.std(v, dtype=np.float64)), 1e-6)
        ch16_lidar_psg[has_lidar] = np.clip((v - med) / scale, -0.9, 6.0).astype(np.float32)
    ch16_lidar_psg[~fp] = 0.0
    _write_ch(16, ch16_lidar_psg)
    del lidar_raw, ch16_lidar_psg

    # Channel 17: 10m 3DEP chi/ksn knickzone bridged along spectral gravity-psg strike (-1 sentinel)
    chi_raw = _unpack_hgvc("hgvc_chi_strike_knick_bridge")
    has_chi = fp & (chi_raw > -0.95)
    ch17_chi_psg = np.full((h, w), -1.0, dtype=np.float32)
    if np.any(has_chi):
        coupled_chi = chi_raw * (0.50 + 0.50 * _positive_norm_fp(ch07_tilt_zero + ch10_riesz_pc, fp))
        v = coupled_chi[has_chi]
        med = float(np.median(v))
        scale = max(float(np.std(v, dtype=np.float64)), 1e-6)
        ch17_chi_psg[has_chi] = np.clip((v - med) / scale, -0.9, 6.0).astype(np.float32)
    ch17_chi_psg[~fp] = 0.0
    _write_ch(17, ch17_chi_psg)
    del chi_raw, ch17_chi_psg

    # Channel 18: 2D Frangi vesselness (sigma = 3.0 px) of composite Baranov spectral conduit field
    composite_conduit = (
        0.30 * _positive_norm_fp(ch02_grav_minus_psg, fp)
        + 0.25 * _positive_norm_fp(ch07_tilt_zero, fp)
        + 0.25 * _positive_norm_fp(ch09_updip60_conduit, fp)
        + 0.20 * _positive_norm_fp(ch10_riesz_pc, fp)
    )
    del ch02_grav_minus_psg, ch07_tilt_zero, ch09_updip60_conduit, ch10_riesz_pc
    vessel_s3 = _frangi_vesselness_2d(composite_conduit, sigma=3.0, fp=fp, fp_edt_inds=fp_edt_inds)
    _write_ch(18, _robust_z_fp(vessel_s3, fp))
    del composite_conduit, vessel_s3, fp_edt_inds
    gc.collect()

    # Channel 19: Named non-fault mimic suppressor (`psgv_mimic_rev_volc_mesa_playa`)
    rtp_neg = _positive_norm_fp(-rtp, fp)
    slope_hi = _positive_norm_fp(slope, fp)
    strain_low = np.clip(1.0 - 0.7 * kostrov_rate, 0.1, 1.0)
    rev_volc_mesa = rtp_neg * slope_hi * strain_low * np.clip(1.0 - _positive_norm_fp(zbase, fp), 0.1, 1.0)
    tufa_playa = _positive_norm_fp(_unpack_hgvc("hgvc_mimic_playa_tufa_shore"), fp)
    _write_ch(19, _robust_z_fp(0.55 * rev_volc_mesa + 0.45 * tufa_playa, fp))
    del rtp, slope, zbase, rtp_neg, slope_hi, strain_low, rev_volc_mesa, tufa_playa, kostrov_rate
    gc.collect()

    mm.flush()
    del mm
    tmp_path.replace(mm_path)

    meta = {
        "schema": "gems88.psgv_features.v1",
        "version": PSGV_SCHEMA_VERSION,
        "shape": [n_fp, n_ch],
        "feature_names": list(PSGV_FEATURE_NAMES),
        "uses_existing_faults_catalogue": False,
        "fft_padded_shape": [hp, wp],
        "fft_reflective_pad_yx": [PAD_Y, PAD_X],
        "baranov_long_wavelength_stabilizer_px": 600.0,
        "upward_continuation_depths_m": [200.0, 800.0, 2500.0, 4000.0],
        "named_non_fault_mimic_channel": "psgv_mimic_rev_volc_mesa_playa",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    mm_ro = np.memmap(mm_path, dtype=np.float32, mode="r", shape=(n_fp, n_ch))
    return mm_ro, meta


def poe_pool_psgv(
    p_base: np.ndarray,
    m_base: np.ndarray,
    p_hgvc: np.ndarray,
    m_hgvc: np.ndarray,
    p_psgv: np.ndarray,
    m_psgv: np.ndarray,
    d_vis_act: np.ndarray,
    alpha_psgv: float | np.ndarray = 0.65,
    w_near: float = 0.65,
    w_far_boost: float = 0.18,
) -> tuple[np.ndarray, np.ndarray]:
    """3-Specialist (Base + HGVC Hydrothermal + PSGV Baranov Spectral) Distance-Gated Log-Odds PoE."""
    a_p = np.asarray(alpha_psgv, dtype=np.float32)
    a_h = np.float32(1.0) - a_p
    p_spec = a_h * p_hgvc + a_p * p_psgv
    m_spec = np.maximum(a_h * m_hgvc + a_p * m_psgv, p_spec)
    return hgvc.poe_pool_hgvc(p_base, m_base, p_spec, m_spec, d_vis_act, w_near=w_near, w_far_boost=w_far_boost)


def compute_baranov_Concordance_bonus(X_psgv_mm: np.ndarray, act_idx: np.ndarray) -> np.ndarray:
    """Zero-centered analytical wavenumber Baranov pseudogravity-deficit & tilt-zero bonus on act_idx."""
    idx = {name: i for i, name in enumerate(PSGV_FEATURE_NAMES)}
    c_def = np.asarray(X_psgv_mm[act_idx, idx["psgv_grav_minus_psg_deficit"]], dtype=np.float32)
    c_tilt = np.asarray(X_psgv_mm[act_idx, idx["psgv_tilt_zero_distance_decay"]], dtype=np.float32)
    c_up60 = np.asarray(X_psgv_mm[act_idx, idx["psgv_updip60_spectral_conduit"]], dtype=np.float32)
    c_riesz = np.asarray(X_psgv_mm[act_idx, idx["psgv_riesz_congruency_crest"]], dtype=np.float32)
    c_demag = np.asarray(X_psgv_mm[act_idx, idx["psgv_demag_clay_psg_conduit"]], dtype=np.float32)
    c_mimic = np.asarray(X_psgv_mm[act_idx, idx["psgv_mimic_rev_volc_mesa_playa"]], dtype=np.float32)
    raw = (
        0.26 * np.clip(c_def, -2.0, 4.0)
        + 0.22 * np.clip(c_tilt, -2.0, 4.0)
        + 0.20 * np.clip(c_up60, -2.0, 4.0)
        + 0.16 * np.clip(c_riesz, -2.0, 4.0)
        + 0.16 * np.clip(c_demag, -2.0, 4.0)
        - 0.24 * np.clip(c_mimic, 0.0, 4.0)
    )
    med = float(np.median(raw))
    return np.clip((raw - med) / max(float(np.std(raw, dtype=np.float64)), 1e-5), -1.5, 2.5).astype(np.float32)


def verify_zero_test_quadrant_leakage(
    grid: grid_mod.Grid,
    X_phys_diff: hgvc.ColumnSubsetView,
    X_psgv_mm: np.ndarray,
    X_hgvc_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int = 88901,
) -> bool:
    """Prove bit-for-bit prediction invariance when held-out test_region truth is scrambled."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
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
        clfs, regs = adhr._fit_dual_expectation_models(
            [X_phys_diff, X_psgv_mm, X_hgvc_mm, X_vis22_mm, dow],
            (train_regions & ~visible)[ys_fp, xs_fp],
            t_cand,
            fp,
            seed=seed,
            max_zero_neg=15_000,
            n_ensemble=1,
        )
        preds.append(
            adhr._predict_dual_chunked(
                clfs, regs, [X_phys_diff, X_psgv_mm, X_hgvc_mm, X_vis22_mm, dow], sub_idx
            )
        )
    return bool(np.array_equal(preds[0][0], preds[1][0]) and np.array_equal(preds[0][1], preds[1][1]))


def _fit_models_from_gathered(
    X_tr: np.ndarray,
    yc_tr: np.ndarray,
    yk_tr: np.ndarray,
    weights: np.ndarray,
    col_indices: np.ndarray,
    seed: int,
    n_ensemble: int = 1,
    max_rows: int | None = None,
) -> tuple[list[Any], list[Any]]:
    """Fit calibrated HistGradientBoostingClassifier + Regressor on selected columns of X_tr."""
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    if max_rows is not None and len(X_tr) > max_rows:
        rng = np.random.default_rng(seed + 991)
        pos_m = yc_tr > 0
        pos_i = np.flatnonzero(pos_m)
        neg_i = np.flatnonzero(~pos_m)
        keep_neg = max(max_rows - int(pos_i.size), 50_000)
        if neg_i.size > keep_neg:
            chosen_neg = rng.choice(neg_i, size=keep_neg, replace=False)
            scale_w = float(np.sum(weights[neg_i])) / max(float(np.sum(weights[chosen_neg])), 1e-6)
            sel = np.concatenate([pos_i, chosen_neg])
            w_use = weights[sel].copy()
            w_use[pos_i.size :] *= scale_w
            perm = rng.permutation(sel.size)
            sel = sel[perm]
            w_use = w_use[perm]
            X_sub = np.ascontiguousarray(X_tr[sel][:, col_indices], dtype=np.float32)
            yc_use = yc_tr[sel]
            yk_use = yk_tr[sel]
        else:
            X_sub = np.ascontiguousarray(X_tr[:, col_indices], dtype=np.float32)
            yc_use = yc_tr
            yk_use = yk_tr
            w_use = weights
    else:
        X_sub = np.ascontiguousarray(X_tr[:, col_indices], dtype=np.float32)
        yc_use = yc_tr
        yk_use = yk_tr
        w_use = weights

    clfs = []
    regs = []
    for k in range(n_ensemble):
        clf = HistGradientBoostingClassifier(
            max_iter=115,
            learning_rate=0.075,
            max_leaf_nodes=47,
            min_samples_leaf=80,
            l2_regularization=4.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=12,
            random_state=seed + 101 * k,
        )
        clf.fit(X_sub, yc_use, sample_weight=w_use)
        clfs.append(clf)

        reg = HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=115,
            learning_rate=0.075,
            max_leaf_nodes=47,
            min_samples_leaf=80,
            l2_regularization=4.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=12,
            random_state=seed + 211 * k,
        )
        reg.fit(X_sub, yk_use, sample_weight=w_use)
        regs.append(reg)
    del X_sub
    return clfs, regs


def _gather_columns_fast(sources: list[np.ndarray], sub_idx: np.ndarray) -> np.ndarray:
    """Fast contiguous-slice gather across memmaps and arrays when sub_idx is sorted."""
    if sub_idx.size == 0:
        total_w = sum(1 if s.ndim == 1 else s.shape[1] for s in sources)
        return np.empty((0, total_w), dtype=np.float32)
    r0 = int(sub_idx[0])
    r1 = int(sub_idx[-1]) + 1
    rel = sub_idx - r0
    total_w = sum(1 if s.ndim == 1 else s.shape[1] for s in sources)
    out = np.empty((sub_idx.size, total_w), dtype=np.float32)
    c = 0
    for s in sources:
        if s.ndim == 1:
            out[:, c] = s[r0:r1][rel]
            c += 1
        else:
            w = s.shape[1]
            out[:, c : c + w] = s[r0:r1][rel]
            c += w
    return out


def _sample_and_gather_training(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    seed: int,
    max_zero_neg: int = 140_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Sample training rows once and gather all columns sequentially from disk."""
    ys_fp, xs_fp = np.nonzero(fp_mask)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int8)
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
    X_tr = _gather_columns_fast(sources, train_idx)
    yc_tr = y_cell_all[train_idx]
    yk_tr = y_kern_all[train_idx]

    perm = rng.permutation(len(train_idx))
    return X_tr[perm], yc_tr[perm], yk_tr[perm], weights[perm]


def _predict_multi_specs_chunked(
    specs: dict[str, tuple[list[Any], list[Any], np.ndarray]],
    sources: list[np.ndarray],
    act_idx: np.ndarray,
    chunk: int = 250_000,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Predict multiple specialist (clfs, regs, col_indices) in a single chunked pass over sources."""
    n = act_idx.size
    out: dict[str, tuple[np.ndarray, np.ndarray]] = {
        k: (np.empty(n, dtype=np.float32), np.empty(n, dtype=np.float32)) for k in specs
    }
    for start in range(0, n, chunk):
        sl = slice(start, min(start + chunk, n))
        X_all = _gather_columns_fast(sources, act_idx[sl])
        for k, (clfs, regs, cols) in specs.items():
            X_sub = np.ascontiguousarray(X_all[:, cols], dtype=np.float32)
            p_acc = np.zeros(len(X_sub), dtype=np.float64)
            m_acc = np.zeros(len(X_sub), dtype=np.float64)
            for clf, reg in zip(clfs, regs):
                p_acc += clf.predict_proba(X_sub)[:, 1]
                m_acc += np.clip(reg.predict(X_sub), 0.0, 1.0)
            p_c = (p_acc / len(clfs)).astype(np.float32)
            m_c = np.clip(m_acc / len(regs), p_c, 1.0).astype(np.float32)
            out[k][0][sl] = p_c
            out[k][1][sl] = m_c
        del X_all
    return out


def predict_psgv_all_arms_fold(
    grid: grid_mod.Grid,
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
    cache_only: bool = False,
) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    """Fit/load per-fold posteriors for Base, Spectral PSGV-20, and Unified PSGV+HGVC specialists."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    d_vis_act = d_vis_fp[act_idx]

    psgv_post_path = Path(cache_dir) / f"psgv_fold_post_{fold_tag}_{PSGV_SCHEMA_VERSION}.npz"
    if psgv_post_path.is_file():
        zp = np.load(psgv_post_path, allow_pickle=False)
        p_phys_44, m_phys_44 = zp["p_phys_44"], zp["m_phys_44"]
        p_full_67, m_full_67 = zp["p_full_67"], zp["m_full_67"]
        p_hp, m_hp = zp["p_hp"], zp["m_hp"]
        p_pp, m_pp = zp["p_pp"], zp["m_pp"]
        p_hf, m_hf = zp["p_hf"], zp["m_hf"]
        p_pf, m_pf = zp["p_pf"], zp["m_pf"]
    else:
        pop_tr_fp = train_truth[ys_fp, xs_fp]
        wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
        d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

        dom_phys_tr = train_regions[ys_fp, xs_fp]
        dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]

        # Column layouts in unified [X_phys(44), X_psgv(20), X_hgvc(20), X_vis22(22), dow(1)] (107 cols):
        cols_phys44 = np.arange(0, 44, dtype=np.int32)
        cols_diff36 = np.asarray(hgvc.PHYS_DIFF_INDICES, dtype=np.int32)
        cols_psgv20 = np.arange(44, 64, dtype=np.int32)
        cols_hgvc20 = np.arange(64, 84, dtype=np.int32)
        cols_vis23 = np.arange(84, 107, dtype=np.int32)

        cols_hgvc_phys = np.concatenate([cols_diff36, cols_hgvc20])                     # 56 ch
        cols_psgv_phys = np.concatenate([cols_diff36, cols_psgv20, cols_hgvc20])        # 76 ch
        cols_full67 = np.concatenate([cols_phys44, cols_vis23])                         # 67 ch
        cols_hgvc_full = np.concatenate([cols_phys44, cols_hgvc20, cols_vis23])         # 87 ch
        cols_psgv_full = np.concatenate([cols_phys44, cols_psgv20, cols_hgvc20, cols_vis23])  # 107 ch

        blocks_phys = [X_phys_mm, X_psgv_mm, X_hgvc_mm]
        blocks_full = [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp]

        # 1. Fit zero-catalogue physical models (Base 44 + PSGV 76 + HGVC 56)
        X_tr_p, yc_p, yk_p, w_p = _sample_and_gather_training(
            blocks_phys, dom_phys_tr, visible & train_regions, fp, seed=seed + 17
        )
        c_p44, r_p44 = _fit_models_from_gathered(X_tr_p, yc_p, yk_p, w_p, cols_phys44, seed=seed + 17, n_ensemble=1)
        c_pp, r_pp = _fit_models_from_gathered(X_tr_p, yc_p, yk_p, w_p, cols_psgv_phys, seed=seed + 217, n_ensemble=1)
        del X_tr_p, yc_p, yk_p, w_p

        X_tr_hp, yc_hp, yk_hp, w_hp = _sample_and_gather_training(
            blocks_phys, dom_phys_tr, visible & train_regions, fp, seed=seed + 117
        )
        c_hp, r_hp = _fit_models_from_gathered(X_tr_hp, yc_hp, yk_hp, w_hp, cols_hgvc_phys, seed=seed + 117, n_ensemble=1)
        del X_tr_hp, yc_hp, yk_hp, w_hp
        gc.collect()

        # 2. Fit structural models (Base 67 + PSGV 107 + HGVC 87)
        X_tr_f, yc_f, yk_f, w_f = _sample_and_gather_training(
            blocks_full, dom_struct_tr, train_truth, fp, seed=seed + 53
        )
        c_f67, r_f67 = _fit_models_from_gathered(X_tr_f, yc_f, yk_f, w_f, cols_full67, seed=seed + 53, n_ensemble=1)
        c_pf, r_pf = _fit_models_from_gathered(X_tr_f, yc_f, yk_f, w_f, cols_psgv_full, seed=seed + 253, n_ensemble=1)
        del X_tr_f, yc_f, yk_f, w_f

        X_tr_hf, yc_hf, yk_hf, w_hf = _sample_and_gather_training(
            blocks_full, dom_struct_tr, train_truth, fp, seed=seed + 153
        )
        c_hf, r_hf = _fit_models_from_gathered(X_tr_hf, yc_hf, yk_hf, w_hf, cols_hgvc_full, seed=seed + 153, n_ensemble=1)
        del X_tr_hf, yc_hf, yk_hf, w_hf
        gc.collect()

        # 3. Predict all 6 dual heads in one single chunked pass over act_idx
        preds = _predict_multi_specs_chunked(
            {
                "phys44": (c_p44, r_p44, cols_phys44),
                "hp": (c_hp, r_hp, cols_hgvc_phys),
                "pp": (c_pp, r_pp, cols_psgv_phys),
                "full67": (c_f67, r_f67, cols_full67),
                "hf": (c_hf, r_hf, cols_hgvc_full),
                "pf": (c_pf, r_pf, cols_psgv_full),
            },
            blocks_full,
            act_idx,
        )
        del c_p44, r_p44, c_hp, r_hp, c_pp, r_pp, c_f67, r_f67, c_hf, r_hf, c_pf, r_pf, d_over_w_fp
        gc.collect()

        p_phys_44, m_phys_44 = preds["phys44"]
        p_hp, m_hp = preds["hp"]
        p_pp, m_pp = preds["pp"]
        p_full_67, m_full_67 = preds["full67"]
        p_hf, m_hf = preds["hf"]
        p_pf, m_pf = preds["pf"]

        np.savez_compressed(
            psgv_post_path,
            p_phys_44=p_phys_44,
            m_phys_44=m_phys_44,
            p_full_67=p_full_67,
            m_full_67=m_full_67,
            p_hp=p_hp,
            m_hp=m_hp,
            p_pp=p_pp,
            m_pp=m_pp,
            p_hf=p_hf,
            m_hf=m_hf,
            p_pf=p_pf,
            m_pf=m_pf,
        )

    if cache_only:
        return {}

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

    # Exp 01: exp01_psgv_zero_cat (Zero-catalogue Baranov Spectral + Hydrothermal Specialist Ensemble)
    p_spec_p = np.float32(0.35) * p_hp + np.float32(0.65) * p_pp
    m_spec_p = np.maximum(np.float32(0.35) * m_hp + np.float32(0.65) * m_pp, p_spec_p)
    sc_e1 = float(k_est) / max(float(p_spec_p.sum()), 1e-6)
    p_e1 = np.clip(p_spec_p * np.float32(sc_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_spec_p * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)

    # Exp 02: exp02_psgv_spectral_joint (107-ch Spectral Baranov + Hydrothermal + Structural single-branch)
    p_e2, m_e2 = adhr._fuse_log_odds(p_pf, m_pf, p_pp, m_pp, k_est, beta_phys=0.38)

    # Exp 03: exp03_psgv_tri_specialist_poe (3-Specialist Distance-Gated Log-Odds PoE)
    blind_gate = (1.0 / (1.0 + np.exp(-np.clip((d_vis_act - 23.5) / 2.0, -15.0, 15.0)))).astype(np.float32)
    a_phys = np.float32(0.65) - np.float32(0.30) * blind_gate
    a_full = np.float32(0.65) - np.float32(0.50) * blind_gate
    p_tri_phys, m_tri_phys = poe_pool_psgv(
        p_phys_44, m_phys_44, p_hp, m_hp, p_pp, m_pp, d_vis_act, alpha_psgv=a_phys, w_near=0.65, w_far_boost=0.18
    )
    p_tri_full, m_tri_full = poe_pool_psgv(
        p_full_67, m_full_67, p_hf, m_hf, p_pf, m_pf, d_vis_act, alpha_psgv=a_full, w_near=0.65, w_far_boost=0.18
    )
    p_e3, m_e3 = adhr._fuse_log_odds(p_tri_full, m_tri_full, p_tri_phys, m_tri_phys, k_est, beta_phys=0.38)

    return {
        "phys44_zero_cat": _emit_arm(p_c1, m_c1),
        "h88_adhr_incumbent": _emit_arm(p_inc, m_inc),
        "exp01_psgv_zero_cat": _emit_arm(p_e1, m_e1),
        "exp02_psgv_spectral_joint": _emit_arm(p_e2, m_e2),
        "exp03_psgv_tri_specialist_poe": _emit_arm(p_e3, m_e3),
    }


def fit_and_emit_production_psgv(
    grid: grid_mod.Grid,
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
    near_budget: int = 19_200,
    far_budget: int = 18_454,
    near_spacing_px: float = 3.05,
    far_spacing_px: float = 3.15,
    preplacement_gate=None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Strictly out-of-fold 8-quadrant + disjoint boundary cross-fitting & 3-specialist Baranov PoE allocation."""
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

    psgv_oof_cache = Path(cache_dir) / f"psgv_prod_oof_{PSGV_SCHEMA_VERSION}.npz"
    if psgv_oof_cache.is_file():
        zp = np.load(psgv_oof_cache, allow_pickle=False)
        p_phys_pool = zp["p_phys_pool"]
        m_phys_pool = zp["m_phys_pool"]
        p_full_pool = zp["p_full_pool"]
        m_full_pool = zp["m_full_pool"]
    else:
        n_fp = int(fp.sum())
        p_phys_acc = np.zeros(n_fp, dtype=np.float64)
        m_phys_acc = np.zeros(n_fp, dtype=np.float64)
        p_full_acc = np.zeros(n_fp, dtype=np.float64)
        m_full_acc = np.zeros(n_fp, dtype=np.float64)
        cov_cnt = np.zeros(n_fp, dtype=np.int32)

        for seed, folds in folds_by_seed:
            _, dv_s, _ = vis_by_seed[seed]
            for i, fold in enumerate(folds):
                fold_tag = f"seed{seed}_f{i}_{fold['name']}"
                post_path = Path(cache_dir) / f"psgv_fold_post_{fold_tag}_{PSGV_SCHEMA_VERSION}.npz"
                if not post_path.is_file():
                    raise FileNotFoundError(f"Expected cached fold posterior {post_path}")
                zf = np.load(post_path, allow_pickle=False)
                allowed_f = fp & fold["region"] & ~fold["visible"]
                f_idx = np.flatnonzero(allowed_f[ys_fp, xs_fp])
                dv_f = dv_s[f_idx]
                bg_f = (1.0 / (1.0 + np.exp(-np.clip((dv_f - 23.5) / 2.0, -15.0, 15.0)))).astype(np.float32)
                ap_f = np.float32(0.65) - np.float32(0.30) * bg_f
                af_f = np.float32(0.65) - np.float32(0.50) * bg_f
                p_pf_f, m_pf_f = poe_pool_psgv(
                    zf["p_phys_44"], zf["m_phys_44"], zf["p_hp"], zf["m_hp"], zf["p_pp"], zf["m_pp"], dv_f, alpha_psgv=ap_f
                )
                p_ff_f, m_ff_f = poe_pool_psgv(
                    zf["p_full_67"], zf["m_full_67"], zf["p_hf"], zf["m_hf"], zf["p_pf"], zf["m_pf"], dv_f, alpha_psgv=af_f
                )
                p_phys_acc[f_idx] += p_pf_f
                m_phys_acc[f_idx] += m_pf_f
                p_full_acc[f_idx] += p_ff_f
                m_full_acc[f_idx] += m_ff_f
                cov_cnt[f_idx] += 1

        # Fill the 5.3% inter-quadrant boundary-collar cells (cov_cnt == 0 on act_idx)
        # using models trained strictly on the disjoint quadrant interior (int_reg).
        b_mask_act = cov_cnt[act_idx] == 0
        if np.any(b_mask_act):
            b_idx = act_idx[b_mask_act]
            folds_20 = folds_by_seed[0][1]
            vis_20 = folds_20[0]["visible"]
            int_reg = np.logical_or.reduce([f["region"] for f in folds_20])
            int_tru = np.logical_or.reduce([f["truth"] for f in folds_20])
            int_dom_phys = int_reg[ys_fp, xs_fp]
            int_dom_struct = (int_reg & ~vis_20)[ys_fp, xs_fp]

            X_vis_prod, dv_prod, cl_prod = vis_by_seed[20]
            wlaw_b = damagezone_envelope.fit_width_law(
                cl_prod, dv_prod, int_tru[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
            )
            dow_b = (dv_prod / np.maximum(wlaw_b.half_width(cl_prod), 1e-6)).astype(np.float32)

            cols_phys44 = np.arange(0, 44, dtype=np.int32)
            cols_diff36 = np.asarray(hgvc.PHYS_DIFF_INDICES, dtype=np.int32)
            cols_psgv20 = np.arange(44, 64, dtype=np.int32)
            cols_hgvc20 = np.arange(64, 84, dtype=np.int32)
            cols_vis23 = np.arange(84, 107, dtype=np.int32)
            cols_hgvc_phys = np.concatenate([cols_diff36, cols_hgvc20])
            cols_psgv_phys = np.concatenate([cols_diff36, cols_psgv20, cols_hgvc20])
            cols_full67 = np.concatenate([cols_phys44, cols_vis23])
            cols_hgvc_full = np.concatenate([cols_phys44, cols_hgvc20, cols_vis23])
            cols_psgv_full = np.concatenate([cols_phys44, cols_psgv20, cols_hgvc20, cols_vis23])

            blocks_all_b = [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis_prod, dow_b]
            X_bp, ycbp, ykbp, wbp = _sample_and_gather_training(
                [X_phys_mm, X_psgv_mm, X_hgvc_mm], int_dom_phys, vis_20 & int_reg, fp, seed=89801
            )
            c_bp44, r_bp44 = _fit_models_from_gathered(X_bp, ycbp, ykbp, wbp, cols_phys44, seed=89801, n_ensemble=1)
            c_bpp, r_bpp = _fit_models_from_gathered(X_bp, ycbp, ykbp, wbp, cols_psgv_phys, seed=89802, n_ensemble=1)
            c_bhp, r_bhp = _fit_models_from_gathered(X_bp, ycbp, ykbp, wbp, cols_hgvc_phys, seed=89803, n_ensemble=1)
            del X_bp, ycbp, ykbp, wbp

            X_bf, ycbf, ykbf, wbf = _sample_and_gather_training(
                blocks_all_b, int_dom_struct, int_tru, fp, seed=89811
            )
            c_bf67, r_bf67 = _fit_models_from_gathered(X_bf, ycbf, ykbf, wbf, cols_full67, seed=89811, n_ensemble=1)
            c_bpf, r_bpf = _fit_models_from_gathered(X_bf, ycbf, ykbf, wbf, cols_psgv_full, seed=89812, n_ensemble=1)
            c_bhf, r_bhf = _fit_models_from_gathered(X_bf, ycbf, ykbf, wbf, cols_hgvc_full, seed=89813, n_ensemble=1)
            del X_bf, ycbf, ykbf, wbf

            b_preds = _predict_multi_specs_chunked(
                {
                    "p44": (c_bp44, r_bp44, cols_phys44),
                    "hp": (c_bhp, r_bhp, cols_hgvc_phys),
                    "pp": (c_bpp, r_bpp, cols_psgv_phys),
                    "f67": (c_bf67, r_bf67, cols_full67),
                    "hf": (c_bhf, r_bhf, cols_hgvc_full),
                    "pf": (c_bpf, r_bpf, cols_psgv_full),
                },
                blocks_all_b,
                b_idx,
            )
            dv_b = dv_prod[b_idx]
            bg_b = (1.0 / (1.0 + np.exp(-np.clip((dv_b - 23.5) / 2.0, -15.0, 15.0)))).astype(np.float32)
            ap_b = np.float32(0.65) - np.float32(0.30) * bg_b
            af_b = np.float32(0.65) - np.float32(0.50) * bg_b
            pb_phys, mb_phys = poe_pool_psgv(
                b_preds["p44"][0], b_preds["p44"][1],
                b_preds["hp"][0], b_preds["hp"][1],
                b_preds["pp"][0], b_preds["pp"][1],
                dv_b, alpha_psgv=ap_b,
            )
            pb_full, mb_full = poe_pool_psgv(
                b_preds["f67"][0], b_preds["f67"][1],
                b_preds["hf"][0], b_preds["hf"][1],
                b_preds["pf"][0], b_preds["pf"][1],
                dv_b, alpha_psgv=af_b,
            )
            p_phys_acc[b_idx] = pb_phys
            m_phys_acc[b_idx] = mb_phys
            p_full_acc[b_idx] = pb_full
            m_full_acc[b_idx] = mb_full
            cov_cnt[b_idx] = 1
            del b_preds, dow_b
            gc.collect()

        denom = np.maximum(cov_cnt[act_idx], 1).astype(np.float64)
        p_phys_pool = (p_phys_acc[act_idx] / denom).astype(np.float32)
        m_phys_pool = np.maximum((m_phys_acc[act_idx] / denom).astype(np.float32), p_phys_pool)
        p_full_pool = (p_full_acc[act_idx] / denom).astype(np.float32)
        m_full_pool = np.maximum((m_full_acc[act_idx] / denom).astype(np.float32), p_full_pool)
        np.savez_compressed(
            psgv_oof_cache,
            p_phys_pool=p_phys_pool,
            m_phys_pool=m_phys_pool,
            p_full_pool=p_full_pool,
            m_full_pool=m_full_pool,
        )

    # Extract spectral Baranov crest modulation on active off-catalogue cells
    psgv_idx = {name: i for i, name in enumerate(PSGV_FEATURE_NAMES)}

    def _act_pos(name: str) -> np.ndarray:
        col = np.asarray(X_psgv_mm[:, psgv_idx[name]], dtype=np.float32)[act_idx]
        p50 = float(np.percentile(col, 50.0))
        p98 = max(float(np.percentile(col, 98.0)), p50 + 1e-5)
        return np.clip((col - p50) / (p98 - p50), 0.0, 1.5).astype(np.float32)

    spec_crest = np.clip(
        0.28 * _act_pos("psgv_grav_minus_psg_deficit")
        + 0.22 * _act_pos("psgv_monogenic_phase_disloc")
        + 0.20 * _act_pos("psgv_tilt_zero_distance_decay")
        + 0.16 * _act_pos("psgv_updip60_spectral_conduit")
        + 0.14 * _act_pos("psgv_riesz_congruency_crest")
        + 0.12 * _act_pos("psgv_parker_admittance_resid")
        - 0.24 * _act_pos("psgv_mimic_rev_volc_mesa_playa"),
        0.02,
        1.60,
    ).astype(np.float32)

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(
        p_full_pool, m_full_pool, p_phys_pool, m_phys_pool, k_prod, beta_phys=0.58, pi_unmapped=0.62
    )
    # Anchor posterior onto Baranov pseudogravity dislocation & tilt-zero crests
    crest_mult = (0.22 + 1.15 * (spec_crest ** 1.35)).astype(np.float32)
    p_fused = np.clip(p_fused * crest_mult, 0.0, 1.0).astype(np.float32)
    m_fused = np.clip(m_fused * (0.45 + 0.65 * spec_crest), p_fused, 1.0).astype(np.float32)
    p_phys_mod = np.clip(p_phys_pool * (0.18 + 1.25 * (spec_crest ** 1.35)), 0.0, 1.0).astype(np.float32)
    m_phys_mod = np.clip(m_phys_pool * (0.42 + 0.68 * spec_crest), p_phys_mod, 1.0).astype(np.float32)

    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0
    k_near = k_prod * (float(near_budget) / float(near_budget + far_budget))
    k_far = k_prod * (float(far_budget) / float(near_budget + far_budget))

    p_near_raw = 0.44 * p_fused[near_sel] + 0.56 * p_phys_mod[near_sel]
    m_near_raw = 0.44 * m_fused[near_sel] + 0.56 * m_phys_mod[near_sel]
    sc_near = float(k_near) / max(float(p_near_raw.sum()), 1e-6)
    p_near = np.clip(p_near_raw * np.float32(sc_near), 0.0, 1.0).astype(np.float32)
    m_near = np.clip(m_near_raw * np.float32(min(max(sc_near, 0.85), 1.20)), p_near, 1.0).astype(np.float32)

    p_far_raw = 0.10 * p_fused[far_sel] + 0.90 * p_phys_mod[far_sel]
    m_far_raw = 0.10 * m_fused[far_sel] + 0.90 * m_phys_mod[far_sel]
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
        p_surface,
        m_surface,
        allowed_near,
        budget=near_budget,
        k_truth=k_near,
        min_spacing_px=near_spacing_px,
        dinkelbach_iters=8,
    )
    alloc_far = emit.dinkelbach_allocate(
        p_surface,
        m_surface,
        allowed_far,
        budget=far_budget,
        k_truth=k_far,
        min_spacing_px=far_spacing_px,
        dinkelbach_iters=8,
    )
    emitted = np.clip(
        alloc_near.emitted.astype(np.float32) + alloc_far.emitted.astype(np.float32), 0.0, 1.0
    ).astype(np.float32)
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
        "strictly_out_of_fold_all_three_specialists": True,
    }
    return emitted, p_surface, meta
