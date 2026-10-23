"""Unit tests for the DTI algebra the CONCENTRATION argument rests on.

The brief asks for the algebra to be derived and unit-tested rather than quoted.
Everything here goes through the shared implementation in
``vendor/gems57/metric.py``; nothing is forked.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vendor.gems57 import metric  # noqa: E402


def _truth_and_dots():
    truth = np.zeros((24, 24), bool)
    truth[10, 4:20] = True                     # an 16-pixel fault trace
    truth[15, 14:18] = True                    # a short splay
    truth[6, 6] = True                         # an isolated pixel
    dots = np.zeros((24, 24), bool)
    dots[10, 4] = True
    dots[10, 8] = True
    dots[10, 12] = True
    dots[11, 12] = True                        # welded to the previous dot
    dots[15, 15] = True
    dots[2, 2] = True                          # far from everything
    return truth, dots


def test_binary_matches_bruteforce():
    truth, dots = _truth_and_dots()
    fast = metric.dti_binary(dots, truth)
    slow = metric.dti_bruteforce(dots.astype(float), truth)
    for key in ("tp", "fp", "fn"):
        assert abs(fast[key] - slow[key]) < 1e-9, (key, fast[key], slow[key])
    assert abs(fast["dti"] - slow["dti"]) < 1e-12


def test_soft_matches_bruteforce():
    truth, dots = _truth_and_dots()
    soft = dots.astype(float)
    soft[3, 3] = 0.4                           # fractional mass is allowed by the metric
    fast = metric.dti_exact(soft, truth)
    slow = metric.dti_bruteforce(soft, truth)
    for key in ("tp", "fp", "fn"):
        assert abs(fast[key] - slow[key]) < 1e-9
    assert abs(fast["dti"] - slow["dti"]) < 1e-12


def test_false_positive_term_equals_count_minus_self_credit():
    """FP_w = n - M with M = sum over dots of max_g k: the key CONCENTRATION identity."""
    truth, dots = _truth_and_dots()
    res = metric.dti_binary(dots, truth)
    dg = metric.kernel(__import__("scipy.ndimage", fromlist=["ndimage"]).distance_transform_edt(~truth))
    m = float(dg[dots].sum())
    assert abs(res["fp"] - (dots.sum() - m)) < 1e-9
    n = dots.sum()
    den = metric.ALPHA * (res["tp"] + n - m) + metric.BETA * truth.sum()
    assert abs(res["dti"] - res["tp"] / den) < 1e-12


def test_isolated_dot_pays_only_above_the_bar():
    """A lone dot around an isolated truth pixel raises DTI iff its credit > alpha*DTI."""
    truth = np.zeros((21, 21), bool)
    truth[10, 10] = True
    gained = []
    for d in (0.0, 1.0, 2.0, 3.0, 4.0):
        dots = np.zeros((21, 21), bool)
        dots[10 + int(d), 10] = True
        dti = metric.dti_binary(dots, truth)["dti"]
        gained.append((d, dti))
    # one truth cell, one dot: T = k, FP = FN = 1 - k, denominator = 1, so DTI == k
    # exactly.  Beyond the 3 px radius the dot earns nothing and DTI is 0.
    values = [v for _d, v in gained]
    assert np.allclose(values, [1.0, 2.0 / 3.0, 1.0 / 3.0, 0.0, 0.0])
    # the exact per-dot bar: adding a zero-credit dot must never help
    empty = metric.dti_binary(np.zeros((21, 21), bool), truth)["dti"]
    assert empty == 0.0
    assert metric.marginal_inclusion_threshold(0.2778) == 0.2 * 0.2778


def test_fixed_count_relocation_identity():
    """Moving one dot from empty ground next to a covering dot is a pure win when m_add > m_rm."""
    truth = np.zeros((40, 40), bool)
    truth[20, 5:35] = True
    base = np.zeros((40, 40), bool)
    base[20, 10] = True                        # sits on the trace
    donor_far = base.copy()
    donor_far[2, 2] = True                     # dropped in empty ground (m_rm = 0)
    welded = base.copy()
    welded[21, 10] = True                      # welded 1 px to the on-trace dot (m_add = 2/3)

    r_far = metric.dti_binary(donor_far, truth)
    r_weld = metric.dti_binary(welded, truth)
    assert donor_far.sum() == welded.sum() == 2   # fixed count, only the location moved
    dg = metric.kernel(__import__("scipy.ndimage", fromlist=["ndimage"]).distance_transform_edt(~truth))
    m_far, m_weld = float(dg[donor_far].sum()), float(dg[welded].sum())
    assert (m_far, round(m_weld, 6)) == (1.0, 1.666667)
    assert r_weld["dti"] > r_far["dti"]
    # and the gain is exactly the denominator relief the mechanism card claims
    assert r_far["tp"] == r_weld["tp"]         # no extra truth credit, only less penalty
    assert abs((r_far["fp"] - r_weld["fp"]) - (m_weld - m_far)) < 1e-9


def test_relocation_into_empty_ground_is_neutral_at_best():
    """Welding onto a dot that is nowhere near truth buys nothing: m_add = m_rm = 0."""
    truth = np.zeros((40, 40), bool)
    truth[20, 5:35] = True
    a = np.zeros((40, 40), bool)
    a[2, 2] = True
    a[2, 6] = True
    b = np.zeros((40, 40), bool)
    b[2, 2] = True
    b[3, 2] = True                             # welded, but both are far from truth
    ra, rb = metric.dti_binary(a, truth), metric.dti_binary(b, truth)
    assert abs(ra["dti"] - rb["dti"]) < 1e-12
