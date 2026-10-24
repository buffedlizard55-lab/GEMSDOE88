#!/usr/bin/env python3
"""Independently validate the frozen H88-TDKL research release.

Default success means that the committed TIFF is safe to download and inspect.
It never means that the artifact is competition-approved. ``--require-submit``
returns 2 while any binding scientific/uniqueness gate is negative.
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid, uniqueness  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_tdkl88(root: Path = ROOT) -> dict:
    root = Path(root)
    card = json.loads((root / "registry/tdkl88_run_card.json").read_text())
    web_card = json.loads((root / "docs/data/tdkl88_run_card.json").read_text())
    gate = json.loads((root / "registry/tdkl88_gate_verdict.json").read_text())
    web_gate = json.loads((root / "docs/data/tdkl88_gate_verdict.json").read_text())
    if card != web_card or gate != web_gate:
        raise ValueError("published TDKL run-card/gate copies differ from canonical registry copies")

    tif = root / card["raster"]["file"]
    archive = root / card["raster"]["zip_file"]
    sample = root / "data/bridge/sample_submission.tif"
    faults = root / "data/bridge/existing_faults.tif"
    witness = root / "data/registry/dense_17gemdoe.tif"
    missing = [str(p) for p in (tif, archive, sample, faults, witness) if not p.is_file()]
    if missing:
        raise FileNotFoundError("required TDKL validation input is missing: " + ", ".join(missing))

    tif_sha, zip_sha = digest(tif), digest(archive)
    if tif_sha != card["raster_sha256"] or tif_sha != gate["sha256"]:
        raise ValueError("TDKL TIFF SHA-256 differs from frozen evidence")
    if zip_sha != card["raster"]["zip_sha256"] or zip_sha != gate["zip_sha256"]:
        raise ValueError("TDKL ZIP SHA-256 differs from frozen evidence")
    with zipfile.ZipFile(archive) as zf:
        if zf.namelist() != [tif.name] or zf.read(tif.name) != tif.read_bytes():
            raise ValueError("TDKL ZIP must contain exactly the byte-identical TIFF")

    gd = grid.load_grid(root / "data/bridge")
    portal = validate_artifact(tif, sample)
    with rasterio.open(tif) as src:
        raster = src.read(1)
    format_ok = bool(
        portal["ok"]
        and np.isfinite(raster).all()
        and float(raster.min()) >= 0.0
        and float(raster.max()) <= 1.0
        and np.all(raster[~gd.footprint] == 0.0)
        and not np.any(raster[gd.catalogue] > 0.0)
    )
    if not format_ok:
        raise ValueError("TDKL written bytes fail format/range/footprint/catalogue validation")

    with rasterio.open(sample) as ref:
        expected_grid = (ref.shape, ref.crs, ref.transform)
    with rasterio.open(witness) as src:
        prior = src.read(1)
    literal_overlap = float(
        uniqueness.dot_overlap(raster, (np.isfinite(prior) & (prior > 0)) & gd.footprint, radius_px=3)
    )
    cert = uniqueness.saturation_certificate(
        witness, gd.footprint, gd.catalogue, expected_grid=expected_grid
    )
    if not cert["universal_overlap_blocker"] or literal_overlap != 1.0:
        raise ValueError("dense-witness saturation certificate or literal overlap changed")

    primary = card["holdout_dti"]["experiments"]["Exp03_h88_tdkl_primary"]
    overall = primary["overall"]
    delta = primary["paired_delta_vs_incumbent_overall"]
    canary = card["leakage_canary"]
    comparisons = card["correlation_overlap_vs_registry"]
    postmerge = comparisons["postmerge_concurrent_overlaps_3px"]
    if not (
        overall["evidence_class"] == "HOLDOUT-DTI"
        and overall["evaluator_version"] == "gems57-pooled-hide-v2"
        and overall["withheld_positive_pixels"] == 22_893
        and 0 <= overall["ci95"][0] <= overall["dti"] <= overall["ci95"][1] <= 1
        and delta["ci95"][0] > 0
        and canary["passed"] is True
        and canary["features_tested"] == 56
        and canary["max_symmetric_auc"] <= 0.90
        and comparisons["pre_placement_surface_max_abs_spearman"] <= 0.90
        and gate["uniqueness_summary"]["worst_like_for_like_overlap"]["value"] <= 0.70
        and max(postmerge["GTHC-88"], postmerge["QTSK-88"]) > 0.70
    ):
        raise ValueError("TDKL holdout/canary/registry evidence is incomplete or inconsistent")

    duplicate = literal_overlap > 0.70
    submit_ok = bool(format_ok and not duplicate and card["verdict"] == "promote" and card["ok_to_submit"])
    if submit_ok != card["ok_to_submit"] or submit_ok != gate["ok_to_submit"]:
        raise ValueError("TDKL card conflicts with independently recomputed binding gate")

    return {
        "schema": "gems88.current-release.v2",
        "candidate": "H88-TDKL",
        "file": card["raster"]["file"],
        "file_sha256": tif_sha,
        "zip_file": card["raster"]["zip_file"],
        "zip_sha256": zip_sha,
        "submission_name": card["submission_name"],
        "submission_note": card["submission_note"],
        "submission_note_length": len(card["submission_note"]),
        "format_valid": format_ok,
        "inside_no_nan": bool(np.isfinite(raster[gd.footprint]).all()),
        "all_finite_entire_raster": bool(np.isfinite(raster).all()),
        "values_0_1": bool(float(raster.min()) >= 0 and float(raster.max()) <= 1),
        "crs_shape_transform_match": portal["ok"],
        "positive_pixels": int((raster > 0).sum()),
        "zip_one_matching_tif": True,
        "holdout_evidence_class": "HOLDOUT-DTI",
        "holdout_evaluator": overall["evaluator_version"],
        "holdout_withheld_positive_pixels": overall["withheld_positive_pixels"],
        "holdout_candidate_dti": overall["dti"],
        "holdout_candidate_ci95": overall["ci95"],
        "paired_delta_vs_incumbent": delta["delta"],
        "paired_delta_ci95": delta["ci95"],
        "canary_features_tested": canary["features_tested"],
        "canary_max_symmetric_auc": canary["max_symmetric_auc"],
        "preplacement_max_abs_spearman": comparisons["pre_placement_surface_max_abs_spearman"],
        "like_for_like_max_overlap_3px": gate["uniqueness_summary"]["worst_like_for_like_overlap"]["value"],
        "postmerge_max_concurrent_overlap_3px": max(postmerge["GTHC-88"], postmerge["QTSK-88"]),
        "literal_registry_overlap_3px": literal_overlap,
        "literal_duplicate": duplicate,
        "duplicate": duplicate,
        "research_download_ok": True,
        "ok_to_download": True,
        "ok_to_submit": submit_ok,
        "approved_for_weekly_slot": False,
        "verdict": "negative",
        "status": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT",
        "stop_reasons": gate["blocking_reasons"],
        "organizer_confirmed_score": None,
        "weekly_slots_used": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate_tdkl88()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"TDKL VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    if args.require_submit and not report["ok_to_submit"]:
        print("AUTOMATIC SUBMISSION GATE: FAIL. NO UPLOAD PERMITTED.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
