"""Regression guards for session 838cc402 post-PR-#152 repairs, archive parity, and run card."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import py_compile
import re
import subprocess
import sys
import warnings
import zipfile

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_submit_md_has_no_withdrawn_lane_clearance_and_matches_audit_count() -> None:
    submit_text = (ROOT / "docs/SUBMIT.md").read_text(encoding="utf-8")
    top_section = submit_text.split("<details>", 1)[0]
    audit = json.loads((ROOT / "docs/data/download_audit.json").read_text(encoding="utf-8"))
    total = audit["total_published_tiff_count"]
    passed = audit["total_research_download_pass_count"]

    assert "(lane H88-SDTL)" not in top_section
    assert "DUPLICATE_STOP" in top_section
    assert "ok_to_submit: false" in top_section
    assert "IR-88-B4DFA10C-08" in top_section
    assert f"**{passed}/{total}**" in top_section
    assert "**45/45**" not in top_section


def test_submissions_directory_archive_integrity_unconditional() -> None:
    sub_dir = ROOT / "submissions"
    symlinks = [p.name for p in sub_dir.iterdir() if p.is_symlink()]
    assert symlinks == []

    tifs = sorted(sub_dir.glob("*.tif"))
    zips = sorted(sub_dir.glob("*.zip"))
    assert len(tifs) == 20
    assert {p.stem for p in tifs} == {p.stem for p in zips}

    for tif in tifs:
        assert "DO-NOT-SUBMIT" in tif.name
        zp = tif.with_suffix(".zip")
        assert "DO-NOT-SUBMIT" in zp.name
        with zipfile.ZipFile(zp) as zf:
            members = zf.namelist()
            assert members == [tif.name], (zp.name, members)
            assert zf.read(tif.name) == tif.read_bytes(), zp.name

    repair = json.loads((ROOT / "evidence/session_838cc402_archive_repair.json").read_text(encoding="utf-8"))
    assert repair["new_tiffs_generated"] == 0
    item = repair["repairs"][0]
    assert _sha256(ROOT / item["file"]) == item["tif_sha256_unchanged"]
    assert _sha256(ROOT / item["archive"]) == item["new_zip_sha256"]
    assert _sha256(ROOT / item["source_already_repaired_archive"]) == item["new_zip_sha256"]


@pytest.mark.skipif(
    not (ROOT / "data/bridge/sample_submission.tif").is_file()
    or not (ROOT / "data/bridge/existing_faults.tif").is_file(),
    reason="validation inputs are restored by scripts/restore_inputs.py --validation",
)
def test_submissions_directory_dual_decoder_format_audit() -> None:
    from scripts.audit_downloads import audit_one

    sample = ROOT / "data/bridge/sample_submission.tif"
    with rasterio.open(sample) as sds:
        footprint = np.isfinite(sds.read(1))
    with rasterio.open(ROOT / "data/bridge/existing_faults.tif") as cds:
        catalogue = cds.read(1) > 0

    tifs = sorted((ROOT / "submissions").glob("*.tif"))
    assert len(tifs) == 20
    for tif in tifs:
        row = audit_one(tif, sample, catalogue, footprint)
        assert row["research_download_ok"] is True, (tif.name, row)
        assert row["ok_to_submit"] is False, (tif.name, row)
        assert row["validator_output"]["ok"] is True, (tif.name, row)
        assert row["zip_one_byte_identical_tif"] is True, (tif.name, row)
        assert row["positive_on_catalogue"] == 0, (tif.name, row)
        assert row["positive_outside_footprint"] == 0, (tif.name, row)


def test_current_hypotheses_reconcile_post_mmrX_queue_and_pgtd_execution() -> None:
    top = (ROOT / "NEW_HYPOTHESES.md").read_text(encoding="utf-8").split("<details>", 1)[0]
    assert "four remaining post-MMRX proposals" in top
    assert "H88-MMRX" in top and "0.188378" in top and "0.797578" in top
    assert "H88-PGTD" in top and "subsequently generated after its runner" in top
    assert "enforce_generation_preflight()" in (ROOT / "scripts/run_pgtd88_experiment.py").read_text()
    for hid in ("H88-SPRV", "H88-CBBC", "H88-TAWA", "H88-MT3D-GDR"):
        assert hid in top
    assert "1. **`H88-SPRV`**" in top and "2. **`H88-CBBC`**" in top

    for fname in ("session-838cc402-review.md", "session-838cc402-hypotheses.md"):
        repo_copy = ROOT / "research" / fname
        pages_copy = ROOT / "docs/research" / fname
        assert repo_copy.is_file() and pages_copy.is_file()
        assert repo_copy.read_bytes() == pages_copy.read_bytes()


def test_publish_sdtl88_has_no_invalid_escape_warnings_and_fails_closed(tmp_path: Path) -> None:
    target = ROOT / "scripts/publish_sdtl88.py"
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        warnings.simplefilter("error", SyntaxWarning)
        py_compile.compile(str(target), cfile=str(tmp_path / "publish_sdtl88.pyc"), doraise=True)

    if (ROOT / "data/registry/dense_17gemdoe.tif").is_file():
        proc = subprocess.run(
            [sys.executable, str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "DUPLICATE_STOP" in (proc.stdout + proc.stderr)


def test_session_838cc402_run_cards_and_leaderboard_snapshot_are_fail_closed() -> None:
    reg = json.loads((ROOT / "registry/session_838cc402_run_card.json").read_text(encoding="utf-8"))
    web = json.loads((ROOT / "docs/data/session_838cc402_run_card.json").read_text(encoding="utf-8"))
    ev = json.loads((ROOT / "evidence/session_838cc402_run_card.json").read_text(encoding="utf-8"))
    assert reg == web == ev

    assert reg["session"] == "838cc402"
    assert reg["decision"] == "DUPLICATE_STOP"
    assert reg["verdict"] == "negative"
    assert reg["ok_to_submit"] is False
    assert reg["ok_to_download_new_tif"] is False
    assert reg["new_rasters_generated"] == 0
    assert reg["experiments_run"] == 0
    assert reg["weekly_slots_used"] == 0
    assert reg["raster_sha256"] is None
    assert reg["holdout_dti"]["dti"] is None
    assert reg["holdout_dti"]["ci95"] is None
    assert 0 < len(reg["submission_name"]) == reg["submission_name_length"] <= 140
    assert 0 < len(reg["submission_note"]) == reg["submission_note_length"] <= 140
    assert "DO NOT SUBMIT" in reg["submission_note"]
    assert [row["id"] for row in reg["ranked_untried_hypotheses"]] == [
        "H88-SPRV",
        "H88-PGTD",
        "H88-CBBC",
        "H88-TAWA",
        "H88-MT3D-GDR",
    ]

    lb_ev = json.loads((ROOT / "evidence/leaderboard_official_snapshot_838cc402_20261025.json").read_text(encoding="utf-8"))
    lb_web = json.loads((ROOT / "docs/data/leaderboard_official_snapshot_838cc402_20261025.json").read_text(encoding="utf-8"))
    assert lb_ev == lb_web
    rows = lb_ev["rows_1_to_50"]
    assert len(rows) == 50
    assert [r["rank"] for r in rows] == list(range(1, 51))
    scores = [r["public_dw_tversky"] for r in rows]
    assert all(scores[i] >= scores[i + 1] for i in range(49))
    assert scores[0] == 0.4413 and scores[-1] == 0.2818
    assert lb_ev["checks"]["rows_matching_user_claim_0_3195"] == 0
    assert lb_ev["checks"]["rows_matching_user_claim_0_2778"] == 0


def test_relative_links_in_session_838cc402_documents_resolve() -> None:
    link_re = re.compile(r"\[[^\]]+\]\(([^)#?\s]+)(?:#[^)]*)?\)")
    targets = [
        ROOT / "docs/SUBMIT.md",
        ROOT / "research/session-838cc402-review.md",
        ROOT / "docs/research/session-838cc402-review.md",
        ROOT / "research/session-838cc402-hypotheses.md",
        ROOT / "docs/research/session-838cc402-hypotheses.md",
    ]
    for md_path in targets:
        text = md_path.read_text(encoding="utf-8")
        for href in link_re.findall(text):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (md_path.parent / href).resolve()
            assert resolved.is_file(), f"Broken relative link {href!r} in {md_path}"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for rel in (
        "research/session-838cc402-review.md",
        "research/session-838cc402-hypotheses.md",
        "registry/session_838cc402_run_card.json",
        "evidence/leaderboard_official_snapshot_838cc402_20261025.json",
        "evidence/session_838cc402_archive_repair.json",
    ):
        assert rel in readme
        assert (ROOT / rel).is_file()

    irreg = (ROOT / "IRREGULARITIES.md").read_text(encoding="utf-8")
    for ir_id in ("IR-88-838C-01", "IR-88-838C-02", "IR-88-838C-03", "IR-88-838C-04", "IR-88-838C-05"):
        assert ir_id in irreg
