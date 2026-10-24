"""H88-VESS: Frangi/Sato vesselness of potential-field gradient magnitudes.

12 label-blind channels from four SHA-pinned competition bands
(B2 ``rtp``, B12 ``det_elev``, B13 ``iso_grav_anom``, B15
``depth_to_base_surf``).  ``existing_faults.tif`` is never read here.

For each field f the gradient-magnitude field ``g = |grad f|`` turns a
basement step into a *ridge* of g.  The scale-normalised Hessian of g at
sigma in {1.5, 3.5} px has eigenvalues lam1, lam2 (|lam1| <= |lam2|).
Frangi vesselness

    Rb = |lam1| / |lam2|          (0 = ideal line, 1 = blob)
    S  = sqrt(lam1^2 + lam2^2)    (structureness)
    V  = exp(-Rb^2 / (2 beta^2)) * (1 - exp(-S^2 / (2 c^2))),  beta = 0.5

with c the 90th percentile of S over the footprint, kept only on bright
ridges (lam2 < 0).  Cross-field min / geometric-mean at sigma=3.5 require
the same line in gravity, magnetics and basement depth; the signed
gravity-basement concordance and the structure-tensor orientation
coherence of the joint gradient field complete the 12 channels.

Memory: full-grid float32 planes (~49 MB each) are freed field by field;
output is a disk-backed (N_fp, 12) float32 memmap.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from . import edge

VESS_FEATURES: tuple[str, ...] = (
    "vess_grav_15",
    "vess_grav_35",
    "vess_rtp_15",
    "vess_rtp_35",
    "vess_zbase_15",
    "vess_zbase_35",
    "vess_elev_35",
    "vess_min_35",
    "vess_geomean_35",
    "vess_polarity_grav_zbase",
    "vess_orient_coh_35",
    "vess_max_15",
)

VESS_SCHEMA_VERSION = "vess88-12ch-v1"
_BETA = 0.5
# band index -> short name (tags verified against EXPECTED tags at build)
_BANDS = ((13, "iso_grav_anom"), (2, "rtp"), (15, "depth_to_base_surf"), (12, "det_elev"))


def _hessian(g: np.ndarray, sigma: float):
    """Scale-normalised Hessian components of g at `sigma`."""
    s2 = np.float32(sigma * sigma)
    hxx = ndi.gaussian_filter(g, sigma=sigma, order=(0, 2), mode="nearest") * s2
    hyy = ndi.gaussian_filter(g, sigma=sigma, order=(2, 0), mode="nearest") * s2
    hxy = ndi.gaussian_filter(g, sigma=sigma, order=(1, 1), mode="nearest") * s2
    return hxx.astype(np.float32), hyy.astype(np.float32), hxy.astype(np.float32)


def vesselness(g: np.ndarray, footprint: np.ndarray, sigma: float) -> np.ndarray:
    """Frangi bright-ridge vesselness of gradient-magnitude field g."""
    hxx, hyy, hxy = _hessian(np.asarray(g, np.float32), sigma)
    tr = hxx + hyy
    disc = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy**2, 0.0))
    la = 0.5 * (tr - disc)  # algebraically smaller
    lb = 0.5 * (tr + disc)  # algebraically larger
    # order by magnitude: lam1 = smaller |.|, lam2 = larger |.|
    swap = np.abs(la) > np.abs(lb)
    lam1 = np.where(swap, lb, la)
    lam2 = np.where(swap, la, lb)
    del hxx, hyy, hxy, tr, disc, la, lb, swap
    s_val = np.sqrt(lam1**2 + lam2**2)
    sample = s_val[footprint][::37]
    c = float(np.percentile(sample, 90.0)) if sample.size else 0.0
    c = max(c, 1e-12)
    rb = np.abs(lam1) / (np.abs(lam2) + np.float32(1e-12))
    v = np.exp(-(rb**2) / np.float32(2.0 * _BETA * _BETA)) * (
        1.0 - np.exp(-(s_val**2) / np.float32(2.0 * c * c))
    )
    v = np.where(lam2 < 0, v, np.float32(0.0))  # bright ridge of |grad f| only
    return np.clip(v, 0.0, 1.0).astype(np.float32)


def _grad_mag(clean: np.ndarray, footprint: np.ndarray, sigma: float = 1.0):
    gy, gx = edge.derivatives(clean, footprint, sigma=sigma)
    return np.hypot(gy, gx).astype(np.float32), gy, gx


def build_or_load_vess_memmap(root: Path, grid, cache_dir: Path):
    """Build or reload disk-backed (N_fp, 12) float32 memmap of VESS features."""
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / "x_vess_12ch_v1.dat"
    meta_path = cache_dir / "x_vess_12ch_v1.json"
    feat_path = root / "data/training_features.tif"
    digest = hashlib.sha256(feat_path.read_bytes()).hexdigest() if feat_path.is_file() else "missing"

    if dat_path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("schema") == VESS_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, len(VESS_FEATURES)]
            and meta.get("features") == list(VESS_FEATURES)
            and meta.get("training_features_sha256") == digest
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, len(VESS_FEATURES))), meta

    fields: dict[str, np.ndarray] = {}
    grads: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    with rasterio.open(feat_path) as src:
        if (src.height, src.width) != grid.shape:
            raise ValueError("training_features.tif grid mismatch")
        for idx, want in _BANDS:
            got = src.tags(idx).get("band_name", "")
            if got != want:
                raise ValueError(f"band {idx}: expected {want!r}, got {got!r}")
            clean, _ = edge.clean_band(src.read(idx), fp)
            fields[want] = clean

    gmag: dict[str, np.ndarray] = {}
    for name, clean in fields.items():
        g, gy, gx = _grad_mag(clean, fp, sigma=1.0)
        gmag[name] = g
        grads[name] = (gy, gx)

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, len(VESS_FEATURES)))
    v35: dict[str, np.ndarray] = {}
    v15: dict[str, np.ndarray] = {}
    col = {"iso_grav_anom": 0, "rtp": 2, "depth_to_base_surf": 4}
    for name, c0 in col.items():
        for j, sigma in enumerate((1.5, 3.5)):
            v = vesselness(gmag[name], fp, sigma)
            mm[:, c0 + j] = v[ys, xs]
            (v15 if sigma == 1.5 else v35)[name] = v
    v_elev = vesselness(gmag["det_elev"], fp, 3.5)
    mm[:, 6] = v_elev[ys, xs]
    del v_elev

    g35 = np.stack([v35["iso_grav_anom"], v35["rtp"], v35["depth_to_base_surf"]])
    mm[:, 7] = g35.min(axis=0)[ys, xs]
    mm[:, 8] = np.cbrt(np.maximum(g35[0] * g35[1] * g35[2], 0.0))[ys, xs]
    del g35
    mm[:, 11] = np.maximum(np.maximum(v15["iso_grav_anom"], v15["rtp"]), v15["depth_to_base_surf"])[ys, xs]
    del v15, v35

    # signed gravity <-> basement step concordance: cos(grad grav, grad zbase)
    # weighted by basement gradient strength (deep-side step polarity is
    # learnable by the downstream GBDT; the channel itself is sign-carrying)
    gy_g, gx_g = grads["iso_grav_anom"]
    gy_z, gx_z = grads["depth_to_base_surf"]
    gz_mag = gmag["depth_to_base_surf"]
    cos_gz = (gy_g * gy_z + gx_g * gx_z) / (
        np.hypot(gy_g, gx_g) * np.maximum(gz_mag, np.float32(1e-12)) + np.float32(1e-12)
    )
    mm[:, 9] = (cos_gz * np.log1p(gz_mag))[ys, xs].astype(np.float32)
    del gy_g, gx_g, gy_z, gx_z, cos_gz

    # orientation coherence of the joint (grav+zbase) gradient-magnitude
    # structure tensor at sigma=3.5 smoothing
    joint = (gmag["iso_grav_anom"] + gz_mag).astype(np.float32)
    jy, jx = np.gradient(ndi.gaussian_filter(joint, sigma=1.0, mode="nearest"))
    jxx = ndi.gaussian_filter(jx * jx, sigma=3.5, mode="nearest")
    jyy = ndi.gaussian_filter(jy * jy, sigma=3.5, mode="nearest")
    jxy = ndi.gaussian_filter(jx * jy, sigma=3.5, mode="nearest")
    del joint, jy, jx
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy**2, 0.0))
    lmax = 0.5 * (jxx + jyy + disc)
    lmin = 0.5 * (jxx + jyy - disc)
    coh = (lmax - lmin) / (lmax + lmin + np.float32(1e-12))
    mm[:, 10] = np.clip(coh, 0.0, 1.0)[ys, xs].astype(np.float32)
    del jxx, jyy, jxy, disc, lmax, lmin, coh, gz_mag, gmag, fields, grads

    mm.flush()
    arr = np.asarray(mm)
    if not np.isfinite(arr).all():
        raise AssertionError("non-finite VESS channel values")
    meta = {
        "schema": VESS_SCHEMA_VERSION,
        "shape": [n_fp, len(VESS_FEATURES)],
        "features": list(VESS_FEATURES),
        "training_features_sha256": digest,
        "bands": {str(k): v for k, v in _BANDS},
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, len(VESS_FEATURES))), meta
