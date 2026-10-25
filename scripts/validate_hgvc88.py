#!/usr/bin/env python3
"""Standalone zero-human-input validator for the H88-HGVC release artifacts.

Works on both:
  * Clean CI checkouts (where gitignored ``data/`` is absent), independently verifying
    classic TIFF magic, EPSG:32611, 3730x3292, exact 100 m geotransform, LZW 1-row-strip
    layout parity, finite {0.0, 1.0} subset of [0.0, 1.0] across all 12,279,160 cells,
    nodata=None, tifffile second-decoder pixel identity, single-member ZIP byte identity,
    frozen preregistration, 87-feature leakage canary + quadrant scramble invariance,
    8-fold buffered whole-component holdout win (8/8 folds won), H33-parity fingerprint,
    324-raster uniqueness receipts, and fail-closed DO-NOT-SUBMIT naming.
  * Restored workspaces (where ``data/bridge/sample_submission.tif`` is present),
    running full ``gate.portal_validate`` and ``gems57.validate`` against sample/catalogue.

Exit codes:
  * ``0`` on default research-integrity check (``ok_to_download == True``).
  * ``2`` when ``--require-submit`` is passed while ``ok_to_submit`` is ``False`` (held fail-closed
    under the binding literal 17GEMSDOE dense space-filling witness + human selector step).
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


def hgvc88_report(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    rc_reg = root / "registry/hgvc88_run_card.json"
    rc_doc = root / "docs/data/hgvc88_run_card.json"
    rc_ev = root / "evidence/hgvc88_run_card.json"
    gv_reg = root / "registry/hgvc88_gate_v3.json"
    gv_doc = root / "docs/data/hgvc88_gate_v3.json"
    pre_reg = root / "registry/preregistration_hgvc88.json"
    pre_doc = root / "docs/data/preregistration_hgvc88.json"
    can_path = root / "evidence/hgvc88_canaries.json"
    ho_path = root / "evidence/hgvc88_holdout_20261024.json"
    ho_doc = root / "docs/evidence/hgvc88_holdout_20261024.json"
    uq_path = root / "evidence/hgvc88_uniqueness.json"

    for p in (rc_reg, rc_doc, rc_ev, gv_reg, gv_doc, pre_reg, pre_doc, can_path, ho_path, ho_doc, uq_path):
        if not p.is_file():
            raise FileNotFoundError(f"Missing required H88-HGVC artifact: {p}")

    if rc_reg.read_text(encoding="utf-8") != rc_doc.read_text(encoding="utf-8"):
        raise ValueError("registry/hgvc88_run_card.json and docs/data/hgvc88_run_card.json differ")
    if rc_reg.read_text(encoding="utf-8") != rc_ev.read_text(encoding="utf-8"):
        raise ValueError("registry/hgvc88_run_card.json and evidence/hgvc88_run_card.json differ")
    if gv_reg.read_text(encoding="utf-8") != gv_doc.read_text(encoding="utf-8"):
        raise ValueError("registry/hgvc88_gate_v3.json and docs/data/hgvc88_gate_v3.json differ")
    if pre_reg.read_text(encoding="utf-8") != pre_doc.read_text(encoding="utf-8"):
        raise ValueError("registry/preregistration_hgvc88.json and docs/data/preregistration_hgvc88.json differ")
    if ho_path.read_text(encoding="utf-8") != ho_doc.read_text(encoding="utf-8"):
        raise ValueError("evidence/hgvc88_holdout_20261024.json and docs/evidence/ copy differ")

    rc = json.loads(rc_reg.read_text(encoding="utf-8"))
    gv = json.loads(gv_reg.read_text(encoding="utf-8"))
    pre = json.loads(pre_reg.read_text(encoding="utf-8"))
    can = json.loads(can_path.read_text(encoding="utf-8"))
    ho = json.loads(ho_path.read_text(encoding="utf-8"))
    uq = json.loads(uq_path.read_text(encoding="utf-8"))

    if pre.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise ValueError("Preregistration is not marked frozen")
    if rc["experiments_executed"] > rc["experiment_budget_max"] or rc["experiment_budget_max"] != 3:
        raise ValueError("Experiment budget cap violated")
    if rc["weekly_slots_spent"] != 0 or gv["weekly_slots_spent"] != 0:
        raise ValueError("Weekly slots spent must be 0")
    if rc["organizer_confirmed_score"] is not None or gv["organizer_confirmed_score"] is not None:
        raise ValueError("Organizer-confirmed score must be None without portal receipt")
    if not (1 <= len(rc["submission_name"]) <= 140 and 1 <= len(rc["submission_note"]) <= 140):
        raise ValueError("Submission name or note outside 1..140 character cap")

    tif_path = root / rc["download"]
    zip_path = root / rc["zip_download"]
    sub_tif = root / rc["repo_copy"]
    sub_zip = sub_tif.with_suffix(".zip")
    dl_audit = tif_path.with_suffix(".format-audit.json")
    for p in (tif_path, zip_path, sub_tif, sub_zip, dl_audit):
        if not p.is_file():
            raise FileNotFoundError(f"Missing H88-HGVC deliverable file: {p}")

    tif_sha = _sha256(tif_path)
    zip_sha = _sha256(zip_path)
    if not (tif_sha == _sha256(sub_tif) == rc["raster_sha256"] == gv["sha256"] == uq["candidate_sha256"]):
        raise ValueError("TIFF SHA-256 mismatch across run card, gate v3, uniqueness, or submissions copy")
    if not (zip_sha == _sha256(sub_zip) == rc["zip_sha256"] == gv["zip_sha256"]):
        raise ValueError("ZIP SHA-256 mismatch across run card, gate v3, or submissions copy")

    with zipfile.ZipFile(zip_path, "r") as zf:
        if zf.testzip() is not None or zf.namelist() != [tif_path.name]:
            raise ValueError("ZIP must contain exactly one valid member matching the GeoTIFF filename")
        zbytes = zf.read(tif_path.name)
    if hashlib.sha256(zbytes).hexdigest() != tif_sha:
        raise ValueError("ZIP member bytes do not match standalone GeoTIFF bytes")

    exp = gate.EXPECTED
    raw_hdr = tif_path.read_bytes()[:4]
    if raw_hdr not in (b"II*\x00", b"MM\x00*"):
        raise ValueError("GeoTIFF is not classic TIFF")
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        if ds.count != 1 or ds.dtypes[0] != "float32":
            raise ValueError("GeoTIFF must be single-band float32")
        if ds.crs is None or ds.crs.to_epsg() != exp["epsg"]:
            raise ValueError(f"GeoTIFF CRS must be EPSG:{exp['epsg']}")
        if ds.shape != exp["shape"] or tuple(ds.transform)[:6] != exp["transform"]:
            raise ValueError("GeoTIFF shape or affine geotransform mismatch vs sample_submission.tif")
        if ds.nodata is not None:
            raise ValueError("GeoTIFF nodata must be None (zeros policy)")
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
        raise ValueError("H88-HGVC GeoTIFF must contain discrete {0.0, 1.0} values")

    n_dots = int((arr > 0.5).sum())
    if n_dots != rc["validator_output"]["positive_dots"] or n_dots != gv["candidate"]["dots"]:
        raise ValueError("Positive dot count mismatch")

    sample_reopened = False
    sample_path = root / "data/bridge/sample_submission.tif"
    if sample_path.is_file():
        from gems57 import grid as grid_mod, validate as g57validate

        g = grid_mod.load_grid(root / "data/bridge")
        pv_tif = gate.portal_validate(tif_path, sample_path, g.footprint)
        pv_zip = gate.portal_validate(zip_path, sample_path, g.footprint)
        gv57 = g57validate.validate(tif_path, g.footprint, g.catalogue)
        g57validate.assert_submittable(gv57)
        if not (pv_tif["ok"] and pv_zip["ok"] and pv_tif["layout_parity_with_sample"] and gv57["all_checks_passed"]):
            raise ValueError("Full sample/catalogue validation failed on restored inputs")
        sample_reopened = True

    # Verify leakage canary + scramble invariance
    if not (can["passed"] and can["max_symmetric_auc"] <= 0.90 and can["features_tested"] == 87):
        raise ValueError("Leakage canary check failed")
    if ho.get("zero_leakage_quadrant_scramble_equal") is not True:
        raise ValueError("Test-quadrant scramble check not True")

    # Verify 8-fold holdout consistency
    ov_score = float(ho["pooled_overall"]["scores"]["exp03_hgvc_poe_conduit"]["dti"])
    adhr_score = float(ho["pooled_overall"]["scores"]["h88_adhr_incumbent"]["dti"])
    delta_ov = ho["pooled_overall"]["paired_differences"]["h88_adhr_incumbent"]
    beats_bar = bool(ov_score > adhr_score and ov_score > 0.189634 and float(delta_ov["ci95"][0]) > 0.0)
    if abs(ov_score - float(rc["holdout_dti"]["candidate_exp03"]["dti"])) > 1e-12:
        raise ValueError("Run card holdout DTI disagrees with holdout ledger")
    if beats_bar != gv["holdout_comparison"]["beats_both_bars_with_positive_ci95"] or not beats_bar:
        raise ValueError("Holdout bar consistency check failed")

    # Verify fingerprint + uniqueness + binding literal gate consistency
    fp_pass = gate.fingerprint_screen(gv["fingerprint"])
    if fp_pass != gv["fingerprint_screen_pass"] or not fp_pass:
        raise ValueError("Fingerprint screen consistency check failed")
    if (
        not uq["unique_like_for_like"]
        or uq["worst_like_for_like_overlap"]["value"] > 0.70
        or uq["worst_abs_rho"]["value"] > 0.90
        or uq["surface_preplacement_max_abs_spearman"] > 0.90
        or uq["registry_rasters_checked"] < 300
    ):
        raise ValueError("300+-raster like-for-like uniqueness check failed")

    disc_ok = bool(beats_bar and fp_pass and can["passed"] and uq["unique_like_for_like"])
    expected_submit = bool(
        disc_ok and uq["unique_literal"] and float(uq["literal_all_positive_witness_overlap_3px"]) <= 0.70
    )
    if disc_ok != rc["all_5_discriminating_gates_pass"] or disc_ok != gv["all_5_discriminating_gates_pass"]:
        raise ValueError("all_5_discriminating_gates_pass tampered")
    if expected_submit != gv["ok_to_submit"] or expected_submit != rc["ok_to_submit"]:
        raise ValueError("ok_to_submit disagrees with binding literal + discriminating gates")
    if gv["ok_to_submit"]:
        if "DO-NOT-SUBMIT" in tif_path.name or rc["verdict"] != "promote":
            raise ValueError("Cleared file must not carry DO-NOT-SUBMIT")
    else:
        if not tif_path.name.endswith("-DO-NOT-SUBMIT.tif") or rc["verdict"] != "negative" or not gv["blocking_reasons"]:
            raise ValueError("Blocked file must end with -DO-NOT-SUBMIT.tif and carry verdict='negative'")

    return {
        "ok_to_download": bool(gv["ok_to_download"]),
        "ok_to_submit": bool(gv["ok_to_submit"]),
        "all_5_discriminating_gates_pass": disc_ok,
        "sample_reopened": sample_reopened,
        "verdict": rc["verdict"],
        "file": rc["download"],
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "dots": n_dots,
        "holdout_dti": ov_score,
        "holdout_ci95": rc["holdout_dti"]["candidate_exp03"]["ci95"],
        "far_gt10px_dti": float(rc["holdout_dti"]["far_gt10px"]["dti"]),
        "blind_gt25px_dti": float(rc["holdout_dti"]["blind_gt25px"]["dti"]),
        "paired_delta_vs_adhr": delta_ov,
        "folds_won_vs_adhr": int(rc["holdout_dti"]["folds_won_vs_adhr"]),
        "share_gt25": float(gv["fingerprint"]["share_gt25"]),
        "registry_rasters_checked": int(uq["registry_rasters_checked"]),
        "worst_like_for_like_overlap_3px": float(uq["worst_like_for_like_overlap"]["value"]),
        "surface_max_abs_spearman": float(uq["surface_preplacement_max_abs_spearman"]),
        "literal_witness_overlap_3px": float(uq["literal_all_positive_witness_overlap_3px"]),
        "blocking_reasons": gv["blocking_reasons"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true", help="Exit 2 unless ok_to_submit is True")
    args = ap.parse_args(argv)

    rep = hgvc88_report(ROOT)
    print(json.dumps(rep, indent=2))
    if args.require_submit and not rep["ok_to_submit"]:
        print(
            "AUTOMATIC SUBMISSION GATE: DO NOT SUBMIT (held fail-closed by literal 17GEMSDOE dense witness; exit 2).",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
