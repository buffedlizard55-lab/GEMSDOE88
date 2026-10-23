#!/usr/bin/env python3
"""Restore only this session's SHA-pinned inputs from public GitHub mirrors.

No DrivenData/Dropbox access, login, token, or credential handling is used.
Existing corrupted files are never overwritten.  ``--verify-only`` performs the
startup hash gate without network access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "data_manifest.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    files = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    if args.verify_only:
        for item in files:
            path = ROOT / item["dest"]
            if not path.is_file() or digest(path) != item["sha256"]:
                raise ValueError(f"missing or bad pinned input: {path}")
            print(f"PIN OK {item['id']} {item['sha256']}")
        return 0

    (ROOT / "data").mkdir(exist_ok=True)
    groups: dict[tuple[str, str], list[dict]] = {}
    for item in files:
        groups.setdefault((item["repo"], item["ref"]), []).append(item)
    for (repo, ref), items in groups.items():
        if all((ROOT / item["dest"]).is_file() and digest(ROOT / item["dest"]) == item["sha256"] for item in items):
            print(f"PIN OK {repo} ({len(items)} files)")
            continue
        for item in items:
            dest = ROOT / item["dest"]
            if dest.exists() and digest(dest) != item["sha256"]:
                raise ValueError(f"PIN MISMATCH; refusing to overwrite {dest}")
        with tempfile.TemporaryDirectory(prefix="r0-prune-restore-", dir=ROOT / "data") as tmp:
            checkout = Path(tmp) / "mirror"
            subprocess.run(
                ["git", "clone", "--quiet", "--depth=1", "--filter=blob:none", "--sparse", f"https://github.com/{repo}.git", str(checkout)],
                check=True,
            )
            if subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip() != ref:
                subprocess.run(["git", "-C", str(checkout), "fetch", "--quiet", "--depth=1", "origin", ref], check=True)
                subprocess.run(["git", "-C", str(checkout), "checkout", "--quiet", "--detach", ref], check=True)
            subprocess.run(
                ["git", "-C", str(checkout), "sparse-checkout", "set", "--no-cone", *("/" + item["path"] for item in items)],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            for item in items:
                source = checkout / item["path"]
                if digest(source) != item["sha256"]:
                    raise ValueError(f"source hash mismatch: {source}")
                dest = ROOT / item["dest"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
                if digest(dest) != item["sha256"]:
                    raise ValueError(f"restored hash mismatch: {dest}")
                print(f"RESTORED/PIN OK {item['id']} {item['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
