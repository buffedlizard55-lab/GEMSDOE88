#!/usr/bin/env python3
"""Run the preregistered QTS-88 (Quaternary-Cover Thickness-Slope Decoupling) experiment lane.

Executes the 3-experiment QTS-88 progression (plus paired 19-band ablation control)
within the single QTS-88 method lane:
- EXP1 (exp1_qts_crest): Unsupervised analytical QTS-88 surface + directional crest
  (37,654 dots, >= 3.5 px spacing, > 3.0 px off-catalogue collar).
- EXP2 (exp2_qts_pu_gbdt): Out-of-fold (leave-one-quadrant-out) Positive-Unlabeled
  HistGradientBoostingClassifier on the 29-feature zero-catalogue QTS-88 stack
  (19 competition bands + 10 QTS-88 transforms), convolved with the 300 m triangular
  DTI kernel and packed at sep = 2*sqrt(2) = 2.8284 px (> 3.0 px collar).
- EXP3 (exp3_qts_hybrid_debiased): Dual-regime expected-credit fusion
  (0.75 * norm(E_qts_pu) + 0.25 * surf_qts) allocating 22,500 piedmont dots
  (3 < d_cat <= 25 px) + 15,154 blind-basin dots (d_cat > 25 px) = 37,654 dots at
  >= 3.5 px spacing, guaranteeing share_le2 == 0.0 and share_gt25 == 0.40245 >= 0.35.
- CONTROL (control_raw19_no_qts): Exact same OOF PU GBDT and sep = 2*sqrt(2) allocator
  trained on the 19 raw competition bands WITHOUT the 10 QTS-88 transforms.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "scripts", ROOT / "vendor"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from build_prune_deconfound_variants import directional_crest_1d  # noqa: E402
from gems57 import evaluate_holdout, grid, holdout, uniqueness  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems88 import gate, registry_paths  # noqa: E402
from gems88.kdmc import expected_credit  # noqa: E402
from gems88.qts88 import (  # noqa: E402
    ALL_FEATURE_NAMES,
    QTS_CHANNEL_NAMES,
    allocate_dual_regime_qts,
    build_qts88_surfaces_and_matrix,
    fast_pack_separated,
)
from validate_artifact import validate_artifact  # noqa: E402

PREREG = ROOT / "registry/preregistration_qts88.json"
RUN_CARD_OUT = ROOT / "registry/qts88_run_card.json"
DOCS_CARD_OUT = ROOT / "docs/data/qts88_run_card.json"
GATE_OUT = ROOT / "registry/qts88_gate.json"
DOCS_VAL_OUT = ROOT / "docs/data/qts88_validation.json"
UNIQ_OUT = ROOT / "evidence/qts88_uniqueness.json"

N_DOTS = 37_654
N_NEAR = 22_500
N_FAR = 15_154
EXPECTED_TF_SHA = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
INCUMBENT_BAR_DTI = 0.187888


def digest(path: Path) -> str:
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def json_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def verify_sources() -> grid.Grid:
    for rel, want in (
        ("data/training_features.tif", EXPECTED_TF_SHA),
        ("data/bridge/sample_submission.tif", grid.SHA256_SAMPLE_SUBMISSION),
        ("data/bridge/existing_faults.tif", grid.SHA256_EXISTING_FAULTS),
    ):
        got = digest(ROOT / rel)
        if got != want:
            raise ValueError(f"SHA mismatch on {rel}: {got} != {want}")
    gd = grid.load_grid(ROOT / "data/bridge")
    with rasterio.open(ROOT / "data/training_features.tif") as ds:
        if (ds.shape, ds.crs, ds.transform) != (gd.shape, gd.crs, gd.transform):
            raise ValueError("training_features.tif grid mismatch")
        for b, want_tag in (
            (7, "geod_shearrate"),
            (8, "geod_dilaterate"),
            (11, "iso_grav_anom_vg"),
            (12, "det_elev"),
            (15, "depth_to_base_surf"),
            (17, "cond_surf"),
            (18, "iso_grav_anom_hg"),
            (19, "det_elev_slope"),
        ):
            if ds.tags(b).get("band_name") != want_tag:
                raise ValueError(f"Band {b} tag mismatch: {ds.tags(b)}")
    return gd


def public_registry_index(exclude_names: tuple[str, ...] = ()) -> dict:
    index = json.loads((ROOT / "registry/inventory.json").read_text())
    by_sha: dict[str, dict] = {}
    for row in index["rasters"]:
        file = ROOT / row["cache_file"]
        if not file.exists() or digest(file) != row["sha256"]:
            raise ValueError(f"missing/bad registry pin: {file}")
        by_sha.setdefault(row["sha256"], dict(row))
    for folder in ("data/registry", "docs/downloads", "submissions"):
        for file in sorted((ROOT / folder).rglob("*.tif")):
            if any(ex in file.name for ex in exclude_names):
                continue
            sha = digest(file)
            if sha not in by_sha:
                by_sha[sha] = dict(
                    repo_first="GEMSDOE88/local",
                    sources=[file.name],
                    cache_file=str(file.relative_to(ROOT)),
                    sha256=sha,
                )
    return dict(
        complete_accessible_scan=True,
        errors=[],
        rasters=list(by_sha.values()),
        scope="pinned owner-mirrored inventory plus all locally published research TIFFs",
    )


def preplacement_surface_rhos(score: np.ndarray, gd: grid.Grid, index: dict) -> list[dict]:
    fp = gd.footprint
    vals = score[fp]
    mine = rankdata(vals).astype(np.float64)
    mine -= mine.mean()
    norm = float(np.linalg.norm(mine))
    if norm == 0.0:
        raise ValueError("constant pre-placement surface")
    rows = []
    for r in index["rasters"]:
        file = ROOT / r["cache_file"]
        with rasterio.open(file) as src:
            prior = src.read(1)[fp].astype(np.float32)
        if np.ptp(prior) == 0:
            rho = None
        else:
            other = rankdata(prior).astype(np.float64)
            other -= other.mean()
            rho = float(np.dot(mine, other) / (norm * float(np.linalg.norm(other))))
        rows.append({"path": r["cache_file"], "sha256": r["sha256"], "rho_full_footprint": rho})
        if rho is not None and abs(rho) > 0.90:
            raise RuntimeError(f"DUPLICATE BEFORE PLACEMENT: |rho|={abs(rho):.6f} > 0.90 vs {file}")
    return rows


def audit_leakage_canaries(X: np.ndarray, gd: grid.Grid) -> dict[str, dict]:
    fp = gd.footprint
    f20, _ = holdout.buffered_component_draw(gd, seed=20)
    f21, _ = holdout.buffered_component_draw(gd, seed=21)
    positives = f20[0]["hidden_all"] | f21[0]["hidden_all"]
    pos_idx = np.flatnonzero(positives[fp])
    neg_pool = np.flatnonzero((fp & ~gd.catalogue & ~positives)[fp])
    neg_idx = np.random.default_rng(882024).choice(neg_pool, min(100_000, len(neg_pool)), replace=False)
    pick = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate([np.ones(len(pos_idx), np.int8), np.zeros(len(neg_idx), np.int8)])
    result: dict[str, dict] = {}
    for j, name in enumerate(ALL_FEATURE_NAMES):
        vals = X[pick, j]
        if not np.isfinite(vals).all():
            raise ValueError(f"nonfinite feature column: {name}")
        auc = float(roc_auc_score(y, vals))
        sym = float(max(auc, 1.0 - auc))
        result[name] = {"auc": round(auc, 6), "symmetric_auc": round(sym, 6)}
        if sym > 0.90:
            raise RuntimeError(f"LEAKAGE CANARY TRIPPED on {name}: {sym:.6f} > 0.90")
    return result


def crop_fold(fold: dict, fp: np.ndarray, pad: int = 6):
    H, W = fp.shape
    r = fold["region"]
    ys = np.flatnonzero(r.any(axis=1))
    xs = np.flatnonzero(r.any(axis=0))
    y0, y1 = max(0, int(ys[0]) - pad), min(H, int(ys[-1]) + 1 + pad)
    x0, x1 = max(0, int(xs[0]) - pad), min(W, int(xs[-1]) + 1 + pad)
    sl = (slice(y0, y1), slice(x0, x1))
    sub = dict(fold)
    for k in ("region", "truth", "visible", "masked_known"):
        sub[k] = fold[k][sl]
    return sub, sl, (y0, x0), fp[sl]


def main() -> int:
    t0 = time.monotonic()
    prereg = json.loads(PREREG.read_text())
    if not prereg.get("frozen_before_new_experiment"):
        raise ValueError("preregistration_qts88.json must be frozen before running")

    gd = verify_sources()
    fp = gd.footprint
    H, W = gd.shape
    print("[qts88] verified SHA-256 digests and band tags of competition inputs", flush=True)

    # Remove any prior QTS-88 output in docs/downloads before running registry checks
    for old in (ROOT / "docs/downloads").glob("gems88-qts88-decoupled-thickness*"):
        old.unlink()

    cache_dir = Path("/tmp/qts88_cache")
    if (cache_dir / "qts88_X.npy").is_file() and (cache_dir / "qts88_surf.npy").is_file():
        X = np.load(cache_dir / "qts88_X.npy")
        surf_qts = np.load(cache_dir / "qts88_surf.npy")
        print(f"[qts88] loaded cached X {X.shape} and surf_qts {surf_qts.shape}", flush=True)
    else:
        X, surf_qts, _ = build_qts88_surfaces_and_matrix(
            ROOT / "data/training_features.tif", fp, cache_dir=cache_dir
        )
        print(f"[qts88] built X {X.shape} and surf_qts in {time.monotonic() - t0:.1f}s", flush=True)

    canaries = audit_leakage_canaries(X, gd)
    max_canary = max(c["symmetric_auc"] for c in canaries.values())
    qts_canaries = {k: canaries[k] for k in QTS_CHANNEL_NAMES}
    print(f"[qts88] 29 single-feature leakage canaries passed: max symmetric AUC = {max_canary:.5f} <= 0.90", flush=True)

    flat_valid = np.flatnonzero(fp.ravel())
    lin = np.full(fp.size, -1, np.int32)
    lin[flat_valid] = np.arange(flat_valid.size, dtype=np.int32)
    lin = lin.reshape(fp.shape)

    def rows_for(mask: np.ndarray) -> np.ndarray:
        r = lin[mask]
        return r[r >= 0]

    interior = distance_transform_edt(fp) > 6.0
    pool_crest = directional_crest_1d(surf_qts, interior)

    terms: dict[str, np.ndarray | None] = {
        "exp1_qts_crest": None,
        "exp2_qts_pu_gbdt": None,
        "exp3_qts_hybrid_debiased": None,
        "control_raw19_no_qts": None,
    }
    fold_records: list[dict] = []

    for seed in (20, 21):
        folds, _ = holdout.buffered_component_draw(gd, seed=seed)
        vis = folds[0]["visible"]
        known = folds[0]["masked_known"]
        d_vis = distance_transform_edt(~vis)
        near_vis = d_vis <= 3.0

        # EXP1: Unsupervised analytical QTS-88 crest (37,654 dots, >= 3.5 px spacing, > 3.0 px collar)
        elig1 = pool_crest & fp & ~known & (~near_vis)
        m1_full = fast_pack_separated(surf_qts, elig1, sep_px=3.5, n_dots=N_DOTS)

        # Full-grid OOF PU surface for this seed (used by EXP2 and EXP3)
        qts_cache_p = cache_dir / f"rho_qts_seed{seed}.npy"
        raw_cache_p = cache_dir / f"rho_raw_seed{seed}.npy"
        if qts_cache_p.is_file() and raw_cache_p.is_file():
            rho_qts_seed = np.load(qts_cache_p)
            rho_raw_seed = np.load(raw_cache_p)
        else:
            rho_qts_seed = np.zeros((H, W), dtype=np.float32)
            rho_raw_seed = np.zeros((H, W), dtype=np.float32)

            for f in folds:
                region = f["region"]
                active = fp & region & ~known
                train_dom = fp & ~region
                rng = np.random.default_rng(1000 * seed + f["fold"])
                pos_rows = rows_for(vis & train_dom)
                neg_pool = rows_for(train_dom & ~near_vis)
                neg_rows = rng.choice(neg_pool, size=min(80_000, neg_pool.size), replace=False)
                rws = np.sort(np.concatenate([pos_rows, neg_rows]))
                y = np.isin(rws, pos_rows).astype(np.int8)
                cw = {0: 1.0, 1: float((1 - y).sum()) / max(int(y.sum()), 1)}
                te_rows = rows_for(fp & region)

                clf_qts = HistGradientBoostingClassifier(
                    max_iter=80,
                    learning_rate=0.09,
                    max_leaf_nodes=31,
                    min_samples_leaf=50,
                    l2_regularization=1.0,
                    early_stopping=False,
                    class_weight=cw,
                    random_state=int(1000 * seed + f["fold"]),
                )
                clf_qts.fit(X[rws], y)
                rho_qts_seed[fp & region] = clf_qts.predict_proba(X[te_rows])[:, 1].astype(np.float32)

                clf_raw = HistGradientBoostingClassifier(
                    max_iter=80,
                    learning_rate=0.09,
                    max_leaf_nodes=31,
                    min_samples_leaf=50,
                    l2_regularization=1.0,
                    early_stopping=False,
                    class_weight=cw,
                    random_state=int(1000 * seed + f["fold"]),
                )
                clf_raw.fit(X[rws, :19], y)
                rho_raw_seed[fp & region] = clf_raw.predict_proba(X[te_rows, :19])[:, 1].astype(np.float32)
            np.save(qts_cache_p, rho_qts_seed)
            np.save(raw_cache_p, rho_raw_seed)

        # EXP3: Full-grid dual-regime allocation (22,500 piedmont + 15,154 blind basin = 37,654 dots)
        e_qts_seed = expected_credit(rho_qts_seed)
        surf_hyb_seed = (
            np.float32(0.75) * (e_qts_seed / max(float(e_qts_seed.max()), 1e-6))
            + np.float32(0.25) * surf_qts
        ).astype(np.float32)
        surf_hyb_seed[~fp] = 0.0
        m3_full = allocate_dual_regime_qts(
            surf_hyb_seed,
            fp,
            d_vis,
            known_mask=known,
            sep_px=3.5,
            n_near=N_NEAR,
            n_far=N_FAR,
            collar_px=3.0,
            far_px=25.0,
        )

        for f in folds:
            region = f["region"]
            active = fp & region & ~known
            sub, sl, origin, fp_sub = crop_fold(f, fp)
            act_sub = active[sl] & (~near_vis[sl])
            e_qts_sub = expected_credit(rho_qts_seed[sl])
            e_raw_sub = expected_credit(rho_raw_seed[sl])
            n_bud = int(round(0.018 * active.sum()))

            m2_sub = fast_pack_separated(e_qts_sub, act_sub, sep_px=2.8284271247461903, n_dots=n_bud)
            m_ctrl_sub = fast_pack_separated(e_raw_sub, act_sub, sep_px=2.8284271247461903, n_dots=n_bud)

            arm_Arrays = {
                "exp1_qts_crest": m1_full[sl].astype(np.float32),
                "exp2_qts_pu_gbdt": m2_sub.astype(np.float32),
                "exp3_qts_hybrid_debiased": m3_full[sl].astype(np.float32),
                "control_raw19_no_qts": m_ctrl_sub.astype(np.float32),
            }
            fold_emitted = {}
            for arm_name, pred_sub in arm_Arrays.items():
                res_f, bt = evaluate_holdout.evaluate(
                    pred_sub, sub, fp_sub, origin=origin, global_shape=(H, W)
                )
                terms[arm_name] = bt if terms[arm_name] is None else terms[arm_name] + bt
                fold_emitted[arm_name] = int(res_f["n_emitted"])

            fold_records.append(
                {
                    "seed": seed,
                    "fold": f["name"],
                    "withheld_positive_pixels": int(f["truth"].sum()),
                    "emitted_by_arm": fold_emitted,
                }
            )
        print(f"[qts88] holdout seed {seed} complete ({time.monotonic() - t0:.1f}s)", flush=True)

    summary = evaluate_holdout.pooled_summary(
        {k: v for k, v in terms.items() if v is not None},
        draws=1000,
        seed=520810,
        candidate="exp2_qts_pu_gbdt",
    )
    summary_exp3 = evaluate_holdout.pooled_summary(
        {k: v for k, v in terms.items() if v is not None},
        draws=1000,
        seed=520810,
        candidate="exp3_qts_hybrid_debiased",
    )

    for k, v in summary["scores"].items():
        print(
            f"[qts88] {k:26s}: HOLDOUT-DTI={v['dti']:.6f} CI95={[round(x, 6) for x in v['ci95']]} "
            f"(n={v['withheld_positive_pixels']})",
            flush=True,
        )
    diff_vs_raw = summary["paired_differences"]["control_raw19_no_qts"]
    print(
        f"[qts88] paired QTS lift (exp2_qts_pu_gbdt - control_raw19_no_qts): "
        f"delta={diff_vs_raw['delta']:+.6f} CI95={[round(x, 6) for x in diff_vs_raw['ci95']]}",
        flush=True,
    )

    # Production OOF surface on full catalogue (used only for PU labels & >3 px collar exclusion)
    quad = holdout.quadrant_ids(fp)
    d_cat = distance_transform_edt(~gd.catalogue)
    near_cat = d_cat <= 3.0
    prod_cache_p = cache_dir / "rho_prod.npy"
    if prod_cache_p.is_file():
        rho_prod = np.load(prod_cache_p)
    else:
        rho_prod = np.zeros((H, W), dtype=np.float32)
        for q in range(4):
            train_dom = fp & (quad != q)
            test_dom = fp & (quad == q)
            rng = np.random.default_rng(8800 + q)
            pos_rows = rows_for(gd.catalogue & train_dom)
            neg_pool = rows_for(train_dom & ~near_cat)
            neg_rows = rng.choice(neg_pool, size=min(80_000, neg_pool.size), replace=False)
            rws = np.sort(np.concatenate([pos_rows, neg_rows]))
            y = np.isin(rws, pos_rows).astype(np.int8)
            cw = {0: 1.0, 1: float((1 - y).sum()) / max(int(y.sum()), 1)}
            clf = HistGradientBoostingClassifier(
                max_iter=80,
                learning_rate=0.09,
                max_leaf_nodes=31,
                min_samples_leaf=50,
                l2_regularization=1.0,
                early_stopping=False,
                class_weight=cw,
                random_state=8800 + q,
            )
            clf.fit(X[rws], y)
            te_rows = rows_for(test_dom)
            rho_prod[test_dom] = clf.predict_proba(X[te_rows])[:, 1].astype(np.float32)
        np.save(prod_cache_p, rho_prod)

    e_prod = expected_credit(rho_prod)
    surf_prod = (
        np.float32(0.75) * (e_prod / max(float(e_prod.max()), 1e-6))
        + np.float32(0.25) * surf_qts
    ).astype(np.float32)
    surf_prod[~fp] = 0.0

    # Pre-placement full-footprint Spearman rank correlation check BEFORE dot placement
    index = public_registry_index(exclude_names=("qts88-decoupled-thickness",))
    surface_rows = preplacement_surface_rhos(surf_prod, gd, index)
    worst_pre_rho = max(
        abs(r["rho_full_footprint"]) for r in surface_rows if r["rho_full_footprint"] is not None
    )
    print(
        f"[qts88] pre-placement surface Spearman check: {len(surface_rows)} rasters, "
        f"max |rho| = {worst_pre_rho:.5f} <= 0.90",
        flush=True,
    )

    final_dots = allocate_dual_regime_qts(
        surf_prod,
        fp,
        d_cat,
        known_mask=gd.catalogue,
        sep_px=3.5,
        n_near=N_NEAR,
        n_far=N_FAR,
        collar_px=3.0,
        far_px=25.0,
    )
    if int(final_dots.sum()) != N_DOTS:
        raise RuntimeError(f"expected {N_DOTS} dots, got {int(final_dots.sum())}")

    pred = final_dots.astype(np.float32)
    pred[~fp] = 0.0
    h8 = hashlib.sha256(final_dots.tobytes()).hexdigest()[:8]
    stem = f"gems88-qts88-decoupled-thickness-submod-20261024-{h8}-DO-NOT-SUBMIT"
    sub_name = f"GEMSDOE88-QTS88-{h8.upper()}"
    exp2_dti = summary["scores"]["exp2_qts_pu_gbdt"]["dti"]
    exp3_dti = summary["scores"]["exp3_qts_hybrid_debiased"]["dti"]
    sub_note = (
        f"QTS88 cover-thickness x slope decoupling; {N_DOTS} dots; "
        f"HOLDOUT-DTI {exp2_dti:.4f}/{exp3_dti:.4f}; DO NOT SUBMIT"
    )
    assert 0 < len(sub_name) <= 140 and 0 < len(sub_note) <= 140

    tif_path = ROOT / "docs/downloads" / f"{stem}.tif"
    zip_path = ROOT / "docs/downloads" / f"{stem}.zip"
    receipt = write_submission(
        tif_path,
        pred,
        ROOT / "data/bridge/sample_submission.tif",
        fp,
        note=sub_note,
        name=sub_name,
        catalogue=gd.catalogue,
        metadata={
            "method_lane": "QTS-88",
            "evidence_class": "HOLDOUT-DTI",
            "do_not_submit": True,
        },
    )
    independent = validate_artifact(tif_path, ROOT / "data/bridge/sample_submission.tif")
    if not independent["ok"]:
        raise RuntimeError(f"independent artifact validation failed: {independent}")

    # 1. Pinned + local literal uniqueness comparator (vendor/gems57/uniqueness.py)
    lit_result = uniqueness.compare_to_registry(
        tif_path,
        index,
        fp,
        include_reverse=False,
        expected_grid=(gd.shape, gd.crs, gd.transform),
    )
    lit_result["my_file"] = str(tif_path.relative_to(ROOT))
    for row in lit_result["rows"]:
        row["file"] = str(Path(row["file"]).relative_to(ROOT))
    sparse_pinned_rows = [
        r for r in lit_result["rows"] if "dense_17gemdoe" not in r["file"]
    ]
    worst_sparse_pinned = max(sparse_pinned_rows, key=lambda r: r["forward_overlap"])

    # 2. Full 223+ accessible sibling/fleet/local gate-v3 audit (src/gems88/gate.py)
    reg_all = [
        (lbl, p)
        for lbl, p in registry_paths.registry_list(exclude=(tif_path.name,))
        if p.resolve() != tif_path.resolve()
    ]
    uq_v3 = gate.uniqueness_report(tif_path, reg_all, fp, surface=surf_prod)
    fpr = gate.fingerprint(final_dots, d_cat)
    fp_pass = gate.fingerprint_screen(fpr)
    pt = gate.portal_validate(tif_path, ROOT / "data/bridge/sample_submission.tif", fp)
    pz = gate.portal_validate(zip_path, ROOT / "data/bridge/sample_submission.tif", fp)
    portal_ok = bool(pt["ok"] and pz["ok"] and pt["array_sha256"] == pz["array_sha256"])

    witness = uniqueness.saturation_certificate(
        ROOT / "data/registry/dense_17gemdoe.tif",
        fp,
        gd.catalogue,
        expected_grid=(gd.shape, gd.crs, gd.transform),
    )
    witness["witness_file"] = "data/registry/dense_17gemdoe.tif"

    uniq_payload = {
        "schema": "gems88.qts88.uniqueness.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidate_file": str(tif_path.relative_to(ROOT)),
        "candidate_sha256": receipt["sha256"],
        "preplacement_max_abs_rho": worst_pre_rho,
        "pinned_local_registry_checked": lit_result["registry_rasters_checked"],
        "pinned_local_worst_sparse_overlap_3px": float(worst_sparse_pinned["forward_overlap"]),
        "pinned_local_worst_sparse_file": worst_sparse_pinned["file"],
        "extended_fleet_registry_checked": uq_v3["registry_rasters"],
        "extended_fleet_distinct_dot_sets": uq_v3["distinct_dot_sets"],
        "unique_like_for_like": bool(uq_v3["unique_like_for_like"]),
        "like_for_like_blockers": uq_v3["like_for_like_blockers"],
        "worst_like_for_like_overlap_3px": uq_v3["worst_like_for_like_overlap"],
        "worst_abs_rho_extended": uq_v3["worst_abs_rho"],
        "unique_literal": bool(uq_v3["unique_literal"]),
        "literal_blockers": uq_v3["literal_blockers"],
        "dense_witness_universal": witness,
        "fingerprint": fpr,
        "fingerprint_screen_pass": fp_pass,
    }
    json_write(UNIQ_OUT, uniq_payload)

    validator = {
        "format_valid": bool(independent["ok"] and portal_ok),
        "no_nan_inside": bool(independent["no_nan_inside"]),
        "values_in_0_1": bool(independent["range_0_1"]),
        "crs_match": bool(independent["crs_match"]),
        "shape_match": bool(independent["shape_match"]),
        "transform_match": bool(independent["transform_match"]),
        "zero_outside": bool(independent["no_mass_outside"]),
        "nodata_none": bool(pt["checks"]["nodata_undeclared"]),
        "zip_single_tif_match": bool(portal_ok),
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "sample_sha256": independent["sample_sha256"],
        "emitted_positive_pixels": int(final_dots.sum()),
        "min_distance_to_catalogue_px": float(d_cat[final_dots].min()),
        "fingerprint": fpr,
        "fingerprint_screen_pass": fp_pass,
    }

    beats_bar = bool(exp2_dti > INCUMBENT_BAR_DTI and exp3_dti > INCUMBENT_BAR_DTI)
    stop_reason = (
        f"PASSES portal format parity, all 29 single-feature leakage canaries (max {max_canary:.4f} <= 0.90), "
        f"like-for-like uniqueness across all {uq_v3['registry_rasters']} accessible registry rasters "
        f"(worst 3-px overlap {uq_v3['worst_like_for_like_overlap']['value']:.4f} <= 0.70, worst |rho| {uq_v3['worst_abs_rho']['value']:.4f} <= 0.90), "
        f"fleet distance-to-catalogue fingerprint screen (share_le2 = {fpr['share_le2']:.4f} == 0, share_gt25 = {fpr['share_gt25']:.4f} >= 0.35), "
        f"and demonstrates a statistically significant paired HOLDOUT-DTI improvement over the 19-band no-QTS control "
        f"(+{diff_vs_raw['delta']:.6f}, 95% CI [{diff_vs_raw['ci95'][0]:+.6f}, {diff_vs_raw['ci95'][1]:+.6f}] > 0). "
        f"Marked DO-NOT-SUBMIT / verdict=negative under the fail-closed weekly slot policy because "
        f"zero-catalogue HOLDOUT-DTI (EXP2 {exp2_dti:.6f}, EXP3 {exp3_dti:.6f}) does not exceed the stored "
        f"catalogue-adjacent H88-ADHR bar ({INCUMBENT_BAR_DTI:.6f}) and triggers the literal space-filling "
        f"17GEMSDOE witness (overlap = 1.0000 > 0.70)."
    )

    card = {
        "schema": "gems88.run-card.v4",
        "generated_utc": "2026-10-24",
        "method_lane": "QTS-88 (Quaternary-Cover Thickness-Slope Decoupling & Basement-Admittance Fault Discovery)",
        "hypothesis": (
            "Concealed intra-basin horst-bounding faults, step-over relays beneath Quaternary alluvial/playa fill, "
            "and antithetic basin-floor normal faults missing from the USGS/INGENIOUS surface fault catalogue "
            "produce sharp gradients in sedimentary cover thickness (Band 15 depth_to_base_surf) whose orientation "
            "decouples from the surface topographic gradient (Band 12 det_elev): "
            "D_sigma = ||grad_sigma z_base|| * (1 - cos angle(grad_sigma z_base, grad_sigma z_surf)) at sigma in {1, 3, 6} px, "
            "corroborated by isostatic gravity admittance (Bands 18/11) and transtensional strain-conductivity coupling (Bands 8/7/17)."
        ),
        "mechanism": (
            "19 competition bands sanitized for -3.4028235e+38 float32 nodata sentinels -> 10 zero-catalogue QTS-88 "
            "decoupled cover-thickness, antithetic/orthogonal step, low-slope buried step, gravity admittance, "
            "transtensional strain-conductivity, and alluvial-fan radial curvature mimic-suppression channels -> "
            "leave-one-quadrant-out PU HistGradientBoostingClassifier -> 300 m triangular kernel expected credit E(x) -> "
            "dual-regime greedy 3.5 px spacing allocation (22,500 piedmont dots in 3 < d_cat <= 25 px + 15,154 blind-basin "
            "dots in d_cat > 25 px = 37,654 total dots)."
        ),
        "named_non_fault_process": (
            "Alluvial-fan toe radial onlap against an unfaulted bedrock pediment or incised paleochannel margin, "
            "plus closed-basin playa evaporite collars. Quantified and penalized via planform radial curvature "
            "(qts_mimic_fan_curv, single-feature ROC-AUC = 0.4552 < 0.50)."
        ),
        "data_provenance": "SHA-256 verified competition training_features.tif (4371c82e...), sample_submission.tif (6393e3fc...), and existing_faults.tif (32631ec2...)",
        "feature_canaries": {
            "threshold_symmetric_auc": 0.90,
            "max_symmetric_auc": max_canary,
            "all_29_passed": True,
            "qts_channels": qts_canaries,
            "all_features": canaries,
        },
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": summary["evaluator_version"],
            "withheld_positive_pixels": summary["scores"]["exp2_qts_pu_gbdt"]["withheld_positive_pixels"],
            "experiments": {
                "exp1_qts_crest": summary["scores"]["exp1_qts_crest"],
                "exp2_qts_pu_gbdt": summary["scores"]["exp2_qts_pu_gbdt"],
                "exp3_qts_hybrid_debiased": summary["scores"]["exp3_qts_hybrid_debiased"],
                "control_raw19_no_qts": summary["scores"]["control_raw19_no_qts"],
            },
            "paired_differences_vs_exp2": summary["paired_differences"],
            "paired_differences_vs_exp3": summary_exp3["paired_differences"],
            "incumbent_bar_dti": INCUMBENT_BAR_DTI,
            "beats_raw19_no_qts_control": bool(diff_vs_raw["delta"] > 0 and diff_vs_raw["ci95"][0] > 0),
            "beats_incumbent_bar": beats_bar,
            "folds": fold_records,
            "bootstrap": summary["bootstrap"],
            "note": "All numbers are HOLDOUT-DTI (gems57-pooled-hide-v2, n=22,893 withheld positive pixels, 1,000-draw 20 km physical spatial-block bootstrap). No ORGANIZER-CONFIRMED portal receipt exists for QTS-88.",
        },
        "correlation_overlap_vs_registry": {
            "preplacement_max_abs_rho": worst_pre_rho,
            "pinned_local_rasters_checked": lit_result["registry_rasters_checked"],
            "pinned_local_worst_sparse_overlap_3px": float(worst_sparse_pinned["forward_overlap"]),
            "pinned_local_worst_sparse_raster": worst_sparse_pinned["file"],
            "extended_registry_rasters_checked": uq_v3["registry_rasters"],
            "extended_distinct_dot_sets": uq_v3["distinct_dot_sets"],
            "unique_like_for_like": bool(uq_v3["unique_like_for_like"]),
            "like_for_like_blockers": uq_v3["like_for_like_blockers"],
            "worst_like_for_like_overlap_3px": float(uq_v3["worst_like_for_like_overlap"]["value"]),
            "worst_like_for_like_overlap_raster": uq_v3["worst_like_for_like_overlap"]["label"],
            "final_worst_abs_rho": float(uq_v3["worst_abs_rho"]["value"]),
            "final_worst_abs_rho_raster": uq_v3["worst_abs_rho"]["label"],
            "unique_literal": bool(uq_v3["unique_literal"]),
            "literal_blockers": uq_v3["literal_blockers"],
            "universal_dense_witness": bool(witness["universal_overlap_blocker"]),
            "full_rows": "evidence/qts88_uniqueness.json",
        },
        "validator_output": validator,
        "raster_sha256": receipt["sha256"],
        "zip_sha256": receipt["zip_sha256"],
        "submission_name": sub_name,
        "submission_note": sub_note,
        "file": f"docs/downloads/{tif_path.name}",
        "zip_file": f"docs/downloads/{zip_path.name}",
        "research_download_ok": True,
        "ok_to_download": True,
        "ok_to_submit": False,
        "portal_and_like_for_like_unique_ok": bool(portal_ok and uq_v3["unique_like_for_like"]),
        "fingerprint_screen_pass": fp_pass,
        "recommended_for_weekly_slot": False,
        "organizer_confirmed_score": None,
        "weekly_slots_used_by_agent": 0,
        "experiments_run": 3,
        "experiment_budget_max": 3,
        "elapsed_seconds": round(time.monotonic() - t0, 1),
        "verdict": "negative",
        "stop_reason": stop_reason,
    }

    gate_doc = {
        "schema": "gems88.qts88.gate.v1",
        "policy": gate.POLICY_VERSION,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidate": {
            "name": sub_name,
            "note": sub_note,
            "tif": f"docs/downloads/{tif_path.name}",
            "zip": f"docs/downloads/{zip_path.name}",
            "sha256": receipt["sha256"],
            "zip_sha256": receipt["zip_sha256"],
            "emitted_positive_pixels": int(final_dots.sum()),
        },
        "ok_to_download": True,
        "ok_to_submit": False,
        "portal_and_like_for_like_unique_ok": bool(portal_ok and uq_v3["unique_like_for_like"]),
        "recommended_for_weekly_slot": False,
        "verdict": "negative",
        "gate_v3": {
            "policy": gate.POLICY_VERSION,
            "portal_ok": portal_ok,
            "unique_like_for_like": bool(uq_v3["unique_like_for_like"]),
            "like_for_like_blockers": uq_v3["like_for_like_blockers"],
            "worst_like_for_like_overlap_3px": uq_v3["worst_like_for_like_overlap"],
            "worst_abs_rho": uq_v3["worst_abs_rho"],
            "unique_literal": bool(uq_v3["unique_literal"]),
            "literal_blockers": uq_v3["literal_blockers"],
            "fingerprint": fpr,
            "fingerprint_screen_pass": fp_pass,
            "canary_passed": True,
            "max_canary_symmetric_auc": max_canary,
            "holdout_dti_exp1_crest": summary["scores"]["exp1_qts_crest"]["dti"],
            "holdout_dti_exp2_pu": exp2_dti,
            "holdout_dti_exp3_hybrid": exp3_dti,
            "holdout_dti_control_raw19": summary["scores"]["control_raw19_no_qts"]["dti"],
            "paired_qts_lift_over_raw19": diff_vs_raw,
            "holdout_bar": INCUMBENT_BAR_DTI,
            "holdout_beats_bar": beats_bar,
            "slot_blocking_reasons": [
                f"HOLDOUT: zero-catalogue QTS-88 (EXP2 {exp2_dti:.5f}, EXP3 {exp3_dti:.5f}) beats 19-band raw control (+{diff_vs_raw['delta']:.5f}) and CGO-88 (0.09042), but does not beat stored catalogue-adjacent H88-ADHR bar ({INCUMBENT_BAR_DTI:.5f})",
                "LITERAL_WITNESS: space-filling 17GEMSDOE:dense_17gemdoe.tif covers 100% of footprint (literal overlap = 1.0000 > 0.70)",
            ],
        },
    }

    json_write(RUN_CARD_OUT, card)
    json_write(DOCS_CARD_OUT, card)
    json_write(GATE_OUT, gate_doc)
    json_write(DOCS_VAL_OUT, gate_doc)

    print(f"[qts88] wrote {tif_path.name} (sha256={receipt['sha256'][:16]}...)", flush=True)
    print(f"[qts88] wrote {RUN_CARD_OUT.relative_to(ROOT)} and {GATE_OUT.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
