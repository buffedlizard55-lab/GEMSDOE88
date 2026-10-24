"""Audit local site links and forbid unlabeled research TIFF/ZIP downloads.

This is a site guard, not the scientific/format gate. The landing page's latest
experiment is MDPS-88; ``current_release.json`` is a separately retained PHASE-88
archive record and must not be mistaken for the latest site decision. A blocked
experiment may publish a clearly marked research-only file for independent audit.
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
    # MRR, KTH, and PHASE are archived historical records; latest MDPS-88 is checked below.
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
    # Archived KTH artifact remains blocked and correctly labelled; it must not
    # be confused with the latest MDPS experiment checked later below.
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
    # The landing page's latest experiment is MDPS-88. The separate
    # current_release.json remains a historical PHASE-88 record; assert that
    # distinction explicitly so an archival pointer cannot silently replace the
    # latest experiment or its download decision.
    mdps = json.loads((root / 'registry/mdps88_run_card.json').read_text())
    mdps_validation = json.loads((root / 'docs/data/mdps88_validation.json').read_text())
    mdps_gate = json.loads((root / 'docs/data/mdps88-gate.json').read_text())
    mdps_tif = root / mdps['raster']['file']
    mdps_zip = root / mdps['raster']['zip']
    assert mdps['verdict'] == 'negative' and mdps['ok_to_download'] is True
    assert mdps['ok_to_submit'] is False and mdps['approved_for_weekly_slot'] is False
    assert mdps_gate['ok_to_download'] is True and mdps_gate['ok_to_submit'] is False
    assert mdps_validation['audit_passed'] is True and mdps_validation['ok_to_submit'] is False
    assert mdps_validation['sha256'] == mdps['raster']['sha256']
    assert mdps_validation['checks']['range_0_1'] is True
    assert mdps_validation['checks']['all_finite'] is True
    assert mdps_validation['checks']['grid_matches_sample'] is True
    assert mdps_validation['checks']['zip_member_bytes_identical'] is True
    assert mdps_tif.is_file() and mdps_zip.is_file()
    assert mdps_tif.name.endswith('DO-NOT-SUBMIT.tif')
    assert _hl.sha256(mdps_tif.read_bytes()).hexdigest() == mdps['raster']['sha256']
    assert _hl.sha256(mdps_zip.read_bytes()).hexdigest() == mdps['raster']['zip_sha256']
    assert len(mdps['submission_name']) <= 140 and len(mdps['submission_note']) <= 140
    assert mdps['submission_note'].endswith('DO NOT SUBMIT')
    assert mdps['holdout']['evidence_class'] == 'HOLDOUT-DTI'
    assert mdps['holdout']['evaluator_version'] == 'gems57-pooled-hide-v2'
    assert mdps['holdout']['far']['withheld_positive_pixels'] > 0
    assert mdps['holdout']['far']['ci95'][0] <= mdps['holdout']['far']['dti'] <= mdps['holdout']['far']['ci95'][1]
    assert mdps['holdout']['far']['paired_vs_base283']['ci95'][0] <= 0
    assert mdps['holdout']['far']['paired_vs_base283']['ci95'][1] >= 0
    assert mdps['correlation_overlap_vs_registry']['surface_preplacement_worst_abs_spearman'] <= .90
    assert mdps['correlation_overlap_vs_registry']['worst_excess_overlap_3px'] <= .70
    assert mdps['correlation_overlap_vs_registry']['worst_literal_forward_overlap_3px'] == 1.0
    assert mdps['correlation_overlap_vs_registry']['literal_duplicate_under_prompt'] is True
    assert mdps['gates']['strict_literal_uniqueness_pass'] is False
    assert any('literal lane rule fails' in reason for reason in mdps_gate['blocking_reasons'])
    # Keep PHASE-88's own frozen current-release record intact, but never call it
    # the latest experiment. Its historical status does not authorize a slot.
    current = json.loads((root / 'docs/data/current_release.json').read_text())
    phase_audit = json.loads((root / 'docs/data/phase88_validation.json').read_text())
    assert current['file'] == phase['download']
    assert current['file_sha256'] == phase['raster_sha256']
    assert current['zip_sha256'] == phase_audit['zip_sha256']
    assert current['ok_to_submit'] is False and current['duplicate'] is True
    assert phase['raster_sha256'] != mdps['raster']['sha256']
    for page in (root / 'docs/index.html', root / 'docs/executive-summary.html'):
        text = page.read_text()
        assert mdps_tif.name in text, f'Latest experiment is not identified on {page.name}'
        upper = text.upper()
        assert 'DO NOT SUBMIT' in upper and ('DOWNLOAD: YES' in upper or 'DOWNLOAD FOR RESEARCH: YES' in upper), page
        assert 'data/mdps88_validation.json' in text, f'Automated audit link missing on {page.name}'
    script = (root / 'docs/assets/site.js').read_text()
    assert "data/mdps88_validation.json" in script and 'data.ok_to_submit === false' in script
    print('PASS: latest MDPS-88 run card, byte audit, download verdict, archival PHASE-88 record, and site links agree')


if __name__ == '__main__':
    main()
