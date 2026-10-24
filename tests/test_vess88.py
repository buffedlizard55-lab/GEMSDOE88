import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88.vess import VESS_FEATURES, vesselness  # noqa: E402


def test_vesselness_line_beats_blob():
    fp = np.ones((64, 64), dtype=bool)
    g_line = np.zeros((64, 64), np.float32)
    g_line[30:34, :] = 1.0  # straight bright ridge (step edge)
    g_blob = np.zeros((64, 64), np.float32)
    yy, xx = np.mgrid[:64, :64]
    g_blob[np.hypot(yy - 32, xx - 32) < 4] = 1.0  # equant blob
    v_line = vesselness(g_line, fp, 1.5)
    v_blob = vesselness(g_blob, fp, 1.5)
    assert np.isfinite(v_line).all() and np.isfinite(v_blob).all()
    assert v_line.min() >= 0.0 and v_line.max() <= 1.0
    # ridge centre responds more strongly than blob centre
    assert v_line[32, 32] > v_blob[32, 32]


def test_vess_feature_names_unique_12():
    assert len(VESS_FEATURES) == 12 and len(set(VESS_FEATURES)) == 12
