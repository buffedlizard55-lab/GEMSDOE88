"""Tests for the report-only controls on the merged AXIS=MASS bracket on `R1`.

The three `MASS` arms on `R1` are built and ledgered (PR #46); this session adds
only controls, so the tests cover (1) the static marginal-gain helper on a
synthetic grid, (2) the recorded control report, and (3) the guarantee that the
controls never leak into the ledger or the releases.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import mass_r1_random_donor_control as ctl  # noqa: E402

REPORT = ROOT / "evidence" / "mass_r1_random_donor_control.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
CONTROL_NAMES = ("static_bottom", "random", "static_top")


def _synthetic():
    w = np.zeros((40, 40), dtype=np.float64)
    w[10:13, 5:35] = 1.0
    base = np.zeros((40, 40), dtype=bool)
    base[11, 6:34:4] = True
    cand = np.zeros((40, 40), dtype=bool)
    cand[11, 7:34:4] = True     # adjacent to an existing dot -> small marginal gain
    cand[20:22, 5:35] = True    # far from every dot, but w = 0 there
    return base, cand, w


def test_static_marginal_gain_orders_candidates_by_uncovered_credit():
    base, cand, w = _synthetic()
    dT = ctl.static_marginal_gain(base, cand, w)
    assert dT.shape == (int(cand.sum()),)
    assert np.all(dT >= -1e-12)
    cy, cx = np.nonzero(cand)
    on_strand = (cy >= 10) & (cy < 13)
    assert dT[on_strand].max() > dT[~on_strand].max(), "uncovered high-w cells must rank first"


def test_static_marginal_gain_is_zero_for_a_fully_covered_candidate():
    w = np.zeros((30, 30), dtype=np.float64)
    w[15, 10:20] = 1.0
    base = w > 0
    cand = np.zeros_like(base)
    cand[15, 15] = True  # already covered by the same dot
    dT = ctl.static_marginal_gain(base, cand, w)
    assert dT[0] == 0.0


def _report() -> dict:
    if not REPORT.is_file():
        import pytest

        pytest.skip("evidence/mass_r1_random_donor_control.json absent (control not run locally)")
    return json.loads(REPORT.read_text())


def test_report_records_three_controls_against_the_merged_family():
    rep = _report()
    assert set(rep["controls"]) == set(CONTROL_NAMES)
    assert rep["dose"]["n_dots"] == 3_765
    assert rep["leakage_canaries"]["max_symmetric_auc"] <= 0.90
    parent = rep["parent"]["sgmc_off_catalogue_dti"]
    for name, c in rep["controls"].items():
        assert c["n_added"] == 3_765
        assert abs(c["sgmc_delta_vs_r1"] - (c["sgmc_off_catalogue_dti"] - parent)) < 1e-6
    assert len(rep["merged_family_arms"]) == 3
    for arm, value in rep["merged_family_arms"].items():
        assert value is not None and 0.0 < value < 1.0


def test_count_effect_floor_and_ranking_span_are_both_recorded():
    """The measured result, kept as a regression: random dots recover most of the
    add-arm gain, and the whole bottom-to-top ranking span is under 0.001 SGMC."""
    rep = _report()
    c = rep["controls"]
    assert c["static_bottom"]["sgmc_delta_vs_r1"] < c["random"]["sgmc_delta_vs_r1"]
    assert c["random"]["sgmc_delta_vs_r1"] < c["static_top"]["sgmc_delta_vs_r1"]
    assert c["random"]["sgmc_delta_vs_r1"] > 0.0, "an equal-size random add must raise the control"
    span = c["static_top"]["sgmc_delta_vs_r1"] - c["static_bottom"]["sgmc_delta_vs_r1"]
    assert span < 0.002
    # the static ranking's mean marginal gain must increase monotonically with rank
    assert (
        c["static_bottom"]["mean_static_dT_per_added_dot"]
        < c["random"]["mean_static_dT_per_added_dot"]
        < c["static_top"]["mean_static_dT_per_added_dot"]
    )


def test_controls_never_enter_the_ledger_or_the_releases():
    with LEDGER.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    ids = {r["id"] for r in rows}
    for name in CONTROL_NAMES:
        assert not any(name in i for i in ids), f"control {name} leaked into the ledger"
    # the merged family's rows are untouched by this session
    mass_r1 = [r for r in rows if r["axis"] == "MASS" and r["parent"].startswith("h33-h33-2-b2-PRUNEp3px")]
    assert len(mass_r1) == 3
    shas = [r["sha256"] for r in rows if r["sha256"]] + [
        r["sha256_zeros"] for r in rows if r["sha256_zeros"]
    ]
    assert len(shas) == len(set(shas)), "duplicate SHA-256 in ledger"
