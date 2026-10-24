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
    # The former MAG-PSG TIFF and its mock generator were synthetic, not a
    # geological prediction. Keep this path removed so it cannot be re-linked
    # or regenerated as a competition submission.
    assert not (root / 'docs/downloads/gems88-hyp-psg-submission.tif').exists()
    assert not (root / 'scripts/build_hypothesis_psg_submission.py').exists()
    assert not (root / 'mock_data.py').exists()
    mdc_status = json.loads((root / 'docs/mdc88/status.json').read_text())
    mdc_reassessment = json.loads((root / 'registry/kdmc_literal_reassessment.json').read_text())
    assert mdc_status['ok_to_submit'] is False and mdc_status['verdict'] == 'negative'
    assert mdc_status['current_protocol'] == 'binding-literal-all-registry-v1'
    assert mdc_status['uniqueness']['literal_forward_overlap_3px'] == 1.0
    assert mdc_reassessment['ok_to_submit'] is False and mdc_reassessment['verdict'] == 'negative'
    assert mdc_reassessment['literal_uniqueness']['duplicate'] is True
    assert mdc_reassessment['historical_gate_record']['stored_ok_to_submit'] is True
    mdc_tif = root / mdc_status['candidate']['archival_file']
    mdc_zip = mdc_tif.with_suffix('.zip')
    assert mdc_tif.is_file() and mdc_zip.is_file()
    assert _hl.sha256(mdc_tif.read_bytes()).hexdigest() == mdc_reassessment['candidate']['sha256']
    assert _hl.sha256(mdc_zip.read_bytes()).hexdigest() == mdc_reassessment['candidate']['zip_sha256']
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
    for rec in sorted((root / 'registry').glob('*gate*.json')):
        try:
            data = json.loads(rec.read_text())
        except (ValueError, OSError):
            continue
        tif_name = Path((data.get('candidate') or {}).get('tif', '')).name
        literal = data.get('uniqueness_literal') or {}
        gate_v3 = data.get('gate_v3') or {}
        literal_duplicate = literal.get('duplicate') is True or gate_v3.get('unique_literal') is False
        if data.get('ok_to_submit') and tif_name and not literal_duplicate:
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
        upper = body.upper()
        assert 'DOWNLOAD FOR RESEARCH: YES' in upper, page
        assert 'OK TO SUBMIT: NO' in upper and 'FILE TO SUBMIT: NONE' in upper, page
        for false_ready_claim in (
            'OK TO SUBMIT: YES',
            'DOWNLOAD TIF FOR SUBMISSION',
            'CLICK TO DOWNLOAD FOR SUBMISSION',
            'GEMSDOE88-HYP-PSG-SUBMISSION',
            'GEMS88-HYP-PSG-SUBMISSION.TIF',
            'FORMAT-COMPLIANT MOCK SUBMISSION',
        ):
            assert false_ready_claim not in upper, f'False submit-ready claim on {page}: {false_ready_claim}'
        page_links = Links()
        page_links.feed(body)
        assert f'downloads/{kth_tif.name}' in page_links.links, f'Missing research TIFF link: {page}'
        assert f'downloads/{canonical_zip.name}' in page_links.links, f'Missing research ZIP link: {page}'
    # Include nested historical sub-sites too: a stale child page must not
    # advertise a different submit-ready candidate than the canonical feed.
    pages = [root / 'index.html', *sorted((root / 'docs').rglob('*.html'))]
    assert len(pages) >= 5
    for page in pages:
        text = page.read_text()
        if page.is_relative_to(root / 'docs'):
            upper = text.upper()
            assert 'OK TO SUBMIT: YES' not in upper, f'False submit-ready claim: {page}'
            assert 'DOWNLOAD TIF FOR SUBMISSION' not in upper, f'False submission download link: {page}'
            assert 'CLICK TO DOWNLOAD FOR SUBMISSION' not in upper, f'False submission instruction: {page}'
            assert 'GEMSDOE88-HYP-PSG-SUBMISSION' not in upper, f'Legacy mock submission claim: {page}'
            assert 'GEMS88-HYP-PSG-SUBMISSION.TIF' not in upper, f'Legacy mock download link: {page}'
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
        text = page.read_text()
        assert kth_tif.name in text, f'Current artifact not identified on {page.name}'
        upper = text.upper()
        assert 'DO NOT SUBMIT' in upper and (
            'DOWNLOAD: YES' in upper or 'DOWNLOAD FOR RESEARCH: YES' in upper
        ), page
    print('PASS: current run card, current release hashes, site links, and explicit negative decision agree')


if __name__ == '__main__':
    main()
