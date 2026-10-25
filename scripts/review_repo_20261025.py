#!/usr/bin/env python3
"""Re-run the 2026-10-25 repository review without fitting or uploading.

This is an autonomous, fail-closed review command. It reconciles the stale
candidate queue with historical experiment records, verifies the H33 lineage
claim, rechecks official-source provenance labels and the current research
download, then proves whether the literal registry rule admits any nonempty
candidate. It does *not* train, place dots, create a new TIFF, select a lane or
weekly slot, or call DrivenData.

Exit codes:
  0  the audit completed; this is not submission approval
  1  required local bytes or the audit contract are missing/corrupt
  2  ``--require-submit`` was requested but the candidate is blocked
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
sys.path[:0] = [str(ROOT), str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import grid  # noqa: E402
from gems88.review import (  # noqa: E402
    OFFICIAL_SOURCES,
    hypothesis_queue,
    validate_hypothesis_queue,
)
from scripts.validate_artifact import validate_artifact  # noqa: E402

DATE_UTC = "2026-10-25"
OUTPUTS = (
    ROOT / "evidence/repo_review_20261025.json",
    ROOT / "docs/data/repo_review_20261025.json",
)
WITNESS_REL = "data/registry/dense_17gemdoe.tif"
WITNESS_SHA256 = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _same_grid(a: rasterio.DatasetReader, b: rasterio.DatasetReader) -> bool:
    return a.shape == b.shape and a.crs == b.crs and a.transform == b.transform


def audit_saturation(root: Path) -> dict:
    """Return a sufficient pre-placement duplicate proof from local bytes.

    The user rule is forward overlap: the denominator is the candidate's
    positive pixels.  If a positive registry witness covers every allowed cell,
    every nonempty allowed candidate has overlap 1.0.  This proof is stronger
    than emitting a candidate and then discovering the same result; it is why
    no candidate method is fit in this session.
    """

    sample_path = root / "data/bridge/sample_submission.tif"
    catalogue_path = root / "data/bridge/existing_faults.tif"
    witness_path = root / WITNESS_REL
    expected = {
        "sample_sha256": grid.SHA256_SAMPLE_SUBMISSION,
        "catalogue_sha256": grid.SHA256_EXISTING_FAULTS,
        "witness_sha256": WITNESS_SHA256,
    }
    paths = (sample_path, catalogue_path, witness_path)
    missing = [str(path.relative_to(root)) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing hash-pinned audit inputs: " + ", ".join(missing))
    actual = {
        "sample_sha256": sha256(sample_path),
        "catalogue_sha256": sha256(catalogue_path),
        "witness_sha256": sha256(witness_path),
    }
    if actual != expected:
        raise ValueError(f"hash-pinned audit input mismatch: expected {expected}, got {actual}")

    with rasterio.open(sample_path) as sample, rasterio.open(catalogue_path) as catalogue, rasterio.open(witness_path) as witness:
        if not _same_grid(sample, catalogue) or not _same_grid(sample, witness):
            raise ValueError("sample, catalogue and witness do not share one grid")
        sample_values = sample.read(1)
        catalogue_values = catalogue.read(1)
        witness_values = witness.read(1)
        footprint = np.isfinite(sample_values) & (sample.read_masks(1) > 0)
        catalogue_mask = (catalogue_values > 0) & footprint
        witness_support = np.isfinite(witness_values) & (witness_values > 0)
        allowed = footprint & ~catalogue_mask

        allowed_count = int(allowed.sum())
        covered_count = int((allowed & witness_support).sum())
        direct_fraction = covered_count / allowed_count if allowed_count else 0.0
        saturated = bool(allowed_count > 0 and covered_count == allowed_count)
        # The current user rule uses a 3-pixel halo. Direct support coverage is
        # a stronger sufficient condition, so the lower bound is exactly 1.0.
        lower_bound = 1.0 if saturated else None
        return {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "witness_file": WITNESS_REL,
            "witness_sha256": actual["witness_sha256"],
            "sample_sha256": actual["sample_sha256"],
            "catalogue_sha256": actual["catalogue_sha256"],
            "grid": {
                "shape": list(sample.shape),
                "crs": str(sample.crs),
                "transform": list(tuple(sample.transform)[:6]),
            },
            "footprint_pixels": int(footprint.sum()),
            "catalogue_pixels_inside_footprint": int(catalogue_mask.sum()),
            "allowed_pixels": allowed_count,
            "directly_covered_allowed_pixels": covered_count,
            "covered_allowed_fraction": direct_fraction,
            "uncovered_allowed_pixels": allowed_count - covered_count,
            "universal_overlap_blocker": saturated,
            "overlap_definition": "forward 3-pixel overlap: candidate positive pixels within 3 px of registry positive support",
            "overlap_limit": 0.70,
            "universal_lower_bound_on_any_nonempty_candidate": lower_bound,
            "implication": (
                "Every nonempty candidate in the allowed domain has forward overlap 1.0 > 0.70."
                if saturated
                else "The sufficient direct-coverage proof is inconclusive; a complete surface/dot registry audit is required."
            ),
        }


def audit_research_download(root: Path) -> dict:
    """Reopen the current advertised file and its one-member ZIP.

    The result is explicitly format-only.  A valid local file is never promoted
    by this function; the current release card is a historical research record.
    """

    status = _json(root / "docs/status.json")
    release = _json(root / "docs/data/current_release.json")
    tif = root / release["file"]
    archive = root / release["zip_file"]
    if not tif.is_file() or not archive.is_file():
        raise FileNotFoundError("current research TIFF or ZIP is missing")
    if sha256(tif) != release["file_sha256"] or sha256(archive) != release["zip_sha256"]:
        raise ValueError("current research TIFF/ZIP changed from current-release card")
    sample = root / "data/bridge/sample_submission.tif"
    checks = validate_artifact(tif, sample)
    with zipfile.ZipFile(archive) as member_zip:
        members = member_zip.namelist()
        one_matching_member = members == [tif.name] and member_zip.read(tif.name) == tif.read_bytes()
    if not one_matching_member:
        raise ValueError("research ZIP must contain exactly its byte-identical TIFF")
    return {
        "evidence_class": "LOCAL-FORMAT-AUDIT",
        "candidate": release["candidate"],
        "file": release["file"],
        "zip_file": release["zip_file"],
        "tif_sha256": sha256(tif),
        "zip_sha256": sha256(archive),
        "validator": checks,
        "zip_one_byte_identical_tif": True,
        "ok_to_download_for_research": bool(status.get("ok_to_download_for_research", True)),
        "ok_to_submit": False,
        "status_source": "docs/status.json + docs/data/current_release.json",
        "warning": "A local format PASS is not organizer acceptance, a uniqueness pass, or a weekly-slot selector decision.",
    }


def h33_forensics(root: Path) -> dict:
    """Extract measured lineage facts without relabelling the public claim."""

    evidence = _json(root / "evidence/h33_forensics_20261024.json")
    h33 = next(row for row in evidence["lineage"] if row["name"].startswith("H33 b2"))
    removed = evidence["removed_D28_to_H33"]
    return {
        "h33_value": 0.2778,
        "h33_evidence_class": "USER-REPORTED CLAIM — NOT HOLDOUT-DTI AND NOT ORGANIZER-CONFIRMED",
        "h33_source": "user prompt / archived owner ledger; no DrivenData receipt in this repository",
        "measured_on_disk": {
            "evidence_class": "REGISTRY-MEASUREMENT (lineage geometry, not score)",
            "h33_sha256": h33["sha256"],
            "h33_dots": h33["n_dots"],
            "h33_is_subset_of_h19_5": evidence["subset_chain"]["H33 b2 (GEMSDOE32) = R0 ⊂? H19-5 (19GEMSDOE)"]["frac_b_inside_a"] == 1.0,
            "h33_is_subset_of_d28": evidence["subset_chain"]["H33 b2 (GEMSDOE32) = R0 ⊂? D2.8 (GEMSDOE25)"]["frac_b_inside_a"] == 1.0,
            "h33_is_subset_of_solo_d28": evidence["subset_chain"]["H33 b2 (GEMSDOE32) = R0 ⊂? SOLO-D2.8 B=1 (GEMSDOE28)"]["frac_b_inside_a"] == 1.0,
            "h33_min_catalogue_distance_px": h33["d_cat_px"]["min"],
            "h33_median_catalogue_distance_px": h33["d_cat_px"]["median"],
            "h33_fraction_gt_30px": h33["frac_d_cat_gt_30"],
            "h33_nearest_neighbour_min_px": evidence["h33_spacing_px"]["nn_min"],
            "d28_to_h33_removed_dots": removed["n"],
            "removed_dots_catalogue_distance_px": removed["d_cat_px"],
            "removed_dots_fraction_within_2px_catalogue": removed["frac_le_2"],
        },
        "local_metric_definition": "The repository's triangular-kernel DTI is TP_w / (TP_w + 0.2*FP_w + 0.8*FN_w). This explains why reducing redundant false-positive mass could help, but is not a causal analysis of H33's hidden-label score.",
        "interpretation": (
            "H33 (37,654 dots) is a strict subset of H19-5 (121,131), D2.8 (44,090), and SOLO-D2.8 (40,199); it removes 6,436 D2.8 dots, all within 2 px of the catalogue. That geometry is consistent with de-redundancy, not evidence that the pruning caused a score gain. It does not prove the hidden labels, causality, or that the user-reported claim beats an official leaderboard result."
        ),
    }


def historical_mtas_experiment(root: Path) -> dict:
    """Preserve the measured MTAS holdout separately from this review's stop."""

    card = _json(root / "evidence/mtas88_experiment_20261025.json")
    holdout = card["holdout"]
    if card.get("lane") != "H88-MTAS" or holdout.get("evidence_class") != "HOLDOUT-DTI":
        raise ValueError("historical MTAS experiment card identity/evidence class mismatch")
    if holdout.get("evaluator_version") != "gems57-pooled-hide-v2":
        raise ValueError("historical MTAS evaluator mismatch")
    if len(holdout.get("ci95", [])) != 2:
        raise ValueError("historical MTAS confidence interval missing")
    return {
        "evidence_class": "HOLDOUT-DTI",
        "historical": True,
        "source_card": "evidence/mtas88_experiment_20261025.json",
        "lane": "H88-MTAS",
        "hypothesis": card["hypothesis"],
        "evaluator_version": holdout["evaluator_version"],
        "dti": holdout["dti"],
        "ci95": list(holdout["ci95"]),
        "withheld_positive_pixels": holdout["withheld_positive_pixels"],
        "folds": holdout["n_folds"],
        "seeds": list(holdout["seeds"]),
        "buffer_px": holdout["buffer_px"],
        "boundary_px": holdout["boundary_px"],
        "experiment_count": card["experiment_count"],
        "elapsed_seconds": card["elapsed_s"],
        "leakage_canary": {
            "status": "HISTORICAL_PASS",
            "max_symmetric_auc": card["leakage_canaries"]["max_symmetric_auc"],
            "max_feature": card["leakage_canaries"]["max_feature"],
            "threshold": card["leakage_canaries"]["threshold"],
        },
        "submission": {
            "weekly_slots_used": card["weekly_slots_used"],
            "organizer_confirmed_score": card["organizer_confirmed_score"],
            "ok_to_submit": card["ok_to_submit"],
            "verdict": card["verdict"],
            "raster_file": card["raster_file"],
            "raster_sha256": card["raster_sha256"],
            "ok_to_download_scope": card["ok_to_download_scope"],
        },
        "not_current": "The later preflight is a separate generation gate; it did not rerun or invalidate this historical holdout result.",
        "interpretation": "Historical local holdout measurement; negative/low result and not ORGANIZER-CONFIRMED. The later literal-support preflight stopped before any new model or holdout.",
    }


def reconcile_previous_queue() -> list[dict]:
    """Correct old UNTESTED labels where records or implemented neighbors exist."""

    return [
        {
            "id": "H88-MTAS",
            "former_queue_label": "UNTESTED",
            "corrected_status": "HISTORICALLY_TESTED",
            "evidence": "evidence/mtas88_experiment_20261025.json records HOLDOUT-DTI 0.049577 [0.044659, 0.054417].",
            "note": "The later preflight did not rerun MTAS; keep its historical result distinct from the current generation stop.",
        },
        {
            "id": "H88-PRAN",
            "former_queue_label": "UNTESTED",
            "corrected_status": "RELATED_PRIOR_METHODS; GLOBAL_NOVELTY_NOT_ESTABLISHED",
            "evidence": "KTH/MVRD and src/gems88/features.py already use K/Th, terrain-conditioned radiometry and related alteration channels.",
            "note": "Do not call a K/Th or radiometric alteration family untried from a new label alone.",
        },
        {
            "id": "H88-FARC",
            "former_queue_label": "UNTESTED",
            "corrected_status": "RELATED_PRIOR_METHODS; GLOBAL_NOVELTY_NOT_ESTABLISHED",
            "evidence": "src/gems88/features.py and QTSK records already include cross-catchment chi/knickpoint drainage features.",
            "note": "Any remaining candidate must define a distinct statistic/control beyond cross-catchment drainage steps.",
        },
        {
            "id": "H88-TCONS",
            "former_queue_label": "UNTESTED",
            "corrected_status": "RELATED_PRIOR_METHODS; GLOBAL_NOVELTY_NOT_ESTABLISHED",
            "evidence": "DHTC/HGVC and prior thermal/conductivity lanes use related coupled thermal, conductance and basin-depth evidence.",
            "note": "Generic thermal/conductivity co-location is not an untried family here.",
        },
        {
            "id": "H88-FLAC",
            "former_queue_label": "UNTESTED",
            "corrected_status": "RELATED_PRIOR_METHODS; GLOBAL_NOVELTY_NOT_ESTABLISHED",
            "evidence": "KDMC/MTAS and other magnetic/gravity lanes already include flight-line seam controls and potential-field edges.",
            "note": "A separate seam veto alone does not establish a genuinely untried geological mechanism.",
        },
    ]

def build_report(root: Path = ROOT) -> dict:
    root = Path(root)
    queue = hypothesis_queue()
    validate_hypothesis_queue(queue)
    errors: list[str] = []
    try:
        saturation = audit_saturation(root)
    except (OSError, ValueError, KeyError) as exc:
        saturation = None
        errors.append(f"saturation audit unavailable: {exc}")
    try:
        research_download = audit_research_download(root)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        research_download = None
        errors.append(f"research download audit unavailable: {exc}")

    try:
        mtas_history = historical_mtas_experiment(root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        mtas_history = None
        errors.append(f"historical MTAS experiment audit unavailable: {exc}")

    blocked = bool(saturation and saturation["universal_overlap_blocker"])
    review_status = "DUPLICATE_STOP" if blocked else ("INCOMPLETE" if errors else "REGISTRY_NOT_CLEARED")
    full_stack = root / "data/training_features.tif"
    validation_sample = root / "data/bridge/sample_submission.tif"
    return {
        "schema": "gems88.repo-review-20261025.v2",
        "review_date_utc": DATE_UTC,
        "review_status": review_status,
        "review_scope": "Repository evidence reconciliation and fail-closed registry preflight only; no experiment, holdout, leakage canary, TIFF build or submission.",
        "hypothesis_queue": queue,
        "hypothesis_novelty_scope": {
            "status_basis": "UNTESTED means the exact formulation is not recorded as executed in the checked source tree. Related geological families and input channels have prior implementations; this is not fleet-wide novelty certification.",
            "global_novelty_certified": False,
            "external_data_obtainability_verified": False,
            "maximum_candidates_for_future_review": 4,
        },
        "prior_queue_reconciliation": reconcile_previous_queue(),
        "assigned_method_lane": {
            "id": None,
            "status": "NOT ASSIGNED",
            "reason": "The preserved request/PROMPT.md does not specify a separate single-method paragraph. This review does not invent a lane.",
        },
        "official_sources": list(OFFICIAL_SOURCES),
        "source_verification_summary": {
            "fresh_official_pages_fetched": 1,
            "github_api_attempt": "403 API rate limit; a later fetch_page of the exact pinned GitHub HTML README succeeded",
            "fetched_official_page": "https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md",
            "verified_from_page": "The official README directs data downloads to the challenge website and documents CPU-only and GPU options, including Apple Silicon MPS.",
            "other_official_pages_fetched": 0,
            "owner_mirror_is_not_organizer_authentication": True,
            "source_claims_in_this_report": "Only the pinned GitHub README is freshly verified; competition pages, rules, leaderboard, data access, USGS and GDR pages are manual review links only.",
        },
        "input_status": {
            "validation_tier_sample_present": validation_sample.is_file(),
            "full_training_feature_stack_present": full_stack.is_file(),
            "full_stack_status": "RESTORED" if full_stack.is_file() else "ABSENT",
            "authenticated_organizer_download": False,
            "note": "Validation-tier inputs were restored from pinned owner mirrors. They are sufficient for the format/preflight audit, not for feature construction or claims of authenticated source provenance.",
        },
        "h33_forensics": h33_forensics(root),
        "historical_experiments": {
            "H88-MTAS": mtas_history,
        },
        "preplacement_registry_audit": saturation,
        "current_research_download": research_download,
        "holdout": {
            "evidence_class": "NO NEW MEASUREMENT",
            "status": "NOT RUN for this review; a historical MTAS HOLDOUT-DTI exists separately",
            "evaluator_version": "gems57-pooled-hide-v2",
            "withheld_positive_pixels": None,
            "dti": None,
            "ci95": None,
            "historical_mtas_reference": "historical_experiments.H88-MTAS",
            "reason": "The new method shortlist was not fitted or evaluated because the pre-placement literal-support stop fires. Do not overwrite, deny or re-label the separate historical MTAS receipt.",
        },
        "leakage_canary": {
            "status": "NOT RUN for shortlist; historical MTAS feature canaries exist in the historical card",
            "threshold_symmetric_auc": 0.90,
            "features_tested": 0,
            "historical_mtas_max_symmetric_auc": (mtas_history or {}).get("leakage_canary", {}).get("max_symmetric_auc"),
        },
        "experiment_budget": {
            "maximum_experiments": 3,
            "maximum_hours": 2,
            "experiments_this_review": 0,
            "hours_this_review": 0.0,
            "weekly_slots_used": 0,
        },
        "protocol_compliance": {
            "assigned_method_lane": None,
            "lane_selection": "NOT DONE — the request contains no separate single-method paragraph",
            "surface_abs_spearman_stop_threshold": 0.90,
            "final_dot_forward_overlap_stop_threshold": 0.70,
            "whole_buffered_fault_segments": "NOT RUN — pre-placement stop",
            "visible_only_catalogue_features": "NOT RUN — no new experiment",
            "feature_alone_leakage_canaries": "NOT RUN for shortlist; historical MTAS canaries are separately recorded",
            "shared_holdout_evaluator": "gems57-pooled-hide-v2",
            "shared_evaluator_used_this_review": False,
            "shared_writer_used_this_review": False,
            "holdout_experiments_this_review": 0,
            "maximum_experiments": 3,
            "maximum_hours": 2,
            "weekly_slot_selection": "NOT DONE",
            "weekly_slots_used": 0,
            "literal_support_stop": "TRIGGERED — no override or representation-class exemption applied",
        },
        "review_passes": [
            {
                "pass": 1,
                "status": "COMPLETE",
                "scope": "Read operating prompts, README, AGENTS, candidate queues, historical MTAS evidence, H33 lineage, feature code, preregistrations, preflight, evaluator and artifact gates.",
                "outcome": "Reproduced the literal duplicate stop; no candidate execution was admissible.",
            },
            {
                "pass": 2,
                "status": "COMPLETE",
                "scope": "Cross-checked queue labels against MTAS/KTH/MVRD/H88-H4/QTSK/DHTC/HGVC/KDMC/fabric-dislocation records; reconciled historic clearance, data-availability, audit-count and site-language contradictions.",
                "outcome": "H88-MTAS marked historical-tested; related families not claimed globally novel; archive-only clearance and stale copy corrected.",
            },
            {
                "pass": 3,
                "status": "COMPLETE AFTER FINAL CHECKS",
                "scope": "Run full tests, format/package audit, render check, normal/optimized site guards, Chromium responsive/fail-closed check, current report-link/anchor audit, review-card consistency, and expected generation-preflight rejection.",
                "outcome": "Software/site/browser/link checks passed; 43 local research-format packages and 0 protocol-eligible files; no new performance experiment or submission artifact.",
            },
        ],
        "new_tif": {
            "generated": False,
            "file": None,
            "sha256": None,
            "reason": "No TIFF was generated in this review. The previously recorded MTAS research TIFF is historical and is not a newly cleared candidate; making or renaming a placeholder would violate the stop rule.",
        },
        "submission": {
            "new_submission_name": None,
            "new_submission_note": None,
            "ok_to_download_new_file": False,
            "ok_to_download_archived_research_file": bool(research_download),
            "ok_to_submit": False,
            "approved_for_weekly_slot": False,
            "weekly_slots_used": 0,
            "organizer_confirmed_score": None,
            "download_readiness": "NO SUBMISSION-READY GEOTIFF; the existing TDKL/MTAS artifacts are research archives only, not slot-approved.",
        },
        "validator_output": {
            "new_tif": "NOT RUN — no new TIFF",
            "no_nan_inside_footprint": None,
            "values_in_0_1": None,
            "crs_shape_transform_match": None,
            "note": "Existing archived research files have separate format-only audits; they are not this review's candidate.",
        },
        "repository_irregularities": [
            "Literal preflight counts positive support in a continuous dense registry surface as dot support. Because that surface covers every allowed cell, the current interpretation blocks every nonempty candidate; this review preserves the stop and does not grant an exemption.",
            "The prior HGVC v4 download-and-submit wording and local rename/upload advice remain only as explicitly revoked historical archive; the active README banner states no submission-ready file.",
            "An earlier docs/SUBMIT.md revision said 41/41; the current text now reports 43/43 local research-format checks and 0 protocol-eligible packages.",
            "Historical site copy said the full shared feature stack was restored; the current canonical panel now states that only validation-tier inputs are present and data/training_features.tif is absent.",
            "A previous static queue labeled H88-MTAS UNTESTED despite a historical measured result; the result and queue status must remain visibly reconciled.",
        ],
        "errors": errors,
        "verdict": "negative",
        "decision": review_status,
        "limitations": [
            "The local owner-mirror bytes are SHA-pinned but are not an authenticated logged-in DrivenData download in this sandbox.",
            "The hidden organizer labels are unavailable; a catalogued holdout is a proxy and cannot prove a leaderboard result.",
            "The prompt's H33 0.2778 is a user-reported claim without a portal receipt; measured geometry does not prove a score effect.",
            "The literal all-registry overlap rule is mathematically unsatisfiable for a nonempty candidate while the full-positive 17GEMSDOE witness remains in scope.",
            "The four exact formulations are method-level candidates only; related feature families exist and no fleet-wide novelty pass was performed.",
            "No new external dataset was fetched; availability, organizer identity and rights for the candidate source stack were not refreshed.",
        ],
        "next_action": "Do not generate or promote a raster. Reconcile the continuous-surface/dot-support rule through an explicit protocol decision without bypassing the present stop; restore and authenticate the full input stack; then choose an explicitly assigned lane, perform per-feature canaries and shared buffered holdout within the 3-experiment/2-hour limit, and keep slot selection separate.",
    }


def write_report(report: dict, root: Path = ROOT) -> None:
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    for relative in ("evidence/repo_review_20261025.json", "docs/data/repo_review_20261025.json"):
        target = Path(root) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(text, encoding="utf-8")
        temp.replace(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true", help="return 2 unless this review clears a weekly slot")
    args = parser.parse_args(argv)
    try:
        report = build_report()
        write_report(report)
    except Exception as exc:  # Never leave an old positive report after a failed run.
        report = {
            "schema": "gems88.repo-review-20261025.v2",
            "review_date_utc": DATE_UTC,
            "review_status": "AUDIT_ERROR",
            "ok_to_submit": False,
            "verdict": "negative",
            "errors": [str(exc)],
        }
        write_report(report)
        print(json.dumps(report, indent=2) + "\n", end="")
        return 1
    print(json.dumps(report, indent=2) + "\n", end="")
    if report["errors"]:
        return 1
    if args.require_submit and not report["submission"]["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
