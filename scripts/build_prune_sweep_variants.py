#!/usr/bin/env python3
"""Build a fixed-count, exact-marginal PRUNE dose sweep from byte-exact R0.

This is a global catalogue-distance treatment only: each output removes R0 dots
within its stated collar and fills the same count from the original H19-5 support
outside that collar. Refill selection uses the shared exact expected-DTI solver
and one fixed, label-free four-line physical field. No region-specific selection,
leaderboard access, submission, or score tuning is performed.

Run from the repository root after the manifest-pinned inputs have been restored:
    .venv/bin/python scripts/build_prune_sweep_variants.py
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from scripts import build_prune_variants as bpv  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
AXIS = "PRUNE"
DATE = "20261023"
N_DOTS = 37_654
NO_EVIDENCE_BAND = 0.01
MANIFEST = ROOT / "registry" / "data_manifest.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS_PATH = ROOT / "ledger" / "mechanism_cards.json"
RELEASES = ROOT / "releases"
REPORT_PATH = ROOT / "evidence" / "prune_sweep_report.json"
PREREG_PATH = ROOT / "registry" / "prune_sweep_preregistration.json"

# Values are thresholds in pixels (100 m/pixel). They were chosen to resolve
# the already-built PRUNE p3px/p4px bracket without reusing either pair. Exact
# expected-DTI projections interpolate/extrapolate the existing MODEL anchors;
# they are not organizer scores and no live result was used to set them.
SPECS: tuple[dict[str, Any], ...] = (
    {
        "value": "p3.2px",
        "threshold_px": 3.2,
        "threshold_m": 320.0,
        "prediction": 0.002,
        "prediction_range": [-0.010, 0.012],
        "hypothesis": (
            "Extending R0's exclusion from 300 m to 320 m removes a narrow fringe of "
            "catalogue-adjacent potential-field side-lobes while the fixed-count refill "
            "retains detections on independently corroborated H19-5 line support."
        ),
    },
    {
        "value": "p3.7px",
        "threshold_px": 3.7,
        "threshold_m": 370.0,
        "prediction": -0.005,
        "prediction_range": [-0.020, 0.008],
        "hypothesis": (
            "Extending the collar to 370 m may begin to remove genuine secondary splays "
            "that sit just beyond the kernel radius; exact marginal refill is predicted "
            "to recover only part of that lost credit."
        ),
    },
    {
        "value": "p4.3px",
        "threshold_px": 4.3,
        "threshold_m": 430.0,
        "prediction": -0.013,
        "prediction_range": [-0.030, 0.006],
        "hypothesis": (
            "A 430 m collar, slightly wider than the reported 400 m GeoDAWN line spacing, "
            "will remove some real range-front step-fault/relay splays, so this upper "
            "bracket is expected to lose live DTI at fixed count."
        ),
    },
)

FIELD_SOURCES = (
    "label-free four-line physical field from scripts/build_prune_variants.py: "
    "surface scarp, subsurface potential-field, strain/seismic, and hydrothermal lines; "
    "all single-channel canaries must be <= 0.90 before the field is used"
)
RANKING_BASIS = (
    "Exact iterative marginal expected-DTI gain via vendor/gems57/metric.py and "
    "scripts/build_prune_variants.py::select_exact_marginal_dti_add; candidate pool is "
    "the original H19-5 binary support outside the threshold; fixed label-free physical "
    "field across all variants; no isolated-pixel shortcut or random tie score"
)
REFERENCES = [
    {
        "url": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
        "claim": "The organizer describes pixel-exact masking of known USGS/INGENIOUS pixels; pixels adjacent to known traces are scored normally.",
    },
    {
        "url": "https://community.drivendata.org/t/where-do-you-draw-the-line/11536",
        "claim": "The organizer describes new-fault truth as including new geometry and allows it to occur within 300 m of known traces; this is the key collar-loss confounder.",
    },
    {
        "url": "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7",
        "claim": "The provided GeoDAWN resolution note reports 400 m line spacing in Area 2; used only as a positional-uncertainty context, not as a target label.",
    },
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_ledger() -> tuple[list[dict[str, str]], list[str]]:
    if not LEDGER.is_file():
        raise FileNotFoundError(f"Required ledger is missing: {LEDGER}")
    with LEDGER.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    required = {
        "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256",
        "sha256_zeros", "status", "predicted_change", "predicted_range",
        "ranking_basis", "receipt_score", "receipt_date", "description", "recommendation",
    }
    if not required.issubset(fields):
        raise ValueError(f"Unexpected ledger schema; missing {sorted(required - set(fields))}")
    return rows, fields


def preflight_pairs(rows: list[dict[str, str]]) -> None:
    values = [spec["value"] for spec in SPECS]
    if len(values) != len(set(values)):
        raise ValueError("The PRUNE sweep contains repeated values")
    pairs = {(row.get("parent"), row.get("axis"), row.get("value")) for row in rows}
    collisions = [(PARENT_ID, AXIS, value) for value in values if (PARENT_ID, AXIS, value) in pairs]
    if collisions:
        raise ValueError(f"Repeated (parent, axis, value) pair(s) in ledger: {collisions}")
    for spec in SPECS:
        prefix = f"{PARENT_ID}-{AXIS}{spec['value']}-{DATE}"
        if any(RELEASES.glob(f"{prefix}-*")):
            raise FileExistsError(f"Artifacts for this value already exist: {prefix}-*")


def ledger_hashes(rows: list[dict[str, str]]) -> set[str]:
    result = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}
    for row in rows:
        result.update(
            value for value in (row.get("sha256"), row.get("sha256_zeros")) if value
        )
    return result


def preregistration_payload(parent: dict[str, Any], manifest_sha: str) -> dict[str, Any]:
    anchors = {}
    for row in load_ledger()[0]:
        if row.get("parent") == PARENT_ID and row.get("axis") == AXIS and row.get("value") in {"p3px", "p4px"}:
            anchors[row["value"]] = {
                "predicted_change": row.get("predicted_change"),
                "predicted_range": row.get("predicted_range"),
                "evidence_class": "MODEL (prior registry projection, not a live score)",
            }
    return {
        "schema": "gems88.prune-dose-preregistration.v1",
        "created_utc": utc_now(),
        "parent": {
            "id": PARENT_ID,
            "n_dots": int(parent["r0"].sum()),
            "zeros_sha256": parent["rebuilt_zeros_sha256"],
            "nan_sha256": parent["rebuilt_nan_sha256"],
            "evidence_class": "REBUILT parent; historical 0.2778 remains CLAIM",
        },
        "axis": AXIS,
        "axis_selection": (
            "The human instructed the agent to select its own axis. PRUNE was selected "
            "because R0 has 2,171 dots at 2 < d_catalogue <= 3 px; a non-PRUNE child "
            "cannot satisfy the brief's >=3 px hard constraint without adding a second, "
            "confounded PRUNE edit. PRUNE is the explicit exception."
        ),
        "manifest_sha256": manifest_sha,
        "git_sha": git_value("rev-parse", "HEAD"),
        "origin_main_sha_checked_before_build": git_value("rev-parse", "origin/main"),
        "prior_model_anchors": anchors,
        "predicted_no_evidence_band": NO_EVIDENCE_BAND,
        "predictions_are": "MODEL, not scores; any live absolute delta < 0.01 is no evidence",
        "treatment": (
            "For each value, remove every R0 dot at d_catalogue <= threshold_px; hold "
            "N=37,654; add the same number from the original H19-5 support at "
            "d_catalogue > threshold_px using exact greedy expected-DTI marginal gain. "
            "All other settings and the fixed physical-field ranking recipe are unchanged."
        ),
        "refill_ranking_basis": RANKING_BASIS,
        "physical_field": FIELD_SOURCES,
        "variants": [
            {
                "value": spec["value"],
                "threshold_px": spec["threshold_px"],
                "threshold_m": spec["threshold_m"],
                "predicted_change": f"MODEL:{spec['prediction']:+.3f}",
                "predicted_range": spec["prediction_range"],
                "hypothesis": spec["hypothesis"],
            }
            for spec in SPECS
        ],
        "report_only_not_gates": [
            "catalogue hide-and-recover PROXY with withheld-positive count and 95% CI",
            "single-feature leakage canary",
            "blind SGMC control",
            "10 km and 12 km dot-density CV",
        ],
        "no_submission": True,
    }


def prune_at_threshold(
    parent: np.ndarray,
    source_support: np.ndarray,
    d_catalogue: np.ndarray,
    expected_fault_weight: np.ndarray,
    threshold_px: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Remove the collar, then exact-marginal refill to the unchanged parent count."""
    if threshold_px <= 0:
        raise ValueError("PRUNE threshold must be positive")
    survivors = np.asarray(parent, dtype=bool) & (d_catalogue > threshold_px)
    removed_n = int(np.asarray(parent, dtype=bool).sum() - survivors.sum())
    candidate_pool = (
        np.asarray(source_support, dtype=bool)
        & ~survivors
        & (d_catalogue > threshold_px)
    )
    if int(candidate_pool.sum()) < removed_n:
        raise ValueError(
            f"Only {int(candidate_pool.sum())} legal refill cells for {removed_n} removals "
            f"at threshold {threshold_px} px"
        )
    candidate = bpv.select_exact_marginal_dti_add(
        base_mask=survivors,
        cand_mask=candidate_pool,
        w=expected_fault_weight,
        n_add=removed_n,
    )
    if int(candidate.sum()) != int(parent.sum()):
        raise AssertionError("Fixed-mass PRUNE invariant failed")
    if np.any(candidate & (d_catalogue <= threshold_px)):
        raise AssertionError("Output contains a dot inside its PRUNE collar")
    added_n = int((candidate & ~parent).sum())
    actual_removed_n = int((parent & ~candidate).sum())
    if added_n != removed_n or actual_removed_n != removed_n:
        raise AssertionError(
            f"Parent difference not a one-for-one relocation: added={added_n}, "
            f"removed={actual_removed_n}, expected={removed_n}"
        )
    pct_moved = 100.0 * actual_removed_n / int(parent.sum())
    if not 1.0 <= pct_moved <= 50.0:
        raise ValueError(f"Changed fraction {pct_moved:.5f}% is outside 1–50%")
    return candidate, {
        "threshold_px": float(threshold_px),
        "threshold_m": float(threshold_px * 100.0),
        "n_removed": actual_removed_n,
        "n_added": added_n,
        "n_refill_candidates": int(candidate_pool.sum()),
        "pct_changed_moved": pct_moved,
        "pct_changed_symmetric_difference": 200.0 * actual_removed_n / int(parent.sum()),
        "min_catalogue_distance_px": float(d_catalogue[candidate].min()),
    }


def nearest_neighbour_stats(mask: np.ndarray) -> dict[str, float]:
    points = np.argwhere(mask)
    if len(points) < 2:
        raise ValueError("Nearest-neighbour statistics need at least two dots")
    distances = cKDTree(points).query(points, k=2)[0][:, 1]
    return {
        "min_px": float(distances.min()),
        "mean_px": float(distances.mean()),
        "p05_px": float(np.percentile(distances, 5)),
        "p95_px": float(np.percentile(distances, 95)),
    }


def build_card(spec: dict[str, Any], stats: dict[str, Any], rec: dict[str, Any], nn: dict[str, Any]) -> dict[str, Any]:
    threshold = float(spec["threshold_px"])
    point = float(spec["prediction"])
    lo, hi = map(float, spec["prediction_range"])
    return {
        "axis": AXIS,
        "value": spec["value"],
        "threshold_px": threshold,
        "threshold_m": float(spec["threshold_m"]),
        "hypothesis": spec["hypothesis"],
        "mechanism": (
            "The organizer says known pixels are masked pixel-exactly, while adjacent "
            "pixels are scored normally. A constant N=37,654 isolates relocation: remove "
            f"{stats['n_removed']:,} parent dots through {threshold*100:.0f} m and refill "
            "the same count on the original H19-5 support strictly outside the collar. "
            "Each addition is selected by the shared metric's exact iterative expected-DTI "
            "marginal gain on one fixed, label-free four-line physical field (surface "
            "scarp, potential-field edge, strain/seismic, hydrothermal), not by an "
            "isolated-truth shortcut. No minimum-spacing optimization is added; nearest-"
            "neighbour change is disclosed as a possible confounder."
        ),
        "non_fault_mimic": (
            "Long-wavelength magnetic/gravity side-lobes, pediment and alluvial-fan "
            "margins, and wave-cut shoreline breaks can parallel range-front structures "
            "without new fault slip. Conversely, a true antithetic splay or relay can lie "
            "inside the removed collar; the organizer explicitly allows new-fault truth "
            "within 300 m of known traces."
        ),
        "predicted_sign_size": (
            f"MODEL predicted live delta {point:+.3f} vs R0, plausible range "
            f"[{lo:+.3f},{hi:+.3f}]. Projection interpolates/extrapolates the prior "
            "PRUNE p3px (+0.005 MODEL) and p4px (-0.009 MODEL) anchors; it is not a "
            "receipt or PROXY. Treat |live delta| < 0.01 as no evidence on public chunks."
        ),
        "falsifier": (
            "A same-entity live receipt >= +0.01 vs R0 supports removal of side-lobe "
            "false positives at this collar. A receipt <= -0.01 falsifies that direction "
            "and indicates net fault truth was removed. A |delta| < 0.01 is inconclusive; "
            "compare the registered 320 m -> 370 m -> 430 m dose sequence only after "
            "receipts are supplied."
        ),
        "fixed_count": N_DOTS,
        "parent_diff": rec["parent_diff"],
        "ranking_basis": RANKING_BASIS,
        "four_line_field": FIELD_SOURCES,
        "nearest_neighbour_stats": nn,
        "spacing_confounded_not_optimized": True,
        "report_only_not_gates": [
            "hide-and-recover catalogue PROXY",
            "single-feature leakage canary",
            "blind SGMC control",
        ],
        "references": REFERENCES,
        "submission_name": rec["id"],
        "form_note": rec["form_note"],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    # The first two gates are fail-closed. Do not build a candidate from an
    # unpinned input or an approximate parent.
    rows, ledger_fields = load_ledger()
    preflight_pairs(rows)
    verified = bpv.verify_manifest(MANIFEST)
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot = lineage["foot"]
    catalogue = lineage["catalogue"]
    d_catalogue = lineage["d_cat"]
    parent = lineage["r0"]
    source_support = lineage["h19_5"]
    if int(parent.sum()) != N_DOTS:
        raise RuntimeError(f"Unexpected R0 dot count: {int(parent.sum())}")
    if lineage["rebuilt_zeros_sha256"] != bpv.PARENT_SHA_ZEROS or lineage["rebuilt_nan_sha256"] != bpv.PARENT_SHA_NAN:
        raise RuntimeError("STOP: R0 rebuild does not byte-match the pinned parent")
    if np.any(parent & catalogue) or int((d_catalogue[parent] <= 2.0).sum()) != 0:
        raise RuntimeError("STOP: R0 failed its recorded zero-catalogue/2 px geometry")

    # Freeze the protocol and predictions before running canaries, holdout, or SGMC.
    manifest_sha = sha256_path(MANIFEST)
    parent_summary = {
        "r0": parent,
        "rebuilt_zeros_sha256": lineage["rebuilt_zeros_sha256"],
        "rebuilt_nan_sha256": lineage["rebuilt_nan_sha256"],
    }
    prereg = preregistration_payload(parent_summary, manifest_sha)
    write_json(PREREG_PATH, prereg)

    # One fixed field/ranking recipe is shared by all three threshold arms.
    expected_fault_weight, canaries = bpv.build_physical_field_and_canaries(
        verified=verified,
        foot=foot,
        catalogue=catalogue,
        h19_5=source_support,
    )
    if not canaries or max(canaries.values()) > 0.90:
        raise RuntimeError(f"LEAKAGE CANARY FAILURE: {canaries}")

    candidates: dict[str, np.ndarray] = {}
    build_stats: dict[str, dict[str, Any]] = {}
    for spec in SPECS:
        value = str(spec["value"])
        key = f"{PARENT_ID}-{AXIS}{value}"
        candidate, stats = prune_at_threshold(
            parent=parent,
            source_support=source_support,
            d_catalogue=d_catalogue,
            expected_fault_weight=expected_fault_weight,
            threshold_px=float(spec["threshold_px"]),
        )
        if int((candidate & catalogue).sum()) != 0:
            raise RuntimeError(f"Non-zero catalogue mass in {value}")
        if stats["min_catalogue_distance_px"] < 3.0:
            raise RuntimeError(f"Non-PRUNE collar floor failed for {value}")
        candidates[key] = candidate
        build_stats[value] = stats

    # REPORT-ONLY diagnostics are run globally and are never used to choose dots.
    arms = {PARENT_ID: parent, **candidates}
    diagnostics = bpv.evaluate_report_only_instruments(
        arms=arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )
    parent_nn = nearest_neighbour_stats(parent)

    existing_shas = ledger_hashes(rows)
    new_rows: list[dict[str, str]] = []
    new_cards: dict[str, dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    for spec in SPECS:
        value = str(spec["value"])
        key = f"{PARENT_ID}-{AXIS}{value}"
        candidate = candidates[key]
        stats = build_stats[value]
        nn = nearest_neighbour_stats(candidate)
        note = (
            f"R0 {PARENT_ID}; PRUNE <= {spec['threshold_px']:g}px "
            f"({spec['threshold_m']:g}m), fixed N=37,654, exact DTI refill; "
            f"pred {spec['prediction']:+.3f} MODEL"
        )
        rec = bpv.write_and_verify_variant(
            mask=candidate,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=parent,
            axis=AXIS,
            value=value,
            note_template=note,
            existing_shas=existing_shas,
            parent_id=PARENT_ID,
            parent_sha_zeros=bpv.PARENT_SHA_ZEROS,
            parent_sha_nan=bpv.PARENT_SHA_NAN,
            date=DATE,
            min_catalogue_px=float(spec["threshold_px"]),
        )
        existing_shas.update((rec["sha256"], rec["sha256_zeros"]))
        diag = diagnostics[key]
        rec.update(
            {
                "evidence_class": "BUILT candidate; MODEL projection only; no receipt",
                "manifest": {
                    "path": "registry/data_manifest.json",
                    "sha256": manifest_sha,
                    "verified_input_count": len(verified),
                    "all_manifest_inputs_verified": True,
                },
                "threshold_px": stats["threshold_px"],
                "threshold_m": stats["threshold_m"],
                "removed_parent_dots": stats["n_removed"],
                "added_dots": stats["n_added"],
                "refill_candidate_pool_size": stats["n_refill_candidates"],
                "pct_changed_exact": stats["pct_changed_moved"],
                "pct_changed_symmetric_difference": stats["pct_changed_symmetric_difference"],
                "ranking_basis": RANKING_BASIS,
                "four_line_field": FIELD_SOURCES,
                "build_script_sha256": sha256_path(Path(__file__).resolve()),
                "git_sha": git_value("rev-parse", "HEAD"),
                "origin_main_sha_checked_before_build": git_value("rev-parse", "origin/main"),
                "nearest_neighbour_stats": {
                    "R0": parent_nn,
                    "candidate": nn,
                    "interpretation": "REPORT ONLY; exact-marginal refill has no extra spacing constraint",
                },
                "report_only_diagnostics": diag,
                "r0_reference_diagnostics": diagnostics[PARENT_ID],
                "leakage_canaries": {
                    "passed": all(value_auc <= 0.90 for value_auc in canaries.values()),
                    "max_single_feature_symmetric_auc": max(canaries.values()),
                    "channels": canaries,
                    "report_only": True,
                },
                "model_prediction": {
                    "evidence_class": "MODEL",
                    "delta_vs_r0": float(spec["prediction"]),
                    "range": list(spec["prediction_range"]),
                    "no_evidence_if_abs_live_delta_below": NO_EVIDENCE_BAND,
                },
                "not_submitted": True,
            }
        )
        write_json(RELEASES / f"{rec['id']}.json", rec)
        receipts.append(rec)
        new_cards[rec["id"]] = build_card(spec, stats, rec, nn)

        new_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": AXIS,
                "value": value,
                "n_dots": str(N_DOTS),
                "pct_changed": f"{stats['pct_changed_moved']:.5f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{spec['prediction']:+.3f}",
                "predicted_range": f"[{spec['prediction_range'][0]:+.3f},{spec['prediction_range'][1]:+.3f}]",
                "ranking_basis": RANKING_BASIS,
                "receipt_score": "",
                "receipt_date": "",
                "description": (
                    f"PRUNE d_catalogue<={spec['threshold_px']:g}px ({spec['threshold_m']:g}m); "
                    f"remove {stats['n_removed']}; exact-marginal H19-5 refill, fixed {N_DOTS:,}."
                ),
                "recommendation": (
                    "HOLD pending human slot choice and live receipt; MODEL magnitude is below "
                    "the brief's 0.01 no-evidence threshold. No score or submission recorded."
                ),
            }
        )

    # Commit the ledger/card updates only after all three variants passed their
    # writer's independent on-disk checks. Preserve historical rows verbatim.
    old_pairs = {(r.get("parent"), r.get("axis"), r.get("value")) for r in rows}
    old_ids = {r.get("id") for r in rows}
    old_hashes = ledger_hashes(rows)
    for new in new_rows:
        pair = (new["parent"], new["axis"], new["value"])
        if new["id"] in old_ids or pair in old_pairs:
            raise RuntimeError(f"Ledger duplicate detected after build: {new['id']} / {pair}")
        if new["sha256"] in old_hashes or new["sha256_zeros"] in old_hashes:
            raise RuntimeError(f"Ledger SHA duplicate detected after build: {new['id']}")
        old_pairs.add(pair)
        old_ids.add(new["id"])
        old_hashes.update((new["sha256"], new["sha256_zeros"]))

    temp_ledger = LEDGER.with_suffix(".csv.tmp")
    with temp_ledger.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=ledger_fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in [*rows, *new_rows]:
            writer.writerow({field: row.get(field, "") for field in ledger_fields})
    os.replace(temp_ledger, LEDGER)

    current_cards = json.loads(CARDS_PATH.read_text(encoding="utf-8")) if CARDS_PATH.is_file() else {}
    overlap = set(current_cards) & set(new_cards)
    if overlap:
        raise RuntimeError(f"Mechanism card key collision: {sorted(overlap)}")
    current_cards.update(new_cards)
    write_json(CARDS_PATH, current_cards)

    parent_diff = {
        "n_parent": N_DOTS,
        "n_candidate": N_DOTS,
        "n_common": [int((candidate & parent).sum()) for candidate in candidates.values()],
        "variants": {
            spec["value"]: {
                "n_removed": build_stats[spec["value"]]["n_removed"],
                "n_added": build_stats[spec["value"]]["n_added"],
                "pct_changed_moved": build_stats[spec["value"]]["pct_changed_moved"],
                "pct_changed_symmetric_difference": build_stats[spec["value"]]["pct_changed_symmetric_difference"],
                "min_catalogue_distance_px": build_stats[spec["value"]]["min_catalogue_distance_px"],
                "nearest_neighbour_stats": nearest_neighbour_stats(candidates[f"{PARENT_ID}-{AXIS}{spec['value']}"]),
            }
            for spec in SPECS
        },
    }
    report = {
        "schema": "gems88.prune-dose-sweep-report.v1",
        "created_utc": utc_now(),
        "axis": AXIS,
        "parent": {
            "id": PARENT_ID,
            "n_dots": N_DOTS,
            "rebuilt_zeros_sha256": lineage["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lineage["rebuilt_nan_sha256"],
            "evidence_class": "REBUILT; historical live 0.2778 is CLAIM",
        },
        "git_sha": git_value("rev-parse", "HEAD"),
        "build_script_sha256": sha256_path(Path(__file__).resolve()),
        "manifest": {
            "path": "registry/data_manifest.json",
            "sha256": manifest_sha,
            "verified_input_count": len(verified),
            "all_manifest_inputs_verified": True,
        },
        "leakage_canaries": {
            "passed": all(value_auc <= 0.90 for value_auc in canaries.values()),
            "max_single_feature_symmetric_auc": max(canaries.values()),
            "channels": canaries,
            "report_only": True,
        },
        "parent_diff": parent_diff,
        "report_only_diagnostics": diagnostics,
        "variants": receipts,
        "predictions_are": "MODEL, not scores; no receipt was supplied or submitted",
        "live_change_under_0.01": "no evidence on public chunks per brief",
        "slots_used": 0,
        "submitted": False,
    }
    write_json(REPORT_PATH, report)

    print(f"R0 exact SHA: zeros={lineage['rebuilt_zeros_sha256']} nan={lineage['rebuilt_nan_sha256']}")
    print(f"Manifest verified: {len(verified)} inputs; leakage canaries max={max(canaries.values()):.5f}")
    for rec in receipts:
        d = rec["report_only_diagnostics"]
        hp = d["holdout_proxy"]
        sgmc = d["sgmc_control"]
        diff = rec["parent_diff"]
        print(
            f"{rec['id']} n={rec['n_dots']:,} moved={diff['pct_changed_moved']:.5f}% "
            f"removed={diff['n_removed']} added={diff['n_added']} "
            f"min_dcat={diff['min_dist_catalogue_px']:.4f}px "
            f"MODEL={rec['model_prediction']['delta_vs_r0']:+.3f} "
            f"PROXY-holdout={hp['dti']:.6f} n={hp['withheld_positives']} CI={hp['ci95']} "
            f"SGMC-PROXY={sgmc['dti']:.6f}"
        )
        print(f"  primary={rec['file_nan']} SHA256={rec['sha256']}")
        print(f"  fallback={rec['file_zeros']} SHA256={rec['sha256_zeros']}")
        print(f"  note ({rec['form_note_chars']}/140): {rec['form_note']}")
    print(f"REPORT: {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
