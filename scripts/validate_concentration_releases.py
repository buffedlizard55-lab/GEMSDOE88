#!/usr/bin/env python3
"""Independent re-read validator for built CONCENTRATION releases (enforced under python -O)."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod  # noqa: E402

PARENT_SHA = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"


def _require(condition: object, message: object = "CONCENTRATION validation failed") -> None:
    if not condition:
        raise AssertionError(str(message))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root: Path = ROOT) -> None:
    root = Path(root)
    sample_path = root / "data/bridge/sample_submission.tif"
    faults_path = root / "data/bridge/existing_faults.tif"
    parent_path = root / "data/registry/h33_education.tif"
    _require(
        sha(sample_path) == grid_mod.SHA256_SAMPLE_SUBMISSION,
        "sample_submission.tif SHA-256 mismatch",
    )
    _require(
        sha(faults_path) == grid_mod.SHA256_EXISTING_FAULTS,
        "existing_faults.tif SHA-256 mismatch",
    )
    _require(sha(parent_path) == PARENT_SHA, "h33_education.tif SHA-256 mismatch")

    with rasterio.open(sample_path) as ds:
        grid = (ds.shape, ds.crs, ds.transform)
    with rasterio.open(faults_path) as ds:
        cat = ds.read(1)
    foot, mapped = np.isin(cat, [0, 1]), cat == 1
    distance = distance_transform_edt(~mapped)
    with rasterio.open(parent_path) as ds:
        parent = (ds.read(1) > 0) & foot
    with (root / "ledger/submissions.csv").open() as fh:
        all_rows = list(csv.DictReader(fh))
    rows = [r for r in all_rows if r["axis"] == "CONCENTRATION" and r["value"] == "15pct-1km-grad"]
    _require(len(rows) == 1, f"expected 1 15pct-1km-grad row, got {len(rows)}")
    all_ledger_hashes = {r["sha256"] for r in all_rows}
    _require(len(all_ledger_hashes) == len(all_rows), "duplicate sha256 in ledger/submissions.csv")
    for row in rows:
        for suffix, key, nan_outside in ((".tif", "sha256", True), ("-zeros.tif", "sha256_zeros", False)):
            path = root / "releases" / f"{row['id']}{suffix}"
            _require(path.is_file() and sha(path) == row[key], f"missing or SHA-mismatched {path}")
            with rasterio.open(path) as ds:
                arr = ds.read(1)
                _require((ds.shape, ds.crs, ds.transform) == grid, f"grid mismatch: {path}")
                _require(ds.count == 1 and ds.dtypes == ("float32",), f"band/dtype mismatch: {path}")
            _require(
                np.isfinite(arr[foot]).all() and np.isin(arr[foot], [0, 1]).all(),
                f"footprint finite/binary check failed: {path}",
            )
            _require(
                np.isnan(arr[~foot]).all() if nan_outside else np.all(arr[~foot] == 0),
                f"outside-footprint encoding check failed: {path}",
            )
            dots = (arr > 0) & foot
            _require(dots.sum() == 37_654 and not np.any(dots & mapped), f"dot count/catalogue overlap failed: {path}")
            _require(np.min(distance[dots]) > 2.0, f"2px collar check failed: {path}")
            moved = round(37_654 * float(row["pct_changed"]) / 100)
            _require(np.count_nonzero(parent & ~dots) == moved, f"dropped dot count mismatch: {path}")
            _require(np.count_nonzero(dots & ~parent) == moved, f"added dot count mismatch: {path}")
        print("PASS", row["id"], row["sha256"])


if __name__ == "__main__":
    main()
