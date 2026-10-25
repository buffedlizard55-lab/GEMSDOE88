"""Regression checks for the preregistered, pre-placement MTAS negative result."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import preflight_mtas88 as preflight  # noqa: E402


@pytest.fixture(scope="module")
def recomputed_card():
    if not (ROOT / preflight.WITNESS_REL).is_file():
        pytest.skip("SHA-pinned validation inputs not restored")
    return preflight.inspect()


def test_hard_blocker_is_preplacement_and_not_a_new_score(recomputed_card):
    c = recomputed_card
    proof = c["preplacement_registry_proof"]
    assert proof["witness_sha256"] == preflight.WITNESS_SHA
    assert proof["allowed_pixels"] == 5_106_385
    assert proof["uncovered_allowed_pixels"] == 0
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"]
    assert proof["universal_overlap_blocker"] is True
    assert c["correlation_overlap_vs_registry"]["universal_lower_bound_on_any_nonempty_candidate_overlap_3px"] == 1.0
    assert c["correlation_overlap_vs_registry"]["surface_rank_correlation"] is None
    assert c["correlation_overlap_vs_registry"]["final_dot_overlap_3px"] is None
    assert c["decision"] == "DUPLICATE_STOP"
    assert c["holdout"]["dti"] is None
    assert c["holdout"]["ci95"] is None
    assert c["single_feature_canaries"]["auc"] is None
    assert c["new_rasters_generated"] == 0
    assert c["raster_sha256"] is None
    assert c["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
    assert c["weekly_slots_used"] == 0
    assert c["experiment_count"] == 0
    assert c["ok_to_submit"] is False
    assert len(c["submission_note"]) <= 140


def test_existing_download_is_format_only(recomputed_card):
    archived = recomputed_card["archived_research_download"]
    assert archived["ok_to_download_for_research_only"] is True
    assert archived["ok_to_submit"] is False
    assert archived["validator_output"]["ok"] is True
    assert archived["validator_output"]["raster_sha256"] == archived["sha256"]
    assert "DO-NOT-SUBMIT" in archived["download"]


def test_fail_closed_on_witness_hash_change(monkeypatch):
    if not (ROOT / preflight.WITNESS_REL).is_file():
        pytest.skip("SHA-pinned validation inputs not restored")
    monkeypatch.setattr(preflight, "WITNESS_SHA", "0" * 64)
    with pytest.raises((RuntimeError, ValueError), match="(?i)(sha|pin|hash)"):
        preflight.inspect()


def test_expected_generation_gate_exit_and_committed_report(recomputed_card):
    result = subprocess.run(
        [sys.executable, "scripts/preflight_mtas88.py", "--gate-generation"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "DUPLICATE_STOP" in result.stdout
    for rel in preflight.OUTPUTS:
        assert json.loads((ROOT / rel).read_text()) == recomputed_card


def test_site_leads_with_current_negative_and_never_falls_back_to_approval():
    for rel in ("docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / rel).read_text()
        assert "data/sdtl88_run_card.json" in text
        assert "data/mtas88_run_card.json" in text or "mtas88" in text
        assert "DO NOT SUBMIT" in text  # archived lanes remain marked
        assert "1.0" in text
        assert "0.70" in text
    js = (ROOT / "docs/assets/site.js").read_text()
    assert "fetch('data/sdtl88_run_card.json'" in js
    assert "PRE-FLIGHT AUDIT UNAVAILABLE" in js
