"""validate_con88 must fail closed, not traceback, when .cache surfaces are absent."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_con88", ROOT / "scripts" / "validate_con88.py")
mod = importlib.util.module_from_spec(spec)
sys.modules.setdefault("validate_con88", mod)
spec.loader.exec_module(mod)


def test_missing_canary_surface_exits_1(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        mod._load_canary_surface(tmp_path / "nope.npy")
    assert exc.value.code == 1
    assert "AUDIT_ERROR" in capsys.readouterr().err


def test_present_canary_surface_loads(tmp_path):
    import numpy as np

    p = tmp_path / "surf.npy"
    np.save(p, np.zeros((2, 2), dtype=np.float32))
    assert mod._load_canary_surface(p).shape == (2, 2)
