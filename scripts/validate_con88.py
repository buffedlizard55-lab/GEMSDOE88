#!/usr/bin/env python3
"""Fail-closed status for the historical CON88 artifact.

The earlier lane-specific equal-support approval was withdrawn. This command
never fits a model, constructs features, writes predictions, or rewrites the
historical gate card. It delegates to the shared literal pre-placement gate.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.generation_guard import inspect

def main() -> int:
    try:
        result = inspect(ROOT)
    except Exception as exc:
        result = {"decision": "AUDIT_ERROR", "error": f"{type(exc).__name__}: {exc}",
                  "generation_allowed": False, "ok_to_submit": False,
                  "verdict": "negative"}
        print(json.dumps(result, indent=2))
        return 1
    result["lane"] = "H88-CON88-HISTORICAL"
    result["artifact_status"] = "RESEARCH_ONLY_DO_NOT_SUBMIT"
    result["reason"] = "Historical equal-support approval withdrawn; literal shared duplicate stop applies."
    print(json.dumps(result, indent=2))
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
