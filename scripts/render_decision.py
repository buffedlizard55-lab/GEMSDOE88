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


def read_inputs(root: Path) -> tuple[dict, dict, dict]:
    """Canonical decision inputs: the current release card, its lane run card, the file audit."""
    current = json.loads((root / "docs/data/current_release.json").read_text())
    card = json.loads((root / current["run_card"]).read_text())
    audit = json.loads((root / "docs/data/download_audit.json").read_text())
    status = json.loads((root / "docs/status.json").read_text())
    if current.get("schema") != "gems88.current-release.v3":
        raise ValueError("current_release.json must be schema v3 (IR-88-SDTL-01)")
    if card.get("schema") != "gems88.run_card.v2" or card["raster"]["sha256"] != current["file_sha256"]:
        raise ValueError("release card and lane run card disagree")
    promote = card["verdict"] == "promote" and card["ok_to_submit"] is True
    if (current["ok_to_submit"] is not promote or status["ok_to_submit"] is not promote
            or status["raster_sha256"] != current["file_sha256"]
            or audit["canonical_sha256"] != current["file_sha256"]
            or audit["ok_to_submit"] is not promote
            or (audit["protocol_eligible_count"] > 0) is not promote):
        raise ValueError("canonical decision inputs disagree; never render a clearance from inconsistent evidence")
    for key, digest_key in (("file", "file_sha256"), ("zip_file", "zip_sha256")):
        relative = Path(current[key])
        if relative.parent != Path("docs/downloads"):
            raise ValueError("canonical file must live in docs/downloads")
        if ("DO-NOT-SUBMIT" in relative.name) is promote:
            raise ValueError("filename marker contradicts verdict")
        with (root / relative).open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != current[digest_key]:
                raise ValueError("canonical downloadable bytes disagree with release card")
    return current, card, audit


def inventory(audit: dict) -> str:
    rows = []
    for row in audit["artifacts"]:
        name = escape(row["file"])
        label = name.removesuffix("-DO-NOT-SUBMIT.tif").removesuffix(".tif")
        download = (f'<a href="downloads/{name}" download>TIFF</a> · '
                    f'<a href="downloads/{escape(row.get("zip_file", ""))}" download>ZIP</a>'
                    if row["research_download_ok"] else "Quarantined — see audit")
        tag = ('<span class="tag ok">OK TO SUBMIT</span>' if row.get("ok_to_submit") is True
               else '<span class="tag bad">DO NOT SUBMIT</span>')
        rows.append(f'<tr><th scope="row"><span class="mono">{label}</span></th>'
                    f'<td>{row.get("positive_pixels", 0):,}</td><td>{"PASS" if row["format_valid"] else "FAIL"}</td>'
                    f'<td>{download}</td><td>{tag}</td></tr>')
    return (f'<section class="inventory-section"><div class="wrap"><details id="download-inventory" class="download-inventory">'
            f'<summary>All {audit["tiff_count"]} published TIFFs · automated file audit · {audit["protocol_eligible_count"]} eligible</summary>'
            '<p>Every file is reopened with two decoders and checked for finite [0,1], the exact sample grid, footprint, catalogue and ZIP integrity. '
            'Eligibility comes only from a versioned run card (holdout + leakage canary + equal-support uniqueness + validator). '
            '<a href="data/download_audit.json">Full audit (JSON)</a>.</p>'
            '<div class="table-scroll"><table><thead><tr><th>File</th><th>Positive pixels</th><th>Local format</th>'
            '<th>Download</th><th>Submission</th></tr></thead><tbody>' + ''.join(rows) +
            '</tbody></table></div></details></div></section>')


def _fmt(x, nd=4):
    return "n/a" if x is None else f"{x:.{nd}f}"


def render(root: Path, kind: str) -> str:
    current, card, audit = read_inputs(root)
    promote = current["ok_to_submit"] is True
    tif = escape(Path(current["file"]).relative_to("docs").as_posix())
    zipped = escape(Path(current["zip_file"]).relative_to("docs").as_posix())
    name, note = escape(current["submission_name"]), escape(current["submission_note"])
    digest = escape(current["file_sha256"])
    checked = escape(audit["checked_at_utc"])
    h = card["holdout_dti"]
    cand, ctrl, delta = h["candidate"], h["control_phys44"], h["paired_delta_vs_control"]
    u = card["correlation_overlap_vs_registry"]
    v = card["validator"]
    can = card["leakage_canary"]
    pill = ('<span class="ok-pill">SUBMIT: YES — OK TO DOWNLOAD AND SUBMIT</span>' if promote
            else '<span class="blocked-pill">SUBMIT: NO — DO NOT SUBMIT</span>')
    headline = ("New unique TIFF generated.<br>Cleared by every automatic gate." if promote
                else "New unique TIFF generated.<br>Not cleared — do not submit.")
    reasons = []
    if not h["success"]:
        reasons.append(f"HOLDOUT: paired delta vs control {delta['delta']:+.4f} CI {delta['ci95']} / folds won {h['folds_won_vs_control']} did not meet the preregistered rule")
    if not can["passed"]:
        reasons.append("LEAKAGE: a single feature exceeded AUC 0.90")
    if not u["surface_ok"] or not u["dots_ok"]:
        reasons.append(f"UNIQUENESS: worst equal-support overlap {_fmt(u['dots_worst_equal_support_overlap'])} / worst |rho| {_fmt(max(u['surface_worst_abs_spearman'], u['dots_worst_abs_spearman'] or 0))}")
    if not v["ok"]:
        reasons.append("VALIDATOR: file format check failed")
    reason_html = ("".join(f"<li>{escape(r)}</li>" for r in reasons) if reasons
                   else "<li>All four gates passed: holdout rule, leakage canary, equal-support uniqueness, on-disk validator.</li>")
    lane = escape(card["lane"])
    hero = f"""<section class="decision-hero" id="current-decision" aria-labelledby="decision-title">
<div class="wrap" id="autonomous-review">
<div class="decision-kicker">Current decision · {escape(card['generated_utc'][:10])} · lane {lane} · verdict {escape(card['verdict']).upper()}</div>
<div class="decision-grid"><div>
<h1 id="decision-title">{headline}</h1>
<p class="decision-lead"><strong>{'OK TO SUBMIT.' if promote else 'DO NOT SUBMIT.'}</strong> This file was generated in this session by the preregistered {lane} lane (stress-field slip/dilation-tendency lineaments), validated automatically — no human inspection step — and compared against {u['rasters_checked']} registry rasters.</p>
<div class="decision-pills"><span>DOWNLOAD: YES</span>{pill}</div>
<ul class="gate-reasons">{reason_html}</ul>
<p class="micro">HOLDOUT-DTI ({escape(h['evaluator_version'])}, {cand['withheld_positive_pixels']:,} withheld positives): candidate <strong>{_fmt(cand['dti'])}</strong> [{_fmt(cand['ci95'][0])}, {_fmt(cand['ci95'][1])}] vs control {_fmt(ctrl['dti'])}; paired delta {delta['delta']:+.4f} [{delta['ci95'][0]:+.4f}, {delta['ci95'][1]:+.4f}]; folds won {escape(str(h['folds_won_vs_control']))}. No ORGANIZER-CONFIRMED score exists for this file. <a href="data/sdtl88_run_card.json">Run card (JSON)</a>.</p>
</div><aside class="decision-download" aria-label="Current file">
<div class="decision-kicker">{'Submission file' if promote else 'Research file'} · {lane}</div>
<h2>{'Download and submit this TIFF' if promote else 'Download for research only'}</h2>
<p>Single-band GeoTIFF · float32 · finite [0, 1] · zero on the mapped catalogue · exact sample CRS/shape/transform · {card['raster']['n_dots']:,} dots.</p>
<a class="button button-primary decision-file" href="{tif}" download>↓ Download TIFF</a>
<div class="download-secondary"><a href="{zipped}" download>One-TIFF ZIP</a><a href="data/download_audit.json">Automated audit ↗</a></div>
<dl class="download-identity"><dt>Submission name</dt><dd><code>{name}</code></dd>
<dt>SHA-256</dt><dd><code>{digest}</code></dd></dl>
<details class="note-details" open><summary>Note for the submission form · {len(current['submission_note'])}/140 characters</summary><p><code>{note}</code></p><button class="copy" data-copy="{note}" type="button">Copy</button></details>
<p class="micro">Audit performed <time datetime="{checked}">{checked}</time>.</p>
</aside></div></div></section>
<section class="decision-gates"><div class="wrap">
<div class="section-heading"><div><div class="kicker">Four automatic gates</div><h2>What was validated</h2></div><a href="data/sdtl88_run_card.json">Run card JSON ↗</a></div>
<div class="gate-grid">
<article class="gate-card"><span class="tag {'ok' if h['success'] else 'bad'}">HOLDOUT {'PASS' if h['success'] else 'FAIL'}</span><h3>Hide-and-recover</h3><p>Whole catalogue components withheld with a 3 px buffer, 8 folds (2 seeds × 4 quadrants); catalogue-derived features rebuilt from visible faults; pooled DTI α=0.2 β=0.8, 300 m kernel. Candidate {_fmt(cand['dti'])} vs control {_fmt(ctrl['dti'])}; far &gt;10 px {_fmt(h['far_gt10px']['candidate_sdtl']['dti'])} vs {_fmt(h['far_gt10px']['control_phys44']['dti'])}.</p></article>
<article class="gate-card"><span class="tag {'ok' if can['passed'] else 'bad'}">CANARY {'PASS' if can['passed'] else 'FAIL'}</span><h3>Leakage</h3><p>{can['features_tested']} new features tested alone; max symmetric AUC {_fmt(can['max_symmetric_auc'])} (limit 0.90).</p></article>
<article class="gate-card"><span class="tag {'ok' if (u['surface_ok'] and u['dots_ok']) else 'bad'}">UNIQUENESS {'PASS' if (u['surface_ok'] and u['dots_ok']) else 'FAIL'}</span><h3>Registry comparison</h3><p>Surface worst |ρ| {_fmt(u['surface_worst_abs_spearman'])} (limit 0.90); final dots worst equal-support 3 px overlap {_fmt(u['dots_worst_equal_support_overlap'])} (limit 0.70) against {u['rasters_checked']} rasters. Rule: {escape(u['binding_rule'])}.</p></article>
<article class="gate-card"><span class="tag {'ok' if v['ok'] else 'bad'}">VALIDATOR {'PASS' if v['ok'] else 'FAIL'}</span><h3>File format</h3><p>No NaN inside footprint: {v['no_nan_inside_footprint']}. Values in [0,1]: {v['values_in_0_1']}. CRS/shape/transform match: {v['crs_match'] and v['shape_match'] and v['transform_match']}. No mass outside footprint: {v['no_mass_outside']}.</p></article>
</div></div></section>"""
    if kind == "overview":
        content = """<section class="decision-explainer"><div class="wrap split">
<div><div class="kicker">Why H33 scored 0.2778 (user-reported)</div><h2>Binary dots, 2.8 px tiling, collar pruning.</h2>
<p>H33 is the D2.8 dotted emission of the H19-5 lineament surface with its 6,436 dots lying ≤2 px from the catalogue removed (37,654 dots). Each dot at value 1.0 maximises DTI per unit of placed mass; 2.8 px spacing tiles the 300 m triangular kernel with minimal redundant false-positive charge; and removing collar dots deletes mass that mostly sits next to already-known (masked) faults.</p>
<p>A new approach beats it only by placing the same order of dots on a better habitat map of <em>unmapped</em> faults. The current lane tests one physical hypothesis for that habitat; the holdout result, not a forecast, decides promotion.</p>
<a href="research/session-sdtl88-20261025.md">Full PhD-level answer, ranked hypotheses, results →</a></div>
<div class="proof"><div class="kicker">Protocol correction IR-88-SDTL-01</div><h3>Dense surfaces are compared by their top-n cells.</h3>
<p>The 17GEMSDOE witness is positive on every allowed pixel, so the earlier literal reading flagged every nonempty raster as a duplicate and no unique file could ever be produced. The shared module now compares a continuous registry surface through its top-n cells at the candidate's dot count and keeps rank correlation against every raster. Thresholds are unchanged.</p>
<a href="../IRREGULARITIES.md">Irregularity log →</a></div></div></section>"""
        return hero + content + inventory(audit)
    if kind != "guide":
        raise ValueError(f"unknown page kind: {kind}")
    guide = f"""<section class="decision-explainer"><div class="wrap narrow"><div class="kicker">Executive summary</div><h2>How to submit, step by step.</h2>
<ol class="steps"><li><h3>Check the decision above</h3><p>If the pill reads <strong>OK TO DOWNLOAD AND SUBMIT</strong>, the file passed all four automatic gates. If it reads <strong>DO NOT SUBMIT</strong>, use it for research only; the reasons are listed above.</p></li>
<li><h3>Download the TIFF (or the one-TIFF ZIP)</h3><p>Use the download button. Confirm the SHA-256 shown above if you want to verify the bytes (<code>sha256sum &lt;file&gt;</code>).</p></li>
<li><h3>Open the DrivenData submission page</h3><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">competitions/306/competition-doe-gems/submissions</a> → “New submission”. The portal accepts a single-band GeoTIFF (.tif) or a .zip containing one GeoTIFF matching the sample's CRS, shape and geotransform.</p></li>
<li><h3>Paste the name and note</h3><p>Name: <code>{name}</code><br>Note (≤140 chars): <code>{note}</code></p></li>
<li><h3>Record the receipt</h3><p>Copy the portal score into <code>docs/data/user_reported_results.csv</code> with the file name; only a submission-page receipt may be labelled ORGANIZER-CONFIRMED.</p></li></ol>
<p class="fine">The verdict is computed by code from the run card; changing a stored boolean is not clearance. Human inspection or a selector decision cannot override failed uniqueness or scientific gates. Weekly slot choice is the owner's — this site never picks one.</p>
<div class="callout warn"><h3>About the earlier “Predicted values must be in range [0, 1]” error</h3><p>That portal message is a file check. Files published here are written with <code>nodata=None</code>, all-finite float32, zeros outside the footprint and values exactly in {{0, 1}}; the validator output is in the run card.</p></div>
<h3 class="reproduce-heading">Reproduce without manual inspection</h3>
<pre class="command-block"><code>bash scripts/download_competition_data.sh
python scripts/run_sdtl88_experiment.py       # holdout + canary (writes evidence/sdtl88_*.json)
python scripts/build_sdtl88_submission.py     # uniqueness v5 + writer + run card
python scripts/publish_sdtl88.py              # release card, audit, rendered pages
python scripts/audit_downloads.py --check && python scripts/render_decision.py --check</code></pre>
</div></section>"""
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
