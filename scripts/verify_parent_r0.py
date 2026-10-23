#!/usr/bin/env python3
"""Fail-closed startup gate: verify manifest pins and byte-exactly rebuild R0.

No experiment is built and no competition page, leaderboard, or submission
service is contacted. The full 5-stage parent lineage must reproduce both
recorded GeoTIFF SHA-256 values; otherwise the script exits nonzero.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_variants as bpv  # noqa: E402

MANIFEST = ROOT / "registry" / "data_manifest.json"
OUT = ROOT / "registry" / "r0_verification.json"
PARENT_ID = "h33-h33-2-b2"


def main() -> int:
    verified = bpv.verify_manifest(MANIFEST)
    lineage = bpv.rebuild_r0_from_lineage(verified)

    foot = lineage["foot"]
    catalogue = lineage["catalogue"]
    r0 = lineage["r0"]
    d_cat = lineage["d_cat"]
    dvals = d_cat[r0]
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    pins = []
    for entry in entries:
        path = verified[entry["id"]]
        actual_hash = bpv.sha256_file(path)
        actual_bytes = path.stat().st_size
        pins.append(
            {
                "id": entry["id"],
                "path": entry["local_path"],
                "sha256": actual_hash,
                "expected_sha256": entry["sha256"],
                "bytes": actual_bytes,
                "expected_bytes": entry["bytes"],
                "ok": actual_hash == entry["sha256"] and actual_bytes == entry["bytes"],
            }
        )

    report = {
        "schema": "gems88.r0-exact-rebuild.v1",
        "ok": True,
        "parent": PARENT_ID,
        "manifest": {
            "path": "registry/data_manifest.json",
            "schema_version": json.loads(MANIFEST.read_text(encoding="utf-8"))["schema_version"],
            "verified_count": len(pins),
            "all_sha256_and_byte_lengths_match": all(item["ok"] for item in pins),
            "files": pins,
        },
        "lineage_rebuild": {
            "method": "full recorded H19-5 -> D1.5 -> D2.8 -> SOLO-D2.8 -> R0 recipe",
            "pixel_identical_to_pinned_r0": True,
            "intermediate_pixel_checks": ["D1.5", "D2.8", "SOLO-D2.8"],
            "n_dots": int(r0.sum()),
            "zeros_sha256": lineage["rebuilt_zeros_sha256"],
            "expected_zeros_sha256": bpv.PARENT_SHA_ZEROS,
            "zeros_sha256_exact": lineage["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS,
            "nan_sha256": lineage["rebuilt_nan_sha256"],
            "expected_nan_sha256": bpv.PARENT_SHA_NAN,
            "nan_sha256_exact": lineage["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN,
        },
        "parent_geometry": {
            "footprint_px": int(foot.sum()),
            "catalogue_px": int(catalogue.sum()),
            "zero_catalogue_mass": int((r0 & catalogue).sum()) == 0,
            "min_catalogue_distance_px": float(dvals.min()),
            "n_within_2px": int((dvals <= 2.0).sum()),
            "n_within_3px": int((dvals <= 3.0).sum()),
            "dots": int(r0.sum()),
        },
        "note": "R0 SHA-256 equality is mandatory, not approximated; R0 0.2778 remains CLAIM without a submission receipt.",
    }
    report["ok"] = bool(
        report["manifest"]["all_sha256_and_byte_lengths_match"]
        and report["lineage_rebuild"]["n_dots"] == 37_654
        and report["lineage_rebuild"]["zeros_sha256_exact"]
        and report["lineage_rebuild"]["nan_sha256_exact"]
        and report["parent_geometry"]["zero_catalogue_mass"]
        and report["parent_geometry"]["n_within_2px"] == 0
    )
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    summary = {
        "ok": report["ok"],
        "verified_inputs": len(pins),
        "parent_dots": int(r0.sum()),
        "zeros_sha256": lineage["rebuilt_zeros_sha256"],
        "nan_sha256": lineage["rebuilt_nan_sha256"],
        "report": str(OUT.relative_to(ROOT)),
    }
    print(json.dumps(summary, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
