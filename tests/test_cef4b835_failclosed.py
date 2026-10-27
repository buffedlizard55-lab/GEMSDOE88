"""Synthetic regression tests for shared gates; never create a GEMS candidate."""
from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from vendor.gems57 import metric, uniqueness, validate  # noqa: E402
from gems88.portfolio_audit import PortfolioUniquenessAuditor  # noqa: E402


def meta(**kwargs):
    return {"my_dots": 5, "candidate_rank_variation": True,
            "candidate_file_sha256": "a" * 64,
            "candidate_decoded_sha256": "b" * 64, **kwargs}


def row(**kwargs):
    return {"submission": "synthetic-prior.tif", "sha256": "c" * 64,
            "decoded_sha256": "d" * 64, "spearman_full_footprint": 0.2,
            "my_dots_within_3px_of_theirs": 0.3, "jaccard_dot_sets": 0.1,
            "duplicate_by_rho": False, "duplicate_by_overlap": False,
            "identical_bytes": False, "identical_decoded_predictions": False, **kwargs}


def summary(rows, *, expected=None, complete=True, metadata=None, errors=None):
    return uniqueness.summarize_registry_rows(
        rows, registry_rasters_expected=len(rows) if expected is None else expected,
        complete_accessible_scan=complete, source_errors=errors or [],
        candidate_meta=metadata or meta(), scope="synthetic test only")


def assert_stopped(result):
    assert result["stop_required"] is True
    assert result["unique"] is False
    assert result["verdict"] == "negative"


def test_empty_complete_registry_is_not_unique():
    result = summary([], expected=0, complete=True)
    assert_stopped(result)
    assert result["registry_rasters_checked"] == 0
    assert result["complete_accessible_scan"] is False


@pytest.mark.parametrize("bad", [None, True, "1", 1.2])
def test_nonnumeric_registry_counts_are_rejected(bad):
    with pytest.raises(ValueError):
        summary([row()], expected=bad if bad is not None else "missing")


@pytest.mark.parametrize("bad", [False, None, "true", 1])
def test_completeness_requires_an_explicit_boolean(bad):
    assert_stopped(summary([row()], complete=bad))


def test_rows_at_both_literal_thresholds_are_not_duplicates_in_fixture():
    result = summary([row(spearman_full_footprint=-0.90,
                          my_dots_within_3px_of_theirs=0.70)])
    assert result["unique"] is True and result["stop_required"] is False
    assert result["verdict"] == "promote-to-selector-only"  # fixture, never approval


@pytest.mark.parametrize("changes", [
    {"spearman_full_footprint": 0.901},
    {"spearman_full_footprint": -0.901},
    {"my_dots_within_3px_of_theirs": 0.701},
    {"identical_bytes": True},
    {"identical_decoded_predictions": True},
    {"sha256": "a" * 64},
    {"decoded_sha256": "b" * 64},
])
def test_raw_measurements_and_digests_stop_even_when_flags_say_no(changes):
    result = summary([row(**changes)])
    assert_stopped(result)
    assert result["duplicate_count"] == 1


def test_worst_correlation_uses_absolute_magnitude_but_reports_sign():
    result = summary([row(submission="negative", spearman_full_footprint=-0.96),
                      row(submission="positive", spearman_full_footprint=0.8)])
    assert_stopped(result)
    assert result["worst_spearman_full_footprint"] == -0.96
    assert result["worst_rho_submission"] == "negative"


@pytest.mark.parametrize("key,value", [
    ("spearman_full_footprint", float("nan")),
    ("spearman_full_footprint", None),
    ("spearman_full_footprint", 1.1),
    ("my_dots_within_3px_of_theirs", float("inf")),
    ("my_dots_within_3px_of_theirs", -0.1),
    ("jaccard_dot_sets", 1.1),
    ("sha256", "not-a-sha"),
    ("decoded_sha256", None),
    ("duplicate_by_overlap", "false"),
    ("identical_bytes", 0),
])
def test_undefined_and_malformed_rows_fail_closed(key, value):
    result = summary([row(**{key: value})])
    assert_stopped(result)
    assert result["missing_or_invalid"] == 1
    assert result["validation_errors"]


@pytest.mark.parametrize("metadata", [
    meta(my_dots=0), meta(my_dots=-1), meta(my_dots=True), meta(my_dots=1.5),
    meta(candidate_rank_variation="false"), meta(candidate_decoded_sha256=None),
    meta(candidate_file_sha256="bogus"),
])
def test_missing_candidate_identity_or_support_cannot_clear(metadata):
    assert_stopped(summary([row()], metadata=metadata))


def test_source_errors_and_partial_scan_fail_closed():
    assert_stopped(summary([row()], expected=2))
    assert_stopped(summary([row()], errors=["prior not available"]))


def test_index_cannot_coerce_string_false_to_complete():
    _, complete, _ = uniqueness.records_from_index({
        "rasters": [], "complete_accessible_scan": "false", "errors": []})
    assert complete is False


def test_real_synthetic_raster_path_detects_duplicates_and_invalid_prior(tmp_path):
    fp = np.ones((12, 12), bool)
    mine = np.zeros(fp.shape, dtype="float32")
    mine[1, 1] = 1
    prior = np.zeros_like(mine)
    path = tmp_path / "prior.tif"
    profile = dict(driver="GTiff", width=12, height=12, count=1, dtype="float32",
                   crs="EPSG:32611", transform=from_origin(100, 1200, 100, 100))

    def scan(values):
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(values, 1)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        index = {"rasters": [{"repo_first": "fixture", "sources": ["prior.tif"],
                              "cache_file": str(path), "sha256": digest}],
                 "complete_accessible_scan": True, "errors": []}
        return uniqueness.compare_array_to_registry(mine, index, fp)

    prior[10, 10] = 1
    assert scan(prior)["unique"] is True
    prior[1, 1] = 1
    assert_stopped(scan(prior))
    prior[5, 5] = np.nan
    invalid = scan(prior)
    assert_stopped(invalid)
    assert "non-finite" in invalid["rows"][0]["error"]


def passing_receipt():
    return {"checks": dict.fromkeys(validate.REQUIRED_LOCAL_CHECKS, True),
            "all_checks_passed": True}


@pytest.mark.parametrize("receipt", [
    {}, {"checks": {}}, {"checks": {"single_band": True}},
    {"checks": {"single_band": 1}, "all_checks_passed": True},
    {"checks": dict.fromkeys(validate.REQUIRED_LOCAL_CHECKS, True)},
    {"checks": dict.fromkeys(validate.REQUIRED_LOCAL_CHECKS, True), "all_checks_passed": False},
])
def test_partial_validator_receipts_fail_closed(receipt):
    with pytest.raises(AssertionError):
        validate.assert_submittable(receipt)


def test_validator_requires_every_value_to_be_actual_true():
    receipt = passing_receipt()
    validate.assert_submittable(receipt)
    receipt["checks"]["single_band"] = 1
    with pytest.raises(AssertionError):
        validate.assert_submittable(receipt)
    receipt = passing_receipt()
    receipt["checks"]["outside_footprint_zero"] = False
    with pytest.raises(AssertionError):
        validate.assert_submittable(receipt)


def test_gates_stay_fail_closed_with_python_optimized():
    script = """
from vendor.gems57 import uniqueness, validate
try:
    validate.assert_submittable({'checks': {}})
except AssertionError:
    pass
else:
    raise RuntimeError('empty validator receipt was accepted')
r = uniqueness.summarize_registry_rows([], registry_rasters_expected=0,
    complete_accessible_scan=True, source_errors=[],
    candidate_meta={'my_dots': 1, 'candidate_rank_variation': True}, scope='test')
if r['unique'] or not r['stop_required']:
    raise RuntimeError('empty registry was accepted')
"""
    subprocess.run([sys.executable, "-O", "-c", script], cwd=ROOT, check=True)


def fake_fast_auditor(*, dense):
    audit = object.__new__(PortfolioUniquenessAuditor)
    audit.index_meta = {"errors": [], "repos_scanned": 1, "complete_accessible_scan": True}
    audit.rasters = [{"repo_first": "fixture", "submission": "prior.tif", "sha256": "c" * 64,
                      "positive_pixels": 16 if dense else 1}]
    # 16 active cells. Dense halo covers them all; sparse halo covers none.
    audit.halos_packed = np.packbits(np.ones((1, 16), np.uint8) if dense else np.zeros((1, 16), np.uint8), axis=1)
    audit.unit_ranks = np.zeros((1, 16), dtype=np.float32)
    audit.is_const = np.zeros(1, dtype=bool)
    audit.sub_idx = np.arange(16)
    audit.n_rasters = 1
    audit.is_discriminating = np.array([not dense])
    return audit


@pytest.mark.parametrize("method", ["audit_surface", "audit_dots"])
def test_fast_screen_never_exempts_dense_prior_or_grants_clearance(method):
    footprint = np.ones((4, 4), bool)
    data = np.arange(16, dtype=np.float32).reshape(4, 4) / 15
    result = getattr(fake_fast_auditor(dense=True), method)(data, footprint, footprint, "fixture")
    assert result["worst_raw_overlap_including_spacefill"] == 1.0
    assert result["duplicate_by_overlap_count"] == 1
    assert result["decision"] == "DUPLICATE_STOP"
    assert result["passed"] is False and result["stop_required"] is True
    # Even a passing *sample* cannot replace the complete full-resolution gate.
    result = getattr(fake_fast_auditor(dense=False), method)(data, footprint, footprint, "fixture")
    assert result["screening_passed"] is True
    assert result["decision"] == "FULL_CHECK_REQUIRED"
    assert result["passed"] is False and result["stop_required"] is True


def test_one_dot_can_cover_multiple_truth_cells():
    truth = np.zeros((7, 7), bool)
    truth[3, 1:6] = True
    dots = np.zeros_like(truth)
    dots[3, 3] = True
    fast = metric.dti_binary(dots, truth)
    slow = metric.dti_bruteforce(dots.astype(float), truth)
    assert fast["tp"] == pytest.approx(3.0)
    assert fast["tp"] > 1.0  # self-credit k=1, but marginal TP is 3
    assert fast["dti"] == pytest.approx(slow["dti"])


def test_metric_change_is_documentation_only():
    class RemoveDocstrings(ast.NodeTransformer):
        def visit_body(self, node):
            self.generic_visit(node)
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:]
            return node
        visit_Module = visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_body

    tree = ast.parse((ROOT / 'vendor/gems57/metric.py').read_text())
    normalized = ast.dump(RemoveDocstrings().visit(tree), include_attributes=False)
    assert hashlib.sha256(normalized.encode()).hexdigest() == (
        'a9848255d8e1ea05ca071603b9be641d51a921fde6120dd0b5970ff8dd27ef2f')
