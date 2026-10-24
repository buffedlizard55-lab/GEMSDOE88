"""Tests for AXIS=SNAP scarp transplant on the gate-clean parent R1 (PRUNEp3px).

Three layers:

* Unit tests on a synthetic grid for the reused allocator
  :func:`build_snap_variants.snap_dots_within_window` under R1 conditions (every
  dot eligible, no frozen collar) and for
  :func:`build_snap_r1_scarp_variants.moved_dot_spacing_invariant`.
* Static tests over tracked artifacts (preregistration, ledger, mechanism cards,
  axis report) that run in CI without the gitignored rasters.
* Artifact tests that re-read the released GeoTIFFs from disk and re-derive every
  MUST gate; they skip when ``releases/`` lacks the family's TIFFs (competition
  rasters are gitignored; regenerate with
  ``python3 scripts/build_snap_r1_scarp_variants.py``).
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
import build_snap_r1_scarp_variants as bsr  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_snap_r1_scarp.json"
REPORT = ROOT / "evidence" / "snap_r1_scarp_axis_report.json"

R1_ID = bsr.R1_ID
OWN_VALUES = set(bsr.OWN_VALUES)

FAMILY_JSON = [
    p for p in sorted(RELEASES.glob(f"{R1_ID}-SNAP*.json"))
    if p.with_suffix("").with_suffix(".tif").is_file()
    and json.loads(p.read_text()).get("value") in OWN_VALUES
]


def _ledger_rows():
    with LEDGER.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _family_rows():
    return [
        r for r in _ledger_rows()
        if r["axis"] == "SNAP" and r["parent"] == R1_ID and r["value"] in OWN_VALUES
    ]


# ---------------------------------------------------------------------------
# Unit tests: allocator behaviour under R1 conditions on a synthetic grid
# ---------------------------------------------------------------------------


def _synthetic(size: int = 40):
    """No dot inside 3 px of the catalogue: every dot is eligible, R1-style."""
    foot = np.ones((size, size), dtype=bool)
    foot[0, :] = False
    catalogue = np.zeros((size, size), dtype=bool)
    catalogue[3, 3] = True
    d_cat = distance_transform_edt(~catalogue)
    mask = np.zeros((size, size), dtype=bool)
    mask[20, 20] = True
    mask[20, 21] = True  # inherited dense pair, 1 px apart (R1 refill geometry)
    mask[30, 30] = True
    h19_5 = np.zeros((size, size), dtype=bool)
    h19_5[20, 18:22] = True
    h19_5[30, 28:32] = True
    field = np.zeros((size, size), dtype=np.float32)
    field[20, 18] = 1.0   # strongest local edge, 2 px left of (20, 20), on support
    field[20, 24] = 0.9   # strong edge OFF support, 2 px right (needs d=... 3 px: unreachable at max_r=2)
    field[20, 23] = 0.8   # reachable off-support edge for (20, 21) at d=2
    field[30, 29] = 0.5
    return foot, mask, catalogue, d_cat, h19_5, field


def test_r1_style_snap_holds_count_and_strict_collar():
    foot, mask, catalogue, d_cat, h19_5, field = _synthetic()
    moved, stats = bsnap.snap_dots_within_window(
        r0_mask=mask, score_field=field, foot=foot, catalogue=catalogue,
        d_cat=d_cat, h19_5=h19_5, max_r=2.0, min_sep=2.8, stay_on_h19=False,
    )
    assert int(moved.sum()) == int(mask.sum())
    assert not moved[catalogue].any()
    assert float(d_cat[moved].min()) > 3.0
    assert stats["max_displacement_px"] <= 2.0 + 1e-9


def test_every_moved_dot_is_spacing_locked_in_the_final_configuration():
    foot, mask, catalogue, d_cat, h19_5, field = _synthetic()
    moved, _ = bsnap.snap_dots_within_window(
        r0_mask=mask, score_field=field, foot=foot, catalogue=catalogue,
        d_cat=d_cat, h19_5=h19_5, max_r=2.0, min_sep=2.8, stay_on_h19=False,
    )
    inv = bsr.moved_dot_spacing_invariant(mask, moved)
    assert inv["n_added_cells"] >= 1
    assert inv["spacing_lock_holds_for_every_moved_dot"]
    assert inv["min_nn_added_vs_all_px"] >= 2.8284 - 1e-9


def test_inherited_dense_pairs_are_reported_not_silently_repaired():
    """A parent pair 1 px apart that the snap does not touch stays 1 px apart."""
    size = 40
    foot = np.ones((size, size), dtype=bool)
    catalogue = np.zeros((size, size), dtype=bool)
    catalogue[3, 3] = True
    d_cat = distance_transform_edt(~catalogue)
    mask = np.zeros((size, size), dtype=bool)
    mask[20, 20] = True
    mask[20, 21] = True
    h19_5 = mask.copy()
    field = np.zeros((size, size), dtype=np.float32)  # flat: no dot can improve
    moved, stats = bsnap.snap_dots_within_window(
        r0_mask=mask, score_field=field, foot=foot, catalogue=catalogue,
        d_cat=d_cat, h19_5=h19_5, max_r=2.0, min_sep=2.8, stay_on_h19=False,
    )
    assert stats["n_dots_displaced"] == 0
    assert np.array_equal(moved, mask)
    inv = bsr.moved_dot_spacing_invariant(mask, moved)
    assert inv["n_added_cells"] == 0
    assert inv["spacing_lock_holds_for_every_moved_dot"]  # vacuous, nothing moved
    assert inv["min_nn_global_px"] == 1.0  # inherited geometry reported honestly


def test_stay_on_h19_locks_targets_to_parent_support():
    foot, mask, catalogue, d_cat, h19_5, field = _synthetic()
    moved, stats = bsnap.snap_dots_within_window(
        r0_mask=mask, score_field=field, foot=foot, catalogue=catalogue,
        d_cat=d_cat, h19_5=h19_5, max_r=2.0, min_sep=2.8, stay_on_h19=True,
    )
    assert stats["stay_on_h19_5_ridge"] is True
    assert not (moved & ~h19_5).any()


def test_window_one_cannot_reach_two_pixels_and_is_deterministic():
    foot, mask, catalogue, d_cat, h19_5, field = _synthetic()
    a, sa = bsnap.snap_dots_within_window(
        r0_mask=mask, score_field=field, foot=foot, catalogue=catalogue,
        d_cat=d_cat, h19_5=h19_5, max_r=1.0, min_sep=2.8, stay_on_h19=False,
    )
    b, sb = bsnap.snap_dots_within_window(
        r0_mask=mask, score_field=field, foot=foot, catalogue=catalogue,
        d_cat=d_cat, h19_5=h19_5, max_r=1.0, min_sep=2.8, stay_on_h19=False,
    )
    assert np.array_equal(a, b) and sa == sb
    assert sa["max_displacement_px"] <= 1.0 + 1e-9
    assert sa["displacement_counts_by_d2"].get("d_2px_d2_4", 0) == 0


# ---------------------------------------------------------------------------
# Static tests over tracked artifacts (CI-safe: no rasters needed)
# ---------------------------------------------------------------------------


def test_preregistration_matches_ledger_predictions():
    prereg = json.loads(PREREG.read_text())
    assert prereg["axis"] == "SNAP"
    assert prereg["parent_chain"]["r1"]["id"] == R1_ID
    arms = {a["value"]: a for a in prereg["arms"]}
    assert set(arms) == OWN_VALUES
    rows = {r["value"]: r for r in _family_rows()}
    assert set(rows) == OWN_VALUES, "builder must add exactly the three preregistered arms"
    for value, arm in arms.items():
        assert rows[value]["predicted_change"] == arm["predicted_change"]
        assert rows[value]["predicted_range"] == arm["predicted_range"]
        assert rows[value]["status"] == "BUILT"
        assert rows[value]["receipt_score"] == "" and rows[value]["receipt_date"] == ""
    for rule in prereg["decision_rules_preregistered_before_proxies"]:
        assert "SGMC" in rule or "receipt" in rule.lower()


def test_ledger_wide_uniqueness_survives_the_new_family():
    rows = _ledger_rows()
    pairs = [(r["parent"], r["axis"], r["value"]) for r in rows]
    assert len(pairs) == len(set(pairs)), "(parent, axis, value) must be unique"
    shas = [r["sha256"] for r in rows if r["sha256"]] + [r["sha256_zeros"] for r in rows if r["sha256_zeros"] and r["sha256_zeros"] != r["sha256"]]  # single-file de-novo rows: sha256_zeros == sha256 (no distinct NaN twin), count once
    assert len(shas) == len(set(shas)), "every primary/fallback hash must be unique"


def test_mechanism_cards_present_for_family():
    cards = json.loads(CARDS.read_text())
    rows = _family_rows()
    assert len(rows) == 3
    for r in rows:
        card = cards[r["id"]]
        for key in ("hypothesis", "mechanism", "non_fault_mimic",
                    "predicted_sign_size", "falsifier"):
            assert len(card[key].strip()) > 20, f"{r['id']} card missing {key}"


def test_axis_report_records_provided_bands_policy_and_r0_reproduction():
    report = json.loads(REPORT.read_text())
    assert report["axis"] == "SNAP"
    assert report["provided_bands_only"] is True
    assert report["external_lidar_used"] is False
    assert report["leakage_canaries"]["passed"] is True
    assert report["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    repro = report["r0_scarp2px_reproduction"]
    assert repro["rebuilt_n_dots_displaced"] == repro["published_n_dots_displaced"]
    assert abs(repro["rebuilt_sgmc"] - repro["published_sgmc"]) <= 1e-6
    assert len(report["variants"]) == 3


# ---------------------------------------------------------------------------
# Artifact tests: re-derive every MUST gate from the bytes on disk
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not FAMILY_JSON, reason="scarp transplant releases not built in this checkout")
def test_family_passes_every_must_gate_on_reread():
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        ref = (ds.shape, str(ds.crs), tuple(ds.transform)[:6], ds.count, ds.dtypes[0])
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        catalogue = (ds.read(1) > 0) & foot
    d_cat = distance_transform_edt(~catalogue)

    assert len(FAMILY_JSON) == 3
    shas = set()
    for path in FAMILY_JSON:
        rec = json.loads(path.read_text())
        assert rec["parent"] == R1_ID
        assert rec["axis"] == "SNAP"
        assert rec["value"] in OWN_VALUES
        assert rec["n_dots"] == 37_654
        assert len(rec["form_note"]) <= 140
        # SNAP is exempt from the 1-50% rule, but the exact percentage is recorded.
        assert rec["parent_diff"]["n_added"] == rec["parent_diff"]["n_removed"] > 0
        assert rec["parent_diff"]["pct_changed_moved"] > 0.0

        with rasterio.open(RELEASES / f"{rec['id']}.tif") as ds:
            arr = ds.read(1)
            assert (ds.shape, str(ds.crs), tuple(ds.transform)[:6], ds.count, ds.dtypes[0]) == ref
        mask = arr > 0.5
        assert int(mask.sum()) == 37_654, "SNAP must not change mass"
        assert int((arr[catalogue] > 0).sum()) == 0
        # Gate-clean WITHOUT waiver: every dot, not only the added ones, > 3 px.
        assert float(d_cat[mask].min()) > 3.0
        assert np.isfinite(arr[foot]).all() and np.isnan(arr[~foot]).all()
        assert 0.0 <= float(arr[foot].min()) and float(arr[foot].max()) <= 1.0

        with rasterio.open(RELEASES / f"{rec['id']}-zeros.tif") as ds:
            zeros = ds.read(1)
        assert np.isfinite(zeros).all()
        assert (zeros[~foot] == 0.0).all()
        assert np.array_equal(zeros > 0.5, mask)

        inv = rec["spacing_lock_final_configuration"]
        assert inv["spacing_lock_holds_for_every_moved_dot"] is True
        disp = rec["displacement"]
        assert disp["max_displacement_px"] <= disp["max_window_radius_px"] + 1e-9
        assert disp["mean_edge_response_after"] > disp["mean_edge_response_before"]
        diag = rec["report_only_diagnostics"]
        assert diag["sgmc_control"]["evidence_label"] == "PROXY"
        assert diag["holdout_proxy"]["evidence_label"] == "PROXY"
        # Triangle inequality (IR-88-20): an all-dots->3px file cannot score a
        # catalogue hide-and-recover holdout.
        assert diag["holdout_proxy"]["dti"] == 0.0
        assert rec["w_weighted_dti_MODEL"]["evidence_label"] == "MODEL"
        assert "receipt_score" not in diag
        shas.update({rec["sha256"], rec["sha256_zeros"]})
    assert len(shas) == 6, "the three variants must be distinct raster pairs"


@pytest.mark.skipif(not FAMILY_JSON, reason="scarp transplant releases not built in this checkout")
def test_support_lock_arm_never_leaves_h19_5():
    for path in FAMILY_JSON:
        rec = json.loads(path.read_text())
        off = rec["off_h19_5_support"]
        if rec["value"] == "ridge2px":
            assert off["stay_on_h19_5"] is True
            assert off["n_dots_off_h19_5_after"] == 0
        else:
            assert off["stay_on_h19_5"] is False
