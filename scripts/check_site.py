"""Audit local site links, the visible submit decision, and the one-click download placement.

This is a site guard, not the scientific/format gate; ``validate_release.py`` is canonical.
Rules (all machine-checked, no human input):

* every local link resolves; every TIFF/ZIP link lives under ``docs/downloads``;
* a published TIFF/ZIP whose gate verdict is not "ok to submit" must carry ``DO-NOT-SUBMIT`` in its
  file name (earlier research files too); the one gated file may carry ``GATE-PASS`` only when
  ``registry/gate_verdict.json`` says ``ok_to_submit``;
* ``docs/index.html`` and ``docs/executive-summary.html`` show the exact verdict label from
  ``registry/gate_verdict.json`` and link the headline TIFF within the first part of ``<main>``;
* ``README.md`` shows the label and the headline download link in its first 4,000 characters;
* the PROVCREST file merged from PR #53 predates gate v3 and carries no ``DO-NOT-SUBMIT`` marker.  It may be linked
  unmarked only while ``registry/provcrest_run_card.json`` still binds to the on-disk bytes AND every page that links it
  also shows the tag ``v3: NOT OK TO SUBMIT`` (when ``registry/provcrest_gate_v3.json`` says ``ok_to_submit`` is false).
"""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TOP_WINDOW = 9000  # characters after <main> within which the headline TIFF links must appear
PROV_TAG = 'v3: NOT OK TO SUBMIT'  # must sit on every page that links the PROVCREST file while gate v3 blocks it


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in ('href', 'src') and value)


def main(root=ROOT):
    # archived Exp 1-3 record (H88-ADHR) must keep telling the truth
    card = json.loads((root / 'registry/run_card.json').read_text())
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert len(card['submission_note']) <= 140
    gv = json.loads((root / 'registry/gate_verdict.json').read_text())
    name, label, ok_submit = gv['name'], gv['label'], bool(gv['ok_to_submit'])
    assert label in ('OK TO DOWNLOAD - OK TO SUBMIT', 'OK TO DOWNLOAD - NOT OK TO SUBMIT', 'NOT OK TO DOWNLOAD OR SUBMIT')
    head_tif = f'downloads/{name}.tif'
    assert (root / 'docs' / head_tif).is_file(), 'headline TIFF missing'
    assert name.endswith('GATE-PASS' if ok_submit else 'DO-NOT-SUBMIT'), 'file name does not encode the verdict'
    # PROVCREST (PR #53): bytes must still match its own run card, and gate v3 must have a verdict record for them
    import hashlib
    prov = json.loads((root / 'registry' / 'provcrest_run_card.json').read_text())
    pgate = json.loads((root / 'registry' / 'provcrest_gate_v3.json').read_text())
    prov_tif = (root / prov['submission']['file']).resolve()
    prov_zip = (root / prov['submission']['zip_file']).resolve()
    assert prov_tif.is_file() and hashlib.sha256(prov_tif.read_bytes()).hexdigest() == prov['submission']['sha256'], 'PROVCREST bytes differ from its run card'
    assert pgate['sha256'] == prov['submission']['sha256'] and pgate['policy'] == 'gems88-gate-v3', 'PROVCREST has no v3 verdict for these bytes'
    prov_head = 'downloads/' + prov_tif.name
    assert len(prov['submission']['submission_note']) <= 140
    pages = [root / 'index.html', *sorted((root / 'docs').glob('*.html'))]
    assert len(pages) >= 5
    for page in pages:
        text = page.read_text()
        if page.name in ('index.html', 'executive-summary.html') and page.parent.name == 'docs':
            assert ('GATE PASS' if ok_submit else 'DO NOT SUBMIT') in text, f'Missing decision banner: {page}'
            assert label.replace('-', '&ndash;') in text or label in text, f'Missing verdict label {label!r}: {page}'
            i = text.find('<main')
            assert i >= 0 and head_tif in text[i:i + TOP_WINDOW], f'Headline TIFF link not at the top of {page.name}'
            assert prov_head in text[i:i + TOP_WINDOW], f'PROVCREST TIFF link not at the top of {page.name}'
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
                if path.name.startswith(name):
                    continue  # the gated headline file: its suffix was checked above
                if path in (prov_tif, prov_zip):
                    if not pgate['ok_to_submit']:
                        assert PROV_TAG in text, f'{page.name} links PROVCREST without the tag {PROV_TAG!r}'
                    continue
                assert 'DO-NOT-SUBMIT' in path.name, f'Unmarked research download: {link}'
    readme = (root / 'README.md').read_text()
    top = readme[:4000]
    assert f'docs/downloads/{name}.tif' in top, 'README top lacks the one-click TIFF link'
    assert f'docs/downloads/{prov_tif.name}' in top, 'README top lacks the PROVCREST TIFF link'
    if not pgate['ok_to_submit']:
        assert pgate['label'] in top, 'README top lacks the PROVCREST v3 label'
    assert label in top, 'README top lacks the verdict label'
    print(f'PASS: site links, verdicts {label!r} / PROVCREST {pgate["label"]!r}, both TIFFs at the top of site/README, marked research downloads')


if __name__ == '__main__':
    main()
