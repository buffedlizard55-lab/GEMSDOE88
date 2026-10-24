#!/usr/bin/env python3
"""Production emission + machine gate for the GEMSDOE88 session-4 candidate.

Fits the arm named on the command line on the FULL visible catalogue (the arm itself was
validated by ``run_halo_experiments.py``), allocates dots with the vendored exact Dinkelbach
allocator, repairs lane overlap pre-placement if (and only if) a registry raster blocks,
writes a portal-parity GeoTIFF + single-member ZIP, then runs every gate:

  format (portal-parity re-open, zip member, second decoder) -> uniqueness vs 215 rasters
  (literal AND like-for-like) -> fingerprint screen -> canary -> holdout bar -> name/note.

Outputs: docs/downloads/<name>.{tif,zip,json,format-audit.json}, registry/gate_verdict.json,
registry/uniqueness_v3.json.  Spends 0 DrivenData slots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import emit, grid as grid_mod, holdout  # noqa: E402
from gems88 import gate, halo, physics, portal_writer, registry_paths  # noqa: E402

HID_RATIO = 11_321 / 48_340   # hidden / visible, seed-20 buffered whole-component draw (fold-sum k_est checked in the runner)
HALO_PX = 3.0
BAR_OVERALL = 0.18789         # stored H88-ADHR pooled HOLDOUT-DTI (gems57-pooled-hide-v2, n=22,893)
BAR_FAR = 0.11478


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="base", choices=["base", "fbmt"])
    ap.add_argument("--stem", default="gems88-phys44-halo3-dinkelbach")
    ap.add_argument("--halo", type=float, default=HALO_PX)
    ap.add_argument("--holdout-json", default="evidence/halo_experiments_20261024.json")
    ap.add_argument("--max-repair", type=int, default=3)
    args = ap.parse_args()
    t0 = time.monotonic()
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    sample = ROOT / "data" / "bridge" / "sample_submission.tif"
    names = list(physics.ALL_PHYS_FEATURES)
    N = int(fp.sum())
    X = np.memmap(ROOT / ".cache/gems88/x_phys_44ch.dat", dtype="float32", mode="r", shape=(N, len(names)))
    d_cat = ndi.distance_transform_edt(~cat)

    print("[1/6] OUT-OF-FOLD production surface (the procedure the holdout validated) ...", flush=True)
    # IR-88-63: fitting on the full catalogue and predicting the same pixels is IN-SAMPLE; the surface then
    # memorises known faults (attempt 1: 6.4% of dots >25 px from the catalogue vs 41% out-of-fold).
    quad = holdout.quadrant_ids(fp)
    p = np.zeros(fp.shape, np.float32)
    allowed = np.zeros(fp.shape, bool)
    k_est = 0.0
    metas = []
    for q in range(4):
        n_vis_tr = int((cat & fp & (quad != q)).sum())
        clf, meta = halo.fit_fold_models(X, g, cat, quad, q, round(HID_RATIO * n_vis_tr), seed=88_2026 + q, mode=args.arm)
        pq, _mq, aq, kq = halo.predict_calibrated(clf, X, g, cat, fp & (quad == q), meta["hid_ratio"], args.halo)
        p += pq
        allowed |= aq
        k_est += kq
        metas.append(dict(quadrant=holdout.FOLD_NAMES[q], k_est=kq, positives=meta["n_pos"]))
        print(f"      {holdout.FOLD_NAMES[q]}: pos={meta['n_pos']} k_est={kq:.0f} ({time.monotonic()-t0:.0f}s)", flush=True)
        del clf
    m = np.clip(emit.expected_credit(p), p, 1.0).astype(np.float32)
    meta = dict(n_pos=int(cat.sum()), hid_ratio=HID_RATIO, quadrants=metas, oof=True)

    registry = registry_paths.registry_list(exclude=(args.stem,))
    print(f"[2/6] allocation + pre-placement lane check against {len(registry)} registry rasters ...", flush=True)
    repair_log, blocked_zone = [], np.zeros(fp.shape, bool)
    for it in range(args.max_repair + 1):
        alloc = emit.dinkelbach_allocate(p, m, allowed & ~blocked_zone, budget=None, k_truth=k_est,
                                         min_spacing_px=2.05, dinkelbach_iters=6)
        dots = alloc.emitted.astype(bool) & fp
        tmp = ROOT / ".cache" / "candidate_tmp.tif"
        portal_writer.write_portal_tif(tmp, dots.astype(np.float32), sample, fp)
        rep = gate.uniqueness_report(tmp, registry, fp, surface=p)
        repair_log.append(dict(iteration=it, dots=int(dots.sum()), unique_like_for_like=rep["unique_like_for_like"],
                               blockers=rep["like_for_like_blockers"][:8],
                               worst=rep["worst_like_for_like_overlap"], worst_rho=rep["worst_abs_rho"]))
        print(f"      iter {it}: dots={int(dots.sum())} unique_like_for_like={rep['unique_like_for_like']} "
              f"worst={rep['worst_like_for_like_overlap']}", flush=True)
        if rep["unique_like_for_like"]:
            break
        # lane repair: forbid the 3-px zone of every blocking raster's dots, then re-allocate
        for r in rep["rows"]:
            if r.get("blocks_like_for_like") and not r.get("dense"):
                vals = gate.read_values(r["path"], fp)
                blocked_zone |= ndi.distance_transform_edt(~((vals > 0) & fp)) <= 3.0
    n_dots = int(dots.sum())
    sha8_dots = hashlib.sha256(np.packbits(dots).tobytes()).hexdigest()[:8]
    uniq = dict(rep, candidate="(final)")  # identical pixels to the last loop iteration (same writer)
    fprint = gate.fingerprint(dots, d_cat)
    fp_pass = gate.fingerprint_screen(fprint)
    ho = json.loads((ROOT / args.holdout_json).read_text())
    sc_all = ho["pooled"]["all__candidate_fbmt"]["scores"][args.arm]
    sc_far = ho["pooled"]["far__candidate_fbmt"]["scores"][args.arm]
    beats = bool(sc_all["dti"] > BAR_OVERALL or sc_far["dti"] > BAR_FAR)
    canary_ok = bool(ho["canary"]["passed"])
    used = [l.split(":", 1)[-1] for l, _ in registry]

    def full_verdict(portal, name, note):
        v = gate.decide(portal=portal, uniqueness=uniq, canary_passed=canary_ok, holdout_beats_bar=beats,
                        name=name, note=note, used_names=used)
        if not fp_pass:
            v["blocking_reasons"].append("FINGERPRINT: catalogue-hugging profile (owner-reported fleet screen)")
            v["ok_to_submit"] = False
            v["label"] = "OK TO DOWNLOAD - NOT OK TO SUBMIT" if v["ok_to_download"] else v["label"]
        return v

    # stage 1: verdict from the temporary file decides the filename suffix
    portal0 = gate.portal_validate(tmp, sample, fp)
    note = (f"GEMS88 label-blind 44-layer geophysics+topography classifier, 300 m halo, exact-DTI dots; {n_dots} dots. "
            "Holdout negative vs ADHR bar.")
    v0 = full_verdict(portal0, f"{args.stem}-{n_dots}dots-20261024-{sha8_dots}", note)
    suffix = "GATE-PASS" if v0["ok_to_submit"] else "DO-NOT-SUBMIT"
    name = f"{args.stem}-{n_dots}dots-20261024-{sha8_dots}-{suffix}"
    if not v0["ok_to_submit"] and len(note) > 140:
        raise SystemExit("note too long")
    assert len(note) <= 140 and len(name) <= 140, (len(note), len(name))

    print("[3/6] writing portal-parity TIF + ZIP ...", flush=True)
    dl = ROOT / "docs" / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    tif = dl / f"{name}.tif"
    zp = dl / f"{name}.zip"
    portal_writer.write_portal_tif(tif, dots.astype(np.float32), sample, fp)
    portal_writer.write_single_member_zip(zp, tif)

    print("[4/6] gates on the FINAL files ...", flush=True)
    portal_tif = gate.portal_validate(tif, sample, fp)
    portal_zip = gate.portal_validate(zp, sample, fp)
    portal = dict(ok=bool(portal_tif["ok"] and portal_zip["ok"]), problems=portal_tif["problems"] + portal_zip["problems"],
                  tif=portal_tif, zip=portal_zip,
                  tif_zip_same_pixels=portal_tif["array_sha256"] == portal_zip["array_sha256"])
    if not portal["tif_zip_same_pixels"]:
        portal["ok"] = False
        portal["problems"].append("ZIP member pixels differ from the TIF")
    uniq["candidate"] = str(tif)
    verdict = full_verdict(portal, name, note)
    assert verdict["ok_to_submit"] == v0["ok_to_submit"], "verdict changed between stage 1 and the final files"

    print("[5/6] receipts ...", flush=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    receipt = dict(
        name=name, note=note, note_len=len(note), generated_utc=now, arm=args.arm, n_dots=n_dots,
        sha256=gate.sha256_file(tif), zip_sha256=gate.sha256_file(zp), tif=tif.name, zip=zp.name,
        bytes_tif=tif.stat().st_size, bytes_zip=zp.stat().st_size,
        production_fit=dict(positives=meta["n_pos"], hid_ratio=meta["hid_ratio"], k_est=k_est, halo_px=args.halo,
                            allocator="vendor/gems57/emit.dinkelbach_allocate budget=None min_spacing_px=2.05 dinkelbach_iters=6",
                            features=names, repair_log=repair_log),
        fingerprint=fprint, fingerprint_screen=dict(passed=fp_pass, rule="share_le2==0 and share_gt25>=%.2f" % gate.FP_SCREEN_MIN_GT25),
        holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=ho["evaluator_version"], arm=args.arm,
                     overall=dict(dti=sc_all["dti"], ci95=sc_all["ci95"], withheld_positives=sc_all["withheld_positive_pixels"]),
                     far_subset=dict(dti=sc_far["dti"], ci95=sc_far["ci95"], withheld_positives=sc_far["withheld_positive_pixels"]),
                     bar=dict(overall=BAR_OVERALL, far=BAR_FAR, source="registry/holdout_result.json (H88-ADHR)"), beats_bar=beats),
        canary=dict(max_symmetric_auc=ho["canary"]["max_symmetric_auc"], passed=canary_ok),
        verdict=verdict, seconds=round(time.monotonic() - t0, 1))
    (dl / f"{name}.json").write_text(json.dumps(receipt, indent=1, default=float))
    (dl / f"{name}.format-audit.json").write_text(json.dumps(portal, indent=1, default=float))
    slim = {k: v for k, v in uniq.items() if k != "rows"}
    slim["rows"] = [{k: r.get(k) for k in ("label", "dense", "registry_dots", "literal_overlap_3px", "like_for_like_overlap_3px",
                                            "rho_final", "rho_preplacement", "blocks_literal", "blocks_like_for_like", "duplicate_of", "error")}
                    for r in uniq["rows"]]
    (ROOT / "registry" / "uniqueness_v3.json").write_text(json.dumps(slim, indent=1, default=float))
    (ROOT / "registry" / "gate_verdict.json").write_text(json.dumps(
        dict(name=name, sha256=receipt["sha256"], zip_sha256=receipt["zip_sha256"], generated_utc=now, **verdict), indent=1))
    print("[6/6] VERDICT:", verdict["label"], "|", verdict["blocking_reasons"], flush=True)
    print(json.dumps(dict(name=name, dots=n_dots, fingerprint=fprint, overall=sc_all["dti"], far=sc_far["dti"],
                          worst_overlap=uniq["worst_like_for_like_overlap"], worst_rho=uniq["worst_abs_rho"]), indent=1))


if __name__ == "__main__":
    main()
