#!/usr/bin/env python3
"""Build H88-VVENT: a novel, unique GEMS submission GeoTIFF.

Geological hypothesis (preregistered below): young volcanic vents and
high-temperature springs mark *concealed* geothermal faults that are missing
from the USGS/INGENIOUS catalogue (which maps Quaternary surface traces, not
young volcanic/geothermal plumbing under piedmont cover).

    * Layers: DOE GDR #1391 volcanic vents (gdr_volcanic_vents_in_footprint.csv,
      all basalt, none on mapped faults, 10/21 > 2.5 km from any mapped fault)
      and high-temperature springs (> 60 C, 2,343 points, 842 > 2.5 km from
      mapped faults) from gdr_wellspring_in_footprint.csv.
    * Physical signature: volcanic vent / hot spring co-located with a
      geophysical edge -- magnetic demagnetisation low, conductive clay cap,
      basement-depth gradient -- indicates a concealed fault controlling
      geothermal upflow.
    * Why it catches catalogue-missing faults: vents and hot springs are direct
      geothermal surface expressions; most lie far from any mapped Quaternary
      trace, so they point at concealed faults the catalogue lacks.
    * Named non-fault mimic: young volcanic centres without fault control,
      fumarolic areas on unfaulted volcanic rock, warm springs from shallow
      (non-fault) circulation, playa clay conductivity.
    * Differs from repo lanes: prior lanes use fault-adjacent geophysics
      (ridge/knickpoint, scalar magnetic or gravity gradients, updip sinter).
      This lane uses *point volcanic/geothermal surface expressions* as the
      primary prior, combined with edge/conductivity/basement evidence, and
      emits dots off-catalogue. Volcanic vents are not used by any existing
      lane.

Built exclusively from pinned public inputs (owner mirrors, DOE GDR #1391 CC
BY 4.0, USGS GeoDAWN/3DEP CC0). No organiser-authenticated data, no leaderboard
truth, no private feature fork. Shared vendor/gems57 tools only.

Output (research artifact; submit status decided separately by the selector):
  docs/downloads/gems88-vvent88-volcanic-vent-hotspring-<sha>-zeros-DO-NOT-SUBMIT.tif
  + one-TIFF ZIP + JSON receipt.

The generated raster is intentionally *not* submitted through this script;
promotion to a weekly competition slot is a separate selector step.
"""

from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    from scripts.generation_guard import enforce_generation_preflight

    enforce_generation_preflight()

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import grid, geo, emit, metric
from gems57.submission_writer import write_submission
from gems57.uniqueness import compare_array_to_registry
from gems57.validate import validate, assert_submittable
from gems57.gates import format_report

# --- lanes / protocol constants -------------------------------------------------
RHO_LIMIT = 0.90
OVERLAP_LIMIT = 0.70
DOT_BUDGET = 37_654  # same successful areal density as the H33 lineage
TILE_PX = 3  # one dot per 3 px tile ~= 300 m spacing, matches the DTI kernel
VENT_SIGMA_PX = 12.0  # ~1.2 km prospectivity halo around each young vent
SPRING_SIGMA_PX = 10.0  # ~1.0 km halo around each hot spring
HOT_C = 60.0  # spring temperature threshold (C) for "high-temperature"

VENTS_CSV = ROOT / "data/external/gdr_volcanic_vents_in_footprint.csv"
SPRINGS_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"
INDEX_PATH = ROOT / "registry/inventory.json"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"
DOWNLOADS = ROOT / "docs/downloads"
NAME = "GEMSDOE88-VVENT88-VOLCANIC-VENT-HOTSPRING-20261025"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_points(path: Path, temp_threshold: float | None = None):
    """Return (n, 2) integer (row, col) pixel points, optionally temperature filtered."""
    pts = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if temp_threshold is not None:
                t = (row.get("temp_c") or "").strip()
                if not t or float(t) <= temp_threshold:
                    continue
            r = int(float(row["row"]))
            c = int(float(row["col"]))
            pts.append((r, c))
    return np.array(pts, dtype=int) if pts else np.zeros((0, 2), dtype=int)


def proximity_signal(points: np.ndarray, shape, sigma_px: float, weights: np.ndarray | None = None):
    """Distance-to-nearest-point decay signal in [0, 1] (1 at the point)."""
    mask = np.zeros(shape, dtype=bool)
    if len(points):
        r = np.clip(points[:, 0], 0, shape[0] - 1)
        c = np.clip(points[:, 1], 0, shape[1] - 1)
        mask[r, c] = True
    d = ndi.distance_transform_edt(~mask)  # inf where no points -> handle below
    if weights is not None and len(points):
        # nearest-point distance then attenuate by the weight of the nearest point
        pass
    sig = np.exp(-np.minimum(d, 6 * sigma_px) / sigma_px)
    sig[~np.isfinite(d)] = 0.0
    return sig


def robust01(a: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Robust min-max to [0,1] inside ``mask`` using 2nd/98th percentiles."""
    v = a[mask]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.zeros_like(a, np.float32)
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    if hi <= lo:
        hi = lo + 1e-6
    out = np.clip((a - lo) / (hi - lo), 0.0, 1.0)
    return np.where(mask, out, 0.0).astype(np.float32)


def build_posterior(g: grid.Grid) -> np.ndarray:
    """Posterior prospectivity in [0, 1], zero off-footprint and zero on faults."""
    H, W = g.shape
    footprint = g.footprint
    faults = g.catalogue

    # --- 1. volcanic vents (young basalt, strong localized geothermal signal) ---
    vents = read_points(VENTS_CSV)
    s_vent = proximity_signal(vents, (H, W), VENT_SIGMA_PX)
    s_vent = robust01(s_vent, footprint)

    # --- 2. high-temperature springs (>60 C), broader geothermal prior ----------
    springs = read_points(SPRINGS_CSV, temp_threshold=HOT_C)
    s_spring = proximity_signal(springs, (H, W), SPRING_SIGMA_PX)
    s_spring = robust01(s_spring, footprint)

    # --- 3. geophysical edge/conductivity/basement evidence (catalogue-free) ----
    planes = geo.load_planes(footprint)
    g_edge_max = np.clip(planes["g_edge_max"], 0.0, None)  # multi-method edge consensus
    g_cond = np.clip(planes["g_cond"], 0.0, None)  # conductivity (clay / alteration)
    g_base = np.clip(planes["g_base_edge"], 0.0, None)  # basement-depth gradient
    s_geo = robust01(g_edge_max + g_cond + g_base, footprint)

    # --- 4. fuse: spring broad + edge + vent local, all catalogue-free ----------
    post = 0.45 * s_spring + 0.30 * s_geo + 0.25 * s_vent
    post = np.clip(post, 0.0, 1.0)
    post = robust01(post, footprint)

    # --- 5. mask visible faults pixel-exactly; zero off-footprint ---------------
    allowed = footprint & ~faults
    post = np.where(allowed, post, 0.0)
    post = np.where(footprint, post, 0.0)
    return post, allowed, vents, springs, dict(
        s_vent=s_vent, s_spring=s_spring, s_geo=s_geo,
    )


def main() -> int:
    g = grid.load_grid(ROOT / "data/bridge")
    post, allowed, vents, springs, comps = build_posterior(g)

    # --- 6. emit sparse dots (one per 3 px tile, top of posterior ranking) -----
    ranked, tile_max = emit.emit_decimated(post, allowed, tile_px=TILE_PX, floor=0.0)
    dots = emit.emit_prefix(ranked, DOT_BUDGET)
    n_dots = int(dots.sum())
    print(f"[build] posterior nonzero px: {int((post > 0).sum())}")
    print(f"[build] allowed px: {int(allowed.sum())}")
    print(f"[build] emitted dots: {n_dots}")
    print(f"[build] vents used: {len(vents)}; hot springs (>60C) used: {len(springs)}")
    print(f"[build] dots on catalogue: {int((dots & g.catalogue).sum())}")
    print(f"[build] dots outside footprint: {int((dots & ~g.footprint).sum())}")

    # Values in [0,1], finite, zero off-footprint and on faults -> portal-safe.
    prediction = dots.astype(np.float32)

    # --- 7. write TIFF + one-TIFF ZIP + receipt ---------------------------------
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Use a content hash as the unique token so the name is reproducible and
    # collision-free (independent of the wall clock).
    content_token = hashlib.sha256(prediction.tobytes()).hexdigest()[:12]
    tif_path = DOWNLOADS / (
        f"gems88-vvent88-volcanic-vent-hotspring-{stamp}-{content_token}"
        f"-zeros-DO-NOT-SUBMIT.tif"
    )
    if tif_path.exists():
        raise FileExistsError(f"refusing to overwrite {tif_path}")

    note = (
        f"H88-VVENT volcanic-vent+hot-spring+geology concealed-fault PoE "
        f"{n_dots} dots; HOLDOUT-DTI pending; values in [0,1]; UNSCORED"
    )
    if len(note) > 140:
        note = note[:137] + "..."
    receipt = write_submission(
        tif_path,
        prediction,
        sample=SAMPLE,
        footprint=g.footprint,
        name=NAME,
        note=note,
        catalogue=g.catalogue,
        metadata=dict(
            lane="H88-VVENT",
            hypothesis="young volcanic vents + high-temperature springs mark concealed geothermal faults missing from the USGS/INGENIOUS catalogue",
            vents=int(len(vents)),
            hot_springs=int(len(springs)),
            n_dots=n_dots,
            tile_px=TILE_PX,
        ),
    )
    print(f"[build] wrote {tif_path.name}")
    print(f"[build] SHA-256: {receipt['sha256']}")
    print(f"[build] submission name: {receipt['submission_name']} ({receipt['note_chars']} chars)")

    # --- 8. local format validation ---------------------------------------------
    fmt = format_report(tif_path, SAMPLE, footprint=g.footprint)
    loc = validate(tif_path, g.footprint, g.catalogue)
    assert_submittable(loc)
    print(f"[validate] format ok={fmt['ok']} bands={fmt['bands']} dtype={fmt['dtype']}")
    print(f"[validate] min={fmt['min']} max={fmt['max']} nan={fmt['n_nan']} "
          f"outside_footprint={fmt.get('mass_outside_footprint')} on_catalogue={loc.get('on_catalogue')}")

    # --- 9. uniqueness vs the public owner-repository inventory (dot fields) ----
    # Run against the full hash-pinned inventory. The dense 17GEMSDOE witness is
    # positive on every footprint cell, so it reports forward_overlap == 1.0 --
    # that is the binding literal blocker reported separately below. Every
    # dot-field sibling is checked for the protocol's two conditions.
    uniq = compare_array_to_registry(
        prediction, INDEX_PATH, g.footprint,
        expected_grid=(g.shape, g.crs, g.transform),
    )
    print(f"[uniqueness] checked {uniq['registry_rasters_checked']} rasters "
          f"(complete_scan={uniq['complete_accessible_scan']})")
    print(f"[uniqueness] worst rho: {uniq['worst_spearman_full_footprint']}")
    print(f"[uniqueness] worst dot overlap: {uniq['worst_dot_overlap']}")
    print(f"[uniqueness] duplicate count: {uniq['duplicate_count']}")
    for row in uniq.get("rows", []):
        if row.get("duplicate_by_rho") or row.get("duplicate_by_overlap"):
            print(f"  [BLOCK] {row.get('repo')}/{row.get('submission')} "
                  f"rho={row.get('spearman_full_footprint')} overlap={row.get('forward_overlap')}")

    # --- 10. write run card ------------------------------------------------------
    run_card = dict(
        schema="gems88.vvent.run-card.v1",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        lane="H88-VVENT",
        hypothesis="Young volcanic vents and high-temperature springs mark concealed geothermal faults missing from the USGS/INGENIOUS Quaternary fault catalogue.",
        mechanism="Vent + hot spring co-located with magnetic demagnetisation low / conductive clay cap / basement gradient indicates a concealed fault controlling geothermal upflow; dots emitted off-catalogue.",
        named_non_fault_mimic="Young volcanic centres without fault control; fumaroles on unfaulted volcanic rock; shallow warm-spring circulation; playa clay conductivity.",
        layers=[
            "DOE GDR #1391 gdr_volcanic_vents_in_footprint.csv (21 basalt vents)",
            "DOE GDR #1391 gdr_wellspring_in_footprint.csv (>60 C springs)",
            "Competition training_features: rtp/mag, cond_surf, depth_to_base_surf (gem57 geo planes)",
        ],
        physical_signature="volcanic vent / hot spring + geophysical edge (mag low, conductivity high, basement gradient)",
        why_catches_missing_faults="vents and hot springs are direct geothermal expressions far from mapped Quaternary traces -> concealed faults absent from USGS/INGENIOUS",
        differs_from_repo="uses point volcanic/geothermal surface expressions as primary prior (vents unused by any lane); off-catalogue emission; no fault-adjacent catalogue features",
        holdout=dict(
            status="SEE_SEPARATE_HOLDOUT_EVALUATION",
            evaluator_version="gems57-pooled-hide-v2",
            note="buffered whole-component hide-and-recover, alpha 0.2 beta 0.8, 300 m triangular kernel",
        ),
        canary=dict(status="SEE_SEPARATE_CANARY", note="each feature alone on held-out positives; AUC > 0.90 = leakage"),
        uniqueness=dict(
            registry_inventory=str(INDEX_PATH),
            rasters_checked=uniq["registry_rasters_checked"],
            complete_accessible_scan=uniq["complete_accessible_scan"],
            worst_spearman_full_footprint=uniq["worst_spearman_full_footprint"],
            worst_dot_overlap_3px=uniq["worst_dot_overlap"],
            duplicate_count=uniq["duplicate_count"],
            note="dense 17GEMSDOE witness is positive on every footprint cell -> forward_overlap 1.0 under literal all-raster reading (binding blocker reported separately)",
        ),
        raster_sha256=receipt["sha256"],
        raster_bytes=receipt["bytes"],
        validator=dict(
            format_ok=fmt["ok"],
            no_nan=fmt["n_nan"] == 0,
            values_in_0_1=(fmt["min"] >= 0 and fmt["max"] <= 1),
            crs_match=fmt["crs"] == "EPSG:32611",
            shape_match=fmt["height"] == g.shape[0] and fmt["width"] == g.shape[1],
            transform_match=list(fmt["transform"])[:6] == list(grid.TRANSFORM)[:6],
            no_positive_outside_footprint=fmt.get("mass_outside_footprint", 1) == 0,
            no_positive_on_catalogue=loc.get("on_catalogue", 1) == 0,
        ),
        submission_name=NAME,
        submission_note=note,
        submission_note_chars=len(note),
        raster_file=tif_path.name,
        zip_file=Path(receipt["zip_file"]).name if isinstance(receipt.get("zip_file"), str) else tif_path.with_suffix(".zip").name,
        zip_sha256=receipt.get("zip_sha256"),
        approved_for_weekly_slot=False,
        promoted=False,
        submission_slots_used=0,
        verdict="negative_under_binding_literal_rule",
        organizer_confirmed_score=None,
        data_provenance="SHA-pinned owner GitHub mirrors; DOE GDR #1391 CC BY 4.0; USGS GeoDAWN/3DEP CC0; not organizer-authenticated",
    )
    run_card_path = ROOT / "registry/vvent88_run_card.json"
    run_card_path.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n")
    print(f"[run card] wrote {run_card_path}")
    print(f"[build] verdict: {run_card['verdict']} (0 weekly slots used)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
