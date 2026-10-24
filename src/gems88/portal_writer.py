"""Write a submission GeoTIFF that mirrors the official ``sample_submission.tif`` layout.

Portal error seen by the owner: "Predicted values must be in range [0, 1]".  The cause is
UNPROVEN (organiser code is not public).  Three suspects are removed at once:
  1. NaN anywhere in the array (a NaN fails ``(a >= 0) & (a <= 1)`` when nodata is undeclared),
  2. values a hair outside [0, 1] (clipped and asserted here),
  3. reader-incompatible layout (earlier files were tiled + DEFLATE; the official sample is
     LZW, striped, 1-row strips, classic TIFF, float32, no predictor) -> the layout is mirrored.
Outside the footprint the file holds 0.0 (finite); the public spec permits "null or nan" there,
and a zero prediction contributes nothing to TP/FP/FN.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import rasterio

ZIP_EPOCH = (2026, 10, 24, 0, 0, 0)  # fixed timestamp -> byte-reproducible ZIP


def write_portal_tif(path, array, sample_path, footprint) -> Path:
    path = Path(path)
    a = np.asarray(array, np.float64)
    if a.ndim != 2:
        raise ValueError("array must be 2-D")
    if not np.isfinite(a[footprint]).all():
        raise ValueError("non-finite prediction inside the footprint")
    a = np.where(footprint, a, 0.0)
    if (a < -1e-9).any() or (a > 1 + 1e-9).any():
        raise ValueError("values outside [0, 1] before clipping")
    a = np.clip(a, 0.0, 1.0).astype(np.float32)
    with rasterio.open(sample_path) as ref:
        if ref.shape != a.shape:
            raise ValueError(f"shape {a.shape} != sample {ref.shape}")
        prof = dict(driver="GTiff", height=ref.height, width=ref.width, count=1, dtype="float32",
                    crs=ref.crs, transform=ref.transform, compress="lzw", tiled=False,
                    blockysize=ref.block_shapes[0][0], nodata=None, BIGTIFF="NO")
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **prof) as ds:
        ds.write(a, 1)
    return path


def write_single_member_zip(zip_path, tif_path) -> Path:
    zip_path, tif_path = Path(zip_path), Path(tif_path)
    info = zipfile.ZipInfo(tif_path.name, date_time=ZIP_EPOCH)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr(info, tif_path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return zip_path
