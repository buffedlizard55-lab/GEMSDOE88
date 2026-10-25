#!/usr/bin/env python3
"""Audit startup state and stop before rebuilding an exhausted PRUNE axis.

Offline after the explicit SHA-pinned restore. No candidate, submission, or new
ledger row is created. Historical release JSON is evidence, not a fresh TIFF
validation or a portal receipt. The current receipt is written only to ignored
``.cache`` state; dated historical evidence is never overwritten.
"""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

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


def main() -> int:
    # Fail closed: this verifies every input, intermediate lineage, and both
    # parent file hashes. Never reuse an old successful report after failure.
    if verify_parent_r0.main() != 0:
        return 1
    parent = json.loads((ROOT / "registry/r0_verification.json").read_text())
    ledger_bytes = (ROOT / "ledger/submissions.csv").read_bytes()
    rows = list(csv.DictReader(io.StringIO(ledger_bytes.decode())))
    remote_bytes = subprocess.check_output(
        ["git", "show", "origin/main:ledger/submissions.csv"], cwd=ROOT)
    remote_rows = list(csv.DictReader(io.StringIO(remote_bytes.decode())))
    coverage = prune_coverage(rows + remote_rows)
    # Collapse duplicated local/remote IDs in the coverage display only.
    for arm in coverage.values():
        arm["existing_ids"] = sorted(set(arm["existing_ids"]))
    # A zeros-safe artifact may intentionally use the same byte identity in its
    # primary and fallback columns. Reject reuse across *different entries*, not
    # the same row's two aliases.
    hash_owners: dict[str, set[str]] = {}
    for row in rows:
        for key in ("sha256", "sha256_zeros"):
            if row[key]:
                hash_owners.setdefault(row[key], set()).add(row["id"])
    unique_hash_owners = all(len(owners) == 1 for owners in hash_owners.values())
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
        "schema": "gems88.session-start-audit.v1",
        "date_utc": "2026-10-23",
        "git_sha": git("rev-parse", "HEAD"),
        "origin_main_sha_at_explicit_fetch": git("rev-parse", "origin/main"),
        "axis": "PRUNE",
        "manifest_inputs_verified": parent["manifest"]["verified_count"],
        "r0_exact_rebuild": parent["ok"],
        "parent_geometry": parent["parent_geometry"],
        "ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
        "ledger_rows": len(rows),
        "remote_ledger_rows": len(remote_rows),
        "unique_primary_and_fallback_hashes": unique_hash_owners,
        "unique_literal_parent_axis_value": len(pairs) == len(set(pairs)),
        "portal_receipts_with_score_and_date": sum(bool(r["receipt_score"] and r["receipt_date"]) for r in rows),
        "requested_prune_radii_px": coverage,
        "decision": "STOP_NO_NEW_VARIANTS" if all(a["do_not_build"] for a in coverage.values()) else "REVIEW_UNBUILT_ARM",
        "new_variants": 0,
        "new_ledger_rows": 0,
        "historical_cards": cards,
        "preexisting_tracked_tif_zip_paths_data_use_unchecked": tracked_bulk,
        "limitations": ["No external rules/deadline verification; prohibited domains not contacted.",
                        "TOP_PUBLIC and rolling-week slot balance unknown in current brief.",
                        "Inspected PRUNEp3px/SNAPscarp2px TIFFs absent; no fresh candidate validation.",
                        "No holdout, leakage-canary, or SGMC rerun; no new model field or candidate."],
    }
    # The 2026-10-23 receipt is immutable historical evidence. A current startup
    # audit belongs in ignored runtime state rather than rewriting old counts.
    out = ROOT / ".cache/session-start-audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"decision": report["decision"], "ledger_rows": len(rows), "report": str(out.relative_to(ROOT))}))
    return 0 if report["unique_primary_and_fallback_hashes"] and report["unique_literal_parent_axis_value"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
