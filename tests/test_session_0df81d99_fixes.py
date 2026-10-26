from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_con88_validator_has_zero_bare_asserts_and_runs_under_python_o() -> None:
    """validate_con88.py must not use bare asserts (stripped by python -O)."""
    validator_path = ROOT / "scripts/validate_con88.py"
    tree = ast.parse(validator_path.read_text(encoding="utf-8"))
    asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert asserts == [], f"validate_con88.py still contains bare assert(s) at lines {asserts}"

    proc = subprocess.run(
        [sys.executable, "-O", str(validator_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(proc.stdout)
    assert report["decision"] == "DUPLICATE_STOP"
    assert report["ok_to_submit"] is False
    assert report["research_download_ok"] is True
    assert report["historical_holdout_valid_for_promotion"] is False
    assert report["experiments_run"] == 0
    assert report["new_rasters_generated"] == 0

    proc_req = subprocess.run(
        [sys.executable, "-O", str(validator_path), "--require-submit"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_req.returncode == 2
    req_report = json.loads(proc_req.stdout)
    assert req_report["ok_to_submit"] is False


def test_con88_validator_detects_run_card_or_gate_tampering(tmp_path: Path) -> None:
    """Tampering with CON88 run-card or gate flags must fail closed (exit 1, AUDIT_ERROR)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import validate_con88

    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    (fake_root / "docs").mkdir()
    for rel in [
        "data",
        "vendor",
        "src",
        "scripts",
        "docs/downloads",
        "docs/data",
        "evidence",
    ]:
        (fake_root / rel).symlink_to(ROOT / rel, target_is_directory=True)
    (fake_root / "registry").mkdir()
    for p in (ROOT / "registry").iterdir():
        if p.name != "con88_gates.json":
            (fake_root / "registry" / p.name).symlink_to(p)
    gates = json.loads((ROOT / "registry/con88_gates.json").read_text(encoding="utf-8"))
    gates["ok_to_submit"] = True
    (fake_root / "registry/con88_gates.json").write_text(json.dumps(gates), encoding="utf-8")
    (fake_root / "run_card_con88.json").symlink_to(ROOT / "run_card_con88.json")

    code = validate_con88.main(argv=[], root=fake_root)
    assert code == 1


def test_all_50_published_tiffs_carry_do_not_submit_and_zero_eligible() -> None:
    # PR #200's bypass pair was withdrawn and removed in PR #202, so the
    # published inventory is 50 (IR-88-AEF1337D-01).
    downloads = sorted((ROOT / "docs/downloads").glob("*.tif"))
    variants = sorted((ROOT / "docs/research-variants").glob("*.tif"))
    all_tiffs = downloads + variants
    assert len(downloads) == 49
    assert len(variants) == 1
    assert len(all_tiffs) == 50
    unmarked = [p.name for p in all_tiffs if "DO-NOT-SUBMIT" not in p.name]
    assert unmarked == []

    audit = json.loads((ROOT / "docs/data/download_audit.json").read_text(encoding="utf-8"))
    assert audit["tiff_count"] == 49
    assert audit["additional_research_tiff_count"] == 1
    assert audit["total_published_tiff_count"] == 50
    assert audit["total_research_download_pass_count"] == 50
    assert audit["protocol_eligible_count"] == 0
    assert audit["ok_to_submit"] is False
    for item in audit["artifacts"] + audit["additional_research_artifacts"]:
        assert item["ok_to_submit"] is False
        assert item["cleared_by_con88_gates"] is False


def test_user_claims_include_gemsdoe91_and_gemsdoe92_and_20261026_updates() -> None:
    report = json.loads((ROOT / "docs/data/user_reported_results.json").read_text(encoding="utf-8"))
    assert report["site_count"] == 92
    assert report["distinct_claim_count"] == 123
    assert report["sites_without_a_reported_result"] == ["GEMSDOE86", "GEMSDOE88"]
    by_site: dict[str, list[tuple[str, str]]] = {}
    for row in report["claims"]:
        by_site.setdefault(row["site"], []).append((row["submission_name"], row["user_reported_value"]))
    assert by_site["GEMSDOE91"] == [
        ("gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros", "0.1367"),
        ("gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros", "0.1823"),
    ]
    assert by_site["GEMSDOE92"] == [("gemsdoe92-listricdip-updip50-37654-20261025T190000Z-zeros", "0.0255")]


def test_session_0df81d99_artifacts_and_browser_receipt_are_synced() -> None:
    for rel in [
        "registry/session_0df81d99_run_card.json",
        "evidence/session_0df81d99_run_card.json",
        "docs/data/session_0df81d99_run_card.json",
        "research/session-0df81d99-hypotheses.md",
        "docs/research/session-0df81d99-hypotheses.md",
        "research/session-0df81d99-review.md",
        "docs/research/session-0df81d99-review.md",
        "evidence/session_0df81d99_browser_check.json",
        "docs/data/session_0df81d99_browser_check.json",
    ]:
        assert (ROOT / rel).is_file(), f"Missing {rel}"

    rc_reg = (ROOT / "registry/session_0df81d99_run_card.json").read_bytes()
    assert rc_reg == (ROOT / "evidence/session_0df81d99_run_card.json").read_bytes()
    assert rc_reg == (ROOT / "docs/data/session_0df81d99_run_card.json").read_bytes()
    rc = json.loads(rc_reg)
    assert rc["verdict"] == "negative"
    assert rc["ok_to_submit"] is False
    assert rc["weekly_slots_used"] == 0
    assert rc["budget"]["geological_experiments_run"] == 0

    br_ev = (ROOT / "evidence/session_0df81d99_browser_check.json").read_bytes()
    assert br_ev == (ROOT / "docs/data/session_0df81d99_browser_check.json").read_bytes()
    br = json.loads(br_ev)
    assert br["status"] == "PASS"
    assert len(br["pages"]) >= 7
    assert br["con88_page"]["pass"] is True
    assert len(br["source_sha256"]) == 14

    status = json.loads((ROOT / "docs/status.json").read_text(encoding="utf-8"))
    active_card = json.loads((ROOT / "docs" / status["current_review"]).read_text(encoding="utf-8"))
    active_br = json.loads((ROOT / active_card["verification"]["browser_evidence"]).read_text(encoding="utf-8"))
    assert active_br["status"] == "PASS" and active_br["ok_to_submit"] is False
    assert set(br["source_sha256"]) <= set(active_br["source_sha256"])
    for rel, pinned_sha in active_br["source_sha256"].items():
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert actual == pinned_sha, f"Active browser receipt stale for {rel}: {actual} != {pinned_sha}"
