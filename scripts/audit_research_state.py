#!/usr/bin/env python3
"""Read-only checks for stale scientific queues and withdrawn GHMD clearance.

No feature/model imports, prediction writing, network access, or slot selection.
A source fingerprint detects drift, not worldwide novelty or scientific validity.
--check-inputs additionally hashes restored data; validation-tier CI need not
restore the full feature raster. Exit 0 means metadata checks passed, never
permission to submit; --require-submit always exits 2 after a successful audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
QUEUE = "registry/hypothesis_queue.json"
LEGACY_CARDS = ("run_card.json", "docs/data/run_card.json", "evidence/run_card.json")
CORRECTION = "evidence/ghmd88_clearance_withdrawal_20261025.json"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def local_file(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"not a repository-relative file: {relative}")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError(f"missing or escaped repository file: {relative}")
    return resolved


def pinned_file(root: Path, relative: str, digest: str) -> Path:
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError(f"invalid SHA-256 pin: {relative}")
    path = local_file(root, relative)
    if sha(path) != digest:
        raise ValueError(f"source/input pin drift: {relative}")
    return path


def model_source_snapshot(root: Path) -> dict:
    """Fingerprint model modules and candidate entrypoints, not this audit."""
    files = set()
    for pattern in ("src/gems88/**/*.py", "vendor/gems57/**/*.py", "scripts/run_*.py",
                    "scripts/build_*.py", "scripts/generate_*.py"):
        files.update(root.glob(pattern))
    if not files:
        raise ValueError("no model source files to review")
    rows = [{"path": p.relative_to(root).as_posix(),
             "sha256": sha(local_file(root, p.relative_to(root).as_posix()))}
            for p in sorted(files)]
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"files": len(rows), "sha256": hashlib.sha256(payload).hexdigest()}


def inspect_queue(root: Path = ROOT, *, check_inputs: bool = False) -> dict:
    root = Path(root)
    queue = json.loads(local_file(root, QUEUE).read_text(encoding="utf-8"))
    if (queue["schema"] != "gems88.hypothesis-queue.v1"
            or queue["ok_to_submit"] is not False
            or queue["generation_authorized"] is not False
            or queue["source_snapshot"] != model_source_snapshot(root)):
        raise ValueError("research queue source snapshot/status drift; review new implementations before ranking")
    published = local_file(root, "docs/data/hypothesis_queue.json").read_bytes()
    if published != local_file(root, QUEUE).read_bytes():
        raise ValueError("published research queue differs from the source-reviewed manifest")
    proposals = queue["proposals"]
    if (not isinstance(proposals, list) or not 3 <= len(proposals) <= 5
            or any(type(p["rank"]) is not int for p in proposals)
            or [p["rank"] for p in proposals] != list(range(1, len(proposals) + 1))):
        raise ValueError("expected 3–5 uniquely ranked proposals")
    retired = queue["already_evaluated"]
    if not {"H88-MMRX", "H88-MTAS", "H88-MFS", "H88-PGTD"}.issubset({p["id"] for p in retired}):
        raise ValueError("known evaluated mechanisms cannot be removed from the review")
    # PGTD implements the generic tensor family formerly proposed as GTD.
    # Different IDs are not physical novelty; do not revive the known alias.
    if any(p["id"] == "H88-GTD" for p in proposals):
        raise ValueError("evaluated PGTD tensor family cannot be revived as untried GTD")
    ids = [p["id"] for p in proposals] + [p["id"] for p in retired]
    if (any(not isinstance(name, str) or re.fullmatch(r"H88-[A-Z0-9]+", name) is None for name in ids)
            or len(ids) != len(set(ids)) or queue["conditional_first_choice"] != proposals[0]["id"]):
        raise ValueError("duplicate or stale first-choice hypothesis")
    for relative, digest in queue["input_pins"].items():
        path = Path(relative)
        if (path.is_absolute() or ".." in path.parts or not relative.startswith("data/")
                or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise ValueError(f"invalid input pin metadata: {relative}")
    required = ("title", "layers", "signature", "off_catalogue_rationale", "non_fault_mimic",
                "difference_from_implemented", "expected_potential", "implementation_cost", "falsification")
    for p in proposals:
        if (p["status"] != "PROPOSED_UNTESTED" or p["new_external_data_required"] is not False
                or any(not p.get(key) for key in required)
                or any(not isinstance(p[key], str) for key in required if key != "layers")):
            raise ValueError(f"incomplete or ineligible proposal: {p['id']}")
        if not p["layers"] or any(layer["file"] not in queue["input_pins"] for layer in p["layers"]):
            raise ValueError(f"unbound input layer: {p['id']}")
        for layer in p["layers"]:
            bands = layer.get("bands")
            if (not isinstance(bands, list) or not bands
                    or any(type(band) is not int or band < 1 for band in bands)
                    or len(bands) != len(set(bands))
                    or not isinstance(layer.get("description"), str) or not layer["description"].strip()):
                raise ValueError(f"unnamed or invalid layer/bands: {p['id']}")
    for row in retired:
        card = json.loads(pinned_file(root, row["run_card"], row["run_card_sha256"]).read_text())
        if card.get("lane") != row["id"] or card.get("verdict") != "negative":
            raise ValueError(f"evaluated lane identity/verdict drift: {row['id']}")
    if check_inputs:
        for relative, digest in queue["input_pins"].items():
            pinned_file(root, relative, digest)
    return queue


def inspect_legacy(root: Path = ROOT) -> dict:
    root = Path(root)
    correction = json.loads(local_file(root, CORRECTION).read_text())
    payloads = [local_file(root, relative).read_bytes() for relative in LEGACY_CARDS]
    if len(set(payloads)) != 1:
        raise ValueError("legacy GHMD mirrors disagree")
    card = json.loads(payloads[0])
    evidence, uniqueness = card["evidence_status"], card["uniqueness"]
    if not (card["verdict"] == "negative" and card["historical_only"] is True
            and card["ok_to_submit"] is False and card["approved_for_weekly_slot"] is False
            and evidence["organizer_confirmed_live_score"] is None
            and evidence["incumbent_organizer_confirmed_live_score"] is None
            and evidence["incumbent_user_reported_claim"] == 0.2778
            and evidence["incumbent_evidence_class"].startswith("USER-REPORTED")
            and uniqueness["unique"] is False and uniqueness["stop_required"] is True
            and uniqueness["literal_overlap_3px"] == 1.0
            and card["correction"]["prediction_bytes_changed"] is False):
        raise ValueError("withdrawn GHMD clearance or unsupported organizer score reintroduced")
    for relative in LEGACY_CARDS:
        pinned_file(root, relative, correction["corrected_metadata_sha256"][relative])
    submission = card["submission"]
    for key, digest_key in (("file", "sha256"), ("repo_copy", "sha256"), ("zip_file", "zip_sha256")):
        if "DO-NOT-SUBMIT" not in Path(submission[key]).name:
            raise ValueError("historical artifact lost its negative filename marker")
        pinned_file(root, submission[key], submission[digest_key])
    if (submission["sha256"] != correction["unchanged_tiff_sha256"]
            or submission["zip_sha256"] != correction["unchanged_zip_sha256"]):
        raise ValueError("historical prediction identity changed")
    return {"mirrors_identical": True, "historical_only": True,
            "organizer_confirmed_score": None, "ok_to_submit": False,
            "raster_sha256": submission["sha256"], "prediction_bytes_changed": False}


def main(argv=None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-inputs", action="store_true")
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args(argv)
    try:
        queue = inspect_queue(root, check_inputs=args.check_inputs)
        legacy = inspect_legacy(root)
        result = {"schema": "gems88.research-state-audit.v1", "status": "PASS",
                  "source_snapshot": queue["source_snapshot"],
                  "conditional_first_choice": queue["conditional_first_choice"],
                  "untested_proposals": [p["id"] for p in queue["proposals"]],
                  "already_evaluated": [p["id"] for p in queue["already_evaluated"]],
                  "input_pins_checked": args.check_inputs, "legacy": legacy,
                  "generation_authorized": False, "ok_to_submit": False, "verdict": "negative"}
        code = 2 if args.require_submit else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"schema": "gems88.research-state-audit.v1", "status": "AUDIT_ERROR",
                  "error": str(exc), "generation_authorized": False,
                  "ok_to_submit": False, "verdict": "negative"}
        code = 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
