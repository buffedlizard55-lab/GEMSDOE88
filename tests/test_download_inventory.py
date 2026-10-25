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
    audit.check_package_inventory(ROOT)
    actual = {(directory, p.name) for directory in audit.PUBLICATION_DIRECTORIES
              for p in audit.published_tiffs(ROOT, directory)}
    all_rows = report['artifacts'] + report['additional_research_artifacts']
    assert {(r.get('publication_directory', 'downloads'), r['file']) for r in all_rows} == actual
    assert len(report['artifacts']) == report['tiff_count'] == report['research_download_pass_count']
    assert len(report['additional_research_artifacts']) == report['additional_research_tiff_count']
    assert len(all_rows) == report['total_published_tiff_count'] == report['total_research_download_pass_count']
    assert all(r['publication_directory'] == 'research-variants' for r in report['additional_research_artifacts'])
    for row in all_rows:
        tif = ROOT / 'docs' / row.get('publication_directory', 'downloads') / row['file']
        zipped = tif.with_suffix('.zip')
        assert audit.sha(tif) == row['sha256']
        assert audit.sha(zipped) == row['zip_sha256']
        assert row['format_valid'] and row['research_download_ok']
        assert row['ok_to_submit'] is False
        assert 'cleared_by_con88_gates' not in row
        assert row['negative_filename_markers'] is True
        with zipfile.ZipFile(zipped) as z:
            assert z.namelist() == [tif.name]
            assert z.read(tif.name) == tif.read_bytes()
    assert report['protocol_eligible_count'] == 0


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


def test_complete_flat_package_inventory_passes(tmp_path):
    directory = tmp_path / 'docs/downloads'
    directory.mkdir(parents=True)
    for name in ('one.tif', 'one.zip', 'two.TIFF', 'two.zip', 'metadata.json'):
        (directory / name).touch()
    audit.check_package_inventory(tmp_path)


@pytest.mark.parametrize('name', ['orphan.zip', 'orphan.ZIP', 'one.ZIP'])
def test_orphan_archive_is_not_silently_omitted(tmp_path, name):
    directory = tmp_path / 'docs/downloads'
    directory.mkdir(parents=True)
    for path in ('one.tif', 'one.zip', name):
        (directory / path).touch()
    with pytest.raises(ValueError, match='orphan ZIPs'):
        audit.check_package_inventory(tmp_path)


def test_missing_archive_is_an_inventory_error(tmp_path):
    directory = tmp_path / 'docs/downloads'
    directory.mkdir(parents=True)
    (directory / 'one.tif').touch()
    with pytest.raises(ValueError, match='missing ZIPs'):
        audit.check_package_inventory(tmp_path)


def test_two_tiff_extensions_cannot_share_one_zip(tmp_path):
    directory = tmp_path / 'docs/downloads'
    directory.mkdir(parents=True)
    for name in ('one.tif', 'one.tiff', 'one.zip'):
        (directory / name).touch()
    with pytest.raises(ValueError, match='share the same ZIP path'):
        audit.check_package_inventory(tmp_path)


@pytest.mark.parametrize('suffix', ['.tif', '.TIFF', '.zip', '.ZIP'])
def test_nested_artifact_cannot_evade_flat_inventory(tmp_path, suffix):
    directory = tmp_path / 'docs/downloads/hidden'
    directory.mkdir(parents=True)
    (directory / ('hidden' + suffix)).touch()
    with pytest.raises(ValueError, match='Nested published artifacts'):
        audit.check_package_inventory(tmp_path)


def test_inventory_error_fails_before_stale_preflight_or_success_can_be_used(tmp_path, monkeypatch):
    directory = tmp_path / 'docs/downloads'
    directory.mkdir(parents=True)
    (directory / 'orphan-DO-NOT-SUBMIT.zip').touch()
    monkeypatch.setattr(audit, 'preflight', lambda _: pytest.fail('bad inventory must stop first'))
    assert audit.main([], tmp_path) == 1
    for relative in audit.OUTPUTS:
        report = json.loads((tmp_path / relative).read_text())
        assert report['decision'] == 'AUDIT_ERROR'
        assert 'orphan ZIPs' in report['error']
        assert report['ok_to_submit'] is False


def test_both_declared_flat_publication_directories_are_audited(tmp_path):
    assert set(audit.PUBLICATION_DIRECTORIES) == {'downloads', 'research-variants'}
    for directory in audit.PUBLICATION_DIRECTORIES:
        base = tmp_path / 'docs' / directory
        base.mkdir(parents=True)
        for name in ('one.tif', 'one.zip', 'two.TIFF', 'two.zip', 'metadata.json'):
            (base / name).touch()
        assert {p.name for p in audit.published_tiffs(tmp_path, directory)} == {'one.tif', 'two.TIFF'}
    audit.check_package_inventory(tmp_path)


@pytest.mark.parametrize('directory', audit.PUBLICATION_DIRECTORIES)
@pytest.mark.parametrize('corruption,match', [
    ('orphan.ZIP', 'orphan ZIPs'),
    ('one.ZIP', 'orphan ZIPs'),
    ('missing', 'missing ZIPs'),
    ('collision', 'share the same ZIP path'),
    ('nested', 'Nested published artifacts'),
])
def test_variant_directory_cannot_evade_package_checks(tmp_path, directory, corruption, match):
    (tmp_path / 'docs/downloads').mkdir(parents=True)
    base = tmp_path / 'docs' / directory
    base.mkdir(exist_ok=True)
    for name in ('one.tif', 'one.zip'):
        (base / name).touch()
    if corruption == 'missing':
        (base / 'one.zip').unlink()
    elif corruption == 'collision':
        (base / 'one.TIFF').touch()
    elif corruption == 'nested':
        (base / 'hidden').mkdir()
        (base / 'hidden/unrecorded.zip').touch()
    else:
        (base / corruption).touch()
    with pytest.raises(ValueError, match=match):
        audit.check_package_inventory(tmp_path)


@pytest.mark.parametrize('suffix', ['.tif', '.TIFF', '.zip', '.ZIP'])
def test_undeclared_publication_directory_is_not_silently_ignored(tmp_path, suffix):
    (tmp_path / 'docs/downloads').mkdir(parents=True)
    unknown = tmp_path / 'docs/another-lane'
    unknown.mkdir()
    (unknown / ('hidden' + suffix)).touch()
    with pytest.raises(ValueError, match='outside the declared audited directories'):
        audit.check_package_inventory(tmp_path)
    with pytest.raises(ValueError, match='Unknown publication directory'):
        audit.published_tiffs(tmp_path, 'another-lane')


@pytest.fixture
def saved_audit(tmp_path, monkeypatch):
    # Exercise the actual --check comparison without reopening 44 large rasters
    # for each JSON mutation. Separate integration tests hash the real packages.
    report = json.loads((ROOT / 'docs/data/download_audit.json').read_text())
    audit.write(tmp_path, report)
    fresh = {**report, 'checked_at_utc': 'a different run timestamp'}
    monkeypatch.setattr(audit, 'audit', lambda _: fresh)
    return report


def test_check_ignores_only_the_top_level_run_timestamp(tmp_path, saved_audit):
    assert audit.main(['--check'], tmp_path) == 0
    for relative in audit.OUTPUTS:
        assert json.loads((tmp_path / relative).read_text()) == saved_audit


@pytest.mark.parametrize('relative', audit.OUTPUTS)
@pytest.mark.parametrize('corruption', ['variant-hash', 'variant-zip', 'variant-missing', 'total-count', 'witness', 'unknown-key'])
def test_check_compares_complete_saved_manifest_not_only_main_rows(tmp_path, saved_audit, relative, corruption):
    path = tmp_path / relative
    stored = json.loads(path.read_text())
    if corruption == 'variant-hash':
        stored['additional_research_artifacts'][0]['sha256'] = '0' * 64
    elif corruption == 'variant-zip':
        stored['additional_research_artifacts'][0]['zip_sha256'] = '0' * 64
    elif corruption == 'variant-missing':
        stored['additional_research_artifacts'] = []
    elif corruption == 'total-count':
        stored['total_published_tiff_count'] -= 1
    elif corruption == 'witness':
        stored['preplacement_registry_proof']['witness_sha256'] = '0' * 64
    else:
        stored['unreviewed_extra_clearance'] = True
    path.write_text(json.dumps(stored))
    before = path.read_bytes()
    assert audit.main(['--check'], tmp_path) == 1
    # A check does not silently rewrite altered evidence into a pass.
    assert path.read_bytes() == before


def test_failed_variant_fresh_audit_invalidates_saved_success(tmp_path, monkeypatch):
    report = json.loads((ROOT / 'docs/data/download_audit.json').read_text())
    report['additional_research_artifacts'][0]['research_download_ok'] = False
    monkeypatch.setattr(audit, 'audit', lambda _: report)
    assert audit.main([], tmp_path) == 1
    for relative in audit.OUTPUTS:
        failed = json.loads((tmp_path / relative).read_text())
        assert failed['decision'] == 'AUDIT_ERROR'
        assert failed['ok_to_submit'] is False
        assert report['additional_research_artifacts'][0]['file'] in failed['error']


def inventory_pair(root, name='research-DO-NOT-SUBMIT.tif'):
    """Empty bytes suffice: these tests exercise coverage, not raster validity."""
    path = root / 'docs/downloads' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    path.with_suffix('.zip').touch()
    return path


def test_closed_publication_inventory_accepts_all_tiff_suffixes(tmp_path):
    expected = [inventory_pair(tmp_path, f'{i}-DO-NOT-SUBMIT{suffix}')
                for i, suffix in enumerate(('.tif', '.TIF', '.tiff', '.TIFF'))]
    (tmp_path / 'docs/downloads/metadata.json').write_text('{}')
    assert audit.publication_inventory(tmp_path) == expected


@pytest.mark.parametrize('name', ['orphan.zip', 'orphan.ZIP', 'orphan.Zip'])
def test_orphan_archive_cannot_escape_all_download_audit(tmp_path, name):
    inventory_pair(tmp_path)
    (tmp_path / 'docs/downloads' / name).touch()
    with pytest.raises(ValueError, match='orphan ZIPs'):
        audit.publication_inventory(tmp_path)


def test_inventory_requires_exact_archive_path_not_case_folded_alias(tmp_path):
    candidate = inventory_pair(tmp_path)
    candidate.with_suffix('.zip').rename(candidate.with_suffix('.ZIP'))
    with pytest.raises(ValueError, match='missing ZIPs=.*orphan ZIPs='):
        audit.publication_inventory(tmp_path)


def test_inventory_rejects_missing_package_and_ambiguous_stem(tmp_path):
    candidate = inventory_pair(tmp_path)
    candidate.with_suffix('.zip').unlink()
    with pytest.raises(ValueError, match='missing ZIPs'):
        audit.publication_inventory(tmp_path)
    candidate.with_suffix('.zip').touch()
    candidate.with_suffix('.tiff').touch()
    with pytest.raises(ValueError, match='Multiple TIFFs'):
        audit.publication_inventory(tmp_path)


@pytest.mark.parametrize('suffix', ['.tif', '.TIFF', '.zip', '.ZIP'])
def test_nested_payloads_are_not_silently_ignored(tmp_path, suffix):
    inventory_pair(tmp_path)
    hidden = tmp_path / 'docs/downloads/archive' / ('hidden' + suffix)
    hidden.parent.mkdir()
    hidden.touch()
    with pytest.raises(ValueError, match='nested TIFF/ZIP'):
        audit.publication_inventory(tmp_path)


@pytest.mark.parametrize('target_type', ['file', 'directory', 'missing'])
def test_symlinked_downloads_fail_closed(tmp_path, target_type):
    inventory_pair(tmp_path)
    target = tmp_path / 'outside'
    if target_type == 'file':
        target.touch()
    elif target_type == 'directory':
        target.mkdir()
    (tmp_path / 'docs/downloads/linked.zip').symlink_to(target)
    with pytest.raises(ValueError, match='Symlinks'):
        audit.publication_inventory(tmp_path)


def test_orphan_archive_invalidates_fresh_evidence_before_preflight(tmp_path, monkeypatch):
    inventory_pair(tmp_path)
    (tmp_path / 'docs/downloads/unchecked.ZIP').touch()
    def forbidden_preflight(_):
        pytest.fail('inventory must fail before expensive preflight')
    monkeypatch.setattr(audit, 'preflight', forbidden_preflight)
    for rel in audit.OUTPUTS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"research_download_pass_count":43,"ok_to_submit":true}')
    assert audit.main([], tmp_path) == 1
    for rel in audit.OUTPUTS:
        result = json.loads((tmp_path / rel).read_text())
        assert result['decision'] == 'AUDIT_ERROR'
        assert result['research_download_pass_count'] == 0
        assert result['ok_to_submit'] is False
        assert 'unchecked.ZIP' in result['error']


def test_inventory_check_failure_is_read_only_but_nonzero(tmp_path):
    inventory_pair(tmp_path)
    (tmp_path / 'docs/downloads/orphan.zip').touch()
    for rel in audit.OUTPUTS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('stored evidence must not be overwritten in --check mode')
    before = {rel: (tmp_path / rel).read_bytes() for rel in audit.OUTPUTS}
    assert audit.main(['--check'], tmp_path) == 1
    assert before == {rel: (tmp_path / rel).read_bytes() for rel in audit.OUTPUTS}


def test_real_publication_inventory_has_no_unchecked_archives():
    paths = audit.publication_inventory(ROOT)
    report = json.loads((ROOT / 'docs/data/download_audit.json').read_text())
    assert {p.with_suffix('.zip').name for p in paths} == {
        row['zip_file'] for row in report['artifacts']}


def test_publication_directory_itself_cannot_be_a_symlink(tmp_path):
    target = tmp_path / 'elsewhere'
    target.mkdir()
    (target / 'research-DO-NOT-SUBMIT.tif').touch()
    (target / 'research-DO-NOT-SUBMIT.zip').touch()
    (tmp_path / 'docs').mkdir()
    (tmp_path / 'docs/downloads').symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='Symlinks'):
        audit.publication_inventory(tmp_path)


@pytest.mark.parametrize('target_type', ['file', 'directory', 'missing', 'publication-root'])
def test_variant_symlinks_are_rejected_by_the_same_inventory_policy(tmp_path, target_type):
    inventory_pair(tmp_path)
    target = tmp_path / 'outside'
    if target_type == 'file':
        target.touch()
    elif target_type in {'directory', 'publication-root'}:
        target.mkdir()
    directory = tmp_path / 'docs/research-variants'
    if target_type == 'publication-root':
        directory.symlink_to(target, target_is_directory=True)
    else:
        directory.mkdir()
        (directory / 'linked-DO-NOT-SUBMIT.zip').symlink_to(target)
    for guard in (audit.check_package_inventory, audit.publication_inventory):
        with pytest.raises(ValueError, match='Symlinks'):
            guard(tmp_path)
