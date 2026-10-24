"""Regression tests for the binding literal rule, not a new geological experiment."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pytest
from scripts.audit_literal_protocol import coverage_proof
from gems57 import uniqueness


def test_coverage_proof_is_sufficient_not_a_uniqueness_certificate():
    fp = np.ones((5, 5), bool)
    dense = np.full(fp.shape, .001)
    assert coverage_proof(fp, dense)['all_nonempty_in_footprint_candidates_blocked']
    dense[2, 2] = 0
    assert not coverage_proof(fp, dense)['all_nonempty_in_footprint_candidates_blocked']
    with pytest.raises(ValueError):
        coverage_proof(np.zeros((5, 5), bool), dense)


@pytest.mark.parametrize('rows', [[], [{'error': 'missing file'}],
    [{'spearman': None, 'forward_overlap': .2}],
    [{'spearman': .2, 'forward_overlap': float('nan')}],
    [{'spearman': float('nan'), 'forward_overlap': .2}]])
def test_incomplete_or_nonfinite_measurements_stop(rows):
    decision = uniqueness.binding_duplicate_decision_v3(rows)
    assert decision['stop_required'] and decision['verdict'] == 'negative'


def test_dense_witness_is_binding_even_with_zero_excess():
    d = uniqueness.binding_duplicate_decision_v3([
        {'file': 'dense', 'spearman': .01, 'forward_overlap': 1., 'halo_coverage': 1.}])
    assert d['duplicate'] and d['stop_required']


def test_chance_correction_cannot_rescue_literal_duplicate():
    d = uniqueness.binding_duplicate_decision_v3([
        {'file': 'sparse', 'spearman': .01, 'forward_overlap': .8, 'halo_coverage': .7}])
    assert d['worst_excess_overlap'] < .70
    assert d['duplicate']


def test_exact_thresholds_pass_measurement_gate_only():
    d = uniqueness.binding_duplicate_decision_v3([
        {'spearman': .90, 'forward_overlap': .70, 'halo_coverage': .1}])
    assert not d['stop_required']  # caller must separately prove registry completeness
