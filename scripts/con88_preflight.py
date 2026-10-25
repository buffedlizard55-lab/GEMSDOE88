#!/usr/bin/env python3
"""Compatibility alias for the project's single literal generation guard.

The former equal-support exception is withdrawn (IR-88-89A41360-01). Dense
prior diagnostics remain available, but candidate generation always delegates
to the shared pre-placement literal-rule guard.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.generation_guard import enforce_generation_preflight

def enforce_con88_preflight(root: Path = ROOT) -> None:
    """Backward-compatible name; enforce the one shared guard without bypass."""
    enforce_generation_preflight(root)

if __name__ == "__main__":
    enforce_generation_preflight()
