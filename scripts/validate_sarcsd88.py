#!/usr/bin/env python3
"""Fail-closed standalone validator for the H88-SAR-CSD release artifacts.

Works on both:
- Clean CI checkouts (where gitignored ``data/`` is absent), verifying exact pinned
  EPSG:32611 / 3730x3292 / 100 m geotransform / LZW 1-row-strip layout, finite [0, 1]
  {0, 1} values, single-member ZIP byte parity, tifffile second-decoder agreement,
  preregistration, 88-feature leakage canary, 8-fold holdout receipts, 264-raster
  uniqueness receipt, fingerprint screen, and fail-closed DO-NOT-SUBMIT naming.
- Restored workspaces (where ``data/bridge/sample_submission.tif`` is present),
  running full sample-parity ``gate.portal_validate`` and ``gems57.validate``.

Usage:
  .venv/bin/python scripts/validate_sarcsd88.py
  .venv/bin/python scripts/validate_sarcsd88.py --require-submit   # exits 2 when negative
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems88 import gate  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sarcsd88_report(root: Path = ROOT) -> dict[str, Any]:
    rc_reg = root / "registry/sarcsd88_run_card.json"
    rc_doc = root / "docs/data/sarcsd88_run_card.json"
    rc_ev = root / "evidence/sarcsd88_run_card.json"
    gv_reg = root / "registry/sarcsd88_gate_v3.json"
    gv_doc = root / "docs/data/sarcsd88_gate_v3.json"
    pre_path = root / "registry/preregistration_sarcsd88.json"
    can_path = root / "evidence/sarcsd88_canaries.json"
    ho_path = root / "evidence/sarcsd88_holdout.json"
    uq_path = root / "evidence/sarcsd88_uniqueness.json"

    for p in (rc_reg, rc_doc, rc_ev, gv_reg, gv_doc, pre_path, can_path, ho_path, uq_path):
        if not p.is_file():
            raise FileNotFoundError(f"Missing required SAR-CSD artifact: {p}")

    if rc_reg.read_text(encoding="utf-8") != rc_doc.read_text(encoding="utf-8"):
        raise ValueError("registry/sarcsd88_run_card.json and docs/data/sarcsd88_run_card.json differ")
    if rc_reg.read_text(encoding="utf-8") != rc_ev.read_text(encoding="utf-8"):
        raise ValueError("registry/sarcsd88_run_card.json and evidence/sarcsd88_run_card.json differ")
    if gv_reg.read_text(encoding="utf-8") != gv_doc.read_text(encoding="utf-8"):
        raise ValueError("registry/sarcsd88_gate_v3.json and docs/data/sarcsd88_gate_v3.json differ")

    rc = json.loads(rc_reg.read_text(encoding="utf-8"))
    gv = json.loads(gv_reg.read_text(encoding="utf-8"))
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    can = json.loads(can_path.read_text(encoding="utf-8"))
    ho = json.loads(ho_path.read_text(encoding="utf-8"))
    uq = json.loads(uq_path.read_text(encoding="utf-8"))

    if pre.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise ValueError("Preregistration is not marked frozen")
    if rc["experiments_run"] > rc["experiment_budget_max"] or rc["experiment_budget_max"] != 3:
        raise ValueError("Experiment budget cap violated")
    if rc["weekly_slots_spent"] != 0 or gv["weekly_slots_spent"] != 0:
        raise ValueError("Weekly slots spent must be 0")
    if rc["organizer_confirmed_score"] is not None or gv["organizer_confirmed_score"] is not None:
        raise ValueError("Organizer-confirmed score must be None without portal receipt")
    if len(rc["submission_name"]) > 140 or not (0 < len(rc["submission_note"]) <= 140):
        raise ValueError("Submission name or note exceeds 140-char limit")

    tif_path = root / rc["download"]
    zip_path = root / rc["zip_download"]
    sub_tif = root / rc["repo_copy"]
    if not (tif_path.is_file() and zip_path.is_file() and sub_tif.is_file()):
        raise FileNotFoundError("Missing SAR-CSD .tif or .zip deliverable")

    tif_sha = _sha256(tif_path)
    zip_sha = _sha256(zip_path)
    sub_sha = _sha256(sub_tif)
    if not (tif_sha == sub_sha == rc["raster_sha256"] == gv["sha256"]):
        raise ValueError("TIFF SHA-256 mismatch across run card, gate v3, or submissions copy")
    if not (zip_sha == rc["zip_sha256"] == gv["zip_sha256"]):
        raise ValueError("ZIP SHA-256 mismatch across run card and gate v3")

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        if names != [tif_path.name]:
            raise ValueError(f"ZIP must hold exactly [{tif_path.name}], got {names}")
        zbytes = zf.read(tif_path.name)
    if hashlib.sha256(zbytes).hexdigest() != tif_sha:
        raise ValueError("ZIP member bytes do not match standalone GeoTIFF bytes")

    exp = gate.EXPECTED
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        if ds.count != 1 or ds.dtypes[0] != "float32":
            raise ValueError("GeoTIFF must be single-band float32")
        if ds.crs is None or ds.crs.to_epsg() != exp["epsg"]:
            raise ValueError(f"GeoTIFF CRS must be EPSG:{exp['epsg']}")
        if ds.shape != exp["shape"] or tuple(ds.transform)[:6] != exp["transform"]:
            raise ValueError("GeoTIFF shape or affine transform mismatch vs sample_submission.tif")
        if ds.nodata is not None:
            raise ValueError("GeoTIFF nodata must be None")
        if str(ds.profile.get("compress", "")).lower() != "lzw" or bool(ds.profile.get("tiled", False)):
            raise ValueError("GeoTIFF must match sample LZW non-tiled strip layout")
        if ds.block_shapes[0] != (1, exp["shape"][1]):
            raise ValueError("GeoTIFF must use 1-row strips matching sample_submission.tif")

    arr_tiff = tifffile.imread(tif_path)
    if not np.array_equal(arr, arr_tiff):
        raise ValueError("Second decoder (tifffile) disagrees with rasterio")
    if not np.isfinite(arr).all() or not bool(np.all((arr >= 0.0) & (arr <= 1.0))):
        raise ValueError("Portal NaN-strict [0, 1] check failed")
    if not set(np.unique(arr)).issubset({0.0, 1.0}):
        raise ValueError("SAR-CSD GeoTIFF must contain discrete {0.0, 1.0} dots")

    n_dots = int((arr > 0.5).sum())
    if n_dots != rc["validator_output"]["positive_dots"] or n_dots != gv["candidate"]["dots"]:
        raise ValueError("Positive dot count mismatch")

    sample_path = root / "data/bridge/sample_submission.tif"
    if sample_path.is_file():
        from gems57 import grid as grid_mod, validate as g57validate
        g = grid_mod.load_grid(root / "data/bridge")
        pv_tif = gate.portal_validate(tif_path, sample_path, g.footprint)
        pv_zip = gate.portal_validate(zip_path, sample_path, g.footprint)
        gv57 = g57validate.validate(tif_path, g.footprint, g.catalogue)
        if not (pv_tif["ok"] and pv_zip["ok"] and gv57["all_checks_passed"]):
            raise ValueError("Full sample-parity validation failed on restored inputs")

    # Verify leakage canary + holdout + uniqueness + fingerprint consistency
    if not (can["passed"] and can["max_symmetric_auc"] <= 0.90 and can["features_tested"] == 88):
        raise ValueError("Leakage canary check failed")
    if ho.get("zero_leakage_quadrant_scramble_equal") is not True:
        raise ValueError("Test-quadrant scramble check not True")

    e3 = float(ho["scores"]["exp03_sar_csd"]["dti"])
    e2 = float(ho["scores"]["exp02_csd_joint"]["dti"])
    adhr_c = float(ho["scores"]["h88_adhr_incumbent"]["dti"])
    stored_bar = float(ho["stored_adhr_bar"])
    d_e3_lo = float(ho["paired_differences"]["h88_adhr_incumbent"]["ci95"][0])
    fp_pass = gate.fingerprint_screen(gv["fingerprint"])
    beats_bar = bool((e3 > stored_bar) and (e3 > adhr_c) and (d_e3_lo > 0.0) and fp_pass)

    if fp_pass != gv["fingerprint_screen_pass"] or not fp_pass:
        raise ValueError("Fingerprint screen consistency check failed")
    if not uq["unique_like_for_like"] or uq["worst_like_for_like_overlap"]["value"] > 0.70 or uq["worst_abs_rho"]["value"] > 0.90:
        raise ValueError("Like-for-like uniqueness check failed")
    if beats_bar != gv["holdout_comparison"]["beats_both_bars_with_positive_ci95"]:
        raise ValueError("Holdout bar boolean mismatch")
    if gv["ok_to_submit"] != beats_bar or rc["gate_v3_ok_to_submit"] != gv["ok_to_submit"]:
        raise ValueError("Tampered gate_v3 verdict: ok_to_submit disagrees with holdout/uniqueness/fingerprint")
    if gv["ok_to_submit"]:
        if "DO-NOT-SUBMIT" in tif_path.name or rc["verdict"] != "promote":
            raise ValueError("Cleared file must not carry DO-NOT-SUBMIT")
    else:
        if not tif_path.name.endswith("-DO-NOT-SUBMIT.tif") or rc["verdict"] != "negative" or not gv["blocking_reasons"]:
            raise ValueError("Blocked file must end with -DO-NOT-SUBMIT.tif and have verdict='negative'")

    return {
        "ok_to_download": bool(gv["ok_to_download"]),
        "ok_to_submit": bool(gv["ok_to_submit"]),
        "verdict": rc["verdict"],
        "file": rc["download"],
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "dots": n_dots,
        "exp02_holdout_dti": e2,
        "exp03_holdout_dti": e3,
        "adhr_holdout_dti": adhr_c,
        "share_gt25": float(gv["fingerprint"]["share_gt25"]),
        "worst_like_for_like_overlap_3px": float(uq["worst_like_for_like_overlap"]["value"]),
        "max_abs_spearman": float(uq["worst_abs_rho"]["value"]),
        "blocking_reasons": gv["blocking_reasons"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true", help="Exit 2 unless ok_to_submit is True")
    args = ap.parse_args(argv)

    rep = sarcsd88_report(ROOT)
    print(json.dumps(rep, indent=2))
    if args.require_submit and not rep["ok_to_submit"]:
        print("DO NOT SUBMIT: SAR-CSD failed the frozen holdout bar -> exiting 2.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
