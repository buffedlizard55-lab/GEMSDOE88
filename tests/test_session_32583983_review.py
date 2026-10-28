"""Session 32583983 negative decision and dated focus evidence stay auditable."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_negative_run_card_and_session_dated_feed_mirrors():
    card_paths = [ROOT / prefix / "session_32583983_run_card.json"
                  for prefix in ("registry", "evidence", "docs/data")]
    raw = card_paths[0].read_bytes()
    assert all(path.read_bytes() == raw for path in card_paths)
    card = json.loads(raw)

    assert card["status"] == card["decision"] == "DUPLICATE_STOP"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is card["approved_for_weekly_slot"] is False
    assert card["new_tif_generated"] is False and card["new_rasters_generated"] == 0
    assert card["raster_file"] is card["raster_sha256"] is None
    assert card["estimated_submission_score"] is None
    assert card["holdout"]["dti"] is card["holdout"]["ci95"] is None
    assert card["holdout"]["withheld_positive_pixels"] is None
    assert card["leakage_canary"]["max_symmetric_auc"] is None
    assert card["organizer_confirmed_score"] is None
    assert card["experiment_count"] == card["weekly_slots_used"] == 0
    assert len(card["submission_note"]) == card["submission_note_length"] <= 140
    assert "DO NOT SUBMIT" in card["submission_note"]
    upstream = card["intervening_mainline_context"]
    assert upstream["pull_request"] == 222 and upstream["ok_to_submit"] is False
    assert upstream["no_slot_used"] is True and upstream["upstream_run_new_rasters_generated"] == 1
    assert upstream["holdout_dti"] is upstream["leakage_canary_auc"] is None
    assert upstream["dense_witness_overlap_3px"] == 1.0

    proof = card["registry_comparison"]["proof"]
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"] == 5_106_385
    assert proof["uncovered_allowed_pixels"] == 0
    assert proof["covered_allowed_fraction"] == 1.0
    assert card["registry_comparison"]["universal_minimum_forward_overlap_3px_for_nonempty_allowed_candidate"] == 1.0
    assert card["registry_comparison"]["overlap_limit"] == 0.70

    feed = card["current_focus_feed"]
    freshness_path = ROOT / feed["head_snapshot_file"]
    sample_path = ROOT / feed["feed_file"]
    sample_evidence_path = ROOT / feed["evidence_file"]
    assert sample_path.read_bytes() == sample_evidence_path.read_bytes()
    freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(freshness_path.read_bytes()).hexdigest() == feed["head_snapshot_sha256"]
    assert hashlib.sha256(sample_path.read_bytes()).hexdigest() == feed["sample_sha256"]
    assert freshness["counts"] == {"changed": 9, "unchanged": 0, "unknown": 0}
    assert sample["counts"]["DUPLICATE_STOP"] == 9
    assert sample["counts"]["NOT_DISCOVERED"] == 0
    assert sample["score_status"].startswith("NOT MEASURED")
    assert feed["ok_to_submit"] is False


def test_review_decision_and_hypotheses_are_explicit_and_embedded_request_is_preserved():
    review = (ROOT / "research/session-32583983-review.md").read_text(encoding="utf-8")
    hypotheses = (ROOT / "research/session-32583983-hypotheses.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    prompt = (ROOT / "USER_PROMPT_20261027.md").read_text(encoding="utf-8").strip()

    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                 "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in review
    assert "USER-REPORTED: 0.2778" in review
    assert "NO NEW TIFF — DO NOT SUBMIT" in review
    assert "three conditional hypotheses" in review
    assert all(name in hypotheses for name in ("H88-SPR", "H88-AWA", "H88-CBC"))
    assert "No hypothesis from session `32583983` was tested" in hypotheses
    assert "DUPLICATE_STOP" in readme and "DO NOT SUBMIT" in readme
    assert "gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif" in readme
    assert "gems88-gtz-damagezone-gauss-150m-20261028T163420Z-zeros-DO-NOT-SUBMIT.tif" in readme
    assert prompt in readme


def test_merged_pr_222_gtz_artifact_is_audited_but_never_cleared():
    card = read_json("docs/data/gtz88_run_card.json")
    path = ROOT / "docs/downloads" / card["validator_output"]["artifact"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == card["raster_sha256"] == card["validator_output"]["sha256"]
    assert card["new_rasters_generated"] == 1  # from merged PR #222, not this session
    assert card["ok_to_submit"] is False and card["verdict"] == "negative"
    assert card["holdout_progression"]["note"].startswith("Holdout not run")
    assert card["leakage_canaries"]["note"].startswith("Not run")
    assert card["correlation_overlap_vs_registry"]["final_dot_overlap_3px_vs_dense_witness"] == 1.0
    assert card["uniqueness_vs_focus_sites"]["gtz_h195_overlap"] == 0.0293
    assert card["uniqueness_vs_focus_sites"]["gtz_unique_vs_h195_lineage"] is True

    audit = read_json("docs/data/download_audit.json")
    row = next(item for item in audit["artifacts"] if item["file"] == path.name)
    assert row["sha256"] == digest and row["format_valid"] is True
    assert row["research_download_ok"] is True and row["ok_to_submit"] is False
    assert row["decision"] == "DUPLICATE_STOP" and row["literal_overlap_lower_bound"] == 1.0
    assert audit["total_published_tiff_count"] == 51 and audit["protocol_eligible_count"] == 0

    page = (ROOT / "docs/executive-summary.html").read_text(encoding="utf-8")
    guide = (ROOT / "docs/SUBMIT.md").read_text(encoding="utf-8")
    assert "GTZ-88: research artifact only — DO NOT SUBMIT" in page
    assert "HOLDOUT-DTI: not run" in page and "1.0000 &gt; 0.70" in page
    assert "do not submit it" in guide.lower()
    assert "51/51" in guide
