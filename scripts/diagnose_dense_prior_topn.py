#!/usr/bin/env python3
"""Diagnostic: how do published candidates score against the dense 17GEMSDOE prior
under a top-N like-for-like dot definition?

The literal shared gate (vendor/gems57/uniqueness.py::_dots) treats every finite
cell > 0 as a 'dot'. 17GEMSDOE is a continuous probability surface with 5,167,373
positive cells, so every candidate has forward 3-px overlap 1.0 with it and the
literal gate can never pass. This script does NOT change the gate. It reports a
clearly labelled alternative: the witness's dots are its N highest-valued cells,
N = that candidate's own dot count. Reuses the shared _near() helper.

Output: evidence/dense_prior_topn_diagnostic.json (decision is left to the user).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.uniqueness import _near, _dots  # noqa: E402  (shared helper, not a fork)
from gems57.metric import RADIUS_PX  # noqa: E402

WITNESS = ROOT / "data/registry/dense_17gemdoe.tif"
OUT = ROOT / "evidence/dense_prior_topn_diagnostic.json"
CANDIDATE_GLOB = "docs/downloads/*.tif"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(1).astype("float64"), src.crs.to_string(), src.transform, src.shape


def main() -> int:
    w, w_crs, w_tr, w_shape = read(WITNESS)
    w_vals = np.where(np.isfinite(w), w, -np.inf)
    rows = []
    for cand in sorted(ROOT.glob(CANDIDATE_GLOB)):
        c, c_crs, c_tr, c_shape = read(cand)
        if c_shape != w_shape or c_crs != w_crs or c_tr != w_tr:
            rows.append({"candidate": cand.name, "error": "grid mismatch vs witness"})
            continue
        c_dots = _dots(c)
        n = int(c_dots.sum())
        if n == 0:
            rows.append({"candidate": cand.name, "candidate_sha256": sha256(cand), "error": "no dots"})
            continue
        # top-N cells of the witness by probability (ties broken by flat index, deterministic)
        flat = w_vals.ravel()
        idx = np.argpartition(-flat, n - 1)[:n]
        w_top = np.zeros(flat.shape, dtype=bool)
        w_top[idx] = True
        w_top = w_top.reshape(w.shape)
        fwd = float(_near(w_top, RADIUS_PX)[c_dots].mean())
        # literal shared rule: every finite positive witness cell is a 'dot'
        w_all = _dots(w)
        literal_fwd = float(_near(w_all, RADIUS_PX)[c_dots].mean())
        rev = float(_near(c_dots, RADIUS_PX)[w_top].mean())
        rows.append({
            "candidate": cand.name,
            "candidate_sha256": sha256(cand),
            "candidate_dots": n,
            "witness_topN_threshold_value": float(flat[idx].min()),
            "literal_forward_3px_overlap_vs_all_positive_witness_cells": round(literal_fwd, 6),
            "forward_3px_overlap_vs_witness_topN": round(fwd, 6),
            "reverse_3px_overlap_witness_topN_within_3px_of_candidate": round(rev, 6),
            "passes_0_70_like_for_like": bool(fwd <= 0.70),
        })
    literal = {"witness": WITNESS.name, "witness_sha256": sha256(WITNESS),
               "witness_positive_cells": int((w > 0).sum()),
               "literal_forward_overlap_all_candidates": 1.0,
               "note": "literal gate: every positive cell is a dot -> 1.0 for any candidate"}
    out = {
        "schema": "gems88.dense-prior-topn-diagnostic.v1",
        "status": "DIAGNOSTIC ONLY - does not change the shared gate and grants no submission",
        "radius_px": RADIUS_PX, "overlap_limit": 0.70,
        "literal_rule": literal,
        "topN_like_for_like": rows,
        "count_passing_topN": sum(1 for r in rows if r.get("passes_0_70_like_for_like")),
        "count_candidates": len(rows),
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("count_passing_topN", "count_candidates")}, indent=2))
    for r in rows:
        print(r.get("candidate"), r.get("candidate_dots"), r.get("forward_3px_overlap_vs_witness_topN"), r.get("error", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
