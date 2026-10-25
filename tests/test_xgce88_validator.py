from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_xgce88.py"


@pytest.mark.parametrize("optimized", [False, True])
def test_xgce88_validator_preserves_negative_slot_verdict(optimized: bool) -> None:
    if not (ROOT / "data/bridge/sample_submission.tif").is_file():
        pytest.skip("hash-pinned validation inputs not restored")
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.extend([str(VALIDATOR), "--require-submit"])
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "literal 1.0>0.70 enforces DO NOT SUBMIT" in result.stdout
    assert "FAIL-CLOSED" in result.stdout
