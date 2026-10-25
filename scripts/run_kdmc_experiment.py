#!/usr/bin/env python3
"""KDMC-88 Experiment 1 — separation x budget surface on the blocked hide-and-recover holdout.

Single-factor design
--------------------
One shared zero-catalogue density surface ``rho`` per fold (leave-one-quadrant-out
PU cross-fit, positives = *visible* catalogue only), one shared expected-credit
surface ``E = rho (*) kernel``, then a 2-D sweep over

* minimum dot separation ``s`` in {2.8284, 4, 6, 8} px, and
* dot budget ``N`` expressed as a fraction of the fold's allowed area,

so packing geometry and budget are separated from each other and from the
geology.  Two label-free references bound the result: a uniform-``rho`` control
(pure geometry, zero geology) and the registry's own best raster restricted to
the same domain.  Everything is scored by the **unmodified** shared evaluator
``vendor/gems57/evaluate_holdout.py``.

Usage::

    python scripts/run_kdmc_experiment.py [--seeds 20] [--out evidence/kdmc_experiment1.json]
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import evaluate_holdout, grid as g57grid, holdout as g57holdout, metric  # noqa: E402
from gems88 import kdmc  # noqa: E402

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

HIDE_FRAC = 0.20
BUFFER_PX = 3
SEPARATIONS = (2.8284271247461903, 4.0, 6.0, 8.0)
BUDGET_FRACTIONS = (0.0025, 0.005, 0.0073, 0.01, 0.02, 0.04, 0.08, 1.0)
COLLAR_ARMS = ()           # extra d_catalogue collars to test at every (sep, budget)
N_NEG = 400_000
N_CANARY_NEG = 150_000
BLOCK_SIDE = 200          # 20 km spatial-bootstrap blocks
N_BOOT = 1000


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def rows_for(mask, lin):
    r = lin[mask]
    return r[r >= 0]


def predict_rows(model, mm, rows, chunk=250_000):
    out = np.empty(rows.size, np.float32)
    order = np.argsort(rows)
    srt = rows[order]
    for a in range(0, srt.size, chunk):
        blk = srt[a:a + chunk]
        out[order[a:a + chunk]] = model.predict_proba(
            np.asarray(mm[blk], np.float32))[:, 1].astype(np.float32)
    return out


def greedy_order(score, allowed, sep):
    """Accepted cell linear indices in exact sequential-greedy-by-weight order."""
    dots, rounds, converged = kdmc.allocate_separated(
        score, allowed, sep, -np.inf, max_rounds=400, return_diagnostics=True)
    if not converged:
        raise RuntimeError(f"greedy packing did not converge at sep={sep}")
    idx = np.flatnonzero(dots.ravel())
    vals = score.ravel()[idx]
    return idx[np.lexsort((idx, -vals))], rounds


def crop_fold(fold, footprint, pad=6):
    r = fold["region"]
    ys = np.flatnonzero(r.any(axis=1))
    xs = np.flatnonzero(r.any(axis=0))
    y0, y1 = max(0, ys[0] - pad), min(r.shape[0], ys[-1] + 1 + pad)
    x0, x1 = max(0, xs[0] - pad), min(r.shape[1], xs[-1] + 1 + pad)
    sl = (slice(y0, y1), slice(x0, x1))
    sub = dict(fold)
    for k in ("region", "truth", "visible", "masked_known"):
        sub[k] = fold[k][sl]
    return sub, sl, (y0, x0), footprint[sl]


def pooled_from(term_list):
    tot = np.sum([t.sum(axis=0) for t in term_list], axis=0)
    tp, fp, fn = float(tot[0]), float(tot[1]), float(tot[2])
    return tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS), tot


def bootstrap_ci(term_list, n_boot=N_BOOT, seed=7):
    acc = np.sum(np.stack(term_list), axis=0)        # (n_blocks, 4)
    acc = acc[acc[:, 3] > 0]
    if acc.shape[0] < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, acc.shape[0], size=(n_boot, acc.shape[0]))
    s = acc[draws].sum(axis=1)
    d = s[:, 0] + metric.ALPHA * s[:, 1] + metric.BETA * s[:, 2]
    v = np.where(d > 0, s[:, 0] / np.maximum(d, 1e-12), 0.0)
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[20])
    ap.add_argument("--out", default="evidence/kdmc_experiment1.json")
    ap.add_argument("--separations", type=float, nargs="+", default=list(SEPARATIONS))
    ap.add_argument("--budgets", type=float, nargs="+", default=list(BUDGET_FRACTIONS))
    ap.add_argument("--collars", type=float, nargs="+", default=list(COLLAR_ARMS))
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    separations, budgets = tuple(args.separations), tuple(args.budgets)

    t0 = time.time()
    grid = g57grid.load_grid()
    H, W = grid.shape
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    mm, names = kdmc.build_feature_stack(ROOT / "data", ROOT / "data" / "external",
                                         valid, ROOT / ".cache" / "kdmc")
    flat_valid = np.flatnonzero(valid.ravel())
    lin = np.full(valid.size, -1, np.int32)
    lin[flat_valid] = np.arange(flat_valid.size, dtype=np.int32)
    lin = lin.reshape(valid.shape)
    log(f"features: {len(names)} columns x {mm.shape[0]:,} valid cells")

    with rasterio.open(ROOT / "data" / "registry" / "h33_education.tif") as ds:
        h33 = np.isfinite(ds.read(1)) & (ds.read(1) > 0)

    terms, metas, canary = {}, {}, {}
    fold_records = []

    for seed in args.seeds:
        folds, _ = g57holdout.buffered_component_draw(
            grid, seed=seed, hide_frac=HIDE_FRAC, buffer_px=BUFFER_PX)
        for f in folds:
            key = f"seed{seed}_{f['name']}"
            region, truth, visible, known = f["region"], f["truth"], f["visible"], f["masked_known"]
            active = grid.footprint & region & ~known
            log(f"--- {key}: region={int(region.sum()):,} truth={int(truth.sum()):,} "
                f"active={int(active.sum()):,}")
            fold_records.append(dict(fold_key=key, region_px=int(region.sum()),
                                     truth_px=int(truth.sum()), active_px=int(active.sum()),
                                     visible_catalogue_px=int(visible.sum()),
                                     receipt=dict(f["receipt"])))

            # ---- PU training, other quadrants only, visible catalogue only --
            # The fitted density depends only on (seed, fold, feature version), never
            # on the arm, so it is cached and shared across experiments. Re-using it
            # keeps every arm comparison exactly paired on one density surface.
            rho_cache = (ROOT / ".cache" / "kdmc" /
                         f"rho_{kdmc.FEATURE_VERSION}_seed{seed}_fold{f['fold']}.npy")
            if rho_cache.is_file():
                rho = np.load(rho_cache).astype(np.float32)
                log(f"    reusing cached fold density {rho_cache.name}")
                model = None
            else:
                rho = None
            train_dom = grid.footprint & ~region
            rng = np.random.default_rng(1000 * seed + f["fold"])
            if rho is None:
                near_visible = ndi.distance_transform_edt(~visible) <= 3
                pos_rows = rows_for(visible & train_dom, lin)
                neg_pool = rows_for(train_dom & ~near_visible, lin)
                neg_rows = rng.choice(neg_pool, size=min(N_NEG, neg_pool.size), replace=False)
                rws = np.sort(np.concatenate([pos_rows, neg_rows]))
                y = np.isin(rws, pos_rows).astype(np.int8)
                log(f"    PU fit: {int(y.sum()):,}+ / {int((1 - y).sum()):,}-")
                model = HistGradientBoostingClassifier(
                    max_iter=250, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=50,
                    l2_regularization=1.0, early_stopping=False,
                    class_weight={0: 1.0, 1: float((1 - y).sum()) / max(int(y.sum()), 1)},
                    random_state=int(1000 * seed + f["fold"]))
                model.fit(np.asarray(mm[rws], np.float32), y)
                del rws, y, near_visible
                rho = np.zeros((H, W), np.float32)
                rho[grid.footprint & region] = predict_rows(
                    model, mm, rows_for(grid.footprint & region, lin))
                rho_cache.parent.mkdir(parents=True, exist_ok=True)
                np.save(rho_cache, rho)
            E = kdmc.expected_credit(rho)

            # ---- leakage canaries -------------------------------------------
            t_rows = rows_for(truth, lin)
            n_pool = rows_for(active & ~truth, lin)
            n_rows = rng.choice(n_pool, size=min(N_CANARY_NEG, n_pool.size), replace=False)
            cr = np.sort(np.concatenate([t_rows, n_rows]))
            lab = np.isin(cr, t_rows).astype(np.int8)
            Xc = np.asarray(mm[cr], np.float32)
            for j, nm in enumerate(names):
                a = roc_auc_score(lab, Xc[:, j])
                canary.setdefault(nm, []).append(float(max(a, 1.0 - a)))
            a = roc_auc_score(lab, rho.ravel()[flat_valid[cr]])
            canary.setdefault("__fitted_rho__", []).append(float(max(a, 1.0 - a)))
            del Xc, cr, lab

            sub, sl, origin, fp_sub = crop_fold(f, grid.footprint)

            def score_arm(arm, dots_full, meta):
                res, tm = evaluate_holdout.evaluate(
                    dots_full[sl].astype(np.float32), sub, fp_sub,
                    block_side=BLOCK_SIDE, origin=origin, global_shape=(H, W))
                terms.setdefault(arm, {})[key] = tm
                metas.setdefault(arm, {})[key] = dict(meta, dti=float(res["dti"]),
                                                      n_emitted=int(res["n_emitted"]))

            # ---- arms: separation x budget (x optional catalogue collar) ----
            d_cat = ndi.distance_transform_edt(~grid.catalogue)
            for collar in (0.0,) + tuple(args.collars):
                dom = active if collar <= 0 else (active & (d_cat > collar))
                tag = "" if collar <= 0 else f"_collar{collar:g}"
                for sep in separations:
                    idx, rounds = greedy_order(E, dom, sep)
                    n_max = idx.size
                    log(f"    sep={sep:.4f}{tag}: n_max={n_max:,} ({rounds} rounds, "
                        f"density={n_max / max(int(dom.sum()), 1):.5f})")
                    for bf in budgets:
                        n = n_max if bf >= 1.0 else min(int(round(bf * active.sum())), n_max)
                        if n <= 0:
                            continue
                        d = np.zeros(H * W, bool)
                        d[idx[:n]] = True
                        score_arm(f"sep{sep:.4f}_bf{bf:g}{tag}", d.reshape(H, W),
                                  dict(sep=sep, budget_fraction=bf, collar_px=collar,
                                       n_dots=int(n), n_max=int(n_max)))

            # ---- control: uniform rho, pure geometry ------------------------
            u = np.zeros((H, W), np.float32)
            u[active] = 1.0 + np.random.default_rng(99).random(int(active.sum())).astype(np.float32) * 1e-3
            idx, _ = greedy_order(u, active, 2.8284271247461903)
            for bf in (0.0073, 0.01, 0.02):
                n = min(int(round(bf * active.sum())), idx.size)
                d = np.zeros(H * W, bool)
                d[idx[:n]] = True
                score_arm(f"CONTROL_uniform_sep2.8284_bf{bf:g}", d.reshape(H, W),
                          dict(sep=2.8284271247461903, budget_fraction=bf, n_dots=int(n)))

            # ---- reference: registry best raster on the same domain ---------
            score_arm("REFERENCE_h33_registry", h33 & active,
                      dict(sep=None, budget_fraction=None, n_dots=int((h33 & active).sum())))

            del rho, E, model
            log(f"    {key} done ({time.time() - t0:.0f}s)")

    arms = []
    for arm, per in terms.items():
        tl = list(per.values())
        dti, tot = pooled_from(tl)
        lo, hi = bootstrap_ci(tl)
        m0 = next(iter(metas[arm].values()))
        arms.append(dict(arm=arm, evidence_class="HOLDOUT-DTI",
                         evaluator_version=evaluate_holdout.VERSION,
                         pooled_dti=float(dti), ci95=[lo, hi],
                         withheld_positive_pixels=int(tot[3]),
                         pooled_tp=float(tot[0]), pooled_fp=float(tot[1]), pooled_fn=float(tot[2]),
                         total_dots=int(sum(v["n_dots"] for v in metas[arm].values())),
                         separation_px=m0["sep"], budget_fraction=m0["budget_fraction"],
                         collar_px=m0.get("collar_px"),
                         n_folds=len(tl),
                         per_fold={k: dict(dti=v["dti"], n_dots=v["n_dots"])
                                   for k, v in metas[arm].items()}))
    arms.sort(key=lambda r: -r["pooled_dti"])
    worst = max(canary.items(), key=lambda kv: max(kv[1]))
    report = dict(
        hypothesis=("KDMC-88: under alpha=0.2/beta=0.8 DTI with a 300 m triangular kernel the "
                    "optimal binary field is a kernel-disjoint packing extended to every cell "
                    "clearing the exact marginal bar, not a fixed ~37.6k-dot field at ~3 px spacing."),
        mechanism=("exact DTI fractional-program algebra (marginal bar alpha*DTI*(1-k_self)/"
                   "(1-alpha*DTI)) applied to a zero-catalogue PU density surface"),
        named_non_fault_mimic=("Pleistocene Lake Lahontan wave-cut shoreline benches (~1,330 m) and "
                               "alluvial-fan risers; GeoDAWN flight-line levelling seams in the "
                               "magnetic bands. Both carried as explicit model features."),
        evaluator=dict(version=evaluate_holdout.VERSION,
                       implementation_sha256=evaluate_holdout.implementation_hashes()),
        constants=dict(alpha=metric.ALPHA, beta=metric.BETA, radius_px=metric.RADIUS_PX,
                       kernel_mass=kdmc.KERNEL_MASS, block_side_px=BLOCK_SIDE, n_bootstrap=N_BOOT),
        holdout=dict(kind="buffered whole-component hide-and-recover; label-blind eroded quadrants",
                     seeds=list(args.seeds), hide_frac=HIDE_FRAC, feature_buffer_px=BUFFER_PX,
                     boundary_erode_px=g57holdout.DOMAIN_ERODE, folds=fold_records),
        feature_names=names,
        canaries={k: dict(max_fold_auc=float(max(v)), mean_auc=float(np.mean(v)))
                  for k, v in sorted(canary.items())},
        canary_summary=dict(n_tested=len(canary), limit=0.90, worst_feature=worst[0],
                            worst_max_auc=float(max(worst[1])),
                            verdict="PASS" if max(worst[1]) <= 0.90 else "LEAKAGE-SUSPECT"),
        reference_note=("REFERENCE_h33_registry is DIAGNOSTIC ONLY and structurally suppressed: "
                        "the registry raster was pruned to d_catalogue >= 2.24 px against the "
                        "FULL catalogue, which already contains the withheld segments, so only "
                        "2.8-4.6% of withheld truth pixels lie within 3 px of any of its dots. "
                        "It is reported for completeness, never as a fair competitor."),
        label=args.label, arms=arms, runtime_seconds=round(time.time() - t0, 1))
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {out}")
    for r in arms:
        log(f"  {r['arm']:<30} DTI={r['pooled_dti']:.5f} "
            f"CI[{r['ci95'][0]:.5f},{r['ci95'][1]:.5f}] dots={r['total_dots']:,}")
    log(f"canary: {report['canary_summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
