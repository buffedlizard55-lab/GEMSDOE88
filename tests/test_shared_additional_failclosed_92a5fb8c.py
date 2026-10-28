"""Additional shared/diagnostic fail-closed regressions.

The validator, sampled-portfolio and metric-prose issues were independently
reported in open PR #214 (cef4b835), whose targeted fixes were incorporated
with attribution. These synthetic arrays are fixtures, not predictions.
"""
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from gems57 import metric, uniqueness, validate
from gems88.portfolio_audit import PortfolioUniquenessAuditor

ROOT = Path(__file__).resolve().parents[1]


def meta(**overrides):
    return {'my_dots': 5, 'candidate_rank_variation': True,
            'candidate_file_sha256': 'a' * 64, 'candidate_decoded_sha256': 'b' * 64, **overrides}


def row(**overrides):
    return {'submission': 'synthetic-prior.tif', 'sha256': 'c' * 64, 'decoded_sha256': 'd' * 64,
            'spearman_full_footprint': 0.2, 'my_dots_within_3px_of_theirs': 0.3,
            'jaccard_dot_sets': 0.1, 'duplicate_by_rho': False, 'duplicate_by_overlap': False,
            'identical_bytes': False, 'identical_decoded_predictions': False, **overrides}


def summary(rows, metadata=None):
    return uniqueness.summarize_registry_rows(rows, registry_rasters_expected=len(rows),
        complete_accessible_scan=True, source_errors=[], candidate_meta=metadata or meta(), scope='synthetic')


@pytest.mark.parametrize('change', [{'sha256': 'a' * 64}, {'decoded_sha256': 'b' * 64},
                                    {'sha256': 'bad'}, {'decoded_sha256': None}])
def test_hash_identity_or_malformed_prior_never_clears(change):
    result = summary([row(**change)])
    assert not result['unique'] and result['stop_required']


@pytest.mark.parametrize('change', [{'candidate_decoded_sha256': None}, {'candidate_file_sha256': 'bad'}])
def test_missing_candidate_identity_never_clears(change):
    assert not summary([row()], meta(**change))['unique']


def test_index_requires_explicit_boolean_completeness():
    _, complete, _ = uniqueness.records_from_index({'rasters': [], 'complete_accessible_scan': 'false', 'errors': []})
    assert complete is False


@pytest.mark.parametrize('receipt', [{}, {'checks': {}}, {'checks': {'single_band': True}},
    {'checks': dict.fromkeys(validate.REQUIRED_LOCAL_CHECKS, True)},
    {'checks': dict.fromkeys(validate.REQUIRED_LOCAL_CHECKS, True), 'all_checks_passed': False}])
def test_incomplete_local_validator_receipt_rejected(receipt):
    with pytest.raises(AssertionError):
        validate.assert_submittable(receipt)


def test_local_validator_requires_all_checks_and_actual_booleans():
    receipt = {'checks': dict.fromkeys(validate.REQUIRED_LOCAL_CHECKS, True), 'all_checks_passed': True}
    validate.assert_submittable(receipt)
    receipt['checks']['single_band'] = 1
    with pytest.raises(AssertionError):
        validate.assert_submittable(receipt)


def fake_auditor(dense):
    audit = object.__new__(PortfolioUniquenessAuditor)
    audit.index_meta = {'errors': [], 'repos_scanned': 1, 'complete_accessible_scan': True}
    audit.rasters = [{'repo_first': 'fixture', 'submission': 'prior.tif', 'sha256': 'c' * 64,
                      'positive_pixels': 16 if dense else 1}]
    audit.halos_packed = np.packbits(np.ones((1, 16), np.uint8) if dense else np.zeros((1, 16), np.uint8), axis=1)
    audit.unit_ranks = np.zeros((1, 16), dtype=np.float32)
    audit.is_const = np.zeros(1, dtype=bool)
    audit.sub_idx = np.arange(16)
    audit.n_rasters = 1
    audit.is_discriminating = np.array([not dense])
    return audit


@pytest.mark.parametrize('method', ['audit_surface', 'audit_dots'])
def test_sampled_portfolio_includes_dense_and_never_grants_clearance(method):
    footprint = np.ones((4, 4), bool)
    values = np.arange(16, dtype=np.float32).reshape(4, 4) / 15
    dense = getattr(fake_auditor(True), method)(values, footprint, footprint, 'fixture')
    assert dense['worst_raw_overlap_including_spacefill'] == 1.0
    assert dense['decision'] == 'DUPLICATE_STOP' and dense['passed'] is False
    sparse = getattr(fake_auditor(False), method)(values, footprint, footprint, 'fixture')
    assert sparse['screening_passed'] is True and sparse['decision'] == 'FULL_CHECK_REQUIRED'
    assert sparse['passed'] is False and sparse['stop_required'] is True


def test_one_dot_can_cover_several_truth_cells():
    truth = np.zeros((7, 7), bool)
    truth[3, 1:6] = True
    dots = np.zeros_like(truth)
    dots[3, 3] = True
    components = metric.dti_binary(dots, truth)
    # For this fixture a single prediction's self-credit is 1, while it
    # contributes positive weighted credit to several distinct truth pixels.
    assert components['tp'] > 1.0


def test_empty_validator_receipt_rejected_in_optimized_python():
    script = "from vendor.gems57 import validate\ntry: validate.assert_submittable({'checks': {}})\nexcept AssertionError: pass\nelse: raise RuntimeError('accepted empty receipt')"
    subprocess.run([sys.executable, '-O', '-c', script], cwd=ROOT, check=True)
