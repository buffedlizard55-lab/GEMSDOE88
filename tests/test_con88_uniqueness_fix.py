"""Regression tests for withdrawal of the unauthorized CON88 exception."""
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
from scripts.validate_con88 import CANDIDATE, EXPECTED_SHA256, inspect  # noqa: E402
from vendor.gems57.uniqueness import (  # noqa: E402
    binding_duplicate_decision_v4,
    equal_support_dots,
)


def test_equal_support_is_available_as_diagnostic_only():
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
    monkeypatch.setattr(con88_preflight, "enforce_generation_preflight", lambda root: calls.append(root))
    con88_preflight.enforce_con88_preflight(tmp_path)
    assert calls == [tmp_path]


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


def test_con88_records_are_negative_and_preserve_historical_diagnostic():
    gates = json.loads((ROOT / "registry/con88_gates.json").read_text())
    card = json.loads((ROOT / "run_card_con88.json").read_text())
    withdrawal = json.loads((ROOT / "evidence/con88_clearance_withdrawal_20261025.json").read_text())
    for record in (gates, card, withdrawal):
        assert record["ok_to_submit"] is False
        assert record["verdict"] == "negative"
    assert gates["clearance_withdrawn"] is True
    assert gates["historical_equal_support_gate"]["historical_pass"] is True
    assert gates["historical_equal_support_gate"]["worst_overlap"] == pytest.approx(0.6936314866946407)
    assert gates["binding_literal_gate"]["forward_overlap_lower_bound"] == 1.0
    assert gates["binding_literal_gate"]["covered_allowed_pixels"] == 5_106_385
    assert "DO-NOT-SUBMIT" in gates["candidate"]
    assert len(card["submission_note"]) <= 140
    assert card["organizer_confirmed_score"] is None


def test_archived_package_is_visibly_negative_and_byte_consistent():
    tif = CANDIDATE
    archive = tif.with_suffix(".zip")
    assert tif.is_file() and archive.is_file()
    assert "DO-NOT-SUBMIT" in tif.name and "DO-NOT-SUBMIT" in archive.name
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == EXPECTED_SHA256
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.namelist() == [tif.name]
        assert zipped.read(tif.name) == tif.read_bytes()


@pytest.mark.skipif(
    not (ROOT / "data/registry/dense_17gemdoe.tif").is_file(),
    reason="validation inputs not restored",
)
def test_read_only_validator_reproduces_negative_decision():
    before = {
        path: (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in (CANDIDATE, CANDIDATE.with_suffix(".zip"), ROOT / "run_card_con88.json")
    }
    result = inspect(ROOT)
    assert result["validator_output"]["ok"] is True
    assert result["research_download_ok"] is True
    assert result["binding_literal_registry"]["uncovered_allowed_pixels"] == 0
    assert result["ok_to_submit"] is False
    assert result["approved_for_weekly_slot"] is False
    assert result["decision"] == "DUPLICATE_STOP"
    assert result["verdict"] == "negative"
    after = {
        path: (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in before
    }
    assert after == before


@pytest.mark.skipif(
    not (ROOT / "data/registry/dense_17gemdoe.tif").is_file(),
    reason="validation inputs not restored",
)
def test_validator_require_submit_fails_closed():
    normal = subprocess.run(
        [sys.executable, "scripts/validate_con88.py"], cwd=ROOT,
        text=True, capture_output=True, timeout=30,
    )
    assert normal.returncode == 0, normal.stdout + normal.stderr
    assert json.loads(normal.stdout)["ok_to_submit"] is False
    strict = subprocess.run(
        [sys.executable, "scripts/validate_con88.py", "--require-submit"], cwd=ROOT,
        text=True, capture_output=True, timeout=30,
    )
    assert strict.returncode == 2, strict.stdout + strict.stderr
    assert json.loads(strict.stdout)["ok_to_submit"] is False
