"""GitHub HEAD drift monitoring must never imply scientific or slot clearance."""
from __future__ import annotations

import copy
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import focus_freshness as monitor  # noqa: E402


@pytest.fixture
def baseline():
    return monitor.baseline(ROOT)


def snapshot(baseline, fetch=None):
    pins, digest = baseline
    if fetch is None:
        fetch = lambda site: (pins[site], "2026-10-26T15:15:00Z")
    return monitor.collect(pins, digest, fetch=fetch, checked_at="2026-10-26T21:00:00Z")


def test_offline_baseline_and_checked_in_snapshot(baseline):
    import json
    pins, digest = baseline
    assert list(pins) == list(monitor.SITES)
    data = json.loads((ROOT / monitor.DEFAULT_OUTPUT).read_text())
    monitor.validate_report(data, pins, digest)
    assert data["ok_to_submit"] is False
    assert data["approved_for_weekly_slot"] is False


def test_mixed_success_and_failure_is_partial_and_never_approved(baseline):
    pins, _ = baseline
    def fetch(site):
        index = monitor.SITES.index(site)
        if index < 3:
            return pins[site], "2026-10-26T15:15:00Z"
        if index < 6:
            return "f" * 40, "2026-10-26T18:16:00Z"
        raise ValueError("Authorization: Bearer top-secret")
    result = snapshot(baseline, fetch)
    assert result["counts"] == {"changed": 3, "unchanged": 3, "unknown": 3}
    assert result["status"] == "PARTIAL"
    assert result["ok_to_submit"] is False
    assert result["approved_for_weekly_slot"] is False
    assert "top-secret" not in str(result)
    for row in result["sites"][6:]:
        assert row["state"] == "UNKNOWN"
        assert row["current_head"] is row["current_commit_utc"] is None
        assert row["error"] == "GitHub response unavailable or invalid"


@pytest.mark.parametrize("error,expected", [
    (HTTPError("https://api.github.com/", 403, "forbidden", {}, None), "GitHub HTTP 403"),
    (URLError("offline"), "GitHub network unavailable or timed out"),
    (TimeoutError("secret"), "GitHub network unavailable or timed out"),
    (ValueError("invalid secret"), "GitHub response unavailable or invalid"),
])
def test_every_fetch_failure_is_unknown_not_a_false_pass(baseline, error, expected):
    def fail(site):
        raise error
    report = snapshot(baseline, fail)
    assert report["counts"] == {"changed": 0, "unchanged": 0, "unknown": 9}
    assert report["status"] == "PARTIAL"
    assert all(row["error"] == expected and row["current_head"] is None for row in report["sites"])
    assert report["ok_to_submit"] is False


@pytest.mark.parametrize("fetched", [
    ("not-a-head", "2026-10-26T15:15:00Z"),
    ("a" * 40, "2026-02-31T00:00:00Z"),
    ("a" * 40, "2026-10-26T15:15:00+00:00"),
    ("a" * 40, "2026-10-26T15:15:00.123Z"),
])
def test_malformed_github_response_is_unknown(baseline, fetched):
    report = snapshot(baseline, lambda _: fetched)
    assert report["counts"]["unknown"] == 9
    assert all(row["current_head"] is None for row in report["sites"])


def test_snapshot_tampering_fails_closed(baseline):
    pins, digest = baseline
    good = snapshot(baseline)
    changes = [
        lambda r: r.update(ok_to_submit=True),
        lambda r: r.update(approved_for_weekly_slot=True),
        lambda r: r.update(audited_snapshot_sha256="0" * 64),
        lambda r: r.update(checked_at_utc="2026-02-31T10:00:00Z"),
        lambda r: r.update(status="PARTIAL"),
        lambda r: r["counts"].update(unchanged=8),
        lambda r: r["sites"].pop(),
        lambda r: r["sites"].__setitem__(0, {}),
        lambda r: r["sites"][0].update(site=monitor.SITES[1]),
        lambda r: r["sites"][0].update(audited_head="f" * 40),
        lambda r: r["sites"][0].update(current_head="f" * 40),
        lambda r: r["sites"][0].update(source_url="https://example.com"),
        lambda r: r["sites"][0].update(state="UNKNOWN", current_head=None, current_commit_utc=None, error=1),
        lambda r: r["sites"][0].update(state="CHANGED"),
    ]
    for change in changes:
        bad = copy.deepcopy(good)
        change(bad)
        with pytest.raises(ValueError):
            monitor.validate_report(bad, pins, digest)
    with pytest.raises(ValueError):
        monitor.validate_report([], pins, digest)


def test_baseline_disagreement_or_malformed_rows_is_rejected(tmp_path):
    for path in (monitor.BASELINE, monitor.EVIDENCE):
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / path).read_bytes())
    (tmp_path / monitor.EVIDENCE).write_text("{}")
    with pytest.raises(ValueError, match="differs"):
        monitor.baseline(tmp_path)
    malformed = '{"schema":"gems88.focus-sites-audit-20261026.v1","summary_verdict":{"ok_to_submit":false},"focus_sites":[null,null,null,null,null,null,null,null,null]}'
    (tmp_path / monitor.BASELINE).write_text(malformed)
    (tmp_path / monitor.EVIDENCE).write_text(malformed)
    with pytest.raises(ValueError, match="invalid historical row"):
        monitor.baseline(tmp_path)


def test_atomic_failure_does_not_leave_a_partial_or_destroy_prior_snapshot(tmp_path, baseline, monkeypatch):
    dest = tmp_path / "fresh.json"
    dest.write_text("previous snapshot")
    def fail(*args):
        raise OSError("disk failure")
    monkeypatch.setattr(monitor.os, "replace", fail)
    with pytest.raises(OSError):
        monitor.write_atomic(dest, snapshot(baseline))
    assert dest.read_text() == "previous snapshot"
    assert list(tmp_path.iterdir()) == [dest]


@pytest.mark.parametrize("url", [
    "http://api.github.com/repos/example", "https://evil.example/",
    "https://api.github.com.evil.example/", "https://api.github.com:444/",
    "https://user@api.github.com/",
])
def test_token_redirects_cannot_leave_github_api(url):
    request = Request("https://api.github.com/repos/example", headers={"Authorization": "Bearer secret"})
    with pytest.raises(ValueError, match="allowed host"):
        monitor.GitHubOnlyRedirect().redirect_request(request, None, 302, "Found", {}, url)


@pytest.mark.parametrize("optimized", [False, True])
def test_cli_check_never_accepts_submit_clearance(tmp_path, baseline, optimized):
    report = snapshot(baseline)
    path = tmp_path / "report.json"
    monitor.write_atomic(path, report)
    cmd = [sys.executable] + (["-O"] if optimized else []) + [
        str(ROOT / "scripts/focus_freshness.py"), "--check", "--output", str(path),
    ]
    good = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert good.returncode == 0, good.stderr
    report["ok_to_submit"] = True
    monitor.write_atomic(path, report)
    bad = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert bad.returncode == 1
    assert '"status": "ERROR"' in bad.stderr
    assert '"ok_to_submit": false' in bad.stderr


def test_javascript_ui_states_without_network():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed")
    result = subprocess.run([node, "--test", "tests/focus_freshness_ui_test.js"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
