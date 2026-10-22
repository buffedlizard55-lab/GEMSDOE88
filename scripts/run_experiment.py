#!/usr/bin/env python3
"""One preregistered MGC-88 experiment. Produces an AUTOMATIC negative/positive card.

No competition upload is performed. Even a locally valid TIFF is NOT approved
if the literal registry witness (or any other gate) fails. A research-only TIFF
is intentionally retained for byte-auditable learning, never masqueraded as a
promoted competition submission. Budget: one fixed experiment, two seed draws.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout, holdout, grid, submission_writer, uniqueness  # noqa: E402
from gems88 import edge, model  # noqa: E402
from restore_inputs import digest  # noqa: E402 -- input verifier (called separately)

DATA = ROOT / "data"
REGISTRY = ROOT / "registry"
DOCS = ROOT / "docs"
PREREG = REGISTRY / "preregistration.json"
ARTIFACT_NAME = "gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT"
NOTE = "MGC88 basin-cover RTP/gravity aligned-edge HGB, 2px-spaced 37654 dots; research only: universal overlap gate blocks upload"
BUDGET = 37654
SEEDS = (20, 21)


def dump(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(content, indent=2, allow_nan=False, sort_keys=True) + "\n"
    )


def checked_inputs():
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
    }
    for name, (path, sha) in expected.items():
        if digest(DATA / path) != sha:
            raise ValueError(
                f"{name} SHA256 mismatch: cannot use unverified input {path}"
            )
    return {k: dict(file=v[0], sha256=v[1]) for k, v in expected.items()}


def bbox(region, pad=4):
    row, col = np.nonzero(region)
    if not row.size:
        raise ValueError("empty fold region")
    return (
        slice(
            max(int(row.min()) - pad, 0), min(int(row.max()) + pad + 1, region.shape[0])
        ),
        slice(
            max(int(col.min()) - pad, 0), min(int(col.max()) + pad + 1, region.shape[1])
        ),
    )


def flat_feature_tie(x, sl, width):
    # Sparse memmap lookup of the 7th label-blind co-edge feature for one crop.
    h = sl[0].stop - sl[0].start
    w = sl[1].stop - sl[1].start
    r = np.arange(sl[0].start, sl[0].stop, dtype=np.int64)
    c = np.arange(sl[1].start, sl[1].stop, dtype=np.int64)
    return np.asarray(x[(r[:, None] * width + c[None, :]).ravel(), 6]).reshape(h, w)


def run():
    start = time.monotonic()
    if not PREREG.is_file():
        raise FileNotFoundError("preregistration missing")
    input_pins = checked_inputs()
    g = grid.load_grid()
    sample = DATA / "bridge" / "sample_submission.tif"
    with rasterio.open(sample) as ref:
        expected = (ref.shape, ref.crs, ref.transform)
    witness = DATA / "registry" / "dense_17gemdoe.tif"
    universal = uniqueness.saturation_certificate(
        witness, g.footprint, g.catalogue, expected_grid=expected
    )
    dump(REGISTRY / "witness_certificate.json", universal)
    print(
        "WITNESS",
        universal["universal_overlap_blocker"],
        universal["uncovered_allowed_pixels"],
        flush=True,
    )
    # This result already rules out promotion. Still run exactly one pre-registered
    # negative experiment; package a labelled research artifact for audit, not upload.
    cache = DATA / "cache" / "mgc88-7channel.f32"
    feature_receipt = edge.build_cache(
        DATA / "training_features.tif", g.footprint, cache
    )
    feature_receipt.update(
        input_sha256=input_pins["training_features.tif"]["sha256"],
        cache_bytes=cache.stat().st_size,
        cache_sha256=digest(cache),
        build_source_sha256=digest(ROOT / "src" / "gems88" / "edge.py"),
    )
    dump(REGISTRY / "feature_receipt.json", feature_receipt)
    x = np.memmap(
        cache, mode="r", dtype="float32", shape=(g.height * g.width, len(edge.NAMES))
    )
    folds = []
    quads = {}
    for seed in SEEDS:
        draw, quad = holdout.buffered_component_draw(
            g, seed=seed, buffer_px=3, boundary_px=12
        )
        folds.extend(draw)
        quads[seed] = quad
    split = dict(
        version="buffered-whole-components-loqo-v2",
        seeds=SEEDS,
        fields=[f["receipt"] for f in folds],
        evaluator=evaluate_holdout.VERSION,
        split_source_sha256=digest(ROOT / "vendor" / "gems57" / "holdout.py"),
    )
    dump(REGISTRY / "holdout_split.json", split)
    print(
        "FOLDS",
        [(f["name"], f["receipt"]["withheld_positive_pixels"]) for f in folds],
        flush=True,
    )
    canaries = model.leakage_canaries(x, edge.NAMES, folds, g.footprint)
    max_auc = max(r["symmetric_auc"] for r in canaries)
    dump(
        REGISTRY / "leakage_canaries.json",
        dict(
            evidence_class="HOLDOUT-FEATURE-CANARY",
            split_version=split["version"],
            max_symmetric_auc=max_auc,
            leakage_threshold=0.90,
            passed=max_auc <= 0.90,
            features=canaries,
        ),
    )
    print("CANARY MAX SYMMETRIC AUC", max_auc, flush=True)
    if max_auc > 0.90:
        raise RuntimeError(
            "feature leakage canary >0.90; experiment STOP: no raster may be trusted"
        )

    terms = {"candidate": None, "raw_control": None}
    folded = []
    for f in folds:
        seed = f["receipt"]["seed"]
        fi = f["fold"]
        train_region = g.footprint & (quads[seed] != fi)
        sl = bbox(f["region"])
        pvalid = g.footprint[sl]
        region = f["region"][sl]
        eligible = region & pvalid & ~f["visible"][sl]
        indices_local = np.flatnonzero(eligible.ravel())
        w = sl[1].stop - sl[1].start
        rr, cc = np.divmod(indices_local, w)
        global_idx = (sl[0].start + rr) * g.width + (sl[1].start + cc)
        budget = max(1, round(BUDGET * int(region.sum()) / int(g.footprint.sum())))
        tie = flat_feature_tie(x, sl, g.width)
        fold_record = dict(
            seed=seed,
            quadrant=f["name"],
            withheld_positive_pixels=int(f["truth"].sum()),
            feature_context_buffer_px=3,
            boundary_buffer_px=12,
            budget=budget,
            arms={},
        )
        for arm, cols in (("raw_control", model.BASE), ("candidate", model.JOINT)):
            fitted, fit_info = model.fit(
                x,
                g.footprint,
                f["visible"],
                train_region,
                cols,
                seed=model.SEED + seed * 4 + fi,
            )
            p = np.zeros(eligible.shape, np.float32)
            p.ravel()[indices_local] = model.probability(fitted, x, global_idx, cols)
            dots, emission = model.spaced_dots(p, eligible, budget, radius=2, tie=tie)
            region_fold = {
                key: val[sl]
                for key, val in f.items()
                if key in ("region", "visible", "masked_known", "truth")
            }
            score, by_block = evaluate_holdout.evaluate(
                dots.astype(np.float32),
                region_fold,
                pvalid,
                origin=(sl[0].start, sl[1].start),
                global_shape=g.shape,
                block_side=200,
            )
            if terms[arm] is None:
                terms[arm] = by_block
            else:
                terms[arm] += by_block
            fold_record["arms"][arm] = dict(
                training=fit_info,
                emission=emission,
                # Fold scores are diagnostic; the pooled score + CI is the evidence.
                tpw=score["tp"],
                fpw=score["fp"],
                fnw=score["fn"],
            )
            print(
                "HOLDOUT",
                seed,
                f["name"],
                arm,
                "truth",
                score["n_truth"],
                "dots",
                emission["emitted"],
                flush=True,
            )
            del fitted, p, dots, by_block, score
        folded.append(fold_record)
    holdout_receipt = evaluate_holdout.pooled_summary(
        terms, draws=1000, seed=88022, candidate="candidate"
    )
    holdout_receipt["split"] = split["version"]
    holdout_receipt["conditional_training"] = (
        "LOQO visible-only labelled positives, noisy unlabeled negatives; no hidden truth feature"
    )
    holdout_receipt["folds"] = folded
    dump(REGISTRY / "holdout_result.json", holdout_receipt)
    print("POOLED HOLDOUT-DTI", holdout_receipt["scores"]["candidate"], flush=True)

    # Freeze production predictor. The only labels used for fitting are the
    # public fault catalogue; exactly those pixels are zeroed for the export.
    predictor, production_fit = model.fit(
        x, g.footprint, g.catalogue, g.footprint, model.JOINT, seed=model.SEED + 1000
    )
    all_idx = np.flatnonzero((g.footprint & ~g.catalogue).ravel())
    surface = np.zeros(g.shape, np.float32)
    surface.ravel()[all_idx] = model.probability(predictor, x, all_idx, model.JOINT)
    del predictor
    if not np.isfinite(surface).all() or surface.min() < 0 or surface.max() > 1:
        raise ValueError("nonfinite or out-of-range surface")
    # RANK-CORRELATION CHECK ON CONTINUOUS SURFACE BEFORE DOT PLACEMENT.
    surface_gate = {}
    for key, path in [
        ("H33", DATA / "registry" / "h33_education.tif"),
        ("dense_prior", witness),
    ]:
        with rasterio.open(path) as src:
            old = src.read(1)
            if (src.shape, src.crs, src.transform) != expected:
                raise ValueError("registry grid does not match sample")
        old = np.where(np.isfinite(old), old, 0).astype(np.float32)
        a = surface[g.footprint]
        b = old[g.footprint]
        rho = float(spearmanr(a, b).statistic)
        surface_gate[key] = dict(
            evidence_class="REGISTRY-MEASUREMENT",
            sha256=digest(path),
            full_footprint_spearman=rho,
            abs_rho=abs(rho),
            rank_duplicate=(abs(rho) > 0.90),
        )
        del old, a, b
    dump(REGISTRY / "preplacement_registry.json", surface_gate)
    if any(r["rank_duplicate"] for r in surface_gate.values()):
        raise RuntimeError(
            "surface rank correlation >.90 with a registry raster: STOP before placement"
        )
    print(
        "SURFACE RHO",
        {k: v["full_footprint_spearman"] for k, v in surface_gate.items()},
        flush=True,
    )
    production_tie = np.asarray(x[:, 6]).reshape(g.shape)
    dots, production_emission = model.spaced_dots(
        surface, g.footprint & ~g.catalogue, BUDGET, radius=2, tie=production_tie
    )
    path = DOCS / "downloads" / f"{ARTIFACT_NAME}.tif"
    receipt = submission_writer.write_submission(
        path,
        dots.astype(np.float32),
        sample,
        g.footprint,
        note=NOTE,
        name=ARTIFACT_NAME,
        catalogue=g.catalogue,
        metadata={
            "lane": "MGC-88",
            "scientific_status": "negative research artifact",
            "submission_permission": "NO: universal registry witness forces forward overlap 1.0",
            "experiment_count": 1,
            "not_organizer_accepted": True,
        },
    )
    # Literal FINAL-DOT overlap check. One pinned universal witness suffices to
    # prove failure; do not weaken the rule or silently exempt the prior.
    overlaps = {}
    for key, path_old in [
        ("H33", DATA / "registry" / "h33_education.tif"),
        ("dense_prior", witness),
    ]:
        with rasterio.open(path_old) as src:
            old = src.read(1)
        t = np.isfinite(old) & (old > 0) & g.footprint
        overlaps[key] = dict(
            evidence_class="REGISTRY-MEASUREMENT",
            sha256=digest(path_old),
            forward_dot_overlap_3px=uniqueness.dot_overlap(dots, t, 3.0),
            exact_shared_pixels=int((dots & t).sum()),
            pixel_identical=bool(np.array_equal(dots, t)),
        )
        overlaps[key]["duplicate"] = bool(
            overlaps[key]["forward_dot_overlap_3px"] > 0.70
            or overlaps[key]["pixel_identical"]
        )
        del old, t
    dump(REGISTRY / "final_registry.json", overlaps)
    bad = [k for k, r in overlaps.items() if r["duplicate"]]
    if bool(universal["universal_overlap_blocker"]) != bool(
        overlaps["dense_prior"]["duplicate"]
    ):
        raise AssertionError("universal proof disagrees with measured final overlap")
    v = receipt["validator"]
    tr = receipt["template_report"]
    preflight = bool(
        v["all_checks_passed"] and tr["ok"] and receipt["sha256"] == digest(path)
    )
    ci = holdout_receipt["scores"]["candidate"]["ci95"]
    score = holdout_receipt["scores"]["candidate"]["dti"]
    baseline = holdout_receipt["scores"]["raw_control"]["dti"]
    paired = holdout_receipt["paired_differences"]["raw_control"]
    promoted = bool(
        preflight
        and not bad
        and max_auc <= 0.90
        and production_emission["emitted"] == BUDGET
        and score > baseline
        and paired["ci95"][0] > 0
        and score > 0.2349
    )
    card = dict(
        schema="gems88.run-card.v1",
        experiment_count=1,
        hypothesis=json.loads(PREREG.read_text())["hypothesis"],
        mechanism="Signed RTP-magnetic / isostatic-gravity co-edge, with depth-to-base as basin-cover covariate; learned on visible public faults only.",
        named_non_fault_process="Unfaulted lithologic contact / sedimentary facies edge; magnetic survey flight-line gridding seam.",
        scores_evidence_class="HOLDOUT-DTI",
        holdout_dti=dict(
            version=holdout_receipt["evaluator_version"],
            withheld_positives=holdout_receipt["scores"]["candidate"][
                "withheld_positive_pixels"
            ],
            candidate=score,
            ci95=ci,
            raw_control=holdout_receipt["scores"]["raw_control"],
            paired_delta_vs_control=paired,
        ),
        correlation_overlap_vs_registry=dict(
            surface_preplacement=surface_gate,
            final_dots=overlaps,
            universal_witness=universal,
            scope="Proof of duplication against two hash-verified owner registry rasters; NOT a full inventory uniqueness certification.",
        ),
        raster_sha256=receipt["sha256"],
        validator_output=dict(
            local_format_ok=preflight,
            all_checks=v["checks"],
            no_nan_in_footprint=v["checks"]["in_footprint_all_finite"],
            values_in_0_1=v["checks"]["range_0_1_guaranteed"],
            crs_shape_transform_match=bool(tr["ok"]),
            grid_reference_provenance="owner-hosted mirror, NOT organizer authenticated",
            warning="local PASS is not organizer upload acceptance",
        ),
        submission_name=ARTIFACT_NAME,
        submission_note=NOTE,
        downloadable_file=f"downloads/{path.name}",
        canary_max_auc=max_auc,
        emitted_dots=production_emission["emitted"],
        production_fit=production_fit,
        experiment_budget_used=1,
        time_elapsed_seconds=round(time.monotonic() - start, 2),
        weekly_slots_used=0,
        stop_reason="literal universal positive-footprint registry witness: 100% forward overlap"
        if bad
        else None,
        verdict="promote-to-selector-only" if promoted else "negative",
        ok_to_download=True,
        ok_to_submit=False,
        independent_organizer_receipt=False,
        provenance=input_pins,
    )
    if len(NOTE) > 140 or len(ARTIFACT_NAME) > 140:
        raise AssertionError("note/name too long")
    dump(REGISTRY / "run_card.json", card)
    dump(DOCS / "data" / "run-card.json", card)
    print(
        "FINAL",
        card["verdict"],
        "format",
        preflight,
        "overlap",
        overlaps,
        "sha256",
        receipt["sha256"],
        "elapsed",
        card["time_elapsed_seconds"],
        flush=True,
    )
    return card


if __name__ == "__main__":
    run()
