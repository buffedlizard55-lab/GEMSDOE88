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


class SiteListing(list):
    """TIF entries tied to an immutable GitHub commit and root tree."""

    def __init__(self, entries: list[dict], head_commit_sha: str, tree_sha: str):
        super().__init__(entries)
        self.head_commit_sha = head_commit_sha
        self.tree_sha = tree_sha


def _gh_json(endpoint: str, site: str) -> dict:
    proc = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{site}: gh api exit {proc.returncode}: {proc.stderr.strip()[:300]}")
    return json.loads(proc.stdout)


def list_tifs(repo: str) -> SiteListing:
    """List *.tif at an immutable current default-branch commit and pin its tree."""
    commit = _gh_json(f"repos/{OWNER}/{repo}/commits/HEAD", repo)
    commit_sha = commit.get("sha")
    expected_tree_sha = commit.get("commit", {}).get("tree", {}).get("sha")
    if not commit_sha or not expected_tree_sha:
        raise RuntimeError(f"{repo}: commit response has no SHA/tree pin")
    tree = _gh_json(f"repos/{OWNER}/{repo}/git/trees/{expected_tree_sha}?recursive=1", repo)
    if tree.get("truncated"):
        raise RuntimeError(f"{repo}: git tree truncated; listing incomplete")
    if tree.get("sha") != expected_tree_sha:
        raise RuntimeError(f"{repo}: pinned tree SHA differs from commit response")
    entries = [
        {"path": e["path"], "blob_sha": e["sha"], "size_bytes": e.get("size")}
        for e in tree.get("tree", [])
        if e.get("type") == "blob" and e["path"].lower().endswith(".tif")
    ]
    return SiteListing(entries, commit_sha, tree["sha"])


def build(sites: list[str]) -> dict:
    files, errors, snapshots = [], [], []
    for repo in sites:
        try:
            listing = list_tifs(repo)
            snapshots.append({
                "site": repo,
                "head_commit_sha": getattr(listing, "head_commit_sha", None),
                "tree_sha": getattr(listing, "tree_sha", None),
                "tif_files": len(listing),
            })
            files.extend({"site": repo, **e} for e in listing)
        except Exception as exc:  # fail-closed: record, keep going, exit nonzero
            errors.append({"site": repo, "error": f"{type(exc).__name__}: {exc}"})
    files.sort(key=lambda f: (f["site"], f["path"]))
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
        "scope": "Immutable default-branch commit/tree pins for each user-listed site repo; *.tif files only",
        "sites": sites,
        "site_snapshots": snapshots,
        "tif_files_listed": len(files),
        "distinct_blobs": len(groups),
        "duplicate_blob_groups": len(dup_groups),
        "files": files,
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
