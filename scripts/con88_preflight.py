#!/usr/bin/env python3
"""Compatibility entrypoint for the shared, literal generation guard.

CON88 previously had an equal-support exception for the dense registry witness.
That exception is withdrawn: the user's binding protocol measures literal
forward overlap against every registry raster, so a fully positive witness is
a stop, not an exemption. Keep this wrapper only so old CLI imports fail closed
through the same shared guard as every other candidate.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def enforce_con88_preflight(root: Path = ROOT) -> None:
    """Delegate to the project-wide preflight; never grant lane-specific bypass."""
    root = Path(root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts.generation_guard import enforce_generation_preflight

    enforce_generation_preflight(root)


if __name__ == "__main__":
    enforce_con88_preflight()
