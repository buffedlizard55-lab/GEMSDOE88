"""MRR-BPR-88: catalogue-blind blockwise magnetic polarity residual features.

The transform uses only organizer-provided competition bands and never reads the
fault catalogue.  It removes a local 10 km nuisance relation between the
vertical magnetic gradient and broad magnetic fields before measuring narrow
negative (demagnetized) corridors.  The implementation is deterministic,
memory-bounded, and cached with input hashes and the complete parameter record.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, sobel, zoom

from .edge import clean_band

MRR_FEATURES: tuple[str, ...] = (
    "mrr_vg_block_residual",
    "mrr_demag_trough_hessian_s2",
    "mrr_demag_depth_weighted",
    "mrr_rtp_residual_crossgradient",
)

BLOCK_SIDE_PX = 100
RIDGE_LAMBDA = 0.05
COEF_SMOOTH_SIGMA_BLOCKS = 0.75


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _robust_standardize(a: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    vals = np.asarray(a, np.float32)[valid]
    q01, med, q99 = (float(x) for x in np.percentile(vals, [1.0, 50.0, 99.0]))
    scale = max((q99 - q01) / 4.6527, 1e-6)
    out = np.clip((np.asarray(a, np.float32) - med) / scale, -6.0, 6.0).astype(np.float32)
    out[~valid] = 0.0
    return out, {"q01": q01, "median": med, "q99": q99, "scale": scale}


def _hessian_trough(a: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """Positive principal curvature at a smoothed negative trough."""
    s = gaussian_filter(np.asarray(a, np.float32), sigma=sigma, mode="nearest")
    gy = sobel(s, axis=0, mode="nearest") * np.float32(0.125)
    gx = sobel(s, axis=1, mode="nearest") * np.float32(0.125)
    gyy = sobel(gy, axis=0, mode="nearest") * np.float32(0.125)
    gxx = sobel(gx, axis=1, mode="nearest") * np.float32(0.125)
    gxy = sobel(gy, axis=1, mode="nearest") * np.float32(0.125)
    tr = gxx + gyy
    rad = np.hypot(gxx - gyy, np.float32(2.0) * gxy)
    return (sigma * sigma * np.maximum(np.float32(0.0), np.float32(0.5) * (tr + rad))).astype(np.float32)


def _smooth_block_coefficients(coef: np.ndarray, has_data: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Normalized smooth + bilinear expansion of a coarse block coefficient."""
    weights = gaussian_filter(has_data.astype(np.float32), COEF_SMOOTH_SIGMA_BLOCKS, mode="nearest")
    numer = gaussian_filter(np.where(has_data, coef, 0.0).astype(np.float32), COEF_SMOOTH_SIGMA_BLOCKS, mode="nearest")
    smooth = np.divide(numer, np.maximum(weights, 1e-6), dtype=np.float32)
    expanded = zoom(smooth, (shape[0] / smooth.shape[0], shape[1] / smooth.shape[1]), order=1, mode="nearest")
    return expanded[: shape[0], : shape[1]].astype(np.float32, copy=False)


def compute_mrr_features(
    mag_anom: np.ndarray,
    rtp: np.ndarray,
    tmi_vg: np.ndarray,
    tmi: np.ndarray,
    depth_to_base: np.ndarray,
    valid: np.ndarray,
    *,
    block_side_px: int = BLOCK_SIDE_PX,
    ridge_lambda: float = RIDGE_LAMBDA,
) -> tuple[list[np.ndarray], dict]:
    """Compute the four preregistered MRR-BPR channels.

    Regression is entirely label/catalogue blind.  Each 10 km block solves a
    winsorized ridge regression ``tmi_vg ~ 1 + tmi + mag_anom``.  Coefficients
    are normalized-smoothed between blocks before the residual is calculated,
    preventing hard block seams from becoming candidate lineaments.
    """
    valid = np.asarray(valid, bool)
    if valid.ndim != 2 or not valid.any() or block_side_px <= 0 or ridge_lambda < 0:
        raise ValueError("invalid MRR grid or parameters")
    arrays = [np.asarray(x, np.float32) for x in (mag_anom, rtp, tmi_vg, tmi, depth_to_base)]
    if any(a.shape != valid.shape for a in arrays):
        raise ValueError("MRR bands and valid mask must share one 2-D shape")
    if any(not np.isfinite(a[valid]).all() for a in arrays):
        raise ValueError("MRR input contains non-finite values inside valid footprint")

    mag_z, mag_stats = _robust_standardize(arrays[0], valid)
    rtp_z, rtp_stats = _robust_standardize(arrays[1], valid)
    vg_z, vg_stats = _robust_standardize(arrays[2], valid)
    tmi_z, tmi_stats = _robust_standardize(arrays[3], valid)
    depth = np.maximum(arrays[4], 0.0).astype(np.float32)

    h, w = valid.shape
    nbr = (h + block_side_px - 1) // block_side_px
    nbc = (w + block_side_px - 1) // block_side_px
    coefs = np.zeros((3, nbr, nbc), dtype=np.float32)
    has_data = np.zeros((nbr, nbc), dtype=bool)
    counts = np.zeros((nbr, nbc), dtype=np.int32)
    ridge = np.diag([0.0, ridge_lambda, ridge_lambda]).astype(np.float64)

    for br in range(nbr):
        rs = slice(br * block_side_px, min((br + 1) * block_side_px, h))
        for bc in range(nbc):
            cs = slice(bc * block_side_px, min((bc + 1) * block_side_px, w))
            m = valid[rs, cs]
            n = int(m.sum())
            counts[br, bc] = n
            if n < 250:
                continue
            x1 = np.clip(tmi_z[rs, cs][m], -4.0, 4.0).astype(np.float64)
            x2 = np.clip(mag_z[rs, cs][m], -4.0, 4.0).astype(np.float64)
            y = np.clip(vg_z[rs, cs][m], -4.0, 4.0).astype(np.float64)
            X = np.column_stack([np.ones(n, dtype=np.float64), x1, x2])
            xtx = X.T @ X
            xty = X.T @ y
            beta = np.linalg.solve(xtx + ridge, xty)
            coefs[:, br, bc] = beta.astype(np.float32)
            has_data[br, bc] = True

    if int(has_data.sum()) < 2:
        raise ValueError("too few populated blocks for MRR regression")
    # Fill isolated empty edge blocks with the global median before normalized smoothing.
    for j in range(3):
        med = float(np.median(coefs[j][has_data]))
        coefs[j][~has_data] = med
    smooth_mask = np.ones_like(has_data, dtype=bool)
    beta_full = [
        _smooth_block_coefficients(coefs[j], smooth_mask, valid.shape)
        for j in range(3)
    ]
    predicted = beta_full[0] + beta_full[1] * tmi_z + beta_full[2] * mag_z
    residual = (vg_z - predicted).astype(np.float32)
    residual[~valid] = 0.0
    residual_z, residual_stats = _robust_standardize(residual, valid)

    trough = _hessian_trough(residual_z, sigma=2.0)
    trough_z, trough_stats = _robust_standardize(trough, valid)
    neg_resid = np.maximum(-residual_z, 0.0)
    depth_gate = np.log1p(depth / np.float32(250.0))
    depth_weighted = (neg_resid * depth_gate).astype(np.float32)
    depth_weighted_z, depth_weighted_stats = _robust_standardize(depth_weighted, valid)

    # Signed-gradient disagreement: magnetic residual corridor crossing an RTP edge.
    rgy = sobel(residual_z, axis=0, mode="nearest") * np.float32(0.125)
    rgx = sobel(residual_z, axis=1, mode="nearest") * np.float32(0.125)
    pgy = sobel(rtp_z, axis=0, mode="nearest") * np.float32(0.125)
    pgx = sobel(rtp_z, axis=1, mode="nearest") * np.float32(0.125)
    cross = np.abs(rgx * pgy - rgy * pgx).astype(np.float32)
    cross_z, cross_stats = _robust_standardize(cross, valid)

    features = [residual_z, trough_z, depth_weighted_z, cross_z]
    for arr in features:
        arr[~valid] = 0.0
        if not np.isfinite(arr).all():
            raise AssertionError("non-finite MRR feature")
    meta = {
        "block_side_px": int(block_side_px),
        "block_side_m": int(block_side_px * 100),
        "ridge_lambda": float(ridge_lambda),
        "coefficient_smoothing_sigma_blocks": COEF_SMOOTH_SIGMA_BLOCKS,
        "populated_blocks": int(has_data.sum()),
        "total_blocks": int(has_data.size),
        "block_valid_count_min": int(counts[has_data].min()),
        "block_valid_count_median": float(np.median(counts[has_data])),
        "normalization": {
            "mag_anom": mag_stats,
            "rtp": rtp_stats,
            "tmi_vg": vg_stats,
            "tmi": tmi_stats,
            "residual": residual_stats,
            "trough": trough_stats,
            "depth_weighted": depth_weighted_stats,
            "crossgradient": cross_stats,
        },
        "coefficient_summary": {
            f"beta_{j}": {
                "min": float(np.min(beta_full[j][valid])),
                "median": float(np.median(beta_full[j][valid])),
                "max": float(np.max(beta_full[j][valid])),
            }
            for j in range(3)
        },
    }
    return features, meta


def build_or_load_mrr_memmap(
    training_features_path: Path,
    valid: np.ndarray,
    cache_dir: Path,
) -> tuple[np.memmap, list[str], dict]:
    """Build/reload a `(N_footprint, 4)` float32 MRR feature memmap."""
    training_features_path = Path(training_features_path)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / "mrr_bpr_4ch.dat"
    meta_path = cache_dir / "mrr_bpr_4ch.json"
    source_sha = sha256_file(training_features_path)
    n_valid = int(np.asarray(valid, bool).sum())
    contract = {
        "schema": "gems88.mrr-bpr-features.v1",
        "source_sha256": source_sha,
        "shape": [n_valid, len(MRR_FEATURES)],
        "features": list(MRR_FEATURES),
        "block_side_px": BLOCK_SIDE_PX,
        "ridge_lambda": RIDGE_LAMBDA,
        "coefficient_smoothing_sigma_blocks": COEF_SMOOTH_SIGMA_BLOCKS,
    }
    if dat_path.is_file() and meta_path.is_file():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            all(old.get(k) == v for k, v in contract.items())
            and dat_path.stat().st_size == n_valid * len(MRR_FEATURES) * 4
            and old.get("cache_sha256") == sha256_file(dat_path)
        ):
            return (
                np.memmap(dat_path, dtype="float32", mode="r", shape=(n_valid, len(MRR_FEATURES))),
                list(MRR_FEATURES),
                old,
            )

    with rasterio.open(training_features_path) as ds:
        expected = {1: "mag_anom", 2: "rtp", 9: "tmi_vg", 14: "tmi", 15: "depth_to_base_surf"}
        bands: dict[int, np.ndarray] = {}
        tags: dict[str, str] = {}
        for idx, want in expected.items():
            got = ds.tags(idx).get("band_name", "")
            if got != want:
                raise ValueError(f"band {idx}: expected {want!r}, got {got!r}")
            tags[str(idx)] = got
            bands[idx] = clean_band(ds.read(idx), valid)[0]
    features, derived = compute_mrr_features(
        bands[1], bands[2], bands[9], bands[14], bands[15], valid
    )
    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_valid, len(MRR_FEATURES)))
    for j, arr in enumerate(features):
        mm[:, j] = arr[valid]
    mm.flush()
    del mm
    payload = {
        **contract,
        "verified_band_tags": tags,
        "derived": derived,
        "cache_sha256": sha256_file(dat_path),
    }
    meta_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return (
        np.memmap(dat_path, dtype="float32", mode="r", shape=(n_valid, len(MRR_FEATURES))),
        list(MRR_FEATURES),
        payload,
    )


class StackedFeatureView:
    """Row-indexable, non-copying logical horizontal stack of feature matrices."""

    def __init__(self, sources: Sequence[np.ndarray]):
        if not sources:
            raise ValueError("StackedFeatureView requires at least one source")
        self.sources = tuple(sources)
        n = int(self.sources[0].shape[0])
        if any(len(src.shape) != 2 or int(src.shape[0]) != n for src in self.sources):
            raise ValueError("all stacked feature sources must be 2-D with equal row count")
        self.shape = (n, sum(int(src.shape[1]) for src in self.sources))
        self.ndim = 2

    def __len__(self) -> int:
        return self.shape[0]

    def __getitem__(self, key):
        # The learning code performs row slicing/indexing only. Supporting a
        # `(rows, cols)` tuple would invite silent cross-source column mistakes.
        if isinstance(key, tuple):
            rows, cols = key
            full = self.__getitem__(rows)
            return full[:, cols]
        parts = []
        for src in self.sources:
            arr = np.asarray(src[key])
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            parts.append(arr)
        return np.hstack(parts)
