"""Automated verification suite for the H88-QTSK lane and emitted GeoTIFF."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor"))

import validate_current  # noqa: E402
import validate_qtsk88  # noqa: E402
from gems88 import qtsk  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_qtsk_preregistration_and_run_card_sync():
    prereg = json.loads((ROOT / "registry/qtsk88_preregistration.json").read_text())
    assert prereg["preregistration_id"] == "gems88-qtsk-prereg-20261024-v1"
    assert prereg["lane"] == "H88-QTSK"
    assert prereg["max_experiments"] == 3
    assert len(prereg["experiments"]) == 3

    rc_reg = (ROOT / "registry/qtsk88_run_card.json").read_text()
    rc_web = (ROOT / "docs/data/qtsk88_run_card.json").read_text()
    assert rc_reg == rc_web

    card = json.loads(rc_reg)
    assert card["lane"] == "H88-QTSK"
    assert card["evidence_label"] == "HOLDOUT-DTI"
    assert card["evaluator_version"] == "gems57-pooled-hide-v2"
    assert card["withheld_positive_pixels"] == 22893
    assert len(card["all_experiments_holdout"]) == 4  # control + 3 experiments
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["approved_for_weekly_slot"] is False
    assert 20 <= len(card["submission_note"]) <= 140
    assert card["submission_note_length"] == len(card["submission_note"])


def test_qtsk_canaries_and_paired_holdout_evidence():
    card = json.loads((ROOT / "registry/qtsk88_run_card.json").read_text())
    ev = json.loads((ROOT / "evidence/qtsk88_experiment_20261024.json").read_text())

    can = card["leakage_canary"]
    assert can["passed"] is True
    assert len(can["qtsk14_features"]) == 14
    assert can["qtsk14_max_symmetric_auc"] <= 0.90
    assert can["phys44_max_symmetric_auc"] <= 0.90

    arms = card["all_experiments_holdout"]
    assert set(arms) == {"control_adhr", "exp1_qtsk_phys", "exp2_qtsk_dual", "exp3_qtsk_strat"}
    assert arms["exp2_qtsk_dual"]["pooled_dti"] > arms["control_adhr"]["pooled_dti"]
    assert (
        card["all_experiments_blind_gt25"]["exp2_qtsk_dual"]["pooled_dti"]
        > card["all_experiments_blind_gt25"]["control_adhr"]["pooled_dti"]
    )
    assert arms["exp3_qtsk_strat"]["pooled_dti"] == card["holdout_dti"]
    assert arms["exp3_qtsk_strat"]["ci95"] == card["holdout_dti_ci95"]

    # Exp 2 was properly stopped on 222-raster near-ribbon overlap > 0.70 per Protocol Rule 1
    exp2_u = ev["production_arm_audits"]["exp2_qtsk_dual"]["uniqueness_dots"]
    assert exp2_u["worst_like_for_like_overlap"]["value"] > 0.70
    assert exp2_u["unique_like_for_like"] is False

    # Emitted Exp 3 clears pre-placement |rho| <= 0.90 across all 228 rasters and 222 pre-merge rasters <= 0.70;
    # post-merge integration against PR #88 (GTHC-88) records 0.724516 > 0.70 without post-hoc retuning.
    u = card["registry_uniqueness"]
    assert u["n_registry_rasters_checked"] >= 222
    assert u["pre_placement_surface_max_abs_spearman_rho"] <= 0.90
    assert u["like_for_like_3px_unique_le_0p70"] is True
    assert u["worst_like_for_like_3px_overlap"]["value"] <= 0.70
    assert u["literal_all_registry_3px_unique_le_0p70"] is False
    assert u["worst_literal_forward_3px_overlap"]["value"] == 1.0
    pm = u["postmerge_228_audit"]
    assert pm["n_registry_rasters_checked"] >= 228
    assert pm["pre_placement_surface_pass_le_0p90"] is True
    assert pm["like_for_like_3px_unique_le_0p70_postmerge"] is False
    assert pm["worst_like_for_like_3px_overlap_postmerge"]["value"] > 0.70


def test_qtsk_geotiff_and_zip_bytes():
    card = json.loads((ROOT / "registry/qtsk88_run_card.json").read_text())
    tif_path = ROOT / card["raster"]["tif_path"]
    zip_path = ROOT / card["raster"]["zip_path"]
    assert tif_path.is_file() and zip_path.is_file()
    assert "DO-NOT-SUBMIT" in tif_path.name and "DO-NOT-SUBMIT" in zip_path.name
    assert _sha256(tif_path) == card["raster"]["sha256"]
    assert _sha256(zip_path) == card["raster"]["zip_sha256"]

    for p in (tif_path, zip_path):
        mode = stat.S_IMODE(os.stat(p).st_mode)
        assert mode & stat.S_IROTH, f"{p} must be world-readable"

    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.shape == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.nodata is None
        assert str(ds.compression).upper() == "COMPRESSION.LZW"

    arr_tf = tifffile.imread(tif_path)
    assert np.array_equal(arr, arr_tf)
    assert np.isfinite(arr).all()
    assert not np.isnan(arr).any()
    assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
    assert int((arr > 0.0).sum()) == card["raster"]["n_positive_dots"] == 53876
    assert set(np.unique(arr).tolist()).issubset({0.0, 1.0})

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert zf.read(names[0]) == tif_path.read_bytes()

    sample_path = ROOT / "data/bridge/sample_submission.tif"
    faults_path = ROOT / "data/bridge/existing_faults.tif"
    if sample_path.is_file() and faults_path.is_file():
        with rasterio.open(sample_path) as ref, rasterio.open(tif_path) as ds:
            assert (ds.shape, ds.crs, ds.transform) == (ref.shape, ref.crs, ref.transform)
        with rasterio.open(faults_path) as ef:
            ef_arr = ef.read(1)
        footprint = np.isfinite(ef_arr) & ((ef_arr == 0.0) | (ef_arr == 1.0))
        catalogue = ef_arr == 1.0
        assert np.all(arr[~footprint] == 0.0)
        assert int((arr[catalogue] > 0.0).sum()) == 0


def test_validate_qtsk88_and_current_release_cli():
    sample_path = ROOT / "data/bridge/sample_submission.tif"
    if not sample_path.is_file():
        pytest.skip("requires restored validation inputs")

    report = validate_qtsk88.validate_qtsk88(ROOT)
    assert report["ok"] is True
    assert report["ok_to_download"] is True
    assert report["ok_to_submit"] is False
    assert report["verdict"] == "negative"

    cur = validate_current.release_report(ROOT)
    saved_cur = json.loads((ROOT / "docs/data/current_release.json").read_text())
    assert cur == saved_cur
    assert cur["candidate"] == "H88-SDTL" and cur["ok_to_submit"] is (cur["verdict"] == "promote")
    assert cur["approved_for_weekly_slot"] is False
    assert cur["organizer_confirmed_score"] is None

    current_gate = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_current.py"), "--require-submit"],
        capture_output=True, text=True,
    )
    assert current_gate.returncode == 0, current_gate.stderr
    current_report = json.loads(current_gate.stdout)
    assert current_report["candidate"] == "H88-SDTL"
    assert current_report["ok_to_submit"] is True
    assert current_report["approved_for_weekly_slot"] is False
    assert current_report["organizer_confirmed_score"] is None
    assert current_report["weekly_slots_used"] == 0

    proc_ok = subprocess.run([sys.executable, str(ROOT / "scripts/validate_qtsk88.py")], capture_output=True, text=True)
    assert proc_ok.returncode == 0

    proc_req = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_qtsk88.py"), "--require-submit"],
        capture_output=True,
        text=True,
    )
    assert proc_req.returncode == 2


def test_qtsk_features_and_hessian_ridge_invariants():
    assert len(qtsk.QTSK_FEATURES) == 14
    x = np.zeros((25, 25), dtype=np.float32)
    x[:, 12] = 10.0  # sharp 1D N-S ridge crest at col 12
    ridge = qtsk._hessian_ridge_lambda_plus(x, sigma=1.5)
    assert ridge.shape == x.shape
    assert np.isfinite(ridge).all()
    assert float(ridge.min()) >= 0.0
    assert float(ridge[12, 12]) > float(ridge[12, 2])
