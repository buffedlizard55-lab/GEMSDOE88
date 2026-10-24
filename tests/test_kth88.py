"""KTH research-only product: synthetic physics, frozen verdict, and byte links."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems88.kth_step import build_surface


def test_local_step_not_created_by_missing_survey():
    f = np.ones((64, 64), bool)
    k = np.full((64,64), 40, dtype=np.uint8)
    th = np.full((64,64), 25, dtype=np.uint8)
    rtp = np.zeros((64,64), np.float32)
    k[:,32:] = 80
    rtp[:,31:34] = -100
    surface, channels, meta = build_surface(k, th, rtp, f)
    assert (surface.shape == f.shape and np.isfinite(surface).all()
            and 0 <= surface.min() <= surface.max() <= 1 and surface.sum() > 0)
    assert meta['radiometric_covered_footprint_pixels'] == f.sum()
    k[:10] = 0
    th[:10] = 0
    surface, _, meta = build_surface(k, th, rtp, f)
    assert not surface[:10].any() and meta['radiometric_covered_footprint_pixels'] == 54*64


def test_frozen_research_verdict_cannot_be_read_as_slot_clearance():
    card = json.loads((ROOT/'registry/kth88_run_card.json').read_text())
    published = json.loads((ROOT/'docs/data/kth88_run_card.json').read_text())
    validation = json.loads((ROOT/'docs/data/kth88_validation.json').read_text())
    assert card == published and card['verdict'] == 'negative'
    assert card['ok_to_download'] and not card['ok_to_submit']
    assert card['correlation_overlap_vs_registry']['final_overlap_3px'] > .70
    assert card['holdout_dti']['ci95'][1] < card['incumbent_holdout_dti']['ci95'][0]
    assert card['organizer_confirmed'] is None and card['slots_spent'] == 0
    file = ROOT/card['download']
    assert 'DO-NOT-SUBMIT' in file.name
    assert hashlib.sha256(file.read_bytes()).hexdigest() == card['raster_sha256']
    assert validation['tif_sha256'] == card['raster_sha256']
    assert validation['local_format_audit']['ok'] and validation['ok_to_submit'] is False
    assert len(card['submission_note']) <= 140
