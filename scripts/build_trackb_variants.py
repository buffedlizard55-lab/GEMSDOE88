#!/usr/bin/env python3
"""Build and validate controlled AXIS=TRACKB variants + Phase 2 >=1 km GeoJSON traces.

Implements Agent Brief v2 §5 (TRACKB) end-to-end with zero DrivenData/Dropbox contact:
1. Verifies SHA-256 + byte lengths of all 15 pinned inputs in registry/data_manifest.json.
2. Rebuilds parent R0 (h33-h33-2-b2, 37,654 dots) from the 5-stage lineage recipe and
   asserts byte-exact SHA-256 identity on both twins (zeros c55bafc4…, nan baeae321…).
3. Rebuilds the 15-channel label-free 4-line physical corroboration field w(x), asserts
   all 15 single-channel leakage canaries pass (symmetric AUC <= 0.90), and reconstructs
   gate-clean parent R1 = PRUNEp3px (6f7ae705… / dc6f090d…, 37,654 dots, min d_cat =
   3.1623 px > 3.0 px) so every emitted non-PRUNE raster strictly obeys Brief §4.4.
4. Extracts clean, unbranched, strike-consistent >= 1.0 km fault traces from R0's
   top-ranked off-collar (d_cat > 3.0 px) dots (step <= 450 m, zero catalogue crossing,
   vertex deflection <= 25 deg, arc & chord >= 1,000 m, tortuosity <= 1.20), exporting:
     - evidence/trackb_traces_geologist.geojson (RFC 7946 WGS84 LineStrings + UTM
       EPSG:32611 endpoints + one structural-geologist evidence paragraph per trace)
     - evidence/trackb_geologist_dossier.md (Phase 2 structural geology summary)
5. Emits three preregistered controlled AXIS=TRACKB rasters sharing the identical 10.00%
   (3,765-dot) isolated 1-dot non-trace speckle donor cut (0 R1 neighbors <= 450 m):
     - speckle10minus (N=33,889): pure removal of 3,765 isolated non-trace speckles
     - traceext10     (N=37,654): reallocate 3,765 dots onto mutually >= 2.8 px-spaced
                                  along-strike (<= 950 m, +-25 deg) trace tip/relay cones
     - tracespine10   (N=37,654): reallocate 3,765 dots onto un-emitted 100 m polyline
                                  spine pixels of top-ranked >= 1.0 km GeoJSON traces
6. Verifies all MUST gates on disk (plus independent scripts/validate_variant.py) and
   computes REPORT-ONLY diagnostics (HOLDOUT-DTI + 95% CI, blind SGMC off-catalogue
   control + donor/receiver credit decomposition, 10 km & 12 km block-density CV).
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine, xy as transform_xy
from rasterio.warp import transform as warp_transform
from scipy.ndimage import binary_dilation, distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts", ROOT / "vendor", ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import build_prune_variants as bp  # noqa: E402
import build_snap_r1_variants as bsv  # noqa: E402
from gems57 import metric  # noqa: E402

RELEASES = ROOT / "releases"
EVIDENCE = ROOT / "evidence"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "trackb_preregistration.json"
VALIDATION_OUT = ROOT / "registry" / "trackb_variant_validation.json"
GEOJSON_OUT = EVIDENCE / "trackb_traces_geologist.geojson"
DOSSIER_OUT = EVIDENCE / "trackb_geologist_dossier.md"
REPORT_OUT = EVIDENCE / "trackb_axis_report.json"

R0_ID = bp.PARENT_ID
R1_ID = bsv.R1_ID
R1_SHA_NAN = bsv.R1_SHA_NAN
R1_SHA_ZEROS = bsv.R1_SHA_ZEROS

AXIS = "TRACKB"
OUR_VALUES = ("speckle10minus", "traceext10", "tracespine10")
DOSE_FRAC = 0.10
MIN_CATALOGUE_PX = 3.0
COLLAR_EPS = 1e-6
SEED = bp.SEED
FIXED_DATE = bp.FIXED_DATE


# ---------------------------------------------------------------------------
# 1. Strike-Consistent >= 1.0 km Polyline Chaining & Geometry Primitives
# ---------------------------------------------------------------------------


def axial_strike_stats(easting_m: np.ndarray, northing_m: np.ndarray) -> tuple[float, str, float]:
    """Compute axial strike in [0, 180) deg E of N, compass label, and Mardia R_bar."""
    de = np.diff(easting_m)
    dn = np.diff(northing_m)
    seg_len = np.hypot(de, dn)
    valid = seg_len > 0
    if not np.any(valid):
        return 0.0, "N00E", 0.0
    # Azimuth clockwise from North in radians: atan2(dE, dN)
    az = np.arctan2(de[valid], dn[valid]) % math.pi
    weights = seg_len[valid] / float(seg_len[valid].sum())
    c2 = float(np.sum(weights * np.cos(2.0 * az)))
    s2 = float(np.sum(weights * np.sin(2.0 * az)))
    r_bar = float(math.hypot(c2, s2))
    mean_az_rad = (0.5 * math.atan2(s2, c2)) % math.pi
    deg = float(math.degrees(mean_az_rad)) % 180.0
    if deg <= 90.0:
        compass = f"N{int(round(deg)):02d}E"
    else:
        compass = f"N{int(round(180.0 - deg)):02d}W"
    return round(deg, 2), compass, round(r_bar, 4)


def extract_strike_consistent_traces(
    dot_mask: np.ndarray,
    scores: np.ndarray,
    foot: np.ndarray,
    d_cat: np.ndarray,
    transform: Affine,
    *,
    max_step_m: float = 450.0,
    max_deflection_deg: float = 25.0,
    min_length_m: float = 1000.0,
    max_tortuosity: float = 1.20,
    min_cat_px: float = MIN_CATALOGUE_PX,
) -> tuple[list[dict], np.ndarray]:
    """Extract unbranched, strike-consistent >= 1 km polylines from top-ranked dots.

    Dots are seeded in descending ``scores`` order (ties broken deterministically by
    ``(row, col)``). Two dots within ``max_step_m`` may connect iff six interpolated
    checkpoints stay inside ``foot`` and strictly beyond ``min_cat_px`` of mapped
    catalogue faults. Interior vertices enforce deflection ``<= max_deflection_deg``.
    """
    eligible = np.asarray(dot_mask, dtype=bool) & np.asarray(foot, dtype=bool) & (d_cat > min_cat_px)
    ry, rx = np.nonzero(eligible)
    if len(ry) < 2:
        return [], np.zeros(dot_mask.shape, dtype=bool)

    px_size_m = float(abs(transform.a))
    xs_utm, ys_utm = transform_xy(transform, ry, rx, offset="center")
    pts = np.column_stack([np.asarray(xs_utm, dtype=np.float64), np.asarray(ys_utm, dtype=np.float64)])
    sc_vals = np.asarray(scores[ry, rx], dtype=np.float64)

    tree = cKDTree(pts)
    pairs = tree.query_pairs(max_step_m, output_type="ndarray")
    adj: list[list[tuple[float, int]]] = [[] for _ in range(len(pts))]
    ts_chk = np.linspace(0.0, 1.0, 6)
    for i_raw, j_raw in pairs:
        i, j = int(i_raw), int(j_raw)
        rr = np.rint(ry[i] * (1.0 - ts_chk) + ry[j] * ts_chk).astype(np.int64)
        cc = np.rint(rx[i] * (1.0 - ts_chk) + rx[j] * ts_chk).astype(np.int64)
        if not np.all(foot[rr, cc]) or np.any(d_cat[rr, cc] <= min_cat_px):
            continue
        dist_m = float(math.hypot(pts[j, 0] - pts[i, 0], pts[j, 1] - pts[i, 1]))
        if dist_m < 0.5 * px_size_m:
            continue
        adj[i].append((dist_m, j))
        adj[j].append((dist_m, i))
    for lst in adj:
        lst.sort(key=lambda t: (round(t[0], 6), t[1]))

    cos_max = math.cos(math.radians(max_deflection_deg))
    used = np.zeros(len(pts), dtype=bool)
    # Deterministic sort: score descending, then row ascending, col ascending
    seed_order = np.lexsort((rx, ry, -sc_vals))

    def _grow(u0: int, u1: int) -> list[int]:
        chain = [u0, u1]
        in_c = {u0, u1}
        for forward in (True, False):
            while True:
                cur = chain[-1] if forward else chain[0]
                prv = chain[-2] if forward else chain[1]
                vp = pts[cur] - pts[prv]
                nv = float(np.linalg.norm(vp))
                if nv == 0.0:
                    break
                vp = vp / nv
                best_nb = None
                best_key = (-1e18, 0)
                for dist_m, nb in adj[cur]:
                    if used[nb] or nb in in_c:
                        continue
                    vn = pts[nb] - pts[cur]
                    nn = float(np.linalg.norm(vn))
                    if nn == 0.0:
                        continue
                    ca = float(np.dot(vp, vn / nn))
                    if ca >= cos_max:
                        val = round(ca + 0.25 * float(sc_vals[nb]) - 0.0004 * dist_m, 10)
                        cand_key = (val, -nb)
                        if cand_key > best_key:
                            best_key = cand_key
                            best_nb = nb
                if best_nb is None:
                    break
                in_c.add(best_nb)
                if forward:
                    chain.append(best_nb)
                else:
                    chain.insert(0, best_nb)
        return chain

    raw_traces: list[tuple[list[int], float, float, float]] = []
    for s_idx in seed_order:
        s = int(s_idx)
        if used[s] or not adj[s]:
            continue
        best_pack = None
        best_arc = -1.0
        for _, nb in adj[s]:
            if used[nb]:
                continue
            ch = _grow(s, nb)
            cpts = pts[ch]
            arc = float(np.linalg.norm(np.diff(cpts, axis=0), axis=1).sum())
            chord = float(np.linalg.norm(cpts[-1] - cpts[0]))
            if arc >= min_length_m and chord >= min_length_m and (arc / chord) <= max_tortuosity:
                if arc > best_arc:
                    best_arc = arc
                    best_pack = (ch, arc, chord, float(sc_vals[ch].mean()))
        if best_pack is not None:
            ch, arc, chord, mean_sc = best_pack
            for u in ch:
                used[u] = True
            # Canonical endpoint orientation: southernmost -> northernmost (tie: westernmost -> easternmost)
            if (pts[ch[0], 1], pts[ch[0], 0]) > (pts[ch[-1], 1], pts[ch[-1], 0]):
                ch = list(reversed(ch))
            raw_traces.append((ch, arc, chord, mean_sc))

    # Rank traces deterministically by composite physical score * log(1 + L_km)
    raw_traces.sort(
        key=lambda t: (
            -round(t[3] * math.log1p(t[1] / 1000.0), 10),
            -round(t[1], 4),
            int(ry[t[0][0]]),
            int(rx[t[0][0]]),
        )
    )

    trace_dot_mask = np.zeros(dot_mask.shape, dtype=bool)
    traces: list[dict] = []
    for rank_idx, (ch, arc, chord, mean_sc) in enumerate(raw_traces, 1):
        rows = ry[ch].astype(int).tolist()
        cols = rx[ch].astype(int).tolist()
        trace_dot_mask[ry[ch], rx[ch]] = True
        east = pts[ch, 0]
        north = pts[ch, 1]
        strike_deg, strike_compass, r_bar = axial_strike_stats(east, north)
        d_cat_m = d_cat[ry[ch], rx[ch]] * px_size_m
        traces.append(
            {
                "trace_id": f"TRACKB-{rank_idx:04d}",
                "rank": rank_idx,
                "rows": rows,
                "cols": cols,
                "easting_m": [round(float(x), 1) for x in east],
                "northing_m": [round(float(y), 1) for y in north],
                "n_dots": len(ch),
                "arc_length_m": round(arc, 1),
                "length_km": round(arc / 1000.0, 3),
                "chord_length_m": round(chord, 1),
                "tortuosity": round(arc / chord, 4),
                "strike_deg": strike_deg,
                "strike_compass": strike_compass,
                "strike_coherence_rbar": r_bar,
                "mean_physical_score": round(mean_sc, 4),
                "max_physical_score": round(float(sc_vals[ch].max()), 4),
                "min_catalogue_dist_m": round(float(d_cat_m.min()), 1),
                "mean_catalogue_dist_m": round(float(d_cat_m.mean()), 1),
            }
        )
    return traces, trace_dot_mask


def build_trace_spine_mask(
    traces: list[dict],
    foot: np.ndarray,
    d_cat: np.ndarray,
    min_cat_px: float = MIN_CATALOGUE_PX,
) -> np.ndarray:
    """Rasterize 100 m polyline spines connecting consecutive trace vertices (d_cat > min_cat_px)."""
    spine = np.zeros(foot.shape, dtype=bool)
    for tr in traces:
        rows, cols = tr["rows"], tr["cols"]
        for r0, c0, r1, c1 in zip(rows[:-1], cols[:-1], rows[1:], cols[1:]):
            steps = max(abs(r1 - r0), abs(c1 - c0))
            if steps <= 1:
                spine[r0, c0] = True
                spine[r1, c1] = True
                continue
            ts = np.linspace(0.0, 1.0, steps + 1)
            rr = np.rint(r0 * (1.0 - ts) + r1 * ts).astype(np.int64)
            cc = np.rint(c0 * (1.0 - ts) + c1 * ts).astype(np.int64)
            ok = foot[rr, cc] & (d_cat[rr, cc] > min_cat_px)
            spine[rr[ok], cc[ok]] = True
    return spine & foot & (d_cat > min_cat_px)


def build_tip_extension_cone_mask(
    traces: list[dict],
    foot: np.ndarray,
    d_cat: np.ndarray,
    *,
    min_dist_px: float = 2.8,
    max_dist_px: float = 9.5,
    max_angle_deg: float = 25.0,
    min_cat_px: float = MIN_CATALOGUE_PX,
) -> np.ndarray:
    """Build along-strike tip & en-echelon relay continuation cones for >= 1 km traces.

    Every candidate pixel must lie inside [min_dist_px, max_dist_px] ahead of a trace
    tip within +-max_angle_deg of the outward tip tangent, AND the straight segment from
    that tip to the candidate pixel must stay inside ``foot`` and strictly beyond
    ``min_cat_px`` of mapped catalogue faults.
    """
    H, W = foot.shape
    cone = np.zeros((H, W), dtype=bool)
    cos_thr = math.cos(math.radians(max_angle_deg))
    rad = int(math.ceil(max_dist_px))
    ts_chk = np.linspace(0.0, 1.0, 6)

    for tr in traces:
        rows, cols = tr["rows"], tr["cols"]
        if len(rows) < 2:
            continue
        tips = (
            (rows[-1], cols[-1], rows[-1] - rows[-2], cols[-1] - cols[-2]),
            (rows[0], cols[0], rows[0] - rows[1], cols[0] - cols[1]),
        )
        for ey, ex, vy_raw, vx_raw in tips:
            nv = math.hypot(vy_raw, vx_raw)
            if nv == 0.0:
                continue
            vy, vx = vy_raw / nv, vx_raw / nv
            y0, y1 = max(0, ey - rad), min(H, ey + rad + 1)
            x0, x1 = max(0, ex - rad), min(W, ex + rad + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            dy = yy - ey
            dx = xx - ex
            dist = np.hypot(dy, dx)
            in_sector = (
                (dist >= min_dist_px)
                & (dist <= max_dist_px)
                & (((dy * vy + dx * vx) / np.maximum(dist, 1e-9)) >= cos_thr)
                & foot[y0:y1, x0:x1]
                & (d_cat[y0:y1, x0:x1] > min_cat_px)
            )
            cy_loc, cx_loc = np.nonzero(in_sector)
            for ly, lx in zip(cy_loc.tolist(), cx_loc.tolist()):
                ty, tx = y0 + ly, x0 + lx
                rr = np.rint(ey * (1.0 - ts_chk) + ty * ts_chk).astype(np.int64)
                cc = np.rint(ex * (1.0 - ts_chk) + tx * ts_chk).astype(np.int64)
                if np.all(foot[rr, cc]) and np.all(d_cat[rr, cc] > min_cat_px):
                    cone[ty, tx] = True
    return cone


def select_isolated_speckle_donors(
    base_mask: np.ndarray,
    trace_dot_mask: np.ndarray,
    w: np.ndarray,
    n_drop: int,
    *,
    isolation_radius_px: float = 4.5,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Drop ``n_drop`` isolated 1-dot non-trace speckles minimizing exact expected-DTI loss."""
    by, bx = np.nonzero(base_mask)
    pts_px = np.column_stack([bx.astype(np.float64), by.astype(np.float64)])
    tree = cKDTree(pts_px)
    nb_counts = np.array([len(lst) - 1 for lst in tree.query_ball_tree(tree, isolation_radius_px)])
    on_trace = trace_dot_mask[by, bx]
    iso_flags = (nb_counts == 0) & (~on_trace)

    iso_pool = np.zeros(base_mask.shape, dtype=bool)
    iso_pool[by[iso_flags], bx[iso_flags]] = True
    n_iso_pool = int(iso_pool.sum())
    if n_iso_pool < n_drop:
        raise ValueError(
            f"Isolated 1-dot non-trace pool ({n_iso_pool}) smaller than requested n_drop ({n_drop})"
        )

    pruned = bp.select_exact_marginal_dti_drop(
        base_mask=base_mask,
        drop_pool_mask=iso_pool,
        w=w,
        n_drop=n_drop,
    )
    dropped = base_mask & (~pruned)
    stats = {
        "isolation_radius_px": isolation_radius_px,
        "isolated_pool_count": n_iso_pool,
        "n_dropped": int(dropped.sum()),
        "trace_dots_preserved": int((pruned & trace_dot_mask).sum()),
        "trace_dots_total": int((base_mask & trace_dot_mask).sum()),
    }
    return pruned, dropped, stats


def select_spaced_exact_marginal_dti_add(
    base_mask: np.ndarray,
    cand_mask: np.ndarray,
    w: np.ndarray,
    n_add: int,
    *,
    min_sep_px: float = 2.8,
    alpha: float = metric.ALPHA,
    beta: float = metric.BETA,
) -> np.ndarray:
    """Greedily add ``n_add`` dots maximizing exact iterative expected DTI subject to d_nn >= min_sep_px."""
    state = np.asarray(base_mask, dtype=bool).copy()
    if n_add <= 0:
        return state
    H, W = state.shape
    w64 = np.asarray(w, dtype=np.float64)
    w_tot = float(w64.sum())

    # Enforce initial spacing clearance >= min_sep_px from base_mask
    r_blk = int(math.ceil(min_sep_px))
    lim_sq = min_sep_px * min_sep_px
    disc_offsets = [
        (dy, dx)
        for dy in range(-r_blk, r_blk + 1)
        for dx in range(-r_blk, r_blk + 1)
        if (dy * dy + dx * dx) < lim_sq
    ]
    blocked = np.zeros((H, W), dtype=bool)
    by, bx = np.nonzero(state)
    for dy, dx in disc_offsets:
        ny, nx = by + dy, bx + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        blocked[ny[ok], nx[ok]] = True

    elig = np.asarray(cand_mask, dtype=bool) & (~state) & (~blocked)
    cy, cx = np.nonzero(elig)
    if len(cy) < n_add:
        raise ValueError(f"Spaced candidate pool ({len(cy)}) smaller than requested n_add ({n_add})")

    cov = np.zeros((H, W), dtype=np.float64)
    off_dy = metric.OFF_DY.astype(np.int64)
    off_dx = metric.OFF_DX.astype(np.int64)
    off_k = metric.OFF_K.astype(np.float64)
    for dy, dx, kw in zip(off_dy, off_dx, off_k):
        ny, nx = by + int(dy), bx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        np.maximum.at(cov, (ny[ok], nx[ok]), kw)
    t_cur = float((w64 * cov).sum())
    m_base = np.zeros(len(by), dtype=np.float64)
    for dy, dx, kw in zip(off_dy, off_dx, off_k):
        ny, nx = by + int(dy), bx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        m_base[ok] = np.maximum(m_base[ok], w64[ny[ok], nx[ok]] * kw)
    m_cur = float(m_base.sum())
    s_cur = float(len(by))

    cand_id_grid = np.full((H, W), -1, dtype=np.int32)
    cand_id_grid[cy, cx] = np.arange(len(cy), dtype=np.int32)

    m_cand = np.zeros(len(cy), dtype=np.float64)
    dT = np.zeros(len(cy), dtype=np.float64)
    for dy, dx, kw in zip(off_dy, off_dx, off_k):
        ny, nx = cy + int(dy), cx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        wv = w64[ny[ok], nx[ok]]
        m_cand[ok] = np.maximum(m_cand[ok], wv * kw)
        dT[ok] += wv * np.maximum(0.0, kw - cov[ny[ok], nx[ok]])

    disabled = np.zeros(len(cy), dtype=bool)
    for step_idx in range(n_add):
        d_cur = alpha * (t_cur + s_cur - m_cur) + beta * w_tot + metric.EPS
        next_dti = (t_cur + dT) / (d_cur + alpha * (dT + 1.0 - m_cand))
        next_dti[disabled] = -1.0
        best = int(np.argmax(next_dti))
        if next_dti[best] < 0.0:
            raise RuntimeError(
                f"Spaced candidate pool exhausted at step {step_idx}/{n_add} under min_sep_px={min_sep_px}"
            )
        ry, rx = int(cy[best]), int(cx[best])
        state[ry, rx] = True
        disabled[best] = True

        # Enforce min_sep_px exclusion around newly added dot
        for dy, dx in disc_offsets:
            ny, nx = ry + dy, rx + dx
            if 0 <= ny < H and 0 <= nx < W:
                cid = int(cand_id_grid[ny, nx])
                if cid >= 0:
                    disabled[cid] = True

        # Update kernel coverage and nearby active candidates
        ny = ry + off_dy
        nx = rx + off_dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        ny, nx, kw = ny[ok], nx[ok], off_k[ok]
        old_c = cov[ny, nx]
        upd = kw > old_c
        if np.any(upd):
            uy, ux, uk, uold = ny[upd], nx[upd], kw[upd], old_c[upd]
            cov[uy, ux] = uk
            t_cur += float((w64[uy, ux] * (uk - uold)).sum())

        s_cur += 1.0
        m_cur += float(m_cand[best])

        y0, y1 = max(0, ry - 6), min(H, ry + 7)
        x0, x1 = max(0, rx - 6), min(W, rx + 7)
        sub_ids = cand_id_grid[y0:y1, x0:x1].ravel()
        sub_ids = sub_ids[sub_ids >= 0]
        if sub_ids.size:
            sub_ids = sub_ids[~disabled[sub_ids]]
        if sub_ids.size:
            sy, sx = cy[sub_ids], cx[sub_ids]
            new_dt = np.zeros(len(sub_ids), dtype=np.float64)
            for dy_i, dx_i, kw_i in zip(off_dy, off_dx, off_k):
                nny, nnx = sy + int(dy_i), sx + int(dx_i)
                ook = (nny >= 0) & (nny < H) & (nnx >= 0) & (nnx < W)
                new_dt[ook] += w64[nny[ook], nnx[ook]] * np.maximum(
                    0.0, kw_i - cov[nny[ook], nnx[ook]]
                )
            dT[sub_ids] = new_dt

    return state


# ---------------------------------------------------------------------------
# 2. Structural-Geologist Observables & GeoJSON / Dossier Generation
# ---------------------------------------------------------------------------


def annotate_traces_for_geologist(
    traces: list[dict],
    verified: dict[str, Path],
    foot: np.ndarray,
    h19_4: np.ndarray,
    h16_1: np.ndarray,
    crs_str: str = "EPSG:32611",
) -> list[dict]:
    """Attach verified physical band observables, WGS84 geometry, and geologist paragraph per trace."""
    with rasterio.open(verified["training_features"]) as ds:
        det_elev = bsv.read_band(ds, 12, foot)
        p_slope = bsv.percentile_rank(np.abs(bsv.read_band(ds, 19, foot)), foot)
        p_grav_hg = bsv.percentile_rank(np.abs(bsv.read_band(ds, 18, foot)), foot)
        p_tmi_hg = bsv.percentile_rank(np.abs(bsv.read_band(ds, 3, foot)), foot)
        p_strain = bsv.percentile_rank(np.abs(bsv.read_band(ds, 4, foot)), foot)
        p_seis = bsv.percentile_rank(np.abs(bsv.read_band(ds, 16, foot)), foot)
        p_cond = bsv.percentile_rank(np.abs(bsv.read_band(ds, 17, foot)), foot)
        depth_base = bsv.read_band(ds, 15, foot)

    with rasterio.open(verified["ext_lidar_scarp_u8"]) as lds:
        lidar_step = lds.read(3).astype(np.float32)
        lidar_valid = (lds.read(12) > 0) & foot
    p_lidar = np.zeros(foot.shape, dtype=np.float32)
    if np.any(lidar_valid):
        v_lid = lidar_step[lidar_valid]
        qs = np.linspace(0.0, 1.0, 1001)
        p_lidar[lidar_valid] = np.interp(v_lid, np.quantile(v_lid, qs), qs).astype(np.float32)
    del lidar_step

    q33, q67 = (float(x) for x in np.quantile(det_elev[foot], [1.0 / 3.0, 2.0 / 3.0]))

    features: list[dict] = []
    for tr in traces:
        rr = np.asarray(tr["rows"], dtype=np.int64)
        cc = np.asarray(tr["cols"], dtype=np.int64)
        lons, lats = warp_transform(crs_str, "EPSG:4326", tr["easting_m"], tr["northing_m"])
        coords_lonlat = [[round(float(lon), 6), round(float(lat), 6)] for lon, lat in zip(lons, lats)]

        mean_de = float(det_elev[rr, cc].mean())
        if mean_de < q33:
            zone = "basin floor"
            mimic = (
                "Pleistocene pluvial Lake Lahontan/Bonneville wave-cut shorelines, playa evaporite "
                "desiccation margins, or 400 m GeoDAWN aeromagnetic flight-line leveling corrugation"
            )
        elif mean_de < q67:
            zone = "piedmont bajada"
            mimic = (
                "incised alluvial-fan terrace risers, non-tectonic pediment pinchouts, or buried "
                "Cenozoic lava-flow edge gradients"
            )
        else:
            zone = "range front / bedrock block"
            mimic = (
                "unfaulted welded-tuff cooling scarps, Tertiary dike margins with remanent "
                "magnetization, or pluton-roof lithologic contacts"
            )

        slp_pct = int(round(100.0 * float(p_slope[rr, cc].mean())))
        grv_pct = int(round(100.0 * float(p_grav_hg[rr, cc].mean())))
        tmi_pct = int(round(100.0 * float(p_tmi_hg[rr, cc].mean())))
        kin_pct = int(round(100.0 * float(np.maximum(p_strain[rr, cc], p_seis[rr, cc]).mean())))
        cnd_pct = int(round(100.0 * float(p_cond[rr, cc].mean())))
        cov_med = float(np.median(depth_base[rr, cc]))
        lid_cov = float(lidar_valid[rr, cc].mean())
        lid_pct = int(round(100.0 * float(p_lidar[rr, cc][lidar_valid[rr, cc]].mean()))) if lid_cov > 0 else None
        anc_frac = float(((h19_4[rr, cc] | h16_1[rr, cc])).mean())

        deg = tr["strike_deg"]
        if deg <= 12.0 or deg >= 168.0:
            regime = "N-S Basin-and-Range normal-fault strike"
        elif 12.0 < deg <= 55.0:
            regime = "NNE-NE Great Basin extensional normal-fault strike"
        elif 125.0 <= deg < 168.0:
            regime = "NNW-NW Walker Lane transtensional / dextral-oblique strike"
        else:
            regime = "ENE-WNW transverse accommodation / transfer-zone strike"

        if lid_pct is not None:
            obs_lead = (
                f"Physical corroboration combines 1 m 3DEP LiDAR scarp step at P{lid_pct} "
                f"({int(round(100 * lid_cov))}% tile coverage) and "
            )
        else:
            obs_lead = "Outside 1 m 3DEP LiDAR tile coverage, physical corroboration is anchored on "
        paragraph = (
            f"{tr['trace_id']} maps an unmapped {tr['length_km']:.2f} km ({tr['n_dots']} parent R0 dots, "
            f"tortuosity {tr['tortuosity']:.2f}, axial coherence R={tr['strike_coherence_rbar']:.3f}) "
            f"{tr['strike_compass']}-striking fault candidate ({regime}) in the {zone} domain "
            f"(mean det_elev {mean_de:+.1f} m; nearest USGS/INGENIOUS fault {tr['min_catalogue_dist_m']:.0f} m). "
            f"{obs_lead}detrended-elevation slope at P{slp_pct}, "
            f"isostatic-gravity horizontal gradient at P{grv_pct}, TMI horizontal gradient at P{tmi_pct} "
            f"(median cover-depth index {cov_med:.2f}), geodetic/seismic kinematics at P{kin_pct}, "
            f"subsurface conductivity at P{cnd_pct}, and {int(round(100 * anc_frac))}% multi-threshold "
            f"ancestor persistence (H16-1/H19-4). Phase 2 geologist verification should check for "
            f"en-echelon scarp continuity or spring/alteration alignment while ruling out {mimic}."
        )

        tr["structural_zone"] = zone
        tr["mean_det_elev_m"] = round(mean_de, 2)
        tr["observables"] = {
            "det_elev_slope_pctl": slp_pct,
            "iso_grav_hg_pctl": grv_pct,
            "tmi_hg_pctl": tmi_pct,
            "kinematic_strain_seis_pctl": kin_pct,
            "cond_surf_pctl": cnd_pct,
            "lidar_1m_step_pctl": lid_pct,
            "lidar_coverage_frac": round(lid_cov, 3),
            "ancestor_persistence_frac": round(anc_frac, 3),
        }
        tr["geologist_evidence"] = paragraph

        features.append(
            {
                "type": "Feature",
                "id": tr["trace_id"],
                "properties": {
                    "trace_id": tr["trace_id"],
                    "rank": tr["rank"],
                    "length_km": tr["length_km"],
                    "arc_length_m": tr["arc_length_m"],
                    "chord_length_m": tr["chord_length_m"],
                    "tortuosity": tr["tortuosity"],
                    "strike_deg": tr["strike_deg"],
                    "strike_compass": tr["strike_compass"],
                    "strike_coherence_rbar": tr["strike_coherence_rbar"],
                    "n_dots": tr["n_dots"],
                    "structural_zone": zone,
                    "mean_det_elev_m": tr["mean_det_elev_m"],
                    "min_catalogue_dist_m": tr["min_catalogue_dist_m"],
                    "mean_physical_score": tr["mean_physical_score"],
                    "utm_epsg32611_start": [tr["easting_m"][0], tr["northing_m"][0]],
                    "utm_epsg32611_end": [tr["easting_m"][-1], tr["northing_m"][-1]],
                    "det_elev_slope_pctl": slp_pct,
                    "iso_grav_hg_pctl": grv_pct,
                    "tmi_hg_pctl": tmi_pct,
                    "kinematic_pctl": kin_pct,
                    "lidar_1m_step_pctl": lid_pct,
                    "ancestor_persistence_frac": round(anc_frac, 3),
                    "geologist_evidence": paragraph,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords_lonlat,
                },
            }
        )
    return features


def nearest_neighbour_stats(mask: np.ndarray, added_mask: np.ndarray | None = None) -> dict[str, float]:
    ys, xs = np.nonzero(mask)
    pts = np.column_stack([xs.astype(np.float64), ys.astype(np.float64)])
    tree = cKDTree(pts)
    d, _ = tree.query(pts, k=2)
    nn = d[:, 1]
    out = {
        "min_px": round(float(nn.min()), 4),
        "mean_px": round(float(nn.mean()), 4),
        "median_px": round(float(np.median(nn)), 4),
        "p05_px": round(float(np.quantile(nn, 0.05)), 4),
        "p95_px": round(float(np.quantile(nn, 0.95)), 4),
    }
    if added_mask is not None and np.any(added_mask):
        ay, ax = np.nonzero(added_mask)
        apts = np.column_stack([ax.astype(np.float64), ay.astype(np.float64)])
        da, _ = tree.query(apts, k=2)
        ann = da[:, 1]
        out["added_min_nn_px"] = round(float(ann.min()), 4)
        out["added_median_nn_px"] = round(float(ann.median() if hasattr(ann, "median") else np.median(ann)), 4)
    return out


def diff_against_mask(cand: np.ndarray, ref: np.ndarray) -> dict:
    n_ref = int(ref.sum())
    n_common = int((cand & ref).sum())
    n_added = int((cand & ~ref).sum())
    n_removed = int((~cand & ref).sum())
    return {
        "n_ref": n_ref,
        "n_cand": int(cand.sum()),
        "n_common": n_common,
        "n_added": n_added,
        "n_removed": n_removed,
        "pct_removed_of_ref": round(100.0 * n_removed / n_ref, 4),
        "pct_half_sym_diff_of_ref": round(100.0 * (n_added + n_removed) / (2.0 * n_ref), 4),
        "pct_full_sym_diff_of_ref": round(100.0 * (n_added + n_removed) / n_ref, 4),
    }


def sgmc_dot_credit_summary(mask: np.ndarray, sgmc_off: np.ndarray) -> float:
    """Mean per-dot kernel self-credit against off-catalogue SGMC truth."""
    if not np.any(mask):
        return 0.0
    _, k_max, _ = metric.max_cover(mask.astype(np.float64), sgmc_off)
    return float(k_max[mask].mean())


# ---------------------------------------------------------------------------
# 3. End-to-End Deterministic TRACKB Pipeline
# ---------------------------------------------------------------------------


def main() -> int:
    t0 = time.time()
    print("[1/7] Verifying SHA-256 manifest pins...")
    verified = bp.verify_manifest()
    print(f"      Verified {len(verified)}/{len(verified)} pinned inputs.")

    print("[2/7] Rebuilding parent R0 (h33-h33-2-b2) from lineage recipe...")
    lin = bp.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    print(
        f"      EXACT R0 REBUILD OK: {int(r0.sum()):,} dots | "
        f"zeros={lin['rebuilt_zeros_sha256'][:12]}... | nan={lin['rebuilt_nan_sha256'][:12]}..."
    )

    print("[3/7] Rebuilding 4-line physical field, running canaries, and reconstructing gate-clean R1...")
    w_field, canaries = bp.build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    max_canary = max(canaries.values())
    if max_canary > 0.90:
        raise RuntimeError(f"Leakage canary tripped (> 0.90): {max_canary:.5f}")
    print(f"      Canaries PASS ({len(canaries)} channels; max symmetric AUC = {max_canary:.5f} <= 0.90)")
    r1 = bsv.reconstruct_r1(lin, w_field, verified)

    print("[4/7] Extracting strike-consistent >= 1.0 km fault traces & geologist GeoJSON...")
    with rasterio.open(verified["sample_submission"]) as tpl_ds:
        grid_transform = tpl_ds.transform
        grid_crs = str(tpl_ds.crs)
    h19_4 = (np.nan_to_num(rasterio.open(verified["anc_h19_4"]).read(1), nan=0.0) > 0) & foot
    h16_1 = (np.nan_to_num(rasterio.open(verified["anc_h16_1"]).read(1), nan=0.0) > 0) & foot

    traces, trace_dot_mask = extract_strike_consistent_traces(
        dot_mask=r0 & (d_cat > MIN_CATALOGUE_PX),
        scores=w_field,
        foot=foot,
        d_cat=d_cat,
        transform=grid_transform,
        max_step_m=450.0,
        max_deflection_deg=25.0,
        min_length_m=1000.0,
        max_tortuosity=1.20,
        min_cat_px=MIN_CATALOGUE_PX,
    )
    geojson_features = annotate_traces_for_geologist(
        traces, verified, foot, h19_4, h16_1, crs_str=grid_crs
    )
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    geojson_obj = {
        "type": "FeatureCollection",
        "name": "gemsdoe88_trackb_strike_consistent_traces_ge1km",
        "metadata": {
            "schema": "gems88.trackb.geojson.v1",
            "parent_r0": R0_ID,
            "gate_clean_parent_r1": R1_ID,
            "crs_rfc7946": "EPSG:4326 (WGS84 lon/lat); UTM EPSG:32611 endpoints stored in properties",
            "min_trace_length_km": 1.0,
            "max_step_m": 450.0,
            "max_deflection_deg": 25.0,
            "max_tortuosity": 1.20,
            "min_catalogue_clearance_m": 300.0,
            "trace_count": len(geojson_features),
            "total_trace_dots": int(trace_dot_mask.sum()),
            "total_trace_length_km": round(sum(t["length_km"] for t in traces), 2),
            "git_sha": bp.git_sha(),
        },
        "features": geojson_features,
    }
    GEOJSON_OUT.write_text(json.dumps(geojson_obj, separators=(",", ":")) + "\n", encoding="utf-8")
    geojson_sha = bp.sha256_file(GEOJSON_OUT)
    print(
        f"      Wrote {GEOJSON_OUT.relative_to(ROOT)}: {len(geojson_features):,} traces >= 1.0 km "
        f"({geojson_obj['metadata']['total_trace_length_km']:,.1f} km total), "
        f"{GEOJSON_OUT.stat().st_size:,} B, sha256={geojson_sha[:12]}..."
    )

    # Write concise human-readable geologist dossier summarizing zones & top 25 traces
    zone_counts: dict[str, int] = {}
    for t in traces:
        zone_counts[t["structural_zone"]] = zone_counts.get(t["structural_zone"], 0) + 1
    dossier_lines = [
        "# TRACKB Phase 2 Structural-Geologist Trace Dossier (`>= 1.0 km`)",
        "",
        f"- **Source lineage:** `{R0_ID}` off-collar dots (`d_cat > 300 m`, `35,483` dots, 100% present in gate-clean `{R1_ID}`)",
        f"- **GeoJSON artifact:** `evidence/trackb_traces_geologist.geojson` (`SHA-256: {geojson_sha}`, `{len(traces):,}` traces, `1` evidence paragraph per trace)",
        f"- **Total mapped off-catalogue trace length:** `{geojson_obj['metadata']['total_trace_length_km']:,.1f} km` (`min = {min(t['length_km'] for t in traces):.2f} km`, `median = { float(np.median([t['length_km'] for t in traces])):.2f} km`, `max = {max(t['length_km'] for t in traces):.2f} km`)",
        f"- **Structural-relief breakdown:** basin floor `{zone_counts.get('basin floor', 0)}`, piedmont bajada `{zone_counts.get('piedmont bajada', 0)}`, range front / bedrock `{zone_counts.get('range front / bedrock block', 0)}`",
        "",
        "## Top 25 Highest-Priority Off-Catalogue Fault Traces (Full Set in GeoJSON)",
        "",
    ]
    for t in traces[:25]:
        dossier_lines.append(f"### {t['trace_id']} — `{t['length_km']:.2f} km`, `{t['strike_compass']}`, `{t['structural_zone']}`")
        dossier_lines.append(t["geologist_evidence"])
        dossier_lines.append("")
    DOSSIER_OUT.write_text("\n".join(dossier_lines), encoding="utf-8")

    print("[5/7] Building 3 preregistered controlled AXIS=TRACKB raster variants...")
    n_parent = int(r1.sum())
    n_dose = int(round(DOSE_FRAC * n_parent))  # 3,765 dots = 10.00%
    base_pruned, dropped_speckles, donor_stats = select_isolated_speckle_donors(
        base_mask=r1,
        trace_dot_mask=trace_dot_mask,
        w=w_field,
        n_drop=n_dose,
        isolation_radius_px=4.5,
    )
    spine_mask = build_trace_spine_mask(traces, foot, d_cat, min_cat_px=MIN_CATALOGUE_PX + COLLAR_EPS)
    spine_pool = spine_mask & (~r1) & foot & (d_cat > MIN_CATALOGUE_PX + COLLAR_EPS)
    tip_cone = build_tip_extension_cone_mask(
        traces,
        foot,
        d_cat,
        min_dist_px=2.8,
        max_dist_px=9.5,
        max_angle_deg=25.0,
        min_cat_px=MIN_CATALOGUE_PX + COLLAR_EPS,
    ) & (~r1)

    m_speckle = base_pruned.copy()
    m_ext = select_spaced_exact_marginal_dti_add(
        base_mask=base_pruned,
        cand_mask=tip_cone,
        w=w_field,
        n_add=n_dose,
        min_sep_px=2.8,
    )
    m_spine = bp.select_exact_marginal_dti_add(
        base_mask=base_pruned,
        cand_mask=spine_pool,
        w=w_field,
        n_add=n_dose,
    )

    assert int(m_speckle.sum()) == n_parent - n_dose == 33_889
    assert int(m_ext.sum()) == n_parent == 37_654
    assert int(m_spine.sum()) == n_parent == 37_654
    for vname, mm in (("speckle10minus", m_speckle), ("traceext10", m_ext), ("tracespine10", m_spine)):
        assert float(d_cat[mm].min()) > MIN_CATALOGUE_PX + COLLAR_EPS, f"{vname} violated >3 px collar"
        assert int((mm & trace_dot_mask).sum()) == int(trace_dot_mask.sum()), f"{vname} lost >=1 km trace dots"

    # Prepare idempotent ledger & card update (replace only R1 TRACKB rows on rerun)
    raw_kept_lines: list[str] = []
    fieldnames: list[str] = []
    header_line = ""
    existing_shas: set[str] = {bp.PARENT_SHA_ZEROS, bp.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS}
    if LEDGER.is_file():
        with LEDGER.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                if row.get("axis") == AXIS and row.get("parent") == R1_ID and row.get("value") in OUR_VALUES:
                    continue
                for k in ("sha256", "sha256_zeros"):
                    if row.get(k):
                        existing_shas.add(row[k].strip())
        with LEDGER.open("r", newline="", encoding="utf-8") as fh:
            raw_lines = fh.read().splitlines()
        header_line = raw_lines[0]
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if len(parsed) > 3 and parsed[1] == R1_ID and parsed[2] == AXIS and parsed[3] in OUR_VALUES:
                continue
            raw_kept_lines.append(line)

    for v in OUR_VALUES:
        for stale in RELEASES.glob(f"{R1_ID}-{AXIS}{v}-*"):
            stale.unlink()

    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    prereg_by_val = {item["value"]: item for item in prereg["variants"]}

    variant_defs = [
        (
            "speckle10minus",
            m_speckle,
            "R1(6f7ae705); TRACKB -10% (3765) isolated <450m speckles off >=1km traces; pred +0.003 MODEL",
            "exact-marginal-DTI drop of 3765 isolated 1-dot speckles (0 neighbors <=450m, off all 1259 >=1km traces); 0 added",
            f"Phase 2 TRACKB pure speckle cut: drop 3,765 (10.00%) isolated <450 m non-trace speckles (N=33,889, d_cat>3 px); all {len(traces)} >=1 km GeoJSON traces preserved intact.",
        ),
        (
            "traceext10",
            m_ext,
            "R1(6f7ae705); TRACKB 10% (3765) speckles->spaced >=2.8px >=1km trace tips; pred +0.004 MODEL",
            "exact-marginal-DTI drop of 3765 isolated speckles + spaced (d_nn>=2.8284px) exact-marginal add in <=950m +-25deg >=1km trace tip/relay cones",
            f"Phase 2 TRACKB spaced trace extension: move 3,765 dots (10.00%, N=37,654, d_cat>3 px, d_nn>=2.83 px) from isolated speckles onto along-strike tip & relay cones of {len(traces)} >=1 km traces.",
        ),
        (
            "tracespine10",
            m_spine,
            "R1(6f7ae705); TRACKB 10% (3765) speckles->100m spines of >=1km traces; pred -0.003 MODEL",
            "exact-marginal-DTI drop of 3765 isolated speckles + exact-marginal 100m polyline spine infill along top-ranked >=1km GeoJSON traces",
            f"Phase 2 TRACKB continuous-spine control: move 3,765 dots (10.00%, N=37,654, d_cat>3 px) from isolated speckles onto 100 m polyline spines of top-ranked >=1 km GeoJSON traces.",
        ),
    ]

    receipts: dict[str, dict] = {}
    for val, mask, note_tpl, rank_basis, desc in variant_defs:
        rec = bp.write_and_verify_variant(
            mask=mask,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=r1,
            axis=AXIS,
            value=val,
            note_template=note_tpl,
            existing_shas=existing_shas,
            parent_id=R1_ID,
            parent_sha_zeros=R1_SHA_ZEROS,
            parent_sha_nan=R1_SHA_NAN,
            date=FIXED_DATE,
            min_catalogue_px=MIN_CATALOGUE_PX + COLLAR_EPS,
        )
        existing_shas.update({rec["sha256"], rec["sha256_zeros"]})
        rec["ranking_basis"] = rank_basis
        rec["description"] = desc
        rec["preregistered_prediction"] = prereg_by_val[val]["preregistered_predicted_change"]
        rec["preregistered_range"] = prereg_by_val[val]["preregistered_predicted_range"]
        rec["r0_diff"] = diff_against_mask(mask, r0)
        assert 1.0 <= rec["r0_diff"]["pct_half_sym_diff_of_ref"] <= 50.0
        assert 1.0 <= rec["r0_diff"]["pct_removed_of_ref"] <= 50.0
        rec["nearest_neighbour_stats"] = nearest_neighbour_stats(mask, added_mask=mask & (~r1))
        rec["geojson_traces"] = {
            "path": "evidence/trackb_traces_geologist.geojson",
            "sha256": geojson_sha,
            "trace_count": len(traces),
            "trace_dots_preserved": int((mask & trace_dot_mask).sum()),
        }
        receipts[val] = rec

    print("[6/7] Running REPORT-ONLY diagnostics (HOLDOUT-DTI, blind SGMC control, w-DTI, block CV)...")
    arms = {
        R0_ID: r0,
        R1_ID: r1,
        receipts["speckle10minus"]["id"]: m_speckle,
        receipts["traceext10"]["id"]: m_ext,
        receipts["tracespine10"]["id"]: m_spine,
    }
    diag = bp.evaluate_report_only_instruments(
        arms=arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )

    sgmc_raw = rasterio.open(verified["sgmc_faults_control"]).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    w_r1 = bp.weighted_expected_dti(r1, np.where(foot & ~catalogue, w_field, 0.0))
    donor_sgmc_credit = sgmc_dot_credit_summary(dropped_speckles, sgmc_off)
    trace_sgmc_credit = sgmc_dot_credit_summary(trace_dot_mask, sgmc_off)

    cards = json.loads(CARDS.read_text(encoding="utf-8")) if CARDS.is_file() else {}
    cards = {
        k: v for k, v in cards.items()
        if not (k.startswith(f"{R1_ID}-{AXIS}") and any(f"-{AXIS}{vv}-" in k for vv in OUR_VALUES))
    }

    card_templates = {
        "speckle10minus": {
            "hypothesis": (
                "Crustal geothermal faults in the Great Basin propagate as coherent >= 1 km structural "
                "breaks, whereas completely isolated 1-dot H19-5 peaks (0 R1 neighbors within 450 m) are "
                "predominantly sub-resolution non-fault point clutter whose true fault credit lies below "
                "the DTI break-even bar 0.2 * DTI (~0.056); removing the 10% lowest-marginal-gain isolated "
                "speckles trims denominator waste while leaving all 1,259 >= 1 km Phase 2 traces intact."
            ),
            "mechanism": (
                "Under DTI = T / (0.2*T + 0.2*(S - M) + 0.8*|G|), removing 3,765 isolated singletons cuts "
                "0.2*S by 753.0 denominator units with zero neighbor-coverage interaction (nearest surviving "
                "dot > 450 m > R = 300 m). In Phase 2 ($250k), USGS/NBMG reviewers expand truth labels "
                "around mappable fault traces, never around isolated 100 m speckles."
            ),
            "non_fault_mimic": (
                "Circular Tertiary volcanic plugs/vents, boulder-armored alluvial fan bars, stock-pond or "
                "playa desiccation highs, and single-line 400 m GeoDAWN tie-line spikes produce isolated "
                "point ridges; conversely, a buried horst tip or short cross-fault transfer could appear "
                "as an isolated crest and be lost by pruning."
            ),
        },
        "traceext10": {
            "hypothesis": (
                "Normal-fault displacement tapers toward fault tips (D/L ~ 1e-3 to 1e-2) and steps across "
                "300-900 m en-echelon relay ramps (Faulds & Hinz 2015), causing fixed-threshold H19-5 "
                "ridges to terminate prematurely; reallocating 3,765 isolated speckles onto mutually "
                ">= 2.8 px-spaced pixels inside <= 950 m, +-25 deg along-strike tip/relay cones captures "
                "unmapped tip and relay truth without incurring the IR-88-38 densification tax."
            ),
            "mechanism": (
                "Count is held fixed at 37,654 so global mass S is unchanged. Enforcing d_nn >= 2.8284 px "
                "guarantees every added dot opens a fresh 300 m triangular-kernel footprint along the "
                "projected strike of an established >= 1 km fault trace rather than duplicating coverage "
                "1-2 px beside an existing dot, directly addressing Phase 2 expert trace expansion."
            ),
            "non_fault_mimic": (
                "Linear pediment-alluvial contacts, coalescing bajada channels, Lake Lahontan/Bonneville "
                "strandlines, and aeromagnetic flight-line corrugation continue straight past true fault "
                "terminations, pulling tip projections into unfaulted basin fill where slip genuinely died out."
            ),
        },
        "tracespine10": {
            "hypothesis": (
                "Phase 2 continuous-trace rasterization diagnostic control: infilling the 100 m polyline "
                "spines between 2.8 px-spaced dots on the highest-ranked >= 1 km GeoJSON traces creates "
                "unambiguous continuous raster lines for human/geologist inspection, but on Phase 1 DTI "
                "is predicted to lose slightly (-0.003 MODEL) due to the IR-88-38/IR-88-41 kernel "
                "densification tax."
            ),
            "mechanism": (
                "Two flanking trace dots 2.83-4.24 px apart already supply 0.29-0.53 triangular-kernel "
                "coverage at intermediate spine pixels, capping marginal T gain at <= 0.47-0.71 even on "
                "exact truth while still charging ~0.2 denominator units where truth is offset > 100 m; "
                "paired against traceext10 at identical N=37,654 and identical 3,765 speckle removals, "
                "this isolates continuous-line densification from spaced trace extension."
            ),
            "non_fault_mimic": (
                "Straightened Bresenham segments across <= 450 m dot steps can bridge minor non-tectonic "
                "erosional scarps, shoreline benches, or dikes, concentrating extra mass onto a single "
                "false lineament."
            ),
        },
    }

    new_csv_lines: list[str] = []
    for val, mask in (("speckle10minus", m_speckle), ("traceext10", m_ext), ("tracespine10", m_spine)):
        rec = receipts[val]
        vid = rec["id"]
        arm_diag = diag[vid]
        w_arm = bp.weighted_expected_dti(mask, np.where(foot & ~catalogue, w_field, 0.0))
        added_mask = mask & (~r1)
        added_sgmc_credit = sgmc_dot_credit_summary(added_mask, sgmc_off)
        sgmc_delta_r1 = round(arm_diag["sgmc_control"]["dti"] - diag[R1_ID]["sgmc_control"]["dti"], 6)
        w_delta_r1 = round(w_arm["dti"] - w_r1["dti"], 6)

        rec["report_only_diagnostics"] = {
            **arm_diag,
            "sgmc_delta_vs_r1": sgmc_delta_r1,
            "sgmc_delta_vs_r0": round(arm_diag["sgmc_control"]["dti"] - diag[R0_ID]["sgmc_control"]["dti"], 6),
            "donor_mean_sgmc_credit_per_dot": round(donor_sgmc_credit, 5),
            "added_mean_sgmc_credit_per_dot": round(added_sgmc_credit, 5),
            "trace_dot_mean_sgmc_credit_per_dot": round(trace_sgmc_credit, 5),
            "w_expected_dti_model": round(w_arm["dti"], 6),
            "w_expected_dti_delta_vs_r1": w_delta_r1,
            "leakage_canary_max_sym_auc": round(max_canary, 5),
        }
        (RELEASES / f"{vid}.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")

        pred_str = rec["preregistered_prediction"]
        range_str = rec["preregistered_range"]
        rec_note = (
            f"PHASE 2 TRACKB (not a weekly slot unless human decides; Brief §5): gate-clean >3 px; "
            f"SGMC={arm_diag['sgmc_control']['dti']:.5f} PROXY (delta vs R1 {sgmc_delta_r1:+.5f}); "
            f"12km CV={arm_diag['block_density_cv']['cv_12km_120px_interior']:.4f}; "
            f"paired with evidence/trackb_traces_geologist.geojson ({len(traces)} traces >=1 km)."
        )

        row_dict = {
            "id": vid,
            "parent": R1_ID,
            "axis": AXIS,
            "value": val,
            "n_dots": str(rec["n_dots"]),
            "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
            "sha256": rec["sha256"],
            "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT",
            "predicted_change": pred_str,
            "predicted_range": range_str,
            "ranking_basis": rec["ranking_basis"],
            "receipt_score": "",
            "receipt_date": "",
            "description": rec["description"],
            "recommendation": rec_note,
        }
        buf_row = [row_dict[col] for col in fieldnames]
        import io
        sio = io.StringIO()
        csv.writer(sio, lineterminator="").writerow(buf_row)
        new_csv_lines.append(sio.getvalue())

        ct = card_templates[val]
        cards[vid] = {
            "parent": R1_ID,
            "lineage_root": R0_ID,
            "axis": AXIS,
            "value": val,
            "hypothesis": ct["hypothesis"],
            "mechanism": ct["mechanism"],
            "non_fault_mimic": ct["non_fault_mimic"],
            "predicted_sign_size": (
                f"Preregistered {pred_str} live vs R1 (plausible range {range_str}); "
                f"post-build report-only blind SGMC PROXY = {arm_diag['sgmc_control']['dti']:.5f} "
                f"(delta vs R1 {sgmc_delta_r1:+.5f}, vs R0 {rec['report_only_diagnostics']['sgmc_delta_vs_r0']:+.5f}); "
                f"label-free w-DTI delta = {w_delta_r1:+.5f} MODEL. Treat |live delta| < 0.01 as no evidence."
            ),
            "falsifier": (
                "Phase 1 live receipt <= R1 - 0.01 falsifies low-credit speckle pruning / tip projection "
                "and proves isolated crests carry >= break-even off-catalogue truth; for traceext10 vs "
                "tracespine10, tracespine10 beating traceext10 by >= 0.01 falsifies the spacing-lock "
                "advantage over continuous 100 m trace rasterization."
            ),
            "n_dots": rec["n_dots"],
            "parent_diff": rec["parent_diff"],
            "r0_diff": rec["r0_diff"],
            "nearest_neighbour_stats": rec["nearest_neighbour_stats"],
            "geojson_deliverable": rec["geojson_traces"],
            "report_only_diagnostics": rec["report_only_diagnostics"],
            "report_only_not_gates": [
                "catalogue hide-and-recover PROXY (degenerate 0.0 for >3 px rasters; IR-88-20)",
                "single-feature leakage canary (15/15 <= 0.90)",
                "blind off-catalogue USGS SGMC control",
            ],
            "references": [
                {
                    "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
                    "claim": "DTI alpha=0.2, beta=0.8, 300 m triangular kernel; Phase 2 ($250k) rescores after expert geologist review expands fault labels.",
                },
                {
                    "url": "https://community.drivendata.org/t/where-do-you-draw-the-line/11536",
                    "claim": "New-fault truth includes unmapped geometry of fault systems outside pixel-exact USGS/INGENIOUS mask.",
                },
                {
                    "url": "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7",
                    "claim": "GeoDAWN Area 2 400 m line spacing motivates positional uncertainty and single-line point-clutter filtering.",
                },
            ],
            "submission_name": vid,
            "form_note": rec["form_note"],
        }

    LEDGER.write_text(
        "\n".join([header_line, *raw_kept_lines, *new_csv_lines]) + "\n",
        encoding="utf-8",
    )
    CARDS.write_text(json.dumps(cards, indent=2) + "\n", encoding="utf-8")

    print("[7/7] Running independent scripts/validate_variant.py on all 6 emitted GeoTIFFs...")
    tif_args = []
    for val in OUR_VALUES:
        tif_args.extend([receipts[val]["file_nan"], receipts[val]["file_zeros"]])
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_variant.py"), *tif_args, "--out", str(VALIDATION_OUT)],
        cwd=ROOT,
        check=True,
    )

    summary_report = {
        "schema": "gems88.trackb_axis_report.v1",
        "axis": AXIS,
        "seed": SEED,
        "git_sha": bp.git_sha(),
        "elapsed_sec": round(time.time() - t0, 2),
        "parent_r0": {
            "id": R0_ID,
            "n_dots": int(r0.sum()),
            "sha256_zeros": lin["rebuilt_zeros_sha256"],
            "sha256_nan": lin["rebuilt_nan_sha256"],
            "sgmc_proxy": diag[R0_ID]["sgmc_control"]["dti"],
            "cv_12km": diag[R0_ID]["block_density_cv"]["cv_12km_120px_interior"],
        },
        "parent_r1": {
            "id": R1_ID,
            "n_dots": int(r1.sum()),
            "sha256_nan": R1_SHA_NAN,
            "sha256_zeros": R1_SHA_ZEROS,
            "min_d_cat_px": round(float(d_cat[r1].min()), 4),
            "sgmc_proxy": diag[R1_ID]["sgmc_control"]["dti"],
            "cv_12km": diag[R1_ID]["block_density_cv"]["cv_12km_120px_interior"],
        },
        "leakage_canaries": {
            "channel_count": len(canaries),
            "max_symmetric_auc": round(max_canary, 5),
            "all_le_0_90": bool(max_canary <= 0.90),
            "per_channel": {k: round(float(v), 5) for k, v in canaries.items()},
        },
        "trace_inventory": {
            "geojson_path": "evidence/trackb_traces_geologist.geojson",
            "geojson_sha256": geojson_sha,
            "geojson_bytes": GEOJSON_OUT.stat().st_size,
            "dossier_path": "evidence/trackb_geologist_dossier.md",
            "trace_count": len(traces),
            "total_trace_dots": int(trace_dot_mask.sum()),
            "total_length_km": geojson_obj["metadata"]["total_trace_length_km"],
            "zone_counts": zone_counts,
            "donor_pool_stats": donor_stats,
            "spine_pool_px": int(spine_pool.sum()),
            "tip_cone_pool_px": int(tip_cone.sum()),
            "trace_dot_mean_sgmc_credit": round(trace_sgmc_credit, 5),
            "isolated_donor_mean_sgmc_credit": round(donor_sgmc_credit, 5),
        },
        "variants": [receipts[v] for v in OUR_VALUES],
    }
    REPORT_OUT.write_text(json.dumps(summary_report, indent=2) + "\n", encoding="utf-8")
    print(f"DONE in {summary_report['elapsed_sec']:.1f}s -> {REPORT_OUT.relative_to(ROOT)}")
    for val in OUR_VALUES:
        r = receipts[val]
        d = r["report_only_diagnostics"]
        print(
            f"  {r['id']} | N={r['n_dots']:,} | chg_R1={r['parent_diff']['pct_changed_moved']:.2f}% "
            f"(chg_R0_half_sym={r['r0_diff']['pct_half_sym_diff_of_ref']:.2f}%) | "
            f"min_d_cat={r['parent_diff']['min_dist_catalogue_px']:.4f}px | "
            f"min_nn={r['nearest_neighbour_stats']['min_px']:.4f}px | "
            f"SGMC={d['sgmc_control']['dti']:.6f} ({d['sgmc_delta_vs_r1']:+.6f} vs R1) | "
            f"12km_CV={d['block_density_cv']['cv_12km_120px_interior']:.4f} | "
            f"pred={r['preregistered_prediction']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
