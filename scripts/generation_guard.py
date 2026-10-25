#!/usr/bin/env python3
"""One project-level stop before any candidate CLI constructs features or dots.

Delegates to the existing shared-template saturation preflight. No alternate
metric, overlap rule, writer, sparse-prior exemption, or approval override.
Imports of historical research modules remain possible for unit tests and
education; invoking a generation CLI is guarded before its other imports.

Session bc757d13 (2026-10-25): preregistered lanes whose frozen protocol
adopts the representation-aware v4 uniqueness decision
(``vendor/gems57/uniqueness.py::binding_duplicate_decision_v4``,
IR-88-249E-01) under the owner's parallel-run protocol take a separate,
equally fail-closed preflight (``_enforce_v4_preregistered``). ONLY the
allowlisted entrypoints below may proceed, only with a frozen preregistration
naming the v4 policy and a passing shared v4 pre-placement proof. Every
other entrypoint keeps the historical behaviour byte-for-byte. Clearing a
preflight never sets ``ok_to_submit``: slot eligibility still requires the
lane's full canary + holdout + final-dot uniqueness + format gates on saved
bytes, and promotion to a real slot remains the owner's separate action.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

V4_PREREGISTERED_ENTRYPOINTS = {
    "run_gtd88_experiment.py": "registry/preregistration_gtd88.json",
}


def _v4_registry_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    reg = root / "data/registry"
    if reg.is_dir():
        paths.extend(sorted(reg.rglob("*.tif")))
    dl = root / "docs/downloads"
    if dl.is_dir():
        paths.extend(p for p in sorted(dl.glob("*.tif")) if "gems88-gtd88" not in p.name)
    sub = root / "submissions"
    if sub.is_dir():
        paths.extend(p for p in sorted(sub.glob("*.tif")) if "gems88-gtd88" not in p.name)
    for extra in (root / "data/siblings_head", root / "data/fleet", root / "data/siblings"):
        if extra.is_dir():
            paths.extend(p for p in sorted(extra.glob("*.tif")) if "gems88-gtd88" not in p.name)
    # De-duplicate identical bytes (same file published in two directories).
    import hashlib

    seen: dict[str, Path] = {}
    for p in paths:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        seen.setdefault(h.hexdigest(), p)
    return sorted(seen.values())


def _enforce_v4_preregistered(root: Path, caller: str) -> None:
    """Fail-closed v4 preflight for allowlisted preregistered lanes only.

    Returns normally (generation may proceed to the lane's own gates) iff the
    frozen preregistration and the shared v4 pre-placement proof both pass.
    SystemExit(2) on a measured universal effective blocker, SystemExit(1)
    on any missing/corrupt prerequisite. Always records the audit JSON.
    """
    result: dict = {
        "schema": "gems88.generation-preflight.v4",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "entrypoint": caller,
        "ok_to_submit": False,
        "weekly_slots_used": 0,
    }
    code = 1
    try:
        prereg_rel = V4_PREREGISTERED_ENTRYPOINTS[caller]
        prereg = json.loads((root / prereg_rel).read_text(encoding="utf-8"))
        if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
            raise ValueError("preregistration is not frozen")
        policy = json.dumps(prereg.get("uniqueness_policy", {}))
        if "binding_duplicate_decision_v4" not in policy:
            raise ValueError("preregistration does not adopt the v4 uniqueness policy")
        sys.path.insert(0, str(root / "vendor"))
        sys.path.insert(0, str(root / "src"))
        from gems57 import grid as _grid, uniqueness as _uniq

        g = _grid.load_grid(root / "data/bridge")
        proof = _uniq.v4_preplacement_proof(
            _v4_registry_paths(root), g.footprint, g.catalogue, n_candidate_dots=37654
        )
        result["preregistration"] = prereg_rel
        result["preregistration_id"] = prereg.get("preregistration_id")
        result["v4_preplacement_proof"] = proof
        # The historical literal reading, verbatim, for the audit trail.
        try:
            result["literal_v3_inspect"] = inspect(root)
        except Exception as exc:  # literal audit is diagnostic here, never a bypass
            result["literal_v3_inspect_error"] = f"{type(exc).__name__}: {exc}"
        if proof["invalid"]:
            result.update(decision="AUDIT_ERROR", generation_allowed=False, verdict="negative")
            code = 1
        elif proof["universal_v4_blocker"]:
            result.update(decision="DUPLICATE_STOP_V4", generation_allowed=False, verdict="negative")
            code = 2
        else:
            result.update(
                decision="CLEAR_V4_PREREGISTERED_EXPERIMENT",
                generation_allowed=True,
                verdict="proceed-to-lane-gates",
                reason=(
                    "No binary dot-field or top-N continuous registry halo covers every allowed "
                    "cell; a nonempty candidate can satisfy the v4 dot test. Final clearance "
                    "still requires surface + final-dot uniqueness, canaries and holdout gates."
                ),
            )
            code = 0
    except SystemExit:
        raise
    except Exception as exc:
        result.update(decision="AUDIT_ERROR", error=f"{type(exc).__name__}: {exc}",
                      generation_allowed=False, verdict="negative")
        code = 1
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    try:
        target = root / ".cache/generation-preflight-v4.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    except OSError:
        pass
    print(payload, end="", file=sys.stderr)
    if code != 0:
        raise SystemExit(code)


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
    of a TIFF or a filename change. Allowlisted preregistered v4 lanes take
    the equally fail-closed ``_enforce_v4_preregistered`` path above.
    """
    root = Path(root)
    caller = Path(sys.argv[0]).name
    if caller in V4_PREREGISTERED_ENTRYPOINTS:
        _enforce_v4_preregistered(root, caller)
        return
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
