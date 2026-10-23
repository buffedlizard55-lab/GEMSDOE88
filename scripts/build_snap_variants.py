#!/usr/bin/env python3
"""Build AXIS=SNAP variants (brief v2 section 5) on the >=3 px-compliant parent.

Parent choice (decision, recorded): R0 (h33-h33-2-b2) itself carries 2,171 dots
at 2 < d_cat <= 3 px, so any non-PRUNE edit of R0 inherits a violation of the
brief's hard constraint 4 (keep >= 3 px unless AXIS=PRUNE) and was therefore
HOLD in prior sessions (MASS, CONCENTRATION). SNAP demands displacement <= 2 px
*and* destinations >= 3 px from the catalogue, which is infeasible for part of
R0's collar (registry/prune3_preregistration.json). We therefore build SNAP on
the already-built, fully compliant PRUNE p3px raster (min d_cat = 3.16 px,
37,654 dots, sha256 6f7ae705...), i.e. the (parent, axis) pair is
(PRUNEp3px, SNAP) - never built before. Diffs are reported against BOTH the
p3 parent and R0.

Method (pre-declared, deterministic, seed unused - no randomness):
  edge field E = 0.5 * rank(|tmi_hg|, band 3) + 0.5 * rank(|iso_grav_anom_hg|, band 18)
  computed from the pinned 19-band training_features.tif
  (sha256 4371c82e...), percentile ranks over finite footprint pixels only.
  These are the *provided* TMI / gravity horizontal-gradient bands named by
  the brief for SNAP; no lidar rasters are used (none supplied by the human).

  For each parent dot, candidate destinations are all pixels within Euclidean
  radius R (including staying put) that are inside the footprint, finite in E,
  and at d_cat > 3.0 px. The desired destination maximises E. Collisions are
  resolved greedily by descending E-gain (ties broken row-major): a mover may
  claim a pixel that is empty in the parent or freed by an already-placed
  mover; its own origin is always available as fallback, so the dot count is
  preserved exactly (37,654). Variants:
    SNAPr1   R = 1.0 px
    SNAPr2   R = 2.0 px
    SNAPr2g  R = 2.0 px, move only if E-gain >= 0.05 rank units
  SNAP is exempt from the 1-50% changed rule (brief section 5); the exact
  changed fractions and mean displacements are recorded regardless.

MODEL predictions are fixed *before* any proxy is computed (see PREDICTIONS
below) and are never revised from proxy output. SGMC control and dot-edge
statistics are REPORT ONLY (brief section 6).

Outputs: releases/<id>.tif (NaN outside) + -zeros.tif + single-TIFF .zips +
<id>.json receipts; registry/snap_report.json; ledger rows printed for the
human/merge step (this script also appends them to ledger/submissions.csv
if --append-ledger is given, refusing duplicates).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import gates, metric, validate  # noqa: E402

GRANDPARENT_ID = "h33-h33-2-b2"  # R0
PARENT_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
PARENT_PATH = ROOT / "releases" / f"{PARENT_ID}.tif"
PARENT_SHA = "6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9"
R0_PATH = ROOT / "data" / "registry" / "h33_education.tif"
R0_SHA = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
FEATURES_PATH = ROOT / "data" / "training_features.tif"
FEATURES_SHA = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
SAMPLE_PATH = ROOT / "data" / "bridge" / "sample_submission.tif"
SAMPLE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
EXISTING_PATH = ROOT / "data" / "bridge" / "existing_faults.tif"
EXISTING_SHA = "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"
SGMC_PATH = ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
SGMC_SHA = "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0"
FIXED_DATE = "20261023"
N_EXPECTED = 37_654

# Pre-declared MODEL predictions (live delta vs the p3 parent), fixed before
# any proxy computation. |delta| < 0.01 on public chunks = no evidence.
PREDICTIONS = {
    "r1": ("MODEL:+0.002", "[-0.006,+0.010]"),
    "r2": ("MODEL:+0.004", "[-0.008,+0.016]"),
    "r2g": ("MODEL:+0.003", "[-0.005,+0.011]"),
}
VARIANTS = [
    ("r1", 1.0, 0.0),
    ("r2", 2.0, 0.0),
    ("r2g", 2.0, 0.05),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def require_pin(path: Path, want: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing pinned input {label}: {path}")
    got = sha256_file(path)
    if got != want:
        raise ValueError(f"SHA256 mismatch for {label}: got {got}, want {want}")
    print(f"PIN OK {label} {want[:12]}...")


def percentile_rank(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Percentile rank in [0, 1] over valid finite pixels; -1 elsewhere."""
    out = np.full(values.shape, -1.0, dtype=np.float32)
    sel = valid & np.isfinite(values)
    v = values[sel].astype(np.float64)
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(v.size, dtype=np.float64)
    ranks[order] = np.arange(v.size, dtype=np.float64)
    # average ranks for ties
    sv = v[order]
    i = 0
    r_sorted = ranks[order]
    while i < v.size:
        j = i + 1
        while j < v.size and sv[j] == sv[i]:
            j += 1
        if j - i > 1:
            r_sorted[i:j] = r_sorted[i:j].mean()
        i = j
    ranks[order] = r_sorted
    out[sel] = (ranks / max(v.size - 1, 1)).astype(np.float32)
    return out


def snap(parent: np.ndarray, edge: np.ndarray, legal: np.ndarray,
         radius: float, min_gain: float) -> tuple[np.ndarray, dict]:
    """Move each dot <= radius px to the max-edge legal pixel. Count exact."""
    H, W = parent.shape
    rows, cols = np.nonzero(parent)
    n = rows.size
    r_int = int(np.ceil(radius))
    offs = [(dy, dx) for dy in range(-r_int, r_int + 1) for dx in range(-r_int, r_int + 1)
            if (dy * dy + dx * dx) <= radius * radius + 1e-9]

    # Per-dot candidate lists sorted by edge desc (stay included).
    cand: list[list[tuple[int, int]]] = []
    gains = np.zeros(n, dtype=np.float64)
    for k in range(n):
        y, x = int(rows[k]), int(cols[k])
        e0 = float(edge[y, x])
        scored: list[tuple[float, int, int]] = []
        for dy, dx in offs:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and legal[ny, nx] and edge[ny, nx] >= 0:
                scored.append((float(edge[ny, nx]), ny, nx))
        # Origin is always an admissible fallback (15 p3 dots sit on
        # feature-nodata pixels: edge undefined there, so they stay).
        if all((ny, nx) != (y, x) for _, ny, nx in scored):
            scored.append((e0, y, x))
        scored.sort(key=lambda t: (-t[0], t[1], t[2]))
        best_e = scored[0][0]
        gains[k] = best_e - e0 if e0 >= 0 else 0.0
        if gains[k] < min_gain:
            scored = [(e0, y, x)]  # forced stay
            gains[k] = 0.0
        cand.append([(ny, nx) for _, ny, nx in scored])

    # Greedy placement by descending gain; row-major tiebreak (stable order).
    order = sorted(range(n), key=lambda k: (-gains[k], int(rows[k]), int(cols[k])))
    claimed = np.zeros((H, W), dtype=bool)
    freed = np.zeros((H, W), dtype=bool)  # origins vacated by placed movers
    dest = np.empty((n, 2), dtype=np.int64)
    for k in order:
        y, x = int(rows[k]), int(cols[k])
        placed = None
        for ny, nx in cand[k]:
            if claimed[ny, nx]:
                continue
            if parent[ny, nx] and not (freed[ny, nx] or (ny == y and nx == x)):
                continue  # occupied by a not-yet-placed dot
            placed = (ny, nx)
            break
        if placed is None:
            placed = (y, x)  # origin is never claimed by another (rule above)
        assert not claimed[placed], f"double claim at {placed}"
        claimed[placed] = True
        dest[k] = placed
        if placed != (y, x):
            freed[y, x] = True

    out = np.zeros((H, W), dtype=bool)
    out[dest[:, 0], dest[:, 1]] = True
    assert int(out.sum()) == n, f"count changed: {out.sum()} != {n}"
    disp = np.hypot(dest[:, 0] - rows, dest[:, 1] - cols)
    moved = disp > 0
    stats = {
        "n_dots": int(n),
        "n_moved": int(moved.sum()),
        "pct_moved": round(100.0 * float(moved.mean()), 4),
        "mean_displacement_px_all": round(float(disp.mean()), 4),
        "mean_displacement_px_moved": round(float(disp[moved].mean()), 4) if moved.any() else 0.0,
        "max_displacement_px": round(float(disp.max()), 4),
        "mean_edge_before": round(float(np.nanmean(np.where(edge[rows, cols] >= 0, edge[rows, cols], np.nan))), 6),
        "mean_edge_after": round(float(np.nanmean(np.where(edge[dest[:, 0], dest[:, 1]] >= 0, edge[dest[:, 0], dest[:, 1]], np.nan))), 6),
        "n_dots_on_feature_nodata_forced_stay": int((edge[rows, cols] < 0).sum()),
        "displacement_hist_px": {
            f"{v:.2f}": int((np.isclose(disp, v)).sum())
            for v in sorted(set(np.round(disp, 4).tolist()))
        },
    }
    return out, stats


def ledger_hashes() -> set[str]:
    out: set[str] = set()
    p = ROOT / "ledger" / "submissions.csv"
    if p.is_file():
        with p.open(newline="") as f:
            for row in csv.DictReader(f):
                for col in ("sha256", "sha256_zeros"):
                    h = (row.get(col) or "").strip()
                    if h:
                        out.add(h)
    return out


def write_variant(mask, foot, catalogue, dist, parent_mask, r0_mask, value,
                  snap_stats, existing_shas) -> dict:
    releases = ROOT / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    with rasterio.open(SAMPLE_PATH) as tpl:
        base_prof = tpl.profile.copy()
        ref_tuple = (tpl.shape, tpl.crs, tpl.transform)
    prof_nan = base_prof.copy()
    prof_nan.update(driver="GTiff", dtype="float32", count=1, compress="deflate",
                    predictor=3, zlevel=9, tiled=True, blockxsize=256,
                    blockysize=256, nodata=np.nan)
    prof_zeros = prof_nan.copy()
    prof_zeros.update(nodata=None)
    arr_nan = np.where(foot, mask.astype(np.float32), np.nan).astype(np.float32)
    arr_zeros = np.where(foot, mask.astype(np.float32), 0.0).astype(np.float32)

    prefix = f"{PARENT_ID}-SNAP{value}-{FIXED_DATE}"
    tmp_nan = releases / f".tmp-{prefix}.tif"
    tmp_zeros = releases / f".tmp-{prefix}-zeros.tif"
    with rasterio.open(tmp_nan, "w", **prof_nan) as dst:
        dst.write(arr_nan, 1)
    with rasterio.open(tmp_zeros, "w", **prof_zeros) as dst:
        dst.write(arr_zeros, 1)
    sha_nan, sha_zeros = sha256_file(tmp_nan), sha256_file(tmp_zeros)
    if sha_nan in existing_shas or sha_zeros in existing_shas:
        tmp_nan.unlink(missing_ok=True)
        tmp_zeros.unlink(missing_ok=True)
        raise RuntimeError(f"Duplicate SHA-256 already in ledger: {sha_nan}")
    vid = f"{prefix}-{sha_nan[:8]}"
    final_nan, final_zeros = releases / f"{vid}.tif", releases / f"{vid}-zeros.tif"
    tmp_nan.replace(final_nan)
    tmp_zeros.replace(final_zeros)
    zip_nan, zip_zeros = releases / f"{vid}.zip", releases / f"{vid}-zeros.zip"
    for tif_p, zip_p in ((final_nan, zip_nan), (final_zeros, zip_zeros)):
        with zipfile.ZipFile(zip_p, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(tif_p, arcname=tif_p.name)
        os.chmod(tif_p, 0o644)
        os.chmod(zip_p, 0o644)

    # MUST gates: independent re-read from disk.
    with rasterio.open(final_nan) as ds:
        back = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform) == ref_tuple
        assert ds.count == 1 and ds.dtypes[0] == "float32" and str(ds.crs) == "EPSG:32611"
        assert np.isfinite(back[foot]).all() and np.isnan(back[~foot]).all()
        assert float(back[foot].min()) >= 0.0 and float(back[foot].max()) <= 1.0
        assert int((back[catalogue] > 0).sum()) == 0
        assert np.array_equal(back[foot] > 0.5, mask[foot])
    with rasterio.open(final_zeros) as ds:
        back = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform) == ref_tuple
        assert np.isfinite(back).all() and np.all(back[~foot] == 0.0)
        assert int((back[catalogue] > 0).sum()) == 0
        assert np.array_equal(back[foot] > 0.5, mask[foot])
    assert gates.format_report(final_zeros, SAMPLE_PATH, footprint=foot)["ok"]
    assert validate.validate(final_zeros, foot, catalogue)["all_checks_passed"]

    dvals = dist[mask]
    assert float(dvals.min()) > 3.0, f"SNAP destination inside 3px collar: {dvals.min()}"

    def diff_vs(other: np.ndarray) -> dict:
        n_p = int(other.sum())
        added = int((mask & ~other).sum())
        removed = int((other & ~mask).sum())
        return {"n_parent": n_p, "common": n_p - removed, "n_added": added,
                "n_removed": removed,
                "pct_changed_moved": round(100.0 * removed / n_p, 4),
                "pct_changed_sym_diff": round(100.0 * (added + removed) / n_p, 4)}

    pred, pred_range = PREDICTIONS[value]
    radius_txt = {"r1": "<=1px", "r2": "<=2px", "r2g": "<=2px gain>=.05"}[value]
    note = (f"PRUNEp3px; SNAP {value} {radius_txt} to max TMI/grav HG, N=37654 held, "
            f"all >3px; pred {pred.replace('MODEL:', '')} MODEL")
    assert len(note) <= 140, f"form note too long ({len(note)})"

    receipt = {
        "id": vid, "parent": PARENT_ID, "parent_sha256": PARENT_SHA,
        "grandparent": GRANDPARENT_ID, "grandparent_sha256_zeros": R0_SHA,
        "axis": "SNAP", "value": value, "fixed_date": FIXED_DATE,
        "git_sha": git_sha(),
        "edge_field": "0.5*rank(|tmi_hg| b3)+0.5*rank(|iso_grav_anom_hg| b18), training_features.tif 4371c82e",
        "file_nan": f"releases/{final_nan.name}", "sha256": sha_nan,
        "bytes_nan": final_nan.stat().st_size,
        "zip_nan": f"releases/{zip_nan.name}", "zip_nan_sha256": sha256_file(zip_nan),
        "file_zeros": f"releases/{final_zeros.name}", "sha256_zeros": sha_zeros,
        "bytes_zeros": final_zeros.stat().st_size,
        "zip_zeros": f"releases/{zip_zeros.name}", "zip_zeros_sha256": sha256_file(zip_zeros),
        "form_note": note, "form_note_chars": len(note),
        "n_dots": int(mask.sum()),
        "snap": snap_stats,
        "parent_diff_vs_prune_p3": diff_vs(parent_mask),
        "parent_diff_vs_r0": diff_vs(r0_mask),
        "min_dist_catalogue_px": round(float(dvals.min()), 4),
        "dots_le_3px": int((dvals <= 3.0).sum()),
        "predicted_change": pred, "predicted_range": pred_range,
        "gates": {"crs_epsg_32611": True, "shape_3730x3292": True,
                  "transform_match": True, "dtype_float32": True,
                  "band_count_1": True, "values_in_0_1": True,
                  "no_nan_inside_footprint": True, "nan_outside_footprint": True,
                  "zeros_fallback_valid": True, "zero_catalogue_mass": True,
                  "all_dots_gt3px_from_catalogue": True,
                  "reread_from_disk_verified": True},
    }
    (releases / f"{vid}.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def sgmc_proxy(mask, foot, catalogue) -> dict:
    """REPORT ONLY: blind off-catalogue USGS SGMC control (never a gate)."""
    with rasterio.open(SGMC_PATH) as ds:
        raw = ds.read(1) > 0
    off = raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    res = metric.dti_binary(mask, off, valid=foot, known=catalogue)
    return {"dti": round(float(res["dti"]), 6), "n_sgmc_off_catalogue_px": int(off.sum()),
            "label": "PROXY (SGMC control, report only)"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--append-ledger", action="store_true")
    args = ap.parse_args()

    print("[1/4] Verifying pins...")
    require_pin(SAMPLE_PATH, SAMPLE_SHA, "sample_submission")
    require_pin(EXISTING_PATH, EXISTING_SHA, "existing_faults")
    require_pin(FEATURES_PATH, FEATURES_SHA, "training_features")
    require_pin(R0_PATH, R0_SHA, "R0 zeros")
    require_pin(PARENT_PATH, PARENT_SHA, "PRUNE p3 parent")
    require_pin(SGMC_PATH, SGMC_SHA, "SGMC control")

    with rasterio.open(SAMPLE_PATH) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(EXISTING_PATH) as ds:
        catalogue = (ds.read(1) == 1) & foot
    dist = distance_transform_edt(~catalogue).astype(np.float32)
    with rasterio.open(PARENT_PATH) as ds:
        parent = np.nan_to_num(ds.read(1), nan=0.0) > 0.5
    with rasterio.open(R0_PATH) as ds:
        r0 = np.nan_to_num(ds.read(1), nan=0.0) > 0.5
    assert int(parent.sum()) == N_EXPECTED and int(r0.sum()) == N_EXPECTED
    assert float(dist[parent].min()) > 3.0

    print("[2/4] Building edge field from provided gradient bands 3 + 18...")
    with rasterio.open(FEATURES_PATH) as ds:
        assert ds.tags(3).get("band_name") == "tmi_hg", ds.tags(3)
        assert ds.tags(18).get("band_name") == "iso_grav_anom_hg", ds.tags(18)
        nodata = ds.nodata
        b3 = ds.read(3).astype(np.float64)
        b18 = ds.read(18).astype(np.float64)
    for b in (b3, b18):
        b[~np.isfinite(b)] = np.nan
        if nodata is not None:
            b[b == nodata] = np.nan
        b[np.abs(b) > 1e30] = np.nan
    r3 = percentile_rank(np.abs(b3), foot)
    r18 = percentile_rank(np.abs(b18), foot)
    edge = np.full(foot.shape, -1.0, dtype=np.float32)
    both = (r3 >= 0) & (r18 >= 0)
    edge[both] = 0.5 * r3[both] + 0.5 * r18[both]
    legal = foot & (dist > 3.0) & (edge >= 0)
    n_nodata_dots = int((parent & ~legal).sum())
    print(f"      parent dots on feature-nodata pixels (forced stay): {n_nodata_dots}")
    assert n_nodata_dots <= 100, f"too many nodata-origin dots: {n_nodata_dots}"
    print(f"      edge finite on {int(both.sum()):,} px; legal destinations {int(legal.sum()):,} px")

    print("[3/4] Snapping variants...")
    existing = ledger_hashes()
    receipts = []
    masks: dict[str, np.ndarray] = {}
    for value, radius, min_gain in VARIANTS:
        mask, stats = snap(parent, edge, legal, radius, min_gain)
        masks[value] = mask
        rec = write_variant(mask, foot, catalogue, dist, parent, r0, value, stats, existing)
        existing.add(rec["sha256"])
        existing.add(rec["sha256_zeros"])
        receipts.append(rec)
        print(f"      {rec['id']} moved={stats['pct_moved']:.2f}% "
              f"meandisp={stats['mean_displacement_px_all']:.3f}px "
              f"edge {stats['mean_edge_before']:.4f}->{stats['mean_edge_after']:.4f}")

    print("[4/4] REPORT-ONLY SGMC proxy (never a gate)...")
    proxies = {"parent_prune_p3": sgmc_proxy(parent, foot, catalogue),
               "grandparent_r0": sgmc_proxy(r0, foot, catalogue)}
    for rec, (value, _, _) in zip(receipts, VARIANTS):
        proxies[rec["id"]] = sgmc_proxy(masks[value], foot, catalogue)
        rec["report_only_sgmc"] = proxies[rec["id"]]
        (ROOT / "releases" / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        print(f"      SGMC PROXY {rec['id']}: {proxies[rec['id']]['dti']:.5f} "
              f"(parent p3 {proxies['parent_prune_p3']['dti']:.5f}, R0 {proxies['grandparent_r0']['dti']:.5f})")

    report = {"schema": "gems88.snap_report.v1", "axis": "SNAP",
              "parent": PARENT_ID, "parent_sha256": PARENT_SHA,
              "grandparent": GRANDPARENT_ID, "git_sha": git_sha(),
              "predictions_predeclared": PREDICTIONS,
              "variants": receipts, "report_only_sgmc": proxies}
    (ROOT / "registry" / "snap_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("wrote registry/snap_report.json")

    if args.append_ledger:
        led = ROOT / "ledger" / "submissions.csv"
        with led.open(newline="") as f:
            rows = list(csv.DictReader(f))
            fields = list(rows[0].keys()) if rows else []
        ids = {r["id"] for r in rows}
        desc = {
            "r1": "SNAP radius 1px on PRUNE-p3: each dot to max provided TMI/gravity horizontal-gradient pixel within 1px; N=37654 held, all >3px from catalogue.",
            "r2": "SNAP radius 2px on PRUNE-p3: each dot to max provided TMI/gravity horizontal-gradient pixel within 2px; N=37654 held, all >3px from catalogue.",
            "r2g": "SNAP radius 2px on PRUNE-p3, move only if edge-rank gain >=0.05; N=37654 held, all >3px from catalogue.",
        }
        new = []
        for rec in receipts:
            if rec["id"] in ids:
                raise RuntimeError(f"ledger already contains {rec['id']}")
            row = {k: "" for k in fields}
            row.update({
                "id": rec["id"], "parent": PARENT_ID, "axis": "SNAP",
                "value": rec["value"], "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff_vs_prune_p3']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"], "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT", "predicted_change": rec["predicted_change"],
                "predicted_range": rec["predicted_range"],
                "ranking_basis": "edge=0.5*rank(|tmi_hg|)+0.5*rank(|iso_grav_anom_hg|) from pinned training_features.tif; greedy gain-ordered collision resolution; deterministic",
                "description": desc[rec["value"]],
                "recommendation": "SNAP test vs PRUNE-p3 parent; spend a slot only after a PRUNE receipt establishes the p3 baseline (see SLOT_PLAN).",
            })
            new.append(row)
        with led.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            for row in new:
                w.writerow(row)
        print(f"appended {len(new)} rows to ledger/submissions.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
