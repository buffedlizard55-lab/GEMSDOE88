"""Fresh review never converts an old research artifact into a slot approval."""
import json
from pathlib import Path

import pytest

from scripts import review_submission_status as audit


def test_fresh_review_uses_existing_shared_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "review", lambda root: {
        "decision": "DUPLICATE_STOP", "ok_to_submit": False,
        "ok_to_download_for_research": True, "approved_for_weekly_slot": False,
        "raster_sha256": "existing", "holdout": {"status": "HISTORICAL"}})
    assert audit.main([], tmp_path) == 0
    card = json.loads((tmp_path / audit.OUTPUTS[0]).read_text())
    assert card["new_rasters_generated"] == card["fresh_geological_hypotheses_tested"] == 0
    assert card["freshness"]["holdout"] == "HISTORICAL_NOT_RERUN"
    assert len(card["submission_note"]) <= 140
    assert (tmp_path / audit.OUTPUTS[0]).read_bytes() == (tmp_path / audit.OUTPUTS[1]).read_bytes()
    assert audit.main(["--require-submit"], tmp_path) == 2


@pytest.mark.parametrize("changed", [None, {"decision": "DUPLICATE_STOP", "ok_to_submit": True},
                                       {"decision": "PROMOTE", "ok_to_submit": False}])
def test_error_and_unexpected_gate_change_erase_stale_approval(tmp_path, monkeypatch, changed):
    def result(root):
        if changed is None:
            raise OSError("missing pinned data")
        return changed
    monkeypatch.setattr(audit, "review", result)
    for output in audit.OUTPUTS:
        p = tmp_path / output
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"ok_to_submit":true}')
    assert audit.main(["--require-submit"], tmp_path) == 1
    for output in audit.OUTPUTS:
        card = json.loads((tmp_path / output).read_text())
        assert card["decision"] == "AUDIT_ERROR"
        assert card["ok_to_submit"] is False
        assert card["ok_to_download_for_research"] is False


def test_public_current_review_matches_report():
    root = Path(__file__).resolve().parents[1]
    assert (root / "research/review-20261025.md").read_bytes() == (root / "docs/research/review-20261025.md").read_bytes()
    assert (root / audit.OUTPUTS[0]).read_bytes() == (root / audit.OUTPUTS[1]).read_bytes()
    for page in ("index.html", "executive-summary.html"):
        text = (root / "docs" / page).read_text()
        assert 'id="review-20261025"' in text
        assert "data/submission_review_latest.json" in text
        assert "No new TIFF generated" in text
