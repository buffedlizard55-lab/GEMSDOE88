"""The follow-up must not turn a stopped audit into a new submission."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_new_card_is_identical_fail_closed_and_has_no_invented_measurements():
    raw = (ROOT / 'registry/session_26588c79_run_card.json').read_bytes()
    assert raw == (ROOT / 'docs/data/session_26588c79_run_card.json').read_bytes()
    card = json.loads(raw)
    assert card['decision'] == 'DUPLICATE_STOP'
    assert card['verdict'] == 'negative'
    assert card['ok_to_submit'] is card['approved_for_weekly_slot'] is False
    assert card['raster_sha256'] is card['raster_file'] is card['organizer_confirmed_score'] is None
    assert card['holdout']['dti'] is card['holdout']['ci95'] is None
    assert card['holdout']['withheld_positive_count'] is None
    assert card['canary']['auc'] is None
    assert card['new_rasters_generated'] == card['budget']['experiments_run'] == card['weekly_slots_used'] == card['portal_submissions'] == 0
    assert 0 < len(card['submission_note']) <= 140
    assert card['validator_output']['status'] == 'NOT_RUN_NO_NEW_RASTER'
    proof = card['preplacement_registry_proof']
    assert proof == json.loads((ROOT / 'registry/mtas88_run_card.json').read_text())['preplacement_registry_proof']
    assert proof['universal_overlap_blocker'] is True
    assert card['correlation_overlap_vs_registry']['surface_spearman'] is None
    old = card['archived_research_download']
    assert old['new_this_session'] is old['ok_to_submit'] is False
    assert hashlib.sha256((ROOT / old['file']).read_bytes()).hexdigest() == old['sha256']
    assert old['validator_output']['ok'] is True


def test_review_is_accessible_and_explicit_about_unmet_goals():
    text = (ROOT / 'research/session-26588c79-review.md').read_text()
    assert text == (ROOT / 'docs/research/session-26588c79-review.md').read_text()
    assert 'UNMET' in text and 'No new TIFF was generated' in text
    assert 'not four newly executed experiments' in text
    assert 'not an ORGANIZER-CONFIRMED score' in text
    assert 'session-26588c79-review.md' in (ROOT / 'README.md').read_text()
