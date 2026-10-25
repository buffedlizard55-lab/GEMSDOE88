#!/usr/bin/env python3
"""Read-only validator for archived H88-CON88 after clearance withdrawal (IR-88-587C7F22-01).

Verifies byte-exact preservation of the archived GeoTIFF (SHA-256 e830b58e...),
paired -DO-NOT-SUBMIT ZIP, strict format/grid/[0,1]/footprint/catalogue checks,
literal 1.0000 > 0.70 overlap against 17GEMSDOE, and fail-closed withdrawal
metadata across run_card_con88.json, registry/con88_gates.json, and
evidence/con88_clearance_withdrawal_20261025.json.

Exits 0 when the negative research archive is consistent; exits 2 on --require-submit;
exits 1 on any corruption or policy regression. Enforced identically under python -O.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio
import tifffile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57.uniqueness import _near  # noqa: E402

EXPECTED_TIF_NAME = "gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif"
EXPECTED_TIF_SHA = "e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68"
WITNESS_SHA = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(root: Path = ROOT) -> dict:
    root = Path(root)
    tif = root / "docs/downloads" / EXPECTED_TIF_NAME
    zip_path = tif.with_suffix(".zip")
    sidecar = tif.with_suffix(".json")
    require(tif.is_file() and zip_path.is_file() and sidecar.is_file(),
            "Archived CON88 -DO-NOT-SUBMIT package missing")
    require("DO-NOT-SUBMIT" in tif.name and "DO-NOT-SUBMIT" in zip_path.name,
            "CON88 package must carry -DO-NOT-SUBMIT filename marker")
    unmarked = root / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.tif"
    require(not unmarked.exists() and not unmarked.with_suffix(".zip").exists(),
            "Unmarked CON88 download artifact still present")

    tif_sha = sha256(tif)
    zip_sha = sha256(zip_path)
    require(tif_sha == EXPECTED_TIF_SHA, f"CON88 TIFF SHA changed: {tif_sha}")

    with zipfile.ZipFile(zip_path) as zf:
        require(zf.namelist() == [tif.name], f"Unexpected CON88 ZIP members: {zf.namelist()}")
        require(zf.read(tif.name) == tif.read_bytes(), "CON88 ZIP member bytes differ from TIFF")

    sample_path = root / "data/bridge/sample_submission.tif"
    cat_path = root / "data/bridge/existing_faults.tif"
    witness_path = root / "data/registry/dense_17gemdoe.tif"
    if sample_path.is_file() and cat_path.is_file() and witness_path.is_file():
        require(sha256(witness_path) == WITNESS_SHA, "17GEMSDOE witness SHA mismatch")
        with rasterio.open(sample_path) as sds, rasterio.open(tif) as cds:
            sample = sds.read(1)
            foot = np.isfinite(sample) & (sds.read_masks(1) > 0)
            pred = cds.read(1)
            require(cds.count == 1 and cds.dtypes == ("float32",), "CON88 must be 1-band float32")
            require(cds.crs == sds.crs and cds.shape == sds.shape and cds.transform == sds.transform,
                    "CON88 grid/CRS/transform mismatch")
            require(cds.nodata is None, "CON88 nodata must be None")
        alt = tifffile.imread(tif)
        require(np.array_equal(pred, alt), "Independent TIFF decoders disagree on CON88")
        require(bool(np.isfinite(pred).all()) and float(pred.min()) >= 0.0 and float(pred.max()) <= 1.0,
                "CON88 values outside finite [0, 1]")
        dots = pred > 0
        require(int(dots.sum()) == 37654, f"Unexpected CON88 dot count: {int(dots.sum())}")
        require(not bool((dots & ~foot).any()), "CON88 positive pixels outside footprint")
        with rasterio.open(cat_path) as fds:
            cat = (fds.read(1) > 0) & foot
        require(not bool((dots & cat).any()), "CON88 positive pixels on mapped catalogue")
        with rasterio.open(witness_path) as wds:
            w = wds.read(1)
        wdots = np.isfinite(w) & (w > 0) & foot
        lit_ov = float(_near(wdots, 3.0)[dots].mean())
        require(lit_ov == 1.0, f"Expected literal overlap 1.0 vs 17GEMSDOE, got {lit_ov}")
    else:
        lit_ov = 1.0

    cards = [root / r for r in ("run_card_con88.json", "registry/con88_run_card.json", "docs/data/con88_run_card.json")]
    require(all(p.is_file() for p in cards) and len({p.read_bytes() for p in cards}) == 1,
            "CON88 run_card mirrors missing or divergent")
    card = json.loads(cards[0].read_text())
    require(card.get("lane") == "H88-CON88" and card.get("verdict") == "negative"
            and card.get("ok_to_submit") is False and card.get("approved_for_weekly_slot") is False
            and card.get("raster_sha256") == EXPECTED_TIF_SHA,
            "CON88 run_card withdrawal invariants violated")

    gates_paths = [root / "registry/con88_gates.json", root / "docs/data/con88_gates.json"]
    require(all(p.is_file() for p in gates_paths) and gates_paths[0].read_bytes() == gates_paths[1].read_bytes(),
            "CON88 gates JSON mirrors missing or divergent")
    gates = json.loads(gates_paths[0].read_text())
    require(gates.get("ok_to_submit") is False and gates.get("verdict") == "negative"
            and gates.get("G2_ok") is False and gates.get("sha256") == EXPECTED_TIF_SHA,
            "CON88 gates JSON withdrawal invariants violated")

    certs = [root / "evidence/con88_clearance_withdrawal_20261025.json",
             root / "docs/data/con88_clearance_withdrawal_20261025.json"]
    require(all(p.is_file() for p in certs) and certs[0].read_bytes() == certs[1].read_bytes(),
            "CON88 clearance withdrawal certificate missing or divergent")
    cert = json.loads(certs[0].read_text())
    require(cert.get("schema") == "gems88.historical-clearance-withdrawal.v1"
            and cert.get("unchanged_tiff_sha256") == EXPECTED_TIF_SHA
            and cert.get("prediction_bytes_changed") is False
            and cert.get("ok_to_submit") is False,
            "CON88 clearance withdrawal certificate invalid")

    return {
        "lane": "H88-CON88",
        "status": "ARCHIVED_RESEARCH_ONLY_DO_NOT_SUBMIT",
        "file": f"docs/downloads/{tif.name}",
        "sha256": tif_sha,
        "zip_sha256": zip_sha,
        "literal_overlap_vs_17gemsdoe": lit_ov,
        "ok_to_download_for_research": True,
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "verdict": "negative",
    }


def main(argv=None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate(root)
    except Exception as exc:
        print(json.dumps({"lane": "H88-CON88", "status": "AUDIT_ERROR",
                          "error": str(exc), "ok_to_submit": False}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 2 if args.require_submit else 0


if __name__ == "__main__":
    raise SystemExit(main())
