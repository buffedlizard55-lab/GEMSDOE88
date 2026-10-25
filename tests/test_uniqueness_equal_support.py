"""IR-88-SDTL-01: equal-support dot definition for continuous registry surfaces."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from gems57 import uniqueness  # noqa: E402


def _grid(h=60, w=60):
    allowed = np.ones((h, w), bool)
    allowed[:, :5] = False  # a strip outside the allowed domain
    return allowed


def test_dot_field_registry_keeps_literal_support():
    allowed = _grid()
    theirs = np.zeros(allowed.shape, np.float32)
    theirs[10, 10] = theirs[30, 30] = 1.0
    mask, info = uniqueness.registry_dots(theirs, allowed, n_candidate_dots=50)
    assert info["kind"] == "dot_field"
    assert mask.sum() == 2 and mask[10, 10] and mask[30, 30]


def test_dense_surface_is_compared_through_its_top_n_cells():
    allowed = _grid()
    rng = np.random.default_rng(0)
    theirs = rng.uniform(0.01, 0.5, allowed.shape).astype(np.float32)
    theirs[20:25, 20:25] = 0.99  # the surface's own strongest cells
    mask, info = uniqueness.registry_dots(theirs, allowed, n_candidate_dots=25)
    assert info["kind"] == "continuous_surface"
    assert info["their_dots"] == 25
    assert mask[20:25, 20:25].all()
    # top-n cells never leave the allowed domain
    assert not mask[~allowed].any()


def test_candidate_thresholded_from_dense_surface_still_fails():
    allowed = _grid()
    rng = np.random.default_rng(1)
    theirs = rng.uniform(0.01, 0.5, allowed.shape).astype(np.float32)
    theirs[40:50, 40:50] = 0.90
    theirs[42:47, 42:47] = 0.99  # the 25 strongest cells
    mine = np.zeros(allowed.shape, np.float32)
    mine[40:50:2, 40:50:2] = 1.0  # 25 dots emitted from the same hot block
    ov, info = uniqueness.equal_support_overlap(mine, theirs, allowed)
    assert info["kind"] == "continuous_surface"
    assert ov > 0.70


def test_candidate_from_different_physics_passes_dense_surface():
    allowed = _grid()
    rng = np.random.default_rng(2)
    theirs = rng.uniform(0.01, 0.5, allowed.shape).astype(np.float32)
    theirs[40:50, 40:50] = 0.95
    mine = np.zeros(allowed.shape, np.float32)
    mine[8:18:2, 8:18:2] = 1.0  # 25 dots far from the surface's top cells
    ov, _ = uniqueness.equal_support_overlap(mine, theirs, allowed)
    literal = uniqueness.dot_overlap(mine, theirs)
    assert literal == 1.0  # the literal reading fires on everything
    assert ov <= 0.70


def test_v5_decision_fails_closed_on_unreadable_raster(tmp_path):
    allowed = _grid()
    mine = np.zeros(allowed.shape, np.float32)
    mine[8, 8] = 1.0
    bad = tmp_path / "missing.tif"
    out = uniqueness.binding_duplicate_decision_v5(mine, [("missing", bad)], allowed, allowed)
    assert out["stop_required"] is True and out["errors"]
