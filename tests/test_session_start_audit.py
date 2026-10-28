"""Do not mint new experiments for aliases of already-built PRUNE radii."""
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import audit_session_start as startup
from audit_session_start import hash_relationships, prune_coverage, radius

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


def test_help_never_runs_or_overwrites_the_historical_audit():
    historical = ROOT / 'evidence/session_20261023_prune_stop.json'
    before = historical.read_bytes()
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/audit_session_start.py'), '--help'],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0 and 'usage:' in result.stdout
    assert historical.read_bytes() == before


def test_failed_startup_clears_any_stale_cached_pass(monkeypatch, tmp_path):
    cache = tmp_path / '.cache'
    cache.mkdir()
    report = cache / 'session-start-audit-current.json'
    report.write_text('{"status":"old PASS"}')
    monkeypatch.setattr(startup, 'ROOT', tmp_path)
    monkeypatch.setattr(startup.verify_parent_r0, 'main', lambda output: 1)
    assert startup.main([]) == 1
    assert not report.exists()


def test_hash_alias_within_one_record_is_not_a_cross_record_duplicate():
    rows = [
        {"id": "same-file", "sha256": "a" * 64, "sha256_zeros": "a" * 64},
        {"id": "different-files", "sha256": "b" * 64, "sha256_zeros": "c" * 64},
    ]
    audit = hash_relationships(rows)
    assert audit["all_hash_values_distinct"] is False
    assert audit["different_rows_have_distinct_hashes"] is True
    assert [row["id"] for row in audit["same_row_primary_fallback_aliases"]] == ["same-file"]
    assert audit["cross_row_duplicates"] == []


def test_primary_reference_must_match_the_full_hash_and_bad_fields_fail_closed():
    primary = 'a' * 64
    good = hash_relationships([{'id': 'ref', 'sha256': primary,
                                'sha256_zeros': 'zeros-variant-is-primary:' + 'a' * 16}])
    assert good['all_hash_fields_resolved'] is True
    assert good['different_rows_have_distinct_hashes'] is True
    assert good['same_row_primary_fallback_aliases'][0]['representation'] == 'primary-reference'
    for value in ('zeros-variant-is-primary:' + 'b' * 16, 'not-a-hash'):
        bad = hash_relationships([{'id': 'bad', 'sha256': primary, 'sha256_zeros': value}])
        assert bad['all_hash_fields_resolved'] is False
        assert bad['different_rows_have_distinct_hashes'] is False
        assert bad['unresolved_hash_fields'][0]['field'] == 'sha256_zeros'


def test_hash_reuse_across_rows_still_fails_even_with_duplicate_ids_or_swapped_columns():
    rows = [
        {"id": "reused-id", "sha256": "a" * 64, "sha256_zeros": ""},
        {"id": "reused-id", "sha256": "b" * 64, "sha256_zeros": "a" * 64},
    ]
    audit = hash_relationships(rows)
    assert audit["different_rows_have_distinct_hashes"] is False
    assert audit["cross_row_duplicates"][0]["row_indices"] == [0, 1]


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
