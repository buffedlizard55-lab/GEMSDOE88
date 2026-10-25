"""Keep imported SDTL science without accepting an unauthorized policy rewrite."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
from gems57 import uniqueness


def read(relative):
    return json.loads((ROOT / relative).read_text())


def test_withdrawal_preserves_original_tiff_and_scientific_measurements():
    record = read('evidence/sdtl88_clearance_withdrawal_20261025.json')
    assert record == read('docs/data/sdtl88_clearance_withdrawal_20261025.json')
    card = read('registry/sdtl88_run_card.json')
    assert card == read('docs/data/sdtl88_run_card.json')
    assert card['ok_to_submit'] is False and card['verdict'] == 'negative'
    assert card['current_session_experiments_run'] == card['current_session_rasters_generated'] == 0
    assert card['archival_relabel_only'] is True
    assert card['correlation_overlap_vs_registry']['dots_ok'] is False
    assert card['correlation_overlap_vs_registry']['equal_support_binding'] is False
    assert card['correlation_overlap_vs_registry']['literal_worst_forward_overlap'] == 1.0
    science = {key: card[key] for key in record['scientific_fields_unchanged']}
    digest = hashlib.sha256(json.dumps(science, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    assert digest == record['scientific_measurements_sha256'] == card['scientific_measurements_sha256']
    retained = record['retained_artifact']
    path = ROOT / retained['file']
    assert 'DO-NOT-SUBMIT' in path.name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == retained['sha256'] == record['original_artifacts']['tif']['sha256']
    assert path.stat().st_size == record['original_artifacts']['tif']['bytes']
    assert retained['tiff_bytes_unchanged'] is True
    with zipfile.ZipFile(ROOT / retained['zip_file']) as archive:
        assert archive.namelist() == [path.name]
        assert archive.read(path.name) == path.read_bytes()
    assert hashlib.sha256((ROOT / retained['zip_file']).read_bytes()).hexdigest() == retained['zip_sha256']
    sidecar = json.loads(path.with_suffix('.json').read_text())
    assert sidecar['ok_to_submit'] is sidecar['approved_for_weekly_slot'] is sidecar['promoted'] is False
    assert sidecar['sha256'] == retained['sha256']
    assert not list((ROOT / 'docs/downloads').glob('*sdtl88*zeros.tif'))
    assert all((ROOT / name).is_file() for name in record['preserved_research'])


def test_public_v5_stops_even_when_equal_support_diagnostic_passes(tmp_path):
    rng = np.random.default_rng(2)
    allowed = np.ones((60, 60), bool)
    theirs = rng.uniform(0.01, 0.5, allowed.shape).astype(np.float32)
    theirs[40:50, 40:50] = 0.95
    mine = np.zeros(allowed.shape, np.float32)
    mine[8:18:2, 8:18:2] = 1.0
    path = tmp_path / 'synthetic_dense_registry.tif'
    transform = from_origin(243350, 4508550, 100, 100)
    with rasterio.open(path, 'w', driver='GTiff', height=60, width=60, count=1,
                       dtype='float32', crs='EPSG:32611', transform=transform) as out:
        out.write(theirs, 1)
    report = uniqueness.binding_duplicate_decision_v5(mine, [('synthetic', path)], allowed, allowed)
    assert report['worst_equal_support_overlap'] <= 0.70
    assert report['worst_literal_forward_overlap'] == 1.0
    assert report['duplicate'] is report['stop_required'] is True
    assert report['equal_support_binding'] is False
    assert report['verdict'] == 'negative'
    assert report['rows'][0]['fails_overlap'] is True
    assert report['rows'][0]['fails_equal_support_diagnostic'] is False


def test_public_v5_empty_inventory_is_not_clearance():
    mine = np.zeros((12, 12), np.float32)
    mine[5, 5] = 1
    allowed = np.ones(mine.shape, bool)
    report = uniqueness.binding_duplicate_decision_v5(mine, [], allowed, allowed)
    assert report['invalid_measurements'] is report['stop_required'] is True
    assert report['verdict'] == 'negative'


def test_current_canonical_release_is_not_imported_sdtl_clearance():
    release = read('docs/data/current_release.json')
    status = read('docs/status.json')
    assert release['ok_to_submit'] is False and status['ok_to_submit'] is False
    assert 'sdtl88' not in json.dumps(release).lower()
    prereg = read('registry/preregistration_sdtl88.json')
    assert prereg['record_status'] == 'HISTORICAL_PREREGISTRATION_PROTOCOL_INTERPRETATION_SUPERSEDED'
