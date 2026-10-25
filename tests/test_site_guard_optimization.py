"""Production release checks must not disappear under Python -O."""

import ast
import json
import shutil
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("optimized", [False, True])
@pytest.mark.parametrize("corruption", ["status", "download", "unique-claim"])
def test_guard_rejects_corruption_under_both_interpreters(
    tmp_path, optimized, corruption
):
    # Copy published bytes: symlinks are not valid publication artifacts.
    (tmp_path / "registry").symlink_to(ROOT / "registry", target_is_directory=True)
    (tmp_path / "evidence").symlink_to(ROOT / "evidence", target_is_directory=True)
    docs = tmp_path / "docs"
    docs.mkdir()
    for source in (ROOT / "docs").iterdir():
        if source.name == "status.json":
            status = json.loads(source.read_text())
            if corruption == "status":
                status["ok_to_submit"] = True
            (docs / source.name).write_text(json.dumps(status))
        elif source.name == "index.html" and corruption == "unique-claim":
            index = source.read_text().replace(
                "Literal forward overlap vs the 17GEMSDOE witness = 1.00 &gt; 0.70",
                "Literal forward overlap vs the 17GEMSDOE witness = 0.10 &lt; 0.70",
            )
            (docs / source.name).write_text(index)
        elif source.name == "downloads" and corruption == "download":
            downloads = docs / source.name
            downloads.mkdir()
            for artifact in source.iterdir():
                shutil.copyfile(artifact, downloads / artifact.name)
            (downloads / "unmarked-research.tif").write_bytes(b"not a TIFF")
        elif source.name in {"downloads", "research-variants"}:
            shutil.copytree(source, docs / source.name)
        else:
            (docs / source.name).symlink_to(source, target_is_directory=source.is_dir())
    command = [sys.executable] + (["-O"] if optimized else [])
    command += [
        "-c",
        "from pathlib import Path; from scripts.check_site import main; "
        "main(Path(__import__('sys').argv[1]))",
        str(tmp_path),
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode != 0
    assert "PASS:" not in result.stdout
    assert "ValueError" in result.stderr
    if corruption == "download":
        assert "unmarked published research artifact" in result.stderr
    elif corruption == "unique-claim":
        assert "must not overstate sparse-screen uniqueness" in result.stderr


@pytest.mark.parametrize("optimized", [False, True])
def test_marked_xgce_is_still_hash_pinned_and_negative(tmp_path, optimized):
    (tmp_path / "registry").symlink_to(ROOT / "registry", target_is_directory=True)
    (tmp_path / "evidence").symlink_to(ROOT / "evidence", target_is_directory=True)
    docs = tmp_path / "docs"
    docs.mkdir()
    for source in (ROOT / "docs").iterdir():
        if source.name != "downloads":
            if source.name == "research-variants":
                shutil.copytree(source, docs / source.name)
            else:
                (docs / source.name).symlink_to(source, target_is_directory=source.is_dir())
            continue
        downloads = docs / "downloads"
        downloads.mkdir()
        for item in source.iterdir():
            if item.name == "gems88-xgce-crossgradient-30000dots-20261025-zeros-DO-NOT-SUBMIT.tif":
                (downloads / item.name).write_bytes(item.read_bytes() + b"tamper")
            else:
                shutil.copyfile(item, downloads / item.name)
    command = [sys.executable] + (["-O"] if optimized else [])
    result = subprocess.run(
        command + ["-c", "from pathlib import Path; from scripts.check_site import main; "
                   "main(Path(__import__('sys').argv[1]))", str(tmp_path)],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "Pinned XGCE research pair must remain negative" in result.stderr


def test_no_disableable_assertions_remain_in_production_site_guard():
    tree = ast.parse((ROOT / "scripts/check_site.py").read_text())
    assert not any(isinstance(node, ast.Assert) for node in ast.walk(tree))


@pytest.mark.parametrize("optimized", [False, True])
def test_real_site_passes_under_both_interpreters(optimized):
    command = [sys.executable] + (["-O"] if optimized else [])
    result = subprocess.run(
        command + ["scripts/check_site.py"], cwd=ROOT, text=True, capture_output=True
    )
    assert result.returncode == 0, result.stderr
    assert "PASS:" in result.stdout
