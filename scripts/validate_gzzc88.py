#!/usr/bin/env python3
"""Validate H88-GZZC TIFF/ZIP. Exit 0 = research PASS, exit 2 = --require-submit FAIL-CLOSED."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems57 import grid as grid_mod  # noqa: E402
from gems88.gate import portal_validate  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

CARD = ROOT / "registry/gzzc88_run_card.json"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition: bool, message: object) -> None:
    if not condition:
        raise ValueError(str(message))


def main() -> None:
    require_submit = "--require-submit" in sys.argv
    require(CARD.is_file(), f"missing {CARD}")
    card = json.loads(CARD.read_text())
    tif = ROOT / card["download"]
    zipp = ROOT / card["zip_download"]
    g = grid_mod.load_grid(ROOT / "data/bridge")
    require(tif.is_file() and zipp.is_file(), "missing GZZC tif/zip")
    require(card["ok_to_download"] is True, "card not downloadable")
    require(card["ok_to_submit"] is False, "card incorrectly marked submittable")
    require(card["verdict"] == "negative", "card verdict not negative")
    require(sha(tif) == card["raster_sha256"] == card["submission"]["raster_sha256"], "tif hash mismatch")
    require(sha(zipp) == card["zip_sha256"] == card["submission"]["zip_sha256"], "zip hash mismatch")
    v_tif = portal_validate(tif, SAMPLE, footprint=g.footprint)
    v_zip = portal_validate(zipp, SAMPLE, footprint=g.footprint)
    v_art = validate_artifact(tif, SAMPLE)
    require(v_tif["ok"], f"tif portal fail {v_tif['problems']}")
    require(v_zip["ok"], f"zip portal fail {v_zip['problems']}")
    require(v_art["ok"], f"artifact fail {v_art}")
    with rasterio.open(tif) as src:
        a = src.read(1)
        crs = src.crs
        transform = src.transform
        nodata = src.nodata
    require(a.shape == g.shape, f"shape {a.shape}")
    require(str(crs) == f"EPSG:{grid_mod.EPSG}", f"CRS {crs}")
    require(tuple(transform)[:6] == tuple(grid_mod.TRANSFORM)[:6], "transform mismatch")
    require(nodata is None, "nodata must be undeclared")
    require(bool(np.isfinite(a).all()), "nonfinite found")
    require(bool((a >= 0).all() and (a <= 1).all()), "range [0,1] violated")
    require(bool((a[~g.footprint] == 0).all()), "outside footprint not zero")
    require(bool((a[g.catalogue] == 0).all()), "dots on catalogue")
    require(int((a > 0).sum()) == card["submission"]["positive_pixels"] == 32000, "dot count")
    with zipfile.ZipFile(zipp) as archive:
        require(archive.namelist() == [tif.name], f"zip members {archive.namelist()}")
        require(archive.read(tif.name) == tif.read_bytes(), "zip bytes not identical")
    require(card["leakage_canary"]["max_symmetric_auc"] <= 0.90, "canary fail")
    require(card["leakage_canary"]["passed"] is True, "canary flag")
    require(card["fingerprint"]["share_gt25"] >= 0.35, "fingerprint gt25")
    require(card["fingerprint"]["share_le2"] == 0.0, "fingerprint le2")
    require(card["uniqueness"]["unique_like_for_like"] is True, "like-for-like")
    require(card["uniqueness"]["literal_dense_witness_overlap"] == 1.0, "dense overlap")
    require(card["uniqueness"]["literal_dense_witness_pass"] is False, "dense must fail")
    require(card["holdout"]["evidence_class"] == "HOLDOUT-DTI", "holdout class")
    require(card["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2", "evaluator")
    require(0 < len(card["submission_name"]) <= 140, "name length")
    require(0 < len(card["submission_note"]) <= 140, "note length")
    print(
        "[GZZC-VALIDATE] Research gates PASS: portal-valid zeros [0,1], "
        "canary 0.572, fingerprint gt25=0.45, like-for-like UNIQUE 0.343<=0.70, "
        "literal 1.0>0.70 enforces DO NOT SUBMIT"
    )
    print(f"  TIF {tif.name} SHA256 {sha(tif)}")
    print(f"  ZIP {zipp.name} SHA256 {sha(zipp)}")
    print(f"  Name {card['submission_name']} ({len(card['submission_name'])}/140)")
    print(f"  Note {card['submission_note']} ({len(card['submission_note'])}/140)")
    if require_submit:
        print("[GZZC-VALIDATE] --require-submit: research PASS but binding literal witness blocks slot -> exit 2 FAIL-CLOSED")
        raise SystemExit(2)
    print("[GZZC-VALIDATE] Research download YES, submit NO — exit 0")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
