#!/usr/bin/env python3
"""Add side-of-ridge features to the LBCAL-PX sample (downhill vs uphill neighbour of the H19-5 ridge).

Physical test: if expert fault traces sit at the BASE of the topographic break that the
ridge indicator marks, truth density should be higher on the downhill-adjacent pixels.
"""
import json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy.ndimage import distance_transform_edt
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lbcal_pixel import grid_masks, load_pred, L, H195, D  # noqa: E402

def side_maps(omega):
    h = load_pred(L / H195, omega) > 0
    d, (iy, ix) = distance_transform_edt(~h, return_indices=True)
    with rasterio.open(D / "geodawn_dem_a2_100m.tif") as ds:
        z = ds.read(1).astype(np.float32); nod = ds.nodata
    z[(z == nod) | ~np.isfinite(z)] = np.nan
    zr = z[iy, ix]
    adj = (d > 0) & (d <= 1.5)
    down = adj & (z < zr)
    up = adj & (z >= zr)
    return down, up, adj, d

if __name__ == "__main__":
    foot, cat, omega = grid_masks()
    z = np.load(L / "px_prep.npz")
    sy, sx = z["sy"], z["sx"]
    down, up, adj, d = side_maps(omega)
    ex = {"ridge_adj_down": down[sy, sx].astype(np.float32), "ridge_adj_up": up[sy, sx].astype(np.float32)}
    print({k: float(v.mean()) for k, v in ex.items()}, "adj frac", float(adj[sy, sx].mean()))
    np.savez_compressed(L / "px_extra.npz", names=np.array(list(ex)), Phi=np.column_stack(list(ex.values())))
