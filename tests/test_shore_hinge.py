import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "registry/shore_hinge_run_card.json"
TIF = ROOT / "docs/downloads/gems88-shore-hinge-piedmont-20261024-42dc0afa-zeros-DO-NOT-SUBMIT.tif"
ZIP = ROOT / "docs/downloads/gems88-shore-hinge-piedmont-20261024-42dc0afa-zeros-DO-NOT-SUBMIT.zip"

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def test_shore_run_card_schema_and_verdict():
    card = json.loads(CARD.read_text())
    assert card["schema"] == "gems88.run-card.v3"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True and card["ok_to_submit"] is False
    assert card["submission"]["verdict"] == "negative"
    assert len(card["submission_name"]) <= 140 and len(card["submission_note"]) <= 140
    assert card["submission_note"] == "SHORE-HINGE piedmont hinge+shoreline filter 37654 dots; HOLDOUT-DTI 0.0000 vs R0 0.0039; UNSCORED"
    assert len(card["submission_note"]) == 97
    assert card["emitted_dots"] == 37654
    assert card["holdout_dti"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert card["holdout_dti"]["withheld_positive_pixels"] == 22893
    assert 0.0 <= card["holdout_dti"]["candidate"] <= 1.0
    assert card["validator"]["fingerprint_pass"] is True

def test_shore_geotiff_format():
    assert "DO-NOT-SUBMIT" in TIF.name and "DO-NOT-SUBMIT" in ZIP.name
    card = json.loads(CARD.read_text())
    assert sha256(TIF) == card["validator"]["raster_sha256"] == card["submission"]["sha256"]
    assert sha256(ZIP) == card["validator"]["zip_sha256"] == card["submission"]["zip_sha256"]
    with rasterio.open(TIF) as ds:
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert ds.shape == (3730, 3292)
        assert ds.crs.to_epsg() == 32611
        assert ds.nodata is None
        a = ds.read(1)
    assert np.isfinite(a).all()
    assert float(a.min()) >= 0.0 and float(a.max()) <= 1.0
    assert sorted(np.unique(a).tolist()) == [0.0, 1.0]
    assert int((a > 0).sum()) == 37654
    # footprint zero outside (verified via sample finite mask if present)
    sample = ROOT / "data/bridge/sample_submission.tif"
    if sample.exists():
        with rasterio.open(sample) as s:
            fp = np.isfinite(s.read(1))
        assert int(((a > 0) & ~fp).sum()) == 0

def test_shore_zip_single_member():
    with zipfile.ZipFile(ZIP) as z:
        assert z.namelist() == [TIF.name]
        assert z.read(TIF.name) == TIF.read_bytes()
        assert zipfile.ZipFile(ZIP).testzip() is None

def test_shore_uniqueness_no_self_collision():
    card = json.loads(CARD.read_text())
    u = card["uniqueness"]
    assert u["unique_like_for_like"] is True
    assert u["worst_like_for_like_overlap"]["value"] <= 0.70
    assert u["worst_abs_rho"]["value"] <= 0.90
    # literal is disclosed, not hidden
    assert u["literal_worst_overlap"] == 1.0
    assert u["literal_duplicate"] is True
