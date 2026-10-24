#!/usr/bin/env python3
"""AXIS = MASS on the gate-clean parent R1 (``PRUNEp3px``) — three dose-matched arms.

Session choice (Brief v2 §5: "Do not prompt me over choosing an Axis for the session,
pick your own session"): **AXIS = MASS**, parent **R1**.

Why this (parent, axis) pair is not a repeat
--------------------------------------------
The 47-row ledger already contains two MASS families, both on R0: ``m10minus/m10plus/
m20minus`` (ranked by an ad-hoc ``0.6*clip(d_cat/50)+0.4*uniform`` score that the PR17
audit showed was a catalogue-collar artefact) and ``r10minus/r10plus/r10swap`` (ranked by
the parent's own exact marginal DTI). No MASS arm exists on a gate-clean parent, so
``(R1, MASS, *)`` is entirely unbuilt. R0 cannot host a non-PRUNE arm at all: it keeps
2,171 dots at ``2 < d_cat <= 3 px`` (IR-88-33/36/43/47).

The question this family answers
--------------------------------
R0's measured mass curve (blind SGMC: 10% drop ``-0.0080``, 10% add ``+0.0029``) is
confounded: R0's lowest-marginal tail contains collar dots that sit in the damage zone of
mapped faults and are therefore credit-rich once catalogue pixels are masked. R1 replaced
those dots with the 2,171 highest-marginal un-emitted candidates. If the mass optimum moves
with the parent, mass stays live; if the ordering and magnitudes reproduce, the mass curve
is a property of the H19-5 + 2.8 px-thinning recipe and MASS is closed for the remaining
slots.

Arms (dose fixed at 10% = 3,765 dots, as Brief §5 mandates) — ALL preregistered in
``registry/preregistration_mass_r1.json`` before anything was computed:

    value        operation                                    N
    r1m10minus   drop the 3,765 lowest exact-marginal dots    33,889
    r1m10plus    add the 3,765 next-ranked un-emitted dots    41,419
    r1m10swap    drop 3,765 lowest + add 3,765 next-ranked    37,654 (count fixed)

Every arm keeps ``d_cat > 3 px`` on every emitted dot (candidates are restricted to that
pool, and the writer asserts ``min_catalogue_px = 3.0``), so all three files are
slot-eligible with no gate waiver.

Determinism / provenance: 15 SHA-256 manifest pins re-verified, R0 rebuilt byte-exactly,
R1 re-derived and both published twins SHA-asserted in-run, fixed seed, git SHA logged,
every raster re-read from disk and independently re-validated. Idempotent reruns replace
ONLY this family's rows, files and cards. No competition page is contacted and nothing is
submitted; the human owns every upload.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_prune_variants as bpv  # noqa: E402
import build_snap_r1_variants as bsv  # noqa: E402

AXIS = "MASS"
FRACTION = 0.10
SEED = 20261023
FIXED_DATE = "20261023"
OWN_VALUES = ("r1m10minus", "r1m10plus", "r1m10swap")
PARENT_ID = bsv.R1_ID
PARENT_SHA_NAN = bsv.R1_SHA_NAN
PARENT_SHA_ZEROS = bsv.R1_SHA_ZEROS
MIN_CATALOGUE_PX = 3.0
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_mass_r1.json"
REPORT = ROOT / "evidence" / "mass_r1_axis_report.json"

RANKING_BASIS = (
    "exact iterative marginal expected-DTI under the pinned label-free physical field w "
    "(parent's own ranking, rebuilt: R1 stores no per-dot score)"
)

# Form notes (<=140 chars each; {sha8} is filled by the writer).
NOTES = {
    "r1m10minus": "R1(PRUNEp3px); MASS -3765 lowest exact-marginal dots 37654->33889; pred {pred} MODEL",
    "r1m10plus": "R1(PRUNEp3px); MASS +3765 next-ranked un-emitted dots d_cat>3px ->41419; pred {pred} MODEL",
    "r1m10swap": "R1(PRUNEp3px); MASS swap 3765 lowest for 3765 next-ranked, count fixed 37654; pred {pred} MODEL",
}

# Ledger descriptions (one line each, factual, no score language).
DESCRIPTIONS = {
    "r1m10minus": (
        "Gate-clean MASS drop: removes the 3,765 lowest exact-marginal-DTI dots from R1; "
        "tests whether R0's measured drop loss was a collar artefact."
    ),
    "r1m10plus": (
        "Gate-clean MASS add: spends the identical 3,765-dot dose on the next-ranked un-emitted "
        "H19-5 candidates after R1's own 2,171-dot refill; direct saturation test."
    ),
    "r1m10swap": (
        "Gate-clean MASS swap at fixed count: isolates ranking quality from mass with the collar "
        "confound removed."
    ),
}



def _recommendation(value: str, sgmc_delta: float, w_delta: float) -> str:
    """Post-build decision text. A PROXY delta is never a score and never a promotion."""
    if sgmc_delta >= 0.01:
        verdict = ("blind off-catalogue SGMC delta >= +0.01 PROXY: the only evidence class that "
                   "could queue it; still requires a live receipt")
    elif sgmc_delta > 0.0:
        verdict = (f"blind off-catalogue SGMC delta {sgmc_delta:+.5f} PROXY is positive but far below "
                   "the 0.01 no-evidence floor")
    else:
        verdict = (f"blind off-catalogue SGMC delta {sgmc_delta:+.5f} PROXY is negative")
    return (
        f"NOT QUEUED ({verdict}). Built and gate-clean as a controlled test of whether the mass "
        f"optimum moves with the parent; in-sample w-model delta {w_delta:+.5f} MODEL (optimistic, "
        "w both ranks and scores). Published for the mass-curve closure, not for a slot."
    )


def _nearest_parent_distance(parent_mask: np.ndarray, added_mask: np.ndarray) -> dict:
    py, px = np.nonzero(parent_mask)
    ay, ax = np.nonzero(added_mask)
    if len(ay) == 0:
        return {"n_added": 0}
    d, _ = cKDTree(np.column_stack([py, px])).query(np.column_stack([ay, ax]))
    return {
        "n_added": int(len(ay)),
        "mean_px": round(float(d.mean()), 3),
        "median_px": round(float(np.median(d)), 3),
        "p90_px": round(float(np.quantile(d, 0.90)), 3),
        "frac_within_3px_of_a_parent_dot": round(float((d <= 3.0).mean()), 4),
    }


def _portable_delta(diag: dict, parent_diag: dict) -> dict:
    """Paired holdout / SGMC / CV deltas expressed against THIS parent (R1)."""
    return {
        "holdout_proxy_dti": diag["holdout_proxy"]["dti"],
        "holdout_proxy_delta_vs_parent": round(
            diag["holdout_proxy"]["dti"] - parent_diag["holdout_proxy"]["dti"], 6
        ),
        "holdout_withheld_positives": diag["holdout_proxy"]["withheld_positives"],
        "sgmc_off_catalogue_dti": diag["sgmc_control"]["dti"],
        "sgmc_delta_vs_parent": round(
            diag["sgmc_control"]["dti"] - parent_diag["sgmc_control"]["dti"], 6
        ),
        "cv_12km": diag["block_density_cv"]["cv_12km_120px_interior"],
        "cv_12km_parent": parent_diag["block_density_cv"]["cv_12km_120px_interior"],
    }


def main() -> int:
    t0 = time.time()
    pre = json.loads(PREREG.read_text(encoding="utf-8"))
    assert pre["frozen_before_build"] is True
    arms_pre = pre["arms"]
    assert set(arms_pre) == set(OWN_VALUES), "prereg arms do not match OWN_VALUES"
    n_dose = int(pre["fixed_dose"]["n_dots"])
    assert n_dose == int(round(FRACTION * 37_654))

    print("[1/7] Verifying the 15 SHA-256 manifest pins ...")
    verified = bpv.verify_manifest()
    print(f"      {len(verified)}/{len(verified)} pins verified (sha256 + byte length).")

    print("[2/7] Rebuilding parent R0 from the lineage recipe (byte-exact) ...")
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    assert int(r0.sum()) == 37_654
    assert lin["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS
    assert lin["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    print(f"      R0 OK: {int(r0.sum()):,} dots | zeros={lin['rebuilt_zeros_sha256'][:12]}... "
          f"| nan={lin['rebuilt_nan_sha256'][:12]}...")

    print("[3/7] Rebuilding the label-free corroboration field w + leakage canaries ...")
    w_field, canaries = bpv.build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    max_auc = max(canaries.values())
    if max_auc > 0.90:
        raise RuntimeError(f"Leakage canary tripped: symmetric AUC {max_auc:.4f} > 0.90")
    print(f"      canaries PASS ({len(canaries)} channels, max symmetric AUC {max_auc:.4f})")

    print("[4/7] Re-deriving parent R1 = PRUNEp3px and asserting both published twins ...")
    r1 = bsv.reconstruct_r1(lin, w_field, verified)
    n_parent = int(r1.sum())
    assert n_parent == 37_654
    if float(d_cat[r1].min()) <= MIN_CATALOGUE_PX + 1e-9:
        raise RuntimeError(f"R1 is not gate-clean: min d_cat {d_cat[r1].min():.4f} px")

    base_terms = bpv.weighted_expected_dti(r1, w_field)
    r0_terms = bpv.weighted_expected_dti(r0, w_field)
    print(f"      R1 w-model: DTI={base_terms['dti']:.6f} T={base_terms['T']:.1f} "
          f"S={base_terms['S']:.0f} M={base_terms['M']:.1f} "
          f"(R0 {r0_terms['dti']:.6f})")

    print(f"[5/7] Allocating 3 AXIS=MASS arms at the fixed 10% dose ({n_dose:,} dots) ...")
    # Candidate pool: parent detector support that is un-emitted AND outside the 3 px collar.
    cand_pool = h19_5 & ~r1 & (d_cat > MIN_CATALOGUE_PX)
    print(f"      candidate pool (H19-5 & ~R1 & d_cat>3px): {int(cand_pool.sum()):,} px")

    t = time.time()
    m_minus = bpv.select_exact_marginal_dti_drop(
        base_mask=r1, drop_pool_mask=r1, w=w_field, n_drop=n_dose
    )
    print(f"      r1m10minus greedy drop: {time.time() - t:.0f}s -> {int(m_minus.sum()):,} dots")

    t = time.time()
    m_plus = bpv.select_exact_marginal_dti_add(
        base_mask=r1, cand_mask=cand_pool, w=w_field, n_add=n_dose
    )
    print(f"      r1m10plus greedy add:  {time.time() - t:.0f}s -> {int(m_plus.sum()):,} dots")

    t = time.time()
    m_swap = bpv.select_exact_marginal_dti_add(
        base_mask=m_minus, cand_mask=cand_pool, w=w_field, n_add=n_dose
    )
    print(f"      r1m10swap greedy add:  {time.time() - t:.0f}s -> {int(m_swap.sum()):,} dots")

    assert int(m_minus.sum()) == n_parent - n_dose == 33_889
    assert int(m_plus.sum()) == n_parent + n_dose == 41_419
    assert int(m_swap.sum()) == n_parent == 37_654
    assert not (m_swap & ~m_minus & r1).any(), "swap must not re-add dropped parent dots"
    for name, mask in (("r1m10minus", m_minus), ("r1m10plus", m_plus), ("r1m10swap", m_swap)):
        dmin = float(d_cat[mask].min())
        if dmin <= MIN_CATALOGUE_PX + 1e-9:
            raise RuntimeError(f"{name}: dot at {dmin:.4f} px from catalogue breaches the 3 px rule")
        if int((mask & catalogue).sum()) != 0:
            raise RuntimeError(f"{name}: mass on catalogue pixels")

    w_model = {}
    for name, mask in (("r1m10minus", m_minus), ("r1m10plus", m_plus), ("r1m10swap", m_swap)):
        tm = bpv.weighted_expected_dti(mask, w_field)
        w_model[name] = {
            "dti": round(tm["dti"], 6),
            "delta_vs_parent_r1": round(tm["dti"] - base_terms["dti"], 6),
            "T": round(tm["T"], 3),
            "S": float(tm["S"]),
            "M": round(tm["M"], 3),
            "denom": round(tm["denom"], 3),
            "note": "IN-SAMPLE and optimistic: w both ranks and scores this arm (PROXY field).",
        }
        print(f"      w-model {name}: DTI={tm['dti']:.6f} "
              f"(delta vs R1 {tm['dti'] - base_terms['dti']:+.6f})")

    print("[6/7] Writing GeoTIFFs (NaN + zeros twins), re-reading from disk, gates ...")
    existing_rows: list[dict[str, str]] = []
    raw_kept_lines: list[str] = []
    fieldnames: list[str] = []
    header_line = ""
    existing_shas: set[str] = {
        bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN, PARENT_SHA_NAN, PARENT_SHA_ZEROS
    }
    if LEDGER.is_file():
        with LEDGER.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                if (
                    row.get("axis") == AXIS
                    and row.get("parent") == PARENT_ID
                    and row.get("value") in OWN_VALUES
                ):
                    continue  # idempotent re-run replaces only this family
                existing_rows.append(row)
                for k in ("sha256", "sha256_zeros"):
                    if row.get(k):
                        existing_shas.add(row[k])
        raw_lines = LEDGER.read_text(encoding="utf-8").splitlines()
        header_line = raw_lines[0] if raw_lines else ""
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if (
                len(parsed) > 3
                and parsed[2] == AXIS
                and parsed[1] == PARENT_ID
                and parsed[3] in OWN_VALUES
            ):
                continue
            raw_kept_lines.append(line)
    for value in OWN_VALUES:
        for stale in RELEASES.glob(f"{PARENT_ID}-{AXIS}{value}-*"):
            stale.unlink()

    masks = {"r1m10minus": m_minus, "r1m10plus": m_plus, "r1m10swap": m_swap}
    built: dict[str, dict] = {}
    for value in OWN_VALUES:
        rec = bpv.write_and_verify_variant(
            mask=masks[value],
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=r1,
            axis=AXIS,
            value=value,
            note_template=NOTES[value].format(pred=arms_pre[value]["preregistered_prediction"],
                                              sha8="{sha8}"),
            existing_shas=existing_shas,
            parent_id=PARENT_ID,
            parent_sha_zeros=PARENT_SHA_ZEROS,
            parent_sha_nan=PARENT_SHA_NAN,
            date=FIXED_DATE,
            min_catalogue_px=MIN_CATALOGUE_PX,
            pct_basis="max",
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])
        rec["parent_rebuild_verified"] = {
            "sha256_nan": PARENT_SHA_NAN, "sha256_zeros": PARENT_SHA_ZEROS,
            "source": "reconstructed in-run by build_snap_r1_variants.reconstruct_r1 "
                      "and asserted against the published ledger twins",
        }
        rec["leakage_canaries"] = {
            "passed": True, "max_symmetric_auc": max_auc, "channels": canaries,
        }
        rec["w_model"] = w_model[value]
        rec["preregistered_prediction"] = arms_pre[value]["preregistered_prediction"]
        rec["preregistered_range"] = arms_pre[value]["preregistered_range"]
        added, removed = masks[value] & ~r1, r1 & ~masks[value]
        rec["saturation_diagnostic_added_dots"] = _nearest_parent_distance(r1, added)
        rec["added_dots"] = {
            "n": int(added.sum()),
            "min_d_cat_px": round(float(d_cat[added].min()), 3) if added.any() else None,
            "mean_d_cat_px": round(float(d_cat[added].mean()), 3) if added.any() else None,
            "mean_w": round(float(w_field[added].mean()), 6) if added.any() else None,
        }
        rec["removed_dots"] = {
            "n": int(removed.sum()),
            "mean_d_cat_px": round(float(d_cat[removed].mean()), 3) if removed.any() else None,
            "mean_w": round(float(w_field[removed].mean()), 6) if removed.any() else None,
            "mean_nn_spacing_px": (
                round(float(cKDTree(np.column_stack(np.nonzero(r1 & ~removed)))
                            .query(np.column_stack(np.nonzero(removed)))[0].mean()), 3)
                if removed.any() else None
            ),
        }
        rec["parent_dots_mean_w"] = round(float(w_field[r1].mean()), 6)
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        built[value] = rec
        pd = rec["parent_diff"]
        print(f"      {rec['id']}\n        dots={rec['n_dots']:,} | added={pd['n_added']:,} "
              f"removed={pd['n_removed']:,} | changed={pd['pct_changed_moved']:.2f}% (max basis) "
              f"| min d_cat={pd['min_dist_catalogue_px']:.4f} px")

    print("[7/7] REPORT-ONLY instruments (catalogue holdout PROXY, SGMC control, block CV) ...")
    eval_arms = {bpv.PARENT_ID: r0, PARENT_ID: r1}
    for value in OWN_VALUES:
        eval_arms[built[value]["id"]] = masks[value]
    eval_report = bpv.evaluate_report_only_instruments(
        arms=eval_arms, foot=foot, catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )
    parent_diag = eval_report[PARENT_ID]
    r0_diag = eval_report[bpv.PARENT_ID]

    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    cards = {
        k: v for k, v in cards.items()
        if not any(k.startswith(f"{PARENT_ID}-{AXIS}{val}-") for val in OWN_VALUES)
    }
    new_rows = []
    for value in OWN_VALUES:
        rec = built[value]
        diag = eval_report[rec["id"]]
        port = _portable_delta(diag, parent_diag)
        rec["report_only_diagnostics"] = diag
        rec["parent_reference_diagnostics"] = parent_diag
        rec["r0_reference_diagnostics"] = r0_diag
        rec["portable_report_only_vs_parent"] = port
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")

        card = {
            "parent": PARENT_ID,
            "axis": AXIS,
            "value": value,
            "preregistered_prediction": arms_pre[value]["preregistered_prediction"],
            "preregistered_range": arms_pre[value]["preregistered_range"],
            "hypothesis": arms_pre[value]["mechanism"],
            "mechanism": arms_pre[value]["operation"] + ". " + arms_pre[value]["mechanism"],
            "non_fault_mimic": arms_pre[value]["non_fault_mimic"],
            "predicted_sign_size": arms_pre[value]["predicted_sign_size"],
            "falsifier": arms_pre[value]["falsifier"],
            "post_build_w_model_delta": f"{w_model[value]['delta_vs_parent_r1']:+.6f}",
            "post_build_report_only": {
                "holdout_proxy_delta_vs_parent": port["holdout_proxy_delta_vs_parent"],
                "sgmc_off_catalogue_dti": port["sgmc_off_catalogue_dti"],
                "sgmc_delta_vs_parent": port["sgmc_delta_vs_parent"],
                "cv_12km": port["cv_12km"],
                "cv_12km_parent": port["cv_12km_parent"],
            },
            "evidence_discipline": (
                "Every number above is PROXY or MODEL. The blind SGMC control orders arms; it is "
                "not a score. A live |delta| < 0.01 is no evidence (Brief §5)."
            ),
        }
        cards[rec["id"]] = card

        pred = arms_pre[value]["preregistered_prediction"]
        pd = rec["parent_diff"]
        new_rows.append({
            "id": rec["id"],
            "parent": PARENT_ID,
            "axis": AXIS,
            "value": value,
            "n_dots": str(rec["n_dots"]),
            "pct_changed": f"{pd['pct_changed_moved']:.2f}",
            "sha256": rec["sha256"],
            "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT",
            "predicted_change": f"MODEL:{pred}",
            "predicted_range": arms_pre[value]["preregistered_range"],
            "ranking_basis": RANKING_BASIS,
            "receipt_score": "",
            "receipt_date": "",
            "description": (
                f"{DESCRIPTIONS[value]} Preregistered {pred} MODEL; post-build w-model delta "
                f"{w_model[value]['delta_vs_parent_r1']:+.4f} vs R1 (in-sample, optimistic); "
                f"holdout PROXY {diag['holdout_proxy']['dti']:.6f} "
                f"(delta vs R1 {port['holdout_proxy_delta_vs_parent']:+.6f}, "
                f"n={port['holdout_withheld_positives']}); SGMC off-cat {port['sgmc_off_catalogue_dti']:.6f} "
                f"vs R1 {parent_diag['sgmc_control']['dti']:.6f} "
                f"(delta {port['sgmc_delta_vs_parent']:+.6f}); CV12km {port['cv_12km']:.4f} vs R1 "
                f"{port['cv_12km_parent']:.4f}; min d_cat {pd['min_dist_catalogue_px']:.4f} px "
                f"({pd['dots_le_3px']:,} dots <=3 px)."
            ),
            "recommendation": _recommendation(
                value, port["sgmc_delta_vs_parent"], w_model[value]["delta_vs_parent_r1"]
            ),
        })

    # ---- ledger write (kept rows byte-verbatim; only this family's rows re-serialised) ----
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    for row in new_rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    body = buf.getvalue().rstrip("\n")
    with LEDGER.open("w", newline="", encoding="utf-8") as fh:
        fh.write(header_line + "\n")
        for line in raw_kept_lines:
            fh.write(line + "\n")
        fh.write(body + "\n")
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")

    summary = {
        "schema": "gems88.mass-r1-axis-report.v1",
        "session_date": "2026-10-23",
        "axis": AXIS,
        "preregistration": "registry/preregistration_mass_r1.json",
        "parent": {
            "id": PARENT_ID,
            "n_dots": n_parent,
            "sha256_nan": PARENT_SHA_NAN,
            "sha256_zeros": PARENT_SHA_ZEROS,
            "min_d_cat_px": round(float(d_cat[r1].min()), 4),
            "w_model": {
                "dti": round(base_terms["dti"], 6),
                "T": round(base_terms["T"], 3),
                "S": float(base_terms["S"]),
                "M": round(base_terms["M"], 3),
            },
        },
        "r0_reference": {
            "id": bpv.PARENT_ID,
            "rebuilt_zeros_sha256": lin["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lin["rebuilt_nan_sha256"],
            "n_dots": int(r0.sum()),
            "w_model_dti": round(r0_terms["dti"], 6),
        },
        "verified_inputs": len(verified),
        "leakage_canaries": {"passed": True, "max_symmetric_auc": max_auc, "channels": canaries},
        "ranking_definition": pre["ranking_definition"],
        "dose": {"fraction": FRACTION, "n_dots": n_dose},
        "candidate_pool_px": int(cand_pool.sum()),
        "preregistered_predictions": {k: v["preregistered_prediction"] for k, v in arms_pre.items()},
        "w_model_deltas": w_model,
        "report_only": eval_report,
        "portable_report_only_vs_parent": {
            v: _portable_delta(eval_report[built[v]["id"]], parent_diag) for v in OWN_VALUES
        },
        "variants": [{k: v for k, v in built[name].items()} for name in OWN_VALUES],
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
        "external_data": "none; 15 pinned manifest inputs only",
    }
    REPORT.write_text(json.dumps(summary, indent=2) + "\n")

    print("\n=== SUMMARY: AXIS=MASS on R1 (all report-only values are PROXY/MODEL, never scores) ===")
    print(f"  parent R1  N={n_parent:,}  SGMC={parent_diag['sgmc_control']['dti']:.6f}  "
          f"CV12km={parent_diag['block_density_cv']['cv_12km_120px_interior']:.4f}")
    for value in OWN_VALUES:
        rec = built[value]
        port = summary["portable_report_only_vs_parent"][value]
        print(f"  {rec['id']}\n    N={rec['n_dots']:,} changed={rec['parent_diff']['pct_changed_moved']:.2f}% "
              f"min_dcat={rec['parent_diff']['min_dist_catalogue_px']:.4f}px | "
              f"SGMC={port['sgmc_off_catalogue_dti']:.6f} (Δ{port['sgmc_delta_vs_parent']:+.6f}) | "
              f"holdout Δ{port['holdout_proxy_delta_vs_parent']:+.6f} | "
              f"CV12km={port['cv_12km']:.4f} | w-model Δ{w_model[value]['delta_vs_parent_r1']:+.6f}")
    print(f"\n  ledger rows added: {len(new_rows)} (total now "
          f"{len(raw_kept_lines) + len(new_rows)}); report: evidence/mass_r1_axis_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
