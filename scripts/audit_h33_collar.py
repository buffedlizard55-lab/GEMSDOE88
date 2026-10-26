#!/usr/bin/env python3
"""Independently recheck H33 subset/collar counts using pinned historical rasters.

Read-only geometry audit; the binary disk-dilation method is distinct from the
existing distance-transform lineage audit. Never constructs a model, writes a
prediction or turns an unreceipted score into confirmed evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from gems57 import grid  # noqa: E402
from scripts.audit_literal_protocol import pinned  # noqa: E402
from scripts.restore_inputs import VALIDATION_GROUPS  # noqa: E402

FILES = {
    "d28": "data/registry/gems25_d28.tif",
    "solo": "data/registry/gems28_h27_4.tif",
    "h33": "data/registry/h33_education.tif",
}


def disk_neighbourhood(mask: np.ndarray, radius: int) -> np.ndarray:
    """Pixels at Euclidean center distance <= radius, with no edge wrapping."""
    if mask.ndim != 2 or radius < 0:
        raise ValueError("expected a two-dimensional mask and non-negative radius")
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    return binary_dilation(mask, structure=(x*x + y*y <= radius*radius), border_value=0)


def inspect(root: Path = ROOT) -> dict:
    root = Path(root)
    expected = {dst: digest for group in VALIDATION_GROUPS for _, dst, digest in group[3]}
    required = {
        "data/bridge/sample_submission.tif": grid.SHA256_SAMPLE_SUBMISSION,
        "data/bridge/existing_faults.tif": grid.SHA256_EXISTING_FAULTS,
        **{name: expected[name] for name in FILES.values()},
    }
    for file, digest in required.items():
        pinned(root, file, digest)
    g = grid.load_grid(root / "data/bridge")
    masks = {}
    for label, file in FILES.items():
        with rasterio.open(root / file) as ds:
            if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != (g.shape, g.crs, g.transform):
                raise ValueError(f"historical grid mismatch: {file}")
            values = ds.read(1)
        masks[label] = np.isfinite(values) & (values > 0) & g.footprint
    d28, solo, h33 = (masks[k] for k in ("d28", "solo", "h33"))
    near1 = disk_neighbourhood(g.catalogue, 1)
    near2 = disk_neighbourhood(g.catalogue, 2)
    removed = d28 & ~h33
    d28_solo = d28 & ~solo
    solo_h33 = solo & ~h33
    return {
        "schema": "gems88.h33-collar-crosscheck.v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Read-only Euclidean binary disk dilation of mapped catalogue; no new prediction",
        "sha256_inputs": required,
        "counts": {
            "d28": int(d28.sum()), "solo": int(solo.sum()), "h33": int(h33.sum()),
            "d28_minus_h33": int(removed.sum()),
            "d28_minus_h33_at_most_1px": int((removed & near1).sum()),
            "d28_minus_h33_gt1_at_most_2px": int((removed & ~near1 & near2).sum()),
            "d28_minus_h33_over_2px": int((removed & ~near2).sum()),
            "d28_minus_solo": int(d28_solo.sum()),
            "solo_minus_h33": int(solo_h33.sum()),
            "h33_at_most_2px": int((h33 & near2).sum()),
        },
        "h33_subset_of_d28": not bool((h33 & ~d28).any()),
        "h33_subset_of_solo": not bool((h33 & ~solo).any()),
        "solo_subset_of_d28": not bool((solo & ~d28).any()),
        "organizer_confirmed_score": None,
        "limitations": "Geometry of owner-mirror bytes only; user-reported scores have no receipt and causality is unproven.",
    }


if __name__ == "__main__":
    print(json.dumps(inspect(), indent=2, allow_nan=False))
