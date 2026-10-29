"""Current 2026-10-29 negative review, fresh bounded feed, and public mirrors."""
import hashlib
import json
from pathlib import Path

from scripts import focus_current_samples, focus_freshness, render_decision

ROOT = Path(__file__).resolve().parents[1]
SESSION = "session_arena_2921f3de"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_run_card_mirrors_bind_negative_stop_and_no_artifact():
    paths = [ROOT / prefix / f"{SESSION}_run_card.json"
             for prefix in ("registry", "evidence", "docs/data")]
    raw = paths[0].read_bytes()
    assert all(path.read_bytes() == raw for path in paths)
    card = json.loads(raw)
    assert card["status"] == card["decision"] == "DUPLICATE_STOP"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is card["approved_for_weekly_slot"] is False
    assert card["new_tif_generated"] is False and card["new_rasters_generated"] == 0
    assert card["raster_file"] is card["raster_sha256"] is None
    assert card["holdout"]["status"] == "NOT_RUN_PREPLACEMENT_DUPLICATE_STOP"
    assert card["holdout"]["dti"] is card["holdout"]["ci95"] is None
    assert card["leakage_canary"]["max_symmetric_auc"] is None
    assert card["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
    assert card["estimated_submission_score"] is card["organizer_confirmed_score"] is None
    assert card["experiment_count"] == card["weekly_slots_used"] == 0
    assert card["maximum_experiments"] == 3 and card["maximum_experiment_seconds"] == 7200
    assert len(card["submission_name"]) <= 140
    assert len(card["submission_note"]) == card["submission_note_length"] <= 140
    proof = card["registry_comparison"]["proof"]
    assert proof["witness_sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"] == 5_106_385
    assert proof["uncovered_allowed_pixels"] == 0 and proof["covered_allowed_fraction"] == 1.0
    assert card["registry_comparison"]["universal_minimum_forward_overlap_3px_for_any_nonempty_allowed_candidate"] == 1.0
    assert card["registry_comparison"]["overlap_limit"] == 0.70
    assert card["current_focus_feed"]["ok_to_submit"] is False
    verification = card["verification"]
    receipt_path = ROOT / verification["browser_evidence"]
    raw_receipt = receipt_path.read_bytes()
    assert hashlib.sha256(raw_receipt).hexdigest() == verification["browser_evidence_sha256"]
    assert raw_receipt == (ROOT / "docs/data" / receipt_path.name).read_bytes()
    receipt = json.loads(raw_receipt)
    assert receipt["status"] == verification["browser_status"] == "PASS"
    assert verification["browser_checked_at_utc"] == receipt["checked_at_utc"] == "2026-10-29T14:59:14.464Z"
    assert len(receipt["pages"]) == verification["responsive_pages_checked"] == 7
    assert receipt["research_download"]["click_matches_canonical_bytes"] is True
    for relative, expected in receipt["source_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_fresh_head_and_bounded_sample_mirrors_are_sha_bound():
    freshness = ROOT / "docs/data/focus-freshness.json"
    sample = ROOT / "docs/data/focus-current-samples.json"
    dated_freshness = ROOT / "docs/data/focus_freshness_20261029_arena2921f3de.json"
    dated_sample = ROOT / "docs/data/focus_current_samples_20261029_arena2921f3de.json"
    evidence_freshness = ROOT / "evidence/focus_freshness_20261029_arena2921f3de.json"
    evidence_sample = ROOT / "evidence/focus_current_samples_20261029_arena2921f3de.json"
    assert freshness.read_bytes() == dated_freshness.read_bytes() == evidence_freshness.read_bytes()
    assert sample.read_bytes() == dated_sample.read_bytes() == evidence_sample.read_bytes()
    card = read_json("registry/session_arena_2921f3de_run_card.json")
    feed = card["current_focus_feed"]
    assert hashlib.sha256(freshness.read_bytes()).hexdigest() == feed["head_snapshot_sha256"]
    assert hashlib.sha256(sample.read_bytes()).hexdigest() == feed["sample_sha256"]
    snapshot = json.loads(freshness.read_text())
    report = json.loads(sample.read_text())
    assert snapshot["counts"] == {"changed": 9, "unchanged": 0, "unknown": 0}
    assert report["counts"]["DUPLICATE_STOP"] == 9
    assert report["counts"]["NOT_DISCOVERED"] == 0
    assert report["score_status"].startswith("NOT MEASURED")
    assert sum(row["format_pass"] for row in report["rows"]) == 7
    assert all(row["decision"] == "DUPLICATE_STOP" and row["overlap_3px"] == 1.0
               for row in report["rows"])
    assert not any(row.get("organizer_receipt") for row in report["rows"])
    assert focus_freshness.main(["--check"], root=ROOT) == 0
    assert focus_current_samples.main(["--check"], root=ROOT) == 0


def test_status_and_rendered_pages_point_to_current_negative_review():
    status = read_json("docs/status.json")
    assert status["current_review"] == "data/session_arena_2921f3de_run_card.json"
    assert status["previous_review"] == "data/session_32583983_run_card.json"
    assert status["current_review_status"] == "DUPLICATE_STOP"
    assert status["new_tif_generated"] is status["ok_to_submit"] is False
    inputs = render_decision.read_inputs(ROOT)
    review = inputs[-1]
    assert review["created_at_utc"] == "2026-10-29T14:38:58Z"
    assert review["review_document"] == "research/session-arena-2921f3de-review-20261029.md"
    for page in ("index.html", "executive-summary.html"):
        text = (ROOT / "docs" / page).read_text(encoding="utf-8")
        assert "Review · 2026-10-29" in text
        assert "session-arena-2921f3de-review-20261029.md" in text
        assert "session_arena_2921f3de_run_card.json" in text
        assert "NO NEW TIFF: DUPLICATE — STOP" in text
        assert "NEW SCORE ESTIMATE: NOT ESTIMABLE" in text
        assert "No current leaderboard estimate" in text
        assert "Current three-pass review (2026-10-29)" in text
        assert "0.998752 reverse H33-to-H28 overlap" in text
        assert "forward H28-to-H33 fraction 0.954727" in text


def test_review_prompt_hypotheses_and_source_mirrors_are_explicit():
    review = (ROOT / "research/session-arena-2921f3de-review-20261029.md").read_text()
    public_review = (ROOT / "docs/research/session-arena-2921f3de-review-20261029.md").read_text()
    hypotheses = (ROOT / "research/session-arena-2921f3de-hypotheses-20261029.md").read_text()
    public_hypotheses = (ROOT / "docs/research/session-arena-2921f3de-hypotheses-20261029.md").read_text()
    sources = (ROOT / "knowledge/official-sources-20261029.md").read_text()
    public_sources = (ROOT / "docs/research/official-sources-20261029.md").read_text()
    prompt = (ROOT / "USER_PROMPT_20261029.md").read_text()
    readme = (ROOT / "README.md").read_text()
    assert review == public_review
    assert hypotheses == public_hypotheses
    assert sources == public_sources
    assert "0.2778" in review and "USER-REPORTED" in review
    assert "0.954727" in review and "0.998752" in review
    assert "reverse denominator" in review
    assert "A Chromium browser receipt at `2026-10-29T14:59:14.464Z`" in review
    assert "NOT ESTIMABLE" in review and "DUPLICATE_STOP" in review
    assert all(lane in hypotheses for lane in ("H88-SPR", "H88-AWA", "H88-CBC"))
    assert "no corresponding paragraph" in hypotheses
    assert "aebe92f7c8a990f0e3443451b7a825d9afd6336b" in sources
    assert "USER_PROMPT_20261029.md" in readme and "USER_PROMPT_20261027.md" in readme
    assert "complete, scope-preserving restatement" in prompt
    assert "0.2778" in readme and "DO NOT SUBMIT" in readme
