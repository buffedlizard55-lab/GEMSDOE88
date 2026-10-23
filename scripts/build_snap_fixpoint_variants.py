#!/usr/bin/env python3
"""AXIS=SNAP on parent R1: fixpoint dose ladder + sign-flip control.

Session choice (Brief v2 §5, "pick your own session"): **SNAP**, because the
R1 scarp family is the only lineage that (a) beats its own gate-clean parent on
the blind off-catalogue SGMC control and (b) is 100% collar-clean, and because
the family's internal dose bracket (``scarp1px`` vs ``scarp2px``) is a tie
(+0.000114 PROXY) -- i.e. the field's *reach* is already saturated and nothing
in the ledger tests whether the *direction* of the move carries the signal.

Three arms, pre-registered in ``registry/preregistration_snap_r1_fixpoint.json``
BEFORE this script computed anything:

    value   edit                                          role
    fp2     1 px spacing-locked scarp snap applied twice  dose extension
    fp3     same snap applied three times                 saturation test
    anti1   same allocator on the NEGATED field (1 pass)  sign-flip control

All three keep the count fixed at 37,654, keep every moved target strictly at
``d_cat > 3.0 px``, enforce the >= 2.8284 px placement lock, use the provided
19-band stack only (zero external LiDAR), and use no RNG.

``anti1`` is the decision-relevant arm: if a move onto the *weakest* scarp
response inside the same 1 px window scores as well as a move onto the
strongest, then the blind SGMC control is paying for displacement rather than
for crest position, and the +0.0015 PROXY margin of ``scarp1px`` carries no
geological information.

Nothing is submitted; no competition or leaderboard page is contacted.
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
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_prune_variants as bpv  # noqa: E402
import build_snap_variants as bsnap  # noqa: E402
import build_snap_r1_variants as bsv  # noqa: E402
import build_snap_r1_scarp_variants as bscarp  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_snap_r1_fixpoint.json"
REPORT = ROOT / "evidence" / "snap_r1_fixpoint_axis_report.json"

R1_ID = bsv.R1_ID
R1_SHA_NAN = bsv.R1_SHA_NAN
R1_SHA_ZEROS = bsv.R1_SHA_ZEROS
SCARP1PX_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SNAPscarp1px-20261023-1944aaf5"

OWN_VALUES = ("fp2", "fp3", "anti1")
MIN_SEP = 2.8
COLLAR_PX = 3.0

PRE = json.loads(PREREG.read_text(encoding="utf-8"))["arms"]

SPECS = [
    (
        "fp2",
        2,
        1.0,
        "R1; SNAP 1px scarp snap x2, spacing-locked, all dots >3px; pred +0.003 MODEL",
        "Two-pass fixpoint dose: the same 1 px spacing-locked scarp snap applied to its own "
        "output, so a dot may climb two successive local field maxima inside 200 m. Count fixed "
        "at 37,654; every target strictly d_cat > 3 px; placement lock >= 2.8284 px; no RNG.",
        {
            "hypothesis": "A single 1 px pass leaves each dot on the best cell of a 4-neighbour window, not on the crest: residual drift of 100-200 m survives wherever the edge_scarp_pot maximum of the second ring is higher. If scarp re-centering is real, the second pass should buy credit at the same cost, because the per-dot triangular-kernel credit still rises while S stays fixed.",
            "mechanism": "Same as the R1 scarp family: a range-front normal fault at ~60 deg dip puts a topographic breakline at its surface emergence (b19 slope, b12 det-elev Hessian ridge) and a magnetisation/density step at the potential-field horizontal-gradient maximum (b18 isostatic gravity, b3 TMI); the field weights the surface term 65%. A second 1 px pass continues the greedy climb toward that composite maximum along the same trail, which is exactly the direction the greedy allocator already chose.",
            "non_fault_mimic": "Lake Lahontan/Bonneville paleoshorelines, welded-tuff mesa rims and fan-terrace risers are sharp breaklines that continue to attract the 65% topographic weight on a second pass; 400 m GeoDAWN flight-line levelling shoulders can attract the 35% potential-field weight. Iterating amplifies whichever of these sits at the local maximum.",
            "predicted_sign_size": "Preregistered MODEL +0.003 live delta vs R1 (range -0.007 to +0.013). Smaller than a slot-resolvable effect: |live delta| < 0.01 is no evidence. The arm is a geometry test at proxy resolution, not a claimed win.",
            "falsifier": "Blind SGMC(fp2) <= SGMC(scarp1px 0.097567) says one pass already saturates the field and the fixpoint idea is dead; SGMC(fp2) <= SGMC(R1 0.096083) parks the arm at HOLD before any slot is spent.",
        },
    ),
    (
        "fp3",
        3,
        1.0,
        "R1; SNAP 1px scarp snap x3, spacing-locked, all dots >3px; pred +0.002 MODEL",
        "Three-pass fixpoint saturation test: the same 1 px spacing-locked scarp snap applied three "
        "times. Count fixed at 37,654; every target strictly d_cat > 3 px; placement lock "
        ">= 2.8284 px; no RNG.",
        {
            "hypothesis": "If the crest is real and the greedy climb is monotone, the third pass should add little relative to the second; if it instead keeps raising blind credit, the arm is walking toward a field maximum that is not the mapped trace, and the family's gain is an artefact of the field rather than of fault geometry.",
            "mechanism": "Identical allocator and field as fp2 with one more iteration. Concave-down curvature of the score surface around the composite crest means successive passes have diminishing per-pass gain; a still-rising third pass implies a broad, non-fault-aligned maximum (shoreline or flight-line shoulder).",
            "non_fault_mimic": "Same mimic set as fp2: paleoshorelines, tuff rims, fan-terrace risers, flight-line levelling. On a third pass, topographic artefacts with wider crests overtake narrow fault breaklines by construction of a greedy maximum search.",
            "predicted_sign_size": "Preregistered MODEL +0.002 live delta vs R1 (range -0.008 to +0.012). Deliberately below fp2: the expected marginal gain of a pass decays. |live delta| < 0.01 is no evidence.",
            "falsifier": "SGMC(fp3) > SGMC(fp2) by >= 0.001 contradicts the saturation hypothesis and says the field is being climbed past the fault trace; SGMC(fp3) <= SGMC(R1) parks the arm at HOLD.",
        },
    ),
    (
        "anti1",
        1,
        1.0,
        "R1; SNAP 1px to WEAKEST scarp response (sign-flip control), all dots >3px; pred -0.006 MODEL",
        "Sign-flip negative control: one pass of the same allocator and the same 1 px spacing lock on "
        "the negated edge_scarp_pot field, so every dot moves onto the weakest composite edge/scarp "
        "response in its window. Count fixed at 37,654; every target strictly d_cat > 3 px.",
        {
            "hypothesis": "The +0.0015 PROXY margin of the scarp family is only interpretable as crest information if its sign flips with the field's sign. This arm prices 'any 1 px displacement' against 'displacement up the crest field', which no arm in the ledger does.",
            "mechanism": "Identical to the scarp transplant except the greedy gain is taken against -edge_scarp_pot: each dot steps to the adjacent cell with the lowest composite edge/scarp response. Nothing about the target label changes, so the difference between anti1 and scarp1px is exactly the direction of the move under a fixed displacement budget.",
            "non_fault_mimic": "None needed: the control deliberately moves mass off breaklines, into the smooth interiors of basins and ranges where no fault trace can be favoured. It is designed to score below the parent if the instrument is measuring geometry at all.",
            "predicted_sign_size": "Preregistered MODEL -0.006 live delta vs R1 (range -0.016 to +0.002). Not a slot candidate by construction; its only job is to calibrate the instrument.",
            "falsifier": "SGMC(anti1) >= SGMC(fp2) means the blind SGMC control pays for displacement rather than crest position; the scarp family's PROXY margin is then uninformative and should not be promoted on proxy evidence. SGMC(anti1) <= SGMC(R1) - 0.001 is the result that makes the crest reading credible.",
        },
    ),
]


def cumulative_displacement(parent: np.ndarray, mask: np.ndarray) -> dict:
    """Net displacement of each final dot to its nearest parent dot (bijection, count fixed)."""
    py, px = np.nonzero(parent)
    my, mx = np.nonzero(mask)
    tree = cKDTree(np.column_stack([py, px]))
    d, _ = tree.query(np.column_stack([my, mx]), k=1)
    moved = d > 0
    return {
        "reference": "nearest pinned-parent R1 dot, per final dot",
        "n_dots_moved_net": int(moved.sum()),
        "pct_dots_moved_net": round(100.0 * float(moved.mean()), 2),
        "mean_net_displacement_all_px": round(float(d.mean()), 4),
        "mean_net_displacement_all_m": round(float(d.mean()) * 100.0, 2),
        "max_net_displacement_px": round(float(d.max()), 4),
        "mean_net_displacement_moved_px": round(float(d[moved].mean()), 4),
    }


def main() -> int:
    t0 = time.time()
    print("[1/8] Verifying every pinned input...")
    verified = bpv.verify_manifest()
    lin = bpv.rebuild_r0_from_lineage(verified)
    r0, foot, catalogue, d_cat, h19_5 = (
        lin["r0"], lin["foot"], lin["catalogue"], lin["d_cat"], lin["h19_5"],
    )
    if bpv.sha256_file(verified["parent_r0_zeros"]) != bpv.PARENT_SHA_ZEROS:
        raise RuntimeError("R0 zeros hash mismatch")
    print(f"      R0 rebuilt: {int(r0.sum()):,} dots, zeros={bpv.PARENT_SHA_ZEROS[:12]}...")

    print("[2/8] Rebuilding the label-free corroboration field w...")
    w_field, w_canaries = bpv.build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    print(f"      w canaries PASS (max symmetric AUC {max(w_canaries.values()):.5f})")

    print("[3/8] Reconstructing R1 and asserting both pinned SHA-256 values...")
    r1 = bsv.reconstruct_r1(lin, w_field, verified)
    if float(d_cat[r1].min()) <= COLLAR_PX:
        raise RuntimeError("R1 is not collar-clean")

    print("[4/8] Building the provided-band edge/scarp field...")
    _, edge_scarp_pot, edge_canaries = bsnap.build_snap_edge_fields_and_canaries(
        verified, foot, catalogue
    )
    max_auc = max(max(w_canaries.values()), max(edge_canaries.values()))
    if max_auc > 0.90:
        raise RuntimeError(f"Leakage canary AUC {max_auc} > 0.90 -- stop and investigate")
    print(f"      edge canaries PASS (max symmetric AUC {max_auc:.5f}); external LiDAR used=False")

    print("[5/8] Running the fixpoint ladder and the sign-flip control...")
    pass_masks: list[np.ndarray] = []
    pass_stats: list[dict] = []
    cur = r1
    for step in range(1, 4):
        cur, disp = bsnap.snap_dots_within_window(
            r0_mask=cur,
            score_field=edge_scarp_pot,
            foot=foot,
            catalogue=catalogue,
            d_cat=d_cat,
            h19_5=h19_5,
            max_r=1.0,
            min_sep=MIN_SEP,
            stay_on_h19=False,
        )
        if int(cur.sum()) != int(r1.sum()):
            raise RuntimeError(f"pass {step} changed the dot count")
        if float(d_cat[cur].min()) <= COLLAR_PX:
            raise RuntimeError(f"pass {step} produced a dot at {d_cat[cur].min():.4f} px")
        pass_masks.append(cur.copy())
        pass_stats.append({k: disp[k] for k in (
            "n_dots_displaced", "mean_displacement_all_px", "min_interdot_nn_dist_px"
        )})
        print(
            f"      pass {step}: {disp['n_dots_displaced']:,} dots moved, mean "
            f"{disp['mean_displacement_all_px']} px, min NN {disp['min_interdot_nn_dist_px']} px"
        )

    anti1, anti_disp = bsnap.snap_dots_within_window(
        r0_mask=r1,
        score_field=-edge_scarp_pot,
        foot=foot,
        catalogue=catalogue,
        d_cat=d_cat,
        h19_5=h19_5,
        max_r=1.0,
        min_sep=MIN_SEP,
        stay_on_h19=False,
    )
    if int(anti1.sum()) != int(r1.sum()):
        raise RuntimeError("anti1 changed the dot count")
    if float(d_cat[anti1].min()) <= COLLAR_PX:
        raise RuntimeError("anti1 produced a collar-breaching dot")
    print(
        f"      anti1: {anti_disp['n_dots_displaced']:,} dots moved, mean "
        f"{anti_disp['mean_displacement_all_px']} px"
    )

    arm_masks = {"fp2": pass_masks[1], "fp3": pass_masks[2], "anti1": anti1}
    arm_disp = {"fp2": pass_stats[1], "fp3": pass_stats[2], "anti1": anti_disp}

    print("[6/8] Writing rasters and re-reading every gate from disk...")
    existing_shas: set[str] = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS}
    ledger_rows: list[dict[str, str]] = []
    raw_kept_lines: list[str] = []
    fieldnames: list[str] = []
    header_line = ""
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
        raw_lines = LEDGER.read_text().splitlines()
        header_line = raw_lines[0] if raw_lines else ""
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if len(parsed) > 3 and parsed[2] == "SNAP" and parsed[1] == R1_ID and parsed[3] in OWN_VALUES:
                continue
            raw_kept_lines.append(line)

    for stale in list(RELEASES.glob(f"{R1_ID}-SNAPfp*")) + list(RELEASES.glob(f"{R1_ID}-SNAPanti1-*")):
        stale.unlink()

    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    cards = {k: v for k, v in cards.items() if not any(k.startswith(f"{R1_ID}-SNAP{v}-") for v in OWN_VALUES)}

    arms = {bpv.PARENT_ID: r0, R1_ID: r1, **arm_masks}
    built = []
    for value, n_passes, window, note, desc, card in SPECS:
        mask = arm_masks[value]
        spacing = bscarp.moved_dot_spacing_invariant(r1, mask)
        if not spacing["spacing_lock_holds_for_every_moved_dot"]:
            raise RuntimeError(f"Spacing lock violated for {value}: {spacing}")
        cum = cumulative_displacement(r1, mask)
        disp = dict(arm_disp[value])
        disp["passes"] = n_passes
        disp["field_sign"] = "negated (weakest response)" if value == "anti1" else "crest (strongest response)"
        disp["cumulative_vs_parent"] = cum
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
            "stay_on_h19_5": False,
            "n_dots_off_h19_5_after": int((mask & ~h19_5).sum()),
            "n_parent_dots_off_h19_5": int((r1 & ~h19_5).sum()),
        }
        rec["preregistration"] = "registry/preregistration_snap_r1_fixpoint.json"
        rec["leakage_canaries"] = {
            "passed": True,
            "max_symmetric_auc": max_auc,
            "w_field_channels": w_canaries,
            "edge_field_channels": edge_canaries,
        }
        rec["mechanism_card"] = card
        cards[rec["id"]] = card
        built.append((rec, disp, {"value": value, "desc": desc,
                                  "pred": PRE[value]["predicted_change"],
                                  "pred_range": PRE[value]["predicted_range"]}))
        print(
            f"      {value}: {rec['parent_diff']['pct_changed_moved']:.2f}% of dots changed, "
            f"net mean displacement {cum['mean_net_displacement_all_px']} px -> {rec['id']}"
        )

    print("[7/8] REPORT-ONLY diagnostics (holdout PROXY, blind SGMC, block CV)...")
    eval_report = bpv.evaluate_report_only_instruments(
        arms=arms, foot=foot, catalogue=catalogue, sgmc_path=verified["sgmc_faults_control"]
    )
    sgmc = lambda key: eval_report[key]["sgmc_control"]["dti"]  # noqa: E731
    sgmc_r0, sgmc_r1 = sgmc(bpv.PARENT_ID), sgmc(R1_ID)
    scarp1 = json.loads((RELEASES / f"{SCARP1PX_ID}.json").read_text())
    sgmc_scarp1 = scarp1["report_only_diagnostics"]["sgmc_control"]["dti"]
    print(f"      blind SGMC: R0 {sgmc_r0:.6f} | R1 {sgmc_r1:.6f} | scarp1px {sgmc_scarp1:.6f}")

    w_dti_r1 = bpv.weighted_expected_dti(r1, w_field)["dti"]
    for rec, disp, meta in built:
        rec["report_only_diagnostics"] = eval_report[meta["value"]]
        rec["parent_reference_diagnostics"] = eval_report[R1_ID]
        rec["r0_reference_diagnostics"] = eval_report[bpv.PARENT_ID]
        rec["scarp1px_reference_diagnostics"] = {
            "evidence_label": "PROXY",
            "source": f"releases/{SCARP1PX_ID}.json",
            "sgmc_control_dti": sgmc_scarp1,
        }
        rec["w_weighted_dti_MODEL"] = {
            "evidence_label": "MODEL",
            "dti_parent_r1": round(float(w_dti_r1), 6),
            "dti_arm": round(float(bpv.weighted_expected_dti(arm_masks[meta["value"]], w_field)["dti"]), 6),
            "caveat": "w under-weights off-H19-5 dots and its ranking has blind AUC 0.47 (IR-88-38); diagnostic only.",
        }
        s = sgmc(meta["value"])
        if meta["value"] == "anti1":
            recomm = (
                f"SIGN-FLIP CONTROL (never a slot): blind off-catalogue SGMC {s:.6f} PROXY vs "
                f"R1 {sgmc_r1:.6f} and scarp1px {sgmc_scarp1:.6f}. "
                + (
                    "The control scores at or above the crest arms, so the SGMC margin is a "
                    "displacement artefact -- do not promote the scarp family on proxy evidence."
                    if s >= sgmc_scarp1 else
                    "The control scores below the crest arms, so the direction of the 1 px move "
                    "carries information the blind control can see."
                )
                + " 100% of dots > 3 px (gate-clean); |live delta| < 0.01 is no evidence."
            )
        elif s >= sgmc_scarp1:
            recomm = (
                f"SLOT-CANDIDATE (dose extension): blind off-catalogue SGMC {s:.6f} PROXY at or "
                f"above scarp1px {sgmc_scarp1:.6f} and parent R1 {sgmc_r1:.6f}; 100% of dots > 3 px. "
                "A live receipt, not this proxy, decides promotion; hold unless the human has a "
                "scarp1px receipt to pair it with, and |live delta| < 0.01 is no evidence."
            )
        elif s > sgmc_r1:
            recomm = (
                f"HOLD: blind SGMC {s:.6f} PROXY above parent R1 {sgmc_r1:.6f} but below scarp1px "
                f"{sgmc_scarp1:.6f}; the preregistered rule keeps the single-pass arm ahead. "
                "Diagnostic dose point only; no slot."
            )
        else:
            recomm = (
                f"HOLD: blind SGMC {s:.6f} PROXY does not exceed parent R1 {sgmc_r1:.6f}; the "
                "preregistered decision rule parks this arm. Diagnostic only; no slot."
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
                    "edge_scarp_pot percentile field (0.42 b19 det_elev_slope + 0.23 b12 "
                    "det_elev Hessian ridge + 0.20 b18 iso_grav_anom_hg + 0.15 b3 tmi_hg); "
                    f"1.0 px window; {disp['passes']} pass(es); field sign "
                    f"{disp['field_sign']}; spacing lock min_sep 2.8 px (>=2.8284 px at "
                    "placement); stay_on_h19_5=False; no ranking model, no RNG"
                ),
                "receipt_score": "",
                "receipt_date": "",
                "description": meta["desc"],
                "recommendation": (
                    recomm
                    + f" SGMC {s:.6f} PROXY (R1 {sgmc_r1:.6f}, R0 {sgmc_r0:.6f}, scarp1px "
                    f"{sgmc_scarp1:.6f}); holdout PROXY structurally 0.0 (IR-88-20); 12 km CV "
                    f"{eval_report[meta['value']]['block_density_cv']['cv_12km_120px_interior']}; "
                    f"net mean displacement {disp['cumulative_vs_parent']['mean_net_displacement_all_px']} px."
                ),
            }
        )

    if fieldnames:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        for row in ledger_rows:
            if row.get("axis") == "SNAP" and row.get("parent") == R1_ID and row.get("value") in OWN_VALUES:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        body = buf.getvalue().rstrip("\n")
        with LEDGER.open("w", newline="") as fh:
            fh.write(header_line + "\n")
            for line in raw_kept_lines:
                fh.write(line + "\n")
            if body:
                fh.write(body + "\n")
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")

    print("[8/8] Writing the axis report...")
    report = {
        "session_date": "2026-10-23",
        "axis": "SNAP",
        "parent_r1": R1_ID,
        "preregistration": "registry/preregistration_snap_r1_fixpoint.json",
        "provided_bands_only": True,
        "external_lidar_used": False,
        "leakage_canaries": {"passed": True, "max_symmetric_auc": max_auc},
        "pass_ladder": pass_stats,
        "sgmc_reference": {
            "r0": sgmc_r0,
            "r1": sgmc_r1,
            "scarp1px_1px_single_pass": sgmc_scarp1,
            "scarp2px_2px_single_pass": "see releases/"
            "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705-SNAPscarp2px-20261023-c003d7d7.json",
        },
        "variants": [json.loads((RELEASES / f"{rec['id']}.json").read_text()) for rec, _, _ in built],
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    print("\nSNAP-R1-FIXPOINT REPORT-ONLY SUMMARY (PROXY/MODEL, never a score)")
    for rec, disp, meta in built:
        d = eval_report[meta["value"]]
        print(
            f"  {rec['value']:<6} SGMC {d['sgmc_control']['dti']:.6f} "
            f"(R1 {sgmc_r1:.6f} / scarp1px {sgmc_scarp1:.6f}) | holdout "
            f"{d['holdout_proxy']['dti']:.6f} | CV12 "
            f"{d['block_density_cv']['cv_12km_120px_interior']} | changed "
            f"{rec['parent_diff']['pct_changed_moved']:.2f}% | {meta['pred']}"
        )
    print(f"Elapsed {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
