"""Dense-prior top-N is diagnostic only; literal uniqueness still blocks."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from gems57.uniqueness import equal_support_dots, dot_overlap, DENSE_POSITIVE_THRESHOLD


def test_equal_support_picks_top_n():
    a = np.arange(100, dtype=float).reshape(10, 10)
    dots = equal_support_dots(a, 5)
    assert dots.sum() == 5
    assert set(a[dots].tolist()) == {95.0, 96.0, 97.0, 98.0, 99.0}


def test_equal_support_is_only_diagnostic_and_literal_gate_still_stops():
    rng = np.random.default_rng(0)
    dense = rng.random((200, 200))  # >0 everywhere: literal overlap is 1.0
    cand = np.zeros((200, 200), np.float32)
    cand[::10, ::10] = 1.0
    support = equal_support_dots(dense, int((cand > 0).sum()))
    assert dot_overlap(cand, support.astype(np.float32)) < 0.70  # diagnostic only
    assert dot_overlap(cand, dense) == 1.0
    assert not (dot_overlap(cand, dense) <= 0.70)  # no exception to protocol


def test_threshold_constant():
    assert DENSE_POSITIVE_THRESHOLD == 200_000
