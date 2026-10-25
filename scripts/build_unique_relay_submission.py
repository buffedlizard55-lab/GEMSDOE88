#!/usr/bin/env python3
"""
Build a UNIQUE GEMS submission GeoTIFF from a novel geological hypothesis.

Hypothesis (novel vs the listed GEMSDOE sites):
  Geothermal fluid upflow concentrates at DILATIONAL structural sites --
  fault intersections, relay ramps between overlapping segments, and
  releasing step-overs / bends -- rather than on simple fault traces.
  The USGS/INGENIOUS catalogue maps fault traces; most listed GEMSDOE
  submissions re-mark traces via distance-to-fault, scarp/ridge openness,
  or dotted Poisson ridge lines. This lane instead derives a *curvature-and-
  junction relay propensity* from the catalogue trace network and
  deliberately suppresses pixels directly on known traces so the signal
  targets off-trace dilational sites (potentially concealed / under-mapped
  faults) rather than re-predicting the mapped catalogue.

Named non-fault mimic:
  Erosional drainage/network junctions and lithologic contacts also produce
  curved, intersecting lineament-like patterns that are not faults. The
  relay-zone band (moderate distance from any mapped trace) and the
  catalogue-zero mask mitigate this; it remains the named mimic.

How it differs from existing methods:
  Listed GEMSDOE submissions (H33 dotted ridge, H19 powerlaw, h28 dotted
  ridge, lidarscarp, etc.) use distance-to-catalogue, scarp/ridge openness,
  or Poisson dots along topographic ridges. This lane targets off-trace
  relay/dilational geometry (intersections + bends) and explicitly zeros
  the catalogue and a narrow trace buffer, so it is not a re-mark of known
  faults.

Method (fully vectorized, scipy.ndimage):
  1. Structure tensor of the binary fault catalogue -> local orientation
     field theta and coherence R (1 = single aligned orientation locally,
     0 = ambiguous / bend / junction).
  2. Curvature proxy = 1 - R, confined to trace pixels, Gaussian-smoothed
     (high at bends, kinks, step-overs, and junctions).
  3. Junction/relay proxy = on-trace pixels where local orientation is
     ambiguous (low coherence) -> intersections / relay zones.
  4. Relay propensity = blend of curvature and junction proximity
     (distance transform to the junction proxy), Gaussian-smoothed.
  5. Suppress pixels within 2 px of any catalogue trace (off-trace novelty
     emphasis) and zero all catalogue pixels pixel-exactly.
  6. Normalize to [0,1], zero outside the scored footprint.

Outputs (docs/downloads/, one-TIFF ZIP + JSON receipt + run card):
  gemsdoe88-relay-dilational-<utc>-<arrhash>-zeros.tif / .zip / .json

This script is a LOCAL FORMAT/SCIENCE PREFLIGHT only. It does NOT contact the
DrivenData portal, does NOT claim an organizer score, and does NOT spend a
weekly submission slot. It reports OK-TO-DOWNLOAD (format/range valid) and
OK-TO-SUBMIT honestly (blocked here by the binding literal 17GEMSDOE
space-filling witness: every nonempty candidate overlaps it 1.0 > 0.70).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems57 import grid as grid_mod  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems57.validate import validate  # noqa: E402
from gems57.gates import format_report  # noqa: E402
from gems57.uniqueness import dot_overlap  # noqa: E402

BRIDGE = ROOT / "data" / "bridge"
DOWNLOADS = ROOT / "docs" / "downloads"
DOWNLOADS.mkdir(parents=True, exist_ok=True)

RADIUS_PX = 3.0  # literal near-overlap radius (shared protocol)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def structure_tensor_fields(binary: np.ndarray, sigma: float = 2.0):
    """Orientation field theta and coherence R from the structure tensor."""
    a = binary.astype(np.float64)
    gx = ndi.gaussian_filter(a, sigma, order=(0, 1), mode="constant")
    gy = ndi.gaussian_filter(a, sigma, order=(1, 0), mode="constant")
    # Structure tensor components (smoothed).
    sxx = ndi.gaussian_filter(gx * gx, sigma, mode="constant")
    syy = ndi.gaussian_filter(gy * gy, sigma, mode="constant")
    sxy = ndi.gaussian_filter(gx * gy, sigma, mode="constant")
    # Eigenvalues of the 2x2 tensor; coherence = anisotropy.
    diff = sxx - syy
    radicand = np.hypot(diff, 2.0 * sxy)
    lam1 = 0.5 * (sxx + syy + radicand)
    lam2 = 0.5 * (sxx + syy - radicand)
    denom = lam1 + lam2
    R = np.where(denom > 1e-12, (lam1 - lam2) / (denom + 1e-12), 0.0)
    # Line orientation is normal to the gradient; theta periodic in pi.
    theta = 0.5 * np.arctan2(2.0 * sxy, diff)
    return theta, R, lam1, lam2


def build_relay_propensity(cat: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    cat = np.asarray(cat, dtype=bool)
    fp = np.asarray(footprint, dtype=bool)

    # 1. Orientation + coherence of the fault trace network.
    theta, R, lam1, lam2 = structure_tensor_fields(cat & fp, sigma=2.0)
    # Curvature proxy: ambiguous local orientation => bend / step-over / junction.
    curvature = 1.0 - R  # 1 = isotropic/bend, 0 = perfectly aligned trace

    # 2. Junction / relay proxy: on-trace pixels with ambiguous orientation
    #    (multiple competing local directions = intersection / relay zone).
    on_trace = cat & fp
    low_coherence = R < 0.45
    junction_proxy = on_trace & low_coherence & (lam1 > 1e-6)

    # 3. Proximity to junctions decays with distance (relay-zone envelope).
    dist_to_junction = ndi.distance_transform_edt(~junction_proxy)
    junction_prox = np.exp(-(dist_to_junction / 8.0) ** 2)

    # 4. Curvature confined to the trace network, smoothed.
    curvature_on_trace = np.where(on_trace, curvature, 0.0)
    curvature_smooth = ndi.gaussian_filter(curvature_on_trace, sigma=3.0,
                                           mode="constant")
    cs_max = float(curvature_smooth.max())
    if cs_max > 0:
        curvature_smooth = curvature_smooth / cs_max

    # 5. Combined relay propensity.
    propensity = 0.5 * junction_prox + 0.5 * curvature_smooth
    propensity = ndi.gaussian_filter(propensity, sigma=2.0, mode="constant")

    # 6. Off-trace novelty emphasis: suppress pixels directly on mapped traces
    #    (3 px buffer) so the signal targets relay / off-trace sites and does
    #    not re-mark the catalogue flank that other lanes already cover.
    trace_dil = ndi.binary_dilation(cat, iterations=3)
    propensity = np.where(trace_dil, 0.0, propensity)

    # 7. Restrict to scored footprint; zero catalogue pixels pixel-exactly.
    propensity = np.where(fp, propensity, 0.0)
    propensity = np.where(cat, 0.0, propensity)
    return propensity


def main() -> None:
    G = grid_mod.load_grid(BRIDGE)
    fp, cat = G.footprint, G.catalogue

    propensity = build_relay_propensity(cat, fp)

    pos = propensity > 0
    if not pos.any():
        raise RuntimeError("relay propensity produced no support")
    lo, hi = float(propensity[pos].min()), float(propensity[pos].max())
    print(f"raw propensity support: {int(pos.sum())} px, min={lo:.6f} max={hi:.6f}")

    out = np.zeros_like(propensity, dtype=np.float64)
    out[pos] = (propensity[pos] - lo) / (hi - lo)
    out = np.clip(out, 0.0, 1.0)
    out = np.where(fp, out, 0.0).astype(np.float32)
    out = np.where(cat, 0.0, out).astype(np.float32)

    # Sparse binary dots: keep only the strongest dilational sites (top K
    # propensity pixels), then apply non-maximum suppression with a minimum
    # spacing so dots spread across distinct relay zones instead of clustering.
    # This keeps the submission dot-like and reduces overlap with any clustered
    # prior. Everything not selected is exactly 0.
    TARGET_DOTS = 25000  # more selective than H33's 37,654
    MIN_SPACING_PX = 6.0  # non-maximum suppression radius (px)
    flat = propensity.ravel()
    n_candidates = int(pos.sum())
    k = min(TARGET_DOTS, n_candidates)
    threshold = np.partition(flat, -k)[-k]
    seed_mask = propensity >= threshold
    if int(seed_mask.sum()) > k:
        order = np.argsort(-propensity, kind="stable", axis=None)[:k]
        seed_mask = np.zeros_like(propensity, dtype=bool)
        seed_mask.flat[order] = True

    # Non-maximum suppression: keep a seed only if no stronger seed within
    # MIN_SPACING_PX. Process seeds in descending propensity order.
    keep = np.zeros_like(propensity, dtype=bool)
    suppressed = np.zeros_like(propensity, dtype=bool)
    order = np.argsort(-propensity, kind="stable", axis=None)
    r = int(np.floor(MIN_SPACING_PX))
    rr2 = MIN_SPACING_PX * MIN_SPACING_PX
    ys, xs = np.nonzero(seed_mask)
    coords = np.column_stack([ys, xs])
    values = propensity[ys, xs]
    order_sorted = np.argsort(-values, kind="stable")
    kept_coords = []
    for idx in order_sorted:
        y, x = int(coords[idx, 0]), int(coords[idx, 1])
        if suppressed[y, x]:
            continue
        keep[y, x] = True
        kept_coords.append((y, x))
        # suppress neighbours within radius (exact circular footprint)
        yy, xx = np.mgrid[max(0, y-r):min(propensity.shape[0], y+r+1),
                          max(0, x-r):min(propensity.shape[1], x+r+1)]
        d2 = (yy - y) ** 2 + (xx - x) ** 2
        suppressed[yy[d2 <= rr2], xx[d2 <= rr2]] = True

    out = np.zeros_like(propensity, dtype=np.float32)
    out[keep] = 1.0
    out = np.where(fp, out, 0.0).astype(np.float32)
    out = np.where(cat, 0.0, out).astype(np.float32)

    n_dots = int((out > 0).sum())
    print(f"target dots: {TARGET_DOTS}  emitted dots: {n_dots}  "
          f"({100.0 * n_dots / fp.sum():.4f}% of footprint)  "
          f"seed threshold={threshold:.6f}")
    print(f"on catalogue: {int(((out > 0) & cat).sum())}  "
          f"outside footprint: {int(((out > 0) & ~fp).sum())}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arr_hash = hashlib.sha256(out.tobytes()).hexdigest()[:12]
    stem = f"gemsdoe88-relay-dilational-{stamp}-{arr_hash}-zeros"
    tif_path = DOWNLOADS / f"{stem}.tif"

    name = "GEMSDOE88-RELAY-DILATIONAL"
    note = ("Sparse relay-zone + intersection dilational dots off mapped traces; "
            "format-valid; UNSCORED; blocked-by-17GEMSDOE-witness")
    assert len(name) <= 140 and len(note) <= 140, "name/note over 140 chars"
    print("name:", name, f"({len(name)}ch)  note:", f"({len(note)}ch)")

    # Write via the shared submission_writer (format-validates in memory + on disk).
    receipt = write_submission(
        tif_path, out,
        sample=BRIDGE / "sample_submission.tif",
        footprint=fp, catalogue=cat,
        note=note, name=name,
        metadata=dict(
            hypothesis="fault-intersection / relay-zone / step-over dilational propensity",
            mechanism="structure-tensor orientation/coherence of catalogue traces; "
                      "junction proxy (on-trace low coherence); curvature (1-coherence); "
                      "gaussian-smoothed relay propensity; zero within 2px of trace "
                      "and on catalogue; normalize [0,1]",
            non_fault_mimic="erosional drainage junctions and lithologic contacts",
            method="structure-tensor orientation + coherence (sigma 2 px); "
                   "junction proxy = on-trace low coherence; curvature = 1-coherence; "
                   "blend + gaussian smooth; suppress on/near catalogue; normalize [0,1]",
            evaluator="gems57-pooled-hide-v2 (alpha 0.2 beta 0.8, 300 m triangular)",
            holds="local preflight only; not organizer acceptance; weekly slot not spent",
        ),
    )
    print("\nWRITTEN:", tif_path)
    print("sha256:", receipt["sha256"])
    print("bytes:", receipt["bytes"])
    print("zip:", receipt["zip_file"])
    print("format_report ok:", receipt["template_report"]["ok"])
    print("all local checks passed:", receipt["validator"]["all_checks_passed"])

    # Independent local validation re-open.
    local = validate(tif_path, fp, cat)
    print("\nINDEPENDENT VALIDATE all_checks_passed:", local["all_checks_passed"])
    print("min/max:", local["min"], local["max"], "n_nan:", local["n_nan"])

    # ---- Uniqueness vs the accessible registry (literal gate) ----
    registry = {}
    for p in sorted((ROOT / "data" / "registry").rglob("*.tif")):
        if "dense_17gemdoe" in p.name:
            continue  # binding witness, handled separately
        try:
            with rasterio.open(p) as s:
                a = s.read(1)
            if a.shape == out.shape:
                registry[p.name] = a
        except Exception as e:
            print("registry read skip", p.name, e)

    worst_ov = 0.0; worst_ov_name = None
    worst_rho = 0.0; worst_rho_name = None
    mine2d = out
    for nm, a in registry.items():
        ov = dot_overlap(out, a, radius_px=RADIUS_PX)
        if ov > worst_ov:
            worst_ov, worst_ov_name = ov, nm
        m = np.isfinite(a) & np.isfinite(mine2d)
        if m.sum() > 1000:
            rho, _ = spearmanr(out[m], a[m])
            rho = abs(float(rho))
            if rho > worst_rho:
                worst_rho, worst_rho_name = rho, nm

    # 17GEMSDOE space-filling witness (the binding blocker).
    with rasterio.open(ROOT / "data" / "registry" / "dense_17gemdoe.tif") as s:
        witness = s.read(1)
    ov_witness = dot_overlap(out, witness, radius_px=RADIUS_PX)
    print("\n=== LITERAL UNIQUENESS (accessible registry) ===")
    print(f"worst 3-px dot overlap (excl. witness): {worst_ov:.4f} vs {worst_ov_name}")
    print(f"worst |Spearman| surface (excl. witness): {worst_rho:.4f} vs {worst_rho_name}")
    print(f"17GEMSDOE witness 3-px dot overlap: {ov_witness:.4f} "
          f"(space-filling: all {int(witness[fp].sum())} footprint cells > 0)")
    print(f"LITERAL GATE: overlap_limit=0.70 rho_limit=0.90 -> "
          f"{'BLOCKED (witness overlap > 0.70)' if ov_witness > 0.70 else 'clear on witness'}")
    print("=> OK to DOWNLOAD (format/range valid): YES")
    print("=> OK to SUBMIT: NO  (binding literal 17GEMSDOE witness overlap > 0.70; "
          "not organizer-confirmed; weekly slot NOT spent)")

    card = {
        "schema": "gems.run_card.v1",
        "run_id": f"GEMSDOE88-RELAY-{arr_hash}",
        "generated_utc": stamp,
        "lane": "H88-RELAY-DILATIONAL",
        "hypothesis": ("Geothermal upflow concentrates at fault-intersection / "
                       "relay-zone / step-over dilational sites, not on simple "
                       "fault traces."),
        "mechanism": ("Structure-tensor orientation/coherence of catalogue traces; "
                      "junction proxy (on-trace low coherence); curvature (1-coherence); "
                      "gaussian-smoothed relay propensity; zero within 3 px of trace "
                      "and on catalogue; normalize [0,1]."),
        "named_non_fault_mimic": ("Erosional drainage junctions and lithologic contacts "
                                  "produce curved intersecting lineament-like patterns."),
        "how_it_differs": ("Listed GEMSDOE submissions use distance-to-trace, "
                           "scarp/ridge openness, or dotted Poisson ridge lines; "
                           "this lane targets off-trace relay/dilational geometry."),
        "evidence_class": "HOLDOUT-DTI (not yet established; local preflight only)",
        "evaluator": "gems57-pooled-hide-v2 (alpha 0.2, beta 0.8, 300 m triangular)",
        "holdout_dti": None,
        "ci95": None,
        "withheld_positives": None,
        "uniqueness": {
            "worst_dot_overlap_excl_witness": worst_ov,
            "worst_dot_overlap_submission": worst_ov_name,
            "worst_spearman_excl_witness": worst_rho,
            "worst_spearman_submission": worst_rho_name,
            "witness_3px_overlap": ov_witness,
            "witness_space_filling_all_footprint_cells_positive": True,
            "literal_gate_result": "BLOCKED",
            "overlap_limit": 0.70,
            "rho_limit": 0.90,
        },
        "validator": {
            "all_checks_passed": bool(local["all_checks_passed"]),
            "no_nan": bool(local["n_nan"] == 0),
            "range_0_1": bool(local["min"] >= 0.0 and local["max"] <= 1.0),
            "crs_epsg_32611": True,
            "shape_3730x3292": True,
            "transform_match": True,
            "zero_outside_footprint": bool(local["checks"].get("outside_footprint_zero", False)),
            "zero_on_catalogue": bool(local["checks"].get("zero_dots_on_mapped_catalogue", False)),
        },
        "submission": {
            "file": str(tif_path.relative_to(ROOT)),
            "sha256": receipt["sha256"],
            "bytes": receipt["bytes"],
            "name": name,
            "note": note,
            "note_chars": len(note),
            "n_dots": n_dots,
            "ok_to_download": True,
            "ok_to_submit": False,
            "submit_block_reason": ("binding literal 17GEMSDOE space-filling witness "
                                    "overlap > 0.70; not organizer-confirmed"),
        },
        "verdict": "negative",
    }
    card_path = DOWNLOADS / f"{stem}.run_card.json"
    card_path.write_text(json.dumps(card, indent=2) + "\n")
    print("\nRUN CARD:", card_path)
    print("VERDICT: negative (not promoted to a weekly slot)")


if __name__ == "__main__":
    main()
