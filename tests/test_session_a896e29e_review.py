"""The 2026-10-28 follow-up keeps source claims, fresh samples and stop gates distinct."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = "a896e29e"


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_run_card_mirrors_are_negative_and_source_bound() -> None:
    paths = [ROOT / f"{prefix}/session_{SESSION}_run_card.json"
             for prefix in ("registry", "evidence", "docs/data")]
    raw = paths[0].read_bytes()
    assert all(path.read_bytes() == raw for path in paths)
    card = json.loads(raw)
    assert card["session_branch"] == "arena/a896e29e-gemsdoe88"
    assert card["status"] == "DUPLICATE_STOP"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is card["approved_for_weekly_slot"] is False
    assert card["new_tif_generated"] is False
    assert card["raster_file"] is card["raster_sha256"] is None
    assert card["holdout_dti"]["dti"] is None
    assert card["holdout_dti"]["ci95"] is None
    assert card["leakage_canary"]["max_auc"] is None
    assert card["registry_comparison"]["surface_rank_correlation"] is None
    assert card["registry_comparison"]["final_dot_overlap"] is None
    proof = card["registry_comparison"]["proof"]
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"] == 5_106_385
    assert proof["covered_allowed_fraction"] == 1.0
    assert proof["witness_sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert len(card["submission_note"]) == card["submission_note_characters"] <= 140
    assert card["budget"]["geological_experiments_run"] == 0
    assert card["budget"]["weekly_slots_used"] == 0
    assert card["verification"]["review_passes"] == 3


def test_dated_feeds_and_historical_winner_bytes_are_mirrored() -> None:
    pairs = (
        "focus_freshness_20261028_a896e29e.json",
        "focus_current_samples_20261028_a896e29e.json",
        "focus_winner_sources_20261028_a896e29e.json",
        "h33_lineage_20261028_a896e29e.json",
        "h33_collar_20261028_a896e29e.json",
        "session_a896e29e_run_card.json",
    )
    for name in pairs:
        assert (ROOT / "evidence" / name).read_bytes() == (ROOT / "docs/data" / name).read_bytes()

    card = read_json("registry/session_a896e29e_run_card.json")
    winners = read_json("evidence/focus_winner_sources_20261028_a896e29e.json")
    assert winners["summary"] == {
        "files_checked": 9,
        "sha256_matches": 9,
        "organizer_receipts": 0,
        "leaderboard_values_verified": 0,
    }
    assert all(row["sha256_match"] is True for row in winners["rows"])
    assert all(row["score_evidence_class"] == "USER-REPORTED CLAIM — NOT HOLDOUT-DTI OR ORGANIZER-CONFIRMED"
               for row in winners["rows"])
    assert card["historical_best_files"]["source_byte_verification"]["evidence_sha256"] == digest(
        "evidence/focus_winner_sources_20261028_a896e29e.json")

    revisions = read_json("evidence/focus_freshness_20261028_a896e29e.json")
    sample = read_json("evidence/focus_current_samples_20261028_a896e29e.json")
    assert revisions["counts"] == {"changed": 9, "unchanged": 0, "unknown": 0}
    assert sample["counts"]["DUPLICATE_STOP"] == 8
    assert sample["counts"]["NOT_DISCOVERED"] == 1
    assert sample["rows"][3]["site"] == "GEMSDOE28"
    assert sample["rows"][3]["decision"] == "NOT_DISCOVERED"
    gem30 = next(row for row in sample["rows"] if row["site"] == "GEMSDOE30")
    assert gem30["format_pass"] is False and gem30["overlap_3px"] == 1.0


def test_h33_geometry_cross_checks_and_score_labels_remain_cautious() -> None:
    lineage = read_json("evidence/h33_lineage_20261028_a896e29e.json")
    collar = read_json("evidence/h33_collar_20261028_a896e29e.json")
    assert lineage["h33_subset_of_d28"] is True
    assert lineage["h33_subset_of_solo"] is True
    assert lineage["organizer_confirmed_score"] is None
    assert collar["h33_subset_of_d28"] is True
    assert collar["h33_subset_of_solo"] is True
    assert collar["counts"]["d28"] == 44_090
    assert collar["counts"]["solo"] == 40_199
    assert collar["counts"]["h33"] == 37_654
    assert collar["counts"]["d28_minus_h33_at_most_1px"] == 3_891
    assert collar["counts"]["d28_minus_h33_gt1_at_most_2px"] == 2_545
    assert collar["counts"]["d28_minus_h33_over_2px"] == 0
    assert collar["counts"]["h33_at_most_2px"] == 0

    report = ROOT / "research/session-a896e29e-review.md"
    mirror = ROOT / "docs/research/session-a896e29e-review.md"
    assert report.read_bytes() == mirror.read_bytes()
    text = report.read_text(encoding="utf-8")
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                 "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in text
    assert "USER-REPORTED CLAIM" in text
    assert "no valid score estimate" in text.lower()
    assert "Do not submit" in text
    assert "No new TIFF or zip is offered" in text


def test_active_site_receipt_stays_bound_after_upstream_base_refresh() -> None:
    status = read_json("docs/status.json")
    assert status["ok_to_submit"] is False
    active = read_json("docs/" + status["current_review"])
    assert active["ok_to_submit"] is False
    receipt = read_json(active["verification"]["browser_evidence"])
    assert receipt["status"] == "PASS" and receipt["ok_to_submit"] is False
    for relative, expected in receipt["source_sha256"].items():
        assert digest(relative) == expected, relative

    # A896E29E's point-in-time 11:30 UTC observations are separate from the
    # newer canonical feed refreshed by upstream PR #219 while this PR was open.
    for name in ("focus_freshness_20261028_a896e29e.json",
                 "focus_current_samples_20261028_a896e29e.json"):
        assert (ROOT / "evidence" / name).read_bytes() == (ROOT / "docs/data" / name).read_bytes()
    card = read_json("registry/session_a896e29e_run_card.json")
    assert card["publication"]["browser_check_this_session"].startswith("NOT_RUN")
    assert card["code_revision_at_capture"] == "866db73e8f3ac600baceb6e9e903225d835374f8"
    assert card["publication"]["canonical_feed_observation_time_utc"] == "2026-10-28T11:47:47+00:00"
    assert card["publication"]["upstream_after_capture"]["session"] == "60f326dc"
