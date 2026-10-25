#!/usr/bin/env python3
"""Revalidate the archived H88-CON88 package without granting submission.

IR-88-0AB98CD1-01 withdrew the former equal-support clearance.  This validator
reopens the exact TIFF and one-TIFF ZIP, verifies their withdrawal record and
runs the shared literal preflight.  A successful default exit means only that
the negatively labelled research archive is intact.  ``--require-submit``
always fails with exit 2 while the binding duplicate stop remains.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.preflight_mtas88 import inspect as inspect_preflight  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402
CANDIDATE = (
    "gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-"
    "DO-NOT-SUBMIT.tif"
)
EXPECTED_TIFF_SHA256 = "e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68"
WITHDRAWAL = "evidence/con88_clearance_withdrawal_20261025.json"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate(root: Path = ROOT) -> dict:
    root = Path(root)
    candidate = root / "docs/downloads" / CANDIDATE
    archive = candidate.with_suffix(".zip")
    format_result = validate_artifact(candidate, root / "data/bridge/sample_submission.tif")
    with zipfile.ZipFile(archive) as zipped:
        zip_exact = (
            zipped.namelist() == [candidate.name]
            and zipped.read(candidate.name) == candidate.read_bytes()
        )
    gates = json.loads((root / "registry/con88_gates.json").read_text())
    run_card = json.loads((root / "run_card_con88.json").read_text())
    withdrawal = json.loads((root / WITHDRAWAL).read_text())
    preflight = inspect_preflight(root)
    digest = sha256(candidate)
    archive_integrity = all(
        (
            digest == EXPECTED_TIFF_SHA256,
            format_result.get("ok") is True,
            zip_exact,
            "DO-NOT-SUBMIT" in candidate.name,
            gates.get("candidate") == candidate.name,
            gates.get("sha256") == digest,
            gates.get("ok_to_submit") is False,
            gates.get("G2_ok") is False,
            run_card.get("raster_sha256") == digest,
            run_card.get("ok_to_submit") is False,
            run_card.get("verdict") == "negative",
            withdrawal.get("tif_sha256_unchanged") == digest,
            withdrawal.get("new_zip_sha256") == sha256(archive),
        )
    )
    duplicate_stop = bool(
        preflight.get("preplacement_registry_proof", {}).get("universal_overlap_blocker")
        and preflight.get("preplacement_registry_proof", {}).get("covered_allowed_fraction") == 1.0
    )
    return {
        "schema": "gems88.con88-archive-validation.v2",
        "candidate": candidate.name,
        "sha256": digest,
        "zip_file": archive.name,
        "zip_sha256": sha256(archive),
        "format_validator": format_result,
        "zip_single_tif_byte_identical": zip_exact,
        "archive_integrity": archive_integrity,
        "literal_overlap": 1.0 if duplicate_stop else None,
        "overlap_limit": 0.70,
        "decision": "DUPLICATE_STOP" if duplicate_stop else "AUDIT_ERROR",
        "ok_to_download_for_research": archive_integrity,
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "verdict": "negative",
        "withdrawal_record": WITHDRAWAL,
        "note": "Default success validates an archived research package only; it is not submission clearance.",
    }


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = validate(root)
    except (KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        result = {
            "schema": "gems88.con88-archive-validation.v2",
            "decision": "AUDIT_ERROR",
            "archive_integrity": False,
            "ok_to_download_for_research": False,
            "ok_to_submit": False,
            "approved_for_weekly_slot": False,
            "verdict": "negative",
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, indent=2, allow_nan=False))
    if not result.get("archive_integrity") or result.get("decision") != "DUPLICATE_STOP":
        return 1
    return 2 if args.require_submit else 0


if __name__ == "__main__":
    raise SystemExit(main())
