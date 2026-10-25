#!/usr/bin/env python3
"""Reopen archived H88-CON88 bytes and enforce the binding negative verdict.

This is a read-only validator. The former equal-support gate is retained in the
historical record, but it cannot override the literal all-registry preflight.
Default exit 0 means the *research archive* is internally valid. Passing
``--require-submit`` exits 2 while the literal duplicate stop binds.
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

from scripts.preflight_mtas88 import inspect as binding_preflight  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402

CANDIDATE = ROOT / (
    "docs/downloads/"
    "gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif"
)
EXPECTED_SHA256 = "e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(root: Path = ROOT) -> dict:
    root = Path(root)
    candidate = root / CANDIDATE.relative_to(ROOT)
    archive = candidate.with_suffix(".zip")
    sample = root / "data/bridge/sample_submission.tif"
    gates = json.loads((root / "registry/con88_gates.json").read_text())
    run_card = json.loads((root / "run_card_con88.json").read_text())
    withdrawal = json.loads((root / "evidence/con88_clearance_withdrawal_20261025.json").read_text())

    digest = sha256(candidate)
    if digest != EXPECTED_SHA256 or digest != gates["sha256"] or digest != run_card["raster_sha256"]:
        raise ValueError("archived CON88 TIFF identity changed")
    if "DO-NOT-SUBMIT" not in candidate.name or "DO-NOT-SUBMIT" not in archive.name:
        raise ValueError("archived CON88 package lost its negative filename marker")
    with zipfile.ZipFile(archive) as zipped:
        if zipped.namelist() != [candidate.name] or zipped.read(candidate.name) != candidate.read_bytes():
            raise ValueError("CON88 ZIP must contain exactly the byte-identical, negatively named TIFF")

    validation = validate_artifact(candidate, sample)
    preflight = binding_preflight(root)
    proof = preflight["preplacement_registry_proof"]
    blocked = bool(proof["universal_overlap_blocker"] and proof["directly_saturated"])
    if not validation["ok"] or not blocked:
        raise ValueError("CON88 research format or binding literal stop did not reproduce")
    if any(record.get("ok_to_submit") is not False for record in (gates, run_card, withdrawal)):
        raise ValueError("withdrawn CON88 clearance was reintroduced")

    return {
        "schema": "gems88.con88-archive-validation.v2",
        "candidate": candidate.relative_to(root).as_posix(),
        "raster_sha256": digest,
        "zip_sha256": sha256(archive),
        "validator_output": validation,
        "historical_equal_support_diagnostic": {
            "status": "HISTORICAL_DIAGNOSTIC_NOT_CLEARANCE",
            "worst_overlap": gates["historical_equal_support_gate"]["worst_overlap"],
            "worst_abs_spearman": gates["historical_equal_support_gate"]["worst_abs_spearman"],
        },
        "binding_literal_registry": proof,
        "research_download_ok": True,
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "organizer_confirmed_score": None,
        "decision": "DUPLICATE_STOP",
        "verdict": "negative",
    }


def main(argv=None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = inspect(root)
    except Exception as exc:
        result = {
            "schema": "gems88.con88-archive-validation.v2",
            "decision": "AUDIT_ERROR",
            "error": f"{type(exc).__name__}: {exc}",
            "research_download_ok": False,
            "ok_to_submit": False,
            "verdict": "negative",
        }
        print(json.dumps(result, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 2 if args.require_submit else 0


if __name__ == "__main__":
    raise SystemExit(main())
