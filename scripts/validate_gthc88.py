#!/usr/bin/env python3
"""Fail-closed disk/ZIP and run-card gate for the GTHC-88 research artifact.

Exit 0 means OK TO DOWNLOAD FOR RESEARCH, never organizer acceptance. Exit 2
when --require-submit is requested and the negative registry/holdout gate stands.
No manual image inspection or portal credentials.
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args(argv)
    card = json.loads((ROOT / "registry/gthc88_run_card.json").read_text())
    pub_card = json.loads((ROOT / "docs/data/gthc88_run_card.json").read_text())
    assert card == pub_card, "registry/gthc88_run_card.json and docs/data/gthc88_run_card.json must match"
    tif = ROOT / card["download"]
    sample = ROOT / "data/bridge/sample_submission.tif"
    zipped = tif.with_suffix(".zip")
    assert tif.name.endswith("DO-NOT-SUBMIT.tif")
    assert len(card["submission_note"]) <= 140
    assert len(card["submission_name"]) <= 140
    assert card["verdict"] == "negative" and not card["ok_to_submit"]
    assert card["holdout_dti"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert card["holdout_dti"]["ci95"] and card["holdout_dti"]["withheld_positive_pixels"] == 22893
    assert card["unstratified_scrd_holdout_dti"]["dti"] > card["incumbent_holdout_dti"]["dti"]
    assert card["correlation_overlap_vs_registry"]["final_overlap_3px"] > 0.70
    assert card["correlation_overlap_vs_registry"]["like_for_like_unique"] is True
    assert card["correlation_overlap_vs_registry"]["like_for_like_worst_overlap_3px"]["value"] <= 0.70
    assert card["correlation_overlap_vs_registry"]["preplacement_max_abs_rho"] <= 0.90
    assert card["correlation_overlap_vs_registry"]["fingerprint_screen_passed"] is True
    assert card["leakage_canary"] and all(
        max(v["auc"], 1.0 - v["auc"]) <= 0.90 for v in card["leakage_canary"].values()
    )
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(sample.read_bytes()).hexdigest() == grid.SHA256_SAMPLE_SUBMISSION
    with zipfile.ZipFile(zipped) as z:
        assert z.namelist() == [tif.name] and z.testzip() is None
        assert z.read(tif.name) == tif.read_bytes()
    independent = validate_artifact(tif, sample)
    assert independent["ok"] and independent["raster_sha256"] == card["raster_sha256"]
    fp = grid.load_grid().footprint
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
    output = ROOT / "docs/data/gthc88_validation.json"
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "local_format_audit"}, indent=2))
    return 2 if args.require_submit else 0


if __name__ == "__main__":
    raise SystemExit(main())
