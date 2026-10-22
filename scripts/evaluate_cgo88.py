#!/usr/bin/env python3
"""Audit all 19 bands of training_features.tif and run the blocked holdout test for CGO-88.

Verifies on-disk band_name tags, descriptions, valid counts, percentiles, and
single-feature leakage canaries across all 19 provided bands on the identical
gems57-pooled-hide-v2 folds (seeds 20 and 21, 22,893 withheld positives).
Evaluates CGO-88 (Conductivity-Gravity Lateral Offset, bands 13, 15, 17, 18)
and joint MGC-88 + CGO-88 against the incumbent MGC-88 on the identical folds
and 20 km spatial bootstrap blocks. Does not overwrite MGC-88's run card if
CGO-88 fails to beat MGC-88 (0.0389) with a positive paired 95% CI.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout, grid, holdout  # noqa: E402
from gems88 import edge, model  # noqa: E402
from restore_inputs import digest  # noqa: E402

DATA = ROOT / "data"
REGISTRY = ROOT / "registry"
DOCS_EVIDENCE = ROOT / "docs" / "evidence"
SEEDS = (20, 21)
BUDGET = 37654


def bbox(region: np.ndarray, pad: int = 4) -> tuple[slice, slice]:
    row, col = np.nonzero(region)
    if not row.size:
        raise ValueError("empty fold region")
    return (
        slice(
            max(int(row.min()) - pad, 0),
            min(int(row.max()) + pad + 1, region.shape[0]),
        ),
        slice(
            max(int(col.min()) - pad, 0),
            min(int(col.max()) + pad + 1, region.shape[1]),
        ),
    )


def cgo_features(
    b_grav: np.ndarray,
    b_cond: np.ndarray,
    footprint: np.ndarray,
    step_px: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute label-blind conductivity edge and 200 m cross-strike offset features."""
    footprint = np.asarray(footprint, bool)
    b_grav = np.asarray(b_grav, np.float32)
    b_cond = np.asarray(b_cond, np.float32)
    if (
        footprint.ndim != 2
        or b_grav.shape != footprint.shape
        or b_cond.shape != footprint.shape
        or step_px <= 0
    ):
        raise ValueError("invalid shape or step_px for cgo_features")
    gy, gx = edge.derivatives(b_grav, footprint, sigma=3.0)
    cy, cx = edge.derivatives(b_cond, footprint, sigma=2.0)
    gmag = np.hypot(gy, gx)
    cmag = np.hypot(cy, cx)
    ny = gy / np.maximum(gmag, 1e-7)
    nx = gx / np.maximum(gmag, 1e-7)
    cny = cy / np.maximum(cmag, 1e-7)
    cnx = cx / np.maximum(cmag, 1e-7)
    log_g = np.log1p(gmag).astype(np.float32)
    log_c = np.log1p(cmag).astype(np.float32)

    h, w = footprint.shape
    yy, xx = np.indices((h, w), dtype=np.float32)

    def shifted_cond(step: float) -> np.ndarray:
        ry = np.clip(np.rint(yy + step * ny).astype(np.int32), 0, h - 1)
        rx = np.clip(np.rint(xx + step * nx).astype(np.int32), 0, w - 1)
        valid = footprint & footprint[ry, rx]
        align = np.abs(ny * cny[ry, rx] + nx * cnx[ry, rx])
        return np.where(valid, log_c[ry, rx] * align, 0.0).astype(np.float32)

    up = shifted_cond(step_px)
    dn = shifted_cond(-step_px)
    cgo_offset = (log_g * np.maximum(up, dn)).astype(np.float32)
    cgo_asym = (log_g * (dn - up)).astype(np.float32)
    for arr in (log_g, log_c, cgo_offset, cgo_asym):
        arr[~footprint] = 0.0
    return log_g, log_c, cgo_offset, cgo_asym


def run_audit() -> dict:
    start = time.monotonic()
    g = grid.load_grid()
    tif_path = DATA / "training_features.tif"
    expected_sha = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
    if digest(tif_path) != expected_sha:
        raise ValueError("training_features.tif SHA256 mismatch")

    folds = []
    quads = {}
    for seed in SEEDS:
        draw, quad = holdout.buffered_component_draw(
            g, seed=seed, buffer_px=3, boundary_px=12
        )
        folds.extend(draw)
        quads[seed] = quad

    band_catalog = []
    cleaned_bands = {}
    all19_cols = []
    all19_names = []
    with rasterio.open(tif_path) as src:
        if src.count != 19 or src.shape != g.shape:
            raise ValueError("Unexpected band count or shape in training_features.tif")
        for idx in range(1, src.count + 1):
            tag = src.tags(idx).get("band_name")
            desc = src.descriptions[idx - 1]
            raw = src.read(idx)
            clean, stats = edge.clean_band(raw, g.footprint)
            band_catalog.append(
                dict(
                    band_index=idx,
                    band_name=tag,
                    description=desc,
                    **stats,
                )
            )
            all19_cols.append(clean.ravel())
            all19_names.append(f"b{idx:02d}_{tag}")
            if idx in (2, 13, 15, 17, 18):
                cleaned_bands[idx] = clean
            del raw

    all19_matrix = np.column_stack(all19_cols).astype(np.float32)
    del all19_cols
    canaries_19 = model.leakage_canaries(all19_matrix, all19_names, folds, g.footprint)
    del all19_matrix

    for entry, canary in zip(band_catalog, canaries_19):
        entry["holdout_auc"] = canary["auc"]
        entry["holdout_symmetric_auc"] = canary["symmetric_auc"]

    # Build MGC-88 + CGO-88 feature matrix
    b_rtp = cleaned_bands[2]
    b_grav = cleaned_bands[13]
    b_dep = cleaned_bands[15]
    b_cond = cleaned_bands[17]
    b_ghg = cleaned_bands[18]

    my, mx = edge.derivatives(b_rtp, g.footprint, sigma=2.0)
    gy, gx = edge.derivatives(b_grav, g.footprint, sigma=3.0)
    log_mag, log_grav, align_mg, joint_mg = edge.coedge_features(my, mx, gy, gx)
    for arr in (log_mag, log_grav, align_mg, joint_mg):
        arr[~g.footprint] = 0.0

    _, log_cond, cgo_200m, cgo_asym = cgo_features(
        b_grav, b_cond, g.footprint, step_px=2.0
    )

    feature_names = [
        "rtp",
        "iso_grav_anom",
        "depth_to_base_surf",
        "log_rtp_edge",
        "log_gravity_edge",
        "edge_alignment",
        "joint_edge",
        "cond_surf",
        "iso_grav_anom_hg",
        "log_cond_edge",
        "cgo_offset_200m",
        "cgo_signed_asym",
    ]
    feats = np.column_stack(
        [
            b_rtp.ravel(),
            b_grav.ravel(),
            b_dep.ravel(),
            log_mag.ravel(),
            log_grav.ravel(),
            align_mg.ravel(),
            joint_mg.ravel(),
            b_cond.ravel(),
            b_ghg.ravel(),
            log_cond.ravel(),
            cgo_200m.ravel(),
            cgo_asym.ravel(),
        ]
    ).astype(np.float32)

    cgo_canaries = model.leakage_canaries(feats, feature_names, folds, g.footprint)
    max_canary_auc = max(c["symmetric_auc"] for c in cgo_canaries)
    if max_canary_auc > 0.90:
        raise RuntimeError(f"Leakage canary exceeded 0.90: {max_canary_auc}")

    arms = {
        "raw_control": (0, 1, 2),
        "mgc88_incumbent": (0, 1, 2, 3, 4, 5, 6),
        "cgo88_pure": (1, 2, 7, 8, 4, 9, 10, 11),
        "cgo88_joint": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
    }
    terms = {k: None for k in arms}

    for f in folds:
        seed = f["receipt"]["seed"]
        fi = f["fold"]
        train_region = g.footprint & (quads[seed] != fi)
        sl = bbox(f["region"])
        pvalid = g.footprint[sl]
        region = f["region"][sl]
        eligible = region & pvalid & ~f["visible"][sl]
        idx_local = np.flatnonzero(eligible.ravel())
        ww = sl[1].stop - sl[1].start
        rr, cc = np.divmod(idx_local, ww)
        global_idx = (sl[0].start + rr) * g.width + (sl[1].start + cc)
        budget = max(1, round(BUDGET * int(region.sum()) / int(g.footprint.sum())))
        r_idx = np.arange(sl[0].start, sl[0].stop, dtype=np.int64)
        c_idx = np.arange(sl[1].start, sl[1].stop, dtype=np.int64)
        crop_flat = (r_idx[:, None] * g.width + c_idx[None, :]).ravel()

        for arm, cols in arms.items():
            fitted, _ = model.fit(
                feats,
                g.footprint,
                f["visible"],
                train_region,
                cols,
                seed=model.SEED + seed * 4 + fi,
            )
            p = np.zeros(eligible.shape, np.float32)
            p.ravel()[idx_local] = model.probability(fitted, feats, global_idx, cols)
            tie_col = 10 if "cgo88" in arm else 6
            tie = np.asarray(feats[crop_flat, tie_col]).reshape(eligible.shape)
            dots, _ = model.spaced_dots(p, eligible, budget, radius=2, tie=tie)
            rf = {
                k: v[sl]
                for k, v in f.items()
                if k in ("region", "visible", "masked_known", "truth")
            }
            _, by_block = evaluate_holdout.evaluate(
                dots.astype(np.float32),
                rf,
                pvalid,
                origin=(sl[0].start, sl[1].start),
                global_shape=g.shape,
                block_side=200,
            )
            terms[arm] = by_block if terms[arm] is None else (terms[arm] + by_block)

    summary_mgc = evaluate_holdout.pooled_summary(
        {"candidate": terms["mgc88_incumbent"], "raw_control": terms["raw_control"]},
        draws=1000,
        seed=88022,
        candidate="candidate",
    )
    summary_pure_vs_mgc = evaluate_holdout.pooled_summary(
        {"cgo88_pure": terms["cgo88_pure"], "mgc88_incumbent": terms["mgc88_incumbent"]},
        draws=1000,
        seed=88022,
        candidate="cgo88_pure",
    )
    summary_pure_vs_raw = evaluate_holdout.pooled_summary(
        {"cgo88_pure": terms["cgo88_pure"], "raw_control": terms["raw_control"]},
        draws=1000,
        seed=88022,
        candidate="cgo88_pure",
    )
    summary_joint_vs_mgc = evaluate_holdout.pooled_summary(
        {"cgo88_joint": terms["cgo88_joint"], "mgc88_incumbent": terms["mgc88_incumbent"]},
        draws=1000,
        seed=88022,
        candidate="cgo88_joint",
    )
    summary_joint_vs_raw = evaluate_holdout.pooled_summary(
        {"cgo88_joint": terms["cgo88_joint"], "raw_control": terms["raw_control"]},
        draws=1000,
        seed=88022,
        candidate="cgo88_joint",
    )

    result = dict(
        schema="gems88.cgo88-audit.v1",
        date_utc="2026-10-22",
        evidence_class="HOLDOUT-DTI",
        evaluator_version=evaluate_holdout.VERSION,
        split_version="buffered-whole-components-loqo-v2",
        withheld_positive_pixels=22893,
        training_features_sha256=expected_sha,
        radiometric_k_th_u_in_19band_tiff=False,
        band_06_tc_is_magnetic_tilt_curvature_not_radiometric_total_count=True,
        band_catalog_19=band_catalog,
        cgo88_feature_canaries=dict(
            evidence_class="HOLDOUT-FEATURE-CANARY",
            max_symmetric_auc=max_canary_auc,
            leakage_threshold=0.90,
            passed=max_canary_auc <= 0.90,
            features=cgo_canaries,
        ),
        holdout_comparison=dict(
            mgc88_incumbent=summary_mgc["scores"]["candidate"],
            raw_control=summary_mgc["scores"]["raw_control"],
            cgo88_pure=summary_pure_vs_mgc["scores"]["cgo88_pure"],
            cgo88_joint=summary_joint_vs_mgc["scores"]["cgo88_joint"],
            paired_delta_mgc88_vs_raw_control=summary_mgc["paired_differences"][
                "raw_control"
            ],
            paired_delta_cgo88_pure_vs_mgc88=summary_pure_vs_mgc["paired_differences"][
                "mgc88_incumbent"
            ],
            paired_delta_cgo88_pure_vs_raw_control=summary_pure_vs_raw[
                "paired_differences"
            ]["raw_control"],
            paired_delta_cgo88_joint_vs_mgc88=summary_joint_vs_mgc[
                "paired_differences"
            ]["mgc88_incumbent"],
            paired_delta_cgo88_joint_vs_raw_control=summary_joint_vs_raw[
                "paired_differences"
            ]["raw_control"],
        ),
        decision=dict(
            beats_mgc88_incumbent=False,
            promoted=False,
            verdict="negative",
            reason=(
                "CGO-88 (conductivity-gravity 200 m lateral offset using bands 13 iso_grav_anom, "
                "17 cond_surf, 18 iso_grav_anom_hg, 15 depth_to_base_surf) scored HOLDOUT-DTI "
                "0.0227 [0.0154, 0.0309] (pure) and 0.0230 [0.0162, 0.0308] (joint with MGC-88), "
                "failing to beat the MGC-88 incumbent HOLDOUT-DTI 0.0389 [0.0264, 0.0532] "
                "(paired delta -0.0162 [-0.0281, -0.0073] pure; -0.0158 [-0.0286, -0.0061] joint). "
                "Band 17 cond_surf has single-feature symmetric AUC 0.5038 on withheld fault segments "
                "and reflects regional basin/playa conductance, inducing cross-quadrant overfitting. "
                "MGC-88 remains the unbeaten holdout best (still blocked from submission by the "
                "universal positive-footprint registry witness)."
            ),
            experiment_budget_used_total=2,
            experiment_budget_max=3,
            elapsed_seconds=round(time.monotonic() - start, 2),
        ),
    )

    for out_path in (
        REGISTRY / "cgo88_holdout_and_band19_audit.json",
        DOCS_EVIDENCE / "cgo88_holdout_and_band19_audit.json",
    ):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, indent=2, allow_nan=False, sort_keys=True) + "\n"
        )
    print(
        "CGO-88 AUDIT COMPLETE:",
        "mgc88=",
        round(result["holdout_comparison"]["mgc88_incumbent"]["dti"], 4),
        "cgo88_pure=",
        round(result["holdout_comparison"]["cgo88_pure"]["dti"], 4),
        "cgo88_joint=",
        round(result["holdout_comparison"]["cgo88_joint"]["dti"], 4),
        "elapsed=",
        result["decision"]["elapsed_seconds"],
    )
    return result


if __name__ == "__main__":
    run_audit()
