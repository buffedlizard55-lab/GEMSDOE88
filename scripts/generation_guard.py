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

# Only entrypoints of the CURRENT preregistered lane may construct features or
# dots. Historical/superseded builders remain importable for tests and
# education but exit 2 when dispatched as a CLI (SUPERSEDED_ENTRYPOINT_STOP).
ACTIVE_LANE_ENTRYPOINTS = frozenset({
    "run_sdtl88_experiment.py",
    "build_sdtl88_submission.py",
})


def inspect(root: Path = ROOT) -> dict:
    """Shared preflight under the corrected equal-support protocol (IR-88-SDTL-01).

    The pinned inputs and the dense 17GEMSDOE witness are still re-verified from
    bytes.  A continuous probability surface binds through rank correlation and
    through its equal-support top-n dots at placement time
    (``gems57.uniqueness.binding_duplicate_decision_v5``); it is no longer read
    as a universal dot-overlap stop, because that reading fires on every
    nonempty candidate and therefore cannot be the protocol.  Missing or corrupt
    prerequisites remain an audit error (exit 1).
    """
    from scripts.preflight_mtas88 import inspect as existing_preflight

    prior = existing_preflight(Path(root))
    proof = prior["preplacement_registry_proof"]
    literal_blocked = proof["universal_overlap_blocker"] is True
    return {
        "schema": "gems88.generation-preflight.v2",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": "GENERATION_ALLOWED_PENDING_UNIQUENESS",
        "reason": (
            "Pinned grid, catalogue and witness verified. The dense witness is a continuous "
            "surface positive on every allowed cell; under the shared equal-support rule "
            "(IR-88-SDTL-01) it binds via rank correlation and top-n dots, checked by the builder "
            "on the surface before placement and on the final dots. This is not submit clearance."
        ),
        "literal_reading_would_block": literal_blocked,
        "protocol_correction": "IR-88-SDTL-01",
        "preplacement_registry_proof": proof,
        "generation_allowed": True,
        "ok_to_submit": False,
        "new_rasters_generated": 0,
        "experiments_run": 0,
        "weekly_slots_used": 0,
        "verdict": "pending",
    }


def enforce_generation_preflight(root: Path = ROOT) -> None:
    """Return on GENERATION_ALLOWED_PENDING_UNIQUENESS; exit 2 for a measured stop; 1 for missing/corrupt prerequisites.

    This guard intentionally has no bypass switch. It does not grant clearance
    if a witness is removed or a boolean in a historical run card is edited.
    Unblocking requires a valid shared experiment contract, not human inspection
    of a TIFF or a filename change.
    """
    root = Path(root)
    entrypoint = Path(sys.argv[0]).name
    try:
        result = inspect(root)
        code = 0 if result.get("generation_allowed") is True else 2
        if code == 0 and entrypoint not in ACTIVE_LANE_ENTRYPOINTS:
            result.update(
                decision="SUPERSEDED_ENTRYPOINT_STOP",
                reason=(
                    f"{entrypoint} is a historical lane builder. Only the current preregistered "
                    "lane entrypoints may generate: " + ", ".join(sorted(ACTIVE_LANE_ENTRYPOINTS))
                ),
                generation_allowed=False,
                verdict="negative",
            )
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
    if code != 0:
        raise SystemExit(code)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    enforce_generation_preflight()
