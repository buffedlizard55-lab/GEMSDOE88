#!/usr/bin/env python3
"""CONCENTRATION axis: relocate mass between km-scale blocks of parent R0.

Parent R0 = ``h33-h33-2-b2`` (GEMSDOE32): 37,654 unit-mass dots, zero within
2 px of the mapped catalogue, sha256 pinned in ``scripts/restore_inputs.py`` and
re-verified by ``scripts/verify_parent_r0.py``.

Axis definition (agent brief v2, section 5)
-------------------------------------------
* Block: 10 x 10 px = 1 km x 1 km on the pinned 100 m grid (EPSG:32611).  The
  third variant repeats the 20 % move on 50 x 50 px = 5 km blocks, which tests
  the *scale* of the same bet rather than spending a slot on a third dose.
* Prior: parent dot density smoothed over ``sigma`` blocks.  Concretely
  ``prior = gaussian_filter(dot_count, sigma) / gaussian_filter(area_km2, sigma)``
  so footprint edges are not biased low.  This is the lineage's own belief about
  where fault fabric is dense, sharpened from pixel scale to km scale.  It is
  not derived from any withheld or test label; the only inputs are the parent
  raster and the mapped catalogue (used only for the exclusion collar).
* Donors: dots in the lowest-prior blocks first, most isolated first (distance
  to nearest other dot descending), then row/col as a total order.  Collar dots
  (<= 3 px from the catalogue) are protected, so collar mass is inherited from
  R0 exactly and cannot be mistaken for an intended sparse-tail removal.
* Receivers: allowed pixels (inside footprint, > 3 px from the catalogue, not
  already a dot) that are 8-adjacent to a dot that *survives* the donation,
  taken in highest-prior-block order.  Each surviving host dot may accept at
  most ``CAP_PER_HOST`` receivers.  Receivers are therefore welded to the most
  confident existing traces, which is what raises the metric's self-credit term.
* Count is fixed at 37,654; only the location of mass changes, so MASS is held
  constant by construction.

Everything is deterministic: every ordering terminates in (row, col) and no
random numbers are drawn, so re-running is bit-reproducible.

Outputs
-------
``releases/<id>.tif`` (NaN outside footprint) and ``releases/<id>-zeros.tif``
(0 outside footprint), plus one single-TIFF ``.zip`` per raster.
``registry/concentration_report.json`` records the parameter set, per-variant
diff statistics (block-density CV before/after for four block sizes, Gini, mean
nearest-neighbour distance, displacement, emptied blocks) and every hash.
"""

from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "data" / "bridge"
REG = ROOT / "data" / "registry"
RELEASES = ROOT / "releases"

PARENT_ID = "h33-h33-2-b2"
PARENT_SHA = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
PIN_SAMPLE = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
PIN_EXISTING = "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"

MIN_BLOCK_AREA_FRAC = 0.5   # ignore blocks less than half inside the footprint
CAP_PER_HOST = 2            # receivers allowed per surviving host dot
COLLAR_PX = 3.0             # strict collar: no variant mass added inside 3 px
DATE_STR = datetime.now(timezone.utc).strftime("%Y%m%d")
CV_LADDER_PX = (5, 10, 20, 50)

# (value tag, fraction of R0 dots moved, block size in px, prior sigma in blocks)
CONFIGS = (
    ("b10px-m10", 0.10, 10, 2.0),
    ("b10px-m20", 0.20, 10, 2.0),
    ("b50px-m20", 0.20, 50, 2.0),
)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:  # pragma: no cover - only if git is unavailable
        return "UNKNOWN"


def load_inputs():
    s_sample = sha256(BRIDGE / "sample_submission.tif")
    s_exist = sha256(BRIDGE / "existing_faults.tif")
    s_parent = sha256(REG / "h33_education.tif")
    assert s_sample == PIN_SAMPLE, f"sample_submission.tif pin mismatch: {s_sample}"
    assert s_exist == PIN_EXISTING, f"existing_faults.tif pin mismatch: {s_exist}"
    assert s_parent == PARENT_SHA, f"parent pin mismatch: {s_parent}"

    with rasterio.open(BRIDGE / "sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
        profile = src.profile.copy()
    with rasterio.open(BRIDGE / "existing_faults.tif") as src:
        ef = src.read(1)
    catalogue = (ef == 1) & footprint
    dist = distance_transform_edt(~catalogue).astype(np.float32)
    with rasterio.open(REG / "h33_education.tif") as src:
        parent = src.read(1) > 0.5
    assert int(parent.sum()) == 37_654
    assert int((parent & catalogue).sum()) == 0
    assert float(dist[parent].min()) > 2.0
    return footprint, catalogue, dist, parent, profile


def block_lattice(footprint: np.ndarray, block: int):
    nb_r = (footprint.shape[0] + block - 1) // block
    nb_c = (footprint.shape[1] + block - 1) // block
    rr, cc = np.nonzero(footprint)
    area_px = np.bincount((rr // block) * nb_c + (cc // block),
                          minlength=nb_r * nb_c).reshape(nb_r, nb_c).astype(np.float64)
    eligible = area_px >= MIN_BLOCK_AREA_FRAC * (block * block)
    return area_px, eligible.ravel(), nb_c


def block_prior(dots: np.ndarray, footprint: np.ndarray, block: int, sigma: float):
    """Smoothed dot-density prior (dots per km2) on a ``block``-px lattice."""
    area_px, eligible, nb_c = block_lattice(footprint, block)
    nb_r = area_px.shape[0]
    dr, dc = np.nonzero(dots)
    count = np.bincount((dr // block) * nb_c + (dc // block),
                        minlength=area_px.size).reshape(nb_r, -1).astype(np.float64)
    area_km2 = area_px * (0.1 * 0.1)
    num = gaussian_filter(count, sigma, mode="constant")
    den = gaussian_filter(area_km2, sigma, mode="constant")
    prior = np.divide(num, den, out=np.zeros_like(num), where=den > 1e-9)
    return prior.ravel(), eligible, nb_c


def block_ids(shape, block: int, nb_c: int):
    rr, cc = np.mgrid[0: shape[0], 0: shape[1]]
    return (rr // block) * nb_c + (cc // block)


def cv_stats(dots: np.ndarray, footprint: np.ndarray, prior: np.ndarray,
             eligible: np.ndarray, bids: np.ndarray) -> dict:
    counts = np.bincount(bids[dots], minlength=prior.size).astype(np.float64)
    occ = counts[eligible & (counts > 0)]
    all_el = counts[eligible]
    hot = np.zeros(prior.size, bool)
    n_hot = max(1, int(round(0.01 * int(eligible.sum()))))
    hot[np.argsort(-np.where(eligible, prior, -np.inf), kind="stable")[:n_hot]] = True
    hot &= eligible
    gini = 0.0
    if occ.size:
        s = np.sort(occ)
        n = s.size
        gini = float((2.0 * np.arange(1, n + 1) - n - 1).dot(s) / (n * s.sum()))
    return {
        "cv_occupied_blocks": float(occ.std() / occ.mean()) if occ.size and occ.mean() else 0.0,
        "cv_all_eligible_blocks": float(all_el.std() / all_el.mean()) if all_el.mean() else 0.0,
        "occupied_blocks": int(occ.size),
        "eligible_blocks": int(eligible.sum()),
        "zero_block_fraction": float(1.0 - occ.size / int(eligible.sum())),
        "gini_occupied": gini,
        "top1pct_prior_blocks": int(n_hot),
        "mass_share_in_top1pct_prior_blocks": float(counts[hot].sum() / counts.sum()),
        "mean_dots_per_occupied_block": float(occ.mean()) if occ.size else 0.0,
    }


def smoothed_density_cv(dots, footprint, block=10, sigmas=(2.0, 3.0, 5.0)):
    """CV of the km-smoothed dot density over footprint blocks.

    The brief quotes a 0.51-0.59 CV band for the best files without defining the
    estimator.  Raw per-block counts give 0.62 for R0; a smoothed density map is
    the definition that lands near the band, so both are reported and neither is
    used as a gate.
    """
    area_px, eligible, nb_c = block_lattice(footprint, block)
    nb_r = area_px.shape[0]
    area_km2 = area_px * 0.01
    dr, dc = np.nonzero(dots)
    count = np.bincount((dr // block) * nb_c + (dc // block),
                        minlength=area_px.size).reshape(nb_r, -1).astype(np.float64)
    dens = np.divide(count, area_km2, out=np.zeros_like(count), where=area_km2 > 0)
    out = {}
    for s in sigmas:
        sm = gaussian_filter(dens, s, mode="constant")
        out[f"cv_density_smoothed_{s:g}blocks"] = float(
            sm.ravel()[eligible].std() / sm.ravel()[eligible].mean())
    return out


def nearest_neighbour_px(rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    pts = np.column_stack([rows, cols]).astype(np.float64)
    if pts.shape[0] < 2:
        return np.zeros(pts.shape[0])
    d, _ = cKDTree(pts).query(pts, k=2)
    return d[:, 1]


def choose_donors(parent, prior, bids, dist, n_drop, keep_one_per_block=True):
    """Coldest blocks first, one dot left behind in every donor block.

    The one-dot floor keeps the occupied-block count fixed, so the variant is a
    pure concentration test and not a disguised sparsification (PRUNE-lite).
    Collar dots (<= 3 px from the catalogue) are protected, so collar mass is
    inherited from R0 exactly.
    """
    rr, cc = np.nonzero(parent)
    nn = nearest_neighbour_px(rr, cc)
    pr = prior[bids[rr, cc]]
    ok = dist[rr, cc] > COLLAR_PX
    order = np.lexsort((cc, rr, -nn, pr))             # cold -> isolated -> row/col
    blk = bids[rr, cc]
    counts = np.bincount(blk, minlength=prior.size)
    taken = np.zeros(prior.size, np.int32)
    sel = []
    for idx in order[ok[order]]:
        b = int(blk[idx])
        if keep_one_per_block and taken[b] >= counts[b] - 1:
            continue
        taken[b] += 1
        sel.append(int(idx))
        if len(sel) == n_drop:
            break
    assert len(sel) == n_drop, f"donor pool too small: {len(sel)} < {n_drop}"
    sel = np.array(sel)
    return rr[sel], cc[sel], nn[sel], pr[sel]


def choose_receivers(survivor, forbidden, allowed, prior, bids, n_add):
    """8-neighbour sites of surviving dots, hottest block first, capped per host."""
    srr, scc = np.nonzero(survivor)
    tree = cKDTree(np.column_stack([srr, scc]).astype(np.float64))
    h, w = survivor.shape
    cand = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = srr + dr, scc + dc
            m = (nr >= 0) & (nr < h) & (nc >= 0) & (nc < w)
            cand.append(np.column_stack([nr[m], nc[m]]))
    cand = np.unique(np.vstack(cand), axis=0)
    cand = cand[allowed[cand[:, 0], cand[:, 1]] & ~forbidden[cand[:, 0], cand[:, 1]]]
    dhost, host = tree.query(cand.astype(np.float64), k=1)
    pr = prior[bids[cand[:, 0], cand[:, 1]]]
    order = np.lexsort((cand[:, 1], cand[:, 0], dhost, -pr))
    used: dict[int, int] = {}
    chosen = []
    for idx in order:
        hidx = int(host[idx])
        if used.get(hidx, 0) >= CAP_PER_HOST:
            continue
        used[hidx] = used.get(hidx, 0) + 1
        chosen.append(int(idx))
        if len(chosen) == n_add:
            break
    if len(chosen) < n_add:
        raise RuntimeError(f"receiver sites exhausted: {len(chosen)} < {n_add}")
    pick = cand[np.array(chosen)]
    sel = np.array(chosen)
    return pick[:, 0], pick[:, 1], dhost[sel], pr[sel]


def write_pair(arr_bool, footprint, profile, base: Path) -> dict:
    h, w = footprint.shape
    nan_arr = np.full((h, w), np.nan, dtype=np.float32)
    nan_arr[footprint] = arr_bool[footprint].astype(np.float32)
    zero_arr = np.zeros((h, w), dtype=np.float32)
    zero_arr[footprint] = arr_bool[footprint].astype(np.float32)
    out: dict = {}
    for arr, suffix, nodata, key in ((nan_arr, "", float("nan"), "nan"),
                                     (zero_arr, "-zeros", None, "zeros")):
        p = base.with_name(base.name + suffix + ".tif")
        prof = profile.copy()
        prof.update(driver="GTiff", dtype="float32", count=1, compress="lzw",
                    tiled=False, nodata=nodata)
        with rasterio.open(p, "w", **prof) as dst:
            dst.write(arr, 1)
        with rasterio.open(p) as src:
            back = src.read(1)
        inside = back[footprint]
        assert np.isfinite(inside).all() and set(np.unique(inside)) <= {0.0, 1.0}
        if nodata is None:
            assert (back[~footprint] == 0).all()
        else:
            assert np.isnan(back[~footprint]).all()
        out[key] = {"n_dots": int((back > 0).sum())}
        zp = p.with_suffix(".zip")
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.write(p, arcname=p.name)
        out[key].update(path=p, zip_path=zp)
    return out


def main() -> int:
    RELEASES.mkdir(exist_ok=True)
    footprint, catalogue, dist, parent, profile = load_inputs()
    n_parent = int(parent.sum())
    allowed3 = footprint & (dist > COLLAR_PX) & ~catalogue
    parent_nn = nearest_neighbour_px(*np.nonzero(parent))

    report: dict = {
        "schema_version": 1,
        "axis": "CONCENTRATION",
        "parent": {"id": PARENT_ID, "sha256": PARENT_SHA, "n_dots": n_parent},
        "parameters": {
            "block_sizes_px": [10, 50],
            "prior_sigma_blocks": 2.0,
            "min_block_area_frac": MIN_BLOCK_AREA_FRAC,
            "cap_per_host": CAP_PER_HOST,
            "collar_px": COLLAR_PX,
            "rng_used": False,
            "determinism": "all orderings terminate in (row, col); no random draws",
        },
        "grid": {"footprint_px": int(footprint.sum()), "catalogue_px": int(catalogue.sum())},
        "parent_stats": {
            "mean_nearest_neighbour_px": float(parent_nn.mean()),
            "median_nearest_neighbour_px": float(np.median(parent_nn)),
            "dots_within_3px_catalogue": int((dist[parent] <= 3).sum()),
            "cv_ladder": {},
        },
        "provenance": {
            "git_sha": git_sha(),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "script": "scripts/make_concentration_variants.py",
            "inputs_sha256": {
                "sample_submission.tif": PIN_SAMPLE,
                "existing_faults.tif": PIN_EXISTING,
                "h33_education.tif": PARENT_SHA,
            },
        },
        "variants": {},
    }

    report["parent_stats"]["smoothed_density_cv"] = smoothed_density_cv(parent, footprint)

    # CV ladder for the parent, so the brief's 0.51-0.59 band can be located
    for b in CV_LADDER_PX:
        prior_b, elig_b, nb_c_b = block_prior(parent, footprint, b, 2.0)
        report["parent_stats"]["cv_ladder"][f"{b}px"] = cv_stats(
            parent, footprint, prior_b, elig_b, block_ids(footprint.shape, b, nb_c_b))

    ledger_rows = []
    for tag, frac, block, sigma in CONFIGS:
        prior, eligible, nb_c = block_prior(parent, footprint, block, sigma)
        bids = block_ids(footprint.shape, block, nb_c)
        base = cv_stats(parent, footprint, prior, eligible, bids)
        n_move = int(round(frac * n_parent))

        d_r, d_c, d_nn, d_pr = choose_donors(parent, prior, bids, dist, n_move)
        survivor = parent.copy()
        survivor[d_r, d_c] = False
        r_r, r_c, r_dh, r_pr = choose_receivers(
            survivor, parent, allowed3, prior, bids, n_move)
        variant = survivor.copy()
        variant[r_r, r_c] = True
        assert int(variant.sum()) == n_parent
        assert int((variant & catalogue).sum()) == 0
        assert float(dist[variant].min()) > 2.0

        stats = cv_stats(variant, footprint, prior, eligible, bids)
        nn_after = nearest_neighbour_px(*np.nonzero(variant))
        pc = np.bincount(bids[parent], minlength=prior.size)
        vc = np.bincount(bids[variant], minlength=prior.size)
        diff = {
            "n_dots": int(variant.sum()),
            "n_moved": int(n_move),
            "pct_of_parent_dots_moved": float(100.0 * n_move / n_parent),
            "n_added": int(len(r_r)),
            "n_removed": int(len(d_r)),
            "dots_within_2px_catalogue": int((dist[variant] <= 2).sum()),
            "dots_within_3px_catalogue": int((dist[variant] <= 3).sum()),
            "removed_nn_px_mean": float(d_nn.mean()),
            "removed_nn_px_quantiles": [float(np.quantile(d_nn, q)) for q in (0.1, 0.5, 0.9)],
            "removed_block_prior_mean": float(d_pr.mean()),
            "added_block_prior_mean": float(r_pr.mean()),
            "added_distance_to_host_px_mean": float(r_dh.mean()),
            "added_distance_to_host_px_max": float(r_dh.max()),
            "variant_nn_px_mean": float(nn_after.mean()),
            "variant_nn_px_median": float(np.median(nn_after)),
            "parent_overlap_fraction": float((variant & parent).sum() / n_parent),
            "block_stats_before": base,
            "block_stats_after": stats,
            "cv_occupied_delta": stats["cv_occupied_blocks"] - base["cv_occupied_blocks"],
            "mass_share_top1pct_delta": (
                stats["mass_share_in_top1pct_prior_blocks"]
                - base["mass_share_in_top1pct_prior_blocks"]),
            "blocks_emptied": int(((pc > 0) & (vc == 0)).sum()),
            "blocks_gained": int(((pc == 0) & (vc > 0)).sum()),
            "cv_ladder_after": {},
            "smoothed_density_cv_after": smoothed_density_cv(variant, footprint),
        }
        for b in CV_LADDER_PX:
            prior_b, elig_b, nb_c_b = block_prior(parent, footprint, b, 2.0)
            diff["cv_ladder_after"][f"{b}px"] = cv_stats(
                variant, footprint, prior_b, elig_b, block_ids(footprint.shape, b, nb_c_b))

        base_name = f"{PARENT_ID}-CONC{tag}-{DATE_STR}"
        written = write_pair(variant, footprint, profile, RELEASES / base_name)
        sha8 = sha256(written["nan"]["path"])[:8]
        final_paths = {
            "nan": RELEASES / f"{base_name}-{sha8}.tif",
            "zeros": RELEASES / f"{base_name}-{sha8}-zeros.tif",
        }
        for key, final in final_paths.items():
            written[key]["path"].replace(final)
            cmd_zip = final.with_suffix(".zip")
            written[key]["zip_path"].replace(cmd_zip)
            written[key].update(
                path=str(final.relative_to(ROOT)),
                sha256=sha256(final),
                zip_path=str(cmd_zip.relative_to(ROOT)),
                zip_sha256=sha256(cmd_zip),
            )
        # gate: re-read from disk after writes and renames
        with rasterio.open(ROOT / written["nan"]["path"]) as src:
            back_nan = src.read(1)
            meta = {"crs": str(src.crs), "shape": list(src.shape), "dtype": src.dtypes[0],
                    "count": src.count, "transform": list(src.transform)[:6]}
        with rasterio.open(ROOT / written["zeros"]["path"]) as src:
            back_zero = src.read(1)
        assert int((back_nan[footprint] > 0).sum()) == n_parent
        assert bool(np.isnan(back_nan[~footprint]).all())
        assert bool((back_zero[~footprint] == 0).all())
        assert int(((back_nan > 0) & catalogue).sum()) == 0
        assert np.array_equal(np.nan_to_num(back_nan, nan=0.0), back_zero)

        vid = final_paths["nan"].name
        written.update(diff_stats=diff, id=vid, meta=meta)
        report["variants"][vid] = written
        ledger_rows.append({
            "id": vid, "parent": PARENT_ID, "axis": "CONCENTRATION", "value": tag,
            "n_dots": n_parent, "pct_changed": f"{100.0 * n_move / n_parent:.2f}",
            "sha256": written["nan"]["sha256"],
            "sha256_zeros": written["zeros"]["sha256"],
            "status": "BUILT", "predicted_change": "PENDING",
            "receipt_score": "", "receipt_date": "",
            "description": (
                f"Move {n_move} dots ({100 * frac:.0f}%) from coldest to hottest {block}px "
                f"({block / 10:g} km) blocks (prior = {sigma:g}-block smoothed parent density); "
                f"count fixed; CV_occ {base['cv_occupied_blocks']:.3f}->"
                f"{stats['cv_occupied_blocks']:.3f}; CV_all {base['cv_all_eligible_blocks']:.3f}->"
                f"{stats['cv_all_eligible_blocks']:.3f}."),
        })
        print(
            f"{vid}  moved={n_move}  CV_occ {base['cv_occupied_blocks']:.3f}->"
            f"{stats['cv_occupied_blocks']:.3f}  CV_all {base['cv_all_eligible_blocks']:.3f}->"
            f"{stats['cv_all_eligible_blocks']:.3f}  top1% "
            f"{base['mass_share_in_top1pct_prior_blocks']:.3f}->"
            f"{stats['mass_share_in_top1pct_prior_blocks']:.3f}  "
            f"blocks {base['occupied_blocks']}->{stats['occupied_blocks']}  "
            f"sha {written['nan']['sha256'][:8]}")

    (ROOT / "registry" / "concentration_report.json").write_text(
        json.dumps(report, indent=2) + "\n")
    work = ROOT / "data" / "work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "concentration_rows.json").write_text(json.dumps(ledger_rows, indent=2) + "\n")
    print("wrote registry/concentration_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
