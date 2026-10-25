#!/usr/bin/env python3
"""Zero-human-intervention validator for the H88-VHGD lane (PREREG-20261025-VHGD88).

Verifies on disk (compatible with CI `--validation` input tier):
  1. Canonical registry & Pages JSON parity (`vhgd88_run_card.json`, `vhgd88_gate_verdict.json`,
     `vhgd88_holdout_20261025.json`, `vhgd88_uniqueness_20261025.json`).
  2. Saved GeoTIFF & single-TIFF `.zip` SHA-256 parity, DrivenData portal `[0, 1]` invariants
     via BOTH `rasterio` and independent `tifffile` decoder (`float32`, `EPSG:32611`,
     `3730x3292`, exact `sample_submission.tif` geotransform, `nodata=None`, zero NaN/Inf,
     zeros outside footprint, zeros on `existing_faults.tif`).
  3. H33-forensic 3-stratum geometry (`27,821` binary dots, `share_le2 == 0.0`, `share_gt25 >= 0.35`).
  4. Protocol gates: 84/84 single-feature leakage canaries `<= 0.90`, `HOLDOUT-DTI` labels +
     95% CIs (`n = 22,893`), pre-placement `|rho| <= 0.90`, 239-raster like-for-like 3-px dot
     overlap `<= 0.70` (`0.688545 <= 0.70`), literal `17GEMSDOE` dense-witness `1.0000` stop,
     and fail-closed `ok_to_download=True`, `ok_to_submit=False`, `verdict="negative"`.
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
import scipy.ndimage as ndi
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import gates, grid, uniqueness, validate  # noqa: E402
from gems88 import gate  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()



def _require(cond: object, msg: object = "validation check failed") -> None:
    if not cond:
        raise AssertionError(str(msg))

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--require-submit",
        action="store_true",
        help="Exit with code 2 unless ok_to_submit is True.",
    )
    args = ap.parse_args()

    rc_reg = json.loads((ROOT / "registry/vhgd88_run_card.json").read_text())
    rc_web = json.loads((ROOT / "docs/data/vhgd88_run_card.json").read_text())
    gv_reg = json.loads((ROOT / "registry/vhgd88_gate_verdict.json").read_text())
    gv_web = json.loads((ROOT / "docs/data/vhgd88_gate_verdict.json").read_text())
    ho_ev = json.loads((ROOT / "evidence/vhgd88_holdout_20261025.json").read_text())
    ho_web = json.loads((ROOT / "docs/evidence/vhgd88_holdout_20261025.json").read_text())
    uq_ev = json.loads((ROOT / "evidence/vhgd88_uniqueness_20261025.json").read_text())
    uq_web = json.loads((ROOT / "docs/evidence/vhgd88_uniqueness_20261025.json").read_text())
    prereg = json.loads((ROOT / "registry/preregistration_vhgd88.json").read_text())

    _require(rc_reg == rc_web, "vhgd88_run_card.json drift between registry/ and docs/data/")
    _require(gv_reg == gv_web, "vhgd88_gate_verdict.json drift between registry/ and docs/data/")
    _require(ho_ev == ho_web, "vhgd88_holdout_20261025.json drift between evidence/ and docs/evidence/")
    _require(uq_ev == uq_web, "vhgd88_uniqueness_20261025.json drift between evidence/ and docs/evidence/")

    _require(prereg["preregistration_id"] == rc_reg["preregistration_id"] == "PREREG-20261025-VHGD88")
    _require(prereg["gates"]["ok_to_submit"] is False)
    _require(rc_reg["lane"] == "H88-VHGD")
    _require(rc_reg["verdict"] == "negative")
    _require(gv_reg["label"] == "OK TO DOWNLOAD - NOT OK TO SUBMIT" and gv_reg["approved_for_weekly_slot"] is False)
    _require(rc_reg["ok_to_download"] is True and gv_reg["ok_to_download"] is True)
    _require(rc_reg["ok_to_submit"] is False and gv_reg["ok_to_submit"] is False)
    _require(rc_reg["organizer_confirmed_score"] is None)
    _require(rc_reg["weekly_slots_used"] == 0)

    sub = rc_reg["submission"]
    _require(0 < len(sub["submission_name"]) <= 140)
    _require(0 < len(sub["submission_note"]) == sub["submission_note_chars"] <= 140)
    _require("UNSCORED" in sub["submission_note"])

    tif_path = ROOT / sub["file"]
    zip_path = ROOT / sub["zip_file"]
    _require(tif_path.is_file() and "DO-NOT-SUBMIT" in tif_path.name, f"missing/unmarked tif: {tif_path}")
    _require(zip_path.is_file() and "DO-NOT-SUBMIT" in zip_path.name, f"missing/unmarked zip: {zip_path}")
    _require(_sha256(tif_path) == rc_reg["raster_sha256"] == gv_reg["sha256"])
    _require(_sha256(zip_path) == rc_reg["zip_sha256"] == gv_reg["zip_sha256"])

    with zipfile.ZipFile(zip_path) as zf:
        _require(zf.namelist() == [tif_path.name], f"ZIP must contain solely {tif_path.name}")
        _require(zf.read(tif_path.name) == tif_path.read_bytes(), "ZIP payload differs from standalone GeoTIFF")

    # Independent second-decoder verification via tifffile
    arr_tf = tifffile.imread(tif_path)
    _require(arr_tf.shape == (3730, 3292) and arr_tf.dtype == np.float32)
    _require(np.isfinite(arr_tf).all(), "NaN or Inf detected by tifffile")
    _require(float(arr_tf.min()) >= 0.0 and float(arr_tf.max()) <= 1.0, "Values outside [0, 1]")

    sample_tif = ROOT / "data/bridge/sample_submission.tif"
    faults_tif = ROOT / "data/bridge/existing_faults.tif"
    dense_witness = ROOT / "data/registry/dense_17gemdoe.tif"
    _require(sample_tif.is_file() and faults_tif.is_file() and dense_witness.is_file())

    g = grid.load_grid(ROOT / "data/bridge")
    val_rep = validate.validate(tif_path, g.footprint, g.catalogue)
    validate.assert_submittable(val_rep)
    _require(val_rep["all_checks_passed"], f"validate.validate failed: {val_rep}")
    fmt_rep = gates.format_report(tif_path, sample_tif)
    _require(fmt_rep["ok"], f"gates.format_report failed: {fmt_rep}")
    p_tif = gate.portal_validate(tif_path, sample_tif, g.footprint)
    _require(p_tif["ok"] and p_tif["n_dots"] == 27821, "gate.portal_validate failed")

    with rasterio.open(tif_path) as ds:
        _require(ds.count == 1 and ds.dtypes == ("float32",) and ds.nodata is None)
        arr = ds.read(1)
    _require(float(np.abs(arr[~g.footprint]).max()) == 0.0, "Nonzero predictions outside footprint")
    _require(float(np.abs(arr[g.catalogue]).max()) == 0.0, "Nonzero predictions on known catalogue faults")

    dots = (arr > 0) & g.footprint
    n_dots = int(dots.sum())
    _require(n_dots == sub["positive_pixels"] == 27821, f"Expected 27821 dots, got {n_dots}")
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    share_le2 = float((d_cat[dots] <= 2.0).mean())
    share_gt25 = float((d_cat[dots] > 25.0).mean())
    _require(share_le2 == 0.0, f"Expected 0 collar dots <= 2px, got {share_le2}")
    _require(share_gt25 >= 0.35 and abs(share_gt25 - sub["share_gt25"]) < 1e-6)

    # Re-verify literal dense-witness overlap directly on disk
    with rasterio.open(dense_witness) as wds:
        w_dots = (wds.read(1) > 0) & g.footprint
    lit_ov = uniqueness.dot_overlap(dots, w_dots, radius_px=3)
    _require(lit_ov == 1.0, f"Expected literal 17GEMSDOE overlap 1.0, got {lit_ov}")

    # Verify protocol metrics recorded in run card & holdout evidence
    canary = rc_reg["leakage_canary"]
    _require(canary["passed"] is True and canary["features_tested"] == 84)
    _require(canary["max_symmetric_auc"] <= 0.90)

    hd = rc_reg["holdout_dti"]
    _require(hd["evidence_class"] == "HOLDOUT-DTI")
    _require(hd["evaluator_version"] == "gems57-pooled-hide-v2")
    _require(hd["withheld_positive_pixels_overall"] == 22893)
    exp2 = hd["exp2_poe_unconstrained"]
    _require(exp2["overall"]["dti"] > hd["control_adhr_lgbm_overall"]["dti"])
    _require(exp2["paired_delta_vs_adhr_control"]["delta"] > 0.0)
    _require(exp2["paired_delta_vs_adhr_control"]["ci95"][0] > 0.0)
    _require(exp2["far_gt10px"]["dti"] > 0.131922)
    _require(exp2["blind_gt25px"]["dti"] > 0.090449)

    corr = rc_reg["correlation_overlap_vs_registry"]
    _require(corr["surface_preplacement_max_abs_spearman"] <= 0.90)
    _require(corr["final_worst_like_for_like_overlap_3px"]["value"] <= 0.70)
    _require(corr["like_for_like_blockers"] == [])
    _require(corr["unique_like_for_like"] is True)
    _require(corr["unique_literal"] is False)

    print(
        f"PASS validate_vhgd88: {tif_path.name} sha256={rc_reg['raster_sha256'][:16]} "
        f"dots={n_dots} share_gt25={share_gt25:.4f} max_like_ov={corr['final_worst_like_for_like_overlap_3px']['value']:.4f} "
        f"Exp2_DTI={exp2['overall']['dti']:.6f} blind_DTI={exp2['blind_gt25px']['dti']:.6f} ok_to_submit=False"
    )
    if args.require_submit and not rc_reg["ok_to_submit"]:
        print("HOLD FOR SUBMIT: ok_to_submit=False (literal 17GEMSDOE dense witness + stratified overall bar)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
