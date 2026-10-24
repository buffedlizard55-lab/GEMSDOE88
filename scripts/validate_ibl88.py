#!/usr/bin/env python3
"""Independent saved-byte and literal-uniqueness audit for the IBL-88 research TIFF.

This validates local TIFF/ZIP format and the user's strict all-registry 3-pixel
rule. A duplicate is a successful audit finding but blocks submission. Exit:
0 = bytes checked (scientific verdict may be negative); 1 = audit error;
2 = --require-submit requested but the candidate is not cleared.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def audit(root: Path = ROOT) -> dict:
    card = json.loads((root / 'registry/ibl88_run_card.json').read_text())
    sub = card['submission']
    tif = root / sub['file']
    archive = root / sub['zip_file']
    sample = root / 'data/bridge/sample_submission.tif'
    catalogue = root / 'data/bridge/existing_faults.tif'
    witness_path = root / 'data/registry/dense_17gemdoe.tif'
    report = {'evidence_class': 'INDEPENDENT-AUDIT (saved bytes + literal registry rule)',
              'file': str(tif.relative_to(root)), 'checks': {}, 'failures': []}
    c = report['checks']
    c['tif_sha256'] = sha(tif)
    c['tif_sha256_matches_run_card'] = c['tif_sha256'] == sub['sha256']
    c['zip_sha256'] = sha(archive)
    c['zip_sha256_matches_run_card'] = c['zip_sha256'] == sub['zip_sha256']
    with rasterio.open(sample) as ds:
        sample_arr = ds.read(1)
        sample_meta = (ds.height, ds.width, str(ds.crs), tuple(ds.transform)[:6])
    footprint = np.isfinite(sample_arr)
    with rasterio.open(tif) as ds:
        pred = ds.read(1)
        pred_meta = (ds.count, ds.dtypes[0], ds.height, ds.width,
                     str(ds.crs), tuple(ds.transform)[:6], ds.nodata)
    c['single_band_float32'] = pred_meta[0:2] == (1, 'float32')
    c['crs_shape_transform_match'] = pred_meta[2:6] == sample_meta
    c['nodata_none'] = pred_meta[6] is None
    c['all_finite'] = bool(np.isfinite(pred).all())
    c['values_in_0_1'] = bool(np.isfinite(pred).all() and pred.min() >= 0 and pred.max() <= 1)
    dots = pred > 0
    c['positive_pixels'] = int(dots.sum())
    c['positive_count_matches_card'] = c['positive_pixels'] == sub['positive_pixels']
    c['zero_positive_outside_footprint'] = int((dots & ~footprint).sum()) == 0
    with rasterio.open(catalogue) as ds:
        cat = ds.read(1) > 0
    c['zero_positive_on_catalogue'] = int((dots & cat).sum()) == 0
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        payloads = [z.read(name) for name in names]
    c['zip_member_name'] = names[0] if len(names) == 1 else None
    c['zip_single_tif'] = len(names) == 1 and names[0].lower().endswith('.tif')
    c['zip_member_byte_identical'] = len(payloads) == 1 and hashlib.sha256(payloads[0]).hexdigest() == c['tif_sha256']

    with rasterio.open(witness_path) as ds:
        w = ds.read(1)
    witness = np.isfinite(w) & (w > 0)
    witness_dist = distance_transform_edt(~witness)
    overlap = float((witness_dist[dots] <= 3.0).mean()) if dots.any() else 0.0
    c['dense_witness_positive_pixels'] = int(witness.sum())
    c['candidate_dots_within_3px_of_dense_witness'] = int((witness_dist[dots] <= 3.0).sum()) if dots.any() else 0
    c['literal_forward_overlap_3px'] = overlap
    c['literal_duplicate_detected'] = bool(overlap > 0.70)
    c['literal_rule_verdict'] = 'DUPLICATE — stop; no exemptions' if overlap > 0.70 else 'PASS'
    c['preplacement_max_abs_spearman_recorded'] = card['uniqueness']['pre_placement_worst_abs_spearman']
    c['preplacement_spearman_pass'] = abs(c['preplacement_max_abs_spearman_recorded']) <= 0.90

    bool_checks = [k for k, v in c.items() if isinstance(v, bool)]
    failures = [k for k in bool_checks if not c[k]]
    report.update({'sha256': c['tif_sha256'], 'audit_passed': not failures,
                   'failures': failures, 'ok_to_download': not failures and card['ok_to_download'],
                   'ok_to_submit': False, 'strict_duplicate': c['literal_duplicate_detected'],
                   'verdict': 'negative'})
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--require-submit', action='store_true')
    args = ap.parse_args()
    result = audit()
    out = ROOT / 'docs/data/ibl88-validation.json'
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))
    if not result['audit_passed']:
        return 1
    if args.require_submit and (result['strict_duplicate'] or not result['ok_to_submit']):
        print('NOT OK TO SUBMIT (literal 3-px registry duplicate; stop)')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
