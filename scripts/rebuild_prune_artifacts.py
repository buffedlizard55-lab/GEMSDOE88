#!/usr/bin/env python3
"""Recreate already-ledgered PRUNE rasters without creating new experiments.

This is artifact recovery for the existing (R0, PRUNE, p1px/p3px/p4px) rows.
It verifies every pinned input and the byte-exact R0 lineage first, reconstructs
masks with the recorded label-free physical-prior / exact-marginal-DTI recipe,
then requires the emitted SHA-256 values to match the existing ledger and
receipts. It never appends, replaces, or edits a ledger row and never contacts
DrivenData or Dropbox.

Competition rasters are written only under the gitignored ``releases/`` path.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_variants as bpv  # noqa: E402

PARENT = "h33-h33-2-b2"
AXIS = "PRUNE"
VALUES = ("p1px", "p3px", "p4px")
LEDGER_PATH = ROOT / "ledger" / "submissions.csv"
RELEASES = ROOT / "releases"
REPORT_PATH = ROOT / "evidence" / "prune_artifact_rebuild.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def git_tree_clean() -> bool | None:
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True
        )
        return not status.strip()
    except Exception:
        return None


def load_ledger_rows() -> dict[str, dict[str, str]]:
    if not LEDGER_PATH.is_file():
        raise FileNotFoundError(f"missing candidate ledger: {LEDGER_PATH}")
    with LEDGER_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    selected: dict[str, dict[str, str]] = {}
    for value in VALUES:
        matches = [
            row for row in rows
            if row.get("parent") == PARENT
            and row.get("axis") == AXIS
            and row.get("value") == value
        ]
        if len(matches) != 1:
            raise ValueError(
                f"expected exactly one existing ledger row for ({PARENT}, {AXIS}, {value}); "
                f"found {len(matches)}"
            )
        row = matches[0]
        if row.get("status") != "BUILT":
            raise ValueError(f"existing variant is not BUILT: {row.get('id')} / {row.get('status')}")
        if not row.get("sha256") or not row.get("sha256_zeros"):
            raise ValueError(f"ledger lacks primary/fallback hashes for {row.get('id')}")
        selected[value] = row

    # Exact-hash dedupe against every *other* ledger row. The existing row for
    # a candidate is its receipt of record, not a duplicate of itself.
    for value, row in selected.items():
        own_hashes = {row["sha256"], row["sha256_zeros"]}
        if len(own_hashes) != 2:
            raise ValueError(f"primary/fallback hashes collide for {row['id']}")
        for other in rows:
            if other.get("id") == row.get("id"):
                continue
            if own_hashes & {other.get("sha256"), other.get("sha256_zeros")}:
                raise ValueError(f"candidate hash is already assigned to another ledger row: {row['id']}")
    return selected


def reconstruct_masks(verified: dict[str, Path], lineage: dict) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    foot = lineage["foot"]
    catalogue = lineage["catalogue"]
    d_cat = lineage["d_cat"]
    h19_5 = lineage["h19_5"]
    r0 = lineage["r0"]
    solo = lineage["solo"]

    # This is the recorded report-only leakage audit plus label-free ranking
    # field. The canary diagnoses the feature construction; it does not tune
    # against public-test or organizer truth.
    w_field, canaries = bpv.build_physical_field_and_canaries(
        verified, foot, catalogue, h19_5
    )
    if max(canaries.values()) > 0.90:
        raise RuntimeError(
            f"single-feature leakage canary exceeded 0.90: {max(canaries.values()):.5f}"
        )

    # R0 -> p1px: restore SOLO flank pixels in (1, 2] px, then drop the same
    # number of lowest exact-marginal-gain off-collar R0 dots.
    flank_1_to_2 = solo & ~r0
    n_restore = int(flank_1_to_2.sum())
    p1 = bpv.select_exact_marginal_dti_drop(
        base_mask=r0 | flank_1_to_2,
        drop_pool_mask=r0 & (d_cat > 2.0),
        w=w_field,
        n_drop=n_restore,
    )

    # R0 -> p3px/p4px: remove the indicated catalogue collar and refill to the
    # same count from original H19-5 support by exact marginal DTI gain.
    r0_gt3 = r0 & (d_cat > 3.0)
    n_remove3 = int(r0.sum() - r0_gt3.sum())
    p3 = bpv.select_exact_marginal_dti_add(
        base_mask=r0_gt3,
        cand_mask=h19_5 & ~r0_gt3 & (d_cat > 3.0),
        w=w_field,
        n_add=n_remove3,
    )

    r0_gt4 = r0 & (d_cat > 4.0)
    n_remove4 = int(r0.sum() - r0_gt4.sum())
    p4 = bpv.select_exact_marginal_dti_add(
        base_mask=r0_gt4,
        cand_mask=h19_5 & ~r0_gt4 & (d_cat > 4.0),
        w=w_field,
        n_add=n_remove4,
    )

    masks = {"p1px": p1, "p3px": p3, "p4px": p4}
    for value, mask in masks.items():
        if int(mask.sum()) != int(r0.sum()) or int(mask.sum()) != 37_654:
            raise RuntimeError(f"fixed-count invariant failed for {value}")
    return masks, canaries


def output_paths(candidate_id: str) -> tuple[Path, Path, Path, Path]:
    primary = RELEASES / f"{candidate_id}.tif"
    fallback = RELEASES / f"{candidate_id}-zeros.tif"
    zip_primary = RELEASES / f"{candidate_id}.zip"
    zip_fallback = RELEASES / f"{candidate_id}-zeros.zip"
    return primary, fallback, zip_primary, zip_fallback


def write_one_raster(
    path: Path,
    mask: np.ndarray,
    footprint: np.ndarray,
    template: Path,
    *,
    outside_nan: bool,
    expected_sha256: str,
) -> dict:
    if path.exists():
        got = sha256(path)
        if got != expected_sha256:
            raise ValueError(
                f"refusing to overwrite existing artifact with a different hash: {path} "
                f"({got} != {expected_sha256})"
            )
    else:
        outside_value = np.nan if outside_nan else 0.0
        arr = np.where(footprint, mask.astype(np.float32), outside_value).astype(np.float32)
        with rasterio.open(template) as ref:
            profile = ref.profile.copy()
        profile.update(
            driver="GTiff",
            dtype="float32",
            count=1,
            compress="deflate",
            predictor=3,
            zlevel=9,
            tiled=True,
            blockxsize=256,
            blockysize=256,
            nodata=np.nan if outside_nan else None,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp")
        if tmp.exists():
            tmp.unlink()
        try:
            with rasterio.open(tmp, "w", **profile) as dst:
                dst.write(arr, 1)
            got = sha256(tmp)
            if got != expected_sha256:
                raise ValueError(
                    f"reconstruction SHA mismatch for {path.name}: {got} != {expected_sha256}; "
                    "do not approximate or substitute the parent/variant"
                )
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)

    # Independent on-disk re-read and format/exclusion gate.
    with rasterio.open(template) as ref, rasterio.open(path) as src:
        back = src.read(1)
        expected_meta = (ref.shape, ref.crs, ref.transform)
        actual_meta = (src.shape, src.crs, src.transform)
        checks = {
            "geotiff": src.driver == "GTiff",
            "one_band": src.count == 1,
            "float32": src.dtypes == ("float32",),
            "crs_shape_transform_match": actual_meta == expected_meta,
            "no_nan_inside": bool(np.isfinite(back[footprint]).all()),
            "values_0_1_inside": bool(((back[footprint] >= 0) & (back[footprint] <= 1)).all()),
            "outside_encoding": bool(np.isnan(back[~footprint]).all()) if outside_nan else bool((back[~footprint] == 0).all()),
            "nodata_encoding": bool(src.nodata is not None and np.isnan(src.nodata)) if outside_nan else src.nodata is None,
            "scored_mask_exact": bool(np.array_equal(back[footprint] > 0.5, mask[footprint])),
            "reread_from_disk": True,
        }
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "checks": checks,
        "ok": all(checks.values()),
    }


def write_zip(path: Path, tif_path: Path, expected_tif_sha: str) -> dict:
    if path.exists():
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            if names != [tif_path.name] or hashlib.sha256(zf.read(tif_path.name)).hexdigest() != expected_tif_sha:
                raise ValueError(f"existing ZIP is not a one-file copy of {tif_path.name}: {path}")
    else:
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.unlink(missing_ok=True)
        try:
            with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(tif_path, arcname=tif_path.name)
            with zipfile.ZipFile(tmp) as zf:
                names = zf.namelist()
                if names != [tif_path.name] or hashlib.sha256(zf.read(tif_path.name)).hexdigest() != expected_tif_sha:
                    raise ValueError(f"ZIP verification failed: {tmp}")
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    rebuild_git_sha = git_sha()
    source_tree_clean = git_tree_clean()
    print("[1/5] Verify all 15 manifest pins...")
    verified = bpv.verify_manifest()
    print(f"      PASS: {len(verified)} pinned inputs (SHA-256 and byte length)")

    print("[2/5] Rebuild R0 from its full recorded lineage...")
    lineage = bpv.rebuild_r0_from_lineage(verified)
    print(
        f"      PASS: {int(lineage['r0'].sum()):,} dots; "
        f"zeros SHA-256 {lineage['rebuilt_zeros_sha256']}; "
        f"NaN SHA-256 {lineage['rebuilt_nan_sha256']}"
    )

    print("[3/5] Check the existing PRUNE ledger pairs and reconstruct their recorded masks...")
    rows = load_ledger_rows()
    masks, canaries = reconstruct_masks(verified, lineage)

    print("[4/5] Recreate only missing local artifacts; exact ledger hashes are mandatory...")
    template = verified["sample_submission"]
    foot = lineage["foot"]
    catalogue = lineage["catalogue"]
    d_cat = lineage["d_cat"]
    report_variants: list[dict] = []
    receipt_updates: list[tuple[Path, dict]] = []

    for value in VALUES:
        row = rows[value]
        candidate_id = row["id"]
        if not candidate_id.endswith(row["sha256"][:8]):
            raise ValueError(f"candidate ID is not content-addressed: {candidate_id}")
        receipt_path = RELEASES / f"{candidate_id}.json"
        if not receipt_path.is_file():
            raise FileNotFoundError(f"missing existing tracked receipt: {receipt_path}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("sha256") != row["sha256"] or receipt.get("sha256_zeros") != row["sha256_zeros"]:
            raise ValueError(f"ledger/receipt hash disagreement for {candidate_id}")

        mask = masks[value]
        if np.any(mask & catalogue):
            raise ValueError(f"non-zero catalogue mass in {candidate_id}")
        if np.any(d_cat[mask] <= 0.0):
            raise ValueError(f"catalogue-pixel overlap in {candidate_id}")
        n_parent = int(lineage["r0"].sum())
        n_common = int((mask & lineage["r0"]).sum())
        n_added = int((mask & ~lineage["r0"]).sum())
        n_removed = int((lineage["r0"] & ~mask).sum())
        moved_pct = 100.0 * n_removed / n_parent
        diff = {
            "n_parent": n_parent,
            "n_candidate": int(mask.sum()),
            "n_common": n_common,
            "n_added": n_added,
            "n_removed": n_removed,
            "pct_changed": moved_pct,
            "symmetric_difference_pct": 100.0 * (n_added + n_removed) / n_parent,
            "min_d_catalogue_px": float(d_cat[mask].min()),
        }
        if n_added != n_removed or not 1.0 <= moved_pct <= 50.0:
            raise ValueError(f"parent-diff constraint failed for {candidate_id}: {diff}")
        recorded_pct = float(row.get("pct_changed") or row.get("%_changed") or "nan")
        matches_exact = np.isclose(recorded_pct, moved_pct, rtol=0.0, atol=5e-7)
        matches_legacy_rounding = np.isclose(recorded_pct, round(moved_pct, 2), rtol=0.0, atol=1e-12)
        if not (matches_exact or matches_legacy_rounding):
            raise ValueError(f"ledger parent-diff mismatch for {candidate_id}: {moved_pct} != {recorded_pct}")

        primary_path, zeros_path, zip_primary_path, zip_zeros_path = output_paths(candidate_id)
        primary = write_one_raster(
            primary_path, mask, foot, template, outside_nan=True, expected_sha256=row["sha256"]
        )
        zeros = write_one_raster(
            zeros_path, mask, foot, template, outside_nan=False, expected_sha256=row["sha256_zeros"]
        )
        if not primary["ok"] or not zeros["ok"]:
            raise ValueError(f"format/re-read gate failed for {candidate_id}")

        # The brief only requires the TIFF twins; restore the single-file ZIPs
        # too because the repository's existing submission checklist and tests
        # consume them. ZIP timestamps may differ from the original run, so the
        # regenerated SHA is recorded below rather than assumed.
        zip_primary = write_zip(zip_primary_path, primary_path, row["sha256"])
        zip_zeros = write_zip(zip_zeros_path, zeros_path, row["sha256_zeros"])

        # Check only exact hashes against other rows; no overlap/correlation gate.
        for other in rows.values():
            if other["id"] == candidate_id:
                continue
            if {row["sha256"], row["sha256_zeros"]} & {other["sha256"], other["sha256_zeros"]}:
                raise ValueError(f"exact candidate hash collision with {other['id']}")

        receipt["zip_nan_sha256"] = zip_primary["sha256"]
        receipt["zip_zeros_sha256"] = zip_zeros["sha256"]
        receipt["artifact_reconstruction"] = {
            "evidence_class": "REPRODUCTION",
            "existing_experiment": True,
            "new_ledger_row": False,
            "git_sha_at_rebuild": rebuild_git_sha,
            "working_tree_clean_at_rebuild_start": source_tree_clean,
            "rebuild_script_sha256": sha256(Path(__file__)),
            "inputs_verified": len(verified),
            "manifest_pins_verified": True,
            "r0_zeros_sha256": lineage["rebuilt_zeros_sha256"],
            "r0_nan_sha256": lineage["rebuilt_nan_sha256"],
        }
        receipt_updates.append((receipt_path, receipt))
        report_variants.append({
            "id": candidate_id,
            "parent": PARENT,
            "axis": AXIS,
            "value": value,
            "status": "REPRODUCED_EXISTING_BUILT_ROW",
            "predicted_change": row.get("predicted_change", ""),
            "form_note": receipt.get("form_note", ""),
            "parent_diff": diff,
            "primary": primary,
            "zeros_fallback": zeros,
            "zip_primary": zip_primary,
            "zip_zeros": zip_zeros,
        })
        print(
            f"      {value}: {int(mask.sum()):,} dots; {moved_pct:.2f}% moved; "
            f"TIFF SHA {primary['sha256'][:8]}...; format/re-read PASS"
        )

    print("[5/5] Save reproduction receipts (no ledger mutation)...")
    for receipt_path, receipt in receipt_updates:
        receipt_path.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    report = {
        "schema": "gems88.prune-artifact-rebuild.v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "git_sha_at_rebuild": rebuild_git_sha,
        "working_tree_clean_at_rebuild_start": source_tree_clean,
        "script_sha256": sha256(Path(__file__)),
        "evidence_class": "REPRODUCTION",
        "new_experiment": False,
        "new_ledger_rows": 0,
        "parent": {
            "id": PARENT,
            "dots": int(lineage["r0"].sum()),
            "zeros_sha256": lineage["rebuilt_zeros_sha256"],
            "nan_sha256": lineage["rebuilt_nan_sha256"],
        },
        "manifest": {
            "verified_count": len(verified),
            "ids": sorted(verified),
            "sha256_and_bytes": "PASS",
        },
        "leakage_canary_report_only": {
            "passed": max(canaries.values()) <= 0.90,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        },
        "variants": report_variants,
        "slots_used": 0,
        "submitted": False,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"PASS: wrote {REPORT_PATH.relative_to(ROOT)}; ledger rows unchanged; no submission made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
