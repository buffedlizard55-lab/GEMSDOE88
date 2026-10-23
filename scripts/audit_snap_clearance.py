#!/usr/bin/env python3
"""Geometry-only feasibility gate for a literal R0 -> SNAP <=2 px experiment.

Only SHA-pinned inputs are opened. The complete R0 lineage and both byte hashes
are checked before inspecting any pixels. No hidden labels or submission portal
are consulted. This does not propose a raster or consume a weekly slot.

If one source dot at d_cat < 3 px has no destination in the footprint at
>=3 px within its 2 px Euclidean window, *no* bijective SNAP of every R0 dot
can satisfy both constraints. Dot collisions/spacing can only make this harder.
"""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
from scripts import build_prune_variants as bpv  # noqa: E402

OUT = ROOT / "evidence" / "session_20261023_snap_clearance.json"


def reachability(parent: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray,
                 *, radius_px: float = 2.0, clearance_px: float = 3.0) -> dict:
    """Exact nearest-legal-pixel distances, without collisions or any ranking.

    An invalid source dot must reach a pixel inside footprint at >= clearance;
    this is a necessary, not sufficient, condition for a fixed-count SNAP.
    """
    if parent.shape != footprint.shape or parent.shape != catalogue.shape:
        raise ValueError("grid shape mismatch")
    if radius_px <= 0 or clearance_px <= 0:
        raise ValueError("radii must be positive")
    if np.any(parent & ~footprint) or np.any(catalogue & ~footprint):
        raise ValueError("parent and catalogue must be within the footprint")
    if np.any(parent & catalogue):
        raise ValueError("parent has catalogue mass")

    d_cat = distance_transform_edt(~catalogue)
    invalid = parent & (d_cat < clearance_px)
    legal = footprint & ~catalogue & (d_cat >= clearance_px)
    if not np.any(legal):
        raise ValueError("no legal destination exists anywhere")
    # Distance to the closest legal destination on the integer grid. No need
    # for an arbitrary window, feature field, geologist prior, or tie-break.
    nearest = distance_transform_edt(~legal)
    y, x = np.nonzero(invalid)
    required = nearest[y, x]
    unreachable = required > radius_px + 1e-12
    coords = [
        {"row": int(yy), "col": int(xx), "catalogue_px": round(float(d_cat[yy, xx]), 6),
         "min_legal_displacement_px": round(float(nearest[yy, xx]), 6)}
        for yy, xx in zip(y[unreachable], x[unreachable])
    ]
    return {
        "parent_dots": int(parent.sum()),
        "footprint_px": int(footprint.sum()),
        "catalogue_px": int(catalogue.sum()),
        "max_snap_displacement_px": radius_px,
        "minimum_catalogue_clearance_px": clearance_px,
        "n_parent_below_clearance": int(invalid.sum()),
        "below_clearance_by_distance_px": {
            f"{key:.6f}": count for key, count in sorted(
                Counter(float(x) for x in d_cat[invalid]).items()
            )
        },
        "n_with_legal_destination_within_window_ignoring_occupancy": int((~unreachable).sum()),
        "n_without_any_legal_destination_within_window": int(unreachable.sum()),
        "min_required_displacement_px": round(float(required.min()), 6) if len(required) else None,
        "max_required_displacement_px": round(float(required.max()), 6) if len(required) else None,
        "unreachable_sources": coords,
        "pure_snap_possible": not np.any(unreachable),
    }


def main() -> int:
    verified = bpv.verify_manifest()
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot, cat, r0 = lineage["foot"], lineage["catalogue"], lineage["r0"]
    result = reachability(r0, foot, cat)
    # The strict >3 px collar used by previous scripts is not the brief's
    # inclusive >=3 px; report its obstruction separately, not as a gate.
    strict = reachability(r0, foot, cat, clearance_px=np.nextafter(3.0, np.inf))
    with (ROOT / "ledger" / "submissions.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if any(row["parent"] == bpv.PARENT_ID and row["axis"] == "SNAP"
           and row["value"] == "clear3-r2" for row in rows):
        raise ValueError("this SNAP value was already built; do not repeat it")
    report = {
        "schema": "gems88.snap-clearance-feasibility.v1",
        "evidence": "GEOMETRY / not a score or a built variant",
        "date_utc": "2026-10-23",
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "seed": "not used (deterministic geometry)",
        "manifest_inputs_sha256_and_bytes_verified": len(verified),
        "r0_rebuilt_zeros_sha256": lineage["rebuilt_zeros_sha256"],
        "r0_rebuilt_nan_sha256": lineage["rebuilt_nan_sha256"],
        "axis_under_test": "SNAP",
        "literal_inclusive_clearance": result,
        "historical_strictly_greater_than_3px_clearance": {
            "n_parent_below_clearance": strict["n_parent_below_clearance"],
            "n_without_any_legal_destination_within_window": strict["n_without_any_legal_destination_within_window"],
        },
        "decision": "STOP_NO_PURE_R0_SNAP_VARIANT" if not result["pure_snap_possible"] else "UNRESOLVED_COLLISION_AND_SPACING",
        "explanation": "Even ignoring other dots and spacing, each unreachable R0 dot cannot move <=2 px to the required >=3 px catalogue clearance. Retaining it violates clearance; moving it further or replacing it elsewhere violates the R0 SNAP-only, 1-to-1 <=2 px treatment. No new (parent,axis,value) or SHA was registered.",
        "slots_used": 0,
        "new_ledger_rows": 0,
        "no_hidden_labels_used": True,
    }
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"decision": report["decision"],
                      "n_unreachable": result["n_without_any_legal_destination_within_window"],
                      "n_invalid_parent": result["n_parent_below_clearance"],
                      "report": str(OUT.relative_to(ROOT))}, indent=2))
    return 0 if not result["pure_snap_possible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
