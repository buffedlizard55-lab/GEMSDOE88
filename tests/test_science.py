import numpy as np
import pytest
from scipy.ndimage import binary_dilation
from gems57 import metric, evaluate_holdout
from gems57.uniqueness import _near, dot_overlap
from gems88.edge import coedge_features, clean_band
from gems88.model import spaced_dots, leakage_canaries


def test_official_kernel_and_example():
    # The organiser's published worked example rounds to 0.60.
    assert metric.dti_from_components(3.0, 1.89, 2.0) == pytest.approx(
        3 / (3 + 0.2 * 1.89 + 0.8 * 2)
    )
    assert round(metric.dti_from_components(3.0, 1.89, 2.0), 2) == 0.60
    g = np.zeros((13, 13), bool)
    g[6, 6] = True
    p = np.zeros((13, 13), np.float32)
    p[6, 7] = 1
    fast = metric.dti_exact(p, g)
    slow = metric.dti_bruteforce(p, g)
    for key in ("tp", "fp", "fn", "dti"):
        assert fast[key] == pytest.approx(slow[key])
    assert fast["tp"] == pytest.approx(2 / 3)


def test_nan_and_sentinel_are_not_gradient_lineaments():
    a = np.full((15, 15), 8.0, np.float32)
    a[7, 7] = -3.402823e38
    a[2, 2] = np.nan
    fp = np.ones_like(a, bool)
    filled, stats = clean_band(a, fp)
    assert stats["invalid_inside"] == 2
    assert np.isfinite(filled).all()
    assert np.all(filled == 8)
    a, b, c, d = coedge_features(
        np.zeros((4, 4)), np.ones((4, 4)), np.ones((4, 4)), np.zeros((4, 4))
    )
    assert np.all(c == 0) and np.all(d == 0)  # orthogonal signed edges
    assert np.isfinite(a).all() and np.isfinite(b).all()


def test_deterministic_spaced_emission_and_range_rejection():
    p = np.arange(20 * 20, dtype=np.float32).reshape(20, 20) / 400
    a, info = spaced_dots(p, np.ones_like(p, bool), budget=20, radius=2, tie=p)
    b, _ = spaced_dots(p, np.ones_like(p, bool), budget=20, radius=2, tie=p)
    np.testing.assert_array_equal(a, b)
    assert a.sum() == 20 and info["requested"] == 20
    from scipy.spatial.distance import pdist

    assert np.min(pdist(np.argwhere(a))) > 2 - 1e-9
    with pytest.raises(ValueError, match="out of range"):
        spaced_dots(np.full((10, 10), 1.01), np.ones((10, 10), bool), 3)


def test_literal_overlap_no_exemptions():
    all_positive = np.ones((11, 11), bool)
    scattered = np.zeros((11, 11), bool)
    scattered[5, 5] = 1
    assert dot_overlap(scattered, all_positive, 3.0) == 1
    # The shared exact Euclidean circle is not a square dilation.
    expected = binary_dilation(
        scattered,
        structure=(
            np.fromfunction(lambda y, x: (y - 3) ** 2 + (x - 3) ** 2 <= 9, (7, 7))
        ),
    )
    np.testing.assert_array_equal(_near(scattered, 3), expected)


def test_symmetric_canary_fires_on_leaked_label_feature():
    h, w = 25, 25
    truth = np.zeros((h, w), bool)
    truth[5:9, 5:9] = 1
    feature = truth.astype(np.float32).reshape(-1, 1)
    region = np.ones_like(truth, bool)
    fold = dict(region=region, truth=truth, masked_known=np.zeros_like(truth))
    r = leakage_canaries(feature, ["smuggled_hidden_truth"], [fold], region)
    assert r[0]["symmetric_auc"] == 1
    assert r[0]["symmetric_auc"] > 0.90


def test_pooled_terms_need_paired_truth_counts():
    a = np.array([[1.0, 2.0, 3.0, 4.0], [0.0, 1.0, 1.0, 1.0]])
    b = a.copy()
    b[0, 3] = 5
    with pytest.raises(ValueError, match="same integer truth count"):
        evaluate_holdout.pooled_summary(
            {"candidate": a, "raw_control": b}, draws=20, candidate="candidate"
        )


def test_cgo_features_masking_and_finite_output():
    from evaluate_cgo88 import cgo_features

    fp = np.zeros((25, 25), bool)
    fp[3:22, 3:22] = True
    yy, xx = np.indices((25, 25), dtype=np.float32)
    grav = np.tanh((xx - 12.0) / 2.0).astype(np.float32)
    cond = np.tanh((xx - 14.0) / 2.0).astype(np.float32)
    log_g, log_c, cgo_off, cgo_asym = cgo_features(grav, cond, fp, step_px=2.0)
    for arr in (log_g, log_c, cgo_off, cgo_asym):
        assert np.isfinite(arr).all()
        assert np.all(arr[~fp] == 0.0)
    assert cgo_off[12, 12] > 0.0
    with pytest.raises(ValueError, match="invalid shape or step_px"):
        cgo_features(grav, cond, fp, step_px=0.0)
    with pytest.raises(ValueError, match="invalid shape or step_px"):
        cgo_features(grav[:10, :10], cond, fp, step_px=2.0)
