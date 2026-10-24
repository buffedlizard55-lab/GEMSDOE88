#!/usr/bin/env python3
"""Geometry of every restored raster whose live score is a user-reported CLAIM.

Question (IR-88-59): why did the h33 lineage (0.2778 CLAIM) beat its ancestors and the
unrelated ideas?  This script measures, for each restored dot raster, the
distance-to-catalogue profile and the nearest-neighbour spacing of its dots, then
tabulates them next to the CLAIMED live score.  Scores are CLAIMS copied from the
prompt/ledger (no portal receipt exists); n = 13 so nothing here is a fitted model,
only a descriptive table.  Output: evidence/lineage_live_vs_geometry.json
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
# (label, path, CLAIMED live score or None, source of the claim)
FILES = [
    ("h16-1", "registry/family_60gemsdoe/calib_h161_01855.tif", 0.1855, "ledger/historical_climb.csv + prompt (16GEMSDOE)"),
    ("h19-4", "registry/family_60gemsdoe/calib_h194_01894.tif", 0.1894, "ledger/historical_climb.csv + prompt (19GEMSDOE)"),
    ("h19-5", "registry/gems19_h19_5.tif", 0.1922, "ledger/historical_climb.csv"),
    ("d1-5", "registry/family_60gemsdoe/calib_d15_02477.tif", 0.2477, "ledger/historical_climb.csv"),
    ("d2-8", "registry/gems25_d28.tif", 0.2600, "ledger/historical_climb.csv"),
    ("h27-4", "registry/gems28_h27_4.tif", 0.2708, "ledger/historical_climb.csv"),
    ("h33 (R0)", "registry/h33_education.tif", 0.2778, "ledger/historical_climb.csv"),
    ("anderson-pinn", "registry/gems36_anderson_pinn.tif", 0.2750, "prompt (GEMSDOE36)"),
    ("gate-ortho", "registry/gems49_gate_ortho.tif", 0.2376, "prompt (GEMSDOE49)"),
    ("p5-dual-submod", "registry/gems70_p5_dualsubmod.tif", 0.2478, "prompt (GEMSDOE70)"),
    ("h83-gvcd", "registry/gems83_h83_gvcd.tif", 0.0573, "prompt (GEMSDOE83)"),
    ("h85a-fold", "registry/gems85_h85a_foldproper.tif", 0.1110, "prompt (GEMSDOE85)"),
    ("h81-contasb", "registry/gems81_contasb.tif", 0.0041, "prompt (GEMSDOE81)"),
    ("PROVCREST (this repo)", None, None, "unscored"),
]


def main():
    prov = json.loads((ROOT / "registry/provcrest_run_card.json").read_text())
    with rasterio.open(D / "bridge/sample_submission.tif") as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(D / "bridge/existing_faults.tif") as f:
        ex = f.read(1)
    cat = np.isfinite(ex) & (ex > 0)
    dcat = ndi.distance_transform_edt(~cat)
    rows = []
    for label, rel, score, src in FILES:
        path = ROOT / prov["submission"]["file"] if rel is None else D / rel
        with rasterio.open(path) as r:
            a = r.read(1)
        m = np.isfinite(a) & (a > 0) & fp
        yx = np.argwhere(m)
        d = dcat[m]
        nn = cKDTree(yx).query(yx, k=2)[0][:, 1]
        rows.append(dict(
            label=label, claimed_live_score=score, claim_source=src, n_dots=int(m.sum()),
            frac_d_cat_le_3px=round(float((d <= 3).mean()), 4),
            frac_d_cat_3_to_10px=round(float(((d > 3) & (d <= 10)).mean()), 4),
            frac_d_cat_10_to_25px=round(float(((d > 10) & (d <= 25)).mean()), 4),
            frac_d_cat_gt_25px=round(float((d > 25).mean()), 4),
            median_d_cat_px=round(float(np.median(d)), 2),
            median_nn_spacing_px=round(float(np.median(nn)), 3),
            frac_nn_lt_2px=round(float((nn < 2).mean()), 4)))
    scored = [r for r in rows if r["claimed_live_score"] is not None]
    x = np.array([r["median_d_cat_px"] for r in scored]); y = np.array([r["claimed_live_score"] for r in scored])
    from scipy.stats import spearmanr
    rho = spearmanr(x, y)
    out = dict(schema="gems88.lineage-geometry.v1", evidence_class="CLAIM (live scores are user-reported; no receipts)",
               n_scored=len(scored),
               spearman_median_dcat_vs_claimed_score=dict(rho=round(float(rho.statistic), 3), p=round(float(rho.pvalue), 4),
                    caveat="descriptive, n=13, lineage members are not independent"),
               rows=rows)
    (ROOT / "evidence/lineage_live_vs_geometry.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["spearman_median_dcat_vs_claimed_score"]))
    for r in rows:
        print(r["label"], r["claimed_live_score"], r["n_dots"], r["median_d_cat_px"], r["median_nn_spacing_px"], r["frac_d_cat_gt_25px"])


if __name__ == "__main__":
    main()
