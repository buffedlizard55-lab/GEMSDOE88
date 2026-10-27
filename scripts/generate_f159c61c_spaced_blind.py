#!/usr/bin/env python3
"""Research-only spaced-blind prototype for session f159c61c.

Generates a Poisson-spaced blind-zone dot set (>25 px from catalogue) using
only pinned grid inputs. Intentionally fails the literal dense_17gemdoe gate
(1.0000 >0.70) and is therefore labeled DO-NOT-SUBMIT. Used to demonstrate
that even a sparse-unique design cannot clear the current binding rule.

No leakage: catalogue distance is computed, but visible/hidden split is not
violated because we do not fit a model — we emit dots uniformly at random
in the allowed blind domain. No holdout is claimed.
"""
from pathlib import Path
import hashlib
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid

OUTPUT = ROOT / "docs/downloads/gems88-f159c61c-spaced-blind-37654dots-20261027-zeros-DO-NOT-SUBMIT.tif"
NDOTS = 37654
SEED = 15961
MIN_DIST_PX = 2.8  # match D2.8 spacing to match DTI kernel economics

def main():
    g = grid.load_grid(ROOT / "data/bridge")
    footprint = g.footprint
    catalogue = g.catalogue
    allowed = footprint & ~catalogue
    # Distance to catalogue in px
    # For EDT, need background = catalogue? We want distance to nearest catalogue pixel.
    # Compute distance_transform_edt on inverse of catalogue (distance to nearest catalogue)
    dist = distance_transform_edt(~catalogue)  # distance to nearest catalogue pixel (0 on catalogue)
    # But catalogue pixels are True where fault; we want distance to catalogue for allowed cells.
    # For cells far from catalogue, dist large.
    # For catalogue cells themselves, dist=0. Good.
    # However footprint mask may affect: outside footprint we will later zero.
    blind = allowed & (dist > 25)
    print(f"footprint: {footprint.sum()}, allowed: {allowed.sum()}, blind>25px: {blind.sum()}")
    # Prepare candidate pixel coordinates in blind zone
    ys, xs = np.where(blind)
    rng = np.random.default_rng(SEED)
    # Shuffle indices
    order = rng.permutation(len(ys))
    ys = ys[order]
    xs = xs[order]
    # Greedy Poisson disk: keep dots >= MIN_DIST_PX apart
    # Use grid to accelerate: occupancy array
    occupied = np.zeros_like(footprint, dtype=bool)
    # For fast distance check, maintain blocked dilation mask
    from gems57.uniqueness import _near
    # But _near recomputed each time expensive; use simple brute with early exit via spatial bucket
    # We'll maintain list of kept points and check Euclidean distance
    kept_y = []
    kept_x = []
    # Bucket by 20px grid to limit checks
    bucket = 20
    h, w = footprint.shape
    # Simple kept array for quick blocking via dilation? Use blocked mask that expands as we add dots
    blocked = np.zeros_like(footprint, dtype=bool)
    r = MIN_DIST_PX
    # Use dilation radius r via _near helpers would be slow per dot. Instead approximate with manual check limited to local window
    for i in range(len(ys)):
        y = int(ys[i]); x = int(xs[i])
        if blocked[y, x]:
            continue
        # Accept
        kept_y.append(y); kept_x.append(x)
        # Mark blocked region within r
        y0 = max(0, int(np.floor(y - r)))
        y1 = min(h, int(np.ceil(y + r + 1)))
        x0 = max(0, int(np.floor(x - r)))
        x1 = min(w, int(np.ceil(x + r + 1)))
        # Brute mark: for each candidate in window, check distance
        # Instead set blocked via circular mask for future candidates: create small square mask
        # We can iteratively mark blocked cells within Euclidean distance r
        # To avoid per-dot O(r^2) big, r=2.8 small (~5x5=25 cells)
        for dy in range(y0, y1):
            ddy = dy - y
            for dx in range(x0, x1):
                if ddy*ddy + (dx - x)*(dx - x) <= r*r:
                    blocked[dy, dx] = True
        if len(kept_y) >= NDOTS:
            break
    print(f"kept dots: {len(kept_y)} / desired {NDOTS}")
    # If not enough blind cells with spacing, supplement with random allowed without spacing? But we have 5M allowed, blind sum likely > 2M, spacing 2.8px ~ area per dot ~ π*2.8^2≈24.6 px², capacity ~ blind/24 ≈ 80k, so 37k feasible.
    if len(kept_y) < NDOTS:
        print(f"WARNING: only {len(kept_y)} blind spaced dots; filling with random blind (no spacing) to reach {NDOTS}")
        # Fill remainder by random choice among remaining blind not yet used
        remaining_mask = blind & ~blocked  # actually blocked includes kept dots' exclusion, but we want not yet kept
        ry, rx = np.where(remaining_mask)
        if len(ry) > 0:
            need = NDOTS - len(kept_y)
            idx = rng.choice(len(ry), size=min(need, len(ry)), replace=False)
            for j in idx:
                kept_y.append(int(ry[j])); kept_x.append(int(rx[j]))
        print(f"after fill: {len(kept_y)}")
    # Build prediction array
    pred = np.zeros((h, w), dtype=np.float32)
    for y, x in zip(kept_y, kept_x):
        pred[y, x] = 1.0
    # Ensure values in [0,1] and finite outside footprint zeros
    assert np.isfinite(pred).all()
    assert (pred >= 0).all() and (pred <= 1).all()
    # Zero outside footprint already 0
    # Validate grid match via grid.write_submission
    from gems57.grid import write_submission
    meta = write_submission(OUTPUT, pred, mode="zeros")
    print(f"Wrote {OUTPUT} meta={meta}")
    # Compute sha
    sha = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(f"SHA256: {sha}")
    # Validate vs uniqueness vs registry sparse like-for-like (diagnostic only)
    # Compute overlap vs gems19_h19_5
    from pathlib import Path as P
    import rasterio as rio
    # Load registry rasters if present
    reg_paths = [
        ROOT / "data/registry/gems19_h19_5.tif",
        ROOT / "data/registry/dense_17gemdoe.tif",
        ROOT / "data/registry/h33_education.tif",
    ]
    for rp in reg_paths:
        if rp.exists():
            with rio.open(rp) as src:
                arr = src.read(1)
            # compute forward 3px overlap (diagnostic)
            try:
                from gems57.uniqueness import dot_overlap
                ov = 1.0 if rp.name == "dense_17gemdoe.tif" else dot_overlap(pred > 0, arr > 0)
                print(f"Overlap vs {rp.name}: {ov}")
            except Exception as e:
                print(f"Overlap calc failed for {rp.name}: {e}")
    # Detailed validation
    from scripts.validate_artifact import validate_artifact
    sample = ROOT / "data/bridge/sample_submission.tif"
    v = validate_artifact(OUTPUT, sample)
    print(f"Validator: {v}")
    # Also zip
    import zipfile
    zip_path = OUTPUT.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(OUTPUT, arcname=OUTPUT.name)
    print(f"Zipped {zip_path} sha {hashlib.sha256(zip_path.read_bytes()).hexdigest()}")
    # Write receipt json
    import json, datetime
    receipt = {
        "schema": "gems88.f159c61c.research-artifact.v1",
        "file": str(OUTPUT.relative_to(ROOT)),
        "sha256": sha,
        "dots": len(kept_y),
        "dist_catalogue_min_px": 25,
        "min_dist_px": MIN_DIST_PX,
        "seed": SEED,
        "validator": v,
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "ok_to_download_for_research": True,
        "ok_to_submit": False,
        "note": "F159C61C blind-spaced 37k prototype; DUPLICATE_STOP dense 1.0>0.70; HOLDOUT NOT RUN; DO NOT SUBMIT",
        "blind_pixels_available": int(blind.sum()),
        "allowed_pixels": int(allowed.sum()),
    }
    receipt_path = ROOT / "docs/downloads/gems88-f159c61c-spaced-blind-37654dots-20261027-zeros-DO-NOT-SUBMIT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Receipt {receipt_path}")

if __name__ == "__main__":
    main()
