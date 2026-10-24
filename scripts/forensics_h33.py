#!/usr/bin/env python3
"""Measured forensics of the user-reported best raster (GEMSDOE32 / H33 / R0).

Everything printed or written here is computed from SHA-pinned rasters on disk;
the public DrivenData scores attached to the lineage are USER-REPORTED CLAIMS
(no organizer receipt exists in this repository) and are labelled as such.

Output: evidence/h33_forensics_20261024.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import grid as grid_mod  # noqa: E402

REG = ROOT / "data" / "registry"
FEAT = ROOT / "data" / "training_features.tif"

# user-reported public scores (CLAIMS) for the pixel-subset lineage
LINEAGE = [
    ("H19-5 (19GEMSDOE)", "gems19_h19_5.tif", 0.1922),
    ("D2.8 (GEMSDOE25)", "gems25_d28.tif", 0.2600),
    ("SOLO-D2.8 B=1 (GEMSDOE28)", "gems28_h27_4.tif", 0.2708),
    ("H33 b2 (GEMSDOE32) = R0", "h33_education.tif", 0.2778),
]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dots_of(path, fp):
    with rasterio.open(path) as ds:
        a = ds.read(1)
    pos = np.isfinite(a) & (a > 0) & fp
    vals = np.unique(a[np.isfinite(a)])
    return pos, vals


def main():
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    d_cat = ndi.distance_transform_edt(~cat)  # px to nearest catalogue pixel
    out = {"evidence_class": "REGISTRY-MEASUREMENT (on-disk rasters); scores are USER-REPORTED CLAIMS",
           "footprint_px": int(fp.sum()), "catalogue_px": int(cat.sum())}

    rows, masks = [], {}
    for name, f, score in LINEAGE:
        p = REG / f
        m, vals = dots_of(p, fp)
        masks[name] = m
        dc = d_cat[m]
        rows.append(dict(
            name=name, file=f, sha256=sha(p), user_reported_public_dti=score,
            n_dots=int(m.sum()), n_unique_values=int(len(vals)),
            values_sample=[float(v) for v in vals[:4]],
            d_cat_px=dict(min=float(dc.min()), p05=float(np.quantile(dc, .05)),
                          p25=float(np.quantile(dc, .25)), median=float(np.median(dc)),
                          p75=float(np.quantile(dc, .75)), p95=float(np.quantile(dc, .95))),
            frac_d_cat_le_1=float((dc <= 1).mean()), frac_d_cat_le_2=float((dc <= 2.0).mean()),
            frac_d_cat_le_3=float((dc <= 3.0).mean()), frac_d_cat_le_10=float((dc <= 10).mean()),
            frac_d_cat_gt_30=float((dc > 30).mean()),
        ))
    out["lineage"] = rows

    # exact pixel-subset chain
    names = [r["name"] for r in rows]
    chain = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, B = masks[a], masks[b]
            chain[f"{b} ⊂? {a}"] = dict(
                inter=int((A & B).sum()), n_b=int(B.sum()), frac_b_inside_a=float((A & B).sum() / B.sum()),
                removed_from_a=int((A & ~B).sum()), added_vs_a=int((B & ~A).sum()))
    out["subset_chain"] = chain

    # dots removed going D2.8 -> H33: where were they relative to the catalogue?
    d28 = masks["D2.8 (GEMSDOE25)"]
    h33 = masks["H33 b2 (GEMSDOE32) = R0"]
    removed = d28 & ~h33
    dr = d_cat[removed]
    out["removed_D28_to_H33"] = dict(
        n=int(removed.sum()), d_cat_px=dict(min=float(dr.min()), median=float(np.median(dr)), max=float(dr.max())),
        frac_le_2=float((dr <= 2.0).mean()))

    # nearest-neighbour spacing of H33 dots
    yx = np.argwhere(h33)
    tree = cKDTree(yx)
    dd, _ = tree.query(yx, k=2)
    nn = dd[:, 1]
    out["h33_spacing_px"] = dict(
        nn_min=float(nn.min()), nn_p05=float(np.quantile(nn, .05)), nn_median=float(np.median(nn)),
        nn_p95=float(np.quantile(nn, .95)), frac_nn_lt_3=float((nn < 3).mean()),
        frac_nn_between_2_and_4=float(((nn >= 2) & (nn <= 4)).mean()),
        mean_neighbours_within_3px=float((np.array([len(x) - 1 for x in tree.query_ball_point(yx, 3.0)])).mean()))

    # band enrichment at H33 dots (ranks within footprint)
    with rasterio.open(FEAT) as ds:
        names_b = [ds.tags(i).get("band_name", f"band{i}") for i in range(1, ds.count + 1)]
        en = {}
        rng = np.random.default_rng(1)
        fp_idx = np.flatnonzero(fp.ravel())
        samp = rng.choice(fp_idx, 400_000, replace=False)
        dot_idx = np.flatnonzero(h33.ravel())
        for i, nm in enumerate(names_b, start=1):
            a = ds.read(i).astype("float64").ravel()
            ok_s = np.isfinite(a[samp])
            base = a[samp][ok_s]
            dv = a[dot_idx]
            dv = dv[np.isfinite(dv)]
            if base.size < 100 or dv.size < 100:
                continue
            # percentile rank of dot values within the footprint distribution
            q = np.searchsorted(np.sort(base), dv) / base.size
            # AUC dots vs footprint, symmetric
            from scipy.stats import rankdata
            allv = np.concatenate([dv, base])
            r = rankdata(allv)
            auc = (r[:dv.size].sum() - dv.size * (dv.size + 1) / 2) / (dv.size * base.size)
            en[nm] = dict(band=i, auc_dots_vs_footprint=float(auc), median_pct_rank=float(np.median(q)),
                          frac_dots_top_decile=float((q >= .9).mean()), frac_dots_bottom_decile=float((q <= .1).mean()))
    out["h33_band_enrichment"] = en
    # ---- lineage arithmetic: what the reported steps imply IF the removed dots were pure false positives
    # DTI = T / D,  D = 0.8|G| + 0.2 (T + n - M).  Removing m pure-FP dots lowers D by 0.2 m and leaves T unchanged,
    # so  T = 0.2 m / (1/DTI_after_removal_denominator ...)  ->  T (1/DTI0 - 1/DTI1) = 0.2 m.
    steps = [("D2.8 -> SOLO-D2.8 (B=1 collar)", 0.2600, 0.2708, 3891, 44090),
             ("SOLO-D2.8 -> H33 (B=2 collar)", 0.2708, 0.2778, 2545, 40199),
             ("D2.8 -> H33 (both)", 0.2600, 0.2778, 6436, 44090)]
    arith = []
    for label, d0, d1, m, n0 in steps:
        T = 0.2 * m / (1.0 / d0 - 1.0 / d1)
        n1 = n0 - m
        row = dict(step=label, dti_before=d0, dti_after=d1, dots_removed=m, T_if_pure_fp=T, dots_after=n1,
                   credit_per_dot_after=T / n1)
        D1 = T / d1
        row["implied_public_positive_pixels_G"] = {
            f"M_over_T={r}": (D1 - 0.2 * (T + n1 - r * T)) / 0.8 for r in (0.33, 0.5, 1.0)}
        arith.append(row)
    out["lineage_arithmetic_INFERENCE"] = dict(
        assumption="removed dots were pure false positives (dT=0, dM=0); reported scores are owner-reported and rounded to 4 d.p.",
        rows=arith,
        marginal_bar="a dot is worth keeping iff its credit exceeds 0.2*DTI/(1-0.2*DTI) of its false-positive cost; for DTI=0.2778 that is 0.0588",
        footprint_baseline_share_d_cat_gt={str(t): float((d_cat[fp] > t).mean()) for t in (2, 3, 5, 10, 25, 50)})
    path = ROOT / "evidence" / "h33_forensics_20261024.json"
    path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out["lineage_arithmetic_INFERENCE"], indent=1))
    srt = sorted(en.items(), key=lambda kv: -abs(kv[1]["auc_dots_vs_footprint"] - .5))
    for nm, v in srt:
        print(f"{nm:24s} AUC={v['auc_dots_vs_footprint']:.3f} top10%={v['frac_dots_top_decile']:.3f} bot10%={v['frac_dots_bottom_decile']:.3f}")


if __name__ == "__main__":
    main()
