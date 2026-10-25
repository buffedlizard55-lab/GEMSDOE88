#!/usr/bin/env python3
"""H88-SDTL hide-and-recover experiment (3 arms, 8 folds) + production surface.

Reuses, unchanged: ``vendor/gems57/holdout.buffered_component_draw`` (split),
``vendor/gems57/evaluate_holdout`` (metric + pooled paired bootstrap),
``vendor/gems57/emit.dinkelbach_allocate`` (dot placement),
``src/gems88/physics`` (shared PHYS-44 cache) and ``src/gems88/adhr``
dual-expectation HistGradientBoosting fitters.  New code is confined to
``src/gems88/sdtl.py`` (features) and this orchestration.

Arms (identical training design, model, emitter and budget rule):
  control_phys44   PHYS-44 only
  candidate_sdtl   PHYS-44 + SDTL-12
  ablation_sdtl    SDTL-12 only

Every catalogue-dependent SDTL feature is rebuilt per seed from the fold's
visible catalogue.  The guard at the top runs the shared preflight; it exits
2 on DUPLICATE_STOP and 1 on an audit error.
"""
from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import emit, evaluate_holdout, grid as grid_mod, holdout  # noqa: E402
from gems88 import adhr, physics, sdtl  # noqa: E402

BLOCK_SIDE = 200
SEEDS = (20, 21)
ARMS = ("control_phys44", "candidate_sdtl", "ablation_sdtl")
CANDIDATE = "candidate_sdtl"
SPACING_PX = 2.05


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sources_for(arm: str, X_phys, X_sdtl):
    if arm == "control_phys44":
        return [X_phys]
    if arm == "candidate_sdtl":
        return [X_phys, X_sdtl]
    if arm == "ablation_sdtl":
        return [X_sdtl]
    raise ValueError(arm)


def canary(X_sdtl, g, folds) -> dict:
    """Single-feature symmetric AUC: withheld positives vs allowed negatives (all 4 fold regions)."""
    fp = g.footprint
    ys, xs = np.nonzero(fp)
    rows = []
    worst = 0.0
    for j, name in enumerate(sdtl.SDTL_FEATURES):
        aucs = []
        for fold in folds:
            allowed = fold["region"] & fp & ~fold["masked_known"]
            sel = allowed[ys, xs]
            y = fold["truth"][ys, xs][sel]
            if y.sum() == 0 or y.sum() == y.size:
                continue
            x = np.asarray(X_sdtl[:, j], np.float64)[sel]
            rng = np.random.default_rng(1000 + j)
            neg = np.flatnonzero(y == 0)
            pos = np.flatnonzero(y == 1)
            if neg.size > 200_000:
                neg = rng.choice(neg, 200_000, replace=False)
            idx = np.concatenate([pos, neg])
            a = roc_auc_score(y[idx], x[idx])
            aucs.append(max(a, 1.0 - a))
        sym = float(np.mean(aucs))
        worst = max(worst, sym)
        rows.append(dict(feature=name, symmetric_auc=sym, per_fold=[float(a) for a in aucs],
                         zero_catalogue=name in sdtl.ZERO_CATALOGUE_FEATURES))
    return dict(evidence_class="HOLDOUT-DTI", evaluator_version=evaluate_holdout.VERSION,
                limit=0.90, max_symmetric_auc=worst, passed=bool(worst <= 0.90),
                features_tested=len(rows), rows=rows)


def fold_predictions(g, X_phys, X_sdtl, fold, folds, seed, fold_i, cache_dir: Path) -> dict:
    fp = g.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    visible = fold["visible"]
    test_region = fold["region"]
    train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != fold_i])
    train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != fold_i])
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("training regions/truth intersect the test region")
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    dom_tr = (train_regions & ~visible)[ys_fp, xs_fp]
    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]
    out = {}
    for arm in ARMS:
        tag = f"seed{seed}_f{fold_i}_{arm}_{sdtl.SDTL_SCHEMA_VERSION}"
        post = cache_dir / f"post_{tag}.npz"
        if post.is_file():
            z = np.load(post)
            p_vec, m_vec = z["p"], z["m"]
        else:
            t0 = time.monotonic()
            clfs, regs = adhr._fit_dual_expectation_models(
                sources_for(arm, X_phys, X_sdtl), dom_tr, train_truth, fp, seed=seed * 100 + fold_i * 7 + 3, n_ensemble=1)
            p_vec, m_vec = adhr._predict_dual_chunked(clfs, regs, sources_for(arm, X_phys, X_sdtl), act_idx)
            del clfs, regs
            gc.collect()
            np.savez_compressed(post, p=p_vec.astype(np.float32), m=m_vec.astype(np.float32))
            print(f"      fit {tag} in {time.monotonic()-t0:.1f}s", flush=True)
        scale = float(k_est) / max(float(p_vec.sum()), 1e-6)
        p_cal = np.clip(p_vec * np.float32(scale), 0.0, 1.0).astype(np.float32)
        m_cal = np.clip(m_vec, p_cal, 1.0).astype(np.float32)
        pg = adhr.scatter_fp(p_cal, ay, ax, g.shape)
        mg = adhr.scatter_fp(m_cal, ay, ax, g.shape)
        alloc = emit.dinkelbach_allocate(pg, mg, allowed, budget=None, k_truth=k_est,
                                         min_spacing_px=SPACING_PX, dinkelbach_iters=6)
        out[arm] = (alloc.emitted.astype(np.float32), int(alloc.n_dots))
    return out


def main() -> int:
    t_start = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_sdtl88.json").read_text())
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("preregistration must be frozen first")
    g = grid_mod.load_grid(ROOT / "data/bridge")
    cache = ROOT / ".cache/gems88_sdtl"
    cache.mkdir(parents=True, exist_ok=True)
    print("[1/5] shared PHYS-44 cache", flush=True)
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, ROOT / ".cache/gems88")
    print("[2/5] zero-catalogue fabric (structure tensors) + per-seed visible-only SDTL features", flush=True)
    fabric = sdtl.load_zero_catalogue_fabric(ROOT, g.footprint)
    folds_by_seed = {}
    X_sdtl_by_seed = {}
    for seed in SEEDS:
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed[seed] = folds
        X_sdtl_by_seed[seed] = sdtl.build_sdtl_fp(fabric, folds[0]["visible"], g.footprint, cache, f"seed{seed}")
    print("[3/5] leakage canary", flush=True)
    can = canary(X_sdtl_by_seed[SEEDS[0]], g, folds_by_seed[SEEDS[0]])
    write_json(ROOT / "evidence/sdtl88_canaries.json", can)
    print(f"      max symmetric AUC {can['max_symmetric_auc']:.4f} (limit 0.90) passed={can['passed']}", flush=True)
    if not can["passed"]:
        raise RuntimeError("LEAKAGE STOP: a single SDTL feature exceeds AUC 0.90")

    print("[4/5] 8-fold hide-and-recover, 3 arms", flush=True)
    terms = {arm: [] for arm in ARMS}
    terms_far = {arm: [] for arm in ARMS}
    fold_rows = []
    for seed in SEEDS:
        folds = folds_by_seed[seed]
        for i, fold in enumerate(folds):
            preds = fold_predictions(g, X_phys, X_sdtl_by_seed[seed], fold, folds, seed, i, cache)
            row = dict(seed=seed, fold=i, name=fold["name"], withheld=int(fold["truth"].sum()))
            d_vis = None
            for arm in ARMS:
                pred, n_dots = preds[arm]
                sc, tm = evaluate_holdout.evaluate(pred, fold, g.footprint, block_side=BLOCK_SIDE)
                terms[arm].append(tm)
                row[arm] = dict(dti=float(sc["dti"]), n_dots=n_dots, tpw=sc["tpw"], fpw=sc["fpw"])
                # far (> 10 px from visible catalogue) sub-population
                if d_vis is None:
                    from scipy import ndimage as ndi
                    d_vis = ndi.distance_transform_edt(~fold["visible"])
                far_fold = dict(fold, region=fold["region"] & (d_vis > 10.0), truth=fold["truth"] & (d_vis > 10.0))
                if far_fold["truth"].any():
                    _, tmf = evaluate_holdout.evaluate(pred, far_fold, g.footprint, block_side=BLOCK_SIDE)
                    terms_far[arm].append(tmf)
            fold_rows.append(row)
            print("      " + " | ".join(f"{arm}={row[arm]['dti']:.4f}({row[arm]['n_dots']})" for arm in ARMS)
                  + f"  [seed {seed} fold {fold['name']} withheld={row['withheld']}]", flush=True)
            gc.collect()
    pooled = evaluate_holdout.pooled_summary({a: np.sum(terms[a], axis=0) for a in ARMS}, candidate=CANDIDATE)
    pooled_far = evaluate_holdout.pooled_summary({a: np.sum(terms_far[a], axis=0) for a in ARMS}, candidate=CANDIDATE)
    won = sum(1 for r in fold_rows if r[CANDIDATE]["dti"] > r["control_phys44"]["dti"])
    payload = dict(schema="gems88.sdtl88.holdout.v1", generated_utc=datetime.now(timezone.utc).isoformat(),
                   preregistration_id=prereg["preregistration_id"], seeds=list(SEEDS), n_folds=len(fold_rows),
                   folds=fold_rows, pooled_overall=pooled, pooled_far_gt10px=pooled_far,
                   folds_won_vs_control=won, elapsed_seconds=time.monotonic() - t_start)
    write_json(ROOT / "evidence/sdtl88_holdout.json", payload)
    c = pooled["scores"][CANDIDATE]
    k = pooled["scores"]["control_phys44"]
    d = pooled["paired_differences"]["control_phys44"]
    print(f"      POOLED candidate={c['dti']:.6f} {c['ci95']} control={k['dti']:.6f} {k['ci95']} "
          f"delta={d['delta']:+.6f} {d['ci95']} folds won {won}/8", flush=True)
    print(f"[5/5] done in {time.monotonic()-t_start:.0f}s; production build is scripts/build_sdtl88_submission.py", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
