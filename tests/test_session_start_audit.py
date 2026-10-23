"""Do not mint new experiments for aliases of already-built PRUNE radii."""
from decimal import Decimal
import json
from pathlib import Path

from audit_session_start import prune_coverage, radius

ROOT = Path(__file__).resolve().parents[1]


def row(value, parent="h33-h33-2-b2", axis="PRUNE"):
    return {"id": f"arm-{value}", "parent": parent, "axis": axis, "value": value}


def test_radius_aliases_and_nonfinite():
    assert radius("3") == radius("p3px") == radius("P3.0PX") == Decimal(3)
    assert radius("p3.2px") == Decimal("3.2")
    for value in ("nan", "inf", "scarp2px", ""):
        assert radius(value) is None


def test_parent_is_not_an_experiment_and_other_axes_do_not_fill_slots():
    coverage = prune_coverage([row("p1px"), row("3", axis="SNAP"), row("p3px", parent="other")])
    assert coverage["1"]["do_not_build"]
    assert coverage["2"]["do_not_build"] and coverage["2"]["is_parent"]
    assert not coverage["3"]["do_not_build"]


def test_existing_alias_covers_arm_without_hash_or_overlap_thresholds():
    coverage = prune_coverage([row("p1px"), row("3")])
    assert all(c["do_not_build"] for c in coverage.values())
    assert coverage["3"]["existing_ids"] == ["arm-3"]


def test_recorded_session_stop_is_not_a_submission_receipt():
    report = json.loads((ROOT / "evidence/session_20261023_prune_stop.json").read_text())
    assert report["r0_exact_rebuild"] and report["manifest_inputs_verified"] == 15
    assert report["decision"] == "STOP_NO_NEW_VARIANTS"
    assert report["new_variants"] == report["new_ledger_rows"] == 0
    assert report["ledger_rows"] == 32
    assert report["unique_primary_and_fallback_hashes"]
    assert report["unique_literal_parent_axis_value"]
    cards = report["historical_cards"]
    snap = next(c for name, c in cards.items() if "SNAP" in name)
    assert snap["minimum_catalogue_distance_px"] < 3
    assert not snap["collar_eligible_from_record"]
    assert report["preexisting_tracked_tif_zip_paths_data_use_unchecked"]
