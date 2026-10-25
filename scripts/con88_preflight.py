#!/usr/bin/env python3
"""Fail-closed preflight guard for H88-CON88 (IR-88-3C391D97-01).

Historical note: PR #158 introduced a lane-specific preflight wrapper that treated
the equal-support helper `equal_support_dots` as a binding exemption to the
literal 3-pixel registry overlap gate (`<= 0.70`) and returned
`generation_allowed: True`. Under AGENTS.md Rules 2-3 and IR-88-D0C3ADEB-08 /
IR-88-B4DFA10C-08 / IR-88-78CFB743-01 / IR-88-3C391D97-01, equal-support helpers
are diagnostic only and run/build/publish entrypoints have no active-lane
exemption. This module therefore delegates directly to the shared
`enforce_generation_preflight()` guard.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generation_guard import enforce_generation_preflight  # noqa: E402


def enforce_con88_preflight(root: Path = ROOT) -> dict:
    """Delegate unconditionally to the shared literal generation guard."""
    return enforce_generation_preflight(root)


if __name__ == "__main__":
    enforce_con88_preflight()
