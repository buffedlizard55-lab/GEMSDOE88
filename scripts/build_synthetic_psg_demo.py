#!/usr/bin/env python3
"""Build a synthetic pseudogravity-shaped DEMO for testing I/O only.

This is not a geophysical transform, a scientific experiment, a candidate, or a
submission. It draws deterministic synthetic line traces because source data are
not available. Output is confined to evidence/simulated/ and is not linked from
GitHub Pages. Do not repurpose the result for competition submission.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/bridge/sample_submission.tif"
FAULTS = ROOT / "data/bridge/existing_faults.tif"
OUTPUT = ROOT / "evidence/simulated/mag-psg-synthetic-demo.tif"


def run() -> Path:
    if not SAMPLE.is_file() or not FAULTS.is_file():
        raise FileNotFoundError("restore the pinned sample grid and catalogue before building the I/O demo")

    with rasterio.open(SAMPLE) as src:
        sample = src.read(1)
        footprint = np.isfinite(sample)
        profile = src.profile.copy()
        grid = (src.shape, src.crs, src.transform)

    with rasterio.open(FAULTS) as src:
        if (src.shape, src.crs, src.transform) != grid:
            raise ValueError("catalogue grid does not match the sample")
        catalogue = src.read(1) > 0

    height, width = sample.shape
    rng = np.random.default_rng(42)
    demo = np.zeros((height, width), dtype=np.float32)
    # Deliberately artificial, evenly spaced vertical strokes. This has no
    # geological provenance and is not produced by a pseudogravity transform.
    for x in range(100, width - 100, 300):
        x1 = min(x + 5, width)
        demo[1000:min(2000, height), x:x1] = 0.8 * rng.random(
            (min(2000, height) - 1000, x1 - x), dtype=np.float32
        )

    demo[~footprint | catalogue] = 0.0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    profile.update(driver="GTiff", count=1, dtype="float32", nodata=None)
    with rasterio.open(OUTPUT, "w", **profile) as dst:
        dst.write(demo, 1)
        dst.update_tags(
            artifact_status="SIMULATED_NOT_SCIENTIFIC_CANDIDATE",
            method="synthetic vertical strokes; no geophysical transform",
            submission_status="DO_NOT_SUBMIT",
        )

    print(f"Wrote simulated I/O demo only: {OUTPUT.relative_to(ROOT)} — DO NOT SUBMIT")
    return OUTPUT


if __name__ == "__main__":
    run()
