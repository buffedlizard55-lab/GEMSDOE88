#!/usr/bin/env python3
"""Audit the brief-v2 startup and stop before rebuilding an exhausted PRUNE axis.

Offline after the explicit SHA-pinned restore. No candidate, submission, or new
ledger row is created. Historical release JSON is evidence, not a fresh TIFF
validation or a portal receipt. The current audit is written to ignored .cache;
it does not overwrite the original 2026-10-23 evidence.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import verify_parent_r0  # noqa: E402


def radius(value: str) -> Decimal | None:
    text = value.strip().lower().removeprefix("p").removesuffix("px")
    try:
        return Decimal(text) if Decimal(text).is_finite() else None
    except InvalidOperation:
        return None


def prune_coverage(rows: list[dict]) -> dict:
    result = {}
    for threshold in (1, 2, 3):
        matches = [r["id"] for r in rows if r["parent"] == "h33-h33-2-b2"
                   and r["axis"] == "PRUNE" and radius(r["value"]) == threshold]
        result[str(threshold)] = {
            "existing_ids": matches,
            "is_parent": threshold == 2,
            "do_not_build": bool(matches) or threshold == 2,
        }
    return result


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def hash_relationships(rows: list[dict]) -> dict:
    """Distinguish aliases within one ledger row from cross-record duplicates.

    The same all-finite file can be both primary and fallback for one record;
    that is not a new candidate. Reuse across *different rows* remains a failure,
    including when duplicated rows have the same ID or swapped hash columns.
    """
    owners: dict[str, set[int]] = {}
    occurrences: dict[str, int] = {}
    same_row_aliases = []
    unresolved = []
    for index, row in enumerate(rows):
        primary, fallback = row.get("sha256", ""), row.get("sha256_zeros", "")
        primary_valid = isinstance(primary, str) and bool(re.fullmatch(r"[0-9a-f]{64}", primary))
        if primary and not primary_valid:
            unresolved.append({"id": row.get("id"), "row_index": index, "field": "sha256"})
        # One historical row uses a symbolic reference rather than repeating
        # the full fallback hash. Accept it only if its prefix matches the full
        # primary SHA; arbitrary strings are unresolved, not unique hashes.
        alias = (re.fullmatch(r"zeros-variant-is-primary:([0-9a-f]{8,64})", fallback)
                 if isinstance(fallback, str) else None)
        if alias and primary_valid and primary.startswith(alias.group(1)):
            fallback_digest = primary
            representation = "primary-reference"
        elif isinstance(fallback, str) and re.fullmatch(r"[0-9a-f]{64}", fallback):
            fallback_digest = fallback
            representation = "identical-digest"
        else:
            fallback_digest = ""
            representation = None
            if fallback:
                unresolved.append({"id": row.get("id"), "row_index": index, "field": "sha256_zeros"})
        if primary_valid and primary == fallback_digest:
            same_row_aliases.append({"id": row.get("id"), "row_index": index, "sha256": primary,
                                     "representation": representation})
        for digest in (primary if primary_valid else "", fallback_digest):
            if digest:
                owners.setdefault(digest, set()).add(index)
                occurrences[digest] = occurrences.get(digest, 0) + 1
    cross_rows = [{"sha256": digest, "row_indices": sorted(indices),
                   "ids": [rows[i].get("id") for i in sorted(indices)]}
                  for digest, indices in sorted(owners.items()) if len(indices) > 1]
    return {"all_hash_values_distinct": not unresolved and all(count == 1 for count in occurrences.values()),
            "different_rows_have_distinct_hashes": not unresolved and not cross_rows,
            "all_hash_fields_resolved": not unresolved,
            "unresolved_hash_fields": unresolved,
            "same_row_primary_fallback_aliases": same_row_aliases,
            "cross_row_duplicates": cross_rows}


def main(argv: list[str] | None = None) -> int:
    # Parse before touching inputs so --help is safe on a fresh checkout.
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    # Fail closed: verify every input, intermediate lineage and both parent
    # hashes, but do not rewrite the historical tracked verification report.
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    out = cache / "session-start-audit-current.json"
    # A failed or interrupted rerun must never leave a prior PASS looking fresh.
    out.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="r0-audit-", dir=cache) as directory:
        parent_path = Path(directory) / "r0.json"
        if verify_parent_r0.main(parent_path) != 0:
            return 1
        parent = json.loads(parent_path.read_text())
    ledger_bytes = (ROOT / "ledger/submissions.csv").read_bytes()
    rows = list(csv.DictReader(io.StringIO(ledger_bytes.decode())))
    remote_bytes = subprocess.check_output(
        ["git", "show", "origin/main:ledger/submissions.csv"], cwd=ROOT)
    remote_rows = list(csv.DictReader(io.StringIO(remote_bytes.decode())))
    coverage = prune_coverage(rows + remote_rows)
    # Collapse duplicated local/remote IDs in the coverage display only.
    for arm in coverage.values():
        arm["existing_ids"] = sorted(set(arm["existing_ids"]))
    relationships = hash_relationships(rows)
    pairs = [(r["parent"], r["axis"], r["value"]) for r in rows]
    tracked_bulk = [p for p in git("ls-files").splitlines()
                    if p.endswith((".tif", ".zip"))]
    cards = {}
    for stem in ("h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705",
                 "h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4"):
        card = json.loads((ROOT / "releases" / f"{stem}.json").read_text())
        cards[stem] = {
            "evidence": "HISTORICAL_BUILD_RECORD_NOT_FRESH_VALIDATION",
            "minimum_catalogue_distance_px": card["parent_diff"]["min_dist_catalogue_px"],
            "collar_eligible_from_record": card["axis"] == "PRUNE" or
                card["parent_diff"]["min_dist_catalogue_px"] >= 3,
            "local_primary_present": (ROOT / card["file_nan"]).is_file(),
            "predicted_change": next(r["predicted_change"] for r in rows if r["id"] == stem),
        }
    report = {
        "schema": "gems88.session-start-audit.v2",
        "date_utc": datetime.now(timezone.utc).date().isoformat(),
        "historical_prune_origin_date": "2026-10-23",
        "git_sha": git("rev-parse", "HEAD"),
        "origin_main_local_ref": git("rev-parse", "origin/main"),
        "axis": "PRUNE",
        "manifest_inputs_verified": parent["manifest"]["verified_count"],
        "r0_exact_rebuild": parent["ok"],
        "parent_geometry": parent["parent_geometry"],
        "ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
        "ledger_rows": len(rows),
        "remote_ledger_rows": len(remote_rows),
        "unique_primary_and_fallback_hashes": relationships["all_hash_values_distinct"],
        "different_rows_have_distinct_hashes": relationships["different_rows_have_distinct_hashes"],
        "all_hash_fields_resolved": relationships["all_hash_fields_resolved"],
        "unresolved_hash_fields": relationships["unresolved_hash_fields"],
        "same_row_primary_fallback_aliases": relationships["same_row_primary_fallback_aliases"],
        "cross_row_hash_duplicates": relationships["cross_row_duplicates"],
        "unique_literal_parent_axis_value": len(pairs) == len(set(pairs)),
        "portal_receipts_with_score_and_date": sum(bool(r["receipt_score"] and r["receipt_date"]) for r in rows),
        "requested_prune_radii_px": coverage,
        "decision": "STOP_NO_NEW_VARIANTS" if all(a["do_not_build"] for a in coverage.values()) else "REVIEW_UNBUILT_ARM",
        "new_variants": 0,
        "new_ledger_rows": 0,
        "historical_cards": cards,
        "preexisting_tracked_tif_zip_paths_data_use_unchecked": tracked_bulk,
        "limitations": ["This startup audit makes no external rules/deadline request.",
                        "origin/main is a local ref, not proof of a fresh remote fetch.",
                        "TOP_PUBLIC and rolling-week slot balance are not checked by this startup audit.",
                        "Inspected PRUNEp3px/SNAPscarp2px TIFFs absent; no fresh candidate validation.",
                        "No holdout, leakage-canary, or SGMC rerun; no new model field or candidate."],
    }
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"decision": report["decision"], "ledger_rows": len(rows),
                      "different_rows_have_distinct_hashes": report["different_rows_have_distinct_hashes"],
                      "same_row_primary_fallback_aliases": len(report["same_row_primary_fallback_aliases"]),
                      "report": str(out.relative_to(ROOT))}))
    return 0 if report["different_rows_have_distinct_hashes"] and report["unique_literal_parent_axis_value"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
