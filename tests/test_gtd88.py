"""Synthetic mechanism tests for H88-GTD (no competition data required)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems88 import gtd  # noqa: E402


@pytest.fixture()
def fp():
    return np.ones((120, 140), dtype=bool)


def _bands(field: np.ndarray) -> dict[str, np.ndarray]:
    z = np.zeros_like(field)
    return {
        "rtp": field.astype(np.float32),
        "iso_grav_anom": field.astype(np.float32),
        "depth_to_base_surf": field.astype(np.float32),
        "det_elev_slope": z.astype(np.float32),
    }


def test_straight_step_is_highly_linear(fp):
    # Vertical step along x=70: gradient is x-directed on the edge -> L ~ 1.
    f = np.zeros(fp.shape, np.float32)
    f[:, 70:] = 10.0
    t = gtd.structure_tensor(f, fp, 2.0)
    edge_lin = t["lin"][40:80, 66:75]
    assert float(np.median(edge_lin)) > 0.9
    # Energy concentrates on the edge, ~0 far away.
    assert float(t["energy"][60, 70]) > 5.0 * float(t["energy"][60, 20] + 1e-9)


def test_radial_bump_centre_is_equant(fp):
    yy, xx = np.mgrid[0: fp.shape[0], 0: fp.shape[1]]
    f = (10.0 * np.exp(-(((yy - 60) ** 2 + (xx - 70) ** 2) / (2 * 12.0**2)))).astype(np.float32)
    t = gtd.structure_tensor(f, fp, 2.0)
    # Exactly at the centre the radial gradient field is isotropic -> L ~ 0.
    # (On the flanks a smooth bump is locally step-like, so L rises there by
    # design; persistence/joint/mimic channels carry that distinction.)
    assert float(t["lin"][58:63, 68:73].max()) < 0.35
    # Two orthogonal plane waves: no dominant orientation anywhere.
    g = (np.sin(2 * np.pi * xx / 24.0) + np.sin(2 * np.pi * yy / 24.0)).astype(np.float32)
    tg = gtd.structure_tensor(g, fp, 2.0)
    assert float(np.median(tg["lin"][30:90, 30:110])) < 0.45


def test_plane_wave_orientation_and_agreement(fp):
    yy, xx = np.mgrid[0: fp.shape[0], 0: fp.shape[1]]
    f = np.sin(2 * np.pi * xx / 24.0).astype(np.float32)  # gradient along x
    t = gtd.structure_tensor(f, fp, 2.0)
    core = t["lin"][30:90, 30:110]
    assert float(np.median(core)) > 0.85


def test_build_channels_shapes_finite_and_joint_on_step(fp):
    f = np.zeros(fp.shape, np.float32)
    f[:, 70:] = 10.0
    chans = gtd.build_gtd_channels(_bands(f), fp)
    assert len(chans) == len(gtd.GTD_FEATURES) == 14
    for ch in chans:
        assert ch.shape == fp.shape and ch.dtype == np.float32
        assert np.isfinite(ch).all()
    joint = chans[gtd.GTD_FEATURES.index("gtd_joint_step")]
    # Joint step peaks on the synthetic fault-like step, not in flat terrain.
    assert float(joint[60, 66:75].max()) > float(joint[60, 5:20].max()) + 0.5
    agree = chans[gtd.GTD_FEATURES.index("gtd_agree_rtp_grav")]
    assert float(np.median(agree[40:80, 66:75])) > 0.5  # identical fields agree


def test_channels_zero_outside_footprint():
    fp = np.zeros((80, 90), dtype=bool)
    fp[10:70, 10:80] = True
    f = np.random.default_rng(0).normal(size=fp.shape).astype(np.float32)
    chans = gtd.build_gtd_channels(_bands(f), fp)
    for ch in chans:
        assert (ch[~fp] == 0.0).all()
        assert np.isfinite(ch).all()


def test_proximity_discount_bounds_and_monotonicity():
    dots = np.zeros((50, 50), dtype=bool)
    dots[25, 25] = True
    w = gtd.proximity_discount(dots, w_min=0.55)
    assert float(w.min()) >= 0.55 and float(w.max()) <= 1.0
    assert float(w[25, 25]) == pytest.approx(0.55)
    assert float(w[25, 40]) == pytest.approx(1.0)  # 15 px away: no discount
    # d=1 -> 0.70, d=2 -> 0.85, d>=3 -> 1.0 (kernel-radius boundary)
    assert float(w[25, 26]) == pytest.approx(0.70, abs=0.01)
    assert float(w[25, 27]) == pytest.approx(0.85, abs=0.01)
    assert float(w[25, 26]) < float(w[25, 27])
    assert float(w[25, 27]) < float(w[25, 28])
    assert float(w[25, 28]) == pytest.approx(1.0)


def test_feature_names_match_preregistration():
    import json

    prereg = json.loads((ROOT / "registry/preregistration_gtd88.json").read_text(encoding="utf-8"))
    assert list(gtd.GTD_FEATURES) == prereg["gtd14_features"]
    assert prereg["frozen_before_feature_canary_holdout_or_production_build"] is True
