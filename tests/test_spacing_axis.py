"""Guards for the lowest-priority, controlled AXIS=SPACING build.

The unit tests use tiny synthetic grids.  Artifact tests read tracked receipts
and skip local-only GeoTIFF assertions when candidate rasters are unavailable.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_spacing_variants as spacing  # noqa: E402


VALUES = {"lattice", "poisson", "alongstrike"}


def test_spacing_values_are_unique_and_predicted_before_proxy():
    assert {str(s["value"]) for s in spacing.SPECS} == VALUES
    assert len(spacing.SPECS) == 3
    for spec in spacing.SPECS:
        lo, hi = spec["prediction_range"]
        assert lo <= spec["prediction"] <= hi
        assert -1.0 <= lo <= hi <= 1.0


def test_json_safe_preserves_portable_nan_semantics():
    assert spacing.json_safe({"nodata": float("nan"), "deep": [float("inf"), -float("inf")]}) == {
        "nodata": "NaN", "deep": ["Infinity", "-Infinity"]
    }


def test_sqrt5_guard_blocks_only_strictly_closer_integer_cells():
    offsets = set(spacing.separation_offsets(math.sqrt(5.0)))
    assert (0, 0) in offsets
    assert (2, 0) in offsets and (0, -2) in offsets
    assert (1, 1) in offsets
    # Exactly sqrt(5) is allowed by the >= sqrt(5) guard.
    assert (2, 1) not in offsets and (1, 2) not in offsets


def test_common_donor_selection_is_geometry_only_and_excludes_collar():
    parent = np.zeros((9, 9), dtype=bool)
    # Dense local group plus spaced dots; two cells are inside the non-PRUNE collar.
    parent[1, 1] = parent[1, 4] = parent[4, 1] = True
    parent[4, 4] = parent[4, 7] = parent[7, 4] = parent[7, 7] = True
    dcat = np.full(parent.shape, 10.0, dtype=np.float32)
    dcat[1, 1] = 2.0
    dcat[1, 4] = 2.9

    donors, stats = spacing.common_crowded_donors(parent, dcat, n_extra=2)
    assert int(donors.sum()) == 2
    assert not donors[1, 1] and not donors[1, 4]
    assert stats["common_collar_removed_n"] == 2
    assert stats["common_crowded_removed_n"] == 2
    assert stats["common_crowded_donor_nn_px"]["max"] <= 4.25


def test_selector_holds_count_and_enforces_registered_separation():
    anchor = np.zeros((16, 16), dtype=bool)
    anchor[2, 2] = True
    cy = np.array([2, 5, 8, 11, 14], dtype=np.int32)
    cx = np.array([8, 8, 8, 8, 8], dtype=np.int32)
    selected, stats = spacing.select_candidates(
        anchor, cy, cx, np.arange(len(cy)), n_select=3, min_separation_px=math.sqrt(5.0)
    )
    assert int(selected.sum()) == 3
    assert stats["candidate_cells_selected"] == 3
    points = np.argwhere(anchor | selected)
    assert cKDTree(points).query(points, k=2)[0][:, 1].min() >= math.sqrt(5.0) - 1e-9


def test_hex_lattice_has_zero_residual_at_lattice_vertex_and_is_deterministic():
    y = np.array([0, 1, 4, 8], dtype=np.int32)
    x = np.array([0, 2, 4, 8], dtype=np.int32)
    a = spacing.hex_lattice_residual(y, x, pitch_px=4.0)
    b = spacing.hex_lattice_residual(y, x, pitch_px=4.0)
    assert np.array_equal(a, b)
    assert a[0] == pytest.approx(0.0)
    assert np.all(a >= 0.0)


def test_geodesic_distance_stays_on_support_and_leaves_disconnected_strand_infinite():
    support = np.zeros((7, 7), dtype=bool)
    support[3, 1:5] = True
    support[0, 0:2] = True  # disconnected component
    anchor = np.zeros_like(support)
    anchor[3, 1] = True
    d = spacing.geodesic_distance_on_support(support, anchor)
    assert d[3, 1] == 0.0
    assert d[3, 4] == pytest.approx(3.0)
    assert np.isinf(d[0, 0])
    assert np.isinf(d[2, 2])


def test_preflight_refuses_repeated_spacing_value(tmp_path, monkeypatch):
    monkeypatch.setattr(spacing, "ROOT", tmp_path)
    (tmp_path / "releases").mkdir()
    rows = [{"parent": "any", "axis": "SPACING", "value": "lattice", "id": "already", "sha256": "a", "sha256_zeros": "b"}]
    with pytest.raises(ValueError, match="already built"):
        spacing.preflight(rows, [])


def test_tracked_receipts_ledger_cards_and_preregistration_agree():
    report_path = ROOT / "evidence" / "spacing_axis_report.json"
    prereg_path = ROOT / "registry" / "spacing_preregistration.json"
    if not report_path.exists():
        pytest.skip("SPACING session has not been built in this checkout")

    report = json.loads(report_path.read_text())
    prereg = json.loads(prereg_path.read_text())
    assert report["axis"] == prereg["axis"] == "SPACING"
    assert report["manifest_inputs_verified"] == 15
    assert report["parent"]["dots"] == 37_654
    assert report["leakage_canary"]["passed"]
    validation = report["independent_validation"]
    assert validation["gates_all_pass"]
    assert len(validation["results"]) == 6
    assert all(r["checks"]["axis_declared"]["ok"] for r in validation["results"])
    assert all(r["checks"]["non_prune_clearance_ge_3px"]["ok"] for r in validation["results"])
    common = report["common_normalization"]
    assert common["canonical_dot_thin_2p8_count_on_legal_support"] == 36_718
    assert "strict_2p8_feasible_count_on_legal_support" not in common
    assert "not a proof" in common["feasibility_interpretation_correction"]
    assert "do not treat the file as a blind proxy preregistration" in prereg["attempt_integrity"]["caveat"]
    assert set(v["value"] for v in prereg["variants"]) == VALUES

    with (ROOT / "ledger" / "submissions.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    ours = [r for r in rows if r["axis"] == "SPACING"]
    assert len(ours) == 3
    assert {r["value"] for r in ours} == VALUES
    assert all(r["parent"] == spacing.PARENT_ID and r["status"] == "BUILT" for r in ours)
    assert all(r["receipt_score"] == r["receipt_date"] == "" for r in ours)
    hashes = [r[k] for r in rows for k in ("sha256", "sha256_zeros")]
    assert len(hashes) == len(set(hashes))

    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
    for row in ours:
        rec_path = ROOT / "releases" / f"{row['id']}.json"
        rec = json.loads(rec_path.read_text())
        assert rec["sha256"] == row["sha256"]
        assert rec["sha256_zeros"] == row["sha256_zeros"]
        assert rec["gates"]["reread_from_disk_verified"]
        assert rec["parent_diff"]["n_added"] == rec["parent_diff"]["n_removed"]
        assert 1.0 <= rec["parent_diff"]["pct_changed_moved"] <= 50.0
        assert rec["parent_diff"]["min_dist_catalogue_px"] >= 3.0
        assert cards[row["id"]]["axis"] == "SPACING"
        assert all(k in cards[row["id"]] for k in ("hypothesis", "mechanism", "non_fault_mimic", "predicted_sign_size", "falsifier"))


def test_local_spacing_rasters_re_read_when_present():
    report_path = ROOT / "evidence" / "spacing_axis_report.json"
    if not report_path.exists():
        pytest.skip("SPACING session has not been built in this checkout")
    report = json.loads(report_path.read_text())
    local = [ROOT / f"releases/{candidate_id}.tif" for candidate_id in report["variants"]]
    if not all(p.exists() for p in local):
        pytest.skip("candidate GeoTIFFs are intentionally local-only")

    import rasterio

    for path in local:
        with rasterio.open(path) as ds:
            arr = ds.read(1)
            assert ds.count == 1 and ds.dtypes[0] == "float32"
            assert str(ds.crs) == "EPSG:32611"
            assert np.isfinite(arr[np.isfinite(arr)]).all()
