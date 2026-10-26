"""The pinned nine-file sample is evidence, not a live or exhaustive clearance."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_focus_sample_20261026 as audit  # noqa: E402


@pytest.fixture
def report():
    return json.loads((ROOT / audit.EVIDENCE).read_text())


def test_nine_immutable_samples_are_mirrored_and_fail_the_literal_gate(report):
    assert (ROOT / audit.EVIDENCE).read_bytes() == (ROOT / audit.PUBLIC).read_bytes()
    audit.check(report)
    assert len(report['rows']) == 9
    for row in report['rows']:
        assert row['positive_pixels'] > 0
        assert row['positive_on_witness_fraction'] == 1.0
        assert row['positive_within_3px_witness_fraction'] == 1.0
        assert row['decision'] == 'DUPLICATE_STOP'
        assert row['ok_to_submit'] is False
        assert row['surface_spearman'] is None
        assert row['organizer_receipt'] is None
    assert [r['site'] for r in report['rows'] if r['sibling_readme_claims_ok_to_submit']] == ['GEMSDOE27', 'GEMSDOE31']


def test_local_format_caveat_does_not_call_nan_exterior_portal_invalid(report):
    rows = {r['site']: r for r in report['rows']}
    assert sum(row['strict_local_format_and_footprint_pass'] for row in rows.values()) == 8
    gdx = rows['GEMSDOE30']
    assert gdx['inside_footprint_finite_in_range'] is True
    assert gdx['strict_local_format_and_footprint_pass'] is False
    assert gdx['strict_format_checks']['all_finite'] is False
    assert 'Portal acceptance is not established' in report['format_caveat']


def test_unsafe_or_inconsistent_sample_reports_are_rejected(report):
    updates = [
        lambda x: x.update(ok_to_submit=True),
        lambda x: x.update(approved_for_weekly_slot=True),
        lambda x: x.update(weekly_slots_selected=1),
        lambda x: x['rows'].pop(),
        lambda x: x['rows'][0].update(head='f' * 40),
        lambda x: x['rows'][0].update(source_url='https://example.com/file'),
        lambda x: x['rows'][0].update(ok_to_submit=True),
        lambda x: x['rows'][0].update(organizer_receipt='invented'),
        lambda x: x['rows'][0].update(surface_spearman=0.2),
        lambda x: x['rows'][0].update(positive_within_3px_witness_fraction=0.2),
        lambda x: x['rows'][0].update(positive_on_witness_fraction=1.1),
        lambda x: x['rows'][0].update(decision='promote'),
        lambda x: x['rows'][0].update(strict_local_format_and_footprint_pass=True, inside_footprint_finite_in_range=False),
    ]
    for update in updates:
        bad = copy.deepcopy(report)
        update(bad)
        with pytest.raises(ValueError):
            audit.check(bad)


@pytest.mark.parametrize('optimized', [False, True])
def test_offline_cli_works_in_normal_and_optimized_python(optimized):
    cmd = [sys.executable] + (['-O'] if optimized else []) + [
        str(ROOT / 'scripts/audit_focus_sample_20261026.py'), '--check']
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data == {'sampled': 9, 'duplicate_stop': 9,
                    'strict_local_format_pass': 8, 'ok_to_submit': False}
