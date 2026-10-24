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
    card = json.loads((root / 'registry/run_card.json').read_text())
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert len(card['submission_note']) <= 140
    # 2026-10-24 PROVCREST promoted candidate (IR-88-58): the ONLY non-DO-NOT-SUBMIT
    # download allowed, and only while its run card still says promote + ok_to_submit
    # and the on-disk TIFF hash matches the card. Fail closed otherwise.
    prov = json.loads((root / 'registry' / 'provcrest_run_card.json').read_text())
    assert prov['verdict'] == 'promote' and prov['submission']['ok_to_submit'] is True
    assert len(prov['submission']['submission_note']) <= 140
    import hashlib as _hl
    prov_tif = root / prov['submission']['file']
    assert prov_tif.is_file() and _hl.sha256(prov_tif.read_bytes()).hexdigest() == prov['submission']['sha256']
    allowed_promoted = {prov_tif.resolve(), (root / prov['submission']['zip_file']).resolve()}
    # 2026-10-24 LBCAL candidate (IR-88-59): hash must match its run card; while the run card says
    # ok_to_submit false the file name must carry DO-NOT-SUBMIT and the pages must say HOLD.
    lb = json.loads((root / 'registry' / 'lbcal_run_card.json').read_text())
    lb_tif = root / lb['raster']['file']
    assert lb_tif.is_file() and _hl.sha256(lb_tif.read_bytes()).hexdigest() == lb['raster']['sha256']
    assert len(lb['raster']['note']) <= 140 and lb['format_ok'] is True and lb['ok_to_download'] is True
    if lb['ok_to_submit'] is not True:
        assert 'DO-NOT-SUBMIT' in lb_tif.name, 'held LBCAL file must be named DO-NOT-SUBMIT'
    else:
        allowed_promoted |= {lb_tif.resolve(), (root / lb['raster']['zip']).resolve()}
    assert json.loads((root / 'docs' / 'data' / 'lbcal_run_card.json').read_text())['raster']['sha256'] == lb['raster']['sha256']
    pages = [root / 'index.html', *sorted((root / 'docs').glob('*.html'))]
    assert len(pages) >= 5
    for page in pages:
        text = page.read_text()
        if page.name in ('index.html', 'executive-summary.html'):
            assert 'DO NOT SUBMIT' in text, f'Missing safety banner: {page}'
        parser = Links()
        parser.feed(text)
        for link in parser.links:
            u = urlsplit(link)
            if u.scheme or u.netloc or not u.path:
                continue
            path = (page.parent / unquote(u.path)).resolve()
            assert path.is_relative_to(root), f'Escaping link: {link}'
            assert path.is_file(), f'Broken link: {page.name}: {link}'
            if path.suffix.lower() in ('.tif', '.tiff', '.zip'):
                assert path.is_relative_to(root / 'docs/downloads'), link
                assert 'DO-NOT-SUBMIT' in path.name or path.resolve() in allowed_promoted, f'Unmarked research download: {link}'
    print('PASS: site links, explicit negative decision, clearly marked research downloads')


if __name__ == '__main__':
    main()
