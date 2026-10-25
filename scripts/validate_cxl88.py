#!/usr/bin/env python3
"""Independent CXL-88 audit: holdout evidence + negative verdict + archived HGVC TIFF format.

Exits 0 when the negative verdict is correctly recorded. --require-submit exits 2
(no CXL raster was promoted; none may be submitted). Python -O safe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]
HGVC_BAR = 0.2029470713394289
SAMPLE_SHA256 = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"


def require(cond: bool, msg: str = "CXL88 validation gate failed") -> None:
    if not cond:
        raise AssertionError(msg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args([] if argv is None and __name__ != "__main__" else argv)

    ho = json.loads((ROOT / "evidence/cxl88_holdout_20261025.json").read_text())
    card = json.loads((ROOT / "registry/cxl88_run_card.json").read_text())
    cand = ho["pooled_overall"]["scores"]["exp02_cxl_poe_conduit"]
    phys = ho["pooled_overall"]["scores"]["phys44_zero_cat"]
    require(ho["evaluator_version"] == "gems57-pooled-hide-v2", "unexpected evaluator_version")
    require(cand["withheld_positive_pixels"] == 22893, "unexpected withheld_positive_pixels")
    require(abs(phys["dti"] - 0.1041632406049392) < 1e-6, "phys44 control must reproduce stored value")
    require(bool(ho["canary"]["passed"]) and ho["canary"]["max_symmetric_auc"] <= 0.90, "canary check failed")
    require(cand["dti"] < HGVC_BAR and ho["beats_stored_hgvc"] is False, "CXL candidate must remain below HGVC bar")
    require(
        card["verdict"] == "negative" and card["ok_to_submit"] is False and card["new_tif_generated"] is False,
        "CXL run card must record negative verdict with no new TIFF",
    )
    # Independently re-audit the archived best research TIFF (HGVC) format.
    import rasterio

    sample = ROOT / "data/bridge/sample_submission.tif"
    require(hashlib.sha256(sample.read_bytes()).hexdigest() == SAMPLE_SHA256, "sample_submission.tif SHA-256 mismatch")
    tif = ROOT / "docs/downloads/gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.tif"
    with rasterio.open(sample) as ref, rasterio.open(tif) as ds:
        a = ds.read(1)
        require(
            ds.count == 1 and str(ds.crs) == str(ref.crs) and ds.shape == ref.shape and ds.transform == ref.transform,
            "HGVC reference grid mismatch",
        )
        require(
            bool(np.isfinite(a).all()) and float(a.min()) >= 0.0 and float(a.max()) <= 1.0 and ds.nodata is None,
            "HGVC finite/[0,1]/nodata check failed",
        )
    print(
        f"CXL88 AUDIT PASS: candidate HOLDOUT-DTI={cand['dti']:.6f} < HGVC bar {HGVC_BAR}; "
        f"phys44 control reproduced {phys['dti']:.6f}; canary max={ho['canary']['max_symmetric_auc']}; "
        "verdict=negative; NO new TIF; archived HGVC TIFF format [0,1]/finite/CRS-shape-transform PASS"
    )
    if args.require_submit:
        print("DO NOT SUBMIT: no CXL candidate passed the promotion gate", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
