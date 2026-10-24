#!/usr/bin/env python3
"""Independent (second-implementation) audit of the MDPS-88 deliverable.

Re-derives from on-disk bytes, with code written separately from the builder:
format/range/grid vs the sample submission, catalogue/footprint exclusion,
ZIP integrity, dot spacing/collar, literal 3 px overlap vs the H33 lineage,
pooled HOLDOUT-DTI arithmetic from per-fold terms, and metric self-consistency
(vendor exact vs vendor brute force on random small grids).

Exit codes: 0 = audit passes (scientific verdict may still be negative);
2 = --require-submit given but the run card is not ok_to_submit; 1 = audit failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor")]
from gems57 import metric  # noqa: E402


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pooled_from_rows(rows, arm, kind):
    if kind == "far":
        tp = sum(r[arm]["far_tpw"] for r in rows)
        fp = sum(r[arm]["far_fpw"] for r in rows)
        n = sum(r["far_withheld_positive_pixels"] for r in rows)
    else:
        tp = sum(r[arm]["tpw"] for r in rows)
        fp = sum(r[arm]["fpw"] for r in rows)
        n = sum(r["withheld_positive_pixels"] for r in rows)
    fn = n - tp
    return tp / (tp + 0.2 * fp + 0.8 * fn + 1e-12), n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args()
    card = json.loads((ROOT / "registry/mdps88_run_card.json").read_text())
    tif = ROOT / card["raster"]["file"]
    failures: list[str] = []
    checks: dict[str, object] = {}

    raw = tif.read_bytes()
    checks["sha256_matches_card"] = sha256_bytes(raw) == card["raster_sha256"]
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        meta = (ds.count, ds.dtypes[0], ds.height, ds.width, str(ds.crs), tuple(ds.transform)[:6], ds.nodata)
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        s = ds.read(1)
        smeta = (ds.height, ds.width, str(ds.crs), tuple(ds.transform)[:6])
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        f = ds.read(1)
    fp = np.isfinite(s)
    cat = (f > 0) & fp
    checks["single_band_float32"] = meta[0] == 1 and meta[1] == "float32"
    checks["grid_matches_sample"] = (meta[2], meta[3], meta[4], meta[5]) == smeta
    checks["nodata_is_none"] = meta[6] is None
    checks["all_finite"] = bool(np.isfinite(a).all())
    checks["range_0_1"] = bool(a.min() >= 0.0 and a.max() <= 1.0)
    checks["values_are_binary_01"] = set(np.unique(a).tolist()) <= {0.0, 1.0}
    dots = a > 0
    checks["dot_count"] = int(dots.sum())
    checks["dot_count_matches_card"] = int(dots.sum()) == card["raster"]["dots"]
    checks["zero_dots_on_catalogue"] = int((dots & cat).sum()) == 0
    checks["zero_dots_outside_footprint"] = int((dots & ~fp).sum()) == 0

    d_cat = distance_transform_edt(~cat)
    dmin = float(d_cat[dots].min())
    checks["min_distance_to_catalogue_px"] = dmin
    checks["b2_collar_respected"] = dmin > 2.0
    yx = np.column_stack(np.nonzero(dots))
    dist, _ = cKDTree(yx).query(yx, k=2)
    nn = dist[:, 1]
    checks["min_nn_spacing_px"] = float(nn.min())
    checks["median_nn_spacing_px"] = float(np.median(nn))
    checks["spacing_at_least_2.83_minus_eps"] = bool(nn.min() >= 2.83 - 1e-6)

    zip_path = ROOT / card["raster"]["zip"]
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        inner = z.read(names[0]) if len(names) == 1 else b""
    checks["zip_one_member"] = len(names) == 1
    checks["zip_member_name_is_tif_name"] = names == [tif.name]
    checks["zip_member_bytes_identical"] = sha256_bytes(inner) == card["raster_sha256"]
    checks["zip_sha_matches_card"] = sha256_bytes(zip_path.read_bytes()) == card["raster"]["zip_sha256"]

    # literal forward overlap vs the lineage that owns 0.2778 (independent EDT code)
    lit = {}
    for label, rel in [("H33_R0", "data/registry/h33_education.tif"),
                       ("SOLO_D28", "data/registry/gems28_h27_4.tif"),
                       ("D28", "data/registry/gems25_d28.tif"),
                       ("H19_5", "data/registry/gems19_h19_5.tif")]:
        with rasterio.open(ROOT / rel) as ds:
            t = np.isfinite(ds.read(1)) & (ds.read(1) > 0) if False else None
        with rasterio.open(ROOT / rel) as ds:
            arr = ds.read(1)
        t = np.isfinite(arr) & (arr > 0)
        d = distance_transform_edt(~t)
        lit[label] = float((d[dots] <= 3.0).mean())
    checks["literal_forward_overlap_3px_vs_lineage"] = lit
    checks["not_a_lineage_copy"] = all(v <= 0.70 for v in lit.values())
    # exact pixel overlap with H33
    with rasterio.open(ROOT / "data/registry/h33_education.tif") as ds:
        h33 = ds.read(1) > 0
    checks["exact_pixel_overlap_frac_vs_H33"] = float((dots & h33).sum() / max(int(dots.sum()), 1))

    # pooled arithmetic from per-fold rows (E2 decisive experiment)
    ev = json.loads((ROOT / "evidence/mdps88_experiment2_20261024.json").read_text())
    rows_chk = {}
    for arm in ("base283", "mdps_mix", "mdps_far", "r0_fixed"):
        for kind in ("far", "all"):
            got, n = pooled_from_rows(ev["per_fold"], arm, kind)
            want = ev["pooled"][f"{kind}__candidate_mdps_mix"]["scores"][arm]["dti"]
            rows_chk[f"{arm}_{kind}"] = dict(recomputed=got, stored=want, n=n,
                                             ok=bool(abs(got - want) < 2e-4))
    checks["pooled_arithmetic_recomputed"] = rows_chk
    checks["pooled_arithmetic_all_ok"] = all(v["ok"] for v in rows_chk.values())

    # metric self-consistency: exact vs brute force on random small grids
    rng = np.random.default_rng(7)
    worst = 0.0
    for _ in range(30):
        truth = rng.random((14, 13)) < 0.15
        pred = np.where(rng.random((14, 13)) < 0.25, rng.random((14, 13)), 0.0)
        worst = max(worst, abs(metric.dti_exact(pred, truth)["dti"] - metric.dti_bruteforce(pred, truth)["dti"]))
    checks["metric_exact_vs_bruteforce_max_abs_err"] = float(worst)
    checks["metric_self_consistent"] = bool(worst < 1e-9)

    checks["note_len_le_140"] = len(card["submission_note"]) <= 140
    checks["name_len_le_140"] = len(card["submission_name"]) <= 140
    checks["filename_matches_verdict"] = (("DO-NOT-SUBMIT" in tif.name) == (not card["ok_to_submit"]))

    bool_keys = [k for k, v in checks.items() if isinstance(v, bool)]
    for k in bool_keys:
        if not checks[k]:
            failures.append(k)
    out = dict(evidence_class="INDEPENDENT-AUDIT (second implementation, on-disk bytes)",
               file=str(tif.relative_to(ROOT)), sha256=card["raster_sha256"],
               checks=checks, failures=failures,
               scientific_verdict=card["verdict"], ok_to_submit=card["ok_to_submit"],
               ok_to_download=True,
               audit_passed=not failures)
    (ROOT / "evidence/mdps88_independent_audit_20261024.json").write_text(json.dumps(out, indent=1, default=float))
    (ROOT / "docs/data/mdps88_validation.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({k: checks[k] for k in bool_keys + ["dot_count", "min_nn_spacing_px",
          "min_distance_to_catalogue_px", "literal_forward_overlap_3px_vs_lineage",
          "exact_pixel_overlap_frac_vs_H33", "pooled_arithmetic_all_ok"]}, indent=1, default=float))
    if failures:
        print("AUDIT FAILURES:", failures)
        return 1
    print("INDEPENDENT AUDIT: PASS")
    if args.require_submit and not card["ok_to_submit"]:
        print("NOT OK TO SUBMIT (scientific gates failed; see run card)")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
