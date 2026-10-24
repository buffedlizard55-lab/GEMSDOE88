#!/usr/bin/env python3
"""Build LBCAL sufficient statistics for every LB-scored sibling raster.

Inputs (gitignored, restored by scripts/lbcal_fetch_receipt_rasters.py):
  data/lbcal/manifest.json + NNN__REPO__file.tif  (exact files behind user-reported LB scores)
  data/bridge/{sample_submission,existing_faults}.tif, data/external/*.tif
Output: data/lbcal/stats_<tag>.npz
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems88.lbcal import raster_stats  # noqa: E402

D = ROOT / "data"


def read1(fn, band=1):
    with rasterio.open(fn) as ds:
        return ds.read(band), ds


def load_pred(fn, omega):
    with rasterio.open(fn) as ds:
        a = ds.read(1).astype(np.float32)
        nod = ds.nodata
    if nod is not None and np.isfinite(nod):
        a[a == nod] = np.nan
    a = np.where(np.isfinite(a), a, 0).astype(np.float32)
    a = np.clip(a, 0, 1)
    a[~omega] = 0
    return a


def build_cells(omega, cat, tag):
    dcat = distance_transform_edt(~cat)
    b_dcat = np.digitize(dcat, [2.01, 3.01, 5, 10, 25, 50]).astype(np.int32)  # 0..6
    h195 = load_pred(D / "lbcal" / "018__19GEMSDOE__gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif", omega) > 0
    d195 = distance_transform_edt(~h195)
    b_r = np.digitize(d195, [0.5, 1.5, 3.01]).astype(np.int32)  # 0:on 1:<=1.5 2:<=3 3:>3
    with rasterio.open(D / "external" / "lidar_scarp_features_u8.tif") as ds:
        valid = ds.read(12) > 0
    with rasterio.open(D / "external" / "topo_10m_derived_100m_u8.tif") as ds:
        slope = ds.read(1).astype(np.float32)
    sv = slope[omega & (slope > 0)]
    qs = np.quantile(sv, [0.25, 0.5, 0.75])
    b_s = np.digitize(slope, qs).astype(np.int32)  # 0..3
    b_s[slope == 0] = 0
    dims = {"dcat": 7, "ridge195": 4, "lidar_valid": 2, "slope_q": 4}
    cell = ((b_dcat * 4 + b_r) * 2 + valid.astype(np.int32)) * 4 + b_s
    ncell = 7 * 4 * 2 * 4
    meta = {"dims": dims, "slope_quartiles": [float(x) for x in qs],
            "dcat_edges_px": [2.01, 3.01, 5, 10, 25, 50], "ridge_edges_px": [0.5, 1.5, 3.01],
            "ridge_source": "19GEMSDOE h19-5 (e27054cf) support, 121131 px"}
    return cell.astype(np.int32), ncell, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v1")
    args = ap.parse_args()
    ss, _ = read1(D / "bridge" / "sample_submission.tif")
    foot = np.isfinite(ss)
    ef, _ = read1(D / "bridge" / "existing_faults.tif")
    cat = ef == 1
    omega = foot & ~cat
    cell, ncell, meta = build_cells(omega, cat, args.tag)
    N = np.bincount(cell[omega], minlength=ncell).astype(np.float64)
    man = json.load(open(D / "lbcal" / "manifest.json"))
    prof = {r["name"]: r for r in json.load(open(D / "lbcal" / "profile.json"))}
    rows, Cs, Es, Ps, ns, seen = [], [], [], [], [], {}
    for m in man:
        if m.get("status") != "ok":
            continue
        pr = prof.get(m["name"], {})
        if not pr.get("grid_ok", False):
            print("skip grid mismatch", m["name"]);
            continue
        p = load_pred(D / "lbcal" / m["file"], omega)
        h = hashlib.sha256(np.packbits(p > 0).tobytes() + p[p > 0].tobytes()).hexdigest()[:16]
        C, E, P, n = raster_stats(p, omega, cell, ncell)
        rows.append({"idx": int(m["file"][:3]), "repo": m["repo"], "name": m["name"], "lb": m["lb"],
                     "file": m["file"], "sha256": m["sha256"], "content_hash": h, "dup_of": seen.get(h),
                     "n": n, "source_url": m.get("source_url")})
        seen.setdefault(h, int(m["file"][:3]))
        Cs.append(C); Es.append(E); Ps.append(P); ns.append(n)
        print(f"{m['file'][:3]} lb={m['lb']:.4f} n={n:9.0f} dup={rows[-1]['dup_of']}", flush=True)
    np.savez_compressed(D / "lbcal" / f"stats_{args.tag}.npz", C=np.array(Cs), E=np.array(Es), P=np.array(Ps),
                        n=np.array(ns), N=N, cell_meta=json.dumps(meta), rows=json.dumps(rows))
    np.save(D / "lbcal" / f"cell_{args.tag}.npy", cell.astype(np.int16))
    print("saved", len(rows), "rasters,", ncell, "cells")


if __name__ == "__main__":
    main()
