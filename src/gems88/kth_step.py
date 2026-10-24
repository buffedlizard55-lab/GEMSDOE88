"""K/Th antisymmetric radiometric step with a *separate* magnetic trough.

Geological hypothesis, not a validated vent detector. No catalogue pixels or
hidden truth enter the surface. The owner mirror's u8 K/Th is a derivative of
USGS GeoDAWN, not an authenticated download of the organizer's original bands.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from .edge import clean_band
from .fabric_dislocation import rank_footprint


def _masked_gaussian(a: np.ndarray, mask: np.ndarray, sigma: float) -> np.ndarray:
    w = mask.astype(np.float32)
    numerator = gaussian_filter(np.where(mask, a, 0).astype(np.float32), sigma, mode="constant")
    denominator = gaussian_filter(w, sigma, mode="constant")
    return numerator / np.maximum(denominator, np.float32(1e-6))


def build_surface(k: np.ndarray, th: np.ndarray, rtp: np.ndarray,
                  footprint: np.ndarray):
    fp = np.asarray(footprint, bool)
    if any(a.shape != fp.shape for a in (k, th, rtp)) or fp.ndim != 2:
        raise ValueError("bands and footprint must share the 2D template grid")
    rad_valid = fp & (k > 0) & (th > 0)
    if not rad_valid.any():
        raise ValueError("no radiometric coverage")
    # Quantized 0 is nodata in the owner-mirror derivative. CAUTION: the u8
    # channels have no physical-unit calibration metadata; this is a log ratio
    # of independently quantized *indices*, NOT a measured elemental K/Th ratio.
    # Normalize only by the measurable footprint so missing-data edges do not
    # create an artificial step across missing survey coverage.
    ratio = np.zeros(fp.shape, np.float32)
    ratio[rad_valid] = np.log((k[rad_valid].astype(np.float32) + 5.0) /
                              (th[rad_valid].astype(np.float32) + 5.0))
    sm = _masked_gaussian(ratio, rad_valid, 2.0)
    residual = sm - _masked_gaussian(ratio, rad_valid, 18.0)
    del ratio, sm
    step = np.zeros(fp.shape, np.float32)
    h, w = fp.shape
    for dy, dx in ((3, 0), (0, 3), (2, 2), (2, -2)):
        ay, ax = abs(dy), abs(dx)
        mid = (slice(ay, h - ay), slice(ax, w - ax))
        plus = (slice(ay+dy, h-ay+dy), slice(ax+dx, w-ax+dx))
        minus = (slice(ay-dy, h-ay-dy), slice(ax-dx, w-ax-dx))
        contrast = np.abs(residual[plus] - residual[minus])
        # At least 2 pixels of actual coverage on either flank; prevent a
        # missing-survey seam from masquerading as a linear potassium step.
        both = rad_valid[mid] & rad_valid[plus] & rad_valid[minus]
        np.maximum(step[mid], np.where(both, contrast, 0), out=step[mid])
    del residual
    clean, metadata = clean_band(rtp, fp)
    local = _masked_gaussian(clean, fp, 2.0)
    regional = _masked_gaussian(clean, fp, 12.0)
    trough = np.maximum(regional - local, 0).astype(np.float32)
    del clean, local, regional
    step_rank = rank_footprint(step, rad_valid)
    trough_rank = rank_footprint(trough, fp)
    # Frozen product: the radiometric change is primary; magnetic evidence
    # may modulate but cannot create a prediction where there was no K/Th step.
    surface = step_rank * (np.float32(.25) + np.float32(.75) * trough_rank)
    surface[~rad_valid] = 0.0
    if not np.isfinite(surface).all() or (surface < 0).any() or (surface > 1).any():
        raise ValueError("surface must be finite in [0,1]")
    return surface, {"kth_antisymmetric_step": step,
                     "rtp_demagnetization_trough": trough,
                     "kth_magnetic_surface": surface}, {
        "radiometric_covered_footprint_pixels": int(rad_valid.sum()),
        "rtp_cleaning": metadata,
        "distance_probe_px": 3,
        "local_sigma_px": 2,
        "background_sigma_px": 18,
        "rtp_background_sigma_px": 12}
