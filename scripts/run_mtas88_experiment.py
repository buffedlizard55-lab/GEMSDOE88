#!/usr/bin/env python3
"""Execute the frozen H88-MTAS preregistration end-to-end (ONE experiment).

Frozen source: registry/preregistration_mtas88.json +
research/candidate-hypotheses-20261025-mtas.md.  The earlier session ran only
the pre-placement duplicate proof (scripts/preflight_mtas88.py, 0 experiments).
This script performs preregistration steps 1-5 exactly once, with no
post-hoc tuning:

  1. restore-check hash-pinned inputs; compute the 7 named shared columns;
  2. single-feature symmetric-AUC leakage canaries (inputs + components);
  3. pre-placement Spearman of the MTAS surface vs every obtainable registry
     raster (shared vendor/gems57/uniqueness.compare_array_to_registry);
  4. hide-and-recover holdout: vendor buffered_component_draw, seeds 20/21,
     8 whole-component folds, 3 px feature buffer, 12 px boundary, 5x5-maxima
     dots capped at 37,654/fold, vendor evaluate_holdout pooled DTI
     (alpha 0.2, beta 0.8, 300 m triangular kernel) + spatial bootstrap CI;
  5. production dots on the full grid (mapped catalogue excluded
     pixel-exactly), packaged with vendor submission_writer, re-validated
     from saved bytes, final-dot registry audit (literal + like-for-like).

The dense 17GEMSDOE witness makes the literal any-raster overlap 1.0 for
every nonempty raster (preflight proof, IR-88-60 lineage), so the verdict is
fail-closed ``negative`` / DO-NOT-SUBMIT and 0 weekly slots are spent,
whatever the holdout says.  Every score is labelled HOLDOUT-DTI; no number
here is ORGANIZER-CONFIRMED and no projection is written as a score.
"""
from __future__ import annotations

# No model/feature work may precede the shared literal duplicate-stop gate.
if __name__ == "__main__":
    from pathlib import Path as _GuardPath
    import sys as _guard_sys
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout, grid as grid_mod  # noqa: E402
from gems57.holdout import buffered_component_draw  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems57.uniqueness import (  # noqa: E402
    binding_duplicate_decision_v3,
    compare_array_to_registry,
    dot_overlap,
    two_phase_summary,
)
from gems57.validate import validate  # noqa: E402
from gems88.mtas import DOT_CAP, build_components, load_inputs, place_maxima  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402

DATE = "20261025"
SEEDS = (20, 21)
HIDE_FRAC = 0.20
BUFFER_PX = 3
BOUNDARY_PX = 12
BOOTSTRAP_SEED = 882025
BOOTSTRAP_DRAWS = 1000
CANARY_SEED = 88
CANARY_N = 20_000
STORED_BAR_NAME = "H88-ADHR (stored repo bar, cross-scope descriptive only)"
STORED_BAR_DTI = 0.187888


def log(msg: str) -> None:
    print(f"[MTAS88] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def registry_records(exclude_name: str) -> list[dict]:
    records = []
    for label, path in registry_list(ROOT, exclude=(exclude_name,)):
        records.append(dict(repo=label.split(":", 1)[0], submission=label,
                            file=str(path), sha256=None))
    return records


def canaries(arrays: dict[str, np.ndarray], hidden_any: np.ndarray,
             footprint: np.ndarray, catalogue: np.ndarray) -> dict:
    """Feature-alone symmetric AUC: withheld positives vs off-catalogue cells."""
    rng = np.random.default_rng(CANARY_SEED)
    pos_y, pos_x = np.nonzero(hidden_any)
    neg_pool_y, neg_pool_x = np.nonzero(footprint & ~catalogue)
    n_pos = min(CANARY_N, pos_y.size)
    n_neg = min(CANARY_N, neg_pool_y.size)
    pi = rng.choice(pos_y.size, size=n_pos, replace=False)
    ni = rng.choice(neg_pool_y.size, size=n_neg, replace=False)
    py, px = pos_y[pi], pos_x[pi]
    ny, nx = neg_pool_y[ni], neg_pool_x[ni]
    y = np.concatenate([np.ones(n_pos), np.zeros(n_neg)])
    rows = []
    for name, arr in arrays.items():
        vals = np.concatenate([arr[py, px], arr[ny, nx]]).astype(np.float64)
        vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
        auc = float(roc_auc_score(y, vals)) if np.ptp(vals) > 0 else 0.5
        rows.append(dict(feature=name, auc=round(auc, 6),
                         symmetric_auc=round(max(auc, 1.0 - auc), 6)))
    worst = max(rows, key=lambda r: r["symmetric_auc"])
    return dict(threshold=0.90, n_positives_sampled=int(n_pos),
                n_negatives_sampled=int(n_neg), seed=CANARY_SEED,
                positives="pooled withheld (hidden) catalogue pixels, seeds 20|21",
                negatives="footprint cells off the full mapped catalogue",
                max_symmetric_auc=worst["symmetric_auc"], max_feature=worst["feature"],
                passed=bool(worst["symmetric_auc"] <= 0.90), rows=rows)


def fingerprint(dots: np.ndarray, d_cat: np.ndarray) -> dict:
    ys, xs = np.nonzero(dots > 0)
    d = d_cat[ys, xs] if ys.size else np.array([], dtype=np.float32)
    if not d.size:
        return dict(n_dots=0)
    # nearest-neighbour spacing via EDT of the dot field with self excluded
    dist = distance_transform_edt(dots == 0)
    nn = dist[ys, xs]  # 0 at self; use second pass on dilated check below
    del dist, nn
    return dict(
        n_dots=int(ys.size),
        share_le2=float((d <= 2).mean()),
        share_gt10=float((d > 10).mean()),
        share_gt25=float((d > 25).mean()),
        median_d_cat_px=float(np.median(d)),
        mean_d_cat_px=float(d.mean()),
        min_d_cat_px=float(d.min()),
        fingerprint_screen_pass=bool((d <= 2).mean() == 0.0 and (d > 25).mean() >= 0.35),
        fingerprint_screen="share_le2 == 0 and share_gt25 >= 0.35 (fleet screen, IR lineage)",
    )


def main() -> int:
    t0 = time.monotonic()
    grid = grid_mod.load_grid(ROOT / "data/bridge")
    footprint, catalogue = grid.footprint, grid.catalogue
    sample_path = ROOT / "data/bridge/sample_submission.tif"
    feat_path = ROOT / "data/training_features.tif"
    if not feat_path.is_file():
        raise SystemExit("missing data/training_features.tif; run restore first")

    # ---- Step 1: shared columns + MTAS surface (label-blind) ----
    log("step 1: computing 7 shared MTAS input columns")
    inputs = load_inputs(feat_path, footprint)
    components = build_components(inputs, footprint)
    surface = components["mtas_surface"]
    log(f"surface: finite={bool(np.isfinite(surface).all())} "
        f"min={float(surface.min()):.4f} max={float(surface.max()):.4f} "
        f"mean={float(surface[footprint].mean()):.5f}")

    # ---- Holdout folds first (needed for canary positives + step 4) ----
    log("building buffered whole-component folds (seeds 20, 21)")
    folds_by_seed: dict[int, list[dict]] = {}
    hidden_any = np.zeros(footprint.shape, bool)
    fold_receipts = []
    for seed in SEEDS:
        folds, _quad = buffered_component_draw(
            grid, seed=seed, hide_frac=HIDE_FRAC, buffer_px=BUFFER_PX,
            boundary_px=BOUNDARY_PX)
        folds_by_seed[seed] = folds
        hidden_any |= folds[0]["hidden_all"]
        fold_receipts.extend(f["receipt"] for f in folds)
    n_withheld_total = int(sum(r["withheld_positive_pixels"] for r in fold_receipts))
    log(f"folds: {len(fold_receipts)}; withheld positives (summed folds)={n_withheld_total}")

    # ---- Step 2: leakage canaries ----
    log("step 2: single-feature canaries")
    canary_arrays = {**inputs, **components}
    canary = canaries(canary_arrays, hidden_any, footprint, catalogue)
    log(f"canary max symmetric AUC={canary['max_symmetric_auc']} "
        f"({canary['max_feature']}) passed={canary['passed']}")
    if not canary["passed"]:
        raise SystemExit("LEAKAGE CANARY FAILED (>0.90); stopping before placement")

    # ---- Step 3: pre-placement surface uniqueness ----
    stem = f"gems88-mtas88-admittance-{DATE}"
    records = registry_records(exclude_name=stem)
    log(f"step 3: pre-placement surface Spearman vs {len(records)} registry rasters")
    phase_a = compare_array_to_registry(surface, records, footprint)
    rows_a = [r for r in phase_a["rows"] if "error" not in r]
    errs_a = [r for r in phase_a["rows"] if "error" in r]
    rhos = [(abs(r["spearman_full_footprint"]), r) for r in rows_a
            if r.get("spearman_full_footprint") is not None]
    worst_abs_rho, worst_rho_row = max(rhos, key=lambda t: t[0]) if rhos else (None, None)
    surface_uniqueness = dict(
        phase="pre-placement surface",
        registry_rasters_compared=len(rows_a),
        registry_errors=len(errs_a),
        error_rows=errs_a[:10],
        worst_signed_spearman=phase_a["worst_spearman_full_footprint"],
        worst_signed_spearman_submission=phase_a["worst_rho_submission"],
        worst_abs_spearman=float(worst_abs_rho) if worst_abs_rho is not None else None,
        worst_abs_spearman_submission=(worst_rho_row or {}).get("submission"),
        rho_limit=0.90,
        rho_pass=bool(worst_abs_rho is not None and worst_abs_rho <= 0.90),
        scope=phase_a["scope"],
    )
    log(f"surface worst |rho|={worst_abs_rho} vs "
        f"{surface_uniqueness['worst_abs_spearman_submission']}")
    if not surface_uniqueness["rho_pass"]:
        raise SystemExit("SURFACE DUPLICATE (|rho|>0.90); stopping before placement")

    # ---- Step 4: holdout (per-fold 5x5 maxima, visible-only exclusion) ----
    log("step 4: 8-fold hide-and-recover holdout")
    terms_total = None
    per_fold = []
    for seed in SEEDS:
        for fold in folds_by_seed[seed]:
            allowed = fold["region"] & footprint & ~fold["masked_known"]
            pred = place_maxima(surface, allowed, cap=DOT_CAP)
            result, terms = evaluate_holdout.evaluate(
                pred, fold, footprint, origin=(0, 0), global_shape=grid.shape)
            terms_total = terms if terms_total is None else terms_total + terms
            per_fold.append(dict(
                seed=seed, fold=fold["name"],
                dti=round(float(result["dti"]), 6),
                n_truth=int(result["n_truth"]),
                n_emitted=int(result["n_emitted"]),
                evidence_class="HOLDOUT-DTI",
                evaluator_version=evaluate_holdout.VERSION))
            del pred, allowed
            log(f"  seed {seed} {fold['name']}: HOLDOUT-DTI={result['dti']:.6f} "
                f"n_truth={result['n_truth']} emitted={result['n_emitted']}")
    pooled = evaluate_holdout.pooled_summary(
        {"mtas88": terms_total}, candidate="mtas88",
        draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED)
    score = pooled["scores"]["mtas88"]
    holdout = dict(
        evidence_class="HOLDOUT-DTI",
        evaluator_version=evaluate_holdout.VERSION,
        alpha=0.2, beta=0.8, triangular_radius_m=300.0,
        split="buffered-whole-components-loqo-v2",
        seeds=list(SEEDS), n_folds=len(per_fold),
        buffer_px=BUFFER_PX, boundary_px=BOUNDARY_PX, hide_frac=HIDE_FRAC,
        dot_rule="5x5 local maxima of the label-blind MTAS surface, "
                 "region & footprint & ~masked_known, cap 37654/fold",
        dti=round(float(score["dti"]), 6),
        ci95=[round(float(score["ci95"][0]), 6), round(float(score["ci95"][1]), 6)],
        withheld_positive_pixels=int(score["withheld_positive_pixels"]),
        tpw=round(float(score["tpw"]), 3), fpw=round(float(score["fpw"]), 3),
        fnw=round(float(score["fnw"]), 3),
        per_fold=per_fold, fold_receipts=fold_receipts,
        bootstrap=pooled["bootstrap"],
        implementation_sha256=pooled["implementation_sha256"],
        stored_bar=dict(name=STORED_BAR_NAME, dti=STORED_BAR_DTI,
                        comparison="descriptive only: different fold construction/"
                                   "withheld count; NOT a paired test",
                        candidate_minus_bar=round(float(score["dti"]) - STORED_BAR_DTI, 6),
                        beats_stored_bar=bool(score["dti"] > STORED_BAR_DTI)),
        note="HOLDOUT-DTI only. Not ORGANIZER-CONFIRMED; not a leaderboard projection.",
    )
    log(f"pooled HOLDOUT-DTI={holdout['dti']} CI95={holdout['ci95']} "
        f"n={holdout['withheld_positive_pixels']}")

    # ---- Step 5: production dots + final uniqueness + packaging ----
    log("step 5: production placement (full catalogue excluded pixel-exactly)")
    allowed_prod = footprint & ~catalogue
    emitted = place_maxima(surface, allowed_prod, cap=DOT_CAP)
    n_dots = int((emitted > 0).sum())
    d_cat = distance_transform_edt(~catalogue).astype(np.float32)
    fp_info = fingerprint(emitted, d_cat)
    log(f"production dots={n_dots}; fingerprint={fp_info}")

    log(f"final-dot registry audit vs {len(records)} rasters")
    phase_b = compare_array_to_registry(emitted, records, footprint)
    rows_b = phase_b["rows"]
    two_phase = two_phase_summary(rows_b, int(footprint.sum()),
                                  expected_rasters=len(records))
    literal_decision = binding_duplicate_decision_v3(rows_b)
    h33_rows = [r for r in rows_b if "h33" in str(r.get("submission", "")).lower()]
    dense_path = ROOT / "data/registry/dense_17gemdoe.tif"
    with rasterio.open(dense_path) as src:
        dense_overlap = float(dot_overlap(emitted, src.read(1), radius_px=3.0))
    final_uniqueness = dict(
        phase="final dots",
        registry_rasters_compared=phase_b["registry_rasters_checked"],
        registry_errors=phase_b["missing_or_invalid"],
        literal_dense_witness_overlap_3px=round(dense_overlap, 6),
        literal_binding_decision={k: literal_decision[k] for k in (
            "binding_rule", "duplicate", "stop_required", "verdict",
            "worst_literal_forward_overlap", "worst_literal_forward_overlap_file",
            "worst_abs_spearman", "worst_abs_spearman_file",
            "overlap_limit", "rho_limit", "rasters_checked",
            "space_filling_priors", "discriminating_priors") if k in literal_decision},
        two_phase=two_phase,
        worst_rows_by_overlap=sorted(
            [r for r in rows_b if "error" not in r],
            key=lambda r: r["my_dots_within_3px_of_theirs"], reverse=True)[:12],
        vs_h33_education=h33_rows,
        scope=phase_b["scope"],
    )
    like = two_phase["like_for_like_reading"]
    unique_like_for_like = bool(not like["duplicate"]
                                and (like["worst_forward_overlap_dot_fields"] or 0) <= 0.70)
    log(f"literal duplicate={literal_decision['duplicate']} "
        f"(dense witness {dense_overlap:.4f}); like-for-like unique={unique_like_for_like} "
        f"(worst dot-field overlap {like['worst_forward_overlap_dot_fields']})")

    # Fail-closed verdict: literal duplicate alone forces negative.
    verdict = "negative"
    ok_to_submit = False
    reasons = []
    if literal_decision["duplicate"]:
        reasons.append(
            f"literal any-raster 3px overlap {dense_overlap:.4f} > 0.70 vs the "
            "space-filling 17GEMSDOE continuous witness (vacuous for every "
            "nonempty raster; binding under the written rule, IR-88-60)")
    if not holdout["stored_bar"]["beats_stored_bar"]:
        reasons.append(
            f"HOLDOUT-DTI {holdout['dti']} does not beat the stored "
            f"{STORED_BAR_DTI} bar (descriptive cross-scope comparison)")
    reasons.append("no paired same-fold incumbent test and no human selector "
                   "decision; promotion is a separate step by protocol")

    file_stem = f"gems88-mtas88-admittance-{n_dots}dots-{DATE}-zeros-DO-NOT-SUBMIT"
    tif_path = ROOT / "docs/downloads" / f"{file_stem}.tif"
    name = "GEMSDOE88-MTAS88-ADMITTANCE-20261025"
    note = (f"MTAS88 grav-mag scale-admittance {n_dots}d; "
            f"HOLDOUT-DTI {holdout['dti']:.4f} n={holdout['withheld_positive_pixels']}; "
            "UNSCORED DO-NOT-SUBMIT")
    assert len(name) <= 140 and len(note) <= 140, (len(name), len(note))
    log(f"writing {tif_path.name} via vendor submission_writer")
    receipt = write_submission(
        tif_path, emitted, sample_path, footprint, note=note, name=name,
        catalogue=catalogue,
        metadata=dict(lane="H88-MTAS", verdict=verdict, ok_to_submit=False,
                      evidence_class="HOLDOUT-DTI",
                      holdout_dti=holdout["dti"], n_dots=n_dots))
    # Independent re-validation from saved bytes + ZIP identity.
    validation = validate(tif_path, footprint, catalogue)
    zip_path = tif_path.with_suffix(".zip")
    with zipfile.ZipFile(zip_path) as z:
        zip_ok = (z.namelist() == [tif_path.name]
                  and z.read(tif_path.name) == tif_path.read_bytes())
    raster_sha = sha256_file(tif_path)
    log(f"saved TIFF sha256={raster_sha} validator_pass={validation['all_checks_passed']} "
        f"zip_ok={zip_ok}")

    run_card = dict(
        schema="gems88.mtas88.experiment-run-card.v1",
        date_utc="2026-10-25",
        lane="H88-MTAS",
        preregistration="registry/preregistration_mtas88.json",
        hypothesis=("A buried basement fault under low-relief cover keeps a "
                    "short-scale (200 m) gravity gradient edge while its "
                    "magnetic (RTP) short-scale edge is smoothed/demagnetized; "
                    "the cross-scale admittance residual "
                    "max(0,(G200-G800)-(M200-M800)), gated by cover, low slope "
                    "and transtension, marks faults missing from the "
                    "USGS/INGENIOUS catalogue."),
        mechanism=("Label-blind percentile-normalized scale residuals of the "
                   "shared RTP/gravity gradient columns; soft multiplicative "
                   "gates (cover 0.25-1.0, low-slope 0.25-1.0, transtension "
                   "0.5-1.0); 5x5 local-maxima dot placement, cap 37654."),
        named_non_fault_process=("Unfaulted intrusive/volcanic lithologic "
                                 "contact with density but weak magnetic "
                                 "contrast (flight-line levelling seams are a "
                                 "second acquisition confounder)."),
        inputs=dict(
            training_features_sha256="4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
            bands={"2": "rtp", "7": "geod_shearrate", "8": "geod_dilaterate",
                   "13": "iso_grav_anom", "15": "depth_to_base_surf",
                   "19": "det_elev_slope"},
            shared_columns=["rtp_grad_200m", "rtp_grad_800m", "grav_grad_200m",
                            "grav_grad_800m", "depth_to_base_log",
                            "det_elev_slope", "geod_transtension"],
            provenance="Owner GitHub mirrors, SHA-pinned; NOT authenticated "
                       "against a logged-in organizer download."),
        leakage_canaries=canary,
        surface_uniqueness=surface_uniqueness,
        holdout=holdout,
        production=dict(
            dot_rule="5x5 local maxima, footprint & ~catalogue (pixel-exact), "
                     "descending surface rank, cap 37654",
            fingerprint=fp_info),
        final_uniqueness=final_uniqueness,
        correlation_overlap_vs_registry=dict(
            surface_worst_abs_spearman=surface_uniqueness["worst_abs_spearman"],
            final_worst_abs_spearman=final_uniqueness["literal_binding_decision"].get("worst_abs_spearman"),
            final_literal_worst_overlap_3px=final_uniqueness["literal_binding_decision"].get("worst_literal_forward_overlap"),
            final_like_for_like_worst_overlap_3px=like["worst_forward_overlap_dot_fields"],
            unique_like_for_like=unique_like_for_like,
            unique_literal=bool(not literal_decision["duplicate"]),
            thresholds=dict(abs_spearman=0.90, forward_overlap_3px=0.70)),
        raster_file=f"docs/downloads/{tif_path.name}",
        raster_sha256=raster_sha,
        zip_file=f"docs/downloads/{zip_path.name}",
        zip_sha256=sha256_file(zip_path),
        zip_single_member_identical=bool(zip_ok),
        validator_output=dict(
            all_checks_passed=bool(validation["all_checks_passed"]),
            checks=validation["checks"], min=validation["min"],
            max=validation["max"], n_nan=validation["n_nan"],
            emitted_positive_pixels=validation["emitted_positive_pixels"],
            meta=validation["meta"], sha256=validation["sha256"],
            writer_receipt_sha256=receipt["sha256"],
            validation_class=validation["validation_class"]),
        submission_name=name, submission_note=note,
        submission_note_length=len(note),
        experiment_count=1, experiments_budget=1,
        weekly_slots_used=0, organizer_confirmed_score=None,
        ok_to_download=True,
        ok_to_download_scope="research/audit only; filename carries DO-NOT-SUBMIT",
        ok_to_submit=ok_to_submit,
        approved_for_weekly_slot=False,
        verdict=verdict,
        verdict_reasons=reasons,
        elapsed_s=round(time.monotonic() - t0, 1),
    )

    payload = json.dumps(run_card, indent=2, allow_nan=False) + "\n"
    for rel in ("registry/mtas88_experiment_run_card.json",
                "docs/data/mtas88_experiment_run_card.json",
                "evidence/mtas88_experiment_20261025.json"):
        target = ROOT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    audit_path = tif_path.with_suffix(".format-audit.json")
    audit_path.write_text(json.dumps(validation, indent=2, allow_nan=False) + "\n",
                          encoding="utf-8")
    log(f"DONE verdict={verdict} ok_to_submit={ok_to_submit} "
        f"HOLDOUT-DTI={holdout['dti']} dots={n_dots} sha256={raster_sha}")
    print(json.dumps(dict(
        file=str(tif_path.relative_to(ROOT)), sha256=raster_sha, n_dots=n_dots,
        holdout_dti=holdout["dti"], ci95=holdout["ci95"],
        withheld=holdout["withheld_positive_pixels"],
        canary_max=canary["max_symmetric_auc"],
        surface_worst_abs_rho=surface_uniqueness["worst_abs_spearman"],
        like_for_like_worst_overlap=like["worst_forward_overlap_dot_fields"],
        literal_dense_overlap=dense_overlap, verdict=verdict,
        ok_to_submit=ok_to_submit, note=note), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
