from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88 import wbhr  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_stacked_feature_view_indexing():
    a = np.arange(20, dtype=np.float32).reshape(5, 4)
    b = np.arange(15, dtype=np.float32).reshape(5, 3) + 100.0
    v = wbhr.StackedFeatureView([a, b])
    assert v.shape == (5, 7)
    assert len(v) == 5
    rows = v[np.array([1, 3])]
    assert rows.shape == (2, 7)
    np.testing.assert_allclose(rows[:, :4], a[[1, 3]])
    np.testing.assert_allclose(rows[:, 4:], b[[1, 3]])
    col = v[np.array([0, 2, 4]), 5]
    np.testing.assert_allclose(col, b[[0, 2, 4], 1])
    with pytest.raises(ValueError):
        wbhr.StackedFeatureView([a, np.zeros((6, 2), dtype=np.float32)])


def test_wallace_polarity_rejects_symmetric_arroyo_and_collinear_worm_detects_line():
    # One-sided fault scarp (`down=120, up=10`) vs symmetric two-bank wash (`down=65, up=65`) of equal total step 130
    down = np.array([120.0, 65.0], dtype=np.float32)
    up = np.array([10.0, 65.0], dtype=np.float32)
    pol = np.abs(down - up) / (down + up + 8.0)
    assert pol[0] > 0.75
    assert pol[1] == 0.0

    # Collinear 9-px scarp line outranks isolated point clutter of equal peak amplitude
    valid = np.ones((25, 25), dtype=bool)
    line = np.zeros((25, 25), dtype=np.float32)
    line[12, 6:19] = 1.0
    blob = np.zeros((25, 25), dtype=np.float32)
    blob[12, 12] = 1.0
    w_line = wbhr._collinear_line_max(line, valid, halflen=4)
    w_blob = wbhr._collinear_line_max(blob, valid, halflen=4)
    assert float(w_line[12, 12]) == pytest.approx(1.0)
    assert float(w_blob[12, 12]) == pytest.approx(1.0 / 9.0, rel=1e-5)


def test_fit_diverse_dual_models_synthetic_finite_bounds():
    rng = np.random.default_rng(88)
    fp = np.ones((24, 24), dtype=bool)
    pos = np.zeros((24, 24), dtype=bool)
    pos[8:18, 12] = True
    n_fp = int(fp.sum())
    x = rng.normal(size=(n_fp, 6)).astype(np.float32)
    ys, xs = np.nonzero(fp)
    x[:, 0] += 3.0 * pos[ys, xs].astype(np.float32)
    dom = np.ones(n_fp, dtype=bool)
    clfs, regs = wbhr.fit_diverse_dual_models([x], dom, pos, fp, seed=42, max_zero_neg=500)
    p = clfs[0].predict_proba(x)[:, 1]
    m = regs[0].predict(x)
    assert np.isfinite(p).all() and (p >= 0.0).all() and (p <= 1.0).all()
    assert np.isfinite(m).all()
    assert float(p[pos[ys, xs]].mean()) > float(p[~pos[ys, xs]].mean())


def test_wbhr88_deliverables_run_card_and_validator():
    prereg = json.loads((ROOT / "registry/preregistration_wbhr88.json").read_text(encoding="utf-8"))
    card = json.loads((ROOT / "registry/wbhr88_run_card.json").read_text(encoding="utf-8"))
    web_card = json.loads((ROOT / "docs/data/wbhr88_run_card.json").read_text(encoding="utf-8"))
    grec = json.loads((ROOT / "registry/wbhr88_gate_v3.json").read_text(encoding="utf-8"))
    web_grec = json.loads((ROOT / "docs/data/wbhr88-gate.json").read_text(encoding="utf-8"))
    can = json.loads((ROOT / "evidence/wbhr88_canary.json").read_text(encoding="utf-8"))
    hold = json.loads((ROOT / "evidence/wbhr88_holdout.json").read_text(encoding="utf-8"))
    uniq = json.loads((ROOT / "evidence/wbhr88_uniqueness.json").read_text(encoding="utf-8"))

    assert card == web_card
    assert grec == web_grec
    assert prereg["lane"] == "WBHR-88"
    assert prereg["frozen_before_feature_canary_holdout_or_production_build"] is True
    assert len(prereg["ranked_hypotheses"]) == 5
    assert card["experiments_used"] == 3 and card["budget_max_experiments"] == 3
    assert card["organizer_confirmed_score"] is None
    assert card["approved_for_weekly_slot"] is False
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert 0 < len(card["submission_name"]) <= 140
    assert 0 < len(card["submission_note"]) <= 140

    # Leakage canary + Holdout + Uniqueness invariants
    assert can["all_clear"] is True and can["features_tested_total"] == 83
    assert can["worst_all83"]["symmetric_auc"] <= 0.90
    assert hold["evaluator_version"] == "gems57-pooled-hide-v2"
    assert hold["withheld_positive_pixels"] == 22893
    assert hold["paired_spatial_block_bootstrap"]["E1_wbhr_phys60_minus_phys44_control"]["ci95"][0] > 0.0
    assert uniq["registry_rasters_checked"] >= 200
    assert uniq["preplacement_surface_gate"]["passed"] is True
    assert uniq["unique_like_for_like"] is True
    assert uniq["worst_like_for_like_overlap_3px"]["value"] <= 0.70

    # Saved GeoTIFF & ZIP verification
    tif_p = ROOT / card["artifact"]
    zip_p = ROOT / card["zip_artifact"]
    assert "DO-NOT-SUBMIT" in tif_p.name
    assert _sha256(tif_p) == card["raster_sha256"]
    assert _sha256(zip_p) == card["zip_sha256"]
    with zipfile.ZipFile(zip_p) as zf:
        assert len(zf.namelist()) == 1
        assert hashlib.sha256(zf.read(zf.namelist()[0])).hexdigest() == card["raster_sha256"]
    with rasterio.open(tif_p) as ds:
        arr = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611" and ds.shape == (3730, 3292)
        assert ds.nodata is None
        assert np.isfinite(arr).all() and float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
        assert int((arr > 0).sum()) == card["validator_output"]["positive_dots"]

    # CLI validator exit-code checks (`0` normal, `2` on `--require-submit`)
    r_ok = subprocess.run([sys.executable, str(ROOT / "scripts/validate_wbhr88.py")], capture_output=True, text=True)
    assert r_ok.returncode == 0
    r_sub = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_wbhr88.py"), "--require-submit"],
        capture_output=True,
        text=True,
    )
    assert r_sub.returncode == 2


def test_wbhr88_site_visibility():
    for page_name in ("index.html", "executive-summary.html"):
        txt = (ROOT / "docs" / page_name).read_text(encoding="utf-8")
        assert "WBHR-88" in txt
        assert "gems88-wbhr88-20261024-DO-NOT-SUBMIT.tif" in txt
        assert "DO NOT SUBMIT" in txt
        assert "DOWNLOAD FOR RESEARCH: YES" in txt.upper()
        assert "OK TO SUBMIT: YES" not in txt.upper()
