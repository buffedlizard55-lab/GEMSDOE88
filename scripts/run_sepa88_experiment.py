#!/usr/bin/env python3
"""Run the preregistered H88-SEPA 3-experiment holdout suite and emit the candidate GeoTIFF.

Lane: H88-SEPA — 18 zero-catalogue seismic-strain partitioning and
potential-field persistence-anisotropy channels (``src/gems88/sepa.py``) on
the shared 44-channel physics stack. Fold machinery is the shared
``tdkl.predict_tdkl_all_arms_fold`` (controls: phys44 zero-cat, H88-ADHR
incumbent; Exp1 zero-cat PoE, Exp2 single joint, Exp3 dual-head PoE) with a
separate SEPA cache directory. Evaluator/writer/uniqueness are the shared
``vendor/gems57`` + ``src/gems88`` modules; the binding gate is
``gate.decide_v4`` (IR-88-127). Preregistration:
``registry/preregistration_sepa88.json``.
"""
from __future__ import annotations

# No candidate generation or unsupported clearance may precede the shared stop.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import gc
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import damagezone_envelope, evaluate_holdout, grid as grid_mod, holdout, submission_writer, uniqueness  # noqa: E402
from gems57 import gates as g57gates  # noqa: E402
from gems57 import validate as g57validate  # noqa: E402
from gems88 import adhr, edge, gate, physics, portal_writer, sepa, tdkl  # noqa: E402
from gems88.registry_paths import registry_list  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

BLOCK_SIDE = 200
BOOT_DRAWS = 2000
BOOT_SEED = 520925
DATE = "20261025"
ARMS_MAP = {
    "phys44_zero_cat": "phys44_zero_cat",
    "h88_adhr_incumbent": "h88_adhr_incumbent",
    "tdkl_phys_only": "exp01_sepa_zero_cat",
    "tdkl_single_79": "exp02_sepa_single_joint",
    "h88_tdkl": "exp03_sepa_poe",
}
CANDIDATE = "exp03_sepa_poe"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_canary(zero_cat_groups, vis_by_seed, g, folds_by_seed) -> dict:
    """Every feature alone on withheld positives; symmetric AUC > 0.90 = leakage until proven otherwise."""
    ys, xs = np.nonzero(g.footprint)
    rows, max_sym, max_feat = [], 0.0, ""
    max_zero_sym, max_zero_feat = 0.0, ""
    for seed, folds in folds_by_seed:
        hidden = folds[0]["hidden_all"][ys, xs]
        vis = folds[0]["visible"][ys, xs]
        pos = np.flatnonzero(hidden)
        neg_pool = np.flatnonzero(~hidden & ~vis)
        rng = np.random.default_rng(8800 + seed)
        neg = rng.choice(neg_pool, size=min(8 * len(pos), len(neg_pool)), replace=False)
        sel = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), dtype=np.int32), np.zeros(len(neg), dtype=np.int32)])
        X_vis22, d_vis_fp, comp_len_fp = vis_by_seed[seed]
        tr_tru = np.logical_or.reduce([folds[j]["truth"] for j in range(1, 4)])
        wlaw = damagezone_envelope.fit_width_law(comp_len_fp, d_vis_fp, tr_tru[ys, xs], quantile=0.90, l0_px=40.0)
        d_over_w = (d_vis_fp / np.maximum(wlaw.half_width(comp_len_fp), 1e-6)).astype(np.float32)[:, None]
        groups = list(zero_cat_groups) + [
            (X_vis22, list(adhr.VIS_STRUCT_FEATURES[:22]), "VIS-22"),
            (d_over_w, [adhr.VIS_STRUCT_FEATURES[22]], "VIS-22"),
        ]
        for X, names, group in groups:
            for j, name in enumerate(names):
                vals = np.asarray(X[sel, j], dtype=np.float64)
                auc = float(roc_auc_score(y, vals))
                sym = max(auc, 1.0 - auc)
                if sym > max_sym:
                    max_sym, max_feat = sym, f"{name} (seed={seed})"
                if group != "VIS-22" and sym > max_zero_sym:
                    max_zero_sym, max_zero_feat = sym, f"{name} (seed={seed})"
                if seed == 20:
                    rows.append({"feature": name, "group": group, "roc_auc": round(auc, 6),
                                 "symmetric_auc": round(sym, 6)})
    rows.sort(key=lambda r: r["symmetric_auc"], reverse=True)
    passed = bool(max_sym <= 0.90)
    if not passed:
        raise RuntimeError(f"STOP: single-feature leakage canary tripped: {max_feat} = {max_sym:.6f} > 0.90")
    total = int(sum(len(n) for _, n, _ in zero_cat_groups) + len(adhr.VIS_STRUCT_FEATURES))
    return {"passed": passed, "threshold": 0.90, "features_tested": total,
            "zero_catalogue_features_tested": int(sum(len(n) for _, n, _ in zero_cat_groups)),
            "fold_visible_features_tested": len(adhr.VIS_STRUCT_FEATURES),
            "max_symmetric_auc": round(float(max_sym), 6), "max_feature": max_feat,
            "max_zero_catalogue_symmetric_auc": round(float(max_zero_sym), 6),
            "max_zero_catalogue_feature": max_zero_feat,
            "sepa_features": [r for r in rows if r["group"] == "SEPA-18"],
            "top15_all_features": rows[:15]}


def collect_registry(root: Path) -> list[tuple[str, Path]]:
    """registry_list() + this repo's submissions/ and releases/ rasters (own lane excluded)."""
    entries = list(registry_list(root, exclude=("sepa88",)))
    seen = {p.resolve() for _, p in entries}
    for sub in ("submissions", "releases"):
        d = root / sub
        if d.is_dir():
            for p in sorted(d.glob("*.tif")):
                if "sepa88" in p.name or p.resolve() in seen:
                    continue
                seen.add(p.resolve())
                entries.append((f"GEMSDOE88-{sub}:{p.name}", p))
    head_dir = root / "data/siblings_head"
    if head_dir.is_dir():
        for p in sorted(head_dir.glob("*.tif")):
            if p.resolve() in seen:
                continue
            seen.add(p.resolve())
            entries.append((f"sibling_head:{p.name}", p))
    return entries


def main() -> int:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_sepa88.json").read_text(encoding="utf-8"))
    if prereg.get("frozen_before_feature_canary_holdout_or_production_build") is not True:
        raise RuntimeError("Preregistration must be frozen before running experiments")

    print("[1/7] Grid + 44-ch physics + 18-ch SEPA memmaps...", flush=True)
    g = grid_mod.load_grid(ROOT / "data/bridge")
    shared_cache = ROOT / ".cache/gems88"
    sepa_cache = ROOT / ".cache/gems88_sepa"
    sepa_cache.mkdir(parents=True, exist_ok=True)
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, shared_cache)
    X_sepa, sepa_meta = sepa.build_or_load_sepa_memmap(ROOT, g, sepa_cache)
    print(f"      SEPA-18 ready: {sepa_meta['features']}", flush=True)

    with rasterio.open(ROOT / "data/training_features.tif") as src:
        if src.tags(12).get("band_name") != "det_elev":
            raise ValueError("Band 12 must be det_elev (IR-88-110 guard)")
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
    scarp_fields = adhr.compute_scarp_fields(det_elev, g.footprint, sepa_cache)
    del det_elev
    gc.collect()
    sense_src = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)

    folds_by_seed: list[tuple[int, list[dict]]] = []
    vis_by_seed: dict[int, tuple] = {}
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        for f in folds[1:]:
            if not np.array_equal(f["visible"], folds[0]["visible"]):
                raise RuntimeError("visible mask differs across quadrant folds of one seed draw")
        folds_by_seed.append((seed, folds))
        tag = "seed20_f0_NW" if seed == 20 else f"seed{seed}_f0_NW"
        vis_by_seed[seed] = adhr.compute_visible_struct_fp(
            g, folds[0]["visible"], sense_src, scarp_fields, sepa_cache, tag)

    print("[2/7] Single-feature leakage canary (62 zero-catalogue + 23 fold-visible)...", flush=True)
    canary_path = ROOT / "evidence/sepa88_canaries.json"
    if canary_path.is_file() and "--recompute-canary" not in sys.argv:
        canary = json.loads(canary_path.read_text(encoding="utf-8"))
        print(f"      LOADED CACHED CANARY max={canary['max_symmetric_auc']}", flush=True)
    else:
        canary = run_canary(
            [(X_phys, list(physics.ALL_PHYS_FEATURES), "PHYS-44"),
             (X_sepa, list(sepa.SEPA_FEATURES), "SEPA-18")],
            vis_by_seed, g, folds_by_seed)
        write_json(canary_path, canary)
    print(f"      PASS {canary['features_tested']} features; max symmetric AUC = "
          f"{canary['max_symmetric_auc']:.6f} ({canary['max_feature']}); "
          f"max zero-cat = {canary['max_zero_catalogue_symmetric_auc']:.6f}", flush=True)

    print("[3/7] 8-fold buffered holdout (2 controls + 3 preregistered experiments)...", flush=True)
    holdout_path = ROOT / "evidence/sepa88_holdout_20261025.json"
    if holdout_path.is_file() and "--recompute-holdout" not in sys.argv:
        payload = json.loads(holdout_path.read_text(encoding="utf-8"))
        pooled_overall = payload["pooled_overall"]
        pooled_far10 = payload["pooled_far_gt10px"]
        pooled_blind25 = payload["pooled_blind_gt25px"]
        fold_rows = payload["folds"]
        print(f"      LOADED CACHED HOLDOUT {CANDIDATE} = {pooled_overall['scores'][CANDIDATE]['dti']:.6f}", flush=True)
    else:
        arms = tuple(ARMS_MAP.values())
        terms = {k: {a: None for a in arms} for k in ("ov", "far", "blind")}
        fold_rows = []
        for seed, folds in folds_by_seed:
            X_vis22, d_vis_fp, comp_len_fp = vis_by_seed[seed]
            d_vis_grid = ndi.distance_transform_edt(~folds[0]["visible"]).astype(np.float32)
            for i, fold in enumerate(folds):
                qname = str(fold["name"])
                tag = f"seed{seed}_f{i}_{qname}"
                train_regions = np.logical_or.reduce([folds[j]["region"] for j in range(4) if j != i])
                train_truth = np.logical_or.reduce([folds[j]["truth"] for j in range(4) if j != i])
                res_raw = tdkl.predict_tdkl_all_arms_fold(
                    g, X_phys, X_sepa, X_vis22, d_vis_fp, comp_len_fp, fold["visible"],
                    train_regions, train_truth, fold["region"], seed=seed * 10 + i,
                    cache_dir=sepa_cache, fold_tag=tag)
                res = {ARMS_MAP[k]: v for k, v in res_raw.items()}
                far_truth = fold["truth"] & fold["region"] & ~fold["masked_known"] & (d_vis_grid > 10.0)
                far_valid = g.footprint & fold["region"] & ~fold["masked_known"] & (d_vis_grid > 10.0)
                far_fold = {**fold, "truth": far_truth, "region": far_valid, "masked_known": np.zeros_like(far_valid)}
                blind_truth = fold["truth"] & fold["region"] & ~fold["masked_known"] & (d_vis_grid > 25.0)
                blind_valid = g.footprint & fold["region"] & ~fold["masked_known"] & (d_vis_grid > 25.0)
                blind_fold = {**fold, "truth": blind_truth, "region": blind_valid, "masked_known": np.zeros_like(blind_valid)}
                row = {"seed": seed, "fold": qname,
                       "withheld_positive_pixels": int((fold["truth"] & fold["region"] & ~fold["masked_known"]).sum()),
                       "far_withheld_positive_pixels": int(far_truth.sum()),
                       "blind_withheld_positive_pixels": int(blind_truth.sum())}
                for arm in arms:
                    emitted, _, meta = res[arm]
                    sc_ov, bt_ov = evaluate_holdout.evaluate(emitted, fold, g.footprint, block_side=BLOCK_SIDE)
                    sc_fr, bt_fr = evaluate_holdout.evaluate(emitted, far_fold, g.footprint, block_side=BLOCK_SIDE)
                    sc_bl, bt_bl = evaluate_holdout.evaluate(emitted, blind_fold, g.footprint, block_side=BLOCK_SIDE)
                    for key, bt in (("ov", bt_ov), ("far", bt_fr), ("blind", bt_bl)):
                        terms[key][arm] = bt if terms[key][arm] is None else terms[key][arm] + bt
                    row[arm] = {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                                "overall_dti": round(float(sc_ov["dti"]), 6),
                                "far_gt10px_dti": round(float(sc_fr["dti"]), 6),
                                "blind_gt25px_dti": round(float(sc_bl["dti"]), 6),
                                "emitted_dots": int(meta["n_dots"])}
                fold_rows.append(row)
                print(f"      [seed={seed} {qname}] ADHR={row['h88_adhr_incumbent']['overall_dti']:.6f} | "
                      f"Exp1={row['exp01_sepa_zero_cat']['overall_dti']:.6f} | "
                      f"Exp2={row['exp02_sepa_single_joint']['overall_dti']:.6f} | "
                      f"Exp3={row[CANDIDATE]['overall_dti']:.6f} "
                      f"(far={row[CANDIDATE]['far_gt10px_dti']:.6f}, blind={row[CANDIDATE]['blind_gt25px_dti']:.6f})", flush=True)
        pooled_overall = evaluate_holdout.pooled_summary(terms["ov"], draws=BOOT_DRAWS, seed=BOOT_SEED, candidate=CANDIDATE)
        pooled_far10 = evaluate_holdout.pooled_summary(terms["far"], draws=BOOT_DRAWS, seed=BOOT_SEED + 1, candidate=CANDIDATE)
        pooled_blind25 = evaluate_holdout.pooled_summary(terms["blind"], draws=BOOT_DRAWS, seed=BOOT_SEED + 2, candidate=CANDIDATE)
        payload = {"schema_version": "gems88-sepa88-holdout-v1",
                   "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "preregistration_id": prereg["preregistration_id"], "evidence_class": "HOLDOUT-DTI",
                   "evaluator_version": evaluate_holdout.VERSION, "seeds": [20, 21], "n_folds": 8,
                   "bootstrap_draws": BOOT_DRAWS, "spatial_block_m": BLOCK_SIDE * 100.0, "canary": canary,
                   "pooled_overall": pooled_overall, "pooled_far_gt10px": pooled_far10,
                   "pooled_blind_gt25px": pooled_blind25, "folds": fold_rows,
                   "stored_baselines": {
                       "h88_hgvc_current_best": prereg["promotion_bar"]["current_holdout_best"],
                       "h88_adhr_stored": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": "gems57-pooled-hide-v2",
                                           "withheld_positive_pixels": 22893, "overall_dti": 0.189634},
                       "h33_owner_claim": {"evidence_class": "USER-REPORTED (no portal receipt in repo)",
                                           "submission_id": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
                                           "reported_public_dti": 0.2778}}}
        write_json(holdout_path, payload)
        write_json(ROOT / "docs/evidence/sepa88_holdout_20261025.json", payload)
    if "--stop-after-holdout" in sys.argv:
        print("Holdout stage complete.", flush=True)
        return 0

    ov = pooled_overall["scores"][CANDIDATE]
    fr = pooled_far10["scores"][CANDIDATE]
    bl = pooled_blind25["scores"][CANDIDATE]
    delta_adhr = pooled_overall["paired_differences"]["h88_adhr_incumbent"]
    folds_won = sum(1 for r in fold_rows if r[CANDIDATE]["overall_dti"] > r["h88_adhr_incumbent"]["overall_dti"])
    beats_hgvc_point = bool(ov["dti"] > prereg["promotion_bar"]["current_holdout_best"]["dti"])
    paired_ci_pos = bool(delta_adhr["ci95"][0] > 0.0)
    print(f"      POOLED {CANDIDATE}: {ov['dti']:.6f} CI {ov['ci95']} (delta vs ADHR "
          f"{delta_adhr['delta']:+.6f} CI {delta_adhr['ci95']}, {folds_won}/8 folds; "
          f"beats HGVC 0.202947 point: {beats_hgvc_point})", flush=True)

    print("[4/7] Production fit + H33-parity emission (37,654 dots)...", flush=True)
    prod_emitted, prod_surface, prod_meta = sepa.fit_and_emit_production_sepa(
        g, X_phys, X_sepa, sense_src, scarp_fields, sepa_cache, seed=8825)
    d_cat_grid = ndi.distance_transform_edt(~g.catalogue).astype(np.float32)
    fp_prof = gate.fingerprint(prod_emitted > 0, d_cat_grid)
    fp_pass = gate.fingerprint_screen(fp_prof)
    print(f"      Emitted {prod_meta['n_dots']} dots; fingerprint {fp_prof}; screen_pass={fp_pass}", flush=True)

    print("[5/7] Registry uniqueness (surface pre-placement rho + final dots, v4 + literal)...", flush=True)
    reg_entries = collect_registry(ROOT)
    print(f"      Registry rasters: {len(reg_entries)}", flush=True)
    sample_path = ROOT / "data/bridge/sample_submission.tif"
    with tempfile.TemporaryDirectory() as tmpd:
        tmp_dir = Path(tmpd)
        sw_tif = tmp_dir / "sw_check.tif"
        sw_receipt = submission_writer.write_submission(
            sw_tif, prod_emitted, sample_path, g.footprint,
            name="GEMSDOE88-SEPA88-SWCHECK", note="SEPA88 shared submission_writer preflight check",
            catalogue=g.catalogue)
        assert sw_receipt["validator"]["all_checks_passed"] is True
        lzw_tmp = tmp_dir / "portal_lzw.tif"
        portal_writer.write_portal_tif(lzw_tmp, prod_emitted, sample_path, g.footprint)
        prelim_sha = sha256_file(lzw_tmp)
        hash8 = prelim_sha[:8]
        uq = gate.uniqueness_report(lzw_tmp, reg_entries, g.footprint, surface=prod_surface)
        surface_max_rho = float(uq["worst_abs_rho"]["value"]) if uq["worst_abs_rho"] else 0.0
        print(f"      worst |rho| = {surface_max_rho:.6f}; worst dot-field overlap = "
              f"{uq['worst_dotfield_overlap']}; worst excess = {uq['worst_excess_overlap']}; "
              f"worst literal = {uq['worst_literal_overlap']}; unique_v4={uq['unique_v4']}; "
              f"unique_literal={uq['unique_literal']}", flush=True)
        if surface_max_rho > 0.90:
            raise RuntimeError(f"STOP DUPLICATE: surface/final |rho| = {surface_max_rho:.6f} > 0.90")

        holdout_beats_bar = bool(beats_hgvc_point and paired_ci_pos and fp_pass)
        sub_name = f"GEMSDOE88-SEPA88-{hash8.upper()}"
        sub_note = (f"SEPA88 seis-strain+persist PoE 37654d; HOLDOUT-DTI {ov['dti']:.4f} "
                    f"far {fr['dti']:.4f} blind {bl['dti']:.4f}; UNSCORED")
        assert 0 < len(sub_name) <= 140 and 0 < len(sub_note) <= 140
        used_names = set()
        for p_rc in (ROOT / "registry").glob("*.json"):
            try:
                d = json.loads(p_rc.read_text(encoding="utf-8"))
                if isinstance(d, dict) and isinstance(d.get("submission_name"), str):
                    used_names.add(d["submission_name"])
            except Exception:
                pass
        portal_tmp = gate.portal_validate(lzw_tmp, sample_path, g.footprint)
        uq_for_decide = {**uq, "registry_complete": bool(uq["missing"] == 0 and uq["registry_rasters"] >= 200),
                         "surface_checked": True}
        gv = gate.decide_v4(portal=portal_tmp, uniqueness=uq_for_decide,
                            canary_passed=bool(canary["passed"]), holdout_beats_bar=holdout_beats_bar,
                            name=sub_name, note=sub_note, used_names=used_names, receipt_sha_matches=True)
        ok_submit = bool(gv["ok_to_submit"])
        verdict = "promote" if ok_submit else "negative"
        suffix = "zeros" if ok_submit else "zeros-DO-NOT-SUBMIT"
        stem = f"gems88-sepa88-seis-strain-persist-37654dots-{DATE}-{hash8}-{suffix}"
        dl_tif = ROOT / "docs/downloads" / f"{stem}.tif"
        dl_zip = ROOT / "docs/downloads" / f"{stem}.zip"
        dl_receipt = ROOT / "docs/downloads" / f"{stem}.json"
        dl_audit = ROOT / "docs/downloads" / f"{stem}.format-audit.json"
        sub_tif = ROOT / "submissions" / f"{stem}.tif"
        sub_zip = ROOT / "submissions" / f"{stem}.zip"
        sub_receipt = ROOT / "submissions" / f"{stem}.json"
        for p in (dl_tif, dl_zip, dl_receipt, dl_audit, sub_tif, sub_zip, sub_receipt):
            p.unlink(missing_ok=True)
        shutil.copy2(lzw_tmp, dl_tif)
        portal_writer.write_single_member_zip(dl_zip, dl_tif)
        shutil.copy2(dl_tif, sub_tif)
        shutil.copy2(dl_zip, sub_zip)
        for p in (dl_tif, dl_zip, sub_tif, sub_zip):
            os.chmod(p, 0o644)

    print("[6/7] Re-opening on-disk .tif/.zip for independent audits...", flush=True)
    portal_tif = gate.portal_validate(dl_tif, sample_path, g.footprint)
    portal_zip = gate.portal_validate(dl_zip, sample_path, g.footprint)
    indep = validate_artifact(dl_tif, sample_path)
    g57_fmt = g57gates.format_report(dl_tif, sample_path, footprint=g.footprint)
    g57_val = g57validate.validate(dl_tif, g.footprint, g.catalogue)
    g57validate.assert_submittable(g57_val)
    if not (portal_tif["ok"] and portal_zip["ok"] and portal_tif["layout_parity_with_sample"]
            and indep["ok"] and g57_fmt["ok"] and g57_val["all_checks_passed"]
            and portal_tif["array_sha256"] == portal_zip["array_sha256"]):
        raise RuntimeError(f"Saved format audit failed: tif={portal_tif['problems']} zip={portal_zip['problems']}")
    tif_sha, zip_sha = sha256_file(dl_tif), sha256_file(dl_zip)
    assert tif_sha == prelim_sha
    write_json(dl_audit, {"portal_tif": portal_tif, "portal_zip": portal_zip,
                          "independent_validate_artifact": indep,
                          "shared_gates_format_report": g57_fmt, "shared_validate": g57_val})

    print("[7/7] Run card + gate verdict + uniqueness evidence...", flush=True)
    ok_uq_rows = [r for r in uq["rows"] if "error" not in r and "duplicate_of" not in r]
    top10 = sorted(ok_uq_rows, key=lambda r: (r["literal_overlap_3px"] if not r["dense"] else -1), reverse=True)[:10]
    uq_slim = {"policy_v4": gate.POLICY_VERSION_V4, "policy_v3_literal": uq["policy"],
               "candidate": f"docs/downloads/{dl_tif.name}", "candidate_sha256": tif_sha,
               "candidate_dots": uq["candidate_dots"], "registry_rasters_checked": uq["registry_rasters"],
               "distinct_dot_sets_checked": uq["distinct_dot_sets"], "missing": uq["missing"],
               "worst_abs_rho": uq["worst_abs_rho"], "worst_dotfield_overlap": uq["worst_dotfield_overlap"],
               "worst_excess_overlap": uq["worst_excess_overlap"], "worst_literal_overlap": uq["worst_literal_overlap"],
               "worst_like_for_like_overlap": uq["worst_like_for_like_overlap"],
               "unique_v4": uq["unique_v4"], "v4_blockers": uq["v4_blockers"],
               "unique_literal": uq["unique_literal"], "literal_blockers": uq["literal_blockers"],
               "space_filling_rasters": uq["space_filling_rasters"],
               "top10_dotfield_overlap": [{"label": r["label"], "overlap": r["literal_overlap_3px"]} for r in top10],
               "vacuity_witness": uq["vacuity_witness"],
               "scope": "registry/inventory.json + data/registry + data/fleet + data/siblings (pinned commits) + docs/downloads + submissions + releases present in this checkout; live unindexed sources are a stated limitation, never a claim of absence."}
    write_json(ROOT / "evidence/sepa88_uniqueness_20261025.json", uq_slim)
    write_json(ROOT / "docs/evidence/sepa88_uniqueness_20261025.json", uq_slim)

    writer_meta = {"file": dl_tif.name, "zip_file": dl_zip.name, "sha256": tif_sha, "zip_sha256": zip_sha,
                   "submission_name": sub_name, "submission_note": sub_note, "note_length": len(sub_note),
                   "positive_pixels": int(prod_meta["n_dots"]), "ok_to_download": True,
                   "ok_to_submit": ok_submit, "verdict": verdict, "weekly_slots_spent": 0,
                   "organizer_confirmed_score": None}
    write_json(dl_receipt, writer_meta)
    write_json(sub_receipt, writer_meta)

    gate_doc = {"schema": "gems88.sepa88.gate_v4.v1", **gv,
                "name": stem, "submission_name": sub_name, "submission_note": sub_note,
                "candidate": {"tif": f"docs/downloads/{dl_tif.name}", "zip": f"docs/downloads/{dl_zip.name}",
                              "sha256": tif_sha, "zip_sha256": zip_sha, "dots": int(prod_meta["n_dots"])},
                "sha256": tif_sha, "zip_sha256": zip_sha,
                "portal_values_and_grid_ok": bool(portal_tif["ok"] and portal_zip["ok"]),
                "portal_layout_parity_with_sample": bool(portal_tif["layout_parity_with_sample"]),
                "leakage_canary_pass": bool(canary["passed"]),
                "fingerprint": fp_prof, "fingerprint_screen_pass": fp_pass,
                "holdout_comparison": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                                       "withheld_positives": int(ov["withheld_positive_pixels"]),
                                       "candidate_dti": float(ov["dti"]), "candidate_ci95": ov["ci95"],
                                       "far_gt10px_dti": float(fr["dti"]), "far_gt10px_ci95": fr["ci95"],
                                       "blind_gt25px_dti": float(bl["dti"]), "blind_gt25px_ci95": bl["ci95"],
                                       "paired_delta_vs_adhr": delta_adhr, "folds_won_vs_adhr": folds_won,
                                       "hgvc_current_best_dti": prereg["promotion_bar"]["current_holdout_best"]["dti"],
                                       "beats_hgvc_point_estimate": beats_hgvc_point,
                                       "paired_delta_ci_positive": paired_ci_pos, "beats_bar": holdout_beats_bar},
                "uniqueness": uq_slim, "weekly_slots_spent": 0, "organizer_confirmed_score": None}
    write_json(ROOT / "registry/sepa88_gate_v4.json", gate_doc)
    write_json(ROOT / "docs/data/sepa88_gate_v4.json", gate_doc)

    run_card = {"schema": "gems.run_card.v1",
                "run_id": f"GEMSDOE88-SEPA88-{DATE}-{hash8}",
                "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lane": "H88-SEPA", "preregistration_id": prereg["preregistration_id"],
                "hypothesis": prereg["hypothesis"],
                "mechanism": ("18 zero-catalogue SEPA channels (seismic structure-tensor anisotropy + Hessian "
                              "ridge/trough of ieq/deq, geodetic strain-partition fractions + strain tensor, "
                              "TMI_up150-vs-TMI and gravity deep/shallow persistence ratios, spin-2 fabric "
                              "agreements) + shared 44-ch physics + 23 fold-visible structural channels -> "
                              "dual-expectation log-odds Product-of-Experts (shared adhr/tdkl machinery) -> "
                              "H33-parity stratified Dinkelbach allocation (37,654 binary dots, d_cat>2.5px, "
                              "21,500 near @2.85px + 16,154 far @3.05px)."),
                "named_non_fault_mimic": prereg["named_non_fault_mimic"],
                "experiments_executed": 3, "experiment_budget_max": 3,
                "elapsed_seconds": round(time.monotonic() - t0, 2), "wallclock_budget_seconds_max": 7200,
                "holdout_dti": {"evidence_class": "HOLDOUT-DTI", "evaluator_version": evaluate_holdout.VERSION,
                                "seeds": [20, 21], "n_folds": 8,
                                "withheld_positive_pixels": int(ov["withheld_positive_pixels"]),
                                "candidate_exp03": ov, "far_gt10px": fr, "blind_gt25px": bl,
                                "exp01_zero_cat": pooled_overall["scores"]["exp01_sepa_zero_cat"],
                                "exp02_single_joint": pooled_overall["scores"]["exp02_sepa_single_joint"],
                                "control_phys44_zero_cat": pooled_overall["scores"]["phys44_zero_cat"],
                                "control_h88_adhr_incumbent": pooled_overall["scores"]["h88_adhr_incumbent"],
                                "paired_delta_vs_adhr_overall": delta_adhr,
                                "paired_delta_vs_adhr_far_gt10px": pooled_far10["paired_differences"]["h88_adhr_incumbent"],
                                "paired_delta_vs_adhr_blind_gt25px": pooled_blind25["paired_differences"]["h88_adhr_incumbent"],
                                "folds_won_vs_adhr": folds_won,
                                "hgvc_current_best_point_comparison": {
                                    "hgvc_dti": prereg["promotion_bar"]["current_holdout_best"]["dti"],
                                    "candidate_beats_point_estimate": beats_hgvc_point,
                                    "note": "HGVC was not recomputed in these folds; this is a point-estimate comparison against its stored same-evaluator result, not a paired test."}},
                "leakage_canary": canary,
                "correlation_overlap_vs_registry": {"evidence_class": "REGISTRY-MEASUREMENT", **uq_slim},
                "raster_sha256": tif_sha, "zip_sha256": zip_sha,
                "download": f"docs/downloads/{dl_tif.name}", "zip_download": f"docs/downloads/{dl_zip.name}",
                "repo_copy": f"submissions/{dl_tif.name}",
                "validator_output": {"portal_ok": bool(portal_tif["ok"] and portal_zip["ok"]),
                                     "layout_parity_with_sample": bool(portal_tif["layout_parity_with_sample"]),
                                     "no_nan_inside_footprint": bool(portal_tif["checks"]["footprint_cells_finite"]),
                                     "no_nan_anywhere": bool(portal_tif["checks"]["all_finite"]),
                                     "values_in_0_1": bool(portal_tif["checks"]["portal_range_check_nan_strict"]),
                                     "crs_match": bool(portal_tif["checks"]["crs_epsg_32611"]),
                                     "shape_match": bool(portal_tif["checks"]["shape_matches_sample"]),
                                     "transform_match": bool(portal_tif["checks"]["transform_matches_sample"]),
                                     "nodata_undeclared": bool(portal_tif["checks"]["nodata_undeclared"]),
                                     "outside_footprint_zero": bool(portal_tif["checks"]["outside_footprint_zero"]),
                                     "zero_on_mapped_catalogue": bool(g57_val["checks"]["zero_dots_on_mapped_catalogue"]),
                                     "second_decoder": portal_tif["second_decoder"],
                                     "positive_dots": int(prod_meta["n_dots"]),
                                     "fingerprint": fp_prof, "fingerprint_screen_pass": fp_pass,
                                     "raster_sha256": tif_sha, "zip_sha256": zip_sha},
                "submission_name": sub_name, "submission_name_length": len(sub_name),
                "submission_note": sub_note, "submission_note_length": len(sub_note),
                "gate_v4": gv, "ok_to_download": True, "ok_to_submit": ok_submit, "verdict": verdict,
                "blocking_reasons": gv["blocking_reasons"], "informational": gv["informational"],
                "organizer_confirmed_score": None, "weekly_slots_spent": 0, "sepa_meta": sepa_meta}
    write_json(ROOT / "registry/sepa88_run_card.json", run_card)
    write_json(ROOT / "docs/data/sepa88_run_card.json", run_card)
    write_json(ROOT / "evidence/sepa88_run_card.json", run_card)
    print(json.dumps({"file": str(dl_tif), "sha256": tif_sha, "holdout_dti": ov["dti"], "ci95": ov["ci95"],
                      "beats_hgvc_point": beats_hgvc_point, "unique_v4": uq["unique_v4"],
                      "unique_literal": uq["unique_literal"], "ok_to_submit": ok_submit,
                      "verdict": verdict, "elapsed_s": round(time.monotonic() - t0, 1)}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
