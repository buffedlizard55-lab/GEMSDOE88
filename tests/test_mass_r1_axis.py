"""Unit & integration tests for the AXIS=MASS session on gate-clean parent R1.

R1 = h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705 (37,654 dots, min d_cat 3.1623 px).
These tests cover:

1. Preregistration frozen before the build and covering all three arms.
2. Report arithmetic: exact 3,765-dot dose, arm counts 33,889 / 41,419 / 37,654,
   100% of dots beyond the 3 px catalogue collar, zero catalogue mass, added dots
   strictly at d_cat > 3 px, and the R1 parent SHA assertion recorded before edit.
3. Ledger integrity: exactly three R1 MASS rows, BUILT, MODEL-labelled, no
   receipts, unique hashes and no repeated (parent, axis, value) anywhere.
4. Mechanism cards for a structural geologist on every arm.
5. On-disk MUST gates whenever the gitignored rasters are restored locally.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_variants as bpv  # noqa: E402

AXIS = "MASS"
R0_ID = "h33-h33-2-b2"
R1_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
R1_SHA_NAN = "6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9"
R1_SHA_ZEROS = "dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f"
VALUES = ("r10minus", "r10plus", "r10swap")
EXPECTED_DOTS = {"r10minus": 33_889, "r10plus": 41_419, "r10swap": 37_654}
DOSE = 3_765
PARENT_DOTS = 37_654
REPORT = ROOT / "evidence" / "mass_r1_axis_report.json"
LEDGER = ROOT / "ledger" / "submissions.csv"


def _report() -> dict:
    if not REPORT.is_file():
        pytest.skip("evidence/mass_r1_axis_report.json absent (MASS-on-R1 build not run locally)")
    return json.loads(REPORT.read_text())


def test_preregistration_precedes_and_covers_every_arm() -> None:
    pre = json.loads((ROOT / "registry" / "mass_r1_preregistration.json").read_text())
    assert pre["frozen_before_any_variant_proxy"] is True
    assert pre["parent"]["id"] == R1_ID
    assert pre["parent"]["parent_sha256_nan"] == R1_SHA_NAN
    assert pre["parent"]["parent_sha256_zeros"] == R1_SHA_ZEROS
    assert pre["fixed_dose"]["fraction"] == 0.10
    assert pre["fixed_dose"]["n_dots"] == DOSE
    assert pre["fixed_dose"]["parent_dots"] == PARENT_DOTS
    for v in VALUES:
        assert v in pre["arms"]
        assert pre["arms"][v]["preregistered_prediction"].startswith(("+", "-"))
        assert pre["arms"][v]["preregistered_range"].startswith("[")
    assert pre["ranking_definition"]["code"].startswith("vendor/gems57/metric.py")


def test_report_records_exact_r1_parent_and_arm_counts() -> None:
    rep = _report()
    p = rep["parent"]
    assert p["n_dots"] == PARENT_DOTS
    assert p["sha_asserted_before_edit"] is True
    assert p["rederived_nan_sha256"] == R1_SHA_NAN
    assert p["rederived_zeros_sha256"] == R1_SHA_ZEROS
    assert p["min_d_cat_px"] == pytest.approx(3.1623, abs=1e-4)
    assert rep["r0_reference"]["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    assert rep["dose"] == {"fraction": 0.10, "n_dots": DOSE}
    assert rep["candidate_pool_px"] == 59_310
    assert rep["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    by_value = {v["value"]: v for v in rep["variants"]}
    for v in VALUES:
        assert by_value[v]["n_dots"] == EXPECTED_DOTS[v]
        pd = by_value[v]["parent_diff"]
        assert 1.0 <= pd["pct_changed_moved"] <= 50.0
        assert pd["pct_changed_basis"] == "max"
        assert int(pd["dots_le_1px"]) == 0
        assert int(pd["dots_le_2px"]) == 0
        assert int(pd["dots_le_3px"]) == 0
        assert pd["min_dist_catalogue_px"] == pytest.approx(3.1623, abs=1e-4)
        assert by_value[v]["gates"]["zero_catalogue_mass"]
        assert by_value[v]["gates"]["reread_from_disk_verified"]
        assert by_value[v]["form_note_chars"] <= 140
        assert by_value[v]["w_model"]["delta_vs_r1"] == pytest.approx(
            by_value[v]["w_model"]["dti"] - rep["parent"]["w_model"]["dti"], abs=1e-6
        )


def test_dose_and_collar_are_exact() -> None:
    rep = _report()
    by_value = {v["value"]: v for v in rep["variants"]}
    assert by_value["r10minus"]["parent_diff"]["n_removed"] == DOSE
    assert by_value["r10minus"]["parent_diff"]["n_added"] == 0
    assert by_value["r10plus"]["parent_diff"]["n_added"] == DOSE
    assert by_value["r10plus"]["parent_diff"]["n_removed"] == 0
    assert by_value["r10plus"]["added_dots"]["min_d_cat_px"] > 3.0
    assert by_value["r10swap"]["parent_diff"]["n_added"] == DOSE
    assert by_value["r10swap"]["parent_diff"]["n_removed"] == DOSE
    assert by_value["r10swap"]["n_dots"] == PARENT_DOTS
    assert by_value["r10swap"]["added_dots"]["min_d_cat_px"] > 3.0
    # every arm stays gate-clean: no dot at or inside the 3 px kernel collar
    for v in VALUES:
        assert by_value[v]["parent_diff"]["min_dist_catalogue_px"] > 3.0
        assert by_value[v]["removed_dots"]["n"] + by_value[v]["added_dots"]["n"] in (DOSE, 2 * DOSE)


def test_ledger_rows_are_unique_and_r1_scoped() -> None:
    rows = list(csv.DictReader(LEDGER.open(newline="")))
    mine = [r for r in rows if r["parent"] == R1_ID and r["axis"] == AXIS and r["value"] in VALUES]
    assert len(mine) == 3, [r["id"] for r in mine]
    # the R0 MASS family must remain exactly three rows (scoping regression guard)
    r0_mass = [r for r in rows if r["parent"] == R0_ID and r["axis"] == AXIS
               and r["value"] in VALUES]
    assert len(r0_mass) == 3
    shas = [r["sha256"] for r in rows if r["sha256"]] + [
        r["sha256_zeros"] for r in rows if r["sha256_zeros"]
    ]
    assert len(shas) == len(set(shas)), "duplicate SHA-256 in ledger"
    for r in mine:
        assert r["status"] == "BUILT"
        assert r["n_dots"] == str(EXPECTED_DOTS[r["value"]])
        assert r["predicted_change"].startswith("MODEL:")
        assert r["receipt_score"] == "" and r["receipt_date"] == ""
        assert float(r["pct_changed"].replace("%", "")) >= 1.0
        assert "preregistered" in r["description"]
        assert len(r["id"]) <= 140
    keys = [(r["parent"], r["axis"], r["value"]) for r in rows]
    assert len(keys) == len(set(keys))


def test_mechanism_cards_cover_every_r1_arm_for_a_geologist() -> None:
    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
    mine = {k: v for k, v in cards.items() if k.startswith(f"{R1_ID}-MASSr")}
    assert len(mine) == 3
    for card in mine.values():
        for field in (
            "hypothesis",
            "mechanism",
            "non_fault_mimic",
            "predicted_sign_size",
            "falsifier",
            "preregistered_prediction",
        ):
            assert card[field].strip()


def test_release_receipts_match_report_and_ledger() -> None:
    rep = _report()
    for v in rep["variants"]:
        rec_path = ROOT / "releases" / f"{v['id']}.json"
        assert rec_path.is_file()
        rec = json.loads(rec_path.read_text())
        assert rec["sha256"] == v["sha256"]
        assert rec["sha256_zeros"] == v["sha256_zeros"]
        assert rec["parent"] == R1_ID
        assert rec["axis"] == AXIS
        assert rec["n_dots"] == EXPECTED_DOTS[rec["value"]]
        assert rec["parent_sha256_nan"] == R1_SHA_NAN
        assert rec["parent_sha256_zeros"] == R1_SHA_ZEROS


def test_release_rasters_revalidate_from_disk() -> None:
    rep = _report()
    import rasterio  # local import: optional at collection time

    tmpl = ROOT / "data" / "bridge" / "sample_submission.tif"
    if not tmpl.is_file():
        pytest.skip("sample_submission.tif not restored locally")
    with rasterio.open(tmpl) as ds:
        foot = np.isfinite(ds.read(1))
        ref = (ds.shape, ds.crs, ds.transform)
    checked = 0
    for v in rep["variants"]:
        p_nan = ROOT / v["file_nan"]
        p_zeros = ROOT / v["file_zeros"]
        if not (p_nan.is_file() and p_zeros.is_file()):
            continue
        assert bpv.sha256_file(p_nan) == v["sha256"]
        assert bpv.sha256_file(p_zeros) == v["sha256_zeros"]
        with rasterio.open(p_nan) as a, rasterio.open(p_zeros) as b:
            assert (a.shape, a.crs, a.transform) == ref == (b.shape, b.crs, b.transform)
            assert a.count == 1 == b.count and a.dtypes[0] == "float32" == b.dtypes[0]
            arr_n, arr_z = a.read(1), b.read(1)
        assert np.isfinite(arr_n[foot]).all() and np.isnan(arr_n[~foot]).all()
        assert np.isfinite(arr_z).all() and np.all(arr_z[~foot] == 0.0)
        assert np.array_equal(arr_n[foot], arr_z[foot])
        assert float(arr_n[foot].min()) >= 0.0 and float(arr_n[foot].max()) <= 1.0
        assert int((arr_z > 0.5).sum()) == EXPECTED_DOTS[v["value"]]
        checked += 1
    if checked == 0:
        pytest.skip("MASS-on-R1 release rasters absent locally (gitignored)")
