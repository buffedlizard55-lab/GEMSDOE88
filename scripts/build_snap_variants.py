#!/usr/bin/env python3
"""Build and validate controlled AXIS=SNAP variants of parent R0 (h33-h33-2-b2).

Implements Agent Brief v2 §5 (AXIS=SNAP) end-to-end with zero DrivenData/Dropbox contact:
1. Verifies SHA-256 + byte size of all 15 pinned inputs in registry/data_manifest.json.
2. Rebuilds parent R0 (h33-h33-2-b2, 37,654 unit-mass dots) across all 5 lineage steps from
   H19-5 (121,131 px -> D1.5 60,069 -> D2.8 44,090 -> SOLO-D2.8 40,199 -> R0 37,654) and
   matches both pinned SHA-256 hashes bit-for-bit:
      - R0 zeros: c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9
      - R0 NaN:   baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd
3. Constructs strictly label-free edge/scarp response surfaces from the organizer-provided
   19-band stack (data/training_features.tif: Band 3 tmi_hg, Band 12 det_elev Hessian ridge,
   Band 18 iso_grav_anom_hg, Band 19 det_elev_slope; no un-supplied external LiDAR used per
   Brief §5 "provided TMI/gravity gradient bands; lidar-derived rasters only if the human
   supplies them") and verifies all 8 single/composite channels pass the leakage canary
   (symmetric ROC AUC <= 0.90; max = 0.54949).
4. Moves each eligible R0 dot <= 2.0 px (<= 200 m, inside the 5x5 Euclidean disk) in a strict
   1-to-1 bijection (Same count = 37,654) preserving R0's inter-dot spacing (d_nn >= sqrt(8)
   = 2.8284 px > 2.8 px so adjacent dots along a fault trace never bunch up and open 300 m
   kernel coverage gaps) and preserving R0's exact catalogue exclusions (0 on catalogue,
   0 at d_cat <= 2.0 px, 2,171 collar dots at 2 < d_cat <= 3.0 px inherited unchanged, and
   100% of moved dots strictly at d_cat > 3.0 px):
      - ridge2px: <= 2.0 px snap constrained to H19-5 parent ridge ribbons (18.81% moved,
                  mean displacement 0.2299 px overall / 1.2222 px moved; de-jitters score-blind
                  BFS tie-breaking of dot_thin(H19-5, 2.8)).
      - pot2px:   <= 2.0 px snap onto provided TMI + isostatic-gravity horizontal-gradient
                  crests (Bands 3 & 18; 82.46% moved, mean displacement 1.3489 px overall /
                  1.6358 px moved; tests hanging-wall dip-offset pull of pure potential fields).
      - scarp2px: <= 2.0 px snap onto co-registered topographic scarp + TMI/gravity edge
                  (Bands 19, 12, 18, 3; 82.03% moved, mean displacement 1.3089 px overall /
                  1.5956 px moved; anchors dots to 0 m updip range-front scarp emergence).
5. Enforces all MUST gates (format parity with sample_submission.tif, NaN outside + -zeros
   fallback, finite [0, 1] inside, zero catalogue mass, non-duplicate SHA-256, parent-diff
   and displacement stats recorded, re-read verification from disk) and computes all
   REPORT-ONLY diagnostics (Holdout-DTI + 95% CI, leakage canaries, blind off-catalogue
   USGS SGMC control, and 10 km / 12 km block-density CV).
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import gates, grid as grid_mod, holdout as holdout_mod, validate  # noqa: E402
from scripts import build_prune_variants as bpv  # noqa: E402

PARENT_ID = bpv.PARENT_ID
PARENT_SHA_ZEROS = bpv.PARENT_SHA_ZEROS
PARENT_SHA_NAN = bpv.PARENT_SHA_NAN
FIXED_DATE = "20261023"
SEED = 20261023
MIN_DCAT = 3.0


def _offsets(max_disp: int) -> list[tuple[int, int, float]]:
    offs = []
    for dy in range(-max_disp, max_disp + 1):
        for dx in range(-max_disp, max_disp + 1):
            r = float(np.hypot(dy, dx))
            if 0.0 < r <= max_disp:
                offs.append((dy, dx, r))
    offs.sort(key=lambda t: (t[2], t[0], t[1]))
    return offs


def snap(
    mask: np.ndarray,
    edge: np.ndarray,
    foot: np.ndarray,
    catalogue: np.ndarray,
    d_cat: np.ndarray,
    max_disp: int,
    min_dcat: float = MIN_DCAT,
    gain_min: float = 0.0,
) -> dict:
    """Unspaced window-argmax snap helper (retained for unit-test compatibility with PR #21)."""
    H, W = mask.shape
    dest_ok = foot & ~catalogue & (d_cat > min_dcat)
    ys, xs = np.nonzero(mask)
    src_edge = edge[ys, xs]
    offs = _offsets(max_disp)

    proposals: list[tuple[float, int, int, int, int]] = []
    for i, (y, x) in enumerate(zip(ys.tolist(), xs.tolist())):
        best_val = src_edge[i]
        best: tuple[int, int] | None = None
        for dy, dx, _r in offs:
            yy, xx = y + dy, x + dx
            if not (0 <= yy < H and 0 <= xx < W):
                continue
            if not dest_ok[yy, xx] or mask[yy, xx]:
                continue
            v = edge[yy, xx]
            if v > best_val:
                best_val = float(v)
                best = (yy, xx)
        if best is not None and (best_val - float(src_edge[i])) > gain_min:
            proposals.append((best_val - float(src_edge[i]), int(y), int(x), best[0], best[1]))

    proposals.sort(key=lambda t: (-t[0], t[1], t[2]))
    claimed: set[tuple[int, int]] = set()
    new_mask = mask.copy()
    moves: list[tuple[int, int, int, int, float]] = []
    for gain, y, x, yy, xx in proposals:
        if (yy, xx) in claimed:
            continue
        claimed.add((yy, xx))
        new_mask[y, x] = False
        new_mask[yy, xx] = True
        moves.append((y, x, yy, xx, gain))

    assert int(new_mask.sum()) == int(mask.sum()), "SNAP must hold the dot count fixed"
    return {
        "mask": new_mask,
        "n_proposed": len(proposals),
        "n_moved": len(moves),
        "moves": moves,
        "max_disp": max_disp,
        "min_dcat": min_dcat,
    }


def build_snap_edge_fields_and_canaries(
    verified: dict[str, Path],
    foot: np.ndarray,
    catalogue: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Build strictly provided-band edge/scarp fields on foot & run leakage canaries BEFORE masking."""
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)
    pos_mask = folds20[0]["hidden_all"] | folds30[0]["hidden_all"]
    del folds20, folds30, gd
    neg_pool = np.flatnonzero(foot & ~catalogue & ~pos_mask)
    rng = np.random.default_rng(SEED)
    neg_sample = rng.choice(neg_pool, size=min(100_000, len(neg_pool)), replace=False)
    del neg_pool
    pos_idx = np.flatnonzero(pos_mask)
    del pos_mask
    eval_idx = np.concatenate([pos_idx, neg_sample])
    y_true = np.concatenate(
        [np.ones(len(pos_idx), dtype=np.int8), np.zeros(len(neg_sample), dtype=np.int8)]
    )
    canaries: dict[str, float] = {}

    def _audit(name: str, arr: np.ndarray) -> None:
        auc = float(roc_auc_score(y_true, arr.ravel()[eval_idx]))
        sym_auc = float(max(auc, 1.0 - auc))
        canaries[name] = round(sym_auc, 5)
        if sym_auc > 0.90:
            raise RuntimeError(
                f"LEAKAGE CANARY TRIPPED on {name}: symmetric AUC = {sym_auc:.5f} > 0.90"
            )

    def _read_clean_band(ds: rasterio.DatasetReader, idx: int) -> np.ndarray:
        arr = np.where(foot, np.nan_to_num(ds.read(idx), nan=0.0), 0.0).astype(np.float32)
        bad = (~np.isfinite(arr)) | (np.abs(arr) > 1e20)
        if np.any(bad & foot):
            arr[bad] = float(np.median(arr[foot & ~bad]))
        arr[~foot] = 0.0
        return arr

    with rasterio.open(verified["training_features"]) as ds:
        tmi_hg_raw = _read_clean_band(ds, 3)      # Band 3: tmi_hg
        det_elev_raw = _read_clean_band(ds, 12)   # Band 12: det_elev
        grav_hg_raw = _read_clean_band(ds, 18)    # Band 18: iso_grav_anom_hg
        elev_slope_raw = _read_clean_band(ds, 19) # Band 19: det_elev_slope

    tmi_hg = bpv._percentile_rank(tmi_hg_raw, foot)
    tmi_crest = bpv._percentile_rank(bpv._hessian_ridge(tmi_hg_raw, 1.2), foot)
    del tmi_hg_raw

    grav_hg = bpv._percentile_rank(grav_hg_raw, foot)
    grav_crest = bpv._percentile_rank(bpv._hessian_ridge(grav_hg_raw, 1.2), foot)
    del grav_hg_raw

    elev_slope = bpv._percentile_rank(elev_slope_raw, foot)
    del elev_slope_raw

    elev_break = bpv._percentile_rank(bpv._hessian_ridge(det_elev_raw, 1.5), foot)
    del det_elev_raw

    _audit("tmi_hg_b03", tmi_hg)
    _audit("tmi_crest_b03", tmi_crest)
    _audit("grav_hg_b18", grav_hg)
    _audit("grav_crest_b18", grav_crest)
    _audit("det_elev_slope_b19", elev_slope)
    _audit("det_elev_break_b12", elev_break)

    # 1. Subsurface potential-field horizontal-gradient + ridge crest response (Bands 3 & 18)
    edge_pot = (
        0.35 * grav_hg + 0.25 * tmi_hg + 0.20 * grav_crest + 0.20 * tmi_crest
    ).astype(np.float32)
    edge_pot[~foot] = 0.0
    _audit("composite_edge_pot", edge_pot)

    # 2. Co-registered surface scarp + subsurface potential-field edge response (Bands 19, 12, 18, 3)
    edge_scarp_pot = (
        0.42 * elev_slope + 0.23 * elev_break + 0.20 * grav_hg + 0.15 * tmi_hg
    ).astype(np.float32)
    edge_scarp_pot[~foot] = 0.0
    _audit("composite_edge_scarp_pot", edge_scarp_pot)

    return edge_pot, edge_scarp_pot, canaries


def snap_dots_within_window(
    r0_mask: np.ndarray,
    score_field: np.ndarray,
    foot: np.ndarray,
    catalogue: np.ndarray,
    d_cat: np.ndarray,
    h19_5: np.ndarray,
    max_r: float = 2.0,
    min_sep: float = 2.8,
    stay_on_h19: bool = False,
) -> tuple[np.ndarray, dict]:
    """Move each eligible R0 dot <= max_r px to the strongest edge/scarp response in its window.

    Enforces:
    - Bijection (count strictly fixed at 37,654).
    - Euclidean displacement ||x' - x||_2 <= max_r (<= 2.0 px = 200 m).
    - Minimum inter-dot spacing ||x'_i - x'_j||_2 >= min_sep (2.8 px -> sqrt(8) = 2.8284 px on Z^2),
      preventing adjacent dots along a fault strand from bunching onto the same pixel and opening
      >300 m kernel gaps.
    - Same exclusions as R0: zero mass on catalogue, zero mass at d_cat <= 2.0 px, R0's 2,171
      collar dots (2.0 < d_cat <= 3.0 px) held fixed so SNAP never confounds PRUNE, and 100% of
      moved dots strictly at d_cat > 3.0 px.
    """
    r0_b = np.asarray(r0_mask, dtype=bool)
    H, W = r0_b.shape
    ry, rx = np.nonzero(r0_b)

    offs = [
        (dy, dx, float(np.hypot(dy, dx)))
        for dy in range(-int(np.ceil(max_r)), int(np.ceil(max_r)) + 1)
        for dx in range(-int(np.ceil(max_r)), int(np.ceil(max_r)) + 1)
        if dy * dy + dx * dx <= max_r * max_r + 1e-9
    ]
    # Tie-break equal score by smaller Euclidean displacement, then (dy, dx)
    offs.sort(key=lambda t: (t[2], t[0], t[1]))

    allowed = foot & ~catalogue & (d_cat > 3.0)
    if stay_on_h19:
        allowed = allowed & h19_5

    occ = r0_b.copy()
    r_sep = int(np.ceil(min_sep))
    sep_offs = [
        (dy, dx)
        for dy in range(-r_sep, r_sep + 1)
        for dx in range(-r_sep, r_sep + 1)
        if 0 < dy * dy + dx * dx < min_sep * min_sep - 1e-9
    ]

    best_gain = np.zeros(len(ry), dtype=np.float32)
    is_eligible = d_cat[ry, rx] > 3.0
    for dy, dx, _dist in offs:
        if dy == 0 and dx == 0:
            continue
        ny = np.clip(ry + dy, 0, H - 1)
        nx = np.clip(rx + dx, 0, W - 1)
        ok = (
            (ry + dy >= 0)
            & (ry + dy < H)
            & (rx + dx >= 0)
            & (rx + dx < W)
            & allowed[ny, nx]
            & is_eligible
        )
        gain = np.where(ok, score_field[ny, nx] - score_field[ry, rx], -1.0)
        best_gain = np.maximum(best_gain, gain)

    # Deterministic total order: largest local edge/scarp gain first, then (row, col)
    order = np.lexsort((rx, ry, -best_gain))
    disps = np.zeros(len(ry), dtype=np.float64)
    dy_taken = np.zeros(len(ry), dtype=np.int32)
    dx_taken = np.zeros(len(ry), dtype=np.int32)
    score_before = float(score_field[r0_b].mean())

    for idx in order:
        y0, x0 = int(ry[idx]), int(rx[idx])
        if d_cat[y0, x0] <= 3.0:
            continue
        occ[y0, x0] = False
        best_s = float(score_field[y0, x0])
        by, bx, bd = y0, x0, 0.0
        for dy, dx, dist in offs:
            if dy == 0 and dx == 0:
                continue
            ny, nx = y0 + dy, x0 + dx
            if not (0 <= ny < H and 0 <= nx < W):
                continue
            if not allowed[ny, nx] or occ[ny, nx]:
                continue
            too_close = False
            for sdy, sdx in sep_offs:
                sy, sx = ny + sdy, nx + sdx
                if 0 <= sy < H and 0 <= sx < W and occ[sy, sx]:
                    too_close = True
                    break
            if too_close:
                continue
            s = float(score_field[ny, nx])
            if s > best_s + 1e-12:
                best_s = s
                by, bx, bd = ny, nx, dist
        occ[by, bx] = True
        disps[idx] = bd
        dy_taken[idx] = by - y0
        dx_taken[idx] = bx - x0

    assert int(occ.sum()) == int(r0_b.sum())
    oy, ox = np.nonzero(occ)
    tree = cKDTree(np.column_stack([oy, ox]))
    d_nn, _ = tree.query(np.column_stack([oy, ox]), k=2)
    min_nn = float(d_nn[:, 1].min())
    mean_nn = float(d_nn[:, 1].mean())

    moved_mask = disps > 0.0
    d2 = dy_taken * dy_taken + dx_taken * dx_taken
    disp_stats = {
        "max_window_radius_px": float(max_r),
        "min_interdot_sep_enforced_px": float(min_sep),
        "min_interdot_nn_dist_px": round(min_nn, 4),
        "mean_interdot_nn_dist_px": round(mean_nn, 4),
        "stay_on_h19_5_ridge": bool(stay_on_h19),
        "n_dots_displaced": int(moved_mask.sum()),
        "n_dots_stationary": int((~moved_mask).sum()),
        "mean_displacement_all_px": round(float(disps.mean()), 4),
        "mean_displacement_all_m": round(float(disps.mean() * 100.0), 2),
        "mean_displacement_moved_px": round(
            float(disps[moved_mask].mean()) if np.any(moved_mask) else 0.0, 4
        ),
        "mean_displacement_moved_m": round(
            float(disps[moved_mask].mean() * 100.0) if np.any(moved_mask) else 0.0, 2
        ),
        "max_displacement_px": round(float(disps.max()), 4),
        "displacement_counts_by_d2": {
            "d_0px_d2_0": int((d2 == 0).sum()),
            "d_1px_d2_1": int((d2 == 1).sum()),
            "d_sqrt2px_d2_2": int((d2 == 2).sum()),
            "d_2px_d2_4": int((d2 == 4).sum()),
        },
        "mean_edge_response_before": round(score_before, 5),
        "mean_edge_response_after": round(float(score_field[occ].mean()), 5),
        "mean_edge_response_gain": round(float(score_field[occ].mean()) - score_before, 5),
    }
    return occ, disp_stats


def write_and_verify_snap_variant(
    mask: np.ndarray,
    disp_stats: dict,
    foot: np.ndarray,
    catalogue: np.ndarray,
    sample_path: Path,
    releases_dir: Path,
    parent_mask: np.ndarray,
    value: str,
    note_template: str,
    existing_shas: set[str],
) -> dict:
    """Write <id>.tif (NaN outside) + <id>-zeros.tif + .zip + .json and re-read verify all gates."""
    releases_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(sample_path) as tpl:
        base_prof = tpl.profile.copy()
        ref_tuple = (tpl.shape, tpl.crs, tpl.transform)

    prof_nan = base_prof.copy()
    prof_nan.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        compress="deflate",
        predictor=3,
        zlevel=9,
        tiled=True,
        blockxsize=256,
        blockysize=256,
        nodata=np.nan,
    )
    prof_zeros = prof_nan.copy()
    prof_zeros.update(nodata=None)

    arr_nan = np.where(foot, mask.astype(np.float32), np.nan).astype(np.float32)
    arr_zeros = np.where(foot, mask.astype(np.float32), 0.0).astype(np.float32)

    prefix = f"{PARENT_ID}-SNAP{value}-{FIXED_DATE}"
    tmp_nan = releases_dir / f".tmp-{prefix}.tif"
    tmp_zeros = releases_dir / f".tmp-{prefix}-zeros.tif"
    with rasterio.open(tmp_nan, "w", **prof_nan) as dst:
        dst.write(arr_nan, 1)
    with rasterio.open(tmp_zeros, "w", **prof_zeros) as dst:
        dst.write(arr_zeros, 1)

    sha_nan = bpv.sha256_file(tmp_nan)
    sha_zeros = bpv.sha256_file(tmp_zeros)
    sha8 = sha_nan[:8]

    if sha_nan in existing_shas or sha_zeros in existing_shas:
        tmp_nan.unlink(missing_ok=True)
        tmp_zeros.unlink(missing_ok=True)
        raise RuntimeError(f"Duplicate SHA-256 already present in ledger: {sha_nan}")

    vid = f"{prefix}-{sha8}"
    final_nan = releases_dir / f"{vid}.tif"
    final_zeros = releases_dir / f"{vid}-zeros.tif"
    tmp_nan.replace(final_nan)
    tmp_zeros.replace(final_zeros)

    zip_nan = releases_dir / f"{vid}.zip"
    zip_zeros = releases_dir / f"{vid}-zeros.zip"
    for tif_p, zip_p in ((final_nan, zip_nan), (final_zeros, zip_zeros)):
        with zipfile.ZipFile(zip_p, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(tif_p, arcname=tif_p.name)
        os.chmod(tif_p, 0o644)
        os.chmod(zip_p, 0o644)

    # MUST-PASS RE-READ VERIFICATION FROM DISK
    with rasterio.open(final_nan) as ds:
        back_nan = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform) == ref_tuple
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert np.isfinite(back_nan[foot]).all(), "NaN/Inf inside footprint in .tif"
        assert np.isnan(back_nan[~foot]).all(), "Non-NaN outside footprint in .tif"
        assert float(back_nan[foot].min()) >= 0.0 and float(back_nan[foot].max()) <= 1.0
        assert int((back_nan[catalogue] > 0.0).sum()) == 0, "Non-zero mass on catalogue"
        assert np.array_equal(back_nan[foot] > 0.5, mask[foot])

    with rasterio.open(final_zeros) as ds:
        back_zeros = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform) == ref_tuple
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert np.isfinite(back_zeros).all()
        assert np.all(back_zeros[~foot] == 0.0)
        assert int((back_zeros[catalogue] > 0.0).sum()) == 0
        assert np.array_equal(back_zeros[foot] > 0.5, mask[foot])

    rep_zeros = gates.format_report(final_zeros, sample_path, footprint=foot)
    val_zeros = validate.validate(final_zeros, foot, catalogue)
    assert rep_zeros["ok"] and val_zeros["all_checks_passed"]

    d_cat = distance_transform_edt(~catalogue)
    dvals = d_cat[mask]
    added_mask = mask & ~parent_mask
    removed_mask = parent_mask & ~mask
    n_parent = int(parent_mask.sum())
    n_dots = int(mask.sum())
    n_added = int(added_mask.sum())
    n_removed = int(removed_mask.sum())
    pct_moved = 100.0 * n_removed / n_parent
    pct_sym_diff = 100.0 * (n_added + n_removed) / n_parent
    assert n_added == n_removed > 0
    assert float(d_cat[added_mask].min()) > 3.0, "Added SNAP dots must strictly satisfy d_cat > 3.0 px"
    assert float(d_cat[removed_mask].min()) > 3.0, "Removed SNAP dots must strictly satisfy d_cat > 3.0 px"

    note = note_template.format(sha8=sha8)
    assert len(note) <= 140, f"Form note > 140 chars ({len(note)}): {note}"

    receipt = {
        "id": vid,
        "parent": PARENT_ID,
        "parent_sha256_zeros": PARENT_SHA_ZEROS,
        "parent_sha256_nan": PARENT_SHA_NAN,
        "axis": "SNAP",
        "value": value,
        "seed": SEED,
        "git_sha": bpv.git_sha(),
        "file_nan": f"releases/{final_nan.name}",
        "sha256": sha_nan,
        "bytes_nan": final_nan.stat().st_size,
        "zip_nan": f"releases/{zip_nan.name}",
        "zip_nan_sha256": bpv.sha256_file(zip_nan),
        "file_zeros": f"releases/{final_zeros.name}",
        "sha256_zeros": sha_zeros,
        "bytes_zeros": final_zeros.stat().st_size,
        "zip_zeros": f"releases/{zip_zeros.name}",
        "zip_zeros_sha256": bpv.sha256_file(zip_zeros),
        "form_note": note,
        "form_note_chars": len(note),
        "n_dots": n_dots,
        "displacement": disp_stats,
        "parent_diff": {
            "n_parent": n_parent,
            "n_common": int((mask & parent_mask).sum()),
            "n_added": n_added,
            "n_removed": n_removed,
            "pct_changed_moved": round(pct_moved, 2),
            "pct_changed_sym_diff": round(pct_sym_diff, 2),
            "min_dist_catalogue_px": round(float(dvals.min()), 4),
            "min_dist_added_catalogue_px": round(float(d_cat[added_mask].min()), 4),
            "dots_le_1px": int((dvals <= 1.0).sum()),
            "dots_le_2px": int((dvals <= 2.0).sum()),
            "dots_le_3px": int((dvals <= 3.0).sum()),
            "dots_le_4px": int((dvals <= 4.0).sum()),
        },
        "gates": {
            "crs_epsg_32611": True,
            "shape_3730x3292": True,
            "transform_match": True,
            "dtype_float32": True,
            "band_count_1": True,
            "values_in_0_1": True,
            "no_nan_inside_footprint": True,
            "nan_outside_footprint": True,
            "zeros_fallback_valid": True,
            "zero_catalogue_mass": True,
            "none_within_2px_catalogue": True,
            "all_moved_dots_gt_3px_catalogue": True,
            "reread_from_disk_verified": True,
        },
    }
    receipt_path = releases_dir / f"{vid}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    os.chmod(receipt_path, 0o644)
    return receipt


def main() -> int:
    t0 = time.time()
    print("[1/5] Verifying SHA-256 manifest pins...")
    verified = bpv.verify_manifest()
    print(f"      Verified {len(verified)}/{len(verified)} pinned inputs.")

    print("[2/5] Rebuilding parent R0 (h33-h33-2-b2) across all 5 lineage steps...")
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    print(
        f"      EXACT R0 REBUILD OK: {int(r0.sum()):,} dots | "
        f"zeros={lin['rebuilt_zeros_sha256'][:12]}... | nan={lin['rebuilt_nan_sha256'][:12]}..."
    )

    print("[3/5] Building provided-band edge/scarp fields & running leakage canaries...")
    edge_pot, edge_scarp_pot, canaries = build_snap_edge_fields_and_canaries(
        verified, foot, catalogue
    )
    print(
        f"      Canaries PASS ({len(canaries)}/{len(canaries)} channels <= 0.90; "
        f"max symmetric AUC = {max(canaries.values()):.5f})"
    )

    print("[4/5] Building 3 controlled AXIS=SNAP variants (<= 2.0 px window, N = 37,654)...")
    m_ridge, d_ridge = snap_dots_within_window(
        r0_mask=r0,
        score_field=edge_scarp_pot,
        foot=foot,
        catalogue=catalogue,
        d_cat=d_cat,
        h19_5=h19_5,
        max_r=2.0,
        min_sep=2.8,
        stay_on_h19=True,
    )
    m_pot, d_pot = snap_dots_within_window(
        r0_mask=r0,
        score_field=edge_pot,
        foot=foot,
        catalogue=catalogue,
        d_cat=d_cat,
        h19_5=h19_5,
        max_r=2.0,
        min_sep=2.8,
        stay_on_h19=False,
    )
    m_scarp, d_scarp = snap_dots_within_window(
        r0_mask=r0,
        score_field=edge_scarp_pot,
        foot=foot,
        catalogue=catalogue,
        d_cat=d_cat,
        h19_5=h19_5,
        max_r=2.0,
        min_sep=2.8,
        stay_on_h19=False,
    )

    ledger_path = ROOT / "ledger" / "submissions.csv"
    existing_rows: list[dict[str, str]] = []
    existing_shas: set[str] = {PARENT_SHA_ZEROS, PARENT_SHA_NAN}
    our_values = {"ridge2px", "pot2px", "scarp2px"}
    if ledger_path.is_file():
        with ledger_path.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("axis") == "SNAP" and row.get("value") in our_values:
                    continue  # idempotent rerun replaces only our spacing-locked SNAP rows
                existing_rows.append(row)
                if row.get("sha256"):
                    existing_shas.add(row["sha256"])
                if row.get("sha256_zeros"):
                    existing_shas.add(row["sha256_zeros"])

    releases_dir = ROOT / "releases"
    for v_name in our_values:
        for old_p in releases_dir.glob(f"{PARENT_ID}-SNAP{v_name}-*"):
            old_p.unlink()

    specs = [
        (
            "ridge2px",
            m_ridge,
            d_ridge,
            "MODEL:+0.003",
            "[-0.004,+0.011]",
            "provided Bands 19/12/18/3 scarp+TMI/gravity edge inside <=2.0 px window on H19-5 ridge support (d_nn>=2.8 px)",
            "h33-2-b2; SNAP <=2px on H19-5 ridge to scarp+TMI/grav peak (18.81% chg, mean disp 0.23px); pred +0.003 MODEL",
            "SNAP <=2.0 px (200 m) inside H19-5 parent ridge ribbons onto provided scarp+TMI/gravity crest at fixed 37654 count; mean displacement 0.2299 px (1.2222 px moved).",
            "HOLD/RESERVE: conservative intra-ribbon BFS de-jittering (+0.003 MODEL, SGMC 0.09644); inherits R0's 2171 2-3px collar dots unchanged.",
            {
                "axis": "SNAP",
                "value": "ridge2px",
                "max_window_px": 2.0,
                "mean_displacement_all_px": d_ridge["mean_displacement_all_px"],
                "mean_displacement_moved_px": d_ridge["mean_displacement_moved_px"],
                "pct_changed": 18.81,
                "hypothesis": "Parent R0's Poisson-disk thinning (dot_thin(H19-5, 2.8)) traversed connected components in score-blind row-major BFS order, systematically anchoring dots on the northern/western outer pixel of 2-3 px wide H19-5 ribbons rather than the physical ridge crest. Shifting each d_cat > 3 px dot <= 2.0 px within its H19-5 ribbon onto the local topographic-scarp and TMI/gravity horizontal-gradient maximum increases kernel coverage T without leaving the parent detector support.",
                "mechanism": "At fixed count S = 37,654 (Delta S = 0), moving a dot by <= 200 m toward a fault axis increases both numerator coverage T and self-credit M, yielding Delta DTI = [(1 - 0.2*DTI)*Delta T + 0.2*DTI*Delta M] / [D + 0.2*(Delta T - Delta M)] > 0 whenever Delta T > 0 and Delta M >= 0. Enforcing d_nn >= sqrt(8) = 2.828 px prevents adjacent dots along strike from bunching onto a single peak and opening >300 m kernel gaps.",
                "non_fault_mimic": "Erosional facet spurs and asymmetrical footwall crest rounding on range fronts can shift the 100 m detrended-elevation slope peak 100-200 m upslope of the basal fault trace inside a 2-3 px H19-5 ribbon.",
                "predicted_sign_size": "MODEL +0.003 live delta vs R0 (scenario range [-0.004, +0.011]; blind off-catalogue SGMC rises +0.00038 from 0.09606 to 0.09644; <0.01 live delta treated as within public-chunk noise unless directional with scarp2px).",
                "falsifier": "Live score drop <= -0.010 vs R0 or underperformance relative to un-snapped R0 when scarp2px also drops <= -0.010 falsifies BFS ribbon-edge jitter as a limiting factor.",
            },
        ),
        (
            "pot2px",
            m_pot,
            d_pot,
            "MODEL:-0.004",
            "[-0.014,+0.006]",
            "provided Bands 3 & 18 TMI + isostatic-gravity horizontal-gradient & Hessian crests inside <=2.0 px window (d_nn>=2.8 px)",
            "h33-2-b2; SNAP <=2px to provided TMI+gravity HG crests (82.46% chg, mean disp 1.35px); pred -0.004 MODEL",
            "SNAP <=2.0 px (200 m) to provided TMI + isostatic-gravity horizontal-gradient crests (Bands 3 & 18) at fixed 37654 count; mean displacement 1.3489 px (1.6358 px moved).",
            "HOLD/DIAGNOSTIC: tests pure potential-field snap (-0.004 MODEL, SGMC 0.09518); hanging-wall dip shift pulls dots off surface traces.",
            {
                "axis": "SNAP",
                "value": "pot2px",
                "max_window_px": 2.0,
                "mean_displacement_all_px": d_pot["mean_displacement_all_px"],
                "mean_displacement_moved_px": d_pot["mean_displacement_moved_px"],
                "pct_changed": 82.46,
                "hypothesis": "Snapping R0 dots <= 2.0 px (200 m) strictly toward subsurface TMI and isostatic-gravity horizontal-gradient maxima (Bands 3 & 18) degrades surface fault alignment because Great Basin normal faults dip ~60 degrees: across 0.5-1.5 km basin fill, the maximum horizontal density and susceptibility gradient sits 200-600 m down-dip in the hanging wall rather than on the surface trace.",
                "mechanism": "Under GeoDAWN Area 2 survey geometry (400 m flight-line spacing, 150-200 m drape height; https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7) and 60-degree Andersonian normal-fault dip (Faulds & Hinz 2015), potential-field horizontal gradients peak basinward of the surface fault emergence. Moving dots 1.35 px toward raw TMI/gravity gradient peaks shifts them 100-200 m into the hanging wall, reducing kernel overlap k(d) = max(0, 1 - d/3) on surface fault traces (blind SGMC drops from 0.09606 to 0.09518).",
                "non_fault_mimic": "Subsurface volcanic dike swarms, pluton margins, and GeoDAWN 400 m flight-line leveling shoulders produce sharp TMI/gravity horizontal gradients displaced 100-200 m from brittle surface fault traces.",
                "predicted_sign_size": "MODEL -0.004 live delta vs R0 (scenario range [-0.014, +0.006]; blind off-catalogue SGMC delta -0.00088 vs R0).",
                "falsifier": "Live score gain >= +0.010 over R0 and over scarp2px falsifies hanging-wall dip-offset degradation and proves hidden test faults are predominantly blind intrabasin basement structures mapped directly from aeromagnetic/gravity gradients.",
            },
        ),
        (
            "scarp2px",
            m_scarp,
            d_scarp,
            "MODEL:+0.006",
            "[-0.005,+0.016]",
            "provided Bands 19/12 det_elev_slope + breakline (65%) + Bands 18/3 gravity/TMI HG (35%) inside <=2.0 px window (d_nn>=2.8 px)",
            "h33-2-b2; SNAP <=2px to provided scarp+TMI/grav co-edge (82.03% chg, mean disp 1.31px); pred +0.006 MODEL",
            "SNAP <=2.0 px (200 m) to co-registered topographic scarp + TMI/gravity edge (Bands 19, 12, 18, 3) at fixed 37654 count; mean displacement 1.3089 px (1.5956 px moved).",
            "PRIMARY SNAP CANDIDATE (+0.006 MODEL, blind SGMC 0.09681, 12km CV 0.5607): all 30889 moved dots >3 px; inherits R0's 2171 2-3px collar dots (pair with PRUNEp3px in Wk 2/3).",
            {
                "axis": "SNAP",
                "value": "scarp2px",
                "max_window_px": 2.0,
                "mean_displacement_all_px": d_scarp["mean_displacement_all_px"],
                "mean_displacement_moved_px": d_scarp["mean_displacement_moved_px"],
                "pct_changed": 82.03,
                "hypothesis": "Snapping R0 dots <= 2.0 px (200 m, half a GeoDAWN 400 m flight-line spacing) onto the co-registered topographic fault-scarp breakline (Bands 19 det_elev_slope + 12 det_elev Hessian ridge, 65% weight) corroborated by TMI/gravity horizontal gradients (Bands 18 & 3, 35% weight) while preserving d_nn >= 2.8 px inter-dot spacing pulls aeromagnetic-drifted H19-5 dots back onto the physical 0 m updip range-front fault trace.",
                "mechanism": "H19-5 blended upward-continued GeoDAWN potential fields (150-200 m terrain clearance, 400 m line spacing) with regional topography, leaving dot centers displaced by ~1-2 px (100-200 m) from the discrete surface scarp breakline. Re-centering each d_cat > 3 px dot by a mean of 1.3089 px (1.5956 px among moved dots) onto the scarp-anchored co-edge increases kernel credit k(d) along off-catalogue range-front traces at fixed S = 37,654 (blind SGMC rises +0.00075 from 0.09606 to 0.09681; +76.67 TP).",
                "non_fault_mimic": "Wave-cut Pleistocene Lake Lahontan / Bonneville paleoshorelines (1,212-1,555 m), welded-tuff mesa rims, and incised alluvial-fan terrace risers form sharp 100 m topographic breaklines within 200 m of piedmont fault corridors without brittle basement throw.",
                "predicted_sign_size": "MODEL +0.006 live delta vs R0 (scenario range [-0.005, +0.016]; blind off-catalogue SGMC = 0.096806 PROXY, highest of SNAP sweep; 12 km block-density CV = 0.5607 inside 0.51-0.59).",
                "falsifier": "Live score drop <= -0.010 vs R0 falsifies topographic scarp re-centering at 100 m grid resolution and shows H19-5's smoothed multi-physics ridge centroid better matches expert fault compilations than local 200 m scarp breaklines.",
            },
        ),
    ]

    built_receipts = []
    cards = (
        json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
        if (ROOT / "ledger" / "mechanism_cards.json").is_file()
        else {}
    )
    cards = {
        k: v
        for k, v in cards.items()
        if not any(f"-SNAP{val}-" in k for val in our_values)
    }

    new_ledger_rows = []
    arms_for_eval = {PARENT_ID: r0}

    for (
        val,
        mask,
        disp_stats,
        pred_delta,
        pred_range,
        rank_basis,
        note_tmpl,
        desc,
        recomm,
        card,
    ) in specs:
        rec = write_and_verify_snap_variant(
            mask=mask,
            disp_stats=disp_stats,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=releases_dir,
            parent_mask=r0,
            value=val,
            note_template=note_tmpl,
            existing_shas=existing_shas,
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])
        built_receipts.append(rec)
        cards[rec["id"]] = card
        arms_for_eval[rec["id"]] = mask
        new_ledger_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": "SNAP",
                "value": val,
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": pred_delta,
                "predicted_range": pred_range,
                "ranking_basis": rank_basis,
                "receipt_score": "",
                "receipt_date": "",
                "description": desc,
                "recommendation": recomm,
            }
        )

    print("[5/5] Running REPORT-ONLY diagnostics (Holdout-DTI + 95% CI, SGMC control, Block CV)...")
    eval_report = bpv.evaluate_report_only_instruments(
        arms=arms_for_eval,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )

    for rec in built_receipts:
        rec["report_only_diagnostics"] = eval_report[rec["id"]]
        rec["r0_reference_diagnostics"] = eval_report[PARENT_ID]
        rec["leakage_canaries"] = {
            "passed": True,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        }
        (releases_dir / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")

    fieldnames = [
        "id",
        "parent",
        "axis",
        "value",
        "n_dots",
        "pct_changed",
        "sha256",
        "sha256_zeros",
        "status",
        "predicted_change",
        "predicted_range",
        "ranking_basis",
        "receipt_score",
        "receipt_date",
        "description",
        "recommendation",
    ]
    with ledger_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in [*existing_rows, *new_ledger_rows]:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    (ROOT / "ledger" / "mechanism_cards.json").write_text(json.dumps(cards, indent=2) + "\n")

    summary_out = {
        "session_date": "2026-10-23",
        "axis": "SNAP",
        "parent_r0": {
            "id": PARENT_ID,
            "n_dots": int(r0.sum()),
            "rebuilt_zeros_sha256": lin["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lin["rebuilt_nan_sha256"],
            "diagnostics": eval_report[PARENT_ID],
        },
        "provided_bands_only": True,
        "external_lidar_used": False,
        "leakage_canaries": {
            "passed": True,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        },
        "variants": built_receipts,
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    (ROOT / "evidence" / "snap_axis_report.json").write_text(
        json.dumps(summary_out, indent=2) + "\n"
    )

    print("\n=== SUMMARY OF BUILT AXIS=SNAP VARIANTS ===")
    for rec in built_receipts:
        diag = rec["report_only_diagnostics"]
        hp = diag["holdout_proxy"]
        sg = diag["sgmc_control"]
        cv = diag["block_density_cv"]
        pdif = rec["parent_diff"]
        dsp = rec["displacement"]
        print(
            f"  {rec['id']} | dots={rec['n_dots']:,} | moved={pdif['pct_changed_moved']:.2f}% "
            f"| mean_disp={dsp['mean_displacement_all_px']:.4f}px (moved={dsp['mean_displacement_moved_px']:.4f}px, max={dsp['max_displacement_px']:.2f}px) "
            f"| min_nn={dsp['min_interdot_nn_dist_px']:.4f}px | HOLDOUT-DTI={hp['dti']:.6f} {hp['ci95']} "
            f"| SGMC={sg['dti']:.6f} | CV12km={cv['cv_12km_120px_interior']:.4f}"
        )
    print(f"Completed in {summary_out['elapsed_seconds']}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
