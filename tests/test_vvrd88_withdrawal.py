"""PR #200's unsupported VVRD deliverable is withdrawn, not a new release."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_withdrawal_mirrors_and_missing_measurements_are_honest():
    paths = [ROOT / p for p in (
        "registry/session_aef1337d_run_card.json",
        "docs/data/session_aef1337d_run_card.json",
        "evidence/vvrd88_withdrawal_20261026.json",
    )]
    assert len({p.read_bytes() for p in paths}) == 1
    card = json.loads(paths[0].read_text())
    assert card["incident"]["generation_guard_bypassed"] is True
    assert card["incident"]["artifact_withdrawn"] is True
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["holdout"]["dti"] is None
    assert card["holdout"]["ci95"] is None
    assert card["holdout"]["withheld_positive_pixels"] is None
    assert card["leakage_canary"]["auc"] is None
    assert card["leakage_canary"]["all_pass"] is None
    assert card["raster_sha256"] is None
    assert card["weekly_slots_used"] == 0
    assert len(card["submission_name"]) <= 140
    assert len(card["submission_note"]) <= 140
    proof = card["preplacement_registry_proof"]
    assert proof["universal_overlap_blocker"] is True
    assert proof["uncovered_allowed_pixels"] == 0
    assert proof["directly_covered_allowed_pixels"] == proof["allowed_pixels"]


def test_unguarded_generator_and_unvalidated_download_are_removed():
    assert not (ROOT / "scripts/generate_unique_submission.py").exists()
    assert not (ROOT / "research/hypotheses-20261026-vvrd.md").exists()
    for directory in ("docs/downloads", "docs/research-variants", "submissions"):
        assert not list((ROOT / directory).glob("*vvrd*"))
    for page in ("docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / page).read_text()
        assert "vvrd-current-candidate" not in text
        assert "downloads/gems88-vvrd" not in text
    card = json.loads((ROOT / "docs/data/current_release.json").read_text())
    assert card["ok_to_submit"] is False


def test_overwritten_canonical_records_are_restored_exactly():
    card = json.loads((ROOT / "registry/session_aef1337d_run_card.json").read_text())
    for relative, digest in card["restored_files"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
