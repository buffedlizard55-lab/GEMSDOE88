#!/usr/bin/env python3
"""One preregistered KTH-ANTISYMMETRIC-STEP experiment; never spends a slot."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'src'), str(ROOT / 'vendor')]
from gems88.kth_step import build_surface
from gems88.registry_paths import registry_list
from gems57 import evaluate_holdout, grid, holdout, uniqueness
from gems57.submission_writer import write_submission
from run_fabric_dislocation import preplacement_surface_rhos, leakage_canaries
from build_prune_deconfound_variants import directional_crest_1d
from build_provcrest_submission import select_dots
from validate_artifact import validate_artifact

N_DOTS = 37654
STEM_PREFIX = 'gems88-kth-antisym-magtrough-20261024'
SAMPLE = ROOT / 'data/bridge/sample_submission.tif'


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def registry_index():
    """Open the pinned registry + all already-published sibling TIFFs. No silent skips."""
    index = json.loads((ROOT / 'registry/inventory.json').read_text())
    if not index['complete_accessible_scan'] or index['errors']:
        raise ValueError('original registry inventory incomplete')
    pins = {str((ROOT / r['cache_file']).resolve()): r['sha256'] for r in index['rasters']}
    inv = json.loads((ROOT / 'registry/sibling_inventory.json').read_text())
    for site, record in inv['sites'].items():
        for r in record['files']:
            if r['kind'] == 'tif':
                name = site + '__' + r['path'].replace('/', '__')
                pins[str((ROOT / 'data/siblings' / name).resolve())] = r['sha256']
    seen = set()
    rows = []
    # Do not compare against this lane's own previously published output on a
    # fresh reproducibility run; the writer independently refuses overwrites.
    for label, p in registry_list(exclude=(STEM_PREFIX,)):
        resolved = str(p.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        actual = sha(p)
        if resolved in pins and pins[resolved] != actual:
            raise ValueError(f'pin mismatch: {p}')
        rows.append(dict(cache_file=str(p.relative_to(ROOT)), sha256=actual,
                         repo_first=label, sources=[p.name]))
    if len(rows) < len(index['rasters']):
        raise ValueError('registry unexpectedly smaller than baseline')
    return dict(rasters=rows, scope='SHA-verified original registry, restored pinned sibling/fleet files and all locally published TIFFs; NOT private/organizer-complete')


def main():
    t0 = time.monotonic()
    pre = json.loads((ROOT / 'registry/preregistration_kth88.json').read_text())
    if not pre['frozen_before_new_experiment'] or pre['n_dots'] != N_DOTS:
        raise ValueError('missing frozen preregistration')
    expected = {
        'data/bridge/sample_submission.tif': grid.SHA256_SAMPLE_SUBMISSION,
        'data/bridge/existing_faults.tif': grid.SHA256_EXISTING_FAULTS,
        'data/training_features.tif': '4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5',
        'data/external/geodawn_rad_u8.tif': 'c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682',
    }
    for p, want in expected.items():
        if sha(ROOT / p) != want:
            raise ValueError(f'input pin failed {p}')
    g = grid.load_grid()
    with rasterio.open(ROOT / 'data/external/geodawn_rad_u8.tif') as rad, rasterio.open(ROOT / 'data/training_features.tif') as features:
        if any((d.shape, d.crs, d.transform) != (g.shape, g.crs, g.transform) for d in (rad, features)):
            raise ValueError('input geotransform mismatch')
        if rad.descriptions[:2] != ('K', 'Th') or features.tags(2).get('band_name') != 'rtp':
            raise ValueError('input band names not as preregistered')
        surface, channels, stats = build_surface(rad.read(1), rad.read(2), features.read(2), g.footprint)
    print('[kth] surface built; no catalogue used', time.monotonic()-t0, flush=True)
    canary = leakage_canaries(channels, g)
    del channels
    print('[kth] canaries', {k: round(v['symmetric_auc'],5) for k,v in canary.items()}, flush=True)
    index = registry_index()
    pre_rows = preplacement_surface_rhos(surface, g, index) # STOP if rho > 0.90
    pre_max = max((abs(r['rho_full_footprint']) for r in pre_rows if r['rho_full_footprint'] is not None), default=0)
    print('[kth] preplacement max |rho|',pre_max,'n=',len(pre_rows),time.monotonic()-t0,flush=True)
    pool = directional_crest_1d(surface, distance_transform_edt(g.footprint) > 6)
    pos = np.flatnonzero(pool)
    if len(pos) < N_DOTS:
        raise ValueError('insufficient K/Th ridge candidates')
    pos = pos[np.argsort(-surface.ravel()[pos], kind='stable')]
    yx = np.column_stack(np.unravel_index(pos, g.shape))
    print('[kth] crest candidates', len(pos), flush=True)
    terms = None
    withheld = 0
    for seed in (20,21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        visible = folds[0]['visible']
        eligible = pool & g.footprint & ~folds[0]['masked_known'] & (distance_transform_edt(~visible) > 3)
        mask = select_dots(yx, eligible, g.shape)
        pred = mask.astype(np.float32)
        for f in folds:
            _, bt = evaluate_holdout.evaluate(pred, f, g.footprint)
            terms = bt if terms is None else terms + bt
            withheld += int(f['truth'].sum())
        print('[kth] fold seed',seed,'complete',time.monotonic()-t0,flush=True)
    summary = evaluate_holdout.pooled_summary({'candidate': terms}, draws=1000, seed=881024, candidate='candidate')
    score = summary['scores']['candidate']
    if score['withheld_positive_pixels'] != withheld:
        raise ValueError('withheld count does not match term totals')
    inc = json.loads((ROOT / 'registry/holdout_result.json').read_text())['scores']['candidate']
    comparable = (score['withheld_positive_pixels'] == inc['withheld_positive_pixels'])
    # Do not claim a paired CI against the incumbent from its point estimate.
    better = comparable and score['dti'] > inc['dti']
    print('[kth] HOLDOUT-DTI', score, 'beats incumbent?',better,flush=True)
    eligible = pool & g.footprint & ~g.catalogue & (distance_transform_edt(~g.catalogue) > 3)
    final = select_dots(yx, eligible, g.shape)
    stem = STEM_PREFIX + '-' + hashlib.sha256(final.tobytes()).hexdigest()[:8] + '-DO-NOT-SUBMIT'
    name = 'GEMSDOE88-KTH-' + hashlib.sha256(final.tobytes()).hexdigest()[:8].upper()
    note = f'K/Th antisymmetric radiometric step + RTP trough, {N_DOTS} dots; HOLDOUT-DTI {score["dti"]:.4f}; UNSCORED; DO NOT SUBMIT'
    path = ROOT / 'docs/downloads' / (stem + '.tif')
    receipt = write_submission(path, final.astype(np.float32), SAMPLE, g.footprint,
                               note=note, name=name, catalogue=g.catalogue,
                               metadata={'lane': pre['lane'], 'slot_authorized': False})
    validator = validate_artifact(path, SAMPLE)
    from gems88.gate import portal_validate
    zip_val = portal_validate(path.with_suffix('.zip'), SAMPLE, footprint=g.footprint)
    if not validator['ok'] or not zip_val['ok']:
        raise ValueError('independent TIFF/ZIP validators failed')
    print('[kth] disk TIFF validated',path.name,flush=True)
    # This intentionally checks the literal positive support of EVERY registry
    # raster, including the dense 17GEMSDOE witness; no special exemptions.
    reg = uniqueness.compare_to_registry(path, index, g.footprint,
        include_reverse=False, expected_grid=(g.shape, g.crs, g.transform))
    reg['my_file'] = str(path.relative_to(ROOT))
    for row in reg['rows']:
        row['file'] = str(Path(row['file']).relative_to(ROOT))
    evidence = {'preplacement_surface':pre_rows, 'final_dots':reg}
    write_json(ROOT / 'evidence/kth88_registry.json', evidence)
    overlap = reg['worst_dot_overlap']
    duplicate = bool(pre_max > .9 or overlap > .7 or reg['stop_required'])
    card = {
        'schema':'gems88.kth88.run-card.v1',
        'hypothesis':pre['ranking'][0]['off_catalogue_rationale'],
        'mechanism':pre['ranking'][0]['physical_signature'],
        'named_non_fault_process':pre['ranking'][0]['non_fault_mimic'],
        'lane':pre['lane'], 'inputs':expected, 'surface_parameters_and_coverage':stats,
        'leakage_canary':canary,
        'holdout_dti':score, 'holdout_evaluator':summary['evaluator_version'],
        'holdout_bootstrap':summary['bootstrap'],
        'incumbent_holdout_dti':inc,
        'comparable_to_incumbent_same_seed_same_split':comparable,
        'paired_incumbent_ci95':None,
        'correlation_overlap_vs_registry':{'preplacement_max_abs_rho':pre_max,
            'final_max_abs_rho':reg['worst_spearman_full_footprint'],
            'final_overlap_3px':overlap, 'worst_registry_raster':reg['worst_overlap_submission'],
            'registry_rasters_checked':reg['registry_rasters_checked'],
            'literal_duplicate':duplicate,
            'literal_blockers':[{'raster':r['submission'], 'overlap_3px':r['my_dots_within_3px_of_theirs']}
                                for r in sorted(reg['rows'], key=lambda r:-r['my_dots_within_3px_of_theirs'])
                                if r['my_dots_within_3px_of_theirs'] > .70],
            'full_rows':'evidence/kth88_registry.json'},
        'raster_sha256':receipt['sha256'],
        'validator_output':validator, 'download':str(path.relative_to(ROOT)),
        'submission_name':name, 'submission_note':note,
        'ok_to_download':True, 'ok_to_submit':False,
        'verdict':'negative', 'experiment_count':1,
        'stop_reason': 'Duplicate by literal >70% forward 3px registry overlap (including an independent GEMSDOE87 prior); stop.' if duplicate else
            'No positive paired holdout improvement over incumbent; stop without spending a slot.',
        'organizer_confirmed':None, 'slots_spent':0,
        'limitations':['U8 K and Th indices have no physical-unit calibration tags: their ratio is not a measured elemental abundance ratio.',
                       'Public GeoDAWN source is official but this owner-mirrored u8 derivative is not independently authenticated to the organizer download.',
                       'Hide-and-recover catalogue labels are not the undisclosed new fault labels.',
                       'Registry excludes private/unlinked competition submissions.',
                       'No portal authorization or submission receipt.']}
    write_json(ROOT / 'registry/kth88_run_card.json', card)
    write_json(ROOT / 'docs/data/kth88_run_card.json', card)
    print('[kth] verdict',card['verdict'],card['stop_reason'],time.monotonic()-t0,flush=True)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
