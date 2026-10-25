"""Bind this negative review to actual evidence, without inventing a candidate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def test_published_session_card_is_an_identical_negative_record():
    card = read('registry/session_d0c3adeb_run_card.json')
    assert card == read('docs/data/session_d0c3adeb_run_card.json')
    assert card['decision'] == 'DUPLICATE_STOP'
    assert card['verdict'] == 'negative'
    assert card['promote'] is card['ok_to_submit'] is card['approved_for_weekly_slot'] is False
    assert card['new_rasters_generated'] == card['weekly_slots_used'] == card['budget']['experiments_run'] == 0
    assert card['portal_submissions'] == 0
    assert card['raster_file'] is card['raster_sha256'] is card['organizer_confirmed_score'] is None
    assert card['validator_output']['status'] == 'NOT_RUN_NO_NEW_RASTER'
    assert card['holdout']['status'] == 'NOT_RUN_DUPLICATE_STOP'
    assert card['holdout']['dti'] is card['holdout']['ci95'] is card['holdout']['withheld_positive_count'] is None
    assert card['validator_output']['finite_inside'] is None
    assert card['validator_output']['range_0_1'] is None
    assert all(card['validator_output'][k] is None for k in ('crs_match', 'shape_match', 'transform_match'))
    assert card['named_non_fault_mimic']
    assert len(card['submission_name']) == card['submission_name_length'] <= 140
    assert len(card['submission_note']) == card['submission_note_length'] <= 140
    assert 'audit identifier only' in card['submission_name_status']


def test_session_proof_is_not_mislabeled_as_candidate_measurement():
    card = read('registry/session_d0c3adeb_run_card.json')
    proof = read('registry/mtas88_run_card.json')['preplacement_registry_proof']
    assert card['preplacement_registry_proof'] == proof
    registry = card['correlation_overlap_vs_registry']
    assert registry['witness_sha256'] == proof['witness_sha256']
    assert registry['universal_nonempty_allowed_forward_overlap_lower_bound'] == 1.0
    assert registry['candidate_measurement_performed'] is False
    assert registry['surface_spearman'] is registry['candidate_final_overlap_3px'] is None
    assert proof['uncovered_allowed_pixels'] == 0


def test_existing_downloads_are_not_passed_off_as_new_rasters():
    card = read('registry/session_d0c3adeb_run_card.json')
    old = card['archived_research_download']
    current = read('docs/data/current_release.json')
    audit = read('docs/data/download_audit.json')
    assert old['new_this_session'] is False
    assert old['file'] == current['file']
    assert old['sha256'] == current['file_sha256'] == audit['canonical_sha256']
    assert old['zip_sha256'] == current['zip_sha256']
    # Historical counts are frozen; new concurrent research does not rewrite them.
    assert old['tiff_zip_pairs'] == old['local_research_passes'] == 43
    assert audit['tiff_count'] == audit['research_download_pass_count'] >= 43
    assert old['protocol_eligible_count'] == 0
    assert card['ok_to_download_new_file'] is False
    assert old['ok_to_download_for_research'] is True
    assert old['ok_to_submit'] is False


def test_recorded_guard_inventory_matches_the_code():
    card = read('registry/session_d0c3adeb_run_card.json')
    actual = sorted(p.name for p in (ROOT / 'scripts').glob('*.py')
                    if p.name != 'generation_guard.py' and 'enforce_generation_preflight()' in p.read_text())
    # Preserve the historical snapshot; later guarded CLIs may be added,
    # but none of the previously guarded entrypoints may lose protection.
    recorded = card['generation_guard']['entrypoints']
    assert set(recorded) <= set(actual)
    assert card['generation_guard']['count'] == len(recorded) == 89
    assert 'run_mfs88_experiment.py' in actual
    assert card['generation_guard']['shared_evaluator_writer_changed'] is False
    assert card['generation_guard']['cli_entrypoints_only_not_a_security_sandbox'] is True


def test_unmet_requirements_and_source_limits_stay_explicit():
    card = read('registry/session_d0c3adeb_run_card.json')
    assert card['acceptance']['unique_new_competition_tiff'] == 'UNMET_BINDING_DUPLICATE_STOP'
    assert card['acceptance']['new_top_candidate_holdout'] == 'NOT_RUN_BINDING_DUPLICATE_STOP'
    assert card['acceptance']['improvement_beyond_h33'] == 'NOT_ESTABLISHED'
    assert card['source_scope']['all_92_sites_freshly_scraped'] is False
    assert card['source_scope']['portal_quota_verified'] is False
    assert card['source_scope']['organizer_receipt_available'] is False
    assert card['software_review']['passes'][2]['all_requested_deliverables_met'] is False
    assert [p['pass'] for p in card['software_review']['passes']] == [1, 2, 3]
    assert card['software_review']['three_passes_completed'] is True
    assert all(p['status'] == 'PASS' for p in card['software_review']['passes'])
    appendix = (ROOT / card['software_review']['completion_appendix']).read_text()
    assert 'UNMET' in appendix
    assert appendix == (ROOT / 'docs/research/session-d0c3adeb-completion.md').read_text()


def test_historical_browser_receipt_remains_a_dated_negative_record():
    card = read('registry/session_d0c3adeb_run_card.json')
    record = read(card['software_review']['browser_evidence'])
    assert record['status'] == 'PASS'
    assert record['ok_to_submit'] is False
    assert record['failed_fetch_stays_negative'] is True
    assert len(record['pages']) == 5
    assert {p['width'] for p in record['pages']} == {390, 1440}
    for page in record['pages']:
        assert page['pass'] and not page['overflow'] and not page['errors']
        assert page['h1'] == 1 and page['openArchives'] == 0
    # This immutable historical receipt describes the earlier published bytes.
    # Later UI corrections must have their own fresh browser receipt, rather
    # than rewriting this measurement or representing it as current evidence.
    for relative, digest in record['source_sha256'].items():
        assert relative.startswith('docs/') and len(digest) == 64
        int(digest, 16)
    current_card = read('registry/session_b4dfa10c_run_card.json')
    current = read(current_card['software_review']['browser_evidence'])
    assert current['status'] == 'PASS' and current['ok_to_submit'] is False
    assert record['checked_at_utc'] < current['checked_at_utc']
    assert current['failed_fetch_stays_negative'] is True
    assert {p['width'] for p in current['pages']} == {390, 1440}
    assert len(current['pages']) == 7 and all(p['pass'] for p in current['pages'])
    assert set(record['source_sha256']) <= set(current['source_sha256'])
    for relative, digest in current['source_sha256'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
