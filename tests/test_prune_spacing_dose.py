"""Tests for the PRUNE spacing-lock dose ladder and its random-order control."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_spacing_dose_variants as bpd  # noqa: E402

REPORT = ROOT / "evidence" / "prune_spacing_dose_report.json"
PREREG = ROOT / "registry" / "prune_spacing_dose_preregistration.json"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
REBUILD_REPORT = ROOT / "evidence" / "prune_spaced_artifact_rebuild.json"


def _rows() -> list[dict[str, str]]:
    with LEDGER.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_registered_arms_are_a_matched_spacing_dose_triplet():
    specs = bpd.SPECS
    assert len(specs) == 3
    assert {spec["value"] for spec in specs} == {"p3space28", "p3space45", "p3space35rand"}
    assert all(spec["spacing_px"] >= 2.8 for spec in specs)
    orders = [spec["order"] for spec in specs]
    assert orders.count("marginal_dti") == 2 and orders.count("random") == 1
    for spec in specs:
        lo, hi = spec["prediction_range"]
        assert -1.0 <= lo <= spec["prediction"] <= hi <= 1.0
        # the dose ladder must bracket the ledgered 3.5 px arm, not replace it
        assert spec["spacing_px"] != 3.5 or spec["order"] == "random"


def test_random_order_refill_is_deterministic_and_respects_the_lock():
    shape = (26, 44)
    base = np.zeros(shape, dtype=bool)
    base[4, 3] = base[10, 40] = base[21, 3] = base[21, 40] = True
    support = np.zeros(shape, dtype=bool)
    support[3:23, 7:37] = True
    first, stats = bpd.spaced_random_add(base, support, n_add=12, spacing_px=3.5, seed=7)
    second, _ = bpd.spaced_random_add(base, support, n_add=12, spacing_px=3.5, seed=7)
    other, _ = bpd.spaced_random_add(base, support, n_add=12, spacing_px=3.5, seed=8)
    assert np.array_equal(first, second), "the control must be reproducible from its seed"
    assert not np.array_equal(first, other), "a different seed must give a different fill"
    assert first.sum() == base.sum() + 12 == stats["filled"] + base.sum()
    points = np.argwhere(first)
    assert cKDTree(points).query(points, k=2)[0][:, 1].min() >= 3.5 - 1e-9


def test_random_order_refill_fails_closed_when_the_lock_cannot_supply_the_count():
    shape = (10, 10)
    base = np.zeros(shape, dtype=bool)
    base[5, 5] = True
    support = np.zeros(shape, dtype=bool)
    support[4:7, 4:7] = True
    with pytest.raises(ValueError):
        bpd.spaced_random_add(base, support, n_add=1, spacing_px=3.5, seed=1)


def test_preregistration_freezes_the_three_predictions_before_any_proxy():
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    assert prereg["predictions_are"].startswith("MODEL")
    assert prereg["no_submission"] is True
    registered = {item["value"]: item for item in prereg["variants"]}
    assert set(registered) == {spec["value"] for spec in bpd.SPECS}
    for spec in bpd.SPECS:
        assert registered[spec["value"]]["spacing_px"] == spec["spacing_px"]
        assert registered[spec["value"]]["predicted_range"] == list(spec["prediction_range"])
    assert prereg["parent"]["zeros_sha256"] == "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"


def test_ledger_rows_are_new_unique_and_byte_consistent_with_the_report():
    rows = _rows()
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    for spec in bpd.SPECS:
        value = spec["value"]
        matches = [row for row in rows if row["parent"] == bpd.PARENT_ID
                   and row["axis"] == "PRUNE" and row["value"] == value]
        assert len(matches) == 1, f"expected exactly one ledger row for {value}"
        row = matches[0]
        rec = report["variants"][value]
        assert row["sha256"] == rec["sha256"] and row["sha256_zeros"] == rec["sha256_zeros"]
        assert row["id"] == rec["id"]
        assert row["status"] == "BUILT"
        assert int(row["n_dots"]) == 37_654
        assert 1.0 <= float(row["pct_changed"]) <= 50.0
        assert row["receipt_score"] == "" and row["receipt_date"] == ""
        assert row["predicted_change"] == f"MODEL:{spec['prediction']:+.3f}"

    pairs = [(row["parent"], row["axis"], row["value"]) for row in rows]
    assert len(pairs) == len(set(pairs)), "repeated (parent, axis, value) pair in the ledger"
    hashes = [row["sha256"] for row in rows] + [row["sha256_zeros"] for row in rows]
    assert len(hashes) == len(set(hashes)), "duplicate artifact hash in the ledger"


def test_gate_clean_geometry_is_recorded_for_every_arm():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    for value, rec in report["variants"].items():
        assert rec["gates"]["zero_catalogue_mass"] is True
        assert rec["gates"]["reread_from_disk_verified"] is True
        assert rec["parent_diff"]["min_dist_catalogue_px"] >= 3.0
        assert rec["refill_min_nn_px"] >= rec["refill_spacing_px"] - 1e-9
        assert rec["removed_parent_dots"] == rec["added_dots"] == 2171
        assert rec["report_only_diagnostics"]["sgmc_control"]["dti"] > 0.0


def test_mechanism_cards_exist_with_the_brief_fields():
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    required = {"hypothesis", "mechanism", "non_fault_mimic", "predicted_sign_size", "falsifier"}
    for rec in report["variants"].values():
        card = cards[rec["id"]]
        assert required <= set(card)
        assert card["axis"] == "PRUNE"
        assert card["fixed_count"] == 37_654


def test_ordering_control_is_numerically_close_to_the_ranked_arm():
    """The blind instrument must be reported as ranking-blind, not as a field win."""
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    diag = report["report_only_diagnostics"]
    r0 = diag["h33-h33-2-b2"]["sgmc_control"]["dti"]
    ranked = diag["h33-h33-2-b2-PRUNEp3space35rand"]["sgmc_control"]["dti"]
    # the random-order arm and the ledgered ranked arm (0.101042) must land within
    # 0.002 on the blind control; a bigger gap would mean the ranking, not the
    # geometry, was doing the work and the report would need rewriting.
    assert abs(ranked - 0.101042) <= 0.002
    assert ranked > r0
    assert report["live_change_under_0.01"].startswith("no evidence")


def test_queue_rebuild_reproduced_both_ledgered_spaced_arms_byte_exactly():
    rebuild = json.loads(REBUILD_REPORT.read_text(encoding="utf-8"))
    assert rebuild["all_byte_exact"] is True
    assert set(rebuild["arms"]) == {"p3space35", "p4space35"}
    for value, rec in rebuild["arms"].items():
        assert rec["sha256"] == rec["expected_sha256"]
        assert rec["sha256_zeros"] == rec["expected_sha256_zeros"]
    # and the rebuild pins still agree with the ledger rows they recover
    rows = {(row["axis"], row["value"]): row for row in _rows()}
    for value in ("p3space35", "p4space35"):
        assert rows[("PRUNE", value)]["sha256"] == rebuild["arms"][value]["sha256"]
