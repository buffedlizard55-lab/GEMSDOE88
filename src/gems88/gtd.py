"""H88-GTD: potential-field gradient-tensor source dimensionality (14 zero-catalogue channels).

Physics
-------
A buried normal fault offsets magnetic/density basement along an elongated,
quasi-2-D step. In potential fields (GeoDAWN B02 ``rtp``, B13
``iso_grav_anom``, B15 ``depth_to_base_surf``) such a source produces a
gradient field whose local structure tensor

    J = G_sigma_i * (grad F)(grad F)^T        (2x2, symmetric PSD)

is strongly anisotropic: one dominant eigenvalue (gradient across strike)
and one near-zero eigenvalue (along strike). The closed-form linearity

    L = (lam1 - lam2) / (lam1 + lam2)  in [0, 1]

is ~1 for a line/step source and ~0 for equant 3-D bodies (pluton roofs,
volcanic centres), regardless of amplitude. Amplitude-only edge maps (and
USGS/INGENIOUS air-photo mapping, which needs a surface scarp) miss covered
faults whose *shape* is diagnostic even when their amplitude is modest.
GTD-14 measures L, the energetic step score S = L*|grad|, cross-field axial
strike agreement cos(2*dtheta), sigma5/sigma2 scale persistence (deep steps
persist; shallow texture and flight-line striping decay), an explicit
equant-source mimic channel (1-L)*E, and a cover-gated joint score
(subsurface step with weak B19 surface slope = buried, unmapped).

Strictly zero catalogue access in feature construction: ``existing_faults.tif``
and ``grid.catalogue`` are never read inside ``build_or_load_gtd_memmap``;
only ``grid.footprint`` is used. Inputs are label-blind cleaned via
``edge.clean_band`` with band-tag assertions.

Difference from prior lanes: SSA-88 measures multi-field orientation
*coherence* only; Frangi/Hessian-crest channels classify surface ridges;
H88-BPWD measures pseudogravity phase dislocation and worms. No prior module
computes structure-tensor eigenvalue dimensionality of the potential-field
sources themselves.

Fold/production predictors adapt ``src/gems88/bpwd.py`` verbatim in
structure (learner, fusion, allocator, collar, budgets) with GTD-14 appended
to both specialists, so the paired same-fold contrast vs the recomputed
H88-BPWD control isolates the GTD marginal contribution. Exp03/production
additionally apply the preregistered incumbent-proximity discount
``w = 0.55 + 0.45*clip(d_inc/3px, 0, 1)`` so the emission does not merely
reselect incumbent crests (IR-88-127 / IR-88-249E-02 failure mode).

Preregistration: ``registry/preregistration_gtd88.json`` (PREREG-20261025-GTD88).
Disclosed deviation: the preregistered mechanism prose mentions Hessians;
the emitted 14 channels use the structure-tensor eigensystem only (the
feature-name list, which is the binding specification, is unchanged).
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

from . import adhr, bpwd, edge, hgvc

GTD_SCHEMA_VERSION = "gtd88-14ch-v1"
CELL_M = 100.0
DISCOUNT_W_MIN = 0.55

GTD_FEATURES: tuple[str, ...] = (
    "gtd_rtp_lin_s2",
    "gtd_rtp_step_s2",
    "gtd_grav_lin_s2",
    "gtd_grav_step_s2",
    "gtd_zbase_lin_s2",
    "gtd_zbase_step_s2",
    "gtd_rtp_lin_s5",
    "gtd_grav_lin_s5",
    "gtd_agree_rtp_grav",
    "gtd_agree_grav_zbase",
    "gtd_joint_step",
    "gtd_persist_grav",
    "gtd_mimic_equant_energy",
    "gtd_cover_gated_joint",
)

_EPS = np.float32(1e-12)


# --------------------------------------------------------------- tensor core
def _smooth_fp(a: np.ndarray, fp: np.ndarray, sigma: float) -> np.ndarray:
    """Footprint-normalised Gaussian smoothing (same convention as edge.derivatives)."""
    w = fp.astype(np.float32)
    numer = ndi.gaussian_filter(np.asarray(a, np.float32) * w, sigma=sigma, mode="constant")
    denom = ndi.gaussian_filter(w, sigma=sigma, mode="constant")
    return (numer / np.maximum(denom, np.float32(1e-6))).astype(np.float32)


def structure_tensor(field: np.ndarray, fp: np.ndarray, sigma_d: float) -> dict[str, np.ndarray]:
    """Eigen-decomposition of the Gaussian structure tensor of ``field``.

    Returns linearity L in [0,1], energy E = sqrt(trace J), dominant axial
    gradient orientation theta (radians, mod pi). All float32, finite, and
    exactly 0 outside ``fp`` for L/E (theta is 0 outside fp by convention).
    Unit identities (tests/test_gtd88.py): a pure plane wave / straight step
    gives L ~ 1 along the edge; the centre of a radial bump gives L ~ 0.
    """
    gy, gx = edge.derivatives(field, fp, sigma=float(sigma_d))
    sigma_i = 2.0 * float(sigma_d)
    jxx = _smooth_fp(gx * gx, fp, sigma_i)
    jxy = _smooth_fp(gx * gy, fp, sigma_i)
    jyy = _smooth_fp(gy * gy, fp, sigma_i)
    del gy, gx
    trace = jxx + jyy
    half_diff = 0.5 * (jxx - jyy)
    disc = np.sqrt(np.maximum(half_diff * half_diff + jxy * jxy, 0.0)).astype(np.float32)
    lam1 = 0.5 * trace + disc
    lam2 = np.maximum(0.5 * trace - disc, 0.0)
    denom = lam1 + lam2 + _EPS
    lin = np.where(trace > np.float32(1e-9), (lam1 - lam2) / denom, 0.0).astype(np.float32)
    lin = np.clip(lin, 0.0, 1.0)
    energy = np.sqrt(np.maximum(trace, 0.0)).astype(np.float32)
    theta = (0.5 * np.arctan2(2.0 * jxy, jxx - jyy)).astype(np.float32)
    del jxx, jxy, jyy, trace, half_diff, disc, lam1, lam2, denom
    lin[~fp] = 0.0
    energy[~fp] = 0.0
    theta[~fp] = 0.0
    return {"lin": lin, "energy": energy, "theta": theta}


def _pct01(arr: np.ndarray, fp: np.ndarray, lo: float = 5.0, hi: float = 95.0) -> np.ndarray:
    v = arr[fp]
    p_lo, p_hi = (float(x) for x in np.percentile(v[::17], [lo, hi]))
    if p_hi <= p_lo:
        return np.zeros_like(arr, dtype=np.float32)
    out = np.clip((arr - np.float32(p_lo)) / np.float32(p_hi - p_lo), 0.0, 1.0).astype(np.float32)
    out[~fp] = 0.0
    return out


def build_gtd_channels(bands: dict[str, np.ndarray], fp: np.ndarray) -> list[np.ndarray]:
    """Build the 14 GTD channels (full-grid float32) from cleaned bands.

    ``bands`` must contain rtp / iso_grav_anom / depth_to_base_surf /
    det_elev_slope. Pure function of (bands, footprint): no catalogue, no
    labels, deterministic. Exposed for synthetic unit tests.
    """
    t_rtp2 = structure_tensor(bands["rtp"], fp, 2.0)
    t_grav2 = structure_tensor(bands["iso_grav_anom"], fp, 2.0)
    t_zbase2 = structure_tensor(bands["depth_to_base_surf"], fp, 2.0)
    t_rtp5 = structure_tensor(bands["rtp"], fp, 5.0)
    t_grav5 = structure_tensor(bands["iso_grav_anom"], fp, 5.0)

    def step(t: dict) -> np.ndarray:
        return bpwd._robust_pos(t["lin"] * t["energy"], fp)

    s_rtp, s_grav, s_zbase = step(t_rtp2), step(t_grav2), step(t_zbase2)
    s_grav5 = bpwd._robust_pos(t_grav5["lin"] * t_grav5["energy"], fp)

    def agree(ta: dict, tb: dict) -> np.ndarray:
        a = np.cos(2.0 * (ta["theta"] - tb["theta"])) * np.minimum(ta["lin"], tb["lin"])
        a = np.clip(a, -1.0, 1.0).astype(np.float32)
        a[~fp] = 0.0
        return a

    joint_raw = np.cbrt(np.maximum(s_rtp * s_grav * s_zbase, 0.0)).astype(np.float32)
    joint = bpwd._robust_pos(joint_raw, fp)
    persist = bpwd._robust_z(np.clip(s_grav5 / (s_grav + np.float32(0.05)), 0.0, 3.0), fp)
    e_grav_n = bpwd._robust_pos(t_grav2["energy"], fp)
    e_rtp_n = bpwd._robust_pos(t_rtp2["energy"], fp)
    mimic = bpwd._robust_pos(
        (1.0 - t_grav2["lin"]) * e_grav_n + (1.0 - t_rtp2["lin"]) * e_rtp_n, fp
    )
    slope_n = _pct01(bands["det_elev_slope"], fp)
    cover_gated = bpwd._robust_pos(joint * (1.0 - slope_n), fp)

    channels = [
        t_rtp2["lin"], s_rtp,
        t_grav2["lin"], s_grav,
        t_zbase2["lin"], s_zbase,
        t_rtp5["lin"], t_grav5["lin"],
        agree(t_rtp2, t_grav2), agree(t_grav2, t_zbase2),
        joint, persist, mimic, cover_gated,
    ]
    if len(channels) != len(GTD_FEATURES):
        raise AssertionError(f"Expected {len(GTD_FEATURES)} GTD channels, built {len(channels)}")
    out = []
    for name, ch in zip(GTD_FEATURES, channels):
        ch = np.nan_to_num(ch, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        ch[~fp] = 0.0
        if not np.isfinite(ch).all():
            raise AssertionError(f"Non-finite GTD channel {name}")
        out.append(ch)
    return out


# --------------------------------------------------------------- memmap IO
def build_or_load_gtd_memmap(root: Path, grid, cache_dir: Path) -> tuple[np.memmap, dict]:
    """Build or load the 14-channel label-blind GTD float32 disk memmap."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = np.asarray(grid.footprint, dtype=bool)
    ys_fp, xs_fp = np.nonzero(fp)
    n_fp = int(ys_fp.size)
    n_cols = len(GTD_FEATURES)
    dat_path = cache_dir / "x_gtd_14ch_v1.dat"
    meta_path = cache_dir / "x_gtd_14ch_v1.json"
    tf_path = Path(root) / "data/training_features.tif"
    hashes = {"training_features.tif": f"size_{tf_path.stat().st_size}"}

    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("schema") == GTD_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(GTD_FEATURES)
            and meta.get("hashes") == hashes
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    expected_tags = {2: "rtp", 13: "iso_grav_anom", 15: "depth_to_base_surf", 19: "det_elev_slope"}
    bands: dict[str, np.ndarray] = {}
    with rasterio.open(tf_path) as src:
        for b_idx, tag_want in expected_tags.items():
            tag_got = src.tags(b_idx).get("band_name")
            if tag_got != tag_want:
                raise ValueError(f"Band {b_idx} tag mismatch: expected {tag_want!r}, got {tag_got!r}")
            cleaned, _ = edge.clean_band(src.read(b_idx), fp)
            bands[tag_want] = cleaned

    raw_channels = build_gtd_channels(bands, fp)
    del bands
    gc.collect()

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))
    col_stats = {}
    for j, (fname, ch) in enumerate(zip(GTD_FEATURES, raw_channels)):
        vec = ch[ys_fp, xs_fp].astype(np.float32)
        mm[:, j] = vec
        col_stats[fname] = {
            "mean": round(float(vec.mean(dtype=np.float64)), 6),
            "std": round(float(vec.std(dtype=np.float64)), 6),
            "min": round(float(vec.min()), 6),
            "max": round(float(vec.max()), 6),
        }
    mm.flush()
    del mm, raw_channels
    gc.collect()
    meta = {
        "schema": GTD_SCHEMA_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(GTD_FEATURES),
        "hashes": hashes,
        "zero_catalogue_reads": True,
        "sigmas_px": [2.0, 5.0],
        "column_stats": col_stats,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta


# --------------------------------------------------------------- discount
def proximity_discount(dots_bool: np.ndarray, w_min: float = DISCOUNT_W_MIN) -> np.ndarray:
    """Full-grid weight w = w_min + (1-w_min)*clip(d/3px, 0, 1) vs incumbent dots."""
    d = ndi.distance_transform_edt(~np.asarray(dots_bool, dtype=bool)).astype(np.float32)
    return (np.float32(w_min) + np.float32(1.0 - w_min) * np.clip(d / np.float32(3.0), 0.0, 1.0)).astype(np.float32)


# --------------------------------------------------------------- fold suite
def predict_gtd_suite_fold(
    grid,
    X_phys_mm: np.ndarray,
    X_phys_diff,
    X_hgvc_mm: np.ndarray,
    X_psgv_mm: np.ndarray,
    X_gtd_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    seed: int,
    psgv_cache_dir: Path,
    gtd_cache_dir: Path,
    fold_tag: str,
) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    """Per-fold posteriors + allocations: 4 controls (incl. recomputed BPWD) + 3 GTD experiments.

    Control/PSGV posterior computation, seeds, fusion and allocator mirror
    ``bpwd.predict_psgv_suite_fold`` exactly (same cache filenames in
    ``psgv_cache_dir``), so ``h88_bpwd_incumbent`` reproduces the H88-BPWD
    Exp03 recipe on identical folds. GTD specialists append GTD-14.
    """
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    d_vis_act = d_vis_fp[act_idx]

    hgvc_post_path = Path(psgv_cache_dir) / f"hgvc_fold_post_{fold_tag}_{hgvc.HGVC_SCHEMA_VERSION}.npz"
    psgv_post_path = Path(psgv_cache_dir) / f"psgv_fold_post_{fold_tag}_{bpwd.PSGV_SCHEMA_VERSION}.npz"
    gtd_post_path = Path(gtd_cache_dir) / f"gtd_fold_post_{fold_tag}_{GTD_SCHEMA_VERSION}.npz"

    pop_tr_fp = train_truth[ys_fp, xs_fp]
    wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, pop_tr_fp, quantile=0.90, l0_px=40.0)
    d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
    dom_phys_tr = train_regions[ys_fp, xs_fp]
    dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]

    if hgvc_post_path.is_file():
        zh = np.load(hgvc_post_path, allow_pickle=False)
        p_phys_44, m_phys_44 = zh["p_phys_44"], zh["m_phys_44"]
        p_full_67, m_full_67 = zh["p_full_67"], zh["m_full_67"]
        p_hgvc_phys, m_hgvc_phys = zh["p_hgvc_phys"], zh["m_hgvc_phys"]
        p_hgvc_full, m_hgvc_full = zh["p_hgvc_full"], zh["m_hgvc_full"]
    else:
        c_p44, r_p44 = adhr._fit_dual_expectation_models(
            [X_phys_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 17, n_ensemble=1)
        p_phys_44, m_phys_44 = adhr._predict_dual_chunked(c_p44, r_p44, [X_phys_mm], act_idx)
        del c_p44, r_p44; gc.collect()
        c_f67, r_f67 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 53, n_ensemble=1)
        p_full_67, m_full_67 = adhr._predict_dual_chunked(c_f67, r_f67, [X_phys_mm, X_vis22_mm, d_over_w_fp], act_idx)
        del c_f67, r_f67; gc.collect()
        c_hp, r_hp = adhr._fit_dual_expectation_models(
            [X_phys_diff, X_hgvc_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 117, n_ensemble=2)
        p_hgvc_phys, m_hgvc_phys = adhr._predict_dual_chunked(c_hp, r_hp, [X_phys_diff, X_hgvc_mm], act_idx)
        del c_hp, r_hp; gc.collect()
        c_hf, r_hf = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 153, n_ensemble=2)
        p_hgvc_full, m_hgvc_full = adhr._predict_dual_chunked(c_hf, r_hf, [X_phys_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp], act_idx)
        del c_hf, r_hf; gc.collect()
        np.savez_compressed(hgvc_post_path, p_phys_44=p_phys_44, m_phys_44=m_phys_44,
                            p_full_67=p_full_67, m_full_67=m_full_67, p_hgvc_phys=p_hgvc_phys,
                            m_hgvc_phys=m_hgvc_phys, p_hgvc_full=p_hgvc_full, m_hgvc_full=m_hgvc_full)

    if psgv_post_path.is_file():
        zp = np.load(psgv_post_path, allow_pickle=False)
        p_psgv_phys, m_psgv_phys = zp["p_psgv_phys"], zp["m_psgv_phys"]
        p_psgv_full, m_psgv_full = zp["p_psgv_full"], zp["m_psgv_full"]
    else:
        cp_lgb, rp_lgb = bpwd._fit_lgbm_dual_models(
            [X_phys_diff, X_psgv_mm, X_hgvc_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 217, n_ensemble=2)
        p_psgv_phys, m_psgv_phys = adhr._predict_dual_chunked(cp_lgb, rp_lgb, [X_phys_diff, X_psgv_mm, X_hgvc_mm], act_idx)
        del cp_lgb, rp_lgb; gc.collect()
        cf_lgb, rf_lgb = bpwd._fit_lgbm_dual_models(
            [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 253, n_ensemble=2)
        p_psgv_full, m_psgv_full = adhr._predict_dual_chunked(cf_lgb, rf_lgb, [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_vis22_mm, d_over_w_fp], act_idx)
        del cf_lgb, rf_lgb; gc.collect()
        np.savez_compressed(psgv_post_path, p_psgv_phys=p_psgv_phys, m_psgv_phys=m_psgv_phys,
                            p_psgv_full=p_psgv_full, m_psgv_full=m_psgv_full)

    if gtd_post_path.is_file():
        zg = np.load(gtd_post_path, allow_pickle=False)
        p_gtd_phys, m_gtd_phys = zg["p_gtd_phys"], zg["m_gtd_phys"]
        p_gtd_full, m_gtd_full = zg["p_gtd_full"], zg["m_gtd_full"]
    else:
        cg_p, rg_p = bpwd._fit_lgbm_dual_models(
            [X_phys_diff, X_psgv_mm, X_hgvc_mm, X_gtd_mm], dom_phys_tr, visible & train_regions, fp, seed=seed + 317, n_ensemble=2)
        p_gtd_phys, m_gtd_phys = adhr._predict_dual_chunked(cg_p, rg_p, [X_phys_diff, X_psgv_mm, X_hgvc_mm, X_gtd_mm], act_idx)
        del cg_p, rg_p; gc.collect()
        cg_f, rg_f = bpwd._fit_lgbm_dual_models(
            [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_gtd_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, train_truth, fp, seed=seed + 353, n_ensemble=2)
        p_gtd_full, m_gtd_full = adhr._predict_dual_chunked(cg_f, rg_f, [X_phys_mm, X_psgv_mm, X_hgvc_mm, X_gtd_mm, X_vis22_mm, d_over_w_fp], act_idx)
        del cg_f, rg_f; gc.collect()
        np.savez_compressed(gtd_post_path, p_gtd_phys=p_gtd_phys, m_gtd_phys=m_gtd_phys,
                            p_gtd_full=p_gtd_full, m_gtd_full=m_gtd_full)
    del d_over_w_fp

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float(train_truth.sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]

    def _emit_arm(p_vec, m_vec, spacing: float = 2.05, discount_vec=None):
        pv = np.asarray(p_vec, np.float32)
        mv = np.asarray(m_vec, np.float32)
        if discount_vec is not None:
            pv = (pv * discount_vec).astype(np.float32)
            mv = np.clip(mv * discount_vec, pv, 1.0).astype(np.float32)
        pg = adhr.scatter_fp(pv, ay, ax, grid.shape)
        mg = adhr.scatter_fp(mv, ay, ax, grid.shape)
        alloc = emit.dinkelbach_allocate(pg, mg, allowed, budget=None, k_truth=k_est,
                                         min_spacing_px=spacing, dinkelbach_iters=6)
        return (alloc.emitted.astype(np.float32), pg,
                {"n_dots": int(alloc.n_dots), "k_truth_est": float(k_est),
                 "surrogate_dti": float(alloc.surrogate_dti)})

    sc_c1 = float(k_est) / max(float(p_phys_44.sum()), 1e-6)
    p_c1 = np.clip(p_phys_44 * np.float32(sc_c1), 0.0, 1.0).astype(np.float32)
    m_c1 = np.clip(m_phys_44 * np.float32(hid_ratio), p_c1, 1.0).astype(np.float32)

    p_adhr_inc, m_adhr_inc = adhr._fuse_log_odds(p_full_67, m_full_67, p_phys_44, m_phys_44, k_est, beta_phys=0.35)

    p_hg_poe_p, m_hg_poe_p = hgvc.poe_pool_hgvc(p_phys_44, m_phys_44, p_hgvc_phys, m_hgvc_phys, d_vis_act)
    p_hg_poe_f, m_hg_poe_f = hgvc.poe_pool_hgvc(p_full_67, m_full_67, p_hgvc_full, m_hgvc_full, d_vis_act)
    p_hgvc_inc, m_hgvc_inc = adhr._fuse_log_odds(p_hg_poe_f, m_hg_poe_f, p_hg_poe_p, m_hg_poe_p, k_est, beta_phys=0.38)

    p_b_tri_p, m_b_tri_p = bpwd.tri_specialist_poe_pool(p_phys_44, m_phys_44, p_hgvc_phys, m_hgvc_phys, p_psgv_phys, m_psgv_phys, d_vis_act)
    p_b_tri_f, m_b_tri_f = bpwd.tri_specialist_poe_pool(p_full_67, m_full_67, p_hgvc_full, m_hgvc_full, p_psgv_full, m_psgv_full, d_vis_act)
    p_bpwd_inc, m_bpwd_inc = adhr._fuse_log_odds(p_b_tri_f, m_b_tri_f, p_b_tri_p, m_b_tri_p, k_est, beta_phys=0.38)

    sc_e1 = float(k_est) / max(float(p_gtd_phys.sum()), 1e-6)
    p_e1 = np.clip(p_gtd_phys * np.float32(sc_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_gtd_phys * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)

    p_g_tri_p, m_g_tri_p = bpwd.tri_specialist_poe_pool(p_phys_44, m_phys_44, p_hgvc_phys, m_hgvc_phys, p_gtd_phys, m_gtd_phys, d_vis_act)
    p_g_tri_f, m_g_tri_f = bpwd.tri_specialist_poe_pool(p_full_67, m_full_67, p_hgvc_full, m_hgvc_full, p_gtd_full, m_gtd_full, d_vis_act)
    p_e2, m_e2 = adhr._fuse_log_odds(p_g_tri_f, m_g_tri_f, p_g_tri_p, m_g_tri_p, k_est, beta_phys=0.38)

    arms: dict[str, tuple[np.ndarray, np.ndarray, dict]] = {
        "phys44_zero_cat": _emit_arm(p_c1, m_c1),
        "h88_adhr_incumbent": _emit_arm(p_adhr_inc, m_adhr_inc),
        "h88_hgvc_incumbent": _emit_arm(p_hgvc_inc, m_hgvc_inc),
        "h88_bpwd_incumbent": _emit_arm(p_bpwd_inc, m_bpwd_inc),
        "exp01_gtd_zero_cat": _emit_arm(p_e1, m_e1),
        "exp02_gtd_tri_poe": _emit_arm(p_e2, m_e2),
    }
    # Exp03: production procedure — Exp02 posteriors discounted vs this fold's
    # BPWD-control dots (fold-fair analogue of the production discount).
    w_grid = proximity_discount(arms["h88_bpwd_incumbent"][0] > 0.5)
    w_vec = w_grid[ay, ax]
    del w_grid
    arms["exp03_gtd_tri_poe_novel"] = _emit_arm(p_e2, m_e2, discount_vec=w_vec)
    del w_vec
    return arms


# --------------------------------------------------------------- production
def fit_and_emit_production_gtd(
    grid,
    X_phys_mm: np.ndarray,
    X_phys_diff,
    X_hgvc_mm: np.ndarray,
    X_psgv_mm: np.ndarray,
    X_gtd_mm: np.ndarray,
    folds_by_seed: list[tuple[int, list[dict]]],
    sense_src: np.ndarray,
    scarp_fields: dict[str, np.ndarray],
    vis_by_seed: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]],
    psgv_cache_dir: Path,
    gtd_cache_dir: Path,
    incumbent_dots: np.ndarray,
    *,
    near_budget: int = 21_200,
    far_budget: int = 16_454,
    near_spacing_px: float = 2.90,
    far_spacing_px: float = 3.12,
    preplacement_gate=None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """4-quadrant / 8-fold OOF cross-fitting + stratified Dinkelbach allocation.

    Mirrors ``bpwd.fit_and_emit_production_psgv`` (fusion weights, budgets,
    spacings, >2.5 px collar) with GTD-14 appended to both OOF specialists,
    GTD joint-step modulation, and the preregistered incumbent-proximity
    discount vs ``incumbent_dots`` applied to the fused surface before the
    pre-placement gate and allocation.
    """
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    d_fullcat = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    d_full_fp = d_fullcat[ys_fp, xs_fp]
    act_idx = np.flatnonzero(d_full_fp > 2.5)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]
    d_act = d_full_fp[act_idx]

    oof_cache = Path(gtd_cache_dir) / f"gtd_prod_oof_{GTD_SCHEMA_VERSION}.npz"
    if oof_cache.is_file():
        z = np.load(oof_cache, allow_pickle=False)
        p_spec_oof, m_spec_oof = z["p_spec_oof"], z["m_spec_oof"]
        p_full_oof, m_full_oof = z["p_full_oof"], z["m_full_oof"]
    else:
        spec_oof_cache = Path(gtd_cache_dir) / f"gtd_prod_spec_oof_{GTD_SCHEMA_VERSION}.npz"
        if spec_oof_cache.is_file():
            zs = np.load(spec_oof_cache, allow_pickle=False)
            p_spec_oof, m_spec_oof = zs["p_spec_oof"], zs["m_spec_oof"]
        else:
            folds_q4 = folds_by_seed[0][1]
            p_spec_oof = np.zeros(act_idx.size, dtype=np.float32)
            m_spec_oof = np.zeros(act_idx.size, dtype=np.float32)
            covered_p = np.zeros(act_idx.size, dtype=bool)
            for q_idx, f_q in enumerate(folds_q4):
                tr_dom_q = (~f_q["region"])[ys_fp, xs_fp]
                c_q, r_q = bpwd._fit_lgbm_dual_models(
                    [X_psgv_mm, X_gtd_mm, X_phys_diff], tr_dom_q, full_cat & (~f_q["region"]),
                    fp, seed=88910 + q_idx, n_ensemble=2)
                mask_q = f_q["region"][ay, ax]
                if q_idx == len(folds_q4) - 1:
                    mask_q = mask_q | (~covered_p)
                covered_p |= mask_q
                pq, mq = adhr._predict_dual_chunked(c_q, r_q, [X_psgv_mm, X_gtd_mm, X_phys_diff], act_idx[mask_q])
                p_spec_oof[mask_q] = pq
                m_spec_oof[mask_q] = mq
                del c_q, r_q, pq, mq; gc.collect()
            np.savez_compressed(spec_oof_cache, p_spec_oof=p_spec_oof, m_spec_oof=m_spec_oof)

        X_vis_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(
            grid, full_cat, sense_src, scarp_fields, Path(psgv_cache_dir), "prod_fullcat")
        p_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        m_full_acc = np.zeros(act_idx.size, dtype=np.float64)
        for seed, folds in folds_by_seed:
            seed_oof_cache = Path(gtd_cache_dir) / f"gtd_prod_struct_s{seed}_{GTD_SCHEMA_VERSION}.npz"
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
                    wlaw_q = damagezone_envelope.fit_width_law(cl_s, dv_s, tr_tru_q[ys_fp, xs_fp], quantile=0.90, l0_px=40.0)
                    dow_s_q = (dv_s / np.maximum(wlaw_q.half_width(cl_s), 1e-6)).astype(np.float32)
                    dom_s_q = (tr_reg_q & ~vis_s)[ys_fp, xs_fp]
                    cs_q, rs_q = bpwd._fit_lgbm_dual_models(
                        [X_phys_mm, X_psgv_mm, X_gtd_mm, X_hgvc_mm, X_vis_s, dow_s_q],
                        dom_s_q, tr_tru_q, fp, seed=89100 + 10 * seed + q_idx, n_ensemble=1)
                    mask_q = f_q["region"][ay, ax]
                    if q_idx == len(folds) - 1:
                        mask_q = mask_q | (~covered_s)
                    covered_s |= mask_q
                    dow_prod_q = (dv_prod / np.maximum(wlaw_q.half_width(cl_prod), 1e-6)).astype(np.float32)
                    pq, mq = adhr._predict_dual_chunked(
                        cs_q, rs_q, [X_phys_mm, X_psgv_mm, X_gtd_mm, X_hgvc_mm, X_vis_prod, dow_prod_q], act_idx[mask_q])
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
        np.savez_compressed(oof_cache, p_spec_oof=p_spec_oof, m_spec_oof=m_spec_oof,
                            p_full_oof=p_full_oof, m_full_oof=m_full_oof)

    # GTD joint-step modulation (analogue of BPWD conduit modulation):
    # cols 10 = gtd_joint_step, 13 = gtd_cover_gated_joint (robust-pos scaled).
    gtd_mod_act = (
        0.50 * np.asarray(X_gtd_mm[act_idx, 10], dtype=np.float32)
        + 0.50 * np.asarray(X_gtd_mm[act_idx, 13], dtype=np.float32)
    )
    conduit_mult = (0.75 + 0.35 * np.tanh(0.45 * gtd_mod_act)).astype(np.float32)
    p_spec_mod = np.clip(p_spec_oof * conduit_mult, 1e-6, 1.0 - 1e-6).astype(np.float32)
    m_spec_mod = np.clip(m_spec_oof * conduit_mult, p_spec_mod, 1.0).astype(np.float32)
    del gtd_mod_act, conduit_mult

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(p_full_oof, m_full_oof, p_spec_mod, m_spec_mod, k_prod, beta_phys=0.58, pi_unmapped=0.65)

    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0
    k_near = k_prod * (float(near_budget) / float(near_budget + far_budget))
    k_far = k_prod * (float(far_budget) / float(near_budget + far_budget))

    p_near_raw = 0.42 * p_fused[near_sel] + 0.58 * p_spec_mod[near_sel]
    m_near_raw = 0.42 * m_fused[near_sel] + 0.58 * m_spec_mod[near_sel]
    sc_near = float(k_near) / max(float(p_near_raw.sum()), 1e-6)
    p_near = np.clip(p_near_raw * np.float32(sc_near), 0.0, 1.0).astype(np.float32)
    m_near = np.clip(m_near_raw * np.float32(min(max(sc_near, 0.85), 1.20)), p_near, 1.0).astype(np.float32)

    p_far_raw = 0.28 * p_fused[far_sel] + 0.72 * p_spec_mod[far_sel]
    m_far_raw = 0.28 * m_fused[far_sel] + 0.72 * m_spec_mod[far_sel]
    sc_far = float(k_far) / max(float(p_far_raw.sum()), 1e-6)
    p_far = np.clip(p_far_raw * np.float32(sc_far), 0.0, 1.0).astype(np.float32)
    m_far = np.clip(m_far_raw * np.float32(min(max(sc_far, 0.85), 1.25)), p_far, 1.0).astype(np.float32)

    p_comb = np.empty_like(p_fused)
    m_comb = np.empty_like(m_fused)
    p_comb[near_sel] = p_near; m_comb[near_sel] = m_near
    p_comb[far_sel] = p_far; m_comb[far_sel] = m_far
    del p_fused, m_fused, p_spec_mod, m_spec_mod, p_near_raw, m_near_raw, p_far_raw, m_far_raw, p_near, m_near, p_far, m_far

    # Preregistered incumbent-proximity novelty discount (BPWD+HGVC+H33 dots).
    w_grid = proximity_discount(incumbent_dots)
    w_act = w_grid[ay, ax]
    del w_grid
    p_comb = (p_comb * w_act).astype(np.float32)
    m_comb = np.clip(m_comb * w_act, p_comb, 1.0).astype(np.float32)
    frac_discounted = float((w_act < 0.999).mean())
    del w_act

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
    emitted = np.clip(alloc_near.emitted.astype(np.float32) + alloc_far.emitted.astype(np.float32), 0.0, 1.0).astype(np.float32)
    dc_dots = d_fullcat[emitted > 0.5]
    n_dots = int((emitted > 0.5).sum())
    meta = {
        "n_dots": n_dots,
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
        "incumbent_discount_w_min": DISCOUNT_W_MIN,
        "incumbent_discount_frac_cells_affected": frac_discounted,
        "incumbent_dots_n": int(np.asarray(incumbent_dots, dtype=bool).sum()),
    }
    return emitted, p_surface, meta


# --------------------------------------------------------------- scramble check
def verify_zero_test_quadrant_leakage(
    grid, X_phys_mm, X_psgv_mm, X_gtd_mm, X_hgvc_mm, X_vis22_mm,
    d_vis_fp, comp_len_fp, fold, train_regions, train_truth, seed: int = 89601,
) -> bool:
    """Bit-identical test-quadrant predictions when held-out truth is scrambled."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    visible = fold["visible"]
    test_region = fold["region"]
    rng = np.random.default_rng(20261025)
    truth_orig = train_truth.copy()
    truth_scram = train_truth.copy()
    truth_scram[test_region] = rng.random(int(test_region.sum())) < 0.20
    sub_idx = np.flatnonzero((fp & test_region & ~visible)[ys_fp, xs_fp])[:4096]
    preds = []
    for t_cand in (truth_orig & train_regions, truth_scram & train_regions):
        wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, t_cand[ys_fp, xs_fp], quantile=0.90, l0_px=40.0)
        dow = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
        clfs, regs = bpwd._fit_lgbm_dual_models(
            [X_phys_mm, X_psgv_mm, X_gtd_mm, X_hgvc_mm, X_vis22_mm, dow],
            (train_regions & ~visible)[ys_fp, xs_fp], t_cand, fp,
            seed=seed, max_zero_neg=15_000, n_ensemble=1)
        preds.append(adhr._predict_dual_chunked(clfs, regs, [X_phys_mm, X_psgv_mm, X_gtd_mm, X_hgvc_mm, X_vis22_mm, dow], sub_idx))
        del clfs, regs, dow; gc.collect()
    return bool(np.array_equal(preds[0][0], preds[1][0]) and np.array_equal(preds[0][1], preds[1][1]))
