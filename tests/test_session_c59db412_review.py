"""Verification tests for session c59db412 (2026-10-26 9-focus-site audit & 124-claim sync)."""
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
    "GEMSDOE24",
    "GEMSDOE25",
    "GEMSDOE27",
    "GEMSDOE28",
    "GEMSDOE30",
    "GEMSDOE31",
    "GEMSDOE32",
    "GEMSDOE33",
    "GEMSDOE36",
]


def test_focus_sites_auditor_has_zero_bare_asserts_and_passes_under_python_o() -> None:
    script = ROOT / "scripts/audit_focus_sites_20261026.py"
    tree = ast.parse(script.read_text(encoding="utf-8"))
    bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert bare_asserts == [], f"audit_focus_sites_20261026.py has bare assert(s) at {bare_asserts}"

    proc = subprocess.run(
        [sys.executable, "-O", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = json.loads(proc.stdout)
    assert out["status"] == "PASS"
    assert out["decision"] == "DUPLICATE_STOP"
    assert out["ok_to_submit"] is False

    proc_req = subprocess.run(
        [sys.executable, "-O", str(script), "--require-submit"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_req.returncode == 2
    assert json.loads(proc_req.stdout)["ok_to_submit"] is False


def test_focus_sites_auditor_rejects_tampering(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import audit_focus_sites_20261026 as auditor

    (tmp_path / "evidence").mkdir()
    (tmp_path / "docs/data").mkdir(parents=True)
    payload = json.loads((ROOT / "evidence/focus_sites_20261026_audit.json").read_text(encoding="utf-8"))
    payload["summary_verdict"]["ok_to_submit"] = True
    bad = json.dumps(payload).encode("utf-8")
    (tmp_path / "evidence/focus_sites_20261026_audit.json").write_bytes(bad)
    (tmp_path / "docs/data/focus_sites_20261026.json").write_bytes(bad)
    (tmp_path / "docs/data/focus_sites_20261026.csv").write_bytes(
        (ROOT / "docs/data/focus_sites_20261026.csv").read_bytes()
    )
    assert auditor.main([], root=tmp_path) == 1


def test_nine_focus_sites_audit_invariants_and_forensic_proofs() -> None:
    ev_bytes = (ROOT / "evidence/focus_sites_20261026_audit.json").read_bytes()
    web_bytes = (ROOT / "docs/data/focus_sites_20261026.json").read_bytes()
    assert ev_bytes == web_bytes
    audit = json.loads(ev_bytes)

    verdict = audit["summary_verdict"]
    assert verdict["focus_site_count"] == 9
    assert verdict["unique_historical_champions_count"] == 0
    assert verdict["cleared_for_submission_count"] == 0
    assert verdict["ok_to_submit"] is False
    assert verdict["decision"] == "DUPLICATE_STOP"

    by_site = {row["site"]: row for row in audit["focus_sites"]}
    assert list(by_site.keys()) == FOCUS_SITES
    for site, row in by_site.items():
        assert row["any_candidate_cleared_to_submit"] is False, site
        champ = row["highest_scoring_submission"]
        assert champ["organizer_receipt"] is None
        assert champ["unique_for_new_submission"] is False
        assert champ["cleared_to_submit"] is False
        reg = champ["vs_gemsdoe88_registry"]
        assert reg["dense_17gemdoe_3px_forward_overlap"] == 1.0
        assert reg["gems19_h19_5_3px_forward_overlap"] >= 0.977

    # Exact pixel identity between GEMSDOE25 and GEMSDOE30 (44,090 dots)
    assert by_site["GEMSDOE25"]["highest_scoring_submission"]["positive_pixels"] == 44090
    assert by_site["GEMSDOE30"]["highest_scoring_submission"]["positive_pixels"] == 44090
    assert by_site["GEMSDOE30"]["highest_scoring_submission"]["exact_0px_fraction_in_D28"] == 1.0

    # GEMSDOE28 0.2715 prompt line byte-identical to GEMSDOE27 0.2449 (IR-88-C59DB412-01)
    proof28 = audit["gemsdoe28_02715_forensic_proof"]
    assert proof28["byte_identical_to_gemsdoe27_02449"] is True
    assert proof28["gemsdoe28_blob_sha256"] == proof28["gemsdoe27_file_sha256"]
    assert proof28["gemsdoe28_blob_sha256"].startswith("33003374335d")

    # GEMSDOE33 99.71% 3-px overlap with H19-5 (IR-88-C59DB412-03)
    ov33 = by_site["GEMSDOE33"]["highest_scoring_submission"]["vs_gemsdoe88_registry"]["gems19_h19_5_3px_forward_overlap"]
    assert 0.997 <= ov33 <= 0.998

    # GEMSDOE36 Anderson PINN is exact superset of H33-2-B2 (37,654 + 1,200 = 38,854)
    c36 = by_site["GEMSDOE36"]["highest_scoring_submission"]
    assert c36["positive_pixels"] == 38854
    assert round(c36["positive_pixels"] * c36["exact_0px_fraction_in_H33_B2"]) == 37654

    # CSV table has 9 rows matching FOCUS_SITES
    with (ROOT / "docs/data/focus_sites_20261026.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["site"] for r in rows] == FOCUS_SITES
    assert all(r["any_candidate_cleared_to_submit"] == "False" for r in rows)


def test_20261026_prompt_diff_and_123_claims_recorded() -> None:
    report = json.loads((ROOT / "docs/data/user_reported_results.json").read_text(encoding="utf-8"))
    assert report["site_count"] == 92
    assert report["distinct_claim_count"] == 123
    assert report["sites_without_a_reported_result"] == ["GEMSDOE86", "GEMSDOE88"]

    claims = {(r["site"], r["submission_name"]): r["user_reported_value"] for r in report["claims"]}
    expected_new = {
        ("GEMSDOE24", "gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros"): "0.0859",
        ("GEMSDOE25", "gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros"): "0.0742",
        ("GEMSDOE27", "gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite"): "0.2190",
        ("GEMSDOE28", "gems28-s18-mxtp-20261025-3e95505c011a-allfinite"): "0.0217",
        ("GEMSDOE28", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan"): "0.2710",
        ("GEMSDOE30", "gems30-MSDB1-edge44090-20261025-e7856ec3f14a"): "0.1462",
    }
    for key, val in expected_new.items():
        assert claims.get(key) == val, f"Missing or mismatched claim {key}"
    assert ("GEMSDOE28", "gems28-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan") not in claims


def test_session_c59db412_and_d634de37_run_cards_markdown_and_browser_receipt() -> None:
    for sid, expected_hyp_ids in (
        ("c59db412", ["H88-PTGM", "H88-BFRK", "H88-DRMC", "H88-VVRD", "H88-3DEP-SCARP"]),
        ("d634de37", ["H88-LGOF", "H88-SEMD", "H88-PHCT", "H88-CFRS", "H88-3DEP-INSAR"]),
    ):
        reg_bytes = (ROOT / f"registry/session_{sid}_run_card.json").read_bytes()
        assert reg_bytes == (ROOT / f"evidence/session_{sid}_run_card.json").read_bytes()
        assert reg_bytes == (ROOT / f"docs/data/session_{sid}_run_card.json").read_bytes()
        card = json.loads(reg_bytes)
        assert card["verdict"] == "negative"
        assert card["ok_to_submit"] is False
        assert card["weekly_slots_used"] == 0
        assert card["budget"]["geological_experiments_run"] == 0
        assert len(card["submission_note"]) == card["submission_note_characters"] <= 140
        assert [h["id"] for h in card["ranked_untried_hypotheses"]] == expected_hyp_ids

    for stem in (
        "session-c59db412-review.md",
        "session-c59db412-hypotheses.md",
        "session-d634de37-review.md",
        "session-d634de37-hypotheses.md",
    ):
        root_md = (ROOT / "research" / stem).read_bytes()
        docs_md = (ROOT / "docs/research" / stem).read_bytes()
        assert root_md == docs_md
        text = root_md.decode("utf-8")
        assert "(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)" in text

    br_ev = (ROOT / "evidence/session_d634de37_browser_check.json").read_bytes()
    assert br_ev == (ROOT / "docs/data/session_d634de37_browser_check.json").read_bytes()
    br = json.loads(br_ev)
    assert br["status"] == "PASS"
    assert br["ok_to_submit"] is False
    assert len(br["pages"]) == 7 and all(p["pass"] and not p["overflow"] for p in br["pages"])
    assert br["con88_page"]["pass"] is True
    for rel, expected_sha in br["source_sha256"].items():
        actual_sha = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert actual_sha == expected_sha, f"Browser pin mismatch on {rel}"

    audit = json.loads((ROOT / "evidence/focus_sites_20261026_audit.json").read_text(encoding="utf-8"))
    assert audit["cached_tiff_inventory_count"] == 44
    assert len(audit["cached_tiff_inventory"]) == 44
    by_cache = {r["cache_filename"]: r for r in audit["cached_tiff_inventory"]}
    # IR-88-D634DE37-01: GEMSDOE27 H31-1 DRCG-WL
    h31_1 = by_cache["GEMSDOE27__gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif"]
    assert h31_1["sha256"].startswith("2c002b02")
    assert h31_1["positive_pixels"] == 37654
    assert h31_1["vs_gemsdoe88_registry"]["dense_17gemdoe_3px_forward_overlap"] == 1.0
    # IR-88-D634DE37-02: GEMSDOE33 A33-R2-HMDT (33,616/42,000 dots outside footprint, 108 on catalogue)
    hmdt = by_cache["GEMSDOE33__gemsdoe33-a33-r2-hmdt-20261026-hmdt-unique-zeros.tif"]
    assert hmdt["sha256"].startswith("8d144302")
    assert hmdt["positive_pixels_total"] == 42000
    assert hmdt["positive_pixels_outside_footprint"] == 33616
    assert hmdt["positive_pixels"] == 8384
    assert hmdt["positive_pixels_on_catalogue"] == 108
    assert hmdt["nn_min_px"] == 1.0

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index_html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    exec_html = (ROOT / "docs/executive-summary.html").read_text(encoding="utf-8")
    for site in FOCUS_SITES:
        assert site in readme
        assert site in index_html
        assert site in exec_html
    for flag in ("IR-88-D634DE37-01", "IR-88-D634DE37-02"):
        assert flag in readme
        assert flag in index_html
        assert flag in exec_html
