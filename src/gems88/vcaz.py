"""H88-VCAZ: Vapor-Chimney Acid-Sulfate / Phreatic-Vent Partitioning,
Silica-Cation Boiling-Mixing Vector & Anisotropic Strike-Steered Subsurface Conduit Tensor.

Preregistration: ``registry/preregistration_vcaz88.json`` (``PREREG-20261025-VCAZ88``).

Zero-catalogue guarantee
------------------------
``build_or_load_vcaz_memmap`` NEVER opens ``existing_faults.tif``, ``trace_segments_utm11.csv``,
or ``sgmc_faults_100m.tif``, and explicitly strips ``dist_known_fault_px`` on load from
``gdr_wellspring_in_footprint.csv``. Every VCAZ-24 channel is strictly invariant to
held-out test-quadrant fault labels and verified against the single-feature symmetric
ROC-AUC <= 0.90 canary across both spatial holdout seeds (20, 21).
"""
from __future__ import annotations

import csv
import gc
import hashlib
import io
import json
import math
import mmap
import zipfile
from collections import defaultdict
from pathlib import Path

import lightgbm as lgb
import numpy as np
import rasterio
from rasterio.warp import transform as crs_transform
from scipy import ndimage as ndi

from gems57 import damagezone_envelope, emit
from . import adhr, physics

VCAZ_SCHEMA_VERSION = "vcaz88-v2"

VCAZ_FEATURES: tuple[str, ...] = (
    # Block I: 4-Facies Thermodynamic Paleo-Vent Partitioning (DOE GDR #1391)
    "vcaz_vapor_chimney_kern",
    "vcaz_sinter_boiling_kern",
    "vcaz_trav_updip_feeder",
    "vcaz_vapor_over_carbonate_ratio",
    # Block II: Multi-Polymorph Solute Boiling-Mixing & Volcanic Dike Alignment
    "vcaz_qtz_chalc_boiling_idx",
    "vcaz_cat_chalc_outflow_updip",
    "vcaz_spring_vs_well_plumbing",
    "vcaz_volc_vent_dike_ridge",
    # Block III: 2-m Probe Conductive dT/dz & 1D Advective Peclet Concavity
    "vcaz_probe_dtdz_norm",
    "vcaz_probe_peclet_concavity",
    # Block IV: Anisotropic Subsurface-Strike-Steered Potential-Field, Alteration & 3DEP Tensor
    "vcaz_strike_grav_slope_ridge",
    "vcaz_strike_mag_tc_ridge",
    "vcaz_euler_deep_fault_index",
    "vcaz_alteration_f_param_uk",
    "vcaz_strike_cond_smectite_gouge",
    "vcaz_lidar_subsurface_strike_lock",
    "vcaz_lidar_orthog_relay_breach",
    "vcaz_seismic_brittle_work_rate",
    "vcaz_3dep_mound_sink_lineament",
    "vcaz_3dep_branch_piracy_div",
    "vcaz_piedmont_burial_hinge",
    "vcaz_conduit_joint_poe_prior",
    # Block V: Explicit Named Non-Fault Mimic Suppressors
    "vcaz_mimic_pluvial_tufa_shore",
    "vcaz_mimic_shallow_volc_edge",
)

# Exclude smooth province-scale DC fields from the translation-invariant zero-catalogue
# specialist so trees split on local fault-conduit mechanics rather than quadrant coordinates.
REGIONAL_DC_EXCLUSIONS: frozenset[str] = frozenset({
    "cond_surf_raw",
    "depth_to_base_log",
    "det_elev",
    "geod_strain_2ndinv",
    "geod_transtension",
    "seismic_prox",
    "probe2m_dab_reg",
    "volcanic_vent_prox",
})

PHYS_DECONF_INDICES: tuple[int, ...] = tuple(
    i for i, nm in enumerate(physics.ALL_PHYS_FEATURES) if nm not in REGIONAL_DC_EXCLUSIONS
)


def _evict_mmap(arr: object) -> None:
    if not hasattr(mmap, "MADV_DONTNEED"):
        return
    base = getattr(arr, "base", arr)
    mm_obj = getattr(base, "_mmap", getattr(arr, "_mmap", None))
    if mm_obj is not None and hasattr(mm_obj, "madvise"):
        try:
            mm_obj.madvise(mmap.MADV_DONTNEED)
        except OSError:
            pass


class ColumnSubsetView:
    """Memory-bounded column view over a disk-backed float32 ``np.memmap``."""

    def __init__(self, base: np.ndarray, cols: tuple[int, ...]) -> None:
        self.base = base
        self.cols = np.asarray(cols, dtype=np.int32)
        self.shape = (base.shape[0], int(self.cols.size))
        self.dtype = np.float32
        self.ndim = 2

    def __getitem__(self, idx) -> np.ndarray:
        sub = np.asarray(self.base[idx], dtype=np.float32)
        out = sub[self.cols].copy() if sub.ndim == 1 else sub[:, self.cols].copy()
        del sub
        _evict_mmap(self.base)
        return out


def _robust_z_fp(vec: np.ndarray) -> np.ndarray:
    v = np.asarray(vec, dtype=np.float32)
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med))) * 1.4826 + 1e-5
    return np.clip((v - np.float32(med)) / np.float32(mad), -8.0, 8.0).astype(np.float32)


def _aniso_strike_ridge_fp(
    field_2d: np.ndarray,
    ys: np.ndarray,
    xs: np.ndarray,
    sy_fp: np.ndarray,
    sx_fp: np.ndarray,
    L_par_1: float = 3.0,
    L_par_2: float = 6.0,
    L_perp: float = 4.0,
    hp_weight: float = 0.55,
) -> np.ndarray:
    """Subpixel subsurface-strike-steered matched-filter ridge at footprint cells.

    Evaluates along-strike coherence at ``+-L_par_1, +-L_par_2`` along ``(sx, sy)``
    contrasted against cross-strike flanks at ``+-L_perp`` along ``(-sy, sx)``.
    """
    c0 = field_2d[ys, xs].astype(np.float32)
    s_p1 = physics._bilinear_at_fp(field_2d, ys, xs, sy_fp * L_par_1, sx_fp * L_par_1)
    s_m1 = physics._bilinear_at_fp(field_2d, ys, xs, -sy_fp * L_par_1, -sx_fp * L_par_1)
    s_p2 = physics._bilinear_at_fp(field_2d, ys, xs, sy_fp * L_par_2, sx_fp * L_par_2)
    s_m2 = physics._bilinear_at_fp(field_2d, ys, xs, -sy_fp * L_par_2, -sx_fp * L_par_2)
    along = (0.40 * c0 + 0.20 * (s_p1 + s_m1) + 0.10 * (s_p2 + s_m2)).astype(np.float32)

    ny_fp = -sx_fp
    nx_fp = sy_fp
    n_p = physics._bilinear_at_fp(field_2d, ys, xs, ny_fp * L_perp, nx_fp * L_perp)
    n_m = physics._bilinear_at_fp(field_2d, ys, xs, -ny_fp * L_perp, -nx_fp * L_perp)
    flank = (0.50 * (n_p + n_m)).astype(np.float32)
    w_hp = np.float32(hp_weight)
    return ((np.float32(1.0) - w_hp) * along + w_hp * (along - flank)).astype(np.float32)


def _classify_paleo_facies(dep_type: str) -> tuple[str, float]:
    """Partition Paleo_geothermal_final.csv into 4 thermodynamic facies."""
    dt = (dep_type or "").strip().lower()
    if not dt or "tufa" in dt:
        return ("tufa_mimic", 1.0 if "tufa" in dt else 0.0)
    if "explosion" in dt:
        return ("vapor_chimney", 2.5)
    if "sulfur" in dt or "sulfate" in dt:
        return ("vapor_chimney", 2.2)
    if "breccia" in dt or "silica vein" in dt or "silica-cemented" in dt:
        return ("vapor_chimney", 2.1)
    if "argillic" in dt or "alteration" in dt:
        return ("vapor_chimney", 1.6)
    if "sinter" in dt or "silicified" in dt:
        return ("sinter_boiling", 2.0)
    if "travertine" in dt or "calcite" in dt or "carbonate" in dt:
        return ("travertine_outflow", 1.4)
    return ("other", 0.5)


def build_or_load_vcaz_memmap(
    root: Path,
    grid,
    cache_dir: Path,
) -> tuple[np.memmap, dict[str, object]]:
    """Build or reload disk-backed ``(N_fp, 24)`` float32 VCAZ feature stack (< 520 MB RSS)."""
    root = Path(root)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    fp = np.asarray(grid.footprint, dtype=bool)
    ys, xs = np.nonzero(fp)
    n_fp = int(ys.size)
    n_cols = len(VCAZ_FEATURES)
    shape = grid.shape
    inv_tf = ~grid.transform

    dat_path = cache_dir / f"x_vcaz_{n_cols}ch_{VCAZ_SCHEMA_VERSION}.dat"
    meta_path = cache_dir / f"x_vcaz_{n_cols}ch_{VCAZ_SCHEMA_VERSION}.json"

    ext = root / "data/external"
    dep_files = (
        root / "data/training_features.tif",
        ext / "paleo_geothermal_regional.zip",
        ext / "gdr_wellspring_in_footprint.csv",
        ext / "gdr_volcanic_vents_in_footprint.csv",
        ext / "2m_temperature_probe_INGENIOUS_regional_data.zip",
        ext / "geodawn_rad_u8.tif",
        ext / "geodawn_extensions_u8.tif",
        ext / "lidar_scarp_features_u8.tif",
        ext / "topo_10m_derived_100m_u8.tif",
        ext / "dem10_chi_100m_i16.tif",
        ext / "dem10_chi_100m_u8.tif",
        ext / "dem10_chi_100m_sig_i32.tif",
    )
    input_hashes = {}
    for p in dep_files:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        input_hashes[p.name] = h.hexdigest()

    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("schema_version") == VCAZ_SCHEMA_VERSION
            and meta.get("shape") == [n_fp, n_cols]
            and meta.get("features") == list(VCAZ_FEATURES)
            and meta.get("input_hashes") == input_hashes
        ):
            return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta

    mm = np.memmap(dat_path, dtype="float32", mode="w+", shape=(n_fp, n_cols))

    # ------------------------------------------------------------------
    # Step 0: Smooth regional hydraulic head gradient (+grad z_smooth) & subsurface strike
    # ------------------------------------------------------------------
    with rasterio.open(ext / "dem10_chi_100m_i16.tif") as ds_chi:
        chi_step_m = (ds_chi.read(1).astype(np.float32)) * np.float32(0.001)
        z_raw = ds_chi.read(5).astype(np.float32)
    z_valid = (z_raw > -1000.0) & fp
    z_med = float(np.median(z_raw[z_valid]))
    z_m = np.where(z_valid, z_raw, z_med).astype(np.float32)
    del z_raw

    z_gy, z_gx, z_gmag = physics._grad_f32(z_m, 7.0)
    updip_y_fp = (z_gy[ys, xs] / (z_gmag[ys, xs] + 1e-4)).astype(np.float32)
    updip_x_fp = (z_gx[ys, xs] / (z_gmag[ys, xs] + 1e-4)).astype(np.float32)
    hyd_gate_fp = np.tanh(z_gmag[ys, xs] / 1.8).astype(np.float32)
    del z_gy, z_gx, z_gmag

    z_fp = z_m[ys, xs]
    lahontan_ring_fp = np.exp(-0.5 * (((z_fp - 1330.0) / 38.0) ** 2)).astype(np.float32)
    bonneville_ring_fp = np.exp(-0.5 * (((z_fp - 1555.0) / 38.0) ** 2)).astype(np.float32)
    pluvial_elev_ring_fp = np.maximum(lahontan_ring_fp, bonneville_ring_fp)
    del z_m, z_fp, lahontan_ring_fp, bonneville_ring_fp
    gc.collect()

    with rasterio.open(ext / "geodawn_extensions_u8.tif") as ds_gext:
        gext_uk_u8 = ds_gext.read(2)
        gext_uth_u8 = ds_gext.read(3)
        gext_tmi150_u8 = ds_gext.read(4)
        gext_valid = (gext_tmi150_u8 > 0) & fp
        tmi150 = np.where(
            gext_valid, gext_tmi150_u8.astype(np.float32), float(np.median(gext_tmi150_u8[gext_valid]))
        ).astype(np.float32)
        uk_f = np.where(gext_uk_u8 > 0, gext_uk_u8.astype(np.float32) / 255.0, 0.0).astype(np.float32)
        uth_f = np.where(gext_uth_u8 > 0, gext_uth_u8.astype(np.float32) / 255.0, 0.0).astype(np.float32)
        del gext_uk_u8, gext_uth_u8, gext_tmi150_u8

    with rasterio.open(root / "data/training_features.tif") as src:
        def rd(idx: int) -> np.ndarray:
            return physics.clean_band(src.read(idx), fp)[0]

        zbase = np.maximum(rd(15), 0.0)
        grav = rd(13)

        bgy, bgx, bmag = physics._grad_f32(zbase, 4.0)
        ggy, ggx, gmag = physics._grad_f32(grav, 4.0)
        mgy, mgx, mmag = physics._grad_f32(tmi150, 4.0)
        del grav

        bn = bmag + float(np.percentile(bmag[fp], 75)) * 0.25 + 1e-5
        gn = gmag + float(np.percentile(gmag[fp], 75)) * 0.25 + 1e-5
        mn = mmag + float(np.percentile(mmag[fp], 75)) * 0.25 + 1e-5

        jxx = ndi.gaussian_filter((bgx / bn) ** 2 + (ggx / gn) ** 2 + 0.6 * (mgx / mn) ** 2, sigma=4.0, mode="nearest")
        jyy = ndi.gaussian_filter((bgy / bn) ** 2 + (ggy / gn) ** 2 + 0.6 * (mgy / mn) ** 2, sigma=4.0, mode="nearest")
        jxy = ndi.gaussian_filter(
            (bgx * bgy) / (bn * bn) + (ggx * ggy) / (gn * gn) + 0.6 * (mgx * mgy) / (mn * mn),
            sigma=4.0,
            mode="nearest",
        )
        del bgy, bgx, ggy, ggx, mgy, mgx, bn, gn, mn

        phi_n = 0.5 * np.arctan2(2.0 * jxy[ys, xs], jxx[ys, xs] - jyy[ys, xs])
        theta_sub_fp = (phi_n + np.float32(0.5 * math.pi)).astype(np.float32)
        sx_fp = np.cos(theta_sub_fp).astype(np.float32)
        sy_fp = np.sin(theta_sub_fp).astype(np.float32)
        del jxx, jyy, jxy, phi_n

        bmag_fp = bmag[ys, xs].copy()
        gmag4_fp = gmag[ys, xs].copy()
        tmi150_mag_fp = mmag[ys, xs].copy()
        del bmag, gmag, mmag

        # Ch 10: Strike-steered B05 iso_grav_anom_slope ridge
        b05_gslope = np.log1p(np.maximum(rd(5), 0.0))
        mm[:, 10] = _robust_z_fp(_aniso_strike_ridge_fp(b05_gslope, ys, xs, sy_fp, sx_fp))
        del b05_gslope

        # Ch 11: Strike-steered B06 magnetic total/tilt curvature ridge
        b06_tc = rd(6)
        b06_abs = np.log1p(np.abs(b06_tc))
        b06_fp = b06_abs[ys, xs].copy()
        mm[:, 11] = _robust_z_fp(_aniso_strike_ridge_fp(b06_abs, ys, xs, sy_fp, sx_fp))
        del b06_tc, b06_abs

        # Ch 12: Euler deep fault contact index
        b03_tmi_hg = np.maximum(rd(3), 0.0)
        b11_gvg = rd(11)
        b18_ghg = np.maximum(rd(18), 0.0)
        grav_tilt_zero = np.exp(-np.abs(np.arctan2(b11_gvg[ys, xs], b18_ghg[ys, xs] + 1e-5)) / 0.38).astype(np.float32)
        tmi_hg_fp = b03_tmi_hg[ys, xs]
        up_survival = tmi150_mag_fp / (tmi150_mag_fp + 0.35 * np.log1p(tmi_hg_fp) + 0.25)
        euler_2d = np.zeros(shape, dtype=np.float32)
        euler_2d[ys, xs] = grav_tilt_zero * up_survival * np.log1p(b18_ghg[ys, xs] * 50.0)
        mm[:, 12] = _robust_z_fp(_aniso_strike_ridge_fp(euler_2d, ys, xs, sy_fp, sx_fp))
        b18_fp = b18_ghg[ys, xs].copy()
        del b03_tmi_hg, b11_gvg, b18_ghg, grav_tilt_zero, up_survival, euler_2d

        # Ch 23 (Named Mimic #2): Shallow volcanic lava-flow edge
        shallow_mag = _robust_z_fp(np.log1p(tmi_hg_fp) + 0.6 * b06_fp)
        deep_quiet = np.exp(
            -(b18_fp / (float(np.percentile(b18_fp, 65)) + 1e-5))
            - (bmag_fp / (float(np.percentile(bmag_fp, 65)) + 1e-5))
        )
        mm[:, 23] = _robust_z_fp(np.maximum(shallow_mag, 0.0) * deep_quiet.astype(np.float32))
        del tmi_hg_fp, b06_fp, shallow_mag, deep_quiet

        # Ch 13: Airborne gamma-ray Efimov F-parameter (K * U / Th^2) + UK + magnetite destruction (high-pass)
        b02_rtp = rd(2)
        rtp_hp_fp = (ndi.gaussian_filter(b02_rtp, sigma=8.0, mode="nearest")[ys, xs] - b02_rtp[ys, xs]).astype(np.float32)
        del b02_rtp
        with rasterio.open(ext / "geodawn_rad_u8.tif") as ds_rad:
            rk = ds_rad.read(1).astype(np.float32)
            rth = ds_rad.read(2).astype(np.float32)
            ru = ds_rad.read(3).astype(np.float32)
        rad_ok = (rk > 0) & (rth > 0) & fp
        f_efimov = np.where(rad_ok, np.log1p((rk * (ru + 1.0)) / (rth * rth + 25.0)), 0.0).astype(np.float32)
        f_efimov_hp = f_efimov - ndi.gaussian_filter(f_efimov, sigma=14.0, mode="nearest")
        uk_hp = uk_f - ndi.gaussian_filter(uk_f, sigma=14.0, mode="nearest")
        uth_hp = uth_f - ndi.gaussian_filter(uth_f, sigma=14.0, mode="nearest")
        del rk, rth, ru, rad_ok, f_efimov, uk_f, uth_f
        alt_2d = np.zeros(shape, dtype=np.float32)
        mag_destr = np.clip(_robust_z_fp(rtp_hp_fp), -2.0, 5.0)
        alt_2d[ys, xs] = (
            _robust_z_fp(f_efimov_hp[ys, xs]) + 0.55 * _robust_z_fp(uk_hp[ys, xs]) + 0.35 * _robust_z_fp(uth_hp[ys, xs])
        ) * (0.5 + 0.5 / (1.0 + np.exp(-mag_destr)))
        mm[:, 13] = _robust_z_fp(_aniso_strike_ridge_fp(alt_2d, ys, xs, sy_fp, sx_fp, hp_weight=0.75))
        del f_efimov_hp, uk_hp, uth_hp, rtp_hp_fp, mag_destr, alt_2d

        # Ch 14: Strike-steered smectite/clay fault-gouge conductivity ridge (local high-pass)
        b17_cond = np.log1p(np.maximum(rd(17), 0.0))
        b17_hp = b17_cond - ndi.gaussian_filter(b17_cond, sigma=12.0, mode="nearest")
        b19_slope = np.maximum(rd(19), 0.0)
        non_playa_fp = np.tanh(b19_slope[ys, xs] / (float(np.percentile(b19_slope[fp], 30)) + 1e-4)).astype(np.float32)
        mm[:, 14] = _robust_z_fp(_aniso_strike_ridge_fp(b17_hp, ys, xs, sy_fp, sx_fp, hp_weight=0.75) * (0.25 + 0.75 * non_playa_fp))
        del b17_cond, b17_hp, b19_slope

        # Ch 17: Locally high-pass normalized seismogenic brittle dilatational work rate
        b07_sh = np.abs(rd(7))
        b08_dl = np.maximum(rd(8), 0.0)
        b10_deq = np.maximum(rd(10), 0.0)
        b16_ieq = np.maximum(rd(16), 0.0)
        work_raw = np.log1p(b07_sh * (0.5 + 10.0 * b08_dl)) * (0.5 + np.exp(-b10_deq / 25000.0) + 0.25 * np.log1p(b16_ieq))
        work_hp = work_raw - ndi.gaussian_filter(work_raw, sigma=18.0, mode="nearest")
        del b07_sh, b08_dl, b10_deq, b16_ieq, work_raw
        seism_2d = np.zeros(shape, dtype=np.float32)
        seism_2d[ys, xs] = work_hp[ys, xs] * np.log1p(b18_fp * 30.0 + bmag_fp * 0.15)
        mm[:, 17] = _robust_z_fp(_aniso_strike_ridge_fp(seism_2d, ys, xs, sy_fp, sx_fp, hp_weight=0.70))
        del work_hp, seism_2d

        # Ch 20: Piedmont burial-hinge curvature (50..650 m cover step basinward of bedrock range fronts)
        zb_lap = ndi.gaussian_laplace(zbase, sigma=3.0, mode="nearest")
        zb_fp = zbase[ys, xs]
        hinge_win = np.exp(-0.5 * (((zb_fp - 260.0) / 240.0) ** 2)).astype(np.float32)
        hinge_2d = np.zeros(shape, dtype=np.float32)
        hinge_2d[ys, xs] = hinge_win * np.log1p(np.abs(zb_lap[ys, xs])) * np.log1p(bmag_fp * 0.2)
        mm[:, 20] = _robust_z_fp(_aniso_strike_ridge_fp(hinge_2d, ys, xs, sy_fp, sx_fp))
        del zbase, zb_lap, zb_fp, hinge_win, hinge_2d
        gc.collect()

    # ------------------------------------------------------------------
    # Step 1: 4-Facies Thermodynamic Paleo-Vent Partitioning (Paleo_geothermal_final.csv, NAD83 lon/lat)
    # ------------------------------------------------------------------
    facies_pts: dict[str, tuple[list[float], list[float], list[float]]] = {
        "vapor_chimney": ([], [], []),
        "sinter_boiling": ([], [], []),
        "travertine_outflow": ([], [], []),
        "tufa_mimic": ([], [], []),
    }
    facies_counts: dict[str, int] = defaultdict(int)
    raw_paleo_lons, raw_paleo_lats, raw_paleo_types = [], [], []
    with zipfile.ZipFile(ext / "paleo_geothermal_regional.zip") as zf:
        txt = io.TextIOWrapper(zf.open("Paleo_geothermal_final.csv"), encoding="utf-8-sig", errors="replace")
        for row in csv.DictReader(txt):
            try:
                lo = float(row["Long_deg_NAD83"])
                la = float(row["Lat_deg_NAD83"])
            except (KeyError, ValueError, TypeError):
                continue
            if math.isfinite(lo) and math.isfinite(la) and -125.0 < lo < -110.0 and 34.0 < la < 44.0:
                raw_paleo_lons.append(lo)
                raw_paleo_lats.append(la)
                raw_paleo_types.append(row.get("Deposit_type", ""))

    p_ux, p_uy = crs_transform("EPSG:4269", grid.crs, raw_paleo_lons, raw_paleo_lats)
    for ux, uy, dtype_str in zip(p_ux, p_uy, raw_paleo_types):
        c_f, r_f = inv_tf * (ux, uy)
        ri, ci = int(math.floor(r_f)), int(math.floor(c_f))
        if not (0 <= ri < shape[0] and 0 <= ci < shape[1] and fp[ri, ci]):
            continue
        fcls, wt = _classify_paleo_facies(dtype_str)
        facies_counts[fcls] += 1
        if fcls in facies_pts and wt > 0.0:
            facies_pts[fcls][0].append(float(ri))
            facies_pts[fcls][1].append(float(ci))
            facies_pts[fcls][2].append(float(wt))

    if facies_counts["vapor_chimney"] < 50 or facies_counts["sinter_boiling"] < 30:
        raise AssertionError(f"Unexpectedly few in-footprint paleo deposits: {dict(facies_counts)}")

    def _multi_splat(key: str, sigmas: tuple[float, float]) -> np.ndarray:
        rr, cc, ww = facies_pts[key]
        r_a = np.asarray(rr, dtype=np.float32)
        c_a = np.asarray(cc, dtype=np.float32)
        w_a = np.asarray(ww, dtype=np.float32)
        s0 = np.log1p(physics._splat_points(shape, r_a, c_a, w_a, sigma_px=sigmas[0]) * 45.0)
        s1 = np.log1p(physics._splat_points(shape, r_a, c_a, w_a, sigma_px=sigmas[1]) * 140.0)
        return (0.60 * s0 + 0.40 * s1).astype(np.float32)

    vap_2d = _multi_splat("vapor_chimney", (3.0, 9.0))
    sin_2d = _multi_splat("sinter_boiling", (3.5, 10.0))
    trv_2d = _multi_splat("travertine_outflow", (4.0, 12.0))
    tuf_2d = _multi_splat("tufa_mimic", (4.0, 12.0))

    mm[:, 0] = _robust_z_fp(vap_2d[ys, xs])
    mm[:, 1] = _robust_z_fp(sin_2d[ys, xs])
    trv_down1 = physics._bilinear_at_fp(trv_2d, ys, xs, -updip_y_fp * 12.0, -updip_x_fp * 12.0)
    trv_down2 = physics._bilinear_at_fp(trv_2d, ys, xs, -updip_y_fp * 25.0, -updip_x_fp * 25.0)
    mm[:, 2] = _robust_z_fp((0.55 * trv_down1 + 0.45 * trv_down2) * (0.35 + 0.65 * hyd_gate_fp))
    mm[:, 3] = _robust_z_fp((vap_2d[ys, xs] + 0.85 * sin_2d[ys, xs]) - 0.65 * (trv_2d[ys, xs] + 2.0 * tuf_2d[ys, xs]))

    grav_quiet_fp = np.exp(-gmag4_fp / (float(np.percentile(gmag4_fp, 65)) + 1e-5)).astype(np.float32)
    mm[:, 22] = _robust_z_fp(pluvial_elev_ring_fp * (0.40 + 1.60 * tuf_2d[ys, xs]) * grav_quiet_fp)
    del vap_2d, sin_2d, trv_2d, tuf_2d, trv_down1, trv_down2, pluvial_elev_ring_fp, grav_quiet_fp
    gc.collect()

    # ------------------------------------------------------------------
    # Step 2: Multi-Polymorph Solute Boiling-Mixing & Volcanic Dike Alignment
    # ------------------------------------------------------------------
    boil_r, boil_c, boil_w = [], [], []
    outf_r, outf_c, outf_w = [], [], []
    spr_r, spr_c, spr_w = [], [], []
    wel_r, wel_c, wel_w = [], [], []
    dropped_dist_col_verified = False

    with (ext / "gdr_wellspring_in_footprint.csv").open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and "dist_known_fault_px" in reader.fieldnames:
            dropped_dist_col_verified = True
        for row in reader:
            row.pop("dist_known_fault_px", None)
            assert "dist_known_fault_px" not in row
            try:
                ri = int(float(row["row"]))
                ci = int(float(row["col"]))
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 <= ri < shape[0] and 0 <= ci < shape[1] and fp[ri, ci]):
                continue
            lyr = (row.get("layer") or "").strip().lower()

            def _pf(k: str) -> float:
                s = (row.get(k) or "").strip()
                if not s:
                    return float("nan")
                try:
                    v = float(s)
                    return v if (-5.0 < v < 400.0) else float("nan")
                except ValueError:
                    return float("nan")

            tm = _pf("temp_c")
            tcat = _pf("geothermcat_c")
            tchl = _pf("geothermchalc_c")
            tqtz = _pf("geothermquartz_c")

            if math.isfinite(tqtz) and tqtz > 95.0:
                tm_eff = tm if math.isfinite(tm) else 20.0
                excess_q = max(tqtz - tm_eff, 0.0)
                coh = math.exp(-abs(tcat - tqtz) / 45.0) if math.isfinite(tcat) else 0.65
                bw = min(excess_q / 30.0, 5.0) * (0.5 + 0.5 * coh) * (1.0 + max(tqtz - 135.0, 0.0) / 60.0)
                if bw > 0.05:
                    boil_r.append(float(ri))
                    boil_c.append(float(ci))
                    boil_w.append(float(bw))

            if math.isfinite(tcat) and math.isfinite(tchl) and tcat > 110.0 and (tcat - tchl) > 12.0:
                ow = min((tcat - tchl) / 25.0, 5.0) * (1.0 + max(tcat - 150.0, 0.0) / 70.0)
                outf_r.append(float(ri))
                outf_c.append(float(ci))
                outf_w.append(float(ow))

            th_score = 0.0
            if math.isfinite(tm) and tm > 26.0:
                th_score += min((tm - 22.0) / 18.0, 4.5)
            if math.isfinite(tqtz) and tqtz > 105.0:
                th_score += min((tqtz - 95.0) / 35.0, 3.5)
            if th_score > 0.05:
                if "spring" in lyr:
                    spr_r.append(float(ri))
                    spr_c.append(float(ci))
                    spr_w.append(float(th_score))
                elif "well" in lyr:
                    wel_r.append(float(ri))
                    wel_c.append(float(ci))
                    wel_w.append(float(th_score))

    boil_2d = (
        0.65 * np.log1p(physics._splat_points(shape, np.asarray(boil_r), np.asarray(boil_c), np.asarray(boil_w), 5.5, True))
        + 0.35 * np.log1p(physics._splat_points(shape, np.asarray(boil_r), np.asarray(boil_c), np.asarray(boil_w), 13.0, True))
    ).astype(np.float32)
    mm[:, 4] = _robust_z_fp(boil_2d[ys, xs])
    del boil_2d

    outf_2d = (
        0.60 * np.log1p(physics._splat_points(shape, np.asarray(outf_r), np.asarray(outf_c), np.asarray(outf_w), 7.0, True))
        + 0.40 * np.log1p(physics._splat_points(shape, np.asarray(outf_r), np.asarray(outf_c), np.asarray(outf_w), 16.0, True))
    ).astype(np.float32)
    outf_d1 = physics._bilinear_at_fp(outf_2d, ys, xs, -updip_y_fp * 14.0, -updip_x_fp * 14.0)
    outf_d2 = physics._bilinear_at_fp(outf_2d, ys, xs, -updip_y_fp * 28.0, -updip_x_fp * 28.0)
    mm[:, 5] = _robust_z_fp((0.55 * outf_d1 + 0.45 * outf_d2) * (0.30 + 0.70 * hyd_gate_fp))
    del outf_2d, outf_d1, outf_d2, updip_y_fp, updip_x_fp, hyd_gate_fp

    spr_2d = np.log1p(physics._splat_points(shape, np.asarray(spr_r), np.asarray(spr_c), np.asarray(spr_w), 6.5, True))
    wel_2d = np.log1p(physics._splat_points(shape, np.asarray(wel_r), np.asarray(wel_c), np.asarray(wel_w), 11.0, True))
    mm[:, 6] = _robust_z_fp(0.60 * spr_2d[ys, xs] + 0.65 * wel_2d[ys, xs] * (1.0 - 0.4 * non_playa_fp))
    del spr_2d, wel_2d

    vr, vc = [], []
    with (ext / "gdr_volcanic_vents_in_footprint.csv").open("r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                vr.append(float(row["row"]))
                vc.append(float(row["col"]))
            except (KeyError, ValueError, TypeError):
                continue
    v_loc = np.log1p(physics._splat_points(shape, np.asarray(vr), np.asarray(vc), np.ones(len(vr), np.float32), 9.0) * 180.0)
    vdike_2d = np.zeros(shape, dtype=np.float32)
    vdike_2d[ys, xs] = v_loc[ys, xs] * np.log1p(tmi150_mag_fp)
    mm[:, 7] = _robust_z_fp(_aniso_strike_ridge_fp(vdike_2d, ys, xs, sy_fp, sx_fp, hp_weight=0.80))
    del tmi150, tmi150_mag_fp, v_loc, vdike_2d
    gc.collect()

    # ------------------------------------------------------------------
    # Step 3: 2-m Probe Conductive dT/dz & 1D Advective Peclet Concavity (1,570 3-depth probes)
    # ------------------------------------------------------------------
    with zipfile.ZipFile(ext / "2m_temperature_probe_INGENIOUS_regional_data.zip") as zf:
        dbf_bytes = zf.read(
            "2m_temperature_probe_INGENIOUS_regional_data/2m_temperature_probe_n83geo/2m_temperature_probe_n83geo.dbf"
        )
    probe_rows = physics._read_dbf_records(dbf_bytes)
    del dbf_bytes

    def _fnum(v: object) -> float:
        if v is None:
            return float("nan")
        s = str(v).strip()
        if not s or s.lower() == "nan":
            return float("nan")
        try:
            return float(s)
        except ValueError:
            return float("nan")

    area_g: dict[str, list[float]] = defaultdict(list)
    area_p: dict[str, list[float]] = defaultdict(list)
    p_recs: list[tuple[float, float, str, float, float]] = []
    n_peclet_stations = 0
    for r in probe_rows:
        lon, lat = _fnum(r.get("LongDegree")), _fnum(r.get("LatDegreeN"))
        if not (math.isfinite(lon) and math.isfinite(lat) and -125.0 < lon < -110.0 and 34.0 < lat < 44.0):
            continue
        area = (r.get("Area") or "UNK").strip() or "UNK"
        t1, t15, t2 = _fnum(r.get("T1m")), _fnum(r.get("T15m")), _fnum(r.get("T2m"))
        gv = float("nan")
        pv = float("nan")
        if math.isfinite(t2) and t2 > 0.5 and math.isfinite(t1) and t1 > 0.5:
            gv = float(np.clip(t2 - t1, -10.0, 20.0))
            area_g[area].append(gv)
            if math.isfinite(t15) and t15 > 0.5:
                pv = float(np.clip(4.0 * (2.0 * t15 - t2 - t1), -12.0, 16.0))
                area_p[area].append(pv)
                n_peclet_stations += 1
        elif math.isfinite(t2) and t2 > 0.5 and math.isfinite(t15) and t15 > 0.5:
            gv = float(np.clip(2.0 * (t2 - t15), -10.0, 20.0))
            area_g[area].append(gv)
        p_recs.append((lon, lat, area, gv, pv))

    med_g = {a: float(np.median(vs)) for a, vs in area_g.items() if vs}
    med_p = {a: float(np.median(vs)) for a, vs in area_p.items() if vs}

    glon, glat, gwt = [], [], []
    plon, plat, pwt = [], [], []
    for lon, lat, area, gv, pv in p_recs:
        if math.isfinite(gv):
            ex_g = max(gv - med_g.get(area, 0.0), 0.0)
            glon.append(lon)
            glat.append(lat)
            gwt.append(ex_g)
            if math.isfinite(pv):
                ex_p = max(pv - med_p.get(area, 0.0), 0.0) * (0.4 + 0.6 * math.tanh(max(ex_g, 0.0)))
                plon.append(lon)
                plat.append(lat)
                pwt.append(ex_p)

    gx_u, gy_u = crs_transform("EPSG:4269", grid.crs, glon, glat)
    gc_a, gr_a = inv_tf * (np.asarray(gx_u), np.asarray(gy_u))
    gw_a = np.asarray(gwt, dtype=np.float32)
    g_s1 = np.log1p(physics._splat_points(shape, np.floor(gr_a), np.floor(gc_a), gw_a, 4.5, True))
    g_s2 = np.log1p(physics._splat_points(shape, np.floor(gr_a), np.floor(gc_a), gw_a, 12.0, True))
    mm[:, 8] = _robust_z_fp((0.65 * g_s1 + 0.35 * g_s2)[ys, xs])
    del g_s1, g_s2

    px_u, py_u = crs_transform("EPSG:4269", grid.crs, plon, plat)
    pc_a, pr_a = inv_tf * (np.asarray(px_u), np.asarray(py_u))
    pw_a = np.asarray(pwt, dtype=np.float32)
    p_s1 = np.log1p(physics._splat_points(shape, np.floor(pr_a), np.floor(pc_a), pw_a, 4.5, True))
    p_s2 = np.log1p(physics._splat_points(shape, np.floor(pr_a), np.floor(pc_a), pw_a, 12.0, True))
    mm[:, 9] = _robust_z_fp((0.65 * p_s1 + 0.35 * p_s2)[ys, xs])
    del p_s1, p_s2, probe_rows, p_recs
    gc.collect()

    # ------------------------------------------------------------------
    # Step 4: Cross-Modal 1 m LiDAR B11 Subsurface Strike Lock & 10 m 3DEP Branch Piracy
    # ------------------------------------------------------------------
    with rasterio.open(ext / "lidar_scarp_features_u8.tif") as ds_lid:
        lid_ex = ds_lid.read(3).astype(np.float32) / 255.0
        lid_rdg = ds_lid.read(6).astype(np.float32) / 255.0
        lid_aniso = ds_lid.read(10).astype(np.float32) / 255.0
        lid_str_u8 = ds_lid.read(11)
        lid_val = (ds_lid.read(12) > 0) & (lid_str_u8 > 0) & fp

    scarp_amp_fp = ((0.40 * lid_ex[ys, xs] + 0.35 * lid_rdg[ys, xs] + 0.25 * lid_aniso[ys, xs]) * lid_val[ys, xs]).astype(
        np.float32
    )
    theta_lid_fp = ((lid_str_u8[ys, xs].astype(np.float32) - 1.0) / 254.0 * np.float32(math.pi)).astype(np.float32)
    cos2_lock = (np.cos(theta_lid_fp - theta_sub_fp) ** 2).astype(np.float32)
    sin2_orth = np.float32(1.0) - cos2_lock
    del lid_ex, lid_rdg, lid_aniso, lid_str_u8, lid_val, theta_lid_fp, theta_sub_fp

    lock_2d = np.zeros(shape, dtype=np.float32)
    lock_2d[ys, xs] = scarp_amp_fp * cos2_lock * np.log1p(b18_fp * 25.0 + bmag_fp * 0.1)
    mm[:, 15] = _robust_z_fp(_aniso_strike_ridge_fp(lock_2d, ys, xs, sy_fp, sx_fp, L_par_1=2.5, L_par_2=5.0, L_perp=3.0))
    del lock_2d

    orth_2d = np.zeros(shape, dtype=np.float32)
    orth_2d[ys, xs] = scarp_amp_fp * sin2_orth * np.log1p(gmag4_fp * 40.0 + bmag_fp * 0.15)
    mm[:, 16] = _robust_z_fp(orth_2d[ys, xs])
    del orth_2d, scarp_amp_fp, cos2_lock, sin2_orth, b18_fp, bmag_fp, gmag4_fp

    with rasterio.open(ext / "dem10_chi_100m_u8.tif") as ds_cu8:
        raised_n = np.log1p(ds_cu8.read(3).astype(np.float32))
    mm[:, 18] = _robust_z_fp(_aniso_strike_ridge_fp(raised_n, ys, xs, sy_fp, sx_fp) * (0.20 + 0.80 * non_playa_fp))
    del raised_n, non_playa_fp

    with rasterio.open(ext / "dem10_chi_100m_sig_i32.tif") as ds_sig:
        sig_i32 = ds_sig.read(1)
    chan_mask = (sig_i32 != -1) & fp
    sig_max = ndi.maximum_filter(np.where(chan_mask, sig_i32, -2_000_000_000), size=5)
    sig_min = ndi.minimum_filter(np.where(chan_mask, sig_i32, 2_000_000_000), size=5)
    branch_jump = ((sig_max > sig_min) & (sig_max >= 0) & (sig_min < 2_000_000_000)).astype(np.float32)
    del sig_i32, chan_mask, sig_max, sig_min
    piracy_2d = ndi.gaussian_filter(branch_jump * np.log1p(np.abs(chi_step_m)), sigma=2.5, mode="nearest")
    mm[:, 19] = _robust_z_fp(_aniso_strike_ridge_fp(piracy_2d, ys, xs, sy_fp, sx_fp))
    del branch_jump, chi_step_m, piracy_2d, sy_fp, sx_fp
    gc.collect()

    hydro_ev = 0.30 * mm[:, 0] + 0.24 * mm[:, 1] + 0.14 * mm[:, 2] + 0.16 * mm[:, 4] + 0.16 * mm[:, 9]
    struct_ev = (
        0.22 * mm[:, 10]
        + 0.18 * mm[:, 12]
        + 0.16 * mm[:, 13]
        + 0.20 * mm[:, 15]
        + 0.12 * mm[:, 17]
        + 0.12 * mm[:, 20]
    )
    mimic_pen = 0.30 * np.maximum(mm[:, 22], 0.0) + 0.25 * np.maximum(mm[:, 23], 0.0)
    mm[:, 21] = _robust_z_fp(0.42 * hydro_ev + 0.58 * struct_ev - mimic_pen)
    del hydro_ev, struct_ev, mimic_pen

    mm.flush()
    arr_chk = np.asarray(mm)
    if not np.isfinite(arr_chk).all():
        raise AssertionError("Non-finite values detected in VCAZ-24 feature memmap")

    meta_out = {
        "schema_version": VCAZ_SCHEMA_VERSION,
        "shape": [n_fp, n_cols],
        "features": list(VCAZ_FEATURES),
        "input_hashes": input_hashes,
        "catalogue_files_accessed": [],
        "dist_known_fault_px_dropped_and_verified": bool(dropped_dist_col_verified),
        "paleo_facies_in_footprint_counts": dict(facies_counts),
        "probe_3depth_peclet_stations": int(n_peclet_stations),
    }
    meta_path.write_text(json.dumps(meta_out, indent=2) + "\n", encoding="utf-8")
    _evict_mmap(mm)
    del mm, arr_chk
    gc.collect()
    return np.memmap(dat_path, dtype="float32", mode="r", shape=(n_fp, n_cols)), meta_out


def fit_ht_lgbm_dual_head(
    sources: list[np.ndarray],
    domain_fp: np.ndarray,
    pos_grid: np.ndarray,
    fp_mask: np.ndarray,
    zbase_fp: np.ndarray,
    seed: int,
    max_zero_neg: int = 140_000,
) -> tuple[lgb.LGBMClassifier, lgb.LGBMRegressor]:
    """Fit early-stopped Horvitz-Thompson cover-propensity-weighted LightGBM dual head on ``domain_fp``."""
    ys_fp, xs_fp = np.nonzero(fp_mask)
    y_cell_all = pos_grid[ys_fp, xs_fp].astype(np.int8)
    y_kern_grid = np.clip(1.0 - ndi.distance_transform_edt(~pos_grid) / 3.0, 0.0, 1.0).astype(np.float32)
    y_kern_all = y_kern_grid[ys_fp, xs_fp]
    del y_kern_grid

    dom_idx = np.flatnonzero(domain_fp)
    yk_dom = y_kern_all[dom_idx]
    near_sel = yk_dom > 0.0
    near_idx = dom_idx[near_sel]
    zero_idx = dom_idx[~near_sel]

    rng = np.random.default_rng(seed)
    if zero_idx.size > max_zero_neg:
        sub_zero = np.sort(rng.choice(zero_idx, size=max_zero_neg, replace=False))
        w_zero = float(zero_idx.size) / float(max_zero_neg)
    else:
        sub_zero = zero_idx
        w_zero = 1.0

    zb_near = np.maximum(zbase_fp[near_idx], 0.0)
    ht_pos_w = np.clip(1.0 + 0.28 * np.tanh(zb_near / 350.0), 1.0, 1.28).astype(np.float64)
    ht_pos_w *= float(near_idx.size) / max(float(ht_pos_w.sum()), 1e-6)

    train_idx = np.concatenate([near_idx, sub_zero])
    weights = np.concatenate([ht_pos_w, np.full(sub_zero.size, w_zero, dtype=np.float64)])
    seq = np.argsort(train_idx)
    train_idx = train_idx[seq]
    weights = weights[seq]
    X_all = adhr.gather_columns(sources, train_idx)
    for src in sources:
        _evict_mmap(src)
    yc_all = y_cell_all[train_idx]
    yk_all = y_kern_all[train_idx]

    perm = rng.permutation(len(train_idx))
    X_all = X_all[perm]
    yc_all = yc_all[perm]
    yk_all = yk_all[perm]
    weights = weights[perm]

    n_val = max(int(0.10 * len(train_idx)), 2_000)
    X_val, yc_val, yk_val, w_val = X_all[:n_val], yc_all[:n_val], yk_all[:n_val], weights[:n_val]
    X_tr, yc_tr, yk_tr, w_tr = X_all[n_val:], yc_all[n_val:], yk_all[n_val:], weights[n_val:]

    clf = lgb.LGBMClassifier(
        n_estimators=180,
        learning_rate=0.065,
        num_leaves=47,
        min_child_samples=95,
        subsample=0.82,
        subsample_freq=1,
        colsample_bytree=0.75,
        reg_alpha=1.0,
        reg_lambda=5.0,
        random_state=seed,
        n_jobs=2,
        verbose=-1,
    )
    clf.fit(
        X_tr,
        yc_tr,
        sample_weight=w_tr,
        eval_set=[(X_val, yc_val)],
        eval_sample_weight=[w_val],
        callbacks=[lgb.early_stopping(14, verbose=False)],
    )

    reg = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=180,
        learning_rate=0.065,
        num_leaves=47,
        min_child_samples=95,
        subsample=0.82,
        subsample_freq=1,
        colsample_bytree=0.75,
        reg_alpha=1.0,
        reg_lambda=5.0,
        random_state=seed + 7,
        n_jobs=2,
        verbose=-1,
    )
    reg.fit(
        X_tr,
        yk_tr,
        sample_weight=w_tr,
        eval_set=[(X_val, yk_val)],
        eval_sample_weight=[w_val],
        callbacks=[lgb.early_stopping(14, verbose=False)],
    )
    del X_all, X_tr, X_val, yc_all, yk_all, weights
    gc.collect()
    return clf, reg


def predict_lgbm_dual_chunked(
    clf: lgb.LGBMClassifier,
    reg: lgb.LGBMRegressor,
    sources: list[np.ndarray],
    idx: np.ndarray,
    chunk_rows: int = 160_000,
) -> tuple[np.ndarray, np.ndarray]:
    n = int(idx.size)
    p_out = np.zeros(n, dtype=np.float32)
    m_out = np.zeros(n, dtype=np.float32)
    for s in range(0, n, chunk_rows):
        sl = slice(s, min(s + chunk_rows, n))
        Xc = adhr.gather_columns(sources, idx[sl])
        p_c = np.clip(clf.predict_proba(Xc)[:, 1], 1e-6, 1.0 - 1e-6).astype(np.float32)
        m_c = np.clip(reg.predict(Xc), p_c, 1.0).astype(np.float32)
        p_out[sl] = p_c
        m_out[sl] = m_c
    for src in sources:
        _evict_mmap(src)
    return p_out, m_out


def _cross_family_blend(
    p_hgb: np.ndarray,
    m_hgb: np.ndarray,
    p_lgb: np.ndarray,
    m_lgb: np.ndarray,
    w_lgb: float = 0.42,
) -> tuple[np.ndarray, np.ndarray]:
    """Calibrated log-odds blend of HistGradientBoosting + Horvitz-Thompson LightGBM."""
    w1 = np.float32(1.0 - w_lgb)
    w2 = np.float32(w_lgb)
    p = adhr._expit(w1 * adhr._logit(p_hgb) + w2 * adhr._logit(p_lgb)).astype(np.float32)
    m = np.maximum(adhr._expit(w1 * adhr._logit(m_hgb) + w2 * adhr._logit(m_lgb)), p).astype(np.float32)
    return p, m


def _poe_pool_vcaz(
    p_base: np.ndarray,
    m_base: np.ndarray,
    p_vcaz: np.ndarray,
    m_vcaz: np.ndarray,
    d_vis_act: np.ndarray,
    w_near: float = 0.70,
    w_far_boost: float = 0.18,
) -> tuple[np.ndarray, np.ndarray]:
    """Distance-adaptive calibrated Log-Odds Product-of-Experts pooling.

    Stays strictly in log-odds space so ``adhr._fuse_log_odds`` performs the single
    completeness marginalization without inflating background floor probabilities.
    """
    far_gate = 1.0 / (1.0 + np.exp(-np.clip((d_vis_act - 20.0) / 5.0, -15.0, 15.0)))
    w_v = np.clip(np.float32(w_near) + np.float32(w_far_boost) * far_gate.astype(np.float32), 0.0, 0.92)
    w_b = np.float32(1.0) - w_v
    lp = w_b * adhr._logit(p_base) + w_v * adhr._logit(p_vcaz)
    lm = w_b * adhr._logit(m_base) + w_v * adhr._logit(m_vcaz)
    p_poe = adhr._expit(lp)
    m_poe = np.maximum(adhr._expit(lm), p_poe).astype(np.float32)
    return p_poe, m_poe


def allocate_3regime_vcaz(
    p_fused: np.ndarray,
    m_fused: np.ndarray,
    p_zerocat: np.ndarray,
    m_zerocat: np.ndarray,
    d_ref_act: np.ndarray,
    ay: np.ndarray,
    ax: np.ndarray,
    grid_shape: tuple[int, int],
    *,
    budgets: tuple[int, int, int] = (10_956, 8_632, 13_612),
    spacings: tuple[float, float, float] = (3.10, 3.15, 3.15),
    collar_px: float = 2.5,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """3-Regime geothermal-conduit Dinkelbach allocation:
      Regime 1: Near-Relay          (collar_px < d <= 11 px)
      Regime 2: Piedmont-Hinge      (11 < d <= 25 px)
      Regime 3: Blind-Basin-Conduit (d > 25 px)
    """
    b_near, b_pied, b_blind = budgets
    s_near, s_pied, s_blind = spacings
    tot_budget = float(b_near + b_pied + b_blind)
    k_tot = tot_budget * 0.48

    sel_r1 = (d_ref_act > collar_px) & (d_ref_act <= 11.0)
    sel_r2 = (d_ref_act > 11.0) & (d_ref_act <= 25.0)
    sel_r3 = d_ref_act > 25.0

    p_surf_act = np.zeros_like(p_fused, dtype=np.float32)
    m_surf_act = np.zeros_like(m_fused, dtype=np.float32)

    specs = (
        ("near_relay", sel_r1, b_near, s_near, 0.62),
        ("piedmont_hinge", sel_r2, b_pied, s_pied, 0.42),
        ("blind_conduit", sel_r3, b_blind, s_blind, 0.14),
    )

    emitted_total = np.zeros(grid_shape, dtype=np.float32)
    regime_counts: dict[str, int] = {}

    for rname, sel, b_reg, s_reg, w_joint in specs:
        if not np.any(sel) or b_reg <= 0:
            regime_counts[rname] = 0
            continue
        wj = np.float32(w_joint)
        wz = np.float32(1.0 - w_joint)
        pr = wj * p_fused[sel] + wz * p_zerocat[sel]
        mr = wj * m_fused[sel] + wz * m_zerocat[sel]
        k_reg = k_tot * (float(b_reg) / max(tot_budget, 1.0))
        sc = float(k_reg) / max(float(pr.sum()), 1e-6)
        pr_cal = np.clip(pr * np.float32(sc), 0.0, 1.0).astype(np.float32)
        mr_cal = np.clip(mr * np.float32(min(max(sc, 0.85), 1.25)), pr_cal, 1.0).astype(np.float32)

        p_surf_act[sel] = pr_cal
        m_surf_act[sel] = mr_cal

        pg = adhr.scatter_fp(pr_cal, ay[sel], ax[sel], grid_shape)
        mg = adhr.scatter_fp(mr_cal, ay[sel], ax[sel], grid_shape)
        allow_reg = np.zeros(grid_shape, dtype=bool)
        allow_reg[ay[sel], ax[sel]] = True
        alloc = emit.dinkelbach_allocate(
            pg,
            mg,
            allow_reg,
            budget=int(b_reg),
            k_truth=max(k_reg * 0.55, 25.0),
            min_spacing_px=float(s_reg),
            dinkelbach_iters=6,
        )
        emitted_total = np.maximum(emitted_total, alloc.emitted.astype(np.float32))
        regime_counts[rname] = int(alloc.n_dots)

    surf_grid = adhr.scatter_fp(p_surf_act, ay, ax, grid_shape)
    return emitted_total, surf_grid, {"n_dots": int((emitted_total > 0.5).sum()), "regime_counts": regime_counts}


def verify_zero_test_quadrant_leakage(
    grid,
    X_phys_deconf: ColumnSubsetView,
    X_vcaz_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    zbase_fp: np.ndarray,
) -> bool:
    """Prove bit-exact invariance of fitted VCAZ models to arbitrary test-quadrant truth."""
    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    act_idx = np.flatnonzero((fp & test_region & ~visible)[ys_fp, xs_fp])[:8_192]
    dom_s = (train_regions & ~visible)[ys_fp, xs_fp]

    outs = []
    for corrupt in (False, True):
        tt = train_truth.copy()
        if corrupt:
            tt = tt | (test_region & fp)
        tr_safe = tt & train_regions
        wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, tr_safe[ys_fp, xs_fp], quantile=0.90, l0_px=40.0)
        dow = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)
        clf, reg = fit_ht_lgbm_dual_head(
            [X_phys_deconf, X_vcaz_mm, X_vis22_mm, dow],
            dom_s,
            tr_safe,
            fp,
            zbase_fp,
            seed=20261025,
            max_zero_neg=25_000,
        )
        outs.append(predict_lgbm_dual_chunked(clf, reg, [X_phys_deconf, X_vcaz_mm, X_vis22_mm, dow], act_idx))
    return bool(np.array_equal(outs[0][0], outs[1][0]) and np.array_equal(outs[0][1], outs[1][1]))


def predict_vcaz_fold(
    grid,
    X_phys_mm: np.ndarray,
    X_phys_deconf: ColumnSubsetView,
    X_vcaz_mm: np.ndarray,
    X_vis22_mm: np.ndarray,
    d_vis_fp: np.ndarray,
    comp_len_fp: np.ndarray,
    visible: np.ndarray,
    train_regions: np.ndarray,
    train_truth: np.ndarray,
    test_region: np.ndarray,
    zbase_fp: np.ndarray,
    seed: int,
    cache_dir: Path,
    fold_tag: str,
    *,
    prod_struct_pack: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None,
) -> tuple[dict[str, tuple[np.ndarray, np.ndarray, dict]], dict[str, np.ndarray] | None]:
    """Fit/load per-fold cross-family posteriors (< 1.1 GB RSS), score 4 arms, and emit OOF struct slice."""
    if np.any(train_regions & test_region) or np.any(train_truth & test_region):
        raise AssertionError("Leakage check failed: training regions/truth intersect test_region")

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    allowed = fp & test_region & ~visible
    act_idx = np.flatnonzero(allowed[ys_fp, xs_fp])
    d_vis_act = d_vis_fp[act_idx]

    post_path = Path(cache_dir) / f"vcaz_fold_post_{fold_tag}_{VCAZ_SCHEMA_VERSION}.npz"
    prod_slice_path = Path(cache_dir) / f"vcaz_prod_struct_{fold_tag}_{VCAZ_SCHEMA_VERSION}.npz"
    prod_slice_out: dict[str, np.ndarray] | None = None

    need_fit = not post_path.is_file() or (prod_struct_pack is not None and not prod_slice_path.is_file())
    if not need_fit:
        z = np.load(post_path, allow_pickle=False)
        p_phys_44, m_phys_44 = z["p_phys_44"], z["m_phys_44"]
        p_full_67, m_full_67 = z["p_full_67"], z["m_full_67"]
        p_vcaz_zc, m_vcaz_zc = z["p_vcaz_zc"], z["m_vcaz_zc"]
        p_vcaz_full, m_vcaz_full = z["p_vcaz_full"], z["m_vcaz_full"]
        if prod_struct_pack is not None:
            zp = np.load(prod_slice_path, allow_pickle=False)
            prod_slice_out = {k: zp[k] for k in zp.files}
    else:
        tr_safe = train_truth & train_regions
        vis_tr_safe = visible & train_regions
        wlaw = damagezone_envelope.fit_width_law(
            comp_len_fp, d_vis_fp, tr_safe[ys_fp, xs_fp], quantile=0.90, l0_px=40.0
        )
        d_over_w_fp = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)

        dom_phys_tr = train_regions[ys_fp, xs_fp]
        dom_struct_tr = (train_regions & ~visible)[ys_fp, xs_fp]

        # 1. Baseline H88-ADHR control heads (exact B12 det_elev ADHR reproduction)
        c_p44, r_p44 = adhr._fit_dual_expectation_models(
            [X_phys_mm], dom_phys_tr, vis_tr_safe, fp, seed=seed + 17, n_ensemble=1
        )
        p_phys_44, m_phys_44 = adhr._predict_dual_chunked(c_p44, r_p44, [X_phys_mm], act_idx)
        del c_p44, r_p44
        _evict_mmap(X_phys_mm)

        c_f67, r_f67 = adhr._fit_dual_expectation_models(
            [X_phys_mm, X_vis22_mm, d_over_w_fp], dom_struct_tr, tr_safe, fp, seed=seed + 53, n_ensemble=1
        )
        p_full_67, m_full_67 = adhr._predict_dual_chunked(
            c_f67, r_f67, [X_phys_mm, X_vis22_mm, d_over_w_fp], act_idx
        )
        del c_f67, r_f67
        _evict_mmap(X_phys_mm)
        _evict_mmap(X_vis22_mm)

        # 2. VCAZ Zero-Catalogue Cross-Family Specialist (36 deconfounded phys + 24 VCAZ = 60 ch)
        zc_sources = [X_phys_deconf, X_vcaz_mm]
        c_zc_hgb, r_zc_hgb = adhr._fit_dual_expectation_models(
            zc_sources, dom_phys_tr, vis_tr_safe, fp, seed=seed + 117, n_ensemble=1
        )
        p_zc_hgb, m_zc_hgb = adhr._predict_dual_chunked(c_zc_hgb, r_zc_hgb, zc_sources, act_idx)
        del c_zc_hgb, r_zc_hgb

        c_zc_lgb, r_zc_lgb = fit_ht_lgbm_dual_head(
            zc_sources, dom_phys_tr, vis_tr_safe, fp, zbase_fp, seed=seed + 217
        )
        p_zc_lgb, m_zc_lgb = predict_lgbm_dual_chunked(c_zc_lgb, r_zc_lgb, zc_sources, act_idx)
        del c_zc_lgb, r_zc_lgb
        p_vcaz_zc, m_vcaz_zc = _cross_family_blend(p_zc_hgb, m_zc_hgb, p_zc_lgb, m_zc_lgb, w_lgb=0.45)

        # 3. VCAZ Joint Hydrothermal + Structural Cross-Family Specialist (44 phys + 24 vcaz + 23 B12 vis_struct = 91 ch)
        full_sources = [X_phys_mm, X_vcaz_mm, X_vis22_mm, d_over_w_fp]
        c_vf_hgb, r_vf_hgb = adhr._fit_dual_expectation_models(
            full_sources, dom_struct_tr, tr_safe, fp, seed=seed + 153, n_ensemble=1
        )
        p_vf_hgb, m_vf_hgb = adhr._predict_dual_chunked(c_vf_hgb, r_vf_hgb, full_sources, act_idx)

        c_vf_lgb, r_vf_lgb = fit_ht_lgbm_dual_head(
            full_sources, dom_struct_tr, tr_safe, fp, zbase_fp, seed=seed + 253
        )
        p_vf_lgb, m_vf_lgb = predict_lgbm_dual_chunked(c_vf_lgb, r_vf_lgb, full_sources, act_idx)
        p_vcaz_full, m_vcaz_full = _cross_family_blend(p_vf_hgb, m_vf_hgb, p_vf_lgb, m_vf_lgb, w_lgb=0.42)

        if prod_struct_pack is not None:
            X_vis_prod, dv_prod, cl_prod, prod_sub_idx = prod_struct_pack
            dow_prod = (dv_prod / np.maximum(wlaw.half_width(cl_prod), 1e-6)).astype(np.float32)
            prod_full_srcs = [X_phys_mm, X_vcaz_mm, X_vis_prod, dow_prod]
            pp_vf_hgb, mp_vf_hgb = adhr._predict_dual_chunked(c_vf_hgb, r_vf_hgb, prod_full_srcs, prod_sub_idx)
            pp_vf_lgb, mp_vf_lgb = predict_lgbm_dual_chunked(c_vf_lgb, r_vf_lgb, prod_full_srcs, prod_sub_idx)
            pp_full, mp_full = _cross_family_blend(pp_vf_hgb, mp_vf_hgb, pp_vf_lgb, mp_vf_lgb, w_lgb=0.42)
            _evict_mmap(X_vis_prod)
            prod_slice_out = {"pp_full": pp_full, "mp_full": mp_full}
            np.savez_compressed(prod_slice_path, **prod_slice_out)
            del dow_prod

        del c_vf_hgb, r_vf_hgb, c_vf_lgb, r_vf_lgb, d_over_w_fp
        _evict_mmap(X_phys_mm)
        _evict_mmap(X_vcaz_mm)
        _evict_mmap(X_vis22_mm)
        gc.collect()

        np.savez_compressed(
            post_path,
            p_phys_44=p_phys_44,
            m_phys_44=m_phys_44,
            p_full_67=p_full_67,
            m_full_67=m_full_67,
            p_vcaz_zc=p_vcaz_zc,
            m_vcaz_zc=m_vcaz_zc,
            p_vcaz_full=p_vcaz_full,
            m_vcaz_full=m_vcaz_full,
        )

    n_vis_tr = max(float((visible & train_regions).sum()), 1.0)
    hid_ratio = float((train_truth & train_regions).sum()) / n_vis_tr
    k_est = max(float((visible & test_region).sum()) * hid_ratio, 50.0)
    ay, ax = ys_fp[act_idx], xs_fp[act_idx]

    def _emit_unconstr(p_vec: np.ndarray, m_vec: np.ndarray, spacing: float = 2.05) -> tuple[np.ndarray, np.ndarray, dict]:
        pg = adhr.scatter_fp(p_vec, ay, ax, grid.shape)
        mg = adhr.scatter_fp(m_vec, ay, ax, grid.shape)
        alloc = emit.dinkelbach_allocate(
            pg, mg, allowed, budget=None, k_truth=k_est, min_spacing_px=spacing, dinkelbach_iters=6
        )
        return (
            alloc.emitted.astype(np.float32),
            pg,
            {"n_dots": int(alloc.n_dots), "k_truth_est": float(k_est), "surrogate_dti": float(alloc.surrogate_dti)},
        )

    # Control: h88_adhr_control
    p_ctrl, m_ctrl = adhr._fuse_log_odds(p_full_67, m_full_67, p_phys_44, m_phys_44, k_est, beta_phys=0.35)

    # Exp 01: exp01_vcaz_zerocat (pure zero-catalogue cross-family hydrothermal-conduit specialist)
    sc_e1 = float(k_est) / max(float(p_vcaz_zc.sum()), 1e-6)
    p_e1 = np.clip(p_vcaz_zc * np.float32(sc_e1), 0.0, 1.0).astype(np.float32)
    m_e1 = np.clip(m_vcaz_zc * np.float32(hid_ratio), p_e1, 1.0).astype(np.float32)

    # Exp 02: exp02_vcaz_crossfam_poe (distance-adaptive Cross-Family Log-Odds PoE + completeness fusion)
    p_phys_poe, m_phys_poe = _poe_pool_vcaz(p_phys_44, m_phys_44, p_vcaz_zc, m_vcaz_zc, d_vis_act)
    p_full_poe, m_full_poe = _poe_pool_vcaz(p_full_67, m_full_67, p_vcaz_full, m_vcaz_full, d_vis_act)
    p_e2, m_e2 = adhr._fuse_log_odds(p_full_poe, m_full_poe, p_phys_poe, m_phys_poe, k_est, beta_phys=0.38)

    # Exp 03: exp03_vcaz_3regime_prod (3-Regime production rule evaluated on fold quadrant scaled by quadrant area)
    q_frac = float(act_idx.size) / max(float((fp & ~visible).sum()), 1.0)
    fold_budgets = (
        max(int(round(10_956 * q_frac)), 100),
        max(int(round(8_632 * q_frac)), 100),
        max(int(round(13_612 * q_frac)), 100),
    )
    em_e3, pg_e3, meta_e3 = allocate_3regime_vcaz(
        p_e2,
        m_e2,
        p_e1,
        m_e1,
        d_vis_act,
        ay,
        ax,
        grid.shape,
        budgets=fold_budgets,
        spacings=(3.10, 3.15, 3.15),
        collar_px=2.5,
    )

    arms_out = {
        "h88_adhr_control": _emit_unconstr(p_ctrl, m_ctrl, spacing=2.05),
        "exp01_vcaz_zerocat": _emit_unconstr(p_e1, m_e1, spacing=2.05),
        "exp02_vcaz_crossfam_poe": _emit_unconstr(p_e2, m_e2, spacing=2.05),
        "exp03_vcaz_3regime_prod": (em_e3, pg_e3, meta_e3),
    }
    return arms_out, prod_slice_out


def fit_oof_zerocat_production(
    grid,
    X_phys_deconf: ColumnSubsetView,
    X_vcaz_mm: np.ndarray,
    folds_q4: list[dict],
    zbase_fp: np.ndarray,
    prod_act_idx: np.ndarray,
    prod_quad_act: np.ndarray,
    cache_dir: Path,
) -> tuple[np.ndarray, np.ndarray]:
    """4-Quadrant strictly out-of-quadrant cross-fit for production zero-catalogue head."""
    ck = Path(cache_dir) / f"vcaz_prod_zc_oof_{VCAZ_SCHEMA_VERSION}.npz"
    if ck.is_file():
        z = np.load(ck, allow_pickle=False)
        return z["p_zc_oof"], z["m_zc_oof"]

    fp = grid.footprint
    ys_fp, xs_fp = np.nonzero(fp)
    full_cat = np.asarray(grid.catalogue, dtype=bool)
    quad_grid = np.zeros(grid.shape, dtype=np.int8)
    quad_grid.fill(-1)
    yy, xx = ys_fp, xs_fp
    ym, xm = int(np.median(yy)), int(np.median(xx))
    gy, gx = np.ogrid[: fp.shape[0], : fp.shape[1]]
    quad_grid[(gy < ym) & (gx < xm) & fp] = 0
    quad_grid[(gy < ym) & (gx >= xm) & fp] = 1
    quad_grid[(gy >= ym) & (gx < xm) & fp] = 2
    quad_grid[(gy >= ym) & (gx >= xm) & fp] = 3

    p_zc_oof = np.zeros(prod_act_idx.size, dtype=np.float32)
    m_zc_oof = np.zeros(prod_act_idx.size, dtype=np.float32)
    zc_sources = [X_phys_deconf, X_vcaz_mm]

    for q_idx in range(4):
        tr_grid = fp & (quad_grid != q_idx) & (~folds_q4[q_idx]["region"])
        tr_dom_fp = tr_grid[ys_fp, xs_fp]
        pos_q = full_cat & tr_grid
        q_sel = prod_quad_act == q_idx
        sub_idx = prod_act_idx[q_sel]

        c_h, r_h = adhr._fit_dual_expectation_models(
            zc_sources, tr_dom_fp, pos_q, fp, seed=88910 + q_idx, n_ensemble=1
        )
        ph, mh = adhr._predict_dual_chunked(c_h, r_h, zc_sources, sub_idx)
        del c_h, r_h

        c_l, r_l = fit_ht_lgbm_dual_head(
            zc_sources, tr_dom_fp, pos_q, fp, zbase_fp, seed=88950 + q_idx
        )
        pl, ml = predict_lgbm_dual_chunked(c_l, r_l, zc_sources, sub_idx)
        del c_l, r_l
        p_q, m_q = _cross_family_blend(ph, mh, pl, ml, w_lgb=0.45)
        p_zc_oof[q_sel] = p_q
        m_zc_oof[q_sel] = m_q
        gc.collect()

    np.savez_compressed(ck, p_zc_oof=p_zc_oof, m_zc_oof=m_zc_oof)
    return p_zc_oof, m_zc_oof
