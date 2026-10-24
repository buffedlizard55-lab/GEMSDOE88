#!/usr/bin/env python3
"""AXIS=PRUNE, spacing-lock dose ladder around the ledgered `p3space35` arm.

Session choice (agent-chosen, brief v2 §5)
------------------------------------------
Every non-``PRUNE`` child of R0 inherits R0's 2,171 dots at
``2 < d_catalogue <= 3 px`` and therefore breaks the brief's literal ``>= 3 px``
rule (IR-88-47), and the ledger has already closed ``MASS``, ``CONCENTRATION``,
``SNAP``, ``RELIEF``, ``SPACING`` and ``TRACKB`` as slot axes on this lineage.
``PRUNE`` is therefore the only axis this session can edit without adding a
second, implicit edit — and within ``PRUNE`` the one live lever the ledger
reports is the *spacing-locked refill* (``p3space35`` ``+0.0050`` and
``p4space35`` ``+0.0064`` on the blind off-catalogue ``SGMC`` control, against
``p3norefill`` ``-0.0024`` and the densifying ``R1`` ``+0.0000``).

The three arms below hold everything else fixed (same parent, same 3 px collar,
same 2,171 donors, same count 37,654, same H19-5/H19-4/H16-1 refill pool, same
exact-marginal expected-DTI ranking on the same label-free four-line field) and
change **only the spacing lock** plus one **ordering control**:

``p3space28``      lock 2.8 px — dose down (sub-kernel: neighbours share credit). **WITHDRAWN at merge:**
                   the concurrent PR #51 independently emitted byte-identical bytes for this
                   ``(parent, axis, value)`` pair, so the merged row is kept and this script's
                   arm is retained only as the replicate (IR-88-55, cf. IR-88-53).
``p3space45``      lock 4.5 px — dose up (fully independent 3 px kernel support)
``p3space35rand``  lock 3.5 px, seeded **random** refill order — the ranking
                   control that separates "geometry pays" from "the four-line
                   field pays", at the ledger's own dose.

No competition page, leaderboard, submission service or credential is touched.
Predictions are frozen in ``registry/prune_spacing_dose_preregistration.json``
before any report-only instrument runs.

Run from the repository root after the manifest-pinned inputs are restored::

    .venv/bin/python scripts/build_prune_spacing_dose_variants.py
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from scripts import build_prune_variants as bpv  # noqa: E402
from scripts import build_prune_spaced_variants as bsv  # noqa: E402
from scripts import validate_variant  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
AXIS = "PRUNE"
DATE = "20261024"
N_DOTS = 37_654
NO_EVIDENCE_BAND = 0.01
SEED = 20261024
# Values whose (parent, axis, value) pair or bytes were claimed by a concurrently merged session.
WITHDRAWN_VALUES = {"p3space28"}
MANIFEST = ROOT / "registry" / "data_manifest.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
RELEASES = ROOT / "releases"
REPORT = ROOT / "evidence" / "prune_spacing_dose_report.json"
PREREG = ROOT / "registry" / "prune_spacing_dose_preregistration.json"
VALIDATION = ROOT / "registry" / "prune_spacing_dose_validation.json"

RANK_BASIS = (
    "Exact iterative marginal expected-DTI gain (vendor/gems57/metric.py) among only those "
    "refill cells that keep a >= spacing_px separation from every surviving R0 dot and from "
    "every already-chosen refill; candidate pool = union of the H19-5, H19-4 and H16-1 ridge "
    "supports outside the collar; one fixed label-free four-line physical field for all arms"
)
RAND_BASIS = (
    "No ranking at all: a seeded (20261024) uniformly random order over the same spacing-legal "
    "refill pool, with the same blocking rule and the same feasibility lookahead, so the count "
    "and the spacing statistics are matched to p3space35 and only the ordering rule differs"
)
FIELD_SOURCES = (
    "label-free four-line physical field from scripts/build_prune_variants.py: surface scarp, "
    "subsurface potential-field, strain/seismic and hydrothermal lines"
)

SPECS: tuple[dict[str, Any], ...] = (
    {
        "value": "p3space28",
        "spacing_px": 2.8,
        "order": "marginal_dti",
        "prediction": 0.002,
        "prediction_range": [-0.006, 0.010],
        "hypothesis": (
            "A 2.8 px lock is just under the 3 px kernel radius, so neighbouring refills still "
            "share kernel support: the arm should recover only part of the spacing-locked gain "
            "and land between the densifying R1 (blind +0.0000) and p3space35 (blind +0.0050)."
        ),
        "blind_prediction": 0.0005,
    },
    {
        "value": "p3space45",
        "spacing_px": 4.5,
        "order": "marginal_dti",
        "prediction": 0.007,
        "prediction_range": [-0.004, 0.018],
        "hypothesis": (
            "At a 4.5 px lock no two refill dots share the triangular R=3 px kernel, so each one "
            "is the nearest dot to a distinct strip of ground and pays full line credit instead "
            "of the 0.04-0.07 TP/dot a densified refill forfeits; it should therefore beat "
            "p3space35 (blind +0.0050) if the effect is monotone in separation."
        ),
        "blind_prediction": 0.0085,
    },
    {
        "value": "p3space35rand",
        "spacing_px": 3.5,
        "order": "random",
        "prediction": 0.004,
        "prediction_range": [-0.006, 0.014],
        "hypothesis": (
            "The spacing-locked gain is geometric, not field-driven: if the 3.5 px lock already "
            "sets the geometry, a random refill order should reproduce most of p3space35's blind "
            "margin and the four-line field contributes little (the MASS random-donor control "
            "bounded the ranking effect at +-0.0018)."
        ),
        "blind_prediction": 0.0040,
    },
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_value(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def spaced_random_add(
    base_mask: np.ndarray,
    cand_mask: np.ndarray,
    n_add: int,
    spacing_px: float,
    seed: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Seeded random-order refill under the same hard minimum-separation lock.

    Geometry is identical to ``bsv.spaced_marginal_add`` (same pool pre-filter,
    same blocking radius, same feasibility lookahead that skips a pick which
    would strand the fill); the only difference is that the pick order is
    uniform random instead of the exact-marginal-DTI ranking.
    """
    state = np.asarray(base_mask, dtype=bool).copy()
    H, W = state.shape
    by, bx = np.nonzero(state)
    cy, cx = np.nonzero(np.asarray(cand_mask, dtype=bool) & ~state)
    if len(cy) == 0:
        raise ValueError("Empty refill pool")
    d_parent = cKDTree(np.column_stack([by, bx]).astype(np.float64)).query(
        np.column_stack([cy, cx]).astype(np.float64), k=1
    )[0]
    keep = d_parent >= spacing_px
    if int(keep.sum()) < n_add:
        raise ValueError(
            f"Only {int(keep.sum())} legal refill cells at >= {spacing_px} px from the survivors, "
            f"but {n_add} are required"
        )
    cy, cx = cy[keep], cx[keep]
    n_pool = len(cy)
    rng = np.random.default_rng(seed)
    priority = rng.permutation(n_pool)
    order = np.argsort(priority, kind="stable")

    cand_id_grid = np.full((H, W), -1, dtype=np.int32)
    cand_id_grid[cy, cx] = np.arange(n_pool, dtype=np.int32)
    avail = np.ones(n_pool, dtype=bool)
    lock = int(np.ceil(spacing_px))
    chosen: list[int] = []

    for cand in order:
        if not avail[cand]:
            continue
        ry, rx = int(cy[cand]), int(cx[cand])
        y0, y1 = max(0, ry - lock), min(H, ry + lock + 1)
        x0, x1 = max(0, rx - lock), min(W, rx + lock + 1)
        sub = cand_id_grid[y0:y1, x0:x1].ravel()
        sub = sub[sub >= 0]
        blocked = 0
        if sub.size:
            blocked = int(
                np.count_nonzero(
                    avail[sub] & (np.hypot(cy[sub] - ry, cx[sub] - rx) < spacing_px)
                )
            )
        need_after = n_add - len(chosen) - 1
        if int(avail.sum()) - 1 - blocked < need_after:
            continue
        chosen.append(int(cand))
        state[ry, rx] = True
        if sub.size:
            avail[sub[np.hypot(cy[sub] - ry, cx[sub] - rx) < spacing_px]] = False
        avail[cand] = False
        if len(chosen) == n_add:
            break
    if len(chosen) != n_add:
        raise ValueError(f"Random-order refill filled {len(chosen)} of {n_add}")
    return state, {
        "requested": int(n_add),
        "filled": len(chosen),
        "spacing_px": float(spacing_px),
        "spacing_pool_cells": int(n_pool),
        "order": "seeded_random",
        "seed": int(seed),
    }


def build_arm(
    parent: np.ndarray,
    support_union: np.ndarray,
    d_catalogue: np.ndarray,
    catalogue: np.ndarray,
    weight: np.ndarray,
    spec: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    collar = 3.0
    survivors = parent & (d_catalogue > collar)
    removed = int(parent.sum() - survivors.sum())
    pool = support_union & ~survivors & (d_catalogue > collar)
    if spec["order"] == "random":
        candidate, lock_stats = spaced_random_add(
            base_mask=survivors,
            cand_mask=pool,
            n_add=removed,
            spacing_px=float(spec["spacing_px"]),
            seed=SEED,
        )
    else:
        candidate, lock_stats = bsv.spaced_marginal_add(
            base_mask=survivors,
            cand_mask=pool,
            w=weight,
            n_add=removed,
            spacing_px=float(spec["spacing_px"]),
        )
    if int(candidate.sum()) != int(parent.sum()) or int(candidate.sum()) != N_DOTS:
        raise AssertionError("fixed-count invariant failed")
    n_added = int((candidate & ~parent).sum())
    n_removed = int((parent & ~candidate).sum())
    if n_added != removed or n_removed != removed:
        raise AssertionError("refill count does not match removals")
    if int((candidate & catalogue).sum()) != 0:
        raise AssertionError("catalogue mass")
    dmin = float(d_catalogue[candidate].min())
    if dmin < 3.0:
        raise AssertionError(f"3 px collar violated: {dmin}")
    refill_pts = np.argwhere(candidate & ~parent)
    dmin_refill = float(
        cKDTree(np.argwhere(candidate).astype(np.float64)).query(
            refill_pts.astype(np.float64), k=2
        )[0][:, 1].min()
    )
    if dmin_refill < float(spec["spacing_px"]) - 1e-9:
        raise AssertionError("spacing lock violated in the emitted refill")
    pct = 100.0 * n_removed / int(parent.sum())
    if not 1.0 <= pct <= 50.0:
        raise AssertionError(f"changed fraction outside 1-50%: {pct}")
    stats = {
        "collar_px": collar,
        "collar_m": collar * 100.0,
        "refill": True,
        "spacing_px": float(spec["spacing_px"]),
        "order": spec["order"],
        "n_removed": n_removed,
        "n_added": n_added,
        "n_dots": int(candidate.sum()),
        "pct_changed_moved": pct,
        "pct_changed_symmetric_difference": 100.0 * (n_added + n_removed) / int(parent.sum()),
        "min_catalogue_distance_px": dmin,
        "refill_min_nn_px": dmin_refill,
        "refill_pool_cells": int(pool.sum()),
        "lock": lock_stats,
    }
    return candidate, stats


def form_note(spec: dict[str, Any], stats: dict[str, Any]) -> str:
    tag = "randorder" if spec["order"] == "random" else "spaced"
    note = (
        f"R0 h33-2-b2; PRUNE<=300m +{stats['n_added']} refill >={spec['spacing_px']:g}px {tag}, "
        f"N 37654; pred {float(spec['prediction']):+.3f} MODEL"
    )
    if len(note) > 140:
        raise AssertionError(f"form note too long: {len(note)}")
    return note


def card(spec: dict[str, Any], stats: dict[str, Any], rec: dict[str, Any]) -> dict[str, Any]:
    lo, hi = map(float, spec["prediction_range"])
    return {
        "axis": AXIS,
        "value": spec["value"],
        "parent": PARENT_ID,
        "change_vs_parent": (
            f"Remove the {stats['n_removed']:,} R0 dots at d_catalogue <= 300 m; add back "
            f"{stats['n_added']:,} dots on the H19-5/H19-4/H16-1 ridge supports outside the "
            f"collar, each >= {spec['spacing_px']:g} px from every other dot in the output "
            f"(observed refill min NN {stats['refill_min_nn_px']:.3f} px); N held at 37,654. "
            f"Refill order: {RANK_BASIS if spec['order'] != 'random' else RAND_BASIS}."
        ),
        "hypothesis": spec["hypothesis"],
        "mechanism": (
            "DTI = T/(0.2T + 0.2(S-M) + 0.8|G|) with T the triangular-kernel credit to unseen "
            "new-fault truth and S-M the mass that is already covered by a stronger neighbour. "
            "A refill only pays if it becomes the nearest dot over a strip of ground that no "
            "other dot already owns. Two dots closer than the 3 px kernel radius split that "
            "strip, so the second one adds S without adding T; a lock wider than the kernel "
            "radius (4.5 px = 450 m) guarantees each refill owns its own visible strip. The "
            "4.5 px arm is the clean test of that statement at a fixed donor set, fixed count "
            "and fixed pool."
        ),
        "non_fault_mimic": (
            "Dispersing dots can also simply decorrelate them from a clustered error field: "
            "GeoDAWN Area 2 was flown at 400 m line spacing, so flight-line corrugation makes "
            "'regularly spaced' patterns look plausible on non-fault ground; equally, a real "
            "fault splay or relay step can be genuinely dense, and a spacing lock would delete "
            "it. Alluvial-fan and pediment margins also produce regularly spaced ridge breaks "
            "on the H19-5 support."
        ),
        "predicted_sign_size": (
            f"MODEL live delta {float(spec['prediction']):+.3f} vs R0 (CLAIM 0.2778), range "
            f"[{lo:+.3f},{hi:+.3f}]; blind SGMC PROXY predicted {float(spec['blind_prediction']):+.4f} "
            f"vs R0 0.096060. Both are projections, not scores; |live delta| < "
            f"{NO_EVIDENCE_BAND:g} on public chunks is no evidence."
        ),
        "falsifier": (
            "For the dose: if p3space45's blind PROXY is not at least 0.001 above p3space35's "
            "0.101042, separation stops paying at 3.5 px and the final file should not push the "
            "lock further. For the ordering control: if p3space35rand falls >= 0.005 below "
            "p3space35, the four-line field (not the geometry) is doing the work and the ranked "
            "refill must be kept. A live receipt of any arm at <= R0 - 0.01 closes the whole "
            "spacing-locked refill family regardless of the proxies."
        ),
        "ranking_basis": RANK_BASIS if spec["order"] != "random" else RAND_BASIS,
        "four_line_field": FIELD_SOURCES if spec["order"] != "random" else "not used (control)",
        "parent_diff": rec["parent_diff"],
        "fixed_count": N_DOTS,
        "submission_name": rec["id"],
        "form_note": rec["form_note"],
        "report_only_not_gates": [
            "hide-and-recover catalogue PROXY",
            "single-feature leakage canary",
            "blind off-catalogue SGMC control",
            "10 km and 12 km dot-density CV",
        ],
    }


def main() -> int:
    rows = list(csv.DictReader(LEDGER.open(newline="", encoding="utf-8")))
    ledger_fields = list(csv.DictReader(LEDGER.open(newline="", encoding="utf-8")).fieldnames or [])
    pairs = {(r.get("parent"), r.get("axis"), r.get("value")) for r in rows}
    for spec in SPECS:
        if (PARENT_ID, AXIS, spec["value"]) in pairs:
            why = (
                "WITHDRAWN at merge (IR-88-55): a concurrent session merged byte-identical "
                "bytes for this pair; the merged row is canonical"
                if spec["value"] in WITHDRAWN_VALUES
                else "already in the ledger"
            )
            raise SystemExit(f"STOP: (parent, axis, value) {spec['value']}: {why}")
        if any(RELEASES.glob(f"{PARENT_ID}-{AXIS}{spec['value']}-{DATE}-*")):
            raise SystemExit(f"STOP: artifacts already exist for {spec['value']}")

    verified = bpv.verify_manifest(MANIFEST)
    lineage = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat, parent = (
        lineage["foot"], lineage["catalogue"], lineage["d_cat"], lineage["r0"],
    )
    if lineage["rebuilt_zeros_sha256"] != bpv.PARENT_SHA_ZEROS or (
        lineage["rebuilt_nan_sha256"] != bpv.PARENT_SHA_NAN
    ):
        raise SystemExit("STOP: R0 rebuild does not byte-match the pinned parent")
    if int(parent.sum()) != N_DOTS:
        raise SystemExit(f"STOP: R0 dot count {int(parent.sum())}")

    support_union = np.zeros_like(parent)
    support_parts: dict[str, int] = {}
    for key in bsv.SOURCE_SUPPORTS:
        mask = (np.nan_to_num(rasterio.open(verified[key]).read(1), nan=0.0) > 0) & foot
        support_parts[key] = int(mask.sum())
        support_union |= mask

    manifest_sha = sha256_file(MANIFEST)
    write_json(
        PREREG,
        {
            "schema": "gems88.prune-spacing-dose-preregistration.v1",
            "created_utc": utc_now(),
            "parent": {
                "id": PARENT_ID,
                "n_dots": N_DOTS,
                "zeros_sha256": lineage["rebuilt_zeros_sha256"],
                "nan_sha256": lineage["rebuilt_nan_sha256"],
            },
            "axis": AXIS,
            "axis_selection": (
                "Agent-chosen. PRUNE is the only axis an R0 child can edit without inheriting "
                "the sub-3 px collar (IR-88-47); MASS/CONCENTRATION/SNAP/RELIEF/SPACING/TRACKB "
                "are all closed as slot axes on this lineage in SLOT_PLAN.md."
            ),
            "design": (
                "Matched triplet at collar 3 px, 2,171 donors, N 37,654, same pool, same seed: "
                "lock 2.8 px (dose down), lock 4.5 px (dose up), lock 3.5 px with random refill "
                "order (ranking control against the ledgered p3space35)."
            ),
            "values_are_new": True,
            "ledger_rows_checked": len(rows),
            "manifest_sha256": manifest_sha,
            "manifest_verified_inputs": len(verified),
            "git_sha": git_value("rev-parse", "HEAD"),
            "source_support_pixels": support_parts,
            "source_support_union_pixels": int(support_union.sum()),
            "refill_ranking_basis": RANK_BASIS,
            "random_control_basis": RAND_BASIS,
            "physical_field": FIELD_SOURCES,
            "predicted_no_evidence_band": NO_EVIDENCE_BAND,
            "predictions_are": "MODEL, registered before any PROXY/SGMC instrument ran",
            "variants": [
                {
                    "value": s["value"],
                    "collar_px": 3.0,
                    "spacing_px": s["spacing_px"],
                    "order": s["order"],
                    "predicted_change": f"MODEL:{float(s['prediction']):+.3f}",
                    "predicted_range": list(s["prediction_range"]),
                    "predicted_blind_sgmc_delta_vs_r0": s["blind_prediction"],
                    "hypothesis": s["hypothesis"],
                }
                for s in SPECS
            ],
            "no_submission": True,
        },
    )

    weight, canaries = bpv.build_physical_field_and_canaries(
        verified=verified,
        foot=foot,
        catalogue=catalogue,
        h19_5=(np.nan_to_num(rasterio.open(verified["anc_h19_5"]).read(1), nan=0.0) > 0) & foot,
    )
    if not canaries or max(canaries.values()) > 0.90:
        raise SystemExit(f"STOP: leakage canary failure {canaries}")

    masks: dict[str, np.ndarray] = {PARENT_ID: parent}
    stats_by_value: dict[str, dict[str, Any]] = {}
    for spec in SPECS:
        candidate, stats = build_arm(parent, support_union, d_cat, catalogue, weight, spec)
        weighted = bpv.weighted_expected_dti(candidate, weight)
        parent_weighted = bpv.weighted_expected_dti(parent, weight)
        stats["expected_dti_field"] = round(float(weighted["dti"]), 6)
        stats["expected_dti_delta_vs_r0"] = round(
            float(weighted["dti"] - parent_weighted["dti"]), 6
        )
        masks[f"{PARENT_ID}-{AXIS}{spec['value']}"] = candidate
        stats_by_value[spec["value"]] = stats
        print(f"built {spec['value']}: N={stats['n_dots']} pool={stats['refill_pool_cells']} "
              f"lock_pool={stats['lock']['spacing_pool_cells']} refill_minNN={stats['refill_min_nn_px']:.3f}")

    diagnostics = bpv.evaluate_report_only_instruments(
        arms=masks, foot=foot, catalogue=catalogue, sgmc_path=verified["sgmc_faults_control"]
    )
    parent_nn = bsv.nearest_neighbour_stats(parent)

    existing_shas = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}
    for row in rows:
        existing_shas.update(v for v in (row.get("sha256"), row.get("sha256_zeros")) if v)

    new_rows: list[dict[str, str]] = []
    new_cards: dict[str, Any] = {}
    receipts: dict[str, Any] = {}
    for spec in SPECS:
        value = spec["value"]
        candidate = masks[f"{PARENT_ID}-{AXIS}{value}"]
        stats = stats_by_value[value]
        nn = bsv.nearest_neighbour_stats(candidate)
        rec = bpv.write_and_verify_variant(
            mask=candidate,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=parent,
            axis=AXIS,
            value=value,
            note_template=form_note(spec, stats),
            existing_shas=existing_shas,
            parent_id=PARENT_ID,
            parent_sha_zeros=bpv.PARENT_SHA_ZEROS,
            parent_sha_nan=bpv.PARENT_SHA_NAN,
            date=DATE,
            min_catalogue_px=3.0,
        )
        existing_shas.update((rec["sha256"], rec["sha256_zeros"]))
        diag = diagnostics[f"{PARENT_ID}-{AXIS}{value}"]
        sgmc_delta = round(float(diag["sgmc_control"]["dti"] - diagnostics[PARENT_ID]["sgmc_control"]["dti"]), 6)
        rec.update(
            {
                "evidence_class": "BUILT candidate; MODEL/PROXY only; no receipt",
                "manifest": {
                    "path": "registry/data_manifest.json",
                    "sha256": manifest_sha,
                    "verified_input_count": len(verified),
                    "all_manifest_inputs_verified": True,
                },
                "collar_px": 3.0,
                "collar_m": 300.0,
                "refill_spacing_px": spec["spacing_px"],
                "refill_order": spec["order"],
                "removed_parent_dots": stats["n_removed"],
                "added_dots": stats["n_added"],
                "refill_pool_cells": stats["refill_pool_cells"],
                "refill_spacing_pool_cells": stats["lock"]["spacing_pool_cells"],
                "refill_min_nn_px": stats["refill_min_nn_px"],
                "pct_changed_exact": stats["pct_changed_moved"],
                "ranking_basis": RANK_BASIS if spec["order"] != "random" else RAND_BASIS,
                "four_line_field": FIELD_SOURCES if spec["order"] != "random" else None,
                "source_support_pixels": support_parts,
                "seed": SEED,
                "build_script_sha256": sha256_file(Path(__file__).resolve()),
                "git_sha": git_value("rev-parse", "HEAD"),
                "nearest_neighbour_stats": {"R0": parent_nn, "candidate": nn},
                "expected_dti_on_four_line_field": {
                    "dti": stats["expected_dti_field"],
                    "delta_vs_r0": stats["expected_dti_delta_vs_r0"],
                    "evidence_class": "MODEL (label-free physics field, not a truth set)",
                },
                "report_only_diagnostics": diag,
                "r0_reference_diagnostics": diagnostics[PARENT_ID],
                "blind_sgmc_delta_vs_r0": sgmc_delta,
                "predicted_change": f"MODEL:{float(spec['prediction']):+.3f}",
                "predicted_range": list(spec["prediction_range"]),
            }
        )
        receipts[value] = rec
        new_cards[rec["id"]] = card(spec, stats, rec)
        new_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": AXIS,
                "value": value,
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{stats['pct_changed_moved']:.3f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{float(spec['prediction']):+.3f}",
                "predicted_range": f"[{spec['prediction_range'][0]:+.3f}, {spec['prediction_range'][1]:+.3f}]",
                "ranking_basis": RANK_BASIS if spec["order"] != "random" else RAND_BASIS,
                "receipt_score": "",
                "receipt_date": "",
                "description": (
                    f"PRUNE <=300 m collar, +{stats['n_added']:,} spacing-locked refill at "
                    f">= {spec['spacing_px']:g} px ({spec['order']}), N held 37,654; "
                    f"blind SGMC PROXY {diag['sgmc_control']['dti']:.6f} "
                    f"({sgmc_delta:+.6f} vs R0), field MODEL "
                    f"{stats['expected_dti_delta_vs_r0']:+.6f}"
                ),
                "recommendation": (
                    f"Spacing-dose arm: compare with p3space35 (blind 0.101042) and "
                    f"p3space45/p3space35rand in the same triplet. {spec['hypothesis']}"
                ),
            }
        )

    with LEDGER.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=ledger_fields, lineterminator="\n")
        for row in new_rows:
            writer.writerow(row)

    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    collisions = set(cards) & set(new_cards)
    if collisions:
        raise SystemExit(f"STOP: mechanism-card id collision {collisions}")
    cards.update(new_cards)
    write_json(CARDS, cards)

    argv = sys.argv[:]
    sys.argv = [
        "validate_variant.py",
        *[str(RELEASES / f"{rec['id']}.tif") for rec in receipts.values()],
        *[str(RELEASES / f"{rec['id']}-zeros.tif") for rec in receipts.values()],
        "--out", str(VALIDATION),
    ]
    gate_rc = validate_variant.main()
    sys.argv = argv
    if gate_rc != 0:
        raise SystemExit("STOP: hardened validator rejected a new artifact")

    write_json(
        REPORT,
        {
            "schema": "gems88.prune-spacing-dose-report.v1",
            "created_utc": utc_now(),
            "axis": AXIS,
            "parent": {
                "id": PARENT_ID,
                "n_dots": N_DOTS,
                "zeros_sha256": lineage["rebuilt_zeros_sha256"],
                "nan_sha256": lineage["rebuilt_nan_sha256"],
                "evidence_class": "REBUILT byte-exact; historical 0.2778 is CLAIM",
            },
            "git_sha": git_value("rev-parse", "HEAD"),
            "build_script_sha256": sha256_file(Path(__file__).resolve()),
            "manifest": {
                "path": "registry/data_manifest.json",
                "sha256": manifest_sha,
                "verified_input_count": len(verified),
                "all_manifest_inputs_verified": True,
            },
            "leakage_canaries": {
                "passed": True,
                "max_single_feature_symmetric_auc": max(canaries.values()),
            },
            "source_support_pixels": support_parts,
            "variants": receipts,
            "report_only_diagnostics": diagnostics,
            "hardened_validator": {
                "out": str(VALIDATION.relative_to(ROOT)), "returncode": 0,
            },
            "reference_arms_not_rebuilt": {
                "p3space35": 0.101042,
                "p4space35": 0.102454,
                "p3norefill": 0.093643,
                "R0": 0.096060,
                "source": "evidence/prune_spaced_report.json (blind off-catalogue SGMC PROXY)",
            },
            "predictions_are": "MODEL/PROXY, frozen in registry/prune_spacing_dose_preregistration.json",
            "live_change_under_0.01": "no evidence (public chunks only)",
            "slots_used": 0,
            "submitted": False,
        },
    )
    print(json.dumps(
        {
            "built": {v: {"id": r["id"], "sha8": r["sha256"][:8],
                          "sgmc": r["report_only_diagnostics"]["sgmc_control"]["dti"],
                          "field_delta": r["expected_dti_on_four_line_field"]["delta_vs_r0"]}
                      for v, r in receipts.items()},
            "report": str(REPORT.relative_to(ROOT)),
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
