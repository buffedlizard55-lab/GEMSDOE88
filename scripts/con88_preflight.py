#!/usr/bin/env python3
"""Deprecated CON88 compatibility shim; delegate to the one shared literal guard.

The equal-support dense-prior exception used by the historical CON88 release
was withdrawn. This module remains only so older imports fail closed through
the same SHA-pinned pre-placement proof as every other candidate CLI.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def enforce_con88_preflight(root: Path = ROOT) -> None:
    """Compatibility API with no lane-specific bypass or clearance."""
    from scripts.generation_guard import enforce_generation_preflight

    enforce_generation_preflight(Path(root))


if __name__ == "__main__":
    enforce_con88_preflight()
