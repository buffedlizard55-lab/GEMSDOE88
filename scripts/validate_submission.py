#!/usr/bin/env python3
"""Strict, local GeoTIFF format/range gate for GEMS submissions.

This validates the raster contract only. It does not run the competition metric,
prove uniqueness, detect leakage, or establish organizer acceptance.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import rasterio
except ImportError as exc:  # pragma: no cover - message exercised by CLI users
    raise SystemExit(
        "Missing validation dependency. Install with: "
        "python -m pip install -r requirements-validation.txt"
    ) from exc


def _transform_values(transform: Any) -> list[float]:
    """Return the six affine coefficients in GDAL order."""
    return [float(v) for v in transform.to_gdal()]


def validate(prediction_path: Path, reference_path: Path) -> dict[str, Any]:
    """Validate one prediction raster against the supplied official grid template."""
    report: dict[str, Any] = {
        "prediction": str(prediction_path),
        "reference": str(reference_path),
        "checks": {},
        "errors": [],
        "status": "FAIL",
    }

    for label, path in (("prediction", prediction_path), ("reference", reference_path)):
        if not path.is_file():
            report["errors"].append(f"{label} file does not exist: {path}")
    if report["errors"]:
        return report

    try:
        with rasterio.open(reference_path) as ref, rasterio.open(prediction_path) as pred:
            report["prediction_band_count"] = pred.count
            report["reference_band_count"] = ref.count
            report["prediction_shape"] = [int(pred.height), int(pred.width)]
            report["reference_shape"] = [int(ref.height), int(ref.width)]
            report["prediction_crs"] = pred.crs.to_string() if pred.crs else None
            report["reference_crs"] = ref.crs.to_string() if ref.crs else None
            report["prediction_transform"] = _transform_values(pred.transform)
            report["reference_transform"] = _transform_values(ref.transform)

            checks = report["checks"]
            checks["single_band"] = pred.count == 1
            checks["reference_single_band"] = ref.count == 1
            checks["crs_match"] = pred.crs is not None and pred.crs == ref.crs
            checks["shape_match"] = (pred.height, pred.width) == (ref.height, ref.width)
            checks["transform_match"] = pred.transform == ref.transform

            if pred.count != 1:
                report["errors"].append(f"prediction must have exactly one band; found {pred.count}")
            if ref.count < 1:
                report["errors"].append("reference has no raster bands")
            if not checks["crs_match"]:
                report["errors"].append("prediction CRS does not match reference CRS")
            if not checks["shape_match"]:
                report["errors"].append("prediction dimensions do not match reference dimensions")
            if not checks["transform_match"]:
                report["errors"].append("prediction geotransform does not exactly match reference")

            if pred.count == 1 and ref.count >= 1 and checks["shape_match"]:
                values = pred.read(1, masked=False)
                footprint = ref.read_masks(1) > 0
                finite = np.isfinite(values)
                in_range = finite & (values >= 0.0) & (values <= 1.0)
                footprint_nan = int(np.count_nonzero(footprint & np.isnan(values)))
                footprint_inf = int(np.count_nonzero(footprint & np.isinf(values)))
                footprint_out_of_range = int(
                    np.count_nonzero(footprint & finite & ((values < 0.0) | (values > 1.0)))
                )
                global_nonfinite = int(values.size - np.count_nonzero(finite))
                global_out_of_range = int(
                    np.count_nonzero(finite & ((values < 0.0) | (values > 1.0)))
                )

                checks["no_nan_inside_footprint"] = footprint_nan == 0
                checks["no_inf_inside_footprint"] = footprint_inf == 0
                checks["footprint_values_in_0_1"] = footprint_out_of_range == 0
                checks["all_values_finite"] = global_nonfinite == 0
                checks["all_values_in_0_1"] = global_out_of_range == 0
                report["footprint_pixel_count"] = int(np.count_nonzero(footprint))
                report["footprint_nan_count"] = footprint_nan
                report["footprint_inf_count"] = footprint_inf
                report["footprint_out_of_range_count"] = footprint_out_of_range
                report["global_nonfinite_count"] = global_nonfinite
                report["global_out_of_range_count"] = global_out_of_range
                finite_values = values[finite]
                report["minimum"] = float(finite_values.min()) if finite_values.size else None
                report["maximum"] = float(finite_values.max()) if finite_values.size else None

                for key, count in (
                    ("NaN inside footprint", footprint_nan),
                    ("infinity inside footprint", footprint_inf),
                    ("out-of-range values inside footprint", footprint_out_of_range),
                    ("non-finite values anywhere in raster", global_nonfinite),
                    ("values outside [0, 1] anywhere in raster", global_out_of_range),
                ):
                    if count:
                        report["errors"].append(f"{key}: {count}")
            else:
                checks["no_nan_inside_footprint"] = False
                checks["all_values_in_0_1"] = False
                report["errors"].append("pixel checks skipped because band count or dimensions are invalid")

    except Exception as exc:
        report["errors"].append(f"could not read GeoTIFF: {type(exc).__name__}: {exc}")

    report["status"] = "PASS" if not report["errors"] and all(report["checks"].values()) else "FAIL"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", required=True, type=Path, help="candidate single-band GeoTIFF")
    parser.add_argument("--reference", required=True, type=Path, help="official sample-submission GeoTIFF")
    parser.add_argument("--report", type=Path, help="optional path to write the JSON report")
    args = parser.parse_args()

    result = validate(args.prediction, args.reference)
    rendered = json.dumps(result, indent=2, allow_nan=False)
    print(rendered)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
