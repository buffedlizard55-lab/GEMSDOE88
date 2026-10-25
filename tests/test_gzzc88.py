from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_gzzc88.py"
CARD = ROOT / "registry/gzzc88_run_card.json"


def test_gzzc88_run_card_is_fail_closed_research_download():
    card = json.loads(CARD.read_text())
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert card["weekly_slots_used"] == 0
    assert card["organizer_confirmed"] is None
    assert card["uniqueness"]["literal_dense_witness_overlap"] == 1.0
    assert card["uniqueness"]["unique_like_for_like"] is True
    assert card["uniqueness"]["max_3px_overlap_disc"] <= 0.70
    assert card["leakage_canary"]["max_symmetric_auc"] <= 0.90
    assert card["fingerprint"]["share_gt25"] >= 0.35
    assert card["fingerprint"]["share_le2"] == 0.0
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert 0 < len(card["submission_name"]) <= 140
    assert 0 < len(card["submission_note"]) <= 140
    assert "DO-NOT-SUBMIT" in Path(card["download"]).name
    web = json.loads((ROOT / "docs/data/gzzc88_run_card.json").read_text())
    assert web == card


@pytest.mark.parametrize("optimized", [False, True])
def test_gzzc88_validator_preserves_negative_slot_verdict(optimized: bool) -> None:
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
