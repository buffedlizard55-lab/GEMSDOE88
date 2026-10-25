"""H88-DHTC: Deep Hydro-Tectonic Conduit Conjunction feature extractor.

16 zero-catalogue channels combining:
- Subsurface electrical conductivity (Band 17 ``cond_surf``)
- Basement density steps (Band 5, 13, 18 ``iso_grav_anom``, ``iso_grav_anom_slope``, ``iso_grav_anom_hg``)
- Depth-to-basement normal fault steps (Band 15 ``depth_to_base_surf``)
- Geodetic dilatational shear strain tensor (Bands 4, 7, 8 ``geod_2ndinv``, ``geod_shearrate``, ``geod_dilaterate``)
- Radiometric hydrothermal alteration redox (U/Th, K/Th from ``geodawn_rad_u8.tif``)
- Cross-scale conduit index and blind basin fault prioritisation.

Zero-catalogue guarantee: ``existing_faults.tif`` is NEVER read.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

DHTC_FEATURES: tuple[str, ...] = (
    "dhtc_cond_surf",
    "dhtc_cond_hg_35",
    "dhtc_grav_anom",
    "dhtc_grav_hg_35",
    "dhtc_grav_slope",
    "dhtc_zbase",
    "dhtc_zbase_step_35",
    "dhtc_basement_density_concord",
    "dhtc_geod_shearrate",
    "dhtc_geod_dilaterate",
    "dhtc_geod_2ndinv",
    "dhtc_dilational_shear_prod",
    "dhtc_rad_u_th_redox",
    "dhtc_rad_k_th_potassic",
    "dhtc_conduit_joint_index",
    "dhtc_basin_blind_conduit",
)

DHTC_SCHEMA_VERSION = "dhtc88-16ch-v1"


def _clean_footprint(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Scrub large sentinels and non-finite cells outside footprint to in-footprint median."""
    v = a.astype(np.float64)
    valid = mask & np.isfinite(v) & (np.abs(v) <= 1e18)
    med = float(np.median(v[valid])) if valid.any() else 0.0
    out = np.where(valid, v, med)
    return out


def _robust_z(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    v = a.astype(np.float64)
    valid = mask & np.isfinite(v) & (np.abs(v) <= 1e18)
    out = np.zeros_like(a, dtype=np.float32)
    if not valid.any():
        return out
    vals = v[valid]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med)))
    denom = max(1.4826 * mad, 1e-6)
    z = np.clip((v - med) / denom, -10.0, 10.0).astype(np.float32)
    out[mask] = z[mask]
    return out


def _grad_mag_2d(clean_img: np.ndarray, sigma: float) -> np.ndarray:
    smooth = ndi.gaussian_filter(clean_img, sigma=sigma, mode="nearest")
    gy, gx = np.gradient(smooth)
    return np.hypot(gy, gx).astype(np.float32)


def build_or_load_dhtc_memmap(root: Path, g, cache_dir: Path) -> tuple[np.memmap, dict]:
    """Build or load the (N_fp, 16) float32 DHTC feature memmap."""
    root = Path(root)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    n_fp = int(g.footprint.sum())
    n_cols = len(DHTC_FEATURES)
    dat_path = cache_dir / "x_dhtc_16ch.dat"
    meta_path = cache_dir / "x_dhtc_16ch.meta.json"

    if dat_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            if meta.get("shape") == [n_fp, n_cols] and meta.get("schema") == DHTC_SCHEMA_VERSION:
                mm = np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols))
                return mm, meta
        except Exception:
            pass

    ys, xs = np.nonzero(g.footprint)
    fp = g.footprint
    features_tif = root / "data/training_features.tif"
    rad_tif = root / "data/external/geodawn_rad_u8.tif"

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    print("[DHTC] Reading core feature bands from training_features.tif...", flush=True)
    with rasterio.open(features_tif) as src:
        # B04 geod_2ndinv
        geod_2ndinv = src.read(4)
        # B05 iso_grav_anom_slope
        grav_slope = src.read(5)
        # B07 geod_shearrate
        geod_shearrate = src.read(7)
        # B08 geod_dilaterate
        geod_dilaterate = src.read(8)
        # B13 iso_grav_anom
        grav_anom = src.read(13)
        # B15 depth_to_base_surf
        zbase = src.read(15)
        # B17 cond_surf
        cond_surf = src.read(17)

    print("[DHTC] Reading radiometric channels from geodawn_rad_u8.tif...", flush=True)
    with rasterio.open(rad_tif) as src:
        rad_k = src.read(1).astype(np.float32)
        rad_th = src.read(2).astype(np.float32)
        rad_u = src.read(3).astype(np.float32)

    # 1. dhtc_cond_surf
    z_cond = _robust_z(cond_surf, fp)
    mm[:, 0] = z_cond[ys, xs]

    # 2. dhtc_cond_hg_35
    cond_clean = _clean_footprint(cond_surf, fp)
    cond_hg = _grad_mag_2d(cond_clean, sigma=3.5)
    mm[:, 1] = _robust_z(cond_hg, fp)[ys, xs]
    del cond_clean, cond_hg

    # 3. dhtc_grav_anom
    z_grav = _robust_z(grav_anom, fp)
    mm[:, 2] = z_grav[ys, xs]

    # 4. dhtc_grav_hg_35
    grav_clean = _clean_footprint(grav_anom, fp)
    grav_hg_calc = _grad_mag_2d(grav_clean, sigma=3.5)
    z_grav_hg = _robust_z(grav_hg_calc, fp)
    mm[:, 3] = z_grav_hg[ys, xs]
    del grav_hg_calc

    # 5. dhtc_grav_slope
    mm[:, 4] = _robust_z(grav_slope, fp)[ys, xs]

    # 6. dhtc_zbase
    z_zbase = _robust_z(zbase, fp)
    mm[:, 5] = z_zbase[ys, xs]

    # 7. dhtc_zbase_step_35
    zbase_clean = _clean_footprint(zbase, fp)
    zbase_step = _grad_mag_2d(zbase_clean, sigma=3.5)
    z_zbase_step = _robust_z(zbase_step, fp)
    mm[:, 6] = z_zbase_step[ys, xs]
    del zbase_step

    # 8. dhtc_basement_density_concord (cosine concordance of gravity and basement gradient vectors)
    smooth_g = ndi.gaussian_filter(grav_clean, sigma=3.5, mode="nearest")
    smooth_z = ndi.gaussian_filter(zbase_clean, sigma=3.5, mode="nearest")
    gy_g, gx_g = np.gradient(smooth_g)
    gy_z, gx_z = np.gradient(smooth_z)
    norm_g = np.hypot(gy_g, gx_g) + 1e-4
    norm_z = np.hypot(gy_z, gx_z) + 1e-4
    dot_prod = (gy_g / norm_g) * (gy_z / norm_z) + (gx_g / norm_g) * (gx_z / norm_z)
    concord = np.clip(dot_prod, -1.0, 1.0).astype(np.float32)
    mm[:, 7] = concord[ys, xs]
    del smooth_g, smooth_z, gy_g, gx_g, gy_z, gx_z, norm_g, norm_z, dot_prod, concord, grav_clean, zbase_clean

    # 9. dhtc_geod_shearrate
    z_shear = _robust_z(geod_shearrate, fp)
    mm[:, 8] = z_shear[ys, xs]

    # 10. dhtc_geod_dilaterate
    z_dilat = _robust_z(geod_dilaterate, fp)
    mm[:, 9] = z_dilat[ys, xs]

    # 11. dhtc_geod_2ndinv
    z_secinv = _robust_z(geod_2ndinv, fp)
    mm[:, 10] = z_secinv[ys, xs]

    # 12. dhtc_dilational_shear_prod (dilational shear rate tensor product)
    dilat_pos = np.maximum(_clean_footprint(geod_dilaterate, fp), 0.0)
    shear_clean = _clean_footprint(geod_shearrate, fp)
    shear_dilat = shear_clean * dilat_pos
    mm[:, 11] = _robust_z(shear_dilat, fp)[ys, xs]
    del dilat_pos, shear_clean, shear_dilat

    # 13. dhtc_rad_u_th_redox
    rad_th_c = np.maximum(rad_th, 0.0)
    rad_u_c = np.maximum(rad_u, 0.0)
    u_th = np.where((rad_th_c > 0) & fp, rad_u_c / (rad_th_c + 1.0), 0.0)
    mm[:, 12] = _robust_z(u_th, fp)[ys, xs]
    del u_th

    # 14. dhtc_rad_k_th_potassic
    rad_k_c = np.maximum(rad_k, 0.0)
    k_th = np.where((rad_th_c > 0) & fp, rad_k_c / (rad_th_c + 1.0), 0.0)
    mm[:, 13] = _robust_z(k_th, fp)[ys, xs]
    del k_th, rad_k, rad_th, rad_u, rad_k_c, rad_th_c, rad_u_c

    # 15. dhtc_conduit_joint_index (conduit conjunction index: conductivity + basement step + shear strain)
    cond_norm = np.clip((z_cond[ys, xs] + 3.0) / 6.0, 0.0, 1.0)
    step_norm = np.clip((z_zbase_step[ys, xs] + 1.0) / 4.0, 0.0, 1.0)
    strain_norm = np.clip((z_shear[ys, xs] + 2.0) / 5.0, 0.0, 1.0)
    conduit_joint = (cond_norm * step_norm * strain_norm) ** (1.0 / 3.0)
    mm[:, 14] = np.nan_to_num(conduit_joint, nan=0.0).astype(np.float32)
    del cond_norm, step_norm, strain_norm, conduit_joint

    # 16. dhtc_basin_blind_conduit (conduit index gated to deep alluvium where zbase > median)
    zbase_fp = zbase[ys, xs]
    valid_zb = np.isfinite(zbase_fp) & (np.abs(zbase_fp) <= 1e18)
    med_zbase = float(np.median(zbase_fp[valid_zb])) if valid_zb.any() else 0.0
    basin_gate = (zbase_fp > med_zbase).astype(np.float32)
    mm[:, 15] = (mm[:, 14] * basin_gate).astype(np.float32)
    del zbase_fp, valid_zb, basin_gate

    mm.flush()

    for j in range(n_cols):
        col_vals = mm[:, j]
        if not np.isfinite(col_vals).all():
            raise AssertionError(f"Non-finite values found in DHTC channel {DHTC_FEATURES[j]}")

    meta = {
        "schema": DHTC_SCHEMA_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(DHTC_FEATURES),
        "feature_count": n_cols,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    del mm
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta
