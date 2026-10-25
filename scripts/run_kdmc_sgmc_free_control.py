#!/usr/bin/env python3
"""Confound control for Experiment 3: is the off-catalogue SGMC proxy margin circular?

``sgmc_logdist`` is column 100 of the KDMC feature stack and the Experiment 3
proxy truth is ``SGMC minus catalogue``.  A model that uses distance-to-SGMC
will place dots near SGMC and score well on an SGMC-derived truth for trivial
reasons.  This script refits the identical 4-quadrant out-of-fold PU density
with **every SGMC-derived column removed**, re-allocates with the identical
allocator and budget, and re-scores on the identical proxy.  The gap between
the two numbers is the size of the circularity.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import json, sys, time
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"vendor")]
from gems57 import grid as g57grid, holdout as g57holdout, metric            # noqa: E402
from gems88 import kdmc                                                      # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier                  # noqa: E402
sys.path.insert(0, str(ROOT/"scripts"))
from run_kdmc_collar_proxy import proxy_truth                                # noqa: E402

BANNED = ("sgmc",)
SEP, DENSITY, N_NEG = 2.8284271247461903, 0.01, 400_000

def log(*a): print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

def main() -> int:
    t0 = time.time()
    grid = g57grid.load_grid()
    with rasterio.open(ROOT/"data"/"bridge"/"sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    mm, names = kdmc.build_feature_stack(ROOT/"data", ROOT/"data"/"external", valid,
                                         ROOT/".cache"/"kdmc")
    keep = [j for j, n in enumerate(names) if not any(b in n.lower() for b in BANNED)]
    dropped = [names[j] for j in range(len(names)) if j not in keep]
    log(f"dropping {len(dropped)} SGMC-derived columns: {dropped}")
    flat = np.flatnonzero(valid.ravel())
    lin = np.full(valid.size, -1, np.int32); lin[flat] = np.arange(flat.size, dtype=np.int32)
    lin = lin.reshape(valid.shape)
    rows_for = lambda m: lin[m][lin[m] >= 0]

    quad = g57holdout.quadrant_ids(grid.footprint)
    near = ndi.distance_transform_edt(~grid.catalogue) <= 3
    rho = np.zeros(grid.shape, np.float32)
    for q in range(4):
        test = (quad == q) & grid.footprint
        train = grid.footprint & ~test
        pos = rows_for(grid.catalogue & train)
        pool = rows_for(train & ~near)
        rng = np.random.default_rng(88_000 + q)
        neg = rng.choice(pool, size=min(N_NEG, pool.size), replace=False)
        rws = np.sort(np.concatenate([pos, neg])); y = np.isin(rws, pos).astype(np.int8)
        log(f"  quadrant {g57holdout.FOLD_NAMES[q]}: {int(y.sum()):,}+ / {int((1-y).sum()):,}-")
        clf = HistGradientBoostingClassifier(
            max_iter=250, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=50,
            l2_regularization=1.0, early_stopping=False, random_state=88_000+q,
            class_weight={0: 1.0, 1: float((1-y).sum())/max(int(y.sum()), 1)})
        clf.fit(np.asarray(mm[rws], np.float32)[:, keep], y)
        tr = rows_for(test); out = np.empty(tr.size, np.float32)
        o = np.argsort(tr); srt = tr[o]
        for a in range(0, srt.size, 250_000):
            blk = srt[a:a+250_000]
            out[o[a:a+250_000]] = clf.predict_proba(
                np.asarray(mm[blk], np.float32)[:, keep])[:, 1].astype(np.float32)
        rho[test] = out
    np.save(ROOT/".cache"/"kdmc"/"rho_oof_sgmcfree.npy", rho)

    truth, receipt = proxy_truth(grid)
    E = kdmc.expected_credit(rho)
    allowed = grid.footprint & ~grid.catalogue
    n = int(round(DENSITY * allowed.sum()))
    dots = kdmc.allocate_separated(E, allowed, SEP, -np.inf, max_rounds=400)
    idx = np.flatnonzero(dots.ravel())
    order = idx[np.lexsort((idx, -E.ravel()[idx]))][:n]
    m = np.zeros(grid.shape, bool); m.ravel()[order] = True
    s = float(metric.dti_binary(m, truth, valid=grid.footprint, known=grid.catalogue)["dti"])

    full = json.loads((ROOT/"evidence"/"kdmc_experiment3_collar.json").read_text())
    base = next(a for a in full["arms"] if a["arm"] == "MDC88_collar0")["sgmc_proxy_dti"]
    h33 = next(a for a in full["arms"] if a["arm"] == "ANCHOR_h33_registry")["sgmc_proxy_dti"]
    rep = dict(
        experiment="kdmc-88-exp3b-sgmc-free-confound-control",
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        question=("How much of the Experiment 3 proxy margin is circular, i.e. produced by the "
                  "SGMC-derived feature column rather than by independent geophysics?"),
        dropped_columns=dropped, n_features_used=len(keep),
        configuration=dict(separation_px=SEP, density=DENSITY, n_dots=int(m.sum())),
        sgmc_free_proxy_dti=s, full_model_proxy_dti=base,
        circularity=base - s, registry_anchor_h33=h33,
        margin_vs_h33_sgmc_free=s - h33,
        verdict=("The margin survives with every SGMC column removed."
                 if s - h33 > 0.01 else "The margin does not survive; treat it as circular."),
        caveat="PROXY, not a score. Repository no-evidence floor is |delta| >= 0.01.")
    out = ROOT/"evidence"/"kdmc_experiment3b_sgmc_free.json"
    out.write_text(json.dumps(rep, indent=2) + "\n")
    log(json.dumps({k: rep[k] for k in ("sgmc_free_proxy_dti","full_model_proxy_dti",
                                        "circularity","registry_anchor_h33",
                                        "margin_vs_h33_sgmc_free","verdict")}, indent=2))
    log(f"wrote {out} ({time.time()-t0:.0f}s)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
