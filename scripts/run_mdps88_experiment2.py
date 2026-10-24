#!/usr/bin/env python3
"""MDPS-88 E2 (budget-matched, amendment1): matched-domain physics surface with distance-regime emission.

Pre-registered in registry/preregistration_mdps88.json + amendment1 (written before this run).
base283/r0/prov terms imported from E1 checkpoints for exact pairing.
Arms (identical folds, paired terms): base283 (control), mdps_far, mdps_mix
(candidate), r0_fixed / prov_fixed (fixed shipped rasters, fold-unfair references).
Every score is HOLDOUT-DTI (gems57-pooled-hide-v2). Spends 0 submission slots.
Reuses vendor/gems57 (holdout, evaluate_holdout, emit) and src/gems88
(physics, halo, adhr) unmodified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import emit, evaluate_holdout, grid as grid_mod, holdout  # noqa: E402
from gems88 import halo, physics  # noqa: E402

BUFFER_PX, BOUNDARY_PX, BLOCK = 3, 12, 200
FAR_PX = 10
SPACING = 2.83
ARMS = ("base283", "mdps_far", "mdps_mix", "r0_fixed", "prov_fixed")
FIXED = {
    "r0_fixed": ROOT / "data/registry/h33_education.tif",
    "prov_fixed": ROOT / "docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros.tif",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canary(X, g, hidden, names, seed=88):
    """Single-feature symmetric ROC AUC (same construction as HALO-88)."""
    fp = g.footprint
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    ys, xs = np.nonzero(fp)
    pos = np.flatnonzero(hidden[ys, xs])
    neg_pool = np.flatnonzero((~g.catalogue & (d_cat > 3))[ys, xs])
    rng = np.random.default_rng(seed)
    neg = np.sort(rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False))
    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(len(pos), int), np.zeros(len(neg), int)])
    order = np.argsort(idx)
    Xs = np.asarray(X[idx[order]], np.float32)
    y = y[order]
    rows = []
    for j, nm in enumerate(names):
        v = Xs[:, j].astype(np.float64)
        ok = np.isfinite(v)
        if ok.sum() < 100 or len(np.unique(y[ok])) < 2:
            rows.append(dict(feature=nm, symmetric_auc=0.5, note="degenerate"))
            continue
        v = np.where(ok, v, np.nanmedian(v[ok]))
        a = float(roc_auc_score(y, v))
        rows.append(dict(feature=nm, roc_auc=a, symmetric_auc=max(a, 1 - a),
                         threshold=0.90, **{"pass": bool(max(a, 1 - a) <= 0.90)}))
    return rows


def load_fixed(path: Path, shape) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1)
    if a.shape != shape:
        raise ValueError(f"{path}: shape {a.shape} != {shape}")
    a = np.where(np.isfinite(a) & (a > 0), 1.0, 0.0).astype(np.float32)
    return a


def alloc(p, m, allowed, k_truth, budget=None):
    return emit.dinkelbach_allocate(p, m, allowed, budget=budget, k_truth=float(k_truth),
                                    min_spacing_px=SPACING, dinkelbach_iters=6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[20, 21])
    ap.add_argument("--out", default="evidence/mdps88_experiment2_20261024.json")
    args = ap.parse_args()
    t0 = time.monotonic()
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    names = list(physics.ALL_PHYS_FEATURES)
    print("[phys] build/load 44ch memmap ...", flush=True)
    X, band_tags, ext_hashes = physics.build_or_load_physics_memmap(ROOT, g, ROOT / ".cache/gems88")
    print(f"[phys] memmap ready {X.shape} at {time.monotonic()-t0:.0f}s", flush=True)
    fixed = {k: load_fixed(p, fp.shape) for k, p in FIXED.items()}
    fixed_sha = {k: sha256(p) for k, p in FIXED.items()}
    ckdir = ROOT / ".cache/mdps88_e2"
    e1dir = ROOT / ".cache/mdps88"
    import math
    ckdir.mkdir(parents=True, exist_ok=True)

    terms = {s: {a: {"all": None, "far": None} for a in ARMS} for s in args.seeds}
    rows = []
    canary_doc = None
    split_receipts = []
    for seed in args.seeds:
        folds, quad = holdout.buffered_component_draw(g, seed=seed, buffer_px=BUFFER_PX, boundary_px=BOUNDARY_PX)
        hidden = folds[0]["hidden_all"]
        visible = folds[0]["visible"]
        split_receipts += [f["receipt"] for f in folds]
        d_vis = ndi.distance_transform_edt(~visible)
        far_mask = d_vis > FAR_PX
        if canary_doc is None:
            print(f"[canary] seed {seed}: {len(names)} features ...", flush=True)
            crows = canary(X, g, hidden, names)
            mx = max(r["symmetric_auc"] for r in crows)
            canary_doc = dict(
                method="single-feature symmetric ROC AUC; withheld whole-component positives vs 8x off-catalogue negatives (d_cat>3 px)",
                seed=seed, features_tested=len(crows), max_symmetric_auc=mx,
                threshold=0.90, passed=bool(mx <= 0.90), features=crows)
            print(f"[canary] max symmetric AUC = {mx:.4f} ({'PASS' if mx <= 0.90 else 'FAIL'})", flush=True)
            if mx > 0.90:
                raise SystemExit("STOP: leakage canary > 0.90")
        for fold in folds:
            q = fold["fold"]
            ck = ckdir / f"mdps_s{seed}_q{q}.npz"
            if ck.is_file():
                z = np.load(ck, allow_pickle=True)
                for a in ARMS:
                    for k in ("all", "far"):
                        bt = z[f"{a}_{k}"]
                        terms[seed][a][k] = bt if terms[seed][a][k] is None else terms[seed][a][k] + bt
                rows.append(json.loads(str(z["row"])))
                print(f"  [ckpt] seed {seed} {fold['name']}", flush=True)
                continue
            region = fold["region"]
            e1 = np.load(e1dir / f"mdps_s{seed}_q{q}.npz", allow_pickle=True)
            e1row = json.loads(str(e1["row"]))
            B_q = int(e1row["base283"]["emitted_in_region"])
            train_truth_px = sum(int(o["truth"].sum()) for o in folds if o["fold"] != q)
            train_truth_mask = hidden & (quad != q) & fp
            # regime shares measured on TRAINING-quadrant withheld truth only
            d_tr = d_vis[train_truth_mask]
            share_far = float((d_tr > 8).mean()) if d_tr.size else 0.8
            share_near = float(((d_tr > 2) & (d_tr <= 8)).mean()) if d_tr.size else 0.2
            row = dict(seed=seed, fold=fold["name"],
                       withheld_positive_pixels=int(fold["truth"].sum()),
                       far_withheld_positive_pixels=int((fold["truth"] & far_mask).sum()),
                       share_far_train=share_far, share_near_train=share_near)
            emissions = {}

            # --- control: base283 (all-positive head, b2 collar, 2.83 spacing)
            tm = time.monotonic()
            clf_base, meta_b = halo.fit_fold_models(X, g, visible, quad, q, train_truth_px,
                                                    seed=88_000 + seed * 10 + q, mode="base")
            p_b, m_b, al_b, k_b = halo.predict_calibrated(clf_base, X, g, visible, region, meta_b["hid_ratio"], 2.0)
            row["base283_meta"] = dict(**meta_b, k_est=k_b, B_q=B_q,
                                       e1_k_est=e1row["base283_meta"]["k_est"],
                                       seconds=round(time.monotonic() - tm, 1))
            print(f"  seed {seed} {fold['name']} base refit: k_b={k_b:.1f} (E1 {e1row['base283_meta']['k_est']:.1f}) B_q={B_q} {time.monotonic()-tm:.0f}s", flush=True)

            # --- far head (isolated-positive training, matched allocation d>8)
            tm = time.monotonic()
            clf_far, meta_f = halo.fit_fold_models(X, g, visible, quad, q, train_truth_px,
                                                   seed=88_000 + seed * 10 + q, mode="fbmt")
            p_f, m_f, al_f, k_tot = halo.predict_calibrated(clf_far, X, g, visible, region, meta_f["hid_ratio"], 8.0)
            k_far = k_b
            p_f2, m_f2 = p_f, m_f
            a_f = alloc(p_f2, m_f2, al_f, k_far, budget=B_q)
            emissions["mdps_far"] = a_f.emitted
            n_far = int(a_f.emitted.sum())
            row["mdps_far_meta"] = dict(**meta_f, k_est_total=k_tot, k_far=k_far, budget=B_q,
                                        surrogate_dti=float(a_f.surrogate_dti),
                                        seconds=round(time.monotonic() - tm, 1))
            print(f"  seed {seed} {fold['name']} mdps_far: n={n_far} k_far={k_far:.0f} {time.monotonic()-tm:.0f}s", flush=True)
            del clf_far

            # --- near tranche for mdps_mix (base head, 2<d<=8, top-1%, capped)
            tm = time.monotonic()
            a_f_mix = alloc(p_f2, m_f2, al_f, k_b, budget=int(math.ceil(0.8 * B_q)))
            near_allowed = al_b & (d_vis <= 8)
            vals = p_b[near_allowed]
            thr = float(np.quantile(vals, 0.99)) if vals.size else float("inf")
            near_allowed2 = near_allowed & (p_b >= thr)
            k_near = k_b
            p_n, m_n = np.where(near_allowed2, p_b, 0).astype(np.float32), m_b
            budget_near = int(0.2 * B_q)
            a_n = alloc(p_n, m_n, near_allowed2, k_near, budget=max(budget_near, 0) or None)
            near_em = a_n.emitted
            if int(a_f_mix.emitted.sum()):
                d_to_far = ndi.distance_transform_edt(~a_f_mix.emitted)
                near_em = near_em & (d_to_far >= SPACING)
            mix_em = a_f_mix.emitted | near_em
            emissions["mdps_mix"] = mix_em
            row["mdps_mix_meta"] = dict(k_near=k_near, near_p99_thr=thr, budget_near=budget_near,
                                        n_near_before_spacing=int(a_n.emitted.sum()),
                                        n_near=int(near_em.sum()), n_far=int(a_f_mix.emitted.sum()), n_far_solo=n_far,
                                        seconds=round(time.monotonic() - tm, 1))
            print(f"  seed {seed} {fold['name']} mdps_mix: n={int(mix_em.sum())} (far {int(a_f_mix.emitted.sum())} + near {int(near_em.sum())})", flush=True)
            del clf_base, p_b, m_b, p_f, m_f, p_f2, m_f2, p_n, m_n

            for a in ("r0_fixed", "prov_fixed"):
                emissions[a] = fixed[a] > 0  # kept for completeness; terms imported from E1

            save = {}
            for a in ARMS:
                if a in ("base283", "r0_fixed", "prov_fixed"):
                    bt_all, bt_far = e1[f"{a}_all"], e1[f"{a}_far"]
                    row[a] = dict(e1row[a], imported_from_e1_checkpoint=True)
                    save[f"{a}_all"] = bt_all
                    save[f"{a}_far"] = bt_far
                    save[f"{a}_emitted"] = e1[f"{a}_emitted"]
                    terms[seed][a]["all"] = bt_all if terms[seed][a]["all"] is None else terms[seed][a]["all"] + bt_all
                    terms[seed][a]["far"] = bt_far if terms[seed][a]["far"] is None else terms[seed][a]["far"] + bt_far
                    print(f"    {a:11s} imported from E1 (dti={row[a]['dti']:.4f} far={row[a]['far_dti']:.4f})", flush=True)
                    continue
                em = emissions[a].astype(np.float32)
                r_all, bt_all = evaluate_holdout.evaluate(em, fold, fp, block_side=BLOCK, global_shape=fp.shape)
                fold_far = dict(fold, truth=fold["truth"] & far_mask)
                r_far, bt_far = evaluate_holdout.evaluate(em, fold_far, fp, block_side=BLOCK, global_shape=fp.shape)
                yy, xx = np.nonzero(emissions[a] & region)
                dd = d_vis[yy, xx]
                row[a] = dict(dti=r_all["dti"], tpw=r_all["tpw"], fpw=r_all["fpw"],
                              emitted_in_region=int(r_all["n_emitted"]),
                              far_dti=r_far["dti"], far_tpw=r_far["tpw"], far_fpw=r_far["fpw"],
                              share_dots_dvis_le2=float((dd <= 2).mean()) if dd.size else None,
                              share_dots_dvis_2_8=float(((dd > 2) & (dd <= 8)).mean()) if dd.size else None,
                              share_dots_dvis_gt25=float((dd > 25).mean()) if dd.size else None)
                save[f"{a}_all"] = bt_all
                save[f"{a}_far"] = bt_far
                save[f"{a}_emitted"] = np.packbits(emissions[a])
                terms[seed][a]["all"] = bt_all if terms[seed][a]["all"] is None else terms[seed][a]["all"] + bt_all
                terms[seed][a]["far"] = bt_far if terms[seed][a]["far"] is None else terms[seed][a]["far"] + bt_far
                print(f"    {a:11s} dti={r_all['dti']:.4f} far={r_far['dti']:.4f} n_region={int(r_all['n_emitted'])}", flush=True)
            np.savez_compressed(ck, row=json.dumps(row), **save)
            rows.append(row)
            print(f"  seed {seed} {fold['name']} done at {time.monotonic()-t0:.0f}s", flush=True)

    pooled = {}
    for kind in ("all", "far"):
        arrs = {a: sum(terms[s][a][kind] for s in args.seeds) for a in ARMS}
        for cand in ("mdps_mix", "mdps_far"):
            pooled[f"{kind}__candidate_{cand}"] = evaluate_holdout.pooled_summary(
                arrs, draws=1000, seed=520810, candidate=cand)
    out = dict(evidence_class="HOLDOUT-DTI", evaluator_version=evaluate_holdout.VERSION,
               lane="MDPS-88", experiment="E2 budget-matched", preregistration="registry/preregistration_mdps88.json + registry/preregistration_mdps88_amendment1.json",
               seeds=args.seeds, buffer_px=BUFFER_PX, boundary_px=BOUNDARY_PX, far_px=FAR_PX,
               spacing_px=SPACING, arms=list(ARMS), fixed_raster_sha256=fixed_sha,
               split_receipts=split_receipts, per_fold=rows, pooled=pooled,
               band_tags=band_tags, ext_hashes=ext_hashes, canary=canary_doc,
               stored_reference_unpaired=dict(name="ADHR (registry/holdout_result.json via docs/research/hypotheses-20261024.md)",
                                              overall=0.18788764184958875, far=0.11478,
                                              note="stored same-fold values, NOT recomputed this session; unpaired comparison only"),
               seconds=round(time.monotonic() - t0, 1))
    (ROOT / args.out).write_text(json.dumps(out, indent=1, default=float))
    for kind in ("far", "all"):
        s = pooled[f"{kind}__candidate_mdps_mix"]["scores"]
        d = pooled[f"{kind}__candidate_mdps_mix"]["paired_differences"]
        print(kind, {a: (round(s[a]["dti"], 5), [round(x, 5) for x in s[a]["ci95"]], s[a]["withheld_positive_pixels"]) for a in ARMS})
        print(kind, "mdps_mix-base283 paired:", round(d["base283"]["delta"], 5), [round(x, 5) for x in d["base283"]["ci95"]])


if __name__ == "__main__":
    main()
