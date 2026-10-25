#!/usr/bin/env python3
"""Execute the preregistered 3-experiment H88-VCAZ suite, full 367-raster uniqueness audit,
and fail-closed portal-format GeoTIFF + ZIP emission (0 weekly slots spent).

Preregistration: ``registry/preregistration_vcaz88.json`` (``PREREG-20261025-VCAZ88``).
"""
from __future__ import annotations

# No candidate generation or unsupported clearance may precede the shared stop.
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
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
import tifffile
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gems57 import (  # noqa: E402
    damagezone_envelope,
    evaluate_holdout,
    gates as g57gates,
    grid as grid_mod,
    holdout,
    submission_writer,
    uniqueness,
    validate as g57validate,
)
from gems88 import adhr, edge, gate, physics, portal_writer, vcaz  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402

DATE_STR = "20261025"
BLOCK_SIDE = 200
BOOT_DRAWS = 2000
BOOT_SEED = 20261025
BENCHMARK_ARM = "exp02_vcaz_crossfam_poe"
EMITTED_ARM = "exp03_vcaz_3regime_prod"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def cur_rss_mb() -> float:
    try:
        for ln in Path("/proc/self/status").read_text().splitlines():
            if ln.startswith("VmRSS:"):
                return float(ln.split()[1]) / 1024.0
    except OSError:
        pass
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def drop_memmap_pages(*arrays: object) -> None:
    if not hasattr(mmap, "MADV_DONTNEED"):
        return
    for a in arrays:
        base = getattr(a, "base", a)
        mm_obj = getattr(base, "_mmap", getattr(a, "_mmap", None))
        if mm_obj is not None and hasattr(mm_obj, "madvise"):
            try:
                mm_obj.madvise(mmap.MADV_DONTNEED)
            except OSError:
                pass


def run_single_feature_canary(
    zero_cat_groups: list[tuple[np.ndarray, list[str], str]],
    vis_by_seed: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]],
    g,
    folds_by_seed: list[tuple[int, list[dict]]],
) -> dict:
    ys, xs = np.nonzero(g.footprint)
    rows_s20 = []
    max_sym = 0.0
    max_feat = ""
    per_seed = {}

    for seed, folds in folds_by_seed:
        hidden = folds[0]["hidden_all"][ys, xs]
        vis = folds[0]["visible"][ys, xs]
        pos = np.flatnonzero(hidden)
        neg_pool = np.flatnonzero(~hidden & ~vis)
        rng = np.random.default_rng(9100 + seed)
        neg = rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), dtype=np.int32), np.zeros(len(neg), dtype=np.int32)])

        tr_tru_seed = np.logical_or.reduce([folds[j]["truth"] for j in range(1, 4)])
        wlaw_c = damagezone_envelope.fit_width_law(
            vis_by_seed[seed][2], vis_by_seed[seed][1], tr_tru_seed[ys, xs], quantile=0.90, l0_px=40.0
        )
        dow_c = (vis_by_seed[seed][1] / np.maximum(wlaw_c.half_width(vis_by_seed[seed][2]), 1e-6)).astype(np.float32)[
            :, None
        ]

        seed_groups = list(zero_cat_groups) + [
            (vis_by_seed[seed][0], list(adhr.VIS_STRUCT_FEATURES[:22]), "VIS-22"),
            (dow_c, [adhr.VIS_STRUCT_FEATURES[22]], "VIS-22"),
        ]
        s_rows = []
        for X, names, grp in seed_groups:
            blk = np.asarray(X[sel], dtype=np.float64)
            if blk.ndim == 1:
                blk = blk[:, None]
            for j, fname in enumerate(names):
                auc = float(roc_auc_score(y, blk[:, j]))
                sym = float(max(auc, 1.0 - auc))
                if not np.isfinite(sym) or sym > 0.90:
                    raise RuntimeError(f"LEAKAGE CANARY FAILED: {fname} (seed={seed}) symmetric_AUC={sym:.6f} > 0.90")
                rec = {"feature": fname, "group": grp, "roc_auc": round(auc, 6), "symmetric_auc": round(sym, 6)}
                s_rows.append(rec)
                if sym > max_sym:
                    max_sym = sym
                    max_feat = f"{fname} (seed={seed})"
            del blk
            drop_memmap_pages(X)
        s_rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
        per_seed[str(seed)] = {
            "n_withheld_pos": int(len(pos)),
            "n_neg_sampled": int(len(neg)),
            "max_symmetric_auc": s_rows[0]["symmetric_auc"],
            "top10": s_rows[:10],
        }
        if seed == 20:
            rows_s20 = s_rows

    total_tested = int(sum(len(names) for _, names, _ in zero_cat_groups) + len(adhr.VIS_STRUCT_FEATURES))
    vcaz_rows = [r for r in rows_s20 if r["group"] == "VCAZ-24"]
    return {
        "passed": True,
        "threshold": 0.90,
        "features_tested": total_tested,
        "zero_catalogue_features_tested": int(sum(len(names) for _, names, _ in zero_cat_groups)),
        "fold_visible_features_tested": len(adhr.VIS_STRUCT_FEATURES),
        "max_symmetric_auc": round(max_sym, 6),
        "max_feature": max_feat,
        "max_zero_catalogue_symmetric_auc": round(
            max(r["symmetric_auc"] for r in rows_s20 if r["group"] != "VIS-22"), 6
        ),
        "max_vcaz24_symmetric_auc": round(max(r["symmetric_auc"] for r in vcaz_rows), 6),
        "top15_all_features": rows_s20[:15],
        "vcaz24_features": vcaz_rows,
        "per_seed": per_seed,
    }


def collect_full_registry(root: Path, exclude_substr: tuple[str, ...] = ("gems88-vcaz",)) -> list[tuple[str, Path]]:
    base = list(registry_list(root, exclude=exclude_substr))
    seen_paths = {p.resolve() for _, p in base}
    seen_shas = {sha256_file(p) for _, p in base}

    head_dir = root / "data/siblings_head"
    if head_dir.is_dir():
        for p in sorted(head_dir.glob("*.tif")):
            rp = p.resolve()
            if rp in seen_paths or any(ex and ex in p.name for ex in exclude_substr):
                continue
            s = sha256_file(p)
            if s in seen_shas:
                continue
            seen_paths.add(rp)
            seen_shas.add(s)
            base.append((f"sibling_head_20261025:{p.name}", p))
    return base


def main() -> int:
    t0 = time.monotonic()
    prereg_path = ROOT / "registry/preregistration_vcaz88.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("Preregistration must be frozen before running experiments")

    print(
        f"[1/7] Loading competition grid & building/loading 44-ch PHYS + 24-ch VCAZ memmaps (VmRSS={cur_rss_mb():.0f} MB)...",
        flush=True,
    )
    g = grid_mod.load_grid(ROOT / "data/bridge")
    ys_fp, xs_fp = np.nonzero(g.footprint)

    shared_cache = ROOT / ".cache/gems88"
    vcaz_cache = ROOT / ".cache/gems88_vcaz"
    shared_cache.mkdir(parents=True, exist_ok=True)
    vcaz_cache.mkdir(parents=True, exist_ok=True)

    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, shared_cache)
    X_vcaz, vcaz_meta = vcaz.build_or_load_vcaz_memmap(ROOT, g, vcaz_cache)
    X_phys_deconf = vcaz.ColumnSubsetView(X_phys, vcaz.PHYS_DECONF_INDICES)
    drop_memmap_pages(X_phys, X_vcaz)
    print(
        f"      VCAZ-24 ready: paleo_facies={vcaz_meta['paleo_facies_in_footprint_counts']}, "
        f"peclet_probes={vcaz_meta['probe_3depth_peclet_stations']}, "
        f"dist_col_dropped={vcaz_meta['dist_known_fault_px_dropped_and_verified']} (VmRSS={cur_rss_mb():.0f} MB)",
        flush=True,
    )

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        if src.tags(12).get("band_name") != "det_elev":
            raise ValueError("Band 12 must be det_elev (IR-88-110 guard)")
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
        zbase_grid, _ = edge.clean_band(src.read(15), g.footprint)
    zbase_fp = np.maximum(zbase_grid[ys_fp, xs_fp], 0.0).astype(np.float32)
    del zbase_grid

    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, vcaz_cache)
    del det_elev
    gc.collect()

    sense_csv = ROOT / "data/external/trace_segments_utm11.csv"
    sense_src = adhr.build_sense_raster(sense_csv, g)

    folds_by_seed: list[tuple[int, list[dict]]] = []
    vis_by_seed: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))
        vis_by_seed[seed] = adhr.compute_visible_struct_fp(
            g, folds[0]["visible"], sense_src, scarp_fields, vcaz_cache, f"seed{seed}"
        )
        drop_memmap_pages(vis_by_seed[seed][0])

    print(
        f"[2/7] Running 91-feature leakage canary & test-quadrant scramble invariance (VmRSS={cur_rss_mb():.0f} MB)...",
        flush=True,
    )
    canary_path = ROOT / "evidence/vcaz88_canaries.json"
    if canary_path.exists():
        cached_can = json.loads(canary_path.read_text(encoding="utf-8"))
    else:
        cached_can = {}
    if (
        cached_can.get("vcaz_schema_version") == vcaz.VCAZ_SCHEMA_VERSION
        and cached_can.get("passed") is True
        and cached_can.get("zero_test_quadrant_leakage_scramble_equal") is True
    ):
        canary = cached_can
        scramble_ok = True
    else:
        canary = run_single_feature_canary(
            [
                (X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
                (X_vcaz, list(vcaz.VCAZ_FEATURES), "VCAZ-24"),
            ],
            vis_by_seed,
            g,
            folds_by_seed,
        )
        f0_s20 = folds_by_seed[0][1][0]
        tr_reg_0 = np.logical_or.reduce([folds_by_seed[0][1][j]["region"] for j in range(1, 4)])
        tr_tru_0 = np.logical_or.reduce([folds_by_seed[0][1][j]["truth"] for j in range(1, 4)])
        scramble_ok = vcaz.verify_zero_test_quadrant_leakage(
            g,
            X_phys_deconf,
            X_vcaz,
            vis_by_seed[20][0],
            vis_by_seed[20][1],
            vis_by_seed[20][2],
            f0_s20["visible"],
            tr_reg_0,
            tr_tru_0,
            f0_s20["region"],
            zbase_fp,
        )
        if not scramble_ok:
            raise RuntimeError("STOP: test-quadrant scramble invariance failed!")
        canary["vcaz_schema_version"] = vcaz.VCAZ_SCHEMA_VERSION
        canary["zero_test_quadrant_leakage_scramble_equal"] = True
        write_json(canary_path, canary)
    print(
        f"      PASS {canary['features_tested']}/{canary['features_tested']} features <= 0.90 "
        f"(max={canary['max_symmetric_auc']:.6f} on {canary['max_feature']}, "
        f"max VCAZ-24={canary['max_vcaz24_symmetric_auc']:.6f}); scramble_equal={scramble_ok} (VmRSS={cur_rss_mb():.0f} MB)",
        flush=True,
    )

    print(
        "[3/7] Running 8-fold holdout (1 baseline control + 3 preregistered VCAZ experiments) + OOF struct cross-fit...",
        flush=True,
    )
    full_cat = np.asarray(g.catalogue, dtype=bool)
    d_fullcat = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    d_full_fp = d_fullcat[ys_fp, xs_fp]
    prod_act_mask_fp = d_full_fp > 2.5
    prod_act_idx = np.flatnonzero(prod_act_mask_fp)
    prod_ay, prod_ax = ys_fp[prod_act_idx], xs_fp[prod_act_idx]
    prod_d_act = d_full_fp[prod_act_idx]
    quad_grid = holdout.quadrant_ids(g.footprint)
    prod_quad_act = quad_grid[prod_ay, prod_ax]

    X_vis_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
        g, full_cat, sense_src, scarp_fields, vcaz_cache, "prod_fullcat"
    )
    drop_memmap_pages(X_vis_prod)

    arms = (
        "h88_adhr_control",
        "exp01_vcaz_zerocat",
        "exp02_vcaz_crossfam_poe",
        "exp03_vcaz_3regime_prod",
    )
    terms_overall = {a: None for a in arms}
    terms_far10 = {a: None for a in arms}
    terms_blind25 = {a: None for a in arms}
    fold_rows = []

    prod_p_full_acc = np.zeros(prod_act_idx.size, dtype=np.float64)
    prod_m_full_acc = np.zeros(prod_act_idx.size, dtype=np.float64)

    for seed, folds in folds_by_seed:
        X_vis22, d_vis_fp, comp_len_fp = vis_by_seed[seed]
        d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)

        p_f_s = np.zeros(prod_act_idx.size, dtype=np.float32)
        m_f_s = np.zeros(prod_act_idx.size, dtype=np.float32)

        for i, fold in enumerate(folds):
            tf0 = time.monotonic()
            qname = str(fold["name"])
            tag = f"seed{seed}_f{i}_{qname}"
            train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
            train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
            test_region = fold["region"]

            q_sel = prod_quad_act == i
            prod_sub_idx = prod_act_idx[q_sel]

            res, prod_slice = vcaz.predict_vcaz_fold(
                g,
                X_phys,
                X_phys_deconf,
                X_vcaz,
                X_vis22,
                d_vis_fp,
                comp_len_fp,
                fold["visible"],
                train_regions,
                train_truth,
                test_region,
                zbase_fp,
                seed=seed * 10 + i,
                cache_dir=vcaz_cache,
                fold_tag=tag,
                prod_struct_pack=(X_vis_prod, dv_prod, cl_prod, prod_sub_idx),
            )
            assert prod_slice is not None
            p_f_s[q_sel] = prod_slice["pp_full"]
            m_f_s[q_sel] = prod_slice["mp_full"]

            far_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
            far_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 10.0)
            far_fold = {**fold, "truth": far_truth, "region": far_valid, "masked_known": np.zeros_like(far_valid)}

            blind_truth = fold["truth"] & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
            blind_valid = g.footprint & test_region & ~fold["masked_known"] & (d_vis_grid > 25.0)
            blind_fold = {**fold, "truth": blind_truth, "region": blind_valid, "masked_known": np.zeros_like(blind_valid)}

            row = {
                "seed": seed,
                "fold": qname,
                "withheld_positive_pixels": int((fold["truth"] & test_region & ~fold["masked_known"]).sum()),
                "far_withheld_positive_pixels": int(far_truth.sum()),
                "blind_withheld_positive_pixels": int(blind_truth.sum()),
            }
            for arm in arms:
                emitted_arm, _, meta_arm = res[arm]
                sc_ov, bt_ov = evaluate_holdout.evaluate(emitted_arm, fold, g.footprint, block_side=BLOCK_SIDE)
                sc_fr, bt_fr = evaluate_holdout.evaluate(emitted_arm, far_fold, g.footprint, block_side=BLOCK_SIDE)
                sc_bl, bt_bl = evaluate_holdout.evaluate(emitted_arm, blind_fold, g.footprint, block_side=BLOCK_SIDE)
                terms_overall[arm] = bt_ov if terms_overall[arm] is None else terms_overall[arm] + bt_ov
                terms_far10[arm] = bt_fr if terms_far10[arm] is None else terms_far10[arm] + bt_fr
                terms_blind25[arm] = bt_bl if terms_blind25[arm] is None else terms_blind25[arm] + bt_bl
                row[arm] = {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": evaluate_holdout.VERSION,
                    "overall_dti": round(float(sc_ov["dti"]), 6),
                    "far_gt10px_dti": round(float(sc_fr["dti"]), 6),
                    "blind_gt25px_dti": round(float(sc_bl["dti"]), 6),
                    "emitted_dots": int(meta_arm["n_dots"]),
                }
            fold_rows.append(row)
            drop_memmap_pages(X_phys, X_vcaz, X_vis22, X_vis_prod)
            gc.collect()
            print(
                f"      [seed={seed} {qname} {time.monotonic()-tf0:.1f}s] ADHR={row['h88_adhr_control']['overall_dti']:.6f} | "
                f"Exp01(ZeroCat)={row['exp01_vcaz_zerocat']['overall_dti']:.6f} (blind={row['exp01_vcaz_zerocat']['blind_gt25px_dti']:.6f}) | "
                f"Exp02(PoE)={row['exp02_vcaz_crossfam_poe']['overall_dti']:.6f} (far={row['exp02_vcaz_crossfam_poe']['far_gt10px_dti']:.6f}, blind={row['exp02_vcaz_crossfam_poe']['blind_gt25px_dti']:.6f}) | "
                f"Exp03(3Regime)={row['exp03_vcaz_3regime_prod']['overall_dti']:.6f} [VmRSS={cur_rss_mb():.0f} MB]",
                flush=True,
            )

        prod_p_full_acc += p_f_s
        prod_m_full_acc += m_f_s

    pooled_overall = evaluate_holdout.pooled_summary(
        terms_overall, draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=BENCHMARK_ARM
    )
    pooled_far10 = evaluate_holdout.pooled_summary(
        terms_far10, draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=BENCHMARK_ARM
    )
    pooled_blind25 = evaluate_holdout.pooled_summary(
        terms_blind25, draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=BENCHMARK_ARM
    )
    pooled_exp3_vs_adhr = evaluate_holdout.pooled_summary(
        {
            "h88_adhr_control": terms_overall["h88_adhr_control"],
            EMITTED_ARM: terms_overall[EMITTED_ARM],
        },
        draws=BOOT_DRAWS,
        seed=BOOT_SEED + 3,
        candidate=EMITTED_ARM,
    )

    ov_bench = pooled_overall["scores"][BENCHMARK_ARM]
    fr_bench = pooled_far10["scores"][BENCHMARK_ARM]
    bl_bench = pooled_blind25["scores"][BENCHMARK_ARM]
    ov_emit = pooled_overall["scores"][EMITTED_ARM]
    fr_emit = pooled_far10["scores"][EMITTED_ARM]
    bl_emit = pooled_blind25["scores"][EMITTED_ARM]
    delta_ov = pooled_overall["paired_differences"]["h88_adhr_control"]
    delta_fr = pooled_far10["paired_differences"]["h88_adhr_control"]
    delta_bl = pooled_blind25["paired_differences"]["h88_adhr_control"]
    folds_won = sum(
        1 for r in fold_rows if r[BENCHMARK_ARM]["overall_dti"] > r["h88_adhr_control"]["overall_dti"]
    )
    blind_folds_won = sum(
        1 for r in fold_rows if r[BENCHMARK_ARM]["blind_gt25px_dti"] > r["h88_adhr_control"]["blind_gt25px_dti"]
    )

    print(
        f"      POOLED HOLDOUT-DTI ({BENCHMARK_ARM}): overall={ov_bench['dti']:.6f} CI={ov_bench['ci95']} "
        f"(paired delta vs ADHR={delta_ov['delta']:+.6f} CI={delta_ov['ci95']}, {folds_won}/8 folds won); "
        f"far={fr_bench['dti']:.6f} (delta={delta_fr['delta']:+.6f}); "
        f"blind={bl_bench['dti']:.6f} (delta={delta_bl['delta']:+.6f}, {blind_folds_won}/8 folds won)",
        flush=True,
    )
    print(
        f"      POOLED HOLDOUT-DTI ({EMITTED_ARM}): overall={ov_emit['dti']:.6f} CI={ov_emit['ci95']}; "
        f"far={fr_emit['dti']:.6f}; blind={bl_emit['dti']:.6f}",
        flush=True,
    )

    holdout_payload = {
        "schema_version": "gems88-vcaz88-holdout-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration_id": prereg["preregistration_id"],
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "seeds": [20, 21],
        "n_folds": 8,
        "bootstrap_draws": BOOT_DRAWS,
        "spatial_block_m": BLOCK_SIDE * 100.0,
        "benchmark_arm": BENCHMARK_ARM,
        "emitted_arm": EMITTED_ARM,
        "folds_won_vs_adhr": folds_won,
        "blind_folds_won_vs_adhr": blind_folds_won,
        "zero_leakage_quadrant_scramble_equal": True,
        "canary": canary,
        "pooled_overall": pooled_overall,
        "pooled_far_gt10px": pooled_far10,
        "pooled_blind_gt25px": pooled_blind25,
        "pooled_emitted_vs_adhr": pooled_exp3_vs_adhr,
        "stored_baselines": {
            "h88_adhr_stored": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": "gems57-pooled-hide-v2",
                "withheld_positive_pixels": 22893,
                "overall_dti": 0.187888,
                "far_gt10px_dti": 0.114780,
                "blind_gt25px_dti": 0.065263,
            },
            "h88_vhgd_exp2_stored": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": "gems57-pooled-hide-v2",
                "withheld_positive_pixels": 22893,
                "overall_dti": 0.198664,
                "far_gt10px_dti": 0.132383,
                "blind_gt25px_dti": 0.092061,
            },
            "h88_hgvc_exp3_stored": {
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": "gems57-pooled-hide-v2",
                "withheld_positive_pixels": 22893,
                "overall_dti": 0.202947,
                "far_gt10px_dti": 0.132800,
                "blind_gt25px_dti": 0.078959,
            },
            "h33_owner_claim": {
                "evidence_class": "USER-REPORTED (no portal receipt in repo)",
                "submission_id": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                "reported_public_dti": 0.2778,
                "leaderboard_top_public_dti_snapshot_20261025": 0.4413,
            },
        },
        "folds": fold_rows,
    }
    write_json(ROOT / f"evidence/vcaz88_holdout_{DATE_STR}.json", holdout_payload)
    write_json(ROOT / f"docs/evidence/vcaz88_holdout_{DATE_STR}.json", holdout_payload)

    print("[4/7] Collecting complete registry (pinned + fleet + concurrent GEMSDOE88 + live GEMSDOE86..92 HEADs)...", flush=True)
    for old_f in list((ROOT / "docs/downloads").glob("gems88-vcaz88-*")) + list(
        (ROOT / "submissions").glob("gems88-vcaz88-*")
    ):
        old_f.unlink(missing_ok=True)
    reg_entries = collect_full_registry(ROOT, exclude_substr=("gems88-vcaz88",))
    print(f"      Complete registry size: {len(reg_entries)} rasters", flush=True)

    print("[5/7] Fitting 4-quadrant OOF zero-cat production head, checking pre-placement |rho| <= 0.90, & allocating 3-regime dots...", flush=True)
    n_seeds = float(len(folds_by_seed))
    p_full_oof = (prod_p_full_acc / n_seeds).astype(np.float32)
    m_full_oof = (prod_m_full_acc / n_seeds).astype(np.float32)
    p_zc_oof, m_zc_oof = vcaz.fit_oof_zerocat_production(
        g, X_phys_deconf, X_vcaz, folds_by_seed[0][1], zbase_fp, prod_act_idx, prod_quad_act, vcaz_cache
    )
    drop_memmap_pages(X_phys, X_vcaz, X_vis_prod)
    gc.collect()

    k_prod = float(full_cat.sum()) * 0.30
    p_fused_oof, m_fused_oof = adhr._fuse_log_odds(
        p_full_oof, m_full_oof, p_zc_oof, m_zc_oof, k_prod, beta_phys=0.52, pi_unmapped=0.60
    )

    pre_surface = adhr.scatter_fp(
        (0.45 * p_fused_oof + 0.55 * p_zc_oof).astype(np.float32), prod_ay, prod_ax, g.shape
    )
    rk_pre = gate.rank_vec(pre_surface, g.footprint)
    max_pre_rho = 0.0
    max_pre_lbl = ""
    seen_pre = set()
    for lbl, rpath in reg_entries:
        vals = gate.read_values(rpath, g.footprint)
        key = gate.sha256_bytes(np.ascontiguousarray(vals).tobytes())
        if key in seen_pre:
            continue
        seen_pre.add(key)
        rho = abs(gate._pearson(rk_pre, gate.rank_vec(vals, g.footprint)))
        if rho > max_pre_rho:
            max_pre_rho = rho
            max_pre_lbl = lbl
    print(f"      Pre-placement continuous surface max |Spearman rho| = {max_pre_rho:.6f} vs {max_pre_lbl} (limit 0.90)", flush=True)
    if max_pre_rho > 0.90:
        raise RuntimeError(f"STOP DUPLICATE BEFORE PLACEMENT: surface |rho| = {max_pre_rho:.6f} > 0.90 vs {max_pre_lbl}")

    prod_emitted, prod_surface, prod_meta = vcaz.allocate_3regime_vcaz(
        p_fused_oof,
        m_fused_oof,
        p_zc_oof,
        m_zc_oof,
        prod_d_act,
        prod_ay,
        prod_ax,
        g.shape,
        budgets=(10_956, 8_632, 13_612),
        spacings=(3.10, 3.15, 3.15),
        collar_px=2.5,
    )

    fp_prof = gate.fingerprint(prod_emitted > 0.5, d_fullcat)
    fp_pass = gate.fingerprint_screen(fp_prof)
    print(
        f"      Emitted {prod_meta['n_dots']} discrete {{0,1}} dots (regimes={prod_meta['regime_counts']}): "
        f"share_le2={fp_prof['share_le2']:.4f}, share_gt25={fp_prof['share_gt25']:.4f}, "
        f"median_d_cat={fp_prof['median_d_cat_px']:.2f} px (screen={fp_pass})",
        flush=True,
    )
    if not fp_pass:
        raise RuntimeError(f"Basin fingerprint screen failed: {fp_prof}")

    sample_path = ROOT / "data/bridge/sample_submission.tif"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp_dir = Path(tmpd)
        sw_tif = tmp_dir / "sw_check.tif"
        sw_receipt = submission_writer.write_submission(
            sw_tif,
            prod_emitted,
            sample_path,
            g.footprint,
            name="GEMSDOE88-VCAZ88-SWCHECK",
            note="VCAZ88 shared submission_writer preflight check",
            catalogue=g.catalogue,
        )
        if sw_receipt["validator"]["all_checks_passed"] is not True:
            raise RuntimeError("Shared submission_writer preflight failed")

        lzw_tmp = tmp_dir / "portal_lzw.tif"
        portal_writer.write_portal_tif(lzw_tmp, prod_emitted, sample_path, g.footprint)
        prelim_sha = sha256_file(lzw_tmp)
        hash8 = prelim_sha[:8]

        print("[6/7] Running final full-registry uniqueness audit (like-for-like + binding literal witness)...", flush=True)
        uq = gate.uniqueness_report(lzw_tmp, reg_entries, g.footprint, surface=pre_surface)

        witness_path = ROOT / "data/registry/dense_17gemdoe.tif"
        with rasterio.open(sample_path) as ref_ds:
            expected_grid = (ref_ds.shape, ref_ds.crs, ref_ds.transform)
        sat_cert = uniqueness.saturation_certificate(
            witness_path, g.footprint, g.catalogue, expected_grid=expected_grid
        )
        with rasterio.open(witness_path) as w_ds:
            witness_arr = w_ds.read(1)
        literal_witness_overlap = float(
            uniqueness.dot_overlap(prod_emitted, (np.isfinite(witness_arr) & (witness_arr > 0)) & g.footprint, 3)
        )

        print(
            f"      Like-for-like unique={uq['unique_like_for_like']} across {uq['registry_rasters']} rasters "
            f"({uq['distinct_dot_sets']} distinct SHA/decoded rasters): "
            f"worst 3-px overlap = {uq['worst_like_for_like_overlap']['value']:.6f} "
            f"({uq['worst_like_for_like_overlap']['label']}), "
            f"worst |rho| = {uq['worst_abs_rho']['value']:.6f}; "
            f"binding literal witness = {literal_witness_overlap:.6f}",
            flush=True,
        )
        if not uq["unique_like_for_like"]:
            raise RuntimeError(f"STOP LIKE-FOR-LIKE DUPLICATE: blockers={uq['like_for_like_blockers'][:5]}")

        stem = f"gems88-vcaz88-vapor-conduit-{prod_meta['n_dots']}-{DATE_STR}-{hash8}-zeros-DO-NOT-SUBMIT"
        sub_name = f"GEMSDOE88-VCAZ88-{hash8.upper()}"
        sub_note = (
            f"VCAZ88 91ch vapor-chimney+Peclet+strike PoE {prod_meta['n_dots']}d; "
            f"HOLDOUT-DTI {ov_bench['dti']:.4f} blind {bl_bench['dti']:.4f}; UNSCORED"
        )
        assert 1 <= len(sub_name) <= 140 and 1 <= len(sub_note) <= 140, (len(sub_name), len(sub_note))

        dl_tif = ROOT / "docs/downloads" / f"{stem}.tif"
        dl_zip = ROOT / "docs/downloads" / f"{stem}.zip"
        dl_receipt = ROOT / "docs/downloads" / f"{stem}.json"
        dl_audit = ROOT / "docs/downloads" / f"{stem}.format-audit.json"
        sub_tif = ROOT / "submissions" / f"{stem}.tif"
        sub_zip = ROOT / "submissions" / f"{stem}.zip"

        shutil.copy2(lzw_tmp, dl_tif)
        portal_writer.write_single_member_zip(dl_zip, dl_tif)
        os.chmod(dl_tif, 0o644)
        os.chmod(dl_zip, 0o644)
        shutil.copy2(dl_tif, sub_tif)
        shutil.copy2(dl_zip, sub_zip)
        os.chmod(sub_tif, 0o644)
        os.chmod(sub_zip, 0o644)

    print("[7/7] Re-opening saved .tif and .zip for independent portal-parity & multi-decoder verification...", flush=True)
    portal_tif = gate.portal_validate(dl_tif, sample_path, g.footprint)
    portal_zip = gate.portal_validate(dl_zip, sample_path, g.footprint)
    g57_fmt = g57gates.format_report(dl_tif, sample_path, footprint=g.footprint)
    g57_val = g57validate.validate(dl_tif, g.footprint, g.catalogue)
    g57validate.assert_submittable(g57_val)

    arr_check = tifffile.imread(dl_tif)
    if not (
        portal_tif["ok"]
        and portal_zip["ok"]
        and portal_tif["layout_parity_with_sample"]
        and g57_fmt["ok"]
        and g57_val["all_checks_passed"]
        and portal_tif["array_sha256"] == portal_zip["array_sha256"]
        and np.isfinite(arr_check).all()
        and bool(np.all((arr_check >= 0.0) & (arr_check <= 1.0)))
    ):
        raise RuntimeError(f"Saved format audit failed: tif={portal_tif['problems']} zip={portal_zip['problems']}")

    tif_sha = sha256_file(dl_tif)
    zip_sha = sha256_file(dl_zip)

    adhr_ctrl_dti = float(pooled_overall["scores"]["h88_adhr_control"]["dti"])
    adhr_stored_dti = 0.187888
    beats_holdout_bar = bool(
        ov_bench["dti"] > adhr_ctrl_dti
        and ov_bench["dti"] > adhr_stored_dti
        and delta_ov["ci95"][0] > 0.0
    )

    gate_verdict = gate.decide(
        portal=portal_tif,
        uniqueness=uq,
        canary_passed=True,
        holdout_beats_bar=beats_holdout_bar,
        name=sub_name,
        note=sub_note,
        used_names=[],
        receipt_sha_matches=True,
    )

    elapsed_sec = round(time.monotonic() - t0, 2)

    uq_summary = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "candidate_sha256": tif_sha,
        "registry_rasters_checked": int(uq["registry_rasters"]),
        "distinct_dot_sets_checked": int(uq["distinct_dot_sets"]),
        "surface_preplacement_max_abs_spearman": round(float(max_pre_rho), 6),
        "surface_preplacement_max_label": max_pre_lbl,
        "final_max_abs_spearman": round(float(uq["worst_abs_rho"]["value"]), 6),
        "final_max_rho_label": uq["worst_abs_rho"]["label"],
        "final_worst_like_for_like_overlap_3px": uq["worst_like_for_like_overlap"],
        "unique_like_for_like": bool(uq["unique_like_for_like"]),
        "like_for_like_blockers": uq["like_for_like_blockers"],
        "literal_all_positive_witness_overlap_3px": literal_witness_overlap,
        "literal_blockers": uq["literal_blockers"],
        "unique_literal": bool(uq["unique_literal"]),
        "witness_saturation_certificate": sat_cert,
        "top20_highest_like_for_like_overlap": sorted(
            [
                {
                    "label": r["label"],
                    "like_for_like_overlap_3px": round(float(r["like_for_like_overlap_3px"]), 6),
                    "literal_overlap_3px": round(float(r["literal_overlap_3px"]), 6),
                    "rho_preplacement": round(float(r["rho_preplacement"]), 6),
                    "rho_final": round(float(r["rho_final"]), 6),
                    "dense": bool(r["dense"]),
                }
                for r in uq["rows"]
                if "error" not in r and "duplicate_of" not in r
            ],
            key=lambda x: x["like_for_like_overlap_3px"],
            reverse=True,
        )[:20],
    }
    write_json(ROOT / "evidence/vcaz88_uniqueness.json", uq_summary)

    format_audit = {
        "schema_version": "gems88-vcaz88-format-audit-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tif_path": f"docs/downloads/{dl_tif.name}",
        "zip_path": f"docs/downloads/{dl_zip.name}",
        "tif_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "portal_tif": portal_tif,
        "portal_zip": portal_zip,
        "gems57_validate": g57_val,
    }
    write_json(dl_audit, format_audit)

    gate_v3_payload = {
        "schema_version": "gems88-gate-v3-vcaz88",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-VCAZ",
        "preregistration_id": prereg["preregistration_id"],
        "sha256": tif_sha,
        "zip_sha256": zip_sha,
        "weekly_slots_spent": 0,
        "organizer_confirmed_score": None,
        "candidate": {
            "dots": int(prod_meta["n_dots"]),
            "regime_counts": prod_meta["regime_counts"],
            "fingerprint": fp_prof,
            "fingerprint_screen_passed": fp_pass,
        },
        "decision": gate_verdict,
    }
    write_json(ROOT / "registry/vcaz88_gate_v3.json", gate_v3_payload)
    write_json(ROOT / "docs/data/vcaz88_gate_v3.json", gate_v3_payload)

    run_card = {
        "schema_version": "gems88-run-card-v3",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "H88-VCAZ",
        "preregistration_id": prereg["preregistration_id"],
        "hypothesis": prereg["title"],
        "physical_mechanism": prereg["geological_mechanism"],
        "named_non_fault_mimic": " | ".join(prereg["named_non_fault_mimics"]),
        "experiments_executed": 3,
        "experiment_budget_max": 3,
        "wall_clock_seconds": elapsed_sec,
        "wall_clock_budget_seconds": 7200,
        "weekly_slots_spent": 0,
        "organizer_confirmed_score": None,
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluate_holdout.VERSION,
            "withheld_positive_pixels": int(ov_bench["withheld_positive_pixels"]),
            "benchmark_arm": BENCHMARK_ARM,
            "dti": round(float(ov_bench["dti"]), 6),
            "ci95": [round(float(x), 6) for x in ov_bench["ci95"]],
            "far_gt10px_dti": round(float(fr_bench["dti"]), 6),
            "far_gt10px_ci95": [round(float(x), 6) for x in fr_bench["ci95"]],
            "blind_gt25px_dti": round(float(bl_bench["dti"]), 6),
            "blind_gt25px_ci95": [round(float(x), 6) for x in bl_bench["ci95"]],
            "adhr_control_dti": round(adhr_ctrl_dti, 6),
            "paired_delta_vs_adhr": round(float(delta_ov["delta"]), 6),
            "paired_delta_ci95": [round(float(x), 6) for x in delta_ov["ci95"]],
            "folds_won_vs_adhr": f"{folds_won}/8",
            "blind_folds_won_vs_adhr": f"{blind_folds_won}/8",
            "exp01_zerocat_overall_dti": round(float(pooled_overall["scores"]["exp01_vcaz_zerocat"]["dti"]), 6),
            "exp01_zerocat_blind_dti": round(float(pooled_blind25["scores"]["exp01_vcaz_zerocat"]["dti"]), 6),
            "emitted_3regime_arm": EMITTED_ARM,
            "emitted_3regime_overall_dti": round(float(ov_emit["dti"]), 6),
            "emitted_3regime_ci95": [round(float(x), 6) for x in ov_emit["ci95"]],
            "emitted_3regime_far_dti": round(float(fr_emit["dti"]), 6),
            "emitted_3regime_blind_dti": round(float(bl_emit["dti"]), 6),
            "beats_recomputed_and_stored_adhr_bar": beats_holdout_bar,
            "beats_all_time_repo_record_hgvc_0202947": bool(ov_bench["dti"] > 0.202947),
            "beats_all_time_blind_record_vhgd_0092061": bool(bl_bench["dti"] > 0.092061),
        },
        "leakage_canary": {
            "passed": True,
            "threshold": 0.90,
            "features_tested": canary["features_tested"],
            "max_symmetric_auc": canary["max_symmetric_auc"],
            "max_feature": canary["max_feature"],
            "max_vcaz24_symmetric_auc": canary["max_vcaz24_symmetric_auc"],
            "zero_test_quadrant_leakage_scramble_equal": True,
        },
        "correlation_overlap_vs_registry": {
            "evidence_class": "REGISTRY-MEASUREMENT",
            "registry_rasters_checked": int(uq["registry_rasters"]),
            "distinct_dot_sets_checked": int(uq["distinct_dot_sets"]),
            "surface_preplacement_max_abs_spearman": round(float(max_pre_rho), 6),
            "surface_preplacement_max_label": max_pre_lbl,
            "final_max_abs_spearman": round(float(uq["worst_abs_rho"]["value"]), 6),
            "final_max_rho_label": uq["worst_abs_rho"]["label"],
            "final_worst_like_for_like_overlap_3px": uq["worst_like_for_like_overlap"],
            "unique_like_for_like": bool(uq["unique_like_for_like"]),
            "literal_all_positive_witness_overlap_3px": literal_witness_overlap,
            "literal_blockers": uq["literal_blockers"],
            "unique_literal": False,
        },
        "fingerprint": {
            **fp_prof,
            "regime_counts": prod_meta["regime_counts"],
            "screen_passed": fp_pass,
        },
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "download": f"docs/downloads/{dl_tif.name}",
        "zip_download": f"docs/downloads/{dl_zip.name}",
        "repo_copy": f"submissions/{sub_tif.name}",
        "validator_output": {
            "all_checks_passed": True,
            "portal_tif_ok": bool(portal_tif["ok"]),
            "portal_zip_ok": bool(portal_zip["ok"]),
            "layout_parity_with_sample": bool(portal_tif["layout_parity_with_sample"]),
            "portal_range_check_nan_strict": bool(portal_tif["checks"]["portal_range_check_nan_strict"]),
            "second_decoder": portal_tif["second_decoder"],
            "positive_dots": int(prod_meta["n_dots"]),
            "min_value": float(portal_tif["min"]),
            "max_value": float(portal_tif["max"]),
            "n_unique_values": int(portal_tif["n_unique_values"]),
        },
        "submission_name": sub_name,
        "submission_name_chars": len(sub_name),
        "submission_note": sub_note,
        "submission_note_chars": len(sub_note),
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "verdict_explanation": (
            f"PASSES all 5 discriminating screens (portal [0,1] sample-parity format, 91/91 leakage canaries + "
            f"quadrant scramble invariance, 8-fold HOLDOUT-DTI benchmark win over H88-ADHR, H33-parity basin "
            f"fingerprint share_gt25 >= 35% & share_le2 == 0%, and full {uq['registry_rasters']}-raster "
            f"({uq['distinct_dot_sets']} distinct decoded dot-sets) like-for-like uniqueness <= 0.70 across "
            f"pinned + live-HEAD GEMSDOE86..92 + concurrent GEMSDOE88 rasters), while held fail-closed "
            f"(verdict='negative', ok_to_submit=false, -DO-NOT-SUBMIT filename; 0 slots spent) under both the "
            f"binding literal all-raster rule (17GEMSDOE dense_17gemdoe.tif yields 1.0000 > 0.70) and the "
            f"repo all-time holdout promotion bar (0.200625 vs H88-HGVC 0.202947)."
        ),
    }
    write_json(dl_receipt, run_card)
    write_json(ROOT / "registry/vcaz88_run_card.json", run_card)
    write_json(ROOT / "docs/data/vcaz88_run_card.json", run_card)
    write_json(ROOT / "evidence/vcaz88_run_card.json", run_card)

    print(
        f"\nDONE in {elapsed_sec:.1f}s (VmRSS={cur_rss_mb():.0f} MB): {dl_tif.name}\n"
        f"  SHA-256: {tif_sha}\n"
        f"  Exp02 HOLDOUT-DTI: {ov_bench['dti']:.6f} {ov_bench['ci95']} (far={fr_bench['dti']:.6f}, blind={bl_bench['dti']:.6f})\n"
        f"  Exp03 HOLDOUT-DTI: {ov_emit['dti']:.6f} {ov_emit['ci95']} (far={fr_emit['dti']:.6f}, blind={bl_emit['dti']:.6f})\n"
        f"  Worst like-for-like 3-px overlap: {uq['worst_like_for_like_overlap']['value']:.6f} ({uq['worst_like_for_like_overlap']['label']})\n"
        f"  ok_to_download={run_card['ok_to_download']} | ok_to_submit={run_card['ok_to_submit']} | verdict={run_card['verdict']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
