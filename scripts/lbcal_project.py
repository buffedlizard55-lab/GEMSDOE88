#!/usr/bin/env python3
"""MODEL-PROJECTION of arbitrary rasters under the LBCAL px1 receipt model (never a score).

Usage: python scripts/lbcal_project.py <tif> [<tif> ...]  -> JSON lines to stdout
"""
import json, sys
from pathlib import Path
import numpy as np, rasterio
ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT / "vendor")):
    sys.path.insert(0, p)
import lbcal_pixel as lp, lbcal_design as ld  # noqa: E402

def main(paths):
    foot, cat, omega = lp.grid_masks()
    fit = json.loads((ROOT / "data/lbcal/px_fit_px1cv.json").read_text())
    z = np.load(ROOT / "data/lbcal/px_prep.npz")
    fstats = json.loads(str(z["fstats"]))
    F = lp.feature_stack(omega, cat)
    q = ld.full_grid_q(np.array(fit["beta"]), fit["labels"], fstats, F); del F
    q[~omega] = 0
    G = float(q.sum())
    out = []
    for p in paths:
        with rasterio.open(p) as ds:
            a = ds.read(1).astype(np.float32); nod = ds.nodata
        if nod is not None and np.isfinite(nod): a[a == nod] = np.nan
        m = (np.nan_to_num(a) > 0) & omega
        d, T, Fp = ld.expected_dti_of_mask(q, m, G)
        r = {"file": str(p), "dots": int(m.sum()), "model_projected_dti": round(float(d), 4),
             "evidence_class": "MODEL-PROJECTION under LBCAL px1 (fit to USER-REPORTED LB receipts); not a score"}
        out.append(r); print(json.dumps(r), flush=True)
    return out

if __name__ == "__main__":
    main(sys.argv[1:])
