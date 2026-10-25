import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_session_c0636fcd_run_card_is_fail_closed_and_complete():
    card = json.loads((ROOT / "evidence/session_c0636fcd_run_card.json").read_text())

    assert card["schema"] == "gems88.session-run-card.v1"
    assert card["verdict"] == "negative"
    assert card["holdout_dti"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["value"] is None
    assert card["holdout_dti"]["ci95"] is None
    assert card["raster_sha256"] is None
    assert card["validator_output"]["candidate_tiff_generated"] is False
    assert card["submission"]["submit"] is False
    assert card["submission"]["download_new_file"] is False
    assert card["submission"]["note_character_count"] == len(card["submission"]["note"])
    assert card["submission"]["note_character_count"] <= 140

    queue = card["candidate_queue"]
    assert [row["id"] for row in queue] == [
        "H88-PRAN", "H88-FARC", "H88-TCONS", "H88-FLAC"
    ]
    assert all(row["experiment_status"].startswith("not run") for row in queue)
    assert all(row["new_external_data_required"] is False for row in queue)


def test_session_c0636fcd_readme_links_review_and_preserves_submission_warning():
    readme = (ROOT / "README.md").read_text()
    assert "research/session-c0636fcd-review-20261025.md" in readme
    assert "evidence/session_c0636fcd_run_card.json" in readme
    assert "DUPLICATE_STOP" in readme
    assert "user-reported, not organizer-confirmed" in readme
