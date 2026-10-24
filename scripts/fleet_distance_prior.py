#!/usr/bin/env python3
"""Diagnostic D3 -- 1-D distance-to-catalogue value profile from the owner-reported fleet.

Model (5 parameters, n=20 rasters): reported_public_dti ~ sum_b a_b * share_b, a_b >= 0, where
share_b is the fraction of a raster's dots whose distance to the mapped catalogue falls in
distance bin b.  Leave-one-out predictions give an honest error bar.  This is a PROJECTION
instrument, never a score.  It uses only a 1-D structural variable (distance to *known* faults),
not per-pixel public feedback, so it cannot memorise where the public-chunk faults are.
Output: evidence/fleet_distance_prior_20261024.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import nnls
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]
from gems57 import grid as grid_mod  # noqa: E402
from calibrate_proxies import FLEET, dot_mask  # noqa: E402

EDGES = [0, 2, 5, 10, 25, 1e9]
LABELS = ["<=2px", "2-5px", "5-10px", "10-25px", ">25px"]


def shares(d, edges=EDGES):
    h = np.histogram(d, bins=edges)[0].astype(float)
    return h / h.sum()


def main():
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    names, S, y, n = [], [], [], []
    for label, path, score in FLEET:
        m, _ = dot_mask(path, g.footprint)
        S.append(shares(d_cat[m]))
        y.append(score)
        names.append(label)
        n.append(int(m.sum()))
    S, y = np.array(S), np.array(y)
    coef, rn = nnls(S, y)
    pred = S @ coef
    loo = []
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        c, _ = nnls(S[keep], y[keep])
        loo.append(float(S[i] @ c))
    loo = np.array(loo)
    out = dict(evidence_class="PROJECTION calibrated on OWNER-REPORTED scores (n=20); not a score",
               bins=LABELS, coef_score_per_unit_share=dict(zip(LABELS, coef.tolist())),
               in_sample_rmse=float(np.sqrt(np.mean((pred - y) ** 2))),
               loo_rmse=float(np.sqrt(np.mean((loo - y) ** 2))),
               loo_spearman=float(spearmanr(loo, y)[0]),
               rows=[dict(label=a, dots=b, reported=float(c), shares=dict(zip(LABELS, s.tolist())),
                          fitted=float(p), loo=float(l)) for a, b, c, s, p, l in zip(names, n, y, S, pred, loo)])
    # single-variable alternatives with LOO
    for nm, col in (("share_gt25", S[:, 4]), ("share_gt10", S[:, 3] + S[:, 4])):
        A = np.column_stack([col, np.ones_like(col)])
        res = []
        for i in range(len(y)):
            keep = np.arange(len(y)) != i
            c, *_ = np.linalg.lstsq(A[keep], y[keep], rcond=None)
            res.append(float(A[i] @ c))
        res = np.array(res)
        c_all, *_ = np.linalg.lstsq(A, y, rcond=None)
        out[f"linear_{nm}"] = dict(slope=float(c_all[0]), intercept=float(c_all[1]),
                                   loo_rmse=float(np.sqrt(np.mean((res - y) ** 2))), loo_spearman=float(spearmanr(res, y)[0]))
    (ROOT / "evidence" / "fleet_distance_prior_20261024.json").write_text(json.dumps(out, indent=1))
    print("coef:", {k: round(v, 3) for k, v in out["coef_score_per_unit_share"].items()})
    print("rmse in-sample %.4f  LOO %.4f  LOO-rho %.3f" % (out["in_sample_rmse"], out["loo_rmse"], out["loo_spearman"]))
    print("linear gt25:", out["linear_share_gt25"], "\nlinear gt10:", out["linear_share_gt10"])
    for r in out["rows"]:
        print(f"{r['label']:32s} rep={r['reported']:.4f} fit={r['fitted']:.4f} loo={r['loo']:.4f}")


if __name__ == "__main__":
    main()
