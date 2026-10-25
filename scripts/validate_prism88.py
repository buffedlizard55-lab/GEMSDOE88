#!/usr/bin/env python3
"""Validate H88-PRISM research TIFF (fail-closed)."""
import sys, json, hashlib, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import gates, grid
import rasterio, numpy as np

TIF = ROOT / "docs/downloads/gems88-prism88-piedmont-ridge-20261025-zeros-DO-NOT-SUBMIT.tif"
ZIP = TIF.with_suffix(".zip")
CARD = ROOT / "registry/prism88_run_card.json"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main(require_submit=False):
    card = json.loads(CARD.read_text())
    # Basic gates
    g = grid.load_grid()
    report = gates.format_report(TIF, ROOT / "data/bridge/sample_submission.tif", footprint=g.footprint)
    assert report["ok"], report["problems"]
    assert report["n_nonzero"] == 37654
    assert report["nan_pixels"] == 0
    assert report["min"] >= 0 and report["max"] <= 1
    with rasterio.open(TIF) as ds:
        a = ds.read(1)
        assert np.isfinite(a).all()
        assert ((a>=0)&(a<=1)).all()
        assert (a[g.catalogue] >0).sum() == 0
        assert (a[~g.footprint] >0).sum() == 0
    with zipfile.ZipFile(ZIP) as z:
        assert z.namelist() == [TIF.name]
        assert z.read(TIF.name) == TIF.read_bytes()
    assert sha(TIF) == card["raster_sha256"]
    assert sha(ZIP) == card["zip_sha256"]
    # Card says negative
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    if require_submit:
        print("PRISM require-submit: FAIL-CLOSED (ok_to_submit false)")
        return 2
    print("PRISM validation PASS (download YES, submit NO)")
    return 0

if __name__ == "__main__":
    sys.exit(main(require_submit="--require-submit" in sys.argv))
