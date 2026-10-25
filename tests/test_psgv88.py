"""Unit and end-to-end validation tests for the H88-PSGV Baranov spectral conduit lane."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems88 import psgv  # noqa: E402
import validate_psgv88  # noqa: E402


def test_psgv_feature_names_and_schema():
    assert len(psgv.PSGV_FEATURES) == 20
    assert len(set(psgv.PSGV_FEATURES)) == 20
    assert psgv.PSGV_SCHEMA_VERSION == "psgv88-20ch-v1"
    for nm in psgv.PSGV_FEATURES:
        assert nm.startswith("psgv_")
        assert "catalogue" not in nm and "existing_faults" not in nm


def test_psgv_fft_baranov_and_riesz_monogenic_operators_finite():
    rng = np.random.default_rng(20261025)
    xs = np.linspace(-6.0, 6.0, 64, dtype=np.float32)[None, :]
    ys = np.linspace(-6.0, 6.0, 64, dtype=np.float32)[:, None]
    step = np.tanh(xs * np.ones_like(ys)) + 0.02 * rng.standard_normal((64, 64)).astype(np.float32)

    taper = psgv._make_cosine_taper(64, 64, psgv.PAD_Y, psgv.PAD_X)
    spec = psgv._pad_taper_rfft2(step, taper)
    rec = psgv._irfft2_unpad(spec, 64, 64)
    assert rec.shape == (64, 64) and rec.dtype == np.float32 and np.isfinite(rec).all()

    ridge = np.exp(-0.5 * (xs / 0.8) ** 2) * np.ones_like(ys)
    fp = np.ones((64, 64), dtype=bool)
    inds = np.indices((64, 64), dtype=np.int32)
    vessel = psgv._frangi_vesselness_2d(ridge, sigma=2.0, fp=fp, fp_edt_inds=inds)
    assert vessel.shape == (64, 64) and np.isfinite(vessel).all() and (vessel >= 0.0).all()
    assert float(vessel[:, 31:33].mean()) > 4.0 * float(vessel[:, 4:8].mean() + 1e-6)


def test_psgv_poe_pool_preserves_self_credit_inequality():
    d_vis = np.array([3.0, 12.0, 25.0, 45.0], dtype=np.float32)
    p_b = np.array([0.20, 0.10, 0.02, 0.01], dtype=np.float32)
    m_b = np.array([0.45, 0.25, 0.06, 0.03], dtype=np.float32)
    p_h = np.array([0.24, 0.14, 0.07, 0.06], dtype=np.float32)
    m_h = np.array([0.48, 0.30, 0.16, 0.14], dtype=np.float32)
    p_p = np.array([0.28, 0.17, 0.09, 0.08], dtype=np.float32)
    m_p = np.array([0.52, 0.35, 0.20, 0.18], dtype=np.float32)
    p_poe, m_poe = psgv.poe_pool_psgv(p_b, m_b, p_h, m_h, p_p, m_p, d_vis)
    assert np.all((p_poe > 0.0) & (p_poe < 1.0))
    assert np.all(m_poe >= p_poe) and np.all(m_poe <= 1.0)


def test_psgv_source_never_reads_existing_faults_in_feature_builder():
    src_text = (ROOT / "src/gems88/psgv.py").read_text(encoding="utf-8")
    fn_block = src_text.split("def build_or_load_psgv_memmap", 1)[1].split("def poe_pool_psgv", 1)[0]
    assert "existing_faults.tif" not in fn_block
    assert "grid.catalogue" not in fn_block
    assert '"uses_existing_faults_catalogue": False' in fn_block


def test_validate_psgv88_passes_research_and_blocks_submit():
    rep = validate_psgv88.psgv88_report(ROOT)
    assert rep["ok_to_download"] is True
    assert rep["ok_to_submit"] is False
    assert rep["all_5_discriminating_gates_pass"] is True
    assert rep["verdict"] == "negative"
    assert rep["dots"] == 37654
    assert rep["folds_won_vs_adhr"] == 8
    assert rep["folds_won_vs_hgvc"] >= 6
    assert rep["holdout_dti"] > 0.204
    assert rep["paired_delta_vs_adhr"]["ci95"][0] > 0.0
    assert rep["share_gt25"] >= 0.35
    assert rep["registry_rasters_checked"] >= 350
    assert rep["worst_like_for_like_overlap_3px"] <= 0.70
    assert rep["surface_max_abs_spearman"] <= 0.90
    assert rep["literal_witness_overlap_3px"] == 1.0
    assert validate_psgv88.main([]) == 0
    assert validate_psgv88.main(["--require-submit"]) == 2


def test_validate_psgv88_detects_tampered_submit_flag(tmp_path):
    rels = [
        "registry/psgv88_run_card.json",
        "docs/data/psgv88_run_card.json",
        "evidence/psgv88_run_card.json",
        "registry/psgv88_gate_v3.json",
        "docs/data/psgv88_gate_v3.json",
        "registry/preregistration_psgv88.json",
        "docs/data/preregistration_psgv88.json",
        "evidence/psgv88_canaries.json",
        "evidence/psgv88_holdout_20261025.json",
        "docs/evidence/psgv88_holdout_20261025.json",
        "evidence/psgv88_uniqueness.json",
    ]
    rc = json.loads((ROOT / "registry/psgv88_run_card.json").read_text(encoding="utf-8"))
    tif_rel = rc["download"]
    zip_rel = rc["zip_download"]
    sub_tif = rc["repo_copy"]
    sub_zip = str(Path(sub_tif).with_suffix(".zip"))
    fmt_rel = str(Path(tif_rel).with_suffix(".format-audit.json"))
    for r in rels + [tif_rel, zip_rel, sub_tif, sub_zip, fmt_rel]:
        dst = tmp_path / r
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / r, dst)

    assert validate_psgv88.psgv88_report(tmp_path)["ok_to_download"] is True

    gv = json.loads((tmp_path / "registry/psgv88_gate_v3.json").read_text(encoding="utf-8"))
    gv["ok_to_submit"] = True
    t_txt = json.dumps(gv, indent=2) + "\n"
    (tmp_path / "registry/psgv88_gate_v3.json").write_text(t_txt, encoding="utf-8")
    (tmp_path / "docs/data/psgv88_gate_v3.json").write_text(t_txt, encoding="utf-8")
    with pytest.raises(ValueError, match="ok_to_submit"):
        validate_psgv88.psgv88_report(tmp_path)
