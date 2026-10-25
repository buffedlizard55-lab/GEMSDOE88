#!/usr/bin/env python3
"""Independent CXL-88 audit: holdout evidence + negative verdict + archived HGVC TIFF format.

Exits 0 when the negative verdict is correctly recorded. --require-submit exits 2
(no CXL raster was promoted; none may be submitted).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]
HGVC_BAR = 0.2029470713394289


def main() -> int:
    ho = json.loads((ROOT / "evidence/cxl88_holdout_20261025.json").read_text())
    card = json.loads((ROOT / "registry/cxl88_run_card.json").read_text())
    cand = ho["pooled_overall"]["scores"]["exp02_cxl_poe_conduit"]
    phys = ho["pooled_overall"]["scores"]["phys44_zero_cat"]
    assert ho["evaluator_version"] == "gems57-pooled-hide-v2"
    assert cand["withheld_positive_pixels"] == 22893
    assert abs(phys["dti"] - 0.1041632406049392) < 1e-6, "phys44 control must reproduce stored value"
    assert ho["canary"]["passed"] and ho["canary"]["max_symmetric_auc"] <= 0.90
    assert cand["dti"] < HGVC_BAR and ho["beats_stored_hgvc"] is False
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False and card["new_tif_generated"] is False
    # Independently re-audit the archived best research TIFF (HGVC) format.
    import rasterio
    tif = ROOT / "docs/downloads/gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.tif"
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ref, rasterio.open(tif) as ds:
        a = ds.read(1)
        assert ds.count == 1 and str(ds.crs) == str(ref.crs) and ds.shape == ref.shape and ds.transform == ref.transform
        assert np.isfinite(a).all() and float(a.min()) >= 0.0 and float(a.max()) <= 1.0 and ds.nodata is None
    print(f"CXL88 AUDIT PASS: candidate HOLDOUT-DTI={cand['dti']:.6f} < HGVC bar {HGVC_BAR}; "
          f"phys44 control reproduced {phys['dti']:.6f}; canary max={ho['canary']['max_symmetric_auc']}; "
          "verdict=negative; NO new TIF; archived HGVC TIFF format [0,1]/finite/CRS-shape-transform PASS")
    if "--require-submit" in sys.argv:
        print("DO NOT SUBMIT: no CXL candidate passed the promotion gate", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
