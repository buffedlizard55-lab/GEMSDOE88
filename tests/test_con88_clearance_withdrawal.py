"""IR-88-F55AFF34-01 must keep the archived CON88 bytes fail-closed."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text())


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_withdrawal_receipt_binds_renamed_tiff_and_zip_member() -> None:
    receipt = load("evidence/con88_clearance_withdrawal_20261025.json")
    assert receipt == load("docs/data/con88_clearance_withdrawal_20261025.json")
    assert receipt["verdict"] == "negative"
    assert receipt["ok_to_submit"] is receipt["approved_for_weekly_slot"] is False
    assert receipt["weekly_slots_used"] == 0
    assert "DO-NOT-SUBMIT" in receipt["new_file"] and "DO-NOT-SUBMIT" in receipt["zip_member"]
    assert digest(receipt["new_file"]) == receipt["tif_sha256_unchanged"]
    zip_path = Path(receipt["new_file"]).with_suffix(".zip")
    assert digest(str(zip_path)) == receipt["new_zip_sha256"]
    with zipfile.ZipFile(ROOT / zip_path) as archive:
        assert archive.namelist() == [receipt["zip_member"]]
        assert hashlib.sha256(archive.read(receipt["zip_member"])).hexdigest() == receipt["tif_sha256_unchanged"]


def test_con88_machine_records_bind_every_failed_gate() -> None:
    card = load("run_card_con88.json")
    gate = load("registry/con88_gates.json")
    assert card == load("docs/data/run_card_con88.json")
    assert gate == load("docs/data/con88_gates.json")
    assert card["verdict"] == gate["verdict"] == "negative"
    assert card["ok_to_submit"] is gate["ok_to_submit"] is False
    assert card["approved_for_weekly_slot"] is gate["approved_for_weekly_slot"] is False
    assert gate["G2_uniqueness"]["binding_literal"]["ok"] is False
    assert gate["G2_uniqueness"]["preplacement_surface"]["ok"] is False
    assert gate["G2_uniqueness"]["inventory_complete"] is False
    assert gate["holdout_ok"] is False
    assert gate["G2_uniqueness"]["binding_literal"]["worst_overlap"] == 1.0


def test_final_session_card_is_one_negative_record() -> None:
    paths = [Path("registry/session_f55aff34_run_card.json"),
             Path("evidence/session_f55aff34_run_card.json"),
             Path("docs/data/session_f55aff34_run_card.json")]
    assert len({(ROOT / path).read_bytes() for path in paths}) == 1
    card = load(str(paths[0]))
    assert card["verdict"] == "negative" and card["status"] == "DUPLICATE_STOP"
    assert card["ok_to_submit"] is card["approved_for_weekly_slot"] is card["new_tif_generated"] is False
    assert card["budget"]["experiments_run"] == card["budget"]["weekly_slots_used"] == 0
    assert card["holdout_result"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout_result"]["withheld_positive_pixels"] == 60988
    assert card["holdout_result"]["beats_repository_best"] is False
    assert card["registry_correlation_overlap"]["binding_literal_overlap_3px"] == 1.0
    assert card["validator_output"]["values_in_0_1"] is True
    assert card["submission_name"] is None
    assert len(card["submission_note"]) == card["submission_note_characters"] <= 140
    assert card["verification"]["three_passes_completed"] is True
    assert card["verification"]["pass3"]["full_tests"]["failed"] == 0


def test_public_con88_surface_is_unambiguously_negative() -> None:
    text = (ROOT / "docs/con88.html").read_text()
    assert "DOWNLOAD FOR RESEARCH — DO NOT SUBMIT" in text
    assert "OK TO DOWNLOAD AND SUBMIT" not in text
    assert "IR-88-F55AFF34-01" in text
    assert "-DO-NOT-SUBMIT.tif" in text and "-DO-NOT-SUBMIT.zip" in text
