#!/usr/bin/env python3
"""Rebuild R0 exactly and make fixed-count CONCENTRATION variants.

The only treatment is the fraction of R0 dots relocated from low-prior to
high-prior 1 km blocks.  The prior is fixed before all treatments: the mean
of robustly scaled official TMI horizontal gradient, isostatic-gravity slope,
and isostatic-gravity horizontal gradient.  No labels are used except for the
published catalogue exclusion mask.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import zipfile

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SAMPLE = DATA / "bridge/sample_submission.tif"
CATALOGUE = DATA / "bridge/existing_faults.tif"
FEATURES = DATA / "training_features.tif"
ANCESTOR = DATA / "registry/family_60gemsdoe/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
PARENT_MIRROR = DATA / "registry/h33_education.tif"
PARENT_ID = "h33-h33-2-b2"
DATE = "20261023"
BLOCK_PX = 10
EXPECTED = {
    SAMPLE: "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    CATALOGUE: "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    FEATURES: "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    ANCESTOR: "91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8",
    PARENT_MIRROR: "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
}
PARENT_SHA = EXPECTED[PARENT_MIRROR]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_inputs() -> None:
    for path, expected in EXPECTED.items():
        actual = digest(path)
        if actual != expected:
            raise ValueError(f"PIN FAIL {path}: {actual} != {expected}")
        print(f"PIN OK {path.relative_to(ROOT)} {actual}")


def output_profile(nodata: float | None) -> dict:
    with rasterio.open(SAMPLE) as ds:
        profile = ds.profile.copy()
    profile.update(
        driver="GTiff", dtype="float32", count=1, compress="deflate",
        predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256,
        nodata=nodata,
    )
    return profile


def write_tif(path: Path, arr: np.ndarray, nodata: float | None) -> None:
    with rasterio.open(path, "w", **output_profile(nodata)) as ds:
        ds.write(arr.astype(np.float32, copy=False), 1)


def rebuild_parent(foot: np.ndarray, catalogue: np.ndarray, distance: np.ndarray) -> np.ndarray:
    """Reproduce H33-2-B2: D2.8 ancestor with all d_catalogue <=2 dots removed."""
    with rasterio.open(ANCESTOR) as ds:
        base = np.isfinite(ds.read(1)) & (ds.read(1) > 0)
    rebuilt = base & foot & (distance > 2.0)
    arr = np.where(foot, rebuilt, 0.0).astype(np.float32)
    out = DATA / "rebuilt-r0.tif"
    write_tif(out, arr, None)
    actual = digest(out)
    if actual != PARENT_SHA:
        raise ValueError(f"STOP: rebuilt R0 hash {actual} != named parent {PARENT_SHA}")
    with rasterio.open(PARENT_MIRROR) as ds:
        mirror = ds.read(1)
    if not np.array_equal(arr, mirror):
        raise ValueError("STOP: rebuilt R0 pixels differ from pinned parent mirror")
    print(f"R0 REBUILD EXACT {actual}; dots={int(rebuilt.sum())}")
    return rebuilt


def robust_unit(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    vals = a[valid & np.isfinite(a)]
    lo, hi = np.percentile(vals, [10.0, 99.0])
    out = np.zeros(a.shape, np.float32)
    out[valid] = np.clip((a[valid] - lo) / max(float(hi - lo), 1e-12), 0, 1)
    return out


def structural_prior(foot: np.ndarray) -> tuple[np.ndarray, list[str]]:
    # Official 1-indexed bands 3, 5, 18; all are edge/gradient responses.
    with rasterio.open(FEATURES) as ds:
        arrays = [ds.read(i).astype(np.float32) for i in (3, 5, 18)]
        names = [ds.descriptions[i - 1].split(" - ")[0] for i in (3, 5, 18)]
        nodata = ds.nodata
    units = []
    for a in arrays:
        valid = foot & np.isfinite(a) & (a != nodata)
        units.append(robust_unit(a, valid))
    prior = np.mean(units, axis=0, dtype=np.float32)
    prior[~foot] = 0
    return prior, names


def block_statistics(foot: np.ndarray, prior: np.ndarray, dots: np.ndarray):
    h, w = foot.shape
    nbc = math.ceil(w / BLOCK_PX)
    rr, cc = np.indices((h, w), sparse=True)
    block_id = (rr // BLOCK_PX) * nbc + (cc // BLOCK_PX)
    nblocks = math.ceil(h / BLOCK_PX) * nbc
    valid_count = np.bincount(block_id[foot], minlength=nblocks)
    prior_sum = np.bincount(block_id[foot], weights=prior[foot], minlength=nblocks)
    block_prior = np.divide(prior_sum, valid_count, out=np.full(nblocks, np.nan), where=valid_count > 0)
    dot_count = np.bincount(block_id[dots], minlength=nblocks)
    return block_id, valid_count, block_prior, dot_count


def density_cv(dot_count: np.ndarray, valid_count: np.ndarray) -> dict[str, float]:
    full = valid_count == BLOCK_PX * BLOCK_PX
    density = dot_count[full] / valid_count[full]
    all_cv = float(np.std(density) / np.mean(density))
    occupied = full & (dot_count > 0)
    occ = dot_count[occupied] / valid_count[occupied]
    occupied_cv = float(np.std(occ) / np.mean(occ))
    return {"all_full_blocks": all_cv, "occupied_full_blocks": occupied_cv,
            "n_full_blocks": int(full.sum()), "n_occupied_full_blocks": int(occupied.sum())}


def validate(path: Path, sample_grid: tuple, foot: np.ndarray, catalogue: np.ndarray,
             distance: np.ndarray, expected_dots: int, nan_outside: bool) -> dict:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
        if (ds.shape, ds.crs, ds.transform) != sample_grid:
            raise ValueError(f"grid mismatch: {path}")
        if ds.count != 1 or ds.dtypes != ("float32",):
            raise ValueError(f"band/dtype mismatch: {path}")
    if not np.isfinite(arr[foot]).all() or not np.isin(arr[foot], [0.0, 1.0]).all():
        raise ValueError(f"inside format failure: {path}")
    if nan_outside and not np.isnan(arr[~foot]).all():
        raise ValueError(f"outside must be NaN: {path}")
    if not nan_outside and not np.all(arr[~foot] == 0):
        raise ValueError(f"outside must be zero: {path}")
    dots = (arr > 0) & foot
    if int(dots.sum()) != expected_dots or np.any(dots & catalogue):
        raise ValueError(f"dot count/catalogue failure: {path}")
    # R0's explicit >2 px collar is inherited to avoid confounding CONCENTRATION with PRUNE.
    if np.any(distance[dots] <= 2.0):
        raise ValueError(f"2 px collar failure: {path}")
    return {"sha256": digest(path), "n_dots": int(dots.sum()),
            "min_catalogue_distance_px": float(distance[dots].min())}


def update_ledgers(rows: list[dict], cards: dict) -> None:
    ledger = ROOT / "ledger/submissions.csv"
    fields = ["id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256",
              "sha256_zeros", "status", "predicted_change", "predicted_range",
              "ranking_basis", "receipt_score", "receipt_date", "description",
              "recommendation"]
    existing = []
    if ledger.exists():
        with ledger.open(newline="") as f:
            reader = csv.DictReader(f)
            existing = list(reader)
            if reader.fieldnames != fields:
                raise ValueError(f"unexpected ledger schema: {reader.fieldnames}")
    ids = {r["id"] for r in existing}
    pairs = {(r.get("parent"), r.get("axis"), r.get("value")) for r in existing}
    for row in rows:
        pair = (row["parent"], row["axis"], row["value"])
        if row["id"] in ids or pair in pairs:
            raise ValueError(f"ledger duplicate: {row['id']} / {pair}")
        existing.append(row)
    with ledger.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(existing)
    card_path = ROOT / "ledger/mechanism_cards.json"
    old = json.loads(card_path.read_text()) if card_path.exists() else {}
    overlap = set(old) & set(cards)
    if overlap:
        raise ValueError(f"mechanism-card duplicate: {sorted(overlap)}")
    old.update(cards)
    card_path.write_text(json.dumps(old, indent=2) + "\n")


def main() -> None:
    verify_inputs()
    with rasterio.open(SAMPLE) as ds:
        sample_grid = (ds.shape, ds.crs, ds.transform)
    with rasterio.open(CATALOGUE) as ds:
        cat_arr = ds.read(1)
    foot = np.isin(cat_arr, [0.0, 1.0])
    catalogue = cat_arr == 1.0
    distance = distance_transform_edt(~catalogue)
    parent = rebuild_parent(foot, catalogue, distance)
    n_parent = int(parent.sum())
    if n_parent != 37_654:
        raise ValueError("unexpected parent count")

    prior, prior_bands = structural_prior(foot)
    block_id, valid_count, block_prior, parent_block_count = block_statistics(foot, prior, parent)
    cv_before = density_cv(parent_block_count, valid_count)

    parent_rows, parent_cols = np.where(parent)
    parent_bid = block_id[parent]

    # Remove low-prior dots while leaving at least one parent dot in each donor
    # block. This avoids conflating the treatment with a loss of spatial coverage
    # and preferentially removes excess density (the geological claim concerns
    # kilometre-scale allocation, not creation of holes).
    donor_blocks = np.where(parent_block_count > 1)[0]
    donor_blocks = donor_blocks[np.argsort(block_prior[donor_blocks])]
    parent_by_block: dict[int, list[int]] = {}
    for idx in np.lexsort((prior[parent_rows, parent_cols], parent_bid)):
        parent_by_block.setdefault(int(parent_bid[idx]), []).append(int(idx))
    remove_order_list: list[int] = []
    for bid in donor_blocks:
        # Keep the highest local-prior parent dot; all others may move.
        remove_order_list.extend(parent_by_block[int(bid)][:-1])
    remove_order = np.asarray(remove_order_list, dtype=np.int64)

    allowed = foot & (distance > 2.0) & ~parent
    cand_rows, cand_cols = np.where(allowed)
    cand_bid = block_id[allowed]
    # "Highest-prior blocks" is frozen as the upper 30% of full 1 km blocks.
    # Add one dot per currently empty receiver block before adding a second dot.
    # This targets high-prior zones without producing a handful of pathological
    # 100-dot blocks; it also makes the requested CV diagnostic interpretable.
    eligible_blocks = np.where(valid_count == BLOCK_PX * BLOCK_PX)[0]
    high_cut = float(np.quantile(block_prior[eligible_blocks], 0.70))
    receiver_blocks = eligible_blocks[(block_prior[eligible_blocks] >= high_cut)]
    receiver_blocks = receiver_blocks[np.argsort(-block_prior[receiver_blocks])]
    receiver_set = np.zeros(valid_count.size, dtype=bool)
    receiver_set[receiver_blocks] = True
    high = receiver_set[cand_bid]
    cand_rows, cand_cols, cand_bid = cand_rows[high], cand_cols[high], cand_bid[high]
    candidate_by_block: dict[int, list[int]] = {}
    for idx in np.lexsort((-prior[cand_rows, cand_cols], cand_bid)):
        candidate_by_block.setdefault(int(cand_bid[idx]), []).append(int(idx))
    add_order_list: list[int] = []
    max_level = max(len(v) for v in candidate_by_block.values())
    # Empty high-prior blocks first, then occupied blocks; within each pass,
    # blocks retain their descending physical-prior order.
    ordered_receivers = [int(b) for b in receiver_blocks if int(b) in candidate_by_block]
    ordered_receivers.sort(key=lambda b: (parent_block_count[b] > 0, -block_prior[b]))
    for level in range(max_level):
        for bid in ordered_receivers:
            vals = candidate_by_block[bid]
            if level < len(vals):
                add_order_list.append(vals[level])
    add_order = np.asarray(add_order_list, dtype=np.int64)

    release_dir = ROOT / "releases"
    release_dir.mkdir(exist_ok=True)
    # Concurrent mainline work already built semantically equivalent 10% and
    # 20% / 1 km arms. Keep only the unique 15% dose after ledger reconciliation.
    predictions = {15: "MODEL:+0.008"}
    rows_out, cards, receipts = [], {}, {}
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

    for pct in (15,):
        moved = int(round(n_parent * pct / 100.0))
        rm_idx = remove_order[:moved]
        add_idx = add_order[:moved]
        variant = parent.copy()
        variant[parent_rows[rm_idx], parent_cols[rm_idx]] = False
        variant[cand_rows[add_idx], cand_cols[add_idx]] = True
        removed = parent & ~variant
        added = variant & ~parent
        if int(variant.sum()) != n_parent or int(removed.sum()) != moved or int(added.sum()) != moved:
            raise ValueError("fixed-count relocation failed")

        _, vc, _, dc = block_statistics(foot, prior, variant)
        cv_after = density_cv(dc, vc)
        arr_nan = np.where(foot, variant, np.nan).astype(np.float32)
        arr_zero = np.where(foot, variant, 0.0).astype(np.float32)
        stem = f"{PARENT_ID}-CONCENTRATION{pct}pct-{DATE}"
        temp = release_dir / f".{stem}.tif"
        write_tif(temp, arr_nan, float("nan"))
        sha = digest(temp)
        identifier = f"{stem}-{sha[:8]}"
        nan_path = release_dir / f"{identifier}.tif"
        zero_path = release_dir / f"{identifier}-zeros.tif"
        temp.replace(nan_path)
        write_tif(zero_path, arr_zero, None)
        nan_report = validate(nan_path, sample_grid, foot, catalogue, distance, n_parent, True)
        zero_report = validate(zero_path, sample_grid, foot, catalogue, distance, n_parent, False)
        if np.count_nonzero(variant ^ parent) != 2 * moved:
            raise ValueError("parent symmetric-diff mismatch")
        for tif in (nan_path, zero_path):
            with zipfile.ZipFile(tif.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(tif, tif.name)

        description = (f"Relocate {pct}% ({moved}) from lowest- to highest-prior 1 km blocks; "
                       f"count fixed; density CV {cv_before['all_full_blocks']:.3f}→"
                       f"{cv_after['all_full_blocks']:.3f}.")
        rows_out.append({
            "id": identifier, "parent": PARENT_ID, "axis": "CONCENTRATION",
            "value": f"15pct-1km-grad", "n_dots": n_parent,
            "pct_changed": f"{pct:.2f}",
            "sha256": nan_report["sha256"], "sha256_zeros": zero_report["sha256"],
            "status": "BUILT", "predicted_change": predictions[pct],
            "predicted_range": "[-0.005,+0.020]",
            "ranking_basis": "low->high 1 km blocks by official TMI-HG/gravity-slope/gravity-HG mean",
            "description": description, "receipt_score": "", "receipt_date": "",
            "recommendation": "HOLD: unique 15% dose; inherited R0 2 px collar conflicts with literal non-PRUNE >=3 px gate.",
        })
        cards[identifier] = {
            "hypothesis": "Undiscovered geothermal-relevant faults are concentrated in kilometre-scale zones where independent magnetic and gravity boundary responses agree.",
            "mechanism": f"Relocated exactly {pct}% of R0 dots from low-prior to high-prior 1 km blocks using official TMI/gravity gradients; total mass stayed 37,654.",
            "non_fault_mimic": "Lithologic contacts, pluton margins, basin-depth gradients, and acquisition-line corrugation can create the same magnetic/gravity boundaries.",
            "predicted_live_change_MODEL": predictions[pct],
            "falsifier": "An absolute live change below 0.01 is no evidence; a decline of at least 0.01 falsifies this concentration level on public chunks.",
            "parent_diff": {"removed": moved, "added": moved, "relocated_pct": pct,
                            "symmetric_diff_pct": round(200 * moved / n_parent, 4)},
            "block_definition": "10x10 pixels = 1 km x 1 km; CV over density in all 100%-footprint blocks",
            "block_density_cv_before": cv_before,
            "block_density_cv_after": cv_after,
            "prior_bands": prior_bands,
            "git_sha_at_build": git_sha,
            "format_report": {"nan": nan_report, "zeros": zero_report},
        }
        note = (f"h33-2-b2; CONC {pct}% in 1km gradient blocks; count 37654; "
                f"pred {predictions[pct]} MODEL")
        if len(note) > 140:
            raise ValueError("form note too long")
        receipts[identifier] = {"file": str(nan_path.relative_to(ROOT)),
                                "fallback": str(zero_path.relative_to(ROOT)),
                                "name": identifier, "note": note,
                                "sha256": nan_report["sha256"],
                                "sha256_zeros": zero_report["sha256"]}
        print(identifier, description)

    update_ledgers(rows_out, cards)
    (ROOT / "ledger/concentration_build_receipt.json").write_text(json.dumps({
        "parent_rebuild_sha256": PARENT_SHA, "parent_dots": n_parent,
        "block_px": BLOCK_PX, "block_m": 1000, "prior_bands": prior_bands,
        "cv_before": cv_before, "variants": receipts, "git_sha_at_build": git_sha,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
