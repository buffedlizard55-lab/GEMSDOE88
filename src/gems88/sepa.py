"""H88-SEPA: Seismic-Strain Partitioning & Potential-Field Persistence Anisotropy.

18 strictly zero-catalogue channels (``existing_faults.tif`` is never read):

* Seismic fabric of the organizer azimuth-sector earthquake fields
  (B16 ``ieq_n100a15``, B10 ``deq_n100a15``): structure-tensor anisotropy at
  integration scales 3 and 8 px, Frangi bright ridge of ``log ieq``, Frangi
  ridge of ``-log deq`` (proximity trough), local seismicity excess over a
  25-px regional mean, and an explicit Hessian-blobness mimic channel
  (isotropic volcanic swarms).
* Geodetic strain partitioning (B4 ``geod_2ndinv``, B7 ``geod_shearrate``,
  B8 ``geod_dilaterate``): shear and positive-dilatation fractions,
  strain-localisation gradient, strain-field tensor anisotropy, and spin-2
  orientation agreement / conjunction with the seismic fabric.
* Deep-vs-shallow potential-field persistence: ``|grad TMI_up150| / |grad tmi|``
  (B14), Frangi ridge of ``|grad TMI_up150|``, ``|grad_6 grav| / |grad_2 grav|``
  (B13), TMI scale-decay ``log(|grad_8| / |grad_2|)``, spin-2 agreement of the
  upward-continued magnetic fabric with the seismic fabric, and a
  strain-gradient x persistence conjunction.

Prior lanes used B10/B16 and B7/B8 only as scalars (`seismic_prox`,
`geod_transtension` in ``physics.py``) and `TMI_up150` only through its own
Laplacian/admittance; the tensor, partition and persistence-ratio transforms
above are new in this repo (preregistered in
``registry/preregistration_sepa88.json``).

Memory: full-grid float32 planes (~49 MB each) are freed field by field;
output is a disk-backed ``(N_fp, 18)`` float32 memmap.
"""
from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from . import edge
from .vess import _hessian, vesselness

SEPA_FEATURES: tuple[str, ...] = (
    "sepa_seis_aniso_s3",
    "sepa_seis_aniso_s8",
    "sepa_seis_ridge_s2",
    "sepa_seis_trough_s2",
    "sepa_seis_local_excess",
    "sepa_seis_blob_mimic",
    "sepa_strain_shear_frac",
    "sepa_strain_dilat_frac",
    "sepa_strain_grad_s3",
    "sepa_strain_aniso_s5",
    "sepa_seis_strain_orient",
    "sepa_seis_x_straingrad",
    "sepa_mag_persist_ratio",
    "sepa_mag_up150_ridge",
    "sepa_grav_persist_ratio",
    "sepa_persist_orient",
    "sepa_mag_scale_decay",
    "sepa_strain_x_persist",
)

SEPA_SCHEMA_VERSION = "sepa88-18ch-v1"
# band index -> expected organizer tag (verified at build; IR-88-110 guard)
_BANDS = (
    (16, "ieq_n100a15"),
    (10, "deq_n100a15"),
    (4, "geod_2ndinv"),
    (7, "geod_shearrate"),
    (8, "geod_dilaterate"),
    (14, "tmi"),
    (13, "iso_grav_anom"),
)


def _grad(a: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gy = ndi.gaussian_filter(a, sigma=sigma, order=(1, 0), mode="nearest").astype(np.float32)
    gx = ndi.gaussian_filter(a, sigma=sigma, order=(0, 1), mode="nearest").astype(np.float32)
    return gy, gx, np.hypot(gy, gx).astype(np.float32)


def _structure_tensor(a: np.ndarray, sigma_deriv: float, sigma_int: float):
    """Return (anisotropy in [0,1], cos2strike, sin2strike) of field ``a``.

    Double-angle convention identical to ``hgvc._structure_tensor_2theta``:
    gradient direction is normal to strike, so ``u = Jyy - Jxx``,
    ``v = -2 Jxy`` point along ``(cos 2*strike, sin 2*strike)``.
    """
    gy, gx, _ = _grad(a, sigma_deriv)
    jxx = ndi.gaussian_filter(gx * gx, sigma=sigma_int, mode="nearest").astype(np.float32)
    jyy = ndi.gaussian_filter(gy * gy, sigma=sigma_int, mode="nearest").astype(np.float32)
    jxy = ndi.gaussian_filter(gx * gy, sigma=sigma_int, mode="nearest").astype(np.float32)
    del gy, gx
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy**2, 0.0)).astype(np.float32)
    trace = jxx + jyy
    aniso = np.clip(disc / (trace + np.float32(1e-12)), 0.0, 1.0).astype(np.float32)
    u = jyy - jxx
    v = -2.0 * jxy
    norm = np.hypot(u, v) + np.float32(1e-12)
    return aniso, (u / norm).astype(np.float32), (v / norm).astype(np.float32)


def _orient_agree(a1, u1, v1, a2, u2, v2) -> np.ndarray:
    """Spin-2 fabric agreement: cos(2*dstrike) weighted by the weaker anisotropy."""
    dot = np.clip(u1 * u2 + v1 * v2, -1.0, 1.0)
    return (dot * np.minimum(a1, a2)).astype(np.float32)


def _blobness(a: np.ndarray, footprint: np.ndarray, sigma: float) -> np.ndarray:
    """Hessian blobness Rb * structureness gate (volcanic-swarm mimic)."""
    hxx, hyy, hxy = _hessian(np.asarray(a, np.float32), sigma)
    tr = hxx + hyy
    disc = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy**2, 0.0))
    la = 0.5 * (tr - disc)
    lb = 0.5 * (tr + disc)
    swap = np.abs(la) > np.abs(lb)
    lam1 = np.where(swap, lb, la)
    lam2 = np.where(swap, la, lb)
    del hxx, hyy, hxy, tr, disc, la, lb, swap
    s_val = np.sqrt(lam1**2 + lam2**2)
    sample = s_val[footprint][::37]
    c = max(float(np.percentile(sample, 90.0)) if sample.size else 0.0, 1e-12)
    rb = np.abs(lam1) / (np.abs(lam2) + np.float32(1e-12))
    blob = rb * (1.0 - np.exp(-(s_val**2) / np.float32(2.0 * c * c)))
    return np.clip(blob, 0.0, 1.0).astype(np.float32)


def build_or_load_sepa_memmap(root: Path, grid, cache_dir: Path):
    """Build or reload the disk-backed (N_fp, 18) float32 SEPA memmap."""
    fp = grid.footprint
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    n_cols = len(SEPA_FEATURES)
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / "x_sepa_18ch_v1.dat"
    meta_path = cache_dir / "x_sepa_18ch_v1.json"
    feat_path = root / "data/training_features.tif"
    ext_path = root / "data/external/geodawn_extensions_u8.tif"
    hashes = {
        "training_features": hashlib.sha256(feat_path.read_bytes()).hexdigest(),
        "geodawn_extensions_u8": hashlib.sha256(ext_path.read_bytes()).hexdigest(),
    }
    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("schema") == SEPA_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(SEPA_FEATURES)
            and meta.get("hashes") == hashes
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    fields: dict[str, np.ndarray] = {}
    with rasterio.open(feat_path) as src:
        if (src.height, src.width) != grid.shape or src.crs != grid.crs or src.transform != grid.transform:
            raise ValueError("training_features.tif grid mismatch")
        for idx, want in _BANDS:
            got = src.tags(idx).get("band_name", "")
            if got != want:
                raise ValueError(f"band {idx}: expected {want!r}, got {got!r}")
            clean, _ = edge.clean_band(src.read(idx), fp)
            fields[want] = clean.astype(np.float32)

    with rasterio.open(ext_path) as ds:
        if (ds.height, ds.width) != grid.shape:
            raise ValueError("geodawn_extensions_u8.tif grid mismatch")
        if ds.descriptions[3] != "TMI_up150":
            raise ValueError(f"extensions band 4: expected 'TMI_up150', got {ds.descriptions[3]!r}")
        up150 = ds.read(4).astype(np.float32)
    up150[~fp] = np.float32(np.median(up150[fp]))

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    def write(col: int, name: str, plane: np.ndarray) -> None:
        if SEPA_FEATURES[col] != name:
            raise AssertionError(f"column mismatch at {col}: {name} != {SEPA_FEATURES[col]}")
        v = np.nan_to_num(np.asarray(plane, dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        mm[:, col] = v[ys, xs]

    # ---- seismic fabric (B16 density, B10 distance)
    log_ieq = np.log1p(np.maximum(fields["ieq_n100a15"], 0.0)).astype(np.float32)
    log_deq = np.log1p(np.maximum(fields["deq_n100a15"], 0.0)).astype(np.float32)
    del fields["ieq_n100a15"], fields["deq_n100a15"]

    seis_aniso3, seis_u3, seis_v3 = _structure_tensor(log_ieq, 1.5, 3.0)
    write(0, "sepa_seis_aniso_s3", seis_aniso3)
    seis_aniso8, _, _ = _structure_tensor(log_ieq, 2.0, 8.0)
    write(1, "sepa_seis_aniso_s8", seis_aniso8)
    del seis_aniso8
    write(2, "sepa_seis_ridge_s2", vesselness(log_ieq, fp, 2.0))
    write(3, "sepa_seis_trough_s2", vesselness(-log_deq, fp, 2.0))
    del log_deq
    regional = ndi.gaussian_filter(log_ieq, sigma=25.0, mode="nearest").astype(np.float32)
    write(4, "sepa_seis_local_excess", log_ieq - regional)
    del regional
    write(5, "sepa_seis_blob_mimic", _blobness(log_ieq, fp, 3.0))
    del log_ieq
    gc.collect()

    # ---- geodetic strain partitioning (B4, B7, B8)
    inv2 = fields.pop("geod_2ndinv")
    shear = np.abs(fields.pop("geod_shearrate"))
    dilat = fields.pop("geod_dilaterate")
    write(6, "sepa_strain_shear_frac", shear / (shear + np.abs(dilat) + np.float32(1.0)))
    write(7, "sepa_strain_dilat_frac", np.maximum(dilat, 0.0) / (np.abs(inv2) + np.float32(1.0)))
    del shear, dilat
    _, _, strain_grad = _grad(inv2, 3.0)
    strain_grad_log = np.log1p(strain_grad).astype(np.float32)
    write(8, "sepa_strain_grad_s3", strain_grad_log)
    del strain_grad
    strain_aniso, strain_u, strain_v = _structure_tensor(inv2, 2.0, 5.0)
    del inv2
    write(9, "sepa_strain_aniso_s5", strain_aniso)
    write(10, "sepa_seis_strain_orient", _orient_agree(seis_aniso3, seis_u3, seis_v3, strain_aniso, strain_u, strain_v))
    del strain_aniso, strain_u, strain_v
    write(11, "sepa_seis_x_straingrad", seis_aniso3 * strain_grad_log)
    gc.collect()

    # ---- deep-vs-shallow potential-field persistence (up150 vs B14 tmi; B13 grav)
    tmi = fields.pop("tmi")
    _, _, tmi_g2 = _grad(tmi, 2.0)
    _, _, tmi_g8 = _grad(tmi, 8.0)
    del tmi
    _, _, up_g2 = _grad(up150, 2.0)
    # unit-free persistence: each gradient field normalised by its own footprint median
    up_norm = up_g2 / np.float32(max(float(np.median(up_g2[fp])), 1e-12))
    tmi_norm = tmi_g2 / np.float32(max(float(np.median(tmi_g2[fp])), 1e-12))
    persist = np.clip(up_norm / (tmi_norm + np.float32(0.05)), 0.0, 10.0).astype(np.float32)
    write(12, "sepa_mag_persist_ratio", persist)
    del up_norm, tmi_norm
    write(13, "sepa_mag_up150_ridge", vesselness(up_g2, fp, 2.5))
    up_aniso, up_u, up_v = _structure_tensor(up150, 2.0, 5.0)
    del up150, up_g2
    grav = fields.pop("iso_grav_anom")
    _, _, grav_g2 = _grad(grav, 2.0)
    _, _, grav_g6 = _grad(grav, 6.0)
    del grav
    write(14, "sepa_grav_persist_ratio",
          np.clip(grav_g6 / (grav_g2 + np.float32(1e-6)), 0.0, 5.0).astype(np.float32))
    del grav_g2, grav_g6
    write(15, "sepa_persist_orient", _orient_agree(seis_aniso3, seis_u3, seis_v3, up_aniso, up_u, up_v))
    del seis_aniso3, seis_u3, seis_v3, up_aniso, up_u, up_v
    write(16, "sepa_mag_scale_decay",
          np.log((tmi_g8 + np.float32(1e-6)) / (tmi_g2 + np.float32(1e-6))).astype(np.float32))
    del tmi_g2, tmi_g8
    write(17, "sepa_strain_x_persist", strain_grad_log * np.log1p(persist))
    del strain_grad_log, persist
    gc.collect()

    mm.flush()
    del mm
    mmr = np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols))
    if not np.isfinite(np.asarray(mmr[::997])).all():
        raise AssertionError("non-finite SEPA channel values (strided check)")
    meta = {
        "schema": SEPA_SCHEMA_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(SEPA_FEATURES),
        "hashes": hashes,
        "bands": {str(k): v for k, v in _BANDS},
        "extensions_band4": "TMI_up150",
        "zero_catalogue": True,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return mmr, meta


def fit_and_emit_production_sepa(grid, X_phys_mm, X_sepa_mm, sense_src, scarp_fields,
                                 cache_dir: Path, seed: int = 8825):
    """Full-catalogue SEPA PoE fit + H33-parity stratified emission (37,654 dots).

    Posterior fitting mirrors ``tdkl.fit_and_emit_production_tdkl`` (shared
    ``adhr`` dual-expectation models + ``tdkl._poe_pool``); only the cache
    identity and the preregistered H33-parity allocation differ:
    collar ``d_cat > 2.5 px``, near 21,500 dots (``2.5 < d <= 25 px``,
    spacing >= 2.85 px) + far 16,154 dots (``d > 25 px``, spacing >= 3.05 px).
    """
    from gems57 import damagezone_envelope, emit, holdout

    from . import adhr
    from .tdkl import _poe_pool

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    n_fp = int(ys_fp.size)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_post = cache_dir / f"sepa_prod_posteriors_s{seed}_{SEPA_SCHEMA_VERSION}.npz"
    X_vis_full, d_full_fp, comp_len_full_fp = adhr.compute_visible_struct_fp(
        grid, full_cat, sense_src, scarp_fields, cache_dir, tag="prod_fullcat")
    act_idx = np.flatnonzero(d_full_fp > 2.5)
    d_act = d_full_fp[act_idx]

    if cache_post.exists():
        data = np.load(cache_post)
        if int(data["act_idx"].size) != int(act_idx.size) or not np.array_equal(data["act_idx"], act_idx):
            raise ValueError("cached SEPA production posteriors do not match the 2.5 px collar domain")
        p_phys_poe, m_phys_poe = data["p_phys_poe"], data["m_phys_poe"]
        p_full_poe, m_full_poe = data["p_full_poe"], data["m_full_poe"]
    else:
        dom_all = np.ones(n_fp, dtype=bool)
        clfs44, regs44 = adhr._fit_dual_expectation_models(
            [X_phys_mm], dom_all, full_cat, fp, seed=seed + 7, n_ensemble=1)
        p44, m44 = adhr._predict_dual_chunked(clfs44, regs44, [X_phys_mm], act_idx)
        del clfs44, regs44
        gc.collect()
        clfs62, regs62 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_sepa_mm], dom_all, full_cat, fp, seed=seed + 107, n_ensemble=1)
        p62, m62 = adhr._predict_dual_chunked(clfs62, regs62, [X_phys_mm, X_sepa_mm], act_idx)
        del clfs62, regs62
        gc.collect()
        p_phys_poe, m_phys_poe = _poe_pool(p44, m44, p62, m62, w_tdkl=0.65, d_vis_act=d_act)
        del p44, m44, p62, m62
        gc.collect()

        syn_folds, _ = holdout.buffered_component_draw(grid, seed=20, hide_frac=0.20, buffer_px=3, boundary_px=12)
        syn_vis = syn_folds[0]["visible"]
        syn_hid = syn_folds[0]["hidden_all"]
        X_vis_syn, d_syn_fp, comp_len_syn_fp = adhr.compute_visible_struct_fp(
            grid, syn_vis, sense_src, scarp_fields, cache_dir, tag="seed20_f0_NW")
        wlaw = damagezone_envelope.fit_width_law(comp_len_syn_fp, d_syn_fp, syn_hid[ys_fp, xs_fp],
                                                 quantile=0.90, l0_px=40.0)
        d_over_w_syn = (d_syn_fp / np.maximum(wlaw.half_width(comp_len_syn_fp), 1e-6)).astype(np.float32)
        d_over_w_full = (d_full_fp / np.maximum(wlaw.half_width(comp_len_full_fp), 1e-6)).astype(np.float32)
        dom_syn = (~syn_vis)[ys_fp, xs_fp]
        c67, r67 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_vis_syn, d_over_w_syn], dom_syn, syn_hid, fp, seed=seed + 41, n_ensemble=1)
        p67, m67 = adhr._predict_dual_chunked(c67, r67, [X_phys_mm, X_vis_full, d_over_w_full], act_idx)
        del c67, r67
        gc.collect()
        c85, r85 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_sepa_mm, X_vis_syn, d_over_w_syn], dom_syn, syn_hid, fp, seed=seed + 141, n_ensemble=1)
        del X_vis_syn, d_syn_fp, comp_len_syn_fp, d_over_w_syn
        p85, m85 = adhr._predict_dual_chunked(c85, r85, [X_phys_mm, X_sepa_mm, X_vis_full, d_over_w_full], act_idx)
        del c85, r85, d_over_w_full
        gc.collect()
        p_full_poe, m_full_poe = _poe_pool(p67, m67, p85, m85, w_tdkl=0.65, d_vis_act=d_act)
        del p67, m67, p85, m85
        gc.collect()
        np.savez(cache_post, act_idx=act_idx, p_phys_poe=p_phys_poe, m_phys_poe=m_phys_poe,
                 p_full_poe=p_full_poe, m_full_poe=m_full_poe)

    k_prod = float(full_cat.sum()) * 0.30
    p_fused, m_fused = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe,
                                           k_prod, beta_phys=0.40, pi_unmapped=0.55)
    near_sel = d_act <= 25.0
    far_sel = d_act > 25.0
    near_budget, far_budget = 21_500, 16_154
    k_near = k_prod * (near_budget / (near_budget + far_budget))
    k_far = k_prod - k_near

    p_comb = np.empty_like(p_fused)
    m_comb = np.empty_like(m_fused)
    scale_near = float(k_near) / max(float(p_fused[near_sel].sum()), 1e-6)
    p_near = np.clip(p_fused[near_sel] * np.float32(scale_near), 0.0, 1.0).astype(np.float32)
    m_near = np.clip(m_fused[near_sel] * np.float32(min(max(scale_near, 0.85), 1.15)), p_near, 1.0).astype(np.float32)
    p_far_raw = 0.30 * p_fused[far_sel] + 0.70 * p_phys_poe[far_sel]
    m_far_raw = 0.30 * m_fused[far_sel] + 0.70 * m_phys_poe[far_sel]
    scale_far = float(k_far) / max(float(p_far_raw.sum()), 1e-6)
    p_far = np.clip(p_far_raw * np.float32(scale_far), 0.0, 1.0).astype(np.float32)
    m_far = np.clip(m_far_raw * np.float32(min(max(scale_far, 0.85), 1.25)), p_far, 1.0).astype(np.float32)
    p_comb[near_sel], m_comb[near_sel] = p_near, m_near
    p_comb[far_sel], m_comb[far_sel] = p_far, m_far
    del p_fused, m_fused, p_near, m_near, p_far, m_far, p_far_raw, m_far_raw

    p_grid = adhr.scatter_fp(p_comb, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    m_grid = adhr.scatter_fp(m_comb, ys_fp[act_idx], xs_fp[act_idx], grid.shape)
    del p_comb, m_comb
    gc.collect()

    allowed_near = np.zeros(grid.shape, dtype=bool)
    allowed_near[ys_fp[act_idx[near_sel]], xs_fp[act_idx[near_sel]]] = True
    allowed_far = np.zeros(grid.shape, dtype=bool)
    allowed_far[ys_fp[act_idx[far_sel]], xs_fp[act_idx[far_sel]]] = True
    alloc_near = emit.dinkelbach_allocate(p_grid, m_grid, allowed_near, budget=near_budget,
                                          k_truth=k_near, min_spacing_px=2.85, dinkelbach_iters=8)
    alloc_far = emit.dinkelbach_allocate(p_grid, m_grid, allowed_far, budget=far_budget,
                                         k_truth=k_far, min_spacing_px=3.05, dinkelbach_iters=8)
    emitted = np.clip(alloc_near.emitted + alloc_far.emitted, 0.0, 1.0).astype(np.float32)
    n_dots = int((emitted > 0).sum())
    n_far = int((alloc_far.emitted > 0).sum())
    return emitted, p_grid, {
        "n_dots": n_dots,
        "n_near_dots": int(alloc_near.n_dots),
        "n_far_dots": n_far,
        "share_gt25": float(n_far / max(n_dots, 1)),
        "k_truth_est": float(k_prod),
        "surrogate_dti_near": float(alloc_near.surrogate_dti),
        "surrogate_dti_far": float(alloc_far.surrogate_dti),
    }
