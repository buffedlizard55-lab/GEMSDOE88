"""A failed or interrupted preparation must never leave stale 'ready' evidence."""
import json
import subprocess

import pytest

import prepare_data as prep


@pytest.fixture
def manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(prep, 'DATA_DIR', tmp_path)
    path = tmp_path / 'prepared_data_manifest.json'
    path.write_text('{"status":"ready","files":{"old":"receipt"}}')
    return path


@pytest.mark.parametrize('failure', [ValueError('bad SHA'), FileNotFoundError('missing'),
                                    subprocess.CalledProcessError(7, 'restore'),
                                    KeyboardInterrupt(), SystemExit(9)])
def test_failed_preparation_revokes_old_success(manifest, monkeypatch, failure):
    def fail(fetch=False):
        current = json.loads(manifest.read_text())
        assert current['status'] == 'preparing'
        assert 'files' not in current
        raise failure
    monkeypatch.setattr(prep, '_prepare_data', fail)
    with pytest.raises(type(failure)):
        prep.prepare_data()
    result = json.loads(manifest.read_text())
    assert result['status'] == 'error'
    assert result['ok_to_submit'] is False
    assert result['generation_authorized'] is False
    assert 'files' not in result
    assert result['error'].startswith(type(failure).__name__)


def test_success_publishes_only_new_checks(manifest, monkeypatch):
    result = {'status': 'ready', 'files': {'new': 'receipt'},
              'generation_authorized': False, 'ok_to_submit': False}
    def success(fetch=False):
        assert fetch is True
        assert json.loads(manifest.read_text())['status'] == 'preparing'
        return result
    monkeypatch.setattr(prep, '_prepare_data', success)
    assert prep.prepare_data(fetch=True) == result
    assert json.loads(manifest.read_text()) == result
    assert not list(manifest.parent.glob('.prepared-*.tmp'))


def test_cannot_invalidate_means_no_preparation(manifest, monkeypatch):
    def denied(*args):
        raise PermissionError('read-only receipt')
    monkeypatch.setattr(prep, 'write_preparation_manifest', denied)
    monkeypatch.setattr(prep, '_prepare_data', lambda **kwargs: pytest.fail('must not start'))
    with pytest.raises(PermissionError):
        prep.prepare_data()


def test_invalid_json_cannot_partially_replace_receipt(manifest):
    before = manifest.read_bytes()
    with pytest.raises(ValueError):
        prep.write_preparation_manifest({'invalid': float('nan')})
    assert manifest.read_bytes() == before
    assert not list(manifest.parent.glob('.prepared-*.tmp'))
