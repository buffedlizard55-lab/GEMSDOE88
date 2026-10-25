"""Execute the Pages decision banner with real local feeds; catch JS schema drift."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


def test_current_decision_precedes_archived_download_on_both_pages():
    for rel in ("docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / rel).read_text()
        current = html.index('id="autonomous-review"')
        historical = html.index('id="hgvc-current"') if rel == "docs/index.html" else html.index("Archived H88-HGVC GeoTIFF")
        assert current < historical, f"stale candidate appears before current decision in {rel}"
        assert "NO NEW TIFF" in html
        assert "H88-HGVC" in html
    guide = (ROOT / "docs/executive-summary.html").read_text()
    assert "CURRENT DECISION 2026-10-25: NO NEW UNIQUE TIFF" in guide


@pytest.mark.skipif(NODE is None, reason="Node.js runtime unavailable")
@pytest.mark.parametrize("state,offset_hours,expected", [
    ("fresh", 1, "NO FILE APPROVED · ARCHIVED RESEARCH DOWNLOAD: YES · SUBMIT: NO — DO NOT SUBMIT"),
    ("missing", 1, "PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT"),
    ("stale", 25, "SAVED LOCAL AUDIT STALE (>24H) · ARCHIVED RESEARCH DOWNLOAD ONLY · SUBMIT: NO — DO NOT SUBMIT"),
    ("future", -2, "PRE-FLIGHT AUDIT UNAVAILABLE OR INCONSISTENT — DO NOT SUBMIT"),
])
def test_mtas_banner_fails_closed_with_fresh_missing_stale_or_future_feeds(state, offset_hours, expected):
    # No browser-only APIs required by the banner. Use the actual site.js and
    # committed JSON; this catches a valid-looking but wrong certificate key.
    snippet = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const banner = {textContent: 'static DO NOT SUBMIT'};
const fail = process.env.AUDIT_STATE === 'missing';
const checked = JSON.parse(fs.readFileSync('docs/data/download_audit.json', 'utf8')).checked_at_utc;
const offsetMs = Number(process.env.CLOCK_OFFSET_HOURS) * 3600_000;
// Anchor the test clock to the saved evidence; CI must also pass years later.
class Clock extends Date { static now() { return Date.parse(checked) + offsetMs; } }
const env = {
  document: {
    querySelector: sel => sel === '[data-card-status]' ? banner : null,
    querySelectorAll: () => [],
  },
  fetch: async url => {
    if (fail && (url === 'data/mtas88_run_card.json' || url === 'data/download_audit.json' || url === 'data/vcaz88_run_card.json')) return {ok: false};
    const data = JSON.parse(fs.readFileSync(path.join('docs', url), 'utf8'));
    return {ok: true, json: async () => data};
  },
  setTimeout, clearTimeout, console, Date: Clock,
};
vm.runInNewContext(fs.readFileSync('docs/assets/site.js', 'utf8'), env);
setImmediate(() => {
  const expected = process.env.EXPECTED_BANNER;
  if (banner.textContent !== expected) {
    console.error('Incorrect decision:', banner.textContent, 'expected:', expected);
    process.exitCode = 1;
  }
});
"""
    import os

    env = {**os.environ, "AUDIT_STATE": state, "CLOCK_OFFSET_HOURS": str(offset_hours),
           "EXPECTED_BANNER": expected}
    result = subprocess.run(
        [NODE, "-e", snippet], cwd=ROOT, env=env, capture_output=True, text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_concurrent_lsc_psgv_and_vcaz_records_cannot_precede_canonical_decision():
    for relative in ('docs/index.html', 'docs/executive-summary.html'):
        html = (ROOT / relative).read_text()
        assert html.index('id="autonomous-review"') < html.index('class="archive-lanes"')
        for anchor in ('vcaz88-archived', 'lsc88-archived', 'psgv88-archived'):
            assert html.index('class="archive-lanes"') < html.index(f'id="{anchor}"')
        assert 'data/vcaz88_run_card.json' in html
        assert 'data/lsc88_run_card.json' in html
        assert 'data/psgv88_run_card.json' in html
