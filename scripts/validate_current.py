#!/usr/bin/env python3
"""Current-release summary and fail-closed gates.

The current summary follows PHASE-88, the latest run card; its TIFF/ZIP is
independently reopened by validate_phase88.py. The full historical fabric audit
remains available as fabric_release_report(). A scientific or uniqueness
failure keeps `ok_to_submit` false; formatting never approves a weekly slot.
Run `--require-submit` to demand a green current gate (exit 2 today). No
organizer upload/login is attempted.
"""
from __future__ import annotations
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'vendor'))
from gems57 import gates, grid, uniqueness, validate  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fabric_release_report(root=ROOT):
    root = Path(root)
    card = json.loads((root / 'registry/fabric_dislocation_run_card.json').read_text())
    web = json.loads((root / 'docs/data/fabric_dislocation_run_card.json').read_text())
    evidence = json.loads((root / 'evidence/fabric_dislocation_uniqueness.json').read_text())
    later = json.loads((root / 'evidence/postmerge_tiltzero_audit.json').read_text())
    if card != web or card['verdict'] != 'negative' or card['ok_to_submit'] is not False:
        raise ValueError('published science/status card is not the canonical negative result')
    if card['file'] != f"docs/downloads/{Path(card['file']).name}" or 'DO-NOT-SUBMIT' not in card['file']:
        raise ValueError('unmarked or escaping research raster')
    sample = root / 'data/bridge/sample_submission.tif'
    catalog = root / 'data/bridge/existing_faults.tif'
    if sha(sample) != grid.SHA256_SAMPLE_SUBMISSION or sha(catalog) != grid.SHA256_EXISTING_FAULTS:
        raise ValueError('owner-mirrored sample/labels have changed or were not restored')
    gd = grid.load_grid(root / 'data/bridge')
    tif = root / card['file']
    archive = root / card['zip_file']
    receipt = json.loads(tif.with_suffix('.json').read_text())
    if sha(tif) != card['raster_sha256'] or sha(archive) != card['zip_sha256']:
        raise ValueError('research TIFF/ZIP SHA256 does not match frozen run card')
    if (receipt['sha256'] != card['raster_sha256'] or
        receipt['zip_sha256'] != card['zip_sha256'] or
        receipt['submission_name'] != card['submission_name'] or
        receipt['note'] != card['submission_note'] or
        len(card['submission_note']) > 140 or not card['submission_note']):
        raise ValueError('writer receipt or short note differs from research run card')
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError('ZIP must contain exactly the byte-identical research TIFF')
    result = gates.format_report(tif, sample, footprint=gd.footprint)
    local = validate.validate(tif, gd.footprint, gd.catalogue)
    independent = validate_artifact(tif, sample)
    if not (result['ok'] and local['all_checks_passed'] and independent['ok']):
        raise ValueError('disk TIFF failed shared writer/independent format checks')
    with rasterio.open(tif) as src:
        raster = src.read(1)
    if not np.isfinite(raster).all() or (raster[~gd.footprint] != 0).any():
        raise ValueError('TIFF contains nonfinite or nonzero outside the footprint')
    if card['validator_output']['raster_sha256'] != sha(tif):
        raise ValueError('validator not bound to the actual TIFF bytes')
    if not all(card['validator_output'][k] for k in ('format_valid','no_nan_inside',
              'values_in_0_1','crs_match','shape_match','transform_match','zero_outside')):
        raise ValueError('frozen machine format preflight was not green')
    holdout = card['holdout']['candidate']
    if (holdout['evaluator_version'] != 'gems57-pooled-hide-v2' or
        holdout['withheld_positive_pixels'] != 22893 or
        not isinstance(holdout['dti'], (int, float)) or
        not np.isfinite(holdout['dti']) or
        not 0 <= holdout['dti'] <= 1):
        raise ValueError('HOLDOUT-DTI report not finite [0,1] on expected split')
    prior = card['holdout']['incumbent_prior_best']
    if (not 0 <= holdout['ci95'][0] <= holdout['dti'] <= holdout['ci95'][1] <= 1 or
        not holdout['dti'] < prior['dti'] or
        not holdout['ci95'][1] < prior['ci95'][0] or
        card['feature_canaries']['max_symmetric_auc'] > .9):
        raise ValueError('candidate science/card is not a negative below the incumbent')
    old = json.loads((root / 'registry/holdout_result.json').read_text())['scores']['candidate']
    if prior != old:
        raise ValueError('incumbent holdout best not reproduced from repository result')
    before = evidence['preplacement_surface']
    if (len(before) != card['correlation_overlap_vs_registry']['registry_rasters_checked'] or
        any('rho_full_footprint' not in r or (r['rho_full_footprint'] is not None and abs(r['rho_full_footprint']) > .9) for r in before)):
        raise ValueError('preplacement surface was unverified/duplicate')
    # Read and rehash *all* frozen final-prior files; remeasure full-footprint
    # Spearman and forward dot overlap using the shared literal comparator.
    stored = evidence['final_dots']
    rows = stored['rows']
    if len(rows) != len(before) or stored['candidate_file_sha256'] != sha(tif):
        raise ValueError('final prior comparison is incomplete or candidate changed')
    if (later['schema'] != 'gems88.posthoc-registry-extension.v1' or
        later['initial_prior_count'] != len(rows) or
        later['candidate_sha256'] != sha(tif) or
        later['remains_blocked'] is not True or
        later['new_prior'] != later['final_dots_posthoc']['file'] or
        later['new_prior'] != later['frozen_surface_posthoc']['path'] or
        later['new_prior_sha256'] != later['final_dots_posthoc']['sha256'] or
        later['new_prior_sha256'] != later['frozen_surface_posthoc']['sha256'] or
        not isinstance(later['frozen_surface_posthoc']['rho_full_footprint'], (float, int)) or
        abs(later['frozen_surface_posthoc']['rho_full_footprint']) > .9):
        raise ValueError('postmerge prior audit is inconsistent with original frozen experiment')
    new_prior = (root / later['new_prior']).resolve()
    if (not new_prior.is_relative_to(root / 'docs/downloads') or
        sha(new_prior) != later['new_prior_sha256'] or
        later['new_prior_sha256'] in {r['sha256'] for r in rows}):
        raise ValueError('postmerge prior missing, moved or SHA changed')
    # A new published TIFF appeared after the initial 29-raster experiment.
    # Fail closed if another unreviewed file appears in the accessible registry.
    observed_hashes = {sha(path) for directory in ('data/registry', 'docs/downloads', 'submissions')
                       for path in (root / directory).rglob('*.tif')}
    expected_hashes = {r['sha256'] for r in rows} | {sha(tif), later['new_prior_sha256']}
    # Rasters that carry a gems88-gate-v3 verdict record (registry/*gate_v3.json, registry/gate_verdict.json) were reviewed against the
    # 216+-raster v3 registry by the session of 2026-10-24 (IR-88-59..71); any OTHER unreviewed TIFF still fails closed.
    for record in ('gate_verdict.json', 'provcrest_gate_v3.json', 'tiltzero_gate_v3.json', 'lbcal_gate_v3.json', 'mvrd_gate_v3.json', 'gthc88_gate_v3.json'):
        rec = root / 'registry' / record
        if rec.is_file():
            expected_hashes.add(json.loads(rec.read_text())['sha256'])
    # MDC-88 (PR #61, IR-88-75/73/74) stores its gate-v3 verdict nested under 'gate_v3'
    # with the file hash in 'candidate'. Same review standard, different record shape.
    for record in ('kdmc_gate.json', 'kdmc_gate_collar3.json', 'qts88_gate.json'):
        rec = root / 'registry' / record
        if not rec.is_file():
            continue
        data = json.loads(rec.read_text())
        if data.get('gate_v3', {}).get('policy') != 'gems88-gate-v3':
            continue
        # Only whitelist a hash that is actually published in a scanned directory; the
        # collar-3 research variant lives in docs/research-variants/ and is intentionally
        # outside the accessible registry (same lane as the primary, IR-88-76/74).
        if (root / 'docs' / 'downloads' / Path(data['candidate']['tif']).name).is_file():
            expected_hashes.add(data['candidate']['sha256'])
    # IR-88-82 (2026-10-24, LBCAL session): the canonical negative run card's own TIFF (MRR-BPR-88, PRs #56/#57)
    # was published without being whitelisted here, so main failed this check on its own bytes. Accept it only
    # via its own run card hash with verdict negative / ok_to_submit false; any other unreviewed TIFF still fails.
    canon = json.loads((root / 'registry' / 'run_card.json').read_text())
    if canon.get('verdict') == 'negative' and canon.get('ok_to_submit') is False and canon.get('raster_sha256'):
        expected_hashes.add(canon['raster_sha256'])
    # IR-88-KTH-02: independently audited KTH research file is a negative
    # deliverable, not an unexplained extra TIFF. Its complete 222-raster
    # comparison and TIFF/ZIP validator are checked here before whitelisting;
    # arbitrary additional research TIFFs remain fail-closed.
    kth_path = root / 'registry/kth88_run_card.json'
    if kth_path.is_file():
        kth = json.loads(kth_path.read_text())
        p = (root / kth['download']).resolve()
        audit = json.loads((root / 'docs/data/kth88_validation.json').read_text())
        comparisons = json.loads((root / 'evidence/kth88_registry.json').read_text())
        if (not p.is_relative_to((root / 'docs/downloads').resolve())
            or kth.get('verdict') != 'negative' or kth.get('ok_to_submit') is not False
            or 'DO-NOT-SUBMIT' not in p.name
            or sha(p) != kth.get('raster_sha256')
            or audit.get('tif_sha256') != sha(p)
            or audit.get('ok_to_submit') is not False
            or not audit.get('tif_and_single_member_zip_validated')
            or audit.get('local_format_audit', {}).get('ok') is not True
            or comparisons['final_dots']['candidate_file_sha256'] != sha(p)
            or comparisons['final_dots']['registry_rasters_checked'] < 200
            or comparisons['final_dots']['worst_dot_overlap'] <= .70):
            raise ValueError('new KTH research TIFF has no verified negative audit')
        expected_hashes.add(sha(p))
    if observed_hashes != expected_hashes:
        raise ValueError('accessible registry changed since postmerge audit; recheck all prior rasters')
    index = dict(complete_accessible_scan=True, errors=[], rasters=[])
    checked_rows = [*rows, later['final_dots_posthoc']]
    for r in checked_rows:
        file = Path(r['file'])
        if not file.is_absolute():
            file = root / file
        if not file.is_relative_to(root) or sha(file) != r['sha256']:
            raise ValueError('registry file moved outside repository or SHA256 changed')
        index['rasters'].append(dict(repo_first=r['repo'], sources=[r['submission']],
                                     cache_file=str(file), sha256=r['sha256']))
    with rasterio.open(sample) as ds:
        expected = (ds.shape, ds.crs, ds.transform)
    measured = uniqueness.compare_to_registry(tif, index, gd.footprint, include_reverse=False,
                                               expected_grid=expected)
    if (not measured['complete_accessible_scan'] or
        measured['registry_rasters_checked'] != len(checked_rows) or
        measured['duplicate_count'] < 1 or
        measured['worst_dot_overlap'] != 1.0):
        raise ValueError('new raster unexpectedly cleared the literal registry gate')
    with rasterio.open(root / 'data/registry/dense_17gemdoe.tif') as src:
        witness = src.read(1)
    dense = uniqueness.saturation_certificate(root / 'data/registry/dense_17gemdoe.tif',
                   gd.footprint, gd.catalogue, expected_grid=expected)
    overlap = uniqueness.dot_overlap(raster, witness, 3)
    if (not dense['universal_overlap_blocker'] or overlap != 1.0 or
        overlap != card['correlation_overlap_vs_registry']['final_worst_overlap_3px']):
        raise ValueError('all-positive witness assertion no longer matches TIFF')
    for observed, recorded in zip(measured['rows'], checked_rows):
        rho, saved = observed.get('spearman_full_footprint'), recorded.get('spearman_full_footprint')
        same_rho = (rho is None and saved is None) or (
            rho is not None and saved is not None and np.isclose(rho, saved, rtol=0, atol=1e-10))
        if (observed.get('sha256') != recorded.get('sha256') or
            not same_rho or
            not np.isclose(observed.get('my_dots_within_3px_of_theirs', -1),
                           recorded.get('my_dots_within_3px_of_theirs', -2), rtol=0, atol=1e-12)):
            raise ValueError('registry comparison changed; archived experiment is not reproducible')
    return dict(schema='gems88.current-release.v1', file=card['file'],
                file_sha256=sha(tif), zip_sha256=sha(archive),
                format_valid=True, no_nan_inside=True, all_values_in_0_1=True,
                crs_shape_transform_match=True, zip_one_exact_tif=True,
                positive_pixels=int((raster > 0).sum()),
                canary_max_auc=card['feature_canaries']['max_symmetric_auc'],
                holdout_dti=holdout['dti'], holdout_ci95=holdout['ci95'],
                incumbent_best_dti=prior['dti'],
                literal_registry_overlap_3px=overlap,
                registry_rasters_checked=measured['registry_rasters_checked'],
                original_preplacement_rasters_checked=len(rows),
                posthoc_rasters_checked=1,
                posthoc_prior_file=later['new_prior'],
                posthoc_prior_surface_rho=later['frozen_surface_posthoc']['rho_full_footprint'],
                posthoc_prior_final_overlap=later['final_dots_posthoc']['my_dots_within_3px_of_theirs'],
                final_worst_abs_rho=max(abs(r['spearman_full_footprint']) for r in measured['rows']
                                        if r['spearman_full_footprint'] is not None),
                duplicate=True, research_download_ok=True, ok_to_submit=False,
                approved_for_weekly_slot=False, verdict='negative',
                reason='Literal dense registry overlap = 1.0 > 0.70; HOLDOUT-DTI below frozen best. DO NOT SUBMIT.',
                provenance='owner-mirrored sample/labels; independent organizer authentication unavailable')



def phase_release_report(root=ROOT):
    """Reopen the current PHASE-88 TIFF/ZIP and independently remeasure witness."""
    from scripts.validate_phase88 import inspect
    root = Path(root)
    card = json.loads((root / 'registry/phase88_run_card.json').read_text())
    validation = inspect(root)
    if validation != json.loads((root / 'docs/data/phase88_validation.json').read_text()):
        raise ValueError('current PHASE-88 public audit differs from independent measurement')
    h = card['holdout_dti']; inc = card['incumbent_holdout_dti']
    comparison = card['correlation_overlap_vs_registry']
    tif = root / card['download']
    return dict(schema='gems88.current-release.v1', file=card['download'],
                file_sha256=sha(tif), zip_sha256=validation['zip_sha256'],
                format_valid=validation['local_format_audit']['ok'],
                no_nan_inside=validation['local_format_audit']['no_nan_inside'],
                all_values_in_0_1=validation['local_format_audit']['range_0_1'],
                crs_shape_transform_match=all(validation['local_format_audit'][k] for k in
                    ('crs_match','shape_match','transform_match')),
                zip_one_exact_tif=validation['tif_and_single_member_zip_validated'],
                positive_pixels=37654,
                canary_max_auc=max(v['symmetric_auc'] for v in card['leakage_canary'].values()),
                holdout_dti=h['dti'],holdout_ci95=h['ci95'],
                holdout_evaluator=h['evaluator_version'],
                withheld_positive_pixels=h['withheld_positive_pixels'],
                incumbent_best_dti=inc['dti'],
                literal_registry_overlap_3px=validation['literal_witness_remeasured_overlap_3px'],
                registry_rasters_checked=comparison['registry_rasters_checked'],
                duplicate=comparison['literal_duplicate'],research_download_ok=True,
                ok_to_submit=False,approved_for_weekly_slot=False,verdict='negative',
                reason=card['stop_reason'],
                provenance='hash-pinned owner mirror; not independently authenticated organizer sample')



def release_report(root=ROOT):
    """Return the canonical current H88-MVRD report."""
    from validate_release import release_report as mvrd_release_report

    return mvrd_release_report(root)

def main():
    report = release_report()
    (ROOT / 'docs/data/current_release.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if '--require-submit' in sys.argv:
        print('AUTOMATIC SUBMISSION GATE: FAIL. NO UPLOAD PERMITTED.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
