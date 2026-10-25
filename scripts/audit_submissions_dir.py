#!/usr/bin/env python3
"""Fail-closed saved-byte package audit for historical research archives in ``submissions/``.

``scripts/audit_downloads.py`` audits ``docs/downloads/`` and ``docs/research-variants/``.
This companion audit closes the gap for ``submissions/`` so no tracked repo-side
TIFF or ZIP can omit the ``DO-NOT-SUBMIT`` marker (either on disk or inside its
ZIP archive), depend on GDAL sidecars, carry invalid ``[0, 1]``/NaN/grid values,
or become an orphan package.

Exit codes:
  0  every ``submissions/`` TIFF/ZIP pair is valid negative research packaging
  1  any packaging, marker, sidecar, or GeoTIFF format check failed
  2  ``--require-submit`` requested (all ``submissions/`` files are DO-NOT-SUBMIT)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_artifact import validate_artifact  # noqa: E402

SIDECAR_SUFFIXES = (".aux.xml", ".ovr", ".msk", ".tfw", ".wld", ".prj")


def verify_zip_package(zip_path: Path, tif_path: Path) -> list[str]:
    """Verify a one-TIFF research ZIP preserves DO-NOT-SUBMIT and exact TIFF bytes."""
    errors: list[str] = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            infos = zf.infolist()
            if len(infos) != 1:
                return [f"ZIP must contain exactly 1 member, got {len(infos)}: {zf.namelist()}"]
            info = infos[0]
            name = info.filename
            if "/" in name or "\\" in name or ".." in name or info.is_dir():
                errors.append(f"unsafe ZIP member path: {name!r}")
            if "DO-NOT-SUBMIT" not in name:
                errors.append(f"ZIP member lacks DO-NOT-SUBMIT marker: {name!r}")
            if name != tif_path.name:
                errors.append(f"ZIP member {name!r} != paired TIFF {tif_path.name!r}")
            if info.flag_bits & 1:
                errors.append("encrypted ZIP member is forbidden")
            unix_mode = (info.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                errors.append("symlink ZIP member is forbidden")
            if not errors and zf.read(name) != tif_path.read_bytes():
                errors.append("ZIP member bytes differ from paired TIFF bytes")
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    return errors


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_submissions_directory(root: Path = ROOT) -> dict:
    sub_dir = Path(root) / "submissions"
    if not sub_dir.is_dir() or sub_dir.is_symlink():
        raise ValueError("submissions/ directory missing or symlinked")

    tifs: list[Path] = []
    zips: list[Path] = []
    jsons: list[Path] = []
    unexpected: list[str] = []
    symlinks: list[str] = []

    for entry in sorted(sub_dir.iterdir(), key=lambda p: p.name):
        if entry.is_symlink():
            symlinks.append(entry.name)
            continue
        lower = entry.name.lower()
        if any(lower.endswith(sfx) for sfx in SIDECAR_SUFFIXES):
            unexpected.append(f"forbidden sidecar: {entry.name}")
        elif lower.endswith((".tif", ".tiff")) and entry.is_file():
            tifs.append(entry)
        elif lower.endswith(".zip") and entry.is_file():
            zips.append(entry)
        elif lower.endswith(".json") and entry.is_file():
            jsons.append(entry)
            if "DO-NOT-SUBMIT" not in entry.name:
                unexpected.append(f"JSON receipt lacks DO-NOT-SUBMIT marker: {entry.name}")
            else:
                try:
                    payload = json.loads(entry.read_text(encoding="utf-8"))
                    if isinstance(payload, dict) and (
                        payload.get("ok_to_submit") is True
                        or payload.get("submission_ready") is True
                        or payload.get("verdict") == "promote"
                    ):
                        unexpected.append(f"JSON receipt advertises clearance: {entry.name}")
                except Exception as exc:
                    unexpected.append(f"invalid JSON {entry.name}: {exc}")
        elif entry.name not in {".gitkeep", "README.md"}:
            unexpected.append(f"unexpected entry: {entry.name}")

    expected_zips = {t.with_suffix(".zip").name for t in tifs}
    orphan_zips = sorted(z.name for z in zips if z.name not in expected_zips)

    sample = Path(root) / "data/bridge/sample_submission.tif"
    faults = Path(root) / "data/bridge/existing_faults.tif"
    has_inputs = sample.is_file() and faults.is_file()
    catalogue = None
    if has_inputs:
        with rasterio.open(sample) as s_ds, rasterio.open(faults) as f_ds:
            footprint = np.isfinite(s_ds.read(1)) & (s_ds.read_masks(1) > 0)
            catalogue = (f_ds.read(1) > 0) & footprint

    rows = []
    pass_count = 0
    for tif in tifs:
        errors: list[str] = []
        zip_path = tif.with_suffix(".zip")
        if "DO-NOT-SUBMIT" not in tif.name:
            errors.append("TIFF filename lacks DO-NOT-SUBMIT marker")
        if not zip_path.is_file():
            errors.append(f"missing paired ZIP: {zip_path.name}")
        else:
            if "DO-NOT-SUBMIT" not in zip_path.name:
                errors.append("ZIP filename lacks DO-NOT-SUBMIT marker")
            errors.extend(verify_zip_package(zip_path, tif))

        fmt_ok = None
        if has_inputs:
            v = validate_artifact(tif, sample)
            fmt_ok = bool(v["ok"])
            if not fmt_ok:
                errors.append(f"validate_artifact failed: {[k for k, ok in v.items() if ok is False]}")
            else:
                with rasterio.open(tif) as ds:
                    arr = ds.read(1)
                if catalogue is not None and int((arr[catalogue] > 0).sum()) != 0:
                    errors.append("positive prediction mass on mapped catalogue pixels")

        ok = not errors and (fmt_ok is not False)
        pass_count += int(ok)
        rows.append({
            "file": tif.name,
            "zip_file": zip_path.name if zip_path.is_file() else None,
            "sha256": sha256_file(tif),
            "zip_sha256": sha256_file(zip_path) if zip_path.is_file() else None,
            "format_checked_with_sample": has_inputs,
            "format_valid": fmt_ok,
            "package_ok": ok,
            "ok_to_submit": False,
            "errors": errors,
        })

    top_errors = list(symlinks) + list(unexpected) + [f"orphan zip: {z}" for z in orphan_zips]
    all_ok = (not top_errors) and pass_count == len(tifs) and len(tifs) > 0
    return {
        "schema": "gems88.submissions-dir-audit.v1",
        "directory": "submissions",
        "tiff_count": len(tifs),
        "zip_count": len(zips),
        "pass_count": pass_count,
        "sample_inputs_verified": has_inputs,
        "orphan_zips": orphan_zips,
        "top_level_errors": top_errors,
        "protocol_eligible_count": 0,
        "all_packages_safe": all_ok,
        "artifacts": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args()
    report = audit_submissions_directory(ROOT)
    summary = {k: v for k, v in report.items() if k != "artifacts"}
    failing = [r for r in report["artifacts"] if not r["package_ok"]]
    if failing:
        summary["failing_artifacts"] = failing
    print(json.dumps(summary, indent=2))
    if not report["all_packages_safe"]:
        return 1
    if args.require_submit:
        print("DO NOT SUBMIT: submissions/ contains only negative DO-NOT-SUBMIT research archives.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
