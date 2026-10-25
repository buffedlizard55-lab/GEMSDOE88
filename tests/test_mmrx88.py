"""H88-MMRX synthetic mechanism tests + representation-aware uniqueness v4 tests.

The synthetic marker is geologically faithful in the one way that matters for
restoration: magnetic anomalies *elongated across* the candidate fault are
recorded on both walls, and the hanging-wall copy is displaced along strike.
Isotropic short-correlation texture is *not* a valid marker (it decorrelates
across the 800 m strip gap), which these tests also document via the control.
"""
import numpy as np
import pytest
from scipy import ndimage as ndi

from gems57 import uniqueness
from gems88 import mmrx


def _synthetic(roll_px: int):
    rng = np.random.default_rng(11)
    tex = ndi.gaussian_filter(
        rng.standard_normal((280, 280)).astype(np.float32), sigma=(2.0, 9.0)).astype(np.float32)
    rtp = tex.copy()
    if roll_px:
        rtp[:, 140:] = np.roll(tex, roll_px, axis=0)[:, 140:]
    rtp = (rtp + 0.10 * ndi.gaussian_filter(
        rng.standard_normal((280, 280)).astype(np.float32), sigma=(1, 1))).astype(np.float32)
    grav = ndi.gaussian_filter(rtp, sigma=(2, 2)).astype(np.float32)
    depth = np.repeat(np.linspace(0, 1000, 280, dtype=np.float32)[None, :], 280, axis=0)
    return rtp, grav, depth, np.ones((280, 280), bool)


def test_displaced_cross_fault_marker_restores():
    ch = mmrx.marker_restoration_channels(*_synthetic(3))
    sl = slice(50, 230)
    gain_line = float(np.median(ch["mmrx_rtp_gain"][sl, 138:142]))
    gain_away = float(np.median(ch["mmrx_rtp_gain"][sl, 50:90]))
    assert gain_line > gain_away + 0.15
    # undisplaced correlation collapses on the fault; displacement restores it
    assert float(np.median(ch["mmrx_rtp_corr0"][sl, 138:142])) < float(np.median(ch["mmrx_rtp_corr_best"][sl, 138:142])) - 0.2


def test_no_fault_control_gain_is_lower():
    fault = mmrx.marker_restoration_channels(*_synthetic(3))
    ctrl = mmrx.marker_restoration_channels(*_synthetic(0))
    sl = slice(50, 230)
    g_fault = float(np.median(fault["mmrx_rtp_gain"][sl, 138:142]))
    g_ctrl = float(np.median(ctrl["mmrx_rtp_gain"][sl, 138:142]))
    assert g_fault > g_ctrl + 0.08


def test_channels_finite_and_complete_on_flat_fields():
    flat = np.ones((60, 60), np.float32)
    depth = np.repeat(np.arange(60, dtype=np.float32)[None, :], 60, axis=0)
    ch = mmrx.marker_restoration_channels(flat, flat, depth, np.ones((60, 60), bool))
    assert list(ch) == list(mmrx.MMRX_FEATURES)
    assert all(np.isfinite(v).all() for v in ch.values())


def test_geometry_normal_points_toward_deeper_basement():
    rng = np.random.default_rng(3)
    field = ndi.gaussian_filter(rng.standard_normal((120, 120)).astype(np.float32), 3).astype(np.float32)
    depth = np.repeat(np.linspace(0, 500, 120, dtype=np.float32)[None, :], 120, axis=0)  # deepens eastward
    fp = np.ones((120, 120), bool)
    tx, ty, nx, ny, coh = mmrx.compute_geometry(field, field, depth, fp)
    # depth gradient is +x everywhere, so the signed normal must have nx > 0
    assert float(np.median(nx)) > 0.5
    # t is the strike: perpendicular to n
    assert np.max(np.abs(tx * nx + ty * ny)) < 1e-5
    assert np.all((coh >= 0) & (coh <= 1))


# --- uniqueness v4 ---------------------------------------------------------

def _row(**kw):
    base = {"file": "x.tif", "forward_overlap": 0.1, "spearman": 0.2,
            "is_continuous_surface": False, "topn_overlap": None}
    base.update(kw)
    return base


def test_v4_random_dots_vs_dense_surface_pass_but_v3_fails():
    rows = [_row(file="dense_proba.tif", forward_overlap=1.0, spearman=-0.001,
                 is_continuous_surface=True, topn_overlap=0.016)]
    diag = uniqueness._representation_aware_diagnostics_v4(rows)
    v4 = uniqueness.binding_duplicate_decision_v4(rows)
    assert diag["verdict"] == "promote"
    assert diag["worst_effective_dot_overlap"] == 0.016
    assert v4["worst_effective_dot_overlap"] == 0.016
    assert v4["worst_literal_forward_overlap"] == 1.0  # literal still reported
    assert v4["representation_aware_binding"] is False
    assert v4["policy_correction"] == "IR-88-78CFB743-01"
    assert v4["verdict"] == "negative"  # public v4 delegates binding verdict to literal v3
    assert v4["duplicate"] is True and v4["stop_required"] is True
    assert v4["literal_v3"]["verdict"] == "negative"



def test_v4_copy_of_dense_topn_blocks():
    rows = [_row(file="dense_proba.tif", forward_overlap=1.0, spearman=0.95,
                 is_continuous_surface=True, topn_overlap=1.0)]
    assert uniqueness.binding_duplicate_decision_v4(rows)["verdict"] == "negative"


def test_v4_sparse_dot_overlap_still_binds_literally():
    rows = [_row(file="sparse.tif", forward_overlap=0.85)]
    assert uniqueness.binding_duplicate_decision_v4(rows)["verdict"] == "negative"
    rows = [_row(file="sparse.tif", forward_overlap=0.5)]
    assert uniqueness.binding_duplicate_decision_v4(rows)["verdict"] == "promote"


def test_v4_missing_topn_for_continuous_fails_closed():
    rows = [_row(file="dense_proba.tif", forward_overlap=1.0, spearman=0.0,
                 is_continuous_surface=True, topn_overlap=None)]
    v4 = uniqueness.binding_duplicate_decision_v4(rows)
    assert v4["verdict"] == "negative" and v4["invalid_measurements"]


def test_v4_rho_binds_dense_and_sparse_alike():
    rows = [_row(file="dense_proba.tif", forward_overlap=1.0, spearman=-0.97,
                 is_continuous_surface=True, topn_overlap=0.01)]
    assert uniqueness.binding_duplicate_decision_v4(rows)["verdict"] == "negative"


def test_v4_empty_rows_fail_closed():
    assert uniqueness.binding_duplicate_decision_v4([])["verdict"] == "negative"
