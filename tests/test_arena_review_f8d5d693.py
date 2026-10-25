from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "evidence/repo_review_arena_f8d5d693_20261025.json"
REPORT_PATH = ROOT / "research/repo-review-arena-f8d5d693-20261025.md"


def test_review_card_is_valid_fail_closed_run_card() -> None:
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    assert card["schema"] == "gems88.arena-repo-review.v1"
    assert card["decision"] == "DUPLICATE_STOP"
    assert card["verdict"] == "negative"
    assert card["raster_sha256"]["new_raster_generated_this_review"] is False
    assert card["raster_sha256"]["new_raster_sha256"] is None
    assert card["holdout_dti"]["dti"] is None
    assert card["holdout_dti"]["ci95"] is None
    assert card["submission"]["ok_to_submit"] is False
    assert card["submission"]["weekly_slots_used"] == 0
    assert len(card["submission"]["note"]) == card["submission"]["note_characters"] <= 140


def test_historical_mtas_artifact_is_explicitly_separate_and_hash_bound() -> None:
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    historical = card["raster_sha256"]["historical_mtas_raster_sha256"]
    tif = ROOT / card["raster_sha256"]["historical_file"]
    assert tif.is_file()
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == historical
    assert "DO-NOT-SUBMIT" in tif.name
    assert card["validator_output"]["historical_mtas_raster"]["ok_to_submit"] is False
    assert card["validator_output"]["historical_mtas_raster"]["ok_to_download_for_research"] is True
    assert any(item["id"] == "MTAS-HISTORY-TIMELINE-CONFLICT" for item in card["irregularities"])


def test_review_report_and_readme_expose_the_negative_decision() -> None:
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    report = REPORT_PATH.read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "DUPLICATE_STOP" in report
    assert "654 passed / 23 skipped" in readme
    assert "research/repo-review-arena-f8d5d693-20261025.md" in readme
    assert "evidence/repo_review_arena_f8d5d693_20261025.json" in readme
    assert card["submission"]["new_tif_download_ok"] is False
