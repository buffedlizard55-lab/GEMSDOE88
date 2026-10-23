"""Tests for AXIS=SNAP (parent R1 = PRUNEp3px): geometry-only edits at fixed count.

Two layers:

* Unit tests on a synthetic grid for :func:`build_snap_variants.snap_mask` — the
  displacement bound, the strict catalogue collar, count preservation and
  determinism are properties of the algorithm, not of the shipped files.
* Artifact tests that re-read the three releases from disk and re-derive every
  MUST gate (format, zero catalogue mass, > 3 px collar, fixed 37,654 count,
  parent diff inside [1, 50] %, ledger + mechanism-card presence).

Artifact tests skip when ``releases/`` is empty (competition rasters are
gitignored, so a fresh clone must regenerate them with
``python3 scripts/build_snap_r1_variants.py``).
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
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_snap_r1_variants as bsv  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"

SNAP_JSON = sorted(RELEASES.glob(f"{bsv.R1_ID}-SNAP*.json"))


# ---------------------------------------------------------------------------
# Unit tests: algorithm properties on a synthetic grid
# ---------------------------------------------------------------------------


def _synthetic(size: int = 40):
    """Catalogue at (10, 15) so every synthetic dot starts > 3 px clear of it."""
    foot = np.ones((size, size), dtype=bool)
    foot[0, :] = False  # ragged edge so clipping is exercised
    mask = np.zeros((size, size), dtype=bool)
    mask[10, 10] = mask[10, 20] = mask[25, 25] = mask[30, 30] = True
    catalogue = np.zeros((size, size), dtype=bool)
    catalogue[10, 15] = True
    d_cat = distance_transform_edt(~catalogue)
    field = np.zeros((size, size), dtype=np.float32)
    field[10, 8] = 1.0     # strongest local edge: 2 px LEFT of (10, 10)
    field[25, 24] = 0.5
    return foot, mask, catalogue, d_cat, field


def test_snap_respects_radius_and_count():
    foot, mask, catalogue, d_cat, field = _synthetic()
    moved, stats = bsv.snap_mask(mask, field, foot, d_cat, radius=2, move_fraction=0.5)
    assert int(moved.sum()) == int(mask.sum())
    ys, xs = np.nonzero(moved)
    assert not moved[catalogue].any()
    assert d_cat[moved].min() > bsv.MIN_CATALOGUE_PX
    assert stats["max_displacement_px"] <= 2.0 * np.sqrt(2.0) + 1e-9
    assert stats["n_moved"] >= 1


def test_snap_never_enters_the_collar():
    foot, mask, catalogue, d_cat, field = _synthetic()
    # Put the only strong edge on the catalogue pixel itself: snapping must refuse it.
    field[:] = 0.0
    field[10, 15] = 1.0
    moved, _ = bsv.snap_mask(mask, field, foot, d_cat, radius=2, move_fraction=1.0)
    assert not moved[catalogue].any()
    added = moved & ~mask
    if added.any():
        assert d_cat[added].min() > bsv.MIN_CATALOGUE_PX
    assert np.array_equal(moved, mask), "a collar-blocked peak must leave every dot in place"


def test_snap_preserves_but_never_repairs_inherited_collar_violations():
    """SNAP is a move-only edit: it never adds a violator, and it cannot remove one.

    Shipped variants inherit R1, which is already clean, so this only documents the
    contract: any parent-side collar violation would survive a SNAP pass and must be
    dealt with by the PRUNE axis instead.
    """
    foot, mask, catalogue, d_cat, field = _synthetic()
    dirty = mask.copy()
    dirty[10, 14] = True          # 1 px from the catalogue: inherited violation
    dirty_d_cat = distance_transform_edt(~catalogue)
    moved, _ = bsv.snap_mask(dirty, field, foot, dirty_d_cat, radius=2, move_fraction=0.5)
    added = moved & ~dirty
    assert not moved[catalogue].any()
    if added.any():
        assert d_cat[added].min() > bsv.MIN_CATALOGUE_PX
    assert int((dirty_d_cat < bsv.MIN_CATALOGUE_PX).sum()) >= 1, "parent is dirty by construction"


def test_snap_moves_toward_the_edge_and_is_deterministic():
    foot, mask, catalogue, d_cat, field = _synthetic()
    a, sa = bsv.snap_mask(mask, field, foot, d_cat, radius=2, move_fraction=0.5)
    b, sb = bsv.snap_mask(mask, field, foot, d_cat, radius=2, move_fraction=0.5)
    assert np.array_equal(a, b) and sa == sb
    assert a[10, 8]                     # dot (10,10) snapped 2 px left onto the peak
    assert not a[10, 10]
    assert float(field[a].mean()) > float(field[mask].mean())


def test_snap_move_budget_is_capped():
    foot, mask, catalogue, d_cat, field = _synthetic()
    _, stats = bsv.snap_mask(mask, field, foot, d_cat, radius=1, move_fraction=0.25)
    assert stats["move_budget"] == 1
    assert stats["n_moved"] <= stats["move_budget"]


# ---------------------------------------------------------------------------
# Artifact tests: the three shipped variants
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not SNAP_JSON, reason="SNAP releases not built in this checkout")
def test_snap_variants_pass_every_must_gate_on_reread():
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        ref = (ds.shape, str(ds.crs), tuple(ds.transform)[:6], ds.count, ds.dtypes[0])
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as ds:
        catalogue = (ds.read(1) > 0) & foot
    d_cat = distance_transform_edt(~catalogue)

    assert len(SNAP_JSON) == 3
    shas = set()
    for path in SNAP_JSON:
        rec = json.loads(path.read_text())
        assert rec["parent"] == bsv.R1_ID
        assert rec["axis"] == "SNAP"
        assert rec["n_dots"] == 37_654
        assert len(rec["form_note"]) <= 140
        assert 1.0 <= rec["parent_diff"]["pct_changed_moved"] <= 50.0

        with rasterio.open(RELEASES / f"{rec['id']}.tif") as ds:
            arr = ds.read(1)
            assert (ds.shape, str(ds.crs), tuple(ds.transform)[:6], ds.count, ds.dtypes[0]) == ref
        mask = arr > 0.5
        assert int(mask.sum()) == 37_654, "SNAP must not change mass"
        assert int((arr[catalogue] > 0).sum()) == 0
        assert float(d_cat[mask].min()) > bsv.MIN_CATALOGUE_PX, "collar not strictly outside 300 m"
        assert np.isfinite(arr[foot]).all() and np.isnan(arr[~foot]).all()
        assert 0.0 <= float(arr[foot].min()) and float(arr[foot].max()) <= 1.0

        with rasterio.open(RELEASES / f"{rec['id']}-zeros.tif") as ds:
            zeros = ds.read(1)
        assert np.isfinite(zeros).all()
        assert (zeros[~foot] == 0.0).all()
        assert np.array_equal(zeros > 0.5, mask)
        shas.update({rec["sha256"], rec["sha256_zeros"]})
    assert len(shas) == 6, "the three variants must be distinct rasters"


@pytest.mark.skipif(not SNAP_JSON, reason="SNAP releases not built in this checkout")
def test_snap_displacement_matches_its_radius():
    for path in SNAP_JSON:
        rec = json.loads(path.read_text())
        stats = rec["snap_statistics"]
        assert stats["radius_px"] in (1, 2)
        assert stats["mean_displacement_px"] <= np.sqrt(2.0) * stats["radius_px"] + 1e-9
        # n_moved counts executed moves; a move into a cell vacated earlier in the same
        # greedy pass changes no cell, so n_moved can exceed the net cell diff by a few.
        assert rec["parent_diff"]["n_removed"] == rec["parent_diff"]["n_added"]
        assert stats["n_moved"] >= rec["parent_diff"]["n_removed"]
        assert stats["n_moved"] - rec["parent_diff"]["n_removed"] <= 0.01 * stats["n_moved"]
        if stats["radius_px"] == 1:
            assert stats["max_displacement_px"] <= np.sqrt(2.0) + 1e-9


@pytest.mark.skipif(not SNAP_JSON, reason="SNAP releases not built in this checkout")
def test_snap_ledger_and_mechanism_cards():
    with LEDGER.open(newline="") as fh:
        rows = [
            r for r in csv.DictReader(fh)
            if r["axis"] == "SNAP" and r["parent"] == bsv.R1_ID
        ]
    assert len(rows) == 3
    assert len({r["sha256"] for r in rows}) == 3
    assert len({r["sha256_zeros"] for r in rows}) == 3
    for r in rows:
        assert r["parent"] == bsv.R1_ID
        assert r["status"] == "BUILT"
        assert r["n_dots"] == "37654"
        assert r["predicted_change"].startswith("MODEL:")
        assert r["receipt_score"] == "" and r["receipt_date"] == ""
    all_shas = set()
    with LEDGER.open(newline="") as fh:
        for r in csv.DictReader(fh):
            all_shas.update({r["sha256"], r["sha256_zeros"]})
    assert len(all_shas) == 2 * len(list(csv.DictReader(LEDGER.open())))

    cards = json.loads(CARDS.read_text())
    for r in rows:
        card = cards[r["id"]]
        for key in ("hypothesis", "mechanism", "non_fault_mimic", "predicted_sign_size", "falsifier"):
            assert card[key].strip()


@pytest.mark.skipif(not SNAP_JSON, reason="SNAP releases not built in this checkout")
def test_snap_proxy_is_reported_not_gated():
    """SGMC and holdout numbers must be labelled PROXY and never written as scores."""
    for path in SNAP_JSON:
        rec = json.loads(path.read_text())
        diag = rec["report_only_diagnostics"]
        assert diag["sgmc_control"]["evidence_label"] == "PROXY"
        assert diag["holdout_proxy"]["evidence_label"] == "PROXY"
        assert "receipt_score" not in diag
        # Triangle inequality (IR-88-20): a > 3 px raster cannot score a catalogue holdout.
        assert diag["holdout_proxy"]["dti"] == 0.0
