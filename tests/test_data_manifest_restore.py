"""Regression checks for manifest-pinned multipart feature restoration."""
from __future__ import annotations

import json
from pathlib import Path

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
