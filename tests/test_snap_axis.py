"""Tests for AXIS=SNAP (scripts/build_snap_variants.py).

Unit tests exercise the snap() collision/count logic on synthetic grids and
run anywhere. Integration tests re-read the built releases from disk and are
skipped when the gitignored data/ or release rasters are absent (CI without
restored inputs).
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_snap_variants as bsv  # noqa: E402

SNAP_ROWS = {
    "r1": "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SNAPr1-20261023-a0133e96",
    "r2": "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SNAPr2-20261023-93187627",
    "r2g": "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SNAPr2g-20261023-06b3ac6a",
}


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- unit


def _grid(dots, edge_peak, shape=(9, 9)):
    parent = np.zeros(shape, dtype=bool)
    for y, x in dots:
        parent[y, x] = True
    edge = np.zeros(shape, dtype=np.float32)
    for (y, x), v in edge_peak.items():
        edge[y, x] = v
    legal = np.ones(shape, dtype=bool)
    return parent, edge, legal


def test_snap_moves_to_local_edge_max_and_holds_count():
    parent, edge, legal = _grid([(4, 4)], {(4, 5): 0.9, (4, 4): 0.1})
    out, stats = bsv.snap(parent, edge, legal, radius=1.0, min_gain=0.0)
    assert int(out.sum()) == 1 and out[4, 5]
    assert stats["n_moved"] == 1 and stats["mean_displacement_px_all"] == 1.0


def test_snap_radius_one_excludes_diagonals():
    parent, edge, legal = _grid([(4, 4)], {(5, 5): 0.9, (4, 4): 0.1})
    out, _ = bsv.snap(parent, edge, legal, radius=1.0, min_gain=0.0)
    assert out[4, 4]  # diagonal is 1.41 px away: unreachable at R=1
    out2, _ = bsv.snap(parent, edge, legal, radius=2.0, min_gain=0.0)
    assert out2[5, 5]


def test_snap_min_gain_forces_stay():
    parent, edge, legal = _grid([(4, 4)], {(4, 5): 0.13, (4, 4): 0.10})
    out, stats = bsv.snap(parent, edge, legal, radius=2.0, min_gain=0.05)
    assert out[4, 4] and stats["n_moved"] == 0  # gain 0.03 < 0.05


def test_snap_collision_keeps_count_and_prefers_higher_gain():
    # Two dots both want (4,5); higher-gain dot wins, loser stays.
    parent, edge, legal = _grid(
        [(4, 4), (4, 6)], {(4, 5): 1.0, (4, 4): 0.0, (4, 6): 0.5})
    out, stats = bsv.snap(parent, edge, legal, radius=1.0, min_gain=0.0)
    assert int(out.sum()) == 2
    assert out[4, 5] and out[4, 6]  # (4,4) dot gained 1.0 > (4,6) dot's 0.5
    assert stats["n_moved"] == 1


def test_snap_never_leaves_legal_area():
    parent, edge, legal = _grid([(4, 4)], {(4, 6): 1.0, (4, 4): 0.1})
    legal[4, 6] = False
    out, _ = bsv.snap(parent, edge, legal, radius=2.0, min_gain=0.0)
    assert not out[4, 6] and int(out.sum()) == 1


def test_snap_nodata_origin_stays():
    parent, edge, legal = _grid([(4, 4)], {(4, 5): 0.9})
    edge[4, 4] = -1.0  # feature-nodata at origin
    legal[4, 4] = False
    out, stats = bsv.snap(parent, edge, legal, radius=1.0, min_gain=0.0)
    # gain is 0 by construction for nodata origins, so no forced move;
    # count must hold either way and the dot must be accounted for.
    assert int(out.sum()) == 1
    assert stats["n_dots_on_feature_nodata_forced_stay"] == 1


def test_percentile_rank_ties_and_invalid():
    vals = np.array([[1.0, 1.0], [3.0, np.nan]])
    valid = np.array([[True, True], [True, True]])
    r = bsv.percentile_rank(vals, valid)
    assert r[0, 0] == pytest.approx(r[0, 1])  # tied values share a rank
    assert r[1, 0] == pytest.approx(1.0)
    assert r[1, 1] == -1.0  # non-finite excluded


def test_predictions_predeclared_for_all_variants():
    for value, _, _ in bsv.VARIANTS:
        pred, rng = bsv.PREDICTIONS[value]
        assert pred.startswith("MODEL:") and rng.startswith("[")


# ---------------------------------------------------------- integration

_HAVE_RELEASES = all((ROOT / "releases" / f"{v}.tif").is_file() for v in SNAP_ROWS.values())
_HAVE_DATA = (ROOT / "data" / "bridge" / "sample_submission.tif").is_file()
needs_disk = pytest.mark.skipif(
    not (_HAVE_RELEASES and _HAVE_DATA),
    reason="restored data/ inputs or built SNAP releases absent",
)


@needs_disk
@pytest.mark.parametrize("value,vid", sorted(SNAP_ROWS.items()))
def test_snap_release_gates_from_disk(value, vid):
    import rasterio
    from scipy.ndimage import distance_transform_edt

    nan_p = ROOT / "releases" / f"{vid}.tif"
    zeros_p = ROOT / "releases" / f"{vid}-zeros.tif"
    rec = json.loads((ROOT / "releases" / f"{vid}.json").read_text())
    assert _sha256(nan_p) == rec["sha256"]
    assert _sha256(zeros_p) == rec["sha256_zeros"]

    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        ref = (ds.shape, str(ds.crs), tuple(ds.transform))
    with rasterio.open(ROOT / "data" / "bridge" / "existing_faults.tif") as ds:
        catalogue = (ds.read(1) == 1) & foot
    dist = distance_transform_edt(~catalogue)

    with rasterio.open(nan_p) as ds:
        assert (ds.shape, str(ds.crs), tuple(ds.transform)) == ref
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        a = ds.read(1)
    assert np.isfinite(a[foot]).all() and np.isnan(a[~foot]).all()
    assert float(a[foot].min()) >= 0.0 and float(a[foot].max()) <= 1.0
    dots = a > 0.5
    assert int(dots.sum()) == 37_654
    assert int(dots[catalogue].sum()) == 0
    assert float(dist[dots].min()) > 3.0  # hard constraint 4 (non-PRUNE)
    assert rec["snap"]["max_displacement_px"] <= 2.0 + 1e-9
    assert len(rec["form_note"]) <= 140

    for zip_p, tif_name in ((ROOT / "releases" / f"{vid}.zip", f"{vid}.tif"),
                            (ROOT / "releases" / f"{vid}-zeros.zip", f"{vid}-zeros.tif")):
        with zipfile.ZipFile(zip_p) as zf:
            assert zf.namelist() == [tif_name]
            payload = zf.read(tif_name)
        assert hashlib.sha256(payload).hexdigest() == _sha256(ROOT / "releases" / tif_name)


@needs_disk
def test_snap_ledger_rows_unique_and_complete():
    with (ROOT / "ledger" / "submissions.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    shas = [r["sha256"] for r in rows] + [r["sha256_zeros"] for r in rows]
    assert len(shas) == len(set(shas)), "duplicate hash in ledger"
    snap = [r for r in rows if r["axis"] == "SNAP"]
    assert {r["id"] for r in snap} == set(SNAP_ROWS.values())
    for r in snap:
        assert r["status"] == "BUILT" and r["n_dots"] == "37654"
        assert r["parent"] == bsv.PARENT_ID
        assert r["predicted_change"].startswith("MODEL:")
