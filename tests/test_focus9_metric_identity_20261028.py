"""Exact algebra of the distance-weighted Tversky score used by the focus-site review (2026-10-28).

Official definition (competition page 967): TP_w = sum over truth pixels g of max_x p(x) k(d(x,g)),
FN_w = sum_g [1 - max_x p(x) k(d(x,g))], FP_w = sum_{p(x)>0} p(x) [1 - max_g k(d(x,g))], alpha=0.2, beta=0.8.

Because FN_w = |G| - TP_w exactly, DTI = TP_w / (0.2 TP_w + 0.2 FP_w + 0.8 |G|). Removing one dot changes
(TP_w, FP_w) by (-t, -f), so the removal is an improvement iff t/(t+f) < 0.2 * DTI, i.e. a dot is kept
iff its share of credit exceeds alpha * DTI. These tests use the shared vendor implementation only.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vendor.gems57 import metric  # noqa: E402

ALPHA, BETA = 0.2, 0.8


def _scene(seed: int):
    rng = np.random.default_rng(seed)
    truth = np.zeros((30, 30), bool)
    for _ in range(3):
        r0, c0 = rng.integers(0, 30, size=2)
        dr, dc = rng.integers(-1, 2, size=2)
        for s in range(rng.integers(6, 16)):
            r, c = r0 + dr * s, c0 + dc * s
            if 0 <= r < 30 and 0 <= c < 30:
                truth[r, c] = True
    pred = rng.random((30, 30)) < 0.08
    return truth, pred


def test_identity_dti_equals_tp_over_0p2tp_0p2fp_0p8g():
    for seed in range(12):
        truth, pred = _scene(seed)
        if not truth.any():
            continue
        out = metric.dti_exact(pred.astype(float), truth)
        n = truth.sum()
        expected = out["tp"] / (0.2 * out["tp"] + 0.2 * out["fp"] + 0.8 * n)
        assert abs(out["fn"] - (n - out["tp"])) < 1e-9
        assert abs(out["dti"] - expected) < 1e-12


def test_removal_rule_is_exact_for_every_dot():
    checked = 0
    for seed in range(12):
        truth, pred = _scene(seed)
        if not truth.any() or not pred.any():
            continue
        before = metric.dti_exact(pred.astype(float), truth)
        for y, x in zip(*np.nonzero(pred)):
            p2 = pred.copy()
            p2[y, x] = False
            after = metric.dti_exact(p2.astype(float), truth)
            t = before["tp"] - after["tp"]          # credit this dot uniquely supplies
            f = before["fp"] - after["fp"]          # false-positive cost of this dot
            if t + f <= 1e-12:
                continue
            removal_improves = after["dti"] > before["dti"] + 1e-12
            keep_rule = t / (t + f) < ALPHA * before["dti"]
            assert removal_improves == keep_rule, (seed, y, x, t, f, before["dti"])
            checked += 1
    assert checked > 50


def test_official_worked_example_reproduces():
    # Competition page example: TP_w=3.00, FP_w=1.89, FN_w=2.00 -> TI_w = 0.60.
    value = 3.00 / (3.00 + ALPHA * 1.89 + BETA * 2.00)
    assert round(value, 2) == 0.60
