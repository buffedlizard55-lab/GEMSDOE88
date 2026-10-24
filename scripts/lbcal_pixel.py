#!/usr/bin/env python3
"""LBCAL-PX: pixel-level log-linear truth density fitted to user-reported LB receipts.

q(y) = exp(beta . phi(y)) on the scored domain (footprint minus catalogue).
phi = physical feature bands only (topography, LiDAR scarp, chi, geophysics,
catalogue distance bands, ridge-distance bands).  No coordinates.

Expected DTI of receipt raster i is evaluated on a fixed seeded random sample S
of the scored domain (sampling fraction s):  T_i ~ (1/s) sum_{y in S} q(y) c_i(y).

Stages:
  --stage prep   : build sample, features, sparse coverage of every receipt raster
  --stage fit    : fit beta (+ LOO / repo-blocked CV)
Outputs in data/lbcal/ (gitignored).  Evidence class of every number here:
MODEL-FIT to USER-REPORTED LB receipts.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, maximum_filter
from scipy.optimize import least_squares
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems88.lbcal import coverage_maps  # noqa: E402

D = ROOT / "data"
L = D / "lbcal"
H195 = "018__19GEMSDOE__gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif"
SFRAC = 0.12
SEED = 88


def grid_masks():
    with rasterio.open(D / "bridge" / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(D / "bridge" / "existing_faults.tif") as ds:
        cat = ds.read(1) == 1
    return foot, cat, foot & ~cat


def load_pred(fn, omega):
    with rasterio.open(fn) as ds:
        a = ds.read(1).astype(np.float32)
        nod = ds.nodata
    if nod is not None and np.isfinite(nod):
        a[a == nod] = np.nan
    a = np.clip(np.where(np.isfinite(a), a, 0), 0, 1).astype(np.float32)
    a[~omega] = 0
    return a


def feature_stack(omega, cat):
    """Return dict name -> full-grid float32 feature (physical only)."""
    F = {}
    dcat = distance_transform_edt(~cat)
    for lo, hi, nm in [(0.5, 2.01, "dcat_le2"), (2.01, 3.01, "dcat_2_3"), (3.01, 5, "dcat_3_5"), (5, 10, "dcat_5_10"),
                       (10, 25, "dcat_10_25")]:
        F[nm] = ((dcat > lo) & (dcat <= hi)).astype(np.float32)          # ref level: > 25 px
    h = load_pred(L / H195, omega) > 0
    d = distance_transform_edt(~h)
    F["ridge_on"] = (d == 0).astype(np.float32)
    F["ridge_le1p5"] = ((d > 0) & (d <= 1.5)).astype(np.float32)
    F["ridge_le3"] = ((d > 1.5) & (d <= 3.01)).astype(np.float32)        # ref level: > 3 px
    with rasterio.open(D / "external" / "lidar_scarp_features_u8.tif") as ds:
        valid = ds.read(12) > 0
        F["lidar_valid"] = valid.astype(np.float32)
        for b, nm in [(1, "lid_ex_max"), (3, "lid_step_max"), (4, "lid_lapneg_max"), (9, "lid_relief"), (10, "lid_coh100")]:
            a = ds.read(b).astype(np.float32)
            a[~valid] = np.nan
            F[nm] = a
    with rasterio.open(D / "external" / "topo_10m_derived_100m_u8.tif") as ds:
        for b, nm in [(1, "topo_slope_p90"), (5, "topo_relief_local"), (6, "topo_curv_prof"), (7, "topo_aspect_coh"),
                      (8, "topo_hs_lineament")]:
            a = ds.read(b).astype(np.float32)
            a[a == 0] = np.nan
            F[nm] = a
    with rasterio.open(D / "external" / "dem10_chi_100m_i16.tif") as ds:
        for b, nm in [(3, "chi_ksn_max")]:
            a = ds.read(b).astype(np.float32)
            a[a == -32768] = np.nan
            F[nm] = a
    with rasterio.open(D / "training_features.tif") as ds:
        nod = ds.nodata
        for b, nm in [(18, "geo_grav_hg"), (3, "geo_tmi_hg"), (19, "geo_elev_slope")]:
            a = ds.read(b).astype(np.float32)
            a[(a == nod) | ~np.isfinite(a) | (np.abs(a) > 1e30)] = np.nan
            F[nm] = a
    # local-maximum localisers: is this pixel the 3x3 max of slope / lidar step (sharpens within-band position)
    s = np.nan_to_num(F["topo_slope_p90"], nan=-1)
    F["loc_slope_max3"] = ((s >= maximum_filter(s, 3)) & (s > 0)).astype(np.float32)
    st = np.nan_to_num(F["lid_step_max"], nan=-1)
    F["loc_step_max3"] = ((st >= maximum_filter(st, 3)) & (st > 0)).astype(np.float32)
    return F


def prep():
    t0 = time.time()
    foot, cat, omega = grid_masks()
    rng = np.random.default_rng(SEED)
    oy, ox = np.nonzero(omega)
    take = rng.random(oy.size) < SFRAC
    sy, sx = oy[take], ox[take]
    F = feature_stack(omega, cat)
    names = list(F)
    Phi = np.zeros((sy.size, len(names)), np.float32)
    stats = {}
    for j, nm in enumerate(names):
        v = F[nm][sy, sx]
        if nm.startswith(("dcat_", "ridge_", "lidar_valid", "loc_")):
            Phi[:, j] = np.nan_to_num(v, nan=0.0)
            stats[nm] = {"type": "indicator"}
        else:
            vv = v[np.isfinite(v)]
            lo, hi = np.quantile(vv, [0.005, 0.995])
            v = np.clip(v, lo, hi)
            mu, sd = float(np.nanmean(v)), float(np.nanstd(v) + 1e-9)
            Phi[:, j] = np.nan_to_num((v - mu) / sd, nan=0.0)
            stats[nm] = {"type": "zscore", "clip": [float(lo), float(hi)], "mu": mu, "sd": sd}
    del F
    man = json.load(open(L / "manifest.json"))
    prof = {r["name"]: r for r in json.load(open(L / "profile.json"))}
    sidx = np.full(omega.shape, -1, np.int64)
    sidx[sy, sx] = np.arange(sy.size)
    rows, cov_i, cov_v, ecov_v, ptr = [], [], [], [], [0]
    seen = {}
    for m in man:
        if m.get("status") != "ok" or not prof.get(m["name"], {}).get("grid_ok", False):
            continue
        p = load_pred(L / m["file"], omega)
        key = (int((p > 0).sum()), float(p.sum()), int(np.flatnonzero(p.ravel())[:50].sum()) if (p > 0).any() else 0)
        c, e = coverage_maps(p)
        cs, es = c[sy, sx], e[sy, sx]
        nz = np.flatnonzero(cs > 0)
        cov_i.append(nz.astype(np.int32)); cov_v.append(cs[nz].astype(np.float32)); ecov_v.append(es[nz].astype(np.float32))
        ptr.append(ptr[-1] + nz.size)
        rows.append({"idx": int(m["file"][:3]), "repo": m["repo"], "name": m["name"], "lb": m["lb"], "n": float(p.sum()),
                     "nan_inside_footprint": int(prof[m["name"]]["nan_in_foot"]), "dup_of": seen.get(key),
                     "sha256": m["sha256"], "source_url": m.get("source_url")})
        seen.setdefault(key, int(m["file"][:3]))
    np.savez_compressed(L / "px_prep.npz", Phi=Phi, names=np.array(names), sy=sy, sx=sx, cov_i=np.concatenate(cov_i),
                        cov_v=np.concatenate(cov_v), ecov_v=np.concatenate(ecov_v), ptr=np.array(ptr),
                        rows=json.dumps(rows), fstats=json.dumps(stats), sfrac=SFRAC)
    print(f"prep done: {sy.size} sample px, {len(names)} features, {len(rows)} rasters, {time.time()-t0:.0f}s")


class Model:
    def __init__(self, z, keep, kappa=2.6, lam=3e-3, feats=None, drop=()):
        self.names = [str(x) for x in z["names"]]
        Phi = z["Phi"]
        if (L / "px_extra.npz").exists():
            zx = np.load(L / "px_extra.npz")
            self.names += [str(x) for x in zx["names"]]
            Phi = np.column_stack([Phi, zx["Phi"]])
        self.fsel = [j for j, n in enumerate(self.names) if (feats is None or n in feats) and n not in drop]
        self.Phi = np.column_stack([np.ones(Phi.shape[0], np.float32), Phi[:, self.fsel]]).astype(np.float64)
        del Phi
        self.labels = ["intercept"] + [self.names[j] for j in self.fsel]
        rows = json.loads(str(z["rows"]))
        ptr = z["ptr"]
        cov_i, cov_v, ecov_v = z["cov_i"], z["cov_v"], z["ecov_v"]   # load each array once
        self.rows = [rows[i] for i in keep]
        from scipy.sparse import csr_matrix
        ns = self.Phi.shape[0]
        ind = np.concatenate([cov_i[ptr[i]:ptr[i + 1]] for i in keep])
        rp = np.concatenate([[0], np.cumsum([ptr[i + 1] - ptr[i] for i in keep])])
        self.A = csr_matrix((np.concatenate([cov_v[ptr[i]:ptr[i + 1]] for i in keep]).astype(np.float64), ind, rp), shape=(len(keep), ns))
        self.E = csr_matrix((np.concatenate([ecov_v[ptr[i]:ptr[i + 1]] for i in keep]).astype(np.float64), ind, rp), shape=(len(keep), ns))
        del cov_i, cov_v, ecov_v, ind
        self.n = np.array([r["n"] for r in self.rows])
        self.lb = np.array([r["lb"] for r in self.rows])
        self.s = float(z["sfrac"])
        self.kappa, self.lam = kappa, lam

    def predict(self, beta, idx=None):
        q = np.exp(np.clip(self.Phi @ beta, -30, 3))
        G = q.sum() / self.s
        A = self.A if idx is None else self.A[idx]
        E = self.E if idx is None else self.E[idx]
        n = self.n if idx is None else self.n[idx]
        T = (A @ q) / self.s
        M = np.minimum((E @ q) / self.s / self.kappa, n)
        F = n - M
        return T / (0.2 * T + 0.2 * F + 0.8 * G), T, F, G

    def fit(self, mask=None, beta0=None):
        mask = np.ones(len(self.rows), bool) if mask is None else mask
        idx = np.flatnonzero(mask)
        p = self.Phi.shape[1]
        if beta0 is None:
            beta0 = np.zeros(p); beta0[0] = np.log(0.003)
        A, E, n, lb = self.A[idx], self.E[idx], self.n[idx], self.lb[idx]   # slice once
        Phi, s, kap = self.Phi, self.s, self.kappa

        def fwd(b):
            q = np.exp(np.clip(Phi @ b, -30, 3))
            G = q.sum() / s
            T = (A @ q) / s
            M = np.minimum((E @ q) / s / kap, n)
            den = 0.2 * T + 0.2 * (n - M) + 0.8 * G
            return q, T, M, G, den

        def res(b):
            q, T, M, G, den = fwd(b)
            return np.concatenate([T / den - lb, np.sqrt(self.lam) * b[1:]])

        def jac(b):
            q, T, M, G, den = fwd(b)
            Qp = Phi * q[:, None]                      # d q / d beta
            dT = (A @ Qp) / s
            capped = ((E @ q) / s / kap) >= n
            dM = np.where(capped[:, None], 0.0, (E @ Qp) / s / kap)
            dG = Qp.sum(0) / s
            dden = 0.2 * dT - 0.2 * dM + 0.8 * dG[None, :]
            J = (dT * den[:, None] - T[:, None] * dden) / (den[:, None] ** 2)
            R = np.zeros((p - 1, p)); R[np.arange(p - 1), np.arange(1, p)] = np.sqrt(self.lam)
            return np.vstack([J, R])

        return least_squares(res, beta0, jac=jac, method="trf", max_nfev=200).x


def fit_stage(args):
    z = np.load(L / "px_prep.npz", allow_pickle=False)
    rows = json.loads(str(z["rows"]))
    keep = [i for i, r in enumerate(rows) if r["dup_of"] is None and r["nan_inside_footprint"] == 0]
    feats = None if not args.feats else args.feats.split(",")
    drop = tuple(x for x in args.drop.split(",") if x)
    M = Model(z, keep, kappa=args.kappa, lam=args.lam, feats=feats, drop=drop)
    t0 = time.time()
    beta = M.fit()
    pred, T, F, G = M.predict(beta)
    out = {"evidence_class": "MODEL-FIT to USER-REPORTED LB receipts (not HOLDOUT-DTI, not ORGANIZER-CONFIRMED)",
           "lam": args.lam, "kappa": args.kappa, "drop": list(drop), "labels": M.labels, "beta": beta.tolist(), "G_px": G,
           "n_receipts": len(M.rows), "fit_rmse": float(np.sqrt(np.mean((pred - M.lb) ** 2))),
           "fit_spearman": float(spearmanr(pred, M.lb)[0]),
           "excluded_nan_inside_footprint": [r["name"] for r in rows if r["nan_inside_footprint"] > 0]}
    print(f"fit {time.time()-t0:.0f}s |G|={G:.0f} RMSE={out['fit_rmse']:.4f} rho={out['fit_spearman']:.3f}", flush=True)
    if args.cv:
        repos = sorted(set(r["repo"] for r in M.rows))
        rng = np.random.default_rng(306)
        fold_of = {rp: k for rp, k in zip(rng.permutation(repos), np.arange(len(repos)) % 8)}
        blk = np.zeros(len(M.rows))
        for k in range(8):
            m = np.array([fold_of[r["repo"]] != k for r in M.rows])
            b = M.fit(m, beta0=beta)
            blk[~m] = M.predict(b, np.flatnonzero(~m))[0]
        out["repo_blocked_rmse"] = float(np.sqrt(np.mean((blk - M.lb) ** 2)))
        out["repo_blocked_spearman"] = float(spearmanr(blk, M.lb)[0])
        out["per_receipt"] = [{"idx": r["idx"], "name": r["name"], "repo": r["repo"], "lb": float(a), "fit": float(b_), "blocked": float(c),
                               "T": float(t), "F": float(f)} for r, a, b_, c, t, f in zip(M.rows, M.lb, pred, blk, T, F)]
        print(f"repo-blocked CV RMSE={out['repo_blocked_rmse']:.4f} rho={out['repo_blocked_spearman']:.3f} ({time.time()-t0:.0f}s)")
    for l, b in zip(M.labels, beta):
        print(f"  {l:20s} {b:+.3f}")
    json.dump(out, open(L / f"px_fit_{args.tag}.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["prep", "fit"], required=True)
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--lam", type=float, default=3e-3)
    ap.add_argument("--kappa", type=float, default=2.6)
    ap.add_argument("--feats", default="")
    ap.add_argument("--drop", default="")
    ap.add_argument("--cv", action="store_true")
    a = ap.parse_args()
    prep() if a.stage == "prep" else fit_stage(a)
