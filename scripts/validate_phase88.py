#!/usr/bin/env python3
"""Independent on-disk research-only preflight. --require-submit exits 2.

Rechecks the pinned grid, TIFF, ZIP and literal dense witness from bytes;
full 223-raster registry measurements are frozen in phase88_final_uniqueness.json
and require restored siblings/fleet to rerun. Never equate local format with
organizer acceptance or selector authorization.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor'),str(ROOT/'src'),str(ROOT/'scripts')]
from gems57 import grid, uniqueness
from gems88.gate import portal_validate
from validate_artifact import validate_artifact
import numpy as np
import rasterio


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def inspect(root=ROOT):
    root=Path(root)
    card=json.loads((root/'registry/phase88_run_card.json').read_text())
    pub=json.loads((root/'docs/data/phase88_run_card.json').read_text())
    evidence=json.loads((root/'evidence/phase88_final_uniqueness.json').read_text())
    if card!=pub or card['verdict']!='negative' or card['ok_to_submit'] is not False:
        raise ValueError('published phase run card inconsistent')
    tif=root/card['download']; archive=tif.with_suffix('.zip')
    if not tif.is_relative_to(root/'docs/downloads') or not tif.name.endswith('-DO-NOT-SUBMIT.tif'):
        raise ValueError('unsafe file name/path')
    sample=root/'data/bridge/sample_submission.tif'; labels=root/'data/bridge/existing_faults.tif'
    if sha(sample)!=grid.SHA256_SAMPLE_SUBMISSION or sha(labels)!=grid.SHA256_EXISTING_FAULTS:
        raise ValueError('restored owner grid hash mismatch')
    if sha(tif)!=card['raster_sha256'] or card['validator_output']['raster_sha256']!=sha(tif):
        raise ValueError('raster sha mismatch')
    receipt=json.loads(tif.with_suffix('.json').read_text())
    if (receipt['sha256']!=sha(tif) or receipt['zip_sha256']!=sha(archive) or
        receipt['note']!=card['submission_note'] or receipt['submission_name']!=card['submission_name'] or
        not 0<len(card['submission_note'])<=140):
        raise ValueError('writer receipt/note mismatch')
    with zipfile.ZipFile(archive) as z:
        if z.namelist()!=[tif.name] or z.testzip() is not None or z.read(tif.name)!=tif.read_bytes():
            raise ValueError('ZIP is not one byte-identical TIFF')
    gd=grid.load_grid(root/'data/bridge')
    check=validate_artifact(tif,sample)
    zip_check=portal_validate(archive,sample,footprint=gd.footprint)
    if not check['ok'] or not zip_check['ok']:
        raise ValueError('reopened TIFF/ZIP failed format check')
    with rasterio.open(tif) as ds:
        a=ds.read(1)
    if int((a>0).sum())!=37654 or np.any((a>0)&gd.catalogue):
        raise ValueError('dot budget/catalogue exclusion drifted')
    # This is a real independent spatial test, not a copied run-card value.
    dense=root/'data/registry/dense_17gemdoe.tif'
    index=json.loads((root/'registry/inventory.json').read_text())
    pinned=[r['sha256'] for r in index['rasters'] if r['cache_file']=='data/registry/dense_17gemdoe.tif']
    if pinned!=[sha(dense)]: raise ValueError('dense witness pin mismatch')
    with rasterio.open(dense) as ds:
        if (ds.shape,ds.crs,ds.transform)!=(gd.shape,gd.crs,gd.transform):
            raise ValueError('dense witness grid mismatch')
        other=ds.read(1)
    overlap=uniqueness.dot_overlap(a,other,3)
    if overlap!=1. or overlap!=card['correlation_overlap_vs_registry']['final_overlap_3px']:
        raise ValueError('literal duplicate witness mismatch')
    if (evidence['candidate_file_sha256']!=sha(tif) or
        evidence['registry_rasters_checked']!=card['correlation_overlap_vs_registry']['registry_rasters_checked'] or
        evidence['missing_or_invalid']!=0 or evidence['worst_dot_overlap']!=overlap or
        not any(r['submission'].startswith('GEMSDOE87__') and r['my_dots_within_3px_of_theirs']>.70 for r in evidence['rows'])):
        raise ValueError('frozen registry measurement inconsistent')
    h=card['holdout_dti']; inc=card['incumbent_holdout_dti']
    if (h['evaluator_version']!='gems57-pooled-hide-v2' or h['withheld_positive_pixels']!=22893 or
        h['ci95'][1]>=inc['ci95'][0] or
        max(v['symmetric_auc'] for v in card['leakage_canary'].values())>.90):
        raise ValueError('negative holdout/canary record inconsistent')
    return {'ok_to_download':True,'ok_to_submit':False,'tif_sha256':sha(tif),
            'zip_sha256':sha(archive),'tif_and_single_member_zip_validated':True,
            'local_format_audit':check,'literal_witness_remeasured_overlap_3px':overlap,
            'full_registry_scope':'frozen SHA-verified scan at generation; see evidence/phase88_final_uniqueness.json',
            'reason':card['stop_reason'],'organizer_accepted':None}


def main():
    args=argparse.ArgumentParser();args.add_argument('--require-submit',action='store_true'); ns=args.parse_args()
    report=inspect()
    out=ROOT/'docs/data/phase88_validation.json'
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='local_format_audit'},indent=2))
    return 2 if ns.require_submit else 0

if __name__=='__main__':raise SystemExit(main())
