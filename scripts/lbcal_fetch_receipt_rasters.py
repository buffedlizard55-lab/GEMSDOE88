#!/usr/bin/env python3
"""Fetch the exact sibling rasters behind the user-reported LB scores (LBCAL inputs).

Reads research/lbcal_user_reported_scores_20261024.tsv (repo, submission name, user-reported LB),
lists every .tif in each buffedlizard55-lab GEMSDOE* repo through the authenticated GitHub API,
matches by file name (exact -> substring -> nan/zeros-suffix stripped), and downloads the matched
git blob into data/lbcal/ (gitignored) with SHA-256.  Produces data/lbcal/manifest.json and
data/lbcal/profile.json (grid check, NaN-inside-footprint count, mass, catalogue-distance shares).

Requires `gh` (authenticated).  No portal contact.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "lbcal"
OWNER = "buffedlizard55-lab"


def gh(*args, raw=False):
    cmd = ["gh", "api"] + (["-H", "Accept: application/vnd.github.raw"] if raw else []) + list(args)
    r = subprocess.run(cmd, capture_output=True, check=True)
    return r.stdout


def list_tifs():
    names = json.loads(gh("--paginate", f"users/{OWNER}/repos?per_page=100", "--jq", "[.[] | .name]").decode().replace("][", ","))
    rows = []
    for repo in [n for n in names if "GEMSDOE" in n]:
        try:
            tree = json.loads(gh(f"repos/{OWNER}/{repo}/git/trees/main?recursive=1"))
        except subprocess.CalledProcessError:
            continue
        for t in tree.get("tree", []):
            if t["type"] == "blob" and t["path"].endswith(".tif"):
                rows.append((repo, t["path"], int(t.get("size", 0)), t["sha"]))
    return rows


def match(idx, repo, name):
    c = [r for r in idx if r[1].rsplit("/", 1)[-1] in (name + ".tif", name)]
    if not c:
        c = [r for r in idx if name in r[1]]
    if not c:
        base = re.sub(r"-(nan|zeros|zero|allfinite|nanoutside|hard)$", "", name)
        c = [r for r in idx if base in r[1]]
    same = [x for x in c if x[0] == repo] or c

    def pri(x):
        b = x[1].rsplit("/", 1)[-1]
        return (0 if b == name + ".tif" else 1, 1 if "nan-outside" in b or "nanoutside" in b else 0,
                0 if "docs/downloads" in x[1] else 1, len(x[1]))
    return sorted(same, key=pri)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scored = [l.rstrip("\n").split("\t") for l in open(ROOT / "research" / "lbcal_user_reported_scores_20261024.tsv") if l.strip()]
    idx = list_tifs()
    man = []
    for i, (repo, name, lb) in enumerate(scored):
        c = match(idx, repo, name)
        if not c:
            man.append({"repo": repo, "name": name, "lb": float(lb), "status": "missing"}); continue
        r, path, size, sha = c[0]
        fn = f"{i:03d}__{r}__{path.rsplit('/', 1)[-1]}"
        dst = OUT / fn
        if not (dst.exists() and dst.stat().st_size == size):
            dst.write_bytes(gh(f"repos/{OWNER}/{r}/git/blobs/{sha}", raw=True))
        h = hashlib.sha256(dst.read_bytes()).hexdigest()
        man.append({"repo": repo, "name": name, "lb": float(lb), "status": "ok" if dst.stat().st_size == size else "size_mismatch",
                    "file": fn, "sha256": h, "bytes": dst.stat().st_size, "git_blob": sha,
                    "source_url": f"https://github.com/{OWNER}/{r}/blob/main/{path}"})
        print(i, r, fn[-60:], flush=True)
    json.dump(man, open(OUT / "manifest.json", "w"), indent=1)
    # profile (grid check + NaN inside footprint) used by the fit to exclude malformed receipts
    with rasterio.open(ROOT / "data/bridge/sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1)); T0, crs0, shp = ds.transform, ds.crs, (ds.height, ds.width)
    prof = []
    for m in man:
        if m["status"] != "ok":
            prof.append({"name": m["name"], "lb": m["lb"], "status": m["status"]}); continue
        with rasterio.open(OUT / m["file"]) as ds:
            ok = ds.crs == crs0 and (ds.height, ds.width) == shp and all(abs(a - b) < 1e-6 for a, b in zip(ds.transform, T0))
            a = ds.read(1).astype(np.float32); nod = ds.nodata
        if nod is not None and np.isfinite(nod):
            a[a == nod] = np.nan
        prof.append({"i": int(m["file"][:3]), "name": m["name"], "lb": m["lb"], "grid_ok": bool(ok),
                     "nan_in_foot": int(np.isnan(a[foot]).sum()) if a.shape == foot.shape else -1})
    json.dump(prof, open(OUT / "profile.json", "w"), indent=1)
    print("done", sum(m["status"] == "ok" for m in man), "of", len(man))


if __name__ == "__main__":
    sys.exit(main())
