"""A format/package audit cannot resurrect a withdrawn scientific approval.

Tiny synthetic rasters only; no competition feature or candidate generation.
"""
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.audit_downloads import audit_one, sha

ROOT = Path(__file__).resolve().parents[1]


def make_package(root, *, marked=True, extra_member=False):
    directory = root / 'docs/downloads'
    directory.mkdir(parents=True)
    name = 'candidate-DO-NOT-SUBMIT.tif' if marked else 'candidate.tif'
    candidate = directory / name
    sample = root / 'sample.tif'
    values = np.zeros((8, 8), dtype='float32')
    values[4, 4] = 1
    profile = dict(driver='GTiff', height=8, width=8, count=1,
                   dtype='float32', crs='EPSG:32611',
                   transform=from_origin(100, 200, 100, 100))
    for path in (candidate, sample):
        with rasterio.open(path, 'w', **profile) as dst:
            dst.write(values, 1)
    with zipfile.ZipFile(candidate.with_suffix('.zip'), 'w') as archive:
        archive.writestr(candidate.name, candidate.read_bytes())
        if extra_member:
            archive.writestr('extra.txt', 'not a single-TIFF ZIP')
    gates = root / 'registry/con88_gates.json'
    gates.parent.mkdir()
    gates.write_text(json.dumps(dict(ok_to_submit=True, candidate=candidate.name,
                                    sha256=sha(candidate), G1_ok=True, G2_ok=True)))
    return candidate, sample


@pytest.mark.parametrize('marked', [True, False])
@pytest.mark.parametrize('extra_member', [True, False])
def test_stale_exact_sha_approval_never_authorizes_download_row(tmp_path, marked, extra_member):
    candidate, sample = make_package(tmp_path, marked=marked, extra_member=extra_member)
    report = audit_one(candidate, sample, np.zeros((8, 8), bool), np.ones((8, 8), bool))
    assert report['format_valid'] is True
    assert report['cleared_by_con88_gates'] is False
    assert report['ok_to_submit'] is False
    assert report['research_download_ok'] is (marked and not extra_member)


@pytest.mark.parametrize('optimized', [False, True])
def test_stale_approval_boundary_survives_optimized_python(tmp_path, optimized):
    candidate, sample = make_package(tmp_path)
    script = (
        'import json,sys,numpy as np; from pathlib import Path; '
        'from scripts.audit_downloads import audit_one; '
        'print(json.dumps(audit_one(Path(sys.argv[1]),Path(sys.argv[2]),'
        'np.zeros((8,8),bool),np.ones((8,8),bool))))'
    )
    command = [sys.executable] + (['-O'] if optimized else [])
    result = subprocess.run(command + ['-c', script, str(candidate), str(sample)],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    assert report['ok_to_submit'] is False
    assert report['cleared_by_con88_gates'] is False
    assert report['research_download_ok'] is True


def test_con88_quarantine_preserves_tiff_and_pins_corrected_metadata():
    record = json.loads((ROOT / 'evidence/con88_clearance_withdrawal_96f5f523.json').read_text())
    packaging = record['packaging']
    assert record['prediction_bytes_changed'] is False
    assert record['new_tiffs_generated'] == 0
    assert not (ROOT / packaging['old_tif']).exists()
    candidate = ROOT / packaging['new_tif']
    assert sha(candidate) == packaging['unchanged_tiff_sha256']
    assert sha(candidate.with_suffix('.zip')) == packaging['new_zip_sha256']
    with zipfile.ZipFile(candidate.with_suffix('.zip')) as archive:
        assert archive.namelist() == [candidate.name]
        assert archive.read(candidate.name) == candidate.read_bytes()
    for relative, digest in record['corrected_metadata_sha256'].items():
        path = ROOT / relative
        assert sha(path) == digest
        card = json.loads(path.read_text())
        assert card['ok_to_submit'] is False
        assert card['approved_for_weekly_slot'] is False
        assert card['verdict'] == 'negative'
        assert card['literal_overlap_3px'] == 1.0
        assert card['historical_holdout_valid_for_promotion'] is False


@pytest.mark.skipif(not (ROOT / 'data/bridge/sample_submission.tif').exists(), reason='validation inputs not restored')
@pytest.mark.parametrize('optimized', [False, True])
@pytest.mark.parametrize('require_submit', [False, True])
def test_con88_validator_is_read_only_and_cannot_promote(optimized, require_submit):
    paths = [ROOT / relative for relative in (
        'registry/con88_gates.json', 'run_card_con88.json',
        'evidence/con88_clearance_withdrawal_96f5f523.json')]
    before = {p: p.read_bytes() for p in paths}
    command = [sys.executable] + (['-O'] if optimized else [])
    command += ['scripts/validate_con88.py'] + (['--require-submit'] if require_submit else [])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == (2 if require_submit else 0), result.stderr
    report = json.loads(result.stdout)
    assert report['decision'] == 'DUPLICATE_STOP'
    assert report['ok_to_submit'] is False
    assert report['research_download_ok'] is True
    assert report['historical_holdout_valid_for_promotion'] is False
    assert report['experiments_run'] == report['new_rasters_generated'] == 0
    assert before == {p: p.read_bytes() for p in paths}


def test_con88_validator_missing_input_fails_closed_without_writing(tmp_path, capsys):
    from scripts.validate_con88 import main
    assert main(['--require-submit'], tmp_path) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['decision'] == 'AUDIT_ERROR'
    assert result['ok_to_submit'] is False
    assert not list(tmp_path.rglob('*'))
