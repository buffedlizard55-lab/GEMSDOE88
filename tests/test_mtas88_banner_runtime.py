"""Execute the Pages decision banner with real local feeds; catch JS schema drift."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


def test_current_decision_precedes_archived_download_on_both_pages():
    # 2026-10-25 (H88-LSC): the newest machine verdict must be the first thing
    # on both pages, ahead of the historical (all DO-NOT-SUBMIT) lane banners.
    index = (ROOT / "docs/index.html").read_text()
    decision = index.index('id="decision"')
    autonomous = index.index('id="autonomous-review"')
    historical = index.index('id="hgvc-current"')
    assert decision < autonomous < historical, "stale candidate appears before current decision in docs/index.html"
    assert "OK TO DOWNLOAD: <span" in index and "DO NOT SUBMIT" in index[decision:autonomous]
    assert "H88-HGVC" in index
    guide = (ROOT / "docs/executive-summary.html").read_text()
    strip = guide.index("CURRENT DECISION 2026-10-25 (H88-LSC")
    assert strip < guide.index("Archived H88-HGVC GeoTIFF")
    assert "OK TO SUBMIT NO" in guide[strip:strip + 400]
    assert "H88-HGVC" in guide


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
    if (fail && (url === 'data/mtas88_run_card.json' || url === 'data/gzzc88_run_card.json')) return {ok: false};
    const data = JSON.parse(fs.readFileSync(path.join('docs', url), 'utf8'));
    return {ok: true, json: async () => data};
  },
  setTimeout, clearTimeout, console, Date,
};
vm.runInNewContext(fs.readFileSync('docs/assets/site.js', 'utf8'), env);
setImmediate(() => {
  const expected = fail ? 'PRE-FLIGHT AUDIT UNAVAILABLE — DO NOT SUBMIT'
    : 'H88-MTAS · NO NEW TIFF · OLD FILE DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO — DO NOT SUBMIT (automated duplicate stop)';
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
