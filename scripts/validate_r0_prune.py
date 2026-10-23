#!/usr/bin/env python3
"""Recompute R0/PRUNE3 and independently re-read both released GeoTIFFs.

This never writes a candidate, changes the ledger, or contacts a remote host.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems88.r0_prune import (  # noqa: E402
    R0_DOTS,
    R0_ZEROS_SHA256,
    prune3_refill,
    sha256_file,
    validate_release_raster,
    write_mask,
)
from run_r0_prune import LEDGER, RELEASES, WORK, read_rasters, verify_pins  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    verify_pins()
    card = json.loads(args.receipt.read_text(encoding="utf-8"))
    grid, support, d28, _ = read_rasters()
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    r0 = d28 & grid.footprint & (d_cat > 2.0)
    if int(r0.sum()) != R0_DOTS:
        raise ValueError("R0 count mismatch during independent validation")
    WORK.mkdir(exist_ok=True)
    r0_check = WORK / "validate-r0-zeros.tif"
    r0_hash = write_mask(r0_check, r0, grid.footprint, ROOT / "data" / "bridge" / "existing_faults.tif", nan_outside=False)
    if r0_hash != R0_ZEROS_SHA256:
        raise ValueError("R0 byte hash mismatch during independent validation")
    candidate, _, _, diff = prune3_refill(r0, support, d_cat)

    primary_path = RELEASES / card["primary"]["file"]
    zeros_path = RELEASES / card["zeros_fallback"]["file"]
    primary = validate_release_raster(
        primary_path, candidate, grid.footprint, grid.catalogue, d_cat,
        ROOT / "data" / "bridge" / "sample_submission.tif", nan_outside=True,
    )
    zeros = validate_release_raster(
        zeros_path, candidate, grid.footprint, grid.catalogue, d_cat,
        ROOT / "data" / "bridge" / "sample_submission.tif", nan_outside=False,
    )
    if primary["sha256"] != card["primary"]["sha256"] or zeros["sha256"] != card["zeros_fallback"]["sha256"]:
        raise ValueError("release hash differs from its run card")
    if card["id"] != args.receipt.name.removesuffix("-receipt.json"):
        raise ValueError("receipt filename and candidate ID differ")
    if not card["id"].endswith(primary["sha256"][:8]):
        raise ValueError("candidate ID does not contain primary SHA-256 prefix")
    for key in ("parent_dots", "candidate_dots", "unchanged_dots", "removed_parent_dots", "added_dots", "symmetric_difference_dots"):
        if card["parent_diff"][key] != diff[key]:
            raise ValueError(f"parent-diff mismatch: {key}")
    if not np.isclose(card["parent_diff"]["pct_parent_dots_changed"], diff["pct_parent_dots_changed"], rtol=0, atol=1e-12):
        raise ValueError("percent-changed mismatch")

    with LEDGER.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    matching = [row for row in rows if row["id"] == card["id"]]
    if len(matching) != 1:
        raise ValueError("ledger must contain exactly one row for the candidate")
    row = matching[0]
    if row["sha256"] != primary["sha256"] or row.get("sha256_zeros") != zeros["sha256"] or row["status"] != "BUILT":
        raise ValueError("ledger hash/status mismatch")
    if not np.isclose(float(row["pct_changed"]), diff["pct_parent_dots_changed"], rtol=0, atol=5e-10):
        raise ValueError("ledger percent-changed mismatch")
    candidate_hashes = {primary["sha256"], zeros["sha256"]}
    for other in rows:
        if other["id"] != card["id"] and candidate_hashes & {other.get("sha256"), other.get("sha256_zeros")}:
            raise ValueError("candidate hash duplicates another ledger row")

    # Historical exact-hash check only; never a similarity/overlap gate.
    historical = set()
    for directory in (ROOT / "data" / "registry", ROOT / "submissions", ROOT / "docs" / "downloads", RELEASES):
        if directory.is_dir():
            for path in directory.rglob("*.tif"):
                if path not in (primary_path, zeros_path):
                    historical.add(sha256_file(path))
    if primary["sha256"] in historical or zeros["sha256"] in historical:
        raise ValueError("candidate twin duplicates an accessible historical raster")

    result = {
        "schema": "gems88.r0-prune-independent-validation.v1",
        "id": card["id"],
        "ok": True,
        "r0_rebuilt_sha256": r0_hash,
        "primary": primary,
        "zeros_fallback": zeros,
        "parent_diff_recomputed": diff,
        "ledger_row": row,
        "historical_exact_hash_duplicate": False,
        "submission_slots_used": 0,
    }
    output = args.output or args.receipt.with_name(args.receipt.name.replace("-receipt.json", "-validation.json"))
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "id": card["id"], "validation": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
