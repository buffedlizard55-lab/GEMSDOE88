from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88.review import (  # noqa: E402
    HISTORICALLY_EXECUTED_LANES,
    HYPOTHESES,
    hypothesis_queue,
    safe_note,
    validate_hypothesis_queue,
)


def test_ranked_queue_has_only_four_unexecuted_hypotheses() -> None:
    queue = hypothesis_queue()
    validate_hypothesis_queue(queue)
    assert len(queue) == 4
    assert [row["rank"] for row in queue] == [1, 2, 3, 4]
    assert [row["id"] for row in queue] == ["H88-FARC", "H88-TCONS", "H88-PRAN", "H88-FLAC"]
    assert all(row["status"] == "UNTESTED" for row in queue)
    assert all(row["layers"] for row in queue)
    assert all(row["non_fault_mimic"] for row in queue)
    assert len(HYPOTHESES) == len(queue)
    assert not set(row["id"] for row in queue) & HISTORICALLY_EXECUTED_LANES


def test_queue_validator_rejects_executed_lane_as_untested() -> None:
    queue = hypothesis_queue()
    queue.append(
        {
            "rank": 5,
            "id": "H88-MTAS",
            "layers": ["rtp_grad_200m"],
            "physical_signature": "historical MTAS lane",
            "missing_fault_rationale": "not applicable",
            "non_fault_mimic": "not applicable",
            "difference_from_repo": "historical lane",
            "expected_gain": "not applicable",
            "implementation_cost": "not applicable",
            "external_data": "not applicable",
            "status": "UNTESTED",
        }
    )
    with pytest.raises(ValueError, match="executed lanes cannot be advertised as untested"):
        validate_hypothesis_queue(queue)


def test_executed_mtas_lane_is_not_mislabeled_as_untried() -> None:
    archived = json.loads((ROOT / "registry/mtas88_experiment_run_card.json").read_text())
    assert archived["lane"] == "H88-MTAS"
    assert archived["verdict"] == "negative"
    assert archived["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert archived["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert archived["holdout"]["withheld_positive_pixels"] == 22893
    assert "H88-MTAS" in HISTORICALLY_EXECUTED_LANES
    assert "H88-MTAS" not in {row["id"] for row in hypothesis_queue()}
    preplacement = json.loads((ROOT / "registry/mtas88_run_card.json").read_text())
    evidence_copy = json.loads((ROOT / "evidence/mtas88_preflight_20261025.json").read_text())
    assert preplacement == evidence_copy
    assert preplacement["decision"] == "DUPLICATE_STOP"
    assert preplacement["experiment_count"] == 0
    assert preplacement["new_rasters_generated"] == 0


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
    assert evidence["schema"] == "gems88.repo-review-20261025.v2"
    assert evidence["review_status"] == "DUPLICATE_STOP"
    assert evidence["new_tif"]["generated"] is False
    assert evidence["submission"]["ok_to_submit"] is False
    assert evidence["submission"]["weekly_slots_used"] == 0
    assert evidence["holdout"]["status"].startswith("NOT RUN")
    assert evidence["holdout"]["candidate_lane"] == "H88-FARC"
    assert evidence["holdout"]["dti"] is None
    assert evidence["selected_lane"]["id"] == "H88-FARC"
    archived = evidence["historical_experiment_reconciliation"]["executed_lane_excluded_from_untried_queue"]
    assert archived["lane"] == "H88-MTAS"
    assert archived["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert archived["holdout"]["dti"] == pytest.approx(0.049577)
    assert archived["zip_one_member_byte_identical"] is True
    assert archived["zip_sha256"] == json.loads((ROOT / "registry/mtas88_experiment_run_card.json").read_text())["zip_sha256"]
    assert archived["conflicting_preplacement_records"]["status"].startswith("CONFLICTS_WITH")
    assert archived["conflicting_preplacement_records"]["recorded_experiment_count"] == 0
    assert archived["conflicting_preplacement_records"]["recorded_decision"] == "DUPLICATE_STOP"
    assert evidence["historical_experiment_reconciliation"]["current_repository_holdout_reference"]["evidence_class"] == "HOLDOUT-DTI"
    assert evidence["preplacement_registry_audit"]["universal_overlap_blocker"] is True
    assert evidence["preplacement_registry_audit"]["covered_allowed_fraction"] == 1.0
    status = json.loads((ROOT / "docs/status.json").read_text())
    assert status["current_review"] == "data/repo_review_20261025.json"
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
