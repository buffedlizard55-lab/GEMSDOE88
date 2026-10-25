#!/usr/bin/env python3
"""Build the KDMC-88 production candidate GeoTIFF and run every automatic gate.

Pipeline
--------
1. Zero-catalogue feature stack (cached, :mod:`gems88.kdmc`).
2. Out-of-fold PU density ``rho``: the footprint is split into the same four
   label-blind quadrants the holdout uses and each quadrant is predicted by a
   model that never saw a single catalogue pixel inside it.  No in-sample flank
   memorisation is possible.
3. ``E = rho (*) k`` — the exact expected TP_w of an isolated dot.
4. Greedy maximum-weight packing at the holdout-selected minimum separation and
   dot density, over ``footprint & ~catalogue`` minus an optional collar.
5. Fail-closed serialisation through the **unmodified** shared writer
   ``vendor/gems57/submission_writer.py`` (all-finite float32 in [0,1], zeros
   outside the footprint, zero dots on mapped faults) + single-TIFF ZIP.
6. Registry uniqueness with the chance-corrected gate (IR-88-76) and a machine
   verdict written to ``registry/kdmc_gate.json`` and ``docs/status.json``.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

from gems57 import grid as g57grid, holdout as g57holdout, metric, submission_writer, uniqueness, validate  # noqa: E402
from gems88 import kdmc  # noqa: E402

from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

N_NEG = 400_000


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def rows_for(mask, lin):
    r = lin[mask]
    return r[r >= 0]


def predict_rows(model, mm, rows, chunk=250_000):
    out = np.empty(rows.size, np.float32)
    order = np.argsort(rows)
    srt = rows[order]
    for a in range(0, srt.size, chunk):
        blk = srt[a:a + chunk]
        out[order[a:a + chunk]] = model.predict_proba(
            np.asarray(mm[blk], np.float32))[:, 1].astype(np.float32)
    return out


def oof_density(grid, mm, lin, cache: Path | None = None) -> np.ndarray:
    """4-quadrant out-of-fold PU density over the whole footprint."""
    if cache is not None and cache.is_file():
        rho = np.load(cache)
        if rho.shape == grid.shape:
            log(f"reusing cached OOF density {cache}")
            return rho.astype(np.float32)
    quad = g57holdout.quadrant_ids(grid.footprint)
    rho = np.zeros(grid.shape, np.float32)
    near_cat = ndi.distance_transform_edt(~grid.catalogue) <= 3
    for q in range(4):
        test = (quad == q) & grid.footprint
        train = grid.footprint & ~test
        pos_rows = rows_for(grid.catalogue & train, lin)
        neg_pool = rows_for(train & ~near_cat, lin)
        rng = np.random.default_rng(88_000 + q)
        neg_rows = rng.choice(neg_pool, size=min(N_NEG, neg_pool.size), replace=False)
        rws = np.sort(np.concatenate([pos_rows, neg_rows]))
        y = np.isin(rws, pos_rows).astype(np.int8)
        log(f"  quadrant {g57holdout.FOLD_NAMES[q]}: fit {int(y.sum()):,}+ / {int((1 - y).sum()):,}- "
            f"-> predict {int(test.sum()):,} cells")
        model = HistGradientBoostingClassifier(
            max_iter=250, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=50,
            l2_regularization=1.0, early_stopping=False,
            class_weight={0: 1.0, 1: float((1 - y).sum()) / max(int(y.sum()), 1)},
            random_state=88_000 + q)
        model.fit(np.asarray(mm[rws], np.float32), y)
        rho[test] = predict_rows(model, mm, rows_for(test, lin))
        del model, rws, y
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache, rho)
    return rho


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sep", type=float, required=True, help="minimum dot separation in px")
    ap.add_argument("--density", type=float, required=True,
                    help="dots per allowed pixel, transferred from the holdout optimum")
    ap.add_argument("--collar-px", type=float, default=0.0,
                    help="exclude cells within this distance of a mapped fault")
    ap.add_argument("--name", required=True)
    ap.add_argument("--note", required=True)
    ap.add_argument("--outdir", default="releases")
    ap.add_argument("--gate-out", default="registry/kdmc_gate.json",
                    help="where to write the machine gate verdict (one file per candidate)")
    args = ap.parse_args()

    t0 = time.time()
    grid = g57grid.load_grid()
    with rasterio.open(ROOT / "data" / "bridge" / "sample_submission.tif") as ds:
        valid = np.isfinite(ds.read(1))
    assert np.array_equal(valid, grid.footprint)
    mm, names = kdmc.build_feature_stack(ROOT / "data", ROOT / "data" / "external",
                                         valid, ROOT / ".cache" / "kdmc")
    flat_valid = np.flatnonzero(valid.ravel())
    lin = np.full(valid.size, -1, np.int32)
    lin[flat_valid] = np.arange(flat_valid.size, dtype=np.int32)
    lin = lin.reshape(valid.shape)

    log("fitting 4-quadrant out-of-fold PU density")
    rho = oof_density(grid, mm, lin, cache=ROOT / ".cache" / "kdmc" / "rho_oof.npy")
    E = kdmc.expected_credit(rho)

    allowed = grid.footprint & ~grid.catalogue
    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    if args.collar_px > 0:
        allowed &= d_cat > args.collar_px
    n_target = int(round(args.density * allowed.sum()))
    log(f"allowed cells {int(allowed.sum()):,}; target dots {n_target:,} "
        f"(density {args.density:.6f}, separation {args.sep} px)")

    dots, rounds, converged = kdmc.allocate_separated(
        E, allowed, args.sep, -np.inf, max_rounds=400, return_diagnostics=True)
    if not converged:
        raise RuntimeError("greedy packing did not converge")
    idx = np.flatnonzero(dots.ravel())
    vals = E.ravel()[idx]
    order = idx[np.lexsort((idx, -vals))][:n_target]
    pred = np.zeros(grid.shape, np.float32)
    pred.ravel()[order] = 1.0
    n_dots = int(pred.sum())
    log(f"packed {int(dots.sum()):,} feasible cells in {rounds} rounds; emitting {n_dots:,}")

    # ---- geometry receipts ------------------------------------------------
    pk = kdmc.packing_efficiency(pred > 0, grid.footprint)
    pts = np.argwhere(pred > 0).astype(np.float64)
    from scipy.spatial import cKDTree
    nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    e_tot = float(E[pred > 0].sum())
    geometry = dict(
        n_dots=n_dots, min_nn_px=float(nn.min()), median_nn_px=float(np.median(nn)),
        frac_nn_lt_6px=float((nn < 6.0).mean()),
        packing_efficiency=pk["packing_efficiency"], credit_mass=pk["credit_mass"],
        halo_fraction_of_footprint=pk["halo_fraction"],
        min_distance_to_catalogue_px=float(d_cat[pred > 0].min()),
        frac_dots_within_3px_of_catalogue=float((d_cat[pred > 0] <= 3).mean()),
        frac_dots_beyond_1km_of_catalogue=float((d_cat[pred > 0] > 10).mean()),
        frac_dots_beyond_2p5km_of_catalogue=float((d_cat[pred > 0] > 25).mean()),
        model_expected_tp=e_tot, model_expected_credit_per_dot=e_tot / max(n_dots, 1),
        model_total_density_mass=float(rho[grid.footprint].sum()))
    log("geometry: " + json.dumps({k: round(v, 6) if isinstance(v, float) else v
                                   for k, v in geometry.items()}))

    # ---- write via the unmodified shared writer ---------------------------
    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    tif = outdir / f"{args.name}.tif"
    for p in (tif, tif.with_suffix(".zip"), tif.with_suffix(".json")):
        p.unlink(missing_ok=True)
    receipt = submission_writer.write_submission(
        tif, pred, ROOT / "data" / "bridge" / "sample_submission.tif", grid.footprint,
        note=args.note, name=args.name, catalogue=grid.catalogue,
        metadata=dict(lane="KDMC-88", separation_px=args.sep, density=args.density,
                      collar_px=args.collar_px, geometry=geometry,
                      feature_version=kdmc.FEATURE_VERSION, n_features=len(names)))
    log(f"wrote {tif} sha256={receipt['sha256']}")

    # ---- registry uniqueness (literal + chance-corrected) -----------------
    inv = json.loads((ROOT / "registry" / "inventory.json").read_text())
    summary = uniqueness.compare_array_to_registry(
        pred, inv, grid.footprint, file_sha256=receipt["sha256"])
    rows = summary["rows"] if isinstance(summary, dict) and "rows" in summary else summary
    v3 = uniqueness.binding_duplicate_decision_v3(rows)
    literal = uniqueness.binding_duplicate_decision(rows)

    local = validate.validate(tif, grid.footprint, grid.catalogue)
    gate = dict(
        evidence_class="AUTOMATED-GATE",
        generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        candidate=dict(name=args.name, note=args.note, note_chars=len(args.note),
                       tif=str(tif.relative_to(ROOT)), sha256=receipt["sha256"],
                       zip_sha256=receipt["zip_sha256"], bytes=receipt["bytes"]),
        format_validation=local,
        geometry=geometry,
        uniqueness_literal=literal,
        uniqueness_chance_corrected=v3,
        ok_to_download=bool(local["all_checks_passed"]),
        ok_to_submit=bool(local["all_checks_passed"] and not v3["duplicate"]),
        verdict=("promote" if local["all_checks_passed"] and not v3["duplicate"] else "negative"))
    gate_path = ROOT / args.gate_out
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps(gate, indent=2) + "\n")
    log(f"gate: ok_to_download={gate['ok_to_download']} ok_to_submit={gate['ok_to_submit']} "
        f"worst_excess={v3['worst_excess_overlap']} worst_rho={v3['worst_abs_spearman']}")
    log(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
