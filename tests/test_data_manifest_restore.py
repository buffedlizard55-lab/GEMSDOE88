"""Regression checks for manifest-pinned multipart feature restoration."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import restore_inputs  # conftest adds the scripts directory to sys.path

ROOT = Path(__file__).resolve().parents[1]


def test_multipart_feature_restore_matches_manifest_source_and_hash():
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text(encoding="utf-8"))
    entry = next(item for item in manifest["files"] if item["id"] == "training_features")

    assert entry["multipart"] is True
    assert restore_inputs.FEATURE_REPO.removesuffix(".git") == f"https://github.com/{entry['repo']}"
    assert restore_inputs.FEATURE_COMMIT == entry["ref"]
    assert restore_inputs.FEATURE_SHA256 == entry["sha256"]
    assert restore_inputs.FEATURE_PARTS[0] == entry["path"]

    prefix = entry["path"].rsplit("-", 1)[0]
    assert restore_inputs.FEATURE_PARTS == [f"{prefix}-{index:03d}" for index in range(5)]
    assert entry["dest"] == "data/training_features.tif"


def test_restore_helper_bootstraps_repo_root_without_pythonpath():
    """Direct helper execution must be able to import the multipart restore code."""
    code = r"""
import os, runpy, sys
root = os.getcwd()
sys.path[:] = [p for p in sys.path if p and os.path.abspath(p) != root]
runpy.run_path('scripts/restore_r0_prune_inputs.py', run_name='restore_helper_test')
assert root in [os.path.abspath(p) for p in sys.path]
from scripts import restore_inputs
assert restore_inputs.FEATURE_SHA256
"""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_restore_group_creates_data_directory_on_fresh_checkout(tmp_path, monkeypatch):
    """Calling the reusable helper must not depend on main() side effects."""
    import hashlib

    root = tmp_path / 'fresh'
    root.mkdir()
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'sample.tif').write_bytes(b'pinned test bytes')
    expected = hashlib.sha256(b'pinned test bytes').hexdigest()
    monkeypatch.setattr(restore_inputs, 'ROOT', root)
    monkeypatch.setattr(restore_inputs, 'DATA', root / 'data')
    monkeypatch.setattr(restore_inputs, 'sparse_fetch', lambda *args: source)
    items = [('sample.tif', 'data/bridge/sample.tif', expected)]
    restore_inputs.restore_group('test', 'unused', 'unused', items)
    assert (root / 'data/bridge/sample.tif').read_bytes() == b'pinned test bytes'
    # Existing verified data must work without fetching again.
    def unexpected_fetch(*args):
        raise AssertionError('already verified input fetched again')
    monkeypatch.setattr(restore_inputs, 'sparse_fetch', unexpected_fetch)
    restore_inputs.restore_group('test', 'unused', 'unused', items)
