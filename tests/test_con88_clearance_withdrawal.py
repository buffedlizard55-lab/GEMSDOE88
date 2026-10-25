"""Regression tests for IR-88-587C7F22-01..05 (H88-CON88 clearance withdrawal & session 587c7f22)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CON88_TIF = "gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif"
CON88_SHA = "e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_con88_clearance_withdrawn_with_unchanged_tiff_bytes():
    tif = ROOT / "docs/downloads" / CON88_TIF
    zipped = tif.with_suffix(".zip")
    sidecar = tif.with_suffix(".json")
    assert tif.is_file() and zipped.is_file() and sidecar.is_file()
    assert sha256(tif) == CON88_SHA

    unmarked = ROOT / "docs/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros.tif"
    assert not unmarked.exists()
    assert not unmarked.with_suffix(".zip").exists()
    assert not unmarked.with_suffix(".json").exists()

    with zipfile.ZipFile(zipped) as zf:
        assert zf.namelist() == [CON88_TIF]
        assert zf.read(CON88_TIF) == tif.read_bytes()

    cards = [ROOT / r for r in ("registry/con88_run_card.json", "docs/data/con88_run_card.json")]
    assert cards[0].read_bytes() == cards[1].read_bytes()
    card = json.loads(cards[0].read_text())
    assert card["lane"] == "H88-CON88"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["approved_for_weekly_slot"] is False
    assert card["raster_sha256"] == CON88_SHA

    root_card = json.loads((ROOT / "run_card_con88.json").read_text())
    assert root_card["verdict"] == "negative"
    assert root_card["ok_to_submit"] is False
    assert root_card["approved_for_weekly_slot"] is False

    gates_a = ROOT / "registry/con88_gates.json"
    gates_b = ROOT / "docs/data/con88_gates.json"
    assert gates_a.read_bytes() == gates_b.read_bytes()
    gates = json.loads(gates_a.read_text())
    assert gates["ok_to_submit"] is False
    assert gates["verdict"] == "negative"

    cert_a = ROOT / "evidence/con88_clearance_withdrawal_20261025.json"
    cert_b = ROOT / "docs/data/con88_clearance_withdrawal_20261025.json"
    assert cert_a.read_bytes() == cert_b.read_bytes()
    cert = json.loads(cert_a.read_text())
    assert cert["schema"] == "gems88.historical-clearance-withdrawal.v1"
    assert cert["unchanged_tiff_sha256"] == CON88_SHA
    assert cert["prediction_bytes_changed"] is False
    assert cert["ok_to_submit"] is False


def test_validate_con88_and_preflight_cli_exits():
    for opt in ([], ["-O"]):
        ok = subprocess.run([sys.executable, *opt, "scripts/validate_con88.py"],
                            cwd=ROOT, text=True, capture_output=True)
        assert ok.returncode == 0, ok.stdout + ok.stderr
        assert '"ok_to_submit": false' in ok.stdout

        deny = subprocess.run([sys.executable, *opt, "scripts/validate_con88.py", "--require-submit"],
                              cwd=ROOT, text=True, capture_output=True)
        assert deny.returncode == 2, deny.stdout + deny.stderr

    if (ROOT / "data/bridge/sample_submission.tif").is_file():
        guard = subprocess.run([sys.executable, "-O", "scripts/con88_preflight.py"],
                               cwd=ROOT, text=True, capture_output=True)
        assert guard.returncode == 2, guard.stdout + guard.stderr


def test_public_surfaces_have_no_con88_promotion_contradiction():
    root_index = (ROOT / "index.html").read_text()
    assert "DO NOT SUBMIT" in root_index
    assert "OK TO DOWNLOAD AND SUBMIT" not in root_index

    con_html = (ROOT / "docs/con88.html").read_text()
    assert "DO NOT SUBMIT" in con_html
    assert "OK TO DOWNLOAD AND SUBMIT" not in con_html
    assert "../registry/" not in con_html
    assert "epsg.io" not in con_html
    assert CON88_TIF in con_html

    submit_md = (ROOT / "docs/SUBMIT.md").read_text()
    assert "exactly `1` eligible" not in submit_md
    assert "`0` protocol-eligible" in submit_md

    prompt_md = (ROOT / "PROMPT.md").read_text()
    assert "✅ OK TO DOWNLOAD AND SUBMIT" not in prompt_md
    assert "NEW UNIQUE TIF GENERATED AND GATES-CLEARED" not in prompt_md


def test_session_587c7f22_records_are_synchronized_and_negative():
    cards = [ROOT / r for r in (
        "registry/session_587c7f22_run_card.json",
        "evidence/session_587c7f22_run_card.json",
        "docs/data/session_587c7f22_run_card.json",
    )]
    assert len({p.read_bytes() for p in cards}) == 1
    card = json.loads(cards[0].read_text())
    assert card["branch"] == "arena/587c7f22-gemsdoe88"
    assert card["verdict"] == "negative" and card["status"] == "DUPLICATE_STOP"
    assert card["ok_to_submit"] is False and card["new_tif_generated"] is False
    assert card["weekly_slots_used"] == 0
    assert len(card["submission_note"]) == card["submission_note_characters"] <= 140

    for stem in ("review", "hypotheses"):
        rel = f"research/session-587c7f22-{stem}.md"
        assert (ROOT / rel).read_bytes() == (ROOT / "docs" / rel).read_bytes()
