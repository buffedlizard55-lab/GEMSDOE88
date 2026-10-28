"""The old compatibility diagnostics must not claim uniqueness from bad data."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems88 import gate


GRID = (20, 20)


def put(path, values):
    with rasterio.open(path, "w", driver="GTiff", height=20, width=20, count=1,
                       dtype="float32", crs="EPSG:32611",
                       transform=from_origin(0, 2000, 100, 100)) as dst:
        dst.write(values.astype(np.float32), 1)


def test_compatibility_diagnostic_does_not_clear_nan_prior(tmp_path):
    fp = np.ones(GRID, bool)
    mine = np.zeros(GRID, np.float32)
    mine[2, 2] = 1
    prior = np.zeros(GRID, np.float32)
    prior[2, 2] = np.nan
    prior[17, 17] = 1
    candidate, bad = tmp_path / "candidate.tif", tmp_path / "prior.tif"
    put(candidate, mine)
    put(bad, prior)
    report = gate.uniqueness_report(candidate, [("prior", bad)], fp, surface=mine)
    assert report["unique_literal"] is False
    assert report["registry_complete"] is False
    assert report["missing"] == 1
    assert "error" in report["rows"][0]


def test_compatibility_rejects_constant_rank_vectors():
    with pytest.raises(ValueError, match="(?i)(undefined|constant)"):
        gate._pearson(np.zeros(4), np.arange(4))
