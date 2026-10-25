"""H88-MTAS executed-experiment run card: negative, unique-like-for-like, fail-closed."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "registry/mtas88_experiment_run_card.json"
SHA = "2cb828939e11cf07e12be7917722f73816550ed4e297e2409b8674ac131479cc"


@pytest.fixture(scope="module")
def card():
    return json.loads(CARD.read_text())


def test_mirrors_identical(card):
    for rel in ("docs/data/mtas88_experiment_run_card.json",
                "evidence/mtas88_experiment_20261025.json"):
        assert json.loads((ROOT / rel).read_text()) == card


def test_negative_verdict_and_no_slot(card):
    assert card["lane"] == "H88-MTAS"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["approved_for_weekly_slot"] is False
    assert card["weekly_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert card["experiment_count"] == 1
    assert "DO-NOT-SUBMIT" in card["raster_file"]


def test_holdout_labelled_with_ci_and_below_bar(card):
    h = card["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["withheld_positive_pixels"] == 22893
    assert h["n_folds"] == 8
    assert h["ci95"][0] <= h["dti"] <= h["ci95"][1]
    assert h["stored_bar"]["beats_stored_bar"] is False
    assert h["dti"] < h["stored_bar"]["dti"]


def test_canaries_and_uniqueness_thresholds(card):
    assert card["leakage_canaries"]["passed"] is True
    assert card["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    assert len(card["leakage_canaries"]["rows"]) == 14
    u = card["correlation_overlap_vs_registry"]
    assert u["surface_worst_abs_spearman"] <= 0.90
    assert u["final_like_for_like_worst_overlap_3px"] <= 0.70
    assert u["unique_like_for_like"] is True
    assert u["unique_literal"] is False  # dense continuous witness, IR-88-60
    assert u["final_literal_worst_overlap_3px"] == 1.0


def test_saved_bytes_match_card(card):
    tif = ROOT / card["raster_file"]
    digest = hashlib.sha256(tif.read_bytes()).hexdigest()
    assert digest == SHA == card["raster_sha256"] == card["validator_output"]["sha256"]
    assert card["validator_output"]["all_checks_passed"] is True
    assert card["validator_output"]["n_nan"] == 0
    assert card["validator_output"]["min"] >= 0.0
    assert card["validator_output"]["max"] <= 1.0
    assert card["production"]["fingerprint"]["n_dots"] == 37654
    assert len(card["submission_name"]) <= 140
    assert len(card["submission_note"]) == card["submission_note_length"] <= 140


def test_independent_validator_fail_closed():
    if not (ROOT / "data/bridge/sample_submission.tif").is_file():
        pytest.skip("SHA-pinned validation inputs not restored")
    ok = subprocess.run([sys.executable, "scripts/validate_mtas88_experiment.py"],
                        cwd=ROOT, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    blocked = subprocess.run(
        [sys.executable, "scripts/validate_mtas88_experiment.py", "--require-submit"],
        cwd=ROOT, capture_output=True, text=True)
    assert blocked.returncode == 2
