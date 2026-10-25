"""H88-MTAS: cross-scale gravity-minus-magnetic admittance residual.

Frozen lane definition: ``research/candidate-hypotheses-20261025-mtas.md`` and
``registry/preregistration_mtas88.json`` (2026-10-25, frozen before computation).

Scientific idea (one scalar, label-blind, zero catalogue-derived inputs):
a buried basement fault beneath low-relief cover can keep a *short-scale
gravity edge* while its *magnetic edge is smoothed/demagnetized* at the same
short scale.  The surface rewards exactly that scale discordance,

    contrast = max(0, (G200 - G800) - (M200 - M800)),

soft-gated by basin cover (thick basement depth), low terrain slope (no
mapped-scarp shortcut) and geodetic transtension.  It therefore targets a
fault *missing* from the USGS/INGENIOUS catalogue (no surface scarp, hence
unmapped), not catalogue geometry.

Named non-fault mimic: an unfaulted intrusive/volcanic lithologic contact
with density contrast but weak magnetic contrast; second confounder:
east-west flight-line levelling seams in the airborne grids.

The seven input columns are computed with the *shared* definitions in
``src/gems88/physics.py`` (``_grad_f32`` at sigma 2 px = 200 m and 8 px =
800 m, ``log1p`` gradient magnitudes, gravity gradients scaled by 100 before
``log1p`` exactly as in the cached 44-channel stack) and the shared
``src/gems88/edge.clean_band`` cleaner.  No private fork: this module only
assembles those columns into the preregistered MTAS contrast.  Raw bands used
(competition ``training_features.tif`` band tags verified on disk):
2 ``rtp``, 7 ``geod_shearrate``, 8 ``geod_dilaterate``, 13 ``iso_grav_anom``,
15 ``depth_to_base_surf``, 19 ``det_elev_slope``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import maximum_filter

from .edge import clean_band
from .physics import _grad_f32

# Competition band indices (1-based), tags asserted against EXPECTED_TRAINING_BANDS.
BAND_RTP = 2
BAND_SHEARRATE = 7
BAND_DILATERATE = 8
BAND_ISO_GRAV = 13
BAND_DEPTH_TO_BASE = 15
BAND_DET_ELEV_SLOPE = 19

INPUT_NAMES = (
    "rtp_grad_200m",
    "rtp_grad_800m",
    "grav_grad_200m",
    "grav_grad_800m",
    "depth_to_base_log",
    "det_elev_slope",
    "geod_transtension",
)

COMPONENT_NAMES = (
    "grav_scale_residual",   # G200n - G800n
    "mag_scale_residual",    # M200n - M800n
    "admittance_contrast",   # normalized max(0, grav_scale - mag_scale)
    "cover_gate",            # normalized depth_to_base_log
    "low_slope_gate",        # 1 - normalized det_elev_slope
    "transtension_gate",     # normalized geod_transtension
    "mtas_surface",          # gated composite in [0, 1]
)

DOT_CAP = 37_654            # preregistered cap (matches the H33-lineage budget)
MAX_FILTER_SIZE = 5         # preregistered 5x5 local-maxima placement


def percentile01(arr: np.ndarray, footprint: np.ndarray,
                 lo: float = 2.0, hi: float = 98.0) -> np.ndarray:
    """Linearly map the [lo, hi] footprint percentile range to [0, 1]."""
    v = arr[footprint]
    p_lo, p_hi = (float(x) for x in np.percentile(v, [lo, hi]))
    if not np.isfinite(p_lo) or not np.isfinite(p_hi) or p_hi <= p_lo:
        return np.zeros(arr.shape, dtype=np.float32)
    out = np.clip((arr.astype(np.float32) - p_lo) / (p_hi - p_lo), 0.0, 1.0)
    out = out.astype(np.float32)
    out[~footprint] = 0.0
    return out


def load_inputs(feat_path: Path, footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Compute the seven preregistered MTAS columns as full-grid float32 arrays.

    Definitions are copied operator-for-operator from the shared cached-stack
    builder ``physics.build_or_load_physics_memmap`` (columns 0, 1, 2, 3, 18,
    21, 24 of ``ALL_PHYS_FEATURES``); only the storage layout differs
    (full grid here vs footprint memmap there).
    """
    from .physics import EXPECTED_TRAINING_BANDS

    with rasterio.open(feat_path) as src:
        if src.count != 19:
            raise ValueError(f"expected 19 bands, got {src.count}")
        for idx in (BAND_RTP, BAND_SHEARRATE, BAND_DILATERATE, BAND_ISO_GRAV,
                    BAND_DEPTH_TO_BASE, BAND_DET_ELEV_SLOPE):
            got = src.tags(idx).get("band_name", "")
            want = EXPECTED_TRAINING_BANDS[idx]
            if got != want:
                raise ValueError(f"band {idx}: expected {want!r}, got {got!r}")

        def rd(idx: int) -> np.ndarray:
            return clean_band(src.read(idx), footprint)[0]

        rtp = rd(BAND_RTP)
        grav = rd(BAND_ISO_GRAV)
        depth = np.maximum(rd(BAND_DEPTH_TO_BASE), 0.0)
        slope = rd(BAND_DET_ELEV_SLOPE)
        shear = rd(BAND_SHEARRATE)
        dilate = rd(BAND_DILATERATE)

    _, _, rmag2 = _grad_f32(rtp, 2.0)
    _, _, rmag8 = _grad_f32(rtp, 8.0)
    del rtp
    _, _, gmag2 = _grad_f32(grav, 2.0)
    _, _, gmag8 = _grad_f32(grav, 8.0)
    del grav

    out = {
        "rtp_grad_200m": np.log1p(rmag2).astype(np.float32),
        "rtp_grad_800m": np.log1p(rmag8).astype(np.float32),
        "grav_grad_200m": np.log1p(gmag2 * 100.0).astype(np.float32),
        "grav_grad_800m": np.log1p(gmag8 * 100.0).astype(np.float32),
        "depth_to_base_log": np.log1p(depth).astype(np.float32),
        "det_elev_slope": slope.astype(np.float32),
        "geod_transtension": (shear * np.maximum(dilate, 0.0)).astype(np.float32),
    }
    for arr in out.values():
        arr[~footprint] = 0.0
    return out


def build_components(inputs: dict[str, np.ndarray],
                     footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Frozen MTAS composite.  All normalizations are label-blind percentiles."""
    g200 = percentile01(inputs["grav_grad_200m"], footprint)
    g800 = percentile01(inputs["grav_grad_800m"], footprint)
    m200 = percentile01(inputs["rtp_grad_200m"], footprint)
    m800 = percentile01(inputs["rtp_grad_800m"], footprint)

    grav_scale = (g200 - g800).astype(np.float32)
    mag_scale = (m200 - m800).astype(np.float32)
    del g200, g800, m200, m800
    grav_scale[~footprint] = 0.0
    mag_scale[~footprint] = 0.0

    contrast_raw = np.maximum(grav_scale - mag_scale, 0.0).astype(np.float32)
    contrast = percentile01(contrast_raw, footprint, lo=5.0, hi=99.5)
    del contrast_raw

    cover = percentile01(inputs["depth_to_base_log"], footprint)
    slope_n = percentile01(inputs["det_elev_slope"], footprint)
    low_slope = (1.0 - slope_n).astype(np.float32)
    low_slope[~footprint] = 0.0
    del slope_n
    transtension = percentile01(inputs["geod_transtension"], footprint)

    # Soft multiplicative gates, fixed before any holdout evaluation:
    # cover and low-slope can each attenuate to 25%, transtension to 50%.
    surface = (
        contrast
        * (0.25 + 0.75 * cover)
        * (0.25 + 0.75 * low_slope)
        * (0.50 + 0.50 * transtension)
    ).astype(np.float32)
    surface[~footprint] = 0.0
    np.clip(surface, 0.0, 1.0, out=surface)

    return {
        "grav_scale_residual": grav_scale,
        "mag_scale_residual": mag_scale,
        "admittance_contrast": contrast,
        "cover_gate": cover,
        "low_slope_gate": low_slope,
        "transtension_gate": transtension,
        "mtas_surface": surface,
    }


def place_maxima(surface: np.ndarray, allowed: np.ndarray,
                 cap: int = DOT_CAP, size: int = MAX_FILTER_SIZE) -> np.ndarray:
    """Preregistered placement: 5x5 local maxima, fixed rank order, capped.

    Rank order is descending surface value with raster (row-major) order as
    the deterministic tie-break.  Returns a float32 binary {0, 1} grid.
    """
    surf = np.asarray(surface, np.float32)
    allowed = np.asarray(allowed, bool)
    if surf.shape != allowed.shape:
        raise ValueError("surface/allowed shape mismatch")
    local_max = maximum_filter(surf, size=size, mode="nearest")
    mask = allowed & (surf > 0) & (surf == local_max)
    del local_max
    flat = np.flatnonzero(mask.ravel())
    out = np.zeros(surf.shape, dtype=np.float32)
    if flat.size == 0:
        return out
    vals = surf.ravel()[flat]
    order = np.argsort(-vals, kind="stable")  # stable => raster-order ties
    chosen = flat[order[:cap]]
    out.ravel()[chosen] = 1.0
    return out
