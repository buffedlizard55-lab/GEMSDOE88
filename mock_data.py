import os
import rasterio
from affine import Affine
import numpy as np
from pathlib import Path

os.makedirs('data/bridge', exist_ok=True)
os.makedirs('data/registry', exist_ok=True)

HEIGHT = 3730
WIDTH = 3292
TRANSFORM = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)

# Create a mock footprint mask (circle in the center)
Y, X = np.ogrid[:HEIGHT, :WIDTH]
dist = np.sqrt((X - WIDTH/2)**2 + (Y - HEIGHT/2)**2)
footprint = dist < 1000

# Write sample_submission.tif
meta = {
    'driver': 'GTiff',
    'height': HEIGHT,
    'width': WIDTH,
    'count': 1,
    'dtype': 'float32',
    'crs': 'EPSG:32611',
    'transform': TRANSFORM,
    'nodata': np.nan,
    'compress': 'deflate'
}
with rasterio.open('data/bridge/sample_submission.tif', 'w', **meta) as dst:
    arr = np.where(footprint, 0.0, np.nan).astype(np.float32)
    dst.write(arr, 1)

# Write existing_faults.tif
meta['nodata'] = None
meta['dtype'] = 'float32'
with rasterio.open('data/bridge/existing_faults.tif', 'w', **meta) as dst:
    arr = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    # fake some faults
    arr[1500:2000, 1500] = 1.0
    dst.write(arr, 1)
