#!/usr/bin/env python3
"""Read-only audit of nine named sibling files at the 21:38 UTC GitHub snapshot.

One explicitly identified file is sampled per repository, not an exhaustive
fleet audit or a new model experiment. --check is offline; --regenerate fetches
only immutable GitHub blobs and writes evidence and Pages copies. Neither mode
contacts DrivenData, chooses a weekly slot, or approves a submission.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]
from gems57 import grid  # noqa: E402
from scripts.audit_literal_protocol import pinned  # noqa: E402
from scripts.validate_artifact import validate, validate_artifact  # noqa: E402

SCHEMA = "gems88.focus-sampled-audit-2b5a8383.v1"
EVIDENCE = Path("evidence/focus_sample_2b5a8383.json")
PUBLIC = Path("docs/data/focus_sample_2b5a8383.json")
CACHE = Path(".scratch/focus_sample_2b5a8383")
WITNESS = "data/registry/dense_17gemdoe.tif"
WITNESS_SHA = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
CAPTURED_AT = "2026-10-26T21:38:08Z"
# One file cited near the top of each README at the captured immutable revision.
# GEMSDOE24 describes its cited H24-DPRF1 as a prior reference, not a new file.
# Full SHA claims are omitted where the README supplies only an internal content ID.
SAMPLES = [
    ("GEMSDOE24", "7ab1c8f77f0b4b8644e3929403a0dab65838b008", "H24-DPRF1 reference",
     "docs/downloads/gems24-dprf1-stitched-oof-tworegime-20261026-81849d67c8bf-zeros.tif",
     "c1257c1d4b5ac9cc0a8e29b0120c614fcaa1f38474bc1f6de98c0a1afb0567f1", False),
    ("GEMSDOE25", "af2b6f2543e5422a7e917638b70e038e6fd91cad", "H73-PM",
     "docs/downloads/gems25-h73-pm-deapron-sapd2-8-k3p0-20261026-1b7533ebb62b-zeros.tif", None, False),
    ("GEMSDOE27", "bef7ae8e8f63b69d299c9214c75988c8f5055f9c", "H31-1 DRCG-WL",
     "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
     "2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe", True),
    ("GEMSDOE28", "2c839d10f57ec9b074829e93c84bc39935f52896", "S21-PUHGB",
     "docs/downloads/gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite.tif",
     "2bf4737ae0a3b844a160d4041d435e5a7daf92c6ec92f128a0c2c596ba23787c", False),
    ("GEMSDOE30", "9c0d637c0171407196b61b780444bc772ce75438", "GDX-1",
     "docs/research/2026-10-26-gdx/gems30-GDX1-44090-20261026-2992ee3619f5.tif",
     "3d569d47f5e62e6e62586ddf940140b113d826ab85a5dc4a1642cb8f882c26ac", False),
    ("GEMSDOE31", "2a7cd0c8f1c30341a3a655a01a1ff5bff67b23d2", "H31-X",
     "docs/downloads/gemsdoe31-h31x-piedmont-junction-37654-20261026-5a956da9-zeros.tif",
     "eff2b18e37378d0f0a2f5c8e22fc68e7c359ee161114502a985135e03dd217f9", True),
    ("GEMSDOE32", "07806249f4ed3efe70b4fbf866183c32392b7853", "H47-3",
     "docs/downloads/gemsdoe32-h47-lli-unique-coupling-49231-20261026T230000Z-33464ce2-zeros.tif",
     "d8da7e947db3ed03a3d7064c02b523c254bcb3ae1c5115b7e59b4b436f80fea1", False),
    ("GEMSDOE33", "1d99d73fe14d9a87126ffca2db52c69336d6099b", "A33-R3-LLC",
     "docs/downloads/gemsdoe33-a33-r3-llc-37654-20261026-7f91f9f3ced9-zeros.tif",
     "76f9e157d01bb9bec2d98c3c5941b6114e06e0f439272d5f140af6e3584c8825", False),
    ("GEMSDOE36", "b90418f852615aa0974cf9a53b92fa569ed133fc", "HVG-36",
     "docs/downloads/gemsdoe36-hvg36-vent-dipole-20261026-b3ee97873192-zeros.tif",
     "85d56b03aff18f72d85de9c1e1ca02a2274263fffcd95aa0a6edac7bc9a08596", False),
]


def fetch(site: str, head: str, path: str, root: Path) -> Path:
    route = f"repos/buffedlizard55-lab/{site}/contents/{path}?ref={head}"
    completed = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github.raw+json", route],
                               capture_output=True, check=False, timeout=40)
    if completed.returncode or not completed.stdout or len(completed.stdout) > 30_000_000:
        raise RuntimeError(f"immutable GitHub blob fetch failed or exceeded limit: {site} {path}")
    dest = root / CACHE / f"{site}__{Path(path).name}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(completed.stdout)
    return dest


def sample(root: Path = ROOT) -> dict:
    root = Path(root)
    pinned(root, "data/bridge/sample_submission.tif", grid.SHA256_SAMPLE_SUBMISSION)
    pinned(root, "data/bridge/existing_faults.tif", grid.SHA256_EXISTING_FAULTS)
    pinned(root, WITNESS, WITNESS_SHA)
    g = grid.load_grid(root / "data/bridge")
    with rasterio.open(root / WITNESS) as ds:
        if (ds.shape, ds.crs, ds.transform) != (g.shape, g.crs, g.transform):
            raise ValueError("witness grid mismatch")
        a = ds.read(1)
    witness = np.isfinite(a) & (a > 0)
    yy, xx = np.ogrid[-3:4, -3:4]
    witness_near = binary_dilation(witness, structure=(xx*xx + yy*yy <= 9), border_value=0)
    rows = []
    for site, head, label, path, claimed, sibling_claim in SAMPLES:
        local = fetch(site, head, path, root)
        fmt = validate(local, root / "data/bridge/sample_submission.tif")
        footprint_audit = validate_artifact(local, root / "data/bridge/sample_submission.tif")
        with rasterio.open(local) as src:
            values = src.read(1)
            same_grid = (src.shape, src.crs, src.transform) == (g.shape, g.crs, g.transform)
            metadata = {"dtype": src.dtypes[0], "bands": src.count, "shape": list(src.shape),
                        "crs": str(src.crs), "transform": list(src.transform[:6])}
        finite = np.isfinite(values)
        positive = finite & (values > 0)
        n = int(positive.sum())
        valid_values = values[finite]
        in_fp = bool(same_grid and np.isfinite(values[g.footprint]).all()
                     and ((values[g.footprint] >= 0) & (values[g.footprint] <= 1)).all())
        overlap = float((positive & witness_near).sum() / n) if same_grid and n else None
        direct = float((positive & witness).sum() / n) if same_grid and n else None
        verdict = "DUPLICATE_STOP" if overlap is not None and overlap > 0.70 else "NOT_CLEARED_INCOMPLETE_AUDIT"
        rows.append({
            "site": site, "head": head, "label": label, "path": path,
            "source_url": f"https://github.com/buffedlizard55-lab/{site}/blob/{head}/{path}",
            "readme_url": f"https://github.com/buffedlizard55-lab/{site}/blob/{head}/README.md",
            "sha256": fmt["sha256"], "bytes": local.stat().st_size,
            "sibling_claimed_sha256": claimed,
            "sha_matches_sibling_claim": None if claimed is None else fmt["sha256"] == claimed,
            "sibling_readme_claims_ok_to_submit": sibling_claim,
            "metadata": metadata, "strict_local_format_and_footprint_pass": bool(footprint_audit["ok"]),
            "strict_format_checks": fmt["checks"], "inside_footprint_finite_in_range": in_fp,
            "finite_cells": int(finite.sum()), "total_cells": int(values.size),
            "min_finite": float(valid_values.min()) if valid_values.size else None,
            "max_finite": float(valid_values.max()) if valid_values.size else None,
            "positive_pixels": n,
            "positive_outside_footprint": int((positive & ~g.footprint).sum()) if same_grid else None,
            "positive_on_catalogue": int((positive & g.catalogue).sum()) if same_grid else None,
            "positive_within_3px_witness_fraction": overlap,
            "positive_on_witness_fraction": direct,
            "surface_spearman": None,
            "scientific_holdout_rerun": False,
            "organizer_receipt": None,
            "decision": verdict, "ok_to_submit": False,
        })
    return {
        "schema": SCHEMA, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "github_heads_captured_at_utc": CAPTURED_AT,
        "scope": "One README-cited file per pinned focus repository; not an exhaustive or live audit.",
        "witness_file": WITNESS, "witness_sha256": WITNESS_SHA,
        "literal_dot_overlap_limit": 0.70,
        "surface_correlations": "NOT_RUN; measured duplicate dot overlap alone is sufficient to stop each blocked sample.",
        "score_status": "Sibling holdouts not rerun; no organizer receipt or score inferred.",
        "format_caveat": "Strict full-grid finite checks are local only; official instructions describe null/NaN outside the footprint. Portal acceptance is not established.",
        "rows": rows, "weekly_slots_selected": 0, "new_tiffs_generated": 0,
        "ok_to_submit": False, "approved_for_weekly_slot": False,
    }


def check(report: dict) -> None:
    if (not isinstance(report, dict) or report.get("schema") != SCHEMA
            or report.get("github_heads_captured_at_utc") != CAPTURED_AT
            or report.get("witness_sha256") != WITNESS_SHA
            or report.get("literal_dot_overlap_limit") != 0.70
            or report.get("ok_to_submit") is not False
            or report.get("approved_for_weekly_slot") is not False
            or report.get("new_tiffs_generated") != 0 or report.get("weekly_slots_selected") != 0):
        raise ValueError("invalid or unsafe sample audit")
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != len(SAMPLES):
        raise ValueError("sample audit must contain exactly nine rows")
    for row, (site, head, label, path, claimed, sibling_claim) in zip(rows, SAMPLES):
        if not isinstance(row, dict) or (row.get("site"), row.get("head"), row.get("label"), row.get("path")) != (site, head, label, path):
            raise ValueError("sample identity differs from immutable manifest")
        if (row.get("source_url") != f"https://github.com/buffedlizard55-lab/{site}/blob/{head}/{path}"
                or row.get("readme_url") != f"https://github.com/buffedlizard55-lab/{site}/blob/{head}/README.md"
                or row.get("sibling_claimed_sha256") != claimed
                or row.get("sibling_readme_claims_ok_to_submit") is not sibling_claim
                or re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256", ""))) is None
                or row.get("sha_matches_sibling_claim") is not (None if claimed is None else row["sha256"] == claimed)
                or row.get("scientific_holdout_rerun") is not False or row.get("organizer_receipt") is not None
                or row.get("ok_to_submit") is not False or row.get("surface_spearman") is not None):
            raise ValueError(f"invalid provenance or clearance for {site}")
        overlap = row.get("positive_within_3px_witness_fraction")
        direct = row.get("positive_on_witness_fraction")
        expected = "DUPLICATE_STOP" if isinstance(overlap, (float, int)) and overlap > 0.70 else "NOT_CLEARED_INCOMPLETE_AUDIT"
        if (isinstance(overlap, bool) or (overlap is not None and (not isinstance(overlap, (float, int)) or not 0 <= overlap <= 1))
                or isinstance(direct, bool) or (direct is not None and (not isinstance(direct, (float, int)) or not 0 <= direct <= 1))
                or (direct is not None and overlap is not None and direct > overlap)
                or row.get("decision") != expected):
            raise ValueError(f"invalid witness result for {site}")
        if (not isinstance(row.get("positive_pixels"), int) or isinstance(row["positive_pixels"], bool)
                or row["positive_pixels"] < 0 or not isinstance(row.get("bytes"), int) or row["bytes"] <= 0
                or not isinstance(row.get("strict_local_format_and_footprint_pass"), bool)
                or not isinstance(row.get("inside_footprint_finite_in_range"), bool)
                or not isinstance(row.get("strict_format_checks"), dict)
                or not all(isinstance(v, bool) for v in row["strict_format_checks"].values())):
            raise ValueError(f"invalid local measurement for {site}")
        if row["strict_local_format_and_footprint_pass"] and (
                not row["inside_footprint_finite_in_range"] or not all(row["strict_format_checks"].values())
                or row.get("positive_outside_footprint") != 0):
            raise ValueError(f"local format result contradicts measurements for {site}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--regenerate", action="store_true")
    args = p.parse_args()
    try:
        if args.regenerate:
            report = sample()
            check(report)
            payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
            for rel in (EVIDENCE, PUBLIC):
                (ROOT / rel).write_text(payload)
        else:
            ev, pub = (ROOT / EVIDENCE).read_bytes(), (ROOT / PUBLIC).read_bytes()
            if ev != pub:
                raise ValueError("evidence and Pages sample audit differ")
            report = json.loads(ev)
            check(report)
        print(json.dumps({"sampled": len(report["rows"]),
                          "duplicate_stop": sum(row["decision"] == "DUPLICATE_STOP" for row in report["rows"]),
                          "strict_local_format_pass": sum(row["strict_local_format_and_footprint_pass"] for row in report["rows"]),
                          "ok_to_submit": False}))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, rasterio.errors.RasterioError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
