"""Regression tests for the nine-site executive audit (2026-10-28).

Committed-record tests need no competition data. Byte-level tests run only when
the pinned owner-repo bytes were restored with ``--fetch`` (they are gitignored).
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC = json.loads((ROOT / "docs/data/nine_sites_20261028.json").read_text(encoding="utf-8"))
BOARD = json.loads((ROOT / "docs/data/leaderboard_public_snapshot_20261028.json").read_text(encoding="utf-8"))
PAGE = (ROOT / "docs/nine-sites/index.html").read_text(encoding="utf-8")
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def _by_site() -> dict:
    return {rec["site"]: rec for rec in DOC["sites"]}


def test_scope_is_exactly_the_nine_requested_sites():
    assert sorted(_by_site()) == sorted(SITES)


def test_nothing_is_cleared_and_no_raster_or_slot_was_created():
    assert DOC["ok_to_submit_any"] is False
    assert DOC["new_rasters_generated"] == 0
    assert DOC["experiments_run"] == 0
    assert DOC["weekly_slots_used"] == 0
    assert DOC["organizer_confirmed_scores"] == 0
    assert DOC["verdict"] == "negative"
    for rec in DOC["sites"]:
        assert rec["ok_to_download_and_submit"] is False
        assert rec["organizer_confirmed_score"] is None
        assert rec["uniqueness"]["passes_protocol_vs_witness"] is False
        assert rec["uniqueness"]["gate_decision"] == "DUPLICATE_STOP"


def test_user_reported_best_matches_the_recorded_csv():
    best: dict[str, float] = {}
    with (ROOT / "docs/data/user_reported_results.csv").open(encoding="utf-8") as stream:
        for rec in csv.DictReader(stream):
            if rec["site"] in SITES:
                best[rec["site"]] = max(best.get(rec["site"], -1.0), float(rec["user_reported_value"]))
    for site in SITES:
        assert _by_site()[site]["user_reported_best"]["user_reported_value"] == pytest.approx(best[site])
    assert _by_site()["GEMSDOE32"]["user_reported_best"]["user_reported_value"] == pytest.approx(0.2778)


def test_winner_hashes_match_the_source_json():
    for rec in DOC["sites"]:
        assert rec["file"]["sha256_matches_source_json"] is True
    source = json.loads((ROOT / "docs/data/focus_winner_sources_20261028_a896e29e.json").read_text())
    expected = {row["site"]: row["sha256"] for row in source["rows"]}
    for rec in DOC["sites"]:
        assert rec["file"]["sha256"] == expected[rec["site"]]


def test_official_format_passes_and_outside_convention_is_recorded():
    for rec in DOC["sites"]:
        fmt = rec["format"]
        assert fmt["official_format_pass"] is True
        assert fmt["bands"] == 1 and fmt["dtype"] == "float32"
        assert fmt["values_in_0_1_where_finite"] is True
        assert fmt["nonfinite_inside_footprint"] == 0
        assert fmt["nonzero_outside_footprint"] == 0
        assert fmt["outside_convention"] in {"nan", "zero"}
    conv = {rec["site"]: rec["format"]["outside_convention"] for rec in DOC["sites"]}
    assert {s for s, c in conv.items() if c == "nan"} == {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27",
                                                          "GEMSDOE28", "GEMSDOE31"}
    assert {s for s, c in conv.items() if c == "zero"} == {"GEMSDOE30", "GEMSDOE32",
                                                           "GEMSDOE33", "GEMSDOE36"}


def test_pairwise_overlap_is_recorded_and_fails_the_protocol():
    matrix = DOC["pairwise_forward_overlap"]
    for a in SITES:
        for b in SITES:
            if a == b:
                continue
            assert 0.0 <= matrix[a][b] <= 1.0
    assert DOC["min_pairwise_forward_overlap_among_nine"] >= 0.86
    assert DOC["max_pairwise_forward_overlap_among_nine"] == pytest.approx(1.0)
    assert DOC["overlap_limit"] == 0.70


def test_h33_lineage_is_a_strict_collar_subset_of_d28():
    lin = DOC["h33_lineage"]
    assert lin["h33_subset_of_d28"] is True
    assert lin["d28_dots"] == 44090 and lin["h33_dots"] == 37654
    assert lin["removed_from_d28"] == 6436 == lin["d28_dots"] - lin["h33_dots"]
    assert lin["removed_within_1px_of_catalogue"] == 3891
    assert lin["removed_between_1_and_2px_of_catalogue"] == 2545
    assert lin["removed_beyond_2px_of_catalogue"] == 0
    assert lin["h33_min_distance_to_catalogue_px"] > 2.0
    assert lin["gems30_vs_gems25_dot_identical"] is True


def test_leaderboard_snapshot_checks_match_the_fetched_rows():
    rows = BOARD["rows"]
    assert len(rows) == 50
    assert rows[0]["public_dw_tversky"] == pytest.approx(0.4544)
    assert BOARD["checks"]["user_claim_0_4413_present_in_top50"] is False
    assert BOARD["checks"]["user_claim_0_3195_rank"] == 26
    assert BOARD["checks"]["user_claim_0_2778_present_in_top50"] is False
    scores = [r["public_dw_tversky"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_page_states_the_decision_and_the_estimate_limit():
    for site in SITES:
        assert site in PAGE
    assert "Decision: no file from these nine sites is cleared" in PAGE
    assert "NO - DO NOT SUBMIT" in PAGE
    assert "NOT ESTIMABLE" in PAGE
    assert "USER-REPORTED" in PAGE


@pytest.mark.skipif(not (ROOT / "data/focus_winners").is_dir(), reason="pinned winner bytes not restored")
def test_restored_bytes_rehash_to_the_recorded_values():
    for rec in DOC["sites"]:
        path = ROOT / "data/focus_winners" / f"{rec['site']}_{Path(rec['file']['path_in_repo']).name}"
        assert path.exists(), path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == rec["file"]["sha256"]
