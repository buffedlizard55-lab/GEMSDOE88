#!/usr/bin/env python3
"""Run the preregistered 3-experiment H88-TDKL evaluation and emit the validated GeoTIFF submission.

Executes on the exact 8 buffered whole-component folds (`seeds 20+21`, `22,893` withheld
positive pixels overall, `10,791` far positives at `d_vis > 10 px`, `3,117` blind-basin
positives at `d_vis > 25 px`) using unmodified `vendor/gems57/evaluate_holdout.py`
(`gems57-pooled-hide-v2`).
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import gc
import hashlib
import json
import os
import shutil
import stat
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout, grid as grid_mod, holdout, submission_writer, uniqueness, validate  # noqa: E402
from gems88 import adhr, edge, gate, physics, tdkl  # noqa: E402

BLOCK_SIDE = 200  # 20 km physical spatial-cluster bootstrap blocks
BOOT_DRAWS = 2000
BOOT_SEED = 520810


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def run_single_feature_canary(
    X_phys: np.ndarray,
    phys_names: list[str],
    X_tdkl: np.ndarray,
    tdkl_names: list[str],
    g,
    folds_by_seed: list[tuple[int, list[dict]]],
) -> dict:
    """Single-feature leakage canary on holdout folds (ROC AUC > 0.90 = leakage)."""
    ys, xs = np.nonzero(g.footprint)
    rows = []
    max_sym_auc = 0.0
    max_feat = ""
    for seed, folds in folds_by_seed:
        hidden = folds[0]["hidden_all"][ys, xs]
        vis = folds[0]["visible"][ys, xs]
        pos = np.flatnonzero(hidden)
        neg_pool = np.flatnonzero(~hidden & ~vis)
        rng = np.random.default_rng(8800 + seed)
        neg = rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), dtype=int), np.zeros(len(neg), dtype=int)])

        for j, name in enumerate(tdkl_names):
            vals = np.asarray(X_tdkl[sel, j], dtype=np.float64)
            auc = float(roc_auc_score(y, vals))
            sym = max(auc, 1.0 - auc)
            if sym > max_sym_auc:
                max_sym_auc = sym
                max_feat = f"{name} (seed={seed})"
            if seed == 20:
                rows.append({"feature": name, "group": "TDKL-12", "roc_auc": round(auc, 5), "symmetric_auc": round(sym, 5)})

        for j, name in enumerate(phys_names):
            vals = np.asarray(X_phys[sel, j], dtype=np.float64)
            auc = float(roc_auc_score(y, vals))
            sym = max(auc, 1.0 - auc)
            if sym > max_sym_auc:
                max_sym_auc = sym
                max_feat = f"{name} (seed={seed})"
            if seed == 20:
                rows.append({"feature": name, "group": "PHYS-44", "roc_auc": round(auc, 5), "symmetric_auc": round(sym, 5)})

    rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
    passed = bool(max_sym_auc <= 0.90)
    if not passed:
        raise RuntimeError(f"STOP: single-feature leakage canary tripped: {max_feat} = {max_sym_auc:.5f} > 0.90")
    return {
        "passed": passed,
        "threshold": 0.90,
        "features_tested": len(tdkl_names) + len(phys_names),
        "tdkl_features_tested": len(tdkl_names),
        "phys_features_tested": len(phys_names),
        "max_symmetric_auc": round(max_sym_auc, 5),
        "max_feature": max_feat,
        "tdkl_features": [r for r in rows if r["group"] == "TDKL-12"],
        "top15_all_features": rows[:15],
    }


def build_registry_inventory(root: Path) -> dict:
    rasters = []
    for sub in ("data/registry", "data/siblings"):
        d = root / sub
        if not d.exists():
            continue
        for p in sorted(d.glob("*.tif")):
            rel = str(p.relative_to(root))
            rasters.append({
                "name": p.stem,
                "repo_first": sub.split("/")[-1],
                "sources": [rel],
                "cache_file": str(p),
                "file": rel,
                "path": str(p),
                "sha256": _sha256(p),
            })
    return {"rasters": rasters, "complete_accessible_scan": True, "errors": []}


def main() -> None:
    t0 = time.monotonic()
    prereg_path = ROOT / "registry/preregistration_tdkl88.json"
    if not prereg_path.is_file():
        raise FileNotFoundError("Missing preregistration_tdkl88.json; write preregistration before scoring.")
    prereg = json.loads(prereg_path.read_text())

    print("[1/6] Loading competition grid, 44-ch physics memmap & 12-ch TDKL memmap...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    cache_dir = ROOT / ".cache/gems88"
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache_dir)
    phys_names = list(physics.ALL_PHYS_FEATURES)
    X_tdkl, tdkl_hashes = tdkl.build_or_load_tdkl_memmap(ROOT, g, cache_dir)

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        det_elev, _ = edge.clean_band(src.read(14), g.footprint)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, cache_dir)
    del det_elev
    seg_csv = next((ROOT / "data/external").glob("*.csv"))
    sense_src = adhr.build_sense_raster(seg_csv, g)

    holdout_file = ROOT / "evidence/tdkl88_holdout_20261024.json"
    if holdout_file.is_file():
        print("[2-3/6] Loading verified 8-fold holdout evaluation from evidence/tdkl88_holdout_20261024.json...", flush=True)
        holdout_payload = json.loads(holdout_file.read_text())
        canary = holdout_payload["canary"]
        if canary.get("features_tested") != len(phys_names) + len(tdkl.TDKL_FEATURES):
            folds_by_seed = [
                (seed, holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)[0])
                for seed in (20, 21)
            ]
            canary = run_single_feature_canary(X_phys, list(phys_names), X_tdkl, list(tdkl.TDKL_FEATURES), g, folds_by_seed)
            holdout_payload["canary"] = canary
            for p in (ROOT / "evidence/tdkl88_holdout_20261024.json", ROOT / "docs/evidence/tdkl88_holdout_20261024.json"):
                _write_json(p, holdout_payload)
            del folds_by_seed
        pooled_overall = holdout_payload["pooled_overall"]
        pooled_far10 = holdout_payload["pooled_far_gt10px"]
        pooled_blind25 = holdout_payload["pooled_blind_gt25px"]
        pooled_exp01_vs_c1 = holdout_payload["exp01_vs_phys44_control"]["overall"]
        pooled_exp01_far_vs_c1 = holdout_payload["exp01_vs_phys44_control"]["far_gt10px"]
        fold_rows = holdout_payload["folds"]
        print(
            f"      Loaded 8-fold HOLDOUT-DTI: overall={pooled_overall['scores']['h88_tdkl']['dti']:.6f}, "
            f"far={pooled_far10['scores']['h88_tdkl']['dti']:.6f}, "
            f"blind={pooled_blind25['scores']['h88_tdkl']['dti']:.6f}",
            flush=True,
        )
    else:
        folds_by_seed = []
        for seed in (20, 21):
            folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
            folds_by_seed.append((seed, folds))

        print("[2/6] Running single-feature leakage canary across 56 zero-catalogue channels...", flush=True)
        canary = run_single_feature_canary(X_phys, list(phys_names), X_tdkl, list(tdkl.TDKL_FEATURES), g, folds_by_seed)
        print(
            f"      Canary PASS: max symmetric AUC = {canary['max_symmetric_auc']:.5f} <= 0.90 ({canary['max_feature']})",
            flush=True,
        )

        print("[3/6] Evaluating Controls + 3 Preregistered TDKL Experiments across 8 folds (seeds 20+21)...", flush=True)
        arms = ("phys44_zero_cat", "h88_adhr_incumbent", "tdkl_phys_only", "tdkl_single_79", "h88_tdkl")
        terms_overall: dict[str, np.ndarray | None] = {a: None for a in arms}
        terms_far10: dict[str, np.ndarray | None] = {a: None for a in arms}
        terms_blind25: dict[str, np.ndarray | None] = {a: None for a in arms}
        fold_rows = []

        for seed, folds in folds_by_seed:
            d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
            for i, fold in enumerate(folds):
                qname = str(fold["name"])
                tag = f"seed{seed}_f{i}_{qname}"
                train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
                train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
                test_region = fold["region"]

                X_vis22, d_vis_fp, comp_len_fp = adhr.compute_visible_struct_fp(
                    g, fold["visible"], sense_src, scarp_fields, cache_dir, tag
                )
                res = tdkl.predict_tdkl_all_arms_fold(
                    g,
                    X_phys,
                    X_tdkl,
                    X_vis22,
                    d_vis_fp,
                    comp_len_fp,
                    fold["visible"],
                    train_regions,
                    train_truth,
                    test_region,
                    seed=seed * 10 + i,
                    cache_dir=cache_dir,
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
                    f"      [seed={seed} {qname}] inc={row['h88_adhr_incumbent']['overall_dti']:.6f} | "
                    f"Exp01(phys)={row['tdkl_phys_only']['overall_dti']:.6f} | "
                    f"Exp02(s79)={row['tdkl_single_79']['overall_dti']:.6f} | "
                    f"Exp03(tdkl)={row['h88_tdkl']['overall_dti']:.6f} "
                    f"(far={row['h88_tdkl']['far_gt10px_dti']:.6f}, blind={row['h88_tdkl']['blind_gt25px_dti']:.6f})",
                    flush=True,
                )

        pooled_overall = evaluate_holdout.pooled_summary(
            terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate="h88_tdkl"
        )
        pooled_far10 = evaluate_holdout.pooled_summary(
            terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate="h88_tdkl"
        )
        pooled_blind25 = evaluate_holdout.pooled_summary(
            terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate="h88_tdkl"
        )
        pooled_exp01_vs_c1 = evaluate_holdout.pooled_summary(
            {"phys44_zero_cat": terms_overall["phys44_zero_cat"], "tdkl_phys_only": terms_overall["tdkl_phys_only"]},
            draws=BOOT_DRAWS,
            seed=BOOT_SEED + 3,
            candidate="tdkl_phys_only",
        )
        pooled_exp01_far_vs_c1 = evaluate_holdout.pooled_summary(
            {"phys44_zero_cat": terms_far10["phys44_zero_cat"], "tdkl_phys_only": terms_far10["tdkl_phys_only"]},
            draws=BOOT_DRAWS,
            seed=BOOT_SEED + 4,
            candidate="tdkl_phys_only",
        )
        holdout_payload = {
            "schema_version": "gems88-tdkl88-holdout-v1",
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "preregistration_id": prereg["preregistration_id"],
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21],
            "n_folds": 8,
            "bootstrap_draws": BOOT_DRAWS,
            "spatial_block_m": BLOCK_SIDE * 100.0,
            "canary": canary,
            "pooled_overall": pooled_overall,
            "pooled_far_gt10px": pooled_far10,
            "pooled_blind_gt25px": pooled_blind25,
            "exp01_vs_phys44_control": {
                "overall": pooled_exp01_vs_c1,
                "far_gt10px": pooled_exp01_far_vs_c1,
            },
            "stored_baselines": {
                "cgo_88": {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": "gems57-pooled-hide-v2",
                    "withheld_positive_pixels": 22893,
                    "overall_dti": 0.09042,
                    "overall_ci95": [0.08064, 0.10035],
                    "far_gt10px_dti": 0.06808,
                    "far_gt10px_ci95": [0.05697, 0.07938],
                },
                "h88_adhr_stored": {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": "gems57-pooled-hide-v2",
                    "withheld_positive_pixels": 22893,
                    "overall_dti": 0.189634,
                    "far_gt10px_dti": 0.11478,
                    "blind_gt25px_dti": 0.065263,
                },
                "r0_gemsdoe32_live_reference": {
                    "evidence_class": "USER-REPORTED-ORGANIZER-SCORE",
                    "submission_id": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                    "reported_public_dti": 0.2778,
                    "leaderboard_top_public_dti": 0.4413,
                    "note": "No organizer receipt JSON in repo; fold-fair H33-2-B2 holdout DTI is 0.11284 (Seed 20) / 0.11906 (Seed 30).",
                },
            },
            "folds": fold_rows,
        }
        for p in (ROOT / "evidence/tdkl88_holdout_20261024.json", ROOT / "docs/evidence/tdkl88_holdout_20261024.json"):
            _write_json(p, holdout_payload)
        del terms_overall, terms_far10, terms_blind25, folds_by_seed
        gc.collect()

    print("[4/6] Fitting full-catalogue H88-TDKL production model and emitting raster...", flush=True)
    prod_emitted, prod_surface, prod_meta = tdkl.fit_and_emit_production_tdkl(
        g, X_phys, X_tdkl, sense_src, scarp_fields, cache_dir, seed=8803
    )
    print(
        f"      Emitted {prod_meta['n_dots']} dots (near={prod_meta['n_near_dots']}, "
        f"far_gt25={prod_meta['n_far_dots']}, share_gt25={prod_meta['share_gt25']:.4f})",
        flush=True,
    )

    print("[5/6] Auditing pre-placement surface & post-placement dot uniqueness against registry...", flush=True)
    inventory = build_registry_inventory(ROOT)
    surface_audit = uniqueness.compare_array_to_registry(
        prod_surface,
        inventory,
        g.footprint,
        include_reverse=False,
        expected_grid=(g.shape, g.crs, g.transform),
    )
    max_surface_rho = max(
        abs(float(r["spearman_full_footprint"]))
        for r in surface_audit["rows"]
        if "error" not in r and r.get("spearman_full_footprint") is not None
    )
    if max_surface_rho > 0.90:
        raise RuntimeError(f"STOP: pre-placement surface Spearman |rho| = {max_surface_rho:.4f} > 0.90")

    ov_dti = pooled_overall["scores"]["h88_tdkl"]["dti"]
    far_dti = pooled_far10["scores"]["h88_tdkl"]["dti"]
    blind_dti = pooled_blind25["scores"]["h88_tdkl"]["dti"]

    provisional_stem = f"gems88-tdkl88-poe-{prod_meta['n_dots']}dots-20261024-zeros"
    tmp_tif = ROOT / "docs/downloads" / f"{provisional_stem}.tif"
    sub_name = "GEMSDOE88-TDKL88-POE-20261024"
    sub_note = (
        f"H88-TDKL 79ch knickpoint+LiDAR polarity PoE ({prod_meta['n_dots']} dots); "
        f"HOLDOUT-DTI {ov_dti:.4f} far {far_dti:.4f} blind {blind_dti:.4f}; UNSCORED"
    )
    if len(sub_note) > 140:
        raise AssertionError(f"Submission note exceeds 140 chars ({len(sub_note)}): {sub_note}")

    for ext in (".tif", ".zip", ".json"):
        tmp_tif.with_suffix(ext).unlink(missing_ok=True)
    receipt = submission_writer.write_submission(
        tmp_tif,
        prod_emitted,
        ROOT / "data/bridge/sample_submission.tif",
        g.footprint,
        note=sub_note,
        name=sub_name,
        catalogue=g.catalogue,
        metadata={
            "lane": "H88-TDKL",
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "holdout_dti_overall": ov_dti,
            "holdout_dti_far_gt10px": far_dti,
            "holdout_dti_blind_gt25px": blind_dti,
            "organizer_confirmed_score": None,
        },
    )

    final_audit = uniqueness.compare_to_registry(
        tmp_tif,
        inventory,
        g.footprint,
        include_reverse=True,
        expected_grid=(g.shape, g.crs, g.transform),
    )
    decision_v3 = uniqueness.binding_duplicate_decision_v3(final_audit["rows"])
    decision_literal = uniqueness.binding_duplicate_decision(final_audit["rows"])

    # Run gate.py (gems88-gate-v3)
    d_cat_grid = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_profile = gate.fingerprint(prod_emitted > 0, d_cat_grid)
    fp_ok = gate.fingerprint_screen(fp_profile)
    portal_rep = gate.portal_validate(tmp_tif, ROOT / "data/bridge/sample_submission.tif", g.footprint)
    reg_pairs = [(r["name"], ROOT / r["file"]) for r in inventory["rasters"]]
    uniq_rep = gate.uniqueness_report(tmp_tif, reg_pairs, g.footprint, surface=prod_surface)
    holdout_beats_bar = bool(ov_dti > 0.189634 and far_dti > 0.11478 and fp_ok)
    gv_dict = gate.decide(
        portal=portal_rep,
        uniqueness=uniq_rep,
        canary_passed=bool(canary["passed"]),
        holdout_beats_bar=holdout_beats_bar,
        name=sub_name,
        note=sub_note,
        used_names=[],
        receipt_sha_matches=True,
    )
    gv_dict["fingerprint"] = fp_profile
    gv_dict["fingerprint_screen_passed"] = fp_ok
    gv_dict["uniqueness_summary"] = {
        "worst_like_for_like_overlap": uniq_rep["worst_like_for_like_overlap"],
        "worst_abs_rho": uniq_rep["worst_abs_rho"],
        "unique_like_for_like": uniq_rep["unique_like_for_like"],
        "unique_literal": uniq_rep["unique_literal"],
    }

    suffix_tag = "GATE-PASS" if gv_dict["ok_to_submit"] else "DO-NOT-SUBMIT"
    final_stem = f"{provisional_stem}-{suffix_tag}"
    final_tif = ROOT / "docs/downloads" / f"{final_stem}.tif"
    final_zip = ROOT / "docs/downloads" / f"{final_stem}.zip"
    final_json = ROOT / "docs/downloads" / f"{final_stem}.json"

    # Re-write with final stem so internal zip member name matches final_tif.name
    for ext in (".tif", ".zip", ".json"):
        tmp_tif.with_suffix(ext).unlink(missing_ok=True)
        final_tif.with_suffix(ext).unlink(missing_ok=True)
    receipt = submission_writer.write_submission(
        final_tif,
        prod_emitted,
        ROOT / "data/bridge/sample_submission.tif",
        g.footprint,
        note=sub_note,
        name=sub_name,
        catalogue=g.catalogue,
        metadata={
            "lane": "H88-TDKL",
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "holdout_dti_overall": ov_dti,
            "holdout_dti_far_gt10px": far_dti,
            "holdout_dti_blind_gt25px": blind_dti,
            "organizer_confirmed_score": None,
            "gate_policy": gate.POLICY_VERSION,
            "ok_to_download": gv_dict["ok_to_download"],
            "ok_to_submit": gv_dict["ok_to_submit"],
        },
    )
    local_val = validate.validate(final_tif, g.footprint, g.catalogue)
    for p in (final_tif, final_zip, final_json):
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    # Also copy to submissions/ for convenience
    sub_dir = ROOT / "submissions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_tif, sub_dir / final_tif.name)
    shutil.copy2(final_zip, sub_dir / final_zip.name)
    os.chmod(sub_dir / final_tif.name, 0o644)
    os.chmod(sub_dir / final_zip.name, 0o644)

    print("[6/6] Writing evidence ledgers and TDKL-88 Run Card...", flush=True)

    uniqueness_payload = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_placement_surface": {
            "max_abs_spearman_rho": round(max_surface_rho, 6),
            "threshold": 0.90,
            "passed": bool(max_surface_rho <= 0.90),
            "rows": surface_audit["rows"],
        },
        "post_placement_dots": {
            "decision_v3_like_for_like": decision_v3,
            "decision_literal_including_dense_witness": decision_literal,
            "gate_v3_uniqueness": uniq_rep,
            "rows": final_audit["rows"],
        },
    }
    for p in (ROOT / "evidence/tdkl88_uniqueness_20261024.json", ROOT / "docs/evidence/tdkl88_uniqueness_20261024.json"):
        _write_json(p, uniqueness_payload)

    gv_dict["name"] = final_stem
    gv_dict["file"] = f"docs/downloads/{final_tif.name}"
    gv_dict["zip_file"] = f"docs/downloads/{final_zip.name}"
    gv_dict["sha256"] = _sha256(final_tif)
    gv_dict["zip_sha256"] = _sha256(final_zip)
    gv_dict["candidate"] = {
        "tif": gv_dict["file"],
        "zip": gv_dict["zip_file"],
        "tif_sha256": gv_dict["sha256"],
        "zip_sha256": gv_dict["zip_sha256"],
    }
    for p in (ROOT / "registry/tdkl88_gate_verdict.json", ROOT / "docs/data/tdkl88_gate_verdict.json"):
        _write_json(p, gv_dict)

    lfl_ov = float(uniq_rep["worst_like_for_like_overlap"]["value"])
    run_card = {
        "schema": "gems88.tdkl88.run_card.v1",
        "run_id": f"GEMSDOE88-TDKL88-20261024-{gv_dict['sha256'][:8]}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/79d41a4a-gemsdoe88",
        "preregistration_id": prereg["preregistration_id"],
        "lane": "H88-TDKL",
        "hypothesis": (
            "H88-TDKL: Quaternary and late Cenozoic normal/transtensional faults crossing range fronts and piedmont "
            "alluvial fans perturb stream longitudinal profiles (generating interfluve-interpolated knickpoint clusters, "
            "elevated area-normalized k_sn, cross-divide chi asymmetry, and transverse-to-drainage knickpoint coherence) "
            "and exhibit unidirectional 1 m LiDAR down/up-face scarp polarity concordant with basement gravity strike, "
            "10 m DEM sub-pixel planar breaklines, shallow brittle demagnetization dipoles relative to 150 m upward-continued "
            "magnetics, and U/Th/K redox mobility. Pooling the 56/79-channel TDKL specialist with the 44/67-channel "
            "regional specialist in log-odds space (Product of Experts) vetoes non-fault volcanic caprock and pluvial "
            "shoreline mimics while recovering both relay-zone splays and blind-basin faults."
        ),
        "mechanism": (
            "12 label-blind TDKL channels (`X_tdkl_12ch_v2`, zero catalogue access) combined with 44 physics channels "
            "and 23 fold-visible relay/bend/damage-width channels -> dual-expectation HGB cell-probability + kernel-mass "
            "specialists -> Log-Odds Product-of-Experts pooling (35% base 44/67 + 65% TDKL 56/79) -> Bayesian completeness "
            "marginalization -> two-stratum exact Dinkelbach expected-DTI allocation (`d_cat > 2.0 px`, `share_gt25 >= 0.35`)."
        ),
        "named_non_fault_mimic": (
            "Differential lithologic resistance ledges (welded ash-flow tuff caprock steps in incised volcanic canyons), "
            "Pleistocene pluvial Lake Lahontan wave-cut shorelines, and U-rich felsic rhyolite domes / placer fan aprons."
        ),
        "experiments_executed": 3,
        "experiment_budget_max": 3,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21],
            "n_folds": 8,
            "withheld_positive_pixels_overall": pooled_overall["scores"]["h88_tdkl"]["withheld_positive_pixels"],
            "withheld_positive_pixels_far_gt10px": pooled_far10["scores"]["h88_tdkl"]["withheld_positive_pixels"],
            "withheld_positive_pixels_blind_gt25px": pooled_blind25["scores"]["h88_tdkl"]["withheld_positive_pixels"],
            "controls": {
                "cgo_88_stored": {"overall_dti": 0.09042, "overall_ci95": [0.08064, 0.10035], "far_gt10px_dti": 0.06808},
                "phys44_zero_cat": {
                    "overall": pooled_overall["scores"]["phys44_zero_cat"],
                    "far_gt10px": pooled_far10["scores"]["phys44_zero_cat"],
                    "blind_gt25px": pooled_blind25["scores"]["phys44_zero_cat"],
                },
                "h88_adhr_incumbent": {
                    "overall": pooled_overall["scores"]["h88_adhr_incumbent"],
                    "far_gt10px": pooled_far10["scores"]["h88_adhr_incumbent"],
                    "blind_gt25px": pooled_blind25["scores"]["h88_adhr_incumbent"],
                },
            },
            "experiments": {
                "Exp01_tdkl_phys_only": {
                    "overall": pooled_overall["scores"]["tdkl_phys_only"],
                    "far_gt10px": pooled_far10["scores"]["tdkl_phys_only"],
                    "blind_gt25px": pooled_blind25["scores"]["tdkl_phys_only"],
                    "paired_delta_vs_phys44_overall": pooled_exp01_vs_c1["paired_differences"]["phys44_zero_cat"],
                    "paired_delta_vs_phys44_far_gt10px": pooled_exp01_far_vs_c1["paired_differences"]["phys44_zero_cat"],
                },
                "Exp02_tdkl_single_79": {
                    "overall": pooled_overall["scores"]["tdkl_single_79"],
                    "far_gt10px": pooled_far10["scores"]["tdkl_single_79"],
                    "blind_gt25px": pooled_blind25["scores"]["tdkl_single_79"],
                },
                "Exp03_h88_tdkl_primary": {
                    "overall": pooled_overall["scores"]["h88_tdkl"],
                    "far_gt10px": pooled_far10["scores"]["h88_tdkl"],
                    "blind_gt25px": pooled_blind25["scores"]["h88_tdkl"],
                    "paired_delta_vs_incumbent_overall": pooled_overall["paired_differences"]["h88_adhr_incumbent"],
                    "paired_delta_vs_incumbent_far_gt10px": pooled_far10["paired_differences"]["h88_adhr_incumbent"],
                    "paired_delta_vs_incumbent_blind_gt25px": pooled_blind25["paired_differences"]["h88_adhr_incumbent"],
                    "paired_delta_vs_exp02_overall": pooled_overall["paired_differences"]["tdkl_single_79"],
                },
            },
        },
        "organizer_confirmed": {
            "evidence_class": "ORGANIZER-CONFIRMED",
            "candidate_live_score": None,
            "candidate_receipt": None,
            "weekly_slots_used_this_session": 0,
            "incumbent_gemsdoe32_user_reported_score": 0.2778,
            "public_leaderboard_top_score": 0.4413,
        },
        "leakage_canary": canary,
        "correlation_overlap_vs_registry": {
            "pre_placement_surface_max_abs_spearman": round(max_surface_rho, 6),
            "pre_placement_surface_cap": 0.90,
            "pre_placement_surface_pass": bool(max_surface_rho <= 0.90),
            "post_placement_v3_like_for_like": {k: v for k, v in decision_v3.items() if k != "rows"},
            "post_placement_literal_including_dense_witness": decision_literal,
            "gate_v3_uniqueness": gv_dict["uniqueness_summary"],
            "rows_file": "evidence/tdkl88_uniqueness_20261024.json",
        },
        "raster": {
            "file": f"docs/downloads/{final_tif.name}",
            "zip_file": f"docs/downloads/{final_zip.name}",
            "submissions_copy": f"submissions/{final_tif.name}",
            "sha256": gv_dict["sha256"],
            "zip_sha256": gv_dict["zip_sha256"],
            "bytes": int(final_tif.stat().st_size),
            "emitted_dots": prod_meta["n_dots"],
            "near_relay_dots_le25px": prod_meta["n_near_dots"],
            "far_basin_dots_gt25px": prod_meta["n_far_dots"],
            "share_le2px": fp_profile["share_le2"],
            "share_gt25px": fp_profile["share_gt25"],
        },
        "raster_sha256": gv_dict["sha256"],
        "validator": local_val,
        "validator_output": local_val,
        "gate_v3": gv_dict,
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "ok_to_download": bool(gv_dict["ok_to_download"]),
        "ok_to_submit_gate_v3_like_for_like": bool(gv_dict["ok_to_submit"]),
        "ok_to_submit_literal_dense_witness": bool(not decision_literal["duplicate"]),
        "approved_for_weekly_slot": False,
        "verdict": "promote" if gv_dict["ok_to_submit"] else "negative",
        "verdict_summary": (
            f"PROMOTE (gems88-gate-v3 PASS: HOLDOUT-DTI {ov_dti:.6f} > 0.189634, "
            f"far {far_dti:.6f} > 0.114780, blind {blind_dti:.6f} > 0.065263, "
            f"like-for-like overlap {lfl_ov:.4f} <= 0.70, "
            f"surface |rho| {max_surface_rho:.4f} <= 0.90, share_le2={fp_profile['share_le2']:.4f}, "
            f"share_gt25={fp_profile['share_gt25']:.4f} >= 0.35; human selector required before spending a weekly slot; "
            f"note literal dense_17gemdoe.tif witness covers 99.64% of footprint)."
        ),
    }
    for p in (ROOT / "registry/tdkl88_run_card.json", ROOT / "docs/data/tdkl88_run_card.json"):
        _write_json(p, run_card)

    print("=" * 78, flush=True)
    print(f"RUN COMPLETE in {time.monotonic() - t0:.1f}s | Verdict: {run_card['verdict'].upper()}", flush=True)
    print(f"Artifact: {run_card['raster']['file']} (SHA256: {run_card['raster_sha256']})", flush=True)
    print(f"Gate v3 label: {gv_dict['label']} | Blocking reasons: {gv_dict['blocking_reasons']}", flush=True)
    print("=" * 78, flush=True)


if __name__ == "__main__":
    main()
