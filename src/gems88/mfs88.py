"""H88-MFS: multifractal gradient-scaling-break channels (zero catalogue).

For each of RTP magnetics (band 2), isostatic gravity (band 13) and detrended
elevation (band 12) of the organizer 19-band stack, compute gradient magnitude
at Gaussian scales sigma in {1, 2, 4} px and summarise the log-log decay by

* ``slope`` = least-squares slope of log G_sigma vs log sigma.  For three
  log-spaced scales (0, ln2, ln4) this is exactly
  ``(1/(2 ln2)) * (log G_4 - log G_1)`` with weight 0.7213475...;
* ``break`` = ``log G_2 - (log G_1 + log G_4)/2`` (scaling curvature: zero for a
  perfect power law, nonzero where the decay changes regime between scales).

Measured on synthetic fields (tests/test_mfs88.py): a step discontinuity has
slope ~ -0.85 (theory -1: the smoothed step's gradient peak decays as 1/sigma
while staying localised on the trace), a smooth ramp or flat field has slope
~ 0, and white noise ~ -1.5.  The pair (slope, break) therefore classifies
*which kind* of edge a large gradient is, which single-scale gradient
amplitudes (bands 3/9/18) cannot.  No catalogue, label or
previous-prediction input is read anywhere in this module.

Preregistration: registry/preregistration_mfs88.json (frozen before compute).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, sobel

SCHEMA = "mfs88-25ch-v1"
SCALES = (1.0, 2.0, 4.0)
# Exact LS slope weight for x = (0, ln2, ln4): w = (x-xbar)/Sxx -> (-c, 0, +c), c = 1/(2 ln2).
SLOPE_W = float(1.0 / (2.0 * np.log(2.0)))
SLOPE_CLIP = (-3.0, 1.0)
BREAK_CLIP = (-2.0, 2.0)
MFS_FIELDS = (("rtp", 2), ("grav", 13), ("topo", 12))  # (name, 1-based band index)
MFS_FEATURES = tuple(
    f"mfs_{name}_{kind}" for name, _ in MFS_FIELDS for kind in ("slope", "break")
)


def clean_band(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Footprint-median fill of non-finite / sentinel cells (repo convention)."""
    out = np.asarray(arr, dtype=np.float32).copy()
    bad = (~np.isfinite(out)) | (np.abs(out) > 1e10)
    good = fp & ~bad
    med = float(np.median(out[good])) if good.any() else 0.0
    out[bad] = med
    out[~fp] = med
    return out


def grad_mag(field: np.ndarray, sigma: float) -> np.ndarray:
    """Sobel gradient magnitude of the Gaussian-smoothed field (repo Sobel/8)."""
    src = gaussian_filter(field, sigma=sigma, mode="nearest") if sigma > 0 else field
    gy = sobel(src, axis=0) * np.float32(0.125)
    gx = sobel(src, axis=1) * np.float32(0.125)
    return np.hypot(gy, gx).astype(np.float32)


def scaling_pair(field: np.ndarray, fp: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (slope, break_) maps from G_1, G_2, G_4 of one cleaned field."""
    g1, g2, g4 = (grad_mag(field, s) for s in SCALES)
    eps = float(np.median(g1[fp]) * 0.01 + 1e-12) if fp.any() else 1e-12
    l1, l2, l4 = (np.log(g + eps) for g in (g1, g2, g4))
    slope = np.clip(SLOPE_W * (l4 - l1), *SLOPE_CLIP).astype(np.float32)
    break_ = np.clip(l2 - 0.5 * (l1 + l4), *BREAK_CLIP).astype(np.float32)
    return slope, break_


def build_or_load(root: Path, fp: np.ndarray, cache: Path):
    """(n_fp, 25) float32 memmap [19 raw bands + 6 MFS channels] + meta dict."""
    cache.mkdir(parents=True, exist_ok=True)
    meta_p = cache / "mfs88_meta.json"
    mmap_p = cache / "mfs88_X_f32.mmap"
    n_fp = int(fp.sum())
    feats19 = []
    with rasterio.open(root / "data/training_features.tif") as ds:
        assert (ds.height, ds.width) == fp.shape and ds.count == 19
        for i in range(1, 20):
            desc = (ds.descriptions[i - 1] or f"band{i}").split(" - ")[0].strip()
            feats19.append(f"b{i:02d}_{desc}")
    names = feats19 + list(MFS_FEATURES)
    meta = {"schema": SCHEMA, "n_valid": n_fp, "names": names}
    if meta_p.exists() and mmap_p.exists():
        old = json.loads(meta_p.read_text())
        if old == meta and mmap_p.stat().st_size == n_fp * len(names) * 4:
            X = np.memmap(mmap_p, dtype=np.float32, mode="r", shape=(n_fp, len(names)))
            return X, meta
    X = np.memmap(mmap_p, dtype=np.float32, mode="w+", shape=(n_fp, len(names)))
    raw = {}
    with rasterio.open(root / "data/training_features.tif") as ds:
        for j in range(19):
            band = clean_band(ds.read(j + 1), fp)
            X[:, j] = band[fp]
            if (j + 1) in {b for _, b in MFS_FIELDS}:
                raw[j + 1] = band
    col = 19
    for _name, band_idx in MFS_FIELDS:
        slope, break_ = scaling_pair(raw.pop(band_idx), fp)
        X[:, col] = slope[fp]
        X[:, col + 1] = break_[fp]
        col += 2
        del slope, break_
    X.flush()
    meta_p.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(mmap_p, dtype=np.float32, mode="r", shape=(n_fp, len(names))), meta
