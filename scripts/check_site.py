"""Audit local site links and forbid unlabeled research TIFF/ZIP downloads.

This is a site guard, not the scientific/format gate; validate_qtsk88.py audits
the current H88-QTSK artifact while validate_kth88.py and validate_release.py
retain historical audits. A blocked or selector-held experiment may publish a
clearly marked research-only file (DO-NOT-SUBMIT) for independent audit.
"""
from html.parser import HTMLParser
import hashlib as _hl
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
    # 1. Historical MRR record remains negative
    historical = json.loads((root / 'registry/run_card.json').read_text())
    assert historical['verdict'] == 'negative' and historical['ok_to_submit'] is False
    assert len(historical['submission_note']) <= 140

    # 2. Archived KTH-88 record remains intact and negative
    kth = json.loads((root / 'registry/kth88_run_card.json').read_text())
    kth_validation = json.loads((root / 'docs/data/kth88_validation.json').read_text())
    kth_tif = root / kth['download']
    assert kth['verdict'] == 'negative' and kth['ok_to_submit'] is False
    assert kth['correlation_overlap_vs_registry']['final_overlap_3px'] > .70
    assert kth_tif.is_file() and kth_tif.name.endswith('DO-NOT-SUBMIT.tif')
    assert _hl.sha256(kth_tif.read_bytes()).hexdigest() == kth['raster_sha256']
    assert kth_validation['tif_sha256'] == kth['raster_sha256']
    assert kth_validation['local_format_audit']['ok'] and not kth_validation['ok_to_submit']
    assert len(kth['submission_note']) <= 140

    # 3. Archived LBCAL candidate integrity
    lb = json.loads((root / 'registry' / 'lbcal_run_card.json').read_text())
    lb_tif = root / lb['raster']['file']
    assert lb_tif.is_file() and _hl.sha256(lb_tif.read_bytes()).hexdigest() == lb['raster']['sha256']
    assert len(lb['raster']['note']) <= 140 and lb['format_ok'] is True and lb['ok_to_download'] is True
    assert lb['ok_to_submit'] is True or 'DO-NOT-SUBMIT' in lb_tif.name, 'held LBCAL file must be named DO-NOT-SUBMIT'
    assert json.loads((root / 'docs' / 'data' / 'lbcal_run_card.json').read_text())['raster']['sha256'] == lb['raster']['sha256']

    # 4. Canonical current release: H88-QTSK
    qtsk = json.loads((root / 'registry/qtsk88_run_card.json').read_text())
    qtsk_web = json.loads((root / 'docs/data/qtsk88_run_card.json').read_text())
    current = json.loads((root / 'docs/data/current_release.json').read_text())
    assert qtsk == qtsk_web
    assert qtsk['verdict'] == 'negative' and qtsk['ok_to_submit'] is False
    assert len(qtsk['submission_note']) <= 140
    assert current['file'] == qtsk['raster']['tif_path']
    assert current['file_sha256'] == qtsk['raster']['sha256']
    assert current['zip_sha256'] == qtsk['raster']['zip_sha256']
    assert current['research_download_ok'] is True
    assert current['ok_to_submit'] is False and current['duplicate'] is True
    assert current['like_for_like_unique_222'] is True
    assert current['holdout_evaluator'] == qtsk['evaluator_version']
    assert current['withheld_positive_pixels'] == qtsk['withheld_positive_pixels']
    assert current['holdout_dti'] == qtsk['holdout_dti']
    assert current['holdout_ci95'] == qtsk['holdout_dti_ci95']
    assert current['literal_registry_overlap_3px'] == qtsk['registry_uniqueness']['worst_literal_forward_3px_overlap']['value']

    canonical_tif = root / qtsk['raster']['tif_path']
    canonical_zip = root / qtsk['raster']['zip_path']
    assert canonical_tif.is_file() and canonical_zip.is_file()
    assert _hl.sha256(canonical_tif.read_bytes()).hexdigest() == qtsk['raster']['sha256']
    assert _hl.sha256(canonical_zip.read_bytes()).hexdigest() == qtsk['raster']['zip_sha256']

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
                if 'DO-NOT-SUBMIT' not in path.name:
                    assert path.name in cleared_names, f'Unmarked research download: {link}'

    for page in (root / 'docs/index.html', root / 'docs/executive-summary.html'):
        text = page.read_text()
        assert canonical_tif.name in text, f'Current QTSK artifact not identified on {page.name}'
        assert qtsk['raster']['sha256'][:16] in text, f'Current QTSK SHA prefix missing on {page.name}'
        upper = text.upper()
        assert 'DO NOT SUBMIT' in upper and (
            'DOWNLOAD: YES' in upper or 'DOWNLOAD FOR RESEARCH: YES' in upper
        ), page
    print('PASS: current H88-QTSK run card, current release hashes, site links, and explicit negative decision agree')


if __name__ == '__main__':
    main()
