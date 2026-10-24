"""Every raster a new candidate must be unlike (uniqueness registry, v3).

Sources (all SHA-pinned by restore scripts; none is organizer-authenticated):
  * ``registry/inventory.json``      21 rasters of the original registry
  * ``data/registry/**``              restored lineage / calibration rasters
  * ``data/fleet/*.tif``              25 scored rasters mirrored by GEMSDOE86
  * ``data/siblings/*.tif``           GEMSDOE86, 87, 89, 90, 91, 92 (IR-88-59: previously missing)
  * ``docs/downloads/*.tif``          this repository's own earlier candidates (site GEMSDOE88)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def registry_list(root: Path = ROOT, exclude: tuple[str, ...] = ()) -> list[tuple[str, Path]]:
    seen, out = set(), []

    def add(label, path):
        p = Path(path)
        if not p.is_file() or p.suffix.lower() not in (".tif", ".tiff"):
            return
        rp = p.resolve()
        if rp in seen or any(x and x in p.name for x in exclude):
            return
        seen.add(rp)
        out.append((label, p))

    inv = json.loads((root / "registry" / "inventory.json").read_text())
    for r in inv["rasters"]:
        add(f"{r['repo_first']}:{Path(r['cache_file']).name}", root / r["cache_file"])
    for p in sorted((root / "data" / "registry").rglob("*.tif")):
        add(f"registry:{p.name}", p)
    for p in sorted((root / "data" / "fleet").glob("*.tif")):
        add(f"fleet:{p.name}", p)
    for p in sorted((root / "data" / "siblings").glob("*.tif")):
        add(f"sibling:{p.name}", p)
    for p in sorted((root / "docs" / "downloads").glob("*.tif")):
        add(f"GEMSDOE88:{p.name}", p)
    return out
