#!/usr/bin/env python3
"""Build the H88-SDTL production raster, check uniqueness (surface + dots), write
the TIFF/ZIP with the shared writer and emit the run card.

Decision logic (automatic, no human inspection):
  promote  <=> holdout success rule met (evidence/sdtl88_holdout.json) AND
               canary passed AND uniqueness v5 passed on surface and dots AND
               the on-disk validator passed.
  Otherwise the file is written with a DO-NOT-SUBMIT marker and verdict negative.
"""
from __future__ import annotations

if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()

import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

from gems57 import emit, grid as grid_mod, holdout, submission_writer, uniqueness  # noqa: E402
from gems88 import adhr, physics, sdtl  # noqa: E402
from validate_artifact import validate_artifact  # noqa: E402

PROD_SEED = 22
SPACING_PX = 2.05
LANE = "H88-SDTL"


def registry_paths() -> list[tuple[str, Path]]:
    out = []
    for p in sorted((ROOT / "data/registry").rglob("*.tif")):
        out.append((f"registry/{p.relative_to(ROOT / 'data/registry')}", p))
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        if "sdtl88" in p.name:
            continue
        out.append((f"gems88/{p.name}", p))
    return out


def main() -> int:
    t0 = time.monotonic()
    prereg = json.loads((ROOT / "registry/preregistration_sdtl88.json").read_text())
    hold_path = ROOT / "evidence/sdtl88_holdout.json"
    can_path = ROOT / "evidence/sdtl88_canaries.json"
    if not hold_path.is_file() or not can_path.is_file():
        raise FileNotFoundError("run scripts/run_sdtl88_experiment.py first (holdout + canary evidence missing)")
    hold = json.loads(hold_path.read_text())
    can = json.loads(can_path.read_text())
    cand = hold["pooled_overall"]["scores"]["candidate_sdtl"]
    ctrl = hold["pooled_overall"]["scores"]["control_phys44"]
    delta = hold["pooled_overall"]["paired_differences"]["control_phys44"]
    won = int(hold["folds_won_vs_control"])
    holdout_success = bool(delta["delta"] > 0 and delta["ci95"][0] > 0 and won >= 5)

    g = grid_mod.load_grid(ROOT / "data/bridge")
    fp, cat = g.footprint, g.catalogue
    cache = ROOT / ".cache/gems88_sdtl"
    print("[1/6] features", flush=True)
    X_phys, _, _ = physics.build_or_load_physics_memmap(ROOT, g, ROOT / ".cache/gems88")
    fabric = sdtl.load_zero_catalogue_fabric(ROOT, fp)
    folds, _ = holdout.buffered_component_draw(g, seed=PROD_SEED, buffer_px=3, boundary_px=12)
    visible = folds[0]["visible"]
    hidden_all = folds[0]["hidden_all"]
    X_sdtl = sdtl.build_sdtl_fp(fabric, visible, fp, cache, f"seed{PROD_SEED}")
    del fabric
    gc.collect()

    print("[2/6] fit production dual-expectation model (positives = withheld components of all quadrants, visible-only features)", flush=True)
    ys, xs = np.nonzero(fp)
    dom = (fp & ~visible)[ys, xs]
    clfs, regs = adhr._fit_dual_expectation_models([X_phys, X_sdtl], dom, hidden_all, fp, seed=PROD_SEED * 100 + 9, n_ensemble=2)
    allowed = fp & ~cat
    act_idx = np.flatnonzero(allowed[ys, xs])
    p_vec, m_vec = adhr._predict_dual_chunked(clfs, regs, [X_phys, X_sdtl], act_idx)
    del clfs, regs
    gc.collect()
    hid_ratio = float(hidden_all.sum()) / max(float(visible.sum()), 1.0)
    k_est = float(cat.sum()) * hid_ratio
    p_cal = np.clip(p_vec * np.float32(k_est / max(float(p_vec.sum()), 1e-6)), 0.0, 1.0).astype(np.float32)
    m_cal = np.clip(m_vec, p_cal, 1.0).astype(np.float32)
    surface = adhr.scatter_fp(p_cal, ys[act_idx], xs[act_idx], g.shape)
    m_surf = adhr.scatter_fp(m_cal, ys[act_idx], xs[act_idx], g.shape)

    print("[3/6] pre-placement surface uniqueness (rank correlation vs every local registry raster)", flush=True)
    regs_list = registry_paths()
    expected_grid = (g.shape, g.crs, g.transform)
    surf_rows = []
    import rasterio
    for label, path in regs_list:
        with rasterio.open(path) as src:
            if (src.shape, src.crs, src.transform) != expected_grid:
                surf_rows.append(dict(file=label, error="grid mismatch"))
                continue
            band = src.read(1)
            theirs = np.where(np.isfinite(band), band, 0.0).astype(np.float32)
            del band
        rho = uniqueness.surface_rho(surface, theirs, fp)["spearman_full_footprint"]
        surf_rows.append(dict(file=label, spearman_full_footprint=(None if not np.isfinite(rho) else float(rho))))
        del theirs
    worst_surf = max((r for r in surf_rows if r.get("spearman_full_footprint") is not None),
                     key=lambda r: abs(r["spearman_full_footprint"]), default=None)
    surface_ok = bool(worst_surf and abs(worst_surf["spearman_full_footprint"]) <= uniqueness.RHO_LIMIT
                      and not any("error" in r for r in surf_rows))
    print(f"      worst |rho| = {abs(worst_surf['spearman_full_footprint']):.4f} ({worst_surf['file']}) ok={surface_ok}", flush=True)

    print("[4/6] Dinkelbach allocation (min spacing 2.05 px)", flush=True)
    alloc = emit.dinkelbach_allocate(surface, m_surf, allowed, budget=None, k_truth=k_est,
                                     min_spacing_px=SPACING_PX, dinkelbach_iters=8)
    pred = np.where(fp, alloc.emitted.astype(np.float32), 0.0).astype(np.float32)
    pred[cat] = 0.0
    n_dots = int((pred > 0).sum())
    print(f"      dots = {n_dots}, k_est = {k_est:.0f}, surrogate = {alloc.surrogate_dti:.4f}", flush=True)

    print("[5/6] final-dot uniqueness v5 (equal-support overlap + rank correlation vs every local registry raster)", flush=True)
    dots_decision = uniqueness.binding_duplicate_decision_v5(pred, regs_list, allowed, fp, expected_grid=expected_grid)
    dots_ok = not dots_decision["stop_required"]
    print(f"      worst equal-support overlap = {dots_decision['worst_equal_support_overlap']:.4f} ({dots_decision['worst_overlap_file']}); "
          f"worst |rho| = {dots_decision['worst_abs_spearman']:.4f}; ok={dots_ok}", flush=True)

    promote = bool(holdout_success and can["passed"] and surface_ok and dots_ok)
    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha8 = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    marker = "" if promote else "-DO-NOT-SUBMIT"
    stem = f"gems88-sdtl88-slipdilation-{n_dots}dots-{utc}-{sha8}-zeros{marker}"
    name = stem[:140]
    note = (f"H88-SDTL stress-field slip/dilation-tendency lineaments; HOLDOUT-DTI {cand['dti']:.4f} "
            f"vs ctrl {ctrl['dti']:.4f}; {n_dots} dots; UNSCORED")[:140]
    out_dir = ROOT / "docs/downloads"
    print("[6/6] shared writer", flush=True)
    receipt = submission_writer.write_submission(out_dir / f"{stem}.tif", pred, ROOT / "data/bridge/sample_submission.tif",
                                                 fp, note=note, name=name, catalogue=cat,
                                                 metadata=dict(lane=LANE, preregistration_id=prereg["preregistration_id"]))
    validator = validate_artifact(out_dir / f"{stem}.tif", ROOT / "data/bridge/sample_submission.tif")
    verdict = "promote" if (promote and validator["ok"]) else "negative"
    card = dict(
        schema="gems88.run_card.v2", lane=LANE, generated_utc=datetime.now(timezone.utc).isoformat(),
        preregistration_id=prereg["preregistration_id"],
        hypothesis=prereg["hypothesis"], mechanism=prereg["mechanism"],
        named_non_fault_mimics=prereg["named_non_fault_mimics"],
        holdout_dti=dict(evidence_class="HOLDOUT-DTI", evaluator_version=cand["evaluator_version"],
                         candidate=cand, control_phys44=ctrl,
                         ablation_sdtl=hold["pooled_overall"]["scores"]["ablation_sdtl"],
                         paired_delta_vs_control=delta, folds_won_vs_control=f"{won}/{hold['n_folds']}",
                         far_gt10px=hold["pooled_far_gt10px"]["scores"],
                         success_rule=prereg["success_rule"], success=holdout_success),
        leakage_canary=dict(max_symmetric_auc=can["max_symmetric_auc"], limit=can["limit"], passed=can["passed"],
                            features_tested=can["features_tested"]),
        correlation_overlap_vs_registry=dict(
            rasters_checked=len(regs_list),
            surface_worst_abs_spearman=abs(worst_surf["spearman_full_footprint"]), surface_worst_file=worst_surf["file"],
            dots_worst_equal_support_overlap=dots_decision["worst_equal_support_overlap"],
            dots_worst_overlap_file=dots_decision["worst_overlap_file"],
            dots_worst_abs_spearman=dots_decision["worst_abs_spearman"],
            rho_limit=uniqueness.RHO_LIMIT, overlap_limit=uniqueness.OVERLAP_LIMIT,
            binding_rule=dots_decision["binding_rule"], surface_ok=surface_ok, dots_ok=dots_ok,
            scope="Local registry: pinned sibling rasters in data/registry plus every GEMSDOE88 published TIFF; not a complete organizer registry."),
        raster=dict(file=f"docs/downloads/{stem}.tif", sha256=receipt["sha256"], zip_file=f"docs/downloads/{receipt['zip_file']}",
                    zip_sha256=receipt["zip_sha256"], n_dots=n_dots, k_truth_est=k_est, production_seed=PROD_SEED),
        validator=dict(no_nan_inside_footprint=validator["no_nan_inside"], values_in_0_1=validator["range_0_1"],
                       crs_match=validator["crs_match"], shape_match=validator["shape_match"],
                       transform_match=validator["transform_match"], no_mass_outside=validator["no_mass_outside"],
                       single_band=validator["single_band"], ok=validator["ok"]),
        submission_name=name, submission_note=note, note_chars=len(note),
        verdict=verdict, ok_to_submit=bool(verdict == "promote"),
        organizer_confirmed=None,
        experiments_run=3, experiment_budget_max=3, weekly_slots_used=0,
        elapsed_seconds=time.monotonic() - t0,
        surface_rows=surf_rows, dots_rows=dots_decision["rows"],
    )
    (ROOT / "registry").mkdir(exist_ok=True)
    (ROOT / "registry/sdtl88_run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    (ROOT / "docs/data").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs/data/sdtl88_run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
    print(f"VERDICT {verdict}  ok_to_submit={card['ok_to_submit']}  file={card['raster']['file']}  sha256={receipt['sha256']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
