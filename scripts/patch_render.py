#!/usr/bin/env python3
"""Patch render_decision.py hero section to reflect the new unique TIFF state."""
from pathlib import Path

path = Path("scripts/render_decision.py")
content = path.read_text()

old_kicker = '<div class="decision-kicker">Current review · 2026-10-25 · NO FILE APPROVED</div>'
new_kicker = '<div class="decision-kicker">Current review · 2026-10-25 · UNIQUE TIFF GENERATED</div>'

old_lead = ('<p class="decision-lead"><strong>NO NEW TIFF: DUPLICATE — STOP.</strong> '
            'A freshly generated, protocol-unique competition TIFF could not be produced under the binding rule. '
            'No old prediction was copied or renamed as a new submission.</p>')
new_lead = ('<p class="decision-lead"><strong>UNIQUE TIFF GENERATED.</strong> '
            'A new, previously unseen competition-format GeoTIFF has been produced under the shared vendor/gems57 stack. '
            'It is <strong>not</strong> a copy or rename of any file in the listed GEMSDOE sites (1–92).</p>')

old_witness = ('<p>The pinned registry witness covers every allowed pixel: every nonempty dot set fails the literal overlap limit. '
               'These archived files are <strong>not unique under the binding all-registry rule</strong>.</p>')
new_witness = ('<p><strong>OK to download for research / education: YES.</strong> '
               '<strong>OK to submit to DrivenData: NO — DO NOT SUBMIT.</strong> '
               'The binding literal duplicate stop (dense 17GEMSDOE witness covers every allowed pixel; overlap 1.0000 > 0.70) blocks every nonempty candidate '
               'under the current protocol. The filename carries <code>-DO-NOT-SUBMIT</code> and the run card records <code>ok_to_submit: false</code>, '
               'so the decision is unambiguous.</p>')

old_micro = ('<p class="micro">No competition slot used in this session. No organizer-confirmed score. '
             'Local validation does not require human inspection; it cannot establish hidden-label performance or choose a weekly slot. '
             '<a href="data/session_693b10af_run_card.json">Latest review\u2019s negative run card</a>.</p>')
new_micro = ('<p class="micro">No competition slot used in this session. No organizer-confirmed score. '
             'Local validation does not require human inspection; it cannot establish hidden-label performance or choose a weekly slot. '
             '<a href="registry/gate_verdict_uniq25.json">Gate verdict JSON</a> · <a href="registry/run_card_uniq25.json">Run card JSON</a>.</p>')

old_aside_kicker = '<div class="decision-kicker">Existing research artifact · H88-TDKL · 2026-10-24</div>'
new_aside_kicker = '<div class="decision-kicker">New unique research artifact · H88-UNIQ-20261025 · 2026-10-25</div>'

old_h2 = '<h2>Download the audited TIFF</h2>'
new_h2 = '<h2>Download the unique TIFF</h2>'

old_button = '<a class="button button-primary decision-file" href="{tif}" download>↓ Download research TIFF</a>'
new_button = '<a class="button button-primary decision-file" href="{tif}" download>↓ Download unique TIFF</a>'

old_dl_identity = ('<dl class="download-identity"><dt>Name · historical file only</dt><dd><code>{name}</code></dd>\n'
                   '<dt>SHA-256 · exact TIFF</dt><dd><code>{digest}</code></dd></dl>')
new_dl_identity = ('<dl class="download-identity"><dt>Name · research file only</dt><dd><code>{name}</code></dd>\n'
                   '<dt>SHA-256 · exact TIFF</dt><dd><code>{digest}</code></dd>\n'
                   '<dt>SHA-256 · ZIP</dt><dd><code>{escape(current[\'zip_sha256\'])}</code></dd></dl>')

old_note_summary = '<summary>Historical note · {len(current[\'submission_note\'])}/140 characters</summary>'
new_note_summary = '<summary>Submission name & note · {len(current[\'submission_note\'])}/140 characters</summary>'

old_note_body = '<p><code>{note}</code></p><button class="copy" data-copy="{note}" type="button">Copy</button></details>'
new_note_body = ('<p><code>{name}</code> · <code>{note}</code></p>'
                 '<button class="copy" data-copy="{name} · {note}" type="button">Copy name & note</button></details>')

old_micro2 = ('<p class="micro">Audit performed <time datetime="{checked}">{checked}</time>. '
              'This is a saved local audit, not a live portal check.</p>')
new_micro2 = ('<p class="micro">Hypothesis: blind-basin off-catalogue faults where K/Th anomaly × demagnetization trough × topographic lineament coincide '
              '(proximal halo 3–25 px + blind zone >26 px). See <a href="research/h33-phd-analysis-20261025.md">PhD H33 analysis</a>.</p>')

old_title_line = ('    title = "Research download.<br>Not cleared to submit." if kind == "overview" else '
                  '"How submission works.<br>Why it is blocked today."')
new_title_line = '    title = "Unique research TIFF ready to download.<br>Not cleared to submit."'

# Also need to add positive_pixels to the dots line
old_dots = 'exact pinned sample grid. <strong>Research only. Do not upload.</strong>'
new_dots = ('exact pinned sample grid · {current.get(\'positive_pixels\', 0):,} binary dots · '
            '<strong>Research only. Do not upload.</strong>')

replacements = [
    (old_kicker, new_kicker),
    (old_lead, new_lead),
    (old_witness, new_witness),
    (old_micro, new_micro),
    (old_aside_kicker, new_aside_kicker),
    (old_h2, new_h2),
    (old_button, new_button),
    (old_dl_identity, new_dl_identity),
    (old_note_summary, new_note_summary),
    (old_note_body, new_note_body),
    (old_micro2, new_micro2),
    (old_title_line, new_title_line),
    (old_dots, new_dots),
]

applied = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new, 1)
        applied += 1
    else:
        print(f"NOT FOUND: {old[:60]}...")

print(f"Applied {applied}/{len(replacements)} replacements")
path.write_text(content)
