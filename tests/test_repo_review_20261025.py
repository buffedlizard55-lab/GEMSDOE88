from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88.review import (  # noqa: E402
    HYPOTHESES,
    hypothesis_queue,
    safe_note,
    validate_hypothesis_queue,
)


def test_ranked_queue_has_four_method_level_candidates_with_novelty_limits() -> None:
    queue = hypothesis_queue()
    validate_hypothesis_queue(queue)
    assert len(queue) == 4
    assert [row["rank"] for row in queue] == [1, 2, 3, 4]
    assert [row["id"] for row in queue] == [
        "MAGNETIC-MARKER-RESTORATION",
        "DRAINAGE-VETOED-SCARP-PROFILE-RESTORATION",
        "TERRAIN-MATCHED-ALTERATION-WIDTH-ASYMMETRY",
        "CONDUCTIVE-BASIN-BREACH-CONTINUITY",
    ]
    assert all(row["status"] == "UNTESTED" for row in queue)
    assert all(row["layers"] for row in queue)
    assert all(row["non_fault_mimic"] for row in queue)
    assert all("related" in row["novelty_scope"].lower() for row in queue)
    assert all("not a claim of global" in row["novelty_scope"].lower() for row in queue)
    assert len(HYPOTHESES) == len(queue)


def test_safe_note_rejects_overlong_text_without_truncation() -> None:
    note = "x" * 140
    assert safe_note(note) == note
    with pytest.raises(ValueError):
        safe_note("x" * 141)
    with pytest.raises(ValueError):
        safe_note("")


def test_published_review_is_fail_closed_and_copies_match() -> None:
    evidence = json.loads((ROOT / "evidence/repo_review_20261025.json").read_text())
    pages = json.loads((ROOT / "docs/data/repo_review_20261025.json").read_text())
    assert evidence == pages
    assert evidence["schema"] == "gems88.repo-review-20261025.v2"
    assert evidence["review_status"] == "DUPLICATE_STOP"
    assert evidence["new_tif"]["generated"] is False
    assert evidence["submission"]["ok_to_submit"] is False
    assert evidence["submission"]["weekly_slots_used"] == 0
    assert evidence["holdout"]["status"].startswith("NOT RUN")
    assert evidence["holdout"]["dti"] is None
    assert evidence["preplacement_registry_audit"]["universal_overlap_blocker"] is True
    assert evidence["preplacement_registry_audit"]["covered_allowed_fraction"] == 1.0
    status = json.loads((ROOT / "docs/status.json").read_text())
    assert status["current_review"] == "data/repo_review_20261025.json"
    assert status["current_review_status"] == "DUPLICATE_STOP"
    assert status["new_tif_generated"] is False
    assert evidence["assigned_method_lane"]["id"] is None
    assert len(evidence["hypothesis_queue"]) == 4
    assert evidence["hypothesis_novelty_scope"]["global_novelty_certified"] is False
    assert evidence["protocol_compliance"]["assigned_method_lane"] is None
    assert evidence["protocol_compliance"]["surface_abs_spearman_stop_threshold"] == 0.90
    assert evidence["protocol_compliance"]["final_dot_forward_overlap_stop_threshold"] == 0.70
    assert evidence["experiment_budget"]["experiments_this_review"] == 0
    assert len(evidence["review_passes"]) == 3


def test_historical_mtas_measurement_is_not_conflated_with_current_preflight():
    report = json.loads((ROOT / "evidence/repo_review_20261025.json").read_text())
    historical = report["historical_experiments"]["H88-MTAS"]
    assert historical["evidence_class"] == "HOLDOUT-DTI"
    assert historical["historical"] is True
    assert historical["evaluator_version"] == "gems57-pooled-hide-v2"
    assert historical["dti"] == pytest.approx(0.049577)
    assert historical["ci95"] == [0.044659, 0.054417]
    assert historical["withheld_positive_pixels"] == 22893
    assert historical["folds"] == 8
    assert historical["submission"]["organizer_confirmed_score"] is None
    assert historical["submission"]["ok_to_submit"] is False
    assert "did not rerun" in historical["not_current"]
    assert report["holdout"]["dti"] is None


def test_previous_queue_relabels_tested_or_overlapping_method_families():
    report = json.loads((ROOT / "evidence/repo_review_20261025.json").read_text())
    rows = {row["id"]: row for row in report["prior_queue_reconciliation"]}
    assert rows["H88-MTAS"]["corrected_status"] == "HISTORICALLY_TESTED"
    assert all(
        rows[key]["corrected_status"] == "RELATED_PRIOR_METHODS; GLOBAL_NOVELTY_NOT_ESTABLISHED"
        for key in ("H88-PRAN", "H88-FARC", "H88-TCONS", "H88-FLAC")
    )
    assert report["source_verification_summary"]["fresh_official_pages_fetched"] == 1
    fetched = "https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md"
    source = next(row for row in report["official_sources"] if row["id"] == "reference_solution")
    assert source["url"] == report["source_verification_summary"]["fetched_official_page"] == fetched


def test_current_readme_site_and_submit_page_do_not_promote_archived_files():
    readme = (ROOT / "README.md").read_text()
    submit = (ROOT / "docs/SUBMIT.md").read_text()
    research = (ROOT / "docs/research.html").read_text()
    sources = (ROOT / "docs/sources.html").read_text()
    assert "Submission-ready GeoTIFF: NONE" in readme
    assert "HGVC v4 clearance and local rename/upload advice are revoked" in readme
    assert "REVOKED" in submit and "43/43" in submit and "41/41" not in submit
    assert "MTAS HOLDOUT-DTI exists; the later preflight did not rerun it" in research
    assert "HOLDOUT-DTI 0.049577 [0.044659, 0.054417]" in research
    assert 'id="h33"' in research and 'id="hypotheses"' in research
    assert 'repo-review-dea470d9-20261025.md#h33' in research
    assert 'repo-review-dea470d9-20261025.md#hypotheses' in research
    report = (ROOT / "docs/research/repo-review-dea470d9-20261025.md").read_text()
    assert '<a id="h33"></a>' in report and '<a id="hypotheses"></a>' in report
    assert '<a id="sources-and-provenance"></a>' in report
    assert "repo-review-dea470d9-20261025.md#sources-and-provenance" in sources
    assert "No official web pages were freshly fetched in this review" not in sources
    assert "One official web page was freshly fetched" in sources
    assert "https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md" in sources
    assert "All 43 local research-format packages" in sources



@pytest.mark.skipif(
    not (ROOT / "data/bridge/sample_submission.tif").is_file(),
    reason="hash-pinned validation inputs are restored in CI or by restore_inputs.py",
)
def test_review_cli_require_submit_exits_two() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/review_repo_20261025.py"), "--require-submit"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert '"decision": "DUPLICATE_STOP"' in result.stdout
    assert '"ok_to_submit": false' in result.stdout
