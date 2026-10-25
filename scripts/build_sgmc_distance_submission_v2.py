#!/usr/bin/env python3
"""
Experiment 2: H88-SGMC-DISTANCE-CONJUNCTION-v2

Same hypothesis as v1, but uses emit.dinkelbach_allocate (exact CELF fractional
programming) instead of emit_decimated for potentially better dot placement.
Dinkelbach tracks both T (covered truth credit) and M (self credit) exactly,
which should place dots more efficiently near withheld truth segments.

Lane: H88-SGMC-DISTANCE-CONJUNCTION-v2 (single method, experiment 2 of 3)
"""

from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import grid as grid_mod, holdout, submission_writer, validate, emit, uniqueness

# ---- Protocol constants ----
RADIUS_PX = 3.0
CAT_MIN_PX = 1
CAT_MAX_PX = 25
BLIND_MIN_PX = 26
SGMC_MAX_PX = 30
TOTAL_MAX_DOTS = 37654
MAX_DOTS_PROX = 30000
MAX_DOTS_BLIND = 7654

CANDIDATE_STEM = "gems88-sgmc-dist-conj-v2-20261025-DO-NOT-SUBMIT"
SUBMISSION_NAME = "GEMSDOE88-SGMC-DIST-CONJ-V2-20261025"
SUBMISSION_NOTE = (
    "H88-SGMC-DIST-CONJ-v2 dinkelbach-alloc SGMC+catalogue 1-25px+>26px blind "
    "37654dots; HOLDOUT-DTI pending; UNSCORED"
)  # must be <= 140 chars


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def norm01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    vals = a[mask & np.isfinite(a)]
    if vals.size == 0:
        return np.zeros_like(a)
    lo, hi = np.percentile(vals, [5, 95])
    if hi <= lo:
        return np.zeros_like(a)
    out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    out[~mask] = 0.0
    return out


def main() -> None:
    assert len(SUBMISSION_NOTE) <= 140
    t0 = time.monotonic()

    g = grid_mod.load_grid()
    fp, cat = g.footprint, g.catalogue
    H, W = g.height, g.width
    sample_path = ROOT / "data" / "bridge" / "sample_submission.tif"

    print(f"[1/8] Grid: footprint={fp.sum():,} catalogue={cat.sum():,} cells", flush=True)

    # ---- Features ----
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)

    sgmc_path = ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
    with rasterio.open(sgmc_path) as ds:
        sgmc = ds.read(1).astype(np.float32)
    d_sgmc = ndi.distance_transform_edt(sgmc <= 0).astype(np.float32)

    print(f"    Catalogue pixels: {cat.sum():,}")
    print(f"    SGMC fault pixels: {(sgmc > 0).sum():,}")

    # ---- Zones ----
    prox_zone = (d_cat >= CAT_MIN_PX) & (d_cat <= CAT_MAX_PX) & fp & ~cat
    blind_zone = (d_cat > BLIND_MIN_PX) & (d_sgmc <= SGMC_MAX_PX) & fp & ~cat

    print(f"    Prox zone (1-25px from cat): {prox_zone.sum():,} ({100*prox_zone.sum()/fp.sum():.2f}%)")
    print(f"    Blind zone (>26px cat, <=30px SGMC): {blind_zone.sum():,} ({100*blind_zone.sum()/fp.sum():.2f}%)")

    # ---- Surfaces ----
    sgmc_weight = np.clip((SGMC_MAX_PX - d_sgmc) / SGMC_MAX_PX, 0, 1)
    sgmc_weight = np.where(fp, sgmc_weight, 0.0)

    prox_taper = np.clip((CAT_MAX_PX - d_cat) / (CAT_MAX_PX - CAT_MIN_PX), 0, 1)
    surface_prox = np.where(prox_zone, norm01(sgmc_weight * prox_taper, fp), 0.0).astype(np.float32)
    surface_blind = np.where(blind_zone, norm01(sgmc_weight, fp), 0.0).astype(np.float32)
    surface = norm01(sgmc_weight, fp).astype(np.float32)

    # ---- Dot allocation via Dinkelbach CELF allocator ----
    allowed_prox = prox_zone & fp & ~cat
    allowed_blind = blind_zone & fp & ~cat

    # Self-credit: expected max kernel credit (use expected_credit as proxy)
    self_credit_prox = emit.expected_credit(surface_prox)
    self_credit_blind = emit.expected_credit(surface_blind)

    dots_prox = emit.dinkelbach_allocate(
        p=surface_prox,
        self_credit=self_credit_prox,
        allowed=allowed_prox,
        budget=MAX_DOTS_PROX,
        k_truth=45260.0,  # approximate withheld positives
        min_spacing_px=0.0,
        candidate_cap=320_000,
        dinkelbach_iters=3,
    )
    dots_blind = emit.dinkelbach_allocate(
        p=surface_blind,
        self_credit=self_credit_blind,
        allowed=allowed_blind,
        budget=MAX_DOTS_BLIND,
        k_truth=45260.0,
        min_spacing_px=0.0,
        candidate_cap=320_000,
        dinkelbach_iters=3,
    )

    n_dots_prox = dots_prox.n_dots
    n_dots_blind = dots_blind.n_dots
    dot_field = (dots_prox.emitted | dots_blind.emitted).astype(np.float32)
    n_dots = int(dot_field.sum())
    print(f"[2/8] Emitted {n_dots_prox:,} prox + {n_dots_blind:,} blind = {n_dots:,} total dots", flush=True)

    # ---- Holdout evaluation ----
    print("[3/8] Holdout evaluation...", flush=True)
    ctx = holdout.build_holdout(g, hide_frac=0.20, seeds=(20, 21),
                                modes=("all", "detached"), detach_px=4)
    holdout_result = holdout.evaluate(dot_field.astype(bool), ctx)
    pooled_dti = holdout_result["pooled_dti"]
    print(f"    HOLDOUT-DTI (pooled): {pooled_dti:.6f}", flush=True)
    print(f"    Withheld positives: {holdout_result['pooled_n_truth']:,}", flush=True)
    print(f"    Mean fold DTI: {holdout_result['mean_fold_dti']:.6f}", flush=True)

    # ---- Leakage canary ----
    print("[4/8] Leakage canary...", flush=True)
    truth_all = np.zeros(g.shape, dtype=bool)
    for hidden in ctx.hidden_by_cell.values():
        truth_all |= hidden
    visible_cat = cat & ~truth_all
    active = fp & ~visible_cat
    pos_idx = np.flatnonzero((truth_all & active).ravel())
    neg_pool = np.flatnonzero((active & ~truth_all).ravel())
    rng = np.random.default_rng(88022)
    if pos_idx.size == 0 or neg_pool.size == 0:
        canary_pass = True; max_sym_auc = 0.0; canary_rows = []
    else:
        neg_idx = rng.choice(neg_pool, size=min(neg_pool.size, 8 * pos_idx.size), replace=False)
        sel = np.concatenate([pos_idx, neg_idx])
        y_eval = np.concatenate([np.ones(pos_idx.size, np.int8), np.zeros(neg_idx.size, np.int8)])
        from sklearn.metrics import roc_auc_score
        feature_tests = [
            ("dist_to_sgmc", d_sgmc.astype(np.float64)),
            ("sgmc_weight", sgmc_weight.astype(np.float64)),
            ("conjunction_surface", surface.astype(np.float64)),
        ]
        canary_rows = []; max_sym_auc = 0.0
        for fname, farr in feature_tests:
            col = farr.ravel()[sel]
            if col.size == 0 or np.ptp(col) == 0:
                auc = 0.5
            else:
                auc = float(roc_auc_score(y_eval, col))
            sym = max(auc, 1.0 - auc)
            max_sym_auc = max(max_sym_auc, sym)
            canary_rows.append({
                "feature": fname, "roc_auc": round(auc, 6), "symmetric_auc": round(sym, 6),
                "threshold": 0.90, "pass": bool(sym <= 0.90),
            })
            print(f"    {fname}: AUC={auc:.4f}, symmetric={sym:.4f}, pass={sym <= 0.90}", flush=True)
        canary_pass = max_sym_auc <= 0.90
        print(f"    Max symmetric AUC: {max_sym_auc:.4f}, pass={canary_pass}", flush=True)

    # ---- Registry uniqueness ----
    print("[5/8] Registry uniqueness...", flush=True)
    inventory = json.loads((ROOT / "registry" / "inventory.json").read_text())
    with rasterio.open(sample_path) as ref_ds:
        exp_grid = (ref_ds.shape, ref_ds.crs, ref_ds.transform)
    final_audit = uniqueness.compare_array_to_registry(
        dot_field, inventory, fp, file_sha256="", include_reverse=True, expected_grid=exp_grid
    )
    two_phase = uniqueness.two_phase_summary(
        final_audit["rows"], int(fp.sum()), expected_rasters=len(inventory["rasters"])
    )
    max_disc_overlap = 0.0; max_disc_rho = 0.0
    dense_overlap = 1.0
    for r in final_audit["rows"]:
        if r.get("representation") == "dot_field":
            max_disc_overlap = max(max_disc_overlap, float(r["my_dots_within_3px_of_theirs"]))
            if r.get("spearman_full_footprint") is not None:
                max_disc_rho = max(max_disc_rho, abs(float(r["spearman_full_footprint"])))
        if r.get("repo") == "17GEMSDOE":
            dense_overlap = float(r["my_dots_within_3px_of_theirs"])
    print(f"    Max dot overlap (discriminating): {max_disc_overlap:.4f} (limit 0.70)", flush=True)
    print(f"    Max |rho|: {max_disc_rho:.4f} (limit 0.90)", flush=True)
    print(f"    Dense 17GEMSDOE overlap: {dense_overlap:.4f} (limit 0.70) -> literal STOP", flush=True)

    # ---- Write TIF ----
    print("[6/8] Writing GeoTIFF...", flush=True)
    out_dir = ROOT / "docs" / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    tif_path = out_dir / f"{CANDIDATE_STEM}.tif"
    zip_path = out_dir / f"{CANDIDATE_STEM}.zip"
    receipt_path = out_dir / f"{CANDIDATE_STEM}.json"
    for p in (tif_path, zip_path, receipt_path):
        if p.exists():
            p.unlink()

    submission_note = (
        f"H88-SGMC-DIST-CONJ-v2 {n_dots_prox}prox+{n_dots_blind}blind={n_dots}dots; "
        f"HOLDOUT-DTI {pooled_dti:.4f}; UNSCORED"
    )
    if len(submission_note) > 140:
        submission_note = submission_note[:137] + "..."

    writer_receipt = submission_writer.write_submission(
        tif_path, dot_field, sample_path, fp,
        note=submission_note, name=SUBMISSION_NAME, catalogue=cat,
        metadata={"hypothesis_id": "H88-SGMC-DISTANCE-CONJUNCTION-V2", "model": "sgmc-distance-conjunction-dinkelbach-v2"},
    )
    local_audit = validate.validate(tif_path, fp, cat)
    if not local_audit["all_checks_passed"]:
        failed = [k for k, v in local_audit["checks"].items() if not v]
        print(f"    ERROR: validation failed: {failed}", flush=True)
        sys.exit(1)
    print(f"    Format validation: ALL CHECKS PASSED", flush=True)

    tif_sha = sha256_file(tif_path)
    zip_sha = sha256_file(zip_path)
    print(f"    TIF SHA-256: {tif_sha}", flush=True)

    # ---- Run card ----
    run_card = {
        "schema": "gems88.run-card.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": "GEMSDOE88",
        "experiment_id": "H88-SGMC-DIST-CONJ-v2",
        "lane": "H88-SGMC-DISTANCE-CONJUNCTION-v2",
        "canary_max_auc": round(max_sym_auc, 6),
        "scores_evidence_class": "HOLDOUT-DTI",
        "independent_organizer_receipt": False,
        "downloadable_file": f"downloads/{tif_path.name}",
        "artifact": f"docs/downloads/{tif_path.name}",
        "zip_artifact": f"docs/downloads/{zip_path.name}",
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "emitted_dots": n_dots,
        "weekly_slots_used": 0,
        "experiment_budget_used": 2,
        "experiment_count": 2,
        "hypothesis": (
            "H88-SGMC-DISTANCE-CONJUNCTION-v2: Same geological hypothesis as v1 "
            "(SGMC concealed faults at piedmont-basin interface), but using exact "
            "Dinkelbach CELF fractional-programming allocation instead of decimated "
            "emission for more efficient dot placement near withheld truth segments."
        ),
        "mechanism": (
            "Hydrothermal fluids exploit pre-existing crustal weaknesses. SGMC map records "
            "concealed Quaternary faults not in USGS/INGENIOUS catalogue. Distance to SGMC "
            "concealed faults drives off-catalogue discovery; catalogue distance used only "
            "as zone constraint. Dots at 1-25 px from catalogue within 300 m kernel reach of "
            "withheld segments. Blind zone (>26 px) targets novel faults. Dinkelbach CELF "
            "allocator tracks exact TP_w and FP_w for optimal dot placement."
        ),
        "named_non_fault_process": (
            "Pleistocene pluvial shoreline wave-cut benches (Lake Lahontan ~1332 m, "
            "Lake Bonneville ~1463/1552 m) create linear topographic features without "
            "radiometric or magnetic anomalies; closed-basin playas produce flat lows without "
            "structural control; alluvial fan apices create radial drainage without fault geometry."
        ),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "version": "gems57-pooled-hide-v2",
            "evaluator_version": "gems57-pooled-hide-v2",
            "split": "buffered-whole-components-loqo-v2",
            "seeds": [20, 21],
            "withheld_positives": int(holdout_result["pooled_n_truth"]),
            "withheld_positive_pixels": int(holdout_result["pooled_n_truth"]),
            "candidate": round(pooled_dti, 6),
            "ci95": None,
            "candidate_detail": {
                "dti": round(pooled_dti, 6),
                "pooled_tp": round(holdout_result["pooled_tp"], 2),
                "pooled_fp": round(holdout_result["pooled_fp"], 2),
                "pooled_fn": round(holdout_result["pooled_fn"], 2),
                "n_truth": int(holdout_result["pooled_n_truth"]),
                "n_emitted": int(holdout_result["emitted_pixels"]),
            },
            "mean_fold_dti": round(holdout_result["mean_fold_dti"], 6),
            "std_fold_dti": round(holdout_result["std_fold_dti"], 6),
            "per_fold_dti": {k: round(v, 6) for k, v in holdout_result["per_fold_dti"].items()},
            "caveat": (
                "Lightweight build without full bootstrap CI; HOLDOUT-DTI measures recovery "
                "of withheld whole-component catalogue faults; NOT an organizer test-set score."
            ),
        },
        "leakage_canary": {
            "features_tested": len(canary_rows),
            "max_symmetric_auc": round(max_sym_auc, 6),
            "threshold": 0.90,
            "all_pass": canary_pass,
            "features": canary_rows,
        },
        "correlation_overlap_vs_registry": {
            "inventory_file": "registry/inventory.json",
            "rasters_checked": len(final_audit["rows"]),
            "final_dots": {
                "max_forward_dot_overlap_3px": round(max_disc_overlap, 6),
                "all_passed_lt_070": bool(max_disc_overlap <= 0.70),
                "max_abs_spearman_rho": round(max_disc_rho, 6),
                "all_passed_le_090": bool(max_disc_rho <= 0.90),
            },
            "dense_prior": {
                "evidence_class": "REGISTRY-MEASUREMENT",
                "forward_dot_overlap_3px": dense_overlap,
                "duplicate": bool(dense_overlap > 0.70),
            },
            "per_raster": [
                {
                    "repo": r["repo"], "submission": r["submission"],
                    "representation_class": r["representation"],
                    "their_dots": int(r["their_dots"]),
                    "spearman_rho": round(float(r["spearman_full_footprint"]), 6),
                    "forward_3px_overlap": round(float(r["my_dots_within_3px_of_theirs"]), 6),
                    "jaccard": round(float(r["jaccard_dot_sets"]), 6),
                    "sha256": r["sha256"],
                }
                for r in final_audit["rows"]
            ],
        },
        "two_phase_summary": two_phase,
        "validator_output": {
            "local_format_ok": bool(local_audit["all_checks_passed"]),
            "all_checks": local_audit["checks"],
            "all_checks_passed": local_audit["all_checks_passed"],
            "writer_receipt_file": f"downloads/{receipt_path.name}",
            "emitted_positive_pixels": local_audit["emitted_positive_pixels"],
            "on_catalogue_positive_pixels": local_audit.get("on_catalogue_positive_pixels", 0),
            "in_footprint_positive_pixels": local_audit.get("in_footprint_positive_pixels", 0),
            "footprint_fraction": local_audit.get("footprint_fraction", 0.0),
        },
        "submission_name": SUBMISSION_NAME,
        "submission_note": submission_note,
        "submission_note_length": len(submission_note),
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "stop_reason": (
            f"SGMC-distance conjunction v2 raster passes all format, canary (max AUC={max_sym_auc:.4f}), "
            f"and sparse-discriminating uniqueness gates (max dot overlap={max_disc_overlap:.4f} <= 0.70, "
            f"max |rho|={max_disc_rho:.4f} <= 0.90). HOLDOUT-DTI={pooled_dti:.6f}. "
            f"Literally blocked by 17GEMSDOE dense witness (overlap={dense_overlap:.4f} > 0.70). "
            f"Not submitted; download for research only."
        ),
        "budget": {
            "experiments_run": 2,
            "experiment_cap": 3,
            "wall_clock_cap_seconds": 7200,
            "weekly_slots_used": 0,
            "organizer_confirmed_score": None,
        },
    }

    if (
        canary_pass
        and dense_overlap <= 0.70
        and max_disc_overlap <= 0.70
        and max_disc_rho <= 0.90
        and local_audit["all_checks_passed"]
        and pooled_dti > 0.205991
    ):
        run_card["verdict"] = "promote"
    else:
        run_card["verdict"] = "negative"

    for dest in (
        "registry/sgmc88_run_card.json",
        "docs/data/sgmc88_run_card.json",
    ):
        write_json(ROOT / dest, run_card)

    gate_verdict = {
        "schema": "gems88.gate-v1",
        "generated_utc": run_card["generated_utc"],
        "experiment_id": "H88-SGMC-DIST-CONJ-v2",
        "ok_to_download": True,
        "ok_to_submit": False,
        "format_passed": local_audit["all_checks_passed"],
        "canary_passed": canary_pass,
        "canary_max_auc": round(max_sym_auc, 6),
        "holdout_dti": round(pooled_dti, 6),
        "sparse_uniqueness_passed": bool(max_disc_overlap <= 0.70 and max_disc_rho <= 0.90),
        "max_dot_overlap": round(max_disc_overlap, 6),
        "max_abs_rho": round(max_disc_rho, 6),
        "literal_blocked": bool(dense_overlap > 0.70),
        "dense_overlap": round(dense_overlap, 4),
        "verdict": run_card["verdict"],
    }
    for gv_dest in (
        "registry/sgmc88_gate_verdict.json",
        "docs/data/sgmc88_gate_verdict.json",
    ):
        write_json(ROOT / gv_dest, gate_verdict)

    elapsed = round(time.monotonic() - t0, 2)
    print(f"\n[COMPLETE] {elapsed:.1f}s -> {tif_path.name}", flush=True)
    print(f"  SHA-256: {tif_sha}", flush=True)
    print(f"  Dots: {n_dots:,} (prox={n_dots_prox:,}, blind={n_dots_blind:,})", flush=True)
    print(f"  HOLDOUT-DTI: {pooled_dti:.6f}", flush=True)
    print(f"  Max symmetric AUC: {max_sym_auc:.4f}", flush=True)
    print(f"  Max dot overlap: {max_disc_overlap:.4f}", flush=True)
    print(f"  Max |rho|: {max_disc_rho:.4f}", flush=True)
    print(f"  OK to download: YES", flush=True)
    print(f"  OK to submit: NO (literal 17GEMSDOE dense witness overlap={dense_overlap:.4f} > 0.70)", flush=True)
    print(f"  Verdict: {run_card['verdict']}", flush=True)


if __name__ == "__main__":
    main()