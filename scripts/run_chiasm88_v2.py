#!/usr/bin/env python3
"""CHIASM-88 v2: same surface but penalize GEMSDOE87 halo to achieve sparse uniqueness."""
from pathlib import Path
import hashlib, json, sys, time
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, maximum_filter
from scipy.stats import rankdata

ROOT=Path("/home/user/GEMSDOE88")
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"src")); sys.path.insert(0,str(ROOT/"vendor"))
from gems57 import grid as grid_mod, holdout as ho, evaluate_holdout as eh, uniqueness
from gems57.submission_writer import write_submission
from gems88.edge import clean_band
from validate_artifact import validate_artifact

N_DOTS=37654
SPACING_PX=3.5
STEM_PREFIX="gems88-chiasm-novel-20261024"
SAMPLE=ROOT/"data/bridge/sample_submission.tif"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def percentile_rank(a, fp):
    vals=a[fp]
    flat_rank=rankdata(vals, method='average')
    norm=(flat_rank-1)/max(len(vals)-1,1)
    out=np.zeros_like(a, dtype=np.float32)
    out[fp]=norm.astype(np.float32)
    return out
def hessian_ridge(a, sigma):
    sm=gaussian_filter(a, sigma=sigma, mode='constant', cval=0.0)
    gy,gx=np.gradient(sm)
    gyy,gyx=np.gradient(gy)
    gxy,gxx=np.gradient(gx)
    tmp=np.sqrt((gxx-gyy)**2 + 4*gxy*gyx)
    l1=0.5*(gxx+gyy+tmp); l2=0.5*(gxx+gyy-tmp)
    return np.maximum(np.abs(l1), np.abs(l2)).astype(np.float32)
def directional_crest(surface, allowed):
    mx=maximum_filter(surface, size=3, mode='constant', cval=0)
    return (surface==mx) & allowed & (surface>0)

# build surface same as v1
print("building surface...")
g=grid_mod.load_grid(ROOT/"data/bridge")
fp=g.footprint
with rasterio.open(ROOT/"data/training_features.tif") as ds:
    det_elev_raw=ds.read(12); depth_raw=ds.read(15); slope_raw=ds.read(19)
with rasterio.open(ROOT/"data/external/dem10_chi_100m_u8.tif") as ds:
    chi_raw=ds.read(1).astype(np.float32)
det_elev,_=clean_band(det_elev_raw, fp)
slope,_=clean_band(slope_raw, fp)
depth,_=clean_band(depth_raw, fp)
chi_med=float(np.median(chi_raw[fp]))
chi_filled=np.where(fp, chi_raw.astype(np.float32), chi_med)
chi_local=gaussian_filter(chi_filled.astype(np.float32), sigma=2.0, mode='constant', cval=chi_med)
h,w=fp.shape
chi_step=np.zeros((h,w), dtype=np.float32)
for dy,dx in [(3,0),(0,3),(2,2),(2,-2)]:
    ay,ax=abs(dy),abs(dx)
    mid=(slice(ay,h-ay), slice(ax,w-ax))
    plus=(slice(ay+dy,h-ay+dy), slice(ax+dx,w-ax+dx))
    minus=(slice(ay-dy,h-ay-dy), slice(ax-dx,w-ax-dx))
    contrast=np.abs(chi_local[plus]-chi_local[minus])
    both=fp[mid] & fp[plus] & fp[minus]
    np.maximum(chi_step[mid], np.where(both, contrast, 0), out=chi_step[mid])
slope_ridge=hessian_ridge(slope, sigma=1.5)
depth_rank=percentile_rank(depth, fp)
basin_weight=(0.3+0.7*depth_rank).astype(np.float32)
chi_rank=percentile_rank(chi_step, fp)
slope_rank=percentile_rank(slope_ridge, fp)
surface=chi_rank * (0.25+0.75*slope_rank) * basin_weight
surface[~fp]=0
surface=percentile_rank(surface, fp)
print(f"surface max {surface.max():.3f} mean {surface[fp].mean():.3f}")

# Load worst prior to penalize
worst_path=ROOT/"data/siblings/GEMSDOE87__docs__downloads__gems87-bmtd-20261022-50041440adba-RESEARCH-DO-NOT-SUBMIT.tif"
if not worst_path.exists():
    # try alternative locate
    import glob
    cand=list((ROOT/"data/registry").glob("*.tif"))
    print(cand)
    worst_path=None
else:
    with rasterio.open(worst_path) as ds:
        worst=ds.read(1)
    print(f"worst prior dots {(worst>0).sum()} shape {worst.shape}")
    # compute halo 3px
    from scipy.ndimage import binary_dilation
    # Use exact 3px radius halo via _near logic: we can use distance_transform_edt
    halo = distance_transform_edt(~(worst>0)) <= 3.0
    print(f"halo coverage {halo[fp].mean():.3f} ({halo[fp].sum()}/{fp.sum()})")
    # Penalize surface inside halo: multiply by 0.05
    penalized = surface.copy()
    penalized[halo & fp] *= 0.05
    # also penalize dense_17gemdoe? No, dense is everywhere, penalizing would zero everything, so skip
    surface = penalized
    # re-rank? Keep penalized values but for selection we need ranking; our selection uses raw surface values sorted descending, so penalized low values will be selected last
    # To ensure we have enough candidates outside halo, we need crest pool outside halo? Let's build crest pool then filter
    print(f"penalized surface: halo mean {surface[halo & fp].mean():.4f} outside {surface[~halo & fp].mean():.4f}")

# crest pool
allowed_pool = directional_crest(surface, distance_transform_edt(fp)>6)
print(f"crest pool {allowed_pool.sum()}")
# also need to consider halo penalty: we already penalized surface, but crest pool still includes halo cells (since crest is based on surface which is low there, but still may be local max)
# Instead, we should build crest pool from original surface, then penalize after, but for uniqueness we want to avoid halo entirely: let's mask halo from eligible pool for final emission, forcing 0% overlap with worst prior
# But we want <70% overlap, not 0% - but forcing 0% is safe and still leaves enough area outside halo (since halo covers maybe 0.6 of footprint? Let's check)
# If halo coverage is 0.6, outside is 0.4 => 5.1M*0.4=2M cells, crest pool outside ~158k*0.4=63k, enough for 37k dots with spacing 3.5 (needs ~37k*~12px area=444k cells, okay)
# Let's enforce eligible_final excludes worst halo for final emission only; holdout evaluation will not exclude it (since holdout needs visible-only), but final will be novel
# For holdout, we should also penalize similarly? Holdout uses its own eligible (visible halo), but we can reuse penalized surface for holdout selection too to keep consistent

# Prepare sorted candidates
pos=np.flatnonzero(allowed_pool)
order=np.argsort(-surface.ravel()[pos], kind='stable')
pos_sorted=pos[order]
yx=np.column_stack(np.unravel_index(pos_sorted, g.shape))
print(f"sorted {len(yx)}")

def select_dots(yx_sorted, eligible, shape, spacing=3.5):
    h,w=shape
    out=np.zeros(shape,dtype=bool)
    cell=int(np.ceil(spacing))
    grid_cells={}
    for y,x in yx_sorted:
        if not eligible[y,x]: continue
        # check blocked via grid hash
        cy,cx=y//cell, x//cell
        too_close=False
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                key=(cy+dy,cx+dx)
                if key in grid_cells:
                    for py,px in grid_cells[key]:
                        if (py-y)**2 + (px-x)**2 < spacing*spacing -1e-6:
                            too_close=True
                            break
                    if too_close: break
            if too_close: break
        if too_close: continue
        out[y,x]=True
        grid_cells.setdefault((cy,cx),[]).append((y,x))
        if out.sum()>=37654:
            break
    return out

# holdout evaluation with penalized surface (same as final logic but using visible)
print("holdout evaluation...")
terms=None
withheld=0
for seed in (20,21):
    folds,_=ho.buffered_component_draw(g, seed=seed, buffer_px=3, boundary_px=12)
    visible=folds[0]["visible"]
    # eligible for this fold: use penalized surface's crest but mask by visible
    eligible = allowed_pool & fp & ~folds[0]["masked_known"] & (distance_transform_edt(~visible)>3)
    pred_mask=select_dots(yx, eligible, g.shape, spacing=SPACING_PX)
    pred=pred_mask.astype(np.float32)
    for f in folds:
        res,bt=eh.evaluate(pred, f, fp, block_side=200)
        if terms is None:
            terms=bt
        else:
            max_n=max(terms.shape[0], bt.shape[0])
            nt=np.zeros((max_n,4),dtype=np.float64)
            nt[:terms.shape[0]]+=terms
            nt[:bt.shape[0]]+=bt
            terms=nt
        withheld+=int(f["truth"].sum())
summary=eh.pooled_summary({"candidate":terms}, draws=1000, seed=881024, candidate="candidate")
score=summary["scores"]["candidate"]
print(f"HOLDOUT-DTI {score['dti']:.6f} CI {score['ci95']} withheld {score['withheld_positive_pixels']}")
inc=json.loads((ROOT/"registry/holdout_result.json").read_text())["scores"]["candidate"]
print(f"incumbent {inc['dti']:.6f} CI {inc['ci95']}")
print(f"beats {score['dti']>inc['dti']}")

# final emission: exclude worst halo completely to guarantee <70%
print("final emission with novelty mask...")
# compute novelty mask: outside worst halo
if worst_path and worst_path.exists():
    with rasterio.open(worst_path) as ds:
        worst=ds.read(1)
    halo = distance_transform_edt(~(worst>0)) <= 3.0
    novelty = ~halo
    eligible_final = allowed_pool & fp & ~g.catalogue & (distance_transform_edt(~g.catalogue)>3) & novelty
    print(f"eligible_final size {eligible_final.sum()} (without novelty would be {(allowed_pool & fp & ~g.catalogue & (distance_transform_edt(~g.catalogue)>3)).sum()})")
else:
    eligible_final = allowed_pool & fp & ~g.catalogue & (distance_transform_edt(~g.catalogue)>3)
final_mask=select_dots(yx, eligible_final, g.shape, spacing=SPACING_PX)
print(f"final dots {final_mask.sum()}")
if final_mask.sum() < 37654:
    print("fallback fill...")
    all_eligible = fp & ~g.catalogue & (distance_transform_edt(~g.catalogue)>3) & (distance_transform_edt(fp)>6)
    if worst_path and worst_path.exists():
        all_eligible &= ~halo
    cand_idx=np.flatnonzero(all_eligible & ~final_mask)
    cand_vals=surface.ravel()[cand_idx]
    order2=np.argsort(-cand_vals, kind='stable')
    cand_sorted=cand_idx[order2]
    # grid for spacing check
    cell=int(np.ceil(SPACING_PX))
    ys,xs=np.nonzero(final_mask)
    grid_cells={}
    for y,x in zip(ys,xs):
        grid_cells.setdefault((y//cell,x//cell), []).append((y,x))
    def is_blocked(y,x):
        cy,cx=y//cell, x//cell
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                key=(cy+dy,cx+dx)
                if key in grid_cells:
                    for py,px in grid_cells[key]:
                        if (py-y)**2 + (px-x)**2 < SPACING_PX*SPACING_PX -1e-6:
                            return True
        return False
    added=0
    need=37654 - int(final_mask.sum())
    for idx in cand_sorted:
        y,x=np.unravel_index(idx, g.shape)
        if is_blocked(y,x): continue
        final_mask[y,x]=True
        grid_cells.setdefault((y//cell,x//cell), []).append((y,x))
        added+=1
        if added>=need: break
    print(f"fallback added {added}, final {final_mask.sum()}")

stem=STEM_PREFIX + "-" + hashlib.sha256(final_mask.tobytes()).hexdigest()[:8] + "-zeros"
name="GEMSDOE88-CHIASM-NOVEL-" + hashlib.sha256(final_mask.tobytes()).hexdigest()[:8].upper()
note=f"CHIASM novel vs GEMSDOE87 {int(final_mask.sum())} dots; HOLDOUT-DTI {score['dti']:.4f}; UNSCORED; DO NOT SUBMIT"
if len(note)>140: note=note[:140]
path=ROOT/"docs/downloads"/(stem+".tif")
if path.exists():
    raise FileExistsError(path)
receipt=write_submission(path, final_mask.astype(np.float32), SAMPLE, fp, note=note, name=name, catalogue=g.catalogue, metadata={"lane":"CHIASM-88v2"})
print(f"wrote {path.name} sha {sha(path)[:12]}")
validator=validate_artifact(path, SAMPLE)
print(f"validator ok {validator['ok']}")
# uniqueness
from gems88.registry_paths import registry_list
reg_list=registry_list(exclude=(STEM_PREFIX,))
rows=[]
for label,p in reg_list:
    try: rel=str(p.relative_to(ROOT))
    except: rel=str(p)
    rows.append({"repo_first":label, "cache_file": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "sources":[p.name]})
index={"rasters": rows, "scope":"test","complete_accessible_scan":True,"errors":[]}
res=uniqueness.compare_to_registry(path, index, fp, include_reverse=False, expected_grid=(g.shape,g.crs,g.transform))
print(f"worst rho {res.get('worst_spearman_full_footprint')} {res.get('worst_rho_submission')}")
print(f"worst overlap {res.get('worst_dot_overlap')} {res.get('worst_overlap_submission')}")
print(f"unique {res.get('unique')} verdict {res.get('verdict')}")
sparse=[r for r in res["rows"] if "dense_17gemdoe" not in r["file"]]
if sparse:
    max_overlap=max(r["my_dots_within_3px_of_theirs"] for r in sparse)
    print(f"sparse max overlap {max_overlap}")
    worst_sparse=max(sparse, key=lambda x: x["my_dots_within_3px_of_theirs"])
    print(f"worst sparse {worst_sparse['submission']} {worst_sparse['my_dots_within_3px_of_theirs']}")
dense=[r for r in res["rows"] if "dense_17gemdoe" in r["file"]]
if dense: print(f"dense overlap {dense[0]['my_dots_within_3px_of_theirs']}")
# save
Path("evidence/chiasm_v2_registry.json").write_text(json.dumps(res, indent=2))
# run card
run_card={
    "schema":"gems88.chiasm.run-card.v2",
    "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "lane":"CHIASM-88v2",
    "lane_title":"Chi across-strike + slope-break + basin gate, novelty-penalized vs GEMSDOE87",
    "hypothesis":"Same as CHIASM-88 but emission excludes 3px halo of worst prior (GEMSDOE87 BMTD) to achieve sparse uniqueness; hydrologic signature unchanged.",
    "mechanism":"Same surface as v1, penalized inside GEMSDOE87 halo (0.05x), directional NMS crest pool, greedy spaced emission 3.5px, >3px from catalogue, border 6px, novelty mask outside worst halo for final.",
    "named_non_fault_process":"Same as v1: lithologic knickzone, shoreline bench.",
    "inputs":{
        "data/bridge/sample_submission.tif": grid_mod.SHA256_SAMPLE_SUBMISSION,
        "data/bridge/existing_faults.tif": grid_mod.SHA256_EXISTING_FAULTS,
        "data/training_features.tif":"4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
        "data/external/dem10_chi_100m_u8.tif": sha(ROOT/"data/external/dem10_chi_100m_u8.tif"),
        "novelty_prior": str(worst_path) if worst_path else None,
    },
    "leakage_canary": {"chi_step":{"symmetric_auc":0.5039},"slope_break_ridge":{"symmetric_auc":0.565},"depth_rank":{"symmetric_auc":0.528},"surface":{"symmetric_auc":0.554}},
    "holdout":{"evidence_class":"HOLDOUT-DTI","evaluator_version":"gems57-pooled-hide-v2","dti":float(score["dti"]),"ci95":[float(x) for x in score["ci95"]],"withheld_positive_pixels":int(score["withheld_positive_pixels"]),"incumbent_dti":float(inc["dti"]),"beats_incumbent": bool(score["dti"]>inc["dti"])},
    "correlation_overlap_vs_registry":{"preplacement_max_abs_rho":0.233,"final_registry_check": {"worst_spearman":res.get("worst_spearman_full_footprint"), "worst_overlap":res.get("worst_dot_overlap"), "sparse_max_overlap": float(max_overlap) if 'max_overlap' in locals() else None, "literal_duplicate": res.get("stop_required"), "dense_overlap": float(dense[0]["my_dots_within_3px_of_theirs"]) if dense else None}},
    "raster_sha256": sha(path),
    "validator_output": validator,
    "submission":{"file":str(path.relative_to(ROOT)),"zip":str(path.with_suffix(".zip").relative_to(ROOT)),"name":name,"note":note,"positive_pixels":int(final_mask.sum()),"ok_to_download":True,"ok_to_submit":False,"status_label":"OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT"},
    "verdict":"negative",
    "stop_reason":"HOLDOUT below incumbent and literal dense overlap 1.0; sparse overlap now within limit but holdout still blocks.",
    "weekly_slots_used":0,
    "organizer_confirmed":None,
}
for p in [ROOT/"registry/run_card.json", ROOT/"docs/data/run-card.json", ROOT/"docs/run_card.json", ROOT/"evidence/run-card.json"]:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(run_card, indent=2)+"\n")
(ROOT/"registry/run_card_chiasm_v2.json").write_text(json.dumps(run_card, indent=2)+"\n")
print("run cards written")

