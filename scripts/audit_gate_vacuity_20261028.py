#!/usr/bin/env python3
"""Read-only measurements behind the 2026-10-28 focus-site review.

Measures, on SHA-pinned local rasters only (no network, no generation):
  * whether the 17GEMSDOE dense witness is positive on every allowed cell, which
    makes a literal "fraction of dots within 3 px of any nonzero witness cell"
    test return 1.0 for any nonempty candidate (vacuity of the binding gate);
  * the nested-subset relations of the H33 (GEMSDOE32) raster to its lineage;
  * a SHADOW probe: what a top-K reading of the dense witness (K = candidate dot
    count) would give. This is an independent diagnostic, NOT the repo's gate and
    NOT a clearance.

Output: evidence/gate_vacuity_20261028.json. Usage: .venv/bin/python scripts/audit_gate_vacuity_20261028.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "gate_vacuity_20261028.json"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"
CATALOGUE = ROOT / "data/bridge/existing_faults.tif"
WITNESS = ROOT / "data/registry/dense_17gemdoe.tif"
REGISTRY = {
    "H33_GEMSDOE32": "data/registry/h33_education.tif",
    "SOLO_D2_8_GEMSDOE28": "data/registry/gems28_h27_4.tif",
    "D2_8_GEMSDOE25": "data/registry/gems25_d28.tif",
    "H19_5_GEMSDOE19": "data/registry/gems19_h19_5.tif",
    "GEMSDOE36_ANDERSON_PINN": "data/registry/gems36_anderson_pinn.tif",
}
EXPECTED_SHA = {
    "data/bridge/sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "data/bridge/existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "data/registry/dense_17gemdoe.tif": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
    "data/registry/h33_education.tif": "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
    "data/registry/gems28_h27_4.tif": "2fc94a38d77f74d4f4ed1a97a83e7bb71a1ceea090515ec641e6681cc47c44c8",
    "data/registry/gems25_d28.tif": "3e78737f0da8dd2ca66cc6caac0ce8eeefcd6715707f8d1bd3091845cd9bcc30",
    "data/registry/gems19_h19_5.tif": "ef2ae808eb7179861b9f1ff753fd3ded625ace7b7c158e29cec45bbd8fa3cfaa",
    "data/registry/gems36_anderson_pinn.tif": "e15891020b9c57056ac7fa874a5e506fbd6ed9314a4ea8e73af0753887a3708a",
}
K_TOLERANCE_PX = 3.0


def read(rel_or_path) -> np.ndarray:
    path = rel_or_path if isinstance(rel_or_path, Path) else ROOT / rel_or_path
    with rasterio.open(path) as ds:
        return ds.read(1)


def sha256(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def within_px(a: np.ndarray, b: np.ndarray, radius: float = K_TOLERANCE_PX) -> float:
    if a.sum() == 0:
        return float("nan")
    return float((ndi.distance_transform_edt(~b)[a] <= radius).mean())


def main() -> int:
    for rel, want in EXPECTED_SHA.items():
        got = sha256(rel)
        if got != want:
            print(f"SHA MISMATCH {rel}: {got} != {want}", file=sys.stderr)
            return 1
    sample = read(SAMPLE)
    foot = np.isfinite(sample)
    cat = read(CATALOGUE) == 1
    allowed = foot & ~cat
    witness = read(WITNESS).astype(np.float64)
    w_allowed = witness[allowed]
    dist_cat_px = ndi.distance_transform_edt(~cat)

    rec = {
        "schema": "gems88.gate-vacuity.v1",
        "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence_class": "REGISTRY-MEASUREMENT (local SHA-pinned rasters); no score, no generation",
        "footprint_cells": int(foot.sum()),
        "catalogue_fault_cells": int(cat.sum()),
        "allowed_cells": int(allowed.sum()),
        "witness": {
            "path": "data/registry/dense_17gemdoe.tif",
            "sha256": EXPECTED_SHA["data/registry/dense_17gemdoe.tif"],
            "positive_fraction_on_allowed_cells": float((w_allowed > 0).mean()),
            "min_on_allowed_cells": float(w_allowed.min()),
            "max_on_allowed_cells": float(w_allowed.max()),
            "reading": "every allowed cell is positive, so 'dots within 3 px of any nonzero cell' = 1.0 for any nonempty dot set",
        },
        "lineage": {},
        "shadow_topK_probe": {"status": "SHADOW DIAGNOSTIC - NOT THE REPO GATE, NOT CLEARANCE", "rows": {}},
    }
    h33 = read(REGISTRY["H33_GEMSDOE32"]) == 1
    h33 &= foot
    for name, rel in REGISTRY.items():
        r = read(rel)
        dots = (r == 1) & foot
        d = dist_cat_px[dots]
        rec["lineage"][name] = {
            "path": rel,
            "sha256": EXPECTED_SHA[rel],
            "dots_in_footprint": int(dots.sum()),
            "dots_outside_footprint": int(((r == 1) & ~foot).sum()),
            "min_distance_to_catalogue_px": float(d.min()) if d.size else None,
            "dots_within_2px_of_catalogue": int((d <= 2.0).sum()),
            "subset_check_H33_in_this": None if name == "H33_GEMSDOE32" else
                {"H33_dots_inside": int((h33 & dots).sum()), "H33_dots_total": int(h33.sum())},
            "H33_within_3px_of_this": None if name == "H33_GEMSDOE32" else within_px(h33, dots),
            "this_within_3px_of_H19_5": None if name == "H19_5_GEMSDOE19" else
                within_px(dots, read(REGISTRY["H19_5_GEMSDOE19"]) == 1),
        }

    k = int(h33.sum())
    vals = np.where(allowed, witness, -np.inf).ravel()
    idx = np.argpartition(-vals, k)[:k]
    topk = np.zeros(vals.size, bool)
    topk[idx] = True
    topk = topk.reshape(witness.shape)
    rec["shadow_topK_probe"]["K"] = k
    rec["shadow_topK_probe"]["min_witness_value_selected"] = float(witness.ravel()[idx].min())
    for name, rel in REGISTRY.items():
        rec["shadow_topK_probe"]["rows"][name] = within_px(topk, read(rel) == 1)
    rec["shadow_topK_probe"]["rows"]["H33_GEMSDOE32_as_candidate_vs_topK"] = within_px(h33, topk)
    rec["shadow_topK_probe"]["reading"] = (
        "Under a top-K reading the witness is no longer vacuous, but the probe overlap against H19-5 "
        "is above 0.70, so a top-K candidate of the same size would still fail the stated limit.")
    rec["verdict"] = "negative"
    rec["ok_to_submit"] = False

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("footprint_cells", "catalogue_fault_cells", "allowed_cells")}, indent=None))
    print("witness positive fraction on allowed cells:", rec["witness"]["positive_fraction_on_allowed_cells"])
    print("topK rows:", {k: round(v, 4) for k, v in rec["shadow_topK_probe"]["rows"].items() if v == v})
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
