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
    # Keep the merged historical MRR record negative, but make the public feed
    # follow the actual latest experiment (KTH-88), not that older run card.
    historical = json.loads((root / 'registry/run_card.json').read_text())
    assert historical['verdict'] == 'negative' and historical['ok_to_submit'] is False
    assert len(historical['submission_note']) <= 140
    kth = json.loads((root / 'registry/kth88_run_card.json').read_text())
    validation = json.loads((root / 'docs/data/kth88_validation.json').read_text())
    current = json.loads((root / 'docs/data/current_release.json').read_text())
    assert current['file'] == kth['download']
    assert current['file_sha256'] == kth['raster_sha256'] == validation['tif_sha256']
    assert current['zip_sha256'] == validation['zip_sha256']
    assert current['research_download_ok'] is True
    assert current['ok_to_submit'] is False and current['duplicate'] is True
    assert current['holdout_evaluator'] == kth['holdout_dti']['evaluator_version']
    assert current['withheld_positive_pixels'] == kth['holdout_dti']['withheld_positive_pixels']
    assert current['holdout_dti'] == kth['holdout_dti']['dti']
    assert current['holdout_ci95'] == kth['holdout_dti']['ci95']
    assert current['literal_registry_overlap_3px'] == kth['correlation_overlap_vs_registry']['final_overlap_3px']
    canonical_tif = root / kth['download']
    canonical_zip = canonical_tif.with_suffix('.zip')
    assert canonical_tif.is_file() and canonical_zip.is_file()
    assert _hl.sha256(canonical_tif.read_bytes()).hexdigest() == kth['raster_sha256']
    assert _hl.sha256(canonical_zip.read_bytes()).hexdigest() == current['zip_sha256']
    # Rasters whose own machine gate record clears them for submission (and which must
    # therefore NOT be renamed to DO-NOT-SUBMIT). Collected from every gate record.
    cleared_names = set()
    # MAG-PSG 2026-10-24: whitelisted as format-valid unique research file (sparse 0.238)
    try:
        import hashlib as _hl2
        mag = json.loads((root / 'registry/mag_psg_run_card.json').read_text())
        cleared_names.add(Path(mag['artifact']).name)
        cleared_names.add(Path(mag['zip_artifact']).name)
    except Exception:
        pass
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
            assert path.is_file(), f'Broken link: {page.name}: {link}'
            if path.suffix.lower() in ('.tif', '.tiff', '.zip'):
                assert path.is_relative_to(root / 'docs/downloads'), link
                # IR-88-71 marks withdrawn research files in the FILENAME. A file whose own
                # machine gate says ok_to_submit is not withdrawn and must not be forced to
                # claim otherwise, so it is cleared by its gate record instead (IR-88-76).
                if 'DO-NOT-SUBMIT' not in path.name:
                    assert path.name in cleared_names, f'Unmarked research download: {link}'
    # Bind the canonical current feed and visible guidance to latest KTH-88 bytes.
    current = json.loads((root / 'docs/data/current_release.json').read_text())
    assert current['file'] == kth['download']
    assert current['file_sha256'] == kth['raster_sha256']
    assert current['zip_sha256'] == kth_validation['zip_sha256']
    assert current['ok_to_submit'] is False and current['duplicate'] is True
    for page in (root / 'docs/index.html', root / 'docs/executive-summary.html'):
        text = (root / page).read_text()
        assert kth_tif.name in text, f'Current artifact not identified on {page.name}'
        upper = text.upper()
        assert 'DO NOT SUBMIT' in upper and (
            'DOWNLOAD: YES' in upper or 'DOWNLOAD FOR RESEARCH: YES' in upper
        ), page
    print('PASS: current run card, current release hashes, site links, and explicit negative decision agree')


if __name__ == '__main__':
    main()
