#!/usr/bin/env python3
"""Prove the literal registry blocker before spending another experiment.

Reuses shared grid/overlap/format tools. One witness is sufficient to reject,
but never sufficient to certify registry-wide uniqueness. No raster is generated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'vendor'), str(ROOT / 'src'), str(ROOT / 'scripts')]
import numpy as np
import rasterio
from gems57 import grid, uniqueness
from gems88.gate import portal_validate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def coverage_proof(footprint, witness):
    if footprint.shape != witness.shape or not footprint.any():
        raise ValueError('Empty or mismatched footprint')
    support = np.isfinite(witness) & (witness > 0)
    # Direct coverage is a stronger sufficient condition than 3px halo coverage.
    covered = int(np.count_nonzero(support & footprint))
    total = int(footprint.sum())
    return {'footprint_pixels': total, 'directly_covered_pixels': covered,
            'all_nonempty_in_footprint_candidates_blocked': covered == total,
            'reason': 'Every allowed dot already lies on positive registry support' if covered == total
                      else 'This sufficient proof is inconclusive; run full registry tests'}


def inspect(root=ROOT):
    root = Path(root)
    for rel, want in [('data/bridge/sample_submission.tif', grid.SHA256_SAMPLE_SUBMISSION),
                      ('data/bridge/existing_faults.tif', grid.SHA256_EXISTING_FAULTS)]:
        if sha(root / rel) != want:
            raise ValueError(f'Grid pin mismatch: {rel}')
    gd = grid.load_grid(root / 'data/bridge')
    rel = 'data/registry/dense_17gemdoe.tif'
    inventory = json.loads((root / 'registry/inventory.json').read_text())
    pins = [r['sha256'] for r in inventory['rasters'] if r['cache_file'] == rel]
    if pins != [sha(root / rel)]:
        raise ValueError('Witness pin mismatch')
    with rasterio.open(root / rel) as ds:
        if (ds.shape, ds.crs, ds.transform) != (gd.shape, gd.crs, gd.transform):
            raise ValueError('Witness grid mismatch')
        witness = ds.read(1)
    proof = coverage_proof(gd.footprint, witness)
    card = json.loads((root / 'registry/mdps88_run_card.json').read_text())
    tif = root / card['raster']['file']
    if sha(tif) != card['raster_sha256']:
        raise ValueError('Candidate pin mismatch')
    sample = root / 'data/bridge/sample_submission.tif'
    v = portal_validate(tif, sample, footprint=gd.footprint)
    z = portal_validate(root / card['raster']['zip'], sample, footprint=gd.footprint)
    with rasterio.open(tif) as ds:
        a = ds.read(1)
    overlap = uniqueness.dot_overlap(a, witness, 3)
    duplicate = overlap > uniqueness.OVERLAP_LIMIT
    return {
        'schema': 'gems88.literal-protocol-audit.v1', 'date_utc': '2026-10-24',
        'hypothesis': 'Existing MDPS-88 uniqueness claim fails the binding literal rule',
        'mechanism': 'Hash-pinned footprint coverage proof plus shared exact dot-overlap measurement',
        'named_non_fault_process': 'Lake Lahontan shoreline benches (existing MDPS geological confounder)',
        'new_experiments': 0, 'new_raster_generated': False, 'slots_used': 0,
        'preplacement_feasibility': proof,
        'holdout': card['holdout'], 'holdout_provenance': 'Historical evidence, not retrained in this audit',
        'correlation_overlap_vs_registry': {
            'witness': rel, 'witness_sha256': pins[0], 'final_overlap_3px': overlap,
            'duplicate': duplicate, 'registry_complete': False,
            'scope': 'One sufficient rejection witness; not a new full-registry certification',
            'surface_rho': None, 'surface_rho_reason': 'No new surface: stop at universal feasibility blocker'},
        'raster_sha256': sha(tif), 'artifact': card['raster']['file'],
        'validator_output': v, 'zip_validator_output': z,
        'submission_name': card['submission_name'],
        'note': 'Existing MDPS-88 audit: literal registry duplicate; format check only; DO NOT SUBMIT.',
        'ok_to_download': bool(v['ok'] and z['ok']), 'ok_to_submit': False,
        'verdict': 'negative', 'stop_required': duplicate,
        'organizer_confirmed_score': None,
        'limitations': ['No new holdout or feature-canary run', 'No current portal receipt or weekly-cap verification',
                        'No unique submission can satisfy the current all-raster rule while this witness remains registered']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--require-submit', action='store_true')
    args = ap.parse_args()
    report = inspect()
    for rel in ('evidence/literal_protocol_audit_20261024.json', 'docs/data/literal_protocol_audit.json'):
        (ROOT / rel).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: report[k] for k in ('preplacement_feasibility', 'ok_to_download', 'ok_to_submit', 'verdict')}, indent=2))
    if not report['ok_to_download']:
        return 1
    return 2 if args.require_submit else 0


if __name__ == '__main__':
    raise SystemExit(main())
