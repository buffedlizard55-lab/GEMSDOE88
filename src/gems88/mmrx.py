"""H88-MMRX: Magnetic Marker Restoration (MMRX-16), zero-catalogue channels.

For each pixel, a joint RTP (B02) + isostatic-gravity (B13) structure tensor
gives a candidate strike ``t`` and cross-strike normal ``n``; ``n`` is signed
toward increasing basement depth (B15), i.e. from footwall into hanging-wall
basin.  High-pass RTP is sampled in strips at ``-4n`` (footwall) and
``+4n + s*t`` (hanging wall) for along-strike displacements
``s in {-4,-2,0,2,4}`` px.  A local (sigma=3 px Gaussian-window) correlation
``corr_s`` measures whether displacing the hanging-wall marker texture by
``s`` restores continuity across the candidate boundary; the restoration
*gain* ``max_s corr_s - corr_0`` is the primary measurement.  A low-passed
(sigma=1.5) hanging-wall strip models the short-wavelength attenuation of a
more deeply buried magnetic source; the cross-strike strip-variance ratio
measures that attenuation directly.  The same geometry on high-pass gravity
at ``s in {-4,0,4}`` gives a second-field restoration gain, and
``min(gain_rtp, gain_grav)`` requires both potential fields to restore.

Named non-fault mimic: an unfaulted lithologic/intrusive contact or
depositional pinch-out produces a coincident RTP+gravity step with *no*
displaced-marker restoration gain; ``mmrx_mimic_contact`` encodes exactly
that combination for the learner.  ``existing_faults.tif`` / ``grid.catalogue``
are never read in this module (zero-catalogue feature construction).

Coordinate convention: arrays are ``[y, x]`` with y increasing southward
(transform ``-100`` m row step) and x increasing eastward.  Vectors below
are ``(vx, vy)`` east/south components.  From gradient second moments
``J``, ``(u, v) = (Jyy-Jxx, -2Jxy) = (cos 2*strike, sin 2*strike)`` (strike
measured from +x toward +y), identical convention to
``hgvc._structure_tensor_2theta``.
"""
from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from .edge import clean_band

MMRX_SCHEMA_VERSION = "mmrx88-16ch-v1"
STRIP_PX = 4.0
SHIFTS_RTP = (-4.0, -2.0, 0.0, 2.0, 4.0)
SHIFTS_GRAV = (-4.0, 0.0, 4.0)
WINDOW_SIGMA = 3.0  # legacy name in cache metadata
ALONG_OFFSETS = (-9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0)
ALONG_SIGMA = 6.0

MMRX_FEATURES: tuple[str, ...] = (
    "mmrx_rtp_corr_best",
    "mmrx_rtp_corr0",
    "mmrx_rtp_gain",
    "mmrx_rtp_shift_best",
    "mmrx_rtp_shift_abs",
    "mmrx_rtp_gain_blur",
    "mmrx_rtp_varratio_abs",
    "mmrx_rtp_step",
    "mmrx_rtp_gain_x_coh",
    "mmrx_rtp_best_x_step",
    "mmrx_grav_corr_best",
    "mmrx_grav_gain",
    "mmrx_grav_varratio_abs",
    "mmrx_cross_gain_min",
    "mmrx_mimic_contact",
    "mmrx_depthstep_aligned",
)


def _robust_z(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    vals = np.asarray(arr, dtype=np.float32)[fp][::17]
    q25, q50, q75 = [float(x) for x in np.percentile(vals, [25.0, 50.0, 75.0])]
    iqr = max(q75 - q25, 1e-6)
    out = np.clip((np.asarray(arr, dtype=np.float32) - np.float32(q50)) / np.float32(iqr), -8.0, 8.0).astype(np.float32)
    out[~fp] = 0.0
    return out


def _grad(a: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    gy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 0), mode="nearest").astype(np.float32)
    gx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 1), mode="nearest").astype(np.float32)
    return gy, gx


def compute_geometry(
    rtp: np.ndarray, grav: np.ndarray, depth: np.ndarray, fp: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(tx, ty, nx, ny, coherence)`` full-grid float32 fields.

    ``n = (nx, ny)`` is signed toward increasing smoothed basement depth;
    ``t = (ny, -nx)`` so that rotating ``t`` by +90 deg in (x, y) gives ``n``.
    """
    def _scale(gy: np.ndarray, gx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        s = float(np.percentile(np.hypot(gy, gx)[fp][::23], 90.0)) or 1.0
        return (gy / np.float32(max(s, 1e-9))).astype(np.float32), (gx / np.float32(max(s, 1e-9))).astype(np.float32)

    # Strike must come from the *boundary* (coarse steps in gravity, basement
    # depth and low-pass RTP at ~1 km scale), not from the marker texture
    # itself; a texture tensor picks random strikes inside isotropic fabric.
    gy1, gx1 = _scale(*_grad(rtp, 3.0))
    gy2, gx2 = _scale(*_grad(grav, 3.0))
    gy3, gx3 = _scale(*_grad(depth, 3.0))
    jxx = ndi.gaussian_filter(gx1 * gx1 + gx2 * gx2 + gx3 * gx3, sigma=8.0, mode="nearest").astype(np.float32)
    jyy = ndi.gaussian_filter(gy1 * gy1 + gy2 * gy2 + gy3 * gy3, sigma=8.0, mode="nearest").astype(np.float32)
    jxy = ndi.gaussian_filter(gx1 * gy1 + gx2 * gy2 + gx3 * gy3, sigma=8.0, mode="nearest").astype(np.float32)
    del gy1, gx1, gy2, gx2, gy3, gx3
    u = (jyy - jxx).astype(np.float32)
    v = (-2.0 * jxy).astype(np.float32)
    trace = (jxx + jyy).astype(np.float32)
    coh = (np.hypot(u, v) / (trace + np.float32(1e-9))).astype(np.float32)
    np.clip(coh, 0.0, 1.0, out=coh)
    theta = (0.5 * np.arctan2(v, u)).astype(np.float32)  # strike axis, (-pi/2, pi/2]
    del jxx, jyy, jxy, u, v, trace
    t_x, t_y = np.cos(theta).astype(np.float32), np.sin(theta).astype(np.float32)
    n_x, n_y = (-t_y).astype(np.float32), t_x.astype(np.float32)  # R+90(t) in (x,y)
    del theta
    # Sign n toward increasing basement depth (hanging-wall basin side).
    dgy, dgx = _grad(depth, 3.0)
    flip = (n_x * dgx + n_y * dgy) < 0.0
    del dgy, dgx
    n_x = np.where(flip, -n_x, n_x).astype(np.float32)
    n_y = np.where(flip, -n_y, n_y).astype(np.float32)
    del flip
    # Re-derive t signed so R+90(t) == n exactly: t = (n_y, -n_x).
    t_x, t_y = n_y.astype(np.float32), (-n_x).astype(np.float32)
    return t_x, t_y, n_x, n_y, coh


def _sample(field: np.ndarray, base_y: np.ndarray, base_x: np.ndarray,
            off_y: np.ndarray, off_x: np.ndarray) -> np.ndarray:
    coords_y = (base_y + off_y).astype(np.float32)
    coords_x = (base_x + off_x).astype(np.float32)
    out = ndi.map_coordinates(field, [coords_y, coords_x], order=1, mode="nearest").astype(np.float32)
    del coords_y, coords_x
    return out


def _smooth_along(
    prod: np.ndarray,
    base_y: np.ndarray, base_x: np.ndarray,
    t_y: np.ndarray, t_x: np.ndarray,
) -> np.ndarray:
    """Gaussian-weighted (sigma=6 px, support +/-9 px) smoothing *along strike*.

    The correlation window must extend ~1.8 km along the candidate fault
    (the marker segment being matched) while staying narrow across it;
    an isotropic window either has too few independent samples (small
    sigma) or mixes neighbouring candidate traces (large sigma).
    A sigma=1.2 isotropic pre-smooth gives the window its cross width.
    """
    pre = ndi.gaussian_filter(prod, sigma=1.2, mode="nearest").astype(np.float32)
    acc = np.zeros(prod.shape, dtype=np.float32)
    wsum = np.float32(0.0)
    for k in ALONG_OFFSETS:
        wgt = np.float32(np.exp(-(k * k) / (2.0 * ALONG_SIGMA * ALONG_SIGMA)))
        if k == 0.0:
            acc += wgt * pre
        else:
            kf = np.float32(k)
            acc += wgt * _sample(pre, base_y, base_x, (kf * t_y).astype(np.float32), (kf * t_x).astype(np.float32))
        wsum += wgt
    del pre
    return (acc / wsum).astype(np.float32)


def _strip_correlations(
    field: np.ndarray,
    base_y: np.ndarray, base_x: np.ndarray,
    t_y: np.ndarray, t_x: np.ndarray,
    a_off: tuple[np.ndarray, np.ndarray],
    b_offs: list[tuple[float, tuple[np.ndarray, np.ndarray]]],
) -> tuple[list[np.ndarray], np.ndarray, list[np.ndarray]]:
    """Along-strike window correlations corr_s between strip A and shifted B strips.

    Returns ``(corrs, SAA, SBBS)`` with ``S(.)`` the along-strike window sum
    (:func:`_smooth_along`).  Fields must already be high-passed (local mean
    ~ 0) so uncentred second moments approximate the local correlation.
    """
    A = _sample(field, base_y, base_x, a_off[0], a_off[1])
    SAA = _smooth_along(A * A, base_y, base_x, t_y, t_x)
    corrs: list[np.ndarray] = []
    sbbs: list[np.ndarray] = []
    for _s, (oy, ox) in b_offs:
        B = _sample(field, base_y, base_x, oy, ox)
        SBB = _smooth_along(B * B, base_y, base_x, t_y, t_x)
        SAB = _smooth_along(A * B, base_y, base_x, t_y, t_x)
        del B
        corr = (SAB / np.sqrt(np.maximum(SAA * SBB, np.float32(1e-18)))).astype(np.float32)
        del SAB
        np.clip(corr, -1.0, 1.0, out=corr)
        corrs.append(corr)
        sbbs.append(SBB)
    del A
    return corrs, SAA, sbbs


def marker_restoration_channels(
    rtp_clean: np.ndarray,
    grav_clean: np.ndarray,
    depth_clean: np.ndarray,
    fp: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute the 16 MMRX grids from cleaned full-grid fields (pure function)."""
    rtp_hp = (rtp_clean - ndi.gaussian_filter(rtp_clean, sigma=8.0, mode="nearest")).astype(np.float32)
    grav_hp = (grav_clean - ndi.gaussian_filter(grav_clean, sigma=8.0, mode="nearest")).astype(np.float32)
    rtp_lp = ndi.gaussian_filter(rtp_clean, sigma=2.0, mode="nearest").astype(np.float32)
    rtp_hp_blur = ndi.gaussian_filter(rtp_hp, sigma=1.5, mode="nearest").astype(np.float32)

    t_x, t_y, n_x, n_y, coh = compute_geometry(rtp_clean, grav_clean, depth_clean, fp)

    h, w = fp.shape
    base_y = np.repeat(np.arange(h, dtype=np.float32)[:, None], w, axis=1)
    base_x = np.repeat(np.arange(w, dtype=np.float32)[None, :], h, axis=0)

    d = np.float32(STRIP_PX)
    a_off = ((-d * n_y).astype(np.float32), (-d * n_x).astype(np.float32))

    def _b_offs(shifts) -> list[tuple[float, tuple[np.ndarray, np.ndarray]]]:
        out = []
        for s in shifts:
            sf = np.float32(s)
            out.append((float(s), ((d * n_y + sf * t_y).astype(np.float32),
                                   (d * n_x + sf * t_x).astype(np.float32))))
        return out

    # --- RTP marker restoration -------------------------------------------------
    corrs, SAA, SBBS = _strip_correlations(rtp_hp, base_y, base_x, t_y, t_x, a_off, _b_offs(SHIFTS_RTP))
    corr_stack = np.stack(corrs)
    best_idx = np.argmax(corr_stack, axis=0)
    corr_best = np.max(corr_stack, axis=0).astype(np.float32)
    corr0 = corr_stack[2].astype(np.float32)
    gain = np.clip(corr_best - corr0, -1.0, 1.0).astype(np.float32)
    shifts_arr = np.asarray(SHIFTS_RTP, dtype=np.float32)
    shift_best = shifts_arr[best_idx].astype(np.float32)
    varratio = (0.5 * np.abs(np.log(np.maximum(SBBS[2], np.float32(1e-18)) / np.maximum(SAA, np.float32(1e-18))))).astype(np.float32)
    del corrs, corr_stack, SBBS
    gc.collect()

    # Blurred (burial-attenuated) hanging-wall strips correlated against the
    # *unblurred* footwall strip (one-sided depth attenuation model).
    A = _sample(rtp_hp, base_y, base_x, a_off[0], a_off[1])
    best_blur = np.full(fp.shape, -2.0, dtype=np.float32)
    for _s, (oy, ox) in _b_offs(SHIFTS_RTP):
        Bb = _sample(rtp_hp_blur, base_y, base_x, oy, ox)
        SBB = _smooth_along(Bb * Bb, base_y, base_x, t_y, t_x)
        SAB = _smooth_along(A * Bb, base_y, base_x, t_y, t_x)
        del Bb
        c = (SAB / np.sqrt(np.maximum(SAA * SBB, np.float32(1e-18)))).astype(np.float32)
        del SBB, SAB
        np.maximum(best_blur, np.clip(c, -1.0, 1.0), out=best_blur)
        del c
    del A
    gain_blur = np.clip(best_blur - corr0, -1.0, 1.0).astype(np.float32)
    del best_blur
    gc.collect()

    # --- Gravity restoration (same geometry) ------------------------------------
    corrs_g, SAA_g, SBBS_g = _strip_correlations(grav_hp, base_y, base_x, t_y, t_x, a_off, _b_offs(SHIFTS_GRAV))
    g_stack = np.stack(corrs_g)
    grav_best = np.max(g_stack, axis=0).astype(np.float32)
    grav_gain = np.clip(grav_best - g_stack[1], -1.0, 1.0).astype(np.float32)
    grav_varratio = (0.5 * np.abs(np.log(np.maximum(SBBS_g[1], np.float32(1e-18)) / np.maximum(SAA_g, np.float32(1e-18))))).astype(np.float32)
    del corrs_g, g_stack, SBBS_g, SAA_g
    gc.collect()

    # --- Steps --------------------------------------------------------------------
    b_off0 = ((d * n_y).astype(np.float32), (d * n_x).astype(np.float32))
    step = np.abs(_sample(rtp_lp, base_y, base_x, *b_off0) - _sample(rtp_lp, base_y, base_x, *a_off)).astype(np.float32)
    depth_step = (_sample(depth_clean, base_y, base_x, *b_off0) - _sample(depth_clean, base_y, base_x, *a_off)).astype(np.float32)
    del base_y, base_x, t_x, t_y, n_x, n_y, rtp_hp, grav_hp, rtp_lp, rtp_hp_blur, SAA
    gc.collect()

    step_z = _robust_z(step, fp)
    step_pos = np.clip(step_z, 0.0, 8.0).astype(np.float32)
    gain_clipped = np.clip(gain, 0.0, 1.0).astype(np.float32)

    out = {
        "mmrx_rtp_corr_best": corr_best,
        "mmrx_rtp_corr0": corr0,
        "mmrx_rtp_gain": gain,
        "mmrx_rtp_shift_best": (shift_best / np.float32(4.0)).astype(np.float32),
        "mmrx_rtp_shift_abs": (np.abs(shift_best) / np.float32(4.0)).astype(np.float32),
        "mmrx_rtp_gain_blur": gain_blur,
        "mmrx_rtp_varratio_abs": _robust_z(varratio, fp),
        "mmrx_rtp_step": step_z,
        "mmrx_rtp_gain_x_coh": (gain * coh).astype(np.float32),
        "mmrx_rtp_best_x_step": _robust_z(np.clip(corr_best, 0.0, 1.0) * np.log1p(step), fp),
        "mmrx_grav_corr_best": grav_best,
        "mmrx_grav_gain": grav_gain,
        "mmrx_grav_varratio_abs": _robust_z(grav_varratio, fp),
        "mmrx_cross_gain_min": np.minimum(gain, grav_gain).astype(np.float32),
        "mmrx_mimic_contact": (step_pos * (1.0 - gain_clipped)).astype(np.float32),
        "mmrx_depthstep_aligned": _robust_z(depth_step, fp),
    }
    for v in out.values():
        v[~fp] = 0.0
        assert np.isfinite(v).all(), "non-finite MMRX channel"
    return out


def build_or_load_mmrx_memmap(root: Path, grid, cache_dir: Path):
    """Build/load the (N_fp, 16) float32 MMRX memmap. Zero catalogue reads."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = np.asarray(grid.footprint, dtype=bool)
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    dat = cache_dir / "x_mmrx_16ch_v1.dat"
    meta_p = cache_dir / "x_mmrx_16ch_v1.json"
    feat = Path(root) / "data/training_features.tif"
    cache_key = f"size_{feat.stat().st_size}"
    if dat.is_file() and meta_p.is_file():
        meta = json.loads(meta_p.read_text())
        if meta.get("schema") == MMRX_SCHEMA_VERSION and meta.get("features") == list(MMRX_FEATURES) and meta.get("cache_key") == cache_key:
            return np.memmap(dat, dtype="float32", mode="r", shape=(n_fp, len(MMRX_FEATURES))), meta

    expect = {2: "rtp", 13: "iso_grav_anom", 15: "depth_to_base_surf"}
    cleaned: dict[int, np.ndarray] = {}
    infos: dict[str, dict] = {}
    with rasterio.open(feat) as src:
        for band, name in expect.items():
            found = src.tags(band).get("band_name")
            if found != name:
                raise ValueError(f"band {band} must be {name!r}, got {found!r}")
            cleaned[band], infos[name] = clean_band(src.read(band), fp)

    chans = marker_restoration_channels(cleaned[2], cleaned[13], cleaned[15], fp)
    del cleaned
    gc.collect()

    mm = np.memmap(dat, dtype="float32", mode="w+", shape=(n_fp, len(MMRX_FEATURES)))
    stats = {}
    for j, name in enumerate(MMRX_FEATURES):
        v = chans[name][ys, xs].astype(np.float32)
        mm[:, j] = v
        stats[name] = {"mean": float(v.mean()), "std": float(v.std()),
                       "min": float(v.min()), "max": float(v.max())}
    mm.flush()
    del mm, chans
    meta = {
        "schema": MMRX_SCHEMA_VERSION,
        "features": list(MMRX_FEATURES),
        "cache_key": cache_key,
        "input_sha256_training_features": hashlib.sha256(feat.read_bytes()).hexdigest() if feat.stat().st_size < 50_000_000 else "size-pinned (see registry/data_manifest.json)",
        "bands": expect,
        "band_clean_info": infos,
        "strip_px": STRIP_PX,
        "shifts_rtp": list(SHIFTS_RTP),
        "shifts_grav": list(SHIFTS_GRAV),
        "along_offsets_px": list(ALONG_OFFSETS), "along_sigma_px": ALONG_SIGMA,
        "zero_catalogue_reads": True,
        "column_stats": stats,
    }
    meta_p.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(dat, dtype="float32", mode="r", shape=(n_fp, len(MMRX_FEATURES))), meta


# ---------------------------------------------------------------------------
# Holdout fold + production (reuse shared fitting/emission machinery verbatim)
# ---------------------------------------------------------------------------
from gems57 import damagezone_envelope, emit  # noqa: E402

from . import adhr, bpwd, hgvc  # noqa: E402


def _fold_posteriors(
    grid, X_phys, X_phys_diff, X_hgvc, X_psgv, X_mmrx, X_vis22,
    d_vis_fp, comp_len_fp, visible, train_regions, train_truth,
    test_region, seed, cache_dir: Path, fold_tag: str,
):
    """Fit/load the three MMRX dual-expectation posteriors for one fold."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage: training regions/truth intersect test_region")
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    post_path = Path(cache_dir) / f"mmrx_fold_post_{fold_tag}_{MMRX_SCHEMA_VERSION}.npz"
    if post_path.is_file():
        z = np.load(post_path, allow_pickle=False)
        return act_idx, allowed, (z["p_e1"], z["m_e1"], z["p_jp"], z["m_jp"], z["p_jf"], z["m_jf"])

    wlaw = damagezone_envelope.fit_width_law(
        comp_len_fp, d_vis_fp, train_truth[ys_fp, xs_fp], quantile=0.90, l0_px=40.0)
    dow = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
    dom_phys = train_regions[ys_fp, xs_fp]
    dom_struct = (train_regions & ~visible)[ys_fp, xs_fp]

    # Exp01 head: zero-catalogue PHYS-diff + MMRX-16 (52 ch, HGB dual expectation)
    c1, r1 = adhr._fit_dual_expectation_models(
        [X_phys_diff, X_mmrx], dom_phys, visible & train_regions, fp, seed=seed + 317, n_ensemble=1)
    p_e1, m_e1 = adhr._predict_dual_chunked(c1, r1, [X_phys_diff, X_mmrx], act_idx)
    del c1, r1
    gc.collect()

    # Joint zero-catalogue head: PHYS-diff + MMRX + HGVC + PSGV (92 ch, LightGBM)
    c2, r2 = bpwd._fit_lgbm_dual_models(
        [X_phys_diff, X_mmrx, X_hgvc, X_psgv], dom_phys, visible & train_regions, fp,
        seed=seed + 353, n_ensemble=2)
    p_jp, m_jp = adhr._predict_dual_chunked(c2, r2, [X_phys_diff, X_mmrx, X_hgvc, X_psgv], act_idx)
    del c2, r2
    gc.collect()

    # Joint full head: + PHYS-44 + VIS-23 (123 ch, LightGBM)
    c3, r3 = bpwd._fit_lgbm_dual_models(
        [X_phys, X_mmrx, X_hgvc, X_psgv, X_vis22, dow], dom_struct, train_truth, fp,
        seed=seed + 389, n_ensemble=2)
    p_jf, m_jf = adhr._predict_dual_chunked(
        c3, r3, [X_phys, X_mmrx, X_hgvc, X_psgv, X_vis22, dow], act_idx)
    del c3, r3, dow
    gc.collect()

    np.savez_compressed(post_path, p_e1=p_e1, m_e1=m_e1, p_jp=p_jp, m_jp=m_jp, p_jf=p_jf, m_jf=m_jf)
    return act_idx, allowed, (p_e1, m_e1, p_jp, m_jp, p_jf, m_jf)


def predict_mmrx_fold(
    grid, X_phys, X_phys_diff, X_hgvc, X_psgv, X_mmrx, X_vis22,
    d_vis_fp, comp_len_fp, visible, train_regions, train_truth,
    test_region, seed, cache_dir: Path, fold_tag: str,
) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    """Return emitted arms exp01/exp02/exp03 for one hide-and-recover fold."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    act_idx, allowed, (p_e1r, m_e1r, p_jp, m_jp, p_jf, m_jf) = _fold_posteriors(
        grid, X_phys, X_phys_diff, X_hgvc, X_psgv, X_mmrx, X_vis22,
        d_vis_fp, comp_len_fp, visible, train_regions, train_truth,
        test_region, seed, cache_dir, fold_tag)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)

    def _emit(p_vec, m_vec, spacing: float = 2.05):
        pg = adhr.scatter_fp(p_vec, ay, ax, grid.shape)
        mg = adhr.scatter_fp(m_vec, ay, ax, grid.shape)
        alloc = emit.dinkelbach_allocate(
            pg, mg, allowed, budget=None, k_truth=k_est,
            min_spacing_px=spacing, dinkelbach_iters=6)
        return (alloc.emitted.astype(np.float32), pg,
                {"n_dots": int(alloc.n_dots), "k_truth_est": float(k_est),
                 "surrogate_dti": float(alloc.surrogate_dti)})

    sc = float(k_est) / max(float(p_e1r.sum()), 1e-6)
    p_e1 = np.clip(p_e1r * np.float32(sc), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_e1r * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)

    p_e2, m_e2 = adhr._fuse_log_odds(p_jf, m_jf, p_jp, m_jp, k_est, beta_phys=0.38)
    p_e3, m_e3 = adhr._fuse_log_odds(p_jf, m_jf, p_jp, m_jp, k_est, beta_phys=0.58, pi_unmapped=0.65)

    return {
        "exp01_mmrx_zero_cat": _emit(p_e1, m_e1),
        "exp02_mmrx_joint_spec": _emit(p_e2, m_e2),
        "exp03_mmrx_candidate": _emit(p_e3, m_e3),
    }


def fit_and_emit_production_mmrx(
    grid, X_phys, X_phys_diff, X_hgvc, X_psgv, X_mmrx,
    folds_by_seed, sense_src, scarp_fields, vis_by_seed, cache_dir: Path,
    *, near_budget: int = 21_200, far_budget: int = 16_454,
    near_spacing_px: float = 2.90, far_spacing_px: float = 3.12,
    preplacement_gate=None,
):
    """OOF production for Exp03 (mirrors bpwd.fit_and_emit_production_psgv)."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    d_fullcat = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    d_full_fp = d_fullcat[ys_fp, xs_fp]
    act_idx = np.flatnonzero(d_full_fp > 2.5)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]
    d_act = d_full_fp[act_idx]

    oof_cache = Path(cache_dir) / f"mmrx_prod_oof_{MMRX_SCHEMA_VERSION}.npz"
    if oof_cache.is_file():
        z = np.load(oof_cache, allow_pickle=False)
        p_spec_oof, m_spec_oof = z["p_spec_oof"], z["m_spec_oof"]
        p_full_oof, m_full_oof = z["p_full_oof"], z["m_full_oof"]
    else:
        spec_cache = Path(cache_dir) / f"mmrx_prod_spec_oof_{MMRX_SCHEMA_VERSION}.npz"
        if spec_cache.is_file():
            zs = np.load(spec_cache, allow_pickle=False)
            p_spec_oof, m_spec_oof = zs["p_spec_oof"], zs["m_spec_oof"]
        else:
            folds_q4 = folds_by_seed[0][1]
            p_spec_oof = np.zeros(act_idx.size, dtype=np.float32)
            m_spec_oof = np.zeros(act_idx.size, dtype=np.float32)
            covered = np.zeros(act_idx.size, dtype=bool)
            for q_idx, f_q in enumerate(folds_q4):
                tr_dom = (~f_q["region"])[ys_fp, xs_fp]
                c_q, r_q = bpwd._fit_lgbm_dual_models(
                    [X_mmrx, X_phys_diff, X_psgv, X_hgvc], tr_dom,
                    full_cat & (~f_q["region"]), fp, seed=88930 + q_idx, n_ensemble=2)
                mask_q = f_q["region"][ay, ax]
                if q_idx == len(folds_q4) - 1:
                    mask_q = mask_q | (~covered)
                covered |= mask_q
                pq, mq = adhr._predict_dual_chunked(
                    c_q, r_q, [X_mmrx, X_phys_diff, X_psgv, X_hgvc], act_idx[mask_q])
                p_spec_oof[mask_q] = pq
                m_spec_oof[mask_q] = mq
                del c_q, r_q, pq, mq
                gc.collect()
            np.savez_compressed(spec_cache, p_spec_oof=p_spec_oof, m_spec_oof=m_spec_oof)

        X_vis_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
            grid, full_cat, sense_src, scarp_fields, cache_dir, "prod_fullcat")
        p_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        m_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        for seed, folds in folds_by_seed:
            seed_cache = Path(cache_dir) / f"mmrx_prod_struct_s{seed}_{MMRX_SCHEMA_VERSION}.npz"
            if seed_cache.is_file():
                zs = np.load(seed_cache, allow_pickle=False)
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
                    tr_reg = reg_all & (~f_q["region"])
                    tr_tru = tr_all & (~f_q["region"])
                    wlaw = damagezone_envelope.fit_width_law(
                        cl_s, dv_s, tr_tru[ys_fp, xs_fp], quantile=0.90, l0_px=40.0)
                    dow_s = (dv_s / np.maximum(wlaw.half_width(cl_s), 1e-6)).astype(np.float32)
                    dom = (tr_reg & ~vis_s)[ys_fp, xs_fp]
                    cs, rs = bpwd._fit_lgbm_dual_models(
                        [X_phys, X_mmrx, X_psgv, X_hgvc, X_vis_s, dow_s], dom, tr_tru, fp,
                        seed=89130 + 10 * seed + q_idx, n_ensemble=1)
                    mask_q = f_q["region"][ay, ax]
                    if q_idx == len(folds) - 1:
                        mask_q = mask_q | (~covered_s)
                    covered_s |= mask_q
                    dow_p = (dv_prod / np.maximum(wlaw.half_width(cl_prod), 1e-6)).astype(np.float32)
                    pq, mq = adhr._predict_dual_chunked(
                        cs, rs, [X_phys, X_mmrx, X_psgv, X_hgvc, X_vis_prod, dow_p], act_idx[mask_q])
                    p_seed[mask_q] = pq
                    m_seed[mask_q] = mq
                    del cs, rs, dow_s, dow_p, pq, mq
                    gc.collect()
                np.savez_compressed(seed_cache, p_seed=p_seed, m_seed=m_seed)
            p_full_acc += p_seed
            m_full_acc += m_seed
            del p_seed, m_seed
            gc.collect()
        p_full_oof = (p_full_acc / len(folds_by_seed)).astype(np.float32)
        m_full_oof = (m_full_acc / len(folds_by_seed)).astype(np.float32)
        del X_vis_prod, dv_prod, cl_prod, p_full_acc, m_full_acc
        gc.collect()
        np.savez_compressed(oof_cache, p_spec_oof=p_spec_oof, m_spec_oof=m_spec_oof,
                            p_full_oof=p_full_oof, m_full_oof=m_full_oof)

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(
        p_full_oof, m_full_oof, p_spec_oof, m_spec_oof, k_prod, beta_phys=0.58, pi_unmapped=0.65)

    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0
    p_comb = np.empty_like(p_fused)
    m_comb = np.empty_like(m_fused)
    for sel, w_joint in ((near_sel, 0.42), (far_sel, 0.28)):
        budget = near_budget if sel is near_sel else far_budget
        k_s = k_prod * (float(budget) / float(near_budget + far_budget))
        p_raw = w_joint * p_fused[sel] + (1.0 - w_joint) * p_spec_oof[sel]
        m_raw = w_joint * m_fused[sel] + (1.0 - w_joint) * m_spec_oof[sel]
        sc_s = float(k_s) / max(float(p_raw.sum()), 1e-6)
        p_s = np.clip(p_raw * np.float32(sc_s), 0.0, 1.0).astype(np.float32)
        m_s = np.clip(m_raw * np.float32(min(max(sc_s, 0.85), 1.25)), p_s, 1.0).astype(np.float32)
        p_comb[sel] = p_s
        m_comb[sel] = m_s
        del p_raw, m_raw, p_s, m_s
    del p_fused, m_fused
    gc.collect()

    p_surface = adhr.scatter_fp(p_comb, ay, ax, grid.shape)
    m_surface = adhr.scatter_fp(m_comb, ay, ax, grid.shape)
    del p_comb, m_comb
    gc.collect()

    if preplacement_gate is not None:
        preplacement_gate(p_surface)

    allowed_near = np.zeros(grid.shape, dtype=bool)
    allowed_near[ay[near_sel], ax[near_sel]] = True
    allowed_far = np.zeros(grid.shape, dtype=bool)
    allowed_far[ay[far_sel], ax[far_sel]] = True
    k_near = k_prod * (float(near_budget) / float(near_budget + far_budget))
    k_far = k_prod * (float(far_budget) / float(near_budget + far_budget))
    alloc_near = emit.dinkelbach_allocate(
        p_surface, m_surface, allowed_near, budget=near_budget, k_truth=k_near,
        min_spacing_px=near_spacing_px, dinkelbach_iters=8)
    alloc_far = emit.dinkelbach_allocate(
        p_surface, m_surface, allowed_far, budget=far_budget, k_truth=k_far,
        min_spacing_px=far_spacing_px, dinkelbach_iters=8)
    emitted = np.clip(alloc_near.emitted.astype(np.float32) + alloc_far.emitted.astype(np.float32), 0.0, 1.0).astype(np.float32)
    dc = d_fullcat[emitted > 0.5]
    meta = {
        "n_dots": int((emitted > 0.5).sum()),
        "n_near_dots": int(alloc_near.n_dots),
        "n_far_dots": int(alloc_far.n_dots),
        "near_spacing_px": float(near_spacing_px),
        "far_spacing_px": float(far_spacing_px),
        "collar_min_d_cat_px": float(dc.min()) if dc.size else 0.0,
        "median_d_cat_px": float(np.median(dc)) if dc.size else 0.0,
        "share_le2": float((dc <= 2.0).mean()) if dc.size else 0.0,
        "share_gt10": float((dc > 10.0).mean()) if dc.size else 0.0,
        "share_gt25": float((dc > 25.0).mean()) if dc.size else 0.0,
        "k_truth_est": float(k_prod),
        "surrogate_dti_near": float(alloc_near.surrogate_dti),
        "surrogate_dti_far": float(alloc_far.surrogate_dti),
        "strictly_out_of_fold_both_heads": True,
    }
    return emitted, p_surface, meta
