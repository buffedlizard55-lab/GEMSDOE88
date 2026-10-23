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
