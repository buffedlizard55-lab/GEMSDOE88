#!/usr/bin/env python3
"""Compatibility wrapper for CON88 preflight after clearance withdrawal (IR-88-587C7F22-01).

Equal-support preflight bypass was revoked under AGENTS.md / IR-88-B4DFA10C-08.
All candidate entrypoints unconditionally delegate to scripts.generation_guard.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generation_guard import enforce_generation_preflight  # noqa: E402


def enforce_con88_preflight(root: Path = ROOT) -> None:
    enforce_generation_preflight(root)


if __name__ == "__main__":
    enforce_con88_preflight()
