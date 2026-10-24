#!/usr/bin/env python3
"""Execute the preregistered H88-QTSK 3-experiment suite end-to-end with <1.4 GB RSS:
  --stage holdout : Canary check (58 cols) + finish paired 8-fold holdout (seeds 20+21, n=22,893)
                    using sparse fold checkpoints and 7 KB block-term accumulators.
  --stage prod    : 4-quadrant OOF production inference + pre-placement surface Spearman |rho| <= 0.90
                    + 223-raster uniqueness + shared submission_writer + LZW sample-parity GeoTIFF/ZIP
                    + JSON run card & evidence receipt.
  --stage all     : Run both stages sequentially.
"""
from __future__ import annotations

import argparse
import ctypes
import gc
import json
import resource
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems57 import (  # noqa: E402
    evaluate_holdout,
    gates as v_gates,
    grid as grid_mod,
    holdout,
    submission_writer,
    validate as v_validate,
)
from gems88 import adhr, edge, gate, physics, portal_writer, qtsk, registry_paths  # noqa: E402

ARMS = ("control_adhr", "exp1_qtsk_phys", "exp2_qtsk_dual", "exp3_qtsk_strat")


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def drop_memmap_pages(*arrays: np.ndarray) -> None:
    """Advise kernel (MADV_DONTNEED=4 on Linux) that clean file-backed mmap pages can be reclaimed."""
    try:
        libc = ctypes.CDLL("libc.so.6")
        for a in arrays:
            if isinstance(a, np.memmap) and a.ctypes.data:
                libc.madvise(ctypes.c_void_p(a.ctypes.data), ctypes.c_size_t(a.nbytes), ctypes.c_int(4))
    except Exception:
        pass


def run_phys44_canaries(grid: grid_mod.Grid, X_phys: np.ndarray, folds_by_seed: dict[int, list[dict]]) -> dict:
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    fp_idx = np.full(grid.shape, -1, dtype=np.int32)
    fp_idx[ys, xs] = np.arange(ys.size, dtype=np.int32)
    pos_rows, neg_rows = [], []
    rng = np.random.default_rng(20261025)
    for seed in sorted(folds_by_seed):
        for fold in folds_by_seed[seed]:
            act = fold["region"] & fp & ~fold["masked_known"]
            tr = fold["truth"] & act
            neg = act & ~tr
            p_i = fp_idx[tr]
            n_i = fp_idx[neg]
            if n_i.size > 25_000:
                n_i = rng.choice(n_i, size=25_000, replace=False)
            pos_rows.append(p_i)
            neg_rows.append(n_i)
    p_all = np.concatenate(pos_rows)
    n_all = np.concatenate(neg_rows)
    y = np.concatenate([np.ones(p_all.size, dtype=np.int8), np.zeros(n_all.size, dtype=np.int8)])
    idx_all = np.concatenate([p_all, n_all])
    worst_sym = 0.0
    worst_name = ""
    for j, name in enumerate(physics.ALL_PHYS_FEATURES):
        vals = np.asarray(X_phys[idx_all, j], dtype=np.float64)
        auc = float(roc_auc_score(y, vals))
        sym = max(auc, 1.0 - auc)
        if sym > worst_sym:
            worst_sym = sym
            worst_name = name
    if worst_sym > 0.90:
        raise RuntimeError(f"PHYS44 canary failed: {worst_name} sym AUC {worst_sym:.5f} > 0.90")
    return {
        "passed": True,
        "n_features": len(physics.ALL_PHYS_FEATURES),
        "max_symmetric_auc": round(worst_sym, 6),
        "max_feature": worst_name,
    }


def run_holdout_stage(t_start: float) -> dict:
    cache_dir = ROOT / ".cache"
    gems88_cache = cache_dir / "gems88"
    ckpt_dir = cache_dir / "qtsk_fold_ckpts_v1"
    gems88_cache.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    data_dir = ROOT / "data"

    g = grid_mod.load_grid()
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache_dir)
    X_qtsk, U_strike, _ = qtsk.build_or_load_qtsk_memmap(g, cache_dir, data_dir)

    folds_by_seed = {
        s: holdout.buffered_component_draw(g, seed=s, buffer_px=3, boundary_px=12)[0]
        for s in (20, 21)
    }

    print(f"[{time.time()-t_start:.1f}s] Step 1: Protocol Rule 4 single-feature leakage canaries (58 cols)...", flush=True)
    canary_qtsk = qtsk.run_single_feature_canaries(g, X_qtsk, folds_by_seed)
    canary_phys = run_phys44_canaries(g, X_phys, folds_by_seed)
    drop_memmap_pages(X_phys, X_qtsk)
    print(
        f"  CANARY PASS: QTSK14 max_sym_auc={canary_qtsk['max_symmetric_auc']} ({canary_qtsk['max_feature']}), "
        f"PHYS44 max_sym_auc={canary_phys['max_symmetric_auc']} ({canary_phys['max_feature']})",
        flush=True,
    )

    with rasterio.open(data_dir / "training_features.tif") as ds:
        det_elev = edge.clean_band(ds.read(12), g.footprint)[0]
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, gems88_cache)
    del det_elev
    sense_src = adhr.build_sense_raster(data_dir / "external/trace_segments_utm11.csv", g)
    vis_cache: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for seed in (20, 21):
        vis_cache[seed] = adhr.compute_visible_struct_fp(
            g, folds_by_seed[seed][0]["visible"], sense_src, scarp_fields, gems88_cache, f"seed{seed}"
        )
    _ = adhr.compute_visible_struct_fp(
        g, g.catalogue, sense_src, scarp_fields, gems88_cache, "prod_fullcat"
    )
    del scarp_fields, sense_src
    gc.collect()

    # Stream block-level Tversky accumulators (7 KB per arm!) instead of holding 32 dense 2D rasters
    terms_full: dict[str, np.ndarray | None] = {a: None for a in ARMS}
    terms_gt25: dict[str, np.ndarray | None] = {a: None for a in ARMS}
    per_fold: dict[str, list[dict]] = {a: [] for a in ARMS}
    withheld_full = 0
    withheld_gt25 = 0
    block_side = 200

    print(f"[{time.time()-t_start:.1f}s] Step 2: Paired 8-fold holdout evaluation (n=22,893)...", flush=True)
    for seed in (20, 21):
        folds = folds_by_seed[seed]
        X_v22, d_vis_fp, comp_len_fp = vis_cache[seed]
        d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
        gt25_mask = d_vis_grid > 25.0
        del d_vis_grid

        for fold in folds:
            qid = int(fold["fold"])
            ckpt = ckpt_dir / f"s{seed}_q{qid}.npz"
            reg_full = fold["region"] & g.footprint & ~fold["masked_known"]
            far_valid = reg_full & gt25_mask
            far_truth = fold["truth"] & far_valid
            withheld_full += int((fold["truth"] & reg_full).sum())
            withheld_gt25 += int(far_truth.sum())
            far_fold = {
                **fold,
                "truth": far_truth,
                "region": far_valid,
                "masked_known": np.zeros_like(far_valid),
            }

            if not ckpt.is_file():
                t_f = time.time()
                train_regions = np.zeros(g.shape, dtype=bool)
                train_truth = np.zeros(g.shape, dtype=bool)
                for other in folds:
                    if int(other["fold"]) != qid:
                        train_regions |= other["region"]
                        train_truth |= other["truth"]
                test_region = fold["region"]
                visible = fold["visible"]
                run_seed = 88_100 + seed * 10 + qid

                p_ctrl, _, _ = adhr.predict_adhr_fold(
                    g, X_phys, X_v22, d_vis_fp, comp_len_fp, visible,
                    train_regions, train_truth, test_region, seed=run_seed
                )
                drop_memmap_pages(X_phys, X_v22)
                arm_preds = qtsk.predict_qtsk_all_arms_fold(
                    g, X_phys, X_qtsk, U_strike, X_v22, d_vis_fp, comp_len_fp, visible,
                    train_regions, train_truth, test_region, seed=run_seed
                )
                drop_memmap_pages(X_phys, X_qtsk, X_v22)
                all_p = {"control_adhr": p_ctrl, **arm_preds}
                save_dict = {}
                for k_arm, arr in all_p.items():
                    dy, dx = np.nonzero(arr > 0)
                    save_dict[k_arm] = np.column_stack([dy, dx]).astype(np.int32)
                np.savez_compressed(ckpt, **save_dict)
                del p_ctrl, arm_preds, all_p, save_dict
                gc.collect()
                elapsed_f = time.time() - t_f
                tag_msg = f"computed in {elapsed_f:.1f}s"
            else:
                tag_msg = "reloaded from ckpt"

            z = np.load(ckpt, allow_pickle=False)
            f_scores = {}
            for a_key in ARMS:
                arr = np.zeros(g.shape, dtype=np.float32)
                yx = z[a_key]
                if len(yx):
                    arr[yx[:, 0], yx[:, 1]] = 1.0
                sc, bt = evaluate_holdout.evaluate(arr, fold, g.footprint, block_side=block_side)
                _, bt_far = evaluate_holdout.evaluate(arr, far_fold, g.footprint, block_side=block_side)
                terms_full[a_key] = bt if terms_full[a_key] is None else (terms_full[a_key] + bt)
                terms_gt25[a_key] = bt_far if terms_gt25[a_key] is None else (terms_gt25[a_key] + bt_far)
                n_dots = int((arr[reg_full] > 0).sum())
                n_far = int((arr[far_valid] > 0).sum())
                f_scores[a_key] = float(sc["dti"])
                per_fold[a_key].append(
                    {
                        "seed": seed,
                        "fold": fold["name"],
                        "dti": round(float(sc["dti"]), 6),
                        "dots": n_dots,
                        "dots_gt25": n_far,
                        "share_gt25": round(float(n_far) / max(n_dots, 1), 5),
                    }
                )
                del arr
            z.close()
            gc.collect()
            print(
                f"  [{time.time()-t_start:.1f}s] Seed {seed} {fold['name']} ({tag_msg}, RSS={rss_mb():.0f}MB) | "
                f"ADHR={f_scores['control_adhr']:.5f} | EXP1={f_scores['exp1_qtsk_phys']:.5f} | "
                f"EXP2={f_scores['exp2_qtsk_dual']:.5f} | EXP3={f_scores['exp3_qtsk_strat']:.5f}",
                flush=True,
            )
        drop_memmap_pages(X_v22)

    def _collect(terms_map: dict[str, np.ndarray | None], boot_seed: int) -> dict:
        out = {}
        base_summary = evaluate_holdout.pooled_summary(
            terms_map, draws=400, seed=boot_seed, candidate="control_adhr"
        )
        for a in ARMS:
            if a == "control_adhr":
                sc_a = base_summary["scores"][a]
                out[a] = {
                    "pooled_dti": round(float(sc_a["dti"]), 6),
                    "ci95": [round(float(x), 6) for x in sc_a["ci95"]],
                    "paired_delta_vs_adhr": 0.0,
                    "paired_delta_ci95": [0.0, 0.0],
                }
            else:
                s_cand = evaluate_holdout.pooled_summary(
                    terms_map, draws=400, seed=boot_seed, candidate=a
                )
                sc_a = s_cand["scores"][a]
                pd_a = s_cand["paired_differences"]["control_adhr"]
                out[a] = {
                    "pooled_dti": round(float(sc_a["dti"]), 6),
                    "ci95": [round(float(x), 6) for x in sc_a["ci95"]],
                    "paired_delta_vs_adhr": round(float(pd_a["delta"]), 6),
                    "paired_delta_ci95": [round(float(x), 6) for x in pd_a["ci95"]],
                }
        return out

    holdout_bundle = {
        "canary_qtsk": canary_qtsk,
        "canary_phys": canary_phys,
        "holdout_summary": {
            "evaluator_version": evaluate_holdout.VERSION,
            "block_side_px": block_side,
            "bootstrap_draws": 400,
            "withheld_positive_pixels_full": withheld_full,
            "withheld_positive_pixels_gt25": withheld_gt25,
            "overall": _collect(terms_full, boot_seed=1729),
            "blind_basin_gt25": _collect(terms_gt25, boot_seed=2718),
            "per_fold": per_fold,
        },
    }
    for arm_name, st in holdout_bundle["holdout_summary"]["overall"].items():
        st_far = holdout_bundle["holdout_summary"]["blind_basin_gt25"][arm_name]
        print(
            f"  SUMMARY {arm_name:16s} | FULL HOLDOUT-DTI={st['pooled_dti']:.6f} {st['ci95']} "
            f"(d_ADHR={st['paired_delta_vs_adhr']:+.6f} {st['paired_delta_ci95']}) | "
            f"BLIND(>25px) DTI={st_far['pooled_dti']:.6f} (d_ADHR={st_far['paired_delta_vs_adhr']:+.6f})",
            flush=True,
        )
    (cache_dir / "qtsk_holdout_bundle_v1.json").write_text(json.dumps(holdout_bundle, indent=2) + "\n")
    return holdout_bundle


def run_prod_stage(t_start: float, holdout_bundle: dict | None = None) -> None:
    cache_dir = ROOT / ".cache"
    gems88_cache = cache_dir / "gems88"
    data_dir = ROOT / "data"
    if holdout_bundle is None:
        holdout_bundle = json.loads((cache_dir / "qtsk_holdout_bundle_v1.json").read_text())
    canary_qtsk = holdout_bundle["canary_qtsk"]
    canary_phys = holdout_bundle["canary_phys"]
    holdout_summary = holdout_bundle["holdout_summary"]

    g = grid_mod.load_grid()
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache_dir)
    X_qtsk, U_strike, _ = qtsk.build_or_load_qtsk_memmap(g, cache_dir, data_dir)

    folds_by_seed = {
        s: holdout.buffered_component_draw(g, seed=s, buffer_px=3, boundary_px=12)[0]
        for s in (20, 21)
    }
    with rasterio.open(data_dir / "training_features.tif") as ds:
        det_elev = edge.clean_band(ds.read(12), g.footprint)[0]
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, gems88_cache)
    del det_elev
    sense_src = adhr.build_sense_raster(data_dir / "external/trace_segments_utm11.csv", g)
    vis_cache = {
        s: adhr.compute_visible_struct_fp(
            g, folds_by_seed[s][0]["visible"], sense_src, scarp_fields, gems88_cache, f"seed{s}"
        )
        for s in (20, 21)
    }
    vis_prod = adhr.compute_visible_struct_fp(
        g, g.catalogue, sense_src, scarp_fields, gems88_cache, "prod_fullcat"
    )
    del scarp_fields, sense_src
    gc.collect()

    print(f"[{time.time()-t_start:.1f}s] Step 5: 4-quadrant OOF production inference across footprint...", flush=True)
    prod_out = qtsk.fit_qtsk_production_oof(
        g, X_phys, X_qtsk, U_strike, folds_by_seed, vis_cache, vis_prod
    )
    drop_memmap_pages(X_phys, X_qtsk)
    del vis_cache, vis_prod
    gc.collect()

    dl_dir = ROOT / "docs/downloads"
    for old_q in dl_dir.glob("gems88-qtsk-coverstep-knickwave-*"):
        old_q.unlink()

    reg_items = registry_paths.registry_list(exclude=("gems88-phys44",))
    d_cat = ndi.distance_transform_edt(~g.catalogue)

    stage_dir = cache_dir / "qtsk_audit_stage"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)
    sample_path = ROOT / "data/bridge/sample_submission.tif"

    cand_reports = {}
    for tag, pred_key, surf_key in (
        ("exp2_qtsk_dual", "exp2_pred", "exp2_surface"),
        ("exp3_qtsk_strat", "exp3_pred", "exp3_surface"),
    ):
        p_arr = prod_out[pred_key]
        s_arr = prod_out[surf_key]
        tmp_tif = stage_dir / f"{tag}.tif"
        portal_writer.write_portal_tif(tmp_tif, p_arr, sample_path, g.footprint)
        dots_mask = (p_arr > 0) & g.footprint
        fp_stats = gate.fingerprint(dots_mask, d_cat)
        fp_pass = gate.fingerprint_screen(fp_stats)
        u_rep = gate.uniqueness_report(tmp_tif, reg_items, g.footprint)
        ok_u_rows = [r for r in u_rep.pop("rows", []) if "error" not in r]
        ok_u_rows.sort(key=lambda r: r["like_for_like_overlap_3px"], reverse=True)
        u_rep["top10_like_for_like"] = [
            {
                "label": r["label"],
                "registry_dots": r["registry_dots"],
                "like_for_like_overlap_3px": round(float(r["like_for_like_overlap_3px"]), 6),
                "literal_overlap_3px": round(float(r["literal_overlap_3px"]), 6),
                "rho_final": round(float(r["rho_final"]), 6),
            }
            for r in ok_u_rows[:10]
        ]
        worst_lit_row = max(ok_u_rows, key=lambda r: r["literal_overlap_3px"], default=None)
        u_rep["worst_literal_forward_overlap"] = (
            None
            if worst_lit_row is None
            else {
                "label": worst_lit_row["label"],
                "value": round(float(worst_lit_row["literal_overlap_3px"]), 6),
            }
        )
        s_rep = qtsk.check_surface_spearman_against_registry(s_arr, reg_items, g.footprint)
        cand_reports[tag] = {
            "dots": int(dots_mask.sum()),
            "fingerprint": fp_stats,
            "fingerprint_screen_pass": fp_pass,
            "uniqueness_dots": u_rep,
            "uniqueness_pre_placement_surface": s_rep,
        }
        print(
            f"  AUDIT {tag:16s}: dots={int(dots_mask.sum())}, share_le2={fp_stats['share_le2']:.4f}, "
            f"share_gt25={fp_stats['share_gt25']:.4f} (fp_pass={fp_pass}), "
            f"like4like_unique={u_rep['unique_like_for_like']} (worst={u_rep['worst_like_for_like_overlap']}), "
            f"surf_max_|rho|={s_rep['max_abs_spearman_rho']} ({s_rep['max_spearman_target']})",
            flush=True,
        )

    eligible_both = []
    eligible_unique = []
    for tag in ("exp2_qtsk_dual", "exp3_qtsk_strat"):
        cr = cand_reports[tag]
        is_uniq = bool(
            cr["uniqueness_dots"]["unique_like_for_like"]
            and cr["uniqueness_pre_placement_surface"]["passed"]
        )
        dti_val = float(holdout_summary["overall"][tag]["pooled_dti"])
        if is_uniq:
            eligible_unique.append((dti_val, tag))
            if cr["fingerprint_screen_pass"]:
                eligible_both.append((dti_val, tag))

    if eligible_both:
        eligible_both.sort(reverse=True)
        chosen_arm = eligible_both[0][1]
        selection_reason = (
            "Passed BOTH 223-raster uniqueness (pre-placement |rho| <= 0.90 and 3-px overlap <= 0.70) "
            "AND fleet blind-basin screen (share_le2 == 0, share_gt25 >= 0.35)."
        )
    elif eligible_unique:
        eligible_unique.sort(reverse=True)
        chosen_arm = eligible_unique[0][1]
        selection_reason = "Highest HOLDOUT-DTI arm passing 223-raster uniqueness (pre-placement |rho| <= 0.90 and 3-px overlap <= 0.70)."
    else:
        chosen_arm = "exp3_qtsk_strat"
        selection_reason = "Fallback diagnostic artifact (logged duplicate/blocked per Protocol Rule 1)."

    chosen_pred = prod_out["exp3_pred" if chosen_arm == "exp3_qtsk_strat" else "exp2_pred"]
    sub_name = "gems88-qtsk-coverstep-knickwave-20261024-v1"
    sub_note = (
        f"GEMSDOE88 {chosen_arm.upper()}: QTS cover-step + 10m chi knickwave + LiDAR polarity + OOF Dinkelbach"
    )[:140]

    sw_stage = cache_dir / "qtsk_submission_writer_verify"
    if sw_stage.exists():
        shutil.rmtree(sw_stage)
    sw_stage.mkdir(parents=True, exist_ok=True)
    sw_receipt = submission_writer.write_submission(
        sw_stage / f"{sub_name}.tif",
        chosen_pred,
        sample_path,
        g.footprint,
        note=sub_note,
        name=sub_name,
        catalogue=g.catalogue,
    )

    tmp_portal_tif = sw_stage / "portal_lzw.tif"
    portal_writer.write_portal_tif(tmp_portal_tif, chosen_pred, sample_path, g.footprint)
    sha_full = gate.sha256_file(tmp_portal_tif)
    sha8 = sha_full[:8]
    final_stem = f"gems88-qtsk-coverstep-knickwave-20261024-{sha8}-DO-NOT-SUBMIT"
    final_tif = dl_dir / f"{final_stem}.tif"
    final_zip = dl_dir / f"{final_stem}.zip"
    shutil.copy2(tmp_portal_tif, final_tif)
    portal_writer.write_single_member_zip(final_zip, final_tif)
    zip_sha = gate.sha256_file(final_zip)

    vals_sw = gate.read_values(sw_stage / f"{sub_name}.tif", g.footprint)
    vals_lzw = gate.read_values(final_tif, g.footprint)
    assert np.array_equal(vals_sw, vals_lzw), "Pixel mismatch between submission_writer and portal_writer!"

    portal_rep = gate.portal_validate(final_tif, sample_path, g.footprint)
    portal_zip_rep = gate.portal_validate(final_zip, sample_path, g.footprint)
    template_fmt_rep = v_gates.format_report(final_tif, sample_path, footprint=g.footprint)
    template_val_rep = v_validate.validate(final_tif, g.footprint, g.catalogue)
    v_validate.assert_submittable(template_val_rep)

    chosen_audit = cand_reports[chosen_arm]
    chosen_holdout = holdout_summary["overall"][chosen_arm]
    chosen_blind = holdout_summary["blind_basin_gt25"][chosen_arm]

    beats_adhr_ci = bool(chosen_holdout["paired_delta_ci95"][0] > 0.0)
    unique_literal = bool(chosen_audit["uniqueness_dots"]["unique_literal"])
    unique_like4like = bool(
        chosen_audit["uniqueness_dots"]["unique_like_for_like"]
        and chosen_audit["uniqueness_pre_placement_surface"]["passed"]
    )

    verdict = (
        "promote"
        if (beats_adhr_ci and unique_literal and unique_like4like and chosen_audit["fingerprint_screen_pass"] and portal_rep["ok"])
        else "negative"
    )

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    wall_s = round(time.time() - t_start, 2)

    run_card = {
        "schema": "gems88-qtsk-run-card-v1",
        "generated_utc": now_utc,
        "branch": "arena/14b2260c-gemsdoe88",
        "lane": "H88-QTSK",
        "emitted_experiment_arm": chosen_arm,
        "emission_selection_reason": selection_reason,
        "hypothesis": (
            "Concealed Basin-and-Range normal faults buried beneath Holocene piedmont/playa cover or hidden inside "
            "Nevada's 24.6% 3DEP 1 m LiDAR gap manifest as (1) multi-scale steps in unconsolidated basin-fill "
            "thickness (depth_to_base_surf) decoupled from modern surface slope (det_elev) and concordant with "
            "negative isostatic gravity gradients, coupled with (2) cross-catchment 10 m DEM fluvial chi-knickpoint "
            "and uplifted-footwall channel wavefronts (dem10_chi_100m_u8), 1 m LiDAR scarp facing polarity "
            "(downface vs upface), and 10 m planar triangular-facet coherence."
        ),
        "mechanism": (
            "14 strictly label-blind QTSK physical-geomorphic channels appended to the 44-col geophysical/hydrothermal "
            "memmap, trained via de-jittered 4-quadrant out-of-fold dual-expectation HistGradientBoosting (excluding "
            "ambiguous 0 < d <= 2.0 px cartographic digitization-jitter flanks from classifier hard negatives while "
            "fitting exact 300 m kernel decay in the regressor), axial spin-2 geological strike smoothing, and "
            "exact Dinkelbach fractional-programming {0, 1} allocation."
        ),
        "named_non_fault_mimic": (
            "Buried pre-Quaternary fluvial paleovalleys / Miocene volcanic pinchouts (mitigated by signed half-graben "
            "gravity concordance and geodetic transtensional dilation), plus lithologic caprock knickpoints, incised "
            "axial trunk rivers (Humboldt/Truckee/Carson), Lake Lahontan 1330 m / 1555 m shorelines, and symmetric "
            "two-walled arroyos (mitigated by log10 drainage-area headwater gating and LiDAR downface-upface polarity)."
        ),
        "evidence_label": "HOLDOUT-DTI",
        "evaluator_version": holdout_summary["evaluator_version"],
        "withheld_positive_pixels": holdout_summary["withheld_positive_pixels_full"],
        "withheld_positive_pixels_blind_gt25": holdout_summary["withheld_positive_pixels_gt25"],
        "holdout_dti": chosen_holdout["pooled_dti"],
        "holdout_dti_ci95": chosen_holdout["ci95"],
        "paired_delta_vs_adhr": chosen_holdout["paired_delta_vs_adhr"],
        "paired_delta_ci95": chosen_holdout["paired_delta_ci95"],
        "blind_basin_gt25_holdout_dti": chosen_blind["pooled_dti"],
        "blind_basin_gt25_ci95": chosen_blind["ci95"],
        "blind_basin_gt25_paired_delta_vs_adhr": chosen_blind["paired_delta_vs_adhr"],
        "blind_basin_gt25_paired_delta_ci95": chosen_blind["paired_delta_ci95"],
        "all_experiments_holdout": {
            "control_adhr": holdout_summary["overall"]["control_adhr"],
            "exp1_qtsk_phys": holdout_summary["overall"]["exp1_qtsk_phys"],
            "exp2_qtsk_dual": holdout_summary["overall"]["exp2_qtsk_dual"],
            "exp3_qtsk_strat": holdout_summary["overall"]["exp3_qtsk_strat"],
        },
        "all_experiments_blind_gt25": holdout_summary["blind_basin_gt25"],
        "leakage_canary": {
            "passed": bool(canary_qtsk["passed"] and canary_phys["passed"]),
            "auc_ceiling": 0.90,
            "qtsk14_max_symmetric_auc": canary_qtsk["max_symmetric_auc"],
            "qtsk14_max_feature": canary_qtsk["max_feature"],
            "phys44_max_symmetric_auc": canary_phys["max_symmetric_auc"],
            "phys44_max_feature": canary_phys["max_feature"],
            "qtsk14_features": canary_qtsk["features"],
        },
        "registry_uniqueness": {
            "n_registry_rasters_checked": len(reg_items),
            "pre_placement_surface_max_abs_spearman_rho": chosen_audit["uniqueness_pre_placement_surface"]["max_abs_spearman_rho"],
            "pre_placement_surface_max_target": chosen_audit["uniqueness_pre_placement_surface"]["max_spearman_target"],
            "pre_placement_surface_pass_le_0p90": chosen_audit["uniqueness_pre_placement_surface"]["passed"],
            "like_for_like_3px_unique_le_0p70": chosen_audit["uniqueness_dots"]["unique_like_for_like"],
            "worst_like_for_like_3px_overlap": chosen_audit["uniqueness_dots"]["worst_like_for_like_overlap"],
            "literal_all_registry_3px_unique_le_0p70": unique_literal,
            "worst_literal_forward_3px_overlap": chosen_audit["uniqueness_dots"]["worst_literal_forward_overlap"],
            "literal_blocker_explanation": (
                "17GEMSDOE_E-proba-multiscale is strictly positive (>0) on all 5,167,373 footprint pixels, "
                "forcing literal forward 3-px dot overlap = 1.0000 for every nonempty raster unless a human "
                "selector explicitly applies like-for-like sparse comparison."
            ),
        },
        "distance_fingerprint": chosen_audit["fingerprint"],
        "distance_fingerprint_screen_pass": chosen_audit["fingerprint_screen_pass"],
        "raster": {
            "tif_path": f"docs/downloads/{final_tif.name}",
            "zip_path": f"docs/downloads/{final_zip.name}",
            "sha256": sha_full,
            "zip_sha256": zip_sha,
            "tif_bytes": final_tif.stat().st_size,
            "zip_bytes": final_zip.stat().st_size,
            "n_positive_dots": chosen_audit["dots"],
        },
        "validator_output": {
            "portal_ok": bool(portal_rep["ok"] and portal_zip_rep["ok"]),
            "zip_ok": bool(portal_zip_rep["ok"]),
            "layout_parity_with_sample": bool(portal_rep["layout_parity_with_sample"]),
            "no_nan_inside_footprint": bool(portal_rep["checks"]["footprint_cells_finite"]),
            "all_cells_finite": bool(portal_rep["checks"]["all_finite"]),
            "values_in_0_1": bool(portal_rep["checks"]["min_ge_0"] and portal_rep["checks"]["max_le_1"]),
            "min_value": portal_rep["min"],
            "max_value": portal_rep["max"],
            "crs": "EPSG:32611" if portal_rep["checks"]["crs_epsg_32611"] else "MISMATCH",
            "shape": list(g.shape),
            "transform": list(g.transform)[:6],
            "compression": portal_rep["layout"]["compress"],
            "second_decoder": portal_rep["second_decoder"],
            "shared_template_format_ok": bool(template_fmt_rep["ok"]),
            "shared_submission_writer_sha256": sw_receipt["sha256"],
            "problems": portal_rep["problems"] + portal_zip_rep["problems"],
        },
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "ok_to_download": bool(portal_rep["ok"] and template_fmt_rep["ok"]),
        "ok_to_submit": False,
        "approved_for_weekly_slot": False,
        "verdict": verdict,
        "wall_seconds": wall_s,
        "peak_rss_mb": round(rss_mb(), 1),
    }

    evidence_payload = {
        "run_card": run_card,
        "holdout_detail": holdout_summary,
        "production_arm_audits": cand_reports,
    }
    (ROOT / "evidence/qtsk88_experiment_20261024.json").write_text(json.dumps(evidence_payload, indent=2) + "\n")
    (ROOT / "registry/qtsk88_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")
    (ROOT / "docs/data/qtsk88_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n")

    print(
        f"\n[{wall_s:.1f}s] COMPLETE! Emitted {final_tif.name} (sha256={sha_full[:16]}..., dots={chosen_audit['dots']}), "
        f"verdict={verdict}, peak_rss={rss_mb():.0f} MB",
        flush=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=("holdout", "prod", "all"), default="all")
    args = ap.parse_args()
    t0 = time.time()
    bundle = None
    if args.stage in ("holdout", "all"):
        bundle = run_holdout_stage(t0)
    if args.stage in ("prod", "all"):
        run_prod_stage(t0, bundle)


if __name__ == "__main__":
    main()
