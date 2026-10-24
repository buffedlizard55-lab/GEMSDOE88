import json
from pathlib import Path
import subprocess
import sys
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
    card = json.loads((ROOT / "docs/data/run-card.json").read_text())
    assert (
        card["submission_note"]
        == json.loads((ROOT / "registry/run_card.json").read_text())["submission_note"]
    )
    assert len(card["submission_note"]) <= 140 and card["verdict"] == "negative"


def test_brief_and_site_are_not_missing():
    readme = (ROOT / "README.md").read_text()
    assert "Maximize P(Win)" in readme and "Own the Outcome" in readme
    assert "MUST GENERATE A UNIQUE TIF SUBMISSION" in readme
    assert "Canonical User Prompt and Standing Operating Constraints" in readme
    site = (ROOT / "docs/index.html").read_text()
    assert "DO NOT SUBMIT" in site
    assert "executive-summary.html" in site
    assert "download" in site.lower()


def test_current_pages_cannot_make_a_static_submit_ready_claim():
    from check_site import main as check_site

    current_tif = "gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif"
    for name in ("index.html", "executive-summary.html"):
        page = (ROOT / "docs" / name).read_text()
        upper = page.upper()
        assert current_tif in page
        assert "DOWNLOAD FOR RESEARCH: YES" in upper
        assert "OK TO SUBMIT: NO" in upper
        assert "FILE TO SUBMIT: NONE" in upper
        assert "DO NOT SUBMIT" in upper
        assert "OK TO SUBMIT: YES" not in upper
        assert "DOWNLOAD TIF FOR SUBMISSION" not in upper
        assert "CLICK TO DOWNLOAD FOR SUBMISSION" not in upper
        assert "GEMSDOE88-HYP-PSG-SUBMISSION" not in upper
        assert "GEMS88-HYP-PSG-SUBMISSION.TIF" not in upper
    assert not (ROOT / "docs/downloads/gems88-hyp-psg-submission.tif").exists()
    assert not (ROOT / "scripts/build_hypothesis_psg_submission.py").exists()
    assert not (ROOT / "mock_data.py").exists()
    check_site(ROOT)


def test_retired_mdc88_publisher_refuses_to_overwrite_the_current_site():
    page = ROOT / "docs/index.html"
    before = page.read_bytes()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/publish_kdmc_site.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "Refusing to publish the retired MDC-88 site" in result.stderr
    assert page.read_bytes() == before
