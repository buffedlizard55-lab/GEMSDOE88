import numpy as np
from gems88.pgtd88 import PGTD_FEATURES, tensor_channels
def test_sheet_step_vs_blob():
    yy, xx = np.mgrid[0:64, 0:64]
    step = np.where(xx >= 32, 10.0, 0.0).astype(np.float32)
    vg = np.zeros_like(step)
    sheet, sxg, dim, aniso, grad = tensor_channels(step, vg)
    assert np.isfinite(sheet).all() and sheet.min() >= 0 and sheet.max() <= 1
    assert float(np.median(sheet[8:-8, 30:35])) > 0.5  # 2D sheet: det~0
    assert len(PGTD_FEATURES) == 12
