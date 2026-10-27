"""Current negative run, reviewed scores and browser evidence stay attributable."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def test_current_card_is_negative_and_does_not_invent_a_candidate():
    paths = ["registry/session_cef4b835_run_card.json", "evidence/session_cef4b835_run_card.json",
             "docs/data/session_cef4b835_run_card.json"]
    assert len({(ROOT / p).read_bytes() for p in paths}) == 1
    card = read(paths[0])
    assert read("docs/status.json")["current_review"] == "data/session_cef4b835_run_card.json"
    assert card["decision"] == "DUPLICATE_STOP" and card["verdict"] == "negative"
    assert card["new_tif_generated"] is False and card["raster_sha256"] is None
    assert card["raster_file"] is None and card["ok_to_submit"] is False
    assert card["approved_for_weekly_slot"] is False and card["weekly_slots_used"] == 0
    assert card["holdout_dti"]["dti"] is None and card["holdout_dti"]["ci95"] is None
    assert card["holdout_dti"]["withheld_positive_pixels"] is None
    assert card["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
    assert card["registry_comparison"]["surface_rank_correlation"] is None
    assert card["registry_comparison"]["final_dot_overlap"] is None
    proof = card["registry_comparison"]["proof"]
    assert proof["allowed_pixels"] == proof["directly_covered_allowed_pixels"] == 5_106_385
    assert proof["witness_sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert card["registry_comparison"]["proof_of_any_nonempty_allowed_dot_overlap"] == 1.0
    assert card["registry_comparison"]["overlap_threshold"] == 0.7
    assert len(card["submission_note"]) == card["submission_note_characters"] <= 140
    assert card["budget"]["geological_experiments_run"] == 0
    assert [p["id"] for p in card["ranked_hypotheses"]] == ["H88-SPR", "H88-AWA", "H88-CBC"]
    assert all(p["status"] == "PROPOSED_UNTESTED" and p["non_fault_mimic"] for p in card["ranked_hypotheses"])
    near = card["focus_sites"]["near_prior_spr"]
    queue = read("registry/hypothesis_queue.json")
    assert queue["reviewed_near_prior"]["sha256"] == near["source_sha256"]
    assert queue["reviewed_near_prior"]["source_url"] == near["source_url"]
    assert "not wholly novel" in near["finding"]
    assert card["organizer_confirmed_score"] is None


def test_rendered_scores_and_intervals_come_from_matching_run_cards():
    card = read("registry/session_cef4b835_run_card.json")
    bpwd = read("registry/bpwd88_run_card.json")["holdout_dti"]
    assert card["historical_holdout_context"]["overall"] == bpwd["candidate_exp03"]
    assert card["historical_holdout_context"]["blind_gt25px"] == bpwd["blind_gt25px"]
    assert round(bpwd["blind_gt25px"]["dti"], 6) == 0.072733
    assert [round(x, 6) for x in bpwd["blind_gt25px"]["ci95"]] == [0.045432, 0.103127]
    assert bpwd["blind_gt25px"]["withheld_positive_pixels"] == 3117
    for file in ("docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / file).read_text().split("<!-- CANONICAL-DECISION:START -->", 1)[1].split(
            "<!-- CANONICAL-DECISION:END -->", 1)[0]
        assert "HOLDOUT-DTI overall:" in text and "0.205991 [0.188105, 0.223344]" in text
        assert "0.072733 [0.045432, 0.103127]" in text
        assert "n=3,117" in text and "gems57-pooled-hide-v2" in text
        assert "0.090449" not in text
        assert "USER-REPORTED" in text and "ORGANIZER-CONFIRMED" in text
        assert "data/session_cef4b835_run_card.json" in text


def test_nine_reviewed_readme_pins_match_observed_heads_and_published_excerpts():
    raw = (ROOT / "evidence/focus_readme_cef4b835.json").read_bytes()
    assert raw == (ROOT / "docs/data/focus_readme_cef4b835.json").read_bytes()
    evidence = json.loads(raw)
    freshness = read("docs/data/focus-freshness.json")
    # A later scheduled HEAD-only refresh may legitimately supersede the feed
    # without rewriting this immutable text-only review.
    assert freshness["checked_at_utc"] >= evidence["github_head_snapshot_utc"]
    expected = {row["site"]: row["current_head"] for row in freshness["sites"]}
    assert len(expected) == len(evidence["rows"]) == 9
    page = (ROOT / "docs/index.html").read_text()
    for row in evidence["rows"]:
        if freshness["checked_at_utc"] == evidence["github_head_snapshot_utc"]:
            assert row["repo_head"] == expected[row["site"]]
        assert re.fullmatch(r"[0-9a-f]{64}", row["readme_sha256"])
        assert row["readme_url"] == (f'https://github.com/buffedlizard55-lab/{row["site"]}'
                                     f'/blob/{row["repo_head"]}/README.md')
        assert row["readme_url"] in page and row["excerpt"]
        assert row["excerpt_line"] > 0
    assert evidence["ok_to_submit"] is False and evidence["weekly_slots_used"] == 0
    assert "no sibling raster, score, quota or full inventory was revalidated" in evidence["scope"]


def test_dossiers_and_fresh_browser_receipt_are_published_without_relabeling_history():
    for suffix in ("review", "hypotheses"):
        name = f"session-cef4b835-{suffix}.md"
        assert (ROOT / "research" / name).read_bytes() == (ROOT / "docs/research" / name).read_bytes()
    card = read("registry/session_cef4b835_run_card.json")
    raw = (ROOT / card["verification"]["browser_evidence"]).read_bytes()
    assert raw == (ROOT / "docs/data/session_cef4b835_browser_check.json").read_bytes()
    browser = json.loads(raw)
    assert browser["status"] == "PASS" and browser["ok_to_submit"] is False
    assert len(browser["pages"]) == 7 and all(p["pass"] and not p["overflow"] for p in browser["pages"])
    assert browser["failed_fetch_stays_negative"] is True
    assert browser["no_javascript_stays_negative"] is True
    assert browser["research_download"]["click_matches_canonical_bytes"] is True
    assert all(browser["focus_freshness"][key] for key in (
        "fresh_snapshot_pass", "missing_feed_fail_closed", "partial_feed_fail_closed", "expired_feed_fail_closed"))
    for path, digest in browser["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    old = read("evidence/session_12f18097_browser_check.json")
    assert old["checked_at_utc"] < browser["checked_at_utc"]
