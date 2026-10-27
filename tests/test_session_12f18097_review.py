"""Regression guards for session 12f18097 (2026-10-27): PR #209/#210 withdrawal, 104-site cross-org claims, executive table, and 5 hypotheses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_user_claims import extract  # noqa: E402


def test_pr209_and_pr210_off_protocol_generators_and_artifacts_remain_withdrawn() -> None:
    forbidden = [
        "scripts/build_unique_submission_20261027.py",
        "scripts/generate_f159c61c_spaced_blind.py",
        "research/hypotheses-20261027-new.md",
        "research/session-f159c61c-hypotheses.md",
        "research/session-f159c61c-review.md",
        "docs/downloads/gemsdoe88-relay-dilational-20261027T171403Z-fec0813c826b-zeros.tif",
        "docs/downloads/gemsdoe88-relay-dilational-20261027T171403Z-fec0813c826b-zeros.zip",
        "docs/downloads/gems88-f159c61c-spaced-blind-37654dots-20261027-zeros-DO-NOT-SUBMIT.tif",
        "docs/downloads/gems88-f159c61c-spaced-blind-37654dots-20261027-zeros-DO-NOT-SUBMIT.zip",
    ]
    for rel in forbidden:
        assert not (ROOT / rel).exists(), f"Withdrawn off-protocol file reappeared: {rel}"

    reg = (ROOT / "registry/pr209_pr210_withdrawal_20261027.json").read_bytes()
    assert reg == (ROOT / "evidence/pr209_pr210_withdrawal_20261027.json").read_bytes()
    assert reg == (ROOT / "docs/data/pr209_pr210_withdrawal_20261027.json").read_bytes()
    w = json.loads(reg)
    assert w["ok_to_submit"] is False
    assert w["approved_for_weekly_slot"] is False
    assert w["verdict"] == "negative"
    assert [i["id"] for i in w["incidents"]] == ["IR-88-12F18097-01", "IR-88-12F18097-02"]
    assert w["withdrawn_files"]["docs/downloads/gemsdoe88-relay-dilational-20261027T171403Z-fec0813c826b-zeros.tif"]["sha256"].startswith("eb86d73d")
    assert w["withdrawn_files"]["docs/downloads/gems88-f159c61c-spaced-blind-37654dots-20261027-zeros-DO-NOT-SUBMIT.tif"]["sha256"].startswith("535e61ed")


def test_user_prompt_20261027_and_cross_org_claims_inventory() -> None:
    prompt_27 = (ROOT / "USER_PROMPT_20261027.md").read_text(encoding="utf-8")
    parsed = extract(prompt_27)
    assert parsed["site_count"] == 104
    assert parsed["distinct_claim_count"] == 128
    assert len(parsed["sites_without_a_reported_result"]) == 14
    for prefix in ("KANLERGEMSDOE", "EUGGEMSDOE", "WBGGEMSDOE", "GINNYGEMSDOE"):
        for idx in (1, 2, 3):
            assert f"{prefix}{idx}" in parsed["sites_without_a_reported_result"]

    claims = {(r["site"], r["submission_name"]): r["user_reported_value"] for r in parsed["claims"]}
    expected_20261026 = {
        ("GEMSDOE27", "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite"): "0.2250",
        ("GEMSDOE28", "gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite"): "0.0206",
        ("GEMSDOE33", "gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros"): "0.0963",
        ("GEMSDOE36", "gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros"): "0.1647",
        ("GEMSDOE91", "gems91-s22-omtj-e1-20261026-a99b8923f0-zeros"): "0.0298",
    }
    for key, val in expected_20261026.items():
        assert claims.get(key) == val


def test_sources_html_and_executive_submission_table_invariants() -> None:
    sources = (ROOT / "docs/sources.html").read_text(encoding="utf-8")
    assert "49 main downloads and 1 historical research variant (50 total)" in sources
    assert "(48 total)" not in sources
    assert "104 sites. 128 distinct reported entries (14 blank sites)." in sources
    assert "92 sites. 124 reported entries." not in sources

    for page in ("docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / page).read_text(encoding="utf-8")
        assert 'id="submission-summary-table"' in html
        assert "File to download (research only)" in html
        assert "Unique vs all 104 listed GEMSDOE sites?" in html
        assert "SUBMIT: NO — DO NOT SUBMIT" in html


def test_session_12f18097_run_card_dossiers_fleet_audit_and_browser_receipt() -> None:
    rc_bytes = (ROOT / "registry/session_12f18097_run_card.json").read_bytes()
    assert rc_bytes == (ROOT / "evidence/session_12f18097_run_card.json").read_bytes()
    assert rc_bytes == (ROOT / "docs/data/session_12f18097_run_card.json").read_bytes()
    rc = json.loads(rc_bytes)
    assert rc["verdict"] == "negative"
    assert rc["ok_to_submit"] is False
    assert rc["approved_for_weekly_slot"] is False
    assert rc["weekly_slots_used"] == 0
    assert rc["budget"]["geological_experiments_run"] == 0
    assert len(rc["submission_note"]) == rc["submission_note_characters"] <= 140
    assert [h["id"] for h in rc["ranked_untried_hypotheses"]] == [
        "H88-BFLX",
        "H88-PCBW",
        "H88-STDD",
        "H88-ZBOF",
        "H88-OPERA-SBAS",
    ]

    fleet_ev = (ROOT / "evidence/focus_and_crossorg_20261027_audit.json").read_bytes()
    assert fleet_ev == (ROOT / "docs/data/focus_and_crossorg_20261027_audit.json").read_bytes()
    fleet = json.loads(fleet_ev)
    assert fleet["summary"]["focus_sites_authorizing_submission_live"] == 0
    assert fleet["summary"]["cross_org_sites_authorizing_submission_live"] == 0
    assert fleet["summary"]["byte_audited_passing_dense_witness_overlap_070"] == 0
    assert fleet["summary"]["ok_to_submit"] is False

    for stem in ("session-12f18097-review.md", "session-12f18097-hypotheses.md"):
        root_md = (ROOT / "research" / stem).read_bytes()
        docs_md = (ROOT / "docs/research" / stem).read_bytes()
        assert root_md == docs_md
        text = root_md.decode("utf-8")
        assert "(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)" in text
        assert ".." not in [line for line in text.splitlines() if "](" in line and "http" not in line]

    br_ev = (ROOT / "evidence/session_12f18097_browser_check.json").read_bytes()
    assert br_ev == (ROOT / "docs/data/session_12f18097_browser_check.json").read_bytes()
    br = json.loads(br_ev)
    assert br["status"] == "PASS" and br["ok_to_submit"] is False
    assert len(br["pages"]) == 7 and all(p["pass"] and not p["overflow"] for p in br["pages"])
    for rel, expected_sha in br["source_sha256"].items():
        actual_sha = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert actual_sha == expected_sha, f"Stale pin on {rel}"
