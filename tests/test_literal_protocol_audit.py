import json
from pathlib import Path

import pytest

from scripts.audit_literal_protocol import inspect, pinned

ROOT = Path(__file__).resolve().parents[1]


def test_pin_rejects_modified_bytes(tmp_path):
    (tmp_path / "input.tif").write_bytes(b"wrong bytes")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        pinned(tmp_path, "input.tif", "0" * 64)


def test_pin_rejects_missing_input(tmp_path):
    with pytest.raises(FileNotFoundError):
        pinned(tmp_path, "missing.tif", "0" * 64)


def test_current_bytes_fail_literal_rule():
    if not (ROOT / "data/registry/dense_17gemdoe.tif").is_file():
        pytest.skip("restore_inputs.py --validation required for disk audit")
    report = inspect()
    assert report["decision"] == "DUPLICATE_STOP"
    assert report["verdict"] == "negative"
    assert report["ok_to_submit"] is False
    assert report["ok_to_download_for_research"] is True
    assert report["validator_output"]["ok"] is True
    assert report["correlation_overlap_vs_registry"]["final_literal_overlap_3px_remeasured"] == 1
    cert = report["saturation_certificate"]
    assert cert["uncovered_allowed_pixels"] == 0
    assert cert["universal_overlap_blocker"] is True
    assert report["new_rasters_generated"] == report["experiments_run"] == report["slots_used"] == 0
    assert len(report["submission_note"]) <= 140
    assert report == json.loads((ROOT / "docs/data/literal_protocol_audit.json").read_text())


def test_public_status_uses_literal_audit():
    js = (ROOT / "docs/assets/site.js").read_text()
    assert "fetch('data/literal_protocol_audit.json'" in js
    assert "data.validator_output?.ok === true" in js
    for name in ("index.html", "executive-summary.html"):
        html = (ROOT / "docs" / name).read_text()
        assert "Literal protocol audit: DUPLICATE — STOP" in html
        assert "no dense-prior exemption" in html
        assert "newest unique GeoTIFF" not in html
        assert "New unique GeoTIFF generated" not in html


def test_audit_does_not_create_a_prediction():
    source = (ROOT / "scripts/audit_literal_protocol.py").read_text()
    assert "write_submission(" not in source
    assert "saturation_certificate(" in source
    assert "uniqueness.dot_overlap(" in source


def test_readiness_erases_stale_success_on_audit_failure(tmp_path, monkeypatch):
    from scripts import readiness
    (tmp_path / "docs").mkdir()
    target = tmp_path / "docs/status.json"
    target.write_text('{"ok_to_submit": true}')
    monkeypatch.setattr(readiness, "ROOT", tmp_path)
    monkeypatch.setattr(readiness, "verify_template", lambda: None)
    def fail():
        raise ValueError("missing witness")
    monkeypatch.setattr(readiness, "current_status", fail)
    assert readiness.main() == 1
    status = json.loads(target.read_text())
    assert status["ok_to_submit"] is False
    assert status["ok_to_download_for_research"] is False
    assert status["status"] == "BLOCKED"
