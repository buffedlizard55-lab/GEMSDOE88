"""Reproduce R0 and run its fixed-count PRUNE<=3 px experiment.

The BFS traversal is the recorded, score-blind H19-5 -> D2.8 operator from
GEMSDOE24 (commit 07345ea0604953d7efb858d9cfbc21e20c7aca0b,
``src/gems/thinning.py``).  It is a deterministic ordering, not a geological
ranking.  No leaderboard, hidden labels, or external service is accessed.
"""
from __future__ import annotations

from collections import deque
import hashlib
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

R0_ZEROS_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
R0_DOTS = 37_654
MIN_DIST_PX = 2.8


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _disc(min_dist: float, width: int) -> list[int]:
    r = int(np.ceil(min_dist))
    lim = min_dist * min_dist
    return [
        dy * width + dx
        for dy in range(-r, r + 1)
        for dx in range(-r, r + 1)
        if dy * dy + dx * dx < lim
    ]


def bfs_order(mask: np.ndarray, min_dist: float = MIN_DIST_PX) -> tuple[np.ndarray, np.ndarray, int]:
    """Return padded mask and the parent's exact FIFO BFS visitation order."""
    mask = np.asarray(mask, bool)
    if mask.ndim != 2:
        raise ValueError("mask must be two-dimensional")
    pad = int(np.ceil(min_dist)) + 1
    padded = np.pad(mask, pad, mode="constant")
    comp, _ = ndi.label(padded, structure=np.ones((3, 3), np.int8))
    flat_comp = comp.ravel()
    nonzero = np.flatnonzero(flat_comp)
    _, first = np.unique(flat_comp[nonzero], return_index=True)
    seeds = nonzero[np.sort(first)]
    present = bytearray(padded.tobytes())
    visited = bytearray(padded.size)
    wp = padded.shape[1]
    neighbours = (-wp - 1, -wp, -wp + 1, -1, 1, wp - 1, wp, wp + 1)
    order: list[int] = []
    for seed in seeds.tolist():
        if visited[seed]:
            continue
        visited[seed] = 1
        queue = deque((seed,))
        while queue:
            q = queue.popleft()
            order.append(q)
            for offset in neighbours:
                nb = q + offset
                if present[nb] and not visited[nb]:
                    visited[nb] = 1
                    queue.append(nb)
    return padded, np.asarray(order, dtype=np.int64), pad


def _unpad(values: bytearray, shape: tuple[int, int], pad: int) -> np.ndarray:
    h, w = shape
    padded = np.frombuffer(bytes(values), dtype=np.uint8).reshape(h + 2 * pad, w + 2 * pad)
    return padded[pad : pad + h, pad : pad + w].astype(bool)


def dot_thin_from_order(
    padded: np.ndarray, order: np.ndarray, pad: int, min_dist: float = MIN_DIST_PX
) -> np.ndarray:
    """Apply the original score-blind D2.8 selection in a supplied BFS order."""
    blocked = bytearray(padded.size)
    kept = bytearray(padded.size)
    disc = _disc(min_dist, padded.shape[1])
    for q in order.tolist():
        if not blocked[q]:
            kept[q] = 1
            for offset in disc:
                blocked[q + offset] = 1
    shape = (padded.shape[0] - 2 * pad, padded.shape[1] - 2 * pad)
    return _unpad(kept, shape, pad)


def refill_padded(
    survivor_padded: np.ndarray,
    eligible_padded: np.ndarray,
    order: np.ndarray,
    pad: int,
    n_add: int,
    min_dist: float | None = None,
) -> np.ndarray:
    """Refill in BFS order; optional inhibition is off for the amended PRUNE design.

    ``eligible_padded`` excludes survivors and BFS visits each pixel once, so
    ``min_dist=None`` still cannot create duplicate dots.  The default is the
    feasibility-amended fixed-count PRUNE rule, not a spacing experiment.
    """
    if survivor_padded.shape != eligible_padded.shape:
        raise ValueError("padded survivor/eligible shape mismatch")
    if n_add < 0:
        raise ValueError("n_add must be non-negative")
    blocked = bytearray(survivor_padded.size)
    disc = _disc(min_dist, survivor_padded.shape[1]) if min_dist is not None else []
    if min_dist is not None:
        for q in np.flatnonzero(survivor_padded).tolist():
            for offset in disc:
                blocked[q + offset] = 1
    eligible_flat = np.asarray(eligible_padded, bool).ravel()
    added = bytearray(survivor_padded.size)
    count = 0
    for q in order.tolist():
        if eligible_flat[q] and not blocked[q]:
            added[q] = 1
            count += 1
            for offset in disc:
                blocked[q + offset] = 1
            if count == n_add:
                break
    if count != n_add:
        raise ValueError(f"only {count} legal refill pixels available; requested {n_add}")
    shape = (survivor_padded.shape[0] - 2 * pad, survivor_padded.shape[1] - 2 * pad)
    return _unpad(added, shape, pad)


def prune3_refill(
    r0: np.ndarray,
    parent_support: np.ndarray,
    d_cat: np.ndarray,
    n_dots: int = R0_DOTS,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Remove R0 dots at d_cat<=3 and refill at fixed count in parent BFS order.

    The pre-scoring feasibility amendment removes additional spacing inhibition;
    nearest-neighbour drift is a measured confounder of this PRUNE-only edit.
    """
    r0 = np.asarray(r0, bool)
    parent_support = np.asarray(parent_support, bool)
    if r0.shape != parent_support.shape or r0.shape != d_cat.shape:
        raise ValueError("R0, support and distance grids must align")
    if int(r0.sum()) != n_dots:
        raise ValueError(f"R0 has {int(r0.sum())} dots, expected {n_dots}")
    survivors = r0 & (d_cat > 3.0)
    removed = r0 & ~survivors
    n_add = int(removed.sum())
    eligible = parent_support & (d_cat > 3.0) & ~survivors
    padded, order, pad = bfs_order(parent_support)
    survivor_padded = np.pad(survivors, pad, mode="constant")
    eligible_padded = np.pad(eligible, pad, mode="constant")
    added = refill_padded(survivor_padded, eligible_padded, order, pad, n_add)
    candidate = survivors | added
    stats = {
        "parent_dots": int(r0.sum()),
        "candidate_dots": int(candidate.sum()),
        "unchanged_dots": int(survivors.sum()),
        "removed_parent_dots": n_add,
        "added_dots": int(added.sum()),
        "pct_parent_dots_changed": float(100.0 * n_add / n_dots),
        "symmetric_difference_dots": int(np.count_nonzero(candidate != r0)),
        "symmetric_difference_pct_of_parent": float(100.0 * np.count_nonzero(candidate != r0) / n_dots),
        "catalogue_distance_rule": "candidate d_cat > 3 px; removed R0 d_cat <= 3 px",
        "refill_rule": "original H19-5 support, d_cat > 3 px, recorded geodesic BFS order, no additional inhibition (pre-scoring feasibility amendment)",
        "spacing_confounder": "refill may reduce nearest-neighbour spacing; measured in parent-diff statistics",
    }
    if int(candidate.sum()) != n_dots or np.any(candidate & ~eligible & ~survivors):
        raise AssertionError("fixed-count/support invariant failed")
    return candidate, removed, added, stats


def parent_profile(template: Path, *, nan_outside: bool) -> dict:
    """The exact R0 serialization profile (not an approximation)."""
    with rasterio.open(template) as src:
        profile = src.profile.copy()
    profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        compress="deflate",
        predictor=3,
        zlevel=9,
        tiled=True,
        blockxsize=256,
        blockysize=256,
        nodata=np.nan if nan_outside else None,
    )
    return profile


def write_mask(path: Path, mask: np.ndarray, footprint: np.ndarray, template: Path, *, nan_outside: bool) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    outside = np.nan if nan_outside else 0.0
    arr = np.where(footprint, mask.astype(np.float32), outside).astype(np.float32)
    with rasterio.open(path, "w", **parent_profile(template, nan_outside=nan_outside)) as dst:
        dst.write(arr, 1)
    return sha256_file(path)


def validate_release_raster(
    path: Path,
    expected_mask: np.ndarray,
    footprint: np.ndarray,
    catalogue: np.ndarray,
    d_cat: np.ndarray,
    sample: Path,
    *,
    nan_outside: bool,
) -> dict:
    """Fail-closed on-disk format, exclusion and scored-content audit."""
    with rasterio.open(sample) as ref, rasterio.open(path) as src:
        arr = src.read(1)
        checks = {
            "geotiff": src.driver == "GTiff",
            "single_band": src.count == 1,
            "dtype_float32": src.dtypes == ("float32",),
            "crs_matches_sample": src.crs is not None and src.crs == ref.crs,
            "shape_matches_sample": src.shape == ref.shape,
            "transform_matches_sample": src.transform == ref.transform,
            "no_nan_inside_footprint": bool(np.isfinite(arr[footprint]).all()),
            "no_inf_anywhere": bool(not np.isinf(arr).any()),
            "values_in_0_1_inside": bool(((arr[footprint] >= 0) & (arr[footprint] <= 1)).all()),
            "binary_inside": bool(np.isin(arr[footprint], [0.0, 1.0]).all()),
            "outside_nan": bool(np.isnan(arr[~footprint]).all()) if nan_outside else True,
            "outside_zero": bool((arr[~footprint] == 0).all()) if not nan_outside else True,
            "nodata_nan": bool(src.nodata is not None and np.isnan(src.nodata)) if nan_outside else True,
            "nodata_none": src.nodata is None if not nan_outside else True,
            "zero_catalogue_mass": bool(not np.any((arr > 0) & catalogue)),
            "all_dots_beyond_3px": bool(np.all(d_cat[arr > 0] > 3.0)),
            "scored_content_exact": bool(np.array_equal(arr > 0.5, expected_mask)),
        }
        n_dots = int(np.count_nonzero(arr[footprint] > 0))
        checks["expected_dot_count"] = n_dots == int(expected_mask.sum())
    result = {
        "file": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "mode": "nan" if nan_outside else "zeros",
        "n_dots": n_dots,
        "checks": checks,
        "ok": all(checks.values()),
        "disk_reread": True,
    }
    if not result["ok"]:
        raise ValueError(f"release validation failed for {path}: {[k for k, v in checks.items() if not v]}")
    return result
