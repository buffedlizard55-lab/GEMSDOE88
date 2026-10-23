"""Do not mint an ineligible R0 SNAP artifact or exempt a PRUNE-descended child."""
from __future__ import annotations

import json
from pathlib import Path
import zipfile

import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.ndimage import distance_transform_edt

from scripts.audit_snap_clearance import reachability
from scripts import validate_variant as vv
from scripts.validate_variant import axis_for_file, clearance_counts

ROOT = Path(__file__).resolve().parents[1]


def test_radius_two_is_insufficient_even_without_other_dots():
    foot = np.ones((12, 14), bool)
    catalogue = np.zeros_like(foot)
    catalogue[:, 0] = True
    catalogue[:, 4] = True
    parent = np.zeros_like(foot)
    parent[5, 2] = True  # d_cat=2, closest legal col=7: >=5 px away
    parent[5, 5] = True  # d_cat=1, legal col=7: exactly 2 px away
    report = reachability(parent, foot, catalogue)
    assert report["n_parent_below_clearance"] == 2
    assert report["n_without_any_legal_destination_within_window"] == 1
    assert report["n_with_legal_destination_within_window_ignoring_occupancy"] == 1
    assert report["unreachable_sources"][0]["row"] == 5
    assert report["unreachable_sources"][0]["col"] == 2
    assert not report["pure_snap_possible"]


def test_fractional_mass_also_obeys_the_collar():
    from scipy.ndimage import distance_transform_edt
    foot = np.ones((11, 11), bool)
    cat = np.zeros_like(foot)
    cat[5, 5] = True
    dist = distance_transform_edt(~cat)
    image = np.zeros(foot.shape, np.float32)
    image[5, 5] = 0.01  # below dot threshold, still forbidden
    image[5, 7] = 0.10  # at d_cat=2, also forbidden for non-PRUNE
    image[5, 8] = 1.0   # d_cat=3, allowed (inclusive)
    assert clearance_counts(image, foot, cat, dist) == (1, 2)
    image[5, 5] = image[5, 7] = 0.0
    assert clearance_counts(image, foot, cat, dist) == (0, 0)


def test_validator_uses_child_axis_not_parent_axis():
    name = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SNAPtrial-20261023-deadbeef.tif"
    assert axis_for_file(Path(name)) == "SNAP"
    assert axis_for_file(Path(name.replace(".tif", "-zeros.tif"))) == "SNAP"
    assert axis_for_file(Path("h33-h33-2-b2-CONCb20px-m15-20261023-deadbeef.tif")) == "CONC"
    assert axis_for_file(Path("h33-h33-2-b2-PRUNEp1px-20261023-0542a27c.tif")) == "PRUNE"
    assert axis_for_file(Path("unidentified.tif")) is None


def test_independent_on_disk_validator_rejects_snap_but_allows_prune_flank(tmp_path, monkeypatch):
    monkeypatch.setattr(vv, "ROOT", tmp_path)
    monkeypatch.setattr(vv, "LEDGER", tmp_path / "missing-ledger.csv")
    foot = np.ones((15, 15), bool)
    foot[0, :] = False
    cat = np.zeros_like(foot)
    cat[8, 8] = True
    dist = distance_transform_edt(~cat)
    mask = np.zeros_like(foot)
    mask[8, 10] = True   # 2 px away: only PRUNE can keep this pixel
    transform = from_origin(250000, 4200000, 100, 100)
    meta = {"crs": "EPSG:32611", "shape": [15, 15],
            "transform": [round(float(x), 6) for x in tuple(transform)[:6]]}
    profile = dict(driver="GTiff", height=15, width=15, count=1,
                   dtype="float32", crs="EPSG:32611", transform=transform)
    for axis in ("SNAP", "PRUNE"):
        path = tmp_path / f"h33-h33-2-b2-{axis}trial-20261023-deadbeef.tif"
        twin = vv.twin_of(path)
        for p, nan_out in ((path, True), (twin, False)):
            arr = np.where(foot, mask.astype(np.float32), np.nan if nan_out else 0.0)
            with rasterio.open(p, "w", **profile) as dst:
                dst.write(arr.astype(np.float32), 1)
            with zipfile.ZipFile(p.with_suffix(".zip"), "w") as zf:
                zf.write(p, arcname=p.name)
        result = vv.validate(path, foot, cat, dist, mask, meta, {})
        assert result["checks"]["axis_declared"]["ok"]
        assert result["checks"]["zero_mass_on_catalogue"]["ok"]
        assert result["checks"]["non_prune_clearance_ge_3px"]["ok"] is (axis == "PRUNE")
        assert result["gates_pass"] is (axis == "PRUNE")


def test_pinned_r0_feasibility_report_explains_stop_without_claiming_score():
    report = json.loads((ROOT / "evidence" / "session_20261023_snap_clearance.json").read_text())
    assert report["decision"] == "STOP_NO_PURE_R0_SNAP_VARIANT"
    assert report["manifest_inputs_sha256_and_bytes_verified"] == 15
    assert report["r0_rebuilt_zeros_sha256"] == "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
    data = report["literal_inclusive_clearance"]
    assert data["n_parent_below_clearance"] == 1611
    assert data["n_without_any_legal_destination_within_window"] == len(data["unreachable_sources"]) == 30
    assert not data["pure_snap_possible"]
    assert all(x["min_legal_displacement_px"] > 2 for x in data["unreachable_sources"])
    assert report["new_ledger_rows"] == report["slots_used"] == 0
