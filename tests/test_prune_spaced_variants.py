"""Unit tests for the spacing-locked (non-densifying) PRUNE refill arms."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_spaced_variants as bps  # noqa: E402


def test_registered_arms_are_unique_gate_clean_and_inside_the_brief():
    specs = bps.SPECS
    assert len(specs) == 3
    assert len({spec["value"] for spec in specs}) == 3
    assert all(spec["collar_px"] >= 3.0 for spec in specs)
    assert sum(1 for spec in specs if not spec["refill"]) == 1
    assert all(spec["spacing_px"] is None or spec["spacing_px"] >= 3.5 for spec in specs)
    for spec in specs:
        lo, hi = spec["prediction_range"]
        assert -1.0 <= lo <= spec["prediction"] <= hi <= 1.0


def _synthetic_grid():
    """Survivors left/right, a refill corridor between them, plenty of slack."""
    shape = (24, 40)
    base = np.zeros(shape, dtype=bool)
    base[4, 2] = base[4, 37] = base[20, 2] = base[20, 37] = True
    support = np.zeros(shape, dtype=bool)
    support[3:22, 6:34] = True
    weight = np.zeros(shape, dtype=np.float32)
    weight[8:16, 6:34] = 1.0
    distance = np.full(shape, 9.0, dtype=np.float32)
    return base, support, distance, weight


def test_spaced_refill_holds_count_and_respects_the_spacing_lock():
    base, support, _, weight = _synthetic_grid()
    n_add = 8
    filled, stats = bps.spaced_marginal_add(
        base_mask=base, cand_mask=support, w=weight, n_add=n_add, spacing_px=3.5
    )
    assert filled.sum() == base.sum() + n_add
    points = np.argwhere(filled)
    nn = cKDTree(points).query(points, k=2)[0][:, 1]
    assert nn.min() >= 3.5 - 1e-9, "refill dots must stay >= spacing from every dot"
    assert stats["filled"] == n_add and stats["spacing_px"] == 3.5


def test_spaced_refill_fails_closed_when_the_pool_cannot_hold_the_count():
    shape = (8, 8)
    base = np.zeros(shape, dtype=bool)
    base[0, 0] = True
    support = np.zeros(shape, dtype=bool)
    support[1:3, 1:3] = True  # all inside a 3.5 px ball of the single survivor
    weight = np.zeros(shape, dtype=np.float32)
    try:
        bps.spaced_marginal_add(base, support, weight, n_add=1, spacing_px=3.5)
    except ValueError as exc:
        assert "refill cells" in str(exc)
    else:
        raise AssertionError("an impossible spacing lock must fail closed")


def test_build_arm_drops_only_the_collar_when_refill_is_off():
    base, support, distance, weight = _synthetic_grid()
    spec = {"value": "norefill", "collar_px": 3.0, "refill": False, "spacing_px": None}
    try:
        bps.build_arm(base, support, distance, weight, spec)
    except ValueError as exc:
        assert "no parent dots" in str(exc)
    else:
        raise AssertionError("an empty collar edit must fail closed")

    tight = distance.copy()
    tight[4, 2] = 2.5  # one survivor now sits inside the collar
    out2, stats2 = bps.build_arm(base, support, tight, weight, spec)
    assert out2.sum() == base.sum() - 1
    assert stats2["n_removed"] == 1 and stats2["n_added"] == 0
    assert not out2[4, 2]


def test_build_arm_refills_to_the_parent_count_without_densifying():
    base, support, distance, weight = _synthetic_grid()
    tight = distance.copy()
    tight[4, 2] = 2.5
    spec = {"value": "spaced", "collar_px": 3.0, "refill": True, "spacing_px": 3.5}
    out, stats = bps.build_arm(base, support, tight, weight, spec)
    assert out.sum() == base.sum()
    assert stats["n_removed"] == stats["n_added"] == 1
    assert stats["refill_min_nn_px"] >= 3.5 - 1e-9
    assert not out[4, 2]
