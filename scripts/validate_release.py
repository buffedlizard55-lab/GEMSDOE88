#!/usr/bin/env python3
"""Independent automatic RELEASE preflight, including hard-negative uniqueness.

`--require-submit` exits 2 unless every gate clears; CI without it verifies
that the published page/receipt tells the truth even for a negative deliverable.
Do not use a successful CI check as permission to upload: read `ok_to_submit`.
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
from gems57 import grid, gates, uniqueness, validate  # noqa: E402 -- vendor path above


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def release_report(root=ROOT):
    root = Path(root)
    card = json.loads((root / "registry" / "run_card.json").read_text())
    published_card = json.loads((root / "docs" / "data" / "run-card.json").read_text())
    holdout = json.loads((root / "registry" / "holdout_result.json").read_text())
    canaries = json.loads((root / "registry" / "leakage_canaries.json").read_text())
    if card != published_card:
        raise ValueError("website scientific run card differs from repository receipt")
    primary = holdout["scores"]["candidate"]
    recorded = card["holdout_dti"]
    if (
        primary["dti"] != recorded["candidate"]
        or primary["ci95"] != recorded["ci95"]
        or primary["withheld_positive_pixels"] != recorded["withheld_positives"]
        or holdout["evaluator_version"] != recorded["version"]
        or canaries["max_symmetric_auc"] != card["canary_max_auc"]
    ):
        raise ValueError(
            "website score/CI/canary claim lacks matching experiment evidence"
        )
    if canaries["max_symmetric_auc"] > 0.90 or not canaries["passed"]:
        raise ValueError("leakage canary warning: do not trust fitted score")
    receipt_file = root / "docs" / "downloads" / f"{card['submission_name']}.json"
    receipt = json.loads(receipt_file.read_text())
    tif = root / "docs" / card["downloadable_file"]
    zipfile_path = tif.with_suffix(".zip")
    gd = grid.load_grid(root / "data" / "bridge")
    sample = root / "data" / "bridge" / "sample_submission.tif"
    mapped = root / "data" / "bridge" / "existing_faults.tif"
    if (
        digest(sample) != grid.SHA256_SAMPLE_SUBMISSION
        or digest(mapped) != grid.SHA256_EXISTING_FAULTS
    ):
        raise ValueError("owner-mirror grid/label SHA256 differs from pinned files")
    if not tif.is_file() or not zipfile_path.is_file():
        raise FileNotFoundError("TIF/ZIP not present")
    with rasterio.open(sample) as ref:
        ref_grid = (ref.shape, ref.crs, ref.transform)
    report = gates.format_report(tif, sample, footprint=gd.footprint)
    local = validate.validate(tif, gd.footprint, gd.catalogue)
    with rasterio.open(tif) as ds:
        raster = ds.read(1)
        exact_grid = (ds.shape, ds.crs, ds.transform) == ref_grid
    if not report["ok"] or not local["all_checks_passed"] or not exact_grid:
        raise ValueError("TIFF local format/footprint/range preflight FAILED")
    if not np.isfinite(raster[gd.footprint]).all() or np.any(
        raster[~gd.footprint] != 0
    ):
        raise ValueError("candidate invalid in/outside footprint")
    sha = digest(tif)
    if sha != card["raster_sha256"] or sha != receipt["sha256"]:
        raise ValueError("raster/receipt/card SHA mismatch")
    if (
        card["submission_name"] != receipt["submission_name"]
        or card["submission_note"] != receipt["note"]
    ):
        raise ValueError("name/note disagreement")
    if len(card["submission_note"]) > 140 or len(card["submission_name"]) > 140:
        raise ValueError("submission note/name exceeds 140 characters")
    with zipfile.ZipFile(zipfile_path) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP must contain exact one matching TIFF")
    if digest(zipfile_path) != receipt["zip_sha256"]:
        raise ValueError("ZIP SHA mismatch")
    witness = root / "data" / "registry" / "dense_17gemdoe.tif"
    if (
        digest(witness)
        != "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    ):
        raise ValueError("witness hash mismatch")
    cert = uniqueness.saturation_certificate(
        witness, gd.footprint, gd.catalogue, expected_grid=ref_grid
    )
    with rasterio.open(witness) as ds:
        prior = ds.read(1)
    measured = uniqueness.dot_overlap(
        raster, (np.isfinite(prior) & (prior > 0)) & gd.footprint, 3
    )
    duplicate = bool(measured > 0.70)
    if (
        cert["universal_overlap_blocker"] != duplicate
        or abs(
            measured
            - card["correlation_overlap_vs_registry"]["final_dots"]["dense_prior"][
                "forward_dot_overlap_3px"
            ]
        )
        > 1e-9
    ):
        raise ValueError("prior/release overlap assertion stale")
    release_ok = bool(
        report["ok"]
        and local["all_checks_passed"]
        and not duplicate
        and card["verdict"] == "promote-to-selector-only"
    )
    # A selector is a SEPARATE step. Promotion is never auto-approval of a slot.
    submit_ok = bool(release_ok and card["ok_to_submit"])
    if submit_ok != bool(card["ok_to_submit"]):
        raise ValueError("page card conflicts with independent local/uniqueness gate")
    if not bool(card["ok_to_download"]):
        raise ValueError("research download availability is misreported")
    return dict(
        format_ok=True,
        inside_no_nan=True,
        values_0_1=True,
        crs_shape_transform_match=True,
        output_sha256=sha,
        zip_one_matching_tif=True,
        registry_witness_sha256=cert["witness_sha256"],
        registry_forward_overlap_3px=measured,
        literal_duplicate=duplicate,
        ok_to_download=card["ok_to_download"],
        ok_to_submit=submit_ok,
        status="DO NOT SUBMIT: duplicate under literal registry rule"
        if duplicate
        else "selector approval required before submission",
        grid_provenance="owner-hosted mirror; not independent organizer authentication",
        checked_against="data/bridge/sample_submission.tif; data/registry/dense_17gemdoe.tif",
    )


def main():
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
    sys.exit(main())
