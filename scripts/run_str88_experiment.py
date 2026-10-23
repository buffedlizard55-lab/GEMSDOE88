#!/usr/bin/env python3
"""Execute Preregistered Experiment 3 of 3 (STR-88) on identical LOQO folds.

Compares STR-88 (18-channel zero-catalogue multi-physics Hessian crest + spin-2
axial strike consensus + exact-shell 300 m Dinkelbach allocation) against:
  - STR-88 + 2-px greedy NMS ablation (`str88_spaced`)
  - Experiment 1 incumbent MGC-88 (`mgc88_incumbent`)
  - Experiment 1 raw 3-band control (`raw_control`)

Generates a brand-new competition-format GeoTIFF via `submission_writer.py`,
checks both pre-placement surface and final-dot uniqueness across all 6 pinned
registry rasters (H33, GEMSDOE36, GEMSDOE70, GEMSDOE73, MGC-88, and 17GEMSDOE
dense_prior), archives MGC-88 canonical receipts, and updates canonical receipts
if STR-88 improves over MGC-88 with strictly positive paired 20 km block-bootstrap
95% CI. Preserves fail-closed DO-NOT-SUBMIT status under IR-88-01.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]

from gems57 import evaluate_holdout, grid, holdout, submission_writer, uniqueness  # noqa: E402
from gems88 import edge, model, str88  # noqa: E402
from readiness import verify_template  # noqa: E402
from restore_inputs import digest  # noqa: E402

DATA = ROOT / "data"
REGISTRY = ROOT / "registry"
DOCS = ROOT / "docs"
PREREG = REGISTRY / "preregistration_str88.json"
ARTIFACT_NAME = "gems88-str88-multiphysics-submod-37654-20261023-v1-DO-NOT-SUBMIT"
NOTE = (
    "GEMSDOE88 STR-88 zero-catalogue 18ch Hessian+spin2 HGB + 300m Dinkelbach "
    "37654 dots; research-only DO-NOT-SUBMIT"
)
BUDGET = 37_654
MIN_SPACING_PX = 2.85
SEEDS = (20, 21)
MGC_TIF_REL = "docs/downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif"


def dump(path: Path, content: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, allow_nan=False, sort_keys=True) + "\n")


def bbox(region: np.ndarray, pad: int = 4) -> tuple[slice, slice]:
    row, col = np.nonzero(region)
    if not row.size:
        raise ValueError("empty fold region")
    return (
        slice(max(int(row.min()) - pad, 0), min(int(row.max()) + pad + 1, region.shape[0])),
        slice(max(int(col.min()) - pad, 0), min(int(col.max()) + pad + 1, region.shape[1])),
    )


def flat_feature_tie(x: np.ndarray, sl: tuple[slice, slice], width: int, col: int) -> np.ndarray:
    h = sl[0].stop - sl[0].start
    w = sl[1].stop - sl[1].start
    r = np.arange(sl[0].start, sl[0].stop, dtype=np.int64)
    c = np.arange(sl[1].start, sl[1].stop, dtype=np.int64)
    return np.asarray(x[(r[:, None] * width + c[None, :]).ravel(), col]).reshape(h, w)


def checked_inputs() -> dict[str, dict[str, str]]:
    expected = {
        "training_features.tif": (
            "training_features.tif",
            "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
        ),
        "sample_submission.tif": (
            "bridge/sample_submission.tif",
            grid.SHA256_SAMPLE_SUBMISSION,
        ),
        "existing_faults.tif": (
            "bridge/existing_faults.tif",
            grid.SHA256_EXISTING_FAULTS,
        ),
        "dense witness": (
            "registry/dense_17gemdoe.tif",
            "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
        ),
        "h33 registry": (
            "registry/h33_education.tif",
            "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
        ),
        "gems36 registry": (
            "registry/gems36_anderson_pinn.tif",
            "e15891020b9c57056ac7fa874a5e506fbd6ed9314a4ea8e73af0753887a3708a",
        ),
        "gems70 registry": (
            "registry/gems70_p8_oof38k.tif",
            "d0e41ce921afcf3af33b7d86d75f6a258653dfbb4d050e864babe643245f0ea8",
        ),
        "gems73 registry": (
            "registry/gems73_mcsc_blakely.tif",
            "fab28aa25f7f803907c91d0e64cbfe2755f9bc1702163f458bbb1017174a0249",
        ),
    }
    for name, (rel_path, sha) in expected.items():
        if digest(DATA / rel_path) != sha:
            raise ValueError(f"{name} SHA256 mismatch on {rel_path}")
    return {k: dict(file=v[0], sha256=v[1]) for k, v in expected.items()}


def archive_mgc88_receipts() -> None:
    pairs = [
        ("run_card.json", "mgc88_run_card.json"),
        ("holdout_result.json", "mgc88_holdout_result.json"),
        ("leakage_canaries.json", "mgc88_leakage_canaries.json"),
        ("preplacement_registry.json", "mgc88_preplacement_registry.json"),
        ("final_registry.json", "mgc88_final_registry.json"),
    ]
    for src_name, dst_name in pairs:
        src = REGISTRY / src_name
        dst = REGISTRY / dst_name
        if src.is_file() and not dst.is_file():
            shutil.copy2(src, dst)


def run() -> dict:
    start = time.monotonic()
    if not PREREG.is_file():
        raise FileNotFoundError(f"Missing preregistration file: {PREREG}")
    if len(NOTE) > 140 or len(ARTIFACT_NAME) > 140:
        raise ValueError("Submission name or note exceeds 140 characters")

    verify_template(ROOT)
    input_pins = checked_inputs()
    g = grid.load_grid()
    sample = DATA / "bridge" / "sample_submission.tif"
    witness = DATA / "registry" / "dense_17gemdoe.tif"
    with rasterio.open(sample) as ref:
        expected_grid = (ref.shape, ref.crs, ref.transform)

    universal = uniqueness.saturation_certificate(
        witness, g.footprint, g.catalogue, expected_grid=expected_grid
    )

    print("[1/6] Building / loading STR-88 18-channel and MGC-88 7-channel memmaps...", flush=True)
    x_str, str_meta = str88.build_str88_cache(
        DATA / "training_features.tif", g.footprint, DATA / "cache"
    )

    mgc_cache = DATA / "cache" / "mgc88-7channel.f32"
    if not mgc_cache.is_file():
        edge.build_cache(DATA / "training_features.tif", g.footprint, mgc_cache)
    x_mgc = np.memmap(
        mgc_cache, mode="r", dtype="float32", shape=(g.height * g.width, len(edge.NAMES))
    )

    print("[2/6] Building LOQO folds (seeds=(20, 21)) & running 18 leakage canaries...", flush=True)
    folds = []
    quads = {}
    for seed in SEEDS:
        draw, quad = holdout.buffered_component_draw(
            g, seed=seed, buffer_px=3, boundary_px=12
        )
        folds.extend(draw)
        quads[seed] = quad

    canaries = model.leakage_canaries(x_str, str88.STR88_NAMES, folds, g.footprint)
    max_auc = max(r["symmetric_auc"] for r in canaries)
    print(f"      max_symmetric_auc = {max_auc:.4f} (limit <= 0.90)", flush=True)
    if max_auc > 0.90:
        raise RuntimeError(f"STR-88 leakage canary exceeded 0.90: {max_auc:.4f}")

    print("[3/6] Running 8 LOQO folds (n=22,893 withheld positives)...", flush=True)
    terms: dict[str, np.ndarray | None] = {
        "candidate": None,
        "str88_spaced": None,
        "mgc88_incumbent": None,
        "raw_control": None,
    }
    folded = []

    for f in folds:
        ft0 = time.monotonic()
        seed = f["receipt"]["seed"]
        fi = f["fold"]
        train_region = g.footprint & (quads[seed] != fi)
        sl = bbox(f["region"])
        pvalid = g.footprint[sl]
        region = f["region"][sl]
        vis_crop = f["visible"][sl]
        eligible = region & pvalid & ~vis_crop
        indices_local = np.flatnonzero(eligible.ravel())
        w_crop = sl[1].stop - sl[1].start
        rr, cc = np.divmod(indices_local, w_crop)
        global_idx = (sl[0].start + rr) * g.width + (sl[1].start + cc)
        fold_budget = max(1, round(BUDGET * int(region.sum()) / int(g.footprint.sum())))

        region_fold = {
            key: val[sl]
            for key, val in f.items()
            if key in ("region", "visible", "masked_known", "truth")
        }

        fold_record = dict(
            seed=seed,
            quadrant=f["name"],
            withheld_positive_pixels=int(f["truth"].sum()),
            feature_context_buffer_px=3,
            boundary_buffer_px=12,
            budget=fold_budget,
            arms={},
        )

        # 1) STR-88 single LOQO fit -> both Dinkelbach (primary) and Spaced (ablation)
        str_seed = model.SEED + seed * 4 + fi
        clf_str, str_fit_info = str88.fit_str88(
            x_str, g.footprint, f["visible"], train_region, seed=str_seed
        )
        p_str = np.zeros(eligible.shape, np.float32)
        p_str.ravel()[indices_local] = str88.predict_indices_str88(clf_str, x_str, global_idx)

        dots_dink, info_dink = str88.allocate_str88_dinkelbach(
            p_str, region & pvalid, vis_crop, budget=fold_budget, min_spacing_px=MIN_SPACING_PX
        )
        tie_str = flat_feature_tie(x_str, sl, g.width, col=13)
        dots_spc, info_spc = model.spaced_dots(
            p_str, eligible, fold_budget, radius=2, tie=tie_str
        )
        del clf_str, p_str

        # 2) MGC-88 incumbent & raw 3-band control (exact reproduction of run_experiment.py)
        tie_mgc = flat_feature_tie(x_mgc, sl, g.width, col=6)
        clf_mgc, mgc_fit_info = model.fit(
            x_mgc, g.footprint, f["visible"], train_region, model.JOINT, seed=str_seed
        )
        p_mgc = np.zeros(eligible.shape, np.float32)
        p_mgc.ravel()[indices_local] = model.probability(clf_mgc, x_mgc, global_idx, model.JOINT)
        dots_mgc, info_mgc = model.spaced_dots(
            p_mgc, eligible, fold_budget, radius=2, tie=tie_mgc
        )
        del clf_mgc, p_mgc

        clf_raw, raw_fit_info = model.fit(
            x_mgc, g.footprint, f["visible"], train_region, model.BASE, seed=str_seed
        )
        p_raw = np.zeros(eligible.shape, np.float32)
        p_raw.ravel()[indices_local] = model.probability(clf_raw, x_mgc, global_idx, model.BASE)
        dots_raw, info_raw = model.spaced_dots(
            p_raw, eligible, fold_budget, radius=2, tie=tie_mgc
        )
        del clf_raw, p_raw

        arm_bundles = [
            ("candidate", dots_dink, str_fit_info, info_dink),
            ("str88_spaced", dots_spc, str_fit_info, info_spc),
            ("mgc88_incumbent", dots_mgc, mgc_fit_info, info_mgc),
            ("raw_control", dots_raw, raw_fit_info, info_raw),
        ]
        for arm_name, arm_dots, f_info, e_info in arm_bundles:
            sc, by_block = evaluate_holdout.evaluate(
                arm_dots.astype(np.float32),
                region_fold,
                pvalid,
                origin=(sl[0].start, sl[1].start),
                global_shape=g.shape,
                block_side=200,
            )
            terms[arm_name] = by_block if terms[arm_name] is None else (terms[arm_name] + by_block)
            fold_record["arms"][arm_name] = dict(
                training=f_info,
                emission=e_info,
                tpw=sc["tp"],
                fpw=sc["fp"],
                fnw=sc["fn"],
                dti=sc["dti"],
            )
        folded.append(fold_record)
        print(
            f"      seed={seed} {f['name']} (truth={int(f['truth'].sum()):,}): "
            f"STR88_dink={fold_record['arms']['candidate']['dti']:.4f}, "
            f"STR88_spc={fold_record['arms']['str88_spaced']['dti']:.4f}, "
            f"MGC88={fold_record['arms']['mgc88_incumbent']['dti']:.4f}, "
            f"raw={fold_record['arms']['raw_control']['dti']:.4f} "
            f"({time.monotonic() - ft0:.1f}s)",
            flush=True,
        )

    holdout_receipt = evaluate_holdout.pooled_summary(
        terms, draws=1000, seed=88022, candidate="candidate"
    )
    spaced_vs_mgc = evaluate_holdout.pooled_summary(
        {"str88_spaced": terms["str88_spaced"], "mgc88_incumbent": terms["mgc88_incumbent"]},
        draws=1000,
        seed=88022,
        candidate="str88_spaced",
    )
    holdout_receipt["experiment_id"] = "STR-88"
    holdout_receipt["split"] = "buffered-whole-components-loqo-v2"
    holdout_receipt["conditional_training"] = (
        "LOQO visible-only labelled positives, prevalence-calibrated PU unlabeled negatives; "
        "zero hidden truth or catalogue proximity features"
    )
    holdout_receipt["paired_differences_spaced_vs_mgc88"] = spaced_vs_mgc["paired_differences"][
        "mgc88_incumbent"
    ]
    holdout_receipt["folds"] = folded

    cand_sc = holdout_receipt["scores"]["candidate"]
    mgc_sc = holdout_receipt["scores"]["mgc88_incumbent"]
    spc_sc = holdout_receipt["scores"]["str88_spaced"]
    raw_sc = holdout_receipt["scores"]["raw_control"]
    d_vs_mgc = holdout_receipt["paired_differences"]["mgc88_incumbent"]
    d_vs_raw = holdout_receipt["paired_differences"]["raw_control"]
    d_spc_mgc = spaced_vs_mgc["paired_differences"]["mgc88_incumbent"]

    print("      === POOLED HOLDOUT-DTI (n=22,893, 1,000 paired 20 km block draws) ===", flush=True)
    print(f"      STR-88 Dinkelbach: {cand_sc['dti']:.4f} [{cand_sc['ci95'][0]:.4f}, {cand_sc['ci95'][1]:.4f}]", flush=True)
    print(f"      STR-88 Spaced:     {spc_sc['dti']:.4f} [{spc_sc['ci95'][0]:.4f}, {spc_sc['ci95'][1]:.4f}]", flush=True)
    print(f"      MGC-88 Incumbent:  {mgc_sc['dti']:.4f} [{mgc_sc['ci95'][0]:.4f}, {mgc_sc['ci95'][1]:.4f}]", flush=True)
    print(f"      Raw 3-band ctrl:   {raw_sc['dti']:.4f} [{raw_sc['ci95'][0]:.4f}, {raw_sc['ci95'][1]:.4f}]", flush=True)
    print(f"      Delta(STR88_dink - MGC88): {d_vs_mgc['delta']:+.4f} [{d_vs_mgc['ci95'][0]:+.4f}, {d_vs_mgc['ci95'][1]:+.4f}]", flush=True)
    print(f"      Delta(STR88_spc  - MGC88): {d_spc_mgc['delta']:+.4f} [{d_spc_mgc['ci95'][0]:+.4f}, {d_spc_mgc['ci95'][1]:+.4f}]", flush=True)
    print(f"      Delta(STR88_dink - raw):   {d_vs_raw['delta']:+.4f} [{d_vs_raw['ci95'][0]:+.4f}, {d_vs_raw['ci95'][1]:+.4f}]", flush=True)

    print("[4/6] Fitting frozen full-footprint STR-88 predictor & checking pre-placement gates...", flush=True)
    prod_clf, prod_fit = str88.fit_str88(
        x_str, g.footprint, g.catalogue, g.footprint, seed=model.SEED + 2000
    )
    allowed_mask = g.footprint & ~g.catalogue
    all_idx = np.flatnonzero(allowed_mask.ravel())
    surface = np.zeros(g.shape, np.float32)
    surface.ravel()[all_idx] = str88.predict_indices_str88(prod_clf, x_str, all_idx)
    del prod_clf

    if not np.isfinite(surface).all() or surface.min() < 0.0 or surface.max() > 1.0:
        raise ValueError("Nonfinite or out-of-range STR-88 production posterior surface")

    ref_paths = [
        ("H33", DATA / "registry/h33_education.tif"),
        ("GEMSDOE36", DATA / "registry/gems36_anderson_pinn.tif"),
        ("GEMSDOE70", DATA / "registry/gems70_p8_oof38k.tif"),
        ("GEMSDOE73", DATA / "registry/gems73_mcsc_blakely.tif"),
        ("MGC88_exp1", ROOT / MGC_TIF_REL),
        ("dense_prior", witness),
    ]
    p99_thresh = float(np.percentile(surface[allowed_mask], 99.0))
    surface_gate = {}
    for key, ref_path in ref_paths:
        with rasterio.open(ref_path) as src:
            old = src.read(1)
            if (src.shape, src.crs, src.transform) != expected_grid:
                raise ValueError(f"Registry grid mismatch on {ref_path}")
        old = np.where(np.isfinite(old), old, 0.0).astype(np.float32)
        rho = float(spearmanr(surface[g.footprint], old[g.footprint]).statistic)
        t_ref = (old > 0) & g.footprint
        # Prospectively close IR-88-06: log both support>0 overlap and top-1% crest overlap!
        ov_support = uniqueness.dot_overlap(surface > 0, t_ref, 3.0)
        ov_top1pct = uniqueness.dot_overlap(surface > p99_thresh, t_ref, 3.0)
        surface_gate[key] = dict(
            evidence_class="REGISTRY-MEASUREMENT",
            sha256=digest(ref_path),
            full_footprint_spearman=rho,
            abs_rho=abs(rho),
            rank_duplicate=bool(abs(rho) > 0.90),
            positive_support_overlap_3px=ov_support,
            top_1pct_crest_overlap_3px=ov_top1pct,
        )
        del old, t_ref

    if any(r["rank_duplicate"] for r in surface_gate.values()):
        raise RuntimeError(f"Pre-placement surface rank correlation > 0.90: {surface_gate}")

    print("[5/6] Running exact-shell 300 m Dinkelbach allocation (budget=37,654, spacing=2.85 px)...", flush=True)
    dots_f32, prod_alloc = str88.allocate_str88_dinkelbach(
        surface, g.footprint, g.catalogue, budget=BUDGET, min_spacing_px=MIN_SPACING_PX
    )
    dots = dots_f32 > 0.5
    print(
        f"      emitted={prod_alloc['n_dots']:,}, surrogate_dti={prod_alloc['surrogate_dti']:.4f}",
        flush=True,
    )

    out_tif = DOCS / "downloads" / f"{ARTIFACT_NAME}.tif"
    receipt = submission_writer.write_submission(
        out_tif,
        dots.astype(np.float32),
        sample,
        g.footprint,
        note=NOTE,
        name=ARTIFACT_NAME,
        catalogue=g.catalogue,
        metadata={
            "lane": "STR-88",
            "scientific_status": "negative research artifact (literal 17GEMSDOE witness IR-88-01)",
            "submission_permission": "NO: universal registry witness forces forward overlap 1.0",
            "experiment_count": 3,
            "not_organizer_accepted": True,
        },
    )

    overlaps = {}
    two_phase_rows = []
    for key, ref_path in ref_paths:
        with rasterio.open(ref_path) as src:
            old = src.read(1)
        old_clean = np.where(np.isfinite(old), old, 0.0).astype(np.float32)
        t_ref = (old_clean > 0) & g.footprint
        ov3 = uniqueness.dot_overlap(dots, t_ref, 3.0)
        rev_ov3 = uniqueness.dot_overlap(t_ref, dots, 3.0)
        rho_dots = float(spearmanr(dots_f32[g.footprint], old_clean[g.footprint]).statistic)
        abs_rho_dots = abs(rho_dots)
        jac = float((dots & t_ref).sum()) / float(max(int((dots | t_ref).sum()), 1))
        pix_eq = bool(np.array_equal(dots, t_ref))
        their_dots = int(t_ref.sum())
        overlaps[key] = dict(
            evidence_class="REGISTRY-MEASUREMENT",
            sha256=digest(ref_path),
            their_dots=their_dots,
            forward_dot_overlap_3px=ov3,
            reverse_dot_overlap_3px=rev_ov3,
            spearman_rho=rho_dots,
            exact_shared_pixels=int((dots & t_ref).sum()),
            jaccard=jac,
            pixel_identical=pix_eq,
            duplicate=bool(ov3 > 0.70 or abs_rho_dots > 0.90 or pix_eq),
        )
        two_phase_rows.append(
            dict(
                submission=key,
                repo=key,
                their_dots=their_dots,
                spearman_full_footprint=abs_rho_dots,
                signed_spearman_full_footprint=rho_dots,
                my_dots_within_3px_of_theirs=ov3,
                their_dots_within_3px_of_mine=rev_ov3,
                jaccard_dot_sets=jac,
            )
        )
        print(
            f"      vs {key:12s}: overlap_3px={ov3:.4f}, rho={rho_dots:+.4f}, "
            f"shared={overlaps[key]['exact_shared_pixels']:,}",
            flush=True,
        )
        del old, old_clean, t_ref

    two_phase = uniqueness.two_phase_summary(
        two_phase_rows, int(g.footprint.sum()), expected_rasters=len(ref_paths)
    )
    discrete_ok = not two_phase["like_for_like_reading"]["duplicate"]
    beats_mgc_95ci = bool(
        cand_sc["dti"] > mgc_sc["dti"] and d_vs_mgc["ci95"][0] > 0.0 and discrete_ok
    )

    elapsed = round(time.monotonic() - start, 2)
    exp3_receipt = {
        "experiment_id": "STR-88",
        "experiment_index": 3,
        "experiment_budget_used": 3,
        "experiment_budget_max": 3,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_seconds": elapsed,
        "beats_mgc88_with_positive_95ci": beats_mgc_95ci,
        "like_for_like_discrete_uniqueness_passed": discrete_ok,
        "literal_dense_prior_duplicate": bool(overlaps["dense_prior"]["duplicate"]),
        "feature_cache_meta": str_meta,
        "leakage_canaries": {
            "evidence_class": "HOLDOUT-FEATURE-CANARY",
            "split_version": "buffered-whole-components-loqo-v2",
            "max_symmetric_auc": max_auc,
            "leakage_threshold": 0.90,
            "passed": max_auc <= 0.90,
            "features": canaries,
        },
        "holdout_summary": {
            "evaluator_version": holdout_receipt["evaluator_version"],
            "scores": holdout_receipt["scores"],
            "paired_differences": holdout_receipt["paired_differences"],
            "paired_differences_spaced_vs_mgc88": d_spc_mgc,
        },
        "production_fit": prod_fit,
        "production_allocation": prod_alloc,
        "preplacement_registry": surface_gate,
        "final_registry": overlaps,
        "two_phase_uniqueness": two_phase,
        "submission_receipt": receipt,
    }
    dump(REGISTRY / "str88_experiment_receipt.json", exp3_receipt)

    if beats_mgc_95ci:
        print("[6/6] STR-88 beat MGC-88 with 95% CI > 0! Archiving MGC-88 & updating canonical receipts...", flush=True)
        archive_mgc88_receipts()
        dump(
            REGISTRY / "leakage_canaries.json",
            dict(
                experiment_id="STR-88",
                evidence_class="HOLDOUT-FEATURE-CANARY",
                split_version="buffered-whole-components-loqo-v2",
                max_symmetric_auc=max_auc,
                leakage_threshold=0.90,
                passed=max_auc <= 0.90,
                features=canaries,
            ),
        )
        dump(REGISTRY / "holdout_result.json", holdout_receipt)
        dump(REGISTRY / "preplacement_registry.json", surface_gate)
        dump(REGISTRY / "final_registry.json", overlaps)

        v = receipt["validator"]
        tr = receipt["template_report"]
        preflight = bool(
            v["all_checks_passed"] and tr["ok"] and receipt["sha256"] == digest(out_tif)
        )
        bad = [k for k, r in overlaps.items() if r["duplicate"]]
        promoted = bool(
            preflight
            and not bad
            and max_auc <= 0.90
            and prod_alloc["n_dots"] == BUDGET
            and cand_sc["dti"] > mgc_sc["dti"]
            and d_vs_mgc["ci95"][0] > 0.0
            and cand_sc["dti"] > 0.2349
        )
        card = dict(
            schema="gems88.run-card.v1",
            experiment_id="STR-88",
            experiment_count=3,
            experiment_budget_used=3,
            experiment_budget_max=3,
            hypothesis=json.loads(PREREG.read_text())["hypothesis_title"],
            mechanism=(
                "18 baseline-invariant zero-catalogue physical channels across topographic "
                "scarp crests (det_elev_slope, det_elev), basement gravity crests & tilt "
                "(iso_grav_anom_slope, iso_grav_anom_hg, iso_grav_anom_vg), magnetic contact "
                "crests & tilt (tmi_hg, tmi_vg, rtp, tc), 4-modality spin-2 axial strike "
                "consensus, local 2.5 km depth_to_base_surf bench relief, and dimensionless "
                "GPS dilatation ratio (geod_dilaterate, geod_shearrate); fitted via LOQO "
                "prevalence-calibrated PU HistGradientBoostingClassifier and allocated to "
                "37,654 binary {0.0, 1.0} off-catalogue dots (min_spacing_px=2.85) via exact "
                "6-shell Bernoulli-max self-credit + emit.dinkelbach_allocate."
            ),
            named_non_fault_process=(
                "Circular Tertiary volcanic plugs/domes (suppressed analytically because spin-2 "
                "director exp(i*2*theta) integrates to zero under 400 m smoothing); Pleistocene "
                "Lake Lahontan wave-cut shorelines and flight-line leveling seams; playa salinity "
                "pans (Band 17 cond_surf excluded after Exp 2 CGO-88 falsification)."
            ),
            scores_evidence_class="HOLDOUT-DTI",
            holdout_dti=dict(
                version=holdout_receipt["evaluator_version"],
                withheld_positives=cand_sc["withheld_positive_pixels"],
                candidate=cand_sc["dti"],
                ci95=cand_sc["ci95"],
                str88_spaced=spc_sc,
                mgc88_incumbent=mgc_sc,
                raw_control=raw_sc,
                paired_delta_vs_control=d_vs_raw,
                paired_delta_vs_mgc88=d_vs_mgc,
                paired_delta_spaced_vs_mgc88=d_spc_mgc,
            ),
            experiments_history=[
                dict(
                    experiment=1,
                    id="MGC-88",
                    dti=mgc_sc["dti"],
                    ci95=mgc_sc["ci95"],
                    status="superseded_archived",
                    archived_tif=MGC_TIF_REL,
                ),
                dict(
                    experiment=2,
                    id="CGO-88",
                    dti=0.02271494225444374,
                    ci95=[0.015400752010557943, 0.030897634012018574],
                    status="falsified_rejected",
                ),
                dict(
                    experiment=3,
                    id="STR-88",
                    dti=cand_sc["dti"],
                    ci95=cand_sc["ci95"],
                    status="repo_holdout_best_research_only",
                    tif=f"docs/downloads/{out_tif.name}",
                ),
            ],
            correlation_overlap_vs_registry=dict(
                surface_preplacement=surface_gate,
                final_dots=overlaps,
                two_phase_summary=two_phase,
                universal_witness=universal,
                scope=(
                    "Checked against 6 SHA-pinned registry rasters (H33, GEMSDOE36, GEMSDOE70, "
                    "GEMSDOE73, MGC88_exp1, and universal dense witness 17GEMSDOE)."
                ),
            ),
            raster_sha256=receipt["sha256"],
            validator_output=dict(
                local_format_ok=preflight,
                all_checks=v["checks"],
                no_nan_in_footprint=v["checks"]["in_footprint_all_finite"],
                values_in_0_1=v["checks"]["range_0_1_guaranteed"],
                crs_shape_transform_match=bool(tr["ok"]),
                grid_reference_provenance="owner-hosted mirror; grid metadata verified against official drivendataorg/gems-prize-reference-solution",
                warning="local PASS is not organizer upload acceptance",
            ),
            submission_name=ARTIFACT_NAME,
            submission_note=NOTE,
            downloadable_file=f"downloads/{out_tif.name}",
            canary_max_auc=max_auc,
            emitted_dots=prod_alloc["n_dots"],
            production_fit=prod_fit,
            production_allocation=prod_alloc,
            time_elapsed_seconds=elapsed,
            weekly_slots_used=0,
            stop_reason=(
                "literal universal positive-footprint registry witness: 100% forward overlap"
                if bad
                else None
            ),
            verdict="promote-to-selector-only" if promoted else "negative",
            ok_to_download=True,
            ok_to_submit=False,
            independent_organizer_receipt=False,
            provenance=input_pins,
        )
        dump(REGISTRY / "run_card.json", card)
        dump(DOCS / "data" / "run-card.json", card)
        dump(DOCS / "run_card.json", card)
        print(
            f"FINAL verdict={card['verdict']} sha256={receipt['sha256']} elapsed={elapsed}s",
            flush=True,
        )
        return card

    print(
        f"[6/6] STR-88 did not beat MGC-88 with 95% CI > 0; MGC-88 kept as primary card (elapsed={elapsed}s).",
        flush=True,
    )
    return exp3_receipt


if __name__ == "__main__":
    run()
