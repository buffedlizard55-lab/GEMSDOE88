#!/usr/bin/env python3
"""Run the 3 preregistered GTHC-88 experiments on buffered whole-component holdout.

Preregistration: registry/preregistration_gthc88.json
Candidate dossier: research/candidate-hypotheses-20261024-gthc88.md
Evaluator: vendor/gems57/evaluate_holdout.py (gems57-pooled-hide-v2, alpha=0.2, beta=0.8, 300 m kernel)
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "vendor"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from gems57 import evaluate_holdout, grid as grid_mod, holdout  # noqa: E402
from gems88 import adhr, gthc, physics  # noqa: E402

BAR_OVERALL = 0.18788764184958875  # registry/holdout_result.json h88_adhr
BAR_OVERALL_RECOMPUTED = 0.18963385584087347  # evidence/mrr88_holdout.json h88_adhr_incumbent
BAR_FAR = 0.11477758100238767  # registry/run_card_20261024.json h88_adhr (d_vis > 10 px)
ARMS = ("gthc88_pure_phys50", "gthc88_dual_scrd", "gthc88_strat_fp")


def run_leakage_canary(
    X_phys_mm: np.memmap,
    X_gthc_mm: np.memmap,
    fp: np.ndarray,
    fold0: dict,
) -> dict:
    """Single-feature leakage canary across all 50 physical/hydrothermal channels (AUC <= 0.90)."""
    ys, xs = np.nonzero(fp)
    reg = fold0["region"][ys, xs]
    tr = fold0["truth"][ys, xs]
    vis_d = ndi.distance_transform_edt(~fold0["visible"])[ys, xs]
    neg = reg & ~tr & (vis_d > 3.0)
    pos_idx = np.flatnonzero(tr)
    rng = np.random.default_rng(20261024)
    neg_idx = rng.choice(np.flatnonzero(neg), size=min(40_000, int(neg.sum())), replace=False)
    idx = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate([np.ones(pos_idx.size, dtype=np.int8), np.zeros(neg_idx.size, dtype=np.int8)])

    rows = []
    for j, name in enumerate(physics.ALL_PHYS_FEATURES):
        v = np.asarray(X_phys_mm[idx, j], dtype=np.float64)
        auc = float(roc_auc_score(y, v)) if np.std(v) > 1e-12 else 0.5
        sym = max(auc, 1.0 - auc)
        rows.append({"feature": name, "group": "phys44", "roc_auc": round(auc, 6), "sym_auc": round(sym, 6)})
    for j, name in enumerate(gthc.GTHC_FEATURES):
        v = np.asarray(X_gthc_mm[idx, j], dtype=np.float64)
        auc = float(roc_auc_score(y, v)) if np.std(v) > 1e-12 else 0.5
        sym = max(auc, 1.0 - auc)
        rows.append({"feature": name, "group": "gthc6", "roc_auc": round(auc, 6), "sym_auc": round(sym, 6)})

    worst = max(rows, key=lambda r: r["sym_auc"])
    worst_gthc = max((r for r in rows if r["group"] == "gthc6"), key=lambda r: r["sym_auc"])
    return {
        "threshold_sym_auc": 0.90,
        "n_features_checked": len(rows),
        "passed": bool(worst["sym_auc"] <= 0.90),
        "max_sym_auc": worst["sym_auc"],
        "max_sym_auc_feature": worst["feature"],
        "max_gthc6_sym_auc": worst_gthc["sym_auc"],
        "max_gthc6_feature": worst_gthc["feature"],
        "gthc6_features": [r for r in rows if r["group"] == "gthc6"],
        "all_features": rows,
    }


def _pack_dots(emitted: np.ndarray) -> np.ndarray:
    dy, dx = np.nonzero(emitted > 0)
    return np.column_stack([dy, dx]).astype(np.int32)


def _unpack_dots(dyx: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    out = np.zeros(shape, dtype=np.float32)
    if dyx.size:
        out[dyx[:, 0], dyx[:, 1]] = 1.0
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="20,21", help="Comma-separated holdout seeds")
    ap.add_argument("--out", default="evidence/gthc88_holdout.json")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    t0 = time.monotonic()
    g = grid_mod.load_grid()
    cdir = ROOT / ".cache" / "gems88"
    cdir.mkdir(parents=True, exist_ok=True)

    X_phys_mm, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cdir)
    X_gthc_mm, _ = gthc.build_or_load_gthc_memmap(g, cdir)
    sense_src = adhr.build_sense_raster(ROOT / "data" / "external" / "trace_segments_utm11.csv", g)
    with rasterio.open(ROOT / "data" / "training_features.tif") as ds:
        det_elev = physics.clean_band(ds.read(12), g.footprint)[0]
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, cdir)

    ys_fp, xs_fp = np.nonzero(g.footprint)

    folds_by_seed = []
    for seed in seeds:
        folds, stats = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds, stats))

    print("[gthc88] Running 50-channel single-feature leakage canary ...", flush=True)
    canary = run_leakage_canary(X_phys_mm, X_gthc_mm, g.footprint, folds_by_seed[0][1][0])
    print(
        f"[gthc88] Canary passed={canary['passed']} max_sym_auc={canary['max_sym_auc']:.4f} "
        f"({canary['max_sym_auc_feature']}), max_gthc6={canary['max_gthc6_sym_auc']:.4f}",
        flush=True,
    )
    if not canary["passed"]:
        raise RuntimeError(f"Leakage canary failed: {canary['max_sym_auc_feature']}={canary['max_sym_auc']}")

    methods = list(ARMS)
    results_all = {m: [] for m in methods}
    terms_all = {m: None for m in methods}
    results_far = {m: [] for m in methods}
    terms_far = {m: None for m in methods}
    fold_records = []

    for seed, folds, _stats in folds_by_seed:
        vis = folds[0]["visible"]
        X_vis22, d_vis_fp, comp_len_fp = adhr.compute_visible_struct_fp(
            g, vis, sense_src, scarp_fields, cdir, f"seed{seed}"
        )
        d_vis_2d = adhr.scatter_fp(d_vis_fp, ys_fp, xs_fp, g.shape)
        far_mask = d_vis_2d > 10.0

        for fid, fold in enumerate(folds):
            fold_far = dict(fold, truth=fold["truth"] & far_mask)
            ckpt = cdir / f"gthc88_fold_s{seed}_f{fid}.npz"
            fseed = 8800 + seed * 100 + fid

            if not args.force and ckpt.is_file():
                z = np.load(ckpt, allow_pickle=False)
                em_by_arm = {
                    m: _unpack_dots(z[f"dots_{m}"], g.shape) for m in methods
                }
                meta_by_arm = json.loads(str(z["meta_json"]))
                print(f"[gthc88] Loaded cached seed={seed} fold={fold['name']} from {ckpt.name}", flush=True)
            else:
                tf = time.monotonic()
                train_regions = np.zeros(g.shape, dtype=bool)
                train_truth = np.zeros(g.shape, dtype=bool)
                for oid, o in enumerate(folds):
                    if oid != fid:
                        train_regions |= o["region"]
                        train_truth |= o["truth"]

                arms_out = gthc.predict_gthc_fold_arms(
                    g,
                    X_phys_mm,
                    X_gthc_mm,
                    X_vis22,
                    d_vis_fp,
                    comp_len_fp,
                    vis,
                    train_regions,
                    train_truth,
                    fold["region"],
                    seed=fseed,
                    n_ensemble=1,
                )
                em_by_arm = {
                    k: v["emitted"] for k, v in arms_out.items()
                }
                meta_by_arm = {
                    k: {
                        "n_dots": int(v["n_dots"]),
                        "k_est": float(v["k_est"]),
                        "surrogate_dti": float(v["surrogate_dti"]),
                    }
                    for k, v in arms_out.items()
                }
                save_kw = {f"dots_{m}": _pack_dots(em_by_arm[m]) for m in methods}
                save_kw["meta_json"] = np.array(json.dumps(meta_by_arm))
                np.savez_compressed(ckpt, **save_kw)
                print(
                    f"[gthc88] Computed & cached seed={seed} fold={fold['name']} in {time.monotonic()-tf:.1f}s",
                    flush=True,
                )

            rec = {
                "seed": seed,
                "fold": fold["name"],
                "withheld_positive_pixels": int(fold["truth"].sum()),
                "withheld_far_positive_pixels": int(fold_far["truth"].sum()),
            }
            for m in methods:
                em = em_by_arm[m]
                r_all, b_all = evaluate_holdout.evaluate(
                    em, fold, g.footprint, block_side=200, global_shape=g.shape
                )
                r_far, b_far = evaluate_holdout.evaluate(
                    em, fold_far, g.footprint, block_side=200, global_shape=g.shape
                )
                results_all[m].append(r_all)
                terms_all[m] = b_all if terms_all[m] is None else (terms_all[m] + b_all)
                results_far[m].append(r_far)
                terms_far[m] = b_far if terms_far[m] is None else (terms_far[m] + b_far)
                dd = d_vis_2d[em > 0]
                rec[m] = {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": evaluate_holdout.VERSION,
                    "dti_overall": round(r_all["dti"], 6),
                    "dti_far_gt10px": round(r_far["dti"], 6),
                    "emitted": int(r_all["n_emitted"]),
                    "share_le2": round(float((dd <= 2.0).mean()) if dd.size else 0.0, 4),
                    "share_gt25": round(float((dd > 25.0).mean()) if dd.size else 0.0, 4),
                }
            print(
                f"  -> seed={seed} {fold['name']}: "
                + " | ".join(
                    f"{m}: all={rec[m]['dti_overall']:.4f} far={rec[m]['dti_far_gt10px']:.4f} "
                    f"(n={rec[m]['emitted']}, gt25={rec[m]['share_gt25']:.3f})"
                    for m in ARMS
                ),
                flush=True,
            )
            fold_records.append(rec)

        del X_vis22, d_vis_fp, comp_len_fp, d_vis_2d, far_mask
        gc.collect()

    if len(seeds) < 2:
        print(f"[gthc88] Partial seed run ({seeds}) finished in {time.monotonic()-t0:.1f}s.", flush=True)
        return 0

    best_overall_arm = max(
        ARMS,
        key=lambda m: float(evaluate_holdout.from_terms(terms_all[m].sum(axis=0))),
    )
    best_far_arm = max(
        ARMS,
        key=lambda m: float(evaluate_holdout.from_terms(terms_far[m].sum(axis=0))),
    )

    overall_summary = evaluate_holdout.pooled_summary(
        terms_all, draws=1000, seed=882026, candidate=best_overall_arm
    )
    far_summary = evaluate_holdout.pooled_summary(
        terms_far, draws=1000, seed=882027, candidate=best_far_arm
    )

    sc_best_all = overall_summary["scores"][best_overall_arm]
    sc_best_far = far_summary["scores"][best_far_arm]
    beats_overall_recorded = bool(sc_best_all["dti"] > BAR_OVERALL)
    beats_overall_recomputed = bool(sc_best_all["dti"] > BAR_OVERALL_RECOMPUTED)
    beats_far_recorded = bool(sc_best_far["dti"] > BAR_FAR)

    payload = {
        "experiment_id": "GTHC-88",
        "preregistration": "registry/preregistration_gthc88.json",
        "hypothesis_dossier": "research/candidate-hypotheses-20261024-gthc88.md",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "seeds": seeds,
        "n_folds": len(fold_records),
        "bars": {
            "h88_adhr_overall_recorded": BAR_OVERALL,
            "h88_adhr_overall_recomputed": BAR_OVERALL_RECOMPUTED,
            "h88_adhr_far_gt10px_recorded": BAR_FAR,
        },
        "canary": canary,
        "best_overall_arm": best_overall_arm,
        "best_far_arm": best_far_arm,
        "beats_overall_recorded_bar": beats_overall_recorded,
        "beats_overall_recomputed_bar": beats_overall_recomputed,
        "beats_far_recorded_bar": beats_far_recorded,
        "overall_pooled": overall_summary,
        "far_gt10px_pooled": far_summary,
        "folds": fold_records,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[gthc88] Wrote {out_path} in {time.monotonic()-t0:.1f}s", flush=True)
    for m in methods:
        s_all = overall_summary["scores"][m]
        s_far = far_summary["scores"][m]
        print(
            f"  POOLED {m:20s}: overall={s_all['dti']:.6f} [{s_all['ci95'][0]:.6f}, {s_all['ci95'][1]:.6f}] | "
            f"far_gt10={s_far['dti']:.6f} [{s_far['ci95'][0]:.6f}, {s_far['ci95'][1]:.6f}]",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
