"""Regression suite for session 78cfb743 repairs and negative run-card invariants."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import uniqueness  # noqa: E402
from gems88.review import (  # noqa: E402
    Hypothesis,
    executed_registry_lanes,
    live_untried_hypothesis_queue,
)
from scripts import audit_submissions_dir, check_site  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v4_public_wrapper_enforces_literal_gate_while_preserving_diagnostics():
    rows = [
        {
            "file": "dense_17gemdoe.tif",
            "spearman": 0.012,
            "forward_overlap": 1.0,
            "is_continuous_surface": True,
            "topn_overlap": 0.016,
        },
        {
            "file": "sparse_prior.tif",
            "spearman": 0.08,
            "forward_overlap": 0.22,
            "is_continuous_surface": False,
        },
    ]
    diag = uniqueness._representation_aware_diagnostics_v4(rows)
    public = uniqueness.binding_duplicate_decision_v4(rows)

    assert diag["verdict"] == "promote"
    assert diag["duplicate"] is False
    assert diag["rows"][0]["effective_dot_overlap"] == pytest.approx(0.016)
    assert diag["worst_effective_dot_overlap"] == pytest.approx(0.22)

    assert public["representation_aware_binding"] is False
    assert public["policy_correction"] == "IR-88-78CFB743-01"
    assert public["rows"][0]["effective_dot_overlap"] == pytest.approx(0.016)
    assert public["worst_effective_dot_overlap"] == pytest.approx(0.22)
    assert public["worst_literal_forward_overlap"] == pytest.approx(1.0)
    assert public["duplicate"] is True
    assert public["stop_required"] is True
    assert public["verdict"] == "negative"
    assert public["rows"][0]["fails_effective_dot_diagnostic"] is False
    assert public["rows"][0]["fails_dot"] is True

    vendor_pins = json.loads((ROOT / "registry/vendor_pins.json").read_text())
    template_pin = json.loads((ROOT / "registry/template_pin.json").read_text())
    actual_sha = _sha256(ROOT / "vendor/gems57/uniqueness.py")
    assert vendor_pins["sha256"]["uniqueness.py"] == actual_sha
    assert template_pin["files"]["uniqueness.py"] == actual_sha


def test_submissions_ibl_zip_member_preserves_do_not_submit_and_dir_audit_passes(tmp_path):
    ibl_tif = ROOT / "submissions/gems88-ibl88-basin-lattice-37654-20261024-zeros-DO-NOT-SUBMIT.tif"
    ibl_zip = ibl_tif.with_suffix(".zip")
    with zipfile.ZipFile(ibl_zip) as zf:
        assert zf.namelist() == [ibl_tif.name]
        assert zf.read(ibl_tif.name) == ibl_tif.read_bytes()

    report = audit_submissions_dir.audit_submissions_directory(ROOT)
    assert report["all_packages_safe"] is True
    assert report["tiff_count"] == report["zip_count"] == report["pass_count"] == 21
    assert report["protocol_eligible_count"] == 0

    # Verify audit_submissions_dir rejects an unmarked inner ZIP member.
    fake_sub = tmp_path / "submissions"
    fake_sub.mkdir()
    sample_tif = fake_sub / "sample-DO-NOT-SUBMIT.tif"
    sample_tif.write_bytes(ibl_tif.read_bytes())
    bad_zip = fake_sub / "sample-DO-NOT-SUBMIT.zip"
    with zipfile.ZipFile(bad_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("sample.tif", ibl_tif.read_bytes())
    bad_report = audit_submissions_dir.audit_submissions_directory(tmp_path)
    assert bad_report["all_packages_safe"] is False
    assert any("DO-NOT-SUBMIT" in err for err in bad_report["artifacts"][0]["errors"])

    # Verify sidecar and orphan-ZIP rejection too.
    with zipfile.ZipFile(bad_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(sample_tif.name, ibl_tif.read_bytes())
    (fake_sub / "sample-DO-NOT-SUBMIT.tif.aux.xml").write_text("<PAMDataset/>", encoding="utf-8")
    (fake_sub / "orphan-DO-NOT-SUBMIT.zip").write_bytes(bad_zip.read_bytes())
    sidecar_report = audit_submissions_dir.audit_submissions_directory(tmp_path)
    assert sidecar_report["all_packages_safe"] is False
    assert "orphan-DO-NOT-SUBMIT.zip" in sidecar_report["orphan_zips"]
    assert any("forbidden sidecar" in err for err in sidecar_report["top_level_errors"])


def test_mmrx88_run_card_mirror_and_validator():
    reg = json.loads((ROOT / "registry/mmrx88_run_card.json").read_text())
    web = json.loads((ROOT / "docs/data/mmrx88_run_card.json").read_text())
    assert reg == web
    assert reg["download"] is None and reg["zip_download"] is None
    assert reg["ok_to_download"] is False
    assert reg["ok_to_download_repo_archive_for_research_only"] is True
    assert reg["ok_to_submit"] is False and reg["verdict"] == "negative"

    if not (ROOT / "data/bridge/sample_submission.tif").is_file():
        pytest.skip("SHA-pinned validation inputs not restored in this checkout")
    ok = subprocess.run(
        [sys.executable, "scripts/validate_mmrx88.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
    blocked = subprocess.run(
        [sys.executable, "scripts/validate_mmrx88.py", "--require-submit"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 2


def test_site_guard_rejects_broken_or_escaping_docs_markdown_links(tmp_path):
    # The source/input auditor intentionally rejects paths escaping root.
    # Use a real isolated corpus, not external symlinks that fail before the
    # Markdown-link probe this test is intended to exercise.
    for directory in ("registry", "evidence", "research", "src", "vendor", "scripts", "submissions"):
        shutil.copytree(ROOT / directory, tmp_path / directory,
                        ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(ROOT / "run_card.json", tmp_path / "run_card.json")
    docs = tmp_path / "docs"
    docs.mkdir()
    for src in (ROOT / "docs").iterdir():
        dest = docs / src.name
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copyfile(src, dest)

    probe = docs / "research/probe.md"
    probe.write_text("Escaping [card](../../registry/mmrx88_run_card.json)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes docs/ Pages root"):
        check_site.main(tmp_path)

    probe.write_text("Broken [missing](../data/does_not_exist.json)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="broken local Markdown link"):
        check_site.main(tmp_path)

    probe.unlink()
    submit = docs / "SUBMIT.md"
    count = json.loads((docs / "data/download_audit.json").read_text())["total_published_tiff_count"]
    original = submit.read_text()
    needle = f"**{count}/{count}**"
    assert needle in original
    submit.write_text(original.replace(needle, "**0/0**", 1))
    with pytest.raises(ValueError, match="Submission guide inventory count is stale"):
        check_site.main(tmp_path)


def test_live_untried_hypothesis_queue_excludes_executed_lanes(monkeypatch):
    import gems88.review as review_mod

    executed = executed_registry_lanes(ROOT)
    assert {"H88-MTAS", "H88-MMRX", "H88-SDTL", "H88-BPWD", "H88-HGVC", "H88-PGTD"}.issubset(executed)
    queue = live_untried_hypothesis_queue(ROOT)
    assert [row["id"] for row in queue] == [
        "H88-FARC",
        "H88-EELG",
        "H88-PRAN",
        "H88-SESR",
        "H88-FLAC",
    ]
    assert not (executed & {row["id"] for row in queue})

    bad = (
        Hypothesis(
            1,
            "H88-MMRX",
            ("rtp",),
            "sig",
            "why",
            "mimic",
            "diff",
            "high",
            "low",
            "none",
        ),
        *review_mod.LIVE_UNTRIED_HYPOTHESES[1:],
    )
    monkeypatch.setattr(review_mod, "LIVE_UNTRIED_HYPOTHESES", bad)
    with pytest.raises(ValueError, match="collides with executed registry lanes"):
        live_untried_hypothesis_queue(ROOT)


def test_session_78cfb743_run_card_and_mirrors_are_consistent():
    reg = json.loads((ROOT / "registry/session_78cfb743_run_card.json").read_text())
    web = json.loads((ROOT / "docs/data/session_78cfb743_run_card.json").read_text())
    ev = json.loads((ROOT / "evidence/session_78cfb743_run_card.json").read_text())
    assert reg == web == ev
    assert reg["status"] == "DUPLICATE_STOP"
    assert reg["verdict"] == "negative"
    assert reg["ok_to_submit"] is False
    assert reg["ok_to_download_new_file"] is False
    assert reg["approved_for_weekly_slot"] is False
    assert reg["weekly_slots_used"] == 0
    assert reg["organizer_confirmed_score"] is None
    assert reg["raster_file"] is None and reg["raster_sha256"] is None
    assert reg["holdout_dti"]["dti"] is None and reg["holdout_dti"]["ci95"] is None
    assert 0 < len(reg["submission_name"]) <= 140
    assert 0 < len(reg["submission_note"]) == reg["submission_note_characters"] <= 140
    assert reg["software_review"]["three_passes_completed"] is True
    for stem in ("review", "hypotheses"):
        rel = f"research/session-78cfb743-{stem}.md"
        assert (ROOT / rel).read_bytes() == (ROOT / "docs" / rel).read_bytes()
        assert rel in (ROOT / "README.md").read_text()


def test_validate_lsc88_fails_closed_on_require_submit():
    if not (ROOT / "data/bridge/sample_submission.tif").is_file():
        pytest.skip("SHA-pinned validation inputs not restored in this checkout")
    ok = subprocess.run(
        [sys.executable, "scripts/validate_lsc88.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0, ok.stdout + ok.stderr
    blocked = subprocess.run(
        [sys.executable, "scripts/validate_lsc88.py", "--require-submit"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 2

