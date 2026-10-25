"""Source claims must stay claims; input readiness must not become slot clearance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_user_claims import extract, LABEL  # noqa: E402


def test_request_is_embedded_completely_and_read_at_session_start():
    request = (ROOT / 'USER_PROMPT_20261025.md').read_text()
    readme = (ROOT / 'README.md').read_text()
    embedded = readme.split('<!-- USER-REQUEST:START -->\n', 1)[1].split('\n<!-- USER-REQUEST:END -->', 1)[0]
    assert embedded == request
    assert all(name in (ROOT / 'AGENTS.md').read_text() for name in ('README.md', 'PROMPT.md', 'USER_PROMPT_20261025.md'))
    assert 'MUST GENERATE A UNIQUE TIF SUBMISSION' in request


def test_supplied_results_keep_zeros_blanks_and_duplicate_line_provenance():
    text = '''https://buffedlizard55-lab.github.io/GEMSDOE1/
a:0.0000
a:0.0000
https://buffedlizard55-lab.github.io/GEMSDOE2/
:
'''
    report = extract(text)
    assert report['site_count'] == 2
    assert report['distinct_claim_count'] == 1
    assert report['claims'][0]['user_reported_value'] == '0.0000'
    assert report['claims'][0]['request_line_numbers'] == [2, 3]
    assert report['sites_without_a_reported_result'] == ['GEMSDOE2']
    assert report['claims'][0]['organizer_receipt'] is None


def test_full_list_is_reproducible_and_not_promoted_to_receipts():
    request = (ROOT / 'USER_PROMPT_20261025.md').read_text()
    report = json.loads((ROOT / 'docs/data/user_reported_results.json').read_text())
    actual = extract(request)
    for k, v in actual.items():
        assert report[k] == v
    assert report['request_sha256'] == hashlib.sha256(request.encode()).hexdigest()
    assert report['site_count'] == 92
    assert report['distinct_claim_count'] == 118
    assert report['sites_without_a_reported_result'] == ['GEMSDOE86', 'GEMSDOE88']
    for row in report['claims']:
        assert row['evidence_class'] == LABEL
        assert row['organizer_receipt'] is None
    assert report['not_used_as_promotion_evidence'] is True


def test_prepared_input_receipt_is_not_an_official_download_or_training_approval():
    data = json.loads((ROOT / 'evidence/session_d0c3adeb_input_receipt.json').read_text())
    assert data['status'] == 'ready'
    assert data['generation_authorized'] is False
    assert data['ok_to_submit'] is False
    assert 'not authenticated organizer' in data['provenance']
    assert len(data['planes']) == 9
    assert all(all(checks.values()) for checks in data['grid_checks'].values())
    assert data['files']['training_features.tif']['sha256'] == '4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5'


def test_historical_full_catalogue_collar_is_not_hide_and_recover():
    # A synthetic regression, not a scientific experiment or reported score.
    # Withheld labels cannot influence the production eligibility mask.
    from scipy.ndimage import distance_transform_edt
    from gems57.metric import dti_bruteforce
    truth = np.zeros((11, 11), bool)
    truth[5, 5] = True
    visible = np.zeros_like(truth)
    candidate = truth.astype(float)
    proper = candidate.copy()
    proper[visible] = 0
    leaked_collar = candidate.copy()
    leaked_collar[distance_transform_edt(~truth) <= 3] = 0
    recovered = dti_bruteforce(proper, truth)
    suppressed = dti_bruteforce(leaked_collar, truth)
    # dti_bruteforce's dictionary API keeps components auditable.
    assert recovered['dti'] > suppressed['dti']


def test_claim_level_review_copies_remain_equal():
    assert (ROOT / 'research/session-d0c3adeb-review.md').read_bytes() == (ROOT / 'docs/research/session-d0c3adeb-review.md').read_bytes()
    assert (ROOT / 'research/session-d0c3adeb-hypotheses.md').read_bytes() == (ROOT / 'docs/research/session-d0c3adeb-hypotheses.md').read_bytes()
    assert (ROOT / 'knowledge/session-d0c3adeb-sources.md').read_bytes() == (ROOT / 'docs/research/session-d0c3adeb-sources.md').read_bytes()


def test_published_csv_matches_every_json_claim_without_upgrading_evidence():
    import csv
    rows = list(csv.DictReader((ROOT / 'docs/data/user_reported_results.csv').read_text().splitlines()))
    stored = json.loads((ROOT / 'docs/data/user_reported_results.json').read_text())['claims']
    assert len(rows) == len(stored)
    for row, claim in zip(rows, stored):
        for key in ('site', 'source_url', 'submission_name', 'user_reported_value', 'evidence_class'):
            assert row[key] == claim[key]
        assert row['organizer_receipt'] == ''
        assert row['request_line_numbers'] == ';'.join(map(str, claim['request_line_numbers']))


def test_current_readme_counts_match_full_download_inventory():
    text = (ROOT / 'README.md').read_text().split('<!-- USER-REQUEST:START -->', 1)[0]
    report = json.loads((ROOT / 'docs/data/download_audit.json').read_text())
    assert f"All **{report['total_published_tiff_count']}** TIFF/ZIP pairs" in text
    assert f"**{report['total_research_download_pass_count']}** pass" in text
    assert f"({report['tiff_count']} main downloads + {report['additional_research_tiff_count']} historical variant)" in text
