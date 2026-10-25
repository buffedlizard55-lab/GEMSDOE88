#!/usr/bin/env python3
"""H88-LSC lane runner: canary -> 8-cell holdout (arm A vs ablation B) -> spacing
policy -> production build -> registry uniqueness -> validation -> run card.

Shared tools only: vendor/gems57 (holdout, evaluate_holdout, metric, submission
writer, validate) and src/gems88 (registry list, shared Poisson-disc emitter).
Preregistration: registry/preregistration_lsc88.json (frozen before any run).
"""
from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from lightgbm import LGBMClassifier
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import evaluate_holdout, grid as grid_mod, holdout, submission_writer, validate  # noqa: E402
from gems88 import lsc  # noqa: E402
from gems88.models_and_alloc import emit_poisson_disk_nms  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402

LANE = "H88-LSC"
DATE = "20261025"
BUDGET = 40_000
COLLAR_PX = 3.0
SPACING_PX = 2.8
BLOCK_SIDE = 200
BOOT_DRAWS = 1000
BOOT_SEED = 520810
SEEDS = (20, 21)
EVID = ROOT / "evidence"
CACHE = ROOT / ".cache/gems88_lsc"
LGBM = dict(n_estimators=250, learning_rate=0.05, num_leaves=63, min_child_samples=200,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
            n_jobs=2, verbose=-1, random_state=88)
N_NEG = 500_000


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wjson(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


# --------------------------------------------------------------------------- model
def fit(X, rows_pos, rows_neg, cols, rng):
    pos = X[np.sort(rows_pos)][:, cols]
    neg = X[np.sort(rows_neg)][:, cols]
    Xt = np.vstack([pos, neg]).astype(np.float32)
    yt = np.r_[np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)]
    spw = min(10.0, max(1.0, len(neg) / max(1, len(pos)) / 4.0))
    m = LGBMClassifier(scale_pos_weight=spw, **LGBM)
    m.fit(Xt, yt)
    return m


def predict_rows(model, X, rows, cols, chunk=400_000):
    out = np.empty(len(rows), np.float32)
    for s in range(0, len(rows), chunk):
        r = rows[s:s + chunk]
        out[s:s + chunk] = model.predict_proba(X[r][:, cols])[:, 1]
    return out


def emit(surface, allowed, n_dots, spacing=SPACING_PX, adaptive=False):
    if not adaptive:
        return emit_poisson_disk_nms(surface, allowed, n_dots=n_dots, min_dist_px=spacing) > 0
    # adaptive: first half of the budget at 2.8 px, remainder at 4.0 px around them
    half = n_dots // 2
    first = emit_poisson_disk_nms(surface, allowed, n_dots=half, min_dist_px=spacing) > 0
    block = ndi.distance_transform_edt(~first) < 4.0
    second = emit_poisson_disk_nms(surface, allowed & ~block, n_dots=n_dots - half, min_dist_px=4.0) > 0
    return first | second


# --------------------------------------------------------------------------- main
def main() -> int:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_lsc88.json").read_text())
    assert prereg["frozen_before_feature_canary_holdout_or_production_build"] is True
    g = grid_mod.load_grid(ROOT / "data/bridge")
    fp = g.footprint
    ys, xs = np.nonzero(fp)
    n_fp = ys.size
    idx_grid = np.full(fp.shape, -1, np.int64)
    idx_grid[ys, xs] = np.arange(n_fp)
    log(f"grid ok: footprint={n_fp} catalogue={int(g.catalogue.sum())}")

    X, meta = lsc.build_or_load(ROOT, fp, CACHE)
    feats = list(lsc.FEATURES)
    cols_A = list(range(len(feats)))
    cols_B = [feats.index(f) for f in lsc.ORGANIZER_ONLY]
    log(f"features ready: {X.shape} schema={meta['schema']}")

    quad = holdout.quadrant_ids(fp)
    folds_by_seed = {s: holdout.buffered_component_draw(g, seed=s, hide_frac=0.20, buffer_px=3,
                                                        boundary_px=12)[0] for s in SEEDS}
    rng = np.random.default_rng(880)

    # ---------------------------------------------------------------- EXP1a canary
    canary_p = EVID / "lsc88_canaries.json"
    if canary_p.exists():
        canary = json.loads(canary_p.read_text())
    else:
        log("EXP1a single-feature leakage canary")
        truth_rows, neg_rows = [], []
        for s in SEEDS:
            for f in folds_by_seed[s]:
                reg = f["region"] & fp & ~f["masked_known"]
                truth_rows.append(idx_grid[f["truth"] & reg])
                cand = idx_grid[reg & ~f["truth"]]
                neg_rows.append(rng.choice(cand, size=min(60_000, cand.size), replace=False))
        tr = np.unique(np.concatenate(truth_rows))
        ng = np.unique(np.concatenate(neg_rows))
        Xa = X[tr]
        Xb = X[ng]
        y = np.r_[np.ones(len(tr)), np.zeros(len(ng))]
        rows = []
        for j, name in enumerate(feats):
            v = np.r_[Xa[:, j], Xb[:, j]]
            auc = float(roc_auc_score(y, v))
            rows.append({"feature": name, "auc": auc, "symmetric_auc": max(auc, 1 - auc)})
        mx = max(rows, key=lambda r: r["symmetric_auc"])
        canary = {"evidence_class": "LEAKAGE-CANARY", "withheld_positive_pixels": int(len(tr)),
                  "negatives": int(len(ng)), "features_tested": len(rows), "limit": 0.90,
                  "max_symmetric_auc": mx["symmetric_auc"], "max_feature": mx["feature"],
                  "passed": bool(mx["symmetric_auc"] <= 0.90), "rows": rows}
        wjson(canary_p, canary)
        del Xa, Xb
    log(f"canary: {canary['features_tested']} features, max sym AUC {canary['max_symmetric_auc']:.4f} "
        f"on {canary['max_feature']} -> {'PASS' if canary['passed'] else 'FAIL'}")
    if not canary["passed"]:
        log("STOP: leakage canary failed")
        return 2

    # ---------------------------------------------------------------- EXP1b/EXP2 holdout
    hold_p = EVID / "lsc88_holdout.json"
    if hold_p.exists() and "--recompute-holdout" not in sys.argv:
        hold = json.loads(hold_p.read_text())
    else:
        arms = ["lsc_A_uniform", "lsc_A_adaptive", "org19_B_uniform"]
        terms = {k: {a: None for a in arms} for k in ("overall", "far10", "blind25")}
        cells = []
        for s in SEEDS:
            folds = folds_by_seed[s]
            vis = folds[0]["visible"]
            d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
            for q, fold in enumerate(folds):
                tc = time.monotonic()
                train_mask = fp & (quad != q) & (quad >= 0)
                pos_rows = idx_grid[train_mask & vis]
                neg_cand = idx_grid[train_mask & (d_vis > COLLAR_PX)]
                neg_rows = rng.choice(neg_cand, size=min(N_NEG, neg_cand.size), replace=False)
                test_rows = idx_grid[fp & (quad == q)]
                region = fold["region"]
                allowed = region & fp & (d_vis > COLLAR_PX) & ~fold["masked_known"]
                n_dots = int(round(BUDGET * region[fp].sum() / n_fp))
                far_truth = fold["truth"] & region & ~fold["masked_known"] & (d_vis > 10.0)
                far_valid = fp & region & ~fold["masked_known"] & (d_vis > 10.0)
                blind_truth = fold["truth"] & region & ~fold["masked_known"] & (d_vis > 25.0)
                blind_valid = fp & region & ~fold["masked_known"] & (d_vis > 25.0)
                cell = {"seed": s, "fold": fold["name"], "n_dots": n_dots,
                        "withheld_positive_pixels": int((fold["truth"] & region).sum()),
                        "far": int(far_truth.sum()), "blind": int(blind_truth.sum()), "arms": {}}
                surfaces = {}
                for arm_name, cols in (("A", cols_A), ("B", cols_B)):
                    model = fit(X, pos_rows, neg_rows, cols, rng)
                    p = np.zeros(fp.shape, np.float32)
                    p[fp & (quad == q)] = predict_rows(model, X, test_rows, cols)
                    surfaces[arm_name] = p
                    del model
                for arm in arms:
                    p = surfaces["A" if arm.startswith("lsc") else "B"]
                    em = emit(p, allowed, n_dots, adaptive=arm.endswith("adaptive")).astype(np.float32)
                    res = {}
                    for key, tr_, va_ in (("overall", None, None), ("far10", far_truth, far_valid),
                                          ("blind25", blind_truth, blind_valid)):
                        fd = fold if tr_ is None else {**fold, "truth": tr_, "region": va_,
                                                       "masked_known": np.zeros_like(va_)}
                        if not (fd["truth"] & fd["region"]).any():
                            res[key] = None
                            continue
                        sc, bt = evaluate_holdout.evaluate(em, fd, fp, block_side=BLOCK_SIDE)
                        terms[key][arm] = bt if terms[key][arm] is None else terms[key][arm] + bt
                        res[key] = round(float(sc["dti"]), 6)
                    res["emitted"] = int(em.sum())
                    cell["arms"][arm] = res
                cells.append(cell)
                log(f"seed {s} fold {fold['name']}: n_dots={n_dots} truth={cell['withheld_positive_pixels']} "
                    + " ".join(f"{a}={cell['arms'][a]['overall']}/{cell['arms'][a]['far10']}/{cell['arms'][a]['blind25']}" for a in arms)
                    + f" ({time.monotonic() - tc:.0f}s)")
                del surfaces
                gc.collect()
        pooled = {}
        for i, key in enumerate(("overall", "far10", "blind25")):
            pooled[key] = evaluate_holdout.pooled_summary(terms[key], draws=BOOT_DRAWS, seed=BOOT_SEED + i,
                                                          candidate="lsc_A_uniform")
        hold = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                "budget_rule": f"{BUDGET} x region_cells / {n_fp}", "collar_px": COLLAR_PX,
                "spacing_px": SPACING_PX, "cells": cells, "pooled": pooled}
        wjson(hold_p, hold)
    for key in ("overall", "far10", "blind25"):
        sc = hold["pooled"][key]["scores"]
        pdiff = hold["pooled"][key]["paired_differences"]
        log(f"HOLDOUT {key}: " + "; ".join(f"{a}={v['dti']:.4f} [{v['ci95'][0]:.4f},{v['ci95'][1]:.4f}] n={v['withheld_positive_pixels']}" for a, v in sc.items()))
        log(f"   paired dA-uniform minus: " + "; ".join(f"{a}: {d['delta']:+.4f} [{d['ci95'][0]:+.4f},{d['ci95'][1]:+.4f}]" for a, d in pdiff.items()))
    ov = hold["pooled"]["overall"]
    far = hold["pooled"]["far10"]
    dA_B = ov["paired_differences"]["org19_B_uniform"]
    dA_B_far = far["paired_differences"]["org19_B_uniform"]
    lane_pass = dA_B["ci95"][0] > 0 and dA_B_far["ci95"][0] > 0
    adaptive_better = ov["scores"]["lsc_A_adaptive"]["dti"] > ov["scores"]["lsc_A_uniform"]["dti"]
    log(f"EXP1 decision: lidar arm beats organizer-only arm with CI>0 on overall AND far: {lane_pass}")
    log(f"EXP2 decision: adaptive spacing better than uniform: {adaptive_better}")
    if "--holdout-only" in sys.argv:
        return 0

    # ---------------------------------------------------------------- EXP3 production
    log("EXP3 production fit on the full visible catalogue")
    d_cat = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    pos_rows = idx_grid[fp & g.catalogue]
    neg_cand = idx_grid[fp & (d_cat > COLLAR_PX)]
    neg_rows = rng.choice(neg_cand, size=min(N_NEG, neg_cand.size), replace=False)
    model = fit(X, pos_rows, neg_rows, cols_A, rng)
    imp = sorted(zip(feats, model.feature_importances_.tolist()), key=lambda t: -t[1])
    p_full = np.zeros(fp.shape, np.float32)
    p_full[ys, xs] = predict_rows(model, X, np.arange(n_fp), cols_A)
    allowed = fp & (d_cat > COLLAR_PX) & ~g.catalogue
    dots = emit(p_full, allowed, BUDGET, adaptive=adaptive_better)
    n_dots = int(dots.sum())
    dd = d_cat[dots]
    fingerprint = {"dots": n_dots, "share_le2": float((dd <= 2).mean()), "share_gt25": float((dd > 25).mean()),
                   "median_d_cat_px": float(np.median(dd)), "min_d_cat_px": float(dd.min()),
                   "on_catalogue": int((dots & g.catalogue).sum()), "outside_footprint": int((dots & ~fp).sum())}
    log(f"production: dots={n_dots} fingerprint={fingerprint}")
    np.save(CACHE / "p_full.npy", p_full)

    # ---------------------------------------------------------------- uniqueness
    log("registry uniqueness (like-for-like dots; top-k/top-2% for dense rasters)")
    reg = registry_list(ROOT, exclude=("lsc88",))
    dots_yx = np.nonzero(dots)
    sub = rng.choice(n_fp, size=300_000, replace=False)
    mine_sub = p_full[ys[sub], xs[sub]]
    rows = []
    worst_overlap, worst_rho = 0.0, 0.0
    for label, path in reg:
        try:
            with rasterio.open(path) as src:
                if (src.height, src.width) != fp.shape:
                    rows.append({"registry": label, "skipped": "shape mismatch"}); continue
                a = src.read(1).astype(np.float32)
        except Exception as exc:  # unreadable registry member is recorded, not hidden
            rows.append({"registry": label, "skipped": str(exc)[:80]}); continue
        a[~np.isfinite(a)] = 0.0
        a[~fp] = 0.0
        pos = a > 0
        n_pos = int(pos.sum())
        dense = n_pos > 0.10 * n_fp
        defs = {}
        if not dense:
            defs["positive_cells"] = pos
        else:
            vals = a[fp]
            for name, k in (("top_k", n_dots), ("top_2pct", int(0.02 * n_fp))):
                thr = np.partition(vals, -k)[-k]
                defs[name] = (a >= thr) & fp
        best = {}
        for name, their in defs.items():
            if their.sum() == 0:
                best[name] = 0.0; continue
            near = ndi.distance_transform_edt(~their) <= 3.0
            best[name] = float(near[dots_yx].mean())
        ov_val = max(best.values())
        rho = float(abs(spearmanr(mine_sub, a[ys[sub], xs[sub]]).statistic)) if a[ys[sub], xs[sub]].std() > 0 else 0.0
        rows.append({"registry": label, "their_positive_cells": n_pos, "dense": dense,
                     "forward_overlap_3px": {k: round(v, 6) for k, v in best.items()},
                     "binding_overlap": round(ov_val, 6), "abs_spearman": round(rho, 6)})
        worst_overlap, worst_rho = max(worst_overlap, ov_val), max(worst_rho, rho)
    uniq = {"rasters_checked": len(rows), "worst_overlap": worst_overlap, "worst_abs_spearman": worst_rho,
            "overlap_limit": 0.70, "rho_limit": 0.90,
            "passed": bool(worst_overlap <= 0.70 and worst_rho <= 0.90), "rows": rows}
    wjson(EVID / "lsc88_uniqueness.json", uniq)
    log(f"uniqueness: {len(rows)} rasters, worst overlap {worst_overlap:.4f}, worst |rho| {worst_rho:.4f} -> "
        f"{'PASS' if uniq['passed'] else 'FAIL'}")

    # ---------------------------------------------------------------- write TIFF
    fingerprint_pass = fingerprint["share_le2"] == 0.0 and fingerprint["share_gt25"] >= 0.35
    ok = bool(lane_pass and uniq["passed"] and fingerprint_pass)
    pred = np.where(dots, 1.0, 0.0).astype(np.float32)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    tag = "" if ok else "-DO-NOT-SUBMIT"
    stem = f"gems88-lsc88-lidarstep-{n_dots}dots-{stamp}-{short}-zeros{tag}"
    out = ROOT / "docs/downloads" / f"{stem}.tif"
    name = f"GEMSDOE88-LSC88-{short.upper()}"
    o = ov["scores"]["lsc_A_adaptive" if adaptive_better else "lsc_A_uniform"]
    note = (f"H88-LSC lidar step-couplet GBM, 3px collar, {'adaptive' if adaptive_better else '2.8px'} carpet, "
            f"{n_dots}d; HOLDOUT-DTI {o['dti']:.4f} far {far['scores']['lsc_A_uniform']['dti']:.4f}; UNSCORED")[:140]
    receipt = submission_writer.write_submission(out, pred, ROOT / "data/bridge/sample_submission.tif", fp,
                                                 note=note, name=name, catalogue=g.catalogue)
    val = validate.validate(out, fp, g.catalogue)
    validate.assert_submittable(val)
    log(f"written {out.name} sha256={val['sha256']} checks={val['all_checks_passed']}")

    card = {
        "lane": LANE, "generated_utc": stamp, "hypothesis": prereg["hypothesis"], "mechanism": prereg["mechanism"],
        "named_non_fault_mimics": prereg["named_non_fault_mimics"],
        "features": feats, "feature_importance_top15": imp[:15],
        "leakage_canary": {k: canary[k] for k in ("features_tested", "max_symmetric_auc", "max_feature", "passed")},
        "holdout": {"evaluator_version": hold["evaluator_version"], "pooled": hold["pooled"],
                    "exp1_lane_pass": lane_pass, "exp2_adaptive_better": adaptive_better},
        "fingerprint": fingerprint, "fingerprint_pass": fingerprint_pass,
        "uniqueness": {k: uniq[k] for k in ("rasters_checked", "worst_overlap", "worst_abs_spearman", "passed")},
        "validator": val, "submission_file": out.name, "zip_file": receipt["zip_file"],
        "sha256_tif": val["sha256"], "sha256_zip": receipt["zip_sha256"],
        "submission_name": name, "submission_note": note, "note_chars": len(note),
        "ok_to_download": bool(val["all_checks_passed"]), "ok_to_submit": ok,
        "verdict": "promote" if ok else "negative",
        "organizer_confirmed": None,
        "labels": "All DTI values are HOLDOUT-DTI (gems57-pooled-hide-v2) unless marked ORGANIZER-CONFIRMED; none are.",
        "runtime_s": round(time.monotonic() - t0, 1),
    }
    wjson(ROOT / "registry/lsc88_run_card.json", card)
    wjson(ROOT / "docs/data/lsc88_run_card.json", card)
    log(f"RUN CARD verdict={card['verdict']} ok_to_submit={ok} runtime={card['runtime_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
