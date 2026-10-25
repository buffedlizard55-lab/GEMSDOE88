#!/usr/bin/env python3
"""Re-run the 2026-10-25 repository review without fitting or uploading.

This is an autonomous, fail-closed review command. It ranks four repo-local,
currently unexecuted hypotheses, reconciles historical MTAS evidence, and
rechecks the current release separately from the selected FARC review lane.
Its pre-placement test records the literal dense-witness bound; the later main
release adopts the documented equal-support v5 rule (IR-88-SDTL-01). This
command does *not* train, place dots, create a new TIFF, select a weekly slot,
or call DrivenData.

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
# A placeholder for the blocked top untested idea, not a portal submission.
# Keep it explicit that no filename/artifact is actually reserved or uploadable.
RESERVED_NAME = "GEMSDOE88-FARC-PREFLIGHT-20261025-NO-FILE"
RESERVED_NOTE = (
    "FARC pre-placement stop; no candidate TIFF, score or slot; UNSCORED; DO NOT SUBMIT"
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
    """Reopen the current release bytes and preserve the recorded policy decision.

    The local format audit is independent of the H88-SDTL run card's holdout,
    canary and v5 uniqueness evidence. This review never upgrades that decision;
    it verifies that current_release, status, the run card and byte audit agree.
    """

    status = _json(root / "docs/status.json")
    release = _json(root / "docs/data/current_release.json")
    audit = _json(root / "docs/data/download_audit.json")
    card = _json(root / release["run_card"])
    tif = root / release["file"]
    archive = root / release["zip_file"]
    if not tif.is_file() or not archive.is_file():
        raise FileNotFoundError("current release TIFF or ZIP is missing")
    tif_digest, zip_digest = sha256(tif), sha256(archive)
    if tif_digest != release["file_sha256"] or zip_digest != release["zip_sha256"]:
        raise ValueError("current release TIFF/ZIP changed from current-release card")
    if card.get("raster", {}).get("sha256") != tif_digest or card.get("raster", {}).get("zip_sha256") != zip_digest:
        raise ValueError("current release and lane run-card hashes disagree")
    if audit.get("canonical_sha256") != tif_digest or audit.get("canonical_file") != tif.name:
        raise ValueError("current release and download audit identify different candidate bytes")
    artifact = next((row for row in audit.get("artifacts", []) if row.get("sha256") == tif_digest), None)
    if artifact is None or artifact.get("zip_sha256") != zip_digest:
        raise ValueError("current release missing from saved-byte download audit")
    sample = root / "data/bridge/sample_submission.tif"
    checks = validate_artifact(tif, sample)
    with zipfile.ZipFile(archive) as member_zip:
        members = member_zip.namelist()
        one_matching_member = members == [tif.name] and member_zip.read(tif.name) == tif.read_bytes()
    if not checks["ok"] or not one_matching_member:
        raise ValueError("current release failed saved-byte format or exact-ZIP validation")

    recorded_submit = bool(
        release.get("ok_to_submit") is True
        and status.get("ok_to_submit") is True
        and card.get("ok_to_submit") is True
        and artifact.get("ok_to_submit") is True
        and audit.get("ok_to_submit") is True
    )
    if bool(release.get("approved_for_weekly_slot")) or int(card.get("weekly_slots_used", 0)) != 0:
        raise ValueError("current release must not silently select or consume a weekly slot")
    uniqueness = card.get("correlation_overlap_vs_registry", {})
    dense_row = next((row for row in card.get("dots_rows", [])
                      if Path(row.get("file", "")).name == Path(WITNESS_REL).name), {})
    holdout = card.get("holdout_dti", {})
    candidate_holdout = holdout.get("candidate", {})
    control_holdout = holdout.get("control_phys44", {})
    paired_delta = holdout.get("paired_delta_vs_control", {})
    return {
        "evidence_class": "LOCAL-FORMAT-AUDIT_NOT_ORGANIZER-ACCEPTANCE",
        "candidate": release["candidate"],
        "lane": card.get("lane"),
        "file": release["file"],
        "zip_file": release["zip_file"],
        "tif_sha256": tif_digest,
        "zip_sha256": zip_digest,
        "validator": checks,
        "zip_one_byte_identical_tif": True,
        "verdict": card.get("verdict"),
        "ok_to_download": release.get("ok_to_download") is True and status.get("ok_to_download_for_research") is True,
        "ok_to_submit_under_current_repository_policy": recorded_submit,
        "approved_for_weekly_slot": release.get("approved_for_weekly_slot") is True,
        "weekly_slots_used": card.get("weekly_slots_used"),
        "organizer_confirmed_score": release.get("organizer_confirmed_score"),
        "protocol_correction": release.get("protocol_correction"),
        "holdout": {
            "evidence_class": candidate_holdout.get("evidence_class"),
            "evaluator_version": candidate_holdout.get("evaluator_version"),
            "withheld_positive_pixels": candidate_holdout.get("withheld_positive_pixels"),
            "candidate_dti": candidate_holdout.get("dti"),
            "candidate_ci95": candidate_holdout.get("ci95"),
            "control_dti": control_holdout.get("dti"),
            "paired_delta": paired_delta.get("delta"),
            "paired_delta_ci95": paired_delta.get("ci95"),
            "folds_won_vs_control": holdout.get("folds_won_vs_control"),
        },
        "leakage_canary": card.get("leakage_canary"),
        "uniqueness": {
            "binding_rule": uniqueness.get("binding_rule"),
            "rasters_checked": uniqueness.get("rasters_checked"),
            "surface_worst_abs_spearman": uniqueness.get("surface_worst_abs_spearman"),
            "final_dot_worst_equal_support_overlap": uniqueness.get("dots_worst_equal_support_overlap"),
            "dense_witness_equal_support_overlap": dense_row.get("equal_support_overlap"),
            "dense_witness_literal_overlap": dense_row.get("literal_overlap"),
            "dense_witness_file": dense_row.get("file"),
        },
        "status_source": "docs/status.json + docs/data/current_release.json + matching run card and download audit",
        "warning": (
            "The current repository marks H88-SDTL eligible under IR-88-SDTL-01 equal-support v5. "
            "The literal dense-witness dot overlap remains 1.0; v5 instead compares continuous-prior top-n cells. "
            "This format audit is not organizer acceptance, a score receipt, or weekly-slot approval."
        ),
    }


def historical_mtas_audit(root: Path) -> dict:
    """Bind the already-executed MTAS lane to its historical evidence card.

    This prevents the queue from relabelling a completed lane as untested.
    The card's holdout is not evidence for the newly selected FARC proposal.
    """

    card_path = root / "registry/mtas88_experiment_run_card.json"
    card = _json(card_path)
    execution_evidence = _json(root / "evidence/mtas88_experiment_20261025.json")
    preplacement = _json(root / "registry/mtas88_run_card.json")
    preflight_evidence = _json(root / "evidence/mtas88_preflight_20261025.json")
    if card.get("lane") != "H88-MTAS" or card.get("verdict") != "negative":
        raise ValueError("archived MTAS execution card is missing or not negative")
    if card != execution_evidence:
        raise ValueError("MTAS execution card and evidence copy disagree")
    if preplacement != preflight_evidence:
        raise ValueError("duplicate copies of the MTAS pre-placement record disagree")
    if (
        preplacement.get("lane") != "H88-MTAS"
        or preplacement.get("decision") != "DUPLICATE_STOP"
        or preplacement.get("experiment_count") != 0
        or preplacement.get("new_rasters_generated") != 0
    ):
        raise ValueError("MTAS pre-placement stop record changed; reconcile before publishing")
    tif = root / card["raster_file"]
    archive = root / card["zip_file"]
    if not tif.is_file() or sha256(tif) != card["raster_sha256"]:
        raise ValueError("archived MTAS TIFF no longer matches its run-card SHA-256")
    if not archive.is_file() or sha256(archive) != card["zip_sha256"]:
        raise ValueError("archived MTAS ZIP no longer matches its run-card SHA-256")
    with zipfile.ZipFile(archive) as members:
        if members.namelist() != [tif.name] or members.read(tif.name) != tif.read_bytes():
            raise ValueError("archived MTAS ZIP is not the one-member identical TIFF")
    holdout = card["holdout"]
    if holdout.get("evidence_class") != "HOLDOUT-DTI":
        raise ValueError("archived MTAS result is not labelled HOLDOUT-DTI")
    return {
        "lane": "H88-MTAS",
        "status": "EXECUTED_HISTORICAL_NEGATIVE_EXCLUDED_FROM_UNTESTED_QUEUE",
        "record": "registry/mtas88_experiment_run_card.json",
        "conflicting_preplacement_records": {
            "records": [
                "registry/mtas88_run_card.json",
                "evidence/mtas88_preflight_20261025.json",
            ],
            "recorded_decision": preplacement["decision"],
            "recorded_experiment_count": preplacement["experiment_count"],
            "recorded_new_rasters_generated": preplacement["new_rasters_generated"],
            "recorded_weekly_slots_used": preplacement["weekly_slots_used"],
            "status": "CONFLICTS_WITH_SEPARATE_EXECUTION_CARD_AND_HASH_MATCHED_RASTER",
            "resolution": "Preserve both records. Treat MTAS as executed for untried-queue accounting because a separate experiment card and matching raster/ZIP exist; do not claim the pre-placement record was rewritten or that the chronology is resolved.",
        },
        "holdout": {
            "evidence_class": holdout["evidence_class"],
            "evaluator_version": holdout["evaluator_version"],
            "withheld_positive_pixels": holdout["withheld_positive_pixels"],
            "dti": holdout["dti"],
            "ci95": holdout["ci95"],
            "split": holdout.get("split"),
            "note": "Historical MTAS result; not a result for the selected FARC proposal and not ORGANIZER-CONFIRMED.",
        },
        "raster_sha256": card["raster_sha256"],
        "zip_sha256": card["zip_sha256"],
        "zip_one_member_byte_identical": True,
        "verdict": card["verdict"],
        "ok_to_submit": card["ok_to_submit"],
    }


def holdout_incumbent_audit(root: Path) -> dict:
    """Return the recorded repository incumbent as local holdout context only."""

    card = _json(root / "registry/bpwd88_run_card.json")
    holdout = card["holdout_dti"]["candidate_exp03"]
    if holdout.get("evidence_class") != "HOLDOUT-DTI":
        raise ValueError("stored incumbent result lacks HOLDOUT-DTI evidence label")
    return {
        "lane": card["lane"],
        "status": "HISTORICAL_REPOSITORY_HOLDOUT_REFERENCE_NOT_LIVE_SCORE",
        "evidence_class": holdout["evidence_class"],
        "evaluator_version": holdout["evaluator_version"],
        "withheld_positive_pixels": holdout["withheld_positive_pixels"],
        "dti": holdout["dti"],
        "ci95": holdout["ci95"],
        "candidate_comparison": "NOT_RUN_FOR_FARC; this historical number is not a paired comparison or leaderboard projection.",
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

    saturation = audit_saturation(root)
    research_download = audit_research_download(root)
    completed_mtas = historical_mtas_audit(root)
    incumbent = holdout_incumbent_audit(root)
    queue_head = queue[0]
    blocked = saturation["universal_overlap_blocker"] is True
    review_status = "DUPLICATE_STOP" if blocked else "REGISTRY_NOT_CLEARED"
    return {
        "schema": "gems88.repo-review-20261025.v2",
        "review_date_utc": DATE_UTC,
        "review_status": review_status,
        "review_scope": "The DUPLICATE_STOP below applies to the H88-FARC candidate considered by this review under the literal pre-placement proof; it is not the current-release selector.",
        "hypothesis_queue": queue,
        "selected_lane": {
            "id": queue_head["id"],
            "selection_reason": "Highest qualitative discovery-potential / cost trade-off among the four currently unexecuted repo-local hypotheses; ordinal judgment only, not a DTI prediction.",
            "status": "NOT FIT — shared pre-placement duplicate proof stops before feature construction",
        },
        "historical_experiment_reconciliation": {
            "executed_lane_excluded_from_untried_queue": completed_mtas,
            "current_repository_holdout_reference": incumbent,
            "note": "The MTAS experiment exists in the repo and is not untested. Conflicting pre-placement and execution records are preserved; its historical holdout does not validate or score FARC.",
        },
        "official_sources": list(OFFICIAL_SOURCES),
        "source_verification_scope": "Official URLs are provided for review. Non-GitHub official pages were not re-fetched in this replay because their hosts are outside the session allowlist; source statuses above are inherited from the prior dated audit, not fresh retrieval. Restored owner-mirror bytes are hash-pinned locally but not authenticated against current organizer downloads.",
        "h33_forensics": h33_forensics(root),
        "preplacement_registry_audit": saturation,
        "current_research_download": research_download,
        "current_repository_release": {
            "lane": research_download["lane"],
            "candidate": research_download["candidate"],
            "file": research_download["file"],
            "sha256": research_download["tif_sha256"],
            "verdict": research_download["verdict"],
            "ok_to_download": research_download["ok_to_download"],
            "ok_to_submit_under_current_repository_policy": research_download["ok_to_submit_under_current_repository_policy"],
            "approved_for_weekly_slot": research_download["approved_for_weekly_slot"],
            "organizer_confirmed_score": research_download["organizer_confirmed_score"],
            "protocol_correction": research_download["protocol_correction"],
            "note": "Inherited from the later origin/main SDTL-88 merge; it was not generated by this FARC review. See docs/research/review-20261025-autonomous.md for the chronology and literal-vs-v5 policy distinction.",
        },
        "holdout": {
            "status": "NOT RUN — pre-placement duplicate stop",
            "candidate_lane": queue_head["id"],
            "evaluator_version_if_unblocked": "gems57-pooled-hide-v2",
            "withheld_positive_pixels": None,
            "dti": None,
            "ci95": None,
            "reason": "No candidate features were constructed or fitted. The archived H88-MTAS result is historical evidence for that completed lane only; it cannot be reused as an H88-FARC score.",
        },
        "leakage_canary": {
            "status": "NOT RUN — no candidate feature was constructed",
            "threshold_symmetric_auc": 0.90,
            "features_tested": 0,
        },
        "new_tif": {
            "scope": "H88-FARC candidate considered in this review only",
            "generated": False,
            "file": None,
            "sha256": None,
            "reason": "For the H88-FARC lane considered by this review under the literal pre-placement test, the SHA-pinned dense witness covers every allowed cell, so any nonempty candidate would have forward overlap 1.0 > 0.70. This does not describe the separately imported H88-SDTL release, which is evaluated under the later documented v5 rule.",
        },
        "submission": {
            "scope": "H88-FARC review candidate only; current H88-SDTL repository release is reported separately",
            "reserved_name": RESERVED_NAME,
            "reserved_name_status": "NO_FILE_NOT_FOR_PORTAL",
            "reserved_note": RESERVED_NOTE,
            "note_characters": len(RESERVED_NOTE),
            "ok_to_download_new_file": False,
            "ok_to_download_archived_research_file": True,
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
            "note": "The archived research TIFF has a separate local-format audit; that pass is not a new candidate validation or submission approval.",
        },
        "errors": [],
        "verdict": "negative",
        "decision": review_status,
        "limitations": [
            "The untested FARC hypothesis has no new HOLDOUT-DTI or canary result because the literal pre-placement rule stops this run first.",
            "The hidden organizer labels are unavailable; catalogued-fault holdout evidence cannot establish the leaderboard score.",
            "H33 0.2778 remains USER-REPORTED without a submission receipt; the prompt's leaderboard snapshots 0.3195 and 0.4413 conflict and were not freshly verified here.",
            "The literal all-registry dot-overlap condition is unsatisfiable for a nonempty candidate while the full-support 17GEMSDOE witness remains in scope; the later main SDTL release uses the documented equal-support v5 correction and records both readings.",
            "The current organizer data page requires account access; the local owner mirrors do not authenticate data identity or rights. No external data were newly downloaded for this review.",
        ],
        "next_action": "Do not spend a slot. The current H88-SDTL release is marked eligible under the shared v5 rule but has no organizer receipt or weekly-slot approval; review its recorded gates and protocol correction before any separate selector decision. This review did not fit H88-FARC. Any later experiment must stay within its own preregistered budget, restore/authenticate inputs, run feature-alone canaries and whole-component buffered holdout with the shared evaluator, then check surface and final dots before separate slot selection.",
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
            "schema": "gems88.repo-review-20261025.v2",
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
