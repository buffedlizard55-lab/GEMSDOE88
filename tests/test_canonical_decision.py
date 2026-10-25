"""The first download and decision are one generated, fail-closed surface."""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import render_decision  # noqa: E402


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.downloads = []
        self.ids = []
        self.h1s = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a' and a.get('href', '').lower().endswith(('.tif', '.tiff')):
            self.downloads.append(a['href'])
        if 'id' in a:
            self.ids.append(a['id'])
        self.h1s += tag == 'h1'


def test_both_pages_lead_with_exact_canonical_research_file_and_one_heading():
    current = json.loads((ROOT / 'docs/data/current_release.json').read_text())
    for name, kind in [('index.html', 'overview'), ('executive-summary.html', 'guide')]:
        text = (ROOT / 'docs' / name).read_text()
        parsed = Page()
        parsed.feed(text)
        assert parsed.downloads[0] == str(Path(current['file']).relative_to('docs'))
        assert parsed.h1s == 1
        assert len(parsed.ids) == len(set(parsed.ids)), 'duplicate anchors break navigation and audit targeting'
        assert text.split('<main id="main">')[1].split(render_decision.START)[0].strip() == ''
        assert render_decision.replace_block(text, render_decision.render(ROOT, kind)) == text
        assert text.index('id="mtas-review"') < text.index('class="archive-lanes"')


@pytest.mark.parametrize('bad', ['', '<!-- CANONICAL-DECISION:START -->',
                                  '<!-- CANONICAL-DECISION:END --><!-- CANONICAL-DECISION:START -->',
                                  render_decision.START * 2 + render_decision.END])
def test_ambiguous_markers_cannot_silently_publish(bad):
    with pytest.raises(ValueError):
        render_decision.replace_block(bad, 'content')


@pytest.mark.parametrize('corruption', ['prepend', 'alter-panel', 'open-archive'])
@pytest.mark.parametrize('optimized', [False, True])
def test_site_guard_rejects_visible_status_regressions(tmp_path, corruption, optimized):
    for directory in ('registry', 'evidence'):
        (tmp_path / directory).symlink_to(ROOT / directory, target_is_directory=True)
    docs = tmp_path / 'docs'
    docs.mkdir()
    for source in (ROOT / 'docs').iterdir():
        if source.name == 'index.html':
            text = source.read_text()
            if corruption == 'prepend':
                text = text.replace('<main id="main">', '<main id="main"><section>NEW UNIQUE TIFF READY TO SUBMIT</section>', 1)
            elif corruption == 'alter-panel':
                text = text.replace('Research download.<br>Not cleared to submit.', 'New unique entry: submit it.', 1)
            else:
                text = text.replace('<details class="archive-lanes">', '<details class="archive-lanes" open>', 1)
            (docs / source.name).write_text(text)
        else:
            (docs / source.name).symlink_to(source, target_is_directory=source.is_dir())
    command = [sys.executable] + (['-O'] if optimized else []) + [
        '-c', 'from pathlib import Path; from scripts.check_site import main; import sys; main(Path(sys.argv[1]))', str(tmp_path)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode != 0
    assert 'PASS:' not in result.stdout


NODE = shutil.which('node')


@pytest.mark.skipif(NODE is None, reason='Node unavailable')
@pytest.mark.parametrize('mutation', ['approve', 'hash', 'missing', 'zip', 'future', 'empty-proof'])
def test_runtime_cannot_upgrade_an_inconsistent_audit(mutation):
    script = r"""
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const banner = {textContent:'DO NOT SUBMIT'};
const mutation = process.env.MUTATION;
const env = {
 document:{querySelector:s=>s==='[data-card-status]'?banner:null,querySelectorAll:()=>[]},
 fetch:async url=>{
  if(mutation==='missing' && url==='data/download_audit.json') return {ok:false};
  let d=JSON.parse(fs.readFileSync(path.join('docs',url),'utf8'));
  if(url==='data/current_release.json'){
   if(mutation==='approve') d.ok_to_submit=true;
   if(mutation==='hash') d.file_sha256='a'.repeat(64);
  }
  if(url==='data/download_audit.json'){
   if(mutation==='zip') d.artifacts.forEach(r=>r.zip_one_byte_identical_tif=false);
   if(mutation==='future') d.checked_at_utc='2999-01-01T00:00:00Z';
  }
  if(mutation==='empty-proof' && url==='data/mtas88_run_card.json') d.preplacement_registry_proof={};
  return {ok:true,json:async()=>d};
 }, Date, console, setTimeout,
};
vm.runInNewContext(fs.readFileSync('docs/assets/site.js','utf8'),env);
setImmediate(()=>{
 if(!banner.textContent.includes('AUDIT UNAVAILABLE') || !banner.textContent.endsWith('DO NOT SUBMIT')){
  console.error(banner.textContent);process.exitCode=1;
 }
});
"""
    import os
    result = subprocess.run([NODE, '-e', script], cwd=ROOT, env={**os.environ, 'MUTATION': mutation}, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
