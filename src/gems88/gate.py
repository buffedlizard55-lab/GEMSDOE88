"""GEMS88 machine gate v3: portal-parity format check, uniqueness (literal AND like-for-like),
evidence gates, and an unambiguous ``ok_to_download`` / ``ok_to_submit`` verdict.

Design rules
------------
* No human input.  Every verdict is recomputed from bytes on disk.
* The *literal* reading of the lane rule ("<=70% of my dots within 3 px of ANY one registry
  raster") is vacuous against a dense continuous raster: ``17GEMSDOE_E-proba-multiscale`` is
  positive on every one of the 5,167,373 footprint pixels, so ANY raster -- including random
  dots -- scores overlap 1.0 (``vacuity_witness`` below proves it on a seeded random raster).
  A gate that no raster can pass cannot discriminate, so v3 evaluates dense registry rasters
  like-for-like: their *effective dots* are their top-N pixels by value, N = candidate dot
  count.  Both readings are always computed and published; the verdict uses like-for-like.
* Rank correlation is Spearman over the footprint (average ranks; binary rasters handled in
  closed form).  Limits: |rho| <= 0.90 and forward 3-px overlap <= 0.70.
* A passing gate means "eligible for a weekly slot".  It never spends a slot and never selects
  the final submission; that is a separate human selector step (rules s3.4, s3.5, s3.6.2).
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
from scipy import ndimage as ndi
from scipy.stats import rankdata

POLICY_VERSION = "gems88-gate-v3"
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
    idx = np.argpartition(-flat, k - 1)[:k]
    out = np.zeros(values.shape, bool)
    out.ravel()[idx] = True
    return out & pos


def forward_overlap(mine, theirs, radius=RADIUS_PX) -> float:
    """Share of ``mine`` dots with a ``theirs`` dot within ``radius`` px (Euclidean, <=)."""
    mine = np.asarray(mine, bool)
    theirs = np.asarray(theirs, bool)
    if not mine.any() or not theirs.any():
        return 0.0
    ty, tx = np.nonzero(theirs)
    if ty.size > 400_000:  # dense raster: a distance transform is cheaper than a huge KD-tree
        d = ndi.distance_transform_edt(~theirs)
        return float((d[mine] <= radius).mean())
    from scipy.spatial import cKDTree
    tree = cKDTree(np.column_stack([ty, tx]))
    d, _ = tree.query(np.argwhere(mine), distance_upper_bound=radius + 1e-9)
    return float(np.mean(d <= radius))


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
    """Prove the literal rule is unsatisfiable: a seeded RANDOM raster has literal overlap 1.0
    against the dense raster, so the literal rule rejects every possible candidate."""
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
        key = sha256_bytes(np.packbits(vals > 0).tobytes()) + ("D" if is_dense(vals, footprint) else "S")
        if key in seen:  # identical decoded dot set already measured; copy the row
            r = dict(seen[key])
            r.update(label=label, path=str(path), duplicate_of=seen[key]["label"])
            rows.append(r)
            continue
        dense = is_dense(vals, footprint)
        lit_dots = (vals > 0) & footprint
        eff_dots = effective_dots(vals, footprint, n)
        lit = forward_overlap(cand_dots, lit_dots)
        like = lit if not dense else forward_overlap(cand_dots, eff_dots)
        rk_v = rank_vec(vals, footprint)
        rho_final = _pearson(rk_final, rk_v)
        rho_pre = rho_final if surface is None else _pearson(rk_pre, rk_v)
        r = dict(label=label, path=str(path), dense=dense, registry_dots=int(lit_dots.sum()),
                 literal_overlap_3px=lit, like_for_like_overlap_3px=like,
                 rho_final=rho_final, rho_preplacement=rho_pre,
                 identical_decoded=bool(np.array_equal(cand_dots, lit_dots)))
        r["blocks_literal"] = bool(lit > OVERLAP_MAX or abs(rho_final) > RHO_MAX or abs(rho_pre) > RHO_MAX or r["identical_decoded"])
        r["blocks_like_for_like"] = bool(like > OVERLAP_MAX or abs(rho_final) > RHO_MAX or abs(rho_pre) > RHO_MAX or r["identical_decoded"])
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
        limits=dict(overlap_max=OVERLAP_MAX, rho_max=RHO_MAX, radius_px=RADIUS_PX, dense_fraction=DENSE_FRACTION),
        registry_rasters=len(rows), distinct_dot_sets=len(seen), missing=len(errors),
        worst_like_for_like_overlap=None if worst is None else dict(label=worst["label"], value=worst["like_for_like_overlap_3px"]),
        worst_abs_rho=None if worst_rho is None else dict(label=worst_rho["label"], value=max(abs(worst_rho["rho_final"]), abs(worst_rho["rho_preplacement"]))),
        literal_blockers=[r["label"] for r in ok_rows if r["blocks_literal"]],
        like_for_like_blockers=[r["label"] for r in ok_rows if r["blocks_like_for_like"]],
        unique_literal=bool(not errors and not any(r["blocks_literal"] for r in ok_rows)),
        unique_like_for_like=bool(not errors and not any(r["blocks_like_for_like"] for r in ok_rows)),
        vacuity_witness=witness, rows=rows)


# ----------------------------------------------------------------------------- fingerprint screen
def fingerprint(dots, d_cat) -> dict:
    """Distance-to-catalogue profile of a dot set (``d_cat`` = EDT distance in px to the nearest mapped-fault pixel)."""
    dc = np.asarray(d_cat)[np.asarray(dots, bool)]
    return dict(n=int(dc.size), median_d_cat_px=float(np.median(dc)), share_le2=float((dc <= 2).mean()),
                share_gt10=float((dc > 10).mean()), share_gt25=float((dc > 25).mean()))


def fingerprint_screen(fp: dict) -> bool:
    """Necessary screen: no dot within 2 px of the catalogue and >= 35% of dots > 25 px away (IR-88-60)."""
    return bool(fp["share_le2"] == 0.0 and fp["share_gt25"] >= FP_SCREEN_MIN_GT25)


# ----------------------------------------------------------------------------- decision
def decide(*, portal, uniqueness, canary_passed, holdout_beats_bar, name, note, used_names,
           receipt_sha_matches=True) -> dict:
    """Combine every gate into ONE verdict.  Every reason is machine-readable."""
    reasons_block, reasons_info = [], []
    ok_download = bool(portal["ok"] and receipt_sha_matches)
    if not portal["ok"]:
        reasons_block.append("FORMAT: portal-parity validation failed: " + "; ".join(portal["problems"][:3]))
    if not receipt_sha_matches:
        reasons_block.append("HASH: receipt sha256 differs from the file on disk")
    if not uniqueness["unique_like_for_like"]:
        reasons_block.append("UNIQUENESS: blocked (like-for-like) by " + ", ".join(uniqueness["like_for_like_blockers"][:5]))
    if not uniqueness["unique_literal"]:
        reasons_info.append("literal registry rule fails only vs dense rasters that no raster can pass (vacuity witness): "
                            + ", ".join(uniqueness["literal_blockers"][:4]))
    if not canary_passed:
        reasons_block.append("LEAKAGE: a single feature has AUC > 0.90")
    if not holdout_beats_bar:
        reasons_block.append("HOLDOUT: did not beat the pre-registered holdout bar (no slot is spent on an unproven idea)")
    if len(name) > MAX_NAME or len(note) > MAX_NAME or not name or not note:
        reasons_block.append(f"NAME/NOTE: name and note must be non-empty and <= {MAX_NAME} characters")
    if name in set(used_names):
        reasons_block.append("NAME: not unique among previously used submission names")
    ok_submit = bool(ok_download and not reasons_block)
    return dict(policy=POLICY_VERSION, ok_to_download=ok_download, ok_to_submit=ok_submit,
                label="OK TO DOWNLOAD - OK TO SUBMIT" if ok_submit else
                      ("OK TO DOWNLOAD - NOT OK TO SUBMIT" if ok_download else "NOT OK TO DOWNLOAD OR SUBMIT"),
                blocking_reasons=reasons_block, informational=reasons_info,
                note_len=len(note), name_len=len(name),
                human_step_remaining="Selecting the final submission and clicking Submit remain human decisions (rules s3.4/s3.5, <= 3 slots per week or the portal limit, whichever the website shows).")
