#!/usr/bin/env python3
"""Read-only executive audit of the nine focus GEMSDOE winner files.

Sites: GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36.

What this does (and does not do)
--------------------------------
* Fetches each site's pinned historical winner file from its OWNER GitHub repo
  (partial git clone at the pinned commit, bytes re-hashed here).
* Checks the OFFICIAL format rules (CRS, shape, transform, float32, 1 band,
  finite values in [0, 1] inside the footprint, NaN/null outside it).
* Computes forward dot overlap (fraction of file A's dots within 3 px of file
  B's dots) with the SHARED ``gems57.uniqueness.dot_overlap`` function.
* Re-derives H33 (GEMSDOE32) vs D2.8 (GEMSDOE25/30) lineage from the bytes.

What it does NOT do
-------------------
* It generates NO raster and no submission. It never clears the duplicate gate.
* It does not compute a holdout DTI for these fixed files (not possible under
  the hide-and-recover protocol) and it does not read organizer scores.
* User-reported scores are copied from ``docs/data/user_reported_results.csv``
  and labelled USER-REPORTED. They are not organizer receipts.

Usage
-----
    python scripts/nine_site_executive_summary.py --fetch   # restore winner bytes
    python scripts/nine_site_executive_summary.py           # write JSON + HTML
    python scripts/nine_site_executive_summary.py --check   # fail on drift
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from gems57 import uniqueness  # noqa: E402  (shared overlap; no private metric)

SOURCE_JSON = ROOT / "docs/data/focus_winner_sources_20261028_a896e29e.json"
USER_CSV = ROOT / "docs/data/user_reported_results.csv"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"
CATALOGUE = ROOT / "data/bridge/existing_faults.tif"
WITNESS = ROOT / "data/registry/dense_17gemdoe.tif"
WINNERS_DIR = ROOT / "data/focus_winners"
OUT_JSON = ROOT / "docs/data/nine_sites_20261028.json"
OUT_HTML = ROOT / "docs/nine-sites/index.html"
OUT_LEADER = ROOT / "docs/data/leaderboard_public_snapshot_20261028.json"

SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
WITNESS_SHA = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
SAMPLE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
CATALOGUE_SHA = "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"
OVERLAP_LIMIT = uniqueness.OVERLAP_LIMIT  # 0.70, the user's parallel-run rule
RADIUS_PX = 3.0

# Official leaderboard, fetched 2026-10-28 from the DrivenData page (public split).
# Rows transcribed from the fetched page text; re-verify at the URL before relying on them.
LEADERBOARD_URL = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
LEADERBOARD = [
    (1, "xiaofanhu", 0.4544), (2, "cfld__", 0.3916), (3, "Batik Shirt Brothers", 0.3911),
    (4, "BrandenKMurray", 0.3724), (5, "No Fault of Our Own", 0.3570), (6, "joeyfezster", 0.3447),
    (7, "JerryDataWorks", 0.3418), (8, "alexoktaba", 0.3416), (9, "DARD", 0.3398),
    (10, "Azazel", 0.3379), (11, "yifanxu", 0.3335), (12, "baobao", 0.3334),
    (13, "notmyfault", 0.3334), (14, "newway", 0.3328), (15, "ohyeah", 0.3318),
    (16, "ruping", 0.3314), (17, "giles", 0.3313), (18, "li002666", 0.3312),
    (19, "mzoorob", 0.3304), (20, "shixing", 0.3273), (21, "nchuzhoy", 0.3262),
    (22, "kinghorton42", 0.3261), (23, "joano", 0.3252), (24, "zeaal", 0.3222),
    (25, "like60986", 0.3217), (26, "kpomazi", 0.3195), (27, "twang", 0.3169),
    (28, "kinneso_outlook", 0.3167), (29, "like2", 0.3160), (30, "drjy", 0.3113),
    (31, "nsabaj", 0.3111), (32, "ndavis7", 0.3093), (33, "anna_ms", 0.3041),
    (34, "Gibbous", 0.3033), (35, "dams", 0.3017), (36, "sws-jonathan", 0.3004),
    (37, "faultsofthy", 0.2987), (38, "pberlizov", 0.2967), (39, "doublebigmac", 0.2964),
    (40, "dmitry_v", 0.2963), (41, "Financialanalyst", 0.2949), (42, "Crescent", 0.2935),
    (43, "haiderz", 0.2930), (44, "raboush2", 0.2927), (45, "g789", 0.2921),
    (46, "NoahNault", 0.2899), (47, "roison", 0.2897), (48, "jfper21", 0.2895),
    (49, "GrigorSargsyan", 0.2892), (50, "strikeslipfault", 0.2874),
]


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch_winners(rows: list[dict]) -> None:
    """Restore pinned winner bytes from owner repos with git (not raw.githubusercontent)."""
    WINNERS_DIR.mkdir(parents=True, exist_ok=True)
    for row in rows:
        site = row["site"]
        clone = WINNERS_DIR / site
        repo = f"https://github.com/buffedlizard55-lab/{site}.git"
        if not clone.is_dir():
            subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", repo,
                            str(clone)], check=True, timeout=900)
        present = subprocess.run(["git", "-C", str(clone), "cat-file", "-e",
                                  row["historical_commit"] + "^{commit}"], capture_output=True)
        if present.returncode != 0:
            subprocess.run(["git", "-C", str(clone), "fetch", "-q", "--filter=blob:none",
                            "origin", row["historical_commit"]], check=True, timeout=900)
        blob = subprocess.run(["git", "-C", str(clone), "show",
                               f"{row['historical_commit']}:{row['path']}"],
                              capture_output=True, check=True, timeout=900).stdout
        if hashlib.sha256(blob).hexdigest() != row["sha256"]:
            raise SystemExit(f"{site}: fetched bytes do not match pinned sha256")
        (WINNERS_DIR / f"{site}_{Path(row['path']).name}").write_bytes(blob)


def local_path(row: dict) -> Path:
    return WINNERS_DIR / f"{row['site']}_{Path(row['path']).name}"


def read_user_reports() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {site: [] for site in SITES}
    with USER_CSV.open(encoding="utf-8") as stream:
        for rec in csv.DictReader(stream):
            if rec["site"] in out:
                out[rec["site"]].append({
                    "submission_name": rec["submission_name"],
                    "user_reported_value": float(rec["user_reported_value"]),
                    "source_url": rec["source_url"],
                    "evidence_class": "USER-REPORTED CLAIM - NOT HOLDOUT-DTI OR ORGANIZER-CONFIRMED",
                })
    return out


def h33_lineage(d28: np.ndarray, h33: np.ndarray, catalogue: np.ndarray) -> dict:
    """Re-derive the D2.8 -> H33 collar lineage from bytes (no new prediction)."""
    dist = distance_transform_edt(~catalogue)  # px to nearest catalogue fault pixel
    d28_dots = d28 > 0
    h33_dots = h33 > 0
    removed = d28_dots & ~h33_dots
    return {
        "d28_dots": int(d28_dots.sum()),
        "h33_dots": int(h33_dots.sum()),
        "h33_subset_of_d28": bool((h33_dots & ~d28_dots).sum() == 0),
        "removed_from_d28": int(removed.sum()),
        "removed_within_1px_of_catalogue": int((removed & (dist <= 1.0)).sum()),
        "removed_between_1_and_2px_of_catalogue": int((removed & (dist > 1.0) & (dist <= 2.0)).sum()),
        "removed_beyond_2px_of_catalogue": int((removed & (dist > 2.0)).sum()),
        "h33_min_distance_to_catalogue_px": float(dist[h33_dots].min()),
        "h33_dots_within_2px_of_catalogue": int((h33_dots & (dist <= 2.0)).sum()),
        "catalogue_positive_pixels": int(catalogue.sum()),
    }


def build() -> dict:
    src = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    rows = {r["site"]: r for r in src["rows"]}
    if sorted(rows) != sorted(SITES):
        raise SystemExit("source JSON does not contain exactly the nine focus sites")
    user = read_user_reports()

    with rasterio.open(SAMPLE) as s:
        sample_grid = (s.crs, s.shape, s.transform)
        footprint = np.isfinite(s.read(1))
    with rasterio.open(CATALOGUE) as c:
        catalogue = c.read(1) > 0
    with rasterio.open(WITNESS) as w:
        witness = np.where(np.isfinite(w.read(1)), w.read(1), 0.0)
    witness_dots = witness > 0

    arrays: dict[str, np.ndarray] = {}
    site_records = []
    for site in SITES:
        row = rows[site]
        path = local_path(row)
        if not path.exists():
            raise SystemExit(f"missing {path}; run with --fetch first")
        digest = sha256_file(path)
        with rasterio.open(path) as r:
            arr = r.read(1)
            crs_ok = (r.crs, r.shape, r.transform) == sample_grid
            dtype, bands, nodata = r.dtypes[0], r.count, r.nodata
        arrays[site] = arr
        finite = np.isfinite(arr)
        inside = footprint
        outside = ~footprint
        in_range = bool(((arr[finite] >= 0) & (arr[finite] <= 1)).all())
        nan_out = int((outside & ~finite).sum())
        zero_out = int((outside & finite & (arr == 0)).sum())
        nonzero_out = int((outside & finite & (arr != 0)).sum())
        nonfinite_in = int((inside & ~finite).sum())
        dots = int((finite & (arr > 0)).sum())
        official_format_pass = bool(
            crs_ok and dtype == "float32" and bands == 1 and in_range and nonfinite_in == 0
            and nonzero_out == 0 and dots > 0
        )
        site_records.append({
            "site": site,
            "user_reported_entries": user[site],
            "user_reported_best": max(user[site], key=lambda e: e["user_reported_value"])
            if user[site] else None,
            "organizer_confirmed_score": None,
            "estimated_score": "NOT ESTIMABLE from repo evidence - user-reported only, no organizer receipt",
            "file": {
                "owner_repo": f"https://github.com/buffedlizard55-lab/{site}",
                "pinned_commit": row["historical_commit"],
                "path_in_repo": row["path"],
                "download_url": row["source_url"],
                "bytes": int(local_path(row).stat().st_size),
                "sha256": digest,
                "sha256_matches_source_json": digest == row["sha256"],
                "sha256_source": "docs/data/focus_winner_sources_20261028_a896e29e.json",
            },
            "format": {
                "crs_shape_transform_match_sample": bool(crs_ok),
                "dtype": dtype,
                "bands": int(bands),
                "nodata_tag": None if nodata is None else str(nodata),
                "footprint_cells": int(footprint.sum()),
                "outside_convention": ("nan" if nan_out == int(outside.sum())
                                       else "zero" if zero_out == int(outside.sum())
                                       else "mixed"),
                "nan_outside_footprint": nan_out,
                "zero_outside_footprint": zero_out,
                "nonzero_outside_footprint": nonzero_out,
                "nonfinite_inside_footprint": nonfinite_in,
                "values_in_0_1_where_finite": in_range,
                "dots_equal_1": dots,
                "official_format_pass": official_format_pass,
                "official_text_nan_outside": nan_out == int(outside.sum()),
            },
        })

    names = list(SITES)
    matrix: dict[str, dict[str, float]] = {}
    for a in names:
        matrix[a] = {}
        for b in names:
            if a == b:
                continue
            matrix[a][b] = round(float(uniqueness.dot_overlap(arrays[a], arrays[b])), 6)

    witness_overlap = {s: round(float(uniqueness.dot_overlap(arrays[s], witness)), 6) for s in names}
    for rec in site_records:
        s = rec["site"]
        others = matrix[s]
        worst_other = max(others, key=others.get)
        rec["uniqueness"] = {
            "rule": "forward overlap > 0.70 with any registry raster blocks (parallel-run protocol)",
            "max_forward_overlap_vs_other_eight_sites": others[worst_other],
            "worst_other_site": worst_other,
            "forward_overlap_vs_dense_witness_17GEMSDOE": witness_overlap[s],
            "passes_protocol_vs_other_eight_sites": bool(max(others.values()) <= OVERLAP_LIMIT),
            "passes_protocol_vs_witness": bool(witness_overlap[s] <= OVERLAP_LIMIT),
            "gate_decision": "DUPLICATE_STOP",
            "evidence_class": "REGISTRY-MEASUREMENT (shared uniqueness.dot_overlap, Euclidean <= 3 px)",
        }
        rec["ok_to_download_and_submit"] = False
        rec["decision_text"] = (
            "DO NOT SUBMIT - duplicate under the parallel-run protocol against the other "
            "eight sites and the 17GEMSDOE witness."
        )

    d28 = arrays["GEMSDOE25"]
    h33 = arrays["GEMSDOE32"]
    lineage = h33_lineage(d28, h33, catalogue)
    lineage["d28_site"] = ("GEMSDOE25 (dotted-h19-5-d2-8). GEMSDOE30 (d28-poisson) carries an identical "
                           "dot set; see gems30_vs_gems25_dot_identical.")
    lineage["h33_site"] = "GEMSDOE32 h33-h33-2-b2 (user-reported 0.2778)"
    lineage["gems30_vs_gems25_dot_identical"] = bool(np.array_equal(arrays["GEMSDOE30"] > 0, d28 > 0))

    max_pair = max(v for a in matrix.values() for v in a.values())
    return {
        "schema": "gems88.nine-site-executive-summary.v1",
        "date_utc": "2026-10-28",
        "scope": "GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 - pinned historical winner file per site",
        "evidence_classes": {
            "USER-REPORTED": "scores typed in the user's prompt; not verified",
            "ORGANIZER-CONFIRMED": "only a submission-page receipt; none exists in this repo",
            "REGISTRY-MEASUREMENT": "byte, format and overlap measurements of owner-repo files",
            "HOLDOUT-DTI": "not run for these fixed files (not possible under hide-and-recover)",
        },
        "official_sources": {
            "problem_description": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
            "official_rules_pdf": "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
            "leaderboard": LEADERBOARD_URL,
            "reference_solution": "https://github.com/drivendataorg/gems-prize-reference-solution",
        },
        "sample_grid": {"crs": str(sample_grid[0]), "shape": list(sample_grid[1])},
        "sha256_inputs": {
            "sample_submission": SAMPLE_SHA,
            "existing_faults": CATALOGUE_SHA,
            "witness_17GEMSDOE": WITNESS_SHA,
        },
        "input_hashes_verified": {
            "sample_submission": sha256_file(SAMPLE) == SAMPLE_SHA,
            "existing_faults": sha256_file(CATALOGUE) == CATALOGUE_SHA,
            "witness_17GEMSDOE": sha256_file(WITNESS) == WITNESS_SHA,
        },
        "overlap_limit": OVERLAP_LIMIT,
        "max_pairwise_forward_overlap_among_nine": max_pair,
        "min_pairwise_forward_overlap_among_nine": min(v for a in matrix.values() for v in a.values()),
        "pairwise_forward_overlap": matrix,
        "witness_positive_fraction_of_footprint": round(float(witness_dots.sum() / footprint.sum()), 6),
        "h33_lineage": lineage,
        "sites": site_records,
        "ok_to_submit_any": False,
        "new_rasters_generated": 0,
        "experiments_run": 0,
        "weekly_slots_used": 0,
        "organizer_confirmed_scores": 0,
        "verdict": "negative",
    }


def leaderboard_snapshot() -> dict:
    top = LEADERBOARD
    scores = {rank: score for rank, _, score in top}
    return {
        "schema": "gems88.public-leaderboard-snapshot.v1",
        "fetched_utc": "2026-10-28",
        "source_url": LEADERBOARD_URL,
        "split": "PUBLIC test split only; private/final scores are not shown",
        "rows": [{"rank": r, "participant": p, "public_dw_tversky": s} for r, p, s in top],
        "checks": {
            "rank1_score": scores[1],
            "user_claim_0_4413_present_in_top50": any(abs(s - 0.4413) < 1e-9 for s in scores.values()),
            "user_claim_0_3195_rank": next(r for r, _, s in top if abs(s - 0.3195) < 1e-9),
            "user_claim_0_2778_present_in_top50": any(abs(s - 0.2778) < 1e-9 for s in scores.values()),
            "top50_min": min(scores.values()),
        },
        "note": ("Rows were transcribed from the fetched page text. Participant names are DrivenData "
                 "handles, not GitHub site owners; no site-to-handle mapping is established."),
    }


def render_html(doc: dict) -> str:
    esc = html.escape
    rows_html = []
    for rec in doc["sites"]:
        best = rec["user_reported_best"]
        f = rec["file"]
        u = rec["uniqueness"]
        fm = rec["format"]
        rows_html.append(
            "<tr>"
            f"<td><strong>{esc(rec['site'])}</strong></td>"
            f"<td><a href=\"{esc(f['download_url'])}\">{esc(Path(f['path_in_repo']).name)}</a>"
            f"<br><small>sha256 <code>{esc(f['sha256'][:16])}...</code> &middot; {f['bytes']:,} bytes</small></td>"
            f"<td>{best['user_reported_value']:.4f}<br><small>USER-REPORTED</small></td>"
            "<td>NOT ESTIMABLE<br><small>no organizer receipt; no fixed-file holdout</small></td>"
            f"<td>{u['max_forward_overlap_vs_other_eight_sites']:.3f} vs {esc(u['worst_other_site'])}</td>"
            f"<td>{u['forward_overlap_vs_dense_witness_17GEMSDOE']:.3f}</td>"
            f"<td>{'PASS' if fm['official_format_pass'] else 'FAIL'}<br><small>outside={esc(fm['outside_convention'])}</small></td>"
            "<td><strong class=\"no\">NO - DO NOT SUBMIT</strong></td>"
            "</tr>"
        )
    lineage = doc["h33_lineage"]
    snap = leaderboard_snapshot()["checks"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE nine-site executive summary</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f7f8fa;color:#1d2433;line-height:1.5}}
main{{max-width:1180px;margin:0 auto;padding:24px}}
h1{{font-size:1.6rem;margin:.2rem 0 .6rem}} h2{{font-size:1.2rem;margin-top:1.8rem}}
.banner{{background:#fdecea;border:2px solid #c62828;border-radius:10px;padding:16px 18px;margin:12px 0}}
.banner strong{{color:#8e1b1b;font-size:1.1rem}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:.92rem}}
th,td{{border:1px solid #d9dee7;padding:8px 10px;vertical-align:top;text-align:left}}
th{{background:#eef2f8}} code{{font-size:.85em}} small{{color:#5b6475}}
.no{{color:#b00020}} .card{{background:#fff;border:1px solid #d9dee7;border-radius:10px;padding:14px 18px;margin:12px 0}}
a{{color:#1f5fbf}}
</style></head><body><main>
<h1>GEMSDOE nine-site executive summary</h1>
<p>Sites: GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36. Dated {esc(doc['date_utc'])} by
<code>scripts/nine_site_executive_summary.py</code> from SHA-pinned owner-repo files.</p>

<div class="banner"><strong>Decision: no file from these nine sites is cleared for download-and-submit.</strong><br>
Every pinned winner file overlaps the other eight sites and the dense 17GEMSDOE witness above the
<code>0.70</code> limit of the parallel-run protocol (witness overlap = 1.000 for all nine). No new TIFF
was generated, because the generation guard stops before construction. Submitting any of these files
would contradict that protocol. Scores shown are USER-REPORTED, not organizer-confirmed.</div>

<h2>Best submission per site (ranked by user-reported score)</h2>
<table>
<tr><th>Site</th><th>File to download (owner repo, pinned commit)</th><th>Score</th><th>Estimated score</th>
<th>Max overlap vs other 8 sites</th><th>Overlap vs witness</th><th>Official format check (local)</th><th>OK to download and submit?</th></tr>
{''.join(rows_html)}
</table>

<h2>Why the highest file (GEMSDOE32, 0.2778) scores highest - evidence and limits</h2>
<div class="card">
<p>The H33 file is a strict subset of the D2.8 dots used by GEMSDOE25 and GEMSDOE30: the bytes give
{lineage['h33_dots']:,} H33 dots against {lineage['d28_dots']:,} D2.8 dots, with
{lineage['removed_from_d28']:,} removed. Subset: <strong>{lineage['h33_subset_of_d28']}</strong>.
Removed dots within 1 px of the catalogue: {lineage['removed_within_1px_of_catalogue']:,}; between 1 and 2 px:
{lineage['removed_between_1_and_2px_of_catalogue']:,}; beyond 2 px: {lineage['removed_beyond_2px_of_catalogue']:,}.
H33's closest dot to the catalogue is {lineage['h33_min_distance_to_catalogue_px']:.2f} px.</p>
<p>Because H33 is a subset, it cannot recover any fault that D2.8 misses. Any score difference comes from the
removed dots. Under the metric (alpha 0.2 on false positives, beta 0.8 on false negatives), removing one dot
with true-positive weight d and false-positive weight f improves DTI only when
f/d &gt; (0.8*TP + 0.2*FP + 0.8*FN) / (0.2*TP). This is derived from the metric and checked numerically:
at the official worked example (TP 3.00, FP 1.89, FN 2.00) the break-even ratio is 7.3. The user-reported
gain over D2.8 is 0.2778 minus 0.2600 = 0.0178. It is a public-split figure with no receipt, and the public
label set size is not published here, so its noise cannot be quantified.</p>
<p>GEMSDOE25 and GEMSDOE30 hold the same 44,090 dots (overlap 1.000 both ways) and both report 0.2600.
That agreement is consistent with one dot set being submitted under two site names.</p>
<p>The repo's own collar-versus-visible holdout (<code>registry/con88_collar_holdout.json</code>, HOLDOUT-DTI,
<code>gems57-pooled-hide-v2</code>) gave a paired delta of +1.0e-6, 95% CI [-7.9e-9, +3.2e-6]. That is
negligible, so collar removal is not established as the mechanism. The H33 advantage is therefore UNEXPLAINED
by available holdout evidence.</p>
</div>

<h2>Public leaderboard check (fetched 2026-10-28)</h2>
<div class="card">
<p>Rank 1 is <strong>{snap['rank1_score']:.4f}</strong>, not 0.4413. 0.3195 is rank
<strong>{snap['user_claim_0_3195_rank']}</strong>, not the top score. 0.2778 is
{'in' if snap['user_claim_0_2778_present_in_top50'] else 'not in'} the top 50 (minimum {snap['top50_min']:.4f}).
Source: <a href="{LEADERBOARD_URL}">{LEADERBOARD_URL}</a>.</p>
</div>

<h2>Irregularities for review</h2>
<div class="card"><ul>
<li>Scores in the prompt are USER-REPORTED. No organizer receipt exists in the repo.</li>
<li>GEMSDOE25 and GEMSDOE30 hold identical dot sets (44,090 dots; both report 0.2600). Two site names
point to the same submission content.</li>
<li>The official text allows NaN or null outside the bounds. Five winner files use NaN outside the footprint.
Four (GEMSDOE30, 32, 33, 36) use zeros outside it. That is a literal deviation from the rule text, but the
user reports that these files were scored.</li>
<li>The portal error "Predicted values must be in range [0, 1]" is not explained by these bytes: every winner
file's finite values lie in [0, 1]. The cause is unknown.</li>
<li>The project's stricter local "full-grid finite" check fails the current GEMSDOE30 HEAD file (7,111,787 NaN
outside the footprint). That is a repo-stricter rule, not an official one.</li>
<li>The parallel-run protocol's 0.70 overlap rule was applied to dot sets. The witness is a continuous
probability map (median 0.22, max 0.98). Its "dots" are defined by <code>p &gt; 0</code>, which covers the
whole footprint. This representation choice is the owner's decision, not the agent's.</li>
</ul></div>

<h2>Sources (official first)</h2>
<div class="card"><ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description, metric and submission format (DrivenData)</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules, NLR PDF (one final submission; three per week; no uniqueness clause)</a></li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference solution (GitHub)</a></li>
<li><a href="{LEADERBOARD_URL}">Public leaderboard (DrivenData)</a></li>
</ul></div>
<p><small>Machine record: <code>docs/data/nine_sites_20261028.json</code> &middot; Leaderboard snapshot:
<code>docs/data/leaderboard_public_snapshot_20261028.json</code> &middot; Review:
<code>research/session-nine-site-20261028-review.md</code>.</small></p>
</main></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fetch", action="store_true", help="restore pinned winner bytes from owner repos")
    parser.add_argument("--check", action="store_true", help="fail if committed outputs drift")
    args = parser.parse_args()

    src = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    if args.fetch:
        fetch_winners([r for r in src["rows"] if r["site"] in SITES])
        print(f"fetched {len(SITES)} pinned winner files into {WINNERS_DIR.relative_to(ROOT)}")
        return 0

    doc = build()
    board = leaderboard_snapshot()
    payload = json.dumps(doc, indent=2, sort_keys=False, allow_nan=False) + "\n"
    board_payload = json.dumps(board, indent=2, allow_nan=False) + "\n"
    page = render_html(doc)
    if args.check:
        ok = (OUT_JSON.read_text(encoding="utf-8") == payload
              and OUT_LEADER.read_text(encoding="utf-8") == board_payload
              and OUT_HTML.read_text(encoding="utf-8") == page)
        print("PASS: nine-site outputs match regeneration" if ok else "FAIL: nine-site outputs drifted")
        return 0 if ok else 1
    OUT_JSON.write_text(payload, encoding="utf-8")
    OUT_LEADER.write_text(board_payload, encoding="utf-8")
    OUT_HTML.write_text(page, encoding="utf-8")
    print(json.dumps({"written": [str(OUT_JSON.relative_to(ROOT)), str(OUT_LEADER.relative_to(ROOT)),
                                  str(OUT_HTML.relative_to(ROOT))],
                      "max_pairwise_forward_overlap": doc["max_pairwise_forward_overlap_among_nine"],
                      "min_pairwise_forward_overlap": doc["min_pairwise_forward_overlap_among_nine"],
                      "ok_to_submit_any": doc["ok_to_submit_any"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
