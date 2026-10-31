#!/usr/bin/env python3
"""Read-only cross-site byte-duplicate audit for the user-listed GEMSDOE sites.

For each site repository it lists every ``*.tif`` in the default branch tree via
the GitHub API (``gh api``) and records git blob SHA-1 + size. Two paths with the
same blob SHA are byte-identical files, regardless of filename. This is a
duplicate-bytes check only: it is NOT the registry dot-overlap gate, NOT a score,
and NOT a submission clearance.

Output: ``evidence/site_blob_duplicates_<stamp>.json`` (schema
``gems88.site-blob-duplicates.v1``). Exit 0 on success, 1 if any listing failed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def list_tifs(repo: str) -> list[dict]:
    """Return tif entries of the HEAD tree. Raises RuntimeError on API failure."""
    proc = subprocess.run(
        ["gh", "api", f"repos/{OWNER}/{repo}/git/trees/HEAD?recursive=1"],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{repo}: gh api exit {proc.returncode}: {proc.stderr.strip()[:300]}")
    tree = json.loads(proc.stdout)
    if tree.get("truncated"):
        raise RuntimeError(f"{repo}: git tree truncated; listing incomplete")
    return [
        {"path": e["path"], "blob_sha": e["sha"], "size_bytes": e.get("size")}
        for e in tree.get("tree", [])
        if e.get("type") == "blob" and e["path"].lower().endswith(".tif")
    ]


def build(sites: list[str]) -> dict:
    files, errors = [], []
    for repo in sites:
        try:
            for e in list_tifs(repo):
                files.append({"site": repo, **e})
        except Exception as exc:  # fail-closed: record, keep going, exit nonzero
            errors.append({"site": repo, "error": f"{type(exc).__name__}: {exc}"})
    groups = defaultdict(list)
    for f in files:
        groups[f["blob_sha"]].append(f"{f['site']}:{f['path']}")
    dup_groups = [
        {"blob_sha": sha, "copies": len(paths), "locations": sorted(paths)}
        for sha, paths in groups.items() if len(paths) > 1
    ]
    dup_groups.sort(key=lambda g: (-g["copies"], g["blob_sha"]))
    return {
        "schema": "gems88.site-blob-duplicates.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence_class": "GITHUB-API-LISTING (git blob SHA-1 identity; not a score)",
        "scope": "HEAD tree of each user-listed site repo, *.tif only",
        "sites": sites,
        "tif_files_listed": len(files),
        "distinct_blobs": len(groups),
        "duplicate_blob_groups": len(dup_groups),
        "duplicate_groups": dup_groups,
        "errors": errors,
        "limitations": [
            "Blob identity proves byte equality only; it does not measure dot overlap.",
            "Only default-branch HEAD trees are listed; historical commits are not audited.",
            "Not a registry gate result, not a score, and not submission clearance.",
        ],
        "submission_clearance": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    report = build(SITES)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out = args.out or ROOT / "evidence" / f"site_blob_duplicates_{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"listed={report['tif_files_listed']} distinct_blobs={report['distinct_blobs']} "
          f"duplicate_groups={report['duplicate_blob_groups']} errors={len(report['errors'])} -> {out}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
