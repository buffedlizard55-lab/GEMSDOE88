#!/usr/bin/env python3
"""CON88 experiment 3: uniqueness-margin blend. Adopted only if worst
contributor/H33 overlap <=0.65 AND >=60% dots corroborated by >=2 contributors."""
from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT / "scripts"))
from gems57 import metric
from gems57.uniqueness import dot_overlap
from run_con88_experiment import spaced_topk, CONTRIBUTORS, N_DOTS, COLLAR_PX

def load(p):
    with rasterio.open(ROOT / p) as ds: return ds.read(1)

def main():
    sample = load("data/bridge/sample_submission.tif"); foot = np.isfinite(sample)
    cat = load("data/bridge/existing_faults.tif") == 1
    dcat = distance_transform_edt(~cat).astype(np.float32)
    h33 = load("data/registry/h33_education.tif"); h33d = dcat[np.isfinite(h33) & (h33 > 0)]
    bins = [(3.0, 5.0), (5.0, 10.0), (10.0, 25.0), (25.0, np.inf)]
    shares = [float(((h33d > lo) & (h33d <= hi)).mean()) for lo, hi in bins]
    shares[0] += float((h33d <= 3.0).mean())
    quotas = [int(round(s * N_DOTS)) for s in shares]; quotas[-1] += N_DOTS - sum(quotas)
    weights = [0.25, 0.375, 0.375]  # down-weight GATE49 (worst overlap 0.6936 in exp2)
    votes, near, carr = [], [], {}
    for (name, p), w in zip(CONTRIBUTORS.items(), weights):
        a = load(p); carr[name] = a
        dist = distance_transform_edt(~(np.isfinite(a) & (a > 0)))
        votes.append(w * metric.kernel(dist).astype(np.float32)); near.append(dist <= 3.0)
    consensus_w = np.sum(votes, axis=0)
    ridge = np.load(ROOT / ".cache/con88_ridge.npy")
    surf = 0.5 * consensus_w + 0.5 * ridge
    allowed = foot & (dcat > COLLAR_PX)
    dots = spaced_topk(surf, allowed, [(((dcat > lo) & (dcat <= hi)), q) for (lo, hi), q in zip(bins, quotas)])
    n_agree = np.sum(near, axis=0)
    stats = dict(n_dots=int(dots.sum()), corroborated_ge2=float((n_agree[dots] >= 2).mean()),
                 overlap_vs_h33=dot_overlap(dots.astype(np.float32), h33),
                 overlaps={k: dot_overlap(dots.astype(np.float32), v) for k, v in carr.items()})
    print(json.dumps(stats, indent=2))
    worst = max([stats["overlap_vs_h33"], *stats["overlaps"].values()])
    if not (worst <= 0.65 and stats["corroborated_ge2"] >= 0.60):
        print("REJECT exp3, keep exp2"); return 1
    pred = np.zeros(sample.shape, np.float32); pred[dots] = 1.0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"gems88-con88-consensus-ridge-{int(dots.sum())}dots-{stamp}-zeros-DO-NOT-SUBMIT"
    note = "H88-CON88 consensus(49,70,BPWD)+label-blind ridge; 3px collar 2.83px spacing H33-profile; DO NOT SUBMIT"
    from gems57.submission_writer import write_submission
    r = write_submission(ROOT / "docs/downloads" / f"{name}.tif", pred,
                         ROOT / "data/bridge/sample_submission.tif", foot,
                         note=note, name=name, catalogue=cat, metadata=dict(exp3=stats))
    np.save(ROOT / ".cache/con88_consensus.npy", (2 * consensus_w))  # keep canary scale-free (AUC invariant)
    (ROOT / "registry/con88_exp3.json").write_text(json.dumps(dict(stats=stats, file=r["file"], sha256=r["sha256"]), indent=2) + "\n")
    print("ADOPTED", r["file"], r["sha256"]); return 0

if __name__ == "__main__":
    raise SystemExit(main())
