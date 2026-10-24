"""Line-by-line verification of the KDMC-88 lane primitives against the shared template.

Nothing here is a claim about a score; every assertion is a mathematical
identity between :mod:`gems88.kdmc` and the unmodified shared implementations in
``vendor/gems57``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import metric, uniqueness  # noqa: E402
from gems88 import kdmc  # noqa: E402


def test_kernel_mass_matches_template():
    assert kdmc.KERNEL_MASS == pytest.approx(float(metric.offsets()[2].sum()), abs=1e-12)
    # 25 offsets carry non-zero weight for R = 3 px
    assert len(kdmc.kernel_offsets()[2]) == len(metric.offsets()[2]) == 25


def test_kernel_offsets_match_template():
    a = np.array(sorted(zip(*kdmc.kernel_offsets())))
    b = np.array(sorted(zip(*metric.offsets())))
    assert np.allclose(a, b)


def test_marginal_bar_equals_template_two_sided_test():
    rng = np.random.default_rng(0)
    tested = 0
    for _ in range(3000):
        T = rng.uniform(1, 5e4)
        n = int(rng.integers(1, 2e5))
        M = rng.uniform(0, n)
        K = rng.uniform(1e3, 2e5)
        if T > K:
            continue
        k = rng.uniform(0.0, 1.0)
        dti = T / (metric.ALPHA * (T + n - M) + metric.BETA * K)
        bar = kdmc.marginal_bar(dti, k)
        for dT in (bar * 0.999, bar * 1.001):
            assert metric.marginal_accept(dT, k, T, M, n, K) == (dT > bar)
        tested += 1
    assert tested > 1000


def test_dti_from_matches_template_binary_scorer():
    truth = np.zeros((80, 80), bool)
    truth[20:60, 30] = True
    truth[40, 10:70] = True
    pred = np.zeros((80, 80), bool)
    pred[25, 30] = pred[41, 50] = pred[70, 70] = True
    r = metric.dti_binary(pred, truth)
    n = int(pred.sum())
    assert kdmc.dti_from(r["tp"], n, n - r["fp"], int(truth.sum())) == pytest.approx(r["dti"], abs=1e-12)


def test_expected_credit_equals_brute_force_including_edges():
    rng = np.random.default_rng(3)
    g = (rng.random((24, 24)) < 0.05).astype(np.float32) * rng.random((24, 24)).astype(np.float32)
    E = kdmc.expected_credit(g)
    dy, dx, kw = metric.offsets()
    for y in range(24):
        for x in range(24):
            tot = sum(k * g[y + j, x + i] for j, i, k in zip(dy, dx, kw)
                      if 0 <= y + j < 24 and 0 <= x + i < 24)
            assert E[y, x] == pytest.approx(tot, abs=1e-5)


@pytest.mark.parametrize("sep", [2.8284271247461903, 3.0, 4.0, 6.0, 8.0])
def test_allocate_separated_is_exactly_sequential_greedy(sep):
    rng = np.random.default_rng(int(sep * 100))
    s = rng.random((70, 70)).astype(np.float32)
    allowed = rng.random((70, 70)) > 0.1
    got = kdmc.allocate_separated(s, allowed, sep, 0.5)
    live = allowed & (s > 0.5)
    idx = np.argwhere(live)
    vals = s[live]
    ref = []
    for t in np.lexsort((np.arange(vals.size), -vals)):
        y, x = idx[t]
        if all((y - a) ** 2 + (x - b) ** 2 >= sep * sep - 1e-9 for a, b in ref):
            ref.append((int(y), int(x)))
    assert set(ref) == set(map(tuple, np.argwhere(got)))
    pts = np.argwhere(got).astype(float)
    if len(pts) > 1:
        from scipy.spatial import cKDTree
        assert cKDTree(pts).query(pts, k=2)[0][:, 1].min() >= sep - 1e-9


def test_allocate_separated_prefix_property():
    """Capping the allocator at N returns exactly the N highest-score accepted cells."""
    rng = np.random.default_rng(11)
    s = rng.random((60, 60)).astype(np.float32)
    allowed = np.ones((60, 60), bool)
    full = kdmc.allocate_separated(s, allowed, 4.0, -np.inf)
    idx = np.flatnonzero(full.ravel())
    order = idx[np.lexsort((idx, -s.ravel()[idx]))]
    for n in (5, 25, 100):
        capped = kdmc.allocate_separated(s, allowed, 4.0, -np.inf, max_dots=n)
        assert set(np.flatnonzero(capped.ravel())) == set(order[:n])


def test_packing_efficiency_of_a_disjoint_lattice_is_one():
    g = np.zeros((120, 120), bool)
    g[6::12, 6::12] = True          # 12 px lattice -> kernels fully disjoint
    fp = np.ones((120, 120), bool)
    r = kdmc.packing_efficiency(g, fp)
    assert r["packing_efficiency"] == pytest.approx(1.0, abs=1e-6)


def test_packing_efficiency_penalises_overlap():
    """Packing efficiency must fall monotonically as the lattice tightens."""
    fp = np.ones((120, 120), bool)
    eff = []
    for step in (12, 6, 4, 3, 2):
        g = np.zeros((120, 120), bool)
        g[6::step, 6::step] = True
        eff.append(kdmc.packing_efficiency(g, fp)["packing_efficiency"])
    assert all(a >= b - 1e-9 for a, b in zip(eff, eff[1:])), eff
    # 6 px is exactly the kernel-disjointness threshold for R = 3 px: a 12 px
    # and a 6 px lattice both realise 100% of their kernel mass, and every
    # tighter lattice wastes mass. This is the whole premise of the KDMC lane.
    assert eff[0] == pytest.approx(1.0, abs=1e-6)
    assert eff[1] == pytest.approx(1.0, abs=1e-6)
    assert eff[2] < 0.85 and eff[3] < 0.65
    assert eff[-1] < 0.35      # a 2 px lattice wastes >65% of its kernel mass


def test_excess_overlap_identities():
    for o in (0.0, 0.1, 0.5, 0.6999, 0.7001, 1.0):
        assert uniqueness.excess_overlap(o, 0.0) == pytest.approx(o)
    assert uniqueness.excess_overlap(1.0, 1.0) is None
    assert uniqueness.excess_overlap(0.68, 0.14) == pytest.approx((0.68 - 0.14) / 0.86)
    # never weaker than the literal rule for a prior with a halo advantage
    for h in (0.05, 0.2, 0.5):
        for o in (0.75, 0.9):
            assert uniqueness.excess_overlap(o, h) < o


def test_binding_decision_v3_blocks_a_real_copy_and_clears_a_space_filling_prior():
    dense = dict(file="dense.tif", forward_overlap=1.0, halo_coverage=1.0,
                 spearman_full_footprint=0.10, their_dots=5_167_373)
    sparse = dict(file="sparse.tif", forward_overlap=0.40, halo_coverage=0.14,
                  spearman_full_footprint=0.03, their_dots=37_654)
    assert uniqueness.binding_duplicate_decision_v3([dense, sparse])["verdict"] == "negative"
    copycat = dict(file="copy.tif", forward_overlap=0.95, halo_coverage=0.15,
                   spearman_full_footprint=0.50, their_dots=40_000)
    d = uniqueness.binding_duplicate_decision_v3([dense, sparse, copycat])
    assert d["verdict"] == "negative" and d["duplicate"] is True
    rho_twin = dict(file="twin.tif", forward_overlap=0.10, halo_coverage=0.05,
                    spearman_full_footprint=0.97, their_dots=40_000)
    assert uniqueness.binding_duplicate_decision_v3([dense, rho_twin])["verdict"] == "negative"


def test_dinkelbach_pack_converges_and_respects_separation():
    rng = np.random.default_rng(5)
    rho = (rng.random((200, 200)).astype(np.float32) ** 6) * 0.05
    allowed = np.ones((200, 200), bool)
    res = kdmc.dinkelbach_pack(rho, allowed, 6.0, max_iter=12)
    assert res.n_dots > 0
    assert 0.0 < res.dti_model < 1.0
    pts = np.argwhere(res.dots).astype(float)
    from scipy.spatial import cKDTree
    assert cKDTree(pts).query(pts, k=2)[0][:, 1].min() >= 6.0 - 1e-9
