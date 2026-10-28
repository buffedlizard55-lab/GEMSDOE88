"""Saved-byte diagnostics distinguish exterior NaN from finite range violations."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from urllib.error import URLError

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from scripts import focus_current_samples as sample


@pytest.fixture
def sampled_fixture(tmp_path, monkeypatch):
    shape = (8, 8)
    transform = from_origin(0, 800, 100, 100)
    crs = CRS.from_epsg(32611)
    fp = np.ones(shape, dtype=bool)
    fp[0, :] = False
    bridge = tmp_path / 'data/bridge'
    bridge.mkdir(parents=True)

    def write(path, values, nodata=None, *, affine=None, bands=1):
        with rasterio.open(path, 'w', driver='GTiff', width=values.shape[1], height=values.shape[0],
                           count=bands, dtype='float32', crs=crs, transform=affine or transform, nodata=nodata) as ds:
            for index in range(1, bands + 1):
                ds.write(values.astype('float32'), index)
        return path.read_bytes()

    reference = np.zeros(shape, dtype='float32')
    reference[~fp] = np.nan
    write(bridge / 'sample_submission.tif', reference, nodata=np.nan)
    witness = tmp_path / 'witness.tif'
    write(witness, np.ones(shape))

    good = np.zeros(shape, dtype='float32')
    good[1, 1] = 1
    good_raw = write(tmp_path / 'good.tif', good)
    outside_nan = good.copy()
    outside_nan[~fp] = np.nan
    outside_raw = write(tmp_path / 'outside.tif', outside_nan, nodata=np.nan)
    range_bad = good.copy()
    range_bad[2, 2] = 1.1
    range_raw = write(tmp_path / 'range.tif', range_bad)
    wrong_shape = write(tmp_path / 'wrong.tif', np.zeros((7, 8)))
    wrong_transform = write(tmp_path / 'shifted.tif', good, affine=from_origin(50, 800, 100, 100))
    multiple_bands = write(tmp_path / 'multiband.tif', good, bands=2)

    revisions = {'checked_at_utc': '2026-10-28T10:00:00Z',
                 'sites': [{'site': name, 'current_head': f'{i:040x}'}
                           for i, name in enumerate(sample.freshness.SITES, 1)]}
    monkeypatch.setattr(sample, 'load_freshness', lambda *args: (revisions, 'b' * 64))
    monkeypatch.setattr(sample, 'pinned', lambda root, rel, sha: witness)
    monkeypatch.setattr(sample.grid, 'load_grid', lambda _: SimpleNamespace(
        shape=shape, crs=crs, transform=transform, footprint=fp))

    def fetch(site, head, path, limit):
        if site == 'GEMSDOE30':
            raise URLError('redacted')
        if path == 'README.md':
            return b'docs/downloads/example.tif'
        return {'GEMSDOE24': outside_raw, 'GEMSDOE25': range_raw,
                'GEMSDOE28': wrong_shape, 'GEMSDOE33': wrong_transform,
                'GEMSDOE36': multiple_bands}.get(site, good_raw)

    report = sample.collect(tmp_path, fetch=fetch, checked_at='2026-10-28T10:01:00Z')
    return report, revisions


def test_exterior_nan_is_not_called_a_finite_range_violation(sampled_fixture):
    report, _ = sampled_fixture
    assert report['schema'] == sample.SCHEMA
    row = report['rows'][0]
    assert row['decision'] == 'DUPLICATE_STOP' and row['format_pass'] is False
    assert row['format_pixel_counts'] == {
        'inside_pixels': 56, 'outside_pixels': 8, 'inside_nonfinite': 0,
        'outside_nonfinite': 8, 'inside_finite_out_of_range': 0,
        'outside_finite_out_of_range': 0, 'outside_finite_nonzero': 0,
    }
    assert 'strict.all_finite' in row['format_failures']
    assert 'strict.no_nodata_sentinel' in row['format_failures']
    assert 'footprint.no_nan_inside' not in row['format_failures']
    assert row['overlap_3px'] == 1.0
    assert row['ok_to_submit'] is False


def test_interior_bad_values_wrong_grids_and_offline_are_not_cleared(sampled_fixture):
    report, _ = sampled_fixture
    rows = {row['site']: row for row in report['rows']}
    bad = rows['GEMSDOE25']
    assert bad['decision'] == 'INVALID_RASTER' and bad['format_pass'] is False
    assert bad['format_pixel_counts']['inside_finite_out_of_range'] == 1
    assert bad['format_pixel_counts']['inside_nonfinite'] == 0
    assert 'footprint.range_0_1' in bad['format_failures']
    assert rows['GEMSDOE27']['format_pass'] is True
    assert rows['GEMSDOE27']['format_failures'] == []
    assert rows['GEMSDOE28']['format_pass'] is False
    assert rows['GEMSDOE28']['format_pixel_counts'] is None
    for site in ('GEMSDOE33', 'GEMSDOE36'):
        assert rows[site]['decision'] == 'INVALID_RASTER'
        assert rows[site]['format_pixel_counts'] is None
    assert 'footprint.transform_match' in rows['GEMSDOE33']['format_failures']
    assert 'footprint.single_band' in rows['GEMSDOE36']['format_failures']
    assert rows['GEMSDOE30']['decision'] == 'UNKNOWN'
    assert rows['GEMSDOE30']['format_failures'] is None
    assert rows['GEMSDOE30']['format_pixel_counts'] is None
    assert all(row['ok_to_submit'] is False for row in rows.values())
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize('mutate', [
    lambda r: r['rows'][0].update(format_failures=[]),
    lambda r: r['rows'][0]['format_failures'].append('arbitrary upstream text'),
    lambda r: r['rows'][0]['format_pixel_counts'].update(inside_nonfinite=57),
    lambda r: r['rows'][0]['format_pixel_counts'].update(outside_nonfinite=-1),
    lambda r: r['rows'][0]['format_pixel_counts'].update(inside_pixels=2**53),
    lambda r: r['rows'][0]['format_pixel_counts'].update(outside_finite_out_of_range=2),
    lambda r: r['rows'][0].update(format_pass=True),
    lambda r: r['rows'][2].update(format_pixel_counts=None),
    lambda r: r['rows'][4].update(format_failures=[]),
])
def test_tampered_or_contradictory_format_evidence_fails_closed(sampled_fixture, mutate):
    report, revisions = sampled_fixture
    changed = copy.deepcopy(report)
    mutate(changed)
    with pytest.raises(ValueError):
        sample.validate_report(changed, revisions, 'b' * 64)


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_browser_displays_diagnostic_counts_and_rejects_tampering(sampled_fixture):
    report, revisions = sampled_fixture
    # The browser validates the public freshness envelope too; the test fixture
    # models only the fields this reader consumes, not a GitHub measurement.
    revisions.update(schema='gems88.focus-freshness.v1', ok_to_submit=False,
                     approved_for_weekly_slot=False)
    script = r"""
const fs = require('fs'), assert = require('node:assert/strict');
const {assess, describeFormat} = require('./docs/assets/focus-current-samples.js');
const [report, revisions] = JSON.parse(fs.readFileSync(0, 'utf8'));
const now = Date.parse(report.checked_at_utc) + 1000;
assert.equal(assess(report, revisions, now).rows.length, 9);
const label = describeFormat(report.rows[0], report.schema);
assert.match(label, /non-finite inside\/outside: 0\/8/);
assert.match(label, /finite out-of-range inside\/outside: 0\/0/);
for (const change of [
  r => r.rows[0].format_failures = [],
  r => r.rows[0].format_failures.push('unexpected'),
  r => r.rows[0].format_pixel_counts.inside_nonfinite = 57,
  r => r.rows[0].format_pixel_counts.outside_nonfinite = -1,
  r => r.rows[2].format_pixel_counts = null,
  r => r.rows[4].format_failures = [],
]) {
  const bad = structuredClone(report); change(bad);
  assert.throws(() => assess(bad, revisions, now));
}
"""
    result = subprocess.run(['node', '-e', script], cwd=Path(__file__).resolve().parents[1],
                            input=json.dumps([report, revisions]), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_legacy_dated_snapshot_remains_valid():
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / 'evidence/focus_current_samples_92a5fb8c.json').read_text())
    revisions, digest = sample.load_freshness(root, root / 'evidence/focus_freshness_92a5fb8c.json')
    assert report['schema'] == sample.LEGACY_SCHEMA
    sample.validate_report(report, revisions, digest)
