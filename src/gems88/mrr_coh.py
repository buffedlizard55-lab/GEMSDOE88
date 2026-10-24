"""MRR-COH-88: label-blind persistence of magnetic-residual corridors.

This module extends the four MRR-BPR channels with four orientation/persistence
channels.  It never reads the fault catalogue.  Catalogue masks are supplied to
models only after this feature cache has been built.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

from .edge import clean_band, derivatives
from .mrr import MRR_FEATURES, sha256_file

COH_FEATURES: tuple[str, ...] = (
    "mrr_residual_axial_coherence_600m",
    "mrr_residual_axial_persistence_200_600m",
    "mrr_coherent_demag_trough",
    "mrr_persistent_corridor_low_hg",
)
ALL_MRR_COH_FEATURES: tuple[str, ...] = MRR_FEATURES + COH_FEATURES

FINE_SOURCE_SIGMA_PX = 2.0
FINE_TENSOR_SIGMA_PX = 6.0
COARSE_SOURCE_SIGMA_PX = 6.0
COARSE_TENSOR_SIGMA_PX = 12.0


def _normalized_smooth(a: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian average that excludes cells outside the footprint."""
    weight = np.asarray(valid, np.float32)
    numer = gaussian_filter(np.asarray(a, np.float32) * weight, sigma=sigma, mode="constant")
    denom = gaussian_filter(weight, sigma=sigma, mode="constant")
    out = np.divide(numer, np.maximum(denom, np.float32(1e-6)), dtype=np.float32)
    out[~valid] = 0.0
    return out


def axial_tensor(
    field: np.ndarray,
    valid: np.ndarray,
    *,
    source_sigma_px: float,
    tensor_sigma_px: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return coherence and the normalized spin-2 gradient orientation.

    ``q_cos`` and ``q_sin`` encode an axial direction: reversing a gradient by
    180 degrees leaves the pair unchanged.  Coherence is zero for a constant or
    locally isotropic field and approaches one for a persistent linear edge.
    """
    field = np.asarray(field, np.float32)
    valid = np.asarray(valid, bool)
    if field.shape != valid.shape or source_sigma_px <= 0 or tensor_sigma_px <= 0:
        raise ValueError("invalid axial-tensor inputs")
    gy, gx = derivatives(field, valid, sigma=source_sigma_px)
    jxx = _normalized_smooth(gx * gx, valid, tensor_sigma_px)
    jyy = _normalized_smooth(gy * gy, valid, tensor_sigma_px)
    jxy = _normalized_smooth(gx * gy, valid, tensor_sigma_px)
    diff = jxx - jyy
    twice = np.float32(2.0) * jxy
    anis = np.hypot(diff, twice).astype(np.float32)
    trace = (jxx + jyy).astype(np.float32)
    coherence = np.divide(anis, np.maximum(trace, np.float32(1e-8)), dtype=np.float32)
    np.clip(coherence, 0.0, 1.0, out=coherence)
    q_cos = np.divide(diff, np.maximum(anis, np.float32(1e-8)), dtype=np.float32)
    q_sin = np.divide(twice, np.maximum(anis, np.float32(1e-8)), dtype=np.float32)
    weak = trace <= np.float32(1e-8)
    coherence[weak] = 0.0
    q_cos[weak] = 0.0
    q_sin[weak] = 0.0
    for out in (coherence, q_cos, q_sin):
        out[~valid] = 0.0
    return coherence, q_cos, q_sin


def compute_coherence_features(
    residual_z: np.ndarray,
    trough_z: np.ndarray,
    tmi_hg: np.ndarray,
    valid: np.ndarray,
) -> tuple[list[np.ndarray], dict]:
    """Compute the four preregistered MRR-COH channels."""
    valid = np.asarray(valid, bool)
    arrays = [np.asarray(a, np.float32) for a in (residual_z, trough_z, tmi_hg)]
    if any(a.shape != valid.shape for a in arrays) or not valid.any():
        raise ValueError("MRR-COH arrays must share one nonempty 2-D footprint")
    if any(not np.isfinite(a[valid]).all() for a in arrays):
        raise ValueError("non-finite MRR-COH input in footprint")

    coh_f, qc_f, qs_f = axial_tensor(
        arrays[0], valid,
        source_sigma_px=FINE_SOURCE_SIGMA_PX,
        tensor_sigma_px=FINE_TENSOR_SIGMA_PX,
    )
    coh_c, qc_c, qs_c = axial_tensor(
        arrays[0], valid,
        source_sigma_px=COARSE_SOURCE_SIGMA_PX,
        tensor_sigma_px=COARSE_TENSOR_SIGMA_PX,
    )
    axial_agreement = np.clip(
        np.float32(0.5) * (np.float32(1.0) + qc_f * qc_c + qs_f * qs_c),
        0.0,
        1.0,
    ).astype(np.float32)
    persistence = (axial_agreement * np.sqrt(np.maximum(coh_f * coh_c, 0.0))).astype(np.float32)

    positive_trough = np.maximum(arrays[1], 0.0).astype(np.float32)
    coherent_trough = (positive_trough * coh_f).astype(np.float32)
    negative_corridor = np.maximum(-arrays[0], 0.0).astype(np.float32)
    hg = np.log1p(np.maximum(arrays[2], 0.0)).astype(np.float32)
    hg95 = max(float(np.percentile(hg[valid], 95.0)), 1e-6)
    hg_scaled = np.clip(hg / np.float32(hg95), 0.0, 4.0)
    low_hg_corridor = (
        negative_corridor * persistence / (np.float32(0.25) + hg_scaled)
    ).astype(np.float32)

    features = [coh_f, persistence, coherent_trough, low_hg_corridor]
    summaries = {}
    for name, arr in zip(COH_FEATURES, features):
        arr[~valid] = 0.0
        if not np.isfinite(arr).all():
            raise AssertionError(f"non-finite derived feature {name}")
        vals = arr[valid]
        summaries[name] = {
            "min": float(vals.min()),
            "median": float(np.median(vals)),
            "p95": float(np.percentile(vals, 95.0)),
            "max": float(vals.max()),
        }
    return features, {
        "fine_source_sigma_px": FINE_SOURCE_SIGMA_PX,
        "fine_tensor_sigma_px": FINE_TENSOR_SIGMA_PX,
        "coarse_source_sigma_px": COARSE_SOURCE_SIGMA_PX,
        "coarse_tensor_sigma_px": COARSE_TENSOR_SIGMA_PX,
        "pixel_size_m": 100,
        "tmi_hg_log_p95": hg95,
        "feature_summaries": summaries,
    }


def build_or_load_mrr_coh_memmap(
    training_features_path: Path,
    valid: np.ndarray,
    mrr_matrix: np.ndarray,
    cache_dir: Path,
) -> tuple[np.memmap, list[str], dict]:
    """Build/reload the four new footprint-row-aligned float32 channels."""
    training_features_path = Path(training_features_path)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    valid = np.asarray(valid, bool)
    n_valid = int(valid.sum())
    if mrr_matrix.shape != (n_valid, len(MRR_FEATURES)):
        raise ValueError("MRR base matrix contract mismatch")
    dat_path = cache_dir / "mrr_coh_4ch.dat"
    meta_path = cache_dir / "mrr_coh_4ch.json"
    source_sha = sha256_file(training_features_path)
    contract = {
        "schema": "gems88.mrr-coh-features.v1",
        "source_sha256": source_sha,
        "shape": [n_valid, len(COH_FEATURES)],
        "features": list(COH_FEATURES),
        "base_features": list(MRR_FEATURES),
        "parameters": {
            "fine_source_sigma_px": FINE_SOURCE_SIGMA_PX,
            "fine_tensor_sigma_px": FINE_TENSOR_SIGMA_PX,
            "coarse_source_sigma_px": COARSE_SOURCE_SIGMA_PX,
            "coarse_tensor_sigma_px": COARSE_TENSOR_SIGMA_PX,
        },
    }
    if dat_path.is_file() and meta_path.is_file():
        old = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            all(old.get(k) == v for k, v in contract.items())
            and dat_path.stat().st_size == n_valid * len(COH_FEATURES) * 4
            and old.get("cache_sha256") == sha256_file(dat_path)
        ):
            return (
                np.memmap(dat_path, dtype="float32", mode="r", shape=(n_valid, len(COH_FEATURES))),
                list(COH_FEATURES),
                old,
            )

    residual = np.zeros(valid.shape, dtype=np.float32)
    trough = np.zeros(valid.shape, dtype=np.float32)
    residual[valid] = np.asarray(mrr_matrix[:, 0], np.float32)
    trough[valid] = np.asarray(mrr_matrix[:, 1], np.float32)
    with rasterio.open(training_features_path) as src:
        got = src.tags(3).get("band_name", "")
        if got != "tmi_hg":
            raise ValueError(f"band 3: expected 'tmi_hg', got {got!r}")
        tmi_hg, hg_stats = clean_band(src.read(3), valid)
    features, derived = compute_coherence_features(residual, trough, tmi_hg, valid)
    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_valid, len(COH_FEATURES)))
    for col, arr in enumerate(features):
        mm[:, col] = arr[valid]
    mm.flush()
    del mm
    payload = {
        **contract,
        "verified_band_tags": {"3": "tmi_hg"},
        "tmi_hg_cleaning": hg_stats,
        "derived": derived,
        "cache_sha256": sha256_file(dat_path),
    }
    meta_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return (
        np.memmap(dat_path, dtype="float32", mode="r", shape=(n_valid, len(COH_FEATURES))),
        list(COH_FEATURES),
        payload,
    )
