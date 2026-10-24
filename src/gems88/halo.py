"""HALO-88: far-basin-matched training, catalogue-completeness residual, ridge-continuity prior.

All three transforms are *label-blind with respect to withheld truth*: they use the
44-column label-blind physics matrix (``gems88.physics``), the VISIBLE catalogue
only, and the vendored official-formula allocator/evaluator.

Evidence behind the design (measured on disk, see ``evidence/h33_forensics_20261024.json``
and ``evidence/proxy_calibration_20261024.json``):

* The user-reported best raster (H33) lies far from the catalogue (median 19.6 px,
  36% beyond 30 px, 0% within 2 px) while the previous ADHR candidate keeps 74% of its
  dots within 10 px of the catalogue.  A catalogue-adjacent surface is rewarded by
  hide-and-recover but cannot be rewarded by a test set made of faults *not already
  captured* by USGS/INGENIOUS (DrivenData staff, thread 11536).
* Therefore the instrument that matters is the *far subset* (withheld positives more
  than 10 px = 1 km from any visible catalogue pixel) and the model must be trained
  on the population it will be tested on: isolated mapped faults standing alone in
  un-mapped terrain, against far-basin background.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier

from gems57 import emit

from . import adhr

STRUCT8 = np.ones((3, 3), bool)


def isolated_mask(cat: np.ndarray, r: int = 5) -> np.ndarray:
    """Catalogue pixels of 8-connected components with no OTHER component within a
    Chebyshev radius ``r`` (square window), i.e. faults standing alone."""
    cat = np.asarray(cat, bool)
    lab, n = ndi.label(cat, structure=STRUCT8)
    if n == 0:
        return np.zeros_like(cat)
    size = 2 * r + 1
    mx = ndi.maximum_filter(lab, size=size)
    mn = ndi.minimum_filter(np.where(lab > 0, lab, n + 1), size=size)
    bad = cat & ((mx != lab) | (mn != lab))
    ok = np.ones(n + 1, bool)
    ok[0] = False
    ok[np.unique(lab[bad])] = False
    return ok[lab] & cat


def _fit_classifier(X, grid, domain_fp, pos_grid, seed, max_zero_neg=140_000):
    """Same sampling as ``adhr._fit_dual_expectation_models`` (all pixels within 3 px of a
    positive + a weighted random subset of the remaining domain) but the single classifier
    head only.  Self-credit is derived from the calibrated surface for EVERY arm, so the arms
    differ only in the training population."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int8)
    near_grid = ndi.distance_transform_edt(~pos_grid) <= 3.0
    near_all = near_grid[ys_fp, xs_fp]
    del near_grid
    dom_idx = np.flatnonzero(domain_fp)
    near_sel = near_all[dom_idx]
    near_idx = dom_idx[near_sel]
    zero_idx = dom_idx[~near_sel]
    rng = np.random.default_rng(seed)
    if zero_idx.size > max_zero_neg:
        sub_zero = np.sort(rng.choice(zero_idx, size=max_zero_neg, replace=False))
        w_zero = float(zero_idx.size) / float(max_zero_neg)
    else:
        sub_zero, w_zero = zero_idx, 1.0
    train_idx = np.concatenate([near_idx, sub_zero])
    weights = np.concatenate([np.ones(near_idx.size), np.full(sub_zero.size, w_zero)])
    seq = np.argsort(train_idx)
    train_idx, weights = train_idx[seq], weights[seq]
    X_tr = adhr.gather_columns([X], train_idx)
    y_tr = y_cell_all[train_idx]
    perm = rng.permutation(len(train_idx))
    clf = HistGradientBoostingClassifier(
        max_iter=115, learning_rate=0.075, max_leaf_nodes=47, min_samples_leaf=80,
        l2_regularization=4.0, early_stopping=True, validation_fraction=0.1,
        n_iter_no_change=12, random_state=seed)
    clf.fit(X_tr[perm], y_tr[perm], sample_weight=weights[perm])
    return clf


def fit_fold_models(X, grid, visible, quad, q, train_truth_px, seed, mode):
    """Fit one classifier for one LOQO fold.

    mode "base": every visible positive in the three training quadrants, whole quadrant
                 as background (identical sampling to ``adhr.predict_cgo_fold``).
    mode "fbmt": far-basin-matched training: positives = ISOLATED visible components;
                 background = pixels >8 px from every visible catalogue pixel, plus the
                 neighbourhood of the isolated positives.  Pixels within 8 px of dense
                 fault networks are unlabeled (neither positive nor negative).
    The expected hidden-truth mass ``k_est`` is common to all arms (hidden fraction of ALL
    visible training positives), so arms never differ by budget.
    """
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    train_quads = fp & (quad != q)
    d_vis = ndi.distance_transform_edt(~visible)
    n_vis_tr = max(int((visible & train_quads).sum()), 1)
    hid_ratio = float(train_truth_px) / n_vis_tr
    if mode == "base":
        pos = visible & train_quads
        domain = train_quads
    elif mode == "fbmt":
        iso = isolated_mask(visible, r=5) & train_quads
        d_iso = ndi.distance_transform_edt(~iso)
        pos = iso
        domain = train_quads & ((d_vis > 8) | (d_iso <= 3))
    else:  # pragma: no cover
        raise ValueError(mode)
    clf = _fit_classifier(X, grid, domain[ys_fp, xs_fp], pos, seed)
    return clf, dict(n_pos=int(pos.sum()), hid_ratio=hid_ratio, n_domain=int(domain.sum()))


def predict_calibrated(clf, X, grid, visible, test_region, hid_ratio, halo_px):
    """Calibrated (p, m) grids on allowed = footprint & test_region & d_vis > halo_px.

    p is scaled to the common expected hidden-truth mass; m (self-credit) is the clipped
    expected kernel credit E[k](x) = sum_g p(g) k(d(x,g)) used by ``emit.greedy_allocate``.
    """
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    d_vis = ndi.distance_transform_edt(~visible)
    allowed = fp & test_region & (d_vis > halo_px)
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    p_raw = np.empty(act_idx.size, np.float32)
    for s0 in range(0, act_idx.size, 160_000):
        sl = slice(s0, min(s0 + 160_000, act_idx.size))
        p_raw[sl] = clf.predict_proba(adhr.gather_columns([X], act_idx[sl]))[:, 1]
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)
    scale_p = float(k_est) / max(float(p_raw.sum()), 1e-6)
    p_cal = np.clip(p_raw * scale_p, 0.0, 1.0).astype(np.float32)
    p_grid = adhr.scatter_fp(p_cal, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_grid = np.clip(emit.expected_credit(p_grid), p_grid, 1.0).astype(np.float32)
    return p_grid, m_grid, allowed, float(k_est)


def _renorm(p, m, allowed, k_est):
    """Rescale p to the common expected truth mass and recompute self-credit with the same rule."""
    s = float(k_est) / max(float(p[allowed].sum()), 1e-9)
    p2 = np.clip(p * np.float32(s), 0.0, 1.0).astype(np.float32)
    m2 = np.clip(emit.expected_credit(p2), p2, 1.0).astype(np.float32)
    return p2, m2


def ccr_boost(p, m, visible, allowed, k_est, gamma=0.5, sigma_px=15.0, nbins=20, zclip=2.0):
    """Catalogue-completeness residual.

    E = Gaussian-smoothed model evidence, C = Gaussian-smoothed VISIBLE catalogue density
    (same window).  f(C) = median E within quantile bins of C over the allowed pixels
    (transductive, label-free).  z = log((E+eps)/(f(C)+eps)) > 0 marks windows where the
    geophysical evidence exceeds what the mapped density usually accompanies.
    p' = p * exp(gamma * clip(z, +-zclip)), renormalised to the same expected truth.
    """
    E = ndi.gaussian_filter(p.astype(np.float32), sigma_px)
    C = ndi.gaussian_filter(visible.astype(np.float32), sigma_px)
    c_al = C[allowed]
    e_al = E[allowed]
    edges = np.quantile(c_al, np.linspace(0, 1, nbins + 1))
    edges[0] -= 1e-9
    edges[-1] += 1e-9
    idx = np.clip(np.searchsorted(edges, C, side="right") - 1, 0, nbins - 1)
    ia = idx[allowed]
    med = np.array([np.median(e_al[ia == b]) if np.any(ia == b) else 0.0 for b in range(nbins)], np.float32)
    f = med[idx]
    eps = np.float32(max(float(np.median(e_al)) * 0.05, 1e-7))
    z = np.log((E + eps) / (f + eps))
    z = np.clip(z, -zclip, zclip)
    p2 = p * np.exp(np.float32(gamma) * z).astype(np.float32)
    return _renorm(p2, m, allowed, k_est) + (dict(median_E_by_bin=med.tolist(), gamma=gamma, sigma_px=sigma_px),)


def continuity_weight(p, allowed, top_frac=0.04, bridge=1, l0_px=12.0, w_min=0.35):
    """Ridge-continuity prior: faults are laterally continuous, isolated short blobs are noise.

    Take the top ``top_frac`` of allowed pixels by p, bridge 1-px gaps, label 8-connected
    components, and weight each component by clip(bbox_diagonal / l0_px, w_min, 1).
    Pixels outside the candidate set keep weight 1 (they are already low).
    """
    vals = p[allowed]
    thr = np.quantile(vals, 1.0 - top_frac)
    cand = (p >= thr) & allowed
    cand_b = ndi.binary_closing(cand, structure=STRUCT8, iterations=bridge) & allowed if bridge else cand
    lab, n = ndi.label(cand_b, structure=STRUCT8)
    w = np.ones(p.shape, np.float32)
    if n == 0:
        return w, dict(n_components=0)
    objs = ndi.find_objects(lab)
    diag = np.zeros(n + 1, np.float32)
    for i, sl in enumerate(objs, start=1):
        h = sl[0].stop - sl[0].start
        wd = sl[1].stop - sl[1].start
        diag[i] = float(np.hypot(h, wd))
    comp_w = np.clip(diag / float(l0_px), w_min, 1.0).astype(np.float32)
    comp_w[0] = 1.0
    w = np.where(lab > 0, comp_w[lab], np.float32(1.0)).astype(np.float32)
    return w, dict(n_components=int(n), frac_components_downweighted=float((comp_w[1:] < 1).mean()),
                   thr=float(thr))


def apply_weight(p, m, w, allowed, k_est):
    return _renorm(p * w, m, allowed, k_est)
