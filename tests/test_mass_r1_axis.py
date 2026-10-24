"""Tests for AXIS=MASS on the gate-clean parent R1 (= PRUNEp3px).

Three layers:

* Preregistration integrity — the three arms, the fixed 10% dose, the parent SHA-256
  twins and the "frozen before build" flag were all written before the build.
* Artifact / ledger integrity — three BUILT rows with MODEL-labelled predictions,
  unique SHA-256, no repeated ``(parent, axis, value)``, mechanism cards complete
  for a structural geologist, receipts matching the ledger and the axis report.
* Gate re-derivation from the bytes — format, zero catalogue mass, strict ``> 3 px``
  collar, requested dot counts and parent-diff percentages. Skipped when the
  (gitignored) competition rasters are absent, e.g. on a fresh clone.

The solver functions themselves (``select_exact_marginal_dti_add/_drop``) are covered
by ``tests/test_mass_r0_axis.py``; this family reuses them unchanged, which is what
makes its deltas comparable to the R0 ``r10*`` arms arm-for-arm.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_snap_r1_variants as bsv  # noqa: E402

PARENT_ID = bsv.R1_ID
AXIS = "MASS"
VALUES = ("r1m10minus", "r1m10plus", "r1m10swap")
EXPECTED_DOTS = {"r1m10minus": 33_889, "r1m10plus": 41_419, "r1m10swap": 37_654}
DOSE = 3_765
PARENT_DOTS = 37_654
REPORT = ROOT / "evidence" / "mass_r1_axis_report.json"
PREREG = ROOT / "registry" / "preregistration_mass_r1.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
RELEASES = ROOT / "releases"


def _rows() -> list[dict[str, str]]:
    with LEDGER.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _mine() -> list[dict[str, str]]:
    return [
        r for r in _rows()
        if r["parent"] == PARENT_ID and r["axis"] == AXIS and r["value"] in VALUES
    ]


# ---------------------------------------------------------------------------
# Preregistration
# ---------------------------------------------------------------------------


def test_preregistration_was_frozen_and_covers_all_arms() -> None:
    pre = json.loads(PREREG.read_text(encoding="utf-8"))
    assert pre["frozen_before_build"] is True
    assert pre["parent"]["id"] == PARENT_ID
    assert pre["parent"]["sha256_zeros"] == bsv.R1_SHA_ZEROS
    assert pre["parent"]["sha256_nan"] == bsv.R1_SHA_NAN
    assert pre["axis_assignment"]["axis"] == AXIS
    assert set(pre["arms"]) == set(VALUES)
    assert pre["fixed_dose"]["n_dots"] == DOSE
    assert pre["fixed_dose"]["fraction"] == pytest.approx(0.10)
    assert pre["fixed_dose"]["n_dots"] == round(pre["fixed_dose"]["fraction"] * PARENT_DOTS)
    for arm in pre["arms"].values():
        assert arm["preregistered_prediction"]
        lo, hi = [float(x) for x in arm["preregistered_range"].strip("[]").split(",")]
        assert lo < hi
        for field in ("mechanism", "non_fault_mimic", "predicted_sign_size", "falsifier"):
            assert arm[field].strip(), field
        assert arm["resulting_dots"] in EXPECTED_DOTS.values()


def test_prereg_pairs_are_not_repeated_in_the_ledger() -> None:
    # No (parent, axis, value) may repeat anywhere, and this family's values must not
    # collide with the pre-existing R0 MASS family.
    keys = [(r["parent"], r["axis"], r["value"]) for r in _rows()]
    assert len(keys) == len(set(keys)), "repeated (parent, axis, value) in ledger"
    r0_values = {r["value"] for r in _rows() if r["parent"] == "h33-h33-2-b2"}
    assert not (set(VALUES) & r0_values)


# ---------------------------------------------------------------------------
# Ledger / cards / receipts
# ---------------------------------------------------------------------------


def test_ledger_rows_are_complete_and_unique() -> None:
    mine = _mine()
    assert len(mine) == 3
    for r in mine:
        assert r["status"] == "BUILT"
        assert r["n_dots"] == str(EXPECTED_DOTS[r["value"]])
        assert r["predicted_change"].startswith("MODEL:")
        assert r["receipt_score"] == "" and r["receipt_date"] == ""
        assert float(r["pct_changed"]) == pytest.approx(10.0, abs=0.01)
        assert "preregistered" in r["description"].lower()
        assert "SGMC" in r["description"]
        assert len(r["id"]) <= 140
    shas = [r["sha256"] for r in _rows()] + [r["sha256_zeros"] for r in _rows() if r["sha256_zeros"] != r["sha256"]]  # single-file de-novo rows: sha256_zeros == sha256 (no distinct NaN twin), count once
    shas = [s for s in shas if s]
    assert len(shas) == len(set(shas)), "duplicate SHA-256 in ledger"


def test_mechanism_cards_are_written_for_a_geologist() -> None:
    cards = json.loads(CARDS.read_text())
    mine = {
        k: v for k, v in cards.items()
        if v.get("parent") == PARENT_ID and v.get("axis") == AXIS and v.get("value") in VALUES
    }
    assert len(mine) == 3
    for card in mine.values():
        for field in (
            "hypothesis",
            "mechanism",
            "non_fault_mimic",
            "predicted_sign_size",
            "falsifier",
            "preregistered_prediction",
            "evidence_discipline",
        ):
            assert card[field].strip(), field


def test_receipts_and_report_agree_with_the_ledger() -> None:
    rep = json.loads(REPORT.read_text())
    assert rep["axis"] == AXIS
    assert rep["parent"]["id"] == PARENT_ID
    assert rep["parent"]["sha256_zeros"] == bsv.R1_SHA_ZEROS
    assert rep["verified_inputs"] == 15
    assert rep["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    by_value = {v["value"]: v for v in rep["variants"]}
    assert set(by_value) == set(VALUES)
    for r in _mine():
        rec = json.loads((RELEASES / f"{r['id']}.json").read_text())
        assert rec["sha256"] == r["sha256"]
        assert rec["sha256_zeros"] == r["sha256_zeros"]
        assert rec["axis"] == AXIS and rec["value"] == r["value"]
        assert rec["parent"] == PARENT_ID
        assert rec["n_dots"] == EXPECTED_DOTS[rec["value"]]
        assert rec["gates"]["zero_catalogue_mass"] is True
        assert rec["gates"]["reread_from_disk_verified"] is True
        assert rec["parent_diff"]["min_dist_catalogue_px"] > 3.0
        assert rec["preregistered_prediction"] == by_value[r["value"]]["preregistered_prediction"]
        assert rec["w_model"]["delta_vs_parent_r1"] == by_value[r["value"]]["w_model"]["delta_vs_parent_r1"]


# ---------------------------------------------------------------------------
# Gate re-derivation from the bytes (skipped without the competition rasters)
# ---------------------------------------------------------------------------

TIFFS = [
    p for p in sorted(RELEASES.glob(f"{PARENT_ID}-{AXIS}r1m10*.tif")) if "-zeros" not in p.name
]


@pytest.mark.skipif(not TIFFS, reason="competition rasters are gitignored (run the builder)")
def test_released_rasters_pass_every_must_gate_on_disk() -> None:
    import numpy as np
    import rasterio
    from scipy.ndimage import distance_transform_edt

    sample = ROOT / "data" / "bridge" / "sample_submission.tif"
    faults = ROOT / "data" / "bridge" / "existing_faults.tif"
    if not (sample.is_file() and faults.is_file()):
        pytest.skip("bridge inputs absent")

    with rasterio.open(sample) as ds:
        ref = (ds.shape, ds.crs, ds.transform)
        foot = np.isfinite(ds.read(1))
    with rasterio.open(faults) as fs:
        catalogue = fs.read(1) > 0
    d_cat = distance_transform_edt(~catalogue)

    assert len(TIFFS) == 3
    for p in TIFFS:
        with rasterio.open(p) as ds:
            arr = ds.read(1)
            assert (ds.shape, ds.crs, ds.transform) == ref
            assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert np.isnan(arr[~foot]).all()
        assert np.isfinite(arr[foot]).all()
        assert float(arr[foot].min()) >= 0.0 and float(arr[foot].max()) <= 1.0
        assert int((arr[catalogue] > 0).sum()) == 0
        dots = arr > 0.5
        assert int(dots.sum()) in EXPECTED_DOTS.values()
        assert float(d_cat[dots].min()) > 3.0
        zeros = p.with_name(p.stem + "-zeros.tif")
        assert zeros.is_file()
        with rasterio.open(zeros) as zs:
            zarr = zs.read(1)
        assert np.array_equal(zarr > 0.5, dots)
        assert float(np.abs(zarr[~foot]).max()) == 0.0
