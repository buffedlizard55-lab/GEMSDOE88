"""H88-SEPA lane: synthetic feature-transform checks + gate v4 (IR-88-127) semantics."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88 import gate, sepa  # noqa: E402


def test_sepa_feature_registry():
    assert len(sepa.SEPA_FEATURES) == 18
    assert len(set(sepa.SEPA_FEATURES)) == 18
    assert all(n.startswith("sepa_") for n in sepa.SEPA_FEATURES)


def test_structure_tensor_line_vs_flat():
    a = np.zeros((64, 64), np.float32)
    a[:, 30:34] = 1.0
    aniso, u, v = sepa._structure_tensor(a, 1.5, 3.0)
    assert aniso[32, 32] > 0.9          # linear fabric at the line
    assert aniso[32, 5] < 0.05          # no fabric in flat field
    agree = sepa._orient_agree(aniso, u, v, aniso, u, v)
    assert agree[32, 32] > 0.9          # a fabric agrees with itself


def test_blobness_blob_vs_line():
    y, x = np.mgrid[0:64, 0:64]
    blob = np.exp(-(((y - 32) ** 2 + (x - 32) ** 2) / 50.0)).astype(np.float32)
    line = np.zeros((64, 64), np.float32)
    line[:, 30:34] = 1.0
    fp = np.ones((64, 64), bool)
    assert sepa._blobness(blob, fp, 3.0)[32, 32] > 0.8   # volcanic-swarm mimic fires on blobs
    assert sepa._blobness(line, fp, 3.0)[32, 32] < 0.05  # ...but not on lines


def _portal_ok():
    return {"ok": True, "problems": []}


def _uq(**kw):
    base = {"unique_v4": True, "unique_literal": False, "v4_blockers": [],
            "worst_literal_overlap": {"label": "17GEMSDOE:dense", "value": 1.0},
            "registry_complete": True, "surface_checked": True}
    base.update(kw)
    return base


def test_gate_v4_promotes_when_only_literal_dense_reading_fails():
    gv = gate.decide_v4(portal=_portal_ok(), uniqueness=_uq(), canary_passed=True,
                        holdout_beats_bar=True, name="X-SEPA-TEST", note="note", used_names=[])
    assert gv["policy"] == "gems88-gate-v4"
    assert gv["ok_to_submit"] is True
    assert gv["label"] == "OK TO DOWNLOAD AND SUBMIT"
    assert any("LITERAL READING" in s for s in gv["informational"])  # disclosed, never hidden
    assert gv["approved_for_weekly_slot"] is False                   # gate never spends a slot


def test_gate_v4_blocks_dotfield_duplicate_and_failed_holdout():
    gv = gate.decide_v4(portal=_portal_ok(), uniqueness=_uq(unique_v4=False, v4_blockers=["rasterA"]),
                        canary_passed=True, holdout_beats_bar=True,
                        name="X-SEPA-TEST", note="note", used_names=[])
    assert gv["ok_to_submit"] is False
    gv2 = gate.decide_v4(portal=_portal_ok(), uniqueness=_uq(), canary_passed=True,
                         holdout_beats_bar=False, name="X-SEPA-TEST", note="note", used_names=[])
    assert gv2["ok_to_submit"] is False
    assert any("HOLDOUT" in s for s in gv2["blocking_reasons"])


def test_gate_v4_blocks_name_reuse_and_bad_format():
    gv = gate.decide_v4(portal={"ok": False, "problems": ["range"]}, uniqueness=_uq(),
                        canary_passed=True, holdout_beats_bar=True,
                        name="X-SEPA-TEST", note="note", used_names=["X-SEPA-TEST"])
    assert gv["ok_to_download"] is False and gv["ok_to_submit"] is False


def test_sepa88_release_artifacts_if_present():
    rc = ROOT / "registry/sepa88_run_card.json"
    if not rc.is_file():
        pytest.skip("SEPA release not built in this checkout")
    sys.path.insert(0, str(ROOT / "scripts"))
    from validate_sepa88 import sepa88_report

    report = sepa88_report(ROOT)
    assert report["ok"], report["problems"]
    assert report["dots"] == 37654


def test_hgvc_v4_reaudit_receipt_if_present():
    """The v4 re-audit (IR-88-127) must not have touched the frozen HGVC bytes/card."""
    import json

    reg = ROOT / "registry/hgvc88_gate_v4_reaudit_20261025.json"
    doc = ROOT / "docs/data/hgvc88_gate_v4_reaudit_20261025.json"
    if not reg.is_file():
        pytest.skip("HGVC v4 re-audit not run in this checkout")
    assert reg.read_text() == doc.read_text()
    d = json.loads(reg.read_text())
    rc = json.loads((ROOT / "registry/hgvc88_run_card.json").read_text())
    assert d["subject"]["sha256"] == rc["raster_sha256"] == "d5329f317682ba3ea15eba32aebe9a2000fc0e42cedfd20a36caae03ef3012ef"
    assert rc["verdict"] == "negative" and rc["ok_to_submit"] is False  # v3 history untouched
    assert d["historical_v3_verdict_unchanged"]["ok_to_submit"] is False
    if d["ok_to_submit"]:
        assert d["uniqueness_recomputed"]["unique_v4"] is True
        assert d["uniqueness_recomputed"]["worst_dotfield_overlap"]["value"] <= 0.70
        assert d["uniqueness_recomputed"]["worst_abs_rho_final"]["value"] <= 0.90
        assert d["uniqueness_recomputed"]["unique_literal"] is False  # literal reading published, not hidden
