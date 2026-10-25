"""Regression & deliverable tests for Session e9074a53 (2026-10-25)."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _read_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


def test_session_e9074a53_run_card_and_mirrors_are_identical_and_negative() -> None:
    reg = _read_json("registry/session_e9074a53_run_card.json")
    web = _read_json("docs/data/session_e9074a53_run_card.json")
    ev = _read_json("evidence/session_e9074a53_run_card.json")
    assert reg == web == ev
    assert reg["session_id"] == "e9074a53"
    assert reg["decision"] == "DUPLICATE_STOP"
    assert reg["verdict"] == "negative"
    assert reg["promote"] is False
    assert reg["ok_to_download_new_file"] is False
    assert reg["ok_to_submit"] is False
    assert reg["approved_for_weekly_slot"] is False
    assert reg["new_rasters_generated"] == 0
    assert reg["weekly_slots_used"] == 0
    assert reg["portal_submissions"] == 0
    assert reg["organizer_confirmed_score"] is None
    assert reg["raster_file"] is None and reg["raster_sha256"] is None
    assert 0 < len(reg["submission_name"]) == reg["submission_name_length"] <= 140
    assert 0 < len(reg["submission_note"]) == reg["submission_note_length"] <= 140
    assert [h["id"] for h in reg["ranked_untried_hypotheses"]] == [
        "H88-ANIS",
        "H88-FLDC",
        "H88-FSTD",
        "H88-CHFR",
        "H88-NWIS-HB",
    ]
    assert reg["remediated_irregularities"] == [
        "IR-88-E907-01",
        "IR-88-E907-02",
        "IR-88-E907-03",
        "IR-88-E907-04",
        "IR-88-E907-05",
    ]
    assert reg["software_review"]["three_passes_completed"] is True
    assert [p["pass"] for p in reg["software_review"]["passes"]] == [1, 2, 3]
    assert reg["software_review"]["passes"][2]["all_requested_deliverables_met"] is False


def test_session_e9074a53_docs_and_leaderboard_snapshot_mirrors_match() -> None:
    rev = (ROOT / "research/session-e9074a53-review.md").read_text()
    assert rev == (ROOT / "docs/research/session-e9074a53-review.md").read_text()
    assert "DUPLICATE_STOP" in rev and "IR-88-E907-01" in rev and "0.2778" in rev

    hyp = (ROOT / "research/session-e9074a53-hypotheses.md").read_text()
    assert hyp == (ROOT / "docs/research/session-e9074a53-hypotheses.md").read_text()
    for code in ("H88-ANIS", "H88-FLDC", "H88-FSTD", "H88-CHFR", "H88-NWIS-HB"):
        assert code in hyp

    snap = _read_json("evidence/leaderboard_official_snapshot_e9074a53_20261025.json")
    assert snap == _read_json("docs/data/leaderboard_official_snapshot_e9074a53_20261025.json")
    assert snap["top_10"][0] == {"rank": 1, "team": "xiaofanhu", "dti": 0.4413, "submissions": 30}
    assert snap["top_10"][7]["team"] == "DARD" and snap["top_10"][7]["dti"] == 0.3398


def test_no_lane_validator_uses_bare_asserts_stripped_by_python_optimize() -> None:
    for path in sorted((ROOT / "scripts").glob("validate_*88*.py")):
        tree = ast.parse(path.read_text())
        bare = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        assert not bare, f"{path.name} contains bare assert(s) stripped under python -O at lines {bare}"


def test_ibl88_phys_near_sgmc88_and_mmrx88_provenance_and_verdict_repairs() -> None:
    ibl = _read_json("registry/ibl88_run_card.json")
    assert ibl == _read_json("docs/data/ibl88_run_card.json") == _read_json("evidence/ibl88_run_card.json")
    assert ibl["evidence_status"]["incumbent_organizer_confirmed_live_score"] is None
    assert ibl["evidence_status"]["incumbent_user_reported_live_score"] == 0.2778
    assert (ROOT / ibl["submission"]["file"]).is_file()
    assert (ROOT / ibl["submission"]["repo_copy"]).is_file()
    assert (ROOT / ibl["validator"]["file"]).is_file()

    for stem in ("phys_near", "sgmc88"):
        rc = _read_json(f"registry/{stem}_run_card.json")
        gv = _read_json(f"registry/{stem}_gate_verdict.json")
        assert rc == _read_json(f"docs/data/{stem}_run_card.json")
        assert gv == _read_json(f"docs/data/{stem}_gate_verdict.json")
        assert rc["verdict"] == "negative" and gv["verdict"] == "negative"
        assert rc["ok_to_submit"] is False and gv["ok_to_submit"] is False
        assert rc["holdout_dti"]["ci95"] is None

    mmrx = _read_json("registry/mmrx88_run_card.json")
    assert mmrx == _read_json("docs/data/mmrx88_run_card.json")
    assert mmrx["download"] is None
    assert (ROOT / mmrx["repo_copy"]).is_file()


def test_fabric_release_report_and_browser_pinned_docs_stay_green() -> None:
    browser = _read_json("evidence/session_693b10af_browser_check.json")
    regenerated = {
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/data/download_audit.json",
        "evidence/download_audit.json",
        "docs/data/hypothesis_queue.json",
    }
    for rel, digest in browser["source_sha256"].items():
        if rel in regenerated:
            continue
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel

    if not (ROOT / "data/registry/dense_17gemdoe.tif").is_file() or len(list((ROOT / "data/registry").rglob("*.tif"))) < 20:
        pytest.skip("full registry tier not restored")
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.validate_current import fabric_release_report

    rep = fabric_release_report(ROOT)
    assert rep["ok_to_submit"] is False
    assert rep["verdict"] == "negative"
