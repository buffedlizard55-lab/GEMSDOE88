#!/usr/bin/env python3
"""Render the submit-status parts of the site from the single gate report.

Reads ``docs/data/submission_gate.json`` (written by scripts/submission_gate.py) and the
registered experiment receipts, then rewrites

* the GATE-BANNER block at the top of ``docs/index.html``
* ``docs/executive-summary.html`` (complete page)

so the site can never disagree with the gate: ``tests/test_site_matches_gate.py`` re-renders
and compares byte-for-byte.  If the verdict is not OK_TO_SUBMIT the pages show DO NOT SUBMIT
and omit the upload steps.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
START, END = "<!-- GATE-BANNER:START -->", "<!-- GATE-BANNER:END -->"
E = html.escape


def _load(rel: str):
    return json.loads((ROOT / rel).read_text())


def _fmt(x, n=4):
    return f"{x:.{n}f}"


def _inputs():
    gate = _load("docs/data/submission_gate.json")
    card = _load("registry/provcrest_run_card.json")
    audit = _load("registry/provcrest_nullcontrol_audit.json")
    spacing = _load("registry/provcrest_spacing_experiment.json")
    count = _load("registry/provcrest_count_experiment.json")
    lb = _load("docs/data/leaderboard.json")
    lin = _load("evidence/lineage_live_vs_geometry.json")
    return gate, card, audit, spacing, count, lb, lin


def banner(gate) -> str:
    ok = gate["verdict"] == "OK_TO_SUBMIT"
    c = gate["candidate"]
    form = gate["submit_form"]
    kb = (ROOT / c["file"]).stat().st_size / 1024
    zkb = (ROOT / c["zip_file"]).stat().st_size / 1024
    n_pass = sum(1 for r in gate["checks"] if r["pass"])
    bg, accent = ("#0c2436", "#76ddca") if ok else ("#4a0f0f", "#ffb4b4")
    head = ("✅ OK TO DOWNLOAD AND SUBMIT — ONE FILE" if ok else
            "⛔ DO NOT SUBMIT — the automated gate failed")
    parts = [
        START,
        f'<section style="background:{bg};color:#fff" aria-labelledby="gate-title" data-gate-verdict="{E(gate["verdict"])}"><div class="wrap">',
        f'<div class="kicker" style="color:{accent}">Automated gate · {n_pass}/{len(gate["checks"])} checks pass · no human inspection needed · 0 weekly slots spent · ORGANIZER-CONFIRMED score: none</div>',
        f'<h2 id="gate-title" style="color:#fff">{head}</h2>',
    ]
    if ok:
        parts += [
            f'<p style="font-size:1.1rem"><a href="downloads/{E(Path(c["file"]).name)}" download class="button button-primary">⬇ DOWNLOAD THE FILE TO SUBMIT ({kb:.0f} KB .tif)</a> '
            f'<a href="downloads/{E(Path(c["zip_file"]).name)}" download class="button button-alert">⬇ or the single-TIFF .zip ({zkb:.0f} KB)</a> '
            f'<a href="executive-summary.html" class="button button-ghost">Step-by-step guide →</a></p>',
            '<ol style="margin:.4rem 0 .8rem 1.2rem">'
            f'<li>Download the <code>.tif</code> above.</li>'
            f'<li>Open the <a href="{E(form["url"])}" style="color:{accent}">DrivenData “New submission” page</a> (login required) → <em>File to submit</em> → choose that file.</li>'
            f'<li>Paste the note below into <em>Note (optional)</em> and submit once.</li></ol>',
            f'<p><strong>File (this is its unique name):</strong> <code>{E(c["file_name"])}</code><br>'
            f'<strong>Note ({c["note_chars"]}/140 chars):</strong> <code>{E(c["note"])}</code> <button type="button" data-copy="{E(c["note"], quote=True)}">Copy</button><br>'
            f'<strong>Tracking label (not a form field):</strong> <code>{E(c["submission_name"])}</code><br>'
            f'<strong>SHA-256:</strong> <code>{E(c["sha256"])}</code></p>',
            '<p style="opacity:.92">What “OK” means: valid single-band float32 GeoTIFF (EPSG:32611, 3730×3292, same transform as the sample submission), '
            f'every value in {{0,1}} ⊂ [0,1], 0 NaN/Inf, unique against all {len(gate["uniqueness_rows"])} restored registry/own rasters, and it beats two no-information control rasters on the hide-and-recover holdout. '
            '<strong>It is not a promise of a leaderboard score</strong> — see <a href="executive-summary.html#limits" style="color:' + accent + '">limits</a>.</p>',
        ]
    else:
        parts += ['<ul>' + "".join(f"<li>{E(f)}</li>" for f in gate["failures"]) + "</ul>",
                  "<p>Do not upload any file from this site until <code>python scripts/submission_gate.py --require-submit</code> exits 0.</p>"]
    parts += ["</div></section>", END]
    return "\n".join(parts)


def strip_text(gate) -> str:
    n = len(gate["checks"])
    if gate["verdict"] == "OK_TO_SUBMIT":
        return (f"✅ OK TO DOWNLOAD AND SUBMIT · {gate['candidate']['file_name']} · all {n} automated gate "
                "checks pass · ORGANIZER-CONFIRMED score: none yet")
    return "⛔ DO NOT SUBMIT · automated gate failed: " + " | ".join(gate["failures"][:2])


def _set_strip(text: str, gate) -> str:
    return re.sub(r'(<span data-card-status>)(.*?)(</span>)',
                  lambda m: m.group(1) + E(strip_text(gate)) + m.group(3), text, count=1, flags=re.S)


def render_strips() -> None:
    """Static fallback for the global status strip on the secondary pages (site.js sets the same text)."""
    gate = _load("docs/data/submission_gate.json")
    for name in ("research.html", "sources.html"):
        p = DOCS / name
        p.write_text(_set_strip(p.read_text(), gate))


def render_index() -> None:
    gate = _load("docs/data/submission_gate.json")
    p = DOCS / "index.html"
    s = p.read_text()
    a, b = s.index(START), s.index(END) + len(END)
    p.write_text(_set_strip(s[:a] + banner(gate) + s[b:], gate))


def render_exec() -> None:
    gate, card, audit, spacing, count, lb, lin = _inputs()
    ok = gate["verdict"] == "OK_TO_SUBMIT"
    c = gate["candidate"]
    form = gate["submit_form"]
    h = card["holdout"]
    allv, farv = audit["views"]["ALL"], audit["views"]["FAR"]
    sc = lambda v, k: v["scores"][k]
    pd = lambda v, k: v["paired_differences_vs_provcrest_rank"][k]
    head_old = (DOCS / "executive-summary.html").read_text()
    head = head_old[: head_old.index('<main id="main">')]
    head = re.sub(r'<meta name="description" content="[^"]*">',
                  '<meta name="description" content="How to submit the GEMSDOE88 GeoTIFF to the DOE GEMS competition: one file, one note, automated pass/fail gate.">', head, count=1)
    chk_rows = "".join(
        f'<tr><td><code>{E(r["id"])}</code></td><td>{"✅" if r["pass"] else "❌"}</td><td>{E(r["description"])}</td></tr>'
        for r in gate["checks"])
    lin_rows = "".join(
        f'<tr><td>{E(r["label"])}</td><td>{"" if r["claimed_live_score"] is None else _fmt(r["claimed_live_score"])}</td>'
        f'<td>{r["n_dots"]:,}</td><td>{r["median_d_cat_px"]}</td><td>{r["frac_d_cat_gt_25px"]:.3f}</td>'
        f'<td>{r["median_nn_spacing_px"]}</td></tr>' for r in lin["rows"])
    cnt = count["scores"]
    spa = spacing["scores"]
    rho = lin["spearman_median_dcat_vs_claimed_score"]
    body = f"""<main id="main">
{banner(gate)}

<section id="steps"><div class="wrap"><div class="kicker">Exactly how to make a submission</div><h2>Five steps · the DrivenData “New submission” form</h2>
<ol class="steps narrow">
<li><h3>Check the verdict above</h3><p>It must read <strong>OK TO DOWNLOAD AND SUBMIT</strong>. To re-prove it yourself: <code>python scripts/restore_inputs.py --validation &amp;&amp; python scripts/submission_gate.py --require-submit</code> (exit code 0 = pass, 2 = do not upload). The page is re-rendered from that report, so they cannot disagree.</p></li>
<li><h3>Download the file</h3><p><a href="downloads/{E(Path(c['file']).name)}" download>{E(c['file_name'])}</a> — or its single-member <a href="downloads/{E(Path(c['zip_file']).name)}" download>.zip</a> (the form accepts “a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF”). SHA-256 <code>{E(c['sha256'])}</code>.</p></li>
<li><h3>Open the form</h3><p><a href="{E(form['url'])}">{E(form['url'])}</a> (DrivenData login required; this repo never logs in or uploads for you). Click <em>File to submit</em> and choose the file.</p></li>
<li><h3>Name + note</h3><p>The form has <strong>no separate name field</strong> — only <em>File to submit</em> and <em>Note (optional)</em>. The unique name is the file name <code>{E(c['file_name'])}</code>; tracking label <code>{E(c['submission_name'])}</code>. Paste this note ({c['note_chars']}/140 characters): <code>{E(c['note'])}</code></p></li>
<li><h3>Submit once, then record the receipt</h3><p>Copy the score the portal shows into <code>ledger/submissions.csv</code> labelled <code>ORGANIZER-CONFIRMED</code> (never overwrite a HOLDOUT-DTI number with it). Weekly feedback is capped (up to 3/week; one final submission counts for the prizes) per <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR Official Rules §3.2–§3.5</a> — which weekly slot to spend is your decision; this repo has spent none.</p></li>
</ol>
<div class="notice"><strong>If the portal says “Predicted values must be in range [0, 1]”</strong><p>An earlier submission was rejected with that message; the most likely cause is NaN/nodata cells (the portal’s own cause is not visible to this repo). The gate now fails closed on any NaN, Inf or value outside [0,1] (checks <code>FMT-06</code>/<code>FMT-07</code>) and on a changed grid (<code>FMT-05</code>). This file has {gate['n_dots']:,} cells equal to 1.0 and all others exactly 0.0, nodata unset. If the portal still rejects it, do not edit the file; report the exact message so the gate can be extended.</p></div>
</div></section>

<section style="background:#e9f2f1"><div class="wrap"><div class="kicker">Why this file and not a copy</div><h2>What the evidence says (every number labelled)</h2>
<p><strong>HOLDOUT-DTI</strong> = pooled Distance-weighted Tversky index (α 0.2, β 0.8, 300 m triangular kernel) on a buffered hide-and-recover split: whole fault components withheld, catalogue features derived from visible faults only, visible faults masked pixel-exactly (<code>{E(h['evaluator_version'])}</code>, seeds 20+30). It is a local instrument, <strong>not</strong> a leaderboard score.</p>
<table class="table"><thead><tr><th>Arm (identical folds)</th><th>ALL: {allv['withheld_positive_pixels']:,} withheld</th><th>FAR (&gt;10 px from visible faults): {farv['withheld_positive_pixels']:,} withheld</th></tr></thead><tbody>
<tr><td><strong>PROVCREST (shipped)</strong></td><td><strong>{_fmt(sc(allv,'provcrest_rank')['dti'])}</strong> [{_fmt(sc(allv,'provcrest_rank')['ci95'][0])}, {_fmt(sc(allv,'provcrest_rank')['ci95'][1])}]</td><td><strong>{_fmt(sc(farv,'provcrest_rank')['dti'])}</strong> [{_fmt(sc(farv,'provcrest_rank')['ci95'][0])}, {_fmt(sc(farv,'provcrest_rank')['ci95'][1])}]</td></tr>
<tr><td>Null: random order, same spacing/collar/N, no crest information</td><td>{_fmt(sc(allv,'null_random')['dti'])} [{_fmt(sc(allv,'null_random')['ci95'][0])}, {_fmt(sc(allv,'null_random')['ci95'][1])}]</td><td>{_fmt(sc(farv,'null_random')['dti'])} [{_fmt(sc(farv,'null_random')['ci95'][0])}, {_fmt(sc(farv,'null_random')['ci95'][1])}]</td></tr>
<tr><td>Null: hexagonal lattice, ~same N, no crest information</td><td>{_fmt(sc(allv,'null_lattice')['dti'])} [{_fmt(sc(allv,'null_lattice')['ci95'][0])}, {_fmt(sc(allv,'null_lattice')['ci95'][1])}]</td><td>{_fmt(sc(farv,'null_lattice')['dti'])} [{_fmt(sc(farv,'null_lattice')['ci95'][0])}, {_fmt(sc(farv,'null_lattice')['ci95'][1])}]</td></tr>
<tr><td>Paired Δ vs random null (95% CI)</td><td>+{_fmt(pd(allv,'null_random')['delta'])} [{_fmt(pd(allv,'null_random')['ci95'][0])}, {_fmt(pd(allv,'null_random')['ci95'][1])}]</td><td>+{_fmt(pd(farv,'null_random')['delta'])} [{_fmt(pd(farv,'null_random')['ci95'][0])}, {_fmt(pd(farv,'null_random')['ci95'][1])}]</td></tr>
<tr><td>Paired Δ vs lattice null (95% CI)</td><td>+{_fmt(pd(allv,'null_lattice')['delta'])} [{_fmt(pd(allv,'null_lattice')['ci95'][0])}, {_fmt(pd(allv,'null_lattice')['ci95'][1])}]</td><td>+{_fmt(pd(farv,'null_lattice')['delta'])} [{_fmt(pd(farv,'null_lattice')['ci95'][0])}, {_fmt(pd(farv,'null_lattice')['ci95'][1])}]</td></tr>
</tbody></table>
<p><strong>Irregularity found and fixed (IR-88-59):</strong> the first promotion compared PROVCREST with the shipped R0 raster (HOLDOUT-DTI {_fmt(h['arms']['r0_control']['dti'])}). R0 was built with the full catalogue, so it scores ≈0 on a hide-and-recover split <em>by construction</em>; beating it proved nothing. The null controls above can fail, and the gate now requires beating them.</p>
<p><strong>Uniqueness:</strong> compared with {len(gate['uniqueness_rows'])} rasters ({gate['uniqueness_summary']['like_for_like_reading']['dot_field_rasters']} dot fields + {gate['uniqueness_summary']['like_for_like_reading']['continuous_surface_rasters']} continuous prior): worst 3-px forward overlap {_fmt(gate['uniqueness_summary']['like_for_like_reading']['worst_forward_overlap_dot_fields'])} (limit 0.70), worst |Spearman| {_fmt(max(abs(r['spearman_full_footprint']) for r in gate['uniqueness_rows'] if r.get('spearman_full_footprint') is not None))} (limit 0.90). The literal “any raster” reading is reported too: the continuous <code>17GEMSDOE</code> prior covers the whole footprint, so it overlaps <em>every</em> non-empty raster at 1.0 — it carries no duplicate information, and is listed rather than silently exempted (<code>UNQ-04</code>).</p>
<p><strong>Reproducibility:</strong> rebuilding the dot mask from the restored, SHA-pinned inputs reproduces the shipped TIFF bit-for-bit (<code>SCI-03</code>).</p>
</div></section>

<section id="limits"><div class="wrap"><div class="kicker">Limits — read before spending a slot</div><h2>What this does <em>not</em> prove</h2>
<ul>
<li><strong>No organizer score exists.</strong> A passing gate means the file is valid and not a copy; it does not predict the portal score.</li>
<li><strong>Leaderboard reality (single read of the public page, {E(lb['checked_utc'][:10])}):</strong> #1 = {lb['top_public_dti']:.4f}; #50 = {lb['rank50_public_dti']:.4f}. The CLAIMED best sibling score 0.2778 would not reach the top 50. The brief also quotes 0.3195 and 0.4413 as “highest” — they cannot both be; the page shows 0.4413. <a href="{E(lb['source_url'])}">Open the live leaderboard ↗</a></li>
<li><strong>The local holdout cannot rank the live winners.</strong> R0 (CLAIM 0.2778) scores 0.004 on it. PROVCREST’s edge over no-information nulls shows its crest field carries signal on withheld faults; it does not show it beats 0.2778.</li>
<li><strong>Protocol interpretation (IR-88-59).</strong> A concurrent review (PR #58) withdrew this file because the continuous 17GEMSDOE prior overlaps every non-empty raster at 1.0 under the literal “any raster” reading. The gate reports that reading (<code>UNQ-04</code>) instead of letting it veto every candidate, applies the 0.70 overlap rule to dot fields and the 0.90 rank rule to all rasters. If the rule owner insists on the literal reading, no file is submittable (<code>scripts/validate_current.py --require-submit</code> exits 2).</li>
<li><strong>Geometry extrapolation risk.</strong> Across the {lin['n_scored']} rasters with CLAIMED live scores, median dot distance from the catalogue correlates with the claimed score (Spearman {rho['rho']}, descriptive, lineage members are not independent). PROVCREST’s median distance (22.8 px) lies beyond the observed range (max 19.7 px).</li>
<li><strong>Dot count.</strong> On the holdout the score rises with N (below), but the live lineage improved while <em>thinning</em>; the holdout and live regimes disagree, so N = 37,654 was kept.</li>
</ul>
<table class="table"><thead><tr><th>Experiment (HOLDOUT-DTI, {allv['withheld_positive_pixels']:,} withheld)</th><th>Result</th></tr></thead><tbody>
<tr><td>Exp 2 · spacing 3.0 / <strong>3.5 (shipped)</strong> / 4.5 px</td><td>{_fmt(spa['S3.0']['dti'])} / <strong>{_fmt(spa['S3.5']['dti'])}</strong> / {_fmt(spa['S4.5']['dti'])} — 3.5 is the local optimum (negative result: no change)</td></tr>
<tr><td>Exp 3 · N = 20k / 28k / <strong>37,654</strong> / 50k / 65k</td><td>{_fmt(cnt['N20000']['dti'])} / {_fmt(cnt['N28000']['dti'])} / <strong>{_fmt(cnt['N37654']['dti'])}</strong> / {_fmt(cnt['N50000']['dti'])} / {_fmt(cnt['N65000']['dti'])} — monotone in this low-score regime, as the DTI marginal rule (a dot helps iff its kernel credit &gt; 0.2·DTI) predicts</td></tr>
</tbody></table></div></div></section>

<section style="background:#e9f2f1"><div class="wrap"><div class="kicker">Why the 0.2778 lineage scored high (CLAIMED scores, descriptive)</div><h2>Geometry of the restored rasters vs their claimed live score</h2>
<table class="table"><thead><tr><th>Raster</th><th>Claimed live score</th><th>Dots</th><th>Median px to catalogue</th><th>Share &gt;25 px</th><th>Median nearest-dot px</th></tr></thead><tbody>{lin_rows}</tbody></table>
<p class="fine">Source: <code>scripts/analyze_lineage.py</code> → <code>evidence/lineage_live_vs_geometry.json</code>. Scores are user-reported CLAIMs (no receipts). Reading: the winners combine (1) dots ≥ 2.2–3 px apart, so 300 m kernels stop overlapping (the 0.19 → 0.26 climb as 121k → 44k dots), and (2) dots far from the mapped catalogue (the 0.26 → 0.278 climb as the ≤3 px share fell 19.5% → 5.8%). The three files that hug the catalogue (median 4–8 px) scored 0.004–0.111.</p>
</div></section>

<section><div class="wrap"><details><summary><strong>All {len(gate['checks'])} automated checks</strong></summary>
<table class="table"><thead><tr><th>ID</th><th></th><th>Check</th></tr></thead><tbody>{chk_rows}</tbody></table>
<p><a href="data/submission_gate.json">Machine-readable gate report →</a> · <a href="data/provcrest_run_card.json">Run card →</a></p></details>
<h3>Archived research files</h3><p>Files named <code>…DO-NOT-SUBMIT…</code> in <code>docs/downloads/</code> are research artifacts (earlier ADHR/MGC/UGFV candidates and a GHMD swap): DO NOT SUBMIT them. <a href="index.html">Back to overview →</a></p>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format">Official GeoTIFF format rules ↗</a> · <a href="sources.html">Data provenance &amp; licensing ↗</a></p></div></section></main>
<footer class="footer"><div class="wrap"><p>GEMSDOE88 · This page is generated from <code>docs/data/submission_gate.json</code> by <code>scripts/render_site.py</code>; verdict: <strong>{E(gate['verdict'])}</strong>.</p><a href="index.html">Back to overview →</a></div></footer></body></html>
"""
    (DOCS / "executive-summary.html").write_text(_set_strip(head, gate) + body)


def render_root() -> None:
    gate = _load("docs/data/submission_gate.json")
    c = gate["candidate"]
    ok = gate["verdict"] == "OK_TO_SUBMIT"
    lead = ("<strong>OK TO DOWNLOAD AND SUBMIT: YES.</strong> One file passes every automated gate "
            f"({sum(r['pass'] for r in gate['checks'])}/{len(gate['checks'])} checks, no human inspection): "
            f"<code>{E(c['file_name'])}</code> (SHA-256 <code>{E(c['sha256'][:16])}…</code>). "
            "It is valid, unique and unscored — ORGANIZER-CONFIRMED score: none; 0 weekly slots spent. "
            "Archived research files named DO-NOT-SUBMIT must not be uploaded."
            if ok else "<strong>DO NOT SUBMIT.</strong> The automated gate failed: " + E(" | ".join(gate["failures"][:2])))
    (ROOT / "index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="refresh" content="0; url=docs/index.html"><title>GEMSDOE88 · Automated Fault-Discovery Desk</title></head>'
        f'<body><main data-gate-verdict="{E(gate["verdict"])}"><h1>GEMSDOE88 — Automated Gate Decision</h1><p>{lead}</p>'
        '<p><a href="docs/index.html">Open the research desk &amp; download the submission &rarr;</a> · '
        '<a href="docs/executive-summary.html">Executive summary &amp; submission guide &rarr;</a></p></main></body></html>\n')


README_START, README_END = "<!-- GATE-BANNER:START -->", "<!-- GATE-BANNER:END -->"


def readme_banner(gate) -> str:
    ok = gate["verdict"] == "OK_TO_SUBMIT"
    c, f = gate["candidate"], gate["submit_form"]
    n_pass = sum(1 for r in gate["checks"] if r["pass"])
    uq = gate["uniqueness_summary"]["like_for_like_reading"]
    head = ("✅ OK TO DOWNLOAD AND SUBMIT — ONE FILE (automated gate passed)" if ok
            else "⛔ DO NOT SUBMIT — the automated gate failed")
    rows = [
        f"> ## {head}",
        f"> **File:** [`{c['file']}`]({c['file']}) · zip with the same TIFF: [`{c['zip_file']}`]({c['zip_file']})",
        f"> **SHA-256:** `{c['sha256']}`",
        f"> **Submission name:** `{c['submission_name']}` · **Note ({c['note_chars']}/140):** `{c['note']}`",
        f"> **Gate:** `python scripts/submission_gate.py --require-submit` → {n_pass}/{len(gate['checks'])} checks pass "
        f"(values in [0,1], no NaN, CRS/shape/transform = sample, 0 dots on the catalogue, worst dot-field 3-px overlap "
        f"{uq['worst_forward_overlap_dot_fields']:.4f} ≤ 0.70, max |ρ| ≤ 0.90, null-control paired CI > 0, canary ≤ 0.90). "
        "The continuous 17GEMSDOE prior overlaps everything at 1.0 and is classified, not hidden (IR-88-58).",
        "> **Status of the number:** HOLDOUT-DTI only; ORGANIZER-CONFIRMED score: **none**; 0 weekly slots spent by any agent. "
        "Every other file in `docs/downloads/` marked `DO-NOT-SUBMIT` is archived research — **DO NOT SUBMIT** them.",
        "> **Pages:** [Executive summary](docs/executive-summary.html) · [Site](docs/index.html) · "
        "[Why 0.2778 / hypotheses](research/session-20261024-audit-why-0.2778.md) · [IR-88-59](IRREGULARITIES.md)",
    ]
    return README_START + "\n" + "\n".join(rows) + "\n" + README_END


def render_readme() -> None:
    gate = _load("docs/data/submission_gate.json")
    p = ROOT / "README.md"
    s = p.read_text()
    a, b = s.index(README_START), s.index(README_END) + len(README_END)
    p.write_text(s[:a] + readme_banner(gate) + s[b:])


if __name__ == "__main__":
    render_root()
    render_index()
    render_exec()
    render_strips()
    render_readme()
    print("rendered docs/index.html banner and docs/executive-summary.html from docs/data/submission_gate.json")
