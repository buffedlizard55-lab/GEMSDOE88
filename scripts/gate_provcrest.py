#!/usr/bin/env python3
"""Apply gate v3 to a de-novo file merged from another parallel session (default: PROVCREST, PR #53; also TILTZERO, PR #59).

Usage: ``python scripts/gate_provcrest.py [provcrest|tiltzero]``.

PR #53's own session promoted it using a 30-raster registry.  This script re-assesses the *same bytes*
against the v3 registry (215+ rasters incl. GEMSDOE86/87/89/92 and the 25 scored rasters) with the same
rules as every other candidate.  Output: registry/provcrest_gate_v3.json (+ docs/data copy).  Read-only
with respect to PR #53's own artifacts and run card.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import grid as grid_mod  # noqa: E402
from gems88 import gate, registry_paths  # noqa: E402

BAR_OVERALL = 0.18789  # stored H88-ADHR pooled HOLDOUT-DTI (seeds 20+21)


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "provcrest"
    card = json.loads((ROOT / f"registry/{tag}_run_card.json").read_text())
    sub = card["submission"]
    tif = ROOT / sub["file"]
    zp = ROOT / sub["zip_file"]
    assert gate.sha256_file(tif) == sub["sha256"], f"{tag} TIFF differs from its own run card"
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    fp = g.footprint
    sample = ROOT / "data/bridge/sample_submission.tif"
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    vals = gate.read_values(tif, fp)
    dots = (vals > 0) & fp
    fpr = gate.fingerprint(dots, d_cat)
    fp_pass = gate.fingerprint_screen(fpr)
    reg = registry_paths.registry_list(exclude=(tif.name,))
    reg = [(l, p) for l, p in reg if p.resolve() != tif.resolve()]
    uq = gate.uniqueness_report(tif, reg, fp)
    pt, pz = gate.portal_validate(tif, sample, fp), gate.portal_validate(zp, sample, fp)
    portal = dict(ok=bool(pt["ok"] and pz["ok"] and pt["array_sha256"] == pz["array_sha256"]), problems=pt["problems"] + pz["problems"])
    h = card["holdout"]
    beats = bool(h["winner_dti"] > BAR_OVERALL)
    name = sub.get("submission_name") or sub.get("name") or tif.stem
    note = sub.get("submission_note") or sub.get("note") or ""
    v = gate.decide(portal=portal, uniqueness=uq, canary_passed=bool(card["leakage_canary"]["passed"]), holdout_beats_bar=beats,
                    name=name, note=note, used_names=[l.split(":", 1)[-1] for l, _ in reg])
    if not fp_pass:
        v["blocking_reasons"].append("FINGERPRINT: catalogue-hugging profile (owner-reported fleet screen)")
        v["ok_to_submit"] = False
        v["label"] = "OK TO DOWNLOAD - NOT OK TO SUBMIT" if v["ok_to_download"] else v["label"]
    blockers = [r for r in uq["rows"] if r.get("blocks_like_for_like")]
    out = dict(
        name=name, note=note, file=sub["file"], sha256=sub["sha256"], zip_sha256=gate.sha256_file(zp), generated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source=f"parallel-session candidate '{tag}', re-assessed by gate v3; its own run card says verdict={card['verdict']} (registry of {card['uniqueness']['rasters_checked']} rasters)",
        **v,
        own_gate=dict(verdict=card["verdict"], registry_rasters_checked=card["uniqueness"]["rasters_checked"],
                      worst_sparse_dot_overlap_3px=card["uniqueness"]["worst_sparse_dot_overlap_3px"]["overlap"]),
        holdout_cross_run=dict(evidence_class="HOLDOUT-DTI", evaluator_version=h["evaluator_version"], seeds=h["seeds"], withheld_positives=h["withheld_positive_pixels"],
                               dti=h["winner_dti"], ci95=h["winner_ci95"], bar=BAR_OVERALL, beats_bar=beats,
                               caveat="bar comes from seeds 20+21 (22,893 withheld); PR #53 used seeds 20+30 (22,663 withheld): a cross-run comparison"),
        fingerprint=fpr, fingerprint_screen_pass=fp_pass, portal_values_and_grid_ok=portal["ok"],
        portal_layout_parity_with_sample=pt["layout_parity_with_sample"], portal_layout=pt["layout"],
        uniqueness=dict(registry_rasters=uq["registry_rasters"], distinct_dot_sets=uq["distinct_dot_sets"], unique_like_for_like=uq["unique_like_for_like"],
                        worst_like_for_like_overlap=uq["worst_like_for_like_overlap"], worst_abs_rho=uq["worst_abs_rho"],
                        like_for_like_blockers=[dict(label=r["label"], overlap=r["like_for_like_overlap_3px"], registry_dots=r["registry_dots"]) for r in blockers]))
    if tag == "provcrest":
        out["pr53_own_gate"] = out["own_gate"]  # key used by validators/tests written for PR #53
    text = json.dumps(out, indent=1, default=float) + "\n"
    (ROOT / f"registry/{tag}_gate_v3.json").write_text(text)
    (ROOT / f"docs/data/{tag}-gate-v3.json").write_text(text)
    print(v["label"], "|", v["blocking_reasons"])
    print(json.dumps(out["uniqueness"], indent=1, default=float)[:900])


if __name__ == "__main__":
    main()
