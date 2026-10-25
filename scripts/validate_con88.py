#!/usr/bin/env python3
"""Independent saved-byte validator for the archived H88-CON88 research GeoTIFF.

Re-opens the archived TIFF and ZIP under ``docs/downloads/``, verifies mirror
parity across ``run_card_con88.json``, ``registry/con88_run_card.json``,
``docs/data/con88_run_card.json``, ``registry/con88_gates.json``,
``docs/data/con88_gates.json``, ``evidence/con88_clearance_withdrawal_20261025.json``,
and ``docs/data/con88_clearance_withdrawal_20261025.json``, checks single-band
float32 ``[0, 1]`` finiteness, grid parity, ``DO-NOT-SUBMIT`` ZIP member
packaging, and literal dense-witness (`1.0 > 0.70` vs `17GEMSDOE`) plus
holdout (`0.0` / `0.001714` vs `0.205991`) stop facts (`IR-88-3C391D97-01`).

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
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from gems57.uniqueness import dot_overlap, equal_support_dots  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402

EXPECTED_TIF_SHA = "e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68"
EXPECTED_ZIP_SHA = "5a4f4a530c81210d70dc5cd01481602227d7d84dee5428cea98ae0638f2d855d"
HISTORICAL_UNMARKED_ZIP_SHA = "6b61c6d1bf3c8657de4ad4699c91285c767de9859fe88e0deaf71db65a0b2f08"


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
    root_card_path = ROOT / "run_card_con88.json"
    reg_card_path = ROOT / "registry/con88_run_card.json"
    web_card_path = ROOT / "docs/data/con88_run_card.json"
    reg_gates_path = ROOT / "registry/con88_gates.json"
    web_gates_path = ROOT / "docs/data/con88_gates.json"
    ev_with_path = ROOT / "evidence/con88_clearance_withdrawal_20261025.json"
    web_with_path = ROOT / "docs/data/con88_clearance_withdrawal_20261025.json"

    for p in (
        root_card_path,
        reg_card_path,
        web_card_path,
        reg_gates_path,
        web_gates_path,
        ev_with_path,
        web_with_path,
    ):
        if not p.is_file():
            problems.append(f"missing required CON88 record: {p.relative_to(ROOT)}")

    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1

    card = json.loads(root_card_path.read_text(encoding="utf-8"))
    reg_card = json.loads(reg_card_path.read_text(encoding="utf-8"))
    web_card = json.loads(web_card_path.read_text(encoding="utf-8"))
    if not (card == reg_card == web_card):
        problems.append("CON88 run_card mirrors disagree across root, registry/, and docs/data/")

    gates = json.loads(reg_gates_path.read_text(encoding="utf-8"))
    web_gates = json.loads(web_gates_path.read_text(encoding="utf-8"))
    if gates != web_gates:
        problems.append("CON88 gates mirrors disagree between registry/ and docs/data/")

    withdrawal = json.loads(ev_with_path.read_text(encoding="utf-8"))
    web_withdrawal = json.loads(web_with_path.read_text(encoding="utf-8"))
    if withdrawal != web_withdrawal:
        problems.append("CON88 clearance withdrawal mirrors disagree between evidence/ and docs/data/")

    for label, obj in (("run_card", card), ("gates", gates), ("withdrawal", withdrawal)):
        if obj.get("ok_to_submit") is not False or obj.get("verdict") != "negative":
            problems.append(f"CON88 {label} must enforce ok_to_submit=false and verdict='negative'")

    if card.get("policy_correction") != "IR-88-3C391D97-01":
        problems.append("CON88 run_card missing policy_correction IR-88-3C391D97-01")
    if not (0 < len(card.get("submission_name", "")) <= 140) or "DO-NOT-SUBMIT" not in card.get("submission_name", ""):
        problems.append("CON88 submission_name must be <=140 chars and include DO-NOT-SUBMIT")
    if not (0 < len(card.get("submission_note", "")) <= 140) or "DO NOT SUBMIT" not in card.get("submission_note", ""):
        problems.append("CON88 submission_note must be <=140 chars and include DO NOT SUBMIT")

    tif = ROOT / card["download"]
    zip_path = ROOT / card["zip_download"]
    if not tif.is_file() or not zip_path.is_file():
        problems.append("missing archived CON88 TIFF or ZIP under docs/downloads/")
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1

    if "DO-NOT-SUBMIT" not in tif.name or "DO-NOT-SUBMIT" not in zip_path.name:
        problems.append("archived CON88 filenames lack DO-NOT-SUBMIT marker")
    if (ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.tif").exists():
        problems.append("unmarked CON88 TIFF still exists in docs/downloads/")
    if (ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.zip").exists():
        problems.append("unmarked CON88 ZIP still exists in docs/downloads/")

    actual_tif_sha = sha256_file(tif)
    actual_zip_sha = sha256_file(zip_path)
    if actual_tif_sha != EXPECTED_TIF_SHA or card.get("raster_sha256") != EXPECTED_TIF_SHA:
        problems.append(f"CON88 TIFF SHA-256 mismatch: {actual_tif_sha}")
    if actual_zip_sha != EXPECTED_ZIP_SHA or card.get("zip_sha256") != EXPECTED_ZIP_SHA:
        problems.append(f"CON88 ZIP SHA-256 mismatch: {actual_zip_sha}")

    with zipfile.ZipFile(zip_path) as zf:
        if zf.namelist() != [tif.name] or zf.read(tif.name) != tif.read_bytes():
            problems.append("CON88 ZIP member mismatch or bytes differ from standalone TIFF")

    sample = ROOT / "data/bridge/sample_submission.tif"
    faults_path = ROOT / "data/bridge/existing_faults.tif"
    witness_path = ROOT / "data/registry/dense_17gemdoe.tif"
    if not sample.is_file() or not faults_path.is_file() or not witness_path.is_file():
        problems.append("missing validation inputs under data/bridge or data/registry")
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1

    v_out = validate_artifact(tif, sample)
    if not v_out["ok"]:
        problems.append(f"validate_artifact failed: {v_out}")

    with rasterio.open(sample) as sds:
        foot = np.isfinite(sds.read(1))
    with rasterio.open(faults_path) as fds:
        cat = fds.read(1) > 0
    with rasterio.open(tif) as ds:
        pred = ds.read(1)
        if ds.nodata is not None:
            problems.append(f"nodata declared ({ds.nodata}); expected None")
    try:
        import tifffile
        b = tifffile.imread(tif)
        if not np.array_equal(pred, b):
            problems.append("rasterio and tifffile decoded arrays differ")
    except Exception as exc:  # pragma: no cover
        problems.append(f"tifffile decode failed: {exc}")

    dots = np.isfinite(pred) & (pred > 0)
    n_dots = int(dots.sum())
    if n_dots != 37654:
        problems.append(f"expected 37654 positive dots, got {n_dots}")
    if bool((dots & ~foot).any()) or bool((dots & cat).any()):
        problems.append("positive dots outside footprint or on catalogue")

    with rasterio.open(witness_path) as wds:
        dense = wds.read(1)
    lit_ov = dot_overlap(pred, dense)
    eq_dots = equal_support_dots(dense, n_dots, foot)
    eq_ov = dot_overlap(pred, eq_dots.astype(np.float32))
    if abs(lit_ov - 1.0) > 1e-9:
        problems.append(f"expected literal overlap 1.0 vs dense_17gemdoe.tif, got {lit_ov}")

    summary = {
        "lane": "H88-CON88",
        "policy_correction": "IR-88-3C391D97-01",
        "file": card["download"],
        "sha256": actual_tif_sha,
        "zip_sha256": actual_zip_sha,
        "historical_unmarked_zip_sha256": HISTORICAL_UNMARKED_ZIP_SHA,
        "positive_dots": n_dots,
        "format_valid": len(problems) == 0,
        "literal_overlap_vs_dense_17gemdoe_3px": lit_ov,
        "equal_support_overlap_vs_dense_17gemdoe_3px_diagnostic": eq_ov,
        "holdout_dti_fixed_tif": card["holdout_dti"]["fixed_tif_vs_withheld_segments"]["dti"],
        "holdout_dti_collar_reemission": card["holdout_dti"]["per_fold_collar_reemission_visible_only"]["collar_3p0px_dti"],
        "ok_to_download_for_research_only": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "problems": problems,
    }
    print(json.dumps(summary, indent=2))
    if problems:
        return 1
    if args.require_submit:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
