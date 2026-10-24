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
    # Current MDPS display must not resurrect the superseded chance-corrected PASS.
    literal = json.loads((root / 'docs/data/literal_protocol_audit.json').read_text())
    mdps = json.loads((root / 'registry/mdps88_run_card.json').read_text())
    assert literal['raster_sha256'] == mdps['raster_sha256']
    assert literal['saturation_certificate']['universal_overlap_blocker']
    assert literal['correlation_overlap_vs_registry']['literal_duplicate'] and not literal['ok_to_submit']
    assert mdps['correlation_overlap_vs_registry']['duplicate']
    assert 'FAIL — DUPLICATE' in (root / 'docs/index.html').read_text()
    # MRR, KTH, and PHASE are historical; the literal audit binds the live MDPS status.
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
    # Archived KTH must remain clearly negative even when older gate records say "promote".
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
    # The legacy PHASE current_release pointer stays internally hash-consistent,
    # but the live status and landing page must follow the latest MDPS audit.
    current_release = json.loads((root / 'docs/data/current_release.json').read_text())
    assert current_release['file'] == phase['download']
    assert current_release['file_sha256'] == phase['raster_sha256']
    assert current_release['zip_sha256'] == validation['zip_sha256']
    assert current_release['ok_to_submit'] is False and current_release['duplicate'] is True
    status = json.loads((root / 'docs/status.json').read_text())
    assert status['raster_sha256'] == literal['raster_sha256']
    assert status['ok_to_submit'] is False and status['ok_to_download_for_research'] is True
    assert status['policy'] == 'binding-literal-all-registry-v1'
    for page in (root / 'docs/index.html', root / 'docs/executive-summary.html'):
        text = (root / 'docs' / page).read_text()
        assert Path(mdps['raster']['file']).name in text, f'Latest artifact not identified on {page.name}'
        assert 'DO NOT SUBMIT' in text.upper()
    print('PASS: latest MDPS literal audit, live status, archival PHASE hashes, and site links agree')


if __name__ == '__main__':
    main()
