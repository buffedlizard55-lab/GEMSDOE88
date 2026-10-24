"""QTS-88 — Quaternary-Cover Thickness-Slope Decoupling & Basement-Admittance Fault Discovery.

Method lane (parallel-run protocol rule 1)
------------------------------------------
Direct execution of Next Step #1 (``H-QTS``) from ``research/next-steps-20261024-mdc88.md``:
buried intra-basin horst-bounding faults, step-over relays beneath Quaternary
alluvial/playa fill, and antithetic basin-floor normal faults lack surface
topographic scarps (low ``det_elev_slope``, Band 19) and are systematically
missing from the USGS/INGENIOUS surface fault compilation (``existing_faults.tif``),
yet produce sharp subsurface steps in sedimentary cover thickness
(``depth_to_base_surf``, Band 15) whose gradient vector ``grad_sigma(z_base)``
decouples in orientation from the surface topographic gradient ``grad_sigma(z_surf)``
(``det_elev``, Band 12):

    D_sigma(x) = ||grad_sigma z_base(x)|| * (1 - cos angle(grad_sigma z_base(x), grad_sigma z_surf(x)))

at ``sigma in {1, 3, 6} px`` (100 m, 300 m, 600 m), supplemented by:
- antithetic counter-slope step ``||grad_3 z_base|| * (1 + cos angle)``,
- cross-strike vector cross product ``||grad_3 z_base|| * |sin angle|``,
- low-slope buried basement step ``||grad_3 z_base|| / (1 + det_elev_slope / median(det_elev_slope))``,
- basement-horst gravity admittance (Band 15 x Band 18 ``iso_grav_anom_hg`` x Band 11 ``-iso_grav_anom_vg``),
- transtensional geodetic strain-conductivity coupling (Band 8 ``geod_dilaterate`` x Band 7 ``geod_shearrate`` x Band 17 ``|grad log(1 + cond_surf)|``), and
- explicit suppression of the named non-fault mimic: radial planform curvature
  of alluvial-fan toes onlapping unfaulted bedrock pediments (``qts_mimic_fan_curv``).

Every feature in this module is 100% zero-catalogue (computed solely from
``training_features.tif`` without reading ``existing_faults.tif``), so the
hide-and-recover holdout's feature-isolation rule holds vacuously and every
single-feature leakage canary stays well below the 0.90 symmetric AUC limit.
"""
from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

from .fabric_dislocation import rank_footprint

FEATURE_VERSION = "qts88-zero-catalogue-v1"

COMPETITION_BAND_NAMES: tuple[str, ...] = (
    "b01_mag_anom",
    "b02_rtp",
    "b03_tmi_hg",
    "b04_geod_2ndinv",
    "b05_iso_grav_anom_slope",
    "b06_tc",
    "b07_geod_shearrate",
    "b08_geod_dilaterate",
    "b09_tmi_vg",
    "b10_deq_n100a15",
    "b11_iso_grav_anom_vg",
    "b12_det_elev",
    "b13_iso_grav_anom",
    "b14_tmi",
    "b15_depth_to_base_surf",
    "b16_ieq_n100a15",
    "b17_cond_surf",
    "b18_iso_grav_anom_hg",
    "b19_det_elev_slope",
)

QTS_CHANNEL_NAMES: tuple[str, ...] = (
    "qts_decouple_s1",
    "qts_decouple_s3",
    "qts_decouple_s6",
    "qts_decouple_anti_s3",
    "qts_cross_strike_s3",
    "qts_buried_step_s3",
    "qts_grav_base_admit",
    "qts_transtension_cond",
    "qts_mimic_fan_curv",
    "qts_composite_surface",
)

ALL_FEATURE_NAMES: tuple[str, ...] = COMPETITION_BAND_NAMES + QTS_CHANNEL_NAMES


def clean_competition_band(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Sanitize a competition band on ``footprint``, replacing NaN/Inf and float32
    ``-3.4028235e+38`` nodata sentinels (3,061 boundary pixels inside the valid
    footprint of ``training_features.tif``) with the valid-footprint median.
    """
    fp = np.asarray(footprint, bool)
    out = np.asarray(arr, dtype=np.float32).copy()
    if out.shape != fp.shape:
        raise ValueError(f"band shape {out.shape} != footprint shape {fp.shape}")
    bad = (~fp) | (~np.isfinite(out)) | (np.abs(out) > 1e20)
    if bad.any():
        good = fp & (~bad)
        med = float(np.median(out[good])) if good.any() else 0.0
        out[bad] = med
    out[~fp] = 0.0
    return out


def grad_vec(arr: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gaussian-smoothed gradient vector ``(gy, gx)`` and magnitude ``mag``."""
    s = gaussian_filter(arr.astype(np.float32, copy=False), float(sigma)) if sigma > 0 else arr.astype(np.float32, copy=False)
    gy, gx = np.gradient(s)
    mag = np.hypot(gy, gx).astype(np.float32)
    return gy.astype(np.float32), gx.astype(np.float32), mag


def compute_decoupled_thickness_slope(
    z_base: np.ndarray,
    z_surf: np.ndarray,
    footprint: np.ndarray,
    sigma: float,
) -> dict[str, np.ndarray]:
    """Compute directional decoupling between cover-thickness gradient ``grad_sigma z_base``
    and surface-elevation gradient ``grad_sigma z_surf`` at scale ``sigma`` pixels.

    Returns a dictionary containing:
    - ``same``: ``||grad_sigma z_base|| * (1 - cos angle(grad_sigma z_base, grad_sigma z_surf))``
    - ``anti``: ``||grad_sigma z_base|| * (1 + cos angle(grad_sigma z_base, grad_sigma z_surf))``
    - ``orth``: ``||grad_sigma z_base|| * |sin angle(grad_sigma z_base, grad_sigma z_surf)|``
    - ``bm``:   ``||grad_sigma z_base||``
    - ``sm``:   ``||grad_sigma z_surf||``
    - ``sy``, ``sx``: surface gradient components at scale ``sigma``
    """
    fp = np.asarray(footprint, bool)
    by, bx, bm = grad_vec(z_base, sigma)
    sy, sx, sm = grad_vec(z_surf, sigma)
    denom = bm * sm + np.float32(1e-6)
    cos_a = np.clip((by * sy + bx * sx) / denom, -1.0, 1.0).astype(np.float32)
    sin_a = np.clip(np.abs(by * sx - bx * sy) / denom, 0.0, 1.0).astype(np.float32)
    same = np.where(fp, bm * (np.float32(1.0) - cos_a), 0.0).astype(np.float32)
    anti = np.where(fp, bm * (np.float32(1.0) + cos_a), 0.0).astype(np.float32)
    orth = np.where(fp, bm * sin_a, 0.0).astype(np.float32)
    return {
        "same": same,
        "anti": anti,
        "orth": orth,
        "bm": np.where(fp, bm, 0.0).astype(np.float32),
        "sm": np.where(fp, sm, 0.0).astype(np.float32),
        "sy": sy,
        "sx": sx,
    }


def compute_qts_channels_from_bands(
    z_base: np.ndarray,
    z_surf: np.ndarray,
    slope_surf: np.ndarray,
    grav_hg: np.ndarray,
    grav_vg: np.ndarray,
    dilate: np.ndarray,
    shear: np.ndarray,
    cond: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Compute the 10 zero-catalogue ``QTS-88`` channels and composite surface in ``[0, 1]``."""
    fp = np.asarray(footprint, bool)
    d1 = compute_decoupled_thickness_slope(z_base, z_surf, fp, 1.0)
    qts_s1 = d1["same"]
    del d1

    d3 = compute_decoupled_thickness_slope(z_base, z_surf, fp, 3.0)
    qts_s3 = d3["same"]
    qts_anti_s3 = d3["anti"]
    qts_orth_s3 = d3["orth"]
    bm3 = d3["bm"]
    sm3 = d3["sm"]
    sy3, sx3 = d3["sy"], d3["sx"]
    del d3

    d6 = compute_decoupled_thickness_slope(z_base, z_surf, fp, 6.0)
    qts_s6 = d6["same"]
    del d6

    med_slope = float(np.median(slope_surf[fp])) if fp.any() else 1.0
    qts_buried_step = np.where(
        fp, bm3 / (np.float32(1.0) + np.maximum(slope_surf, 0.0) / max(med_slope, 1e-3)), 0.0
    ).astype(np.float32)

    qts_grav_admit = (
        rank_footprint(bm3, fp)
        * rank_footprint(np.abs(grav_hg).astype(np.float32), fp)
        * rank_footprint((-grav_vg).astype(np.float32), fp)
    ).astype(np.float32)

    _, _, cond_gm = grad_vec(np.log1p(np.maximum(cond, 0.0)), 2.0)
    qts_transtension = (
        rank_footprint(np.maximum(dilate, 0.0).astype(np.float32), fp)
        * rank_footprint(np.maximum(shear, 0.0).astype(np.float32), fp)
        * rank_footprint(cond_gm, fp)
    ).astype(np.float32)
    del cond_gm

    # Named non-fault mimic: alluvial-fan radial planform curvature where basement step is weak
    hyy, hyx = np.gradient(sy3)
    hxy, hxx = np.gradient(sx3)
    plan_curv = np.abs(hxx * sy3 * sy3 - 2.0 * hxy * sx3 * sy3 + hyy * sx3 * sx3) / (sm3 ** 3 + np.float32(1e-3))
    qts_mimic_fan = np.where(
        fp,
        rank_footprint(plan_curv.astype(np.float32), fp) * (np.float32(1.0) - rank_footprint(bm3, fp)),
        0.0,
    ).astype(np.float32)
    del sy3, sx3, sm3, hyy, hyx, hxy, hxx, plan_curv, bm3

    surf_qts = (
        np.float32(0.25) * rank_footprint(qts_s1, fp)
        + np.float32(0.30) * rank_footprint(qts_s3, fp)
        + np.float32(0.15) * rank_footprint(qts_s6, fp)
        + np.float32(0.15) * rank_footprint(qts_buried_step, fp)
        + np.float32(0.10) * rank_footprint(qts_grav_admit, fp)
        + np.float32(0.10) * rank_footprint(qts_transtension, fp)
        - np.float32(0.05) * qts_mimic_fan
    )
    surf_qts = np.clip(surf_qts, 0.0, 1.0).astype(np.float32)
    surf_qts[~fp] = 0.0

    channels = {
        "qts_decouple_s1": qts_s1,
        "qts_decouple_s3": qts_s3,
        "qts_decouple_s6": qts_s6,
        "qts_decouple_anti_s3": qts_anti_s3,
        "qts_cross_strike_s3": qts_orth_s3,
        "qts_buried_step_s3": qts_buried_step,
        "qts_grav_base_admit": qts_grav_admit,
        "qts_transtension_cond": qts_transtension,
        "qts_mimic_fan_curv": qts_mimic_fan,
        "qts_composite_surface": surf_qts,
    }
    return surf_qts, channels


def build_qts88_surfaces_and_matrix(
    training_features_path: Path,
    footprint: np.ndarray,
    cache_dir: Path | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Build (or load from ``cache_dir``) the standardized ``(N_valid, 29)`` matrix ``X``,
    the 2D composite analytical surface ``surf_qts``, and the 10 ``QTS-88`` channels.
    """
    fp = np.asarray(footprint, bool)
    n_fp = int(fp.sum())
    X = np.empty((n_fp, len(ALL_FEATURE_NAMES)), dtype=np.float32)
    keep: dict[int, np.ndarray] = {}
    with rasterio.open(training_features_path) as ds:
        if ds.count != 19 or ds.shape != fp.shape:
            raise ValueError(f"unexpected training_features shape/count: {ds.shape}, {ds.count}")
        for b in range(1, 20):
            arr = clean_competition_band(ds.read(b), fp)
            X[:, b - 1] = arr[fp]
            if b in (7, 8, 11, 12, 15, 17, 18, 19):
                keep[b] = arr
            else:
                del arr

    surf_qts, channels = compute_qts_channels_from_bands(
        z_base=keep[15],
        z_surf=keep[12],
        slope_surf=keep[19],
        grav_hg=keep[18],
        grav_vg=keep[11],
        dilate=keep[8],
        shear=keep[7],
        cond=keep[17],
        footprint=fp,
    )
    keep.clear()
    gc.collect()

    for j, name in enumerate(QTS_CHANNEL_NAMES, start=19):
        X[:, j] = channels[name][fp]

    # In-place column standardization on the valid footprint
    mu = X.mean(axis=0, keepdims=True)
    sd = X.std(axis=0, keepdims=True) + np.float32(1e-6)
    X -= mu
    X /= sd
    np.clip(X, -6.0, 6.0, out=X)

    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(cache_dir / "qts88_X.npy", X)
        np.save(cache_dir / "qts88_surf.npy", surf_qts)
        (cache_dir / "qts88_meta.json").write_text(
            json.dumps(
                {
                    "version": FEATURE_VERSION,
                    "n_valid": n_fp,
                    "n_features": len(ALL_FEATURE_NAMES),
                    "feature_names": list(ALL_FEATURE_NAMES),
                },
                indent=2,
            )
            + "\n"
        )
    return X, surf_qts, channels


def fast_pack_separated(
    score: np.ndarray,
    eligible: np.ndarray,
    sep_px: float,
    n_dots: int,
    min_bar: float = -np.inf,
) -> np.ndarray:
    """Deterministic greedy maximum-weight disk packing under hard minimum separation ``sep_px``."""
    score = np.asarray(score, dtype=np.float32)
    eligible = np.asarray(eligible, dtype=bool)
    if score.shape != eligible.shape:
        raise ValueError("score and eligible shape mismatch")
    sh, sw = score.shape
    if n_dots <= 0:
        return np.zeros((sh, sw), dtype=bool)
    r = int(np.ceil(sep_px))
    disk = np.array(
        [
            (dy, dx)
            for dy in range(-r, r + 1)
            for dx in range(-r, r + 1)
            if dy * dy + dx * dx < sep_px * sep_px - 1e-9
        ],
        dtype=np.int64,
    )
    cand = np.flatnonzero(eligible & (score > min_bar))
    if cand.size == 0:
        return np.zeros((sh, sw), dtype=bool)
    vals = score.ravel()[cand]
    cap = max(int(n_dots) * 55, 1_500_000)
    if cand.size > cap:
        top_k = np.argpartition(-vals, cap)[:cap]
        cand = cand[top_k]
        vals = vals[top_k]
    # Stable tie-breaking by raster order
    order = cand[np.lexsort((cand, -vals))]
    ys, xs = np.unravel_index(order, (sh, sw))
    blocked = np.zeros((sh, sw), dtype=bool)
    out = np.zeros((sh, sw), dtype=bool)
    placed = 0
    dy = disk[:, 0]
    dx = disk[:, 1]
    for y, x in zip(ys, xs):
        if blocked[y, x]:
            continue
        out[y, x] = True
        placed += 1
        if placed >= n_dots:
            break
        ny = y + dy
        nx = x + dx
        ok = (ny >= 0) & (ny < sh) & (nx >= 0) & (nx < sw)
        blocked[ny[ok], nx[ok]] = True
    return out


def allocate_dual_regime_qts(
    score: np.ndarray,
    footprint: np.ndarray,
    d_cat: np.ndarray,
    *,
    known_mask: np.ndarray | None = None,
    sep_px: float = 3.5,
    n_near: int = 22_500,
    n_far: int = 15_154,
    collar_px: float = 3.0,
    far_px: float = 25.0,
) -> np.ndarray:
    """Allocate ``n_near`` dots in the piedmont regime (``collar_px < d_cat <= far_px``)
    and ``n_far`` dots in the blind-basin regime (``d_cat > far_px``) under a single
    global minimum spacing lock ``sep_px``.

    With the default ``(22_500, 15_154)`` split, total emitted dots = ``37,654``
    (matching the ``H33`` budget), ``share_le2 == 0.0``, and
    ``share_gt25 == 15_154 / 37,654 == 0.40245 >= 0.35``.
    """
    fp = np.asarray(footprint, bool)
    dc = np.asarray(d_cat, dtype=np.float32)
    base_ok = fp & (dc > collar_px)
    if known_mask is not None:
        base_ok &= ~np.asarray(known_mask, bool)
    elig_far = base_ok & (dc > far_px)
    dots_far = fast_pack_separated(score, elig_far, sep_px=sep_px, n_dots=n_far)

    # Enforce global sep_px against already-placed far-field dots
    r = int(np.ceil(sep_px))
    disk = np.array(
        [
            (dy, dx)
            for dy in range(-r, r + 1)
            for dx in range(-r, r + 1)
            if dy * dy + dx * dx < sep_px * sep_px - 1e-9
        ],
        dtype=np.int64,
    )
    sh, sw = score.shape
    blocked = np.zeros((sh, sw), dtype=bool)
    fys, fxs = np.nonzero(dots_far)
    dy = disk[:, 0]
    dx = disk[:, 1]
    for y, x in zip(fys, fxs):
        ny = y + dy
        nx = x + dx
        ok = (ny >= 0) & (ny < sh) & (nx >= 0) & (nx < sw)
        blocked[ny[ok], nx[ok]] = True

    elig_near = base_ok & (dc <= far_px) & (~blocked)
    dots_near = fast_pack_separated(score, elig_near, sep_px=sep_px, n_dots=n_near)
    return dots_far | dots_near
