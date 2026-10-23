"""Unit tests for the new, single-axis PRUNE collar dose sweep."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_sweep_variants as sweep  # noqa: E402


def test_registered_sweep_is_unique_ordered_and_within_brief_change_range():
    specs = sweep.SPECS
    assert len(specs) == 3
    assert len({spec["value"] for spec in specs}) == 3
    assert [spec["threshold_px"] for spec in specs] == sorted(
        spec["threshold_px"] for spec in specs
    )
    assert all(spec["threshold_px"] > 3.0 for spec in specs)
    assert all(-1.0 <= spec["prediction_range"][0] <= spec["prediction"] <= spec["prediction_range"][1] <= 1.0
               for spec in specs)


def test_prune_at_threshold_keeps_count_and_enforces_threshold_only():
    parent = np.zeros((12, 12), dtype=bool)
    parent[2, 2] = True
    parent[4, 4] = True
    parent[7, 7] = True
    parent[9, 9] = True

    distance = np.full(parent.shape, 9.0, dtype=np.float32)
    distance[2, 2] = 2.5
    distance[4, 4] = 3.5
    distance[7, 7] = 5.0
    distance[9, 9] = 6.0
    support = np.ones(parent.shape, dtype=bool)
    weight = np.zeros(parent.shape, dtype=np.float32)
    weight[1:11, 1:11] = np.linspace(0.0, 1.0, 100, dtype=np.float32).reshape(10, 10)

    candidate, stats = sweep.prune_at_threshold(
        parent=parent,
        source_support=support,
        d_catalogue=distance,
        expected_fault_weight=weight,
        threshold_px=3.0,
    )

    assert int(candidate.sum()) == int(parent.sum()) == 4
    assert not np.any(candidate & (distance <= 3.0))
    assert stats["n_removed"] == stats["n_added"] == 1
    assert stats["pct_changed_moved"] == 25.0
    assert stats["pct_changed_symmetric_difference"] == 50.0
    assert stats["min_catalogue_distance_px"] > 3.0
    assert candidate[4, 4] and candidate[7, 7] and candidate[9, 9]


def test_threshold_refill_fails_closed_when_legal_source_pool_is_too_small():
    parent = np.zeros((6, 6), dtype=bool)
    parent[2, 2] = True
    distance = np.full(parent.shape, 5.0, dtype=np.float32)
    distance[2, 2] = 2.0
    support = np.zeros(parent.shape, dtype=bool)
    support[2, 2] = True  # not legal: this cell is inside the collar
    weight = np.zeros(parent.shape, dtype=np.float32)

    try:
        sweep.prune_at_threshold(parent, support, distance, weight, threshold_px=3.0)
    except ValueError as exc:
        assert "legal refill cells" in str(exc)
    else:
        raise AssertionError("insufficient legal refill pool must fail closed")
