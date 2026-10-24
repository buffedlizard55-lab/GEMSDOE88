"""Synthetic, label-free invariants for the new MAG-FABRIC-DISLOCATION lane."""
import numpy as np
import pytest

from gems88.fabric_dislocation import axial_side_contrast, rank_footprint, build_surface
from gems57 import uniqueness


def test_pairwise_axial_azimuth_no_ghost_on_uniform_or_edge_wrap():
    fp = np.ones((35, 35), dtype=bool)
    qx = np.ones(fp.shape, np.float32)
    qy = np.zeros_like(qx)
    assert not np.any(axial_side_contrast(qx, qy, fp))
    # Same axial orientation after a 180-degree reversal is represented by the
    # same Q; rotating orientation 90 degrees reverses Q and is detected.
    qx[:, 18:] = -1
    contrast = axial_side_contrast(qx, qy, fp)
    assert contrast[17, 18] == pytest.approx(1.0)
    assert contrast[17, 5] == 0
    assert np.all(contrast[:, :3] == 0)
    assert np.all(contrast[:, -3:] == 0)
    fp[:, 19:] = False
    assert axial_side_contrast(qx, qy, fp)[17, 18] == 0


def test_rank_degenerate_and_input_fail_closed():
    valid = np.ones((8, 9), bool)
    raw = np.full(valid.shape, 7, np.float32)
    assert not rank_footprint(raw, valid).any()
    raw[0, 0] = 12
    assert rank_footprint(raw, valid)[0, 0] > rank_footprint(raw, valid)[1, 0]
    raw[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        rank_footprint(raw, valid)


def test_surface_is_label_blind_finite_and_masks_boundary():
    h, w = 70, 65
    fp = np.ones((h, w), bool)
    fp[:5] = False
    yy, xx = np.indices((h, w))
    rtp = (xx + 0.1 * yy + 8 * (xx > 30) * np.sin(yy / 4)).astype(np.float32)
    grav = (yy / 8 + 5 * (xx > 30)).astype(np.float32)
    rtp[3, 4] = -3.4028235e38  # Sentinel OUTSIDE footprint is not signal.
    a, channels, details = build_surface(rtp, grav, fp)
    assert a.shape == fp.shape and np.all(a[~fp] == 0)
    assert a.dtype == np.float32 and np.isfinite(a).all()
    assert 0 <= float(a.min()) <= float(a.max()) <= 1
    assert set(channels) == {"rtp_fabric_dislocation", "rtp_gradient_energy",
                             "gravity_gradient_energy", "fabric_gravity_surface"}
    assert details["tensor_epsilon"] > 0


def test_literal_dense_witness_forces_negative_no_exemption():
    # A probability surface with positive support everywhere makes every
    # nonempty dot raster a duplicate under the inherited *literal* rule.
    mine = np.zeros((11, 12), np.float32)
    mine[3, 4] = mine[7, 8] = 1
    prior = np.full_like(mine, 0.01)
    assert uniqueness.dot_overlap(mine, prior, 3) == 1.0
