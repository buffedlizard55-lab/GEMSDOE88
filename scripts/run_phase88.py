#!/usr/bin/env python3
"""Exactly one preregistered PHASE-88 experiment; zero organizer submissions.

Run only with restored SHA-pinned owner-mirror inputs. A literal registry
collision is a negative result: never reinterpret a file-hash difference as
clearance to submit. Refuses to overwrite outputs.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts'), str(ROOT / 'vendor')]
from gems88.phase88 import build_surface
from gems88.registry_paths import registry_list
from gems88.gate import portal_validate
from gems57 import evaluate_holdout, grid, holdout, uniqueness
from gems57.submission_writer import write_submission
from run_fabric_dislocation import preplacement_surface_rhos, leakage_canaries, verify_sources
from build_prune_deconfound_variants import directional_crest_1d
from build_provcrest_submission import select_dots
from validate_artifact import validate_artifact

N_DOTS = 37654
PREFIX = 'gems88-phase88-crossgrad-20261024'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def registry_index():
    base = json.loads((ROOT/'registry/inventory.json').read_text())
    siblings = json.loads((ROOT/'registry/sibling_inventory.json').read_text())
    if not base['complete_accessible_scan'] or base['errors']:
        raise ValueError('pinned base registry incomplete')
    pins = {str((ROOT/r['cache_file']).resolve()):r['sha256'] for r in base['rasters']}
    for site, siteinfo in siblings['sites'].items():
        for r in siteinfo['files']:
            if r['kind'] == 'tif':
                name = site+'__'+r['path'].replace('/', '__')
                pins[str((ROOT/'data/siblings'/name).resolve())] = r['sha256']
                if site == 'GEMSDOE86' and r['path'].startswith('data/scored_fleet/'):
                    pins[str((ROOT/'data/fleet'/Path(r['path']).name).resolve())] = r['sha256']
    # registry_list() skips missing files. Check the complete pinned inventory
    # BEFORE using it; otherwise a partial restore could falsely certify unique.
    for path, expected in pins.items():
        file = Path(path)
        if not file.is_file() or sha(file) != expected:
            raise ValueError(f'missing or changed pinned registry TIFF: {file}')
    entries = []
    scanned = set()
    for label, file in registry_list(exclude=(PREFIX,)):
        key = str(file.resolve())
        scanned.add(key)
        digest = sha(file)
        if key in pins and digest != pins[key]:
            raise ValueError(f'registry hash mismatch: {file}')
        entries.append({'cache_file':str(file.relative_to(ROOT)), 'repo_first':label,
                        'sha256':digest, 'sources':[file.name]})
    if not set(pins).issubset(scanned):
        raise ValueError('some pinned registry TIFFs were omitted by registry_list')
    return {'rasters':entries, 'complete_accessible_scan':True, 'errors':[],
            'scope':'Pinned accessible base/sibling/fleet rasters plus SHA-measured local publications; NOT private/organizer-complete'}


def main():
    start = time.monotonic()
    pre = json.loads((ROOT/'registry/preregistration_phase88.json').read_text())
    assert pre['frozen_before_experiment'] and pre['selected'] == 'PHASE-88'
    gd = verify_sources()
    with rasterio.open(ROOT/'data/training_features.tif') as f:
        surface, channels, stats = build_surface(f.read(2), f.read(13), gd.footprint)
    print('surface ready',time.monotonic()-start,flush=True)
    canaries = leakage_canaries(channels,gd)
    del channels
    if any(v['symmetric_auc'] > .9 for v in canaries.values()):
        raise ValueError('leakage canary tripped: STOP')
    print('canaries ready',time.monotonic()-start,flush=True)
    index = registry_index()
    pre_rows = preplacement_surface_rhos(surface, gd, index)
    pre_max = max((abs(r['rho_full_footprint']) for r in pre_rows
                   if r['rho_full_footprint'] is not None), default=0.)
    save(ROOT/'evidence/phase88_surface_uniqueness.json',pre_rows)
    print('preplacement max |rho|',pre_max,'registry',len(pre_rows),time.monotonic()-start,flush=True)
    # Placement is forbidden if the *surface* is a registered duplicate.
    if pre_max > .90:
        save(ROOT/'registry/phase88_stop.json',{'verdict':'negative','reason':'surface duplicate before placement',
                                              'max_abs_spearman':pre_max,'raster_sha256':None})
        return 0
    crest = directional_crest_1d(surface,distance_transform_edt(gd.footprint)>6)
    coords = np.flatnonzero(crest)
    if len(coords) < N_DOTS: raise ValueError('not enough crest locations')
    coords = coords[np.argsort(-surface.ravel()[coords],kind='stable')]
    yx = np.column_stack(np.unravel_index(coords,gd.shape))
    del coords
    terms = None
    folds_counts=[]
    for seed in pre['holdout_seeds']:
        folds, _ = holdout.buffered_component_draw(gd,seed=seed,buffer_px=3,boundary_px=12)
        visible = folds[0]['visible']
        eligible = crest & gd.footprint & ~folds[0]['masked_known'] & (distance_transform_edt(~visible)>3)
        pred = select_dots(yx, eligible, gd.shape).astype(np.float32)
        for fold in folds:
            _, block_terms = evaluate_holdout.evaluate(pred,fold,gd.footprint)
            terms = block_terms if terms is None else terms + block_terms
            folds_counts.append(int(fold['truth'].sum()))
        print('holdout seed',seed,'complete',time.monotonic()-start,flush=True)
    summary = evaluate_holdout.pooled_summary({'candidate':terms},draws=1000,seed=881025,candidate='candidate')
    score=summary['scores']['candidate']
    if score['withheld_positive_pixels'] != sum(folds_counts): raise ValueError('fold total mismatch')
    inc = json.loads((ROOT/'registry/holdout_result.json').read_text())['scores']['candidate']
    comparable = score['withheld_positive_pixels']==inc['withheld_positive_pixels']
    # Old incumbent terms unavailable; a point comparison is NOT a paired CI.
    print('HOLDOUT-DTI',score['dti'],score['ci95'],'withheld',score['withheld_positive_pixels'],flush=True)
    eligible=crest & gd.footprint & ~gd.catalogue & (distance_transform_edt(~gd.catalogue)>3)
    final=select_dots(yx, eligible, gd.shape)
    stamp=hashlib.sha256(final.tobytes()).hexdigest()[:8]
    name='GEMSDOE88-PHASE-'+stamp.upper()
    note=f'RTP/gravity cross-gradient disagreement; {N_DOTS} dots; HOLDOUT-DTI {score["dti"]:.4f}; UNSCORED; DO NOT SUBMIT'
    path=ROOT/'docs/downloads'/(PREFIX+'-'+stamp+'-DO-NOT-SUBMIT.tif')
    receipt=write_submission(path,final.astype(np.float32),ROOT/'data/bridge/sample_submission.tif',
                             gd.footprint,note=note,name=name,catalogue=gd.catalogue,
                             metadata={'lane':'PHASE-88','slot_authorized':False})
    check=validate_artifact(path,ROOT/'data/bridge/sample_submission.tif')
    zip_check=portal_validate(path.with_suffix('.zip'), ROOT/'data/bridge/sample_submission.tif',footprint=gd.footprint)
    if not check['ok'] or not zip_check['ok']: raise ValueError('on-disk TIFF/ZIP validation failed')
    print('TIFF written and disk validated; uniqueness not yet checked',time.monotonic()-start,flush=True)
    reg=uniqueness.compare_to_registry(path,index,gd.footprint,
                            include_reverse=False,expected_grid=(gd.shape,gd.crs,gd.transform))
    for row in reg['rows']:
        row['file']=str(Path(row['file']).relative_to(ROOT))
    reg['my_file']=str(path.relative_to(ROOT))
    save(ROOT/'evidence/phase88_final_uniqueness.json',reg)
    overlap=reg['worst_dot_overlap']
    duplicate=bool(reg['stop_required'] or pre_max > .90 or overlap > .70)
    card={'schema':'gems88.phase88.run-card.v1','hypothesis':pre['ranking'][0]['off_catalogue_rationale'],
          'mechanism':pre['ranking'][0]['physical_signature'],
          'named_non_fault_process':pre['ranking'][0]['non_fault_mimic'],
          'lane':'PHASE-88','source_pins':{'sample':grid.SHA256_SAMPLE_SUBMISSION,
                    'catalogue':grid.SHA256_EXISTING_FAULTS,
                    'features':sha(ROOT/'data/training_features.tif')},
          'surface_input_stats':stats,'leakage_canary':canaries,
          'holdout_dti':score,'holdout_evaluator':summary['evaluator_version'],
          'holdout_bootstrap':summary['bootstrap'],'incumbent_holdout_dti':inc,
          'comparable_to_incumbent_same_split':comparable,'paired_improvement_ci95':None,
          'correlation_overlap_vs_registry':{'preplacement_max_abs_rho':pre_max,
                'final_max_abs_rho':max((abs(r['spearman_full_footprint']) for r in reg['rows']
                                           if r.get('spearman_full_footprint') is not None),default=0.),
                'final_overlap_3px':overlap,'worst_registry_raster':reg['worst_overlap_submission'],
                'registry_rasters_checked':reg['registry_rasters_checked'],
                'literal_duplicate':duplicate,'full_rows':'evidence/phase88_final_uniqueness.json'},
          'raster_sha256':receipt['sha256'], 'validator_output':check,
          'zip_validation_ok':zip_check['ok'],'download':str(path.relative_to(ROOT)),
          'submission_name':name,'submission_note':note,'ok_to_download':True,
          'ok_to_submit':False,'verdict':'negative','organizer_confirmed_score':None,
          'weekly_slots_used':0,'experiments_run':1,
          'stop_reason':('DUPLICATE under literal 3-px overlap: stop.' if duplicate else
             'No positive paired improvement CI; no demonstrated superiority to best on identical split.'),
          'elapsed_seconds':round(time.monotonic()-start,1)}
    save(ROOT/'registry/phase88_run_card.json',card)
    save(ROOT/'docs/data/phase88_run_card.json',card)
    print('FINAL',card['stop_reason'],'overlap',overlap,'sha',receipt['sha256'],flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
