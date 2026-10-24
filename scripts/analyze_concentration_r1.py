#!/usr/bin/env python3
"""REPORT-ONLY confounder diagnostic for the R1 CONCENTRATION family.

The three built arms differ only in where the 3,765/7,531 receivers land, and
the blind control scored the hot-prior arm far below the cold-prior mirror.
Before that is read as "the potential-field prior is anti-predictive", this
script tests the competing explanation: that the two block sets sit in
different parts of the *control map* (off-catalogue USGS SGMC faults), so the
comparison is a geography artefact rather than a prior effect.

For donors and receivers of every arm it measures the distance to the nearest
off-catalogue SGMC pixel, the credit actually earned, and the SGMC coverage of
the donor/receiver blocks.  Nothing here is a gate and nothing here changes a
preregistered prediction.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt
from scipy.spatial import cKDTree

import build_prune_variants as bp
import build_spacing_variants as bsp

ROOT = bp.ROOT
RELEASES = ROOT / "releases"
OUT = ROOT / "evidence" / "concentration_r1_diagnostic.json"
R1_ID = bsp.R1_ID
R1_SHA_NAN = bsp.R1_SHA_NAN


def main() -> int:
    verified = bp.verify_manifest()
    lin = bp.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat, h19 = lin["foot"], lin["catalogue"], lin["d_cat"], lin["h19_5"]
    w, _ = bp.build_physical_field_and_canaries(verified, foot, catalogue, h19)
    r1 = bsp.reconstruct_r1(lin, w, verified["sample_submission"])

    with rasterio.open(verified["sgmc_faults_control"]) as ds:
        sgmc = ds.read(1) > 0
    sgmc_off = sgmc & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    d_sgmc = distance_transform_edt(~sgmc_off)
    sy, sx = np.nonzero(sgmc_off)
    sgmc_tree = cKDTree(np.column_stack([sy, sx]).astype(np.float64))

    rows = [r for r in csv.DictReader(open(ROOT / "ledger" / "submissions.csv"))
            if r["parent"] == R1_ID and r["axis"] == "CONCENTRATION"]
    out = {"schema": "gems88.concentration-r1-confounder-diagnostic.v1",
           "parent": R1_ID, "evidence_label": "PROXY (report only; never a gate)",
           "sgmc_off_catalogue_px": int(sgmc_off.sum()),
           "note": ("Receivers in all three arms are off the H19-5 support, so their credit comes from incident "
                    "alignment with off-catalogue SGMC traces. Distance-to-control is the confounder test: if the "
                    "hot-block receivers sit further from the control map than the cold-block receivers, the arm "
                    "difference is geography, not prior."),
           "arms": {}}

    for row in rows:
        with rasterio.open(RELEASES / f"{row['id']}.tif") as ds:
            mask = ds.read(1) > 0.5
        assert int(mask.sum()) == int(row["n_dots"])
        donors = r1 & ~mask
        receivers = mask & ~r1
        rec = {}
        for name, pts in (("donors", donors), ("receivers", receivers)):
            y, x = np.nonzero(pts)
            d = d_sgmc[y, x]
            credit = np.zeros(len(y))
            for radius in (3.0,):
                dk = sgmc_tree.query(np.column_stack([y, x]).astype(np.float64), k=1)[0]
                credit = np.clip(1.0 - dk / radius, 0.0, 1.0)
            rec[name] = {
                "n": int(len(y)),
                "median_dist_to_sgmc_off_catalogue_px": round(float(np.median(d)), 2),
                "frac_within_3px_of_sgmc": round(float((d <= 3.0).mean()), 4),
                "mean_isolated_kernel_credit_per_dot": round(float(credit.mean()), 4),
                "frac_on_h19_5_support": round(float(h19[y, x].mean()), 4),
            }
        out["arms"][row["id"]] = rec
        print(f"{row['value']:14s} donors: med d_sgmc {rec['donors']['median_dist_to_sgmc_off_catalogue_px']:7.2f} "
              f"frac<3px {rec['donors']['frac_within_3px_of_sgmc']:.4f} | receivers: med "
              f"{rec['receivers']['median_dist_to_sgmc_off_catalogue_px']:7.2f} "
              f"frac<3px {rec['receivers']['frac_within_3px_of_sgmc']:.4f} "
              f"credit {rec['receivers']['mean_isolated_kernel_credit_per_dot']:.4f}")

    # Baseline: an untouched random footprint pixel and the parent's own dots.
    rng = np.random.default_rng(bp.SEED)
    fy, fx = np.nonzero(foot)
    pick = rng.choice(len(fy), size=50_000, replace=False)
    out["baseline"] = {
        "random_footprint_px": {
            "median_dist_to_sgmc_off_catalogue_px": round(float(np.median(d_sgmc[fy[pick], fx[pick]])), 2),
            "frac_within_3px_of_sgmc": round(float((d_sgmc[fy[pick], fx[pick]] <= 3.0).mean()), 4),
        },
        "parent_R1_dots": {
            "median_dist_to_sgmc_off_catalogue_px": round(float(np.median(d_sgmc[r1])), 2),
            "frac_within_3px_of_sgmc": round(float((d_sgmc[r1] <= 3.0).mean()), 4),
        },
    }
    print("baseline:", json.dumps(out["baseline"]))
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
