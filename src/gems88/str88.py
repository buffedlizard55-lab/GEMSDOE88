"""STR-88: Zero-catalogue multi-physics curvilinear crest + spin-2 strike + exact-shell submodular DTI."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter
from sklearn.ensemble import HistGradientBoostingClassifier

from gems57 import emit

FULL_VALID_PIXELS = 5_167_373

STR88_BAND_SPECS = {
    2: "rtp",
    3: "tmi_hg",
    5: "iso_grav_anom_slope",
    6: "tc",
    7: "geod_shearrate",
    8: "geod_dilaterate",
    9: "tmi_vg",
    11: "iso_grav_anom_vg",
    12: "det_elev",
    13: "iso_grav_anom",
    15: "depth_to_base_surf",
    18: "iso_grav_anom_hg",
    19: "det_elev_slope",
}

STR88_NAMES = [
    "topo_slope_100m",
    "topo_grad_300m",
    "topo_ridge_200m",
    "topo_lap_abs_200m",
    "grav_slope_100m",
    "grav_hg_100m",
    "grav_ridge_300m",
    "grav_tilt_abs",
    "mag_log_hg",
    "mag_tilt_abs",
    "mag_ridge_200m",
    "tc_grad_200m",
    "spin2_mp_consensus",
    "spin2_mp_persist_400m",
    "mgc_grav_mag_align",
    "basement_depth_grad_400m",
    "local_basin_relief_2500m",
    "strain_extensional_ratio",
]

CACHE_STEM = "str88-18ch-v1"


def _neumann_smooth(arr: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Footprint-normalized Gaussian smoothing with natural zero-flux boundary extension.

    Extending num/w wherever w > 1e-5 before finite-differencing prevents artificial
    jump derivatives along the outer polygon rim while keeping sentinel/NaN values
    completely excluded.
    """
    w = gaussian_filter(valid.astype(np.float32), sigma=sigma, mode="nearest")
    clean = np.where(valid, np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0), 0.0).astype(
        np.float32
    )
    num = gaussian_filter(clean, sigma=sigma, mode="nearest")
    return np.where(w > 1e-5, num / np.maximum(w, 1e-5), 0.0).astype(np.float32)


def smooth_footprint(arr: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    s = _neumann_smooth(arr, valid, sigma)
    s[~valid] = 0.0
    return s


def grad_footprint(
    arr: np.ndarray, valid: np.ndarray, sigma: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (gy, gx, gmag) inside valid with zero outer-rim jump artifacts."""
    s = _neumann_smooth(arr, valid, sigma)
    gy, gx = np.gradient(s)
    gy = np.where(valid, gy, 0.0).astype(np.float32)
    gx = np.where(valid, gx, 0.0).astype(np.float32)
    gm = np.hypot(gy, gx).astype(np.float32)
    return gy, gx, gm


def laplacian_abs_footprint(arr: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    s = _neumann_smooth(arr, valid, sigma)
    gy, gx = np.gradient(s)
    gyy, _ = np.gradient(gy)
    _, gxx = np.gradient(gx)
    lap = np.abs(gyy + gxx).astype(np.float32)
    lap[~valid] = 0.0
    return lap


def hessian_crest(arr: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Scale-normalized curvilinear crest strength sigma^2 * max(0, -lambda_min(H))."""
    s = _neumann_smooth(arr, valid, sigma)
    gy, gx = np.gradient(s)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    hxy = np.float32(0.5) * (gyx + gxy)
    half_tr = np.float32(0.5) * (gyy + gxx)
    half_df = np.float32(0.5) * (gyy - gxx)
    rad = np.hypot(half_df, hxy)
    lam_min = half_tr - rad
    crest = (np.float32(sigma * sigma) * np.maximum(np.float32(0.0), -lam_min)).astype(np.float32)
    crest[~valid] = 0.0
    return crest


def spin2_multiphysics(
    modalities: list[tuple[np.ndarray, float]],
    valid: np.ndarray,
    persist_sigma: float = 4.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute pointwise and spatially integrated spin-2 axial strike consensus.

    Each modality contributes w_m * (cos 2*theta_m, sin 2*theta_m) where theta_m is the
    gradient normal angle and w_m = min(1, |grad| / P95(|grad|)). Invariant to sign
    reversals across contacts; integrates to zero around circular volcanic plugs/domes.
    """
    u_sum = np.zeros(valid.shape, dtype=np.float32)
    v_sum = np.zeros(valid.shape, dtype=np.float32)
    for field, sigma in modalities:
        gy, gx, gm = grad_footprint(field, valid, sigma=sigma)
        vals = gm[valid]
        p95 = float(np.percentile(vals, 95.0)) if vals.size else 1.0
        scale = np.float32(max(p95, 1e-6))
        w = np.minimum(np.float32(1.0), gm / scale)
        denom = gm * gm + np.float32(1e-12)
        u_sum += w * ((gx * gx - gy * gy) / denom)
        v_sum += w * ((np.float32(2.0) * gx * gy) / denom)
    u_sum[~valid] = 0.0
    v_sum[~valid] = 0.0
    consensus = np.hypot(u_sum, v_sum).astype(np.float32)
    consensus[~valid] = 0.0
    u_bar = smooth_footprint(u_sum, valid, sigma=persist_sigma)
    v_bar = smooth_footprint(v_sum, valid, sigma=persist_sigma)
    persist = np.hypot(u_bar, v_bar).astype(np.float32)
    persist[~valid] = 0.0
    return consensus, persist


def _kernel_shells() -> list[tuple[float, list[tuple[int, int]]]]:
    """Group 300 m DTI kernel offsets by descending exact weight shells."""
    buckets: dict[int, list[tuple[int, int, float]]] = {}
    for dy, dx, k in zip(emit.OFF_DY.tolist(), emit.OFF_DX.tolist(), emit.OFF_K.tolist()):
        d2 = int(dy * dy + dx * dx)
        buckets.setdefault(d2, []).append((int(dy), int(dx), float(k)))
    shells = []
    for d2 in sorted(buckets.keys()):
        entries = buckets[d2]
        k_val = entries[0][2]
        offsets = [(dy, dx) for dy, dx, _ in entries]
        shells.append((k_val, offsets))
    shells.sort(key=lambda item: item[0], reverse=True)
    return shells


_SHELLS = _kernel_shells()


def exact_bernoulli_self_credit(p: np.ndarray) -> np.ndarray:
    """Exact E[max_{g in N_3(x)} k(||x-g||) * Bernoulli(p(g))] in [0, 1].

    Uses the ordered radial-shell tail-sum identity across the 6 distinct distance
    shells of the 300 m triangular kernel. On any binary truth map G in {0, 1},
    reproduces max_{g in G} k(||x-g||) to floating-point precision while never
    exceeding 1.0 on soft posterior probabilities.
    """
    H, W = p.shape
    p_clip = np.clip(np.nan_to_num(p, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0).astype(
        np.float32
    )
    # Track log survival inside (0, 1) and an exact hit count for p == 1.0 cells.
    log_surv = np.zeros((H, W), dtype=np.float32)
    hit_one = np.zeros((H, W), dtype=bool)
    out = np.zeros((H, W), dtype=np.float32)

    for idx, (k_curr, offsets) in enumerate(_SHELLS):
        k_next = _SHELLS[idx + 1][0] if idx + 1 < len(_SHELLS) else 0.0
        dk = np.float32(k_curr - k_next)
        for j, i in offsets:
            ys0, ys1 = max(0, j), min(H, H + j)
            xs0, xs1 = max(0, i), min(W, W + i)
            src = p_clip[max(0, -j) : min(H, H - j), max(0, -i) : min(W, W - i)]
            ones = src >= np.float32(0.9999999)
            hit_one[ys0:ys1, xs0:xs1] |= ones
            safe = np.where(ones, np.float32(0.0), src)
            log_surv[ys0:ys1, xs0:xs1] += np.log1p(-safe)
        prob_ge = np.where(hit_one, np.float32(1.0), -np.expm1(log_surv))
        out += dk * prob_ge
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def _read_clean_band(
    src: rasterio.io.DatasetReader, band_idx: int, expected_name: str, footprint: np.ndarray
) -> tuple[np.ndarray, dict]:
    actual = src.tags(band_idx).get("band_name")
    if actual != expected_name:
        raise ValueError(f"Band {band_idx} tag mismatch: expected {expected_name!r}, got {actual!r}")
    raw = np.asarray(src.read(band_idx), dtype=np.float32)
    ok = footprint & np.isfinite(raw)
    if src.nodata is not None:
        ok &= raw != np.float32(src.nodata)
    ok &= np.abs(raw) < np.float32(1e30)
    if not ok.any():
        raise ValueError(f"Band {band_idx} ({expected_name}) has zero valid pixels in footprint")
    sample = raw.ravel()[np.flatnonzero(ok.ravel())[::37]]
    lo, med, hi = [float(x) for x in np.percentile(sample, [0.05, 50.0, 99.95])]
    clean = np.where(ok, raw, np.float32(med)).astype(np.float32, copy=False)
    np.clip(clean, np.float32(lo), np.float32(hi), out=clean)
    clean[~footprint] = np.float32(0.0)
    stats = {
        "band": band_idx,
        "valid_in_footprint": int(ok.sum()),
        "imputed_in_footprint": int((footprint & ~ok).sum()),
        "p0005": lo,
        "median": med,
        "p9995": hi,
    }
    return clean, stats


def build_str88_cache(
    feature_tif: Path, footprint: np.ndarray, cache_dir: Path
) -> tuple[np.memmap, dict]:
    """Stream-compute the 18-channel STR-88 feature stack into a disk memmap (<600 MiB RAM)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta_path = cache_dir / f"{CACHE_STEM}.json"
    feat_path = cache_dir / f"{CACHE_STEM}.f32"
    valid = np.asarray(footprint, dtype=bool)
    h, w = valid.shape

    if meta_path.is_file() and feat_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (
            meta.get("names") == STR88_NAMES
            and meta.get("n_channels") == len(STR88_NAMES)
            and meta.get("valid_pixels") == int(valid.sum())
        ):
            mm = np.memmap(feat_path, dtype="float32", mode="r", shape=(h * w, len(STR88_NAMES)))
            return mm, meta

    band_stats: dict[str, dict] = {}
    with rasterio.open(feature_tif) as src:
        if src.shape != (h, w):
            raise ValueError(f"Feature shape {src.shape} != footprint {(h, w)}")
        mm = np.memmap(feat_path, dtype="float32", mode="w+", shape=(h * w, len(STR88_NAMES)))

        def _store(col: int, name: str, arr2d: np.ndarray) -> None:
            assert STR88_NAMES[col] == name
            out = np.where(valid, np.nan_to_num(arr2d, nan=0.0, posinf=0.0, neginf=0.0), 0.0).astype(
                np.float32
            )
            mm[:, col] = out.ravel()

        # Block A: Topographic scarp & curvilinear crest geometry (Bands 19, 12)
        det_slope, st = _read_clean_band(src, 19, "det_elev_slope", valid)
        band_stats["det_elev_slope"] = st
        _store(0, "topo_slope_100m", det_slope)
        _store(2, "topo_ridge_200m", hessian_crest(det_slope, valid, sigma=2.0))
        del det_slope

        det_elev, st = _read_clean_band(src, 12, "det_elev", valid)
        band_stats["det_elev"] = st
        _, _, topo_g3 = grad_footprint(det_elev, valid, sigma=3.0)
        _store(1, "topo_grad_300m", topo_g3)
        del topo_g3
        _store(3, "topo_lap_abs_200m", laplacian_abs_footprint(det_elev, valid, sigma=2.0))

        # Block B: Gravity basement-step & curvilinear crest geometry (Bands 5, 18, 11)
        grav_slope, st = _read_clean_band(src, 5, "iso_grav_anom_slope", valid)
        band_stats["iso_grav_anom_slope"] = st
        _store(4, "grav_slope_100m", grav_slope)
        _store(6, "grav_ridge_300m", hessian_crest(grav_slope, valid, sigma=3.0))
        del grav_slope

        grav_hg, st = _read_clean_band(src, 18, "iso_grav_anom_hg", valid)
        band_stats["iso_grav_anom_hg"] = st
        _store(5, "grav_hg_100m", grav_hg)
        grav_vg, st = _read_clean_band(src, 11, "iso_grav_anom_vg", valid)
        band_stats["iso_grav_anom_vg"] = st
        grav_tilt = np.abs(
            np.arctan2(grav_vg, np.maximum(grav_hg, np.float32(0.0)) + np.float32(1e-6))
        ).astype(np.float32)
        _store(7, "grav_tilt_abs", grav_tilt)
        del grav_hg, grav_vg, grav_tilt

        # Block C: Magnetic structural contact & curvilinear crest geometry (Bands 3, 9, 6)
        tmi_hg, st = _read_clean_band(src, 3, "tmi_hg", valid)
        band_stats["tmi_hg"] = st
        mag_log = np.log1p(np.maximum(tmi_hg, np.float32(0.0))).astype(np.float32)
        _store(8, "mag_log_hg", mag_log)
        _store(10, "mag_ridge_200m", hessian_crest(mag_log, valid, sigma=2.0))
        del mag_log

        tmi_vg, st = _read_clean_band(src, 9, "tmi_vg", valid)
        band_stats["tmi_vg"] = st
        mag_tilt = np.abs(
            np.arctan2(tmi_vg, np.maximum(tmi_hg, np.float32(0.0)) + np.float32(1e-3))
        ).astype(np.float32)
        _store(9, "mag_tilt_abs", mag_tilt)
        del tmi_hg, tmi_vg, mag_tilt

        tc, st = _read_clean_band(src, 6, "tc", valid)
        band_stats["tc"] = st
        _, _, tc_g2 = grad_footprint(tc, valid, sigma=2.0)
        _store(11, "tc_grad_200m", tc_g2)
        del tc_g2

        # Block D: Spin-2 4-modality axial strike consensus & cross-potential alignment (Bands 12, 2, 13, 6)
        rtp, st = _read_clean_band(src, 2, "rtp", valid)
        band_stats["rtp"] = st
        iso_grav, st = _read_clean_band(src, 13, "iso_grav_anom", valid)
        band_stats["iso_grav_anom"] = st
        consensus, persist = spin2_multiphysics(
            [(det_elev, 2.0), (rtp, 2.0), (iso_grav, 3.0), (tc, 2.0)],
            valid,
            persist_sigma=4.0,
        )
        _store(12, "spin2_mp_consensus", consensus)
        _store(13, "spin2_mp_persist_400m", persist)
        del det_elev, tc, consensus, persist

        gy_g, gx_g, gm_g = grad_footprint(iso_grav, valid, sigma=3.0)
        gy_m, gx_m, gm_m = grad_footprint(rtp, valid, sigma=2.0)
        cos_gm = np.abs(gy_g * gy_m + gx_g * gx_m) / (gm_g * gm_m + np.float32(1e-6))
        gm_align = (cos_gm * np.log1p(gm_g * gm_m)).astype(np.float32)
        _store(14, "mgc_grav_mag_align", gm_align)
        del rtp, iso_grav, gy_g, gx_g, gm_g, gy_m, gx_m, gm_m, cos_gm, gm_align

        # Block E: Cover-bench relief & dimensionless GPS strain regime (Bands 15, 7, 8)
        dtb, st = _read_clean_band(src, 15, "depth_to_base_surf", valid)
        band_stats["depth_to_base_surf"] = st
        _, _, dtb_g4 = grad_footprint(dtb, valid, sigma=4.0)
        _store(15, "basement_depth_grad_400m", dtb_g4)
        del dtb_g4
        dtb_rel = dtb - smooth_footprint(dtb, valid, sigma=25.0)
        _store(16, "local_basin_relief_2500m", dtb_rel)
        del dtb, dtb_rel

        shear, st = _read_clean_band(src, 7, "geod_shearrate", valid)
        band_stats["geod_shearrate"] = st
        dilat, st = _read_clean_band(src, 8, "geod_dilaterate", valid)
        band_stats["geod_dilaterate"] = st
        strain_ratio = dilat / (np.abs(shear) + np.abs(dilat) + np.float32(1e-9))
        _store(17, "strain_extensional_ratio", strain_ratio)
        del shear, dilat, strain_ratio

        mm.flush()

    meta = {
        "cache_stem": CACHE_STEM,
        "shape": [h, w],
        "n_channels": len(STR88_NAMES),
        "names": STR88_NAMES,
        "bands_used": {str(k): v for k, v in STR88_BAND_SPECS.items()},
        "band_imputation_stats": band_stats,
        "valid_pixels": int(valid.sum()),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(feat_path, dtype="float32", mode="r", shape=(h * w, len(STR88_NAMES))), meta


def fit_str88(
    x: np.ndarray,
    footprint: np.ndarray,
    visible: np.ndarray,
    training_domain: np.ndarray | None = None,
    seed: int = 88,
    pos_cap: int = 32_000,
    neg_cap: int = 96_000,
) -> tuple[HistGradientBoostingClassifier, dict]:
    """Fit prevalence-calibrated LOQO PU HistGradientBoostingClassifier on visible traces."""
    from scipy.ndimage import binary_dilation

    dom = footprint if training_domain is None else (footprint & training_domain)
    pos_all = np.flatnonzero((dom & visible).ravel())
    excl = binary_dilation(visible, iterations=3)
    neg_all = np.flatnonzero((dom & ~excl).ravel())
    if pos_all.size == 0 or neg_all.size == 0:
        raise ValueError("STR-88 requires non-empty positive and unlabeled pixel sets.")

    pi_vis = float(pos_all.size) / float(pos_all.size + neg_all.size)
    rng = np.random.default_rng(seed)
    pos = rng.choice(pos_all, min(pos_cap, pos_all.size), replace=False)
    neg = rng.choice(neg_all, min(neg_cap, neg_all.size), replace=False)

    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(pos.size, dtype=np.int8), np.zeros(neg.size, dtype=np.int8)])

    # Inverse-sampling weights restore natural footprint prevalence pi_vis.
    w_pos = pi_vis / float(pos.size)
    w_neg = (1.0 - pi_vis) / float(neg.size)
    sw = np.concatenate(
        [np.full(pos.size, w_pos, dtype=np.float64), np.full(neg.size, w_neg, dtype=np.float64)]
    )
    sw *= float(sw.size) / float(sw.sum())

    order = rng.permutation(idx.size)
    idx, y, sw = idx[order], y[order], sw[order]

    clf = HistGradientBoostingClassifier(
        max_iter=140,
        learning_rate=0.06,
        max_leaf_nodes=31,
        min_samples_leaf=80,
        max_bins=128,
        l2_regularization=2.0,
        random_state=seed,
    )
    clf.fit(np.asarray(x[idx], dtype=np.float32), y, sample_weight=sw)
    info = {
        "n_visible_training": int(pos_all.size),
        "n_positives": int(pos.size),
        "n_unlabeled": int(neg.size),
        "prevalence_pi": float(pi_vis),
        "columns": list(range(x.shape[1])),
        "noisy_pu_negative_sampling": True,
        "prevalence_calibrated_weights": True,
    }
    return clf, info


def predict_indices_str88(
    clf: HistGradientBoostingClassifier,
    x: np.ndarray,
    indices: np.ndarray,
    chunk: int = 150_000,
) -> np.ndarray:
    """Chunked prevalence-calibrated posterior prediction on 1-D global indices."""
    res = np.empty(indices.size, dtype=np.float32)
    for start in range(0, indices.size, chunk):
        part = indices[start : start + chunk]
        res[start : start + part.size] = clf.predict_proba(
            np.asarray(x[part], dtype=np.float32)
        )[:, 1].astype(np.float32)
    return res


def allocate_str88_dinkelbach(
    posterior: np.ndarray,
    valid: np.ndarray,
    visible: np.ndarray,
    budget: int,
    min_spacing_px: float = 2.85,
) -> tuple[np.ndarray, dict]:
    """Allocate binary {0, 1} off-catalogue dots via exact-shell self-credit + Dinkelbach."""
    allowed = valid & ~visible
    n_allowed = int(allowed.sum())
    if budget <= 0 or n_allowed == 0:
        return np.zeros(posterior.shape, dtype=np.float32), {"n_dots": 0, "lambda_star": 0.0}
    eff_budget = min(int(budget), n_allowed)
    p_clean = np.where(valid, np.clip(posterior, 0.0, 1.0), 0.0).astype(np.float32)
    self_credit = exact_bernoulli_self_credit(p_clean)
    cand_cap = min(n_allowed, max(eff_budget * 30, 60_000))
    k_truth = max(float(p_clean[allowed].sum()), 1.0)
    alloc = emit.dinkelbach_allocate(
        p=p_clean,
        self_credit=self_credit,
        allowed=allowed,
        budget=eff_budget,
        k_truth=k_truth,
        min_spacing_px=min_spacing_px,
        candidate_cap=cand_cap,
    )
    info = {
        "n_dots": int(alloc.n_dots),
        "requested": int(eff_budget),
        "surrogate_dti": float(alloc.surrogate_dti),
        "expected_covered_credit": float(alloc.expected_covered_credit),
        "expected_self_credit": float(alloc.expected_self_credit),
        "rounds": int(alloc.rounds),
    }
    return alloc.emitted.astype(np.float32), info


def holdout_str88_dinkelbach(
    posterior: np.ndarray,
    valid: np.ndarray,
    visible: np.ndarray,
    full_budget: int = 37_654,
    min_spacing_px: float = 2.85,
) -> np.ndarray:
    """Proportional-budget Dinkelbach allocation for cropped holdout folds."""
    target = max(1, int(round(full_budget * float(valid.sum()) / float(FULL_VALID_PIXELS))))
    dots, _ = allocate_str88_dinkelbach(
        posterior, valid, visible, budget=target, min_spacing_px=min_spacing_px
    )
    return dots
