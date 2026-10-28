import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOCUS_SITES = {
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
}


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_negative_run_card_is_mirrored_and_fails_closed():
    canonical = (ROOT / "registry/session_3ad2104f_run_card.json").read_bytes()
    assert canonical == (ROOT / "evidence/session_3ad2104f_run_card.json").read_bytes()
    assert canonical == (ROOT / "docs/data/session_3ad2104f_run_card.json").read_bytes()
    card = json.loads(canonical)
    assert card["session_branch"] == "arena/3ad2104f-gemsdoe88"
    assert card["review_document"] == "research/session-3ad2104f-review.md"
    assert card["mainline_artifact_context"]["pr"] == 222
    assert card["mainline_artifact_context"]["sha256"] == "1547a37a48cbfd74909243706e9ec84c70907351077a49e715aa3753e6c7a676"
    assert card["mainline_artifact_context"]["disposition"].endswith("DO NOT SUBMIT.")
    download_audit = card["verification"]["research_download_audit"]
    assert download_audit["published_download_tiffs"] == 50
    assert download_audit["published_research_variant_tiffs"] == 1
    assert download_audit["total_published_tiffs"] == 51
    assert download_audit["local_research_format_passes"] == 51
    assert download_audit["protocol_eligible"] == 0
    assert card["verdict"] == "negative"
    assert card["decision"] == "DUPLICATE_STOP"
    assert card["ok_to_submit"] is False
    assert card["approved_for_weekly_slot"] is False
    assert card["weekly_slots_used"] == 0
    assert card["experiments_run"] == 0
    assert card["new_tif_generated"] is False
    assert card["ok_to_download_new_file"] is False
    assert card["ok_to_download_research_artifacts"] is True
    assert card["raster_file"] is None
    assert card["raster_sha256"] is None
    assert card["holdout_dti"]["dti"] is None
    assert card["holdout_dti"]["ci95"] is None
    assert card["holdout_dti"]["withheld_positive_pixels"] is None
    assert card["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
    assert len(card["submission_name"]) <= 140
    assert len(card["submission_note"]) == card["submission_note_characters"]
    assert len(card["submission_note"]) <= 140
    assert card["submission_name_status"] == "RESERVED_ONLY_NO_FILE_NOT_FOR_PORTAL"


def test_fresh_focus_sample_is_bound_to_current_snapshot_and_fail_closed():
    freshness = read_json("evidence/focus_freshness_20261028_3ad2104f.json")
    sample = read_json("evidence/focus_current_samples_20261028_3ad2104f.json")
    assert freshness == read_json("docs/data/focus_freshness_20261028_3ad2104f.json")
    assert sample == read_json("docs/data/focus_current_samples_20261028_3ad2104f.json")
    assert freshness["status"] == "COMPLETE"
    assert freshness["counts"] == {"changed": 9, "unchanged": 0, "unknown": 0}
    assert sample["ok_to_submit"] is False
    assert sample["approved_for_weekly_slot"] is False
    assert sample["new_tiffs_generated"] == 0
    assert sample["weekly_slots_used"] == 0
    assert {row["site"] for row in sample["rows"]} == FOCUS_SITES
    assert len(sample["rows"]) == 9
    assert all(row["decision"] == "DUPLICATE_STOP" for row in sample["rows"])
    assert all(row["overlap_3px"] == 1.0 for row in sample["rows"])
    assert sum(row["format_pass"] is False for row in sample["rows"]) == 2
    exterior_nan_rows = {
        row["site"] for row in sample["rows"]
        if row.get("format_pixel_counts", {}).get("outside_nonfinite") == 7_111_787
    }
    assert exterior_nan_rows == {"GEMSDOE28", "GEMSDOE30"}
    for row in sample["rows"]:
        counts = row.get("format_pixel_counts")
        assert counts["inside_nonfinite"] == 0
        assert counts["inside_finite_out_of_range"] == 0


def test_current_site_status_and_inventory_include_post_snapshot_mainline_artifact():
    status = read_json("docs/status.json")
    assert status["current_review"] == "data/session_3ad2104f_run_card.json"
    assert status["previous_review"] == "data/session_60f326dc_run_card.json"
    assert status["ok_to_submit"] is False
    assert (ROOT / "docs/research/session-3ad2104f-review.md").is_file()
    assert read_json("docs/data/focus_freshness_20261028_3ad2104f.json") == read_json(
        "evidence/focus_freshness_20261028_3ad2104f.json"
    )
    assert read_json("docs/data/focus_current_samples_20261028_3ad2104f.json") == read_json(
        "evidence/focus_current_samples_20261028_3ad2104f.json"
    )
    audit = read_json("docs/data/download_audit.json")
    assert audit["tiff_count"] == 50
    assert audit["additional_research_tiff_count"] == 1
    assert audit["total_published_tiff_count"] == 51
    assert audit["total_research_download_pass_count"] == 51
    assert audit["protocol_eligible_count"] == 0
    gtz = next(row for row in audit["artifacts"]
               if row["file"] == "gems88-gtz-damagezone-gauss-150m-20261028T163420Z-zeros-DO-NOT-SUBMIT.tif")
    assert gtz["sha256"] == "1547a37a48cbfd74909243706e9ec84c70907351077a49e715aa3753e6c7a676"
    assert gtz["research_download_ok"] is True
    assert gtz["ok_to_submit"] is False
    assert gtz["decision"] == "DUPLICATE_STOP"


def test_preplacement_witness_proof_and_h33_geometry_are_evidence_only():
    card = read_json("registry/session_3ad2104f_run_card.json")
    proof = card["registry_comparison"]["preflight"]
    assert proof["exit_code"] == 2
    assert proof["witness_file"] == "data/registry/dense_17gemdoe.tif"
    assert proof["witness_sha256"] == "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    assert proof["allowed_pixels"] == 5_106_385
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"]
    assert card["registry_comparison"]["universal_lower_bound_overlap_3px_for_any_nonempty_allowed_candidate"] == 1.0
    h33 = card["h33_forensics"]
    assert h33["organizer_confirmed_score"] is None
    assert h33["positive_pixels"] == 37_654
    assert h33["d2_8_pixels_removed"] == 6_436
    assert h33["removed_at_most_1px"] + h33["removed_between_1_and_2px"] == h33["d2_8_pixels_removed"]
    assert h33["removed_over_2px"] == 0


def test_hypotheses_and_user_claims_are_not_scores_or_clearance():
    card = read_json("registry/session_3ad2104f_run_card.json")
    queue = read_json("registry/hypothesis_queue.json")
    assert [row["id"] for row in card["candidate_hypotheses"]] == [
        "H88-SPR", "H88-AWA", "H88-CBC"
    ]
    assert [row["id"] for row in queue["proposals"]] == [
        "H88-SPR", "H88-AWA", "H88-CBC"
    ]
    claims = card["historical_focus_claims"]
    assert claims["organizer_receipts_found"] == 0
    assert claims["valid_fixed_file_estimate"] is None
    assert claims["evidence_class"].startswith("USER-REPORTED CLAIMS")
    assert set(claims["claims_by_site"]) == FOCUS_SITES
    assert claims["claims_by_site"]["GEMSDOE32"] == ["0.2778"]
    assert claims["leaderboard_maxima_in_user_message"] == ["0.3195", "0.4413"]
    assert claims["leaderboard_status"] == "UNRECONCILED_NOT_FRESHLY_RETRIEVED"


def test_prompt_and_readme_record_the_current_session_without_overclaiming():
    prompt = (ROOT / "USER_PROMPT_20261028.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    source = read_json("evidence/session_3ad2104f_source_access.json")
    assert "not represented as a verbatim replay" in prompt
    assert "USER_PROMPT_20261028.md" in agents
    assert "CURRENT DECISION (`2026-10-28`, Session `3ad2104f`)" in readme.splitlines()[2]
    assert "Latest three-pass evidence-only review (`3ad2104f`" in readme
    assert "research/session-3ad2104f-review.md" in readme
    assert "DO NOT SUBMIT" in readme
    assert source["fresh_official_source_retrieved"]["branch_head_sha"] == "aebe92f7c8a990f0e3443451b7a825d9afd6336b"
    assert source["fresh_official_source_retrieved"]["readme_sha256"] == "cfa4d55559c9128313beb9417eae7e0a94c31677132afb1120f9e86222804239"
    assert source["verdict"] == "LIMITED_SOURCE_VERIFICATION"


def test_public_review_mirror_uses_valid_site_relative_links():
    original = (ROOT / "research/session-3ad2104f-review.md").read_text(encoding="utf-8")
    public = (ROOT / "docs/research/session-3ad2104f-review.md").read_text(encoding="utf-8")
    expected = original
    for old, new in (("../docs/data/", "../data/"), ("../evidence/", "../data/"),
                     ("../registry/", "../data/")):
        expected = expected.replace(old, new)
    for script in ("download_competition_data.sh", "prepare_data.py"):
        expected = expected.replace(
            f"../scripts/{script}",
            f"https://github.com/buffedlizard55-lab/GEMSDOE88/blob/arena/3ad2104f-gemsdoe88/scripts/{script}",
        )
    assert public == expected


def test_active_browser_receipt_binds_current_site_and_research_download():
    card = read_json("docs/data/session_3ad2104f_run_card.json")
    receipt_path = card["verification"]["browser_evidence"]
    receipt_bytes = (ROOT / receipt_path).read_bytes()
    assert receipt_bytes == (ROOT / "docs/data" / Path(receipt_path).name).read_bytes()
    receipt = json.loads(receipt_bytes)
    assert receipt["status"] == "PASS"
    assert receipt["ok_to_submit"] is False
    assert receipt["research_download"]["click_matches_canonical_bytes"] is True
    archived = card["archived_research_download"]
    assert receipt["research_download"]["sha256"] == archived["sha256"]
    assert receipt["research_download"]["ok_to_submit"] is False
    assert archived["ok_to_submit"] is False
    assert hashlib.sha256((ROOT / archived["file"]).read_bytes()).hexdigest() == archived["sha256"]
    for relative, expected in receipt["source_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
