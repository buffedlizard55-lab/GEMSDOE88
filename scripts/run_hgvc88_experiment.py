#!/usr/bin/env python3
"""Run the preregistered H88-HGVC 3-experiment holdout suite and emit the validated GeoTIFF.

Lane: H88-HGVC — Hydrothermal Geochemical-Outflow Up-Dip Advection, Pluvial-Tufa-Decontaminated
Sinter & Perched Clay-Cap Conduit Tensor (20 zero-catalogue channels in ``src/gems88/hgvc.py``
paired with the shared 44-channel ``src/gems88/physics.py`` stack).

Reuses unmodified ``vendor/gems57/`` (``holdout.buffered_component_draw``, ``evaluate_holdout``,
``submission_writer``, ``uniqueness``, ``validate``, ``gates``) and ``src/gems88/`` (``adhr``,
``gate``, ``portal_writer``, ``physics``, ``registry_paths``).
Corrects IR-88-110 (B12 ``det_elev`` scarp input) and IR-88-111 (explicit ``trace_segments_utm11.csv``),
and expands the uniqueness registry with live 2026-10-24 HEAD rasters from GEMSDOE86..92 (IR-88-113).
"""
from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import (  # noqa: E402
    evaluate_holdout,
    gates as g57gates,
    grid as grid_mod,
    holdout,
    submission_writer,
    uniqueness,
    validate as g57validate,
)
from gems88 import adhr, edge, gate, hgvc, physics, portal_writer  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

BLOCK_SIDE = 200
BOOT_DRAWS = 2000
BOOT_SEED = 520888
CANDIDATE_ARM = "exp03_hgvc_poe_conduit"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_single_feature_canary(
    zero_cat_groups: list[tuple[np.ndarray, list[str], str]],
    vis_by_seed: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]],
    g,
    folds_by_seed,
) -> dict:
    """Test every input feature alone on held-out positives; symmetric AUC > 0.90 = leakage."""
    ys, xs = np.nonzero(g.footprint)
    rows = []
    max_sym = 0.0
    max_feat = ""
    for seed, folds in folds_by_seed:
        hidden = folds[0]["hidden_all"][ys, xs]
        vis = folds[0]["visible"][ys, xs]
        pos = np.flatnonzero(hidden)
        neg_pool = np.flatnonzero(~hidden & ~vis)
        rng = np.random.default_rng(8800 + seed)
        neg = rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), dtype=np.int32), np.zeros(len(neg), dtype=np.int32)])
        tr_tru_seed = np.logical_or.reduce([folds[j]["truth"] for j in range(1, 4)])
        wlaw_c = hgvc.damagezone_envelope.fit_width_law(
            vis_by_seed[seed][2], vis_by_seed[seed][1], tr_tru_seed[ys, xs], quantile=0.90, l0_px=40.0
        )
        dow_c = (vis_by_seed[seed][1] / np.maximum(wlaw_c.half_width(vis_by_seed[seed][2]), 1e-6)).astype(np.float32)[:, None]
        seed_groups = list(zero_cat_groups) + [
            (vis_by_seed[seed][0], list(adhr.VIS_STRUCT_FEATURES[:22]), "VIS-22"),
            (dow_c, [adhr.VIS_STRUCT_FEATURES[22]], "VIS-22"),
        ]
        for X, names, group in seed_groups:
            for j, name in enumerate(names):
                vals = np.asarray(X[sel, j], dtype=np.float64)
                auc = float(roc_auc_score(y, vals))
                sym = max(auc, 1.0 - auc)
                if sym > max_sym:
                    max_sym = sym
                    max_feat = f"{name} (seed={seed})"
                if seed == 20:
                    rows.append(
                        {
                            "feature": name,
                            "group": group,
                            "roc_auc": round(auc, 6),
                            "symmetric_auc": round(sym, 6),
                        }
                    )
    rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
    passed = bool(max_sym <= 0.90)
    if not passed:
        raise RuntimeError(f"STOP: single-feature leakage canary tripped: {max_feat} = {max_sym:.6f} > 0.90")
    total_tested = int(sum(len(names) for _, names, _ in zero_cat_groups) + len(adhr.VIS_STRUCT_FEATURES))
    return {
        "passed": passed,
        "threshold": 0.90,
        "features_tested": total_tested,
        "zero_catalogue_features_tested": int(sum(len(names) for _, names, _ in zero_cat_groups)),
        "fold_visible_features_tested": len(adhr.VIS_STRUCT_FEATURES),
        "max_symmetric_auc": round(max_sym, 6),
        "max_feature": max_feat,
        "max_zero_catalogue_symmetric_auc": round(
            max(r["symmetric_auc"] for r in rows if r["group"] != "VIS-22"), 6
        ),
        "top15_all_features": rows[:15],
        "hgvc20_features": [r for r in rows if r["group"] == "HGVC-20"],
    }


def collect_full_registry(root: Path, exclude_substr: tuple[str, ...] = ("gems88-hgvc",)) -> list[tuple[str, Path]]:
    """Collect all pinned registry + fleet + sibling + concurrent GEMSDOE88 + live HEAD sibling rasters."""
    base = list(registry_list(root, exclude=exclude_substr))
    seen_paths = {p.resolve() for _, p in base}
    seen_shas = {sha256_file(p) for _, p in base}

    head_dir = root / "data/siblings_head"
    if head_dir.is_dir():
        for p in sorted(head_dir.glob("*.tif")):
            rp = p.resolve()
            if rp in seen_paths or any(ex and ex in p.name for ex in exclude_substr):
                continue
            s = sha256_file(p)
            if s in seen_shas:
                continue
            seen_paths.add(rp)
            seen_shas.add(s)
            base.append((f"sibling_head_20261024:{p.name}", p))
    return base


def main() -> int:
    t0 = time.monotonic()
    prereg_path = ROOT / "registry/preregistration_hgvc88.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("Preregistration must be frozen before running experiments")

    print("[1/7] Loading competition grid & building/loading 44-ch physics + 20-ch HGVC memmaps...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    shared_cache = ROOT / ".cache/gems88"
    hgvc_cache = ROOT / ".cache/gems88_hgvc"
    shared_cache.mkdir(parents=True, exist_ok=True)
    hgvc_cache.mkdir(parents=True, exist_ok=True)

    X_phys, band_tags, _ = physics.build_or_load_physics_memmap(ROOT, g, shared_cache)
    X_hgvc, hgvc_meta = hgvc.build_or_load_hgvc_memmap(ROOT, g, hgvc_cache)
    X_phys_diff = hgvc.ColumnSubsetView(X_phys, hgvc.PHYS_DIFF_INDICES)
    print(
        f"      HGVC-20 ready: cold_wells_rejected={hgvc_meta['cold_wells_rejected']}, "
        f"sinter_pts={hgvc_meta['hydrothermal_sinter_travertine_points']}, "
        f"tufa_mimics_separated={hgvc_meta['pluvial_tufa_mimic_points_separated']}",
        flush=True,
    )

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        if src.tags(12).get("band_name") != "det_elev":
            raise ValueError("Band 12 must be det_elev (IR-88-110 guard)")
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, hgvc_cache)
    del det_elev
    gc.collect()

    sense_csv = ROOT / "data/external/trace_segments_utm11.csv"
    if not sense_csv.is_file():
        raise FileNotFoundError(f"Missing explicit trace_segments_utm11.csv: {sense_csv}")
    sense_src = adhr.build_sense_raster(sense_csv, g)

    folds_by_seed: list[tuple[int, list[dict]]] = []
    vis_by_seed: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))
        # Visible catalogue is identical across all 4 quadrant folds of a seed draw
        vis_by_seed[seed] = adhr.compute_visible_struct_fp(
            g, folds[0]["visible"], sense_src, scarp_fields, hgvc_cache, f"seed{seed}"
        )

    print("[2/7] Running single-feature leakage canary (64 zero-catalogue + 23 fold-visible features) & quadrant-scramble invariance...", flush=True)
    canary_path = ROOT / "evidence/hgvc88_canaries.json"
    if canary_path.is_file():
        canary = json.loads(canary_path.read_text(encoding="utf-8"))
        scramble_ok = bool(canary.get("zero_test_quadrant_leakage_scramble_equal"))
    else:
        canary = None
        scramble_ok = False
    if not (canary and canary.get("features_tested") == 87 and canary.get("passed") and scramble_ok):
        canary = run_single_feature_canary(
            [
                (X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
                (X_hgvc, list(hgvc.HGVC_FEATURES), "HGVC-20"),
            ],
            vis_by_seed,
            g,
            folds_by_seed,
        )
        f0_s20 = folds_by_seed[0][1][0]
        tr_reg_0 = np.logical_or.reduce([folds_by_seed[0][1][j]["region"] for j in range(1, 4)])
        tr_tru_0 = np.logical_or.reduce([folds_by_seed[0][1][j]["truth"] for j in range(1, 4)])
        scramble_ok = hgvc.verify_zero_test_quadrant_leakage(
            g,
            X_phys_diff,
            X_hgvc,
            vis_by_seed[20][0],
            vis_by_seed[20][1],
            vis_by_seed[20][2],
            f0_s20["visible"],
            tr_reg_0,
            tr_tru_0,
            f0_s20["region"],
        )
        if not scramble_ok:
            raise RuntimeError("STOP: test-quadrant scramble invariance check failed!")
        canary["zero_test_quadrant_leakage_scramble_equal"] = True
        write_json(canary_path, canary)
    print(
        f"      PASS {canary['features_tested']}/{canary['features_tested']} features <= 0.90 "
        f"(max={canary['max_symmetric_auc']:.6f} on {canary['max_feature']}); scramble_equal={scramble_ok}",
        flush=True,
    )

    print("[3/7] Running 8-fold buffered whole-component holdout (2 controls + 3 preregistered experiments)...", flush=True)
    holdout_cache_path = ROOT / "evidence/hgvc88_holdout_20261024.json"
    if holdout_cache_path.is_file() and "--recompute-holdout" not in sys.argv:
        holdout_payload = json.loads(holdout_cache_path.read_text(encoding="utf-8"))
        pooled_overall = holdout_payload["pooled_overall"]
        pooled_far10 = holdout_payload["pooled_far_gt10px"]
        pooled_blind25 = holdout_payload["pooled_blind_gt25px"]
        fold_rows = holdout_payload["folds"]
        folds_won = int(holdout_payload["folds_won_vs_adhr"])
        ov_cand = pooled_overall["scores"][CANDIDATE_ARM]
        fr_cand = pooled_far10["scores"][CANDIDATE_ARM]
        bl_cand = pooled_blind25["scores"][CANDIDATE_ARM]
        delta_ov_adhr = pooled_overall["paired_differences"]["h88_adhr_incumbent"]
        delta_fr_adhr = pooled_far10["paired_differences"]["h88_adhr_incumbent"]
        delta_bl_adhr = pooled_blind25["paired_differences"]["h88_adhr_incumbent"]
        print(
            f"      LOADED CACHED 8-FOLD HOLDOUT ({CANDIDATE_ARM}): overall={ov_cand['dti']:.6f} CI={ov_cand['ci95']} "
            f"(delta={delta_ov_adhr['delta']:+.6f} CI={delta_ov_adhr['ci95']}, {folds_won}/8 folds won)",
            flush=True,
        )
    else:
        arms = (
            "phys44_zero_cat",
            "h88_adhr_incumbent",
            "exp01_hgvc_zero_cat",
            "exp02_hgvc_single_joint",
            "exp03_hgvc_poe_conduit",
        )
        terms_overall = {a: None for a in arms}
        terms_far10 = {a: None for a in arms}
        terms_blind25 = {a: None for a in arms}
        fold_rows = []

        for seed, folds in folds_by_seed:
            X_vis22, d_vis_fp, comp_len_fp = vis_by_seed[seed]
            d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
            for i, fold in enumerate(folds):
                qname = str(fold["name"])
                tag = f"seed{seed}_f{i}_{qname}"
                train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
                train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
                test_region = fold["region"]

                res = hgvc.predict_hgvc_all_arms_fold(
                    g,
                    X_phys,
                    X_phys_diff,
                    X_hgvc,
                    X_vis22,
                    d_vis_fp,
                    comp_len_fp,
                    fold["visible"],
                    train_regions,
                    train_truth,
                    test_region,
                    seed=seed * 10 + i,
                    cache_dir=hgvc_cache,
                    fold_tag=tag,
                )

                far_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
                far_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
                far_fold = {**fold, "truth": far_truth, "region": far_valid, "masked_known": np.zeros_like(far_valid)}

                blind_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
                blind_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
                blind_fold = {**fold, "truth": blind_truth, "region": blind_valid, "masked_known": np.zeros_like(blind_valid)}

                row = {
                    "seed": seed,
                    "fold": qname,
                    "withheld_positive_pixels": int((fold["truth"] & test_region & ~fold["masked_known"]).sum()),
                    "far_withheld_positive_pixels": int(far_truth.sum()),
                    "blind_withheld_positive_pixels": int(blind_truth.sum()),
                }
                for arm in arms:
                    emitted_arm, _, meta_arm = res[arm]
                    sc_ov, bt_ov = evaluate_holdout.evaluate(emitted_arm, fold, g.footprint, block_side=BLOCK_SIDE)
                    sc_fr, bt_fr = evaluate_holdout.evaluate(emitted_arm, far_fold, g.footprint, block_side=BLOCK_SIDE)
                    sc_bl, bt_bl = evaluate_holdout.evaluate(emitted_arm, blind_fold, g.footprint, block_side=BLOCK_SIDE)
                    terms_overall[arm] = bt_ov if terms_overall[arm] is None else terms_overall[arm] + bt_ov
                    terms_far10[arm] = bt_fr if terms_far10[arm] is None else terms_far10[arm] + bt_fr
                    terms_blind25[arm] = bt_bl if terms_blind25[arm] is None else terms_blind25[arm] + bt_bl
                    row[arm] = {
                        "evidence_class": "HOLDOUT-DTI",
                        "evaluator_version": evaluate_holdout.VERSION,
                        "overall_dti": round(float(sc_ov["dti"]), 6),
                        "far_gt10px_dti": round(float(sc_fr["dti"]), 6),
                        "blind_gt25px_dti": round(float(sc_bl["dti"]), 6),
                        "emitted_dots": int(meta_arm["n_dots"]),
                    }
                fold_rows.append(row)
                print(
                    f"      [seed={seed} {qname}] ADHR={row['h88_adhr_incumbent']['overall_dti']:.6f} | "
                    f"Exp01={row['exp01_hgvc_zero_cat']['overall_dti']:.6f} | "
                    f"Exp02={row['exp02_hgvc_single_joint']['overall_dti']:.6f} | "
                    f"Exp03={row[CANDIDATE_ARM]['overall_dti']:.6f} "
                    f"(far={row[CANDIDATE_ARM]['far_gt10px_dti']:.6f}, blind={row[CANDIDATE_ARM]['blind_gt25px_dti']:.6f})",
                    flush=True,
                )

        pooled_overall = evaluate_holdout.pooled_summary(
            terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=CANDIDATE_ARM
        )
        pooled_far10 = evaluate_holdout.pooled_summary(
            terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=CANDIDATE_ARM
        )
        pooled_blind25 = evaluate_holdout.pooled_summary(
            terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=CANDIDATE_ARM
        )

        ov_cand = pooled_overall["scores"][CANDIDATE_ARM]
        fr_cand = pooled_far10["scores"][CANDIDATE_ARM]
        bl_cand = pooled_blind25["scores"][CANDIDATE_ARM]
        delta_ov_adhr = pooled_overall["paired_differences"]["h88_adhr_incumbent"]
        delta_fr_adhr = pooled_far10["paired_differences"]["h88_adhr_incumbent"]
        delta_bl_adhr = pooled_blind25["paired_differences"]["h88_adhr_incumbent"]
        folds_won = sum(
            1 for r in fold_rows if r[CANDIDATE_ARM]["overall_dti"] > r["h88_adhr_incumbent"]["overall_dti"]
        )
        print(
            f"      POOLED HOLDOUT-DTI ({CANDIDATE_ARM}): overall={ov_cand['dti']:.6f} CI={ov_cand['ci95']} "
            f"(paired delta vs ADHR={delta_ov_adhr['delta']:+.6f} CI={delta_ov_adhr['ci95']}, {folds_won}/8 folds won); "
            f"far={fr_cand['dti']:.6f} (delta={delta_fr_adhr['delta']:+.6f}); "
            f"blind={bl_cand['dti']:.6f} (delta={delta_bl_adhr['delta']:+.6f})",
            flush=True,
        )

        holdout_payload = {
            "schema_version": "gems88-hgvc88-holdout-v1",
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "preregistration_id": prereg["preregistration_id"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21],
            "n_folds": 8,
            "bootstrap_draws": BOOT_DRAWS,
            "spatial_block_m": BLOCK_SIDE * 100.0,
            "folds_won_vs_adhr": folds_won,
            "zero_leakage_quadrant_scramble_equal": True,
            "canary": canary,
            "pooled_overall": pooled_overall,
            "pooled_far_gt10px": pooled_far10,
            "pooled_blind_gt25px": pooled_blind25,
            "stored_baselines": {
                "h88_adhr_stored": {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": "gems57-pooled-hide-v2",
                    "withheld_positive_pixels": 22893,
                    "overall_dti": 0.189634,
                    "far_gt10px_dti": 0.114780,
                    "blind_gt25px_dti": 0.065263,
                },
                "h88_tdkl_stored": {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": "gems57-pooled-hide-v2",
                    "withheld_positive_pixels": 22893,
                    "overall_dti": 0.196237,
                    "far_gt10px_dti": 0.124175,
                    "blind_gt25px_dti": 0.076881,
                    "note": "Blocked post-merge by 0.7623 > 0.70 3-px overlap vs GTHC-88 and B14 tmi scarp input (IR-88-106/110).",
                },
                "h88_vess_stored": {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": "gems57-pooled-hide-v2",
                    "withheld_positive_pixels": 22893,
                    "overall_dti": 0.200941,
                    "far_gt10px_dti": 0.131922,
                    "blind_gt25px_dti": 0.090449,
                    "note": "Blocked as lane duplicate by 0.8455 > 0.70 3-px overlap vs H88-TDKL (IR-88-112).",
                },
                "h33_owner_claim": {
                    "evidence_class": "USER-REPORTED (no portal receipt in repo)",
                    "submission_id": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                    "reported_public_dti": 0.2778,
                    "leaderboard_top_public_dti_snapshot_20261024": 0.4413,
                },
            },
            "folds": fold_rows,
        }
        write_json(holdout_cache_path, holdout_payload)
        write_json(ROOT / "docs/evidence/hgvc88_holdout_20261024.json", holdout_payload)
    if "--stop-after-holdout" in sys.argv:
        print("      Holdout stage complete (--stop-after-holdout).", flush=True)
        return 0

    print("[4/7] Collecting complete registry (pinned + fleet + concurrent GEMSDOE88 + live GEMSDOE86..92 HEAD)...", flush=True)
    for old_f in list((ROOT / "docs/downloads").glob("gems88-hgvc88-*")) + list(
        (ROOT / "submissions").glob("gems88-hgvc88-*")
    ):
        old_f.unlink(missing_ok=True)
    reg_entries = collect_full_registry(ROOT, exclude_substr=("gems88-hgvc88",))
    print(f"      Registry size for uniqueness check: {len(reg_entries)} rasters", flush=True)

    surface_check_holder: dict[str, float | str] = {}

    def _preplacement_surface_gate(p_surface: np.ndarray) -> None:
        rk_s = gate.rank_vec(p_surface, g.footprint)
        max_rho = 0.0
        max_lbl = ""
        seen_k = set()
        for lbl, rpath in reg_entries:
            vals = gate.read_values(rpath, g.footprint)
            key = gate.sha256_bytes(np.packbits(vals > 0).tobytes()) + ("D" if gate.is_dense(vals, g.footprint) else "S")
            if key in seen_k:
                continue
            seen_k.add(key)
            rho = abs(gate._pearson(rk_s, gate.rank_vec(vals, g.footprint)))
            if rho > max_rho:
                max_rho = rho
                max_lbl = lbl
        surface_check_holder["max_abs_spearman"] = round(float(max_rho), 6)
        surface_check_holder["max_rho_label"] = max_lbl
        print(f"      Pre-placement surface max |Spearman rho| = {max_rho:.6f} vs {max_lbl} (limit 0.90)", flush=True)
        if max_rho > 0.90:
            raise RuntimeError(f"STOP DUPLICATE BEFORE PLACEMENT: surface |rho| = {max_rho:.6f} > 0.90 vs {max_lbl}")

    print("[5/7] Fitting 4-quadrant out-of-fold production heads & allocating H33-parity kernel-spaced dots...", flush=True)
    prod_emitted, prod_surface, prod_meta = hgvc.fit_and_emit_production_hgvc(
        g,
        X_phys,
        X_phys_diff,
        X_hgvc,
        folds_by_seed,
        sense_src,
        scarp_fields,
        vis_by_seed,
        hgvc_cache,
        near_budget=prereg["production_design"]["near_stratum"]["budget"],
        far_budget=prereg["production_design"]["far_stratum"]["budget"],
        near_spacing_px=prereg["production_design"]["near_stratum"]["min_spacing_px"],
        far_spacing_px=prereg["production_design"]["far_stratum"]["min_spacing_px"],
        preplacement_gate=_preplacement_surface_gate,
    )
    print(
        f"      Emitted {prod_meta['n_dots']} discrete {{0,1}} dots: "
        f"share_le2={prod_meta['share_le2']:.4f}, share_gt25={prod_meta['share_gt25']:.4f}, "
        f"median_d_cat={prod_meta['median_d_cat_px']:.2f} px",
        flush=True,
    )

    sample_path = ROOT / "data/bridge/sample_submission.tif"
    d_cat_grid = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_prof = gate.fingerprint(prod_emitted > 0.5, d_cat_grid)
    fp_pass = gate.fingerprint_screen(fp_prof)

    # First verify via shared vendor submission_writer in temporary directory, then write sample-parity LZW strip GeoTIFF
    with tempfile.TemporaryDirectory() as tmpd:
        tmp_dir = Path(tmpd)
        sw_tif = tmp_dir / "sw_check.tif"
        sw_receipt = submission_writer.write_submission(
            sw_tif,
            prod_emitted,
            sample_path,
            g.footprint,
            name="GEMSDOE88-HGVC88-SWCHECK",
            note="HGVC88 shared submission_writer preflight check",
            catalogue=g.catalogue,
        )
        assert sw_receipt["validator"]["all_checks_passed"] is True
        lzw_tmp = tmp_dir / "portal_lzw.tif"
        portal_writer.write_portal_tif(lzw_tmp, prod_emitted, sample_path, g.footprint)
        prelim_sha = sha256_file(lzw_tmp)
        hash8 = prelim_sha[:8]

        print("[6/7] Running final 330+-raster uniqueness gate (like-for-like + binding literal witness)...", flush=True)
        uq = gate.uniqueness_report(lzw_tmp, reg_entries, g.footprint, surface=prod_surface)

        # Explicitly measure literal 17GEMSDOE saturation certificate via vendor/gems57/uniqueness.py
        witness_path = ROOT / "data/registry/dense_17gemdoe.tif"
        with rasterio.open(sample_path) as ref_ds:
            expected_grid = (ref_ds.shape, ref_ds.crs, ref_ds.transform)
        sat_cert = uniqueness.saturation_certificate(
            witness_path, g.footprint, g.catalogue, expected_grid=expected_grid
        )
        with rasterio.open(witness_path) as w_ds:
            witness_arr = w_ds.read(1)
        literal_witness_overlap = float(
            uniqueness.dot_overlap(prod_emitted, (np.isfinite(witness_arr) & (witness_arr > 0)) & g.footprint, 3)
        )

        print(
            f"      Like-for-like unique={uq['unique_like_for_like']} across {uq['registry_rasters']} rasters "
            f"({uq['distinct_dot_sets']} distinct dot sets): "
            f"worst 3-px overlap = {uq['worst_like_for_like_overlap']['value']:.6f} "
            f"({uq['worst_like_for_like_overlap']['label']}), "
            f"worst |rho| = {uq['worst_abs_rho']['value']:.6f}; "
            f"binding literal witness = {literal_witness_overlap:.6f}",
            flush=True,
        )

        # Per IR-88-86, literal 17GEMSDOE witness = 1.0000 > 0.70 holds automated ok_to_submit False
        stem = f"gems88-hgvc88-updip-sinter-conduit-{prod_meta['n_dots']}-20261024-{hash8}-zeros-DO-NOT-SUBMIT"
        sub_name = f"GEMSDOE88-HGVC88-{hash8.upper()}"
        sub_note = (
            f"HGVC88 87ch hydrothermal up-dip+sinter PoE {prod_meta['n_dots']}d; "
            f"HOLDOUT-DTI {ov_cand['dti']:.4f} far {fr_cand['dti']:.4f} blind {bl_cand['dti']:.4f}; UNSCORED"
        )
        assert 0 < len(sub_name) <= 140 and 0 < len(sub_note) <= 140, (len(sub_name), len(sub_note))

        dl_tif = ROOT / "docs/downloads" / f"{stem}.tif"
        dl_zip = ROOT / "docs/downloads" / f"{stem}.zip"
        dl_receipt = ROOT / "docs/downloads" / f"{stem}.json"
        dl_audit = ROOT / "docs/downloads" / f"{stem}.format-audit.json"
        sub_tif = ROOT / "submissions" / f"{stem}.tif"
        sub_zip = ROOT / "submissions" / f"{stem}.zip"
        sub_receipt = ROOT / "submissions" / f"{stem}.json"

        shutil.copy2(lzw_tmp, dl_tif)
        portal_writer.write_single_member_zip(dl_zip, dl_tif)
        os.chmod(dl_tif, 0o644)
        os.chmod(dl_zip, 0o644)
        shutil.copy2(dl_tif, sub_tif)
        shutil.copy2(dl_zip, sub_zip)
        os.chmod(sub_tif, 0o644)
        os.chmod(sub_zip, 0o644)

    print("[7/7] Re-opening on-disk .tif and .zip for independent portal-parity & multi-decoder audit...", flush=True)
    portal_tif = gate.portal_validate(dl_tif, sample_path, g.footprint)
    portal_zip = gate.portal_validate(dl_zip, sample_path, g.footprint)
    indep_audit = validate_artifact(dl_tif, sample_path)
    g57_fmt = g57gates.format_report(dl_tif, sample_path, footprint=g.footprint)
    g57_val = g57validate.validate(dl_tif, g.footprint, g.catalogue)
    g57validate.assert_submittable(g57_val)

    if not (
        portal_tif["ok"]
        and portal_zip["ok"]
        and portal_tif["layout_parity_with_sample"]
        and indep_audit["ok"]
        and g57_fmt["ok"]
        and g57_val["all_checks_passed"]
        and portal_tif["array_sha256"] == portal_zip["array_sha256"]
    ):
        raise RuntimeError(f"Saved format audit failed: tif={portal_tif['problems']} zip={portal_zip['problems']}")

    tif_sha = sha256_file(dl_tif)
    zip_sha = sha256_file(dl_zip)

    adhr_recomp = float(pooled_overall["scores"]["h88_adhr_incumbent"]["dti"])
    adhr_stored = 0.189634
    beats_holdout_bar = bool(
        ov_cand["dti"] > adhr_recomp
        and ov_cand["dti"] > adhr_stored
        and delta_ov_adhr["ci95"][0] > 0.0
    )

    used_names: set[str] = set()
    for p_rc in (ROOT / "registry").glob("*.json"):
        if "hgvc" in p_rc.name:
            continue
        try:
            d = json.loads(p_rc.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("submission_name"), str):
                used_names.add(d["submission_name"])
        except Exception:
            pass

    uq_for_decide = {
        **uq,
        "registry_complete": bool(uq["missing"] == 0 and uq["registry_rasters"] >= 300),
        "surface_checked": True,
    }
    v3_raw = gate.decide(
        portal=portal_tif,
        uniqueness=uq_for_decide,
        canary_passed=bool(canary["passed"] and scramble_ok),
        holdout_beats_bar=bool(beats_holdout_bar and fp_pass),
        name=sub_name,
        note=sub_note,
        used_names=used_names,
        receipt_sha_matches=True,
    )
    all_5_discriminating_gates_pass = bool(
        portal_tif["ok"]
        and portal_tif["layout_parity_with_sample"]
        and canary["passed"]
        and scramble_ok
        and beats_holdout_bar
        and fp_pass
        and uq["unique_like_for_like"]
        and uq["worst_like_for_like_overlap"]["value"] <= 0.70
        and uq["worst_abs_rho"]["value"] <= 0.90
        and surface_check_holder["max_abs_spearman"] <= 0.90
    )
    # Enforce binding literal rule (IR-88-86 / IR-88-113): literal 17GEMSDOE dense witness = 1.0 > 0.70 keeps ok_to_submit False
    blocking_reasons = list(v3_raw["blocking_reasons"])
    if (not uq["unique_literal"] or literal_witness_overlap > 0.70) and not any(
        "literal" in r.lower() for r in blocking_reasons
    ):
        blocking_reasons.append(
            f"UNIQUENESS (binding literal rule, IR-88-86): forward 3-px overlap = {literal_witness_overlap:.4f} > 0.70 "
            "against full-footprint continuous 17GEMSDOE witness (5,167,373/5,167,373 footprint pixels > 0)"
        )
    ok_to_submit = bool(all_5_discriminating_gates_pass and uq["unique_literal"] and literal_witness_overlap <= 0.70)
    verdict = "promote" if ok_to_submit else "negative"

    # Top-10 closest rasters by like-for-like 3-px overlap for transparent audit
    ok_uq_rows = [r for r in uq["rows"] if "error" not in r and "duplicate_of" not in r]
    top10_overlap = sorted(ok_uq_rows, key=lambda r: r["like_for_like_overlap_3px"], reverse=True)[:10]
    concurrent_gems88 = {
        r["label"]: round(float(r["like_for_like_overlap_3px"]), 6)
        for r in uq["rows"]
        if "error" not in r and str(r["label"]).startswith("GEMSDOE88")
    }
    sibling_head_summary = {
        r["label"]: round(float(r["like_for_like_overlap_3px"]), 6)
        for r in uq["rows"]
        if "error" not in r and str(r["label"]).startswith("sibling_head_20261024:")
    }

    uq_slim = {
        "policy": uq["policy"],
        "candidate": f"docs/downloads/{dl_tif.name}",
        "candidate_sha256": tif_sha,
        "candidate_dots": uq["candidate_dots"],
        "registry_rasters_checked": uq["registry_rasters"],
        "distinct_dot_sets_checked": uq["distinct_dot_sets"],
        "missing": uq["missing"],
        "surface_preplacement_max_abs_spearman": surface_check_holder["max_abs_spearman"],
        "surface_preplacement_max_label": surface_check_holder["max_rho_label"],
        "worst_like_for_like_overlap": uq["worst_like_for_like_overlap"],
        "worst_abs_rho": uq["worst_abs_rho"],
        "like_for_like_blockers": uq["like_for_like_blockers"],
        "unique_like_for_like": uq["unique_like_for_like"],
        "literal_all_positive_witness_overlap_3px": literal_witness_overlap,
        "saturation_certificate": sat_cert,
        "unique_literal": uq["unique_literal"],
        "vacuity_witness": uq["vacuity_witness"],
        "top10_like_for_like_overlaps": top10_overlap,
        "concurrent_gems88_overlaps_3px": concurrent_gems88,
        "live_head_20261024_sibling_count": len(sibling_head_summary),
        "live_head_20261024_max_overlap_3px": max(sibling_head_summary.values()) if sibling_head_summary else 0.0,
    }
    write_json(ROOT / "evidence/hgvc88_uniqueness.json", uq_slim)

    format_audit = {
        "portal_tif": portal_tif,
        "portal_zip": portal_zip,
        "independent_validate_artifact": indep_audit,
        "shared_gates_format_report": g57_fmt,
        "shared_validate": g57_val,
    }
    write_json(dl_audit, format_audit)

    writer_meta = {
        "file": dl_tif.name,
        "zip_file": dl_zip.name,
        "sha256": tif_sha,
        "zip_sha256": zip_sha,
        "submission_name": sub_name,
        "submission_note": sub_note,
        "note_length": len(sub_note),
        "positive_pixels": int(prod_meta["n_dots"]),
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "all_5_discriminating_gates_pass": all_5_discriminating_gates_pass,
        "verdict": verdict,
        "weekly_slots_spent": 0,
        "organizer_confirmed_score": None,
    }
    write_json(dl_receipt, writer_meta)
    write_json(sub_receipt, writer_meta)

    elapsed_s = round(time.monotonic() - t0, 2)

    gate_v3_doc = {
        "schema": "gems88.hgvc88.gate_v3.v1",
        "policy": gate.POLICY_VERSION,
        "binding_literal_policy": "IR-88-86-literal-all-registry-v1",
        "name": stem,
        "submission_name": sub_name,
        "submission_note": sub_note,
        "candidate": {
            "tif": f"docs/downloads/{dl_tif.name}",
            "zip": f"docs/downloads/{dl_zip.name}",
            "sha256": tif_sha,
            "zip_sha256": zip_sha,
            "dots": int(prod_meta["n_dots"]),
        },
        "sha256": tif_sha,
        "zip_sha256": zip_sha,
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "all_5_discriminating_gates_pass": all_5_discriminating_gates_pass,
        "verdict": verdict,
        "label": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT (held only by literal 17GEMSDOE dense witness + human selector)"
        if all_5_discriminating_gates_pass and not ok_to_submit
        else v3_raw["label"],
        "blocking_reasons": blocking_reasons,
        "portal_values_and_grid_ok": bool(portal_tif["ok"] and portal_zip["ok"]),
        "portal_layout_parity_with_sample": bool(portal_tif["layout_parity_with_sample"]),
        "leakage_canary_pass": bool(canary["passed"] and scramble_ok),
        "fingerprint": fp_prof,
        "fingerprint_screen_pass": fp_pass,
        "holdout_comparison": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "withheld_positives": int(ov_cand["withheld_positive_pixels"]),
            "candidate_dti": float(ov_cand["dti"]),
            "candidate_ci95": ov_cand["ci95"],
            "far_gt10px_dti": float(fr_cand["dti"]),
            "far_gt10px_ci95": fr_cand["ci95"],
            "blind_gt25px_dti": float(bl_cand["dti"]),
            "blind_gt25px_ci95": bl_cand["ci95"],
            "adhr_incumbent_recomputed_dti": adhr_recomp,
            "adhr_incumbent_stored_dti": adhr_stored,
            "paired_delta_vs_adhr": delta_ov_adhr,
            "folds_won_vs_adhr": folds_won,
            "beats_both_bars_with_positive_ci95": beats_holdout_bar,
        },
        "uniqueness": {
            "registry_rasters_checked": uq["registry_rasters"],
            "distinct_dot_sets_checked": uq["distinct_dot_sets"],
            "surface_preplacement_max_abs_spearman": surface_check_holder["max_abs_spearman"],
            "worst_like_for_like_overlap": uq["worst_like_for_like_overlap"],
            "worst_abs_rho": uq["worst_abs_rho"],
            "unique_like_for_like": uq["unique_like_for_like"],
            "literal_all_positive_witness_overlap_3px": literal_witness_overlap,
            "unique_literal": uq["unique_literal"],
        },
        "weekly_slots_spent": 0,
        "organizer_confirmed_score": None,
    }
    write_json(ROOT / "registry/hgvc88_gate_v3.json", gate_v3_doc)
    write_json(ROOT / "docs/data/hgvc88_gate_v3.json", gate_v3_doc)

    run_card = {
        "schema": "gems88.hgvc88.run_card.v1",
        "run_id": f"GEMSDOE88-HGVC88-20261024-{hash8}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-HGVC",
        "preregistration_id": prereg["preregistration_id"],
        "hypothesis": prereg["hypothesis"],
        "mechanism": (
            "20 zero-catalogue HGVC hydrothermal/geochemical/shallow-probe/clay-cap/sinter/basement-decoupling "
            "channels (dist_known_fault_px stripped on read; pluvial tufa separated; cold irrigation wells rejected; "
            "B12 det_elev scarp input; explicit trace_segments_utm11.csv) + 44 shared physics channels -> "
            "distance-adaptive Log-Odds Product-of-Experts (base 44/67-ch + decontaminated HGVC 56/87-ch with "
            "blind-basin tail preservation) -> 4-quadrant OOF cross-fitting -> H33-parity kernel-spaced CELF "
            f"Dinkelbach allocation ({prod_meta['n_dots']} discrete {{0,1}} float32 dots, d_cat > 2.5 px, "
            f"share_gt25 = {prod_meta['share_gt25']:.4f})."
        ),
        "named_non_fault_mimic": prereg["named_non_fault_mimic"],
        "experiments_executed": 3,
        "experiment_budget_max": 3,
        "elapsed_seconds": elapsed_s,
        "wallclock_budget_seconds_max": 7200,
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21],
            "n_folds": 8,
            "withheld_positive_pixels": int(ov_cand["withheld_positive_pixels"]),
            "folds_won_vs_adhr": folds_won,
            "candidate_exp03": ov_cand,
            "exp01_zero_cat": pooled_overall["scores"]["exp01_hgvc_zero_cat"],
            "exp02_single_joint": pooled_overall["scores"]["exp02_hgvc_single_joint"],
            "control_phys44_zero_cat": pooled_overall["scores"]["phys44_zero_cat"],
            "control_h88_adhr_incumbent": pooled_overall["scores"]["h88_adhr_incumbent"],
            "far_gt10px": fr_cand,
            "blind_gt25px": bl_cand,
            "paired_delta_vs_adhr_overall": delta_ov_adhr,
            "paired_delta_vs_adhr_far_gt10px": delta_fr_adhr,
            "paired_delta_vs_adhr_blind_gt25px": delta_bl_adhr,
        },
        "leakage_canary": canary,
        "correlation_overlap_vs_registry": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "registry_rasters_checked": uq["registry_rasters"],
            "distinct_dot_sets_checked": uq["distinct_dot_sets"],
            "live_head_20261024_sibling_rasters_included": len(sibling_head_summary),
            "surface_preplacement_max_abs_spearman": surface_check_holder["max_abs_spearman"],
            "surface_preplacement_max_label": surface_check_holder["max_rho_label"],
            "final_max_abs_spearman": uq["worst_abs_rho"]["value"],
            "final_max_rho_label": uq["worst_abs_rho"]["label"],
            "final_worst_like_for_like_overlap_3px": uq["worst_like_for_like_overlap"],
            "unique_like_for_like": uq["unique_like_for_like"],
            "literal_all_positive_witness_overlap_3px": literal_witness_overlap,
            "unique_literal": uq["unique_literal"],
            "concurrent_gems88_max_overlap_3px": max(concurrent_gems88.values()) if concurrent_gems88 else 0.0,
            "live_head_20261024_sibling_max_overlap_3px": max(sibling_head_summary.values())
            if sibling_head_summary
            else 0.0,
        },
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "download": f"docs/downloads/{dl_tif.name}",
        "zip_download": f"docs/downloads/{dl_zip.name}",
        "repo_copy": f"submissions/{sub_tif.name}",
        "validator_output": {
            "portal_ok": bool(portal_tif["ok"] and portal_zip["ok"]),
            "layout_parity_with_sample": bool(portal_tif["layout_parity_with_sample"]),
            "no_nan_inside_footprint": bool(portal_tif["checks"]["footprint_cells_finite"]),
            "no_nan_anywhere": bool(portal_tif["checks"]["all_finite"]),
            "values_in_0_1": bool(portal_tif["checks"]["portal_range_check_nan_strict"]),
            "crs_match": bool(portal_tif["checks"]["crs_epsg_32611"]),
            "shape_match": bool(portal_tif["checks"]["shape_matches_sample"]),
            "transform_match": bool(portal_tif["checks"]["transform_matches_sample"]),
            "nodata_undeclared": bool(portal_tif["checks"]["nodata_undeclared"]),
            "outside_footprint_zero": bool(portal_tif["checks"]["outside_footprint_zero"]),
            "zero_on_mapped_catalogue": bool(g57_val["checks"]["zero_dots_on_mapped_catalogue"]),
            "second_decoder": portal_tif["second_decoder"],
            "positive_dots": int(prod_meta["n_dots"]),
            "fingerprint": fp_prof,
            "fingerprint_screen_pass": fp_pass,
            "raster_sha256": tif_sha,
            "zip_sha256": zip_sha,
        },
        "submission_name": sub_name,
        "submission_name_length": len(sub_name),
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "all_5_discriminating_gates_pass": all_5_discriminating_gates_pass,
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "verdict": verdict,
        "blocking_reasons": blocking_reasons,
        "organizer_confirmed_score": None,
        "weekly_slots_spent": 0,
    }
    write_json(ROOT / "registry/hgvc88_run_card.json", run_card)
    write_json(ROOT / "docs/data/hgvc88_run_card.json", run_card)
    write_json(ROOT / "evidence/hgvc88_run_card.json", run_card)

    print(
        f"\nDONE in {elapsed_s:.1f}s! File: docs/downloads/{dl_tif.name}\n"
        f"  SHA-256: {tif_sha}\n"
        f"  all_5_discriminating_gates_pass = {all_5_discriminating_gates_pass}\n"
        f"  ok_to_download = True | ok_to_submit = {ok_to_submit} | verdict = {verdict}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
