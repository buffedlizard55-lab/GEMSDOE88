"""Regression tests: CON88 equal-support values are diagnostics, never clearance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import con88_preflight, generation_guard  # noqa: E402
from scripts.validate_con88 import FILE, SHA256  # noqa: E402
from vendor.gems57.uniqueness import (  # noqa: E402
    binding_duplicate_decision_v4,
    equal_support_dots,
)

CANDIDATE = ROOT / FILE


def test_equal_support_remains_available_as_a_diagnostic():
    surface = np.linspace(0.0, 1.0, 100, dtype=np.float32).reshape(10, 10)
    valid = np.ones_like(surface, dtype=bool)
    dots = equal_support_dots(surface, 7, valid)
    assert dots.dtype == np.bool_
    assert int(dots.sum()) == 7
    assert np.all(dots[surface < np.partition(surface.ravel(), -7)[-7]] == 0)


def test_dense_topn_pass_cannot_override_literal_overlap_failure():
    rows = [{
        "file": "dense.tif",
        "forward_overlap": 1.0,
        "spearman": 0.1,
        "is_continuous_surface": True,
        "topn_overlap": 0.2,
    }]
    result = binding_duplicate_decision_v4(rows)
    assert result["representation_aware_binding"] is False
    assert result["worst_literal_forward_overlap"] == 1.0
    assert result["duplicate"] is True
    assert result["stop_required"] is True
    assert result["verdict"] == "negative"
    assert result["rows"][0]["fails_effective_dot_diagnostic"] is False
    assert result["rows"][0]["fails_dot"] is True


def test_con88_preflight_delegates_to_shared_guard(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(generation_guard, "enforce_generation_preflight", lambda root: calls.append(root))
    con88_preflight.enforce_con88_preflight(tmp_path)
    assert calls == [tmp_path]


def test_corrected_records_preserve_diagnostics_but_deny_submission():
    gates = json.loads((ROOT / "registry/con88_gates.json").read_text())
    card = json.loads((ROOT / "run_card_con88.json").read_text())
    withdrawal = json.loads((ROOT / "evidence/con88_clearance_withdrawal_96f5f523.json").read_text())
    assert gates["G1_ok"] and gates["G3_ok"] and gates["canary_ok"]
    assert gates["G2_uniqueness"]["worst_overlap"]["overlap_equal_support"] == pytest.approx(0.6936314866946407)
    assert gates["literal_overlap_3px"] == card["literal_overlap_3px"] == 1.0
    assert gates["G2_ok"] is False
    assert gates["holdout"]["usable_for_promotion"] is False
    assert card["holdout_DTI"]["usable_for_promotion"] is False
    for record in (gates, card, withdrawal):
        assert record["ok_to_submit"] is False
        assert record["verdict"] == "negative"
    assert gates["approved_for_weekly_slot"] is False
    assert card["organizer_confirmed_score"] is None
    assert len(card["submission_note"]) <= 140


def test_archived_package_is_visibly_negative_and_byte_consistent():
    archive = CANDIDATE.with_suffix(".zip")
    assert CANDIDATE.is_file() and archive.is_file()
    assert "DO-NOT-SUBMIT" in CANDIDATE.name and "DO-NOT-SUBMIT" in archive.name
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() == SHA256
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.namelist() == [CANDIDATE.name]
        assert zipped.read(CANDIDATE.name) == CANDIDATE.read_bytes()


@pytest.mark.skipif(
    not (ROOT / "data/registry/dense_17gemdoe.tif").is_file(),
    reason="validation inputs not restored",
)
def test_real_con88_preflight_stops_in_all_entry_modes():
    for command in (
        [sys.executable, "scripts/con88_preflight.py"],
        [sys.executable, "-O", "scripts/con88_preflight.py"],
        [sys.executable, "-m", "scripts.con88_preflight"],
    ):
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=30)
        assert result.returncode == 2, result.stdout + result.stderr
        payload = json.loads(result.stderr)
        assert payload["decision"] == "DUPLICATE_STOP"
        assert payload["preplacement_registry_proof"]["uncovered_allowed_pixels"] == 0
        assert payload["generation_allowed"] is False
        assert payload["experiments_run"] == payload["new_rasters_generated"] == 0
        assert result.stdout == ""


@pytest.mark.skipif(
    not (ROOT / "data/registry/dense_17gemdoe.tif").is_file(),
    reason="validation inputs not restored",
)
def test_read_only_validator_passes_research_and_denies_submission():
    paths = (CANDIDATE, CANDIDATE.with_suffix(".zip"), ROOT / "run_card_con88.json")
    before = {path: (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths}
    normal = subprocess.run(
        [sys.executable, "scripts/validate_con88.py"], cwd=ROOT,
        text=True, capture_output=True, timeout=30,
    )
    assert normal.returncode == 0, normal.stdout + normal.stderr
    payload = json.loads(normal.stdout)
    assert payload["decision"] == "DUPLICATE_STOP"
    assert payload["research_download_ok"] is True
    assert payload["ok_to_submit"] is False
    strict = subprocess.run(
        [sys.executable, "scripts/validate_con88.py", "--require-submit"], cwd=ROOT,
        text=True, capture_output=True, timeout=30,
    )
    assert strict.returncode == 2, strict.stdout + strict.stderr
    assert json.loads(strict.stdout)["ok_to_submit"] is False
    after = {path: (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths}
    assert after == before
