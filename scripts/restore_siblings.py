#!/usr/bin/env python3
"""Restore (and optionally build the inventory of) GeoTIFFs published by the sibling GEMSDOE sites.

Why: the original uniqueness registry (scripts/restore_inputs.py) lacked GEMSDOE86, 87, 89-92
(irregularity IR-88-57).  The prompt requires the candidate to be unlike EVERY listed site, so
those rasters are now part of the registry.

* ``--build``   clone each site at its current default-branch head (shallow, plain git, no REST
                quota), hash every .tif/.zip member, write ``registry/sibling_inventory.json``.
* default       re-fetch each site at the PINNED commit, copy the .tif files into
                ``data/siblings/<site>__<path>.tif`` and verify every SHA-256.
Rasters stay out of Git (``/data/`` is ignored); only the inventory is committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "registry" / "sibling_inventory.json"
OUT = ROOT / "data" / "siblings"
FLEET = ROOT / "data" / "fleet"
OWNER = "buffedlizard55-lab"
SITES = ["GEMSDOE86", "GEMSDOE87", "GEMSDOE89", "GEMSDOE90", "GEMSDOE91", "GEMSDOE92"]


def sha(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sh(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def clone(site, workdir, commit=None):
    dest = Path(workdir) / site
    url = f"https://github.com/{OWNER}/{site}.git"
    if commit is None:
        sh(["git", "clone", "--depth", "1", "-q", url, str(dest)])
    else:
        dest.mkdir(parents=True)
        sh(["git", "init", "-q"], cwd=dest)
        sh(["git", "remote", "add", "origin", url], cwd=dest)
        sh(["git", "fetch", "--depth", "1", "-q", "origin", commit], cwd=dest)
        sh(["git", "checkout", "-q", "FETCH_HEAD"], cwd=dest)
    return dest, sh(["git", "rev-parse", "HEAD"], cwd=dest)


def collect(dest: Path, site: str):
    rows = []
    for p in sorted(dest.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        rel = p.relative_to(dest).as_posix()
        if p.suffix.lower() in (".tif", ".tiff"):
            rows.append(dict(site=site, path=rel, kind="tif", bytes=p.stat().st_size, sha256=sha(p)))
        elif p.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(p) as z:
                    members = [n for n in z.namelist() if n.lower().endswith((".tif", ".tiff"))]
                rows.append(dict(site=site, path=rel, kind="zip", bytes=p.stat().st_size, sha256=sha(p), tif_members=members))
            except zipfile.BadZipFile:
                rows.append(dict(site=site, path=rel, kind="zip", bytes=p.stat().st_size, sha256=sha(p), error="BadZipFile"))
    return rows


def flat(site, rel):
    return f"{site}__{rel.replace('/', '__')}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.build:
        inv = dict(schema="gems88.sibling_inventory.v1", owner=OWNER, sites={}, note="Owner-hosted mirrors; not organizer-authenticated. Rasters are not committed.")
        with tempfile.TemporaryDirectory() as td:
            for site in SITES:
                dest, commit = clone(site, td)
                rows = collect(dest, site)
                inv["sites"][site] = dict(commit=commit, n_tif=sum(r["kind"] == "tif" for r in rows), n_zip=sum(r["kind"] == "zip" for r in rows), files=rows)
                if site == "GEMSDOE86":
                    ps = dest / "registry" / "prior_scores.csv"
                    inv["sites"][site]["extras"] = [dict(path="registry/prior_scores.csv", dest="data/fleet/prior_scores.csv", sha256=sha(ps),
                                                         note="owner-reported public scores (OWNER-REPORTED); used by scripts/calibrate_proxies.py")]
                    inv["fleet_copy_rule"] = "every .tif under GEMSDOE86 data/scored_fleet/ is also copied to data/fleet/<basename> for the calibration scripts"
                for r in rows:
                    if r["kind"] == "tif":
                        shutil.copy2(dest / r["path"], OUT / flat(site, r["path"]))
                print(f"{site}: {commit[:10]} tif={inv['sites'][site]['n_tif']} zip={inv['sites'][site]['n_zip']}")
        INV.write_text(json.dumps(inv, indent=1))
        return 0
    inv = json.loads(INV.read_text())
    bad = 0
    FLEET.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        for site, info in inv["sites"].items():
            tifs = [r for r in info["files"] if r["kind"] == "tif"]
            extras = info.get("extras", [])
            need = [r for r in tifs if not (OUT / flat(site, r["path"])).is_file() or sha(OUT / flat(site, r["path"])) != r["sha256"]]
            need_extra = [e for e in extras if not (ROOT / e["dest"]).is_file() or sha(ROOT / e["dest"]) != e["sha256"]]
            fleet_need = [r for r in tifs if site == "GEMSDOE86" and r["path"].startswith("data/scored_fleet/")
                          and (not (FLEET / Path(r["path"]).name).is_file() or sha(FLEET / Path(r["path"]).name) != r["sha256"])]
            if not (need or need_extra or fleet_need):
                continue
            dest, _ = clone(site, td, info["commit"])
            for r in need:
                shutil.copy2(dest / r["path"], OUT / flat(site, r["path"]))
                if sha(OUT / flat(site, r["path"])) != r["sha256"]:
                    print("SHA MISMATCH", site, r["path"]); bad += 1
            for r in fleet_need:
                shutil.copy2(dest / r["path"], FLEET / Path(r["path"]).name)
                if sha(FLEET / Path(r["path"]).name) != r["sha256"]:
                    print("SHA MISMATCH (fleet)", r["path"]); bad += 1
            for e in need_extra:
                (ROOT / e["dest"]).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest / e["path"], ROOT / e["dest"])
                if sha(ROOT / e["dest"]) != e["sha256"]:
                    print("SHA MISMATCH (extra)", e["path"]); bad += 1
    print("restore OK" if not bad else f"{bad} mismatches")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
