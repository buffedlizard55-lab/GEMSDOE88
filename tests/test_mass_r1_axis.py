"""Tests for AXIS=MASS on the gate-clean parent R1 (``PRUNEp3px``).

Three layers:

* Unit tests on a synthetic grid for the reused exact-marginal solvers under R1
  conditions (every dot already outside the 3 px collar, so an ADD arm can only
  stay gate-clean if the candidate pool itself is collar-filtered).
* Static tests over tracked artifacts (preregistration, ledger, mechanism cards,
  axis report) that run in CI without the gitignored rasters.
* Artifact tests that re-read the released GeoTIFFs from disk and re-derive every
  MUST gate; they skip when ``releases/`` lacks the family's TIFFs (competition
  rasters are gitignored; regenerate with
  ``python3 scripts/build_mass_r1_variants.py``).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_prune_variants as bpv  # noqa: E402
import build_snap_r1_variants as bsv  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_mass_r1.json"
REPORT = ROOT / "evidence" / "mass_r1_axis_report.json"

AXIS = "MASS"
R1_ID = bsv.R1_ID
R1_SHA_NAN = bsv.R1_SHA_NAN
R1_SHA_ZEROS = bsv.R1_SHA_ZEROS
VALUES = ("r10minus", "r10plus", "r10swap")
EXPECTED_DOTS = {"r10minus": 33_889, "r10plus": 41_419, "r10swap": 37_654}
DOSE = 3_765
PARENT_DOTS = 37_654

FAMILY_JSON = [
    p for p in sorted(RELEASES.glob(f"{R1_ID}-MASS*.json"))
    if p.with_suffix("").with_suffix(".tif").is_file()
    and json.loads(p.read_text()).get("value") in VALUES
]


def _ledger_rows():
    with LEDGER.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _family_rows():
    return [
        r for r in _ledger_rows()
        if r["axis"] == AXIS and r["parent"] == R1_ID and r["value"] in VALUES
    ]


def _report() -> dict:
    if not REPORT.is_file():
        pytest.skip("evidence/mass_r1_axis_report.json absent (MASS-R1 build not run locally)")
    return json.loads(REPORT.read_text())


# ---------------------------------------------------------------------------
# Unit tests: solvers under R1 conditions
# ---------------------------------------------------------------------------


def _synthetic():
    """R1-style parent: a spaced dot field, all dots far from the catalogue."""
    rng = np.random.default_rng(20261023)
    size = 48
    w = np.zeros((size, size), dtype=np.float64)
    w[10:13, 5:43] = 1.0
    w[30:32, 5:43] = 0.5
    w += rng.uniform(0, 0.05, w.shape)
    foot = np.ones((size, size), dtype=bool)
    catalogue = np.zeros((size, size), dtype=bool)
    catalogue[0, 0] = True          # corner: distance grows away from it
    base = np.zeros((size, size), dtype=bool)
    base[11, 6:42:4] = True
    base[30, 6:42:5] = True
    d_cat = distance_transform_edt(~catalogue)
    base &= d_cat > 3.0
    return base, w, foot, catalogue, d_cat


def test_add_solver_only_emits_pool_pixels_and_keeps_the_collar():
    base, w, foot, catalogue, d_cat = _synthetic()
    pool = (d_cat > 3.0) & foot & ~base
    pool[:] = pool & (np.arange(pool.shape[0])[:, None] > 8)  # keep a realistic sub-pool
    before = int(base.sum())
    out = bpv.select_exact_marginal_dti_add(base, pool, w, 12)
    assert int(out.sum()) == before + 12
    added = out & ~base
    assert np.all(added <= pool)
    assert float(d_cat[out].min()) > 3.0
    assert not (out & catalogue).any()


def test_drop_solver_removes_exactly_the_dose_and_keeps_the_collar():
    base, w, _, _, d_cat = _synthetic()
    out = bpv.select_exact_marginal_dti_drop(base, base, w, 5)
    assert int(out.sum()) == int(base.sum()) - 5
    assert float(d_cat[out].min()) > 3.0


def test_swap_never_re_adds_a_dropped_dot():
    base, w, _, _, d_cat = _synthetic()
    pool = (d_cat > 3.0) & ~base
    dropped = bpv.select_exact_marginal_dti_drop(base, base, w, 4)
    swapped = bpv.select_exact_marginal_dti_add(dropped, pool, w, 4)
    assert int(swapped.sum()) == int(base.sum())
    assert not (swapped & base & ~dropped).any(), "swap must not re-add a dropped parent dot"


# ---------------------------------------------------------------------------
# Preregistration, ledger, cards, report
# ---------------------------------------------------------------------------


def test_preregistration_covers_every_arm_and_names_the_parent():
    pre = json.loads(PREREG.read_text())
    assert pre["axis"] == AXIS
    assert pre["parent_chain"]["r1"]["id"] == R1_ID
    assert pre["parent_chain"]["r1"]["nan_sha256"] == R1_SHA_NAN
    assert pre["parent_chain"]["r1"]["zeros_sha256"] == R1_SHA_ZEROS
    assert pre["dose"]["n_dots"] == DOSE
    assert pre["dose"]["fraction"] == pytest.approx(0.10)
    assert {a["value"] for a in pre["arms"]} == set(VALUES)
    for arm in pre["arms"]:
        assert arm["predicted_change"].startswith("MODEL:")
        assert arm["predicted_range"].startswith("[")
        assert arm["prediction_basis"].strip()
    assert "select_exact_marginal_dti" in pre["ranking_definition"]


def test_ledger_rows_are_complete_unique_and_receipt_free():
    rows = _ledger_rows()
    mine = _family_rows()
    assert len(mine) == 3, [r["id"] for r in mine]
    shas = [r["sha256"] for r in rows if r["sha256"]] + [
        r["sha256_zeros"] for r in rows if r["sha256_zeros"]
    ]
    assert len(shas) == len(set(shas)), "duplicate SHA-256 in ledger"
    keys = [(r["parent"], r["axis"], r["value"]) for r in rows]
    assert len(keys) == len(set(keys)), "duplicate (parent, axis, value) in ledger"
    for r in mine:
        assert r["status"] == "BUILT"
        assert r["n_dots"] == str(EXPECTED_DOTS[r["value"]])
        assert r["predicted_change"].startswith("MODEL:")
        assert r["receipt_score"] == "" and r["receipt_date"] == ""
        assert 1.0 <= float(r["pct_changed"]) <= 50.0
        assert r["parent"] == R1_ID


def test_report_records_every_arm_gate_clean_on_the_gate_clean_parent():
    rep = _report()
    assert rep["parent"]["id"] == R1_ID
    assert rep["parent"]["nan_sha256"] == R1_SHA_NAN
    assert rep["parent"]["zeros_sha256"] == R1_SHA_ZEROS
    assert rep["parent"]["n_dots"] == PARENT_DOTS
    assert rep["parent"]["min_d_cat_px"] > 3.0
    assert rep["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    assert rep["dose"]["n_dots"] == DOSE
    by_value = {v["value"]: v for v in rep["variants"]}
    assert set(by_value) == set(VALUES)
    for v in VALUES:
        rec = by_value[v]
        assert rec["n_dots"] == EXPECTED_DOTS[v]
        assert rec["axis"] == AXIS and rec["parent"] == R1_ID
        assert rec["form_note_chars"] <= 140
        pd = rec["parent_diff"]
        assert pd["pct_changed_basis"] == "max"
        assert 1.0 <= pd["pct_changed_moved"] <= 50.0
        # the R1 family is gate-clean: unlike the R0 family, NO arm keeps a sub-3 px dot
        assert pd["dots_le_3px"] == 0, v
        assert pd["min_dist_catalogue_px"] > 3.0
        assert rec["gates"]["zero_catalogue_mass"]
        assert rec["gates"]["reread_from_disk_verified"]
        assert rec["gates"]["nan_outside_footprint"]
        assert rec["gates"]["zeros_fallback_valid"]


def test_dose_arithmetic_and_saturation_diagnostics():
    rep = _report()
    by_value = {v["value"]: v for v in rep["variants"]}
    assert by_value["r10minus"]["parent_diff"]["n_removed"] == DOSE
    assert by_value["r10minus"]["parent_diff"]["n_added"] == 0
    assert by_value["r10plus"]["parent_diff"]["n_added"] == DOSE
    assert by_value["r10plus"]["parent_diff"]["n_removed"] == 0
    assert by_value["r10swap"]["parent_diff"]["n_added"] == DOSE
    assert by_value["r10swap"]["parent_diff"]["n_removed"] == DOSE
    assert by_value["r10swap"]["n_dots"] == PARENT_DOTS
    for v in ("r10plus", "r10swap"):
        assert by_value[v]["added_dots"]["min_d_cat_px"] > 3.0
        assert by_value[v]["added_dots"]["n"] == DOSE
    # Every added dot is inside the 300 m kernel of an existing R1 dot: the add arm
    # densifies coverage, it does not extend strands. This is a reported diagnostic,
    # never a gate.
    assert by_value["r10plus"]["added_dot_saturation"]["frac_within_3px_of_a_parent_dot"] > 0.9


def test_random_donor_control_is_recorded_and_the_ranking_beats_it():
    rep = _report()
    ctrl = rep["random_donor_control"]
    assert ctrl["n_added"] == DOSE
    assert ctrl["sgmc_off_catalogue_dti"] > 0
    # report-only instrument, never a gate; recorded so the count effect is separable
    assert "sgmc_delta_vs_r1" in ctrl and "w_model_delta_vs_r1" in ctrl


def test_mechanism_cards_are_written_for_a_geologist():
    cards = json.loads(CARDS.read_text())
    mine = {
        k: v for k, v in cards.items()
        if k.startswith(f"{R1_ID}-MASS") and v.get("value") in VALUES
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
            "preregistered_range",
        ):
            assert card[field].strip()
        assert card["parent"] == R1_ID and card["axis"] == AXIS


def test_every_receipt_matches_its_ledger_row_and_the_twin_shas_differ():
    for row in _family_rows():
        rec = json.loads((RELEASES / f"{row['id']}.json").read_text())
        assert rec["sha256"] == row["sha256"]
        assert rec["sha256_zeros"] == row["sha256_zeros"]
        assert rec["sha256"] != rec["sha256_zeros"]
        assert rec["parent"] == R1_ID
        assert rec["axis"] == AXIS
        assert rec["n_dots"] == EXPECTED_DOTS[rec["value"]]
        assert rec["file_nan"].endswith(f"{row['id']}.tif")
        assert rec["file_zeros"].endswith(f"{row['id']}-zeros.tif")


# ---------------------------------------------------------------------------
# Disk re-read gates (skipped when the gitignored rasters are absent)
# ---------------------------------------------------------------------------


def test_release_rasters_revalidate_from_disk():
    tmpl = ROOT / "data" / "bridge" / "sample_submission.tif"
    if not tmpl.is_file():
        pytest.skip("sample_submission.tif not restored locally")
    if not FAMILY_JSON:
        pytest.skip("MASS-R1 release rasters absent locally (gitignored)")
    with rasterio.open(tmpl) as ds:
        foot = np.isfinite(ds.read(1))
        ref = (ds.shape, ds.crs, ds.transform)
    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as ds:
        catalogue = (ds.read(1) == 1) & foot
    d_cat = distance_transform_edt(~catalogue)

    checked = 0
    for rec_path in FAMILY_JSON:
        rec = json.loads(rec_path.read_text())
        p_nan = ROOT / rec["file_nan"]
        p_zeros = ROOT / rec["file_zeros"]
        assert bpv.sha256_file(p_nan) == rec["sha256"]
        assert bpv.sha256_file(p_zeros) == rec["sha256_zeros"]
        with rasterio.open(p_nan) as a, rasterio.open(p_zeros) as b:
            assert (a.shape, a.crs, a.transform) == ref == (b.shape, b.crs, b.transform)
            assert a.count == 1 == b.count
            assert a.dtypes[0] == "float32" == b.dtypes[0]
            arr_n, arr_z = a.read(1), b.read(1)
        assert np.isfinite(arr_n[foot]).all() and np.isnan(arr_n[~foot]).all()
        assert np.isfinite(arr_z).all() and np.all(arr_z[~foot] == 0.0)
        assert np.array_equal(arr_n[foot], arr_z[foot])
        assert float(arr_n[foot].min()) >= 0.0 and float(arr_n[foot].max()) <= 1.0
        dots = arr_z > 0.5
        assert int(dots.sum()) == EXPECTED_DOTS[rec["value"]]
        assert int((dots & catalogue).sum()) == 0
        assert float(d_cat[dots].min()) > 3.0, "non-PRUNE MASS arm inside the 3 px collar"
        checked += 1
    assert checked == len(FAMILY_JSON)
