#!/usr/bin/env python3
"""Build a PRUNE collar experiment whose refill is spacing-locked (non-densifying).

Why this axis and these values
------------------------------
R0 = ``h33-h33-2-b2`` holds 2,171 dots at ``2 < d_catalogue <= 3 px``.  Every
non-PRUNE child inherits that collar and therefore breaks the brief's literal
``>= 3 px`` rule, so PRUNE is the only axis that can be edited without adding a
second, implicit edit.  The existing PRUNE inventory answers the *collar*
question (``p1px`` ... ``p4.3px``) but every one of those arms refills from the
H19-5 support with no spacing constraint, which the ledger itself records as a
confounder (refill nearest-neighbour collapses from ``2.83`` to ``1.0`` px, and
the RELIEF family measured a densified add at only ``0.04-0.07`` TP/dot against
``0.11-0.16`` for a spaced one).

This script therefore builds three arms that separate the two mechanisms:

``p3norefill``  collar removal alone, no refill (N = 35,483).  Isolates the
                collar effect from any refill artefact.
``p3space35``   collar removal + 2,171 refills, each ``>= 3.5 px`` from every
                surviving dot and from every other refill (N = 37,654).  This
                is the gate-clean candidate: same edit as ``R1 = PRUNEp3px``,
                same count, but no densification penalty.
``p4space35``   the same non-densifying treatment at a 400 m collar (3,825
                refills).  Tests whether the negative ``p3.7px``/``p4.3px``
                slope in the existing sweep was caused by densifying refills.

Refill ranking is the shared exact iterative expected-DTI marginal gain on the
same fixed, label-free four-line physical field used by every prior PRUNE arm
(no leaderboard, no submission, no region-isolated probing).  The refill pool is
the union of the three lineage ridge supports (H19-5, H19-4, H16-1) outside the
collar; H19-5 alone cannot supply a spaced refill (only 57 legal cells at
``>= 3.5 px``).

Run from the repository root after the manifest-pinned inputs are restored::

    .venv/bin/python scripts/build_prune_spaced_variants.py
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from scripts import build_prune_variants as bpv  # noqa: E402
from gems57 import metric  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
AXIS = "PRUNE"
DATE = "20261023"
N_DOTS = 37_654
NO_EVIDENCE_BAND = 0.01
# How many top-ranked refill cells the greedy may inspect for feasibility at each step.
LOOKAHEAD = 256
MANIFEST = ROOT / "registry" / "data_manifest.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS_PATH = ROOT / "ledger" / "mechanism_cards.json"
RELEASES = ROOT / "releases"
REPORT_PATH = ROOT / "evidence" / "prune_v2_report.json"
PREREG_PATH = ROOT / "registry" / "prune_v2_preregistration.json"

SOURCE_SUPPORTS = ("anc_h19_5", "anc_h19_4", "anc_h16_1")

# Predictions were fixed from mechanism before any PROXY/SGMC instrument ran;
# they extend the spaced-refill ladder (p3space35 +0.007 SGMC +0.0050, p4space35 +0.002 SGMC +0.0064) to test spacing dose and collar width.
SPECS: tuple[dict[str, Any], ...] = (
    {
        "value": "p3space28",
        "collar_px": 3.0,
        "refill": True,
        "spacing_px": 2.8,
        "prediction": 0.005,
        "prediction_range": [-0.003, 0.014],
        "hypothesis": "At the 300m kernel radius, a 2.8px spacing lock (just inside the kernel) still prevents 1.0px densification that forfeits 0.04-0.07 TP/dot, while opening ~15% more candidates than 3.5px; should sit slightly below p3space35 (+0.007) but above densified R1 (+0.005).",
    },
    {
        "value": "p3.5space35",
        "collar_px": 3.5,
        "refill": True,
        "spacing_px": 3.5,
        "prediction": 0.004,
        "prediction_range": [-0.005, 0.013],
        "hypothesis": "A 350m collar removes ~30% more collar dots than 300m; if the collar is net-negative (potential-field side-lobes) the extra removal adds credit, but if it cuts real relay splays the spacing lock limits loss; predicted intermediate between p3space35 (+0.007) and p4space35 (+0.002).",
    },
    {
        "value": "p4space28",
        "collar_px": 4.0,
        "refill": True,
        "spacing_px": 2.8,
        "prediction": 0.001,
        "prediction_range": [-0.008, 0.012],
        "hypothesis": "400m equals GeoDAWN line spacing; if prior p3.7/p4.3 decline was densification-driven, a 2.8px lock should recover to break-even; if it was tip-loss it remains negative. Tightest spacing tests whether 2.8px is sufficient to keep refills non-redundant at larger collar.",
    },
)

FIELD_SOURCES = (
    "label-free four-line physical field from scripts/build_prune_variants.py: "
    "surface scarp, subsurface potential-field, strain/seismic and hydrothermal lines"
)
RANKING_BASIS = (
    "Exact iterative marginal expected-DTI gain (vendor/gems57/metric.py) among only "
    "those refill cells that keep a >= spacing_px separation from every surviving parent "
    "dot and from every already-chosen refill; candidate pool is the union of the H19-5, "
    "H19-4 and H16-1 ridge supports outside the collar; one fixed label-free physical "
    "field for all arms; no isolated-pixel shortcut and no random tie score"
)
REFERENCES = [
    {
        "url": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
        "claim": "Known USGS/INGENIOUS pixels are masked pixel-exactly; adjacent pixels are scored normally, so a collar dot is neither free nor certainly wrong.",
    },
    {
        "url": "https://community.drivendata.org/t/where-do-you-draw-the-line/11536",
        "claim": "New-fault truth may lie within 300 m of known traces, which is why both removing and refilling inside/near the collar must be tested rather than assumed.",
    },
    {
        "url": "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7",
        "claim": "GeoDAWN Area 2 line spacing is 400 m; used only as positional-uncertainty context for how far a dot may be re-centred, never as a label.",
    },
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_ledger() -> tuple[list[dict[str, str]], list[str]]:
    if not LEDGER.is_file():
        raise FileNotFoundError(f"Required ledger is missing: {LEDGER}")
    with LEDGER.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    required = {
        "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256",
        "sha256_zeros", "status", "predicted_change", "predicted_range",
        "ranking_basis", "receipt_score", "receipt_date", "description", "recommendation",
    }
    if not required.issubset(fields):
        raise ValueError(f"Unexpected ledger schema; missing {sorted(required - set(fields))}")
    return rows, fields


def preflight_pairs(rows: list[dict[str, str]]) -> None:
    values = [spec["value"] for spec in SPECS]
    if len(values) != len(set(values)):
        raise ValueError("This build contains repeated PRUNE values")
    pairs = {(row.get("parent"), row.get("axis"), row.get("value")) for row in rows}
    collisions = [(PARENT_ID, AXIS, v) for v in values if (PARENT_ID, AXIS, v) in pairs]
    if collisions:
        raise ValueError(f"Repeated (parent, axis, value) pair(s) in ledger: {collisions}")
    for spec in SPECS:
        prefix = f"{PARENT_ID}-{AXIS}{spec['value']}-{DATE}"
        if any(RELEASES.glob(f"{prefix}-*")):
            raise FileExistsError(f"Artifacts for this value already exist: {prefix}-*")


def ledger_hashes(rows: list[dict[str, str]]) -> set[str]:
    result = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}
    for row in rows:
        result.update(v for v in (row.get("sha256"), row.get("sha256_zeros")) if v)
    return result


def spaced_marginal_add(
    base_mask: np.ndarray,
    cand_mask: np.ndarray,
    w: np.ndarray,
    n_add: int,
    spacing_px: float,
    alpha: float = metric.ALPHA,
    beta: float = metric.BETA,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Greedy exact expected-DTI refill under a hard minimum-separation lock.

    Same arithmetic as ``build_prune_variants.select_exact_marginal_dti_add``
    (exact coverage ``C_A``, exact ``dT`` per candidate, exact two-sided DTI
    test), with one addition: a chosen refill permanently disables every
    candidate closer than ``spacing_px`` (and the initial pool already excludes
    cells closer than that to a surviving parent dot).  Fails closed if the
    spacing lock cannot supply ``n_add`` refills.
    """
    state = np.asarray(base_mask, dtype=bool).copy()
    if n_add <= 0:
        return state, {"requested": int(n_add), "filled": 0, "spacing_px": float(spacing_px)}
    H, W = state.shape
    w64 = np.asarray(w, dtype=np.float64)
    w_tot = float(w64.sum())

    cov = np.zeros((H, W), dtype=np.float64)
    by, bx = np.nonzero(state)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = by + int(dy), bx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        np.maximum.at(cov, (ny[ok], nx[ok]), kw)
    t_cur = float((w64 * cov).sum())
    m_base = np.zeros(len(by), dtype=np.float64)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = by + int(dy), bx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        m_base[ok] = np.maximum(m_base[ok], w64[ny[ok], nx[ok]] * kw)
    m_cur = float(m_base.sum())
    s_cur = float(len(by))

    # Spacing pre-filter against surviving parent dots.
    cy, cx = np.nonzero(cand_mask & ~state)
    if len(cy) == 0:
        raise ValueError("Empty refill pool")
    parent_pts = np.column_stack([by, bx]).astype(np.float64)
    cand_pts = np.column_stack([cy, cx]).astype(np.float64)
    d_parent = cKDTree(parent_pts).query(cand_pts, k=1)[0]
    keep = d_parent >= spacing_px
    # A pairwise pass bounds the maximal fill (greedy order dependent) before the loop.
    if int(keep.sum()) < n_add:
        raise ValueError(
            f"Only {int(keep.sum())} cage-free refill cells at >= {spacing_px} px from the "
            f"survivors, but {n_add} are required"
        )
    cy, cx = cy[keep], cx[keep]
    n_pool = len(cy)

    cand_id_grid = np.full((H, W), -1, dtype=np.int32)
    cand_id_grid[cy, cx] = np.arange(n_pool, dtype=np.int32)

    m_cand = np.zeros(n_pool, dtype=np.float64)
    dT = np.zeros(n_pool, dtype=np.float64)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = cy + int(dy), cx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        wv = w64[ny[ok], nx[ok]]
        m_cand[ok] = np.maximum(m_cand[ok], wv * kw)
        dT[ok] += wv * np.maximum(0.0, kw - cov[ny[ok], nx[ok]])

    chosen = np.zeros(n_pool, dtype=bool)
    avail = np.ones(n_pool, dtype=bool)
    off_dy = metric.OFF_DY.astype(np.int64)
    off_dx = metric.OFF_DX.astype(np.int64)
    off_k = metric.OFF_K.astype(np.float64)
    lock = int(np.ceil(spacing_px))
    best_dti_trace: list[float] = []

    for _ in range(n_add):
        d_cur = alpha * (t_cur + s_cur - m_cur) + beta * w_tot + metric.EPS
        next_dti = (t_cur + dT) / (d_cur + alpha * (dT + 1.0 - m_cand))
        next_dti[~avail] = -np.inf
        if not np.isfinite(next_dti.max()):
            raise ValueError(
                f"Spacing lock exhausted the refill pool after {int(chosen.sum())} of {n_add}"
            )
        # Feasibility lookahead: among the top-ranked available cells, take the best
        # one whose spacing footprint still leaves enough cells to finish the fill.
        # The DTI ranking is unchanged; only an infeasible (blocking) pick is skipped.
        top = np.argpartition(-next_dti, min(n_pool - 1, LOOKAHEAD))[: LOOKAHEAD + 1]
        top = top[np.argsort(-next_dti[top], kind="stable")]
        need_after = n_add - int(chosen.sum()) - 1
        avail_n = int(avail.sum())
        best = -1
        fallback = -1
        fallback_blocked = None
        for cand_id in top:
            if not avail[cand_id] or not np.isfinite(next_dti[cand_id]):
                continue
            ry, rx = int(cy[cand_id]), int(cx[cand_id])
            y0, y1 = max(0, ry - lock), min(H, ry + lock + 1)
            x0, x1 = max(0, rx - lock), min(W, rx + lock + 1)
            sub = cand_id_grid[y0:y1, x0:x1].ravel()
            sub = sub[sub >= 0]
            if sub.size:
                blocked_n = int(
                    np.count_nonzero(
                        avail[sub]
                        & (np.hypot(cy[sub] - ry, cx[sub] - rx) < spacing_px)
                    )
                )
            else:
                blocked_n = 0
            remaining_after = avail_n - 1 - blocked_n
            if fallback < 0 or blocked_n < fallback_blocked:
                fallback, fallback_blocked = int(cand_id), blocked_n
            if remaining_after >= need_after:
                best = int(cand_id)
                break
        if best < 0:
            if fallback < 0:
                raise ValueError(
                    f"No feasible refill cell remained after {int(chosen.sum())} of {n_add}"
                )
            best = int(fallback)
        chosen[best] = True
        best_dti_trace.append(float(next_dti[best]))
        ry, rx = int(cy[best]), int(cx[best])
        state[ry, rx] = True

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

        # Spacing lock: every candidate within spacing_px of the new dot is disabled.
        y0, y1 = max(0, ry - lock), min(H, ry + lock + 1)
        x0, x1 = max(0, rx - lock), min(W, rx + lock + 1)
        sub = cand_id_grid[y0:y1, x0:x1].ravel()
        sub = sub[sub >= 0]
        if sub.size:
            dyv = (cy[sub] - ry).astype(np.float64)
            dxv = (cx[sub] - rx).astype(np.float64)
            avail[sub[np.hypot(dyv, dxv) < spacing_px]] = False
        avail[best] = False

        # Exact dT refresh inside the 6 px kernel neighbourhood.
        y0, y1 = max(0, ry - 6), min(H, ry + 7)
        x0, x1 = max(0, rx - 6), min(W, rx + 7)
        sub_ids = cand_id_grid[y0:y1, x0:x1].ravel()
        sub_ids = sub_ids[sub_ids >= 0]
        if sub_ids.size:
            sub_ids = sub_ids[avail[sub_ids]]
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

    return state, {
        "requested": int(n_add),
        "filled": int(chosen.sum()),
        "spacing_px": float(spacing_px),
        "spacing_pool_cells": int(n_pool),
        "min_filled_marginal_dti": float(min(best_dti_trace)) if best_dti_trace else None,
        "max_filled_marginal_dti": float(max(best_dti_trace)) if best_dti_trace else None,
    }


def nearest_neighbour_stats(mask: np.ndarray) -> dict[str, float]:
    points = np.argwhere(mask)
    if len(points) < 2:
        raise ValueError("Nearest-neighbour statistics need at least two dots")
    distances = cKDTree(points).query(points, k=2)[0][:, 1]
    return {
        "min_px": float(distances.min()),
        "mean_px": float(distances.mean()),
        "p05_px": float(np.percentile(distances, 5)),
        "p95_px": float(np.percentile(distances, 95)),
    }


def build_arm(
    parent: np.ndarray,
    support_union: np.ndarray,
    d_catalogue: np.ndarray,
    weight: np.ndarray,
    spec: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Remove the collar; optionally refill to the parent count under a spacing lock."""
    collar_px = float(spec["collar_px"])
    survivors = np.asarray(parent, dtype=bool) & (d_catalogue > collar_px)
    removed_n = int(np.asarray(parent, dtype=bool).sum() - survivors.sum())
    if removed_n <= 0:
        raise ValueError("Collar removed no parent dots")
    stats: dict[str, Any] = {
        "collar_px": collar_px,
        "collar_m": collar_px * 100.0,
        "n_removed": removed_n,
        "refill": bool(spec["refill"]),
        "spacing_px": spec["spacing_px"],
    }
    if not spec["refill"]:
        candidate = survivors
        stats.update(n_added=0, refill_pool_cells=0)
    else:
        pool = np.asarray(support_union, dtype=bool) & ~survivors & (d_catalogue > collar_px)
        if int(pool.sum()) < removed_n:
            raise ValueError(f"Legal refill pool ({int(pool.sum())}) < removals ({removed_n})")
        candidate, lock_stats = spaced_marginal_add(
            base_mask=survivors,
            cand_mask=pool,
            w=weight,
            n_add=removed_n,
            spacing_px=float(spec["spacing_px"]),
        )
        stats.update(refill_pool_cells=int(pool.sum()), spacing=lock_stats)
        if int(candidate.sum()) != int(np.asarray(parent).sum()):
            raise AssertionError(f"Fixed-count invariant failed: {int(candidate.sum())}")
        added_n = int((candidate & ~parent).sum())
        if added_n != removed_n:
            raise AssertionError(f"Refill count {added_n} != removals {removed_n}")
    n_added = int((candidate & ~parent).sum())
    n_removed_actual = int((parent & ~candidate).sum())
    stats.update(
        n_added=n_added,
        n_removed=n_removed_actual,
        pct_changed_moved=100.0 * n_removed_actual / int(parent.sum()),
        pct_changed_symmetric_difference=100.0 * (n_added + n_removed_actual) / int(parent.sum()),
        min_catalogue_distance_px=float(d_catalogue[candidate].min()),
        n_dots=int(candidate.sum()),
    )
    if not 1.0 <= stats["pct_changed_moved"] <= 50.0:
        raise ValueError(f"Changed fraction outside 1-50%: {stats['pct_changed_moved']:.3f}")
    if stats["min_catalogue_distance_px"] < 3.0:
        raise ValueError("Non-PRUNE 3 px collar floor failed")
    if spec["refill"]:
        refill_pts = np.argwhere(candidate & ~parent)
        all_pts = np.argwhere(candidate)
        dmin = cKDTree(all_pts).query(refill_pts, k=2)[0][:, 1]
        stats["refill_min_nn_px"] = float(dmin.min())
        if dmin.min() < float(spec["spacing_px"]) - 1e-9:
            raise AssertionError("Spacing lock violated in the emitted refill")
    return candidate, stats


def build_card(spec: dict[str, Any], stats: dict[str, Any], rec: dict[str, Any],
               nn: dict[str, float], parent_nn: dict[str, float]) -> dict[str, Any]:
    lo, hi = map(float, spec["prediction_range"])
    if spec["refill"]:
        change = (
            f"Remove {stats['n_removed']:,} R0 dots at d_catalogue <= {stats['collar_m']:.0f} m; "
            f"add back {stats['n_added']:,} dots from the H19-5/H19-4/H16-1 ridge supports "
            f"that are >= {spec['spacing_px']:g} px from every other dot in the output "
            f"(observed refill min NN {stats.get('refill_min_nn_px', float('nan')):.3f} px); "
            f"N held at {N_DOTS:,}."
        )
    else:
        change = (
            f"Remove {stats['n_removed']:,} R0 dots at d_catalogue <= {stats['collar_m']:.0f} m "
            f"and add nothing; N falls to {stats['n_dots']:,} (-{100.0 - 100.0 * stats['n_dots'] / N_DOTS:.2f}%)."
        )
    return {
        "axis": AXIS,
        "value": spec["value"],
        "collar_px": float(spec["collar_px"]),
        "collar_m": float(stats["collar_m"]),
        "refill": bool(spec["refill"]),
        "refill_spacing_px": spec["spacing_px"],
        "change_vs_parent": change,
        "hypothesis": spec["hypothesis"],
        "mechanism": (
            "For a binary dot field the metric is DTI = T / (0.2T + 0.2(S-M) + 0.8|G|), "
            "so a dot always pays 0.2 of mass and can only recover credit T where it is the "
            "nearest dot to a true new-fault pixel. Two dots 1 px apart cannot both be that "
            "nearest dot, which is why the ledger measured densified adds at 0.04-0.07 TP/dot "
            "and spaced ones at 0.11-0.16. The collar dots at 200-300 m from mapped traces are "
            "the strongest candidate false-positive population available (they are potential-field "
            "side-lobes of a known trace, and the known trace itself is masked and unscored), so "
            "removing them and refilling only on non-redundant, independent ridge support is the "
            "cleanest available mass-and-location edit."
        ),
        "non_fault_mimic": (
            "Long-wavelength magnetic/gravity side-lobes, pediment and alluvial-fan margins, and "
            "wave-cut shoreline breaks parallel range-front structures without new fault slip; "
            "in the other direction, a genuine antithetic splay or relay step can sit inside the "
            "200-300 m collar, and the organizer explicitly allows new-fault truth within 300 m "
            "of known traces."
        ),
        "predicted_sign_size": (
            f"MODEL predicted live delta {float(spec['prediction']):+.3f} vs R0 (CLAIM 0.2778), "
            f"plausible range [{lo:+.3f},{hi:+.3f}]. This is a projection, not a score; any live "
            f"|delta| < {NO_EVIDENCE_BAND:g} on public chunks is no evidence."
        ),
        "falsifier": (
            "A reception of <= R0 - 0.01 falsifies the collar hypothesis for this arm; a paired "
            "comparison with the densifying R1 (PRUNEp3px, MODEL +0.005) tests whether spacing is "
            "what pays: if p3norefill and p3space35 both land within +-0.01 of R0 while R1 does "
            "not, the whole collar family is noise. If p4space35 beats p3space35 by >= 0.01, the "
            "existing p3.7px/p4.3px decline was a refill artefact, not splay loss."
        ),
        "fixed_count": N_DOTS if spec["refill"] else stats["n_dots"],
        "parent_diff": rec["parent_diff"],
        "ranking_basis": RANKING_BASIS,
        "four_line_field": FIELD_SOURCES,
        "nearest_neighbour_stats": {
            "R0": parent_nn,
            "candidate": nn,
            "refill_min_nn_px": stats.get("refill_min_nn_px"),
        },
        "report_only_not_gates": [
            "hide-and-recover catalogue PROXY",
            "single-feature leakage canary",
            "blind off-catalogue SGMC control",
            "10 km and 12 km dot-density CV",
        ],
        "references": REFERENCES,
        "submission_name": rec["id"],
        "form_note": rec["form_note"],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def form_note(spec: dict[str, Any], stats: dict[str, Any]) -> str:
    if spec["refill"]:
        note = (
            f"R0 h33-2-b2; PRUNE<={stats['collar_m']:.0f}m +{stats['n_added']} refill "
            f">={spec['spacing_px']:g}px spaced, N {N_DOTS}; pred {float(spec['prediction']):+.3f} MODEL"
        )
    else:
        note = (
            f"R0 h33-2-b2; PRUNE<={stats['collar_m']:.0f}m no refill -{stats['n_removed']}, "
            f"N {stats['n_dots']}; pred {float(spec['prediction']):+.3f} MODEL"
        )
    return note


def main() -> int:
    rows, ledger_fields = load_ledger()
    preflight_pairs(rows)
    verified = bpv.verify_manifest(MANIFEST)
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot = lineage["foot"]
    catalogue = lineage["catalogue"]
    d_catalogue = lineage["d_cat"]
    parent = lineage["r0"]
    if int(parent.sum()) != N_DOTS:
        raise RuntimeError(f"Unexpected R0 dot count: {int(parent.sum())}")
    if lineage["rebuilt_zeros_sha256"] != bpv.PARENT_SHA_ZEROS or (
        lineage["rebuilt_nan_sha256"] != bpv.PARENT_SHA_NAN
    ):
        raise RuntimeError("STOP: R0 rebuild does not byte-match the pinned parent")
    if np.any(parent & catalogue) or int((d_catalogue[parent] <= 2.0).sum()) != 0:
        raise RuntimeError("STOP: R0 failed its recorded zero-catalogue/2 px geometry")

    support_union = np.zeros_like(parent)
    support_parts: dict[str, int] = {}
    for key in SOURCE_SUPPORTS:
        mask = (np.nan_to_num(rasterio.open(verified[key]).read(1), nan=0.0) > 0) & foot
        support_parts[key] = int(mask.sum())
        support_union |= mask

    manifest_sha = sha256_path(MANIFEST)
    write_json(
        PREREG_PATH,
        {
            "schema": "gems88.prune-spaced-preregistration.v1",
            "created_utc": utc_now(),
            "parent": {
                "id": PARENT_ID,
                "n_dots": N_DOTS,
                "zeros_sha256": lineage["rebuilt_zeros_sha256"],
                "nan_sha256": lineage["rebuilt_nan_sha256"],
                "evidence_class": "REBUILT byte-exact parent; historical 0.2778 remains CLAIM",
            },
            "axis": AXIS,
            "axis_selection": (
                "Agent-chosen. Every non-PRUNE child of R0 inherits the 2,171 dots at "
                "2 < d_catalogue <= 3 px and therefore violates the brief's literal >= 3 px rule; "
                "PRUNE is the only axis that can be edited on R0 without a second, implicit edit. "
                "The existing PRUNE arms all answer the collar width question with a densifying "
                "refill, so this session fixes the refill's spacing instead."
            ),
            "values_are_new": True,
            "ledger_pairs_checked": len(rows),
            "manifest_sha256": manifest_sha,
            "manifest_verified_inputs": len(verified),
            "git_sha": git_value("rev-parse", "HEAD"),
            "origin_main_sha_checked_before_build": git_value("rev-parse", "origin/main"),
            "source_support_pixels": support_parts,
            "source_support_union_pixels": int(support_union.sum()),
            "treatment": (
                "Remove every R0 dot at d_catalogue <= collar_px. Refill (or not) from the union "
                "of the H19-5, H19-4 and H16-1 ridge supports outside the collar, admitting only "
                "cells >= spacing_px from every surviving dot and disabling every cell within "
                "spacing_px of each chosen refill, ranked by exact iterative expected-DTI gain on "
                "the fixed four-line physical field."
            ),
            "refill_ranking_basis": RANKING_BASIS,
            "physical_field": FIELD_SOURCES,
            "predicted_no_evidence_band": NO_EVIDENCE_BAND,
            "predictions_are": "MODEL, registered before any PROXY/SGMC instrument ran",
            "variants": [
                {
                    "value": spec["value"],
                    "collar_px": spec["collar_px"],
                    "refill": spec["refill"],
                    "spacing_px": spec["spacing_px"],
                    "predicted_change": f"MODEL:{float(spec['prediction']):+.3f}",
                    "predicted_range": list(spec["prediction_range"]),
                    "hypothesis": spec["hypothesis"],
                }
                for spec in SPECS
            ],
            "report_only_not_gates": [
                "catalogue hide-and-recover PROXY with withheld-positive count and 95% CI",
                "single-feature leakage canary",
                "blind off-catalogue SGMC control",
                "10 km and 12 km dot-density CV",
            ],
            "no_submission": True,
        },
    )

    weight, canaries = bpv.build_physical_field_and_canaries(
        verified=verified, foot=foot, catalogue=catalogue, h19_5=(
            np.nan_to_num(rasterio.open(verified["anc_h19_5"]).read(1), nan=0.0) > 0
        ) & foot,
    )
    if not canaries or max(canaries.values()) > 0.90:
        raise RuntimeError(f"LEAKAGE CANARY FAILURE: {canaries}")

    candidates: dict[str, np.ndarray] = {}
    build_stats: dict[str, dict[str, Any]] = {}
    for spec in SPECS:
        key = f"{PARENT_ID}-{AXIS}{spec['value']}"
        candidate, stats = build_arm(
            parent=parent,
            support_union=support_union,
            d_catalogue=d_catalogue,
            weight=weight,
            spec=spec,
        )
        if int((candidate & catalogue).sum()) != 0:
            raise RuntimeError(f"Non-zero catalogue mass in {spec['value']}")
        weighted = bpv.weighted_expected_dti(candidate, weight)
        parent_weighted = bpv.weighted_expected_dti(parent, weight)
        stats["expected_dti_field"] = round(float(weighted["dti"]), 6)
        stats["expected_dti_delta_vs_r0"] = round(
            float(weighted["dti"] - parent_weighted["dti"]), 6
        )
        candidates[key] = candidate
        build_stats[spec["value"]] = stats

    arms = {PARENT_ID: parent, **candidates}
    diagnostics = bpv.evaluate_report_only_instruments(
        arms=arms, foot=foot, catalogue=catalogue, sgmc_path=verified["sgmc_faults_control"]
    )
    parent_nn = nearest_neighbour_stats(parent)

    existing_shas = ledger_hashes(rows)
    new_rows: list[dict[str, str]] = []
    new_cards: dict[str, dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    for spec in SPECS:
        value = str(spec["value"])
        key = f"{PARENT_ID}-{AXIS}{value}"
        candidate = candidates[key]
        stats = build_stats[value]
        nn = nearest_neighbour_stats(candidate)
        rec = bpv.write_and_verify_variant(
            mask=candidate,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=parent,
            axis=AXIS,
            value=value,
            note_template=form_note(spec, stats),
            existing_shas=existing_shas,
            parent_id=PARENT_ID,
            parent_sha_zeros=bpv.PARENT_SHA_ZEROS,
            parent_sha_nan=bpv.PARENT_SHA_NAN,
            date=DATE,
            min_catalogue_px=3.0,
        )
        existing_shas.update((rec["sha256"], rec["sha256_zeros"]))
        diag = diagnostics[key]
        rec.update(
            {
                "evidence_class": "BUILT candidate; MODEL projection only; no receipt",
                "manifest": {
                    "path": "registry/data_manifest.json",
                    "sha256": manifest_sha,
                    "verified_input_count": len(verified),
                    "all_manifest_inputs_verified": True,
                },
                "collar_px": stats["collar_px"],
                "collar_m": stats["collar_m"],
                "refill": stats["refill"],
                "refill_spacing_px": stats["spacing_px"],
                "removed_parent_dots": stats["n_removed"],
                "added_dots": stats["n_added"],
                "refill_pool_cells": stats.get("refill_pool_cells"),
                "refill_spacing_pool_cells": stats.get("spacing", {}).get("spacing_pool_cells"),
                "refill_min_nn_px": stats.get("refill_min_nn_px"),
                "pct_changed_exact": stats["pct_changed_moved"],
                "pct_changed_symmetric_difference": stats["pct_changed_symmetric_difference"],
                "ranking_basis": RANKING_BASIS,
                "four_line_field": FIELD_SOURCES,
                "source_support_pixels": support_parts,
                "build_script_sha256": sha256_path(Path(__file__).resolve()),
                "git_sha": git_value("rev-parse", "HEAD"),
                "origin_main_sha_checked_before_build": git_value("rev-parse", "origin/main"),
                "nearest_neighbour_stats": {
                    "R0": parent_nn,
                    "candidate": nn,
                    "refill_min_nn_px": stats.get("refill_min_nn_px"),
                    "interpretation": (
                        "REPORT ONLY. Refill cells are locked at >= the stated spacing from every "
                        "dot in the output; the parent's own 2.83 px pairs are inherited unchanged."
                    ),
                },
                "expected_dti_on_four_line_field": {
                    "dti": stats["expected_dti_field"],
                    "delta_vs_r0": stats["expected_dti_delta_vs_r0"],
                    "evidence_class": "MODEL (label-free physics field, not a truth set)",
                },
                "report_only_diagnostics": diag,
                "r0_reference_diagnostics": diagnostics[PARENT_ID],
                "leakage_canaries": {
                    "passed": all(v <= 0.90 for v in canaries.values()),
                    "max_single_feature_symmetric_auc": max(canaries.values()),
                    "channels": canaries,
                    "report_only": True,
                },
                "model_prediction": {
                    "evidence_class": "MODEL",
                    "delta_vs_r0": float(spec["prediction"]),
                    "range": list(spec["prediction_range"]),
                    "no_evidence_if_abs_live_delta_below": NO_EVIDENCE_BAND,
                    "registered_before_proxies": True,
                },
                "not_submitted": True,
            }
        )
        write_json(RELEASES / f"{rec['id']}.json", rec)
        receipts.append(rec)
        new_cards[rec["id"]] = build_card(spec, stats, rec, nn, parent_nn)

        new_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": AXIS,
                "value": value,
                "n_dots": str(stats["n_dots"]),
                "pct_changed": f"{stats['pct_changed_moved']:.5f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{float(spec['prediction']):+.3f}",
                "predicted_range": (
                    f"[{float(spec['prediction_range'][0]):+.3f},"
                    f"{float(spec['prediction_range'][1]):+.3f}]"
                ),
                "ranking_basis": RANKING_BASIS,
                "receipt_score": "",
                "receipt_date": "",
                "description": (
                    f"PRUNE d_catalogue<={stats['collar_px']:g}px ({stats['collar_m']:.0f}m); "
                    f"remove {stats['n_removed']}; "
                    + (
                        f"spacing-locked refill {stats['n_added']} at >= {stats['spacing_px']:g}px, "
                        f"N fixed {N_DOTS:,}."
                        if stats["refill"]
                        else f"no refill, N {stats['n_dots']:,}."
                    )
                ),
                "recommendation": "",
            }
        )

    # Write the ledger only after all three candidates passed their on-disk gates.
    old_pairs = {(r.get("parent"), r.get("axis"), r.get("value")) for r in rows}
    old_ids = {r.get("id") for r in rows}
    old_hashes = ledger_hashes(rows)
    for new in new_rows:
        pair = (new["parent"], new["axis"], new["value"])
        if new["id"] in old_ids or pair in old_pairs:
            raise RuntimeError(f"Ledger duplicate detected after build: {new['id']} / {pair}")
        if new["sha256"] in old_hashes or new["sha256_zeros"] in old_hashes:
            raise RuntimeError(f"Ledger SHA duplicate detected after build: {new['id']}")
        old_pairs.add(pair)
        old_ids.add(new["id"])
        old_hashes.update((new["sha256"], new["sha256_zeros"]))

    temp_ledger = LEDGER.with_suffix(".csv.tmp")
    with temp_ledger.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=ledger_fields, lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        for row in [*rows, *new_rows]:
            writer.writerow({field: row.get(field, "") for field in ledger_fields})
    os.replace(temp_ledger, LEDGER)

    current_cards = json.loads(CARDS_PATH.read_text(encoding="utf-8")) if CARDS_PATH.is_file() else {}
    overlap = set(current_cards) & set(new_cards)
    if overlap:
        raise RuntimeError(f"Mechanism card key collision: {sorted(overlap)}")
    current_cards.update(new_cards)
    write_json(CARDS_PATH, current_cards)

    write_json(
        REPORT_PATH,
        {
            "schema": "gems88.prune-spaced-report.v1",
            "created_utc": utc_now(),
            "axis": AXIS,
            "parent": {
                "id": PARENT_ID,
                "n_dots": N_DOTS,
                "rebuilt_zeros_sha256": lineage["rebuilt_zeros_sha256"],
                "rebuilt_nan_sha256": lineage["rebuilt_nan_sha256"],
                "evidence_class": "REBUILT; historical live 0.2778 is CLAIM",
            },
            "git_sha": git_value("rev-parse", "HEAD"),
            "build_script_sha256": sha256_path(Path(__file__).resolve()),
            "manifest": {
                "path": "registry/data_manifest.json",
                "sha256": manifest_sha,
                "verified_input_count": len(verified),
                "all_manifest_inputs_verified": True,
            },
            "source_support_pixels": support_parts,
            "leakage_canaries": {
                "passed": all(v <= 0.90 for v in canaries.values()),
                "max_single_feature_symmetric_auc": max(canaries.values()),
                "channels": canaries,
                "report_only": True,
            },
            "parent_diff": {
                spec["value"]: {
                    "collar_px": build_stats[spec["value"]]["collar_px"],
                    "refill": build_stats[spec["value"]]["refill"],
                    "spacing_px": build_stats[spec["value"]]["spacing_px"],
                    "n_removed": build_stats[spec["value"]]["n_removed"],
                    "n_added": build_stats[spec["value"]]["n_added"],
                    "pct_changed_moved": build_stats[spec["value"]]["pct_changed_moved"],
                    "pct_changed_symmetric_difference": build_stats[spec["value"]][
                        "pct_changed_symmetric_difference"
                    ],
                    "min_catalogue_distance_px": build_stats[spec["value"]][
                        "min_catalogue_distance_px"
                    ],
                    "refill_min_nn_px": build_stats[spec["value"]].get("refill_min_nn_px"),
                    "refill_spacing_pool_cells": build_stats[spec["value"]]
                    .get("spacing", {})
                    .get("spacing_pool_cells"),
                    "expected_dti_field": build_stats[spec["value"]]["expected_dti_field"],
                    "expected_dti_delta_vs_r0": build_stats[spec["value"]][
                        "expected_dti_delta_vs_r0"
                    ],
                }
                for spec in SPECS
            },
            "report_only_diagnostics": diagnostics,
            "variants": receipts,
            "predictions_are": "MODEL, not scores; no receipt was supplied or submitted",
            "live_change_under_0.01": "no evidence on public chunks per brief",
            "slots_used": 0,
            "submitted": False,
        },
    )

    print(f"R0 exact SHA: zeros={lineage['rebuilt_zeros_sha256']} nan={lineage['rebuilt_nan_sha256']}")
    print(f"Manifest verified: {len(verified)} inputs; canary max={max(canaries.values()):.5f}")
    print(f"Support union: {int(support_union.sum()):,} px {support_parts}")
    for rec in receipts:
        d = rec["report_only_diagnostics"]
        hp = d["holdout_proxy"]
        sgmc = d["sgmc_control"]
        pd = rec["parent_diff"]
        print(
            f"{rec['id']} n={rec['n_dots']:,} removed={pd['n_removed']} added={pd['n_added']} "
            f"moved={pd['pct_changed_moved']:.4f}% symdiff={pd['pct_changed_sym_diff']:.4f}% "
            f"min_dcat={pd['min_dist_catalogue_px']:.4f} "
            f"refill_minNN={rec['refill_min_nn_px']} "
            f"MODEL={rec['model_prediction']['delta_vs_r0']:+.3f} "
            f"fieldDTI={rec['expected_dti_on_four_line_field']['delta_vs_r0']:+.6f} "
            f"holdoutPROXY={hp['dti']:.6f} CI={hp['ci95']} "
            f"SGMC={sgmc['dti']:.6f}"
        )
        print(f"  primary={rec['file_nan']} sha256={rec['sha256']}")
        print(f"  fallback={rec['file_zeros']} sha256={rec['sha256_zeros']}")
        print(f"  note ({rec['form_note_chars']}/140): {rec['form_note']}")
    print(f"REPORT: {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
