#!/usr/bin/env python3
"""Independent fail-closed preflight for the canonical research artifact.

A successful default run means the file is reproducible and safe to download.
It does *not* mean it is safe to submit.  ``--require-submit`` exits 2 while any
scientific or literal registry gate is negative.  No competition API is called.
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
from gems57 import gates, grid, uniqueness, validate  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mrr_release_report(root=ROOT):
    root = Path(root)
    card_paths = (
        root / "registry/run_card.json",
        root / "docs/data/run-card.json",
        root / "docs/run_card.json",
        root / "evidence/run-card.json",
    )
    card_texts = [p.read_text(encoding="utf-8") for p in card_paths]
    if len(set(card_texts)) != 1:
        raise ValueError("canonical run-card copies are not byte-identical")
    card = json.loads(card_texts[0])

    holdout = json.loads((root / "evidence/mrr88_holdout.json").read_text())
    canaries = json.loads((root / "evidence/mrr88_canaries.json").read_text())
    primary = holdout["scores"]["mrr_bpr_candidate"]
    paired = holdout["paired_differences"]["h88_adhr_incumbent"]
    recorded = card["holdout_dti"]
    if (
        primary["dti"] != recorded["candidate"]
        or primary["ci95"] != recorded["ci95"]
        or primary["withheld_positive_pixels"] != recorded["withheld_positive_pixels"]
        or holdout["evaluator_version"] != recorded["evaluator_version"]
        or paired["delta"] != recorded["paired_delta_vs_incumbent"]
        or paired["ci95"] != recorded["paired_delta_ci95"]
    ):
        raise ValueError("run-card HOLDOUT-DTI claim lacks matching experiment evidence")
    if not canaries["passed"] or canaries["max_symmetric_auc"] > 0.90:
        raise ValueError("leakage canary failed")
    if canaries != card["leakage_canary"]:
        raise ValueError("run-card canary evidence is stale")

    tif = root / card["artifact"]
    zip_path = root / card["zip_artifact"]
    receipt_path = tif.with_suffix(".json")
    if not tif.is_file() or not zip_path.is_file() or not receipt_path.is_file():
        raise FileNotFoundError("canonical TIFF/ZIP/writer receipt is missing")
    receipt = json.loads(receipt_path.read_text())

    gd = grid.load_grid(root / "data/bridge")
    sample = root / "data/bridge/sample_submission.tif"
    mapped = root / "data/bridge/existing_faults.tif"
    if digest(sample) != grid.SHA256_SAMPLE_SUBMISSION or digest(mapped) != grid.SHA256_EXISTING_FAULTS:
        raise ValueError("owner-mirror grid/label hash differs from pinned file")
    with rasterio.open(sample) as ref:
        ref_grid = (ref.shape, ref.crs, ref.transform)
    report = gates.format_report(tif, sample, footprint=gd.footprint)
    local = validate.validate(tif, gd.footprint, gd.catalogue)
    with rasterio.open(tif) as ds:
        raster = ds.read(1)
        exact_grid = (ds.shape, ds.crs, ds.transform) == ref_grid
    if not report["ok"] or not local["all_checks_passed"] or not exact_grid:
        raise ValueError("TIFF local format/footprint/range preflight failed")
    if not np.isfinite(raster).all() or np.any(raster[~gd.footprint] != 0):
        raise ValueError("candidate has non-finite or nonzero outside-footprint cells")
    if float(raster.min()) < 0 or float(raster.max()) > 1:
        raise ValueError("candidate lies outside [0,1]")

    sha = digest(tif)
    if sha != card["raster_sha256"] or sha != receipt["sha256"]:
        raise ValueError("raster/receipt/card hash mismatch")
    if card["submission_name"] != receipt["submission_name"] or card["submission_note"] != receipt["note"]:
        raise ValueError("name/note disagreement")
    if not (0 < len(card["submission_name"]) <= 140 and 0 < len(card["submission_note"]) <= 140):
        raise ValueError("name/note length invalid")
    with zipfile.ZipFile(zip_path) as archive:
        if archive.namelist() != [tif.name] or archive.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP must contain exactly one byte-identical TIFF")
    if digest(zip_path) != card["zip_sha256"] or digest(zip_path) != receipt["zip_sha256"]:
        raise ValueError("ZIP hash mismatch")

    # Recompute final-dot comparisons from the saved TIFF against all restored,
    # SHA-pinned registry rasters.  Do not rely only on the run card's maxima.
    inventory = json.loads((root / "registry/inventory.json").read_text())
    final_audit = uniqueness.compare_to_registry(
        tif,
        inventory,
        gd.footprint,
        include_reverse=True,
        expected_grid=ref_grid,
    )
    if (
        final_audit["registry_rasters_checked"] != len(inventory["rasters"])
        or not final_audit["complete_accessible_scan"]
        or final_audit["missing_or_invalid"]
        or not final_audit["byte_unique_among_checked"]
        or not final_audit["pixel_unique_among_checked"]
    ):
        raise ValueError("final registry scan is incomplete or candidate bytes/pixels are copied")
    rows_ok = [row for row in final_audit["rows"] if "error" not in row]
    max_final_rho = max(
        abs(float(row["spearman_full_footprint"]))
        for row in rows_ok if row.get("spearman_full_footprint") is not None
    )
    max_all_overlap = max(float(row["my_dots_within_3px_of_theirs"]) for row in rows_ok)
    max_sparse_overlap = max(
        float(row["my_dots_within_3px_of_theirs"])
        for row in rows_ok
        if int(row["their_dots"]) / int(gd.footprint.sum()) <= 0.20
    )
    registry_card = card["correlation_overlap_vs_registry"]
    if (
        abs(max_final_rho - registry_card["final_max_abs_spearman"]) > 1e-6
        or abs(max_all_overlap - registry_card["final_max_forward_overlap_3px_all_rasters"]) > 1e-6
        or abs(max_sparse_overlap - registry_card["final_max_forward_overlap_3px_sparse_rasters"]) > 1e-6
        or max_final_rho > 0.90
        or max_sparse_overlap > 0.70
    ):
        raise ValueError("final registry evidence is stale or sparse/rank uniqueness failed")

    # The continuous production surface is gated before allocation and recorded
    # because the surface itself is not a competition artifact.  Verify complete
    # hash-pinned row coverage and the recorded maximum here.
    surface_audit = json.loads((root / "evidence/mrr88_surface_uniqueness.json").read_text())
    surface_rows = [row for row in surface_audit["rows"] if "error" not in row]
    inventory_hashes = {entry["sha256"] for entry in inventory["rasters"]}
    surface_hashes = {row["sha256"] for row in surface_rows}
    max_surface_rho = max(
        abs(float(row["spearman_full_footprint"]))
        for row in surface_rows if row.get("spearman_full_footprint") is not None
    )
    if (
        surface_audit["registry_rasters_checked"] != len(inventory["rasters"])
        or not surface_audit["complete_accessible_scan"]
        or surface_audit["missing_or_invalid"]
        or surface_hashes != inventory_hashes
        or abs(max_surface_rho - registry_card["surface_preplacement_max_abs_spearman"]) > 1e-6
        or max_surface_rho > 0.90
    ):
        raise ValueError("pre-placement surface registry evidence is incomplete, stale, or duplicate")

    witness = root / "data/registry/dense_17gemdoe.tif"
    witness_sha = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
    if digest(witness) != witness_sha:
        raise ValueError("registry witness hash mismatch")
    cert = uniqueness.saturation_certificate(
        witness, gd.footprint, gd.catalogue, expected_grid=ref_grid
    )
    with rasterio.open(witness) as ds:
        prior = ds.read(1)
    measured = uniqueness.dot_overlap(
        raster, (np.isfinite(prior) & (prior > 0)) & gd.footprint, 3
    )
    recorded_overlap = card["correlation_overlap_vs_registry"][
        "final_max_forward_overlap_3px_all_rasters"
    ]
    duplicate = bool(measured > 0.70)
    if not cert["universal_overlap_blocker"] or abs(measured - recorded_overlap) > 1e-9:
        raise ValueError("literal registry overlap evidence is stale")

    scientific_positive = bool(
        recorded["paired_delta_vs_incumbent"] > 0
        and recorded["paired_delta_ci95"][0] > 0
    )
    release_ok = bool(
        report["ok"] and local["all_checks_passed"] and not duplicate
        and scientific_positive and card["verdict"] == "promote"
    )
    submit_ok = bool(release_ok and card["ok_to_submit"])
    if submit_ok != bool(card["ok_to_submit"]):
        raise ValueError("run card conflicts with independently recomputed gates")
    if not card["ok_to_download"]:
        raise ValueError("valid research artifact is misreported as unavailable")

    return {
        "format_ok": True,
        "inside_no_nan": True,
        "all_finite_entire_raster": True,
        "values_0_1": True,
        "crs_shape_transform_match": True,
        "output_sha256": sha,
        "zip_one_matching_tif": True,
        "holdout_evaluator": recorded["evaluator_version"],
        "holdout_withheld_positive_pixels": recorded["withheld_positive_pixels"],
        "holdout_candidate_dti": recorded["candidate"],
        "holdout_candidate_ci95": recorded["ci95"],
        "paired_delta_vs_incumbent": recorded["paired_delta_vs_incumbent"],
        "paired_delta_ci95": recorded["paired_delta_ci95"],
        "registry_witness_sha256": cert["witness_sha256"],
        "registry_forward_overlap_3px": measured,
        "literal_duplicate": duplicate,
        "ok_to_download": True,
        "ok_to_submit": submit_ok,
        "status": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT",
        "stop_reasons": [
            "HOLDOUT: candidate DTI is below the paired recomputed incumbent",
            "UNIQUENESS: literal registry overlap with full-footprint witness is 1.0 > 0.70",
        ],
        "grid_provenance": "owner-hosted mirror; not independent organizer authentication",
        "checked_against": "data/bridge/sample_submission.tif; data/registry/dense_17gemdoe.tif",
    }



# Compatibility validators retained for the concurrent gate-v3 research artifacts.
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


def provcrest_report_v3(root=ROOT, tag="provcrest"):
    """Verify the v3 re-assessment record of a parallel-session file (PROVCREST PR #53, TILTZERO PR #59) against its bytes (no data/ needed)."""
    sys.path.insert(0, str(root / "src"))
    from gems88 import gate  # noqa: E402

    card = json.loads((root / "registry" / f"{tag}_run_card.json").read_text())
    rec = json.loads((root / "registry" / f"{tag}_gate_v3.json").read_text())
    site = json.loads((root / "docs" / "data" / f"{tag}-gate-v3.json").read_text())
    errs = []
    if rec != site:
        errs.append("site copy of the PROVCREST v3 record differs")
    tif = root / card["submission"]["file"]
    zp = root / card["submission"]["zip_file"]
    if digest(tif) != card["submission"]["sha256"] or digest(tif) != rec["sha256"]:
        errs.append(f"{tag} TIFF bytes differ from its run card / v3 record")
    if digest(zp) != rec["zip_sha256"]:
        errs.append("PROVCREST ZIP bytes differ from the v3 record")
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        e = gate.EXPECTED
        ok = (ds.count == 1 and ds.dtypes[0] == "float32" and ds.crs.to_epsg() == e["epsg"] and ds.shape == e["shape"]
              and tuple(ds.transform)[:6] == e["transform"] and bool(np.isfinite(a).all()) and float(a.min()) >= 0 and float(a.max()) <= 1)
    if not ok:
        errs.append("PROVCREST value/grid re-open failed")
    if int((a > 0).sum()) != rec["fingerprint"]["n"]:
        errs.append("PROVCREST dot count differs from the v3 record")
    fp_ok = gate.fingerprint_screen(rec["fingerprint"])
    if fp_ok != rec["fingerprint_screen_pass"]:
        errs.append("fingerprint screen flag inconsistent with its numbers")
    h = rec["holdout_cross_run"]
    if h["beats_bar"] != bool(h["dti"] > h["bar"]):
        errs.append("holdout comparison inconsistent")
    expected_ok = bool(ok and rec["uniqueness"]["unique_like_for_like"] and card["leakage_canary"]["passed"] and h["beats_bar"] and fp_ok)
    if expected_ok != rec["ok_to_submit"]:
        errs.append("PROVCREST v3 verdict not reproducible from its components")
    worst = rec["uniqueness"]["worst_like_for_like_overlap"]["value"]
    if rec["uniqueness"]["unique_like_for_like"] != (worst <= 0.70 and not rec["uniqueness"]["like_for_like_blockers"]):
        errs.append("PROVCREST uniqueness flag inconsistent with its blockers")
    if errs:
        raise ValueError("; ".join(errs))
    return dict(name=rec["name"], sha256=rec["sha256"], ok_to_download=rec["ok_to_download"], ok_to_submit=rec["ok_to_submit"], label=rec["label"],
                blocking_reasons=rec["blocking_reasons"], worst_like_for_like_overlap=worst, fingerprint_screen_pass=fp_ok,
                own_verdict=(rec.get("own_gate") or rec["pr53_own_gate"])["verdict"], pr53_own_verdict=(rec.get("own_gate") or rec["pr53_own_gate"])["verdict"])


def mvrd_report_v3(root=ROOT):
    """Verify and return the canonical H88-MVRD machine decision."""
    root = Path(root)
    card_path = root / "registry/mvrd_run_card.json"
    gate_path = root / "registry/mvrd_gate_v3.json"
    card = json.loads(card_path.read_text())
    gate_record = json.loads(gate_path.read_text())
    raster = root / card["artifact"]
    if not raster.is_file():
        raise FileNotFoundError(f"canonical MVRD artifact is missing: {raster}")
    raster_sha = digest(raster)
    if raster_sha != card["raster_sha256"] or raster_sha != gate_record["sha256"]:
        raise ValueError("canonical MVRD artifact SHA-256 does not match card/gate")
    if card.get("verdict") != "negative" or card.get("ok_to_submit") is not False:
        raise ValueError("canonical MVRD run card must remain fail-closed")
    if gate_record.get("own_gate", {}).get("verdict") != "negative" or gate_record.get("ok_to_submit") is not False:
        raise ValueError("canonical MVRD gate must remain fail-closed")
    return {
        "artifact": card["artifact"],
        "raster_sha256": raster_sha,
        "holdout_ok": bool(gate_record["holdout_cross_run"]["beats_bar"]),
        "beats_holdout_bar": bool(gate_record["holdout_cross_run"]["beats_bar"]),
        "canaries_ok": bool(card["leakage_canary"]["all_pass"]),
        "sparse_registry_ok": bool(gate_record["uniqueness"]["unique_like_for_like"]),
        "unique_like_for_like": bool(gate_record["uniqueness"]["unique_like_for_like"]),
        "literal_registry_ok": card["correlation_overlap_vs_registry"]["literal_all_positive_witness_overlap_3px"] <= 0.70,
        "distance_fingerprint_ok": bool(gate_record["fingerprint_screen_pass"]),
        "format_ok": bool(gate_record["portal_values_and_grid_ok"] and gate_record["portal_layout_parity_with_sample"]),
        "ok_to_download": bool(card["ok_to_download"]),
        "ok_to_submit": bool(card["ok_to_submit"]),
        "verdict": card["verdict"],
    }


def release_report(root=ROOT):
    """Reopen current MVRD bytes and independently derive the fail-closed verdict."""
    root = Path(root)
    mvrd = mvrd_report_v3(root)
    card = json.loads((root / "registry/mvrd_run_card.json").read_text())
    tif = root / card["artifact"]
    zip_path = root / card["zip_artifact"]
    sample = root / "data/bridge/sample_submission.tif"
    mapped = root / "data/bridge/existing_faults.tif"
    witness = root / "data/registry/dense_17gemdoe.tif"
    missing = [str(path) for path in (sample, mapped, witness) if not path.is_file()]
    if missing:
        raise FileNotFoundError("required current-release audit input is missing: " + ", ".join(missing))

    gd = grid.load_grid(root / "data/bridge")
    if digest(sample) != grid.SHA256_SAMPLE_SUBMISSION or digest(mapped) != grid.SHA256_EXISTING_FAULTS:
        raise ValueError("owner-mirror grid/label hash differs from pinned file")
    with rasterio.open(sample) as ref, rasterio.open(tif) as ds:
        ref_grid = (ref.shape, ref.crs, ref.transform)
        raster = ds.read(1)
        sample_match = bool(ds.count == 1 and ds.dtypes[0] == "float32" and (ds.shape, ds.crs, ds.transform) == ref_grid)
        nodata_none = ds.nodata is None
    inside_no_nan = bool(np.isfinite(raster[gd.footprint]).all())
    outside_no_nan = bool(np.isfinite(raster[~gd.footprint]).all())
    values_0_1 = bool(np.isfinite(raster).all() and float(raster.min()) >= 0 and float(raster.max()) <= 1)
    no_positive_outside = not bool(((raster > 0) & ~gd.footprint).any())
    local = validate.validate(tif, gd.footprint, gd.catalogue)
    portal = gates.format_report(tif, sample, footprint=gd.footprint)

    with rasterio.open(witness) as ds:
        prior = ds.read(1)
    prior_dots = (np.isfinite(prior) & (prior > 0)) & gd.footprint
    measured_overlap = uniqueness.dot_overlap(raster, prior_dots, 3)
    literal_duplicate = bool(measured_overlap > 0.70)

    zip_ok = False
    with zipfile.ZipFile(zip_path) as archive:
        zip_ok = archive.namelist() == [tif.name] and archive.read(tif.name) == tif.read_bytes()
    format_ok = bool(
        sample_match and nodata_none and inside_no_nan and outside_no_nan and values_0_1
        and no_positive_outside and local["all_checks_passed"] and portal["ok"] and zip_ok
        and mvrd["format_ok"]
    )
    ok_to_submit = bool(
        format_ok and mvrd["holdout_ok"] and mvrd["canaries_ok"]
        and mvrd["sparse_registry_ok"] and not literal_duplicate
        and mvrd["distance_fingerprint_ok"] and card.get("ok_to_submit") is True
    )
    return {
        "candidate": "H88-MVRD",
        "file": card["artifact"],
        "file_sha256": mvrd["raster_sha256"],
        "zip_file": card["zip_artifact"],
        "zip_sha256": digest(zip_path),
        "name": card["submission_name"],
        "note": card["submission_note"],
        "note_length": card["submission_note_length"],
        "format_ok": format_ok,
        "format_valid": format_ok,
        "inside_no_nan": inside_no_nan,
        "outside_no_nan": outside_no_nan,
        "all_finite_entire_raster": bool(inside_no_nan and outside_no_nan),
        "values_0_1": values_0_1,
        "crs_shape_transform_match": sample_match,
        "positive_pixels": int(((raster > 0) & gd.footprint).sum()),
        "zip_one_matching_tif": zip_ok,
        "holdout_evaluator": card["holdout_dti"]["evaluator_version"],
        "holdout_withheld_positive_pixels": card["holdout_dti"]["withheld_positive_pixels"],
        "holdout_candidate_dti": card["holdout_dti"]["candidate"],
        "holdout_candidate_ci95": card["holdout_dti"]["ci95"],
        "paired_delta_vs_incumbent": card["holdout_dti"]["paired_delta_vs_h88_adhr"]["delta"],
        "paired_delta_ci95": card["holdout_dti"]["paired_delta_vs_h88_adhr"]["ci95"],
        "holdout_dti": card["holdout_dti"]["candidate"],
        "incumbent_best_dti": card["holdout_dti"]["h88_adhr_incumbent"]["dti"],
        "registry_forward_overlap_3px": measured_overlap,
        "literal_registry_overlap_3px": measured_overlap,
        "literal_duplicate": literal_duplicate,
        "duplicate": literal_duplicate,
        "sparse_registry_ok": mvrd["sparse_registry_ok"],
        "distance_fingerprint_ok": mvrd["distance_fingerprint_ok"],
        "ok_to_download": bool(card["ok_to_download"] and format_ok),
        "research_download_ok": bool(card["ok_to_download"] and format_ok),
        "ok_to_submit": ok_to_submit,
        "verdict": "negative" if not ok_to_submit else "selector-required",
        "status": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT" if not ok_to_submit else "SELECTOR REQUIRED",
        "stop_reasons": [
            "UNIQUENESS: literal registry overlap with full-footprint witness is 1.0 > 0.70",
            "FINGERPRINT: only 2.87% of final dots are >25 catalogue pixels away; requires 35%",
        ],
        "organizer_confirmed_score": None,
        "weekly_slots_used": 0,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-submit", action="store_true")
    args = parser.parse_args()
    try:
        result = release_report()
    except OSError as exc:
        print(json.dumps({
            "status": "BLOCKED_VALIDATION_UNAVAILABLE",
            "ok_to_download": False,
            "ok_to_submit": False,
            "stop_reasons": [f"LOCAL INPUTS MISSING OR UNREADABLE: {exc}"],
        }, indent=2))
        print("AUTOMATIC PREFLIGHT: INCOMPLETE. No upload permitted.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if args.require_submit and not result["ok_to_submit"]:
        print("AUTOMATIC SUBMISSION GATE: FAIL. No upload permitted.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
