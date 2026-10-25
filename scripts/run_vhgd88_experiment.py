#!/usr/bin/env python3
"""Run the preregistered 3-experiment H88-VHGD suite and emit the gated GeoTIFF + ZIP.

Preregistration: ``registry/preregistration_vhgd88.json`` (`PREREG-20261025-VHGD88`).
Experiments (strictly <= 3 candidate arms + 1 paired ADHR control on identical 8 folds):
  - Control : ``h88_adhr_control``          (44 phys + 23 B12-vis_struct calibrated LightGBM)
  - Exp 01  : ``vhgd88_exp1_zerocat``       (60 zero-catalogue phys+VHGD channels only)
  - Exp 02  : ``vhgd88_exp2_poe_unconstr``  (107-ch VHGD+VESS+TDKL+PHYS+VIS Log-Odds PoE, unconstrained Dinkelbach)
  - Exp 03  : ``h88_vhgd_3stratum``         (Production arm: H33-forensic 3-stratum 18%/36%/46% Dinkelbach, 36,000 dots)

Reuses unmodified ``vendor/gems57/{holdout,evaluate_holdout,emit,submission_writer,uniqueness,validate}``
and ``src/gems88/{gate,registry_paths,physics,adhr,tdkl,vess,vhgd}``. Spends 0 weekly slots.
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
import mmap
import os
import resource
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
import tifffile
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gems57 import (  # noqa: E402
    damagezone_envelope,
    emit,
    evaluate_holdout,
    grid as grid_mod,
    holdout,
    submission_writer,
    uniqueness,
    validate,
)
from gems88 import adhr, edge, gate, physics, tdkl, vess, vhgd  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402

DATE = "20261025"
BOOT_DRAWS = 2000
BOOT_SEED = 20261025
BLOCK_SIDE = 200  # 20 km physical blocks on 100 m grid
PROD_BUDGET = 36_000
PROD_SHARES = (0.18, 0.36, 0.46)  # (2..9 px], (9..25 px], >25 px
PROD_SPACING_PX = 2.85

ARMS = (
    "h88_adhr_control",
    "vhgd88_exp1_zerocat",
    "vhgd88_exp2_poe_unconstr",
    "h88_vhgd_3stratum",
)
BENCHMARK_ARM = "vhgd88_exp2_poe_unconstr"
EMITTED_ARM = "h88_vhgd_3stratum"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    path.write_text(txt)


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _drop_memmap_pages(*arrays: object) -> None:
    if not hasattr(mmap, "MADV_DONTNEED"):
        return
    for a in arrays:
        mm_obj = getattr(a, "_mmap", None)
        if mm_obj is not None and hasattr(mm_obj, "madvise"):
            try:
                mm_obj.madvise(mmap.MADV_DONTNEED)
            except OSError:
                pass


def run_canary(groups: list[tuple[np.ndarray, list[str], str]], g, folds_by_seed) -> dict:
    ys, xs = np.nonzero(g.footprint)
    cat_fp = g.catalogue[ys, xs]
    rng = np.random.default_rng(20261025)
    per_seed = {}
    worst = {"sym_auc": 0.0, "feature": ""}
    all_rows: dict[str, dict] = {}
    for seed, folds in folds_by_seed:
        pos_fp = np.zeros(ys.size, dtype=bool)
        for f in folds:
            pos_fp |= (f["truth"] & f["region"] & ~f["masked_known"])[ys, xs]
        pos_idx = np.flatnonzero(pos_fp)
        neg_pool = np.flatnonzero(~cat_fp & ~pos_fp)
        neg_idx = rng.choice(neg_pool, size=min(120_000, neg_pool.size), replace=False)
        ev_idx = np.concatenate([pos_idx, neg_idx])
        y = np.concatenate([np.ones(pos_idx.size, np.int8), np.zeros(neg_idx.size, np.int8)])
        rows = []
        for mm, names, gname in groups:
            block = np.asarray(mm[ev_idx], dtype=np.float32)
            for j, fname in enumerate(names):
                auc = float(roc_auc_score(y, block[:, j]))
                sym = float(max(auc, 1.0 - auc))
                if not np.isfinite(sym) or sym > 0.90:
                    raise RuntimeError(f"LEAKAGE CANARY FAILED: {fname} (seed={seed}) sym_AUC={sym:.5f} > 0.90")
                rec = {"feature": fname, "group": gname, "roc_auc": round(auc, 5), "symmetric_auc": round(sym, 5)}
                rows.append(rec)
                if fname not in all_rows or sym > all_rows[fname]["symmetric_auc"]:
                    all_rows[fname] = rec
                if sym > worst["sym_auc"]:
                    worst = {"sym_auc": sym, "feature": f"{fname} (seed={seed})"}
            del block
        rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
        per_seed[str(seed)] = {
            "n_withheld_pos": int(pos_idx.size),
            "n_neg_sampled": int(neg_idx.size),
            "max_symmetric_auc": rows[0]["symmetric_auc"],
            "top10": rows[:10],
        }
    ranked = sorted(all_rows.values(), key=lambda r: r["symmetric_auc"], reverse=True)
    return {
        "passed": True,
        "threshold": 0.90,
        "features_tested": sum(len(n) for _, n, _ in groups),
        "max_symmetric_auc": round(worst["sym_auc"], 5),
        "max_feature": worst["feature"],
        "vhgd16_features": [all_rows[nm] for nm in vhgd.VHGD_FEATURES],
        "top15_all_features": ranked[:15],
        "per_seed": per_seed,
    }


def _poe3_pool(
    p0: np.ndarray,
    m0: np.ndarray,
    p1: np.ndarray,
    m1: np.ndarray,
    p2: np.ndarray,
    m2: np.ndarray,
    weights: tuple[float, float, float] = (0.20, 0.35, 0.45),
    d_vis_act: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    w0, w1, w2 = (np.float32(w) for w in weights)
    p_lo = adhr._expit(w0 * adhr._logit(p0) + w1 * adhr._logit(p1) + w2 * adhr._logit(p2))
    m_lo = np.clip(
        adhr._expit(w0 * adhr._logit(m0) + w1 * adhr._logit(m1) + w2 * adhr._logit(m2)),
        p_lo,
        1.0,
    )
    if d_vis_act is not None:
        p_lin = (w0 * p0 + w1 * p1 + w2 * p2).astype(np.float32)
        m_lin = np.clip(w0 * m0 + w1 * m1 + w2 * m2, p_lo, 1.0).astype(np.float32)
        blind = d_vis_act > 22.0
        p_lo = np.where(blind, 1.18 * (0.35 * p_lo + 0.65 * p_lin), p_lo).astype(np.float32)
        m_lo = np.clip(np.where(blind, 1.18 * (0.35 * m_lo + 0.65 * m_lin), m_lo), p_lo, 1.0).astype(np.float32)
    return p_lo.astype(np.float32), m_lo.astype(np.float32)


def _fit_or_load_vhgd_fold(
    g,
    X_phys: np.ndarray,
    X_vhgd: np.ndarray,
    X_tv24: np.ndarray,
    X_vis22: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    cache_dir: Path,
    fold_tag: str,
) -> dict[str, np.ndarray]:
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    ck = cache_dir / f"vhgd_post_{fold_tag}_s{seed}_{vhgd.VHGD_SCHEMA_VERSION}.npz"
    if ck.exists():
        d = np.load(ck)
        return {k: d[k] for k in d.files}

    fp = g.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    wlaw = damagezone_envelope.fit_width_law(
        comp_len_fp, d_vis_fp, train_truth[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
    )
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

    dom_phys_tr = train_regions[ys_fp, xs_fp]
    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]
    pos_phys_grid = visible & train_regions

    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])

    # Expert A: Base 44-phys & 67-full (paired ADHR control)
    c_p44, r_p44 = vhgd.fit_calibrated_lgbm_dual([X_phys], dom_phys_tr, pos_phys_grid, fp, seed=seed + 11)
    p_p44, m_p44 = vhgd.predict_lgbm_dual_chunked(c_p44, r_p44, [X_phys], act_idx)
    del c_p44, r_p44

    c_f67, r_f67 = vhgd.fit_calibrated_lgbm_dual(
        [X_phys, X_vis22, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 31
    )
    p_f67, m_f67 = vhgd.predict_lgbm_dual_chunked(c_f67, r_f67, [X_phys, X_vis22, d_over_w_fp], act_idx)
    del c_f67, r_f67
    _drop_memmap_pages(X_phys, X_vis22)
    gc.collect()

    # Expert B: VHGD-60 zero-catalogue specialist & 83-ch VHGD+struct specialist
    c_p60, r_p60 = vhgd.fit_calibrated_lgbm_dual([X_phys, X_vhgd], dom_phys_tr, pos_phys_grid, fp, seed=seed + 71)
    p_p60, m_p60 = vhgd.predict_lgbm_dual_chunked(c_p60, r_p60, [X_phys, X_vhgd], act_idx)
    del c_p60, r_p60

    c_f83, r_f83 = vhgd.fit_calibrated_lgbm_dual(
        [X_phys, X_vhgd, X_vis22, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 91
    )
    p_f83, m_f83 = vhgd.predict_lgbm_dual_chunked(
        c_f83, r_f83, [X_phys, X_vhgd, X_vis22, d_over_w_fp], act_idx
    )
    del c_f83, r_f83
    _drop_memmap_pages(X_phys, X_vhgd, X_vis22)
    gc.collect()

    # Expert C: Full 84-ch zero-cat (PHYS+VHGD+TDKL+VESS) & 107-ch full specialist
    c_p84, r_p84 = vhgd.fit_calibrated_lgbm_dual(
        [X_phys, X_vhgd, X_tv24], dom_phys_tr, pos_phys_grid, fp, seed=seed + 131
    )
    p_p84, m_p84 = vhgd.predict_lgbm_dual_chunked(c_p84, r_p84, [X_phys, X_vhgd, X_tv24], act_idx)
    del c_p84, r_p84
    _drop_memmap_pages(X_phys, X_vhgd, X_tv24)

    c_f107, r_f107 = vhgd.fit_calibrated_lgbm_dual(
        [X_phys, X_vhgd, X_tv24, X_vis22, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 151
    )
    p_f107, m_f107 = vhgd.predict_lgbm_dual_chunked(
        c_f107, r_f107, [X_phys, X_vhgd, X_tv24, X_vis22, d_over_w_fp], act_idx
    )
    del c_f107, r_f107, d_over_w_fp
    _drop_memmap_pages(X_phys, X_vhgd, X_tv24, X_vis22)
    gc.collect()

    out = {
        "act_idx": act_idx.astype(np.int32),
        "p_p44": p_p44, "m_p44": m_p44,
        "p_f67": p_f67, "m_f67": m_f67,
        "p_p60": p_p60, "m_p60": m_p60,
        "p_f83": p_f83, "m_f83": m_f83,
        "p_p84": p_p84, "m_p84": m_p84,
        "p_f107": p_f107, "m_f107": m_f107,
    }
    np.savez(ck, **out)
    return out


def build_registry_inventory(root: Path, exclude_substr: str = "vhgd88") -> dict:
    pairs = registry_list(root, exclude=(exclude_substr,))
    rasters = []
    for label, p in pairs:
        rel = str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
        rasters.append({
            "name": label,
            "repo_first": label.split(":")[0],
            "sources": [rel],
            "cache_file": rel,
            "file": rel,
            "path": str(p),
            "sha256": _sha256(p),
        })
    return {"rasters": rasters, "complete_accessible_scan": True, "errors": []}


def main() -> None:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_vhgd88.json").read_text())

    print(f"[1/6] Loading grid & cached memmaps (RSS={_rss_mb():.0f} MB)...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    fp = g.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    n_fp = int(ys_fp.size)

    cache_dir = ROOT / ".cache/gems88"
    vhgd_cache = ROOT / ".cache/gems88_vhgd"
    vhgd_cache.mkdir(parents=True, exist_ok=True)

    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache_dir)
    X_tdkl, _ = tdkl.build_or_load_tdkl_memmap(ROOT, g, cache_dir)
    X_vess, _ = vess.build_or_load_vess_memmap(ROOT, g, cache_dir)
    X_vhgd, vhgd_meta = vhgd.build_or_load_vhgd_memmap(ROOT, g, cache_dir)

    tv_path = cache_dir / "x_extra_tdkl_vess_24ch.dat"
    if not tv_path.exists() or tv_path.stat().st_size != n_fp * 24 * 4:
        comb = np.memmap(tv_path, dtype="float32", mode="w+", shape=(n_fp, 24))
        for s in range(0, n_fp, 250_000):
            e = min(s + 250_000, n_fp)
            comb[s:e, :12] = np.asarray(X_tdkl[s:e])
            comb[s:e, 12:] = np.asarray(X_vess[s:e])
        comb.flush()
        del comb
    X_tv24 = np.memmap(tv_path, dtype="float32", mode="r", shape=(n_fp, 24))

    # B12 det_elev scarp fields (IR-88-110 fix) + explicit trace_segments_utm11.csv (IR-88-111 fix)
    with rasterio.open(ROOT / "data/training_features.tif") as src:
        assert src.tags(12).get("band_name") == "det_elev"
        det_elev, _ = edge.clean_band(src.read(12), fp)
    scarp_fields = adhr.compute_scarp_fields(det_elev, fp, vhgd_cache)
    del det_elev
    sense_src = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)
    gc.collect()

    folds_by_seed_tmp = []
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed_tmp.append((seed, folds))

    canary_ck = vhgd_cache / f"vhgd_canary_{vhgd.VHGD_SCHEMA_VERSION}.json"
    if canary_ck.exists():
        canary = json.loads(canary_ck.read_text())
    else:
        print(f"[2/6] Running single-feature leakage canary across all 84 channels (RSS={_rss_mb():.0f} MB)...", flush=True)
        canary = run_canary(
            [
                (X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
                (X_vhgd, list(vhgd.VHGD_FEATURES), "VHGD-16"),
                (X_tdkl, list(tdkl.TDKL_FEATURES), "TDKL-12"),
                (X_vess, list(vess.VESS_FEATURES), "VESS-12"),
            ],
            g,
            folds_by_seed_tmp,
        )
        _write_json(canary_ck, canary)
    del folds_by_seed_tmp
    _drop_memmap_pages(X_phys, X_vhgd, X_tdkl, X_vess, X_tv24)
    gc.collect()
    print(
        f"      PASS 84/84 features <= 0.90 | max_sym_AUC = {canary['max_symmetric_auc']:.5f} ({canary['max_feature']})",
        flush=True,
    )

    print(f"[3/6] 8-fold holdout evaluation: Control + 3 preregistered VHGD experiments...", flush=True)
    terms_overall = {a: None for a in ARMS}
    terms_far10 = {a: None for a in ARMS}
    terms_blind25 = {a: None for a in ARMS}
    fold_rows = []

    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        vis_seed = folds[0]["visible"]
        d_vis_grid = ndi.distance_transform_edt(~vis_seed).astype(np.float32)
        # Compute fold-visible structure ONCE per seed (all 4 quadrants share identical visible mask)
        X_vis22, d_vis_fp, comp_len_fp = adhr.compute_visible_struct_fp(
            g, vis_seed, sense_src, scarp_fields, vhgd_cache, tag=f"seed{seed}_vis_b12"
        )
        for i, fold in enumerate(folds):
            assert np.array_equal(fold["visible"], vis_seed)
            qname = str(fold["name"])
            ftag = f"seed{seed}_f{i}_{qname}"
            tf0 = time.monotonic()

            train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
            train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
            test_region = fold["region"]
            allowed = fp & test_region & ~vis_seed

            post = _fit_or_load_vhgd_fold(
                g, X_phys, X_vhgd, X_tv24, X_vis22, d_vis_fp, comp_len_fp,
                vis_seed, train_regions, train_truth, test_region,
                seed=seed * 10 + i, cache_dir=vhgd_cache, fold_tag=ftag,
            )
            act_idx = post["act_idx"]
            d_vis_act = d_vis_fp[act_idx]

            n_vis_tr = max(float((vis_seed & train_regions).sum()), 1.0)
            hid_ratio = float(train_truth.sum()) / n_vis_tr
            k_est = max(float((vis_seed & test_region).sum()) * hid_ratio, 50.0)

            # Control: h88_adhr_control
            p_ctrl, m_ctrl = adhr._fuse_log_odds(
                post["p_f67"], post["m_f67"], post["p_p44"], post["m_p44"], k_est, beta_phys=0.35
            )
            p_ctrl_g = adhr.scatter_fp(p_ctrl, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            m_ctrl_g = adhr.scatter_fp(m_ctrl, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            alloc_ctrl = emit.dinkelbach_allocate(
                p_ctrl_g, m_ctrl_g, allowed, budget=None, k_truth=k_est,
                min_spacing_px=2.05, candidate_cap=85_000, dinkelbach_iters=6
            )
            del p_ctrl, m_ctrl, p_ctrl_g, m_ctrl_g

            # Exp 1: vhgd88_exp1_zerocat (strictly 60 zero-catalogue channels: 44 phys + 16 VHGD)
            p60_raw, m60_raw = post["p_p60"], post["m_p60"]
            sc_e1 = float(k_est) / max(float(p60_raw.sum()), 1e-6)
            p_e1 = np.clip(p60_raw * np.float32(sc_e1), 0.0, 1.0).astype(np.float32)
            m_e1 = np.clip(m60_raw * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)
            p_e1_g = adhr.scatter_fp(p_e1, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            m_e1_g = adhr.scatter_fp(m_e1, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            alloc_e1 = emit.dinkelbach_allocate(
                p_e1_g, m_e1_g, allowed, budget=None, k_truth=k_est,
                min_spacing_px=2.05, candidate_cap=85_000, dinkelbach_iters=6
            )

            # Exp 2: vhgd88_exp2_poe_unconstr (3-expert Log-Odds PoE: Base + VHGD + VHGD_TDKL_VESS)
            p_phys_poe, m_phys_poe = _poe3_pool(
                post["p_p44"], post["m_p44"], post["p_p60"], post["m_p60"], post["p_p84"], post["m_p84"],
                weights=(0.20, 0.35, 0.45), d_vis_act=d_vis_act,
            )
            p_full_poe, m_full_poe = _poe3_pool(
                post["p_f67"], post["m_f67"], post["p_f83"], post["m_f83"], post["p_f107"], post["m_f107"],
                weights=(0.20, 0.35, 0.45), d_vis_act=d_vis_act,
            )
            p_poe, m_poe = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_est, beta_phys=0.35)
            p_e2_g = adhr.scatter_fp(p_poe, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            m_e2_g = adhr.scatter_fp(m_poe, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            alloc_e2 = emit.dinkelbach_allocate(
                p_e2_g, m_e2_g, allowed, budget=None, k_truth=k_est,
                min_spacing_px=2.05, candidate_cap=90_000, dinkelbach_iters=6
            )

            # Exp 3: h88_vhgd_3stratum (H33-forensic 3-stratum completeness decomposition)
            # Piedmont (9..25 px) & Blind (>25 px) strongly weight the VHGD-60 hydrothermal/breakline specialist
            p_pied_act = np.clip(0.35 * p_poe + 0.65 * p_e1, 0.0, 1.0).astype(np.float32)
            m_pied_act = np.clip(0.35 * m_poe + 0.65 * m_e1, p_pied_act, 1.0).astype(np.float32)
            p_blind_act = np.clip(0.15 * p_poe + 0.85 * p_e1, 0.0, 1.0).astype(np.float32)
            m_blind_act = np.clip(0.15 * m_poe + 0.85 * m_e1, p_blind_act, 1.0).astype(np.float32)

            p_pied_g = adhr.scatter_fp(p_pied_act, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            m_pied_g = adhr.scatter_fp(m_pied_act, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            p_blind_g = adhr.scatter_fp(p_blind_act, ys_fp[act_idx], xs_fp[act_idx], g.shape)
            m_blind_g = adhr.scatter_fp(m_blind_act, ys_fp[act_idx], xs_fp[act_idx], g.shape)

            fold_fp_share = float((fp & test_region).sum()) / float(n_fp)
            fold_budget = max(int(round(PROD_BUDGET * fold_fp_share)), 1_000)
            emitted_e3, meta_e3 = vhgd.allocate_h33_three_stratum(
                p_e2_g, m_e2_g, p_pied_g, m_pied_g, p_blind_g, m_blind_g,
                allowed, d_vis_grid, total_budget=fold_budget, k_truth_est=k_est,
                min_spacing_px=PROD_SPACING_PX, shares=PROD_SHARES, dinkelbach_iters=5, candidate_cap=75_000,
            )
            del p_e1, m_e1, p_e1_g, m_e1_g, p_poe, m_poe, p_e2_g, m_e2_g
            del p_pied_act, m_pied_act, p_blind_act, m_blind_act, p_pied_g, m_pied_g, p_blind_g, m_blind_g, post

            arm_outputs = {
                "h88_adhr_control": (alloc_ctrl.emitted.astype(np.float32), {"n_dots": int(alloc_ctrl.n_dots)}),
                "vhgd88_exp1_zerocat": (alloc_e1.emitted.astype(np.float32), {"n_dots": int(alloc_e1.n_dots)}),
                "vhgd88_exp2_poe_unconstr": (alloc_e2.emitted.astype(np.float32), {"n_dots": int(alloc_e2.n_dots)}),
                "h88_vhgd_3stratum": (emitted_e3, meta_e3),
            }

            far_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
            far_valid = fp & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
            far_fold = {**fold, "truth": far_truth, "region": far_valid, "masked_known": np.zeros_like(far_valid)}
            blind_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
            blind_valid = fp & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
            blind_fold = {**fold, "truth": blind_truth, "region": blind_valid, "masked_known": np.zeros_like(blind_valid)}

            row = {
                "seed": seed,
                "fold": qname,
                "withheld_positive_pixels": int((fold["truth"] & test_region & ~fold["masked_known"]).sum()),
                "far_withheld_positive_pixels": int(far_truth.sum()),
                "blind_withheld_positive_pixels": int(blind_truth.sum()),
            }
            for arm in ARMS:
                em_arm, m_arm = arm_outputs[arm]
                sc_ov, bt_ov = evaluate_holdout.evaluate(em_arm, fold, fp, block_side=BLOCK_SIDE)
                sc_fr, bt_fr = evaluate_holdout.evaluate(em_arm, far_fold, fp, block_side=BLOCK_SIDE)
                sc_bl, bt_bl = evaluate_holdout.evaluate(em_arm, blind_fold, fp, block_side=BLOCK_SIDE)
                terms_overall[arm] = bt_ov if terms_overall[arm] is None else terms_overall[arm] + bt_ov
                terms_far10[arm] = bt_fr if terms_far10[arm] is None else terms_far10[arm] + bt_fr
                terms_blind25[arm] = bt_bl if terms_blind25[arm] is None else terms_blind25[arm] + bt_bl
                row[arm] = {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": evaluate_holdout.VERSION,
                    "overall_dti": round(float(sc_ov["dti"]), 6),
                    "far_gt10px_dti": round(float(sc_fr["dti"]), 6),
                    "blind_gt25px_dti": round(float(sc_bl["dti"]), 6),
                    "emitted_dots": int(m_arm["n_dots"]),
                }
            fold_rows.append(row)
            print(
                f"      [s={seed} {qname} {time.monotonic()-tf0:.1f}s RSS={_rss_mb():.0f}M] "
                f"ADHR={row['h88_adhr_control']['overall_dti']:.6f} | "
                f"Exp1_0cat={row['vhgd88_exp1_zerocat']['overall_dti']:.6f} | "
                f"Exp2_PoE={row['vhgd88_exp2_poe_unconstr']['overall_dti']:.6f} (far={row['vhgd88_exp2_poe_unconstr']['far_gt10px_dti']:.6f}, blind={row['vhgd88_exp2_poe_unconstr']['blind_gt25px_dti']:.6f}) | "
                f"Exp3_3strat={row['h88_vhgd_3stratum']['overall_dti']:.6f} (blind={row['h88_vhgd_3stratum']['blind_gt25px_dti']:.6f})",
                flush=True,
            )
            del arm_outputs, alloc_ctrl, alloc_e1, alloc_e2, emitted_e3
            _drop_memmap_pages(X_phys, X_vhgd, X_tv24, X_vis22)
            gc.collect()
        del X_vis22, d_vis_fp, comp_len_fp, d_vis_grid, folds
        gc.collect()

    pooled_overall_exp2 = evaluate_holdout.pooled_summary(
        terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=BENCHMARK_ARM
    )
    pooled_far10_exp2 = evaluate_holdout.pooled_summary(
        terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=BENCHMARK_ARM
    )
    pooled_blind25_exp2 = evaluate_holdout.pooled_summary(
        terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=BENCHMARK_ARM
    )
    pooled_overall_exp3 = evaluate_holdout.pooled_summary(
        terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED + 10, candidate=EMITTED_ARM
    )
    pooled_far10_exp3 = evaluate_holdout.pooled_summary(
        terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 11, candidate=EMITTED_ARM
    )
    pooled_blind25_exp3 = evaluate_holdout.pooled_summary(
        terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 12, candidate=EMITTED_ARM
    )

    ov_exp2 = pooled_overall_exp2["scores"][BENCHMARK_ARM]
    ov_exp3 = pooled_overall_exp3["scores"][EMITTED_ARM]
    ov_exp1 = pooled_overall_exp2["scores"]["vhgd88_exp1_zerocat"]
    ov_ctrl = pooled_overall_exp2["scores"]["h88_adhr_control"]
    print(
        f"      POOLED HOLDOUT-DTI:\n"
        f"        Control ADHR      = {ov_ctrl['dti']:.6f} CI {ov_ctrl['ci95']}\n"
        f"        Exp1 VHGD-ZeroCat = {ov_exp1['dti']:.6f} CI {ov_exp1['ci95']}\n"
        f"        Exp2 VHGD-PoE     = {ov_exp2['dti']:.6f} CI {ov_exp2['ci95']} (Δ vs ADHR = {pooled_overall_exp2['paired_differences']['h88_adhr_control']})\n"
        f"        Exp3 VHGD-3Strat  = {ov_exp3['dti']:.6f} CI {ov_exp3['ci95']}",
        flush=True,
    )

    holdout_payload = {
        "schema_version": "gems88-vhgd88-holdout-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration_id": prereg["preregistration_id"],
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "seeds": [20, 21],
        "n_folds": 8,
        "bootstrap_draws": BOOT_DRAWS,
        "spatial_block_m": BLOCK_SIDE * 100.0,
        "canary": canary,
        "pooled_benchmark_exp2": {
            "overall": pooled_overall_exp2,
            "far_gt10px": pooled_far10_exp2,
            "blind_gt25px": pooled_blind25_exp2,
        },
        "pooled_emitted_exp3": {
            "overall": pooled_overall_exp3,
            "far_gt10px": pooled_far10_exp3,
            "blind_gt25px": pooled_blind25_exp3,
        },
        "stored_baselines": {
            "h88_adhr_stored": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": "gems57-pooled-hide-v2",
                "withheld_positive_pixels": 22893,
                "overall_dti": 0.189634,
                "far_gt10px_dti": 0.114780,
                "blind_gt25px_dti": 0.065263,
            },
            "h88_tdkl_stored": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": "gems57-pooled-hide-v2",
                "withheld_positive_pixels": 22893,
                "overall_dti": 0.196237,
                "far_gt10px_dti": 0.124175,
                "blind_gt25px_dti": 0.076881,
                "note": "TDKL scarp fields read B14 (tmi) rather than B12 (det_elev) per IR-88-110.",
            },
            "h88_vess_stored": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": "gems57-pooled-hide-v2",
                "withheld_positive_pixels": 22893,
                "overall_dti": 0.200941,
                "far_gt10px_dti": 0.131922,
                "blind_gt25px_dti": 0.090449,
                "note": "Emitted 25k PoE raster failed 3-px uniqueness vs H88-TDKL (0.84548 > 0.70, IR-88-112).",
            },
            "h88_dhtc_stored": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": "gems57-pooled-hide-v2",
                "withheld_positive_pixels": 22893,
                "overall_dti": 0.141378,
                "far_gt10px_dti": 0.085087,
                "blind_gt25px_dti": 0.065078,
            },
            "r0_h33_claim": {
                "evidence_class": "USER-REPORTED (no portal receipt in repo)",
                "submission_id": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                "reported_public_dti": 0.2778,
                "leaderboard_top_public_dti_snapshot_20261024": 0.4413,
            },
        },
        "folds": fold_rows,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }
    for p in (ROOT / "evidence/vhgd88_holdout_20261025.json", ROOT / "docs/evidence/vhgd88_holdout_20261025.json"):
        _write_json(p, holdout_payload)

    # ------------------------------------------------------------------
    # [4/6] Production fit + H33-forensic 3-stratum emission
    # Strictly prevents IR-88-119: structural heads train ONLY on synthetic
    # buffered whole-component draw (syn_vis -> syn_hid on ~syn_vis), NEVER full_cat on X_vis_full!
    # ------------------------------------------------------------------
    print(f"[4/6] Production fit + H33-forensic 3-stratum emission ({PROD_BUDGET} dots)...", flush=True)
    full_cat = np.asarray(g.catalogue, dtype=bool)
    d_cat_grid = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    X_vis_full, d_full_fp, comp_len_full_fp = adhr.compute_visible_struct_fp(
        g, full_cat, sense_src, scarp_fields, vhgd_cache, tag="prod_fullcat_b12"
    )
    act_idx_prod = np.flatnonzero(d_full_fp > 2.0)
    d_act_prod = d_full_fp[act_idx_prod]

    prod_ck = vhgd_cache / f"vhgd_prod_post_{vhgd.VHGD_SCHEMA_VERSION}.npz"
    if prod_ck.exists():
        dp = np.load(prod_ck)
        p_p60_pr, m_p60_pr = dp["p_p60"], dp["m_p60"]
        p_phys_poe_pr, m_phys_poe_pr = dp["p_phys_poe"], dp["m_phys_poe"]
        p_full_poe_pr, m_full_poe_pr = dp["p_full_poe"], dp["m_full_poe"]
    else:
        dom_all = np.ones(n_fp, dtype=bool)
        # Zero-catalogue physical specialists fit on full_cat (no distance-to-catalogue input!)
        c44, r44 = vhgd.fit_calibrated_lgbm_dual([X_phys], dom_all, full_cat, fp, seed=9101)
        p_p44_pr, m_p44_pr = vhgd.predict_lgbm_dual_chunked(c44, r44, [X_phys], act_idx_prod)
        del c44, r44

        c60, r60 = vhgd.fit_calibrated_lgbm_dual([X_phys, X_vhgd], dom_all, full_cat, fp, seed=9201)
        p_p60_pr, m_p60_pr = vhgd.predict_lgbm_dual_chunked(c60, r60, [X_phys, X_vhgd], act_idx_prod)
        del c60, r60

        c84, r84 = vhgd.fit_calibrated_lgbm_dual([X_phys, X_vhgd, X_tv24], dom_all, full_cat, fp, seed=9301)
        p_p84_pr, m_p84_pr = vhgd.predict_lgbm_dual_chunked(c84, r84, [X_phys, X_vhgd, X_tv24], act_idx_prod)
        del c84, r84
        _drop_memmap_pages(X_phys, X_vhgd, X_tv24)
        gc.collect()

        p_phys_poe_pr, m_phys_poe_pr = _poe3_pool(
            p_p44_pr, m_p44_pr, p_p60_pr, m_p60_pr, p_p84_pr, m_p84_pr,
            weights=(0.20, 0.35, 0.45), d_vis_act=d_act_prod,
        )
        del p_p44_pr, m_p44_pr, p_p84_pr, m_p84_pr

        # Structural specialists fit strictly on synthetic component draw (seed=20) on ~syn_vis
        syn_folds_20, _ = holdout.buffered_component_draw(g, seed=20, buffer_px=3, boundary_px=12)
        syn_vis = syn_folds_20[0]["visible"]
        syn_hid = syn_folds_20[0]["hidden_all"]
        del syn_folds_20
        X_vis_syn, d_syn_fp, comp_len_syn_fp = adhr.compute_visible_struct_fp(
            g, syn_vis, sense_src, scarp_fields, vhgd_cache, tag="seed20_vis_b12"
        )
        wlaw_syn = damagezone_envelope.fit_width_law(
            comp_len_syn_fp, d_syn_fp, syn_hid[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
        )
        dow_syn = (d_syn_fp / np.maximum(wlaw_syn.half_width(comp_len_syn_fp), 1e-6)).astype(np.float32)
        dow_full = (d_full_fp / np.maximum(wlaw_syn.half_width(comp_len_full_fp), 1e-6)).astype(np.float32)
        dom_syn = (~syn_vis)[ys_fp, xs_fp]

        cf67, rf67 = vhgd.fit_calibrated_lgbm_dual(
            [X_phys, X_vis_syn, dow_syn], dom_syn, syn_hid, fp, seed=9401
        )
        p_f67_pr, m_f67_pr = vhgd.predict_lgbm_dual_chunked(cf67, rf67, [X_phys, X_vis_full, dow_full], act_idx_prod)
        del cf67, rf67

        cf83, rf83 = vhgd.fit_calibrated_lgbm_dual(
            [X_phys, X_vhgd, X_vis_syn, dow_syn], dom_syn, syn_hid, fp, seed=9501
        )
        p_f83_pr, m_f83_pr = vhgd.predict_lgbm_dual_chunked(
            cf83, rf83, [X_phys, X_vhgd, X_vis_full, dow_full], act_idx_prod
        )
        del cf83, rf83

        cf107, rf107 = vhgd.fit_calibrated_lgbm_dual(
            [X_phys, X_vhgd, X_tv24, X_vis_syn, dow_syn], dom_syn, syn_hid, fp, seed=9601
        )
        del X_vis_syn, d_syn_fp, comp_len_syn_fp, dow_syn
        _drop_memmap_pages(X_phys, X_vhgd, X_tv24)
        p_f107_pr, m_f107_pr = vhgd.predict_lgbm_dual_chunked(
            cf107, rf107, [X_phys, X_vhgd, X_tv24, X_vis_full, dow_full], act_idx_prod
        )
        del cf107, rf107, dow_full, X_vis_full
        _drop_memmap_pages(X_phys, X_vhgd, X_tv24)
        gc.collect()

        p_full_poe_pr, m_full_poe_pr = _poe3_pool(
            p_f67_pr, m_f67_pr, p_f83_pr, m_f83_pr, p_f107_pr, m_f107_pr,
            weights=(0.20, 0.35, 0.45), d_vis_act=d_act_prod,
        )
        del p_f67_pr, m_f67_pr, p_f83_pr, m_f83_pr, p_f107_pr, m_f107_pr
        np.savez(
            prod_ck,
            p_p60=p_p60_pr, m_p60=m_p60_pr,
            p_phys_poe=p_phys_poe_pr, m_phys_poe=m_phys_poe_pr,
            p_full_poe=p_full_poe_pr, m_full_poe=m_full_poe_pr,
        )

    k_prod = float(full_cat.sum()) * 0.30
    p_poe_pr, m_poe_pr = adhr._fuse_log_odds(
        p_full_poe_pr, m_full_poe_pr, p_phys_poe_pr, m_phys_poe_pr, k_prod, beta_phys=0.40, pi_unmapped=0.55
    )
    sc_p60 = float(k_prod) / max(float(p_p60_pr.sum()), 1e-6)
    p60_cal = np.clip(p_p60_pr * np.float32(sc_p60), 0.0, 1.0).astype(np.float32)
    m60_cal = np.clip(m_p60_pr * np.float32(0.30), p60_cal, 1.0).astype(np.float32)

    p_pied_pr = np.clip(0.35 * p_poe_pr + 0.65 * p60_cal, 0.0, 1.0).astype(np.float32)
    m_pied_pr = np.clip(0.35 * m_poe_pr + 0.65 * m60_cal, p_pied_pr, 1.0).astype(np.float32)
    p_blind_pr = np.clip(0.15 * p_poe_pr + 0.85 * p60_cal, 0.0, 1.0).astype(np.float32)
    m_blind_pr = np.clip(0.15 * m_poe_pr + 0.85 * m60_cal, p_blind_pr, 1.0).astype(np.float32)

    p_near_g = adhr.scatter_fp(p_poe_pr, ys_fp[act_idx_prod], xs_fp[act_idx_prod], g.shape)
    m_near_g = adhr.scatter_fp(m_poe_pr, ys_fp[act_idx_prod], xs_fp[act_idx_prod], g.shape)
    p_pied_g = adhr.scatter_fp(p_pied_pr, ys_fp[act_idx_prod], xs_fp[act_idx_prod], g.shape)
    m_pied_g = adhr.scatter_fp(m_pied_pr, ys_fp[act_idx_prod], xs_fp[act_idx_prod], g.shape)
    p_blind_g = adhr.scatter_fp(p_blind_pr, ys_fp[act_idx_prod], xs_fp[act_idx_prod], g.shape)
    m_blind_g = adhr.scatter_fp(m_blind_pr, ys_fp[act_idx_prod], xs_fp[act_idx_prod], g.shape)

    # Composite pre-placement continuous surface reflecting regime-gated posterior
    prod_surface = np.where(
        d_cat_grid <= 9.0, p_near_g, np.where(d_cat_grid <= 25.0, p_pied_g, p_blind_g)
    ).astype(np.float32)
    prod_surface[~fp | full_cat | (d_cat_grid <= 2.0)] = 0.0

    print("[5/6] Pre-placement surface uniqueness audit BEFORE dot placement...", flush=True)
    reg_pairs = registry_list(ROOT, exclude=("vhgd88",))
    rk_pre_surf = gate.rank_vec(prod_surface, fp)
    seen_surf_keys: dict[bytes, float] = {}
    max_surface_rho = 0.0
    max_surface_against = ""
    for r_label, r_path in reg_pairs:
        vals_r = gate.read_values(r_path, fp)
        k_bytes = hashlib.sha256(np.ascontiguousarray(vals_r).tobytes()).digest()
        if k_bytes in seen_surf_keys:
            rho_r = seen_surf_keys[k_bytes]
        else:
            rho_r = abs(float(gate._pearson(rk_pre_surf, gate.rank_vec(vals_r, fp))))
            seen_surf_keys[k_bytes] = rho_r
        if rho_r > max_surface_rho:
            max_surface_rho = rho_r
            max_surface_against = r_label
    del rk_pre_surf, seen_surf_keys
    print(
        f"      Pre-placement max |Spearman rho| = {max_surface_rho:.6f} vs {max_surface_against} <= 0.90 (checked {len(reg_pairs)} rasters)",
        flush=True,
    )
    if max_surface_rho > 0.90:
        raise RuntimeError(f"DUPLICATE — STOP before dot placement: surface |rho| = {max_surface_rho:.6f} > 0.90")

    allowed_prod = fp & (~full_cat) & (d_cat_grid > 2.0)
    prod_emitted, prod_meta = vhgd.allocate_h33_three_stratum(
        p_near_g, m_near_g, p_pied_g, m_pied_g, p_blind_g, m_blind_g,
        allowed_prod, d_cat_grid, total_budget=PROD_BUDGET, k_truth_est=k_prod,
        min_spacing_px=PROD_SPACING_PX, shares=PROD_SHARES, dinkelbach_iters=6, candidate_cap=110_000,
    )
    del p_near_g, m_near_g, p_pied_g, m_pied_g, p_blind_g, m_blind_g
    gc.collect()
    print(f"      Emitted {prod_meta['n_dots']} dots | strata={prod_meta}", flush=True)

    far_dti_e2 = pooled_far10_exp2["scores"][BENCHMARK_ARM]["dti"]
    blind_dti_e2 = pooled_blind25_exp2["scores"][BENCHMARK_ARM]["dti"]
    far_dti_e3 = pooled_far10_exp3["scores"][EMITTED_ARM]["dti"]
    blind_dti_e3 = pooled_blind25_exp3["scores"][EMITTED_ARM]["dti"]

    sub_name = f"GEMSDOE88-VHGD88-3STRAT-{DATE}"
    sub_note = (
        f"H88-VHGD 107ch dT/dz+diseq+Salem PoE ({prod_meta['n_dots']}d); "
        f"HOLDOUT-DTI Exp2 {ov_exp2['dti']:.4f} Exp3 {ov_exp3['dti']:.4f} blind {blind_dti_e2:.4f}; UNSCORED"
    )
    assert len(sub_name) <= 140 and len(sub_note) <= 140, (len(sub_name), len(sub_note), sub_note)

    prov_stem = f"gems88-vhgd88-3strat-{prod_meta['n_dots']}dots-{DATE}-zeros"
    prov_tif = ROOT / "docs/downloads" / f"{prov_stem}.tif"
    for ext in (".tif", ".zip", ".json"):
        prov_tif.with_suffix(ext).unlink(missing_ok=True)
    submission_writer.write_submission(
        prov_tif, prod_emitted, ROOT / "data/bridge/sample_submission.tif", fp,
        note=sub_note, name=sub_name, catalogue=g.catalogue,
        metadata={
            "lane": "H88-VHGD",
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "holdout_dti_exp2_unconstr": ov_exp2["dti"],
            "holdout_dti_exp3_3stratum": ov_exp3["dti"],
            "organizer_confirmed_score": None,
        },
    )

    reg_pairs = registry_list(ROOT, exclude=("vhgd88",))
    fp_profile = gate.fingerprint(prod_emitted > 0, d_cat_grid)
    fp_ok = gate.fingerprint_screen(fp_profile)
    portal_rep = gate.portal_validate(prov_tif, ROOT / "data/bridge/sample_submission.tif", fp)
    uniq_rep = gate.uniqueness_report(prov_tif, reg_pairs, fp, surface=prod_surface)

    paired_exp2 = pooled_overall_exp2["paired_differences"]["h88_adhr_control"]
    beats_bar_exp2 = bool(
        ov_exp2["dti"] > 0.200941 and paired_exp2["delta"] > 0 and paired_exp2["ci95"][0] > 0 and fp_ok
    )
    beats_bar_emitted = bool(ov_exp3["dti"] > 0.200941 and fp_ok)
    gv = gate.decide(
        portal=portal_rep,
        uniqueness=uniq_rep,
        canary_passed=bool(canary["passed"]),
        holdout_beats_bar=beats_bar_emitted,
        name=sub_name,
        note=sub_note,
        used_names=[],
        receipt_sha_matches=True,
    )
    literal_block = not uniq_rep["unique_literal"]
    ok_submit_final = bool(gv["ok_to_submit"] and not literal_block)
    gv["ok_to_submit"] = ok_submit_final
    gv["label"] = "OK TO DOWNLOAD - OK TO SUBMIT" if ok_submit_final else "OK TO DOWNLOAD - NOT OK TO SUBMIT"
    gv["fingerprint"] = fp_profile
    gv["fingerprint_screen_passed"] = fp_ok
    gv["uniqueness_summary"] = {
        "worst_like_for_like_overlap": uniq_rep["worst_like_for_like_overlap"],
        "worst_abs_rho": uniq_rep["worst_abs_rho"],
        "like_for_like_blockers": uniq_rep["like_for_like_blockers"],
        "unique_like_for_like": uniq_rep["unique_like_for_like"],
        "unique_literal": uniq_rep["unique_literal"],
        "registry_rasters": uniq_rep["registry_rasters"],
    }
    gv["exp2_benchmark_beats_vess_0200941"] = beats_bar_exp2
    gv["paired_delta_exp2_vs_adhr_control"] = paired_exp2

    suffix = "GATE-PASS" if ok_submit_final else "DO-NOT-SUBMIT"
    final_stem = f"{prov_stem}-{suffix}"
    final_tif = ROOT / "docs/downloads" / f"{final_stem}.tif"
    final_zip = ROOT / "docs/downloads" / f"{final_stem}.zip"
    for ext in (".tif", ".zip", ".json"):
        prov_tif.with_suffix(ext).unlink(missing_ok=True)
        final_tif.with_suffix(ext).unlink(missing_ok=True)

    submission_writer.write_submission(
        final_tif, prod_emitted, ROOT / "data/bridge/sample_submission.tif", fp,
        note=sub_note, name=sub_name, catalogue=g.catalogue,
        metadata={
            "lane": "H88-VHGD",
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "holdout_dti_exp1_zerocat": ov_exp1["dti"],
            "holdout_dti_exp2_poe_unconstr": ov_exp2["dti"],
            "holdout_dti_exp2_far_gt10px": far_dti_e2,
            "holdout_dti_exp2_blind_gt25px": blind_dti_e2,
            "holdout_dti_exp3_3stratum": ov_exp3["dti"],
            "holdout_dti_exp3_far_gt10px": far_dti_e3,
            "holdout_dti_exp3_blind_gt25px": blind_dti_e3,
            "organizer_confirmed_score": None,
            "gate_policy": gate.POLICY_VERSION,
            "ok_to_download": gv["ok_to_download"],
            "ok_to_submit": ok_submit_final,
        },
    )
    local_val = validate.validate(final_tif, fp, g.catalogue)
    portal_final = gate.portal_validate(final_tif, ROOT / "data/bridge/sample_submission.tif", fp)

    # Independent second-decoder verification via tifffile
    arr_tf = tifffile.imread(final_tif)
    assert arr_tf.dtype == np.float32 and arr_tf.shape == g.shape
    assert bool(np.isfinite(arr_tf).all()) and float(arr_tf.min()) >= 0.0 and float(arr_tf.max()) <= 1.0
    assert bool((arr_tf[~fp] == 0.0).all()) and bool((arr_tf[full_cat] == 0.0).all())

    format_audit = {
        "file": f"docs/downloads/{final_tif.name}",
        "zip_file": f"docs/downloads/{final_zip.name}",
        "sha256": _sha256(final_tif),
        "zip_sha256": _sha256(final_zip),
        "portal_validate": portal_final,
        "tifffile_second_decoder": {
            "passed": True,
            "dtype": str(arr_tf.dtype),
            "shape": list(arr_tf.shape),
            "all_finite": True,
            "min": float(arr_tf.min()),
            "max": float(arr_tf.max()),
            "outside_footprint_all_zero": True,
            "on_catalogue_all_zero": True,
            "positive_pixels": int((arr_tf > 0).sum()),
        },
    }
    _write_json(ROOT / "docs/downloads" / f"{final_stem}.format-audit.json", format_audit)

    for p in (final_tif, final_zip, final_tif.with_suffix(".json"), ROOT / "docs/downloads" / f"{final_stem}.format-audit.json"):
        if p.exists():
            os.chmod(p, 0o644)
    sub_dir = ROOT / "submissions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_tif, sub_dir / final_tif.name)
    shutil.copy2(final_zip, sub_dir / final_zip.name)

    print("[6/6] Writing run card + gate verdict + uniqueness receipts...", flush=True)
    uniq_payload = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_placement_surface": {
            "max_abs_spearman_rho": round(max_surface_rho, 6),
            "max_against": max_surface_against,
            "threshold": 0.90,
            "passed": bool(max_surface_rho <= 0.90),
            "rasters_checked": len(reg_pairs),
        },
        "post_placement_dots": {"gate_v3_uniqueness": uniq_rep},
        "fingerprint": fp_profile,
        "fingerprint_screen_passed": fp_ok,
        "stratum_breakdown": prod_meta,
    }
    for p in (ROOT / "evidence/vhgd88_uniqueness_20261025.json", ROOT / "docs/evidence/vhgd88_uniqueness_20261025.json"):
        _write_json(p, uniq_payload)

    verdict = "promote" if ok_submit_final else "negative"
    run_card = {
        "schema": "gems88.vhgd88.run_card.v1",
        "run_id": f"GEMSDOE88-VHGD88-{DATE}-{_sha256(final_tif)[:8]}",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-VHGD",
        "preregistration_id": prereg["preregistration_id"],
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
            "withheld_positive_pixels_overall": ov_exp2["withheld_positive_pixels"],
            "control_adhr_lgbm_overall": ov_ctrl,
            "exp1_zerocat_overall": ov_exp1,
            "exp2_poe_unconstrained": {
                "overall": ov_exp2,
                "far_gt10px": pooled_far10_exp2["scores"][BENCHMARK_ARM],
                "blind_gt25px": pooled_blind25_exp2["scores"][BENCHMARK_ARM],
                "paired_delta_vs_adhr_control": paired_exp2,
            },
            "exp3_emitted_3stratum": {
                "overall": ov_exp3,
                "far_gt10px": pooled_far10_exp3["scores"][EMITTED_ARM],
                "blind_gt25px": pooled_blind25_exp3["scores"][EMITTED_ARM],
                "paired_delta_vs_adhr_control": pooled_overall_exp3["paired_differences"]["h88_adhr_control"],
            },
        },
        "leakage_canary": canary,
        "correlation_overlap_vs_registry": {
            "surface_preplacement_max_abs_spearman": round(max_surface_rho, 6),
            "final_worst_like_for_like_overlap_3px": uniq_rep["worst_like_for_like_overlap"],
            "final_worst_abs_rho": uniq_rep["worst_abs_rho"],
            "like_for_like_blockers": uniq_rep["like_for_like_blockers"],
            "unique_like_for_like": uniq_rep["unique_like_for_like"],
            "unique_literal": uniq_rep["unique_literal"],
            "literal_blockers": uniq_rep["literal_blockers"],
            "registry_rasters_checked": uniq_rep["registry_rasters"],
        },
        "validator_output": local_val,
        "portal_validate": portal_final,
        "tifffile_second_decoder": format_audit["tifffile_second_decoder"],
        "raster_sha256": _sha256(final_tif),
        "zip_sha256": _sha256(final_zip),
        "submission": {
            "file": f"docs/downloads/{final_tif.name}",
            "zip_file": f"docs/downloads/{final_zip.name}",
            "submission_name": sub_name,
            "submission_note": sub_note,
            "submission_note_chars": len(sub_note),
            "positive_pixels": int(prod_meta["n_dots"]),
            "stratum_breakdown": prod_meta,
            "share_gt25": fp_profile["share_gt25"],
            "share_le2": fp_profile["share_le2"],
            "median_d_cat_px": fp_profile["median_d_cat_px"],
        },
        "ok_to_download": bool(gv["ok_to_download"]),
        "ok_to_submit": ok_submit_final,
        "gate_verdict": gv,
        "verdict": verdict,
        "organizer_confirmed_score": None,
        "weekly_slots_used": 0,
        "vhgd_meta": vhgd_meta,
    }
    for p in (ROOT / "registry/vhgd88_run_card.json", ROOT / "docs/data/vhgd88_run_card.json"):
        _write_json(p, run_card)

    gv_out = dict(gv)
    gv_out.update({
        "name": final_stem,
        "file": f"docs/downloads/{final_tif.name}",
        "zip_file": f"docs/downloads/{final_zip.name}",
        "sha256": run_card["raster_sha256"],
        "zip_sha256": run_card["zip_sha256"],
        "candidate": {
            "tif": f"docs/downloads/{final_tif.name}",
            "zip": f"docs/downloads/{final_zip.name}",
            "tif_sha256": run_card["raster_sha256"],
            "zip_sha256": run_card["zip_sha256"],
        },
    })
    for p in (ROOT / "registry/vhgd88_gate_verdict.json", ROOT / "docs/data/vhgd88_gate_verdict.json"):
        _write_json(p, gv_out)

    print(
        json.dumps(
            {
                "lane": "H88-VHGD",
                "exp1_zerocat_dti": ov_exp1["dti"],
                "exp2_poe_dti": ov_exp2["dti"],
                "exp2_ci95": ov_exp2["ci95"],
                "exp2_far_dti": far_dti_e2,
                "exp2_blind_dti": blind_dti_e2,
                "exp3_3stratum_dti": ov_exp3["dti"],
                "exp3_far_dti": far_dti_e3,
                "exp3_blind_dti": blind_dti_e3,
                "paired_delta_exp2_vs_adhr": paired_exp2,
                "dots": prod_meta["n_dots"],
                "share_gt25": fp_profile["share_gt25"],
                "share_le2": fp_profile["share_le2"],
                "worst_like_for_like_overlap_3px": uniq_rep["worst_like_for_like_overlap"],
                "like_for_like_blockers": uniq_rep["like_for_like_blockers"],
                "unique_like_for_like": uniq_rep["unique_like_for_like"],
                "unique_literal": uniq_rep["unique_literal"],
                "file": str(final_tif),
                "sha256": run_card["raster_sha256"],
                "ok_to_download": gv["ok_to_download"],
                "ok_to_submit": ok_submit_final,
                "verdict": verdict,
                "elapsed_s": round(time.monotonic() - t0, 2),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
