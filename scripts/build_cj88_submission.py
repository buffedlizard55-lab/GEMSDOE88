#!/usr/bin/env python3
"""CJ88: Crest-Junction/Termination prior. Unique lane: dots ranked by proximity to
skeleton junctions/endpoints/stepovers of the B19/3/18/15 composite crest (geophysics+topo only,
no catalogue geometry). Holdout: seeds20+30 buffered hide-and-recover, gems57-pooled-hide-v2.
Mimic: unfaulted bajada/terrace/volcanic-flow crest junctions."""
import hashlib,json,sys,time,zipfile
from pathlib import Path
import numpy as np, rasterio
from scipy.ndimage import binary_dilation,distance_transform_edt,convolve
from scipy.spatial import cKDTree
sys.path.insert(0,str(Path(__file__).parents[1])); sys.path.insert(0,str(Path(__file__).parents[1]/"vendor")); sys.path.insert(0,str(Path(__file__).parent))
from gems57 import evaluate_holdout, grid as gm, holdout as hm, uniqueness
from gems57.submission_writer import write_submission
import build_provcrest_submission as pc
ROOT=Path(__file__).parents[1]; N=37654; SPACING=3.5
def sha(b): return hashlib.sha256(b).hexdigest()
def select(order,elig,shape):
    blocked=np.zeros(shape,bool); out=np.zeros(shape,bool); disk=np.array(pc._DISK)
    n=0
    for y,x in order:
        if n>=N: break
        if not elig[y,x] or blocked[y,x]: continue
        out[y,x]=True; n+=1
        ys, xs=y+disk[:,0],x+disk[:,1]; ok=(ys>=0)&(ys<shape[0])&(xs>=0)&(xs<shape[1]); blocked[ys[ok],xs[ok]]=True
    if n!=N: raise RuntimeError(f"placed {n}")
    return out
def main():
    t0=time.time(); verified=pc.bpv.verify_manifest(); gd=gm.load_grid(ROOT/"data/bridge"); foot,cat=gd.footprint,gd.catalogue
    dcat=distance_transform_edt(~cat)
    crest,cmask,canaries=pc.build_crest(verified,foot,cat); print("crest",cmask.sum(),canaries,flush=True)
    from skimage.morphology import skeletonize
    skel=skeletonize(cmask)
    neigh=convolve(skel.astype(np.int32),np.ones((3,3),int),mode='constant')-skel
    junction=skel&(neigh>=3); endpoint=skel&(neigh==1)
    print(f"skel={skel.sum()} junctions={junction.sum()} endpoints={endpoint.sum()}",flush=True)
    # distance to nearest junction/endpoint (px); bonus decays 12px
    dj=distance_transform_edt(~junction); de=distance_transform_edt(~endpoint)
    bonus=(np.exp(-dj/6.0)+0.7*np.exp(-de/6.0)).astype(np.float32)
    surface=(crest*(0.35+bonus)).astype(np.float32); surface[~foot]=0
    # canary for surface
    from sklearn.metrics import roc_auc_score
    folds20,_=hm.buffered_component_draw(gd,seed=20); folds30,_=hm.buffered_component_draw(gd,seed=30)
    pos=folds20[0]["hidden_all"]|folds30[0]["hidden_all"]; rng=np.random.default_rng(1)
    neg=rng.choice(np.flatnonzero(foot&~cat&~pos),size=100000,replace=False); pidx=np.flatnonzero(pos)
    ei=np.concatenate([pidx,neg]); y=np.concatenate([np.ones(len(pidx)),np.zeros(len(neg))])
    auc=float(roc_auc_score(y,surface.ravel()[ei])); canaries["cj88_surface"]=round(max(auc,1-auc),5)
    assert canaries["cj88_surface"]<=0.90, canaries
    import os
    if os.environ.get("CJ88_EXCLUDE_PROVCREST"):
        with rasterio.open(ROOT/"../GEMSDOE88/docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros-DO-NOT-SUBMIT.tif") as _d: pass
        with rasterio.open(ROOT/"docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros-DO-NOT-SUBMIT.tif") as _d: prov=(_d.read(1)>0)&foot
        cmask = cmask & ~binary_dilation(prov, structure=np.ones((7,7),bool))
        print("excluded provcrest neighbourhood, crest pool", int(cmask.sum()), flush=True)
    cy,cx=np.nonzero(cmask); score=surface[cy,cx]
    rank=np.column_stack([cy[np.argsort(-score,kind="stable")],cx[np.argsort(-score,kind="stable")]])
    rand=np.column_stack([cy[rng.permutation(len(cy))],cx[rng.permutation(len(cy))] if False else cx]) # placeholder fixed below
    rng2=np.random.default_rng(20261024); perm=rng2.permutation(len(cy)); rand=np.column_stack([cy[perm],cx[perm]])
    terms={}; masks={}
    for seed in (20,30):
        folds,_=hm.buffered_component_draw(gd,seed=seed); vis=folds[0]["visible"]; mk=folds[0]["masked_known"]; dv=distance_transform_edt(~vis)
        elig=cmask&foot&~mk&(dv>3.0)
        for arm,cand in (("cj88",rank),("null_rand",rand)):
            m=select(cand,elig,foot.shape); masks[(arm,seed)]=m
            for f in folds:
                _,t=evaluate_holdout.evaluate(m.astype(np.float32),f,foot); terms[arm]=t if arm not in terms else terms[arm]+t
        print("seed done",seed,time.time()-t0,flush=True)
    pooled=evaluate_holdout.pooled_summary(terms,draws=1000,seed=520810,candidate="cj88"); print(json.dumps(pooled["scores"],indent=1),flush=True)
    print("paired",pooled["paired_differences"],flush=True)
    cj=pooled["scores"]["cj88"]; beats = cj["dti"]>pooled["scores"]["null_rand"]["dti"] and pooled["paired_differences"]["null_rand"]["ci95"][0]>0
    eligF=cmask&foot&~cat&(dcat>3.0); final=select(rank,eligF,foot.shape)
    # uniqueness vs registry+downloads (sparse literal, report dense separately)
    mine=np.where(foot,final.astype(np.float32),0).astype(np.float32); rows=[]; worst_ov=(0,""); worst_rho=(0,"")
    files=sorted((ROOT/"data/registry").rglob("*.tif"))+sorted((ROOT/"docs/downloads").glob("*.tif"))
    for p in files:
        try:
            with rasterio.open(p) as ds: th=ds.read(1)
            if th.shape!=foot.shape: continue
            ov=float(uniqueness.dot_overlap(mine,th)); rho=uniqueness.surface_rho(mine,th,foot)["spearman_full_footprint"]
            dense=float(((th>0)&foot).sum()/foot.sum()); rows.append({"file":str(p.relative_to(ROOT)),"overlap3":round(ov,5),"rho":round(float(rho),5) if np.isfinite(rho) else None,"pos_frac":round(dense,4)})
            if dense<=0.5:
                if ov>worst_ov[0]: worst_ov=(ov,str(p.relative_to(ROOT)))
                if np.isfinite(rho) and abs(rho)>abs(worst_rho[0]): worst_rho=(float(rho),str(p.relative_to(ROOT)))
        except Exception as e: rows.append({"file":str(p.relative_to(ROOT)),"error":str(e)})
    sparse_ok=worst_ov[0]<=0.70 and abs(worst_rho[0])<=0.90
    pts=np.argwhere(final); d=cKDTree(pts).query(pts,k=2)[0][:,1]
    dvals=dcat[final]; share_gt25=float((dvals>25).mean())
    fingerprint_ok = share_gt25>=0.35
    ok_submit=bool(beats and sparse_ok and fingerprint_ok)
    short=sha(final.tobytes())[:10]; stem=f"gems88-cj88-crestjunction-37654dots-20261024-{short}-zeros" + ("" if ok_submit else "-DO-NOT-SUBMIT")
    out=ROOT/"docs/downloads"/f"{stem}.tif"
    note0=f"CJ88 crest junction/termination 37654d >=3.5px; HOLDOUT-DTI {cj['dti']:.4f}; UNSCORED"[:140]
    receipt=write_submission(out, np.where(foot,final.astype(np.float32),0.0), ROOT/"data/bridge/sample_submission.tif", foot, note=note0, name=stem[:140], catalogue=cat)
    # validator: reload
    with rasterio.open(out) as ds: a=ds.read(1); prof=(ds.crs,ds.shape,ds.transform,ds.count)
    with rasterio.open(ROOT/"data/bridge/sample_submission.tif") as ds: ref=(ds.crs,ds.shape,ds.transform,ds.count)
    valid=bool(np.isfinite(a[foot]).all() and a[foot].min()>=0 and a[foot].max()<=1 and set(np.unique(a[foot]))<= {0.0,1.0} and (a[~foot]==0).all() and prof==ref)
    zip_path=out.with_suffix(".zip")
    note=f"CJ88 crest junction/termination 37654d >=3.5px; HOLDOUT-DTI {cj['dti']:.4f} CI[{cj['ci95'][0]:.3f},{cj['ci95'][1]:.3f}] vs null; UNSCORED"[:140]
    card={"hypothesis":"Crest junctions/endpoints/stepovers of B19/3/18/15 composite crest host uncatalogued geothermal faults (Faulds&Hinz favourable settings)","mechanism":"skeletonize crest mask; rank crest px by crest*(0.35+exp(-d_junction/6)+0.7exp(-d_endpoint/6)); greedy >=3.5px, >3px catalogue collar, 37654 binary dots","named_non_fault_process":"unfaulted bajada/terrace/volcanic-flow crest junctions","holdout":{"label":"HOLDOUT-DTI","evaluator":"gems57-pooled-hide-v2 alpha0.2 beta0.8 300m triangular","cj88":cj,"null_rand":pooled["scores"]["null_rand"],"paired_vs_null":pooled["paired_differences"]["null_rand"],"canaries":canaries,"beats_null_ci":bool(beats)},"uniqueness":{"worst_sparse_overlap3":worst_ov,"worst_sparse_rho":worst_rho,"sparse_ok":sparse_ok,"rows":rows},"fingerprint":{"n":int(final.sum()),"share_gt25":share_gt25,"share_le3":float((dvals<=3).mean()),"median_dcat":float(np.median(dvals)),"nn_min":float(d.min()),"nn_median":float(np.median(d))},"validator":{"values_0_1_binary":valid,"crs_shape_transform_match":prof==ref,"no_nan_inside_footprint":bool(np.isfinite(a[foot]).all()),"zeros_outside":bool((a[~foot]==0).all())},"raster_sha256":sha(out.read_bytes()),"zip_sha256":sha(zip_path.read_bytes()),"submission_name":stem,"note":note,"note_len":len(note),"ok_to_download":True,"ok_to_submit":ok_submit,"verdict":"promote" if ok_submit else "negative","slots_spent":0}
    (ROOT/"docs/data/cj88_run_card.json").write_text(json.dumps(card,indent=1)); (ROOT/"run_card_cj88.json").write_text(json.dumps(card,indent=1))
    print(json.dumps({k:card[k] for k in ("holdout","uniqueness","fingerprint","validator","raster_sha256","ok_to_submit","verdict","submission_name","note")},indent=1)[:4000])
if __name__=="__main__": main()
