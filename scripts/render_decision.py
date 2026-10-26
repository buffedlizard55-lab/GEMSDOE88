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
from scripts.audit_focus_sample_20261026 import check as check_sample_audit  # noqa: E402

START = "<!-- CANONICAL-DECISION:START -->"
END = "<!-- CANONICAL-DECISION:END -->"
QUEUE_START = "<!-- RESEARCH-QUEUE:START -->"
QUEUE_END = "<!-- RESEARCH-QUEUE:END -->"


def read_inputs(root: Path) -> tuple[dict, dict, dict, dict, dict]:
    current = json.loads((root / "docs/data/current_release.json").read_text())
    stop = json.loads((root / "registry/mtas88_run_card.json").read_text())
    audit = json.loads((root / "docs/data/download_audit.json").read_text())
    status = json.loads((root / "docs/status.json").read_text())
    focus = json.loads((root / "docs/data/focus_sites_20261026.json").read_text())
    sampled_bytes = (root / "docs/data/focus_sample_2b5a8383.json").read_bytes()
    if sampled_bytes != (root / "evidence/focus_sample_2b5a8383.json").read_bytes():
        raise ValueError("sampled audit evidence and public copy differ")
    sampled = json.loads(sampled_bytes)
    check_sample_audit(sampled)
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
    return current, stop, audit, focus, sampled


def focus_sites_panel(focus: dict, sampled: dict) -> str:
    rows = []
    later = {row["site"]: row for row in sampled["rows"]}
    stopped = sum(row["decision"] == "DUPLICATE_STOP" for row in sampled["rows"])
    conflict_sites = ", ".join(escape(row["site"]) for row in sampled["rows"] if row["sibling_readme_claims_ok_to_submit"])
    for item in focus["focus_sites"]:
        site = escape(item["site"])
        url = escape(item["pages_url"])
        champ_obj = item["highest_scoring_submission"]
        champ = escape(champ_obj["prompt_name"])
        # The historic tree paths were independently checked at each audited
        # immutable HEAD. This links research bytes, not a submission clearance.
        audited_head = escape(item["inspected_repo_head_sha"], quote=True)
        champ_name = Path(champ_obj["cache_filename"].split("__", 1)[-1]).name
        champ_source = escape(f'{item["repo_url"]}/blob/{item["inspected_repo_head_sha"]}/docs/downloads/{champ_name}', quote=True)
        score = escape(str(champ_obj["user_reported_value"]))
        sha_short = escape(champ_obj["sha256"][:12])
        dots = f'{int(champ_obj["positive_pixels"]):,}'
        reg = champ_obj["vs_gemsdoe88_registry"]
        ov_h19 = f'{float(reg["gems19_h19_5_3px_forward_overlap"]):.4f}'
        ov_17 = f'{float(reg["dense_17gemdoe_3px_forward_overlap"]):.4f}'
        lineage = champ_obj["lineage_role"]
        lineage = lineage.replace("(#1 user-reported across all 92 sites)", "(highest of nine listed user claims)")
        lineage = lineage.replace("(#2 user-reported)", "(user-reported)")
        lineage = lineage.replace("-0.0028 user-reported drag vs D1.5", "reported difference -0.0028; causality unproven")
        lineage = lineage.replace("-0.0028 user-reported drag vs 0.2778", "reported difference -0.0028; causality unproven")
        lineage = escape(lineage)
        row = later[item["site"]]
        sample_name = escape(Path(row["path"]).name)
        sample_url = escape(row["source_url"], quote=True)
        sample_label = escape(row["label"])
        local_format = "Local strict finite check: PASS" if row["strict_local_format_and_footprint_pass"] else (
            "Local strict finite check: FAIL; in-footprint range " + ("passed" if row["inside_footprint_finite_in_range"] else "failed/unknown"))
        overlap = row["positive_within_3px_witness_fraction"]
        overlap_text = f"{overlap:.4f}" if overlap is not None else "not measured"
        conflict = "<br><strong>Sibling says submit; local protocol does not approve.</strong>" if row["sibling_readme_claims_ok_to_submit"] else ""
        recent = (f'<a href="{sample_url}"><code>{sample_name}</code></a><br>{sample_label} · '
                  f'{local_format}<br>17GEMSDOE overlap: {overlap_text} · DO NOT SUBMIT{conflict}')
        rows.append(
            f'<tr><th scope="row"><a href="{url}">{site}</a><br>'
            f'<span class="focus-freshness-label" data-focus-freshness="{site}" data-audited-head="{audited_head}">Revision not checked</span></th>'
            f'<td style="overflow-wrap:anywhere"><a href="{champ_source}"><code>{champ}</code></a><br><strong>{score}</strong> <span class="micro">(user-reported; no receipt)</span></td>'
            f'<td><code>{sha_short}…</code><br>{dots} px</td>'
            f'<td><strong>UNIQUE: NO (DUPLICATE)</strong><br><code>{ov_h19}</code> / <code>{ov_17}</code></td>'
            f'<td>{lineage}</td>'
            f'<td>{recent}</td>'
            f'<td><span class="tag bad">DOWNLOAD: YES (RESEARCH)<br>SUBMIT: NO — DO NOT SUBMIT</span></td></tr>'
        )
    return (
        '<section class="focus-sites-section" id="focus-sites-executive-summary"><div class="wrap">'
        '<div class="section-heading"><div><div class="kicker">Pinned forensic audit · historical, not live scores</div>'
        '<h2>Executive summary: GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 &amp; 36</h2></div>'
        '<a href="data/focus_sites_20261026.json">Machine JSON ↗</a></div>'
        '<div class="focus-freshness" role="region" aria-label="Focus site revision freshness">'
        '<strong>Audit freshness</strong><p data-focus-feed-status role="status" aria-live="polite">'
        'Revision check unavailable until the GitHub snapshot loads. The table is historical; do not submit.</p>'
        '<p class="focus-freshness-explainer">Scheduled GitHub HEAD checks compare against the older winner audit; '
        'they do not re-audit rasters, verify scores, check quota or authorize a file. '
        '<a href="data/focus-freshness.json">View dated revision snapshot</a>.</p></div>'
        '<p><strong>Later, selective byte audit:</strong> one README-cited file per site was reopened at the GitHub revisions captured '
        f'2026-10-26 21:38 UTC; {stopped}/9 failed the dense-witness duplicate gate. The pinned READMEs for {conflict_sites} '
        'described their sampled files as submit-ready, but this repository does not approve them. '
        'This is a nine-file sample, not a complete fleet audit or a new score. '
        '<a href="data/focus_sample_2b5a8383.json">Sample audit and pinned source links →</a></p>'
        '<p>Every historical champion across all 9 focus sites (<code>0.2449</code>–<code>0.2778</code>, all unreceipted user-reported claims) '
        'has <code>0.9775–1.0000</code> 3-pixel forward overlap with <code>19GEMSDOE</code> <code>H19-5</code> and <code>1.0000</code> with '
        '<code>dense_17gemdoe.tif</code>: one nested <code>D1.5</code>/<code>D2.8</code>/<code>SOLO</code>/<code>H33-2-B2</code> ridge-pruning family (<strong>0/9 unique</strong>). '
        'None of the candidates assessed in the dated audit cleared its protocol gates—including <code>GEMSDOE27</code> <code>H31-1 DRCG-WL</code> '
        '(<code>IR-88-D634DE37-01</code>: historical unverified holdout figures <code>0.047302</code> buffered / <code>0.115636</code> unbuffered, evaluator and CI not established; <code>88.79% &gt; 70%</code> 3-px coverage of <code>H29-S</code>, '
        'and <code>100%</code> <code>dense_17gemdoe</code> overlap), <code>GEMSDOE33</code> <code>A33-R2-HMDT</code> '
        '(<code>IR-88-D634DE37-02</code>: <code>33,616 / 42,000</code> (<code>80.04%</code>) positive pixels outside the study footprint, <code>108</code> on catalogue faults, '
        '<code>nn_min_px = 1.0</code> scanlines, and <code>Holdout: NOT MEASURED</code>), and <code>GEMSDOE32</code> <code>R6-1-stepprofile</code> '
        '(<code>IR-88-C59DB412-02</code>, now self-demoted to <code>DO NOT SUBMIT</code> in commit <code>9e55d5d</code>). '
        '<a href="data/focus_sites_20261026.csv" download>Download 9-site CSV</a> · '
        '<a href="research/session-d634de37-review.md">Full PhD forensic review (d634de37) →</a> · '
        '<a href="research/session-c59db412-review.md">Prior review (c59db412)</a></p>'
        '<p><strong>No current leaderboard estimate:</strong> these are reported historical results, not organizer receipts or fresh comparable holdout scores. '
        'The listed files are for identification and research, not recommended submissions.</p>'
        '<div class="table-scroll"><table><thead><tr><th>Focus site &amp; revision</th><th>Historical file &amp; reported claim</th>'
        '<th>SHA-256 &amp; dots</th><th>Unique? (3-px overlap H19-5 / 17GEMSDOE)</th><th>Measured lineage</th>'
        '<th>One later sampled file · 21:38 UTC pin</th><th>OK to download / submit?</th></tr></thead><tbody>'
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
    current, stop, audit, focus, sampled = read_inputs(root)
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
<div class="decision-kicker">Review · 2026-10-26 · NO FILE APPROVED · 0/9 CLEARED IN HISTORICAL AUDIT</div>
<div class="decision-grid"><div>
<h1 id="decision-title">{title}</h1>
<p class="decision-lead"><strong>NO NEW TIFF: DUPLICATE — STOP.</strong> A freshly generated, protocol-unique competition TIFF could not be produced under the binding rule. The pinned nine-site audit found no qualifying candidate; it is not a current census. No old prediction was copied or renamed as a new submission.</p>
<p>The pinned registry witness covers every allowed pixel: every nonempty dot set fails the literal overlap limit. These archived files are <strong>not unique under the binding all-registry rule</strong>.</p>
<div class="decision-pills"><span>DOWNLOAD FOR RESEARCH: YES</span><span class="blocked-pill">SUBMIT: NO — DO NOT SUBMIT</span></div>
<p class="micro">No competition slot used in this session. No organizer-confirmed score. Local validation does not require human inspection; it cannot establish hidden-label performance or choose a weekly slot. <a href="data/session_2b5a8383_run_card.json">This review’s negative run card</a> · <a href="data/focus_sites_20261026.json">Historical 9-site audit JSON</a>.</p>
</div><aside class="decision-download" aria-label="Canonical archived research download">
<div class="decision-kicker">Existing research artifact · H88-TDKL · 2026-10-24</div>
<h2>Download the audited TIFF</h2>
<p>Single-band float32 GeoTIFF · locally finite [0, 1] · exact pinned mirror grid. <strong>Research only. Do not upload.</strong></p>
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
</div></div></section>''' + focus_sites_panel(focus, sampled)
    if kind == "overview":
        content = f'''<section class="decision-explainer"><div class="wrap split">
<div><div class="kicker">H33 &amp; 9-focus-site forensic answer</div><h2>Learn from the geometry.<br>Do not copy the submission.</h2>
<p><strong>0.2778 is a user-reported claim, not an ORGANIZER-CONFIRMED receipt.</strong> The audited H33-2-B2 support (<code>37,654</code> dots) is an exact subset of D2.8 (<code>44,090</code> dots): all <code>6,436</code> removed dots were within two pixels of the public catalogue. The intermediate SOLO version had already removed <code>3,891</code>; the remaining SOLO-to-H33 difference is <code>2,545</code>. An independent disk-dilation audit confirms the distinction. The corresponding reported values are <code>0.2778</code> and <code>0.2600</code>. Under the official metric (<code>α = 0.2</code>, <code>β = 0.8</code>, 300 m triangular kernel), thinning may reduce false-positive weight while retaining coverage. This is a hypothesis, not proof of the cause: hidden organizer labels and weighted components were not observed. Distance from the known catalogue is not proof of a fault discovery.</p>
<p>No experiment here establishes that a new submission will beat the user-reported H33 value or either conflicting leaderboard value. Higher-resolution data may help, but are not proven necessary or sufficient.</p>
<a href="research/session-2b5a8383-review.md">Nine-site sample, H33 analysis and limitations →</a></div>
<div class="proof"><div class="kicker">Source-bound research queue</div><h3>Test physical deconvolution—with null controls.</h3>
<p>The conditional source-bound first choice is <strong>{escape(first_choice['id'])}</strong>: {escape(first_choice['title'])}. The pinned queue contains three proposed contrasts, named confounders and falsification tests. None has been fitted in this session or authorizes generation while the duplicate stop binds.</p>
<p><strong>Research caution:</strong> the separate historical five-hypothesis dossier contains unsupported numerical projections and physical assertions; its estimates are not HOLDOUT-DTI results. The older document is retained for audit, not as evidence of performance or geological discovery.</p>
<p><strong>Evaluated mechanisms are retired, never recycled:</strong> MMRX, MTAS, MFS, PGTD, and CON88 already have historical negative execution records.</p>
<a href="data/hypothesis_queue.json">Source-bound ranked queue →</a> · <a href="research/session-d634de37-hypotheses.md">Historical five-hypothesis dossier and correction</a></div></div></section>
<section class="decision-actions"><div class="wrap"><div class="kicker">Operational handoff</div><h2>Data and protocol are separate gates.</h2><p>Hash-pinned owner mirrors of the core feature raster and shared external inputs can be restored with the project script. They are not authenticated organizer downloads. Preparation, modeling and placement remain paused behind the literal uniqueness stop; scientific validation and organizer access are separate requirements.</p>
<div class="button-row"><a class="button button-primary" href="executive-summary.html">Open the submission guide →</a><a href="sources.html" class="button decision-outline">Sources &amp; verification limits</a></div>
<p class="fine">Maximize P(Win): preserve scarce slots for evidence-backed, distinct candidates. Own the Outcome: report an unmet requirement instead of presenting a research TIFF as submission-ready.</p></div></section>'''
        return hero + content + inventory(audit)
    if kind != "guide":
        raise ValueError(f"unknown page kind: {kind}")
    guide = f'''<section class="decision-explainer"><div class="wrap narrow"><div class="kicker">Executive summary</div><h2>Do not submit any current file.</h2>
<p><strong>NO NEW UNIQUE TIFF; NO FILE APPROVED.</strong> The download above is an archived research artifact, not a newly selected competition candidate. The nine-site table is a pinned historical audit, not a current census. Under the binding witness rule, no nonempty in-domain candidate can pass the present overlap gate.</p>
<ol class="steps"><li><h3>Run the automated project checks</h3><p>Restore pinned inputs, reopen saved TIFF/ZIP bytes, validate finite [0,1], the exact sample grid and footprint, one full-resolution raster and no external sidecar dependency, and check the pre-placement registry gate. Internal overviews are allowed; orphan or nested download packages fail the inventory check. No human inspector is required to decide these local checks.</p></li>
<li><h3>Require scientific evidence for a genuinely new candidate</h3><p>Withhold whole fault segments with a buffer. Recompute catalogue-derived features from visible faults only; run every single-feature leakage canary; mask visible faults exactly. Use the shared pooled DTI evaluator, a paired confidence interval against the same-fold incumbent, then full surface/final-dot registry tests. Stop on a failed gate.</p></li>
<li><h3>Keep slot selection separate</h3><p>Even if every local gate passes, the separate selector must authorize a slot within the current account limit. Current quota, competition timing and data-use terms are not verified from this sandbox. No guessed weekly allowance is used.</p></li>
<li><h3>Only after clearance, upload exactly one approved artifact</h3><p>On the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submission page</a>, choose the approved single-band TIFF and confirm the current portal instructions. Verify the filename and hash against the cleared run card. Never upload a file containing <code>DO-NOT-SUBMIT</code>.</p></li>
<li><h3>Use the cleared name/note and retain the receipt</h3><p>Paste the unique name and note of at most 140 characters from that run card, not from a historical artifact. Only a score linked to the actual submission-page receipt may be labeled ORGANIZER-CONFIRMED. This project has no such receipt for a new candidate.</p></li></ol>
<div class="callout warn"><h3>The range error is a file check, not a scientific score.</h3><p>The cause of the reported portal error “Predicted values must be in range [0, 1]” is unverified. Check the saved float32 values, nonfinite values and nodata conventions. All {count} archived research files pass our stricter full-grid finite [0, 1] check, but that is not proof of portal acceptance. The organizer's published format describes null/NaN outside the footprint; our local zero-filled exterior differs. The current authenticated template and portal behavior remain unverified.</p></div>
<h3 class="reproduce-heading">Reproduce without manual inspection</h3>
<pre class="command-block"><code>bash scripts/download_competition_data.sh --validation
python scripts/audit_downloads.py --check
python -O scripts/audit_focus_sites_20261026.py
python -O scripts/audit_focus_sample_20261026.py --check
python scripts/focus_freshness.py --check
python scripts/audit_h33_collar.py
python scripts/audit_research_state.py
python scripts/render_decision.py --check
python -O scripts/check_site.py
python scripts/preflight_mtas88.py --gate-generation
# Expected final exit: 2 (DUPLICATE_STOP). Not a build failure to bypass.</code></pre>
<p><a href="research/session-2b5a8383-review.md">Current review and limitations</a> · <a href="data/focus_sample_2b5a8383.json">Nine-file sample audit</a> · <a href="data/focus_sites_20261026.json">Historical 9-site audit JSON</a> · <a href="data/literal_protocol_audit.json">Literal audit</a> · <a href="data/session_2b5a8383_run_card.json">Negative run card</a> · <a href="data/con88_clearance_withdrawal_20261025.json">CON88 withdrawal receipt</a></p>
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
            '<p>The separate five-hypothesis dossier contains unsupported projections and physical assertions; read its correction before using it as context. '
            '<a href="research/session-d634de37-hypotheses.md">Historical five-hypothesis dossier (corrected) →</a> · '
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
