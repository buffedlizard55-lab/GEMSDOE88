"""The literal lane rule must not silently exempt dense registry priors."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_mdps88_submission import strict_literal_overlap_pass  # noqa: E402


def test_literal_overlap_gate_blocks_positive_everywhere_witness():
    # A dense full-footprint prior returns 1.0 for every non-empty prediction.
    assert not strict_literal_overlap_pass({"worst_literal_forward_overlap": 1.0})


def test_literal_overlap_gate_uses_inclusive_seventy_percent_limit():
    assert strict_literal_overlap_pass({"worst_literal_forward_overlap": 0.70})
    assert not strict_literal_overlap_pass({"worst_literal_forward_overlap": 0.700001})


def test_literal_overlap_gate_fails_closed_on_missing_or_invalid_measurement():
    assert not strict_literal_overlap_pass({})
    assert not strict_literal_overlap_pass({"worst_literal_forward_overlap": float("nan")})
    assert not strict_literal_overlap_pass({"worst_literal_forward_overlap": -0.1})
