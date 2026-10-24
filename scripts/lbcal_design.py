#!/usr/bin/env python3
"""LBCAL design: greedy expected-DTI emission under a fitted receipt-calibrated density q(y),
with a provable lane-separation cap (<= CAP of dots inside the union of registry 3-px halos).

Library used by scripts/build_lbcal_submission.py.  Pure function of (q, pools); never reads labels.
"""
from __future__ import annotations

import heapq
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from gems88.lbcal import OFFS, coverage_maps  # noqa: E402

ALPHA, BETA = 0.2, 0.8


def full_grid_q(beta, labels, fstats, F):
    """Evaluate q = exp(beta.phi) on the full grid with the exact training transforms."""
    eta = np.full(next(iter(F.values())).shape, beta[0], np.float64)
    for b, nm in zip(beta[1:], labels[1:]):
        v = F[nm].astype(np.float64)
        st = fstats.get(nm, {"type": "indicator"})
        if st["type"] == "zscore":
            lo, hi = st["clip"]
            v = np.clip(v, lo, hi)
            v = (v - st["mu"]) / st["sd"]
        v = np.nan_to_num(v, nan=0.0)
        eta += b * v
    return np.exp(np.clip(eta, -30, 3))


def kernel_sum(q):
    """s(x) = sum_y q(y) k(d(x,y))."""
    _, e = coverage_maps(q.astype(np.float32))
    return e.astype(np.float64)


def greedy(q, cand, G, kappa=2.6, max_dots=200000, min_ratio=0.0):
    """Lazy-greedy max-coverage with FP cost (1 - s/kappa).  Returns ordered picks with dT, dF."""
    H, W = q.shape
    qf = q.ravel()
    s = kernel_sum(q).ravel()
    cov = np.zeros(H * W, np.float64)
    offs = [(dy * W + dx, dy, dx, float(k)) for dy, dx, k in OFFS]
    ys, xs = np.nonzero(cand)
    idx = ys * W + xs

    def gain(i):
        y, x = divmod(i, W)
        g = 0.0
        for o, dy, dx, k in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                j = i + o
                c = cov[j]
                if k > c:
                    g += qf[j] * (k - c)
        return g

    cost = np.maximum(1.0 - np.minimum(s[idx] / kappa, 1.0), 1e-3)
    heap = []
    for i, c0 in zip(idx.tolist(), cost.tolist()):
        g0 = s[i]  # initial gain with empty coverage equals kernel sum
        heapq.heappush(heap, (-g0 / c0, i, c0))
    picks, dT, dF = [], [], []
    taken = set()
    while heap and len(picks) < max_dots:
        r, i, c0 = heapq.heappop(heap)
        if i in taken:
            continue
        g = gain(i)
        if heap and g / c0 < -heap[0][0] - 1e-12:
            heapq.heappush(heap, (-g / c0, i, c0))
            continue
        if g / c0 <= min_ratio:
            break
        taken.add(i)
        y, x = divmod(i, W)
        for o, dy, dx, k in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                j = i + o
                if k > cov[j]:
                    cov[j] = k
        picks.append(i); dT.append(g); dF.append(c0)
    return np.array(picks, np.int64), np.array(dT), np.array(dF)


def best_split(dTA, dFA, dTB, dFB, G, cap):
    """Choose prefix sizes (nA, nB) maximising expected DTI subject to nA <= cap * (nA + nB)."""
    cTA, cFA = np.concatenate([[0], np.cumsum(dTA)]), np.concatenate([[0], np.cumsum(dFA)])
    cTB, cFB = np.concatenate([[0], np.cumsum(dTB)]), np.concatenate([[0], np.cumsum(dFB)])
    best = (-1, 0, 0)
    for nB in range(0, len(dTB) + 1, max(1, len(dTB) // 4000 or 1)):
        nA_max = len(dTA) if cap >= 1 else int(np.floor(cap / (1 - cap) * nB))
        nA_max = min(nA_max, len(dTA))
        nA_grid = np.arange(0, nA_max + 1)
        T = cTA[nA_grid] + cTB[nB]
        F = cFA[nA_grid] + cFB[nB]
        D = T / (ALPHA * T + ALPHA * F + BETA * G + 1e-12)
        j = int(np.argmax(D))
        if D[j] > best[0]:
            best = (float(D[j]), int(nA_grid[j]), nB)
    return best


def expected_dti_of_mask(q, mask, G, kappa=2.6):
    """Model-projected DTI of an arbitrary binary mask under q (MODEL-PROJECTION, never a score)."""
    c, e = coverage_maps(mask.astype(np.float32))
    T = float((q * c).sum())
    s = kernel_sum(q)
    M = float(np.minimum(s[mask] / kappa, 1.0).sum())
    F = float(mask.sum()) - M
    return T / (ALPHA * T + ALPHA * F + BETA * G), T, F


def greedy_capped(q, cand, members, rowmap, cap, G, kappa=2.6, max_dots=150000, repush_every=200):
    """Lazy-greedy expected-DTI emission with a running per-raster lane cap.

    members : bool matrix (n_candidates x K) — candidate row r lies in the 3-px halo of raster k
    rowmap  : int array over the flattened grid -> candidate row (or -1)
    Invariant after every acceptance: for every raster k, count_k <= cap * n_dots.
    Stops when no feasible candidate has marginal ratio above the DTI break-even bar
    0.2D/(1-0.2D) (D = running expected DTI under q).
    """
    H, W = q.shape
    qf = q.ravel()
    s = kernel_sum(q).ravel()
    cov = np.zeros(H * W, np.float64)
    offs = [(dy * W + dx, dy, dx, float(k)) for dy, dx, k in OFFS]
    ys, xs = np.nonzero(cand)
    idx = ys * W + xs
    K = members.shape[1]
    counts = np.zeros(K, np.int64)

    def gain(i):
        y, x = divmod(i, W)
        g = 0.0
        for o, dy, dx, k in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                j = i + o
                c = cov[j]
                if k > c:
                    g += qf[j] * (k - c)
        return g

    cost_all = np.maximum(1.0 - np.minimum(s / kappa, 1.0), 1e-3)
    heap = [(-s[i] / cost_all[i], i) for i in idx.tolist()]
    heapq.heapify(heap)
    picks, T, F, n = [], 0.0, 0.0, 0
    deferred, taken = [], np.zeros(H * W, bool)
    since = 0
    while len(picks) < max_dots:
        if not heap:
            if not deferred or since == 0:
                break
            for it in deferred:
                heapq.heappush(heap, it)
            deferred, since = [], 0
            continue
        r, i = heapq.heappop(heap)
        if taken[i]:
            continue
        c0 = cost_all[i]
        g = gain(i)
        if heap and g / c0 < -heap[0][0] - 1e-12:
            heapq.heappush(heap, (-g / c0, i))
            continue
        D = T / (0.2 * T + 0.2 * F + 0.8 * G) if n else 0.0
        bar = 0.2 * D / (1 - 0.2 * D)
        if g / c0 <= bar:
            if deferred and since > 0:
                for it in deferred:
                    heapq.heappush(heap, it)
                deferred, since = [], 0
                heapq.heappush(heap, (-g / c0, i))
                continue
            break
        mem = members[rowmap[i]]
        if mem.any() and np.any(counts[mem] + 1 > cap * (n + 1)):
            deferred.append((-g / c0, i))
            continue
        taken[i] = True
        y, x = divmod(i, W)
        for o, dy, dx, k in offs:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                j = i + o
                if k > cov[j]:
                    cov[j] = k
        counts[mem] += 1
        n += 1; T += g; F += c0
        picks.append(i)
        since += 1
        if since >= repush_every and deferred:
            for it in deferred:
                heapq.heappush(heap, it)
            deferred, since = [], 0
    D = T / (0.2 * T + 0.2 * F + 0.8 * G) if n else 0.0
    return np.array(picks, np.int64), {"n": n, "T": T, "F": F, "model_projected_dti": D,
                                       "max_share": float(counts.max() / max(n, 1)), "argmax_share": int(counts.argmax())}
