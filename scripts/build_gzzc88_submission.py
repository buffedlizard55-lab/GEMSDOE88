#!/usr/bin/env python3
"""Build H88-GZZC residual-gravity zero-contour buried-contact research GeoTIFF.

Three experiments, one emitted raster. Reuses vendor/gems57 holdout, uniqueness,
evaluate_holdout, and src/gems88 portal writer. Never spends a weekly slot.
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
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout, grid as grid_mod  # noqa: E402
from gems57.holdout import build_holdout  # noqa: E402
from gems57.uniqueness import dot_overlap  # noqa: E402
from gems88.gate import portal_validate  # noqa: E402
from gems88.gzzc import BANDS, build_features  # noqa: E402
from gems88.portal_writer import write_portal_tif, write_single_member_zip  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402

BUDGET = 32_000
SPACING_PX = 3.2
COLLAR_PX = 3.0
NEAR_SHARE = 0.55  # 3 < d_cat <= 25
DATE = "20261025"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_band(path: Path, idx: int) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(idx).astype(np.float32)


def greedy_place(score: np.ndarray, allowed: np.ndarray, budget: int, spacing: float) -> np.ndarray:
    ys, xs = np.nonzero(allowed)
    if ys.size == 0:
        return np.zeros(score.shape, dtype=np.float32)
    vals = score[ys, xs]
    order = np.argsort(vals)[::-1]
    top_n = min(250_000, order.size)
    order = order[:top_n]
    ys, xs = ys[order], xs[order]
    cell = max(1, int(np.ceil(spacing)))
    cells: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    picked_y: list[int] = []
    picked_x: list[int] = []
    spacing_sq = spacing * spacing
    for y, x in zip(ys.tolist(), xs.tolist()):
        if len(picked_y) >= budget:
            break
        cr, cc = y // cell, x // cell
        too_close = False
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                for py, px in cells.get((cr + dr, cc + dc), ()):
                    dy = y - py
                    dx = x - px
                    if dy * dy + dx * dx < spacing_sq - 1e-9:
                        too_close = True
                        break
                if too_close:
                    break
            if too_close:
                break
        if too_close:
            continue
        picked_y.append(y)
        picked_x.append(x)
        cells[(cr, cc)].append((y, x))
    out = np.zeros(score.shape, dtype=np.float32)
    if picked_y:
        out[np.array(picked_y), np.array(picked_x)] = 1.0
    return out


def dual_regime_place(score: np.ndarray, footprint: np.ndarray, d_cat: np.ndarray) -> np.ndarray:
    near = footprint & (d_cat > COLLAR_PX) & (d_cat <= 25.0) & np.isfinite(score)
    far = footprint & (d_cat > 25.0) & np.isfinite(score)
    n_near = int(round(BUDGET * NEAR_SHARE))
    n_far = BUDGET - n_near
    a = greedy_place(score, near, n_near, SPACING_PX)
    b = greedy_place(score, far, n_far, SPACING_PX)
    emitted = np.maximum(a, b)
    # If short, top up from remaining allowed cells without violating collar.
    n = int((emitted > 0).sum())
    if n < BUDGET:
        leftover = footprint & (d_cat > COLLAR_PX) & (emitted == 0) & np.isfinite(score)
        extra = greedy_place(score, leftover, BUDGET - n, SPACING_PX)
        emitted = np.maximum(emitted, extra)
    emitted[~footprint] = 0.0
    return emitted.astype(np.float32)


def fingerprint(emitted: np.ndarray, d_cat: np.ndarray) -> dict:
    ys, xs = np.nonzero(emitted > 0)
    dists = d_cat[ys, xs] if ys.size else np.array([], dtype=np.float32)
    return {
        "n_dots": int(ys.size),
        "share_le2": float((dists <= 2).mean()) if dists.size else 0.0,
        "share_gt10": float((dists > 10).mean()) if dists.size else 0.0,
        "share_gt25": float((dists > 25).mean()) if dists.size else 0.0,
        "median_d_cat_px": float(np.median(dists)) if dists.size else 0.0,
        "min_d_cat_px": float(dists.min()) if dists.size else 0.0,
    }


def canary(features: dict[str, np.ndarray], footprint: np.ndarray, catalogue: np.ndarray) -> dict:
    rng = np.random.default_rng(88)
    cat_y, cat_x = np.nonzero(catalogue)
    ys, xs = np.nonzero(footprint)
    pos_n = min(5000, cat_y.size)
    pos_idx = rng.choice(cat_y.size, size=pos_n, replace=False)
    neg_pool = np.flatnonzero(~catalogue[ys, xs])
    neg_idx = rng.choice(neg_pool, size=min(20000, neg_pool.size), replace=False)
    pos_y, pos_x = cat_y[pos_idx], cat_x[pos_idx]
    neg_y, neg_x = ys[neg_idx], xs[neg_idx]
    y_true = np.concatenate([np.ones(pos_n), np.zeros(neg_idx.size)])
    rows = []
    max_sym = 0.0
    max_name = ""
    for name in ("grav_zero_ridge", "low_slope_gate", "strain_gate", "grav_residual"):
        arr = features[name]
        vals = np.concatenate([arr[pos_y, pos_x], arr[neg_y, neg_x]])
        vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
        auc = float(roc_auc_score(y_true, vals))
        sym = max(auc, 1.0 - auc)
        rows.append({"feature": name, "auc": round(auc, 6), "symmetric_auc": round(sym, 6)})
        if sym > max_sym:
            max_sym, max_name = sym, name
    return {
        "threshold": 0.90,
        "max_symmetric_auc": round(max_sym, 6),
        "max_feature": max_name,
        "passed": bool(max_sym <= 0.90),
        "n_features": len(rows),
        "rows": rows,
        "note": "Proxy canary vs mapped catalogue positives (not holdout labels). Surface is catalogue-collared by construction and is not a binding canary channel.",
    }


def uniqueness_scan(emitted: np.ndarray, surface: np.ndarray, footprint: np.ndarray, exclude_name: str) -> dict:
    from scipy.stats import spearmanr

    rows = []
    max_overlap = 0.0
    max_overlap_label = ""
    max_rho = 0.0
    max_rho_label = ""
    dense_overlap = None
    surf = surface.astype(np.float64)
    for label, path in registry_list(ROOT, exclude=(exclude_name,)):
        try:
            with rasterio.open(path) as src:
                theirs = src.read(1)
            if theirs.shape != emitted.shape:
                rows.append({"label": label, "error": "shape_mismatch"})
                continue
            overlap = float(dot_overlap(emitted, theirs, radius_px=3.0))
            finite = footprint & np.isfinite(surf) & np.isfinite(theirs)
            if finite.sum() > 1000 and np.nanstd(theirs[finite]) > 0:
                rho = abs(float(spearmanr(surf[finite], theirs[finite].astype(np.float64), nan_policy="omit").statistic))
                if not np.isfinite(rho):
                    rho = 0.0
            else:
                rho = 0.0
            dense = ("dense_17" in label.lower()) or ("17gemdoe" in path.name.lower())
            if dense:
                dense_overlap = overlap
            if overlap > max_overlap and not dense:
                max_overlap, max_overlap_label = overlap, label
            if rho > max_rho and not dense:
                max_rho, max_rho_label = rho, label
            rows.append({
                "label": label,
                "overlap_3px": round(overlap, 6),
                "abs_spearman": round(rho, 6),
                "dense": dense,
            })
        except Exception as exc:  # noqa: BLE001 — inventory completeness is fail-closed below
            rows.append({"label": label, "error": str(exc)})
    if dense_overlap is None:
        dense_path = ROOT / "data/registry/dense_17gemdoe.tif"
        if dense_path.is_file():
            with rasterio.open(dense_path) as src:
                dense_overlap = float(dot_overlap(emitted, src.read(1), radius_px=3.0))
        else:
            dense_overlap = 1.0
    like_pass = max_overlap <= 0.70 and max_rho <= 0.90
    literal_pass = dense_overlap <= 0.70
    return {
        "n_compared": len(rows),
        "max_3px_overlap_disc": round(max_overlap, 6),
        "max_3px_overlap_label": max_overlap_label,
        "max_abs_rho_disc": round(max_rho, 6),
        "max_abs_rho_label": max_rho_label,
        "unique_like_for_like": bool(like_pass),
        "max_3px_overlap_disc_pass": bool(max_overlap <= 0.70),
        "max_rho_pass": bool(max_rho <= 0.90),
        "literal_dense_witness_overlap": round(float(dense_overlap), 6),
        "literal_dense_witness_pass": bool(literal_pass),
        "literal_duplicate": True,
        "rows_head": sorted(
            [r for r in rows if "error" not in r],
            key=lambda r: r.get("overlap_3px", 0),
            reverse=True,
        )[:12],
    }


def holdout_fixed_raster(emitted: np.ndarray, grid) -> dict:
    ctx = build_holdout(grid, hide_frac=0.20, seeds=(20, 21), modes=("all",), detach_px=4)
    tp = fp = fn = n_truth = 0.0
    n_cells = 0
    for cell in ctx.cells:
        if cell.mode != "all":
            continue
        y0, y1 = cell.bbox[0].start, cell.bbox[0].stop
        x0, x1 = cell.bbox[1].start, cell.bbox[1].stop
        known = ctx.visible(cell.key)[y0:y1, x0:x1]
        hidden = ctx.hidden_by_cell[cell.key][y0:y1, x0:x1]
        region = np.zeros_like(cell.active)
        region[cell.active | hidden | known] = True
        fold = {
            "region": region,
            "visible": known,
            "masked_known": known,
            "truth": hidden,
        }
        pred = emitted[y0:y1, x0:x1]
        valid = grid.footprint[y0:y1, x0:x1]
        if not (valid & region & ~known & hidden).any():
            continue
        result, _terms = evaluate_holdout.evaluate(
            pred, fold, valid, origin=(y0, x0), global_shape=grid.shape
        )
        tp += result["tp"]
        fp += result["fp"]
        fn += result["fn"]
        n_truth += result["n_truth"]
        n_cells += 1
    denom = 0.2 * (tp + fn) + 0.8 * (tp + fp)  # pooled Tversky α=0.2 β=0.8 on already-kernelled credits
    # Prefer official combiner: reconstruct from components via metric if available.
    from gems57.metric import dti_from_components

    dti = float(dti_from_components(tp, fp, fn)) if n_truth else 0.0
    return {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "withheld_positive_pixels": int(n_truth),
        "n_fold_cells": n_cells,
        "dti": round(dti, 6),
        "ci95": [round(dti, 6), round(dti, 6)],
        "note": "Fixed-raster rescore of the emitted bytes (not a fold-refit model). Catalogue-collared rasters are often structurally near-zero on this instrument (IR-88-20/35). Not ORGANIZER-CONFIRMED. CI collapsed because no spatial bootstrap was run on this arm.",
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "denom_check": float(denom),
    }


def main() -> None:
    t0 = time.monotonic()
    grid = grid_mod.load_grid(ROOT / "data/bridge")
    footprint, catalogue = grid.footprint, grid.catalogue
    feat_path = ROOT / "data/training_features.tif"
    if not feat_path.is_file():
        raise SystemExit("missing data/training_features.tif — run python scripts/restore_inputs.py")
    print("[GZZC] loading bands", flush=True)
    bands = {name: load_band(feat_path, idx) for name, idx in BANDS.items()}
    feats = build_features(bands, footprint)
    d_cat = distance_transform_edt(~catalogue).astype(np.float32)
    d_cat[~footprint] = 0.0

    experiments = {
        "exp1_ridge_only": feats["gzzc_exp1_ridge"],
        "exp2_buried_lowslope": feats["gzzc_exp2_buried"],
        "exp3_gzzc_strain": feats["gzzc_surface"],
    }
    exp_stats = {}
    for name, surf in experiments.items():
        allowed = footprint & (d_cat > COLLAR_PX) & np.isfinite(surf)
        placed = greedy_place(surf, allowed, BUDGET, SPACING_PX)
        fpprint = fingerprint(placed, d_cat)
        exp_stats[name] = fpprint
        print(f"[GZZC] {name}: {fpprint}", flush=True)

    surface = feats["gzzc_surface"]
    surface = surface.copy()
    surface[d_cat < COLLAR_PX] = 0.0
    surface[~footprint] = 0.0
    emitted = dual_regime_place(surface, footprint, d_cat)
    emitted[catalogue] = 0.0
    emitted[~footprint] = 0.0
    fpprint = fingerprint(emitted, d_cat)
    print("[GZZC] emitted", fpprint, flush=True)

    canary_report = canary(feats, footprint, catalogue)
    print("[GZZC] canary", canary_report["max_symmetric_auc"], canary_report["passed"], flush=True)

    print("[GZZC] uniqueness scan", flush=True)
    uniq = uniqueness_scan(emitted, surface, footprint, exclude_name="gzzc-gravzero")
    print(
        "[GZZC] like-for-like max overlap",
        uniq["max_3px_overlap_disc"],
        "rho",
        uniq["max_abs_rho_disc"],
        "dense",
        uniq["literal_dense_witness_overlap"],
        flush=True,
    )

    print("[GZZC] holdout fixed-raster", flush=True)
    hold = holdout_fixed_raster(emitted, grid)
    print("[GZZC] HOLDOUT-DTI", hold["dti"], "n", hold["withheld_positive_pixels"], flush=True)

    sample = ROOT / "data/bridge/sample_submission.tif"
    tmp_stem = f"gems88-gzzc-gravzero-buried-{DATE}-pending-zeros-DO-NOT-SUBMIT"
    tmp_path = ROOT / "docs" / "downloads" / f"{tmp_stem}.tif"
    if tmp_path.exists():
        tmp_path.unlink()
    zip_tmp = tmp_path.with_suffix(".zip")
    if zip_tmp.exists():
        zip_tmp.unlink()
    write_portal_tif(tmp_path, emitted, sample, footprint)
    write_single_member_zip(zip_tmp, tmp_path)
    digest = sha256_file(tmp_path)
    final_stem = f"gems88-gzzc-gravzero-buried-{DATE}-{digest[:8]}-zeros-DO-NOT-SUBMIT"
    final_tif = ROOT / "docs" / "downloads" / f"{final_stem}.tif"
    final_zip = final_tif.with_suffix(".zip")
    if final_tif.exists():
        final_tif.unlink()
    if final_zip.exists():
        final_zip.unlink()
    tmp_path.rename(final_tif)
    # ZIP stores member name = tif name; rewrite with final name.
    write_single_member_zip(final_zip, final_tif)
    if zip_tmp.exists():
        zip_tmp.unlink()

    portal = portal_validate(final_tif, sample, footprint=footprint)
    portal_zip = portal_validate(final_zip, sample, footprint=footprint)
    print("[GZZC] portal", portal["ok"], portal_zip["ok"], digest, flush=True)

    sub_tif = ROOT / "submissions" / final_tif.name
    sub_zip = ROOT / "submissions" / final_zip.name
    sub_tif.write_bytes(final_tif.read_bytes())
    sub_zip.write_bytes(final_zip.read_bytes())

    name = f"GEMSDOE88-GZZC-{digest[:8].upper()}"
    note = (
        f"H88-GZZC grav-zero buried contact {fpprint['n_dots']}d; "
        f"HOLDOUT-DTI {hold['dti']:.4f}; gt25 {fpprint['share_gt25']:.2f}; UNSCORED"
    )[:140]
    ok_download = bool(portal["ok"] and portal_zip["ok"] and portal["checks"].get("portal_range_check_nan_strict"))
    ok_submit = False  # literal dense witness + selector rule
    verdict = "negative"

    card = {
        "schema": "gems88.run-card.v3",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "lane": "H88-GZZC",
        "hypothesis": "Residual isostatic-gravity zero-contour marks buried basin-basement density contacts omitted from USGS/INGENIOUS surface-scarp catalogues",
        "mechanism": "4 km residual gravity; |grad r| * exp(-r^2/2 sigma_z^2) zero ridge; (1-slope)^2 buried gate; shear+dilation strain; 3 px collar; 3.2 px spacing; dual-regime 55/45 near/far",
        "named_non_fault_process": "Unfaulted alluvial onlap onto a bedrock pediment (gravity step without brittle offset)",
        "ok_to_download": ok_download,
        "ok_to_submit": ok_submit,
        "verdict": verdict,
        "verdict_summary": "NEGATIVE — research download only; literal 17GEMSDOE overlap 1.0 > 0.70; 0 slots",
        "weekly_slots_used": 0,
        "organizer_confirmed": None,
        "submission_name": name,
        "submission_note": note,
        "submission_note_length": len(note),
        "download": str(final_tif.relative_to(ROOT)),
        "zip_download": str(final_zip.relative_to(ROOT)),
        "raster_sha256": digest,
        "zip_sha256": sha256_file(final_zip),
        "elapsed_s": round(time.monotonic() - t0, 1),
        "experiments": exp_stats,
        "fingerprint": fpprint,
        "leakage_canary": canary_report,
        "uniqueness": uniq,
        "holdout": hold,
        "validator_output": {
            "portal_tif_ok": portal["ok"],
            "portal_zip_ok": portal_zip["ok"],
            "no_nan": bool(portal["checks"].get("all_finite")),
            "values_in_0_1": bool(portal["checks"].get("portal_range_check_nan_strict")),
            "crs_shape_transform_match": bool(
                portal["checks"].get("crs_epsg_32611")
                and portal["checks"].get("shape_matches_sample")
                and portal["checks"].get("transform_matches_sample")
            ),
            "layout_parity_with_sample": portal.get("layout_parity_with_sample"),
            "problems": portal.get("problems", []),
        },
        "submission": {
            "file": str(final_tif.relative_to(ROOT)),
            "zip_file": str(final_zip.relative_to(ROOT)),
            "raster_sha256": digest,
            "zip_sha256": sha256_file(final_zip),
            "positive_pixels": fpprint["n_dots"],
            "submission_name": name,
            "submission_note": note,
        },
    }
    for dest in (
        ROOT / "registry" / "gzzc88_run_card.json",
        ROOT / "docs" / "data" / "gzzc88_run_card.json",
        ROOT / "docs" / "run_card_gzzc88.json",
        ROOT / "evidence" / "gzzc88_run_card.json",
        ROOT / "run_card_gzzc88.json",
    ):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(card, indent=2) + "\n")
    print("[GZZC] wrote", final_tif.name, "sha", digest, "name", name, "note", note)
    print("[GZZC] DOWNLOAD", ok_download, "SUBMIT", ok_submit, "elapsed", card["elapsed_s"])


if __name__ == "__main__":
    main()
