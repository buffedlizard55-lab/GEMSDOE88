#!/usr/bin/env python3
"""Compatibility wrapper for the retired H88-CON88 preflight exception.

CON88 no longer has a private/equal-support authorization path. Every CLI
entrypoint delegates to the single shared, fail-closed generation guard.
"""
from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _root = _GuardPath(__file__).resolve().parents[1]
    _guard_sys.path.insert(0, str(_root))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def enforce_con88_preflight(root: Path = ROOT) -> None:
    """Backward-compatible name; enforce the shared policy without exception."""
    sys.path.insert(0, str(Path(root).resolve()))
    from scripts.generation_guard import enforce_generation_preflight

    enforce_generation_preflight(root)
