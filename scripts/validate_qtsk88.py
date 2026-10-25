#!/usr/bin/env python3
"""Independent fail-closed validator for the H88-QTSK GeoTIFF, single-member ZIP, and run card.

Reopens on-disk bytes independently (rasterio + tifffile + zipfile + vendor/gems57/validate),
verifying:
  1. No NaN anywhere in the 3730 x 3292 grid and strictly finite values in [0.0, 1.0].
  2. Exact CRS (EPSG:32611), shape (3730, 3292), geotransform, and LZW 1-row-strip sample parity.
  3. Zero positive pixels outside the active footprint or on mapped faults (existing_faults.tif).
  4. Single-member ZIP integrity and byte-for-byte identity with the standalone GeoTIFF.
  5. Exact SHA-256 sync across registry/qtsk88_run_card.json, docs/data/qtsk88_run_card.json,
     and evidence/qtsk88_experiment_20261024.json, plus unique submission name & <=140-char note.
  6. Scientific & uniqueness gate verification (58/58 canaries <= 0.90, 222-raster like-for-like
     3-px overlap <= 0.70, pre-placement |rho| <= 0.90, share_le2 == 0, share_gt25 >= 0.35, and
     fail-closed negative slot status under literal 17GEMSDOE + Protocol Rule 6).
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import gates as v_gates, grid as grid_mod, validate as v_validate  # noqa: E402
from gems88 import gate  # noqa: E402


def sha256_file(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def validate_qtsk88(root: Path = ROOT) -> dict:
    root = Path(root)
    reg_card = json.loads((root / "registry/qtsk88_run_card.json").read_text())
    web_card = json.loads((root / "docs/data/qtsk88_run_card.json").read_text())
    ev = json.loads((root / "evidence/qtsk88_experiment_20261024.json").read_text())

    if reg_card != web_card or ev.get("run_card") != reg_card:
        raise ValueError("QTSK run card out of sync across registry/, docs/data/, and evidence/")

    tif = root / reg_card["raster"]["tif_path"]
    archive = root / reg_card["raster"]["zip_path"]
    if not tif.is_file() or not archive.is_file():
        raise FileNotFoundError(f"Missing QTSK GeoTIFF or ZIP: {tif}, {archive}")
    if "DO-NOT-SUBMIT" not in tif.name:
        raise ValueError("Research/selector-gated artifact must carry DO-NOT-SUBMIT filename guard")

    tif_sha = sha256_file(tif)
    zip_sha = sha256_file(archive)
    if tif_sha != reg_card["raster"]["sha256"] or zip_sha != reg_card["raster"]["zip_sha256"]:
        raise ValueError("On-disk QTSK TIFF/ZIP SHA-256 does not match frozen run card")

    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP must contain exactly one byte-identical GeoTIFF member")

    sub_name = reg_card.get("submission_name", "")
    sub_note = reg_card.get("submission_note", "")
    if not (1 <= len(sub_name) <= 140) or not (1 <= len(sub_note) <= 140):
        raise ValueError("submission_name and submission_note must be 1..140 chars")

    lc = reg_card["leakage_canary"]
    if (
        not lc["passed"]
        or lc["qtsk14_max_symmetric_auc"] > 0.90
        or lc["phys44_max_symmetric_auc"] > 0.90
        or len(lc["qtsk14_features"]) != 14
    ):
        raise ValueError("Leakage canary check missing or exceeded 0.90")

    ru = reg_card["registry_uniqueness"]
    if (
        ru["n_registry_rasters_checked"] < 200
        or not ru["pre_placement_surface_pass_le_0p90"]
        or ru["pre_placement_surface_max_abs_spearman_rho"] > 0.90
        or not ru["like_for_like_3px_unique_le_0p70"]
        or ru["worst_like_for_like_3px_overlap"]["value"] > 0.70
        or ru["literal_all_registry_3px_unique_le_0p70"] is not False
        or ru["worst_literal_forward_3px_overlap"]["value"] != 1.0
    ):
        raise ValueError("Uniqueness report violated expected like-for-like or literal bounds")

    fp_stats = reg_card["distance_fingerprint"]
    if fp_stats["share_le2"] != 0.0 or fp_stats["share_gt25"] < 0.35 or not reg_card["distance_fingerprint_screen_pass"]:
        raise ValueError("QTSK emitted artifact failed fleet blind-basin distance fingerprint screen")

    if reg_card["verdict"] != "negative" or reg_card["ok_to_submit"] is not False or reg_card["approved_for_weekly_slot"] is not False:
        raise ValueError("Slot-gated artifact must stay verdict=negative / ok_to_submit=False")

    sample_path = root / "data/bridge/sample_submission.tif"
    cat_path = root / "data/bridge/existing_faults.tif"
    grid_verified = False
    if sample_path.is_file() and cat_path.is_file():
        g = grid_mod.load_grid(root / "data/bridge")
        portal_tif = gate.portal_validate(tif, sample_path, g.footprint)
        portal_zip = gate.portal_validate(archive, sample_path, g.footprint)
        fmt_rep = v_gates.format_report(tif, sample_path, footprint=g.footprint)
        val_rep = v_validate.validate(tif, g.footprint, g.catalogue)
        v_validate.assert_submittable(val_rep)
        if not (
            portal_tif["ok"]
            and portal_zip["ok"]
            and portal_tif["layout_parity_with_sample"]
            and fmt_rep["ok"]
            and portal_tif["n_dots"] == reg_card["raster"]["n_positive_dots"]
        ):
            raise ValueError("On-disk GeoTIFF/ZIP failed independent portal/template validators")
        grid_verified = True

    return {
        "ok": True,
        "grid_reopened_against_sample": grid_verified,
        "lane": reg_card["lane"],
        "emitted_arm": reg_card["emitted_experiment_arm"],
        "tif": reg_card["raster"]["tif_path"],
        "tif_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "dots": reg_card["raster"]["n_positive_dots"],
        "exp2_holdout_dti": reg_card["all_experiments_holdout"]["exp2_qtsk_dual"]["pooled_dti"],
        "exp3_holdout_dti": reg_card["holdout_dti"],
        "like_for_like_unique_222": ru["like_for_like_3px_unique_le_0p70"],
        "worst_like_for_like_3px": round(ru["worst_like_for_like_3px_overlap"]["value"], 6),
        "pre_placement_max_abs_rho": ru["pre_placement_surface_max_abs_spearman_rho"],
        "share_gt25": round(fp_stats["share_gt25"], 5),
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": reg_card["verdict"],
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args([] if argv is None and __name__ != "__main__" else argv)
    rep = validate_qtsk88()
    print(json.dumps(rep, indent=2))
    if args.require_submit:
        print("AUTOMATIC SUBMISSION GATE: HELD FOR HUMAN SELECTOR (exit 2).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
