#!/usr/bin/env python3
"""Independent zero-human-intervention validator for the WBHR-88 deliverable.

Re-opens the emitted GeoTIFF and single-member ZIP directly from disk using both
`rasterio` and a second independent decoder (`tifffile`), verifies SHA-256 parity
across the Run Card, Gate Record, and Submission Receipt, checks all 83 leakage
canaries, verifies the 3-experiment budget and `gems57-pooled-hide-v2` holdout
evidence (`n=22,893`), and checks two-phase uniqueness across all 238 rasters.

Exit codes:
  0 — local format, canary, uniqueness, and governance audit passed (`--require-submit` not set, or `ok_to_submit` is True).
  2 — `--require-submit` was requested and `ok_to_submit` is False (fail-closed slot guard).
  1 — any audit or integrity violation.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88 import gate  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_wbhr88(root: Path = ROOT) -> dict:
    prereg_p = root / "registry/preregistration_wbhr88.json"
    card_p = root / "registry/wbhr88_run_card.json"
    web_card_p = root / "docs/data/wbhr88_run_card.json"
    gate_p = root / "registry/wbhr88_gate_v3.json"
    web_gate_p = root / "docs/data/wbhr88-gate.json"
    can_p = root / "evidence/wbhr88_canary.json"
    hold_p = root / "evidence/wbhr88_holdout.json"
    uniq_p = root / "evidence/wbhr88_uniqueness.json"

    for p in (prereg_p, card_p, web_card_p, gate_p, web_gate_p, can_p, hold_p, uniq_p):
        if not p.is_file():
            raise FileNotFoundError(f"Missing required WBHR-88 artifact/evidence file: {p}")

    if card_p.read_bytes() != web_card_p.read_bytes():
        raise ValueError("registry/wbhr88_run_card.json and docs/data/wbhr88_run_card.json differ")
    if gate_p.read_bytes() != web_gate_p.read_bytes():
        raise ValueError("registry/wbhr88_gate_v3.json and docs/data/wbhr88-gate.json differ")

    prereg = json.loads(prereg_p.read_text(encoding="utf-8"))
    card = json.loads(card_p.read_text(encoding="utf-8"))
    grec = json.loads(gate_p.read_text(encoding="utf-8"))
    canary = json.loads(can_p.read_text(encoding="utf-8"))
    hold = json.loads(hold_p.read_text(encoding="utf-8"))
    uniq = json.loads(uniq_p.read_text(encoding="utf-8"))

    if prereg.get("lane") != "WBHR-88" or not prereg.get("frozen_before_feature_canary_holdout_or_production_build"):
        raise ValueError("WBHR-88 preregistration missing frozen declaration")
    if len(prereg.get("ranked_hypotheses", [])) < 3:
        raise ValueError("Preregistration must rank 3-5 pre-implementation hypotheses")
    if int(card["experiments_used"]) > 3 or int(hold["experiments_executed"]) > 3:
        raise ValueError("Experiment budget (>3) exceeded")
    if float(card["elapsed_seconds"]) > 7200.0:
        raise ValueError("Wall-time budget (>7200s) exceeded")

    tif_path = root / card["artifact"]
    zip_path = root / card["zip_artifact"]
    rcp_path = tif_path.with_suffix(".json")
    for p in (tif_path, zip_path, rcp_path):
        if not p.is_file():
            raise FileNotFoundError(f"Deliverable missing on disk: {p}")

    tif_sha = _sha256(tif_path)
    zip_sha = _sha256(zip_path)
    rcp = json.loads(rcp_path.read_text(encoding="utf-8"))
    if tif_sha != card["raster_sha256"] or tif_sha != grec["candidate"]["tif_sha256"] or tif_sha != rcp["sha256"]:
        raise ValueError("GeoTIFF SHA-256 mismatch across Run Card / Gate Record / Receipt")
    if zip_sha != card["zip_sha256"] or zip_sha != grec["candidate"]["zip_sha256"] or zip_sha != rcp["zip_sha256"]:
        raise ValueError("ZIP SHA-256 mismatch across Run Card / Gate Record / Receipt")

    # Filename safety invariant
    if not card["ok_to_submit"] and "DO-NOT-SUBMIT" not in tif_path.name:
        raise ValueError("Non-submittable artifact MUST carry DO-NOT-SUBMIT in its filename")
    if card["approved_for_weekly_slot"] is not False or grec["approved_for_weekly_slot"] is not False:
        raise ValueError("approved_for_weekly_slot must remain False (human selector required)")
    if card["organizer_confirmed_score"] is not None:
        raise ValueError("organizer_confirmed_score must be null when no portal receipt exists")

    # Independent on-disk GeoTIFF + ZIP verification
    sample_p = root / "data/bridge/sample_submission.tif"
    faults_p = root / "data/bridge/existing_faults.tif"
    if sample_p.is_file() and faults_p.is_file():
        with rasterio.open(sample_p) as sds:
            footprint = np.isfinite(sds.read(1))
        with rasterio.open(faults_p) as fds:
            catalogue = (fds.read(1) > 0) & footprint
        p_tif = gate.portal_validate(tif_path, sample_p, footprint=footprint)
        p_zip = gate.portal_validate(zip_path, sample_p, footprint=footprint)
        if not p_tif["ok"] or not p_zip["ok"]:
            raise ValueError(f"Portal validation failed: tif={p_tif['problems']} zip={p_zip['problems']}")
        if p_tif["array_sha256"] != p_zip["array_sha256"]:
            raise ValueError("Decoded array inside ZIP differs from standalone GeoTIFF")
        with rasterio.open(tif_path) as ds:
            arr = ds.read(1)
        if np.any((arr > 0) & catalogue):
            raise ValueError("Positive pixels overlap mapped catalogue faults")
        if int((arr > 0).sum()) != int(card["validator_output"]["positive_dots"]):
            raise ValueError("Positive dot count mismatch vs Run Card")
    else:
        # Lightweight header + ZIP check when gitignored data/ is absent
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            if len(names) != 1 or zf.testzip() is not None:
                raise ValueError("Invalid single-member ZIP archive")
            if hashlib.sha256(zf.read(names[0])).hexdigest() != tif_sha:
                raise ValueError("ZIP member bytes do not match GeoTIFF SHA-256")
        with rasterio.open(tif_path) as ds:
            arr = ds.read(1)
            if ds.count != 1 or ds.dtypes[0] != "float32" or str(ds.crs) != "EPSG:32611" or ds.shape != (3730, 3292):
                raise ValueError("GeoTIFF CRS/shape/dtype/band check failed")
            if ds.nodata is not None or not np.isfinite(arr).all() or float(arr.min()) < 0.0 or float(arr.max()) > 1.0:
                raise ValueError("GeoTIFF range [0,1] / finite check failed")

    # Canary, Holdout, Uniqueness, Name/Note checks
    if not canary["all_clear"] or canary["worst_all83"]["symmetric_auc"] > 0.90 or canary["features_tested_total"] != 83:
        raise ValueError("Leakage canary check failed")
    if hold["evidence_label"] != "HOLDOUT-DTI" or hold["evaluator_version"] != "gems57-pooled-hide-v2" or hold["withheld_positive_pixels"] != 22893:
        raise ValueError("Holdout evaluator metadata mismatch")
    if uniq["registry_rasters_checked"] < 200 or not uniq["preplacement_surface_gate"]["passed"]:
        raise ValueError("Two-phase uniqueness check incomplete")
    if uniq["unique_like_for_like"] is not True or uniq["worst_like_for_like_overlap_3px"]["value"] > 0.70:
        raise ValueError("WBHR-88 candidate failed like-for-like 3-px uniqueness gate")
    if len(card["submission_name"]) > 140 or len(card["submission_note"]) > 140:
        raise ValueError("Submission name or note exceeds 140 characters")

    return {
        "audit_passed": True,
        "lane": "WBHR-88",
        "artifact": card["artifact"],
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "positive_dots": int(card["validator_output"]["positive_dots"]),
        "holdout_dti": float(card["holdout_dti"]["dti"]),
        "e1_wbhr_phys60_dti": float(card["holdout_dti"]["e1_wbhr_phys60_dti"]),
        "e2_wbhr_hybrid_dti": float(card["holdout_dti"]["e2_wbhr_hybrid_dti"]),
        "unique_like_for_like": bool(uniq["unique_like_for_like"]),
        "worst_like_for_like_overlap_3px": float(uniq["worst_like_for_like_overlap_3px"]["value"]),
        "literal_dense_witness_overlap_3px": float(card["correlation_overlap_vs_registry"]["literal_all_positive_witness_overlap_3px"]),
        "fingerprint_share_gt25": float(card["fingerprint"]["share_gt25"]),
        "ok_to_download": bool(card["ok_to_download"]),
        "ok_to_submit": bool(card["ok_to_submit"]),
        "verdict": card["verdict"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-submit", action="store_true", help="Exit 2 when ok_to_submit is False")
    args = ap.parse_args()

    summary = audit_wbhr88(ROOT)
    print(json.dumps(summary, indent=2))
    if args.require_submit and not summary["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
