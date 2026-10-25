#!/usr/bin/env python3
"""Automated fail-closed review gates for archived H88-CON88.

IR-88-F55AFF34-01 withdrew its former clearance: equal-support overlap is a
diagnostic, not an exemption from the user's literal all-registry rule; the
pre-placement surface check was not recorded; and CON88 did not beat the
current HOLDOUT-DTI best.  Exit 0 only if every binding gate passes.
"""
from __future__ import annotations
import hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
from gems57 import evaluate_holdout, spatial
from gems57.uniqueness import dot_overlap, _near, equal_support_dots, DENSE_POSITIVE_THRESHOLD

CAND_GLOB = "gems88-con88-consensus-ridge-*-zeros-DO-NOT-SUBMIT.tif"
CURRENT_HOLDOUT_BEST = 0.205991

def load(p):
    with rasterio.open(p) as ds:
        return ds.read(1), ds

def topn_support(a, n, foot):
    """Equal-support dots for a dense raster: its n highest finite footprint pixels."""
    out = np.zeros(a.shape, bool)
    vals = np.where(foot & np.isfinite(a), a, -np.inf).ravel()
    idx = np.argpartition(vals, -n)[-n:]
    out.ravel()[idx] = True
    return out

def main():
    cand = sorted((ROOT / "docs/downloads").glob(CAND_GLOB))[-1]
    sample, sds = load(ROOT / "data/bridge/sample_submission.tif")
    foot = np.isfinite(sample)
    faults, _ = load(ROOT / "data/bridge/existing_faults.tif")
    cat = faults == 1
    dcat = distance_transform_edt(~cat)
    pred, cds = load(cand)
    dots = np.isfinite(pred) & (pred > 0)
    n = int(dots.sum())

    # G1 format (independent re-read, exact grid identity)
    g1 = dict(
        one_band=cds.count == 1,
        crs_match=str(cds.crs) == str(sds.crs),
        shape_match=(cds.height, cds.width) == (sds.height, sds.width),
        transform_match=tuple(cds.transform)[:6] == tuple(sds.transform)[:6],
        finite_everywhere=bool(np.isfinite(pred).all()),
        in_01=bool(pred.min() >= 0 and pred.max() <= 1),
        zero_outside_footprint=bool((pred[~foot] == 0).all()),
        zero_on_catalogue=bool((pred[cat] == 0).all()),
        min=float(pred.min()), max=float(pred.max()), n_dots=n,
    )
    zpath = cand.with_suffix(".zip")
    with zipfile.ZipFile(zpath) as z:
        g1["zip_single_tif_byte_identical"] = z.namelist() == [cand.name] and z.read(cand.name) == cand.read_bytes()
    g1_ok = all(v for k, v in g1.items() if isinstance(v, bool))

    # G2 uniqueness. Equal-support is retained as a diagnostic, while the
    # literal all-registry overlap and pre-placement surface tests are binding.
    consensus_path = ROOT / ".cache/con88_consensus.npy"
    ridge_path = ROOT / ".cache/con88_ridge.npy"
    cache_ok = consensus_path.is_file() and ridge_path.is_file()
    consensus = np.load(consensus_path) if cache_ok else None
    ridge = np.load(ridge_path) if cache_ok else None
    preplacement_surface = (0.6 * consensus + 0.4 * ridge) if cache_ok else None
    paths = []
    for d in ["data/registry", "data/registry/family_60gemsdoe", "docs/downloads",
              "docs/research-variants", "submissions", "releases"]:
        paths += sorted((ROOT / d).glob("*.tif"))
    cand_sha = hashlib.sha256(cand.read_bytes()).hexdigest()
    rows, seen = [], {cand_sha}  # skip the candidate's own copies (submissions/)
    rng = np.random.default_rng(88)
    fy, fx = np.nonzero(foot)
    sel = rng.choice(len(fy), min(300_000, len(fy)), replace=False)
    pred_sample_rank = rankdata(pred[fy[sel], fx[sel]])
    surface_sample_rank = (
        rankdata(preplacement_surface[fy[sel], fx[sel]]) if preplacement_surface is not None else None
    )
    for p in paths:
        if p.resolve() == cand.resolve():
            continue
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if sha in seen:
            continue
        seen.add(sha)
        a, _ = load(p)
        their_dots = np.isfinite(a) & (a > 0) & foot
        nd = int(their_dots.sum())
        if nd == 0:
            continue
        dense = nd > DENSE_POSITIVE_THRESHOLD
        support = topn_support(a, n, foot) if dense else their_dots
        ov = float(_near(support, 3.0)[dots].mean())
        # Spearman is measured on a deterministic footprint sample for both
        # the pre-placement continuous surface and final binary dots.
        their_rank = rankdata(a[fy[sel], fx[sel]])
        rho = float(np.corrcoef(pred_sample_rank, their_rank)[0, 1]) if np.ptp(their_rank) > 0 else 0.0
        surface_rho = (
            float(np.corrcoef(surface_sample_rank, their_rank)[0, 1])
            if surface_sample_rank is not None and np.ptp(surface_sample_rank) > 0 and np.ptp(their_rank) > 0
            else None
        )
        literal_ov = float(_near(their_dots, 3.0)[dots].mean()) if dense else ov
        rows.append(dict(file=str(p.relative_to(ROOT)), sha256=sha, their_dots=nd,
                         dense=bool(dense), overlap_equal_support=ov,
                         overlap_literal=literal_ov, spearman=rho,
                         preplacement_surface_spearman=surface_rho))
    worst_ov = max(rows, key=lambda r: r["overlap_equal_support"])
    worst_literal_ov = max(rows, key=lambda r: r["overlap_literal"])
    worst_rho = max(rows, key=lambda r: abs(r["spearman"]))
    surface_rows = [r for r in rows if r["preplacement_surface_spearman"] is not None]
    worst_surface_rho = max(surface_rows, key=lambda r: abs(r["preplacement_surface_spearman"]), default=None)
    equal_support_diagnostic_ok = (
        worst_ov["overlap_equal_support"] <= 0.70 and abs(worst_rho["spearman"]) <= 0.90
    )
    literal_overlap_ok = worst_literal_ov["overlap_literal"] <= 0.70
    surface_ok = bool(
        worst_surface_rho is not None
        and abs(worst_surface_rho["preplacement_surface_spearman"]) <= 0.90
    )
    g2_ok = bool(equal_support_diagnostic_ok and literal_overlap_ok and surface_ok)

    # G3 H33-parity fingerprint (thresholds from fleet forensics, research/h33-forensics)
    d = dcat[dots]
    from scipy.spatial import cKDTree
    pts = np.argwhere(dots).astype(float)
    nn_dist, _ = cKDTree(pts).query(pts, k=2)
    nn1 = nn_dist[:, 1]
    g3 = dict(share_gt25=float((d > 25).mean()), share_le3=float((d <= 3).mean()),
              median_dcat=float(np.median(d)),
              nn_spacing_min=float(nn1.min()), nn_spacing_median=float(np.median(nn1)),
              frac_nn_between_2_and_4=float(((nn1 >= 2) & (nn1 <= 4)).mean()))
    g3_ok = (g3["share_gt25"] >= 0.35 and g3["share_le3"] == 0.0 and g3["median_dcat"] >= 15.0
             and 30_000 <= n <= 45_000 and g3["nn_spacing_min"] >= 2.83 - 1e-9)

    # Holdout: fixed predictions on identical label-blind quadrant folds (shared evaluator)
    arms = {"con88": pred}
    for key, p in [("h33", "data/registry/h33_education.tif"),
                   ("bpwd_fixed_tif", "docs/downloads/gems88-bpwd88-baranov-worm-conduit-37654-20261025-b8543782-zeros-DO-NOT-SUBMIT.tif")]:
        a, _ = load(ROOT / p)
        arms[key] = np.where(np.isfinite(a), a, 0).astype(np.float64)
    terms = {k: None for k in arms}
    canary_pos, canary_neg = [], []
    if not cache_ok:
        raise RuntimeError("CON88 pre-placement surfaces are absent; cannot reproduce canary or surface gate")
    n_withheld = 0
    for fold in spatial.folds(cat, foot, buffer_px=80):
        f = dict(region=fold["region"], truth=fold["truth"], visible=fold["visible"],
                 masked_known=fold["visible"])
        n_withheld += int(fold["truth"].sum())
        for k, a in arms.items():
            _, t = evaluate_holdout.evaluate(a, f, foot, block_side=200)
            terms[k] = t if terms[k] is None else terms[k] + t
        # canary: surface AUC withheld positives vs region negatives (sampled)
        rng = np.random.default_rng(7 + fold["fold"])
        pos = np.argwhere(fold["truth"] & fold["region"])
        neg_all = np.argwhere(fold["region"] & ~cat & (dcat > 3))
        neg = neg_all[rng.choice(len(neg_all), min(len(neg_all), 20000), replace=False)]
        canary_pos.append(pos); canary_neg.append(neg)
    pooled = evaluate_holdout.pooled_summary(terms, draws=1000, seed=520810, candidate="con88")
    pos = np.vstack(canary_pos); neg = np.vstack(canary_neg)
    y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    canary = {}
    for nm, surf in [("consensus", consensus), ("ridge", ridge),
                     ("exp2_blend", 0.6 * consensus + 0.4 * ridge)]:
        s = np.r_[surf[pos[:, 0], pos[:, 1]], surf[neg[:, 0], neg[:, 1]]]
        auc = float(roc_auc_score(y, s))
        canary[nm] = dict(auc=auc, symmetric_auc=max(auc, 1 - auc))
    canary_ok = all(v["symmetric_auc"] <= 0.90 for v in canary.values())
    reemit = json.loads((ROOT / "registry/con88_collar_holdout.json").read_text())
    reemit_score = reemit["pooled"]["scores"]["collar3p0"]
    holdout_ok = bool(
        reemit_score["dti"] > CURRENT_HOLDOUT_BEST
        and reemit_score["ci95"][0] > CURRENT_HOLDOUT_BEST
    )

    out = dict(
        candidate=cand.name,
        sha256=hashlib.sha256(cand.read_bytes()).hexdigest(),
        G1_format=g1, G1_ok=bool(g1_ok),
        G2_uniqueness=dict(
            rasters_checked=len(rows),
            equal_support_diagnostic=dict(ok=bool(equal_support_diagnostic_ok), worst_overlap=worst_ov),
            literal_binding=dict(ok=bool(literal_overlap_ok), worst_overlap=worst_literal_ov),
            preplacement_surface=dict(ok=bool(surface_ok), worst_spearman=worst_surface_rho),
            worst_final_spearman=worst_rho,
            rule=("binding: literal >0 support against every raster plus pre-placement surface rho; "
                  "dense top-N equal-support is diagnostic only"),
            rows=sorted(rows, key=lambda r: -r["overlap_equal_support"])[:10],
        ),
        G2_ok=bool(g2_ok), G3_fingerprint=g3, G3_ok=bool(g3_ok),
        holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=evaluate_holdout.VERSION,
                     n_withheld_positives=n_withheld, pooled=pooled,
                     per_fold_reemission_collar3p0=reemit_score,
                     current_best=CURRENT_HOLDOUT_BEST,
                     beats_current_best=bool(holdout_ok),
                     caveat="fixed predictions on label-blind quadrant whole-component folds; "
                            "candidate collar used full-catalogue distance so holdout is conservative (underestimate)"),
        holdout_ok=bool(holdout_ok),
        leakage_canary=canary, canary_ok=bool(canary_ok),
    )
    out["ok_to_submit"] = bool(g1_ok and g2_ok and g3_ok and canary_ok and holdout_ok)
    (ROOT / "registry/con88_gates.json").write_text(json.dumps(out, indent=2, default=float) + "\n")
    print(json.dumps({k: out[k] for k in ["candidate", "sha256", "G1_ok", "G2_ok", "G3_ok", "canary_ok", "holdout_ok", "ok_to_submit"]}, indent=2))
    print("worst_overlap", worst_ov["file"], round(worst_ov["overlap_equal_support"], 4))
    print("worst_rho", worst_rho["file"], round(worst_rho["spearman"], 4))
    print("holdout scores", {k: v for k, v in pooled.get("scores", {}).items()})
    return 0 if out["ok_to_submit"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
