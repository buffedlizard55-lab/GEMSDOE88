"""The active negative review is bound to measurements, not past receipts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def test_negative_run_card_mirrors_and_current_measurements():
    rel = 'session_5a295887_run_card.json'
    raw = (ROOT / 'registry' / rel).read_bytes()
    assert raw == (ROOT / 'evidence' / rel).read_bytes() == (ROOT / 'docs/data' / rel).read_bytes()
    card = json.loads(raw)
    status = load('docs/status.json')
    assert status['current_review'] == f'data/{rel}'
    assert status['previous_review'] == 'data/session_92a5fb8c_run_card.json'
    assert card['status'] == 'DUPLICATE_STOP' and card['verdict'] == 'negative'
    assert card['ok_to_submit'] is card['approved_for_weekly_slot'] is False
    assert card['raster_file'] is card['raster_sha256'] is None and card['new_tif_generated'] is False
    assert card['holdout_dti']['dti'] is card['holdout_dti']['ci95'] is None
    assert card['leakage_canary']['max_auc'] is None
    assert card['registry_comparison']['surface_rank_correlation'] is None
    assert card['registry_comparison']['final_dot_overlap'] is None
    preflight = load(card['registry_comparison']['fresh_preflight_evidence'])
    assert preflight['decision'] == 'DUPLICATE_STOP' and preflight['generation_allowed'] is False
    proof = preflight['preplacement_registry_proof']
    assert proof == card['registry_comparison']['proof']
    assert proof['directly_covered_allowed_pixels'] == proof['allowed_pixels'] == 5_106_385
    assert proof['uncovered_allowed_pixels'] == 0 and proof['directly_saturated'] is True
    assert card['budget']['geological_experiments_run'] == card['budget']['weekly_slots_used'] == 0
    assert len(card['submission_note']) == card['submission_note_characters'] <= 140
    assert [r['id'] for r in card['ranked_conditional_hypotheses']] == ['H88-SPR', 'H88-AWA', 'H88-CBC']
    assert card['focus_readme_byte_sample']['counts']['DUPLICATE_STOP'] == 9
    assert card['focus_readme_byte_sample']['strict_format_fail_sites'] == ['GEMSDOE30']


def test_dated_sample_and_archived_file_bind_to_exact_bytes():
    card = load('registry/session_5a295887_run_card.json')
    sample = load(card['focus_readme_byte_sample']['evidence'])
    head_bytes = (ROOT / card['focus_revision_snapshot']['evidence']).read_bytes()
    assert sample['schema'] == 'gems88.focus-current-samples.v2'
    assert sample['head_snapshot_sha256'] == hashlib.sha256(head_bytes).hexdigest()
    rows = {r['site']: r for r in sample['rows']}
    assert rows['GEMSDOE28']['readme_bytes'] > 16_384 and rows['GEMSDOE28']['path']
    assert rows['GEMSDOE30']['format_pass'] is False
    assert {'all_finite', 'values_in_0_1'} <= set(rows['GEMSDOE30']['format_failures'])
    assert all(row['decision'] == 'DUPLICATE_STOP' and row['ok_to_submit'] is False for row in rows.values())
    archive = card['archived_research_download']
    fmt = load(archive['full_local_format_audit'])
    assert fmt['format_valid'] is True and fmt['submission_ready'] is False
    assert all(fmt['checks'].values()) and fmt['footprint_audit']['ok'] is True
    assert hashlib.sha256((ROOT / archive['download']).read_bytes()).hexdigest() == archive['sha256'] == fmt['sha256']
    assert archive['ok_to_submit'] is False


def test_active_browser_receipt_binds_current_site_and_failure_cases():
    card = load('registry/session_5a295887_run_card.json')
    receipt_path = Path(card['verification']['browser_evidence'])
    raw = (ROOT / receipt_path).read_bytes()
    assert raw == (ROOT / 'docs/data' / receipt_path.name).read_bytes()
    receipt = json.loads(raw)
    assert receipt['status'] == 'PASS' and receipt['ok_to_submit'] is False
    assert len(receipt['pages']) == 7 and all(p['pass'] and not p['overflow'] for p in receipt['pages'])
    sample = receipt['focus_current_samples']
    assert sample['row_count'] == 9
    for name in ('fresh_snapshot_pass', 'format_diagnostics_rendered', 'missing_feed_fail_closed',
                 'head_mismatch_fail_closed', 'snapshot_bytes_mismatch_fail_closed', 'expired_feed_fail_closed'):
        assert sample[name] is True, name
    assert receipt['research_download']['click_matches_canonical_bytes'] is True
    for rel, expected in receipt['source_sha256'].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected, rel
    assert (ROOT / 'research/session-5a295887-review.md').read_bytes() == (ROOT / 'docs/research/session-5a295887-review.md').read_bytes()


def test_public_guides_keep_format_and_submission_separate():
    for rel in ('docs/index.html', 'docs/executive-summary.html'):
        text = (ROOT / rel).read_text()
        assert 'complete README (up to 2,000,000 bytes)' in text
        assert 'not an organizer acceptance test' in text
        assert 'DO NOT SUBMIT' in text
        assert 'all portal checks PASS' not in text


def test_ci_separates_stored_structure_from_post_refresh_freshness():
    for rel in ('.github/workflows/pages.yml', '.github/workflows/ci.yml', '.github/workflows/checks.yml'):
        assert 'python scripts/focus_current_samples.py --check --structural-only' in (ROOT / rel).read_text()
    pages = (ROOT / '.github/workflows/pages.yml').read_text()
    refresh = pages.index('python scripts/focus_current_samples.py --refresh')
    assert pages.index('python scripts/focus_current_samples.py --check\n', refresh) > refresh
