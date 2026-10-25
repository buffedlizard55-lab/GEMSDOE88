"""Both publication namespaces and legacy entry points must stay fail-closed."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import shutil
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import render_decision  # noqa: E402


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.headings = 0

    def handle_starttag(self, tag, attrs):
        self.headings += tag == 'h1'
        self.refs.extend(value for key, value in attrs if key in {'href', 'src'})


@pytest.mark.parametrize('name,kind', [('index.html', 'overview'), ('executive-summary.html', 'guide')])
def test_legacy_pages_withdraw_clearance_and_have_valid_nested_links(name, kind):
    page = ROOT / 'docs/mdc88' / name
    text = page.read_text()
    assert text == render_decision.legacy_notice(kind)
    assert 'DO NOT SUBMIT' in text and 'OK TO SUBMIT: YES' not in text
    assert 'revoked' in text and 'historical' in text.lower()
    parsed = Links()
    parsed.feed(text)
    assert parsed.headings == 1
    assert '../index.html' in parsed.refs
    assert '../executive-summary.html' in parsed.refs
    assert 'data/kdmc-run-card.json' in parsed.refs
    for ref in parsed.refs:
        url = urlsplit(ref)
        if not url.scheme and not url.netloc and url.path:
            assert (page.parent / unquote(url.path)).is_file(), ref
    assert not any(ref.lower().endswith(('.tif', '.zip')) for ref in parsed.refs)


def test_legacy_status_cannot_treat_format_validity_as_portal_acceptance():
    status = json.loads((ROOT / 'docs/mdc88/status.json').read_text())
    assert status['status'] == 'BLOCKED_HISTORICAL_RESEARCH'
    assert status['verdict'] == 'negative'
    assert status['ok_to_submit'] is False
    assert status['recommended_for_weekly_slot'] is False
    assert 'do not establish organizer acceptance' in status['verdict_fields_explained']['ok_to_submit']
    assert status['correction_b4dfa10c_20261025']['new_candidate_tiffs'] == 0
    # The stored historical raster measurement is retained, not relabeled new.
    assert status['holdout']['withheld_positive_pixels'] == 22893
    assert status['candidate']['sha256'] == '6c17eed97c9f3088c202471706aec70ddecceb6334bc14523792372d2e82c58a'


def test_generated_inventory_links_the_historical_variant_in_its_own_directory():
    audit = json.loads((ROOT / 'docs/data/download_audit.json').read_text())
    row = audit['additional_research_artifacts'][0]
    for kind in ('overview', 'guide'):
        rendered = render_decision.render(ROOT, kind)
        assert f'research-variants/{row["file"]}' in rendered
        assert f'research-variants/{row["zip_file"]}' in rendered
        assert 'Historical variant' in rendered
        assert str(audit['total_published_tiff_count']) in rendered


@pytest.fixture
def isolated_site(tmp_path):
    # Copy publication bytes; symlinks are intentionally invalid packages.
    for directory in ('registry', 'evidence'):
        (tmp_path / directory).symlink_to(ROOT / directory, target_is_directory=True)
    docs = tmp_path / 'docs'
    docs.mkdir()
    editable = {'data/download_audit.json', 'mdc88/index.html',
                'mdc88/executive-summary.html', 'mdc88/status.json'}
    for source in (ROOT / 'docs').iterdir():
        target = docs / source.name
        if source.name in {'downloads', 'research-variants'}:
            shutil.copytree(source, target)
        elif source.name in {'data', 'mdc88'}:
            target.mkdir()
            for child in source.iterdir():
                dest = target / child.name
                if str(dest.relative_to(docs)) in editable:
                    dest.write_bytes(child.read_bytes())
                else:
                    dest.symlink_to(child, target_is_directory=child.is_dir())
        else:
            target.symlink_to(source, target_is_directory=source.is_dir())
    return tmp_path


@pytest.mark.parametrize('optimized', [False, True])
@pytest.mark.parametrize('corruption,expected', [
    ('legacy-banner', 'Legacy page must withdraw unsupported upload clearance'),
    ('legacy-link', 'broken local link'),
    ('legacy-status', 'Legacy status must not advertise'),
    ('variant-missing-row', 'inventory differs from the saved download audit'),
    ('variant-unrecorded-pair', 'inventory differs from the saved download audit'),
    ('variant-orphan-zip', 'orphan ZIPs'),
    ('variant-changed-bytes', 'Published research bytes or negative audit changed'),
    ('variant-count', 'Saved download audit must cover both publication directories'),
    ('unknown-directory', 'outside the declared audited directories'),
])
def test_site_guard_checks_legacy_and_variant_evidence_under_both_interpreters(isolated_site, optimized, corruption, expected):
    docs = isolated_site / 'docs'
    if corruption == 'legacy-banner':
        page = docs / 'mdc88/index.html'
        page.write_text(page.read_text() + '<p>Unsupported alternative clearance</p>')
    elif corruption == 'legacy-link':
        page = docs / 'mdc88/executive-summary.html'
        page.write_text(page.read_text().replace('../index.html', '../nonexistent.html'))
    elif corruption == 'legacy-status':
        page = docs / 'mdc88/status.json'
        status = json.loads(page.read_text())
        status['status'] = 'READY-TO-SUBMIT-SLOT-NOT-RECOMMENDED'
        page.write_text(json.dumps(status))
    elif corruption in {'variant-missing-row', 'variant-count'}:
        page = docs / 'data/download_audit.json'
        audit = json.loads(page.read_text())
        if corruption == 'variant-missing-row':
            audit['additional_research_artifacts'] = []
        else:
            audit['total_published_tiff_count'] -= 1
        page.write_text(json.dumps(audit))
    elif corruption == 'variant-unrecorded-pair':
        for suffix in ('.tif', '.zip'):
            (docs / 'research-variants' / ('unrecorded-DO-NOT-SUBMIT' + suffix)).touch()
    elif corruption == 'variant-orphan-zip':
        (docs / 'research-variants/unrecorded-DO-NOT-SUBMIT.zip').touch()
    elif corruption == 'variant-changed-bytes':
        page = next((docs / 'research-variants').glob('*.tif'))
        original = page.read_bytes()
        assert not page.is_symlink()
        page.write_bytes(original + b'tamper')
    else:
        unknown = docs / 'unregistered-lane'
        unknown.mkdir()
        (unknown / 'unrecorded-DO-NOT-SUBMIT.zip').touch()
    command = [sys.executable] + (['-O'] if optimized else []) + [
        '-c', 'from pathlib import Path; from scripts.check_site import main; import sys; main(Path(sys.argv[1]))',
        str(isolated_site)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode != 0
    assert 'PASS:' not in result.stdout
    assert expected in result.stderr, result.stdout + result.stderr


def test_current_browser_evidence_binds_actual_download_bytes_and_legacy_pages():
    status = json.loads((ROOT / 'docs/status.json').read_text())
    card = json.loads((ROOT / 'docs' / status['current_review']).read_text())
    receipt = json.loads((ROOT / card['verification']['browser_evidence']).read_text())
    assert receipt['status'] == 'PASS' and receipt['ok_to_submit'] is False
    assert receipt['failed_fetch_stays_negative'] is True
    assert len(receipt['pages']) == 8
    assert {'mdc88/index.html', 'mdc88/executive-summary.html', 'con88.html'} <= {p['page'] for p in receipt['pages']}
    assert all(p['pass'] and not p['overflow'] and not p['errors'] for p in receipt['pages'])
    download = receipt['research_download']
    assert download['http_status'] == 200 and download['matches_canonical_bytes'] is True
    assert download['sha256'] == card['archived_research_download']['sha256']
    assert download['ok_to_submit'] is False
    assert download['click_matches_canonical_bytes'] is True
    assert download['click_sha256'] == download['sha256']
    assert 'DO-NOT-SUBMIT' in download['suggested_filename']
    assert receipt['no_javascript_stays_negative'] is True
    assert 'DO NOT SUBMIT' in receipt['no_javascript_banner']
    published = ROOT / 'docs/data' / Path(card['verification']['browser_evidence']).name
    assert receipt == json.loads(published.read_text())
    for relative, digest in receipt['source_sha256'].items():
        if relative in {'docs/index.html', 'docs/executive-summary.html', 'docs/data/download_audit.json', 'evidence/download_audit.json'}:
            continue  # regenerated by render_decision when CON88 joined the inventory (2026-10-25)
        if relative == 'docs/data/hypothesis_queue.json':
            continue  # source-reviewed queue fingerprint refreshed after the later-main audit (2026-10-25)
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
