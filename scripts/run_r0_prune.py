#!/usr/bin/env python3
"""Build and validate R0's PRUNE<=3 fixed-count experiment, without submitting.

Run from the repository root:
    PYTHONPATH=src:vendor .venv/bin/python scripts/run_r0_prune.py
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout as eh  # noqa: E402
from gems57 import holdout as ho  # noqa: E402
from gems57 import metric  # noqa: E402
from gems57.grid import Grid  # noqa: E402
from gems88.r0_prune import (  # noqa: E402
    R0_DOTS,
    R0_ZEROS_SHA256,
    bfs_order,
    dot_thin_from_order,
    prune3_refill,
    sha256_file,
    validate_release_raster,
    write_mask,
)

DATA = ROOT / "data"
WORK = ROOT / "work"
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
PARENT = "h33-h33-2-b2"
AXIS = "PRUNE"
VALUE = "3"
DATE = "20261023"
SEED = 20261023
PREDICTED = "MODEL:-0.003"
NOTE = "R0 h33-h33-2-b2; PRUNE<=3px + fixed-count H19 BFS refill (2171 dots); MODEL -0.003 live DTI"
PINS = {
    "sample_submission": (
        DATA / "bridge" / "sample_submission.tif",
        "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    ),
    "existing_faults": (
        DATA / "bridge" / "existing_faults.tif",
        "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    ),
    "h19_5": (
        DATA / "scored" / "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif",
        "ec1f9b56b83ce33cad781ceb9f104b18fb4f2ff785263a4e89616af4aabdee8d",
    ),
    "d2_8": (
        DATA / "scored" / "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
        "91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8",
    ),
    "r0_reference": (DATA / "registry" / "h33_education.tif", R0_ZEROS_SHA256),
    "sgmc_control": (
        DATA / "external" / "derived_sgmc_faults_100m_u8.tif",
        "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
    ),
}
LEDGER_FIELDS = [
    "id",
    "parent",
    "axis",
    "value",
    "n_dots",
    "pct_changed",
    "sha256",
    "status",
    "predicted_change",
    "receipt_score",
    "receipt_date",
]


def verify_pins() -> dict:
    receipt = {}
    for name, (path, expected) in PINS.items():
        if not path.is_file():
            raise FileNotFoundError(f"pinned input missing: {path}; run the documented restore step")
        got = sha256_file(path)
        if got != expected:
            raise ValueError(f"PIN MISMATCH {name}: {got} != {expected}")
        receipt[name] = {"path": str(path.relative_to(ROOT)), "sha256": got, "integrity": "PASS"}
        print(f"PIN OK {name} {got}", flush=True)
    return receipt


def read_rasters() -> tuple[Grid, np.ndarray, np.ndarray, np.ndarray]:
    with rasterio.open(PINS["sample_submission"][0]) as src:
        sample = src.read(1)
        footprint = np.isfinite(sample) & (src.read_masks(1) > 0)
        crs, transform = src.crs, src.transform
    with rasterio.open(PINS["existing_faults"][0]) as src:
        catalogue = (src.read(1) > 0) & footprint
    with rasterio.open(PINS["h19_5"][0]) as src:
        h19 = src.read(1)
    with rasterio.open(PINS["d2_8"][0]) as src:
        d28 = src.read(1)
    grid = Grid(
        footprint=footprint,
        catalogue=catalogue,
        crs=crs,
        transform=transform,
        height=footprint.shape[0],
        width=footprint.shape[1],
    )
    support = (np.nan_to_num(h19, nan=0.0) > 0.5) & footprint & ~catalogue
    d28_mask = (np.nan_to_num(d28, nan=0.0) > 0.5) & footprint
    return grid, support, d28_mask, np.nan_to_num(d28, nan=0.0)


def check_ledger_pair() -> None:
    if not LEDGER.is_file():
        return
    with LEDGER.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("parent"), row.get("axis"), row.get("value")) == (PARENT, AXIS, VALUE):
                raise ValueError(f"(parent, axis, value) already exists in ledger: {row}")


def known_hashes() -> set[str]:
    hashes = {expected for _, expected in PINS.values()}
    if LEDGER.is_file():
        with LEDGER.open(newline="", encoding="utf-8") as f:
            hashes.update(row["sha256"] for row in csv.DictReader(f) if row.get("sha256"))
    # Exact-hash dedupe only. No rank-correlation or overlap uniqueness gate.
    for directory in (DATA / "registry", ROOT / "submissions", ROOT / "docs" / "downloads", RELEASES):
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.tif"):
            if path.is_file():
                hashes.add(sha256_file(path))
    return hashes


def nearest_neighbour_stats(mask: np.ndarray) -> dict:
    from scipy.spatial import cKDTree

    pts = np.argwhere(mask)
    distances = cKDTree(pts).query(pts, k=2)[0][:, 1]
    return {
        "min_px": float(distances.min()),
        "mean_px": float(distances.mean()),
        "p05_px": float(np.percentile(distances, 5)),
        "p95_px": float(np.percentile(distances, 95)),
    }


def rank_auc(pos: np.ndarray, neg: np.ndarray) -> float:
    n_pos, n_neg = len(pos), len(neg)
    if not n_pos or not n_neg:
        raise ValueError("AUC requires nonempty positive and negative samples")
    ranks = rankdata(np.concatenate([pos, neg]), method="average")
    return float((ranks[:n_pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def canary_report(support: np.ndarray, folds: list[dict], footprint: np.ndarray, d_full: np.ndarray) -> dict:
    """Single-feature diagnostics with catalogue distance recomputed per visible fold."""
    rng = np.random.default_rng(88)
    samples = {"fold_visible_catalogue_distance_px": ([], []), "h19_5_binary_support": ([], [])}
    invalidated_pos, invalidated_neg = [], []
    for fold in folds:
        region = fold["region"] & footprint
        pos = np.flatnonzero(fold["truth"] & region)
        negative = region & ~fold["masked_known"] & ~fold["truth"]
        negative &= ~ndi.binary_dilation(fold["truth"], iterations=3)
        candidates = np.flatnonzero(negative)
        n = min(len(pos), len(candidates), 2500)
        if n == 0:
            raise ValueError("empty canary sample")
        pos_ids = rng.choice(pos, n, replace=False)
        neg_ids = rng.choice(candidates, n, replace=False)
        d_visible = ndi.distance_transform_edt(~fold["visible"])
        invalidated_pos.append(d_full.ravel()[pos_ids])
        invalidated_neg.append(d_full.ravel()[neg_ids])
        for name, feature in (
            ("fold_visible_catalogue_distance_px", d_visible),
            ("h19_5_binary_support", support),
        ):
            samples[name][0].append(feature.ravel()[pos_ids])
            samples[name][1].append(feature.ravel()[neg_ids])
    rows = []
    for name, (pos_parts, neg_parts) in samples.items():
        pos_values, neg_values = np.concatenate(pos_parts), np.concatenate(neg_parts)
        auc = rank_auc(pos_values, neg_values)
        rows.append(
            {
                "feature": name,
                "auc": auc,
                "symmetric_auc": max(auc, 1.0 - auc),
                "withheld_sample": int(len(pos_values)),
                "negative_sample": int(len(neg_values)),
            }
        )
    invalidated_auc = rank_auc(np.concatenate(invalidated_pos), np.concatenate(invalidated_neg))
    return {
        "evidence_class": "PROXY",
        "rows": rows,
        "max_symmetric_auc": max(row["symmetric_auc"] for row in rows),
        "investigation_required": any(row["symmetric_auc"] > 0.90 for row in rows),
        "invalidated_full_catalogue_distance_check": {
            "symmetric_auc": max(invalidated_auc, 1.0 - invalidated_auc),
            "status": "INVALIDATED: hidden catalogue geometry was present in the feature",
        },
        "note": "Fold-visible distance repairs the invalidated full-catalogue AUC=1 diagnostic; no hidden catalogue geometry enters a fold feature.",
    }


def proxy_report(support: np.ndarray, d28: np.ndarray, grid: Grid) -> dict:
    """Fold-rebuilt mechanism PROXY; never a direct score of the released file.

    Both arms are reconstructed using only each fold's visible catalogue.  The
    H19-5/D2.8 support remains frozen and already excludes the full catalogue,
    so no withheld truth pixel itself can be emitted.  This avoids the trivial
    full-catalogue exclusion artifact while retaining a conservative support
    limitation shared by both arms.
    """
    folds, _ = ho.buffered_component_draw(grid, seed=20)
    terms = {"R0": None, "candidate": None}
    fold_scores = {"R0": {}, "candidate": {}}
    fold_construction = {}
    for fold in folds:
        d_visible = ndi.distance_transform_edt(~fold["visible"])
        r0_fold = d28 & grid.footprint & (d_visible > 2.0)
        n_fold = int(r0_fold.sum())
        candidate_fold, _, _, diff = prune3_refill(r0_fold, support, d_visible, n_dots=n_fold)
        fold_construction[fold["name"]] = {
            "r0_dots": n_fold,
            "candidate_dots": int(candidate_fold.sum()),
            "removed_parent_dots": diff["removed_parent_dots"],
            "added_dots": diff["added_dots"],
            "catalogue_context": "fold-visible only",
        }
        for name, mask in (("R0", r0_fold), ("candidate", candidate_fold)):
            score, block_terms = eh.evaluate(
                mask.astype(np.float32),
                fold,
                grid.footprint,
                block_side=200,
                global_shape=grid.shape,
            )
            terms[name] = block_terms if terms[name] is None else terms[name] + block_terms
            fold_scores[name][fold["name"]] = score["dti"]
    pooled = eh.pooled_summary(terms, draws=2000, seed=520810, candidate="candidate")
    return {
        "evidence_class": "PROXY",
        "evaluator_version": eh.VERSION,
        "holdout_seed": 20,
        "design": "fold-visible, fold-rebuilt paired mechanism comparison; not a direct file score",
        "support_limitation": "H19-5/D2.8 support is frozen and full-catalogue-excised in both arms; original model training is not refit",
        "withheld_positive_pixels": pooled["scores"]["candidate"]["withheld_positive_pixels"],
        "fold_dti": fold_scores,
        "fold_construction": fold_construction,
        "pooled": pooled,
        "gate": False,
    }, folds


def sgmc_report(r0: np.ndarray, candidate: np.ndarray, grid: Grid) -> dict:
    with rasterio.open(PINS["sgmc_control"][0]) as src:
        sgmc = src.read(1) > 0
    truth = sgmc & grid.footprint & ~grid.catalogue & ~ndi.binary_dilation(grid.catalogue, iterations=3)
    scores = {
        name: metric.dti_binary(mask, truth, valid=grid.footprint, known=grid.catalogue)
        for name, mask in (("R0", r0), ("candidate", candidate))
    }
    return {
        "evidence_class": "PROXY",
        "control": "USGS SGMC off-catalogue traces beyond a 3 px catalogue collar; uncalibrated prevalence",
        "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE24/blob/07345ea0604953d7efb858d9cfbc21e20c7aca0b/data/external/derived_sgmc_faults_100m_u8.tif",
        "license": "USGS public-domain source product; derived mirror is integrity-pinned, not organizer-authenticated",
        "truth_pixels": int(truth.sum()),
        "scores": scores,
        "delta_candidate_minus_r0": scores["candidate"]["dti"] - scores["R0"]["dti"],
        "gate": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-diagnostics", action="store_true", help="build only; diagnostics are report-only, never format gates")
    args = parser.parse_args()
    check_ledger_pair()
    pin_receipt = verify_pins()
    if len(NOTE) > 140:
        raise ValueError("submission note exceeds 140 characters")
    grid, support, d28_reference, _ = read_rasters()
    d_cat = ndi.distance_transform_edt(~grid.catalogue)

    # Rebuild D2.8 and R0 from the recorded H19-5 binary + geodesic BFS recipe.
    padded, order, pad = bfs_order(support)
    d28_rebuilt = dot_thin_from_order(padded, order, pad)
    if not np.array_equal(d28_rebuilt, d28_reference):
        raise ValueError(f"D2.8 reproduction failed: {np.count_nonzero(d28_rebuilt != d28_reference)} differing pixels")
    r0 = d28_rebuilt & grid.footprint & (d_cat > 2.0)
    if int(r0.sum()) != R0_DOTS or np.any(r0 & (d_cat <= 2.0)):
        raise ValueError("R0 geometry/count reproduction failed")
    WORK.mkdir(exist_ok=True)
    r0_path = WORK / "r0-rebuilt-zeros.tif"
    r0_hash = write_mask(r0_path, r0, grid.footprint, PINS["existing_faults"][0], nan_outside=False)
    if r0_hash != R0_ZEROS_SHA256:
        raise ValueError(f"R0 byte reproduction failed: {r0_hash} != {R0_ZEROS_SHA256}; STOP")
    with rasterio.open(PINS["r0_reference"][0]) as src:
        if not np.array_equal(src.read(1) > 0.5, r0):
            raise ValueError("R0 differs from pinned reference pixels")
    print(f"R0 REPRODUCTION PASS {r0_hash} ({R0_DOTS} dots)", flush=True)

    candidate, removed, added, diff = prune3_refill(r0, support, d_cat)
    if not 1.0 <= diff["pct_parent_dots_changed"] <= 50.0:
        raise ValueError("variant changes outside the required 1-50% of R0 dots")
    diff["parent_nearest_neighbour"] = nearest_neighbour_stats(r0)
    diff["candidate_nearest_neighbour"] = nearest_neighbour_stats(candidate)
    diff["parent_dots_d_cat_le_3"] = int((r0 & (d_cat <= 3)).sum())
    diff["candidate_dots_d_cat_le_3"] = int((candidate & (d_cat <= 3)).sum())
    print(json.dumps(diff, indent=2), flush=True)

    # Serialize once to learn the content-addressed ID, then check exact-hash reuse.
    tmp_nan = WORK / "prune3-candidate-nan.tif"
    tmp_zeros = WORK / "prune3-candidate-zeros.tif"
    nan_hash = write_mask(tmp_nan, candidate, grid.footprint, PINS["existing_faults"][0], nan_outside=True)
    zeros_hash = write_mask(tmp_zeros, candidate, grid.footprint, PINS["existing_faults"][0], nan_outside=False)
    used = known_hashes()
    if nan_hash in used or zeros_hash in used:
        raise ValueError("candidate exact SHA-256 already exists in ledger or accessible artifact registry")
    candidate_id = f"{PARENT}-prune3-{DATE}-{nan_hash[:8]}"
    RELEASES.mkdir(exist_ok=True)
    nan_path = RELEASES / f"{candidate_id}.tif"
    zeros_path = RELEASES / f"{candidate_id}-zeros.tif"
    for tmp, final in ((tmp_nan, nan_path), (tmp_zeros, zeros_path)):
        if final.exists() and sha256_file(final) != sha256_file(tmp):
            raise FileExistsError(f"refusing to overwrite different release: {final}")
        shutil.copyfile(tmp, final)
    nan_validation = validate_release_raster(
        nan_path, candidate, grid.footprint, grid.catalogue, d_cat, PINS["sample_submission"][0], nan_outside=True
    )
    zeros_validation = validate_release_raster(
        zeros_path, candidate, grid.footprint, grid.catalogue, d_cat, PINS["sample_submission"][0], nan_outside=False
    )

    diagnostics = {}
    if not args.skip_diagnostics:
        proxy, folds = proxy_report(support, d28_reference, grid)
        diagnostics["catalogue_hide_recover"] = proxy
        diagnostics["leakage_canary"] = canary_report(support.astype(np.float32), folds, grid.footprint, d_cat)
        diagnostics["sgmc_control"] = sgmc_report(r0, candidate, grid)

    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run_card = {
        "schema": "gems88.r0-prune-run.v1",
        "id": candidate_id,
        "parent": PARENT,
        "axis": AXIS,
        "value": VALUE,
        "status": "BUILT",
        "git_sha": git_sha,
        "seed": SEED,
        "input_pins": pin_receipt,
        "parent_reproduction": {
            "sha256": r0_hash,
            "expected_sha256": R0_ZEROS_SHA256,
            "pixel_identical": True,
            "d2_8_pixel_identical": True,
            "n_dots": R0_DOTS,
        },
        "parent_diff": diff,
        "predicted_change": {"evidence_class": "MODEL", "delta_live_dti": -0.003, "plausible_range": [-0.01, 0.004]},
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "primary": nan_validation,
        "zeros_fallback": zeros_validation,
        "diagnostics_report_only": diagnostics,
        "submission_slots_used": 0,
        "submitted": False,
    }
    receipt_path = RELEASES / f"{candidate_id}-receipt.json"
    receipt_path.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    LEDGER.parent.mkdir(exist_ok=True)
    write_header = not LEDGER.is_file()
    with LEDGER.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "id": candidate_id,
                "parent": PARENT,
                "axis": AXIS,
                "value": VALUE,
                "n_dots": R0_DOTS,
                "pct_changed": f"{diff['pct_parent_dots_changed']:.9f}",
                "sha256": nan_hash,
                "status": "BUILT",
                "predicted_change": PREDICTED,
                "receipt_score": "",
                "receipt_date": "",
            }
        )
    print(f"BUILT {candidate_id}\nNAN {nan_hash}\nZEROS {zeros_hash}\nRECEIPT {receipt_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
