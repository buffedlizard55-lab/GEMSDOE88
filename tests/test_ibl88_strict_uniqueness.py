import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_ibl88 import audit  # noqa: E402


def test_ibl88_saved_artifact_is_literal_duplicate_and_research_only():
    card = json.loads((ROOT / 'registry/ibl88_run_card.json').read_text())
    mirrored = json.loads((ROOT / 'docs/data/ibl88_run_card.json').read_text())
    gate = json.loads((ROOT / 'registry/ibl88_gate.json').read_text())
    audit_result = audit(ROOT)
    assert card == mirrored
    assert card['uniqueness']['literal_binding_decision']['duplicate'] is True
    assert card['uniqueness']['literal_binding_decision']['stop_required'] is True
    assert card['uniqueness']['literal_binding_decision']['forward_overlap_3px'] == 1.0
    assert card['uniqueness']['literal_binding_decision']['limit'] == 0.70
    assert card['ok_to_download'] is True
    assert card['ok_to_submit'] is False
    assert gate['ok_to_download'] is True and gate['ok_to_submit'] is False
    assert gate['literal_binding_decision']['duplicate'] is True
    assert audit_result['audit_passed'] is True
    assert audit_result['strict_duplicate'] is True
    assert audit_result['checks']['positive_pixels'] == 37654
    assert audit_result['checks']['candidate_dots_within_3px_of_dense_witness'] == 37654
    assert audit_result['checks']['literal_forward_overlap_3px'] == 1.0
    assert audit_result['checks']['tif_sha256'] == card['submission']['sha256']
    assert audit_result['ok_to_download'] is True
    assert audit_result['ok_to_submit'] is False


def test_ibl88_validator_refuses_submission_clearance():
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/validate_ibl88.py'), '--require-submit'],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert 'NOT OK TO SUBMIT' in result.stdout
    assert 'DUPLICATE' in result.stdout
