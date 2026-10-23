#!/usr/bin/env python3
"""Autonomously restore pinned *owner mirrors*, never claim organizer authentication.

Run: python scripts/restore_inputs.py [--grid-only] [--validation] [--verify-only].
Uses GitHub sparse/partial checkout and validates every byte against a SHA-256.
No passwords, DrivenData cookies, Dropbox downloads, manual data placement, or
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
    "external": dict(
        repo="60GEMSDOE",
        ref="02563d07fb85d2f4d35887503d380d34d4017197",
        files={
            "data/external/lidar_scarp_features_u8.tif": (
                "external/lidar_scarp_features_u8.tif",
                "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
            ),
            "data/external/geodawn_rad_u8.tif": (
                "external/geodawn_rad_u8.tif",
                "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
            ),
            "data/external/geodawn_extensions_u8.tif": (
                "external/geodawn_extensions_u8.tif",
                "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
            ),
            "data/external/topo_10m_derived_100m_u8.tif": (
                "external/topo_10m_derived_100m_u8.tif",
                "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
            ),
            "data/external/topo_10m_derived_100m_u8.manifest.json": (
                "external/topo_10m_derived_100m_u8.manifest.json",
                "181d5527ba7ed2990031918a8b6c9d5d94e3998b2daf656de0c33322ca94120a",
            ),
            "data/external/dem10_chi_100m_i16.tif": (
                "external/dem10_chi_100m_i16.tif",
                "8897ba9c30ef1cd7ad5f23c16c6dfd7bb070e7e757f36fd9486eb45edfd973a5",
            ),
            "data/external/dem10_chi_100m_u8.tif": (
                "external/dem10_chi_100m_u8.tif",
                "e8830ba6f0bb99f525266b1b3a483b0722d25cd4758c2bbccc6e7f54eb6b1b6a",
            ),
            "data/external/dem10_chi_100m.manifest.json": (
                "external/dem10_chi_100m.manifest.json",
                "187a961ef5da45278c84b25d16296a5f3458da37abff45046d31ed58b9f5af86",
            ),
            "data/external/2m_temperature_probe_INGENIOUS_regional_data.zip": (
                "external/2m_temperature_probe_INGENIOUS_regional_data.zip",
                "1301f70d230058e616ea5d34d1c7a32fabf7d49198172f376c59c89bd652eca3",
            ),
            "data/external/paleo_geothermal_regional.zip": (
                "external/paleo_geothermal_regional.zip",
                "faffcf697f32dbbf6cbb317cd1effb3e305538ce38eb239d72d0c6fa071e91ca",
            ),
            "data/external/gdr_wellspring_in_footprint.csv": (
                "external/gdr_wellspring_in_footprint.csv",
                "122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea",
            ),
            "data/external/gdr_volcanic_vents_in_footprint.csv": (
                "external/gdr_volcanic_vents_in_footprint.csv",
                "f91bafbaccaaf2754e71d60434fc0f9eb2c7b880c6e714883f4974542ff6a0bf",
            ),
            "data/external/trace_segments_utm11.csv": (
                "external/trace_segments_utm11.csv",
                "c5edf9df3e0e1413c52784884fc38e5b9ca54627b27c6f8baf7713e908f48513",
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
    DATA.mkdir(parents=True, exist_ok=True)
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


def ensure_registry_60():
    target_dir = DATA / "registry/family_60gemsdoe"
    existing = list(target_dir.glob("*.tif")) if target_dir.is_dir() else []
    if len(existing) >= 62:
        print("PIN OK registry_60", f"({len(existing)} rasters)")
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    ref = SOURCES["h33"]["ref"]
    with tempfile.TemporaryDirectory(prefix="gems88-reg60-", dir=DATA) as tmp:
        checkout = Path(tmp) / "mirror"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--depth=1",
                "--filter=blob:none",
                "--sparse",
                "https://github.com/buffedlizard55-lab/60GEMSDOE.git",
                str(checkout),
            ],
            check=True,
        )
        if (
            subprocess.check_output(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
            ).strip()
            != ref
        ):
            subprocess.run(
                ["git", "-C", str(checkout), "fetch", "--quiet", "--depth=1", "origin", ref],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(checkout), "checkout", "--quiet", "--detach", ref],
                check=True,
            )
        subprocess.run(
            ["git", "-C", str(checkout), "sparse-checkout", "set", "registry/rasters"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        copied = 0
        for tif in sorted((checkout / "registry/rasters").glob("*.tif")):
            shutil.copy2(tif, target_dir / tif.name)
            copied += 1
    print("RESTORED/PIN OK registry_60", f"({copied} rasters)")


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
        else ["grid", "features", "witness", "h33", "external"]
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
    if not args.grid_only and not args.validation and not args.verify_only:
        ensure_registry_60()


if __name__ == "__main__":
    main()
