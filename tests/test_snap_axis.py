"""Tests for AXIS = SNAP (scripts/build_snap_variants.py, brief v2 §5).

Two layers:

* a pure-geometry unit layer that exercises :func:`snap` on a tiny synthetic
  grid (count fixed, exclusions honoured, window respected, deterministic), and
* a ledger layer that checks every ``axis == SNAP`` row for internal
  consistency and re-verifies the released rasters when they are present on
  disk (they are gitignored, so this part skips in a fresh clone).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_snap_variants import MIN_DCAT, snap  # noqa: E402

LEDGER = ROOT / "ledger" / "submissions.csv"
RELEASES = ROOT / "releases"


def _toy():
    h = w = 40
    foot = np.ones((h, w), bool)
    catalogue = np.zeros((h, w), bool)
    catalogue[18, 5:35] = True                     # a horizontal catalogue trace
    d_cat = np.hypot(*np.meshgrid(np.arange(w), np.arange(h)))  # placeholder
    # exact Euclidean distance to the trace (float, in pixels)
    yy, xx = np.mgrid[0:h, 0:w]
    d_cat = np.min(np.abs(yy - 18).astype(float), axis=0)[None, :].repeat(h, axis=0)
    d_cat = np.abs(yy - 18).astype(float)
    rng = np.random.default_rng(7)
    edge = rng.random((h, w)).astype(np.float32)
    mask = np.zeros((h, w), bool)
    idx = rng.choice(h * w, size=60, replace=False)
    mask.reshape(-1)[idx] = True
    mask &= foot & ~catalogue
    return mask, edge, foot, catalogue, d_cat


def test_snap_holds_count_and_exclusions():
    mask, edge, foot, catalogue, d_cat = _toy()
    res = snap(mask, edge, foot, catalogue, d_cat, max_disp=2)
    out = res["mask"]
    assert int(out.sum()) == int(mask.sum())
    assert int((out & catalogue).sum()) == 0
    moved = out & ~mask
    assert moved.sum() > 0
    assert float(d_cat[moved].min()) > MIN_DCAT
    # every new dot is within the window of some old dot
    ys, xs = np.nonzero(moved)
    for y, x in zip(ys, xs):
        win = mask[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
        assert win.any()


def test_snap_only_moves_uphill_and_is_deterministic():
    mask, edge, foot, catalogue, d_cat = _toy()
    a = snap(mask, edge, foot, catalogue, d_cat, max_disp=2)["mask"]
    b = snap(mask, edge, foot, catalogue, d_cat, max_disp=2)["mask"]
    assert np.array_equal(a, b)
    # destinations strictly beat their sources in the edge field
    for y, x, yy, xx, gain in snap(mask, edge, foot, catalogue, d_cat, max_disp=2)["moves"]:
        assert gain > 0
        assert edge[yy, xx] > edge[y, x]


def test_snap_window_one_cannot_reach_two_pixels():
    mask, edge, foot, catalogue, d_cat = _toy()
    res = snap(mask, edge, foot, catalogue, d_cat, max_disp=1)
    for y, x, yy, xx, _g in res["moves"]:
        assert abs(yy - y) <= 1 and abs(xx - x) <= 1


def test_snap_gain_gate_suppresses_marginal_moves():
    mask, edge, foot, catalogue, d_cat = _toy()
    loose = snap(mask, edge, foot, catalogue, d_cat, max_disp=2, gain_min=0.0)["n_moved"]
    tight = snap(mask, edge, foot, catalogue, d_cat, max_disp=2, gain_min=0.4)["n_moved"]
    assert tight < loose


# ---------------------------------------------------------------------------
# Ledger / release consistency
# ---------------------------------------------------------------------------

# Scoped to this family: a second SNAP family on parent R1 = PRUNEp3px landed in the
# same session (tests/test_snap_r1_axis.py, IR-88-29); both share the ledger.
SNAP_PARENT = "h33-h33-2-b2"


def _ledger_rows():
    if not LEDGER.is_file():
        pytest.skip("no ledger")
    with LEDGER.open(newline="") as f:
        return [
            r for r in csv.DictReader(f)
            if r.get("axis") == "SNAP" and r.get("parent") == SNAP_PARENT
        ]


def test_ledger_has_three_unique_snap_variants():
    rows = _ledger_rows()
    assert len(rows) == 3, [r["id"] for r in rows]
    assert len({(r["parent"], r["axis"], r["value"]) for r in rows}) == 3
    shas = {r["sha256"] for r in rows} | {r["sha256_zeros"] for r in rows}
    assert len(shas) == 6
    assert {r["value"] for r in rows} == {"w2E1", "w2S2", "w2E2"}
    for r in rows:
        assert r["parent"] == SNAP_PARENT
        assert r["status"] == "BUILT"
        assert r["predicted_change"].startswith("MODEL:")
        assert int(r["n_dots"]) == 37654
        assert 1.0 <= float(r["pct_changed"]) <= 100.0


def test_each_snap_row_has_a_receipt_with_gates_and_a_short_note():
    for r in _ledger_rows():
        p = RELEASES / f"{r['id']}.json"
        if not p.is_file():
            pytest.skip("receipts are gitignored in a fresh clone")
        rec = json.loads(p.read_text())
        assert rec["sha256"] == r["sha256"] and rec["sha256_zeros"] == r["sha256_zeros"]
        assert rec["form_note_chars"] <= 140
        assert all(rec["gates"].values())
        pd = rec["parent_diff"]
        assert pd["n_added"] == pd["n_removed"]          # count held
        assert pd["dots_le_1px"] == 0 and pd["dots_le_2px"] == 0
        assert pd["min_dist_catalogue_px"] > 2.0


def test_released_snap_rasters_revalidate_from_disk():
    import rasterio

    rows = _ledger_rows()
    if not rows or not (RELEASES / f"{rows[0]['id']}-zeros.tif").is_file():
        pytest.skip("SNAP rasters are gitignored / not built in this checkout")
    with rasterio.open(ROOT / "data" / "registry" / "h33_education.tif") as src:
        parent = src.read(1) > 0.5
    for r in rows:
        with rasterio.open(RELEASES / f"{r['id']}.tif") as src:
            arr = src.read(1)
            assert src.count == 1 and src.dtypes[0] == "float32"
        dots = arr > 0.5
        assert int(dots.sum()) == int(parent.sum())
        with rasterio.open(RELEASES / f"{r['id']}-zeros.tif") as src:
            z = src.read(1)
        assert np.array_equal(z > 0.5, dots)
