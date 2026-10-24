from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]

from gems88 import adhr, mvrd, physics  # noqa: E402


def test_mvrd_feature_registries_exclude_distance_leakage():
    assert len(mvrd.MVRD_EXTRA_PHYS_FEATURES) == 18
    assert len(mvrd.MPSC_FEATURES) == 62
    assert len(mvrd.MVRD_ALL_FEATURES) == 85
    for name in mvrd.MVRD_ALL_FEATURES:
        assert "dist_known_fault" not in name.lower()
        assert "b19" not in name.lower()


def test_completeness_gated_fusion_zero_flank_bleed_and_self_credit_bounds():
    rng = np.random.default_rng(88024)
    n = 4000
    p_rel = rng.uniform(1e-4, 0.25, size=n).astype(np.float32)
    m_rel = np.clip(p_rel * rng.uniform(1.15, 2.4, size=n), p_rel, 0.95).astype(np.float32)
    p_vis = rng.uniform(1e-4, 0.30, size=n).astype(np.float32)
    m_vis = np.clip(p_vis * rng.uniform(1.10, 2.2, size=n), p_vis, 0.95).astype(np.float32)
    p_hid = rng.uniform(1e-4, 0.20, size=n).astype(np.float32)
    m_hid = np.clip(p_hid * rng.uniform(1.10, 2.2, size=n), p_hid, 0.95).astype(np.float32)
    d_vis = rng.uniform(2.1, 45.0, size=n).astype(np.float32)

    p_f, m_f = mvrd.completeness_gated_fuse(
        p_rel,
        m_rel,
        p_vis,
        m_vis,
        p_hid,
        m_hid,
        d_vis,
        k_target=160.0,
        phys_vis_all_sum=float(p_vis.sum()) * 1.35,
        n_vis_test=220.0,
    )
    assert p_f.dtype == np.float32 and m_f.dtype == np.float32
    assert np.isfinite(p_f).all() and np.isfinite(m_f).all()
    assert float(p_f.min()) >= 0.0 and float(m_f.max()) <= 1.0
    assert np.all(m_f >= p_f)
    assert np.isclose(float(p_f.sum()), 160.0, rtol=0.05)

    # Verify w_blind_max=0 vs w_blind_max=0.42 leaves d_vis <= 3.5 relative mix unaffected before global renorm
    d_near = np.full(n, 2.5, dtype=np.float32)
    p_near_0, _ = mvrd.completeness_gated_fuse(
        p_rel, m_rel, p_vis, m_vis, p_hid, m_hid, d_near, 160.0, float(p_vis.sum()) * 1.35, 220.0, w_blind_max=0.0
    )
    p_near_42, _ = mvrd.completeness_gated_fuse(
        p_rel, m_rel, p_vis, m_vis, p_hid, m_hid, d_near, 160.0, float(p_vis.sum()) * 1.35, 220.0, w_blind_max=0.42
    )
    assert np.allclose(p_near_0, p_near_42, atol=1e-6)


def test_strand_enhance_preserves_mass_and_boosts_collinear_strand():
    h, w = 64, 64
    fp = np.ones((h, w), dtype=bool)
    ys_fp, xs_fp = np.nonzero(fp)
    n_fp = ys_fp.size
    act_idx = np.arange(n_fp, dtype=np.int64)

    # Vertical N-S fault strand along column 32 vs isolated point noise at (32, 12)
    p_grid = np.zeros((h, w), dtype=np.float32)
    p_grid[16:48, 32] = 0.20
    p_grid[32, 12] = 0.20
    m_grid = np.clip(p_grid * 1.8, p_grid, 0.95).astype(np.float32)

    director = {
        "dir_dy_fp": np.ones(n_fp, dtype=np.float32),
        "dir_dx_fp": np.zeros(n_fp, dtype=np.float32),
        "coh_fp": np.full(n_fp, 0.90, dtype=np.float32),
    }

    p_enh_fp, m_enh_fp = mvrd.strand_enhance_probabilities(
        p_grid.ravel(), m_grid.ravel(), act_idx, ys_fp, xs_fp, director, (h, w)
    )
    p_enh = p_enh_fp.reshape(h, w)
    assert np.isclose(float(p_enh_fp.sum()), float(p_grid.sum()), rtol=1e-4)
    assert np.all(m_enh_fp >= p_enh_fp)
    assert float(p_enh[32, 32]) > float(p_enh[32, 12]) * 1.25


def test_mvrd_and_mpsc_zero_test_quadrant_leakage_bit_invariance(tmp_path):
    """Scrambling held-out test-quadrant truth must produce bit-identical predictions."""
    rng = np.random.default_rng(20261024)
    h, w = 140, 160
    fp = np.ones((h, w), dtype=bool)
    fp[:2, :] = False
    catalogue = np.zeros((h, w), dtype=bool)
    visible = np.zeros((h, w), dtype=bool)

    for r0, c0 in ((6, 6), (6, 84), (74, 6), (74, 84)):
        for c_off, vlen in ((0, 8), (24, 24), (50, 50)):
            visible[r0 : r0 + vlen, c0 + c_off] = True
            catalogue[r0 : r0 + vlen, c0 + c_off] = True
            catalogue[r0 : r0 + 46, c0 + c_off + 4 : c0 + c_off + 7] = True

    g = SimpleNamespace(shape=(h, w), footprint=fp, catalogue=catalogue)
    n_fp = int(fp.sum())
    X_phys = rng.normal(size=(n_fp, len(physics.ALL_PHYS_FEATURES))).astype(np.float32)
    X_extra = rng.normal(size=(n_fp, len(mvrd.MVRD_EXTRA_PHYS_FEATURES))).astype(np.float32)
    mpsc_sources = [X_phys, X_extra]
    theta = rng.uniform(0.0, np.pi, size=n_fp).astype(np.float32)
    director = {
        "dir_dy_fp": np.sin(theta).astype(np.float32),
        "dir_dx_fp": np.cos(theta).astype(np.float32),
        "coh_fp": rng.uniform(0.1, 0.9, size=n_fp).astype(np.float32),
    }
    sense = rng.choice([-1, 1], size=(h, w)).astype(np.float32)
    theta_g = rng.uniform(0.0, np.pi, size=(h, w)).astype(np.float32)
    scarp = {
        "cos2": np.cos(2.0 * theta_g).astype(np.float32),
        "sin2": np.sin(2.0 * theta_g).astype(np.float32),
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

    X_v22, dv, cl = adhr.compute_visible_struct_fp(g, visible, sense, scarp, tmp_path, "synth_mvrd")
    test_reg = folds_clean[0]["region"]
    train_reg = fp & ~test_reg
    train_truth_a = np.zeros((h, w), dtype=bool)
    for f in folds_clean[1:]:
        train_truth_a |= f["truth"]

    # Explicit leakage guard must reject leaked test_reg truth
    with pytest.raises(AssertionError, match="Leakage check failed"):
        mvrd.predict_mpsc_fold(
            g, mpsc_sources, director, visible, train_reg, catalogue, test_reg, seed=88
        )
    with pytest.raises(AssertionError, match="Leakage check failed"):
        mvrd.predict_mvrd_fold(
            g, mpsc_sources, X_v22, dv, cl, director, visible, train_reg, catalogue, test_reg, seed=88
        )

    mpsc_a, mpsc_surf_a, _ = mvrd.predict_mpsc_fold(
        g, mpsc_sources, director, visible, train_reg, train_truth_a, test_reg, seed=88
    )
    mvrd_a, mvrd_surf_a, _ = mvrd.predict_mvrd_fold(
        g, mpsc_sources, X_v22, dv, cl, director, visible, train_reg, train_truth_a, test_reg, seed=88
    )

    # Scramble held-out fold-0 ground truth completely
    scrambled_nw_truth = (rng.uniform(size=(h, w)) > 0.25) & q_nw & ~visible
    folds_dirty = [
        {"fold": 0, "region": q_nw & fp, "visible": visible, "truth": scrambled_nw_truth},
        *folds_clean[1:],
    ]
    train_truth_b = np.zeros((h, w), dtype=bool)
    for f in folds_dirty[1:]:
        train_truth_b |= f["truth"]

    mpsc_b, mpsc_surf_b, _ = mvrd.predict_mpsc_fold(
        g, mpsc_sources, director, visible, train_reg, train_truth_b, test_reg, seed=88
    )
    mvrd_b, mvrd_surf_b, _ = mvrd.predict_mvrd_fold(
        g, mpsc_sources, X_v22, dv, cl, director, visible, train_reg, train_truth_b, test_reg, seed=88
    )

    assert np.array_equal(mpsc_a, mpsc_b)
    assert np.array_equal(mpsc_surf_a, mpsc_surf_b)
    assert np.array_equal(mvrd_a, mvrd_b)
    assert np.array_equal(mvrd_surf_a, mvrd_surf_b)


def test_mvrd_production_artifact_zip_and_receipts_integrity():
    import hashlib
    import json
    import zipfile

    import rasterio
    from scipy.ndimage import distance_transform_edt
    from scipy.spatial import cKDTree

    card_paths = [
        ROOT / "registry/mvrd_run_card.json",
        ROOT / "docs/data/mvrd_run_card.json",
        ROOT / "evidence/mvrd_run_card.json",
    ]
    raw_bytes = [p.read_bytes() for p in card_paths]
    for b in raw_bytes[1:]:
        assert b == raw_bytes[0], "Canonical mvrd_run_card.json mirrors must be byte-identical"

    card = json.loads(raw_bytes[0].decode("utf-8"))
    assert card["experiment_id"] == "H88-MVRD-v1"
    assert card["scores_evidence_class"] == "HOLDOUT-DTI"
    assert card["independent_organizer_receipt"] is False
    assert 0 < len(card["submission_name"]) <= 140
    assert 0 < len(card["submission_note"]) <= 140
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert card["portal_layout_parity_with_sample"] is True

    tif_path = ROOT / card["artifact"]
    zip_path = ROOT / card["zip_artifact"]
    assert tif_path.exists() and zip_path.exists()
    assert (tif_path.stat().st_mode & 0o777) == 0o644
    assert (zip_path.stat().st_mode & 0o777) == 0o644
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["zip_sha256"]
    assert card["raster_sha256"] != "f8e56f2a2f5fd6df8738364e2f98bbaf955512c027f9d53b5e404a9fef62eccd"

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        inner_bytes = zf.read(names[0])
        assert hashlib.sha256(inner_bytes).hexdigest() == card["raster_sha256"]

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes == ("float32",)
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.nodata is None
        assert ds.profile["compress"] == "lzw"
        assert not ds.profile["tiled"]
        assert ds.block_shapes[0] == (1, 3292)
        arr = ds.read(1)
        crs = ds.crs
        transform = ds.transform

    assert np.isfinite(arr).all()
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    uniq = set(np.unique(arr).tolist())
    assert uniq == {0.0, 1.0}
    ys, xs = np.nonzero(arr > 0.5)
    assert int(ys.size) == card["emitted_dots"] == 33167

    pts = np.column_stack([ys, xs]).astype(np.float64)
    d_nn, _ = cKDTree(pts).query(pts, k=2)
    assert float(d_nn[:, 1].min()) >= 2.0

    sample_path = ROOT / "data/bridge/sample_submission.tif"
    faults_path = ROOT / "data/bridge/existing_faults.tif"
    if sample_path.exists() and faults_path.exists():
        with rasterio.open(sample_path) as ref:
            assert crs == ref.crs
            assert transform == ref.transform
            ref_arr = ref.read(1)
            fp = np.isfinite(ref_arr) if ref.nodata is None else (ref_arr != ref.nodata) & np.isfinite(ref_arr)
        assert int((arr[~fp] != 0.0).sum()) == 0
        with rasterio.open(faults_path) as fds:
            cat = (fds.read(1) > 0) & fp
        assert int((arr[cat] > 0.0).sum()) == 0
        d_cat = distance_transform_edt(~cat)
        assert float(d_cat[ys, xs].min()) > 2.0

    hr = json.loads((ROOT / "evidence/mvrd88_holdout.json").read_text())
    pooled = {k: v["dti"] for k, v in hr["scores"].items()}
    assert (
        pooled["h88_mvrd"]
        > pooled["h88_adhr"]
        > pooled["mpsc_88"]
        > pooled["cgo_88"]
        > pooled["mgc_88"]
        > pooled["raw_control"]
    )
    for cmp_key in ("h88_adhr", "mpsc_88", "cgo_88", "mgc_88", "raw_control"):
        assert hr["paired_differences"][cmp_key]["ci95"][0] > 0.0

    gv = json.loads((ROOT / "registry/mvrd_gate_v3.json").read_text())
    assert (ROOT / "docs/data/mvrd-gate-v3.json").read_text() == (ROOT / "registry/mvrd_gate_v3.json").read_text()
    assert gv["policy"] == "gems88-gate-v3"
    assert gv["ok_to_download"] is True and gv["ok_to_submit"] is False
    assert gv["holdout_cross_run"]["beats_bar"] is True
    assert gv["uniqueness"]["registry_rasters"] >= 200
    assert gv["uniqueness"]["unique_like_for_like"] is True
    assert gv["uniqueness"]["worst_like_for_like_overlap"]["value"] <= 0.70

    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_release import mvrd_report_v3

    rep = mvrd_report_v3(ROOT)
    assert rep["ok_to_download"] is True and rep["ok_to_submit"] is False
    assert rep["beats_holdout_bar"] is True and rep["unique_like_for_like"] is True

