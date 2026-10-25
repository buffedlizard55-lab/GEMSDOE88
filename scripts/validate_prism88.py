#!/usr/bin/env python3
"""Validate H88-PRISM research TIFF (fail-closed even under python -O)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import gates, grid  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

TIF = ROOT / "docs/downloads/gems88-prism88-piedmont-ridge-20261025-zeros-DO-NOT-SUBMIT.tif"
ZIP = TIF.with_suffix(".zip")
CARD = ROOT / "registry/prism88_run_card.json"


def _require(condition: object, message: object = "PRISM validation failed") -> None:
    if not condition:
        raise AssertionError(str(message))


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(require_submit: bool = False, root: Path = ROOT) -> int:
    root = Path(root)
    tif = root / "docs/downloads/gems88-prism88-piedmont-ridge-20261025-zeros-DO-NOT-SUBMIT.tif"
    zipped = tif.with_suffix(".zip")
    card_path = root / "registry/prism88_run_card.json"
    sample = root / "data/bridge/sample_submission.tif"
    faults = root / "data/bridge/existing_faults.tif"

    _require(
        sample.is_file() and sha(sample) == grid.SHA256_SAMPLE_SUBMISSION,
        "sample_submission.tif missing or SHA-256 mismatch",
    )
    _require(
        faults.is_file() and sha(faults) == grid.SHA256_EXISTING_FAULTS,
        "existing_faults.tif missing or SHA-256 mismatch",
    )
    card = json.loads(card_path.read_text())
    g = grid.load_grid(root / "data/bridge")
    report = gates.format_report(tif, sample, footprint=g.footprint)
    _require(report["ok"], report["problems"])
    _require(report["n_nonzero"] == 37654, f"unexpected n_nonzero: {report['n_nonzero']}")
    _require(report["nan_pixels"] == 0, f"unexpected nan_pixels: {report['nan_pixels']}")
    _require(report["min"] >= 0 and report["max"] <= 1, "values outside [0, 1]")
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        _require(np.isfinite(a).all(), "non-finite values in PRISM raster")
        _require(((a >= 0) & (a <= 1)).all(), "values outside [0, 1] in PRISM raster")
        _require((a[g.catalogue] > 0).sum() == 0, "positive values on catalogue")
        _require((a[~g.footprint] > 0).sum() == 0, "positive values outside footprint")
    with zipfile.ZipFile(zipped) as z:
        _require(z.namelist() == [tif.name] and z.testzip() is None, "invalid PRISM ZIP archive")
        _require(z.read(tif.name) == tif.read_bytes(), "PRISM ZIP member bytes mismatch")
    _require(sha(tif) == card["raster_sha256"], "PRISM TIFF SHA-256 mismatch")
    _require(sha(zipped) == card["zip_sha256"], "PRISM ZIP SHA-256 mismatch")
    _require(card["ok_to_download"] is True, "expected ok_to_download=True")
    _require(card["ok_to_submit"] is False, "expected ok_to_submit=False")
    _require(card["verdict"] == "negative", "expected verdict='negative'")
    if require_submit:
        print("PRISM require-submit: FAIL-CLOSED (ok_to_submit false)")
        return 2
    print("PRISM validation PASS (download YES, submit NO)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args()
    sys.exit(main(require_submit=args.require_submit))
