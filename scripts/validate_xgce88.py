#!/usr/bin/env python3
"""Run local artifact checks for archived H88-XGCE without spending a slot.
Exit 0 means local file checks completed; it does not mean scientific gates pass.
Exit 2 is the fail-closed result when --require-submit is requested.
"""
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

TIF = ROOT/"docs/downloads/gems88-xgce-crossgradient-30000dots-20261025-zeros.tif"
ZIP = ROOT/"docs/downloads/gems88-xgce-crossgradient-30000dots-20261025-zeros.zip"
SAMPLE = ROOT/"data/bridge/sample_submission.tif"
CARD = ROOT/"registry/xgce88_run_card.json"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1<<20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    require_submit = "--require-submit" in sys.argv
    g = grid_mod.load_grid(ROOT/"data/bridge")
    assert TIF.exists(), f"missing {TIF}"
    assert ZIP.exists(), f"missing {ZIP}"
    assert CARD.exists(), f"missing {CARD}"
    card = json.loads(CARD.read_text())
    assert card["ok_to_download"] is True, "card not downloadable"
    assert card["ok_to_submit"] is False, "card incorrectly marked submittable"
    assert card["verdict"] == "negative", "card verdict not negative"
    # Check hashes
    assert sha(TIF) == card["submission"]["raster_sha256"], "tif hash mismatch vs run card"
    assert sha(ZIP) == card["submission"]["zip_sha256"], "zip hash mismatch"
    # Portal validation
    v_tif = portal_validate(TIF, SAMPLE, footprint=g.footprint)
    v_zip = portal_validate(ZIP, SAMPLE, footprint=g.footprint)
    v_art = validate_artifact(TIF, SAMPLE)
    assert v_tif["ok"], f"tif portal fail {v_tif['problems']}"
    assert v_zip["ok"], f"zip portal fail {v_zip['problems']}"
    assert v_art["ok"], f"artifact fail {v_art}"
    # Check values in [0,1] no NaN
    with rasterio.open(TIF) as src:
        a = src.read(1)
    assert a.shape == g.shape, f"shape {a.shape} != {g.shape}"
    assert str(src.crs) == f"EPSG:{grid_mod.EPSG}", f"CRS {src.crs}"
    assert tuple(src.transform)[:6] == tuple(grid_mod.TRANSFORM)[:6], "transform mismatch"
    assert np.isfinite(a).all(), "nonfinite found"
    assert (a >= 0).all() and (a <= 1).all(), "range [0,1] violated"
    assert (a[~g.footprint] == 0).all(), "outside footprint not zero"
    assert (a[g.catalogue] == 0).all(), "dots on catalogue"
    assert int((a>0).sum()) == card["submission"]["positive_pixels"], "dot count mismatch"
    # Check ZIP contains exactly same bytes
    with zipfile.ZipFile(ZIP) as z:
        assert z.namelist() == [TIF.name], f"zip members {z.namelist()}"
        assert z.read(TIF.name) == TIF.read_bytes(), "zip bytes not identical"
    # Fail closed: the historical catalogue-vs-random proxy is not a valid blocked canary.
    canary = card["leakage_canary"]
    assert canary["passed"] is False, "unvalidated proxy must not be marked passed"
    assert canary["valid_fold_isolated_feature_tests"] == 0
    assert canary["evidence_class"] == "PROXY-DIAGNOSTIC-NOT-FOLD-ISOLATED-CANARY"
    holdout = card["holdout_dti"]
    assert holdout["evidence_class"] == "UNSCORED"
    assert holdout["overall"] is None and holdout["ci95"] is None
    # Fingerprint
    assert card["fingerprint"]["share_gt25"] >= 0.35, "fingerprint fail"
    assert card["fingerprint"]["share_le2"] == 0.0
    # No uniqueness clearance: the historical sparse comparison is not enough,
    # and a valid pre-placement continuous-surface rank check is absent.
    assert card["uniqueness"]["unique_like_for_like"] is False
    assert card["uniqueness"]["max_rho_pass"] is False
    assert card["uniqueness"]["pre_placement_worst_abs_spearman"] is None
    # Literal must be 1.0 -> fail-closed
    assert card["uniqueness"]["literal_dense_witness_overlap"] == 1.0
    assert card["uniqueness"]["literal_dense_witness_pass"] is False
    print("[XGCE-VALIDATE] Local artifact format/range/ZIP checks PASS for this run; leakage NOT VALIDATED, HOLDOUT-DTI NOT COMPUTED; recorded literal overlap 1.0>0.70 enforces DO NOT SUBMIT")
    print(f"  TIF {TIF.name} SHA256 {sha(TIF)}")
    print(f"  ZIP {ZIP.name} SHA256 {sha(ZIP)}")
    print(f"  Name {card['submission']['submission_name']} ({len(card['submission']['submission_name'])}/140)")
    print(f"  Note {card['submission']['submission_note']} ({len(card['submission']['submission_note'])}/140)")
    if require_submit:
        print("[XGCE-VALIDATE] --require-submit: candidate holdout/canary/pre-placement and literal uniqueness gates do not pass -> exit 2 FAIL-CLOSED")
        sys.exit(2)
    else:
        print("[XGCE-VALIDATE] Research download YES, submit NO — exit 0")
        sys.exit(0)

if __name__ == "__main__":
    main()
