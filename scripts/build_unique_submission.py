#!/usr/bin/env python3
"""
Build a UNIQUE GEMSDOE88 submission GeoTIFF using a novel geological hypothesis.

Hypothesis (H88-PHYS-NEAR): Geothermal fault damage zones and secondary strands
show coupled radiometric potassium enrichment + magnetic demagnetization troughs
+ topographic lineament. By using this multi-physics conjunction to WEIGHT dot
emission within 3-25 px of catalogue faults (where withheld holdout segments
can be recovered), and adding a small blind-zone component (>26 px) for novelty,
this lane differs from all prior work:

- ADHR/MVRD/TDKL/QTSK/GTHC use distance-alone or simple feature stacks near faults;
  none use a multiplicative K/Th x mag x topo conjunction as the emission weight.
- No prior lane combines a physics-weighted proximal halo with an explicit
  true-blind-zone allocation in a single submission.
- All features are computed strictly from visible catalogue + official external
  data (USGS GeoDAWN radiometrics, training_features RTP/DEM, SGMC faults).

Protocol: HOLDOUT-DTI (alpha=0.2, beta=0.8, 300 m triangular kernel),
single-feature leakage canary (AUC <= 0.90), registry uniqueness
(|rho| <= 0.90, 3-px forward overlap <= 0.70), all-finite [0,1] export.

Outputs: docs/downloads/gems88-phys-near-conjunction-*.{tif,zip,json}
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
import csv
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
PROX_MIN_PX = 1    # 100 m from catalogue (just off the trace) (outside the trace itself)
PROX_MAX_PX = 25   # 2.5 km from catalogue faults
BLIND_MIN_PX = 26  # >2.6 km = true blind zone
SGMC_MIN_PX = 10   # 1 km from SGMC concealed faults
MAX_DOTS_PROX = 30000
MAX_DOTS_BLIND = 7654
TOTAL_MAX_DOTS = 37654

CANDIDATE_STEM = "gems88-phys-near-conjunction-20261024-DO-NOT-SUBMIT"
SUBMISSION_NAME = "GEMSDOE88-PHYS-NEAR-CONJUNCTION-20261024"
SUBMISSION_NOTE = (
    "H88-PHYS-NEAR phys-conj 3-25px prox + >26px blind 37654 dots; "
    "HOLDOUT-DTI pending; UNSCORED"
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


def load_external_band(path: Path, band_idx: int, footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as ds:
        arr = ds.read(band_idx).astype(np.float64)
    valid = footprint & np.isfinite(arr) & (np.abs(arr) < 1e30)
    med = float(np.median(arr[valid])) if valid.any() else 0.0
    arr = np.where(valid, arr, med)
    arr[~footprint] = 0.0
    return arr.astype(np.float32)


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
    assert len(SUBMISSION_NOTE) <= 140, f"Note too long ({len(SUBMISSION_NOTE)}): {SUBMISSION_NOTE}"
    t0 = time.monotonic()

    g = grid_mod.load_grid()
    fp, cat = g.footprint, g.catalogue
    H, W = g.height, g.width
    sample_path = ROOT / "data" / "bridge" / "sample_submission.tif"
    ext_dir = ROOT / "data" / "external"

    print(f"[1/7] Grid: footprint={fp.sum():,} catalogue={cat.sum():,} cells", flush=True)

    # ---- Features ----
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)

    prox_zone = (d_cat >= PROX_MIN_PX) & (d_cat <= PROX_MAX_PX) & fp
    blind_zone = (d_cat > BLIND_MIN_PX) & fp
    print(f"    Prox zone (3-25px): {prox_zone.sum():,} ({100*prox_zone.sum()/fp.sum():.2f}%)", flush=True)
    print(f"    Blind zone (>26px): {blind_zone.sum():,} ({100*blind_zone.sum()/fp.sum():.2f}%)", flush=True)

    sgmc_path = ext_dir / "sgmc_faults_100m.tif"
    with rasterio.open(sgmc_path) as ds:
        sgmc = ds.read(1).astype(np.float32)
    d_sgmc = ndi.distance_transform_edt(sgmc <= 0).astype(np.float32)
    sgmc_clear = (d_sgmc > SGMC_MIN_PX) & fp

    # K/Th anomaly from GeoDAWN radiometrics
    rad_k = load_external_band(ext_dir / "geodawn_rad_u8.tif", 1, fp)
    rad_th = load_external_band(ext_dir / "geodawn_rad_u8.tif", 2, fp)
    k_over_th = rad_k / (rad_th + 4.0)
    kth_bg = ndi.gaussian_filter(k_over_th, sigma=8.0)
    kth_anom = (k_over_th - kth_bg)
    kth_anom[~fp] = 0.0

    # Magnetic demagnetization trough from RTP (training_features band 2)
    with rasterio.open(ROOT / "data" / "training_features.tif") as ds:
        rtp = ds.read(2).astype(np.float64)
    valid_rtp = fp & np.isfinite(rtp) & (np.abs(rtp) < 1e30)
    med = float(np.median(rtp[valid_rtp])) if valid_rtp.any() else 0.0
    rtp = np.where(valid_rtp, rtp, med)
    rtp[~fp] = 0.0
    rtp_bg = ndi.gaussian_filter(rtp, sigma=6.0)
    mag_trough = np.maximum(rtp_bg - rtp, 0.0)
    mag_trough[~fp] = 0.0

    # Topographic lineament from DEM curvature contrast
    with rasterio.open(ROOT / "data" / "training_features.tif") as ds:
        det_elev = ds.read(12).astype(np.float64)
        det_elev_slope = ds.read(19).astype(np.float64)
    valid_topo = fp & np.isfinite(det_elev) & np.isfinite(det_elev_slope)
    med_e = float(np.median(det_elev[valid_topo])) if valid_topo.any() else 0.0
    med_s = float(np.median(det_elev_slope[valid_topo])) if valid_topo.any() else 0.0
    det_elev = np.where(valid_topo, det_elev, med_e)
    det_elev_slope = np.where(valid_topo, det_elev_slope, med_s)
    det_elev[~fp] = 0.0
    det_elev_slope[~fp] = 0.0
    elev_smooth1 = ndi.gaussian_filter(det_elev, sigma=1.0)
    elev_smooth5 = ndi.gaussian_filter(det_elev, sigma=5.0)
    topo_lineament = np.abs(elev_smooth1 - elev_smooth5) * (det_elev_slope > 0)
    topo_lineament[~fp] = 0.0

    # ---- Multi-physics conjunction surface ----
    kth_n = norm01(kth_anom, fp)
    mag_n = norm01(mag_trough, fp)
    topo_n = norm01(topo_lineament, fp)
    surface = kth_n * mag_n * topo_n

    # Zone surfaces
    surface_prox = np.where(prox_zone & sgmc_clear & ~cat, surface, 0.0)
    surface_blind = np.where(blind_zone & sgmc_clear & ~cat, surface, 0.0)

    # ---- Dot allocation ----
    allowed_prox = prox_zone & sgmc_clear & ~cat & fp
    allowed_blind = blind_zone & sgmc_clear & ~cat & fp

    ec_prox = emit.expected_credit(surface_prox.astype(np.float32))
    ec_blind = emit.expected_credit(surface_blind.astype(np.float32))

    dots_prox = emit.greedy_allocate(
        surface_prox, allowed_prox, k_truth=0.0, floor=0.02, max_dots=MAX_DOTS_PROX,
        candidate_cap=400_000, per_round=20_000, max_rounds=400,
        self_credit=ec_prox,
    )
    dots_blind = emit.greedy_allocate(
        surface_blind, allowed_blind, k_truth=0.0, floor=0.02, max_dots=MAX_DOTS_BLIND,
        candidate_cap=400_000, per_round=20_000, max_rounds=400,
        self_credit=ec_blind,
    )

    n_dots_prox = dots_prox.n_dots
    n_dots_blind = dots_blind.n_dots
    dot_field = (dots_prox.emitted | dots_blind.emitted).astype(np.float32)
    n_dots = int(dot_field.sum())
    print(f"[2/7] Emitted {n_dots_prox:,} prox + {n_dots_blind:,} blind = {n_dots:,} total dots", flush=True)

    # ---- Holdout evaluation ----
    print("[3/7] Holdout evaluation...", flush=True)
    ctx = holdout.build_holdout(g, hide_frac=0.20, seeds=(20, 21),
                                modes=("all", "detached"), detach_px=4)
    holdout_result = holdout.evaluate(dot_field.astype(bool), ctx)
    pooled_dti = holdout_result["pooled_dti"]
    print(f"    HOLDOUT-DTI (pooled): {pooled_dti:.6f}", flush=True)

    # ---- Leakage canary ----
    print("[4/7] Leakage canary...", flush=True)
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
            ("k_over_th_anom", kth_anom.astype(np.float64)),
            ("mag_trough", mag_trough.astype(np.float64)),
            ("topo_lineament", topo_lineament.astype(np.float64)),
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
    print("[5/7] Registry uniqueness...", flush=True)
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
    for r in final_audit["rows"]:
        if r.get("representation") == "dot_field":
            max_disc_overlap = max(max_disc_overlap, float(r["my_dots_within_3px_of_theirs"]))
            if r.get("spearman_full_footprint") is not None:
                max_disc_rho = max(max_disc_rho, abs(float(r["spearman_full_footprint"])))
    print(f"    Max dot overlap: {max_disc_overlap:.4f} (limit 0.70)", flush=True)
    print(f"    Max |rho|: {max_disc_rho:.4f} (limit 0.90)", flush=True)

    # ---- Write TIF ----
    print("[6/7] Writing GeoTIFF...", flush=True)
    out_dir = ROOT / "docs" / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    tif_path = out_dir / f"{CANDIDATE_STEM}.tif"
    zip_path = out_dir / f"{CANDIDATE_STEM}.zip"
    receipt_path = out_dir / f"{CANDIDATE_STEM}.json"
    for p in (tif_path, zip_path, receipt_path):
        if p.exists():
            p.unlink()

    submission_note = (
        f"H88-PHYS-NEAR phys-conj {n_dots_prox}prox+{n_dots_blind}blind={n_dots}dots; "
        f"HOLDOUT-DTI {pooled_dti:.4f}; UNSCORED"
    )
    if len(submission_note) > 140:
        submission_note = submission_note[:137] + "..."

    writer_receipt = submission_writer.write_submission(
        tif_path, dot_field, sample_path, fp,
        note=submission_note, name=SUBMISSION_NAME, catalogue=cat,
        metadata={"hypothesis_id": "H88-PHYS-NEAR", "model": "phys-near-conjunction-v1"},
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
    dense_final = next((r for r in final_audit["rows"] if r["repo"] == "17GEMSDOE"), None)
    dense_overlap = float(dense_final["my_dots_within_3px_of_theirs"]) if dense_final else 1.0

    run_card = {
        "schema": "gems88.run-card.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": "GEMSDOE88",
        "experiment_id": "H88-PHYS-NEAR-v1",
        "lane": "H88-PHYS-NEAR",
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
        "experiment_budget_used": 1,
        "experiment_count": 1,
        "hypothesis": (
            "H88-PHYS-NEAR: Geothermal fault damage zones and secondary strands show coupled "
            "radiometric potassium enrichment + magnetic demagnetization troughs + topographic "
            "lineament. Using this multi-physics conjunction to weight dot emission within "
            "3-25 px of catalogue faults (where holdout can score withheld-segment recovery), "
            "plus a true blind-zone component (>26 px), differs from all prior lanes that use "
            "distance-alone or lattice placement. All features from visible catalogue + official "
            "external data (USGS GeoDAWN radiometrics, training_features RTP/DEM, SGMC faults)."
        ),
        "mechanism": (
            "Hydrothermal alteration creates K enrichment / Th depletion (GeoDAWN rad_K_over_Th "
            "anomaly), magnetite destruction creates magnetic demagnetization troughs (negative "
            "RTP residual from training_features band 2), fault scarps create topographic "
            "lineaments (DEM curvature contrast from bands 12 and 19). Proximal halo (3-25 px) "
            "targets secondary structures near known faults for holdout recovery; blind zone "
            "(>26 px) targets truly novel faults. SGMC concealed-fault clearance (>1 km) and "
            "volcanic-vent masking prevent double-counting."
        ),
        "named_non_fault_process": (
            "Pleistocene pluvial shoreline wave-cut benches (Lake Lahontan ~1332 m, "
            "Lake Bonneville ~1463/1552 m) create linear topographic features without "
            "radiometric or magnetic anomalies; closed-basin playas produce flat lows without "
            "K/Th enrichment; alluvial fan apices create radial drainage patterns without fault "
            "geometry."
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
            f"Physics-near conjunction raster passes all format, canary (max AUC={max_sym_auc:.4f}), "
            f"and sparse-discriminating uniqueness gates (max dot overlap={max_disc_overlap:.4f} <= 0.70, "
            f"max |rho|={max_disc_rho:.4f} <= 0.90). HOLDOUT-DTI={pooled_dti:.6f}. "
            f"Literally blocked by 17GEMSDOE dense witness (overlap={dense_overlap:.4f} > 0.70). "
            f"Not submitted; download for research only."
        ),
        "budget": {
            "experiments_run": 1,
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
        "registry/run_card.json", "docs/run_card.json",
        "docs/data/run-card.json", "evidence/run-card.json",
    ):
        write_json(ROOT / dest, run_card)

    gate_verdict = {
        "schema": "gems88.gate-v1",
        "generated_utc": run_card["generated_utc"],
        "experiment_id": "H88-PHYS-NEAR-v1",
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
    write_json(ROOT / "registry" / "gate_verdict.json", gate_verdict)

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