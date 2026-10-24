#!/usr/bin/env python3
"""Independent fail-closed validator for the QTS-88 research GeoTIFF and run card.

Verifies from bytes on disk:
1. Run card and gate parity across registry/ and docs/data/.
2. GeoTIFF and single-TIFF ZIP SHA-256 digests, CRS (EPSG:32611), shape (3730x3292),
   100 m affine transform, nodata=None, zero NaN/Inf anywhere, all values in [0, 1],
   zero outside footprint, zero on mapped catalogue faults, 37,654 positive pixels.
3. Fleet distance-to-catalogue fingerprint (share_le2 == 0.0, share_gt25 >= 0.35).
4. All 29 single-feature leakage canaries <= 0.90 symmetric AUC.
5. Pre-placement and post-placement Spearman |rho| <= 0.90 and like-for-like 3-px
   dot overlap <= 0.70 across all 223 accessible registry rasters.
6. HOLDOUT-DTI provenance (gems57-pooled-hide-v2, n=22,893 withheld positive pixels)
   and paired positive lift over the 19-band no-QTS control.
7. Exits 0 on research validation, and exits 2 on --require-submit when ok_to_submit is False.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "scripts", ROOT / "vendor"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from gems57 import gates, grid, validate  # noqa: E402
from gems88 import gate  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402


def sha256_file(path: Path) -> str:
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def qts88_release_report(root: Path = ROOT) -> dict:
    root = Path(root)
    card = json.loads((root / "registry/qts88_run_card.json").read_text())
    web_card = json.loads((root / "docs/data/qts88_run_card.json").read_text())
    gate_doc = json.loads((root / "registry/qts88_gate.json").read_text())
    web_gate = json.loads((root / "docs/data/qts88_validation.json").read_text())
    uniq_doc = json.loads((root / "evidence/qts88_uniqueness.json").read_text())

    if card != web_card:
        raise ValueError("registry/qts88_run_card.json and docs/data/qts88_run_card.json differ")
    if gate_doc != web_gate:
        raise ValueError("registry/qts88_gate.json and docs/data/qts88_validation.json differ")
    if card["verdict"] != "negative" or card["ok_to_submit"] is not False or card["ok_to_download"] is not True:
        raise ValueError("QTS-88 run card verdict/gate flags invalid")

    tif = root / card["file"]
    zp = root / card["zip_file"]
    receipt = json.loads(tif.with_suffix(".json").read_text())
    if "DO-NOT-SUBMIT" not in tif.name or "DO-NOT-SUBMIT" not in zp.name:
        raise ValueError("QTS-88 negative deliverable must carry DO-NOT-SUBMIT in filename")
    if sha256_file(tif) != card["raster_sha256"] or sha256_file(zp) != card["zip_sha256"]:
        raise ValueError("QTS-88 TIFF/ZIP SHA-256 mismatch")
    if (
        receipt["sha256"] != card["raster_sha256"]
        or receipt["zip_sha256"] != card["zip_sha256"]
        or receipt["submission_name"] != card["submission_name"]
        or receipt["note"] != card["submission_note"]
        or not (0 < len(card["submission_name"]) <= 140)
        or not (0 < len(card["submission_note"]) <= 140)
    ):
        raise ValueError("QTS-88 writer receipt or name/note invalid")

    with zipfile.ZipFile(zp) as zf:
        if zf.namelist() != [tif.name] or zf.read(tif.name) != tif.read_bytes():
            raise ValueError("QTS-88 ZIP must contain exactly the byte-identical GeoTIFF")

    sample = root / "data/bridge/sample_submission.tif"
    gd = grid.load_grid(root / "data/bridge")
    fmt = gates.format_report(tif, sample, footprint=gd.footprint)
    loc = validate.validate(tif, gd.footprint, gd.catalogue)
    ind = validate_artifact(tif, sample)
    pt = gate.portal_validate(tif, sample, gd.footprint)
    pz = gate.portal_validate(zp, sample, gd.footprint)
    if not (fmt["ok"] and loc["all_checks_passed"] and ind["ok"] and pt["ok"] and pz["ok"]):
        raise ValueError("QTS-88 GeoTIFF/ZIP failed independent portal-parity checks")

    vals = gate.read_values(tif, gd.footprint)
    dots = (vals > 0) & gd.footprint
    d_cat = distance_transform_edt(~gd.catalogue)
    fpr = gate.fingerprint(dots, d_cat)
    if (
        int(dots.sum()) != 37_654
        or fpr["share_le2"] != 0.0
        or fpr["share_gt25"] < 0.35
        or not gate.fingerprint_screen(fpr)
    ):
        raise ValueError(f"QTS-88 fingerprint screen failed: {fpr}")

    canaries = card["feature_canaries"]
    if (
        not canaries["all_29_passed"]
        or len(canaries["all_features"]) != 29
        or max(v["symmetric_auc"] for v in canaries["all_features"].values()) > 0.90
    ):
        raise ValueError("QTS-88 single-feature leakage canary check failed")

    hold = card["holdout"]
    exp2 = hold["experiments"]["exp2_qts_pu_gbdt"]
    exp3 = hold["experiments"]["exp3_qts_hybrid_debiased"]
    ctrl = hold["experiments"]["control_raw19_no_qts"]
    lift = hold["paired_differences_vs_exp2"]["control_raw19_no_qts"]
    if (
        hold["evaluator_version"] != "gems57-pooled-hide-v2"
        or hold["withheld_positive_pixels"] != 22893
        or not (exp2["dti"] > ctrl["dti"] > 0.09)
        or not (exp3["dti"] > ctrl["dti"] > 0.09)
        or not (lift["delta"] > 0 and lift["ci95"][0] > 0)
    ):
        raise ValueError("QTS-88 holdout evaluation or paired ablation lift invalid")

    corr = card["correlation_overlap_vs_registry"]
    if (
        not corr["unique_like_for_like"]
        or corr["like_for_like_blockers"] != []
        or corr["worst_like_for_like_overlap_3px"] > 0.70
        or corr["preplacement_max_abs_rho"] > 0.90
        or corr["final_worst_abs_rho"] > 0.90
        or uniq_doc["candidate_sha256"] != card["raster_sha256"]
    ):
        raise ValueError("QTS-88 uniqueness report invalid")

    return {
        "schema": "gems88.qts88.validation-summary.v1",
        "submission_name": card["submission_name"],
        "submission_note": card["submission_note"],
        "file": card["file"],
        "zip_file": card["zip_file"],
        "raster_sha256": card["raster_sha256"],
        "zip_sha256": card["zip_sha256"],
        "ok_to_download": True,
        "ok_to_submit": False,
        "portal_and_like_for_like_unique_ok": True,
        "fingerprint_screen_pass": True,
        "holdout_dti_exp2_pu": exp2["dti"],
        "holdout_dti_exp3_hybrid": exp3["dti"],
        "paired_lift_over_raw19": lift["delta"],
        "paired_lift_ci95": lift["ci95"],
        "verdict": card["verdict"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args(argv)
    report = qts88_release_report(ROOT)
    print(json.dumps(report, indent=2))
    if args.require_submit and not report["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
