"""H88-QTSK: Decoupled Quaternary Cover-Thickness Steps + Tectonic Fluvial Chi-Knickpoint
& Scarp-Polarity Wavefront Discovery.

All 14 QTSK channels are strictly label-blind (zero fault-catalogue inputs):
  0. qts_decoupled_s1          : 100 m basement-fill gradient orthogonal to surface slope (B15, B12)
  1. qts_decoupled_s3          : 300 m kernel-scale decoupled cover-thickness step (B15, B12)
  2. qts_decoupled_s6          : 600 m master half-graben decoupled cover-thickness step (B15, B12)
  3. qts_signed_grav_concord   : Half-graben density-step concordance -grad(grav)*grad(z_base) (B13, B15)
  4. qts_hessian_ridge_s2      : Principal positive Hessian crest of buried-fill step minus surface crest
  5. chi_knick_wavefront       : Cross-drainage smoothed 10 m DEM fluvial knickpoint density (dem10_chi_u8 B1,B2)
  6. chi_raised_footwall_step  : Across-slope gradient of uplifted channel fraction (dem10_chi_u8 B3,B4)
  7. chi_bipolar_headwater     : Headwater-gated 10 m DEM chi-step contrast suppressing trunk rivers (dem10_chi_i16)
  8. lidar_facing_asymmetry    : 1 m LiDAR scarp facing polarity (downface - upface)/(downface + upface + 8)
  9. lidar_graben_cross_ridge  : 1 m LiDAR antithetic graben index sqrt(cross_max * max(downface, upface))
 10. topo10_planar_facet       : 10 m DEM planar triangular-facet coherence across the 24.6% LiDAR gap
 11. multifield_strike_kappa   : Cross-depth spin-2 strike concentration across det_elev, rtp, and z_base
 12. cond_elev_upflow_resid    : Local 5 km elevation-detrended shallow MT conductance anomaly (B17, topo10 B9)
 13. transtension_bstep_couple : Geodetic dilatational-shear strain coupled to buried basement step (B4, B8, B15)

Statistical & Structural Innovations inside the H88-QTSK Lane:
  - De-jittered dual-expectation PU training: excludes ambiguous 0 < d <= 2.0 px cartographic
    digitization-jitter flank pixels from the binary classifier's negative pool inside train_regions
    (with exact inverse-probability negative reweighting so expected positive mass remains calibrated),
    while the kernel regressor continues to learn exact y_kern = max(1 - d/3, 0) on all pixels.
  - Non-leaky L2-regularized full-quadrant boosting (no pixel-random validation_fraction split).
  - Axial geological strike-continuity smoothing along the label-blind spin-2 structure tensor.
  - Paired comparison of constant-prior fusion (Exp 2: H88-QTSK-DUAL) vs radial mapping-completeness
    stratified Dinkelbach allocation (Exp 3: H88-QTSK-STRAT) on identical 8-fold OOF heads.
"""
from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import roc_auc_score

from gems57 import damagezone_envelope, emit, evaluate_holdout, grid as grid_mod, holdout
from gems88 import adhr, physics

ROOT = Path(__file__).resolve().parents[2]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

QTSK_FEATURES: tuple[str, ...] = (
    "qts_decoupled_s1",
    "qts_decoupled_s3",
    "qts_decoupled_s6",
    "qts_signed_grav_concord",
    "qts_hessian_ridge_s2",
    "chi_knick_wavefront",
    "chi_raised_footwall_step",
    "chi_bipolar_headwater",
    "lidar_facing_asymmetry",
    "lidar_graben_cross_ridge",
    "topo10_planar_facet",
    "multifield_strike_kappa",
    "cond_elev_upflow_resid",
    "transtension_bstep_couple",
)

QTSK_CACHE_VERSION = "gems88_qtsk14_v1"
STRIKE_CACHE_VERSION = "gems88_qtsk_strike2_v1"


def _grad_f32(arr: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gy = ndi.gaussian_filter(arr, sigma=sigma, order=[1, 0], mode="nearest").astype(np.float32)
    gx = ndi.gaussian_filter(arr, sigma=sigma, order=[0, 1], mode="nearest").astype(np.float32)
    mag = np.hypot(gx, gy).astype(np.float32)
    return gy, gx, mag


def _hessian_ridge_lambda_plus(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Principal positive ridge curvature (-Hessian largest eigenvalue) for 1D crest sharpening."""
    hxx = ndi.gaussian_filter(arr, sigma=sigma, order=[0, 2], mode="nearest").astype(np.float32)
    hyy = ndi.gaussian_filter(arr, sigma=sigma, order=[2, 0], mode="nearest").astype(np.float32)
    hxy = ndi.gaussian_filter(arr, sigma=sigma, order=[1, 1], mode="nearest").astype(np.float32)
    tr = -(hxx + hyy)
    disc = np.hypot(hxx - hyy, 2.0 * hxy)
    return np.maximum(0.5 * (tr + disc), 0.0).astype(np.float32)


def _dequantize_topo10_band(ds: rasterio.DatasetReader, band_idx: int, fp: np.ndarray) -> np.ndarray:
    q = ds.read(band_idx).astype(np.float32)
    tags = ds.tags(band_idx)
    q_lo = float(tags["q_lo"])
    q_hi = float(tags["q_hi"])
    phys = np.where(q > 0.0, q_lo + (q - 1.0) / 254.0 * (q_hi - q_lo), np.nan).astype(np.float32)
    return physics.clean_band(phys, fp)[0]


def build_or_load_qtsk_memmap(
    grid: grid_mod.Grid | None = None,
    cache_dir: Path | str | None = None,
    data_dir: Path | str | None = None,
) -> tuple[np.memmap, np.memmap, dict]:
    """Build or open cached float32 memmaps:
      - X_qtsk: (n_fp, 14) strictly label-blind QTSK features
      - U_strike: (n_fp, 2) unit geological strike vector (uy, ux) from spin-2 cross-depth tensor
    """
    if grid is None:
        grid = grid_mod.load_grid()
    cdir = Path(cache_dir) if cache_dir is not None else (ROOT / ".cache")
    ddir = Path(data_dir) if data_dir is not None else (ROOT / "data")
    ext = ddir / "external"
    cdir.mkdir(parents=True, exist_ok=True)

    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    n_cols = len(QTSK_FEATURES)

    q_dat = cdir / f"{QTSK_CACHE_VERSION}.dat"
    q_meta = cdir / f"{QTSK_CACHE_VERSION}.json"
    s_dat = cdir / f"{STRIKE_CACHE_VERSION}.dat"

    req_ext = {
        "dem10_chi_100m_u8.tif": _sha256_file(ext / "dem10_chi_100m_u8.tif"),
        "dem10_chi_100m_i16.tif": _sha256_file(ext / "dem10_chi_100m_i16.tif"),
        "lidar_scarp_features_u8.tif": _sha256_file(ext / "lidar_scarp_features_u8.tif"),
        "topo_10m_derived_100m_u8.tif": _sha256_file(ext / "topo_10m_derived_100m_u8.tif"),
    }

    if q_dat.is_file() and q_meta.is_file() and s_dat.is_file():
        meta = json.loads(q_meta.read_text())
        if (
            meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(QTSK_FEATURES)
            and meta.get("ext_hashes") == req_ext
        ):
            q_mm = np.memmap(q_dat, dtype="float32", mode="r", shape=(n_fp, n_cols))
            s_mm = np.memmap(s_dat, dtype="float32", mode="r", shape=(n_fp, 2))
            return q_mm, s_mm, meta

    q_mm = np.memmap(q_dat, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    s_mm = np.memmap(s_dat, dtype="float32", mode="w+", shape=(n_fp, 2))

    with rasterio.open(ddir / "training_features.tif") as src:
        def rd(idx: int) -> np.ndarray:
            return physics.clean_band(src.read(idx), fp)[0]

        rtp = rd(2)
        g2inv = np.maximum(rd(4), 0.0)
        gdil = rd(8)
        det = rd(12)
        grav = rd(13)
        zbase = np.maximum(rd(15), 0.0)
        cond = rd(17)

    # 1. Decoupled Quaternary cover-thickness steps across 100 m, 300 m, 600 m scales
    for col_idx, sig in ((0, 1.0), (1, 3.0), (2, 6.0)):
        zgy, zgx, zmag = _grad_f32(zbase, sig)
        dgy, dgx, dmag = _grad_f32(det, sig)
        cos_ang = np.abs(zgx[ys, xs] * dgx[ys, xs] + zgy[ys, xs] * dgy[ys, xs]) / (
            zmag[ys, xs] * dmag[ys, xs] + 1e-5
        )
        q_mm[:, col_idx] = np.log1p(zmag[ys, xs] * (1.0 - np.clip(cos_ang, 0.0, 1.0))).astype(np.float32)
        if sig == 3.0:
            zgy3, zgx3, zmag3 = zgy, zgx, zmag
            dgy3, dgx3, dmag3 = dgy, dgx, dmag
        else:
            del zgy, zgx, zmag, dgy, dgx, dmag

    # 2. Signed half-graben density-step concordance (-grad_3 grav dot grad_3 zbase)
    ggy3, ggx3, gmag3 = _grad_f32(grav, 3.0)
    del grav
    dot_zg = -(zgx3[ys, xs] * ggx3[ys, xs] + zgy3[ys, xs] * ggy3[ys, xs]) / (
        zmag3[ys, xs] * gmag3[ys, xs] + 1e-6
    )
    q_mm[:, 3] = (
        dot_zg * np.sqrt(np.log1p(zmag3[ys, xs]) * np.log1p(gmag3[ys, xs] * 100.0))
    ).astype(np.float32)
    del ggy3, ggx3, gmag3, dot_zg

    # 3. Buried basement-step Hessian positive ridge curvature minus surface det_elev crest
    _, _, zlog_mag2 = _grad_f32(np.log1p(zbase), 1.8)
    _, _, d_mag2 = _grad_f32(det, 1.8)
    z_crest = _hessian_ridge_lambda_plus(zlog_mag2, 1.6)
    d_crest = _hessian_ridge_lambda_plus(np.log1p(d_mag2), 1.6)
    q_mm[:, 4] = (z_crest[ys, xs] - 0.35 * d_crest[ys, xs]).astype(np.float32)
    del zlog_mag2, d_mag2, z_crest, d_crest, zbase
    gc.collect()

    # 4. Cross-depth spin-2 strike concentration (det_elev + rtp + z_base) & strike unit vectors
    rgy3, rgx3, rmag3 = _grad_f32(rtp, 3.0)
    del rtp
    c2_acc = np.zeros(n_fp, dtype=np.float32)
    s2_acc = np.zeros(n_fp, dtype=np.float32)
    w_acc = np.full(n_fp, 1e-5, dtype=np.float32)
    for gy_f, gx_f, mag_f in ((dgy3, dgx3, dmag3), (rgy3, rgx3, rmag3), (zgy3, zgx3, zmag3)):
        # Strike vector u = (-gy, gx) / mag; spin-2 double angle (cos 2theta, sin 2theta)
        m = mag_f[ys, xs]
        uy = -gy_f[ys, xs] / (m + 1e-6)
        ux = gx_f[ys, xs] / (m + 1e-6)
        w = np.tanh(m / (float(np.percentile(m, 75)) + 1e-5)).astype(np.float32)
        c2_acc += w * (ux * ux - uy * uy)
        s2_acc += w * (2.0 * ux * uy)
        w_acc += w
    c2_grid = np.zeros(grid.shape, dtype=np.float32)
    s2_grid = np.zeros(grid.shape, dtype=np.float32)
    w_grid = np.zeros(grid.shape, dtype=np.float32)
    c2_grid[ys, xs] = c2_acc
    s2_grid[ys, xs] = s2_acc
    w_grid[ys, xs] = w_acc
    c2_sm = ndi.gaussian_filter(c2_grid, sigma=3.5, mode="nearest")
    s2_sm = ndi.gaussian_filter(s2_grid, sigma=3.5, mode="nearest")
    w_sm = ndi.gaussian_filter(w_grid, sigma=3.5, mode="nearest") + 1e-5
    r_len = np.hypot(c2_sm[ys, xs], s2_sm[ys, xs])
    kappa = np.clip(r_len / w_sm[ys, xs], 0.0, 1.0).astype(np.float32)
    theta_strike = 0.5 * np.arctan2(s2_sm[ys, xs], c2_sm[ys, xs])
    s_mm[:, 0] = np.sin(theta_strike).astype(np.float32)  # uy
    s_mm[:, 1] = np.cos(theta_strike).astype(np.float32)  # ux
    q_mm[:, 11] = kappa
    del rgy3, rgx3, rmag3, dgy3, dgx3, dmag3, zgy3, zgx3, c2_grid, s2_grid, w_grid, c2_sm, s2_sm, w_sm

    # 5. Geodetic transtensional dilation coupled to buried basement-step magnitude
    q_mm[:, 13] = (
        np.arcsinh(gdil[ys, xs] / 15.0)
        * np.log1p(g2inv[ys, xs] / 10.0)
        * np.log1p(zmag3[ys, xs])
    ).astype(np.float32)
    del gdil, g2inv, zmag3, det
    gc.collect()

    # 6. Fluvial chi-knickpoint wavefront & raised-footwall transition (dem10_chi_100m_u8 & i16)
    with rasterio.open(ext / "dem10_chi_100m_u8.tif") as ds:
        chan_n = ds.read(1).astype(np.float32)
        knick_n = ds.read(2).astype(np.float32)
        raised_n = ds.read(3).astype(np.float32)
        valid_n = np.maximum(ds.read(4).astype(np.float32), 1.0)
    knick_sm = ndi.gaussian_filter(knick_n, sigma=2.5, mode="nearest")
    chan_sm = ndi.gaussian_filter(chan_n, sigma=2.5, mode="nearest")
    knick_rate_loc = knick_n[ys, xs] / (chan_n[ys, xs] + 1.0)
    knick_wave = knick_sm[ys, xs] / (chan_sm[ys, xs] + 0.35)
    q_mm[:, 5] = np.log1p(0.5 * knick_rate_loc + 0.5 * knick_wave).astype(np.float32)

    raised_frac = (raised_n / valid_n).astype(np.float32)
    _, _, rstep2 = _grad_f32(raised_frac, 2.0)
    q_mm[:, 6] = np.log1p(rstep2[ys, xs] * 25.0).astype(np.float32)
    del chan_n, knick_n, raised_n, valid_n, knick_sm, chan_sm, raised_frac, rstep2

    with rasterio.open(ext / "dem10_chi_100m_i16.tif") as ds:
        smax = ds.read(1).astype(np.float32)
        smin = ds.read(2).astype(np.float32)
        larea = ds.read(4).astype(np.float32)
    has_chan = (larea > -30000.0) & (smax > -30000.0) & (smin > -30000.0)
    log10_a = np.where(has_chan, larea / 1000.0, 7.5).astype(np.float32)
    # Headwater / piedmont fan gate: pass log10(A in m^2) <= 6.8 (<6.3 km^2), suppress trunk rivers (>50 km^2)
    hw_gate = 1.0 / (1.0 + np.exp((log10_a - 6.7) / 0.55))
    bipolar_raw = np.where(has_chan, np.maximum(smax - smin, 0.0) / 1000.0 * hw_gate, 0.0).astype(np.float32)
    bipolar_sm = ndi.gaussian_filter(bipolar_raw, sigma=2.2, mode="nearest")
    q_mm[:, 7] = np.log1p(5.0 * (0.45 * bipolar_raw[ys, xs] + 0.55 * bipolar_sm[ys, xs])).astype(np.float32)
    del smax, smin, larea, has_chan, log10_a, hw_gate, bipolar_raw, bipolar_sm
    gc.collect()

    # 7. 1 m LiDAR scarp facing polarity & antithetic graben cross-scarp index
    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as ds:
        down_m = ds.read(6)[ys, xs].astype(np.float32)
        up_m = ds.read(7)[ys, xs].astype(np.float32)
        cross_m = ds.read(8)[ys, xs].astype(np.float32)
        lv = ds.read(12)[ys, xs] > 0
    asym = np.abs(down_m - up_m) / (down_m + up_m + 8.0) * np.log1p(np.maximum(down_m, up_m) / 16.0)
    graben = np.sqrt(cross_m * np.maximum(down_m, up_m)) / 32.0
    q_mm[:, 8] = np.where(lv, asym, -1.0).astype(np.float32)
    q_mm[:, 9] = np.where(lv, graben, -1.0).astype(np.float32)
    del down_m, up_m, cross_m, lv, asym, graben

    # 8. 10 m DEM planar triangular-facet coherence + elevation-detrended MT conductance anomaly
    with rasterio.open(ext / "topo_10m_derived_100m_u8.tif") as ds:
        steep_f = _dequantize_topo10_band(ds, 3, fp)
        slope_sd = _dequantize_topo10_band(ds, 4, fp)
        asp_coh = _dequantize_topo10_band(ds, 7, fp)
        dem10 = _dequantize_topo10_band(ds, 9, fp)
    facet = (steep_f * (asp_coh ** 2)) / (slope_sd + 1.25)
    q_mm[:, 10] = np.log1p(facet[ys, xs] * 12.0).astype(np.float32)
    del steep_f, slope_sd, asp_coh, facet

    # Local 5 km elevation-regressed MT conductance residual: separates elevated range-front clay caps
    # from closed basin-bottom saline playas (where cond is high only because local elevation is minimal)
    cond_loc = ndi.gaussian_filter(cond, sigma=45.0, mode="nearest")
    dem_loc = ndi.gaussian_filter(dem10, sigma=45.0, mode="nearest")
    elev_anom_up = np.tanh((dem10[ys, xs] - dem_loc[ys, xs]) / 80.0).astype(np.float32)
    cond_resid = (cond[ys, xs] - cond_loc[ys, xs]) * (1.0 + 0.5 * np.maximum(elev_anom_up, 0.0))
    q_mm[:, 12] = cond_resid.astype(np.float32)
    del cond, dem10, cond_loc, dem_loc, elev_anom_up, cond_resid
    gc.collect()

    q_mm.flush()
    s_mm.flush()
    for j in range(n_cols):
        if not np.isfinite(q_mm[:, j]).all():
            raise AssertionError(f"Non-finite values in QTSK column {QTSK_FEATURES[j]}")
    if not np.isfinite(s_mm).all():
        raise AssertionError("Non-finite values in strike unit vector memmap")

    meta = {
        "version": QTSK_CACHE_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(QTSK_FEATURES),
        "ext_hashes": req_ext,
    }
    q_meta.write_text(json.dumps(meta, indent=2) + "\n")
    del q_mm, s_mm
    gc.collect()
    return (
        np.memmap(q_dat, dtype="float32", mode="r", shape=(n_fp, n_cols)),
        np.memmap(s_dat, dtype="float32", mode="r", shape=(n_fp, 2)),
        meta,
    )


def run_single_feature_canaries(
    grid: grid_mod.Grid,
    X_qtsk: np.ndarray,
    folds_by_seed: dict[int, list[dict]],
    max_neg_sample: int = 200_000,
    auc_ceiling: float = 0.90,
) -> dict:
    """Protocol Rule 4: test EVERY new feature individually on withheld whole-component faults
    across seeds 20 & 21 before fitting any model. Symmetric AUC > 0.90 aborts immediately.
    """
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    fp_idx = np.full(grid.shape, -1, dtype=np.int32)
    fp_idx[ys, xs] = np.arange(ys.size, dtype=np.int32)

    pos_rows: list[np.ndarray] = []
    neg_rows: list[np.ndarray] = []
    rng = np.random.default_rng(20261024)
    for seed in sorted(folds_by_seed):
        for fold in folds_by_seed[seed]:
            act = fold["region"] & fp & ~fold["masked_known"]
            tr = fold["truth"] & act
            neg = act & ~tr
            p_i = fp_idx[tr]
            n_i = fp_idx[neg]
            if n_i.size > max_neg_sample // 8:
                n_i = rng.choice(n_i, size=max_neg_sample // 8, replace=False)
            pos_rows.append(p_i)
            neg_rows.append(n_i)
    p_all = np.concatenate(pos_rows)
    n_all = np.concatenate(neg_rows)
    y = np.concatenate([np.ones(p_all.size, dtype=np.int8), np.zeros(n_all.size, dtype=np.int8)])
    idx_all = np.concatenate([p_all, n_all])

    rows = []
    worst_sym = 0.0
    worst_name = ""
    for j, name in enumerate(QTSK_FEATURES):
        vals = np.asarray(X_qtsk[idx_all, j], dtype=np.float64)
        auc = float(roc_auc_score(y, vals))
        sym = float(max(auc, 1.0 - auc))
        if sym > worst_sym:
            worst_sym = sym
            worst_name = name
        rows.append(
            {
                "feature": name,
                "raw_auc": round(auc, 6),
                "symmetric_auc": round(sym, 6),
                "pass_le_0p90": bool(sym <= auc_ceiling),
            }
        )
    passed = bool(worst_sym <= auc_ceiling)
    if not passed:
        raise RuntimeError(
            f"LEAKAGE CANARY ABORT: feature {worst_name!r} symmetric AUC {worst_sym:.5f} > {auc_ceiling}"
        )
    return {
        "passed": passed,
        "auc_ceiling": auc_ceiling,
        "n_withheld_positives_pooled": int(p_all.size),
        "n_background_negatives_sampled": int(n_all.size),
        "max_symmetric_auc": round(worst_sym, 6),
        "max_feature": worst_name,
        "features": rows,
    }


def _fit_dejittered_dual_models(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    seed: int,
    flank_exclude_px: float = 2.0,
    max_zero_neg: int = 140_000,
    n_ensemble: int = 1,
) -> tuple[list[HistGradientBoostingClassifier], list[HistGradientBoostingRegressor]]:
    """De-jittered dual-expectation fit strictly inside domain_fp (disjoint from test_region):
      - Classifier excludes ambiguous 0 < d <= flank_exclude_px cartographic-jitter flank pixels
        from its hard-negative set, reweighting clean d > flank_exclude_px background negatives
        so total negative sample weight matches the full non-positive domain mass.
      - Kernel regressor fits exact y_kern = max(1 - d/3, 0) across positives + near flanks + background.
    """
    ys_fp, xs_fp = np.nonzero(fp_mask)
    d_pos_grid = ndi.distance_transform_edt(~pos_grid).astype(np.float32)
    d_all = d_pos_grid[ys_fp, xs_fp]
    del d_pos_grid

    dom_idx = np.flatnonzero(domain_fp)
    d_dom = d_all[dom_idx]
    pos_mask = d_dom == 0.0
    flank_mask = (d_dom > 0.0) & (d_dom < 3.0)
    clean_neg_mask = d_dom > flank_exclude_px
    far_zero_mask = d_dom >= 3.0

    pos_idx = dom_idx[pos_mask]
    flank_idx = dom_idx[flank_mask]
    clean_neg_idx = dom_idx[clean_neg_mask]
    far_zero_idx = dom_idx[far_zero_mask]

    rng = np.random.default_rng(seed)
    # 1. Classifier training index: positives (d==0) + subsampled clean negatives (d > flank_exclude_px)
    n_nonpos_total = int(dom_idx.size - pos_idx.size)
    if clean_neg_idx.size > max_zero_neg:
        sub_cneg = np.sort(rng.choice(clean_neg_idx, size=max_zero_neg, replace=False))
        w_cneg = float(n_nonpos_total) / float(max_zero_neg)
    else:
        sub_cneg = clean_neg_idx
        w_cneg = float(n_nonpos_total) / float(max(clean_neg_idx.size, 1))

    clf_idx = np.concatenate([pos_idx, sub_cneg])
    clf_w = np.concatenate([
        np.ones(pos_idx.size, dtype=np.float64),
        np.full(sub_cneg.size, w_cneg, dtype=np.float64),
    ])
    clf_y = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int8),
        np.zeros(sub_cneg.size, dtype=np.int8),
    ])
    seq_c = np.argsort(clf_idx)
    clf_idx, clf_w, clf_y = clf_idx[seq_c], clf_w[seq_c], clf_y[seq_c]
    X_clf = adhr.gather_columns(sources, clf_idx)
    perm_c = rng.permutation(clf_idx.size)
    X_clf, clf_y, clf_w = X_clf[perm_c], clf_y[perm_c], clf_w[perm_c]

    clfs: list[HistGradientBoostingClassifier] = []
    for k in range(n_ensemble):
        clf = HistGradientBoostingClassifier(
            max_iter=115,
            learning_rate=0.075,
            max_leaf_nodes=47,
            min_samples_leaf=85,
            l2_regularization=5.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=12,
            random_state=seed + 131 * k,
        )
        clf.fit(X_clf, clf_y, sample_weight=clf_w)
        clfs.append(clf)
    del X_clf, clf_y, clf_w

    # 2. Regressor training index: all near-kernel pixels (d < 3) + subsampled d >= 3 background
    if far_zero_idx.size > max_zero_neg:
        sub_rneg = np.sort(rng.choice(far_zero_idx, size=max_zero_neg, replace=False))
        w_rneg = float(far_zero_idx.size) / float(max_zero_neg)
    else:
        sub_rneg = far_zero_idx
        w_rneg = 1.0
    near_idx = np.concatenate([pos_idx, flank_idx])
    reg_idx = np.concatenate([near_idx, sub_rneg])
    reg_w = np.concatenate([
        np.ones(near_idx.size, dtype=np.float64),
        np.full(sub_rneg.size, w_rneg, dtype=np.float64),
    ])
    seq_r = np.argsort(reg_idx)
    reg_idx, reg_w = reg_idx[seq_r], reg_w[seq_r]
    X_reg = adhr.gather_columns(sources, reg_idx)
    reg_y = np.clip(1.0 - d_all[reg_idx] / 3.0, 0.0, 1.0).astype(np.float32)
    perm_r = rng.permutation(reg_idx.size)
    X_reg, reg_y, reg_w = X_reg[perm_r], reg_y[perm_r], reg_w[perm_r]

    regs: list[HistGradientBoostingRegressor] = []
    for k in range(n_ensemble):
        reg = HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=115,
            learning_rate=0.075,
            max_leaf_nodes=47,
            min_samples_leaf=85,
            l2_regularization=5.0,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=12,
            random_state=seed + 257 * k,
        )
        reg.fit(X_reg, reg_y, sample_weight=reg_w)
        regs.append(reg)
    del X_reg, reg_y, reg_w
    return clfs, regs


def axial_strike_smooth(
    field_2d: np.ndarray,
    U_strike_fp: np.ndarray,
    ys_fp: np.ndarray,
    xs_fp: np.ndarray,
    alpha: float = 0.20,
    step_px: float = 1.25,
) -> np.ndarray:
    """Smooth a 2D probability/self-credit field strictly along local geological strike (label-blind)."""
    uy = U_strike_fp[:, 0] * step_px
    ux = U_strike_fp[:, 1] * step_px
    f_plus = physics._bilinear_at_fp(field_2d, ys_fp, xs_fp, uy, ux)
    f_minus = physics._bilinear_at_fp(field_2d, ys_fp, xs_fp, -uy, -ux)
    out = np.zeros_like(field_2d, dtype=np.float32)
    c = field_2d[ys_fp, xs_fp]
    out[ys_fp, xs_fp] = ((1.0 - 2.0 * alpha) * c + alpha * (f_plus + f_minus)).astype(np.float32)
    return out


def allocate_stratified_dual_regime(
    p_full_raw: np.ndarray,
    m_full_raw: np.ndarray,
    p_phys_raw: np.ndarray,
    m_phys_raw: np.ndarray,
    d_ref_act: np.ndarray,
    act_mask: np.ndarray,
    ys_act: np.ndarray,
    xs_act: np.ndarray,
    U_strike_fp: np.ndarray,
    ys_fp: np.ndarray,
    xs_fp: np.ndarray,
    k_total_truth: float,
    near_share: float = 0.60,
    collar_px: float = 2.24,
    split_px: float = 25.0,
    near_spacing_px: float = 2.55,
    far_spacing_px: float = 2.83,
    dinkelbach_iters: int = 6,
) -> tuple[np.ndarray, np.ndarray]:
    """Completeness-stratified two-regime Dinkelbach allocation (Exp 3: H88-QTSK-STRAT):
      - Near-relay regime (collar_px < d_ref <= split_px): fused QTSK + structural relay posterior,
        allocated with near_share of expected truth mass and near_spacing_px spacing.
      - Blind-basin regime (d_ref > split_px): pure de-jittered 58-channel QTSK discovery posterior,
        allocated with (1 - near_share) of expected truth mass and far_spacing_px spacing.
    Returns (binary_pred_2d, continuous_pre_placement_score_2d).
    """
    shape = act_mask.shape
    near_sel = (d_ref_act > collar_px) & (d_ref_act <= split_px)
    far_sel = d_ref_act > split_px

    p_dual, m_dual = adhr._fuse_log_odds(
        p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, k_total_truth, beta_phys=0.40, pi_unmapped=0.45
    )

    p_near_2d = np.zeros(shape, dtype=np.float32)
    m_near_2d = np.zeros(shape, dtype=np.float32)
    p_near_2d[ys_act[near_sel], xs_act[near_sel]] = p_dual[near_sel]
    m_near_2d[ys_act[near_sel], xs_act[near_sel]] = m_dual[near_sel]
    p_near_2d = axial_strike_smooth(p_near_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.18)
    m_near_2d = np.maximum(axial_strike_smooth(m_near_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.18), p_near_2d)

    p_far_2d = np.zeros(shape, dtype=np.float32)
    m_far_2d = np.zeros(shape, dtype=np.float32)
    p_far_2d[ys_act[far_sel], xs_act[far_sel]] = p_phys_raw[far_sel]
    m_far_2d[ys_act[far_sel], xs_act[far_sel]] = m_phys_raw[far_sel]
    p_far_2d = axial_strike_smooth(p_far_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.22)
    m_far_2d = np.maximum(axial_strike_smooth(m_far_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.22), p_far_2d)

    near_mask_2d = np.zeros(shape, dtype=bool)
    far_mask_2d = np.zeros(shape, dtype=bool)
    near_mask_2d[ys_act[near_sel], xs_act[near_sel]] = True
    far_mask_2d[ys_act[far_sel], xs_act[far_sel]] = True

    k_near = max(float(k_total_truth) * near_share, 50.0)
    k_far = max(float(k_total_truth) * (1.0 - near_share), 50.0)
    s_near = k_near / max(float(p_near_2d[near_mask_2d].sum()), 1e-6)
    s_far = k_far / max(float(p_far_2d[far_mask_2d].sum()), 1e-6)

    pn_cal = np.clip(p_near_2d * s_near, 0.0, 0.95).astype(np.float32)
    mn_cal = np.clip(np.maximum(m_near_2d * min(s_near, 1.35), pn_cal), 0.0, 1.0).astype(np.float32)
    pf_cal = np.clip(p_far_2d * s_far, 0.0, 0.95).astype(np.float32)
    mf_cal = np.clip(np.maximum(m_far_2d * min(s_far, 1.35), pf_cal), 0.0, 1.0).astype(np.float32)

    surf_2d = np.zeros(shape, dtype=np.float32)
    surf_2d[near_mask_2d] = pn_cal[near_mask_2d]
    surf_2d[far_mask_2d] = pf_cal[far_mask_2d]

    alloc_near = emit.dinkelbach_allocate(
        pn_cal,
        mn_cal,
        near_mask_2d,
        budget=None,
        k_truth=k_near,
        min_spacing_px=near_spacing_px,
        dinkelbach_iters=dinkelbach_iters,
    )
    alloc_far = emit.dinkelbach_allocate(
        pf_cal,
        mf_cal,
        far_mask_2d,
        budget=None,
        k_truth=k_far,
        min_spacing_px=far_spacing_px,
        dinkelbach_iters=dinkelbach_iters,
    )
    pred_bin = np.clip(
        alloc_near.emitted.astype(np.float32) + alloc_far.emitted.astype(np.float32), 0.0, 1.0
    ).astype(np.float32)
    return pred_bin, surf_2d


def predict_qtsk_all_arms_fold(
    grid: grid_mod.Grid,
    X_phys_mm: np.ndarray,
    X_qtsk_mm: np.ndarray,
    U_strike_fp: np.ndarray,
    X_v22: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int = 0,
) -> dict[str, np.ndarray]:
    """Fit de-jittered QTSK blind + structural heads ONCE on train_regions (strictly disjoint from
    test_region) and emit fold predictions for Exp 1 (QTSK-PHYS), Exp 2 (QTSK-DUAL), Exp 3 (QTSK-STRAT).
    """
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)

    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

    phys_sources = [X_phys_mm, X_qtsk_mm]
    full_sources = [X_phys_mm, X_qtsk_mm, X_v22, d_over_w_fp]

    dom_phys_tr = train_regions[ys_fp, xs_fp]
    clfs_phys, regs_phys = _fit_dejittered_dual_models(
        phys_sources, dom_phys_tr, visible & train_regions, fp, seed=seed + 17, n_ensemble=1
    )

    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]
    clfs_full, regs_full = _fit_dejittered_dual_models(
        full_sources, dom_struct_tr, train_truth, fp, seed=seed + 53, n_ensemble=1
    )

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    ys_act, xs_act = ys_fp[act_idx], xs_fp[act_idx]
    d_vis_act = d_vis_fp[act_idx]

    p_phys_raw, m_phys_raw = adhr._predict_dual_chunked(clfs_phys, regs_phys, phys_sources, act_idx)
    p_full_raw, m_full_raw = adhr._predict_dual_chunked(clfs_full, regs_full, full_sources, act_idx)
    del clfs_phys, regs_phys, clfs_full, regs_full, d_over_w_fp

    # --- Exp 1: H88-QTSK-PHYS (Pure 58-col zero-catalogue blind discovery) ---
    s1 = float(k_est) / max(float(p_phys_raw.sum()), 1e-6)
    p1_cal = np.clip(p_phys_raw * s1, 0.0, 1.0).astype(np.float32)
    m1_cal = np.clip(m_phys_raw * hid_ratio, p1_cal, 1.0).astype(np.float32)
    p1_2d = adhr.scatter_fp(p1_cal, ys_act, xs_act, grid.shape)
    m1_2d = adhr.scatter_fp(m1_cal, ys_act, xs_act, grid.shape)
    p1_2d = axial_strike_smooth(p1_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.18)
    m1_2d = np.maximum(axial_strike_smooth(m1_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.18), p1_2d)
    p1_2d[~allowed] = 0.0
    m1_2d[~allowed] = 0.0
    alloc1 = emit.dinkelbach_allocate(
        p1_2d, m1_2d, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # --- Exp 2: H88-QTSK-DUAL (Full 81-col de-jittered QTSK + visible relay fusion) ---
    p_f2, m_f2 = adhr._fuse_log_odds(
        p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, k_est, beta_phys=0.38, pi_unmapped=0.50
    )
    p2_2d = adhr.scatter_fp(p_f2, ys_act, xs_act, grid.shape)
    m2_2d = adhr.scatter_fp(m_f2, ys_act, xs_act, grid.shape)
    p2_2d = axial_strike_smooth(p2_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.16)
    m2_2d = np.maximum(axial_strike_smooth(m2_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.16), p2_2d)
    p2_2d[~allowed] = 0.0
    m2_2d[~allowed] = 0.0
    alloc2 = emit.dinkelbach_allocate(
        p2_2d, m2_2d, allowed, budget=None, k_truth=k_est, min_spacing_px=2.05, dinkelbach_iters=6
    )

    # --- Exp 3: H88-QTSK-STRAT (Completeness-stratified near-relay 60% + blind-basin 40%) ---
    pred_exp3, _ = allocate_stratified_dual_regime(
        p_full_raw,
        m_full_raw,
        p_phys_raw,
        m_phys_raw,
        d_vis_act,
        allowed,
        ys_act,
        xs_act,
        U_strike_fp,
        ys_fp,
        xs_fp,
        k_total_truth=k_est,
        near_share=0.60,
        collar_px=2.24,
        split_px=25.0,
        near_spacing_px=2.55,
        far_spacing_px=2.83,
        dinkelbach_iters=6,
    )

    return {
        "exp1_qtsk_phys": alloc1.emitted.astype(np.float32),
        "exp2_qtsk_dual": alloc2.emitted.astype(np.float32),
        "exp3_qtsk_strat": pred_exp3,
    }


def score_pooled_and_blind_stratum(
    grid: grid_mod.Grid,
    folds_by_seed: dict[int, list[dict]],
    preds_by_arm: dict[str, dict[tuple[int, int], np.ndarray]],
    baseline_arm: str = "control_adhr",
    block_side: int = 200,
    bootstrap_draws: int = 400,
) -> dict:
    """Score all arms strictly through vendor/gems57/evaluate_holdout.py (evaluate + pooled_summary)
    on both the full holdout (n = 22,893) and the blind-basin stratum d_vis > 25 px (n = 3,117).
    """
    arms = list(preds_by_arm.keys())
    terms_full: dict[str, np.ndarray | None] = {a: None for a in arms}
    terms_gt25: dict[str, np.ndarray | None] = {a: None for a in arms}
    per_fold: dict[str, list[dict]] = {a: [] for a in arms}
    withheld_full = 0
    withheld_gt25 = 0

    for seed in sorted(folds_by_seed):
        folds = folds_by_seed[seed]
        d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
        gt25 = d_vis_grid > 25.0
        for fold in folds:
            qid = int(fold["fold"])
            reg_full = fold["region"] & grid.footprint & ~fold["masked_known"]
            far_valid = reg_full & gt25
            far_truth = fold["truth"] & far_valid
            withheld_full += int((fold["truth"] & reg_full).sum())
            withheld_gt25 += int(far_truth.sum())
            far_fold = {
                **fold,
                "truth": far_truth,
                "region": far_valid,
                "masked_known": np.zeros_like(far_valid),
            }
            for a in arms:
                p = preds_by_arm[a][(seed, qid)]
                sc, bt = evaluate_holdout.evaluate(p, fold, g_fp := grid.footprint, block_side=block_side)
                _, bt_far = evaluate_holdout.evaluate(p, far_fold, g_fp, block_side=block_side)
                terms_full[a] = bt if terms_full[a] is None else (terms_full[a] + bt)
                terms_gt25[a] = bt_far if terms_gt25[a] is None else (terms_gt25[a] + bt_far)
                n_dots = int((p[reg_full] > 0).sum())
                n_far = int((p[far_valid] > 0).sum())
                per_fold[a].append(
                    {
                        "seed": seed,
                        "fold": fold["name"],
                        "dti": round(float(sc["dti"]), 6),
                        "dots": n_dots,
                        "dots_gt25": n_far,
                        "share_gt25": round(float(n_far) / max(n_dots, 1), 5),
                    }
                )

    def _collect(terms_map: dict[str, np.ndarray | None], boot_seed: int) -> dict:
        out = {}
        base_summary = evaluate_holdout.pooled_summary(
            terms_map, draws=bootstrap_draws, seed=boot_seed, candidate=baseline_arm
        )
        for a in arms:
            if a == baseline_arm:
                sc_a = base_summary["scores"][a]
                out[a] = {
                    "pooled_dti": round(float(sc_a["dti"]), 6),
                    "ci95": [round(float(x), 6) for x in sc_a["ci95"]],
                    "paired_delta_vs_adhr": 0.0,
                    "paired_delta_ci95": [0.0, 0.0],
                }
            else:
                s_cand = evaluate_holdout.pooled_summary(
                    terms_map, draws=bootstrap_draws, seed=boot_seed, candidate=a
                )
                sc_a = s_cand["scores"][a]
                pd_a = s_cand["paired_differences"][baseline_arm]
                out[a] = {
                    "pooled_dti": round(float(sc_a["dti"]), 6),
                    "ci95": [round(float(x), 6) for x in sc_a["ci95"]],
                    "paired_delta_vs_adhr": round(float(pd_a["delta"]), 6),
                    "paired_delta_ci95": [round(float(x), 6) for x in pd_a["ci95"]],
                }
        return out

    return {
        "evaluator_version": evaluate_holdout.VERSION,
        "block_side_px": block_side,
        "bootstrap_draws": bootstrap_draws,
        "withheld_positive_pixels_full": withheld_full,
        "withheld_positive_pixels_gt25": withheld_gt25,
        "overall": _collect(terms_full, boot_seed=1729),
        "blind_basin_gt25": _collect(terms_gt25, boot_seed=2718),
        "per_fold": per_fold,
    }


def fit_qtsk_production_oof(
    grid: grid_mod.Grid,
    X_phys_mm: np.ndarray,
    X_qtsk_mm: np.ndarray,
    U_strike_fp: np.ndarray,
    folds_by_seed: dict[int, list[dict]],
    vis_cache: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]],
    vis_prod: tuple[np.ndarray, np.ndarray, np.ndarray],
    cache_dir: Path | None = None,
) -> dict[str, np.ndarray]:
    """4-quadrant out-of-fold physical head + 2-seed component-holdout structural head across footprint,
    matching adhr.fit_and_emit_production_adhr's exact out-of-fold protocol with zero in-sample leakage.
    """
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    c_npz = (Path(cache_dir) if cache_dir is not None else (ROOT / ".cache")) / "qtsk_prod_oof_v1.npz"
    if c_npz.is_file():
        z = np.load(c_npz, allow_pickle=False)
        e2 = np.zeros(grid.shape, dtype=np.float32)
        e3 = np.zeros(grid.shape, dtype=np.float32)
        if len(z["exp2_yx"]):
            e2[z["exp2_yx"][:, 0], z["exp2_yx"][:, 1]] = 1.0
        if len(z["exp3_yx"]):
            e3[z["exp3_yx"][:, 0], z["exp3_yx"][:, 1]] = 1.0
        s2 = adhr.scatter_fp(z["exp2_surf_fp"], ys_fp, xs_fp, grid.shape)
        s3 = adhr.scatter_fp(z["exp3_surf_fp"], ys_fp, xs_fp, grid.shape)
        z.close()
        return {
            "exp2_pred": e2,
            "exp2_surface": s2,
            "exp3_pred": e3,
            "exp3_surface": s3,
        }

    d_fullcat = ndi.distance_transform_edt(~grid.catalogue).astype(np.float32)
    allowed_prod = fp & (d_fullcat > 2.0)
    act_idx = np.flatnonzero(allowed_prod[ys_fp, xs_fp])
    ys_act, xs_act = ys_fp[act_idx], xs_fp[act_idx]
    d_cat_act = d_fullcat[ys_act, xs_act]

    phys_sources = [X_phys_mm, X_qtsk_mm]
    folds_q4 = folds_by_seed[20]
    p_phys_raw = np.zeros(act_idx.size, dtype=np.float32)
    m_phys_raw = np.zeros(act_idx.size, dtype=np.float32)
    covered = np.zeros(act_idx.size, dtype=bool)
    for q_idx, f_q in enumerate(folds_q4):
        train_dom_q = (~f_q["region"])[ys_fp, xs_fp]
        c_q, r_q = _fit_dejittered_dual_models(
            phys_sources,
            train_dom_q,
            grid.catalogue,
            fp,
            seed=880510 + q_idx,
            max_zero_neg=120_000,
            n_ensemble=1,
        )
        mask_q = f_q["region"][ys_act, xs_act]
        if q_idx == len(folds_q4) - 1:
            mask_q = mask_q | (~covered)
        covered |= mask_q
        pq, mq = adhr._predict_dual_chunked(c_q, r_q, phys_sources, act_idx[mask_q])
        p_phys_raw[mask_q] = pq
        m_phys_raw[mask_q] = mq
        del c_q, r_q, pq, mq
        gc.collect()

    struct_clfs: list[HistGradientBoostingClassifier] = []
    struct_regs: list[HistGradientBoostingRegressor] = []
    w_laws: list[damagezone_envelope.WidthLaw] = []
    ratios: list[float] = []
    for seed in sorted(folds_by_seed):
        folds = folds_by_seed[seed]
        vis_s = folds[0]["visible"]
        X_v22, dv_s, cl_s = vis_cache[seed]
        reg_s = np.zeros(grid.shape, dtype=bool)
        tr_s = np.zeros(grid.shape, dtype=bool)
        for f in folds:
            reg_s |= f["region"]
            tr_s |= f["truth"]
        ratios.append(float(tr_s.sum()) / max(float((vis_s & reg_s).sum()), 1.0))
        pop_fp = tr_s[ys_fp, xs_fp]
        wlaw = damagezone_envelope.fit_width_law(cl_s, dv_s, pop_fp, quantile=0.90, l0_px=40.0)
        w_laws.append(wlaw)
        dow_s = (dv_s / np.maximum(wlaw.half_width(cl_s), 1e-6)).astype(np.float32)
        dom_s = (reg_s & ~vis_s)[ys_fp, xs_fp]
        cs, rs = _fit_dejittered_dual_models(
            [X_phys_mm, X_qtsk_mm, X_v22, dow_s],
            dom_s,
            tr_s,
            fp,
            seed=880600 + seed,
            max_zero_neg=140_000,
            n_ensemble=1,
        )
        struct_clfs.extend(cs)
        struct_regs.extend(rs)
        del dow_s, dom_s, reg_s, tr_s
        gc.collect()

    X_v22_prod, dv_prod, cl_prod = vis_prod
    hw_prod = np.mean([wl.half_width(cl_prod) for wl in w_laws], axis=0).astype(np.float32)
    dow_prod = (dv_prod / np.maximum(hw_prod, 1e-6)).astype(np.float32)
    prod_sources = [X_phys_mm, X_qtsk_mm, X_v22_prod, dow_prod]

    hid_ratio_mean = float(np.mean(ratios))
    k_prod = float(grid.catalogue.sum()) * hid_ratio_mean

    p_full_raw, m_full_raw = adhr._predict_dual_chunked(struct_clfs, struct_regs, prod_sources, act_idx)
    del struct_clfs, struct_regs, prod_sources, dow_prod, hw_prod
    gc.collect()

    # Production Arm 2: H88-QTSK-DUAL
    p_f2, m_f2 = adhr._fuse_log_odds(
        p_full_raw, m_full_raw, p_phys_raw, m_phys_raw, k_prod, beta_phys=0.38, pi_unmapped=0.50
    )
    p2_2d = adhr.scatter_fp(p_f2, ys_act, xs_act, grid.shape)
    m2_2d = adhr.scatter_fp(m_f2, ys_act, xs_act, grid.shape)
    p2_2d = axial_strike_smooth(p2_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.16)
    m2_2d = np.maximum(axial_strike_smooth(m2_2d, U_strike_fp, ys_fp, xs_fp, alpha=0.16), p2_2d)
    p2_2d[~allowed_prod] = 0.0
    m2_2d[~allowed_prod] = 0.0
    alloc_exp2 = emit.dinkelbach_allocate(
        p2_2d,
        m2_2d,
        allowed_prod,
        budget=None,
        k_truth=k_prod,
        min_spacing_px=2.05,
        dinkelbach_iters=8,
    )

    # Production Arm 3: H88-QTSK-STRAT (60% near-relay, 40% blind-basin >25 px)
    pred_exp3, surf_exp3 = allocate_stratified_dual_regime(
        p_full_raw,
        m_full_raw,
        p_phys_raw,
        m_phys_raw,
        d_cat_act,
        allowed_prod,
        ys_act,
        xs_act,
        U_strike_fp,
        ys_fp,
        xs_fp,
        k_total_truth=float(grid.catalogue.sum()) * 0.45,
        near_share=0.60,
        collar_px=2.24,
        split_px=25.0,
        near_spacing_px=2.55,
        far_spacing_px=2.83,
        dinkelbach_iters=8,
    )

    e2_out = alloc_exp2.emitted.astype(np.float32)
    s2_out = np.clip(p2_2d, 0.0, 1.0).astype(np.float32)
    s3_out = np.clip(surf_exp3, 0.0, 1.0).astype(np.float32)
    y2, x2 = np.nonzero(e2_out > 0)
    y3, x3 = np.nonzero(pred_exp3 > 0)
    np.savez_compressed(
        c_npz,
        exp2_yx=np.column_stack([y2, x2]).astype(np.int32),
        exp3_yx=np.column_stack([y3, x3]).astype(np.int32),
        exp2_surf_fp=s2_out[ys_fp, xs_fp].astype(np.float32),
        exp3_surf_fp=s3_out[ys_fp, xs_fp].astype(np.float32),
    )

    return {
        "exp2_pred": e2_out,
        "exp2_surface": s2_out,
        "exp3_pred": pred_exp3,
        "exp3_surface": s3_out,
    }


def check_surface_spearman_against_registry(
    surface_2d: np.ndarray,
    registry_items: list[tuple[str, Path]],
    fp: np.ndarray,
    sample_pixels: int = 250_000,
    rho_ceiling: float = 0.90,
) -> dict:
    """Protocol Rule 1: check Spearman rank-correlation of the PRE-PLACEMENT continuous score surface
    against EVERY raster in the registry/sibling archive on a fixed deterministic 250k footprint sample.
    """
    ys, xs = np.nonzero(fp)
    rng = np.random.default_rng(882026)
    sel = np.sort(rng.choice(ys.size, size=min(sample_pixels, ys.size), replace=False))
    ry, rx = ys[sel], xs[sel]
    cand_s = surface_2d[ry, rx].astype(np.float64)

    worst_abs = 0.0
    worst_lbl = ""
    worst_raw = 0.0
    blockers = []
    top5 = []
    for label, path in registry_items:
        with rasterio.open(path) as ds:
            arr = ds.read(1)[ry, rx].astype(np.float64)
        arr = np.where(np.isfinite(arr), arr, 0.0)
        if np.std(arr) < 1e-12:
            rho = 0.0
        else:
            r = spearmanr(cand_s, arr).statistic
            rho = 0.0 if (r is None or not np.isfinite(r)) else float(r)
        ar = abs(rho)
        top5.append((ar, round(rho, 6), label))
        if ar > worst_abs:
            worst_abs = ar
            worst_lbl = label
            worst_raw = rho
        if ar > rho_ceiling:
            blockers.append({"label": label, "spearman_rho": round(rho, 6)})
    top5.sort(key=lambda t: t[0], reverse=True)
    return {
        "sample_pixels": int(sel.size),
        "rho_ceiling": rho_ceiling,
        "passed": len(blockers) == 0,
        "max_abs_spearman_rho": round(worst_abs, 6),
        "max_spearman_signed": round(worst_raw, 6),
        "max_spearman_target": worst_lbl,
        "blockers": blockers,
        "top5_abs_correlations": [{"label": lbl, "rho": r} for _, r, lbl in top5[:5]],
    }
