#!/usr/bin/env python3
"""Render one canonical decision above all archived lanes, from machine evidence.

No model, no writer, no portal access. --check rejects stale or hand-edited
primary panels. Historical HTML remains in a closed, explicitly marked archive.
"""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_research_state import inspect_legacy, inspect_queue  # noqa: E402

START = "<!-- CANONICAL-DECISION:START -->"
END = "<!-- CANONICAL-DECISION:END -->"
QUEUE_START = "<!-- RESEARCH-QUEUE:START -->"
QUEUE_END = "<!-- RESEARCH-QUEUE:END -->"


def read_inputs(root: Path) -> tuple[dict, dict, dict, dict]:
    current = json.loads((root / "docs/data/current_release.json").read_text())
    stop = json.loads((root / "registry/mtas88_run_card.json").read_text())
    audit = json.loads((root / "docs/data/download_audit.json").read_text())
    status = json.loads((root / "docs/status.json").read_text())
    focus = json.loads((root / "docs/data/focus_sites_20261026.json").read_text())
    verdict = focus["summary_verdict"]
    if not (
        current["ok_to_submit"] is False and current["ok_to_download"] is True
        and status["ok_to_submit"] is False and status["raster_sha256"] == current["file_sha256"]
        and stop["decision"] == "DUPLICATE_STOP" and stop["new_rasters_generated"] == 0
        and stop["preplacement_registry_proof"]["universal_overlap_blocker"] is True
        and audit["ok_to_submit"] is False and audit["canonical_sha256"] == current["file_sha256"]
        and audit["protocol_eligible_count"] == 0
        and verdict["focus_site_count"] == 9
        and verdict["unique_historical_champions_count"] == 0
        and verdict["cleared_for_submission_count"] == 0
        and verdict["ok_to_submit"] is False
    ):
        raise ValueError("canonical decision inputs disagree; never render a clearance")
    for key, digest_key in (("file", "file_sha256"), ("zip_file", "zip_sha256")):
        relative = Path(current[key])
        if relative.parent != Path("docs/downloads") or "DO-NOT-SUBMIT" not in relative.name:
            raise ValueError("canonical file must remain in research downloads with negative label")
        with (root / relative).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != current[digest_key]:
                raise ValueError("canonical downloadable bytes disagree with release card")
    return current, stop, audit, focus


def focus_sites_panel(focus: dict) -> str:
    rows = []
    for item in focus["focus_sites"]:
        site = escape(item["site"])
        url = escape(item["pages_url"])
        champ_obj = item["highest_scoring_submission"]
        champ = escape(champ_obj["prompt_name"])
        score = escape(str(champ_obj["user_reported_value"]))
        sha_short = escape(champ_obj["sha256"][:12])
        dots = f'{int(champ_obj["positive_pixels"]):,}'
        reg = champ_obj["vs_gemsdoe88_registry"]
        ov_h19 = f'{float(reg["gems19_h19_5_3px_forward_overlap"]):.4f}'
        ov_17 = f'{float(reg["dense_17gemdoe_3px_forward_overlap"]):.4f}'
        lineage = escape(champ_obj["lineage_role"])
        recent_list = item.get("recent_20261025_20261026_candidates", [])
        if recent_list:
            rec_parts = []
            for rc in recent_list:
                rname = escape(rc.get("submission_filename", "").removesuffix(".tif")[:28])
                rval = rc.get("user_reported_value")
                rtag = f' ({escape(str(rval))})' if rval else " (unscored)"
                rec_parts.append(f'<code style="overflow-wrap:anywhere">{rname}…</code>{rtag}: NO')
            recent = "<br>".join(rec_parts)
        else:
            recent = "No new 2026-10-25/26 TIFF (negative card)"
        rows.append(
            f'<tr><th scope="row"><a href="{url}">{site}</a></th>'
            f'<td style="overflow-wrap:anywhere"><code>{champ}</code><br><strong>{score}</strong> <span class="micro">(user-reported)</span></td>'
            f'<td><code>{sha_short}…</code><br>{dots} px</td>'
            f'<td><strong>UNIQUE: NO (DUPLICATE)</strong><br><code>{ov_h19}</code> / <code>{ov_17}</code></td>'
            f'<td>{lineage}</td>'
            f'<td>{recent}</td>'
            f'<td><span class="tag bad">DOWNLOAD: YES (RESEARCH)<br>SUBMIT: NO — DO NOT SUBMIT</span></td></tr>'
        )
    return (
        '<section class="focus-sites-section" id="focus-sites-executive-summary"><div class="wrap">'
        '<div class="section-heading"><div><div class="kicker">2026-10-26 forensic audit · 9 focus sites · 0/9 unique · 0/9 cleared</div>'
        '<h2>Executive summary: GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 &amp; 36</h2></div>'
        '<a href="data/focus_sites_20261026.json">Machine JSON ↗</a></div>'
        '<p>Every historical champion across all 9 focus sites (<code>0.2449</code>–<code>0.2778</code>, all unreceipted user-reported claims) '
        'has <code>0.9775–1.0000</code> 3-pixel forward overlap with <code>19GEMSDOE</code> <code>H19-5</code> and <code>1.0000</code> with '
        '<code>dense_17gemdoe.tif</code>: one nested <code>D1.5</code>/<code>D2.8</code>/<code>SOLO</code>/<code>H33-2-B2</code> ridge-pruning family (<strong>0/9 unique</strong>). '
        'Zero historical or <code>2026-10-25/26</code> candidates clear protocol gates—including <code>GEMSDOE27</code> <code>H31-1 DRCG-WL</code> '
        '(<code>IR-88-D634DE37-01</code>: <code>HOLDOUT-DTI = 0.047302</code> buffered / <code>0.115636</code> unbuffered, <code>88.79% &gt; 70%</code> 3-px coverage of <code>H29-S</code>, '
        'and <code>100%</code> <code>dense_17gemdoe</code> overlap), <code>GEMSDOE33</code> <code>A33-R2-HMDT</code> '
        '(<code>IR-88-D634DE37-02</code>: <code>33,616 / 42,000</code> (<code>80.04%</code>) positive pixels outside the study footprint, <code>108</code> on catalogue faults, '
        '<code>nn_min_px = 1.0</code> scanlines, and <code>Holdout: NOT MEASURED</code>), and <code>GEMSDOE32</code> <code>R6-1-stepprofile</code> '
        '(<code>IR-88-C59DB412-02</code>, now self-demoted to <code>DO NOT SUBMIT</code> in commit <code>9e55d5d</code>). '
        '<a href="data/focus_sites_20261026.csv" download>Download 9-site CSV</a> · '
        '<a href="research/session-d634de37-review.md">Full PhD forensic review (d634de37) →</a> · '
        '<a href="research/session-c59db412-review.md">Prior review (c59db412)</a></p>'
        '<div class="table-scroll"><table><thead><tr><th>Focus site</th><th>Best leaderboard submission &amp; claim</th>'
        '<th>SHA-256 &amp; dots</th><th>Unique? (3-px overlap H19-5 / 17GEMSDOE)</th><th>Why best scored &amp; lineage</th>'
        '<th>2026-10-25/26 candidates</th><th>OK to download / submit?</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div></div></section>"
    )


def inventory(audit: dict) -> str:
    rows = []
    all_rows = audit["artifacts"] + audit.get("additional_research_artifacts", [])
    for row in all_rows:
        directory = row.get("publication_directory", "downloads")
        if directory not in {"downloads", "research-variants"}:
            raise ValueError("unknown audited publication directory")
        name = escape(row["file"])
        label = name.removesuffix("-DO-NOT-SUBMIT.tif")
        if directory == "research-variants":
            label = "Historical variant · " + label
        download = (f'<a href="{directory}/{name}" download aria-label="Research-only TIFF {label}">TIFF</a> · '
                    f'<a href="{directory}/{escape(row.get("zip_file", ""))}" download>ZIP</a>'
                    if row["research_download_ok"] else "Quarantined — see audit")
        rows.append(f'<tr><th scope="row"><span class="mono">{label}</span></th>'
                    f'<td>{row.get("positive_pixels", 0):,}</td><td>{"PASS" if row["format_valid"] else "FAIL"}</td>'
                    f'<td>{download}</td><td><span class="tag bad">DO NOT SUBMIT</span></td></tr>')
    return (f'<section class="inventory-section"><div class="wrap"><details id="download-inventory" class="download-inventory">'
            f'<summary>All {len(all_rows)} archived research TIFFs · automated file audit</summary>'
            '<p>These are existing artifacts, not new submissions from this session. Different bytes are not proof of protocol uniqueness. '
            'Every nonempty allowed candidate is blocked by the same literal witness. '
            '<a href="data/download_audit.json">Full hashes, format checks, ZIP checks and duplicate groups (JSON)</a>.</p>'
            '<div class="table-scroll"><table><thead><tr><th>Archived file</th><th>Positive pixels</th><th>Local format</th>'
            '<th>Research download</th><th>Submission</th></tr></thead><tbody>' + ''.join(rows) +
            '</tbody></table></div></details></div></section>')


def render(root: Path, kind: str) -> str:
    current, stop, audit, focus = read_inputs(root)
    queue = inspect_queue(root)
    inspect_legacy(root)  # metadata can be public through legacy URLs as well
    first_choice = queue["proposals"][0]
    tif = escape(Path(current["file"]).relative_to("docs").as_posix())
    zipped = escape(Path(current["zip_file"]).relative_to("docs").as_posix())
    name, note = escape(current["submission_name"]), escape(current["submission_note"])
    digest = escape(current["file_sha256"])
    checked = escape(audit["checked_at_utc"])
    count = len(audit["artifacts"]) + len(audit.get("additional_research_artifacts", []))
    title = "Research download.<br>Not cleared to submit." if kind == "overview" else "How submission works.<br>Why it is blocked today."
    hero = f'''<section class="decision-hero" id="mtas-review" aria-labelledby="decision-title">
<div class="wrap" id="autonomous-review">
<div class="decision-kicker">Current review · 2026-10-26 · NO FILE APPROVED · 0/9 FOCUS SITES CLEARED</div>
<div class="decision-grid"><div>
<h1 id="decision-title">{title}</h1>
<p class="decision-lead"><strong>NO NEW TIFF: DUPLICATE — STOP.</strong> A freshly generated, protocol-unique competition TIFF could not be produced under the binding rule, and <strong>0/9</strong> inspected focus sites (<code>GEMSDOE24..36</code>) hold an unsubmitted protocol-unique candidate. No old prediction was copied or renamed as a new submission.</p>
<p>The pinned registry witness covers every allowed pixel: every nonempty dot set fails the literal overlap limit. These archived files are <strong>not unique under the binding all-registry rule</strong>.</p>
<div class="decision-pills"><span>DOWNLOAD FOR RESEARCH: YES</span><span class="blocked-pill">SUBMIT: NO — DO NOT SUBMIT</span></div>
<p class="micro">No competition slot used in this session. No organizer-confirmed score. Local validation does not require human inspection; it cannot establish hidden-label performance or choose a weekly slot. <a href="data/session_d634de37_run_card.json">Latest review’s negative run card (d634de37)</a> · <a href="data/focus_sites_20261026.json">9-focus-site audit JSON</a>.</p>
</div><aside class="decision-download" aria-label="Canonical archived research download">
<div class="decision-kicker">Existing research artifact · H88-TDKL · 2026-10-24</div>
<h2>Download the audited TIFF</h2>
<p>Single-band GeoTIFF · finite [0, 1] · exact pinned sample grid. <strong>Research only. Do not upload.</strong></p>
<a class="button button-primary decision-file" href="{tif}" download>↓ Download research TIFF</a>
<div class="download-secondary"><a href="{zipped}" download>One-TIFF ZIP</a><a href="data/download_audit.json">Automated audit ↗</a></div>
<dl class="download-identity"><dt>Name · historical file only</dt><dd><code>{name}</code></dd>
<dt>SHA-256 · exact TIFF</dt><dd><code>{digest}</code></dd></dl>
<details class="note-details"><summary>Historical note · {len(current['submission_note'])}/140 characters</summary><p><code>{note}</code></p><button class="copy" data-copy="{note}" type="button">Copy</button></details>
<p class="micro">Audit performed <time datetime="{checked}">{checked}</time>. This is a saved local audit, not a live portal check.</p>
</aside></div></div></section>
<section class="decision-gates"><div class="wrap">
<div class="section-heading"><div><div class="kicker">One decision, separate gates</div><h2>What is—and is not—validated</h2></div><a href="data/mtas88_run_card.json">Pre-placement proof JSON ↗</a></div>
<div class="gate-grid">
<article class="gate-card"><span class="tag">LOCAL FORMAT PASS</span><h3>File correctness</h3><p>All {count} published TIFFs were reopened. The canonical TIFF has no NaN or infinity, is within [0, 1], and matches CRS, shape and transform. It contains one full-resolution raster with self-contained georeferencing; its ZIP contains the same TIFF.</p></article>
<article class="gate-card"><span class="tag bad">UNIQUENESS FAIL</span><h3>Duplicate stop</h3><p>Registry measurement: the 17GEMSDOE witness covers all 5,106,385 allowed cells (overlap 1.00 &gt; 0.70), and all 9 focus-site champions overlap H19-5 at 0.9775–1.0000.</p></article>
<article class="gate-card"><span class="tag dim">NOT RUN THIS SESSION</span><h3>Scientific performance</h3><p>No new holdout or leakage canary was run after the prerequisite failed. Historical HOLDOUT-DTI is not a new candidate result and is not an organizer score.</p></article>
<article class="gate-card"><span class="tag bad">NO SLOT AUTHORIZED</span><h3>Competition eligibility</h3><p>A format pass cannot clear a duplicate, prove a leaderboard improvement, establish current quota, or authorize a submission. Slot selection remains separate.</p></article>
</div></div></section>''' + focus_sites_panel(focus)
    if kind == "overview":
        content = f'''<section class="decision-explainer"><div class="wrap split">
<div><div class="kicker">H33 &amp; 9-focus-site forensic answer</div><h2>Learn from the geometry.<br>Do not copy the submission.</h2>
<p><strong>0.2778 is a user-reported claim, not an ORGANIZER-CONFIRMED receipt.</strong> Byte-exact float64 auditing shows H33-2-B2 (<code>37,654</code> px) is an exact subset of SOLO-D2.8 (<code>40,199</code> px, <code>0.2708</code>) and D2.8 (<code>44,090</code> px, <code>0.2600</code>): under DTI (<code>α = 0.2</code> on FP, <code>β = 0.8</code> on FN), stripping <code>6,436</code> <code>d &lt;= 2 px</code> digitization-shadow dots removed denominator drag while preserving <code>41.74%</code> blind-basin (<code>&gt; 25 px</code>) discovery—matching our 5-site <code>2026-10-25</code> monotonic far-field law (<code>1.18% → 0.0742</code> up to <code>37.87% → 0.2190</code>).</p>
<p>There is no defensible guarantee that this repository will beat that claim, the older 0.3195 claim, or the 0.4413 claim without higher-precision subsurface/1-m 3DEP features and selector scoping of the dense prior.</p>
<a href="research/session-d634de37-review.md">Latest 9-focus-site audit, PhD 0.2778 analysis &amp; limitations (d634de37) →</a></div>
<div class="proof"><div class="kicker">Source-bound research queue</div><h3>Test physical deconvolution—with null controls.</h3>
<p>The conditional source-bound first choice is <strong>{escape(first_choice['id'])}</strong>: {escape(first_choice['title'])}. Five new 2026-10-26 untried hypotheses (<code>H88-LGOF</code> LiDAR-gap isotonic subsurface expert + hydraulic outflow back-tracking, <code>H88-SEMD</code> signed magnetite-destruction × clay-cap cross-gradient dipole, <code>H88-PHCT</code> multi-height phase migration, <code>H88-CFRS</code> conjugate Reidel &amp; graben-pair filter, and external 1-m 3DEP/InSAR <code>H88-3DEP-INSAR</code>) are ranked alongside the queue; none authorizes generation while the duplicate stop binds.</p>
<p><strong>Evaluated mechanisms are retired, never recycled:</strong> MMRX, MTAS, MFS, PGTD, and CON88 already have historical negative execution records.</p>
<a href="research/session-d634de37-hypotheses.md">Latest 5 ranked hypotheses (H88-LGOF..3DEP-INSAR) →</a> · <a href="research/session-c59db412-hypotheses.md">Prior 2026-10-26 dossier (c59db412)</a> · <a href="data/hypothesis_queue.json">Machine-readable queue</a></div></div></section>
<section class="decision-actions"><div class="wrap"><div class="kicker">Operational handoff</div><h2>Data placement is no longer the blocker.</h2><p>The pinned core feature raster and shared external inputs have been restored; the existing preparation command successfully loads the shared feature planes on CPU. The remaining blocker is not a missing download: it is the unsatisfiable literal uniqueness condition, followed by scientific and organizer-access gates.</p>
<div class="button-row"><a class="button button-primary" href="executive-summary.html">Open the submission guide →</a><a href="sources.html" class="button decision-outline">Sources &amp; verification limits</a></div>
<p class="fine">Maximize P(Win): preserve scarce slots for evidence-backed, distinct candidates. Own the Outcome: report an unmet requirement instead of presenting a research TIFF as submission-ready.</p></div></section>'''
        return hero + content + inventory(audit)
    if kind != "guide":
        raise ValueError(f"unknown page kind: {kind}")
    guide = '''<section class="decision-explainer"><div class="wrap narrow"><div class="kicker">Executive summary</div><h2>Do not submit any current file.</h2>
<p><strong>CURRENT DECISION 2026-10-26: NO NEW UNIQUE TIFF (0/9 FOCUS SITES CLEARED).</strong> The download above is an archived research artifact, not a newly selected competition candidate. Neither GEMSDOE88 nor any of the 9 focus repositories (GEMSDOE24..36) currently holds a protocol-cleared submission.</p>
<ol class="steps"><li><h3>Run the automated project checks</h3><p>Restore pinned inputs, reopen saved TIFF/ZIP bytes, validate finite [0,1], the exact sample grid and footprint, one full-resolution raster and no external sidecar dependency, and check the pre-placement registry gate. Internal overviews are allowed; orphan or nested download packages fail the inventory check. No human inspector is required to decide these local checks.</p></li>
<li><h3>Require scientific evidence for a genuinely new candidate</h3><p>Withhold whole fault segments with a buffer. Recompute catalogue-derived features from visible faults only; run every single-feature leakage canary; mask visible faults exactly. Use the shared pooled DTI evaluator, a paired confidence interval against the same-fold incumbent, then full surface/final-dot registry tests. Stop on a failed gate.</p></li>
<li><h3>Keep slot selection separate</h3><p>Even if every local gate passes, the separate selector must authorize a slot within the current account limit. Current quota, competition timing and data-use terms are not verified from this sandbox. No guessed weekly allowance is used.</p></li>
<li><h3>Only after clearance, upload exactly one approved artifact</h3><p>On the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submission page</a>, choose the approved single-band TIFF or its one-TIFF ZIP. Verify the filename and hash against the cleared run card. Never upload a file containing <code>DO-NOT-SUBMIT</code>.</p></li>
<li><h3>Use the cleared name/note and retain the receipt</h3><p>Paste the unique name and note of at most 140 characters from that run card, not from a historical artifact. Only a score linked to the actual submission-page receipt may be labeled ORGANIZER-CONFIRMED. This project has no such receipt for a new candidate.</p></li></ol>
<div class="callout warn"><h3>The range error is a file check, not a scientific score.</h3><p>“Predicted values must be in range [0, 1]” can be caused by negative values, infinities, exterior NaNs (as found in GEMSDOE30’s MSDB1 and nearslay rasters) or nodata sentinels. All 48 audited GEMSDOE88 research files pass strict full-grid [0, 1] numeric checks.</p></div>
<h3 class="reproduce-heading">Reproduce without manual inspection</h3>
<pre class="command-block"><code>bash scripts/download_competition_data.sh --validation
python scripts/audit_downloads.py --check
python -O scripts/audit_focus_sites_20261026.py
python scripts/audit_research_state.py
python scripts/render_decision.py --check
python -O scripts/check_site.py
python scripts/preflight_mtas88.py --gate-generation
# Expected final exit: 2 (DUPLICATE_STOP). Not a build failure to bypass.</code></pre>
<p><a href="research/session-d634de37-review.md">Latest 9-focus-site review and limitations (d634de37)</a> · <a href="data/focus_sites_20261026.json">9-site audit JSON</a> · <a href="data/literal_protocol_audit.json">Literal audit</a> · <a href="data/session_d634de37_run_card.json">Negative run card (d634de37)</a> · <a href="data/con88_clearance_withdrawal_20261025.json">CON88 withdrawal receipt</a></p>
</div></section>'''
    return hero + guide + inventory(audit)


def legacy_notice(kind: str) -> str:
    """Withdraw contradictory archived upload guides instead of hiding a warning.

    Historical JSON remains available; neither a stale YES card nor a broken
    relative download should survive on an independently reachable legacy URL.
    """
    if kind not in {"overview", "guide"}:
        raise ValueError(f"unknown legacy page kind: {kind}")
    title = "Archived MDC-88 research" if kind == "overview" else "Archived MDC-88 submission guide"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Historical MDC-88 research only. No file is cleared for submission.">
<title>GEMSDOE88 · {title} · DO NOT SUBMIT</title>
<link rel="stylesheet" href="../assets/site.css"><link rel="stylesheet" href="../assets/gate.css">
</head><body><a href="#main" class="sr-only">Skip to content</a>
<header class="header"><div class="wrap"><a class="brand" href="../index.html">GEMSDOE88</a>
<nav class="nav" aria-label="Main navigation"><a href="../index.html">Current decision</a>
<a href="../executive-summary.html">Submission guide</a><a href="../sources.html">Sources</a></nav></div></header>
<main id="main"><section><div class="wrap">
<div class="kicker">Historical page corrected · 2026-10-25</div><h1>{title}</h1>
<div class="callout warn"><h2>SUBMIT: NO — DO NOT SUBMIT</h2>
<p>The previous clearance on this legacy URL was revoked. A local format pass does not establish organizer acceptance, protocol uniqueness, scientific improvement, or permission to use a weekly slot.</p></div>
<p>The registered 17GEMSDOE probability raster covers every allowed cell, so every nonempty candidate fails the binding literal overlap rule. There is no dense-prior or creation-order exemption. Renaming a <code>DO-NOT-SUBMIT</code> file cannot clear it.</p>
<p><strong>No new TIFF is presented on this page.</strong> Existing MDC-88 files and the collar research variant remain research-only. Their saved bytes are included in the current automated audit; they are not selected submissions.</p>
<div class="button-row"><a class="button button-primary" href="../index.html">Current decision &amp; audited research download</a>
<a class="button" href="../executive-summary.html">Current executive submission guide</a></div>
<p><a href="../data/download_audit.json">All saved-byte TIFF/ZIP checks</a> · <a href="../research/session-b4dfa10c-review.md">Review and limitations</a> · <a href="status.json">Corrected historical status</a> · <a href="data/kdmc-run-card.json">Historical measurements, not upload authorization</a></p>
<p>No submission slot was used by this review. No ORGANIZER-CONFIRMED score or current account quota is asserted.</p>
</div></section></main></body></html>
'''


def render_research_queue(root: Path) -> str:
    queue = inspect_queue(root)
    rows = []
    for proposal in queue["proposals"]:
        rows.append(
            '<tr><th scope="row">' + str(proposal["rank"]) + ' · ' + escape(proposal["id"]) + '</th>'
            '<td>' + escape(proposal["title"]) + '</td>'
            '<td>' + escape(proposal["non_fault_mimic"]) + '</td>'
            '<td>' + escape(proposal["expected_potential"]) + ' / ' + escape(proposal["implementation_cost"]) + '</td></tr>'
        )
    return ('<section><div class="wrap"><div class="kicker">Source-bound conditional queue · no generation authorized</div>'
            '<h2>' + str(len(queue["proposals"])) + ' unrun contrasts—not another stale first choice.</h2>'
            '<p>Magnetic-marker restoration (MMRX), cross-scale admittance (MTAS), gradient-scaling breaks (MFS), harmonic tensor dimensionality (PGTD), '
            'and cross-fleet consensus ridge (CON88) already have historical negative execution records. They are not untested proposals. Their execution '
            'does not authorize bypassing the unchanged duplicate stop.</p>'
            '<div class="table-scroll"><table><thead><tr><th>Rank / lane</th><th>Proposed physical test</th>'
            '<th>Non-fault alternative</th><th>Potential / cost</th></tr></thead><tbody>' + ''.join(rows) +
            '</tbody></table></div><p>Priorities are qualitative, not predicted scores. These are source-reviewed, '
            'still-unimplemented variants in this checkout, not proof of worldwide novelty. All inputs are in the '
            'existing pinned owner-mirror tier; no new external data availability is assumed. Every proposal is '
            'held before feature construction by the same literal witness.</p>'
            '<p><a href="research/session-d634de37-hypotheses.md">Five 2026-10-26 untried hypotheses (H88-LGOF..3DEP-INSAR) →</a> · '
            '<a href="research/session-c59db412-hypotheses.md">Prior 2026-10-26 dossier (H88-PTGM..3DEP-SCARP) →</a> · '
            '<a href="research/session-0df81d99-hypotheses.md">Prior dossier (H88-HRLC..USMT-3D) →</a> · '
            '<a href="research/session-693b10af-hypotheses.md">Queue notes (SPR/AWA/CBC) →</a> · '
            '<a href="data/hypothesis_queue.json">Source-fingerprinted JSON queue</a></p></div></section>')


def replace_block(text: str, content: str, start: str = START, end: str = END) -> str:
    if text.count(start) != 1 or text.count(end) != 1 or text.index(end) < text.index(start):
        raise ValueError("missing or ambiguous canonical decision markers")
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    return before + start + "\n" + content + "\n" + end + after


def main(argv=None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        for name, kind in (("index.html", "overview"), ("executive-summary.html", "guide")):
            path = root / "docs" / name
            old = path.read_text()
            new = replace_block(old, render(root, kind))
            if args.check:
                if new != old:
                    raise ValueError(f"stale canonical decision: {name}; run scripts/render_decision.py")
            else:
                path.write_text(new, encoding="utf-8")
        research = root / "docs/research.html"
        old = research.read_text()
        expected = replace_block(old, render_research_queue(root), QUEUE_START, QUEUE_END)
        if args.check:
            if expected != old:
                raise ValueError("stale research queue: research.html; run scripts/render_decision.py")
        else:
            research.write_text(expected, encoding="utf-8")
        for name, kind in (("index.html", "overview"), ("executive-summary.html", "guide")):
            path = root / "docs/mdc88" / name
            expected = legacy_notice(kind)
            if args.check:
                if path.read_text() != expected:
                    raise ValueError(f"stale legacy correction: mdc88/{name}")
            else:
                path.write_text(expected, encoding="utf-8")
        print("PASS: canonical overview, submission guide and legacy corrections match machine evidence")
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"DECISION RENDER FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
