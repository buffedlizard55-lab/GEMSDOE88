"""The 2026-10-28 review preserves the literal stop and labels bounded evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION = "a1612614"
SITES = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_run_card_mirrors_are_negative_and_complete() -> None:
    paths = [ROOT / f"{prefix}/session_{SESSION}_run_card.json"
             for prefix in ("registry", "evidence", "docs/data", "docs/evidence")]
    raw = paths[0].read_bytes()
    assert all(path.read_bytes() == raw for path in paths)
    card = json.loads(raw)
    assert card["session_branch"] == f"arena/{SESSION}-gemsdoe88"
    assert card["status"] == "DUPLICATE_STOP"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is card["approved_for_weekly_slot"] is False
    assert card["new_tif_generated"] is False
    assert card["raster_file"] is card["raster_sha256"] is None
    assert card["holdout_dti"]["status"] == "NOT_RUN_PREPLACEMENT_DUPLICATE_STOP"
    assert card["holdout_dti"]["evaluator_version"] is None
    assert card["holdout_dti"]["withheld_positive_pixels"] is None
    assert card["holdout_dti"]["dti"] is card["holdout_dti"]["ci95"] is None
    assert card["leakage_canary"]["max_auc"] is None
    assert card["registry_comparison"]["surface_rank_correlation"] is None
    assert card["registry_comparison"]["final_dot_overlap"] is None
    assert card["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
    assert card["validator_output"]["no_nan_inside_footprint"] is None
    assert card["validator_output"]["values_in_0_1"] is None
    assert card["validator_output"]["crs_match"] is None
    assert card["validator_output"]["shape_match"] is None
    assert card["validator_output"]["transform_match"] is None
    assert len(card["submission_note"]) == card["submission_note_characters"] <= 140
    assert card["budget"]["geological_experiments_run"] == 0
    assert card["budget"]["weekly_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert card["verification"]["status"] == "PASS_WITH_EXPECTED_NEGATIVE_GATES"
    assert card["verification"]["test_suite"] == {
        "command": ".venv/bin/python -m pytest -q", "status": "PASS",
        "passed": 1109, "skipped": 23, "failed": 0, "warnings": 115,
        "duration_seconds": 346.79,
        "warnings_note": "PendingDeprecationWarning from Rasterio Affine multiplication and one expected NotGeoreferencedWarning in a negative ZIP-container test.",
    }
    assert card["verification"]["session_tests"] == {
        "command": ".venv/bin/python -m pytest -q tests/test_session_a1612614_review.py",
        "status": "PASS", "passed": 6, "failed": 0,
    }
    browser_path = card["verification"]["browser_evidence"]
    browser = read_json(browser_path)
    assert browser["status"] == card["verification"]["browser_status"] == "PASS"
    assert browser["ok_to_submit"] is False and len(browser["pages"]) == 7
    assert browser["research_download"]["click_matches_canonical_bytes"] is True
    for prefix in ("docs/data", "docs/evidence"):
        assert (ROOT / f"{prefix}/{Path(browser_path).name}").read_bytes() == (ROOT / browser_path).read_bytes()
    import hashlib
    for relative, digest in browser["source_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    assert card["verification"]["checks"][-1]["exit_code"] == 2
    assert card["verification"]["checks"][-1]["decision"] == "DUPLICATE_STOP"
    assert card["concurrent_upstream_integration"]["generated_by_a1612614"] is False
    assert card["concurrent_upstream_integration"]["artifact"]["ok_to_submit"] is False
    assert card["concurrent_upstream_integration"]["artifact"]["decision"] == "DUPLICATE_STOP"


def test_fresh_preflight_and_input_hashes_are_source_bound() -> None:
    preflight = read_json("evidence/generation_preflight_a1612614_20261028.json")
    proof = preflight["preplacement_registry_proof"]
    assert preflight["decision"] == "DUPLICATE_STOP"
    assert preflight["generation_allowed"] is False
    assert proof["witness_sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"] == 5_106_385
    assert proof["uncovered_allowed_pixels"] == 0
    assert proof["covered_allowed_fraction"] == 1.0
    assert proof["universal_overlap_blocker"] is True
    assert proof["overlap_limit"] == 0.70

    state = read_json("evidence/research_state_a1612614_20261028.json")
    assert state["status"] == "PASS"
    assert state["input_pins_checked"] is True
    assert state["generation_authorized"] is False
    inputs = read_json("evidence/input_integrity_a1612614_20261028.json")
    assert inputs["summary"]["files_checked"] == 47
    assert inputs["summary"]["sha256_matches"] == 47
    assert inputs["summary"]["mismatches_or_missing"] == 0
    assert inputs["summary"]["generation_authorized"] is False
    assert all(row["sha256_match"] is True for row in inputs["rows"])
    assert all(row["source_repo"].startswith("https://github.com/") for row in inputs["rows"])
    assert inputs["provenance"].startswith("Public GitHub owner mirrors")
    assert "not authenticated" in inputs["provenance"]


def test_current_focus_sample_is_bounded_and_every_sample_hits_witness() -> None:
    names = (
        "focus_freshness_a1612614_20261028.json",
        "focus_current_samples_a1612614_20261028.json",
        "research_state_a1612614_20261028.json",
        "generation_preflight_a1612614_20261028.json",
        "input_integrity_a1612614_20261028.json",
    )
    for name in names:
        assert (ROOT / "evidence" / name).read_bytes() == (ROOT / "docs/data" / name).read_bytes()
        assert (ROOT / "evidence" / name).read_bytes() == (ROOT / "docs/evidence" / name).read_bytes()

    fresh = read_json("evidence/focus_freshness_a1612614_20261028.json")
    samples = read_json("evidence/focus_current_samples_a1612614_20261028.json")
    assert fresh["counts"] == {"changed": 9, "unchanged": 0, "unknown": 0}
    assert [row["site"] for row in fresh["sites"]] == list(SITES)
    assert samples["counts"] == {
        "DUPLICATE_STOP": 9, "NOT_CLEARED": 0, "INVALID_RASTER": 0,
        "NOT_DISCOVERED": 0, "UNKNOWN": 0,
    }
    assert samples["ok_to_submit"] is False
    assert samples["approved_for_weekly_slot"] is False
    assert samples["new_tiffs_generated"] == 0
    assert samples["weekly_slots_used"] == 0
    assert "not a winner search" in samples["scope"]
    assert "no holdout rerun" in samples["score_status"]
    assert [row["site"] for row in samples["rows"]] == list(SITES)
    assert all(row["decision"] == "DUPLICATE_STOP" for row in samples["rows"])
    assert all(row["overlap_3px"] == 1.0 for row in samples["rows"])
    assert all(row["ok_to_submit"] is False for row in samples["rows"])
    for row in samples["rows"]:
        assert row["source_url"].startswith(
            f"https://github.com/buffedlizard55-lab/{row['site']}/blob/{row['head']}/")
        assert row["positive_inside_footprint"] > 0
        assert "score_estimate" not in row

    for site in ("GEMSDOE28", "GEMSDOE30"):
        row = next(r for r in samples["rows"] if r["site"] == site)
        counts = row["format_pixel_counts"]
        assert row["format_pass"] is False
        assert counts["inside_nonfinite"] == 0
        assert counts["outside_nonfinite"] == 7_111_787
        assert counts["inside_finite_out_of_range"] == 0
        assert counts["outside_finite_out_of_range"] == 0
    for site in set(SITES) - {"GEMSDOE28", "GEMSDOE30"}:
        row = next(r for r in samples["rows"] if r["site"] == site)
        assert row["format_pass"] is True


def test_historical_scores_are_claims_and_report_has_all_sites() -> None:
    winners = read_json("evidence/focus_winner_sources_20261028_a896e29e.json")
    assert winners["summary"] == {
        "files_checked": 9,
        "sha256_matches": 9,
        "organizer_receipts": 0,
        "leaderboard_values_verified": 0,
    }
    assert all(row["sha256_match"] is True for row in winners["rows"])
    assert all("USER-REPORTED CLAIM" in row["score_evidence_class"] for row in winners["rows"])
    card = read_json("registry/session_a1612614_run_card.json")
    assert card["historical_focus_site_claims"]["organizer_receipts_found"] == 0
    assert card["historical_focus_site_claims"]["new_submission_score_estimate"] is None
    assert card["h33_forensics"]["user_reported_score"] == "0.2778"
    assert card["h33_forensics"]["organizer_confirmed_score"] is None
    assert card["repository_holdout_reference"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["repository_holdout_reference"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert card["repository_holdout_reference"]["withheld_positive_pixels"] == 22_893
    assert card["repository_holdout_reference"]["ci95"] == [
        0.18810523423482492, 0.22334363824908246]

    review = ROOT / "research/session-a1612614-review.md"
    mirror = ROOT / "docs/research/session-a1612614-review.md"
    assert review.read_bytes() == mirror.read_bytes()
    text = review.read_text(encoding="utf-8")
    for site in SITES:
        assert site in text
    assert "USER-REPORTED CLAIM" in text
    assert "Not measured / not estimable" in text
    assert "Do not submit" in text
    assert "no numerical DTI improvement is projected" in text
    assert "no evidence in this review that a new method beats it" in text
    assert "0.3195` / `0.4413" in text
    assert "ORGANIZER-CONFIRMED` scores: **none found**" in text
    assert "No single assigned method paragraph was found" in text
    assert "format-valid for research, but `DUPLICATE_STOP`" in text
    assert "new TIFF was generated" in text
    readme = (ROOT / "README.md").read_text()
    assert readme.count("USER-REQUEST:START") == 1
    assert "session-a1612614-review.md" in readme
    assert "session-a1612614-review.md" in (ROOT / "PROMPT.md").read_text()


def test_concurrent_pr222_artifact_is_audited_and_stays_blocked() -> None:
    for prefix in ("evidence", "docs/data", "docs/evidence"):
        assert (ROOT / f"{prefix}/session_a1612614_concurrent_pr222.json").is_file()
        assert (ROOT / f"{prefix}/session_a1612614_concurrent_pr222.json").read_bytes() == (
            ROOT / "evidence/session_a1612614_concurrent_pr222.json").read_bytes()
    report = read_json("evidence/session_a1612614_concurrent_pr222.json")
    assert report["pull_request"]["state"] == "MERGED"
    assert report["pull_request"]["number"] == 222
    assert report["upstream_checks"]["status"] == "FAILED_AFTER_MERGE"
    assert report["upstream_checks"]["merge_timing"]["interpretation"].startswith(
        "Both jobs were in progress at merge time")
    assert report["independent_local_audit"]["published_tiffs"] == 51
    assert report["independent_local_audit"]["research_download_format_pass"] == 51
    assert report["independent_local_audit"]["protocol_eligible"] == 0
    artifact = report["independent_local_audit"]["artifact"]
    assert artifact["sha256"] == "1547a37a48cbfd74909243706e9ec84c70907351077a49e715aa3753e6c7a676"
    assert artifact["format_valid"] is True
    assert artifact["ok_to_submit"] is False
    assert artifact["literal_overlap_lower_bound"] == 1.0
    assert artifact["decision"] == "DUPLICATE_STOP"
    run_card = read_json("docs/data/gtz88_run_card.json")
    assert run_card["new_rasters_generated"] == 1
    assert run_card["experiments_run"] == 0
    assert run_card["evidence_status"]["score_label"].startswith("NONE — HOLDOUT-DTI not run")
    page = (ROOT / "docs/executive-summary.html").read_text(encoding="utf-8")
    assert page.count("<!-- CANONICAL-DECISION:START -->") == 1
    assert page.count("<!-- CANONICAL-DECISION:END -->") == 1
    assert "gems88-gtz-damagezone-gauss-150m-20261028T163420Z-zeros-DO-NOT-SUBMIT.tif" in page


def test_official_reference_commit_pin_and_no_unscored_files_promoted() -> None:
    card = read_json("registry/session_a1612614_run_card.json")
    assert card["official_source_retrieval"]["freshly_retrieved_this_session"][-1].endswith(
        "aebe92f7c8a990f0e3443451b7a825d9afd6336b.")
    assert len(card["conditional_ranked_hypotheses"]) == 3
    assert [p["rank"] for p in card["conditional_ranked_hypotheses"]] == [1, 2, 3]
    assert all(p["status"] == "PROPOSED_UNTESTED" for p in card["conditional_ranked_hypotheses"])
    assert card["budget"]["geological_experiments_run"] == 0
    assert card["budget"]["weekly_slots_used"] == 0
    assert card["verdict"] == "negative"
