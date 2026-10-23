#!/usr/bin/env python3
"""Gate 0 of the GEMS brief: verify pinned inputs and re-derive parent R0.

Checks performed (all must pass before any variant is built):

1. sha256 of ``sample_submission.tif`` and ``existing_faults.tif`` against the
   pins recorded in ``scripts/restore_inputs.py`` (the repo's data manifest).
2. sha256 of the parent raster ``data/registry/h33_education.tif`` against the
   ledger pin ``c55bafc4...``.
3. Parent geometry: 37,654 positive cells, every cell inside the scored
   footprint, zero positive cells on the catalogue, minimum Euclidean distance
   to the nearest catalogue pixel > 2 px.
4. Re-emission: write the parent's boolean mask back out on the pinned grid and
   compare (a) the array read from disk and (b) the sha256 of the byte stream.
   Byte identity is reported, never forced: GDAL/zlib builds may differ, so the
   *array* is the reproducible object and the byte hash is a receipt only.

Writes ``registry/r0_verification.json``. Exit code 1 if any hard check fails.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "data" / "bridge"
P = ROOT / "data" / "registry" / "h33_education.tif"
OUT = ROOT / "registry" / "r0_verification.json"

PIN_SAMPLE = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
PIN_EXISTING = "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"
PIN_PARENT = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
N_PARENT = 37_654


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    report: dict = {"checks": {}, "ok": True}

    def check(name: str, ok: bool, detail) -> None:
        report["checks"][name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            report["ok"] = False

    s_sample, s_exist, s_parent = sha256(B / "sample_submission.tif"), sha256(
        B / "existing_faults.tif"
    ), sha256(P)
    check("pin_sample_submission", s_sample == PIN_SAMPLE, s_sample)
    check("pin_existing_faults", s_exist == PIN_EXISTING, s_exist)
    check("pin_parent_R0", s_parent == PIN_PARENT, s_parent)

    with rasterio.open(B / "existing_faults.tif") as src:
        ef = src.read(1)
    with rasterio.open(B / "sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
        sample_profile = src.profile.copy()
    catalogue = (ef == 1) & footprint
    dist = distance_transform_edt(~catalogue).astype(np.float32)

    with rasterio.open(P) as src:
        parent = src.read(1)
        parent_profile = src.profile.copy()
    dots = parent > 0.5
    dvals = dist[dots]
    n_dots = int(dots.sum())
    check("n_dots_37654", n_dots == N_PARENT, n_dots)
    check("all_dots_in_footprint", bool(dots[~footprint].sum() == 0), int(dots[~footprint].sum()))
    check("zero_on_catalogue", bool((dots & catalogue).sum() == 0), int((dots & catalogue).sum()))
    check("none_within_2px", bool((dvals <= 2.0).sum() == 0), int((dvals <= 2.0).sum()))
    report["parent_geometry"] = {
        "min_dist_px": float(dvals.min()),
        "n_within_3px": int((dvals <= 3.0).sum()),
        "frac_within_3px": float((dvals <= 3.0).mean()),
        "footprint_px": int(footprint.sum()),
        "catalogue_px": int(catalogue.sum()),
        "dot_density_frac_of_footprint": float(n_dots / footprint.sum()),
    }

    # (4) Re-emit the parent's own array.  Two writers are tried: an exact copy
    # of the parent's profile and the LZW single-strip profile the releases use.
    with rasterio.open(B / "sample_submission.tif") as src:
        lzw_profile = src.profile.copy()
    lzw_profile.update(dtype="float32", count=1, compress="lzw", tiled=False, nodata=None)

    tmp = ROOT / "data" / "work"
    tmp.mkdir(parents=True, exist_ok=True)
    reemit = {}
    for name, profile in (("parent_profile", parent_profile), ("lzw_profile", lzw_profile)):
        out = tmp / f"r0_reemit_{name}.tif"
        prof = profile.copy()
        prof.update(dtype="float32", count=1)
        with rasterio.open(out, "w", **prof) as dst:
            dst.write(parent.astype(np.float32), 1)
        with rasterio.open(out) as src:
            back = src.read(1)
        reemit[name] = {
            "sha256": sha256(out),
            "sha256_matches_parent": sha256(out) == PIN_PARENT,
            "array_identical": bool(np.array_equal(back, parent)),
            "n_differing_px": int((back != parent).sum()),
            "profile": {k: str(v) for k, v in prof.items()},
        }
    check("reemit_array_identical", any(v["array_identical"] for v in reemit.values()), reemit)
    report["reemit"] = reemit
    report["byte_sha_reproduced"] = any(v["sha256_matches_parent"] for v in reemit.values())
    report["note"] = (
        "The reproducible object is the 37,654-pixel dot mask (array identity). "
        "Byte-level sha256 equality additionally requires the same GDAL/zlib build; "
        "it is reported, not enforced, and every variant is named by the sha256 of "
        "the bytes we actually write."
    )
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
