#!/usr/bin/env python3
"""Build and validate controlled AXIS=PRUNE deconfounding variants of parent R0 (h33-h33-2-b2).

Session choice (Agent Brief v2 §5: "Do not prompt me over choosing an Axis for the session,
pick your own session"): **AXIS = PRUNE**, parent **R0 = h33-h33-2-b2**.

Why AXIS=PRUNE and why these three arms
---------------------------------------
Across the 56-row ledger, MASS (IR-88-52/53), CONCENTRATION (IR-88-52), and SNAP (IR-88-47/51)
are closed as slot-spending axes, RELIEF has 9 negative HOLD arms, SPACING is sub-threshold
(+0.00074 max) and marked lowest priority, and TRACKB is Phase 2 only. Every active candidate in
SLOT_PLAN.md sits on AXIS=PRUNE (parent R0), led on the blind off-catalogue control by
``PRUNEp3space35`` (``49fff49b``, SGMC 0.101042 = +0.0050 vs R0). Yet ``PRUNEp3space35`` carries
three unresolved confounders/blockers documented in IR-88-45, IR-88-47, and SLOT_PLAN.md:

1. **Exact < 3.0 px kernel-zero boundary (IR-88-47)**: Under the official R = 300 m (3.0 px)
   triangular kernel ``k(d) = max(0, 1 - d/3.0)``, R0's 560 dots at exact ``d_cat == 3.0000 px``
   (``d^2 = 9``) already have ``k(3.0) == 0.0`` and already satisfy Brief §4.4's literal ``>= 3 px``
   rule (``under_3px == 0`` in ``validate_variant.py``). Every prior 3 px PRUNE arm used ``<= 3.0``
   (2,171 dots) instead of ``< 3.0`` (1,611 dots), deleting 560 compliant 300 m rim dots.
2. **Ranking falsifier on w (IR-88-45 & IR-88-38)**: ``p3space35`` ranked refills by the four-line
   field ``w``, later measured at blind SGMC AUC 0.4724 (< 0.50) because ``w`` upweights
   hydrothermal/high-gradient hubs around already-catalogued faults. IR-88-45 queued a score-blind
   geometry ranking control at identical collar, pool, count, and >= 3.5 px spacing lock.
3. **Leaderboard-tuned sibling support provenance (IR-88-45)**: ``p3space35`` widened H19-5 with
   ``H19-4`` and ``H16-1`` (+35,954 px -> 157,085 px), sibling artifacts whose thresholds were
   chosen on historical leaderboard runs.

Using byte-reconstructed ``p3space35`` (``49fff49b``) as the single shared control pivot (rebuilt
and verified on disk without adding a duplicate ledger row, together with ``p4space35``
``07bd8182`` to clear SLOT_PLAN.md's local-absence blocker), each new arm changes ONLY ONE factor
relative to ``p3space35`` while remaining a pure single-axis ``PRUNE`` child of ``R0`` at fixed
count ``N = 37,654``:

* ``lt3space35``    -- ``d_cat < 3.0 px`` (1,611 removed = 4.27843%, keeping all 560 ``d_cat == 3``
                       R0 dots) + 1,611 ``>= 3.5 px`` exact-marginal ``w`` refills on
                       ``H19-5 | H19-4 | H16-1``.
* ``p3space35fp``   -- ``d_cat <= 3.0 px`` (2,171 removed = 5.76566%) + 2,171 ``>= 3.5 px``
                       score-blind greedy farthest-point refills on ``H19-5 | H19-4 | H16-1``
                       (zero ``w`` field, zero physical bands, zero RNG).
* ``p3space35prov`` -- ``d_cat <= 3.0 px`` (2,171 removed = 5.76566%) + 2,171 ``>= 3.5 px``
                       refills on area-matched 157,085-px ``H19-5 | R_prov`` built strictly from
                       organizer-provided ``training_features.tif`` Bands 19/3/18/15 structural
                       breakline/gradient Hessian crests (zero ``H19-4``/``H16-1``, zero external
                       LiDAR, zero GDR wells).

All predictions were frozen in ``registry/preregistration_prune_deconfound.json`` before any proxy
or SGMC evaluation ran and are preserved verbatim. Zero contact with drivendata.org or dropbox.com.
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
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gems57 import grid as grid_mod, holdout as holdout_mod  # noqa: E402
import build_prune_spaced_variants as bps  # noqa: E402
import build_prune_variants as bpv  # noqa: E402
import validate_variant as vv  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
AXIS = "PRUNE"
DATE = "20261024"
SEED = 20261024
N_DOTS = 37_654
SPACING_PX = 3.5
NO_EVIDENCE_BAND = 0.01

OUR_VALUES: tuple[str, ...] = ("lt3space35", "p3space35fp", "p3space35prov")

P3SPACE35_ID = "h33-h33-2-b2-PRUNEp3space35-20261023-49fff49b"
P3SPACE35_SHA_NAN = "49fff49b03c47d7ac3822df185f1efd55b0b30855133360689754ce85167a61a"
P3SPACE35_SHA_ZEROS = "e0b9d59b765a198aa5327bb99bddf09fec52e2806410a403b63ccce2d204824e"

P4SPACE35_ID = "h33-h33-2-b2-PRUNEp4space35-20261023-07bd8182"
P4SPACE35_SHA_NAN = "07bd8182ec4d542aa127601febb2eb37b1458885bce1941593bf846b85f4bb2a"
P4SPACE35_SHA_ZEROS = "fb7ee110c9ac96a32e53f7d9558bade00d6244f4b5622e35eab8326464646e3766"
# Read exact expected hashes from ledger at runtime as authoritative pin.

MANIFEST = ROOT / "registry" / "data_manifest.json"
PREREG_PATH = ROOT / "registry" / "preregistration_prune_deconfound.json"
VALIDATION_PATH = ROOT / "registry" / "prune_deconfound_validation.json"
RECON_VALIDATION_PATH = ROOT / "registry" / "prune_spaced_revalidation.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS_PATH = ROOT / "ledger" / "mechanism_cards.json"
RELEASES = ROOT / "releases"
REPORT_PATH = ROOT / "evidence" / "prune_deconfound_report.json"

REFERENCES = [
    {
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "claim": "Official DTI metric uses alpha=0.2, beta=0.8, and triangular kernel R=300 m (3.0 px), where k(3.0)=0.0 (supplied by brief; not fetched).",
    },
    {
        "url": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
        "claim": "Known USGS/INGENIOUS pixels are masked pixel-exactly; adjacent pixels are scored normally against new-fault truth, which can lie within 300 m of known traces (supplied by brief; not fetched).",
    },
    {
        "url": "https://community.drivendata.org/t/where-do-you-draw-the-line/11536",
        "claim": "New fault includes newly mapped geometry (splays, relays, step-overs) of existing fault systems (supplied by brief; not fetched).",
    },
    {
        "url": "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7",
        "claim": "GeoDAWN Area 2 400 m flight-line spacing sets lateral potential-field uncertainty near one kernel radius (supplied by brief; not fetched).",
    },
    {
        "url": "https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d",
        "claim": "USGS SGMC mapped bedrock/concealed faults used strictly as a report-only off-catalogue diagnostic control, never for construction or gating.",
    },
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Pure, synthetic-grid-testable algorithmic primitives
# ---------------------------------------------------------------------------


def directional_crest_1d(score: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """1D directional non-maximum suppression crest mask across 4 axial orientations."""
    s = np.where(valid, np.asarray(score, dtype=np.float32), -1.0)
    p = np.pad(s, 1, mode="constant", constant_values=-1.0)
    c = p[1:-1, 1:-1]
    crest = (
        ((c >= p[:-2, 1:-1]) & (c >= p[2:, 1:-1]))
        | ((c >= p[1:-1, :-2]) & (c >= p[1:-1, 2:]))
        | ((c >= p[:-2, :-2]) & (c >= p[2:, 2:]))
        | ((c >= p[:-2, 2:]) & (c >= p[2:, :-2]))
    )
    return crest & valid & (s > 0.0)


def spaced_farthest_point_add(
    base_mask: np.ndarray,
    cand_mask: np.ndarray,
    n_add: int,
    spacing_px: float = SPACING_PX,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Score-blind greedy farthest-point completion under a hard >= spacing_px lock.

    Uses ZERO physical bands, ZERO corroboration field, and ZERO RNG: ties break
    deterministically by row-major ``(y, x)`` index via ``np.argmax``.
    """
    state = np.asarray(base_mask, dtype=bool).copy()
    if n_add < 0:
        raise ValueError(f"n_add must be >= 0, got {n_add}")
    if n_add == 0:
        return state, {
            "requested": 0,
            "filled": 0,
            "spacing_px": float(spacing_px),
            "spacing_pool_cells": 0,
            "min_pick_clearance_px": None,
        }
    by, bx = np.nonzero(state)
    cy, cx = np.nonzero(np.asarray(cand_mask, dtype=bool) & ~state)
    if len(cy) == 0:
        raise ValueError("Empty refill candidate pool")
    if len(by) > 0:
        d_init = cKDTree(np.column_stack([by, bx]).astype(np.float64)).query(
            np.column_stack([cy, cx]).astype(np.float64), k=1
        )[0]
    else:
        d_init = np.full(len(cy), np.inf, dtype=np.float64)

    keep = d_init >= float(spacing_px)
    if int(keep.sum()) < n_add:
        raise ValueError(
            f"Only {int(keep.sum())} cage-free refill cells at >= {spacing_px} px from "
            f"survivors, but {n_add} are required"
        )
    cy_k = cy[keep].astype(np.int64)
    cx_k = cx[keep].astype(np.int64)
    cur_d = d_init[keep].astype(np.float64).copy()

    chosen_idx: list[int] = []
    pick_clearances: list[float] = []
    for step in range(n_add):
        idx = int(np.argmax(cur_d))
        best_d = float(cur_d[idx])
        if best_d < float(spacing_px):
            raise ValueError(
                f"Farthest-point spacing lock (< {spacing_px} px) exhausted pool at step "
                f"{step} of {n_add} (best remaining clearance {best_d:.4f} px)"
            )
        chosen_idx.append(idx)
        pick_clearances.append(best_d)
        ry, rx = int(cy_k[idx]), int(cx_k[idx])
        d_new = np.hypot(cy_k - ry, cx_k - rx)
        cur_d = np.minimum(cur_d, d_new)
        cur_d[idx] = -1.0

    ry_sel = cy_k[chosen_idx]
    rx_sel = cx_k[chosen_idx]
    state[ry_sel, rx_sel] = True
    return state, {
        "requested": int(n_add),
        "filled": len(chosen_idx),
        "spacing_px": float(spacing_px),
        "spacing_pool_cells": int(len(cy_k)),
        "first_pick_clearance_px": round(float(pick_clearances[0]), 4),
        "median_pick_clearance_px": round(float(np.median(pick_clearances)), 4),
        "min_pick_clearance_px": round(float(min(pick_clearances)), 4),
    }


def build_lt3_spaced_arm(
    parent: np.ndarray,
    support_union: np.ndarray,
    d_catalogue: np.ndarray,
    w: np.ndarray,
    spacing_px: float = SPACING_PX,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Prune strictly d_catalogue < 3.0 px (preserving d_cat == 3.0 px) + spaced w refill."""
    survivors = np.asarray(parent, dtype=bool) & ~(d_catalogue < 3.0)
    n_removed = int(np.asarray(parent, dtype=bool).sum() - survivors.sum())
    if n_removed <= 0:
        raise ValueError("Collar d_catalogue < 3.0 px removed no parent dots")
    preserved_at_3px = int((survivors & (d_catalogue == 3.0)).sum())
    pool = np.asarray(support_union, dtype=bool) & ~survivors & (d_catalogue >= 3.0)
    out, sp_stats = bps.spaced_marginal_add(
        base_mask=survivors,
        cand_mask=pool,
        w=w,
        n_add=n_removed,
        spacing_px=spacing_px,
    )
    return out, {
        "collar_rule": "d_catalogue < 3.0",
        "collar_px": 3.0,
        "strict_inequality": True,
        "preserved_exact_3px_parent_dots": preserved_at_3px,
        "n_removed": n_removed,
        "n_added": int((out & ~survivors).sum()),
        "n_dots": int(out.sum()),
        "refill_pool_cells": int(pool.sum()),
        "spacing": sp_stats,
    }


def build_provided_crest_support_and_field(
    verified: dict[str, Path],
    foot: np.ndarray,
    catalogue: np.ndarray,
    h19_5: np.ndarray,
    target_extra_px: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, float], dict[str, Any]]:
    """Build area-matched provided-band Hessian breakline/gradient crest support & field.

    Uses ONLY organizer-provided ``training_features.tif`` Bands 3, 15, 18, 19:
      - Band 19 ``det_elev_slope``: ``Hessian(|grad(det_elev_slope)|, 1.5)`` isolates
        piedmont/range-front slope-inflection breaklines while rejecting constant-slope
        bedrock canyon walls.
      - Band 3 ``tmi_hg`` & Band 18 ``iso_grav_anom_hg``: ``Hessian(., 1.5)`` isolates
        magnetic and isostatic-gravity fault-contact gradient crests.
      - Band 15 ``depth_to_base_surf``: ``Hessian(|grad(depth_to_base_surf)|, 1.5)``
        isolates concealed Cenozoic basin-bounding basement fault steps.
    Zero ``H19-4``/``H16-1``, zero external LiDAR, zero GDR 1391 wells.
    All channels pass single-feature leakage canaries BEFORE catalogue masking.
    """
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)
    pos_mask = folds20[0]["hidden_all"] | folds30[0]["hidden_all"]
    del folds20, folds30, gd
    neg_pool = np.flatnonzero(foot & ~catalogue & ~pos_mask)
    rng = np.random.default_rng(20261023)
    neg_sample = rng.choice(neg_pool, size=min(100_000, len(neg_pool)), replace=False)
    del neg_pool
    pos_idx = np.flatnonzero(pos_mask)
    del pos_mask
    eval_idx = np.concatenate([pos_idx, neg_sample])
    y_true = np.concatenate(
        [np.ones(len(pos_idx), dtype=np.int8), np.zeros(len(neg_sample), dtype=np.int8)]
    )

    prov_canaries: dict[str, float] = {}

    def _audit_pr(name: str, arr: np.ndarray) -> np.ndarray:
        auc = float(roc_auc_score(y_true, arr.ravel()[eval_idx]))
        sym_auc = float(max(auc, 1.0 - auc))
        prov_canaries[name] = round(sym_auc, 5)
        if sym_auc > 0.90:
            raise RuntimeError(
                f"LEAKAGE CANARY TRIPPED on {name}: symmetric AUC = {sym_auc:.5f} > 0.90"
            )
        return bpv._percentile_rank(arr, foot)

    def _clean(ds: rasterio.DatasetReader, idx: int) -> np.ndarray:
        a = np.where(foot, np.nan_to_num(ds.read(idx), nan=0.0), 0.0).astype(np.float32)
        bad = (~np.isfinite(a)) | (np.abs(a) > 1e20)
        if np.any(bad & foot):
            a[bad] = float(np.median(a[foot & ~bad]))
        a[~foot] = 0.0
        return a

    with rasterio.open(verified["training_features"]) as ds:
        b19 = _clean(ds, 19)
        gy19, gx19 = np.gradient(gaussian_filter(b19, 1.5))
        del b19
        grad19 = np.hypot(gy19, gx19).astype(np.float32)
        del gy19, gx19
        c_b19 = _audit_pr("prov_slope_break_hess_b19", bpv._hessian_ridge(grad19, 1.5))
        del grad19

        b03 = _clean(ds, 3)
        c_b03 = _audit_pr("prov_tmi_hg_hess_b03", bpv._hessian_ridge(b03, 1.5))
        del b03

        b18 = _clean(ds, 18)
        c_b18 = _audit_pr("prov_grav_hg_hess_b18", bpv._hessian_ridge(b18, 1.5))
        del b18

        b15 = _clean(ds, 15)
        gy15, gx15 = np.gradient(gaussian_filter(b15, 1.5))
        del b15
        grad15 = np.hypot(gy15, gx15).astype(np.float32)
        del gy15, gx15
        c_b15 = _audit_pr("prov_basement_step_hess_b15", bpv._hessian_ridge(grad15, 1.5))
        del grad15

    provided_crest = (
        0.45 * c_b19 + 0.20 * c_b03 + 0.20 * c_b18 + 0.15 * c_b15
    ).astype(np.float32)
    provided_crest[~foot] = 0.0
    del c_b19, c_b03, c_b18, c_b15

    auc_comp = float(roc_auc_score(y_true, provided_crest.ravel()[eval_idx]))
    sym_comp = float(max(auc_comp, 1.0 - auc_comp))
    prov_canaries["prov_composite_crest"] = round(sym_comp, 5)
    if sym_comp > 0.90:
        raise RuntimeError(f"LEAKAGE CANARY TRIPPED on prov_composite_crest: {sym_comp:.5f}")

    crest_candidates = directional_crest_1d(provided_crest, foot & ~h19_5)
    ry, rx = np.nonzero(crest_candidates)
    if len(ry) < target_extra_px:
        raise ValueError(
            f"Provided-band crest candidates ({len(ry)}) fewer than target_extra_px ({target_extra_px})"
        )
    order = np.argsort(-provided_crest[ry, rx], kind="stable")
    sel = order[:target_extra_px]
    prov_extra = np.zeros(foot.shape, dtype=bool)
    prov_extra[ry[sel], rx[sel]] = True
    prov_union = h19_5 | prov_extra

    # Calibrated label-free expected-fault weight on off-catalogue pixels (provided bands only)
    w_prov = np.where(
        foot & ~catalogue,
        np.where(prov_union, 0.04 + 0.22 * provided_crest, 0.005 + 0.04 * provided_crest),
        0.0,
    ).astype(np.float32)

    meta = {
        "provided_bands_used": [
            "Band 3: tmi_hg",
            "Band 15: depth_to_base_surf",
            "Band 18: iso_grav_anom_hg",
            "Band 19: det_elev_slope",
        ],
        "external_rasters_used": [],
        "sibling_supports_used": ["anc_h19_5 (parent support only; zero H19-4, zero H16-1)"],
        "h19_5_pixels": int(h19_5.sum()),
        "directional_crest_pool_outside_h19_5": int(len(ry)),
        "selected_extra_crest_pixels": int(prov_extra.sum()),
        "total_union_pixels": int(prov_union.sum()),
        "min_selected_crest_score": round(float(provided_crest[ry[sel[-1]], rx[sel[-1]]]), 6),
        "mean_crest_on_h19_5": round(float(provided_crest[h19_5].mean()), 6),
        "mean_crest_on_footprint": round(float(provided_crest[foot].mean()), 6),
    }
    return prov_union, w_prov, prov_canaries, meta


# ---------------------------------------------------------------------------
# Reference reconstruction of p3space35 / p4space35 (clears SLOT_PLAN blocker)
# ---------------------------------------------------------------------------


def reconstruct_and_verify_spaced_pivots(
    parent: np.ndarray,
    support_union: np.ndarray,
    d_catalogue: np.ndarray,
    w: np.ndarray,
    foot: np.ndarray,
    catalogue: np.ndarray,
    sample_path: Path,
    ledger_rows: list[dict[str, str]],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Rebuild existing p3space35 & p4space35 byte-identically on disk (zero new ledger rows)."""
    row_by_val = {
        r["value"]: r
        for r in ledger_rows
        if r["parent"] == PARENT_ID and r["axis"] == "PRUNE" and r["value"] in ("p3space35", "p4space35")
    }
    if set(row_by_val) != {"p3space35", "p4space35"}:
        raise RuntimeError("Expected p3space35 and p4space35 in ledger/submissions.csv")

    with rasterio.open(sample_path) as tpl:
        prof_nan = tpl.profile.copy()
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

    rebuilt_masks: dict[str, np.ndarray] = {}
    rebuilt_info: dict[str, Any] = {}
    tifs_to_validate: list[Path] = []

    for spec in bps.SPECS:
        val = spec["value"]
        if val not in ("p3space35", "p4space35"):
            continue
        mask, _ = bps.build_arm(parent, support_union, d_catalogue, w, spec)
        row = row_by_val[val]
        vid = row["id"]
        p_nan = RELEASES / f"{vid}.tif"
        p_zeros = RELEASES / f"{vid}-zeros.tif"
        z_nan = RELEASES / f"{vid}.zip"
        z_zeros = RELEASES / f"{vid}-zeros.zip"
        RELEASES.mkdir(parents=True, exist_ok=True)

        arr_nan = np.where(foot, mask.astype(np.float32), np.nan).astype(np.float32)
        arr_zeros = np.where(foot, mask.astype(np.float32), 0.0).astype(np.float32)
        with rasterio.open(p_nan, "w", **prof_nan) as dst:
            dst.write(arr_nan, 1)
        with rasterio.open(p_zeros, "w", **prof_zeros) as dst:
            dst.write(arr_zeros, 1)

        sha_nan = bpv.sha256_file(p_nan)
        sha_zeros = bpv.sha256_file(p_zeros)
        if sha_nan != row["sha256"] or sha_zeros != row["sha256_zeros"]:
            raise RuntimeError(
                f"Byte reconstruction mismatch for {vid}: got ({sha_nan}, {sha_zeros}) vs "
                f"ledger ({row['sha256']}, {row['sha256_zeros']})"
            )
        for tif_p, zip_p in ((p_nan, z_nan), (p_zeros, z_zeros)):
            with zipfile.ZipFile(zip_p, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(tif_p, arcname=tif_p.name)
            os.chmod(tif_p, 0o644)
            os.chmod(zip_p, 0o644)

        rebuilt_masks[val] = mask
        tifs_to_validate.extend([p_nan, p_zeros])
        rebuilt_info[val] = {
            "id": vid,
            "sha256": sha_nan,
            "sha256_zeros": sha_zeros,
            "byte_exact_ledger_match": True,
            "n_dots": int(mask.sum()),
        }

    # Run hardened validate_variant.py on all 4 reconstructed files
    with rasterio.open(sample_path) as src:
        sample_meta = {
            "crs": str(src.crs),
            "shape": [src.height, src.width],
            "transform": [round(float(x), 6) for x in tuple(src.transform)[:6]],
        }
    dist32 = distance_transform_edt(~catalogue).astype(np.float32)
    hashes_map = vv.ledger_hashes()
    val_results = [
        vv.validate(p, foot, catalogue, dist32, parent, sample_meta, hashes_map)
        for p in tifs_to_validate
    ]
    if not all(r["gates_pass"] for r in val_results):
        raise RuntimeError("Reconstructed p3space35/p4space35 failed hardened validate_variant.py")
    write_json(
        RECON_VALIDATION_PATH,
        {
            "validator": "validate_variant.py",
            "note": "Exact byte-identical reconstruction and fresh hardened-gate validation of already-ledgered PRUNEp3space35 (49fff49b) and PRUNEp4space35 (07bd8182); zero new ledger rows.",
            "gates_all_pass": True,
            "rebuilt": rebuilt_info,
            "results": val_results,
        },
    )
    return rebuilt_masks["p3space35"], rebuilt_info


def refill_nn_summary(candidate: np.ndarray, survivors: np.ndarray) -> dict[str, float]:
    added = candidate & ~survivors
    pts_all = np.argwhere(candidate).astype(np.float64)
    pts_add = np.argwhere(added).astype(np.float64)
    tree = cKDTree(pts_all)
    nn_all = tree.query(pts_all, k=2)[0][:, 1]
    nn_add = tree.query(pts_add, k=2)[0][:, 1]
    return {
        "all_min_nn_px": round(float(nn_all.min()), 4),
        "all_median_nn_px": round(float(np.median(nn_all)), 4),
        "all_mean_nn_px": round(float(nn_all.mean()), 4),
        "refill_min_nn_px": round(float(nn_add.min()), 4),
        "refill_median_nn_px": round(float(np.median(nn_add)), 4),
        "refill_mean_nn_px": round(float(nn_add.mean()), 4),
        "refill_frac_nn_ge_6px_non_overlapping_kernels": round(float((nn_add >= 6.0).mean()), 4),
    }


def load_support_union(verified: dict[str, Path], foot: np.ndarray) -> tuple[np.ndarray, dict[str, int]]:
    support_union = np.zeros(foot.shape, dtype=bool)
    support_parts: dict[str, int] = {}
    for key in bps.SOURCE_SUPPORTS:
        with rasterio.open(verified[key]) as ds:
            mask = (np.nan_to_num(ds.read(1), nan=0.0) > 0) & foot
        support_parts[key] = int(mask.sum())
        support_union |= mask
    return support_union, support_parts


def main() -> int:
    if not PREREG_PATH.is_file():
        raise FileNotFoundError(f"Preregistration must exist before build: {PREREG_PATH}")
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    assert prereg["frozen_before_any_variant_proxy_or_sgmc"] is True

    # 1. Verify all 15 manifest pins and rebuild R0 byte-exactly
    verified = bpv.verify_manifest(MANIFEST)
    manifest_sha = bpv.sha256_file(MANIFEST)
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot = lineage["foot"]
    catalogue = lineage["catalogue"]
    d_catalogue = lineage["d_cat"]
    parent = lineage["r0"]
    h19_5 = lineage["h19_5"]
    assert int(parent.sum()) == N_DOTS

    # 2. Load ledger and scope-clean ONLY our 3 values on rerun (IR-88-50 idempotency)
    all_rows, ledger_fields = bps.load_ledger()
    purged_ids = {
        r["id"]
        for r in all_rows
        if r.get("parent") == PARENT_ID and r.get("axis") == AXIS and r.get("value") in OUR_VALUES
    }
    kept_rows = [r for r in all_rows if r["id"] not in purged_ids]
    for val in OUR_VALUES:
        for old_p in RELEASES.glob(f"{PARENT_ID}-{AXIS}{val}-{DATE}-*"):
            old_p.unlink(missing_ok=True)
    for pid in purged_ids:
        for old_p in RELEASES.glob(f"{pid}*"):
            old_p.unlink(missing_ok=True)

    # 3. Load ancestor union H19-5 | H19-4 | H16-1
    support_union, support_parts = load_support_union(verified, foot)
    extra_anc_px = int((support_union & ~h19_5).sum())  # 35,954

    # 4. Build four-line w field + canaries AND provided-band crest support/field + canaries
    w_fourline, canaries_fourline = bpv.build_physical_field_and_canaries(
        verified=verified, foot=foot, catalogue=catalogue, h19_5=h19_5
    )
    prov_union, w_prov, canaries_prov, prov_meta = build_provided_crest_support_and_field(
        verified=verified,
        foot=foot,
        catalogue=catalogue,
        h19_5=h19_5,
        target_extra_px=extra_anc_px,
    )
    assert int(prov_union.sum()) == int(support_union.sum()) == 157_085
    all_canaries = {**canaries_fourline, **canaries_prov}
    if max(all_canaries.values()) > 0.90:
        raise RuntimeError(f"LEAKAGE CANARY FAILURE: {all_canaries}")

    # 5. Reconstruct existing p3space35 & p4space35 byte-identically on disk + hardened validate
    p3space35_mask, recon_info = reconstruct_and_verify_spaced_pivots(
        parent=parent,
        support_union=support_union,
        d_catalogue=d_catalogue,
        w=w_fourline,
        foot=foot,
        catalogue=catalogue,
        sample_path=verified["sample_submission"],
        ledger_rows=kept_rows,
    )

    # 6. Build the 3 preregistered single-factor PRUNE variants of R0
    candidates: dict[str, np.ndarray] = {}
    arm_meta: dict[str, dict[str, Any]] = {}

    # Arm 1: lt3space35 (d_cat < 3.0 px, 1,611 removed, >= 3.5 px w-ranked refill on union_anc)
    mask_lt3, st_lt3 = build_lt3_spaced_arm(
        parent=parent,
        support_union=support_union,
        d_catalogue=d_catalogue,
        w=w_fourline,
        spacing_px=SPACING_PX,
    )
    surv_lt3 = parent & ~(d_catalogue < 3.0)
    st_lt3["nn_summary"] = refill_nn_summary(mask_lt3, surv_lt3)
    st_lt3["overlap_with_p3space35_dots"] = int((mask_lt3 & p3space35_mask).sum())
    candidates[f"{PARENT_ID}-{AXIS}lt3space35"] = mask_lt3
    arm_meta["lt3space35"] = st_lt3

    # Arm 2: p3space35fp (d_cat <= 3.0 px, 2,171 removed, >= 3.5 px score-blind farthest-point refill)
    surv_le3 = parent & ~(d_catalogue <= 3.0)
    n_rem_le3 = int(parent.sum() - surv_le3.sum())
    pool_le3_anc = support_union & ~surv_le3 & (d_catalogue > 3.0)
    mask_fp, sp_fp = spaced_farthest_point_add(
        base_mask=surv_le3,
        cand_mask=pool_le3_anc,
        n_add=n_rem_le3,
        spacing_px=SPACING_PX,
    )
    st_fp = {
        "collar_rule": "d_catalogue <= 3.0",
        "collar_px": 3.0,
        "strict_inequality": False,
        "preserved_exact_3px_parent_dots": 0,
        "n_removed": n_rem_le3,
        "n_added": int((mask_fp & ~surv_le3).sum()),
        "n_dots": int(mask_fp.sum()),
        "refill_pool_cells": int(pool_le3_anc.sum()),
        "spacing": sp_fp,
        "nn_summary": refill_nn_summary(mask_fp, surv_le3),
        "overlap_with_p3space35_dots": int((mask_fp & p3space35_mask).sum()),
        "refill_overlap_with_p3space35_refills": int(
            ((mask_fp & ~surv_le3) & (p3space35_mask & ~surv_le3)).sum()
        ),
    }
    candidates[f"{PARENT_ID}-{AXIS}p3space35fp"] = mask_fp
    arm_meta["p3space35fp"] = st_fp

    # Arm 3: p3space35prov (d_cat <= 3.0 px, 2,171 removed, >= 3.5 px refill on 157,085-px provided-band crests)
    pool_le3_prov = prov_union & ~surv_le3 & (d_catalogue > 3.0)
    mask_prov, sp_prov = bps.spaced_marginal_add(
        base_mask=surv_le3,
        cand_mask=pool_le3_prov,
        w=w_prov,
        n_add=n_rem_le3,
        spacing_px=SPACING_PX,
    )
    st_prov = {
        "collar_rule": "d_catalogue <= 3.0",
        "collar_px": 3.0,
        "strict_inequality": False,
        "preserved_exact_3px_parent_dots": 0,
        "n_removed": n_rem_le3,
        "n_added": int((mask_prov & ~surv_le3).sum()),
        "n_dots": int(mask_prov.sum()),
        "refill_pool_cells": int(pool_le3_prov.sum()),
        "spacing": sp_prov,
        "provided_support": prov_meta,
        "nn_summary": refill_nn_summary(mask_prov, surv_le3),
        "overlap_with_p3space35_dots": int((mask_prov & p3space35_mask).sum()),
        "refill_overlap_with_p3space35_refills": int(
            ((mask_prov & ~surv_le3) & (p3space35_mask & ~surv_le3)).sum()
        ),
    }
    candidates[f"{PARENT_ID}-{AXIS}p3space35prov"] = mask_prov
    arm_meta["p3space35prov"] = st_prov

    # 7. Compute w-field expected DTI (diagnostic) and REPORT-ONLY instruments
    parent_w = bpv.weighted_expected_dti(parent, w_fourline)
    pivot_w = bpv.weighted_expected_dti(p3space35_mask, w_fourline)
    for val in OUR_VALUES:
        key = f"{PARENT_ID}-{AXIS}{val}"
        wd = bpv.weighted_expected_dti(candidates[key], w_fourline)
        arm_meta[val]["expected_dti_fourline_w"] = round(float(wd["dti"]), 6)
        arm_meta[val]["expected_dti_delta_vs_r0"] = round(float(wd["dti"] - parent_w["dti"]), 6)
        arm_meta[val]["expected_dti_delta_vs_p3space35"] = round(
            float(wd["dti"] - pivot_w["dti"]), 6
        )

    eval_arms = {
        PARENT_ID: parent,
        P3SPACE35_ID: p3space35_mask,
        **candidates,
    }
    diagnostics = bpv.evaluate_report_only_instruments(
        arms=eval_arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )

    # 8. Write GeoTIFFs + ZIPs + disk re-read gates
    existing_shas = bps.ledger_hashes(kept_rows)
    form_notes = {
        "lt3space35": "h33-2-b2; PRUNE d_cat<3px (-1611, keep 560 d=3px) +1611 >=3.5px refill, N=37654; pred +0.006 MODEL",
        "p3space35fp": "h33-2-b2; PRUNE <=3px (-2171) +2171 >=3.5px farthest-point null-rank refill, N=37654; pred +0.008 MODEL",
        "p3space35prov": "h33-2-b2; PRUNE <=3px (-2171) +2171 >=3.5px provided-band B19/3/18/15 crest refill, N=37654; pred +0.004 MODEL",
    }
    ranking_bases = {
        "lt3space35": (
            "Exact <3.0px collar (d^2<=8, preserving 560 d_cat==3.0px R0 dots where k(3.0)=0) + "
            "exact iterative marginal expected-DTI gain at >=3.5px spacing lock on H19-5|H19-4|H16-1 under four-line field w"
        ),
        "p3space35fp": (
            "Score-blind greedy farthest-point Euclidean completion (row-major tie-break; zero w-field, "
            "zero bands, zero RNG) at >=3.5px spacing lock on H19-5|H19-4|H16-1 outside d_cat<=3.0px"
        ),
        "p3space35prov": (
            "Exact iterative marginal expected-DTI gain at >=3.5px spacing lock on area-matched 157,085-px "
            "H19-5 union 35,954 1D-NMS structural crests of provided Bands 19/3/18/15 (zero H19-4/H16-1, zero external LiDAR/GDR)"
        ),
    }

    r0_sgmc = diagnostics[PARENT_ID]["sgmc_control"]["dti"]
    piv_sgmc = diagnostics[P3SPACE35_ID]["sgmc_control"]["dti"]

    new_rows: list[dict[str, str]] = []
    new_cards: dict[str, dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    built_tif_paths: list[Path] = []

    for val in OUR_VALUES:
        key = f"{PARENT_ID}-{AXIS}{val}"
        mask = candidates[key]
        st = arm_meta[val]
        arm_prereg = prereg["arms"][val]
        pred_str = arm_prereg["predicted_change_model"]
        pred_lo, pred_hi = arm_prereg["predicted_range_model"]

        rec = bpv.write_and_verify_variant(
            mask=mask,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=parent,
            axis=AXIS,
            value=val,
            note_template=form_notes[val],
            existing_shas=existing_shas,
            parent_id=PARENT_ID,
            parent_sha_zeros=bpv.PARENT_SHA_ZEROS,
            parent_sha_nan=bpv.PARENT_SHA_NAN,
            date=DATE,
            min_catalogue_px=3.0,
        )
        existing_shas.update((rec["sha256"], rec["sha256_zeros"]))
        built_tif_paths.extend([ROOT / rec["file_nan"], ROOT / rec["file_zeros"]])

        diag = diagnostics[key]
        sgmc_dti = diag["sgmc_control"]["dti"]
        d_sgmc_r0 = round(sgmc_dti - r0_sgmc, 6)
        d_sgmc_piv = round(sgmc_dti - piv_sgmc, 6)

        if val == "lt3space35":
            rec_note = (
                f"GATE-CLEAN (<3px exact kernel-zero collar; 0 pixels <3px, preserves 560 d_cat==3.0px R0 dots). "
                f"Blind SGMC {sgmc_dti:.6f} PROXY ({d_sgmc_r0:+.6f} vs R0, {d_sgmc_piv:+.6f} vs p3space35); "
                f"four-line field delta {st['expected_dti_delta_vs_r0']:+.6f} MODEL. "
                f"{'Slot-eligible alternative to p3space35.' if sgmc_dti > r0_sgmc else 'HOLD diagnostic.'}"
            )
            desc = (
                f"PRUNE strictly d_catalogue<3.0px (remove 1611 at d^2<=8, preserve 560 R0 dots at exact d_cat==3.0px "
                f"where k(3.0)=0); spacing-locked refill 1611 at >=3.5px on H19-5|H19-4|H16-1, N fixed 37,654."
            )
        elif val == "p3space35fp":
            rec_note = (
                f"IR-88-45 RANKING FALSIFIER (score-blind farthest-point vs w-field on identical 6,632-cell pool, "
                f"min refill NN {st['nn_summary']['refill_min_nn_px']:.2f}px, median {st['nn_summary']['refill_median_nn_px']:.2f}px). "
                f"Blind SGMC {sgmc_dti:.6f} PROXY ({d_sgmc_r0:+.6f} vs R0, {d_sgmc_piv:+.6f} vs w-ranked p3space35); "
                f"four-line field delta {st['expected_dti_delta_vs_r0']:+.6f} MODEL."
            )
            desc = (
                f"PRUNE d_catalogue<=3.0px (remove 2171); score-blind greedy farthest-point refill 2171 at >=3.5px "
                f"on H19-5|H19-4|H16-1 (zero w-field, min refill NN {st['nn_summary']['refill_min_nn_px']:.2f}px), N fixed 37,654."
            )
        else:
            rec_note = (
                f"IR-88-45 PROVENANCE CONTROL (100% provided Bands 19/3/18/15 Hessian crests + H19-5, 157,085px area-matched; "
                f"zero H19-4/H16-1, zero external LiDAR/GDR). Blind SGMC {sgmc_dti:.6f} PROXY "
                f"({d_sgmc_r0:+.6f} vs R0, {d_sgmc_piv:+.6f} vs p3space35); four-line field delta {st['expected_dti_delta_vs_r0']:+.6f} MODEL."
            )
            desc = (
                f"PRUNE d_catalogue<=3.0px (remove 2171); >=3.5px refill 2171 on area-matched 157,085-px "
                f"H19-5 union provided-band B19/3/18/15 structural crests (zero H19-4/H16-1, zero external data), N fixed 37,654."
            )

        rec.update(
            {
                "evidence_class": "BUILT candidate; preregistered MODEL prediction; proxies REPORT ONLY; no receipt",
                "preregistration": str(PREREG_PATH.relative_to(ROOT)),
                "single_factor_vs_p3space35": arm_prereg["single_factor_vs_p3space35"],
                "manifest": {
                    "path": "registry/data_manifest.json",
                    "sha256": manifest_sha,
                    "verified_input_count": len(verified),
                    "all_manifest_inputs_verified": True,
                },
                "arm_statistics": st,
                "ranking_basis": ranking_bases[val],
                "leakage_canaries": {
                    "passed": True,
                    "max_single_feature_symmetric_auc": max(all_canaries.values()),
                    "channels": all_canaries,
                    "report_only": True,
                },
                "report_only_diagnostics": diag,
                "reference_diagnostics": {
                    "R0": diagnostics[PARENT_ID],
                    "p3space35_pivot": diagnostics[P3SPACE35_ID],
                    "sgmc_delta_vs_r0_PROXY": d_sgmc_r0,
                    "sgmc_delta_vs_p3space35_PROXY": d_sgmc_piv,
                },
                "model_prediction": {
                    "evidence_class": "MODEL",
                    "predicted_change": f"MODEL:{pred_str}",
                    "range": [pred_lo, pred_hi],
                    "frozen_before_proxies": True,
                    "no_evidence_if_abs_live_delta_below": NO_EVIDENCE_BAND,
                },
                "build_script_sha256": bpv.sha256_file(Path(__file__).resolve()),
                "not_submitted": True,
            }
        )
        write_json(RELEASES / f"{rec['id']}.json", rec)
        receipts.append(rec)

        pct_exact = 100.0 * st["n_removed"] / N_DOTS
        new_cards[rec["id"]] = {
            "id": rec["id"],
            "parent": PARENT_ID,
            "axis": AXIS,
            "value": val,
            "hypothesis": arm_prereg["hypothesis"],
            "mechanism": (
                f"Single-factor PRUNE contrast against {P3SPACE35_ID}: {arm_prereg['single_factor_vs_p3space35']}. "
                f"Removes {st['n_removed']} R0 dots ({pct_exact:.5f}%) and adds {st['n_added']} dots at >= {SPACING_PX} px "
                f"spacing lock (N fixed at {N_DOTS}; 0 pixels < 3.0 px from catalogue; min refill NN "
                f"{st['nn_summary']['refill_min_nn_px']:.2f} px, median {st['nn_summary']['refill_median_nn_px']:.2f} px)."
            ),
            "non_fault_mimic": arm_prereg["non_fault_mimic"],
            "predicted_sign_size": (
                f"MODEL {pred_str} live DTI vs R0 (frozen preregistered range [{pred_lo:+.3f}, {pred_hi:+.3f}]; "
                f"|live delta| < {NO_EVIDENCE_BAND:.2f} on public chunks is no evidence)."
            ),
            "predicted_sign_and_size": (
                f"MODEL {pred_str} live DTI vs R0 (range [{pred_lo:+.3f}, {pred_hi:+.3f}])."
            ),
            "falsifier": arm_prereg["falsifier"],
            "confounder": (
                "Public leaderboard samples only a subset of spatial chunks; SGMC off-catalogue control is bedrock-biased "
                "and four-line field w is in-sample on ancestor supports (IR-88-44/45)."
            ),
            "post_build_report_only": {
                "evidence_label": "PROXY / MODEL (never a score, never a gate)",
                "sgmc_off_catalogue_dti_PROXY": sgmc_dti,
                "sgmc_delta_vs_r0_PROXY": d_sgmc_r0,
                "sgmc_delta_vs_p3space35_PROXY": d_sgmc_piv,
                "holdout_dti_PROXY": diag["holdout_proxy"]["dti"],
                "holdout_withheld_positives": diag["holdout_proxy"]["withheld_positives"],
                "holdout_ci95_PROXY": diag["holdout_proxy"]["ci95"],
                "fourline_w_expected_dti_delta_vs_r0_MODEL": st["expected_dti_delta_vs_r0"],
                "block_cv_10km": diag["block_density_cv"]["cv_10km_100px_interior"],
                "block_cv_12km": diag["block_density_cv"]["cv_12km_120px_interior"],
            },
            "references": REFERENCES,
        }

        new_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": AXIS,
                "value": val,
                "n_dots": str(N_DOTS),
                "pct_changed": f"{pct_exact:.5f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{pred_str}",
                "predicted_range": f"[{pred_lo:+.3f},{pred_hi:+.3f}]",
                "ranking_basis": ranking_bases[val],
                "receipt_score": "",
                "receipt_date": "",
                "description": desc,
                "recommendation": rec_note,
            }
        )

    # 9. Update ledger atomically (verify global uniqueness of (parent, axis, value) and SHA-256)
    combined_rows = [*kept_rows, *new_rows]
    seen_pairs: set[tuple[str, str, str]] = set()
    seen_shas: set[str] = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}
    for r in combined_rows:
        pair = (r["parent"], r["axis"], r["value"])
        if pair in seen_pairs:
            raise RuntimeError(f"Duplicate (parent, axis, value) in ledger: {pair}")
        seen_pairs.add(pair)
        for col in ("sha256", "sha256_zeros"):
            h = r[col]
            if h in seen_shas:
                raise RuntimeError(f"Duplicate SHA-256 in ledger: {h}")
            seen_shas.add(h)

    tmp_ledger = LEDGER.with_suffix(".csv.tmp")
    with tmp_ledger.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ledger_fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for r in combined_rows:
            writer.writerow({k: r.get(k, "") for k in ledger_fields})
    os.replace(tmp_ledger, LEDGER)

    # 10. Update mechanism_cards.json (removing only purged_ids, adding new_cards)
    cards = json.loads(CARDS_PATH.read_text(encoding="utf-8")) if CARDS_PATH.is_file() else {}
    for pid in purged_ids:
        cards.pop(pid, None)
    cards.update(new_cards)
    write_json(CARDS_PATH, cards)

    # 11. Run independent hardened validate_variant.py on all 6 new GeoTIFFs AFTER ledger write
    with rasterio.open(verified["sample_submission"]) as src:
        sample_meta = {
            "crs": str(src.crs),
            "shape": [src.height, src.width],
            "transform": [round(float(x), 6) for x in tuple(src.transform)[:6]],
        }
    dist32 = distance_transform_edt(~catalogue).astype(np.float32)
    hashes_after = vv.ledger_hashes()
    val_results = [
        vv.validate(p, foot, catalogue, dist32, parent, sample_meta, hashes_after)
        for p in built_tif_paths
    ]
    if not all(r["gates_pass"] for r in val_results):
        raise RuntimeError(f"Hardened validate_variant.py failed: {val_results}")
    # Also assert non_prune_clearance_ge_3px (under_3px == 0) is literally 0 on ALL 6 files!
    for r in val_results:
        u3 = r["checks"]["non_prune_clearance_ge_3px"]["detail"]["positive_pixels_below_3px"]
        if u3 != 0:
            raise RuntimeError(f"Expected 0 positive pixels < 3 px, got {u3} in {r['artifact']}")

    write_json(
        VALIDATION_PATH,
        {
            "validator": "validate_variant.py",
            "gates_all_pass": True,
            "all_positive_pixels_ge_3px": True,
            "results": val_results,
        },
    )

    # 12. Write comprehensive axis evidence report
    report = {
        "schema": "gems88.prune-deconfound-report.v1",
        "created_utc": utc_now(),
        "session_date": DATE,
        "axis": AXIS,
        "parent": {
            "id": PARENT_ID,
            "n_dots": N_DOTS,
            "rebuilt_zeros_sha256": lineage["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lineage["rebuilt_nan_sha256"],
            "evidence_class": "REBUILT byte-exact parent; historical live 0.2778 remains CLAIM",
        },
        "control_pivot_rebuilt_byte_exact": recon_info,
        "preregistration": str(PREREG_PATH.relative_to(ROOT)),
        "git_sha": bpv.git_sha(),
        "seed": SEED,
        "manifest": {
            "path": "registry/data_manifest.json",
            "sha256": manifest_sha,
            "verified_input_count": len(verified),
            "all_manifest_inputs_verified": True,
        },
        "support_ cardinalities": {
            "anc_h19_5": support_parts["anc_h19_5"],
            "anc_h19_4": support_parts["anc_h19_4"],
            "anc_h16_1": support_parts["anc_h16_1"],
            "lineage_union_px": int(support_union.sum()),
            "provided_crest_union_px": int(prov_union.sum()),
            "exact_cardinality_matched": int(prov_union.sum()) == int(support_union.sum()),
        },
        "leakage_canaries": {
            "passed": True,
            "max_single_feature_symmetric_auc": max(all_canaries.values()),
            "channels": all_canaries,
            "report_only": True,
        },
        "reference_diagnostics_REPORT_ONLY": {
            "R0": diagnostics[PARENT_ID],
            "p3space35_pivot": diagnostics[P3SPACE35_ID],
            "R0_fourline_w_expected_dti_MODEL": round(float(parent_w["dti"]), 6),
            "p3space35_fourline_w_expected_dti_MODEL": round(float(pivot_w["dti"]), 6),
        },
        "variants": [
            {
                "id": rec["id"],
                "value": rec["value"],
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "n_dots": rec["n_dots"],
                "pct_changed_moved": round(100.0 * arm_meta[rec["value"]]["n_removed"] / N_DOTS, 5),
                "form_note": rec["form_note"],
                "single_factor_vs_p3space35": rec["single_factor_vs_p3space35"],
                "preregistered_prediction": rec["model_prediction"],
                "arm_statistics": arm_meta[rec["value"]],
                "report_only_diagnostics": rec["report_only_diagnostics"],
                "sgmc_delta_vs_r0_PROXY": rec["reference_diagnostics"]["sgmc_delta_vs_r0_PROXY"],
                "sgmc_delta_vs_p3space35_PROXY": rec["reference_diagnostics"]["sgmc_delta_vs_p3space35_PROXY"],
            }
            for rec in receipts
        ],
        "hardened_validator": {
            "path": str(VALIDATION_PATH.relative_to(ROOT)),
            "gates_all_pass": True,
            "files_validated": len(val_results),
        },
        "no_submission": True,
    }
    # Fix accidental space in key name cleanly
    report["support_cardinalities"] = report.pop("support_ cardinalities")
    write_json(REPORT_PATH, report)

    print(
        json.dumps(
            {
                "ok": True,
                "parent_r0_rebuilt": True,
                "pivots_rebuilt_byte_exact": list(recon_info.keys()),
                "variants": [
                    {
                        "id": v["id"],
                        "value": v["value"],
                        "pct_changed": v["pct_changed_moved"],
                        "pred": v["preregistered_prediction"]["predicted_change"],
                        "sgmc_PROXY": v["report_only_diagnostics"]["sgmc_control"]["dti"],
                        "sgmc_vs_r0_PROXY": v["sgmc_delta_vs_r0_PROXY"],
                        "sgmc_vs_p3space35_PROXY": v["sgmc_delta_vs_p3space35_PROXY"],
                        "w_delta_vs_r0_MODEL": v["arm_statistics"]["expected_dti_delta_vs_r0"],
                    }
                    for v in report["variants"]
                ],
                "ledger_rows_total": len(combined_rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
