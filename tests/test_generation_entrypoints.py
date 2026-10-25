"""Every candidate CLI must stop BEFORE its model/feature imports or writes."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import generation_guard  # noqa: E402


def entrypoints() -> list[Path]:
    files = set()
    for glob in ("build*.py", "run*.py", "generate*.py", "rebuild*.py", "fit*.py", "predict*.py", "train*.py", "emit*.py"):
        files.update((ROOT / "scripts").glob(glob))
    files.difference_update(ROOT / "scripts" / name for name in (
        "build_candidate_matrix.py", "generate_figures.py"))
    # No research-only exception: MFS is included in the same mandatory
    # pre-import guard contract as every other candidate runner.
    files.update(ROOT / "scripts" / name for name in (
        "make_concentration_variants.py", "evaluate_cgo88.py", "eval_concentration_proxy.py",
        "exp_provcrest_spacing.py", "publish_kdmc_site.py", "publish_sdtl88.py",
        "finalize_concentration.py", "write_concentration_receipts.py",
        "lbcal_build_stats.py", "lbcal_pixel.py", "lbcal_fit.py", "lbcal_extra_features.py",
        "mass_r0_ranking_control.py", "reaudit_hgvc88_v4.py"))
    return sorted(path for path in files if '__name__' in path.read_text())


@pytest.mark.parametrize("path", entrypoints(), ids=lambda p: p.name)
def test_guard_is_first_and_reached_before_historical_cli_body(path, monkeypatch):
    tree = ast.parse(path.read_text())
    executable = [n for n in tree.body if not (
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
    ) and not (isinstance(n, ast.ImportFrom) and n.module == "__future__")]
    first = executable[0]
    assert isinstance(first, ast.If), f"{path.name} can execute before the preflight"
    assert ast.unparse(first.test) == "__name__ == '__main__'"
    assert isinstance(first.body[-1], ast.Expr)
    assert ast.unparse(first.body[-1]) == 'enforce_generation_preflight()'

    class PreflightReached(Exception):
        pass

    def stop():
        raise PreflightReached

    monkeypatch.setattr(generation_guard, "enforce_generation_preflight", stop)
    # Imports/functions remain usable by synthetic tests, but an actual CLI
    # dispatch must encounter the shared guard before any heavy model code.
    with pytest.raises(PreflightReached):
        runpy.run_path(str(path), run_name="__main__")


def test_absent_or_corrupt_input_is_error_and_invalidates_cached_success(tmp_path):
    out = tmp_path / ".cache/generation-preflight.json"
    out.parent.mkdir()
    out.write_text('{"generation_allowed":true}')
    with pytest.raises(SystemExit) as exc:
        generation_guard.enforce_generation_preflight(tmp_path)
    assert exc.value.code == 1
    result = json.loads(out.read_text())
    assert result["decision"] == "AUDIT_ERROR"
    assert result["generation_allowed"] is False
    assert result["ok_to_submit"] is False


def test_witness_removed_is_not_automatic_permission(monkeypatch):
    from scripts import preflight_mtas88
    monkeypatch.setattr(preflight_mtas88, "inspect", lambda _: {
        "preplacement_registry_proof": {"universal_overlap_blocker": False}})
    result = generation_guard.inspect(ROOT)
    assert result["decision"] == "INCOMPLETE_REGISTRY_GATE"
    assert result["generation_allowed"] is False


@pytest.mark.skipif(not (ROOT / "data/registry/dense_17gemdoe.tif").is_file(), reason="validation inputs not restored")
@pytest.mark.parametrize("command", [
    ["scripts/build_unique_relay_submission.py"],
    ["-O", "scripts/run_gems88_pipeline.py"],
    ["-m", "scripts.build_ssa88_submission"],
    ["scripts/publish_kdmc_site.py"],
    ["scripts/run_mfs88_experiment.py"],
    ["-O", "scripts/run_mfs88_experiment.py"],
    ["-m", "scripts.run_mfs88_experiment"],
    ["scripts/run_sdtl88_experiment.py"],
    ["-O", "scripts/build_sdtl88_submission.py"],
    ["-m", "scripts.publish_sdtl88"],
])
def test_real_entrypoints_exit_two_without_writing_candidates(command):
    before = {p.name: p.stat().st_mtime_ns for p in (ROOT / "docs/downloads").iterdir()}
    page_before = (ROOT / "docs/index.html").read_bytes()
    result = subprocess.run([sys.executable, *command], cwd=ROOT, text=True, capture_output=True, timeout=30)
    assert result.returncode == 2, result.stdout + result.stderr
    report = json.loads(result.stderr)
    assert report["decision"] == "DUPLICATE_STOP"
    assert report["new_rasters_generated"] == report["experiments_run"] == 0
    assert result.stdout == ""  # historical builder did not start
    assert before == {p.name: p.stat().st_mtime_ns for p in (ROOT / "docs/downloads").iterdir()}
    assert page_before == (ROOT / "docs/index.html").read_bytes()
