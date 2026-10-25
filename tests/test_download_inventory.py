"""Independently test the all-download audit, including extraction-label drift."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_downloads as audit  # noqa: E402


@pytest.fixture
def files(tmp_path):
    sample = tmp_path / "sample.tif"
    candidate = tmp_path / "candidate-DO-NOT-SUBMIT.tif"
    profile = dict(driver="GTiff", width=8, height=8, count=1, dtype="float32",
                   crs="EPSG:32611", transform=from_origin(240000, 4500000, 100, 100), nodata=None)
    sample_values = np.zeros((8, 8), dtype=np.float32)
    sample_values[0] = np.nan
    footprint = np.isfinite(sample_values)
    catalogue = np.zeros_like(footprint)
    catalogue[7, 7] = True
    values = np.zeros_like(sample_values)
    values[4, 4] = 1
    with rasterio.open(sample, "w", **profile) as dst:
        dst.write(sample_values, 1)

    def write(array=values, member=None, extra=False, tags=None):
        with rasterio.open(candidate, "w", **{**profile, "height": array.shape[0], "width": array.shape[1]}) as dst:
            dst.write(array, 1)
            if tags:
                dst.update_tags(**tags)
        with zipfile.ZipFile(candidate.with_suffix('.zip'), 'w') as z:
            z.writestr(member or candidate.name, candidate.read_bytes())
            if extra:
                z.writestr('extra.txt', 'not a one-TIFF archive')
        return audit.audit_one(candidate, sample, catalogue, footprint)

    return write, values, candidate


def test_valid_package_is_never_slot_approved(files):
    write, _, _ = files
    report = write()
    assert report["research_download_ok"] is True
    assert report["format_valid"] is True
    assert report["independent_decoders_agree"] is True
    assert report["ok_to_submit"] is False
    assert report["positive_pixels"] == 1


@pytest.mark.parametrize('bad_value', [-0.1, 1.001, np.nan, np.inf, -np.inf])
def test_nonfinite_or_out_of_range_is_rejected_without_clipping(files, bad_value):
    write, values, _ = files
    values[3, 3] = bad_value
    report = write(values)
    assert report["format_valid"] is False
    assert report["research_download_ok"] is False


def test_outside_and_known_fault_support_fail(files):
    write, values, _ = files
    values[0, 0] = 1
    assert write(values)["research_download_ok"] is False
    values[0, 0] = 0
    values[7, 7] = 1
    report = write(values)
    assert report["positive_on_catalogue"] == 1
    assert report["research_download_ok"] is False


@pytest.mark.parametrize('member,extra', [('old-unmarked.tif', False), ('../bad.tif', False), (None, True)])
def test_zip_must_preserve_exact_negative_name_and_single_payload(files, member, extra):
    write, _, _ = files
    report = write(member=member, extra=extra)
    assert report["format_valid"] is True
    assert report["zip_one_byte_identical_tif"] is False
    assert report["research_download_ok"] is False


def test_shape_mismatch_and_empty_support_fail(files):
    write, _, _ = files
    report = write(np.zeros((7, 8), dtype=np.float32))
    assert report["research_download_ok"] is False
    report = write(np.zeros((8, 8), dtype=np.float32))
    assert report["research_download_ok"] is False


def test_metadata_change_is_not_pixel_uniqueness(files):
    write, _, _ = files
    before = write(tags={"comment": "first"})
    after = write(tags={"comment": "a different TIFF header, same predictions"})
    assert before["sha256"] != after["sha256"]
    assert before["decoded_float32_sha256"] == after["decoded_float32_sha256"]
    assert before["positive_support_sha256"] == after["positive_support_sha256"]


def test_decoder_failure_fails_closed(files, monkeypatch):
    write, _, candidate = files
    write()
    monkeypatch.setattr(audit.tifffile, 'imread', lambda _: (_ for _ in ()).throw(ValueError('decoder failed')))
    report = write()
    assert report["research_download_ok"] is False
    assert report["ok_to_submit"] is False
    assert 'decoder failed' in report["errors"][0]


def test_failed_fresh_audit_overwrites_success(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'audit', lambda _: (_ for _ in ()).throw(ValueError('changed witness')))
    for rel in audit.OUTPUTS:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"ok_to_submit":true}')
    assert audit.main([], tmp_path) == 1
    for rel in audit.OUTPUTS:
        report = json.loads((tmp_path / rel).read_text())
        assert report['decision'] == 'AUDIT_ERROR'
        assert report['ok_to_submit'] is False


def test_published_inventory_covers_every_actual_tiff_and_zip():
    report = json.loads((ROOT / 'docs/data/download_audit.json').read_text())
    assert report == json.loads((ROOT / 'evidence/download_audit.json').read_text())
    actual = {p.name for p in audit.published_tiffs(ROOT)}
    sdtl = json.loads((ROOT / 'registry/sdtl88_run_card.json').read_text())
    promoted_sha = sdtl['raster']['sha256'] if (sdtl['verdict'] == 'promote' and sdtl['ok_to_submit'] is True) else None
    assert {r['file'] for r in report['artifacts']} == actual
    assert len(report['artifacts']) == report['tiff_count']
    for row in report['artifacts']:
        tif = ROOT / 'docs/downloads' / row['file']
        zipped = tif.with_suffix('.zip')
        assert audit.sha(tif) == row['sha256']
        assert audit.sha(zipped) == row['zip_sha256']
        assert row['format_valid'] and row['research_download_ok']
        # IR-88-SDTL-01: only the canonical promoted card's bytes may carry ok_to_submit.
        assert row['ok_to_submit'] is (row['sha256'] == promoted_sha)
        with zipfile.ZipFile(zipped) as z:
            assert z.namelist() == [tif.name]
            assert z.read(tif.name) == tif.read_bytes()
    assert report['protocol_eligible_count'] == (1 if promoted_sha else 0)


def test_packaging_repairs_did_not_change_any_tiff_bytes():
    record = json.loads((ROOT / 'evidence/archive_repairs_20261025.json').read_text())
    assert record['new_tiffs_generated'] == 0
    for row in record['repairs']:
        assert audit.sha(ROOT / row['file']) == row['tif_sha256_unchanged']
        assert audit.sha(ROOT / row['archive']) == row['new_zip_sha256']
        assert row['old_zip_sha256'] != row['new_zip_sha256']
        assert 'DO-NOT-SUBMIT' in row['new_member']


def test_inventory_recognizes_all_tiff_suffix_cases(tmp_path):
    directory = tmp_path / 'docs/downloads'
    directory.mkdir(parents=True)
    for name in ('one.tif', 'two.TIF', 'three.tiff', 'four.TIFF', 'archive.zip', 'notes.md'):
        (directory / name).touch()
    (directory / 'not-a-file.tif').mkdir()
    assert {p.name for p in audit.published_tiffs(tmp_path)} == {'one.tif', 'two.TIF', 'three.tiff', 'four.TIFF'}


def test_missing_archive_is_rejected(files):
    write, _, candidate = files
    write()
    candidate.with_suffix('.zip').unlink()
    sample = candidate.parent / 'sample.tif'
    footprint = np.ones((8, 8), dtype=bool)
    footprint[0] = False
    catalogue = np.zeros_like(footprint)
    report = audit.audit_one(candidate, sample, catalogue, footprint)
    assert report['format_valid'] is True
    assert report['research_download_ok'] is False
    assert report['ok_to_submit'] is False
    assert 'FileNotFoundError' in report['errors'][0]


def test_cli_rejects_even_a_noncanonical_bad_download(tmp_path, monkeypatch):
    report = {'tiff_count': 2, 'research_download_pass_count': 1, 'artifacts': [
        {'file': 'canonical.tif', 'research_download_ok': True},
        {'file': 'bad.tif', 'research_download_ok': False}]}
    monkeypatch.setattr(audit, 'audit', lambda _: report)
    assert audit.main([], tmp_path) == 1
    stored = json.loads((tmp_path / audit.OUTPUTS[0]).read_text())
    assert stored['decision'] == 'AUDIT_ERROR'
    assert 'bad.tif' in stored['error']
    assert stored['ok_to_submit'] is False
