#!/usr/bin/env python3
"""Re-audit the frozen H88-HGVC artifact (2026-10-24) under gate v4 (IR-88-118).

This is a *gate re-evaluation only*: no model is fit, no raster is generated,
moved, renamed or copied, and the historical v3 run card / gate verdict are
not modified. It re-opens the exact saved bytes
(SHA-256 ``d5329f31...``), re-validates portal format, re-reads the stored
canary + 8-fold holdout evidence from the original session ledgers, and
recomputes final-dot uniqueness against the registry as it exists today
(including the live-head GEMSDOE86..92 rasters cloned 2026-10-25 and this
session's SEPA candidate) with ``gate.decide_v4``.

The one evidence item not recomputable today is HGVC's pre-placement
*continuous surface* (not archived); its stored receipt value
(max |Spearman| = 0.208144 across 326 rasters, evidence
``docs/evidence/hgvc88_holdout_20261024.json`` + run card) is used and
labelled STORED-RECEIPT. Final-dot rank correlation is recomputed fresh
against every registry raster present today.

Exit codes: 0 = re-audit receipt written and internally consistent;
with ``--require-submit``, 2 unless ``ok_to_submit`` is True.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import grid as grid_mod  # noqa: E402
from gems88 import gate  # noqa: E402
from run_sepa88_experiment import collect_registry  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true")
    args = ap.parse_args(argv)

    rc = json.loads((ROOT / "registry/hgvc88_run_card.json").read_text(encoding="utf-8"))
    tif = ROOT / rc["download"]
    zip_p = ROOT / rc["zip_download"]
    if _sha256(tif) != rc["raster_sha256"] or _sha256(zip_p) != rc["zip_sha256"]:
        raise ValueError("HGVC saved bytes no longer match their run card SHA-256; refusing re-audit")

    g = grid_mod.load_grid(ROOT / "data/bridge")
    sample_path = ROOT / "data/bridge/sample_submission.tif"
    portal = gate.portal_validate(tif, sample_path, g.footprint)
    portal_zip = gate.portal_validate(zip_p, sample_path, g.footprint)
    if not (portal["ok"] and portal_zip["ok"] and portal["array_sha256"] == portal_zip["array_sha256"]):
        raise ValueError(f"HGVC portal re-validation failed: {portal['problems']} / {portal_zip['problems']}")

    can = json.loads((ROOT / "evidence/hgvc88_canaries.json").read_text(encoding="utf-8"))
    ho = json.loads((ROOT / "evidence/hgvc88_holdout_20261024.json").read_text(encoding="utf-8"))
    stored_cand = ho["pooled_overall"]["scores"]["exp03_hgvc_poe_conduit"]
    stored_delta = ho["pooled_overall"]["paired_differences"]["h88_adhr_incumbent"]
    if abs(stored_cand["dti"] - rc["holdout_dti"]["candidate_exp03"]["dti"]) > 1e-12:
        raise ValueError("stored HGVC holdout ledger disagrees with its run card")
    canary_passed = bool(can["passed"] and can["max_symmetric_auc"] <= 0.90
                         and can.get("zero_test_quadrant_leakage_scramble_equal") is True)
    fingerprint = rc["validator_output"]["fingerprint"]
    holdout_beats_bar = bool(stored_delta["ci95"][0] > 0 and gate.fingerprint_screen(fingerprint))

    entries = [(lbl, p) for lbl, p in collect_registry(ROOT) if p.resolve() != tif.resolve()
               and "hgvc88" not in p.name]
    print(f"Re-auditing HGVC vs {len(entries)} registry rasters (v4)...", flush=True)
    uq = gate.uniqueness_report(tif, entries, g.footprint, surface=None)
    stored_surface_rho = rc["correlation_overlap_vs_registry"]["surface_preplacement_max_abs_spearman"]
    uq_for_decide = {**uq,
                     "registry_complete": bool(uq["missing"] == 0 and uq["registry_rasters"] >= 200),
                     "surface_checked": True}
    used_names = set()
    for p_rc in (ROOT / "registry").glob("*.json"):
        if "hgvc" in p_rc.name:
            continue
        try:
            d = json.loads(p_rc.read_text(encoding="utf-8"))
            if isinstance(d, dict) and isinstance(d.get("submission_name"), str):
                used_names.add(d["submission_name"])
        except Exception:
            pass
    gv = gate.decide_v4(portal=portal, uniqueness=uq_for_decide, canary_passed=canary_passed,
                        holdout_beats_bar=holdout_beats_bar, name=rc["submission_name"],
                        note=rc["submission_note"], used_names=used_names, receipt_sha_matches=True)
    # The stored pre-placement surface checked rho only; certify it separately.
    if stored_surface_rho > 0.90:
        gv["ok_to_submit"] = False
        gv["eligible_for_selector"] = False
        gv["blocking_reasons"] = list(gv["blocking_reasons"]) + [
            f"UNIQUENESS: stored pre-placement surface |rho| = {stored_surface_rho} > 0.90"]
        gv["label"] = "OK TO DOWNLOAD — DO NOT SUBMIT"

    receipt = {
        "schema": "gems88.hgvc88.gate_v4_reaudit.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subject": {"lane": "H88-HGVC", "built_utc": rc["generated_utc"],
                    "tif": rc["download"], "zip": rc["zip_download"],
                    "sha256": rc["raster_sha256"], "zip_sha256": rc["zip_sha256"],
                    "dots": rc["validator_output"]["positive_dots"],
                    "filename_marker_note": ("The 'DO-NOT-SUBMIT' suffix in the filename is the historical "
                                             "v3 (IR-88-86) marker from build day. It is retained byte-for-byte; "
                                             "this v4 re-audit supersedes that policy reading (IR-88-118). The "
                                             "DrivenData portal name/note are separate metadata below.")},
        "historical_v3_verdict_unchanged": {"verdict": rc["verdict"], "ok_to_submit": rc["ok_to_submit"],
                                            "gate": "registry/hgvc88_gate_v3.json (not modified)"},
        "policy": gate.POLICY_VERSION_V4,
        "ok_to_download": gv["ok_to_download"], "ok_to_submit": gv["ok_to_submit"],
        "label": gv["label"], "blocking_reasons": gv["blocking_reasons"], "informational": gv["informational"],
        "human_step_remaining": gv["human_step_remaining"],
        "portal_revalidation": {"tif_ok": portal["ok"], "zip_ok": portal_zip["ok"],
                                "array_sha256": portal["array_sha256"],
                                "values_in_0_1": bool(portal["checks"]["portal_range_check_nan_strict"]),
                                "no_nan_anywhere": bool(portal["checks"]["all_finite"]),
                                "crs_shape_transform_match": bool(portal["checks"]["crs_epsg_32611"]
                                                                  and portal["checks"]["shape_matches_sample"]
                                                                  and portal["checks"]["transform_matches_sample"])},
        "stored_evidence": {"canary": {"passed": canary_passed, "features_tested": can["features_tested"],
                                       "max_symmetric_auc": can["max_symmetric_auc"],
                                       "source": "evidence/hgvc88_canaries.json (STORED-RECEIPT)"},
                            "holdout": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": ho["evaluator_version"],
                                        "candidate": stored_cand, "paired_delta_vs_adhr": stored_delta,
                                        "beats_bar": holdout_beats_bar,
                                        "source": "evidence/hgvc88_holdout_20261024.json (STORED-RECEIPT)"},
                            "preplacement_surface_max_abs_spearman": stored_surface_rho,
                            "preplacement_surface_source": "registry/hgvc88_run_card.json (STORED-RECEIPT; continuous surface not archived)"},
        "uniqueness_recomputed": {"registry_rasters_checked": uq["registry_rasters"],
                                  "distinct_dot_sets_checked": uq["distinct_dot_sets"], "missing": uq["missing"],
                                  "worst_abs_rho_final": uq["worst_abs_rho"],
                                  "worst_dotfield_overlap": uq["worst_dotfield_overlap"],
                                  "worst_excess_overlap": uq["worst_excess_overlap"],
                                  "worst_literal_overlap": uq["worst_literal_overlap"],
                                  "unique_v4": uq["unique_v4"], "v4_blockers": uq["v4_blockers"],
                                  "unique_literal": uq["unique_literal"], "literal_blockers": uq["literal_blockers"],
                                  "space_filling_rasters": uq["space_filling_rasters"],
                                  "scope": ("registry/inventory.json + data/registry + data/fleet + data/siblings "
                                            "(pinned) + data/siblings_head (live HEAD clones 2026-10-25) + "
                                            "docs/downloads + submissions + releases in this checkout, HGVC itself excluded")},
        "submission_name": rc["submission_name"], "submission_note": rc["submission_note"],
        "submission_note_length": len(rc["submission_note"]),
        "organizer_confirmed_score": None, "weekly_slots_spent": 0,
    }
    for p in (ROOT / "registry/hgvc88_gate_v4_reaudit_20261025.json",
              ROOT / "docs/data/hgvc88_gate_v4_reaudit_20261025.json"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_rows = ROOT / "evidence/hgvc88_uniqueness_v4_20261025.json"
    write_rows.write_text(json.dumps({**receipt["uniqueness_recomputed"], "rows": uq["rows"]},
                                     indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("label", "ok_to_download", "ok_to_submit")}, indent=2))
    print(json.dumps(receipt["uniqueness_recomputed"], indent=2))
    if args.require_submit and not receipt["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
