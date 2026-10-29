"""Current 5aeeb70b review is negative, mirrored, dated and evidence-bounded."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from scripts import render_decision

ROOT = Path(__file__).resolve().parents[1]
SITES = (
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
)
STAMP = "20261029_5aeeb70b_r2"
PRIOR_STAMP = "20261029_5aeeb70b"


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_active_negative_card_and_session_feed_are_hash_pinned_and_mirrored():
    card_paths = [ROOT / base / "session_5aeeb70b_run_card.json"
                  for base in ("registry", "evidence", "docs/data")]
    raw = card_paths[0].read_bytes()
    assert all(path.read_bytes() == raw for path in card_paths)
    card = json.loads(raw)
    assert card["session_branch"] == "arena/5aeeb70b-gemsdoe88"
    assert card["status"] == card["decision"] == "DUPLICATE_STOP"
    assert card["verdict"] == "negative"
    assert card["new_tif_generated"] is False and card["new_rasters_generated"] == 0
    assert card["raster_file"] is card["raster_sha256"] is None
    assert card["ok_to_submit"] is card["approved_for_weekly_slot"] is False
    assert card["estimated_submission_score"] is None
    assert card["organizer_confirmed_score"] is None
    assert card["holdout"]["status"] == "NOT_RUN_PREPLACEMENT_DUPLICATE_STOP"
    assert card["holdout"]["dti"] is card["holdout"]["ci95"] is None
    assert card["leakage_canary"]["status"] == "NOT_RUN_NO_FEATURES_CONSTRUCTED"
    assert card["leakage_canary"]["max_symmetric_auc"] is None
    assert card["experiment_count"] == card["weekly_slots_used"] == 0
    assert card["submission_note_length"] == len(card["submission_note"]) <= 140
    assert "DUPLICATE_STOP" in card["submission_note"] and "DO NOT SUBMIT" in card["submission_note"]

    proof = card["registry_comparison"]["proof"]
    assert proof["witness_sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"] == 5_106_385
    assert proof["uncovered_allowed_pixels"] == 0 and proof["directly_saturated"] is True
    assert card["registry_comparison"]["universal_minimum_forward_overlap_3px_for_nonempty_allowed_candidate"] == 1.0
    assert card["registry_comparison"]["overlap_limit"] == 0.70
    assert card["registry_comparison"]["surface_rank_correlation"] is None
    assert card["registry_comparison"]["final_dot_overlap_3px"] is None
    assert card["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
    assert card["candidate_queue"]["conditional_first_choice"] == "H88-SPR"
    assert card["candidate_queue"]["generation_authorized"] is False
    assert card["data_access"]["training_features_present"] is False
    assert not any(card["data_access"]["queue_feature_inputs_present"].values())

    status = read("docs/status.json")
    assert status["current_review"] == "data/session_5aeeb70b_run_card.json"
    assert status["previous_review"] == "data/session_32583983_run_card.json"
    assert status["current_review_status"] == "DUPLICATE_STOP"
    assert status["ok_to_submit"] is False and status["new_tif_generated"] is False
    assert (ROOT / "docs/data/session_32583983_run_card.json").read_bytes() == (
        ROOT / "registry/session_32583983_run_card.json").read_bytes()

    dated = {
        "focus_current_samples": f"focus_current_samples_{STAMP}.json",
        "focus_freshness": f"focus_freshness_{STAMP}.json",
    }
    for feed_name in dated.values():
        docs_copy = ROOT / "docs/data" / feed_name
        evidence_copy = ROOT / "evidence" / feed_name
        assert docs_copy.read_bytes() == evidence_copy.read_bytes()
    sample_path = ROOT / "docs/data" / dated["focus_current_samples"]
    freshness_path = ROOT / "docs/data" / dated["focus_freshness"]
    assert sample_path.read_bytes() == (ROOT / "docs/data/focus-current-samples.json").read_bytes()
    assert freshness_path.read_bytes() == (ROOT / "docs/data/focus-freshness.json").read_bytes()
    feed = card["current_focus_feed"]
    assert hashlib.sha256(sample_path.read_bytes()).hexdigest() == feed["sample_sha256"]
    assert hashlib.sha256(freshness_path.read_bytes()).hexdigest() == feed["head_snapshot_sha256"]
    assert feed["ok_to_submit"] is False and feed["scores_measured"] is False

    samples = json.loads(sample_path.read_text())
    freshness = json.loads(freshness_path.read_text())
    assert freshness["status"] == "PARTIAL"
    assert freshness["counts"] == {"changed": 0, "unchanged": 0, "unknown": 9}
    assert samples["counts"]["UNKNOWN"] == 9
    assert samples["counts"]["DUPLICATE_STOP"] == 0
    assert len(samples["rows"]) == 9
    assert all(row["decision"] == "UNKNOWN" and row["overlap_3px"] is None for row in samples["rows"])
    assert all(row["format_pass"] is None for row in samples["rows"])
    for site in SITES:
        assert any(row["site"] == site for row in samples["rows"])

    # Retain the earlier complete sample as a dated point-in-time result, not
    # as the current feed after a later HEAD change and API rate limit.
    prior_sample = ROOT / "docs/data" / f"focus_current_samples_{PRIOR_STAMP}.json"
    prior_head = ROOT / "docs/data" / f"focus_freshness_{PRIOR_STAMP}.json"
    assert prior_sample.read_bytes() == (ROOT / "evidence" / prior_sample.name).read_bytes()
    assert prior_head.read_bytes() == (ROOT / "evidence" / prior_head.name).read_bytes()
    prior = json.loads(prior_sample.read_text())
    prior_freshness = json.loads(prior_head.read_text())
    assert prior["counts"]["DUPLICATE_STOP"] == 9
    assert prior_freshness["counts"] == {"changed": 9, "unchanged": 0, "unknown": 0}
    assert sum(row["format_pass"] is True for row in prior["rows"]) == 7
    assert sum(row["format_pass"] is False for row in prior["rows"]) == 2
    assert feed["prior_full_snapshot"]["status"].startswith("HISTORICAL_POINT_IN_TIME")
    assert feed["later_git_ls_remote_probe"]["site"] == "GEMSDOE32"
    assert feed["later_git_ls_remote_probe"]["observed_head"] != feed["later_git_ls_remote_probe"]["previous_sample_head"]
    assert feed["head_snapshot_status"] == "PARTIAL" and feed["sample_unknown_count"] == 9


def test_three_pass_review_hypotheses_and_prompt_mirrors_are_complete():
    review_path = ROOT / "research/session-5aeeb70b-review.md"
    public_review_path = ROOT / "docs/research/session-5aeeb70b-review.md"
    hypotheses_path = ROOT / "research/session-5aeeb70b-hypotheses.md"
    public_hypotheses_path = ROOT / "docs/research/session-5aeeb70b-hypotheses.md"
    review = review_path.read_text(encoding="utf-8")
    public_review = public_review_path.read_text(encoding="utf-8")
    hypotheses = hypotheses_path.read_text(encoding="utf-8")
    public_hypotheses = public_hypotheses_path.read_text(encoding="utf-8")
    conversions = {
        "../docs/data/": "../data/",
        "../docs/downloads/": "../downloads/",
        "../registry/session_5aeeb70b_run_card.json": "../data/session_5aeeb70b_run_card.json",
        "../registry/hypothesis_queue.json": "../data/hypothesis_queue.json",
    }
    expected_public_review = review
    expected_public_hypotheses = hypotheses
    for old, new in conversions.items():
        expected_public_review = expected_public_review.replace(old, new)
        expected_public_hypotheses = expected_public_hypotheses.replace(old, new)
    assert public_review == expected_public_review
    assert public_hypotheses == expected_public_hypotheses

    for site in SITES:
        assert site in review
    for value in ("0.2477", "0.2600", "0.2449", "0.2710", "0.2708", "0.2778", "0.2632", "0.2750"):
        assert value in review
    assert "USER-REPORTED" in review
    assert "Can we substantiate a new score above 0.2778? No" in review
    assert "Pass 1" in review and "Pass 2" in review and "Pass 3" in review
    assert "pending final" not in review
    assert all(name in hypotheses for name in ("H88-SPR", "H88-AWA", "H88-CBC"))
    for required in ("layers", "Physical signature", "Mimics", "Difference", "potential", "cost"):
        assert required.lower() in hypotheses.lower()
    assert "No hypothesis was fitted, scored, or validated" in hypotheses
    assert "2026-10-29" in (ROOT / "README.md").read_text()
    assert "Start every session by rereading" in (ROOT / "README.md").read_text()
    assert "rereading `README.md`" in (ROOT / "PROMPT.md").read_text()
    prompt = (ROOT / "USER_PROMPT_20261027.md").read_text(encoding="utf-8").strip()
    assert prompt in (ROOT / "README.md").read_text(encoding="utf-8")

    for relative_doc in (public_review_path, public_hypotheses_path):
        for target in re.findall(r"\]\(([^)]+)\)", relative_doc.read_text()):
            if target.startswith(("https://", "http://", "#")):
                continue
            assert (relative_doc.parent / target).resolve().is_file(), (relative_doc, target)

    research_page = (ROOT / "docs/research.html").read_text()
    assert "Current review · 5aeeb70b · 2026-10-29" in research_page
    assert "9 UNKNOWN" in research_page
    assert "9/9 then-observed" in research_page
    assert "research/session-5aeeb70b-review.md" in research_page


def test_current_renderer_and_browser_receipt_bind_the_new_review():
    # The canonical renderer validates current pointers, mirrors, file hashes,
    # and negative evidence without re-writing any artifacts.
    render_decision.read_inputs(ROOT)
    overview = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    guide = (ROOT / "docs/executive-summary.html").read_text(encoding="utf-8")
    assert "Review · 2026-10-29 · NO FILE APPROVED" in overview
    assert "session_5aeeb70b_run_card.json" in overview
    assert "NO NEW TIFF: DUPLICATE — STOP" in overview
    assert "SUBMIT: NO — DO NOT SUBMIT" in guide
    card = read("registry/session_5aeeb70b_run_card.json")
    browser_path = Path(card["verification"]["browser_evidence"])
    raw = (ROOT / browser_path).read_bytes()
    assert raw == (ROOT / "docs/data" / browser_path.name).read_bytes()
    receipt = json.loads(raw)
    assert receipt["status"] == "PASS" and receipt["ok_to_submit"] is False
    assert len(receipt["pages"]) == 7 and all(page["pass"] and not page["overflow"] for page in receipt["pages"])
    assert receipt["focus_comparison"]["pass"] is True
    assert receipt["research_download"]["click_matches_canonical_bytes"] is True
    assert receipt["focus_current_samples"]["row_count"] == 9
    assert receipt["focus_current_samples"]["diagnostic_site"] is None
    assert receipt["focus_current_samples"]["diagnostic_dom_pass"] is None
    assert receipt["focus_current_samples"]["fresh_snapshot_pass"] is True
    assert receipt["focus_freshness"]["partial_feed_fail_closed"] is True
    for path, digest in receipt["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
