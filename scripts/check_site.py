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
    import hashlib as _hl
    card = json.loads((root / 'registry/run_card.json').read_text())
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert len(card['submission_note']) <= 140
    # The executive page, home page and public JSON feed must identify the same
    # current artifact; stale parallel-session banners are a safety defect.
    current = json.loads((root / 'docs' / 'data' / 'current_release.json').read_text())
    assert current['file'] == card['artifact']
    assert current['file_sha256'] == card['raster_sha256']
    assert current['zip_sha256'] == card['zip_sha256']
    assert current['ok_to_download_for_research'] is True
    assert current['ok_to_submit'] is False
    assert current['holdout_evaluator'] == card['holdout_dti']['evaluator_version']
    assert current['holdout_withheld_positive_pixels'] == card['holdout_dti']['withheld_positive_pixels']
    assert current['holdout_dti'] == card['holdout_dti']['candidate']
    assert current['literal_registry_overlap_3px'] == card['correlation_overlap_vs_registry']['final_max_forward_overlap_3px_all_rasters']
    canonical_tif = root / card['artifact']
    canonical_zip = root / card['zip_artifact']
    assert canonical_tif.is_file() and canonical_zip.is_file()
    assert _hl.sha256(canonical_tif.read_bytes()).hexdigest() == card['raster_sha256']
    assert _hl.sha256(canonical_zip.read_bytes()).hexdigest() == card['zip_sha256']
    # Rasters whose own machine gate record clears them for submission (and which must
    # therefore NOT be renamed to DO-NOT-SUBMIT). Collected from every gate record.
    cleared_names = set()
    for rec in sorted((root / 'registry').glob('*gate*.json')):
        try:
            data = json.loads(rec.read_text())
        except (ValueError, OSError):
            continue
        tif_name = Path((data.get('candidate') or {}).get('tif', '')).name
        if data.get('ok_to_submit') and tif_name:
            cleared_names.add(tif_name)
            cleared_names.add(tif_name[:-4] + '.zip')
    # Archived LBCAL candidate: retain its independent file-integrity and safety checks.
    lb = json.loads((root / 'registry' / 'lbcal_run_card.json').read_text())
    lb_tif = root / lb['raster']['file']
    assert lb_tif.is_file() and _hl.sha256(lb_tif.read_bytes()).hexdigest() == lb['raster']['sha256']
    assert len(lb['raster']['note']) <= 140 and lb['format_ok'] is True and lb['ok_to_download'] is True
    assert lb['ok_to_submit'] is True or 'DO-NOT-SUBMIT' in lb_tif.name, 'held LBCAL file must be named DO-NOT-SUBMIT'
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
                # IR-88-71 marks withdrawn research files in the FILENAME. A file whose own
                # machine gate says ok_to_submit is not withdrawn and must not be forced to
                # claim otherwise, so it is cleared by its gate record instead (IR-88-76).
                if 'DO-NOT-SUBMIT' not in path.name:
                    assert path.name in cleared_names, f'Unmarked research download: {link}'
    print('PASS: site links, explicit negative decision, clearly marked research downloads')


if __name__ == '__main__':
    main()
