#!/usr/bin/env python3
"""Independent fail-closed preflight for the canonical research artifact.

A successful default run means the file is reproducible and safe to download.
It does *not* mean it is safe to submit.  ``--require-submit`` exits 2 while any
scientific or literal registry gate is negative.  No competition API is called.
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
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import gates, grid, uniqueness, validate  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def release_report(root=ROOT):
    root = Path(root)
    card_paths = (
        root / "registry/run_card.json",
        root / "docs/data/run-card.json",
        root / "docs/run_card.json",
        root / "evidence/run-card.json",
    )
    card_texts = [p.read_text(encoding="utf-8") for p in card_paths]
    if len(set(card_texts)) != 1:
        raise ValueError("canonical run-card copies are not byte-identical")
    card = json.loads(card_texts[0])

    holdout = json.loads((root / "evidence/mrr88_holdout.json").read_text())
    canaries = json.loads((root / "evidence/mrr88_canaries.json").read_text())
    primary = holdout["scores"]["mrr_bpr_candidate"]
    paired = holdout["paired_differences"]["h88_adhr_incumbent"]
    recorded = card["holdout_dti"]
    if (
        primary["dti"] != recorded["candidate"]
        or primary["ci95"] != recorded["ci95"]
        or primary["withheld_positive_pixels"] != recorded["withheld_positive_pixels"]
        or holdout["evaluator_version"] != recorded["evaluator_version"]
        or paired["delta"] != recorded["paired_delta_vs_incumbent"]
        or paired["ci95"] != recorded["paired_delta_ci95"]
    ):
        raise ValueError("run-card HOLDOUT-DTI claim lacks matching experiment evidence")
    if not canaries["passed"] or canaries["max_symmetric_auc"] > 0.90:
        raise ValueError("leakage canary failed")
    if canaries != card["leakage_canary"]:
        raise ValueError("run-card canary evidence is stale")

    tif = root / card["artifact"]
    zip_path = root / card["zip_artifact"]
    receipt_path = tif.with_suffix(".json")
    if not tif.is_file() or not zip_path.is_file() or not receipt_path.is_file():
        raise FileNotFoundError("canonical TIFF/ZIP/writer receipt is missing")
    receipt = json.loads(receipt_path.read_text())

    gd = grid.load_grid(root / "data/bridge")
    sample = root / "data/bridge/sample_submission.tif"
    mapped = root / "data/bridge/existing_faults.tif"
    if digest(sample) != grid.SHA256_SAMPLE_SUBMISSION or digest(mapped) != grid.SHA256_EXISTING_FAULTS:
        raise ValueError("owner-mirror grid/label hash differs from pinned file")
    with rasterio.open(sample) as ref:
        ref_grid = (ref.shape, ref.crs, ref.transform)
    report = gates.format_report(tif, sample, footprint=gd.footprint)
    local = validate.validate(tif, gd.footprint, gd.catalogue)
    with rasterio.open(tif) as ds:
        raster = ds.read(1)
        exact_grid = (ds.shape, ds.crs, ds.transform) == ref_grid
    if not report["ok"] or not local["all_checks_passed"] or not exact_grid:
        raise ValueError("TIFF local format/footprint/range preflight failed")
    if not np.isfinite(raster).all() or np.any(raster[~gd.footprint] != 0):
        raise ValueError("candidate has non-finite or nonzero outside-footprint cells")
    if float(raster.min()) < 0 or float(raster.max()) > 1:
        raise ValueError("candidate lies outside [0,1]")

    sha = digest(tif)
    if sha != card["raster_sha256"] or sha != receipt["sha256"]:
        raise ValueError("raster/receipt/card hash mismatch")
    if card["submission_name"] != receipt["submission_name"] or card["submission_note"] != receipt["note"]:
        raise ValueError("name/note disagreement")
    if not (0 < len(card["submission_name"]) <= 140 and 0 < len(card["submission_note"]) <= 140):
        raise ValueError("name/note length invalid")
    with zipfile.ZipFile(zip_path) as archive:
        if archive.namelist() != [tif.name] or archive.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP must contain exactly one byte-identical TIFF")
    if digest(zip_path) != card["zip_sha256"] or digest(zip_path) != receipt["zip_sha256"]:
        raise ValueError("ZIP hash mismatch")

    # Recompute final-dot comparisons from the saved TIFF against all restored,
    # SHA-pinned registry rasters.  Do not rely only on the run card's maxima.
    inventory = json.loads((root / "registry/inventory.json").read_text())
    final_audit = uniqueness.compare_to_registry(
        tif,
        inventory,
        gd.footprint,
        include_reverse=True,
        expected_grid=ref_grid,
    )
    if (
        final_audit["registry_rasters_checked"] != len(inventory["rasters"])
        or not final_audit["complete_accessible_scan"]
        or final_audit["missing_or_invalid"]
        or not final_audit["byte_unique_among_checked"]
        or not final_audit["pixel_unique_among_checked"]
    ):
        raise ValueError("final registry scan is incomplete or candidate bytes/pixels are copied")
    rows_ok = [row for row in final_audit["rows"] if "error" not in row]
    max_final_rho = max(
        abs(float(row["spearman_full_footprint"]))
        for row in rows_ok if row.get("spearman_full_footprint") is not None
    )
    max_all_overlap = max(float(row["my_dots_within_3px_of_theirs"]) for row in rows_ok)
    max_sparse_overlap = max(
        float(row["my_dots_within_3px_of_theirs"])
        for row in rows_ok
        if int(row["their_dots"]) / int(gd.footprint.sum()) <= 0.20
    )
    registry_card = card["correlation_overlap_vs_registry"]
    if (
        abs(max_final_rho - registry_card["final_max_abs_spearman"]) > 1e-6
        or abs(max_all_overlap - registry_card["final_max_forward_overlap_3px_all_rasters"]) > 1e-6
        or abs(max_sparse_overlap - registry_card["final_max_forward_overlap_3px_sparse_rasters"]) > 1e-6
        or max_final_rho > 0.90
        or max_sparse_overlap > 0.70
    ):
        raise ValueError("final registry evidence is stale or sparse/rank uniqueness failed")

    # The continuous production surface is gated before allocation and recorded
    # because the surface itself is not a competition artifact.  Verify complete
    # hash-pinned row coverage and the recorded maximum here.
    surface_audit = json.loads((root / "evidence/mrr88_surface_uniqueness.json").read_text())
    surface_rows = [row for row in surface_audit["rows"] if "error" not in row]
    inventory_hashes = {entry["sha256"] for entry in inventory["rasters"]}
    surface_hashes = {row["sha256"] for row in surface_rows}
    max_surface_rho = max(
        abs(float(row["spearman_full_footprint"]))
        for row in surface_rows if row.get("spearman_full_footprint") is not None
    )
    if (
        surface_audit["registry_rasters_checked"] != len(inventory["rasters"])
        or not surface_audit["complete_accessible_scan"]
        or surface_audit["missing_or_invalid"]
        or surface_hashes != inventory_hashes
        or abs(max_surface_rho - registry_card["surface_preplacement_max_abs_spearman"]) > 1e-6
        or max_surface_rho > 0.90
    ):
        raise ValueError("pre-placement surface registry evidence is incomplete, stale, or duplicate")

    witness = root / "data/registry/dense_17gemdoe.tif"
    witness_sha = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    if digest(witness) != witness_sha:
        raise ValueError("registry witness hash mismatch")
    cert = uniqueness.saturation_certificate(
        witness, gd.footprint, gd.catalogue, expected_grid=ref_grid
    )
    with rasterio.open(witness) as ds:
        prior = ds.read(1)
    measured = uniqueness.dot_overlap(
        raster, (np.isfinite(prior) & (prior > 0)) & gd.footprint, 3
    )
    recorded_overlap = card["correlation_overlap_vs_registry"][
        "final_max_forward_overlap_3px_all_rasters"
    ]
    duplicate = bool(measured > 0.70)
    if not cert["universal_overlap_blocker"] or abs(measured - recorded_overlap) > 1e-9:
        raise ValueError("literal registry overlap evidence is stale")

    scientific_positive = bool(
        recorded["paired_delta_vs_incumbent"] > 0
        and recorded["paired_delta_ci95"][0] > 0
    )
    release_ok = bool(
        report["ok"] and local["all_checks_passed"] and not duplicate
        and scientific_positive and card["verdict"] == "promote"
    )
    submit_ok = bool(release_ok and card["ok_to_submit"])
    if submit_ok != bool(card["ok_to_submit"]):
        raise ValueError("run card conflicts with independently recomputed gates")
    if not card["ok_to_download"]:
        raise ValueError("valid research artifact is misreported as unavailable")

    return {
        "format_ok": True,
        "inside_no_nan": True,
        "all_finite_entire_raster": True,
        "values_0_1": True,
        "crs_shape_transform_match": True,
        "output_sha256": sha,
        "zip_one_matching_tif": True,
        "holdout_evaluator": recorded["evaluator_version"],
        "holdout_withheld_positive_pixels": recorded["withheld_positive_pixels"],
        "holdout_candidate_dti": recorded["candidate"],
        "holdout_candidate_ci95": recorded["ci95"],
        "paired_delta_vs_incumbent": recorded["paired_delta_vs_incumbent"],
        "paired_delta_ci95": recorded["paired_delta_ci95"],
        "registry_witness_sha256": cert["witness_sha256"],
        "registry_forward_overlap_3px": measured,
        "literal_duplicate": duplicate,
        "ok_to_download": True,
        "ok_to_submit": submit_ok,
        "status": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT",
        "stop_reasons": [
            "candidate HOLDOUT-DTI is below the paired recomputed incumbent",
            "literal registry overlap with full-footprint witness is 1.0 > 0.70",
        ],
        "grid_provenance": "owner-hosted mirror; not independent organizer authentication",
        "checked_against": "data/bridge/sample_submission.tif; data/registry/dense_17gemdoe.tif",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args()
    result = release_report()
    print(json.dumps(result, indent=2))
    if args.require_submit and not result["ok_to_submit"]:
        print("AUTOMATIC SUBMISSION GATE: FAIL. No upload permitted.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
