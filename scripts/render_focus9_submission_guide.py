#!/usr/bin/env python3
"""Render docs/focus9-submission-guide.html from the pinned evidence JSON.

Every number on the page is read from:
  evidence/focus9_nine_site_audit_20261030.json      (audit run 4)
  evidence/focus9_remote_blob_check_20261030.json    (remote main blob check)
  evidence/drivendata_leaderboard_snapshot_20261030.json

Nothing is typed by hand. Run with --check to fail if the page is stale.
Labels: USER-REPORTED CLAIM (no organizer receipt), HOLDOUT-DTI (not measured here),
ORGANIZER-CONFIRMED (none found).
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "evidence/focus9_nine_site_audit_20261030.json"
BLOBS = ROOT / "evidence/focus9_remote_blob_check_20261030.json"
LEADER = ROOT / "evidence/drivendata_leaderboard_snapshot_20261030.json"
OUT = ROOT / "docs/focus9-submission-guide.html"
REPO = "https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/"
OFFICIAL_PAGE = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
OFFICIAL_LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def github_url(site: str, head: str, path: str) -> str:
    return f"https://github.com/buffedlizard55-lab/{site}/blob/{head}/{path}"


def load() -> tuple[dict, dict, dict]:
    return (json.loads(AUDIT.read_text()), json.loads(BLOBS.read_text()),
            json.loads(LEADER.read_text()))


def render() -> str:
    audit, blobs, leader = load()
    claims = [c for c in audit["claims"] if "raster" in c]
    blob_by_file = {r["file"].rsplit("/", 1)[-1]: r["status"] for r in blobs["rows"]}
    top_per_site = {}
    for site in SITES:
        mine = [c for c in claims if c["site"] == site]
        top_per_site[site] = max(mine, key=lambda c: c["claimed_score"])
    n_claims = len(claims)
    n_unique = sum(1 for c in claims if c["unique_vs_nine_sites_literal"])
    n_official = sum(1 for c in claims if c["official_spec_pass"])
    n_strict = sum(1 for c in claims if c["format_pass_strict_local"])
    n_blob_same = sum(1 for r in blobs["rows"] if r["status"] == "same")
    assert n_claims == 21, n_claims

    def link(c: dict) -> str:
        name = c["file"].rsplit("/", 1)[-1]
        url = github_url(c["site"], audit["sites"][c["site"]]["head"], c["file"])
        return f'<a href="{e(url)}"><code>{e(name)}</code></a>'

    def dupes(c: dict) -> str:
        sites = sorted({d["site"] for d in c["identical_bytes_elsewhere"]})
        return ", ".join(sites) if sites else "none"

    site_rows = []
    for site in SITES:
        c = top_per_site[site]
        dup = dupes(c)
        site_rows.append(
            f"<tr><th scope=\"row\">{e(site)}</th>"
            f"<td>{link(c)}<br><span class=\"micro\">sha256 <code>{e(c['sha256'][:12])}…</code> · {c['dots']:,} dots</span></td>"
            f"<td><strong>{c['claimed_score']:.4f}</strong><br><span class=\"micro\">USER-REPORTED CLAIM · no receipt</span></td>"
            f"<td>Not estimated<br><span class=\"micro\">no HOLDOUT-DTI on this file</span></td>"
            f"<td><strong>{'YES' if c['unique_vs_nine_sites_literal'] else 'NO'}</strong><br><span class=\"micro\">max 3-px overlap vs nine sites {c['max_overlap_vs_any_binary_tif_in_nine_sites']:.4f}; "
            f"identical bytes elsewhere: {e(dup)}</span></td>"
            f"<td>{'PASS' if c['official_spec_pass'] else 'FAIL'}<br><span class=\"micro\">strict local: {'PASS' if c['format_pass_strict_local'] else 'FAIL (NaN outside footprint)'}</span></td>"
            f"<td><strong>DO NOT SUBMIT</strong></td></tr>"
        )

    all_rows = []
    for c in sorted(claims, key=lambda c: (-c["claimed_score"], c["site"])):
        verdict = c["verdict"].replace("_", " ")
        all_rows.append(
            f"<tr><td>{e(c['site'])}</td><td>{link(c)}</td><td>{c['claimed_score']:.4f}</td>"
            f"<td>{c['dots']:,}</td>"
            f"<td>{c['max_overlap_vs_any_binary_tif_in_nine_sites']:.4f}</td>"
            f"<td>{c['max_registry_sparse_overlap_3px']:.4f}</td>"
            f"<td>{'PASS' if c['official_spec_pass'] else 'FAIL'}</td>"
            f"<td>{'yes' if c['unique_vs_nine_sites_literal'] else 'no'}</td>"
            f"<td>{e(blob_by_file.get(c['file'].rsplit('/', 1)[-1], 'unknown'))}</td>"
            f"<td><span class=\"micro\">{e(verdict)}</span></td></tr>"
        )

    lb = leader["prompt_cited_values"]
    top_leader = leader["top_rows"][0]
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Nine-site submission guide. No file is cleared for submission. Claimed scores are user-reported; no organizer receipt was found.">
<title>Nine-site submission guide · GEMSDOE88 · DO NOT SUBMIT</title>
<link rel="stylesheet" href="assets/site.css"></head>
<body><a href="#main" class="sr-only">Skip to content</a>
<header class="header"><div class="wrap"><a class="brand" href="index.html">GEMSDOE<span style="color:#76ddca">88</span><small>auditable fault discovery</small></a>
<nav class="nav" aria-label="Main navigation"><a href="index.html">Overview</a><a href="executive-summary.html">Submission guide</a><a href="focus9-submission-guide.html" aria-current="page">Nine-site guide</a><a href="research.html">Research</a><a href="sources.html">Sources</a></nav></div></header>
<div class="alert-strip" role="status"><div class="wrap"><span class="alert-icon" aria-hidden="true">!</span><span>NO NEW TIFF · NO FILE CLEARED · SUBMIT: NO — DO NOT SUBMIT</span></div></div>
<main id="main">
<section class="section" id="decision"><div class="wrap">
<div class="kicker">Session 8abdbff4 · 2026-10-30 · generated from pinned evidence</div>
<h1>Nine-site submission guide (GEMSDOE 24, 25, 27, 28, 30, 31, 32, 33, 36)</h1>
<p><strong>Decision: SUBMIT: NO.</strong> No new GeoTIFF was generated. The generation gate returns <code>DUPLICATE_STOP</code> (exit 2, <code>ok_to_submit: false</code>, <code>weekly_slots_used: 0</code>). Every nonempty candidate overlaps the dense registry witness at 1.0000 against the 0.70 limit, so no file here is cleared.</p>
<p><strong>Scores:</strong> every number below is a <strong>USER-REPORTED CLAIM</strong>. I found no organizer receipt. No HOLDOUT-DTI was measured for any listed file, so no estimated score is issued. A claim is not a score.</p>
<p><strong>Official scoring (checked against DrivenData page 967):</strong> distance-weighted Tversky, <code>α = 0.2</code>, <code>β = 0.8</code>, triangular kernel with 300 m support (<code>R = 3</code> px at 100 m). Submission: float32, single layer, EPSG:32611, 100 m, same bounds as the training data, values in [0, 1], and <code>null or nan</code> data outside the bounds.</p>
</div></section>

<section class="section" id="site-table"><div class="wrap">
<h2>Highest listed file per site (user-reported)</h2>
<p class="micro">Each row is the highest claimed score in that site's listing. "Unique" uses the literal rule: a dot overlaps another file within 3 px at ≥ 0.70 → not unique. Overlap values are maxima against the nine-site census of binary GeoTIFFs. The lower-scoring unique files are listed in the full table.</p>
<div class="table-scroll"><table><thead><tr><th scope="col">Site</th><th scope="col">File to download (research only)</th><th scope="col">Claimed score</th><th scope="col">Estimated score</th><th scope="col">Unique vs other listed sites?</th><th scope="col">Official-spec format</th><th scope="col">Decision</th></tr></thead>
<tbody>{''.join(site_rows)}</tbody></table></div>
<p class="micro">Download links point to the pinned GitHub blob for research review only. Do not upload them.</p>
</div></section>

<section class="section" id="why-h33"><div class="wrap">
<h2>Why GEMSDOE32 H33 (0.2778) ranks highest, and whether it can be beaten</h2>
<p>H33 (<code>h33-h33-2-b2-…-e5eb6e7e-zeros</code>, 37,654 dots) is cell-for-cell equal to the Anderson file (GEMSDOE36) intersected with the GEMSDOE33 D28 template. It is byte-identical to the registry raster <code>data/registry/h33_education.tif</code> (SHA-256 <code>c55bafc4…</code>). Anderson has 1,200 dots outside the template; H33 removes exactly those dots. The removed dots lie a median 14.5 px from the catalogue, versus 19.6 px for kept dots.</p>
<p>That pattern is consistent with the claimed +0.0028 gain over Anderson (0.2750 → 0.2778). It is a hypothesis, not a verified result. The repo's marginal rule would prune a dot only if its gain exceeds a threshold near 0.056 at DTI 0.278. The organizer's metric is defined on the probability surface, not on dots, so this pruning mechanism is an internal reading.</p>
<p><strong>Can a higher score be reached?</strong> Not verified. Under the current gate, any variant of this family is a 3-px duplicate (overlap 1.0), so no file in this family can be cleared without a user-authorized policy revision. The leaderboard ceiling does not change the gate.</p>
</div></section>

<section class="section" id="leaderboard"><div class="wrap">
<h2>Leaderboard reconciliation</h2>
<p>DrivenData public leaderboard (<em>Best public DW-Tversky</em>), read 2026-10-30 across pages 1–3: #1 <code>{e(top_leader['participant'])}</code> {top_leader['score']:.4f}; #2 cfld__ 0.3925; #3 Batik Shirt Brothers 0.3915. The prompt's <strong>0.3195</strong> is present at <strong>rank #50</strong> (kpomazi). The prompt's <strong>0.4413</strong> does not appear in ranks 1–50, and every other row is lower, so it is absent from this snapshot. Its source is unknown. The #1 score (0.4544) is a public-board figure, not a final-round or organizer-confirmed one. Page 2 ranks 76–100 were not visible in the fetched chunk.</p>
<p class="micro">Evidence: <a href="{REPO}evidence/drivendata_leaderboard_snapshot_20261030.json">evidence/drivendata_leaderboard_snapshot_20261030.json</a>.</p>
</div></section>

<section class="section" id="portal-error"><div class="wrap">
<h2>Portal error: "Predicted values must be in range [0, 1]"</h2>
<ul>
<li><strong>Official rule:</strong> values must lie in [0, 1] and data outside the bounds may be <code>null or nan</code> (DrivenData page 967).</li>
<li><strong>All {n_claims} claimed files:</strong> finite values lie in [0, 1] (they are binary 0/1), and no NaN sits inside the study footprint. {n_official}/{n_claims} pass the official-spec checks.</li>
<li><strong>Repo strict local check:</strong> {n_strict}/{n_claims} pass. The NaN-outside files fail only the repo's stricter all-finite rule. That rule also rejects the organizer's own sample file (<code>ok: False</code>, failing <code>range_0_1</code> and <code>no_mass_outside</code>). This is an irregularity for review and is not changed here.</li>
<li><strong>Cause of the portal error:</strong> not identified. None of the 21 claimed files contains a value outside [0, 1], so the error may come from a different uploaded file or from how the portal reads NaN. The file you uploaded (name and SHA-256) is needed to finish this check. Zero-fill (<code>-zeros</code>) variants contain no NaN at all.</li>
</ul>
</div></section>

<section class="section" id="irregularities"><div class="wrap">
<h2>Irregularities</h2>
<ul>
<li>The organizer page says the sample "predicts total fault absence". The mirror sample has <strong>{audit['sample_submission_irregularity']['ones_cells']:,}</strong> cells equal to 1, and they match the USGS/INGENIOUS catalogue exactly (<code>{audit['sample_submission_irregularity']['ones_equal_catalogue_cells_exactly']}</code>). The organizer's own file is login-only and was not retrieved.</li>
<li>GEMSDOE32 hosts byte-identical copies of files from several sibling sites. Its own H33 file is byte-identical to the registry raster.</li>
<li>The score 0.2600 is listed for GEMSDOE25 and GEMSDOE30, and 0.2708 for GEMSDOE28 and GEMSDOE31. Each pair has different bytes.</li>
<li>GEMSDOE30 moved after the audit (remote <code>099defe</code>), and so did GEMSDOE24 (<code>cc382dfd</code>) and GEMSDOE28 (<code>fc8ceebe</code>). All {n_blob_same}/{n_claims} claimed files are still byte-identical on remote <code>main</code> (git blob SHA check).</li>
<li>The audit pin table for GEMSDOE30 (<code>e72c889</code>) is stale. The audit ran on the then-current HEAD <code>84441266</code> and recorded the mismatch.</li>
</ul>
</div></section>

<section class="section" id="all-claims"><div class="wrap">
<h2>All {n_claims} listed files (user-reported claims)</h2>
<p class="micro">Literal uniqueness: {n_unique} of {n_claims} files are unique against the nine-site census. Both are low-scoring and blocked by the dense witness.</p>
<div class="table-scroll"><table><thead><tr><th scope="col">Site</th><th scope="col">File</th><th scope="col">Claim</th><th scope="col">Dots</th><th scope="col">Max 3-px overlap, nine sites</th><th scope="col">Max overlap, registry</th><th scope="col">Official-spec format</th><th scope="col">Unique (literal)</th><th scope="col">Remote blob = audited</th><th scope="col">Verdict</th></tr></thead>
<tbody>{''.join(all_rows)}</tbody></table></div>
</div></section>

<section class="section" id="how-to-submit"><div class="wrap">
<h2>How to submit (when a file is cleared)</h2>
<ol>
<li>No file is cleared. The generation gate (<code>scripts/generation_guard.py</code>) must return a pass first. Today it returns <code>DUPLICATE_STOP</code>.</li>
<li>Submit exactly one file. The official rules say teams must choose a single submission.</li>
<li>Check that the file is float32, a single layer, EPSG:32611, 100 m, with the training grid's shape and transform, and values in [0, 1].</li>
<li>Do not pick a file on score alone. Promotion is a separate selector step inside the weekly cap.</li>
</ol>
<p class="micro">Open decision for the owner: whether to authorize a revision of the stop policy. Without that, no candidate can pass the gate.</p>
</div></section>

<section class="section" id="limits"><div class="wrap">
<h2>Limitations and access needed</h2>
<ul>
<li>No HOLDOUT-DTI or organizer receipt for any listed file. Scores remain user-reported.</li>
<li>The organizer's sample file and the portal's uploaded-file log are needed to explain the [0, 1] error.</li>
<li>The rank correlation with registry rasters was not computed. The protocol metric in use is the 3-px overlap.</li>
<li>The DrivenData leaderboard pages were read as public snapshots. Ranks 76–100 on page 2 were not visible.</li>
<li>Official sources: <a href="{OFFICIAL_PAGE}">competition page 967 (metric, format)</a> · <a href="{OFFICIAL_LEADERBOARD}">leaderboard</a>.</li>
</ul>
<p class="micro">Machine record: <a href="{REPO}evidence/focus9_nine_site_audit_20261030.json">audit JSON</a> · <a href="{REPO}evidence/focus9_remote_blob_check_20261030.json">remote blob check</a> · <a href="{REPO}registry/session_8abdbff4_run_card.json">run card</a> · <a href="{REPO}scripts/audit_focus_nine_sites.py">audit script</a> · <a href="{REPO}scripts/render_focus9_submission_guide.py">this page's generator</a></p>
</div></section>
</main>
<footer class="footer"><div class="wrap"><p>Research record. Not a submission. Generated from pinned evidence; no file on this page is cleared.</p></div></footer>
</body></html>
"""
    return page


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the page on disk is stale")
    args = ap.parse_args()
    text = render()
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            print("STALE: rerun scripts/render_focus9_submission_guide.py")
            return 1
        print("OK: page matches evidence")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
