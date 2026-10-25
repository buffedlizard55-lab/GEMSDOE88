#!/usr/bin/env python3
"""Zero-human-input validator for the H88-PSGV artifacts (no manual inspection).

Re-opens the emitted .tif and one-member .zip with rasterio + tifffile and checks,
line by line: SHA-256 vs run card, classic TIFF, single band float32, EPSG:32611,
3730x3292, exact sample geotransform, nodata=None, all 12,279,160 cells finite in
{0.0,1.0} subset [0,1] (the portal sentence "Predicted values must be in range
[0, 1]"), ZIP byte identity, mirrored run-card/gate copies identical.

Exit 0 = OK TO DOWNLOAD (research integrity).  With --require-submit, exit 2
while ok_to_submit is False (binding literal-witness rule + selector step).
A local PASS is never an organizer score or acceptance guarantee.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
import tifffile

ROOT = Path(__file__).resolve().parents[1]
EXPECT_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args()
    rc_paths = [ROOT / "registry/psgv88_run_card.json", ROOT / "docs/data/psgv88_run_card.json",
                ROOT / "evidence/psgv88_run_card.json"]
    gv_paths = [ROOT / "registry/psgv88_gate_v3.json", ROOT / "docs/data/psgv88_gate_v3.json"]
    for p in rc_paths + gv_paths:
        if not p.is_file():
            print(f"FAIL missing {p}"); return 1
    if len({p.read_text(encoding="utf-8") for p in rc_paths}) != 1:
        print("FAIL mirrored run cards differ"); return 1
    if len({p.read_text(encoding="utf-8") for p in gv_paths}) != 1:
        print("FAIL mirrored gate docs differ"); return 1
    rc = json.loads(rc_paths[0].read_text(encoding="utf-8"))
    tif = ROOT / rc["download"]; zip_p = ROOT / rc["zip_download"]
    checks = {}
    checks["tif_sha256_matches_run_card"] = sha256(tif) == rc["raster_sha256"]
    checks["zip_sha256_matches_run_card"] = sha256(zip_p) == rc["zip_sha256"]
    raw = tif.read_bytes()
    checks["classic_tiff_magic"] = raw[:4] in (b"II*\x00", b"MM\x00*")
    with zipfile.ZipFile(zip_p) as z:
        checks["zip_single_member"] = z.namelist() == [tif.name]
        checks["zip_member_byte_identical"] = z.read(tif.name) == raw
        checks["zip_testzip_ok"] = z.testzip() is None
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        checks["one_band"] = ds.count == 1
        checks["dtype_float32"] = ds.dtypes[0] == "float32"
        checks["crs_epsg_32611"] = ds.crs is not None and ds.crs.to_epsg() == 32611
        checks["shape_3730x3292"] = (ds.height, ds.width) == (3730, 3292)
        checks["transform_exact"] = tuple(ds.transform)[:6] == EXPECT_TRANSFORM
        checks["nodata_undeclared"] = ds.nodata is None
    checks["all_finite_12279160"] = bool(np.isfinite(a).all() and a.size == 12_279_160)
    checks["strict_range_0_1"] = bool(np.all((a >= 0) & (a <= 1)))
    checks["binary_0_1_only"] = set(np.unique(a).tolist()) <= {0.0, 1.0}
    checks["dot_count_matches_run_card"] = int((a > 0).sum()) == int(rc["validator_output"]["positive_dots"])
    b = tifffile.imread(io.BytesIO(raw))
    checks["second_decoder_tifffile_equal"] = bool(b.shape == a.shape and np.array_equal(b.astype(np.float32), a))
    checks["note_le_140"] = len(rc["submission_note"]) <= 140 and len(rc["submission_name"]) <= 140
    ok = all(checks.values())
    print(json.dumps({"file": rc["download"], "sha256": rc["raster_sha256"], "checks": checks,
                      "all_checks_passed": ok, "ok_to_download": rc["ok_to_download"],
                      "ok_to_submit": rc["ok_to_submit"], "verdict": rc["verdict"],
                      "submission_name": rc["submission_name"], "submission_note": rc["submission_note"],
                      "note": "Local format/range validation only; not organizer acceptance or a score."}, indent=2))
    if not ok:
        return 1
    if args.require_submit and not rc["ok_to_submit"]:
        print("DO NOT SUBMIT (see blocking_reasons in run card)")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
