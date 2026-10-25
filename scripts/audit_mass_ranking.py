#!/usr/bin/env python3
"""Audit the ranking that produced the three MASS variants of R0.

The agent brief (v2, section 5) specifies that MASS variants drop/add by
"the parent's own ranking (rebuild the ranking from the recorded recipe if it
is not stored)".  R0's model score is not stored anywhere in this repository
(every raster in the H33 lineage is binary), so this script asks and answers
four falsifiable questions about what was actually used:

  Q1 RECONSTRUCTION  Can the shipped drop/add sets be reproduced exactly from the
                     ranking formula recorded in scripts/generate_axis_variants.py?
  Q2 WHAT IT RANKS  If that formula is 0.6*clip(d_catalogue/50)+0.4*uniform(seed),
                     then the "lowest-ranked 10%" is a near-catalogue deletion, not
                     a low-prior deletion.  Measure it against the random baseline.
  Q3 STABILITY       How much of the drop set survives a change of the random seed?
  Q4 PRIOR ALIGNMENT Are the dropped dots actually the low-prior ones under an
                     independent model score (the pinned dense witness)?

It writes registry/mass_ranking_audit.json and exits non-zero if the audit
cannot reconstruct the shipped files (so CI catches silent drift). Enforces
SHA-256 and probability invariants even under python -O.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid as grid_mod, metric  # noqa: E402

BRIDGE = ROOT / "data" / "bridge"
H33 = ROOT / "data" / "registry" / "h33_education.tif"
DENSE = ROOT / "data" / "registry" / "dense_17gemdoe.tif"
RELEASES = ROOT / "releases"

PARENT_SHA = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
DENSE_SHA = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"

# Shipped variants: id suffix -> (release sha8, operator, fraction)
SHIPPED = {
    "MASSm10minus": ("7132935e", "drop", 0.10),
    "MASSm10plus": ("82673b57", "add", 0.10),
    "MASSm20minus": ("6c73303c", "drop", 0.20),
}


def _require(condition: object, message: object = "MASS ranking audit failed") -> None:
    if not condition:
        raise AssertionError(str(message))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(p: Path) -> np.ndarray:
    with rasterio.open(p) as src:
        return src.read(1)


def main(root: Path = ROOT, write_output: bool = True) -> int:
    root = Path(root)
    bridge = root / "data" / "bridge"
    h33_path = root / "data" / "registry" / "h33_education.tif"
    dense_path = root / "data" / "registry" / "dense_17gemdoe.tif"
    releases_dir = root / "releases"
    sample_path = bridge / "sample_submission.tif"
    faults_path = bridge / "existing_faults.tif"

    _require(sha256(h33_path) == PARENT_SHA, "R0 hash mismatch -- re-run restore_inputs.py")
    _require(
        sha256(sample_path) == grid_mod.SHA256_SAMPLE_SUBMISSION,
        "sample_submission.tif hash mismatch",
    )
    _require(
        sha256(faults_path) == grid_mod.SHA256_EXISTING_FAULTS,
        "existing_faults.tif hash mismatch",
    )
    _require(sha256(dense_path) == DENSE_SHA, "dense witness hash mismatch")

    r0 = read(h33_path) > 0.5
    ef = read(faults_path)
    catalogue = ef == 1
    footprint = (ef == 0) | (ef == 1)
    d_cat = distance_transform_edt(~catalogue)
    d_parent = d_cat[r0]
    n_parent = int(r0.sum())

    dense = read(dense_path)
    finite_dense = np.isfinite(dense)
    _require(
        finite_dense.all() or (finite_dense == footprint).all(),
        "dense witness must be finite exactly on the footprint",
    )
    _require(
        (dense[finite_dense] >= 0).all() and (dense[finite_dense] <= 1).all(),
        "dense witness must be a probability",
    )

    rows, cols = np.where(r0)

    # ---- Q1: reconstruct the shipped ranking exactly ------------------------
    rng88 = np.random.default_rng(88)
    norm_parent = np.clip(d_parent / 50.0, 0.0, 1.0)
    parent_score = 0.6 * norm_parent + 0.4 * rng88.random(n_parent)
    order_low_to_high = np.argsort(parent_score)

    allowed_2px = footprint & (d_cat > 2.0)
    pool = allowed_2px & (~r0)
    p_rows, p_cols = np.where(pool)
    rng90 = np.random.default_rng(90)
    cand_score = 0.6 * np.clip(d_cat[pool] / 50.0, 0.0, 1.0) + 0.4 * rng90.random(p_rows.size)
    cand_high_to_low = np.argsort(-cand_score)

    build = {}
    for value, (sha8, op, frac) in SHIPPED.items():
        k = int(round(n_parent * frac))
        arr = np.zeros_like(r0)
        if op == "drop":
            keep = order_low_to_high[k:]
            arr[rows[keep], cols[keep]] = True
        else:
            arr[r0] = True
            sel = cand_high_to_low[:k]
            arr[p_rows[sel], p_cols[sel]] = True
        built = releases_dir / f"h33-h33-2-b2-{value}-20261023-{sha8}.tif"
        on_disk = read(built) > 0.5
        build[value] = {
            "release_present": built.is_file(),
            "reconstructed_sha8": sha8,
            "identical_to_on_disk": bool(np.array_equal(arr, on_disk)),
            "n_dots": int(arr.sum()),
            "frac_changed": round(
                float((k / n_parent) if op == "drop" else ((arr.sum() - n_parent) / n_parent)) * 100,
                2,
            ),
            "_changed": (r0 & ~arr) if op == "drop" else (arr & ~r0),
        }

    reconstructed_all = all(v["identical_to_on_disk"] for v in build.values())

    # ---- Q2: what the ranking actually ranks -------------------------------
    collar = [5, 10, 20, 50]
    baseline = {c: float((d_parent <= c).mean()) for c in collar}
    confound = {}
    for value, v in build.items():
        if SHIPPED[value][1] != "drop":
            continue
        dd = d_cat[v["_changed"]]
        confound[value] = {
            "n_dropped": int(dd.size),
            "mean_dist_to_catalogue_px": round(float(dd.mean()), 2),
            "mean_dist_kept_px": round(float(d_cat[r0 & ~v["_changed"]].mean()), 2),
            "frac_dropped_within_px": {str(c): round(float((dd <= c).mean()), 3) for c in collar},
            "baseline_frac_within_px": {str(c): round(baseline[c], 3) for c in collar},
            "enrichment_vs_random": {
                str(c): round(float((dd <= c).mean() / baseline[c]), 2) if baseline[c] > 0 else None
                for c in collar
            },
            "d_catalogue_saturates_at_50px_frac_of_parent": round(
                float((norm_parent >= 1.0).mean()), 3
            ),
        }

    # ---- Q3: stability of the drop set under a seed swap -------------------
    rng_alt = np.random.default_rng(99)
    alt_score = 0.6 * norm_parent + 0.4 * rng_alt.random(n_parent)
    stability = {}
    for value, v in build.items():
        if SHIPPED[value][1] != "drop":
            continue
        k = int(round(n_parent * SHIPPED[value][2]))
        alt_dropped = np.zeros(n_parent, bool)
        alt_dropped[np.argsort(alt_score)[:k]] = True
        orig_dropped = np.zeros(n_parent, bool)
        orig_dropped[order_low_to_high[:k]] = True
        overlap = int((orig_dropped & alt_dropped).sum())
        stability[value] = {
            "n_dropped": k,
            "overlap_with_seed99": overlap,
            "jaccard_with_seed99": round(overlap / float((orig_dropped | alt_dropped).sum()), 3),
            "pearson_score_vs_alt": round(float(np.corrcoef(parent_score, alt_score)[0, 1]), 3),
            "verdict": (
                "unstable (<0.5 Jaccard: the ranking is majority noise)"
                if overlap / float((orig_dropped | alt_dropped).sum()) < 0.5
                else "stable"
            ),
        }

    # ---- Q4: alignment with an independent pinned model score --------------
    dv = dense[r0]
    prior = {}
    for value, v in build.items():
        if SHIPPED[value][1] != "drop":
            continue
        changed = v["_changed"]
        prior[value] = {
            "mean_dense_prior_dropped": round(float(dense[changed].mean()), 4),
            "mean_dense_prior_kept": round(float(dense[r0 & ~changed].mean()), 4),
            "parent_mean_dense_prior": round(float(dv.mean()), 4),
            "interpretation": (
                "dropped dots are NOT the low-prior dots"
                if float(dense[changed].mean()) >= float(dv.mean())
                else "dropped dots are lower-prior than the parent mean"
            ),
        }

    dti_ref = 0.2778
    bar = metric.marginal_inclusion_threshold(dti_ref)
    bar_px = float(metric.RADIUS_PX * (1.0 - bar))
    k_check = float(metric.kernel(np.array([bar_px]))[0])

    D0 = 18233.289656199096  # docs/evidence/GEMSDOE32__registry__submission_build.json
    dti_claim = dti_ref
    T0 = dti_claim * D0
    _require(abs(bar - metric.marginal_inclusion_threshold(dti_claim)) < 1e-12, "bar formula mismatch")

    sensitivity = {}
    for value, (sha8, op, frac) in SHIPPED.items():
        n_changed = int(round(n_parent * frac))

        def delta(c: float, _op: str = op, _n: int = n_changed) -> float:
            if _op == "drop":
                num, den = T0 - _n * c, D0 - 0.2 * _n
            else:
                num, den = T0 + _n * c, D0 + 0.2 * _n
            return round(float(num / den - dti_claim), 4)

        sensitivity[value] = {
            "operator": op,
            "n_changed": n_changed,
            "predicted_delta_if_credit_zero": delta(0.0),
            "predicted_delta_if_credit_half_bar": delta(bar / 2),
            "predicted_delta_if_credit_at_bar": delta(bar),
            "predicted_delta_if_credit_one": delta(1.0),
            "break_even_credit": round(float(bar), 4),
            "caveat": (
                "credit is to UNSEEN truth and is not observable; these are "
                "MODEL values conditional on a stated mean credit, not scores"
            ),
        }

    receipt = {
        "schema": "gems88.mass_ranking_audit.v1",
        "parent_sha256": PARENT_SHA,
        "parent_dots": n_parent,
        "ranking_as_built": "0.6*clip(d_catalogue_px/50,0,1) + 0.4*uniform(seed)",
        "q1_reconstruction": {
            "all_variants_reproduced": reconstructed_all,
            "detail": {
                k: {kk: vv for kk, vv in v.items() if kk != "_changed"} for k, v in build.items()
            },
        },
        "q2_what_the_ranking_ranks": confound,
        "q3_stability": stability,
        "q4_prior_alignment": prior,
        "marginal_gain_bar": {
            "dti_reference": dti_ref,
            "alpha_times_dti": round(float(bar), 4),
            "equivalent_catalogue_distance_px": round(bar_px, 2),
            "kernel_at_that_distance": round(k_check, 4),
            "note": (
                "a dot pays only if unseen truth lies within this distance; "
                "beyond it the dot is a fixed 0.2 denominator cost"
            ),
        },
        "catalogue_collar_baseline": {str(c): round(baseline[c], 3) for c in collar},
        "denominator_model": {
            "D0_from": "docs/evidence/GEMSDOE32__registry__submission_build.json (projected live-mirror build)",
            "D0": D0,
            "dti_claim": dti_claim,
            "T0_implied": round(float(T0), 1),
            "note": "D0 is a MODEL input from a prior projected build, not an organiser number",
        },
        "sensitivity": sensitivity,
    }

    if write_output:
        out = root / "registry" / "mass_ranking_audit.json"
        out.write_text(json.dumps(receipt, indent=1, allow_nan=False) + "\n")
        print(f"wrote {out.relative_to(root)}")

    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "q1_reconstruction",
                    "q2_what_the_ranking_ranks",
                    "q3_stability",
                    "q4_prior_alignment",
                    "marginal_gain_bar",
                    "sensitivity",
                )
            },
            indent=1,
            allow_nan=False,
        )
    )
    if not reconstructed_all:
        print("AUDIT FAIL: shipped MASS variants do not match the recorded ranking")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
