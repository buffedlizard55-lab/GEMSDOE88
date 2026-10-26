#!/usr/bin/env python3
"""Build ONE unique, format-valid GEMS research GeoTIFF and prove its submit status.

Contrarian hypothesis (distinct from every lane already in this repo):
blind hydrothermal upflow under young piedmont alluvial cover leaves subtle
potassium metasomatism (USGS GeoDAWN eK) and drainage control (DEM chi/knickpoints)
but NO resolvable LiDAR scarp and NO mapped USGS/INGENIOUS trace -- so it is an
off-catalogue, radiometric-alteration-on-young-cover target that scarp-, magnetic-,
gravity- and sinter-hunting lanes systematically miss.

Named non-fault mimic: K-rich transported alluvium / unfaulted lithologic K source /
drainage concentration (no discrete fault required).

This script REUSES the shared vendor stack only:
  gems57.grid        - pinned EPSG:32611 / 3730x3292 / sample transform + footprint/catalogue
  gems57.validate    - all-finite [0,1], CRS/shape/transform, no mass outside footprint
  gems57.gates       - on-disk format_report (rasterio)
  gems57.submission_writer - byte-exact TIF + one-TIFF ZIP + receipt JSON
  gems57.uniqueness  - registry rank-correlation + 3-px dot-overlap gate

Nothing is trained, nothing is copied from a previous submission.  The emitted raster is
zero outside the footprint and zero on the mapped catalogue, so it passes the local
range/format policy that produced the historical "Predicted values must be in range [0, 1]"
rejection for NaN-outside files.

The binding shared preflight (DUPLICATE_STOP: the pinned 17GEMSDOE dense witness covers
every allowed cell) is RUN and RECORDED, not bypassed.  Because every nonempty allowed
candidate has literal forward 3-px overlap 1.0 with that witness, this file is:

  OK to DOWNLOAD for research / education:  YES
  OK to SUBMIT to the competition:         NO  -- DO NOT SUBMIT

It is published strictly as a research artifact with a -DO-NOT-SUBMIT name, a SHA-256,
an automated validator receipt, and a negative run card.
"""
from __future__ import annotations

if __name__ == "__main__":
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight

    enforce_generation_preflight()


import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

from gems57 import grid as grid_mod  # noqa: E402
from gems57 import validate, gates, submission_writer, uniqueness  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "preflight_mtas88", ROOT / "scripts" / "preflight_mtas88.py"
)
_preflight_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_preflight_mod)  # type: ignore[attr-defined]
preflight_inspect = _preflight_mod.inspect  # noqa: E402

# --- Reserved submission identity (<= 140 chars each) -----------------------
NAME = "GEMSDOE88-GEORAD-YOUNGCOVER-20261026"
NOTE = ("GEORAD88 radiometric K + young cover + drainage, off USGS catalogue; 20000 dots; "
        "blocked by 17GEMSDOE witness; UNSCORED; DO NOT SUBMIT")
assert len(NAME) <= 140 and len(NOTE) <= 140, "name/note must be <= 140 chars"

TIFF_STEM = "gems88-georad-youngcover-offcatalogue-20261026-zeros-DO-NOT-SUBMIT"
TIFF_PATH = ROOT / "docs" / "downloads" / f"{TIFF_STEM}.tif"
ZIP_PATH = ROOT / "docs" / "downloads" / f"{TIFF_STEM}.zip"
RECEIPT_PATH = ROOT / "docs" / "downloads" / f"{TIFF_STEM}.receipt.json"
RUN_CARD_PATH = ROOT / "registry" / "georad88_run_card.json"

N_DOTS = 20_000


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_band(path: Path, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(band).astype(np.float64)


def percentile(a: np.ndarray, q: float) -> float:
    return float(np.percentile(a, q))


def build_prediction(g: grid_mod.Grid) -> np.ndarray:
    fp = g.footprint
    cat = g.catalogue

    # ---- Layers (all free official sources, pinned by restore_inputs.py) ----
    k = load_band(ROOT / "data" / "external" / "geodawn_rad_u8.tif", 1) / 255.0  # eK
    thk = load_band(ROOT / "data" / "external" / "geodawn_extensions_u8.tif", 1) / 255.0  # K-Th
    slope = load_band(ROOT / "data" / "external" / "topo_10m_derived_100m_u8.tif", 1) / 255.0  # slope_p90
    chan = load_band(ROOT / "data" / "external" / "dem10_chi_100m_u8.tif", 1)  # chan_n
    knick = load_band(ROOT / "data" / "external" / "dem10_chi_100m_u8.tif", 2)  # knick_n

    # Radiometric K anomaly (hydrothermal K-metasomatism / alteration halo)
    k_lo, k_hi = percentile(k[fp], 5.0), percentile(k[fp], 95.0)
    k_score = np.clip((k - k_lo) / max(k_hi - k_lo, 1e-9), 0.0, 1.0)

    # Young alluvial cover proxy: low slope buries scarps -> faults stay unmapped
    cover_score = 1.0 - np.clip(slope, 0.0, 1.0)

    # Drainage structural control: blind faults reorganize channels/knickpoints
    drain = chan.astype(float) + 0.5 * knick.astype(float)
    d_lo, d_hi = percentile(drain[fp], 5.0), percentile(drain[fp], 95.0)
    drain_score = np.clip((drain - d_lo) / max(d_hi - d_lo, 1e-9), 0.0, 1.0)

    # Off-catalogue weight: rises to 1 beyond ~15 px (1.5 km) from any mapped trace
    from scipy import ndimage as ndi

    dist_to_cat = ndi.distance_transform_edt(~cat)
    offcat = np.clip(dist_to_cat / 15.0, 0.0, 1.0)

    # Multiplicative, zero if any ingredient is absent; zero on catalogue / outside footprint
    score = k_score * cover_score * drain_score * thk * offcat
    score = np.where(fp & ~cat, score, 0.0)
    assert not (((score > 0) & cat).any()), "positive mass on mapped catalogue"
    assert not (((score > 0) & ~fp).any()), "positive mass outside footprint"

    # Deterministic top-N dot emission (ties broken by row-major order)
    flat = score.ravel()
    order = np.argpartition(-flat, N_DOTS - 1)[:N_DOTS]
    order = order[flat[order] > 0]
    dots = np.zeros_like(score, dtype=bool)
    dots.ravel()[order] = True
    print(f"emitted dots: {int(dots.sum())}  (requested {N_DOTS})")

    pred = dots.astype(np.float32)
    assert np.isfinite(pred).all() and pred.min() >= 0.0 and pred.max() <= 1.0
    assert not ((pred > 0) & ~fp).any()
    assert not ((pred > 0) & cat).any()
    return pred


def registry_index() -> list[dict]:
    """Hash-verified registry rasters on the pinned grid."""
    records = []
    reg_dir = ROOT / "data" / "registry"
    for p in sorted(reg_dir.rglob("*.tif")):
        digest = sha256_file(p)
        with rasterio.open(p) as src:
            a = src.read(1)
        their_dots = int((np.isfinite(a) & (a > 0)).sum())
        records.append(
            dict(
                repo=p.parent.name,
                submission=p.name,
                file=str(p),
                sha256=digest,
                sources=[p.name],
            )
        )
    return records


def main() -> int:
    (ROOT / "docs" / "downloads").mkdir(parents=True, exist_ok=True)
    (ROOT / "registry").mkdir(parents=True, exist_ok=True)

    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    print(f"grid {g.shape} footprint={int(g.footprint.sum())} "
          f"catalogue={int(g.catalogue.sum())} allowed={int((g.footprint & ~g.catalogue).sum())}")

    pred = build_prediction(g)

    # ---- Write byte-exact TIF + one-TIFF ZIP + receipt (shared writer) ----
    sample = ROOT / "data" / "bridge" / "sample_submission.tif"
    receipt = submission_writer.write_submission(
        TIFF_PATH,
        pred,
        sample,
        g.footprint,
        note=NOTE,
        name=NAME,
        catalogue=g.catalogue,
        metadata=dict(
            hypothesis="H88-GEORAD: blind hydrothermal upflow as radiometric K alteration "
            "on young alluvial cover, off the USGS/INGENIOUS catalogue",
            mechanism="eK x young-cover(low slope) x drainage-control(chi/knickpoint) x "
            "off-catalogue distance, top-N binary emission",
            named_non_fault_mimic="K-rich transported alluvium / lithologic K source / "
            "drainage concentration",
            n_dots=int((pred > 0).sum()),
            pixel_m=100.0,
            radius_m=300.0,
            source_layers=[
                "data/external/geodawn_rad_u8.tif b1 K",
                "data/external/geodawn_extensions_u8.tif b1 ThK",
                "data/external/topo_10m_derived_100m_u8.tif b1 slope_p90",
                "data/external/dem10_chi_100m_u8.tif b1 chan_n b2 knick_n",
            ],
        ),
    )
    print(f"wrote {TIFF_PATH}  sha256={receipt['sha256']}")
    print(f"wrote {ZIP_PATH}  sha256={receipt['zip_sha256']}")

    # ---- Automated format/range validation (two decoders: rasterio via validate/gates) ----
    val_receipt = validate.validate(TIFF_PATH, g.footprint, g.catalogue)
    fmt_report = gates.format_report(TIFF_PATH, sample, footprint=g.footprint)
    print("validate.all_checks_passed:", val_receipt["all_checks_passed"])
    print("format_report.ok:", fmt_report["ok"], "problems:", fmt_report["problems"])

    # ---- Registry uniqueness (shared literal gate; NOT a clearance) ----
    expected_grid = (g.shape, g.crs, g.transform)
    uni = uniqueness.compare_array_to_registry(
        pred,
        registry_index(),
        g.footprint,
        expected_grid=expected_grid,
    )
    print("registry rasters checked:", uni["registry_rasters_checked"])
    print("worst literal forward overlap:", uni["worst_dot_overlap"],
          "vs", uni["worst_overlap_submission"])
    print("worst |spearman|:", uni["worst_spearman_full_footprint"],
          "vs", uni["worst_rho_submission"])
    print("literal duplicate flagged:", bool(uni["duplicate_count"] > 0), "unique:", uni["unique"])

    # ---- Binding shared preflight (recorded, not bypassed) ----
    preflight = preflight_inspect(ROOT)
    print("preflight decision:", preflight["decision"], "ok_to_submit:", preflight["ok_to_submit"])

    # ---- Run card (labels every number; projection is never a score) ----
    run_card = dict(
        schema="gems88.run-card.v1",
        reviewed_at_utc=datetime.now(timezone.utc).isoformat(),
        lane="H88-GEORAD",
        hypothesis="Blind hydrothermal upflow under young piedmont alluvial cover produces "
        "radiometric potassium alteration and drainage control but no resolvable scarp and "
        "no mapped USGS/INGENIOUS trace; an off-catalogue radiometric-on-young-cover target "
        "missed by scarp-, magnetic-, gravity- and sinter-hunting lanes.",
        mechanism="eK (GeoDAWN) x young-cover (low topo slope) x drainage control "
        "(DEM chi + knickpoints) x off-catalogue distance; deterministic top-N binary "
        "emission; zeros on catalogue and outside footprint.",
        layers=[
            {"file": "data/external/geodawn_rad_u8.tif", "bands": [1], "description": "eK"},
            {"file": "data/external/geodawn_extensions_u8.tif", "bands": [1], "description": "ThK contrast"},
            {"file": "data/external/topo_10m_derived_100m_u8.tif", "bands": [1], "description": "slope_p90 (young-cover proxy)"},
            {"file": "data/external/dem10_chi_100m_u8.tif", "bands": [1, 2], "description": "chan_n, knick_n (drainage control)"},
        ],
        off_catalogue_rationale="Young alluvium buries scarps, so USGS/INGENIOUS did not map "
        "these traces; the hunt is deliberately outside the catalogue to target missing faults.",
        named_non_fault_mimic="K-rich transported alluvium, unfaulted lithologic K source, "
        "drainage concentration",
        difference_from_implemented="XGCE uses grav x mag cross-gradient; BPWD uses Baranov "
        "pseudogravity + Poisson + worm; TDKL/LSC/SSA need scarps; HGVC needs surface sinter. "
        "This lane uses radiometric K + young cover + drainage on off-catalogue cells.",
        expected_potential="Unquantified; no numerical DTI projection (protocol forbids "
        "writing a projection as a score).",
        implementation_cost="Low; cached pinned inputs only, deterministic, no training.",
        falsification="Reject if a K-rich alluvium / lithology / drainage null reproduces "
        "the pattern, or the signal vanishes when the catalogue collar is widened.",
        evidence_class="RESEARCH ARTIFACT; NOT AN ORGANIZER SCORE",
        evaluator_version="gems57-pooled-hide-v2 (not run -- pre-placement duplicate stop)",
        withheld_positive_pixels=None,
        holdout_dti=None,
        ci95=None,
        holdout_reason="Pre-placement DUPLICATE_STOP precedes holdout; off-catalogue target is "
        "not measurable by catalogue-segment recovery, so no HOLDOUT-DTI is claimed.",
        leakage_canary=dict(
            status="NOT_RUN_PREPLACEMENT_STOP",
            auc=None,
            threshold=0.90,
            reason="No feature was fitted; canary requires a fitted candidate.",
        ),
        correlation_overlap_vs_registry=dict(
            registry_rasters_checked=uni["registry_rasters_checked"],
            worst_spearman_full_footprint=uni["worst_spearman_full_footprint"],
            worst_spearman_submission=uni["worst_rho_submission"],
            worst_forward_overlap_3px=uni["worst_dot_overlap"],
            worst_overlap_submission=uni["worst_overlap_submission"],
            literal_overlap_vs_17GEMSDOE=1.0,
            literal_limit=0.70,
            duplicate=bool(uni["duplicate_count"] > 0),
            stop_required=True,
        ),
        raster_sha256=receipt["sha256"],
        zip_sha256=receipt["zip_sha256"],
        bytes=receipt["bytes"],
        tif_file=str(TIFF_PATH.relative_to(ROOT)),
        zip_file=str(ZIP_PATH.relative_to(ROOT)),
        receipt_file=str(RECEIPT_PATH.relative_to(ROOT)),
        validator_output=dict(
            all_checks_passed=val_receipt["all_checks_passed"],
            no_nan_inside=val_receipt["checks"]["no_nan_anywhere"],
            no_inf_anywhere=val_receipt["checks"]["no_inf_anywhere"],
            values_in_0_1=val_receipt["checks"]["range_0_1_guaranteed"],
            crs_match=val_receipt["checks"][f"crs_epsg_{grid_mod.EPSG}"],
            shape_match=val_receipt["checks"][f"dimensions_{grid_mod.HEIGHT}x{grid_mod.WIDTH}"],
            transform_match=val_receipt["checks"]["transform_matches_sample_submission"],
            no_mass_outside_footprint=val_receipt["checks"]["outside_footprint_zero"],
            zero_dots_on_catalogue=val_receipt["checks"]["zero_dots_on_mapped_catalogue"],
            emitted_positive_pixels=val_receipt["emitted_positive_pixels"],
            min=val_receipt["min"],
            max=val_receipt["max"],
            format_report_ok=fmt_report["ok"],
            format_report_problems=fmt_report["problems"],
        ),
        submission_name=NAME,
        submission_name_chars=len(NAME),
        submission_note=NOTE,
        submission_note_chars=len(NOTE),
        approved_for_weekly_slot=False,
        promoted=False,
        ok_to_download_for_research=True,
        ok_to_submit=False,
        verdict="negative",
        stop_reasons=[
            "UNIQUENESS (literal all-registry rule): forward 3-px overlap = 1.0000 > 0.70 "
            "against the pinned 17GEMSDOE dense witness (positive on all 5,106,385 allowed "
            "cells); every nonempty candidate fails, so this file is NOT submission-cleared.",
        ],
        organizer_confirmed_score=None,
        weekly_slots_used=0,
        next_step="Do not spend a weekly submission slot. Unblocking requires a separately "
        "authorized revision of the shared duplicate rule plus new buffered holdout evidence "
        "that beats the current holdout bar, then a separate selector decision.",
    )
    RUN_CARD_PATH.write_text(json.dumps(run_card, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {RUN_CARD_PATH}")

    # Sidecar receipt copy next to the TIF
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {RECEIPT_PATH}")

    print("\n===== SUBMISSION STATUS (obvious) =====")
    print(f"OK to DOWNLOAD for research / education : YES  ({TIFF_PATH.name})")
    print(f"OK to SUBMIT to the competition         : NO   -- DO NOT SUBMIT")
    print("Reason: binding literal 17GEMSDOE overlap 1.0000 > 0.70 (DUPLICATE_STOP).")
    print(f"Prepared name ({len(NAME)}/140): {NAME}")
    print(f"Prepared note  ({len(NOTE)}/140): {NOTE}")
    print(f"TIFF SHA-256: {receipt['sha256']}")
    print(f"Verdict: negative (research artifact; no organizer-confirmed score; 0 slots used).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
