#!/usr/bin/env python3
"""Fail-closed re-validation of the H88-LSC deliverable against its run card.

Checks (no human inspector):
  * registry card == docs mirror; card verdict/ok_to_submit are consistent
    with the preregistered gate (lane pass AND uniqueness AND fingerprint);
  * TIFF + ZIP bytes match the SHA-256 recorded in the card; ZIP holds exactly
    the TIFF;
  * raster is single-band float32 on the exact sample grid, nodata None,
    all cells finite in [0, 1], zeros outside the footprint, zero on the
    catalogue, dot count equals the card;
  * file name carries DO-NOT-SUBMIT iff ok_to_submit is False;
  * name/note <= 140 characters.
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
sys.path.insert(0, str(ROOT / "vendor" / "gems57"))
from grid import load_grid  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"LSC88 VALIDATION FAILED: {msg}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args(argv)

    card = json.loads((ROOT / "registry/lsc88_run_card.json").read_text())
    mirror = json.loads((ROOT / "docs/data/lsc88_run_card.json").read_text())
    require(card == mirror, "docs/data mirror differs from registry card")
    gates = {
        "lane_pass": bool(card["holdout"]["exp1_lane_pass"]),
        "uniqueness_pass": bool(card["uniqueness"]["passed"]),
        "fingerprint_pass": bool(card["fingerprint_pass"]),
    }
    expected = bool(gates["lane_pass"] and gates["uniqueness_pass"] and gates["fingerprint_pass"])
    require(card["ok_to_submit"] is expected, "ok_to_submit inconsistent with gates")
    require(card["verdict"] == ("promote" if expected else "negative"), "verdict inconsistent")
    require(card["ok_to_download"] is True and card["validator"]["all_checks_passed"] is True, "validator")
    require(0 < len(card["submission_name"]) <= 140 and 0 < len(card["submission_note"]) <= 140, "name/note length")

    tif = ROOT / "docs/downloads" / card["submission_file"]
    zf = tif.with_suffix(".zip")
    require(tif.exists() and zf.exists(), "deliverable files missing")
    require(("DO-NOT-SUBMIT" in tif.name) is (not card["ok_to_submit"]), "DO-NOT-SUBMIT suffix inconsistent")
    require(sha256(tif) == card["sha256_tif"], "TIFF sha256 mismatch")
    require(sha256(zf) == card["sha256_zip"], "ZIP sha256 mismatch")
    with zipfile.ZipFile(zf) as z:
        require(z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes(), "ZIP content")

    grid = load_grid(ROOT / "data" / "bridge")
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as s:
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
    print(json.dumps({
        "ok": True, "file": tif.name, "sha256": card["sha256_tif"], "dots": n_dots,
        "ok_to_download": card["ok_to_download"], "ok_to_submit": card["ok_to_submit"],
        "verdict": card["verdict"], "gates": gates,
    }, indent=1))
    if args.require_submit and not card["ok_to_submit"]:
        print("DO NOT SUBMIT: H88-LSC verdict is negative (ok_to_submit=false).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
