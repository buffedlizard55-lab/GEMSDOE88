"""H88-SSA: scale-selective multi-physics structure-tensor azimuth coherence.

Zero-catalogue. Uses competition GeoDAWN bands only. The circular resultant
length of 2-theta orientations across magnetic, gravity, basement-depth, and
surface-elevation structure tensors is high where a crustal-scale feeder
aligns strike through cover — a signature USGS/INGENIOUS air-photo catalogues
miss under alluvium.

Mimic: unfaulted tilted-block dip slopes / batholith contacts. Mitigated by
requiring a basement-depth gradient and penalizing high surface-slope
coherence without a basement step.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, sobel

BANDS = {
    "rtp": 2,
    "tmi_hg": 3,
    "iso_grav_anom_hg": 18,
    "depth_to_base_surf": 15,
    "det_elev": 12,
    "det_elev_slope": 19,
    "cond_surf": 17,
}

FEATURE_NAMES = (
    "ssa_kappa",
    "ssa_basement_step",
    "ssa_low_slope",
    "ssa_cal_residual",
    "ssa_surface",
)

SENTINEL = -1.0e20
TENSOR_SIGMA = 3.0  # 300 m at 100 m pixels


def clean_band(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, np.float32)
    bad = (~np.isfinite(a)) | (a < SENTINEL)
    out = a.copy()
    good = footprint & ~bad
    fill = float(np.median(out[good])) if good.any() else 0.0
    out[bad] = fill
    out[~footprint] = 0.0
    return out


def percentile01(arr: np.ndarray, footprint: np.ndarray, lo: float = 5.0, hi: float = 95.0) -> np.ndarray:
    v = arr[footprint]
    p_lo, p_hi = np.percentile(v, [lo, hi])
    if p_hi <= p_lo:
        return np.zeros_like(arr, dtype=np.float32)
    out = np.clip((arr - p_lo) / (p_hi - p_lo), 0.0, 1.0).astype(np.float32)
    out[~footprint] = 0.0
    return out


def structure_theta(field: np.ndarray, footprint: np.ndarray, sigma: float = TENSOR_SIGMA) -> tuple[np.ndarray, np.ndarray]:
    """Return (theta, energy) of the 2-D structure tensor at scale sigma.

    Theta is the axial orientation of the gradient (mod pi). Energy is |G|^2.
    """
    sm = gaussian_filter(np.where(footprint, field, 0.0).astype(np.float32), sigma=sigma)
    gy = sobel(sm, axis=0) * 0.125
    gx = sobel(sm, axis=1) * 0.125
    energy = (gx * gx + gy * gy).astype(np.float32)
    theta = np.arctan2(gy, gx).astype(np.float32)  # gradient direction; strike is theta + pi/2, axial 2θ identical
    energy[~footprint] = 0.0
    return theta, energy


def circular_resultant(thetas: list[np.ndarray], energies: list[np.ndarray], footprint: np.ndarray) -> np.ndarray:
    """Weighted circular mean resultant length of axial (2θ) orientations."""
    cx = np.zeros(thetas[0].shape, np.float64)
    cy = np.zeros_like(cx)
    wsum = np.zeros_like(cx)
    for th, en in zip(thetas, energies):
        w = np.sqrt(np.maximum(en, 0.0))
        cx += w * np.cos(2.0 * th)
        cy += w * np.sin(2.0 * th)
        wsum += w
    kappa = np.where(wsum > 1e-8, np.hypot(cx, cy) / np.maximum(wsum, 1e-8), 0.0)
    kappa = kappa.astype(np.float32)
    kappa[~footprint] = 0.0
    return kappa


def cal_residual(cond: np.ndarray, elev: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Elevation-detrended log-conductivity residual (CAL-88 auxiliary)."""
    logc = np.log1p(np.maximum(cond, 0.0))
    z = elev.astype(np.float64)
    m = footprint & np.isfinite(logc) & np.isfinite(z)
    if m.sum() < 100:
        return np.zeros_like(cond, dtype=np.float32)
    A = np.column_stack([np.ones(int(m.sum())), z[m]])
    y = logc[m]
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = coef[0] + coef[1] * z
    resid = (logc - pred).astype(np.float32)
    resid[~footprint] = 0.0
    return resid


def build_features(bands: dict[str, np.ndarray], footprint: np.ndarray) -> dict[str, np.ndarray]:
    cleaned = {k: clean_band(v, footprint) for k, v in bands.items()}
    fields = [
        cleaned["rtp"],
        cleaned["tmi_hg"],
        cleaned["iso_grav_anom_hg"],
        cleaned["depth_to_base_surf"],
        cleaned["det_elev"],
    ]
    thetas, energies = [], []
    for f in fields:
        th, en = structure_theta(f, footprint)
        thetas.append(th)
        energies.append(en)
    kappa = circular_resultant(thetas, energies, footprint)
    _, base_en = structure_theta(cleaned["depth_to_base_surf"], footprint, sigma=3.0)
    basement_step = percentile01(np.sqrt(base_en), footprint)
    slope = percentile01(cleaned["det_elev_slope"], footprint)
    low_slope = (1.0 - slope).astype(np.float32)
    low_slope[~footprint] = 0.0
    cal = percentile01(np.abs(cal_residual(cleaned["cond_surf"], cleaned["det_elev"], footprint)), footprint)
    # Feeder: coherent strike AND a basement step, down-weight high-slope dip-slope mimics.
    surface = (percentile01(kappa, footprint) * (0.35 + 0.65 * basement_step) * (0.40 + 0.60 * low_slope) * (0.70 + 0.30 * cal)).astype(np.float32)
    surface[~footprint] = 0.0
    return {
        "ssa_kappa": percentile01(kappa, footprint),
        "ssa_basement_step": basement_step,
        "ssa_low_slope": low_slope,
        "ssa_cal_residual": cal,
        "ssa_surface": surface,
    }
