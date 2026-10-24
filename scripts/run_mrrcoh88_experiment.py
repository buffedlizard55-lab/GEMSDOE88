#!/usr/bin/env python3
"""Run the one preregistered MRR-COH-88 experiment and publish its gated TIFF.

The experiment is physics-only.  It reuses the shared buffered whole-component
holdout, pooled DTI evaluator, uniqueness implementation, and submission writer.
No competition portal submission is made.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout, grid as grid_mod, holdout, submission_writer, uniqueness, validate  # noqa: E402
from gems88 import adhr, mrr, mrr_coh  # noqa: E402
from gems88.gate import portal_validate  # noqa: E402
from gems88.registry_paths import build_accessible_registry_index  # noqa: E402

PREREG = ROOT / "registry/preregistration_mrrcoh88.json"
CACHE = ROOT / ".cache/gems88-mrrcoh"
SEEDS = (20, 21)
BUFFER_PX = 3
BOUNDARY_PX = 12
BLOCK_SIDE = 200
BOOT_DRAWS = 1000
BOOT_SEED = 882_024
SAMPLE = ROOT / "data/bridge/sample_submission.tif"
FEATURES = ROOT / "data/training_features.tif"
INCUMBENT_RESULT = ROOT / "registry/holdout_result.json"
STEM_PREFIX = "gems88-mrrcoh-persistent-demag-oof-20261024"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def single_feature_canaries(
    matrix: np.ndarray,
    names: list[str],
    grid,
    folds: list[dict],
) -> dict:
    """Audit every candidate feature alone on Seed-20 whole-component truth."""
    truth = np.asarray(folds[0]["hidden_all"], bool)
    visible = np.asarray(folds[0]["visible"], bool)
    region = np.zeros(grid.shape, dtype=bool)
    for fold in folds:
        region |= fold["region"]
    ys, xs = np.nonzero(grid.footprint)
    active_idx = np.flatnonzero((region & ~visible)[ys, xs])
    is_pos = truth[ys[active_idx], xs[active_idx]]
    positives = active_idx[is_pos]
    negatives = active_idx[~is_pos]
    rng = np.random.default_rng(882_024)
    negatives = np.sort(
        rng.choice(negatives, size=min(len(negatives), 8 * len(positives)), replace=False)
    )
    selected = np.concatenate([positives, negatives])
    labels = np.concatenate([
        np.ones(len(positives), dtype=np.int8),
        np.zeros(len(negatives), dtype=np.int8),
    ])
    rows = []
    for col, name in enumerate(names):
        values = np.asarray(matrix[selected, col], np.float32)
        auc = float(roc_auc_score(labels, values)) if float(np.ptp(values)) > 0 else 0.5
        symmetric = max(auc, 1.0 - auc)
        rows.append({
            "feature": name,
            "roc_auc": auc,
            "symmetric_auc": symmetric,
            "withheld_positive_sample": int(len(positives)),
            "negative_sample": int(len(negatives)),
            "threshold": 0.90,
            "pass": bool(symmetric <= 0.90),
        })
    max_row = max(rows, key=lambda row: row["symmetric_auc"])
    return {
        "schema": "gems88.mrrcoh88-canaries.v1",
        "evidence_class": "LEAKAGE-CANARY",
        "method": "Seed-20 buffered whole-component hidden positives versus 8x active off-trace negatives; each feature alone",
        "features_tested": len(rows),
        "threshold": 0.90,
        "max_symmetric_auc": max_row["symmetric_auc"],
        "max_feature": max_row["feature"],
        "passed": bool(max_row["symmetric_auc"] <= 0.90),
        "features": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recompute", action="store_true", help="ignore fold and production checkpoints")
    args = parser.parse_args()
    started = time.monotonic()

    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("MRR-COH preregistration is not frozen")
    if prereg.get("selected_hypothesis") != "MRR-COH-88":
        raise RuntimeError("unexpected selected lane")
    CACHE.mkdir(parents=True, exist_ok=True)
    if args.recompute:
        for path in CACHE.glob("fold_s*_q*.npz"):
            path.unlink()
        (CACHE / "prod_mrrcoh_oof_v1.npz").unlink(missing_ok=True)

    grid = grid_mod.load_grid()
    print("[1/7] Build eight preregistered catalogue-blind features", flush=True)
    x_mrr, mrr_names, mrr_meta = mrr.build_or_load_mrr_memmap(FEATURES, grid.footprint, CACHE)
    x_coh, coh_names, coh_meta = mrr_coh.build_or_load_mrr_coh_memmap(
        FEATURES, grid.footprint, x_mrr, CACHE
    )
    matrix = mrr.StackedFeatureView([x_mrr, x_coh])
    names = list(mrr_names) + list(coh_names)
    if names != list(mrr_coh.ALL_MRR_COH_FEATURES) or matrix.shape[1] != 8:
        raise AssertionError("MRR-COH feature contract mismatch")

    folds_by_seed: list[tuple[int, list[dict]]] = []
    quadrant_ids = None
    for seed in SEEDS:
        folds, quadrant = holdout.buffered_component_draw(
            grid, seed=seed, buffer_px=BUFFER_PX, boundary_px=BOUNDARY_PX
        )
        folds_by_seed.append((seed, folds))
        if quadrant_ids is None:
            quadrant_ids = quadrant
        elif not np.array_equal(quadrant_ids, quadrant):
            raise AssertionError("quadrant partition changed by seed")

    canaries = single_feature_canaries(matrix, names, grid, folds_by_seed[0][1])
    write_json(ROOT / "evidence/mrrcoh88_canaries.json", canaries)
    if not canaries["passed"]:
        raise SystemExit(
            f"STOP leakage canary {canaries['max_feature']}={canaries['max_symmetric_auc']:.6f} > 0.90"
        )
    print(
        f"      PASS {len(names)}/{len(names)}; max symmetric AUC "
        f"{canaries['max_symmetric_auc']:.6f} ({canaries['max_feature']})",
        flush=True,
    )

    print("[2/7] Evaluate 8 spatially blocked hide-and-recover folds", flush=True)
    terms = None
    fold_rows = []
    for seed, folds in folds_by_seed:
        for fold in folds:
            q = int(fold["fold"])
            checkpoint = CACHE / f"fold_s{seed}_q{q}.npz"
            if checkpoint.is_file() and not args.recompute:
                saved = np.load(checkpoint, allow_pickle=False)
                block_terms = saved["block_terms"]
                row = json.loads(str(saved["row_json"]))
            else:
                train_regions = np.zeros(grid.shape, dtype=bool)
                train_truth = np.zeros(grid.shape, dtype=bool)
                for other in folds:
                    if int(other["fold"]) != q:
                        train_regions |= other["region"]
                        train_truth |= other["truth"]
                prediction, _surface, allocation = adhr.predict_cgo_fold(
                    grid,
                    matrix,
                    fold["visible"],
                    train_regions,
                    train_truth,
                    fold["region"],
                    seed=882_100 + seed * 10 + q,
                    min_visible_distance_px=3.0,
                )
                score, block_terms = evaluate_holdout.evaluate(
                    prediction, fold, grid.footprint, block_side=BLOCK_SIDE
                )
                row = {
                    "seed": seed,
                    "fold": fold["name"],
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": evaluate_holdout.VERSION,
                    "withheld_positive_pixels": int(score["n_truth"]),
                    "dti": float(score["dti"]),
                    "emitted": int(score["emitted"]),
                    "allocation": allocation,
                }
                np.savez_compressed(
                    checkpoint,
                    block_terms=block_terms,
                    row_json=np.array(json.dumps(row)),
                )
                del prediction, _surface
                gc.collect()
            terms = block_terms if terms is None else terms + block_terms
            fold_rows.append(row)
            print(
                f"      seed={seed} {fold['name']} DTI={row['dti']:.5f} "
                f"truth={row['withheld_positive_pixels']} emitted={row['emitted']}",
                flush=True,
            )
    if terms is None:
        raise AssertionError("no holdout terms")
    holdout_summary = evaluate_holdout.pooled_summary(
        {"candidate": terms}, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate="candidate"
    )
    holdout_summary["folds"] = fold_rows
    holdout_summary["split"] = "buffered-whole-components-loqo-v2; seeds 20+21"
    candidate_score = holdout_summary["scores"]["candidate"]
    incumbent = json.loads(INCUMBENT_RESULT.read_text(encoding="utf-8"))["scores"]["candidate"]
    comparable = (
        incumbent["evaluator_version"] == candidate_score["evaluator_version"]
        and incumbent["withheld_positive_pixels"] == candidate_score["withheld_positive_pixels"]
    )
    beat_incumbent = bool(comparable and candidate_score["dti"] > incumbent["dti"])
    holdout_summary["stored_same_split_incumbent"] = incumbent
    holdout_summary["same_split_and_evaluator"] = comparable
    holdout_summary["candidate_exceeds_stored_incumbent"] = beat_incumbent
    holdout_summary["paired_difference"] = None
    holdout_summary["paired_difference_reason"] = (
        "Stored incumbent block terms are absent. A point-estimate win would require recomputation before promotion."
    )
    write_json(ROOT / "evidence/mrrcoh88_holdout.json", holdout_summary)
    print(
        f"      HOLDOUT-DTI={candidate_score['dti']:.6f} CI={candidate_score['ci95']} "
        f"n={candidate_score['withheld_positive_pixels']}; stored best={incumbent['dti']:.6f}",
        flush=True,
    )

    print("[3/7] Assemble SHA-verified expanded registry", flush=True)
    registry_index = build_accessible_registry_index(exclude=(STEM_PREFIX,))
    write_json(ROOT / "registry/mrrcoh88_accessible_registry.json", registry_index)
    print(f"      {len(registry_index['rasters'])} accessible raster paths", flush=True)

    print("[4/7] Fit strict-quadrant-OOF production surface; gate before placement", flush=True)
    surface_holder: dict[str, Any] = {}

    def preplacement_gate(surface: np.ndarray) -> None:
        audit = uniqueness.compare_array_to_registry(
            surface,
            registry_index,
            grid.footprint,
            include_reverse=False,
            expected_grid=(grid.shape, grid.crs, grid.transform),
        )
        write_json(ROOT / "evidence/mrrcoh88_surface_uniqueness.json", audit)
        rows = [r for r in audit["rows"] if "error" not in r]
        max_row = max(
            (r for r in rows if r.get("spearman_full_footprint") is not None),
            key=lambda r: abs(float(r["spearman_full_footprint"])),
            default=None,
        )
        surface_holder["audit"] = audit
        surface_holder["max_abs_rho"] = (
            abs(float(max_row["spearman_full_footprint"])) if max_row else 0.0
        )
        surface_holder["worst"] = max_row
        if surface_holder["max_abs_rho"] > 0.90:
            raise RuntimeError(f"STOP pre-placement surface duplicate: {max_row}")

    production_dots, production_surface, _m_surface, production_meta = (
        adhr.fit_and_emit_production_physics_oof(
            grid,
            matrix,
            quadrant_ids,
            folds_by_seed,
            CACHE,
            cache_tag="prod_mrrcoh_oof_v1",
            min_catalogue_distance_px=3.0,
            preplacement_gate=preplacement_gate,
        )
    )
    if surface_holder.get("audit") is None:
        raise AssertionError("pre-placement registry gate did not run")
    print(
        f"      pre-placement max |rho|={surface_holder['max_abs_rho']:.6f}; "
        f"allocated {production_meta['n_dots']} dots",
        flush=True,
    )

    print("[5/7] Write and independently reopen TIFF plus one-TIFF ZIP", flush=True)
    pixel_fingerprint = hashlib.sha256(np.ascontiguousarray(production_dots).tobytes()).hexdigest()[:12]
    stem = f"{STEM_PREFIX}-{production_meta['n_dots']}dots-{pixel_fingerprint}-DO-NOT-SUBMIT"
    submission_name = f"GEMSDOE88-MRRCOH-{pixel_fingerprint.upper()}"
    note = (
        f"MRR coherence OOF, {production_meta['n_dots']} dots; HOLDOUT-DTI "
        f"{candidate_score['dti']:.4f}; UNSCORED; DO NOT SUBMIT"
    )
    if len(note) > 140:
        raise AssertionError(f"note is {len(note)} characters")
    output = ROOT / "docs/downloads" / f"{stem}.tif"
    receipt = submission_writer.write_submission(
        output,
        production_dots.astype(np.float32),
        SAMPLE,
        grid.footprint,
        note=note,
        name=submission_name,
        catalogue=grid.catalogue,
        metadata={
            "lane": "MRR-COH-88",
            "holdout_evaluator": evaluate_holdout.VERSION,
            "holdout_dti": candidate_score["dti"],
            "organizer_confirmed_score": None,
            "slot_authorized": False,
        },
    )
    audit_path = output.with_suffix(".format-audit.json")
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_artifact.py"),
            str(output),
            "--template",
            str(SAMPLE),
            "--output",
            str(audit_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    disk_audit = json.loads(proc.stdout)
    writer_validation = receipt["validator"]
    shared_validation = validate.validate(output, grid.footprint, grid.catalogue)
    zip_validation = portal_validate(output.with_suffix(".zip"), SAMPLE, footprint=grid.footprint)
    format_ok = bool(
        writer_validation["all_checks_passed"]
        and shared_validation["all_checks_passed"]
        and disk_audit["format_valid"]
        and zip_validation["ok"]
    )
    if not format_ok:
        raise RuntimeError("one or more independent TIFF/ZIP validators failed")

    print("[6/7] Audit final dots against every accessible registry raster", flush=True)
    final_audit = uniqueness.compare_to_registry(
        output,
        registry_index,
        grid.footprint,
        include_reverse=True,
        expected_grid=(grid.shape, grid.crs, grid.transform),
    )
    rows_ok = [r for r in final_audit["rows"] if "error" not in r]
    if len(rows_ok) != len(registry_index["rasters"]):
        raise RuntimeError("final registry audit has missing/error rows")
    binding_v3 = uniqueness.binding_duplicate_decision_v3(rows_ok)
    phase_summary = uniqueness.two_phase_summary(
        rows_ok,
        int(grid.footprint.sum()),
        expected_rasters=len(registry_index["rasters"]),
    )
    dot_rows = [
        r for r in rows_ok
        if int(r["their_dots"]) / int(grid.footprint.sum()) <= uniqueness.DENSE_SUPPORT_FRACTION
    ]
    worst_dot = max(dot_rows, key=lambda r: float(r["my_dots_within_3px_of_theirs"]))
    literal_dot_duplicate = bool(float(worst_dot["my_dots_within_3px_of_theirs"]) > 0.70)
    byte_or_pixel_duplicate = any(
        r.get("identical_bytes") or r.get("identical_decoded_predictions") for r in rows_ok
    )
    unique_ok = bool(
        not binding_v3["duplicate"]
        and not literal_dot_duplicate
        and not byte_or_pixel_duplicate
    )
    uniqueness_doc = {
        "schema": "gems88.mrrcoh88-uniqueness.v1",
        "candidate": str(output.relative_to(ROOT)),
        "candidate_sha256": receipt["sha256"],
        "registry_scope": registry_index["scope"],
        "preplacement_max_abs_spearman": surface_holder["max_abs_rho"],
        "preplacement_worst": surface_holder["worst"],
        "binding_v3": binding_v3,
        "literal_dot_field_gate": {
            "support_fraction_max": uniqueness.DENSE_SUPPORT_FRACTION,
            "rasters_checked": len(dot_rows),
            "overlap_limit": 0.70,
            "worst_forward_overlap": float(worst_dot["my_dots_within_3px_of_theirs"]),
            "worst_file": worst_dot["file"],
            "duplicate": literal_dot_duplicate,
        },
        "byte_or_decoded_duplicate": byte_or_pixel_duplicate,
        "unique": unique_ok,
        "two_phase_summary": phase_summary,
        "rows": rows_ok,
    }
    write_json(ROOT / "evidence/mrrcoh88_final_uniqueness.json", uniqueness_doc)

    paired_evidence_ok = False  # no point-estimate win; paired terms therefore not rerun
    holdout_ok = bool(beat_incumbent and paired_evidence_ok)
    verdict = "promote" if (holdout_ok and unique_ok and format_ok) else "negative"
    # Scientific promotion only enters a separate portfolio selector. The
    # experiment runner can never authorize or consume a competition slot.
    ok_to_submit = False
    blockers = []
    if not beat_incumbent:
        blockers.append("HOLDOUT: candidate did not exceed the same-split stored best")
    elif not paired_evidence_ok:
        blockers.append("HOLDOUT: paired incumbent block terms must be recomputed before promotion")
    if not unique_ok:
        blockers.append("UNIQUENESS: final dot field exceeds a binding registry threshold")
    if not format_ok:
        blockers.append("FORMAT: independent TIFF/ZIP validation failed")
    if not blockers:
        blockers.append("none")

    elapsed = time.monotonic() - started
    validator_output = {
        "no_nan_inside_footprint": bool(writer_validation["checks"]["in_footprint_all_finite"]),
        "all_finite_entire_raster": bool(
            writer_validation["checks"]["no_nan_anywhere"]
            and writer_validation["checks"]["no_inf_anywhere"]
        ),
        "values_in_0_1": bool(writer_validation["checks"]["in_footprint_range_0_1"]),
        "crs_shape_transform_match": bool(disk_audit["format_valid"]),
        "single_band_float32": bool(disk_audit["format_valid"]),
        "zip_contains_exactly_one_matching_tiff": bool(zip_validation["ok"]),
        "all_checks_passed": format_ok,
        "format_audit": str(audit_path.relative_to(ROOT)),
    }
    run_card = {
        "schema": "gems88.mrrcoh88-run-card.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_git_sha_at_generation": git_value("rev-parse", "HEAD"),
        "hypothesis": prereg["ranking"][0]["off_catalogue_rationale"],
        "mechanism": prereg["ranking"][0]["physical_signature"],
        "named_non_fault_process": prereg["ranking"][0]["named_non_fault_mimic"],
        "lane": prereg["lane"],
        "holdout_dti": {
            **candidate_score,
            "stored_same_split_best": incumbent,
            "candidate_exceeds_stored_best": beat_incumbent,
            "paired_difference": None,
            "paired_difference_reason": holdout_summary["paired_difference_reason"],
        },
        "correlation_overlap_vs_registry": {
            "registry_rasters_checked": len(rows_ok),
            "preplacement_max_abs_spearman": surface_holder["max_abs_rho"],
            "final_max_abs_spearman": binding_v3["worst_abs_spearman"],
            "final_max_literal_forward_overlap_all": binding_v3["worst_literal_forward_overlap"],
            "final_max_literal_forward_overlap_dot_fields": uniqueness_doc["literal_dot_field_gate"]["worst_forward_overlap"],
            "final_max_excess_overlap": binding_v3["worst_excess_overlap"],
            "rho_limit": 0.90,
            "overlap_limit": 0.70,
            "unique": unique_ok,
            "evidence": "evidence/mrrcoh88_final_uniqueness.json",
        },
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "validator_output": validator_output,
        "submission_name": submission_name,
        "submission_note": note,
        "submission_note_chars": len(note),
        "artifact": str(output.relative_to(ROOT)),
        "zip_artifact": str(output.with_suffix(".zip").relative_to(ROOT)),
        "positive_pixels": int(production_meta["n_dots"]),
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "organizer_confirmed": None,
        "weekly_slots_used": 0,
        "verdict": verdict,
        "blockers": blockers,
        "experiment_count": 1,
        "experiment_cap": 3,
        "wall_seconds": elapsed,
        "wall_cap_seconds": 7200,
        "input_provenance": {
            "sample_submission_sha256": sha256_file(SAMPLE),
            "training_features_sha256": sha256_file(FEATURES),
            "mrr_metadata": mrr_meta,
            "mrr_coherence_metadata": coh_meta,
            "new_external_data": [],
        },
        "production": production_meta,
        "limitations": [
            "Hide-and-recover catalogue labels are a proxy, not undisclosed organizer truth.",
            "Owner-mirrored competition bytes are hash-pinned but not organizer-authenticated in this environment.",
            "The public registry cannot include private, unlinked, or inaccessible submissions.",
            "No DrivenData portal upload or organizer acceptance receipt was created."
        ],
    }
    for path in (
        ROOT / "registry/mrrcoh88_run_card.json",
        ROOT / "docs/data/mrrcoh88_run_card.json",
        ROOT / "evidence/mrrcoh88_run_card.json",
    ):
        write_json(path, run_card)
    current_release = {
        "schema": "gems88.current-release.v2",
        "candidate_id": "MRR-COH-88",
        "artifact": str(output.relative_to(ROOT)),
        "zip_artifact": str(output.with_suffix(".zip").relative_to(ROOT)),
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "format_valid": format_ok,
        "no_nan_inside": validator_output["no_nan_inside_footprint"],
        "all_values_in_0_1": validator_output["values_in_0_1"],
        "crs_shape_transform_match": validator_output["crs_shape_transform_match"],
        "zip_one_exact_tif": validator_output["zip_contains_exactly_one_matching_tiff"],
        "positive_pixels": int(production_meta["n_dots"]),
        "canary_max_auc": canaries["max_symmetric_auc"],
        "holdout_dti": candidate_score["dti"],
        "holdout_ci95": candidate_score["ci95"],
        "holdout_evaluator": candidate_score["evaluator_version"],
        "withheld_positive_pixels": candidate_score["withheld_positive_pixels"],
        "incumbent_best_dti": incumbent["dti"],
        "preplacement_max_abs_spearman": surface_holder["max_abs_rho"],
        "final_max_abs_spearman": binding_v3["worst_abs_spearman"],
        "literal_registry_overlap_all_3px": binding_v3["worst_literal_forward_overlap"],
        "literal_dot_field_overlap_3px": uniqueness_doc["literal_dot_field_gate"]["worst_forward_overlap"],
        "max_excess_overlap_3px": binding_v3["worst_excess_overlap"],
        "registry_rasters_checked": len(rows_ok),
        "unique": unique_ok,
        "duplicate": not unique_ok,
        "research_download_ok": True,
        "ok_to_submit": ok_to_submit,
        "approved_for_weekly_slot": False,
        "verdict": verdict,
        "status_label": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT",
        "reason": "; ".join(blockers),
        "provenance": "hash-pinned owner-mirrored inputs; organizer authentication unavailable",
    }
    write_json(ROOT / "docs/data/current_release.json", current_release)
    write_json(
        ROOT / "docs/status.json",
        {
            "evidence_schema_complete": True,
            "approved_for_weekly_slot": False,
            "status": "SELECTOR_REQUIRED" if verdict == "promote" else "BLOCKED",
            "problems": [] if verdict == "promote" else blockers,
            "ok_to_download_for_research": True,
            "ok_to_submit": False,
            "raster_sha256": receipt["sha256"],
            "policy": "mrrcoh88-expanded-registry-v1",
        },
    )
    receipt_path = output.with_suffix(".json")
    disk_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    disk_receipt.update({
        "approved_for_weekly_slot": ok_to_submit,
        "promoted": verdict == "promote",
        "status": current_release["status_label"],
        "run_card": "../data/mrrcoh88_run_card.json",
    })
    write_json(receipt_path, disk_receipt)

    print("[7/7] COMPLETE", flush=True)
    print(json.dumps({
        "artifact": str(output.relative_to(ROOT)),
        "sha256": receipt["sha256"],
        "HOLDOUT-DTI": candidate_score,
        "stored_best_HOLDOUT-DTI": incumbent,
        "canary_max_symmetric_auc": canaries["max_symmetric_auc"],
        "preplacement_max_abs_rho": surface_holder["max_abs_rho"],
        "final_literal_dot_overlap": uniqueness_doc["literal_dot_field_gate"]["worst_forward_overlap"],
        "final_excess_overlap": binding_v3["worst_excess_overlap"],
        "unique": unique_ok,
        "format_valid": format_ok,
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "blockers": blockers,
        "wall_seconds": elapsed,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
