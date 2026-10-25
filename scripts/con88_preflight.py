#!/usr/bin/env python3
"""Compatibility entry point for the shared candidate-generation preflight.

IR-88-F55AFF34-01 withdrew CON88's lane-specific equal-support bypass.  The
request requires the overlap stop against any registry raster and requires the
top candidate to beat the current HOLDOUT-DTI best before a slot can be used.
CON88 satisfies neither condition.  Equal-support remains a diagnostic in
``vendor/gems57/uniqueness.py``; it cannot authorize generation.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.generation_guard import enforce_generation_preflight  # noqa: E402


def enforce_con88_preflight(root: Path = ROOT) -> None:
    """Delegate to the one shared fail-closed generation guard."""
    enforce_generation_preflight(Path(root))


if __name__ == "__main__":
    enforce_con88_preflight()
