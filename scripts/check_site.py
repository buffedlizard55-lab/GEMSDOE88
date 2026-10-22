"""Check every local HTML href and ensure blocked status cannot expose a TIFF."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json

ROOT = Path(__file__).resolve().parents[1]

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ('href', 'src') and value)


def main():
    card = json.loads((ROOT / 'evidence/run-card.json').read_text())
    assert len(card['submission_note']) <= 140
    assert card['verdict'] in ('negative', 'promote')
    pages = [ROOT / 'index.html', ROOT / 'docs/executive-summary.html']
    for page in pages:
        parser = Links(); parser.feed(page.read_text())
        if not card['submission_ready']:
            assert 'BLOCKED — DO NOT SUBMIT' in page.read_text()
        for link in parser.links:
            u = urlsplit(link)
            if u.scheme or u.netloc or not u.path:
                continue
            path = (page.parent / unquote(u.path)).resolve()
            assert path.is_relative_to(ROOT), f'Escaping link: {link}'
            assert path.is_file(), f'Broken link: {page.name}: {link}'
            if not card['submission_ready']:
                assert path.suffix.lower() not in ('.tif', '.tiff', '.zip')
    print('PASS: local links, blocked banners, note length, no misleading submission download')

if __name__ == '__main__':
    main()
