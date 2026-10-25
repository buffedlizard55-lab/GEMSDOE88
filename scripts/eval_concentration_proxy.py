#!/usr/bin/env python3
"""REPORT-ONLY hide-and-recover PROXY for the CONCENTRATION variants.

This is *not* a gate and *never* a score.  It re-uses the repo's shared
instrument (``vendor/gems57/holdout.buffered_component_draw`` +
``vendor/gems57/evaluate_holdout``) with the split version recorded in
``registry/holdout_split.json``: whole catalogue components withheld inside
label-blind eroded quadrants, seeds 20 and 21, 3 px context buffer, 12 px
boundary buffer, 22,893 withheld positive pixels.

Why the number is weak evidence for this axis
---------------------------------------------
R0 was built with a 2 px collar around the *full* catalogue, withheld
components included.  So the proxy rewards a dot that sits 2-3 px from a
withheld strand -- geometry the candidate already knew about -- and says
nothing about the km-scale prior that CONCENTRATION actually bets on.  It is
reported because the brief asks for it, with the caveat printed alongside.

Output: ``registry/concentration_proxy.json`` (PROXY labels only).
"""

from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vendor.gems57 import evaluate_holdout, holdout  # noqa: E402
from vendor.gems57.grid import load_grid  # noqa: E402

RELEASES = ROOT / "releases"
OUT = ROOT / "registry" / "concentration_proxy.json"
SEEDS = (20, 21)


def arm_paths() -> dict:
    report = json.loads((ROOT / "registry" / "concentration_report.json").read_text())
    arms = {"R0_parent": ROOT / "data" / "registry" / "h33_education.tif"}
    for vid, v in report["variants"].items():
        arms[vid.split("-CONC")[1].split("-2026")[0]] = ROOT / v["zeros"]["path"]
    return arms


def main() -> int:
    grid = load_grid(ROOT / "data" / "bridge")
    folds = []
    for seed in SEEDS:
        f, _quad = holdout.buffered_component_draw(grid, seed=seed, hide_frac=0.20,
                                                   buffer_px=3, boundary_px=12)
        folds.extend(f)

    arms = arm_paths()
    preds = {}
    for name, path in arms.items():
        with rasterio.open(path) as src:
            arr = src.read(1).astype(np.float64)
        arr = np.where(np.isfinite(arr), arr, 0.0)
        assert arr.shape == grid.footprint.shape
        preds[name] = arr

    terms = {name: None for name in arms}
    per_fold = {name: {} for name in arms}
    for fold in folds:
        for name, pred in preds.items():
            res, t = evaluate_holdout.evaluate(pred, fold, grid.footprint,
                                               block_side=200)
            per_fold[name][f"{fold['receipt']['seed']}_{fold['name']}"] = res["dti"]
            terms[name] = t if terms[name] is None else terms[name] + t

    withheld = int(sum(f["receipt"]["withheld_positive_pixels"] for f in folds))
    summary = evaluate_holdout.pooled_summary(terms, candidate="R0_parent",
                                              draws=1000, seed=88022)
    out = {
        "evidence_class": "PROXY",
        "evaluator_version": evaluate_holdout.VERSION,
        "split_version": folds[0]["receipt"]["split_version"],
        "seeds": list(SEEDS),
        "n_folds": len(folds),
        "withheld_positive_pixels": withheld,
        "alpha": 0.2, "beta": 0.8, "triangular_radius_m": 300.0,
        "caveat": ("Catalogue hide-and-recover only. R0's 2 px collar was computed "
                   "on the full catalogue, so this instrument partly rewards geometry "
                   "the candidate already knew. It is not a gate, not a live score, "
                   "and not evidence about km-scale priors."),
        "report_only_others": {
            "leakage_canary": ("not applicable: this axis uses no feature channel -- the only inputs are "
                               "the parent raster and the pinned catalogue geometry, so there is no "
                               "single-feature AUC to test"),
            "sgmc_control": "not applicable: no SGMC layer is used by this axis",
        },
        "pooled": summary,
        "per_fold_dti": per_fold,
        "delta_vs_parent_PROXY": {
            name: {
                "delta": summary["scores"][name]["dti"] - summary["scores"]["R0_parent"]["dti"],
                "paired_ci95": summary["paired_differences"][name]["ci95"],
            }
            for name in arms if name != "R0_parent"
        },
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    for name in arms:
        s = summary["scores"][name]
        print(f"{name:22s} PROXY_DTI={s['dti']:.4f} CI={[round(x,4) for x in s['ci95']]} "
              f"withheld={s['withheld_positive_pixels']}")
    for name, d in out["delta_vs_parent_PROXY"].items():
        print(f"delta {name:20s} {d['delta']:+.4f}  paired CI {[round(x,4) for x in d['paired_ci95']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
