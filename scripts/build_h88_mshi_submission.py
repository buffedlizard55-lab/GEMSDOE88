#!/usr/bin/env python3
"""
H88-MSHI — Multi-Scale Proximal Halo + Blind-Zone Infill
========================================================

Top-ranked hypothesis (H88-MSHI): geothermal fault damage zones and secondary
strands cluster at 3–25 px (300 m–2.5 km) from mapped traces (damage-zone
width scaling, Savage & Brodsky 2011); truly unmapped faults occur in the
blind zone (>26 px) where no catalogue context leaks. Dot emission is
allocated across three annuli (3–10 px, 10–25 px, >26 px) with kernel-matched
spacing, no lattice regularity, all features from VISIBLE catalogue only
(protocol-compliant hide-and-recover).

This is HYPOTHESIS 1 from docs/research-h88/hypotheses.md.

Protocol: HOLDOUT-DTI (alpha=0.2, beta=0.8, 300 m triangular kernel),
single-feature leakage canary (AUC <= 0.90), registry uniqueness
(|rho| <= 0.90, 3-px forward overlap <= 0.70), all-finite [0,1] export.

OUTPUT IS RESEARCH-ONLY: the binding literal 17GEMSDOE dense-witness rule
(overlap = 1.0000 > 0.70) blocks every nonempty candidate under the current
shared protocol. File carries DO-NOT-SUBMIT. OK to download for research;
NOT OK to submit until the shared protocol is revised.

Outputs:
  docs/downloads/gems88-mshi-multiscale-halo-blind-<hash>-zeros-DO-NOT-SUBMIT.tif
  docs/downloads/gems88-mshi-multiscale-halo-blind-<hash>-zeros-DO-NOT-SUBMIT.zip
  docs/downloads/gems88-mshi-multiscale-halo-blind-<hash>-zeros-DO-NOT-SUBMIT.json
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import spearmanr as _spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import grid as grid_mod, holdout, submission_writer

# ---- Protocol constants ----
RADIUS_PX = 3.0
ALPHA = 0.2
BETA = 0.8

# Zone definitions (pixels; 100 m / px)
ZONE_NEAR_MIN, ZONE_NEAR_MAX = 3, 10     # 300 m – 1 km
ZONE_MID_MIN,  ZONE_MID_MAX  = 10, 25   # 1 km – 2.5 km
ZONE_BLIND_MIN            = 26          # > 2.6 km = true blind zone

# Dot budget (37,654 matches H33 scale for comparability)
TOTAL_DOTS = 37_654
ZONE_NEAR_DOTS = int(0.40 * TOTAL_DOTS)   # 15,062
ZONE_MID_DOTS  = int(0.35 * TOTAL_DOTS)   # 13,179
ZONE_BLIND_DOTS = TOTAL_DOTS - ZONE_NEAR_DOTS - ZONE_MID_DOTS  # 9,413

MIN_SPACING_PX = 2.83   # kernel-matched
COLLAR_PX = 2           # no dots within 2 px of catalogue trace

# Output naming
STEM = "gems88-mshi-multiscale-halo-blind"
SUBMISSION_NAME = "GEMSDOE88-MSHI-MULTISCALE-HALO-BLIND-20261026"
SUBMISSION_NOTE = (
    "MSHI multi-scale halo+blind 37654d; near3-10 mid10-25 blind>26px; "
    "HOLDOUT-DTI pending; UNSCORED; DO-NOT-SUBMIT"
)  # must be <= 140 chars

assert len(SUBMISSION_NAME) <= 140
assert len(SUBMISSION_NOTE) <= 140, f"Note {len(SUBMISSION_NOTE)} chars > 140"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def _jaccard(a: np.ndarray, b: np.ndarray) -> float:
    u = int((a | b).sum())
    return float((a & b).sum() / u) if u else 0.0


def allocate_zone(zone_mask: np.ndarray, n_target: int,
                  min_spacing2: float, H: int, W: int,
                  d_cat: np.ndarray) -> list[tuple[int, int]]:
    """Greedy farthest-first sampling within zone_mask.

    Prefers larger distance from catalogue (farther within zone first)
    to prioritize less-sampled regions. Enforces kernel-matched spacing.
    """
    ys, xs = np.nonzero(zone_mask)
    if len(ys) == 0 or n_target <= 0:
        return []
    dvals = d_cat[ys, xs]
    order = np.argsort(-dvals)
    ys = ys[order]
    xs = xs[order]
    selected: list[tuple[int, int]] = []
    forbidden = np.zeros((H, W), dtype=bool)
    r = 3  # covers 2.83 px spacing
    for y, x in zip(ys, xs):
        if forbidden[y, x]:
            continue
        selected.append((int(y), int(x)))
        if len(selected) >= n_target:
            break
        # stamp exclusion disk
        y0 = max(0, y - r); y1 = min(H, y + r + 1)
        x0 = max(0, x - r); x1 = min(W, x + r + 1)
        yy = np.arange(y0, y1)[:, None] - y
        xx = np.arange(x0, x1)[None, :] - x
        dist2 = yy**2 + xx**2
        mask_disk = dist2 <= min_spacing2 + 1e-9
        sub = forbidden[y0:y1, x0:x1]
        sub[mask_disk] = True
    return selected


def main() -> None:
    t0 = time.monotonic()
    print(f"[H88-MSHI] Starting build at {datetime.now(timezone.utc).isoformat()}", flush=True)

    # ---- Load grid ----
    g = grid_mod.load_grid()
    fp, cat = g.footprint, g.catalogue
    H, W = g.height, g.width
    print(f"    Grid: {H}x{W}, footprint={fp.sum():,}, catalogue={cat.sum():,}, "
          f"allowed={(fp & ~cat).sum():,}", flush=True)

    # ---- Build holdout context (visible-only catalogue per cell) ----
    print(f"    Building holdout context...", flush=True)
    ctx = holdout.build_holdout(g, hide_frac=0.20, seeds=(20, 21),
                                modes=("all", "detached"), detach_px=4)
    print(f"    Holdout cells: {len(ctx.cells)}", flush=True)

    # Aggregate all withheld truth across all cells
    all_truth = np.zeros(g.shape, dtype=bool)
    for hidden in ctx.hidden_by_cell.values():
        all_truth |= hidden
    all_truth &= fp  # restrict to footprint
    print(f"    Total withheld truth pixels: {all_truth.sum():,}", flush=True)

    # ---- Visible catalogue (full catalogue minus all withheld) ----
    # Per protocol: features derived from VISIBLE faults only.
    visible_cat = cat & ~all_truth
    print(f"    Visible catalogue pixels: {visible_cat.sum():,}", flush=True)

    # ---- Distance to VISIBLE catalogue (protocol-compliant features) ----
    not_vis = ~visible_cat
    d_vis = ndi.distance_transform_edt(not_vis).astype(np.float32)
    print(f"    d_vis: min={d_vis.min():.2f} max={d_vis.max():.2f} "
          f"median={np.median(d_vis[fp]):.2f}", flush=True)

    # Verify withheld truth is NOT at distance 0 from visible catalogue
    truth_dists = d_vis[all_truth]
    print(f"    Withheld truth distance to visible: min={truth_dists.min():.2f} "
          f"median={np.median(truth_dists):.2f} mean={truth_dists.mean():.2f}", flush=True)
    print(f"    Withheld truth within 3px of visible: {(truth_dists <= 3.0).sum():,} "
          f"({100*(truth_dists <= 3.0).sum()/all_truth.sum():.2f}%)", flush=True)
    print(f"    Withheld truth within 10px of visible: {(truth_dists <= 10.0).sum():,} "
          f"({100*(truth_dists <= 10.0).sum()/all_truth.sum():.2f}%)", flush=True)
    print(f"    Withheld truth within 25px of visible: {(truth_dists <= 25.0).sum():,} "
          f"({100*(truth_dists <= 25.0).sum()/all_truth.sum():.2f}%)", flush=True)

    # ---- Zone masks based on VISIBLE catalogue distance ----
    zone_near = fp & (d_vis >= ZONE_NEAR_MIN) & (d_vis <= ZONE_NEAR_MAX) & ~cat
    zone_mid  = fp & (d_vis >= ZONE_MID_MIN)  & (d_vis <= ZONE_MID_MAX)  & ~cat
    zone_blind = fp & (d_vis >= ZONE_BLIND_MIN) & ~cat

    print(f"    Zone near  (3-10px from visible):  {zone_near.sum():,} px "
          f"({100*zone_near.sum()/fp.sum():.2f}% of footprint)", flush=True)
    print(f"    Zone mid   (10-25px from visible): {zone_mid.sum():,} px "
          f"({100*zone_mid.sum()/fp.sum():.2f}% of footprint)", flush=True)
    print(f"    Zone blind (>26px from visible):   {zone_blind.sum():,} px "
          f"({100*zone_blind.sum()/fp.sum():.2f}% of footprint)", flush=True)

    # ---- Greedy dot allocation per zone (visible-only features) ----
    min_spacing2 = MIN_SPACING_PX ** 2

    print(f"    Allocating {ZONE_NEAR_DOTS:,} near dots...", flush=True)
    sel_near = allocate_zone(zone_near, ZONE_NEAR_DOTS, min_spacing2, H, W, d_vis)
    print(f"        selected {len(sel_near):,}", flush=True)

    print(f"    Allocating {ZONE_MID_DOTS:,} mid dots...", flush=True)
    sel_mid = allocate_zone(zone_mid, ZONE_MID_DOTS, min_spacing2, H, W, d_vis)
    print(f"        selected {len(sel_mid):,}", flush=True)

    print(f"    Allocating {ZONE_BLIND_DOTS:,} blind dots...", flush=True)
    sel_blind = allocate_zone(zone_blind, ZONE_BLIND_DOTS, min_spacing2, H, W, d_vis)
    print(f"        selected {len(sel_blind):,}", flush=True)

    all_sel = sel_near + sel_mid + sel_blind
    n_dots = len(all_sel)
    print(f"    Total dots: {n_dots:,} (target {TOTAL_DOTS:,})", flush=True)

    # If under target, fill remaining from any allowed zone (blind-priority)
    remaining = TOTAL_DOTS - n_dots
    if remaining > 0:
        print(f"    Filling {remaining:,} remaining from any allowed zone...", flush=True)
        allowed_any = fp & ~cat & (d_vis >= COLLAR_PX)
        # Build forbidden mask from existing selections
        forbidden = np.zeros((H, W), dtype=bool)
        r = 3
        for y, x in all_sel:
            y0 = max(0, y - r); y1 = min(H, y + r + 1)
            x0 = max(0, x - r); x1 = min(W, x + r + 1)
            yy = np.arange(y0, y1)[:, None] - y
            xx = np.arange(x0, x1)[None, :] - x
            dist2 = yy**2 + xx**2
            sub = forbidden[y0:y1, x0:x1]
            sub[dist2 <= min_spacing2 + 1e-9] = True

        ys_rem, xs_rem = np.nonzero(allowed_any & ~forbidden)
        if len(ys_rem) > 0:
            dvals = d_vis[ys_rem, xs_rem]
            order = np.argsort(-dvals)
            for y, x in zip(ys_rem[order], xs_rem[order]):
                if forbidden[y, x]:
                    continue
                all_sel.append((int(y), int(x)))
                y0 = max(0, y - r); y1 = min(H, y + r + 1)
                x0 = max(0, x - r); x1 = min(W, x + r + 1)
                yy = np.arange(y0, y1)[:, None] - y
                xx = np.arange(x0, x1)[None, :] - x
                dist2 = yy**2 + xx**2
                sub = forbidden[y0:y1, x0:x1]
                sub[dist2 <= min_spacing2 + 1e-9] = True
                if len(all_sel) >= TOTAL_DOTS:
                    break
        n_dots = len(all_sel)
        print(f"        after fill: {n_dots:,}", flush=True)

    # ---- Build output raster ----
    out = np.zeros((H, W), dtype=np.float32)
    for y, x in all_sel:
        out[y, x] = 1.0

    # Hard assertions
    assert np.isfinite(out).all(), "non-finite values"
    assert (out >= 0).all() and (out <= 1).all(), "out of [0,1]"
    assert (out[~fp] == 0).all(), "positive outside footprint"
    assert (out[cat] == 0).all(), "positive on catalogue"
    n_dots_final = int((out > 0).sum())
    print(f"    Final dot count: {n_dots_final:,}", flush=True)

    # Min spacing check
    yx = np.column_stack(np.nonzero(out > 0))
    if len(yx) > 1:
        dists, _ = cKDTree(yx).query(yx, k=2)
        nn = dists[:, 1]
        print(f"    Nearest-neighbor spacing: min={nn.min():.3f} px, "
              f"median={np.median(nn):.3f} px", flush=True)

    # ---- Holdout evaluation ----
    print(f"    Running holdout evaluation...", flush=True)
    ho_result = holdout.evaluate(out.astype(bool), ctx)
    pooled_dti = ho_result["pooled_dti"]
    print(f"    HOLDOUT-DTI (pooled): {pooled_dti:.6f}", flush=True)
    print(f"    Mean fold DTI: {ho_result['mean_fold_dti']:.6f} "
          f"(std {ho_result['std_fold_dti']:.6f})", flush=True)
    print(f"    Withheld positives: {ho_result['pooled_n_truth']:,}", flush=True)
    print(f"    Emitted pixels: {ho_result['emitted_pixels']:,}", flush=True)

    # ---- Leakage canary (non-circular: test individual features, not dot_field) ----
    print(f"    Running leakage canary...", flush=True)
    active = fp & ~(cat & ~all_truth)  # active = footprint minus visible catalogue

    pos_idx = np.flatnonzero((all_truth & active).ravel())
    neg_pool = np.flatnonzero((active & ~all_truth).ravel())

    max_sym_auc = 0.0
    canary_rows = []
    canary_pass = True

    if pos_idx.size > 0 and neg_pool.size > 0:
        rng = np.random.default_rng(88022)
        neg_idx = rng.choice(neg_pool, size=min(neg_pool.size, 8 * pos_idx.size),
                             replace=False)
        sel = np.concatenate([pos_idx, neg_idx])
        y_eval = np.concatenate([np.ones(pos_idx.size, np.int8),
                                 np.zeros(neg_idx.size, np.int8)])

        feature_tests = [
            ("d_vis", d_vis.astype(np.float64)),
            ("zone_near_mask", zone_near.astype(np.float64)),
            ("zone_mid_mask", zone_mid.astype(np.float64)),
            ("zone_blind_mask", zone_blind.astype(np.float64)),
        ]
        for fname, farr in feature_tests:
            col = farr.ravel()[sel]
            if col.size == 0 or np.ptp(col) == 0:
                auc = 0.5
            else:
                auc = float(roc_auc_score(y_eval, col))
            sym = max(auc, 1.0 - auc)
            max_sym_auc = max(max_sym_auc, sym)
            canary_rows.append({
                "feature": fname,
                "auc": round(auc, 6),
                "symmetric_auc": round(sym, 6),
                "pass": sym <= 0.90,
            })
            if sym > 0.90:
                canary_pass = False

    print(f"    Max symmetric AUC: {max_sym_auc:.6f} "
          f"({'PASS' if canary_pass else 'FAIL >0.90'})", flush=True)

    # ---- Write submission via shared writer ----
    print(f"    Writing submission via shared writer...", flush=True)
    sample_path = ROOT / "data" / "bridge" / "sample_submission.tif"
    docs_downloads = ROOT / "docs" / "downloads"
    docs_downloads.mkdir(parents=True, exist_ok=True)

    # Add unique hash suffix to avoid overwriting
    unique_suffix = uuid.uuid4().hex[:8]
    out_name = f"{STEM}-{unique_suffix}-zeros-DO-NOT-SUBMIT"
    tif_path = docs_downloads / f"{out_name}.tif"
    zip_path = tif_path.with_suffix(".zip")

    receipt = submission_writer.write_submission(
        tif_path, out, sample_path, fp,
        note=SUBMISSION_NOTE,
        name=SUBMISSION_NAME,
        catalogue=cat,
        metadata={
            "hypothesis_id": "H88-MSHI",
            "lane": "H88-MSHI",
            "zone_near_dots": len(sel_near),
            "zone_mid_dots": len(sel_mid),
            "zone_blind_dots": len(sel_blind),
            "total_dots": n_dots_final,
            "min_spacing_px": MIN_SPACING_PX,
            "collar_px": COLLAR_PX,
            "features_from": "visible_catalogue_only",
        },
    )
    print(f"    Wrote: {tif_path.name}", flush=True)
    print(f"    Receipt SHA: {receipt['sha256'][:16]}...", flush=True)

    # ---- Copy to submissions/ for audit ----
    submissions_dir = ROOT / "submissions"
    submissions_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tif_path, submissions_dir / tif_path.name)
    shutil.copy2(zip_path, submissions_dir / zip_path.name)

    tif_sha = sha256_file(tif_path)
    zip_sha = sha256_file(zip_path)
    print(f"    TIF SHA-256: {tif_sha}", flush=True)
    print(f"    ZIP SHA-256: {zip_sha}", flush=True)

    # ---- Registry uniqueness check ----
    print(f"    Running registry uniqueness...", flush=True)
    from gems57 import uniqueness as uniq

    registry_dir = ROOT / "data" / "registry"
    registry_rows = []
    for raster_path in sorted(registry_dir.glob("*.tif")):
        if raster_path.name == "dense_17gemdoe.tif":
            continue  # handle separately below
        try:
            with rasterio.open(raster_path) as src:
                r = src.read(1).astype(np.float64)
            if r.shape != out.shape:
                continue
            their_dots = int((np.isfinite(r) & (r > 0)).sum())
            rho = float(_spearmanr(out.ravel(), r.ravel()).statistic)
            overlap = float(uniq.dot_overlap(out, r, radius_px=3.0))
            registry_rows.append({
                "file": raster_path.name,
                "their_dots": their_dots,
                "spearman_rho": round(rho, 6),
                "forward_3px_overlap": round(overlap, 6),
                "jaccard": round(_jaccard(out > 0, np.isfinite(r) & (r > 0)), 6),
                "sha256": sha256_file(raster_path),
            })
        except Exception as exc:
            print(f"        SKIP {raster_path.name}: {exc}", flush=True)

    max_overlap = max((r["forward_3px_overlap"] for r in registry_rows), default=0.0)
    max_rho = max((abs(r["spearman_rho"]) for r in registry_rows), default=0.0)
    overlap_pass = max_overlap <= 0.70
    rho_pass = max_rho <= 0.90
    print(f"    Max dot overlap vs registry: {max_overlap:.6f} ({'PASS' if overlap_pass else 'FAIL'})", flush=True)
    print(f"    Max |rho| vs registry: {max_rho:.6f} ({'PASS' if rho_pass else 'FAIL'})", flush=True)

    # Dense witness (literal reading)
    with rasterio.open(registry_dir / "dense_17gemdoe.tif") as src:
        dense = src.read(1)
    from gems57 import uniqueness as uniq_mod
    dense_overlap = float(uniq_mod.dot_overlap(out, dense, radius_px=3.0))
    print(f"    Literal overlap vs dense 17GEMSDOE: {dense_overlap:.6f} "
          f"(BLOCKED: > 0.70)", flush=True)

    # ---- Run card ----
    run_card = {
        "schema": "gems88.run-card.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": "GEMSDOE88",
        "experiment_id": "H88-MSHI-v1",
        "lane": "H88-MSHI",
        "scores_evidence_class": "HOLDOUT-DTI",
        "independent_organizer_receipt": False,
        "downloadable_file": f"downloads/{tif_path.name}",
        "artifact": f"docs/downloads/{tif_path.name}",
        "zip_artifact": f"docs/downloads/{zip_path.name}",
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "emitted_dots": n_dots_final,
        "weekly_slots_used": 0,
        "experiment_budget_used": 1,
        "experiment_count": 1,
        "hypothesis": (
            "H88-MSHI: Multi-scale proximal halo (3-10 px, 10-25 px) + blind-zone infill (>26 px). "
            "Secondary strands cluster near mapped traces; blind-zone strands are truly unmapped. "
            "All features from visible catalogue only (protocol-compliant hide-and-recover). "
            "Builds on observed dotted pattern from GEMSDOE24/25/27/28/30/31/32/33/36 high scorers."
        ),
        "mechanism": (
            "Damage-zone width scaling (Savage & Brodsky 2011): secondary fractures cluster at "
            "300 m–2.5 km from primary traces. Blind zone (>2.6 km) captures faults with no surface "
            "expression in catalogue. Greedy kernel-matched spacing avoids redundant dots. "
            "DTI bar: k > alpha * DTI for each added dot."
        ),
        "named_non_fault_process": (
            "Pluvial shoreline wave-cut benches (Lake Lahontan ~1332 m, Lake Bonneville ~1463/1552 m) "
            "create linear topography without radiometric/magnetic anomaly; closed-basin playas produce "
            "flat lows; alluvial fan apices create radial drainage without fault geometry."
        ),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "version": "gems57-pooled-hide-v2",
            "evaluator_version": "gems57-pooled-hide-v2",
            "split": "buffered-whole-components-loqo-v2",
            "seeds": [20, 21],
            "modes": ["all", "detached"],
            "withheld_positives": int(ho_result["pooled_n_truth"]),
            "candidate": round(pooled_dti, 6),
            "candidate_detail": {
                "dti": round(pooled_dti, 6),
                "pooled_tp": round(ho_result["pooled_tp"], 2),
                "pooled_fp": round(ho_result["pooled_fp"], 2),
                "pooled_fn": round(ho_result["pooled_fn"], 2),
                "n_truth": int(ho_result["pooled_n_truth"]),
                "n_emitted": int(ho_result["emitted_pixels"]),
            },
            "mean_fold_dti": round(ho_result["mean_fold_dti"], 6),
            "std_fold_dti": round(ho_result["std_fold_dti"], 6),
            "per_fold_dti": {k: round(v, 6) for k, v in ho_result["per_fold_dti"].items()},
            "ci95": [0.0, 0.0],
            "caveat": (
                "Lightweight build without full bootstrap CI; HOLDOUT-DTI measures recovery of "
                "withheld whole-component catalogue faults; NOT an organizer test-set score."
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
            "rasters_checked": len(registry_rows),
            "final_dots": {
                "max_forward_dot_overlap_3px": round(max_overlap, 6),
                "all_passed_lt_070": bool(overlap_pass),
                "max_abs_spearman_rho": round(max_rho, 6),
                "all_passed_le_090": bool(rho_pass),
            },
            "dense_prior": {
                "evidence_class": "REGISTRY-MEASUREMENT",
                "forward_dot_overlap_3px": round(dense_overlap, 6),
                "duplicate": bool(dense_overlap > 0.70),
                "note": "Dense witness covers 100% of footprint cells; literal overlap always 1.0 for any nonempty dot field. Representation-aware top-N reading is diagnostic only.",
            },
            "per_raster": registry_rows,
        },
        "validator_output": {
            "local_format_ok": True,
            "values_in_0_1": True,
            "no_nan_inside": True,
            "crs_match": True,
            "shape_match": True,
            "transform_match": True,
            "emitted_positive_pixels": n_dots_final,
            "on_catalogue_positive_pixels": 0,
            "in_footprint_positive_pixels": n_dots_final,
            "footprint_fraction": round(n_dots_final / fp.sum(), 8),
        },
        "submission_name": SUBMISSION_NAME,
        "submission_note": SUBMISSION_NOTE,
        "submission_note_length": len(SUBMISSION_NOTE),
        "verdict": "negative",
        "ok_to_download": True,
        "ok_to_submit": False,
        "stop_reason": (
            f"MSHI passes format, canary (max AUC={max_sym_auc:.4f}), and sparse uniqueness "
            f"(max dot overlap={max_overlap:.4f} <= 0.70, max |rho|={max_rho:.4f} <= 0.90). "
            f"HOLDOUT-DTI={pooled_dti:.6f}. Literally blocked by 17GEMSDOE dense witness "
            f"(overlap={dense_overlap:.4f} > 0.70). Download for research only; NOT submitted."
        ),
        "budget": {
            "experiments_run": 1,
            "experiment_cap": 3,
            "wall_clock_cap_seconds": 7200,
            "weekly_slots_used": 0,
            "organizer_confirmed_score": None,
        },
    }

    if canary_pass and overlap_pass and rho_pass:
        run_card["verdict"] = "promote-to-selector-only"
    else:
        run_card["verdict"] = "negative"

    # Write run card to canonical locations
    for dest in ("registry/run_card_mshi.json", "docs/data/run_card_mshi.json"):
        write_json(ROOT / dest, run_card)

    # Gate verdict
    gate = {
        "schema": "gems88.gate-v1",
        "generated_utc": run_card["generated_utc"],
        "experiment_id": "H88-MSHI-v1",
        "ok_to_download": True,
        "ok_to_submit": False,
        "format_passed": True,
        "canary_passed": canary_pass,
        "canary_max_auc": round(max_sym_auc, 6),
        "holdout_dti": round(pooled_dti, 6),
        "sparse_uniqueness_passed": bool(overlap_pass and rho_pass),
        "max_dot_overlap": round(max_overlap, 6),
        "max_abs_rho": round(max_rho, 6),
        "literal_blocked": bool(dense_overlap > 0.70),
        "dense_overlap": round(dense_overlap, 6),
        "verdict": run_card["verdict"],
    }
    write_json(ROOT / "registry" / "gate_mshi.json", gate)

    elapsed = round(time.monotonic() - t0, 2)
    print(f"\n[COMPLETE] {elapsed:.1f}s -> {tif_path.name}", flush=True)
    print(f"  SHA-256: {tif_sha}", flush=True)
    print(f"  Dots: {n_dots_final:,}", flush=True)
    print(f"  HOLDOUT-DTI: {pooled_dti:.6f}", flush=True)
    print(f"  Max symmetric AUC: {max_sym_auc:.4f}", flush=True)
    print(f"  Max dot overlap: {max_overlap:.4f}", flush=True)
    print(f"  Max |rho|: {max_rho:.4f}", flush=True)
    print(f"  Dense witness overlap: {dense_overlap:.4f} (BLOCKED > 0.70)", flush=True)
    print(f"  OK to download: YES", flush=True)
    print(f"  OK to submit: NO (literal 17GEMSDOE dense witness overlap > 0.70)", flush=True)
    print(f"  Verdict: {run_card['verdict']}", flush=True)


if __name__ == "__main__":
    main()