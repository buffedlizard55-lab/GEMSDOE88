"""Every raster a new candidate must be unlike (uniqueness registry, v3).

Sources (all SHA-pinned by restore scripts; none is organizer-authenticated):
  * ``registry/inventory.json``      21 rasters of the original registry
  * ``data/registry/**``              restored lineage / calibration rasters
  * ``data/fleet/*.tif``              25 scored rasters mirrored by GEMSDOE86
  * ``data/siblings/*.tif``           GEMSDOE86, 87, 89, 90, 91, 92 (IR-88-59: previously missing)
  * ``docs/downloads/*.tif``          this repository's own earlier candidates (site GEMSDOE88)
"""
from __future__ import annotations

import hashlib
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


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_accessible_registry_index(
    root: Path = ROOT,
    exclude: tuple[str, ...] = (),
) -> dict:
    """Build a SHA-verified index over every locally accessible registry TIFF.

    Restored files that occur in the committed inventories must match their
    pins.  Locally published GEMSDOE88 artifacts are Git-tracked evidence and
    are hashed at audit time.  No missing private/unlinked file is implied.
    """
    root = Path(root)
    base = json.loads((root / "registry" / "inventory.json").read_text())
    if not base.get("complete_accessible_scan") or base.get("errors"):
        raise ValueError("base registry inventory is not complete or has errors")
    pins: dict[str, str] = {
        str((root / row["cache_file"]).resolve()): row["sha256"]
        for row in base["rasters"]
    }
    sibling = json.loads((root / "registry" / "sibling_inventory.json").read_text())
    for site, record in sibling["sites"].items():
        for row in record["files"]:
            if row.get("kind") != "tif":
                continue
            flat = f"{site}__{row['path'].replace('/', '__')}"
            pins[str((root / "data" / "siblings" / flat).resolve())] = row["sha256"]

    rows = []
    for label, path in registry_list(root=root, exclude=exclude):
        resolved = str(path.resolve())
        actual = _sha256(path)
        if resolved in pins and pins[resolved] != actual:
            raise ValueError(f"registry SHA-256 pin mismatch: {path}")
        repo = label.split(":", 1)[0]
        rows.append({
            "repo_first": repo,
            "sources": [path.name],
            "cache_file": str(path.relative_to(root)),
            "sha256": actual,
        })
    if len(rows) < len(base["rasters"]):
        raise ValueError("expanded registry is unexpectedly smaller than base inventory")
    return {
        "schema": "gems88.accessible-expanded-registry.v1",
        "complete_accessible_scan": True,
        "errors": [],
        "rasters": rows,
        "scope": (
            "Every restored SHA-pinned base/fleet/sibling TIFF and every tracked "
            "GEMSDOE88 download present in this checkout; private, unlinked or "
            "inaccessible competition submissions are outside scope."
        ),
    }
