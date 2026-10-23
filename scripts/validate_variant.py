#!/usr/bin/env python3
"""Independent gate check for a released variant raster (brief v2, section 6).

MUST-pass gates, re-derived from the bytes on disk (never from the builder's
in-memory array):

1. GeoTIFF, one band, float32, CRS/shape/transform identical to
   ``sample_submission.tif``.
2. Values inside the scored footprint are finite and in [0, 1].
3. Outside the footprint: NaN for the primary file, exact 0 for the ``-zeros``
   fallback; the two files must agree inside the footprint.
4. Zero positive cells on the mapped catalogue and zero cells within 2 px of it
   (the parent's collar; the 2-3 px ring is reported, not gated).
5. sha256 is not already in ``ledger/submissions.csv`` (exact-hash dedupe only).
6. Parent-diff statistics are recorded: common / added / removed dots and the
   percentage of R0's dots that changed.
7. The single-TIFF ``.zip`` beside the raster unpacks to one file whose sha256
   equals the raster's.
8. The file is re-read from disk after all of the above (the checks below run on
   a second, independent read).

``--report ONLY`` gates (catalogue hide-and-recover PROXY, leakage canary, SGMC
control) are intentionally absent: they can never fail a release.

Usage::

    python scripts/validate_variant.py releases/<id>.tif [more.tif ...] \
        --out registry/variant_validation.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "data" / "bridge"
PARENT = ROOT / "data" / "registry" / "h33_education.tif"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def twin_of(path: Path) -> Path:
    return (path.with_name(path.name.replace("-zeros.tif", ".tif"))
            if path.name.endswith("-zeros.tif") else
            path.with_name(path.stem + "-zeros.tif"))


def ledger_hashes() -> dict[str, str]:
    """sha256 -> row id, from every hash column of the ledger."""
    out: dict[str, str] = {}
    p = ROOT / "ledger" / "submissions.csv"
    if not p.is_file():
        return out
    with p.open(newline="") as f:
        for row in csv.DictReader(f):
            for col in ("sha256", "sha256_zeros"):
                h = (row.get(col) or "").strip()
                if h:
                    out.setdefault(h, []).append(row["id"])  # type: ignore[arg-type]
    return out


def validate(path: Path, footprint, catalogue, dist, parent, sample_meta, hashes) -> dict:
    checks: dict[str, dict] = {}

    def check(name, ok, detail=None):
        checks[name] = {"ok": bool(ok), "detail": detail}

    with rasterio.open(path) as src:
        arr = src.read(1)
        meta = {"driver": src.driver, "count": src.count, "dtype": src.dtypes[0],
                "crs": str(src.crs), "shape": [src.height, src.width],
                "transform": [round(float(x), 6) for x in tuple(src.transform)[:6]],
                "nodata": src.nodata}
    check("geotiff", meta["driver"] == "GTiff", meta["driver"])
    check("single_band", meta["count"] == 1, meta["count"])
    check("float32", meta["dtype"] == "float32", meta["dtype"])
    check("crs", meta["crs"] == sample_meta["crs"], meta["crs"])
    check("shape", meta["shape"] == sample_meta["shape"], meta["shape"])
    check("transform", meta["transform"] == sample_meta["transform"], meta["transform"])

    inside = arr[footprint]
    outside = arr[~footprint]
    is_zeros = path.name.endswith("-zeros.tif")
    finite_inside = bool(np.isfinite(inside).all())
    check("finite_inside_footprint", finite_inside, int((~np.isfinite(inside)).sum()))
    check("values_in_0_1_inside", finite_inside and bool(((inside >= 0) & (inside <= 1)).all()),
          [float(np.nanmin(inside)), float(np.nanmax(inside))] if finite_inside else None)
    if is_zeros:
        check("zeros_outside_footprint", bool((outside == 0).all()), int((outside != 0).sum()))
    else:
        check("nan_outside_footprint", bool(np.isnan(outside).all()), int((~np.isnan(outside)).sum()))

    dots = np.where(np.isfinite(arr), arr, 0.0) > 0.5
    check("zero_mass_on_catalogue", int((dots & catalogue).sum()) == 0, int((dots & catalogue).sum()))
    dvals = dist[dots]
    check("none_within_2px_catalogue", int((dvals <= 2.0).sum()) == 0, int((dvals <= 2.0).sum()))
    check("dot_values_are_binary", bool(np.isin(np.unique(arr[footprint][np.isfinite(arr[footprint])]),
                                                [0.0, 1.0]).all()), len(np.unique(inside)))

    h = sha256(path)
    owners = hashes.get(h, [])
    own_id = path.name.replace("-zeros.tif", ".tif").rsplit(".tif", 1)[0]
    duplicate = [o for o in owners if not o.startswith(own_id)]
    check("sha256_not_previously_submitted", len(duplicate) == 0, {"sha256": h, "owners": owners})

    n_common = int((dots & parent).sum())
    n_added = int((dots & ~parent).sum())
    n_removed = int((~dots & parent).sum())
    check("parent_diff_recorded", {"common": n_common, "added": n_added, "removed": n_removed} is not None,
          {"common": n_common, "added": n_added, "removed": n_removed,
           "pct_of_parent_changed": round(100.0 * (n_added + n_removed) / 2 / int(parent.sum()), 2)})

    twin = twin_of(path)
    check("twin_present", twin.is_file(), str(twin.name))
    if twin.is_file():
        with rasterio.open(twin) as t:
            tarr = t.read(1)
        check("twin_agrees_inside_footprint",
              np.array_equal(np.nan_to_num(arr, nan=0.0), np.nan_to_num(tarr, nan=0.0)), None)

    zp = path.with_suffix(".zip")
    check("zip_present", zp.is_file(), zp.name)
    if zp.is_file():
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
            payload = z.read(names[0]) if names else b""
        check("zip_single_tiff", len(names) == 1 and names[0].endswith(".tif"), names)
        check("zip_sha_matches_raster",
              hashlib.sha256(payload).hexdigest() == h, None)

    # second independent read: the object that will actually be uploaded
    with rasterio.open(path) as src:
        again = src.read(1)
    check("reread_identical", np.array_equal(np.nan_to_num(again, nan=0.0),
                                             np.nan_to_num(arr, nan=0.0)), None)

    return {
        "artifact": str(path.relative_to(ROOT)),
        "sha256": h,
        "n_dots": int(dots.sum()),
        "colour": "zeros" if is_zeros else "nan",
        "meta": meta,
        "parent_diff": {"common": n_common, "added": n_added, "removed": n_removed},
        "checks": checks,
        "gates_pass": all(c["ok"] for c in checks.values()),
        "report_only_not_gated": ["catalogue hide-and-recover PROXY", "leakage canary", "SGMC control"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    with rasterio.open(BRIDGE / "sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
        sample_meta = {"crs": str(src.crs), "shape": [src.height, src.width],
                       "transform": [round(float(x), 6) for x in tuple(src.transform)[:6]]}
    with rasterio.open(BRIDGE / "existing_faults.tif") as src:
        catalogue = (src.read(1) == 1) & footprint
    dist = distance_transform_edt(~catalogue).astype(np.float32)
    with rasterio.open(PARENT) as src:
        parent = src.read(1) > 0.5
    hashes = ledger_hashes()

    results = []
    ok = True
    for p in args.paths:
        p = (ROOT / p) if not p.is_absolute() else p
        r = validate(p, footprint, catalogue, dist, parent, sample_meta, hashes)
        ok &= r["gates_pass"]
        results.append(r)
        failed = [k for k, v in r["checks"].items() if not v["ok"]]
        print(f"{'PASS' if r['gates_pass'] else 'FAIL'}  {r['artifact']}  n={r['n_dots']}  "
              f"sha={r['sha256'][:12]}  {'' if not failed else 'failed: ' + ', '.join(failed)}")

    payload = {"validator": "validate_variant.py", "gates_all_pass": bool(ok),
               "results": results}
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"wrote {args.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
