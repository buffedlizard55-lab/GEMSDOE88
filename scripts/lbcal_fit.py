#!/usr/bin/env python3
"""Fit the LBCAL log-additive truth-density model to user-reported LB receipts.

Outputs data/lbcal/fit_<tag>.json (parameters, per-cell q, LOO/blocked CV).
Every number produced here is a MODEL FIT to USER-REPORTED leaderboard scores;
none of it is a HOLDOUT-DTI or an ORGANIZER-CONFIRMED score.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems88.lbcal import predict_dti  # noqa: E402

D = ROOT / "data" / "lbcal"


def design(dims):
    names = list(dims)
    sizes = [dims[k] for k in names]
    levels = np.array(list(itertools.product(*[range(s) for s in sizes])))  # ncell x ndim, C-order matches builder
    cols, labels = [], []
    for j, (nm, s) in enumerate(zip(names, sizes)):
        for lv in range(1, s):
            cols.append((levels[:, j] == lv).astype(float))
            labels.append(f"{nm}={lv}")
    X = np.column_stack([np.ones(len(levels))] + cols)
    return X, ["intercept"] + labels, levels


def fit(X, C, E, n, N, lb, w, lam, kappa, theta0=None):
    p = X.shape[1]
    if theta0 is None:
        theta0 = np.zeros(p); theta0[0] = np.log(0.003)

    def res(th):
        q = np.exp(np.clip(X @ th, -30, 5))
        d, *_ = predict_dti(q, C, E, n, N, kappa)
        r = (d - lb) * w
        return np.concatenate([r, np.sqrt(lam) * th[1:]])

    sol = least_squares(res, theta0, method="trf", max_nfev=4000, x_scale=1.0)
    return sol.x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--lam", type=float, default=1e-4)
    ap.add_argument("--kappa", type=float, default=2.6)
    ap.add_argument("--drop-dims", default="")
    args = ap.parse_args()
    z = np.load(D / f"stats_{args.tag}.npz", allow_pickle=False)
    rows = json.loads(str(z["rows"]))
    meta = json.loads(str(z["cell_meta"]))
    C, E, n, N = z["C"], z["E"], z["n"], z["N"]
    keep = [i for i, r in enumerate(rows) if r["dup_of"] is None]
    C, E, n = C[keep], E[keep], n[keep]
    rows = [rows[i] for i in keep]
    lb = np.array([r["lb"] for r in rows])
    w = np.ones_like(lb)
    X, labels, levels = design(meta["dims"])
    drop = [d for d in args.drop_dims.split(",") if d]
    if drop:
        sel = [j for j, l in enumerate(labels) if l.split("=")[0] not in drop]
        X, labels = X[:, sel], [labels[j] for j in sel]
    th = fit(X, C, E, n, N, lb, w, args.lam, args.kappa)
    q = np.exp(X @ th)
    pred, T, F, G = predict_dti(q, C, E, n, N, args.kappa)
    rmse = float(np.sqrt(np.mean((pred - lb) ** 2)))
    # leave-one-out
    loo = np.zeros_like(lb)
    for i in range(len(lb)):
        m = np.ones(len(lb), bool); m[i] = False
        thi = fit(X, C[m], E[m], n[m], N, lb[m], w[m], args.lam, args.kappa, theta0=th)
        qi = np.exp(X @ thi)
        loo[i] = predict_dti(qi, C[i:i + 1], E[i:i + 1], n[i:i + 1], N, args.kappa)[0][0]
    # repo-blocked CV (all receipts from one sibling repo held out together)
    repos = sorted(set(r["repo"] for r in rows))
    blk = np.zeros_like(lb)
    for rp in repos:
        m = np.array([r["repo"] != rp for r in rows])
        thi = fit(X, C[m], E[m], n[m], N, lb[m], w[m], args.lam, args.kappa, theta0=th)
        qi = np.exp(X @ thi)
        blk[~m] = predict_dti(qi, C[~m], E[~m], n[~m], N, args.kappa)[0]
    out = {
        "evidence_class": "MODEL-FIT to USER-REPORTED LB receipts (not HOLDOUT-DTI, not ORGANIZER-CONFIRMED)",
        "tag": args.tag, "lam": args.lam, "kappa": args.kappa, "drop_dims": drop,
        "n_receipts_unique": len(lb), "labels": labels, "theta": th.tolist(),
        "G_total_px_whole_region_equiv": float(G),
        "fit_rmse": rmse, "fit_spearman": float(spearmanr(pred, lb)[0]),
        "loo_rmse": float(np.sqrt(np.mean((loo - lb) ** 2))), "loo_spearman": float(spearmanr(loo, lb)[0]),
        "repo_blocked_rmse": float(np.sqrt(np.mean((blk - lb) ** 2))), "repo_blocked_spearman": float(spearmanr(blk, lb)[0]),
        "q_cell": q.tolist(), "dims": meta["dims"], "cell_meta": meta,
        "per_receipt": [{"idx": r["idx"], "name": r["name"], "lb": r["lb"], "fit": float(a), "loo": float(b), "blocked": float(c),
                         "T": float(t), "F": float(f)} for r, a, b, c, t, f in zip(rows, pred, loo, blk, T, F)],
    }
    json.dump(out, open(D / f"fit_{args.tag}{'_drop-' + '-'.join(drop) if drop else ''}_lam{args.lam:g}_k{args.kappa:g}.json", "w"), indent=1)
    print(f"unique receipts={len(lb)} params={X.shape[1]} |G|~{G:.0f}px  fit RMSE={rmse:.4f} rho={out['fit_spearman']:.3f}  "
          f"LOO RMSE={out['loo_rmse']:.4f} rho={out['loo_spearman']:.3f}  repo-blocked RMSE={out['repo_blocked_rmse']:.4f} rho={out['repo_blocked_spearman']:.3f}")
    for l, t in zip(labels, th):
        print(f"  {l:18s} {t:+.3f}  (x{np.exp(t):.3f})")
    worst = sorted(out["per_receipt"], key=lambda r: -abs(r["loo"] - r["lb"]))[:8]
    for r in worst:
        print(f"  worst LOO: {r['idx']:3d} lb={r['lb']:.4f} fit={r['fit']:.4f} loo={r['loo']:.4f} {r['name'][:50]}")


if __name__ == "__main__":
    main()
