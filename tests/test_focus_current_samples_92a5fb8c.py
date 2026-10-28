"""A bounded README sample is not a winner census, new model or release gate."""
from datetime import datetime, timedelta
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
    # The predecessor's 16 KiB cutoff missed eligible citations farther down.
    assert sample.first_local_tiff(b' ' * 16_384 + b'docs/downloads/later.tif') == 'docs/downloads/later.tif'
    assert sample.first_local_tiff(b' ' * sample.README_PREFIX_BYTES + b'docs/downloads/later.tif') is None
    with pytest.raises(ValueError):
        sample.first_local_tiff(b'docs/downloads/../escape.tif')
    with pytest.raises(UnicodeDecodeError):
        sample.first_local_tiff(b'invalid-utf8-\xff')


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

    footprint = np.ones(shape, dtype=bool)
    footprint[0, 0] = False
    template = np.zeros(shape)
    template[0, 0] = np.nan
    write_raster(bridge / 'sample_submission.tif', template)
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
        shape=shape, crs=crs, transform=transform, footprint=footprint))

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
    assert report['schema'] == 'gems88.focus-current-samples.v2'
    assert first['readme_sha256'] == hashlib.sha256(b'docs/downloads/first.tif').hexdigest()
    assert first['readme_bytes'] == len(b'docs/downloads/first.tif')
    assert first['format_failures'] == []
    assert first['sha256'] == hashlib.sha256(raw).hexdigest()
    assert first['format_pass'] is True and first['positive_inside_footprint'] == 1
    assert first['overlap_3px'] == 1 and first['decision'] == 'DUPLICATE_STOP'
    assert all(row['ok_to_submit'] is False for row in report['rows'])
    assert report['ok_to_submit'] is report['approved_for_weekly_slot'] is False
    assert 'secret-token-in-upstream-error' not in json.dumps(report)
    assert report['new_tiffs_generated'] == report['weekly_slots_used'] == 0
    with pytest.raises(ValueError, match='expired'):
        sample.collect(tmp_path, fetch=fetch, checked_at='2026-10-29T00:00:00Z')

    invalid_values = candidate.copy()
    invalid_values[0, 0] = 1.5  # outside footprint: overlap can still be measured
    bad = write_raster(tmp_path / 'bad.tif', invalid_values)
    invalid_inside = candidate.copy()
    invalid_inside[2, 3] = 1.5
    bad_inside = write_raster(tmp_path / 'bad-inside.tif', invalid_inside)

    def mixed_failures(site, head, path, limit):
        if site == 'GEMSDOE24' and path == 'README.md':
            return b'invalid-utf8-\xff'
        if site == 'GEMSDOE28' and path == 'README.md':
            return b'x' * (limit + 1)  # even an injected fetcher must enforce the README bound
        if site == 'GEMSDOE31' and path != 'README.md':
            return b'not a GeoTIFF'  # fetched and hashed, but not a measured raster
        if site == 'GEMSDOE30' and path != 'README.md':
            return bad  # grid matches, so format and overlap are separate observations
        if site == 'GEMSDOE32' and path != 'README.md':
            raise ValueError('oversized raster')
        if site == 'GEMSDOE33' and path != 'README.md':
            return bad_inside
        return fetch(site, head, path, limit)

    changed = sample.collect(tmp_path, fetch=mixed_failures, checked_at='2026-10-27T23:01:00Z')
    by_site = {r['site']: r for r in changed['rows']}
    assert by_site['GEMSDOE24']['decision'] == 'UNKNOWN' and by_site['GEMSDOE24']['readme_sha256']
    assert by_site['GEMSDOE28']['decision'] == 'UNKNOWN' and by_site['GEMSDOE28']['readme_sha256'] is None
    assert by_site['GEMSDOE32']['decision'] == 'UNKNOWN' and by_site['GEMSDOE32']['path']
    assert by_site['GEMSDOE31']['decision'] == 'INVALID_RASTER' and by_site['GEMSDOE31']['sha256']
    assert by_site['GEMSDOE31']['format_failures'] == ['raster_decode_or_grid_error']
    assert by_site['GEMSDOE30']['decision'] == 'DUPLICATE_STOP'
    assert by_site['GEMSDOE30']['format_pass'] is False
    assert {'values_in_0_1', 'range_0_1'} <= set(by_site['GEMSDOE30']['format_failures'])
    assert by_site['GEMSDOE33']['decision'] == 'INVALID_RASTER'
    assert by_site['GEMSDOE33']['overlap_3px'] is None
    assert {'values_in_0_1', 'range_0_1'} <= set(by_site['GEMSDOE33']['format_failures'])


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
    # CI validates the immutable fixture without calling it fresh.
    assert sample.main(['--check', '--structural-only']) == 0


def test_current_cli_age_gate_rejects_expired_and_future_snapshots():
    report = json.loads((ROOT / 'evidence/focus_current_samples_5a295887.json').read_text())
    revisions, _ = sample.load_freshness(ROOT, ROOT / 'evidence/focus_freshness_5a295887.json')
    checked = datetime.fromisoformat(report['checked_at_utc'].replace('Z', '+00:00'))
    sample.validate_current_age(report, revisions, now=checked + timedelta(seconds=1))
    with pytest.raises(ValueError, match='expired'):
        sample.validate_current_age(report, revisions, now=checked + timedelta(hours=13))
    with pytest.raises(ValueError, match='future'):
        sample.validate_current_age(report, revisions, now=checked - timedelta(minutes=10))


@pytest.mark.parametrize('mutation', ['legacy-live', 'readme-hash', 'readme-size', 'diagnostics', 'scope', 'binding', 'age'])
def test_v2_rejects_bad_provenance_and_legacy_cannot_be_current(mutation):
    report = json.loads((ROOT / 'evidence/focus_current_samples_5a295887.json').read_text())
    revisions, digest = sample.load_freshness(ROOT, ROOT / 'evidence/focus_freshness_5a295887.json')
    sample.validate_report(report, revisions, digest, allow_legacy=False)
    if mutation == 'legacy-live': report['schema'] = sample.LEGACY_SCHEMA
    elif mutation == 'readme-hash': report['rows'][0]['readme_sha256'] = None
    elif mutation == 'readme-size': report['rows'][0]['readme_bytes'] = sample.README_LIMIT + 1
    elif mutation == 'diagnostics': report['rows'][0]['format_failures'] = ['values_in_0_1']
    elif mutation == 'scope': report['scope'] = 'complete registry clearance'
    elif mutation == 'binding': report['head_snapshot_sha256'] = '0' * 64
    else: report['checked_at_utc'] = '2026-10-29T23:33:42Z'
    with pytest.raises(ValueError):
        sample.validate_report(report, revisions, digest, allow_legacy=False)


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_browser_rejects_tampering_and_expires_snapshots():
    script = r"""
const fs=require('fs'), crypto=require('crypto'), assert=require('node:assert/strict');
const {assess}=require('./docs/assets/focus-current-samples.js');
const report=JSON.parse(fs.readFileSync('evidence/focus_current_samples_5a295887.json'));
const raw=fs.readFileSync('evidence/focus_freshness_5a295887.json');
const revisions=JSON.parse(raw);
const sha=crypto.createHash('sha256').update(raw).digest('hex');
const now=Date.parse(report.checked_at_utc)+1000;
assert.equal(assess(report,revisions,now,sha).counts.DUPLICATE_STOP,9);
assert.equal(assess(report,revisions,now+13*3600000,sha).expired,true);
for (const corrupt of [
  r=>r.ok_to_submit=true,
  r=>r.rows[0].head='a'.repeat(40),
  r=>r.rows[0].overlap_3px=.70,
  r=>r.rows[0].source_url='https://example.com/evil',
  r=>r.rows[0].format_pass='PASS',
  r=>r.rows[0].readme_sha256=null,
  r=>r.rows[0].format_failures=['values_in_0_1'],
  r=>r.scope='complete registry audit',
  r=>r.counts.DUPLICATE_STOP=0,
]) {const changed=structuredClone(report); corrupt(changed); assert.throws(()=>assess(changed,revisions,now,sha));}
const later=structuredClone(revisions); later.sites[0].current_head='a'.repeat(40);
assert.throws(()=>assess(report,later,now,sha));
const whitespaceSha=crypto.createHash('sha256').update(raw).update('\n').digest('hex');
assert.throws(()=>assess(report,revisions,now,whitespaceSha));
const legacy=JSON.parse(fs.readFileSync('evidence/focus_current_samples_92a5fb8c.json'));
assert.throws(()=>assess(legacy,revisions,now,sha));
"""
    subprocess.run(['node', '-e', script], cwd=ROOT, check=True)
