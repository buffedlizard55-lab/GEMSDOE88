from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from gems88.mrr import MRR_FEATURES, StackedFeatureView, compute_mrr_features  # noqa: E402


def synthetic_fields(shape=(230, 260), seed=88):
    rng = np.random.default_rng(seed)
    yy, xx = np.indices(shape, dtype=np.float32)
    valid = np.ones(shape, dtype=bool)
    valid[:8, :] = False
    valid[:, :5] = False
    tmi = 0.4 * xx + 0.2 * yy + 15 * np.sin(xx / 37.0)
    mag = 0.7 * tmi + 8 * np.cos(yy / 29.0)
    # Local relation plus a planted narrow negative residual corridor.
    vg = 0.025 * tmi - 0.011 * mag + rng.normal(0, 0.4, shape)
    corridor = np.abs(xx - (0.45 * yy + 70.0)) < 2.0
    vg[corridor] -= 5.0
    rtp = 0.8 * tmi + 3.0 * np.sin((xx + yy) / 13.0)
    depth = 200.0 + 4.0 * yy
    return [a.astype(np.float32) for a in (mag, rtp, vg, tmi, depth)], valid, corridor


def test_mrr_features_are_deterministic_finite_and_catalogue_independent():
    bands, valid, corridor = synthetic_fields()
    f1, meta1 = compute_mrr_features(*bands, valid, block_side_px=50)
    f2, meta2 = compute_mrr_features(*bands, valid, block_side_px=50)
    assert len(f1) == len(MRR_FEATURES) == 4
    assert meta1 == meta2
    for a, b in zip(f1, f2):
        assert a.shape == valid.shape and a.dtype == np.float32
        assert np.isfinite(a).all()
        assert np.array_equal(a, b)
        assert np.all(a[~valid] == 0)
    # The signed residual must respond more negatively on the planted corridor.
    assert float(np.median(f1[0][corridor & valid])) < float(np.median(f1[0][valid]))
    assert meta1["block_side_px"] == 50
    assert meta1["populated_blocks"] > 1


def test_mrr_rejects_invalid_inputs():
    bands, valid, _ = synthetic_fields((80, 90))
    bad = bands[0].copy()
    bad[valid] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        compute_mrr_features(bad, *bands[1:], valid, block_side_px=40)
    with pytest.raises(ValueError, match="invalid"):
        compute_mrr_features(*bands, valid, block_side_px=0)


def test_stacked_feature_view_matches_horizontal_stack():
    a = np.arange(30, dtype=np.float32).reshape(10, 3)
    b = np.arange(20, dtype=np.float32).reshape(10, 2) + 100
    view = StackedFeatureView([a, b])
    expected = np.hstack([a, b])
    assert view.shape == (10, 5)
    np.testing.assert_array_equal(view[[1, 7, 3]], expected[[1, 7, 3]])
    np.testing.assert_array_equal(view[2:6], expected[2:6])
    np.testing.assert_array_equal(view[4], expected[[4]])
    np.testing.assert_array_equal(view[[2, 5], 1:4], expected[[2, 5], 1:4])
