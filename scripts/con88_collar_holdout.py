#!/usr/bin/env python3
"""Per-fold re-emission collar sweep for H88-CON88 (experiment 2 of 3).

Fixed-TIF holdout is 0 by construction when collar >= kernel radius.
Here dots are re-emitted inside each fold using distance to VISIBLE faults
only (withheld components hidden), shared evaluator, pooled terms.
Surface = exp2 blend (contributor votes still fixed: conservative bias kept
and disclosed). Collars: 2.236 (H33 parity) vs 3.0 (exp2 as built).
Final collar = argmax pooled HOLDOUT-DTI (pre-registered rule).

Historical only: IR-88-0AB98CD1-01 withdrew CON88 clearance. The shared literal
preflight now stops this experiment before scientific imports or writes.
"""
from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import json, sys
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import evaluate_holdout, spatial
from run_con88_experiment import spaced_topk

def load(p):
    with rasterio.open(ROOT / p) as ds: return ds.read(1)

def main():
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()
    foot = np.isfinite(load("data/bridge/sample_submission.tif"))
    cat = load("data/bridge/existing_faults.tif") == 1
    surf = 0.6 * np.load(ROOT / ".cache/con88_consensus.npy") + 0.4 * np.load(ROOT / ".cache/con88_ridge.npy")
    collars = {"collar2p236": 2.236, "collar3p0": 3.0}
    terms = {k: None for k in collars}
    budget_total = 37654
    for fold in spatial.folds(cat, foot, buffer_px=80):
        region, visible = fold["region"], fold["visible"]
        dvis = distance_transform_edt(~visible)
        quota = int(round(budget_total * region.sum() / foot.sum()))
        f = dict(region=region, truth=fold["truth"], visible=visible, masked_known=visible)
        for name, collar in collars.items():
            allowed = region & foot & (dvis > collar)
            dots = spaced_topk(surf, allowed, [(np.ones_like(allowed), quota)])
            pred = dots.astype(np.float64)
            _, t = evaluate_holdout.evaluate(pred, f, foot, block_side=200)
            terms[name] = t if terms[name] is None else terms[name] + t
            print(name, "fold", fold["fold"], "dots", int(dots.sum()), flush=True)
    pooled = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810, candidate="collar2p236")
    out = dict(evidence_class="HOLDOUT-DTI", evaluator_version=evaluate_holdout.VERSION,
               method="per-fold re-emission, collar vs visible only, whole-component quadrant folds, buffer 80px",
               pooled=pooled)
    (ROOT / "registry/con88_collar_holdout.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(json.dumps(pooled.get("scores", {}), indent=2, default=float))
    print(json.dumps(pooled.get("paired_differences", {}), indent=2, default=float))

if __name__ == "__main__":
    main()
