"""A bounded README sample is not a winner census, new model or release gate."""
import copy
import hashlib
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

ROOT = Path(__file__).resolve().parents[1]


def test_first_local_tiff_has_a_bounded_safe_discovery_rule():
    assert sample.first_local_tiff(b'look docs/downloads/research/first.tif and docs/research/second.tiff') == 'docs/downloads/research/first.tif'
    assert sample.first_local_tiff(b'https://github.com/other/repo/blob/main/docs/downloads/external.tif') is None
    assert sample.first_local_tiff(b'./docs/downloads/relative-prefix.tif') is None
    assert sample.first_local_tiff(b'submissions/not-in-scope.tif') is None
    assert sample.first_local_tiff(b' ' * sample.README_PREFIX_BYTES + b'docs/downloads/later.tif') is None
    with pytest.raises(ValueError):
        sample.first_local_tiff(b'docs/downloads/../escape.tif')


def test_atomic_public_snapshot_is_world_readable(tmp_path):
    import stat
    path = tmp_path / 'published.json'
    sample.freshness.write_atomic(path, {'ok_to_submit': False})
    assert json.loads(path.read_text())['ok_to_submit'] is False
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_pinned_synthetic_byte_sample_and_fail_closed_network(monkeypatch, tmp_path):
    shape = (8, 8)
    crs = CRS.from_epsg(32611)
    transform = from_origin(0, 800, 100, 100)
    bridge = tmp_path / 'data/bridge'
    bridge.mkdir(parents=True)

    def write_raster(path, values):
        with rasterio.open(path, 'w', driver='GTiff', width=shape[1], height=shape[0], count=1,
                           dtype='float32', crs=crs, transform=transform) as ds:
            ds.write(values.astype('float32'), 1)
        return path.read_bytes()

    write_raster(bridge / 'sample_submission.tif', np.zeros(shape))
    witness = tmp_path / 'witness.tif'
    write_raster(witness, np.ones(shape))
    candidate = np.zeros(shape)
    candidate[2, 3] = 0.75
    raw = write_raster(tmp_path / 'sample.tif', candidate)
    empty = write_raster(tmp_path / 'empty.tif', np.zeros(shape))
    revisions = {'checked_at_utc': '2026-10-27T23:00:00Z',
                 'sites': [{'site': name, 'current_head': f'{i:040x}'} for i, name in enumerate(sample.freshness.SITES, 1)]}
    monkeypatch.setattr(sample, 'load_freshness', lambda *args: (revisions, 'b' * 64))
    monkeypatch.setattr(sample, 'pinned', lambda root, rel, sha: witness)
    monkeypatch.setattr(sample.grid, 'load_grid', lambda _: SimpleNamespace(
        shape=shape, crs=crs, transform=transform, footprint=np.ones(shape, dtype=bool)))

    def fetch(site, head, path, limit):
        if site == 'GEMSDOE28':
            raise URLError('secret-token-in-upstream-error')
        if path == 'README.md':
            return b'no locally cited file' if site == 'GEMSDOE27' else b'docs/downloads/first.tif'
        return empty if site == 'GEMSDOE25' else raw

    report = sample.collect(tmp_path, fetch=fetch, checked_at='2026-10-27T23:01:00Z')
    assert report['counts'] == {'DUPLICATE_STOP': 6, 'NOT_CLEARED': 0, 'INVALID_RASTER': 1,
                                'NOT_DISCOVERED': 1, 'UNKNOWN': 1}
    first = report['rows'][0]
    assert first['sha256'] == hashlib.sha256(raw).hexdigest()
    assert first['format_pass'] is True and first['positive_inside_footprint'] == 1
    assert first['overlap_3px'] == 1 and first['decision'] == 'DUPLICATE_STOP'
    assert all(row['ok_to_submit'] is False for row in report['rows'])
    assert report['ok_to_submit'] is report['approved_for_weekly_slot'] is False
    assert 'secret-token-in-upstream-error' not in json.dumps(report)
    assert report['new_tiffs_generated'] == report['weekly_slots_used'] == 0
    with pytest.raises(ValueError, match='expired'):
        sample.collect(tmp_path, fetch=fetch, checked_at='2026-10-29T00:00:00Z')


@pytest.mark.parametrize('mutation', ['approval', 'head', 'threshold', 'count', 'path', 'sha', 'format', 'unmeasured'])
def test_stored_observations_reject_inconsistent_or_unsafe_reports(mutation):
    report = json.loads((ROOT / 'evidence/focus_current_samples_92a5fb8c.json').read_text())
    revisions, digest = sample.load_freshness(ROOT, ROOT / 'evidence/focus_freshness_92a5fb8c.json')
    sample.validate_report(report, revisions, digest)
    row = report['rows'][0]
    if mutation == 'approval': report['ok_to_submit'] = True
    elif mutation == 'head': row['head'] = 'a' * 40
    elif mutation == 'threshold': row['overlap_3px'] = 0.70
    elif mutation == 'count': report['counts']['DUPLICATE_STOP'] = 0
    elif mutation == 'path': row['source_url'] = 'https://example.com/forged.tif'
    elif mutation == 'sha': row['sha256'] = 'bad'
    elif mutation == 'format': row['format_pass'] = 'PASS'
    else: report['rows'][3]['overlap_3px'] = 0
    with pytest.raises(ValueError):
        sample.validate_report(report, revisions, digest)


def test_report_is_reproducible_offline_and_preserves_historical_snapshot():
    snapshot = ROOT / 'evidence/focus_freshness_92a5fb8c.json'
    report_path = ROOT / 'evidence/focus_current_samples_92a5fb8c.json'
    revisions, digest = sample.load_freshness(ROOT, snapshot)
    report = json.loads(report_path.read_text())
    sample.validate_report(report, revisions, digest)
    assert report['counts']['DUPLICATE_STOP'] == 8
    assert report['counts']['NOT_DISCOVERED'] == 1
    assert sample.main(['--check']) == 0


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_browser_rejects_tampering_and_expires_snapshots():
    script = r"""
const fs=require('fs'), assert=require('node:assert/strict');
const {assess}=require('./docs/assets/focus-current-samples.js');
const report=JSON.parse(fs.readFileSync('evidence/focus_current_samples_92a5fb8c.json'));
const revisions=JSON.parse(fs.readFileSync('evidence/focus_freshness_92a5fb8c.json'));
const now=Date.parse(report.checked_at_utc)+1000;
assert.equal(assess(report,revisions,now).counts.DUPLICATE_STOP,8);
assert.equal(assess(report,revisions,now+13*3600000).expired,true);
for (const corrupt of [
  r=>r.ok_to_submit=true,
  r=>r.rows[0].head='a'.repeat(40),
  r=>r.rows[0].overlap_3px=.70,
  r=>r.rows[0].source_url='https://example.com/evil',
  r=>r.rows[0].format_pass='PASS',
  r=>r.rows[3].positive_inside_footprint=1,
  r=>r.counts.DUPLICATE_STOP=0,
]) {const changed=structuredClone(report); corrupt(changed); assert.throws(()=>assess(changed,revisions,now));}
const later=structuredClone(revisions); later.sites[0].current_head='a'.repeat(40);
assert.throws(()=>assess(report,later,now));
"""
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True)
