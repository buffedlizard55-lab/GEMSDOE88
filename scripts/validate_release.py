#!/usr/bin/env python3
"""Independent automatic RELEASE preflight, including hard-negative uniqueness.

`--require-submit` exits 2 unless every gate clears; CI without it verifies
that the published page/receipt tells the truth even for a negative deliverable.
Do not use a successful CI check as permission to upload: read `ok_to_submit`.
"""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import grid, gates, uniqueness, validate  # noqa: E402 -- vendor path above


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def release_report(root=ROOT):
    root = Path(root)
    card = json.loads((root / "registry" / "run_card.json").read_text())
    published_card = json.loads((root / "docs" / "data" / "run-card.json").read_text())
    root_site_card = json.loads((root / "docs" / "run_card.json").read_text())
    if card != root_site_card:
        raise ValueError("root GitHub Pages run card differs from canonical receipt")
    holdout = json.loads((root / "registry" / "holdout_result.json").read_text())
    canaries = json.loads((root / "registry" / "leakage_canaries.json").read_text())
    if card != published_card:
        raise ValueError("website scientific run card differs from repository receipt")
    primary = holdout["scores"]["candidate"]
    recorded = card["holdout_dti"]
    if (
        primary["dti"] != recorded["candidate"]
        or primary["ci95"] != recorded["ci95"]
        or primary["withheld_positive_pixels"] != recorded["withheld_positives"]
        or holdout["evaluator_version"] != recorded["version"]
        or canaries["max_symmetric_auc"] != card["canary_max_auc"]
    ):
        raise ValueError(
            "website score/CI/canary claim lacks matching experiment evidence"
        )
    if canaries["max_symmetric_auc"] > 0.90 or not canaries["passed"]:
        raise ValueError("leakage canary warning: do not trust fitted score")
    receipt_file = root / "docs" / "downloads" / f"{card['submission_name']}.json"
    receipt = json.loads(receipt_file.read_text())
    tif = root / "docs" / card["downloadable_file"]
    zipfile_path = tif.with_suffix(".zip")
    gd = grid.load_grid(root / "data" / "bridge")
    sample = root / "data" / "bridge" / "sample_submission.tif"
    mapped = root / "data" / "bridge" / "existing_faults.tif"
    if (
        digest(sample) != grid.SHA256_SAMPLE_SUBMISSION
        or digest(mapped) != grid.SHA256_EXISTING_FAULTS
    ):
        raise ValueError("owner-mirror grid/label SHA256 differs from pinned files")
    if not tif.is_file() or not zipfile_path.is_file():
        raise FileNotFoundError("TIF/ZIP not present")
    with rasterio.open(sample) as ref:
        ref_grid = (ref.shape, ref.crs, ref.transform)
    report = gates.format_report(tif, sample, footprint=gd.footprint)
    local = validate.validate(tif, gd.footprint, gd.catalogue)
    with rasterio.open(tif) as ds:
        raster = ds.read(1)
        exact_grid = (ds.shape, ds.crs, ds.transform) == ref_grid
    if not report["ok"] or not local["all_checks_passed"] or not exact_grid:
        raise ValueError("TIFF local format/footprint/range preflight FAILED")
    if not np.isfinite(raster[gd.footprint]).all() or np.any(
        raster[~gd.footprint] != 0
    ):
        raise ValueError("candidate invalid in/outside footprint")
    sha = digest(tif)
    if sha != card["raster_sha256"] or sha != receipt["sha256"]:
        raise ValueError("raster/receipt/card SHA mismatch")
    if (
        card["submission_name"] != receipt["submission_name"]
        or card["submission_note"] != receipt["note"]
    ):
        raise ValueError("name/note disagreement")
    if len(card["submission_note"]) > 140 or len(card["submission_name"]) > 140:
        raise ValueError("submission note/name exceeds 140 characters")
    with zipfile.ZipFile(zipfile_path) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP must contain exact one matching TIFF")
    if digest(zipfile_path) != receipt["zip_sha256"]:
        raise ValueError("ZIP SHA mismatch")
    witness = root / "data" / "registry" / "dense_17gemdoe.tif"
    if (
        digest(witness)
        != "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    ):
        raise ValueError("witness hash mismatch")
    cert = uniqueness.saturation_certificate(
        witness, gd.footprint, gd.catalogue, expected_grid=ref_grid
    )
    with rasterio.open(witness) as ds:
        prior = ds.read(1)
    measured = uniqueness.dot_overlap(
        raster, (np.isfinite(prior) & (prior > 0)) & gd.footprint, 3
    )
    duplicate = bool(measured > 0.70)
    if (
        cert["universal_overlap_blocker"] != duplicate
        or abs(
            measured
            - card["correlation_overlap_vs_registry"]["final_dots"]["dense_prior"][
                "forward_dot_overlap_3px"
            ]
        )
        > 1e-9
    ):
        raise ValueError("prior/release overlap assertion stale")
    release_ok = bool(
        report["ok"]
        and local["all_checks_passed"]
        and not duplicate
        and card["verdict"] == "promote-to-selector-only"
    )
    # A selector is a SEPARATE step. Promotion is never auto-approval of a slot.
    submit_ok = bool(release_ok and card["ok_to_submit"])
    if submit_ok != bool(card["ok_to_submit"]):
        raise ValueError("page card conflicts with independent local/uniqueness gate")
    if not bool(card["ok_to_download"]):
        raise ValueError("research download availability is misreported")
    return dict(
        format_ok=True,
        inside_no_nan=True,
        values_0_1=True,
        crs_shape_transform_match=True,
        output_sha256=sha,
        zip_one_matching_tif=True,
        registry_witness_sha256=cert["witness_sha256"],
        registry_forward_overlap_3px=measured,
        literal_duplicate=duplicate,
        ok_to_download=card["ok_to_download"],
        ok_to_submit=submit_ok,
        status="DO NOT SUBMIT: duplicate under literal registry rule"
        if duplicate
        else "selector approval required before submission",
        grid_provenance="owner-hosted mirror; not independent organizer authentication",
        checked_against="data/bridge/sample_submission.tif; data/registry/dense_17gemdoe.tif",
    )


def release_report_v3(root=ROOT, full=False):
    """Independent re-verification of the CURRENT headline candidate (gems88-gate-v3).

    Everything is recomputed from the committed bytes; nothing is trusted from the receipts except
    to compare against.  Works in CI without the large input rasters (uses pinned grid constants);
    when data/bridge is present the portal-parity check also compares against the official sample.
    """
    sys.path.insert(0, str(root / "src"))
    from gems88 import gate  # noqa: E402 -- project gate library

    gv = json.loads((root / "registry" / "gate_verdict.json").read_text())
    card = json.loads((root / "registry" / "run_card_20261024.json").read_text())
    site_card = json.loads((root / "docs" / "data" / "run-card-20261024.json").read_text())
    if card != site_card:
        raise ValueError("site run card differs from registry run card (v3)")
    name = gv["name"]
    rcpt = json.loads((root / "docs" / "downloads" / f"{name}.json").read_text())
    tif = root / "docs" / "downloads" / f"{name}.tif"
    zp = root / "docs" / "downloads" / f"{name}.zip"
    if not tif.is_file() or not zp.is_file():
        raise FileNotFoundError("v3 TIF/ZIP missing")
    errs = []
    if not (card["submission_name"] == rcpt["name"] == gv["name"] == name):
        errs.append("name disagreement")
    if card["submission_note"] != rcpt["note"] or len(rcpt["note"]) > 140 or len(name) > 140 or not rcpt["note"]:
        errs.append("note disagreement or > 140 chars")
    sha = digest(tif)
    zsha = digest(zp)
    if not (sha == card["raster_sha256"] == rcpt["sha256"] == gv["sha256"]):
        errs.append("raster sha256 mismatch")
    if not (zsha == card["zip_sha256"] == rcpt["zip_sha256"] == gv["zip_sha256"]):
        errs.append("zip sha256 mismatch")
    with zipfile.ZipFile(zp) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            errs.append("ZIP must contain exactly the matching TIFF")
    # re-open like a portal (grid constants pinned; sample used when present)
    sample = root / "data" / "bridge" / "sample_submission.tif"
    fp = None
    if sample.is_file() and (root / "data" / "bridge" / "existing_faults.tif").is_file():
        fp = grid.load_grid(root / "data" / "bridge").footprint
        pv = gate.portal_validate(tif, sample, fp)
        pz = gate.portal_validate(zp, sample, fp)
        portal_ok = bool(pv["ok"] and pz["ok"] and pv["array_sha256"] == pz["array_sha256"])
        if not portal_ok:
            errs.append("portal-parity re-open failed: " + "; ".join((pv["problems"] + pz["problems"])[:3]))
    else:
        with rasterio.open(tif) as ds:
            a = ds.read(1)
            e = gate.EXPECTED
            ok = (ds.count == 1 and ds.dtypes[0] == "float32" and ds.crs.to_epsg() == e["epsg"] and ds.shape == e["shape"]
                  and tuple(ds.transform)[:6] == e["transform"] and ds.nodata is None
                  and bool(np.isfinite(a).all()) and float(a.min()) >= 0 and float(a.max()) <= 1)
        portal_ok = bool(ok)
        if not ok:
            errs.append("pinned-constant re-open failed")
        pv = dict(n_dots=int((a > 0).sum()))
    if card["gate"]["ok_to_submit"] != gv["ok_to_submit"] or card["gate"]["label"] != gv["label"]:
        errs.append("run card gate differs from gate verdict")
    if gv["ok_to_submit"]:
        if not name.endswith("GATE-PASS") or card["verdict"] != "promote-to-selector-only" or gv["blocking_reasons"]:
            errs.append("file name / verdict inconsistent with ok_to_submit=true")
    else:
        if not name.endswith("DO-NOT-SUBMIT") or card["verdict"] != "negative" or not gv["blocking_reasons"]:
            errs.append("file name / verdict inconsistent with ok_to_submit=false")
    # holdout + canary evidence bound to the receipts
    ho = json.loads((root / "evidence" / "halo_experiments_20261024.json").read_text())
    arm = rcpt["arm"]
    sc = ho["pooled"]["all__candidate_fbmt"]["scores"][arm]
    if abs(sc["dti"] - card["holdout"]["emitted_arm_overall"]["dti"]) > 1e-12 or sc["withheld_positive_pixels"] != card["holdout"]["emitted_arm_overall"]["withheld_positives"]:
        errs.append("holdout evidence differs from run card")
    if not ho["canary"]["passed"] or ho["canary"]["max_symmetric_auc"] > 0.90:
        errs.append("leakage canary failed")
    uq = json.loads((root / "registry" / "uniqueness_v3.json").read_text())
    rows = [r for r in uq["rows"] if not r.get("error")]
    worst = max((r["like_for_like_overlap_3px"] for r in rows), default=1.0)
    worst_rho = max((max(abs(r["rho_final"]), abs(r["rho_preplacement"])) for r in rows), default=1.0)
    if uq["unique_like_for_like"] != (worst <= 0.70 and worst_rho <= 0.90 and uq["missing"] == 0):
        errs.append("uniqueness summary inconsistent with its rows")
    if uq["candidate_dots"] != pv["n_dots"]:
        errs.append("uniqueness candidate dot count differs from the file")
    # re-derive the holdout comparison from the evidence files (bars come from the archived H88-ADHR result)
    ho_adhr = json.loads((root / "registry" / "holdout_result.json").read_text())
    bar_all = round(ho_adhr["scores"]["candidate"]["dti"], 5)
    bar_far = round(ho_adhr["far_from_visible_gt_10px_diagnostic"]["h88_adhr"]["dti"], 5)
    cbar = card["holdout"]["bar"]
    if (round(cbar["overall"], 5), round(cbar["far"], 5)) != (bar_all, bar_far):
        errs.append("holdout bar in the run card differs from the archived H88-ADHR evidence")
    far_sc = ho["pooled"]["far__candidate_fbmt"]["scores"][arm]
    beats = bool(sc["dti"] > cbar["overall"] or far_sc["dti"] > cbar["far"])
    if beats != card["holdout"]["beats_bar"]:
        errs.append("run card beats_bar differs from the evidence")
    # re-derive the verdict from its committed components (catches a hand-edited verdict)
    fp_ok = gate.fingerprint_screen(rcpt["fingerprint"])
    expected_ok = bool(portal_ok and uq["unique_like_for_like"] and ho["canary"]["passed"] and beats and fp_ok)
    if expected_ok != gv["ok_to_submit"]:
        errs.append(f"verdict not reproducible from components (expected ok_to_submit={expected_ok})")
    if (not fp_ok) and not any(r.startswith("FINGERPRINT") for r in gv["blocking_reasons"]):
        errs.append("fingerprint screen failed but is not listed as a blocking reason")
    if (not beats) and not any(r.startswith("HOLDOUT") for r in gv["blocking_reasons"]):
        errs.append("holdout bar failed but is not listed as a blocking reason")
    recomputed = None
    if full:
        # recompute fingerprint and the whole uniqueness report from bytes (needs data/: restore_inputs + restore_siblings)
        from scipy import ndimage as ndi
        from gems88 import registry_paths
        gd = grid.load_grid(root / "data" / "bridge")
        vals = gate.read_values(tif, gd.footprint)
        dots = (vals > 0) & gd.footprint
        d_cat = ndi.distance_transform_edt(~gd.catalogue)
        fpr = gate.fingerprint(dots, d_cat)
        if any(abs(fpr[k] - rcpt["fingerprint"][k]) > 1e-9 for k in fpr):
            errs.append("fingerprint recomputation differs from receipt")
        reg = registry_paths.registry_list(root, exclude=(name,))
        rep = gate.uniqueness_report(tif, reg, gd.footprint)
        if (rep["unique_like_for_like"] != uq["unique_like_for_like"] or rep["registry_rasters"] != uq["registry_rasters"]
                or abs(rep["worst_like_for_like_overlap"]["value"] - uq["worst_like_for_like_overlap"]["value"]) > 1e-9):
            errs.append("uniqueness recomputation differs from registry/uniqueness_v3.json")
        recomputed = dict(fingerprint=fpr, registry_rasters=rep["registry_rasters"], unique_like_for_like=rep["unique_like_for_like"],
                          worst_like_for_like_overlap=rep["worst_like_for_like_overlap"]["value"])
    if errs:
        raise ValueError("; ".join(errs))
    return dict(policy=gate.POLICY_VERSION, name=name, recomputed_from_bytes=recomputed, raster_sha256=sha, zip_sha256=zsha, portal_parity_reopen_ok=portal_ok,
                ok_to_download=gv["ok_to_download"], ok_to_submit=gv["ok_to_submit"], label=gv["label"],
                blocking_reasons=gv["blocking_reasons"], unique_like_for_like=uq["unique_like_for_like"],
                worst_like_for_like_overlap=worst, worst_abs_rho=worst_rho)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    parser.add_argument("--full", action="store_true", help="recompute fingerprint + uniqueness from bytes (needs restored data/)")
    args = parser.parse_args()
    legacy = release_report()
    current = release_report_v3(full=args.full)
    print(json.dumps(dict(current_headline_candidate_v3=current, archived_h88_adhr_literal_gate=legacy), indent=2))
    if args.require_submit and not current["ok_to_submit"]:
        print("AUTOMATIC SUBMISSION GATE: FAIL (" + "; ".join(current["blocking_reasons"]) + "). No upload permitted.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
