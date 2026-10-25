#!/usr/bin/env python3
"""Reopen every published research TIFF and ZIP; no predictions are generated.

The manifest separates local format validity from competition eligibility.
Exact decoded-field duplicates are reported even if TIFF metadata/hashes differ.
A single SHA-pinned saturation witness rejects eligibility; this is deliberately
NOT advertised as an exhaustive registry correlation/overlap clearance.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from scripts.preflight_mtas88 import inspect as preflight  # noqa: E402
from scripts.validate_artifact import validate_artifact  # noqa: E402

OUTPUTS = ("evidence/download_audit.json", "docs/data/download_audit.json")
# Two existing publication namespaces. A historical same-lane variant remains
# outside the modeling registry, but must not be outside the file safety audit.
PUBLICATION_DIRECTORIES = ("downloads", "research-variants")


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit_one(path: Path, sample: Path, catalogue: np.ndarray, footprint: np.ndarray) -> dict:
    result = {
        "file": path.name,
        "sha256": sha(path),
        "bytes": path.stat().st_size,
        "evidence_class": "LOCAL-FORMAT-AUDIT_NOT_ORGANIZER_ACCEPTANCE",
        "format_valid": False,
        "research_download_ok": False,
        "ok_to_submit": False,
        "errors": [],
    }
    try:
        checks = validate_artifact(path, sample)
        result["validator_output"] = checks
        with rasterio.open(path) as source:
            values = source.read(1)
            result["grid"] = {
                "shape": list(source.shape), "crs": str(source.crs),
                "transform": list(source.transform)[:6],
                "bands": source.count, "dtype": source.dtypes[0],
            }
        # Independent decoder catches layout/codec issues, rather than trusting
        # a self-reported writer receipt or rasterio alone.
        decoded = tifffile.imread(path)
        result["independent_decoders_agree"] = bool(np.array_equal(values, decoded, equal_nan=True))
        del decoded
        if values.shape != footprint.shape or np.iscomplexobj(values):
            raise ValueError("invalid shape or complex-valued prediction")
        positive = np.isfinite(values) & (values > 0)
        result["positive_pixels"] = int(positive.sum())
        result["positive_on_catalogue"] = int((positive & catalogue).sum())
        result["positive_outside_footprint"] = int((positive & ~footprint).sum())
        result["decoded_float32_sha256"] = hashlib.sha256(
            np.ascontiguousarray(values, dtype="<f4").tobytes()).hexdigest()
        result["positive_support_sha256"] = hashlib.sha256(
            np.packbits(positive.ravel(), bitorder="little").tobytes()).hexdigest()
        result["format_valid"] = checks["ok"] and result["independent_decoders_agree"]
        archive = path.with_suffix(".zip")
        result["zip_file"] = archive.name
        result["zip_sha256"] = sha(archive)
        with zipfile.ZipFile(archive) as z:
            result["zip_one_byte_identical_tif"] = (
                z.namelist() == [path.name] and z.read(path.name) == path.read_bytes()
            )
        result["negative_filename_markers"] = all(
            "DO-NOT-SUBMIT" in item.name for item in (path, archive)
        )
        # Local file validity never grants competition clearance. The shared
        # protocol currently blocks every nonempty prediction; published bytes
        # must carry an explicit negative filename marker.
        result["ok_to_submit"] = False
        result["research_download_ok"] = bool(
            result["format_valid"] and result["zip_one_byte_identical_tif"]
            and result["negative_filename_markers"]
            and result["positive_pixels"] > 0
            and result["positive_on_catalogue"] == 0
            and result["positive_outside_footprint"] == 0
        )
        if not result["research_download_ok"]:
            result["errors"].append("Failed at least one format, footprint, catalogue, ZIP or labeling check")
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    return result


def published_tiffs(root: Path, directory: str = "downloads") -> list[Path]:
    """Do not silently ignore .tiff or uppercase filename suffixes."""
    if directory not in PUBLICATION_DIRECTORIES:
        raise ValueError(f"Unknown publication directory: {directory}")
    base = root / "docs" / directory
    if directory != "downloads" and not base.exists():
        return []
    return sorted(p for p in base.iterdir()
                  if p.is_file() and p.suffix.lower() in {".tif", ".tiff"})


def check_package_inventory(root: Path) -> None:
    """Every published ZIP must have exactly one audited TIFF partner.

    Both existing publication namespaces are flat. Without this check an
    orphan ZIP, uppercase .ZIP, nested artifact, or historical research variant
    is silently omitted by a downloads-only audit even though Pages serves it.
    Symlinked directories and entries are rejected, including dangling links.
    Sidecars are rejected separately by the self-contained TIFF format check.
    """
    root = Path(root)
    docs = root / "docs"
    for name in PUBLICATION_DIRECTORIES:
        directory = docs / name
        if directory.is_symlink():
            raise ValueError(f"Symlinks are not audited publication artifacts: {directory}")
        entries = list(directory.rglob("*"))
        links = sorted(str(p.relative_to(directory)) for p in entries if p.is_symlink())
        if links:
            raise ValueError(f"Symlinks are not audited publication artifacts in {name}: {links}")
        artifacts = [p for p in entries
                     if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"}]
        nested = sorted(str(p.relative_to(directory)) for p in artifacts if p.parent != directory)
        if nested:
            raise ValueError(f"Nested published artifacts are outside the flat audited inventory (unaudited nested TIFF/ZIP): {nested}")
        tiffs = published_tiffs(root, name)
        expected = [p.with_suffix(".zip") for p in tiffs]
        if len(expected) != len(set(expected)):
            raise ValueError("Multiple TIFFs share the same ZIP path")
        actual = {p for p in artifacts if p.suffix.lower() == ".zip"}
        missing = sorted(p.name for p in set(expected) - actual)
        orphaned = sorted(p.name for p in actual - set(expected))
        if missing or orphaned:
            raise ValueError(f"Published TIFF/ZIP inventory mismatch in {name}: missing ZIPs={missing}; orphan ZIPs={orphaned}")
    known = {docs / name for name in PUBLICATION_DIRECTORIES}
    unknown = sorted(str(p.relative_to(docs)) for p in docs.rglob("*")
                     if p.is_file() and p.suffix.lower() in {".tif", ".tiff", ".zip"}
                     and p.parent not in known)
    if unknown:
        raise ValueError(f"Published artifacts outside the declared audited directories: {unknown}")


def publication_inventory(root: Path) -> list[Path]:
    """Compatibility API: main download TIFFs after the shared full inventory check.

    Historical callers keep their main-download count; variant packages are
    checked by the same policy and audited separately in schema v2.
    """
    root = Path(root)
    check_package_inventory(root)
    paths = published_tiffs(root)
    if not paths:
        raise ValueError("no published research TIFFs found")
    return paths


def audit(root: Path = ROOT) -> dict:
    root = Path(root)
    paths = publication_inventory(root)
    prerequisite = preflight(root)
    certificate = prerequisite["preplacement_registry_proof"]
    if certificate["universal_overlap_blocker"] is not True or certificate["directly_saturated"] is not True:
        raise ValueError("universal literal stop did not reproduce; no stale eligibility may be used")
    sample = root / "data/bridge/sample_submission.tif"
    with rasterio.open(sample) as s:
        footprint = np.isfinite(s.read(1)) & (s.read_masks(1) > 0)
    with rasterio.open(root / "data/bridge/existing_faults.tif") as s:
        catalogue = (s.read(1) > 0) & footprint
    rows = [audit_one(path, sample, catalogue, footprint) for path in paths]
    additional = []
    for directory in PUBLICATION_DIRECTORIES[1:]:
        for path in published_tiffs(root, directory):
            row = audit_one(path, sample, catalogue, footprint)
            row["publication_directory"] = directory
            additional.append(row)
    by_field: dict[str, list[str]] = defaultdict(list)
    for row in rows + additional:
        if row.get("decoded_float32_sha256"):
            identifier = row["file"] if "publication_directory" not in row else f'{row["publication_directory"]}/{row["file"]}'
            by_field[row["decoded_float32_sha256"]].append(identifier)
        admissible = (row.get("positive_pixels", 0) > 0
                      and row.get("positive_on_catalogue") == 0
                      and row.get("positive_outside_footprint") == 0)
        row["literal_overlap_lower_bound"] = 1.0 if admissible else None
        row["decision"] = "DUPLICATE_STOP" if admissible else "RESEARCH_ARTIFACT_INVALID"
    release = json.loads((root / "docs/data/current_release.json").read_text())
    current = next((r for r in rows if r["file"] == Path(release["file"]).name), None)
    if (current is None or current["sha256"] != release["file_sha256"]
            or current.get("zip_sha256") != release["zip_sha256"]
            or not current["research_download_ok"]):
        raise ValueError("canonical research TIFF/ZIP missing, changed or invalid")
    return {
        "schema": "gems88.download-audit.v2",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Every TIFF in docs/downloads and docs/research-variants, paired ZIP, two decoders, exact-value duplicate groups; NOT full-fleet scientific uniqueness",
        "preplacement_registry_proof": certificate,
        "canonical_file": current["file"],
        "canonical_sha256": current["sha256"],
        "tiff_count": len(rows),
        "research_download_pass_count": sum(r["research_download_ok"] for r in rows),
        "additional_research_tiff_count": len(additional),
        "total_published_tiff_count": len(rows) + len(additional),
        "total_research_download_pass_count": sum(r["research_download_ok"] for r in rows + additional),
        "additional_research_artifacts": additional,
        "protocol_eligible_count": 0,
        "exact_decoded_duplicate_groups": [
            {"decoded_float32_sha256": digest, "files": names}
            for digest, names in sorted(by_field.items()) if len(names) > 1
        ],
        "artifacts": rows,
        "new_tiffs_generated": 0,
        "ok_to_submit": False,
        "verdict": "negative",
    }


def write(root: Path, result: dict) -> None:
    payload = json.dumps(result, indent=2, allow_nan=False) + "\n"
    for relative in OUTPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)


def main(argv=None, root: Path = ROOT) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true", help="Recompute and compare, ignoring only the audit timestamp")
    args = p.parse_args(argv)
    try:
        result = audit(root)
        all_rows = result["artifacts"] + result.get("additional_research_artifacts", [])
        if (result["research_download_pass_count"] != result["tiff_count"]
                or any(not r["research_download_ok"] for r in all_rows)):
            bad = [r["file"] for r in all_rows if not r["research_download_ok"]]
            raise ValueError(f"Invalid published TIFF/ZIP pair(s): {bad}")
        if args.check:
            for relative in OUTPUTS:
                stored = json.loads((root / relative).read_text())
                stored.pop("checked_at_utc", None)
                actual = {k: v for k, v in result.items() if k != "checked_at_utc"}
                if stored != actual:
                    raise ValueError(f"Stale or altered download audit: {relative}")
        else:
            write(root, result)
        print(json.dumps({k: result[k] for k in ("tiff_count", "research_download_pass_count", "additional_research_tiff_count", "total_published_tiff_count", "total_research_download_pass_count", "protocol_eligible_count", "exact_decoded_duplicate_groups")}))
        return 0
    except Exception as exc:
        failed = {"schema": "gems88.download-audit.v2", "decision": "AUDIT_ERROR",
                  "error": f"{type(exc).__name__}: {exc}", "ok_to_submit": False,
                  "verdict": "negative", "research_download_pass_count": 0}
        if not args.check:
            write(root, failed)  # invalidate stale success on any failed fresh audit
        print(json.dumps(failed), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
