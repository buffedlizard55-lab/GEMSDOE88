#!/usr/bin/env python3
"""H88-MTAS pre-placement feasibility gate; NEVER creates a prediction.

The literal all-raster rule applies to BOTH a surface and its emitted dots. A
SHA-pinned full-coverage registry witness therefore makes *every* nonempty
candidate inadmissible. This gate runs before feature construction, holdout,
dot placement, or the writer. Exit 0 means the audit finished, NOT permission
to submit; --require-submit and --gate-generation exit 2 on DUPLICATE_STOP.
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
from scripts.audit_literal_protocol import pinned  # noqa: E402
from scripts.restore_inputs import VALIDATION_GROUPS  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402

OUTPUTS = (
    "registry/mtas88_run_card.json",
    "docs/data/mtas88_run_card.json",
    "evidence/mtas88_preflight_20261025.json",
)
NAME = "GEMSDOE88-MTAS-PREFLIGHT-20261025-NO-FILE"
NOTE = "MTAS pre-placement duplicate: registry covers all allowed cells; no TIFF built; UNSCORED; DO NOT SUBMIT"
# Independent expected bytes; the restoration manifest is checked against this pin.
WITNESS_REL = "data/registry/dense_17gemdoe.tif"
WITNESS_SHA = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
ARCHIVED_TIF = "docs/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif"
ARCHIVED_SHA = "db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def archive_for_research(root: Path, sample: Path) -> dict:
    """Reopen the prior research TIFF/ZIP; never call it a NEW candidate."""
    # IR-88-SDTL-01: the canonical current release is no longer TDKL; the archived
    # research artifact is pinned by its own historical run card and constants.
    tdkl = json.loads((root / "registry/tdkl88_run_card.json").read_text())
    card = dict(candidate="H88-TDKL", file=tdkl["raster"]["file"], file_sha256=tdkl["raster"]["sha256"],
                zip_file=tdkl["raster"]["zip_file"], zip_sha256=tdkl["raster"]["zip_sha256"])
    if card["file"] != ARCHIVED_TIF or card["file_sha256"] != ARCHIVED_SHA:
        raise ValueError("archived research download no longer matches pinned H88-TDKL release")
    relative = card["file"]
    tif = (root / relative).resolve()
    archive = (root / card["zip_file"]).resolve()
    base = (root / "docs/downloads").resolve()
    if not tif.is_relative_to(base) or not archive.is_relative_to(base):
        raise ValueError("archived research download escapes docs/downloads")
    if "DO-NOT-SUBMIT" not in tif.name or "DO-NOT-SUBMIT" not in archive.name:
        raise ValueError("archived research download lacks DO-NOT-SUBMIT marker")
    if sha(tif) != card["file_sha256"] or sha(archive) != card["zip_sha256"]:
        raise ValueError("archived research TIFF/ZIP SHA-256 mismatch")
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError("archived ZIP must contain exactly the identical TIFF")
    validation = validate_artifact(tif, sample)
    if not validation["ok"] or validation["raster_sha256"] != card["file_sha256"]:
        raise ValueError("archived research TIFF failed saved-byte format check")
    return {
        "status": "EXISTING_2026-10-24_RESEARCH_ARTIFACT_NOT_A_NEW_SUBMISSION",
        "download": relative,
        "zip_download": card["zip_file"],
        "sha256": card["file_sha256"],
        "zip_sha256": card["zip_sha256"],
        "validator_output": validation,
        "ok_to_download_for_research_only": True,
        "ok_to_submit": False,
    }


def inspect(root: Path = ROOT) -> dict:
    """Recompute the universal bound from pinned bytes, not old card claims."""
    root = Path(root)
    if not NAME or len(NAME) > 140 or not NOTE or len(NOTE) > 140:
        raise ValueError("invalid reserved name/note")
    prereg = json.loads((root / "registry/preregistration_mtas88.json").read_text())
    if prereg["lane"] != "H88-MTAS" or prereg["frozen_before_computation"] is not True:
        raise ValueError("MTAS preregistration missing or not frozen")
    sample = pinned(root, "data/bridge/sample_submission.tif", grid.SHA256_SAMPLE_SUBMISSION)
    pinned(root, "data/bridge/existing_faults.tif", grid.SHA256_EXISTING_FAULTS)
    group = next(g for g in VALIDATION_GROUPS if g[0] == "17GEMSDOE-witness")
    path, witness_rel, digest = group[3][0]
    if witness_rel != WITNESS_REL or digest != WITNESS_SHA:
        raise ValueError("witness path/SHA-256 pin mismatch in restoration manifest")
    witness = pinned(root, witness_rel, WITNESS_SHA)
    g = grid.load_grid(root / "data/bridge")
    valid = g.footprint
    allowed = valid & ~g.catalogue
    if not valid.any() or not allowed.any():
        raise ValueError("empty footprint/allowed domain")
    expected_grid = (g.shape, g.crs, g.transform)
    certificate = uniqueness.saturation_certificate(
        witness, valid, g.catalogue, expected_grid=expected_grid
    )
    if certificate["witness_sha256"] != digest:
        raise ValueError("witness changed between pin check and saturation audit")
    # Stronger than the halo certificate: every allowed dot is already ON the
    # witness's positive support. Compare exact pixels, not only rounded stats.
    with rasterio.open(witness) as src:
        prior = src.read(1)
    direct = np.isfinite(prior) & (prior > 0)
    direct_count = int((direct & allowed).sum())
    directly_saturated = direct_count == int(allowed.sum())
    if certificate["universal_overlap_blocker"] != directly_saturated:
        raise ValueError("unexpected disagreement between direct and halo proof")
    certificate["directly_covered_allowed_pixels"] = direct_count
    certificate["directly_saturated"] = directly_saturated
    certificate["witness_file"] = witness_rel  # stable across checkout paths/CI
    certificate["source_url"] = (
        f"{group[1].removesuffix('.git')}/blob/{group[2]}/{path}"
    )
    archive = archive_for_research(root, sample)
    blocked = certificate["universal_overlap_blocker"]
    return {
        "schema": "gems88.mtas88.preplacement.v1",
        "date_utc": "2026-10-25",
        "lane": "H88-MTAS",
        "hypothesis": "A buried fault may produce a narrow gravity edge but a diffuse/demagnetized RTP edge beneath low-relief cover; test a cross-scale admittance residual.",
        "mechanism": "Difference of cached 200 m versus 800 m gravity and RTP gradient responses, conditioned on basin cover, terrain slope and transtension; preregistered but NOT FIT due to the universal registry stop.",
        "named_non_fault_process": "Unfaulted intrusive or volcanic lithologic contact with a density but weak magnetic contrast.",
        "candidate_ranking": "research/candidate-hypotheses-20261025-mtas.md",
        "preplacement_registry_proof": certificate,
        "correlation_overlap_vs_registry": {
            "surface_rank_correlation": None,
            "final_dot_rank_correlation": None,
            "final_dot_overlap_3px": None,
            "universal_lower_bound_on_any_nonempty_candidate_overlap_3px": 1.0 if blocked else None,
            "threshold": 0.70,
            "scope": "One SHA-pinned counterexample suffices to reject. NOT an inventory-wide uniqueness clearance.",
        },
        "holdout": {
            "status": "NOT_RUN_PREPLACEMENT_DUPLICATE_STOP" if blocked else "NOT_RUN_REGISTRY_NOT_CLEARED",
            "evaluator_version_if_unblocked": "gems57-pooled-hide-v2",
            "withheld_positive_pixels": None,
            "dti": None,
            "ci95": None,
            "reason": "No hypothesis was fitted and no prediction was emitted. A historical HOLDOUT-DTI cannot be relabelled as MTAS evidence.",
        },
        "single_feature_canaries": {"status": "NOT_RUN_NO_FEATURES_FITTED", "auc": None},
        "validator_output": {
            "status": "NOT_RUN_NO_NEW_RASTER",
            "no_nan_inside": None,
            "values_in_0_1": None,
            "crs_match": None,
            "shape_match": None,
            "transform_match": None,
        },
        "raster_sha256": None,
        "raster_file": None,
        "archived_research_download": archive,
        "submission_name": NAME,
        "submission_name_status": "RESERVED_ONLY_NO_FILE_NOT_FOR_PORTAL",
        "submission_note": NOTE,
        "submission_note_length": len(NOTE),
        "experiment_count": 0,
        "new_rasters_generated": 0,
        "weekly_slots_used": 0,
        "organizer_confirmed_score": None,
        "data_provenance": "Pinned owner GitHub mirrors, not authenticated against logged-in current organizer downloads; redistribution terms unchecked.",
        "official_reference_url": "https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/README.md",
        "ok_to_download_new_file": False,
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "decision": "DUPLICATE_STOP" if blocked else "REGISTRY_NOT_CLEARED",
        "verdict": "negative",
        "next_step": "Keep the binding rule; no eligible TIFF exists. A separately authorized, representation-aware policy revision would be required before another build, followed by new buffered holdout and two-phase uniqueness checks.",
    }


def write_report(root: Path, report: dict) -> None:
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    for name in OUTPUTS:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(payload, encoding="utf-8")
        temp.replace(target)


def main(argv=None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true")
    ap.add_argument("--gate-generation", action="store_true")
    args = ap.parse_args(argv)
    try:
        report = inspect(root)
    except Exception as exc:
        report = {
            "schema": "gems88.mtas88.preplacement.v1",
            "lane": "H88-MTAS",
            "decision": "AUDIT_ERROR",
            "verdict": "negative",
            "ok_to_submit": False,
            "ok_to_download_new_file": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        write_report(Path(root), report)  # erase any stale positive audit on failure
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 1
    write_report(Path(root), report)
    print(json.dumps(report, indent=2, allow_nan=False))
    if args.require_submit or args.gate_generation:
        return 2  # lack of a full registry/holdout pass NEVER clears a build
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
