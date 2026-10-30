"""Historical 60f326dc evidence remains intact beside the active successor."""
import hashlib
import json
from pathlib import Path

import pytest

from scripts import render_decision

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def test_current_run_card_is_single_negative_result_with_explicit_unknowns():
    paths = [ROOT / prefix / 'session_60f326dc_run_card.json'
             for prefix in ('registry', 'evidence', 'docs/data')]
    assert all(path.read_bytes() == paths[0].read_bytes() for path in paths)
    card = json.loads(paths[0].read_bytes())
    assert card['status'] == 'DUPLICATE_STOP' and card['verdict'] == 'negative'
    assert card['ok_to_submit'] is card['approved_for_weekly_slot'] is False
    assert card['new_tif_generated'] is False
    assert card['raster_file'] is card['raster_sha256'] is None
    assert card['holdout_dti']['dti'] is card['holdout_dti']['ci95'] is None
    assert card['leakage_canary']['max_auc'] is None
    assert card['registry_comparison']['surface_rank_correlation'] is None
    assert card['registry_comparison']['final_dot_overlap'] is None
    proof = card['registry_comparison']['proof']
    assert proof['directly_covered_allowed_pixels'] == proof['allowed_pixels'] == 5_106_385
    assert proof['directly_saturated'] and proof['universal_overlap_blocker']
    assert card['registry_comparison']['universal_overlap_for_nonempty_allowed_candidate'] == 1
    assert card['registry_comparison']['overlap_limit'] == .7
    assert card['budget']['geological_experiments_run'] == card['budget']['weekly_slots_used'] == 0
    assert len(card['submission_note']) == card['submission_note_characters'] <= 140
    assert card['organizer_confirmed_score'] is None
    status = read('docs/status.json')
    assert status['current_review'] == 'data/session_1cea5a72_run_card.json'
    assert status['previous_review'] == 'data/session_5aeeb70b_run_card.json'
    assert status['new_tif_generated'] is status['ok_to_submit'] is False


def test_sample_counts_are_pinned_and_not_called_a_portal_receipt():
    card = read('registry/session_60f326dc_run_card.json')
    sample = read(card['focus_readme_byte_sample']['evidence'])
    assert sample['schema'] == 'gems88.focus-current-samples.v2'
    assert card['focus_readme_byte_sample']['counts'] == sample['counts']
    assert sample['counts']['DUPLICATE_STOP'] == 8
    assert sample['counts']['NOT_DISCOVERED'] == 1
    row = next(row for row in sample['rows'] if row['site'] == 'GEMSDOE30')
    diagnosis = card['format_irregularity']
    assert diagnosis['sha256'] == row['sha256']
    assert diagnosis['pixel_counts'] == row['format_pixel_counts']
    counts = diagnosis['pixel_counts']
    assert counts['inside_nonfinite'] == 0 and counts['outside_nonfinite'] == 7_111_787
    assert counts['inside_finite_out_of_range'] == counts['outside_finite_out_of_range'] == 0
    assert 'strict.all_finite' in diagnosis['format_failures']
    assert diagnosis['cause_of_user_portal_error'].startswith('Unknown')
    assert diagnosis['organizer_nodata_acceptance'] == 'Unknown'
    assert row['format_pass'] is False and row['decision'] == 'DUPLICATE_STOP'
    # This is a historical snapshot; never compare it to the mutable current feed.
    historical_mirror = read('docs/data/focus_current_samples_60f326dc.json')
    assert sample == historical_mirror
    assert (ROOT / 'evidence/focus_current_samples_60f326dc.json').read_bytes() == (
        ROOT / 'docs/data/focus_current_samples_60f326dc.json').read_bytes()
    assert card['h33_geometry_crosscheck']['counts']['d28_minus_h33'] == 6436
    assert card['h33_geometry_crosscheck']['counts']['d28_minus_h33_over_2px'] == 0


def test_fresh_browser_receipt_binds_current_pages_and_v2_diagnostics():
    card = read('registry/session_60f326dc_run_card.json')
    path = Path(card['verification']['browser_evidence'])
    raw = (ROOT / path).read_bytes()
    assert raw == (ROOT / 'docs/data' / path.name).read_bytes()
    receipt = json.loads(raw)
    assert receipt['status'] == 'PASS' and receipt['ok_to_submit'] is False
    assert len(receipt['pages']) == 7 and all(p['pass'] and not p['overflow'] for p in receipt['pages'])
    assert receipt['failed_fetch_stays_negative'] and receipt['no_javascript_stays_negative']
    assert receipt['research_download']['click_matches_canonical_bytes']
    sample = receipt['focus_current_samples']
    assert sample['diagnostic_site'] == 'GEMSDOE30'
    assert sample['diagnostic_dom_pass'] and sample['tampered_diagnostic_fails_closed']
    # A historical browser receipt is immutable evidence for its old page set;
    # its source hashes are not expected to match today's mutable feed/pages.
    for path, expected in receipt['source_sha256'].items():
        assert path.startswith('docs/') and len(expected) == 64, path
        int(expected, 16)
    assert (ROOT / 'research/session-60f326dc-review.md').read_bytes() == (
        ROOT / 'docs/research/session-60f326dc-review.md').read_bytes()
    assert card['shared_repairs']['source_after_sha256'] == hashlib.sha256(
        (ROOT / card['shared_repairs']['file']).read_bytes()).hexdigest()


@pytest.fixture
def rendering_workspace(tmp_path):
    # Most immutable inputs are symlinked; mutable status and the active card
    # are copied so corruptions cannot change the real workspace.
    for name in ('registry', 'evidence'):
        (tmp_path / name).symlink_to(ROOT / name, target_is_directory=True)
    docs = tmp_path / 'docs'
    docs.mkdir()
    for entry in (ROOT / 'docs').iterdir():
        if entry.name == 'status.json':
            (docs / entry.name).write_bytes(entry.read_bytes())
        elif entry.name == 'data':
            data = docs / 'data'
            data.mkdir()
            for item in entry.iterdir():
                if item.name == 'session_1cea5a72_run_card.json':
                    (data / item.name).write_bytes(item.read_bytes())
                else:
                    (data / item.name).symlink_to(item, target_is_directory=item.is_dir())
        else:
            (docs / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    return tmp_path


@pytest.mark.parametrize('target,key,value', [
    ('status', 'current_review', '../registry/session_5aeeb70b_run_card.json'),
    ('status', 'previous_review', '../registry/session_32583983_run_card.json'),
    ('card', 'review_document', '../status.json'),
    ('card', 'verdict', 'promote'),
    ('card', 'ok_to_submit', True),
    ('card', 'new_tif_generated', True),
    ('card', 'created_at_utc', '2026-10-28'),
    ('card', 'created_at_utc', 'not an ISO time'),
])
def test_renderer_fails_closed_for_bad_current_or_previous_review(rendering_workspace, target, key, value):
    path = rendering_workspace / ('docs/status.json' if target == 'status'
                                   else 'docs/data/session_1cea5a72_run_card.json')
    data = json.loads(path.read_text())
    data[key] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        render_decision.read_inputs(rendering_workspace)
