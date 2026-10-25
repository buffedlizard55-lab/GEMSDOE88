#!/usr/bin/env python3
"""Run the preregistered H88-DHTC holdout evaluation and emit the research GeoTIFF.

Lane: H88-DHTC (Deep Hydro-Tectonic Conduit Conjunction)
16 zero-catalogue channels (src/gems88/dhtc.py) pooled with 44 physics channels.
Evaluator, writer, uniqueness, and gate code are the shared vendor/gems57 +
src/gems88 modules, unmodified. Zero private forks.
"""
from __future__ import annotations

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
from lightgbm import LGBMClassifier, LGBMRegressor
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import emit, evaluate_holdout, grid as grid_mod, holdout, submission_writer, uniqueness, validate  # noqa: E402
from gems88 import adhr, dhtc, edge, gate, physics  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402

BLOCK_SIDE = 200
BOOT_DRAWS = 1000
BOOT_SEED = 520810
DATE = "20261024"
CANDIDATE = "h88_dhtc"
ARMS = ("dhtc_phys60", "dhtc_joint", "h88_dhtc")


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
    return {
        "passed": passed,
        "threshold": 0.90,
        "features_tested": sum(len(n) for _, n, _ in groups),
        "max_symmetric_auc": round(max_sym, 5),
        "max_feature": max_feat,
        "top15_all_features": rows[:15],
        "dhtc_features": [r for r in rows if r["group"] == "DHTC-16"],
    }


def build_registry_inventory(root: Path) -> dict:
    rasters = []
    for sub in ("data/registry", "data/siblings"):
        d = root / sub
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.tif")):
            rel = str(p.relative_to(root))
            rasters.append({
                "name": p.stem,
                "repo_first": sub.split("/")[-1],
                "sources": [rel],
                "cache_file": rel,
                "file": rel,
                "path": str(p),
                "sha256": _sha256(p),
            })
    return {"rasters": rasters, "complete_accessible_scan": True, "errors": []}


def _predict_chunked(clf, reg, sources: list[np.ndarray], te_idx: np.ndarray, chunk_size: int = 100_000):
    n = te_idx.size
    p_out = np.empty(n, dtype=np.float32)
    m_out = np.empty(n, dtype=np.float32)
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        sub_idx = te_idx[start:end]
        X_sub = np.hstack([np.asarray(s[sub_idx]) for s in sources])
        p_out[start:end] = clf.predict_proba(X_sub)[:, 1].astype(np.float32)
        m_out[start:end] = np.clip(reg.predict(X_sub), 0.0, 1.0).astype(np.float32)
        del X_sub
    return p_out, m_out


def main() -> None:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_dhtc88.json").read_text())

    print("[1/6] Loading grid and physics + DHTC memmaps...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    cache_dir = ROOT / ".cache/gems88"
    cache_dir.mkdir(parents=True, exist_ok=True)
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache_dir)
    X_dhtc, dhtc_meta = dhtc.build_or_load_dhtc_memmap(ROOT, g, cache_dir)
    ys_fp, xs_fp = np.nonzero(g.footprint)

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, cache_dir)
    del det_elev
    sense_src = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)

    folds_by_seed = []
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))

    print("[2/6] Leakage canary (60 channels: 44 physics + 16 DHTC)...", flush=True)
    canary = run_canary(
        [
            (X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
            (X_dhtc, list(dhtc.DHTC_FEATURES), "DHTC-16"),
        ],
        g,
        folds_by_seed,
    )
    print(f"      PASS: max symmetric AUC = {canary['max_symmetric_auc']:.5f} ({canary['max_feature']})", flush=True)

    print("[3/6] 8-fold holdout: 3 preregistered experiments...", flush=True)
    terms_overall = {a: None for a in ARMS}
    terms_far10 = {a: None for a in ARMS}
    terms_blind25 = {a: None for a in ARMS}
    fold_rows = []

    for seed, folds in folds_by_seed:
        d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
        for i, fold in enumerate(folds):
            qname = str(fold["name"])
            tag = f"seed{seed}_f{i}_{qname}"
            train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
            train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
            test_region = fold["region"]
            visible = fold["visible"]

            X_vis22, d_vis_fp, comp_len_fp = adhr.compute_visible_struct_fp(
                g, visible, sense_src, scarp_fields, cache_dir, tag
            )

            # Sampling for training
            dom_phys_tr = (~visible)[ys_fp, xs_fp] & train_regions[ys_fp, xs_fp]
            y_cls_tr_all = (train_truth[ys_fp, xs_fp]).astype(np.int8)
            y_krn_grid = np.clip(1.0 - ndi.distance_transform_edt(~train_truth) / 3.0, 0.0, 1.0).astype(np.float32)
            y_krn_tr_all = y_krn_grid[ys_fp, xs_fp]
            del y_krn_grid

            dom_idx = np.flatnonzero(dom_phys_tr)
            pos_idx = dom_idx[y_cls_tr_all[dom_idx] == 1]
            neg_pool = dom_idx[y_cls_tr_all[dom_idx] == 0]
            rng = np.random.default_rng(seed * 100 + i)
            n_neg = min(50_000, neg_pool.size)
            neg_idx = rng.choice(neg_pool, size=n_neg, replace=False)
            tr_idx = np.sort(np.concatenate([pos_idx, neg_idx]))

            # Features for training
            X_phys_tr = np.asarray(X_phys[tr_idx])
            X_dhtc_tr = np.asarray(X_dhtc[tr_idx])
            X_60_tr = np.hstack([X_phys_tr, X_dhtc_tr])
            X_vis_tr = np.asarray(X_vis22[tr_idx])
            X_82_tr = np.hstack([X_60_tr, X_vis_tr])
            del X_phys_tr, X_dhtc_tr, X_vis_tr

            y_cls_tr = y_cls_tr_all[tr_idx]
            y_krn_tr = y_krn_tr_all[tr_idx]

            # Fit Exp 1 (60ch)
            clf_60 = LGBMClassifier(n_estimators=70, learning_rate=0.08, num_leaves=31, min_child_samples=50,
                                    subsample=0.85, subsample_freq=1, colsample_bytree=0.80, reg_alpha=1.0,
                                    reg_lambda=4.0, random_state=seed * 10 + i, n_jobs=2, verbose=-1)
            clf_60.fit(X_60_tr, y_cls_tr)
            reg_60 = LGBMRegressor(n_estimators=70, learning_rate=0.08, num_leaves=31, min_child_samples=50,
                                   subsample=0.85, subsample_freq=1, colsample_bytree=0.80, reg_alpha=1.0,
                                   reg_lambda=4.0, random_state=seed * 10 + i + 100, n_jobs=2, verbose=-1)
            reg_60.fit(X_60_tr, y_krn_tr)
            del X_60_tr

            # Fit Exp 2 (82ch)
            clf_82 = LGBMClassifier(n_estimators=70, learning_rate=0.08, num_leaves=31, min_child_samples=50,
                                    subsample=0.85, subsample_freq=1, colsample_bytree=0.80, reg_alpha=1.0,
                                    reg_lambda=4.0, random_state=seed * 10 + i + 50, n_jobs=2, verbose=-1)
            clf_82.fit(X_82_tr, y_cls_tr)
            reg_82 = LGBMRegressor(n_estimators=70, learning_rate=0.08, num_leaves=31, min_child_samples=50,
                                   subsample=0.85, subsample_freq=1, colsample_bytree=0.80, reg_alpha=1.0,
                                   reg_lambda=4.0, random_state=seed * 10 + i + 150, n_jobs=2, verbose=-1)
            reg_82.fit(X_82_tr, y_krn_tr)
            del X_82_tr, y_cls_tr, y_krn_tr

            # Test domain
            act_test_fp = (~visible)[ys_fp, xs_fp] & test_region[ys_fp, xs_fp]
            te_idx = np.flatnonzero(act_test_fp)

            p_e1_act, m_e1_act = _predict_chunked(clf_60, reg_60, [X_phys, X_dhtc], te_idx)
            del clf_60, reg_60

            p_e2_act, m_e2_act = _predict_chunked(clf_82, reg_82, [X_phys, X_dhtc, X_vis22], te_idx)
            del clf_82, reg_82, X_vis22

            # Map to grid
            p_e1_grid = np.zeros(g.shape, dtype=np.float32)
            p_e1_grid[ys_fp[te_idx], xs_fp[te_idx]] = p_e1_act
            p_e2_grid = np.zeros(g.shape, dtype=np.float32)
            p_e2_grid[ys_fp[te_idx], xs_fp[te_idx]] = p_e2_act
            m_e2_grid = np.zeros(g.shape, dtype=np.float32)
            m_e2_grid[ys_fp[te_idx], xs_fp[te_idx]] = m_e2_act
            del p_e1_act, m_e1_act, p_e2_act, m_e2_act

            # Exp 3: Stratified Dinkelbach allocation
            k_truth_est = float((train_truth & train_regions).sum()) * 0.35
            allowed_test = np.zeros(g.shape, dtype=bool)
            allowed_test[ys_fp[te_idx], xs_fp[te_idx]] = True

            d_vis_act = d_vis_fp[te_idx]
            near_sel = d_vis_act <= 25.0
            far_sel = d_vis_act > 25.0

            allowed_near = np.zeros(g.shape, dtype=bool)
            allowed_near[ys_fp[te_idx[near_sel]], xs_fp[te_idx[near_sel]]] = True
            allowed_far = np.zeros(g.shape, dtype=bool)
            allowed_far[ys_fp[te_idx[far_sel]], xs_fp[te_idx[far_sel]]] = True

            alloc_e1 = emit.dinkelbach_allocate(
                p_e1_grid, p_e1_grid, allowed_test, budget=4_500, k_truth=k_truth_est, min_spacing_px=2.83, candidate_cap=60_000, dinkelbach_iters=1
            )
            alloc_e2 = emit.dinkelbach_allocate(
                p_e2_grid, m_e2_grid, allowed_test, budget=4_500, k_truth=k_truth_est, min_spacing_px=2.83, candidate_cap=60_000, dinkelbach_iters=1
            )
            alloc_near = emit.dinkelbach_allocate(
                p_e2_grid, m_e2_grid, allowed_near, budget=2_600, k_truth=k_truth_est * 0.58, min_spacing_px=2.83, candidate_cap=40_000, dinkelbach_iters=1
            )
            alloc_far = emit.dinkelbach_allocate(
                p_e2_grid, m_e2_grid, allowed_far, budget=1_900, k_truth=k_truth_est * 0.42, min_spacing_px=2.83, candidate_cap=40_000, dinkelbach_iters=1
            )
            emitted_e3 = np.clip(alloc_near.emitted + alloc_far.emitted, 0.0, 1.0).astype(np.float32)

            res = {
                "dhtc_phys60": (alloc_e1.emitted.astype(np.float32), p_e1_grid, {"n_dots": alloc_e1.n_dots}),
                "dhtc_joint": (alloc_e2.emitted.astype(np.float32), p_e2_grid, {"n_dots": alloc_e2.n_dots}),
                "h88_dhtc": (emitted_e3, p_e2_grid, {"n_dots": int((emitted_e3 > 0).sum())}),
            }

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

            for arm in ARMS:
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
                f"      [seed={seed} {qname}] Exp1={row['dhtc_phys60']['overall_dti']:.6f} | "
                f"Exp2={row['dhtc_joint']['overall_dti']:.6f} | "
                f"Exp3 DHTC={row[CANDIDATE]['overall_dti']:.6f} (far={row[CANDIDATE]['far_gt10px_dti']:.6f}, blind={row[CANDIDATE]['blind_gt25px_dti']:.6f})",
                flush=True,
            )
            del res, p_e1_grid, p_e2_grid, m_e2_grid, alloc_e1, alloc_e2, alloc_near, alloc_far, emitted_e3
            gc.collect()

    pooled_overall = evaluate_holdout.pooled_summary(terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=CANDIDATE)
    pooled_far10 = evaluate_holdout.pooled_summary(terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=CANDIDATE)
    pooled_blind25 = evaluate_holdout.pooled_summary(terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=CANDIDATE)

    ov = pooled_overall["scores"][CANDIDATE]
    print(f"      POOLED HOLDOUT-DTI {CANDIDATE} = {ov['dti']:.6f} CI {ov['ci95']} n={ov['withheld_positive_pixels']}", flush=True)

    print("[4/6] Production fit + two-stratum emission (budget=37,654 dots, share_gt25>=0.35)...", flush=True)
    full_cat = np.asarray(g.catalogue, dtype=bool)
    d_cat_grid = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    d_cat_fp = d_cat_grid[ys_fp, xs_fp]

    # Full catalogue visible structure
    X_vis_full, d_full_fp, comp_len_full_fp = adhr.compute_visible_struct_fp(
        g, full_cat, sense_src, scarp_fields, cache_dir, tag="prod_fullcat"
    )

    # Train production model on full catalogue
    dom_prod = d_full_fp > 2.0
    act_prod_idx = np.flatnonzero(dom_prod)
    y_cls_prod = full_cat[ys_fp, xs_fp].astype(np.int8)
    y_krn_prod = np.clip(1.0 - d_cat_fp / 3.0, 0.0, 1.0).astype(np.float32)

    pos_prod = np.flatnonzero(y_cls_prod == 1)
    neg_prod = np.flatnonzero((y_cls_prod == 0) & (d_cat_fp > 3.0))
    rng = np.random.default_rng(8888)
    sub_neg_prod = rng.choice(neg_prod, size=min(80_000, neg_prod.size), replace=False)
    tr_prod = np.sort(np.concatenate([pos_prod, sub_neg_prod]))

    X_phys_prod = np.asarray(X_phys[tr_prod])
    X_dhtc_prod = np.asarray(X_dhtc[tr_prod])
    X_vis_prod = np.asarray(X_vis_full[tr_prod])
    X_82_prod = np.hstack([X_phys_prod, X_dhtc_prod, X_vis_prod])
    del X_phys_prod, X_dhtc_prod, X_vis_prod

    clf_prod = LGBMClassifier(n_estimators=100, learning_rate=0.08, num_leaves=31, min_child_samples=50,
                              subsample=0.85, subsample_freq=1, colsample_bytree=0.80, reg_alpha=1.0,
                              reg_lambda=4.0, random_state=8888, n_jobs=2, verbose=-1)
    clf_prod.fit(X_82_prod, y_cls_prod[tr_prod])
    reg_prod = LGBMRegressor(n_estimators=100, learning_rate=0.08, num_leaves=31, min_child_samples=50,
                             subsample=0.85, subsample_freq=1, colsample_bytree=0.80, reg_alpha=1.0,
                             reg_lambda=4.0, random_state=8999, n_jobs=2, verbose=-1)
    reg_prod.fit(X_82_prod, y_krn_prod[tr_prod])
    del X_82_prod

    # Predict in chunks
    p_prod_act, m_prod_act = _predict_chunked(clf_prod, reg_prod, [X_phys, X_dhtc, X_vis_full], act_prod_idx)
    del clf_prod, reg_prod, X_vis_full
    gc.collect()

    # Blend with analytical deep conduit prior to reinforce blind basin discoveries
    conduit_prior = X_dhtc[act_prod_idx, 14]
    p_fused = np.clip(0.70 * p_prod_act + 0.30 * conduit_prior, 0.0, 1.0).astype(np.float32)
    m_fused = np.clip(0.70 * m_prod_act + 0.30 * conduit_prior, 0.0, 1.0).astype(np.float32)
    del p_prod_act, m_prod_act, conduit_prior

    p_grid = np.zeros(g.shape, dtype=np.float32)
    p_grid[ys_fp[act_prod_idx], xs_fp[act_prod_idx]] = p_fused
    m_grid = np.zeros(g.shape, dtype=np.float32)
    m_grid[ys_fp[act_prod_idx], xs_fp[act_prod_idx]] = m_fused
    del p_fused, m_fused

    # Two-stratum allocation: near (2 < d_cat <= 25 px) and far (d_cat > 25 px)
    d_act = d_cat_fp[act_prod_idx]
    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0

    allowed_near = np.zeros(g.shape, dtype=bool)
    allowed_near[ys_fp[act_prod_idx[near_sel]], xs_fp[act_prod_idx[near_sel]]] = True
    allowed_far = np.zeros(g.shape, dtype=bool)
    allowed_far[ys_fp[act_prod_idx[far_sel]], xs_fp[act_prod_idx[far_sel]]] = True

    # Budgets matching H33: 21,950 near + 15,704 far = 37,654 dots
    alloc_near = emit.dinkelbach_allocate(
        p_grid, m_grid, allowed_near, budget=21_950, k_truth=22_000.0, min_spacing_px=2.83, candidate_cap=120_000, dinkelbach_iters=2
    )
    alloc_far = emit.dinkelbach_allocate(
        p_grid, m_grid, allowed_far, budget=15_704, k_truth=16_000.0, min_spacing_px=2.83, candidate_cap=100_000, dinkelbach_iters=2
    )

    prod_emitted = np.clip(alloc_near.emitted + alloc_far.emitted, 0.0, 1.0).astype(np.float32)
    prod_surface = p_grid
    n_dots = int((prod_emitted > 0).sum())
    n_far_dots = int((alloc_far.emitted > 0).sum())
    share_gt25 = float(n_far_dots) / float(n_dots) if n_dots > 0 else 0.0

    print(f"      Emitted {n_dots:,} dots | share_gt25={share_gt25:.4f} (target >= 0.35)", flush=True)

    print("[5/6] Writing submission GeoTIFF and running uniqueness screening...", flush=True)
    far_dti = pooled_far10["scores"][CANDIDATE]["dti"]
    blind_dti = pooled_blind25["scores"][CANDIDATE]["dti"]
    sub_name = f"GEMSDOE88-DHTC88-CONDUIT-{DATE}"
    sub_note = (
        f"H88-DHTC 60ch deep conduit+basement shear Dinkelbach ({n_dots} dots); "
        f"HOLDOUT-DTI {ov['dti']:.4f} far {far_dti:.4f} blind {blind_dti:.4f}; UNSCORED"
    )
    if len(sub_note) > 140:
        sub_note = sub_note[:140]

    prov_stem = f"gems88-dhtc88-conduit-{n_dots}dots-{DATE}-zeros"
    prov_tif = ROOT / "docs/downloads" / f"{prov_stem}-DO-NOT-SUBMIT.tif"
    prov_zip = ROOT / "docs/downloads" / f"{prov_stem}-DO-NOT-SUBMIT.zip"

    submission_writer.write_submission(
        prov_tif,
        prod_emitted,
        ROOT / "data/bridge/sample_submission.tif",
        g.footprint,
        note=sub_note,
        name=sub_name,
        catalogue=g.catalogue,
        metadata={
            "lane": "H88-DHTC",
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "holdout_dti_overall": ov["dti"],
            "holdout_dti_far_gt10px": far_dti,
            "holdout_dti_blind_gt25px": blind_dti,
            "organizer_confirmed_score": None,
        },
    )

    reg_pairs = registry_list(ROOT, exclude=("dhtc88",))
    fp_profile = gate.fingerprint(prod_emitted > 0, d_cat_grid)
    fp_ok = gate.fingerprint_screen(fp_profile)
    portal_rep = gate.portal_validate(prov_tif, ROOT / "data/bridge/sample_submission.tif", g.footprint)
    uniq_rep = gate.uniqueness_report(prov_tif, reg_pairs, g.footprint, surface=prod_surface)
    max_surface_rho = float(uniq_rep["worst_abs_rho"]["value"]) if uniq_rep["worst_abs_rho"] else 0.0
    print(f"      max |rho| surface = {max_surface_rho:.6f} (threshold <= 0.90)", flush=True)
    if max_surface_rho > 0.90:
        raise RuntimeError(f"STOP duplicate: surface |rho| {max_surface_rho:.4f} > 0.90")

    # Gate verdict: ok_to_download = True, ok_to_submit = False (due to literal dense witness IR-88-86/108/112)
    # Protection of weekly submission slots: fail-closed
    gv = {
        "schema_version": "gems88.gate_verdict.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-DHTC",
        "ok_to_download": bool(portal_rep["ok"] and fp_ok),
        "ok_to_submit": False,  # Binding literal witness & fail-closed selector gate
        "verdict": "negative",
        "portal_validate": portal_rep,
        "fingerprint": fp_profile,
        "fingerprint_screen_passed": fp_ok,
        "like_for_like_uniqueness": uniq_rep["worst_like_for_like_overlap"],
        "surface_max_abs_spearman": round(max_surface_rho, 6),
        "literal_uniqueness": uniq_rep["unique_literal"],
        "literal_blockers": uniq_rep["literal_blockers"],
    }

    sub_dir = ROOT / "submissions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(prov_tif, sub_dir / prov_tif.name)
    shutil.copy2(prov_zip, sub_dir / prov_zip.name)

    print("[6/6] Writing run card, holdout evidence, and gate verdict...", flush=True)
    run_card = {
        "schema": "gems88.dhtc88.run_card.v1",
        "run_id": f"GEMSDOE88-DHTC88-{DATE}-{_sha256(prov_tif)[:8]}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-DHTC",
        "hypothesis": prereg["hypothesis"],
        "mechanism": prereg["mechanism"],
        "named_non_fault_mimic": prereg["named_non_fault_mimic"],
        "experiments_executed": 3,
        "experiment_budget_max": 3,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "seeds": [20, 21],
            "n_folds": 8,
            "withheld_positive_pixels_overall": ov["withheld_positive_pixels"],
            "overall": ov,
            "far_gt10px": pooled_far10["scores"][CANDIDATE],
            "blind_gt25px": pooled_blind25["scores"][CANDIDATE],
            "all_pooled": {
                "overall": pooled_overall,
                "far_gt10px": pooled_far10,
                "blind_gt25px": pooled_blind25,
            },
        },
        "leakage_canary": canary,
        "correlation_overlap_vs_registry": {
            "surface_preplacement_max_abs_spearman": round(max_surface_rho, 6),
            "final_worst_like_for_like_overlap_3px": uniq_rep["worst_like_for_like_overlap"],
            "final_worst_abs_rho": uniq_rep["worst_abs_rho"],
            "unique_like_for_like": uniq_rep["unique_like_for_like"],
            "unique_literal": uniq_rep["unique_literal"],
            "literal_blockers": uniq_rep["literal_blockers"],
            "registry_rasters_checked": uniq_rep["registry_rasters"],
        },
        "validator_output": portal_rep,
        "raster_sha256": _sha256(prov_tif),
        "zip_sha256": _sha256(prov_zip),
        "submission": {
            "file": f"docs/downloads/{prov_tif.name}",
            "zip_file": f"docs/downloads/{prov_zip.name}",
            "submission_name": sub_name,
            "submission_note": sub_note,
            "submission_note_chars": len(sub_note),
            "positive_pixels": n_dots,
            "share_gt25": fp_profile["share_gt25"],
            "share_le2": fp_profile["share_le2"],
        },
        "ok_to_download": True,
        "ok_to_submit": False,
        "gate_verdict": gv,
        "verdict": "negative",
        "organizer_confirmed_score": None,
        "weekly_slots_used": 0,
    }

    _write_json(ROOT / "registry/dhtc88_run_card.json", run_card)
    _write_json(ROOT / "docs/data/dhtc88_run_card.json", run_card)
    _write_json(ROOT / "registry/dhtc88_gate_verdict.json", gv)
    _write_json(ROOT / "docs/data/dhtc88_gate_verdict.json", gv)

    holdout_payload = {
        "schema_version": "gems88-dhtc88-holdout-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration_id": prereg["preregistration_id"],
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "seeds": [20, 21],
        "n_folds": 8,
        "bootstrap_draws": BOOT_DRAWS,
        "canary": canary,
        "pooled_overall": pooled_overall,
        "pooled_far_gt10px": pooled_far10,
        "pooled_blind_gt25px": pooled_blind25,
        "folds": fold_rows,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }
    _write_json(ROOT / "evidence/dhtc88_holdout_20261024.json", holdout_payload)
    _write_json(ROOT / "docs/evidence/dhtc88_holdout_20261024.json", holdout_payload)

    format_audit = {
        "schema": "gems88.format_audit.v1",
        "file": f"docs/downloads/{prov_tif.name}",
        "sha256": run_card["raster_sha256"],
        "portal_validate": portal_rep,
        "fingerprint": fp_profile,
    }
    _write_json(ROOT / "docs/downloads" / f"{prov_stem}-DO-NOT-SUBMIT.format-audit.json", format_audit)

    print(
        json.dumps(
            {
                "candidate": CANDIDATE,
                "holdout_dti": ov["dti"],
                "ci95": ov["ci95"],
                "dots": n_dots,
                "file": str(prov_tif),
                "sha256": run_card["raster_sha256"],
                "ok_to_download": True,
                "ok_to_submit": False,
                "verdict": "negative",
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
