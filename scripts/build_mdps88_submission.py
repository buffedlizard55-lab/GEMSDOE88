#!/usr/bin/env python3
"""MDPS-88 E3: final full-catalogue fit, uniqueness audit, gated packaging.

Reads E1/E2 evidence, applies the frozen gates from
registry/preregistration_mdps88.json, builds ONE GeoTIFF (plus one-TIFF ZIP via
the vendored submission writer), validates the on-disk bytes independently, and
writes the JSON run card. If any scientific/uniqueness gate fails the file name
carries DO-NOT-SUBMIT and the card says ok_to_submit=false. Spends 0 slots.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import emit, grid as grid_mod, submission_writer, uniqueness, validate  # noqa: E402
from gems88 import halo, physics  # noqa: E402

SPACING = 2.83
BUDGET_TOTAL = 37_654
K_LIVE_EST = 14_000.0   # INFERENCE from lineage arithmetic (docs/research/hypotheses-20261024-mdps88.md)
ADHR_FAR_STORED = 0.11478
LANE_CAP = 0.66


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def registry_paths() -> list[Path]:
    paths: list[Path] = []
    reg = ROOT / "data/registry"
    paths += sorted(reg.glob("*.tif")) + sorted((reg / "family_60gemsdoe").glob("*.tif"))
    paths += sorted((ROOT / "docs/downloads").glob("*.tif"))
    paths += sorted((ROOT / "releases").glob("*.tif"))
    seen, out = set(), []
    for p in paths:
        rp = p.resolve()
        if rp not in seen and p.is_file():
            seen.add(rp)
            out.append(p)
    return out


def read1(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        return s.read(1)


def uniqueness_rows(candidate_dots: np.ndarray, surface: np.ndarray, allowed: np.ndarray,
                    sample_valid: np.ndarray) -> tuple[list[dict], dict]:
    rows = []
    for p in registry_paths():
        try:
            a = read1(p)
        except Exception as exc:  # recorded, never silently skipped
            rows.append(dict(file=str(p.relative_to(ROOT)), error=f"{type(exc).__name__}: {exc}"))
            continue
        if a.shape != candidate_dots.shape:
            rows.append(dict(file=str(p.relative_to(ROOT)), error=f"shape {a.shape} != {candidate_dots.shape}"))
            continue
        support = np.isfinite(a) & (a > 0)
        h_cov = uniqueness.halo_coverage(support, allowed)
        fwd = uniqueness.dot_overlap(candidate_dots.astype(np.float32), np.where(support, 1.0, 0.0).astype(np.float32))
        rho_info = uniqueness.surface_rho(surface, np.where(np.isfinite(a), a, 0.0).astype(np.float32), sample_valid)
        rows.append(dict(
            file=str(p.relative_to(ROOT)), their_dots=int(support.sum()),
            halo_coverage=h_cov, forward_overlap=fwd,
            spearman_full_footprint=(None if rho_info["spearman_full_footprint"] is None or
                                      (isinstance(rho_info["spearman_full_footprint"], float) and math.isnan(rho_info["spearman_full_footprint"]))
                                      else float(rho_info["spearman_full_footprint"])),
            spearman_on_dot_union=(None if isinstance(rho_info["spearman_on_dot_union"], float) and math.isnan(rho_info["spearman_on_dot_union"])
                                   else float(rho_info["spearman_on_dot_union"])),
            jaccard_dot_sets=float(rho_info["jaccard_dot_sets"])))
    decision = uniqueness.binding_duplicate_decision_v3(rows)
    return rows, decision


def main():
    t0 = time.monotonic()
    e1 = json.loads((ROOT / "evidence/mdps88_experiment1_20261024.json").read_text())
    e2_path = ROOT / "evidence/mdps88_experiment2_20261024.json"
    ev = json.loads(e2_path.read_text()) if e2_path.is_file() else e1
    ev_name = e2_path.name if e2_path.is_file() else "mdps88_experiment1_20261024.json"

    # ---- frozen scientific gates from the decisive (budget-matched) experiment
    def summ(kind, cand):
        return ev["pooled"][f"{kind}__candidate_{cand}"]
    cand_name = "mdps_mix"  # preregistered candidate arm; no post-hoc arm selection
    far = summ("far", cand_name)
    dci = far["paired_differences"]["base283"]
    gate_far_paired = bool(dci["ci95"][0] > 0)
    far_alt = summ("far", "mdps_far")
    allk = summ("all", cand_name)
    cand_far_dti = far["scores"][cand_name]["dti"]
    cand_all_dti = allk["scores"][cand_name]["dti"]
    base_all_dti = allk["scores"]["base283"]["dti"]
    gate_far_adhr = bool(cand_far_dti > ADHR_FAR_STORED)
    gate_all_base = bool(cand_all_dti >= base_all_dti)
    gate_canary = bool(ev["canary"]["passed"])

    # ---- final fit on the full catalogue (no hidden labels exist at final time)
    g = grid_mod.load_grid(ROOT / "data" / "bridge")
    fp, cat = g.footprint, g.catalogue
    X, band_tags, _ = physics.build_or_load_physics_memmap(ROOT, g, ROOT / ".cache/gems88")
    ys_fp, xs_fp = np.nonzero(fp)
    d_cat = ndi.distance_transform_edt(~cat)
    hid_ratio = K_LIVE_EST / float(cat.sum())

    print("[final] fit far head (isolated positives, far background) ...", flush=True)
    iso = halo.isolated_mask(cat, r=5)
    d_iso = ndi.distance_transform_edt(~iso)
    domain_far = fp & ((d_cat > 8) | (d_iso <= 3))
    clf_far = halo._fit_classifier(X, g, domain_far[ys_fp, xs_fp], iso, seed=880_001)
    p_far, m_far, al_far, k_far = halo.predict_calibrated(clf_far, X, g, cat, fp, hid_ratio, 8.0)
    print(f"[final] far head done k={k_far:.0f} at {time.monotonic()-t0:.0f}s", flush=True)
    del clf_far

    surface = p_far.copy()
    p_near_reg = None
    if cand_name == "mdps_mix":
        print("[final] fit near head (all positives) ...", flush=True)
        clf_base = halo._fit_classifier(X, g, fp[ys_fp, xs_fp], cat, seed=880_002)
        p_b, m_b, al_b, k_b = halo.predict_calibrated(clf_base, X, g, cat, fp, hid_ratio, 2.0)
        near_allowed = al_b & (d_cat <= 8)
        thr = float(np.quantile(p_b[near_allowed], 0.99)) if near_allowed.any() else float("inf")
        near_allowed2 = near_allowed & (p_b >= thr)
        p_near_reg = (p_b, m_b, near_allowed2, k_b)
        surface = np.maximum(surface, np.where(near_allowed2, p_b, 0)).astype(np.float32)
        print(f"[final] near head done k={k_b:.0f} thr={thr:.4f} at {time.monotonic()-t0:.0f}s", flush=True)
        del clf_base
    else:
        p_b = None

    # ---- PRE-PLACEMENT surface uniqueness (protocol: check surface before dots)
    rng = np.random.default_rng(88)
    sample_valid = np.zeros(fp.shape, bool)
    fi = np.flatnonzero(fp)
    sel = np.sort(rng.choice(fi.size, size=min(600_000, fi.size), replace=False))
    ys_s, xs_s = np.nonzero(fp)
    sample_valid[ys_s[sel], xs_s[sel]] = True
    allowed_final = fp & ~cat & (d_cat > 2)
    _rows0, decision0 = uniqueness_rows((surface >= np.quantile(surface[fp], 0.99)) & fp, surface,
                                        allowed_final, sample_valid)
    print(f"[uniq-surface] worst |rho|={decision0['worst_abs_spearman']} "
          f"worst excess={decision0['worst_excess_overlap']} dup={decision0['duplicate']}", flush=True)

    # ---- allocation (candidate config, live budget)
    def alloc(p, m, allowed, k, budget):
        return emit.dinkelbach_allocate(p, m, allowed, budget=budget, k_truth=float(k),
                                        min_spacing_px=SPACING, dinkelbach_iters=6)
    if cand_name == "mdps_mix":
        a_far = alloc(p_far, m_far, al_far, k_far, int(math.ceil(0.8 * BUDGET_TOTAL)))
        p_b, m_b, near_allowed2, k_b = p_near_reg
        a_near = alloc(np.where(near_allowed2, p_b, 0).astype(np.float32), m_b, near_allowed2, k_b,
                       int(0.2 * BUDGET_TOTAL))
        near_em = a_near.emitted & (ndi.distance_transform_edt(~a_far.emitted) >= SPACING)
        emitted = a_far.emitted | near_em
        alloc_meta = dict(n_far=int(a_far.emitted.sum()), n_near=int(near_em.sum()),
                          surrogate_dti_far=float(a_far.surrogate_dti))
    else:
        a_far = alloc(p_far, m_far, al_far, k_far, BUDGET_TOTAL)
        emitted = a_far.emitted
        alloc_meta = dict(n_far=int(a_far.emitted.sum()), n_near=0,
                          surrogate_dti_far=float(a_far.surrogate_dti))
    print(f"[alloc] n={int(emitted.sum())} {alloc_meta} at {time.monotonic()-t0:.0f}s", flush=True)

    # ---- lane-cap repair vs discriminating priors (deterministic, recorded)
    rows, decision = uniqueness_rows(emitted, surface, allowed_final, sample_valid)
    repair_log = []
    for _round in range(3):
        worst = None
        for r in rows:
            if "error" in r or r.get("halo_coverage", 1) >= 1.0 - 1e-12:
                continue
            ex = uniqueness.excess_overlap(r["forward_overlap"], r["halo_coverage"])
            r["excess_overlap_now"] = ex
            if ex is not None and ex > LANE_CAP and (worst is None or ex > worst[0]):
                worst = (ex, r)
        if worst is None:
            break
        _, wr = worst
        sup = np.isfinite(read1(ROOT / wr["file"])) & (read1(ROOT / wr["file"]) > 0)
        halo_mask = uniqueness._near(sup, 3.0)
        inside = emitted & halo_mask
        n_in, n_tot = int(inside.sum()), int(emitted.sum())
        # target: excess <= LANE_CAP  =>  overlap <= h + LANE_CAP*(1-h)
        h = wr["halo_coverage"]
        target_fwd = h + LANE_CAP * (1 - h)
        n_allowed = int(target_fwd * n_tot)
        n_remove = max(0, n_in - n_allowed)
        if n_remove == 0:
            break
        ys, xs = np.nonzero(inside)
        order = np.argsort(surface[ys, xs], kind="stable")  # drop lowest-surface first
        emitted[ys[order[:n_remove]], xs[order[:n_remove]]] = False
        # refill outside this halo, spacing-respecting, by surface rank
        d_em = ndi.distance_transform_edt(~emitted)
        pool = al_far & ~halo_mask & (d_em >= SPACING) & ~emitted
        ys2, xs2 = np.nonzero(pool)
        order2 = np.argsort(-surface[ys2, xs2], kind="stable")
        added = 0
        for idx in order2:
            if added >= n_remove:
                break
            y, x = int(ys2[idx]), int(xs2[idx])
            y0, y1, x0, x1 = max(0, y - 3), min(emitted.shape[0], y + 4), max(0, x - 3), min(emitted.shape[1], x + 4)
            if emitted[y0:y1, x0:x1].any():
                yy, xx = np.nonzero(emitted[y0:y1, x0:x1])
                if np.any(np.hypot(yy + y0 - y, xx + x0 - x) < SPACING):
                    continue
            emitted[y, x] = True
            added += 1
        repair_log.append(dict(prior=wr["file"], excess_before=float(wr["excess_overlap_now"]),
                               removed=int(n_remove), refilled=int(added)))
        rows, decision = uniqueness_rows(emitted, surface, allowed_final, sample_valid)
        print(f"[repair] {repair_log[-1]} n={int(emitted.sum())}", flush=True)
    print(f"[uniq-final] duplicate={decision['duplicate']} worst_excess={decision['worst_excess_overlap']} "
          f"vs {decision['worst_excess_overlap_file']} worst|rho|={decision['worst_abs_spearman']} "
          f"rasters={decision['rasters_checked']}", flush=True)

    # ---- gates -> naming
    sci_ok = bool(gate_far_paired and gate_far_adhr and gate_all_base and gate_canary)
    uniq_ok = bool(not decision["duplicate"])
    surface_dup = bool(decision0["worst_abs_spearman"] is not None and decision0["worst_abs_spearman"] > 0.90)
    ok_submit_candidate = bool(sci_ok and uniq_ok and not surface_dup)
    stem_cfg = "mix" if cand_name == "mdps_mix" else "far"
    base_name = f"gems88-mdps88-{stem_cfg}-{int(emitted.sum())}dots-20261024"
    provisional = base_name + "-zeros" + ("" if ok_submit_candidate else "-DO-NOT-SUBMIT")
    out_dir = ROOT / "docs/downloads"
    out_path = out_dir / f"{provisional}.tif"
    pred = np.zeros(fp.shape, np.float32)
    pred[emitted] = 1.0
    name140 = ("GEMSDOE88-MDPS88-MIX-20261024" if cand_name == "mdps_mix" else "GEMSDOE88-MDPS88-FAR-20261024")
    note = (f"MDPS-88 matched-domain physics {stem_cfg}, {int(emitted.sum())} dots; "
            f"HOLDOUT far {cand_far_dti:.4f} overall {cand_all_dti:.4f}; UNSCORED"
            + ("" if ok_submit_candidate else "; DO NOT SUBMIT"))[:140]
    receipt = submission_writer.write_submission(
        out_path, pred, ROOT / "data/bridge/sample_submission.tif", fp,
        note=note, name=name140, catalogue=cat,
        metadata=dict(lane="MDPS-88", candidate=cand_name, experiment=ev_name,
                      evidence_class="HOLDOUT-DTI", ok_to_submit=ok_submit_candidate))
    short = receipt["sha256"][:8]
    finals = {suffix: out_dir / f"{provisional}{suffix}" for suffix in (".tif", ".zip", ".json")}
    assert all(f.exists() for f in finals.values())
    assert finals[".tif"].name == receipt["file"]
    v = validate.validate(finals[".tif"], fp, cat)
    import zipfile
    with zipfile.ZipFile(finals[".zip"]) as z:
        members = z.namelist()
        zip_member_ok = len(members) == 1
        # member name inside zip is the provisional tif name; record it
        zip_member_name = members[0] if members else None
        zip_bytes_match = zip_member_ok and hashlib.sha256(z.read(members[0])).hexdigest() == v["sha256"]
    format_ok = bool(v["all_checks_passed"] and zip_member_ok and zip_bytes_match)
    ok_to_submit = bool(ok_submit_candidate and format_ok)

    ys_d, xs_d = np.nonzero(emitted)
    dd = d_cat[ys_d, xs_d]
    card = {
        "schema": "gems.run_card.v1",
        "run_id": f"GEMSDOE88-MDPS88-20261024-{short}",
        "generated_utc": "2026-10-24",
        "hypothesis": "Unmapped basin faults are missed by range-front-trained rankers (covariate shift); a physics ranker trained only on isolated mapped strands vs far-basin background, allocated in matched distance regimes (far d>8 px + capped physics-snapped near tranche 2-8 px), kernel-matched 2.83 px spacing and b2 collar, recovers far withheld faults better than all-positive training and adds low-relief support the H19-5 lineage lacks.",
        "mechanism": "44 label-blind physics columns (GeoDAWN magnetics/gravity/radiometrics, 1 m LiDAR scarps, 10 m topo/chi, strain, seismicity, GDR geothermal points) -> per-fold HGB PU rankers (isolated-component positives vs far background) -> Dinkelbach expected-DTI allocation; final: full-catalogue fit, 37,654-class live budget, lane-capped vs registry priors.",
        "named_non_fault_process": "Pleistocene pluvial (Lake Lahontan) shoreline benches and fluvial terrace risers: constant-elevation scarps with the same LiDAR dipole/curvature signature as young fault scarps but no brittle offset.",
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": ev["evaluator_version"],
            "experiment_file": f"evidence/{ev_name}",
            "candidate_arm": cand_name,
            "far": {"dti": cand_far_dti, "ci95": far["scores"][cand_name]["ci95"],
                    "withheld_positive_pixels": far["scores"][cand_name]["withheld_positive_pixels"],
                    "paired_vs_base283": dci},
            "overall": {"dti": cand_all_dti, "ci95": allk["scores"][cand_name]["ci95"],
                        "withheld_positive_pixels": allk["scores"][cand_name]["withheld_positive_pixels"]},
            "base283_control": {"far": far["scores"]["base283"], "overall": allk["scores"]["base283"]},
            "r0_fixed_shipped_h33": {"far": far["scores"]["r0_fixed"], "overall": allk["scores"]["r0_fixed"],
                                     "note": "fold-UNFAIR fixed raster; USER-REPORTED live claim 0.2778 (no organizer receipt in repo)"},
            "mdps_far_alternative_arm": {"far": far_alt["scores"]["mdps_far"],
                                         "paired_vs_base283": far_alt["paired_differences"]["base283"]},
            "stored_reference_unpaired": {"name": "ADHR far (same folds, stored)", "dti": ADHR_FAR_STORED},
        },
        "leakage_canary": {"max_symmetric_auc": ev["canary"]["max_symmetric_auc"], "threshold": 0.90,
                           "passed": gate_canary, "features_tested": ev["canary"]["features_tested"]},
        "correlation_overlap_vs_registry": {
            "method": "vendor uniqueness.binding_duplicate_decision_v3; surface Spearman on seeded 600k footprint sample (pre-placement and final surfaces identical file)",
            "rasters_checked": decision["rasters_checked"],
            "worst_abs_spearman": decision["worst_abs_spearman"],
            "worst_abs_spearman_file": decision["worst_abs_spearman_file"],
            "worst_excess_overlap_3px": decision["worst_excess_overlap"],
            "worst_excess_overlap_file": decision["worst_excess_overlap_file"],
            "worst_literal_forward_overlap_3px": decision["worst_literal_forward_overlap"],
            "worst_literal_file": decision["worst_literal_forward_overlap_file"],
            "space_filling_priors": decision["space_filling_files"],
            "duplicate": decision["duplicate"],
            "surface_preplacement_worst_abs_spearman": decision0["worst_abs_spearman"],
            "surface_preplacement_duplicate_by_rho": surface_dup,
            "lane_cap_repairs": repair_log,
            "scope_limit": "restored registry rasters (18 pinned + family) + tracked docs/downloads + releases tifs on disk this session; sibling rasters not restored are NOT covered",
            "rows_file": "evidence/mdps88_uniqueness_20261024.json",
        },
        "raster": {
            "file": str(finals[".tif"].relative_to(ROOT)), "zip": str(finals[".zip"].relative_to(ROOT)),
            "sha256": v["sha256"], "zip_sha256": sha256(finals[".zip"]), "bytes": v["bytes"],
            "dots": int(emitted.sum()), "allocation": alloc_meta,
            "dot_distance_to_catalogue_px": {"min": float(dd.min()), "median": float(np.median(dd)),
                                             "frac_le2": float((dd <= 2).mean()), "frac_gt25": float((dd > 25).mean())},
            "zip_member_name": zip_member_name,
        },
        "raster_sha256": v["sha256"],
        "validator": v,
        "format_ok": format_ok,
        "submission_name": name140,
        "submission_note": note,
        "submission_note_chars": len(note),
        "gates": {"canary_le_0.90": gate_canary, "far_paired_ci_gt_0_vs_base283": gate_far_paired,
                  "far_gt_stored_adhr_0.11478_unpaired": gate_far_adhr,
                  "overall_ge_base283": gate_all_base, "uniqueness_v3_pass": uniq_ok,
                  "surface_preplacement_pass": bool(not surface_dup),
                  "format_all_checks_passed": bool(v["all_checks_passed"]),
                  "zip_one_member_bytes_match": bool(zip_member_ok and zip_bytes_match)},
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "approved_for_weekly_slot": False,
        "verdict": "promote" if ok_to_submit else "negative",
        "verdict_reason": ("all frozen gates pass; human selector still required before any slot"
                           if ok_to_submit else "one or more frozen gates failed (see gates); do not spend a weekly slot"),
        "organizer_confirmed_score": None,
        "slots_used_by_this_session": 0,
        "seconds": round(time.monotonic() - t0, 1),
    }
    (ROOT / "evidence/mdps88_uniqueness_20261024.json").write_text(json.dumps(
        dict(evidence_class="REGISTRY-MEASUREMENT", rows=rows, decision=decision,
             surface_decision=decision0), indent=1, default=float))
    for dest in (ROOT / "registry/mdps88_run_card.json", ROOT / "docs/data/mdps88_run_card.json"):
        dest.write_text(json.dumps(card, indent=1, default=float))
    print(json.dumps({k: card[k] for k in ("verdict", "ok_to_submit", "raster_sha256", "gates")}, indent=1, default=float))
    print("CARD", finals[".tif"], name140, f"note[{len(note)}]={note}")


if __name__ == "__main__":
    main()
