from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    ROOT / "registry/session_db4a5e4b_run_card.json",
    ROOT / "docs/data/session_db4a5e4b_run_card.json",
    ROOT / "evidence/session_db4a5e4b_run_card.json",
]


def test_session_card_is_identical_and_fail_closed() -> None:
    payloads = [path.read_bytes() for path in PATHS]
    assert payloads[0] == payloads[1] == payloads[2]
    card = json.loads(payloads[0])
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["raster_file"] is None
    assert card["raster_sha256"] is None
    assert card["experiments_executed"] == 0
    assert card["weekly_slots_used"] == 0
    assert card["correlation_overlap_vs_registry"]["decision"] == "DUPLICATE_STOP"
    assert card["correlation_overlap_vs_registry"]["universal_lower_bound_on_any_nonempty_candidate_overlap_3px"] == 1.0
    assert card["correlation_overlap_vs_registry"]["overlap_limit"] == 0.70
    assert card["holdout_dti"]["status"] == "NOT_RUN_PREPLACEMENT_DUPLICATE_STOP"
    assert card["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
    assert len(card["submission_note"]) <= 140


def test_session_review_does_not_claim_a_new_tiff_or_receipt() -> None:
    review = (ROOT / "research/session-db4a5e4b-review.md").read_text()
    hypotheses = (ROOT / "research/session-db4a5e4b-hypotheses.md").read_text()
    assert "New competition TIFF: NOT GENERATED" in review
    assert "USER-REPORTED" in review
    assert "Not established" in review
    assert "none was executed" in hypotheses
    assert "not a score or projection" in hypotheses
