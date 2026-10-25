"""CON88 equal-support fix: dense priors must not make uniqueness vacuous."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from gems57.uniqueness import equal_support_dots, dot_overlap, DENSE_POSITIVE_THRESHOLD


def test_equal_support_picks_top_n():
    a = np.arange(100, dtype=float).reshape(10, 10)
    dots = equal_support_dots(a, 5)
    assert dots.sum() == 5
    assert set(a[dots].tolist()) == {95.0, 96.0, 97.0, 98.0, 99.0}


def test_dense_constant_field_no_longer_vacuous():
    rng = np.random.default_rng(0)
    dense = rng.random((200, 200))  # >0 everywhere: literal overlap would be 1.0
    cand = np.zeros((200, 200), np.float32)
    cand[::10, ::10] = 1.0
    support = equal_support_dots(dense, int((cand > 0).sum()))
    assert dot_overlap(cand, support.astype(np.float32)) < 0.70
    assert dot_overlap(cand, dense) == 1.0  # literal rule retained & reported


def test_threshold_constant():
    assert DENSE_POSITIVE_THRESHOLD == 200_000


def test_historical_equal_support_diagnostics_cannot_clear_literal_stop():
    from scripts.validate_con88 import apply_literal_gate
    out = {"G1_ok": True, "G2_equal_support_diagnostic_ok": True,
           "G3_ok": True, "canary_ok": True, "ok_to_submit": True}
    preflight = {"decision": "DUPLICATE_STOP", "preplacement_registry_proof": {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "witness_sha256": "a" * 64,
        "covered_allowed_fraction": 1.0,
        "universal_lower_bound_on_any_nonempty_candidate_overlap_3px": 1.0,
        "overlap_limit": 0.70,
        "implication": "All allowed cells are directly covered.",
    }}
    result = apply_literal_gate(out, preflight)
    assert result["literal_registry_gate"]["passes"] is False
    assert result["literal_registry_gate"]["candidate_forward_overlap_lower_bound_3px"] == 1.0
    assert result["ok_to_submit"] is False
    assert result["decision"] == "DUPLICATE_STOP"
    assert result["verdict"] == "negative"
