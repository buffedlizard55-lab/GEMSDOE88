#!/usr/bin/env python3
"""Read-only, pinned-byte H33 lineage audit. No copied/exported predictions.

Reuses the existing forensic raster readers. Reports geometry only, not hidden
labels, an estimated leaderboard score, or a causal interpretation of pruning.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from gems57 import grid  # noqa: E402
from scripts.forensics_h33 import LINEAGE, dots_of, sha  # noqa: E402
from scripts.restore_inputs import VALIDATION_GROUPS  # noqa: E402
from scripts.audit_literal_protocol import pinned  # noqa: E402


def inspect(root: Path = ROOT) -> dict:
    root = Path(root)
    expected = {dst: digest for group in VALIDATION_GROUPS for _, dst, digest in group[3]}
    # Grid parity alone does not authenticate the footprint or catalogue values.
    # Verify both inputs before deriving distances or any lineage conclusions.
    pinned(root, "data/bridge/sample_submission.tif", grid.SHA256_SAMPLE_SUBMISSION)
    pinned(root, "data/bridge/existing_faults.tif", grid.SHA256_EXISTING_FAULTS)
    g = grid.load_grid(root / "data/bridge")
    dcat = distance_transform_edt(~g.catalogue)
    masks = []
    rows = []
    for label, filename, _unverified_claim in LINEAGE:
        relative = f"data/registry/{filename}"
        path = root / relative
        if sha(path) != expected[relative]:
            raise ValueError(f"lineage raster pin mismatch: {filename}")
        with rasterio.open(path) as source:
            if (source.shape, source.crs, source.transform) != (g.shape, g.crs, g.transform):
                raise ValueError(f"lineage grid mismatch: {filename}")
        dots, _ = dots_of(path, g.footprint)
        masks.append(dots)
        rows.append({"label": label, "file": relative, "sha256": sha(path),
                     "positive_pixels": int(dots.sum())})
    h19, d28, solo, h33 = masks
    removed = d28 & ~h33
    nn, _ = cKDTree(np.column_stack(np.nonzero(h33))).query(
        np.column_stack(np.nonzero(h33)), k=2)
    return {
        "schema": "gems88.h33-lineage-audit.v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "REGISTRY-MEASUREMENT_NOT_A_PERFORMANCE_SCORE",
        "inputs": rows,
        "h33_subset_of_d28": bool(not (h33 & ~d28).any()),
        "h33_subset_of_solo": bool(not (h33 & ~solo).any()),
        "h33_subset_of_h19": bool(not (h33 & ~h19).any()),
        "d28_to_h33_removed_pixels": int(removed.sum()),
        "removed_pixels_all_within_2px_catalogue": bool((dcat[removed] <= 2).all()),
        "h33_positive_within_2px_catalogue": int((h33 & (dcat <= 2)).sum()),
        "h33_minimum_nearest_neighbour_px": float(nn[:, 1].min()),
        "h33_median_catalogue_distance_px": float(np.median(dcat[h33])),
        "organizer_confirmed_score": None,
        "new_rasters_generated": 0,
        "limitations": [
            "Geometry is measured from owner-mirror bytes, not hidden organizer truth.",
            "The supplied 0.2778 is an unverified claim; no portal receipt is present.",
            "A nested thinning/collar-removal lineage is not proof of causal score improvement.",
        ],
    }


if __name__ == "__main__":
    result = inspect()
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    for name in ("evidence/h33_lineage_recheck.json", "docs/data/h33_lineage_recheck.json"):
        (ROOT / name).write_text(text)
    print(text)
