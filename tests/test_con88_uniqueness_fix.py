"""CON88 diagnostics must never override the binding literal registry rule."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.uniqueness import DENSE_POSITIVE_THRESHOLD, dot_overlap, equal_support_dots  # noqa: E402


def test_equal_support_top_n_remains_a_diagnostic():
    a = np.arange(100, dtype=float).reshape(10, 10)
    dots = equal_support_dots(a, 5)
    assert dots.sum() == 5
    assert set(a[dots].tolist()) == {95.0, 96.0, 97.0, 98.0, 99.0}


def test_dense_diagnostic_does_not_change_literal_result():
    rng = np.random.default_rng(0)
    dense = rng.random((200, 200))
    candidate = np.zeros((200, 200), np.float32)
    candidate[::10, ::10] = 1.0
    support = equal_support_dots(dense, int((candidate > 0).sum()))
    assert dot_overlap(candidate, support.astype(np.float32)) < 0.70
    assert dot_overlap(candidate, dense) == 1.0


def test_corrected_cards_apply_literal_and_holdout_stops():
    gate = json.loads((ROOT / "registry/con88_gates.json").read_text())
    card = json.loads((ROOT / "run_card_con88.json").read_text())
    assert gate["G2_equal_support_diagnostic"]["evidence_class"].endswith("NOT_BINDING_CLEARANCE")
    assert gate["G2_uniqueness"]["candidate_literal_3px_overlap"] == 1.0
    assert gate["G2_uniqueness"]["passes"] is False
    assert gate["G2_ok"] is gate["ok_to_submit"] is False
    assert gate["holdout_selection"]["candidate_beats_incumbent"] is False
    assert card["correlation_overlap_vs_registry"]["binding_literal_witness"]["passes"] is False
    assert card["holdout_DTI"]["selection_gate"]["passes"] is False
    assert card["ok_to_submit"] is False and card["verdict"] == "negative"
    assert "DO-NOT-SUBMIT" in gate["candidate"] == card["artifact_file"]
    assert len(card["submission_note"]) <= 140


def test_threshold_constant_is_retained_for_historical_diagnostics():
    assert DENSE_POSITIVE_THRESHOLD == 200_000


@pytest.mark.skipif(
    not (ROOT / "data/bridge/sample_submission.tif").is_file(),
    reason="validation inputs not restored",
)
def test_archive_validator_passes_research_integrity_but_rejects_submission():
    normal = subprocess.run(
        [sys.executable, "scripts/validate_con88.py"], cwd=ROOT, text=True, capture_output=True, timeout=60
    )
    assert normal.returncode == 0, normal.stdout + normal.stderr
    result = json.loads(normal.stdout)
    assert result["archive_integrity"] is True
    assert result["decision"] == "DUPLICATE_STOP"
    assert result["ok_to_download_for_research"] is True
    assert result["ok_to_submit"] is False
    required = subprocess.run(
        [sys.executable, "scripts/validate_con88.py", "--require-submit"],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    assert required.returncode == 2, required.stdout + required.stderr
    assert json.loads(required.stdout)["ok_to_submit"] is False


@pytest.mark.skipif(
    not (ROOT / "data/bridge/sample_submission.tif").is_file()
    or not (ROOT / "data/registry/dense_17gemdoe.tif").is_file(),
    reason="literal preflight inputs not restored",
)
def test_con88_preflight_direct_cli_delegates_to_shared_guard():
    """The documented direct-script entry point must not fail at import time."""
    result = subprocess.run(
        [sys.executable, "scripts/con88_preflight.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    payload = json.loads(result.stderr)
    assert payload["decision"] == "DUPLICATE_STOP"
    assert payload["ok_to_submit"] is False
