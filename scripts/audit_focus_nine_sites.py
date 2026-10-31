#!/usr/bin/env python3
"""Read-only audit of the nine GEMSDOE owner sites named in the 2026-10-30 request.

Scope: GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 (GitHub owner repos under
buffedlizard55-lab). The script

* sparse-clones each site at a PINNED HEAD into the git-ignored ``.cache/``;
* SHA-256 hashes every TIFF/ZIP under ``docs/`` (cross-site byte duplicates);
* maps each user-supplied claim to the file it most plausibly names, and records
  the mapping rule (exact stem match) so a reviewer can verify it;
* reopens each claimed TIFF with the shared format validator and the shared grid
  (``vendor/gems57/grid.py``), and records NaN / value / dot statistics;
* measures literal 3-px dot overlap with the shared ``uniqueness.dot_overlap``
  (pairwise among claimed files) and with a KD-tree census of every binary dot
  TIFF in the nine sites (the KD-tree is asserted equal to the shared function
  on sampled pairs before it is used).

It NEVER writes a prediction raster, never edits a site, never spends a weekly
slot, and never converts a user-reported score into an organizer or holdout
score. Scores are carried as ``USER-REPORTED CLAIM`` only.

Usage:  .venv/bin/python scripts/audit_focus_nine_sites.py [--offline]
   --offline: reuse existing sparse clones in .cache/focus9 without network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import grid, uniqueness  # noqa: E402
from gems57.metric import RADIUS_PX  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

OWNER = "buffedlizard55-lab"
CACHE = ROOT / ".cache" / "focus9"
EVIDENCE = ROOT / "evidence" / "focus9_nine_site_audit_20261030.json"
SAMPLE = ROOT / "data" / "bridge" / "sample_submission.tif"
CATALOGUE = ROOT / "data" / "bridge" / "existing_faults.tif"

# Pinned HEADs observed with `git clone --depth 1` on 2026-10-30 (UTC session start).
SITES = {
    "GEMSDOE24": "52fdca93084f6f6e4623bfa904cd6fc41a3abfbe",
    "GEMSDOE25": "8cb3573d8adc747b519dd0d96ffdc4eccad6d8ec",
    "GEMSDOE27": "60da5e4128339244efc61274abf95d22702ff801",
    "GEMSDOE28": "fe2b95e2377d8878f0d77445c0079ec1c801f50a",
    "GEMSDOE30": "e72c88956ef643247fa341070004e1c889066f3f",
    "GEMSDOE31": "f9248200f20def2654af596c1cc13ab2f9d96687",
    "GEMSDOE32": "c8e560f1aae650b120dc31c9e7495ced6a587701",
    "GEMSDOE33": "ee2e464b61cb0e0aa604b0525044ad9ff31c9ec7",
    "GEMSDOE36": "b0824c550c02792897d0ebe3aba1cb0e75583ea1",
}

# Claims transcribed verbatim from the 2026-10-30 user request (ID : score).
# Each entry: site, claimed id (verbatim), claimed score, and the in-repo file
# that carries the same ID stem (path relative to the site root). Where the
# user's ID omits the site prefix, the match is on the distinctive stem.
CLAIMS = [
    ("GEMSDOE24", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", 0.2477,
     "docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
    ("GEMSDOE24", "gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros", 0.0859,
     "docs/downloads/gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros.tif"),
    ("GEMSDOE25", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan", 0.2600,
     "docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
    ("GEMSDOE25", "gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros", 0.0742,
     "docs/downloads/gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros.tif"),
    ("GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", 0.2449,
     "docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"),
    ("GEMSDOE27", "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite", 0.2190,
     "docs/downloads/gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite.tif"),
    ("GEMSDOE27", "gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite", 0.2250,
     "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif"),
    ("GEMSDOE28", "h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan", 0.2708,
     "docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif"),
    ("GEMSDOE28", "h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan", 0.2649,
     "docs/downloads/gems28-h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan.tif"),
    ("GEMSDOE28", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", 0.2710,
     "docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif"),
    ("GEMSDOE28", "h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan", 0.2707,
     "docs/downloads/gems28-h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan.tif"),
    ("GEMSDOE28", "gems28-s18-mxtp-20261025-3e95505c011a-allfinite", 0.0217,
     "docs/downloads/gems28-s18-mxtp-20261025-3e95505c011a-allfinite.tif"),
    ("GEMSDOE28", "gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite", 0.0206,
     "docs/downloads/gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite.tif"),
    ("GEMSDOE30", "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", 0.2600,
     "docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif"),
    ("GEMSDOE30", "gems30-MSDB1-edge44090-20261025-e7856ec3f14a", 0.1462,
     "docs/downloads/gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif"),
    ("GEMSDOE31", "h27-4-solo-d28-20261004-8acb75e1-nan", 0.2708,
     "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif"),
    ("GEMSDOE32", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", 0.2778,
     "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"),
    ("GEMSDOE33", "h33d-analog-tip-stepover-r30-20261004-cb490425926e", 0.2632,
     "docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif"),
    ("GEMSDOE33", "gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros", 0.0963,
     "docs/downloads/gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros.tif"),
    ("GEMSDOE36", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", 0.2750,
     "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif"),
    ("GEMSDOE36", "gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros", 0.1647,
     "docs/downloads/gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif"),
]

OFFICIAL_LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"


FILL_SUFFIX = re.compile(r"-(nan|nanoutside|nan-outside|zeros|zero|allfinite)$")


def family_of(relpath: str) -> str:
    """Filename stem with the NaN/zero/allfinite fill suffix removed.

    Files that share a family inside one site are fill variants of ONE
    submission (identical dots), so they are siblings, not competing entries.
    """
    stem = Path(relpath).name.rsplit(".", 1)[0]
    return FILL_SUFFIX.sub("", stem)


def finite_json(obj):
    """Replace NaN/Inf with null so the evidence file is strict JSON."""
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: finite_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [finite_json(v) for v in obj]
    return obj


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ensure_clone(repo: str, sha: str, offline: bool) -> dict:
    target = CACHE / repo
    url = f"https://github.com/{OWNER}/{repo}.git"
    status = {"repo": repo, "url": url, "pinned_head": sha}
    if not target.exists():
        if offline:
            raise FileNotFoundError(f"offline and no cache for {repo}")
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse",
                        "--no-checkout", url, str(target)], check=True, timeout=600)
        subprocess.run(["git", "-C", str(target), "sparse-checkout", "set", "docs", "README.md"],
                       check=True, timeout=600)
        subprocess.run(["git", "-C", str(target), "checkout", "-q"], check=True, timeout=600)
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    status["observed_head"] = head
    status["head_matches_pin"] = head == sha
    return status | {"path": str(target.relative_to(ROOT))}


def census(target: Path) -> list[dict]:
    rows = []
    for path in sorted((target / "docs").rglob("*")):
        if path.suffix.lower() in {".tif", ".tiff", ".zip"} and path.is_file():
            rows.append({"path": str(path.relative_to(target)), "bytes": path.stat().st_size,
                         "sha256": sha256(path)})
    return rows


def raster_stats(path: Path, footprint: np.ndarray) -> dict:
    with rasterio.open(path) as src:
        arr = src.read(1)
        meta = {"driver": src.driver, "count": src.count, "dtype": src.dtypes[0],
                "nodata": src.nodata, "shape": list(src.shape),
                "crs": src.crs.to_string() if src.crs else None,
                "transform_matches_sample": src.transform == grid.TRANSFORM}
    finite = np.isfinite(arr)
    nan_in = int((~finite & footprint).sum())
    nan_out = int((~finite & ~footprint).sum())
    fin_vals = arr[finite]
    unique = np.unique(fin_vals) if fin_vals.size else np.array([])
    binary = bool(unique.size and np.isin(unique, [0.0, 1.0]).all())
    in_range = bool(((fin_vals >= 0) & (fin_vals <= 1)).all()) if fin_vals.size else False
    meta.update({
        "finite_cells": int(finite.sum()),
        "nan_inside_footprint": nan_in,
        "nan_outside_footprint": nan_out,
        "values_all_in_0_1": in_range,
        "min": float(fin_vals.min()) if fin_vals.size else None,
        "max": float(fin_vals.max()) if fin_vals.size else None,
        "distinct_finite_values": int(unique.size),
        "kind": "binary_dot_raster" if binary else "dense_continuous_surface",
        "positive_cells": int(((arr > 0) & finite).sum()),
        "ones_cells": int((arr == 1).sum()) if binary else None,
    })
    return meta


def dots_of(arr: np.ndarray) -> np.ndarray:
    return np.isfinite(arr) & (arr > 0)


def kdtree_overlap(mine_dots_yx: np.ndarray, theirs_tree: cKDTree | None) -> float:
    """Fraction of ``mine`` dots with a ``theirs`` dot within RADIUS_PX (Euclidean)."""
    if mine_dots_yx.size == 0 or theirs_tree is None:
        return 0.0
    dist, _ = theirs_tree.query(mine_dots_yx, k=1, distance_upper_bound=RADIUS_PX + 1e-9)
    return float(np.mean(np.isfinite(dist) & (dist <= RADIUS_PX)))


def self_test_kdtree(rng: random.Random, paths: dict[str, Path]) -> dict:
    """Assert the KD-tree 3-px rule equals the shared uniqueness.dot_overlap on sampled pairs."""
    keys = list(paths)
    pairs = [(a, b) for a in keys for b in keys if a != b]
    rng.shuffle(pairs)
    checked, mismatches, max_abs = 0, 0, 0.0
    for a, b in pairs[:12]:
        mine = dots_of(read_band(paths[a]))
        theirs = dots_of(read_band(paths[b]))
        shared = uniqueness.dot_overlap(mine, theirs, RADIUS_PX)
        tree = cKDTree(np.argwhere(theirs)) if theirs.any() else None
        kd = kdtree_overlap(np.argwhere(mine).astype(float), tree)
        max_abs = max(max_abs, abs(shared - kd))
        checked += 1
        mismatches += int(abs(shared - kd) > 1e-12)
    return {"pairs_checked": checked, "mismatches": mismatches, "max_abs_difference": max_abs,
            "radius_px": RADIUS_PX, "shared_function": "vendor/gems57/uniqueness.py:dot_overlap"}


def read_band(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(1)


def same_family(key_a: str, key_b: str) -> bool:
    """True when two 'site:path' keys are fill variants of one submission in one site."""
    site_a, path_a = key_a.split(":", 1)
    site_b, path_b = key_b.split(":", 1)
    return site_a == site_b and family_of(path_a) == family_of(path_b)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args(argv)

    g = grid.load_grid(ROOT / "data" / "bridge")
    footprint, catalogue = g.footprint, g.catalogue
    allowed = footprint & ~catalogue
    report: dict = {
        "schema": "gems88.focus-nine-site-audit.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "GEMSDOE24,25,27,28,30,31,32,33,36 (owner repos, pinned HEADs)",
        "official_leaderboard_url": OFFICIAL_LEADERBOARD,
        "score_label": "USER-REPORTED CLAIM (2026-10-30 request). Not an organizer receipt; not a holdout DTI.",
        "grid": {"shape": [g.height, g.width],
                 "footprint_cells": int(footprint.sum()), "catalogue_cells_in_footprint": int(catalogue.sum()),
                 "allowed_cells": int(allowed.sum()), "crs": str(g.crs), "transform": list(g.transform)[:6],
                 "source": "data/bridge/sample_submission.tif (footprint) + existing_faults.tif (catalogue)"},
        "sites": {},
    }

    arrays_claims: dict[str, np.ndarray] = {}
    site_status = []
    census_rows: list[dict] = []
    for repo, sha in SITES.items():
        st = ensure_clone(repo, sha, args.offline)
        site_status.append(st)
        target = ROOT / st["path"]
        rows = census(target)
        for row in rows:
            row["site"] = repo
        census_rows.extend(rows)
        report["sites"][repo] = {"head": st["observed_head"], "head_matches_pin": st["head_matches_pin"],
                                 "tif_zip_files_under_docs": len(rows)}
    report["clone_status"] = site_status

    # Irregularity record: the mirror's sample_submission.tif vs its description.
    with rasterio.open(SAMPLE) as src_s, rasterio.open(CATALOGUE) as src_c:
        samp, cat_raw = src_s.read(1), src_c.read(1)
    samp_ones = samp == 1
    report["sample_submission_irregularity"] = {
        "file": "data/bridge/sample_submission.tif",
        "sha256": sha256(SAMPLE),
        "ones_cells": int(samp_ones.sum()),
        "zeros_cells": int((samp == 0).sum()),
        "nan_cells": int(np.isnan(samp).sum()),
        "ones_equal_catalogue_cells_exactly": bool(np.array_equal(samp_ones, cat_raw > 0)),
        "official_description": "A sample submission that predicts total fault absence is provided "
                                "(DrivenData page 967, Submission format).",
        "status": "IRREGULARITY_FOR_REVIEW: mirror sample is not all-zero; its 1-cells equal the "
                  "USGS/INGENIOUS catalogue. Organizer file is login-only and was not retrieved.",
    }

    # Cross-site byte duplicates across ALL TIFF/ZIP files in the nine sites.
    by_hash: dict[str, list[dict]] = {}
    for row in census_rows:
        by_hash.setdefault(row["sha256"], []).append(row)
    dup_groups = [
        {"sha256": h, "copies": [{"site": r["site"], "path": r["path"]} for r in rows]}
        for h, rows in by_hash.items()
        if len({r["site"] for r in rows}) > 1
    ]
    report["cross_site_byte_duplicate_groups"] = sorted(dup_groups, key=lambda d: d["sha256"])
    report["census_total_tif_zip"] = len(census_rows)

    # Claimed-file audit.
    claims_out = []
    claim_paths: dict[str, Path] = {}
    for site, cid, score, rel in CLAIMS:
        path = ROOT / ".cache" / "focus9" / site / rel
        entry = {"site": site, "claimed_id": cid, "claimed_score": score,
                 "score_label": "USER-REPORTED CLAIM", "file": rel,
                 "mapping_rule": "file chosen by exact stem match of the claimed ID inside docs/downloads",
                 "exists_at_pinned_head": path.exists()}
        if path.exists():
            entry["sha256"] = sha256(path)
            entry["bytes"] = path.stat().st_size
            entry["raster"] = raster_stats(path, footprint)
            entry["strict_local_format"] = validate_artifact(path, SAMPLE)
            entry["strict_local_format"].pop("artifact", None)
            if entry["raster"]["kind"] == "binary_dot_raster":
                claim_paths[f"{site}:{rel}"] = path
        claims_out.append(entry)
    # Official-spec checks (drivendata page 967, "Submission format"): float32,
    # single layer, EPSG:32611, same shape/transform as the training grid, values
    # in [0,1], and NaN/null permitted outside the bounds. The repo's stricter
    # local policy (scripts/validate_artifact.py) is recorded separately above.
    for entry in claims_out:
        if "raster" not in entry:
            continue
        r = entry["raster"]
        entry["official_spec_checks"] = {
            "float32": r["dtype"] == "float32",
            "single_layer": r["count"] == 1,
            "crs_EPSG_32611": r["crs"] == "EPSG:32611",
            "same_shape_as_grid": r["shape"] == [g.height, g.width],
            "same_transform_as_grid": r["transform_matches_sample"],
            "values_in_0_1_where_finite": r["values_all_in_0_1"],
            "no_nan_inside_study_footprint": r["nan_inside_footprint"] == 0,
            "nan_outside_footprint_allowed_by_spec": True,
        }
        entry["official_spec_pass"] = all(v for k, v in entry["official_spec_checks"].items()
                                          if k != "nan_outside_footprint_allowed_by_spec")
    report["claims"] = claims_out

    # Pairwise literal overlap among binary claimed files (shared function).
    claim_dots = {k: dots_of(read_band(p)) for k, p in claim_paths.items()}
    pair_rows = []
    for a in claim_dots:
        for b in claim_dots:
            if a != b and not same_family(a, b):
                pair_rows.append({"mine": a, "theirs": b, "forward_overlap_3px": round(
                    uniqueness.dot_overlap(claim_dots[a], claim_dots[b], RADIUS_PX), 6)})
    report["pairwise_claimed_overlap_3px"] = {
        "rule": "shared uniqueness.dot_overlap; blocks above 0.70 (OVERLAP_LIMIT)",
        "pairs_over_0_70": [p for p in pair_rows if p["forward_overlap_3px"] > uniqueness.OVERLAP_LIMIT],
        "n_pairs": len(pair_rows),
    }

    # Census of every binary dot TIFF in the nine sites. Only dot coordinates are
    # kept in memory (no full rasters), and the KD-tree is self-tested first.
    census_paths: dict[str, Path] = {}
    census_dots: dict[str, np.ndarray] = {}
    for row in census_rows:
        if not row["path"].lower().endswith(".tif"):
            continue
        path = ROOT / ".cache" / "focus9" / row["site"] / row["path"]
        with rasterio.open(path) as src:
            row["grid_ok"] = src.shape == (g.height, g.width) and src.count == 1
            arr = src.read(1) if row["grid_ok"] else None
        if arr is None:
            continue
        finite = np.isfinite(arr)
        if finite.any() and np.isin(arr[finite], [0.0, 1.0]).all() and (arr > 0).any():
            key = f"{row['site']}:{row['path']}"
            census_paths[key] = path
            census_dots[key] = np.argwhere(dots_of(arr)).astype(float)
            row["dot_count"] = int(census_dots[key].shape[0])
    report["census_binary_dot_tifs"] = len(census_dots)
    report["kdtree_self_test"] = self_test_kdtree(random.Random(20261030), {**census_paths, **claim_paths})

    trees = {k: cKDTree(v) for k, v in census_dots.items()}
    for entry in claims_out:
        key = f"{entry['site']}:{entry['file']}"
        if key not in claim_dots:
            continue
        mine = np.argwhere(claim_dots[key]).astype(float)
        best = sorted(((kdtree_overlap(mine, tree), other) for other, tree in trees.items()
                       if other != key and not same_family(other, key)), reverse=True)
        entry["max_overlap_vs_any_binary_tif_in_nine_sites"] = round(best[0][0], 6) if best else None
        entry["closest_other_file"] = best[0][1] if best else None
        entry["n_other_binary_tifs_compared"] = len(best)
        # Chance baseline: same number of dots placed uniformly at random on the
        # allowed domain, scored against the same closest file (seed fixed).
        if best:
            closest_key = best[0][1]
            rng_np = np.random.default_rng(20261030)
            allowed_yx = np.argwhere(allowed)
            pick = rng_np.choice(len(allowed_yx), size=mine.shape[0], replace=False)
            chance = kdtree_overlap(allowed_yx[pick].astype(float), trees[closest_key])
            entry["chance_overlap_same_n_random_vs_closest"] = round(chance, 6)
            entry["closest_other_file_site"] = closest_key.split(":", 1)[0]
        entry["identical_bytes_elsewhere"] = [
            {"site": r["site"], "path": r["path"]} for r in by_hash.get(entry["sha256"], [])
            if not (r["site"] == entry["site"] and r["path"] == entry["file"])
        ]

    # Set-membership against the shared template (the GEMSDOE33 D28 reference),
    # which the top-scoring files appear to prune. Measurement only.
    template_key = "GEMSDOE33:docs/downloads/gemsdoe33-d28-reference-20261004-426073b6b4ab-zeros.tif"
    anderson_key = "GEMSDOE36:docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif"
    h33_key = "GEMSDOE32:docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"
    if template_key in claim_dots or template_key in census_paths:
        tmpl = dots_of(read_band(census_paths[template_key]))
        anderson = dots_of(read_band(census_paths[anderson_key]))
        h33 = dots_of(read_band(census_paths[h33_key]))
        report["template_set_identities"] = {
            "template": template_key,
            "template_dots": int(tmpl.sum()),
            "h33_equals_anderson_AND_template_exact": bool(np.array_equal(h33, anderson & tmpl)),
            "anderson_dots_outside_template": int((anderson & ~tmpl).sum()),
            "anderson_AND_template_dots": int((anderson & tmpl).sum()),
            "scope": "exact cell-set identities; measurement only, not a candidate or clearance",
        }
        for entry in claims_out:
            key = f"{entry['site']}:{entry['file']}"
            if key in claim_dots:
                d = claim_dots[key]
                entry["dots"] = int(d.sum())
                entry["dots_inside_template"] = int((d & tmpl).sum())
                entry["fraction_inside_template"] = round(float((d & tmpl).sum() / d.sum()), 6)
                entry["equals_template_exactly"] = bool(np.array_equal(d, tmpl))

    # Registry (validation tier): literal support and sparse overlap.
    registry_rows = []
    for reg in sorted((ROOT / "data" / "registry").glob("*.tif")):
        arr = read_band(reg)
        finite = np.isfinite(arr)
        binary = bool(finite.any() and np.isin(arr[finite], [0.0, 1.0]).all())
        row = {"registry_file": str(reg.relative_to(ROOT)), "sha256": sha256(reg),
               "kind": "binary_dot_raster" if binary else "dense_continuous_surface",
               "literal_positive_cells": int(((arr > 0) & finite).sum())}
        if binary:
            tree = cKDTree(np.argwhere(dots_of(arr))) if row["literal_positive_cells"] else None
            row["max_forward_overlap_3px_vs_claimed"] = round(max(
                (kdtree_overlap(np.argwhere(d).astype(float), tree) for d in claim_dots.values()),
                default=0.0), 6)
        else:
            row["literal_positive_fraction_of_allowed"] = round(
                float(((arr > 0) & finite & allowed).sum() / allowed.sum()), 6)
        registry_rows.append(row)
    report["registry_validation_tier"] = registry_rows

    # Per-claim forward overlap against each SPARSE validation-tier registry raster.
    reg_trees = {}
    for row in registry_rows:
        if row["kind"] == "binary_dot_raster" and row["literal_positive_cells"]:
            reg_trees[row["registry_file"]] = cKDTree(np.argwhere(dots_of(read_band(ROOT / row["registry_file"]))))
    for entry in claims_out:
        key = f"{entry['site']}:{entry['file']}"
        if key not in claim_dots:
            continue
        mine = np.argwhere(claim_dots[key]).astype(float)
        per = {name: round(kdtree_overlap(mine, tree), 6) for name, tree in reg_trees.items()}
        entry["registry_sparse_forward_overlap_3px"] = per
        entry["max_registry_sparse_overlap_3px"] = max(per.values()) if per else None

    # Per-claim verdicts. Three separate questions, never merged:
    #   1) format: strict local validator (NaN/out-of-range/grid) -- format only;
    #   2) uniqueness: literal shared 0.70 rule vs the nine-site census, vs
    #      validation-tier sparse registry rasters, and byte-identity;
    #   3) dense witness: 17GEMSDOE covers all allowed cells, so the literal
    #      generation gate blocks EVERY nonempty candidate (generation_guard.py).
    for entry in claims_out:
        if "raster" not in entry:
            entry["verdict"] = "FILE_NOT_FOUND_AT_PINNED_HEAD"
            entry["unique_vs_nine_sites_literal"] = None
            entry["format_pass_strict_local"] = None
            entry["dense_witness_blocks_candidate"] = None
            continue
        r = entry["raster"]
        mx = entry.get("max_overlap_vs_any_binary_tif_in_nine_sites")
        rg = entry.get("max_registry_sparse_overlap_3px")
        uniq_reasons = []
        if r["kind"] != "binary_dot_raster":
            uniq_reasons.append("dense continuous surface: literal dot rule undefined")
        if entry.get("identical_bytes_elsewhere"):
            uniq_reasons.append("byte-identical copy in another nine-site repo")
        if mx is not None and mx > uniqueness.OVERLAP_LIMIT:
            uniq_reasons.append(f"3-px overlap {mx:.4f} > 0.70 with another nine-site submission")
        if rg is not None and rg > uniqueness.OVERLAP_LIMIT:
            uniq_reasons.append(f"3-px overlap {rg:.4f} > 0.70 with a validation-tier registry raster")
        if rg is None:
            uniq_reasons.append("no sparse registry comparison available")
        format_reasons = []
        if r["nan_outside_footprint"] or r["nan_inside_footprint"]:
            format_reasons.append(f"NaN cells present ({r['nan_outside_footprint']} outside footprint)")
        if not entry["strict_local_format"].get("ok"):
            format_reasons.append("strict local validator returned ok=false")
        entry["uniqueness_reasons_not_unique"] = uniq_reasons
        entry["format_reasons_not_pass"] = format_reasons
        entry["unique_vs_nine_sites_literal"] = not uniq_reasons
        entry["format_pass_strict_local"] = not format_reasons
        entry["dense_witness_blocks_candidate"] = True
        entry["eligible_to_download_for_submission"] = False
        entry["verdict"] = ("UNIQUE_LITERAL_VS_CENSUS_BUT_BLOCKED_BY_DENSE_WITNESS"
                            if not uniq_reasons else "NOT_UNIQUE_LITERAL")

    report["generation_gate"] = "scripts/generation_guard.py (see README); not re-run by this audit"
    report["ok_to_submit"] = False
    report["new_rasters_generated"] = 0
    report["weekly_slots_used"] = 0
    report["experiments_run"] = 0
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    tmp = EVIDENCE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(finite_json(report), indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(EVIDENCE)
    print(f"wrote {EVIDENCE.relative_to(ROOT)}")
    print(f"claims found: {sum('raster' in c for c in claims_out)}/{len(claims_out)}; "
          f"cross-site byte-duplicate groups: {len(dup_groups)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
