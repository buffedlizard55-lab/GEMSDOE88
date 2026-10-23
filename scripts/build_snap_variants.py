#!/usr/bin/env python3
"""AXIS = SNAP: relocate each R0 dot <=w px onto the strongest potential-field edge.

One change from a named parent, one axis. The parent is the hash-pinned R0
(``c55bafc4...``, 37,654 binary dots). Each variant moves dots *within* a
w-pixel window onto the local maximum of a potential-field edge response. The
dot count is held exactly constant and no dot is allowed to land on the
catalogue or inside the 3 px kernel haloes.

Three variants (one axis, three values):

* ``SNAPw2E1`` -- window <= 2 px, edge response E1 = robust-z(|grad rtp|) +
  robust-z(|grad iso_grav_anom|) (recomputed gradient magnitude of the magnetic
  and isostatic-gravity bands, 1 px Gaussian pre-smoothing).
* ``SNAPw2S2`` -- window <= 2 px, E1s = the same operator smoothed at sigma =
  2 px (a 200 m structural edge) with a gain gate (move only if the destination
  beats the source by > 0.25 robust-z). This is the noise-chasing control: if
  the literal arm fails because pixel-scale detector maxima are noise, the
  structural arm should lose less.
* ``SNAPw2E2`` -- window <= 2 px, edge response E2 = sum of robust-z of the
  *organizer-provided* derivative bands 3 (tmi_hg), 9 (tmi_vg), 18
  (iso_grav_anom_hg). No gradients are recomputed, so the operator differs from
  E1 even though the physical target is the same.

A fourth arm (window = 1 px) was designed as a dose control and is NOT built:
every arm already saturates its window (mean displacement 1.82 px of 2 px), so a
1 px arm would measure pixel noise rather than dose.

Mechanism: fault-parallel basement steps appear in magnetic/gravity data as
horizontal-gradient maxima (a "magmatic/structural edge"), but GeoDAWN Area 2
was flown at 400 m line spacing and 150-200 m drape, so the potential-field edge
maximum can sit 1-3 px off the mapped trace (brief §2; USGS GeoDAWN Area 2
metadata). A <=2 px snap therefore re-centres dots on the geophysical anomaly
rather than on the (uncertain) mapped position.

Gates (brief §6 MUST-pass) are re-derived from the bytes on disk after writing;
PROXY instruments (catalogue hide-and-recover, SGMC control, block-density CV)
are reported and never gate.

Usage::

    python scripts/build_snap_variants.py            # build + write receipts
    python scripts/build_snap_variants.py --explore  # diagnostics only, no writes
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout, gates, grid as grid_mod, holdout as holdout_mod, metric, validate  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
PARENT_SHA_ZEROS = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
PARENT_SHA_NAN = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
FEATURES_SHA = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
SAMPLE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
CATALOGUE_SHA = "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"

SEED = 20261023
FIXED_DATE = "20261023"
MIN_DCAT = 3.0          # px; destinations must clear the 300 m kernel halo

DATA = ROOT / "data"
BRIDGE = DATA / "bridge"
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"


# ---------------------------------------------------------------------------
# 1. Pinned inputs
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:                                   # pragma: no cover
        return "unknown"


def verify_pins() -> dict[str, Path]:
    pins = {
        "parent_r0_zeros": (DATA / "registry" / "h33_education.tif", PARENT_SHA_ZEROS),
        "sample_submission": (BRIDGE / "sample_submission.tif", SAMPLE_SHA),
        "existing_faults": (BRIDGE / "existing_faults.tif", CATALOGUE_SHA),
        "training_features": (DATA / "training_features.tif", FEATURES_SHA),
    }
    out: dict[str, Path] = {}
    for name, (path, want) in pins.items():
        if not path.is_file():
            raise SystemExit(f"MISSING pinned input {name}: {path}")
        got = sha256_file(path)
        if got != want:
            raise SystemExit(f"SHA-256 MISMATCH {name}: {got} != {want}")
        out[name] = path
        print(f"      PIN OK {name:<20} {got[:12]}...")
    return out


# ---------------------------------------------------------------------------
# 2. Edge responses
# ---------------------------------------------------------------------------

def _fill_nonfinite(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Replace the -3.4e38 float32 sentinels (outside-footprint only) with a median."""
    a = a.astype(np.float64, copy=True)
    bad = ~np.isfinite(a) | (a < -1e30)
    if bad.any():
        a[bad] = np.median(a[foot])
    return a


def _robust_z(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    v = a[foot]
    med = np.median(v)
    iqr = np.percentile(v, 75) - np.percentile(v, 25)
    return (a - med) / max(iqr, 1e-12)


def _gradmag(a: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    sm = gaussian_filter(a, sigma)
    gy, gx = np.gradient(sm)
    return np.hypot(gx, gy)


def build_edge_fields(path: Path, foot: np.ndarray, sigma_struct: float = 2.0) -> dict[str, np.ndarray]:
    """E1 = recomputed |grad| of rtp + isostatic gravity; E2 = provided derivative bands."""
    with rasterio.open(path) as src:
        rtp = _fill_nonfinite(src.read(2), foot)        # band 2  rtp
        igrav = _fill_nonfinite(src.read(13), foot)     # band 13 iso_grav_anom
        tmi_hg = _fill_nonfinite(src.read(3), foot)     # band 3  tmi_hg
        tmi_vg = _fill_nonfinite(src.read(9), foot)     # band 9  tmi_vg
        igrav_hg = _fill_nonfinite(src.read(18), foot)  # band 18 iso_grav_anom_hg

    e1 = (_robust_z(_gradmag(rtp), foot) + _robust_z(_gradmag(igrav), foot)).astype(np.float32)
    # E1s: the same operator at a 2 px (200 m) smoothing scale, i.e. a structural
    # edge rather than a 1 px detector maximum. Used by the coherence-gated arm.
    e1s = (_robust_z(_gradmag(rtp, sigma_struct), foot)
           + _robust_z(_gradmag(igrav, sigma_struct), foot)).astype(np.float32)
    e2 = (np.abs(_robust_z(gaussian_filter(tmi_hg, 1.0), foot))
          + np.abs(_robust_z(gaussian_filter(tmi_vg, 1.0), foot))
          + np.abs(_robust_z(gaussian_filter(igrav_hg, 1.0), foot))).astype(np.float32)
    return {"E1": e1, "E1s": e1s, "E2": e2}


# ---------------------------------------------------------------------------
# 3. The snap itself
# ---------------------------------------------------------------------------

def _offsets(max_disp: int) -> list[tuple[int, int, float]]:
    offs = []
    for dy in range(-max_disp, max_disp + 1):
        for dx in range(-max_disp, max_disp + 1):
            r = float(np.hypot(dy, dx))
            if 0.0 < r <= max_disp:
                offs.append((dy, dx, r))
    offs.sort(key=lambda t: (t[2], t[0], t[1]))
    return offs


def snap(mask: np.ndarray, edge: np.ndarray, foot: np.ndarray, catalogue: np.ndarray,
         d_cat: np.ndarray, max_disp: int, min_dcat: float = MIN_DCAT,
         gain_min: float = 0.0) -> dict:
    """Move each dot to the highest-edge pixel within <=max_disp px.

    Rules (all deterministic, seed-free):
      * destination inside the footprint, off catalogue, ``d_cat > min_dcat``;
      * destination must be empty (never land on another dot) -> count is fixed;
      * only strict edge-gain moves are made; ties pick the shortest displacement,
        then the smallest (dy, dx);
      * proposals are committed in descending gain, so a contested destination
        goes to the dot that gains most.
    """
    H, W = mask.shape
    dest_ok = foot & ~catalogue & (d_cat > min_dcat)
    ys, xs = np.nonzero(mask)
    src_edge = edge[ys, xs]
    offs = _offsets(max_disp)

    proposals: list[tuple[float, int, int, int, int]] = []
    for i, (y, x) in enumerate(zip(ys.tolist(), xs.tolist())):
        best_val = src_edge[i]
        best: tuple[int, int] | None = None
        for dy, dx, _r in offs:
            yy, xx = y + dy, x + dx
            if not (0 <= yy < H and 0 <= xx < W):
                continue
            if not dest_ok[yy, xx] or mask[yy, xx]:
                continue
            v = edge[yy, xx]
            if v > best_val:                     # strict improvement only
                best_val = float(v)
                best = (yy, xx)
        if best is not None and (best_val - float(src_edge[i])) > gain_min:
            proposals.append((best_val - float(src_edge[i]), int(y), int(x), best[0], best[1]))

    proposals.sort(key=lambda t: (-t[0], t[1], t[2]))
    claimed: set[tuple[int, int]] = set()
    new_mask = mask.copy()
    moves: list[tuple[int, int, int, int, float]] = []
    for gain, y, x, yy, xx in proposals:
        if (yy, xx) in claimed:
            continue
        claimed.add((yy, xx))
        new_mask[y, x] = False
        new_mask[yy, xx] = True
        moves.append((y, x, yy, xx, gain))

    assert int(new_mask.sum()) == int(mask.sum()), "SNAP must hold the dot count fixed"
    return {
        "mask": new_mask,
        "n_proposed": len(proposals),
        "n_moved": len(moves),
        "moves": moves,
        "max_disp": max_disp,
        "min_dcat": min_dcat,
    }


# ---------------------------------------------------------------------------
# 4. Report-only instruments (never gates)
# ---------------------------------------------------------------------------

def block_cv(mask: np.ndarray, foot: np.ndarray, block_px: int) -> float:
    H, W = foot.shape
    Hs, Ws = (H // block_px) * block_px, (W // block_px) * block_px
    fb = foot[:Hs, :Ws].reshape(Hs // block_px, block_px, Ws // block_px, block_px).sum(axis=(1, 3))
    interior = fb == block_px * block_px
    ab = mask[:Hs, :Ws].reshape(Hs // block_px, block_px, Ws // block_px, block_px).sum(axis=(1, 3))
    dens = ab[interior] / fb[interior]
    return float(dens.std() / dens.mean())


def sgmc_control(mask: np.ndarray, foot: np.ndarray, catalogue: np.ndarray) -> dict:
    raw = rasterio.open(DATA / "external" / "derived_sgmc_faults_100m_u8.tif").read(1) > 0
    off = raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    res = metric.dti_binary(mask, off, valid=foot, known=catalogue)
    return {
        "evidence_label": "PROXY",
        "dti": round(float(res["dti"]), 6),
        "n_sgmc_off_catalogue_px": int(off.sum()),
        "tp": round(float(res["tp"]), 2),
        "fp": round(float(res["fp"]), 2),
    }


def holdout_proxy(arms: dict[str, np.ndarray], foot: np.ndarray, catalogue: np.ndarray) -> dict:
    """Catalogue hide-and-recover PROXY, reported per arm (never a gate)."""
    gd = grid_mod.load_grid(BRIDGE)
    folds = [*holdout_mod.buffered_component_draw(gd, seed=20)[0],
             *holdout_mod.buffered_component_draw(gd, seed=30)[0]]
    terms = {}
    for name, mask in arms.items():
        pred = mask.astype(np.float32)
        total = None
        for f in folds:
            _, t = evaluate_holdout.evaluate(pred, f, foot)
            total = t if total is None else total + t
        terms[name] = total
    key = "R0" if "R0" in arms else next(iter(arms))
    others = [k for k in arms if k != key]
    pooled = evaluate_holdout.pooled_summary(terms, draws=400, seed=520810, candidate=others[0])
    active = np.any(np.stack([a.sum(axis=1) > 0 for a in terms.values()]), axis=0)
    nb = int(active.sum())
    rng = np.random.default_rng(520810)
    picks = rng.integers(0, nb, size=(400, nb))
    base = evaluate_holdout.from_terms(terms[key][active][picks].sum(axis=1))
    out = {}
    for name in arms:
        boot = evaluate_holdout.from_terms(terms[name][active][picks].sum(axis=1))
        d = boot - base
        s = pooled["scores"][name]
        out[name] = {
            "evidence_label": "PROXY",
            "evaluator_version": evaluate_holdout.VERSION,
            "dti": round(float(s["dti"]), 6),
            "ci95": [round(float(x), 6) for x in s["ci95"]],
            "withheld_positives": int(s["withheld_positive_pixels"]),
            "paired_delta_vs_r0": round(float(s["dti"] - pooled["scores"][key]["dti"]), 6),
            "paired_delta_vs_r0_ci95": [round(float(x), 6) for x in np.quantile(d, [0.025, 0.975])],
        }
    return out


def edge_percentiles(edge: np.ndarray, foot: np.ndarray, masks: dict[str, np.ndarray]) -> dict:
    ref = np.sort(edge[foot])
    out = {}
    for name, m in masks.items():
        vals = edge[m]
        pct = np.searchsorted(ref, vals) / ref.size
        out[name] = {"mean_percentile": round(float(pct.mean()), 4),
                     "median_percentile": round(float(np.median(pct)), 4)}
    return out


# ---------------------------------------------------------------------------
# 5. Writer + MUST-pass gates re-read from disk
# ---------------------------------------------------------------------------

def write_variant(mask, foot, catalogue, sample_path, parent_mask, value, note,
                  existing_shas: set[str]) -> dict:
    with rasterio.open(sample_path) as tpl:
        base = tpl.profile.copy()
        ref_tuple = (tpl.shape, tpl.crs, tpl.transform)

    prof_nan = base.copy()
    prof_nan.update(driver="GTiff", dtype="float32", count=1, compress="deflate",
                    predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256,
                    nodata=np.nan)
    prof_zeros = prof_nan.copy()
    prof_zeros.update(nodata=None)

    arr_nan = np.where(foot, mask.astype(np.float32), np.nan).astype(np.float32)
    arr_zeros = np.where(foot, mask.astype(np.float32), 0.0).astype(np.float32)

    prefix = f"{PARENT_ID}-SNAP{value}-{FIXED_DATE}"
    tmp_nan = RELEASES / f".tmp-{prefix}.tif"
    tmp_zeros = RELEASES / f".tmp-{prefix}-zeros.tif"
    with rasterio.open(tmp_nan, "w", **prof_nan) as dst:
        dst.write(arr_nan, 1)
    with rasterio.open(tmp_zeros, "w", **prof_zeros) as dst:
        dst.write(arr_zeros, 1)

    sha_nan = sha256_file(tmp_nan)
    sha_zeros = sha256_file(tmp_zeros)
    if sha_nan in existing_shas or sha_zeros in existing_shas:
        tmp_nan.unlink(missing_ok=True)
        tmp_zeros.unlink(missing_ok=True)
        raise RuntimeError(f"Duplicate SHA-256 already in ledger: {sha_nan}")
    vid = f"{prefix}-{sha_nan[:8]}"
    final_nan = RELEASES / f"{vid}.tif"
    final_zeros = RELEASES / f"{vid}-zeros.tif"
    tmp_nan.replace(final_nan)
    tmp_zeros.replace(final_zeros)

    zips = {}
    for tif_p in (final_nan, final_zeros):
        zp = tif_p.with_suffix(".zip")
        with zipfile.ZipFile(zp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(tif_p, arcname=tif_p.name)
        zips[tif_p.name] = sha256_file(zp)

    # --- MUST-PASS re-read from disk -------------------------------------
    with rasterio.open(final_nan) as ds:
        back = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform) == ref_tuple
        assert ds.count == 1 and ds.dtypes[0] == "float32" and str(ds.crs) == "EPSG:32611"
        assert np.isfinite(back[foot]).all()
        assert np.isnan(back[~foot]).all()
        assert 0.0 <= float(back[foot].min()) and float(back[foot].max()) <= 1.0
        assert int((back[catalogue] > 0.0).sum()) == 0
        assert np.array_equal(back[foot] > 0.5, mask[foot])
    with rasterio.open(final_zeros) as ds:
        bz = ds.read(1)
        assert np.isfinite(bz).all() and np.all(bz[~foot] == 0.0)
        assert int((bz[catalogue] > 0.0).sum()) == 0
        assert np.array_equal(bz[foot] > 0.5, mask[foot])
    assert gates.format_report(final_zeros, sample_path, footprint=foot)["ok"]
    assert validate.validate(final_zeros, foot, catalogue)["all_checks_passed"]

    d_cat = distance_transform_edt(~catalogue)
    dv = d_cat[mask]
    n_parent = int(parent_mask.sum())
    n_added = int((mask & ~parent_mask).sum())
    n_removed = int((parent_mask & ~mask).sum())
    assert len(note) <= 140, f"note too long ({len(note)}): {note}"

    receipt = {
        "id": vid,
        "parent": PARENT_ID,
        "parent_sha256_zeros": PARENT_SHA_ZEROS,
        "parent_sha256_nan": PARENT_SHA_NAN,
        "axis": "SNAP",
        "value": value,
        "seed": SEED,
        "git_sha": git_sha(),
        "file_nan": f"releases/{final_nan.name}",
        "sha256": sha_nan,
        "bytes_nan": final_nan.stat().st_size,
        "zip_nan": f"releases/{final_nan.with_suffix('.zip').name}",
        "zip_nan_sha256": zips[final_nan.name],
        "file_zeros": f"releases/{final_zeros.name}",
        "sha256_zeros": sha_zeros,
        "bytes_zeros": final_zeros.stat().st_size,
        "zip_zeros": f"releases/{final_zeros.with_suffix('.zip').name}",
        "zip_zeros_sha256": zips[final_zeros.name],
        "form_note": note,
        "form_note_chars": len(note),
        "n_dots": int(mask.sum()),
        "parent_diff": {
            "n_parent": n_parent,
            "n_added": n_added,
            "n_removed": n_removed,
            "pct_changed_moved": round(100.0 * n_removed / n_parent, 2),
            "pct_changed_sym_diff": round(100.0 * (n_added + n_removed) / n_parent, 2),
            "min_dist_catalogue_px": round(float(dv.min()), 4),
            "dots_le_1px": int((dv <= 1.0).sum()),
            "dots_le_2px": int((dv <= 2.0).sum()),
            "dots_le_3px": int((dv <= 3.0).sum()),
            "dots_le_4px": int((dv <= 4.0).sum()),
        },
        "gates": {
            "crs_epsg_32611": True, "shape_3730x3292": True, "transform_match": True,
            "dtype_float32": True, "band_count_1": True, "values_in_0_1": True,
            "no_nan_inside_footprint": True, "nan_outside_footprint": True,
            "zeros_fallback_valid": True, "zero_catalogue_mass": True,
            "reread_from_disk_verified": True,
        },
    }
    (RELEASES / f"{vid}.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------

VARIANTS = [
    dict(value="w2E1", edge="E1", window=2, gain_min=0.0,
         note="h33-2-b2; SNAP<=2px to max |grad rtp+igrav|; 37654 held; pred -0.002 MODEL"),
    dict(value="w2S2", edge="E1s", window=2, gain_min=0.25,
         note="h33-2-b2; SNAP<=2px to 200m-scale edge, gain>=0.25z only; pred -0.001 MODEL"),
    dict(value="w2E2", edge="E2", window=2, gain_min=0.0,
         note="h33-2-b2; SNAP<=2px on organizer tmi/igrav derivative bands; pred -0.002 MODEL"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--explore", action="store_true", help="diagnostics only; write nothing")
    ap.add_argument("--skip-holdout", action="store_true")
    args = ap.parse_args()
    t0 = time.time()

    print("[1/6] Verifying pinned inputs...")
    pins = verify_pins()

    print("[2/6] Loading parent R0 and the pinned grid...")
    grid = grid_mod.load_grid(BRIDGE)
    foot, catalogue = grid.footprint, grid.catalogue
    with rasterio.open(pins["parent_r0_zeros"]) as src:
        r0 = src.read(1) > 0.5
    d_cat = distance_transform_edt(~catalogue)
    assert int(r0.sum()) == 37654
    assert int((r0 & catalogue).sum()) == 0
    assert int((d_cat[r0] <= 2.0).sum()) == 0
    print(f"      R0 {int(r0.sum()):,} dots | min d_cat {d_cat[r0].min():.3f} px | "
          f"collar 2-3 px {int(((d_cat[r0] > 2) & (d_cat[r0] <= 3)).sum()):,}")

    print("[3/6] Building edge responses E1, E2...")
    edges = build_edge_fields(pins["training_features"], foot)

    print("[4/6] Snapping...")
    results, masks = {}, {"R0": r0}
    for spec in VARIANTS:
        res = snap(r0, edges[spec["edge"]], foot, catalogue, d_cat, spec["window"],
                   gain_min=spec.get("gain_min", 0.0))
        masks[spec["value"]] = res["mask"]
        moves = np.array([(m[0], m[1], m[2], m[3]) for m in res["moves"]], float)
        gains = np.array([m[4] for m in res["moves"]], float)
        disp = np.hypot(moves[:, 0] - moves[:, 2], moves[:, 1] - moves[:, 3]) if len(moves) else np.array([0.0])
        dv = d_cat[res["mask"]]
        results[spec["value"]] = dict(
            value=spec["value"], edge=spec["edge"], window=spec["window"],
            gain_min=spec.get("gain_min", 0.0),
            n_dots=int(res["mask"].sum()),
            n_moved=int(res["n_moved"]),
            pct_moved=round(100.0 * res["n_moved"] / int(r0.sum()), 2),
            n_proposed=int(res["n_proposed"]),
            mean_displacement_px=round(float(disp.mean()), 3),
            median_displacement_px=round(float(np.median(disp)), 3),
            max_displacement_px=round(float(disp.max()), 3),
            mean_edge_gain=round(float(gains.mean()), 4) if len(gains) else 0.0,
            min_dist_catalogue_px=round(float(dv.min()), 4),
            dots_le_2px=int((dv <= 2.0).sum()),
            dots_le_3px=int((dv <= 3.0).sum()),
            collar_dots_2_3px=int(((dv > 2) & (dv <= 3)).sum()),
        )
        print(f"      {spec['value']}: moved {results[spec['value']]['n_moved']:,} "
              f"({results[spec['value']]['pct_moved']}%) | mean disp "
              f"{results[spec['value']]['mean_displacement_px']} px | "
              f"collar now {results[spec['value']]['collar_dots_2_3px']:,}")

    print("[5/6] Report-only PROXY instruments...")
    diag = {"edge_percentiles": {k: edge_percentiles(edges[k], foot, masks) for k in edges}}
    for name, m in masks.items():
        diag.setdefault("sgmc_control", {})[name] = sgmc_control(m, foot, catalogue)
        diag.setdefault("block_density_cv", {})[name] = {
            "cv_10km_100px_interior": round(block_cv(m, foot, 100), 4),
            "cv_12km_120px_interior": round(block_cv(m, foot, 120), 4),
        }
    if not args.skip_holdout:
        diag["holdout_proxy"] = holdout_proxy(masks, foot, catalogue)

    for spec in VARIANTS:
        v = spec["value"]
        results[v]["sgmc_control"] = diag["sgmc_control"][v]
        results[v]["sgmc_delta_vs_r0"] = round(
            diag["sgmc_control"][v]["dti"] - diag["sgmc_control"]["R0"]["dti"], 6)
        results[v]["block_density_cv"] = diag["block_density_cv"][v]
        results[v]["edge_percentile_before"] = diag["edge_percentiles"][spec["edge"]]["R0"]
        results[v]["edge_percentile_after"] = diag["edge_percentiles"][spec["edge"]][v]
        if "holdout_proxy" in diag:
            results[v]["holdout_proxy"] = diag["holdout_proxy"][v]
        print(f"      {v}: SGMC {results[v]['sgmc_control']['dti']:.5f} "
              f"(delta {results[v]['sgmc_delta_vs_r0']:+.5f}) | "
              f"CV12km {results[v]['block_density_cv']['cv_12km_120px_interior']:.4f} | "
              f"E-pct {results[v]['edge_percentile_before']['mean_percentile']:.3f} -> "
              f"{results[v]['edge_percentile_after']['mean_percentile']:.3f}")

    out = {"axis": "SNAP", "parent": PARENT_ID, "seed": SEED,
           "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "git_sha": git_sha(), "variants": results,
           "r0": {"n_dots": int(r0.sum()),
                  "min_dist_catalogue_px": round(float(d_cat[r0].min()), 4),
                  "collar_dots_2_3px": int(((d_cat[r0] > 2) & (d_cat[r0] <= 3)).sum()),
                  "sgmc_control": diag["sgmc_control"]["R0"],
                  "block_density_cv": diag["block_density_cv"]["R0"]}}
    (ROOT / "registry" / "snap_analysis.json").write_text(json.dumps(out, indent=2) + "\n")

    if args.explore:
        print("[6/6] --explore: nothing written to releases/ or ledger/")
        return 0

    print("[6/6] Writing rasters, receipts, ledger rows, mechanism cards...")
    existing = {PARENT_SHA_ZEROS, PARENT_SHA_NAN}
    if LEDGER.is_file():
        with LEDGER.open(newline="") as f:
            for row in csv.DictReader(f):
                for col in ("sha256", "sha256_zeros"):
                    if row.get(col):
                        existing.add(row[col])
    receipts = {}
    for spec in VARIANTS:
        v = spec["value"]
        receipts[v] = write_variant(masks[v], foot, catalogue, BRIDGE / "sample_submission.tif",
                                    r0, v, spec["note"], existing)
        existing.add(receipts[v]["sha256"])
        existing.add(receipts[v]["sha256_zeros"])
        print(f"      {receipts[v]['id']}  {receipts[v]['sha256'][:12]}")
    for spec in VARIANTS:
        v = spec["value"]
        rec = receipts[v]
        with (RELEASES / f"{rec['id']}.json").open() as f:
            body = json.load(f)
        body["report_only_diagnostics"] = {
            k: results[v][k] for k in
            ("sgmc_control", "sgmc_delta_vs_r0", "block_density_cv",
             "edge_percentile_before", "edge_percentile_after", "holdout_proxy")
            if k in results[v]
        }
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(body, indent=2) + "\n")

    append_ledger(results, receipts)
    update_mechanism_cards(results, receipts)
    print(f"done in {time.time() - t0:.1f}s")
    return 0


LEDGER_FIELDS = ["id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256",
                 "sha256_zeros", "status", "predicted_change", "predicted_range",
                 "ranking_basis", "receipt_score", "receipt_date", "description",
                 "recommendation"]

PREDICTION = {
    "w2E1": ("MODEL:-0.002", "[-0.010,+0.006]"),
    "w2S2": ("MODEL:-0.001", "[-0.009,+0.007]"),
    "w2E2": ("MODEL:-0.002", "[-0.010,+0.006]"),
}


def append_ledger(results: dict, receipts: dict) -> None:
    rows = []
    if LEDGER.is_file():
        with LEDGER.open(newline="") as f:
            # Only this family's rows are replaced; a second SNAP family on parent
            # R1 = PRUNEp3px lives in scripts/build_snap_r1_variants.py (IR-88-29).
            rows = [
                r for r in csv.DictReader(f)
                if not (r.get("axis") == "SNAP" and r.get("parent") == PARENT_ID)
            ]
    for v, rec in receipts.items():
        r = results[v]
        pred, rng = PREDICTION[v]
        rows.append({
            "id": rec["id"], "parent": PARENT_ID, "axis": "SNAP", "value": v,
            "n_dots": rec["n_dots"], "pct_changed": f"{r['pct_moved']}",
            "sha256": rec["sha256"], "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT", "predicted_change": pred, "predicted_range": rng,
            "ranking_basis": (f"edge {r['edge']} local argmax within {r['window']} px; "
                              "no ranking model used (count held)"),
            "receipt_score": "", "receipt_date": "",
            "description": (f"Move {r['n_moved']} of 37654 dots <= {r['window']} px to the local "
                            f"maximum of {r['edge']} (mean displacement "
                            f"{r['mean_displacement_px']} px, edge percentile "
                            f"{r['edge_percentile_before']['mean_percentile']} -> "
                            f"{r['edge_percentile_after']['mean_percentile']}); destinations "
                            f">3 px from catalogue."),
            "recommendation": ("HOLD: diagnostic axis, negative PROXY (SGMC blind-fault delta "
                               f"{r['sgmc_delta_vs_r0']:+.5f}); only a live slot if the human wants "
                               "the axis retired with a receipt."),
        })
    with LEDGER.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in LEDGER_FIELDS})


CARDS = {
    "w2E1": {
        "hypothesis": "R0's dots sit on the H19-5 ridge field, not on the geophysical anomaly; moving each dot at most 2 px onto the local maximum of the magnetic/gravity gradient magnitude re-centres it on the basement step a new fault actually produces, and DTI inside the 300 m kernel pays for that re-centring.",
        "mechanism": "Fault-parallel basement offset -> density and susceptibility contrast -> horizontal-gradient maximum of rtp magnetics and isostatic gravity. GeoDAWN Area 2 was flown at 400 m line spacing and 150-200 m drape (https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7), so a potential-field edge maximum can sit 1-3 px off the mapped trace. The dot count is held fixed, so any change is credit-only (T and M), never mass.",
        "non_fault_mimic": "Basalt-flow margins, Lake Lahontan shorelines and welded-tuff caprock boundaries produce gradient maxima with no Quaternary fault; E-W GeoDAWN flight-line corrugation is a pixel-scale artefact, which is why both fields are pre-smoothed before differencing.",
        "predicted_sign_size": "A-priori +0.004. Post-build the paired SGMC blind-fault PROXY fell 0.00796, so the shipped MODEL prediction is -0.002 (range [-0.010, +0.006]): the SGMC delta attenuated by ~0.25 because SGMC is compiled at a different scale from the scored new-fault truth. Below the 0.01 evidence bar either way.",
        "falsifier": "A live change of +0.01 or more (recovering the lost blind-fault proximity) falsifies the negative PROXY; a live change between -0.01 and +0.01 confirms SNAP is not a lever at this window, which retires the axis for the remaining slots.",
    },
    "w2S2": {
        "hypothesis": "The negative SGMC result for w2E1 is noise-chasing, not a failure of the edge idea: at 1 px smoothing the within-window maximum is dominated by pixel-scale detector noise, so the same snap on a 200 m-scale edge, gated to moves with a real gain (>= 0.25 robust-z), should keep whatever structural signal exists.",
        "mechanism": "Gaussian smoothing at sigma = 2 px (200 m) suppresses single-pixel corrugation while leaving basement-step gradients 200-600 m wide intact. The gain gate then only moves a dot when the destination is a distinct local maximum rather than a marginal noisy neighbour, which is why 52% rather than 95% of dots move.",
        "non_fault_mimic": "Smoothing also smears adjacent parallel lineaments together, so a dot can be dragged onto the wrong strand of a fault zone; alluvial-fan surface breaks still produce edges at this scale.",
        "predicted_sign_size": "MODEL -0.001 (range [-0.009, +0.007]): half of the w2E1 blind-fault loss, consistent with the measured SGMC delta of -0.00396 vs -0.00796, so most but not all of the w2E1 damage is pixel noise.",
        "falsifier": "If w2S2 scores below w2E1 live, the noise hypothesis is wrong and the loss comes from leaving the parent's ridge geometry, not from edge noise; if it scores above w2E1 by more than 0.01 the edge idea survives and a coherence-weighted SNAP deserves a slot.",
    },
    "w2E2": {
        "hypothesis": "The operator choice does not matter: the organizer's own derivative bands should give the same result as a recomputed gradient if the effect (negative or positive) is physical rather than an artefact of my smoothing.",
        "mechanism": "Bands 3 (tmi_hg), 9 (tmi_vg) and 18 (iso_grav_anom_hg) are already first derivatives, so their magnitudes peak over the same basement steps as E1 while skipping a second differencing step. Robust z-scores make the three bands scale-free before summing.",
        "non_fault_mimic": "Vertical-gradient bands amplify shallow sources - alluvium thickness and topography - more than deep basement steps, so E2 is expected to be more shallow-biased and more susceptible to fan-surface contacts than E1.",
        "predicted_sign_size": "MODEL -0.002 (range [-0.010, +0.006]); effectively identical to w2E1 (SGMC -0.00795 vs -0.00796), which is the point of the arm: the operator is not the lever.",
        "falsifier": "A live difference of 0.01 or more between w2E1 and w2E2 would show the derivative-band definition matters and make operator choice a live decision; near-equality retires it.",
    },
}

def update_mechanism_cards(results: dict, receipts: dict) -> None:
    path = ROOT / "ledger" / "mechanism_cards.json"
    cards = json.loads(path.read_text()) if path.is_file() else {}
    for v, rec in receipts.items():
        card = dict(CARDS[v])
        card["predicted_change"] = PREDICTION[v][0]
        card["predicted_range"] = PREDICTION[v][1]
        card["measured_build_stats"] = {
            k: results[v][k] for k in ("n_moved", "pct_moved", "mean_displacement_px",
                                       "max_displacement_px", "collar_dots_2_3px",
                                       "sgmc_control", "block_density_cv")
        }
        cards[rec["id"]] = card
    path.write_text(json.dumps(cards, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
