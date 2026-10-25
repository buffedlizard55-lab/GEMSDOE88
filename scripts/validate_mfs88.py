#!/usr/bin/env python3
"""Fail-closed re-validation of the H88-MFS research deliverable vs its run card.

No human inspector: registry card == docs mirror; ok_to_submit consistent with
ALL preregistered gates (canary, paired holdout lane pass, beats repo holdout
best, LITERAL uniqueness, fingerprint, format); TIFF/ZIP SHA-256 match; ZIP
holds exactly the TIFF; single-band float32 on the exact sample grid, nodata
unset, finite [0,1] everywhere, 0 outside footprint and on catalogue; dot
count equals card; DO-NOT-SUBMIT in filename iff ok_to_submit is False;
name/note <= 140 chars.  Exit 0 = card honestly describes the bytes;
--require-submit exits 2 while ok_to_submit is False.
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
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from gems57.grid import load_grid  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"MFS88 VALIDATION FAILED: {msg}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args()
    card = json.loads((ROOT / "registry/mfs88_run_card.json").read_text())
    mirror = json.loads((ROOT / "docs/data/mfs88_run_card.json").read_text())
    require(card == mirror, "docs/data mirror differs from registry card")
    gates = {
        "canary": bool(card["leakage_canary"]["passed"]),
        "lane_pass": bool(card["holdout"]["exp2_lane_pass"]),
        "beats_repo_best": bool(card["holdout"]["beats_repo_best"]),
        "literal_uniqueness": bool(card["uniqueness"]["literal_pass"]),
        "corrected_uniqueness": bool(card["uniqueness"]["corrected_pass"]),
        "fingerprint": bool(card["fingerprint_pass"]),
        "format": bool(card["validator"]["all_checks_passed"]),
    }
    expected = bool(gates["canary"] and gates["lane_pass"] and gates["beats_repo_best"]
                    and gates["literal_uniqueness"] and gates["fingerprint"] and gates["format"])
    require(card["ok_to_submit"] is expected, f"ok_to_submit inconsistent with gates {gates}")
    require(card["verdict"] == ("promote" if expected else "negative"), "verdict inconsistent")
    require(card["ok_to_download"] is True and gates["format"], "validator/download")
    require(card["weekly_slots_used"] == 0 and card["organizer_confirmed"] is None, "slots/receipt")
    require(card["preflight_generation_guard"]["decision"] == "DUPLICATE_STOP", "preflight record")
    require(0 < len(card["submission_name"]) <= 140, "name length")
    require(card["note_chars"] == len(card["submission_note"]) and 0 < card["note_chars"] <= 140,
            "note length")

    tif = ROOT / "docs/downloads" / card["submission_file"]
    zf = tif.with_suffix(".zip")
    require(tif.exists() and zf.exists(), "deliverable files missing")
    require(("DO-NOT-SUBMIT" in tif.name) is (not card["ok_to_submit"]),
            "DO-NOT-SUBMIT suffix inconsistent with ok_to_submit")
    require(sha256(tif) == card["sha256_tif"], "TIFF sha256 mismatch")
    require(sha256(zf) == card["sha256_zip"], "ZIP sha256 mismatch")
    with zipfile.ZipFile(zf) as z:
        require(z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes(), "ZIP content")

    shared_format = validate_artifact(tif, ROOT / "data/bridge/sample_submission.tif")
    require(shared_format["ok"], "shared saved-file format audit failed")
    grid = load_grid(ROOT / "data/bridge")
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as s:
        ref = (s.crs, s.width, s.height, s.transform)
    with rasterio.open(tif) as d:
        require(d.count == 1 and d.dtypes[0] == "float32", "band/dtype")
        require((d.crs, d.width, d.height, d.transform) == ref, "grid mismatch vs sample")
        require(d.nodata is None, "nodata must be None (zeros mode)")
        arr = d.read(1)
    require(bool(np.isfinite(arr).all()), "non-finite values (portal [0,1] check would fail)")
    require(float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0, "values outside [0,1]")
    require(set(np.unique(arr).tolist()) <= {0.0, 1.0}, "expected binary dotted emission")
    fp = grid.footprint
    require(float(np.abs(arr[~fp]).max(initial=0.0)) == 0.0, "non-zero outside footprint")
    require(float(arr[grid.catalogue].max(initial=0.0)) == 0.0, "non-zero on catalogue")
    n_dots = int((arr > 0).sum())
    require(n_dots == card["fingerprint"]["dots"], f"dot count {n_dots} != card")
    print(json.dumps({
        "ok": True, "file": tif.name, "sha256": card["sha256_tif"], "dots": n_dots,
        "ok_to_download": card["ok_to_download"], "ok_to_submit": card["ok_to_submit"],
        "verdict": card["verdict"], "gates": gates, "stop_reasons": card["stop_reasons"],
        "shared_local_format_audit": shared_format,
    }, indent=1))
    if args.require_submit and not card["ok_to_submit"]:
        print("NOT CLEARED FOR A COMPETITION SLOT", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
