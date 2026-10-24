"""Label-blind paired-side *magnetic fabric dislocation* hypothesis.

USGS Dixie Valley O.F. 02-384 documents shallow buried faults imaged by local
magnetic anomalies and also warns that magnetic basement geology can mask them.
This is a geological *hypothesis*, not a fault detector whose positives have
been confirmed in the field. Catalogue geometry is never passed to this module.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from .edge import clean_band, derivatives

# Frozen in registry/preregistration_fabric_dislocation.json before scoring.
SIDES = ((3, 0), (0, 3), (2, 2), (2, -2))


def axial_side_contrast(qx: np.ndarray, qy: np.ndarray,
                        valid: np.ndarray, pairs=SIDES) -> np.ndarray:
    """A change in coherent, *axial* gradient direction on opposite sides.

    Axial q=(cos 2theta,sin 2theta)*coherence identifies antiparallel directions
    as the same fabric. Scores vanish for constant fabric even if its original
    scalar field has a strong edge. Boundary pairs are never wrapped across the
    grid; both sides must lie inside the footprint.
    """
    qx = np.asarray(qx, dtype=np.float32)
    qy = np.asarray(qy, dtype=np.float32)
    valid = np.asarray(valid, dtype=bool)
    if qx.ndim != 2 or qx.shape != qy.shape or qx.shape != valid.shape:
        raise ValueError("paired-side field and footprint must be matching 2-D arrays")
    if not np.isfinite(qx).all() or not np.isfinite(qy).all():
        raise ValueError("axial fabric must be finite")
    h, w = qx.shape
    coh = np.hypot(qx, qy)
    result = np.zeros((h, w), dtype=np.float32)
    for dy, dx in pairs:
        ay, ax = abs(dy), abs(dx)
        if h <= 2 * ay or w <= 2 * ax:
            continue
        mid = (slice(ay, h - ay), slice(ax, w - ax))
        plus = (slice(ay + dy, h - ay + dy), slice(ax + dx, w - ax + dx))
        minus = (slice(ay - dy, h - ay - dy), slice(ax - dx, w - ax - dx))
        difference = np.hypot(qx[plus] - qx[minus], qy[plus] - qy[minus]) * 0.5
        difference *= np.minimum(coh[plus], coh[minus])
        difference *= valid[plus] & valid[minus] & valid[mid]
        np.maximum(result[mid], difference, out=result[mid])
    return result


def rank_footprint(field: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Label-free quantile scale with deterministic subsampling and no sorting of truth.

    Repeated quantiles are collapsed, so uniform-input fields have rank zero
    and can never produce a spurious constant positive submission surface.
    """
    field = np.asarray(field, dtype=np.float32)
    valid = np.asarray(valid, bool)
    if field.shape != valid.shape or not np.isfinite(field[valid]).all():
        raise ValueError("percentile inputs must be finite on the valid footprint")
    out = np.zeros(field.shape, dtype=np.float32)
    if not valid.any():
        return out
    data = field[valid]
    sample = data[::37]
    knots, ix = np.unique(np.quantile(sample, np.linspace(0, 1, 257)), return_index=True)
    if len(knots) > 1:
        out[valid] = np.interp(data, knots, ix.astype(float) / 256.0).astype(np.float32)
    return out


def build_surface(rtp: np.ndarray, grav: np.ndarray,
                  footprint: np.ndarray) -> tuple[np.ndarray, dict[str, np.ndarray], dict]:
    """Produce the frozen four-channel unsupervised structural candidate field."""
    fp = np.asarray(footprint, bool)
    if rtp.shape != fp.shape or grav.shape != fp.shape or fp.ndim != 2:
        raise ValueError("both competition bands must match the two-dimensional grid")
    m, ms = clean_band(rtp, fp)
    g, gs = clean_band(grav, fp)
    my, mx = derivatives(m, fp, sigma=2.0)
    del m
    mag_energy = np.hypot(my, mx).astype(np.float32)
    # Smooth each locally quadratic tensor component. Normalization cancels
    # magnetic contrast amplitude; it does not change with gradient sign.
    xx = gaussian_filter(mx * mx, 4.0, mode="nearest", output=np.float32)
    yy = gaussian_filter(my * my, 4.0, mode="nearest", output=np.float32)
    xy = gaussian_filter(mx * my, 4.0, mode="nearest", output=np.float32)
    del mx, my
    trace = xx + yy
    # A near-zero tensor is an orientation-free cell: epsilon suppresses it.
    eps = max(float(np.percentile(trace[fp][::37], 25)) * 0.001, 1e-8)
    qx = (xx - yy) / (trace + np.float32(eps))
    qy = (2.0 * xy) / (trace + np.float32(eps))
    del xx, yy, xy, trace
    side = axial_side_contrast(qx, qy, fp)
    del qx, qy
    gy, gx = derivatives(g, fp, sigma=3.0)
    del g
    grav_energy = np.hypot(gy, gx).astype(np.float32)
    del gy, gx
    # Preserve the *dislocation* as the primary signal; independent gravity
    # and local magnetic energy only modulate its rank. All coefficients frozen.
    sr = rank_footprint(side, fp)
    gr = rank_footprint(grav_energy, fp)
    mr = rank_footprint(mag_energy, fp)
    surface = sr * (np.float32(.35) + np.float32(.65) * gr)
    surface *= np.float32(.25) + np.float32(.75) * mr
    surface[~fp] = 0
    if not np.isfinite(surface).all() or (surface < 0).any() or (surface > 1).any():
        raise ValueError("computed structural surface is not finite in [0,1]")
    return surface, {"rtp_fabric_dislocation": side,
                     "rtp_gradient_energy": mag_energy,
                     "gravity_gradient_energy": grav_energy,
                     "fabric_gravity_surface": surface}, {"rtp": ms, "gravity": gs, "tensor_epsilon": eps}
