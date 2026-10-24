"""KDMC-88 — Kernel-Disjoint Maximal-Coverage packing for the DOE GEMS DTI.

Lane statement (one method paragraph, parallel-run protocol rule 1)
-------------------------------------------------------------------
Treat the competition's Distance-weighted Tversky Index as the fractional
program it is.  With ``alpha = 0.2``, ``beta = 0.8`` and the 300 m triangular
kernel on a 100 m grid, adding one binary dot ``x`` to a dot field changes

    DTI = TP_w / (TP_w + alpha*FP_w + beta*|G|-TP_w ... )

so that the dot is worth emitting **iff** its marginal truth credit clears

    dT  >  alpha*DTI*(1 - k_self) / (1 - alpha*DTI)                     (1)

(derived and unit-tested in :mod:`gems57.metric`; at ``DTI = 0.2778`` and
``k_self = 0`` the bar is ``0.058829`` truth-pixel-equivalents).  An *isolated*
dot in a region whose off-catalogue fault density equals the footprint mean
earns ``sum_offsets k = 9.380298`` times that density, i.e. ``0.110711`` — a
factor ``1.88`` above the bar.  Two consequences follow, and they are the whole
lane:

1. **Kernel overlap is the dominant waste.**  Two dots closer than ``2R = 6 px``
   share kernel mass; the shared part is paid for twice in ``FP_w`` and credited
   once in ``TP_w``.  Measured packing efficiency (realised credit mass divided
   by ``n * 9.380298``) of the registry's own high scorers runs 0.41 (121 k dots)
   to 0.89 — none of them is kernel-disjoint.
2. **The field is budget-starved, not budget-limited.**  Every cell whose
   predicted density exceeds ``0.53x`` the footprint mean clears (1).  The
   registry's best raster addresses 13.7 % of the footprint.

KDMC therefore (a) estimates a *zero-catalogue* off-catalogue fault density
``rho(x)`` by PU learning with spatially-blocked leave-one-quadrant-out
cross-fitting, (b) convolves it with the official kernel to get the exact
expected credit ``E(x)`` of an isolated dot, and (c) allocates binary dots by
greedy maximum-weight packing under a hard minimum separation ``s``, stopping at
the Dinkelbach fixed point of (1) rather than at a hand-chosen ``N``.

Named non-fault process that could mimic the signature
------------------------------------------------------
Pleistocene Lake Lahontan wave-cut shoreline benches (highstand ~1,330 m) and
alluvial-fan risers produce laterally continuous, range-parallel topographic
breaks with scarp-like slope/curvature signatures that are not faults; GeoDAWN
flight-line levelling seams produce the same in the magnetic bands.  Both are
carried as explicit features so the model can price them, and both are reported
in the run card.

Nothing in this module reads ``existing_faults.tif`` to build a feature.  The
catalogue is used only as PU *labels* and as the allocation exclusion mask, so
the hide-and-recover holdout's "derive every catalogue-based feature only from
the visible faults" requirement is satisfied vacuously and cannot leak.
"""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import (
    binary_dilation,
    distance_transform_edt,
    gaussian_filter,
    maximum_filter,
    uniform_filter,
)

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
FEATURE_VERSION = "kdmc88-zero-catalogue-v1"


# --------------------------------------------------------------------------
# marginal-bar algebra (exact, no approximation)
# --------------------------------------------------------------------------
def marginal_bar(dti: float, k_self: float = 0.0, alpha: float = ALPHA) -> float:
    """Minimum marginal truth credit for one more dot to raise the DTI.

    Derivation (identical algebra to :func:`gems57.metric.marginal_accept`):
    with ``D`` the current denominator, adding a dot gives
    ``dD = alpha*(dT + 1 - k_self)``, so ``dDTI > 0`` iff
    ``dT*(1 - alpha*DTI) > alpha*DTI*(1 - k_self)``.
    """
    lam = alpha * float(dti)
    if lam >= 1.0:
        raise ValueError("alpha*DTI must be < 1")
    return lam * (1.0 - float(k_self)) / (1.0 - lam)


def dti_from(tp: float, n_dots: float, m_self: float, k_truth: float,
             alpha: float = ALPHA, beta: float = BETA) -> float:
    """DTI of a binary field from (TP_w, n, M, |G|)."""
    fp = float(n_dots) - float(m_self)
    fn = float(k_truth) - float(tp)
    return float(tp / (tp + alpha * fp + beta * fn + 1e-12))


def kernel_offsets(radius: float = RADIUS_PX):
    r = int(np.ceil(radius))
    dy, dx, kw = [], [], []
    for j in range(-r, r + 1):
        for i in range(-r, r + 1):
            k = 1.0 - float(np.hypot(j, i)) / radius
            if k > 0.0:
                dy.append(j), dx.append(i), kw.append(k)
    return np.array(dy, np.int64), np.array(dx, np.int64), np.array(kw, np.float64)


#: ``sum_{|d|<R} max(1 - |d|/R, 0)`` over the integer lattice, computed from the
#: same offset rule the shared template uses (``gems57.metric.offsets``) so the
#: two can never drift apart.  Verified equal in ``tests/test_kdmc.py``.
KERNEL_MASS = float(kernel_offsets()[2].sum())


def expected_credit(rho: np.ndarray, radius: float = RADIUS_PX) -> np.ndarray:
    """``E(x) = sum_delta rho(x+delta) * k(|delta|)`` — exact TP_w of an isolated dot."""
    dy, dx, kw = kernel_offsets(radius)
    out = np.zeros(rho.shape, np.float32)
    h, w = rho.shape
    for j, i, k in zip(dy, dx, kw):
        ys0, ys1 = max(0, -j), min(h, h - j)
        xs0, xs1 = max(0, -i), min(w, w - i)
        out[ys0:ys1, xs0:xs1] += np.float32(k) * rho[ys0 + j:ys1 + j, xs0 + i:xs1 + i]
    return out


def self_credit(rho: np.ndarray, radius: float = RADIUS_PX) -> np.ndarray:
    """``E[k_self]`` approximated by the kernel-weighted maximum density nearby.

    ``k_self = max_g k(d(x,g))`` is bounded by 1; we use the expected value of
    the largest kernel weight that a truth pixel in the neighbourhood would
    contribute, which for the sparse densities here is well approximated by
    ``min(1, E(x))``.  It only ever *lowers* the bar, and we clip it so the bar
    is never below the ``k_self = 0`` value times ``1 - min(1, E)``.
    """
    return np.minimum(expected_credit(rho, radius), 1.0)


# --------------------------------------------------------------------------
# allocation: greedy maximum-weight packing under a hard minimum separation
# --------------------------------------------------------------------------
def _conflict_footprint(sep_px: float) -> np.ndarray:
    """Boolean footprint of all offsets strictly closer than ``sep_px``."""
    r = int(np.ceil(sep_px)) + 1
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return np.hypot(yy, xx) < sep_px - 1e-9


def allocate_separated(score: np.ndarray, allowed: np.ndarray, sep_px: float,
                       bar: np.ndarray | float, *, max_rounds: int = 400,
                       max_dots: int | None = None,
                       return_diagnostics: bool = False):
    """Greedy max-weight packing: accept cells in descending ``score`` order,
    skipping any cell within ``sep_px`` of an already-accepted cell, and stopping
    at ``score <= bar``.

    Implemented round-wise: in each round every remaining candidate that is the
    strict maximum of its own conflict disk is accepted.  That set is exactly
    what sequential greedy-by-weight would accept next (a cell that dominates
    its disk is reached by the sequential scan with no accepted neighbour), so
    the result is identical to the sequential algorithm while costing a handful
    of ``maximum_filter`` passes instead of millions of Python iterations.
    Ties inside a disk are broken deterministically by raster index.
    """
    score = np.asarray(score, np.float32)
    allowed = np.asarray(allowed, bool)
    if score.shape != allowed.shape:
        raise ValueError("score/allowed shape mismatch")
    bar_arr = np.asarray(bar, np.float32)
    live = allowed & (score > bar_arr)
    if not live.any():
        empty = np.zeros(score.shape, bool)
        return (empty, 0, True) if return_diagnostics else empty

    foot = _conflict_footprint(sep_px)
    # deterministic tie-break: add a strictly-increasing, negligible index term
    idx = np.arange(score.size, dtype=np.float64).reshape(score.shape)
    span = float(score[live].max()) - float(score[live].min())
    eps = (span if span > 0 else 1.0) * 1e-9 / max(score.size, 1)
    key = score.astype(np.float64) + idx * eps

    accepted = np.zeros(score.shape, bool)
    neg = -np.inf
    rounds = 0
    converged = False
    for _ in range(max_rounds):
        rounds += 1
        if not live.any():
            converged = True
            break
        cand_key = np.where(live, key, neg)
        mx = maximum_filter(cand_key, footprint=foot, mode="constant", cval=neg)
        win = live & (cand_key >= mx)
        if not win.any():
            converged = True
            break
        accepted |= win
        live &= ~binary_dilation(win, structure=foot)
        live &= ~win
    else:
        converged = not live.any()

    if max_dots is not None and int(accepted.sum()) > max_dots:
        # Sequential greedy stopped after ``max_dots`` acceptances accepts
        # exactly the ``max_dots`` highest-key members of the *uncapped*
        # accepted set, because acceptances happen in descending key order.
        # Capping inside a round would be wrong: a later round can accept a
        # cell whose key exceeds that of an earlier round's weakest winner.
        ak = key[accepted]
        cut = np.partition(ak, ak.size - max_dots)[ak.size - max_dots]
        accepted &= key >= cut
    return (accepted, rounds, converged) if return_diagnostics else accepted


def packing_efficiency(dots: np.ndarray, footprint: np.ndarray,
                       radius: float = RADIUS_PX) -> dict:
    """Realised kernel credit mass of a dot field vs the kernel-disjoint ideal."""
    dots = np.asarray(dots, bool)
    n = int(dots.sum())
    if n == 0:
        return dict(n_dots=0, credit_mass=0.0, packing_efficiency=0.0, halo_fraction=0.0)
    d = distance_transform_edt(~dots)
    k = np.maximum(1.0 - d / radius, 0.0)
    fp = np.asarray(footprint, bool)
    return dict(n_dots=n,
                credit_mass=float(k[fp].sum()),
                packing_efficiency=float(k[fp].sum() / (n * KERNEL_MASS)),
                halo_fraction=float(((d < radius) & fp).sum() / max(int(fp.sum()), 1)))


@dataclass
class DinkelbachResult:
    dots: np.ndarray
    dti_model: float
    bar: float
    n_dots: int
    tp_model: float
    iterations: int
    trace: list


def dinkelbach_pack(rho: np.ndarray, allowed: np.ndarray, sep_px: float, *,
                    k_truth: float | None = None, tol: float = 1e-5,
                    max_iter: int = 40, max_dots: int | None = None,
                    use_self_credit: bool = True) -> DinkelbachResult:
    """Allocate to the fixed point of the exact marginal bar (1).

    ``k_truth`` defaults to the model's own total expected off-catalogue fault
    mass ``sum_x rho(x)``; it only sets the scale of the MODEL DTI used to pick
    the bar, and is reported as a MODEL quantity, never as a score.
    """
    rho = np.asarray(rho, np.float32)
    allowed = np.asarray(allowed, bool)
    e = expected_credit(rho)
    ks = self_credit(rho) if use_self_credit else np.zeros_like(e)
    k_truth = float(rho.sum()) if k_truth is None else float(k_truth)
    lam, trace = 0.0, []
    dots = np.zeros(rho.shape, bool)
    for it in range(max_iter):
        bar = marginal_bar(lam) * (1.0 - ks)
        dots = allocate_separated(e, allowed, sep_px, bar, max_dots=max_dots)
        n = int(dots.sum())
        if n == 0:
            trace.append(dict(iteration=it, bar=float(marginal_bar(lam)), n_dots=0, dti_model=0.0))
            break
        tp = float(e[dots].sum())
        m = float(ks[dots].sum())
        new = dti_from(tp, n, m, k_truth)
        trace.append(dict(iteration=it, bar=float(marginal_bar(lam)), n_dots=n,
                          tp_model=tp, dti_model=new))
        if abs(new - lam) < tol:
            lam = new
            break
        lam = new
    return DinkelbachResult(dots=dots, dti_model=float(lam), bar=float(marginal_bar(lam)),
                            n_dots=int(dots.sum()), tp_model=float(expected_credit(rho)[dots].sum())
                            if dots.any() else 0.0, iterations=len(trace), trace=trace)


# --------------------------------------------------------------------------
# zero-catalogue feature stack
# --------------------------------------------------------------------------
def _clean(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.asarray(a, np.float32).copy()
    bad = ~np.isfinite(out) | (np.abs(out) > 1e30)
    if bad.any():
        good = valid & ~bad
        out[bad] = float(np.median(out[good])) if good.any() else 0.0
    return out


def _grad_mag(a: np.ndarray, sigma: float) -> np.ndarray:
    s = gaussian_filter(a, sigma) if sigma > 0 else a
    gy, gx = np.gradient(s)
    return np.hypot(gy, gx).astype(np.float32)


def _ridgeness(a: np.ndarray, sigma: float) -> np.ndarray:
    """Most-negative Hessian eigenvalue (bright-ridge strength) at scale sigma."""
    s = gaussian_filter(a, sigma)
    gy, gx = np.gradient(s)
    hyy, hyx = np.gradient(gy)
    hxy, hxx = np.gradient(gx)
    tr = hyy + hxx
    det = hyy * hxx - 0.5 * (hyx + hxy) * (hyx + hxy)
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    lam_min = tr / 2.0 - disc
    return (-np.minimum(lam_min, 0.0)).astype(np.float32)


def _local_z(a: np.ndarray, size: int) -> np.ndarray:
    m = uniform_filter(a, size, mode="nearest")
    v = uniform_filter(a * a, size, mode="nearest") - m * m
    return ((a - m) / np.sqrt(np.maximum(v, 1e-12))).astype(np.float32)


def build_feature_stack(data_dir: Path, ext_dir: Path, valid: np.ndarray,
                        cache_dir: Path) -> tuple[np.memmap, list[str]]:
    """Build (or reload) the cached zero-catalogue ``(N_valid, F)`` float16 stack."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta_p = cache_dir / "kdmc_features_meta.json"
    mm_p = cache_dir / "kdmc_features_f16.mmap"
    n_valid = int(valid.sum())
    if meta_p.is_file() and mm_p.is_file():
        meta = json.loads(meta_p.read_text())
        if (meta.get("version") == FEATURE_VERSION and meta.get("n_valid") == n_valid
                and mm_p.stat().st_size == n_valid * meta["n_features"] * 2):
            return (np.memmap(mm_p, np.float16, "r", shape=(n_valid, meta["n_features"])),
                    meta["names"])

    tmp_p = cache_dir / "kdmc_features_tmp.mmap"
    max_cols = 128
    mm = np.memmap(tmp_p, np.float16, "w+", shape=(n_valid, max_cols))
    names: list[str] = []

    def add(name: str, arr2d: np.ndarray) -> None:
        v = np.asarray(arr2d, np.float32)[valid]
        v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
        lo, hi = np.percentile(v, [0.1, 99.9])
        if hi > lo:
            v = np.clip(v, lo, hi)
            v = (v - lo) / (hi - lo)
        else:
            v = np.zeros_like(v)
        mm[:, len(names)] = v.astype(np.float16)
        names.append(name)

    with rasterio.open(Path(data_dir) / "training_features.tif") as ds:
        raw = {}
        for b in range(1, ds.count + 1):
            desc = (ds.descriptions[b - 1] or f"band{b}").split(" - ")[0].strip()
            a = _clean(ds.read(b), valid)
            add(f"b{b:02d}_{desc}", a)
            raw[b] = a

    # Multi-scale edge / ridge transforms on the bands that carry structure.
    derive = {2: "rtp", 3: "tmi_hg", 6: "tc", 11: "isograv_vg", 12: "det_elev",
              13: "iso_grav", 15: "z_base", 17: "cond_surf", 18: "isograv_hg", 19: "det_slope"}
    for b, nm in derive.items():
        a = raw[b]
        add(f"g1_{nm}", _grad_mag(a, 1.0))
        add(f"g3_{nm}", _grad_mag(a, 3.0))
        add(f"ridge2_{nm}", _ridgeness(a, 2.0))
        add(f"z25_{nm}", _local_z(a, 25))
    # cover-thickness x basement-gradient interaction (concealed basin-bounding faults)
    add("zbase_x_ghg", raw[15] * _grad_mag(raw[13], 2.0))
    add("cond_edge", _grad_mag(np.log1p(np.maximum(raw[17], 0.0)), 2.0))
    del raw

    def add_raster(fname: str, prefix: str, scale: float = 1.0) -> None:
        with rasterio.open(Path(ext_dir) / fname) as ds:
            for b in range(1, ds.count + 1):
                d = (ds.descriptions[b - 1] or f"b{b}").strip()
                add(f"{prefix}_{d}", _clean(ds.read(b).astype(np.float32) * scale, valid))

    add_raster("topo_10m_derived_100m_u8.tif", "topo10")
    add_raster("lidar_scarp_features_u8.tif", "lid")
    add_raster("dem10_chi_100m_i16.tif", "chi")
    add_raster("dem10_chi_100m_u8.tif", "chin")
    add_raster("geodawn_rad_u8.tif", "gdrad")
    add_raster("geodawn_extensions_u8.tif", "gdext")

    # Published pre-Quaternary bedrock structure (USGS SGMC) — an independent map,
    # not the competition catalogue. Carried as a distance feature and canaried.
    with rasterio.open(Path(ext_dir) / "sgmc_faults_100m.tif") as ds:
        sgmc = ds.read(1)
    sgmc_pos = (sgmc > 0) & (sgmc != 255)
    add("sgmc_logdist", np.log1p(np.minimum(distance_transform_edt(~sgmc_pos), 100.0)))

    # Named mimic #1 — Pleistocene Lake Lahontan shoreline benches. Elevation is
    # carried explicitly so the model can price constant-elevation lineaments.
    with rasterio.open(Path(data_dir) / "geodawn_dem_a2_100m.tif") as ds:
        dem = _clean(ds.read(1), valid)
    add("dem_abs", dem)
    add("lahontan_band", np.exp(-0.5 * ((dem - 1330.0) / 25.0) ** 2))
    add("bonneville_band", np.exp(-0.5 * ((dem - 1555.0) / 25.0) ** 2))
    # Named mimic #2 — GeoDAWN flight-line levelling seams: N-S high-frequency
    # striping in the magnetic bands, captured as a directional-anisotropy ratio.
    with rasterio.open(Path(data_dir) / "training_features.tif") as ds:
        rtp = _clean(ds.read(2), valid)
    gy, gx = np.gradient(gaussian_filter(rtp, 1.0))
    add("mag_stripe_ratio", np.abs(gx) / (np.abs(gy) + np.abs(gx) + 1e-6))
    del dem, rtp, gy, gx

    n_feat = len(names)
    mm.flush()
    out = np.memmap(mm_p, np.float16, "w+", shape=(n_valid, n_feat))
    for j in range(n_feat):
        out[:, j] = mm[:, j]
    out.flush()
    del mm, out
    tmp_p.unlink(missing_ok=True)
    meta_p.write_text(json.dumps(dict(version=FEATURE_VERSION, n_valid=n_valid,
                                      n_features=n_feat, names=names), indent=2) + "\n")
    return np.memmap(mm_p, np.float16, "r", shape=(n_valid, n_feat)), names


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
