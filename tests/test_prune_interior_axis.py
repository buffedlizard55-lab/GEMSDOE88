"""Unit tests for the PRUNE interior-annulus bracket (2.236 / 2.828 / 5 px).

Synthetic, label-free tests only: CI restores the validation subset, so these
tests never open the 419 MB feature stack or a released TIFF. End-to-end build
consistency is checked, when the local build exists, against the tracked ledger,
preregistration and evidence report JSONs.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_interior_variants as interior  # noqa: E402

LEDGER = ROOT / "ledger" / "submissions.csv"
PREREG = ROOT / "registry" / "prune_interior_preregistration.json"
REPORT = ROOT / "evidence" / "prune_interior_report.json"
SQRT5 = 5 ** 0.5
SQRT8 = 8 ** 0.5


def test_specs_are_unique_ordered_and_span_the_unsampled_annulus():
    specs = interior.SPECS
    assert len(specs) == 3
    assert len({spec["value"] for spec in specs}) == 3
    thresholds = [spec["threshold_px"] for spec in specs]
    assert thresholds == sorted(thresholds)
    # The two interior arms are the only distinct pixel-centre bands below 3 px
    # besides R0's own 2 px collar; the third extends the outer sweep (> 4.3 px).
    assert thresholds == pytest.approx([SQRT5, SQRT8, 5.0])
    assert max(thresholds[:2]) < 3.0
    assert min(thresholds[2:]) > 4.3
    for spec in specs:
        lo, point, hi = spec["prediction_range"][0], spec["prediction"], spec["prediction_range"][1]
        assert -1.0 <= lo <= point <= hi <= 1.0
        assert spec["threshold_m"] == pytest.approx(100.0 * spec["threshold_px"])


def test_specs_do_not_repeat_any_ledgered_parent_axis_value():
    values = {spec["value"] for spec in interior.SPECS}
    with LEDGER.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    collisions = [
        r["id"] for r in rows
        if r["parent"] == interior.PARENT_ID and r["axis"] == interior.AXIS and r["value"] in values
    ]
    # After the build these rows exist exactly once each; before the build none exist.
    assert len(collisions) in (0, 3)


def test_prune_at_threshold_keeps_count_and_respects_a_sub_3px_collar():
    parent = np.zeros((14, 14), dtype=bool)
    parent[2, 2] = True   # d = 2.5 -> inside the 2.828 collar, removed
    parent[4, 4] = True   # d = 3.5 -> survivor
    parent[7, 7] = True   # d = 5.0 -> survivor at the boundary band (> 2.828)
    parent[9, 9] = True   # d = 6.0 -> survivor

    distance = np.full(parent.shape, 9.0, dtype=np.float32)
    distance[2, 2] = 2.5
    distance[4, 4] = 3.5
    distance[7, 7] = 5.0
    distance[9, 9] = 6.0
    support = np.ones(parent.shape, dtype=bool)
    weight = np.zeros(parent.shape, dtype=np.float32)
    weight[1:13, 1:13] = np.linspace(0.0, 1.0, 144, dtype=np.float32).reshape(12, 12)

    candidate, stats = interior.prune_at_threshold(
        parent=parent,
        source_support=support,
        d_catalogue=distance,
        expected_fault_weight=weight,
        threshold_px=SQRT8,
    )

    assert int(candidate.sum()) == int(parent.sum()) == 4
    assert stats["n_removed"] == stats["n_added"] == 1
    assert not np.any(candidate & (distance <= SQRT8))
    assert stats["min_catalogue_distance_px"] > SQRT8
    assert stats["pct_changed_moved"] == 25.0
    assert stats["pct_changed_symmetric_difference"] == 50.0
    # PRUNE is the section 4.4 exception: sub-3 px minima are legal for this axis.
    assert candidate[4, 4] and candidate[7, 7] and candidate[9, 9]


def test_prune_accepts_the_inclusive_50_percent_change_boundary():
    parent = np.zeros((20, 20), dtype=bool)
    parent[0, 0] = True
    parent[19, 19] = True
    distance = np.full(parent.shape, 9.0, dtype=np.float32)
    distance[0, 0] = 2.1  # inside the 2.236 collar: one of two dots removed -> 50%
    support = np.ones(parent.shape, dtype=bool)
    weight = np.ones(parent.shape, dtype=np.float32)
    candidate, stats = interior.prune_at_threshold(
        parent, support, distance, weight, threshold_px=SQRT5
    )
    assert int(candidate.sum()) == 2
    assert stats["pct_changed_moved"] == pytest.approx(50.0)


@pytest.mark.skipif(not PREREG.is_file(), reason="interior PRUNE build has not run locally")
def test_preregistration_froze_three_arms_before_proxies():
    prereg = json.loads(PREREG.read_text())
    assert prereg["schema"] == "gems88.prune-interior-annulus-preregistration.v1"
    assert [v["value"] for v in prereg["variants"]] == ["p2.236px", "p2.828px", "p5px"]
    assert prereg["annulus_geometry"]["r0_dots_in_annulus_2_to_3"] == 2171
    assert prereg["no_submission"] is True
    for variant in prereg["variants"]:
        assert variant["predicted_change"].startswith("MODEL:")
        lo, hi = variant["predicted_range"]
        point = float(variant["predicted_change"].split(":")[1])
        assert lo <= point <= hi


@pytest.mark.skipif(not REPORT.is_file(), reason="interior PRUNE build has not run locally")
def test_report_ledger_and_cards_agree_on_the_three_built_arms():
    report = json.loads(REPORT.read_text())
    with LEDGER.open(newline="", encoding="utf-8") as stream:
        ledger = {r["id"]: r for r in csv.DictReader(stream)}
    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())

    assert len(report["variants"]) == 3
    seen_pairs = set()
    for rec in report["variants"]:
        row = ledger[rec["id"]]
        assert row["axis"] == "PRUNE" and row["status"] == "BUILT"
        assert row["sha256"] == rec["sha256"]
        assert row["sha256_zeros"] == rec["sha256_zeros"]
        assert int(row["n_dots"]) == rec["n_dots"] == 37654
        assert rec["id"] in cards
        pair = (row["parent"], row["axis"], row["value"])
        assert pair not in seen_pairs
        seen_pairs.add(pair)
        # Fixed-count one-for-one relocation and the arm's own collar.
        diff = rec["parent_diff"]
        assert diff["n_added"] == diff["n_removed"]
        assert diff["min_dist_catalogue_px"] >= rec["threshold_px"]
        assert 1.0 <= float(row["pct_changed"]) <= 50.0
