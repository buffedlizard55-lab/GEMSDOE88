#!/usr/bin/env python3
"""Experiments 2 and 3 (IR-88-59): single-factor tests on the PROVCREST recipe.

``python scripts/exp_provcrest_spacing.py``      Exp 2: spacing sweep (below)
``python scripts/exp_provcrest_spacing.py count`` Exp 3: dot-count sweep
  N in {20,000, 28,000, 37,654 (shipped), 50,000, 65,000} at spacing 3.5 px, same
  ranked pool/collar -> registry/provcrest_count_experiment.json.  DTI theory
  (metric.py): a marginal dot helps iff its kernel credit > alpha*DTI, so the
  optimal N falls as the realised DTI rises; this reports the holdout regime only.

Factor: minimum mutual dot spacing S in {3.0, 3.5 (shipped), 4.5} px with the
crest-ranked order, pool, collar and N=37,654 held fixed.  S=3.0 matches the
live-scored dotted lineage (nn median 3.00, k(3.0)=0 so kernels just touch).
Evidence class: HOLDOUT-DTI (gems57-pooled-hide-v2).  No slot, no portal.
Output: registry/provcrest_spacing_experiment.json
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import json, sys, time
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from gems57 import evaluate_holdout, grid as grid_mod, holdout as holdout_mod  # noqa: E402
import build_provcrest_submission as bps  # noqa: E402
import build_prune_variants as bpv  # noqa: E402

SPACINGS = (3.0, 3.5, 4.5)
COUNTS = (20_000, 28_000, 37_654, 50_000, 65_000)


def select(cand_yx, eligible, shape, spacing, n=bps.N_DOTS):
    r = int(np.ceil(spacing))
    disk = np.array([(dy, dx) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
                     if dy * dy + dx * dx < spacing * spacing], dtype=np.int64)
    blocked = np.zeros(shape, bool); out = np.zeros(shape, bool); H, W = shape; k = 0
    for y, x in cand_yx:
        if k >= n:
            break
        if not eligible[y, x] or blocked[y, x]:
            continue
        out[y, x] = True; k += 1
        ys = y + disk[:, 0]; xs = x + disk[:, 1]
        ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
        blocked[ys[ok], xs[ok]] = True
    if k != n:
        raise RuntimeError(f"pool exhausted at spacing {spacing}: {k}/{n}")
    return out


def main():
    count_mode = len(sys.argv) > 1 and sys.argv[1] == "count"
    arms = ([(f"N{n}", 3.5, n) for n in COUNTS] if count_mode
            else [(f"S{s}", s, bps.N_DOTS) for s in SPACINGS])
    ref = "N37654" if count_mode else "S3.5"
    t0 = time.time()
    verified = bpv.verify_manifest()
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    foot, catalogue = gd.footprint, gd.catalogue
    crest, crest_mask, canaries = bps.build_crest(verified, foot, catalogue)
    cy, cx = np.nonzero(crest_mask)
    o = np.argsort(-crest[cy, cx], kind="stable")
    rank_yx = np.column_stack([cy[o], cx[o]])
    terms = {a[0]: None for a in arms}
    for seed in (20, 30):
        folds, _ = holdout_mod.buffered_component_draw(gd, seed=seed)
        d_vis = distance_transform_edt(~folds[0]["visible"])
        elig = crest_mask & foot & ~folds[0]["masked_known"] & (d_vis > 3.0)
        for label, s, n in arms:
            m = select(rank_yx, elig, foot.shape, s, n).astype(np.float32)
            for f in folds:
                _, t = evaluate_holdout.evaluate(m, f, foot)
                terms[label] = t if terms[label] is None else terms[label] + t
        print(f"seed {seed} done {time.time()-t0:.0f}s", flush=True)
    pooled = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810, candidate=ref)
    out = {"schema": "gems88.spacing-experiment.v1", "evidence_class": "HOLDOUT-DTI",
           "evaluator_version": evaluate_holdout.VERSION, "reference_arm": ref + " (shipped)",
           "scores": {k: {"dti": round(float(v["dti"]), 6), "ci95": [round(float(x), 6) for x in v["ci95"]],
                          "withheld_positive_pixels": int(v["withheld_positive_pixels"])}
                      for k, v in pooled["scores"].items()},
           "paired_differences_vs_reference": pooled["paired_differences"],
           "elapsed_seconds": round(time.time() - t0, 1)}
    (ROOT / "registry" / ("provcrest_count_experiment.json" if count_mode else "provcrest_spacing_experiment.json")).write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
