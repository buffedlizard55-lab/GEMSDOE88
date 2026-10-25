#!/usr/bin/env python3
"""Independent fail-closed validator for the H88-VCAZ research deliverable.

Works both with restored ``data/bridge`` + ``data/registry`` inputs and in a
standalone git checkout (without ``data/``).

Exit codes:
  0  Artifact, ZIP, Run Card, preregistration, holdout, canary, concurrent-lane
     like-for-like uniqueness, and portal format checks all pass (0 slots spent).
  1  Structural/format/hash/evidence error or regression.
  2  ``--require-submit`` requested while ``ok_to_submit`` is False.
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
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gems57 import uniqueness  # noqa: E402
from gems88 import gate  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_vcaz88(root: Path = ROOT) -> dict:
    root = Path(root)
    problems: list[str] = []

    def req(cond: bool, msg: str) -> None:
        if not cond:
            problems.append(msg)

    mirror_pairs = (
        ("registry/preregistration_vcaz88.json", "docs/data/preregistration_vcaz88.json"),
        ("research/candidate-hypotheses-20261025-vcaz88.md", "docs/research/candidate-hypotheses-20261025-vcaz88.md"),
        ("registry/vcaz88_gate_v3.json", "docs/data/vcaz88_gate_v3.json"),
        ("evidence/vcaz88_holdout_20261025.json", "docs/evidence/vcaz88_holdout_20261025.json"),
    )
    for rel_a, rel_b in mirror_pairs:
        pa, pb = root / rel_a, root / rel_b
        req(pa.is_file() and pb.is_file(), f"missing mirrored file pair: {rel_a} / {rel_b}")
        if pa.is_file() and pb.is_file():
            req(
                pa.read_text(encoding="utf-8") == pb.read_text(encoding="utf-8"),
                f"mirror mismatch: {rel_a} vs {rel_b}",
            )

    card_paths = [
        root / "registry/vcaz88_run_card.json",
        root / "docs/data/vcaz88_run_card.json",
        root / "evidence/vcaz88_run_card.json",
    ]
    uq_path = root / "evidence/vcaz88_uniqueness.json"
    can_path = root / "evidence/vcaz88_canaries.json"
    for p in (*card_paths, uq_path, can_path):
        req(p.is_file(), f"missing evidence/card file: {p.relative_to(root)}")
    if problems:
        return {"ok": False, "ok_to_submit": False, "problems": problems}

    card = json.loads(card_paths[0].read_text(encoding="utf-8"))
    gv = json.loads((root / "registry/vcaz88_gate_v3.json").read_text(encoding="utf-8"))
    uq = json.loads(uq_path.read_text(encoding="utf-8"))
    can = json.loads(can_path.read_text(encoding="utf-8"))
    hold = json.loads((root / "evidence/vcaz88_holdout_20261025.json").read_text(encoding="utf-8"))

    dl_tif = root / card["download"]
    dl_zip = root / card["zip_download"]
    sub_tif = root / card["repo_copy"]
    sub_zip = sub_tif.with_suffix(".zip")
    dl_receipt = dl_tif.with_suffix(".json")
    dl_audit = dl_tif.with_suffix(".format-audit.json")

    card_paths.append(dl_receipt)
    texts = [p.read_text(encoding="utf-8") for p in card_paths if p.is_file()]
    req(len(texts) == 4 and len(set(texts)) == 1, "Run Card copies are not byte-identical")
    req(dl_tif.is_file() and dl_zip.is_file() and dl_audit.is_file(), "download .tif/.zip/.format-audit.json missing")
    req(sub_tif.is_file() and sub_zip.is_file(), "submissions/ .tif/.zip mirror missing")
    if problems:
        return {"ok": False, "ok_to_submit": False, "problems": problems}

    req(dl_tif.stem.endswith("-DO-NOT-SUBMIT"), "TIFF filename must carry -DO-NOT-SUBMIT suffix")
    tif_sha = sha256_file(dl_tif)
    zip_sha = sha256_file(dl_zip)
    req(
        tif_sha == sha256_file(sub_tif) == card["raster_sha256"] == gv["sha256"] == uq["candidate_sha256"],
        "TIFF SHA-256 mismatch across Run Card, gate_v3, uniqueness ledger, or submissions/",
    )
    req(
        zip_sha == sha256_file(sub_zip) == card["zip_sha256"] == gv["zip_sha256"],
        "ZIP SHA-256 mismatch across Run Card, gate_v3, or submissions/",
    )

    with zipfile.ZipFile(dl_zip, "r") as zf:
        req(
            zf.testzip() is None and zf.namelist() == [dl_tif.name] and zf.read(dl_tif.name) == dl_tif.read_bytes(),
            "ZIP does not contain exactly one byte-identical GeoTIFF",
        )

    exp = gate.EXPECTED
    req(dl_tif.read_bytes()[:4] in (b"II*\x00", b"MM\x00*"), "GeoTIFF is not classic TIFF")
    with rasterio.open(dl_tif) as ds:
        arr = ds.read(1)
        req(ds.count == 1 and ds.dtypes[0] == "float32", "GeoTIFF must be single-band float32")
        req(ds.crs is not None and ds.crs.to_epsg() == exp["epsg"], f"GeoTIFF CRS must be EPSG:{exp['epsg']}")
        req(ds.shape == exp["shape"] and tuple(ds.transform)[:6] == exp["transform"], "GeoTIFF shape/transform mismatch")
        req(ds.nodata is None, "GeoTIFF nodata must be None")
        req(
            str(ds.profile.get("compress", "")).lower() == "lzw" and not bool(ds.profile.get("tiled", False)),
            "GeoTIFF must match sample LZW non-tiled strip layout",
        )
        req(ds.block_shapes[0] == (1, exp["shape"][1]), "GeoTIFF must use 1-row strips")

    arr_tf = tifffile.imread(dl_tif)
    req(np.array_equal(arr, arr_tf), "tifffile second decoder disagrees with rasterio")
    req(bool(np.isfinite(arr).all()), "GeoTIFF contains NaN or Inf")
    req(bool(np.all((arr >= 0.0) & (arr <= 1.0))), "GeoTIFF values outside [0, 1]")
    req(set(np.unique(arr)).issubset({0.0, 1.0}), "GeoTIFF must contain discrete {0.0, 1.0} values")

    n_dots = int((arr > 0.5).sum())
    req(n_dots == int(card["fingerprint"]["n"]) == int(gv["candidate"]["dots"]), "positive dot count mismatch")

    # Live re-measurement against concurrent in-repo sparse artifacts in docs/downloads/
    concurrent_worst_ov = 0.0
    concurrent_worst_lbl = ""
    cand_dots = arr > 0.5
    for peer in sorted((root / "docs/downloads").glob("*.tif")):
        if peer.resolve() == dl_tif.resolve():
            continue
        with rasterio.open(peer) as pds:
            parr = pds.read(1)
        ppos = np.isfinite(parr) & (parr > 0)
        if int(ppos.sum()) > 500_000:
            continue
        ov = float(uniqueness.dot_overlap(cand_dots, ppos, 3))
        if ov > concurrent_worst_ov:
            concurrent_worst_ov = ov
            concurrent_worst_lbl = peer.name
    req(concurrent_worst_ov <= 0.70, f"concurrent docs/downloads 3-px overlap {concurrent_worst_ov:.6f} > 0.70")

    sample_reopened = False
    sample_path = root / "data/bridge/sample_submission.tif"
    if sample_path.is_file():
        from gems57 import gates as g57gates, grid as grid_mod, validate as g57validate

        g = grid_mod.load_grid(root / "data/bridge")
        req(sha256_file(sample_path) == grid_mod.SHA256_SAMPLE_SUBMISSION, "sample_submission.tif SHA mismatch")
        portal_tif = gate.portal_validate(dl_tif, sample_path, g.footprint)
        portal_zip = gate.portal_validate(dl_zip, sample_path, g.footprint)
        g57_fmt = g57gates.format_report(dl_tif, sample_path, footprint=g.footprint)
        g57_val = g57validate.validate(dl_tif, g.footprint, g.catalogue)
        req(bool(portal_tif["ok"]) and bool(portal_zip["ok"]), "portal_validate failed on restored sample")
        req(bool(portal_tif["layout_parity_with_sample"]), "layout_parity_with_sample failed")
        req(bool(g57_fmt["ok"]) and bool(g57_val["all_checks_passed"]), "gems57 format/validate failed")

        d_fullcat = ndi.distance_transform_edt(~np.asarray(g.catalogue, dtype=bool)).astype(np.float32)
        fp_prof = gate.fingerprint(cand_dots, d_fullcat)
        req(gate.fingerprint_screen(fp_prof), f"basin fingerprint screen failed: {fp_prof}")

        witness = root / "data/registry/dense_17gemdoe.tif"
        if witness.is_file():
            with rasterio.open(witness) as wds:
                w_arr = wds.read(1)
            lit_ov = float(uniqueness.dot_overlap(cand_dots, (np.isfinite(w_arr) & (w_arr > 0)) & g.footprint, 3))
            req(lit_ov > 0.70, "expected dense witness literal overlap > 0.70")
        sample_reopened = True

    # Canary, scramble, holdout, and full-registry ledger verification
    req(can["passed"] is True and float(can["max_symmetric_auc"]) <= 0.90, "leakage canary failed")
    req(int(can["features_tested"]) == 91, f"expected 91 canary features, got {can['features_tested']}")
    req(can.get("zero_test_quadrant_leakage_scramble_equal") is True, "scramble invariance flag missing/false")

    bench_sc = hold["pooled_overall"]["scores"][hold["benchmark_arm"]]
    delta_adhr = hold["pooled_overall"]["paired_differences"]["h88_adhr_control"]
    req(round(float(bench_sc["dti"]), 6) == card["holdout"]["dti"], "Run Card holdout DTI mismatch")
    req(int(bench_sc["withheld_positive_pixels"]) == card["holdout"]["withheld_positive_pixels"], "withheld count mismatch")
    req(float(delta_adhr["ci95"][0]) > 0.0, "paired 95% CI vs H88-ADHR must be strictly > 0")
    req(int(hold["folds_won_vs_adhr"]) == 8, "expected 8/8 fold wins vs H88-ADHR")

    req(
        bool(uq["unique_like_for_like"])
        and float(uq["final_worst_like_for_like_overlap_3px"]["value"]) <= 0.70
        and float(uq["surface_preplacement_max_abs_spearman"]) <= 0.90
        and float(uq["final_max_abs_spearman"]) <= 0.90
        and int(uq["registry_rasters_checked"]) >= 300,
        "300+-raster uniqueness ledger failed",
    )

    # Governance & budget invariants
    req(int(card["experiments_executed"]) <= 3, "experiment budget > 3")
    req(float(card["wall_clock_seconds"]) <= 7200.0, "wall-clock budget > 7200s")
    req(int(card["weekly_slots_spent"]) == 0, "weekly_slots_spent must be 0")
    req(card["organizer_confirmed_score"] is None, "organizer_confirmed_score must be None")
    req(1 <= len(card["submission_name"]) <= 140, "submission_name length invalid")
    req(1 <= len(card["submission_note"]) <= 140, "submission_note length invalid")
    req(card["ok_to_download"] is True, "ok_to_download must be True")
    req(card["ok_to_submit"] is False and gv["decision"]["ok_to_submit"] is False, "ok_to_submit must be False")
    req(card["verdict"] == "negative", "verdict must be 'negative'")

    return {
        "ok": len(problems) == 0,
        "lane": "H88-VCAZ",
        "preregistration_id": card["preregistration_id"],
        "sample_reopened": sample_reopened,
        "tif": card["download"],
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "dots": n_dots,
        "holdout_dti": card["holdout"]["dti"],
        "holdout_ci95": card["holdout"]["ci95"],
        "paired_delta_vs_adhr": card["holdout"]["paired_delta_vs_adhr"],
        "folds_won_vs_adhr": card["holdout"]["folds_won_vs_adhr"],
        "concurrent_in_repo_worst_overlap_3px": {
            "label": concurrent_worst_lbl,
            "value": round(concurrent_worst_ov, 6),
        },
        "full_registry_checked": int(uq["registry_rasters_checked"]),
        "full_registry_worst_like_for_like_overlap_3px": uq["final_worst_like_for_like_overlap_3px"],
        "ok_to_download": bool(card["ok_to_download"]),
        "ok_to_submit": bool(card["ok_to_submit"]),
        "verdict": card["verdict"],
        "problems": problems,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-submit", action="store_true", help="Exit 2 unless ok_to_submit is True")
    ap.add_argument("--json", action="store_true", help="Print full JSON report")
    args = ap.parse_args(argv)

    rep = validate_vcaz88(ROOT)
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        status = "PASS (RESEARCH DOWNLOAD ONLY; DO NOT SUBMIT)" if rep["ok"] else "FAIL"
        print(
            f"[validate_vcaz88] {status} | sha256={rep.get('raster_sha256', '')[:12]} | "
            f"dots={rep.get('dots')} | HOLDOUT-DTI={rep.get('holdout_dti')} | "
            f"folds={rep.get('folds_won_vs_adhr')} | worst_lfl_3px={rep.get('full_registry_worst_like_for_like_overlap_3px', {}).get('value', 'n/a')} | "
            f"ok_to_submit={rep.get('ok_to_submit')}"
        )
        for p in rep["problems"]:
            print(f"  PROBLEM: {p}", file=sys.stderr)

    if not rep["ok"]:
        return 1
    if args.require_submit and not rep["ok_to_submit"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
