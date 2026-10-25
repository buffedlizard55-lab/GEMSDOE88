#!/usr/bin/env python3
"""Independent saved-byte validator for the archived H88-MMRX research GeoTIFF.

Re-opens the archived TIFF and ZIP under ``submissions/``, verifies mirror
parity between ``registry/mmrx88_run_card.json`` and
``docs/data/mmrx88_run_card.json``, checks single-band float32 ``[0, 1]``
finiteness, grid parity, ``DO-NOT-SUBMIT`` ZIP member packaging, and dense-witness
/ HGVC overlap facts.

Exit codes:
  0  negative research-archive integrity check passed (NOT portal clearance)
  1  corrupt bytes, mirror drift, or format/metadata mismatch
  2  ``--require-submit`` requested on a negative DO-NOT-SUBMIT archive
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from gems57 import grid as grid_mod  # noqa: E402
from gems57.uniqueness import dot_overlap  # noqa: E402
from scripts.audit_submissions_dir import verify_zip_package  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402

CARD = ROOT / "registry/mmrx88_run_card.json"
WEB_CARD = ROOT / "docs/data/mmrx88_run_card.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args()

    problems: list[str] = []
    if not CARD.is_file() or not WEB_CARD.is_file():
        print(json.dumps({"ok": False, "problems": ["missing mmrx88 run card mirror"]}, indent=2))
        return 1

    card = json.loads(CARD.read_text(encoding="utf-8"))
    web_card = json.loads(WEB_CARD.read_text(encoding="utf-8"))
    if card != web_card:
        problems.append("docs/data/mmrx88_run_card.json differs from registry/mmrx88_run_card.json")

    if card.get("download") is not None or card.get("zip_download") is not None:
        problems.append("mmrx88 run card must not advertise nonexistent docs/downloads paths")
    if card.get("ok_to_download") is not False:
        problems.append("mmrx88 ok_to_download must be false (archived only in submissions/)")
    if card.get("ok_to_submit") is not False or card.get("verdict") != "negative":
        problems.append("mmrx88 run card must remain negative and ok_to_submit=false")
    if card.get("weekly_slots_used_by_agent") != 0 or card.get("organizer_confirmed_score") is not None:
        problems.append("mmrx88 slot/receipt fields invalid")

    tif = ROOT / card["repo_copy"]
    zip_path = ROOT / card["repo_zip_copy"]
    if not tif.is_file() or not zip_path.is_file():
        problems.append("missing archived mmrx88 TIFF or ZIP in submissions/")
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1

    if "DO-NOT-SUBMIT" not in tif.name or "DO-NOT-SUBMIT" not in zip_path.name:
        problems.append("archived mmrx88 filenames lack DO-NOT-SUBMIT marker")
    if sha256_file(tif) != card["raster_sha256"]:
        problems.append("TIFF SHA-256 differs from run card")
    if sha256_file(zip_path) != card["zip_sha256"]:
        problems.append("ZIP SHA-256 differs from run card")
    problems.extend(verify_zip_package(zip_path, tif))

    sample = ROOT / "data/bridge/sample_submission.tif"
    if not sample.is_file():
        problems.append("missing validation input: data/bridge/sample_submission.tif")
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1
    v_out = validate_artifact(tif, sample)
    if not v_out["ok"]:
        problems.append(f"validate_artifact failed: {v_out}")

    grid = grid_mod.load_grid(ROOT / "data/bridge")
    with rasterio.open(tif) as src:
        a = src.read(1)
        if src.nodata is not None:
            problems.append(f"nodata declared ({src.nodata}); expected None")
    try:
        import tifffile
        b = tifffile.imread(tif)
        if not np.array_equal(np.nan_to_num(b, nan=-1.0), np.nan_to_num(a, nan=-1.0)):
            problems.append("tifffile decoder disagrees with rasterio")
    except ImportError:
        pass

    n_dots = int((a > 0).sum())
    if n_dots != card["production"]["n_dots"]:
        problems.append(f"dot count {n_dots} != {card['production']['n_dots']}")
    if int((a[grid.catalogue] > 0).sum()) != 0:
        problems.append("positive pixels on mapped catalogue")
    if int((a[~grid.footprint] > 0).sum()) != 0:
        problems.append("positive pixels outside footprint")

    dense_path = ROOT / "data/registry/dense_17gemdoe.tif"
    dense_ov = None
    if dense_path.is_file():
        with rasterio.open(dense_path) as src:
            dense_ov = float(dot_overlap(a, src.read(1), radius_px=3.0))
        if abs(dense_ov - 1.0) > 1e-9:
            problems.append(f"expected literal dense overlap 1.0, got {dense_ov}")

    if not (0 < len(card["submission_name"]) <= 140 and 0 < len(card["submission_note"]) <= 140):
        problems.append("submission_name or submission_note violates <=140-char cap")

    report = {
        "lane": card["lane"],
        "repo_copy": card["repo_copy"],
        "repo_zip_copy": card["repo_zip_copy"],
        "sha256": card["raster_sha256"],
        "zip_sha256": card["zip_sha256"],
        "n_dots": n_dots,
        "min": float(a.min()),
        "max": float(a.max()),
        "n_nan": int(np.isnan(a).sum()),
        "dense_witness_overlap_3px": dense_ov,
        "format_ok": not problems,
        "ok_to_download_repo_archive_for_research_only": not problems,
        "ok_to_submit": False,
        "problems": problems,
        "note": "Local format/identity audit of negative research archive only; NOT organizer acceptance.",
    }
    print(json.dumps(report, indent=2))
    if problems:
        return 1
    if args.require_submit:
        print("DO NOT SUBMIT: H88-MMRX verdict is negative (0/8 folds vs BPWD; 0.7976 > 0.70 overlap vs HGVC; literal 1.0 vs dense witness).")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
