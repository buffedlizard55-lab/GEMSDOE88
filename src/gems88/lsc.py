"""H88-LSC: lidar step-coherence zero-catalogue feature stack.

36 label-blind channels built from
* ``data/external/lidar_scarp_features_u8.tif`` (3DEP 1 m lidar derived, 12 bands),
* ``data/external/topo_10m_derived_100m_u8.tif`` (3DEP 1/3" derived, 9 bands),
* ``data/external/dem10_chi_100m_u8.tif`` (channel / knickpoint counts),
* ``data/training_features.tif`` (organizer 19-band; 8 bands used).

``existing_faults.tif`` is never read here: the catalogue enters only the
training labels and the emission collar in the experiment runner.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

SCHEMA = "lsc88-36ch-v1"

LIDAR_BANDS = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
               "downface_max", "upface_max", "cross_max", "relief", "coh100",
               "strike", "valid"]
TOPO_BANDS = ["slope_p90", "slope_max", "steep_frac", "slope_std", "relief_local",
              "curv_prof_absmax", "aspect_coherence", "hs_lineament", "dem_mean"]
CHI_BANDS = {"chan_n": 1, "knick_n": 2}
ORG_BANDS = {"det_elev": 12, "det_slope": 19, "mag_tilt": 6, "depth_to_base": 15,
             "cond_surf": 17, "rtp": 2, "grav_hg": 18, "tmi_hg": 3}
DERIVED = ["step_coh", "couplet", "persist", "strike_sin2", "strike_cos2"]

FEATURES: tuple[str, ...] = tuple(
    [f"lidar_{b}" for b in LIDAR_BANDS] + DERIVED
    + [f"topo_{b}" for b in TOPO_BANDS] + list(CHI_BANDS) + list(ORG_BANDS))

# Organizer-only ablation arm (no lidar / 10 m topo information).
ORGANIZER_ONLY: tuple[str, ...] = tuple(ORG_BANDS)


def _line_kernels(length: int = 5) -> list[np.ndarray]:
    r = length // 2
    ks = []
    for theta in (0.0, 45.0, 90.0, 135.0):
        k = np.zeros((length, length), np.float32)
        t = np.deg2rad(theta)
        for s in range(-r, r + 1):
            y = int(round(-s * np.sin(t)))
            x = int(round(s * np.cos(t)))
            k[r + y, r + x] = 1.0
        ks.append(k / k.sum())
    return ks


def _clean(a: np.ndarray, fp: np.ndarray, nodata=None) -> np.ndarray:
    v = a.astype(np.float32)
    bad = ~np.isfinite(v) | (np.abs(v) > 1e18)
    if nodata is not None:
        bad |= v == nodata
    bad |= ~fp
    if (~bad).any():
        med = float(np.median(v[~bad]))
    else:
        med = 0.0
    v[bad] = med
    return v


def build_or_load(root: Path, footprint: np.ndarray, cache: Path):
    """Return ``(memmap[N_fp, 36] float32, meta)``; builds once and caches."""
    root, cache = Path(root), Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    ys, xs = np.nonzero(footprint)
    n, f = int(ys.size), len(FEATURES)
    dat, meta_p = cache / "x_lsc36.dat", cache / "x_lsc36.meta.json"
    if dat.exists() and meta_p.exists():
        meta = json.loads(meta_p.read_text())
        if meta.get("schema") == SCHEMA and meta.get("shape") == [n, f]:
            return np.memmap(dat, dtype="float32", mode="r", shape=(n, f)), meta
    mm = np.memmap(dat, dtype="float32", mode="w+", shape=(n, f))
    col = {name: i for i, name in enumerate(FEATURES)}
    fp = footprint

    with rasterio.open(root / "data/external/lidar_scarp_features_u8.tif") as src:
        assert list(src.descriptions) == LIDAR_BANDS, src.descriptions
        lid = {b: src.read(i + 1) for i, b in enumerate(LIDAR_BANDS)}
    for b in LIDAR_BANDS:
        mm[:, col[f"lidar_{b}"]] = lid[b][ys, xs].astype(np.float32)
    step = lid["step_max"].astype(np.float32)
    coh = lid["coh100"].astype(np.float32)
    mm[:, col["step_coh"]] = (step * coh / 255.0)[ys, xs]
    mm[:, col["couplet"]] = np.minimum(lid["lapneg_max"], lid["lappos_max"])[ys, xs].astype(np.float32)
    persist = np.zeros(step.shape, np.float32)
    for k in _line_kernels(5):
        np.maximum(persist, ndi.convolve(step, k, mode="nearest"), out=persist)
    mm[:, col["persist"]] = persist[ys, xs]
    # strike band is a uint8 code; treat it as a circular 0..180 degree axis.
    ang = lid["strike"].astype(np.float32) / 255.0 * np.pi  # 0..pi
    mm[:, col["strike_sin2"]] = np.sin(2 * ang)[ys, xs]
    mm[:, col["strike_cos2"]] = np.cos(2 * ang)[ys, xs]
    del lid, step, coh, persist, ang

    with rasterio.open(root / "data/external/topo_10m_derived_100m_u8.tif") as src:
        assert list(src.descriptions) == TOPO_BANDS, src.descriptions
        for i, b in enumerate(TOPO_BANDS):
            mm[:, col[f"topo_{b}"]] = src.read(i + 1)[ys, xs].astype(np.float32)
    with rasterio.open(root / "data/external/dem10_chi_100m_u8.tif") as src:
        for b, i in CHI_BANDS.items():
            mm[:, col[b]] = src.read(i)[ys, xs].astype(np.float32)
    with rasterio.open(root / "data/training_features.tif") as src:
        nd = src.nodata
        for b, i in ORG_BANDS.items():
            mm[:, col[b]] = _clean(src.read(i), fp, nd)[ys, xs]
    mm.flush()
    meta = {"schema": SCHEMA, "shape": [n, f], "features": list(FEATURES)}
    meta_p.write_text(json.dumps(meta, indent=1))
    return np.memmap(dat, dtype="float32", mode="r", shape=(n, f)), meta
