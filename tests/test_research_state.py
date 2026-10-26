"""Prevent stale untested claims and legacy score/promotion regressions.

These are metadata/source tests, not geological experiments or new predictions.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

from packaging.requirements import Requirement
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import audit_research_state as audit  # noqa: E402


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


@pytest.fixture
def queue_root(tmp_path):
    for directory in ("src/gems88", "vendor/gems57"):
        shutil.copytree(ROOT / directory, tmp_path / directory, ignore=shutil.ignore_patterns("__pycache__"))
    for pattern in ("run_*.py", "build_*.py", "generate_*.py"):
        (tmp_path / "scripts").mkdir(exist_ok=True)
        for source in (ROOT / "scripts").glob(pattern):
            shutil.copyfile(source, tmp_path / "scripts" / source.name)
    queue = json.loads((ROOT / audit.QUEUE).read_text())
    for relative in (audit.QUEUE, "docs/data/hypothesis_queue.json", *[r["run_card"] for r in queue["already_evaluated"]]):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def replace_queue(root, queue):
    for relative in (audit.QUEUE, "docs/data/hypothesis_queue.json"):
        save(root / relative, queue)


def test_current_queue_is_source_bound_and_does_not_recommend_evaluated_lanes():
    queue = audit.inspect_queue(ROOT)
    assert queue["conditional_first_choice"] == "H88-SPR"
    assert {p["id"] for p in queue["proposals"]} == {"H88-SPR", "H88-AWA", "H88-CBC"}
    assert {p["id"] for p in queue["already_evaluated"]} == {"H88-MMRX", "H88-MTAS", "H88-MFS", "H88-PGTD", "H88-CON88", "H88-MSHI", "H88-GEORAD", "H88-VVRD"}
    assert queue["ok_to_submit"] is queue["generation_authorized"] is False


@pytest.mark.parametrize("mutation", ["rank", "boolean-rank", "repeat", "tested", "external", "missing-mimic", "unbound-input", "approve", "snapshot", "first", "bad-pin", "bad-band", "removed-retired", "retired-tensor-alias"])
def test_queue_rejects_stale_or_incomplete_status(queue_root, mutation):
    queue = json.loads((queue_root / audit.QUEUE).read_text())
    if mutation == "rank":
        queue["proposals"][0]["rank"] = 5
    elif mutation == "boolean-rank":
        queue["proposals"][0]["rank"] = True
    elif mutation == "bad-pin":
        first = next(iter(queue["input_pins"]))
        queue["input_pins"][first] = "not-a-sha256"
    elif mutation == "bad-band":
        queue["proposals"][0]["layers"][0]["bands"] = [True, -1]
    elif mutation == "removed-retired":
        queue["already_evaluated"] = []
    elif mutation == "retired-tensor-alias":
        queue["proposals"][0]["id"] = "H88-GTD"
        queue["conditional_first_choice"] = "H88-GTD"
    elif mutation == "repeat":
        queue["proposals"][0]["id"] = "H88-MMRX"
        queue["conditional_first_choice"] = "H88-MMRX"
    elif mutation == "tested":
        queue["proposals"][0]["status"] = "EVALUATED"
    elif mutation == "external":
        queue["proposals"][0]["new_external_data_required"] = True
    elif mutation == "missing-mimic":
        queue["proposals"][0]["non_fault_mimic"] = ""
    elif mutation == "unbound-input":
        queue["proposals"][0]["layers"][0]["file"] = "data/never-obtained.tif"
    elif mutation == "approve":
        queue["generation_authorized"] = True
    elif mutation == "snapshot":
        queue["source_snapshot"]["sha256"] = "0" * 64
    else:
        queue["conditional_first_choice"] = "H88-MMRX"
    replace_queue(queue_root, queue)
    with pytest.raises(ValueError):
        audit.inspect_queue(queue_root)


def test_source_changes_invalidate_the_review_without_constructing_features(queue_root):
    source = queue_root / "src/gems88/mmrx.py"
    source.write_text(source.read_text() + "\n# concurrent implementation change\n")
    with pytest.raises(ValueError, match="snapshot/status drift"):
        audit.inspect_queue(queue_root)


def test_site_queue_mirror_cannot_diverge(queue_root):
    (queue_root / "docs/data/hypothesis_queue.json").write_text("{}\n")
    with pytest.raises(ValueError, match="published research queue"):
        audit.inspect_queue(queue_root)


def test_requiring_inputs_never_uses_a_stored_availability_claim(queue_root):
    with pytest.raises(ValueError, match="missing or escaped"):
        audit.inspect_queue(queue_root, check_inputs=True)


def test_evaluated_card_is_pinned_and_must_stay_negative(queue_root):
    queue = json.loads((queue_root / audit.QUEUE).read_text())
    row = queue["already_evaluated"][0]
    path = queue_root / row["run_card"]
    card = json.loads(path.read_text())
    card["verdict"] = "promote"
    save(path, card)
    row["run_card_sha256"] = audit.sha(path)
    replace_queue(queue_root, queue)
    with pytest.raises(ValueError, match="identity/verdict drift"):
        audit.inspect_queue(queue_root)


@pytest.mark.parametrize("path", ["../outside.json", "/etc/passwd"])
def test_pins_cannot_escape_the_repository(tmp_path, path):
    with pytest.raises(ValueError):
        audit.pinned_file(tmp_path, path, "0" * 64)


@pytest.fixture
def legacy_root(tmp_path):
    card = json.loads((ROOT / audit.LEGACY_CARDS[0]).read_text())
    files = (*audit.LEGACY_CARDS, audit.CORRECTION, card["submission"]["file"],
             card["submission"]["repo_copy"], card["submission"]["zip_file"])
    for relative in files:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def test_historical_ghmd_preserves_bytes_without_promoting_or_inventing_receipts():
    result = audit.inspect_legacy(ROOT)
    assert result["organizer_confirmed_score"] is None
    assert result["historical_only"] is result["mirrors_identical"] is True
    assert result["ok_to_submit"] is result["prediction_bytes_changed"] is False


@pytest.mark.parametrize("mutation", ["verdict", "organizer", "historical", "unique", "allow", "marker", "raster"])
def test_historical_metadata_cannot_revive_a_withdrawn_clearance(legacy_root, mutation):
    card = json.loads((legacy_root / audit.LEGACY_CARDS[0]).read_text())
    if mutation == "verdict":
        card["verdict"] = "promote"
    elif mutation == "organizer":
        card["evidence_status"]["incumbent_organizer_confirmed_live_score"] = 0.2778
    elif mutation == "historical":
        card["historical_only"] = False
    elif mutation == "unique":
        card["uniqueness"]["unique"] = True
    elif mutation == "allow":
        card["ok_to_submit"] = True
    elif mutation == "marker":
        card["submission"]["file"] = card["submission"]["file"].replace("-DO-NOT-SUBMIT", "")
    else:
        p = legacy_root / card["submission"]["file"]
        p.write_bytes(p.read_bytes() + b"changed")
    correction = json.loads((legacy_root / audit.CORRECTION).read_text())
    # Rebind metadata hashes, proving semantic checks do not trust hashes alone.
    for relative in audit.LEGACY_CARDS:
        save(legacy_root / relative, card)
        correction["corrected_metadata_sha256"][relative] = audit.sha(legacy_root / relative)
    save(legacy_root / audit.CORRECTION, correction)
    with pytest.raises(ValueError):
        audit.inspect_legacy(legacy_root)


def test_legacy_pipeline_cannot_recreate_old_false_score_label_or_promotion():
    tree = ast.parse((ROOT / "scripts/run_gems88_pipeline.py").read_text())
    assignment = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "run_card" for t in n.targets))
    values = {key.value: value for key, value in zip(assignment.keys, assignment.values)}
    assert ast.literal_eval(values["verdict"]) == "negative"
    assert ast.literal_eval(values["ok_to_submit"]) is False
    labels = {key.value: value for key, value in zip(values["evidence_status"].keys, values["evidence_status"].values)}
    assert ast.literal_eval(labels["incumbent_organizer_confirmed_live_score"]) is None
    assert ast.literal_eval(labels["incumbent_user_reported_claim"]) == 0.2778


def test_audit_success_is_not_submission_clearance(monkeypatch, capsys):
    queue = {"source_snapshot": {}, "conditional_first_choice": "H88-SPR", "proposals": [], "already_evaluated": []}
    monkeypatch.setattr(audit, "inspect_queue", lambda *a, **kw: copy.deepcopy(queue))
    monkeypatch.setattr(audit, "inspect_legacy", lambda *a: {"ok_to_submit": False})
    assert audit.main([]) == 0
    assert audit.main(["--require-submit"]) == 2
    assert '"ok_to_submit": false' in capsys.readouterr().out


def test_audit_error_cannot_be_success(monkeypatch, capsys):
    def broken(*args, **kwargs):
        raise ValueError("bad source pin")
    monkeypatch.setattr(audit, "inspect_queue", broken)
    assert audit.main(["--require-submit"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "AUDIT_ERROR" and output["ok_to_submit"] is False


def test_cpu_dependency_constraints_cover_every_direct_requirement():
    requirements = (ROOT / "requirements.txt").read_text().splitlines()
    assert "-c requirements-constraints.txt" in requirements
    pins = [Requirement(line) for line in (ROOT / "requirements-constraints.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")]
    by_name = {p.name.lower(): p for p in pins}
    for line in requirements:
        if line.strip() and not line.startswith(("#", "-")):
            direct = Requirement(line)
            specifiers = list(by_name[direct.name.lower()].specifier)
            assert len(specifiers) == 1 and specifiers[0].operator == "=="
            assert specifiers[0].version in direct.specifier
    assert str(by_name["rasterio"].specifier) == "==1.4.4"
    assert str(by_name["numpy"].specifier) == "==2.3.4"


def test_all_ci_paths_check_research_state_and_dependency_constraints():
    for name in ("checks.yml", "ci.yml", "pages.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        assert "python scripts/audit_research_state.py\n" in text
        assert "python scripts/audit_research_state.py --require-submit" in text
        assert "requirements-constraints.txt" in text


def test_research_page_queue_is_generated_from_the_same_reviewed_manifest():
    from scripts import render_decision
    text = (ROOT / "docs/research.html").read_text()
    assert render_decision.replace_block(text, render_decision.render_research_queue(ROOT),
                                         render_decision.QUEUE_START, render_decision.QUEUE_END) == text
    current = text.split(render_decision.QUEUE_START, 1)[1].split(render_decision.QUEUE_END, 1)[0]
    assert "already have historical negative execution records" in current
    assert "source-reviewed" in current
    for lane in ("H88-SPR", "H88-AWA", "H88-CBC"):
        assert lane in current
    assert "Restore matching magnetic markers" not in current


def test_session_record_is_one_honest_negative_without_an_invented_candidate():
    cards = [ROOT / relative for relative in ("registry/session_693b10af_run_card.json",
              "evidence/session_693b10af_run_card.json", "docs/data/session_693b10af_run_card.json")]
    assert len({p.read_bytes() for p in cards}) == 1
    card = json.loads(cards[0].read_text())
    assert card["base_commit"] == "d7f7502d93dc5e5d9685ba90d7374d71a2bc2a68"
    assert card["branch"] == "arena/693b10af-gemsdoe88"
    assert card["verdict"] == "negative" and card["status"] == "DUPLICATE_STOP"
    assert card["raster_file"] is card["raster_sha256"] is card["organizer_confirmed_score"] is None
    assert card["holdout_dti"]["dti"] is card["holdout_dti"]["ci95"] is None
    assert card["validator_output"]["no_nan_inside_footprint"] is None
    assert card["ok_to_submit"] is card["approved_for_weekly_slot"] is card["new_tif_generated"] is False
    assert card["budget"]["geological_experiments_run"] == card["weekly_slots_used"] == 0
    assert len(card["submission_note"]) == card["submission_note_characters"] <= 140
    assert card["correlation_overlap_vs_registry"]["universal_overlap_lower_bound"] == 1.0
    assert card["archived_research_download"]["new_in_this_session"] is False
    assert card["source_scope"]["all_92_sites_freshly_scraped"] is False
    assert card["source_scope"]["leaderboard_verified_this_session"] is False
    snapshot = card["research_queue"]["source_snapshot"]
    assert snapshot["files"] >= 150 and len(snapshot["sha256"]) == 64
    int(snapshot["sha256"], 16)  # historical snapshot; do not rewrite for future code
    for stem in ("review", "hypotheses"):
        path = f"research/session-693b10af-{stem}.md"
        assert (ROOT / path).read_bytes() == (ROOT / "docs" / path).read_bytes()


def test_fresh_software_receipts_are_reproducible_and_cannot_promote():
    for suffix in ("cpu_reproduction", "gate_check"):
        name = f"session_693b10af_{suffix}.json"
        assert (ROOT / "evidence" / name).read_bytes() == (ROOT / "docs/data" / name).read_bytes()
        receipt = json.loads((ROOT / "evidence" / name).read_text())
        assert receipt["status"] == "PASS" and receipt["ok_to_submit"] is False
        assert receipt["geological_experiments_run"] == 0
    gates = json.loads((ROOT / "evidence/session_693b10af_gate_check.json").read_text())
    assert len(gates["checks"]) == 53
    assert gates["expected_negative_count"] == 26
    assert all(r["pass"] and r["exit_code"] == r["expected_exit"] for r in gates["checks"])
    assert any(r["command"] == "-O scripts/audit_research_state.py --require-submit" for r in gates["checks"])
    cpu = json.loads((ROOT / "evidence/session_693b10af_cpu_reproduction.json").read_text())
    assert cpu["fresh_venv"] is True and cpu["hash_verification_bypassed"] is False
    assert cpu["pip_check"] == cpu["unchanged_byte_exact_h33_rebuild_test"]["status"] == "PASS"
    assert cpu["rasterio"] == "1.4.4" and cpu["gdal"] == "3.10.3" and cpu["numpy"] == "2.3.4"
    pinned = dict(line.split("==", 1) for line in (ROOT / "requirements-constraints.txt").read_text().splitlines()
                  if line and not line.startswith("#"))
    normalized = lambda s: s.lower().replace("_", "-")
    actual = {normalized(p["name"]): p["version"] for p in cpu["installed_distributions"]}
    assert actual == {normalized(name): version for name, version in pinned.items()}
    assert all(len(p["sha256"]) == 64 for p in cpu["installed_distributions"])


@pytest.mark.parametrize("relative", ["src/gems88/proposed/__init__.py", "vendor/gems57/newphysics/contrast.py", "scripts/run_additional_lane.py"])
def test_new_nested_model_or_candidate_files_also_invalidate_the_queue(queue_root, relative):
    source = queue_root / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# unreviewed implementation\n")
    with pytest.raises(ValueError, match="snapshot/status drift"):
        audit.inspect_queue(queue_root)


def test_model_fingerprint_cannot_read_a_source_symlink_outside_the_repository(queue_root):
    source = queue_root / "src/gems88/mmrx.py"
    source.unlink()
    source.symlink_to(ROOT / "src/gems88/mmrx.py")
    with pytest.raises(ValueError, match="missing or escaped"):
        audit.model_source_snapshot(queue_root)
