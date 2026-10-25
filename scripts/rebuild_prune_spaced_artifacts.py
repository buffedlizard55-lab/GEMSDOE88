#!/usr/bin/env python3
"""Recreate the two already-ledgered spacing-locked PRUNE rasters from scratch.

Both ``(R0, PRUNE, p3space35)`` and ``(R0, PRUNE, p4space35)`` are in
``ledger/submissions.csv`` with recorded SHA-256 values, but their GeoTIFFs are
absent from this checkout (``releases/*.tif`` is gitignored), which blocks the
slot queue: a file that cannot be reproduced cannot be uploaded.  This script is
artifact recovery, exactly like ``scripts/rebuild_prune_artifacts.py``, and it
creates **no** new experiment:

* verify every manifest pin and the byte-exact R0 lineage;
* rebuild the two masks with the recorded recipe (collar purge, then a greedy
  exact-marginal-expected-DTI refill locked at >= 3.5 px from every other dot,
  pool = union of the H19-5 / H19-4 / H16-1 ridge supports outside the collar);
* require the emitted NaN-outside and zeros-outside SHA-256 values to equal the
  ones already in the ledger, and STOP otherwise (never approximate a parent or
  a ledgered arm);
* re-read every written file from disk and run the hardened
  ``scripts/validate_variant.py`` gate on it.

No ledger row is appended or edited, no slot is spent, and no competition page,
leaderboard or submission service is contacted.
"""
from __future__ import annotations

# Historical reconstruction/fitting must not bypass the shared generation stop.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import csv
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from scripts import build_prune_variants as bpv  # noqa: E402
from scripts import build_prune_spaced_variants as bsv  # noqa: E402
from scripts import validate_variant  # noqa: E402

MANIFEST = ROOT / "registry" / "data_manifest.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
RELEASES = ROOT / "releases"
REPORT = ROOT / "evidence" / "prune_spaced_artifact_rebuild.json"

# Ledger-recorded hashes for the two arms; the rebuild must reproduce them byte
# for byte or this script fails closed.
EXPECTED = {
    "p3space35": {
        "sha256": "49fff49b03c47d7ac3822df185f1efd55b0b30855133360689754ce85167a61a",
        "sha256_zeros": "e0b9d59b765a198aa5327bb99bddf09fec52e2806410a403b63ccce2d204824e",
        "collar_px": 3.0,
        "spacing_px": 3.5,
    },
    "p4space35": {
        "sha256": "07bd8182ec4d542aa127601febb2eb37b1458885bce1941593bf846b85f4bb2a",
        "sha256_zeros": "fb7ee110c9ac96a32e53f7d9558bade00d6244f4b5622e35eab83264646e3766",
        "collar_px": 4.0,
        "spacing_px": 3.5,
    },
}
REGISTERED_NOTES = {
    "p3space35": "R0 h33-2-b2; PRUNE<=300m +2171 refill >=3.5px spaced, N 37654; pred +0.007 MODEL",
    "p4space35": "R0 h33-2-b2; PRUNE<=400m +3825 refill >=3.5px spaced, N 37654; pred +0.002 MODEL",
}
PARENT = "h33-h33-2-b2"
AXIS = "PRUNE"
DATE = "20261023"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def ledger_rows() -> list[dict[str, str]]:
    with LEDGER.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def ledger_row(rows: list[dict[str, str]], value: str) -> dict[str, str]:
    matches = [
        row for row in rows
        if row.get("parent") == PARENT and row.get("axis") == AXIS and row.get("value") == value
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one ledger row for {PARENT}/{AXIS}/{value}, got {len(matches)}")
    row = matches[0]
    if row["sha256"] != EXPECTED[value]["sha256"] or row["sha256_zeros"] != EXPECTED[value]["sha256_zeros"]:
        raise ValueError(f"ledger hashes for {value} do not match this script's pins; refusing to guess")
    return row


def main() -> int:
    rows = ledger_rows()
    verified = bpv.verify_manifest(MANIFEST)
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot = lineage["foot"]
    catalogue = lineage["catalogue"]
    d_cat = lineage["d_cat"]
    parent = lineage["r0"]
    if lineage["rebuilt_zeros_sha256"] != bpv.PARENT_SHA_ZEROS or (
        lineage["rebuilt_nan_sha256"] != bpv.PARENT_SHA_NAN
    ):
        raise SystemExit("STOP: R0 rebuild does not byte-match the pinned parent")
    if int(parent.sum()) != 37_654:
        raise SystemExit(f"STOP: unexpected R0 dot count {int(parent.sum())}")

    support_union = np.zeros_like(parent)
    support_parts: dict[str, int] = {}
    for key in bsv.SOURCE_SUPPORTS:
        mask = (np.nan_to_num(rasterio.open(verified[key]).read(1), nan=0.0) > 0) & foot
        support_parts[key] = int(mask.sum())
        support_union |= mask

    weight, canaries = bpv.build_physical_field_and_canaries(
        verified=verified,
        foot=foot,
        catalogue=catalogue,
        h19_5=(np.nan_to_num(rasterio.open(verified["anc_h19_5"]).read(1), nan=0.0) > 0) & foot,
    )
    if not canaries or max(canaries.values()) > 0.90:
        raise SystemExit(f"STOP: leakage canary failure {canaries}")

    existing_shas = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}
    for row in rows:
        existing_shas.update(v for v in (row.get("sha256"), row.get("sha256_zeros")) if v)

    results: dict[str, Any] = {}
    for value, pin in EXPECTED.items():
        row = ledger_row(rows, value)
        collar = float(pin["collar_px"])
        survivors = parent & (d_cat > collar)
        removed = int(parent.sum() - survivors.sum())
        pool = support_union & ~survivors & (d_cat > collar)
        candidate, lock_stats = bsv.spaced_marginal_add(
            base_mask=survivors,
            cand_mask=pool,
            w=weight,
            n_add=removed,
            spacing_px=float(pin["spacing_px"]),
        )
        if int(candidate.sum()) != 37_654:
            raise SystemExit(f"STOP: fixed-count invariant failed for {value}")
        if float(d_cat[candidate].min()) < 3.0:
            raise SystemExit(f"STOP: {value} violates the 3 px collar")
        if int((candidate & catalogue).sum()) != 0:
            raise SystemExit(f"STOP: {value} emits mass on the catalogue")

        # The note is the arm's registered form note (evidence/prune_spaced_report.json),
        # reproduced verbatim so the rebuilt receipt matches the ledgered arm exactly.
        note = REGISTERED_NOTES[value]
        receipt = bpv.write_and_verify_variant(
            mask=candidate,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=parent,
            axis=AXIS,
            value=value,
            note_template=note,
            existing_shas=existing_shas - {pin["sha256"], pin["sha256_zeros"]},
            parent_id=PARENT,
            parent_sha_zeros=bpv.PARENT_SHA_ZEROS,
            parent_sha_nan=bpv.PARENT_SHA_NAN,
            date=DATE,
            min_catalogue_px=3.0,
        )
        got = (receipt["sha256"], receipt["sha256_zeros"])
        want = (pin["sha256"], pin["sha256_zeros"])
        exact = got == want
        if not exact:
            raise SystemExit(
                f"STOP: {value} reconstruction SHA mismatch\n  got  {got[0]}\n  want {want[0]}"
            )
        if receipt["id"] != row["id"]:
            raise SystemExit(f"STOP: id mismatch for {value}: {receipt['id']} != {row['id']}")

        results[value] = {
            "ledger_id": row["id"],
            "sha256": got[0],
            "sha256_zeros": got[1],
            "expected_sha256": want[0],
            "expected_sha256_zeros": want[1],
            "byte_exact": exact,
            "n_dots": receipt["n_dots"],
            "collar_px": collar,
            "spacing_px": float(pin["spacing_px"]),
            "n_removed": removed,
            "n_added": receipt["parent_diff"]["n_added"],
            "min_catalogue_distance_px": receipt["parent_diff"]["min_dist_catalogue_px"],
            "refill_spacing_pool_cells": lock_stats["spacing_pool_cells"],
            "refill_min_nn_px": receipt["parent_diff"].get("refill_min_nn_px"),
            "file_nan": receipt["file_nan"],
            "file_zeros": receipt["file_zeros"],
            "form_note": receipt["form_note"],
            "gates": receipt["gates"],
        }

    # Independent hardened gate on the released bytes (reads from disk itself).
    gate_out = ROOT / "registry" / "prune_spaced_rebuild_validation.json"
    sys.argv = [
        "validate_variant.py",
        *[str(RELEASES / f"{item['ledger_id']}.tif") for item in results.values()],
        *[str(RELEASES / f"{item['ledger_id']}-zeros.tif") for item in results.values()],
        "--out", str(gate_out),
    ]
    gate_rc = validate_variant.main()
    if gate_rc != 0:
        raise SystemExit("STOP: hardened validator rejected a rebuilt artifact")
    payload = {
        "schema": "gems88.prune-spaced-artifact-rebuild.v1",
        "created_utc": utc_now(),
        "purpose": (
            "Recreate the two ledgered spacing-locked PRUNE rasters that are absent from this "
            "checkout so the slot queue is executable. No new experiment, no ledger edit, no slot."
        ),
        "git_sha": git_value("rev-parse", "HEAD"),
        "manifest": {
            "path": "registry/data_manifest.json",
            "verified_input_count": len(verified),
            "all_manifest_inputs_verified": True,
        },
        "parent": {
            "id": PARENT,
            "n_dots": int(parent.sum()),
            "zeros_sha256": lineage["rebuilt_zeros_sha256"],
            "nan_sha256": lineage["rebuilt_nan_sha256"],
            "byte_exact": True,
        },
        "source_support_pixels": support_parts,
        "leakage_canaries": {"passed": True, "max": max(canaries.values())},
        "arms": results,
        "all_byte_exact": all(item["byte_exact"] for item in results.values()),
        "hardened_validator": {"out": "registry/prune_spaced_rebuild_validation.json", "returncode": 0},
        "no_submission": True,
        "slots_used": 0,
    }
    REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": payload["all_byte_exact"], "arms": {
        k: {"sha8": v["sha256"][:8], "id": v["ledger_id"]} for k, v in results.items()
    }, "report": str(REPORT.relative_to(ROOT))}, indent=2))
    return 0 if payload["all_byte_exact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
