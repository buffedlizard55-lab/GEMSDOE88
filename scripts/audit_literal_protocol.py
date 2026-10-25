#!/usr/bin/env python3
"""Recheck the latest advertised artifact against the literal duplicate-stop rule.

Audit only: never emits predictions, adjusts a threshold, or uses a slot. Uses
shared template format, overlap and saturation tools, not a private evaluator.
Exit 0 means a consistent completed audit; --require-submit returns 2 for a
blocked artifact, and corrupted/missing inputs return 1 (no stale success).
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from gems57 import grid, uniqueness  # noqa: E402
from scripts.restore_inputs import VALIDATION_GROUPS  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pinned(root, relative, digest):
    path = root / relative
    if sha(path) != digest:
        raise ValueError(f"SHA256 mismatch: {relative}")
    return path


def coverage_proof(footprint, witness):
    if footprint.shape != witness.shape or not footprint.any():
        raise ValueError('Empty or mismatched footprint')
    support = np.isfinite(witness) & (witness > 0)
    # Direct coverage is a stronger sufficient condition than 3px halo coverage.
    covered = int(np.count_nonzero(support & footprint))
    total = int(footprint.sum())
    return {'footprint_pixels': total, 'directly_covered_pixels': covered,
            'all_nonempty_in_footprint_candidates_blocked': covered == total,
            'reason': 'Every allowed dot already lies on positive registry support' if covered == total
                      else 'This sufficient proof is inconclusive; run full registry tests'}


def inspect(root=ROOT):
    root = Path(root)
    card = json.loads((root / "registry/mdps88_run_card.json").read_text())
    sample = pinned(root, "data/bridge/sample_submission.tif", grid.SHA256_SAMPLE_SUBMISSION)
    catalogue = pinned(root, "data/bridge/existing_faults.tif", grid.SHA256_EXISTING_FAULTS)
    group = next(g for g in VALIDATION_GROUPS if g[0] == "17GEMSDOE-witness")
    source_path, witness_rel, witness_hash = group[3][0]
    witness = pinned(root, witness_rel, witness_hash)
    tif = (root / card["raster"]["file"]).resolve()
    archive = (root / card["raster"]["zip"]).resolve()
    for path in (tif, archive):
        if not path.is_relative_to((root / "docs/downloads").resolve()):
            raise ValueError("candidate escapes download directory")
    if sha(tif) != card["raster_sha256"] or sha(archive) != card["raster"]["zip_sha256"]:
        raise ValueError("candidate TIFF/ZIP hash mismatch")
    validation = validate_artifact(tif, sample)
    if not validation["ok"]:
        raise ValueError("candidate failed on-disk format/footprint audit")
    with rasterio.open(sample) as src:
        footprint = np.isfinite(src.read(1)) & (src.read_masks(1) > 0)
        expected_grid = (src.shape, src.crs, src.transform)
    with rasterio.open(catalogue) as src:
        if (src.shape, src.crs, src.transform) != expected_grid:
            raise ValueError("catalogue grid mismatch")
        cat = (src.read(1) > 0) & footprint
    with rasterio.open(tif) as src:
        dots = src.read(1) > 0
    if not dots.any() or (dots & cat).any():
        raise ValueError("empty prediction or positive support on catalogue")
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP does not contain exactly the byte-identical TIFF")
    certificate = uniqueness.saturation_certificate(
        witness, footprint, cat, expected_grid=expected_grid)
    certificate["witness_file"] = witness_rel
    with rasterio.open(witness) as src:
        prior = src.read(1)
    overlap = uniqueness.dot_overlap(dots, np.isfinite(prior) & (prior > 0) & footprint)
    literal_duplicate = overlap > .70
    # One witnessed violation is sufficient to reject; this is NOT a full fleet scan.
    if not certificate["universal_overlap_blocker"] or not literal_duplicate:
        raise ValueError("historical universal blocker no longer reproduces; review required")
    note = card["submission_note"]
    if not note.strip() or len(note) > 140:
        raise ValueError("invalid submission note")
    return {
        "schema": "gems88.literal-protocol-audit.v1",
        "date_utc": "2026-10-25",
        "hypothesis": card["hypothesis"],
        "mechanism": card["mechanism"],
        "named_non_fault_process": card["named_non_fault_process"],
        "holdout": card["holdout"],
        "holdout_provenance": "Historical run card; not retrained in this audit. Pooled arithmetic checked separately by validate_mdps88.py.",
        "correlation_overlap_vs_registry": {
            "final_literal_overlap_3px_remeasured": overlap,
            "literal_duplicate": literal_duplicate,
            "scope": "One hash-pinned counterexample suffices to reject; NOT a complete registry uniqueness scan.",
            "preplacement": "Universal coverage certificate blocks every nonempty dot placement before training; no new surface created.",
            "historical_surface_abs_spearman": card["correlation_overlap_vs_registry"]["surface_preplacement_worst_abs_spearman"],
            "historical_surface_rho_not_recomputed": True,
        },
        "saturation_certificate": certificate,
        "witness_source": f"{group[1].removesuffix('.git')}/blob/{group[2]}/{source_path}",
        "raster": card["raster"]["file"],
        "raster_sha256": sha(tif),
        "validator_output": validation,
        "zip_one_byte_identical_tif": True,
        "submission_name": card["submission_name"],
        "submission_note": note,
        "new_rasters_generated": 0,
        "experiments_run": 0,
        "slots_used": 0,
        "organizer_confirmed_score": None,
        "ok_to_download_for_research": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "decision": "DUPLICATE_STOP",
        "reason": "Literal 3px overlap exceeds 70%; no dense-prior exemption authorized. Existing holdout gates also fail.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args()
    try:
        result = inspect()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        result = {"schema": "gems88.literal-protocol-audit.v1", "decision": "AUDIT_ERROR",
                  "ok_to_download_for_research": False, "ok_to_submit": False,
                  "verdict": "negative", "error": str(exc)}
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    for output in (ROOT / "evidence/literal_protocol_audit_20261025.json",
                   ROOT / "docs/data/literal_protocol_audit.json"):
        output.write_text(text)
    print(text, end="")
    if result["decision"] == "AUDIT_ERROR":
        return 1
    return 2 if args.require_submit else 0


if __name__ == "__main__":
    raise SystemExit(main())
