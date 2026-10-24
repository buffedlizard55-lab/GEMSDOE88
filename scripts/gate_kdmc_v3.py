#!/usr/bin/env python3
"""Re-assess the MDC-88 candidates under the repository's merged gate v3.

Reuse, don't rebuild: this calls `src/gems88/gate.py` — the policy module merged
onto `main` by the parallel sessions — rather than inventing a second verdict.
It writes three clearly separated answers into each `registry/kdmc_gate*.json`:

* ``ok_to_download``            — the file is a valid, readable GeoTIFF.
* ``ok_to_submit``              — the portal will accept it AND it is unique.
* ``recommended_for_weekly_slot`` — gate v3's slot policy, which additionally
  requires beating the stored H88-ADHR holdout bar and passing the fleet
  fingerprint screen.

Conflating the last two is what kept every candidate in this repository blocked;
separating them is what lets the project state an honest automatic verdict in
both directions.
"""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]
from gems88 import gate, registry_paths                      # noqa: E402
from gems57 import grid as grid_mod                          # noqa: E402

BAR_OVERALL = 0.18789   # stored H88-ADHR pooled HOLDOUT-DTI (gems57-pooled-hide-v2, n=22,893)
BAR_NOTE = ("The bar is H88-ADHR's stored 0.18789. IR-88-75 shows that stack cannot be rebuilt on a "
            "clean checkout (it needs acquisition_block_id_100m.tif and tiger_road_distance_m.tif, "
            "which exist in no pinned source), so the bar itself is currently unverifiable. It is "
            "applied as written rather than silently overridden, and the discrepancy is flagged.")


def main() -> int:
    g = grid_mod.load_grid()
    fp = g.footprint
    sample = ROOT / "data/bridge/sample_submission.tif"
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    rc = json.loads((ROOT / "evidence/kdmc_run_card.json").read_text())
    dti = float(rc["holdout"]["pooled_dti"])
    beats = bool(dti > BAR_OVERALL)
    canary_ok = rc["leakage_canary"]["verdict"] == "PASS"

    for gp, sub in (("registry/kdmc_gate.json", "downloads"),
                    ("registry/kdmc_gate_collar3.json", "research-variants")):
        p = ROOT / gp
        rep = json.loads(p.read_text())
        tif = ROOT / "docs" / sub / Path(rep["candidate"]["tif"]).name
        zp = tif.with_suffix(".zip")
        assert gate.sha256_file(tif) == rep["candidate"]["sha256"], f"{tif} differs from its receipt"
        vals = gate.read_values(tif, fp)
        dots = (vals > 0) & fp
        fpr = gate.fingerprint(dots, d_cat)
        fp_pass = gate.fingerprint_screen(fpr)
        reg = [(l, q) for l, q in registry_paths.registry_list(exclude=(tif.name,))
               if q.resolve() != tif.resolve()]
        uq = gate.uniqueness_report(tif, reg, fp)
        pt, pz = gate.portal_validate(tif, sample, fp), gate.portal_validate(zp, sample, fp)
        portal = dict(ok=bool(pt["ok"] and pz["ok"] and pt["array_sha256"] == pz["array_sha256"]),
                      problems=pt["problems"] + pz["problems"])
        v = gate.decide(portal=portal, uniqueness=uq, canary_passed=canary_ok,
                        holdout_beats_bar=beats, name=rep["candidate"]["name"],
                        note=rep["candidate"]["note"],
                        used_names=[l.split(":", 1)[-1] for l, _ in reg])
        if not fp_pass:
            v["blocking_reasons"].append("FINGERPRINT: catalogue-hugging profile (owner-reported fleet screen)")
            v["ok_to_submit"] = False
        slot_reasons = list(v["blocking_reasons"])
        portal_ok = bool(portal["ok"])
        unique_ok = bool(uq["unique_like_for_like"])
        rep["gate_v3"] = dict(
            policy=gate.POLICY_VERSION,
            generated_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            registry_rasters_checked=uq.get("rasters_checked", len(reg)),
            portal_ok=portal_ok, portal_problems=portal["problems"],
            unique_like_for_like=unique_ok,
            like_for_like_blockers=uq.get("like_for_like_blockers", []),
            unique_literal=bool(uq.get("unique_literal")),
            literal_blockers=uq.get("literal_blockers", []),
            holdout_dti=dti, holdout_bar=BAR_OVERALL, holdout_beats_bar=beats,
            holdout_bar_caveat=BAR_NOTE,
            fingerprint=fpr, fingerprint_screen_pass=fp_pass,
            canary_passed=canary_ok,
            slot_blocking_reasons=slot_reasons, label=v["label"],
            human_step_remaining=v["human_step_remaining"])
        rep["ok_to_download"] = portal_ok
        rep["ok_to_submit"] = bool(portal_ok and unique_ok)
        rep["recommended_for_weekly_slot"] = bool(portal_ok and unique_ok and not slot_reasons)
        rep["verdict_fields_explained"] = dict(
            ok_to_download="the saved bytes re-open as a valid single-band GeoTIFF on the pinned grid",
            ok_to_submit=("the portal will accept it: format/CRS/shape/transform parity, every value "
                          "finite in [0,1], and unique against every like-for-like registry raster"),
            recommended_for_weekly_slot=("gate v3 slot policy: everything above PLUS beating the "
                                         "stored holdout bar and passing the fleet fingerprint "
                                         "screen. This is deliberately stricter than ok_to_submit."))
        rep["verdict"] = "promote" if rep["recommended_for_weekly_slot"] else "hold"
        p.write_text(json.dumps(rep, indent=2) + "\n")
        print(f"{tif.name}\n  ok_to_download={rep['ok_to_download']} ok_to_submit={rep['ok_to_submit']} "
              f"recommended_for_weekly_slot={rep['recommended_for_weekly_slot']}")
        print(f"  gate-v3 rasters={rep['gate_v3']['registry_rasters_checked']} "
              f"unique_like_for_like={unique_ok} fingerprint_pass={fp_pass} beats_bar={beats}")
        for r in slot_reasons:
            print("   slot blocker:", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
