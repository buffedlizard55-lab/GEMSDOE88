"""Synthetic tests for H88-MFS scaling channels (no data files needed)."""
import numpy as np
import pytest

from gems88.mfs88 import (
    BREAK_CLIP,
    MFS_FEATURES,
    SLOPE_CLIP,
    SLOPE_W,
    clean_band,
    scaling_pair,
)


def test_slope_weight_is_exact_ls_for_log_spaced_scales():
    # LS slope for points (0, y1), (ln2, y2), (ln4, y3) weights middle point 0.
    x = np.log([1.0, 2.0, 4.0])
    y = np.array([0.3, -0.7, 1.9])
    ls = np.polyfit(x, y, 1)[0]
    assert ls == pytest.approx(SLOPE_W * (y[2] - y[0]), abs=1e-12)


def test_step_edge_has_discontinuity_scaling_exponent():
    # Measured physics: a step's smoothed-gradient peak decays ~1/sigma
    # (slope ~ -1, discrete estimate -0.85), a smooth ramp is scale-free
    # (slope ~ 0), white noise decays faster (~ -1.5). The channel separates
    # singularity classes; amplitude bands in the stack say where edges are.
    fp = np.ones((64, 64), bool)
    step = np.zeros((64, 64), np.float32)
    step[:, 32:] = 10.0
    yy, xx = np.mgrid[0:64, 0:64]
    ramp = (10.0 * xx / 63.0).astype(np.float32)
    s_step, _ = scaling_pair(step, fp)
    s_ramp, _ = scaling_pair(ramp, fp)
    edge = float(np.median(s_step[8:-8, 31:34]))
    interior = float(np.median(s_step[8:-8, 4:16]))
    ramp_mid = float(np.median(s_ramp[8:-8, 8:-8]))
    assert edge == pytest.approx(-0.85, abs=0.1)
    assert interior == pytest.approx(0.0, abs=0.05)
    assert ramp_mid == pytest.approx(0.0, abs=0.05)
    rng = np.random.default_rng(0)
    s_noise, _ = scaling_pair(rng.normal(0, 1, (64, 64)).astype(np.float32), fp)
    assert float(np.median(s_noise[8:-8, 8:-8])) < edge - 0.3
    for s in (s_step, s_ramp, s_noise):
        assert np.isfinite(s).all()
        assert s.min() >= SLOPE_CLIP[0] and s.max() <= SLOPE_CLIP[1]


def test_constant_field_is_finite_and_clipped():
    fp = np.ones((16, 16), bool)
    slope, break_ = scaling_pair(np.full((16, 16), 3.0, np.float32), fp)
    assert np.isfinite(slope).all() and np.isfinite(break_).all()
    assert break_.min() >= BREAK_CLIP[0] and break_.max() <= BREAK_CLIP[1]


def test_clean_band_fills_sentinels_with_footprint_median():
    fp = np.array([[1, 1], [1, 0]], bool)
    a = np.array([[1.0, np.nan], [3.0, 99.0]], np.float32)
    out = clean_band(a, fp)
    assert np.isfinite(out).all()
    assert out[0, 1] == 2.0  # median of finite footprint cells {1, 3}
    assert out[1, 1] == 2.0  # outside footprint -> same median


def test_feature_names_frozen():
    assert MFS_FEATURES == (
        "mfs_rtp_slope", "mfs_rtp_break",
        "mfs_grav_slope", "mfs_grav_break",
        "mfs_topo_slope", "mfs_topo_break",
    )


def test_mfs_runner_stops_before_imports_and_cannot_submit():
    """IR-88-B4DFA10C-07: historical disclosure does not authorize a bypass."""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "scripts/run_mfs88_experiment.py").read_text()
    assert src.index("enforce_generation_preflight()") < src.index("import numpy")
    # The historical runner body retains its original read-only proof record.
    assert src.index("guard_inspect(ROOT)") < src.index("build_or_load(ROOT")
    assert src.index("guard_inspect(ROOT)") < src.index("emit_regime(p")
    # ok_to_submit requires the literal uniqueness gate (and the holdout bar).
    assert "ok = bool(lane_pass and beats_repo_best and literal_pass" in src
    # The shared writer/evaluator are used; no private metric fork appears.
    assert "submission_writer.write_submission" in src
    assert "evaluate_holdout.evaluate" in src and "evaluate_holdout.pooled_summary" in src
