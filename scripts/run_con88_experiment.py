#!/usr/bin/env python3
"""H88-CON88: cross-fleet consensus + label-blind ridge, H33-parity emission.

Lane (one method paragraph): dots are emitted only where (a) at least two
mutually-independent high-scoring fleet surfaces agree within the 3 px DTI
kernel OR a fresh label-blind multi-modal ridge (magnetic/gravity/topographic
edge ranks from the 19-band GeoDAWN stack, computed with no catalogue labels)
is locally extreme, (b) distance to the USGS/INGENIOUS catalogue is > 3 px
(one full kernel radius; H33 used 2.236 px), (c) inter-dot spacing >= 2.83 px,
and (d) the distance-to-catalogue histogram matches H33's measured profile.
No catalogue-trained classifier is fitted; the catalogue is used only as an
exclusion mask and distance field, exactly as the organiser masks it.

Historical method only — generation is not authorized. The pinned 17GEMSDOE
registry raster is positive on 100% of the allowed footprint, so the user's
literal >70%-within-3px rule rejects every nonempty candidate. The former
equal-support top-N exception is withdrawn by IR-88-0AB98CD1-01; those figures
remain diagnostics only. The shared mandatory guard stops this CLI before model
imports, and ``main()`` repeats that guard for programmatic callers.
"""
from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, laplace
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import metric
from gems57.uniqueness import dot_overlap

N_DOTS = 37654
MIN_SPACING = 2.83
COLLAR_PX = 3.0
CONTRIBUTORS = {
    "GATE49_gems49_gate_ortho_userreported_0.2376": "data/registry/gems49_gate_ortho.tif",
    "G70SUB_gems70_p5_dualsubmod_userreported_0.2478": "data/registry/gems70_p5_dualsubmod.tif",
    "BPWD_gems88_bpwd_holdout_0.205991_unscored": "docs/downloads/gems88-bpwd88-baranov-worm-conduit-37654-20261025-b8543782-zeros-DO-NOT-SUBMIT.tif",
}
# H33-lineage / near-duplicates excluded from the surface (education only):
EXCLUDED_LINEAGE = ["h33_education", "gems19_h19_5", "gems25_d28", "gems28_h27_4",
                    "gems36_anderson_pinn (0.974 overlap with H33, measured)"]

def load(p):
    with rasterio.open(ROOT / p) as ds:
        return ds.read(1), ds.profile

def rank01(x, mask):
    out = np.zeros(x.shape, np.float32)
    v = x[mask]
    out[mask] = (rankdata(v) / len(v)).astype(np.float32)
    return out

def spaced_topk(surface, allowed, quotas):
    """Greedy spaced selection per distance-bin quota. Returns bool dots."""
    dots = np.zeros(surface.shape, bool)
    blocked = np.zeros(surface.shape, bool)  # within MIN_SPACING of a chosen dot
    r = int(np.ceil(MIN_SPACING))
    offs = [(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
            if np.hypot(dy, dx) < MIN_SPACING]
    for sel_mask, quota in quotas:
        cand = np.argwhere(sel_mask & allowed)
        if len(cand) == 0 or quota == 0:
            continue
        vals = surface[cand[:, 0], cand[:, 1]]
        order = cand[np.argsort(-vals)]
        taken = 0
        for y, x in order:
            if taken >= quota:
                break
            if blocked[y, x] or dots[y, x]:
                continue
            dots[y, x] = True
            taken += 1
            for dy, dx in offs:
                yy, xx = y + dy, x + dx
                if 0 <= yy < dots.shape[0] and 0 <= xx < dots.shape[1]:
                    blocked[yy, xx] = True
        print(f"  bin quota {quota} taken {taken}", flush=True)
    return dots

def main():
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sample, prof = load("data/bridge/sample_submission.tif")
    foot = np.isfinite(sample)
    faults, _ = load("data/bridge/existing_faults.tif")
    cat = faults == 1
    dcat = distance_transform_edt(~cat).astype(np.float32)
    h33, _ = load("data/registry/h33_education.tif")
    h33dots = np.isfinite(h33) & (h33 > 0)
    # H33 distance-profile quotas (measured, not assumed)
    bins = [(3.0, 5.0), (5.0, 10.0), (10.0, 25.0), (25.0, np.inf)]
    h33d = dcat[h33dots]
    shares = [float(((h33d > lo) & (h33d <= hi)).mean()) for lo, hi in bins]
    shares[0] += float((h33d <= 3.0).mean())  # H33's <=3px mass moves to first allowed bin
    print("H33 bin shares (3-5,5-10,10-25,>25):", [round(s, 4) for s in shares])

    # --- label-blind ridge from 19-band stack (bands are 1-indexed) ---
    with rasterio.open(ROOT / "data/training_features.tif") as ds:
        tmi_hg = ds.read(3).astype(np.float64)    # tmi_hg
        tc = ds.read(6).astype(np.float64)        # tilt/total curvature
        grav_slope = ds.read(5).astype(np.float64)
        grav_hg = ds.read(18).astype(np.float64)
        det = ds.read(12).astype(np.float64)
    det_f = np.where(np.isfinite(det), det, np.nanmean(det[np.isfinite(det)]))
    ridge = (rank01(tmi_hg, foot) + rank01(np.abs(tc), foot) + rank01(grav_hg, foot)
             + rank01(grav_slope, foot) + rank01(np.abs(laplace(det_f)), foot)) / 5.0
    print("ridge done")

    # --- contributor votes: kernel credit of nearest contributor dot ---
    votes = []
    near_masks = []
    for name, p in CONTRIBUTORS.items():
        a, _ = load(p)
        d = np.isfinite(a) & (a > 0)
        dist = distance_transform_edt(~d)
        votes.append(metric.kernel(dist).astype(np.float32))
        near_masks.append(dist <= 3.0)
        print(name, "dots", int(d.sum()))
    votes = np.stack(votes)
    n_agree = np.sum(near_masks, axis=0)
    consensus = votes.mean(axis=0)

    experiments = {
        "exp1_consensus_only": consensus,
        "exp2_consensus_plus_ridge": 0.6 * consensus + 0.4 * ridge,
        "exp3_ridge_only": ridge,
    }
    allowed = foot & (dcat > COLLAR_PX)
    quotas_base = [int(round(s * N_DOTS)) for s in shares]
    quotas_base[-1] += N_DOTS - sum(quotas_base)
    results = {}
    chosen = {}
    for ename, surf in experiments.items():
        print("==", ename)
        qs = []
        for (lo, hi), q in zip(bins, quotas_base):
            qs.append(((dcat > lo) & (dcat <= hi), q))
        dots = spaced_topk(surf, allowed, qs)
        # top-up if spacing/quota left shortfall, respecting spacing via second pass
        short = N_DOTS - int(dots.sum())
        if short > 0:
            extra = spaced_topk(surf + dots * -1e9, allowed & ~dots, [(np.ones_like(allowed), short)])
            # spaced_topk above cannot see existing dots; enforce spacing by masking near existing
            near_existing = distance_transform_edt(~dots) < MIN_SPACING
            extra &= ~near_existing
            dots |= extra
        chosen[ename] = dots
        d = dcat[dots]
        results[ename] = dict(
            n_dots=int(dots.sum()),
            share_gt25=float((d > 25).mean()), share_le3=float((d <= 3).mean()),
            median_dcat=float(np.median(d)),
            overlap_vs_h33=dot_overlap(dots.astype(np.float32), h33),
            corroborated_ge2=float((n_agree[dots] >= 2).mean()),
            mean_surface=float(surf[dots].mean()),
        )
        print(results[ename])

    # Pre-registered pick: exp2 (only arm that can add non-fleet dots => new credit)
    dots = chosen["exp2_consensus_plus_ridge"]
    pred = np.zeros(sample.shape, np.float32)
    pred[dots] = 1.0
    # Self-checks before writing anything
    assert np.isfinite(pred).all() and pred.min() >= 0 and pred.max() <= 1
    assert not (dots & cat).any() and not (dots & ~foot).any()
    assert (dcat[dots] > COLLAR_PX).all()

    name = f"gems88-con88-consensus-ridge-{int(dots.sum())}dots-{stamp}-zeros-DO-NOT-SUBMIT"
    out = ROOT / "docs/downloads" / f"{name}.tif"
    note = "H88-CON88 archived research; literal overlap gate must be rerun after any policy change; DO NOT SUBMIT"
    assert len(note) <= 140, len(note)
    from gems57.submission_writer import write_submission
    receipt = write_submission(out, pred, ROOT / "data/bridge/sample_submission.tif",
                               foot, note=note, name=name, catalogue=cat,
                               metadata=dict(experiments=results, contributors=list(CONTRIBUTORS),
                                             excluded_lineage=EXCLUDED_LINEAGE))
    print(json.dumps({"file": receipt["file"], "sha256": receipt["sha256"],
                      "n_dots": int(dots.sum()), "note_chars": len(note)}, indent=2))
    (ROOT / "registry/con88_experiments.json").write_text(
        json.dumps(dict(stamp=stamp, results=results, chosen="exp2_consensus_plus_ridge",
                        sha256=receipt["sha256"], file=receipt["file"]), indent=2) + "\n")
    np.save(ROOT / ".cache/con88_consensus.npy", consensus)
    np.save(ROOT / ".cache/con88_ridge.npy", ridge)

if __name__ == "__main__":
    main()
