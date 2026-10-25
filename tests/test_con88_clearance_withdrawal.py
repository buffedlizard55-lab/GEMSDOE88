"""Regression tests for the H88-CON88 clearance withdrawal (IR-88-3C391D97-01) and session 3c391d97."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_con88_run_card_gates_and_withdrawal_mirrors_are_negative():
    root_card = json.loads((ROOT / "run_card_con88.json").read_text())
    reg_card = json.loads((ROOT / "registry/con88_run_card.json").read_text())
    web_card = json.loads((ROOT / "docs/data/con88_run_card.json").read_text())
    assert root_card == reg_card == web_card
    assert root_card["verdict"] == "negative"
    assert root_card["ok_to_submit"] is False
    assert root_card["ok_to_download"] is True
    assert root_card["approved_for_weekly_slot"] is False
    assert root_card["policy_correction"] == "IR-88-3C391D97-01"
    assert root_card["correlation_and_overlap_vs_registry"]["max_literal_dot_overlap_3px"] == 1.0
    assert root_card["correlation_and_overlap_vs_registry"]["literal_unique"] is False
    assert root_card["correlation_and_overlap_vs_registry"]["literal_stop_required"] is True
    assert root_card["holdout_dti"]["fixed_tif_vs_withheld_segments"]["dti"] == 0.0
    assert root_card["holdout_dti"]["per_fold_collar_reemission_visible_only"]["beats_holdout_best"] is False
    assert 0 < len(root_card["submission_name"]) <= 140
    assert "DO-NOT-SUBMIT" in root_card["submission_name"]
    assert 0 < len(root_card["submission_note"]) == root_card["submission_note_chars"] <= 140
    assert "DO NOT SUBMIT" in root_card["submission_note"]

    gates = json.loads((ROOT / "registry/con88_gates.json").read_text())
    web_gates = json.loads((ROOT / "docs/data/con88_gates.json").read_text())
    assert gates == web_gates
    assert gates["ok_to_submit"] is False
    assert gates["verdict"] == "negative"
    assert gates["G2_ok"] is False
    assert gates["holdout_ok"] is False
    assert gates["all_gates_ok"] is False

    withdrawal = json.loads((ROOT / "evidence/con88_clearance_withdrawal_20261025.json").read_text())
    web_withdrawal = json.loads((ROOT / "docs/data/con88_clearance_withdrawal_20261025.json").read_text())
    assert withdrawal == web_withdrawal
    assert withdrawal["irregularity_id"] == "IR-88-3C391D97-01"
    assert withdrawal["ok_to_submit"] is False
    assert withdrawal["verdict"] == "negative"


def test_con88_archived_package_carries_do_not_submit_with_unchanged_tiff_bytes():
    tif = ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif"
    zip_path = tif.with_suffix(".zip")
    meta_path = tif.with_suffix(".json")
    assert tif.is_file() and zip_path.is_file() and meta_path.is_file()
    assert not (ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.tif").exists()
    assert not (ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.zip").exists()
    assert not (ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.json").exists()

    expected_tif_sha = "e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68"
    expected_zip_sha = "5a4f4a530c81210d70dc5cd01481602227d7d84dee5428cea98ae0638f2d855d"
    assert _sha256(tif) == expected_tif_sha
    assert _sha256(zip_path) == expected_zip_sha

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif.name]
        assert zf.read(tif.name) == tif.read_bytes()

    meta = json.loads(meta_path.read_text())
    assert meta["ok_to_submit"] is False
    assert meta["verdict"] == "negative"
    assert meta["sha256"] == expected_tif_sha
    assert meta["zip_sha256"] == expected_zip_sha


@pytest.mark.skipif(
    not (ROOT / "data/bridge/sample_submission.tif").is_file()
    or not (ROOT / "data/registry/dense_17gemdoe.tif").is_file(),
    reason="validation inputs not restored",
)
def test_validate_con88_and_preflight_fail_closed():
    ok = subprocess.run([sys.executable, "scripts/validate_con88.py"], cwd=ROOT, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    payload = json.loads(ok.stdout)
    assert payload["ok_to_submit"] is False
    assert payload["verdict"] == "negative"
    assert payload["literal_overlap_vs_dense_17gemdoe_3px"] == 1.0

    blocked = subprocess.run(
        [sys.executable, "scripts/validate_con88.py", "--require-submit"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 2


def test_documentation_and_html_withdraw_con88_upload_clearance():
    for rel in ("README.md", "PROMPT.md", "docs/SUBMIT.md", "index.html", "docs/con88.html"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "OK TO DOWNLOAD AND SUBMIT: H88-CON88" not in text
        assert "IR-88-3C391D97-01" in text

    for stem in ("session-con88-20261025.md", "session-3c391d97-review.md"):
        assert (ROOT / "research" / stem).read_bytes() == (ROOT / "docs/research" / stem).read_bytes()

    reg = json.loads((ROOT / "registry/session_3c391d97_run_card.json").read_text())
    web = json.loads((ROOT / "docs/data/session_3c391d97_run_card.json").read_text())
    ev = json.loads((ROOT / "evidence/session_3c391d97_run_card.json").read_text())
    assert reg == web == ev
    assert reg["session_id"] == "3c391d97"
    assert reg["branch"] == "arena/3c391d97-gemsdoe88"
    assert reg["status"] == "DUPLICATE_STOP" and reg["verdict"] == "negative"
    assert reg["ok_to_submit"] is False and reg["new_tif_generated"] is False
    assert reg["weekly_slots_used"] == 0 and reg["organizer_confirmed_score"] is None
    assert 0 < len(reg["submission_name"]) <= 140
    assert 0 < len(reg["submission_note"]) == reg["submission_note_characters"] <= 140
