"""Automated regression & release-integrity tests for H88-SAR-CSD (2026-10-24).

Runs cleanly on fresh CI checkouts without gitignored ``data/`` as well as in
restored workspaces.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems88 import gate, sar_csd  # noqa: E402
import validate_sarcsd88  # noqa: E402


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_sar_csd_unit_primitives():
    # ColumnSubsetView preserves sequential slice gathering without duplicating memory
    mat = np.arange(60, dtype=np.float32).reshape(10, 6)
    view = sar_csd.ColumnSubsetView(mat, (1, 3, 5))
    assert view.shape == (10, 3)
    sub = view[np.array([0, 4, 9])]
    assert sub.shape == (3, 3)
    assert np.array_equal(sub, mat[[0, 4, 9]][:, [1, 3, 5]])

    # completeness_propensity_fp decays strictly monotonically with distance from mapped faults
    fp = np.ones((24, 24), dtype=bool)
    vis = np.zeros((24, 24), dtype=bool)
    vis[12, 12] = True
    dens_fp, c_fp = sar_csd.completeness_propensity_fp(vis, fp, lambda_px=6.0)
    assert dens_fp.shape == (576,) and c_fp.shape == (576,)
    c_grid = c_fp.reshape(24, 24)
    assert np.isclose(c_grid[12, 12], 1.0)
    assert c_grid[12, 12] > c_grid[12, 16] > c_grid[12, 22] > 0.0

    # fuse_csd_joint and fuse_sar_missingness_grid preserve [0, 1] and m >= p pointwise
    rng = np.random.default_rng(88)
    n = 400
    pf = rng.uniform(1e-4, 0.08, size=n).astype(np.float32)
    mf = np.clip(pf + rng.uniform(0.0, 0.15, size=n), pf, 1.0).astype(np.float32)
    ps = rng.uniform(1e-4, 0.12, size=n).astype(np.float32)
    ms = np.clip(ps + rng.uniform(0.0, 0.18, size=n), ps, 1.0).astype(np.float32)
    pn, mn, k2 = sar_csd.fuse_csd_joint(pf, mf, ps, ms, k_target=60.0)
    assert np.isclose(k2, 60.0)
    assert np.all((pn >= 0.0) & (pn <= 1.0)) and np.all((mn >= pn) & (mn <= 1.0))

    ys, xs = np.divmod(np.arange(n), 20)
    d_act = rng.uniform(3.0, 45.0, size=n).astype(np.float32)
    c_act = np.exp(-((d_act / 18.0) ** 2)).astype(np.float32)
    p3, m3, k3 = sar_csd.fuse_sar_missingness_grid(
        pf, mf, ps, ms, d_act, c_act, ys, xs, (20, 20), k_target=60.0, far_frac=0.45
    )
    assert k3 > k2
    assert np.all((p3 >= 0.0) & (p3 <= 1.0)) and np.all((m3 >= p3) & (m3 <= 1.0))


def test_sarcsd88_run_card_and_gate_contracts():
    rc = json.loads((ROOT / "registry/sarcsd88_run_card.json").read_text())
    gv = json.loads((ROOT / "registry/sarcsd88_gate_v3.json").read_text())
    ho = json.loads((ROOT / "evidence/sarcsd88_holdout.json").read_text())
    can = json.loads((ROOT / "evidence/sarcsd88_canaries.json").read_text())

    # Protocol mandatory fields
    for key in (
        "hypothesis", "mechanism", "named_non_fault_mimic", "holdout_dti",
        "leakage_canary", "correlation_overlap_vs_registry", "fingerprint",
        "raster_sha256", "validator_output", "submission_name", "submission_note", "verdict",
    ):
        assert key in rc, key

    assert rc["experiments_run"] == 3 <= rc["experiment_budget_max"] == 3
    assert rc["weekly_slots_spent"] == 0 and rc["organizer_confirmed_score"] is None
    assert len(rc["submission_name"]) <= 140 and 0 < len(rc["submission_note"]) <= 140

    # Evidence labeling + holdout verification
    hd = rc["holdout_dti"]
    assert hd["evidence_class"] == "HOLDOUT-DTI"
    assert hd["evaluator_version"] == "gems57-pooled-hide-v2"
    assert hd["withheld_positive_pixels"] == 22893
    # Exp 02 beats H88-ADHR on mapped-relay recovery (+505 bps); Exp 03 clears share_gt25 >= 0.35
    assert hd["exp02_csd_joint"]["dti"] > hd["h88_adhr_recomputed_control"]["dti"]
    assert rc["fingerprint"]["share_le2"] == 0.0 and rc["fingerprint"]["share_gt25"] >= 0.35
    assert rc["fingerprint"]["passed"] is True
    assert can["passed"] is True and can["features_tested"] == 88 and can["max_symmetric_auc"] <= 0.90
    assert ho["zero_leakage_quadrant_scramble_equal"] is True

    # Uniqueness across 264 registry + latest sibling rasters
    uq = rc["correlation_overlap_vs_registry"]
    assert uq["registry_rasters_checked"] >= 260
    assert uq["preplacement_max_abs_spearman"] <= 0.90
    assert uq["final_max_abs_spearman"] <= 0.90
    assert uq["final_worst_like_for_like_overlap_3px"] <= 0.70
    assert uq["unique_like_for_like"] is True

    # Fail-closed verdict & DO-NOT-SUBMIT filename binding
    assert gv["ok_to_download"] is True and gv["ok_to_submit"] is False
    assert rc["verdict"] == "negative"
    assert rc["download"].endswith("-DO-NOT-SUBMIT.tif")


def test_sarcsd88_artifact_portal_parity_and_validator():
    rep = validate_sarcsd88.sarcsd88_report(ROOT)
    assert rep["ok_to_download"] is True and rep["ok_to_submit"] is False
    assert rep["dots"] == 35998

    tif = ROOT / rep["file"]
    zpath = tif.with_suffix(".zip")
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert ds.crs.to_epsg() == gate.EXPECTED["epsg"]
        assert ds.shape == gate.EXPECTED["shape"]
        assert tuple(ds.transform)[:6] == gate.EXPECTED["transform"]
        assert ds.nodata is None
        assert ds.profile["compress"] == "lzw" and not ds.profile["tiled"]
        assert ds.block_shapes[0] == (1, gate.EXPECTED["shape"][1])
    assert np.array_equal(arr, tifffile.imread(tif))
    assert np.isfinite(arr).all() and set(np.unique(arr)) <= {0.0, 1.0}
    with zipfile.ZipFile(zpath) as zf:
        assert zf.namelist() == [tif.name]
        assert _sha(tif) == hashlib.sha256(zf.read(tif.name)).hexdigest()

    # --require-submit must fail closed with exit code 2
    assert validate_sarcsd88.main([]) == 0
    assert validate_sarcsd88.main(["--require-submit"]) == 2


def test_sarcsd88_validator_catches_tampering(tmp_path):
    rc = json.loads((ROOT / "registry/sarcsd88_run_card.json").read_text())
    for rel in (
        "registry/sarcsd88_run_card.json",
        "docs/data/sarcsd88_run_card.json",
        "evidence/sarcsd88_run_card.json",
        "registry/sarcsd88_gate_v3.json",
        "docs/data/sarcsd88_gate_v3.json",
        "registry/preregistration_sarcsd88.json",
        "evidence/sarcsd88_canaries.json",
        "evidence/sarcsd88_holdout.json",
        "evidence/sarcsd88_uniqueness.json",
        rc["download"],
        rc["zip_download"],
        rc["repo_copy"],
    ):
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)

    assert validate_sarcsd88.sarcsd88_report(tmp_path)["ok_to_submit"] is False

    # Flipping ok_to_submit to True in gate_v3 must raise ValueError
    gv = json.loads((tmp_path / "registry/sarcsd88_gate_v3.json").read_text())
    gv["ok_to_submit"] = True
    gv["blocking_reasons"] = []
    txt = json.dumps(gv)
    (tmp_path / "registry/sarcsd88_gate_v3.json").write_text(txt)
    (tmp_path / "docs/data/sarcsd88_gate_v3.json").write_text(txt)
    with pytest.raises(ValueError):
        validate_sarcsd88.sarcsd88_report(tmp_path)
