"""Regression tests for research-score provenance and fail-closed rendering."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_executive_metrics as audit  # noqa: E402
from scripts import render_decision  # noqa: E402


def test_each_displayed_metric_is_the_named_evidence_arm_and_has_its_own_n_and_ci():
    rows = audit.inspect(ROOT)
    assert rows['BPWD']['blind_gt25px']['dti'] == pytest.approx(0.07273260752166534)
    assert rows['BPWD']['blind_gt25px']['withheld_positive_pixels'] == 3117
    assert rows['BPWD']['blind_gt25px']['ci95'] == pytest.approx([0.045431941846986866, 0.10312672176862667])
    assert rows['BPWD']['overall']['withheld_positive_pixels'] == 22893
    assert rows['QTS']['experiment'] == 'exp3_qts_hybrid_debiased'
    assert rows['QTS']['overall']['dti'] == pytest.approx(0.094850566455273)
    assert rows['QTS']['holdout_evidence'] is None

    current = json.loads((ROOT / 'docs/data/current_release.json').read_text())
    table = render_decision.submission_summary_table(ROOT, str(Path(current['file']).relative_to('docs')))
    for lane, row in rows.items():
        fragment = table.split(f'data-executive-lane="{lane}"', 1)[1].split('</tr>', 1)[0]
        assert row['research_tiff'].removeprefix('docs/') in fragment
        assert render_decision.format_holdout(row['overall']) in fragment
        if row['blind_gt25px'] is not None:
            assert render_decision.format_holdout(row['blind_gt25px']) in fragment
        assert 'SUBMIT: NO — DO NOT SUBMIT' in fragment
    bpwd_row = table.split('data-executive-lane="BPWD"', 1)[1].split('</tr>', 1)[0]
    qts_row = table.split('data-executive-lane="QTS"', 1)[1].split('</tr>', 1)[0]
    assert '0.090449' not in bpwd_row
    assert '0.6698' not in bpwd_row
    assert '0.098210' not in qts_row
    assert '0.094851' in qts_row and 'Exp3' in qts_row
    assert 'not a score of the downloaded TIFF' in table
    assert 'not a complete raster census' in table


def fixture_for_one_lane(tmp_path, monkeypatch, lane='BPWD'):
    source = audit.SOURCES[lane]
    monkeypatch.setattr(audit, 'SOURCES', {lane: source})
    card_rel, raster_keys, evidence_rel, *_ = source
    card = json.loads((ROOT / card_rel).read_text())
    paths = [Path(card_rel), Path('docs/data') / Path(card_rel).name, Path(audit.get_path(card, raster_keys))]
    if evidence_rel:
        paths += [Path(evidence_rel), Path('docs/evidence') / Path(evidence_rel).name]
    for path in paths:
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, dest)
    return source, card


def rewrite_card_and_mirror(root, relative, card):
    payload = json.dumps(card, indent=2) + '\n'
    (root / relative).write_text(payload)
    (root / 'docs/data' / Path(relative).name).write_text(payload)


@pytest.mark.parametrize('mutation', ['wrong_blind_arm', 'wrong_ci', 'invalid_n', 'wrong_evaluator',
                                       'false_approval', 'bad_hash', 'missing_mirror', 'bad_evidence'])
def test_inconsistent_metric_identity_or_approval_cannot_render(tmp_path, monkeypatch, mutation):
    source, card = fixture_for_one_lane(tmp_path, monkeypatch)
    card_rel, _raster_keys, evidence_rel, *_ = source
    if mutation == 'wrong_blind_arm':
        card['holdout_dti']['blind_gt25px']['dti'] = 0.09044884156382559
    elif mutation == 'wrong_ci':
        card['holdout_dti']['blind_gt25px']['ci95'] = [0.9, 0.1]
    elif mutation == 'invalid_n':
        card['holdout_dti']['blind_gt25px']['withheld_positive_pixels'] = True
    elif mutation == 'wrong_evaluator':
        card['holdout_dti']['candidate_exp03']['evaluator_version'] = 'invented'
    elif mutation == 'false_approval':
        card['ok_to_submit'] = True
    elif mutation == 'bad_hash':
        card['raster_sha256'] = '0' * 64
    elif mutation == 'missing_mirror':
        (tmp_path / 'docs/data' / Path(card_rel).name).unlink()
    elif mutation == 'bad_evidence':
        evidence = tmp_path / evidence_rel
        data = json.loads(evidence.read_text())
        data['pooled_blind_gt25px']['scores']['exp03_psgv_tri_poe']['ci95'][0] = 0.02
        payload = json.dumps(data, indent=2) + '\n'
        evidence.write_text(payload)
        (tmp_path / 'docs/evidence' / evidence.name).write_text(payload)
    if mutation != 'missing_mirror':
        rewrite_card_and_mirror(tmp_path, card_rel, card)
    with pytest.raises((OSError, KeyError, TypeError, ValueError)):
        audit.inspect(tmp_path)


@pytest.mark.parametrize('change', ['nan', 'inf', 'negative', 'bad_ci', 'empty_n', 'boolean'])
def test_metric_values_require_valid_labeled_finite_evidence(change):
    metric = copy.deepcopy(audit.inspect(ROOT)['BPWD']['overall'])
    if change == 'nan': metric['dti'] = float('nan')
    if change == 'inf': metric['ci95'][0] = float('inf')
    if change == 'negative': metric['dti'] = -0.1
    if change == 'bad_ci': metric['ci95'] = [0.2, 0.1]
    if change == 'empty_n': metric['withheld_positive_pixels'] = 0
    if change == 'boolean': metric['dti'] = True
    with pytest.raises(ValueError):
        audit.checked_metric(metric)


def test_optimized_python_runs_the_same_metric_audit():
    result = subprocess.run([sys.executable, '-O', 'scripts/audit_executive_metrics.py'],
                            cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['status'] == 'PASS' and report['ok_to_submit'] is False
    assert report['metrics']['QTS']['experiment'] == 'exp3_qts_hybrid_debiased'


def test_sources_do_not_claim_the_local_check_established_portal_rejection():
    index = (ROOT / 'docs/index.html').read_text()
    guide = (ROOT / 'docs/executive-summary.html').read_text()
    root = (ROOT / 'index.html').read_text()
    assert 'old <code>nan</code>-outside files fail the portal' not in index
    assert 'which the portal strict check' not in guide
    assert 'weekly allowance unknown' in root
    assert 'Weekly competition slots used: <strong>0 / 3</strong>' not in root


def test_qts_does_not_silently_fall_back_to_exp2(tmp_path, monkeypatch):
    source, card = fixture_for_one_lane(tmp_path, monkeypatch, 'QTS')
    del card['holdout']['experiments']['exp3_qts_hybrid_debiased']
    rewrite_card_and_mirror(tmp_path, source[0], card)
    with pytest.raises(KeyError):
        audit.inspect(tmp_path)


@pytest.mark.parametrize('mutation', ['substituted_raster', 'divergent_card_mirror', 'divergent_evidence_mirror', 'unsafe_path'])
def test_substitution_divergence_and_path_escape_are_rejected(tmp_path, monkeypatch, mutation):
    source, card = fixture_for_one_lane(tmp_path, monkeypatch)
    card_rel, raster_keys, evidence_rel, *_ = source
    if mutation == 'substituted_raster':
        target = tmp_path / audit.get_path(card, raster_keys)
        with target.open('ab') as f:
            f.write(b'not the archived bytes')
    elif mutation == 'divergent_card_mirror':
        (tmp_path / 'docs/data' / Path(card_rel).name).write_text('{}\n')
    elif mutation == 'divergent_evidence_mirror':
        (tmp_path / 'docs/evidence' / Path(evidence_rel).name).write_text('{}\n')
    else:
        card['download'] = '../DO-NOT-SUBMIT.tif'
        rewrite_card_and_mirror(tmp_path, card_rel, card)
    with pytest.raises((OSError, KeyError, TypeError, ValueError)):
        audit.inspect(tmp_path)


def test_current_review_public_mirror_matches_source_and_uses_working_local_links():
    import re
    source = (ROOT / 'research/session-92002f70-review.md').read_text()
    public = (ROOT / 'docs/research/session-92002f70-review.md').read_text()
    conversions = {
        '../evidence/focus_sites_20261026_audit.json': '../data/focus_sites_20261026.json',
        '../evidence/focus_sample_2b5a8383.json': '../data/focus_sample_2b5a8383.json',
        '../docs/evidence/GEMSDOE32__registry__submission_build.json': '../evidence/GEMSDOE32__registry__submission_build.json',
        '../registry/bpwd88_run_card.json': '../data/bpwd88_run_card.json',
        '../registry/qts88_run_card.json': '../data/qts88_run_card.json',
        '../registry/hypothesis_queue.json': '../data/hypothesis_queue.json',
        '../scripts/run_qts88_experiment.py': 'https://github.com/buffedlizard55-lab/GEMSDOE88/blob/a9f928241cf690dfc3d4c4ee7b05e6d166605ebd/scripts/run_qts88_experiment.py',
    }
    for old, new in conversions.items():
        source = source.replace('](' + old + ')', '](' + new + ')')
    assert public == source
    for target in re.findall(r'\]\(([^)]+)\)', public):
        if not target.startswith(('https://', 'http://', '#')):
            assert (ROOT / 'docs/research' / target).is_file(), target


def test_current_run_card_and_fresh_browser_receipt_match_their_mirrors_and_bytes():
    import hashlib
    card_bytes = (ROOT / 'registry/session_92002f70_run_card.json').read_bytes()
    assert card_bytes == (ROOT / 'evidence/session_92002f70_run_card.json').read_bytes()
    assert card_bytes == (ROOT / 'docs/data/session_92002f70_run_card.json').read_bytes()
    card = json.loads(card_bytes)
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert card['new_tif_generated'] is False and card['raster_sha256'] is None
    assert card['holdout_dti']['dti'] is None and card['leakage_canary']['max_auc'] is None
    assert card['registry_comparison']['final_dot_overlap'] is None
    proof = card['registry_comparison']['proof']
    assert proof['directly_covered_allowed_pixels'] == proof['allowed_pixels'] == 5106385
    assert proof['covered_allowed_fraction'] == 1.0 and proof['overlap_limit'] == 0.7
    assert len(card['submission_note']) == card['submission_note_characters'] <= 140
    status = json.loads((ROOT / 'docs/status.json').read_text())
    assert status['current_review'] == 'data/session_a1612614_run_card.json'
    assert status['previous_review'] == 'data/session_60f326dc_run_card.json'
    receipt_path = Path(card['verification']['browser_evidence'])
    receipt_bytes = (ROOT / receipt_path).read_bytes()
    assert receipt_bytes == (ROOT / 'docs/data' / receipt_path.name).read_bytes()
    receipt = json.loads(receipt_bytes)
    assert receipt['status'] == 'PASS' and receipt['ok_to_submit'] is False
    assert receipt['focus_comparison']['pass'] is True
    assert receipt['research_download']['click_matches_canonical_bytes'] is True
    assert receipt['research_download']['click_sha256'] == card['archived_research_download']['sha256']
    # This receipt describes the prior pages, not the current mutable files.
    # The active review has a separate fresh receipt binding today's bytes.
    for rel, expected in receipt['source_sha256'].items():
        assert rel.startswith('docs/') and len(expected) == 64
        int(expected, 16)
    active = json.loads((ROOT / 'docs' / status['current_review']).read_text())
    fresh = json.loads((ROOT / active['verification']['browser_evidence']).read_text())
    assert fresh['status'] == 'PASS' and set(receipt['source_sha256']) <= set(fresh['source_sha256'])
    for rel, expected in fresh['source_sha256'].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected, rel


@pytest.mark.parametrize('optimized', [False, True])
@pytest.mark.parametrize('corruption,expected', [
    ('stale-date', 'Overview must present the current fail-closed decision'),
    ('escaped-review', 'Current review must point to a public data card'),
])
def test_site_guard_rejects_stale_review_or_unsafe_review_path(tmp_path, optimized, corruption, expected):
    (tmp_path / 'registry').symlink_to(ROOT / 'registry', target_is_directory=True)
    (tmp_path / 'evidence').symlink_to(ROOT / 'evidence', target_is_directory=True)
    docs = tmp_path / 'docs'
    docs.mkdir()
    for source in (ROOT / 'docs').iterdir():
        if source.name == 'index.html' and corruption == 'stale-date':
            original = source.read_text()
            card = json.loads((ROOT / 'docs' / json.loads((ROOT / 'docs/status.json').read_text())['current_review']).read_text())
            review_date = card['created_at_utc'][:10]
            changed = original.replace('Review · ' + review_date, 'Review · 1900-01-01')
            assert changed != original
            (docs / source.name).write_text(changed)
        elif source.name == 'status.json' and corruption == 'escaped-review':
            status = json.loads(source.read_text())
            status['current_review'] = '../registry/session_92002f70_run_card.json'
            (docs / source.name).write_text(json.dumps(status))
        elif source.name in {'downloads', 'research-variants'}:
            shutil.copytree(source, docs / source.name)
        else:
            (docs / source.name).symlink_to(source, target_is_directory=source.is_dir())
    command = [sys.executable] + (['-O'] if optimized else []) + [
        '-c', 'from pathlib import Path; from scripts.check_site import main; import sys; main(Path(sys.argv[1]))',
        str(tmp_path)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert expected in result.stderr


def test_gemsdoe27_overlap_correction_is_bound_to_counts_and_machine_audit():
    card = json.loads((ROOT / 'registry/session_92002f70_run_card.json').read_text())
    corrected = card['corrections']['gemsdoe27_h19_forward_overlap']
    audit_data = json.loads((ROOT / 'evidence/focus_sites_20261026_audit.json').read_text())
    site = next(row for row in audit_data['focus_sites'] if row['site'] == 'GEMSDOE27')
    champ = site['highest_scoring_submission']
    assert corrected['champion_sha256'] == champ['sha256']
    assert corrected['candidate_positive_pixels'] == champ['positive_pixels'] == 61328
    assert corrected['matched_positive_pixels'] == 60141
    assert corrected['measured_fraction'] == pytest.approx(60141 / 61328)
    assert round(corrected['measured_fraction'], 6) == champ['vs_gemsdoe88_registry']['gems19_h19_5_3px_forward_overlap']
    assert corrected['rounded_4dp'] == round(corrected['measured_fraction'], 4) == 0.9806
    line = next(line for line in (ROOT / 'README.md').read_text().splitlines() if line.startswith('| **[GEMSDOE27]'))
    assert '`0.9806` / `1.0000`' in line and '0.9854' not in line
