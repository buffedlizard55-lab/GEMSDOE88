#!/usr/bin/env python3
"""IR-88-59 audit of the PROVCREST `promote` verdict (no slot, no portal contact).

Why this exists
---------------
The original promotion compared PROVCREST with the shipped R0 raster on the
hide-and-recover holdout.  R0 was built with the *full* catalogue, so every R0
dot sits outside the 300 m kernel of every withheld segment and R0 scores
~0.004 there by construction (IR-88-20).  Beating that control proves nothing.
This script adds the controls that can fail:

  provcrest_rank   crest-ranked dots (the shipped recipe)           -- replicated
  null_random      seeded random order over ALL eligible pixels, same >=3.5 px
                   spacing, same visible-catalogue collar, same N, NO crest info
  null_lattice     hexagonal lattice with the density that yields ~N dots on the
                   eligible area, NO crest info

and two readouts on identical folds with the unmodified vendored evaluator:
  ALL    every withheld positive
  FAR    only withheld positives > 10 px (1 km) from any visible fault, i.e. the
         "unmapped regime" that the live-scored lineage appears to live in

It also rebuilds the shipped dot mask from the restored inputs and compares it
pixel-for-pixel with the published TIFF (reproducibility check).

Evidence class of every number: HOLDOUT-DTI (gems57-pooled-hide-v2).
Output: registry/provcrest_nullcontrol_audit.json
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gems57 import evaluate_holdout, grid as grid_mod, holdout as holdout_mod  # noqa: E402
import build_provcrest_submission as bps  # noqa: E402
import build_prune_variants as bpv  # noqa: E402

FAR_PX = 10.0
OUT = ROOT / "registry" / "provcrest_nullcontrol_audit.json"


def hex_lattice(eligible: np.ndarray, n_target: int) -> np.ndarray:
    """Hex lattice thinned by `eligible`, spacing tuned so the kept count ~ n_target."""
    area = float(eligible.sum())
    s = np.sqrt(2.0 * area / (np.sqrt(3.0) * n_target))
    best = None
    for scale in np.linspace(0.85, 1.15, 31):
        step = s * scale
        H, W = eligible.shape
        pts = []
        row = 0
        y = 0.0
        while y < H:
            off = 0.0 if row % 2 == 0 else step / 2.0
            xs = np.arange(off, W, step)
            ys = np.full_like(xs, y)
            pts.append(np.column_stack([ys, xs]))
            y += step * np.sqrt(3.0) / 2.0
            row += 1
        P = np.rint(np.vstack(pts)).astype(np.int64)
        P = P[(P[:, 0] < H) & (P[:, 1] < W)]
        m = np.zeros(eligible.shape, dtype=bool)
        m[P[:, 0], P[:, 1]] = True
        m &= eligible
        gap = abs(int(m.sum()) - n_target)
        if best is None or gap < best[0]:
            best = (gap, m)
    return best[1]


def main() -> int:
    t0 = time.time()
    verified = bpv.verify_manifest()
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    foot, catalogue = gd.footprint, gd.catalogue
    d_cat = distance_transform_edt(~catalogue)

    crest, crest_mask, canaries = bps.build_crest(verified, foot, catalogue)
    cy, cx = np.nonzero(crest_mask)
    order = np.argsort(-crest[cy, cx], kind="stable")
    rank_yx = np.column_stack([cy[order], cx[order]])

    # ---- reproducibility: rebuild the shipped file from restored inputs -------------
    prov = json.loads((ROOT / "registry" / "provcrest_run_card.json").read_text())
    shipped_path = ROOT / prov["submission"]["file"]
    eligible_final = crest_mask & foot & ~catalogue & (d_cat > 3.0)
    final_mask = bps.select_dots(rank_yx, eligible_final, foot.shape)
    with rasterio.open(shipped_path) as ds:
        shipped = ds.read(1) > 0
    reproduced = bool(np.array_equal(final_mask, shipped))
    print(f"[audit] reproduced shipped dot mask bit-for-bit: {reproduced} ({time.time()-t0:.0f}s)", flush=True)

    arms = ("provcrest_rank", "null_random", "null_lattice")
    terms = {v: {a: None for a in arms} for v in ("ALL", "FAR")}
    withheld = {"ALL": 0, "FAR": 0}
    nstats = {a: [] for a in arms}
    for seed in (20, 30):
        folds, _ = holdout_mod.buffered_component_draw(gd, seed=seed)
        visible = folds[0]["visible"]
        masked_known = folds[0]["masked_known"]
        d_vis = distance_transform_edt(~visible)
        eligible_all = foot & ~masked_known & (d_vis > 3.0)
        eligible_crest = crest_mask & eligible_all
        rng = np.random.default_rng(88_59_00 + seed)
        ey, ex = np.nonzero(eligible_all)
        rand_yx = np.column_stack([ey, ex])[rng.permutation(len(ey))]
        masks = {
            "provcrest_rank": bps.select_dots(rank_yx, eligible_crest, foot.shape),
            "null_random": bps.select_dots(rand_yx, eligible_all, foot.shape),
            "null_lattice": hex_lattice(eligible_all, bps.N_DOTS),
        }
        for a, m in masks.items():
            nstats[a].append(int(m.sum()))
        for f in folds:
            far_f = copy.copy(f)
            far_f["truth"] = np.asarray(f["truth"], bool) & (d_vis > FAR_PX)
            for view, fold in (("ALL", f), ("FAR", far_f)):
                if not np.asarray(fold["truth"], bool).any():
                    continue
                if view == "FAR" and not (np.asarray(fold["truth"], bool) & np.asarray(f["region"], bool)).any():
                    continue
                withheld[view] += int(np.asarray(fold["truth"], bool).sum())
                for a, m in masks.items():
                    _, t = evaluate_holdout.evaluate(m.astype(np.float32), fold, foot)
                    terms[view][a] = t if terms[view][a] is None else terms[view][a] + t
        print(f"[audit] seed {seed} done ({time.time()-t0:.0f}s) dots={ {a: nstats[a][-1] for a in arms} }", flush=True)

    result = {
        "schema": "gems88.nullcontrol-audit.v1",
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluate_holdout.VERSION,
        "shipped_file": str(shipped_path.relative_to(ROOT)),
        "shipped_sha256": hashlib.sha256(shipped_path.read_bytes()).hexdigest(),
        "reproduced_bit_for_bit_from_restored_inputs": reproduced,
        "far_threshold_px": FAR_PX,
        "dots_per_fold_by_arm": nstats,
        "canaries_max_symmetric_auc": max(canaries.values()),
        "views": {},
    }
    for view in ("ALL", "FAR"):
        pooled = evaluate_holdout.pooled_summary(
            {a: terms[view][a] for a in arms}, draws=1000, seed=520810, candidate="provcrest_rank")
        result["views"][view] = {
            "withheld_positive_pixels": withheld[view] // 1,
            "scores": {k: {"dti": round(float(v["dti"]), 6),
                           "ci95": [round(float(x), 6) for x in v["ci95"]]}
                       for k, v in pooled["scores"].items()},
            "paired_differences_vs_provcrest_rank": pooled["paired_differences"],
        }
        print(f"[audit] {view}: " + json.dumps({k: v['dti'] for k, v in result['views'][view]['scores'].items()}), flush=True)
    result["elapsed_seconds"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(json.dumps(result["views"], indent=1, default=float)[:3000])
    return 0 if reproduced else 3


if __name__ == "__main__":
    raise SystemExit(main())
