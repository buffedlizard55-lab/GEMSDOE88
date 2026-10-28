"""Synthetic regression cases for the shared literal uniqueness gate.

These tiny rasters are test fixtures, not competition predictions or geological
experiments. An incomplete or contradictory comparison must never clear a lane.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems57 import uniqueness
import preflight_mtas88


SHAPE = (20, 20)
TRANSFORM = from_origin(0, 2000, 100, 100)
CRS = rasterio.crs.CRS.from_epsg(32611)
GRID = (SHAPE, CRS, TRANSFORM)


def write(path: Path, values: np.ndarray, *, transform=TRANSFORM, nodata=None, mask=None):
    with rasterio.open(path, "w", driver="GTiff", height=SHAPE[0], width=SHAPE[1],
                       count=1, dtype="float32", crs=CRS, transform=transform,
                       nodata=nodata) as ds:
        ds.write(values.astype(np.float32), 1)
        if mask is not None:
            ds.write_mask(mask.astype(np.uint8) * 255)


def index(path: Path):
    return {"complete_accessible_scan": True, "errors": [], "rasters": [{
        "repo_first": "synthetic", "sources": ["prior"], "cache_file": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }]}


def sample():
    fp = np.ones(SHAPE, bool)
    mine = np.zeros(SHAPE, np.float32)
    mine[2, 2] = 1
    prior = np.zeros(SHAPE, np.float32)
    prior[17, 17] = 1
    return fp, mine, prior


def compare(mine, path, fp):
    return uniqueness.compare_array_to_registry(mine, index(path), fp, expected_grid=GRID)


@pytest.mark.parametrize("bad", ["nan", "inf", "negative", "over-one", "masked"])
def test_invalid_prior_inside_footprint_is_never_a_unique_pass(tmp_path, bad):
    fp, mine, prior = sample()
    mask = np.ones(SHAPE, bool)
    if bad == "nan":
        prior[2, 2] = np.nan
    elif bad == "inf":
        prior[2, 2] = np.inf
    elif bad == "negative":
        prior[2, 2] = -0.1
    elif bad == "over-one":
        prior[2, 2] = 1.1
    else:
        mask[2, 2] = False
    path = tmp_path / "prior.tif"
    write(path, prior, mask=mask if bad == "masked" else None)
    result = compare(mine, path, fp)
    assert result["unique"] is False
    assert result["stop_required"] is True
    assert result["missing_or_invalid"] >= 1
    assert "error" in result["rows"][0]


def test_nan_and_nodata_outside_the_footprint_are_allowed(tmp_path):
    fp, mine, prior = sample()
    fp[0, :] = False
    prior[0, :] = np.nan
    path = tmp_path / "prior.tif"
    write(path, prior, nodata=np.nan)
    result = compare(mine, path, fp)
    assert result["missing_or_invalid"] == 0
    assert result["unique"] is True  # synthetic measurement only; not slot approval


def test_constant_prior_has_undefined_spearman_and_cannot_clear(tmp_path):
    fp, mine, prior = sample()
    prior[:] = 0
    path = tmp_path / "prior.tif"
    write(path, prior)
    result = compare(mine, path, fp)
    assert result["unique"] is False
    assert result["stop_required"] is True
    assert result["missing_or_invalid"] >= 1


def test_contradictory_saved_duplicate_flags_cannot_override_overlap(tmp_path):
    fp, mine, prior = sample()
    path = tmp_path / "prior.tif"
    write(path, prior)
    good = compare(mine, path, fp)
    row = copy.deepcopy(good["rows"][0])
    row.update(forward_overlap=1.0, my_dots_within_3px_of_theirs=1.0,
               duplicate_by_overlap=False)
    result = uniqueness.summarize_registry_rows(
        [row], registry_rasters_expected=1, complete_accessible_scan=True,
        source_errors=[], candidate_meta={"my_dots": 1, "candidate_rank_variation": True},
        scope="synthetic",
    )
    assert result["unique"] is False
    assert result["stop_required"] is True
    assert result["missing_or_invalid"] >= 1
    assert result["duplicate_count"] >= 1


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), 1.1, -1.1])
def test_missing_or_invalid_rho_never_clears(tmp_path, bad):
    fp, mine, prior = sample()
    path = tmp_path / "prior.tif"
    write(path, prior)
    row = copy.deepcopy(compare(mine, path, fp)["rows"][0])
    row["spearman_full_footprint"] = bad
    result = uniqueness.summarize_registry_rows(
        [row], registry_rasters_expected=1, complete_accessible_scan=True,
        source_errors=[], candidate_meta={"my_dots": 1, "candidate_rank_variation": True},
        scope="synthetic",
    )
    assert not result["unique"] and result["stop_required"]
    assert result["missing_or_invalid"] >= 1


def test_empty_inventory_and_invalid_candidate_count_never_clear(tmp_path):
    common = dict(complete_accessible_scan=True, source_errors=[], scope="synthetic")
    empty = uniqueness.summarize_registry_rows(
        [], registry_rasters_expected=0,
        candidate_meta={"my_dots": 1, "candidate_rank_variation": True}, **common)
    assert not empty["unique"] and empty["stop_required"]
    fp, mine, prior = sample()
    path = tmp_path / "prior.tif"
    write(path, prior)
    row = compare(mine, path, fp)["rows"][0]
    for count in (-1, 0, True, 0.5):
        result = uniqueness.summarize_registry_rows(
            [row], registry_rasters_expected=1,
            candidate_meta={"my_dots": count, "candidate_rank_variation": True}, **common)
        assert not result["unique"] and result["stop_required"]


def test_file_comparison_checks_candidate_crs_and_transform(tmp_path):
    fp, mine, prior = sample()
    prior_path = tmp_path / "prior.tif"
    candidate_path = tmp_path / "candidate.tif"
    write(prior_path, prior)
    write(candidate_path, mine, transform=from_origin(100, 2000, 100, 100))
    with pytest.raises(ValueError, match="(?i)(candidate|grid|transform)"):
        uniqueness.compare_to_registry(candidate_path, index(prior_path), fp, expected_grid=GRID)


def test_v5_compatibility_gate_also_rejects_invalid_registry_cells(tmp_path):
    fp, mine, prior = sample()
    prior[2, 2] = np.nan
    path = tmp_path / "prior.tif"
    write(path, prior)
    result = uniqueness.binding_duplicate_decision_v5(
        mine, [("prior", path)], fp, fp, expected_grid=GRID)
    assert result["stop_required"] is True
    assert result["verdict"] == "negative"
    assert result["errors"]


def test_halo_saturation_does_not_require_direct_saturation(tmp_path):
    shape = (5, 5)
    fp = np.ones(shape, bool)
    prior = np.zeros(shape, np.float32)
    prior[2, 2] = 1
    path = tmp_path / "witness.tif"
    transform = from_origin(0, 500, 100, 100)
    with rasterio.open(path, "w", driver="GTiff", height=5, width=5, count=1,
                       dtype="float32", crs=CRS, transform=transform) as ds:
        ds.write(prior, 1)
    proof = uniqueness.saturation_certificate(path, fp, expected_grid=(shape, CRS, transform))
    assert proof["universal_overlap_blocker"] is True
    result = preflight_mtas88.add_direct_coverage(proof, prior, fp)
    assert result["directly_saturated"] is False
    assert result["universal_overlap_blocker"] is True
