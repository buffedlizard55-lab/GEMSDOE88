"""Automated verification tests for the H88-TDKL lane (`tests/test_tdkl88.py`)."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88 import gate, tdkl  # noqa: E402


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_tdkl_poe_pool_vetoes_false_positives_and_preserves_blind_tail():
    p_base = np.array([0.25, 0.25, 0.002], dtype=np.float32)
    m_base = np.array([0.35, 0.35, 0.004], dtype=np.float32)
    p_tdkl = np.array([0.004, 0.28, 0.006], dtype=np.float32)
    m_tdkl = np.array([0.008, 0.38, 0.010], dtype=np.float32)
    d_vis = np.array([6.0, 6.0, 30.0], dtype=np.float32)

    p_out, m_out = tdkl._poe_pool(p_base, m_base, p_tdkl, m_tdkl, w_tdkl=0.65, d_vis_act=d_vis)
    assert p_out.shape == (3,) and m_out.shape == (3,)
    assert np.isfinite(p_out).all() and np.isfinite(m_out).all()
    assert np.all(m_out >= p_out) and np.all((p_out >= 0.0) & (p_out <= 1.0))
    # Pixel 0: TDKL vetoes the false positive (much lower than linear average 0.35*0.25 + 0.65*0.004 = 0.0901)
    assert float(p_out[0]) < 0.035
    # Pixel 1: Concordant fault scarp remains strong
    assert float(p_out[1]) > 0.26
    # Pixel 2 (blind basin d_vis=30 > 22): tail preservation exceeds pure log-odds product
    p_lo_only, _ = tdkl._poe_pool(p_base, m_base, p_tdkl, m_tdkl, w_tdkl=0.65, d_vis_act=None)
    assert float(p_out[2]) > float(p_lo_only[2])


def test_tdkl_preregistration_and_run_card_integrity():
    prereg_path = ROOT / "registry/preregistration_tdkl88.json"
    rc_path = ROOT / "registry/tdkl88_run_card.json"
    docs_rc_path = ROOT / "docs/data/tdkl88_run_card.json"
    ev_path = ROOT / "evidence/tdkl88_holdout_20261024.json"
    docs_ev_path = ROOT / "docs/evidence/tdkl88_holdout_20261024.json"

    assert prereg_path.is_file()
    assert rc_path.is_file() and docs_rc_path.is_file()
    assert ev_path.is_file() and docs_ev_path.is_file()
    assert _sha256(rc_path) == _sha256(docs_rc_path)
    assert _sha256(ev_path) == _sha256(docs_ev_path)

    prereg = json.loads(prereg_path.read_text())
    rc = json.loads(rc_path.read_text())
    assert rc["preregistration_id"] == prereg["preregistration_id"] == "PREREG-20261024-TDKL88"
    assert len(prereg["candidate_hypotheses_ranked"]) == 4
    assert rc["experiments_executed"] == rc["experiment_budget_max"] == 3
    assert len(rc["submission_name"]) <= 140
    assert 0 < len(rc["submission_note"]) <= 140
    assert rc["organizer_confirmed"]["candidate_live_score"] is None
    assert rc["organizer_confirmed"]["weekly_slots_used_this_session"] == 0
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["features_tested"] == 56
    assert rc["leakage_canary"]["max_symmetric_auc"] <= 0.90


def test_tdkl_holdout_monotonic_progression_and_paired_significance():
    rc = json.loads((ROOT / "registry/tdkl88_run_card.json").read_text())
    ho = rc["holdout_dti"]
    assert ho["evidence_class"] == "HOLDOUT-DTI"
    assert ho["evaluator_version"] == "gems57-pooled-hide-v2"
    assert ho["withheld_positive_pixels_overall"] == 22893
    assert ho["withheld_positive_pixels_far_gt10px"] == 10791
    assert ho["withheld_positive_pixels_blind_gt25px"] == 3117

    c_phys44 = ho["controls"]["phys44_zero_cat"]["overall"]["dti"]
    c_inc_ov = ho["controls"]["h88_adhr_incumbent"]["overall"]["dti"]
    c_inc_far = ho["controls"]["h88_adhr_incumbent"]["far_gt10px"]["dti"]
    c_inc_blind = ho["controls"]["h88_adhr_incumbent"]["blind_gt25px"]["dti"]

    e1_ov = ho["experiments"]["Exp01_tdkl_phys_only"]["overall"]["dti"]
    e2_ov = ho["experiments"]["Exp02_tdkl_single_79"]["overall"]["dti"]
    e3_ov = ho["experiments"]["Exp03_h88_tdkl_primary"]["overall"]["dti"]
    e3_far = ho["experiments"]["Exp03_h88_tdkl_primary"]["far_gt10px"]["dti"]
    e3_blind = ho["experiments"]["Exp03_h88_tdkl_primary"]["blind_gt25px"]["dti"]

    # Zero-catalogue improvement and full-model monotonic progression
    assert e1_ov > c_phys44 > 0.09042
    assert c_inc_ov < e2_ov < e3_ov
    assert e3_far > ho["experiments"]["Exp02_tdkl_single_79"]["far_gt10px"]["dti"] > c_inc_far > 0.11478
    assert e3_blind > c_inc_blind > 0.065263

    # Paired 95% spatial-cluster bootstrap CIs exclude zero for both overall and far > 10 px
    delta_ov = ho["experiments"]["Exp03_h88_tdkl_primary"]["paired_delta_vs_incumbent_overall"]
    delta_far = ho["experiments"]["Exp03_h88_tdkl_primary"]["paired_delta_vs_incumbent_far_gt10px"]
    assert delta_ov["delta"] > 0.005 and delta_ov["ci95"][0] > 0.0
    assert delta_far["delta"] > 0.006 and delta_far["ci95"][0] > 0.0


def test_tdkl_geotiff_and_zip_portal_parity_and_uniqueness_gates():
    rc = json.loads((ROOT / "registry/tdkl88_run_card.json").read_text())
    tif_path = ROOT / rc["raster"]["file"]
    zip_path = ROOT / rc["raster"]["zip_file"]
    sub_copy = ROOT / rc["raster"]["submissions_copy"]

    assert tif_path.is_file() and zip_path.is_file() and sub_copy.is_file()
    assert _sha256(tif_path) == _sha256(sub_copy) == rc["raster_sha256"]
    assert _sha256(zip_path) == rc["raster"]["zip_sha256"]

    for p in (tif_path, zip_path, sub_copy):
        mode = stat.S_IMODE(os.stat(p).st_mode)
        assert mode & stat.S_IROTH

    e = gate.EXPECTED
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert ds.crs.to_epsg() == e["epsg"] == 32611
        assert ds.shape == e["shape"] == (3730, 3292)
        assert tuple(ds.transform)[:6] == e["transform"]

    assert np.isfinite(arr).all() and not np.isnan(arr).any()
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    assert int((arr > 0).sum()) == rc["raster"]["emitted_dots"] == 25000
    assert rc["raster"]["share_le2px"] == 0.0
    assert rc["raster"]["share_gt25px"] >= 0.35

    with zipfile.ZipFile(zip_path) as z:
        assert z.namelist() == [tif_path.name]
        assert hashlib.sha256(z.read(tif_path.name)).hexdigest() == rc["raster_sha256"]

    uniq = rc["correlation_overlap_vs_registry"]
    assert uniq["pre_placement_surface_max_abs_spearman"] <= 0.90
    assert uniq["post_placement_v3_like_for_like"]["worst_excess_overlap"] <= 0.70
    assert uniq["post_placement_v3_like_for_like"]["worst_abs_spearman"] <= 0.90
    assert uniq["post_placement_v3_like_for_like"]["duplicate"] is False
    assert uniq["gate_v3_uniqueness"]["unique_like_for_like"] is True
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit_gate_v3_like_for_like"] is True
    # The literal all-raster and post-merge rules remain binding.
    assert uniq["post_placement_literal_including_dense_witness"]["worst_forward_overlap"] == 1.0
    assert max(uniq["postmerge_concurrent_overlaps_3px"][k] for k in ("GTHC-88", "QTSK-88")) > 0.70
    assert rc["ok_to_submit"] is False and rc["verdict"] == "negative"


def test_tdkl_independent_current_release_validator():
    if not (ROOT / "data/bridge/existing_faults.tif").is_file():
        pytest.skip("restore data/bridge via scripts/restore_inputs.py --validation")
    from scripts.validate_tdkl88 import validate_tdkl88

    report = validate_tdkl88(ROOT)
    saved = json.loads((ROOT / "docs/data/current_release.json").read_text())
    assert report == saved
    assert report["candidate"] == "H88-TDKL"
    assert report["format_valid"] is True
    assert report["literal_duplicate"] is True
    assert report["ok_to_download"] is True
    assert report["ok_to_submit"] is False
