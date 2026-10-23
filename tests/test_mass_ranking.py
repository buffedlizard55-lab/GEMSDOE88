"""Guards on the MASS-variant ranking audit (registry/mass_ranking_audit.json).

These tests do not judge whether the MASS experiments are wise.  They lock the
four facts that were measured, so that a future session cannot quietly restate
the ranking as "the parent's own ranking" again, and so that vectorised
reconstruction of the shipped files cannot drift.

They skip when the pinned inputs are absent (CI restores them first).
"""
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
H33 = ROOT / "data" / "registry" / "h33_education.tif"
EF = ROOT / "data" / "bridge" / "existing_faults.tif"
AUDIT = ROOT / "registry" / "mass_ranking_audit.json"

needs_inputs = pytest.mark.skipif(
    not (H33.exists() and EF.exists()),
    reason="restore pinned inputs via scripts/restore_inputs.py --validation",
)


@pytest.fixture(scope="module")
def ctx():
    with rasterio.open(H33) as s:
        r0 = s.read(1) > 0.5
    with rasterio.open(EF) as s:
        ef = s.read(1)
    cat = ef == 1
    return r0, cat, distance_transform_edt(~cat)


@pytest.fixture(scope="module")
def audit():
    return json.loads(AUDIT.read_text())


@needs_inputs
def test_audit_receipt_exists_and_reconstructs_shipped_files(audit):
    q1 = audit["q1_reconstruction"]
    assert q1["all_variants_reproduced"], "shipped MASS files no longer match the recipe"
    assert set(q1["detail"]) == {"MASSm10minus", "MASSm10plus", "MASSm20minus"}
    for value, d in q1["detail"].items():
        assert d["identical_to_on_disk"], value


@needs_inputs
def test_ranking_is_distance_to_catalogue_not_a_model_score(audit, ctx):
    """The recorded formula is 0.6*d_catalogue + 0.4*uniform, so a 'low-rank'
    drop is enriched for dots near the mapped catalogue.  Measured, not asserted
    from the source comment."""
    r0, cat, d_cat = ctx
    conf = audit["q2_what_the_ranking_ranks"]["MASSm10minus"]
    # The audit's own numbers must still hold against the live inputs.
    rng = np.random.default_rng(88)
    rows, cols = np.where(r0)
    score = 0.6 * np.clip(d_cat[r0] / 50.0, 0, 1) + 0.4 * rng.random(rows.size)
    k = int(round(r0.sum() * 0.10))
    drop = np.argsort(score)[:k]
    frac10 = float((d_cat[rows[drop], cols[drop]] <= 10).mean())
    base10 = float((d_cat[r0] <= 10).mean())
    assert frac10 == pytest.approx(conf["frac_dropped_within_px"]["10"], abs=0.005)
    assert frac10 > 2.0 * base10, "the drop must remain a near-catalogue deletion"
    assert conf["mean_dist_to_catalogue_px"] < conf["mean_dist_kept_px"]


@needs_inputs
def test_drop_set_is_majority_noise_under_a_seed_swap(audit):
    """40% of the ranking is uniform noise, so the drop set must not reproduce."""
    for value, s in audit["q3_stability"].items():
        assert s["jaccard_with_seed99"] < 0.5, value
        assert s["verdict"].startswith("unstable")


@needs_inputs
def test_dropped_dots_are_not_the_low_prior_dots(audit):
    """The mechanism cards claimed the dropped tail was low-prior.  It is not."""
    for value, p in audit["q4_prior_alignment"].items():
        assert p["mean_dense_prior_dropped"] > p["mean_dense_prior_kept"], value
        assert p["mean_dense_prior_dropped"] > p["parent_mean_dense_prior"], value


def test_marginal_bar_matches_the_metric_module(audit):
    """The audit must quote the bar from vendor metric code, not from prose."""
    from gems57 import metric

    bar = audit["marginal_gain_bar"]
    assert bar["alpha_times_dti"] == pytest.approx(metric.marginal_inclusion_threshold(0.2778), abs=1e-4)
    assert bar["equivalent_catalogue_distance_px"] == pytest.approx(
        metric.RADIUS_PX * (1.0 - metric.marginal_inclusion_threshold(0.2778)), abs=0.01
    )
