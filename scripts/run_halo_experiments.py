#!/usr/bin/env python3
"""Pre-registered HALO-88 experiments E1-E3 (hide-and-recover, buffered whole components).

E1  FBMT  far-basin-matched training                       vs  BASE (all-positive training)
E2  FBMT + CCR  catalogue-completeness residual (gamma=0.5 pre-registered; 0.25/1.0 sensitivity only)
E3  FBMT + CCR + RCP  ridge-continuity prior

Every number is HOLDOUT-DTI (evaluator ``gems57-pooled-hide-v2``).  The PRIMARY endpoint is the
far subset (withheld positives > 10 px from every visible catalogue pixel) because the real test
set is faults *not already captured* by USGS/INGENIOUS; the overall number is reported too.
Uses the vendored allocator/evaluator unmodified.  Spends 0 DrivenData slots.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import emit, evaluate_holdout, grid as grid_mod, holdout  # noqa: E402
from gems88 import halo, physics  # noqa: E402

BUFFER_PX, BOUNDARY_PX, BLOCK = 3, 12, 200
FAR_PX = 10
ARMS = ("base", "fbmt", "fbmt_ccr", "fbmt_ccr_rcp", "fbmt_ccr025", "fbmt_ccr100")


def canary(X, g, hidden, names, seed=88):
    """Single-feature symmetric ROC AUC: withheld positives vs 8x off-catalogue negatives."""
    fp = g.footprint
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    ys, xs = np.nonzero(fp)
    pos = np.flatnonzero(hidden[ys, xs])
    neg_pool = np.flatnonzero((~g.catalogue & (d_cat > 3))[ys, xs])
    rng = np.random.default_rng(seed)
    neg = np.sort(rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False))
    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(len(pos), int), np.zeros(len(neg), int)])
    order = np.argsort(idx)
    Xs = np.asarray(X[idx[order]], np.float32)
    y = y[order]
    rows = []
    for j, nm in enumerate(names):
        v = Xs[:, j].astype(np.float64)
        ok = np.isfinite(v)
        if ok.sum() < 100 or len(np.unique(y[ok])) < 2:
            rows.append(dict(feature=nm, symmetric_auc=0.5, note="degenerate"))
            continue
        v = np.where(ok, v, np.nanmedian(v[ok]))
        a = float(roc_auc_score(y, v))
        rows.append(dict(feature=nm, roc_auc=a, symmetric_auc=max(a, 1 - a), threshold=0.90, **{"pass": bool(max(a, 1 - a) <= 0.90)}))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[20, 21])
    ap.add_argument("--halo", type=float, default=3.0)
    ap.add_argument("--out", default="evidence/halo_experiments_20261024.json")
    args = ap.parse_args()
    t0 = time.monotonic()
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    N = int(fp.sum())
    names = list(physics.ALL_PHYS_FEATURES)
    X = np.memmap(ROOT / ".cache/gems88/x_phys_44ch.dat", dtype="float32", mode="r", shape=(N, len(names)))
    ckdir = ROOT / ".cache/halo"
    ckdir.mkdir(parents=True, exist_ok=True)

    terms = {s: {a: {"all": None, "far": None} for a in ARMS} for s in args.seeds}
    rows = []
    canary_doc = None
    for seed in args.seeds:
        folds, quad = holdout.buffered_component_draw(g, seed=seed, buffer_px=BUFFER_PX, boundary_px=BOUNDARY_PX)
        hidden = folds[0]["hidden_all"]
        visible = folds[0]["visible"]
        d_vis = ndi.distance_transform_edt(~visible)
        far_mask = d_vis > FAR_PX
        if canary_doc is None:
            print(f"[canary] seed {seed}: {len(names)} features ...", flush=True)
            crows = canary(X, g, hidden, names)
            mx = max(r["symmetric_auc"] for r in crows)
            canary_doc = dict(method="single-feature symmetric ROC AUC; withheld whole-component positives vs 8x off-catalogue negatives (d_cat>3 px)",
                              seed=seed, features_tested=len(crows), max_symmetric_auc=mx, threshold=0.90, passed=bool(mx <= 0.90),
                              features=crows)
            print(f"[canary] max symmetric AUC = {mx:.4f} ({'PASS' if mx <= 0.90 else 'FAIL'})", flush=True)
            if mx > 0.90:
                raise SystemExit("STOP: leakage canary > 0.90")
        for fold in folds:
            q = fold["fold"]
            ck = ckdir / f"halo_s{seed}_q{q}.npz"
            if ck.is_file():
                z = np.load(ck, allow_pickle=True)
                for a in ARMS:
                    for k in ("all", "far"):
                        bt = z[f"{a}_{k}"]
                        terms[seed][a][k] = bt if terms[seed][a][k] is None else terms[seed][a][k] + bt
                rows.append(json.loads(str(z["row"])))
                print(f"  [ckpt] seed {seed} {fold['name']}", flush=True)
                continue
            region = fold["region"]
            train_truth_px = sum(int(o["truth"].sum()) for o in folds if o["fold"] != q)
            row = dict(seed=seed, fold=fold["name"], withheld_positive_pixels=int(fold["truth"].sum()),
                       far_withheld_positive_pixels=int((fold["truth"] & far_mask).sum()))
            surf = {}
            for mode in ("base", "fbmt"):
                tm = time.monotonic()
                clf, meta = halo.fit_fold_models(X, g, visible, quad, q, train_truth_px, seed=88_000 + seed * 10 + q, mode=mode)
                p, m, allowed, k_est = halo.predict_calibrated(clf, X, g, visible, region, meta["hid_ratio"], args.halo)
                surf[mode] = (p, m, allowed, k_est)
                row[f"{mode}_meta"] = dict(**meta, k_est=k_est, seconds=round(time.monotonic() - tm, 1))
                print(f"  seed {seed} {fold['name']} {mode}: pos={meta['n_pos']} dom={meta['n_domain']} k_est={k_est:.0f} {time.monotonic()-tm:.0f}s", flush=True)
                del clf
            p0, m0, al, k = surf["fbmt"]
            arms = {"base": surf["base"], "fbmt": (p0, m0, al, k)}
            p1, m1, _cinfo = halo.ccr_boost(p0, m0, visible, al, k, gamma=0.5)
            arms["fbmt_ccr"] = (p1, m1, al, k)
            for tag, gam in (("fbmt_ccr025", 0.25), ("fbmt_ccr100", 1.0)):
                pp, mm, _ = halo.ccr_boost(p0, m0, visible, al, k, gamma=gam)
                arms[tag] = (pp, mm, al, k)
            w, winfo = halo.continuity_weight(p1, al)
            p3, m3 = halo.apply_weight(p1, m1, w, al, k)
            arms["fbmt_ccr_rcp"] = (p3, m3, al, k)
            row["rcp"] = winfo
            save = {}
            for a in ARMS:
                pa, ma, ala, ka = arms[a]
                alloc = emit.dinkelbach_allocate(pa, ma, ala, budget=None, k_truth=ka, min_spacing_px=2.05, dinkelbach_iters=6)
                em = alloc.emitted.astype(np.float32)
                r_all, bt_all = evaluate_holdout.evaluate(em, fold, fp, block_side=BLOCK, global_shape=fp.shape)
                fold_far = dict(fold, truth=fold["truth"] & far_mask)
                r_far, bt_far = evaluate_holdout.evaluate(em, fold_far, fp, block_side=BLOCK, global_shape=fp.shape)
                dd = d_vis[em > 0]
                row[a] = dict(dti=r_all["dti"], tpw=r_all["tpw"], fpw=r_all["fpw"], emitted=int(r_all["n_emitted"]),
                              far_dti=r_far["dti"], far_tpw=r_far["tpw"], far_fpw=r_far["fpw"],
                              share_dots_dvis_le10=float((dd <= 10).mean()) if dd.size else None,
                              share_dots_dvis_gt25=float((dd > 25).mean()) if dd.size else None,
                              surrogate_dti=float(alloc.surrogate_dti))
                save[f"{a}_all"] = bt_all
                save[f"{a}_far"] = bt_far
                terms[seed][a]["all"] = bt_all if terms[seed][a]["all"] is None else terms[seed][a]["all"] + bt_all
                terms[seed][a]["far"] = bt_far if terms[seed][a]["far"] is None else terms[seed][a]["far"] + bt_far
                print(f"    {a:13s} dti={r_all['dti']:.4f} far={r_far['dti']:.4f} n={int(r_all['n_emitted'])} "
                      f"d<=10={row[a]['share_dots_dvis_le10']}", flush=True)
            np.savez_compressed(ck, row=json.dumps(row), **save)
            rows.append(row)
            print(f"  seed {seed} {fold['name']} done at {time.monotonic()-t0:.0f}s", flush=True)

    pooled = {}
    for kind in ("all", "far"):
        arrs = {a: sum(terms[s][a][kind] for s in args.seeds) for a in ARMS}
        for cand in ("fbmt_ccr_rcp", "fbmt", "fbmt_ccr"):
            pooled[f"{kind}__candidate_{cand}"] = evaluate_holdout.pooled_summary(arrs, draws=1000, seed=520810, candidate=cand)
    out = dict(evidence_class="HOLDOUT-DTI", evaluator_version=evaluate_holdout.VERSION, seeds=args.seeds,
               halo_px=args.halo, far_px=FAR_PX, arms=list(ARMS), per_fold=rows, pooled=pooled, canary=canary_doc,
               seconds=round(time.monotonic() - t0, 1))
    (ROOT / args.out).write_text(json.dumps(out, indent=1, default=float))
    for kind in ("all", "far"):
        s = pooled[f"{kind}__candidate_fbmt"]["scores"]
        print(kind, {a: (round(s[a]['dti'], 5), [round(x, 5) for x in s[a]['ci95']], s[a]['withheld_positive_pixels']) for a in ARMS})


if __name__ == "__main__":
    main()
