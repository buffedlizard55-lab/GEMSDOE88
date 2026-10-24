"""LBCAL unit tests: expected-DTI algebra agrees with the vendor metric on a toy grid,
and the shipped LBCAL artefact matches its run card (format, uniqueness, honesty labels)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")):
    sys.path.insert(0, p)
from gems88.lbcal import coverage_maps, predict_dti  # noqa: E402


def test_expected_tp_equals_vendor_metric_for_deterministic_truth():
    from gems57 import metric
    rng = np.random.default_rng(0)
    H, W = 60, 70
    truth = np.zeros((H, W), bool); truth[30, 5:65] = True; truth[5:50, 20] = True
    pred = np.zeros((H, W), np.float32)
    pred[31, 6:60:3] = 1; pred[rng.integers(0, H, 40), rng.integers(0, W, 40)] = 1
    c, e = coverage_maps(pred)
    T = float(c[truth].sum())                                  # exact TP under a 0/1 truth density
    covers, q, _ = metric.max_cover(pred.astype(np.float64), truth)
    assert abs(T - float(covers.sum())) < 1e-4
    # predict_dti with one cell == the deterministic truth reproduces the vendor DTI up to the M approximation
    cell_q = np.array([1.0])
    C = np.array([[T]]); N = np.array([float(truth.sum())])
    M_exact = float((pred * q).sum())
    E = np.array([[M_exact * 2.6]])
    d, *_ = predict_dti(cell_q, C, E, np.array([float(pred.sum())]), N, kappa=2.6)
    ref = metric.dti_exact(pred.astype(np.float64), truth)["dti"]
    assert abs(float(d[0]) - float(ref)) < 1e-6


def test_lbcal_run_card_is_honest_and_matches_file():
    card = json.loads((ROOT / "registry" / "lbcal_run_card.json").read_text())
    tif = ROOT / card["raster"]["file"]
    if not tif.exists():
        pytest.skip("artefact not present")
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster"]["sha256"]
    assert len(card["raster"]["note"]) <= 140
    assert card["receipt_model"]["evidence_class"].startswith("MODEL-FIT")
    assert card["model_projection"]["evidence_class"].startswith("MODEL-PROJECTION")
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["uniqueness"]["worst_sparse_dot_overlap_3px"]["overlap"] <= 0.70
    assert abs(card["uniqueness"]["worst_spearman_all_rasters"]["rho"]) <= 0.90
    assert card["leakage_canary"]["max_symmetric_auc"] <= 0.90
    v = card["validator"]
    assert v["no_nan_anywhere"] and v["values_in_0_1"] and v["crs_shape_transform_match"]
    assert v["positive_on_catalogue"] == 0 and v["positive_outside_footprint"] == 0
    # the user's slot rule: no slot unless the holdout beats the current best
    if not card["holdout"]["beats_current_holdout_best"]:
        assert card["ok_to_submit"] is False and "DO-NOT-SUBMIT" in tif.name
