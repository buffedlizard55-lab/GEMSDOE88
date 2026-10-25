#!/usr/bin/env python3
"""Run the single preregistered H88-MRR-BPR experiment and emit a negative-safe TIFF.

Protocol invariants:
* one candidate experiment (incumbent H88-ADHR is a recomputed control);
* unmodified gems57 whole-component holdout/evaluator/writer/uniqueness tools;
* four single-feature leakage canaries before model fitting;
* pre-placement surface Spearman audit before Dinkelbach dot placement;
* literal all-raster final overlap gate with no dense-prior exemption;
* locally valid GeoTIFF is still emitted as a negative deliverable, but its
  `DO-NOT-SUBMIT` name and machine status prevent accidental slot use.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import argparse
import gc
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout, grid as grid_mod, holdout, submission_writer, uniqueness, validate  # noqa: E402
from gems88 import adhr, edge, mrr, physics  # noqa: E402

PREREG = ROOT / "registry/preregistration_mrr88.json"
INVENTORY = ROOT / "registry/inventory.json"
CACHE = ROOT / ".cache/gems88-mrr"
SEEDS = (20, 21)
BUFFER_PX = 3
BOUNDARY_PX = 12
BLOCK_SIDE = 200
BOOT_DRAWS = 1000
BOOT_SEED = 881024
STEM = "gems88-mrr-bpr-blockresid-dinkelbach-20261024-v1-DO-NOT-SUBMIT"
SUBMISSION_NAME = "GEMSDOE88-MRR-BPR-20261024-DO-NOT-SUBMIT"


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


def canary_rows(X_mrr: np.ndarray, names: list[str], g, folds: list[dict]) -> list[dict[str, Any]]:
    """Single-channel Seed-20 symmetric AUC on whole-component hidden positives."""
    visible = folds[0]["visible"]
    truth = np.zeros(g.shape, dtype=bool)
    regions = np.zeros(g.shape, dtype=bool)
    for fold in folds:
        truth |= fold["truth"]
        regions |= fold["region"]
    ys, xs = np.nonzero(g.footprint)
    active = regions & ~visible
    active_idx = np.flatnonzero(active[ys, xs])
    t = truth[ys[active_idx], xs[active_idx]]
    positives = active_idx[t]
    negatives = active_idx[~t]
    rng = np.random.default_rng(881024)
    negatives = rng.choice(negatives, size=min(len(negatives), 8 * len(positives)), replace=False)
    sel = np.concatenate([positives, negatives])
    y = np.concatenate([np.ones(len(positives), np.int8), np.zeros(len(negatives), np.int8)])
    rows = []
    for col, name in enumerate(names):
        v = np.asarray(X_mrr[sel, col], np.float32)
        auc = float(roc_auc_score(y, v)) if float(np.ptp(v)) > 0 else 0.5
        sym = max(auc, 1.0 - auc)
        rows.append({
            "feature": name,
            "roc_auc": round(auc, 6),
            "symmetric_auc": round(sym, 6),
            "withheld_positive_sample": int(len(positives)),
            "negative_sample": int(len(negatives)),
            "threshold": 0.90,
            "pass": bool(sym <= 0.90),
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recompute", action="store_true", help="ignore fold checkpoints and rerun both arms")
    args = ap.parse_args()
    t0 = time.monotonic()
    if not PREREG.is_file():
        raise FileNotFoundError(f"frozen preregistration missing: {PREREG}")
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("preregistration is not marked frozen")

    CACHE.mkdir(parents=True, exist_ok=True)
    g = grid_mod.load_grid()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    feature_path = ROOT / "data/training_features.tif"

    print("[1/7] Build cached baseline + MRR features and exact holdout geometry", flush=True)
    X_phys, band_tags, ext_hashes = physics.build_or_load_physics_memmap(ROOT, g, ROOT / ".cache/gems88")
    X_mrr, mrr_names, mrr_meta = mrr.build_or_load_mrr_memmap(feature_path, g.footprint, CACHE)
    X_aug = mrr.StackedFeatureView([X_phys, X_mrr])
    if X_aug.shape[1] != len(physics.ALL_PHYS_FEATURES) + len(mrr.MRR_FEATURES):
        raise AssertionError("augmented feature width mismatch")

    folds_by_seed: list[tuple[int, list[dict], np.ndarray]] = []
    for seed in SEEDS:
        folds, quad = holdout.buffered_component_draw(
            g, seed=seed, buffer_px=BUFFER_PX, boundary_px=BOUNDARY_PX
        )
        folds_by_seed.append((seed, folds, quad))

    canaries = canary_rows(X_mrr, mrr_names, g, folds_by_seed[0][1])
    max_canary = max(r["symmetric_auc"] for r in canaries)
    canary_doc = {
        "schema": "gems88.mrr88-canaries.v1",
        "evidence_class": "LEAKAGE-CANARY",
        "method": "Seed-20 whole-component hidden positives vs 8x active off-trace negatives; each MRR channel alone",
        "threshold": 0.90,
        "features_tested": len(canaries),
        "max_symmetric_auc": max_canary,
        "passed": bool(max_canary <= 0.90),
        "features": canaries,
    }
    write_json(ROOT / "evidence/mrr88_canaries.json", canary_doc)
    if not canary_doc["passed"]:
        raise SystemExit(f"STOP: MRR leakage canary {max_canary:.6f} > 0.90")
    print(f"      Canary PASS: {len(canaries)}/{len(canaries)}, max symmetric AUC={max_canary:.6f}", flush=True)

    print("[2/7] Build fold-visible structural frames", flush=True)
    with rasterio.open(feature_path) as ds:
        det_elev = edge.clean_band(ds.read(12), g.footprint)[0]
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, ROOT / ".cache/gems88")
    del det_elev
    sense_src = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)
    vis_cache: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for seed, folds, _ in folds_by_seed:
        vis_cache[seed] = adhr.compute_visible_struct_fp(
            g, folds[0]["visible"], sense_src, scarp_fields, ROOT / ".cache/gems88", f"seed{seed}"
        )
    _ = adhr.compute_visible_struct_fp(
        g, g.catalogue, sense_src, scarp_fields, ROOT / ".cache/gems88", "prod_fullcat"
    )

    print("[3/7] Recompute incumbent and candidate on identical 8 buffered whole-component folds", flush=True)
    terms: dict[str, np.ndarray | None] = {"h88_adhr_incumbent": None, "mrr_bpr_candidate": None}
    fold_rows: list[dict[str, Any]] = []
    blind_terms = {k: np.zeros(4, dtype=np.float64) for k in terms}
    for seed, folds, quad in folds_by_seed:
        X_v22, d_vis_fp, comp_len_fp = vis_cache[seed]
        d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
        for fold in folds:
            q = int(fold["fold"])
            ckpt = CACHE / f"fold_s{seed}_q{q}.npz"
            if ckpt.is_file() and not args.recompute:
                z = np.load(ckpt, allow_pickle=False)
                row = json.loads(str(z["row_json"]))
                for arm in terms:
                    bt = z[f"bt_{arm}"]
                    terms[arm] = bt if terms[arm] is None else terms[arm] + bt
                    blind_terms[arm] += z[f"blind_{arm}"]
                fold_rows.append(row)
                print(f"      [ckpt] seed={seed} {fold['name']} cand={row['mrr_bpr_candidate']['dti']:.5f}", flush=True)
                continue

            train_regions = np.zeros(g.shape, dtype=bool)
            train_truth = np.zeros(g.shape, dtype=bool)
            for other in folds:
                if int(other["fold"]) != q:
                    train_regions |= other["region"]
                    train_truth |= other["truth"]
            test_region = fold["region"]
            visible = fold["visible"]
            run_seed = 88_100 + seed * 10 + q

            incumbent, _, inc_meta = adhr.predict_adhr_fold(
                g, X_phys, X_v22, d_vis_fp, comp_len_fp, visible,
                train_regions, train_truth, test_region, seed=run_seed
            )
            candidate, _, cand_meta = adhr.predict_adhr_fold(
                g, X_aug, X_v22, d_vis_fp, comp_len_fp, visible,
                train_regions, train_truth, test_region, seed=run_seed
            )

            row: dict[str, Any] = {
                "seed": seed,
                "fold": fold["name"],
                "withheld_positive_pixels": int((fold["truth"] & test_region & ~fold["masked_known"]).sum()),
            }
            bt_fold: dict[str, np.ndarray] = {}
            blind_fold: dict[str, np.ndarray] = {}
            for arm, pred, meta in (
                ("h88_adhr_incumbent", incumbent, inc_meta),
                ("mrr_bpr_candidate", candidate, cand_meta),
            ):
                score, bt = evaluate_holdout.evaluate(pred, fold, g.footprint, block_side=BLOCK_SIDE)
                terms[arm] = bt if terms[arm] is None else terms[arm] + bt
                bt_fold[arm] = bt
                row[arm] = {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": evaluate_holdout.VERSION,
                    "dti": round(float(score["dti"]), 6),
                    "emitted": int(score["emitted"]),
                }
                far_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
                far_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
                _, far_bt = evaluate_holdout.evaluate(
                    pred,
                    {**fold, "truth": far_truth, "region": far_valid, "masked_known": np.zeros_like(far_valid)},
                    g.footprint,
                    block_side=BLOCK_SIDE,
                )
                far_total = far_bt.sum(axis=0)
                blind_terms[arm] += far_total
                blind_fold[arm] = far_total
            fold_rows.append(row)
            np.savez_compressed(
                ckpt,
                row_json=np.array(json.dumps(row)),
                **{f"bt_{k}": v for k, v in bt_fold.items()},
                **{f"blind_{k}": v for k, v in blind_fold.items()},
            )
            print(
                f"      seed={seed} {fold['name']:>2s} incumbent={row['h88_adhr_incumbent']['dti']:.5f} "
                f"candidate={row['mrr_bpr_candidate']['dti']:.5f}",
                flush=True,
            )
            del incumbent, candidate
            gc.collect()

    if any(v is None for v in terms.values()):
        raise AssertionError("missing pooled holdout terms")
    summary = evaluate_holdout.pooled_summary(
        terms, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate="mrr_bpr_candidate"
    )
    summary["folds"] = fold_rows
    summary["blind_basin_gt_25px"] = {}
    for arm, vals in blind_terms.items():
        summary["blind_basin_gt_25px"][arm] = {
            "evidence_class": "HOLDOUT-DTI-SUBSET",
            "evaluator_version": evaluate_holdout.VERSION,
            "distance_from_visible_fault_px": ">25",
            "withheld_positive_pixels": int(round(vals[3])),
            "dti": round(float(evaluate_holdout.from_terms(vals)), 6),
        }
    write_json(ROOT / "evidence/mrr88_holdout.json", summary)
    cand_score = summary["scores"]["mrr_bpr_candidate"]
    inc_score = summary["scores"]["h88_adhr_incumbent"]
    paired = summary["paired_differences"]["h88_adhr_incumbent"]
    beat_incumbent = bool(cand_score["dti"] > inc_score["dti"])
    print(
        f"      HOLDOUT-DTI candidate={cand_score['dti']:.6f} CI={cand_score['ci95']} "
        f"incumbent={inc_score['dti']:.6f}; paired delta={paired['delta']:+.6f} CI={paired['ci95']}",
        flush=True,
    )

    print("[4/7] Fit production candidate; run surface audit BEFORE dot placement", flush=True)
    surface_audit_holder: dict[str, Any] = {}

    def preplacement_gate(surface: np.ndarray) -> None:
        audit = uniqueness.compare_array_to_registry(
            surface,
            inventory,
            g.footprint,
            include_reverse=False,
            expected_grid=(g.shape, g.crs, g.transform),
        )
        surface_audit_holder["audit"] = audit
        write_json(ROOT / "evidence/mrr88_surface_uniqueness.json", audit)
        rank_flags = [
            r for r in audit["rows"]
            if "error" not in r and r.get("spearman_full_footprint") is not None
            and abs(float(r["spearman_full_footprint"])) > 0.90
        ]
        if rank_flags:
            raise RuntimeError(f"STOP: pre-placement surface rank duplicate: {rank_flags[0]}")

    folds_only = [(seed, folds) for seed, folds, _ in folds_by_seed]
    prod_dots, prod_surface, _, prod_meta = adhr.fit_and_emit_production_adhr(
        g,
        X_aug,
        folds_only,
        sense_src,
        scarp_fields,
        ROOT / ".cache/gems88",
        cache_tag="prod_mrr_bpr_20261024_v1",
        preplacement_gate=preplacement_gate,
    )
    del X_aug, X_mrr, X_phys, vis_cache
    gc.collect()

    print("[5/7] Write all-finite single-band GeoTIFF and one-TIFF ZIP", flush=True)
    docs_dl = ROOT / "docs/downloads"
    docs_dl.mkdir(parents=True, exist_ok=True)
    tif_path = docs_dl / f"{STEM}.tif"
    for suffix in (".tif", ".zip", ".json", ".format-audit.json"):
        (docs_dl / f"{STEM}{suffix}").unlink(missing_ok=True)
    note = (
        f"MRR88 block-VG residual+demag trough; {int(prod_meta['n_dots'])} dots; "
        f"HOLDOUT-DTI {cand_score['dti']:.4f}; literal registry overlap blocks submit"
    )
    if len(note) > 140:
        raise AssertionError(f"submission note too long ({len(note)}): {note}")
    receipt = submission_writer.write_submission(
        tif_path,
        prod_dots,
        ROOT / "data/bridge/sample_submission.tif",
        g.footprint,
        note=note,
        name=SUBMISSION_NAME,
        catalogue=g.catalogue,
        metadata={
            "lane": "H88-MRR-BPR",
            "holdout_evaluator": evaluate_holdout.VERSION,
            "holdout_dti": cand_score["dti"],
            "organizer_confirmed_score": None,
        },
    )
    format_audit_path = docs_dl / f"{STEM}.format-audit.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_artifact.py"), str(tif_path),
         "--template", str(ROOT / "data/bridge/sample_submission.tif"),
         "--output", str(format_audit_path)],
        check=True, capture_output=True, text=True,
    )
    format_audit = json.loads(proc.stdout)
    local_validation = validate.validate(tif_path, g.footprint, g.catalogue)
    if not receipt["validator"]["all_checks_passed"] or not local_validation["all_checks_passed"] or not format_audit["format_valid"]:
        raise RuntimeError("saved artifact failed one or more independent format validators")

    print("[6/7] Apply literal final-dot registry gate (no continuous-surface exemption)", flush=True)
    final_audit = uniqueness.compare_to_registry(
        tif_path,
        inventory,
        g.footprint,
        include_reverse=True,
        expected_grid=(g.shape, g.crs, g.transform),
    )
    two_phase = uniqueness.two_phase_summary(
        final_audit["rows"], int(g.footprint.sum()), expected_rasters=len(inventory["rasters"])
    )
    binding = uniqueness.binding_duplicate_decision(final_audit["rows"])
    witness = uniqueness.saturation_certificate(
        ROOT / "data/registry/dense_17gemdoe.tif",
        g.footprint,
        g.catalogue,
        expected_grid=(g.shape, g.crs, g.transform),
    )
    write_json(ROOT / "evidence/mrr88_final_uniqueness.json", final_audit)
    write_json(ROOT / "evidence/mrr88_two_phase_uniqueness.json", two_phase)
    write_json(ROOT / "evidence/mrr88_witness.json", witness)

    rows_ok = [r for r in final_audit["rows"] if "error" not in r]
    max_abs_rho = max(abs(float(r["spearman_full_footprint"])) for r in rows_ok if r.get("spearman_full_footprint") is not None)
    max_overlap = max(float(r["my_dots_within_3px_of_theirs"]) for r in rows_ok)
    sparse_rows = [r for r in rows_ok if int(r["their_dots"]) / int(g.footprint.sum()) <= 0.20]
    max_sparse_overlap = max(float(r["my_dots_within_3px_of_theirs"]) for r in sparse_rows)
    max_surface_rho = max(
        abs(float(r["spearman_full_footprint"]))
        for r in surface_audit_holder["audit"]["rows"]
        if "error" not in r and r.get("spearman_full_footprint") is not None
    )
    literal_duplicate = bool(binding["duplicate"])
    verdict = "negative" if (literal_duplicate or not beat_incumbent) else "promote"
    ok_to_submit = bool(verdict == "promote")
    # The known universal witness makes this false for every nonempty artifact.
    if ok_to_submit:
        raise AssertionError("unexpected promotion despite literal universal witness")

    cached_verification_seconds = round(time.monotonic() - t0, 2)
    # Conservative, reproducible budget clock: preregistration freeze through
    # first production-cache completion.  It survives a later cached audit rerun.
    prod_cache = ROOT / ".cache/gems88/prod_mrr_bpr_20261024_v1.npz"
    frozen_to_production_seconds = round(
        max(0.0, prod_cache.stat().st_mtime - PREREG.stat().st_mtime), 2
    )
    run_card = {
        "schema": "gems88.run-card.v3",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_git_sha_at_generation": git_value("rev-parse", "HEAD"),
        "lane": "H88-MRR-BPR",
        "artifact": f"docs/downloads/{tif_path.name}",
        "zip_artifact": f"docs/downloads/{tif_path.with_suffix('.zip').name}",
        "downloadable_file": f"downloads/{tif_path.name}",
        "submission_name": SUBMISSION_NAME,
        "submission_note": note,
        "emitted_dots": int(prod_meta["n_dots"]),
        "ok_to_download": True,
        "ok_to_submit": False,
        "independent_organizer_receipt": False,
        "weekly_slots_used": 0,
        "hypothesis": prereg["selected_hypothesis"],
        "mechanism": prereg["selected_hypothesis"]["mechanism"],
        "named_non_fault_process": prereg["selected_hypothesis"]["named_non_fault_mimic"],
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "withheld_positive_pixels": cand_score["withheld_positive_pixels"],
            "candidate": cand_score["dti"],
            "ci95": cand_score["ci95"],
            "incumbent_recomputed": inc_score["dti"],
            "incumbent_ci95": inc_score["ci95"],
            "paired_delta_vs_incumbent": paired["delta"],
            "paired_delta_ci95": paired["ci95"],
            "beat_current_holdout_best": beat_incumbent,
            "blind_basin_gt_25px": summary["blind_basin_gt_25px"],
        },
        "organizer_confirmed": {
            "score": None,
            "receipt": None,
            "weekly_slots_used": 0,
        },
        "leakage_canary": canary_doc,
        "correlation_overlap_vs_registry": {
            "inventory": "registry/inventory.json",
            "rasters_checked": len(rows_ok),
            "surface_preplacement_max_abs_spearman": round(max_surface_rho, 6),
            "surface_limit": 0.90,
            "final_max_abs_spearman": round(max_abs_rho, 6),
            "final_max_forward_overlap_3px_all_rasters": round(max_overlap, 6),
            "final_max_forward_overlap_3px_sparse_rasters": round(max_sparse_overlap, 6),
            "overlap_limit": 0.70,
            "literal_binding_decision": binding,
            "universal_witness": witness,
        },
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "validator_output": {
            "no_nan_inside_footprint": bool(receipt["validator"]["checks"]["in_footprint_all_finite"]),
            "all_finite_entire_raster": bool(
                receipt["validator"]["checks"]["no_nan_anywhere"]
                and receipt["validator"]["checks"]["no_inf_anywhere"]
            ),
            "values_in_0_1": bool(receipt["validator"]["checks"]["in_footprint_range_0_1"]),
            "crs_shape_transform_match": bool(format_audit["format_valid"]),
            "single_band_float32": bool(format_audit["format_valid"]),
            "all_checks_passed": True,
            "format_audit": f"docs/downloads/{format_audit_path.name}",
        },
        "submission": {
            "file": f"docs/downloads/{tif_path.name}",
            "zip": f"docs/downloads/{tif_path.with_suffix('.zip').name}",
            "name": SUBMISSION_NAME,
            "note": note,
            "note_chars": len(note),
            "positive_pixels": int(prod_meta["n_dots"]),
            "ok_to_download": True,
            "ok_to_submit": ok_to_submit,
            "status_label": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT",
        },
        "verdict": verdict,
        "stop_reason": (
            "Literal 3-pixel overlap gate fires on the all-positive 17GEMSDOE registry witness "
            "(overlap 1.0 > 0.70); no continuous-surface exemption is authorized."
            if literal_duplicate else
            "Candidate failed to exceed the recomputed incumbent HOLDOUT-DTI."
        ),
        "budget": {
            "candidate_experiments_run": 1,
            "candidate_experiment_cap": 3,
            "experiments_run": 1,
            "wall_seconds": frozen_to_production_seconds,
            "wall_measurement": "preregistration file mtime through first production-cache completion",
            "cached_full_audit_rerun_seconds": cached_verification_seconds,
            "wall_cap_seconds": 7200,
            "weekly_slots_used": 0,
            "organizer_confirmed_score": None,
        },
        "input_provenance": {
            "training_features_sha256": sha256_file(feature_path),
            "verified_competition_band_tags": mrr_meta["verified_band_tags"],
            "baseline_band_tags": band_tags,
            "external_baseline_hashes": ext_hashes,
            "new_external_data": [],
            "mrr_feature_cache_metadata": mrr_meta,
        },
    }
    for out in (
        ROOT / "registry/run_card_mrr88.json",
        ROOT / "evidence/run-card-mrr88.json",
        ROOT / "docs/data/run-card-mrr88.json",
        ROOT / "docs/run_card_mrr88.json",
        ROOT / "registry/run_card.json",
        ROOT / "evidence/run-card.json",
        ROOT / "docs/data/run-card.json",
        ROOT / "docs/run_card.json",
    ):
        write_json(out, run_card)
    write_json(
        ROOT / "docs/status_mrr88.json",
        {
            "evidence_schema_complete": True,
            "approved_for_weekly_slot": False,
            "status": "BLOCKED",
            "problems": [run_card["stop_reason"]],
            "ok_to_download_for_research": True,
            "ok_to_submit": False,
            "raster_sha256": receipt["sha256"],
        },
    )
    # Mirror the explicit status into the writer receipt without claiming approval.
    receipt_path = tif_path.with_suffix(".json")
    disk_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    disk_receipt.update({
        "approved_for_weekly_slot": False,
        "promoted": False,
        "status": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT; literal registry witness duplicate",
        "run_card": "../data/run-card.json",
    })
    write_json(receipt_path, disk_receipt)

    print("[7/7] COMPLETE", flush=True)
    print(json.dumps({
        "file": str(tif_path.relative_to(ROOT)),
        "sha256": receipt["sha256"],
        "holdout_dti": cand_score,
        "paired_delta": paired,
        "surface_max_abs_rho": max_surface_rho,
        "final_max_overlap_all": max_overlap,
        "final_max_overlap_sparse": max_sparse_overlap,
        "validator_pass": True,
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": verdict,
        "wall_seconds": frozen_to_production_seconds,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
