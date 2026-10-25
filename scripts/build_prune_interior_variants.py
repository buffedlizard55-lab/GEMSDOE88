#!/usr/bin/env python3
"""Build a fixed-count, exact-marginal PRUNE *interior annulus* bracket from byte-exact R0.

Context (why this family exists)
--------------------------------
R0 = h33-h33-2-b2 already clears every catalogue pixel within 2 px (200 m). The
already-built PRUNE sweep samples collars at 1, 3, 3.2, 3.7, 4, 4.3 px but leaves
the 2-3 px annulus -- one triangular-kernel radius (R = 300 m = 3 px) immediately
outside R0's collar -- completely unsampled: R0 itself is the 2 px point and
PRUNEp3px (= R1) jumps straight to 3 px. Pixel-centre Euclidean distances inside
that annulus take only three values, so it decomposes exactly into three natural
sub-bands (counts on R0):

    sqrt(5) ~= 2.2361 px (224 m):  941 dots
    sqrt(8) ~= 2.8284 px (283 m):  670 dots (cumulative 1,611)
    3.0000 px          (300 m):  560 dots (cumulative 2,171 = the full R1 purge)

This script builds the two unbuilt interior treatments (2.236 px, 2.828 px) plus
one new upper-bracket point (5 px / 500 m) extending the measured descending limb
beyond p4.3px (430 m). Every output is a global catalogue-distance treatment only:
remove R0 dots within the stated collar, hold N = 37,654, and refill one-for-one
from the original H19-5 support outside the collar with the shared exact iterative
expected-DTI marginal solver on one fixed, label-free four-line physical field.
No region-specific selection, leaderboard access, submission, or score tuning.

PRUNE is the sole Brief v2 section 4.4 exception to the >= 3 px non-PRUNE clearance
rule, so the two interior arms legally retain dots at 2.828 px / 3.0 px; their
minimum catalogue distance is asserted to lie strictly outside their own collar.

Run from the repository root after the manifest-pinned inputs have been restored:
    .venv/bin/python scripts/build_prune_interior_variants.py
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
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from scripts import build_prune_variants as bpv  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
AXIS = "PRUNE"
DATE = "20261024"
N_DOTS = 37_654
NO_EVIDENCE_BAND = 0.01
MANIFEST = ROOT / "registry" / "data_manifest.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS_PATH = ROOT / "ledger" / "mechanism_cards.json"
RELEASES = ROOT / "releases"
REPORT_PATH = ROOT / "evidence" / "prune_interior_report.json"
PREREG_PATH = ROOT / "registry" / "prune_interior_preregistration.json"

SQRT5 = math.sqrt(5.0)   # 2.2360679... px = 223.6 m, innermost annulus band
SQRT8 = math.sqrt(8.0)   # 2.8284271... px = 282.8 m, outer annulus band

# Predictions are MODEL projections frozen before any proxy/canary runs.
# Interior arms: linear-in-removed-count interpolation between R0 (0 removals,
# delta 0) and PRUNEp3px (2,171 removals, MODEL +0.005), because inside the
# (2, 3] px annulus the only changed treatment is the fraction purged and the
# refill uses the identical solver/field.  p5px: linear extrapolation of the
# measured descending limb through p4px (3,825 removed, -0.009) and p4.3px
# (4,488 removed, -0.013); explicitly an out-of-bracket extrapolation.
SPECS: tuple[dict[str, Any], ...] = (
    {
        "value": "p2.236px",
        "threshold_px": SQRT5,
        "threshold_m": 100.0 * SQRT5,
        "band": "inner annulus fringe only (d_cat = sqrt(5) px)",
        "prediction": 0.002,
        "prediction_range": [-0.004, 0.008],
        "prediction_basis": (
            "Linear interpolation R0(0 removed -> 0.000) to PRUNEp3px (2,171 removed -> "
            "MODEL +0.005): 0.005 * 941 / 2,171 = +0.0022, rounded +0.002."
        ),
        "hypothesis": (
            "The 941 R0 dots on the innermost catalogue fringe (224 m, one to two pixel "
            "centres beyond R0's 200 m collar) are dominated by catalogue-parallel "
            "potential-field side-lobes rather than unmapped fault tips; purging only this "
            "fringe and refilling on independent H19-5 ridges recovers a small positive "
            "share of the full 300 m purge's benefit while disturbing under 2.5% of dots."
        ),
    },
    {
        "value": "p2.828px",
        "threshold_px": SQRT8,
        "threshold_m": 100.0 * SQRT8,
        "band": "inner + outer annulus fringe (d_cat <= sqrt(8) px); leaves the 3.0 px ring",
        "prediction": 0.004,
        "prediction_range": [-0.002, 0.010],
        "prediction_basis": (
            "Linear interpolation R0 to PRUNEp3px: 0.005 * 1,611 / 2,171 = +0.0037, "
            "rounded +0.004."
        ),
        "hypothesis": (
            "Purging both sub-kernel-radius fringes (1,611 dots, 224-283 m) but retaining "
            "the 560 dots that sit at exactly one kernel radius (300 m) captures most of "
            "R1's annulus treatment; if annulus toxicity is uniform with distance, this arm "
            "should sit close to R1's MODEL +0.005 at a smaller edit, whereas toxicity "
            "concentrated on the 300 m ring would leave it close to R0."
        ),
    },
    {
        "value": "p5px",
        "threshold_px": 5.0,
        "threshold_m": 500.0,
        "band": "upper collar bracket beyond the measured p4.3px (430 m) point",
        "prediction": -0.020,
        "prediction_range": [-0.040, 0.002],
        "prediction_basis": (
            "Linear extrapolation of the descending limb through p4px (3,825 removed, "
            "-0.009) and p4.3px (4,488 removed, -0.013): slope -6.03e-6 per dot; at 5,637 "
            "removed -> -0.0199, rounded -0.020. Extrapolation outside the measured bracket; "
            "range widened accordingly."
        ),
        "hypothesis": (
            "A 500 m collar (1.67 kernel radii; beyond the 400 m GeoDAWN flight-line "
            "spacing) removes genuine relay/step-over splays and antithetic strands of the "
            "known systems -- the 'new geometry of existing systems' the organizer includes "
            "in new-fault truth -- faster than exact-marginal refill can replace them, so "
            "the live DTI loss deepens the measured p3.7 -> p4.3 descent."
        ),
    },
)

FIELD_SOURCES = (
    "label-free four-line physical field from scripts/build_prune_variants.py: "
    "surface scarp, subsurface potential-field, strain/seismic, and hydrothermal lines; "
    "all single-channel canaries must be <= 0.90 before the field is used"
)
RANKING_BASIS = (
    "Exact iterative marginal expected-DTI gain via vendor/gems57/metric.py and "
    "scripts/build_prune_variants.py::select_exact_marginal_dti_add; candidate pool is "
    "the original H19-5 binary support outside the threshold; fixed label-free physical "
    "field across all variants; no isolated-pixel shortcut or random tie score"
)
REFERENCES = [
    {
        "url": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
        "claim": "The organizer describes pixel-exact masking of known USGS/INGENIOUS pixels; pixels adjacent to known traces are scored normally.",
    },
    {
        "url": "https://community.drivendata.org/t/where-do-you-draw-the-line/11536",
        "claim": "New-fault truth includes newly mapped geometry of existing systems and may occur within 300 m of known traces; the key collar-loss confounder.",
    },
    {
        "url": "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7",
        "claim": "GeoDAWN Area 2 was flown at 400 m line spacing, 150-200 m above terrain; lineament positions are uncertain by about the 300 m kernel radius.",
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
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
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
        raise ValueError("The interior PRUNE bracket contains repeated values")
    pairs = {(row.get("parent"), row.get("axis"), row.get("value")) for row in rows}
    collisions = [(PARENT_ID, AXIS, value) for value in values if (PARENT_ID, AXIS, value) in pairs]
    if collisions:
        raise ValueError(f"Repeated (parent, axis, value) pair(s) in ledger: {collisions}")
    for spec in SPECS:
        prefix = f"{PARENT_ID}-{AXIS}{spec['value']}-{DATE}"
        if any(RELEASES.glob(f"{prefix}-*")):
            raise FileExistsError(f"Artifacts for this value already exist: {prefix}-*")


def ledger_hashes(rows: list[dict[str, str]]) -> set[str]:
    result = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}
    for row in rows:
        result.update(
            value for value in (row.get("sha256"), row.get("sha256_zeros")) if value
        )
    return result


def preregistration_payload(parent: dict[str, Any], manifest_sha: str) -> dict[str, Any]:
    anchors = {}
    for row in load_ledger()[0]:
        if row.get("parent") == PARENT_ID and row.get("axis") == AXIS and row.get("value") in {
            "p3px", "p4px", "p4.3px"
        }:
            anchors[row["value"]] = {
                "predicted_change": row.get("predicted_change"),
                "predicted_range": row.get("predicted_range"),
                "evidence_class": "MODEL (prior registry projection, not a live score)",
            }
    return {
        "schema": "gems88.prune-interior-annulus-preregistration.v1",
        "created_utc": utc_now(),
        "parent": {
            "id": PARENT_ID,
            "n_dots": int(parent["r0"].sum()),
            "zeros_sha256": parent["rebuilt_zeros_sha256"],
            "nan_sha256": parent["rebuilt_nan_sha256"],
            "evidence_class": "REBUILT parent; historical 0.2778 remains CLAIM",
        },
        "axis": AXIS,
        "axis_selection": (
            "The agent selected its own axis per the brief. The PRUNE 2-3 px annulus is the "
            "only unsampled interior of the collar curve (R0 is the 2 px point; PRUNEp3px "
            "jumps to 3 px), and PRUNE is the section 4.4 exception under which sub-3 px "
            "collars are gate-legal. Every other brief axis already has multiple R0/R1 arms."
        ),
        "annulus_geometry": {
            "distinct_pixel_centre_distances_px": [2.2360679, 2.8284271, 3.0],
            "r0_dots_per_band": {"2.2361": 941, "2.8284": 670, "3.0": 560},
            "r0_dots_in_annulus_2_to_3": 2171,
            "kernel_radius_px": 3.0,
        },
        "manifest_sha256": manifest_sha,
        "git_sha": git_value("rev-parse", "HEAD"),
        "origin_main_sha_checked_before_build": git_value("rev-parse", "origin/main"),
        "prior_model_anchors": anchors,
        "predicted_no_evidence_band": NO_EVIDENCE_BAND,
        "predictions_are": "MODEL, not scores; any live absolute delta < 0.01 is no evidence",
        "treatment": (
            "For each value, remove every R0 dot at d_catalogue <= threshold_px; hold "
            "N=37,654; add the same number from the original H19-5 support at "
            "d_catalogue > threshold_px using exact greedy expected-DTI marginal gain. "
            "All other settings and the fixed physical-field ranking recipe are unchanged."
        ),
        "refill_ranking_basis": RANKING_BASIS,
        "physical_field": FIELD_SOURCES,
        "variants": [
            {
                "value": spec["value"],
                "threshold_px": spec["threshold_px"],
                "threshold_m": spec["threshold_m"],
                "band": spec["band"],
                "predicted_change": f"MODEL:{spec['prediction']:+.3f}",
                "predicted_range": spec["prediction_range"],
                "prediction_basis": spec["prediction_basis"],
                "hypothesis": spec["hypothesis"],
            }
            for spec in SPECS
        ],
        "report_only_not_gates": [
            "catalogue hide-and-recover PROXY with withheld-positive count and 95% CI",
            "single-feature leakage canary",
            "blind SGMC control",
            "10 km and 12 km dot-density CV",
        ],
        "no_submission": True,
    }


def prune_at_threshold(
    parent: np.ndarray,
    source_support: np.ndarray,
    d_catalogue: np.ndarray,
    expected_fault_weight: np.ndarray,
    threshold_px: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Remove the collar, then exact-marginal refill to the unchanged parent count."""
    if threshold_px <= 0:
        raise ValueError("PRUNE threshold must be positive")
    survivors = np.asarray(parent, dtype=bool) & (d_catalogue > threshold_px)
    removed_n = int(np.asarray(parent, dtype=bool).sum() - survivors.sum())
    candidate_pool = (
        np.asarray(source_support, dtype=bool)
        & ~survivors
        & (d_catalogue > threshold_px)
    )
    if int(candidate_pool.sum()) < removed_n:
        raise ValueError(
            f"Only {int(candidate_pool.sum())} legal refill cells for {removed_n} removals "
            f"at threshold {threshold_px} px"
        )
    candidate = bpv.select_exact_marginal_dti_add(
        base_mask=survivors,
        cand_mask=candidate_pool,
        w=expected_fault_weight,
        n_add=removed_n,
    )
    if int(candidate.sum()) != int(parent.sum()):
        raise AssertionError("Fixed-mass PRUNE invariant failed")
    if np.any(candidate & (d_catalogue <= threshold_px)):
        raise AssertionError("Output contains a dot inside its PRUNE collar")
    added_n = int((candidate & ~parent).sum())
    actual_removed_n = int((parent & ~candidate).sum())
    if added_n != removed_n or actual_removed_n != removed_n:
        raise AssertionError(
            f"Parent difference not a one-for-one relocation: added={added_n}, "
            f"removed={actual_removed_n}, expected={removed_n}"
        )
    pct_moved = 100.0 * actual_removed_n / int(parent.sum())
    if not 1.0 <= pct_moved <= 50.0:
        raise ValueError(f"Changed fraction {pct_moved:.5f}% is outside 1-50%")
    min_d = float(d_catalogue[candidate].min())
    if not min_d > threshold_px:
        raise AssertionError(f"min d_cat {min_d} not strictly outside collar {threshold_px}")
    return candidate, {
        "threshold_px": float(threshold_px),
        "threshold_m": float(threshold_px * 100.0),
        "n_removed": actual_removed_n,
        "n_added": added_n,
        "n_refill_candidates": int(candidate_pool.sum()),
        "pct_changed_moved": pct_moved,
        "pct_changed_symmetric_difference": 200.0 * actual_removed_n / int(parent.sum()),
        "min_catalogue_distance_px": min_d,
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


def build_card(spec: dict[str, Any], stats: dict[str, Any], rec: dict[str, Any], nn: dict[str, Any]) -> dict[str, Any]:
    threshold = float(spec["threshold_px"])
    point = float(spec["prediction"])
    lo, hi = map(float, spec["prediction_range"])
    interior = threshold < 3.0
    return {
        "axis": AXIS,
        "value": spec["value"],
        "threshold_px": threshold,
        "threshold_m": float(spec["threshold_m"]),
        "hypothesis": spec["hypothesis"],
        "mechanism": (
            "Known USGS/INGENIOUS pixels are masked pixel-exactly but adjacent pixels are "
            "scored normally, and the organizer allows new-fault truth (including new "
            "geometry of existing systems) within 300 m of a known trace. At constant "
            f"N=37,654 this arm removes {stats['n_removed']:,} R0 dots through "
            f"{threshold*100:.0f} m and refills the same count on the original H19-5 ridge "
            "support strictly outside the collar. Each addition is the exact iterative "
            "expected-DTI marginal maximum on one fixed label-free four-line physical field "
            "(surface scarp, potential-field edge, strain/seismic, hydrothermal). The 300 m "
            "triangular kernel and the ~400 m GeoDAWN line spacing make the 200-300 m annulus "
            "the positional-uncertainty band: this bracket measures whether catalogue-flank "
            "dots there behave as side-lobe false positives or as real near-trace splays."
            if interior else
            "At 500 m the collar extends to 1.67 kernel radii, beyond the 400 m GeoDAWN line "
            f"spacing. The same fixed-count recipe removes {stats['n_removed']:,} R0 dots and "
            "refills on H19-5 ridges outside the collar; the mechanism question is whether "
            "over-collaring deletes genuine relay/step-over strands faster than the exact "
            "marginal solver can replace their credit."
        ),
        "non_fault_mimic": (
            "Long-wavelength magnetic/gravity edge-response side-lobes and lithologic contacts "
            "parallel to mapped faults, pediment and alluvial-fan margins, wave-cut shoreline "
            "breaks, and anthropogenic LiDAR scarps (roads, landslides) can all place ridge "
            "pixels within one kernel radius of a catalogue trace without any new fault slip. "
            "Conversely, a true antithetic splay, relay ramp or tip of the known system can lie "
            "inside the removed collar; the organizer explicitly allows new-fault truth within "
            "300 m of known traces, so every removed dot is a real credit-risk."
        ),
        "predicted_sign_size": (
            f"MODEL predicted live delta {point:+.3f} vs R0, plausible range [{lo:+.3f},{hi:+.3f}]. "
            f"{spec['prediction_basis']} It is a projection, not a receipt or PROXY. Treat "
            "|live delta| < 0.01 as no evidence on public chunks."
        ),
        "falsifier": (
            "A same-entity live receipt >= +0.01 vs R0 supports the side-lobe-purge reading at "
            "this collar; a receipt <= -0.01 falsifies it and shows net fault truth was removed. "
            "A |delta| < 0.01 is inconclusive. The three arms form a nested dose sequence "
            "(2.236 -> 2.828 -> 3.0 px = existing R1, then 5.0 px): a non-monotone interior "
            "sequence falsifies the uniform-annulus-toxicity model, and a 5 px arm that does "
            "not deepen the p3.7 -> p4.3 descent falsifies the over-collaring extrapolation."
        ),
        "fixed_count": N_DOTS,
        "parent_diff": rec["parent_diff"],
        "ranking_basis": RANKING_BASIS,
        "four_line_field": FIELD_SOURCES,
        "nearest_neighbour_stats": nn,
        "spacing_confounded_not_optimized": True,
        "report_only_not_gates": [
            "hide-and-recover catalogue PROXY",
            "single-feature leakage canary",
            "blind SGMC control",
        ],
        "references": REFERENCES,
        "submission_name": rec["id"],
        "form_note": rec["form_note"],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    # The first two gates are fail-closed. Do not build a candidate from an
    # unpinned input or an approximate parent.
    rows, ledger_fields = load_ledger()
    preflight_pairs(rows)
    verified = bpv.verify_manifest(MANIFEST)
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot = lineage["foot"]
    catalogue = lineage["catalogue"]
    d_catalogue = lineage["d_cat"]
    parent = lineage["r0"]
    source_support = lineage["h19_5"]
    if int(parent.sum()) != N_DOTS:
        raise RuntimeError(f"Unexpected R0 dot count: {int(parent.sum())}")
    if lineage["rebuilt_zeros_sha256"] != bpv.PARENT_SHA_ZEROS or lineage["rebuilt_nan_sha256"] != bpv.PARENT_SHA_NAN:
        raise RuntimeError("STOP: R0 rebuild does not byte-match the pinned parent")
    if np.any(parent & catalogue) or int((d_catalogue[parent] <= 2.0).sum()) != 0:
        raise RuntimeError("STOP: R0 failed its recorded zero-catalogue/2 px geometry")

    # Freeze the protocol and predictions before running canaries, holdout, or SGMC.
    manifest_sha = sha256_path(MANIFEST)
    parent_summary = {
        "r0": parent,
        "rebuilt_zeros_sha256": lineage["rebuilt_zeros_sha256"],
        "rebuilt_nan_sha256": lineage["rebuilt_nan_sha256"],
    }
    prereg = preregistration_payload(parent_summary, manifest_sha)
    write_json(PREREG_PATH, prereg)

    # One fixed field/ranking recipe is shared by all three collar arms.
    expected_fault_weight, canaries = bpv.build_physical_field_and_canaries(
        verified=verified,
        foot=foot,
        catalogue=catalogue,
        h19_5=source_support,
    )
    if not canaries or max(canaries.values()) > 0.90:
        raise RuntimeError(f"LEAKAGE CANARY FAILURE: {canaries}")

    candidates: dict[str, np.ndarray] = {}
    build_stats: dict[str, dict[str, Any]] = {}
    for spec in SPECS:
        value = str(spec["value"])
        key = f"{PARENT_ID}-{AXIS}{value}"
        candidate, stats = prune_at_threshold(
            parent=parent,
            source_support=source_support,
            d_catalogue=d_catalogue,
            expected_fault_weight=expected_fault_weight,
            threshold_px=float(spec["threshold_px"]),
        )
        if int((candidate & catalogue).sum()) != 0:
            raise RuntimeError(f"Non-zero catalogue mass in {value}")
        candidates[key] = candidate
        build_stats[value] = stats

    # REPORT-ONLY diagnostics are run globally and are never used to choose dots.
    arms = {PARENT_ID: parent, **candidates}
    diagnostics = bpv.evaluate_report_only_instruments(
        arms=arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
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
        note = (
            f"R0 {PARENT_ID}; PRUNE <= {spec['threshold_px']:.4g}px "
            f"({spec['threshold_m']:.0f}m), fixed N=37,654, exact DTI refill; "
            f"pred {spec['prediction']:+.3f} MODEL"
        )
        rec = bpv.write_and_verify_variant(
            mask=candidate,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=parent,
            axis=AXIS,
            value=value,
            note_template=note,
            existing_shas=existing_shas,
            parent_id=PARENT_ID,
            parent_sha_zeros=bpv.PARENT_SHA_ZEROS,
            parent_sha_nan=bpv.PARENT_SHA_NAN,
            date=DATE,
            min_catalogue_px=float(spec["threshold_px"]),
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
                "threshold_px": stats["threshold_px"],
                "threshold_m": stats["threshold_m"],
                "removed_parent_dots": stats["n_removed"],
                "added_dots": stats["n_added"],
                "refill_candidate_pool_size": stats["n_refill_candidates"],
                "pct_changed_exact": stats["pct_changed_moved"],
                "pct_changed_symmetric_difference": stats["pct_changed_symmetric_difference"],
                "ranking_basis": RANKING_BASIS,
                "four_line_field": FIELD_SOURCES,
                "build_script_sha256": sha256_path(Path(__file__).resolve()),
                "git_sha": git_value("rev-parse", "HEAD"),
                "origin_main_sha_checked_before_build": git_value("rev-parse", "origin/main"),
                "nearest_neighbour_stats": {
                    "R0": parent_nn,
                    "candidate": nn,
                    "interpretation": "REPORT ONLY; exact-marginal refill has no extra spacing constraint",
                },
                "report_only_diagnostics": diag,
                "r0_reference_diagnostics": diagnostics[PARENT_ID],
                "leakage_canaries": {
                    "passed": all(value_auc <= 0.90 for value_auc in canaries.values()),
                    "max_single_feature_symmetric_auc": max(canaries.values()),
                    "channels": canaries,
                    "report_only": True,
                },
                "model_prediction": {
                    "evidence_class": "MODEL",
                    "delta_vs_r0": float(spec["prediction"]),
                    "range": list(spec["prediction_range"]),
                    "basis": spec["prediction_basis"],
                    "no_evidence_if_abs_live_delta_below": NO_EVIDENCE_BAND,
                },
                "not_submitted": True,
            }
        )
        write_json(RELEASES / f"{rec['id']}.json", rec)
        receipts.append(rec)
        new_cards[rec["id"]] = build_card(spec, stats, rec, nn)

        new_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": AXIS,
                "value": value,
                "n_dots": str(N_DOTS),
                "pct_changed": f"{stats['pct_changed_moved']:.5f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{spec['prediction']:+.3f}",
                "predicted_range": f"[{spec['prediction_range'][0]:+.3f},{spec['prediction_range'][1]:+.3f}]",
                "ranking_basis": RANKING_BASIS,
                "receipt_score": "",
                "receipt_date": "",
                "description": (
                    f"PRUNE d_catalogue<={spec['threshold_px']:.4g}px ({spec['threshold_m']:.0f}m); "
                    f"remove {stats['n_removed']}; exact-marginal H19-5 refill, fixed {N_DOTS:,}. "
                    f"Interior annulus bracket: {spec['band']}."
                ),
                "recommendation": (
                    "HOLD pending human slot choice and live receipt; MODEL magnitude is below "
                    "the brief's 0.01 no-evidence threshold. No score or submission recorded."
                ),
            }
        )

    # Commit the ledger/card updates only after all three variants passed their
    # writer's independent on-disk checks. Preserve historical rows verbatim.
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
        writer = csv.DictWriter(stream, fieldnames=ledger_fields, lineterminator="\n", extrasaction="ignore")
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

    parent_diff = {
        "n_parent": N_DOTS,
        "n_candidate": N_DOTS,
        "n_common": [int((candidate & parent).sum()) for candidate in candidates.values()],
        "variants": {
            spec["value"]: {
                "n_removed": build_stats[spec["value"]]["n_removed"],
                "n_added": build_stats[spec["value"]]["n_added"],
                "pct_changed_moved": build_stats[spec["value"]]["pct_changed_moved"],
                "pct_changed_symmetric_difference": build_stats[spec["value"]]["pct_changed_symmetric_difference"],
                "min_catalogue_distance_px": build_stats[spec["value"]]["min_catalogue_distance_px"],
                "nearest_neighbour_stats": nearest_neighbour_stats(candidates[f"{PARENT_ID}-{AXIS}{spec['value']}"]),
            }
            for spec in SPECS
        },
    }
    report = {
        "schema": "gems88.prune-interior-annulus-report.v1",
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
        "annulus_geometry": prereg["annulus_geometry"],
        "leakage_canaries": {
            "passed": all(value_auc <= 0.90 for value_auc in canaries.values()),
            "max_single_feature_symmetric_auc": max(canaries.values()),
            "channels": canaries,
            "report_only": True,
        },
        "parent_diff": parent_diff,
        "report_only_diagnostics": diagnostics,
        "variants": receipts,
        "predictions_are": "MODEL, not scores; no receipt was supplied or submitted",
        "live_change_under_0.01": "no evidence on public chunks per brief",
        "slots_used": 0,
        "submitted": False,
    }
    write_json(REPORT_PATH, report)

    print(f"R0 exact SHA: zeros={lineage['rebuilt_zeros_sha256']} nan={lineage['rebuilt_nan_sha256']}")
    print(f"Manifest verified: {len(verified)} inputs; leakage canaries max={max(canaries.values()):.5f}")
    for rec in receipts:
        d = rec["report_only_diagnostics"]
        hp = d["holdout_proxy"]
        sgmc = d["sgmc_control"]
        diff = rec["parent_diff"]
        print(
            f"{rec['id']} n={rec['n_dots']:,} moved={diff['pct_changed_moved']:.5f}% "
            f"removed={diff['n_removed']} added={diff['n_added']} "
            f"min_dcat={diff['min_dist_catalogue_px']:.4f}px "
            f"MODEL={rec['model_prediction']['delta_vs_r0']:+.3f} "
            f"PROXY-holdout={hp['dti']:.6f} n={hp['withheld_positives']} CI={hp['ci95']} "
            f"SGMC-PROXY={sgmc['dti']:.6f}"
        )
        print(f"  primary={rec['file_nan']} SHA256={rec['sha256']}")
        print(f"  fallback={rec['file_zeros']} SHA256={rec['sha256_zeros']}")
        print(f"  note ({rec['form_note_chars']}/140): {rec['form_note']}")
    print(f"REPORT: {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
