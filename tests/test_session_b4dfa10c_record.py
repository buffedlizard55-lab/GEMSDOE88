"""This review's software progress must not masquerade as a new scored raster."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def test_session_card_is_one_mirrored_negative_record():
    card = read('registry/session_b4dfa10c_run_card.json')
    assert card == read('docs/data/session_b4dfa10c_run_card.json') == read('evidence/session_b4dfa10c_run_card.json')
    assert card['base_commit'] == 'dcd60754749e1e5d88d535c0973245c889f8c15f'
    assert card['branch'] == 'arena/b4dfa10c-gemsdoe88'
    assert card['status'] == 'DUPLICATE_STOP' and card['verdict'] == 'negative'
    assert card['raster_file'] is card['raster_sha256'] is card['organizer_confirmed_score'] is None
    assert card['holdout_dti']['dti'] is card['holdout_dti']['ci95'] is None
    assert card['holdout_dti']['withheld_positive_pixels'] is None
    assert card['single_feature_canaries']['auc'] is None
    assert card['validator_output']['status'] == 'NOT_RUN_NO_NEW_RASTER'
    assert card['budget']['geological_experiments_run'] == card['budget']['new_candidate_tiffs'] == card['weekly_slots_used'] == 0
    assert card['ok_to_download_new_file'] is card['ok_to_submit'] is card['approved_for_weekly_slot'] is False
    assert 0 < len(card['submission_note']) == card['submission_note_characters'] <= 140


def test_session_audit_counts_main_and_variant_without_rewriting_history():
    card = read('registry/session_b4dfa10c_run_card.json')
    inventory = card['download_inventory']
    audit = read(inventory['historical_snapshot'])
    current = read('docs/data/download_audit.json')
    assert current['total_published_tiff_count'] >= inventory['total_published_tiff_count']
    assert current['protocol_eligible_count'] == 0
    assert inventory['schema'] == 'gems88.download-audit.v2'
    assert inventory['tiff_count'] == inventory['research_download_pass_count'] == 45
    assert inventory['additional_research_tiff_count'] == 1
    assert inventory['total_published_tiff_count'] == inventory['total_research_download_pass_count'] == 46
    assert inventory['protocol_eligible_count'] == 0
    for key in ('tiff_count', 'additional_research_tiff_count', 'total_published_tiff_count', 'exact_decoded_duplicate_groups'):
        assert inventory[key] == audit[key]
    assert inventory['saved_audit_sha256'] == hashlib.sha256((ROOT / inventory['historical_snapshot']).read_bytes()).hexdigest()
    assert (ROOT / inventory['historical_snapshot']).read_bytes() == (ROOT / 'docs/data/download_audit_b4dfa10c_snapshot.json').read_bytes()
    archive = card['archived_research_download']
    assert hashlib.sha256((ROOT / archive['download']).read_bytes()).hexdigest() == archive['sha256']
    assert archive['ok_to_download_for_research_only'] is True and archive['ok_to_submit'] is False
    assert archive['fresh_local_format_audit']['validator'] == 'gems88-format-audit-v2'
    assert archive['fresh_local_format_audit']['format_valid'] is True
    assert archive['fresh_local_format_audit']['submission_ready'] is False


def test_scope_and_unmet_scientific_requirements_remain_explicit():
    card = read('registry/session_b4dfa10c_run_card.json')
    assert card['acceptance']['unique_new_competition_tiff'] == 'UNMET_BINDING_DUPLICATE_STOP'
    assert card['acceptance']['new_top_candidate_holdout'] == 'NOT_RUN_BINDING_DUPLICATE_STOP'
    assert card['acceptance']['improvement_beyond_h33'] == 'NOT_ESTABLISHED'
    assert card['source_scope']['all_92_sites_freshly_scraped'] is False
    assert card['live_organizer_access']['receipt'] is None
    assert card['live_organizer_access']['leaderboard_verified_this_session'] is False
    assert card['live_organizer_access']['weekly_quota_verified'] is False
    assert card['h33_claim']['evidence_class'] == 'USER-REPORTED_NOT_ORGANIZER-CONFIRMED'
    assert card['h33_claim']['causal_score_improvement_established'] is False
    assert card['h33_claim']['owner_projection_is_not_a_score'] is True
    for stem in ('review', 'hypotheses'):
        relative = f'research/session-b4dfa10c-{stem}.md'
        assert (ROOT / relative).read_text() == (ROOT / 'docs' / relative).read_text()
        assert relative in (ROOT / 'README.md').read_text()
    software = card['software_review']
    assert [entry['pass'] for entry in software['passes']] == [1, 2, 3]
    if software['final_verification_status'] == 'PASS':
        assert software['three_passes_completed'] is True
        assert all(entry['status'] == 'PASS' for entry in software['passes'])
        assert software['final_pytest']['passed'] >= 727
        assert all(entry['pass'] for entry in software['final_gates']['checks'])
    else:
        assert software['final_verification_status'] == 'PENDING_POST_INTEGRATION_RECHECK'
        assert software['three_passes_completed'] is False
