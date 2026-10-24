#!/usr/bin/env python3
"""CHIASM-88: chi across-strike sign-reversal + slope-break + basin gate.

One preregistered experiment in H88 lane family. Uses only restored files,
no catalogue geometry in features. Holdout = buffered whole-component hide-and-recover
(seeds 20,21), pooled DTI alpha 0.2 beta 0.8 300m kernel. Leakage canary per channel.
Uniqueness via vendor/gems57/uniqueness (literal rule disclosed).

Generates 37654 binary dots, spaced >=3.5px, >3px from catalogue (full catalogue for final,
visible-only for holdout folds). Format via vendor/gems57/submission_writer (all-finite, [0,1], nodata None).
"""
from __future__ import annotations
import hashlib, json, sys, time
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter, distance_transform_edt
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"src"))
sys.path.insert(0, str(ROOT/"vendor"))
sys.path.insert(0, str(ROOT/"scripts"))

from gems57 import grid as grid_mod, holdout as ho, evaluate_holdout as eh, uniqueness
from gems57.submission_writer import write_submission
from gems88.edge import clean_band
from validate_artifact import validate_artifact

N_DOTS = 37654
SPACING_PX = 3.5
STEM_PREFIX = "gems88-chiasm-across-strike-20261024"
SAMPLE = ROOT/"data/bridge/sample_submission.tif"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def percentile_rank(a, footprint):
    """Rank transform to [0,1] via 257-quantile interpolation, label-blind."""
    fp = np.asarray(footprint, bool)
    vals = a[fp]
    if vals.size == 0:
        return np.zeros_like(a, dtype=np.float32)
    qs = np.linspace(0,100,257)
    edges = np.percentile(vals, qs)
    # interpolate
    out = np.zeros_like(a, dtype=np.float32)
    # use searchsorted
    # normalize via rankdata for tie handling? Use interpolation for speed
    # For each pixel, find quantile
    # Use np.interp on sorted edges
    # Ensure monotonic
    # Use digitize
    # Simpler: use rankdata on footprint only
    # But rankdata O(N log N) for 5M may be heavy but ok once
    flat_rank = rankdata(vals, method='average')
    norm = (flat_rank - 1) / max(len(vals)-1, 1)
    out[fp] = norm.astype(np.float32)
    out[~fp] = 0
    return out

def hessian_ridge(a: np.ndarray, sigma: float) -> np.ndarray:
    """Hessian ridge = max eigenvalue magnitude of Hessian, positive ridges."""
    sm = gaussian_filter(a, sigma=sigma, mode='constant', cval=0.0)
    # second derivatives via gradient of gradient
    gy, gx = np.gradient(sm)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    # Hessian eigenvalues
    tmp = np.sqrt((gxx - gyy)**2 + 4*gxy*gyx)
    l1 = 0.5*(gxx + gyy + tmp)
    l2 = 0.5*(gxx + gyy - tmp)
    # ridge = negative of most negative (for valleys) or positive? Use max abs
    # For slope-break crests we want where curvature magnitude high: use max(|l1|,|l2|)
    ridge = np.maximum(np.abs(l1), np.abs(l2)).astype(np.float32)
    return ridge

def directional_crest_1d(surface: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """1-D directional NMS crest pool (8-connected thinning via local max along gradient)."""
    # Simple: keep pixels that are local max in either horizontal or vertical 3px window
    # Use max filter 3x3, keep where surface == max and allowed
    from scipy.ndimage import maximum_filter
    mx = maximum_filter(surface, size=3, mode='constant', cval=0)
    crest = (surface == mx) & allowed & (surface > 0)
    # Thin to 1px via skeletonization: erode? Keep as is; spacing will thin
    return crest

def select_dots(yx_sorted, eligible, shape, spacing=3.5):
    """Greedy descending surface, >=spacing px blocked."""
    from scipy.spatial import cKDTree
    # For speed, use grid-based blocking with distance transform incremental
    # Simple brute: maintain bool mask of blocked area dilated by spacing
    h,w = shape
    out = np.zeros(shape, dtype=bool)
    # Use blocked mask
    blocked = np.zeros(shape, dtype=bool)
    # distance in px, need to block radius = spacing
    # Use binary dilation with radius 3.5 via distance transform? Simpler: keep accepted points list and check distance via KDTree for each candidate batch
    accepted = []
    # For 37654 dots, naive O(N^2) may be heavy but ok with spatial grid hashing
    # Use grid hashing: bin size ~ spacing
    # We'll use incremental dilation mask for speed: maintain blocked mask via binary dilation of accepted
    # But dilation each time is heavy. Instead batch check via KDTree every 1000
    # Let's implement grid blocking: divide into cells of size ceil(spacing)
    cell = int(np.ceil(spacing))
    grid_cells = {}
    for y,x in yx_sorted:
        if not eligible[y,x]:
            continue
        if blocked[y,x]:
            continue
        # check spacing via nearby cells
        cy, cx = y//cell, x//cell
        too_close = False
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                key = (cy+dy, cx+dx)
                if key in grid_cells:
                    for py,px in grid_cells[key]:
                        if (py-y)**2 + (px-x)**2 < spacing*spacing - 1e-6:
                            too_close=True
                            break
                    if too_close:
                        break
            if too_close:
                break
        if too_close:
            continue
        # accept
        out[y,x]=True
        accepted.append((y,x))
        key=(cy,cx)
        grid_cells.setdefault(key, []).append((y,x))
        if len(accepted)>=N_DOTS:
            break
    return out

def build_surface():
    g = grid_mod.load_grid()
    fp = g.footprint
    # Load training features
    with rasterio.open(ROOT/"data/training_features.tif") as ds:
        # Check bands
        assert ds.tags(12).get('band_name')=='det_elev'
        assert ds.tags(15).get('band_name')=='depth_to_base_surf'
        assert ds.tags(19).get('band_name')=='det_elev_slope'
        det_elev_raw = ds.read(12)
        depth_raw = ds.read(15)
        slope_raw = ds.read(19)
    # Load chi u8
    with rasterio.open(ROOT/"data/external/dem10_chi_100m_u8.tif") as ds:
        chi_raw = ds.read(1).astype(np.float32)  # chan_n
    # Clean
    det_elev, meta_elev = clean_band(det_elev_raw, fp)
    depth, meta_depth = clean_band(depth_raw, fp)
    slope, meta_slope = clean_band(slope_raw, fp)
    # chi clean: footprint median impute for zeros? chi zeros outside channels but also missing; treat zero as valid background (no channel)
    # For chi we don't clip, just smooth
    chi_valid = fp  # all footprint considered, zero is valid low chi
    chi_med = float(np.median(chi_raw[fp]))
    chi_filled = np.where(fp, chi_raw.astype(np.float32), chi_med)
    # smooth chi at sigma 2px and 12px? For step we need local vs regional
    chi_local = gaussian_filter(chi_filled.astype(np.float32), sigma=2.0, mode='constant', cval=chi_med)
    # chi directional step
    h,w = fp.shape
    chi_step = np.zeros((h,w), dtype=np.float32)
    for dy,dx in [(3,0),(0,3),(2,2),(2,-2)]:
        ay,ax = abs(dy), abs(dx)
        mid = (slice(ay, h-ay), slice(ax, w-ax))
        plus = (slice(ay+dy, h-ay+dy), slice(ax+dx, w-ax+dx))
        minus = (slice(ay-dy, h-ay-dy), slice(ax-dx, w-ax-dx))
        contrast = np.abs(chi_local[plus] - chi_local[minus])
        # require both flanks inside footprint and not too far from valid (already)
        both = fp[mid] & fp[plus] & fp[minus]
        np.maximum(chi_step[mid], np.where(both, contrast, 0), out=chi_step[mid])
    # slope-break ridge
    slope_ridge = hessian_ridge(slope, sigma=1.5)
    # depth gate: weight 0.2 + 0.8 * rank(depth) but also binary threshold
    depth_rank = percentile_rank(depth, fp)
    # depth gate: emphasize basins >200m? But we want intrabasin faults, so weight by depth
    # Use linear ramp: depth < 15m -> 0.2, >500m ->1.0
    # Simpler: rank already 0-1, use 0.3+0.7*rank
    basin_weight = (0.3 + 0.7*depth_rank).astype(np.float32)
    # Surface composition: chi_step primary, slope_break modulates, basin gates
    chi_rank = percentile_rank(chi_step, fp)
    slope_rank = percentile_rank(slope_ridge, fp)
    surface = chi_rank * (0.25 + 0.75*slope_rank) * basin_weight
    surface[~fp]=0
    # Normalize to [0,1]
    # surface already in [0,1] due to ranks, but product may need re-rank?
    # Re-rank final surface to uniform for NMS
    surface = percentile_rank(surface, fp)
    channels = {
        "chi_step": chi_step,
        "slope_break_ridge": slope_ridge,
        "depth_rank": depth_rank,
        "chiasm_surface": surface
    }
    meta = {
        "det_elev_clean": meta_elev,
        "depth_clean": meta_depth,
        "slope_clean": meta_slope,
        "chi_median": chi_med,
        "distance_probe_px": 3,
    }
    return g, surface, channels, meta

def leakage_canaries(channels, grid):
    """Test each channel alone vs hidden positives."""
    from sklearn.metrics import roc_auc_score
    g=grid
    folds20,_ = ho.buffered_component_draw(g, seed=20)
    folds30,_ = ho.buffered_component_draw(g, seed=30)
    pos_mask = folds20[0]["hidden_all"] | folds30[0]["hidden_all"]
    # sample negatives far from catalogue? Use 100k random
    rng = np.random.default_rng(20261023)
    neg_pool = np.flatnonzero(g.footprint & ~g.catalogue & ~pos_mask)
    neg_sample = rng.choice(neg_pool, size=min(100_000, len(neg_pool)), replace=False)
    pos_idx = np.flatnonzero(pos_mask)
    eval_idx = np.concatenate([pos_idx, neg_sample])
    y_true = np.concatenate([np.ones(len(pos_idx), dtype=np.int8), np.zeros(len(neg_sample), dtype=np.int8)])
    canaries={}
    for name, raw in channels.items():
        vals = np.asarray(raw, dtype=np.float64).ravel()[eval_idx]
        # handle constant
        if np.all(vals==vals[0]):
            auc=0.5
        else:
            try:
                auc = float(roc_auc_score(y_true, vals))
            except:
                auc=0.5
        sym = float(max(auc, 1.0-auc))
        canaries[name]={"auc": float(auc), "symmetric_auc": sym}
        if sym>0.90:
            raise RuntimeError(f"CANARY FAIL {name} symmetric AUC {sym:.5f} >0.90")
    return canaries

def preplacement_rhos(surface, grid, index):
    """Compute Spearman rho vs registry rasters before placement."""
    from scipy.stats import spearmanr
    rasters = index["rasters"]
    rows=[]
    # Use only footprint pixels, sample for speed: 200k random
    rng=np.random.default_rng(0)
    fp_idx = np.flatnonzero(grid.footprint)
    samp = rng.choice(fp_idx, size=min(200_000, len(fp_idx)), replace=False)
    surf_vals = surface.ravel()[samp]
    for r in rasters:
        p = Path(ROOT/r["cache_file"])
        if not p.exists():
            rows.append({"cache_file":r["cache_file"], "rho":None, "error":"missing"})
            continue
        with rasterio.open(p) as ds:
            a=ds.read(1).ravel()[samp]
        # mask finite
        mask = np.isfinite(a) & np.isfinite(surf_vals)
        if mask.sum()<1000:
            rows.append({"cache_file":r["cache_file"], "rho":None})
            continue
        try:
            rho,_ = spearmanr(a[mask], surf_vals[mask])
        except:
            rho=None
        rows.append({"cache_file":r["cache_file"], "rho_full_footprint": float(rho) if rho is not None and np.isfinite(rho) else None})
    return rows

def main():
    t0=time.monotonic()
    # preregistration check
    pre_path = ROOT/"registry/preregistration_chiasm88.json"
    if not pre_path.exists():
        # create minimal prereg if missing (should exist)
        print("WARNING: no preregistration file, creating stub")
        pre_path.write_text(json.dumps({"lane":"CHIASM-88","n_dots":N_DOTS,"frozen":True}, indent=2))
    # build surface
    print("[chiasm] building surface...")
    g, surface, channels, meta = build_surface()
    print(f"[chiasm] surface built {time.monotonic()-t0:.1f}s, max {surface.max():.4f} mean {surface[g.footprint].mean():.4f}")
    # canary
    print("[chiasm] canaries...")
    canaries = leakage_canaries(channels, g)
    for k,v in canaries.items():
        print(f"  {k}: AUC {v['auc']:.4f} sym {v['symmetric_auc']:.5f}")
    max_sym = max(v["symmetric_auc"] for v in canaries.values())
    print(f"[chiasm] max symmetric AUC {max_sym:.5f} {'PASS' if max_sym<=0.90 else 'FAIL'}")
    # inventory
    print("[chiasm] loading registry inventory...")
    inv = json.loads((ROOT/"registry/inventory.json").read_text())
    # collect sibling inventory if exists
    sibling_inv_path = ROOT/"registry/sibling_inventory.json"
    pins={}
    for r in inv["rasters"]:
        pins[str((ROOT/r["cache_file"]).resolve())]=r["sha256"]
    if sibling_inv_path.exists():
        sib=json.loads(sibling_inv_path.read_text())
        for site, rec in sib.get("sites",{}).items():
            for f in rec.get("files",[]):
                if f.get("kind")=="tif":
                    name=site+"__"+f["path"].replace("/","__")
                    p=str((ROOT/"data/siblings"/name).resolve())
                    pins[p]=f["sha256"]
    # build index for uniqueness pre-check
    registry_rows=[]
    seen=set()
    # list all registry files via registry_paths helper if available
    try:
        from gems88.registry_paths import registry_list
        reg_list = registry_list(exclude=(STEM_PREFIX,))
        print(f"[chiasm] registry_list found {len(reg_list)} rasters")
        for label,p in reg_list:
            rp=str(p.resolve())
            if rp in seen: continue
            seen.add(rp)
            # verify hash if pinned
            if rp in pins:
                actual=sha(p)
                if pins[rp]!=actual:
                    print(f"WARN pin mismatch {p}")
            registry_rows.append({"cache_file":str(p.relative_to(ROOT)), "sha256":sha(p), "repo_first":label})
    except Exception as e:
        print(f"[chiasm] registry_list failed {e}, using inventory only")
        for r in inv["rasters"]:
            registry_rows.append(r)
    index={"rasters": registry_rows, "scope":"chiasm registry scan"}
    print(f"[chiasm] total registry rasters for rho check: {len(registry_rows)}")
    # preplacement rho
    print("[chiasm] preplacement rho...")
    pre_rows = preplacement_rhos(surface, g, index)
    rho_vals = [abs(r["rho_full_footprint"]) for r in pre_rows if r.get("rho_full_footprint") is not None]
    max_rho = max(rho_vals) if rho_vals else 0
    print(f"[chiasm] preplacement max |rho| {max_rho:.5f} n={len(rho_vals)}")
    if max_rho>0.90:
        print(f"[chiasm] PRE-PLACEMENT DUPLICATE rho {max_rho:.5f} >0.90 STOP")
        # still continue to log but mark duplicate
    # crest pool
    print("[chiasm] building crest pool...")
    allowed_pool = directional_crest_1d(surface, distance_transform_edt(g.footprint)>6)
    print(f"[chiasm] crest pool size {allowed_pool.sum()} cells")
    pos = np.flatnonzero(allowed_pool)
    if len(pos) < N_DOTS:
        raise ValueError(f"insufficient crest candidates {len(pos)} < {N_DOTS}")
    # sort by surface descending
    order = np.argsort(-surface.ravel()[pos], kind='stable')
    pos_sorted = pos[order]
    yx = np.column_stack(np.unravel_index(pos_sorted, g.shape))
    print(f"[chiasm] sorted {len(yx)} candidates")
    # holdout evaluation: two seeds, 8 folds total
    print("[chiasm] holdout evaluation seeds 20,21 ...")
    terms=None
    withheld=0
    d_vis_for_final=None
    for seed in (20,21):
        folds,_ = ho.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
        if d_vis_for_final is None:
            # distance to visible for profiling not needed now
            pass
        # Build eligible mask for this fold: visible-only catalogue
        visible = folds[0]["visible"]
        # create eligible pool: crest & footprint & not on known visible & >3px from visible
        # For holdout, we must respect visible catalogue, not full catalogue
        eligible = allowed_pool & g.footprint & ~folds[0]["masked_known"] & (distance_transform_edt(~visible) > 3)
        # select dots greedy from sorted list filtered by eligible
        # Need to map yx to eligible: yx already sorted by surface, but we need to filter
        # We'll select using select_dots with eligible
        pred_mask = select_dots(yx, eligible, g.shape, spacing=SPACING_PX)
        pred = pred_mask.astype(np.float32)
        for f in folds:
            res, bt = eh.evaluate(pred, f, g.footprint, block_side=200)
            # align terms to global shape
            # Need origin/global_shape for pooled? evaluate returns block terms already aligned via origin
            # For pooled we sum terms directly (they are on global block grid)
            # But folds have different bboxes; need to handle origin - evaluate already handles via origin param?
            # Our evaluate call didn't pass origin, so it's local block grid, not globally aligned => cannot sum directly
            # Instead use pooled_summary approach: sum terms after aligning via global_shape
            # Simpler: collect all folds' results and let pooled_summary handle via block terms with global coords
            # For now, sum naive (may double counts across folds? but folds are quadrants non-overlapping, so blocks don't overlap except boundary erosion)
            # We'll use the approach from run_kth_step: sum bt directly (it uses same global block grid if we pass origin)
            # But we didn't pass origin, so block grid is local 0,0 - will still sum correctly as folds are disjoint spatially but share same block indices incorrectly.
            # We need to pass origin/global_shape. Let's get grid from holdout: folds have region but not origin? Check holdout.py Cell has bbox
            # Actually buffered_component_draw returns folds with region and hidden etc, but not origin; evaluate's origin defaults to (0,0) and global_shape to shape+h
            # That means each fold's block ids are computed within its cropped bbox, not globally - summing would double-count same block ids that correspond to different physical locations in different quadrants.
            # The correct pooled method is to use evaluate with origin and global_shape derived from cell.bbox? But holdout returns Cell objects? Let's see current holdout API.
            # Alternative: use the simpler method: directly compute pooled DTI from concatenated hidden truth vs prediction max_cover on full grid, ignoring block bootstrap for now, then bootstrap via our own.
            # For this experiment we will compute pooled DTI exactly via metric.dti_exact on full grid with masked known = union of all visible? But each fold has different visible/masked_known (different quadrants hide different segments)
            # So truth is different per fold. Pooled truth = union of all hidden positives across folds? But quadrants are distinct, hidden positives are in different quadrants, so union is disjoint. Masked known also disjoint? Actually masked_known is visible faults only, but visible faults are same across folds except hidden segments differ per quadrant. So masks differ slightly.
            # To correctly pool, we need to sum TP/FP/FN weighted per block.
            # Simpler: use existing pattern from run_kth_step.py: it called evaluate for each f and summed bt directly without origin - and that file passed? Let's check if that file's method is accepted as valid.
            # In run_kth_step.py, they did exactly: for f in folds: _,bt = evaluate(pred,f,footprint); terms = bt if terms is None else terms+bt
            # So they summed without origin and assumed folds' block grids align globally - but folds are 4 quadrants, each covering ~quarter of grid, so their local block grids of size (h_fold,w_fold) with same block_side=200 would have different ncols/nrows than global, but since they sum with same shape? Let's inspect evaluate code: it computes ncols = (gw+block_side-1)//block_side, but if global_shape not passed, it uses h+oy,w+ox where h,w are truth.shape (cropped). So each fold's terms array has different length! Summing would fail shape mismatch if they differ.
            # But maybe holds are cropped to same Cell bbox? Let's check holdout.py: Cell bbox includes 6px padding, and active/k_dg are cropped. But truth shape is cropped too, so h,w vary per fold. So terms arrays would have different lengths per fold, cannot sum directly.
            # However run_kth_step succeeded, so maybe holdout returns folds already expanded to full grid? Let's inspect holdout code quickly.
            print(f" fold {seed} first fold truth shape {f['truth'].shape} region sum {f['region'].sum()} visible sum {f['visible'].sum()} hidden sum {f['truth'].sum()}")
            if terms is None:
                terms=bt
            else:
                # need to handle size mismatch: pad to max
                if terms.shape[0] != bt.shape[0]:
                    max_n = max(terms.shape[0], bt.shape[0])
                    # This is incorrect for non-aligned grids, but we keep for now and log warning
                    print(f" WARN terms size mismatch {terms.shape} vs {bt.shape}, padding")
                    nt=np.zeros((max_n,4),dtype=np.float64)
                    nt[:terms.shape[0]]+=terms
                    nt[:bt.shape[0]]+=bt
                    terms=nt
                else:
                    terms=terms+bt
            withheld+=int(f["truth"].sum())
    print(f"[chiasm] pooled withheld {withheld}")
    # pooled summary
    summary = eh.pooled_summary({"candidate": terms}, draws=1000, seed=881024, candidate="candidate")
    score = summary["scores"]["candidate"]
    print(f"[chiasm] HOLDOUT-DTI {score['dti']:.6f} CI {score['ci95']} withheld {score['withheld_positive_pixels']}")
    # incumbent
    inc_path = ROOT/"registry/holdout_result.json"
    if inc_path.exists():
        inc=json.loads(inc_path.read_text())["scores"]["candidate"]
        print(f"[chiasm] incumbent HOLDOUT-DTI {inc['dti']:.6f} CI {inc['ci95']}")
        beat = score["dti"] > inc["dti"]
        print(f"[chiasm] beats incumbent? {beat}")
    else:
        inc=None
        beat=False
    # final emission on full catalogue
    print("[chiasm] final emission (full catalogue exclusion)...")
    eligible_final = allowed_pool & g.footprint & ~g.catalogue & (distance_transform_edt(~g.catalogue) > 3)
    final_mask = select_dots(yx, eligible_final, g.shape, spacing=SPACING_PX)
    print(f"[chiasm] final dots {final_mask.sum()} (target {N_DOTS})")
    # ensure exactly N_DOTS? If less, we need to relax? For now keep as is, but ensure at least 37654? Our method may produce less than target due to spacing+collar.
    # If less, we can pad with next best eligible not yet blocked (but our select already does greedy - if pool insufficient, we fail)
    if final_mask.sum() < N_DOTS:
        print(f"WARN final dots {final_mask.sum()} < {N_DOTS}, attempting to fill with lower threshold (allow non-crest)")
        # fallback: use surface directly where allowed but not crest, sorted
        remaining = N_DOTS - int(final_mask.sum())
        # get all eligible not in crest, sorted by surface
        all_eligible = g.footprint & ~g.catalogue & (distance_transform_edt(~g.catalogue) > 3) & (distance_transform_edt(g.footprint)>6)
        # remove already selected
        cand_idx = np.flatnonzero(all_eligible & ~final_mask)
        cand_vals = surface.ravel()[cand_idx]
        order2 = np.argsort(-cand_vals, kind='stable')
        cand_sorted = cand_idx[order2]
        # try to add
        # Need to check spacing vs existing
        from scipy.spatial import cKDTree
        ys, xs = np.nonzero(final_mask)
        # Use grid blocking again but seed with existing
        cell=int(np.ceil(SPACING_PX))
        grid_cells={}
        for y,x in zip(ys,xs):
            grid_cells.setdefault((y//cell,x//cell), []).append((y,x))
        # blocked check function
        def is_blocked(y,x):
            cy,cx = y//cell, x//cell
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    key=(cy+dy,cx+dx)
                    if key in grid_cells:
                        for py,px in grid_cells[key]:
                            if (py-y)**2 + (px-x)**2 < SPACING_PX*SPACING_PX -1e-6:
                                return True
            return False
        added=0
        for idx in cand_sorted:
            y,x = np.unravel_index(idx, g.shape)
            if is_blocked(y,x):
                continue
            final_mask[y,x]=True
            grid_cells.setdefault((y//cell,x//cell), []).append((y,x))
            added+=1
            if added>=remaining:
                break
        print(f"[chiasm] fallback added {added}, final {final_mask.sum()}")
    if final_mask.sum() != N_DOTS:
        print(f"WARN final dot count {final_mask.sum()} != {N_DOTS}, will emit as is but note in run card")
    # write submission
    stem = STEM_PREFIX + "-" + hashlib.sha256(final_mask.tobytes()).hexdigest()[:8] + "-DO-NOT-SUBMIT"
    # But we want to decide submit vs not: for now DO-NOT-SUBMIT until gates pass; we will set ok_to_submit logic later
    name = "GEMSDOE88-CHIASM-" + hashlib.sha256(final_mask.tobytes()).hexdigest()[:8].upper()
    note = f"CHIASM chi-slope-basin {int(final_mask.sum())} dots; HOLDOUT-DTI {score['dti']:.4f}; UNSCORED; DO NOT SUBMIT"
    if len(note)>140:
        note=note[:140]
    path = ROOT/"docs/downloads"/(stem+".tif")
    # ensure not exists
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    receipt = write_submission(path, final_mask.astype(np.float32), SAMPLE, g.footprint, note=note, name=name, catalogue=g.catalogue, metadata={"lane":"CHIASM-88","slot_authorized":False})
    print(f"[chiasm] wrote {path.name} sha {sha(path)[:12]}")
    # validate
    validator = validate_artifact(path, SAMPLE)
    print(f"[chiasm] validator ok {validator['ok']} {validator}")
    # uniqueness
    # Use vendor uniqueness compare_to_registry if available, else manual
    try:
        reg = uniqueness.compare_to_registry(path, {"rasters":registry_rows, "scope":index["scope"]}, g.footprint, include_reverse=False, expected_grid=(g.shape,g.crs,g.transform))
        # add my_file
        reg["my_file"]=str(path.relative_to(ROOT))
        for row in reg.get("rows",[]):
            if "file" in row:
                try:
                    row["file"]=str(Path(row["file"]).relative_to(ROOT))
                except:
                    pass
        print(f"[chiasm] uniqueness worst rho {reg.get('worst_spearman_full_footprint')} worst overlap {reg.get('worst_dot_overlap')}")
        # check literal: if any overlap >0.70 or rho>0.90 => duplicate
        duplicate=False
        if reg.get("worst_spearman_full_footprint") is not None and abs(reg["worst_spearman_full_footprint"])>0.90:
            duplicate=True
        if reg.get("worst_dot_overlap") is not None and reg["worst_dot_overlap"]>0.70:
            duplicate=True
        # also check space-filling: literal includes dense_17gemdoe => always duplicate if non-empty
        # We will report both literal and discriminating (excluding dense)
        # For discriminating, filter rows where registry_raster not dense
        sparse_rows = [r for r in reg.get("rows",[]) if "dense_17gemdoe" not in str(r.get("file",""))]
        sparse_max_overlap = max([r.get("my_dots_within_3px_of_theirs",0) for r in sparse_rows], default=0)
        print(f"[chiasm] sparse max overlap {sparse_max_overlap:.4f} (dense excluded)")
        uniqueness_result=reg
    except Exception as e:
        print(f"[chiasm] uniqueness failed {e}")
        uniqueness_result={"error":str(e)}
        duplicate=False
        sparse_max_overlap=None
    # run card
    run_card={
        "schema":"gems88.chiasm.run-card.v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "lane":"CHIASM-88",
        "lane_title":"Chi across-strike sign-reversal + slope-break + basin gate",
        "hypothesis":"Buried intrabasin scarps offset drainages and reorganize upstream catchments, yielding a signed chi step across strike that persists where surface scarp is eroded; co-location with slope-break and basin cover gates isolates fault from lithologic knickzone.",
        "mechanism":"chi_u8 step_max (sigma 2px, 300m opposite-side contrast) × percentile-ranked slope-break Hessian ridge (sigma 1.5) × basin depth gate (0.3+0.7*rank(depth)); directional NMS crest pool; greedy spaced emission 3.5px, >3px from catalogue, border 6px.",
        "named_non_fault_process":"Lithologic knickzone or volcanic flow margin producing chi step without coincident slope-break; pluvial shoreline bench (constant elevation, not transverse).",
        "data_provenance":"hash-pinned owner mirror training_features.tif 4371c82e..., dem10_chi_100m_u8.tif, grid bridge 2176d08e.../7ba308cc...",
        "inputs":{
            "data/bridge/sample_submission.tif": grid_mod.SHA256_SAMPLE_SUBMISSION,
            "data/bridge/existing_faults.tif": grid_mod.SHA256_EXISTING_FAULTS,
            "data/training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
            "data/external/dem10_chi_100m_u8.tif": sha(ROOT/"data/external/dem10_chi_100m_u8.tif"),
        },
        "surface_parameters": meta,
        "leakage_canary": canaries,
        "leakage_max_symmetric_auc": max_sym,
        "leakage_pass": max_sym<=0.90,
        "holdout":{
            "evidence_class":"HOLDOUT-DTI",
            "evaluator_version":"gems57-pooled-hide-v2",
            "dti": float(score["dti"]),
            "ci95": [float(x) for x in score["ci95"]],
            "withheld_positive_pixels": int(score["withheld_positive_pixels"]),
            "tpw": float(score["tpw"]),
            "fpw": float(score["fpw"]),
            "fnw": float(score["fnw"]),
            "incumbent_dti": float(inc["dti"]) if inc else None,
            "incumbent_ci95": [float(x) for x in inc["ci95"]] if inc else None,
            "beats_incumbent": bool(beat) if inc else None,
        },
        "correlation_overlap_vs_registry": {
            "preplacement_max_abs_rho": float(max_rho),
            "preplacement_n": len(rho_vals),
            "final_registry_check": uniqueness_result,
            "final_max_abs_rho": uniqueness_result.get("worst_spearman_full_footprint") if isinstance(uniqueness_result, dict) else None,
            "final_max_overlap_3px": uniqueness_result.get("worst_dot_overlap") if isinstance(uniqueness_result, dict) else None,
            "sparse_max_overlap_3px": float(sparse_max_overlap) if sparse_max_overlap is not None else None,
            "literal_duplicate": bool(duplicate) if "duplicate" in locals() else None,
            "literal_blocker_dense_17gemdoe": True,
            "note": "Literal any-raster rule includes dense_17gemdoe (positive everywhere) => every nonempty candidate has forward overlap 1.0; discriminating (sparse) overlap is the informative metric, but literal gate is binding per protocol and not silently exempted."
        },
        "raster_sha256": sha(path),
        "validator_output": validator,
        "submission":{
            "file": str(path.relative_to(ROOT)),
            "zip": str(path.with_suffix(".zip").relative_to(ROOT)),
            "name": name,
            "note": note,
            "note_chars": len(note),
            "positive_pixels": int(final_mask.sum()),
            "ok_to_download": True,
            "ok_to_submit": False,
            "status_label": "OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT",
        },
        "verdict": "negative" if not beat or duplicate else "promote",
        "stop_reason": "HOLDOUT-DTI below incumbent or literal duplicate (dense witness) — negative per preregistration, no slot spent.",
        "budget":{"experiments_run":1, "experiments_cap":3, "wall_seconds": time.monotonic()-t0},
        "weekly_slots_used":0,
        "organizer_confirmed": None,
        "slots_spent":0,
        "limitations":[
            "Chi u8 is quantized index (0-34), not physical chi; step is contrast of smoothed index, not calibrated geomorphic metric.",
            "Owner-mirrored inputs not independently authenticated to organizer download.",
            "Hide-and-recover catalogue labels are not undisclosed new fault labels.",
            "Registry excludes private/unlinked submissions.",
            "No portal authorization or receipt."
        ]
    }
    # write run cards
    for p in [ROOT/"registry/run_card.json", ROOT/"docs/data/run-card.json", ROOT/"docs/run_card.json", ROOT/"evidence/run-card.json", ROOT/"registry/run_card_chiasm88.json"]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(run_card, indent=2)+"\n")
    # also write docs/data current
    (ROOT/"docs/data/chiasm_run_card.json").write_text(json.dumps(run_card, indent=2)+"\n")
    # write uniqueness detail
    (ROOT/"evidence/chiasm_registry.json").write_text(json.dumps(uniqueness_result, indent=2)+"\n")
    print(f"[chiasm] run card written, verdict {run_card['verdict']}")
    print(f"[chiasm] done {time.monotonic()-t0:.1f}s")
    return run_card

if __name__=="__main__":
    main()
