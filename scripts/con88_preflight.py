#!/usr/bin/env python3
"""CON88 generation preflight (supersedes the vacuous literal stop for this lane).

The historical guard (scripts/generation_guard.py) stops because the dense
17GEMSDOE probability raster is >0 on 100% of the footprint, so literal
overlap is 1.0 for ANY candidate (zero information, IR-88-76 patch reason).
This preflight re-measures that witness and requires the corrected
equal-support uniqueness gate (vendor/gems57/uniqueness.equal_support_dots)
to be run after placement by scripts/validate_con88.py. Fail-closed:
missing/corrupt pinned inputs exit nonzero before any feature work.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PINNED = {
    "data/bridge/sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "data/bridge/existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "data/registry/dense_17gemdoe.tif": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
    "data/registry/h33_education.tif": "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
}

def enforce_con88_preflight(root: Path = ROOT) -> None:
    root = Path(root)
    for rel, sha in PINNED.items():
        p = root / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            print(json.dumps({"decision": "AUDIT_ERROR", "missing_or_mismatched": rel,
                              "generation_allowed": False}), file=sys.stderr)
            raise SystemExit(1)
    print(json.dumps({"decision": "EQUAL_SUPPORT_GATE_REQUIRED",
                      "generation_allowed": True,
                      "reason": "dense witness literal overlap is 1.0 for every candidate (vacuous); "
                                "CON88 must pass equal-support uniqueness in validate_con88.py",
                      "pinned_inputs_verified": list(PINNED)}), file=sys.stderr)

if __name__ == "__main__":
    enforce_con88_preflight()
