"""Unit and release-artifact tests for the QTS-88 method lane."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from gems88.qts88 import (
    QTS_CHANNEL_NAMES,
    allocate_dual_regime_qts,
    clean_competition_band,
    compute_decoupled_thickness_slope,
    compute_qts_channels_from_bands,
    fast_pack_separated,
)
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "scripts", ROOT / "vendor"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from validate_qts88 import main as validate_qts88_main, qts88_release_report  # noqa: E402


def test_clean_competition_band_masks_float32_nodata_sentinel():
    fp = np.ones((20, 20), dtype=bool)
    fp[:2, :] = False
    arr = np.full((20, 20), 100.0, dtype=np.float32)
    arr[5, 5] = np.float32(-3.4028235e38)
    arr[6, 6] = np.nan
    arr[7, 7] = np.inf
    cleaned = clean_competition_band(arr, fp)
    assert np.isfinite(cleaned).all()
    assert (cleaned[~fp] == 0.0).all()
    assert np.allclose(cleaned[fp], 100.0)


def test_compute_decoupled_thickness_slope_directional_identities():
    yy, xx = np.mgrid[:40, :40].astype(np.float32)
    fp = np.ones((40, 40), dtype=bool)

    # Case 1: parallel gradients (z_base = 2*xx, z_surf = 3*xx -> cos = +1)
    res_par = compute_decoupled_thickness_slope(2.0 * xx, 3.0 * xx, fp, sigma=0.0)
    assert np.allclose(res_par["same"][5:-5, 5:-5], 0.0, atol=1e-4)
    assert np.allclose(res_par["anti"][5:-5, 5:-5], 4.0, atol=1e-4)
    assert np.allclose(res_par["orth"][5:-5, 5:-5], 0.0, atol=1e-4)

    # Case 2: antiparallel gradients (z_base = 2*xx, z_surf = -3*xx -> cos = -1)
    res_anti = compute_decoupled_thickness_slope(2.0 * xx, -3.0 * xx, fp, sigma=0.0)
    assert np.allclose(res_anti["same"][5:-5, 5:-5], 4.0, atol=1e-4)
    assert np.allclose(res_anti["anti"][5:-5, 5:-5], 0.0, atol=1e-4)

    # Case 3: orthogonal gradients (z_base = 2*xx, z_surf = 3*yy -> sin = 1, cos = 0)
    res_orth = compute_decoupled_thickness_slope(2.0 * xx, 3.0 * yy, fp, sigma=0.0)
    assert np.allclose(res_orth["same"][5:-5, 5:-5], 2.0, atol=1e-4)
    assert np.allclose(res_orth["orth"][5:-5, 5:-5], 2.0, atol=1e-4)


def test_compute_qts_channels_and_dual_regime_allocator():
    rng = np.random.default_rng(88)
    fp = np.ones((80, 80), dtype=bool)
    fp[0, :] = False
    z_base = rng.normal(300.0, 50.0, size=(80, 80)).astype(np.float32)
    z_surf = rng.normal(0.0, 20.0, size=(80, 80)).astype(np.float32)
    slope = np.abs(rng.normal(4.0, 2.0, size=(80, 80))).astype(np.float32)
    ghg = rng.normal(0.0, 1.0, size=(80, 80)).astype(np.float32)
    gvg = rng.normal(0.0, 1.0, size=(80, 80)).astype(np.float32)
    dil = rng.normal(2.0, 3.0, size=(80, 80)).astype(np.float32)
    shr = np.abs(rng.normal(8.0, 2.0, size=(80, 80))).astype(np.float32)
    cnd = np.abs(rng.normal(2.5, 0.5, size=(80, 80))).astype(np.float32)

    surf, ch = compute_qts_channels_from_bands(
        z_base, z_surf, slope, ghg, gvg, dil, shr, cnd, fp
    )
    assert set(ch.keys()) == set(QTS_CHANNEL_NAMES)
    assert np.isfinite(surf).all()
    assert (surf >= 0.0).all() and (surf <= 1.0).all()
    assert (surf[~fp] == 0.0).all()

    cat = np.zeros((80, 80), dtype=bool)
    cat[40, 10:30] = True
    d_cat = distance_transform_edt(~cat)
    dots = allocate_dual_regime_qts(
        surf, fp, d_cat, known_mask=cat, sep_px=3.5, n_near=30, n_far=20, collar_px=3.0, far_px=25.0
    )
    assert int(dots.sum()) == 50
    assert float(d_cat[dots].min()) > 3.0
    assert float((d_cat[dots] > 25.0).mean()) == 20 / 50
    pts = np.argwhere(dots).astype(np.float64)
    d_nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    assert float(d_nn.min()) >= 3.5 - 1e-6


def test_qts88_release_report_and_fail_closed_gate():
    import pytest

    if not (ROOT / "data/bridge/existing_faults.tif").is_file():
        pytest.skip("data/bridge/existing_faults.tif not restored")
    rep = qts88_release_report()
    assert rep["ok_to_download"] is True
    assert rep["ok_to_submit"] is False
    assert rep["portal_and_like_for_like_unique_ok"] is True
    assert rep["fingerprint_screen_pass"] is True
    assert rep["verdict"] == "negative"
    assert rep["paired_lift_over_raw19"] > 0.005
    assert rep["paired_lift_ci95"][0] > 0.0
    assert validate_qts88_main([]) == 0
    assert validate_qts88_main(["--require-submit"]) == 2
