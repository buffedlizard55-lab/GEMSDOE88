"""Label-blind magnetic/gravity edge features on the competition grid.

Only the three named layers in the owner-mirrored competition feature stack are
read. Nodata/sentinel cells are imputed with a label-blind median *before*
Gaussian smoothing; weighted smoothing prevents a footprint boundary or a
single missing cell from becoming an artificial lineament. Nothing depends on
hidden, visible or full catalogue geometry (those are used only for fit masks).
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

BANDS = ((2, "rtp"), (13, "iso_grav_anom"), (15, "depth_to_base_surf"))
NAMES = ("rtp", "iso_grav_anom", "depth_to_base_surf", "log_rtp_edge",
         "log_gravity_edge", "edge_alignment", "joint_edge")


def clean_band(a: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    """Replace invalid pixels, clip 1st..99th percentile to resist grid artifacts."""
    a = np.asarray(a, np.float32)
    valid = footprint & np.isfinite(a) & (a > -1e30) & (a < 1e30)
    if not valid.any() or valid.shape != a.shape:
        raise ValueError("bad input band or footprint")
    sample = a.ravel()[np.flatnonzero(valid.ravel())[::41]]
    lo, med, hi = [float(x) for x in np.percentile(sample, [1, 50, 99])]
    filled = np.where(valid, a, med).astype(np.float32, copy=False)
    np.clip(filled, lo, hi, out=filled)
    return filled, dict(valid=int(valid.sum()), invalid_inside=int((footprint & ~valid).sum()),
                        clip01=lo, median=med, clip99=hi)


def derivatives(a: np.ndarray, footprint: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    """Smooth with a normalized kernel then take two signed spatial gradients."""
    if sigma <= 0 or a.shape != footprint.shape:
        raise ValueError("sigma/footprint mismatch")
    weight = footprint.astype(np.float32)
    numer = gaussian_filter(a * weight, sigma=sigma, mode="constant", output=np.float32)
    denom = gaussian_filter(weight, sigma=sigma, mode="constant", output=np.float32)
    smoothed = numer / np.maximum(denom, np.float32(1e-6))
    gy, gx = np.gradient(smoothed)
    return gy.astype(np.float32), gx.astype(np.float32)


def coedge_features(my: np.ndarray, mx: np.ndarray, gy: np.ndarray,
                    gx: np.ndarray) -> tuple[np.ndarray, ...]:
    """Magnitudes and |cos(theta)| plus their signed-gradient co-edge product.

    Alignment alone is not evidence of a fault: lithologic contacts can yield
    exactly the same feature. Zero-gradient pixels receive alignment zero.
    """
    if not (my.shape == mx.shape == gy.shape == gx.shape):
        raise ValueError("edge gradient shape mismatch")
    mag = np.hypot(my, mx)
    grav = np.hypot(gy, gx)
    align = np.abs(my * gy + mx * gx) / np.maximum(mag * grav, 1e-7)
    np.clip(align, 0, 1, out=align)
    log_mag = np.log1p(mag)
    log_grav = np.log1p(grav)
    joint = log_mag * log_grav * align
    return tuple(np.asarray(v, np.float32) for v in (log_mag, log_grav, align, joint))


def build_cache(src_file: Path, footprint: np.ndarray, dest: Path) -> dict:
    """Create label-blind 7-channel float32 memmap; raw data never enter Git."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    h, w = footprint.shape
    x = np.memmap(dest, dtype="float32", mode="w+", shape=(h*w, len(NAMES)))
    metadata = {"bands": {}, "names": NAMES,
                "description": "Band 2 RTP and band 13 gravity Gaussian-normalized gradients (2 and 3 px); band 15 sediment-cover covariate"}
    with rasterio.open(src_file) as source:
        if source.shape != footprint.shape or source.count < 15:
            raise ValueError("feature stack does not match grid/required bands")
        for col, (idx, expected) in enumerate(BANDS):
            # The organizer-mirrored TIFF's description contains explanatory prose;
            # its band_name tag is the exact machine-readable identifier.
            found = source.tags(idx).get('band_name')
            if found != expected:
                raise ValueError(f"band {idx}: expected tag {expected!r}, got {found!r}")
            clean, stats = clean_band(source.read(idx), footprint)
            x[:, col] = clean.ravel()
            metadata["bands"][expected] = {"index": idx, **stats}
            if idx in (2, 13):
                dy, dx = derivatives(clean, footprint, sigma=2.0 if idx == 2 else 3.0)
                if idx == 2:
                    my, mx = dy, dx
                else:
                    gy, gx = dy, dx
                del dy, dx
            del clean
    for col, feature in enumerate(coedge_features(my, mx, gy, gx), start=3):
        feature[~footprint] = 0
        if not np.isfinite(feature).all():
            raise ValueError(f"nonfinite feature {NAMES[col]}")
        x[:, col] = feature.ravel()
        del feature
    x.flush()
    del x, my, mx, gy, gx
    return metadata
