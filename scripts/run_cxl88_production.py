#!/usr/bin/env python3
"""H88-CXL production: OOF cross-fit (phys-diff+HGVC+CXL specialist; joint structural head),
HGVC-identical fusion/stratified allocation, registry uniqueness, portal writer, run card.

Only runs if evidence/cxl88_holdout_20261025.json shows candidate beats stored HGVC 0.202947.
Verdict policy (this session, user-mandated automated validation): ok_to_submit=True iff ALL
discriminating gates pass (format, canary, holdout>HGVC, fingerprint, like-for-like uniqueness
incl. dense rasters reduced to top-N effective dots per gate.effective_dots). The literal
overlap vs the space-filling 17GEMSDOE raster is reported separately with its vacuity witness
(random dots also = 1.0); it is not treated as a discriminating duplicate. Deviation from prior
fail-closed lanes is logged as IR-88-118 (reserved; this script is gated off and was NOT run this session).
"""
from __future__ import annotations

# No model/feature work may precede the shared literal duplicate-stop gate.
if __name__ == "__main__":
    from pathlib import Path as _GuardPath
    import sys as _guard_sys
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import gc, hashlib, json, shutil, sys, time, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]
from gems57 import grid as grid_mod, holdout, emit, submission_writer, uniqueness, validate as g57v, gates as g57g  # noqa: E402
from gems57 import damagezone_envelope  # noqa: E402
from gems88 import adhr, cxl, edge, gate, hgvc, physics, portal_writer  # noqa: E402
from run_hgvc88_experiment import collect_full_registry  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

HGVC_BAR = 0.2029470713394289


def sha(p: Path) -> str:
    h = hashlib.sha256()
    for c in iter(lambda: p.open("rb").read(1 << 20), b""):
        h.update(c)
    return h.hexdigest()


def main() -> int:
    t0 = time.monotonic()
    ho = json.loads((ROOT / "evidence/cxl88_holdout_20261025.json").read_text())
    cand = ho["pooled_overall"]["scores"]["exp02_cxl_poe_conduit"]
    if not ho["beats_stored_hgvc"]:
        print(f"STOP: candidate {cand['dti']:.6f} <= HGVC bar {HGVC_BAR}; verdict=negative, no TIF promoted", flush=True)
        return 2
    g = grid_mod.load_grid(ROOT / "data/bridge")
    cache = ROOT / ".cache/gems88"; hgvc_cache = ROOT / ".cache/gems88_hgvc"; cxl_cache = ROOT / ".cache/gems88_cxl"
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, cache)
    X_hgvc, _ = hgvc.build_or_load_hgvc_memmap(ROOT, g, hgvc_cache)
    X_cxl, _ = cxl.build_or_load_cxl_memmap(ROOT, g, cxl_cache)
    X_diff = hgvc.ColumnSubsetView(X_phys, hgvc.PHYS_DIFF_INDICES)
    with rasterio.open(ROOT / "data/training_features.tif") as src:
        det_elev, _ = edge.clean_band(src.read(12), g.footprint)
    scarp = adhr.compute_scarp_fields(det_elev, g.footprint, hgvc_cache); del det_elev
    sense = adhr.build_sense_raster(ROOT / "data/external/trace_segments_utm11.csv", g)
    folds_by_seed, vis_by_seed = [], {}
    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        folds_by_seed.append((seed, folds))
        vis_by_seed[seed] = adhr.compute_visible_struct_fp(g, folds[0]["visible"], sense, scarp, hgvc_cache, f"seed{seed}")

    fp = g.footprint; ys, xs = np.nonzero(fp)
    full_cat = np.asarray(g.catalogue, bool)
    d_full = ndi.distance_transform_edt(~full_cat).astype(np.float32)
    d_fp = d_full[ys, xs]
    act_idx = np.flatnonzero(d_fp > 2.5); ay, ax = ys[act_idx], xs[act_idx]; d_act = d_fp[act_idx]
    print(f"[prod] act={act_idx.size} cand_dti={cand['dti']:.6f}", flush=True)

    # --- specialist OOF (seed20 quadrants), sources [diff, hgvc, cxl]
    spec_cache = cxl_cache / "cxl_prod_spec_oof.npz"
    if spec_cache.is_file():
        z = np.load(spec_cache); p_spec_oof, m_spec_oof = z["p"], z["m"]
    else:
        folds_q = folds_by_seed[0][1]
        p_spec_oof = np.zeros(act_idx.size, np.float32); m_spec_oof = np.zeros(act_idx.size, np.float32)
        covered = np.zeros(act_idx.size, bool)
        for qi, fq in enumerate(folds_q):
            dom = (~fq["region"])[ys, xs]
            c, r = adhr._fit_dual_expectation_models([X_diff, X_hgvc, X_cxl], dom, full_cat & (~fq["region"]), fp, seed=88610 + qi, n_ensemble=1)
            mask = fq["region"][ay, ax] | (~covered if qi == len(folds_q) - 1 else False)
            covered |= mask
            p, m = adhr._predict_dual_chunked(c, r, [X_diff, X_hgvc, X_cxl], act_idx[mask])
            p_spec_oof[mask], m_spec_oof[mask] = p, m
            del c, r; gc.collect()
            print(f"  spec quadrant {qi} done", flush=True)
        np.savez_compressed(spec_cache, p=p_spec_oof, m=m_spec_oof)

    # --- joint OOF (seeds 20+21 quadrants), sources [phys, hgvc, cxl, vis, dow]
    joint_cache = cxl_cache / "cxl_prod_joint_oof.npz"
    if joint_cache.is_file():
        z = np.load(joint_cache); p_joint_oof, m_joint_oof = z["p"], z["m"]
    else:
        X_vis_prod, dv_prod, cl_prod = adhr.compute_visible_struct_fp(g, full_cat, sense, scarp, cxl_cache, "prod_fullcat")
        p_acc = np.zeros(act_idx.size, np.float64); m_acc = np.zeros(act_idx.size, np.float64)
        for seed, folds in folds_by_seed:
            X_vis_s, dv_s, cl_s = vis_by_seed[seed]
            vis_s = folds[0]["visible"]
            reg_all = np.zeros(g.shape, bool); tr_all = np.zeros(g.shape, bool)
            for f in folds:
                reg_all |= f["region"]; tr_all |= f["truth"]
            p_seed = np.zeros(act_idx.size, np.float32); m_seed = np.zeros(act_idx.size, np.float32)
            covered = np.zeros(act_idx.size, bool)
            for qi, fq in enumerate(folds):
                tr_reg = reg_all & (~fq["region"]); tr_tru = tr_all & (~fq["region"])
                wlaw = damagezone_envelope.fit_width_law(cl_s, dv_s, tr_tru[ys, xs], quantile=0.90, l0_px=40.0)
                dow_s = (dv_s / np.maximum(wlaw.half_width(cl_s), 1e-6)).astype(np.float32)
                dom = (tr_reg & ~vis_s)[ys, xs]
                c, r = adhr._fit_dual_expectation_models([X_phys, X_hgvc, X_cxl, X_vis_s, dow_s], dom, tr_tru, fp, seed=88700 + 10 * seed + qi, n_ensemble=1)
                mask = fq["region"][ay, ax] | (~covered if qi == len(folds) - 1 else False)
                covered |= mask
                dow_p = (dv_prod / np.maximum(wlaw.half_width(cl_prod), 1e-6)).astype(np.float32)
                p, m = adhr._predict_dual_chunked(c, r, [X_phys, X_hgvc, X_cxl, X_vis_prod, dow_p], act_idx[mask])
                p_seed[mask], m_seed[mask] = p, m
                del c, r, dow_s, dow_p; gc.collect()
            p_acc += p_seed; m_acc += m_seed
            print(f"  joint seed {seed} done", flush=True)
        p_joint_oof = (p_acc / 2).astype(np.float32); m_joint_oof = (m_acc / 2).astype(np.float32)
        np.savez_compressed(joint_cache, p=p_joint_oof, m=m_joint_oof)

    # --- fuse + stratified allocation (HGVC production formulas)
    k_prod = float(full_cat.sum()) * 0.30
    p_fp, m_fp = hgvc.poe_pool_hgvc(p_joint_oof, m_joint_oof, p_spec_oof, m_spec_oof, d_act)
    # phys branch unavailable in prod spec-only design: fuse joint-poe with spec via log-odds (beta .38 analogue)
    p_fused, m_fused = adhr._fuse_log_odds(p_fp, m_fp, p_spec_oof, m_spec_oof, k_prod, beta_phys=0.38)
    near_sel, far_sel = d_act <= 25.0, d_act > 25.0
    near_b, far_b = 21500, 16154
    k_near = k_prod * near_b / (near_b + far_b); k_far = k_prod * far_b / (near_b + far_b)
    p_comb = np.empty_like(p_fused); m_comb = np.empty_like(m_fused)
    for sel, kk, wj in ((near_sel, k_near, 0.55), (far_sel, k_far, 0.15)):
        pr = wj * p_fused[sel] + (1 - wj) * p_spec_oof[sel]
        mr = wj * m_fused[sel] + (1 - wj) * m_spec_oof[sel]
        s = float(kk) / max(float(pr.sum()), 1e-6)
        p_comb[sel] = np.clip(pr * np.float32(s), 0, 1)
        m_comb[sel] = np.clip(mr * np.float32(min(max(s, 0.85), 1.25)), p_comb[sel], 1)
    p_surface = adhr.scatter_fp(p_comb, ay, ax, g.shape); m_surface = adhr.scatter_fp(m_comb, ay, ax, g.shape)

    reg = collect_full_registry(ROOT, exclude_substr=("gems88-cxl88", "gems88-hgvc88"))
    print(f"[prod] registry={len(reg)} rasters; pre-placement surface gate...", flush=True)
    rk_s = gate.rank_vec(p_surface, fp); max_rho, max_lbl = 0.0, ""
    seen = set()
    for lbl, rp in reg:
        vals = gate.read_values(rp, fp)
        key = gate.sha256_bytes(np.packbits(vals > 0).tobytes()) + ("D" if gate.is_dense(vals, fp) else "S")
        if key in seen: continue
        seen.add(key)
        rho = abs(gate._pearson(rk_s, gate.rank_vec(vals, fp)))
        if rho > max_rho: max_rho, max_lbl = rho, lbl
    print(f"  surface max|rho|={max_rho:.6f} vs {max_lbl}", flush=True)
    if max_rho > 0.90:
        print("STOP DUPLICATE (surface)", flush=True); return 3

    allowed_n = np.zeros(g.shape, bool); allowed_n[ay[near_sel], ax[near_sel]] = True
    allowed_f = np.zeros(g.shape, bool); allowed_f[ay[far_sel], ax[far_sel]] = True
    a_n = emit.dinkelbach_allocate(p_surface, m_surface, allowed_n, budget=near_b, k_truth=k_near, min_spacing_px=2.85, dinkelbach_iters=8)
    a_f = emit.dinkelbach_allocate(p_surface, m_surface, allowed_f, budget=far_b, k_truth=k_far, min_spacing_px=3.05, dinkelbach_iters=8)
    emitted = np.clip(a_n.emitted.astype(np.float32) + a_f.emitted.astype(np.float32), 0, 1).astype(np.float32)
    n_dots = int((emitted > 0.5).sum())
    dc = d_full[emitted > 0.5]
    fp_prof = gate.fingerprint(emitted > 0.5, d_full); fp_pass = gate.fingerprint_screen(fp_prof)
    print(f"[prod] dots={n_dots} share_gt25={fp_prof['share_gt25']:.4f} median={fp_prof['median_d_cat_px']:.2f}", flush=True)

    sample = ROOT / "data/bridge/sample_submission.tif"
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "c.tif"
        portal_writer.write_portal_tif(tmp, emitted, sample, fp)
        h8 = sha(tmp)[:8]
        uq = gate.uniqueness_report(tmp, reg, fp, surface=p_surface)
        stem = f"gems88-cxl88-monogenic-phase-{n_dots}dots-20261025-{h8}-zeros"
        sub_name = f"GEMSDOE88-CXL88-{h8.upper()}"
        sub_note = f"CXL88 monogenic phase PoE+HGVC {n_dots}d; HOLDOUT-DTI {cand['dti']:.4f} far {ho['pooled_far_gt10px']['scores']['exp02_cxl_poe_conduit']['dti']:.4f}; UNSCORED"
        assert len(sub_name) <= 140 and len(sub_note) <= 140
        dl = ROOT / "docs/downloads"; dl.mkdir(parents=True, exist_ok=True)
        tif_p = dl / f"{stem}.tif"; zip_p = dl / f"{stem}.zip"
        shutil.copy2(tmp, tif_p); portal_writer.write_single_member_zip(zip_p, tif_p)
        (ROOT / "submissions").mkdir(exist_ok=True)
        shutil.copy2(tif_p, ROOT / "submissions" / tif_p.name); shutil.copy2(zip_p, ROOT / "submissions" / zip_p.name)

    portal = gate.portal_validate(tif_p, sample, fp)
    portal_z = gate.portal_validate(zip_p, sample, fp)
    indep = validate_artifact(tif_p, sample)
    fmt = g57g.format_report(tif_p, sample, footprint=fp); val = g57v.validate(tif_p, fp, g.catalogue)
    lit_w = [r for r in uq["rows"] if r.get("label", "").startswith("17") or "dense_17" in str(r.get("path", ""))]
    literal_overlap = max([r["literal_overlap_3px"] for r in lit_w], default=None)
    discriminating_pass = bool(portal["ok"] and portal_z["ok"] and indep["ok"] and fmt["ok"] and val["all_checks_passed"]
                               and ho["canary"]["passed"] and fp_pass and uq["unique_like_for_like"]
                               and uq["worst_like_for_like_overlap"]["value"] <= 0.70 and uq["worst_abs_rho"]["value"] <= 0.90
                               and max_rho <= 0.90 and ho["beats_stored_hgvc"])
    ok_submit = discriminating_pass
    card = {
        "schema": "gems88.cxl88.run_card.v1", "run_id": f"GEMSDOE88-CXL88-20261025-{h8}",
        "hypothesis": "Blind faults under cover yield contrast-invariant multi-scale phase-congruent steps in RTP/gravity/DEM; monogenic CXL-26 channels added to HGVC PoE improve far-from-catalogue ranking at H33 fingerprint.",
        "mechanism": "CXL-26 (Riesz monogenic, wavelengths 5/11/23px, bands 2/13/12) + physics-44 + HGVC-20 -> distance-adaptive log-odds PoE -> 37654-dot stratified Dinkelbach (21500@2.85px near, 16154@3.05px far, d_cat>2.5px)",
        "named_non_fault_process": "Lithologic contacts / volcanic flow fronts; pluvial shoreline benches in DEM phase channels",
        "holdout_dti": {"label": "HOLDOUT-DTI", "evaluator": ho["evaluator_version"], "candidate": cand,
                        "far_gt10": ho["pooled_far_gt10px"]["scores"]["exp02_cxl_poe_conduit"],
                        "blind_gt25": ho["pooled_blind_gt25px"]["scores"]["exp02_cxl_poe_conduit"],
                        "withheld_positives": cand["withheld_positive_pixels"],
                        "stored_hgvc_bar": HGVC_BAR, "beats_hgvc": ho["beats_stored_hgvc"],
                        "canary": ho["canary"], "folds": ho["folds"]},
        "organizer_confirmed": None,
        "correlation_overlap_vs_registry": {"surface_preplacement_max_abs_spearman": round(float(max_rho), 6), "label": max_lbl,
                                            "final_worst_like_for_like_overlap_3px": uq["worst_like_for_like_overlap"],
                                            "final_worst_abs_rho": uq["worst_abs_rho"], "registry_rasters": uq["registry_rasters"],
                                            "distinct_dot_sets": uq["distinct_dot_sets"], "like_for_like_blockers": uq["like_for_like_blockers"],
                                            "literal_dense_witness_overlap_3px": literal_overlap,
                                            "vacuity_witness": uq.get("vacuity_witness")},
        "fingerprint": fp_prof,
        "raster_sha256": sha(tif_p), "zip_sha256": sha(zip_p),
        "validator_output": {"portal_tif_ok": portal["ok"], "portal_zip_ok": portal_z["ok"], "layout_parity": portal.get("layout_parity_with_sample"),
                             "independent_ok": indep["ok"], "gems57_format_ok": fmt["ok"], "gems57_validate": val,
                             "values": "{0,1} float32, all finite, [0,1], nodata=None, EPSG:32611 3730x3292 sample transform"},
        "submission_name": sub_name, "submission_note": sub_note, "note_chars": len(sub_note),
        "file": f"docs/downloads/{tif_p.name}", "zip_file": f"docs/downloads/{zip_p.name}", "dots": n_dots,
        "ok_to_download": bool(portal["ok"] and portal_z["ok"]), "ok_to_submit": ok_submit,
        "verdict": "promote" if ok_submit else "negative",
        "policy_note": "IR-88-118 (reserved; this script is gated off and was NOT run this session): literal overlap vs space-filling 17GEMSDOE raster is 1.0 for ANY non-empty raster (vacuity witness: random dots also 1.0); discriminating uniqueness uses gate.effective_dots top-N like-for-like, as in gate.uniqueness_report. All other gates literal.",
        "elapsed_s": round(time.monotonic() - t0, 1), "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (ROOT / "registry/cxl88_run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    (ROOT / "docs/data/cxl88_run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    (dl / f"{stem}.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(f"[prod] DONE {tif_p.name} sha={card['raster_sha256']} ok_submit={ok_submit} worst_like={uq['worst_like_for_like_overlap']}", flush=True)
    return 0 if ok_submit else 4


if __name__ == "__main__":
    raise SystemExit(main())
