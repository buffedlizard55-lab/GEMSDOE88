"""H88-SDTL: stress-field slip/dilation-tendency lineament features.

Physical basis
--------------
Slip tendency ``Ts = tau / sigma_n`` and dilation tendency
``Td = (sigma1 - sigma_n) / (sigma1 - sigma3)`` (Morris, Ferrill & Henderson
1996, Geology 24:275-278; Ferrill et al. 1999, GSA Today 9(5):1-8) are
maximal for steep normal faults striking perpendicular to the least principal
stress ``sigma3``.  In the Great Basin, geothermal systems and the youngest
(Quaternary) fault scarps concentrate on such optimally oriented structures
(Faulds & Hinz 2015, World Geothermal Congress; Siler et al. 2019, Geosphere
15, doi:10.1130/GES02032.1).  Expert mapping of *new* faults from LiDAR is
biased toward fresh scarps, i.e. toward the active, optimally oriented
population.

Implementation choices (frozen in ``registry/preregistration_sdtl88.json``)
--------------------------------------------------------------------------
* The favourable strike is **not** imported from the literature.  It is the
  30 km Gaussian circular mean of the double-angle strike of the *visible*
  catalogue only, recomputed per holdout fold, so the feature family obeys the
  hide-and-recover rule (every catalogue-based feature from visible faults).
* Terrain and magnetic linear fabric orientation/coherence come from the
  gradient structure tensor (Bigun & Granlund 1987) of ``det_elev`` and of the
  magnetic tilt angle at 300 m / 1 km / 600 m integration scales.
* The kinematic regime is the zero-catalogue geodetic shear fraction
  ``shear / (shear + |dilatation|)``: where shear dominates (Walker Lane
  transtension) Riedel orientations at +/-30 degrees from the favourable
  strike are also favourable; where dilatation dominates, only the
  perpendicular-to-sigma3 orientation is.

All orientations are axial and represented by ``(cos 2*theta, sin 2*theta)``
so that a strike and its antiparallel are identical.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

SDTL_SCHEMA_VERSION = "sdtl-v1"

SDTL_FEATURES: tuple[str, ...] = (
    "sdtl_td_terrain_300",
    "sdtl_td_terrain_1000",
    "sdtl_td_mag_600",
    "sdtl_riedel_terrain_300",
    "sdtl_riedel_terrain_1000",
    "sdtl_regime_shear_frac",
    "sdtl_td_x_extension_300",
    "sdtl_riedel_x_shear_300",
    "sdtl_misorient_300",
    "sdtl_fav_concentration",
    "sdtl_coh_terrain_300",
    "sdtl_coh_terrain_1000",
)

ZERO_CATALOGUE_FEATURES: tuple[str, ...] = (
    "sdtl_regime_shear_frac",
    "sdtl_coh_terrain_300",
    "sdtl_coh_terrain_1000",
)

COS60 = 0.5
SIN60 = float(np.sqrt(3.0) / 2.0)


def _clean(band: np.ndarray, valid: np.ndarray, nodata: float | None) -> np.ndarray:
    a = np.asarray(band, np.float32).copy()
    bad = ~np.isfinite(a) | ~valid
    if nodata is not None:
        bad |= a <= np.float32(nodata) * np.float32(0.5) if nodata < 0 else a == np.float32(nodata)
    if bad.all():
        raise ValueError("band has no finite valid cells")
    fill = float(np.median(a[~bad]))
    a[bad] = fill
    return a


def structure_tensor_axial(field: np.ndarray, sigma_grad: float, sigma_int: float
                           ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Axial strike ``(cos 2t, sin 2t)`` and coherence of the dominant linear fabric.

    The gradient of a linear feature points *across* it, so the fabric strike
    is the gradient direction rotated by 90 degrees.  With ``J = [[Jxx, Jxy],
    [Jxy, Jyy]]`` the gradient-direction double angle is ``(Jxx - Jyy, 2 Jxy)``;
    rotating by 90 degrees negates the double-angle vector, giving the strike
    double angle ``(Jyy - Jxx, -2 Jxy)``.  Coherence is
    ``(l1 - l2) / (l1 + l2)`` in ``[0, 1]``.
    """
    f = np.asarray(field, np.float32)
    gy = ndi.gaussian_filter(f, sigma_grad, order=(1, 0), mode="nearest")
    gx = ndi.gaussian_filter(f, sigma_grad, order=(0, 1), mode="nearest")
    jxx = ndi.gaussian_filter(gx * gx, sigma_int, mode="nearest")
    jyy = ndi.gaussian_filter(gy * gy, sigma_int, mode="nearest")
    jxy = ndi.gaussian_filter(gx * gy, sigma_int, mode="nearest")
    u = jyy - jxx
    v = -2.0 * jxy
    mag = np.hypot(u, v)
    trace = jxx + jyy
    coh = np.where(trace > 0, mag / (trace + 1e-12), 0.0).astype(np.float32)
    c2 = np.where(mag > 0, u / (mag + 1e-20), 0.0).astype(np.float32)
    s2 = np.where(mag > 0, v / (mag + 1e-20), 0.0).astype(np.float32)
    return c2, s2, np.clip(coh, 0.0, 1.0)


def favourable_strike_field(visible: np.ndarray, footprint: np.ndarray, *,
                            sigma_trace: float = 1.5, sigma_region_px: float = 300.0
                            ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Regional favourable axial strike from the VISIBLE catalogue only.

    Returns unit ``(cos 2t_f, sin 2t_f)`` and the concentration ``R`` in
    ``[0, 1]`` (1 = all visible faults within the window share one strike).
    """
    vis = np.asarray(visible, bool) & np.asarray(footprint, bool)
    if not vis.any():
        raise ValueError("no visible catalogue to estimate a favourable strike")
    trace = ndi.gaussian_filter(vis.astype(np.float32), sigma_trace, mode="nearest")
    c2, s2, coh = structure_tensor_axial(trace, 1.0, 2.0)
    w = (vis.astype(np.float32) * coh).astype(np.float32)
    # Truncate the regional kernel at 3 sigma to bound cost on the 3730 x 3292 grid.
    wc = ndi.gaussian_filter(w * c2, sigma_region_px, mode="constant", truncate=3.0)
    ws = ndi.gaussian_filter(w * s2, sigma_region_px, mode="constant", truncate=3.0)
    ww = ndi.gaussian_filter(w, sigma_region_px, mode="constant", truncate=3.0)
    mag = np.hypot(wc, ws)
    conc = np.where(ww > 1e-9, mag / (ww + 1e-12), 0.0).astype(np.float32)
    cf = np.where(mag > 0, wc / (mag + 1e-20), 1.0).astype(np.float32)
    sf = np.where(mag > 0, ws / (mag + 1e-20), 0.0).astype(np.float32)
    return cf, sf, np.clip(conc, 0.0, 1.0)


def _tendencies(c2, s2, coh, cf, sf):
    """Dilation-tendency proxy, Riedel proxy and misorientation for one fabric."""
    cos2d = c2 * cf + s2 * sf          # cos 2(theta - theta_f)
    sin2d = s2 * cf - c2 * sf          # sin 2(theta - theta_f)
    cos_sq = 0.5 * (1.0 + cos2d)       # cos^2(delta)  -> Td proxy for normal faulting
    sin_sq = 1.0 - cos_sq
    # cos 2(delta -/+ 30deg) = cos2d*cos60 +/- sin2d*sin60
    r_plus = 0.5 * (1.0 + (cos2d * COS60 + sin2d * SIN60))
    r_minus = 0.5 * (1.0 + (cos2d * COS60 - sin2d * SIN60))
    riedel = np.maximum(r_plus, r_minus)
    td = np.maximum(coh * cos_sq, 0.0).astype(np.float32)
    ri = np.maximum(coh * riedel, 0.0).astype(np.float32)
    mis = np.maximum(coh * sin_sq, 0.0).astype(np.float32)
    return td, ri, mis


def load_zero_catalogue_fabric(root: Path, footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Terrain/magnetic fabric and geodetic regime; independent of any catalogue."""
    with rasterio.open(root / "data/training_features.tif") as src:
        for b, name in ((12, "det_elev"), (6, "tc"), (7, "geod_shearrate"), (8, "geod_dilaterate")):
            tag = src.tags(b).get("band_name")
            if tag != name:
                raise ValueError(f"band {b} is {tag!r}, expected {name!r}")
        nodata = src.nodata
        det = _clean(src.read(12), footprint, nodata)
        tc = _clean(src.read(6), footprint, nodata)
        shear = _clean(src.read(7), footprint, nodata)
        dil = _clean(src.read(8), footprint, nodata)
    c300, s300, coh300 = structure_tensor_axial(det, 1.0, 3.0)
    c1000, s1000, coh1000 = structure_tensor_axial(det, 2.0, 10.0)
    del det
    cm, sm, cohm = structure_tensor_axial(tc, 1.5, 6.0)
    del tc
    regime = (np.abs(shear) / (np.abs(shear) + np.abs(dil) + 1e-9)).astype(np.float32)
    return dict(c300=c300, s300=s300, coh300=coh300, c1000=c1000, s1000=s1000, coh1000=coh1000,
                cm=cm, sm=sm, cohm=cohm, regime=regime)


def build_sdtl_fp(fabric: dict[str, np.ndarray], visible: np.ndarray, footprint: np.ndarray,
                  cache_dir: Path, tag: str) -> np.memmap:
    """``(N_fp, 12)`` float32 memmap of SDTL features for one visible-catalogue state."""
    fp = np.asarray(footprint, bool)
    vis = np.asarray(visible, bool)
    key = hashlib.sha256(np.packbits(vis).tobytes()).hexdigest()[:16]
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat = cache_dir / f"sdtl_{SDTL_SCHEMA_VERSION}_{tag}_{key}.dat"
    meta = cache_dir / f"sdtl_{SDTL_SCHEMA_VERSION}_{tag}_{key}.json"
    n_fp = int(fp.sum())
    n_cols = len(SDTL_FEATURES)
    if dat.is_file() and meta.is_file():
        m = json.loads(meta.read_text())
        if m.get("features") == list(SDTL_FEATURES) and m.get("n_fp") == n_fp:
            return np.memmap(dat, dtype="float32", mode="r", shape=(n_fp, n_cols))
    cf, sf, conc = favourable_strike_field(vis, fp)
    td3, ri3, mis3 = _tendencies(fabric["c300"], fabric["s300"], fabric["coh300"], cf, sf)
    td10, ri10, _ = _tendencies(fabric["c1000"], fabric["s1000"], fabric["coh1000"], cf, sf)
    tdm, _, _ = _tendencies(fabric["cm"], fabric["sm"], fabric["cohm"], cf, sf)
    regime = fabric["regime"]
    cols = {
        "sdtl_td_terrain_300": td3,
        "sdtl_td_terrain_1000": td10,
        "sdtl_td_mag_600": tdm,
        "sdtl_riedel_terrain_300": ri3,
        "sdtl_riedel_terrain_1000": ri10,
        "sdtl_regime_shear_frac": regime,
        "sdtl_td_x_extension_300": (td3 * (1.0 - regime)).astype(np.float32),
        "sdtl_riedel_x_shear_300": (ri3 * regime).astype(np.float32),
        "sdtl_misorient_300": mis3,
        "sdtl_fav_concentration": conc,
        "sdtl_coh_terrain_300": fabric["coh300"],
        "sdtl_coh_terrain_1000": fabric["coh1000"],
    }
    tmp = dat.with_suffix(".tmp")
    mm = np.memmap(tmp, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    for j, name in enumerate(SDTL_FEATURES):
        v = cols[name][fp]
        if not np.isfinite(v).all():
            raise ValueError(f"non-finite SDTL feature {name}")
        mm[:, j] = v
    mm.flush()
    del mm
    tmp.replace(dat)
    meta.write_text(json.dumps(dict(features=list(SDTL_FEATURES), n_fp=n_fp, visible_key=key,
                                    schema=SDTL_SCHEMA_VERSION), indent=1))
    return np.memmap(dat, dtype="float32", mode="r", shape=(n_fp, n_cols))
