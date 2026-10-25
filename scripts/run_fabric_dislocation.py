#!/usr/bin/env python3
"""One preregistered unsupervised MAG-FABRIC-DISLOCATION experiment.

Produces a BRAND NEW research GeoTIFF, not a copy or remix of a prior output.
The canonical template's literal uniqueness gate is never overridden: the
space-filling 17GEMSDOE raster makes every nonempty candidate a duplicate.
The artifact is permanently named DO-NOT-SUBMIT unless the protocol changes
in a *future* session, independent of whether its GeoTIFF format passes.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / 'src', ROOT / 'scripts', ROOT / 'vendor'):
    sys.path.insert(0, str(p))

from gems88.fabric_dislocation import build_surface  # noqa: E402
from gems57 import evaluate_holdout, grid, holdout, uniqueness  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from build_prune_deconfound_variants import directional_crest_1d  # noqa: E402
from build_provcrest_submission import select_dots  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

PREREG = ROOT / 'registry/preregistration_fabric_dislocation.json'
OUTPUT = ROOT / 'registry/fabric_dislocation_run_card.json'
EVIDENCE = ROOT / 'evidence/fabric_dislocation_uniqueness.json'
N_DOTS = 37_654
EXPECTED_SHA = '4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5'


def digest(path: Path) -> str:
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def json_write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def verify_sources():
    for name, want in (('data/training_features.tif', EXPECTED_SHA),
                       ('data/bridge/sample_submission.tif', grid.SHA256_SAMPLE_SUBMISSION),
                       ('data/bridge/existing_faults.tif', grid.SHA256_EXISTING_FAULTS)):
        got = digest(ROOT / name)
        if got != want:
            raise ValueError(f'unverified owner mirror {name}: {got} != {want}')
    g = grid.load_grid(ROOT / 'data/bridge')
    with rasterio.open(ROOT / 'data/training_features.tif') as ds:
        if (ds.shape, ds.crs, ds.transform) != (g.shape, g.crs, g.transform):
            raise ValueError('19-band feature stack not aligned with pinned sample grid')
        for b, name in ((2, 'rtp'), (13, 'iso_grav_anom')):
            if ds.tags(b).get('band_name') != name:
                raise ValueError(f'band {b} was not {name}: {ds.tags(b)}')
    return g


def public_registry_index():
    """Verify every pinned prior; add all already published local downloads.

    This *accessible* inventory cannot see private, unlinked or later-published
    files and must never be called complete for all competition submissions.
    """
    index = json.loads((ROOT / 'registry/inventory.json').read_text())
    if not index.get('complete_accessible_scan') or index.get('errors'):
        raise ValueError('pinned accessible inventory is incomplete')
    by_sha = {}
    for row in index['rasters']:
        file = ROOT / row['cache_file']
        if not file.exists() or digest(file) != row['sha256']:
            raise ValueError(f'missing/bad registry pin: {file}')
        by_sha.setdefault(row['sha256'], dict(row))
    # Other tracked repo publications must be checked too, including the
    # previous site's PROVCREST (not in the older pinned inventory).
    for folder in ('data/registry', 'docs/downloads', 'submissions'):
        for file in sorted((ROOT / folder).rglob('*.tif')):
            sha = digest(file)
            if sha not in by_sha:
                by_sha[sha] = dict(repo_first='GEMSDOE88/local', sources=[file.name],
                                   cache_file=str(file.relative_to(ROOT)), sha256=sha)
    return dict(complete_accessible_scan=True, errors=[], rasters=list(by_sha.values()),
                scope='pinned owner-mirrored inventory plus all locally published research TIFFs; private/unlinked submissions not observed')


def preplacement_surface_rhos(score, gd, index):
    """Exact, full-footprint tie-aware Spearman; abort before any dot placement.

    A continuous surface has *no selected dots yet*, so dot overlap is tested
    strictly AFTER placement via the template's literal registry comparator.
    """
    fp = gd.footprint
    vals = score[fp]
    mine = rankdata(vals).astype(np.float64)
    mine -= mine.mean()
    norm = np.linalg.norm(mine)
    if norm == 0:
        raise ValueError('structural surface constant: cannot place dots')
    rows = []
    for r in index['rasters']:
        file = ROOT / r['cache_file']
        if digest(file) != r['sha256']:
            raise ValueError(f'registry changed during run: {file}')
        with rasterio.open(file) as src:
            if src.count != 1 or (src.shape, src.crs, src.transform) != (gd.shape, gd.crs, gd.transform):
                raise ValueError(f'prior not on the exact grid: {file}')
            prior = src.read(1)[fp].astype(np.float32)
        # The shared template ignores nonfinite prior values (e.g. NaN outside);
        # inside the valid footprint, an invalid pixel must not be used for ranking.
        if not np.isfinite(prior).all():
            raise ValueError(f'nonfinite prior inside footprint: {file}')
        if np.ptp(prior) == 0:
            rho = None
        else:
            other = rankdata(prior).astype(np.float64)
            other -= other.mean()
            rho = float(np.dot(mine, other) / (norm * np.linalg.norm(other)))
        rows.append({'path':r['cache_file'], 'sha256':r['sha256'], 'rho_full_footprint':rho})
        if rho is not None and abs(rho) > .9:
            raise RuntimeError(f'DUPLICATE BEFORE PLACEMENT: |rho|={abs(rho):.6f} > .90 vs {file}; stop')
    return rows


def leakage_canaries(channels, gd):
    # Only the AUC *audit* uses hidden labels. Fitted field is wholly label-blind.
    f20, _ = holdout.buffered_component_draw(gd, seed=20)
    f21, _ = holdout.buffered_component_draw(gd, seed=21)
    positives = f20[0]['hidden_all'] | f21[0]['hidden_all']
    pos_idx = np.flatnonzero(positives)
    neg_pool = np.flatnonzero(gd.footprint & ~gd.catalogue & ~positives)
    neg_idx = np.random.default_rng(882024).choice(neg_pool, min(100_000, len(neg_pool)), replace=False)
    pick = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate([np.ones(len(pos_idx), np.int8), np.zeros(len(neg_idx), np.int8)])
    result = {}
    for name, arr in channels.items():
        values = arr.ravel()[pick]
        if not np.isfinite(values).all():
            raise ValueError(f'nonfinite single-feature AUC channel: {name}')
        auc = float(roc_auc_score(y, values))
        sym = max(auc, 1.0 - auc)
        result[name] = dict(auc=auc, symmetric_auc=sym)
        if sym > .9:
            raise RuntimeError(f'LEAKAGE CANARY {name}: {sym:.6f} > .90; stop')
    return result


def choose(sorted_yx, eligible, shape):
    return select_dots(sorted_yx, eligible, shape)


def main():
    t0 = time.monotonic()
    prereg = json.loads(PREREG.read_text())
    if not prereg['frozen_before_new_experiment'] or prereg['method']['dot_count'] != N_DOTS:
        raise ValueError('preregistration changed unexpectedly')
    gd = verify_sources()
    print('[fabric] input SHA and band tags verified', flush=True)
    with rasterio.open(ROOT / 'data/training_features.tif') as src:
        surface, channels, stats = build_surface(src.read(2), src.read(13), gd.footprint)
    print('[fabric] paired-side surface computed', flush=True)
    canary = leakage_canaries(channels, gd)
    del channels
    print('[fabric] single-feature canaries:', {k: round(v['symmetric_auc'], 5) for k,v in canary.items()}, flush=True)
    index = public_registry_index()
    surface_rows = preplacement_surface_rhos(surface, gd, index)
    print(f'[fabric] pre-placement full-footprint Spearman: {len(surface_rows)} checked, worst={max(abs(r["rho_full_footprint"]) for r in surface_rows if r["rho_full_footprint"] is not None):.5f}', flush=True)
    interior = distance_transform_edt(gd.footprint) > 6.0
    pool = directional_crest_1d(surface, interior)
    positions = np.flatnonzero(pool)
    if len(positions) < N_DOTS:
        raise RuntimeError(f'crest pool too small: {len(positions)} < {N_DOTS}')
    positions = positions[np.argsort(-surface.ravel()[positions], kind='stable')]
    sorted_yx = np.column_stack(np.unravel_index(positions, gd.shape))
    print('[fabric] label-blind directional crest pool:', len(positions), flush=True)

    terms = None
    fold_counts = []
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(gd, seed=seed)
        # Only fold-VISIBLE faults inform this >300 m catalogue collar.
        visible = folds[0]['visible']
        masked = folds[0]['masked_known']  # masking, not a ranking feature
        eligible = pool & gd.footprint & ~masked & (distance_transform_edt(~visible) > 3.0)
        mask = choose(sorted_yx, eligible, gd.shape)
        pred = mask.astype(np.float32)
        for f in folds:
            _, block_terms = evaluate_holdout.evaluate(pred, f, gd.footprint)
            terms = block_terms if terms is None else terms + block_terms
            fold_counts.append(dict(seed=seed, fold=f['name'],
                                    withheld_positive_pixels=int(f['truth'].sum()),
                                    emitted=int((mask & f['region'] & ~f['masked_known']).sum())))
        print(f'[fabric] holdout seed {seed} complete ({time.monotonic() - t0:.1f}s)', flush=True)
    summary = evaluate_holdout.pooled_summary({'candidate':terms}, draws=1000,
                                                seed=880824, candidate='candidate')
    score = summary['scores']['candidate']
    prior_best = json.loads((ROOT / 'registry/holdout_result.json').read_text())['scores']['candidate']
    assert summary['evaluator_version'] == 'gems57-pooled-hide-v2'
    if score['withheld_positive_pixels'] != prior_best['withheld_positive_pixels']:
        raise ValueError('withheld-positive count differs from incumbent: split not comparable')
    print(f"[fabric] HOLDOUT-DTI={score['dti']:.6f} CI95={score['ci95']} vs prior best={prior_best['dti']:.6f}", flush=True)

    # Final raster uses the full public catalogue ONLY for exclusion. Prior
    # submission pixels are never used for this candidate's construction.
    d_cat = distance_transform_edt(~gd.catalogue)
    eligible_final = pool & gd.footprint & ~gd.catalogue & (d_cat > 3.0)
    final = choose(sorted_yx, eligible_final, gd.shape)
    pred = final.astype(np.float32)
    pred[~gd.footprint] = 0.0
    stem = f"gems88-fabric-dislocation-20261024-{hashlib.sha256(final.tobytes()).hexdigest()[:8]}-DO-NOT-SUBMIT"
    note = f"FAB88 RTP fabric dislocation x gravity; {N_DOTS} dots; HOLDOUT-DTI {score['dti']:.4f}; no receipt; DO NOT SUBMIT"
    name = f"GEMSDOE88-FABDIS-{hashlib.sha256(final.tobytes()).hexdigest()[:8].upper()}"
    assert 0 < len(note) <= 140 and len(name) <= 140
    path = ROOT / 'docs/downloads' / f'{stem}.tif'
    receipt = write_submission(path, pred, ROOT / 'data/bridge/sample_submission.tif',
                               gd.footprint, note=note, name=name, catalogue=gd.catalogue,
                               metadata={'method_lane':'MAG-FABRIC-DISLOCATION',
                                         'evidence_class':'HOLDOUT-DTI',
                                         'do_not_submit':True})
    independent = validate_artifact(path, ROOT / 'data/bridge/sample_submission.tif')
    if not independent['ok']:
        raise RuntimeError('independent disk re-read failed after shared submission writer')
    del pred
    print('[fabric] TIFF created and independently validated:', path.name, flush=True)
    # Shared literal comparator checks ALL prior positive supports, dense ones
    # included. An overlap violation is an automatic negative with no override.
    result = uniqueness.compare_to_registry(path, index, gd.footprint,
                                             include_reverse=False,
                                             expected_grid=(gd.shape, gd.crs, gd.transform))
    if result['registry_rasters_checked'] != len(index['rasters']):
        raise RuntimeError('final registry audit incomplete')
    # Canonicalise paths before writing tracked evidence: CI checkout paths
    # differ from this sandbox, while file hashes/metrics remain immutable.
    result['my_file'] = str(path.relative_to(ROOT))
    for row in result['rows']:
        row['file'] = str(Path(row['file']).relative_to(ROOT))
    witness = uniqueness.saturation_certificate(ROOT / 'data/registry/dense_17gemdoe.tif',
        gd.footprint, gd.catalogue, expected_grid=(gd.shape, gd.crs, gd.transform))
    witness['witness_file'] = 'data/registry/dense_17gemdoe.tif'
    uniqueness_receipt = {'schema':'gems88.uniqueness.v1',
                          'preplacement_surface':surface_rows,
                          'final_dots':result,
                          'dense_witness_universal':witness}
    json_write(EVIDENCE, uniqueness_receipt)
    json_write(ROOT / 'docs/data/fabric_dislocation_uniqueness.json', uniqueness_receipt)
    block = result['stop_required'] or witness['universal_overlap_blocker']
    # Promotion also fails if new method doesn't beat the current best on this
    # exact split. Paired incumbent bootstrap terms are not cached: if this ever
    # beats it, reproduction of the incumbent and paired CI is still required.
    holdout_better = score['dti'] > prior_best['dti']
    validator = dict(format_valid=independent['ok'], no_nan_inside=independent['no_nan_inside'],
                     values_in_0_1=independent['range_0_1'],
                     crs_match=independent['crs_match'], shape_match=independent['shape_match'],
                     transform_match=independent['transform_match'],
                     zero_outside=independent['no_mass_outside'],
                     raster_sha256=receipt['sha256'],
                     sample_sha256=independent['sample_sha256'],
                     emitted_positive_pixels=int(final.sum()),
                     min_distance_to_catalogue_px=float(d_cat[final].min()))
    card = dict(schema='gems88.run-card.v4', generated_utc='2026-10-24',
        hypothesis='Buried offsets of magnetic basement fabric leave a paired-side axial RTP orientation dislocation corroborated by a separate gravity gradient, even without a mapped fault trace.',
        mechanism='Signed Band-2 RTP gradients -> Gaussian structure tensor -> opposite-side axial rotation at 300/283 m -> rank-modulate by Band-13 gravity gradient -> directional NMS, binary spaced dots; only visible faults provide holdout catalogue exclusion.',
        named_non_fault_process='Unfaulted intrusive/volcanic lithologic contact or airborne magnetic flight-line seam that rotates magnetic fabric without brittle fault displacement.',
        method_lane='MAG-FABRIC-DISLOCATION', data_provenance='hash-pinned owner mirror, not independently authenticated organizer download',
        feature_canaries={'threshold_symmetric_auc':.9, 'per_channel':canary,
                          'max_symmetric_auc':max(c['symmetric_auc'] for c in canary.values())},
        holdout=dict(evidence_class='HOLDOUT-DTI', evaluator_version=summary['evaluator_version'],
                     candidate=score, incumbent_prior_best=prior_best,
                     withheld_positive_pixels=score['withheld_positive_pixels'],
                     folds=fold_counts, bootstrap=summary['bootstrap'],
                     comparable_split='same frozen whole-component folds seeds 20/21; no paired incumbent terms stored',
                     beats_prior_point_estimate=holdout_better,
                     paired_improvement_ci95=None,
                     note='Neither this HOLDOUT-DTI nor prior best is an ORGANIZER-CONFIRMED result; no live score is claimed.'),
        correlation_overlap_vs_registry=dict(
            preplacement_max_abs_rho=max(abs(r['rho_full_footprint']) for r in surface_rows if r['rho_full_footprint'] is not None),
            final_worst_abs_rho=max(abs(r['spearman_full_footprint']) for r in result['rows'] if r.get('spearman_full_footprint') is not None),
            final_worst_overlap_3px=result['worst_dot_overlap'],
            final_worst_overlap_raster=result['worst_overlap_submission'],
            registry_rasters_checked=result['registry_rasters_checked'],
            registry_scope=index['scope'],
            raw_duplicate_count=result['duplicate_count'],
            universal_dense_witness=witness['universal_overlap_blocker'],
            full_rows='evidence/fabric_dislocation_uniqueness.json',
            raw_gate_pass=bool(result['unique'])),
        validator_output=validator,
        raster_sha256=receipt['sha256'], zip_sha256=receipt['zip_sha256'],
        submission_name=name, submission_note=note,
        file=f'docs/downloads/{path.name}', zip_file=f'docs/downloads/{path.stem}.zip',
        research_download_ok=True, ok_to_submit=False,
        organizer_confirmed_score=None, weekly_slots_used_by_agent=0,
        experiments_run=1, experiment_budget_max=3,
        elapsed_seconds=round(time.monotonic()-t0, 1),
        verdict='negative',
        stop_reason=('DUPLICATE under literal >70% forward 3px registry gate; stop (dense 17GEMSDOE universal witness). '
                     if block else 'No demonstrated paired improvement over holdout best; stop. ')
                    + ('Holdout below existing best.' if not holdout_better else 'Paired incumbent interval unavailable; cannot promote.'))
    json_write(OUTPUT, card)
    json_write(ROOT / 'docs/data/fabric_dislocation_run_card.json', card)
    print(f"[fabric] STOP/NEGATIVE: {card['stop_reason']}", flush=True)
    print('[fabric] SHA256:', receipt['sha256'], 'zip:', receipt['zip_sha256'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
