import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt

from gems57 import metric
from gems88.r0_prune import bfs_order, dot_thin_from_order, prune3_refill
from run_r0_prune import canary_report


def test_recorded_bfs_thinning_on_unit_line():
    support = np.ones((1, 10), dtype=bool)
    padded, order, pad = bfs_order(support)
    thinned = dot_thin_from_order(padded, order, pad)
    np.testing.assert_array_equal(np.argwhere(thinned), np.array([[0, 0], [0, 3], [0, 6], [0, 9]]))


def test_prune3_refill_is_fixed_count_and_only_changes_collar():
    r0 = np.zeros((9, 9), dtype=bool)
    r0[2, 2] = r0[2, 5] = r0[5, 2] = r0[5, 5] = True
    d_cat = np.full((9, 9), 4.0)
    d_cat[2, 5] = 2.0
    support = np.ones((9, 9), dtype=bool)
    candidate, removed, added, stats = prune3_refill(r0, support, d_cat, n_dots=4)
    assert candidate.sum() == 4
    assert removed.sum() == added.sum() == 1
    assert removed[2, 5]
    assert candidate[2, 2] and candidate[5, 2] and candidate[5, 5]
    assert np.all(d_cat[candidate] > 3)
    assert not np.any(added & ~support)
    assert not np.any(added & r0)
    assert stats["pct_parent_dots_changed"] == 25.0


def test_prune3_refill_requires_enough_legal_support():
    r0 = np.zeros((5, 5), dtype=bool)
    r0[2, 2] = True
    d_cat = np.full((5, 5), 4.0)
    d_cat[2, 2] = 2.0
    with pytest.raises(ValueError, match="only 0 legal refill"):
        prune3_refill(r0, r0.copy(), d_cat, n_dots=1)


def test_binary_dti_algebra_matches_metric_components():
    truth = np.zeros((11, 11), dtype=bool)
    truth[3, 4] = truth[8, 8] = True
    pred = np.zeros((11, 11), dtype=bool)
    pred[3, 5] = pred[1, 1] = pred[8, 9] = True
    result = metric.dti_binary(pred, truth)
    d_g = distance_transform_edt(~truth)
    T = result["tp"]
    S = float(pred.sum())
    M = float(metric.kernel(d_g[pred]).sum())
    G = float(truth.sum())
    algebraic = T / (0.2 * T + 0.2 * (S - M) + 0.8 * G + metric.EPS)
    assert result["dti"] == pytest.approx(algebraic, rel=1e-12, abs=1e-12)


def test_canary_retains_invalidated_full_catalogue_check():
    footprint = np.ones((20, 20), dtype=bool)
    visible = np.zeros((20, 20), dtype=bool)
    visible[8:12, 5] = True
    hidden = np.zeros((20, 20), dtype=bool)
    hidden[8:12, 10] = True
    fold = dict(region=footprint, truth=hidden, masked_known=visible, visible=visible)
    d_full = distance_transform_edt(~(visible | hidden))
    report = canary_report(np.zeros((20, 20), np.float32), [fold], footprint, d_full)
    assert report["invalidated_full_catalogue_distance_check"]["symmetric_auc"] == 1.0
    assert report["rows"][0]["feature"] == "fold_visible_catalogue_distance_px"


def test_isolated_truth_dot_credit_bar_uses_exact_marginal_rule():
    # A non-redundant dot helps exactly when dT=k exceeds alpha*current DTI.
    # T=28, M=28, S=100, |G|=100 gives current DTI exactly 0.28.
    assert 28 / (0.2 * (28 + 100 - 28) + 0.8 * 100) == pytest.approx(0.28)
    assert not metric.marginal_accept(dT=0.055, k_self=0.055, T=28, M=28, n=100, K=100)
    assert metric.marginal_accept(dT=0.057, k_self=0.057, T=28, M=28, n=100, K=100)
