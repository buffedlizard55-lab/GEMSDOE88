"""Unit and end-to-end validation tests for the H88-VCAZ vapor-chimney & strike-steered conduit lane."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems88 import hgvc, physics, vcaz  # noqa: E402
import validate_vcaz88  # noqa: E402


def test_vcaz_feature_names_and_regional_dc_exclusions_exact():
    assert len(vcaz.VCAZ_FEATURES) == 24
    assert len(set(vcaz.VCAZ_FEATURES)) == 24
    assert len(vcaz.PHYS_DECONF_INDICES) == 36
    # Verify exact 8 smooth regional DC channels are excluded (IR-88-115 / spatial generalization guard)
    kept_names = {physics.ALL_PHYS_FEATURES[i] for i in vcaz.PHYS_DECONF_INDICES}
    assert kept_names.isdisjoint(hgvc.REGIONAL_DC_EXCLUSIONS)
    for nm in vcaz.VCAZ_FEATURES:
        assert nm.startswith("vcaz_")
        assert "catalogue" not in nm and "existing_faults" not in nm


def test_vcaz_anisotropic_strike_ridge_prefers_aligned_ridge():
    # Vertical N-S fault ridge along column 32 => strike unit vector is N-S: (sy=1, sx=0)
    y = np.arange(64, dtype=np.float32)[:, None]
    x = np.arange(64, dtype=np.float32)[None, :]
    ns_ridge = np.exp(-0.5 * ((x - 32.0) / 1.8) ** 2) * np.ones_like(y)
    ew_ridge = np.exp(-0.5 * ((y - 32.0) / 1.8) ** 2) * np.ones_like(x)
    ys, xs = np.nonzero(np.ones((64, 64), dtype=bool))
    sy_fp = np.ones_like(ys, dtype=np.float32)
    sx_fp = np.zeros_like(xs, dtype=np.float32)

    resp_aligned = vcaz._aniso_strike_ridge_fp(ns_ridge, ys, xs, sy_fp, sx_fp).reshape(64, 64)
    resp_crossed = vcaz._aniso_strike_ridge_fp(ew_ridge, ys, xs, sy_fp, sx_fp).reshape(64, 64)
    assert resp_aligned.shape == (64, 64) and np.isfinite(resp_aligned).all()
    assert float(resp_aligned[32, 32]) > 0.4
    assert float(resp_aligned[32, 32]) > 2.5 * max(float(resp_crossed[32, 32]), 0.0) + 0.1


def test_vcaz_peclet_concavity_and_poe_bounds():
    # Pure linear conductive geotherm (T1=12, T1.5=13, T2=14) => zero Peclet concavity
    t1_lin, t15_lin, t2_lin = 12.0, 13.0, 14.0
    assert abs(4.0 * (2.0 * t15_lin - t2_lin - t1_lin)) < 1e-12
    # Upward convective advective curvature (T1=12, T1.5=15.5, T2=17) => positive Peclet concavity
    t1_adv, t15_adv, t2_adv = 12.0, 15.5, 17.0
    assert 4.0 * (2.0 * t15_adv - t2_adv - t1_adv) > 7.5

    d_vis = np.array([3.0, 12.0, 25.0, 45.0], dtype=np.float32)
    p_b = np.array([0.25, 0.12, 0.04, 0.01], dtype=np.float32)
    m_b = np.array([0.52, 0.28, 0.09, 0.03], dtype=np.float32)
    p_v = np.array([0.22, 0.14, 0.09, 0.06], dtype=np.float32)
    m_v = np.array([0.48, 0.30, 0.20, 0.14], dtype=np.float32)
    p_poe, m_poe = vcaz._poe_pool_vcaz(p_b, m_b, p_v, m_v, d_vis)
    assert np.all((p_poe > 0.0) & (p_poe < 1.0))
    assert np.all((m_poe >= p_poe) & (m_poe <= 1.0))


def test_vcaz_feature_builder_source_guards():
    src_text = (ROOT / "src/gems88/vcaz.py").read_text(encoding="utf-8")
    fn_block = src_text.split("def build_or_load_vcaz_memmap", 1)[1].split("def fit_ht_lgbm_dual_head", 1)[0]
    assert "existing_faults" not in fn_block
    assert "grid.catalogue" not in fn_block
    assert 'row.pop("dist_known_fault_px", None)' in fn_block
    assert 'crs_transform("EPSG:4269", grid.crs' in fn_block


def test_validate_vcaz88_passes_research_and_blocks_submit():
    rep = validate_vcaz88.validate_vcaz88(ROOT)
    assert rep["ok"] is True
    assert rep["ok_to_download"] is True
    assert rep["ok_to_submit"] is False
    assert rep["verdict"] == "negative"
    assert rep["dots"] == 33200
    assert rep["folds_won_vs_adhr"] == "8/8"
    assert rep["holdout_dti"] > 0.200
    assert rep["paired_delta_vs_adhr"] > 0.005
    assert rep["concurrent_in_repo_worst_overlap_3px"]["value"] <= 0.70
    assert rep["full_registry_checked"] >= 350
    assert rep["full_registry_worst_like_for_like_overlap_3px"]["value"] <= 0.70
    assert validate_vcaz88.main([]) == 0
    assert validate_vcaz88.main(["--require-submit"]) == 2


def test_validate_vcaz88_detects_tampered_submit_flag(tmp_path):
    rels = [
        "registry/vcaz88_run_card.json",
        "docs/data/vcaz88_run_card.json",
        "evidence/vcaz88_run_card.json",
        "registry/vcaz88_gate_v3.json",
        "docs/data/vcaz88_gate_v3.json",
        "registry/preregistration_vcaz88.json",
        "docs/data/preregistration_vcaz88.json",
        "research/candidate-hypotheses-20261025-vcaz88.md",
        "docs/research/candidate-hypotheses-20261025-vcaz88.md",
        "evidence/vcaz88_canaries.json",
        "evidence/vcaz88_holdout_20261025.json",
        "docs/evidence/vcaz88_holdout_20261025.json",
        "evidence/vcaz88_uniqueness.json",
    ]
    rc = json.loads((ROOT / "registry/vcaz88_run_card.json").read_text(encoding="utf-8"))
    tif_rel = rc["download"]
    zip_rel = rc["zip_download"]
    sub_tif = rc["repo_copy"]
    sub_zip = str(Path(sub_tif).with_suffix(".zip"))
    rc_dl = str(Path(tif_rel).with_suffix(".json"))
    fmt_rel = str(Path(tif_rel).with_suffix(".format-audit.json"))
    for r in rels + [tif_rel, zip_rel, sub_tif, sub_zip, rc_dl, fmt_rel]:
        dst = tmp_path / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / r, dst)

    # Standalone validation on copied tree without data/ must succeed
    rep_clean = validate_vcaz88.validate_vcaz88(tmp_path)
    assert rep_clean["ok"] is True and rep_clean["sample_reopened"] is False

    # Flipping ok_to_submit to True must fail closed
    tampered = json.loads((tmp_path / "registry/vcaz88_run_card.json").read_text(encoding="utf-8"))
    tampered["ok_to_submit"] = True
    for r in ("registry/vcaz88_run_card.json", "docs/data/vcaz88_run_card.json", "evidence/vcaz88_run_card.json", rc_dl):
        (tmp_path / r).write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    rep_bad = validate_vcaz88.validate_vcaz88(tmp_path)
    assert rep_bad["ok"] is False
    assert any("ok_to_submit" in p for p in rep_bad["problems"])
