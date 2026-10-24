"""Audit local site links and forbid unlabeled research TIFF/ZIP downloads.

This is a site guard, not the scientific/format gate; validate_kth88.py audits
the current research artifact, while legacy validators remain historical. A blocked experiment may still
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
    # Historical MRR and KTH remain negative; latest PHASE-88 controls the site.
    historical = json.loads((root / 'registry/run_card.json').read_text())
    assert historical['verdict'] == 'negative' and historical['ok_to_submit'] is False
    phase = json.loads((root / 'registry/phase88_run_card.json').read_text())
    validation = json.loads((root / 'docs/data/phase88_validation.json').read_text())
    current = json.loads((root / 'docs/data/current_release.json').read_text())
    assert current['file'] == phase['download']
    assert current['file_sha256'] == phase['raster_sha256'] == validation['tif_sha256']
    assert current['zip_sha256'] == validation['zip_sha256']
    assert current['research_download_ok'] and not current['ok_to_submit'] and current['duplicate']
    assert current['holdout_evaluator'] == phase['holdout_dti']['evaluator_version']
    assert current['withheld_positive_pixels'] == phase['holdout_dti']['withheld_positive_pixels']
    assert current['holdout_dti'] == phase['holdout_dti']['dti']
    assert current['holdout_ci95'] == phase['holdout_dti']['ci95']
    assert current['literal_registry_overlap_3px'] == phase['correlation_overlap_vs_registry']['final_overlap_3px']
    # MDPS-88 is the newest research artifact, but its strict literal uniqueness
    # gate fails against the all-positive registry witness. Keep its display fail-closed.
    mdps = json.loads((root / 'registry/mdps88_run_card.json').read_text())
    assert mdps['correlation_overlap_vs_registry']['literal_binding_decision']['duplicate'] is True
    assert mdps['correlation_overlap_vs_registry']['literal_binding_decision']['stop_required'] is True
    assert mdps['correlation_overlap_vs_registry']['literal_binding_decision']['forward_overlap_3px'] > 0.70
    assert mdps['gates']['uniqueness_literal_pass'] is False and not mdps['ok_to_submit']
    status = json.loads((root / 'docs/status.json').read_text())
    assert status['raster_sha256'] == mdps['raster_sha256']
    assert status['ok_to_download_for_research'] is True and status['ok_to_submit'] is False
    assert any('DUPLICATE' in reason for reason in status['problems'])
    for page_name in ('index.html', 'executive-summary.html'):
        page_body = (root / 'docs' / page_name).read_text()
        assert 'DUPLICATE' in page_body and 'literal' in page_body.lower(), page_name
        assert 'New unique GeoTIFF' not in page_body, page_name
    canonical_tif = root / phase['download']; canonical_zip = canonical_tif.with_suffix('.zip')
    assert canonical_tif.is_file() and canonical_zip.is_file()
    assert _hl.sha256(canonical_tif.read_bytes()).hexdigest() == phase['raster_sha256']
    assert _hl.sha256(canonical_zip.read_bytes()).hexdigest() == current['zip_sha256']
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
    # Latest experiment must be present on both landing/guide pages and stay
    # blocked even if a historical gate record elsewhere says "promote".
    kth = json.loads((root / 'registry/kth88_run_card.json').read_text())
    kth_tif = root / kth['download']
    kth_validation = json.loads((root / 'docs/data/kth88_validation.json').read_text())
    assert kth['verdict'] == 'negative' and kth['ok_to_submit'] is False
    assert kth['correlation_overlap_vs_registry']['final_overlap_3px'] > .70
    assert kth_tif.is_file() and kth_tif.name.endswith('DO-NOT-SUBMIT.tif')
    assert _hl.sha256(kth_tif.read_bytes()).hexdigest() == kth['raster_sha256']
    assert kth_validation['tif_sha256'] == kth['raster_sha256']
    assert kth_validation['local_format_audit']['ok'] and not kth_validation['ok_to_submit']
    assert len(kth['submission_note']) <= 140
    for page in ('index.html', 'executive-summary.html'):
        body = (root / 'docs' / page).read_text()
        assert kth_tif.name in body and 'DO NOT SUBMIT' in body, page
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
            # Pages uploads only docs/: a repo-relative link outside docs/
            # exists locally but 404s on the deployed website.
            if page.is_relative_to(root / 'docs'):
                assert path.is_relative_to(root / 'docs'), f'Link outside Pages artifact: {page.name}: {link}'
            assert path.is_file(), f'Broken link: {page.name}: {link}'
            if path.suffix.lower() in ('.tif', '.tiff', '.zip'):
                assert path.is_relative_to(root / 'docs/downloads'), link
                # IR-88-71 marks withdrawn research files in the FILENAME. A file whose own
                # machine gate says ok_to_submit is not withdrawn and must not be forced to
                # claim otherwise, so it is cleared by its gate record instead (IR-88-76).
                if 'DO-NOT-SUBMIT' not in path.name:
                    assert path.name in cleared_names, f'Unmarked research download: {link}'
    # Old KTH links remain archival, but the *first* panel must show PHASE-88.
    current = json.loads((root / 'docs/data/current_release.json').read_text())
    assert current['file'] == phase['download']
    assert current['file_sha256'] == phase['raster_sha256']
    assert current['zip_sha256'] == validation['zip_sha256']
    assert current['ok_to_submit'] is False and current['duplicate'] is True
    for page in (root / 'docs/index.html', root / 'docs/executive-summary.html'):
        text = page.read_text()
        assert phase['download'].split('/')[-1] in text, f'Current artifact not identified on {page.name}'
        upper = text.upper()
        assert 'DO NOT SUBMIT' in upper and ('DOWNLOAD: YES' in upper or 'DOWNLOAD FOR RESEARCH: YES' in upper), page
    print('PASS: PHASE-88 release hashes/site links and MDPS-88 literal-duplicate safety display agree; both are explicitly negative')


if __name__ == '__main__':
    main()
