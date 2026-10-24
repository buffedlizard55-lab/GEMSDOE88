"""PHASE-88 physics and machine-release safety, no portal or manual inspector."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from gems88.phase88 import build_surface
from validate_phase88 import inspect
import run_phase88


def test_missing_pinned_sibling_fails_closed(tmp_path, monkeypatch):
    import hashlib
    (tmp_path/'registry').mkdir()
    # The baseline file is present but the sibling manifest points to a
    # missing TIFF. registry_list() would silently skip it; index must not.
    (tmp_path/'data/registry').mkdir(parents=True)
    base=tmp_path/'data/registry/base.tif';base.write_bytes(b'fixture')
    digest=hashlib.sha256(base.read_bytes()).hexdigest()
    (tmp_path/'registry/inventory.json').write_text(json.dumps({
        'complete_accessible_scan':True,'errors':[],
        'rasters':[{'cache_file':'data/registry/base.tif','sha256':digest}]}))
    (tmp_path/'registry/sibling_inventory.json').write_text(json.dumps({
        'sites':{'GEMSDOE87':{'files':[{'kind':'tif','path':'docs/x.tif','sha256':digest}]}}}))
    monkeypatch.setattr(run_phase88,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='missing or changed pinned registry TIFF'):
        run_phase88.registry_index()


def test_finite_shape_and_no_catalogue_dependency():
    y,x=np.mgrid[:96,:96]
    m=(x*x/400 + np.sin(y/11.)).astype(np.float32)
    g=(y*y/400 + np.cos(x/13.)).astype(np.float32)
    fp=np.ones((96,96),bool);fp[:3]=False
    m[:3]=-3.4e38;g[:3]=-3.4e38
    surface, channels, stats=build_surface(m,g,fp)
    assert surface.shape==fp.shape and np.isfinite(surface).all()
    assert 0<=surface.min()<=surface.max()<=1
    assert not surface[~fp].any()
    assert set(channels)=={'gradient_misalignment','rtp_gradient_strength','gravity_gradient_strength','phase_surface'}
    assert stats['rtp']['invalid_inside']==0
    with pytest.raises(ValueError):build_surface(m,g[:10],fp)


def test_phase_frozen_card_and_format_recheck():
    card=json.loads((ROOT/'registry/phase88_run_card.json').read_text())
    file=ROOT/card['download']
    assert file.name.endswith('DO-NOT-SUBMIT.tif')
    assert card['ok_to_download'] and not card['ok_to_submit']
    assert card['verdict']=='negative' and card['weekly_slots_used']==0
    assert len(card['submission_note'])<=140
    assert hashlib.sha256(file.read_bytes()).hexdigest()==card['raster_sha256']
    h=card['holdout_dti']; prior=card['incumbent_holdout_dti']
    assert h['evaluator_version']=='gems57-pooled-hide-v2'
    assert h['withheld_positive_pixels']==prior['withheld_positive_pixels']==22893
    assert h['ci95'][1]<prior['ci95'][0]
    assert card['correlation_overlap_vs_registry']['final_overlap_3px']>.70
    assert all(v['symmetric_auc']<=.90 for v in card['leakage_canary'].values())
    if not (ROOT/'data/bridge/sample_submission.tif').exists():
        pytest.skip('hash-pinned validation inputs absent; restore_inputs.py --validation')
    audit=inspect()
    assert audit==json.loads((ROOT/'docs/data/phase88_validation.json').read_text())
    assert audit['local_format_audit']['ok']
    assert not audit['ok_to_submit']
