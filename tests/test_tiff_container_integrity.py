"""A single-band first page is not necessarily a self-contained prediction TIFF.

All raster creation here is tiny synthetic test data, never a competition
candidate. Regressions are exercised through the existing shared local format
check and public-download audit, not through a private writer or evaluator.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
import tifffile

from scripts.audit_downloads import audit_one
from scripts.validate_artifact import validate, validate_artifact

ROOT = Path(__file__).resolve().parents[1]
SHAPE = (8, 8)
TRANSFORM = from_origin(100, 200, 100, 100)


def geotiff(path: Path) -> Path:
    values = np.zeros(SHAPE, dtype=np.float32)
    values[4, 4] = 1
    with rasterio.open(path, "w", driver="GTiff", height=SHAPE[0], width=SHAPE[1],
                       count=1, dtype="float32", crs="EPSG:32611", transform=TRANSFORM) as dst:
        dst.write(values, 1)
    return path


def package(path: Path) -> Path:
    with zipfile.ZipFile(path.with_suffix(".zip"), "w") as archive:
        archive.writestr(path.name, path.read_bytes())
    return path


def download_audit(path: Path, sample: Path) -> dict:
    return audit_one(package(path), sample, np.zeros(SHAPE, dtype=bool), np.ones(SHAPE, dtype=bool))


@pytest.mark.parametrize("extra_shape", [SHAPE, (2, 2)])
@pytest.mark.parametrize("extra_value", [0.5, -123.0, np.nan])
def test_second_full_resolution_raster_is_rejected(tmp_path, extra_shape, extra_value):
    sample = geotiff(tmp_path / "sample.tif")
    candidate = geotiff(tmp_path / "multipage-DO-NOT-SUBMIT.tif")
    with tifffile.TiffWriter(candidate, append=True) as writer:
        writer.write(np.full(extra_shape, extra_value, dtype=np.float32), metadata=None)
    # This was the false-positive path: both readers may show the first page,
    # and count=1 says nothing about the additional full-resolution IFD.
    with rasterio.open(candidate) as src:
        assert src.count == 1
        assert len(src.subdatasets) == 2
    result = validate(candidate, sample)
    assert result["validator"] == "gems88-format-audit-v2"
    assert result["checks"]["values_in_0_1"] is True  # first page only
    assert result["checks"]["single_raster_dataset"] is False
    assert result["format_valid"] is False
    assert validate_artifact(candidate, sample)["ok"] is False
    assert download_audit(candidate, sample)["research_download_ok"] is False


def test_ambiguous_multipage_template_is_rejected(tmp_path):
    sample = geotiff(tmp_path / "sample.tif")
    candidate = geotiff(tmp_path / "candidate.tif")
    with tifffile.TiffWriter(sample, append=True) as writer:
        writer.write(np.zeros((2, 2), dtype=np.float32), metadata=None)
    result = validate(candidate, sample)
    assert result["checks"]["template_single_raster_dataset"] is False
    assert result["format_valid"] is False


def sidecar_georeferenced_tiff(path: Path) -> Path:
    tifffile.imwrite(path, np.eye(*SHAPE, dtype=np.float32), metadata=None)
    Path(str(path) + ".aux.xml").write_text(
        "<PAMDataset><SRS>EPSG:32611</SRS>"
        "<GeoTransform>100,100,0,200,0,-100</GeoTransform></PAMDataset>"
    )
    return path


def test_sidecar_cannot_supply_georeferencing_missing_from_zip(tmp_path):
    sample = geotiff(tmp_path / "sample.tif")
    candidate = sidecar_georeferenced_tiff(tmp_path / "sidecar-DO-NOT-SUBMIT.tif")
    with rasterio.open(candidate) as local:
        assert local.crs.to_epsg() == 32611
        assert local.transform == TRANSFORM
        assert len(local.files) == 2
    # The portal sees the one-TIFF ZIP, not our local .aux.xml. This proves
    # that byte identity alone does not establish a standalone ZIP roundtrip.
    with MemoryFile(candidate.read_bytes()) as memory, memory.open() as embedded:
        assert embedded.crs is None
        assert embedded.transform != TRANSFORM
    result = validate(candidate, sample)
    assert result["checks"]["crs_match"] is True  # previously enough to pass
    assert result["checks"]["transform_match"] is True
    assert result["checks"]["self_contained_dataset"] is False
    assert result["format_valid"] is False
    assert download_audit(candidate, sample)["research_download_ok"] is False


def test_sidecar_dependent_template_is_rejected(tmp_path):
    sample = sidecar_georeferenced_tiff(tmp_path / "sample.tif")
    candidate = geotiff(tmp_path / "candidate.tif")
    result = validate(candidate, sample)
    assert result["checks"]["template_self_contained_dataset"] is False
    assert result["format_valid"] is False


def test_internal_overviews_are_not_extra_full_resolution_rasters(tmp_path):
    sample = geotiff(tmp_path / "sample.tif")
    candidate = geotiff(tmp_path / "overviews-DO-NOT-SUBMIT.tif")
    with rasterio.open(candidate, "r+") as src:
        src.build_overviews([2, 4], Resampling.average)
    with rasterio.open(candidate) as src:
        assert src.overviews(1) == [2, 4]
        assert src.subdatasets == []
    assert validate(candidate, sample)["format_valid"] is True
    assert download_audit(candidate, sample)["research_download_ok"] is True


@pytest.mark.parametrize("optimized", [False, True])
def test_cli_rejects_multipage_container_even_under_optimized_python(tmp_path, optimized):
    sample = geotiff(tmp_path / "sample.tif")
    candidate = geotiff(tmp_path / "bad.tif")
    with tifffile.TiffWriter(candidate, append=True) as writer:
        writer.write(np.full((2, 2), -123, dtype=np.float32), metadata=None)
    command = [sys.executable] + (["-O"] if optimized else [])
    result = subprocess.run(command + [str(ROOT / "scripts/validate_artifact.py"),
                            str(candidate), "--template", str(sample)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["format_valid"] is False
    assert report["submission_ready"] is False
    assert report["footprint_audit"]["ok"] is False


def test_published_research_tiffs_have_one_self_contained_raster():
    # Metadata-only audit of all saved deliverables, including internal-overview
    # compatibility. The full numeric audit is exercised by audit_downloads.py.
    paths = sorted((ROOT / "docs/downloads").glob("*.tif"))
    assert paths
    for path in paths:
        with rasterio.open(path) as source:
            assert source.count == 1, path.name
            assert source.subdatasets == [], path.name
            assert {Path(p).resolve() for p in source.files} == {path.resolve()}, path.name
