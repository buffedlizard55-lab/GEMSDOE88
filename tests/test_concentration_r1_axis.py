"""Tests for AXIS=CONCENTRATION on gate-clean parent R1 = PRUNEp3px.

Two layers, mirroring tests/test_spacing_axis.py:

* Unit tests on synthetic grids for ``robust_unit`` / ``block_tables`` /
  ``block_density_cv`` / ``spacing_blocked_mask`` / ``greedy_place`` /
  ``choose_donors`` - the spacing lock, the collar, the fixed count, the
  keep-one-dot-per-block rule and determinism are properties of the algorithm,
  not of the shipped files.
* Artifact tests that re-read the three releases from disk and re-derive the
  MUST gates (format, zero catalogue mass, 3 px collar, fixed 37,654 count,
  10/20/10 % parent diff vs R1, preregistered predictions, ledger + cards +
  report consistency).

Artifact tests skip when the gitignored rasters are absent (fresh clone):
regenerate with ``python scripts/build_concentration_r1_variants.py`` after
restoring the pinned inputs.  PROXY values are asserted to be *reported*,
never gated.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_concentration_r1_variants as ccv  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_concentration_r1.json"
REPORT = ROOT / "evidence" / "concentration_r1_axis_report.json"

OUR_VALUES = set(ccv.ARMS)
CRES_JSON = [
    p for v in OUR_VALUES
    for p in sorted(RELEASES.glob(f"{ccv.R1_ID}-CONCENTRATION{v}-*.json"))
    if (RELEASES / f"{p.stem}.tif").is_file()
]


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_robust_unit_is_bounded_and_monotone():
    a = np.array([[0.0, 1.0, 2.0, 3.0, 100.0]], dtype=np.float32)
    valid = np.ones_like(a, dtype=bool)
    out = ccv.robust_unit(a, valid)
    assert float(out.min()) >= 0.0 and float(out.max()) <= 1.0
    assert np.all(np.diff(out[0, :4]) >= 0)
    # values outside the valid mask stay exactly zero
    invalid = np.zeros_like(valid)
    assert float(ccv.robust_unit(a, invalid).max()) == 0.0


def test_spacing_offsets_are_strictly_inside_the_lock():
    # The stamp includes its own centre (so a placed receiver forbids its own pixel)
    # and every integer offset closer than the lock, and nothing else.
    assert (0, 0) in ccv.SPACING_OFFSETS
    for dy, dx in ccv.SPACING_OFFSETS:
        assert 0 <= dy * dy + dx * dx < ccv.SPACING_PX ** 2
    # (2,2) is 2.8284 px >= 2.8 and must therefore be a legal placement
    assert (2, 2) not in ccv.SPACING_OFFSETS
    assert (1, 1) in ccv.SPACING_OFFSETS and (2, 1) in ccv.SPACING_OFFSETS


def test_spacing_blocked_mask_blocks_only_within_the_lock():
    shape = (9, 9)
    blocked = ccv.spacing_blocked_mask(np.array([[4, 4]]), shape)
    assert blocked[4, 4] and blocked[4, 5] and blocked[5, 5]
    # (2,2) is 2.8284 px away and therefore legal under a 2.8 px lock
    assert not blocked[6, 6]
    assert not blocked[7, 7]


def test_greedy_place_honours_lock_collar_and_count():
    shape = (20, 20)
    blocked = np.zeros(shape, dtype=bool)
    d_cat = np.full(shape, 10.0)
    d_cat[0, :] = 1.0  # catalogue row: every candidate there must be rejected
    cy, cx = np.meshgrid(np.arange(shape[0]), np.arange(shape[1]), indexing="ij")
    cy, cx = cy.ravel(), cx.ravel()
    placed = ccv.greedy_place(cy, cx, blocked, d_cat, 5)
    assert int(placed.sum()) == 5
    assert not placed[0, :].any()
    pts = np.column_stack(np.nonzero(placed)).astype(np.float64)
    assert float(cKDTree(pts).query(pts, k=2)[0][:, 1].min()) >= ccv.SPACING_PX
    # determinism
    again = ccv.greedy_place(cy, cx, blocked, d_cat, 5)
    assert np.array_equal(placed, again)


def test_greedy_place_raises_when_the_pool_is_exhausted():
    blocked = np.zeros((6, 6), dtype=bool)
    d_cat = np.full((6, 6), 10.0)
    cy = np.array([0], dtype=np.int64)
    cx = np.array([0], dtype=np.int64)
    with pytest.raises(RuntimeError):
        ccv.greedy_place(cy, cx, blocked, d_cat, 2)


def _toy_tables():
    foot = np.ones((40, 40), dtype=bool)
    prior = np.tile(np.linspace(0.0, 1.0, 40, dtype=np.float32), (40, 1))
    return foot, prior, ccv.block_tables(foot, prior)


def test_block_tables_mark_only_full_blocks_eligible():
    foot = np.ones((40, 40), dtype=bool)
    foot[0, 0] = False
    prior = np.ones((40, 40), dtype=np.float32)
    tables = ccv.block_tables(foot, prior)
    assert tables["nblocks"] == 16
    # block 0 contains the missing pixel -> not full, not eligible
    assert not tables["full"][0]
    assert 0 not in set(tables["eligible"].tolist())
    assert len(tables["eligible"]) == 15
    assert np.allclose(tables["block_prior"][tables["eligible"]], 1.0)


def test_block_density_cv_flags_concentration():
    foot = np.ones((40, 40), dtype=bool)
    dots = np.zeros((40, 40), dtype=bool)
    dots[0:10, 0:10] = True  # one filled block only
    cv = ccv.block_density_cv(dots, foot, 10)
    assert cv["cv_all_full_blocks"] > 2.0
    assert cv["cv_occupied_full_blocks"] == pytest.approx(0.0, abs=1e-9)
    empty = ccv.block_density_cv(np.zeros_like(dots), foot, 10)
    assert empty["n_occupied_full_blocks"] == 0


def test_choose_donors_is_cold_first_and_keeps_one_dot_per_block():
    foot, prior, tables = _toy_tables()
    parent = np.zeros((40, 40), dtype=bool)
    # block (0,0) is the coldest block; put 3 dots in it and 3 in the hottest
    parent[1, 1] = parent[1, 3] = parent[3, 1] = True
    parent[1, 35] = parent[1, 37] = parent[3, 35] = True
    donors = ccv.choose_donors(parent, prior, tables, 2, "high")
    assert int(donors.sum()) == 2
    ys, xs = np.nonzero(donors)
    assert np.all(xs < 10)  # both come out of the cold block
    # the cold block must still hold one dot
    assert int(parent[0:10, 0:10].sum() - donors[0:10, 0:10].sum()) == 1
    again = ccv.choose_donors(parent, prior, tables, 2, "high")
    assert np.array_equal(donors, again)


def test_choose_donors_raises_when_the_pool_is_too_small():
    foot, prior, tables = _toy_tables()
    parent = np.zeros((40, 40), dtype=bool)
    parent[1, 1] = True  # a single dot in a single block: keep-one rule blocks it
    with pytest.raises(RuntimeError):
        ccv.choose_donors(parent, prior, tables, 1, "high")


def test_preregistration_matches_builder_and_is_predictive():
    prereg = json.loads(PREREG.read_text())
    assert prereg["written_before_any_proxy"] is True
    assert prereg["axis"] == "CONCENTRATION"
    assert prereg["parent"]["id"] == ccv.R1_ID
    assert prereg["parent"]["sha256_nan"] == ccv.R1_SHA_NAN
    assert prereg["parent"]["sha256_zeros"] == ccv.R1_SHA_ZEROS
    arms = {a["value"]: a for a in prereg["arms"]}
    assert set(arms) == OUR_VALUES
    for value, (frac, _pole) in ccv.ARMS.items():
        assert arms[value]["move_frac"] == frac
        assert arms[value]["n_moved"] == int(round(frac * ccv.N_PARENT_DOTS))
        assert arms[value]["predicted_change"] == ccv.PREDICTIONS[value][0]
        assert arms[value]["predicted_range"] == ccv.PREDICTIONS[value][1]
    assert prereg["definition"]["block_px"] == ccv.BLOCK_PX == 10
    assert prereg["definition"]["prior_bands_1indexed"] == list(ccv.PRIOR_BANDS)
    assert prereg["definition"]["block_m"] == ccv.BLOCK_PX * 100


def test_collar_constant_meets_the_brief():
    assert ccv.MIN_CATALOGUE_PX >= 3.0
    assert ccv.N_DOTS == ccv.N_PARENT_DOTS == 37_654
    assert ccv.R1_ID.endswith("6f7ae705")


# ---------------------------------------------------------------------------
# Artifact tests (skip without locally built rasters)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not CRES_JSON, reason="CONCENTRATION releases not built in this checkout")
def test_concentration_arms_pass_every_must_gate_on_reread():
    bridge = ROOT / "data" / "bridge"
    if not (bridge / "sample_submission.tif").is_file():
        pytest.skip("pinned bridge inputs not restored")
    with rasterio.open(bridge / "sample_submission.tif") as ds:
        ref = (ds.shape, str(ds.crs), ds.transform)
        foot = np.isfinite(ds.read(1))
    with rasterio.open(bridge / "existing_faults.tif") as ds:
        catalogue = (ds.read(1) > 0) & foot
    d_cat = distance_transform_edt(~catalogue)

    seen_shas: set[str] = set()
    for path in CRES_JSON:
        rec = json.loads(path.read_text())
        assert rec["parent"] == ccv.R1_ID
        assert rec["parent_sha256_nan"] == ccv.R1_SHA_NAN
        assert rec["axis"] == "CONCENTRATION" and rec["value"] in OUR_VALUES
        exp_pct = 100.0 * rec["parent_diff"]["n_removed"] / ccv.N_PARENT_DOTS
        assert rec["parent_diff"]["pct_changed_moved"] == pytest.approx(exp_pct, abs=0.01)
        assert 1.0 <= rec["parent_diff"]["pct_changed_moved"] <= 50.0
        assert rec["parent_diff"]["n_added"] == rec["parent_diff"]["n_removed"]
        assert rec["n_dots"] == ccv.N_DOTS
        assert len(rec["form_note"]) <= 140
        assert rec["gates"]["reread_from_disk_verified"] is True
        assert rec["gates"]["zero_catalogue_mass"] is True

        tif = RELEASES / f"{rec['id']}.tif"
        zeros = RELEASES / f"{rec['id']}-zeros.tif"
        assert _sha256(tif) == rec["sha256"]
        assert _sha256(zeros) == rec["sha256_zeros"]
        assert rec["sha256"] not in seen_shas and rec["sha256_zeros"] not in seen_shas
        seen_shas.update({rec["sha256"], rec["sha256_zeros"]})

        with rasterio.open(tif) as ds:
            assert (ds.shape, str(ds.crs), ds.transform) == ref
            assert ds.count == 1 and ds.dtypes[0] == "float32"
            arr = ds.read(1)
        assert float(d_cat[arr > 0.5].min()) > ccv.MIN_CATALOGUE_PX
        assert int((arr[catalogue] > 0).sum()) == 0
        assert int((arr[foot] > 0.5).sum()) == ccv.N_DOTS
        assert np.isfinite(arr[foot]).all() and np.isnan(arr[~foot]).all()

        with rasterio.open(zeros) as ds:
            z = ds.read(1)
        assert np.isfinite(z).all() and float(z[~foot].max()) == 0.0
        assert np.array_equal(z[foot] > 0.5, arr[foot] > 0.5)


@pytest.mark.skipif(not CRES_JSON, reason="CONCENTRATION releases not built in this checkout")
def test_ledger_cards_and_report_agree_with_the_receipts():
    rows = [r for r in csv.DictReader(LEDGER.open())
            if r["parent"] == ccv.R1_ID and r["axis"] == "CONCENTRATION"]
    assert len(rows) == len(OUR_VALUES) == 3
    assert {r["value"] for r in rows} == OUR_VALUES
    cards = json.loads(CARDS.read_text())
    report = json.loads(REPORT.read_text()) if REPORT.is_file() else {"arms": {}}
    for row in rows:
        assert row["status"] == "BUILT"
        assert row["receipt_score"] == "" and row["receipt_date"] == ""
        assert row["predicted_change"] == f"MODEL:{ccv.PREDICTIONS[row['value']][0]}"
        assert row["predicted_range"] == ccv.PREDICTIONS[row["value"]][1]
        assert row["n_dots"] == str(ccv.N_DOTS)
        rec = json.loads((RELEASES / f"{row['id']}.json").read_text())
        assert rec["sha256"] == row["sha256"]
        assert rec["sha256_zeros"] == row["sha256_zeros"]
        card = cards[row["id"]]
        for field in ("hypothesis", "mechanism", "non_fault_mimic",
                      "predicted_sign_and_size", "falsifier", "confounder"):
            assert card[field]
        if row["id"] in report["arms"]:
            arm = report["arms"][row["id"]]
            assert arm["sgmc_control"]["evidence_label"] == "PROXY"
            assert "sgmc_delta_vs_R1_PROXY" in arm
            assert arm["holdout_note"]
    # no duplicate (parent, axis, value) anywhere in the ledger
    triples = [(r["parent"], r["axis"], r["value"]) for r in csv.DictReader(LEDGER.open())]
    assert len(triples) == len(set(triples))
