"""The independent disk audit must enforce the organizer's float32 format.

These tiny files are synthetic tests, not model experiments or submissions.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_artifact import validate, validate_artifact  # noqa: E402


def write_raster(path: Path, dtype: str, value: float = 0) -> Path:
    data = np.full((8, 8), value, dtype=dtype)
    with rasterio.open(
        path, "w", driver="GTiff", width=8, height=8, count=1,
        dtype=dtype, crs="EPSG:32611", transform=from_origin(0, 800, 100, 100),
    ) as dst:
        dst.write(data, 1)
    return path


@pytest.mark.parametrize("dtype", ["float64", "uint8", "int16", "complex64"])
def test_non_float32_fails_even_when_values_are_finite_and_in_range(tmp_path, dtype):
    sample = write_raster(tmp_path / "sample.tif", "float32")
    candidate = write_raster(tmp_path / "candidate.tif", dtype)
    result = validate(candidate, sample)
    assert result["checks"]["dtype_float32"] is False
    assert result["format_valid"] is False
    assert result["submission_ready"] is False
    assert validate_artifact(candidate, sample)["ok"] is False


def test_float32_format_pass_is_not_slot_approval(tmp_path):
    sample = write_raster(tmp_path / "sample.tif", "float32")
    candidate = write_raster(tmp_path / "candidate.tif", "float32", 0.5)
    result = validate(candidate, sample)
    assert result["validator"] == "gems88-format-audit-v3"
    assert result["checks"]["dtype_float32"] is True
    assert result["format_valid"] is True
    assert result["submission_ready"] is False
    assert validate_artifact(candidate, sample)["ok"] is True


@pytest.mark.parametrize("optimized", [False, True])
def test_cli_rejects_float64_under_normal_and_optimized_python(tmp_path, optimized):
    sample = write_raster(tmp_path / "sample.tif", "float32")
    candidate = write_raster(tmp_path / "candidate.tif", "float64")
    command = [sys.executable] + (["-O"] if optimized else []) + [
        str(ROOT / "scripts/validate_artifact.py"), str(candidate),
        "--template", str(sample),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 1, completed.stderr
    report = json.loads(completed.stdout)
    assert report["checks"]["dtype_float32"] is False
    assert report["format_valid"] is False
    assert report["footprint_audit"]["strict_audit"] is False
    assert report["submission_ready"] is False
