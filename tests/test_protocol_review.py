"""Protocol-integrity review regressions; no model training or TIFF output."""
import json
from pathlib import Path
import zipfile

import pytest

from scripts import audit_protocol_integrity as audit

ROOT = Path(__file__).resolve().parents[1]


def test_review_remeasures_existing_bytes_and_keeps_stop():
    if not (ROOT / "data/registry/dense_17gemdoe.tif").exists():
        pytest.skip("restore_inputs.py --validation required")
    report = audit.review()
    assert report["decision"] == "DUPLICATE_STOP"
    assert report["verdict"] == "negative"
    assert report["ok_to_download_for_research"] is True
    assert report["ok_to_submit"] is report["approved_for_weekly_slot"] is False
    assert report["new_rasters_generated"] == report["experiments_run"] == report["slots_used"] == 0
    assert all(report["software_checks"].values())
    assert report["validator_output"]["ok"] is True
    assert report["validator_output"]["raster_sha256"] == report["raster_sha256"]
    assert report["saturation_certificate"]["uncovered_allowed_pixels"] == 0
    assert report["correlation_overlap_vs_registry"]["final_literal_overlap_3px_remeasured"] == 1.0
    assert report["holdout"]["status"].startswith("HISTORICAL_ONLY")
    assert len(report["submission_note"]) <= 140
    for relative in audit.OUTPUTS:
        assert report == json.loads((ROOT / relative).read_text())


@pytest.mark.parametrize("error", [ValueError("bad pin"), zipfile.BadZipFile("bad ZIP"), RuntimeError("bad decoder")])
def test_review_failure_overwrites_stale_success(tmp_path, monkeypatch, error):
    for relative in audit.OUTPUTS:
        p = tmp_path / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"ok_to_submit":true,"ok_to_download_for_research":true}')
    def broken(root):
        raise error
    monkeypatch.setattr(audit, "review", broken)
    assert audit.main([], root=tmp_path) == 1
    for relative in audit.OUTPUTS:
        result = json.loads((tmp_path / relative).read_text())
        assert result["ok_to_submit"] is False
        assert result["ok_to_download_for_research"] is False
        assert result["decision"] == "AUDIT_ERROR"


def test_submit_requirement_exits_two_not_success(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "review", lambda root: {"decision": "DUPLICATE_STOP", "ok_to_submit": False})
    assert audit.main(["--require-submit"], root=tmp_path) == 2


def test_review_is_identical_in_site_and_repository():
    name = "review-43d08c7a-20261024.md"
    assert (ROOT / "research" / name).read_bytes() == (ROOT / "docs/research" / name).read_bytes()
    for name in ("index.html", "executive-summary.html"):
        html = (ROOT / "docs" / name).read_text()
        assert 'id="protocol-review"' in html
        assert "data/protocol_review_43d08c7a.json" in html
        assert "No new TIFF was generated or copied" in html
        assert 'will pass the portal check' not in html
        assert 'will <strong>not</strong> return' not in html
