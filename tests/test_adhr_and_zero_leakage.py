from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems88 import adhr, physics  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_calibrated_fusion_preserves_self_credit_dominance_and_bounds():
    rng = np.random.default_rng(8801)
    n = 5000
    p_full = rng.uniform(1e-4, 0.25, size=n).astype(np.float32)
    m_full = np.clip(p_full * rng.uniform(1.2, 2.5, size=n), p_full, 0.95).astype(np.float32)
    p_phys = rng.uniform(1e-4, 0.20, size=n).astype(np.float32)
    m_phys = np.clip(p_phys * rng.uniform(1.1, 2.2, size=n), p_phys, 0.95).astype(np.float32)

    p_out, m_out = adhr._fuse_log_odds(p_full, m_full, p_phys, m_phys, k_target=180.0)
    assert p_out.dtype == np.float32 and m_out.dtype == np.float32
    assert np.isfinite(p_out).all() and np.isfinite(m_out).all()
    assert float(p_out.min()) >= 0.0 and float(m_out.max()) <= 1.0
    assert np.all(m_out >= p_out)
    assert np.isclose(float(p_out.sum()), 180.0, rtol=0.05)


def test_zero_test_quadrant_truth_leakage_bit_identical_under_scrambling(tmp_path):
    """Corrupting held-out test-quadrant truth must not alter a single predicted bit."""
    rng = np.random.default_rng(20261022)
    h, w = 150, 180
    fp = np.ones((h, w), dtype=bool)
    fp[:2, :] = False
    catalogue = np.zeros((h, w), dtype=bool)
    visible = np.zeros((h, w), dtype=bool)

    # Plant synthetic visible traces across 3 distinct length bins (8, 25, 55 px) + >=250 positives/bin
    for r0, c0 in ((6, 6), (6, 94), (78, 6), (78, 94)):
        for c_off, vlen in ((0, 8), (28, 25), (58, 55)):
            visible[r0 : r0 + vlen, c0 + c_off] = True
            catalogue[r0 : r0 + vlen, c0 + c_off] = True
            catalogue[r0 : r0 + 50, c0 + c_off + 3 : c0 + c_off + 7] = True

    g = SimpleNamespace(shape=(h, w), footprint=fp, catalogue=catalogue)
    n_fp = int(fp.sum())
    X_cgo = rng.normal(size=(n_fp, len(physics.CGO_FEATURES))).astype(np.float32)
    X_phys = rng.normal(size=(n_fp, len(physics.ALL_PHYS_FEATURES))).astype(np.float32)
    sense = rng.choice([-1, 1], size=(h, w)).astype(np.float32)
    theta = rng.uniform(0.0, np.pi, size=(h, w)).astype(np.float32)
    scarp = {
        "cos2": np.cos(2.0 * theta).astype(np.float32),
        "sin2": np.sin(2.0 * theta).astype(np.float32),
        "coherence": rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32),
    }

    q_nw = np.zeros((h, w), dtype=bool)
    q_nw[: h // 2, : w // 2] = True
    q_ne = np.zeros((h, w), dtype=bool)
    q_ne[: h // 2, w // 2 :] = True
    q_sw = np.zeros((h, w), dtype=bool)
    q_sw[h // 2 :, : w // 2] = True
    q_se = np.zeros((h, w), dtype=bool)
    q_se[h // 2 :, w // 2 :] = True

    hidden = catalogue & ~visible
    folds_clean = [
        {"fold": 0, "region": q_nw & fp, "visible": visible, "truth": hidden & q_nw},
        {"fold": 1, "region": q_ne & fp, "visible": visible, "truth": hidden & q_ne},
        {"fold": 2, "region": q_sw & fp, "visible": visible, "truth": hidden & q_sw},
        {"fold": 3, "region": q_se & fp, "visible": visible, "truth": hidden & q_se},
    ]

    X_v22, dv, cl = adhr.compute_visible_struct_fp(g, visible, sense, scarp, tmp_path, "synth")
    test_reg = folds_clean[0]["region"]
    train_reg = fp & ~test_reg
    train_truth_a = np.zeros((h, w), dtype=bool)
    for f in folds_clean[1:]:
        train_truth_a |= f["truth"]

    cgo_a, _, _ = adhr.predict_cgo_fold(g, X_cgo, visible, train_reg, train_truth_a, test_reg, seed=77)
    adhr_a, surf_a, _ = adhr.predict_adhr_fold(
        g, X_phys, X_v22, dv, cl, visible, train_reg, train_truth_a, test_reg, seed=77
    )

    # 1. Explicit guard must reject any attempt to leak test_region truth into train_truth
    import pytest
    with pytest.raises(AssertionError, match="Leakage check failed"):
        adhr.predict_adhr_fold(g, X_phys, X_v22, dv, cl, visible, train_reg, catalogue, test_reg, seed=77)
    with pytest.raises(AssertionError, match="Leakage check failed"):
        adhr.predict_cgo_fold(g, X_cgo, visible, train_reg, catalogue, test_reg, seed=77)

    # 2. Completely scramble held-out test-quadrant (fold 0) ground truth and re-derive fold inputs
    scrambled_nw_truth = (rng.uniform(size=(h, w)) > 0.25) & q_nw & ~visible
    folds_dirty = [
        {"fold": 0, "region": q_nw & fp, "visible": visible, "truth": scrambled_nw_truth},
        *folds_clean[1:],
    ]
    train_truth_b = np.zeros((h, w), dtype=bool)
    for f in folds_dirty[1:]:
        train_truth_b |= f["truth"]

    cgo_b, _, _ = adhr.predict_cgo_fold(g, X_cgo, visible, train_reg, train_truth_b, test_reg, seed=77)
    adhr_b, surf_b, _ = adhr.predict_adhr_fold(
        g, X_phys, X_v22, dv, cl, visible, train_reg, train_truth_b, test_reg, seed=77
    )

    np.testing.assert_array_equal(cgo_a, cgo_b)
    np.testing.assert_array_equal(adhr_a, adhr_b)
    np.testing.assert_array_equal(surf_a, surf_b)


def test_h88_adhr_candidate_artifact_zip_and_19_raster_receipts():
    rc = json.loads((ROOT / "registry/run_card.json").read_text())
    assert rc == json.loads((ROOT / "docs/run_card.json").read_text())
    assert rc == json.loads((ROOT / "docs/data/run-card.json").read_text())

    tif = ROOT / rc["artifact"]
    zpath = ROOT / rc["zip_artifact"]
    assert tif.is_file() and zpath.is_file()
    assert _sha256(tif) == rc["raster_sha256"]
    assert _sha256(zpath) == rc["zip_sha256"]
    assert 0 < len(rc["submission_name"]) <= 140
    assert 0 < len(rc["submission_note"]) <= 140

    with zipfile.ZipFile(zpath) as zf:
        assert zf.namelist() == [tif.name]
        assert zf.read(tif.name) == tif.read_bytes()

    with rasterio.open(tif) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert ds.nodata is None
        arr = ds.read(1)

    assert np.isfinite(arr).all()
    uniq = set(np.unique(arr).tolist())
    assert uniq == {0.0, 1.0}
    assert int((arr > 0).sum()) == rc["emitted_dots"]
    assert 25000 <= rc["emitted_dots"] <= 42000

    if (ROOT / "data/bridge/existing_faults.tif").is_file():
        with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as cf:
            cat = cf.read(1) > 0
        assert int((arr[cat] > 0).sum()) == 0

    two_phase = json.loads((ROOT / "registry/two_phase_uniqueness.json").read_text())
    assert two_phase["rasters_checked"] == 21
    assert two_phase["like_for_like_reading"]["dot_field_rasters"] == 20
    assert two_phase["like_for_like_reading"]["forward_overlap_firings"] == 0
    assert two_phase["like_for_like_reading"]["duplicate"] is False
    assert two_phase["literal_reading"]["duplicate"] is True
    assert rc["ok_to_download"] is True and rc["ok_to_submit"] is False
    assert rc["independent_organizer_receipt"] is False
    assert rc["budget"]["weekly_slots_used"] == 0
    assert rc["budget"]["organizer_confirmed_score"] is None
    assert rc["budget"]["experiments_run"] <= 3


def test_feature_dimensions_and_evidence_labels_consistent():
    assert len(physics.CGO_FEATURES) == 26
    assert len(physics.EXT_PHYS_FEATURES) == 18
    assert len(physics.ALL_PHYS_FEATURES) == 44
    assert len(adhr.VIS_STRUCT_FEATURES) == 23
    canaries = json.loads((ROOT / "registry/leakage_canaries.json").read_text())
    assert canaries["adhr_features_tested"] == 67
    assert canaries["features_tested"] == 74
    assert canaries["passed"] is True and canaries["all_pass"] is True
    assert canaries["max_symmetric_auc"] <= 0.90

    holdout = json.loads((ROOT / "registry/holdout_result.json").read_text())
    assert holdout["evidence_class"] == "HOLDOUT-DTI"
    assert holdout["evaluator_version"] == "gems57-pooled-hide-v2"
    scores = holdout["scores"]
    assert scores["h88_adhr"]["dti"] > scores["cgo_88"]["dti"] > scores["mgc_88"]["dti"] > scores["raw_control"]["dti"]
    assert len(holdout["folds"]) == 8
    for fold in holdout["folds"]:
        assert fold["h88_adhr"]["dti"] > fold["cgo_88"]["dti"] > fold["mgc_88"]["dti"]
        assert fold["h88_adhr"]["dti"] > fold["raw_control"]["dti"]

