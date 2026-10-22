import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.validate_submission import validate


class ValidateSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.reference = self.root / "sample.tif"
        self.prediction = self.root / "prediction.tif"
        self.profile = {
            "driver": "GTiff",
            "height": 4,
            "width": 5,
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:32611",
            "transform": from_origin(100, 200, 10, 10),
            "nodata": -9999.0,
        }
        reference_data = np.array(
            [[1, 1, 1, 1, -9999], [1, 1, 1, 1, -9999], [1, 1, 1, 1, -9999], [1, 1, 1, 1, -9999]],
            dtype="float32",
        )
        with rasterio.open(self.reference, "w", **self.profile) as dst:
            dst.write(reference_data, 1)

    def tearDown(self):
        self.temp.cleanup()

    def write_prediction(self, data, *, transform=None, count=1):
        profile = dict(self.profile)
        profile["count"] = count
        if transform is not None:
            profile["transform"] = transform
        with rasterio.open(self.prediction, "w", **profile) as dst:
            if count == 1:
                dst.write(np.asarray(data, dtype="float32"), 1)
            else:
                for band in range(1, count + 1):
                    dst.write(np.asarray(data, dtype="float32"), band)

    def test_valid_single_band_grid_and_range_passes(self):
        data = np.zeros((4, 5), dtype="float32")
        data[0, 0] = 1.0
        self.write_prediction(data)
        report = validate(self.prediction, self.reference)
        self.assertEqual(report["status"], "PASS", report)
        self.assertTrue(report["checks"]["no_nan_inside_footprint"])
        self.assertTrue(report["checks"]["all_values_in_0_1"])

    def test_out_of_range_value_outside_footprint_fails(self):
        data = np.zeros((4, 5), dtype="float32")
        data[0, 4] = 1.01  # template marks this pixel outside the valid footprint
        self.write_prediction(data)
        report = validate(self.prediction, self.reference)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["all_values_in_0_1"])

    def test_nan_inside_footprint_fails(self):
        data = np.zeros((4, 5), dtype="float32")
        data[1, 1] = np.nan
        self.write_prediction(data)
        report = validate(self.prediction, self.reference)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["no_nan_inside_footprint"])

    def test_transform_mismatch_fails(self):
        data = np.zeros((4, 5), dtype="float32")
        self.write_prediction(data, transform=from_origin(101, 200, 10, 10))
        report = validate(self.prediction, self.reference)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["transform_match"])

    def test_multiband_prediction_fails(self):
        data = np.zeros((4, 5), dtype="float32")
        self.write_prediction(data, count=2)
        report = validate(self.prediction, self.reference)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["single_band"])


if __name__ == "__main__":
    unittest.main()
