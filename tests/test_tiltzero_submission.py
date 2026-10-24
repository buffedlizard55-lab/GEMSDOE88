"""TILTZERO negative-result gates (2026-10-24). Must stay DO-NOT-SUBMIT."""
import csv, hashlib, json, zipfile
from pathlib import Path
import numpy as np, rasterio
ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "registry" / "tiltzero_run_card.json"

def test_tiltzero_negative_and_not_beating_provcrest():
    rc = json.loads(CARD.read_text())
    assert rc["verdict"] == "negative"
    assert rc["submission"]["ok_to_submit"] is False
    assert rc["submission"]["organizer_confirmed_score"] is None
    h = rc["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI" and h["withheld_positive_pixels"] == 22663
    assert h["winner_dti"] == 0.055083
    assert h["winner_dti"] < 0.076277  # preregistered bar: shipped PROVCREST best
    assert h["paired_differences_vs_candidate_rank"]["r0_control"]["ci95"][0] > 0
    assert rc["leakage_canary"]["max_symmetric_auc"] <= 0.90
    u = rc["uniqueness"]
    assert abs(u["worst_sparse_spearman"]["rho"]) <= 0.90
    assert u["worst_sparse_dot_overlap_3px"]["overlap"] <= 0.70

def test_tiltzero_tif_format_but_labelled_do_not_submit():
    rc = json.loads(CARD.read_text())
    tif = ROOT / rc["submission"]["file"]
    assert "DO-NOT-SUBMIT" in tif.name
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == rc["submission"]["sha256"]
    with zipfile.ZipFile(ROOT / rc["submission"]["zip_file"]) as z:
        assert z.namelist() == [tif.name]
    assert 0 < len(rc["submission"]["submission_note"]) <= 140
    with rasterio.open(tif) as ds:
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292) and str(ds.crs) == "EPSG:32611"
        a = ds.read(1)
    assert np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1
    assert set(np.unique(a).tolist()) <= {0.0, 1.0} and int((a > 0).sum()) == 37654
    assert rc["validator"]["vendor_validate"]["all_checks_passed"] is True

def test_tiltzero_ledger_negative():
    rc = json.loads(CARD.read_text())
    stem = Path(rc["submission"]["file"]).stem
    rows = [r for r in csv.DictReader((ROOT/"ledger"/"submissions.csv").open()) if r["id"] == stem]
    assert len(rows) == 1 and rows[0]["axis"] == "TILTZERO" and rows[0]["receipt_score"] == ""
    assert rows[0]["recommendation"].startswith("NEGATIVE")
