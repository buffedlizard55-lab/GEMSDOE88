"""H88-GZZC: residual isostatic-gravity zero-contour buried density contact.

Zero-catalogue. Sentinel-valued GeoDAWN/competition bands are cleaned inside
the scored footprint. No catalogue-derived features.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

BANDS = {
    "iso_grav_anom": 13,
    "iso_grav_anom_vg": 11,
    "iso_grav_anom_hg": 18,
    "iso_grav_anom_slope": 5,
    "det_elev_slope": 19,
    "geod_shearrate": 7,
    "geod_dilaterate": 8,
    "depth_to_base_surf": 15,
}

FEATURE_NAMES = (
    "grav_residual",
    "grav_zero_ridge",
    "low_slope_gate",
    "strain_gate",
    "gzzc_surface",
)

SENTINEL = -1.0e20
REGIONAL_SIGMA_PX = 40.0  # 4 km at 100 m pixels
RIDGE_SMOOTH_PX = 1.5


def clean_band(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, np.float32)
    bad = (~np.isfinite(a)) | (a < SENTINEL)
    out = a.copy()
    good = footprint & ~bad
    fill = float(np.median(out[good])) if good.any() else 0.0
    out[bad] = fill
    out[~footprint] = 0.0
    return out


def neumann_smooth(arr: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    w = gaussian_filter(valid.astype(np.float32), sigma=sigma, mode="nearest")
    clean = np.where(valid, arr, 0.0).astype(np.float32)
    num = gaussian_filter(clean, sigma=sigma, mode="nearest")
    out = np.where(w > 1e-5, num / np.maximum(w, 1e-5), 0.0).astype(np.float32)
    out[~valid] = 0.0
    return out


def percentile01(arr: np.ndarray, footprint: np.ndarray, lo: float = 2.0, hi: float = 98.0) -> np.ndarray:
    v = arr[footprint]
    p_lo, p_hi = np.percentile(v, [lo, hi])
    if p_hi <= p_lo:
        out = np.zeros_like(arr, dtype=np.float32)
        return out
    out = np.clip((arr - p_lo) / (p_hi - p_lo), 0.0, 1.0).astype(np.float32)
    out[~footprint] = 0.0
    return out


def residual_gravity(grav: np.ndarray, footprint: np.ndarray, sigma: float = REGIONAL_SIGMA_PX) -> np.ndarray:
    regional = neumann_smooth(grav, footprint, sigma)
    residual = (grav - regional).astype(np.float32)
    residual[~footprint] = 0.0
    return residual


def zero_contour_ridge(residual: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """High |∇r| on the r≈0 contour (buried density contact)."""
    sm = neumann_smooth(residual, footprint, RIDGE_SMOOTH_PX)
    gy, gx = np.gradient(sm)
    grad = np.hypot(gx, gy).astype(np.float32)
    sigma_z = float(np.std(sm[footprint]))
    if not np.isfinite(sigma_z) or sigma_z < 1e-6:
        sigma_z = 1.0
    ridge = grad * np.exp(-0.5 * (sm / (0.35 * sigma_z)) ** 2)
    ridge = ridge.astype(np.float32)
    ridge[~footprint] = 0.0
    return ridge


def build_features(bands: dict[str, np.ndarray], footprint: np.ndarray) -> dict[str, np.ndarray]:
    grav = clean_band(bands["iso_grav_anom"], footprint)
    slope = clean_band(bands["det_elev_slope"], footprint)
    shear = clean_band(bands["geod_shearrate"], footprint)
    dilate = clean_band(bands["geod_dilaterate"], footprint)

    residual = residual_gravity(grav, footprint)
    ridge = zero_contour_ridge(residual, footprint)
    ridge_n = percentile01(ridge, footprint, 5, 99.5)
    slope_n = percentile01(slope, footprint, 2, 98)
    low_slope = ((1.0 - slope_n) ** 2).astype(np.float32)
    low_slope[~footprint] = 0.0

    shear_n = percentile01(shear, footprint, 2, 98)
    dil_pos = np.clip(dilate, 0.0, None)
    dil_n = percentile01(dil_pos, footprint, 2, 98)
    strain = (0.5 * shear_n + 0.5 * dil_n).astype(np.float32)
    strain[~footprint] = 0.0

    exp1 = ridge_n
    exp2 = (ridge_n * (0.25 + 0.75 * low_slope)).astype(np.float32)
    exp3 = (exp2 * (0.35 + 0.65 * strain)).astype(np.float32)
    for arr in (exp1, exp2, exp3):
        arr[~footprint] = 0.0

    return {
        "grav_residual": residual,
        "grav_zero_ridge": ridge_n,
        "low_slope_gate": low_slope,
        "strain_gate": strain,
        "gzzc_exp1_ridge": exp1,
        "gzzc_exp2_buried": exp2,
        "gzzc_surface": exp3,
    }
