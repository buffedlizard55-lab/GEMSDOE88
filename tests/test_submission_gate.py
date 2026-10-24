"""Fail-closed behaviour of scripts/submission_gate.py (IR-88-59)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import submission_gate as sg  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ROOT / "data" / "bridge" / "sample_submission.tif").is_file()
    or not (ROOT / "data" / "registry" / "h33_education.tif").is_file(),
    reason="gitignored grid/registry rasters not restored (python scripts/restore_inputs.py --validation)")


def _card():
    return json.loads((ROOT / "registry" / "provcrest_run_card.json").read_text())


def _sandbox(tmp_path, *, tif_bytes=None, extra_registry=None):
    """Copy the candidate + cards into tmp; symlink the large restored inputs."""
    card = _card()
    for rel in ("registry/provcrest_run_card.json", "registry/provcrest_nullcontrol_audit.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, tmp_path / rel)
    dl = tmp_path / "docs" / "downloads"
    dl.mkdir(parents=True)
    tif = ROOT / card["submission"]["file"]
    for suf in (".tif", ".zip", ".json"):
        shutil.copy2(tif.with_suffix(suf), dl / tif.with_suffix(suf).name)
    (tmp_path / "submissions").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "bridge").symlink_to(ROOT / "data" / "bridge")
    reg = tmp_path / "data" / "registry"
    reg.mkdir()
    for p in (ROOT / "data" / "registry").rglob("*.tif"):
        (reg / p.relative_to(ROOT / "data" / "registry")).parent.mkdir(parents=True, exist_ok=True)
        (reg / p.relative_to(ROOT / "data" / "registry")).symlink_to(p)
    if extra_registry is not None:
        shutil.copy2(extra_registry, reg / "planted_duplicate.tif")
    if tif_bytes is not None:
        (dl / tif.name).write_bytes(tif_bytes)
    return tmp_path


def _failed_ids(result):
    return {r["id"] for r in result["checks"] if not r["pass"]}


def test_published_candidate_passes_every_gate():
    res = sg.run_gate(ROOT)
    assert res["failures"] == [], res["failures"]
    assert res["verdict"] == "OK_TO_SUBMIT" and res["ok_to_submit"] is True
    assert res["approved_for_weekly_slot"] is False
    assert res["candidate"]["note_chars"] <= 140
    assert res["n_dots"] == 37654 and res["min_catalogue_distance_px"] > 3.0
    ids = {r["id"] for r in res["checks"]}
    assert {"FMT-06", "FMT-07", "UNQ-02", "UNQ-03", "SCI-04-ALL", "SCI-04-FAR"} <= ids


def test_committed_gate_json_matches_a_fresh_run():
    fresh = sg.run_gate(ROOT)
    committed = json.loads((ROOT / "docs" / "data" / "submission_gate.json").read_text())
    assert committed == fresh


def test_nan_in_footprint_fails_closed(tmp_path):
    root = _sandbox(tmp_path)
    tif = root / "docs" / "downloads" / Path(_card()["submission"]["file"]).name
    with rasterio.open(tif) as ds:
        prof = ds.profile
        a = ds.read(1)
    a[np.argwhere(a == 0)[0][0], np.argwhere(a == 0)[0][1]] = np.nan
    with rasterio.open(tif, "w", **prof) as out:
        out.write(a, 1)
    res = sg.run_gate(root)
    assert res["ok_to_submit"] is False and res["verdict"] == "DO_NOT_SUBMIT"
    assert {"FMT-06", "ID-01"} <= _failed_ids(res)


def test_out_of_range_value_fails_closed(tmp_path):
    root = _sandbox(tmp_path)
    tif = root / "docs" / "downloads" / Path(_card()["submission"]["file"]).name
    with rasterio.open(tif) as ds:
        prof = ds.profile
        a = ds.read(1)
    yx = np.argwhere(a > 0)[0]
    a[yx[0], yx[1]] = 1.25
    with rasterio.open(tif, "w", **prof) as out:
        out.write(a, 1)
    res = sg.run_gate(root)
    assert res["ok_to_submit"] is False
    assert {"FMT-07", "FMT-10"} <= _failed_ids(res)


def test_wrong_grid_fails_closed(tmp_path):
    root = _sandbox(tmp_path)
    tif = root / "docs" / "downloads" / Path(_card()["submission"]["file"]).name
    with rasterio.open(tif) as ds:
        prof = ds.profile
        a = ds.read(1)
    prof["transform"] = rasterio.Affine(100.0, 0.0, 243450.0, 0.0, -100.0, 4508550.0)
    with rasterio.open(tif, "w", **prof) as out:
        out.write(a, 1)
    assert "FMT-05" in _failed_ids(sg.run_gate(root))


def test_planted_pixel_duplicate_is_caught(tmp_path):
    cand = ROOT / _card()["submission"]["file"]
    root = _sandbox(tmp_path)
    # a byte-different but pixel-identical copy (re-encoded) planted in the registry
    with rasterio.open(cand) as ds:
        prof = ds.profile
        a = ds.read(1)
    prof.update(compress="lzw")
    planted = tmp_path / "planted_src.tif"
    with rasterio.open(planted, "w", **prof) as out:
        out.write(a, 1)
    shutil.copy2(planted, tmp_path / "data" / "registry" / "planted_duplicate.tif")
    res = sg.run_gate(root)
    failed = _failed_ids(res)
    assert res["ok_to_submit"] is False
    assert "UNQ-01" in failed and "UNQ-02" in failed


def test_missing_inputs_fail_closed_without_crashing(tmp_path):
    root = _sandbox(tmp_path)
    (root / "data" / "bridge").unlink()
    res = sg.run_gate(root)
    assert res["ok_to_submit"] is False and "FMT-00" in _failed_ids(res)


def test_weakened_science_blocks(tmp_path):
    root = _sandbox(tmp_path)
    p = root / "registry" / "provcrest_nullcontrol_audit.json"
    audit = json.loads(p.read_text())
    audit["views"]["FAR"]["paired_differences_vs_provcrest_rank"]["null_random"]["ci95"][0] = -0.001
    p.write_text(json.dumps(audit))
    res = sg.run_gate(root)
    assert res["ok_to_submit"] is False and "SCI-04-FAR" in _failed_ids(res)


def test_name_note_limits(tmp_path):
    root = _sandbox(tmp_path)
    p = root / "registry" / "provcrest_run_card.json"
    card = json.loads(p.read_text())
    card["submission"]["submission_note"] = "x" * 141
    p.write_text(json.dumps(card))
    assert "ID-03" in _failed_ids(sg.run_gate(root))
