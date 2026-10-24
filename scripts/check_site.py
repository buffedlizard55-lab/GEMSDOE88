"""Audit local site links and forbid unlabeled research TIFF/ZIP downloads.

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
    pages = [root / 'index.html', *sorted((root / 'docs').glob('*.html'))]
    assert len(pages) >= 5
    for page in pages:
        text = page.read_text()
        if page.name in ('index.html', 'executive-summary.html'):
            assert 'DO NOT SUBMIT' in text, f'Missing safety banner: {page}'
            assert 'OK TO DOWNLOAD AND SUBMIT' not in text, f'Unsafe stale approval: {page}'
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
    print('PASS: site links, explicit negative decision, clearly marked research downloads')


if __name__ == '__main__':
    main()
