#!/usr/bin/env python3
"""Posthoc audit for a prior published AFTER the frozen experiment.

Not another experiment or a retroactive pre-placement check: the already-frozen
label-blind surface is rebuilt from the pinned stack only for a *newly emerged*
prior, and the existing TIFF is compared byte-for-byte. No new TIFF is written.
Records the timing distinction so the original 29-raster run card stays immutable.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import rasterio

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / 'src', ROOT / 'vendor', ROOT / 'scripts'):
    sys.path.insert(0, str(p))

from gems57 import uniqueness  # noqa: E402
from gems88.fabric_dislocation import build_surface  # noqa: E402
from run_fabric_dislocation import digest, preplacement_surface_rhos, verify_sources  # noqa: E402


def audit_new_prior(prior, *, source_label='concurrently merged public prior'):
    prior = Path(prior).resolve()
    if not prior.is_file() or not prior.is_relative_to(ROOT):
        raise ValueError('new prior must be a public, repository-local GeoTIFF')
    gd = verify_sources()
    frozen = json.loads((ROOT / 'evidence/fabric_dislocation_uniqueness.json').read_text())
    card = json.loads((ROOT / 'registry/fabric_dislocation_run_card.json').read_text())
    sha = digest(prior)
    if sha == card['raster_sha256'] or sha in {r['sha256'] for r in frozen['final_dots']['rows']}:
        raise ValueError('not a newly published prior relative to the frozen experiment')
    relpath = str(prior.relative_to(ROOT))
    with rasterio.open(ROOT / 'data/training_features.tif') as features:
        surface, _, _ = build_surface(features.read(2), features.read(13), gd.footprint)
    index = dict(complete_accessible_scan=True, errors=[], rasters=[
        dict(repo_first=source_label, sources=[prior.name], cache_file=relpath, sha256=sha)])
    posthoc_surface = preplacement_surface_rhos(surface, gd, index)[0]
    with rasterio.open(ROOT / 'data/bridge/sample_submission.tif') as ref:
        expected = (ref.shape, ref.crs, ref.transform)
    result = uniqueness.compare_to_registry(ROOT / card['file'], index, gd.footprint,
                                             include_reverse=False, expected_grid=expected)
    if result['registry_rasters_checked'] != 1 or result['candidate_file_sha256'] != card['raster_sha256']:
        raise ValueError('failed comparison of frozen TIFF with new prior')
    final = result['rows'][0]
    final['file'] = relpath
    return dict(schema='gems88.posthoc-registry-extension.v1',
                date_utc=datetime.now(timezone.utc).isoformat(),
                reason='A prior was published on main after this candidate was already emitted.',
                timing='Rebuilt the frozen structural surface for retrospective correlation; the original 29 checks happened before dot placement, but this NEW comparison could only be made AFTER placement. No new experiment or TIFF.',
                initial_prior_count=len(frozen['final_dots']['rows']),
                new_prior=relpath, new_prior_sha256=sha,
                candidate_sha256=card['raster_sha256'],
                frozen_surface_posthoc=posthoc_surface,
                final_dots_posthoc=final,
                remains_blocked=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prior', type=Path, help='newly published public prior inside repository')
    parser.add_argument('--source-label', default='GEMSDOE88/TILTZERO PR #59')
    args = parser.parse_args()
    report = audit_new_prior(args.prior, source_label=args.source_label)
    text = json.dumps(report, indent=2, allow_nan=False) + '\n'
    for path in (ROOT / 'evidence/postmerge_tiltzero_audit.json',
                 ROOT / 'docs/data/postmerge_tiltzero_audit.json'):
        path.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
