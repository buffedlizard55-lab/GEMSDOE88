#!/usr/bin/env python3
"""Build and validate controlled AXIS=SNAP scarp-transplant variants of parent R1.

Session context (Brief v2, human instruction: "pick your own axis")
-------------------------------------------------------------------
``AXIS = SNAP`` on the gate-clean parent ``R1 = h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705``.

Why this axis/parent pair:

1. The spacing-locked scarp snap on R0 (``SNAPscarp2px``, ``fae77ff4``) is the ONLY
   built candidate above R0 on the blind off-catalogue USGS SGMC control
   (``0.096806`` vs ``0.096060`` PROXY); pure potential-field snaps and every
   RELIEF/PRUNE-widening/CONCENTRATION arm lose on that control.
2. IR-88-43 placed every R0-parented non-PRUNE arm on HOLD: R0 carries 2,171 dots
   at ``2 < d_cat <= 3 px``, a literal breach of the brief's ``>= 3 px`` non-PRUNE
   rule. R1 (min ``d_cat = 3.1623 px``) is the named gate-clean parent (IR-88-33).
3. Transplanting the SAME field and the SAME deterministic spacing-locked bijection
   onto R1 keeps the winning mechanism slot-eligible with no waiver, and the arm
   double-serves as the week-2 "fuse the two best axes" composite (collar-prune +
   scarp re-centering) that SLOT_PLAN.md defers until receipts exist.

Arms (all preregistered in registry/preregistration_snap_r1_scarp.json BEFORE any
proxy was run; MODEL values are scenario anchors, never scores):

    value      field            window   support lock   role
    scarp2px   edge_scarp_pot   <=2 px   off-support    primary fusion candidate
    scarp1px   edge_scarp_pot   <=1 px   off-support    displacement-dose bracket
    ridge2px   edge_scarp_pot   <=2 px   H19-5 only     intra-support control

``edge_scarp_pot`` = 0.42*det_elev_slope(b19) + 0.23*det_elev Hessian ridge(b12)
+ 0.20*iso_grav_anom_hg(b18) + 0.15*tmi_hg(b3), percentile-ranked inside the
footprint -- provided competition bands ONLY, zero external LiDAR -- built by
``scripts/build_snap_variants.py::build_snap_edge_fields_and_canaries`` (the exact
field of the R0 winner). The allocator is ``snap_dots_within_window`` from the same
module (min_sep 2.8 -> 2.8284 px on Z^2, best-gain-first, ties by (row, col), no
RNG). Unlike the R0 family there are no frozen collar dots: EVERY R1 dot is
eligible and EVERY target satisfies ``d_cat > 3.0 px``, so the whole file is
gate-clean, not merely its additions.

The script also rebuilds the R0 ``scarp2px`` reference mask in-memory (never
written to releases/) and asserts it reproduces the published receipt statistics,
so the cross-parent SGMC comparison is same-run and the winner is reproducible
without its gitignored TIFF.

Everything is deterministic, SHA-256 pinned, fail-closed, and re-read from disk.
Idempotent reruns replace ONLY this family's rows/files/cards (IR-88-39).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import sys
import time

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_prune_variants as bpv  # noqa: E402
import build_snap_variants as bsnap  # noqa: E402
import build_snap_r1_variants as bsv  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_snap_r1_scarp.json"
REPORT = ROOT / "evidence" / "snap_r1_scarp_axis_report.json"

R1_ID = bsv.R1_ID
R1_SHA_NAN = bsv.R1_SHA_NAN
R1_SHA_ZEROS = bsv.R1_SHA_ZEROS
R0SCARP_REF_ID = "h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4"

# This builder owns ONLY these (parent=R1, axis=SNAP, value) rows/cards/files.
OWN_VALUES = ("scarp2px", "scarp1px", "ridge2px")

# Preregistered scenario MODEL anchors (registry/preregistration_snap_r1_scarp.json).
PRE_REGISTERED = {
    "scarp2px": ("MODEL:+0.006", "[-0.006,+0.016]"),
    "scarp1px": ("MODEL:+0.003", "[-0.006,+0.012]"),
    "ridge2px": ("MODEL:+0.002", "[-0.005,+0.010]"),
}

MIN_SEP = 2.8          # -> 2.8284 px on Z^2, the R0 family's spacing lock
MIN_SEP_GRID = 2.8284  # sqrt(8), the smallest grid distance >= 2.8
COLLAR_PX = 3.0


SPECS = [
    (
        "scarp2px",
        2.0,
        False,
        "h33-2-b2 PRUNEp3px R1; SNAP <=2px to scarp+TMI/grav co-edge, spacing-locked, 100% of dots >3px; pred +0.006 MODEL",
        "Full-dose transplant of the R0 blind-control winner: every R1 dot may move "
        "<=2.0 px (200 m) onto the strongest edge_scarp_pot cell (0.42 b19 slope + "
        "0.23 b12 Hessian ridge + 0.20 b18 iso-grav HG + 0.15 b3 TMI HG percentile "
        "ranks; provided bands only), spacing lock >=2.8284 px at placement, targets "
        "strictly d_cat > 3.0 px, count fixed at 37,654. Same field and allocator as "
        "R0 SNAPscarp2px (fae77ff4, SGMC 0.096806 PROXY), new gate-clean parent.",
        {
            "hypothesis": "R1's dots inherit from H19-5 the ~1-2 px (100-200 m) displacement of GeoDAWN Area 2 lineaments (400 m flight-line spacing, 150-200 m drape; https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7) relative to the discrete surface fault scarp. Re-centering every dot <=2 px onto the co-registered topographic scarp + TMI/gravity co-edge -- the only edit that beat R0 on the blind off-catalogue SGMC control (0.096806 vs 0.096060 PROXY) -- keeps that gain on the gate-clean parent R1, whose 2,171 w-field refills are exactly the dots whose placement is least proven (refill ranking AUC 0.47 blind, IR-88-38) and most in need of an independent geometric anchor.",
            "mechanism": "A range-front normal fault at ~60 deg Andersonian dip through 0.5-1.5 km of basin fill puts (i) a topographic breakline at its updip surface emergence (band 19 det_elev_slope, band 12 det_elev Hessian ridge crest) and (ii) magnetisation/density steps imaged as horizontal-gradient maxima (band 18 isostatic gravity, band 3 TMI). The snap field weights the surface emergence 65% and the potential-field edge 35%. A dot at distance d from a line-like truth earns triangular-kernel credit 1 - d/3 inside 300 m, so shifting drifted ridge centroids onto the scarp breakline raises per-truth-pixel credit along off-catalogue traces at fixed S = 37,654: no added wasted mass (0.2*FP_w) and no lost coverage. The >=2.8284 px placement lock stops adjacent dots bunching onto one breakline pixel and opening >300 m along-strike kernel gaps -- the failure mode of the unspaced w2E1/w2E2 arms (SGMC -0.008).",
            "non_fault_mimic": "Wave-cut Pleistocene Lake Lahontan/Bonneville paleoshorelines (~1,330/1,555 m), welded-tuff mesa rims, and incised alluvial-fan terrace risers form sharp 100 m topographic breaklines inside the snap window of piedmont fault corridors without brittle basement throw; GeoDAWN 400 m flight-line levelling shoulders can attract the 35% potential-field weight.",
            "predicted_sign_size": "Preregistered MODEL +0.006 live delta vs R1 (scenario range [-0.006,+0.016]), anchored on the identical R0 edit's preregistered +0.006; deliberately NOT additive with R1's own +0.005 MODEL because snapping relocates the same dots the collar refill placed. |live delta| < 0.01 vs the parent actually submitted is no evidence.",
            "falsifier": "Live receipt <= R1 - 0.01 falsifies scarp re-centering on the refilled parent and says the w-field refills already sit better than topographic crests; if SGMC(arm) <= SGMC(R1) at build time the preregistered decision rule parks the arm at HOLD before any slot is spent.",
        },
    ),
    (
        "scarp1px",
        1.0,
        False,
        "h33-2-b2 PRUNEp3px R1; SNAP <=1px to scarp+TMI/grav co-edge, spacing-locked, 100% of dots >3px; pred +0.003 MODEL",
        "Displacement-dose bracket: same field and allocator as the scarp2px arm, "
        "window halved to <=1.0 px (100 m, four-neighbour moves only). Tests whether "
        "the re-centering gain survives when the worst-case kernel cost of a move is "
        "halved; count fixed at 37,654; targets strictly d_cat > 3.0 px.",
        {
            "hypothesis": "If the drift between H19-5 ridge centroids and the physical scarp is mostly ~1 px rather than ~2 px, a <=1 px window captures most of the blind-control gain at half the worst-case displacement risk; if the gain needs the full 200 m reach (flight-line-scale drift), this arm underperforms its 2 px sibling and the dose-response identifies 200 m as the operative drift scale.",
            "mechanism": "Triangular-kernel credit 1 - d/3 is linear in misalignment but the risk is asymmetric: a wrong 2 px move can take a dot from d=1 (credit 0.67) to d=3 (credit 0) across a thin truth strand, while a wrong 1 px move keeps >= 0.33. At max_r = 1.0 the offset set is the four unit neighbours, so every executed move is exactly 100 m and no dot can cross a 2 px-wide ribbon in one step; the same best-gain-first deterministic order and >=2.8284 px placement lock apply.",
            "non_fault_mimic": "Same breakline mimics as scarp2px (pluvial shorelines, tuff rims, fan risers); additionally at a single-cell reach, 100 m DEM grid noise and detrending artefacts inside one cell become competitive attractors.",
            "predicted_sign_size": "Preregistered MODEL +0.003 live delta vs R1 (scenario range [-0.006,+0.012]), the half-dose anchor of the scarp2px scenario, mirroring the R1 f35 family's lower-variance argument for its own 1 px arm.",
            "falsifier": "SGMC(scarp1px) >= SGMC(scarp2px) falsifies 'the gain needs 200 m reach' and says the drift field is sub-pixel; a live receipt >= R1 + 0.01 while scarp2px is <= R1 - 0.01 would identify displacement distance, not field quality, as the binding risk.",
        },
    ),
    (
        "ridge2px",
        2.0,
        True,
        "h33-2-b2 PRUNEp3px R1; SNAP <=2px on H19-5 support to scarp co-edge, spacing-locked, 100% of dots >3px; pred +0.002 MODEL",
        "Intra-support control: same field and allocator, but targets are restricted "
        "to H19-5 ridge pixels (stay_on_h19_5=True), so no dot ever leaves the parent "
        "detector's own support. Separates 'de-jitter within the ribbon' from 'reach "
        "the off-support topographic crest'; count fixed at 37,654.",
        {
            "hypothesis": "If the blind-control gain of scarp snapping is intra-support de-jittering (dot_thin's score-blind BFS anchored dots on the northern/western outer pixel of 2-3 px wide H19-5 ribbons), restricting targets to H19-5 preserves most of it; if the gain is off-support crest reach, this arm loses to scarp2px as it did on R0 (0.096439 vs 0.096806 PROXY). On R1 the contrast also probes the 2,171 refills: they were placed at w-field maxima ON support, so intra-support jitter should be smaller for them than for BFS-thinned R0 dots.",
            "mechanism": "Targets must satisfy h19_5 & foot & ~catalogue & d_cat > 3.0 px; moves stay inside the 2-3 px ribbon, so displacement is small (R0 analog: mean 0.23 px over all dots) and the kernel cost of a wrong move is bounded by the ribbon width. The >=2.8284 px placement lock again prevents along-strike bunching; bijection keeps S = 37,654.",
            "non_fault_mimic": "The ribbon itself: intra-support de-jittering cannot fix a genuinely mislocated ribbon (a drifted aeromagnetic lineament with no surface fault); pluvial-shoreline breaklines that run along H19-5 ribbons attract the same field within support.",
            "predicted_sign_size": "Preregistered MODEL +0.002 live delta vs R1 (scenario range [-0.005,+0.010]); discounted from the R0 family's ridge2px +0.003 because R1's refills were already placed at on-support field maxima.",
            "falsifier": "SGMC(ridge2px) >= SGMC(scarp2px) reverses the R0 ordering and says the gain is intra-support de-jittering, so future snaps must stay support-locked; live receipts <= R1 - 0.01 for both ridge2px and scarp2px close SNAP on R1 (three families then agree: IR-88-31/32, f35, this one).",
        },
    ),
]


def moved_dot_spacing_invariant(parent_mask: np.ndarray, mask: np.ndarray) -> dict:
    """Prove the placement lock on the FINAL configuration.

    Every net-added cell was checked against every occupied cell when it was
    placed, and later placements re-check against it, so each net-added dot must
    end >= MIN_SEP_GRID px from every other dot. Unmoved inherited pairs (R1's
    non-spacing-locked refills) may stay closer; that is reported, never hidden.
    """
    added = mask & ~parent_mask
    ay, ax = np.nonzero(added)
    my, mx = np.nonzero(mask)
    tree = cKDTree(np.column_stack([my, mx]))
    d_nn_added, _ = tree.query(np.column_stack([ay, ax]), k=2)
    d_nn_all, _ = tree.query(np.column_stack([my, mx]), k=2)
    return {
        "n_added_cells": int(added.sum()),
        "min_nn_added_vs_all_px": round(float(d_nn_added[:, 1].min()), 4) if len(ay) else None,
        "spacing_lock_holds_for_every_moved_dot": bool(
            len(ay) == 0 or float(d_nn_added[:, 1].min()) >= MIN_SEP_GRID - 1e-9
        ),
        "min_nn_global_px": round(float(d_nn_all[:, 1].min()), 4),
        "mean_nn_global_px": round(float(d_nn_all[:, 1].mean()), 4),
        "note": (
            "global min NN may be < 2.8284 px: R1's 2,171 exact-marginal refills were "
            "selected without a spacing lock (IR-88-37); SNAP never repairs inherited "
            "pairs, it only guarantees placement spacing for dots it moves."
        ),
    }


def main() -> int:
    t0 = time.time()
    prereg = json.loads(PREREG.read_text())

    print("[1/7] Verifying SHA-256 manifest pins...")
    verified = bpv.verify_manifest()
    print(f"      Verified {len(verified)}/{len(verified)} pinned inputs.")

    print("[2/7] Rebuilding R0 (h33-h33-2-b2) byte-exactly from the 5-stage lineage...")
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    print(
        f"      EXACT R0 REBUILD OK: {int(r0.sum()):,} dots | "
        f"zeros={lin['rebuilt_zeros_sha256'][:12]}... | nan={lin['rebuilt_nan_sha256'][:12]}..."
    )

    print("[3/7] Rebuilding the label-free corroboration field w (for the R1 refill)...")
    w_field, w_canaries = bpv.build_physical_field_and_canaries(
        verified, foot, catalogue, h19_5
    )
    print(f"      w-field canaries PASS (max symmetric AUC = {max(w_canaries.values()):.5f})")

    print("[4/7] Reconstructing parent R1 = PRUNEp3px and asserting its published SHA-256...")
    r1 = bsv.reconstruct_r1(lin, w_field, verified)
    if float(d_cat[r1].min()) <= COLLAR_PX:
        raise RuntimeError("R1 collar violation before snapping")

    print("[5/7] Building provided-band edge fields & snapping (spacing-locked bijections)...")
    edge_pot, edge_scarp_pot, edge_canaries = bsnap.build_snap_edge_fields_and_canaries(
        verified, foot, catalogue
    )
    del edge_pot  # pot-only field lost on R0 (0.095178 PROXY); not re-run here.
    print(
        f"      Edge canaries PASS (max symmetric AUC = {max(edge_canaries.values()):.5f}); "
        "provided bands only, external_lidar_used=False."
    )

    # Reference: rebuild the R0 winner mask in-memory and check the published receipt.
    m_scarp_r0, d_scarp_r0 = bsnap.snap_dots_within_window(
        r0_mask=r0,
        score_field=edge_scarp_pot,
        foot=foot,
        catalogue=catalogue,
        d_cat=d_cat,
        h19_5=h19_5,
        max_r=2.0,
        min_sep=MIN_SEP,
        stay_on_h19=False,
    )
    r0_receipt_path = RELEASES / f"{R0SCARP_REF_ID}.json"
    r0_receipt = json.loads(r0_receipt_path.read_text())
    r0_ref_disp = r0_receipt["displacement"]
    repro = {
        "reference_id": R0SCARP_REF_ID,
        "rebuilt_n_dots_displaced": d_scarp_r0["n_dots_displaced"],
        "published_n_dots_displaced": r0_ref_disp["n_dots_displaced"],
        "rebuilt_mean_displacement_all_px": d_scarp_r0["mean_displacement_all_px"],
        "published_mean_displacement_all_px": r0_ref_disp["mean_displacement_all_px"],
    }
    if (
        repro["rebuilt_n_dots_displaced"] != repro["published_n_dots_displaced"]
        or abs(
            repro["rebuilt_mean_displacement_all_px"]
            - repro["published_mean_displacement_all_px"]
        )
        > 1e-4
    ):
        raise RuntimeError(f"R0 scarp2px reference does not reproduce its receipt: {repro}")
    print(
        f"      R0 scarp2px reference reproduced exactly "
        f"({repro['rebuilt_n_dots_displaced']:,} displaced, mean {repro['rebuilt_mean_displacement_all_px']} px)."
    )

    # Idempotent re-run: drop ONLY this family's rows/files/cards first.
    ledger_rows: list[dict[str, str]] = []
    raw_kept_lines: list[str] = []
    fieldnames: list[str] = []
    header_line = ""
    existing_shas: set[str] = {
        bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS,
    }
    if LEDGER.is_file():
        with LEDGER.open("r", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                if (
                    row.get("axis") == "SNAP"
                    and row.get("parent") == R1_ID
                    and row.get("value") in OWN_VALUES
                ):
                    continue
                ledger_rows.append(row)
                for k in ("sha256", "sha256_zeros"):
                    if row.get(k):
                        existing_shas.add(row[k])
        with LEDGER.open("r", newline="") as fh:
            raw_lines = fh.read().splitlines()
        header_line = raw_lines[0] if raw_lines else ""
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if (
                len(parsed) > 3
                and parsed[2] == "SNAP"
                and parsed[1] == R1_ID
                and parsed[3] in OWN_VALUES
            ):
                continue
            raw_kept_lines.append(line)
    for v_name in OWN_VALUES:
        for stale in RELEASES.glob(f"{R1_ID}-SNAP{v_name}-*"):
            stale.unlink()

    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    cards = {
        k: v
        for k, v in cards.items()
        if not any(k.startswith(f"{R1_ID}-SNAP{val}-") for val in OWN_VALUES)
    }

    arms = {bpv.PARENT_ID: r0, R1_ID: r1, R0SCARP_REF_ID: m_scarp_r0}
    built: list[tuple[dict, dict, dict]] = []

    w_dti_r1 = bpv.weighted_expected_dti(r1, w_field)["dti"]

    for value, max_r, stay_on_h19, note, desc, card in SPECS:
        mask, disp = bsnap.snap_dots_within_window(
            r0_mask=r1,
            score_field=edge_scarp_pot,
            foot=foot,
            catalogue=catalogue,
            d_cat=d_cat,
            h19_5=h19_5,
            max_r=max_r,
            min_sep=MIN_SEP,
            stay_on_h19=stay_on_h19,
        )
        if int(mask.sum()) != int(r1.sum()):
            raise RuntimeError("SNAP changed the dot count")
        if float(d_cat[mask].min()) <= COLLAR_PX:
            raise RuntimeError(f"SNAP produced a dot at {d_cat[mask].min():.4f} px <= 3 px")
        spacing = moved_dot_spacing_invariant(r1, mask)
        if not spacing["spacing_lock_holds_for_every_moved_dot"]:
            raise RuntimeError(f"Spacing lock violated for moved dots: {spacing}")
        w_dti_arm = bpv.weighted_expected_dti(mask, w_field)["dti"]
        w_delta = w_dti_arm - w_dti_r1

        pred, pred_range = PRE_REGISTERED[value]
        rec = bsnap.write_and_verify_snap_variant(
            mask=mask,
            disp_stats=disp,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=r1,
            value=value,
            note_template=note,
            existing_shas=existing_shas,
            parent_id=R1_ID,
            parent_sha_zeros=R1_SHA_ZEROS,
            parent_sha_nan=R1_SHA_NAN,
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])
        rec["parent_rebuild_verified"] = {
            "r0_zeros_sha256": bpv.PARENT_SHA_ZEROS,
            "r0_nan_sha256": bpv.PARENT_SHA_NAN,
            "r1_sha256_zeros": R1_SHA_ZEROS,
            "r1_sha256_nan": R1_SHA_NAN,
        }
        rec["spacing_lock_final_configuration"] = spacing
        rec["off_h19_5_support"] = {
            "stay_on_h19_5": bool(stay_on_h19),
            "n_dots_off_h19_5_after": int((mask & ~h19_5).sum()),
            "n_parent_dots_off_h19_5": int((r1 & ~h19_5).sum()),
        }
        rec["w_weighted_dti_MODEL"] = {
            "evidence_label": "MODEL",
            "field": "label-free corroboration field w (build_prune_variants.py)",
            "dti_parent_r1": round(w_dti_r1, 6),
            "dti_arm": round(w_dti_arm, 6),
            "delta_vs_r1": round(w_delta, 6),
            "caveat": (
                "w under-weights dots off H19-5 support (0.015*p_phys vs 0.045+) and its "
                "ranking has blind AUC 0.47 (IR-88-38); recorded as a mechanical diagnostic, "
                "the ledger prediction stays the preregistered scenario MODEL."
            ),
        }
        rec["preregistration"] = "registry/preregistration_snap_r1_scarp.json"
        rec["leakage_canaries"] = {
            "passed": True,
            "max_symmetric_auc": max(max(w_canaries.values()), max(edge_canaries.values())),
            "w_field_channels": w_canaries,
            "edge_field_channels": edge_canaries,
        }
        rec["mechanism_card"] = card
        cards[rec["id"]] = card
        arms[rec["id"]] = mask
        built.append((rec, disp, {"value": value, "desc": desc, "pred": pred, "pred_range": pred_range}))
        print(
            f"      {value}: moved {disp['n_dots_displaced']:,} dots "
            f"({rec['parent_diff']['pct_changed_moved']:.2f}% changed), mean displacement "
            f"{disp['mean_displacement_all_px']} px, min NN added {spacing['min_nn_added_vs_all_px']} px "
            f"-> {rec['id']}"
        )

    print("[6/7] REPORT-ONLY diagnostics (holdout PROXY, blind SGMC control, block CV)...")
    eval_report = bpv.evaluate_report_only_instruments(
        arms=arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )

    sgmc = lambda key: eval_report[key]["sgmc_control"]["dti"]  # noqa: E731
    sgmc_r0, sgmc_r1 = sgmc(bpv.PARENT_ID), sgmc(R1_ID)
    sgmc_r0scarp = sgmc(R0SCARP_REF_ID)
    published_sgmc_r0scarp = r0_receipt["report_only_diagnostics"]["sgmc_control"]["dti"]
    repro["rebuilt_sgmc"] = sgmc_r0scarp
    repro["published_sgmc"] = published_sgmc_r0scarp
    if abs(sgmc_r0scarp - published_sgmc_r0scarp) > 1e-6:
        raise RuntimeError(
            f"R0 scarp2px SGMC did not reproduce: {sgmc_r0scarp} != {published_sgmc_r0scarp}"
        )

    for rec, disp, meta in built:
        rec["report_only_diagnostics"] = eval_report[rec["id"]]
        rec["parent_reference_diagnostics"] = eval_report[R1_ID]
        rec["r0_reference_diagnostics"] = eval_report[bpv.PARENT_ID]
        rec["r0_scarp2px_reference_diagnostics"] = eval_report[R0SCARP_REF_ID]
        s = sgmc(rec["id"])
        # Preregistered decision rules (never gates; PROXY ordering only).
        if s >= sgmc_r0scarp:
            recomm = (
                f"GATE-CLEAN PRIMARY: blind off-catalogue SGMC {s:.6f} PROXY is at or above the "
                f"R0 winner {sgmc_r0scarp:.6f} and parent R1 {sgmc_r1:.6f}, with 100% of dots "
                ">3 px from the catalogue (no IR-88-43 waiver). Queue ahead of the HOLDed R0 "
                "scarp arm as the gate-clean SNAP/fusion candidate; a live receipt, not this "
                "proxy, decides promotion and |delta| < 0.01 is no evidence."
            )
        elif s > sgmc_r1:
            recomm = (
                f"SLOT-ELIGIBLE gate-clean SNAP candidate: blind SGMC {s:.6f} PROXY above parent "
                f"R1 {sgmc_r1:.6f} but below the R0 winner {sgmc_r0scarp:.6f}; the transplant "
                "keeps the mechanism without the collar breach. Promotion still requires a live "
                "receipt; |delta| < 0.01 is no evidence."
            )
        else:
            recomm = (
                f"HOLD: blind SGMC {s:.6f} PROXY does not exceed parent R1 {sgmc_r1:.6f}; the "
                "preregistered decision rule parks this arm (scarp re-centering does not "
                "transfer to the refilled parent). Diagnostic only; no slot."
            )
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        ledger_rows.append(
            {
                "id": rec["id"],
                "parent": R1_ID,
                "axis": "SNAP",
                "value": meta["value"],
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": meta["pred"],
                "predicted_range": meta["pred_range"],
                "ranking_basis": (
                    f"edge_scarp_pot percentile field (0.42 b19 det_elev_slope + 0.23 b12 "
                    f"det_elev Hessian ridge + 0.20 b18 iso_grav_anom_hg + 0.15 b3 tmi_hg); "
                    f"{disp['max_window_radius_px']} px window; spacing lock min_sep 2.8 px "
                    f"(>=2.8284 px at placement); stay_on_h19_5={disp['stay_on_h19_5_ridge']}; "
                    f"same field+allocator as R0 SNAPscarp2px (fae77ff4); no ranking model, no RNG"
                ),
                "receipt_score": "",
                "receipt_date": "",
                "description": meta["desc"],
                "recommendation": (
                    recomm
                    + f" SGMC {s:.6f} PROXY (R1 {sgmc_r1:.6f}, R0 {sgmc_r0:.6f}, R0-scarp2px "
                    f"{sgmc_r0scarp:.6f}); holdout PROXY structurally 0.0 (IR-88-20); 12 km CV "
                    f"{eval_report[rec['id']]['block_density_cv']['cv_12km_120px_interior']}; "
                    f"w-weighted DTI delta {rec['w_weighted_dti_MODEL']['delta_vs_r1']:+.6f} MODEL."
                ),
            }
        )

    if fieldnames:
        new_rows = [
            r
            for r in ledger_rows
            if r.get("axis") == "SNAP"
            and r.get("parent") == R1_ID
            and r.get("value") in OWN_VALUES
        ]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        for row in new_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
        body = buf.getvalue().rstrip("\n")
        with LEDGER.open("w", newline="") as fh:
            fh.write(header_line + "\n")
            for line in raw_kept_lines:
                fh.write(line + "\n")
            if body:
                fh.write(body + "\n")
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")

    print("[7/7] Writing the axis report...")
    report = {
        "session_date": "2026-10-23",
        "axis": "SNAP",
        "parent_r1": R1_ID,
        "parent_r0": bpv.PARENT_ID,
        "preregistration": "registry/preregistration_snap_r1_scarp.json",
        "provided_bands_only": True,
        "external_lidar_used": False,
        "leakage_canaries": {
            "passed": True,
            "max_symmetric_auc": max(max(w_canaries.values()), max(edge_canaries.values())),
            "w_field_channels": w_canaries,
            "edge_field_channels": edge_canaries,
        },
        "r0_scarp2px_reproduction": repro,
        "sgmc_reference": {
            "r0": sgmc_r0,
            "r1": sgmc_r1,
            "r0_scarp2px_rebuilt": sgmc_r0scarp,
        },
        "variants": [json.loads((RELEASES / f"{rec['id']}.json").read_text()) for rec, _, _ in built],
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    print("\nSNAP-R1-SCARP REPORT-ONLY SUMMARY (PROXY/MODEL, never a score)")
    for rec, disp, meta in built:
        d = eval_report[rec["id"]]
        print(
            f"  {rec['value']:<9} SGMC {d['sgmc_control']['dti']:.6f} "
            f"(R1 {sgmc_r1:.6f} / R0-scarp {sgmc_r0scarp:.6f}) | holdout "
            f"{d['holdout_proxy']['dti']:.6f} | CV12 "
            f"{d['block_density_cv']['cv_12km_120px_interior']} | moved "
            f"{disp['n_dots_displaced']:,} ({rec['parent_diff']['pct_changed_moved']:.2f}%) | "
            f"{meta['pred']}"
        )
    print(f"Elapsed {time.time() - t0:.1f}s. Receipts in releases/, report in {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
