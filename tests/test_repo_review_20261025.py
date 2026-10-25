from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88.review import (  # noqa: E402
    HYPOTHESES,
    hypothesis_queue,
    safe_note,
    validate_hypothesis_queue,
)


def test_historical_review_retains_its_original_five_hypotheses() -> None:
    queue = hypothesis_queue()
    validate_hypothesis_queue(queue)
    assert len(queue) == 5
    assert [row["rank"] for row in queue] == [1, 2, 3, 4, 5]
    assert [row["id"] for row in queue] == ["H88-MTAS", "H88-PRAN", "H88-FARC", "H88-TCONS", "H88-FLAC"]
    assert all(row["status"] == "UNTESTED" for row in queue)
    assert all(row["layers"] for row in queue)
    assert all(row["non_fault_mimic"] for row in queue)
    assert len(HYPOTHESES) == len(queue)


def test_safe_note_rejects_overlong_text_without_truncation() -> None:
    note = "x" * 140
    assert safe_note(note) == note
    with pytest.raises(ValueError):
        safe_note("x" * 141)
    with pytest.raises(ValueError):
        safe_note("")


def test_published_review_is_fail_closed_and_copies_match() -> None:
    evidence = json.loads((ROOT / "evidence/repo_review_20261025.json").read_text())
    pages = json.loads((ROOT / "docs/data/repo_review_20261025.json").read_text())
    assert evidence == pages
    assert evidence["schema"] == "gems88.repo-review-20261025.v1"
    assert evidence["review_status"] == "DUPLICATE_STOP"
    assert evidence["new_tif"]["generated"] is False
    assert evidence["submission"]["ok_to_submit"] is False
    assert evidence["submission"]["weekly_slots_used"] == 0
    assert evidence["holdout"]["status"].startswith("NOT RUN")
    assert evidence["preplacement_registry_audit"]["universal_overlap_blocker"] is True
    assert evidence["preplacement_registry_audit"]["covered_allowed_fraction"] == 1.0
    status = json.loads((ROOT / "docs/status.json").read_text())
    assert evidence["snapshot_scope"] == "HISTORICAL_HYPOTHESES_AND_SOURCE_ACCESS_NOT_REFRESHED_BY_REPLAY"
    assert status["current_review"] == "data/session_96f5f523_run_card.json"
    assert status["historical_review"] == "data/repo_review_20261025.json"
    assert status["research_queue"] == "data/hypothesis_queue.json"
    assert status["current_review_status"] == "DUPLICATE_STOP"
    assert status["new_tif_generated"] is False


@pytest.mark.skipif(
    not (ROOT / "data/bridge/sample_submission.tif").is_file(),
    reason="hash-pinned validation inputs are restored in CI or by restore_inputs.py",
)
def test_review_cli_require_submit_exits_two() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/review_repo_20261025.py"), "--require-submit"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert '"decision": "DUPLICATE_STOP"' in result.stdout
    assert '"ok_to_submit": false' in result.stdout
