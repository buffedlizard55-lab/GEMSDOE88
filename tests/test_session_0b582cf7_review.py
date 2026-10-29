"""Verification tests for session 0b582cf7 (2026-10-26 late focus-9 re-audit)."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOCUS_SITES = [
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
]


def test_focus_latest_auditor_offline_check_passes_under_python_o() -> None:
    script = ROOT / "scripts/audit_focus_latest_20261026b.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert bare_asserts == [], f"bare assert(s) at {bare_asserts}"

    proc = subprocess.run(
        [sys.executable, "-O", str(script)], cwd=ROOT,
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = json.loads(proc.stdout)
    assert out["status"] == "PASS"
    assert out["decision"] == "DUPLICATE_STOP"
    assert out["ok_to_submit"] is False
    assert out["sibling_sites_claiming_ok_to_submit"] == ["GEMSDOE27"]

    proc_req = subprocess.run(
        [sys.executable, "-O", str(script), "--require-submit"], cwd=ROOT,
        capture_output=True, text=True, check=False,
    )
    assert proc_req.returncode == 2
    assert json.loads(proc_req.stdout)["ok_to_submit"] is False


def test_focus_latest_auditor_rejects_tampering(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import audit_focus_latest_20261026b as auditor

    (tmp_path / "evidence").mkdir()
    (tmp_path / "docs/data").mkdir(parents=True)
    payload = json.loads((ROOT / "evidence/focus_latest_20261026b_audit.json").read_text(encoding="utf-8"))
    payload["summary_verdict"]["ok_to_submit"] = True
    bad = json.dumps(payload).encode("utf-8")
    (tmp_path / "evidence/focus_latest_20261026b_audit.json").write_bytes(bad)
    (tmp_path / "docs/data/focus_latest_20261026b.json").write_bytes(bad)
    (tmp_path / "docs/data/focus_latest_20261026b.csv").write_bytes(
        (ROOT / "docs/data/focus_latest_20261026b.csv").read_bytes()
    )
    assert auditor.main([], root=tmp_path) == 1


def test_late_focus_audit_measured_invariants() -> None:
    ev = (ROOT / "evidence/focus_latest_20261026b_audit.json").read_bytes()
    assert ev == (ROOT / "docs/data/focus_latest_20261026b.json").read_bytes()
    audit = json.loads(ev)
    rows = audit["focus_sites"]
    assert [r["site"] for r in rows] == FOCUS_SITES
    assert audit["summary_verdict"]["heads_advanced_since_prior_audit"] == 9
    assert audit["summary_verdict"]["ok_to_submit"] is False

    for row in rows:
        # Fresh measurements from saved sibling bytes at pinned HEADs.
        assert row["overlap_3px_vs_dense_17gemdoe"] == 1.0
        assert row["portal_safe_full_grid_0_1_and_grid_match"] is True
        assert row["finite_cells"] == row["total_cells"] == 12279160
        assert row["positive_on_catalogue"] == 0
        assert row["d_cat_le2_px"] == 0
        assert row["positive_pixels"] > 0
        # Genuinely off the historical H19-5/D2.8/H33 lineage on sparse tests.
        assert row["overlap_3px_vs_h33_h33_2_b2"] < 0.70
        assert row["organizer_confirmed_score"] is None
        if row["sibling_claimed_sha256"] is not None:
            assert row["sha256_matches_sibling_claim"] is True

    by_site = {r["site"]: r for r in rows}
    # The only site claiming OK TO SUBMIT, and its measured geometry.
    g27 = by_site["GEMSDOE27"]
    assert g27["sibling_claims_ok_to_submit"] is True
    assert g27["sha256"].startswith("2c002b0279241986")
    assert abs(g27["overlap_3px_vs_h33_h33_2_b2"] - 0.5023370691028841) < 1e-12
    # Extreme catalogue-collar concentration flag (IR-88-0B582CF7-03).
    assert by_site["GEMSDOE33"]["frac_gt25_px_from_catalogue"] < 0.03
    # Nonstandard dot budget on GEMSDOE25's latest lane.
    assert by_site["GEMSDOE25"]["positive_pixels"] == 59472

    with (ROOT / "docs/data/focus_latest_20261026b.csv").open(encoding="utf-8") as fh:
        csv_rows = list(csv.DictReader(fh))
    assert [r["site"] for r in csv_rows] == FOCUS_SITES
    assert all(r["cleared_to_submit_under_gemsdoe88_literal_protocol"] == "False" for r in csv_rows)


def test_selector_packet_ptgm_prereg_and_leaderboard_are_fail_closed() -> None:
    packet_ev = (ROOT / "evidence/selector_scoping_packet_20261026.json").read_bytes()
    assert packet_ev == (ROOT / "docs/data/selector_scoping_packet_20261026.json").read_bytes()
    packet = json.loads(packet_ev)
    assert packet["status"] == "DECISION_NOT_MADE"
    assert packet["ok_to_submit"] is False
    assert packet["decision_record_template"]["option_adopted"] is None
    assert packet["problem_proved_in_this_session"]["uncovered_allowed_pixels"] == 0
    cond = {c["candidate"]: c for c in packet["conditional_consequences_not_clearance"]["gemsdoe88_archived_top_candidates"]}
    assert cond["H88-BPWD"]["holdout_dti"] == 0.205991
    assert "WOULD STILL FAIL" in cond["H88-TDKL (canonical research download)"]["conditional_status_under_b"]

    prereg = json.loads((ROOT / "registry/preregistration_h88_ptgm_20261026.json").read_text(encoding="utf-8"))
    assert prereg["lane"] == "H88-PTGM"
    assert prereg["frozen_before_computation"] is True
    assert prereg["status"] == "NOT_EXECUTED_BLOCKED_BY_GENERATION_GUARD"
    assert prereg["experiments_run"] == 0 and prereg["rasters_generated"] == 0
    assert prereg["ok_to_submit"] is False

    lb_ev = (ROOT / "evidence/leaderboard_official_snapshot_0b582cf7_20261026.json").read_bytes()
    assert lb_ev == (ROOT / "docs/data/leaderboard_official_snapshot_0b582cf7_20261026.json").read_bytes()
    lb = json.loads(lb_ev)
    assert lb["evidence_class"].startswith("OBSERVED-PUBLIC")
    assert lb["top_rows_transcribed"][0] == {
        "rank": 1, "participant": "xiaofanhu",
        "best_public_dw_tversky": 0.4437, "submissions_shown": 31,
    }


def test_session_0b582cf7_run_card_and_review_mirror() -> None:
    reg = (ROOT / "registry/session_0b582cf7_run_card.json").read_bytes()
    assert reg == (ROOT / "evidence/session_0b582cf7_run_card.json").read_bytes()
    assert reg == (ROOT / "docs/data/session_0b582cf7_run_card.json").read_bytes()
    card = json.loads(reg)
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["new_tif_generated"] is False
    assert card["raster_sha256"] is None
    assert card["budget"]["geological_experiments_run"] == 0
    assert card["weekly_slots_used"] == 0
    assert len(card["submission_note"]) == card["submission_note_characters"] <= 140
    assert card["holdout_dti"]["dti"] is None
    assert card["correlation_overlap_vs_registry"]["universal_overlap_lower_bound"] == 1.0
    assert [h["id"] for h in card["ranked_untried_hypotheses"]] == [
        "H88-PTGM", "H88-BFRK", "H88-DRMC", "H88-VVRD", "H88-3DEP-SCARP",
    ]

    root_md = (ROOT / "research/session-0b582cf7-review.md").read_bytes()
    assert root_md == (ROOT / "docs/research/session-0b582cf7-review.md").read_bytes()
    text = root_md.decode("utf-8")
    assert "(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)" in text
    assert "IR-88-0B582CF7-01" in text
    for site in FOCUS_SITES:
        assert site in text
    # The earlier same-day decision on the site itself is unchanged.
    assert "DO NOT SUBMIT" in (ROOT / "docs/index.html").read_text(encoding="utf-8")


def test_post_merge_vvrd_withdrawal_and_active_browser_receipt() -> None:
    vvrd = json.loads((ROOT / "registry/vvrd88_run_card.json").read_text(encoding="utf-8"))
    assert vvrd["verdict"] == "negative"
    assert vvrd["ok_to_submit"] is False
    assert vvrd["original_verdict_in_pr200"] == "promote-to-selector-only"
    gate = json.loads((ROOT / "registry/vvrd88_gate_verdict.json").read_text(encoding="utf-8"))
    assert gate["verdict"] == "negative" and gate["ok_to_submit"] is False
    withdrawal_ev = (ROOT / "evidence/vvrd88_clearance_withdrawal_20261026.json").read_bytes()
    assert withdrawal_ev == (ROOT / "docs/data/vvrd88_clearance_withdrawal_20261026.json").read_bytes()
    # Canonical run card/gate restored (not the VVRD overwrites).
    canonical = json.loads((ROOT / "registry/gate_verdict.json").read_text(encoding="utf-8"))
    assert canonical["name"].startswith("gems88-phys44")
    # The bypass entrypoint and artifact were removed entirely in PR #202.
    assert not (ROOT / "scripts/generate_unique_submission.py").exists()
    assert not list((ROOT / "docs/downloads").glob("*vvrd*"))
    # Queue retires VVRD and still authorizes nothing.
    queue = json.loads((ROOT / "registry/hypothesis_queue.json").read_text(encoding="utf-8"))
    assert "H88-VVRD" in {r["id"] for r in queue["already_evaluated"]}
    assert queue["generation_authorized"] is False and queue["ok_to_submit"] is False
    # The prior receipts remain historical; the current review must bind a
    # fresh browser receipt instead of re-labelling old page hashes as current.
    status = json.loads((ROOT / "docs/status.json").read_text(encoding="utf-8"))
    assert status["current_review"] == "data/session_arena_2921f3de_run_card.json"
    assert status["previous_review"] == "data/session_32583983_run_card.json"
    br_ev = (ROOT / "evidence/session_0b582cf7_browser_check.json").read_bytes()
    assert br_ev == (ROOT / "docs/data/session_0b582cf7_browser_check.json").read_bytes()
    br = json.loads(br_ev)
    assert br["status"] == "PASS" and br["ok_to_submit"] is False
    assert len(br["pages"]) == 7 and all(p["pass"] and not p["overflow"] for p in br["pages"])
    active_card = json.loads((ROOT / "docs" / status["current_review"]).read_text(encoding="utf-8"))
    active_br = json.loads((ROOT / active_card["verification"]["browser_evidence"]).read_text(encoding="utf-8"))
    assert active_br["status"] == "PASS" and active_br["ok_to_submit"] is False
    assert set(br["source_sha256"]) <= set(active_br["source_sha256"])
    for rel, expected_sha in active_br["source_sha256"].items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert actual == expected_sha, f"Active browser pin mismatch on {rel}"
    # PTGM preregistration carries the PR #199 scientific correction.
    prereg = json.loads((ROOT / "registry/preregistration_h88_ptgm_20261026.json").read_text(encoding="utf-8"))
    assert "Gaussian" in prereg["amendments"][0]["corrected_operator"]
