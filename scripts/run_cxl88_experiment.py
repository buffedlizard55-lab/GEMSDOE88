#!/usr/bin/env python3
"""H88-CXL holdout suite: phys44 control + CXL zero-cat + CXL-PoE candidate (3 arms, 8 folds).

Reuses vendor/gems57 evaluator/holdout/emit and src/gems88 physics/HGVC/adhr stacks unmodified.
Candidate promotion gate (preregistered): pooled HOLDOUT-DTI > 0.202947 (stored HGVC Exp03).
"""
from __future__ import annotations
import gc, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout, grid as grid_mod, holdout, emit  # noqa: E402
from gems88 import adhr, cxl, hgvc, physics  # noqa: E402
from gems57 import damagezone_envelope  # noqa: E402

ARMS = ("phys44_zero_cat", "exp01_cxl_zero_cat", "exp02_cxl_poe_conduit")
CAND = "exp02_cxl_poe_conduit"


def main() -> int:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_cxl88.json").read_text())
    assert prereg["frozen_before_feature_canary_holdout_or_production_build"] is True
    g = grid_mod.load_grid(ROOT / "data/bridge")
    cache = ROOT / ".cache/gems88"; cache.mkdir(parents=True, exist_ok=True)
    hgvc_cache = ROOT / ".cache/gems88_hgvc"; hgvc_cache.mkdir(parents=True, exist_ok=True)
    cxl_cache = ROOT / ".cache/gems88_cxl"; cxl_cache.mkdir(parents=True, exist_ok=True)
    print("[1/4] memmaps...", flush=True)
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache)
    X_hgvc, hmeta = hgvc.build_or_load_hgvc_memmap(ROOT, g, hgvc_cache)
    X_cxl, cmeta = cxl.build_or_load_cxl_memmap(ROOT, g, cxl_cache)
    X_diff = hgvc.ColumnSubsetView(X_phys, hgvc.PHYS_DIFF_INDICES)
    print(f"  phys/hgvc/cxl ready {cmeta['schema']}", flush=True)

    import rasterio
    from gems88 import edge
    with rasterio.open(ROOT / "data/training_features.tif") as src:
        assert src.tags(12).get("band_name") == "det_elev"
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
    scarp = adhr.compute_scarp_fields(det_elev, g.footprint, hgvc_cache); del det_elev
    sense = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)

    folds_by_seed, vis_by_seed = [], {}
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))
        vis_by_seed[seed] = adhr.compute_visible_struct_fp(g, folds[0]["visible"], sense, scarp, hgvc_cache, f"seed{seed}")

    print("[2/4] CXL-26 single-feature canary...", flush=True)
    ys, xs = np.nonzero(g.footprint)
    seed0, folds0 = folds_by_seed[0]
    hidden = folds0[0]["hidden_all"][ys, xs]; vis = folds0[0]["visible"][ys, xs]
    pos = np.flatnonzero(hidden); rng = np.random.default_rng(8820)
    neg = rng.choice(np.flatnonzero(~hidden & ~vis), size=min(8 * len(pos), int((~hidden & ~vis).sum())), replace=False)
    sel = np.concatenate([pos, neg]); y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    can_rows = []
    for j, name in enumerate(cxl.CXL_FEATURES):
        auc = float(roc_auc_score(y, np.asarray(X_cxl[sel, j], float)))
        can_rows.append({"feature": name, "roc_auc": round(auc, 6), "symmetric_auc": round(max(auc, 1 - auc), 6)})
    can_rows.sort(key=lambda r: -r["symmetric_auc"])
    canary = {"passed": can_rows[0]["symmetric_auc"] <= 0.90, "features_tested": 26,
              "max_symmetric_auc": can_rows[0]["symmetric_auc"], "max_feature": can_rows[0]["feature"], "top10": can_rows[:10],
              "note": "CXL-26 only; physics-44/HGVC-20 canaries stored in evidence/hgvc88_canaries.json (max 0.770155)"}
    print(f"  canary max={canary['max_symmetric_auc']} {canary['max_feature']}", flush=True)
    if not canary["passed"]:
        raise RuntimeError("STOP leakage canary")

    print("[3/4] 8-fold holdout...", flush=True)
    terms = {a: None for a in ARMS}; terms_far = {a: None for a in ARMS}; terms_blind = {a: None for a in ARMS}
    fold_rows = []
    for seed, folds in folds_by_seed:
        X_vis22, d_vis_fp, comp_len_fp = vis_by_seed[seed]
        d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
        for i, fold in enumerate(folds):
            tag = f"seed{seed}_f{i}"
            train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
            train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
            test_region = fold["region"]
            fp = g.footprint
            dom_phys = train_regions[ys, xs]; dom_struct = (train_regions & ~fold["visible"])[ys, xs]
            pop_tr = train_truth[ys, xs]
            wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr, quantile=0.90, l0_px=40.0)
            dow = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
            allowed = fp & test_region & ~fold["visible"]
            act_idx = np.flatnonzero(allowed[ys, xs]); ay, ax = ys[act_idx], xs[act_idx]
            d_act = d_vis_fp[act_idx]
            n_vis_tr = max(float((fold["visible"] & train_regions).sum()), 1.0)
            hid_ratio = float(train_truth.sum()) / n_vis_tr
            k_est = max(float((fold["visible"] & test_region).sum()) * hid_ratio, 50.0)

            def fit_predict(sources, dom, posg, s):
                c, r = adhr._fit_dual_expectation_models(sources, dom, posg, fp, seed=s, n_ensemble=1)
                out = adhr._predict_dual_chunked(c, r, sources, act_idx); del c, r; gc.collect(); return out

            p_phys, m_phys = fit_predict([X_phys], dom_phys, fold["visible"] & train_regions, seed * 10 + i + 17)
            p_spec, m_spec = fit_predict([X_diff, X_hgvc, X_cxl], dom_phys, fold["visible"] & train_regions, seed * 10 + i + 117)
            p_joint, m_joint = fit_predict([X_phys, X_hgvc, X_cxl, X_vis22, dow], dom_struct, train_truth, seed * 10 + i + 153)
            del dow

            sc = float(k_est) / max(float(p_phys.sum()), 1e-6)
            p_c1 = np.clip(p_phys * np.float32(sc), 0, 1).astype(np.float32); m_c1 = np.clip(m_phys * np.float32(hid_ratio), p_c1, 1).astype(np.float32)
            sc1 = float(k_est) / max(float(p_spec.sum()), 1e-6)
            p_e1 = np.clip(p_spec * np.float32(sc1), 0, 1).astype(np.float32); m_e1 = np.clip(m_spec * np.float32(hid_ratio), p_e1, 1).astype(np.float32)
            p_fp, m_fp = hgvc.poe_pool_hgvc(p_joint, m_joint, p_spec, m_spec, d_act)
            p_pp, m_pp = hgvc.poe_pool_hgvc(p_phys, m_phys, p_spec, m_spec, d_act)
            p_e2, m_e2 = adhr._fuse_log_odds(p_fp, m_fp, p_pp, m_pp, k_est, beta_phys=0.38)

            far_t = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 10)
            far_v = fp & test_region & ~fold["masked_known"] & (d_vis_grid > 10)
            bl_t = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 25)
            bl_v = fp & test_region & ~fold["masked_known"] & (d_vis_grid > 25)
            far_fold = {**fold, "truth": far_t, "region": far_v, "masked_known": np.zeros_like(far_v)}
            bl_fold = {**fold, "truth": bl_t, "region": bl_v, "masked_known": np.zeros_like(bl_v)}
            row = {"seed": seed, "fold": str(fold["name"]), "withheld": int((fold["truth"] & test_region & ~fold["masked_known"]).sum())}
            for arm, (pv, mv) in zip(ARMS, [(p_c1, m_c1), (p_e1, m_e1), (p_e2, m_e2)]):
                pg = adhr.scatter_fp(pv, ay, ax, g.shape); mg = adhr.scatter_fp(mv, ay, ax, g.shape)
                alloc = emit.dinkelbach_allocate(pg, mg, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6)
                em = alloc.emitted.astype(np.float32)
                s_ov, b_ov = evaluate_holdout.evaluate(em, fold, fp, block_side=200)
                s_fr, b_fr = evaluate_holdout.evaluate(em, far_fold, fp, block_side=200)
                s_bl, b_bl = evaluate_holdout.evaluate(em, bl_fold, fp, block_side=200)
                terms[arm] = b_ov if terms[arm] is None else terms[arm] + b_ov
                terms_far[arm] = b_fr if terms_far[arm] is None else terms_far[arm] + b_fr
                terms_blind[arm] = b_bl if terms_blind[arm] is None else terms_blind[arm] + b_bl
                row[arm] = {"dti": round(float(s_ov["dti"]), 6), "far": round(float(s_fr["dti"]), 6),
                            "blind": round(float(s_bl["dti"]), 6), "dots": int(alloc.n_dots)}
            fold_rows.append(row)
            print(f"  [{tag}] phys={row[ARMS[0]]['dti']:.4f} zero={row[ARMS[1]]['dti']:.4f} cand={row[ARMS[2]]['dti']:.4f}", flush=True)

    pooled = evaluate_holdout.pooled_summary(terms, draws=2000, seed=520888, candidate=CAND)
    pooled_far = evaluate_holdout.pooled_summary(terms_far, draws=2000, seed=520889, candidate=CAND)
    pooled_blind = evaluate_holdout.pooled_summary(terms_blind, draws=2000, seed=520890, candidate=CAND)
    cand_dti = pooled["scores"][CAND]["dti"]
    payload = {"schema": "gems88.cxl88.holdout.v1", "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
               "canary": canary, "folds": fold_rows, "pooled_overall": pooled, "pooled_far_gt10px": pooled_far,
               "pooled_blind_gt25px": pooled_blind,
               "stored_hgvc_exp03": {"dti": 0.2029470713394289, "ci95": [0.185868859876156, 0.21979007541452142], "n": 22893},
               "beats_stored_hgvc": bool(cand_dti > 0.2029470713394289),
               "folds_won_vs_phys": int(sum(1 for r in fold_rows if r[CAND]["dti"] > r["phys44_zero_cat"]["dti"])),
               "elapsed_s": round(time.monotonic() - t0, 1)}
    out = ROOT / "evidence/cxl88_holdout_20261025.json"
    out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    print(f"[4/4] CANDIDATE HOLDOUT-DTI={cand_dti:.6f} CI={pooled['scores'][CAND]['ci95']} beats_hgvc={payload['beats_stored_hgvc']} -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
