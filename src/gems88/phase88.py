"""PHASE-88: label-blind cross-gradient *disagreement* of RTP and gravity.

No fault catalogue, previous predictions, or holdout labels enter this transform.
The amplitude normalization is empirical within the valid footprint only.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from .edge import clean_band, derivatives
from .fabric_dislocation import rank_footprint


def build_surface(rtp: np.ndarray, grav: np.ndarray, footprint: np.ndarray):
    fp = np.asarray(footprint, bool)
    if fp.ndim != 2 or rtp.shape != fp.shape or grav.shape != fp.shape:
        raise ValueError('RTP, gravity and footprint must share a two-dimensional grid')
    m, ms = clean_band(rtp, fp)
    g, gs = clean_band(grav, fp)
    my, mx = derivatives(m, fp, sigma=2.0)
    gy, gx = derivatives(g, fp, sigma=4.0)
    del m, g
    me = np.hypot(mx, my).astype(np.float32)
    ge = np.hypot(gx, gy).astype(np.float32)
    # |sin theta| distinguishes discordant geophysical boundaries from the
    # co-edges used in prior lanes. Opposite-polarity PARALLEL edges score 0.
    eps = np.float32(1e-8)
    cross = np.abs(mx * gy - my * gx) / (me * ge + eps)
    cross = np.clip(cross, 0., 1.).astype(np.float32)
    del mx, my, gx, gy
    # A broad cross gradient at a single isolated pixel is not a coherent
    # basement-break candidate. Rank-normalized independent edge energies.
    mr = rank_footprint(me, fp)
    gr = rank_footprint(ge, fp)
    cr = rank_footprint(gaussian_filter(cross, 1., mode='nearest', output=np.float32), fp)
    surface = (cr * np.sqrt(mr * gr)).astype(np.float32)
    surface[~fp] = 0
    if not np.isfinite(surface).all() or surface.min() < 0 or surface.max() > 1:
        raise ValueError('nonfinite/out-of-range PHASE-88 surface')
    return surface, {'gradient_misalignment': cross, 'rtp_gradient_strength': me,
                     'gravity_gradient_strength': ge, 'phase_surface': surface}, {'rtp':ms, 'gravity':gs}
