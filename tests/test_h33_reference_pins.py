"""Lineage evidence must authenticate reference values, not just grid metadata."""
from unittest.mock import Mock

import pytest

from scripts import audit_h33_lineage as audit


@pytest.mark.parametrize("corrupt", ["sample_submission.tif", "existing_faults.tif"])
def test_reference_corruption_stops_before_grid_loading(tmp_path, monkeypatch, corrupt):
    bridge = tmp_path / "data/bridge"
    bridge.mkdir(parents=True)
    for filename in ("sample_submission.tif", "existing_faults.tif"):
        (bridge / filename).write_bytes(b"tampered reference")
    real_pin = audit.pinned
    checked = []

    def pin(root, relative, digest):
        checked.append(relative)
        if relative.endswith(corrupt):
            return real_pin(root, relative, digest)
        return root / relative

    load = Mock(side_effect=AssertionError("must not derive features"))
    monkeypatch.setattr(audit, "pinned", pin)
    monkeypatch.setattr(audit.grid, "load_grid", load)
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        audit.inspect(tmp_path)
    assert checked[-1].endswith(corrupt)
    load.assert_not_called()


def test_both_reference_pins_precede_derivation(tmp_path, monkeypatch):
    pin = Mock()
    load = Mock(side_effect=RuntimeError("stop after reference verification"))
    monkeypatch.setattr(audit, "pinned", pin)
    monkeypatch.setattr(audit.grid, "load_grid", load)
    with pytest.raises(RuntimeError, match="stop after reference verification"):
        audit.inspect(tmp_path)
    assert pin.call_args_list[0].args == (
        tmp_path, "data/bridge/sample_submission.tif", audit.grid.SHA256_SAMPLE_SUBMISSION)
    assert pin.call_args_list[1].args == (
        tmp_path, "data/bridge/existing_faults.tif", audit.grid.SHA256_EXISTING_FAULTS)
    assert pin.call_count == 2
