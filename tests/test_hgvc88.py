"""Unit and end-to-end validation tests for the H88-HGVC hydrothermal conduit lane."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems88 import hgvc  # noqa: E402
import validate_hgvc88  # noqa: E402


def test_hgvc_feature_names_and_regional_exclusions_disjoint():
    assert len(hgvc.HGVC_FEATURES) == 20
    assert len(set(hgvc.HGVC_FEATURES)) == 20
    assert len(hgvc.PHYS_DIFF_INDICES) == 36
    # Ensure zero catalogue-derived feature names in HGVC_FEATURES
    for nm in hgvc.HGVC_FEATURES:
        assert nm.startswith("hgvc_")
        assert "catalogue" not in nm and "existing_faults" not in nm


def test_hgvc_operators_finite_and_ridge_selective():
    rng = np.random.default_rng(88)
    grid_2d = np.zeros((64, 64), dtype=np.float32)
    # Create a sharp linear ridge along column 32
    xs = np.arange(64, dtype=np.float32)[None, :]
    grid_2d[:] = np.exp(-0.5 * ((xs - 32.0) / 1.8) ** 2) + 0.02 * rng.standard_normal((64, 64)).astype(np.float32)

    crest = hgvc._hessian_crest(grid_2d, sigma=2.0)
    vessel = hgvc._frangi_line_2d(grid_2d, sigma=2.0)
    assert crest.shape == (64, 64) and np.isfinite(crest).all() and (crest >= 0.0).all()
    assert vessel.shape == (64, 64) and np.isfinite(vessel).all() and (vessel >= 0.0).all()
    assert float(crest[:, 32].mean()) > 4.0 * float(crest[:, 8].mean() + 1e-6)
    assert float(vessel[:, 32].mean()) > 4.0 * float(vessel[:, 8].mean() + 1e-6)


def test_hgvc_structure_tensor_strike_alignment():
    # Two synthetic fields stepping across the same vertical N-S fault (strike = pi/2)
    x = np.linspace(-5.0, 5.0, 48, dtype=np.float32)[None, :]
    f1 = np.tanh(x * np.ones((48, 1), dtype=np.float32))
    f2 = -2.0 * np.tanh(x * np.ones((48, 1), dtype=np.float32))  # opposite sign, same strike!
    gy1 = np.gradient(f1, axis=0).astype(np.float32)
    gx1 = np.gradient(f1, axis=1).astype(np.float32)
    gy2 = np.gradient(f2, axis=0).astype(np.float32)
    gx2 = np.gradient(f2, axis=1).astype(np.float32)
    c1, s1 = hgvc._structure_tensor_2theta(gy1, gx1, sigma_int=2.0)
    c2, s2 = hgvc._structure_tensor_2theta(gy2, gx2, sigma_int=2.0)
    kappa = np.hypot(0.5 * (c1 + c2), 0.5 * (s1 + s2))
    assert float(kappa[24, 24]) > 0.99


def test_hgvc_poe_pool_preserves_self_credit_inequality():
    d_vis = np.array([3.0, 12.0, 25.0, 45.0], dtype=np.float32)
    p_b = np.array([0.20, 0.10, 0.02, 0.01], dtype=np.float32)
    m_b = np.array([0.45, 0.25, 0.06, 0.03], dtype=np.float32)
    p_h = np.array([0.25, 0.15, 0.08, 0.07], dtype=np.float32)
    m_h = np.array([0.50, 0.32, 0.18, 0.16], dtype=np.float32)
    p_poe, m_poe = hgvc.poe_pool_hgvc(p_b, m_b, p_h, m_h, d_vis)
    assert np.all((p_poe > 0.0) & (p_poe < 1.0))
    assert np.all(m_poe >= p_poe) and np.all(m_poe <= 1.0)


def test_hgvc_source_never_reads_existing_faults_in_feature_builder():
    src_text = (ROOT / "src/gems88/hgvc.py").read_text(encoding="utf-8")
    fn_block = src_text.split("def build_or_load_hgvc_memmap", 1)[1].split("def poe_pool_hgvc", 1)[0]
    assert "existing_faults" not in fn_block
    assert "grid.catalogue" not in fn_block
    assert 'r.pop("dist_known_fault_px", None)' in fn_block


def test_validate_hgvc88_passes_research_and_blocks_submit():
    rep = validate_hgvc88.hgvc88_report(ROOT)
    assert rep["ok_to_download"] is True
    assert rep["ok_to_submit"] is False
    assert rep["all_5_discriminating_gates_pass"] is True
    assert rep["verdict"] == "negative"
    assert rep["dots"] == 37654
    assert rep["folds_won_vs_adhr"] == 8
    assert rep["holdout_dti"] > 0.202
    assert rep["paired_delta_vs_adhr"]["ci95"][0] > 0.0
    assert rep["share_gt25"] >= 0.35
    assert rep["registry_rasters_checked"] >= 320
    assert rep["worst_like_for_like_overlap_3px"] <= 0.70
    assert rep["surface_max_abs_spearman"] <= 0.90
    assert rep["literal_witness_overlap_3px"] == 1.0
    assert validate_hgvc88.main([]) == 0
    assert validate_hgvc88.main(["--require-submit"]) == 2


def test_validate_hgvc88_detects_tampered_submit_flag(tmp_path):
    rels = [
        "registry/hgvc88_run_card.json",
        "docs/data/hgvc88_run_card.json",
        "evidence/hgvc88_run_card.json",
        "registry/hgvc88_gate_v3.json",
        "docs/data/hgvc88_gate_v3.json",
        "registry/preregistration_hgvc88.json",
        "docs/data/preregistration_hgvc88.json",
        "evidence/hgvc88_canaries.json",
        "evidence/hgvc88_holdout_20261024.json",
        "docs/evidence/hgvc88_holdout_20261024.json",
        "evidence/hgvc88_uniqueness.json",
    ]
    rc = json.loads((ROOT / "registry/hgvc88_run_card.json").read_text(encoding="utf-8"))
    tif_rel = rc["download"]
    zip_rel = rc["zip_download"]
    sub_tif = rc["repo_copy"]
    sub_zip = str(Path(sub_tif).with_suffix(".zip"))
    fmt_rel = str(Path(tif_rel).with_suffix(".format-audit.json"))
    for r in rels + [tif_rel, zip_rel, sub_tif, sub_zip, fmt_rel]:
        dst = tmp_path / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / r, dst)

    # Untouched copy passes
    assert validate_hgvc88.hgvc88_report(tmp_path)["ok_to_download"] is True

    # Tamper ok_to_submit -> True while literal witness = 1.0 -> must raise ValueError
    gv = json.loads((tmp_path / "registry/hgvc88_gate_v3.json").read_text(encoding="utf-8"))
    gv["ok_to_submit"] = True
    t_txt = json.dumps(gv, indent=2) + "\n"
    (tmp_path / "registry/hgvc88_gate_v3.json").write_text(t_txt, encoding="utf-8")
    (tmp_path / "docs/data/hgvc88_gate_v3.json").write_text(t_txt, encoding="utf-8")
    with pytest.raises(ValueError, match="ok_to_submit"):
        validate_hgvc88.hgvc88_report(tmp_path)
