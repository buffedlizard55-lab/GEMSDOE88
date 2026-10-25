"""Downloader modes must not substitute unofficial fallbacks or ignore errors."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/download_competition_data.sh'


@pytest.mark.parametrize('mode, expected', [
    ([], ['restore_inputs.py', 'prepare_data.py']),
    (['--validation'], ['restore_inputs.py --validation']),
    (['--registry'], ['restore_inputs.py', 'restore_siblings.py', 'prepare_data.py']),
])
def test_modes_use_pinned_restore_then_prepare(tmp_path, mode, expected):
    fake = tmp_path / 'python'
    log = tmp_path / 'calls.txt'
    fake.write_text('#!/bin/bash\necho "$(basename "$1") ${2:-}" >> "$CALL_LOG"\n')
    fake.chmod(0o755)
    result = subprocess.run(['bash', str(SCRIPT), *mode], cwd=tmp_path,
                            env={**os.environ, 'PYTHON': str(fake), 'CALL_LOG': str(log)},
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert [r.strip() for r in log.read_text().splitlines()] == expected
    assert 'Owner-mirror' in result.stdout
    assert 'Organizer provenance' in result.stdout


def test_restore_error_stops_before_preparation(tmp_path):
    fake = tmp_path / 'python'
    log = tmp_path / 'calls.txt'
    fake.write_text('#!/bin/bash\necho "$(basename "$1")" >> "$CALL_LOG"\nexit 7\n')
    fake.chmod(0o755)
    result = subprocess.run(['bash', str(SCRIPT)], cwd=tmp_path,
                            env={**os.environ, 'PYTHON': str(fake), 'CALL_LOG': str(log)},
                            text=True, capture_output=True)
    assert result.returncode == 7
    assert log.read_text().splitlines() == ['restore_inputs.py']
    assert 'verified locally' not in result.stdout


def test_unknown_mode_is_not_silently_ignored(tmp_path):
    result = subprocess.run(['bash', str(SCRIPT), '--ignore-pins'], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode != 0
    assert 'Usage:' in result.stderr


def test_all_three_workflows_validate_bytes_and_rendered_decision():
    for file in ('checks.yml', 'ci.yml', 'pages.yml'):
        text = (ROOT / '.github/workflows' / file).read_text()
        for command in ('python scripts/audit_downloads.py --check', 'python scripts/render_decision.py --check', 'python -O scripts/check_site.py'):
            assert command in text


@pytest.mark.parametrize('arguments', [['--validation', '--registry'], ['', '--ignore-pins']])
def test_extra_arguments_fail_before_any_download(tmp_path, arguments):
    fake = tmp_path / 'python'
    fake.write_text('#!/bin/bash\necho UNEXPECTED_RESTORE\n')
    fake.chmod(0o755)
    result = subprocess.run(['bash', str(SCRIPT), *arguments], cwd=tmp_path,
                            env={**os.environ, 'PYTHON': str(fake)},
                            text=True, capture_output=True)
    assert result.returncode == 1
    assert 'Usage:' in result.stderr
    assert 'UNEXPECTED_RESTORE' not in result.stdout
