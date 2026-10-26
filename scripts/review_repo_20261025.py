#!/usr/bin/env python3
"""Re-run the 2026-10-25 repository review without fitting or uploading.

This is an autonomous, fail-closed replay of the original dated review. It
retains that review's five-hypothesis and source-access snapshot; it does NOT
refetch official pages or certify that its old proposals are still untested.
The current source-reviewed queue is registry/hypothesis_queue.json. This
command reopens the archived research download and proves (from hash-pinned
local bytes) whether the literal registry rule admits any nonempty candidate.  It does *not* train,
place dots, create a new TIFF, select a weekly slot, or call DrivenData.

Exit codes:
  0  the audit completed; this is not submission approval
  1  required local bytes or the audit contract are missing/corrupt
  2  ``--require-submit`` was requested but the candidate is blocked
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import grid  # noqa: E402
from gems88.review import (  # noqa: E402
    OFFICIAL_SOURCES,
    hypothesis_queue,
    safe_note,
    validate_hypothesis_queue,
)
from scripts.validate_artifact import validate_artifact  # noqa: E402

DATE_UTC = "2026-10-25"
OUTPUTS = (
    ROOT / "evidence/repo_review_20261025.json",
    ROOT / "docs/data/repo_review_20261025.json",
)
WITNESS_REL = "data/registry/dense_17gemdoe.tif"
WITNESS_SHA256 = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
# This is a prepared note for a hypothetical future selector, not permission
# to upload it.  Keeping it here makes the <=140-character constraint testable
# without manufacturing a portal receipt.
RESERVED_NAME = "GEMSDOE88-MTAS-PREFLIGHT-20261025-NO-FILE"
RESERVED_NOTE = (
    "MTAS pre-placement duplicate: registry covers all allowed cells; no TIFF built; UNSCORED; DO NOT SUBMIT"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _same_grid(a: rasterio.DatasetReader, b: rasterio.DatasetReader) -> bool:
    return a.shape == b.shape and a.crs == b.crs and a.transform == b.transform


def audit_saturation(root: Path) -> dict:
    """Return a sufficient pre-placement duplicate proof from local bytes.

    The user rule is forward overlap: the denominator is the candidate's
    positive pixels.  If a positive registry witness covers every allowed cell,
    every nonempty allowed candidate has overlap 1.0.  This proof is stronger
    than emitting a candidate and then discovering the same result; it is why
    the selected method is not fit in this session.
    """

    sample_path = root / "data/bridge/sample_submission.tif"
    catalogue_path = root / "data/bridge/existing_faults.tif"
    witness_path = root / WITNESS_REL
    expected = {
        "sample_sha256": grid.SHA256_SAMPLE_SUBMISSION,
        "catalogue_sha256": grid.SHA256_EXISTING_FAULTS,
        "witness_sha256": WITNESS_SHA256,
    }
    paths = (sample_path, catalogue_path, witness_path)
    missing = [str(path.relative_to(root)) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing hash-pinned audit inputs: " + ", ".join(missing))
    actual = {
        "sample_sha256": sha256(sample_path),
        "catalogue_sha256": sha256(catalogue_path),
        "witness_sha256": sha256(witness_path),
    }
    if actual != expected:
        raise ValueError(f"hash-pinned audit input mismatch: expected {expected}, got {actual}")

    with rasterio.open(sample_path) as sample, rasterio.open(catalogue_path) as catalogue, rasterio.open(witness_path) as witness:
        if not _same_grid(sample, catalogue) or not _same_grid(sample, witness):
            raise ValueError("sample, catalogue and witness do not share one grid")
        sample_values = sample.read(1)
        catalogue_values = catalogue.read(1)
        witness_values = witness.read(1)
        footprint = np.isfinite(sample_values) & (sample.read_masks(1) > 0)
        catalogue_mask = (catalogue_values > 0) & footprint
        witness_support = np.isfinite(witness_values) & (witness_values > 0)
        allowed = footprint & ~catalogue_mask

        allowed_count = int(allowed.sum())
        covered_count = int((allowed & witness_support).sum())
        direct_fraction = covered_count / allowed_count if allowed_count else 0.0
        saturated = bool(allowed_count > 0 and covered_count == allowed_count)
        # The current user rule uses a 3-pixel halo. Direct support coverage is
        # a stronger sufficient condition, so the lower bound is exactly 1.0.
        lower_bound = 1.0 if saturated else None
        return {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "witness_file": WITNESS_REL,
            "witness_sha256": actual["witness_sha256"],
            "sample_sha256": actual["sample_sha256"],
            "catalogue_sha256": actual["catalogue_sha256"],
            "grid": {
                "shape": list(sample.shape),
                "crs": str(sample.crs),
                "transform": list(tuple(sample.transform)[:6]),
            },
            "footprint_pixels": int(footprint.sum()),
            "catalogue_pixels_inside_footprint": int(catalogue_mask.sum()),
            "allowed_pixels": allowed_count,
            "directly_covered_allowed_pixels": covered_count,
            "covered_allowed_fraction": direct_fraction,
            "uncovered_allowed_pixels": allowed_count - covered_count,
            "universal_overlap_blocker": saturated,
            "overlap_definition": "forward 3-pixel overlap: candidate positive pixels within 3 px of registry positive support",
            "overlap_limit": 0.70,
            "universal_lower_bound_on_any_nonempty_candidate": lower_bound,
            "implication": (
                "Every nonempty candidate in the allowed domain has forward overlap 1.0 > 0.70."
                if saturated
                else "The sufficient direct-coverage proof is inconclusive; a complete surface/dot registry audit is required."
            ),
        }


def audit_research_download(root: Path) -> dict:
    """Reopen the current advertised file and its one-member ZIP.

    The result is explicitly format-only.  A valid local file is never promoted
    by this function; the current release card is a historical research record.
    """

    status = _json(root / "docs/status.json")
    release = _json(root / "docs/data/current_release.json")
    tif = root / release["file"]
    archive = root / release["zip_file"]
    if not tif.is_file() or not archive.is_file():
        raise FileNotFoundError("current research TIFF or ZIP is missing")
    if sha256(tif) != release["file_sha256"] or sha256(archive) != release["zip_sha256"]:
        raise ValueError("current research TIFF/ZIP changed from current-release card")
    sample = root / "data/bridge/sample_submission.tif"
    checks = validate_artifact(tif, sample)
    with zipfile.ZipFile(archive) as member_zip:
        members = member_zip.namelist()
        one_matching_member = members == [tif.name] and member_zip.read(tif.name) == tif.read_bytes()
    if not one_matching_member:
        raise ValueError("research ZIP must contain exactly its byte-identical TIFF")
    return {
        "evidence_class": "LOCAL-FORMAT-AUDIT",
        "candidate": release["candidate"],
        "file": release["file"],
        "zip_file": release["zip_file"],
        "tif_sha256": sha256(tif),
        "zip_sha256": sha256(archive),
        "validator": checks,
        "zip_one_byte_identical_tif": True,
        "ok_to_download_for_research": bool(status.get("ok_to_download_for_research", True)),
        "ok_to_submit": False,
        "status_source": "docs/status.json + docs/data/current_release.json",
        "warning": "A local format PASS is not organizer acceptance, a uniqueness pass, or a weekly-slot selector decision.",
    }


def h33_forensics(root: Path) -> dict:
    """Extract measured lineage facts without relabelling the public claim."""

    evidence = _json(root / "evidence/h33_forensics_20261024.json")
    h33 = next(row for row in evidence["lineage"] if row["name"].startswith("H33 b2"))
    removed = evidence["removed_D28_to_H33"]
    return {
        "h33_value": 0.2778,
        "h33_evidence_class": "USER-REPORTED CLAIM — NOT HOLDOUT-DTI AND NOT ORGANIZER-CONFIRMED",
        "h33_source": "user prompt / archived owner ledger; no DrivenData receipt in this repository",
        "measured_on_disk": {
            "evidence_class": "REGISTRY-MEASUREMENT (lineage geometry, not score)",
            "h33_sha256": h33["sha256"],
            "h33_dots": h33["n_dots"],
            "h33_median_catalogue_distance_px": h33["d_cat_px"]["median"],
            "h33_fraction_gt_30px": h33["frac_d_cat_gt_30"],
            "h33_nearest_neighbour_min_px": evidence["h33_spacing_px"]["nn_min"],
            "d28_to_h33_removed_dots": removed["n"],
            "removed_dots_fraction_within_2px_catalogue": removed["frac_le_2"],
        },
        "interpretation": (
            "The nested support and approximately three-pixel de-redundancy are consistent with a better precision/coverage trade-off under the published metric. "
            "They do not prove the hidden labels, causality, or that the claim beats the official leaderboard."
        ),
    }


def build_report(root: Path = ROOT) -> dict:
    root = Path(root)
    queue = hypothesis_queue()
    validate_hypothesis_queue(queue)
    safe_note(RESERVED_NOTE)
    if len(RESERVED_NAME) > 140:
        raise ValueError("reserved submission name exceeds 140 characters")

    errors: list[str] = []
    try:
        saturation = audit_saturation(root)
    except (OSError, ValueError, KeyError) as exc:
        saturation = None
        errors.append(f"saturation audit unavailable: {exc}")
    try:
        research_download = audit_research_download(root)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        research_download = None
        errors.append(f"research download audit unavailable: {exc}")

    blocked = bool(saturation and saturation["universal_overlap_blocker"])
    review_status = "DUPLICATE_STOP" if blocked else ("INCOMPLETE" if errors else "REGISTRY_NOT_CLEARED")
    return {
        "schema": "gems88.repo-review-20261025.v1",
        "review_date_utc": DATE_UTC,
        "snapshot_scope": "HISTORICAL_HYPOTHESES_AND_SOURCE_ACCESS_NOT_REFRESHED_BY_REPLAY",
        "current_research_queue": "registry/hypothesis_queue.json",
        "current_review_addendum": "docs/data/session_c59db412_run_card.json",
        "review_status": review_status,
        "hypothesis_queue": queue,
        "selected_lane": {
            "id": "H88-MTAS",
            "selection_reason": "Highest qualitative gain-to-cost hypothesis using only restored cached layers; no external data required.",
            "status": "NOT FIT — pre-placement duplicate proof fires before feature construction",
        },
        "official_sources": list(OFFICIAL_SOURCES),
        "h33_forensics": h33_forensics(root),
        "preplacement_registry_audit": saturation,
        "current_research_download": research_download,
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "status": "NOT RUN — pre-placement duplicate stop",
            "evaluator_version": "gems57-pooled-hide-v2",
            "withheld_positive_pixels": None,
            "dti": None,
            "ci95": None,
            "reason": "No feature stack was fitted and no MTAS prediction was emitted. A historical number cannot be relabelled as MTAS evidence.",
        },
        "leakage_canary": {
            "status": "NOT RUN — no MTAS feature was constructed",
            "threshold_symmetric_auc": 0.90,
            "features_tested": 0,
        },
        "new_tif": {
            "generated": False,
            "file": None,
            "sha256": None,
            "reason": "The binding pre-placement proof rejects every nonempty candidate; making or renaming a TIFF would violate the stop rule and would not make it unique.",
        },
        "submission": {
            "reserved_name": RESERVED_NAME,
            "reserved_note": RESERVED_NOTE,
            "note_characters": len(RESERVED_NOTE),
            "ok_to_download_new_file": False,
            "ok_to_download_archived_research_file": bool(research_download),
            "ok_to_submit": False,
            "approved_for_weekly_slot": False,
            "weekly_slots_used": 0,
            "organizer_confirmed_score": None,
        },
        "validator_output": {
            "new_tif": "NOT RUN — no new TIFF",
            "no_nan_inside_footprint": None,
            "values_in_0_1": None,
            "crs_shape_transform_match": None,
            "note": "The archived research file has a separate local-format audit; it is not this session's candidate.",
        },
        "errors": errors,
        "verdict": "negative",
        "decision": review_status,
        "limitations": [
            "The local owner-mirror bytes are SHA-pinned but are not an authenticated logged-in DrivenData download in this sandbox.",
            "The hidden organizer labels are unavailable; a catalogued holdout is a proxy and cannot prove a leaderboard result.",
            "The prompt's H33 0.2778 is a user-reported claim without a portal receipt; the public leaderboard snapshot is separate evidence.",
            "The literal all-registry overlap rule is mathematically unsatisfiable for a nonempty candidate while the full-positive 17GEMSDOE witness remains in scope.",
            "No external dataset was needed for the selected hypothesis, so no new license-dependent layer was consumed.",
        ],
        "next_action": "Require an explicit, documented resolution of the universal witness/protocol contradiction before constructing another candidate; then rerun the ranked lane through shared buffered holdout and two-phase uniqueness.",
    }


def write_report(report: dict, root: Path = ROOT) -> None:
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    for relative in ("evidence/repo_review_20261025.json", "docs/data/repo_review_20261025.json"):
        target = Path(root) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(text, encoding="utf-8")
        temp.replace(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true", help="return 2 unless this review clears a weekly slot")
    args = parser.parse_args(argv)
    try:
        report = build_report()
        write_report(report)
    except Exception as exc:  # Never leave an old positive report after a failed run.
        report = {
            "schema": "gems88.repo-review-20261025.v1",
            "review_date_utc": DATE_UTC,
            "review_status": "AUDIT_ERROR",
            "ok_to_submit": False,
            "verdict": "negative",
            "errors": [str(exc)],
        }
        write_report(report)
        print(json.dumps(report, indent=2) + "\n", end="")
        return 1
    print(json.dumps(report, indent=2) + "\n", end="")
    if report["errors"]:
        return 1
    if args.require_submit and not report["submission"]["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
