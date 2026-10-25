#!/usr/bin/env python3
"""Prepare and verify competition data for training, inference, and validation.

This script restores the shared input tier, matches SHA-256 checksums recorded
in owner mirrors (NOT organizer-authenticated checksums), verifies grid parity,
populates historical data/official and data/bridge paths, and loads feature planes.
Data preparation does not authorize generation or establish end-to-end model validity.

Can be run with optional `--fetch` flag to invoke restore_inputs.py automatically.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OFFICIAL_DIR = DATA_DIR / "official"
BRIDGE_DIR = DATA_DIR / "bridge"

sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

EXPECTED_HASHES = {
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
}

EXPECTED_GRID = {
    "crs": 32611,
    "shape": (3730, 3292),
    "transform": (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_symlink(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.exists():
        if target.resolve() == source.resolve():
            return
        target.unlink()
    try:
        target.symlink_to(source)
    except OSError:
        import shutil
        shutil.copy2(source, target)


def write_preparation_manifest(manifest: dict) -> None:
    """Publish a complete status atomically; never expose partially written JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=DATA_DIR,
                                         prefix=".prepared-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
        temporary.replace(DATA_DIR / "prepared_data_manifest.json")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare_data(fetch: bool = False) -> dict:
    """Invalidate a previous success BEFORE fetching or examining mutable inputs.

    A killed process leaves ``preparing`` (not ready); caught failures leave
    ``error``. Exceptions still propagate so CLI and automation fail nonzero.
    This is a preparation receipt, not an authorization or concurrency lock.
    """
    pending = {
        "status": "preparing",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_authorized": False,
        "ok_to_submit": False,
        "provenance": "SHA-pinned owner mirrors; not authenticated organizer downloads",
    }
    write_preparation_manifest(pending)
    try:
        result = _prepare_data(fetch=fetch)
        write_preparation_manifest(result)
        return result
    except BaseException as exc:
        # Also invalidate on Ctrl-C/SystemExit from restoration helpers.
        write_preparation_manifest({**pending, "status": "error",
                                    "error": f"{type(exc).__name__}: {exc}"})
        raise


def _prepare_data(fetch: bool = False) -> dict:
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)
    BRIDGE_DIR.mkdir(parents=True, exist_ok=True)

    if fetch:
        print("[prepare_data] Invoking scripts/restore_inputs.py...")
        subprocess.run([sys.executable, str(ROOT / "scripts/restore_inputs.py")], check=True)
        subprocess.run([sys.executable, str(ROOT / "scripts/restore_siblings.py")], check=True)

    # Resolve core files across possible locations
    resolved = {}
    for fname in ("sample_submission.tif", "existing_faults.tif", "training_features.tif"):
        candidates = [
            DATA_DIR / fname,
            BRIDGE_DIR / fname,
            OFFICIAL_DIR / fname,
        ]
        found = None
        for c in candidates:
            if c.is_file():
                found = c
                break
        resolved[fname] = found

    # If any file is missing, attempt restore
    missing = [k for k, v in resolved.items() if v is None]
    if missing:
        print(f"[prepare_data] Missing files: {missing}. Running restore_inputs.py...")
        subprocess.run([sys.executable, str(ROOT / "scripts/restore_inputs.py")], check=True)
        for fname in missing:
            for c in (DATA_DIR / fname, BRIDGE_DIR / fname, OFFICIAL_DIR / fname):
                if c.is_file():
                    resolved[fname] = c
                    break

    # Verify SHA-256 checksums
    print("[prepare_data] Verifying SHA-256 checksums...")
    audit = {}
    for fname, exp_hash in EXPECTED_HASHES.items():
        fpath = resolved.get(fname)
        if fpath is None or not fpath.is_file():
            raise FileNotFoundError(f"Required competition file {fname} not found in data directories.")
        h = sha256_file(fpath)
        if h != exp_hash:
            raise ValueError(f"Checksum mismatch for {fname}: expected {exp_hash}, got {h}")
        audit[fname] = {"path": str(fpath), "sha256": h, "bytes": fpath.stat().st_size, "verified": True}
        print(f"  [OK] {fname}: {h[:16]}... ({fpath.stat().st_size:,} bytes)")

    # Establish canonical links in both official/ and bridge/
    sample_src = resolved["sample_submission.tif"]
    faults_src = resolved["existing_faults.tif"]
    features_src = resolved["training_features.tif"]

    ensure_symlink(sample_src, BRIDGE_DIR / "sample_submission.tif")
    ensure_symlink(faults_src, BRIDGE_DIR / "existing_faults.tif")
    ensure_symlink(sample_src, OFFICIAL_DIR / "sample_submission.tif")
    ensure_symlink(faults_src, OFFICIAL_DIR / "existing_faults.tif")
    ensure_symlink(features_src, OFFICIAL_DIR / "training_features.tif")
    ensure_symlink(features_src, DATA_DIR / "training_features.tif")

    # Grid check via rasterio
    import rasterio
    print("[prepare_data] Validating spatial grid and reference system...")
    with rasterio.open(BRIDGE_DIR / "sample_submission.tif") as ds:
        epsg = ds.crs.to_epsg() if ds.crs else None
        shape = ds.shape
        t = tuple(ds.transform)[:6]
        if epsg != EXPECTED_GRID["crs"]:
            raise ValueError(f"CRS mismatch: expected EPSG:32611, got {epsg}")
        if shape != EXPECTED_GRID["shape"]:
            raise ValueError(f"Shape mismatch: expected (3730, 3292), got {shape}")
        if t != EXPECTED_GRID["transform"]:
            raise ValueError(f"Transform mismatch: expected {EXPECTED_GRID['transform']}, got {t}")
        print(f"  [OK] Spatial Grid: EPSG:{epsg}, {shape[0]}x{shape[1]}, Affine={t}")

    # Check every core file, not just the sample. A filename is not a grid contract.
    grid_checks = {}
    for fname, fpath in resolved.items():
        with rasterio.open(fpath) as ds:
            expected_count = 19 if fname == "training_features.tif" else 1
            checks = {
                "crs_match": ds.crs is not None and ds.crs.to_epsg() == EXPECTED_GRID["crs"],
                "shape_match": ds.shape == EXPECTED_GRID["shape"],
                "transform_match": tuple(ds.transform)[:6] == EXPECTED_GRID["transform"],
                "band_count_match": ds.count == expected_count,
            }
            if not all(checks.values()):
                raise ValueError(f"Core input grid/band mismatch: {fname}: {checks}")
            grid_checks[fname] = checks

    # Verify planes load via vendor/gems57/geo.py
    print("[prepare_data] Testing feature stack integration (vendor/gems57/geo.py)...")
    from gems57 import geo, grid
    g = grid.load_grid(BRIDGE_DIR)
    planes = geo.load_planes(g.footprint)
    print(f"  [OK] Successfully loaded {len(planes)} robust-z geophysical planes: {list(planes.keys())}")

    manifest = {
        "status": "ready",
        "footprint_pixels": int(g.footprint.sum()),
        "catalogue_pixels": int(g.catalogue.sum()),
        "files": audit,
        "planes": list(planes.keys()),
        "grid_checks": grid_checks,
        "provenance": "SHA-pinned owner mirrors; not authenticated organizer downloads",
        "scope": "shared core inputs and feature-plane load only; not every lane-specific dataset or fitted model",
        "generation_authorized": False,
        "ok_to_submit": False,
    }
    out_path = DATA_DIR / "prepared_data_manifest.json"
    print(f"\n[prepare_data] Data checks complete. Manifest destination: {out_path}.")
    print("Shared inputs prepared; generation preflight, scientific validation and slot approval remain separate.")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and verify competition data.")
    parser.add_argument("--fetch", action="store_true", help="Fetch/restore inputs from bridges before verifying")
    args = parser.parse_args()
    prepare_data(fetch=args.fetch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
