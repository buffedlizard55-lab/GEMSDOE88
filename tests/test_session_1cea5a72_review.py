"""2026-10-30 review, current feed and real-browser evidence stay negative and pinned."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import render_decision  # noqa: E402

CARD_NAME = "session_1cea5a72_run_card.json"
BROWSER_NAME = "session_1cea5a72_browser_check.json"
SAMPLE_NAME = "focus_current_samples_20261030_1cea5a72.json"
FRESHNESS_NAME = "focus_freshness_20261030_1cea5a72.json"


def read(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_current_review_is_a_mirrored_negative_run_card():
    paths = [ROOT / folder / CARD_NAME for folder in ("registry", "evidence", "docs/data")]
    card_bytes = paths[0].read_bytes()
    assert all(path.read_bytes() == card_bytes for path in paths)
    card = json.loads(card_bytes)
    assert card["schema"] == "gems88.session-run-card.v1"
    assert card["session_branch"] == "arena/1cea5a72-gemsdoe88"
    assert card["status"] == card["decision"] == "DUPLICATE_STOP"
    assert card["verdict"] == "negative"
    assert card["new_tif_generated"] is False and card["new_rasters_generated"] == 0
    assert card["raster_file"] is card["raster_sha256"] is None
    assert card["estimated_submission_score"] is None
    assert card["organizer_confirmed_score"] is None
    assert card["archived_research_download"]["ok_to_download_for_research"] is True
    assert card["archived_research_download"]["ok_to_submit"] is False
    assert "DO-NOT-SUBMIT" in card["archived_research_download"]["file"]
    assert card["ok_to_submit"] is card["approved_for_weekly_slot"] is False
    assert card["weekly_slots_used"] == card["experiment_count"] == 0
    assert card["holdout"]["status"] == "NOT_RUN_PREPLACEMENT_DUPLICATE_STOP"
    assert card["holdout"]["dti"] is card["holdout"]["ci95"] is None
    assert card["leakage_canary"]["status"] == "NOT_RUN_NO_FEATURES_CONSTRUCTED"
    assert card["leakage_canary"]["max_symmetric_auc"] is None
    assert len(card["submission_note"]) == card["submission_note_length"] <= 140
    assert "DUPLICATE_STOP" in card["submission_note"] and "DO NOT SUBMIT" in card["submission_note"]

    proof = card["registry_comparison"]["proof"]
    assert proof["witness_file"] == "data/registry/dense_17gemdoe.tif"
    assert proof["witness_sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"] == 5_106_385
    assert proof["uncovered_allowed_pixels"] == 0 and proof["covered_allowed_fraction"] == 1.0
    assert proof["directly_saturated"] is True
    assert card["registry_comparison"]["universal_minimum_forward_overlap_3px_for_nonempty_allowed_candidate"] == 1.0
    assert card["registry_comparison"]["overlap_limit"] == 0.70
    assert card["registry_comparison"]["surface_rank_correlation"] is None
    assert card["registry_comparison"]["final_dot_overlap_3px"] is None

    status = read("docs/status.json")
    assert status["current_review"] == "data/session_1cea5a72_run_card.json"
    assert status["previous_review"] == "data/session_5aeeb70b_run_card.json"
    assert status["ok_to_submit"] is False and status["new_tif_generated"] is False
    assert status["current_review_status"] == "DUPLICATE_STOP"
    assert status["current_review_note"].startswith("Session 1cea5a72")


def test_fresh_focus_feed_is_dated_mirrored_and_scoped_as_a_sample():
    for name in (SAMPLE_NAME, FRESHNESS_NAME):
        assert (ROOT / "docs/data" / name).read_bytes() == (ROOT / "evidence" / name).read_bytes()
    sample_path = ROOT / "docs/data" / SAMPLE_NAME
    freshness_path = ROOT / "docs/data" / FRESHNESS_NAME
    assert sample_path.read_bytes() == (ROOT / "docs/data/focus-current-samples.json").read_bytes()
    assert freshness_path.read_bytes() == (ROOT / "docs/data/focus-freshness.json").read_bytes()
    sample = json.loads(sample_path.read_text())
    freshness = json.loads(freshness_path.read_text())
    assert freshness["status"] == "COMPLETE"
    assert freshness["counts"] == {"changed": 9, "unchanged": 0, "unknown": 0}
    assert sample["counts"]["DUPLICATE_STOP"] == 7
    assert sample["counts"]["NOT_DISCOVERED"] == 2
    assert sample["counts"]["UNKNOWN"] == 0
    assert len(sample["rows"]) == 9
    assert all(row["overlap_3px"] == 1.0 for row in sample["rows"] if row["decision"] == "DUPLICATE_STOP")
    assert {row["site"] for row in sample["rows"] if row["decision"] == "NOT_DISCOVERED"} == {"GEMSDOE25", "GEMSDOE28"}
    assert sample["score_status"].startswith("NOT MEASURED")
    assert sample["scope"].startswith("First bare")

    card = read("registry/" + CARD_NAME)
    assert hashlib.sha256(sample_path.read_bytes()).hexdigest() == card["focus_feed"]["sample_sha256"]
    assert hashlib.sha256(freshness_path.read_bytes()).hexdigest() == card["focus_feed"]["freshness_sha256"]
    assert card["focus_feed"]["current_winner_search"] is False
    assert card["focus_feed"]["ok_to_submit"] is False


def test_automated_chromium_receipt_binds_current_public_bytes_and_stays_negative():
    card = read("registry/" + CARD_NAME)
    receipt_path = Path(card["verification"]["browser_evidence"])
    raw = (ROOT / receipt_path).read_bytes()
    assert raw == (ROOT / "docs/data" / receipt_path.name).read_bytes()
    receipt = json.loads(raw)
    assert receipt["status"] == "PASS" and receipt["ok_to_submit"] is False
    assert receipt["browser"] == "153.0.8010.0"
    assert len(receipt["pages"]) == 7 and all(page["pass"] and not page["overflow"] for page in receipt["pages"])
    assert receipt["focus_comparison"]["pass"] is True
    assert receipt["research_download"]["click_matches_canonical_bytes"] is True
    assert receipt["research_download"]["ok_to_submit"] is False
    assert receipt["focus_freshness"]["fresh_snapshot_pass"] is True
    assert receipt["focus_freshness"]["missing_feed_fail_closed"] is True
    assert receipt["focus_freshness"]["partial_feed_fail_closed"] is True
    assert receipt["focus_freshness"]["expired_feed_fail_closed"] is True
    assert receipt["focus_current_samples"]["row_count"] == 9
    assert receipt["focus_current_samples"]["diagnostic_site"] == "GEMSDOE30"
    assert receipt["focus_current_samples"]["diagnostic_dom_pass"] is True
    assert receipt["focus_current_samples"]["tampered_diagnostic_fails_closed"] is True
    assert receipt["no_javascript_stays_negative"] is True
    assert card["verification"]["browser_evidence_sha256"] == hashlib.sha256(raw).hexdigest()
    assert card["verification"]["source_sha256"] == receipt["source_sha256"]
    assert card["verification"]["ok_to_submit"] is False
    for relative, digest in receipt["source_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative


def test_canonical_renderer_and_site_guards_bind_the_current_review():
    render_decision.read_inputs(ROOT)
    research = (ROOT / "docs/research.html").read_text(encoding="utf-8")
    assert "Current review · 1cea5a72 · 2026-10-30" in research
    assert "7 bounded README-cited TIFF samples returned DUPLICATE_STOP" in research
    assert "2 were not discovered" in research
    assert "research/session-1cea5a72-review.md" in research
    assert "data/session_1cea5a72_browser_check.json" in research
    assert "Current H33 analysis and nine-site table" in research

    review_path = ROOT / "research/session-1cea5a72-review.md"
    public_path = ROOT / "docs/research/session-1cea5a72-review.md"
    source = review_path.read_text(encoding="utf-8")
    public = public_path.read_text(encoding="utf-8")
    for old, new in (
        ("../docs/downloads/", "../downloads/"),
        ("../docs/data/", "../data/"),
        ("../evidence/session_1cea5a72_browser_check.json", "../data/session_1cea5a72_browser_check.json"),
        ("../evidence/focus_current_samples_20261030_1cea5a72.json", "../data/focus_current_samples_20261030_1cea5a72.json"),
        ("../registry/session_1cea5a72_run_card.json", "../data/session_1cea5a72_run_card.json"),
    ):
        source = source.replace(old, new)
    assert public == source
    for target in re.findall(r"\]\(([^)]+)\)", public):
        if not target.startswith(("https://", "http://", "#")):
            assert (public_path.parent / target).resolve().is_file(), target

    for command in (
        [sys.executable, "scripts/render_decision.py", "--check"],
        [sys.executable, "scripts/check_site.py"],
        [sys.executable, "-O", "scripts/check_site.py"],
    ):
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
