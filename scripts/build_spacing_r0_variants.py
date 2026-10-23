#!/usr/bin/env python3
"""Build R0 three controlled, fixed-count AXIS=SPACING variants from exact R0.

This is deliberately the lowest-priority axis in Agent Brief v2.  It tests only
how dots are arranged on the already-recorded H19-5 ridge support:

* ``lattice``: a 4-pixel (400 m) hex-lattice phase preference;
* ``poisson``: deterministic Poisson-disk dart throwing;
* ``alongstrike``: graph-geodesic gap filling along connected H19-5 support.

All three candidates use the same parent, count, legal support, common crowded
parent donors, and forced 3-pixel catalogue-collar repair.  The common repair
is a hard-constraint normalization, not evidence for the SPACING mechanism;
it is reported prominently because it prevents a clean score attribution to
R0.  No portal, leaderboard, credentials, Dropbox, or unpinned input is used.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import heapq
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import numpy as np
from scipy.ndimage import binary_dilation, label as ndi_label
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import grid as grid_mod, holdout as holdout_mod, metric  # noqa: E402
from scripts import build_prune_variants as bpv  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
AXIS = "SPACING"
DATE = "20261023"
SEED = 20261023
COLLAR_PX = 3.0
# sqrt(5) is the tightest integer-grid guard that allows a fixed-N, 3-pixel
# collar-clean field on this finite H19-5 support.  R0's original D2.8 field
# had minimum NN sqrt(8); the feasibility result is recorded in IR-88-50.
MIN_SEPARATION_PX = math.sqrt(5.0)
HEX_LATTICE_PITCH_PX = 4.0
COMMON_CROWDED_DONOR_N = 3_765  # round(10% of R0's 37,654 dots)

SPECS: tuple[dict[str, Any], ...] = (
    {
        "value": "lattice",
        "strategy": "4-pixel hexagonal lattice residual, pinned to the grid origin",
        "prediction": -0.007,
        "prediction_range": [-0.020, 0.006],
        "hypothesis": (
            "A grid-phase control should lose credit because Nevada fault traces change strike, "
            "whereas a global 400 m hex phase preferentially retains raster geometry rather than "
            "the local structural fabric."
        ),
    },
    {
        "value": "poisson",
        "strategy": "seeded Poisson-disk dart throwing on legal un-emitted H19-5 support",
        "prediction": -0.003,
        "prediction_range": [-0.016, 0.010],
        "hypothesis": (
            "Evenly spaced dots can reduce locally redundant kernel overlap, but R0 was already "
            "created by 2.8-pixel geodesic thinning, so a new global Poisson realization is more "
            "likely to discard useful ridge-phase information than to improve it."
        ),
    },
    {
        "value": "alongstrike",
        "strategy": "H19-5-component geodesic gap priority plus the shared separation guard",
        "prediction": 0.002,
        "prediction_range": [-0.012, 0.016],
        "hypothesis": (
            "At a fixed dot budget, prioritising the farthest geodesic gaps on connected ridge "
            "support may extend kernel coverage along a physical fault strand better than R0's "
            "row-major component BFS phase."
        ),
    },
)

LEDGER_FIELDS = (
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256", "sha256_zeros",
    "status", "predicted_change", "predicted_range", "ranking_basis", "receipt_score",
    "receipt_date", "description", "recommendation",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def json_safe(value: Any) -> Any:
    """Convert NumPy/Python non-finite values to portable JSON strings."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
    return value


def load_ledger() -> tuple[list[dict[str, str]], list[str]]:
    path = ROOT / "ledger" / "submissions.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    missing = set(LEDGER_FIELDS) - set(fields)
    if missing:
        raise ValueError(f"ledger schema missing {sorted(missing)}")
    return rows, fields


def remote_ledger_rows() -> list[dict[str, str]]:
    """Read the explicitly fetched origin/main ledger without fetching or scraping."""
    raw = subprocess.check_output(
        ["git", "show", "origin/main:ledger/submissions.csv"], cwd=ROOT
    ).decode("utf-8")
    return list(csv.DictReader(raw.splitlines()))


def preflight(rows: list[dict[str, str]], remote_rows: list[dict[str, str]]) -> None:
    """Fail closed on a repeated (axis, value), hash, or residual local artifact."""
    values = [str(s["value"]) for s in SPECS]
    if len(values) != len(set(values)):
        raise ValueError("SPACING specification repeats a value")

    all_rows = [*rows, *remote_rows]
    repeated = [
        (r.get("parent"), r.get("axis"), r.get("value"), r.get("id"))
        for r in all_rows
        if r.get("axis") == AXIS and r.get("value") in values
    ]
    if repeated:
        raise ValueError(f"AXIS/value already built in local or origin/main ledger: {repeated}")

    # The brief scopes uniqueness across sessions by (AXIS, value), not only parent.
    reused_value = [
        (r.get("axis"), r.get("value"), r.get("id"))
        for r in all_rows
        if r.get("axis") == AXIS and r.get("value") in values
    ]
    if reused_value:
        raise ValueError(f"SPACING value already exists: {reused_value}")

    seen: list[str] = []
    for row in rows:
        seen.extend(x for x in (row.get("sha256"), row.get("sha256_zeros")) if x)
    if len(seen) != len(set(seen)):
        raise ValueError("existing ledger has duplicate primary/fallback SHA-256 values")

    release_dir = ROOT / "releases"
    for value in values:
        pattern = f"{PARENT_ID}-{AXIS}{value}-{DATE}-*"
        leftovers = sorted(release_dir.glob(pattern))
        if leftovers:
            raise FileExistsError(
                f"Refusing to overwrite a pre-existing local artifact for {value}: {leftovers}"
            )


def separation_offsets(min_separation_px: float) -> list[tuple[int, int]]:
    """Integer offsets that must be blocked to enforce distance >= min_separation."""
    if min_separation_px <= 0:
        raise ValueError("minimum separation must be positive")
    radius = int(math.ceil(min_separation_px))
    limit = min_separation_px * min_separation_px
    return [
        (dy, dx)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if dy * dy + dx * dx < limit - 1e-12
    ]


def blocking_structure(min_separation_px: float) -> tuple[np.ndarray, list[tuple[int, int]]]:
    offsets = separation_offsets(min_separation_px)
    radius = int(math.ceil(min_separation_px))
    structure = np.zeros((2 * radius + 1, 2 * radius + 1), dtype=bool)
    for dy, dx in offsets:
        structure[dy + radius, dx + radius] = True
    return structure, offsets


def common_crowded_donors(
    parent: np.ndarray,
    d_catalogue: np.ndarray,
    n_extra: int = COMMON_CROWDED_DONOR_N,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Select one identical geometry-only donor set for every SPACING arm.

    The parent collar is necessarily removed by the global non-PRUNE rule.  To
    make the treatment more than a collar repair, every arm also relocates the
    same 10% subset of legal R0 dots having the shortest nearest-neighbour
    distance.  No fault-likelihood or proxy ranking occurs here.
    """
    legal_parent = np.asarray(parent, dtype=bool) & (d_catalogue >= COLLAR_PX)
    collar = np.asarray(parent, dtype=bool) & ~legal_parent
    points = np.argwhere(legal_parent)
    if len(points) <= n_extra:
        raise ValueError("not enough legal parent dots for common SPACING donors")
    nn = cKDTree(points).query(points, k=2)[0][:, 1]
    # Stable tie breaks prevent scipy/KD-tree traversal details from changing the selection.
    order = np.lexsort((points[:, 1], points[:, 0], nn))
    donor_points = points[order[:n_extra]]
    donors = np.zeros_like(parent, dtype=bool)
    donors[donor_points[:, 0], donor_points[:, 1]] = True
    if int(donors.sum()) != n_extra:
        raise AssertionError("common donor count drifted")
    if np.any(donors & collar):
        raise AssertionError("common crowded donor set includes an already-forced collar removal")
    return donors, {
        "common_collar_removed_n": int(collar.sum()),
        "common_crowded_removed_n": int(donors.sum()),
        "common_crowded_donor_nn_px": {
            "min": round(float(nn[order[:n_extra]].min()), 4),
            "median": round(float(np.median(nn[order[:n_extra]])), 4),
            "max": round(float(nn[order[:n_extra]].max()), 4),
        },
        "parent_legal_n": int(legal_parent.sum()),
    }


def candidate_arrays(
    support_legal: np.ndarray,
    parent: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    candidates = np.asarray(support_legal, dtype=bool) & ~np.asarray(parent, dtype=bool)
    y, x = np.nonzero(candidates)
    if not len(y):
        raise ValueError("no un-emitted legal support candidates")
    return candidates, y.astype(np.int32), x.astype(np.int32)


def hex_lattice_residual(y: np.ndarray, x: np.ndarray, pitch_px: float = HEX_LATTICE_PITCH_PX) -> np.ndarray:
    """Distance from each cell centre to the nearest vertex of a fixed hex lattice."""
    if pitch_px <= 0:
        raise ValueError("hex lattice pitch must be positive")
    xx = np.asarray(x, dtype=np.float64)
    yy = np.asarray(y, dtype=np.float64)
    row_step = math.sqrt(3.0) * pitch_px / 2.0
    row = np.rint(yy / row_step).astype(np.int64)
    residual = np.full(len(xx), np.inf, dtype=np.float64)
    # At most three nearby rows can own the nearest hex vertex.
    for j in (row - 1, row, row + 1):
        vertex_x = np.rint((xx - 0.5 * (j & 1) * pitch_px) / pitch_px) * pitch_px
        vertex_x += 0.5 * (j & 1) * pitch_px
        vertex_y = j * row_step
        residual = np.minimum(residual, np.hypot(xx - vertex_x, yy - vertex_y))
    return residual


def poisson_order(n: int, seed: int = SEED) -> tuple[np.ndarray, dict[str, Any]]:
    return np.random.default_rng(seed + 101).permutation(n), {
        "selector": "seeded uniform dart order; reject candidates inside the separation disk",
        "seed": seed + 101,
    }


def geodesic_distance_on_support(support: np.ndarray, anchors: np.ndarray) -> np.ndarray:
    """Multi-source 8-neighbour Dijkstra distance constrained to binary ridge support."""
    support = np.asarray(support, dtype=bool)
    anchors = np.asarray(anchors, dtype=bool)
    if np.any(anchors & ~support):
        raise ValueError("an anchor is outside support")
    h, w = support.shape
    flat_support = support.ravel()
    dist = np.full(h * w, np.inf, dtype=np.float32)
    heap: list[tuple[float, int]] = []
    for row, col in np.argwhere(anchors):
        idx = int(row * w + col)
        dist[idx] = 0.0
        heap.append((0.0, idx))
    heapq.heapify(heap)
    offsets = [
        (dy, dx, float(math.hypot(dy, dx)))
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if dy or dx
    ]
    while heap:
        current, idx = heapq.heappop(heap)
        # Distances are stored compactly as float32; exact float equality would
        # discard valid diagonal entries after their heap value is rounded.
        if current > float(dist[idx]) + 1e-6:
            continue
        row, col = divmod(idx, w)
        for dy, dx, step in offsets:
            rr, cc = row + dy, col + dx
            if not (0 <= rr < h and 0 <= cc < w):
                continue
            nxt = rr * w + cc
            candidate = current + step
            if flat_support[nxt] and candidate < float(dist[nxt]) - 1e-7:
                dist[nxt] = candidate
                heapq.heappush(heap, (candidate, nxt))
    return dist.reshape(h, w)


def alongstrike_order(
    support_legal: np.ndarray,
    anchors: np.ndarray,
    candidate_y: np.ndarray,
    candidate_x: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any], np.ndarray]:
    """Order cells by ridge-constrained gaps, with long unanchored strands explicit.

    Existing-anchor components use graph distance to their nearest retained R0
    dot.  Components without an anchor receive a bounded priority based only on
    component extent, allowing a large previously unrepresented H19-5 strand to
    enter the fixed budget without using a fault-probability field.
    """
    labels, n_components = ndi_label(support_legal, structure=np.ones((3, 3), dtype=int))
    component_sizes = np.bincount(labels.ravel(), minlength=n_components + 1)
    anchor_counts = np.bincount(labels[anchors], minlength=n_components + 1)
    distance = geodesic_distance_on_support(support_legal, anchors)
    component_at_candidate = labels[candidate_y, candidate_x]
    geodesic = distance[candidate_y, candidate_x].astype(np.float64)
    anchored_component = anchor_counts[component_at_candidate] > 0
    # A size-only priority of at most 8 px for unanchored components: it makes
    # their treatment auditable and never converts their raw H19 membership
    # into a fault-likelihood ranking.
    unanchored_priority = np.minimum(8.0, 2.0 * np.log1p(component_sizes[component_at_candidate]))
    priority = np.where(anchored_component, geodesic, unanchored_priority)
    order = np.lexsort((candidate_x, candidate_y, -priority))
    stats = {
        "selector": "descending graph-geodesic gap; long unanchored-component size fallback",
        "support_components": int(n_components),
        "components_without_retained_anchor": int((anchor_counts[1:] == 0).sum()),
        "candidate_cells_on_previously_unanchored_components": int((~anchored_component).sum()),
        "candidate_geodesic_px": {
            "min": round(float(np.min(geodesic[anchored_component])), 4),
            "median": round(float(np.median(geodesic[anchored_component])), 4),
            "p90": round(float(np.quantile(geodesic[anchored_component], 0.90)), 4),
            "max": round(float(np.max(geodesic[anchored_component])), 4),
        },
    }
    return order, stats, labels


def select_candidates(
    anchor_mask: np.ndarray,
    candidate_y: np.ndarray,
    candidate_x: np.ndarray,
    order: np.ndarray,
    n_select: int,
    min_separation_px: float = MIN_SEPARATION_PX,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Select exactly n cells under the fixed separation guard in supplied order."""
    if n_select <= 0:
        raise ValueError("must select at least one candidate")
    h, w = anchor_mask.shape
    structure, offsets = blocking_structure(min_separation_px)
    blocked = binary_dilation(anchor_mask, structure=structure)
    initially_eligible = int((~blocked[candidate_y, candidate_x]).sum())
    selected = np.zeros_like(anchor_mask, dtype=bool)
    n = 0
    for idx in np.asarray(order, dtype=np.int64):
        row, col = int(candidate_y[idx]), int(candidate_x[idx])
        if blocked[row, col]:
            continue
        selected[row, col] = True
        n += 1
        # The radius is only two pixels here; explicit writes are deterministic
        # and avoid a full-array dilation for every selected dot.
        for dy, dx in offsets:
            rr, cc = row + dy, col + dx
            if 0 <= rr < h and 0 <= cc < w:
                blocked[rr, cc] = True
        if n == n_select:
            break
    if n != n_select:
        raise ValueError(
            f"spacing selector exhausted after {n:,} cells; required {n_select:,}. "
            "Do not relax the pre-registered count or separation silently."
        )
    return selected, {
        "candidate_cells_initially_eligible": initially_eligible,
        "candidate_cells_selected": n,
        "minimum_separation_guard_px": round(float(min_separation_px), 6),
        "blocked_integer_offsets": [[int(dy), int(dx)] for dy, dx in offsets],
    }


def nearest_neighbour_stats(mask: np.ndarray) -> dict[str, float]:
    points = np.argwhere(mask)
    if len(points) < 2:
        raise ValueError("nearest-neighbour statistics need at least two dots")
    d = cKDTree(points).query(points, k=2)[0][:, 1]
    return {
        "min_px": round(float(d.min()), 4),
        "p05_px": round(float(np.quantile(d, 0.05)), 4),
        "median_px": round(float(np.median(d)), 4),
        "mean_px": round(float(d.mean()), 4),
        "p95_px": round(float(np.quantile(d, 0.95)), 4),
    }


def source_geometry_model(mask: np.ndarray, support_legal: np.ndarray, foot: np.ndarray, catalogue: np.ndarray) -> dict[str, float | str]:
    """Exact DTI arithmetic against the parent support, explicitly not a score/proxy."""
    result = metric.dti_binary(mask, support_legal, valid=foot, known=catalogue)
    return {
        "evidence_label": "MODEL",
        "meaning": "Exact DTI against H19-5 source support only; circular geometry diagnostic, not a live score or proxy gate.",
        "dti": round(float(result["dti"]), 6),
        "tp": round(float(result["tp"]), 3),
        "fp": round(float(result["fp"]), 3),
        "truth_pixels": int(result["n_truth"]),
    }


def h19_single_feature_canary(foot: np.ndarray, catalogue: np.ndarray, h19_5: np.ndarray) -> dict[str, Any]:
    """Report-only leakage canary for the single static parent-support feature."""
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)
    positives = folds20[0]["hidden_all"] | folds30[0]["hidden_all"]
    neg_pool = np.flatnonzero(foot & ~catalogue & ~positives)
    rng = np.random.default_rng(SEED)
    neg = rng.choice(neg_pool, size=min(100_000, len(neg_pool)), replace=False)
    pos = np.flatnonzero(positives)
    idx = np.concatenate([pos, neg])
    truth = np.concatenate([np.ones(len(pos), dtype=np.int8), np.zeros(len(neg), dtype=np.int8)])
    auc = float(roc_auc_score(truth, np.asarray(h19_5, dtype=np.float32).ravel()[idx]))
    symmetric_auc = max(auc, 1.0 - auc)
    if symmetric_auc > 0.90:
        raise RuntimeError(
            f"LEAKAGE CANARY TRIPPED for H19-5 support: symmetric AUC={symmetric_auc:.5f} > 0.90"
        )
    return {
        "evidence_label": "REPORT_ONLY_CANARY",
        "feature": "pinned ancestor H19-5 binary support",
        "positive_withheld_catalogue_pixels": int(len(pos)),
        "negative_sample_pixels": int(len(neg)),
        "auc": round(auc, 5),
        "symmetric_auc": round(symmetric_auc, 5),
        "passed": True,
        "threshold": 0.90,
        "note": "A canary is an investigation stop, never a candidate-promotion gate.",
    }


def form_note(spec: dict[str, Any], n_move: int) -> str:
    return (
        f"h33-2-b2; SPACING {spec['value']}, {n_move} relocations, N=37654; "
        f"pred {spec['prediction']:+.3f} MODEL"
    )


def mechanism_card(spec: dict[str, Any], rec: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
    value = str(spec["value"])
    strategy = str(spec["strategy"])
    prediction = float(spec["prediction"])
    lo, hi = map(float, spec["prediction_range"])
    per_strategy = {
        "lattice": (
            "A global lattice is a deliberately non-geologic spacing control: if it matches or beats "
            "the other arms, claimed along-strike benefit is not evidence of actual structural continuity."
        ),
        "poisson": (
            "Poisson-disk placement reduces very short neighbour pairs without inferring a local fault "
            "strike; it isolates generic coverage regularity from geologic line following."
        ),
        "alongstrike": (
            "Graph distance is measured only along connected H19-5 ridge pixels, so the arm spends its "
            "replacement budget first at unrepresented along-support gaps rather than by map-grid phase."
        ),
    }[value]
    return {
        "axis": AXIS,
        "value": value,
        "hypothesis": str(spec["hypothesis"]),
        "mechanism": (
            f"R0 was produced by deterministic component-BFS thinning at 2.8 pixels. {per_strategy} "
            f"This arm uses {strategy}; all arms retain N=37,654 and use the same {stats['n_removed']:,} "
            "R0 removals, so the only arm-to-arm treatment is the spacing ordering of legal replacements."
        ),
        "non_fault_mimic": (
            "Drainage-line pixels, lithologic contacts, pediment margins, and the rasterized orientation "
            "of the H19 detector can form long or regular-looking strings without an unmapped brittle fault."
        ),
        "predicted_sign_size": (
            f"MODEL predicted live delta {prediction:+.3f} versus the R0 CLAIM; plausible band "
            f"[{lo:+.3f},{hi:+.3f}]. Constants were fixed before the successful-run report-only pass, "
            "but a prior serialization failure exposed preliminary diagnostics; see the failure record. "
            "A public live change with magnitude below 0.010 is no evidence."
        ),
        "falsifier": (
            "Against a contemporaneously validated collar-clean control, a live delta <= -0.010 falsifies "
            "the stated spacing mechanism; >= +0.010 supports it. R0 has no receipt, so a one-sided "
            "comparison to its owner-reported CLAIM alone remains provisional."
        ),
        "mandatory_common_normalization": (
            "All arms remove R0's 1,611 dots at d_catalogue <3 px to satisfy the hard non-PRUNE collar "
            "(R0 dots exactly 3 px away are legal and retained), and move the same 3,765 crowded legal donors. "
            "This shared change is a spacing/collar confounder, not a second claimed mechanism."
        ),
        "parent_diff": rec["parent_diff"],
        "spacing": stats,
        "submission_name": rec["id"],
        "form_note": rec["form_note"],
        "report_only_not_gates": [
            "catalogue hide-and-recover PROXY",
            "single-feature leakage canary",
            "SGMC mapped-fault control",
            "H19 support-geometry MODEL",
        ],
    }


def write_preregistration(
    lin: dict[str, Any], common: dict[str, Any], n_move: int, manifest_sha: str, origin_main_sha: str
) -> Path:
    """Write fixed hypotheses/configuration before any proxy or canary computation."""
    payload = {
        "schema": "gems88.spacing-preregistration.v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "git_sha": git_value("rev-parse", "HEAD"),
        "origin_main_sha_checked_before_build": origin_main_sha,
        "manifest_sha256": manifest_sha,
        "parent": {
            "id": PARENT_ID,
            "dots": int(lin["r0"].sum()),
            "zeros_sha256": lin["rebuilt_zeros_sha256"],
            "nan_sha256": lin["rebuilt_nan_sha256"],
            "evidence": "R0 0.2778 is CLAIM, not a receipt",
        },
        "axis": AXIS,
        "axis_selection": (
            "MASS, CONCENTRATION, SNAP, PRUNE, and RELIEF values are already represented in the reconciled "
            "ledger. SPACING has no existing value and is explicitly lowest priority in the brief; TRACKB is "
            "Phase-2 geologist preparation rather than a weekly candidate."
        ),
        "support": "pinned ancestor H19-5 binary ridge support only; no external data or fault-likelihood feature",
        "hard_constraints": {
            "catalogue_mass": 0,
            "minimum_catalogue_distance_px": COLLAR_PX,
            "count_fixed": int(lin["r0"].sum()),
            "seed": SEED,
        },
        "common_normalization": {
            **common,
            "total_parent_dots_relocated": n_move,
            "pct_parent_dots_relocated": round(100.0 * n_move / int(lin["r0"].sum()), 6),
            "minimum_interdot_separation_px": round(MIN_SEPARATION_PX, 6),
            "feasibility_note": (
                "The canonical dot_thin(H19-5 legal support, 2.8 px) run emitted 36,718 dots, below "
                "R0's 37,654. This construction-specific diagnostic is not a proof of a global packing "
                "maximum; the sqrt(5) guard is disclosed rather than silently changing during arm construction."
            ),
        },
        "variants": [
            {
                "value": s["value"],
                "strategy": s["strategy"],
                "predicted_change": f"MODEL:{float(s['prediction']):+.3f}",
                "predicted_range": [float(x) for x in s["prediction_range"]],
                "hypothesis": s["hypothesis"],
            }
            for s in SPECS
        ],
        "report_only_not_gates": [
            "hide-and-recover catalogue PROXY with 95% CI",
            "single static-feature leakage canary",
            "SGMC control",
            "H19 source-support geometry MODEL",
        ],
        "attempt_integrity": {
            "first_attempt_failure_record": "evidence/spacing_r0_first_attempt_failure.json",
            "prediction_constants_unchanged_after_failure": True,
            "caveat": "The durable design record is written before this successful run's diagnostics, but a prior local serialization failure exposed preliminary report-only values. No prediction was revised; do not treat the file as a blind proxy preregistration.",
        },
        "no_submission": True,
    }
    out = ROOT / "registry" / "spacing_r0_preregistration.json"
    out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return out


def write_ledger(existing: list[dict[str, str]], new_rows: list[dict[str, str]], fields: list[str]) -> None:
    rows = [*existing, *new_rows]
    hashes = [r[k] for r in rows for k in ("sha256", "sha256_zeros") if r.get(k)]
    pairs = [(r.get("parent"), r.get("axis"), r.get("value")) for r in rows]
    if len(hashes) != len(set(hashes)):
        raise RuntimeError("ledger SHA-256 uniqueness failed before write")
    if len(pairs) != len(set(pairs)):
        raise RuntimeError("ledger exact (parent, axis, value) uniqueness failed before write")
    with (ROOT / "ledger" / "submissions.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def finalize_existing_interrupted_build() -> int:
    """Finish only the tracked receipts/report after an interrupted final serialization.

    This path is intentionally narrow: it re-verifies pins and exact R0, refuses
    missing/changed candidate receipts, regenerates only their mechanism cards,
    and serializes the already-computed report-only diagnostics.  It never
    changes a candidate TIFF, ledger row, prediction, or portal state.
    """
    verified = bpv.verify_manifest(ROOT / "registry" / "data_manifest.json")
    lin = bpv.rebuild_r0_from_lineage(verified)
    prereg_path = ROOT / "registry" / "spacing_r0_preregistration.json"
    validation_path = ROOT / "evidence" / "spacing_r0_axis_validation.json"
    if not prereg_path.is_file() or not validation_path.is_file():
        raise FileNotFoundError("cannot finalize: preregistration or independent validation is missing")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if not validation.get("gates_all_pass"):
        raise RuntimeError("cannot finalize: independent validation is not all-pass")

    rows, _ = load_ledger()
    ours = [r for r in rows if r.get("parent") == PARENT_ID and r.get("axis") == AXIS]
    by_value = {r["value"]: r for r in ours}
    expected = {str(s["value"]): s for s in SPECS}
    if set(by_value) != set(expected) or len(ours) != len(expected):
        raise RuntimeError("cannot finalize: ledger does not contain exactly this SPACING family")

    cards_path = ROOT / "ledger" / "mechanism_cards.json"
    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    variants: dict[str, Any] = {}
    r0_reference = None
    canary = None
    for value, spec in expected.items():
        row = by_value[value]
        receipt_path = ROOT / "releases" / f"{row['id']}.json"
        if not receipt_path.is_file():
            raise FileNotFoundError(f"cannot finalize: missing receipt {receipt_path}")
        rec = json.loads(receipt_path.read_text(encoding="utf-8"))
        if rec.get("sha256") != row["sha256"] or rec.get("sha256_zeros") != row["sha256_zeros"]:
            raise RuntimeError(f"cannot finalize: receipt/ledger hash mismatch for {row['id']}")
        required = {"spacing", "prediction", "report_only_diagnostics", "r0_reference_diagnostics",
                    "leakage_canary", "source_support_geometry_model"}
        if missing := required - set(rec):
            raise RuntimeError(f"cannot finalize: incomplete receipt {row['id']}: {sorted(missing)}")
        cards[row["id"]] = mechanism_card(spec, rec, rec["spacing"])
        variants[row["id"]] = {
            "value": value,
            "sha256": rec["sha256"],
            "sha256_zeros": rec["sha256_zeros"],
            "prediction": rec["prediction"],
            "spacing": rec["spacing"],
            "report_only": rec["report_only_diagnostics"],
            "source_support_geometry_model": rec["source_support_geometry_model"],
        }
        r0_reference = rec["r0_reference_diagnostics"]
        canary = rec["leakage_canary"]
    assert r0_reference is not None and canary is not None
    cards_path.write_text(json.dumps(json_safe(cards), indent=2, allow_nan=False) + "\n", encoding="utf-8")

    common = prereg["common_normalization"]
    report = {
        "schema": "gems88.spacing-axis-report.v1",
        "date_utc": "2026-10-23",
        "git_sha": git_value("rev-parse", "HEAD"),
        "origin_main_sha_checked_before_build": prereg["origin_main_sha_checked_before_build"],
        "axis": AXIS,
        "parent": {
            "id": PARENT_ID,
            "dots": int(lin["r0"].sum()),
            "zeros_sha256": lin["rebuilt_zeros_sha256"],
            "nan_sha256": lin["rebuilt_nan_sha256"],
            "score": "CLAIM:0.2778 (no receipt)",
        },
        "manifest_inputs_verified": len(verified),
        "preregistration": str(prereg_path.relative_to(ROOT)),
        "common_normalization": {
            **common,
            "canonical_dot_thin_2p8_count_on_legal_support": 36_718,
            "feasibility_interpretation_correction": (
                "The 36,718 count is from the canonical dot_thin construction, not a proof of a global packing maximum."
            ),
            "actual_minimum_separation_guard_px": round(MIN_SEPARATION_PX, 6),
        },
        "leakage_canary": canary,
        "independent_validation": validation,
        "variants": variants,
        "r0_report_only_reference": r0_reference,
        "evidence_labels": {
            "r0_claim": "CLAIM",
            "predicted_change": "MODEL",
            "source_support_geometry": "MODEL",
            "hide_recover_and_sgmc": "PROXY",
            "leakage_canary": "REPORT_ONLY_CANARY",
        },
        "build_integrity": {
            "finalized_from_interrupted_report_serialization": True,
            "failure_record": "evidence/spacing_r0_first_attempt_failure.json",
            "no_candidate_or_ledger_change_during_finalization": True,
        },
        "no_submission": True,
    }
    report_path = ROOT / "evidence" / "spacing_r0_axis_report.json"
    report_path.write_text(json.dumps(json_safe(report), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"finalized": str(report_path.relative_to(ROOT)), "variants": sorted(variants)}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="build masks and invariants without writing artifacts")
    parser.add_argument("--finalize-existing", action="store_true", help="finish an interrupted final report without changing candidates")
    args = parser.parse_args()
    if args.finalize_existing:
        if args.dry_run:
            raise ValueError("--dry-run and --finalize-existing are mutually exclusive")
        return finalize_existing_interrupted_build()
    started = time.time()

    print("[1/7] Verifying SHA-256 manifest pins and rebuilding exact R0...")
    verified = bpv.verify_manifest(ROOT / "registry" / "data_manifest.json")
    lin = bpv.rebuild_r0_from_lineage(verified)
    r0 = lin["r0"]
    foot = lin["foot"]
    catalogue = lin["catalogue"]
    d_catalogue = lin["d_cat"]
    h19_5 = lin["h19_5"]
    print(f"      {len(verified)} pins OK; R0={int(r0.sum()):,}; both recorded parent SHA-256 values match.")

    print("[2/7] Checking local and explicitly fetched origin/main ledger for new SPACING values...")
    existing_rows, fields = load_ledger()
    origin_sha = git_value("rev-parse", "origin/main")
    remote_rows = remote_ledger_rows()
    preflight(existing_rows, remote_rows)
    print(f"      local={len(existing_rows)} rows; origin/main={origin_sha[:12]}; no SPACING value/hash collision.")

    support_legal = h19_5 & foot & ~catalogue & (d_catalogue >= COLLAR_PX)
    donors, common = common_crowded_donors(r0, d_catalogue)
    collar = r0 & (d_catalogue < COLLAR_PX)
    anchors = r0 & ~collar & ~donors
    n_move = int(collar.sum() + donors.sum())
    candidates, cy, cx = candidate_arrays(support_legal, r0)
    if int(anchors.sum()) + n_move != int(r0.sum()):
        raise AssertionError("fixed-count common-normalization invariant failed")
    print(
        f"[3/7] Common spacing treatment: remove collar={int(collar.sum()):,} + crowded={int(donors.sum()):,}; "
        f"add={n_move:,}; support candidates={int(candidates.sum()):,}."
    )

    print("[4/7] Selecting matched-count lattice, Poisson-disk, and along-strike placements...")
    lattice_residual = hex_lattice_residual(cy, cx)
    order_lattice = np.lexsort((cx, cy, lattice_residual))
    order_poisson, poisson_detail = poisson_order(len(cy), SEED)
    order_along, along_detail, support_labels = alongstrike_order(support_legal, anchors, cy, cx)
    orders = {
        "lattice": (order_lattice, {
            "selector": "ascending distance to a fixed 4-pixel hex-lattice vertex",
            "hex_lattice_pitch_px": HEX_LATTICE_PITCH_PX,
            "candidate_lattice_residual_px": {
                "median": round(float(np.median(lattice_residual)), 4),
                "p90": round(float(np.quantile(lattice_residual, 0.90)), 4),
            },
        }),
        "poisson": (order_poisson, poisson_detail),
        "alongstrike": (order_along, along_detail),
    }
    masks: dict[str, np.ndarray] = {}
    stats_by_value: dict[str, dict[str, Any]] = {}
    common_removed = collar | donors
    for spec in SPECS:
        value = str(spec["value"])
        addition, selection = select_candidates(anchors, cy, cx, orders[value][0], n_move)
        out = anchors | addition
        if int(out.sum()) != int(r0.sum()):
            raise AssertionError(f"{value}: count changed")
        if not np.array_equal(r0 & ~out, common_removed):
            raise AssertionError(f"{value}: removal set differs from common treatment")
        if int((out & ~r0).sum()) != n_move or np.any(addition & r0):
            raise AssertionError(f"{value}: parent-difference invariant failed")
        if np.any(out & ~support_legal) or float(d_catalogue[out].min()) < COLLAR_PX:
            raise AssertionError(f"{value}: illegal support/catalogue collar output")
        nn = nearest_neighbour_stats(out)
        if nn["min_px"] + 1e-4 < MIN_SEPARATION_PX:
            raise AssertionError(f"{value}: separation guard did not survive selection")
        added_labels = support_labels[addition]
        component_anchor_counts = np.bincount(support_labels[anchors], minlength=int(support_labels.max()) + 1)
        stats_by_value[value] = {
            "strategy": spec["strategy"],
            "n_parent": int(r0.sum()),
            "n_removed": int((r0 & ~out).sum()),
            "n_added": int((out & ~r0).sum()),
            "pct_changed_moved": round(100.0 * int((r0 & ~out).sum()) / int(r0.sum()), 6),
            "min_catalogue_distance_px": round(float(d_catalogue[out].min()), 4),
            "common_normalization": common,
            "selection": {**orders[value][1], **selection},
            "nearest_neighbour_after_px": nn,
            "nearest_neighbour_r0_px": nearest_neighbour_stats(r0),
            "added_on_previously_unanchored_components": int((component_anchor_counts[added_labels] == 0).sum()),
            "added_component_count": int(np.unique(added_labels).size),
        }
        masks[value] = out
        print(
            f"      {value}: N={int(out.sum()):,}; changed={stats_by_value[value]['pct_changed_moved']:.3f}%; "
            f"min NN={nn['min_px']:.4f}; min d_catalogue={stats_by_value[value]['min_catalogue_distance_px']:.4f}."
        )
    del support_labels

    if args.dry_run:
        print("DRY RUN PASS: no preregistration, releases, ledger, cards, or diagnostics written.")
        return 0

    print("[5/7] Writing pre-registration before report-only diagnostics...")
    prereg_path = write_preregistration(
        lin,
        common,
        n_move,
        sha256_file(ROOT / "registry" / "data_manifest.json"),
        origin_sha,
    )

    existing_shas = {
        value for row in existing_rows for value in (row.get("sha256"), row.get("sha256_zeros")) if value
    }
    receipts: dict[str, dict[str, Any]] = {}
    for spec in SPECS:
        value = str(spec["value"])
        rec = bpv.write_and_verify_variant(
            mask=masks[value],
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=ROOT / "releases",
            parent_mask=r0,
            axis=AXIS,
            value=value,
            note_template=form_note(spec, n_move),
            existing_shas=existing_shas,
            parent_id=PARENT_ID,
            parent_sha_zeros=lin["rebuilt_zeros_sha256"],
            parent_sha_nan=lin["rebuilt_nan_sha256"],
            date=DATE,
            min_catalogue_px=COLLAR_PX,
        )
        existing_shas.update((rec["sha256"], rec["sha256_zeros"]))
        receipts[value] = rec

    print("[6/7] Running independent disk validator and report-only instruments...")
    validation_path = ROOT / "evidence" / "spacing_r0_axis_validation.json"
    all_paths = [
        p
        for spec in SPECS
        for p in (receipts[str(spec["value"])]["file_nan"], receipts[str(spec["value"])]["file_zeros"])
    ]
    subprocess.run(
        [sys.executable, "scripts/validate_variant.py", *all_paths, "--out", str(validation_path)],
        cwd=ROOT,
        check=True,
    )
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if not validation["gates_all_pass"]:
        raise RuntimeError("independent variant validator did not pass")

    # These are explicitly report-only.  They run after preregistration and can
    # neither approve nor reject a candidate.
    canary = h19_single_feature_canary(foot, catalogue, h19_5)
    arms = {PARENT_ID: r0, **{receipts[v]["id"]: masks[v] for v in masks}}
    report_only = bpv.evaluate_report_only_instruments(
        arms=arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )
    geometry_models = {
        value: source_geometry_model(masks[value], support_legal, foot, catalogue)
        for value in masks
    }

    cards_path = ROOT / "ledger" / "mechanism_cards.json"
    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    new_rows: list[dict[str, str]] = []
    for spec in SPECS:
        value = str(spec["value"])
        rec = receipts[value]
        rec["spacing"] = stats_by_value[value]
        rec["prediction"] = {
            "evidence_label": "MODEL",
            "delta_vs_r0_claim": float(spec["prediction"]),
            "range": [float(x) for x in spec["prediction_range"]],
            "fixed_before_successful_run_report_only_diagnostics": True,
            "unchanged_after_prior_serialization_failure": True,
        }
        rec["preregistration"] = str(prereg_path.relative_to(ROOT))
        rec["independent_validation"] = str(validation_path.relative_to(ROOT))
        rec["report_only_diagnostics"] = report_only[rec["id"]]
        rec["r0_reference_diagnostics"] = report_only[PARENT_ID]
        rec["leakage_canary"] = canary
        rec["source_support_geometry_model"] = geometry_models[value]
        rec["disposition"] = (
            "HOLD: lowest-priority geometry experiment; common collar repair and lowered minimum spacing "
            "prevent a clean R0 attribution. It is not a recommended weekly-slot candidate without a fresh "
            "human decision and a >=0.010 receipt-backed effect."
        )
        receipt_path = ROOT / f"releases/{rec['id']}.json"
        receipt_path.write_text(json.dumps(rec, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        cards[rec["id"]] = mechanism_card(spec, rec, stats_by_value[value])
        new_rows.append({
            "id": rec["id"],
            "parent": PARENT_ID,
            "axis": AXIS,
            "value": value,
            "n_dots": str(rec["n_dots"]),
            "pct_changed": f"{stats_by_value[value]['pct_changed_moved']:.6f}",
            "sha256": rec["sha256"],
            "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT",
            "predicted_change": f"MODEL:{float(spec['prediction']):+.3f}",
            "predicted_range": f"[{float(spec['prediction_range'][0]):+.3f},{float(spec['prediction_range'][1]):+.3f}]",
            "ranking_basis": "geometry-only spacing order; no fault-likelihood ranking; exact source-support DTI is report-only MODEL",
            "receipt_score": "",
            "receipt_date": "",
            "description": (
                f"{value}: move the same {n_move} R0 dots ({int(collar.sum()):,} forced <3 px collar + "
                f"{int(donors.sum()):,} crowded donors) to legal H19-5 support under {spec['strategy']}; N fixed."
            ),
            "recommendation": "HOLD: SPACING is lowest priority and collar/spacing normalization confounds R0 attribution; not a weekly-slot recommendation.",
        })

    write_ledger(existing_rows, new_rows, fields)
    cards_path.write_text(json.dumps(cards, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    report = {
        "schema": "gems88.spacing-axis-report.v1",
        "date_utc": "2026-10-23",
        "git_sha": git_value("rev-parse", "HEAD"),
        "origin_main_sha_checked_before_build": origin_sha,
        "axis": AXIS,
        "parent": {
            "id": PARENT_ID,
            "dots": int(r0.sum()),
            "zeros_sha256": lin["rebuilt_zeros_sha256"],
            "nan_sha256": lin["rebuilt_nan_sha256"],
            "score": "CLAIM:0.2778 (no receipt)",
        },
        "manifest_inputs_verified": len(verified),
        "preregistration": str(prereg_path.relative_to(ROOT)),
        "common_normalization": {
            **common,
            "total_relocated": n_move,
            "pct_relocated": round(100.0 * n_move / int(r0.sum()), 6),
            "canonical_dot_thin_2p8_count_on_legal_support": 36_718,
            "feasibility_interpretation_correction": (
                "The 36,718 count is from the canonical dot_thin construction, not a proof of a global packing maximum."
            ),
            "actual_minimum_separation_guard_px": round(MIN_SEPARATION_PX, 6),
        },
        "leakage_canary": canary,
        "independent_validation": validation,
        "variants": {
            receipts[value]["id"]: {
                "value": value,
                "sha256": receipts[value]["sha256"],
                "sha256_zeros": receipts[value]["sha256_zeros"],
                "prediction": receipts[value]["prediction"],
                "spacing": stats_by_value[value],
                "report_only": report_only[receipts[value]["id"]],
                "source_support_geometry_model": geometry_models[value],
            }
            for value in receipts
        },
        "r0_report_only_reference": report_only[PARENT_ID],
        "evidence_labels": {
            "r0_claim": "CLAIM",
            "predicted_change": "MODEL",
            "source_support_geometry": "MODEL",
            "hide_recover_and_sgmc": "PROXY",
            "leakage_canary": "REPORT_ONLY_CANARY",
        },
        "no_submission": True,
        "elapsed_seconds": round(time.time() - started, 2),
    }
    report_path = ROOT / "evidence" / "spacing_r0_axis_report.json"
    report_path.write_text(json.dumps(json_safe(report), indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print("[7/7] Built and independently re-read three local-only candidates:")
    for spec in SPECS:
        rec = receipts[str(spec["value"])]
        diag = report_only[rec["id"]]
        print(
            f"      {rec['id']} | MODEL {float(spec['prediction']):+.3f} | "
            f"PROXY SGMC={diag['sgmc_control']['dti']:.6f} | "
            f"hide/recover={diag['holdout_proxy']['dti']:.6f}"
        )
    print(f"      report={report_path.relative_to(ROOT)}; validation={validation_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
