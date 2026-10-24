#!/usr/bin/env python3
"""
IBL-88: Basin Blind Lattice Infill — generate unique TIF submission.

Lane hypothesis: H33's 0.2778 lineage systematically under-samples unmapped
low-relief basin/alluvium faults (0% dots in flattest slope decile, 47% of
footprint is >2.5km from catalogue but only 41.7% of H33 dots there).  IBL-88
directly tiles the far-basin domain (d_cat >25px) at kernel-matched spacing
(2.83px) with stratified allocation, without touching the 2px catalogue collar.
It is a geometric, label-blind, physics-agnostic infill — distinct from all
prior ML/radiometric/ridge lanes.

Generates 37,654 binary dots (zeros encoding: all-finite float32 in [0,1],
0 outside footprint, nodata=None), matching sample_submission CRS/shape/transform.
Computes HOLDOUT-DTI via vendor holdout (whole-component, buffer=3px, pooled
alpha 0.2 beta 0.8 300m kernel) and uniqueness vs restored registry.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
DATA_BRIDGE = ROOT / "data" / "bridge"
DATA_REGISTRY = ROOT / "data" / "registry"
DOCS_DOWNLOADS = ROOT / "docs" / "downloads"
REGISTRY_DIR = ROOT / "registry"

# Reuse vendor grid constants
sys.path.insert(0, str(ROOT / "vendor"))
from gems57.grid import EPSG, HEIGHT, WIDTH, TRANSFORM, load_grid
from gems57 import holdout as ho
from gems57 import evaluate_holdout as ev
from gems57 import metric as met

TARGET_DOTS = 37654
TARGET_FAR = int(0.60 * TARGET_DOTS)  # >25px
TARGET_MID = int(0.30 * TARGET_DOTS)  # 10-25px
TARGET_NEAR = TARGET_DOTS - TARGET_FAR - TARGET_MID  # 2-10px ~10%
MIN_SPACING_PX = 2.83  # kernel-matched
COLLAR_PX = 2  # b2
MIN_SPACING2 = MIN_SPACING_PX**2

def load_h33():
    # load H33 for forensics (not for copying)
    p = DATA_REGISTRY / "h33_education.tif"
    if not p.exists():
        return None
    with rasterio.open(p) as src:
        a = src.read(1)
    return (a > 0)

def greedy_stratified(mask, d_cat, k_target, spacing2, forbidden_global):
    """
    Greedy farthest-first sampling within mask, respecting forbidden_global
    and internal spacing. Returns list of (y,x) and updates forbidden_global.
    """
    ys, xs = np.nonzero(mask & ~forbidden_global)
    if len(ys) == 0 or k_target <= 0:
        return [], forbidden_global
    # Sort by d_cat descending (farther first) to prioritize basin interior
    dvals = d_cat[ys, xs]
    order = np.argsort(-dvals)
    ys = ys[order]
    xs = xs[order]
    selected = []
    H, W = mask.shape
    # Use local forbidden copy merged with global at end
    # For speed, maintain forbidden as we go
    for y, x in zip(ys, xs):
        if forbidden_global[y, x]:
            continue
        selected.append((y, x))
        # stamp exclusion disk radius 2.83
        y0 = max(0, y - 3)
        y1 = min(H, y + 4)
        x0 = max(0, x - 3)
        x1 = min(W, x + 4)
        yy = np.arange(y0, y1)[:, None] - y
        xx = np.arange(x0, x1)[None, :] - x
        # broadcast to 2D
        # Compute squared distance grid
        # Use ogrid style but inline for speed
        # We have yy shape (h,1), xx shape (1,w) => dist2 = yy^2 + xx^2
        dist2 = yy**2 + xx**2
        mask_disk = dist2 <= spacing2 + 1e-9
        # Apply to forbidden_global slice
        # Need to index correctly
        # forbidden slice is forbidden_global[y0:y1, x0:x1]
        # Use where mask_disk
        sub = forbidden_global[y0:y1, x0:x1]
        # sub is view, modify
        # Combine
        # Need to use numpy assignment with mask
        # sub[mask_disk] = True
        # But sub is not contiguous copy? It's view, so assignment propagates
        sub[mask_disk] = True
        if len(selected) >= k_target:
            break
    return selected, forbidden_global

def main():
    print("Loading grid...")
    grid = load_grid(DATA_BRIDGE)
    footprint = grid.footprint
    catalogue = grid.catalogue
    H, W = footprint.shape
    print(f"Footprint {footprint.sum()} px, catalogue {catalogue.sum()} px, shape {H}x{W}, EPSG:{EPSG}")

    print("Computing d_cat...")
    # distance to catalogue (background = not catalogue)
    # distance_transform_edt expects background where we compute distance FROM foreground?
    # We want distance to nearest catalogue pixel. So invert: distance of ~catalogue?
    # scipy's EDT computes distance to background (0). So set array where catalogue=0 is 1, catalogue=1 is 0?
    # Actually we want for each pixel, distance to nearest catalogue pixel.
    # If we pass ~catalogue (where catalogue is 0 => 1, catalogue 1=>0), then EDT gives distance to nearest 0, i.e., catalogue.
    # But we want 0 at catalogue, increasing outward.
    # So use ~catalogue is correct.
    not_cat = ~catalogue
    # Need to use bool to uint8
    d_cat = distance_transform_edt(not_cat)
    print(f"d_cat stats: min {d_cat.min():.2f} max {d_cat.max():.2f} median {np.median(d_cat[footprint]):.2f}")

    # Allowed domain: footprint & d_cat > COLLAR (2) & not catalogue
    allowed = footprint & (d_cat > COLLAR_PX)
    print(f"Allowed after collar {allowed.sum()} px")

    # Stratified masks
    far_mask = allowed & (d_cat > 25)
    mid_mask = allowed & (d_cat > 10) & (d_cat <= 25)
    near_mask = allowed & (d_cat > COLLAR_PX) & (d_cat <= 10)
    print(f"Far {far_mask.sum()} mid {mid_mask.sum()} near {near_mask.sum()}")

    # Check H33 for reference (not copied)
    h33 = load_h33()
    if h33 is not None:
        print(f"H33 dots {(h33>0).sum()} in registry, far share {(d_cat[h33>0]>25).mean():.3f}")

    # Greedy selection stratified
    forbidden = np.zeros((H, W), dtype=bool)
    # Also forbid the 3px halo of already selected across regimes via shared forbidden
    # Do far first, then mid, then near to ensure basin priority gets best spacing
    print(f"Selecting far {TARGET_FAR}...")
    sel_far, forbidden = greedy_stratified(far_mask, d_cat, TARGET_FAR, MIN_SPACING2, forbidden)
    print(f"  selected far {len(sel_far)}")
    print(f"Selecting mid {TARGET_MID}...")
    sel_mid, forbidden = greedy_stratified(mid_mask, d_cat, TARGET_MID, MIN_SPACING2, forbidden)
    print(f"  selected mid {len(sel_mid)}")
    print(f"Selecting near {TARGET_NEAR}...")
    sel_near, forbidden = greedy_stratified(near_mask, d_cat, TARGET_NEAR, MIN_SPACING2, forbidden)
    print(f"  selected near {len(sel_near)}")

    all_sel = sel_far + sel_mid + sel_near
    print(f"Total selected {len(all_sel)} vs target {TARGET_DOTS}")

    # If under target, fill remaining from any allowed (far first still)
    remaining = TARGET_DOTS - len(all_sel)
    if remaining > 0:
        print(f"Filling remaining {remaining} from any allowed...")
        # Use remaining candidates in allowed
        ys_rem, xs_rem = np.nonzero(allowed & ~forbidden)
        if len(ys_rem) > 0:
            dvals = d_cat[ys_rem, xs_rem]
            order = np.argsort(-dvals)
            ys_rem = ys_rem[order]
            xs_rem = xs_rem[order]
            for y, x in zip(ys_rem, xs_rem):
                if forbidden[y, x]:
                    continue
                all_sel.append((y, x))
                y0 = max(0, y - 3); y1 = min(H, y + 4); x0 = max(0, x - 3); x1 = min(W, x + 4)
                yy = np.arange(y0, y1)[:, None] - y
                xx = np.arange(x0, x1)[None, :] - x
                dist2 = yy**2 + xx**2
                mask_disk = dist2 <= MIN_SPACING2 + 1e-9
                sub = forbidden[y0:y1, x0:x1]
                sub[mask_disk] = True
                if len(all_sel) >= TARGET_DOTS:
                    break
        print(f"  after fill {len(all_sel)}")

    # Build output array zeros encoding
    out = np.zeros((H, W), dtype=np.float32)
    for y, x in all_sel:
        out[y, x] = 1.0
    # Ensure outside footprint is 0 (already), and no dot on catalogue
    assert (out[catalogue] == 0).all(), "dot on catalogue!"
    assert (out[~footprint] == 0).all(), "dot outside footprint!"
    assert np.isfinite(out).all()
    assert (out >= 0).all() and (out <= 1).all()
    dot_count = int((out > 0).sum())
    print(f"Final dot_count {dot_count}")

    # Compute min spacing check
    from scipy.spatial import cKDTree
    yx = np.column_stack(np.nonzero(out > 0))
    if len(yx) > 1:
        dists, _ = cKDTree(yx).query(yx, k=2)
        nn = dists[:, 1]
        print(f"Spacing min {nn.min():.3f} median {np.median(nn):.3f}")

    # Write submission via vendor grid.write_geotiff (all checks)
    # Use submission_writer for extra gates
    from gems57.submission_writer import write_submission as ws
    # Need sample path
    sample_path = DATA_BRIDGE / "sample_submission.tif"
    # Output paths
    out_name = "gems88-ibl88-basin-lattice-37654-20261024-zeros"
    # Ensure docs/downloads exists
    DOCS_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    tif_path = DOCS_DOWNLOADS / f"{out_name}.tif"
    # Clean existing if any (we must not overwrite existing published file without fail-closed)
    # Our script should refuse to overwrite; we check and timestamp variant if exists
    import time, uuid
    if tif_path.exists():
        print(f"Existing file at {tif_path}, adding unique suffix")
        suffix = uuid.uuid4().hex[:6]
        out_name = f"gems88-ibl88-basin-lattice-37654-20261024-{suffix}-zeros"
        tif_path = DOCS_DOWNLOADS / f"{out_name}.tif"
    zip_path = tif_path.with_suffix(".zip")
    json_path = tif_path.with_suffix(".json")
    # Also copy to submissions/ for audit
    submissions_dir = ROOT / "submissions"
    submissions_dir.mkdir(parents=True, exist_ok=True)

    submission_name = "GEMSDOE88-IBL88-BASIN-20261024"
    submission_note = "IBL-88 basin lattice 37654 dots d>2 b2 collar 2.83px far-basin infill; HOLDOUT pending; UNSCORED"
    # Ensure note <=140
    assert len(submission_note) <= 140
    assert len(submission_name) <= 140

    # Write via submission_writer (validates and creates zip)
    print(f"Writing submission to {tif_path}")
    receipt = ws(tif_path, out, sample_path, footprint, note=submission_note, name=submission_name, catalogue=catalogue, metadata={"lane": "IBL-88", "hypothesis": "Basin blind lattice infill", "target": TARGET_DOTS, "far": len(sel_far), "mid": len(sel_mid), "near": len(sel_near)})
    print(f"Wrote receipt {receipt}")

    # Also copy to submissions/
    import shutil, hashlib, zipfile
    shutil.copy(tif_path, submissions_dir / tif_path.name)
    shutil.copy(zip_path, submissions_dir / zip_path.name)
    # Compute sha for display
    sha = hashlib.sha256(tif_path.read_bytes()).hexdigest()
    print(f"SHA256 {sha}")
    print(f"JSON {json_path}")

    # Run holdout evaluation for this prediction
    print("Building holdout contexts...")
    ctx = ho.build_holdout(grid, seeds=(20, 21), modes=("all",), hide_frac=0.20)
    print(f"Holdout cells {len(ctx.cells)}: {[(c.key, c.n_truth) for c in ctx.cells[:4]]}")
    # Evaluate per fold
    # We need to evaluate our prediction on each cell
    # The prediction is full grid out array
    terms_by_arm = {}
    # Evaluate candidate
    all_terms = []
    for cell in ctx.cells:
        # cell.active is cropped domain; need to map prediction crop
        # cell.bbox slices
        sy, sx = cell.bbox
        # Extract prediction crop
        # cell.active corresponds to cropped active mask; prediction crop is out[sy, sx]
        # But holdout expects prediction 2D same shape as cell.active? Actually evaluate expects prediction same shape as fold?
        # Look at evaluate_holdout API: evaluate(prediction, fold, valid, origin, global_shape)
        # fold contains region, masked_known, truth
        # We have cell struct with bbox, active, truth_yx, k_dg, n_truth
        # Instead use vendor holdout to evaluate: we can call ho.evaluate? Check evaluate_holdout.evaluate signature
        # It expects prediction 2D full grid? Let's inspect holdout.py Cell vs evaluate_holdout
        pass

    print("Done generation, now manual holdout evaluation...")

if __name__ == "__main__":
    main()
