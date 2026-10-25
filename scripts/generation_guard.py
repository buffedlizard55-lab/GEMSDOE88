#!/usr/bin/env python3
"""One project-level stop before any candidate CLI constructs features or dots.

Delegates to the existing shared-template saturation preflight. No alternate
metric, overlap rule, writer, sparse-prior exemption, or approval override.
Imports of historical research modules remain possible for unit tests and
education; invoking a generation CLI is guarded before its other imports.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def inspect(root: Path = ROOT) -> dict:
    # Lazy import: an environment/import failure is a failed preflight, never
    # an excuse to continue into a builder with a stale stored approval.
    from scripts.preflight_mtas88 import inspect as existing_preflight

    prior = existing_preflight(Path(root))
    proof = prior["preplacement_registry_proof"]
    blocked = proof["universal_overlap_blocker"] is True
    return {
        "schema": "gems88.generation-preflight.v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": "DUPLICATE_STOP" if blocked else "INCOMPLETE_REGISTRY_GATE",
        "reason": (
            "Every nonempty allowed prediction overlaps the pinned registry witness; "
            "stop BEFORE feature construction, fitting, placement and writing."
            if blocked else
            "No universal witness is not a complete surface/final-dot uniqueness pass. "
            "A newly validated shared protocol and complete experiment gate are required."
        ),
        "preplacement_registry_proof": proof,
        "generation_allowed": False,
        "ok_to_submit": False,
        "new_rasters_generated": 0,
        "experiments_run": 0,
        "weekly_slots_used": 0,
        "verdict": "negative",
    }


def enforce_generation_preflight(root: Path = ROOT) -> None:
    """Exit 2 for a measured stop; 1 for missing/corrupt prerequisites.

    This guard intentionally has no bypass switch. It does not grant clearance
    if a witness is removed or a boolean in a historical run card is edited.
    Unblocking requires a valid shared experiment contract, not human inspection
    of a TIFF or a filename change.
    """
    root = Path(root)
    try:
        result = inspect(root)
        code = 2
    except Exception as exc:  # fail-closed CLI boundary, including dependency failures
        result = {
            "schema": "gems88.generation-preflight.v1",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "decision": "AUDIT_ERROR",
            "error": f"{type(exc).__name__}: {exc}",
            "generation_allowed": False,
            "ok_to_submit": False,
            "new_rasters_generated": 0,
            "experiments_run": 0,
            "weekly_slots_used": 0,
            "verdict": "negative",
        }
        code = 1
    result["entrypoint"] = Path(sys.argv[0]).name
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    # A transient audit is useful but cannot be a dependency for stopping.
    try:
        target = root / ".cache/generation-preflight.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    except OSError:
        pass
    print(payload, end="", file=sys.stderr)
    raise SystemExit(code)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    enforce_generation_preflight()
