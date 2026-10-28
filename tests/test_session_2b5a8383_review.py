"""The current negative card, sampled evidence and fresh browser receipt agree."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def test_negative_session_card_is_mirrored_and_distinguishes_no_candidate():
    paths = ['registry/session_2b5a8383_run_card.json',
             'evidence/session_2b5a8383_run_card.json',
             'docs/data/session_2b5a8383_run_card.json']
    assert len({(ROOT / path).read_bytes() for path in paths}) == 1
    card = read(paths[0])
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert card['approved_for_weekly_slot'] is False
    assert card['new_tif_generated'] is False and card['raster_sha256'] is None
    assert card['holdout_dti']['dti'] is None and card['holdout_dti']['ci95'] is None
    assert card['leakage_canary']['max_auc'] is None
    assert card['registry_comparison']['surface_rank_correlation'] is None
    assert card['registry_comparison']['final_dot_overlap'] is None
    assert card['registry_comparison']['proof_of_any_nonempty_allowed_dot_overlap'] == 1.0
    assert card['registry_comparison']['proof']['directly_covered_allowed_pixels'] == 5106385
    assert card['validator_output']['status'] == 'NOT_RUN_NO_NEW_RASTER'
    assert card['budget']['geological_experiments_run'] == 0
    assert card['budget']['weekly_slots_used'] == 0
    assert card['verification']['full_suite'] == card['verification']['full_pytest_status'] == 'PASS'
    assert '971 passed, 23 skipped' in card['verification']['full_pytest']
    assert 'PENDING' not in json.dumps(card['verification'])
    assert 0 < len(card['submission_note']) == card['submission_note_characters'] <= 140
    assert [p['id'] for p in card['conditional_ranked_hypotheses']] == ['H88-SPR', 'H88-AWA', 'H88-CBC']
    archive = card['archived_research_download']
    assert archive['new_in_this_session'] is False and archive['ok_to_submit'] is False
    assert archive['local_format_audit']['validator'] == 'gems88-format-audit-v3'
    assert archive['local_format_audit']['checks']['dtype_float32'] is True
    assert archive['local_format_audit']['submission_ready'] is False
    assert hashlib.sha256((ROOT / archive['file']).read_bytes()).hexdigest() == archive['sha256']
    counts = card['h33_geometry_crosscheck']['counts']
    assert (counts['d28_minus_h33'], counts['d28_minus_solo'], counts['solo_minus_h33']) == (6436, 3891, 2545)
    assert counts['d28_minus_h33_over_2px'] == 0
    assert card['focus_sites']['samples_duplicate_stopped'] == 9
    assert card['focus_sites']['siblings_claiming_submit_ready_at_pinned_heads'] == ['GEMSDOE27', 'GEMSDOE31']


def test_real_browser_receipt_is_fresh_and_every_feed_failure_remains_negative():
    hist_br = read('evidence/session_2b5a8383_browser_check.json')
    assert hist_br == read('docs/data/session_2b5a8383_browser_check.json')
    assert hist_br['status'] == 'PASS' and hist_br['ok_to_submit'] is False

    status = read('docs/status.json')
    assert status['current_review'] == 'data/session_a1612614_run_card.json'
    assert status['previous_review'] == 'data/session_60f326dc_run_card.json'
    card = read('docs/' + status['current_review'])
    evidence = Path(card['verification']['browser_evidence'])
    assert (ROOT / evidence).read_bytes() == (ROOT / 'docs/data' / evidence.name).read_bytes()
    report = read(evidence)
    assert report['status'] == 'PASS' and report['ok_to_submit'] is False
    assert len(report['pages']) == 7 and all(p['pass'] for p in report['pages'])
    assert report['failed_fetch_stays_negative'] is True
    assert report['no_javascript_stays_negative'] is True
    focus = report['focus_freshness']
    assert focus['fresh_snapshot_pass'] and focus['missing_feed_fail_closed']
    assert focus['partial_feed_fail_closed'] and focus['expired_feed_fail_closed']
    assert set(hist_br['source_sha256']) <= set(report['source_sha256'])
    for path, digest in report['source_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    assert 'docs/assets/focus-freshness.js' in report['source_sha256']


def test_workflow_and_pages_keep_the_sample_and_freshness_scope_clear():
    workflow = (ROOT / '.github/workflows/pages.yml').read_text()
    assert "cron: '17 */6 * * *'" in workflow
    assert 'python scripts/focus_freshness.py --refresh' in workflow
    assert 'python -O scripts/audit_focus_sample_20261026.py --check' in workflow
    historical = read('docs/data/focus_sites_20261026.json')['focus_sites']
    review = (ROOT / 'research/session-2b5a8383-review.md').read_text()
    assert review == (ROOT / 'docs/research/session-2b5a8383-review.md').read_text()
    for file in ('docs/index.html', 'docs/executive-summary.html'):
        html = (ROOT / file).read_text()
        assert 'assets/focus-freshness.js' in html
        assert 'nine-file sample, not a complete fleet audit' in html
        assert 'data/focus_sample_2b5a8383.json' in html
        assert 'NO NEW TIFF: DUPLICATE — STOP' in html
        for row in historical:
            name = row['highest_scoring_submission']['cache_filename'].split('__', 1)[1]
            url = f'{row["repo_url"]}/blob/{row["inspected_repo_head_sha"]}/docs/downloads/{name}'
            assert url in html and url in review
