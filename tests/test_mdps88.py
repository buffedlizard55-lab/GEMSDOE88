"""MDPS-88 deliverable consistency (run card <-> bytes <-> gate <-> site strings)."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "registry/mdps88_run_card.json").read_text())


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_mdps88_card_matches_bytes():
    tif = ROOT / CARD["raster"]["file"]
    assert tif.is_file() and sha(tif) == CARD["raster_sha256"] == CARD["raster"]["sha256"]
    assert sha(ROOT / CARD["raster"]["zip"]) == CARD["raster"]["zip_sha256"]
    web = json.loads((ROOT / "docs/data/mdps88_run_card.json").read_text())
    assert web == CARD


def test_mdps88_negative_verdict_is_consistent_everywhere():
    assert CARD["verdict"] == "negative" and CARD["ok_to_submit"] is False
    assert CARD["approved_for_weekly_slot"] is False and CARD["organizer_confirmed_score"] is None
    assert "DO-NOT-SUBMIT" in Path(CARD["raster"]["file"]).name
    assert len(CARD["submission_note"]) <= 140 and CARD["submission_note_chars"] == len(CARD["submission_note"])
    audit = json.loads((ROOT / "evidence/mdps88_independent_audit_20261024.json").read_text())
    assert audit["audit_passed"] is True and audit["sha256"] == CARD["raster_sha256"]
    gate = json.loads((ROOT / "docs/data/mdps88-gate.json").read_text())
    assert gate["ok_to_submit"] is False and gate["sha256"] == CARD["raster_sha256"]


def test_mdps88_holdout_numbers_are_labelled_and_in_range():
    h = CARD["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI" and h["evaluator_version"] == "gems57-pooled-hide-v2"
    for k in ("far", "overall"):
        d = h[k]["dti"]
        assert h[k]["ci95"][0] <= d <= h[k]["ci95"][1] and 0 <= d <= 1
        assert h[k]["withheld_positive_pixels"] > 0
    assert CARD["holdout"]["far"]["paired_vs_base283"]["ci95"][0] <= 0  # the documented null result
    assert CARD["leakage_canary"]["max_symmetric_auc"] <= 0.90 and CARD["leakage_canary"]["passed"]
    u = CARD["correlation_overlap_vs_registry"]
    assert u["duplicate"] is False and u["worst_excess_overlap_3px"] <= 0.70 and abs(u["worst_abs_spearman"]) <= 0.90


def test_mdps88_site_decision_strings():
    for page in ("docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / page).read_text()
        # 2026-10-24 (IR-88-88): the landing/summary pages lead with the canonical PHASE-88 release.
        assert Path(json.loads((ROOT / "registry/phase88_run_card.json").read_text())["download"]).name in text
        assert "DO NOT SUBMIT" in text and "DOWNLOAD FOR RESEARCH: YES" in text
        assert "hyp-psg" not in text  # withdrawn mock must never be offered again (IR-88-83)
