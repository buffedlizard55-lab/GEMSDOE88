#!/usr/bin/env python3
"""Compatibility wrapper for the binding project generation preflight.

CON88 once used a lane-specific equal-support exception for dense probability
rasters. That exception conflicts with the supplied literal all-registry rule
and was withdrawn. Keep this import path for historical runners, but delegate
without alteration to :mod:`scripts.generation_guard`; there is no bypass.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.generation_guard import enforce_generation_preflight  # noqa: E402


def enforce_con88_preflight(root: Path = ROOT) -> None:
    """Apply the same fail-closed literal preflight as every candidate CLI."""
    enforce_generation_preflight(Path(root))


if __name__ == "__main__":
    enforce_con88_preflight()
