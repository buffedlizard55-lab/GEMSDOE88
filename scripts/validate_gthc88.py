#!/usr/bin/env python3
"""Fail-closed disk/ZIP and run-card gate for the GTHC-88 research artifact.

Exit 0 means OK TO DOWNLOAD FOR RESEARCH, never organizer acceptance. Exit 2
when --require-submit is requested and the negative registry/holdout gate stands.
Enforces every invariant even under python -O (no bare assert stripping).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import grid  # noqa: E402
from gems88.gate import portal_validate  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402


def _require(condition: object, message: object = "GTHC88 validation failed") -> None:
    if not condition:
        raise AssertionError(str(message))


def main(argv: list[str] | None = None, root: Path = ROOT, write_output: bool = True) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args(argv)
    root = Path(root)
    card = json.loads((root / "registry/gthc88_run_card.json").read_text())
    pub_card = json.loads((root / "docs/data/gthc88_run_card.json").read_text())
    _require(
        card == pub_card,
        "registry/gthc88_run_card.json and docs/data/gthc88_run_card.json must match",
    )
    tif = root / card["download"]
    sample = root / "data/bridge/sample_submission.tif"
    faults = root / "data/bridge/existing_faults.tif"
    zipped = tif.with_suffix(".zip")
    _require(tif.name.endswith("DO-NOT-SUBMIT.tif"), "GTHC TIFF missing DO-NOT-SUBMIT suffix")
    _require(len(card["submission_note"]) <= 140, "submission_note exceeds 140 chars")
    _require(len(card["submission_name"]) <= 140, "submission_name exceeds 140 chars")
    _require(
        card["verdict"] == "negative" and not card["ok_to_submit"],
        "GTHC card must stay negative and ok_to_submit=False",
    )
    _require(card["holdout_dti"]["evidence_class"] == "HOLDOUT-DTI", "missing HOLDOUT-DTI label")
    _require(
        card["holdout_dti"]["evaluator_version"] == "gems57-pooled-hide-v2",
        "unexpected evaluator_version",
    )
    _require(
        card["holdout_dti"]["ci95"] and card["holdout_dti"]["withheld_positive_pixels"] == 22893,
        "missing ci95 or withheld_positive_pixels!=22893",
    )
    _require(
        card["unstratified_scrd_holdout_holdout_dti"]["dti"] > card["incumbent_holdout_dti"]["dti"]
        if "unstratified_scrd_holdout_holdout_dti" in card
        else card["unstratified_scrd_holdout_dti"]["dti"] > card["incumbent_holdout_dti"]["dti"],
        "expected unstratified SCRD > incumbent holdout DTI",
    )
    _require(
        card["correlation_overlap_vs_registry"]["final_overlap_3px"] > 0.70,
        "expected literal overlap > 0.70",
    )
    _require(
        card["correlation_overlap_vs_registry"]["like_for_like_unique"] is True,
        "expected like_for_like_unique=True",
    )
    _require(
        card["correlation_overlap_vs_registry"]["like_for_like_worst_overlap_3px"]["value"] <= 0.70,
        "expected like_for_like_worst_overlap_3px <= 0.70",
    )
    _require(
        card["correlation_overlap_vs_registry"]["preplacement_max_abs_rho"] <= 0.90,
        "expected preplacement_max_abs_rho <= 0.90",
    )
    _require(
        card["correlation_overlap_vs_registry"]["fingerprint_screen_passed"] is True,
        "expected fingerprint_screen_passed=True",
    )
    _require(
        card["leakage_canary"]
        and all(max(v["auc"], 1.0 - v["auc"]) <= 0.90 for v in card["leakage_canary"].values()),
        "leakage canary check failed",
    )
    _require(
        hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"],
        "GTHC TIFF SHA-256 mismatch",
    )
    _require(
        hashlib.sha256(sample.read_bytes()).hexdigest() == grid.SHA256_SAMPLE_SUBMISSION,
        "sample_submission.tif SHA-256 mismatch",
    )
    _require(
        hashlib.sha256(faults.read_bytes()).hexdigest() == grid.SHA256_EXISTING_FAULTS,
        "existing_faults.tif SHA-256 mismatch",
    )
    with zipfile.ZipFile(zipped) as z:
        _require(z.namelist() == [tif.name] and z.testzip() is None, "invalid GTHC ZIP")
        _require(z.read(tif.name) == tif.read_bytes(), "GTHC ZIP payload mismatch")
    independent = validate_artifact(tif, sample)
    _require(
        independent["ok"] and independent["raster_sha256"] == card["raster_sha256"],
        "validate_artifact failed for GTHC",
    )
    fp = grid.load_grid(root / "data/bridge").footprint
    for file in (tif, zipped):
        report = portal_validate(file, sample, footprint=fp)
        if not report["ok"]:
            raise ValueError(f"portal parity rejected {file}: {report['problems']}")
    report = dict(
        ok_to_download=True,
        ok_to_submit=False,
        label="OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT",
        tif_sha256=card["raster_sha256"],
        zip_sha256=hashlib.sha256(zipped.read_bytes()).hexdigest(),
        tif_and_single_member_zip_validated=True,
        local_format_audit=independent,
        reason=card["stop_reason"],
        organizer_accepted=None,
    )
    if write_output:
        output = root / "docs/data/gthc88_validation.json"
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "local_format_audit"}, indent=2))
    return 2 if args.require_submit else 0


if __name__ == "__main__":
    raise SystemExit(main())
