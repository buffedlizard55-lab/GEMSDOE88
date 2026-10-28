"""The shared writer must not clobber other runs when output names collide.

Only synthetic temporary files are used here; this is not a model experiment or
an attempt to create a competition candidate. Existing raster/format tests
exercise the real GDAL encoder and validators independently.
"""
from concurrent.futures import ThreadPoolExecutor
import errno
import hashlib
import importlib
import json
import os
from pathlib import Path
import threading
import zipfile

import numpy as np
import pytest
import rasterio

from gems57 import submission_writer as writer
from scripts.validate_artifact import validate_artifact


@pytest.fixture
def synthetic_writer(tmp_path, monkeypatch):
    sample = tmp_path / 'sample.tif'
    sample.write_bytes(b'synthetic template')
    prediction = np.array([[1.0]], dtype=np.float32)
    footprint = np.array([[True]])

    def fake_raster(path, pixels, nodata):
        assert pixels.shape == (1, 1) and nodata is None
        Path(path).write_bytes(b'synthetic raster bytes')

    def fake_report(path, sample_path, footprint):
        return {'ok': True, 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                'n_nonzero': 1}

    monkeypatch.setattr(writer.grid, 'write_geotiff', fake_raster)
    monkeypatch.setattr(writer.gates, 'format_report', fake_report)
    monkeypatch.setattr(writer, 'validate', lambda *args: {'synthetic': True})
    monkeypatch.setattr(writer, 'assert_submittable', lambda receipt: None)

    def run():
        return writer.write_submission(tmp_path / 'run.tif', prediction, sample, footprint,
                                       name='synthetic-run', note='test only')
    return run


def test_real_encoder_and_validators_on_a_tiny_synthetic_grid(tmp_path, monkeypatch):
    """Exercise real raster serialization without producing a competition-grid file."""
    validator = importlib.import_module('gems57.validate')
    shape = (8, 8)
    monkeypatch.setattr(writer.grid, 'SHAPE', shape)
    monkeypatch.setattr(validator, 'HEIGHT', 8)
    monkeypatch.setattr(validator, 'WIDTH', 8)
    required = {key for key in validator.REQUIRED_LOCAL_CHECKS if not key.startswith('dimensions_')}
    monkeypatch.setattr(validator, 'REQUIRED_LOCAL_CHECKS', frozenset(required | {'dimensions_8x8'}))
    sample = tmp_path / 'synthetic-grid.tif'
    fp = np.ones(shape, dtype=bool)
    fp[0, :] = False
    sample_values = np.zeros(shape, dtype='float32')
    sample_values[~fp] = np.nan
    with rasterio.open(sample, 'w', driver='GTiff', width=8, height=8, count=1,
                       dtype='float32', crs=writer.grid.CRS_EPSG,
                       transform=writer.grid.TRANSFORM, nodata=np.nan) as output:
        output.write(sample_values, 1)
    prediction = np.zeros(shape, dtype='float32')
    prediction[2, 3] = .5
    path = tmp_path / 'synthetic-output.tif'
    receipt = writer.write_submission(path, prediction, sample, fp, name='synthetic only', note='not a submission')
    assert receipt['validator']['all_checks_passed'] is True
    assert receipt['template_report']['ok'] is True
    assert validate_artifact(path, sample)['ok'] is True
    with rasterio.open(path) as source:
        assert source.count == 1 and source.dtypes == ('float32',)
        assert source.shape == shape and source.transform == writer.grid.TRANSFORM
        assert np.array_equal(source.read(1), prediction)
    with zipfile.ZipFile(path.with_suffix('.zip')) as archive:
        assert archive.namelist() == [path.name] and archive.read(path.name) == path.read_bytes()
    assert receipt['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert not receipt['approved_for_weekly_slot'] and not receipt['promoted']


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -.01, 1.01])
def test_invalid_prediction_values_fail_before_writing(tmp_path, bad):
    sample = tmp_path / 'sample.tif'
    sample.write_bytes(b'unread fixture')
    with pytest.raises(ValueError):
        writer.write_submission(tmp_path / 'run.tif', np.array([[bad]]), sample,
                                np.array([[True]]), name='synthetic', note='test')
    assert sorted(p.name for p in tmp_path.iterdir()) == ['sample.tif']


def test_normal_write_is_complete_and_refuses_reuse(tmp_path, synthetic_writer):
    receipt = synthetic_writer()
    tif = tmp_path / 'run.tif'
    with zipfile.ZipFile(tmp_path / 'run.zip') as z:
        assert z.namelist() == ['run.tif']
        assert z.read('run.tif') == tif.read_bytes() == b'synthetic raster bytes'
    assert json.loads((tmp_path / 'run.json').read_text()) == receipt
    assert 'verify TIFF and ZIP hashes together' in receipt['publication']
    assert receipt['approved_for_weekly_slot'] is False
    with pytest.raises(FileExistsError):
        synthetic_writer()
    assert not list(tmp_path.glob('.run.*'))


@pytest.mark.parametrize('suffix', ['.zip', '.json', '.tif'])
def test_late_name_collision_never_overwrites_or_removes_other_file(
        tmp_path, synthetic_writer, monkeypatch, suffix):
    target = (tmp_path / 'run.tif').with_suffix(suffix)
    actual_link = os.link

    def raced_link(source, destination, **kwargs):
        if Path(destination) == target:
            target.write_bytes(b'created by another writer')
        return actual_link(source, destination, **kwargs)

    monkeypatch.setattr(writer.os, 'link', raced_link)
    with pytest.raises(FileExistsError) as failure:
        synthetic_writer()
    if suffix != '.zip' and hasattr(failure.value, '__notes__'):
        assert any('Publication incomplete' in note for note in failure.value.__notes__)
    assert target.read_bytes() == b'created by another writer'
    # No public name is removed during rollback: a portable inode-conditional
    # unlink does not exist. Earlier auxiliary links remain explicitly orphaned.
    remaining = {path.suffix for path in (tmp_path / 'run.zip', tmp_path / 'run.json', tmp_path / 'run.tif') if path.exists()}
    assert remaining == ({'.zip'} if suffix == '.zip' else
                         {'.zip', '.json'} if suffix == '.json' else {'.zip', '.json', '.tif'})
    assert not list(tmp_path.glob('.run.*'))


def test_failure_does_not_delete_a_replaced_auxiliary(tmp_path, synthetic_writer, monkeypatch):
    actual_link = os.link
    zip_path = tmp_path / 'run.zip'

    def other_writer_replaces_zip(source, destination, **kwargs):
        if Path(destination) == tmp_path / 'run.json':
            zip_path.unlink()
            zip_path.write_bytes(b'other writer now owns the zip')
            raise OSError('synthetic failure before receipt commit')
        return actual_link(source, destination, **kwargs)

    monkeypatch.setattr(writer.os, 'link', other_writer_replaces_zip)
    with pytest.raises(OSError, match='synthetic failure'):
        synthetic_writer()
    assert zip_path.read_bytes() == b'other writer now owns the zip'
    assert not (tmp_path / 'run.tif').exists()
    assert not (tmp_path / 'run.json').exists()
    assert not list(tmp_path.glob('.run.*'))


def test_failure_never_unlinks_a_public_name_even_after_it_was_published(tmp_path, synthetic_writer, monkeypatch):
    """Prevents the stat-then-unlink race, rather than relying on inode checks."""
    real_link, real_unlink = os.link, Path.unlink
    public = {tmp_path / 'run.zip', tmp_path / 'run.json', tmp_path / 'run.tif'}

    def fail_late(source, destination, **kwargs):
        if Path(destination) == tmp_path / 'run.tif':
            raise OSError('synthetic final publication failure')
        return real_link(source, destination, **kwargs)

    def no_public_unlink(path, *args, **kwargs):
        assert path not in public, 'public pathname deletion can race with another writer'
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(writer.os, 'link', fail_late)
    monkeypatch.setattr(Path, 'unlink', no_public_unlink)
    with pytest.raises(OSError, match='synthetic final publication failure'):
        synthetic_writer()
    assert (tmp_path / 'run.zip').is_file() and (tmp_path / 'run.json').is_file()
    assert not (tmp_path / 'run.tif').exists()
    assert not list(tmp_path.glob('.run.*'))


def test_unsupported_atomic_publication_fails_closed(tmp_path, synthetic_writer, monkeypatch):
    def unsupported(*args, **kwargs):
        raise OSError(errno.EOPNOTSUPP, 'hard links unsupported')
    monkeypatch.setattr(writer.os, 'link', unsupported)
    with pytest.raises(OSError):
        synthetic_writer()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['sample.tif']


def test_dangling_symlink_destination_is_not_replaced(tmp_path, synthetic_writer):
    target = tmp_path / 'run.zip'
    target.symlink_to('missing-other-writer')
    with pytest.raises(FileExistsError):
        synthetic_writer()
    assert target.is_symlink() and os.readlink(target) == 'missing-other-writer'
    assert not (tmp_path / 'run.tif').exists()


def test_parallel_writers_only_one_can_claim_a_name(tmp_path, synthetic_writer, monkeypatch):
    barrier = threading.Barrier(2, timeout=10)
    original = writer.grid.write_geotiff

    def synchronized(*args, **kwargs):
        barrier.wait()
        return original(*args, **kwargs)

    monkeypatch.setattr(writer.grid, 'write_geotiff', synchronized)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(synthetic_writer) for _ in range(2)]
        results = []
        for future in futures:
            try:
                results.append(future.result())
            except FileExistsError:
                results.append('collision')
    assert sum(result == 'collision' for result in results) == 1
    assert sum(isinstance(result, dict) for result in results) == 1
    with zipfile.ZipFile(tmp_path / 'run.zip') as archive:
        assert archive.read('run.tif') == (tmp_path / 'run.tif').read_bytes()
    assert not list(tmp_path.glob('.run.*'))
