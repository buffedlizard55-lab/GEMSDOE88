import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
from scripts.validate_current import release_report  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: str):
    return json.loads((ROOT / path).read_text())


def test_current_mrrcoh_card_and_saved_bytes_are_canonical():
    cards = [
        load("registry/mrrcoh88_run_card.json"),
        load("evidence/mrrcoh88_run_card.json"),
        load("docs/data/mrrcoh88_run_card.json"),
    ]
    assert cards[0] == cards[1] == cards[2]
    card = cards[0]
    assert card["lane"] == "MRR-COH-88"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True and card["ok_to_submit"] is False
    assert card["weekly_slots_used"] == 0 and card["organizer_confirmed"] is None
    assert len(card["submission_note"]) <= 140

    tif, archive = ROOT / card["artifact"], ROOT / card["zip_artifact"]
    assert "DO-NOT-SUBMIT" in tif.name
    assert sha(tif) == card["raster_sha256"]
    assert sha(archive) == card["zip_sha256"]
    with zipfile.ZipFile(archive) as zf:
        assert zf.namelist() == [tif.name]
        assert zf.read(tif.name) == tif.read_bytes()


def test_current_release_reopens_bytes_and_fails_only_scientific_gate():
    if not (ROOT / "data/bridge/sample_submission.tif").is_file():
        pytest.skip("restore hash-pinned validation inputs first")
    report = release_report()
    published = load("docs/data/current_release.json")
    assert report == published
    assert report["format_valid"] and report["unique"]
    assert not report["duplicate"]
    assert report["literal_dot_field_overlap_3px"] <= 0.70
    assert report["preplacement_max_abs_spearman"] <= 0.90
    assert report["holdout_dti"] < report["incumbent_best_dti"]
    assert report["research_download_ok"] and not report["ok_to_submit"]
    assert report["reason"].startswith("HOLDOUT:")


def test_current_evidence_classes_and_public_copy_are_fail_closed():
    card = load("registry/mrrcoh88_run_card.json")
    holdout = card["holdout_dti"]
    assert holdout["evidence_class"] == "HOLDOUT-DTI"
    assert holdout["evaluator_version"] == "gems57-pooled-hide-v2"
    assert holdout["withheld_positive_pixels"] == 22_893
    assert holdout["ci95"][0] <= holdout["dti"] <= holdout["ci95"][1]
    assert card["organizer_confirmed"] is None

    for path in (
        "README.md",
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/research.html",
        "docs/sources.html",
        "docs/SUBMIT.md",
    ):
        text = (ROOT / path).read_text()
        assert "DO NOT SUBMIT" in text, path
    current_pages = "\n".join(
        (ROOT / path).read_text()
        for path in ("README.md", "docs/index.html", "docs/executive-summary.html", "docs/SUBMIT.md")
    )
    assert "gems88-mrrcoh-persistent-demag-oof" in current_pages
    assert "MAG-PSG" not in current_pages
