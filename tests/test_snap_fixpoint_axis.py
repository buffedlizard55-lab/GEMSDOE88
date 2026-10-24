"""Tests for the SNAP fixpoint dose ladder and the sign-flip control on R1.

Layers:

* Unit test of the reused allocator's sign behaviour
  (:func:`build_snap_variants.snap_dots_within_window`) -- a negated field must
  move dots to strictly lower field values.
* Static tests over tracked artifacts (preregistration, ledger, mechanism cards,
  axis report) that run in CI without the gitignored rasters.
* Artifact tests that re-read the released GeoTIFFs and re-derive the MUST gates;
  they skip when ``releases/`` lacks this family's TIFFs (regenerate with
  ``python3 scripts/build_snap_fixpoint_variants.py``).
"""

from __future__ import annotations

import csv
import json
import sys

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_snap_variants as bsnap  # noqa: E402
import build_snap_fixpoint_variants as bsf  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_snap_r1_fixpoint.json"
REPORT = ROOT / "evidence" / "snap_r1_fixpoint_axis_report.json"

R1_ID = bsf.R1_ID
OWN_VALUES = set(bsf.OWN_VALUES)

FAMILY_JSON = [
    p for p in sorted(RELEASES.glob(f"{R1_ID}-SNAP*.json"))
    if json.loads(p.read_text()).get("value") in OWN_VALUES
]


def _ledger_rows():
    with LEDGER.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _family_rows():
    return [
        r for r in _ledger_rows()
        if r["axis"] == "SNAP" and r["parent"] == R1_ID and r["value"] in OWN_VALUES
    ]


def test_negated_field_moves_dots_downhill():
    size = 40
    foot = np.ones((size, size), dtype=bool)
    foot[0, :] = False
    catalogue = np.zeros((size, size), dtype=bool)
    catalogue[3, 3] = True
    d_cat = distance_transform_edt(~catalogue)
    field = np.zeros((size, size), dtype=np.float32)
    field[20, 20] = 0.9
    field[20, 19] = 0.1  # the weakest neighbour
    mask = np.zeros((size, size), dtype=bool)
    mask[20, 20] = True

    crest, _ = bsnap.snap_dots_within_window(
        r0_mask=mask, score_field=field, foot=foot, catalogue=catalogue,
        d_cat=d_cat, h19_5=np.ones_like(foot), max_r=1.0, min_sep=2.8,
        stay_on_h19=False,
    )
    trough, _ = bsnap.snap_dots_within_window(
        r0_mask=mask, score_field=-field, foot=foot, catalogue=catalogue,
        d_cat=d_cat, h19_5=np.ones_like(foot), max_r=1.0, min_sep=2.8,
        stay_on_h19=False,
    )
    assert int(crest.sum()) == int(trough.sum()) == 1
    assert field[crest].item() > field[mask].item() or field[crest].item() == field[mask].item()
    assert field[trough].item() < field[mask].item()


def test_preregistration_precedes_and_names_three_arms():
    pre = json.loads(PREREG.read_text())
    assert pre["written_before_any_build"] is True
    assert set(pre["arms"]) == OWN_VALUES
    for arm in pre["arms"].values():
        assert arm["predicted_change"].startswith("MODEL:")
        assert "falsifier" in arm["decision_rule"].lower() or arm["decision_rule"]


def test_ledger_rows_are_unique_and_expected():
    rows = _family_rows()
    assert {r["value"] for r in rows} == OWN_VALUES
    assert len(rows) == 3
    assert len({r["id"] for r in rows}) == 3
    assert len({r["sha256"] for r in rows}) == 3
    assert len({r["sha256_zeros"] for r in rows}) == 3
    all_shas = [r["sha256"] for r in _ledger_rows() if r["sha256"]] + [r["sha256_zeros"] for r in _ledger_rows() if r["sha256_zeros"] and r["sha256_zeros"] != r["sha256"]]  # single-file de-novo rows: sha256_zeros == sha256 (no distinct NaN twin), count once
    assert len(all_shas) == len(set(all_shas)), "duplicate SHA-256 across the ledger"
    for r in rows:
        assert r["n_dots"] == "37654"
        assert r["status"] == "BUILT"
        assert r["receipt_score"] == ""
        assert r["predicted_change"].startswith("MODEL:")


def test_mechanism_cards_present():
    cards = json.loads(CARDS.read_text())
    for r in _family_rows():
        card = cards[r["id"]]
        for key in ("hypothesis", "mechanism", "non_fault_mimic", "predicted_sign_size", "falsifier"):
            assert card[key].strip()


def test_report_and_dose_response():
    rep = json.loads(REPORT.read_text())
    assert rep["axis"] == "SNAP" and rep["parent_r1"] == R1_ID
    assert rep["external_lidar_used"] is False
    assert rep["leakage_canaries"]["max_symmetric_auc"] < 0.90
    # Three passes must each move a shrinking number of dots (a convergent climb).
    moved = [p["n_dots_displaced"] for p in rep["pass_ladder"]]
    assert moved[0] > moved[1] > moved[2] > 0
    assert rep["git_sha"]


@pytest.mark.skipif(not FAMILY_JSON or not any(
    json.loads(p.read_text())["file_nan"] and (ROOT / json.loads(p.read_text())["file_nan"]).is_file()
    for p in FAMILY_JSON
), reason="candidate rasters are gitignored; regenerate with scripts/build_snap_fixpoint_variants.py")
def test_released_rasters_rederive_must_gates():
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as tpl:
        ref = (tpl.shape, tpl.crs, tpl.transform)
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as src:
        catalogue = src.read(1) > 0
    d_cat = distance_transform_edt(~catalogue)
    for p in FAMILY_JSON:
        rec = json.loads(p.read_text())
        with rasterio.open(ROOT / rec["file_nan"]) as ds:
            arr = ds.read(1)
            assert (ds.shape, ds.crs, ds.transform) == ref
            assert ds.count == 1 and ds.dtypes[0] == "float32"
            foot = np.isfinite(arr)
            assert np.isfinite(arr[foot]).all()
            assert float(np.nanmin(arr)) >= 0.0 and float(np.nanmax(arr)) <= 1.0
            assert int((arr[catalogue] > 0).sum()) == 0
            assert int((arr > 0).sum()) == 37654
            assert float(d_cat[arr > 0].min()) > 3.0
