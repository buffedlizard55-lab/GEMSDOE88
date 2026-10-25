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

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- CANONICAL-DECISION:START -->"
END = "<!-- CANONICAL-DECISION:END -->"


def read_inputs(root: Path) -> tuple[dict, dict, dict, dict]:
    current = json.loads((root / "docs/data/current_release.json").read_text())
    stop = json.loads((root / "registry/mtas88_run_card.json").read_text())
    audit = json.loads((root / "docs/data/download_audit.json").read_text())
    historical = json.loads((root / "docs/data/mtas88_experiment_run_card.json").read_text())
    historical_registry = json.loads((root / "registry/mtas88_experiment_run_card.json").read_text())
    historical_evidence = json.loads((root / "evidence/mtas88_experiment_20261025.json").read_text())
    status = json.loads((root / "docs/status.json").read_text())
    if not (
        current["ok_to_submit"] is False and current["ok_to_download"] is True
        and status["ok_to_submit"] is False and status["raster_sha256"] == current["file_sha256"]
        and stop["decision"] == "DUPLICATE_STOP" and stop["new_rasters_generated"] == 0
        and stop["preplacement_registry_proof"]["universal_overlap_blocker"] is True
        and audit["ok_to_submit"] is False and audit["canonical_sha256"] == current["file_sha256"]
        and audit["protocol_eligible_count"] == 0
        and historical == historical_registry == historical_evidence
        and historical.get("lane") == "H88-MTAS"
        and historical.get("holdout", {}).get("evidence_class") == "HOLDOUT-DTI"
        and historical.get("holdout", {}).get("evaluator_version") == "gems57-pooled-hide-v2"
        and historical.get("ok_to_submit") is False
        and historical.get("organizer_confirmed_score") is None
    ):
        raise ValueError("canonical decision inputs disagree; never render a clearance")
    for key, digest_key in (("file", "file_sha256"), ("zip_file", "zip_sha256")):
        relative = Path(current[key])
        if relative.parent != Path("docs/downloads") or "DO-NOT-SUBMIT" not in relative.name:
            raise ValueError("canonical file must remain in research downloads with negative label")
        with (root / relative).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != current[digest_key]:
                raise ValueError("canonical downloadable bytes disagree with release card")
    return current, stop, audit, historical


def inventory(audit: dict) -> str:
    rows = []
    for row in audit["artifacts"]:
        name = escape(row["file"])
        label = name.removesuffix("-DO-NOT-SUBMIT.tif")
        download = (f'<a href="downloads/{name}" download aria-label="Research-only TIFF {label}">TIFF</a> · '
                    f'<a href="downloads/{escape(row.get("zip_file", ""))}" download>ZIP</a>'
                    if row["research_download_ok"] else "Quarantined — see audit")
        rows.append(f'<tr><th scope="row"><span class="mono">{label}</span></th>'
                    f'<td>{row.get("positive_pixels", 0):,}</td><td>{"PASS" if row["format_valid"] else "FAIL"}</td>'
                    f'<td>{download}</td><td><span class="tag bad">DO NOT SUBMIT</span></td></tr>')
    return (f'<section class="inventory-section"><div class="wrap"><details id="download-inventory" class="download-inventory">'
            f'<summary>All {audit["tiff_count"]} archived research TIFFs · automated file audit</summary>'
            '<p>These are existing artifacts, not new submissions from this session. Different bytes are not proof of protocol uniqueness. '
            'Every nonempty allowed candidate is blocked by the same literal witness. '
            '<a href="data/download_audit.json">Full hashes, format checks, ZIP checks and duplicate groups (JSON)</a>.</p>'
            '<div class="table-scroll"><table><thead><tr><th>Archived file</th><th>Positive pixels</th><th>Local format</th>'
            '<th>Research download</th><th>Submission</th></tr></thead><tbody>' + ''.join(rows) +
            '</tbody></table></div></details></div></section>')


def render(root: Path, kind: str) -> str:
    current, stop, audit, historical = read_inputs(root)
    tif = escape(Path(current["file"]).relative_to("docs").as_posix())
    zipped = escape(Path(current["zip_file"]).relative_to("docs").as_posix())
    name, note = escape(current["submission_name"]), escape(current["submission_note"])
    digest = escape(current["file_sha256"])
    checked = escape(audit["checked_at_utc"])
    count = audit["tiff_count"]
    title = "Research download.<br>Not cleared to submit." if kind == "overview" else "How submission works.<br>Why it is blocked today."
    hero = f'''<section class="decision-hero" id="mtas-review" aria-labelledby="decision-title">
<div class="wrap" id="autonomous-review">
<div class="decision-kicker">Current review · 2026-10-25 · NO FILE APPROVED</div>
<div class="decision-grid"><div>
<h1 id="decision-title">{title}</h1>
<p class="decision-lead"><strong>NO NEW TIFF: DUPLICATE — STOP.</strong> A freshly generated, protocol-unique competition TIFF could not be produced under the binding rule. No old prediction was copied or renamed as a new submission.</p>
<p>The pinned registry witness covers every allowed pixel: every nonempty dot set fails the literal overlap limit. These archived files are <strong>not unique under the binding all-registry rule</strong>.</p>
<div class="decision-pills"><span>DOWNLOAD FOR RESEARCH: YES</span><span class="blocked-pill">SUBMIT: NO — DO NOT SUBMIT</span></div>
<p class="micro">No competition slot used in this review. No organizer-confirmed score. Local validation cannot establish hidden-label performance or choose a weekly slot. <a href="data/repo_review_20261025.json">Current review card</a> · <a href="research/repo-review-dea470d9-20261025.md">Three-pass report</a>.</p>
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
<article class="gate-card"><span class="tag">LOCAL FORMAT PASS</span><h3>File correctness</h3><p>All {count} published TIFFs were reopened. The canonical TIFF has no NaN or infinity, is within [0, 1], and matches CRS, shape and transform. Its ZIP contains the same TIFF.</p></article>
<article class="gate-card"><span class="tag bad">UNIQUENESS FAIL</span><h3>Duplicate stop</h3><p>Registry measurement: the 17GEMSDOE witness covers all 5,106,385 allowed cells. The overlap lower bound is 1.00; the limit is 0.70. No sparse-only exemption.</p></article>
<article class="gate-card"><span class="tag dim">NOT RUN THIS SESSION</span><h3>Scientific performance</h3><p>No new holdout or leakage canary was run after the prerequisite failed. Historical HOLDOUT-DTI is not a new candidate result and is not an organizer score.</p></article>
<article class="gate-card"><span class="tag bad">NO SLOT AUTHORIZED</span><h3>Competition eligibility</h3><p>A format pass cannot clear a duplicate, prove a leaderboard improvement, establish current quota, or authorize a submission. Slot selection remains separate.</p></article>
</div></div></section>'''
    if kind == "overview":
        content = '''<section class="decision-explainer"><div class="wrap split">
<div><div class="kicker">H33 forensic answer</div><h2>Learn from the geometry.<br>Do not copy the submission.</h2>
<p><strong>0.2778 is a user-reported claim, not an ORGANIZER-CONFIRMED receipt.</strong> H33's 37,654 dots are a strict subset of H19-5, D2.8 and SOLO-D2.8; it removes 6,436 D2.8 dots, all within 2 pixels of the catalogue. This supports a de-redundancy hypothesis but does not establish score causality.</p>
<p>There is no defensible guarantee that this repository will beat that claim or the older 0.3195/0.4413 figures. A buffered, fold-matched improvement is a necessary project gate, not a leaderboard forecast.</p>
<a href="research/repo-review-dea470d9-20261025.md#h33">H33 evidence, metric and limitations →</a></div>
<div class="proof"><div class="kicker">Next scientific work</div><h3>Test displacement—not another edge map.</h3>
<p>Four exact method-level formulations remain untested, but their broad geological families and inputs overlap prior lanes. Global/fleet-wide novelty is not certified. The leading formulation asks whether a coherent magnetic marker becomes continuous after a repeatable cross-boundary displacement; intrusive contacts and depositional pinch-outs are explicit alternatives.</p>
<p>No candidate has been selected or run. The universal duplicate stop comes first; official source availability and data rights remain unverified.</p>
<a href="research/repo-review-dea470d9-20261025.md#hypotheses">Read the four conditional hypotheses →</a></div></div></section>
<section class="decision-actions"><div class="wrap"><div class="kicker">Operational handoff</div><h2>The full feature stack is absent.</h2><p>Only validation-tier inputs are currently available. <code>data/training_features.tif</code> is absent, and owner-mirror bytes are not authenticated organizer downloads. First resolve the literal-support/dot-set protocol contradiction explicitly without bypassing the current stop; then verify source provenance/rights and restore the full stack before any assigned method's shared canaries and buffered holdout.</p>
<div class="button-row"><a class="button button-primary" href="executive-summary.html">Open the submission guide →</a><a href="sources.html" class="button decision-outline">Sources &amp; verification limits</a></div>
<p class="fine">Maximize P(Win): preserve scarce slots for evidence-backed, distinct candidates. Own the Outcome: report an unmet requirement instead of presenting a research TIFF as submission-ready.</p></div></section>'''
        historical_holdout = historical["holdout"]
        mtas_section = f'''<section class="decision-explainer" id="historical-mtas-result"><div class="wrap narrow"><div class="kicker">Historical experiment · not this preflight</div><h2>H88-MTAS has a measured negative holdout.</h2>
<p><strong>HOLDOUT-DTI {historical_holdout["dti"]:.6f} [{historical_holdout["ci95"][0]:.6f}, {historical_holdout["ci95"][1]:.6f}]</strong> · evaluator <code>{escape(historical_holdout["evaluator_version"])}</code> · {historical_holdout["withheld_positive_pixels"]:,} withheld positives · {historical_holdout["n_folds"]} folds. This is a historical local result, not ORGANIZER-CONFIRMED. The later generation preflight stopped before a new experiment; it did not rerun or invalidate this result.</p>
<p><a href="data/mtas88_experiment_run_card.json">Historical MTAS experiment run card →</a> · <a href="data/repo_review_20261025.json">Current preflight/review card →</a></p></div></section>'''
        return hero + content + mtas_section + inventory(audit)
    if kind != "guide":
        raise ValueError(f"unknown page kind: {kind}")
    guide = '''<section class="decision-explainer"><div class="wrap narrow"><div class="kicker">Executive summary</div><h2>Do not submit any current file.</h2>
<p><strong>CURRENT DECISION 2026-10-25: NO NEW UNIQUE TIFF.</strong> The download above is an archived research artifact, not a newly selected competition candidate. There is no safe file to choose in the portal under the current project protocol.</p>
<ol class="steps"><li><h3>Run the automated project checks</h3><p>Restore pinned inputs, reopen saved TIFF/ZIP bytes, validate finite [0,1], the exact sample grid and footprint, and check the pre-placement registry gate. No human inspector is required to decide these local checks.</p></li>
<li><h3>Require scientific evidence for a genuinely new candidate</h3><p>Withhold whole fault segments with a buffer. Recompute catalogue-derived features from visible faults only; run every single-feature leakage canary; mask visible faults exactly. Use the shared pooled DTI evaluator, a paired confidence interval against the same-fold incumbent, then full surface/final-dot registry tests. Stop on a failed gate.</p></li>
<li><h3>Keep slot selection separate</h3><p>Even if every local gate passes, the separate selector must authorize a slot within the current account limit. Current quota, competition timing and data-use terms are not verified from this sandbox. No guessed weekly allowance is used.</p></li>
<li><h3>Only after clearance, upload exactly one approved artifact</h3><p>On the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submission page</a>, choose the approved single-band TIFF or its one-TIFF ZIP. Verify the filename and hash against the cleared run card. Never upload a file containing <code>DO-NOT-SUBMIT</code>.</p></li>
<li><h3>Use the cleared name/note and retain the receipt</h3><p>Paste the unique name and note of at most 140 characters from that run card, not from a historical artifact. Only a score linked to the actual submission-page receipt may be labeled ORGANIZER-CONFIRMED. This project has no such receipt for a new candidate.</p></li></ol>
<div class="callout warn"><h3>The range error is a file check, not a scientific score.</h3><p>“Predicted values must be in range [0, 1]” can be caused by negative values, infinities, NaNs or nodata sentinels. The audited research files pass strict local numeric checks. This does not assert that an unauthenticated portal has accepted them.</p></div>
<h3 class="reproduce-heading">Reproduce without manual inspection</h3>
<pre class="command-block"><code>bash scripts/download_competition_data.sh --validation
python scripts/audit_downloads.py --check
python scripts/render_decision.py --check
python scripts/check_site.py
python scripts/preflight_mtas88.py --gate-generation
# Expected final exit: 2 (DUPLICATE_STOP). Not a build failure to bypass.</code></pre>
<p><a href="research/repo-review-dea470d9-20261025.md">Current review and limitations</a> · <a href="data/repo_review_20261025.json">Current machine review card</a> · <a href="data/literal_protocol_audit.json">Literal audit</a> · <a href="data/mtas88_run_card.json">Preflight stop card</a> · <a href="data/mtas88_experiment_run_card.json">Historical MTAS experiment card</a></p>
</div></section>'''
    return hero + guide + inventory(audit)


def replace_block(text: str, content: str) -> str:
    if text.count(START) != 1 or text.count(END) != 1 or text.index(END) < text.index(START):
        raise ValueError("missing or ambiguous canonical decision markers")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    return before + START + "\n" + content + "\n" + END + after


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
        print("PASS: canonical overview and submission guide match machine evidence")
        return 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"DECISION RENDER FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
