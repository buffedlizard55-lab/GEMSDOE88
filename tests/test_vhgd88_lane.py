import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import scipy.spatial as sps

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems88 import vhgd  # noqa: E402


def test_vhgd88_validator_script_passes():
    required_inputs = (
        ROOT / "data/bridge/sample_submission.tif",
        ROOT / "data/bridge/existing_faults.tif",
        ROOT / "data/registry/dense_17gemdoe.tif",
    )
    if not all(path.is_file() for path in required_inputs):
        pytest.skip("restore hash-pinned inputs with scripts/restore_inputs.py --validation")

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_vhgd88.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"validate_vhgd88.py failed:\n{proc.stdout}\n{proc.stderr}"
    assert "PASS validate_vhgd88:" in proc.stdout

    proc_sub = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_vhgd88.py"), "--require-submit"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc_sub.returncode == 2, f"Expected exit code 2 on --require-submit, got {proc_sub.returncode}"


def test_vhgd88_run_card_and_uniqueness_invariants():
    reg = json.loads((ROOT / "registry/vhgd88_run_card.json").read_text())
    web = json.loads((ROOT / "docs/data/vhgd88_run_card.json").read_text())
    assert reg == web
    assert reg["lane"] == "H88-VHGD" and reg["verdict"] == "negative"
    assert reg["ok_to_download"] is True and reg["ok_to_submit"] is False
    assert reg["organizer_confirmed_score"] is None and reg["weekly_slots_used"] == 0

    hd = reg["holdout_dti"]
    assert hd["evidence_class"] == "HOLDOUT-DTI"
    assert hd["evaluator_version"] == "gems57-pooled-hide-v2"
    assert hd["withheld_positive_pixels_overall"] == 22893
    exp2 = hd["exp2_poe_unconstrained"]
    assert exp2["overall"]["dti"] > hd["control_adhr_lgbm_overall"]["dti"]
    assert exp2["paired_delta_vs_adhr_control"]["ci95"][0] > 0.0
    assert exp2["far_gt10px"]["dti"] > 0.131922
    assert exp2["blind_gt25px"]["dti"] > 0.090449

    assert reg["leakage_canary"]["passed"] is True
    assert reg["leakage_canary"]["features_tested"] == 84
    assert reg["leakage_canary"]["max_symmetric_auc"] <= 0.90

    sub = reg["submission"]
    assert len(sub["submission_name"]) <= 140
    assert len(sub["submission_note"]) == sub["submission_note_chars"] <= 140
    tif = ROOT / sub["file"]
    archive = ROOT / sub["zip_file"]
    assert tif.is_file() and archive.is_file() and "DO-NOT-SUBMIT" in tif.name
    with zipfile.ZipFile(archive) as zf:
        assert zf.namelist() == [tif.name] and zf.read(tif.name) == tif.read_bytes()

    corr = reg["correlation_overlap_vs_registry"]
    assert corr["surface_preplacement_max_abs_spearman"] <= 0.90
    assert corr["final_worst_like_for_like_overlap_3px"]["value"] <= 0.70
    assert corr["like_for_like_blockers"] == []
    assert corr["unique_like_for_like"] is True
    assert corr["unique_literal"] is False


def test_vhgd88_source_quarantine_and_ir_guards():
    import ast

    vhgd_src = (ROOT / "src/gems88/vhgd.py").read_text()
    tree = ast.parse(vhgd_src)
    # Strip module/function docstrings so we inspect executable AST string literals
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                doc_nodes.add(id(first.value))
    exec_strings = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in doc_nodes
    ]
    joined = "\n".join(exec_strings)
    assert "dist_known_fault_px" in vhgd.FORBIDDEN_CSV_COLUMNS
    # Verify dist_known_fault_px is NEVER read via subscript or .get(...) anywhere in vhgd.py
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            assert node.slice.value not in vhgd.FORBIDDEN_CSV_COLUMNS
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            if node.args and isinstance(node.args[0], ast.Constant):
                assert node.args[0].value not in vhgd.FORBIDDEN_CSV_COLUMNS
    assert "existing_faults.tif" not in joined
    assert "sgmc_faults_100m.tif" not in joined
    assert "blm_closed_claim" not in joined

    runner_src = (ROOT / "scripts/run_vhgd88_experiment.py").read_text()
    assert "src.read(12)" in runner_src and '"det_elev"' in runner_src, (
        "Runner must read B12 det_elev (band 12) for compute_visible_struct_fp (IR-88-110)"
    )
    assert "syn_hid" in runner_src and "syn_vis" in runner_src, "Production structural head must fit on synthetic split (IR-88-119)"


def test_vhgd_three_stratum_allocator_seam_spacing_and_collar():
    rng = np.random.default_rng(88)
    h, w = 80, 80
    fp = np.ones((h, w), dtype=bool)
    known = np.zeros((h, w), dtype=bool)
    known[0, :] = True  # row 0 is catalogue fault -> row r has d_cat = r px
    allowed = fp & (~known)

    p_hit = rng.uniform(0.15, 0.55, size=(h, w)).astype(np.float32)
    m_hit = rng.uniform(0.55, 0.90, size=(h, w)).astype(np.float32)
    # Boost stratum seam rows r=9 and r=25 to force cross-stratum adjacency pressure
    p_hit[9, :] = 0.85
    p_hit[10, :] = 0.85
    p_hit[25, :] = 0.85
    p_hit[26, :] = 0.85

    d_cat = np.broadcast_to(np.arange(h, dtype=np.float32)[:, None], (h, w)).copy()
    emitted, info = vhgd.allocate_h33_three_stratum(
        p_hit,
        m_hit,
        p_hit,
        m_hit,
        p_hit,
        m_hit,
        allowed,
        d_cat,
        total_budget=120,
        k_truth_est=400.0,
        min_spacing_px=2.85,
        shares=(0.20, 0.40, 0.40),
    )
    dots = emitted > 0
    assert int(dots.sum()) == info["n_dots"] > 0
    assert not np.any(dots[d_cat <= 2.0]), "Must never emit dots inside <=2 px collar"
    assert not np.any(dots[known]), "Must never emit dots on known faults"

    rc = np.argwhere(dots).astype(np.float64)
    if len(rc) >= 2:
        dmat = sps.distance.pdist(rc)
        assert float(dmat.min()) >= 2.85 - 1e-6, f"Cross-stratum seam spacing violated: min dist = {dmat.min():.4f}"
