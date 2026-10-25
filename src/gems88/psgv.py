"""H88-PSGV: wavenumber-domain Baranov pseudogravity discordance (8 zero-catalogue channels).

Physics
-------
For a common source distribution, Poisson's relation links the magnetic
potential to the gravity field.  After reduction to the pole (RTP: vertical
magnetization, vertical ambient field), the *pseudogravity* anomaly is the
gravity field that the magnetic sources would produce if magnetization were
replaced by proportional density (Baranov 1957, doi:10.1190/1.1438369;
Blakely 1995, *Potential Theory in Gravity and Magnetic Applications*).
In the wavenumber domain (``k`` in rad/m, ``|k| = sqrt(kx^2+ky^2)``)::

    g_psg_hat(k) = C * RTP_hat(k) / |k|        (C > 0 arbitrary; absorbed by regression)

with a smooth high-pass ``1 - exp(-(|k|/k0)^2)`` (``k0 = 2*pi/50 km``) so the
``1/|k|`` operator does not amplify the regional field, and ``g_psg_hat(0)=0``.

Hydrothermal alteration destroys magnetite along permeable fault damage zones
(magnetization contrast -> 0) while the fault still offsets basement density,
so observed gravity and pseudogravity *disagree* along blind, covered faults.
The 8 channels below measure that disagreement (global/local regression
residual, tilt-phase dislocation, analytic-signal ratio, gradient-direction
discordance) plus a pseudogravity-only edge locator and a cover-gated residual.

Strictly zero catalogue access: ``existing_faults.tif`` is never opened here;
inputs are competition bands B02 ``rtp``, B13 ``iso_grav_anom`` and
B15 ``depth_to_base_surf`` only, cleaned label-blind via ``edge.clean_band``.
Lane preregistration: ``registry/preregistration_psgv88.json``.
Fold/production predictors adapt ``src/gems88/hgvc.py`` verbatim in structure
(learner, fusion, allocator, collar, budgets) with PSGV-8 appended to the two
specialist heads, so the paired holdout contrast isolates these channels.
"""
from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems57 import damagezone_envelope, emit

from . import adhr, edge, hgvc, physics

PSGV_SCHEMA_VERSION = "psgv88-8ch-v1"
CELL_M = 100.0
PAD_PX = 384
K0_WAVELENGTH_M = 50_000.0

PSGV_FEATURES: tuple[str, ...] = (
    "psgv_resid_signed",
    "psgv_resid_crest_s2",
    "psgv_tilt_phase_dislocation",
    "psgv_tiltzero_edge",
    "psgv_log_analytic_ratio",
    "psgv_grad_direction_discordance",
    "psgv_local_slope_deviation",
    "psgv_cover_gated_resid",
)


# ---------------------------------------------------------------- FFT core
def _tapered_pad(a: np.ndarray, pad: int) -> tuple[np.ndarray, tuple[slice, slice]]:
    """Edge-replicate ``a`` by ``pad`` px and cosine-decay the pad to the field mean.

    Returns the padded float64 array (mean-subtracted) and the crop slices that
    recover the original domain.  The taper suppresses periodic wrap-around
    discontinuities without altering values inside the original domain.
    """
    a = np.asarray(a, dtype=np.float64)
    mu = float(a.mean())
    p = np.pad(a - mu, pad, mode="edge")
    ny, nx = p.shape
    wy = np.ones(ny)
    wx = np.ones(nx)
    ramp = 0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, pad + 2)[1:-1]))  # 1 -> 0
    wy[:pad] = ramp[::-1]
    wy[-pad:] = ramp
    wx[:pad] = ramp[::-1]
    wx[-pad:] = ramp
    p *= wy[:, None] * wx[None, :]
    return p, (slice(pad, pad + a.shape[0]), slice(pad, pad + a.shape[1]))


def _kgrid(ny: int, nx: int, dx_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(ky column, kx row, |k| matrix) for an ``(ny, nx)`` real field, rad/m."""
    ky = (2.0 * np.pi * np.fft.fftfreq(ny, d=dx_m))[:, None]
    kx = (2.0 * np.pi * np.fft.rfftfreq(nx, d=dx_m))[None, :]
    return ky, kx, np.sqrt(ky ** 2 + kx ** 2)


def pseudogravity(rtp: np.ndarray, dx_m: float = CELL_M, pad: int = PAD_PX,
                  k0_wavelength_m: float = K0_WAVELENGTH_M) -> np.ndarray:
    """Baranov pseudogravity of an RTP field via the ``1/|k|`` Poisson operator.

    Unit-test identity: applying the vertical-derivative operator ``|k|`` to the
    result recovers the high-passed RTP field (see ``tests/test_psgv.py``).
    """
    p, crop = _tapered_pad(rtp, pad)
    shape = p.shape
    F = np.fft.rfft2(p)
    del p
    _, _, k = _kgrid(shape[0], shape[1], dx_m)
    k0 = 2.0 * np.pi / float(k0_wavelength_m)
    hp = 1.0 - np.exp(-((k / k0) ** 2))
    op = np.zeros_like(k)
    nz = k > 0
    op[nz] = hp[nz] / k[nz]
    out = np.fft.irfft2(F * op, s=shape)
    del F, k, hp, op
    return out[crop].astype(np.float32)


def _fft_derivatives(a: np.ndarray, dx_m: float = CELL_M, pad: int = PAD_PX):
    """Return (vertical derivative, d/dy, d/dx) via FFT multipliers |k|, i*ky, i*kx."""
    p, crop = _tapered_pad(a, pad)
    shape = p.shape
    F = np.fft.rfft2(p)
    del p
    ky, kx, k = _kgrid(shape[0], shape[1], dx_m)
    vdr = np.fft.irfft2(F * k, s=shape)[crop].astype(np.float32)
    gy = np.fft.irfft2(F * (1j * ky), s=shape)[crop].astype(np.float32)
    gx = np.fft.irfft2(F * (1j * kx), s=shape)[crop].astype(np.float32)
    del F, ky, kx, k
    return vdr, gy, gx


def _zscore_fp(a: np.ndarray, fp: np.ndarray) -> np.ndarray:
    v = a[fp]
    mu, sd = float(v.mean()), float(v.std())
    return ((a - mu) / max(sd, 1e-12)).astype(np.float32)


def _hessian_crest(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Scale-normalized principal Hessian bright-ridge crest (same form as hgvc)."""
    a = np.asarray(arr, dtype=np.float32)
    s2 = np.float32(sigma * sigma)
    gxx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 2), mode="nearest") * s2
    gyy = ndi.gaussian_filter(a, sigma=sigma, order=(2, 0), mode="nearest") * s2
    gxy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 1), mode="nearest") * s2
    tr = gxx + gyy
    rad = np.hypot(gxx - gyy, 2.0 * gxy)
    lam = 0.5 * (tr - rad)  # most-negative eigenvalue: bright ridge across-track
    return np.maximum(-lam, 0.0).astype(np.float32)


# ---------------------------------------------------------------- memmap
def build_or_load_psgv_memmap(root: Path, grid, cache_dir: Path) -> tuple[np.memmap, dict]:
    """Stream the 8 label-blind PSGV channels into a disk-backed float32 memmap."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    n_fp = int(ys_fp.size)
    n_cols = len(PSGV_FEATURES)
    dat_path = cache_dir / "x_psgv_8ch_v1.dat"
    meta_path = cache_dir / "x_psgv_8ch_v1.json"
    tf_path = root / "data/training_features.tif"
    cache_key = {"training_features_bytes": tf_path.stat().st_size,
                 "pad_px": PAD_PX, "k0_wavelength_m": K0_WAVELENGTH_M}
    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text())
        if (meta.get("schema") == PSGV_SCHEMA_VERSION and meta.get("shape") == [n_fp, n_cols]
                and meta.get("features") == list(PSGV_FEATURES) and meta.get("cache_key") == cache_key
                and dat_path.stat().st_size == n_fp * n_cols * 4):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    with rasterio.open(tf_path) as src:
        if (src.height, src.width) != grid.shape or src.crs != grid.crs or src.transform != grid.transform:
            raise ValueError("training_features.tif grid mismatch")
        for idx in (2, 13, 15):
            got = src.tags(idx).get("band_name", "")
            if got != physics.EXPECTED_TRAINING_BANDS[idx]:
                raise ValueError(f"band {idx}: expected {physics.EXPECTED_TRAINING_BANDS[idx]!r}, got {got!r}")
        rtp = edge.clean_band(src.read(2), fp)[0]
        grav = edge.clean_band(src.read(13), fp)[0]
        zbase = np.maximum(edge.clean_band(src.read(15), fp)[0], 0.0)

    psg = pseudogravity(rtp)
    del rtp
    gc.collect()
    gz = _zscore_fp(grav, fp)
    pz = _zscore_fp(psg, fp)
    del grav, psg
    gc.collect()

    # Global robust-scale regression grav_z ~ a * psg_z on a footprint subsample.
    sub = np.flatnonzero(fp.ravel())[::7]
    pv = pz.ravel()[sub].astype(np.float64)
    gv = gz.ravel()[sub].astype(np.float64)
    a_glob = float((pv * gv).sum() / max((pv * pv).sum(), 1e-12))
    resid = (gz - np.float32(a_glob) * pz).astype(np.float32)
    del pv, gv, sub

    vdr_g, gy_g, gx_g = _fft_derivatives(gz)
    vdr_p, gy_p, gx_p = _fft_derivatives(pz)
    thdr_g = np.hypot(gy_g, gx_g)
    thdr_p = np.hypot(gy_p, gx_p)
    tilt_g = np.arctan2(vdr_g, thdr_g + 1e-12)
    tilt_p = np.arctan2(vdr_p, thdr_p + 1e-12)
    amp_g = np.sqrt(thdr_g ** 2 + vdr_g ** 2)
    amp_p = np.sqrt(thdr_p ** 2 + vdr_p ** 2)
    del vdr_g, vdr_p
    gc.collect()

    phase_disl = np.abs(np.sin(tilt_g - tilt_p)).astype(np.float32)
    med_amp_p = float(np.median(amp_p[fp]))
    tiltzero = (np.exp(-((tilt_p / (np.pi / 10.0)) ** 2)) * (amp_p / (amp_p + med_amp_p))).astype(np.float32)
    del tilt_g, tilt_p
    eps_a = float(np.percentile(amp_g[fp], 5)) + 1e-12
    log_ratio = (np.log(amp_g + eps_a) - np.log(amp_p + eps_a)).astype(np.float32)
    del amp_g, amp_p
    cross = np.abs(gy_g * gx_p - gx_g * gy_p)
    denom = (thdr_g * thdr_p) + 1e-12
    grad_disc = np.clip(cross / denom, 0.0, 1.0).astype(np.float32)
    del gy_g, gx_g, gy_p, gx_p, thdr_g, thdr_p, cross, denom
    gc.collect()

    # Local regression slope deviation (Gaussian moments, sigma = 8 px).
    s = 8.0
    mp = ndi.gaussian_filter(pz, s, mode="nearest")
    mg = ndi.gaussian_filter(gz, s, mode="nearest")
    mpp = ndi.gaussian_filter(pz * pz, s, mode="nearest")
    mpg = ndi.gaussian_filter(pz * gz, s, mode="nearest")
    var_p = np.maximum(mpp - mp * mp, 1e-6)
    a_loc = ((mpg - mp * mg) / var_p).astype(np.float32)
    del mp, mg, mpp, mpg, var_p
    med_a = float(np.median(a_loc[fp]))
    q25, q75 = (float(x) for x in np.percentile(a_loc[fp], [25, 75]))
    slope_dev = (np.abs(a_loc - med_a) / max(q75 - q25, 1e-6)).astype(np.float32)
    del a_loc

    logz = np.log1p(zbase)
    med_lz = float(np.median(logz[fp]))
    q25z, q75z = (float(x) for x in np.percentile(logz[fp], [25, 75]))
    gate = (1.0 / (1.0 + np.exp(-np.clip((logz - med_lz) / max(0.5 * (q75z - q25z), 1e-6), -15, 15)))).astype(np.float32)
    del logz, zbase
    cover_gated = (np.abs(resid) * gate).astype(np.float32)
    del gate
    resid_crest = _hessian_crest(np.abs(resid), sigma=2.0)
    del gz, pz
    gc.collect()

    cols = [resid, resid_crest, phase_disl, tiltzero, log_ratio, grad_disc, slope_dev, cover_gated]
    tmp_path = cache_dir / "x_psgv_8ch_v1.tmp"
    mm = np.memmap(tmp_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    stats = {}
    for j, (name, arr) in enumerate(zip(PSGV_FEATURES, cols)):
        v = np.nan_to_num(np.asarray(arr, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)[ys_fp, xs_fp]
        lo, hi = np.percentile(v, [0.05, 99.95])
        v = np.clip(v, lo, hi).astype(np.float32)
        mm[:, j] = v
        stats[name] = {"clip_lo": float(lo), "clip_hi": float(hi),
                       "mean": float(v.mean()), "std": float(v.std())}
        del v
    mm.flush()
    del mm, cols, resid, resid_crest, phase_disl, tiltzero, log_ratio, grad_disc, slope_dev, cover_gated
    gc.collect()
    tmp_path.replace(dat_path)
    meta = {"schema": PSGV_SCHEMA_VERSION, "shape": [n_fp, n_cols],
            "features": list(PSGV_FEATURES), "cache_key": cache_key,
            "global_regression_slope_grav_on_psg_z": a_glob, "column_stats": stats,
            "inputs": "training_features.tif B02 rtp, B13 iso_grav_anom, B15 depth_to_base_surf (SHA-verified at restore)",
            "zero_catalogue": True}
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta


# ---------------------------------------------------------------- lane folds
def predict_psgv_all_arms_fold(
    grid, X_phys_mm, X_phys_diff, X_hgvc_mm, X_psgv_mm, X_vis22_mm,
    d_vis_fp, comp_len_fp, visible, train_regions, train_truth, test_region,
    seed: int, cache_dir: Path, fold_tag: str,
) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    """Per-fold posteriors + allocations: 2 controls + 3 preregistered PSGV arms.

    Identical in learner/fusion/allocator to ``hgvc.predict_hgvc_all_arms_fold``
    except the two specialist heads append PSGV-8.  Cache files are PSGV-specific.
    """
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    d_vis_act = d_vis_fp[act_idx]

    post_path = Path(cache_dir) / f"psgv_fold_post_{fold_tag}_{PSGV_SCHEMA_VERSION}.npz"
    if post_path.is_file():
        z = np.load(post_path, allow_pickle=False)
        p_phys_44, m_phys_44 = z["p_phys_44"], z["m_phys_44"]
        p_full_67, m_full_67 = z["p_full_67"], z["m_full_67"]
        p_spec_phys, m_spec_phys = z["p_spec_phys"], z["m_spec_phys"]
        p_spec_full, m_spec_full = z["p_spec_full"], z["m_spec_full"]
    else:
        pop_tr_fp = train_truth[ys_fp, xs_fp]
        wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
        d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
        dom_phys_tr = train_regions[ys_fp, xs_fp]
        dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]

        c_p44, r_p44 = adhr._fit_dual_expectation_models(
            [X_phys_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 17, n_ensemble=1)
        p_phys_44, m_phys_44 = adhr._predict_dual_chunked(c_p44, r_p44, [X_phys_mm], act_idx)
        del c_p44, r_p44; gc.collect()

        c_f67, r_f67 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 53, n_ensemble=1)
        p_full_67, m_full_67 = adhr._predict_dual_chunked(c_f67, r_f67, [X_phys_mm, X_vis22_mm, d_over_w_fp], act_idx)
        del c_f67, r_f67; gc.collect()

        c_hp, r_hp = adhr._fit_dual_expectation_models(
            [X_phys_diff, X_hgvc_mm, X_psgv_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 117, n_ensemble=2)
        p_spec_phys, m_spec_phys = adhr._predict_dual_chunked(c_hp, r_hp, [X_phys_diff, X_hgvc_mm, X_psgv_mm], act_idx)
        del c_hp, r_hp; gc.collect()

        c_hf, r_hf = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_hgvc_mm, X_psgv_mm, X_vis22_mm, d_over_w_fp],
            dom_struct_tr, train_truth, fp, seed=seed + 153, n_ensemble=2)
        p_spec_full, m_spec_full = adhr._predict_dual_chunked(
            c_hf, r_hf, [X_phys_mm, X_hgvc_mm, X_psgv_mm, X_vis22_mm, d_over_w_fp], act_idx)
        del c_hf, r_hf, d_over_w_fp; gc.collect()

        np.savez_compressed(post_path, p_phys_44=p_phys_44, m_phys_44=m_phys_44,
                            p_full_67=p_full_67, m_full_67=m_full_67,
                            p_spec_phys=p_spec_phys, m_spec_phys=m_spec_phys,
                            p_spec_full=p_spec_full, m_spec_full=m_spec_full)

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]

    def _emit_arm(p_vec, m_vec, spacing: float = 2.05):
        pg = adhr.scatter_fp(p_vec, ay, ax, grid.shape)
        mg = adhr.scatter_fp(m_vec, ay, ax, grid.shape)
        alloc = emit.dinkelbach_allocate(pg, mg, allowed, budget=None, k_truth=k_est,
                                         min_spacing_px=spacing, dinkelbach_iters=6)
        return (alloc.emitted.astype(np.float32), pg,
                {"n_dots": int(alloc.n_dots), "k_truth_est": float(k_est),
                 "surrogate_dti": float(alloc.surrogate_dti)})

    sc_c1 = float(k_est) / max(float(p_phys_44.sum()), 1e-6)
    p_c1 = np.clip(p_phys_44 * np.float32(sc_c1), 0.0, 1.0).astype(np.float32)
    m_c1 = np.clip(m_phys_44 * np.float32(hid_ratio), p_c1, 1.0).astype(np.float32)
    p_inc, m_inc = adhr._fuse_log_odds(p_full_67, m_full_67, p_phys_44, m_phys_44, k_est, beta_phys=0.35)

    sc_e1 = float(k_est) / max(float(p_spec_phys.sum()), 1e-6)
    p_e1 = np.clip(p_spec_phys * np.float32(sc_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_spec_phys * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)
    p_e2, m_e2 = adhr._fuse_log_odds(p_spec_full, m_spec_full, p_spec_phys, m_spec_phys, k_est, beta_phys=0.38)

    p_phys_poe, m_phys_poe = hgvc.poe_pool_hgvc(p_phys_44, m_phys_44, p_spec_phys, m_spec_phys, d_vis_act)
    p_full_poe, m_full_poe = hgvc.poe_pool_hgvc(p_full_67, m_full_67, p_spec_full, m_spec_full, d_vis_act)
    p_e3, m_e3 = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_est, beta_phys=0.38)

    return {
        "phys44_zero_cat": _emit_arm(p_c1, m_c1),
        "h88_adhr_incumbent": _emit_arm(p_inc, m_inc),
        "exp01_psgv_zero_cat": _emit_arm(p_e1, m_e1),
        "exp02_psgv_single_joint": _emit_arm(p_e2, m_e2),
        "exp03_psgv_poe_conduit": _emit_arm(p_e3, m_e3),
    }


def fit_and_emit_production_psgv(
    grid, X_phys_mm, X_phys_diff, X_hgvc_mm, X_psgv_mm, folds_by_seed,
    sense_src, scarp_fields, vis_by_seed, cache_dir: Path, *,
    near_budget: int = 21_500, far_budget: int = 16_154,
    near_spacing_px: float = 2.85, far_spacing_px: float = 3.05,
    preplacement_gate=None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Strict OOF production cross-fitting + H33-parity allocation (mirrors HGVC)."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    d_fullcat = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    d_full_fp = d_fullcat[ys_fp, xs_fp]
    act_idx = np.flatnonzero(d_full_fp > 2.5)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]
    d_act = d_full_fp[act_idx]

    oof_cache = Path(cache_dir) / f"psgv_prod_oof_{PSGV_SCHEMA_VERSION}.npz"
    if oof_cache.is_file():
        z = np.load(oof_cache, allow_pickle=False)
        p_phys_oof, m_phys_oof = z["p_phys_oof"], z["m_phys_oof"]
        p_full_oof, m_full_oof = z["p_full_oof"], z["m_full_oof"]
    else:
        phys_oof_cache = Path(cache_dir) / f"psgv_prod_phys_oof_{PSGV_SCHEMA_VERSION}.npz"
        if phys_oof_cache.is_file():
            zp = np.load(phys_oof_cache, allow_pickle=False)
            p_phys_oof, m_phys_oof = zp["p_phys_oof"], zp["m_phys_oof"]
        else:
            folds_q4 = folds_by_seed[0][1]
            p_phys_oof = np.zeros(act_idx.size, dtype=np.float32)
            m_phys_oof = np.zeros(act_idx.size, dtype=np.float32)
            covered_p = np.zeros(act_idx.size, dtype=bool)
            for q_idx, f_q in enumerate(folds_q4):
                tr_dom_q = (~f_q["region"])[ys_fp, xs_fp]
                c_q, r_q = adhr._fit_dual_expectation_models(
                    [X_phys_diff, X_hgvc_mm, X_psgv_mm], tr_dom_q,
                    full_cat & (~f_q["region"]), fp, seed=88610 + q_idx, n_ensemble=2)
                mask_q = f_q["region"][ay, ax]
                if q_idx == len(folds_q4) - 1:
                    mask_q = mask_q | (~covered_p)
                covered_p |= mask_q
                pq, mq = adhr._predict_dual_chunked(c_q, r_q, [X_phys_diff, X_hgvc_mm, X_psgv_mm], act_idx[mask_q])
                p_phys_oof[mask_q] = pq
                m_phys_oof[mask_q] = mq
                del c_q, r_q, pq, mq; gc.collect()
            np.savez_compressed(phys_oof_cache, p_phys_oof=p_phys_oof, m_phys_oof=m_phys_oof)

        X_vis_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
            grid, full_cat, sense_src, scarp_fields, cache_dir, "prod_fullcat_psgv")
        p_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        m_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        for seed, folds in folds_by_seed:
            seed_oof_cache = Path(cache_dir) / f"psgv_prod_struct_s{seed}_{PSGV_SCHEMA_VERSION}.npz"
            if seed_oof_cache.is_file():
                zs = np.load(seed_oof_cache, allow_pickle=False)
                p_seed, m_seed = zs["p_seed"], zs["m_seed"]
            else:
                vis_s = folds[0]["visible"]
                X_vis_s, dv_s, cl_s = vis_by_seed[seed]
                reg_all = np.zeros(grid.shape, dtype=bool)
                tr_all = np.zeros(grid.shape, dtype=bool)
                for f in folds:
                    reg_all |= f["region"]
                    tr_all |= f["truth"]
                p_seed = np.zeros(act_idx.size, dtype=np.float32)
                m_seed = np.zeros(act_idx.size, dtype=np.float32)
                covered_s = np.zeros(act_idx.size, dtype=bool)
                for q_idx, f_q in enumerate(folds):
                    tr_reg_q = reg_all & (~f_q["region"])
                    tr_tru_q = tr_all & (~f_q["region"])
                    wlaw_q = damagezone_envelope.fit_width_law(
                        cl_s, dv_s, tr_tru_q[ys_fp, xs_fp], quantile=0.90, l0_px=40.0)
                    dow_s_q = (dv_s / np.maximum(wlaw_q.half_width(cl_s), 1e-6)).astype(np.float32)
                    dom_s_q = (tr_reg_q & ~vis_s)[ys_fp, xs_fp]
                    cs_q, rs_q = adhr._fit_dual_expectation_models(
                        [X_phys_mm, X_hgvc_mm, X_psgv_mm, X_vis_s, dow_s_q],
                        dom_s_q, tr_tru_q, fp, seed=88700 + 10 * seed + q_idx, n_ensemble=1)
                    mask_q = f_q["region"][ay, ax]
                    if q_idx == len(folds) - 1:
                        mask_q = mask_q | (~covered_s)
                    covered_s |= mask_q
                    dow_prod_q = (dv_prod / np.maximum(wlaw_q.half_width(cl_prod), 1e-6)).astype(np.float32)
                    pq, mq = adhr._predict_dual_chunked(
                        cs_q, rs_q, [X_phys_mm, X_hgvc_mm, X_psgv_mm, X_vis_prod, dow_prod_q], act_idx[mask_q])
                    p_seed[mask_q] = pq
                    m_seed[mask_q] = mq
                    del cs_q, rs_q, dow_s_q, dow_prod_q, pq, mq; gc.collect()
                np.savez_compressed(seed_oof_cache, p_seed=p_seed, m_seed=m_seed)
            p_full_acc += p_seed
            m_full_acc += m_seed
            del p_seed, m_seed; gc.collect()
        p_full_oof = (p_full_acc / len(folds_by_seed)).astype(np.float32)
        m_full_oof = (m_full_acc / len(folds_by_seed)).astype(np.float32)
        del X_vis_prod, dv_prod, cl_prod, p_full_acc, m_full_acc; gc.collect()
        np.savez_compressed(oof_cache, p_phys_oof=p_phys_oof, m_phys_oof=m_phys_oof,
                            p_full_oof=p_full_oof, m_full_oof=m_full_oof)

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(p_full_oof, m_full_oof, p_phys_oof, m_phys_oof,
                                           k_prod, beta_phys=0.52, pi_unmapped=0.60)
    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0
    k_near = k_prod * (float(near_budget) / float(near_budget + far_budget))
    k_far = k_prod * (float(far_budget) / float(near_budget + far_budget))

    p_near_raw = 0.55 * p_fused[near_sel] + 0.45 * p_phys_oof[near_sel]
    m_near_raw = 0.55 * m_fused[near_sel] + 0.45 * m_phys_oof[near_sel]
    sc_near = float(k_near) / max(float(p_near_raw.sum()), 1e-6)
    p_near = np.clip(p_near_raw * np.float32(sc_near), 0.0, 1.0).astype(np.float32)
    m_near = np.clip(m_near_raw * np.float32(min(max(sc_near, 0.85), 1.20)), p_near, 1.0).astype(np.float32)

    p_far_raw = 0.15 * p_fused[far_sel] + 0.85 * p_phys_oof[far_sel]
    m_far_raw = 0.15 * m_fused[far_sel] + 0.85 * m_phys_oof[far_sel]
    sc_far = float(k_far) / max(float(p_far_raw.sum()), 1e-6)
    p_far = np.clip(p_far_raw * np.float32(sc_far), 0.0, 1.0).astype(np.float32)
    m_far = np.clip(m_far_raw * np.float32(min(max(sc_far, 0.85), 1.25)), p_far, 1.0).astype(np.float32)

    p_comb = np.empty_like(p_fused)
    m_comb = np.empty_like(m_fused)
    p_comb[near_sel], m_comb[near_sel] = p_near, m_near
    p_comb[far_sel], m_comb[far_sel] = p_far, m_far
    del p_fused, m_fused, p_near_raw, m_near_raw, p_far_raw, m_far_raw, p_near, m_near, p_far, m_far

    p_surface = adhr.scatter_fp(p_comb, ay, ax, grid.shape)
    m_surface = adhr.scatter_fp(m_comb, ay, ax, grid.shape)
    del p_comb, m_comb; gc.collect()

    if preplacement_gate is not None:
        preplacement_gate(p_surface)

    allowed_near = np.zeros(grid.shape, dtype=bool)
    allowed_near[ay[near_sel], ax[near_sel]] = True
    allowed_far = np.zeros(grid.shape, dtype=bool)
    allowed_far[ay[far_sel], ax[far_sel]] = True
    alloc_near = emit.dinkelbach_allocate(p_surface, m_surface, allowed_near, budget=near_budget,
                                          k_truth=k_near, min_spacing_px=near_spacing_px, dinkelbach_iters=8)
    alloc_far = emit.dinkelbach_allocate(p_surface, m_surface, allowed_far, budget=far_budget,
                                         k_truth=k_far, min_spacing_px=far_spacing_px, dinkelbach_iters=8)
    emitted = np.clip(alloc_near.emitted.astype(np.float32) + alloc_far.emitted.astype(np.float32),
                      0.0, 1.0).astype(np.float32)
    dc_dots = d_fullcat[emitted > 0.5]
    meta = {
        "n_dots": int((emitted > 0.5).sum()),
        "n_near_dots": int(alloc_near.n_dots),
        "n_far_dots": int(alloc_far.n_dots),
        "near_spacing_px": float(near_spacing_px),
        "far_spacing_px": float(far_spacing_px),
        "collar_min_d_cat_px": float(dc_dots.min()) if dc_dots.size else 0.0,
        "median_d_cat_px": float(np.median(dc_dots)) if dc_dots.size else 0.0,
        "share_le2": float((dc_dots <= 2.0).mean()) if dc_dots.size else 0.0,
        "share_gt10": float((dc_dots > 10.0).mean()) if dc_dots.size else 0.0,
        "share_gt25": float((dc_dots > 25.0).mean()) if dc_dots.size else 0.0,
        "k_truth_est": float(k_prod),
        "surrogate_dti_near": float(alloc_near.surrogate_dti),
        "surrogate_dti_far": float(alloc_far.surrogate_dti),
        "strictly_out_of_fold_both_heads": True,
    }
    return emitted, p_surface, meta
