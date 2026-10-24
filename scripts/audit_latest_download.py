"""Reopen the latest advertised TDKL bytes; never train, emit, or approve a slot."""
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
from scripts.audit_literal_protocol import pinned, sha
from scripts.restore_inputs import VALIDATION_GROUPS
from scripts.validate_artifact import validate_artifact
from gems57 import grid, uniqueness
import numpy as np
import rasterio


def inspect():
    card = json.loads((ROOT / 'registry/tdkl88_run_card.json').read_text())
    sample = pinned(ROOT, 'data/bridge/sample_submission.tif', grid.SHA256_SAMPLE_SUBMISSION)
    group = next(g for g in VALIDATION_GROUPS if g[0] == '17GEMSDOE-witness')
    _, relative, digest = group[3][0]
    witness = pinned(ROOT, relative, digest)
    tif = pinned(ROOT, card['raster']['file'], card['raster_sha256'])
    archive = pinned(ROOT, card['raster']['zip_file'], card['raster']['zip_sha256'])
    validation = validate_artifact(tif, sample)
    if not validation['ok']:
        raise ValueError('written-byte format failed')
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError('ZIP must contain exactly the identical TIFF')
    with rasterio.open(sample) as src:
        footprint = np.isfinite(src.read(1)) & (src.read_masks(1) > 0)
    with rasterio.open(witness) as src:
        support = np.isfinite(src.read(1)) & (src.read(1) > 0) & footprint
    with rasterio.open(tif) as src:
        dots = src.read(1) > 0
    overlap = uniqueness.dot_overlap(dots, support)
    if not dots.any() or overlap <= .70:
        raise ValueError('expected literal duplicate no longer reproduced; review required')
    return dict(schema='gems88.latest-download-audit.v1', date_utc='2026-10-24',
                hypothesis=card['hypothesis'], mechanism=card['mechanism'],
                named_non_fault_process=card['named_non_fault_mimic'],
                holdout=card['holdout_dti'],
                holdout_provenance='Historical fold-refit results; NOT retrained in this audit',
                correlation_overlap_vs_registry=dict(final_overlap_3px=overlap,
                    witness_sha256=sha(witness),
                    scope='One counterexample suffices to reject; not a complete fleet scan',
                    surface='No new surface: stopped before training or placement'),
                raster=card['raster']['file'], raster_sha256=sha(tif),
                validator_output=validation, zip_one_identical_tif=True,
                submission_name=card['submission_name'], submission_note=card['submission_note'],
                ok_to_download_for_research=True, ok_to_submit=False,
                verdict='negative', decision='DUPLICATE_STOP',
                experiments_run=0, new_rasters_generated=0, slots_used=0,
                organizer_confirmed_score=None)


if __name__ == '__main__':
    # Failure raises and exits nonzero; never reuse a stale success report.
    print(json.dumps(inspect(), indent=2, allow_nan=False))
