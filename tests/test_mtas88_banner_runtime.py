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
@pytest.mark.parametrize("missing", [False, True])
def test_mtas_banner_fails_closed_with_real_or_missing_feeds(missing):
    # No browser-only APIs required by the banner. Use the actual site.js and
    # committed JSON; this catches a valid-looking but wrong certificate key.
    snippet = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const banner = {textContent: 'static DO NOT SUBMIT'};
const fail = process.env.MISSING_FEED === '1';
const env = {
  document: {
    querySelector: sel => sel === '[data-card-status]' ? banner : null,
    querySelectorAll: () => [],
  },
  fetch: async url => {
    if (fail && (url === 'data/mtas88_run_card.json' || url === 'data/download_audit.json')) return {ok: false};
    const data = JSON.parse(fs.readFileSync(path.join('docs', url), 'utf8'));
    return {ok: true, json: async () => data};
  },
  setTimeout, clearTimeout, console, Date,
};
vm.runInNewContext(fs.readFileSync('docs/assets/site.js', 'utf8'), env);
setImmediate(() => {
  const expected = fail ? 'PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT'
    : 'NO FILE APPROVED · ARCHIVED RESEARCH DOWNLOAD: YES · SUBMIT: NO — DO NOT SUBMIT';
  if (banner.textContent !== expected) {
    console.error('Incorrect decision:', banner.textContent, 'expected:', expected);
    process.exitCode = 1;
  }
});
"""
    import os

    env = {**os.environ, "MISSING_FEED": "1" if missing else "0"}
    result = subprocess.run(
        [NODE, "-e", snippet], cwd=ROOT, env=env, capture_output=True, text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_concurrent_lsc_and_psgv_records_cannot_precede_canonical_decision():
    for relative in ('docs/index.html', 'docs/executive-summary.html'):
        html = (ROOT / relative).read_text()
        assert html.index('id="autonomous-review"') < html.index('class="archive-lanes"')
        for anchor in ('lsc88-archived', 'psgv88-archived'):
            assert html.index('class="archive-lanes"') < html.index(f'id="{anchor}"')
        assert 'data/lsc88_run_card.json' in html
        assert 'data/psgv88_run_card.json' in html
