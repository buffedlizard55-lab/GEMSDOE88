"""Audit local site links, the machine verdicts (current-release audit AND gate v3) and download placement.

This is a site guard, not the scientific/format gate; validate_release.py is
canonical for the current research artifact. A blocked experiment may still
publish a clearly marked research-only file for independent audit.
"""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ('href', 'src') and value)


def main(root=ROOT):
    # A historical PROVCREST experiment once called itself 'promote', but its
    # literal full-footprint witness fails. It may not be linked as an upload.
    current = json.loads((root / 'registry/fabric_dislocation_run_card.json').read_text())
    status = json.loads((root / 'docs/status.json').read_text())
    audit = json.loads((root / 'docs/data/current_release.json').read_text())
    assert current['verdict'] == 'negative' and current['ok_to_submit'] is False
    assert status['status'] == 'BLOCKED' and status['ok_to_submit'] is False
    assert audit['duplicate'] is True and audit['ok_to_submit'] is False
    assert status['raster_sha256'] == audit['file_sha256'] == current['raster_sha256']
    assert status['current_file'] == audit['file'] == current['file']
    assert (root / 'docs/data/fabric_dislocation_run_card.json').read_bytes() == (root / 'registry/fabric_dislocation_run_card.json').read_bytes()
    assert (root / 'docs/data/fabric_dislocation_uniqueness.json').read_bytes() == (root / 'evidence/fabric_dislocation_uniqueness.json').read_bytes()
    assert (root / 'docs/data/postmerge_tiltzero_audit.json').read_bytes() == (root / 'evidence/postmerge_tiltzero_audit.json').read_bytes()
    assert audit['registry_rasters_checked'] == status['registry_rasters_checked'] == current['correlation_overlap_vs_registry']['registry_rasters_checked'] + 1
    assert (root / 'docs/research/candidates-20261024-fabric-dislocation.md').read_bytes() == (root / 'research/candidates-20261024-fabric-dislocation.md').read_bytes()
    assert (root / 'docs/assets/site.js').is_file() and (root / 'docs/status.json').is_file()
    assert len(current['submission_note']) <= 140
    # ---- gate v3 (session 2026-10-24, IR-88-59..71): candidate B + re-assessed parallel candidates ----
    gv = json.loads((root / 'registry/gate_verdict.json').read_text())
    name, label, ok_submit = gv['name'], gv['label'], bool(gv['ok_to_submit'])
    assert label in ('OK TO DOWNLOAD - OK TO SUBMIT', 'OK TO DOWNLOAD - NOT OK TO SUBMIT', 'NOT OK TO DOWNLOAD OR SUBMIT')
    head_tif = f'downloads/{name}.tif'
    assert (root / 'docs' / head_tif).is_file(), 'candidate B TIFF missing'
    assert name.endswith('GATE-PASS' if ok_submit else 'DO-NOT-SUBMIT'), 'file name does not encode the verdict'
    assert (root / 'docs/data/gate-verdict.json').read_bytes() == (root / 'registry/gate_verdict.json').read_bytes()
    import hashlib
    for tag in ('provcrest', 'tiltzero'):
        rc = json.loads((root / f'registry/{tag}_run_card.json').read_text())
        rec = json.loads((root / f'registry/{tag}_gate_v3.json').read_text())
        f = (root / rc['submission']['file'])
        assert f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest() == rc['submission']['sha256'] == rec['sha256'], f'{tag}: bytes differ from run card / v3 record'
        assert rec['policy'] == 'gems88-gate-v3' and rec['ok_to_submit'] is False, f'{tag}: unexpected v3 verdict'
        assert (root / f'docs/data/{tag}-gate-v3.json').read_bytes() == (root / f'registry/{tag}_gate_v3.json').read_bytes()
    # a file whose name lacks DO-NOT-SUBMIT (PROVCREST) must never be linked from a page (withdrawn, IR-88-71)
    pages = [root / 'index.html', *sorted((root / 'docs').glob('*.html'))]
    assert len(pages) >= 5
    for page in pages:
        text = page.read_text()
        if page.name in ('index.html', 'executive-summary.html'):
            assert 'DO NOT SUBMIT' in text, f'Missing safety banner: {page}'
            assert 'OK TO DOWNLOAD AND SUBMIT' not in text, f'Unsafe stale approval: {page}'
        if page.name in ('index.html', 'executive-summary.html') and page.parent.name == 'docs':
            assert label in text or label.replace('-', '&ndash;') in text, f'Missing verdict label {label!r}: {page}'
            i = text.find('<main')
            assert i >= 0 and head_tif in text[i:i + 9000], f'Candidate B TIFF link not at the top of {page.name}'
            assert 'v3: NOT OK TO SUBMIT' in text, f'{page.name} lacks the v3 re-assessment tag for the parallel candidates'
        parser = Links()
        parser.feed(text)
        for link in parser.links:
            u = urlsplit(link)
            if u.scheme or u.netloc or not u.path:
                continue
            path = (page.parent / unquote(u.path)).resolve()
            assert path.is_relative_to(root), f'Escaping link: {link}'
            if page.is_relative_to(root / 'docs'):
                assert path.is_relative_to(root / 'docs'), f'Link outside published Pages tree: {link}'
            assert path.is_file(), f'Broken link: {page.name}: {link}'
            if path.suffix.lower() in ('.tif', '.tiff', '.zip'):
                assert path.is_relative_to(root / 'docs/downloads'), link
                assert 'DO-NOT-SUBMIT' in path.name, f'Unmarked or withdrawn research download: {link}'
    readme = (root / 'README.md').read_text()
    top = readme[:4000]
    assert f'docs/downloads/{name}.tif' in top, 'README top lacks the one-click TIFF link for candidate B'
    assert label in top, 'README top lacks the verdict label'
    print('PASS: site links, gate-v3 verdicts, current-release audit, one-click downloads at the top, marked research downloads')


if __name__ == '__main__':
    main()
