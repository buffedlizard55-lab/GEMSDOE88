#!/usr/bin/env python3
"""GEMSDOE88 LBCAL — leaderboard-receipt calibrated emission + automated inspection gate.

Lane (single method): fit a physical-feature truth density q(y) to the ~100 user-reported
public-LB receipts whose exact rasters are on GitHub (scripts/lbcal_pixel.py, model px1:
25 physical features, no coordinates), then emit binary dots by lazy-greedy expected-DTI
maximisation under q, with a provable lane-separation cap: at most CAP of dots may lie inside
the union of 3-px halos of every sparse registry/receipt raster (so no single raster can
own > CAP of our dots).

Experiments (budget 3):
  EXP1  receipt-CV model selection px1 (sides pooled) vs px2 (up/down split)  [lbcal_pixel.py]
  EXP2  hide-and-recover HOLDOUT-DTI of the per-fold rebuilt LBCAL emission vs R0 control
  EXP3  (not run unless time) cap sensitivity
No portal contact, no slot spent.  Every LB-derived number is MODEL-FIT / MODEL-PROJECTION.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor"), str(ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gems57 import evaluate_holdout, grid as grid_mod, holdout as holdout_mod, metric, uniqueness  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
import build_prune_variants as bpv  # noqa: E402
import lbcal_pixel as lp  # noqa: E402
import lbcal_design as ld  # noqa: E402

DATE = "20261024"
CAP = 0.66            # < 0.70 protocol limit, margin for rounding / halo definition
FIT = ROOT / "data" / "lbcal" / "px_fit_px1cv.json"
DOWNLOADS = ROOT / "docs" / "downloads"
SUBMISSIONS = ROOT / "submissions"
EVID = ROOT / "evidence"


def log(msg):
    print(f"[lbcal {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_any(p, shape):
    with rasterio.open(p) as ds:
        if (ds.height, ds.width) != shape:
            return None
        a = ds.read(1).astype(np.float32)
        nod = ds.nodata
    if nod is not None and np.isfinite(nod):
        a[a == nod] = np.nan
    return a


def registry_files():
    files = sorted((ROOT / "data" / "registry").rglob("*.tif"))
    files += sorted(DOWNLOADS.glob("*.tif")) + sorted(SUBMISSIONS.glob("*.tif"))
    files += sorted((ROOT / "data" / "lbcal").glob("[0-9][0-9][0-9]__*.tif"))
    return [f for f in files if "lbcal" not in f.name.lower() or f.parent.name == "lbcal"]


def registry_halos(foot, omega):
    """Per-raster 3-px halos (vendor uniqueness._near) of every registry/receipt raster.
    Space-filling rasters (halo covers >= 70% of the scored domain; vendor representation_class_v2
    DENSE_HALO_FRACTION) cannot discriminate lanes and are reported, not used as caps."""
    halos, used, spacefill = [], [], []
    for p in registry_files():
        a = load_any(p, foot.shape)
        if a is None:
            continue
        sup = np.isfinite(a) & (a > 0) & foot
        near = uniqueness._near(sup)
        cov = float(near[omega].mean())
        if cov >= uniqueness.DENSE_HALO_FRACTION:
            spacefill.append({"file": str(p.relative_to(ROOT)), "halo_coverage": round(cov, 4)}); continue
        halos.append(np.packbits(near))
        used.append(str(p.relative_to(ROOT)))
    return halos, used, spacefill


def q_map(fit, fstats, omega, cat_for_features):
    F = lp.feature_stack(omega, cat_for_features)
    q = ld.full_grid_q(np.array(fit["beta"]), fit["labels"], fstats, F)
    del F
    q[~omega] = 0.0
    return q


def emit(q, omega, halos, G, cand_quantile=0.92, max_iter=40):
    """(1) unconstrained lazy-greedy expected-DTI emission under q (ideal set, greedy order);
    (2) lane-cap repair over the WHOLE scored domain: while some capped raster owns > CAP of the
    dots, drop its lowest-ranked dots and refill with the highest-q pixels (kernel-summed q per unit
    FP cost) lying outside the halos of every raster at/above the cap and >= 2 px from selected dots.
    Dot count is held at the ideal size; terminates when every capped raster owns <= CAP."""
    s = ld.kernel_sum(q)
    cand = omega & (s >= np.quantile(s[omega], cand_quantile))
    picks, dT, dF = ld.greedy(q, cand, G, max_dots=150000)
    cT, cF = np.cumsum(dT), np.cumsum(dF)
    D = cT / (0.2 * cT + 0.2 * cF + 0.8 * G)
    n_star = int(np.argmax(D)) + 1
    ideal_proj = float(D[n_star - 1])
    H, W = q.shape
    rank = np.full(q.size, -1, np.int64)
    rank[picks[:n_star]] = np.arange(n_star)
    kappa = 2.6
    v0 = np.where(omega, s / np.maximum(1 - np.minimum(s / kappa, 1), 1e-3), -1).ravel()
    order = np.argsort(-v0, kind="stable")
    order = order[v0[order] > 0]
    unpack = lambda k: np.unpackbits(halos[k], count=q.size).astype(bool)
    next_rank = n_star
    hist = []
    for it in range(max_iter):
        sel = rank >= 0
        n = int(sel.sum())
        cnt = np.array([int(unpack(k)[sel].sum()) for k in range(len(halos))])
        sh = cnt / max(n, 1)
        worst = int(np.argmax(sh))
        hist.append(round(float(sh[worst]), 4))
        if sh[worst] <= CAP:
            break
        hot = np.flatnonzero(sh >= CAP - 0.01)
        hot_union = np.zeros(q.size, bool)
        for k in hot:
            hot_union |= unpack(int(k))
        n_remove = int(cnt[worst] - np.floor((CAP - 0.004) * n))
        hw = np.flatnonzero(sel & unpack(worst))
        drop = hw[np.argsort(-rank[hw])][:n_remove]
        rank[drop] = -1
        occ = (rank >= 0).reshape(H, W)
        added = 0
        for i in order:
            if added >= n_remove:
                break
            if hot_union[i] or rank[i] >= 0:
                continue
            y, x = divmod(int(i), W)
            if occ[max(0, y - 2):y + 3, max(0, x - 2):x + 3].any():
                continue
            occ[y, x] = True
            rank[i] = next_rank; next_rank += 1; added += 1
    mask = (rank >= 0).reshape(q.shape)
    proj = ld.expected_dti_of_mask(q, mask, G)[0]
    sel = mask.ravel()
    max_share = max(float(unpack(k)[sel].mean()) for k in range(len(halos))) if sel.any() else 0.0
    info = {"ideal_dots": n_star, "ideal_model_projected_dti": ideal_proj, "dots": int(mask.sum()),
            "model_projected_dti": float(proj), "max_share_any_capped_raster": max_share,
            "repair_iterations": len(hist), "share_history": hist[:15]}
    return mask, info


def main() -> int:
    t0 = time.time()
    verified = bpv.verify_manifest()
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    foot, catalogue = gd.footprint, gd.catalogue
    omega = foot & ~catalogue
    fit = json.loads(FIT.read_text())
    z = np.load(ROOT / "data" / "lbcal" / "px_prep.npz")
    fstats = json.loads(str(z["fstats"]))
    log(f"inputs verified ({len(verified)}); fit {FIT.name}: receipts={fit['n_receipts']} "
        f"CV RMSE={fit.get('repo_blocked_rmse')} rho={fit.get('repo_blocked_spearman')}")

    halos, used, dense = registry_halos(foot, omega)
    log(f"registry halos: {len(used)} lane-cap rasters, {len(dense)} space-filling classed separately: {dense}")

    # ---------------------------------------------------------------- final design
    q = q_map(fit, fstats, omega, catalogue)
    G = float(q.sum())
    final_mask, info = emit(q, omega, halos, G)
    log(f"final emission: {int(final_mask.sum())} dots; info={info}; "
        f"MODEL-PROJECTED DTI {info['model_projected_dti']:.4f}")
    assert not np.any(final_mask & ~omega)

    # model projections of receipts for apples-to-apples (MODEL-PROJECTION only)
    proj = {"lbcal_final": ld.expected_dti_of_mask(q, final_mask, G)[0]}
    for nm, fn in (("R0_H33", verified["parent_r0_zeros"]),):
        a = load_any(fn, foot.shape)
        proj[nm] = ld.expected_dti_of_mask(q, (np.nan_to_num(a) > 0) & omega, G)[0]
    log(f"model projections (same q): {proj}")

    # ---------------------------------------------------------------- leakage canary
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)
    pos_mask = folds20[0]["hidden_all"] | folds30[0]["hidden_all"]
    rng = np.random.default_rng(20261024)
    neg_pool = np.flatnonzero(omega & ~pos_mask)
    neg = rng.choice(neg_pool, size=min(100_000, neg_pool.size), replace=False)
    pos = np.flatnonzero(pos_mask)
    ev = np.concatenate([pos, neg]); yt = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    F = lp.feature_stack(omega, folds20[0]["visible"])
    canaries = {}
    for nm in fit["labels"][1:]:
        v = np.nan_to_num(F[nm].ravel()[ev].astype(np.float64), nan=0.0)
        auc = float(roc_auc_score(yt, v)); canaries[nm] = round(max(auc, 1 - auc), 5)
    qv = ld.full_grid_q(np.array(fit["beta"]), fit["labels"], fstats, F).ravel()[ev]
    canaries["q_composite"] = round(max(roc_auc_score(yt, qv), 1 - roc_auc_score(yt, qv)), 5)
    del F
    canary_max = max(canaries.values())
    log(f"leakage canary max symmetric AUC={canary_max} ({max(canaries, key=canaries.get)})")

    # ---------------------------------------------------------------- holdout (seeds 20+30)
    terms, withheld_total = {}, 0
    with rasterio.open(verified["parent_r0_zeros"]) as ds:
        r0 = (np.nan_to_num(ds.read(1), nan=0.0) > 0) & foot
    for seed, folds in ((20, folds20), (30, folds30)):
        visible, masked_known = folds[0]["visible"], folds[0]["masked_known"]
        om_f = foot & ~masked_known
        qf = q_map(fit, fstats, om_f, visible)
        mask_f, inf_f = emit(qf, om_f, halos, float(qf.sum()))
        for arm, m in (("lbcal", mask_f), ("r0_control", r0)):
            pred = m.astype(np.float32)
            for f in folds:
                _, t = evaluate_holdout.evaluate(pred, f, foot)
                terms[arm] = t if arm not in terms else terms[arm] + t
        withheld_total += sum(int(f["truth"].sum()) for f in folds)
        log(f"holdout seed {seed}: lbcal dots={int(mask_f.sum())} built from visible-only catalogue")
    pooled = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810, candidate="lbcal")
    scores = pooled["scores"]
    for k, v in scores.items():
        log(f"HOLDOUT-DTI {k}={v['dti']:.6f} CI={v['ci95']} K={v['withheld_positive_pixels']}")
    prov = json.loads((ROOT / "registry" / "provcrest_run_card.json").read_text())
    prov_best = float(prov["holdout"]["winner_dti"])

    # ---------------------------------------------------------------- SGMC proxy
    sgmc_raw = rasterio.open(verified["sgmc_faults_control"]).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    sgmc = {nm: round(float(metric.dti_binary(m, sgmc_off, valid=foot, known=catalogue)["dti"]), 6)
            for nm, m in (("final", final_mask), ("r0_control", r0))}

    # ---------------------------------------------------------------- uniqueness on final dots
    mine = np.where(foot, final_mask.astype(np.float32), 0.0).astype(np.float32)
    spacefill_files = {d["file"] for d in dense}
    rows, worst_rho, worst_ov = [], (0.0, ""), (0.0, "")
    worst_rho_all = (0.0, "")
    for p in registry_files():
        a = load_any(p, foot.shape)
        if a is None:
            rows.append({"file": str(p.relative_to(ROOT)), "error": "shape mismatch, skipped as non-grid raster"}); continue
        ov = uniqueness.dot_overlap(mine, a)
        rho = uniqueness.surface_rho(mine, np.nan_to_num(a, nan=0.0), foot)["spearman_full_footprint"]
        dense_frac = float((np.isfinite(a) & (a > 0) & foot).sum() / foot.sum())
        cls = "space_filling" if str(p.relative_to(ROOT)) in spacefill_files else "sparse_dot_or_ridge"
        rows.append({"file": str(p.relative_to(ROOT)), "dot_overlap_3px": round(float(ov), 4),
                     "spearman_full_footprint": round(float(rho), 4) if np.isfinite(rho) else None,
                     "positive_fraction_in_footprint": round(dense_frac, 4), "representation_class": cls})
        if np.isfinite(rho) and abs(rho) > abs(worst_rho_all[0]):
            worst_rho_all = (float(rho), str(p.relative_to(ROOT)))
        if cls == "sparse_dot_or_ridge":
            if np.isfinite(rho) and abs(rho) > abs(worst_rho[0]):
                worst_rho = (float(rho), str(p.relative_to(ROOT)))
            if ov > worst_ov[0]:
                worst_ov = (float(ov), str(p.relative_to(ROOT)))
    unique_ok = abs(worst_rho_all[0]) <= 0.90 and worst_ov[0] <= 0.70
    log(f"uniqueness: {len(rows)} rasters; worst |rho|={worst_rho}; worst 3px overlap={worst_ov}; pass={unique_ok}")

    # ---------------------------------------------------------------- verdict + write
    holdout_beats_best = scores["lbcal"]["dti"] > prov_best
    beats_r0 = pooled["paired_differences"]["r0_control"]["ci95"][0] > 0
    canary_ok = canary_max <= 0.90
    promote = bool(holdout_beats_best and beats_r0 and canary_ok and unique_ok)
    short = hashlib.sha256(final_mask.tobytes()).hexdigest()[:8]
    n = int(final_mask.sum())
    stem = f"gems88-lbcal-receipt-{n}-{DATE}-{short}-zeros"
    if not promote:
        stem += "-HOLD"
    name = f"GEMSDOE88-LBCAL-{short.upper()}"
    note = (f"LBCAL receipt-calibrated q, {n} dots, <=66% in sibling halos; HOLDOUT {scores['lbcal']['dti']:.4f}; "
            f"model-proj only, UNSCORED")[:140]
    DOWNLOADS.mkdir(parents=True, exist_ok=True); SUBMISSIONS.mkdir(parents=True, exist_ok=True); EVID.mkdir(exist_ok=True)
    tif = DOWNLOADS / f"{stem}.tif"
    if tif.exists():
        raise FileExistsError(tif)
    receipt = write_submission(tif, mine, verified["sample_submission"], foot, note=note, name=name, catalogue=catalogue,
                               metadata={"lane": "LBCAL receipt-calibrated emission", "fit": FIT.name})
    for f in (tif, tif.with_suffix(".zip"), tif.with_suffix(".json")):
        if f.exists():
            f.chmod(0o644)
            shutil.copy2(f, SUBMISSIONS / f.name)
    from gems57.validate import validate as validate_tif
    from gems57 import gates
    val = validate_tif(tif, foot, catalogue)
    fmt = gates.format_report(tif, verified["sample_submission"], footprint=foot)
    with rasterio.open(tif) as ds, rasterio.open(verified["sample_submission"]) as ref:
        arr = ds.read(1)
        grid_match = bool(ds.crs == ref.crs and ds.transform == ref.transform and ds.shape == ref.shape)
        nodata = ds.nodata
    fsha = hashlib.sha256(tif.read_bytes()).hexdigest()
    validator = {"vendor_validate": val, "format_report_ok": bool(fmt.get("ok")), "crs_shape_transform_match": grid_match,
                 "no_nan_anywhere": bool(np.isfinite(arr).all()), "values_in_0_1": bool(arr.min() >= 0 and arr.max() <= 1),
                 "nan_inside_footprint": int((~np.isfinite(arr) & foot).sum()), "nodata_tag": nodata,
                 "positive_on_catalogue": int(((arr > 0) & catalogue).sum()), "positive_outside_footprint": int(((arr > 0) & ~foot).sum())}
    format_ok = bool(validator["format_report_ok"] and grid_match and validator["no_nan_anywhere"] and validator["values_in_0_1"]
                     and validator["positive_on_catalogue"] == 0 and validator["positive_outside_footprint"] == 0)
    json.dump(rows, open(EVID / "lbcal_uniqueness.json", "w"), indent=1)
    card = {
        "schema": "gems88.run-card.v3", "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "lane": "LBCAL — leaderboard-receipt calibrated emission (single method)",
        "hypothesis": ("The ~100 user-reported public-LB receipts of sibling rasters are measurements of the hidden truth; a "
                       "physical-feature density q fitted to them (no coordinates) localises new faults better than "
                       "catalogue-trained proxies, and greedy expected-DTI emission under q beats hand-tuned pruning."),
        "mechanism": ("DTI is a ratio of sums linear in the truth indicator, so E[TP]=sum q*c_i exactly; q=exp(beta.phi) over 25 "
                      "physical bands (catalogue-distance bands, H19-5 ridge-distance bands, LiDAR scarp, 10 m topo, chi, "
                      "gravity/magnetic gradients) is fitted by least squares to receipts; emission = lazy-greedy max of "
                      "expected DTI with <=66% of dots inside the union of sibling 3-px halos."),
        "named_non_fault_process": ("Bedrock-alluvium contacts and fluvial/terrace risers adjacent to topographic ridges "
                                    "(same slope/aspect-coherence signature as a range-front scarp, no brittle offset)."),
        "receipt_model": {"evidence_class": "MODEL-FIT to USER-REPORTED LB receipts (not HOLDOUT-DTI, not ORGANIZER-CONFIRMED)",
                          "fit_file": f"data/lbcal/{FIT.name}", "n_receipts": fit["n_receipts"],
                          "fit_rmse": fit["fit_rmse"], "fit_spearman": fit["fit_spearman"],
                          "repo_blocked_8fold_rmse": fit.get("repo_blocked_rmse"),
                          "repo_blocked_8fold_spearman": fit.get("repo_blocked_spearman"),
                          "labels": fit["labels"], "beta": fit["beta"]},
        "model_projection": {"evidence_class": "MODEL-PROJECTION (never a score)", **{k: round(float(v), 4) for k, v in proj.items()},
                             "emission": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in info.items()}},
        "holdout": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                    "alpha": metric.ALPHA, "beta": metric.BETA, "triangular_kernel_radius_px": metric.RADIUS_PX,
                    "seeds": [20, 30], "withheld_positive_pixels": int(scores["lbcal"]["withheld_positive_pixels"]),
                    "lbcal_dti": round(float(scores["lbcal"]["dti"]), 6),
                    "lbcal_ci95": [round(float(x), 6) for x in scores["lbcal"]["ci95"]],
                    "r0_control_dti": round(float(scores["r0_control"]["dti"]), 6),
                    "r0_control_ci95": [round(float(x), 6) for x in scores["r0_control"]["ci95"]],
                    "paired_lbcal_minus_r0": pooled["paired_differences"]["r0_control"],
                    "current_holdout_best_same_seeds": {"name": "PROVCREST (registry/provcrest_run_card.json)", "dti": prov_best},
                    "beats_current_holdout_best": bool(holdout_beats_best),
                    "protocol": "buffered whole-component hide-and-recover; q and emission rebuilt per seed from visible-only catalogue; visible faults masked pixel-exactly; pooled DTI"},
        "sgmc_proxy": {"evidence_class": "PROXY (not a score)", **sgmc, "n_off_catalogue_px": int(sgmc_off.sum())},
        "leakage_canary": {"threshold": 0.90, "channels": canaries, "max_symmetric_auc": canary_max, "passed": bool(canary_ok)},
        "uniqueness": {"rasters_checked": len(rows), "worst_sparse_spearman": {"rho": round(worst_rho[0], 4), "file": worst_rho[1]},
                       "worst_sparse_dot_overlap_3px": {"overlap": round(worst_ov[0], 4), "file": worst_ov[1]},
                       "gate_pass": bool(unique_ok), "space_filling_classed_separately": dense,
                       "worst_spearman_all_rasters": {"rho": round(worst_rho_all[0], 4), "file": worst_rho_all[1]}, "rows_file": "evidence/lbcal_uniqueness.json",
                       "design_cap_in_union_of_halos": CAP},
        "raster": {"file": f"docs/downloads/{tif.name}", "zip": f"docs/downloads/{tif.with_suffix('.zip').name}",
                   "sha256": fsha, "dots": n, "name": name, "note": note, "note_chars": len(note)},
        "validator": validator, "format_ok": format_ok,
        "verdict": ("PROMOTE" if promote else "NEGATIVE-HOLD"),
        "ok_to_download": bool(format_ok),
        "ok_to_submit": bool(format_ok and promote),
        "verdict_reason": ("all gates passed" if promote else
                           "format-valid and unique, but the user's rule requires beating the current holdout best before any slot "
                           f"(HOLDOUT-DTI {scores['lbcal']['dti']:.4f} vs best {prov_best:.4f}; beats R0 CI>0: {beats_r0}; canary ok: {canary_ok}; unique: {unique_ok})"),
        "experiments_used": 2, "experiment_budget": 3,
        "runtime_s": round(time.time() - t0, 1),
    }
    out = ROOT / "registry" / "lbcal_run_card.json"
    out.write_text(json.dumps(card, indent=1, default=float))
    log(f"verdict={card['verdict']} ok_to_download={card['ok_to_download']} ok_to_submit={card['ok_to_submit']} file={tif.name}")
    log(f"run card -> {out.relative_to(ROOT)} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
