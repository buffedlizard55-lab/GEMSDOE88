#!/usr/bin/env python3
"""Independent CXL-88 audit: holdout evidence + negative verdict + archived HGVC TIFF format.

Exits 0 when the negative verdict is correctly recorded. --require-submit exits 2
(no CXL raster was promoted; none may be submitted). Enforces checks under python -O.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import grid  # noqa: E402

HGVC_BAR = 0.2029470713394289


def _require(condition: object, message: object = "CXL88 validation failed") -> None:
    if not condition:
        raise AssertionError(str(message))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(root: Path = ROOT, argv: list[str] | None = None) -> int:
    root = Path(root)
    argv = sys.argv[1:] if argv is None else argv
    ho = json.loads((root / "evidence/cxl88_holdout_20261025.json").read_text())
    card = json.loads((root / "registry/cxl88_run_card.json").read_text())
    cand = ho["pooled_overall"]["scores"]["exp02_cxl_poe_conduit"]
    phys = ho["pooled_overall"]["scores"]["phys44_zero_cat"]
    _require(ho["evaluator_version"] == "gems57-pooled-hide-v2", "evaluator_version mismatch")
    _require(cand["withheld_positive_pixels"] == 22893, "withheld_positive_pixels mismatch")
    _require(
        abs(phys["dti"] - 0.1041632406049392) < 1e-6,
        "phys44 control must reproduce stored value",
    )
    _require(
        ho["canary"]["passed"] and ho["canary"]["max_symmetric_auc"] <= 0.90,
        "canary gate failed",
    )
    _require(
        cand["dti"] < HGVC_BAR and ho["beats_stored_hgvc"] is False,
        "candidate must record negative comparison against HGVC bar",
    )
    _require(
        card["verdict"] == "negative"
        and card["ok_to_submit"] is False
        and card["new_tif_generated"] is False,
        "run card must remain negative / ok_to_submit=False / new_tif_generated=False",
    )
    # Independently re-audit the archived best research TIFF (HGVC) format and sample pin.
    import rasterio

    sample = root / "data/bridge/sample_submission.tif"
    faults = root / "data/bridge/existing_faults.tif"
    _require(
        sample.is_file() and _sha256(sample) == grid.SHA256_SAMPLE_SUBMISSION,
        "sample_submission.tif missing or SHA-256 pin mismatch",
    )
    _require(
        faults.is_file() and _sha256(faults) == grid.SHA256_EXISTING_FAULTS,
        "existing_faults.tif missing or SHA-256 pin mismatch",
    )
    tif = root / "docs/downloads/gems88-hgvc88-updip-sinter-conduit-37654-20261024-d5329f31-zeros-DO-NOT-SUBMIT.tif"
    with rasterio.open(sample) as ref, rasterio.open(faults) as cds, rasterio.open(tif) as ds:
        ref_arr = ref.read(1)
        cat_arr = cds.read(1)
        a = ds.read(1)
        _require(
            ds.count == 1
            and str(ds.crs) == str(ref.crs)
            and ds.shape == ref.shape
            and ds.transform == ref.transform,
            "HGVC TIFF grid/CRS/transform mismatch",
        )
        _require(
            int(np.isnan(a).sum()) == 0
            and np.isfinite(a).all()
            and float(a.min()) >= 0.0
            and float(a.max()) <= 1.0
            and ds.nodata is None,
            "HGVC TIFF failed finite/[0,1]/nodata check",
        )
        _require(
            int((a[~np.isfinite(ref_arr)] != 0).sum()) == 0
            and int((a[cat_arr > 0] > 0).sum()) == 0,
            "HGVC TIFF failed outside-footprint zero or catalogue zero check",
        )
    print(
        f"CXL88 AUDIT PASS: candidate HOLDOUT-DTI={cand['dti']:.6f} < HGVC bar {HGVC_BAR}; "
        f"phys44 control reproduced {phys['dti']:.6f}; canary max={ho['canary']['max_symmetric_auc']}; "
        "verdict=negative; NO new TIF; archived HGVC TIFF format [0,1]/finite/CRS-shape-transform PASS"
    )
    if "--require-submit" in argv:
        print("DO NOT SUBMIT: no CXL candidate passed the promotion gate", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
