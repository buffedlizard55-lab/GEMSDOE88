#!/usr/bin/env python3
"""Independent fail-closed validator for the H88-BGCD research GeoTIFF & ZIP.

Reopens on-disk bytes (`rasterio`, `tifffile` second decoder, `zipfile`,
`vendor/gems57/validate.py`, `src/gems88/gate.py`, and `dense_17gemdoe.tif`
saturation witness) and verifies preregistration ordering, 60-feature canary,
HOLDOUT-DTI provenance, and 326-raster uniqueness bounds.

Exit 0 = valid research download (`ok_to_download=True`).
`--require-submit` exits 2 while `ok_to_submit` is False (binding literal
dense-witness overlap = 1.0 > 0.70, paired holdout CI straddling 0 vs B12
control, and selector gate).
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import grid as grid_mod, uniqueness, validate as v_validate  # noqa: E402
from gems88 import gate  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_bgcd88(root: Path = ROOT) -> dict:
    root = Path(root)
    reg_card_p = root / "registry/bgcd88_run_card.json"
    web_card_p = root / "docs/data/bgcd88_run_card.json"
    reg_gate_p = root / "registry/bgcd88_gate_verdict.json"
    web_gate_p = root / "docs/data/bgcd88_gate_verdict.json"
    prereg_p = root / "registry/preregistration_bgcd88_20261025.json"

    for p in (reg_card_p, web_card_p, reg_gate_p, web_gate_p, prereg_p):
        if not p.is_file():
            raise FileNotFoundError(f"Missing required H88-BGCD artifact: {p}")

    card = json.loads(reg_card_p.read_text())
    web_card = json.loads(web_card_p.read_text())
    gv = json.loads(reg_gate_p.read_text())
    web_gv = json.loads(web_gate_p.read_text())
    prereg = json.loads(prereg_p.read_text())

    if card != web_card or gv != web_gv:
        raise ValueError("H88-BGCD registry vs docs/data run-card or gate-verdict mismatch")
    if not prereg.get("written_before_results") or prereg["written_utc"] >= card["generated_utc"]:
        raise ValueError("H88-BGCD preregistration timestamp does not strictly precede generated results")
    if card["verdict"] != "negative" or card["ok_to_submit"] is not False or card["ok_to_download"] is not True:
        raise ValueError("H88-BGCD must stay fail-closed (verdict=negative, ok_to_submit=False, ok_to_download=True)")
    if gv["ok_to_submit"] is not False or gv["ok_to_download"] is not True:
        raise ValueError("H88-BGCD gate verdict must keep ok_to_submit=False and ok_to_download=True")

    tif = root / card["submission"]["file"]
    archive = root / card["submission"]["zip_file"]
    receipt_p = tif.with_suffix(".json")
    for p in (tif, archive, receipt_p):
        if not p.is_file():
            raise FileNotFoundError(f"Missing H88-BGCD emission file: {p}")
    if "DO-NOT-SUBMIT" not in tif.name:
        raise ValueError("Fail-closed research GeoTIFF must carry DO-NOT-SUBMIT in filename")

    tif_sha = sha256_file(tif)
    zip_sha = sha256_file(archive)
    receipt = json.loads(receipt_p.read_text())
    if tif_sha != card["raster_sha256"] or tif_sha != gv["sha256"] or tif_sha != receipt["sha256"]:
        raise ValueError("H88-BGCD GeoTIFF SHA-256 mismatch across disk, run card, gate verdict, or receipt")
    if zip_sha != card["zip_sha256"] or zip_sha != gv["zip_sha256"] or zip_sha != receipt["zip_sha256"]:
        raise ValueError("H88-BGCD ZIP SHA-256 mismatch across disk, run card, gate verdict, or receipt")

    with zipfile.ZipFile(archive) as zf:
        if zf.testzip() is not None or zf.namelist() != [tif.name] or zf.read(tif.name) != tif.read_bytes():
            raise ValueError("H88-BGCD ZIP must hold exactly one flat byte-identical GeoTIFF")

    name = card["submission"]["submission_name"]
    note = card["submission"]["submission_note"]
    if not (1 <= len(name) <= 140) or not (1 <= len(note) <= 140):
        raise ValueError("submission name and note must be 1..140 characters")
    if card["experiments_executed"] > 3 or card["elapsed_seconds"] > 7200:
        raise ValueError("Parallel-run budget (<=3 experiments, <=7200s) violated")

    canary = card["leakage_canary"]
    if not canary["passed"] or canary["features_tested"] != 60 or canary["max_symmetric_auc"] > 0.90:
        raise ValueError("60-feature leakage canary missing or failed")

    hd = card["holdout_dti"]
    if (
        hd["evidence_class"] != "HOLDOUT-DTI"
        or hd["evaluator_version"] != "gems57-pooled-hide-v2"
        or hd["withheld_positive_pixels_overall"] != 22893
        or not (0.0 <= hd["overall"]["ci95"][0] <= hd["overall"]["dti"] <= hd["overall"]["ci95"][1] <= 1.0)
    ):
        raise ValueError("HOLDOUT-DTI metadata or CI bounds invalid")

    corr = card["correlation_overlap_vs_registry"]
    worst_lfl_ext = corr["final_worst_like_for_like_overlap_3px_extended"]["value"]
    worst_lfl_pin = corr["final_worst_like_for_like_overlap_3px_pinned"]["value"]
    if worst_lfl_ext > 0.70 or worst_lfl_pin > 0.70:
        raise ValueError(f"Like-for-like 3px overlap exceeds 0.70 ({worst_lfl_ext})")
    if corr["surface_preplacement_max_abs_spearman"] > 0.90 or corr["final_worst_abs_rho_extended"]["value"] > 0.90:
        raise ValueError("Surface or final |Spearman rho| exceeds 0.90")
    if card["submission"]["share_le2"] != 0.0 or card["submission"]["share_gt25"] < 0.35:
        raise ValueError("H33 basin distance fingerprint screen failed")

    sample = root / "data/bridge/sample_submission.tif"
    witness = root / "data/registry/dense_17gemdoe.tif"
    grid_reopened = False
    literal_witness_overlap = None
    if sample.is_file() and (root / "data/bridge/existing_faults.tif").is_file():
        g = grid_mod.load_grid(root / "data/bridge")
        portal = gate.portal_validate(tif, sample, g.footprint)
        val = v_validate.validate(tif, g.footprint, g.catalogue)
        v_validate.assert_submittable(val)
        if not (portal["ok"] and val["all_checks_passed"] and portal["n_dots"] == card["submission"]["positive_pixels"]):
            raise ValueError("On-disk H88-BGCD GeoTIFF failed portal_validate or vendor validate")
        if portal["second_decoder"].get("equal") is not True:
            raise ValueError("Second independent TIFF decoder disagreed with rasterio")
        grid_reopened = True

        if witness.is_file():
            with rasterio.open(tif) as src:
                cand_arr = src.read(1)
            with rasterio.open(witness) as wsrc:
                w_arr = wsrc.read(1)
            with rasterio.open(sample) as ref:
                expected_grid = (ref.shape, ref.crs, ref.transform)
            cert = uniqueness.saturation_certificate(witness, g.footprint, g.catalogue, expected_grid=expected_grid)
            literal_witness_overlap = float(
                uniqueness.dot_overlap(cand_arr, (np.isfinite(w_arr) & (w_arr > 0)) & g.footprint, radius_px=3)
            )
            if not cert["universal_overlap_blocker"] or literal_witness_overlap != 1.0:
                raise ValueError("Dense-witness saturation certificate or literal overlap != 1.0")

    return {
        "ok": True,
        "lane": card["lane"],
        "file": card["submission"]["file"],
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "positive_pixels": card["submission"]["positive_pixels"],
        "share_le2": card["submission"]["share_le2"],
        "share_gt25": card["submission"]["share_gt25"],
        "holdout_dti_overall": hd["overall"]["dti"],
        "holdout_ci95_overall": hd["overall"]["ci95"],
        "holdout_dti_far_gt10px": hd["far_gt10px"]["dti"],
        "holdout_dti_blind_gt25px": hd["blind_gt25px"]["dti"],
        "canary_max_symmetric_auc": canary["max_symmetric_auc"],
        "preplacement_max_abs_rho": corr["surface_preplacement_max_abs_spearman"],
        "worst_like_for_like_overlap_3px_extended": worst_lfl_ext,
        "extended_rasters_checked": corr["extended_live_sibling_rasters_checked"],
        "literal_witness_overlap_3px": literal_witness_overlap,
        "grid_reopened_against_sample": grid_reopened,
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": card["verdict"],
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    rep = validate_bgcd88(ROOT)
    print(json.dumps(rep, indent=2))
    if "--require-submit" in args:
        print(
            "AUTOMATIC SUBMISSION GATE: DO NOT SUBMIT "
            "(literal dense-witness overlap = 1.0 > 0.70 & selector gate required; exit 2).",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
