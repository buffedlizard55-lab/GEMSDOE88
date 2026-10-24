#!/usr/bin/env python3
"""Diagnostic D1 -- does any local proxy rank-order the owner-reported public scores?

READ-ONLY measurement of already-existing rasters (no candidate is built here).
The public scores are OWNER-REPORTED CLAIMS copied from the GEMSDOE86 registry
file ``registry/prior_scores.csv`` (evidence class "OWNER-REPORTED"); the
repository holds no organizer receipt for any of them.

Behavioural fingerprints (median distance to the catalogue, share of dots > 10 / > 25 px away) are
tested as predictors of the reported public score as well.

Proxies (all use the vendored official-formula metric ``gems57.metric.dti_binary``;
the mapped catalogue is masked exactly as the organiser describes in thread 11516):
  sgmc_gap  : truth = USGS SGMC bedrock-map fault pixels more than 3 px from the
              Quaternary catalogue  (an *off-catalogue* truth population)
  sgmc_all  : truth = every SGMC fault pixel not on the catalogue
  d_cat_*   : share of dots within 2 / 3 px of the catalogue (collar waste)
  n_dots    : dot budget
Rank statistics: Spearman rho and Kendall tau against the reported score, over
(a) all rasters, (b) reported score >= 0.15, (c) reported score >= 0.23.
Output: evidence/proxy_calibration_20261024.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import kendalltau, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import grid as grid_mod, metric  # noqa: E402

R = ROOT / "data" / "registry"
F = ROOT / "data" / "fleet"
FAM = R / "family_60gemsdoe"

# (label, path, owner-reported public score)  -- scores from registry/prior_scores.csv (GEMSDOE86 mirror)
FLEET = [
    ("GEMSDOE32 H33 b2", R / "h33_education.tif", 0.2778),
    ("GEMSDOE36 Anderson-PINN", R / "gems36_anderson_pinn.tif", 0.2750),
    ("GEMSDOE28 h36-1 rung30-blind", F / "GEMSDOE28__gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710),
    ("GEMSDOE28 SOLO-D2.8", R / "gems28_h27_4.tif", 0.2708),
    ("GEMSDOE28 h38-1 hf-euler", F / "GEMSDOE28__gems28-h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan.tif", 0.2707),
    ("GEMSDOE33 h33d tip-stepover", F / "GEMSDOE33__GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", 0.2632),
    ("GEMSDOE25 D2.8", R / "gems25_d28.tif", 0.2600),
    ("GEMSDOE70 p5 dual-submod", R / "gems70_p5_dualsubmod.tif", 0.2478),
    ("GEMSDOE24 D1.5", FAM / "calib_d15_02477.tif", 0.2477),
    ("GEMSDOE49 gate_ortho", R / "gems49_gate_ortho.tif", 0.2376),
    ("GEMSDOE63 cvarlw-thin", F / "GEMSDOE63__gemsdoe63-cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4-nan.tif", 0.2303),
    ("19GEMSDOE H19-5", R / "gems19_h19_5.tif", 0.1922),
    ("GEMSDOE73 mcsc-blakely", F / "GEMSDOE73__gems73-h73-mcsc-seamfree-blakely-37654dots-20261021T073716Z-b27ac445-zeros.tif", 0.1917),
    ("19GEMSDOE H19-4", FAM / "calib_h194_01894.tif", 0.1894),
    ("16GEMSDOE H16-1", FAM / "calib_h161_01855.tif", 0.1855),
    ("GEMSDOE75 radon-ridge", F / "GEMSDOE75__gems75-trlt-radon-loco-ridge-20261021-zeros.tif", 0.1627),
    ("GEMSDOE76 geotherm-tilt", F / "GEMSDOE76__gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros.tif", 0.1555),
    ("GEMSDOE66 lidar03-cv", F / "GEMSDOE66__gems66-lidar03-cvretrain-reliefdecile-37654dots-20261020T190152Z-zeros.tif", 0.1152),
    ("GEMSDOE80 h80g-choquet", F / "GEMSDOE80__gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros.tif", 0.0943),
    ("GEMSDOE81 cont-poisson-buf2", F / "GEMSDOE81__gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros.tif", 0.0041),
]


def dot_mask(path, fp):
    with rasterio.open(path) as ds:
        a = ds.read(1)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    return (a > 0) & fp, int(np.unique(a).size)


def stat(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 4 or np.ptp(x) == 0:
        return dict(n=len(x), spearman=None, kendall=None)
    r, p = spearmanr(x, y)
    t, pt = kendalltau(x, y)
    return dict(n=int(len(x)), spearman=float(r), spearman_p=float(p), kendall=float(t), kendall_p=float(pt))


def main():
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    d_cat = ndi.distance_transform_edt(~cat)
    with rasterio.open(ROOT / "data/external/sgmc_faults_100m.tif") as ds:
        sgmc = ds.read(1) > 0
    sgmc_gap = sgmc & (d_cat > 3) & fp
    sgmc_all = sgmc & ~cat & fp
    # chance level for "near SGMC-gap": share of scored footprint within 3 px of it
    near_gap = ndi.distance_transform_edt(~sgmc_gap) <= 3
    chance = float(near_gap[fp & ~cat].mean())
    out = dict(evidence_class="PROXY-CALIBRATION on OWNER-REPORTED scores (no organizer receipts)",
               truth_px=dict(sgmc_gap=int(sgmc_gap.sum()), sgmc_all=int(sgmc_all.sum())),
               chance_share_within_3px_of_sgmc_gap=chance, rows=[])
    for label, path, score in FLEET:
        path = Path(path)
        if not path.exists():
            out["rows"].append(dict(label=label, missing=str(path)))
            continue
        m, nuniq = dot_mask(path, fp)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        row = dict(label=label, file=path.name, sha256=sha, reported_public_dti=score, n_dots=int(m.sum()), n_unique_values=nuniq)
        for nm, truth in (("sgmc_gap", sgmc_gap), ("sgmc_all", sgmc_all)):
            r = metric.dti_binary(m, truth, valid=fp, known=cat)
            row[f"dti_{nm}"] = r["dti"]
            row[f"cov_{nm}"] = r["coverage"]
            row[f"prec_{nm}"] = 1.0 - r["fp"] / max(1, r["n_emitted"])
        dc = d_cat[m]
        row["frac_dots_dcat_le2"] = float((dc <= 2).mean())
        row["frac_dots_dcat_le3"] = float((dc <= 3).mean())
        row["median_d_cat_px"] = float(np.median(dc))
        row["frac_dots_dcat_gt10"] = float((dc > 10).mean())
        row["frac_dots_dcat_gt25"] = float((dc > 25).mean())
        row["frac_dots_within3_of_sgmc_gap"] = float(near_gap[m].mean())
        row["lift_vs_chance"] = row["frac_dots_within3_of_sgmc_gap"] / chance
        out["rows"].append(row)
        print(f"{label:34s} rep={score:.4f} n={row['n_dots']:7d} dti_gap={row['dti_sgmc_gap']:.4f} dti_all={row['dti_sgmc_all']:.4f} "
              f"near_gap={row['frac_dots_within3_of_sgmc_gap']:.3f} lift={row['lift_vs_chance']:.2f} d<=2={row['frac_dots_dcat_le2']:.3f}", flush=True)
    rows = [r for r in out["rows"] if "missing" not in r]
    keys = ["dti_sgmc_gap", "dti_sgmc_all", "prec_sgmc_gap", "frac_dots_within3_of_sgmc_gap", "frac_dots_dcat_le2", "frac_dots_dcat_le3",
            "median_d_cat_px", "frac_dots_dcat_gt10", "frac_dots_dcat_gt25", "n_dots"]
    corr = {}
    for thr_name, thr in (("all", -1.0), ("score>=0.15", 0.15), ("score>=0.23", 0.23)):
        sel = [r for r in rows if r["reported_public_dti"] >= thr]
        corr[thr_name] = {k: stat([r[k] for r in sel], [r["reported_public_dti"] for r in sel]) for k in keys}
    out["rank_correlation_with_reported_public_score"] = corr
    out["caveats"] = [
        "Reported scores are owner-reported claims; no organizer receipt is in the repository.",
        "SGMC positions are nominally 1:500,000-1:1,000,000 scale and may be hundreds of metres off, depressing absolute DTI for every raster.",
        "A rank correlation over ~20 rasters is weak evidence (n small, rasters share ancestry); treat as a sanity check, not a validation.",
    ]
    path = ROOT / "evidence" / "proxy_calibration_20261024.json"
    path.write_text(json.dumps(out, indent=2))
    print(json.dumps(corr, indent=1))


if __name__ == "__main__":
    main()
