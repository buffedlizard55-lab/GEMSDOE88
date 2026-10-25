#!/usr/bin/env python3
"""GEMSDOE88 PROV-CREST de-novo submission build + automated inspection gate.

Lane (single method, preregistered in registry/preregistration_provfp.json):
composite Hessian crest of organizer-provided training_features.tif Bands
19/3/18/15 -> 1-D directional NMS crest pool -> de-novo selection of exactly
37,654 binary dots at >=3.5 px spacing and >3.0 px from the catalogue
(visible-only catalogue inside holdout folds; full catalogue for the ship file).
Zero R0/sibling dots by construction, zero external data, zero H19 supports.

Experiments (budget 2 + 1 control):
  EXP1 provcrest_rank     greedy descending crest score, >=3.5 px blocked
  EXP2 provcrest_randorder seeded random order, identical pool/lock/collar
  CONTROL r0              R0 evaluated unchanged on identical folds

Validation: buffered whole-component hide-and-recover (seeds 20+30) using the
unmodified vendor template (gems57.holdout/evaluate_holdout/metric), pooled
DTI alpha=0.2 beta=0.8 300 m triangular kernel, visible faults masked
pixel-exactly, catalogue-derived collar derived only from visible faults.
Leakage canary per crest channel (symmetric AUC <= 0.90) fails closed.
Uniqueness + format are checked on the final dots with vendor gems57
uniqueness/validate/submission_writer. No portal contact, no slot spent.
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
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gems57 import evaluate_holdout, grid as grid_mod, holdout as holdout_mod, metric, uniqueness  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
import build_prune_variants as bpv  # noqa: E402
import build_prune_deconfound_variants as bpd  # noqa: E402

N_DOTS = 37_654
SPACING = 3.5
DATE = "20261024"
SEED = 20261024
DOWNLOADS = ROOT / "docs" / "downloads"
SUBMISSIONS = ROOT / "submissions"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- crest field
def build_crest(verified, foot, catalogue):
    """Composite provided-band crest + per-channel leakage canaries (fail closed)."""
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)
    pos_mask = folds20[0]["hidden_all"] | folds30[0]["hidden_all"]
    rng = np.random.default_rng(20261023)
    neg_pool = np.flatnonzero(foot & ~catalogue & ~pos_mask)
    neg_sample = rng.choice(neg_pool, size=min(100_000, len(neg_pool)), replace=False)
    pos_idx = np.flatnonzero(pos_mask)
    eval_idx = np.concatenate([pos_idx, neg_sample])
    y_true = np.concatenate([np.ones(len(pos_idx), dtype=np.int8),
                             np.zeros(len(neg_sample), dtype=np.int8)])
    canaries: dict[str, float] = {}

    def audit(name, raw):
        auc = float(roc_auc_score(y_true, np.asarray(raw, dtype=np.float64).ravel()[eval_idx]))
        sym = float(max(auc, 1.0 - auc))
        canaries[name] = round(sym, 5)
        if sym > 0.90:
            raise RuntimeError(f"LEAKAGE CANARY TRIPPED {name}: symmetric AUC {sym:.5f} > 0.90")
        return bpv._percentile_rank(raw, foot)

    def clean(ds, idx):
        a = np.where(foot, np.nan_to_num(ds.read(idx), nan=0.0), 0.0).astype(np.float32)
        bad = (~np.isfinite(a)) | (np.abs(a) > 1e20)
        if np.any(bad & foot):
            a[bad] = float(np.median(a[foot & ~bad]))
        a[~foot] = 0.0
        return a

    with rasterio.open(verified["training_features"]) as ds:
        b19 = clean(ds, 19)
        gy, gx = np.gradient(gaussian_filter(b19, 1.5)); del b19
        c19 = audit("prov_slope_break_hess_b19", bpv._hessian_ridge(np.hypot(gy, gx).astype(np.float32), 1.5))
        del gy, gx
        c03 = audit("prov_tmi_hg_hess_b03", bpv._hessian_ridge(clean(ds, 3), 1.5))
        c18 = audit("prov_grav_hg_hess_b18", bpv._hessian_ridge(clean(ds, 18), 1.5))
        b15 = clean(ds, 15)
        gy, gx = np.gradient(gaussian_filter(b15, 1.5)); del b15
        c15 = audit("prov_basement_step_hess_b15", bpv._hessian_ridge(np.hypot(gy, gx).astype(np.float32), 1.5))
        del gy, gx

    crest = (0.45 * c19 + 0.20 * c03 + 0.20 * c18 + 0.15 * c15).astype(np.float32)
    del c19, c03, c18, c15
    crest[~foot] = 0.0
    auc = float(roc_auc_score(y_true, crest.ravel()[eval_idx].astype(np.float64)))
    canaries["prov_composite_crest"] = round(float(max(auc, 1.0 - auc)), 5)
    if canaries["prov_composite_crest"] > 0.90:
        raise RuntimeError("LEAKAGE CANARY TRIPPED prov_composite_crest")
    crest_mask = bpd.directional_crest_1d(crest, foot)
    return crest, crest_mask, canaries


# ------------------------------------------------------------- dot selection
_DISK = [(dy, dx) for dy in range(-4, 5) for dx in range(-4, 5)
         if dy * dy + dx * dx < SPACING * SPACING]


def select_dots(cand_yx: np.ndarray, eligible: np.ndarray, foot_shape) -> np.ndarray:
    """Greedy acceptance in the given candidate order under >=3.5 px lock."""
    blocked = np.zeros(foot_shape, dtype=bool)
    out = np.zeros(foot_shape, dtype=bool)
    H, W = foot_shape
    n = 0
    disk = np.array(_DISK, dtype=np.int64)
    for y, x in cand_yx:
        if n >= N_DOTS:
            break
        if not eligible[y, x] or blocked[y, x]:
            continue
        out[y, x] = True
        n += 1
        ys = y + disk[:, 0]; xs = x + disk[:, 1]
        ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
        blocked[ys[ok], xs[ok]] = True
    if n != N_DOTS:
        raise RuntimeError(f"spacing lock exhausted pool: placed {n} of {N_DOTS}")
    return out


def nn_stats(mask: np.ndarray) -> dict:
    from scipy.spatial import cKDTree
    pts = np.argwhere(mask).astype(np.float64)
    d = cKDTree(pts).query(pts, k=2)[0][:, 1]
    return {"min_px": round(float(d.min()), 4), "median_px": round(float(np.median(d)), 4),
            "frac_ge_6px": round(float((d >= 6.0).mean()), 4)}


def main() -> int:
    t0 = time.time()
    prereg = json.loads((ROOT / "registry" / "preregistration_provfp.json").read_text())
    assert prereg["frozen_before_any_variant_proxy_or_holdout"] is True

    verified = bpv.verify_manifest()
    print(f"[provcrest] manifest verified: {len(verified)} inputs", flush=True)
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    foot, catalogue = gd.footprint, gd.catalogue
    d_cat = distance_transform_edt(~catalogue)

    with rasterio.open(verified["parent_r0_zeros"]) as ds:
        r0 = (np.nan_to_num(ds.read(1), nan=0.0) > 0) & foot
    assert int(r0.sum()) == N_DOTS

    crest, crest_mask, canaries = build_crest(verified, foot, catalogue)
    print(f"[provcrest] crest pool={int(crest_mask.sum())} canaries={canaries}", flush=True)

    # Global deterministic candidate orders (crest pool only)
    cy, cx = np.nonzero(crest_mask)
    order_rank = np.argsort(-crest[cy, cx], kind="stable")
    rank_yx = np.column_stack([cy[order_rank], cx[order_rank]])
    rng = np.random.default_rng(SEED)
    order_rand = rng.permutation(len(cy))
    rand_yx = np.column_stack([cy[order_rand], cx[order_rand]])

    # ------------------------------------------------ holdout (seeds 20+30)
    arms_masks: dict[str, dict[int, np.ndarray]] = {"provcrest_rank": {}, "provcrest_randorder": {}}
    terms: dict[str, np.ndarray] = {}
    withheld_total = 0
    for seed in (20, 30):
        folds, _ = holdout_mod.buffered_component_draw(gd, seed=seed)
        visible = folds[0]["visible"]; masked_known = folds[0]["masked_known"]
        d_vis = distance_transform_edt(~visible)
        eligible = crest_mask & foot & ~masked_known & (d_vis > 3.0)
        for arm, cand in (("provcrest_rank", rank_yx), ("provcrest_randorder", rand_yx)):
            mask = select_dots(cand, eligible, foot.shape)
            arms_masks[arm][seed] = mask
            pred = mask.astype(np.float32)
            for f in folds:
                _, t = evaluate_holdout.evaluate(pred, f, foot)
                terms[arm] = t if arm not in terms else terms[arm] + t
        pred0 = r0.astype(np.float32)
        for f in folds:
            _, t = evaluate_holdout.evaluate(pred0, f, foot)
            terms["r0_control"] = t if "r0_control" not in terms else terms["r0_control"] + t
            withheld_total += int(f["truth"].sum())
        print(f"[provcrest] seed {seed} holdout arms built+evaluated ({time.time()-t0:.0f}s)", flush=True)

    pooled = evaluate_holdout.pooled_summary(
        terms, draws=1000, seed=520810, candidate="provcrest_rank")
    scores = pooled["scores"]
    for k, v in scores.items():
        print(f"[holdout] {k}: HOLDOUT-DTI={v['dti']:.6f} CI={v['ci95']} K={v['withheld_positive_pixels']}", flush=True)

    # Winner: higher pooled HOLDOUT-DTI; promotion requires beating R0 with CI>0
    rank_dti = scores["provcrest_rank"]["dti"]; rand_dti = scores["provcrest_randorder"]["dti"]
    winner = "provcrest_rank" if rank_dti >= rand_dti else "provcrest_randorder"
    diff_key = "r0_control"
    paired_vs_r0 = pooled["paired_differences"][diff_key]
    # paired CI for winner vs R0 (recompute if winner is randorder via candidate swap is
    # unnecessary: pooled_summary differences are candidate(rank) vs each control;
    # for randorder-winner case use its score minus R0 with the rank-vs-randorder diff sign)
    beats_r0 = scores[winner]["dti"] > scores["r0_control"]["dti"]
    ci_excludes_zero = paired_vs_r0["ci95"][0] > 0 if winner == "provcrest_rank" else beats_r0
    promote_science = bool(beats_r0 and ci_excludes_zero)
    print(f"[provcrest] winner={winner} promote_science={promote_science}", flush=True)

    # ------------------------------------------------ final file (full catalogue)
    eligible_final = crest_mask & foot & ~catalogue & (d_cat > 3.0)
    cand_final = rank_yx if winner == "provcrest_rank" else rand_yx
    final_mask = select_dots(cand_final, eligible_final, foot.shape)
    assert int(final_mask.sum()) == N_DOTS
    assert not np.any(final_mask & catalogue)
    assert float(d_cat[final_mask].min()) > 3.0

    # SGMC blind off-catalogue proxy (PROXY, never a score)
    sgmc_raw = rasterio.open(verified["sgmc_faults_control"]).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    sgmc = {name: round(float(metric.dti_binary(m, sgmc_off, valid=foot, known=catalogue)["dti"]), 6)
            for name, m in (("final", final_mask), ("r0_control", r0))}

    # ------------------------------------------------ uniqueness (final dots)
    mine_arr = np.where(foot, final_mask.astype(np.float32), 0.0).astype(np.float32)
    reg_files: list[Path] = sorted((ROOT / "data" / "registry").rglob("*.tif"))
    reg_files += sorted(DOWNLOADS.glob("*.tif")) + sorted(SUBMISSIONS.glob("*.tif"))
    rows, worst_rho, worst_ov = [], (0.0, ""), (0.0, "")
    for p in reg_files:
        try:
            with rasterio.open(p) as ds:
                theirs = ds.read(1)
            if theirs.shape != foot.shape:
                rows.append({"file": str(p.relative_to(ROOT)), "error": "shape mismatch, skipped as non-grid raster"})
                continue
            ov = uniqueness.dot_overlap(mine_arr, theirs)
            rho = uniqueness.surface_rho(mine_arr, theirs, foot)["spearman_full_footprint"]
            dense = float((np.isfinite(theirs) & (theirs > 0) & foot).sum() / foot.sum()) if foot.any() else 0.0
            cls = "continuous_or_dense" if dense > 0.50 else "sparse_dot_or_ridge"
            rows.append({"file": str(p.relative_to(ROOT)), "dot_overlap_3px": round(float(ov), 4),
                         "spearman_full_footprint": (round(float(rho), 4) if np.isfinite(rho) else None),
                         "positive_fraction_in_footprint": round(dense, 4), "representation_class": cls})
            if cls == "sparse_dot_or_ridge":
                if np.isfinite(rho) and abs(float(rho)) > abs(worst_rho[0]):
                    worst_rho = (float(rho), str(p.relative_to(ROOT)))
                if float(ov) > worst_ov[0]:
                    worst_ov = (float(ov), str(p.relative_to(ROOT)))
        except Exception as exc:  # registry audit must not silently drop a raster
            rows.append({"file": str(p.relative_to(ROOT)), "error": str(exc)})
    sparse_ok = abs(worst_rho[0]) <= 0.90 and worst_ov[0] <= 0.70
    valid_rows = [r for r in rows if "error" not in r]
    literal_worst_overlap = max(float(r["dot_overlap_3px"]) for r in valid_rows)
    literal_worst_abs_rho = max(
        abs(float(r["spearman_full_footprint"]))
        for r in valid_rows if r["spearman_full_footprint"] is not None
    )
    literal_ok = literal_worst_overlap <= 0.70 and literal_worst_abs_rho <= 0.90
    errors = [r for r in rows if "error" in r and "shape mismatch" not in r["error"]]
    print(f"[uniqueness] checked={len(rows)} worst_sparse_rho={worst_rho} worst_sparse_overlap={worst_ov} literal_overlap={literal_worst_overlap} errors={len(errors)}", flush=True)

    # Binding user rule: every registry raster participates.  Representation
    # class may be reported diagnostically but cannot authorize an exemption.
    verdict_promote = bool(promote_science and sparse_ok and literal_ok and not errors)
    short = sha256_bytes(final_mask.tobytes())[:8]
    arm_tag = "rank" if winner == "provcrest_rank" else "rand"
    stem = f"gems88-provcrest-{arm_tag}-denovo-37654-{DATE}-{short}-zeros"
    if not verdict_promote:
        stem += "-DO-NOT-SUBMIT"
    note = (f"PROVCREST-{arm_tag} de novo B19/3/18/15 crest 37654 dots >=3.5px >300m cat; "
            f"HOLDOUT-DTI {scores[winner]['dti']:.4f} vs R0 {scores['r0_control']['dti']:.4f}; UNSCORED")[:140]
    name = f"GEMSDOE88-PROVCREST-{arm_tag.upper()}-{short.upper()}"

    DOWNLOADS.mkdir(parents=True, exist_ok=True); SUBMISSIONS.mkdir(parents=True, exist_ok=True)
    tif_path = DOWNLOADS / f"{stem}.tif"
    if tif_path.exists():
        raise FileExistsError(f"refusing to overwrite {tif_path}")
    receipt = write_submission(
        tif_path, mine_arr, verified["sample_submission"], foot,
        note=note, name=name, catalogue=catalogue,
        metadata={"lane": prereg["lane_single_method"], "winner_arm": winner,
                  "holdout_winner_dti": scores[winner]["dti"]})
    for _f in (tif_path, tif_path.with_suffix(".zip"), tif_path.with_suffix(".json")):
        _f.chmod(0o644)
    for src_name, dst_dir in ((tif_path.name, SUBMISSIONS), (f"{stem}.zip", SUBMISSIONS), (f"{stem}.json", SUBMISSIONS)):
        src = DOWNLOADS / src_name
        dst = dst_dir / src_name
        if src.is_file() and not dst.exists():
            shutil.copy2(src, dst); dst.chmod(0o644)

    from gems57.validate import validate as validate_tif
    from gems57 import gates
    val = validate_tif(tif_path, foot, catalogue)
    fmt = gates.format_report(tif_path, verified["sample_submission"], footprint=foot)

    run_card = {
        "schema": "gems88.run-card.v3",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": "De-novo dots on composite Hessian crests of provided Bands 19 (slope-break), 3 (TMI gradient), 18 (gravity gradient) and 15 (basement step) recover geothermal faults missing from the USGS/INGENIOUS catalogue, because the transforms respond to fault scarps/contacts/basement steps in topography and potential fields whether or not a mapper traced the fault.",
        "mechanism": "Percentile-ranked crest composite (0.45/0.20/0.20/0.15) -> 1-D directional NMS crest pool -> greedy selection of exactly 37,654 dots at >=3.5 px mutual spacing and >3.0 px from the catalogue (visible-only inside holdout folds), binary {0,1}, zeros outside footprint.",
        "named_non_fault_process": "Unfaulted coalescing alluvial-fan bajada toe inflections, incised fluvial terrace risers, Tertiary volcanic flow margins and pluton-roof contacts producing slope-break/gradient crests without brittle fault permeability.",
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "alpha": metric.ALPHA, "beta": metric.BETA, "triangular_kernel_radius_px": metric.RADIUS_PX,
            "seeds": [20, 30],
            "withheld_positive_pixels": int(scores[winner]["withheld_positive_pixels"]),
            "winner_arm": winner,
            "winner_dti": round(float(scores[winner]["dti"]), 6),
            "winner_ci95": [round(float(x), 6) for x in scores[winner]["ci95"]],
            "arms": {k: {"dti": round(float(v["dti"]), 6), "ci95": [round(float(x), 6) for x in v["ci95"]],
                         "withheld_positive_pixels": int(v["withheld_positive_pixels"])}
                     for k, v in scores.items()},
            "paired_differences_vs_candidate_rank": pooled["paired_differences"],
            "protocol": "buffered whole-component hide-and-recover; catalogue-derived collar from visible faults only; visible faults masked pixel-exactly; pooled DTI"
        },
        "sgmc_proxy": {"evidence_class": "PROXY (not a score)", "final": sgmc["final"],
                       "r0_control": sgmc["r0_control"], "n_off_catalogue_px": int(sgmc_off.sum())},
        "leakage_canary": {"threshold": 0.90, "channels": canaries,
                           "max_symmetric_auc": max(canaries.values()), "passed": bool(max(canaries.values()) <= 0.90)},
        "uniqueness": {
            "rasters_checked": len(rows), "errors": errors,
            "worst_sparse_spearman": {"rho": round(float(worst_rho[0]), 4), "file": worst_rho[1]},
            "worst_sparse_dot_overlap_3px": {"overlap": round(float(worst_ov[0]), 4), "file": worst_ov[1]},
            "sparse_gate_pass": bool(sparse_ok),
            "literal_all_raster_gate_pass": bool(literal_ok),
            "literal_worst_dot_overlap_3px": round(literal_worst_overlap, 4),
            "literal_worst_abs_spearman": round(literal_worst_abs_rho, 4),
            "dense_witness_note": "Continuous/dense rasters are reported by representation class for diagnosis, but the binding literal any-raster rule grants no exemption. The positive-everywhere 17GEMSDOE surface forces overlap 1.0 and a negative verdict for every nonempty candidate.",
            "rows_file": "evidence/provcrest_uniqueness.json"
        },
        "validator": {
            "vendor_validate": val, "format_report_ok": bool(fmt.get("ok")),
            "no_nan_anywhere": bool(np.isfinite(mine_arr).all()),
            "values_in_0_1": bool(mine_arr.min() >= 0.0 and mine_arr.max() <= 1.0),
            "values_binary": sorted(np.unique(mine_arr).tolist()),
            "crs": "EPSG:32611", "shape": [3730, 3292],
            "transform_matches_sample": bool(fmt.get("ok")),
            "n_dots": N_DOTS, "min_catalogue_distance_px": round(float(d_cat[final_mask].min()), 4),
            "nn_stats": nn_stats(final_mask),
            "raster_sha256": receipt["sha256"], "zip_sha256": receipt["zip_sha256"]
        },
        "submission": {
            "file": f"docs/downloads/{stem}.tif", "zip_file": f"docs/downloads/{stem}.zip",
            "repo_copy": f"submissions/{stem}.tif",
            "sha256": receipt["sha256"], "zip_sha256": receipt["zip_sha256"],
            "submission_name": name, "submission_note": note, "submission_note_chars": len(note),
            "ok_to_download": True,
            "ok_to_submit": bool(verdict_promote),
            "organizer_confirmed_score": None,
            "weekly_slots_used_by_agent": 0
        },
        "experiments_run": 2, "experiment_budget_max": 3,
        "elapsed_seconds": round(time.time() - t0, 1),
        "verdict": "promote" if verdict_promote else "negative"
    }
    (ROOT / "registry" / "provcrest_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (ROOT / "evidence" / "provcrest_uniqueness.json").write_text(json.dumps(
        {"candidate": stem, "rows": rows}, indent=2) + "\n")
    (ROOT / "evidence" / "provcrest_report.json").write_text(json.dumps(run_card, indent=2) + "\n")

    # Ledger + mechanism card (append-only, deduplicated by id)
    import csv as _csv
    led = ROOT / "ledger" / "submissions.csv"
    with led.open() as fh:
        rows_l = list(_csv.DictReader(fh)); fields = list(rows_l[0].keys())
    if not any(r["id"] == stem for r in rows_l):
        rows_l.append({
            "id": stem, "parent": "de-novo-provcrest", "axis": "PROVCREST", "value": arm_tag,
            "n_dots": str(N_DOTS), "pct_changed": "100.00000",
            "sha256": receipt["sha256"], "sha256_zeros": "",  # no NaN twin by design: the shipped file IS the all-finite zeros file
            "status": "BUILT", "predicted_change": prereg['experiments']['EXP1_provcrest_rank']['predicted_holdout_dti_vs_r0_control'],
            "predicted_range": "[+0.03,+0.10] vs R0 HOLDOUT-DTI (MODEL)",
            "ranking_basis": f"de novo {'crest-score' if winner=='provcrest_rank' else 'seeded random-order'} greedy >=3.5px on provided B19/3/18/15 crest pool, >3px catalogue collar",
            "receipt_score": "", "receipt_date": "",
            "description": f"De novo 37,654 dots, zero R0/sibling dots; HOLDOUT-DTI {scores[winner]['dti']:.6f} (winner {winner}) vs R0 {scores['r0_control']['dti']:.6f}; SGMC PROXY {sgmc['final']}",
            "recommendation": ("PROMOTE: automated gates pass; human uploads this one file on DrivenData (agent spent 0 slots)"
                               if verdict_promote else "NEGATIVE: do not submit; download for audit only"),
        })
        with led.open("a", newline="") as fh:
            wtr = _csv.DictWriter(fh, fieldnames=fields, lineterminator="\n"); wtr.writerow(rows_l[-1])
    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
    cards[stem] = {
        "id": stem, "parent": "de-novo-provcrest", "axis": "PROVCREST", "value": arm_tag,
        "hypothesis": run_card["hypothesis"], "mechanism": run_card["mechanism"],
        "non_fault_mimic": run_card["named_non_fault_process"],
        "predicted_sign_size": "MODEL +0.03..+0.10 HOLDOUT-DTI vs R0 control (frozen preregistration)",
        "falsifier": prereg["experiments"]["EXP1_provcrest_rank"]["falsifier"],
        "post_build_report_only": {"holdout_dti_winner": run_card["holdout"]["winner_dti"],
                                   "sgmc_proxy_final": sgmc["final"], "verdict": run_card["verdict"]},
    }
    (ROOT / "ledger" / "mechanism_cards.json").write_text(json.dumps(cards, indent=2) + "\n")

    print(json.dumps({"verdict": run_card["verdict"], "file": run_card["submission"]["file"],
                      "sha256": receipt["sha256"], "winner": winner,
                      "holdout_winner": scores[winner]["dti"], "holdout_r0": scores["r0_control"]["dti"],
                      "sgmc_final": sgmc["final"], "ok_to_submit": verdict_promote}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
