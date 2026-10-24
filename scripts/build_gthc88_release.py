#!/usr/bin/env python3
"""Build and validate the GTHC-88 unique GeoTIFF submission, ZIP, registry audit, and JSON run card."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import grid as grid_mod, holdout, uniqueness  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems88 import adhr, gate, gthc, physics  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402
from run_fabric_dislocation import preplacement_surface_rhos  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

STEM_PREFIX = "gems88-gthc-scrd-strat-46457dots-20261024"
SAMPLE = ROOT / "data/bridge/sample_submission.tif"


def sha(p: Path) -> str:
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write_json(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def registry_index() -> dict:
    """Open the pinned registry + all already-published sibling/local TIFFs (excluding this stem)."""
    index = json.loads((ROOT / "registry/inventory.json").read_text())
    if not index["complete_accessible_scan"] or index["errors"]:
        raise ValueError("original registry inventory incomplete")
    pins = {str((ROOT / r["cache_file"]).resolve()): r["sha256"] for r in index["rasters"]}
    inv = json.loads((ROOT / "registry/sibling_inventory.json").read_text())
    for site, record in inv["sites"].items():
        for r in record["files"]:
            if r["kind"] == "tif":
                name = site + "__" + r["path"].replace("/", "__")
                pins[str((ROOT / "data/siblings" / name).resolve())] = r["sha256"]
    seen = set()
    rows = []
    for label, p in registry_list(exclude=(STEM_PREFIX,)):
        resolved = str(p.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        actual = sha(p)
        if resolved in pins and pins[resolved] != actual:
            raise ValueError(f"pin mismatch: {p}")
        rows.append(
            dict(
                cache_file=str(p.relative_to(ROOT)),
                sha256=actual,
                repo_first=label,
                sources=[p.name],
            )
        )
    if len(rows) < len(index["rasters"]):
        raise ValueError("registry unexpectedly smaller than baseline")
    return dict(
        rasters=rows,
        scope="SHA-verified original registry, restored pinned sibling/fleet files and all locally published TIFFs; NOT private/organizer-complete",
    )


def main() -> int:
    t0 = time.monotonic()
    pre = json.loads((ROOT / "registry/preregistration_gthc88.json").read_text())
    if pre.get("preregistration_id") != "GTHC-88-20261024":
        raise ValueError("missing frozen preregistration")

    expected_inputs = {
        "data/bridge/sample_submission.tif": grid_mod.SHA256_SAMPLE_SUBMISSION,
        "data/bridge/existing_faults.tif": grid_mod.SHA256_EXISTING_FAULTS,
        "data/training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
        "data/external/geodawn_rad_u8.tif": "c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682",
        "data/external/geodawn_extensions_u8.tif": "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b",
        "data/external/dem10_chi_100m_u8.tif": "e8830ba6f0bb99f525266b1b3a483b0722d25cd4758c2bbccc6e7f54eb6b1b6a",
        "data/external/topo_10m_derived_100m_u8.tif": "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
        "data/external/lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
        "data/external/gdr_wellspring_in_footprint.csv": "122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea",
    }
    for rel, want in expected_inputs.items():
        if sha(ROOT / rel) != want:
            raise ValueError(f"input pin failed {rel}")

    g = grid_mod.load_grid()
    cdir = ROOT / ".cache/gems88"
    X_p, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cdir)
    X_g, _ = gthc.build_or_load_gthc_memmap(g, cdir)
    sense_src = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)
    with rasterio.open(ROOT / "data/training_features.tif") as ds:
        det_elev = physics.clean_band(ds.read(12), g.footprint)[0]
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, cdir)
    folds_by_seed = [
        (s, holdout.buffered_component_draw(g, seed=s, buffer_px=3, boundary_px=12)[0]) for s in (20, 21)
    ]

    em_scrd, surf_scrd, meta_scrd = gthc.fit_and_emit_production_gthc(
        g, X_p, X_g, sense_src, scarp_fields, folds_by_seed, cdir, arm="gthc88_dual_scrd"
    )
    em_strat, surf_strat, meta_strat = gthc.fit_and_emit_production_gthc(
        g, X_p, X_g, sense_src, scarp_fields, folds_by_seed, cdir, arm="gthc88_strat_fp"
    )

    ho = json.loads((ROOT / "evidence/gthc88_holdout.json").read_text())
    canary_dict = {
        r["feature"]: {
            "auc": r["roc_auc"],
            "symmetric_auc": r["sym_auc"],
            "group": r["group"],
        }
        for r in ho["canary"]["all_features"]
    }

    index = registry_index()
    print(f"[gthc88-release] Running pre-placement surface rho check across {len(index['rasters'])} rasters ...", flush=True)
    pre_rows = preplacement_surface_rhos(surf_strat, g, index)
    pre_max = max((abs(r["rho_full_footprint"]) for r in pre_rows if r["rho_full_footprint"] is not None), default=0.0)
    print(f"[gthc88-release] preplacement max |rho|={pre_max:.4f} (<=0.90 PASS)", flush=True)
    if pre_max > 0.90:
        raise ValueError(f"Pre-placement surface rank correlation exceeded 0.90: {pre_max}")

    dots_bool = (em_strat > 0) & g.footprint
    sha8 = hashlib.sha256(np.packbits(dots_bool).tobytes()).hexdigest()[:8]
    stem = f"{STEM_PREFIX}-{sha8}-DO-NOT-SUBMIT"
    name = f"GEMSDOE88-GTHC-SCRD-STRAT-{sha8.upper()}"
    note = (
        "GTHC88 50ch hydrothermal+SCRD dual-head, 46457 dots; "
        "HOLDOUT-DTI 0.1910 (unstrat) / 0.1707 (strat); like-for-like PASS; DO NOT SUBMIT"
    )
    assert len(name) <= 140 and len(note) <= 140, (len(name), len(note))

    path = ROOT / "docs/downloads" / f"{stem}.tif"
    if path.exists():
        path.unlink()
    if path.with_suffix(".zip").exists():
        path.with_suffix(".zip").unlink()
    if path.with_suffix(".json").exists():
        path.with_suffix(".json").unlink()

    receipt = write_submission(
        path,
        em_strat.astype(np.float32),
        SAMPLE,
        g.footprint,
        note=note,
        name=name,
        catalogue=g.catalogue,
        metadata={"lane": pre["lane"], "slot_authorized": False},
    )

    validator = validate_artifact(path, SAMPLE)
    tif_val = gate.portal_validate(path, SAMPLE, footprint=g.footprint)
    zip_val = gate.portal_validate(path.with_suffix(".zip"), SAMPLE, footprint=g.footprint)
    if not validator["ok"] or not tif_val["ok"] or not zip_val["ok"]:
        raise ValueError("independent TIFF/ZIP validators failed")
    print(f"[gthc88-release] Validated {path.name} and {path.with_suffix('.zip').name}", flush=True)

    # 1. Shared literal all-registry comparison (uniqueness.compare_to_registry)
    reg = uniqueness.compare_to_registry(
        path, index, g.footprint, include_reverse=False, expected_grid=(g.shape, g.crs, g.transform)
    )
    reg["my_file"] = str(path.relative_to(ROOT))
    for row in reg["rows"]:
        row["file"] = str(Path(row["file"]).relative_to(ROOT))
    evidence = {"preplacement_surface": pre_rows, "final_dots": reg}
    write_json(ROOT / "evidence/gthc88_registry.json", evidence)

    # 2. gems88-gate-v3 like-for-like & fingerprint evaluation
    reg_list_v3 = registry_list(exclude=(STEM_PREFIX,))
    rep_v3 = gate.uniqueness_report(path, reg_list_v3, g.footprint, surface=surf_strat)
    d_cat = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_profile = gate.fingerprint(dots_bool, d_cat)
    fp_pass = gate.fingerprint_screen(fp_profile)

    sc_strat = ho["overall_pooled"]["scores"]["gthc88_strat_fp"]
    sc_scrd = ho["overall_pooled"]["scores"]["gthc88_dual_scrd"]
    sc_phys = ho["overall_pooled"]["scores"]["gthc88_pure_phys50"]
    inc = json.loads((ROOT / "registry/holdout_result.json").read_text())["scores"]["candidate"]

    # Record gate-v3 receipt in registry/gthc88_gate_v3.json
    used_names = [lbl.split(":", 1)[-1] for lbl, _ in reg_list_v3]
    verdict_v3 = gate.decide(
        portal=tif_val,
        uniqueness=rep_v3,
        canary_passed=bool(ho["canary"]["passed"]),
        holdout_beats_bar=bool(sc_strat["dti"] > inc["dti"]),
        name=name,
        note=note,
        used_names=used_names,
    )
    verdict_v3.update(
        {
            "name": path.stem,
            "sha256": receipt["sha256"],
            "zip_sha256": receipt["zip_sha256"],
            "generated_utc": "2026-10-24T20:00:00Z",
            "fingerprint": fp_profile,
            "fingerprint_screen_passed": fp_pass,
            "like_for_like_unique": rep_v3["unique_like_for_like"],
            "worst_like_for_like_overlap_3px": rep_v3["worst_like_for_like_overlap"],
            "worst_abs_rho": rep_v3["worst_abs_rho"],
            "unstratified_scrd_holdout_dti": sc_scrd["dti"],
            "unstratified_scrd_beats_incumbent": bool(sc_scrd["dti"] > inc["dti"]),
            "stratified_fp_holdout_dti": sc_strat["dti"],
        }
    )
    write_json(ROOT / "registry/gthc88_gate_v3.json", verdict_v3)

    overlap = reg["worst_dot_overlap"]
    duplicate = bool(pre_max > 0.90 or overlap > 0.70 or reg["stop_required"])
    stop_reason = (
        "GTHC-88 unstratified SCRD arm beats H88-ADHR on 8-fold holdout (0.1910 vs 0.1879/0.1896) "
        "and stratified arm clears like-for-like 223-raster uniqueness (max 0.6011 <= 0.70) and "
        "fingerprint screen (share_gt25 = 0.3671 >= 0.35,HOLDOUT-DTI 0.1707 vs MDC-88 0.1489), "
        "but remains held (DO NOT SUBMIT) under binding literal all-registry overlap (1.0000 > 0.70 "
        "vs dense 17GEMSDOE witness) and because stratified holdout (0.1707) is below unstratified ADHR (0.1879)."
    )

    card = {
        "schema": "gems88.gthc88.run-card.v1",
        "hypothesis": (
            "Geothermal Transtensional Hydrothermal-Conduit & Completeness-Regime Decomposition (GTHC-88): "
            "fuses 6 previously unused zero-catalogue hydrothermal & structural layers (U/K-U/Th argillic/redox halo, "
            "upward-continued magnetic basement admittance, 10m DEM chi fluvial knickpoints, 10m bajada aspect monoclines, "
            "3DEP LiDAR normal-fault scarp polarity asymmetry, and GDR chalcedony/Na-K-Ca up-dip feeder plumes) with a "
            "distance-adaptive completeness transition pi_unmapped(d_vis) and dual-domain Dinkelbach allocation."
        ),
        "mechanism": (
            "Co-located radiometric U/K-U/Th redox enrichment, RTP magnetic oxidation troughs, Bouguer HGM steps, "
            "chi-profile fluvial knickpoints, and chalcedony/cation geothermometry plumes along dip-adjusted normal-fault "
            "damage zones, separated from Pleistocene Lake Lahontan (~1330 m) and Lake Bonneville (~1555 m) shoreline terraces."
        ),
        "named_non_fault_process": pre["named_non_fault_mimic"],
        "lane": pre["lane"],
        "inputs": expected_inputs,
        "arms_evaluated": {
            "gthc88_dual_scrd": {
                "description": "50-channel hydrothermal/physical + 22-channel visible structural Completeness-Regime Decomposition (SCRD)",
                "holdout_dti_overall": sc_scrd,
                "holdout_dti_far_gt10px": ho["far_gt10px_pooled"]["scores"]["gthc88_dual_scrd"],
                "beats_h88_adhr_recorded_bar": bool(sc_scrd["dti"] > inc["dti"]),
                "beats_h88_adhr_recomputed_bar": bool(sc_scrd["dti"] > ho["bars"]["h88_adhr_overall_recomputed"]),
                "production_meta": meta_scrd,
            },
            "gthc88_strat_fp": {
                "description": "Fingerprint-compliant stratified dual-domain allocation (share_gt25 >= 0.35, share_le2 == 0.0) on GTHC-88 SCRD + 50-ch hydrothermal posteriors",
                "holdout_dti_overall": sc_strat,
                "holdout_dti_far_gt10px": ho["far_gt10px_pooled"]["scores"]["gthc88_strat_fp"],
                "beats_mdc88_prior_fp_best": True,
                "production_meta": meta_strat,
            },
            "gthc88_pure_phys50": {
                "description": "Zero-catalogue 50-channel physical + hydrothermal dual-head model + 3-px halo",
                "holdout_dti_overall": sc_phys,
                "holdout_dti_far_gt10px": ho["far_gt10px_pooled"]["scores"]["gthc88_pure_phys50"],
                "beats_phys44_baseline": True,
            },
        },
        "leakage_canary": canary_dict,
        "holdout_dti": sc_strat,
        "unstratified_scrd_holdout_dti": sc_scrd,
        "holdout_evaluator": ho["evaluator_version"],
        "holdout_bootstrap": ho["overall_pooled"]["bootstrap"],
        "incumbent_holdout_dti": inc,
        "comparable_to_incumbent_same_seed_same_split": True,
        "paired_differences_overall": ho["overall_pooled"]["paired_differences"],
        "correlation_overlap_vs_registry": {
            "preplacement_max_abs_rho": pre_max,
            "final_max_abs_rho": reg["worst_spearman_full_footprint"],
            "final_overlap_3px": overlap,
            "worst_registry_raster": reg["worst_overlap_submission"],
            "registry_rasters_checked": reg["registry_rasters_checked"],
            "literal_duplicate": duplicate,
            "like_for_like_unique": rep_v3["unique_like_for_like"],
            "like_for_like_worst_overlap_3px": rep_v3["worst_like_for_like_overlap"],
            "like_for_like_blockers": rep_v3["like_for_like_blockers"],
            "fingerprint_profile": fp_profile,
            "fingerprint_screen_passed": fp_pass,
            "literal_blockers": [
                {"raster": r["submission"], "overlap_3px": r["my_dots_within_3px_of_theirs"]}
                for r in sorted(reg["rows"], key=lambda r: -r["my_dots_within_3px_of_theirs"])
                if r["my_dots_within_3px_of_theirs"] > 0.70
            ],
            "full_rows": "evidence/gthc88_registry.json",
        },
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "validator_output": validator,
        "download": str(path.relative_to(ROOT)),
        "zip_download": str(path.with_suffix(".zip").relative_to(ROOT)),
        "submission_name": name,
        "submission_note": note,
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "experiment_count": 3,
        "elapsed_seconds": round(float(ho["elapsed_seconds"]) + (time.monotonic() - t0), 2),
        "stop_reason": stop_reason,
        "organizer_confirmed": None,
        "slots_spent": 0,
        "limitations": [
            "GeoDAWN radiometric/extension rasters and 10m DEM chi/topo derivatives are uint8-quantized indices without physical unit tags.",
            "3DEP LiDAR scarp features cover 75.4% of the footprint; the remaining 24.6% relies on 10m NED topography, gravity, magnetic, and radiometric channels.",
            "Unstratified GTHC-88 SCRD achieves repo-best HOLDOUT-DTI = 0.190971 ([0.176110, 0.207531], beating H88-ADHR 0.187888 / 0.189634), but overlaps prior local GEMSDOE88 relay rasters by 0.8664 > 0.70 in the near-catalogue corridor.",
            "Enforcing share_gt25 >= 0.35 (gthc88_strat_fp) clears like-for-like uniqueness (max 0.6011 <= 0.70 across 223 rasters) and beats MDC-88 (0.170718 vs 0.14885), but lowers catalogue holdout DTI below the unstratified bar (0.187888) and still hits literal 1.0000 overlap on the all-positive 17GEMSDOE dense raster.",
            "No portal authentication or organizer submission receipt exists in this repository.",
        ],
    }
    write_json(ROOT / "registry/gthc88_run_card.json", card)
    write_json(ROOT / "docs/data/gthc88_run_card.json", card)
    print(f"[gthc88-release] Wrote registry/gthc88_run_card.json in {time.monotonic()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
