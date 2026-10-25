#!/usr/bin/env python3
"""Fresh protocol-integrity review, no training, TIFF generation or slot use.

Exit 0: research review completed, NOT clearance. Exit 2 with --require-submit:
submission blocked. Exit 1: audit could not finish, no stale success retained.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]

from gems88 import gate  # noqa: E402
from scripts.audit_literal_protocol import inspect  # noqa: E402
from scripts.readiness import assess, verify_template  # noqa: E402

OUTPUTS = ("evidence/protocol_review_43d08c7a.json", "docs/data/protocol_review_43d08c7a.json")


def review(root=ROOT):
    root = Path(root)
    verify_template(root)
    audit = inspect(root)  # reopens pinned TIFF, ZIP, sample, catalogue, witness
    synthetic = gate.decide(
        portal={"ok": True, "problems": []},
        uniqueness={"unique_like_for_like": True, "unique_literal": False,
                    "literal_blockers": ["dense"], "like_for_like_blockers": [],
                    "registry_complete": True, "surface_checked": True},
        canary_passed=True, holdout_beats_bar=True,
        name="synthetic-review-probe", note="not a raster or scientific experiment", used_names=[])
    if synthetic["ok_to_submit"] or synthetic["eligible_for_selector"]:
        raise ValueError("Legacy dense-prior bypass remains open")
    for auc in (0.01, 0.99):
        result = assess({"feature_names": ["probe"], "canaries": [{"feature": "probe", "auc": auc}]}, root)
        if "Leakage canary blocked: probe" not in result["problems"]:
            raise ValueError("Directional leakage bypass remains open")
    if audit["decision"] != "DUPLICATE_STOP" or not audit["saturation_certificate"]["universal_overlap_blocker"]:
        raise ValueError("Universal blocker did not reproduce; review the protocol before training")
    note = "Protocol-integrity audit of existing MDPS88; literal duplicate stop; no new model or organizer score; DO NOT SUBMIT"
    if len(note) > 140:
        raise ValueError("Research note exceeds portal length")
    return {
        "schema": "gems88.protocol-integrity-review.v1",
        "date_utc": "2026-10-24",
        "lane": "protocol-integrity-only",
        "hypothesis": "Local eligibility must not authorize literal duplicates or inverted leakage features.",
        "mechanism": "Shared pinned-byte saturation/overlap and format audits plus synthetic negative gate probes; no geological model fitted.",
        "named_non_fault_process": "Not tested in this software review. Existing MDPS88 artifact's geological mimic: pluvial shoreline benches and fluvial terrace risers.",
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "status": "HISTORICAL_ONLY_NOT_RETRAINED_IN_THIS_REVIEW",
            "evaluator_version": audit["holdout"]["evaluator_version"],
            **audit["holdout"]["overall"],
            "source": audit["holdout"]["experiment_file"],
            "new_holdout_experiments": 0,
            "limitation": "Catalogue recovery does not validate hidden off-catalogue leaderboard performance. No new experiment permitted after DUPLICATE_STOP.",
        },
        "correlation_overlap_vs_registry": audit["correlation_overlap_vs_registry"],
        "saturation_certificate": audit["saturation_certificate"],
        "validator_output": audit["validator_output"],
        "existing_research_artifact": audit["raster"],
        "raster_sha256": audit["raster_sha256"],
        "zip_one_byte_identical_tif": audit["zip_one_byte_identical_tif"],
        "submission_name": audit["submission_name"],
        "submission_note": note,
        "software_checks": {
            "template_pins_unchanged": True,
            "literal_duplicate_cannot_be_selector_eligible": True,
            "both_auc_directions_blocked": True,
        },
        "new_rasters_generated": 0,
        "experiments_run": 0,
        "slots_used": 0,
        "organizer_confirmed_score": None,
        "ok_to_download_for_research": True,
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "decision": "DUPLICATE_STOP",
        "verdict": "negative",
        "limitations": [
            "No actual single-method paragraph was supplied; software review lane only.",
            "No protocol-unique nonempty raster exists against the measured dense witness under the current support definition.",
            "Current DrivenData standings, rules, deadlines, account receipts and weekly allowance cannot be verified within this sandbox's host allowlist.",
            "Restored input hashes authenticate owner-mirror bytes, not organizer provenance or redistribution permission.",
        ],
    }


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    root = Path(root)
    try:
        report = review(root)
    except Exception as exc:  # CLI boundary: erase stale success even on decoder/schema errors
        report = {
            "schema": "gems88.protocol-integrity-review.v1",
            "decision": "AUDIT_ERROR", "error": str(exc), "verdict": "negative",
            "ok_to_submit": False, "ok_to_download_for_research": False,
            "approved_for_weekly_slot": False,
        }
    for relative in OUTPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    if report["decision"] == "AUDIT_ERROR":
        return 1
    return 2 if args.require_submit else 0


if __name__ == "__main__":
    raise SystemExit(main())
