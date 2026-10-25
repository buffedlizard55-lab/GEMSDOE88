#!/usr/bin/env python3
"""Independent saved-byte validator for the H88-MTAS research GeoTIFF.

Re-opens the TIFF and ZIP from disk (rasterio + tifffile second decoder),
re-derives every portal-format fact, recomputes the dense-witness and H33
3-pixel overlaps, and cross-checks the run card.  Exit 0 = research file is
exactly what the run card says.  ``--require-submit`` exits 2 because the
automated verdict is negative (literal duplicate + holdout below bar); a
local format PASS is never organizer acceptance.
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
from gems57 import grid as grid_mod  # noqa: E402
from gems57.uniqueness import dot_overlap  # noqa: E402

CARD = ROOT / "registry/mtas88_experiment_run_card.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args()
    card = json.loads(CARD.read_text())
    tif = ROOT / card["raster_file"]
    zip_path = ROOT / card["zip_file"]
    problems: list[str] = []

    if sha256_file(tif) != card["raster_sha256"]:
        problems.append("TIFF SHA-256 differs from run card")
    if sha256_file(zip_path) != card["zip_sha256"]:
        problems.append("ZIP SHA-256 differs from run card")
    with zipfile.ZipFile(zip_path) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            problems.append("ZIP is not exactly one identical TIFF member")

    grid = grid_mod.load_grid(ROOT / "data/bridge")
    with rasterio.open(tif) as src:
        a = src.read(1)
        if src.count != 1:
            problems.append(f"band count {src.count} != 1")
        if src.dtypes[0] != "float32":
            problems.append(f"dtype {src.dtypes[0]} != float32")
        if (src.height, src.width) != (grid_mod.HEIGHT, grid_mod.WIDTH):
            problems.append("shape mismatch vs pinned grid")
        if str(src.crs) != "EPSG:32611":
            problems.append(f"CRS {src.crs} != EPSG:32611")
        if tuple(src.transform)[:6] != tuple(grid_mod.TRANSFORM)[:6]:
            problems.append("transform mismatch vs sample submission")
        if src.nodata is not None:
            problems.append(f"nodata declared ({src.nodata}); expected none (zeros policy)")
    try:
        import tifffile
        b = tifffile.imread(tif)
        if not np.array_equal(np.nan_to_num(b, nan=-1.0), np.nan_to_num(a, nan=-1.0)):
            problems.append("second decoder (tifffile) disagrees with rasterio")
    except ImportError:
        print("WARN tifffile unavailable; second-decoder check skipped")

    if not np.isfinite(a).all():
        problems.append("non-finite values present")
    if float(a.min()) < 0.0 or float(a.max()) > 1.0:
        problems.append(f"values outside [0,1]: min={a.min()} max={a.max()}")
    uniq = np.unique(a)
    if not set(float(x) for x in uniq).issubset({0.0, 1.0}):
        problems.append(f"non-binary values present: {uniq[:5]}")
    n_dots = int((a > 0).sum())
    if n_dots != card["production"]["fingerprint"]["n_dots"]:
        problems.append("dot count differs from run card fingerprint")
    if int((a[grid.catalogue] > 0).sum()) != 0:
        problems.append("positive pixels on mapped catalogue")
    if int((a[~grid.footprint] > 0).sum()) != 0:
        problems.append("positive pixels outside footprint")

    with rasterio.open(ROOT / "data/registry/dense_17gemdoe.tif") as src:
        dense_ov = float(dot_overlap(a, src.read(1), radius_px=3.0))
    if abs(dense_ov - card["final_uniqueness"]["literal_dense_witness_overlap_3px"]) > 1e-9:
        problems.append("dense-witness overlap differs from run card")
    with rasterio.open(ROOT / "data/registry/h33_education.tif") as src:
        h33_ov = float(dot_overlap(a, src.read(1), radius_px=3.0))

    if len(card["submission_note"]) > 140 or len(card["submission_name"]) > 140:
        problems.append("submission name/note exceeds 140 chars")
    if card["ok_to_submit"] is not False or card["verdict"] != "negative":
        problems.append("run card does not record the negative fail-closed verdict")

    report = dict(
        file=card["raster_file"], sha256=card["raster_sha256"], n_dots=n_dots,
        min=float(a.min()), max=float(a.max()), n_nan=int(np.isnan(a).sum()),
        dense_witness_overlap_3px=dense_ov, h33_overlap_3px=h33_ov,
        problems=problems, format_ok=not problems,
        ok_to_download_for_research=bool(not problems),
        ok_to_submit=False,
        note="Local format/identity audit only; NOT organizer acceptance.",
    )
    print(json.dumps(report, indent=2))
    if problems:
        return 1
    if args.require_submit:
        print("DO NOT SUBMIT: automated verdict is negative "
              "(literal duplicate vs dense witness; HOLDOUT-DTI below bar)")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
