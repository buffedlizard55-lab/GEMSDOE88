#!/usr/bin/env python3
"""Independent fail-closed validator for the H88-VESS research GeoTIFF.

Reopens on-disk bytes (rasterio via vendor validate + gate portal parity +
zipfile) and re-checks the frozen run card.  Exit 0 = valid research
download; `--require-submit` exits 2 because the candidate is a lane
duplicate (3 px overlap 0.8455 vs H88-TDKL > 0.70) and fails the literal
dense-witness rule, so it must never be uploaded.
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

from gems57 import grid as grid_mod, validate as v_validate  # noqa: E402
from gems88 import gate  # noqa: E402


def sha256_file(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def validate_vess88(root: Path = ROOT) -> dict:
    root = Path(root)
    reg = json.loads((root / "registry/vess88_run_card.json").read_text())
    web = json.loads((root / "docs/data/vess88_run_card.json").read_text())
    if reg != web:
        raise ValueError("VESS run card out of sync registry/ vs docs/data/")
    if reg["verdict"] != "negative" or reg["ok_to_submit"] is not False or reg["ok_to_download"] is not True:
        raise ValueError("VESS artifact must stay verdict=negative / ok_to_submit=False / ok_to_download=True")

    tif = root / reg["submission"]["file"]
    archive = root / reg["submission"]["zip_file"]
    if "DO-NOT-SUBMIT" not in tif.name:
        raise ValueError("selector-gated artifact must carry DO-NOT-SUBMIT filename guard")
    if sha256_file(tif) != reg["raster_sha256"] or sha256_file(archive) != reg["zip_sha256"]:
        raise ValueError("on-disk SHA-256 does not match frozen run card")
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP must contain exactly one byte-identical GeoTIFF member")

    name, note = reg["submission"]["submission_name"], reg["submission"]["submission_note"]
    if not (1 <= len(name) <= 140) or not (1 <= len(note) <= 140):
        raise ValueError("submission name/note must be 1..140 chars")

    canary = reg["leakage_canary"]
    if not canary["passed"] or canary["max_symmetric_auc"] > 0.90 or canary["features_tested"] != 68:
        raise ValueError("leakage canary missing/failed")

    hd = reg["holdout_dti"]
    if hd["evidence_class"] != "HOLDOUT-DTI" or hd["evaluator_version"] != "gems57-pooled-hide-v2":
        raise ValueError("holdout evidence mislabelled")
    paired = hd["paired_delta_vs_adhr_incumbent"]
    if not (hd["overall"]["dti"] > 0.196237 and paired["delta"] > 0 and paired["ci95"][0] > 0):
        raise ValueError("holdout bar/paired-delta evidence inconsistent with run card")

    corr = reg["correlation_overlap_vs_registry"]
    worst_lfl = corr["final_worst_like_for_like_overlap_3px"]["value"]
    if not (corr["surface_preplacement_max_abs_spearman"] <= 0.90 and worst_lfl > 0.70 and corr["unique_literal"] is False):
        raise ValueError("uniqueness evidence inconsistent (expected surface pass, dot duplicate, literal fail)")

    grid_verified = False
    sample = root / "data/bridge/sample_submission.tif"
    if sample.is_file():
        g = grid_mod.load_grid(root / "data/bridge")
        portal = gate.portal_validate(tif, sample, g.footprint)
        val = v_validate.validate(tif, g.footprint, g.catalogue)
        v_validate.assert_submittable(val)
        if not (portal["ok"] and val["all_checks_passed"] and portal["n_dots"] == reg["submission"]["positive_pixels"]):
            raise ValueError("on-disk GeoTIFF failed independent portal/template validators")
        if not (val["checks"]["no_nan_anywhere"] and val["checks"]["range_0_1_guaranteed"]):
            raise ValueError("range [0,1] / no-NaN guarantee failed (portal range-error guard)")
        grid_verified = True

    return {"ok": True, "grid_reopened_against_sample": grid_verified, "lane": reg["lane"],
            "tif": reg["submission"]["file"], "tif_sha256": reg["raster_sha256"],
            "zip_sha256": reg["zip_sha256"], "dots": reg["submission"]["positive_pixels"],
            "holdout_dti": reg["holdout_dti"]["overall"]["dti"],
            "holdout_ci95": reg["holdout_dti"]["overall"]["ci95"],
            "paired_delta_vs_adhr": paired, "worst_like_for_like_overlap_3px": worst_lfl,
            "surface_max_abs_rho": corr["surface_preplacement_max_abs_spearman"],
            "ok_to_download": True, "ok_to_submit": False, "verdict": reg["verdict"]}


def main() -> int:
    rep = validate_vess88()
    print(json.dumps(rep, indent=2))
    if "--require-submit" in sys.argv:
        print("AUTOMATIC SUBMISSION GATE: DO NOT SUBMIT (lane duplicate + literal witness; exit 2).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
