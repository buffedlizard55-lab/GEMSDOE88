#!/usr/bin/env python3
"""Compatibility entry point for the binding shared generation preflight.

H88-CON88 previously bypassed the literal registry rule by substituting an
"equal-support" dense-raster diagnostic.  That exception is withdrawn by
IR-88-0AB98CD1-01.  Keep this module so historical runners and imports remain
reproducible, but delegate every decision to the same mandatory guard used by
all candidate generators.  There is no CON88-specific allow path.
"""
from __future__ import annotations

from pathlib import Path

from scripts.generation_guard import ROOT, enforce_generation_preflight


def enforce_con88_preflight(root: Path = ROOT) -> None:
    """Fail closed using the shared literal-overlap generation guard."""
    enforce_generation_preflight(Path(root))


if __name__ == "__main__":
    enforce_con88_preflight()
