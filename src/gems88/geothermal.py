"""GEO-THERMAL-88 surface builder: measured geothermal water temperature x young-scarp corridor.

Positions dots from DOE GDR INGENIOUS hot well/spring locations (measured water
temperature, CC BY 4.0) gated to USGS 3DEP lidar-derived young fault-scarp
amplitude and thin sedimentary cover.  Measured hydrothermal temperature is a
direct geothermal indicator -- not a fault proxy -- so this lane targets blind
geothermal systems that can spring/scarp without a mapped Quaternary fault trace
in the USGS/INGENIOUS catalogue.

No catalogue pixels are used to build the surface; the catalogue is used ONLY
for pixel-exact exclusion of the final dots (never a ranking feature).
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

RADIUS_PX = 3.0          # 300 m triangular kernel radius, matches the DTI kernel
DOT_MIN_SPACING_PX = 3.0  # dots spaced ~one kernel radius apart (H33 geometry)


def read_hot_springs(csv_path: Path, footprint: np.ndarray,
                     temp_min_c: float = 45.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (rows, cols, temp_weights) for Hot geothermal wells/springs inside the footprint.

    `thermalclass` values include 'Hot', 'Hot ', 'Warm', 'Cold', 'Unknown', NULL, ''.
    We keep rows whose thermalclass starts with 'Hot' (case-insensitive, trimmed) and
    whose measured temp_c >= temp_min_c, deduplicating to one record per pixel cell.
    Weight = temp_c (hotter = stronger geothermal prior).
    """
    rows, cols, temps = [], [], []
    seen = set()
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for rec in reader:
            cls = (rec.get('thermalclass') or '').strip()
            if not cls.lower().startswith('hot'):
                continue
            t = (rec.get('temp_c') or '').strip()
            if not t:
                continue
            try:
                temp = float(t)
            except ValueError:
                continue
            if temp < temp_min_c:
                continue
            try:
                row = int(float(rec['row'])); col = int(float(rec['col']))
            except (ValueError, KeyError, TypeError):
                continue
            if 0 <= row < footprint.shape[0] and 0 <= col < footprint.shape[1] and footprint[row, col]:
                key = (row, col)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row); cols.append(col); temps.append(temp)
    if not rows:
        raise ValueError('no hot geothermal wells/springs found inside footprint')
    return (np.asarray(rows, np.int32), np.asarray(cols, np.int32),
            np.asarray(temps, np.float64))


def gaussian_kernel(size_px: float, sigma_px: float) -> np.ndarray:
    """Normalized 2D Gaussian kernel, size = ceil(3*sigma) each side."""
    r = int(math.ceil(3.0 * sigma_px))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = np.exp(-(xx * xx + yy * yy) / (2.0 * sigma_px * sigma_px))
    k /= k.sum()
    return k


def build_surface(hot_rows: np.ndarray, hot_cols: np.ndarray, hot_temps: np.ndarray,
                  shape: tuple[int, int], scarp: np.ndarray | None = None,
                  scarp_gate_quantile: float = 0.70,
                  cover: np.ndarray | None = None) -> tuple[np.ndarray, dict]:
    """Build the GEO-THERMAL-88 favorability surface.

    Parameters
    ----------
    hot_rows, hot_cols, hot_temps : pixel coordinates and measured temperatures of
        hot geothermal wells/springs (deduplicated, footprint-filtered).
    shape : (height, width) of the competition grid.
    scarp : lidar scarp amplitude band (uint8).  If given, dots are gated to cells
        above the `scarp_gate_quantile` of positive scarp values (young-scarp corridors).
    cover : depth-to-basement surface (lower = thinner cover = more geothermal).  If
        given, cells with thinner cover are up-weighted.
    """
    H, W = shape
    surface = np.zeros(shape, np.float64)

    # Temp-weighted Gaussian kernel density of hot wells/springs (sigma ~ kernel radius).
    k = gaussian_kernel(RADIUS_PX, RADIUS_PX / 2.0)
    r = k.shape[0] // 2
    for row, col, temp in zip(hot_rows, hot_cols, hot_temps):
        r0, r1 = max(0, row - r), min(H, row + r + 1)
        c0, c1 = max(0, col - r), min(W, col + r + 1)
        kr0, kr1 = r - (row - r0), r - (row - r1) + (r1 - r0)  # noqa: F841
        # slice kernel to match array window
        ksr0 = r - (row - r0); ksr1 = ksr0 + (r1 - r0)
        ksc0 = r - (col - c0); ksc1 = ksc0 + (c1 - c0)
        surface[r0:r1, c0:c1] += temp * k[ksr0:ksr1, ksc0:ksc1]

    if not np.isfinite(surface).all() or surface.max() <= 0:
        raise ValueError('degenerate geothermal surface')
    surface /= surface.max()  # normalize to [0, 1]

    stats = {'hot_locations': int(len(hot_rows)),
             'mean_temp_c': float(hot_temps.mean()),
             'max_temp_c': float(hot_temps.max()),
             'surface_max': float(surface.max()),
             'surface_mean': float(surface[surface > 0].mean()) if (surface > 0).any() else 0.0}

    # Gate to young-scarp corridors: keep only cells above the scarp quantile.
    scarp_mask = np.ones(shape, bool)
    if scarp is not None:
        pos = scarp[(scarp > 0) & np.isfinite(scarp)]
        if pos.size:
            thr = float(np.quantile(pos, scarp_gate_quantile))
            scarp_mask = scarp >= thr
            stats['scarp_gate_threshold'] = thr
            stats['scarp_gated_cells'] = int(scarp_mask.sum())
        surface = np.where(scarp_mask, surface, 0.0)

    # Thin-cover favorability: shallower basement = more geothermal.
    if cover is not None:
        finite = cover[np.isfinite(cover)]
        if finite.size:
            # Invert: low depth -> high favorability.  Use (p10 - depth) clipped.
            p10 = float(np.quantile(finite, 0.10))
            fav = np.clip((p10 - cover) / (p10 - float(np.quantile(finite, 0.90)) + 1e-6), 0.0, 1.0)
            fav[~np.isfinite(cover)] = 0.0
            surface = surface * fav
            stats['cover_favorability_applied'] = True

    if not np.isfinite(surface).all() or surface.max() <= 0:
        raise ValueError('degenerate geothermal surface after gating')
    surface /= surface.max()
    stats['final_surface_max'] = float(surface.max())
    stats['final_surface_mean_pos'] = float(surface[surface > 0].mean()) if (surface > 0).any() else 0.0
    return surface, stats


def spaced_dots(surface: np.ndarray, eligible: np.ndarray,
                max_dots: int, min_spacing_px: float = DOT_MIN_SPACING_PX) -> np.ndarray:
    """Greedy farthest-point selection: highest surface first, min pairwise spacing.

    Returns a boolean mask of chosen dot cells.  Deterministic (stable sort by
    descending surface value, ties broken by row-major order).  Chosen dots are
    separated by at least `min_spacing_px`; every other cell is barred.
    """
    if max_dots <= 0:
        return np.zeros(surface.shape, bool)
    order = np.lexsort((np.arange(surface.size), -surface.ravel()))
    eligible_flat = eligible.ravel()
    taken = np.zeros(surface.size, bool)   # actual chosen dots
    barred = np.zeros(surface.size, bool)  # taken dots + their neighbourhoods
    n_chosen = 0
    r = int(math.ceil(min_spacing_px))
    H, W = surface.shape
    for idx in order:
        if n_chosen >= max_dots:
            break
        if not eligible_flat[idx] or barred[idx]:
            continue
        cy, cx = divmod(int(idx), W)
        taken[idx] = True
        barred[idx] = True
        n_chosen += 1
        y0, y1 = max(0, cy - r), min(H, cy + r + 1)
        x0, x1 = max(0, cx - r), min(W, cx + r + 1)
        sub = barred[y0:y1, x0:x1].ravel()
        yy = np.arange(y0, y1)[:, None]
        xx = np.arange(x0, x1)[None, :]
        near = ((yy - cy) ** 2 + (xx - cx) ** 2) <= min_spacing_px * min_spacing_px
        barred[y0:y1, x0:x1] = np.where(near, True, barred[y0:y1, x0:x1])
        # re-assert the chosen cell as taken (it is also barred, fine)
        taken[idx] = True
    mask = taken.reshape(H, W)
    return mask
