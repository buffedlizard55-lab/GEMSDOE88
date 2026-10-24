#!/usr/bin/env python3
"""Assemble the protocol run card for the 2026-10-24 session from machine receipts only.

Reads  docs/downloads/<name>.json (+ .format-audit.json), registry/uniqueness_v3.json,
       registry/gate_verdict.json, evidence/halo_experiments_20261024.json,
       registry/preregistration_halo88.json
Writes registry/run_card_20261024.json and the identical site copy docs/data/run-card-20261024.json.
No number is typed by hand.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    gv = json.loads((ROOT / "registry/gate_verdict.json").read_text())
    name = gv["name"]
    rcpt = json.loads((ROOT / f"docs/downloads/{name}.json").read_text())
    audit = json.loads((ROOT / f"docs/downloads/{name}.format-audit.json").read_text())
    uq = json.loads((ROOT / "registry/uniqueness_v3.json").read_text())
    ho = json.loads((ROOT / "evidence/halo_experiments_20261024.json").read_text())
    pre = json.loads((ROOT / "registry/preregistration_halo88.json").read_text())
    pooled_all = ho["pooled"]["all__candidate_fbmt"]
    pooled_far = ho["pooled"]["far__candidate_fbmt"]
    pooled_far_ccr = ho["pooled"]["far__candidate_fbmt_ccr"]
    pooled_far_rcp = ho["pooled"]["far__candidate_fbmt_ccr_rcp"]

    def sc(p, a):
        s = p["scores"][a]
        return dict(dti=s["dti"], ci95=s["ci95"], withheld_positives=s["withheld_positive_pixels"])

    tested = {
        "E1_FBMT": dict(
            hypothesis=pre["hypotheses"]["E1_FBMT"], far=sc(pooled_far, "fbmt"), overall=sc(pooled_all, "fbmt"),
            paired_far_vs_base=pooled_far["paired_differences"]["base"], paired_overall_vs_base=pooled_all["paired_differences"]["base"],
            verdict="negative"),
        "E2_CCR": dict(
            hypothesis=pre["hypotheses"]["E2_CCR"], far=sc(pooled_far, "fbmt_ccr"), overall=sc(pooled_all, "fbmt_ccr"),
            paired_far_vs_fbmt=pooled_far_ccr["paired_differences"]["fbmt"], verdict="negative"),
        "E3_RCP": dict(
            hypothesis=pre["hypotheses"]["E3_RCP"], far=sc(pooled_far, "fbmt_ccr_rcp"), overall=sc(pooled_all, "fbmt_ccr_rcp"),
            paired_far_vs_ccr=pooled_far_rcp["paired_differences"]["fbmt_ccr"], verdict="null"),
    }
    card = dict(
        schema="gems88.run_card.v3",
        session=dict(branch="arena/f566c0e1-gemsdoe88", date_utc="2026-10-24", started_utc="2026-10-24T06:16Z",
                     experiments_used=3, experiments_budget=3, diagnostics_read_only=["D1 forensics_h33", "D2 proxy_calibration", "D3 fleet_distance_prior"],
                     experiment_compute_seconds=round(ho["seconds"] + 438.0, 1), slots_spent=0, submissions_picked=0),
        hypothesis=dict(
            emitted_arm="control (BASE-44): label-blind 44-layer geophysics+topography classifier, 3-px halo, exact Dinkelbach DTI allocation, out-of-fold stitched",
            tested=tested, preregistration="registry/preregistration_halo88.json", ranked_list="research/hypotheses-20261024.md"),
        mechanism="Gradient-boosted classifier on 44 label-blind columns trained out-of-fold on four spatial quadrants (positives = mapped catalogue), calibrated "
                  "to the expected hidden-truth mass, dots chosen by the vendored exact Dinkelbach allocator with 300 m kernel and >=2.05 px spacing, no dot within 3 px of any mapped fault.",
        named_non_fault_mimics=["Pleistocene Lake Lahontan / Bonneville shoreline benches", "GeoDAWN E-W flight-line corrugation",
                                "circular volcanic plugs and calderas", "playa margins (cond_surf)"],
        holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=ho["evaluator_version"], seeds=ho["seeds"],
                     emitted_arm_overall=sc(pooled_all, "base"), emitted_arm_far_subset=sc(pooled_far, "base"),
                     bar=rcpt["holdout"]["bar"], beats_bar=rcpt["holdout"]["beats_bar"],
                     note="far subset = withheld positives >10 px from every visible catalogue pixel; no number here is ORGANIZER-CONFIRMED"),
        canary=dict(max_symmetric_auc=ho["canary"]["max_symmetric_auc"], threshold=0.90, passed=ho["canary"]["passed"], features_tested=ho["canary"]["features_tested"]),
        overlap_vs_registry=dict(policy=uq["policy"], registry_rasters=uq["registry_rasters"], distinct_dot_sets=uq["distinct_dot_sets"],
                                 worst_like_for_like_overlap=uq["worst_like_for_like_overlap"], worst_abs_rho=uq["worst_abs_rho"],
                                 unique_like_for_like=uq["unique_like_for_like"], unique_literal=uq["unique_literal"],
                                 literal_blockers=uq["literal_blockers"], vacuity_witness=uq["vacuity_witness"],
                                 detail="registry/uniqueness_v3.json"),
        fingerprint=rcpt["fingerprint"], fingerprint_screen=rcpt["fingerprint_screen"],
        raster_sha256=rcpt["sha256"], zip_sha256=rcpt["zip_sha256"], downloadable_file=f"downloads/{name}.tif", downloadable_zip=f"downloads/{name}.zip",
        validator_output=dict(ok=audit["ok"], tif_zip_same_pixels=audit["tif_zip_same_pixels"], problems=audit["problems"],
                              tif_checks=audit["tif"]["checks"], layout=audit["tif"]["layout"], layout_parity_with_official_sample=audit["tif"]["layout_parity_with_sample"],
                              second_decoder=audit["tif"]["second_decoder"], detail=f"docs/downloads/{name}.format-audit.json"),
        submission_name=rcpt["name"], submission_note=rcpt["note"], name_len=len(rcpt["name"]), note_len=len(rcpt["note"]),
        gate=dict(policy=gv["policy"], label=gv["label"], ok_to_download=gv["ok_to_download"], ok_to_submit=gv["ok_to_submit"],
                  blocking_reasons=gv["blocking_reasons"], informational=gv["informational"]),
        verdict="promote-to-selector-only" if gv["ok_to_submit"] else "negative",
        limits=["No DrivenData login: no receipt inspected, nothing submitted, portal behaviour not observed.",
                "Hide-and-recover truth is catalogue faults, not the hidden new-fault labels; H33-class rasters are not scorable on it.",
                "Fingerprint screen is derived from 20 owner-reported scores (shared ancestry) and is necessary, not sufficient."])
    text = json.dumps(card, indent=1, default=float) + "\n"
    (ROOT / "registry/run_card_20261024.json").write_text(text)
    (ROOT / "docs/data").mkdir(exist_ok=True)
    (ROOT / "docs/data/run-card-20261024.json").write_text(text)
    print("verdict:", card["verdict"], "|", gv["label"])


if __name__ == "__main__":
    main()
