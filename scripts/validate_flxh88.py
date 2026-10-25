#!/usr/bin/env python3
"""Independent validator for H88-FLXH research GeoTIFF.
Exit 0 = valid research download; --require-submit exits 2 because holdout is structural low (far-biased) and verdict negative.
"""
from __future__ import annotations
import hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import grid as grid_mod, validate as v_validate
from gems88 import gate

def sha256_file(p: Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1<<20), b""): h.update(c)
    return h.hexdigest()

def validate_flxh88(root: Path=ROOT)->dict:
    reg = ROOT / "registry/flxh88_run_card.json"
    web = ROOT / "docs/data/flxh88_run_card.json"
    if not reg.is_file() or not web.is_file():
        raise FileNotFoundError("FLXH run card missing")
    r=json.loads(reg.read_text()); w=json.loads(web.read_text())
    if r!=w: raise ValueError("run card out of sync registry vs docs/data")
    # allow negative verdict but ok_to_download true
    if r["ok_to_download"] is not True:
        raise ValueError("ok_to_download must be true")
    tif = ROOT / r["submission"]["file"]
    zipp = ROOT / r["submission"]["zip_file"]
    if not tif.is_file() or not zipp.is_file():
        raise FileNotFoundError(f"missing {tif} or {zipp}")
    if sha256_file(tif)!=r["raster_sha256"] or sha256_file(zipp)!=r["zip_sha256"]:
        raise ValueError("SHA mismatch")
    with zipfile.ZipFile(zipp) as z:
        if z.testzip() is not None or z.namelist()!=[tif.name] or z.read(tif.name)!=tif.read_bytes():
            raise ValueError("ZIP must contain exactly one byte-identical TIFF")
    name, note = r["submission"]["submission_name"], r["submission"]["submission_note"]
    if not (1 <= len(name) <=140) or not (1 <= len(note) <=140):
        raise ValueError("name/note length")
    canary=r["leakage_canary"]
    if not canary["passed"] or canary["max_symmetric_auc"]>0.90:
        raise ValueError("canary fail")
    hd=r["holdout_dti"]
    if hd["evidence_class"]!="HOLDOUT-DTI" or hd["evaluator_version"]!="gems57-pooled-hide-v2":
        raise ValueError("holdout label")
    corr=r["correlation_overlap_vs_registry"]
    if corr["final_worst_like_for_like_overlap_3px"]["value"]>0.70:
        raise ValueError(f"like-for-like overlap {corr['final_worst_like_for_like_overlap_3px']['value']:.4f} >0.70")
    if corr["surface_preplacement_max_abs_spearman"]>0.90:
        raise ValueError(f"rho {corr['surface_preplacement_max_abs_spearman']:.4f}>0.90")
    # grid check if bridge exists
    sample=ROOT/"data/bridge/sample_submission.tif"
    grid_verified=False
    if sample.is_file():
        g=grid_mod.load_grid(ROOT/"data/bridge")
        portal=gate.portal_validate(tif, sample, g.footprint)
        val=v_validate.validate(tif, g.footprint, g.catalogue)
        v_validate.assert_submittable(val)
        if not (portal["ok"] and val["all_checks_passed"] and portal["n_dots"]==r["submission"]["positive_pixels"]):
            raise ValueError("portal/validate failed")
        if not (val["checks"]["no_nan_anywhere"] and val["checks"]["range_0_1_guaranteed"]):
            raise ValueError("range/NaN fail")
        grid_verified=True
    return {"ok": True, "grid_reopened": grid_verified, "lane": r["lane"], "tif": r["submission"]["file"], "tif_sha256": r["raster_sha256"], "zip_sha256": r["zip_sha256"], "dots": r["submission"]["positive_pixels"], "holdout_dti": r["holdout_dti"]["overall"]["dti"], "worst_like_for_like_overlap": corr["final_worst_like_for_like_overlap_3px"]["value"], "surface_max_abs_rho": corr["surface_preplacement_max_abs_spearman"], "ok_to_download": True, "ok_to_submit": r["ok_to_submit"], "verdict": r["verdict"]}

def main()->int:
    rep=validate_flxh88()
    print(json.dumps(rep, indent=2))
    if "--require-submit" in sys.argv:
        print("AUTOMATIC SUBMISSION GATE: DO NOT SUBMIT as promoted slot (holdout structural zero for far-biased; verdict negative; 0 slots spent) — exit 2.", file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    import sys as _s; _s.exit(main())
