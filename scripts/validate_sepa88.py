#!/usr/bin/env python3
"""Standalone zero-human-input validator for the H88-SEPA release artifacts.

Works in a clean checkout (no gitignored ``data/``): re-opens the saved TIFF
with two decoders (rasterio + tifffile), verifies EPSG:32611, 3730x3292,
exact sample geotransform, undeclared nodata, all-finite values in [0, 1]
(the exact portal sentence that previously failed: "Predicted values must
be in range [0, 1]"), SHA-256 identity against the run card, single-member
ZIP byte identity, frozen preregistration, leakage canary, holdout numbers
cross-checked against the evidence ledger, v4 gate fields (IR-88-118), and
naming consistency with the verdict (promote => no DO-NOT-SUBMIT marker;
negative => DO-NOT-SUBMIT marker mandatory).

Where ``data/bridge/sample_submission.tif`` has been restored, it also runs
``gate.portal_validate`` and ``gems57.validate`` against sample/catalogue.

Exit codes: 0 = research-integrity check passed; with ``--require-submit``,
2 unless ``ok_to_submit`` is True.
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
import tifffile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sepa88_report(root: Path = ROOT) -> dict:
    root = Path(root)
    rc_paths = [root / "registry/sepa88_run_card.json", root / "docs/data/sepa88_run_card.json",
                root / "evidence/sepa88_run_card.json"]
    gv_paths = [root / "registry/sepa88_gate_v4.json", root / "docs/data/sepa88_gate_v4.json"]
    pre_path = root / "registry/preregistration_sepa88.json"
    can_path = root / "evidence/sepa88_canaries.json"
    ho_paths = [root / "evidence/sepa88_holdout_20261025.json", root / "docs/evidence/sepa88_holdout_20261025.json"]
    uq_paths = [root / "evidence/sepa88_uniqueness_20261025.json", root / "docs/evidence/sepa88_uniqueness_20261025.json"]
    for p in rc_paths + gv_paths + ho_paths + uq_paths + [pre_path, can_path]:
        if not p.is_file():
            raise FileNotFoundError(f"Missing required H88-SEPA artifact: {p}")
    for group in (rc_paths, gv_paths, ho_paths, uq_paths):
        texts = [p.read_text(encoding="utf-8") for p in group]
        if any(t != texts[0] for t in texts[1:]):
            raise ValueError(f"copies differ within {group}")

    rc = json.loads(rc_paths[0].read_text(encoding="utf-8"))
    gv = json.loads(gv_paths[0].read_text(encoding="utf-8"))
    pre = json.loads(pre_path.read_text(encoding="utf-8"))
    can = json.loads(can_path.read_text(encoding="utf-8"))
    ho = json.loads(ho_paths[0].read_text(encoding="utf-8"))
    uq = json.loads(uq_paths[0].read_text(encoding="utf-8"))

    problems: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            problems.append(msg)

    check(pre.get("frozen_before_feature_canary_holdout_or_production_build") is True, "preregistration not frozen")
    check(pre.get("lane") == "H88-SEPA" and rc.get("lane") == "H88-SEPA", "lane mismatch")
    check(rc["experiments_executed"] <= 3 and rc["experiment_budget_max"] == 3, "experiment budget violated")
    check(rc["weekly_slots_spent"] == 0 and gv["weekly_slots_spent"] == 0, "weekly slots must be 0")
    check(rc["organizer_confirmed_score"] is None and gv["organizer_confirmed_score"] is None,
          "organizer-confirmed score must be null without a portal receipt")
    check(1 <= len(rc["submission_name"]) <= 140 and 1 <= len(rc["submission_note"]) <= 140, "name/note length")
    check(can["passed"] is True and can["max_symmetric_auc"] <= 0.90 and can["features_tested"] == 85,
          "leakage canary receipt inconsistent (85 features, max <= 0.90 required)")

    cand_key = "exp03_sepa_poe"
    ho_cand = ho["pooled_overall"]["scores"][cand_key]
    check(abs(ho_cand["dti"] - rc["holdout_dti"]["candidate_exp03"]["dti"]) < 1e-12, "holdout DTI card/ledger mismatch")
    check(ho_cand["withheld_positive_pixels"] == rc["holdout_dti"]["withheld_positive_pixels"] == 22893,
          "withheld positives must be 22,893")
    check(rc["holdout_dti"]["candidate_exp03"].get("evidence_class", "HOLDOUT-DTI") == "HOLDOUT-DTI", "evidence class")

    check(gv.get("policy") == "gems88-gate-v4", "gate policy must be gems88-gate-v4")
    check(uq["candidate_sha256"] == rc["raster_sha256"], "uniqueness/candidate sha mismatch")
    check(rc["correlation_overlap_vs_registry"]["unique_v4"] == uq["unique_v4"], "unique_v4 mismatch card vs evidence")

    tif_path = root / rc["download"]
    zip_path = root / rc["zip_download"]
    sub_tif = root / rc["repo_copy"]
    sub_zip = sub_tif.with_suffix(".zip")
    audit_path = tif_path.with_suffix(".format-audit.json")
    for p in (tif_path, zip_path, sub_tif, sub_zip, audit_path):
        check(p.is_file(), f"missing file {p}")
    if problems:
        return {"ok": False, "problems": problems, "ok_to_submit": bool(rc.get("ok_to_submit"))}

    check(_sha256(tif_path) == rc["raster_sha256"], "tif sha256 != run card")
    check(_sha256(zip_path) == rc["zip_sha256"], "zip sha256 != run card")
    check(_sha256(sub_tif) == rc["raster_sha256"] and _sha256(sub_zip) == rc["zip_sha256"], "repo copy sha mismatch")
    with zipfile.ZipFile(zip_path) as z:
        check(z.namelist() == [tif_path.name] and z.read(tif_path.name) == tif_path.read_bytes(),
              "ZIP must contain exactly the identical TIFF")

    promote = rc["verdict"] == "promote" and rc["ok_to_submit"] is True
    if promote:
        check("DO-NOT-SUBMIT" not in tif_path.name, "promoted file must not carry DO-NOT-SUBMIT")
        check(gv["label"] == "OK TO DOWNLOAD AND SUBMIT", "promoted gate label mismatch")
        check(uq["unique_v4"] is True, "promoted candidate must be unique_v4")
        check(rc["holdout_dti"]["candidate_exp03"]["dti"] > pre["promotion_bar"]["current_holdout_best"]["dti"],
              "promoted candidate must beat the preregistered HGVC holdout bar")
        check(rc["holdout_dti"]["paired_delta_vs_adhr_overall"]["ci95"][0] > 0, "promoted paired delta CI must be > 0")
    else:
        check("DO-NOT-SUBMIT" in tif_path.name, "negative file must carry DO-NOT-SUBMIT in its name")
        check(rc["ok_to_submit"] is False, "negative verdict must have ok_to_submit false")

    with rasterio.open(tif_path) as ds:
        a = ds.read(1)
        check(ds.count == 1 and ds.dtypes[0] == "float32", "must be single-band float32")
        check(ds.crs is not None and ds.crs.to_epsg() == 32611, "CRS must be EPSG:32611")
        check(ds.shape == (3730, 3292), f"shape must be 3730x3292, got {ds.shape}")
        check(tuple(ds.transform)[:6] == EXPECTED_TRANSFORM, "transform must match the sample grid")
        check(ds.nodata is None, "nodata must be undeclared")
    b = tifffile.imread(tif_path)
    check(np.array_equal(a, b), "tifffile second decoder disagrees with rasterio")
    check(bool(np.isfinite(a).all()), "no NaN/Inf anywhere (incl. inside footprint)")
    check(bool(np.all((a >= 0) & (a <= 1))), 'all values must satisfy the portal range check [0, 1]')
    check(set(np.unique(a).tolist()) <= {0.0, 1.0}, "values must be binary {0.0, 1.0}")
    n_dots = int((a > 0).sum())
    check(n_dots == rc["validator_output"]["positive_dots"], "dot count mismatch vs run card")
    check(rc["validator_output"]["zero_on_mapped_catalogue"] is True, "card must certify zero dots on catalogue")
    check(rc["validator_output"]["fingerprint"]["share_le2"] == 0.0, "share_le2 must be 0")
    check(rc["validator_output"]["fingerprint"]["share_gt25"] >= 0.35, "share_gt25 must be >= 0.35")

    restored = (root / "data/bridge/sample_submission.tif").is_file()
    portal_ok = None
    if restored:
        from gems57 import grid as grid_mod
        from gems57 import validate as g57validate
        from gems88 import gate

        g = grid_mod.load_grid(root / "data/bridge")
        portal = gate.portal_validate(tif_path, root / "data/bridge/sample_submission.tif", g.footprint)
        val = g57validate.validate(tif_path, g.footprint, g.catalogue)
        portal_ok = bool(portal["ok"] and val["all_checks_passed"])
        check(portal_ok, "restored-workspace portal/shared validation failed")
        check(int((a[g.catalogue] > 0).sum()) == 0, "dots found on mapped catalogue (restored check)")
        check(bool((a[~g.footprint] == 0).all()), "nonzero outside footprint (restored check)")

    return {"ok": not problems, "problems": problems, "ok_to_download": True,
            "ok_to_submit": bool(rc["ok_to_submit"]), "verdict": rc["verdict"],
            "file": rc["download"], "sha256": rc["raster_sha256"], "dots": n_dots,
            "submission_name": rc["submission_name"], "submission_note": rc["submission_note"],
            "restored_portal_check": portal_ok,
            "holdout_dti": rc["holdout_dti"]["candidate_exp03"],
            "unique_v4": uq["unique_v4"], "unique_literal": uq["unique_literal"],
            "worst_dotfield_overlap": uq["worst_dotfield_overlap"], "worst_abs_rho": uq["worst_abs_rho"]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true", help="Exit 2 unless ok_to_submit is True")
    args = ap.parse_args(argv)
    try:
        report = sepa88_report(ROOT)
    except Exception as exc:  # noqa: BLE001 - validator must fail closed with a readable report
        print(json.dumps({"ok": False, "problems": [f"{type(exc).__name__}: {exc}"], "ok_to_submit": False}, indent=2))
        return 1
    print(json.dumps(report, indent=2, allow_nan=False))
    if not report["ok"]:
        return 1
    if args.require_submit and not report["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
