#!/usr/bin/env python3
"""Validate H88-PRISM research TIFF (fail-closed, Python -O safe)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import gates, grid  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

TIF = ROOT / "docs/downloads/gems88-prism88-piedmont-ridge-20261025-zeros-DO-NOT-SUBMIT.tif"
ZIP = TIF.with_suffix(".zip")
CARD = ROOT / "registry/prism88_run_card.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def require(cond: bool, msg: object = "PRISM validation gate failed") -> None:
    if not cond:
        raise AssertionError(str(msg))


def main(require_submit: bool = False) -> int:
    card = json.loads(CARD.read_text())
    sample = ROOT / "data/bridge/sample_submission.tif"
    catalogue = ROOT / "data/bridge/existing_faults.tif"
    require(sha(sample) == grid.SHA256_SAMPLE_SUBMISSION, "sample_submission.tif SHA-256 mismatch")
    require(sha(catalogue) == grid.SHA256_EXISTING_FAULTS, "existing_faults.tif SHA-256 mismatch")
    g = grid.load_grid()
    report = gates.format_report(TIF, sample, footprint=g.footprint)
    require(bool(report["ok"]), report["problems"])
    require(report["n_nonzero"] == 37654, "expected 37,654 positive pixels")
    require(report["nan_pixels"] == 0, "NaN pixels present")
    require(report["min"] >= 0 and report["max"] <= 1, "values outside [0, 1]")
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        require(bool(np.isfinite(a).all()), "non-finite values in TIFF")
        require(bool(((a >= 0) & (a <= 1)).all()), "values outside [0, 1]")
        require(int((a[g.catalogue] > 0).sum()) == 0, "positive pixels on mapped catalogue")
        require(int((a[~g.footprint] > 0).sum()) == 0, "positive pixels outside footprint")
    with zipfile.ZipFile(ZIP) as z:
        require(z.namelist() == [TIF.name], "ZIP member list mismatch")
        require(z.read(TIF.name) == TIF.read_bytes(), "ZIP member bytes mismatch")
    require(sha(TIF) == card["raster_sha256"], "TIFF SHA-256 mismatch")
    require(sha(ZIP) == card["zip_sha256"], "ZIP SHA-256 mismatch")
    require(card["ok_to_download"] is True, "ok_to_download must be True")
    require(card["ok_to_submit"] is False, "ok_to_submit must be False")
    require(card["verdict"] == "negative", "verdict must be negative")
    if require_submit:
        print("PRISM require-submit: FAIL-CLOSED (ok_to_submit false)")
        return 2
    print("PRISM validation PASS (download YES, submit NO)")
    return 0


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    return main(require_submit=args.require_submit)


if __name__ == "__main__":
    raise SystemExit(cli())
