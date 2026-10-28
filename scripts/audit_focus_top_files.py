#!/usr/bin/env python3
"""Read-only, GitHub-API-only audit of each focus site's top user-reported TIFF.

For each focus owner repository this script:
  1. lists ``docs/downloads`` through api.github.com (no other host);
  2. finds the TIFF whose name contains the submission's hash fragment;
  3. downloads its bytes via the contents API (base64) and reopens them;
  4. records SHA-256, grid/CRS/transform, value range, positive count and the
     3-px overlap of its dots against the pinned H19-5 registry raster.

It does not query DrivenData, train, score, select a slot or write a TIFF.
User-reported scores are copied from the prompt and labelled as such.
Usage:  .venv/bin/python scripts/audit_focus_top_files.py [--output PATH]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "evidence" / "focus_top_files_20261028.json"
H19_5 = ROOT / "data" / "registry" / "gems19_h19_5.tif"
SAMPLE = ROOT / "data" / "bridge" / "sample_submission.tif"
OWNER = "buffedlizard55-lab"

# Site -> (user-reported top submission name as it appears in the prompt,
#          hash fragment used to locate the file in docs/downloads).
FOCUS = {
    "GEMSDOE24": ("h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", "989f59505db1", "0.2477"),
    "GEMSDOE25": ("dotted-h19-5-d2-8-20261002-e56ea318af89-nan", "e56ea318af89", "0.2600"),
    "GEMSDOE27": ("topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", "5512495c6bd1", "0.2449"),
    "GEMSDOE28": ("h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", "b531dae0a36f", "0.2710"),
    "GEMSDOE30": ("d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", "91eae1ca", "0.2600"),
    "GEMSDOE31": ("h27-4-solo-d28-20261004-8acb75e1-nan", "8acb75e1", "0.2708"),
    "GEMSDOE32": ("h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", "e5eb6e7e", "0.2778"),
    "GEMSDOE33": ("h33d-analog-tip-stepover-r30-20261004-cb490425926e", "cb490425926e", "0.2632"),
    "GEMSDOE36": ("anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", "9b9ea4e6", "0.2750"),
}


def gh_json(endpoint: str):
    out = subprocess.run(["gh", "api", endpoint], capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"gh api {endpoint} failed: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout)


def dots_within_3px(a: np.ndarray, b: np.ndarray) -> float:
    if a.sum() == 0:
        return float("nan")
    dt = ndi.distance_transform_edt(~b)
    return float((dt[a] <= 3.0).mean())


def describe(raw: bytes, h19: np.ndarray) -> dict:
    with MemoryFile(raw) as mem, mem.open() as ds:
        a = ds.read(1)
        meta = {
            "crs": ds.crs.to_string() if ds.crs else None,
            "shape": list(a.shape),
            "dtype": str(a.dtype),
            "count": ds.count,
            "nodata": ds.nodata,
            "transform": list(ds.transform)[:6],
        }
    finite = np.isfinite(a)
    vals = a[finite]
    dots = (a == 1) & finite
    sample = rasterio.open(SAMPLE).read(1)
    foot = np.isfinite(sample)
    meta.update({
        "grid_matches_sample": bool(a.shape == sample.shape and meta["crs"] == "EPSG:32611"
                                    and meta["transform"] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]),
        "finite_pixels": int(finite.sum()),
        "nan_pixels": int((~finite).sum()),
        "nan_inside_footprint": int((~finite & foot).sum()),
        "finite_outside_footprint": int((finite & ~foot).sum()),
        "min": float(vals.min()) if vals.size else None,
        "max": float(vals.max()) if vals.size else None,
        "all_in_0_1": bool(vals.size and vals.min() >= 0.0 and vals.max() <= 1.0),
        "is_binary_0_1": bool(np.isin(vals, [0.0, 1.0]).all()),
        "positive_pixels": int(dots.sum()),
        "positive_pixels_outside_footprint": int((dots & ~foot).sum()),
        "overlap_3px_vs_H19_5": dots_within_3px(dots, h19 == 1),
    })
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()
    h19 = rasterio.open(H19_5).read(1)
    rows = []
    for site, (name, frag, reported) in FOCUS.items():
        row = {"site": site, "user_reported_name": name, "user_reported_value": reported,
               "evidence_class": "USER-REPORTED CLAIM - NOT HOLDOUT-DTI OR ORGANIZER-CONFIRMED",
               "repo_url": f"https://github.com/{OWNER}/{site}",
               "pages_url": f"https://{OWNER}.github.io/{site}/"}
        try:
            listing = gh_json(f"repos/{OWNER}/{site}/contents/docs/downloads")
            hits = [e for e in listing if frag in e["name"] and e["name"].endswith(".tif")]
            row["tif_matches_in_docs_downloads"] = [e["name"] for e in hits]
            if not hits:
                row["status"] = "NOT_FOUND_IN_DOCS_DOWNLOADS"
            else:
                # Every matching TIFF is reported (the owner may publish nan and zeros variants).
                variants = []
                for e in hits[:4]:
                    # git blob API: the contents API omits bodies above 1 MB.
                    blob = gh_json(f"repos/{OWNER}/{site}/git/blobs/{e['sha']}")
                    raw = base64.b64decode(blob["content"])
                    if len(raw) != e["size"]:
                        raise RuntimeError(f"size mismatch for {e['name']}: {len(raw)} != {e['size']}")
                    item = {
                        "status": "DOWNLOADED_AND_REOPENED",
                        "file": e["name"],
                        "download_path": f"docs/downloads/{e['name']}",
                        "github_blob_sha": e["sha"],
                        "size_bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "file_url": f"https://github.com/{OWNER}/{site}/blob/main/docs/downloads/{e['name']}",
                    }
                    item.update(describe(raw, h19))
                    variants.append(item)
                row["variants"] = variants
                row["status"] = "DOWNLOADED_AND_REOPENED"
                row["file"] = variants[0]["file"]
                row["sha256"] = variants[0]["sha256"]
                row["positive_pixels"] = variants[0]["positive_pixels"]
        except Exception as exc:  # record, never silently drop a site
            row["status"] = "ERROR"
            row["error"] = str(exc)[:400]
        rows.append(row)
        for v in row.get("variants", []):
            print(site, v["file"], v["sha256"][:16], "dots", v["positive_pixels"], "nan_in_fp", v["nan_inside_footprint"])
        if row.get("status") != "DOWNLOADED_AND_REOPENED":
            print(site, row.get("status"), row.get("error", ""))
    out = {
        "schema": "gems88.focus-top-files.v1",
        "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": ["api.github.com contents API (docs/downloads of each owner repo)"],
        "not_used": ["DrivenData (no login)", "GitHub Pages hosts (not on the sandbox allowlist)"],
        "h19_5_reference": {"path": "data/registry/gems19_h19_5.tif",
                             "sha256": hashlib.sha256(H19_5.read_bytes()).hexdigest()},
        "rows": rows,
        "organizer_confirmed_scores": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("wrote", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
