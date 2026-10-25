"""Unit and integration tests for lane H88-DHTC."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

from gems88 import dhtc
try:
    from validate_dhtc88 import validate_dhtc88
except ImportError:
    from scripts.validate_dhtc88 import validate_dhtc88


def test_dhtc_features_list():
    assert len(dhtc.DHTC_FEATURES) == 16
    assert "dhtc_cond_surf" in dhtc.DHTC_FEATURES
    assert "dhtc_conduit_joint_index" in dhtc.DHTC_FEATURES
    assert "dhtc_basin_blind_conduit" in dhtc.DHTC_FEATURES


def test_dhtc_validation_passes():
    res = validate_dhtc88(ROOT)
    assert res["ok"] is True
    assert res["lane"] == "H88-DHTC"
    assert res["ok_to_download"] is True
    assert res["ok_to_submit"] is False
    assert res["verdict"] == "negative"
    assert res["worst_like_for_like_overlap_3px"] <= 0.70
    assert res["surface_max_abs_rho"] <= 0.90


def test_dhtc_run_card_integrity():
    reg = json.loads((ROOT / "registry/dhtc88_run_card.json").read_text())
    web = json.loads((ROOT / "docs/data/dhtc88_run_card.json").read_text())
    assert reg == web
    assert reg["lane"] == "H88-DHTC"
    assert reg["leakage_canary"]["passed"] is True
    assert reg["leakage_canary"]["max_symmetric_auc"] <= 0.90
    assert reg["validator_output"]["ok"] is True
    assert reg["validator_output"]["checks"]["portal_range_check_nan_strict"] is True
