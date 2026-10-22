#!/usr/bin/env python3
"""Autonomously restore pinned *owner mirrors*, never claim organizer authentication.

Run: python scripts/restore_inputs.py [--grid-only] [--verify-only].
Uses GitHub sparse/partial checkout and validates every byte against a SHA-256.
No passwords, DriveData cookies, Dropbox downloads, manual data placement, or
new external source are needed. Large files remain ignored under data/.
"""

from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SOURCES = {
    "grid": dict(
        repo="60GEMSDOE",
        ref="02563d07fb85d2f4d35887503d380d34d4017197",
        files={
            "data/official/existing_faults.tif": (
                "bridge/existing_faults.tif",
                "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
            ),
            "data/official/sample_submission.tif": (
                "bridge/sample_submission.tif",
                "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
            ),
        },
    ),
    "features": dict(
        repo="GEMSDOE",
        ref="bb2e070a3659f4f5c16ac927e62606f1f7f495a6",
        files={
            "data/bridge/gems-geodawn-numerical-features.tif.part-000": None,
            "data/bridge/gems-geodawn-numerical-features.tif.part-001": None,
            "data/bridge/gems-geodawn-numerical-features.tif.part-002": None,
            "data/bridge/gems-geodawn-numerical-features.tif.part-003": None,
            "data/bridge/gems-geodawn-numerical-features.tif.part-004": None,
        },
    ),
    "witness": dict(
        repo="17GEMSDOE",
        ref="6fc71d19d49dca4960d5434bd81b6dd06fcc030a",
        files={
            "docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif": (
                "registry/dense_17gemdoe.tif",
                "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
            ),
        },
    ),
    "h33": dict(
        repo="60GEMSDOE",
        ref="02563d07fb85d2f4d35887503d380d34d4017197",
        files={
            "registry/rasters/GEMSDOE32__h33-2-b2-zeros.tif": (
                "registry/h33_education.tif",
                "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9",
            ),
        },
    ),
}
TRAIN_HASH = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"


def digest(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure(repo_key, dests):
    source = SOURCES[repo_key]
    if all(dest.is_file() and digest(dest) == sha for dest, sha in dests):
        print("PIN OK", repo_key, [str(p.relative_to(ROOT)) for p, _ in dests])
        return
    # Do not overwrite an unexpected/corrupted file without explicit diagnosis.
    for dest, sha in dests:
        if dest.exists() and digest(dest) != sha:
            raise ValueError(f"PIN MISMATCH: {dest} (will not silently replace)")
    with tempfile.TemporaryDirectory(prefix="gems88-restore-", dir=DATA) as tmp:
        checkout = Path(tmp) / "mirror"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--depth=1",
                "--filter=blob:none",
                "--sparse",
                f"https://github.com/buffedlizard55-lab/{source['repo']}.git",
                str(checkout),
            ],
            check=True,
        )
        # Fetch the immutable source, not today's mutable main branch.
        if (
            subprocess.check_output(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
            ).strip()
            != source["ref"]
        ):
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(checkout),
                    "fetch",
                    "--quiet",
                    "--depth=1",
                    "origin",
                    source["ref"],
                ],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(checkout),
                    "checkout",
                    "--quiet",
                    "--detach",
                    source["ref"],
                ],
                check=True,
            )
        subprocess.run(
            [
                "git",
                "-C",
                str(checkout),
                "sparse-checkout",
                "set",
                "--no-cone",
                *("/" + p for p in source["files"]),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        if repo_key == "features":
            out = DATA / "training_features.tif"
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("wb") as f:
                for p in source["files"]:
                    with (checkout / p).open("rb") as part:
                        shutil.copyfileobj(part, f)
            if digest(out) != TRAIN_HASH:
                out.unlink()
                raise ValueError("training feature mirror SHA256 did not match pin")
        else:
            for origin, (target, sha) in source["files"].items():
                dst = DATA / target
                if digest(checkout / origin) != sha:
                    raise ValueError(f"source {origin} did not match SHA256 pin")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(checkout / origin, dst)
    if any(digest(p) != sha for p, sha in dests):
        raise ValueError(f"failed to restore {repo_key} against SHA256 pins")
    print("RESTORED/PIN OK", repo_key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--grid-only", action="store_true", help="only owner-mirrored format grid"
    )
    group.add_argument(
        "--validation",
        action="store_true",
        help="grid and two registry witnesses; skip large features",
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    targets = (
        ["grid"]
        if args.grid_only
        else ["grid", "witness", "h33"]
        if args.validation
        else ["grid", "features", "witness", "h33"]
    )
    for key in targets:
        if key == "features":
            expected = [(DATA / "training_features.tif", TRAIN_HASH)]
        else:
            expected = [
                (DATA / target, sha) for target, sha in SOURCES[key]["files"].values()
            ]
        if args.verify_only:
            for path, sha in expected:
                if not path.is_file() or digest(path) != sha:
                    raise ValueError(f"missing or bad input: {path}")
            print("PIN OK", key)
        else:
            ensure(key, expected)


if __name__ == "__main__":
    main()
