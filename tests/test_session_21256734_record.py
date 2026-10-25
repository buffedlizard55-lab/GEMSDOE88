"""Regression guards for session 21256734 (-O validator/forensics hardening, cross-fleet screen, and run card)."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import py_compile
import re
import subprocess
import sys
import warnings

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HARDENED_SCRIPTS = (
    "scripts/validate_cxl88.py",
    "scripts/validate_prism88.py",
    "scripts/validate_gthc88.py",
    "scripts/validate_kth88.py",
    "scripts/validate_vhgd88.py",
    "scripts/validate_concentration_releases.py",
    "scripts/audit_mass_ranking.py",
    "scripts/forensics_h33.py",
)

NEW_HYPOTHESIS_IDS = (
    "H88-ACDR",
    "H88-POFD",
    "H88-WDCS",
    "H88-OCST",
    "H88-OPERA-INSAR",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hardened_scripts_have_zero_bare_asserts_and_pin_reference_rasters() -> None:
    for rel in HARDENED_SCRIPTS:
        path = ROOT / rel
        assert path.is_file(), rel
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            py_compile.compile(str(path), doraise=True)
        assert caught == [], (rel, [str(w.message) for w in caught])

        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel)
        bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        assert bare_asserts == [], f"{rel} still contains bare assert statements at lines {bare_asserts}"
        if rel == "scripts/forensics_h33.py":
            assert "def verify_forensic_pins(" in source
        else:
            assert "def _require(" in source, f"{rel} missing _require() helper"
        assert "SHA256_SAMPLE_SUBMISSION" in source, f"{rel} missing sample_submission SHA-256 pin"
        assert "SHA256_EXISTING_FAULTS" in source, f"{rel} missing existing_faults SHA-256 pin"


def test_python_optimized_require_guard_cannot_be_stripped() -> None:
    cmd = [
        sys.executable,
        "-O",
        "-c",
        (
            "import sys; sys.path.insert(0, '.'); "
            "from scripts.validate_cxl88 import _require; "
            "ok = False\n"
            "try:\n"
            "    _require(False, 'must_fail_under_dash_O')\n"
            "except (AssertionError, RuntimeError) as exc:\n"
            "    ok = ('must_fail_under_dash_O' in str(exc))\n"
            "raise SystemExit(0 if ok else 1)"
        ),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr


@pytest.mark.skipif(
    not (ROOT / "data/bridge/sample_submission.tif").is_file()
    or not (ROOT / "data/bridge/existing_faults.tif").is_file(),
    reason="validation inputs are restored by scripts/restore_inputs.py --validation",
)
def test_hardened_validators_pass_and_missing_release_fails_closed_under_python_optimized_mode() -> None:
    for rel in (
        "scripts/validate_cxl88.py",
        "scripts/validate_prism88.py",
        "scripts/validate_gthc88.py",
        "scripts/validate_kth88.py",
        "scripts/validate_vhgd88.py",
    ):
        proc = subprocess.run(
            [sys.executable, "-O", rel],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"{rel} failed under python -O:\n{proc.stdout}\n{proc.stderr}"

    # CONCENTRATION15pct binary TIFF is absent from releases/; under -O it must still fail closed.
    conc = subprocess.run(
        [sys.executable, "-O", "scripts/validate_concentration_releases.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert conc.returncode != 0
    assert "missing or SHA-mismatched" in conc.stderr


def test_forensics_h33_pins_and_sentinel_guard() -> None:
    import scripts.forensics_h33 as fh
    from scripts.restore_inputs import VALIDATION_GROUPS

    assert fh.SHA256_TRAINING_FEATURES == "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
    expected = {dst: digest for group in VALIDATION_GROUPS for _, dst, digest in group[3]}
    for _label, fn, _claim in fh.LINEAGE:
        assert f"data/registry/{fn}" in expected
    assert callable(fh.run_forensics)

    src = Path(fh.__file__).read_text(encoding="utf-8")
    assert "allow_nan=False" in src
    assert "1e30" in src


def test_session_21256734_run_card_and_leaderboard_snapshot_parity() -> None:
    reg_card = ROOT / "registry/session_21256734_run_card.json"
    doc_card = ROOT / "docs/data/session_21256734_run_card.json"
    evd_card = ROOT / "evidence/session_21256734_run_card.json"
    assert reg_card.is_file() and doc_card.is_file() and evd_card.is_file()
    raw = reg_card.read_text(encoding="utf-8")
    assert raw == doc_card.read_text(encoding="utf-8")
    assert raw == evd_card.read_text(encoding="utf-8")

    card = json.loads(raw)
    json.dumps(card, allow_nan=False)
    assert card["session"] == "21256734"
    assert card["branch"] == "arena/21256734-gemsdoe88"
    assert card["status"] == "DUPLICATE_STOP"
    assert card["decision"] == "DUPLICATE_STOP"
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["ok_to_download_new_tif"] is False
    assert card["ok_to_download_existing_research_tifs"] is True
    assert card["new_rasters_generated"] == 0
    assert card["experiments_run"] == 0
    assert card["weekly_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert len(card["submission_name"]) == card["submission_name_length"] <= 140
    assert len(card["submission_note"]) == card["submission_note_length"] <= 140
    assert [row["id"] for row in card["ranked_untried_hypotheses"]] == list(NEW_HYPOTHESIS_IDS)

    evd_lb = ROOT / "evidence/leaderboard_official_snapshot_21256734_20261025.json"
    doc_lb = ROOT / "docs/data/leaderboard_official_snapshot_21256734_20261025.json"
    assert evd_lb.is_file() and doc_lb.is_file()
    lb_raw = evd_lb.read_text(encoding="utf-8")
    assert lb_raw == doc_lb.read_text(encoding="utf-8")
    assert _sha256(evd_lb) == card["h33_and_leaderboard_reconciliation"]["live_leaderboard_snapshot_sha256"]

    lb = json.loads(lb_raw)
    json.dumps(lb, allow_nan=False)
    rows = lb["rows_1_to_50"]
    assert len(rows) == 50
    assert rows[0]["rank"] == 1
    assert rows[0]["participant"] == "xiaofanhu"
    assert rows[0]["public_dw_tversky"] == 0.4413
    assert rows[0]["submissions"] == 30
    assert rows[7]["rank"] == 8
    assert rows[7]["participant"] == "DARD"
    assert rows[7]["public_dw_tversky"] == 0.3398
    assert rows[7]["submissions"] == 27
    assert rows[-1]["rank"] == 50
    assert rows[-1]["public_dw_tversky"] == 0.2818


def test_session_21256734_docs_mirrors_links_and_untried_novelty() -> None:
    for stem in ("session-21256734-review.md", "session-21256734-hypotheses.md"):
        r_path = ROOT / "research" / stem
        d_path = ROOT / "docs/research" / stem
        assert r_path.is_file() and d_path.is_file()
        text = r_path.read_text(encoding="utf-8")
        assert text == d_path.read_text(encoding="utf-8")
        assert "../" not in text

    link_re = re.compile(r"\[[^\]]+\]\(([^)#\s]+)(?:#[^)]*)?\)")
    for md_rel in (
        "research/session-21256734-review.md",
        "research/session-21256734-hypotheses.md",
        "docs/research/session-21256734-review.md",
        "docs/research/session-21256734-hypotheses.md",
        "NEW_HYPOTHESES.md",
        "IRREGULARITIES.md",
        "SLOT_PLAN.md",
        "docs/SUBMIT.md",
    ):
        md_path = ROOT / md_rel
        md_top = md_path.read_text(encoding="utf-8").split("<details>", 1)[0]
        for href in link_re.findall(md_top):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (md_path.parent / href).resolve()
            assert resolved.is_file(), f"Broken relative link {href!r} in {md_rel}"

    nh_top = (ROOT / "NEW_HYPOTHESES.md").read_text(encoding="utf-8").split("<details>", 1)[0]
    for hid in NEW_HYPOTHESIS_IDS:
        assert hid in nh_top

    code_paths = list((ROOT / "src").rglob("*.py")) + list((ROOT / "vendor").rglob("*.py"))
    code_blob = "\n".join(p.read_text(encoding="utf-8") for p in code_paths).lower()
    for token in ("acdr", "pofd", "wdcs", "ocst", "opera_insar", "parker_oldenburg", "guspi"):
        assert token not in code_blob, f"Unexpected existing implementation match for {token}"

    irreg = (ROOT / "IRREGULARITIES.md").read_text(encoding="utf-8")
    for ir_id in (
        "IR-88-21256734-01",
        "IR-88-21256734-02",
        "IR-88-21256734-03",
        "IR-88-21256734-04",
        "IR-88-21256734-05",
    ):
        assert ir_id in irreg

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for rel in (
        "research/session-21256734-review.md",
        "research/session-21256734-hypotheses.md",
        "registry/session_21256734_run_card.json",
        "evidence/leaderboard_official_snapshot_21256734_20261025.json",
    ):
        assert rel in readme
        assert (ROOT / rel).is_file()

    browser_pins = json.loads((ROOT / "evidence/session_693b10af_browser_check.json").read_text(encoding="utf-8"))
    assert len(browser_pins["source_sha256"]) == 14
    regenerated = {
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/data/download_audit.json",
        "evidence/download_audit.json",
        "docs/data/hypothesis_queue.json",
    }
    for rel, expected_sha in browser_pins["source_sha256"].items():
        if rel in regenerated:
            continue
        assert _sha256(ROOT / rel) == expected_sha, f"Pinned browser file drifted: {rel}"


def test_post_merge_ir06_and_pgtd_guard() -> None:
    irreg = (ROOT / "IRREGULARITIES.md").read_text(encoding="utf-8")
    assert "IR-88-21256734-06" in irreg

    pgtd_runner = (ROOT / "scripts/run_pgtd88_experiment.py").read_text(encoding="utf-8")
    assert "enforce_generation_preflight()" in pgtd_runner
    assert "print(_gi())" not in pgtd_runner
