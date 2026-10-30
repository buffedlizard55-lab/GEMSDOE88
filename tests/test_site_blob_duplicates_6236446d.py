"""Unit tests for the read-only cross-site blob-duplicate audit (session 6236446d).

These tests replace the GitHub listing with fixtures; they make no network calls.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "audit_site_blob_duplicates", ROOT / "scripts" / "audit_site_blob_duplicates.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _fake_listing(table):
    def _list(repo):
        if repo not in table:
            raise RuntimeError(f"{repo}: fixture missing")
        return table[repo]
    return _list


def test_identical_blobs_across_sites_are_grouped(monkeypatch):
    table = {
        "A": [{"path": "docs/x.tif", "blob_sha": "aaa", "size_bytes": 10}],
        "B": [{"path": "docs/y.tif", "blob_sha": "aaa", "size_bytes": 10},
              {"path": "docs/z.tif", "blob_sha": "bbb", "size_bytes": 11}],
    }
    monkeypatch.setattr(mod, "list_tifs", _fake_listing(table))
    rep = mod.build(["A", "B"])
    assert rep["tif_files_listed"] == 3
    assert rep["distinct_blobs"] == 2
    assert rep["duplicate_blob_groups"] == 1
    assert rep["duplicate_groups"][0]["copies"] == 2
    assert rep["submission_clearance"] is False


def test_listing_failure_is_recorded_not_hidden(monkeypatch):
    table = {"A": [{"path": "docs/x.tif", "blob_sha": "aaa", "size_bytes": 10}]}
    monkeypatch.setattr(mod, "list_tifs", _fake_listing(table))
    rep = mod.build(["A", "MISSING"])
    assert rep["tif_files_listed"] == 1
    assert len(rep["errors"]) == 1 and "MISSING" in rep["errors"][0]["error"]


def test_committed_evidence_is_consistent_with_schema():
    path = ROOT / "evidence" / "site_blob_duplicates_20261030.json"
    data = json.loads(path.read_text())
    assert data["schema"] == "gems88.site-blob-duplicates.v1"
    assert data["sites"] == mod.SITES
    assert data["errors"] == []
    assert data["submission_clearance"] is False
    assert data["duplicate_blob_groups"] == len(data["duplicate_groups"])
    for g in data["duplicate_groups"]:
        assert g["copies"] == len(g["locations"]) >= 2


def test_committed_run_card_stays_negative():
    card = json.loads((ROOT / "registry" / "session_6236446d_run_card.json").read_text())
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["new_tif_generated"] is False
    assert card["weekly_slots_used"] == 0
    assert card["registry_comparison"]["proof"]["universal_overlap_blocker"] is True
