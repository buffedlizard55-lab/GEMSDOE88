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
    # Single authoritative gate (scripts/submission_gate.py, IR-88-59): the promoted TIFF/ZIP are
    # the only non-DO-NOT-SUBMIT downloads allowed, only while docs/data/submission_gate.json says
    # OK_TO_SUBMIT with zero failures and the on-disk TIFF hash matches. Fail closed otherwise.
    import hashlib as _hl
    gate = json.loads((root / 'docs' / 'data' / 'submission_gate.json').read_text())
    cand = gate['candidate']
    assert len(cand['note']) <= 140 and len(cand['submission_name']) <= 140
    prov_tif = root / cand['file']
    assert prov_tif.is_file() and _hl.sha256(prov_tif.read_bytes()).hexdigest() == cand['sha256']
    gate_ok = gate['verdict'] == 'OK_TO_SUBMIT' and gate['ok_to_submit'] is True and not gate['failures']
    allowed_promoted = {prov_tif.resolve(), (root / cand['zip_file']).resolve()} if gate_ok else set()
    pages = [root / 'index.html', *sorted((root / 'docs').glob('*.html'))]
    assert len(pages) >= 5
    for page in pages:
        text = page.read_text()
        if page.name in ('index.html', 'executive-summary.html'):
            assert f'data-gate-verdict="{gate["verdict"]}"' in text, f'Page disagrees with gate verdict: {page}'
            assert 'DO-NOT-SUBMIT' in text or 'DO NOT SUBMIT' in text, f'Missing archive safety marker: {page}'
            if not gate_ok:
                assert 'DO NOT SUBMIT' in text, f'Missing safety banner: {page}'
            elif page.parent == root / 'docs':
                assert cand['sha256'] in text and cand['note'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') in text, f'Page lacks gate sha/note: {page}'
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
                assert path in allowed_promoted or 'DO-NOT-SUBMIT' in path.name, f'Unmarked or withdrawn research download: {link}'
    print('PASS: site links, explicit negative decision, clearly marked research downloads')


if __name__ == '__main__':
    main()
