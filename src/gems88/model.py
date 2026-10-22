"""Single fixed LOQO learning/emission rule for MGC-88 (no tuning on holdout)."""

from __future__ import annotations
import numpy as np
from scipy.ndimage import binary_dilation
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

BASE = (0, 1, 2)
JOINT = (0, 1, 2, 3, 4, 5, 6)
SEED = 88


def leakage_canaries(features, names, folds, footprint, *, seed=SEED):
    """Holdout-only diagnostics; no hidden labels are passed to fitting.

    Negatives are sampled from active score domains away from truth; this is a
    diagnostic of catalogue discrimination, not a test of unmapped fault truth.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for col, name in enumerate(names):
        yes, no = [], []
        for fold in folds:
            region = fold["region"] & footprint
            pos = np.flatnonzero(fold["truth"] & region)
            if not len(pos):
                raise ValueError("empty holdout fold")
            # Sampling negatives is a *diagnostic*, never a model feature.
            negative = region & ~fold["masked_known"] & ~fold["truth"]
            negative &= ~binary_dilation(fold["truth"], iterations=3)
            candidates = np.flatnonzero(negative)
            n = min(len(pos), len(candidates), 2500)
            yes.append(features[rng.choice(pos, n, replace=False), col])
            no.append(features[rng.choice(candidates, n, replace=False), col])
        yy, nn = np.concatenate(yes), np.concatenate(no)
        auc = float(
            roc_auc_score(np.r_[np.ones(yy.size), np.zeros(nn.size)], np.r_[yy, nn])
        )
        rows.append(
            dict(
                feature=name,
                auc=auc,
                symmetric_auc=max(auc, 1.0 - auc),
                withheld_sample=int(yy.size),
                negative_sample=int(nn.size),
            )
        )
    return rows


def fit(features, footprint, visible, training_domain, columns, *, seed=SEED):
    """Train on visible catalogue *only*; unlabeled background is noisy PU data.

    `training_domain` is label-blind and omits the held-out quadrant + boundary.
    The hidden components never enter X or the positive-label construction.
    """
    valid = footprint & training_domain
    positives = np.flatnonzero(valid & visible)
    if not len(positives):
        raise ValueError("no visible catalogue positives for training")
    exclusion = binary_dilation(visible, iterations=3)
    negatives = np.flatnonzero(valid & ~exclusion)
    if not len(negatives):
        raise ValueError("no unlabeled negatives for training")
    rng = np.random.default_rng(seed)
    p = rng.choice(positives, min(16000, len(positives)), replace=False)
    n = rng.choice(negatives, min(48000, len(negatives)), replace=False)
    idx = np.r_[p, n]
    y = np.r_[np.ones(len(p), dtype=np.int8), np.zeros(len(n), dtype=np.int8)]
    model = HistGradientBoostingClassifier(
        max_iter=55,
        learning_rate=0.08,
        max_leaf_nodes=15,
        max_bins=128,
        l2_regularization=1.0,
        random_state=seed,
    )
    model.fit(np.asarray(features[idx][:, columns]), y)
    return model, dict(
        n_visible_training=int(len(positives)),
        n_positives=int(len(p)),
        n_unlabeled=int(len(n)),
        columns=list(columns),
        noisy_pu_negative_sampling=True,
    )


def probability(model, features, indices, columns, chunk=100_000):
    result = np.empty(len(indices), dtype=np.float32)
    for start in range(0, len(indices), chunk):
        part = indices[start : start + chunk]
        result[start : start + len(part)] = model.predict_proba(
            np.asarray(features[part][:, columns])
        )[:, 1]
    return result


def spaced_dots(prob, eligible, budget, radius=2, *, tie=None):
    """Fixed-budget greedy pixel-space thinning, stable across machines.

    This is not the exact expected-DTI optimizer in other GEMSDOE lanes; it
    emits independent local maxima of an out-of-fold learned physical surface.
    """
    prob = np.asarray(prob, np.float32)
    eligible = np.asarray(eligible, bool)
    if prob.ndim != 2 or eligible.shape != prob.shape or budget < 1 or radius < 0:
        raise ValueError("invalid probability grid/eligibility/budget")
    if not np.isfinite(prob).all() or (prob < 0).any() or (prob > 1).any():
        raise ValueError("probabilities out of range")
    candidates = np.flatnonzero(eligible.ravel() & (prob.ravel() > 0))
    if not len(candidates):
        raise ValueError("no eligible probabilities")
    t = (
        np.zeros(prob.size, np.float32)
        if tie is None
        else np.asarray(tie, np.float32).ravel()
    )
    if t.shape != (prob.size,) or not np.isfinite(t[candidates]).all():
        raise ValueError("bad tie-breaking feature")
    # Bounded-pool selection protects RAM while allowing radius-2 inhibition.
    poolsize = min(len(candidates), max(8000, budget * 25))
    if poolsize < len(candidates):
        # Continuous physically derived tie breaks make HGB plateaus deterministic.
        ranking = prob.ravel()[candidates].astype(np.float64) + (1e-9 * t[candidates])
        kept = np.argpartition(ranking, -poolsize)[-poolsize:]
        candidates = candidates[kept]
    order = np.lexsort((candidates, -t[candidates], -prob.ravel()[candidates]))
    ordered = candidates[order]
    out = np.zeros(prob.shape, bool)
    blocked = np.zeros(prob.shape, bool)
    h, w = prob.shape
    offsets = [
        (j, i)
        for j in range(-radius, radius + 1)
        for i in range(-radius, radius + 1)
        if j * j + i * i <= radius * radius
    ]
    count = 0
    for flat in ordered:
        row, col = divmod(int(flat), w)
        if blocked[row, col]:
            continue
        out[row, col] = True
        count += 1
        for dy, dx in offsets:
            yy, xx = row + dy, col + dx
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True
        if count >= budget:
            break
    return out, dict(
        requested=int(budget),
        emitted=int(count),
        poolsize=int(poolsize),
        radius_px=radius,
    )
