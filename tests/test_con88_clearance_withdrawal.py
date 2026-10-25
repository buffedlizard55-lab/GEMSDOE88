"""Regression suite for H88-CON88 clearance withdrawal (IR-88-96F5F523-01 / IR-88-3C391D97-01) and session 3c391d97 artifacts."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_con88_run_card_gates_and_withdrawal_mirrors_are_negative():
    rc_root = json.loads((ROOT / "run_card_con88.json").read_text(encoding="utf-8"))
    rc_reg = json.loads((ROOT / "registry/con88_run_card.json").read_text(encoding="utf-8"))
    rc_web = json.loads((ROOT / "docs/data/con88_run_card.json").read_text(encoding="utf-8"))
    rc_dl = json.loads(
        (
            ROOT
            / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.json"
        ).read_text(encoding="utf-8")
    )
    assert rc_reg == rc_web
    assert rc_reg["lane"] == "H88-CON88"
    assert {k: v for k, v in rc_reg.items() if k != "lane"} == rc_root
    for card in (rc_root, rc_dl):
        assert card["ok_to_submit"] is False
        assert card["verdict"] == "negative"
        assert card["decision"] == "DUPLICATE_STOP"
        assert card["approved_for_weekly_slot"] is False
        assert card["literal_overlap_3px"] == 1.0
        assert card["historical_holdout_valid_for_promotion"] is False
    assert rc_root["submission_name"].endswith("-DO-NOT-SUBMIT")
    assert 0 < len(rc_root["submission_note"]) <= 140
    assert "DO NOT SUBMIT" in rc_root["submission_note"]

    gates_reg = json.loads((ROOT / "registry/con88_gates.json").read_text(encoding="utf-8"))
    gates_web = json.loads((ROOT / "docs/data/con88_gates.json").read_text(encoding="utf-8"))
    assert gates_reg == gates_web
    assert gates_reg["ok_to_submit"] is False
    assert gates_reg["verdict"] == "negative"
    assert gates_reg["decision"] == "DUPLICATE_STOP"
    assert gates_reg["literal_overlap_3px"] == pytest.approx(1.0)
    assert gates_reg["historical_holdout_valid_for_promotion"] is False
    assert gates_reg["candidate"].endswith("-DO-NOT-SUBMIT.tif")

    exp_reg = json.loads((ROOT / "registry/con88_experiments.json").read_text(encoding="utf-8"))
    exp_web = json.loads((ROOT / "docs/data/con88_experiments.json").read_text(encoding="utf-8"))
    assert exp_reg == exp_web
    assert exp_reg["ok_to_submit"] is False
    assert exp_reg["verdict"] == "negative"

    collar_reg = json.loads((ROOT / "registry/con88_collar_holdout.json").read_text(encoding="utf-8"))
    collar_web = json.loads((ROOT / "docs/data/con88_collar_holdout.json").read_text(encoding="utf-8"))
    assert collar_reg == collar_web

    w_ev = json.loads((ROOT / "evidence/con88_clearance_withdrawal_20261025.json").read_text(encoding="utf-8"))
    w_web = json.loads((ROOT / "docs/data/con88_clearance_withdrawal_20261025.json").read_text(encoding="utf-8"))
    assert w_ev == w_web
    assert w_ev["irregularity_id"] == "IR-88-3C391D97-01"
    assert w_ev["ok_to_submit"] is False
    assert w_ev["verdict"] == "negative"


def test_con88_archived_package_carries_do_not_submit_with_unchanged_tiff_bytes():
    old_tif = ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.tif"
    old_zip = old_tif.with_suffix(".zip")
    old_json = old_tif.with_suffix(".json")
    assert not old_tif.exists() and not old_zip.exists() and not old_json.exists()

    tif_path = (
        ROOT
        / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif"
    )
    zip_path = tif_path.with_suffix(".zip")
    assert tif_path.is_file() and zip_path.is_file()
    assert _sha256(tif_path) == "e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68"
    assert _sha256(zip_path) == "73ee608ad9401e70bbaeb1b28104118086b554569ae5891146de6430f39bf9cb"
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()


def test_validate_con88_and_preflight_fail_closed():
    if not (ROOT / "data/bridge/sample_submission.tif").is_file():
        pytest.skip("SHA-pinned validation inputs not restored in this checkout")

    res_ok = subprocess.run(
        [sys.executable, "scripts/validate_con88.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res_ok.returncode == 0, res_ok.stdout + res_ok.stderr
    payload = json.loads(res_ok.stdout)
    assert payload["ok_to_submit"] is False
    assert payload["verdict"] == "negative"
    assert payload["research_download_ok"] is True

    res_req = subprocess.run(
        [sys.executable, "scripts/validate_con88.py", "--require-submit"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res_req.returncode == 2

    res_pre = subprocess.run(
        [sys.executable, "scripts/con88_preflight.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert res_pre.returncode == 2


def test_documentation_and_html_withdraw_con88_upload_clearance():
    for rel in ("README.md", "PROMPT.md", "docs/SUBMIT.md", "index.html", "docs/con88.html"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "OK TO DOWNLOAD AND SUBMIT: H88-CON88" not in text
        assert "IR-88-3C391D97-01" in text

    for stem in ("session-con88-20261025.md", "session-3c391d97-review.md"):
        assert (ROOT / "research" / stem).read_bytes() == (ROOT / "docs/research" / stem).read_bytes()

    for rc_rel in (
        "registry/session_3c391d97_run_card.json",
        "docs/data/session_3c391d97_run_card.json",
        "evidence/session_3c391d97_run_card.json",
    ):
        card = json.loads((ROOT / rc_rel).read_text(encoding="utf-8"))
        assert card["status"] == "DUPLICATE_STOP"
        assert card["verdict"] == "negative"
        assert card["ok_to_submit"] is False
        assert card["weekly_slots_used"] == 0
        assert 0 < len(card["submission_name"]) <= 140
        assert 0 < len(card["submission_note"]) == card["submission_note_characters"] <= 140
