"""PROVCREST de-novo candidate gates (2026-10-24, IR-88-58)."""
from __future__ import annotations

import csv
import hashlib
import json
import stat
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "registry" / "provcrest_run_card.json"


def _card():
    return json.loads(CARD.read_text())


def test_provcrest_run_card_negative_under_literal_gate_and_labels():
    rc = _card()
    assert rc["verdict"] == "negative"
    assert rc["submission"]["ok_to_download"] is True
    assert rc["submission"]["ok_to_submit"] is False
    assert rc["submission"]["organizer_confirmed_score"] is None
    assert rc["experiments_run"] <= rc["experiment_budget_max"] == 3
    h = rc["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["withheld_positive_pixels"] == 22663
    assert h["winner_dti"] == pytest.approx(0.076277, abs=1e-6)
    assert h["arms"]["r0_control"]["dti"] == pytest.approx(0.004006, abs=1e-6)
    d = h["paired_differences_vs_candidate_rank"]["r0_control"]
    assert d["ci95"][0] > 0  # paired improvement over R0 excludes zero
    assert rc["sgmc_proxy"]["evidence_class"].startswith("PROXY")
    assert rc["leakage_canary"]["passed"] is True
    assert rc["leakage_canary"]["max_symmetric_auc"] <= 0.90


def test_provcrest_uniqueness_gates():
    u = _card()["uniqueness"]
    assert u["sparse_gate_pass"] is True
    assert u["literal_all_raster_gate_pass"] is False
    assert u["literal_worst_dot_overlap_3px"] == 1.0
    assert u["errors"] == []
    assert abs(u["worst_sparse_spearman"]["rho"]) <= 0.90
    assert u["worst_sparse_dot_overlap_3px"]["overlap"] <= 0.70
    rows = json.loads((ROOT / "evidence" / "provcrest_uniqueness.json").read_text())["rows"]
    assert len(rows) == u["rasters_checked"]
    dense = [r for r in rows if r.get("representation_class") == "continuous_or_dense"]
    assert dense and all(r["positive_fraction_in_footprint"] > 0.50 for r in dense)


def test_provcrest_tif_bytes_range_and_note():
    rc = _card()
    tif = ROOT / rc["submission"]["file"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == rc["submission"]["sha256"]
    assert stat.S_IMODE(tif.stat().st_mode) & stat.S_IROTH
    zpath = ROOT / rc["submission"]["zip_file"]
    with zipfile.ZipFile(zpath) as z:
        assert z.namelist() == [tif.name]
        assert hashlib.sha256(z.read(tif.name)).hexdigest() == rc["submission"]["sha256"]
    note = rc["submission"]["submission_note"]
    assert 0 < len(note) <= 140 and rc["submission"]["submission_note_chars"] == len(note)
    with rasterio.open(tif) as ds:
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611" and ds.nodata is None
        a = ds.read(1)
    assert np.isfinite(a).all() and a.min() >= 0.0 and a.max() <= 1.0
    assert set(np.unique(a).tolist()) <= {0.0, 1.0}
    assert int((a > 0).sum()) == 37654
    v = rc["validator"]
    assert v["all_checks_passed"] if "all_checks_passed" in v else v["vendor_validate"]["all_checks_passed"]
    assert v["min_catalogue_distance_px"] > 3.0


@pytest.mark.skipif(not (ROOT / "data" / "bridge" / "sample_submission.tif").is_file(),
                    reason="gitignored bridge rasters not restored in this checkout")
def test_provcrest_transform_and_catalogue_on_disk():
    rc = _card()
    with rasterio.open(ROOT / rc["submission"]["file"]) as c, \
            rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as s, \
            rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as e:
        assert c.transform == s.transform and c.crs == s.crs
        a = c.read(1); cat = e.read(1) > 0; foot = np.isfinite(s.read(1))
    assert not np.any((a > 0) & cat)
    assert np.all(a[~foot] == 0.0)


def test_provcrest_ledger_single_row_no_receipt():
    rc = _card()
    stem = Path(rc["submission"]["file"]).stem
    rows = list(csv.DictReader((ROOT / "ledger" / "submissions.csv").open()))
    ours = [r for r in rows if r["id"] == stem]
    assert len(ours) == 1
    assert ours[0]["axis"] == "PROVCREST" and ours[0]["receipt_score"] == ""
    pairs = [(r["parent"], r["axis"], r["value"]) for r in rows]
    assert len(pairs) == len(set(pairs))
