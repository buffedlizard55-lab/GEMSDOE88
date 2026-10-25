"""Release-integrity regression for the H88-PSGV negative artifact (tracked files only)."""
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_psgv88_artifact_matches_run_card_and_is_fail_closed():
    rc = json.loads((ROOT / "registry/psgv88_run_card.json").read_text())
    assert (ROOT / "registry/psgv88_run_card.json").read_text() == (ROOT / "docs/data/psgv88_run_card.json").read_text()
    assert (ROOT / "registry/psgv88_gate_v3.json").read_text() == (ROOT / "docs/data/psgv88_gate_v3.json").read_text()
    assert rc["verdict"] == "negative" and rc["ok_to_submit"] is False and rc["ok_to_download"] is True
    assert rc["weekly_slots_spent"] == 0 and rc["organizer_confirmed_score"] is None
    assert len(rc["submission_name"]) <= 140 and len(rc["submission_note"]) <= 140
    assert "DO-NOT-SUBMIT" in rc["download"]
    h = rc["holdout_dti"]["candidate_exp03"]
    assert h["evidence_class"] == "HOLDOUT-DTI" and h["withheld_positive_pixels"] == 22893
    assert h["dti"] <= 0.2029470713394289  # pre-registered kill rule: must exceed HGVC bar
    tif = ROOT / rc["download"]
    zip_p = ROOT / rc["zip_download"]
    assert _sha(tif) == rc["raster_sha256"] and _sha(zip_p) == rc["zip_sha256"]
    with zipfile.ZipFile(zip_p) as z:
        assert z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes()
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32" and ds.nodata is None
        assert (ds.height, ds.width) == (3730, 3292) and ds.crs.to_epsg() == 32611
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    assert np.isfinite(a).all() and np.all((a >= 0) & (a <= 1))
    assert int((a > 0).sum()) == rc["validator_output"]["positive_dots"] == 37654
    uq = json.loads((ROOT / "evidence/psgv88_uniqueness.json").read_text())
    assert uq["worst_like_for_like_overlap"]["value"] > 0.70  # HGVC-lane duplicate, documented
    assert uq["candidate_sha256"] == rc["raster_sha256"]
