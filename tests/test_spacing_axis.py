"""Tests for AXIS=SPACING (parent R1 = PRUNEp3px): shared-decluster receiver geometry.

Two layers, mirroring tests/test_relief_bracket_axis.py:

* Unit tests on a synthetic grid for ``greedy_declutter`` / ``lattice_distance``
  / ``poisson_farthest_point`` / ``ranked_greedy_pick`` / ``h19_strike_field`` /
  ``strike_alignment`` - decluster minimality, survivor spacing, lattice phase,
  farthest-point ordering, exclusion handling and determinism are properties of
  the algorithm, not of the shipped files.
* Artifact tests that re-read the three releases from disk and re-derive the
  MUST gates (format, zero catalogue mass, >3 px collar, fixed 37,654 count,
  5.08% parent diff vs R1, preregistered predictions, ledger + cards).

Artifact tests skip when the gitignored rasters are absent (fresh clone):
regenerate with ``python scripts/build_spacing_variants.py`` after restoring
the pinned inputs. PROXY values are asserted to be *reported*, never gated.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_spacing_variants as spv  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
REPORT = ROOT / "evidence" / "spacing_axis_report.json"
PREREG = ROOT / "registry" / "spacing_preregistration.json"

PREREG_PRED = {
    "poisson28": "MODEL:+0.003",
    "lattice4px": "MODEL:-0.004",
    "strike": "MODEL:+0.000",
}
SPACING_JSON = [
    p for v in spv.OUR_VALUES
    for p in sorted(RELEASES.glob(f"{spv.R1_ID}-SPACING{v}-*.json"))
    if (RELEASES / f"{p.stem}.tif").is_file()
]


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def _toy_parent():
    rng = np.random.default_rng(7)
    mask = np.zeros((40, 40), dtype=bool)
    # regular 4 px grid plus a tight cluster block to decluster
    mask[4:36:4, 4:36:4] = True
    mask[18:21, 18:21] = True  # 3x3 block: NN 1.0 everywhere inside
    mask |= rng.random((40, 40)) < 0.002
    return mask


def test_greedy_declutter_restores_spacing_and_is_minimal():
    parent = _toy_parent()
    donors, surv = spv.greedy_declutter(parent)
    assert donors.sum() > 0
    assert int(surv.sum()) + int(donors.sum()) == int(parent.sum())
    assert not (surv & donors).any()
    pts = np.column_stack(np.nonzero(surv)).astype(np.float64)
    assert float(cKDTree(pts).query(pts, k=2)[0][:, 1].min()) >= 2.8
    # every donor was clustered in the parent (NN < 2.8); greedy-time justification.
    # (Post-hoc, chain removals A->B->C can leave a donor >=2.8 px from the final
    # survivors; the builder reports that donor->survivor distribution exactly.)
    parent_pts = np.column_stack(np.nonzero(parent)).astype(np.float64)
    parent_nn = cKDTree(parent_pts).query(parent_pts, k=2)[0][:, 1]
    idx_of = {tuple(p): i for i, p in enumerate(parent_pts.astype(int).tolist())}
    for y, x in np.column_stack(np.nonzero(donors)).tolist():
        assert parent_nn[idx_of[(y, x)]] < 2.8


def test_greedy_declutter_is_deterministic_and_keeps_spaced_sets():
    parent = _toy_parent()
    a_d, a_s = spv.greedy_declutter(parent)
    b_d, b_s = spv.greedy_declutter(parent)
    assert np.array_equal(a_d, b_d) and np.array_equal(a_s, b_s)
    spaced = np.zeros((40, 40), dtype=bool)
    spaced[4:36:4, 4:36:4] = True
    d2, s2 = spv.greedy_declutter(spaced)
    assert int(d2.sum()) == 0 and np.array_equal(s2, spaced)


def test_lattice_distance_phase_and_period():
    y = np.array([0, 0, 2, 4, 5, 7], dtype=np.int64)
    x = np.array([0, 1, 2, 4, 5, 7], dtype=np.int64)
    d = spv.lattice_distance(y, x, period=4)
    assert d[0] == pytest.approx(0.0) and d[3] == pytest.approx(0.0)
    assert d[1] == pytest.approx(1.0)
    assert d[2] == pytest.approx(np.sqrt(8.0))  # farthest point of a 4px cell
    assert d[4] == pytest.approx(np.sqrt(2.0))
    assert d[5] == pytest.approx(np.sqrt(2.0))  # wraps: (7,7) is 1px off node (8,8)


def test_poisson_farthest_point_orders_by_distance_and_tie_breaks_on_index():
    # candidates on a line; survivors at 0 -> farthest first, ties -> low index
    cy = np.zeros(6, dtype=np.int64)
    cx = np.array([1, 5, 9, 9, 3, 7], dtype=np.int64)
    d0 = np.array([1.0, 5.0, 9.0, 9.0, 3.0, 7.0])
    picks = spv.poisson_farthest_point(cy, cx, d0, 3)
    assert picks[0] == 2  # first of the tied farthest pair (index tie-break)
    assert len(set(picks)) == 3
    again = spv.poisson_farthest_point(cy, cx, d0, 3)
    assert picks == again
    with pytest.raises(ValueError):
        spv.poisson_farthest_point(cy, cx, d0, 7)


def test_ranked_greedy_pick_honours_order_and_exclusion():
    cy = np.array([5, 5, 5, 20], dtype=np.int64)
    cx = np.array([5, 6, 8, 20], dtype=np.int64)
    order = np.array([0, 1, 2, 3])  # preference order
    picks = spv.ranked_greedy_pick(order, cy, cx, (40, 40), 3, exclusion_px=1.5)
    assert picks[0] == 0
    assert 1 not in picks  # adjacent to pick 0 -> excluded
    assert picks == [0, 2, 3]
    with pytest.raises(ValueError):
        spv.ranked_greedy_pick(order, cy, cx, (40, 40), 4, exclusion_px=1.5)


def test_strike_field_and_alignment_on_a_vertical_ridge():
    h19 = np.zeros((40, 40), dtype=bool)
    h19[5:35, 19:21] = True  # vertical strand: strike ~ north-south
    angle, coh = spv.h19_strike_field(h19)
    assert float(np.median(coh[h19])) > 0.5
    surv_y = np.array([20])
    surv_x = np.array([19])
    tree = cKDTree(np.column_stack([[20.0], [19.0]]))
    # candidate due north of survivor (along strike) vs due east (across)
    along = spv.strike_alignment(np.array([15]), np.array([19]), angle, tree, surv_y, surv_x)
    across = spv.strike_alignment(np.array([20]), np.array([24]), angle, tree, surv_y, surv_x)
    assert float(along[0]) > 0.9
    assert float(across[0]) < 0.5


def test_preregistration_matches_builder_variants_and_predictions():
    prereg = json.loads(PREREG.read_text())
    assert prereg["written_before_variant_proxy_evaluation"] is True
    fixed = {v["value"]: v for v in prereg["variants_fixed_before_any_proxy"]}
    assert set(fixed) == set(spv.OUR_VALUES) == {v for v, _p, _r in spv.VARIANTS}
    for value, pred, pred_range in spv.VARIANTS:
        assert fixed[value]["predicted_change_vs_parent_R1_live"] == f"MODEL:{pred}"
        assert fixed[value]["predicted_range_vs_parent_R1_live"] == pred_range
    assert prereg["parent"]["sha256_nan"] == spv.R1_SHA_NAN
    assert prereg["parent"]["sha256_zeros"] == spv.R1_SHA_ZEROS
    assert prereg["dose"]["n_donors_receivers"].startswith("1,914")


# ---------------------------------------------------------------------------
# Artifact tests (skip without locally built rasters)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not SPACING_JSON, reason="SPACING releases not built in this checkout")
def test_spacing_variants_pass_every_must_gate_on_reread():
    report = json.loads(REPORT.read_text())
    variants = {v["value"]: v for v in report["variants"]}
    assert set(variants) == set(spv.OUR_VALUES)
    assert report["n_shift"] == spv.N_DONORS_PINNED == 1914
    bridge = ROOT / "data" / "bridge"
    if not (bridge / "sample_submission.tif").is_file():
        pytest.skip("pinned bridge inputs not restored")
    with rasterio.open(bridge / "sample_submission.tif") as ds:
        tmpl = (ds.shape, ds.crs, ds.transform)
        foot = np.isfinite(ds.read(1))
    with rasterio.open(bridge / "existing_faults.tif") as ds:
        catalogue = (ds.read(1) > 0) & foot
    d_cat = distance_transform_edt(~catalogue)

    for value, rec in variants.items():
        assert rec["parent"] == spv.R1_ID and rec["n_dots"] == 37_654
        assert rec["parent_diff"]["n_added"] == rec["parent_diff"]["n_removed"] == 1914
        assert rec["parent_diff"]["pct_changed_moved"] == pytest.approx(5.08, abs=0.01)
        assert 1.0 <= rec["parent_diff"]["pct_changed_moved"] <= 50.0
        assert rec["parent_diff"]["dots_le_3px"] == 0
        assert rec["parent_diff"]["min_dist_catalogue_px"] > 3.0
        assert len(rec["form_note"]) <= 140

        p_nan, p_zeros = ROOT / rec["file_nan"], ROOT / rec["file_zeros"]
        receipt = json.loads((RELEASES / f"{rec['id']}.json").read_text())
        assert receipt["sha256"] == rec["sha256"] == _sha256(p_nan)
        assert receipt["sha256_zeros"] == rec["sha256_zeros"] == _sha256(p_zeros)
        for tif_p, zip_key in ((p_nan, "zip_nan"), (p_zeros, "zip_zeros")):
            with zipfile.ZipFile(ROOT / rec[zip_key]) as zf:
                names = zf.namelist()
            assert names == [tif_p.name]

        with rasterio.open(p_nan) as dn, rasterio.open(p_zeros) as dz:
            assert (dn.shape, dn.crs, dn.transform) == tmpl == (dz.shape, dz.crs, dz.transform)
            assert dn.count == dz.count == 1 and dn.dtypes[0] == dz.dtypes[0] == "float32"
            assert str(dn.crs) == "EPSG:32611"
            arr_n, arr_z = dn.read(1), dz.read(1)
        assert np.isfinite(arr_n[foot]).all() and np.isnan(arr_n[~foot]).all()
        assert np.isfinite(arr_z).all() and (arr_z[~foot] == 0.0).all()
        assert np.array_equal(arr_n[foot], arr_z[foot])
        assert 0.0 <= float(arr_n[foot].min()) and float(arr_n[foot].max()) <= 1.0
        mask = arr_z > 0.5
        assert int(mask.sum()) == 37_654
        assert int((mask & catalogue).sum()) == 0
        assert float(d_cat[mask].min()) > 3.0


@pytest.mark.skipif(not SPACING_JSON, reason="SPACING releases not built in this checkout")
def test_spacing_receiver_sets_differ_only_by_geometry():
    report = json.loads(REPORT.read_text())
    for pair, overlap in report["receiver_overlap"].items():
        # three genuinely different receiver geometries sharing one donor set
        assert overlap < report["n_shift"] // 2, pair
    stats = {v["value"]: v["spacing_statistics"] for v in report["variants"]}
    # each arm wins its own geometric criterion (clean experimental separation)
    assert stats["poisson28"]["receiver_dist_to_survivor_px"]["median"] > \
        stats["lattice4px"]["receiver_dist_to_survivor_px"]["median"]
    assert stats["poisson28"]["receiver_dist_to_survivor_px"]["median"] > \
        stats["strike"]["receiver_dist_to_survivor_px"]["median"]
    assert stats["lattice4px"]["receiver_lattice_dist_px"]["median"] < \
        stats["poisson28"]["receiver_lattice_dist_px"]["median"]
    assert stats["strike"]["receiver_strike_align"]["median"] > \
        stats["poisson28"]["receiver_strike_align"]["median"]
    for v in report["variants"]:
        assert v["spacing_statistics"]["n_donors"] == v["spacing_statistics"]["n_receivers"] == 1914


@pytest.mark.skipif(not SPACING_JSON, reason="SPACING releases not built in this checkout")
def test_spacing_ledger_cards_and_hash_uniqueness():
    with LEDGER.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    all_hashes = [h for r in rows for h in (r["sha256"], r["sha256_zeros"]) if h]
    assert len(all_hashes) == len(set(all_hashes)), "duplicate SHA-256 in ledger"
    pairs = [(r["parent"], r["axis"], r["value"]) for r in rows]
    assert len(pairs) == len(set(pairs)), "repeated (parent, axis, value) pair"

    cards = json.loads(CARDS.read_text())
    spacing_rows = {r["value"]: r for r in rows if r["axis"] == "SPACING"}
    assert set(spacing_rows) == set(spv.OUR_VALUES)
    for value, row in spacing_rows.items():
        assert row["parent"] == spv.R1_ID
        assert row["status"] == "BUILT" and row["n_dots"] == "37654"
        assert row["predicted_change"] == PREREG_PRED[value] and not row["receipt_score"]
        card = cards[row["id"]]
        for field in ("hypothesis", "mechanism", "non_fault_mimic",
                      "predicted_sign_size", "falsifier", "post_build_report_only"):
            assert card.get(field)
        assert "MODEL" in card["predicted_sign_size"]
        assert card["references"] and all(r["url"].startswith("https://") for r in card["references"])


@pytest.mark.skipif(not SPACING_JSON, reason="SPACING releases not built in this checkout")
def test_spacing_proxies_are_reported_not_gated():
    report = json.loads(REPORT.read_text())
    r1_sgmc = report["parent_R1"]["diagnostics"]["sgmc_control"]["dti"]
    assert r1_sgmc == pytest.approx(0.096083, abs=1e-6)
    assert report["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    assert set(report["leakage_canaries"]["spacing_geometry"]) == {
        "spacing_survivor_distance", "spacing_lattice_distance", "spacing_strike_alignment"}
    for v in report["variants"]:
        d = v["report_only_diagnostics"]
        # Hide-and-recover is degenerate by construction for >3 px files (IR-88-20),
        # and every MUST gate still passes: the proxy cannot fail a variant.
        assert d["holdout_proxy"]["dti"] == 0.0
        assert d["holdout_proxy"]["evidence_label"] == "PROXY"
        assert d["sgmc_control"]["evidence_label"] == "PROXY"
        assert d["sgmc_delta_vs_R1_PROXY"] == pytest.approx(
            d["sgmc_control"]["dti"] - r1_sgmc, abs=1e-6)
        assert all(v["gates"].values())
