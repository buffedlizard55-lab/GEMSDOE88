#!/usr/bin/env python3
"""Retired CON88 promotion validator; it cannot approve or emit a candidate.

The former private validator used an unapproved dense-prior equal-support
exception and could write a positive gate. Historical measurements are kept in
research/session-con88-20261025.md and run_card_con88.json, now explicitly
withdrawn. Current candidate CLIs must pass the shared generation guard first.
"""
from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from scripts.generation_guard import enforce_generation_preflight

    enforce_generation_preflight(ROOT)
    # Even if a future policy change removes today's duplicate stop, this
    # retired promotion path must not silently become an approving validator.
    print(json.dumps({
        "decision": "RETIRED_VALIDATOR",
        "reason": "CON88's private equal-support promotion gate was withdrawn; use shared saved-byte audits only.",
        "ok_to_submit": False,
        "verdict": "negative",
    }), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
