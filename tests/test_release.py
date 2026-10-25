import json
from pathlib import Path
import pytest
from validate_release import release_report

ROOT = Path(__file__).resolve().parents[1]


def test_published_card_and_tif_fail_closed():
    if not (ROOT / "data/bridge/sample_submission.tif").exists():
        pytest.skip(
            "restore grid and registry witness via scripts/restore_inputs.py --validation"
        )
    if not (ROOT / "data/registry/dense_17gemdoe.tif").exists():
        pytest.skip(
            "restore registry witness via scripts/restore_inputs.py --validation"
        )
    report = release_report()
    assert report["format_ok"]
    assert report["values_0_1"] and report["inside_no_nan"]
    assert report["literal_duplicate"] and report["registry_forward_overlap_3px"] == 1
    assert report["ok_to_download"] and not report["ok_to_submit"]
    card = json.loads((ROOT / "docs/data/run-card-mrr88.json").read_text())
    assert (
        card["submission_note"]
        == json.loads((ROOT / "registry/run_card_mrr88.json").read_text())["submission_note"]
    )
    assert len(card["submission_note"]) <= 140 and card["verdict"] == "negative"


def test_brief_and_site_are_not_missing():
    readme = (ROOT / "README.md").read_text()
    assert "Maximize P(Win)" in readme and "Own the Outcome" in readme
    assert "MUST GENERATE A UNIQUE TIF SUBMISSION" in readme
    site = (ROOT / "docs/index.html").read_text()
    assert "DO NOT SUBMIT" in site
    assert "executive-summary.html" in site
    assert "download" in site.lower()
