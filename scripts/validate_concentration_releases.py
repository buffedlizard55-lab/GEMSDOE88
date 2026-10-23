#!/usr/bin/env python3
"""Independent re-read validator for built CONCENTRATION releases."""
from __future__ import annotations
import csv
import hashlib
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        grid = (ds.shape, ds.crs, ds.transform)
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        cat = ds.read(1)
    foot, mapped = np.isin(cat, [0, 1]), cat == 1
    distance = distance_transform_edt(~mapped)
    with rasterio.open(ROOT / "data/registry/h33_education.tif") as ds:
        parent = (ds.read(1) > 0) & foot
    rows = list(csv.DictReader((ROOT / "ledger/submissions.csv").open()))
    rows = [r for r in rows if r["axis"] == "CONCENTRATION"]
    # Mainline reconciliation removed semantically duplicate 10%/20% arms;
    # this branch contributes the unique official-gradient 15% dose only.
    rows = [r for r in rows if r["value"] == "15pct-1km-grad"]
    assert len(rows) == 1
    all_ledger_hashes = {r["sha256"] for r in list(csv.DictReader((ROOT / "ledger/submissions.csv").open()))}
    assert len(all_ledger_hashes) == sum(1 for _ in csv.DictReader((ROOT / "ledger/submissions.csv").open()))
    for row in rows:
        for suffix, key, nan_outside in ((".tif", "sha256", True), ("-zeros.tif", "sha256_zeros", False)):
            path = ROOT / "releases" / f"{row['id']}{suffix}"
            assert path.is_file() and sha(path) == row[key]
            with rasterio.open(path) as ds:
                arr = ds.read(1)
                assert (ds.shape, ds.crs, ds.transform) == grid
                assert ds.count == 1 and ds.dtypes == ("float32",)
            assert np.isfinite(arr[foot]).all() and np.isin(arr[foot], [0, 1]).all()
            assert np.isnan(arr[~foot]).all() if nan_outside else np.all(arr[~foot] == 0)
            dots = (arr > 0) & foot
            assert dots.sum() == 37_654 and not np.any(dots & mapped)
            assert np.min(distance[dots]) > 2.0
            moved = round(37_654 * float(row["pct_changed"]) / 100)
            assert np.count_nonzero(parent & ~dots) == moved
            assert np.count_nonzero(dots & ~parent) == moved
        print("PASS", row["id"], row["sha256"])

if __name__ == "__main__":
    main()
