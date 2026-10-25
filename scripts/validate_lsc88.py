#!/usr/bin/env python3
"""Fail-closed re-validation of the H88-LSC deliverable against its run card.

Checks (no human inspector):
  * registry card == docs mirror; card verdict/ok_to_submit are consistent
    with the preregistered gate AND the binding literal 17GEMSDOE witness;
  * pinned SHA-256 verification of sample_submission.tif, existing_faults.tif,
    and dense_17gemdoe.tif;
  * TIFF + ZIP bytes match the SHA-256 recorded in the card; ZIP holds exactly
    the TIFF;
  * raster is single-band float32 on the exact sample grid, nodata None,
    all cells finite in [0, 1], zeros outside the footprint, zero on the
    catalogue, dot count equals the card;
  * file name carries DO-NOT-SUBMIT iff ok_to_submit is False;
  * name/note <= 140 characters;
  * --require-submit exits 2 fail-closed whenever ok_to_submit is False.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod, uniqueness  # noqa: E402

WITNESS_SHA256 = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"LSC88 VALIDATION FAILED: {msg}")


def validate_lsc88(root: Path = ROOT) -> dict:
    root = Path(root)
    card = json.loads((root / "registry/lsc88_run_card.json").read_text())
    mirror = json.loads((root / "docs/data/lsc88_run_card.json").read_text())
    require(card == mirror, "docs/data mirror differs from registry card")

    sample_path = root / "data/bridge/sample_submission.tif"
    catalogue_path = root / "data/bridge/existing_faults.tif"
    witness_path = root / "data/registry/dense_17gemdoe.tif"
    require(sample_path.is_file() and catalogue_path.is_file(), "bridge validation rasters missing")
    require(sha256(sample_path) == grid_mod.SHA256_SAMPLE_SUBMISSION, "sample_submission.tif SHA-256 mismatch")
    require(sha256(catalogue_path) == grid_mod.SHA256_EXISTING_FAULTS, "existing_faults.tif SHA-256 mismatch")

    tif = root / "docs/downloads" / card["submission_file"]
    zf = tif.with_suffix(".zip")
    require(tif.exists() and zf.exists(), "deliverable files missing")
    require(("DO-NOT-SUBMIT" in tif.name) is (not card["ok_to_submit"]), "DO-NOT-SUBMIT suffix inconsistent")
    require(sha256(tif) == card["sha256_tif"], "TIFF sha256 mismatch")
    require(sha256(zf) == card["sha256_zip"], "ZIP sha256 mismatch")
    with zipfile.ZipFile(zf) as z:
        require(z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes(), "ZIP content")

    grid = grid_mod.load_grid(root / "data" / "bridge")
    with rasterio.open(sample_path) as s:
        ref = (s.crs, s.width, s.height, s.transform)
    with rasterio.open(tif) as d:
        require(d.count == 1 and d.dtypes[0] == "float32", "band/dtype")
        require((d.crs, d.width, d.height, d.transform) == ref, "grid mismatch vs sample_submission")
        require(d.nodata is None, "nodata must be None")
        arr = d.read(1)
    require(bool(np.isfinite(arr).all()), "non-finite values")
    require(float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0, "values outside [0,1]")
    fp = grid.footprint
    require(float(np.abs(arr[~fp]).max(initial=0.0)) == 0.0, "non-zero outside footprint")
    require(float(arr[grid.catalogue].max(initial=0.0)) == 0.0, "non-zero on catalogue")
    n_dots = int((arr > 0).sum())
    require(n_dots == card["fingerprint"]["dots"], f"dot count {n_dots} != card")

    literal_overlap = float(card["uniqueness"].get("worst_literal_overlap_3px", 1.0))
    if witness_path.is_file():
        require(sha256(witness_path) == WITNESS_SHA256, "dense_17gemdoe.tif SHA-256 mismatch")
        with rasterio.open(witness_path) as wds:
            witness = wds.read(1)
        literal_overlap = float(uniqueness.dot_overlap(arr, witness, 3))
        require(literal_overlap == 1.0, f"expected literal witness overlap 1.0, got {literal_overlap}")

    gates = {
        "lane_pass": bool(card["holdout"]["exp1_lane_pass"]),
        "uniqueness_like_for_like_pass": bool(card["uniqueness"]["passed"]),
        "literal_dense_witness_pass": bool(literal_overlap <= 0.70),
        "fingerprint_pass": bool(card["fingerprint_pass"]),
    }
    expected = bool(
        gates["lane_pass"]
        and gates["uniqueness_like_for_like_pass"]
        and gates["literal_dense_witness_pass"]
        and gates["fingerprint_pass"]
    )
    require(card["ok_to_submit"] is False and expected is False, "ok_to_submit must remain False under literal witness + failed fingerprint")
    require(card["verdict"] == "negative", "verdict must be negative")
    require(card["ok_to_download"] is True and card["validator"]["all_checks_passed"] is True, "validator")
    require(0 < len(card["submission_name"]) <= 140 and 0 < len(card["submission_note"]) <= 140, "name/note length")

    return {
        "ok": True,
        "file": tif.name,
        "sha256": card["sha256_tif"],
        "dots": n_dots,
        "literal_witness_overlap_3px": literal_overlap,
        "ok_to_download": card["ok_to_download"],
        "ok_to_submit": card["ok_to_submit"],
        "verdict": card["verdict"],
        "gates": gates,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-submit",
        action="store_true",
        help="Exit 2 unless ok_to_submit is True.",
    )
    args = parser.parse_args(argv)
    report = validate_lsc88(ROOT)
    print(json.dumps(report, indent=1))
    if args.require_submit and not report["ok_to_submit"]:
        print(
            "AUTOMATIC SUBMISSION GATE: DO NOT SUBMIT "
            "(fingerprint gate failed + literal 17GEMSDOE witness overlap = 1.0 > 0.70; exit 2).",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
