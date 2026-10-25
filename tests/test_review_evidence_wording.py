"""Public research records must not imply portal validation or fake uncertainty."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_archived_estimate_has_no_placeholder_confidence_interval():
    for name in ('index.html', 'executive-summary.html'):
        text = (ROOT / 'docs' / name).read_text()
        assert 'HOLDOUT-DTI 0.056081 [0.0, 0.0]' not in text
        assert '95% CI unavailable' in text
        assert 'review-20261025-recheck.md' in text


def test_local_check_does_not_claim_live_portal_status():
    text = (ROOT / 'docs/index.html').read_text()
    assert 'Live Portal Status:' not in text
    assert 'Archived local artifact status (not portal-verified):' in text
    assert 'LZW deflate' not in text


def test_historical_lane_does_not_override_current_stop():
    text = (ROOT / 'PROMPT.md').read_text()
    assert 'Current precedence note (2026-10-25, H88-GZZC)' not in text
    assert 'Historical parallel-lane record' in text
    assert 'obey the literal duplicate stop before constructing any new candidate' in text
