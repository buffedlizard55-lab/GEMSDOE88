from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("scipy")

from gems88.mrr_coh import COH_FEATURES, axial_tensor, compute_coherence_features


def test_axial_tensor_constant_is_zero_and_finite():
    valid = np.ones((61, 67), dtype=bool)
    field = np.full(valid.shape, 3.25, dtype=np.float32)
    coh, qc, qs = axial_tensor(
        field, valid, source_sigma_px=2.0, tensor_sigma_px=6.0
    )
    assert np.isfinite(coh).all()
    assert np.isfinite(qc).all()
    assert np.isfinite(qs).all()
    assert float(coh.max()) == pytest.approx(0.0, abs=1e-6)


def test_axial_tensor_detects_straight_edge_more_than_isotropic_crossing():
    valid = np.ones((101, 101), dtype=bool)
    yy, xx = np.indices(valid.shape)
    straight = (xx >= 50).astype(np.float32)
    crossing = ((xx >= 50) | (yy >= 50)).astype(np.float32)
    c_line, _, _ = axial_tensor(
        straight, valid, source_sigma_px=1.5, tensor_sigma_px=6.0
    )
    c_cross, _, _ = axial_tensor(
        crossing, valid, source_sigma_px=1.5, tensor_sigma_px=6.0
    )
    assert float(c_line[50, 50]) > 0.90
    assert float(c_line[50, 50]) > float(c_cross[50, 50]) + 0.20


def test_coherence_features_contract_and_low_hg_suppression():
    valid = np.ones((81, 87), dtype=bool)
    _, xx = np.indices(valid.shape)
    residual = -np.exp(-0.5 * ((xx - 43.0) / 2.0) ** 2).astype(np.float32)
    trough = np.exp(-0.5 * ((xx - 43.0) / 2.0) ** 2).astype(np.float32)
    hg_low = np.ones(valid.shape, dtype=np.float32)
    low, meta = compute_coherence_features(residual, trough, hg_low, valid)
    assert len(low) == len(COH_FEATURES) == 4
    assert meta["pixel_size_m"] == 100
    assert all(a.shape == valid.shape and np.isfinite(a).all() for a in low)
    assert all(float(a.min()) >= 0.0 for a in low)
    # A spatially constant HG field is normalized by its own P95, so test a
    # locally dike-like high-HG stripe instead of comparing two global scales.
    hg_stripe = np.ones(valid.shape, dtype=np.float32)
    hg_stripe[:, 42:45] = 1000.0
    stripe, _ = compute_coherence_features(residual, trough, hg_stripe, valid)
    assert float(stripe[3][40, 43]) < float(low[3][40, 43])


def test_mrr_coherence_rejects_bad_contracts():
    a = np.zeros((10, 11), dtype=np.float32)
    with pytest.raises(ValueError):
        compute_coherence_features(a, a[:, :-1], a, np.ones_like(a, bool))
    with pytest.raises(ValueError):
        axial_tensor(a, np.ones_like(a, bool), source_sigma_px=0, tensor_sigma_px=1)
