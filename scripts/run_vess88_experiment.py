#!/usr/bin/env python3
"""Run the preregistered H88-VESS holdout evaluation and emit the research GeoTIFF.

Lane: 12 zero-catalogue Frangi vesselness channels (src/gems88/vess.py)
pooled with 44 physics + 12 TDKL channels via the shared log-odds PoE
machinery.  Evaluator, writer, uniqueness and gate code are the shared
vendor/gems57 + src/gems88 modules, unmodified.  Corrects IR-88-110/108
for this lane: scarp fields come from B12 (det_elev) and the slip-sense
CSV is named explicitly (trace_segments_utm11.csv).
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
from gems88 import adhr, edge, gate, physics, tdkl, vess  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402

BLOCK_SIDE = 200
BOOT_DRAWS = 2000
BOOT_SEED = 520810
DATE = "20261024"
ARMS_MAP = {
    "phys44_zero_cat": "phys44_zero_cat",
    "h88_adhr_incumbent": "h88_adhr_incumbent",
    "tdkl_phys_only": "vess_extra_phys_only",
    "tdkl_single_79": "vess_single_combined",
    "h88_tdkl": "h88_vess",
}
CANDIDATE = "h88_vess"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def run_canary(groups, g, folds_by_seed) -> dict:
    """Single-feature leakage canary: symmetric AUC > 0.90 = leakage."""
    ys, xs = np.nonzero(g.footprint)
    rows, max_sym, max_feat = [], 0.0, ""
    for seed, folds in folds_by_seed:
        hidden = folds[0]["hidden_all"][ys, xs]
        vis = folds[0]["visible"][ys, xs]
        pos = np.flatnonzero(hidden)
        neg_pool = np.flatnonzero(~hidden & ~vis)
        rng = np.random.default_rng(8800 + seed)
        neg = rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), int), np.zeros(len(neg), int)])
        for X, names, group in groups:
            for j, name in enumerate(names):
                vals = np.asarray(X[sel, j], dtype=np.float64)
                auc = float(roc_auc_score(y, vals))
                sym = max(auc, 1.0 - auc)
                if sym > max_sym:
                    max_sym, max_feat = sym, f"{name} (seed={seed})"
                if seed == 20:
                    rows.append({"feature": name, "group": group, "roc_auc": round(auc, 5), "symmetric_auc": round(sym, 5)})
    rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
    passed = bool(max_sym <= 0.90)
    if not passed:
        raise RuntimeError(f"STOP: leakage canary tripped: {max_feat} = {max_sym:.5f} > 0.90")
    return {"passed": passed, "threshold": 0.90, "features_tested": sum(len(n) for _, n, _ in groups),
            "max_symmetric_auc": round(max_sym, 5), "max_feature": max_feat, "top15_all_features": rows[:15],
            "vess_features": [r for r in rows if r["group"] == "VESS-12"]}


def build_registry_inventory(root: Path) -> dict:
    rasters = []
    for sub in ("data/registry", "data/siblings"):
        d = root / sub
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.tif")):
            rel = str(p.relative_to(root))
            rasters.append({"name": p.stem, "repo_first": sub.split("/")[-1], "sources": [rel],
                            "cache_file": rel, "file": rel, "path": str(p), "sha256": _sha256(p)})
    return {"rasters": rasters, "complete_accessible_scan": True, "errors": []}


def main() -> None:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_vess88.json").read_text())

    print("[1/6] Loading grid, physics/TDKL/VESS memmaps...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    cache_dir = ROOT / ".cache/gems88"
    vess_cache = ROOT / ".cache/gems88_vess"
    vess_cache.mkdir(parents=True, exist_ok=True)
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache_dir)
    X_tdkl, _ = tdkl.build_or_load_tdkl_memmap(ROOT, g, cache_dir)
    X_vess, vess_meta = vess.build_or_load_vess_memmap(ROOT, g, cache_dir)
    # combined extra stack (TDKL 12 + VESS 12 = 24 ch) as one memmap
    n_fp = int(g.footprint.sum())
    comb_path = cache_dir / "x_extra_tdkl_vess_24ch.dat"
    if not comb_path.exists() or comb_path.stat().st_size != n_fp * 24 * 4:
        comb = np.memmap(comb_path, dtype="float32", mode="w+", shape=(n_fp, 24))
        for s in range(0, n_fp, 250_000):
            e = min(s + 250_000, n_fp)
            comb[s:e, :12] = np.asarray(X_tdkl[s:e])
            comb[s:e, 12:] = np.asarray(X_vess[s:e])
        comb.flush()
        del comb
    X_extra = np.memmap(comb_path, dtype="float32", mode="r", shape=(n_fp, 24))
    extra_names = list(tdkl.TDKL_FEATURES) + list(vess.VESS_FEATURES)

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)  # B12 det_elev (IR-88-110 fix)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, vess_cache)
    del det_elev
    sense_src = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)  # IR-88-111 fix

    folds_by_seed = []
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))

    print("[2/6] Leakage canary (68 features)...", flush=True)
    canary = run_canary(
        [(X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
         (X_tdkl, list(tdkl.TDKL_FEATURES), "TDKL-12"),
         (X_vess, list(vess.VESS_FEATURES), "VESS-12")], g, folds_by_seed)
    print(f"      PASS max symmetric AUC = {canary['max_symmetric_auc']:.5f} ({canary['max_feature']})", flush=True)

    print("[3/6] 8-fold holdout: controls + 3 preregistered experiments...", flush=True)
    arms = tuple(ARMS_MAP.values())
    terms_overall = {a: None for a in arms}
    terms_far10 = {a: None for a in arms}
    terms_blind25 = {a: None for a in arms}
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
                g, fold["visible"], sense_src, scarp_fields, vess_cache, tag)
            res_raw = tdkl.predict_tdkl_all_arms_fold(
                g, X_phys, X_extra, X_vis22, d_vis_fp, comp_len_fp, fold["visible"],
                train_regions, train_truth, test_region, seed=seed * 10 + i,
                cache_dir=vess_cache, fold_tag=tag)
            res = {ARMS_MAP[k]: v for k, v in res_raw.items()}
            far_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
            far_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
            far_fold = {**fold, "truth": far_truth, "region": far_valid, "masked_known": np.zeros_like(far_valid)}
            blind_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
            blind_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
            blind_fold = {**fold, "truth": blind_truth, "region": blind_valid, "masked_known": np.zeros_like(blind_valid)}
            row = {"seed": seed, "fold": qname,
                   "withheld_positive_pixels": int((fold["truth"] & test_region & ~fold["masked_known"]).sum()),
                   "far_withheld_positive_pixels": int(far_truth.sum()),
                   "blind_withheld_positive_pixels": int(blind_truth.sum())}
            for arm in arms:
                emitted_arm, _, meta_arm = res[arm]
                sc_ov, bt_ov = evaluate_holdout.evaluate(emitted_arm, fold, g.footprint, block_side=BLOCK_SIDE)
                sc_fr, bt_fr = evaluate_holdout.evaluate(emitted_arm, far_fold, g.footprint, block_side=BLOCK_SIDE)
                sc_bl, bt_bl = evaluate_holdout.evaluate(emitted_arm, blind_fold, g.footprint, block_side=BLOCK_SIDE)
                terms_overall[arm] = bt_ov if terms_overall[arm] is None else terms_overall[arm] + bt_ov
                terms_far10[arm] = bt_fr if terms_far10[arm] is None else terms_far10[arm] + bt_fr
                terms_blind25[arm] = bt_bl if terms_blind25[arm] is None else terms_blind25[arm] + bt_bl
                row[arm] = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                            "overall_dti": round(float(sc_ov["dti"]), 6),
                            "far_gt10px_dti": round(float(sc_fr["dti"]), 6),
                            "blind_gt25px_dti": round(float(sc_bl["dti"]), 6),
                            "emitted_dots": int(meta_arm["n_dots"])}
            fold_rows.append(row)
            print(f"      [seed={seed} {qname}] inc={row['h88_adhr_incumbent']['overall_dti']:.6f} | "
                  f"Exp1={row['vess_extra_phys_only']['overall_dti']:.6f} | Exp2={row['vess_single_combined']['overall_dti']:.6f} | "
                  f"Exp3 VESS={row[CANDIDATE]['overall_dti']:.6f} (far={row[CANDIDATE]['far_gt10px_dti']:.6f}, blind={row[CANDIDATE]['blind_gt25px_dti']:.6f})", flush=True)

    pooled_overall = evaluate_holdout.pooled_summary(terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=CANDIDATE)
    pooled_far10 = evaluate_holdout.pooled_summary(terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=CANDIDATE)
    pooled_blind25 = evaluate_holdout.pooled_summary(terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=CANDIDATE)
    holdout_payload = {
        "schema_version": "gems88-vess88-holdout-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration_id": prereg["preregistration_id"],
        "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
        "seeds": [20, 21], "n_folds": 8, "bootstrap_draws": BOOT_DRAWS,
        "spatial_block_m": BLOCK_SIDE * 100.0, "canary": canary,
        "pooled_overall": pooled_overall, "pooled_far_gt10px": pooled_far10, "pooled_blind_gt25px": pooled_blind25,
        "stored_baselines": {
            "h88_adhr_stored": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2",
                                "withheld_positive_pixels": 22893, "overall_dti": 0.189634, "far_gt10px_dti": 0.11478, "blind_gt25px_dti": 0.065263},
            "h88_tdkl_stored": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2",
                                "withheld_positive_pixels": 22893, "overall_dti": 0.196237, "far_gt10px_dti": 0.124175, "blind_gt25px_dti": 0.076881,
                                "note": "TDKL run derived scarp fields from B14 (tmi) not B12 (IR-88-110); stored bar is therefore not strictly like-for-like with this lane's B12 scarp fields."},
            "r0_claim": {"evidence_class": "USER-REPORTED (no portal receipt in repo)", "submission_id": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                         "reported_public_dti": 0.2778, "leaderboard_top_public_dti_snapshot_20261024": 0.4413},
        },
        "folds": fold_rows,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }
    for p in (ROOT / "evidence/vess88_holdout_20261024.json", ROOT / "docs/evidence/vess88_holdout_20261024.json"):
        _write_json(p, holdout_payload)
    ov = pooled_overall["scores"][CANDIDATE]
    print(f"      POOLED HOLDOUT-DTI {CANDIDATE} = {ov['dti']:.6f} CI {ov['ci95']} n={ov['withheld_positive_pixels']}", flush=True)

    print("[4/6] Production fit + emission (two-stratum share_gt25>=0.35)...", flush=True)
    prod_emitted, prod_surface, prod_meta = tdkl.fit_and_emit_production_tdkl(
        g, X_phys, X_extra, sense_src, scarp_fields, vess_cache, seed=8811)
    print(f"      Emitted {prod_meta['n_dots']} dots share_gt25={prod_meta['share_gt25']:.4f}", flush=True)

    print("[5/6] Pre-placement surface uniqueness (vendor registry audit)...", flush=True)
    inventory = build_registry_inventory(ROOT)
    surface_audit = uniqueness.compare_array_to_registry(
        prod_surface, inventory, g.footprint, include_reverse=False,
        expected_grid=(g.shape, g.crs, g.transform))
    max_surface_rho = max(abs(float(r["spearman_full_footprint"])) for r in surface_audit["rows"]
                          if "error" not in r and r.get("spearman_full_footprint") is not None)
    print(f"      max |rho| surface = {max_surface_rho:.6f} (limit 0.90)", flush=True)
    if max_surface_rho > 0.90:
        raise RuntimeError(f"STOP duplicate: surface |rho| {max_surface_rho:.4f} > 0.90")

    far_dti = pooled_far10["scores"][CANDIDATE]["dti"]
    blind_dti = pooled_blind25["scores"][CANDIDATE]["dti"]
    sub_name = "GEMSDOE88-VESS88-POE-20261024"
    sub_note = (f"H88-VESS Frangi vesselness+TDKL PoE ({prod_meta['n_dots']} dots); "
                f"HOLDOUT-DTI {ov['dti']:.4f} far {far_dti:.4f} blind {blind_dti:.4f}; UNSCORED")
    assert len(sub_name) <= 140 and len(sub_note) <= 140, (sub_name, sub_note)

    # Write provisional, audit, then rewrite with final DO-NOT-SUBMIT/GATE tag stem
    prov_stem = f"gems88-vess88-poe-{prod_meta['n_dots']}dots-{DATE}-zeros"
    prov_tif = ROOT / "docs/downloads" / f"{prov_stem}.tif"
    for ext in (".tif", ".zip", ".json"):
        prov_tif.with_suffix(ext).unlink(missing_ok=True)
    submission_writer.write_submission(
        prov_tif, prod_emitted, ROOT / "data/bridge/sample_submission.tif", g.footprint,
        note=sub_note, name=sub_name, catalogue=g.catalogue,
        metadata={"lane": "H88-VESS", "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                  "holdout_dti_overall": ov["dti"], "holdout_dti_far_gt10px": far_dti,
                  "holdout_dti_blind_gt25px": blind_dti, "organizer_confirmed_score": None})

    reg_pairs = registry_list(ROOT, exclude=("vess88",))
    d_cat_grid = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_profile = gate.fingerprint(prod_emitted > 0, d_cat_grid)
    fp_ok = gate.fingerprint_screen(fp_profile)
    portal_rep = gate.portal_validate(prov_tif, ROOT / "data/bridge/sample_submission.tif", g.footprint)
    uniq_rep = gate.uniqueness_report(prov_tif, reg_pairs, g.footprint, surface=prod_surface)
    paired = pooled_overall["paired_differences"]["h88_adhr_incumbent"]
    beats_bar = bool(ov["dti"] > 0.196237 and paired["delta"] > 0 and paired["ci95"][0] > 0 and fp_ok)
    gv = gate.decide(portal=portal_rep, uniqueness=uniq_rep, canary_passed=bool(canary["passed"]),
                     holdout_beats_bar=beats_bar, name=sub_name, note=sub_note, used_names=[], receipt_sha_matches=True)
    # Protocol literal reading: dense-witness overlap is a blocker, not info.
    literal_block = not uniq_rep["unique_literal"]
    ok_submit_final = bool(gv["ok_to_submit"] and not literal_block)
    gv["ok_to_submit"] = ok_submit_final
    gv["blocking_reasons"] = list(gv.get("blocking_reasons", [])) + (
        ["UNIQUENESS (literal rule): forward 3px overlap vs dense/full-footprint registry raster(s): "
         + ", ".join(uniq_rep["literal_blockers"][:4])] if literal_block else [])
    gv["label"] = "OK TO DOWNLOAD - OK TO SUBMIT" if ok_submit_final else "OK TO DOWNLOAD - NOT OK TO SUBMIT"
    gv["fingerprint"] = fp_profile
    gv["fingerprint_screen_passed"] = fp_ok
    gv["uniqueness_summary"] = {"worst_like_for_like_overlap": uniq_rep["worst_like_for_like_overlap"],
                                "worst_abs_rho": uniq_rep["worst_abs_rho"],
                                "unique_like_for_like": uniq_rep["unique_like_for_like"],
                                "unique_literal": uniq_rep["unique_literal"],
                                "registry_rasters": uniq_rep["registry_rasters"]}
    gv["paired_delta_vs_adhr_incumbent"] = paired
    gv["holdout_beats_tdkl_stored_bar"] = bool(ov["dti"] > 0.196237)

    suffix = "GATE-PASS" if ok_submit_final else "DO-NOT-SUBMIT"
    final_stem = f"{prov_stem}-{suffix}"
    final_tif = ROOT / "docs/downloads" / f"{final_stem}.tif"
    final_zip = ROOT / "docs/downloads" / f"{final_stem}.zip"
    for ext in (".tif", ".zip", ".json"):
        prov_tif.with_suffix(ext).unlink(missing_ok=True)
        final_tif.with_suffix(ext).unlink(missing_ok=True)
    receipt = submission_writer.write_submission(
        final_tif, prod_emitted, ROOT / "data/bridge/sample_submission.tif", g.footprint,
        note=sub_note, name=sub_name, catalogue=g.catalogue,
        metadata={"lane": "H88-VESS", "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                  "holdout_dti_overall": ov["dti"], "holdout_dti_far_gt10px": far_dti,
                  "holdout_dti_blind_gt25px": blind_dti, "organizer_confirmed_score": None,
                  "gate_policy": gate.POLICY_VERSION, "ok_to_download": gv["ok_to_download"], "ok_to_submit": ok_submit_final})
    local_val = validate.validate(final_tif, g.footprint, g.catalogue)
    for p in (final_tif, final_zip, final_tif.with_suffix(".json")):
        if p.exists():
            os.chmod(p, 0o644)
    sub_dir = ROOT / "submissions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_tif, sub_dir / final_tif.name)
    shutil.copy2(final_zip, sub_dir / final_zip.name)

    print("[6/6] Writing run card + gate verdict + uniqueness evidence...", flush=True)
    uniqueness_payload = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_placement_surface": {"max_abs_spearman_rho": round(max_surface_rho, 6), "threshold": 0.90,
                                  "passed": bool(max_surface_rho <= 0.90), "rows": surface_audit["rows"]},
        "post_placement_dots": {"gate_v3_uniqueness": uniq_rep},
        "fingerprint": fp_profile, "fingerprint_screen_passed": fp_ok,
    }
    for p in (ROOT / "evidence/vess88_uniqueness_20261024.json", ROOT / "docs/evidence/vess88_uniqueness_20261024.json"):
        _write_json(p, uniqueness_payload)

    verdict = "promote" if ok_submit_final else "negative"
    run_card = {
        "schema": "gems88.vess88.run_card.v1",
        "run_id": f"GEMSDOE88-VESS88-{DATE}-{_sha256(final_tif)[:8]}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-VESS",
        "hypothesis": prereg["hypothesis"], "mechanism": prereg["mechanism"],
        "named_non_fault_mimic": prereg["named_non_fault_mimic"],
        "experiments_executed": 3, "experiment_budget_max": 3,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "holdout_dti": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                        "seeds": [20, 21], "n_folds": 8,
                        "withheld_positive_pixels_overall": ov["withheld_positive_pixels"],
                        "overall": ov, "far_gt10px": pooled_far10["scores"][CANDIDATE],
                        "blind_gt25px": pooled_blind25["scores"][CANDIDATE],
                        "paired_delta_vs_adhr_incumbent": paired,
                        "all_pooled": {"overall": pooled_overall, "far_gt10px": pooled_far10, "blind_gt25px": pooled_blind25}},
        "leakage_canary": canary,
        "correlation_overlap_vs_registry": {
            "surface_preplacement_max_abs_spearman": round(max_surface_rho, 6),
            "final_worst_like_for_like_overlap_3px": uniq_rep["worst_like_for_like_overlap"],
            "final_worst_abs_rho": uniq_rep["worst_abs_rho"],
            "unique_like_for_like": uniq_rep["unique_like_for_like"],
            "unique_literal": uniq_rep["unique_literal"],
            "literal_blockers": uniq_rep["literal_blockers"],
            "registry_rasters_checked": uniq_rep["registry_rasters"]},
        "validator_output": local_val,
        "portal_validate": portal_rep,
        "raster_sha256": _sha256(final_tif), "zip_sha256": _sha256(final_zip),
        "submission": {"file": f"docs/downloads/{final_tif.name}", "zip_file": f"docs/downloads/{final_zip.name}",
                       "submission_name": sub_name, "submission_note": sub_note,
                       "submission_note_chars": len(sub_note), "positive_pixels": int(prod_meta["n_dots"]),
                       "share_gt25": fp_profile["share_gt25"], "share_le2": fp_profile["share_le2"]},
        "ok_to_download": bool(gv["ok_to_download"]), "ok_to_submit": ok_submit_final,
        "gate_verdict": gv, "verdict": verdict,
        "organizer_confirmed_score": None, "weekly_slots_used": 0,
        "vess_meta": vess_meta,
    }
    for p in (ROOT / "registry/vess88_run_card.json", ROOT / "docs/data/vess88_run_card.json"):
        _write_json(p, run_card)
    gv_out = dict(gv)
    gv_out.update({"name": final_stem, "file": f"docs/downloads/{final_tif.name}",
                   "zip_file": f"docs/downloads/{final_zip.name}",
                   "sha256": run_card["raster_sha256"], "zip_sha256": run_card["zip_sha256"],
                   "candidate": {"tif": f"docs/downloads/{final_tif.name}", "zip": f"docs/downloads/{final_zip.name}",
                                 "tif_sha256": run_card["raster_sha256"], "zip_sha256": run_card["zip_sha256"]}})
    for p in (ROOT / "registry/vess88_gate_verdict.json", ROOT / "docs/data/vess88_gate_verdict.json"):
        _write_json(p, gv_out)
    # NOTE: repo-root run_card.json is the frozen GHMD canonical card (synced
    # to docs/data/run_card.json + evidence/run_card.json); never overwrite it.
    print(json.dumps({"candidate": CANDIDATE, "holdout_dti": ov["dti"], "ci95": ov["ci95"],
                      "paired_delta_vs_adhr": paired, "dots": prod_meta["n_dots"],
                      "file": str(final_tif), "sha256": run_card["raster_sha256"],
                      "ok_to_download": gv["ok_to_download"], "ok_to_submit": ok_submit_final,
                      "verdict": verdict}, indent=2), flush=True)


if __name__ == "__main__":
    main()
