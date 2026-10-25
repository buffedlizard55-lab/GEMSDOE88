"""GEMS88 machine gate v3: portal-parity format check, uniqueness (literal AND like-for-like),
evidence gates, and an unambiguous ``ok_to_download`` / ``ok_to_submit`` verdict.

Compatibility policy (IR-88-113)
-------------------------------
Dense/top-N comparisons are historical diagnostics ONLY. Literal overlap and
rank correlation against every registered raster remain binding. Measurements
use the shared template's overlap implementation; no private clearance rule.
An arbitrary list of priors is not a verified complete registry. A missing
pre-placement surface cannot be replaced by final dots for clearance. A local
PASS can only establish selector eligibility; it cannot approve or spend a slot.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from gems57.uniqueness import _near, dot_overlap, excess_overlap
from scipy.stats import rankdata

POLICY_VERSION = "gems88-gate-v3"
POLICY_VERSION_V4 = "gems88-gate-v4"
FP_SCREEN_MIN_GT25 = 0.35   # share of dots > 25 px from any mapped fault (derived from 20 owner-reported rasters; necessary, not sufficient)
OVERLAP_MAX = 0.70
RHO_MAX = 0.90
RADIUS_PX = 3.0
DENSE_FRACTION = 0.05
EXPECTED = dict(epsg=32611, shape=(3730, 3292), cell=100.0, transform=(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0))
MAX_NAME = 140


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ----------------------------------------------------------------------------- format / portal parity
def _checks_from_dataset(ds, sample, footprint):
    """Return (checks dict, array) for an open rasterio dataset."""
    c = {}
    c["one_band"] = ds.count == 1
    c["dtype_float32"] = ds.dtypes[0] == "float32"
    c["crs_epsg_32611"] = ds.crs is not None and ds.crs.to_epsg() == EXPECTED["epsg"]
    c["shape_matches_sample"] = ds.shape == sample["shape"]
    c["transform_matches_sample"] = tuple(ds.transform)[:6] == sample["transform"]
    c["bounds_match_sample"] = tuple(ds.bounds) == sample["bounds"]
    c["resolution_100m"] = tuple(abs(x) for x in ds.res) == (EXPECTED["cell"], EXPECTED["cell"])
    c["nodata_undeclared"] = ds.nodata is None  # policy: no nodata declaration, no NaN anywhere
    a = ds.read(1)
    am = ds.read(1, masked=True)
    c["all_finite"] = bool(np.isfinite(a).all())
    c["masked_read_no_masked_cells"] = int(np.ma.count_masked(am)) == 0
    finite = np.isfinite(a)
    c["min_ge_0"] = bool(finite.any() and float(a[finite].min()) >= 0.0)
    c["max_le_1"] = bool(finite.any() and float(a[finite].max()) <= 1.0)
    # the portal sentence: "Predicted values must be in range [0, 1]" -- emulate both common implementations
    c["portal_range_check_nan_strict"] = bool(np.all((a >= 0) & (a <= 1)))
    c["portal_range_check_nanmin_nanmax"] = bool(np.nanmin(a) >= 0 and np.nanmax(a) <= 1)
    if footprint is not None:
        c["footprint_cells_finite"] = bool(np.isfinite(a[footprint]).all())
        c["outside_footprint_zero"] = bool((a[~footprint] == 0).all())
    c["has_dots"] = bool((a > 0).any())
    c["no_internal_mask_band"] = not bool((ds.dataset_mask() == 0).any())
    return c, a


def load_sample(sample_path):
    with rasterio.open(sample_path) as s:
        return dict(shape=s.shape, transform=tuple(s.transform)[:6], bounds=tuple(s.bounds),
                    compress=str(s.profile.get("compress")), tiled=bool(s.profile.get("tiled")),
                    block_shapes=list(s.block_shapes), sha256=sha256_file(sample_path))


def _classic_tiff_header(b: bytes) -> dict:
    magic = b[:4]
    return dict(byte_order="II" if b[:2] == b"II" else "MM" if b[:2] == b"MM" else "?",
                is_classic_tiff=magic in (b"II*\x00", b"MM\x00*"),
                is_bigtiff=magic in (b"II+\x00", b"MM\x00+"))


def portal_validate(path, sample_path, footprint=None) -> dict:
    """Open the file the way a portal would: from a .zip member, via /vsimem, and a second decoder.

    ``path`` may be a .tif or a .zip holding exactly one .tif/.tiff.
    """
    path = Path(path)
    sample = load_sample(sample_path)
    out = dict(path=str(path), policy=POLICY_VERSION, bytes=path.stat().st_size, sha256=sha256_file(path), problems=[])
    problems = out["problems"]
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            infos = z.infolist()
            out["zip_members"] = names
            out["zip_testzip"] = z.testzip()
            if len(names) != 1 or not names[0].lower().endswith((".tif", ".tiff")) or "/" in names[0] or ".." in names[0]:
                problems.append("zip must hold exactly one flat .tif/.tiff member")
                out.update(ok=False, checks={}, n_dots=None)
                return out
            out["zip_member_compress_type"] = infos[0].compress_type
            raw = z.read(names[0])
            out["member_name"] = names[0]
    else:
        raw = path.read_bytes()
        out["member_name"] = path.name
    out["tiff_header"] = _classic_tiff_header(raw)
    if not out["tiff_header"]["is_classic_tiff"]:
        problems.append("not classic TIFF (BigTIFF or not a TIFF)")
    with MemoryFile(raw) as mf:
        with mf.open() as ds:
            checks, a = _checks_from_dataset(ds, sample, footprint)
            prof = ds.profile
            out["layout"] = dict(compress=str(prof.get("compress")), tiled=bool(prof.get("tiled")),
                                 block_shapes=list(ds.block_shapes), predictor=prof.get("predictor"),
                                 interleave=str(prof.get("interleave")))
    out["checks"] = checks
    out["array_sha256"] = sha256_bytes(np.ascontiguousarray(a).tobytes())
    out["n_dots"] = int((a > 0).sum())
    out["min"] = float(a.min())
    out["max"] = float(a.max())
    out["n_unique_values"] = int(np.unique(a).size)
    # layout parity with the official sample (warn-level, not a value problem)
    out["layout_parity_with_sample"] = (out["layout"]["compress"] == sample["compress"]
                                        and out["layout"]["tiled"] == sample["tiled"]
                                        and out["layout"]["block_shapes"] == sample["block_shapes"])
    # second, independent decoder
    out["second_decoder"] = dict(name=None, equal=None)
    for name in ("tifffile", "PIL"):
        try:
            if name == "tifffile":
                import tifffile  # type: ignore
                b = tifffile.imread(io.BytesIO(raw))
            else:
                from PIL import Image  # type: ignore
                b = np.array(Image.open(io.BytesIO(raw)))
            out["second_decoder"] = dict(name=name, equal=bool(b.shape == a.shape and np.array_equal(b.astype(np.float32), a)))
            break
        except Exception as e:  # noqa: BLE001 -- decoder availability varies; record and try next
            out["second_decoder"] = dict(name=name, equal=None, error=type(e).__name__ + ": " + str(e)[:120])
    for k, v in checks.items():
        if v is False:
            problems.append(f"check failed: {k}")
    if out["second_decoder"].get("equal") is False:
        problems.append("second decoder disagrees with rasterio")
    out["ok"] = not problems
    return out


# ----------------------------------------------------------------------------- uniqueness
def read_values(path, footprint):
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    a[~footprint] = 0.0
    return a


def is_dense(values, footprint) -> bool:
    return float(((values > 0) & footprint).sum()) / float(footprint.sum()) > DENSE_FRACTION


def effective_dots(values, footprint, n_target):
    """Literal dots for sparse rasters; top-``n_target`` pixels by value for dense rasters."""
    pos = (values > 0) & footprint
    if not is_dense(values, footprint):
        return pos
    flat = np.where(footprint, values, -np.inf).ravel()
    k = min(int(n_target), int(pos.sum()))
    if k <= 0:
        return np.zeros(values.shape, bool)
    idx = np.argpartition(-flat, k - 1)[:k]
    out = np.zeros(values.shape, bool)
    out.ravel()[idx] = True
    return out & pos


def forward_overlap(mine, theirs, radius=RADIUS_PX) -> float:
    """Compatibility alias for the shared literal Euclidean support test."""
    return dot_overlap(mine, theirs, radius_px=radius)


def rank_vec(a, footprint):
    """Average-rank vector over the footprint; binary arrays reduce to their 0/1 indicator
    (an affine map of their ranks, so Pearson on indicators equals Spearman)."""
    x = np.asarray(a)[footprint].astype(np.float64)
    u = np.unique(x)
    if len(u) <= 2:
        return (x == u[-1]).astype(np.float64) if len(u) == 2 else np.zeros_like(x)
    return rankdata(x)


def _pearson(u, v) -> float:
    if u.std() == 0 or v.std() == 0:
        return 0.0
    u = u - u.mean()
    v = v - v.mean()
    return float((u @ v) / np.sqrt((u @ u) * (v @ v)))


def spearman_on_footprint(a, b, footprint) -> float:
    """Spearman rho over footprint pixels with average ranks (closed form for binary vs binary)."""
    return _pearson(rank_vec(a, footprint), rank_vec(b, footprint))


def vacuity_witness(dense_values, footprint, n_dots, seed=88, radius=RADIUS_PX) -> dict:
    """Random-overlap diagnostic, not a universal mathematical certificate.

    Only the shared saturation_certificate can prove coverage of every allowed
    cell. One random placement alone cannot establish that universal claim.
    """
    rng = np.random.default_rng(seed)
    idx = rng.choice(np.flatnonzero(footprint.ravel()), size=int(n_dots), replace=False)
    rnd = np.zeros(footprint.shape, bool)
    rnd.ravel()[idx] = True
    literal = forward_overlap(rnd, (dense_values > 0) & footprint, radius)
    like = forward_overlap(rnd, effective_dots(dense_values, footprint, n_dots), radius)
    return dict(random_dots=int(n_dots), seed=seed, literal_overlap=literal, like_for_like_overlap=like,
                literal_rule_vacuous=bool(literal > OVERLAP_MAX))


def uniqueness_report(candidate_path, registry, footprint, surface=None) -> dict:
    """Compare a candidate against every registry raster.

    ``registry`` = list of (label, path).  ``surface`` = optional pre-placement float surface
    (2-D array) used for the pre-placement rank-correlation check; if omitted the binary
    candidate is used for both checks.
    """
    cand = read_values(candidate_path, footprint)
    cand_dots = (cand > 0) & footprint
    n = int(cand_dots.sum())
    surf = cand if surface is None else np.asarray(surface, np.float32)
    if surf.shape != cand.shape or not np.isfinite(surf[footprint]).all():
        raise ValueError("pre-placement surface must match the grid and be finite inside footprint")
    surf_dots = (surf > 0) & footprint
    rk_final = rank_vec(cand, footprint)
    rk_pre = rk_final if surface is None else rank_vec(surf, footprint)
    rows, seen = [], {}
    witness = None
    for label, path in registry:
        path = Path(path)
        if not path.is_file():
            rows.append(dict(label=label, path=str(path), error="missing"))
            continue
        vals = read_values(path, footprint)
        key = sha256_bytes(np.ascontiguousarray(vals).tobytes())
        if key in seen:  # identical decoded VALUES (not merely support)
            r = dict(seen[key])
            r.update(label=label, path=str(path), duplicate_of=seen[key]["label"])
            rows.append(r)
            continue
        dense = is_dense(vals, footprint)
        lit_dots = (vals > 0) & footprint
        eff_dots = effective_dots(vals, footprint, n)
        lit = forward_overlap(cand_dots, lit_dots)
        pre_lit = forward_overlap(surf_dots, lit_dots)
        like = lit if not dense else forward_overlap(cand_dots, eff_dots)
        rk_v = rank_vec(vals, footprint)
        rho_final = _pearson(rk_final, rk_v)
        rho_pre = rho_final if surface is None else _pearson(rk_pre, rk_v)
        r = dict(label=label, path=str(path), dense=dense, registry_dots=int(lit_dots.sum()),
                 literal_overlap_3px=lit, surface_literal_overlap_3px=pre_lit, like_for_like_overlap_3px=like,
                 rho_final=rho_final, rho_preplacement=rho_pre,
                 identical_decoded=bool(np.array_equal(cand_dots, lit_dots)))
        r["blocks_literal"] = bool(lit > OVERLAP_MAX or pre_lit > OVERLAP_MAX or abs(rho_final) > RHO_MAX or abs(rho_pre) > RHO_MAX or r["identical_decoded"])
        r["blocks_like_for_like"] = bool(like > OVERLAP_MAX or abs(rho_final) > RHO_MAX or abs(rho_pre) > RHO_MAX or r["identical_decoded"])
        # --- Historical v4 diagnostics ONLY (not an authorized decision policy).
        # The binding literal rule remains above and in decide(). Dense surfaces
        # on rank correlation plus chance-corrected excess overlap when their
        # 3-px halo does not already cover the whole footprint. A continuous
        # probability surface positive everywhere has no dots, so the literal
        # `>0`-support overlap (= 1.0 for every candidate) cannot evidence
        # lane drift; it is still reported verbatim above as `literal_*`.
        if dense:
            halo_cov = float(_near(lit_dots, RADIUS_PX)[footprint].mean())
            excess = excess_overlap(lit, halo_cov)
        else:
            halo_cov, excess = None, None
        r["halo_coverage_footprint"] = halo_cov
        r["excess_overlap_3px"] = excess
        r["space_filling"] = bool(dense and excess is None)
        rho_blocks = abs(rho_final) > RHO_MAX or abs(rho_pre) > RHO_MAX
        if not dense:
            dot_blocks = lit > OVERLAP_MAX
        elif excess is not None:
            dot_blocks = excess > OVERLAP_MAX
        else:
            dot_blocks = False  # historical diagnostic only; literal overlap still blocks
        r["blocks_v4"] = bool(rho_blocks or dot_blocks or r["identical_decoded"])
        rows.append(r)
        seen[key] = r
        if dense and witness is None:
            witness = vacuity_witness(vals, footprint, n)
            witness["dense_label"] = label
    ok_rows = [r for r in rows if "error" not in r]
    errors = [r for r in rows if "error" in r]
    worst = max(ok_rows, key=lambda r: r["like_for_like_overlap_3px"], default=None)
    worst_rho = max(ok_rows, key=lambda r: max(abs(r["rho_final"]), abs(r["rho_preplacement"])), default=None)
    return dict(
        policy=POLICY_VERSION, candidate=str(candidate_path), candidate_dots=n,
        surface_checked=surface is not None,
        registry_complete=False,  # curated path lists cannot certify the full inventory
        scope="Historical compatibility diagnostics; use the shared indexed registry gate for clearance",
        limits=dict(overlap_max=OVERLAP_MAX, rho_max=RHO_MAX, radius_px=RADIUS_PX, dense_fraction=DENSE_FRACTION),
        registry_rasters=len(rows), distinct_dot_sets=len(seen), missing=len(errors),
        worst_like_for_like_overlap=None if worst is None else dict(label=worst["label"], value=worst["like_for_like_overlap_3px"]),
        worst_abs_rho=None if worst_rho is None else dict(label=worst_rho["label"], value=max(abs(worst_rho["rho_final"]), abs(worst_rho["rho_preplacement"]))),
        literal_blockers=[r["label"] for r in ok_rows if r["blocks_literal"]],
        like_for_like_blockers=[r["label"] for r in ok_rows if r["blocks_like_for_like"]],
        unique_literal=bool(n > 0 and ok_rows and not errors and not any(r["blocks_literal"] for r in ok_rows)),
        unique_like_for_like=bool(n > 0 and ok_rows and not errors and not any(r["blocks_like_for_like"] for r in ok_rows)),
        policy_v4=POLICY_VERSION_V4,
        v4_blockers=[r["label"] for r in ok_rows if r["blocks_v4"]],
        unique_v4=bool(n > 0 and ok_rows and not errors and not any(r["blocks_v4"] for r in ok_rows)),
        space_filling_rasters=[r["label"] for r in ok_rows if r.get("space_filling")],
        worst_dotfield_overlap=(lambda w: None if w is None else dict(label=w["label"], value=w["literal_overlap_3px"]))(
            max((r for r in ok_rows if not r["dense"]), key=lambda r: r["literal_overlap_3px"], default=None)),
        worst_excess_overlap=(lambda w: None if w is None else dict(label=w["label"], value=w["excess_overlap_3px"]))(
            max((r for r in ok_rows if r.get("excess_overlap_3px") is not None), key=lambda r: r["excess_overlap_3px"], default=None)),
        worst_literal_overlap=(lambda w: None if w is None else dict(label=w["label"], value=w["literal_overlap_3px"]))(
            max(ok_rows, key=lambda r: r["literal_overlap_3px"], default=None)),
        vacuity_witness=witness, rows=rows)


# ----------------------------------------------------------------------------- fingerprint screen
def fingerprint(dots, d_cat) -> dict:
    """Distance-to-catalogue profile of a dot set (``d_cat`` = EDT distance in px to the nearest mapped-fault pixel)."""
    dc = np.asarray(d_cat)[np.asarray(dots, bool)]
    return dict(n=int(dc.size), median_d_cat_px=float(np.median(dc)), share_le2=float((dc <= 2).mean()),
                share_gt10=float((dc > 10).mean()), share_gt25=float((dc > 25).mean()))


def fingerprint_screen(fp: dict) -> bool:
    """Necessary screen: no dot within 2 px of the catalogue and >= 35% of dots > 25 px away (IR-88-62)."""
    return bool(fp["share_le2"] == 0.0 and fp["share_gt25"] >= FP_SCREEN_MIN_GT25)


# ----------------------------------------------------------------------------- decision
def decide(*, portal, uniqueness, canary_passed, holdout_beats_bar, name, note, used_names,
           receipt_sha_matches=True) -> dict:
    """Fail-closed compatibility verdict; never approve a competition slot.

    Indexed inventory verification belongs to the shared registry gate. This
    function must not reinterpret literal failures as dense-prior exemptions.
    """
    reasons_block, reasons_info = [], []
    ok_download = portal.get("ok") is True and receipt_sha_matches is True
    if portal.get("ok") is not True:
        reasons_block.append("FORMAT: local saved-byte validation failed: " + "; ".join(portal.get("problems", [])[:3]))
    if receipt_sha_matches is not True:
        reasons_block.append("HASH: receipt sha256 differs from the file on disk")
    if uniqueness.get("unique_literal") is not True:
        reasons_block.append("UNIQUENESS: literal registry rule failed or unverified; no dense-prior exemption: "
                             + ", ".join(uniqueness.get("literal_blockers", [])[:5]))
    if uniqueness.get("registry_complete") is not True:
        reasons_block.append("UNIQUENESS: complete indexed registry audit not verified")
    if uniqueness.get("surface_checked") is not True:
        reasons_block.append("UNIQUENESS: pre-placement surface audit not verified")
    if uniqueness.get("unique_like_for_like") is False:
        reasons_info.append("Like-for-like comparison also fails; diagnostic only")
    if canary_passed is not True:
        reasons_block.append("LEAKAGE: every feature must pass the symmetric AUC <= 0.90 canary")
    if holdout_beats_bar is not True:
        reasons_block.append("HOLDOUT: did not beat the pre-registered holdout bar (no slot is spent on an unproven idea)")
    valid_text = all(isinstance(x, str) and 0 < len(x.strip()) <= MAX_NAME
                     and len(x) <= MAX_NAME for x in (name, note))
    if not valid_text:
        reasons_block.append(f"NAME/NOTE: name and note must be non-empty and <= {MAX_NAME} characters")
    if isinstance(name, str) and name in set(used_names):
        reasons_block.append("NAME: not unique among previously used submission names")
    eligible = bool(ok_download and not reasons_block)
    return dict(policy=POLICY_VERSION, ok_to_download=ok_download, ok_to_submit=False,
                eligible_for_selector=eligible, approved_for_weekly_slot=False,
                label=("OK TO DOWNLOAD - SELECTOR REQUIRED - DO NOT SUBMIT" if eligible else
                       "OK TO DOWNLOAD - NOT OK TO SUBMIT" if ok_download else
                       "NOT OK TO DOWNLOAD OR SUBMIT"),
                blocking_reasons=reasons_block, informational=reasons_info,
                note_len=len(note) if isinstance(note, str) else None,
                name_len=len(name) if isinstance(name, str) else None,
                human_step_remaining="Separate selector authorization and the account's current portal allowance are required; this gate never spends a slot.")


def decide_v4(*, portal, uniqueness, canary_passed, holdout_beats_bar, name, note, used_names,
              receipt_sha_matches=True) -> dict:
    """Compatibility name only: delegate to the original literal gate.

    IR-88-127's dense/creation-order exemptions were not authorized by the
    user's any-registry rule. The v4 diagnostic fields may remain in historical
    evidence, but cannot replace unique_literal or authorize a selector/slot.
    Keeping one decision implementation avoids a second, weaker policy path.
    """
    result = decide(portal=portal, uniqueness=uniqueness, canary_passed=canary_passed,
                    holdout_beats_bar=holdout_beats_bar, name=name, note=note,
                    used_names=used_names, receipt_sha_matches=receipt_sha_matches)
    result["compatibility_entrypoint"] = POLICY_VERSION_V4
    result["informational"].append(
        "Legacy v4/excess-overlap diagnostics are not authorization to waive the literal any-registry gate.")
    return result
