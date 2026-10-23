#!/usr/bin/env python3
"""Build and validate controlled AXIS=RELIEF variants of parent R1 = PRUNEp3px.

Preregistered in ``registry/relief_preregistration.json`` (predictions fixed
before any variant PROXY was computed). Zero DrivenData/Dropbox contact.

Why R1 and not R0
-----------------
Brief v2 section 4.4 requires >=3 px from the catalogue for every non-PRUNE
axis. ``R0 = h33-h33-2-b2`` keeps 2,171 dots at ``2 < d_cat <= 3 px``, so a
RELIEF edit of R0 would inherit an unspendable collar (as the R0-based
MASS/CONCENTRATION families did). ``R1`` is the same 37,654 dots with the
collar removed at constant count (``min d_cat = 3.162 px``); SLOT_PLAN
Week 2 already scheduled RELIEF on R1. This script rebuilds R1 from the
pinned lineage and asserts BOTH published SHA-256 values (NaN ``6f7ae705...``,
zeros ``dc6f090d...``) before touching it; any mismatch aborts the build.
Nothing is approximated.

What RELIEF does
----------------
Relief class = footprint tercile of the supplied Band 12 ``det_elev``
(detrended elevation): T1 basin (<=q1), T2 piedmont/range-front (q1, q2],
T3 range (>q2). Each variant moves ``n_shift = 4,518`` dots (11.9987% of the
parent, inside the brief's RELIEF 10-15% range) from one tercile to another
at strictly fixed count (37,654):

  * donors:    parent dots in the SOURCE tercile with the lowest exact
               marginal DTI loss under the parent's own label-free
               corroboration field ``w`` (the ranking that built R1);
  * receivers: un-emitted H19-5 ridge pixels in the TARGET tercile with the
               highest exact marginal DTI gain under the same ``w``,
               restricted to the footprint and ``d_cat > 3.0 px``.

The untouched tercile keeps its exact parent count, the detector support
(H19-5) and the ranking field never change, and there is no RNG anywhere:
each variant differs from R1 ONLY in relief-tercile allocation.

Variants: ``rng2bas12`` (range->basin, primary), ``rng2pmt12``
(range->piedmont, range-front rival), ``bas2rng12`` (reverse SGMC-direction
bracket). MUST gates per Brief section 6; hide-and-recover (degenerate for
>3 px files), SGMC control, block CV and leakage canaries are REPORT ONLY.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import tempfile
import time

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, maximum_filter, minimum_filter
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score

import build_prune_variants as bp

ROOT = bp.ROOT
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
REPORT = ROOT / "evidence" / "relief_axis_report.json"
DIAGNOSTIC = ROOT / "registry" / "relief_diagnostic.json"

R1_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
R1_SHA_NAN = "6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9"
R1_SHA_ZEROS = "dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f"
N_DOTS = 37_654
N_SHIFT = int(round(0.12 * N_DOTS))  # 4,518 == 11.9987% of the parent
MIN_CATALOGUE_PX = 3.0

TERCILE_NAMES = ("T1_basin", "T2_piedmont", "T3_range")
# This module owns ONE of the two concurrently built RELIEF families (IR-88-39).
# A rerun replaces ONLY these values; the up/dn family lives in
# scripts/build_relief_variants.py and must survive untouched.
OUR_VALUES = {"rng2bas12", "rng2pmt12", "bas2rng12"}
# value, source class, target class, preregistered MODEL prediction vs R1
VARIANTS = [
    ("rng2bas12", 2, 0, "+0.008", "[-0.008,+0.024]"),
    ("rng2pmt12", 2, 1, "+0.002", "[-0.010,+0.014]"),
    ("bas2rng12", 0, 2, "-0.010", "[-0.026,+0.006]"),
]

REFERENCES = [
    {"claim": "Competition DTI metric/format (supplied by human brief; not fetched by agent)",
     "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"},
    {"claim": "Organizer: known faults masked pixel-exactly; new-fault truth may lie within 300 m of known traces (supplied by human brief; not fetched)",
     "url": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516"},
    {"claim": "Organizer: new fault includes newly mapped geometry of existing systems (supplied by human brief; not fetched)",
     "url": "https://community.drivendata.org/t/where-do-you-draw-the-line/11536"},
    {"claim": "USGS GeoDAWN Area 2 acquisition (400 m lines, 150-200 m drape) context (supplied by human brief; not fetched)",
     "url": "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7"},
    {"claim": "Faulds & Hinz 2015: structural settings (step-overs, intersections, terminations) of Great Basin geothermal systems on range-front fault systems; URL as already recorded in SLOT_PLAN.md",
     "url": "https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11072.pdf"},
    {"claim": "USGS SGMC source for the report-only off-catalogue control (manifest source_url)",
     "url": "https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d"},
]


# ---------------------------------------------------------------------------
# Relief terciles + allocation primitive (unit-tested in tests/test_relief_axis.py)
# ---------------------------------------------------------------------------


def read_clean_band(path: Path, idx: int, foot: np.ndarray) -> np.ndarray:
    """One supplied band cleaned exactly as build_prune_variants cleans bands."""
    with rasterio.open(path) as ds:
        arr = np.where(foot, np.nan_to_num(ds.read(idx), nan=0.0), 0.0).astype(np.float32)
    bad = (~np.isfinite(arr)) | (np.abs(arr) > 1e20)
    if np.any(bad & foot):
        arr[bad] = float(np.median(arr[foot & ~bad]))
    arr[~foot] = 0.0
    return arr


def tercile_classes(field: np.ndarray, foot: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Footprint terciles of ``field``: 0 (<=q1), 1 (q1,q2], 2 (>q2), -1 outside."""
    field = np.asarray(field, dtype=np.float64)
    foot = np.asarray(foot, dtype=bool)
    q1, q2 = (float(x) for x in np.quantile(field[foot], [1.0 / 3.0, 2.0 / 3.0]))
    if not q1 < q2:
        raise ValueError(f"degenerate tercile thresholds q1={q1} q2={q2}")
    cls = np.full(field.shape, -1, dtype=np.int8)
    cls[foot & (field <= q1)] = 0
    cls[foot & (field > q1) & (field <= q2)] = 1
    cls[foot & (field > q2)] = 2
    return cls, q1, q2


def relief_shift(
    parent_mask: np.ndarray,
    cls: np.ndarray,
    source: int,
    target: int,
    cand_base: np.ndarray,
    w: np.ndarray,
    n_shift: int,
) -> tuple[np.ndarray, dict]:
    """Move exactly ``n_shift`` dots source-tercile -> target-tercile at fixed count.

    Donors are the source-tercile parent dots of lowest exact marginal DTI
    loss; receivers are target-tercile ``cand_base`` pixels of highest exact
    marginal DTI gain (both under ``w``). ``cand_base`` must already encode
    footprint/collar/support restrictions. Deterministic (argmax ties break
    on candidate index inside the shared selectors).
    """
    parent = np.asarray(parent_mask, dtype=bool)
    if source == target:
        raise ValueError("source and target terciles must differ")
    before = [int((parent & (cls == k)).sum()) for k in range(3)]
    if before[source] < n_shift:
        raise ValueError(f"source tercile {source} holds {before[source]} dots < n_shift={n_shift}")
    pool_n = int((cand_base & (cls == target) & ~parent).sum())
    if pool_n < n_shift:
        raise ValueError(f"target tercile {target} candidate pool {pool_n} < n_shift={n_shift}")

    dropped = bp.select_exact_marginal_dti_drop(
        base_mask=parent,
        drop_pool_mask=parent & (cls == source),
        w=w,
        n_drop=n_shift,
    )
    out = bp.select_exact_marginal_dti_add(
        base_mask=dropped,
        cand_mask=cand_base & (cls == target),
        w=w,
        n_add=n_shift,
    )
    after = [int((out & (cls == k)).sum()) for k in range(3)]
    donors = parent & ~out
    receivers = out & ~parent
    assert int(out.sum()) == int(parent.sum()), "RELIEF must hold count fixed"
    assert int(donors.sum()) == n_shift and int(receivers.sum()) == n_shift
    assert int((donors & (cls == source)).sum()) == n_shift
    assert int((receivers & (cls == target)).sum()) == n_shift
    other = ({0, 1, 2} - {source, target}).pop()
    assert after[other] == before[other], "untouched tercile must keep its parent count"
    stats = {
        "source": TERCILE_NAMES[source],
        "target": TERCILE_NAMES[target],
        "n_shift": n_shift,
        "candidate_pool_target_not_parent": pool_n,
        "dots_before": dict(zip(TERCILE_NAMES, before)),
        "dots_after": dict(zip(TERCILE_NAMES, after)),
        "share_pct_before": {TERCILE_NAMES[k]: round(100.0 * before[k] / sum(before), 3) for k in range(3)},
        "share_pct_after": {TERCILE_NAMES[k]: round(100.0 * after[k] / sum(after), 3) for k in range(3)},
        "mean_w_donors": round(float(np.mean(w[donors])), 6) if donors.any() else 0.0,
        "mean_w_receivers": round(float(np.mean(w[receivers])), 6) if receivers.any() else 0.0,
        "mean_w_survivors": round(float(np.mean(w[out & parent])), 6),
        "w_weighted_dti_before": round(float(bp.weighted_expected_dti(parent, w)["dti"]), 6),
        "w_weighted_dti_after": round(float(bp.weighted_expected_dti(out, w)["dti"]), 6),
    }
    stats["w_weighted_dti_delta_MODEL"] = round(
        stats["w_weighted_dti_after"] - stats["w_weighted_dti_before"], 6
    )
    return out, stats


def saturation_stats(parent: np.ndarray, variant: np.ndarray, h19: np.ndarray,
                       cls: np.ndarray) -> dict:
    """Post-build kernel-saturation diagnostic (REPORT ONLY, computed after allocation).

    Receivers can only add DTI credit on strand length not already inside a
    survivor's 3 px kernel, while every donor whose nearest survivor ends up
    >3 px away leaves a coverage hole. The asymmetry between the two is the
    saturation cost of reallocating from an interstitial candidate pool.
    """
    survivors = parent & variant
    donors = parent & ~variant
    receivers = variant & ~parent
    tree = cKDTree(np.column_stack(np.nonzero(survivors)).astype(np.float64))
    d_rec, _ = tree.query(np.column_stack(np.nonzero(receivers)).astype(np.float64), k=1)
    d_don, _ = tree.query(np.column_stack(np.nonzero(donors)).astype(np.float64), k=1)

    def support_coverage(mask: np.ndarray) -> dict:
        d = distance_transform_edt(~mask)
        return {TERCILE_NAMES[k]: round(float(((d <= 3.0) & h19 & (cls == k)).sum()
                                               / max(int((h19 & (cls == k)).sum()), 1)), 4)
                for k in range(3)}

    return {
        "receiver_dist_to_survivor_px": {
            "median": round(float(np.median(d_rec)), 3),
            "frac_le_1p5": round(float((d_rec <= 1.5).mean()), 4),
            "frac_le_2p8": round(float((d_rec <= 2.8).mean()), 4),
            "frac_gt_3": round(float((d_rec > 3.0).mean()), 4),
        },
        "donor_dist_to_survivor_after_removal_px": {
            "median": round(float(np.median(d_don)), 3),
            "frac_gt_3": round(float((d_don > 3.0).mean()), 4),
            "frac_gt_5": round(float((d_don > 5.0).mean()), 4),
        },
        "h19_support_within_3px_parent": support_coverage(parent),
        "h19_support_within_3px_variant": support_coverage(variant),
    }


def nn_stats(mask: np.ndarray) -> dict:
    pts = np.column_stack(np.nonzero(mask)).astype(np.float64)
    d, _ = cKDTree(pts).query(pts, k=2)
    nn = d[:, 1]
    return {
        "min_nn_px": round(float(nn.min()), 4),
        "median_nn_px": round(float(np.median(nn)), 4),
        "frac_nn_lt_2p8": round(float((nn < 2.8).mean()), 4),
    }


# ---------------------------------------------------------------------------
# Parent R1 reconstruction with published-hash assertion
# ---------------------------------------------------------------------------


def reconstruct_r1(lin: dict, w: np.ndarray, verified: dict[str, Path], sample_path: Path) -> np.ndarray:
    """Rebuild R1 = PRUNEp3px from R0 exactly as the PRUNE session did; assert hashes."""
    foot, d_cat, h19, r0 = lin["foot"], lin["d_cat"], lin["h19_5"], lin["r0"]
    r0_gt3 = r0 & (d_cat > 3.0)
    n_rem = int(r0.sum() - r0_gt3.sum())
    assert n_rem == 2171, f"expected 2,171 collar dots, got {n_rem}"
    r1 = bp.select_exact_marginal_dti_add(
        base_mask=r0_gt3,
        cand_mask=h19 & ~r0_gt3 & (d_cat > 3.0),
        w=w,
        n_add=n_rem,
    )
    assert int(r1.sum()) == N_DOTS
    # Assert the published container hashes before R1 is used as a parent.
    with rasterio.open(sample_path) as tpl:
        base_prof = tpl.profile.copy()
    for nodata, expected, outside in ((np.nan, R1_SHA_NAN, np.nan), (None, R1_SHA_ZEROS, 0.0)):
        prof = base_prof.copy()
        prof.update(driver="GTiff", dtype="float32", count=1, compress="deflate",
                    predictor=3, zlevel=9, tiled=True, blockxsize=256,
                    blockysize=256, nodata=nodata)
        arr = np.where(foot, r1.astype(np.float32), outside).astype(np.float32)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "r1.tif"
            with rasterio.open(p, "w", **prof) as dst:
                dst.write(arr, 1)
            got = bp.sha256_file(p)
        if got != expected:
            raise RuntimeError(f"R1 rebuild SHA mismatch: got {got}, expected {expected}; STOP")
    return r1


# ---------------------------------------------------------------------------
# Relief-axis leakage canary for the stratifier itself (REPORT ONLY)
# ---------------------------------------------------------------------------


def relief_canary(det_elev: np.ndarray, cls: np.ndarray, foot: np.ndarray,
                  catalogue: np.ndarray) -> dict[str, float]:
    """Symmetric AUC of Band 12 / tercile class on whole-component hidden positives.

    Mirrors the canary design in build_prune_variants (folds seeds 20/30,
    first fold hidden positives, 100k footprint negatives, SEED=20261023).
    A stratifier is not a detector; this only checks the >0.90 trip line.
    """
    from gems57 import grid as grid_mod, holdout as holdout_mod  # vendor path set by bp import

    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)
    pos_mask = folds20[0]["hidden_all"] | folds30[0]["hidden_all"]
    del folds20, folds30, gd
    neg_pool = np.flatnonzero(foot & ~catalogue & ~pos_mask)
    rng = np.random.default_rng(bp.SEED)
    neg_sample = rng.choice(neg_pool, size=min(100_000, len(neg_pool)), replace=False)
    pos_idx = np.flatnonzero(pos_mask)
    idx = np.concatenate([pos_idx, neg_sample])
    y = np.concatenate([np.ones(len(pos_idx), np.int8), np.zeros(len(neg_sample), np.int8)])
    out: dict[str, float] = {}
    for name, field in (("det_elev_b12_raw", det_elev.ravel().astype(np.float64)),
                        ("det_elev_tercile_class", cls.ravel().astype(np.float64))):
        auc = float(roc_auc_score(y, field[idx]))
        sym = round(float(max(auc, 1.0 - auc)), 5)
        if sym > 0.90:
            raise RuntimeError(f"LEAKAGE CANARY TRIPPED on {name}: symmetric AUC {sym} > 0.90")
        out[name] = sym
    return out


# ---------------------------------------------------------------------------
# Pre-build relief diagnostic (feasibility of alternative relief fields)
# ---------------------------------------------------------------------------


def relief_diagnostic(verified, foot, catalogue, d_cat, h19, r0, r1, det_elev, cls) -> dict:
    from scipy.ndimage import binary_dilation

    sgmc_raw = rasterio.open(verified["sgmc_faults_control"]).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    cand = h19 & ~r1 & (d_cat > 3.0)
    masks = {"catalogue": catalogue, "sgmc_off_catalogue": sgmc_off, "R0": r0, "R1": r1,
             "candidate_pool_H19_not_R1_gt3px": cand}
    foot_n = [int((foot & (cls == k)).sum()) for k in range(3)]

    def table(classes):
        fn = [int((foot & (classes == k)).sum()) for k in range(3)]
        t = {}
        for name, m in masks.items():
            tot = int(m.sum())
            counts = [int((m & (classes == k)).sum()) for k in range(3)]
            t[name] = {
                "counts": counts,
                "share_pct": [round(100.0 * c / tot, 3) if tot else 0.0 for c in counts],
                "per_1k_footprint": [round(1000.0 * c / f, 3) if f else 0.0
                                     for c, f in zip(counts, fn)],
            }
        t["footprint_px"] = fn
        return t

    b19 = read_clean_band(verified["training_features"], 19, foot)
    cls19, s1, s2 = tercile_classes(b19, foot)
    del b19
    lr = (maximum_filter(det_elev, size=11, mode="nearest")
          - minimum_filter(det_elev, size=11, mode="nearest")).astype(np.float32)
    cls_lr, l1, l2 = tercile_classes(lr, foot)
    del lr
    return {
        "schema": "gems88.relief-diagnostic.v1",
        "evidence_label": "PROXY/MODEL diagnostics only; SGMC and catalogue distributions never gate and never select dots",
        "axis_field": "Band 12 det_elev footprint terciles (see relief_axis_report for exact thresholds)",
        "footprint_px": int(foot.sum()),
        "band12_det_elev_terciles": table(cls),
        "band19_det_elev_slope_terciles_NOT_USED": {"q1": s1, "q2": s2, **table(cls19)},
        "local_relief_11x11_range_terciles_NOT_USED": {"q1": l1, "q2": l2, **table(cls_lr)},
        "infeasibility_note": (
            "Low Band-19-slope and low local-relief terciles contain <1.1% of parent dots and "
            "only a few hundred H19-5 refill candidates, so a 10-15% RELIEF shift into them "
            "would require importing a new detector instead of reallocating the parent's mass."
        ),
        "marginal_return_ratio_catalogue_over_R1_dot_density_by_band12_tercile": {
            TERCILE_NAMES[k]: round(
                (int((catalogue & (cls == k)).sum()) / foot_n[k])
                / (int((r1 & (cls == k)).sum()) / foot_n[k]), 3)
            for k in range(3)
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    t0 = time.time()
    print("[1/7] Verifying SHA-256 manifest pins...")
    verified = bp.verify_manifest()
    print(f"      Verified {len(verified)}/{len(verified)} pinned inputs.")

    print("[2/7] Rebuilding R0 from lineage (byte-exact)...")
    lin = bp.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19, r0 = lin["h19_5"], lin["r0"]
    print(f"      R0 OK: {int(r0.sum()):,} dots | zeros={lin['rebuilt_zeros_sha256'][:12]}... "
          f"| nan={lin['rebuilt_nan_sha256'][:12]}...")

    print("[3/7] Building parent corroboration field w + canaries...")
    w, canaries = bp.build_physical_field_and_canaries(verified, foot, catalogue, h19)
    print(f"      Canaries PASS ({len(canaries)} channels; max sym AUC = {max(canaries.values()):.5f})")

    print("[4/7] Reconstructing parent R1 and asserting published SHA-256 (both twins)...")
    r1 = reconstruct_r1(lin, w, verified, verified["sample_submission"])
    print(f"      R1 OK: {int(r1.sum()):,} dots, min d_cat = {d_cat[r1].min():.4f} px, hashes match.")

    print("[5/7] Relief diagnostic + terciles + stratifier canary...")
    det_elev = read_clean_band(verified["training_features"], 12, foot)
    cls, q1, q2 = tercile_classes(det_elev, foot)
    relief_canaries = relief_canary(det_elev, cls, foot, catalogue)
    diag = relief_diagnostic(verified, foot, catalogue, d_cat, h19, r0, r1, det_elev, cls)
    DIAGNOSTIC.write_text(json.dumps(diag, indent=2) + "\n")
    print(f"      B12 terciles q1={q1:.4f} m, q2={q2:.4f} m | relief canaries {relief_canaries}")
    cand_base = h19 & foot & (d_cat > 3.0)

    # Idempotent rerun: replace ONLY this (bracket) family's ledger rows/files/cards.
    ledger_rows: list[dict[str, str]] = []
    fieldnames: list[str] = []
    header_line = ""
    raw_kept: list[str] = []
    existing_shas: set[str] = {bp.PARENT_SHA_ZEROS, bp.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS}
    if LEDGER.is_file():
        with LEDGER.open("r", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            all_rows = list(reader)
        for row in all_rows:
            if row.get("axis") == "RELIEF" and row.get("parent") == R1_ID and row.get("value") in OUR_VALUES:
                continue
            ledger_rows.append(row)
            for k in ("sha256", "sha256_zeros"):
                if row.get(k):
                    existing_shas.add(row[k])
        raw_lines = LEDGER.read_text().splitlines()
        header_line = raw_lines[0] if raw_lines else ""
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if len(parsed) > 3 and parsed[2] == "RELIEF" and parsed[1] == R1_ID and parsed[3] in OUR_VALUES:
                continue
            raw_kept.append(line)
    for _v in OUR_VALUES:
        for stale in RELEASES.glob(f"{R1_ID}-RELIEF{_v}-*"):
            stale.unlink()
    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    cards = {k: v for k, v in cards.items()
             if not any(k.startswith(f"{R1_ID}-RELIEF{_v}-") for _v in OUR_VALUES)}

    print("[6/7] Allocating 3 RELIEF variants (12% each, count fixed)...")
    arms: dict[str, np.ndarray] = {bp.PARENT_ID: r0, R1_ID: r1}
    built = []
    parent_nn = nn_stats(r1)
    notes = {
        "rng2bas12": "R1(6f7ae705); RELIEF range->basin 12% (4518) B12 terciles, 37654, >3px; pred +0.008 MODEL vs R1",
        "rng2pmt12": "R1(6f7ae705); RELIEF range->piedmont 12% (4518) B12 terciles, 37654, >3px; pred +0.002 MODEL vs R1",
        "bas2rng12": "R1(6f7ae705); RELIEF basin->range 12% (4518) B12 terciles, 37654, >3px; pred -0.010 MODEL vs R1",
    }
    ranking_basis = (
        "Exact marginal DTI under parent R1 corroboration field w: donors = lowest-loss source-tercile "
        "dots; receivers = highest-gain H19-5 target-tercile pixels at d_cat>3 px (Band 12 terciles)"
    )
    for value, source, target, pred, pred_range in VARIANTS:
        mask, stats = relief_shift(r1, cls, source, target, cand_base, w, N_SHIFT)
        stats["nn_parent_R1"] = parent_nn
        stats["nn"] = nn_stats(mask)
        rec = bp.write_and_verify_variant(
            mask=mask, foot=foot, catalogue=catalogue,
            sample_path=verified["sample_submission"], releases_dir=RELEASES,
            parent_mask=r1, axis="RELIEF", value=value,
            note_template=notes[value], existing_shas=existing_shas,
            parent_id=R1_ID, parent_sha_zeros=R1_SHA_ZEROS, parent_sha_nan=R1_SHA_NAN,
            date=bp.FIXED_DATE, min_catalogue_px=MIN_CATALOGUE_PX,
        )
        existing_shas.update({rec["sha256"], rec["sha256_zeros"]})
        rec["relief_statistics"] = stats
        rec["relief_terciles"] = {
            "field": "training_features.tif Band 12 det_elev",
            "q1_footprint_tercile": q1, "q2_footprint_tercile": q2,
            "classes": "T1_basin <=q1; T2_piedmont (q1,q2]; T3_range >q2",
            "preregistration": "registry/relief_preregistration.json",
        }
        rec["parent_rebuild_verified"] = {"R0_sha256_zeros": lin["rebuilt_zeros_sha256"],
                                           "R0_sha256_nan": lin["rebuilt_nan_sha256"],
                                           "R1_sha256_nan": R1_SHA_NAN, "R1_sha256_zeros": R1_SHA_ZEROS}
        rec["leakage_canaries"] = {"passed": True,
                                    "max_symmetric_auc": max(max(canaries.values()),
                                                             max(relief_canaries.values())),
                                    "channels": canaries, "relief_stratifier": relief_canaries}
        rec["predicted_change"] = f"MODEL:{pred} vs parent R1 (live, preregistered)"
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        cards[rec["id"]] = mechanism_card(value, stats, pred, pred_range, q1, q2)
        arms[rec["id"]] = mask
        built.append((rec, stats, pred, pred_range))
        print(f"      {value}: {stats['source']}->{stats['target']} n_shift={N_SHIFT} "
              f"wDTI delta={stats['w_weighted_dti_delta_MODEL']:+.6f} -> {rec['id']}")

    print("[7/7] REPORT-ONLY diagnostics (holdout [degenerate >3px], SGMC, block CV)...")
    eval_report = bp.evaluate_report_only_instruments(
        arms=arms, foot=foot, catalogue=catalogue, sgmc_path=verified["sgmc_faults_control"])
    r1_sgmc = eval_report[R1_ID]["sgmc_control"]["dti"]
    descriptions = {
        "rng2bas12": "Move 4518 dots (12.00%) range T3->basin T1 (Band 12 det_elev terciles) at fixed 37654, d_cat>3 px, exact-marginal donor/receiver ranking under parent field w.",
        "rng2pmt12": "Move 4518 dots (12.00%) range T3->piedmont T2 (Band 12 det_elev terciles) at fixed 37654, d_cat>3 px, exact-marginal donor/receiver ranking under parent field w.",
        "bas2rng12": "Reverse bracket: move 4518 dots (12.00%) basin T1->range T3 (Band 12 det_elev terciles) at fixed 37654, d_cat>3 px, exact-marginal donor/receiver ranking under parent field w.",
    }
    recommendations = {
        "rng2bas12": ("HOLD-CONDITIONAL: preregistered MODEL +0.008 vs R1 stands as the experiment prediction, "
                      "but post-build w-MODEL and SGMC PROXY both move against it and the saturation diagnostic "
                      "shows basin receivers mostly thicken already-covered strands. Spend a live slot only as a "
                      "deliberate falsification experiment (a gain despite saturation would strongly support the "
                      "basin hypothesis); not an expected-score pick ahead of R1."),
        "rng2pmt12": ("HOLD-CONDITIONAL / range-front bracket: same saturation caveat as rng2bas12. Only useful "
                      "live after an rng2bas12 receipt separates basin-receiver waste from range-donor value."),
        "bas2rng12": ("HOLD / reverse falsification bracket: loses least on both report-only instruments, "
                      "consistent with partial offset by the bedrock-biased SGMC population, but still below R1 "
                      "on both. Spend only if the human wants the relief direction closed with receipts."),
    }
    for rec, stats, pred, pred_range in built:
        d = eval_report[rec["id"]]
        d = dict(d)
        d["sgmc_delta_vs_R1_PROXY"] = round(d["sgmc_control"]["dti"] - r1_sgmc, 6)
        d["holdout_note"] = ("Catalogue hide-and-recover is degenerate (0.0) for every >3 px file: "
                             "kernel R=3 px can earn no credit on hidden catalogue pixels (IR-88-20). "
                             "Reported for completeness, cannot rank R1 descendants.")
        rec["report_only_diagnostics"] = d
        sat = saturation_stats(r1, arms[rec["id"]], h19, cls)
        rec["relief_statistics"]["post_build_saturation_REPORT_ONLY"] = sat
        cards[rec["id"]]["post_build_report_only"] = (
            f"A-priori preregistered prediction above is unchanged. Measured after build (REPORT ONLY, "
            f"never gates): parent-field w-weighted DTI delta {stats['w_weighted_dti_delta_MODEL']:+.6f} MODEL; "
            f"blind SGMC {d['sgmc_control']['dti']:.6f} PROXY ({d['sgmc_delta_vs_R1_PROXY']:+.6f} vs R1). "
            f"Saturation diagnostic: {sat['receiver_dist_to_survivor_px']['frac_le_2p8']:.1%} of receivers land "
            f"<=2.8 px from a survivor (median {sat['receiver_dist_to_survivor_px']['median']:.2f} px) while "
            f"{sat['donor_dist_to_survivor_after_removal_px']['frac_gt_3']:.1%} of donor sites end >3 px from "
            f"the nearest survivor; H19-5 support within-3px coverage by tercile moves parent "
            f"{sat['h19_support_within_3px_parent']} -> variant {sat['h19_support_within_3px_variant']}. "
            f"A live loss therefore cannot cleanly falsify the relief direction (it may reflect receiver "
            f"saturation), whereas a live gain >=+0.01 despite saturation would be strong support."
        )
        rec["parent_reference_diagnostics"] = eval_report[R1_ID]
        rec["grandparent_reference_diagnostics"] = eval_report[bp.PARENT_ID]
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        ledger_rows.append({
            "id": rec["id"], "parent": R1_ID, "axis": "RELIEF", "value": rec["value"],
            "n_dots": str(rec["n_dots"]),
            "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
            "sha256": rec["sha256"], "sha256_zeros": rec["sha256_zeros"], "status": "BUILT",
            "predicted_change": f"MODEL:{pred}", "predicted_range": pred_range,
            "ranking_basis": ranking_basis, "receipt_score": "", "receipt_date": "",
            "description": descriptions[rec["value"]],
            "recommendation": (f"{recommendations[rec['value']]} "
                               f"SGMC={d['sgmc_control']['dti']:.6f} PROXY (delta vs R1 {d['sgmc_delta_vs_R1_PROXY']:+.6f}); "
                               f"w-weighted DTI delta {stats['w_weighted_dti_delta_MODEL']:+.6f} MODEL."),
        })

    if fieldnames:
        new_rows = [r for r in ledger_rows if r.get("axis") == "RELIEF"
                    and r.get("parent") == R1_ID and r.get("value") in OUR_VALUES]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        for row in new_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
        with LEDGER.open("w", newline="") as fh:
            fh.write(header_line + "\n")
            for line in raw_kept:
                fh.write(line + "\n")
            body = buf.getvalue().rstrip("\n")
            if body:
                fh.write(body + "\n")
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")

    report = {
        "session_date": "2026-10-23",
        "axis": "RELIEF",
        "preregistration": "registry/relief_preregistration.json",
        "diagnostic": "registry/relief_diagnostic.json",
        "git_sha": bp.git_sha(),
        "seed": bp.SEED,
        "build_script_sha256": bp.sha256_file(Path(__file__).resolve()),
        "elapsed_seconds": round(time.time() - t0, 2),
        "parent_R1": {
            "id": R1_ID, "n_dots": N_DOTS, "sha256_nan": R1_SHA_NAN, "sha256_zeros": R1_SHA_ZEROS,
            "min_d_cat_px": round(float(d_cat[r1].min()), 4), "nn": parent_nn,
            "relief_share_pct": {TERCILE_NAMES[k]: round(100.0 * int((r1 & (cls == k)).sum()) / N_DOTS, 3)
                                 for k in range(3)},
            "diagnostics": eval_report[R1_ID],
        },
        "grandparent_R0": {
            "id": bp.PARENT_ID,
            "rebuilt_zeros_sha256": lin["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lin["rebuilt_nan_sha256"],
            "diagnostics": eval_report[bp.PARENT_ID],
        },
        "relief_terciles": {"field": "Band 12 det_elev", "q1": q1, "q2": q2,
                            "classes": "T1_basin <=q1; T2_piedmont (q1,q2]; T3_range >q2; -1 outside footprint"},
        "n_shift": N_SHIFT,
        "leakage_canaries": {"passed": True,
                             "max_symmetric_auc": max(max(canaries.values()), max(relief_canaries.values())),
                             "channels": canaries, "relief_stratifier": relief_canaries},
        "variants": [dict(r) for r, _s, _p, _pr in built],
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    print("\nRELIEF SUMMARY (predictions MODEL vs R1; proxies never scores)")
    for rec, stats, pred, _pr in built:
        d = rec["report_only_diagnostics"]
        print(f"  {rec['value']:10s} pred={pred}  wDTI={stats['w_weighted_dti_delta_MODEL']:+.6f} MODEL  "
              f"SGMC={d['sgmc_control']['dti']:.6f} ({d['sgmc_delta_vs_R1_PROXY']:+.6f} vs R1) PROXY  "
              f"CV12km={d['block_density_cv']['cv_12km_120px_interior']:.4f}  -> {rec['id']}")
    return 0


def mechanism_card(value: str, stats: dict, pred: str, pred_range: str, q1: float, q2: float) -> dict:
    sb, sa = stats["share_pct_before"], stats["share_pct_after"]
    common = (f"Count fixed at 37,654 so DTI changes only through kernel credit T and self-credit M "
              f"(DTI = T/(0.2T+0.2(S-M)+0.8|G|), S constant). Donors are the 4,518 source-tercile dots "
              f"whose removal loses least exact marginal DTI under the parent field w; receivers are the "
              f"4,518 target-tercile H19-5 pixels gaining most, all at d_cat>3 px. Terciles are footprint "
              f"quantiles of Band 12 det_elev (q1={q1:.1f} m, q2={q2:.1f} m). "
              f"Shares basin/piedmont/range move {sb['T1_basin']:.1f}/{sb['T2_piedmont']:.1f}/{sb['T3_range']:.1f}% "
              f"-> {sa['T1_basin']:.1f}/{sa['T2_piedmont']:.1f}/{sa['T3_range']:.1f}%.")
    cards = {
        "rng2bas12": {
            "hypothesis": "For a structural geologist: the incumbent spends its mass like a bedrock map. It holds 37.8% of dots in detrended-elevation highs (range interiors and crests, where bedrock is exposed and the USGS/INGENIOUS catalogue is most complete) but only 20.4% in detrended lows (basins and lower piedmonts), where the catalogue itself puts 30.4% of fault pixels on the same one-third of the area. Catalogue fault density per 1,000 footprint pixels is nearly equal in basin and range (10.8 vs 10.3), yet R1 dot density is 4.5 vs 8.3, so the marginal kernel return on the next basin dot is roughly twice that on the next range dot. New faults - including newly mapped geometry of known systems - should therefore be relatively enriched in the alluviated basin/piedmont population, where scarps are buried or degraded and pre-GeoDAWN mapping was poorest.",
            "mechanism": common + " Range-front normal faults throw basin fill against bedrock; their surface and shallow traces run along piedmonts and basin margins (detrended lows/mids), and intra-basin growth faults never reach exposed bedrock. Moving the weakest range dots basinward raises expected T per dot because basin receiver pixels sit on the parent's own highest-gain H19-5 strands in terrain the parent under-samples relative to fault density, while range donors are chosen where neighbouring dots already cover the same w-weighted strand.",
            "non_fault_mimic": "Alluvial-fan channel networks, fan-head trenches, playa and Pleistocene Lake Lahontan shoreline benches, and buried lithologic contacts in the basin fill can all generate linear H19-5 ridge/valley-skeleton detections in detrended lows with no brittle fault throw.",
            "predicted_sign_size": f"MODEL predicted live delta {pred} vs parent R1 (range {pred_range}, preregistered in registry/relief_preregistration.json before any PROXY was computed; |delta|<0.01 live is no evidence). Parent-field w-weighted DTI delta and the bedrock-biased SGMC PROXY delta are recorded separately in the release receipt and are expected to understate/oppose this prediction.",
            "falsifier": "A live RECEIPT <= R1-0.01 falsifies basinward reallocation at 12% dose: either basin H19-5 receivers are dominantly fan/shoreline mimics or the new-fault population is bedrock-range faulting (then rng2pmt12 and ultimately bas2rng12 bracket the truth). A RECEIPT >= R1+0.01 confirms the direction and licenses a dose/proportional-allocation follow-up.",
            "references": REFERENCES,
        },
        "rng2pmt12": {
            "hypothesis": "For a structural geologist: if the geothermal-relevant new faults are concentrated where the catalogue fault density per unit area is highest - the piedmont/range-front tercile (14.4 fault pixels per 1,000 footprint pixels, vs 10.8 basin and 10.3 range), i.e. along the range-front fault systems whose step-overs, intersections and terminations host Great Basin geothermal systems (Faulds & Hinz 2015) - then feeding range-interior dots into the piedmont tercile should win even though R1 already holds the piedmont near its catalogue share (41.8% of dots vs 40.6% of catalogue pixels).",
            "mechanism": common + " Piedmont receivers are the parent's highest-gain un-emitted H19-5 strands in the detrended mid-band: range-front scarps, relay ramps between en echelon segments, and faulted fan surfaces at the bedrock/alluvium transition. At fixed S the gain must come from higher T and M per moved dot; the question this arm answers is whether absolute fault density (piedmont) beats marginal under-sampling (basin).",
            "non_fault_mimic": "Alluvial-fan terrace risers, the erosional bases of triangular facets, and pluvial shoreline benches concentrated at the piedmont break can imitate range-front scarps in detrended mid elevations without active faulting.",
            "predicted_sign_size": f"MODEL predicted live delta {pred} vs parent R1 (range {pred_range}, preregistered; |delta|<0.01 live is no evidence). Deliberately weaker than rng2bas12 because the parent already allocates the piedmont at its catalogue share.",
            "falsifier": "If rng2bas12 loses live (>=0.01 below R1) but rng2pmt12 wins (>=0.01 above R1), basin receivers are the problem, not range donors, and the axis optimum is the range front. If both lose, range-interior dots were load-bearing and RELIEF should close toward the ranges.",
            "references": REFERENCES,
        },
        "bas2rng12": {
            "hypothesis": "Reverse bracket, built to be proven wrong under the primary hypothesis: if the hidden new-fault population resembles a state bedrock geologic-map compilation (the USGS SGMC off-catalogue control is 63.6% range-tercile pixels at 23.2 per 1,000 footprint pixels, vs 4.1 in the basin tercile), then mass should move INTO the ranges, where unmapped intra-range and bedrock faults would dominate and basin dots are mostly spent on fan drainage lineaments.",
            "mechanism": common + " This arm starves the basin tercile to single-digit dot share and loads the range tercile to about half of all dots, using the same exact-marginal donor/receiver ranking as the other arms so that only the relief direction differs. Under catalogue-like truth its basin donors forfeit the highest marginal-return terrain; under SGMC-like truth its range receivers harvest dense bedrock fault pixels.",
            "non_fault_mimic": "Bedrock lithologic contacts, dike swarms, joint/foliation lineaments, ridge crests and range-interior drainages generate strong linear detections in detrended highs; a bedrock map also records many range faults precisely because they are exposed, which is a mapping-completeness bias rather than a hidden-fault density.",
            "predicted_sign_size": f"MODEL predicted live delta {pred} vs parent R1 (range {pred_range}, preregistered; |delta|<0.01 live is no evidence). The bedrock-biased SGMC PROXY is expected to prefer this arm; that preference is reported, never gated on.",
            "falsifier": "A live RECEIPT >= R1+0.01 for this arm (after a directional rng2bas12 loss) falsifies the burial-incompleteness model and establishes that the scored new-fault population is dominated by exposed bedrock faulting; RELIEF would then be re-aimed range-ward. It is HOLD unless that rng2bas12 result occurs.",
            "references": REFERENCES,
        },
    }
    return cards[value]


if __name__ == "__main__":
    raise SystemExit(main())
