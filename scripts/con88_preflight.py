#!/usr/bin/env python3
"""Compatibility name for the shared literal preflight; no CON88 exemption.

Equal-support comparisons are research diagnostics, not authority to override
this user's all-registry overlap rule. See IR-88-96F5F523-01.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def enforce_con88_preflight(root: Path = ROOT) -> None:
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight(root)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    enforce_con88_preflight()
