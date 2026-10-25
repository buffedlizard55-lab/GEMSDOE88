import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems88 import gcsd  # noqa: E402
from validate_gcsd88 import validate_gcsd88  # noqa: E402


def test_gcsd_feature_names_match_preregistration():
    assert len(gcsd.GCSD_FEATURES) == 12
    assert len(set(gcsd.GCSD_FEATURES)) == 12
    prereg = json.loads((ROOT / "registry/preregistration_gcsd88.json").read_text())
    assert list(gcsd.GCSD_FEATURES) == prereg["gcsd_12_channels"]


def test_hessian_trough_and_crest_synthetic_response():
    arr = np.zeros((48, 48), dtype=np.float32)
    arr[22:25, :] = -3.0  # linear magnetite-destructive RTP trough
    trough = gcsd._hessian_trough_2d(arr, sigma=1.5)
    assert np.isfinite(trough).all() and (trough >= 0.0).all()
    assert trough[23, 24] > trough[5, 24] + 0.5

    ridge = np.zeros((48, 48), dtype=np.float32)
    ridge[22:25, :] = 3.0  # linear hydrothermal-strike crest
    crest = gcsd._hessian_crest_2d(ridge, sigma=1.5)
    assert np.isfinite(crest).all() and (crest >= 0.0).all()
    assert crest[23, 24] > crest[5, 24] + 0.5


def test_tri_poe_pool_reliability_and_bounds():
    rng = np.random.default_rng(88)
    n = 256
    p_b = rng.uniform(0.01, 0.4, size=n).astype(np.float32)
    m_b = np.clip(p_b + 0.1, p_b, 1.0).astype(np.float32)
    p_v = rng.uniform(0.01, 0.5, size=n).astype(np.float32)
    m_v = np.clip(p_v + 0.1, p_v, 1.0).astype(np.float32)
    p_g = rng.uniform(0.01, 0.6, size=n).astype(np.float32)
    m_g = np.clip(p_g + 0.1, p_g, 1.0).astype(np.float32)
    d_vis = rng.uniform(3.0, 40.0, size=n).astype(np.float32)
    xg = rng.normal(0.0, 1.0, size=(n, 12)).astype(np.float32)

    p_out, m_out = gcsd.tri_poe_pool(p_b, m_b, p_v, m_v, p_g, m_g, d_vis_act=d_vis, x_gcsd_act=xg)
    assert np.isfinite(p_out).all() and np.isfinite(m_out).all()
    assert (p_out >= 0.0).all() and (p_out <= 1.0).all()
    assert (m_out >= p_out).all() and (m_out <= 1.0).all()


def test_gcsd88_independent_validator_and_fail_closed_gate():
    rep = validate_gcsd88(ROOT)
    assert rep["ok"] is True
    assert rep["lane"] == "H88-GCSD"
    assert rep["dots"] == 30000
    assert rep["share_gt25"] >= 0.40
    assert rep["share_le2"] == 0.0
    assert rep["holdout_dti"] > 0.200941
    assert rep["far_gt10px_dti"] > 0.131922
    assert rep["paired_delta_vs_adhr"]["delta"] > 0.0
    assert rep["paired_delta_vs_adhr"]["ci95"][0] > 0.0
    assert rep["worst_like_for_like_overlap_3px"] <= 0.70
    assert rep["unique_like_for_like"] is True
    assert rep["unique_literal"] is False
    assert rep["ok_to_download"] is True
    assert rep["ok_to_submit"] is False
    assert rep["verdict"] == "negative"

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_gcsd88.py"), "--require-submit"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    assert "DO NOT SUBMIT" in proc.stderr
