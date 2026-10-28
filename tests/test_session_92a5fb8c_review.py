"""Preserve the historical negative review; bind current bytes to its successor."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_negative_card_mirrors_and_bindings():
    paths = [ROOT / f'{prefix}/session_92a5fb8c_run_card.json' for prefix in ('registry', 'evidence', 'docs/data')]
    raw = paths[0].read_bytes()
    assert all(path.read_bytes() == raw for path in paths)
    card = json.loads(raw)
    assert card['status'] == 'DUPLICATE_STOP' and card['verdict'] == 'negative'
    assert card['ok_to_submit'] is card['approved_for_weekly_slot'] is False
    assert card['new_tif_generated'] is False and card['raster_file'] is card['raster_sha256'] is None
    assert card['holdout_dti']['dti'] is card['holdout_dti']['ci95'] is None
    assert card['leakage_canary']['max_auc'] is None
    assert card['validator_output']['no_nan_inside_footprint'] is None
    proof = card['registry_comparison']['proof']
    assert proof['directly_covered_allowed_pixels'] == proof['allowed_pixels'] == 5106385
    assert proof['directly_saturated'] is proof['universal_overlap_blocker'] is True
    assert card['registry_comparison']['surface_rank_correlation'] is None
    assert card['registry_comparison']['final_dot_overlap'] is None
    assert len(card['submission_note']) == card['submission_note_characters'] <= 140
    assert card['budget']['geological_experiments_run'] == card['budget']['weekly_slots_used'] == 0
    assert card['focus_readme_byte_sample']['counts']['DUPLICATE_STOP'] == 8
    assert card['focus_readme_byte_sample']['counts']['NOT_DISCOVERED'] == 1
    status = json.loads((ROOT / 'docs/status.json').read_text())
    assert status['previous_review'] == 'data/session_92a5fb8c_run_card.json'
    assert status['ok_to_submit'] is status['approved_for_weekly_slot'] is False


def test_historical_browser_mirror_and_current_successor():
    card = json.loads((ROOT / 'registry/session_92a5fb8c_run_card.json').read_text())
    path = ROOT / card['verification']['browser_evidence']
    raw = path.read_bytes()
    assert raw == (ROOT / 'docs/data' / path.name).read_bytes()
    receipt = json.loads(raw)
    assert receipt['status'] == 'PASS' and receipt['ok_to_submit'] is False
    assert all(page['pass'] and not page['overflow'] for page in receipt['pages'])
    sample = receipt['focus_current_samples']
    assert sample['row_count'] == 9 and all(sample[key] is True for key in (
        'fresh_snapshot_pass', 'missing_feed_fail_closed', 'head_mismatch_fail_closed', 'expired_feed_fail_closed'))
    # Preserve the old receipt, checking its historical bytes if the baseline
    # commit is available (shallow CI checkouts may omit that commit).
    baseline = '866db73e8f3ac600baceb6e9e903225d835374f8'
    available = subprocess.run(['git', 'cat-file', '-e', baseline + '^{commit}'],
                               cwd=ROOT, capture_output=True).returncode == 0
    for rel, digest in receipt['source_sha256'].items():
        assert rel.startswith('docs/') and len(digest) == 64
        int(digest, 16)
        if available:
            prior = subprocess.run(['git', 'show', f'{baseline}:{rel}'], cwd=ROOT,
                                   check=True, capture_output=True).stdout
            assert hashlib.sha256(prior).hexdigest() == digest, rel
    status = json.loads((ROOT / 'docs/status.json').read_text())
    active_card = json.loads((ROOT / 'docs' / status['current_review']).read_text())
    active = json.loads((ROOT / active_card['verification']['browser_evidence']).read_text())
    assert active['status'] == 'PASS' and active['ok_to_submit'] is False
    assert set(receipt['source_sha256']) <= set(active['source_sha256'])
    for rel, digest in active['source_sha256'].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel
    assert (ROOT / 'research/session-92a5fb8c-review.md').read_bytes() == (ROOT / 'docs/research/session-92a5fb8c-review.md').read_bytes()
