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
cannot reconstruct the shipped files (so CI catches silent drift).

No catalogue geometry enters any *emitted* raster: this script only reads the
catalogue to measure the confound in files that already exist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(p: Path) -> np.ndarray:
    with rasterio.open(p) as src:
        return src.read(1)


def main() -> int:
    r0 = read(H33) > 0.5
    assert sha256(H33) == PARENT_SHA, "R0 hash mismatch -- re-run restore_inputs.py"
    ef = read(BRIDGE / "existing_faults.tif")
    catalogue = ef == 1
    footprint = (ef == 0) | (ef == 1)
    d_cat = distance_transform_edt(~catalogue)
    d_parent = d_cat[r0]
    n_parent = int(r0.sum())

    assert sha256(DENSE) == DENSE_SHA, "dense witness hash mismatch"
    dense = read(DENSE)
    finite_dense = np.isfinite(dense)
    assert finite_dense.all() or (finite_dense == footprint).all(), \
        "dense witness must be finite exactly on the footprint"
    assert (dense[finite_dense] >= 0).all() and (dense[finite_dense] <= 1).all(), \
        "dense witness must be a probability"

    rows, cols = np.where(r0)

    # ---- Q1: reconstruct the shipped ranking exactly ------------------------
    # Transcription of scripts/generate_axis_variants.py::make_variants.
    rng88 = np.random.default_rng(88)
    norm_parent = np.clip(d_parent / 50.0, 0.0, 1.0)
    parent_score = 0.6 * norm_parent + 0.4 * rng88.random(n_parent)
    order_low_to_high = np.argsort(parent_score)          # numpy sort: stable, ascending

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
        built = RELEASES / f"h33-h33-2-b2-{value}-20261023-{sha8}.tif"
        on_disk = read(built) > 0.5
        build[value] = {
            "release_present": built.is_file(),
            "reconstructed_sha8": sha8,
            "identical_to_on_disk": bool(np.array_equal(arr, on_disk)),
            "n_dots": int(arr.sum()),
            "frac_changed": round(float(
                (k / n_parent) if op == "drop" else ((arr.sum() - n_parent) / n_parent)
            ) * 100, 2),
            "_changed": (r0 & ~arr) if op == "drop" else (arr & ~r0),
        }

    reconstructed_all = all(v["identical_to_on_disk"] for v in build.values())

    # ---- Q2: what the ranking actually ranks -------------------------------
    # Fraction of the parent's dots inside a given catalogue collar, i.e. the
    # baseline a random drop would inherit.
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
            "frac_dropped_within_px": {
                str(c): round(float((dd <= c).mean()), 3) for c in collar
            },
            "baseline_frac_within_px": {str(c): round(baseline[c], 3) for c in collar},
            "enrichment_vs_random": {
                str(c): round(float((dd <= c).mean() / baseline[c]), 2)
                if baseline[c] > 0 else None for c in collar
            },
            "d_catalogue_saturates_at_50px_frac_of_parent": round(float((norm_parent >= 1.0).mean()), 3),
        }

    # ---- Q3: stability of the drop set under a seed swap -------------------
    rng_alt = np.random.default_rng(99)
    alt_score = 0.6 * norm_parent + 0.4 * rng_alt.random(n_parent)
    stability = {}
    for value, v in build.items():
        if SHIPPED[value][1] != "drop":
            continue
        k = int(round(n_parent * SHIPPED[value][2]))
        alt_keep = np.argsort(alt_score)[k:]
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
            "verdict": "unstable (<0.5 Jaccard: the ranking is majority noise)" if
                       overlap / float((orig_dropped | alt_dropped).sum()) < 0.5 else "stable",
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
            "interpretation": "dropped dots are NOT the low-prior dots"
            if float(dense[changed].mean()) >= float(dv.mean()) else
            "dropped dots are lower-prior than the parent mean",
        }

    # ---- marginal-gain bar, from the metric code (no fork) -----------------
    import sys
    sys.path.insert(0, str(ROOT / "vendor"))
    from gems57 import metric  # noqa: E402

    dti_ref = 0.2778
    bar = metric.marginal_inclusion_threshold(dti_ref)
    bar_px = float(metric.RADIUS_PX * (1.0 - bar))
    k_check = float(metric.kernel(np.array([bar_px]))[0])

    # ---- exact sensitivity of DTI to k changed dots ------------------------
    # Binary-dot algebra from vendor/gems57/metric.py:
    #   DTI = T / (alpha*(T + n - M) + beta*K),  alpha=0.2, beta=0.8
    # Removing one dot with realised credit c lowers the denominator by exactly
    # alpha regardless of c, so a removal gains iff c < alpha*DTI.
    # Adding one dot raises the denominator by exactly alpha, so an addition
    # gains iff c > alpha*DTI.  Both are exact, not approximations.
    # D is taken from the recorded live-mirror build for R0 (MODEL input, not a
    # score); T follows from the CLAIMED live DTI.
    D0 = 18233.289656199096          # docs/evidence/GEMSDOE32__registry__submission_build.json
    dti_claim = dti_ref
    T0 = dti_claim * D0
    assert abs(bar - metric.marginal_inclusion_threshold(dti_claim)) < 1e-12

    sensitivity = {}
    for value, (sha8, op, frac) in SHIPPED.items():
        n = build[value]["n_dots"]
        n_changed = int(round(n_parent * frac))
        def delta(c):
            if op == "drop":
                num, den = T0 - n_changed * c, D0 - 0.2 * n_changed
            else:
                num, den = T0 + n_changed * c, D0 + 0.2 * n_changed
            return round(float(num / den - dti_claim), 4)
        sensitivity[value] = {
            "operator": op,
            "n_changed": n_changed,
            "predicted_delta_if_credit_zero": delta(0.0),
            "predicted_delta_if_credit_half_bar": delta(bar / 2),
            "predicted_delta_if_credit_at_bar": delta(bar),
            "predicted_delta_if_credit_one": delta(1.0),
            "break_even_credit": round(float(bar), 4),
            "caveat": "credit is to UNSEEN truth and is not observable; these are "
                      "MODEL values conditional on a stated mean credit, not scores",
        }

    receipt = {
        "schema": "gems88.mass_ranking_audit.v1",
        "parent_sha256": PARENT_SHA,
        "parent_dots": n_parent,
        "ranking_as_built": "0.6*clip(d_catalogue_px/50,0,1) + 0.4*uniform(seed)",
        "q1_reconstruction": {
            "all_variants_reproduced": reconstructed_all,
            "detail": {k: {kk: vv for kk, vv in v.items() if kk != "_changed"}
                       for k, v in build.items()},
        },
        "q2_what_the_ranking_ranks": confound,
        "q3_stability": stability,
        "q4_prior_alignment": prior,
        "marginal_gain_bar": {
            "dti_reference": dti_ref,
            "alpha_times_dti": round(float(bar), 4),
            "equivalent_catalogue_distance_px": round(bar_px, 2),
            "kernel_at_that_distance": round(k_check, 4),
            "note": "a dot pays only if unseen truth lies within this distance; "
                    "beyond it the dot is a fixed 0.2 denominator cost",
        },
        "catalogue_collar_baseline": {str(c): round(baseline[c], 3) for c in collar},
        "denominator_model": {
            "D0_from": "docs/evidence/GEMSDOE32__registry__submission_build.json (projected live-mirror build)",
            "D0": D0, "dti_claim": dti_claim, "T0_implied": round(float(T0), 1),
            "note": "D0 is a MODEL input from a prior projected build, not an organiser number",
        },
        "sensitivity": sensitivity,
    }

    out = ROOT / "registry" / "mass_ranking_audit.json"
    out.write_text(json.dumps(receipt, indent=1) + "\n")

    print(json.dumps({k: receipt[k] for k in
                      ("q1_reconstruction", "q2_what_the_ranking_ranks",
                       "q3_stability", "q4_prior_alignment", "marginal_gain_bar",
                       "sensitivity")},
                     indent=1))
    print(f"wrote {out.relative_to(ROOT)}")
    if not reconstructed_all:
        print("AUDIT FAIL: shipped MASS variants do not match the recorded ranking")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
