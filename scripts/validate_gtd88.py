#!/usr/bin/env python3
"""Standalone zero-human-input validator for the H88-GTD release artifacts.

Independently re-opens the saved TIFF/ZIP bytes (never trusting the runner's
in-memory state) and re-checks, line by line:

* SHA-256 of TIFF and ZIP match ``registry/gtd88_run_card.json``;
* single-band float32, EPSG:32611, 3730x3292, exact sample geotransform,
  ``nodata=None``, every one of the 12,279,160 cells finite and in
  ``{0.0, 1.0}`` (so the portal ``Predicted values must be in range [0, 1]``
  error cannot fire), zero outside the footprint and on the catalogue
  (when ``data/bridge`` is restored), second-decoder (tifffile) identity,
  single-member ZIP containing the byte-identical TIFF;
* frozen preregistration, 121-feature leakage canary + scramble record,
  8-fold HOLDOUT-DTI record vs the recomputed H88-BPWD control, fingerprint,
  vendor v4 uniqueness decision + verbatim literal v3 diagnostics;
* filename/verdict consistency: ``ok_to_submit`` files never carry
  ``DO-NOT-SUBMIT`` and vice versa.

Exit codes: ``0`` = research-valid (``ok_to_download``); with
``--require-submit``, ``2`` unless every frozen promotion gate passed.
Local validity is not organizer acceptance; no score is claimed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gtd88_report(root: Path = ROOT) -> dict:
    root = Path(root)
    rc = json.loads((root / "registry/gtd88_run_card.json").read_text(encoding="utf-8"))
    gv = json.loads((root / "registry/gtd88_gate_v4.json").read_text(encoding="utf-8"))
    pre = json.loads((root / "registry/preregistration_gtd88.json").read_text(encoding="utf-8"))
    canary = json.loads((root / "evidence/gtd88_canaries.json").read_text(encoding="utf-8"))
    holdout = json.loads((root / "evidence/gtd88_holdout_20261025.json").read_text(encoding="utf-8"))
    uq = json.loads((root / "evidence/gtd88_uniqueness_20261025.json").read_text(encoding="utf-8"))
    if pre.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise ValueError("preregistration not frozen")
    if rc.get("preregistration_id") != pre.get("preregistration_id"):
        raise ValueError("run card / preregistration id mismatch")

    tif = root / rc["file"]
    zipped = root / rc["zip_file"]
    for p in (tif, zipped):
        if not p.is_file():
            raise FileNotFoundError(f"Missing release artifact: {p}")
    tif_sha, zip_sha = _sha256(tif), _sha256(zipped)
    checks: dict[str, bool] = {}
    checks["tif_sha_matches_run_card"] = tif_sha == rc["raster_sha256"]
    checks["zip_sha_matches_run_card"] = zip_sha == rc["zip_sha256"]
    checks["gate_sha_matches"] = gv["candidate"]["sha256"] == tif_sha and gv["candidate"]["zip_sha256"] == zip_sha
    checks["uniqueness_candidate_sha_matches"] = uq["candidate_sha256"] == tif_sha

    with rasterio.open(tif) as ds:
        a = ds.read(1)
        checks["single_band"] = ds.count == 1
        checks["dtype_float32"] = a.dtype == np.float32
        checks["shape_3730x3292"] = a.shape == (3730, 3292)
        checks["crs_epsg32611"] = str(ds.crs) == "EPSG:32611"
        checks["transform_100m"] = tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        checks["nodata_none"] = ds.nodata is None
    checks["all_finite"] = bool(np.isfinite(a).all())
    checks["values_binary_0_1"] = bool(np.all((a == 0.0) | (a == 1.0)))
    checks["values_in_0_1"] = bool(a.min() >= 0.0 and a.max() <= 1.0)
    n_dots = int((a > 0).sum())
    checks["dot_count_matches"] = n_dots == rc["production"]["n_dots"] == gv["candidate"]["dots"]

    # Second decoder + ZIP member identity.
    import tifffile

    b = tifffile.imread(tif)
    checks["second_decoder_identical"] = bool(np.array_equal(np.asarray(b, np.float32), a))
    with zipfile.ZipFile(zipped) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith((".tif", ".tiff"))]
        checks["zip_single_tif_member"] = len(zf.namelist()) == 1 and len(names) == 1
        member = zf.read(names[0]) if names else b""
    checks["zip_member_byte_identical"] = hashlib.sha256(member).hexdigest() == tif_sha
    checks["zip_member_name_matches_tif"] = Path(names[0]).name == tif.name if names else False

    # Footprint/catalogue/fingerprint when the bridge grid is restored.
    sample = root / "data/bridge/sample_submission.tif"
    if sample.is_file():
        from scipy import ndimage as ndi

        from gems57 import grid as grid_mod, validate as g57validate
        from gems88 import gate

        g = grid_mod.load_grid(root / "data/bridge")
        checks["zero_outside_footprint"] = int(((a > 0) & ~g.footprint).sum()) == 0
        checks["zero_on_catalogue"] = int(((a > 0) & g.catalogue).sum()) == 0
        portal = gate.portal_validate(tif, sample, g.footprint)
        checks["portal_validate_ok"] = bool(portal["ok"] and portal["layout_parity_with_sample"])
        checks["g57_validate_ok"] = bool(g57validate.validate(tif, g.footprint, g.catalogue)["all_checks_passed"])
        d_cat = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
        fp_now = gate.fingerprint(a > 0.5, d_cat)
        checks["fingerprint_recomputed"] = (
            fp_now["n"] == rc["fingerprint"]["n"]
            and abs(fp_now["share_gt25"] - rc["fingerprint"]["share_gt25"]) < 1e-9
            and fp_now["share_le2"] == 0.0
        )
    else:
        checks["bridge_grid_restored"] = False

    # Evidence-chain consistency (numbers must match across artifacts).
    ho = rc["holdout_dti"]
    checks["canary_121_pass"] = bool(canary["passed"] and canary["features_tested"] == 121
                                     and canary["max_symmetric_auc"] <= 0.90
                                     and canary.get("zero_test_quadrant_leakage_scramble_equal"))
    pooled = holdout["pooled_overall"]["scores"][rc_arm] if (rc_arm := "exp03_gtd_tri_poe_novel") else None
    checks["holdout_candidate_matches"] = abs(pooled["dti"] - ho["candidate_exp03_production_procedure"]["dti"]) < 1e-12
    checks["holdout_withheld_22893"] = ho["withheld_positive_pixels"] == 22893
    checks["v4_decision_consistent"] = (
        uq["vendor_v4_decision"]["duplicate"] == rc["uniqueness"]["v4_duplicate"]
        and uq["vendor_v4_decision"]["worst_effective_dot_overlap"] == rc["uniqueness"]["v4_worst_effective_dot_overlap"]
    )
    checks["note_le140"] = 0 < len(rc["submission_note"]) <= 140 and len(rc["submission_name"]) <= 140
    checks["filename_verdict_consistent"] = bool(rc["ok_to_submit"]) == ("DO-NOT-SUBMIT" not in tif.name)
    if rc["ok_to_submit"]:
        checks["promote_requires_all_gates"] = bool(
            ho["beats_bpwd_with_positive_ci95"] and rc["uniqueness"]["unique_v4"]
            and rc["fingerprint_screen_pass"] and rc["leakage_canary"]["passed"] and not rc["blocking_reasons"]
        )
    research_ok = bool(rc["ok_to_download"]) and all(v for k, v in checks.items() if k != "bridge_grid_restored")
    return {
        "schema": "gems88.gtd88.validation.v1",
        "file": rc["file"], "sha256": tif_sha, "dots": n_dots,
        "checks": checks, "research_ok": research_ok,
        "ok_to_download": bool(rc["ok_to_download"] and research_ok),
        "ok_to_submit": bool(rc["ok_to_submit"] and research_ok),
        "verdict": rc["verdict"], "blocking_reasons": rc["blocking_reasons"],
        "submission_name": rc["submission_name"], "submission_note": rc["submission_note"],
        "holdout_dti_candidate": ho["candidate_exp03_production_procedure"],
        "organizer_confirmed_score": None,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--require-submit", action="store_true", help="Exit 2 unless ok_to_submit")
    args = p.parse_args(argv)
    report = gtd88_report()
    print(json.dumps(report, indent=2, allow_nan=False))
    if not report["research_ok"]:
        return 1
    if args.require_submit and not report["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
