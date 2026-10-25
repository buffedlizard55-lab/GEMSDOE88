#!/usr/bin/env python3
"""H88-PGTD lane runner: preflight record -> canary -> 8-cell holdout (A vs B)
-> production -> two-phase uniqueness -> shared writer -> run card.

Shared tools only for scoring/writing/validation: vendor/gems57
(holdout, evaluate_holdout, submission_writer, validate, uniqueness) and
src/gems88 (pgtd88 features, shared Poisson-disc emitter, registry list).
Preregistration: registry/preregistration_pgtd88.json (frozen before any run).

HISTORICAL GUARD DEVIATION: concurrent session ba739e0f recorded a
DUPLICATE_STOP and proceeded research-only. That exception is revoked by
IR-88-B4DFA10C-07: the CLI now delegates to the unchanged shared preflight
BEFORE importing any model/feature code. The archived file and measurements
remain evidence only, never permission to rerun or submit.
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
import rasterio
from lightgbm import LGBMClassifier
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import evaluate_holdout, grid as grid_mod, holdout, submission_writer, uniqueness, validate  # noqa: E402
from gems88 import pgtd88  # noqa: E402
from gems88.models_and_alloc import emit_poisson_disk_nms  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402
from scripts.generation_guard import inspect as guard_inspect  # noqa: E402

LANE = "H88-PGTD"
BUDGET = 37_654
COLLAR_PX = 3.0
SPACING_PX = 2.8
REGIME_BLIND_FRAC = 0.40
REGIME_SPLIT_PX = 25.0
BLOCK_SIDE = 200
BOOT_DRAWS = 1000
BOOT_SEED = 520810
SEEDS = (20, 21)
REPO_HOLDOUT_BEST = 0.205991
EVID = ROOT / "evidence"
CACHE = ROOT / ".cache/gems88_mfs"
LGBM = dict(n_estimators=250, learning_rate=0.05, num_leaves=63, min_child_samples=200,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
            n_jobs=2, verbose=-1, random_state=88)
N_NEG = 500_000


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def wjson(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def fit(X, rows_pos, rows_neg, cols):
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


def emit_regime(surface, allowed, d_ref, n_dots):
    """60% near (d<=25) / 40% blind (d>25) Poisson-disc dots, cross-spacing kept."""
    n_blind = int(round(REGIME_BLIND_FRAC * n_dots))
    n_near = n_dots - n_blind
    blind = emit_poisson_disk_nms(surface, allowed & (d_ref > REGIME_SPLIT_PX),
                                  n_dots=n_blind, min_dist_px=SPACING_PX) > 0
    block = ndi.distance_transform_edt(~blind) < SPACING_PX if blind.any() else np.zeros_like(blind)
    near = emit_poisson_disk_nms(surface, allowed & (d_ref <= REGIME_SPLIT_PX) & ~block,
                                 n_dots=n_near, min_dist_px=SPACING_PX) > 0
    dots = blind | near
    short = n_dots - int(dots.sum())
    if short > 0:  # top up from either regime, still spacing-respecting
        block = ndi.distance_transform_edt(~dots) < SPACING_PX
        extra = emit_poisson_disk_nms(surface, allowed & ~block,
                                      n_dots=short, min_dist_px=SPACING_PX) > 0
        dots = dots | extra
    return dots


def main() -> int:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_pgtd88.json").read_text())
    assert prereg["frozen_before_feature_canary_holdout_or_production_build"] is True

    # ---- preflight: record the literal guard decision BEFORE features ----
    preflight = guard_inspect(ROOT)
    wjson(EVID / "pgtd88_preflight.json", preflight)
    literal_blocked = preflight["decision"] == "DUPLICATE_STOP"
    log(f"preflight: {preflight['decision']} (literal duplicate stop recorded; research-only)")

    g = grid_mod.load_grid(ROOT / "data/bridge")
    fp = g.footprint
    ys, xs = np.nonzero(fp)
    n_fp = ys.size
    idx_grid = np.full(fp.shape, -1, np.int64)
    idx_grid[ys, xs] = np.arange(n_fp)
    log(f"grid ok: footprint={n_fp} catalogue={int(g.catalogue.sum())}")

    X, meta = pgtd88.build_or_load(ROOT, fp, CACHE)
    feats = meta["names"]
    cols_A = list(range(31))
    cols_B = list(range(19))
    log(f"features ready: {X.shape} schema={meta['schema']}")

    quad = holdout.quadrant_ids(fp)
    folds_by_seed = {s: holdout.buffered_component_draw(
        g, seed=s, hide_frac=0.20, buffer_px=3, boundary_px=12)[0] for s in SEEDS}
    rng = np.random.default_rng(880)

    # ---------------------------------------------------------------- EXP1 canary
    canary_p = EVID / "pgtd88_canaries.json"
    if canary_p.exists():
        canary = json.loads(canary_p.read_text())
    else:
        log("EXP1 single-feature leakage canary")
        truth_rows, neg_rows = [], []
        for s in SEEDS:
            for f in folds_by_seed[s]:
                reg = f["region"] & fp & ~f["masked_known"]
                truth_rows.append(idx_grid[f["truth"] & reg])
                cand = idx_grid[reg & ~f["truth"]]
                neg_rows.append(rng.choice(cand, size=min(60_000, cand.size), replace=False))
        tr = np.unique(np.concatenate(truth_rows))
        ng = np.unique(np.concatenate(neg_rows))
        Xa, Xb = X[tr], X[ng]
        y = np.r_[np.ones(len(tr)), np.zeros(len(ng))]
        rows = []
        for j, name in enumerate(feats):
            auc = float(roc_auc_score(y, np.r_[Xa[:, j], Xb[:, j]]))
            rows.append({"feature": name, "auc": auc, "symmetric_auc": max(auc, 1 - auc)})
        mx = max(rows, key=lambda r: r["symmetric_auc"])
        canary = {"evidence_class": "LEAKAGE-CANARY", "withheld_positive_pixels": int(len(tr)),
                  "negatives": int(len(ng)), "features_tested": len(rows), "limit": 0.90,
                  "max_symmetric_auc": mx["symmetric_auc"], "max_feature": mx["feature"],
                  "passed": bool(mx["symmetric_auc"] <= 0.90), "rows": rows}
        wjson(canary_p, canary)
        del Xa, Xb
    log(f"canary: {canary['features_tested']} features, max sym AUC "
        f"{canary['max_symmetric_auc']:.4f} on {canary['max_feature']} -> "
        f"{'PASS' if canary['passed'] else 'FAIL'}")
    if not canary["passed"]:
        log("STOP: leakage canary failed; no emission")
        return 2

    # ---------------------------------------------------------------- EXP2 holdout
    hold_p = EVID / "pgtd88_holdout.json"
    if hold_p.exists() and "--recompute-holdout" not in sys.argv:
        hold = json.loads(hold_p.read_text())
    else:
        arms = ["pgtd_A_regime", "org19_B_regime"]
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
                    model = fit(X, pos_rows, neg_rows, cols)
                    p = np.zeros(fp.shape, np.float32)
                    p[fp & (quad == q)] = predict_rows(model, X, test_rows, cols)
                    surfaces[arm_name] = p
                    del model
                for arm in arms:
                    p = surfaces["A" if arm.startswith("pgtd") else "B"]
                    em = emit_regime(p, allowed, d_vis, n_dots).astype(np.float32)
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
                log(f"seed {s} fold {fold['name']}: n_dots={n_dots} "
                    f"truth={cell['withheld_positive_pixels']} "
                    + " ".join(f"{a}={cell['arms'][a]['overall']}/{cell['arms'][a]['far10']}"
                               f"/{cell['arms'][a]['blind25']}" for a in arms)
                    + f" ({time.monotonic() - tc:.0f}s)")
                del surfaces
                gc.collect()
        pooled = {key: evaluate_holdout.pooled_summary(
            terms[key], draws=BOOT_DRAWS, seed=BOOT_SEED + i, candidate="pgtd_A_regime")
            for i, key in enumerate(("overall", "far10", "blind25"))}
        hold = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                "budget_rule": f"{BUDGET} x region_cells / {n_fp}", "collar_px": COLLAR_PX,
                "spacing_px": SPACING_PX, "regime": "60% 3<d<=25 / 40% d>25 (visible-only)",
                "cells": cells, "pooled": pooled}
        wjson(hold_p, hold)
    for key in ("overall", "far10", "blind25"):
        sc = hold["pooled"][key]["scores"]
        pdiff = hold["pooled"][key]["paired_differences"]
        log(f"HOLDOUT {key}: " + "; ".join(
            f"{a}={v['dti']:.4f} [{v['ci95'][0]:.4f},{v['ci95'][1]:.4f}] "
            f"n={v['withheld_positive_pixels']}" for a, v in sc.items()))
        log("   paired A-minus: " + "; ".join(
            f"{a}: {d['delta']:+.4f} [{d['ci95'][0]:+.4f},{d['ci95'][1]:+.4f}]"
            for a, d in pdiff.items()))
    ov, far = hold["pooled"]["overall"], hold["pooled"]["far10"]
    lane_pass = (ov["paired_differences"]["org19_B_regime"]["ci95"][0] > 0
                 and far["paired_differences"]["org19_B_regime"]["ci95"][0] > 0)
    a_dti = ov["scores"]["pgtd_A_regime"]["dti"]
    beats_repo_best = bool(a_dti > REPO_HOLDOUT_BEST)
    log(f"EXP2 decision: A beats B (CI>0 overall AND far): {lane_pass}; "
        f"A={a_dti:.4f} vs repo best {REPO_HOLDOUT_BEST}: beats={beats_repo_best}")
    if "--holdout-only" in sys.argv:
        return 0

    # ---------------------------------------------------------------- EXP3 production
    log("EXP3 production fit on the full visible catalogue")
    d_cat = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    pos_rows = idx_grid[fp & g.catalogue]
    neg_cand = idx_grid[fp & (d_cat > COLLAR_PX)]
    neg_rows = rng.choice(neg_cand, size=min(N_NEG, neg_cand.size), replace=False)
    model = fit(X, pos_rows, neg_rows, cols_A)
    imp = sorted(zip(feats, model.feature_importances_.tolist()), key=lambda t: -t[1])
    p_full = np.zeros(fp.shape, np.float32)
    p_full[ys, xs] = predict_rows(model, X, np.arange(n_fp), cols_A)
    del model
    allowed_prod = fp & (d_cat > COLLAR_PX) & ~g.catalogue

    # ---- uniqueness phase 1: surface rank-correlation BEFORE placement ----
    reg = registry_list(ROOT, exclude=("pgtd88",))
    sub = rng.choice(n_fp, size=300_000, replace=False)
    mine_sub = p_full[ys[sub], xs[sub]]
    surf_rows, worst_rho = [], 0.0
    log(f"uniqueness phase 1: surface Spearman vs {len(reg)} registry rasters")
    reg_arrays = []
    for label, path in reg:
        try:
            with rasterio.open(path) as src:
                if (src.height, src.width) != fp.shape:
                    surf_rows.append({"registry": label, "skipped": "shape mismatch"})
                    continue
                a = src.read(1).astype(np.float32)
        except Exception as exc:
            surf_rows.append({"registry": label, "skipped": str(exc)[:80]})
            continue
        a[~np.isfinite(a)] = 0.0
        reg_arrays.append((label, path))  # re-read in phase 2; never hold all grids
        v = a[ys[sub], xs[sub]]
        rho = float(abs(spearmanr(mine_sub, v).statistic)) if v.std() > 0 else 0.0
        surf_rows.append({"registry": label, "abs_spearman_surface": round(rho, 6)})
        worst_rho = max(worst_rho, rho)
    log(f"surface worst |rho| = {worst_rho:.4f} (limit 0.90)")

    dots = emit_regime(p_full, allowed_prod, d_cat, BUDGET)
    n_dots = int(dots.sum())
    dd = d_cat[dots]
    fingerprint = {"dots": n_dots, "share_le2": float((dd <= 2).mean()),
                   "share_gt25": float((dd > 25).mean()),
                   "median_d_cat_px": float(np.median(dd)), "min_d_cat_px": float(dd.min()),
                   "on_catalogue": int((dots & g.catalogue).sum()),
                   "outside_footprint": int((dots & ~fp).sum())}
    log(f"production: dots={n_dots} fingerprint={fingerprint}")
    np.save(CACHE / "p_full.npy", p_full)

    # ---- uniqueness phase 2: final-dot overlaps (literal + like-for-like) ----
    log("uniqueness phase 2: final-dot 3px overlaps")
    dots_yx = np.nonzero(dots)
    rows = []
    worst_literal = worst_like = 0.0
    worst_literal_who = worst_like_who = None
    worst_excess = None
    for label, path in reg_arrays:
        with rasterio.open(path) as src:
            a = src.read(1).astype(np.float32)
        a[~np.isfinite(a)] = 0.0
        a_fp = np.where(fp, a, 0.0)
        del a
        pos = a_fp > 0
        n_pos = int(pos.sum())
        dense = n_pos > 0.10 * n_fp
        near = ndi.distance_transform_edt(~pos) <= 3.0 if n_pos else np.zeros_like(pos)
        lit = float(near[dots_yx].mean()) if n_pos else 0.0
        halo_cov = float(near[allowed_prod].mean()) if n_pos else 0.0
        excess = uniqueness.excess_overlap(lit, halo_cov)
        if not dense:
            like = lit
            defs = {"positive_cells": round(lit, 6)}
        else:
            vals = a_fp[fp]
            defs = {}
            for nm, k in (("top_k", n_dots), ("top_2pct", int(0.02 * n_fp))):
                thr = np.partition(vals, -k)[-k]
                their = (a_fp >= thr) & fp
                defs[nm] = round(float((ndi.distance_transform_edt(~their) <= 3.0)[dots_yx].mean()), 6)
            like = max(defs.values())
        rows.append({"registry": label, "their_positive_cells": n_pos, "dense": bool(dense),
                     "literal_forward_overlap_3px": round(lit, 6),
                     "halo_coverage_allowed": round(halo_cov, 6),
                     "excess_overlap": None if excess is None else round(float(excess), 6),
                     "like_for_like_defs": defs, "like_for_like_overlap": round(float(like), 6)})
        if lit > worst_literal:
            worst_literal, worst_literal_who = lit, label
        if like > worst_like:
            worst_like, worst_like_who = like, label
        if excess is not None:
            worst_excess = float(excess) if worst_excess is None else max(worst_excess, float(excess))
        del a_fp, pos, near
        gc.collect()
    literal_pass = bool(worst_literal <= 0.70 and worst_rho <= 0.90)
    corrected_pass = bool(worst_like <= 0.70 and worst_rho <= 0.90
                          and (worst_excess is None or worst_excess <= 0.70))
    uniq = {"rasters_checked": len(rows), "surface_rows": surf_rows,
            "worst_abs_spearman_surface": worst_rho,
            "worst_literal_overlap": worst_literal, "worst_literal_who": worst_literal_who,
            "worst_like_for_like_overlap": worst_like, "worst_like_for_like_who": worst_like_who,
            "worst_excess_overlap_discriminating": worst_excess,
            "overlap_limit": 0.70, "rho_limit": 0.90,
            "literal_pass": literal_pass, "corrected_pass": corrected_pass, "rows": rows}
    wjson(EVID / "pgtd88_uniqueness.json", uniq)
    log(f"uniqueness: literal worst {worst_literal:.4f} ({worst_literal_who}) pass={literal_pass}; "
        f"like-for-like worst {worst_like:.4f} ({worst_like_who}); corrected pass={corrected_pass}")

    fingerprint_pass = fingerprint["share_le2"] == 0.0 and fingerprint["share_gt25"] >= 0.35
    ok = bool(lane_pass and beats_repo_best and literal_pass and fingerprint_pass
              and canary["passed"])
    pred = np.where(dots, 1.0, 0.0).astype(np.float32)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    stem = f"gems88-pgtd88-marussi-{n_dots}dots-{stamp}-{short}-zeros" + ("" if ok else "-DO-NOT-SUBMIT")
    out = ROOT / "docs/downloads" / f"{stem}.tif"
    name = f"GEMSDOE88-PGTD88-{short.upper()}"
    o, f_ = ov["scores"]["pgtd_A_regime"], far["scores"]["pgtd_A_regime"]
    note = (f"H88-PGTD Marussi tensor dimensionality 31ch, two-regime 37654d; "
            f"HOLDOUT-DTI {o['dti']:.4f} far {f_['dti']:.4f}; UNSCORED")[:140]
    receipt = submission_writer.write_submission(
        out, pred, ROOT / "data/bridge/sample_submission.tif", fp,
        note=note, name=name, catalogue=g.catalogue)
    val = validate.validate(out, fp, g.catalogue)
    validate.assert_submittable(val)
    log(f"written {out.name} sha256={val['sha256']} checks={val['all_checks_passed']}")

    stop_reasons = []
    if literal_blocked or not literal_pass:
        stop_reasons.append(
            f"UNIQUENESS (literal rule): forward 3px overlap = {worst_literal:.4f} > 0.70 "
            f"vs {worst_literal_who} (space-filling witness; random dots also 1.0)")
    if not corrected_pass:
        stop_reasons.append(f"UNIQUENESS (corrected): like-for-like {worst_like:.4f} / "
                            f"|rho| {worst_rho:.4f} vs limits 0.70/0.90")
    if not lane_pass:
        stop_reasons.append("HOLDOUT: arm A did not beat arm B with paired CI>0 on overall AND far")
    if not beats_repo_best:
        stop_reasons.append(f"HOLDOUT: A {a_dti:.6f} does not beat repo best {REPO_HOLDOUT_BEST} (same evaluator)")
    if not fingerprint_pass:
        stop_reasons.append("FINGERPRINT: share_le2/share_gt25 screen failed")
    card = {
        "lane": LANE, "generated_utc": stamp,
        "hypothesis": prereg["hypothesis"], "mechanism": prereg["mechanism"],
        "named_non_fault_mimics": prereg["named_non_fault_mimics"],
        "preflight_generation_guard": {"decision": preflight["decision"],
                                       "generation_allowed": preflight["generation_allowed"],
                                       "evidence": "evidence/pgtd88_preflight.json"},
        "features": feats, "feature_importance_top15": imp[:15],
        "leakage_canary": {k: canary[k] for k in
                           ("features_tested", "max_symmetric_auc", "max_feature", "passed",
                            "withheld_positive_pixels")},
        "holdout": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": hold["evaluator_version"],
                    "pooled": hold["pooled"], "exp2_lane_pass": lane_pass,
                    "armA_overall_dti": a_dti, "repo_best_to_beat": REPO_HOLDOUT_BEST,
                    "beats_repo_best": beats_repo_best},
        "fingerprint": fingerprint, "fingerprint_pass": fingerprint_pass,
        "uniqueness": {k: uniq[k] for k in
                       ("rasters_checked", "worst_abs_spearman_surface", "worst_literal_overlap",
                        "worst_literal_who", "worst_like_for_like_overlap", "worst_like_for_like_who",
                        "worst_excess_overlap_discriminating", "literal_pass", "corrected_pass")},
        "validator": val, "submission_file": out.name, "zip_file": receipt["zip_file"],
        "sha256_tif": val["sha256"], "sha256_zip": receipt["zip_sha256"],
        "submission_name": name, "submission_note": note, "note_chars": len(note),
        "ok_to_download": bool(val["all_checks_passed"]), "ok_to_submit": ok,
        "verdict": "promote" if ok else "negative", "stop_reasons": stop_reasons,
        "organizer_confirmed": None, "weekly_slots_used": 0,
        "labels": "All DTI values are HOLDOUT-DTI (gems57-pooled-hide-v2); no ORGANIZER-CONFIRMED score exists.",
        "runtime_s": round(time.monotonic() - t0, 1),
    }
    wjson(ROOT / "registry/pgtd88_run_card.json", card)
    wjson(ROOT / "docs/data/pgtd88_run_card.json", card)
    log(f"RUN CARD verdict={card['verdict']} ok_to_submit={ok} runtime={card['runtime_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
