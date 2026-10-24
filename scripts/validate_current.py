#!/usr/bin/env python3
"""Current-release summary and fail-closed gates.

MRR-COH-88 is the current release. This validator reopens its TIFF and one-TIFF
ZIP, checks the frozen holdout/canary/expanded-registry evidence, and regenerates
the public JSON feed. A unique and format-valid raster remains blocked when it
does not beat the same-split holdout best. No organizer upload/login is attempted.
"""
from __future__ import annotations
import hashlib
import json
import sys
import zipfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'vendor'))
from gems57 import evaluate_holdout, gates, grid, uniqueness, validate  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@lru_cache(maxsize=4)
def release_report(root=ROOT):
    """Independently reconstruct the current MRR-COH-88 release decision."""
    root = Path(root)
    card = json.loads((root / 'registry/mrrcoh88_run_card.json').read_text())
    web_card = json.loads((root / 'docs/data/mrrcoh88_run_card.json').read_text())
    evidence_card = json.loads((root / 'evidence/mrrcoh88_run_card.json').read_text())
    canaries = json.loads((root / 'evidence/mrrcoh88_canaries.json').read_text())
    holdout_doc = json.loads((root / 'evidence/mrrcoh88_holdout.json').read_text())
    unique_doc = json.loads((root / 'evidence/mrrcoh88_final_uniqueness.json').read_text())
    surface_doc = json.loads((root / 'evidence/mrrcoh88_surface_uniqueness.json').read_text())
    registry_doc = json.loads((root / 'registry/mrrcoh88_accessible_registry.json').read_text())
    if card != web_card or card != evidence_card or card.get('lane') != 'MRR-COH-88':
        raise ValueError('current MRR-COH run cards differ or identify the wrong lane')
    tif = (root / card['artifact']).resolve()
    archive = (root / card['zip_artifact']).resolve()
    downloads = (root / 'docs/downloads').resolve()
    if (not tif.is_relative_to(downloads) or not archive.is_relative_to(downloads)
            or 'DO-NOT-SUBMIT' not in tif.name or not tif.is_file() or not archive.is_file()):
        raise ValueError('current artifact is missing, outside downloads, or lacks its safety marker')
    tif_hash, zip_hash = sha(tif), sha(archive)
    if tif_hash != card['raster_sha256'] or zip_hash != card['zip_sha256']:
        raise ValueError('current TIFF/ZIP differs from the run-card hashes')
    receipt = json.loads(tif.with_suffix('.json').read_text())
    if (receipt.get('sha256') != tif_hash or receipt.get('zip_sha256') != zip_hash
            or receipt.get('submission_name') != card['submission_name']
            or receipt.get('note') != card['submission_note']
            or receipt.get('approved_for_weekly_slot') is not False
            or receipt.get('promoted') is not False
            or receipt.get('submission_slots_used') != 0
            or receipt.get('metadata', {}).get('organizer_confirmed_score') is not None
            or len(card['submission_note']) > 140):
        raise ValueError('submission-writer receipt differs from the current run card')
    with zipfile.ZipFile(archive) as zipped:
        if zipped.namelist() != [tif.name] or zipped.read(tif.name) != tif.read_bytes():
            raise ValueError('current ZIP does not contain exactly the byte-identical TIFF')

    sample = root / 'data/bridge/sample_submission.tif'
    catalogue = root / 'data/bridge/existing_faults.tif'
    if sha(sample) != grid.SHA256_SAMPLE_SUBMISSION or sha(catalogue) != grid.SHA256_EXISTING_FAULTS:
        raise ValueError('restored sample/catalogue hash pin failed')
    gd = grid.load_grid(root / 'data/bridge')
    fmt = gates.format_report(tif, sample, footprint=gd.footprint)
    shared = validate.validate(tif, gd.footprint, gd.catalogue)
    independent = validate_artifact(tif, sample)
    if not (fmt['ok'] and shared['all_checks_passed'] and independent['ok']):
        raise ValueError('current TIFF failed an independent saved-byte format check')
    with rasterio.open(tif) as source:
        raster = source.read(1)
    if (not np.isfinite(raster).all() or (raster < 0).any() or (raster > 1).any()
            or (raster[~gd.footprint] != 0).any()):
        raise ValueError('current TIFF contains nonfinite/out-of-range/outside mass')

    holdout_score = card['holdout_dti']
    incumbent = holdout_score['stored_same_split_best']
    if (holdout_score['evaluator_version'] != evaluate_holdout.VERSION
            or holdout_score['withheld_positive_pixels'] != 22893
            or holdout_doc['scores']['candidate']['dti'] != holdout_score['dti']
            or holdout_score['candidate_exceeds_stored_best'] is not False
            or not holdout_score['dti'] < incumbent['dti']
            or not 0 <= holdout_score['ci95'][0] <= holdout_score['dti'] <= holdout_score['ci95'][1] <= 1):
        raise ValueError('current HOLDOUT-DTI evidence is inconsistent')
    stored = json.loads((root / 'registry/holdout_result.json').read_text())['scores']['candidate']
    if incumbent != stored:
        raise ValueError('current incumbent is not the stored same-split best')
    if (not canaries.get('passed') or canaries.get('features_tested') != 8
            or canaries.get('max_symmetric_auc', 1) > .90):
        raise ValueError('feature-alone leakage canary did not pass')

    corr = card['correlation_overlap_vs_registry']
    registry_rows = registry_doc.get('rasters', [])
    if (registry_doc.get('complete_accessible_scan') is not True
            or registry_doc.get('errors') != []
            or len(registry_rows) != corr['registry_rasters_checked']
            or len({row.get('cache_file') for row in registry_rows}) != len(registry_rows)
            or any(len(str(row.get('sha256', ''))) != 64 for row in registry_rows)):
        raise ValueError('expanded registry index is incomplete')
    actual_registry_hashes = []
    for row in registry_rows:
        prior = (root / row.get('cache_file', '')).resolve()
        if (not prior.is_relative_to(root) or not prior.is_file()
                or 'gems88-mrrcoh-persistent-demag-oof' in prior.name):
            raise ValueError(f"unsafe, missing, or self-referential registry row: {row!r}")
        actual = sha(prior)
        if actual != row.get('sha256'):
            raise ValueError(f'expanded-registry hash mismatch: {prior}')
        actual_registry_hashes.append(actual)
    evidence_hashes = [row.get('sha256') for row in unique_doc.get('rows', [])]
    surface_hashes = [row.get('sha256') for row in surface_doc.get('rows', [])]
    if (sorted(actual_registry_hashes) != sorted(evidence_hashes)
            or sorted(actual_registry_hashes) != sorted(surface_hashes)
            or any('error' in row for row in surface_doc.get('rows', []))):
        raise ValueError('expanded-registry index and uniqueness rows differ')
    surface_rhos = [abs(float(row['spearman_full_footprint']))
                    for row in surface_doc['rows']
                    if row.get('spearman_full_footprint') is not None]
    if (not surface_rhos
            or not np.isclose(max(surface_rhos), corr['preplacement_max_abs_spearman'],
                              rtol=0, atol=1e-12)):
        raise ValueError('frozen pre-placement surface evidence is inconsistent')
    if (unique_doc.get('candidate_sha256') != tif_hash
            or len(unique_doc.get('rows', [])) != corr['registry_rasters_checked']
            or unique_doc.get('unique') is not True or corr.get('unique') is not True
            or corr['preplacement_max_abs_spearman'] > corr['rho_limit']
            or corr['final_max_abs_spearman'] > corr['rho_limit']
            or corr['final_max_literal_forward_overlap_dot_fields'] > corr['overlap_limit']
            or corr['final_max_excess_overlap'] > corr['overlap_limit']
            or any(r.get('identical_bytes') or r.get('identical_decoded_predictions')
                   for r in unique_doc['rows'])):
        raise ValueError('expanded-registry uniqueness evidence is incomplete or failing')

    # Recompute final saved-byte comparisons rather than trusting only the
    # experiment's JSON. This is intentionally independent of model fitting.
    measured = uniqueness.compare_to_registry(
        tif, registry_doc, gd.footprint, include_reverse=True,
        expected_grid=(gd.shape, gd.crs, gd.transform),
    )
    measured_rows = [row for row in measured['rows'] if 'error' not in row]
    if (not measured.get('complete_accessible_scan')
            or len(measured_rows) != corr['registry_rasters_checked']
            or len(measured_rows) != len(measured['rows'])):
        raise ValueError('independent final registry remeasurement is incomplete')
    for observed, frozen in zip(measured_rows, unique_doc['rows']):
        for key in ('sha256', 'decoded_sha256', 'their_dots', 'identical_bytes',
                    'identical_decoded_predictions'):
            if observed.get(key) != frozen.get(key):
                raise ValueError(f'independent registry row changed: {key}')
        for key in ('my_dots_within_3px_of_theirs', 'halo_coverage',
                    'their_dots_within_3px_of_mine', 'jaccard_dot_sets'):
            if not np.isclose(observed[key], frozen[key], rtol=0, atol=1e-12):
                raise ValueError(f'independent registry metric changed: {key}')
        old_rho, new_rho = frozen.get('spearman_full_footprint'), observed.get('spearman_full_footprint')
        if not ((old_rho is None and new_rho is None)
                or (old_rho is not None and new_rho is not None
                    and np.isclose(old_rho, new_rho, rtol=0, atol=1e-12))):
            raise ValueError('independent registry Spearman value changed')
    binding = uniqueness.binding_duplicate_decision_v3(measured_rows)
    dot_rows = [row for row in measured_rows
                if int(row['their_dots']) / int(gd.footprint.sum())
                <= uniqueness.DENSE_SUPPORT_FRACTION]
    worst_dot = max(float(row['my_dots_within_3px_of_theirs']) for row in dot_rows)
    if (binding['duplicate']
            or not np.isclose(binding['worst_abs_spearman'], corr['final_max_abs_spearman'],
                              rtol=0, atol=1e-12)
            or not np.isclose(binding['worst_excess_overlap'], corr['final_max_excess_overlap'],
                              rtol=0, atol=1e-12)
            or not np.isclose(binding['worst_literal_forward_overlap'],
                              corr['final_max_literal_forward_overlap_all'], rtol=0, atol=1e-12)
            or not np.isclose(worst_dot,
                              corr['final_max_literal_forward_overlap_dot_fields'], rtol=0, atol=1e-12)):
        raise ValueError('independent representation-aware uniqueness decision changed')
    v = card['validator_output']
    format_valid = bool(v.get('all_checks_passed') and all(v.get(k) for k in (
        'no_nan_inside_footprint', 'all_finite_entire_raster', 'values_in_0_1',
        'crs_shape_transform_match', 'single_band_float32',
        'zip_contains_exactly_one_matching_tiff')))
    if not format_valid:
        raise ValueError('frozen validator output is not green')
    ok_to_submit = bool(card.get('ok_to_submit'))
    if card.get('verdict') != 'negative' or ok_to_submit:
        raise ValueError('holdout-negative current candidate must remain blocked')
    reason = '; '.join(card.get('blockers', []))
    return dict(
        schema='gems88.current-release.v2',
        candidate_id='MRR-COH-88',
        artifact=str(tif.relative_to(root)),
        zip_artifact=str(archive.relative_to(root)),
        raster_sha256=tif_hash,
        zip_sha256=zip_hash,
        format_valid=format_valid,
        no_nan_inside=True,
        all_values_in_0_1=True,
        crs_shape_transform_match=True,
        zip_one_exact_tif=True,
        positive_pixels=int((raster > 0).sum()),
        canary_max_auc=canaries['max_symmetric_auc'],
        holdout_dti=holdout_score['dti'],
        holdout_ci95=holdout_score['ci95'],
        holdout_evaluator=holdout_score['evaluator_version'],
        withheld_positive_pixels=holdout_score['withheld_positive_pixels'],
        incumbent_best_dti=incumbent['dti'],
        preplacement_max_abs_spearman=corr['preplacement_max_abs_spearman'],
        final_max_abs_spearman=corr['final_max_abs_spearman'],
        literal_registry_overlap_all_3px=corr['final_max_literal_forward_overlap_all'],
        literal_dot_field_overlap_3px=corr['final_max_literal_forward_overlap_dot_fields'],
        max_excess_overlap_3px=corr['final_max_excess_overlap'],
        registry_rasters_checked=corr['registry_rasters_checked'],
        unique=True,
        duplicate=False,
        research_download_ok=True,
        ok_to_submit=False,
        approved_for_weekly_slot=False,
        verdict='negative',
        status_label='OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT',
        reason=reason,
        provenance='hash-pinned owner-mirrored inputs; organizer authentication unavailable',
    )


def main():
    report = release_report()
    (ROOT / 'docs/data/current_release.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if '--require-submit' in sys.argv and not report['ok_to_submit']:
        print('AUTOMATIC SUBMISSION GATE: FAIL. NO UPLOAD PERMITTED.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
