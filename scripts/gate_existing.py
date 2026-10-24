#!/usr/bin/env python3
"""Apply the v3 fingerprint + uniqueness gate to the *earlier* GEMSDOE88 research rasters (read-only).

Output: evidence/existing_candidates_gate_20261024.json.  Purpose: show how H88-ADHR (previous headline)
and siblings look under the same rules as the new candidate.  Does not change any earlier receipt.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import grid as grid_mod  # noqa: E402
from gems88 import gate, registry_paths  # noqa: E402

SKIP = "gems88-phys44"


def main():
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    sample = ROOT / "data/bridge/sample_submission.tif"
    d_cat = ndi.distance_transform_edt(~cat)
    out = []
    for tif in sorted((ROOT / "docs/downloads").glob("*.tif")):
        if SKIP in tif.name:
            continue
        vals = gate.read_values(tif, fp)
        dots = (vals > 0) & fp
        dc = d_cat[dots]
        reg = [(l, p) for l, p in registry_paths.registry_list(exclude=(SKIP, tif.name)) if p.resolve() != tif.resolve()]
        rep = gate.uniqueness_report(tif, reg, fp)
        portal = gate.portal_validate(tif, sample, fp)
        out.append(dict(file=tif.name, sha256=gate.sha256_file(tif), dots=int(dots.sum()),
                        fingerprint=dict(median_d_cat_px=float(np.median(dc)), share_le2=float((dc <= 2).mean()),
                                         share_gt10=float((dc > 10).mean()), share_gt25=float((dc > 25).mean())),
                        fingerprint_screen_pass=bool((dc <= 2).mean() == 0 and (dc > 25).mean() >= 0.35),
                        unique_like_for_like=rep["unique_like_for_like"], unique_literal=rep["unique_literal"],
                        worst_like_for_like_overlap=rep["worst_like_for_like_overlap"], like_for_like_blockers=rep["like_for_like_blockers"],
                        portal_ok_values_and_grid=portal["ok"], portal_layout_parity_with_sample=portal["layout_parity_with_sample"],
                        portal_problems=portal["problems"]))
        print(out[-1]["file"][:70], out[-1]["fingerprint"], out[-1]["unique_like_for_like"], flush=True)
    (ROOT / "evidence/existing_candidates_gate_20261024.json").write_text(json.dumps(
        dict(policy=gate.POLICY_VERSION, note="read-only comparison; earlier receipts unchanged", rows=out), indent=1, default=float))


if __name__ == "__main__":
    main()
