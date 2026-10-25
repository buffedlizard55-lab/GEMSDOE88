from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_lsc88.py"
CARD = ROOT / "registry/lsc88_run_card.json"


def test_lsc88_run_card_is_fail_closed_research_download() -> None:
    card = json.loads(CARD.read_text())
    mirror = json.loads((ROOT / "docs/data/lsc88_run_card.json").read_text())
    assert card == mirror
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert card["fingerprint_pass"] is False
    assert card["uniqueness"]["literal_dense_witness_overlap_3px"] == 1.0
    assert card["uniqueness"]["literal_dense_witness_pass"] is False
    assert card["organizer_confirmed"] is None
    assert "DO-NOT-SUBMIT" in card["submission_file"]
    assert 0 < len(card["submission_name"]) <= 140
    assert 0 < len(card["submission_note"]) <= 140


@pytest.mark.parametrize("optimized", [False, True])
def test_lsc88_validator_enforces_require_submit_and_strict_cli(optimized: bool) -> None:
    if not (ROOT / "data/bridge/sample_submission.tif").is_file():
        pytest.skip("hash-pinned validation inputs not restored")
    base = [sys.executable, *(["-O"] if optimized else []), str(VALIDATOR)]

    ok_res = subprocess.run(base, cwd=ROOT, text=True, capture_output=True)
    assert ok_res.returncode == 0, ok_res.stdout + ok_res.stderr
    rep = json.loads(ok_res.stdout)
    assert rep["ok"] is True
    assert rep["ok_to_download"] is True
    assert rep["ok_to_submit"] is False
    assert rep["verdict"] == "negative"
    assert rep["gates"]["literal_dense_witness_pass"] is False
    assert rep["gates"]["fingerprint_pass"] is False

    sub_res = subprocess.run([*base, "--require-submit"], cwd=ROOT, text=True, capture_output=True)
    assert sub_res.returncode == 2, sub_res.stdout + sub_res.stderr
    assert "DO NOT SUBMIT" in sub_res.stderr

    typo_res = subprocess.run([*base, "--require-submt"], cwd=ROOT, text=True, capture_output=True)
    assert typo_res.returncode == 2, typo_res.stdout + typo_res.stderr
