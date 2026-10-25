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
        # Labeling rule: a file carries DO-NOT-SUBMIT unless (and only unless)
        # a versioned run card promotes exactly these bytes; checked in audit().
        result["labels_consistent"] = (
            all("DO-NOT-SUBMIT" in item.name for item in (path, archive))
            or all("DO-NOT-SUBMIT" not in item.name for item in (path, archive))
        )
        result["research_download_ok"] = bool(
            result["format_valid"] and result["zip_one_byte_identical_tif"]
            and result["labels_consistent"]
            and result["positive_pixels"] > 0
            and result["positive_on_catalogue"] == 0
            and result["positive_outside_footprint"] == 0
        )
        if not result["research_download_ok"]:
            result["errors"].append("Failed at least one format, footprint, catalogue, ZIP or labeling check")
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    return result


def published_tiffs(root: Path) -> list[Path]:
    """Do not silently ignore .tiff or uppercase filename suffixes."""
    return sorted(p for p in (root / "docs/downloads").iterdir()
                  if p.is_file() and p.suffix.lower() in {".tif", ".tiff"})


def audit(root: Path = ROOT) -> dict:
    root = Path(root)
    prerequisite = preflight(root)
    certificate = prerequisite["preplacement_registry_proof"]
    if certificate["universal_overlap_blocker"] is not True or certificate["directly_saturated"] is not True:
        raise ValueError("dense witness measurement did not reproduce; no stale eligibility may be used")
    # IR-88-SDTL-01: eligibility is decided per file by a versioned run card
    # (equal-support uniqueness + holdout + validator), never by the literal
    # all-positive witness alone. Only cards that exist and say promote count.
    eligible: dict[str, dict] = {}
    for card_path in sorted((root / "registry").glob("*_run_card.json")):
        try:
            card = json.loads(card_path.read_text())
        except (OSError, ValueError):
            continue
        raster = card.get("raster") if isinstance(card.get("raster"), dict) else None
        if (card.get("schema") == "gems88.run_card.v2" and card.get("ok_to_submit") is True
                and card.get("verdict") == "promote" and raster):
            eligible[Path(raster["file"]).name] = dict(sha256=raster["sha256"], card=card_path.name)
    sample = root / "data/bridge/sample_submission.tif"
    with rasterio.open(sample) as s:
        footprint = np.isfinite(s.read(1)) & (s.read_masks(1) > 0)
    with rasterio.open(root / "data/bridge/existing_faults.tif") as s:
        catalogue = (s.read(1) > 0) & footprint
    paths = published_tiffs(root)
    if not paths:
        raise ValueError("no published research TIFFs found")
    rows = [audit_one(path, sample, catalogue, footprint) for path in paths]
    by_field: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get("decoded_float32_sha256"):
            by_field[row["decoded_float32_sha256"]].append(row["file"])
        admissible = (row.get("positive_pixels", 0) > 0
                      and row.get("positive_on_catalogue") == 0
                      and row.get("positive_outside_footprint") == 0)
        row["literal_overlap_lower_bound"] = 1.0 if admissible else None
        card = eligible.get(row["file"])
        if card and admissible and card["sha256"] == row["sha256"] and row.get("research_download_ok"):
            row["decision"] = "PROMOTE_EQUAL_SUPPORT_V5"
            row["ok_to_submit"] = True
            row["run_card"] = card["card"]
        else:
            row["decision"] = "DO_NOT_SUBMIT" if admissible else "RESEARCH_ARTIFACT_INVALID"
            if not row.get("negative_filename_markers") and row.get("research_download_ok"):
                # An unpromoted file without the negative marker is a labeling fault.
                row["research_download_ok"] = False
                row["errors"].append("unpromoted file lacks DO-NOT-SUBMIT marker")
    release = json.loads((root / "docs/data/current_release.json").read_text())
    current = next((r for r in rows if r["file"] == Path(release["file"]).name), None)
    if (current is None or current["sha256"] != release["file_sha256"]
            or current.get("zip_sha256") != release["zip_sha256"]
            or not current["research_download_ok"]):
        raise ValueError("canonical research TIFF/ZIP missing, changed or invalid")
    return {
        "schema": "gems88.download-audit.v2",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Every TIFF in docs/downloads, paired ZIP, two decoders, exact-value duplicate groups; NOT full-fleet scientific uniqueness",
        "preplacement_registry_proof": certificate,
        "canonical_file": current["file"],
        "canonical_sha256": current["sha256"],
        "tiff_count": len(rows),
        "research_download_pass_count": sum(r["research_download_ok"] for r in rows),
        "protocol_eligible_count": sum(1 for r in rows if r.get("ok_to_submit") is True),
        "protocol_eligible_files": [r["file"] for r in rows if r.get("ok_to_submit") is True],
        "exact_decoded_duplicate_groups": [
            {"decoded_float32_sha256": digest, "files": names}
            for digest, names in sorted(by_field.items()) if len(names) > 1
        ],
        "artifacts": rows,
        "new_tiffs_generated": 0,
        "ok_to_submit": bool(current.get("ok_to_submit") is True),
        "verdict": "promote" if current.get("ok_to_submit") is True else "negative",
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
        if result["research_download_pass_count"] != result["tiff_count"]:
            bad = [r["file"] for r in result["artifacts"] if not r["research_download_ok"]]
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
        print(json.dumps({k: result[k] for k in ("tiff_count", "research_download_pass_count", "protocol_eligible_count", "exact_decoded_duplicate_groups")}))
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
