import importlib.util
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

spec = importlib.util.spec_from_file_location('audit', Path(__file__).parents[1] / 'scripts/validate_artifact.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def write(path, array=None, **kwargs):
    options = dict(driver='GTiff', height=3, width=4, count=1,
                   dtype='float32', crs='EPSG:32611', transform=from_origin(100, 200, 100, 100))
    options.update(kwargs)
    with rasterio.open(path, 'w', **options) as d:
        d.write(np.zeros((options['count'], options['height'], options['width']), dtype='float32'))
        if array is not None:
            d.write(array, 1)
    return path


def test_valid_never_means_ready(tmp_path):
    p = write(tmp_path / 'a.tif')
    report = audit.validate(p, p)
    assert report['format_valid']
    assert not report['submission_ready']
    assert len(report['sha256']) == 64


@pytest.mark.parametrize('bad', [-1, 1.01, np.nan, np.inf, -np.inf, -3.4e38])
def test_reject_bad_values(tmp_path, bad):
    ref = write(tmp_path / 'ref.tif')
    x = np.zeros((3, 4), dtype='float32'); x[0, 0] = bad
    assert not audit.validate(write(tmp_path / 'bad.tif', x), ref)['format_valid']


@pytest.mark.parametrize('options', [dict(count=2), dict(crs='EPSG:4326'),
    dict(width=5), dict(transform=from_origin(101, 200, 100, 100)),
    dict(nodata=0)])
def test_reject_grid_or_metadata(tmp_path, options):
    ref = write(tmp_path / 'ref.tif')
    assert not audit.validate(write(tmp_path / 'bad.tif', **options), ref)['format_valid']


def test_mask_cannot_hide_error(tmp_path):
    ref = write(tmp_path / 'ref.tif')
    bad = write(tmp_path / 'bad.tif')
    with rasterio.open(bad, 'r+') as d:
        mask = np.full((3, 4), 255, dtype='uint8'); mask[0, 0] = 0
        d.write_mask(mask)
    assert not audit.validate(bad, ref)['format_valid']


def test_complex_raster_rejected(tmp_path):
    ref = write(tmp_path / 'ref.tif')
    bad = write(tmp_path / 'bad.tif', dtype='complex64')
    assert not audit.validate(bad, ref)['format_valid']


def test_invalid_template_rejected(tmp_path):
    ref = write(tmp_path / 'ref.tif', count=2)
    good = write(tmp_path / 'good.tif')
    assert not audit.validate(good, ref)['format_valid']
