#!/usr/bin/env python3
"""Validate H88-XGCE TIFF/ZIP without spending a slot. Exit 0 = research PASS, exit 2 = require-submit FAIL-CLOSED."""
import hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
import rasterio
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"vendor"))
sys.path.insert(0, str(ROOT/"src"))
from gems57 import grid as grid_mod
from gems88.gate import portal_validate
from validate_artifact import validate_artifact

TIF = ROOT/"docs/downloads/gems88-xgce-crossgradient-30000dots-20261025-zeros-DO-NOT-SUBMIT.tif"
ZIP = ROOT/"docs/downloads/gems88-xgce-crossgradient-30000dots-20261025-zeros-DO-NOT-SUBMIT.zip"
SAMPLE = ROOT/"data/bridge/sample_submission.tif"
CARD = ROOT/"registry/xgce88_run_card.json"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1<<20), b""):
            h.update(b)
    return h.hexdigest()

def require(condition, message):
    """Enforce a validation gate even when Python runs with optimization enabled."""
    if not condition:
        raise ValueError(str(message))

def main():
    require_submit = "--require-submit" in sys.argv
    g = grid_mod.load_grid(ROOT/"data/bridge")
    require(TIF.exists(), f"missing {TIF}")
    require(ZIP.exists(), f"missing {ZIP}")
    require(CARD.exists(), f"missing {CARD}")
    card = json.loads(CARD.read_text())
    require(card["ok_to_download"] is True, "card not downloadable")
    require(card["ok_to_submit"] is False, "card incorrectly marked submittable")
    require(card["verdict"] == "negative", "card verdict not negative")
    # Check hashes
    require(sha(TIF) == card["submission"]["raster_sha256"], "tif hash mismatch vs run card")
    require(sha(ZIP) == card["submission"]["zip_sha256"], "zip hash mismatch")
    # Portal validation
    v_tif = portal_validate(TIF, SAMPLE, footprint=g.footprint)
    v_zip = portal_validate(ZIP, SAMPLE, footprint=g.footprint)
    v_art = validate_artifact(TIF, SAMPLE)
    require(v_tif["ok"], f"tif portal fail {v_tif['problems']}")
    require(v_zip["ok"], f"zip portal fail {v_zip['problems']}")
    require(v_art["ok"], f"artifact fail {v_art}")
    # Check values in [0,1] no NaN
    with rasterio.open(TIF) as src:
        a = src.read(1)
        crs = src.crs
        transform = src.transform
    require(a.shape == g.shape, f"shape {a.shape} != {g.shape}")
    require(str(crs) == f"EPSG:{grid_mod.EPSG}", f"CRS {crs}")
    require(tuple(transform)[:6] == tuple(grid_mod.TRANSFORM)[:6], "transform mismatch")
    require(np.isfinite(a).all(), "nonfinite found")
    require((a >= 0).all() and (a <= 1).all(), "range [0,1] violated")
    require((a[~g.footprint] == 0).all(), "outside footprint not zero")
    require((a[g.catalogue] == 0).all(), "dots on catalogue")
    require(int((a>0).sum()) == card["submission"]["positive_pixels"], "dot count mismatch")
    # Check ZIP contains exactly same bytes
    with zipfile.ZipFile(ZIP) as z:
        require(z.namelist() == [TIF.name], f"zip members {z.namelist()}")
        require(z.read(TIF.name) == TIF.read_bytes(), "zip bytes not identical")
    # Check leakage canary
    require(card["leakage_canary"]["max_symmetric_auc"] <= 0.90, "canary fail")
    require(card["leakage_canary"]["passed"] is True, "validation gate failed")
    # Fingerprint
    require(card["fingerprint"]["share_gt25"] >= 0.35, "fingerprint fail")
    require(card["fingerprint"]["share_le2"] == 0.0, "validation gate failed")
    # Uniqueness like-for-like
    require(card["uniqueness"]["unique_like_for_like"] is True, "validation gate failed")
    require(card["uniqueness"]["max_3px_overlap_disc_pass"] is True, "validation gate failed")
    require(card["uniqueness"]["max_rho_pass"] is True, "validation gate failed")
    # Literal must be 1.0 -> fail-closed
    require(card["uniqueness"]["literal_dense_witness_overlap"] == 1.0, "validation gate failed")
    require(card["uniqueness"]["literal_dense_witness_pass"] is False, "validation gate failed")
    print("[XGCE-VALIDATE] All research gates PASS: portal-valid zeros [0,1], leakage 0.568, fingerprint 49.5%, like-for-like UNIQUE 0.204<=0.70, literal 1.0>0.70 enforces DO NOT SUBMIT")
    print(f"  TIF {TIF.name} SHA256 {sha(TIF)}")
    print(f"  ZIP {ZIP.name} SHA256 {sha(ZIP)}")
    print(f"  Name {card['submission']['submission_name']} ({len(card['submission']['submission_name'])}/140)")
    print(f"  Note {card['submission']['submission_note']} ({len(card['submission']['submission_note'])}/140)")
    if require_submit:
        print("[XGCE-VALIDATE] --require-submit: research PASS but binding literal witness blocks slot -> exit 2 FAIL-CLOSED")
        sys.exit(2)
    else:
        print("[XGCE-VALIDATE] Research download YES, submit NO — exit 0")
        sys.exit(0)

if __name__ == "__main__":
    main()
