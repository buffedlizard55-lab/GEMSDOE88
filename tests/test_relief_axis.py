"""Tests for AXIS=RELIEF (parent R1 = PRUNEp3px): tercile reallocation at fixed count.

Two layers, mirroring ``test_snap_r1_axis.py``:

* Unit tests on a synthetic grid for :func:`build_relief_variants.terrain_terciles` and
  :func:`build_relief_variants.relief_move` -- count preservation, source/target tercile
  discipline, the strict catalogue collar, and determinism are properties of the
  algorithm, not of the shipped files.
* Artifact tests that re-read the three releases from disk and re-derive every MUST gate
  (format, zero catalogue mass, ``> 3 px`` collar, fixed 37,654 count, parent diff inside
  the brief's 10-15 % dose, ledger + mechanism-card presence).

Artifact tests skip when the rasters are absent: ``releases/*.tif`` is gitignored, so a
fresh clone must regenerate them with ``python3 scripts/build_relief_variants.py``.
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

import build_relief_variants as brv  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"

OUR_VALUES = ("up2t10", "up2t15", "dn2t15")  # this family only; see test_relief_bracket_axis.py (IR-88-36)
RELIEF_JSON = [
    p for v in OUR_VALUES
    for p in sorted(RELEASES.glob(f"{brv.R1_ID}-RELIEF{v}-*.json"))
    if p.with_suffix("").with_suffix(".tif").is_file()
]


# ---------------------------------------------------------------------------
# Unit tests: algorithm properties on a synthetic grid
# ---------------------------------------------------------------------------


def _synthetic(size: int = 48):
    """Detrended elevation increases linearly with row, so rows split into thirds.

    Rows near the top are the low ('basin') tercile, the middle rows are 'piedmont' and
    the bottom rows are the high ('range_front') tercile. The catalogue sits far from
    every dot so the collar never binds on the synthetic grid.
    """
    foot = np.ones((size, size), dtype=bool)
    foot[0, :] = False  # ragged edge so clipping is exercised
    det_elev = np.repeat(
        np.arange(size, dtype=np.float32)[:, None], size, axis=1
    )

    cls, thresholds = brv.terrain_terciles(det_elev, foot)

    mask = np.zeros((size, size), dtype=bool)
    for r in (5, 9, 13, 17, 21):        # source side (basin/piedmont)
        mask[r, 4] = mask[r, 12] = mask[r, 30] = True
    for r in (32, 36, 40, 44):          # target side (range front)
        mask[r, 4] = mask[r, 20] = mask[r, 40] = True

    catalogue = np.zeros((size, size), dtype=bool)
    catalogue[1, 1] = True
    d_cat = distance_transform_edt(~catalogue)

    ridge = np.zeros((size, size), dtype=bool)
    ridge[30:46, 3:42] = True           # unused range-front ridge support

    w = np.zeros((size, size), dtype=np.float32)
    w[mask] = 0.2
    w[ridge] = 0.05
    return foot, mask, catalogue, d_cat, cls, thresholds, ridge, w


def test_terciles_are_equal_area_and_label_outside_footprint():
    foot, _, _, _, cls, thresholds, _, _ = _synthetic()
    assert thresholds[0] < thresholds[1]
    assert (cls[~foot] == -1).all()
    assert set(np.unique(cls[foot])) == {0, 1, 2}
    counts = np.bincount(cls[foot], minlength=3)
    # Equal area in each tercile: every class holds a third of the footprint (+/- 5%).
    share = counts / counts.sum()
    assert np.allclose(share, 1.0 / 3.0, atol=0.05), share


def test_relief_move_holds_count_and_respects_terciles():
    foot, mask, catalogue, d_cat, cls, _, ridge, w = _synthetic()
    n_move = 6
    new, stats = brv.relief_move(
        mask=mask,
        foot=foot,
        cls=cls,
        w=w,
        d_cat=d_cat,
        ridge=ridge,
        source_classes=(0, 1),
        target_class=2,
        n_move=n_move,
    )
    assert int(new.sum()) == int(mask.sum())
    assert stats["n_move"] == n_move
    assert stats["target_class"] == 2

    removed = mask & ~new
    added = new & ~mask
    assert int(removed.sum()) == n_move and int(added.sum()) == n_move
    # Donors only ever come from the source terciles, receivers only from the target.
    assert not (cls[removed] == 2).any()
    assert (cls[added] == 2).all()
    assert stats["donors_removed_per_class"]["range_front"] == 0


def test_relief_move_is_deterministic_and_collar_clean():
    foot, mask, catalogue, d_cat, cls, _, ridge, w = _synthetic()
    kw = dict(foot=foot, cls=cls, w=w, d_cat=d_cat, ridge=ridge,
              source_classes=(0, 1), target_class=2, n_move=5)
    first, _ = brv.relief_move(mask=mask, **kw)
    second, _ = brv.relief_move(mask=mask, **kw)
    assert np.array_equal(first, second)
    assert not first[catalogue].any()
    assert d_cat[first].min() > brv.MIN_CATALOGUE_PX


def test_relief_move_rejects_impossible_pools():
    foot, mask, catalogue, d_cat, cls, _, ridge, w = _synthetic()
    with pytest.raises(ValueError):
        brv.relief_move(
            mask=mask, foot=foot, cls=cls, w=w, d_cat=d_cat, ridge=ridge,
            source_classes=(0, 1), target_class=2, n_move=int(mask.sum()),
        )
    with pytest.raises(ValueError):
        brv.relief_move(
            mask=mask, foot=foot, cls=cls, w=w, d_cat=d_cat, ridge=ridge,
            source_classes=(0, 1), target_class=2, n_move=0,
        )


def test_relief_move_refuses_target_inside_the_collar():
    foot, mask, catalogue, _, cls, _, ridge, w = _synthetic()
    d_cat_collar = np.zeros(mask.shape, dtype=np.float64)
    d_cat_collar[:, :] = 1.0  # every cell violates the 3 px collar
    with pytest.raises(ValueError):
        brv.relief_move(
            mask=mask, foot=foot, cls=cls, w=w, d_cat=d_cat_collar, ridge=ridge,
            source_classes=(0, 1), target_class=2, n_move=4,
        )


# ---------------------------------------------------------------------------
# Artifact tests: re-read shipped rasters and re-derive the gates
# ---------------------------------------------------------------------------


def _ledger_rows() -> list[dict[str, str]]:
    with LEDGER.open("r", newline="") as fh:
        return [r for r in csv.DictReader(fh)
                if r.get("axis") == "RELIEF" and r.get("value") in OUR_VALUES]


def test_ledger_has_one_row_per_relief_variant():
    rows = _ledger_rows()
    assert {r["value"] for r in rows} == {"up2t10", "up2t15", "dn2t15"}
    shas = [r["sha256"] for r in rows] + [r["sha256_zeros"] for r in rows]
    assert len(set(shas)) == len(shas), "duplicate SHA-256 across RELIEF rows"
    for r in rows:
        assert r["parent"] == brv.R1_ID
        assert r["status"] == "BUILT"
        assert r["predicted_change"].startswith("MODEL:")
        assert r["n_dots"] == "37654"


def test_mechanism_cards_exist_for_every_relief_variant():
    cards = json.loads(CARDS.read_text())
    for r in _ledger_rows():
        assert r["id"] in cards, f"missing mechanism card for {r['id']}"
        card = cards[r["id"]]
        for key in ("hypothesis", "mechanism", "non_fault_mimic", "predicted_sign_size", "falsifier"):
            assert card[key].strip(), f"{r['id']} card is missing {key}"


@pytest.mark.skipif(not RELIEF_JSON, reason="relief rasters are gitignored; rebuild with scripts/build_relief_variants.py")
def test_relief_rasters_pass_every_must_gate():
    if not (ROOT / "data" / "bridge" / "sample_submission.tif").is_file():
        pytest.skip("competition grid not restored")
    sample_path = ROOT / "data" / "bridge" / "sample_submission.tif"
    with rasterio.open(sample_path) as tpl:
        ref = (tpl.shape, tpl.crs, tpl.transform)
    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as ds:
        catalogue = ds.read(1) == 1

    assert len(RELIEF_JSON) == 3
    for receipt_path in RELIEF_JSON:
        rec = json.loads(receipt_path.read_text())
        assert all(rec["gates"].values()), f"{rec['id']} failed a MUST gate"
        assert rec["parent"] == brv.R1_ID
        assert 10.0 <= rec["parent_diff"]["pct_changed_moved"] <= 15.0
        assert rec["parent_diff"]["dots_le_3px"] == 0
        assert rec["form_note_chars"] <= 140

        tif = ROOT / rec["file_nan"]
        with rasterio.open(tif) as ds:
            assert (ds.shape, ds.crs, ds.transform) == ref
            assert ds.count == 1 and ds.dtypes[0] == "float32"
            arr = ds.read(1)
        foot = np.isfinite(arr)
        assert np.isfinite(arr[foot]).all()
        assert np.isnan(arr[~foot]).all()
        assert float(arr[foot].min()) >= 0.0 and float(arr[foot].max()) <= 1.0
        assert (arr[catalogue] > 0.0).sum() == 0
        assert int((arr[foot] > 0.5).sum()) == 37654

        d_cat = distance_transform_edt(~catalogue)
        assert d_cat[arr > 0.5].min() > brv.MIN_CATALOGUE_PX

        zeros = ROOT / rec["file_zeros"]
        with rasterio.open(zeros) as ds:
            zarr = ds.read(1)
        assert np.isfinite(zarr).all()
        assert np.array_equal(zarr > 0.5, arr > 0.5)
