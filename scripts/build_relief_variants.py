#!/usr/bin/env python3
"""Build and validate controlled AXIS=RELIEF variants of parent R0 (h33-h33-2-b2).

Agent Brief v2 §5, AXIS=RELIEF: "shift 10-15% of mass between basin / piedmont /
range-front terciles (relief from the detrended-elevation bands), count fixed."

Zero DrivenData/Dropbox contact. Pipeline:
1. Verify SHA-256 + byte size of all 15 pinned inputs (registry/data_manifest.json).
2. Rebuild parent R0 byte-for-byte across the 5-stage lineage
      H19-5 (121,131 px) -> D1.5 -> D2.8 -> SOLO-D2.8 -> R0 (37,654 dots)
   and assert both pinned SHA-256 values (zeros c55bafc4..., NaN baeae321...).
3. Relief classes from the provided stack ONLY: Band 12 ``det_elev`` (detrended
   elevation; -3.4e38 sentinels inside the footprint replaced by the footprint
   median), split into AREA terciles over the footprint:
      class 1 = basin (lowest third), 2 = piedmont, 3 = range-front / range.
4. Three constant-count variants, one dose (12% of N = 4,518 dots), three directions:
      basin12  : piedmont + range  -> basin
      pied12   : basin + range     -> piedmont
      range12  : basin + piedmont  -> range
   Donor terciles are thinned by the SAME fraction of their movable dots (proportional
   thinning). R0's 2,171 collar dots (2 < d_cat <= 3 px) are frozen (never donors);
   every added dot sits on an un-emitted H19-5 ridge pixel at d_cat > 3 px inside the
   receiver tercile. Within-tercile choice of WHICH dots leave and WHERE dots land uses
   the exact iterative marginal expected-DTI solvers and the 15-channel label-free
   physics field already validated for PRUNEp3px (scripts/build_prune_variants.py),
   identically in all three arms, so differences between arms isolate relief.
5. MUST gates via bpv.write_and_verify_variant (format parity with sample_submission.tif,
   NaN outside + -zeros fallback, finite [0,1] inside, zero catalogue mass, unique
   SHA-256 vs ledger, parent-diff stats, re-read from disk) plus REPORT-ONLY instruments
   (hide-and-recover PROXY + 95% CI, blind off-catalogue USGS SGMC control, 10/12 km
   block-density CV, tercile shares before/after).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import time

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_variants as bpv  # noqa: E402

PARENT_ID = bpv.PARENT_ID
PARENT_SHA_ZEROS = bpv.PARENT_SHA_ZEROS
PARENT_SHA_NAN = bpv.PARENT_SHA_NAN
FIXED_DATE = "20261023"
SEED = bpv.SEED
AXIS = "RELIEF"
DOSE_PCT = 12.0
MIN_DCAT_NEW = 3.0
CLASS_NAMES = {1: "basin", 2: "piedmont", 3: "range"}
DIRECTIONS = {
    # value -> (receiver class, donor classes)
    "basin12": (1, (2, 3)),
    "pied12": (2, (1, 3)),
    "range12": (3, (1, 2)),
}
# Final MODEL predictions written AFTER the REPORT-ONLY instruments of the first build were seen
# (pre-registered values live in registry/relief_preregistration.json and are kept in every card).
# Reason for the revision: on the blind off-catalogue SGMC control every direction loses, with random
# donors too, because each spaced donor dot loses 0.10-0.16 TP while each densified add on the
# exhausted H19-5 support recovers only 0.04-0.07 TP (see evidence/relief_axis_report.json).
FINAL_MODEL = {
    "basin12": {"delta_live_vs_r0": -0.010, "range": [-0.020, 0.000]},
    "pied12": {"delta_live_vs_r0": -0.008, "range": [-0.018, 0.002]},
    "range12": {"delta_live_vs_r0": -0.003, "range": [-0.012, 0.008]},
}


# ---------------------------------------------------------------------------
# Relief classification (pure functions, unit-tested)
# ---------------------------------------------------------------------------


def sanitize_band(arr: np.ndarray, foot: np.ndarray) -> tuple[np.ndarray, int]:
    """Replace non-finite / float32-sentinel cells inside the footprint by the footprint median."""
    out = np.asarray(arr, dtype=np.float64).copy()
    bad = (~np.isfinite(out)) | (np.abs(out) > 1e20)
    good = foot & ~bad
    med = float(np.median(out[good]))
    out[bad] = med
    out[~foot] = 0.0
    return out, int((bad & foot).sum())


def relief_terciles(det_elev: np.ndarray, foot: np.ndarray) -> tuple[np.ndarray, tuple[float, float]]:
    """Area terciles of detrended elevation over the footprint.

    Returns int8 class grid (0 outside footprint, 1 basin, 2 piedmont, 3 range) and the two
    cut values. Each class holds one third of the footprint pixels up to quantile ties.
    """
    v = np.asarray(det_elev, dtype=np.float64)[foot]
    lo, hi = np.quantile(v, [1.0 / 3.0, 2.0 / 3.0])
    cls = np.zeros(foot.shape, dtype=np.int8)
    cls[foot] = 1 + np.digitize(np.asarray(det_elev, dtype=np.float64)[foot], [lo, hi])
    return cls, (float(lo), float(hi))


def proportional_donor_counts(n_move: int, movable_by_class: dict[int, int], donors: tuple[int, ...]) -> dict[int, int]:
    """Split n_move across donor classes in proportion to their movable dots (largest-remainder rounding)."""
    tot = sum(movable_by_class[c] for c in donors)
    if tot < n_move:
        raise ValueError(f"donor pool {tot} < n_move {n_move}")
    raw = {c: n_move * movable_by_class[c] / tot for c in donors}
    counts = {c: int(np.floor(raw[c])) for c in donors}
    short = n_move - sum(counts.values())
    for c in sorted(donors, key=lambda k: (raw[k] - counts[k], k), reverse=True)[:short]:
        counts[c] += 1
    assert sum(counts.values()) == n_move
    return counts


def class_shares(mask: np.ndarray, cls: np.ndarray) -> dict[str, dict[str, float]]:
    n = int(mask.sum())
    out = {}
    for k, name in CLASS_NAMES.items():
        m = cls == k
        nk = int((mask & m).sum())
        out[name] = {
            "n_dots": nk,
            "share": round(nk / n, 6) if n else 0.0,
            "density_per_1000px": round(1000.0 * nk / int(m.sum()), 4) if m.any() else 0.0,
        }
    return out


def sgmc_decomposition(
    r0: np.ndarray,
    variant: np.ndarray,
    truth_off: np.ndarray,
    foot: np.ndarray,
    catalogue: np.ndarray,
) -> dict:
    """REPORT-ONLY: split the blind SGMC control change into donor-removal loss and add gain."""
    from gems57 import metric

    removed = r0 & ~variant
    added = variant & ~r0
    mid = r0 & ~removed
    t0 = metric.dti_binary(r0, truth_off, valid=foot, known=catalogue)
    t1 = metric.dti_binary(mid, truth_off, valid=foot, known=catalogue)
    t2 = metric.dti_binary(variant, truth_off, valid=foot, known=catalogue)
    return {
        "evidence_label": "PROXY",
        "r0_dti": round(float(t0["dti"]), 6),
        "after_removal_dti": round(float(t1["dti"]), 6),
        "after_add_dti": round(float(t2["dti"]), 6),
        "removal_delta_tp": round(float(t1["tp"] - t0["tp"]), 2),
        "add_delta_tp": round(float(t2["tp"] - t1["tp"]), 2),
        "removal_tp_loss_per_dot": round(float((t0["tp"] - t1["tp"]) / max(int(removed.sum()), 1)), 4),
        "add_tp_gain_per_dot": round(float((t2["tp"] - t1["tp"]) / max(int(added.sum()), 1)), 4),
    }


def random_donor_sensitivity(
    r0: np.ndarray,
    cls: np.ndarray,
    receiver: int,
    donors: tuple[int, ...],
    n_move: int,
    *,
    w_field: np.ndarray,
    h19_5: np.ndarray,
    foot: np.ndarray,
    catalogue: np.ndarray,
    d_cat: np.ndarray,
    truth_off: np.ndarray,
    seed: int = SEED,
) -> dict:
    """REPORT-ONLY: same adds, but donors drawn uniformly at random inside each donor tercile.

    Separates the relief effect from the physics-field ranking of WHICH donor dots leave.
    """
    rng = np.random.default_rng(seed)
    movable = r0 & (d_cat > MIN_DCAT_NEW)
    movable_by_class = {c: int((movable & (cls == c)).sum()) for c in CLASS_NAMES}
    donor_counts = proportional_donor_counts(n_move, movable_by_class, donors)
    state = r0.copy()
    for c in sorted(donors):
        idx = np.flatnonzero((movable & (cls == c)).ravel())
        state.ravel()[rng.choice(idx, size=donor_counts[c], replace=False)] = False
    cand = h19_5 & ~r0 & foot & ~catalogue & (d_cat > MIN_DCAT_NEW) & (cls == receiver)
    out = bpv.select_exact_marginal_dti_add(base_mask=state, cand_mask=cand, w=w_field, n_add=n_move)
    dec = sgmc_decomposition(r0, out, truth_off, foot, catalogue)
    dec["seed"] = seed
    dec["note"] = "random uniform donors inside each donor tercile; exact-marginal adds; not a release candidate"
    return dec


def build_relief_variant(
    r0: np.ndarray,
    cls: np.ndarray,
    receiver: int,
    donors: tuple[int, ...],
    n_move: int,
    *,
    w_field: np.ndarray,
    h19_5: np.ndarray,
    foot: np.ndarray,
    catalogue: np.ndarray,
    d_cat: np.ndarray,
    collar_px: float = MIN_DCAT_NEW,
) -> tuple[np.ndarray, dict]:
    """Move n_move dots from donor terciles into the receiver tercile at fixed count."""
    movable = r0 & (d_cat > collar_px)
    movable_by_class = {c: int((movable & (cls == c)).sum()) for c in CLASS_NAMES}
    donor_counts = proportional_donor_counts(n_move, movable_by_class, donors)

    state = r0.copy()
    for c in sorted(donors):
        state = bpv.select_exact_marginal_dti_drop(
            base_mask=state,
            drop_pool_mask=movable & (cls == c),
            w=w_field,
            n_drop=donor_counts[c],
        )
    removed = r0 & ~state
    assert int(removed.sum()) == n_move
    assert not np.any(removed & (d_cat <= collar_px)), "a collar dot was used as a donor"

    cand = h19_5 & ~r0 & foot & ~catalogue & (d_cat > collar_px) & (cls == receiver)
    out = bpv.select_exact_marginal_dti_add(
        base_mask=state,
        cand_mask=cand,
        w=w_field,
        n_add=n_move,
    )
    added = out & ~r0
    assert int(added.sum()) == n_move
    assert int(out.sum()) == int(r0.sum())
    assert not np.any(added & ~(cls == receiver))
    assert float(d_cat[added].min()) > collar_px

    # Nearest-neighbour spacing of added dots to the retained parent dots (diagnostic only).
    from scipy.spatial import cKDTree

    ry, rx = np.nonzero(state)
    ay, ax = np.nonzero(added)
    d_nn, _ = cKDTree(np.column_stack([ry, rx])).query(np.column_stack([ay, ax]), k=1)
    d_nn = np.asarray(d_nn, dtype=np.float64)
    stats = {
        "n_move": int(n_move),
        "receiver": CLASS_NAMES[receiver],
        "donors": [CLASS_NAMES[c] for c in sorted(donors)],
        "donor_counts": {CLASS_NAMES[c]: int(donor_counts[c]) for c in sorted(donors)},
        "donor_thinning_fraction": {
            CLASS_NAMES[c]: round(donor_counts[c] / movable_by_class[c], 6) for c in sorted(donors)
        },
        "movable_parent_dots_by_class": {CLASS_NAMES[c]: movable_by_class[c] for c in CLASS_NAMES},
        "candidate_pool_receiver_px": int(cand.sum()),
        "added_min_dcat_px": round(float(d_cat[added].min()), 4),
        "added_median_dcat_px": round(float(np.median(d_cat[added])), 4),
        "removed_median_dcat_px": round(float(np.median(d_cat[removed])), 4),
        "added_nn_to_retained_parent_px": {
            "min": round(float(d_nn.min()), 4),
            "median": round(float(np.median(d_nn)), 4),
            "mean": round(float(d_nn.mean()), 4),
            "share_lt_2px": round(float((d_nn < 2.0).mean()), 4),
            "share_ge_2p8px": round(float((d_nn >= 2.8).mean()), 4),
        },
        "shares_before": class_shares(r0, cls),
        "shares_after": class_shares(out, cls),
    }
    return out, stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    t0 = time.time()
    print("[1/6] Verifying SHA-256 manifest pins...")
    verified = bpv.verify_manifest()
    print(f"      Verified {len(verified)}/{len(verified)} pinned inputs.")

    print("[2/6] Rebuilding parent R0 (h33-h33-2-b2) across all 5 lineage steps...")
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    print(
        f"      EXACT R0 REBUILD OK: {int(r0.sum()):,} dots | "
        f"zeros={lin['rebuilt_zeros_sha256'][:12]}... | nan={lin['rebuilt_nan_sha256'][:12]}..."
    )

    print("[3/6] Relief terciles from provided Band 12 det_elev...")
    with rasterio.open(verified["training_features"]) as ds:
        assert ds.descriptions[11].startswith("det_elev -"), ds.descriptions[11]
        b12_raw = ds.read(12)
        b19_raw = ds.read(19)
    b12, n_bad12 = sanitize_band(b12_raw, foot)
    b19, _ = sanitize_band(b19_raw, foot)
    del b12_raw, b19_raw
    cls, (cut_lo, cut_hi) = relief_terciles(b12, foot)
    relief_summary = {
        "band": "training_features.tif Band 12 det_elev (detrended elevation, m)",
        "sentinels_replaced_inside_footprint": n_bad12,
        "tercile_cuts_m": [round(cut_lo, 3), round(cut_hi, 3)],
        "classes": {},
    }
    for k, name in CLASS_NAMES.items():
        m = cls == k
        relief_summary["classes"][name] = {
            "footprint_px": int(m.sum()),
            "det_elev_mean_m": round(float(b12[m].mean()), 2),
            "det_elev_slope_b19_mean": round(float(b19[m].mean()), 4),
            "catalogue_px": int((catalogue & m).sum()),
            "catalogue_share": round(float((catalogue & m).sum() / catalogue.sum()), 4),
            "h19_5_px": int((h19_5 & m).sum()),
            "r0_dots": int((r0 & m).sum()),
            "r0_share": round(float((r0 & m).sum() / r0.sum()), 4),
            "r0_density_per_1000px": round(float(1000.0 * (r0 & m).sum() / m.sum()), 4),
            "r0_collar_dots_2_3px": int((r0 & m & (d_cat <= 3.0)).sum()),
        }
    del b12, b19
    print(f"      cuts = {cut_lo:.2f} m / {cut_hi:.2f} m; R0 shares = "
          + ", ".join(f"{n}:{relief_summary['classes'][n]['r0_share']:.3f}" for n in CLASS_NAMES.values()))

    print("[4/6] Rebuilding label-free physics field & leakage canaries (same as PRUNE)...")
    w_field, canaries = bpv.build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    print(
        f"      Canaries PASS ({len(canaries)}/{len(canaries)} channels <= 0.90; "
        f"max symmetric AUC = {max(canaries.values()):.5f})"
    )

    n_move = int(round(DOSE_PCT / 100.0 * int(r0.sum())))
    print(f"[5/6] Building {len(DIRECTIONS)} AXIS=RELIEF variants (dose {DOSE_PCT:.0f}% = {n_move:,} dots, N fixed)...")
    masks: dict[str, np.ndarray] = {}
    stats: dict[str, dict] = {}
    for val, (receiver, donors) in DIRECTIONS.items():
        t1 = time.time()
        m, st = build_relief_variant(
            r0, cls, receiver, donors, n_move,
            w_field=w_field, h19_5=h19_5, foot=foot, catalogue=catalogue, d_cat=d_cat,
        )
        masks[val] = m
        stats[val] = st
        print(f"      {val}: receiver={st['receiver']} donors={st['donor_counts']} "
              f"pool={st['candidate_pool_receiver_px']:,} added_nn_med={st['added_nn_to_retained_parent_px']['median']} "
              f"({time.time() - t1:.1f}s)")

    # REPORT-ONLY decomposition on the blind off-catalogue USGS SGMC control + random-donor sensitivity
    from scipy.ndimage import binary_dilation

    sgmc_raw = rasterio.open(verified["sgmc_faults_control"]).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)
    del sgmc_raw
    for val, (receiver, donors) in DIRECTIONS.items():
        stats[val]["sgmc_decomposition"] = sgmc_decomposition(r0, masks[val], sgmc_off, foot, catalogue)
        stats[val]["sgmc_random_donor_sensitivity"] = random_donor_sensitivity(
            r0, cls, receiver, donors, n_move,
            w_field=w_field, h19_5=h19_5, foot=foot, catalogue=catalogue, d_cat=d_cat, truth_off=sgmc_off,
        )
        dec, rnd = stats[val]["sgmc_decomposition"], stats[val]["sgmc_random_donor_sensitivity"]
        print(f"      {val}: SGMC removal {dec['removal_tp_loss_per_dot']:.4f} TP/dot lost, add {dec['add_tp_gain_per_dot']:.4f} TP/dot gained "
              f"-> {dec['after_add_dti']:.5f} (random donors {rnd['after_add_dti']:.5f}; R0 {dec['r0_dti']:.5f})")
    # Does the physics field rank blind SGMC-credited parent dots higher? (REPORT-ONLY leakage/quality check)
    from scipy.ndimage import distance_transform_edt
    from sklearn.metrics import roc_auc_score

    k_sgmc = np.clip(1.0 - distance_transform_edt(~sgmc_off) / 3.0, 0.0, 1.0)
    ranking_quality = {
        "evidence_label": "PROXY",
        "question": "AUC of the PRUNE physics field w for (SGMC self-credit > 0) among parent R0 dots",
        "auc_all_r0_dots": round(float(roc_auc_score(k_sgmc[r0] > 0, w_field[r0])), 4),
        "auc_by_tercile": {
            name: round(float(roc_auc_score(k_sgmc[r0 & (cls == c)] > 0, w_field[r0 & (cls == c)])), 4)
            for c, name in CLASS_NAMES.items()
        },
    }
    del k_sgmc, sgmc_off
    print(f"      physics-field ranking vs blind SGMC: AUC {ranking_quality['auc_all_r0_dots']} {ranking_quality['auc_by_tercile']}")
    del w_field

    prereg = json.loads((ROOT / "registry" / "relief_preregistration.json").read_text())
    pre = prereg["pre_registered_model_predictions"]

    ledger_path = ROOT / "ledger" / "submissions.csv"
    existing_rows: list[dict[str, str]] = []
    existing_shas: set[str] = {PARENT_SHA_ZEROS, PARENT_SHA_NAN}
    if ledger_path.is_file():
        with ledger_path.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("axis") == AXIS and row.get("value") in DIRECTIONS and row.get("parent") == PARENT_ID:
                    continue  # idempotent rerun replaces only this family's rows
                existing_rows.append(row)
                for key in ("sha256", "sha256_zeros"):
                    if row.get(key):
                        existing_shas.add(row[key])
    # (parent, axis, value) dedupe: no other row may already carry one of our pairs
    for row in existing_rows:
        assert not (row.get("parent") == PARENT_ID and row.get("axis") == AXIS and row.get("value") in DIRECTIONS)

    releases_dir = ROOT / "releases"
    for val in DIRECTIONS:
        for old_p in releases_dir.glob(f"{PARENT_ID}-{AXIS}{val}-*"):
            old_p.unlink()

    cards_path = ROOT / "ledger" / "mechanism_cards.json"
    cards = json.loads(cards_path.read_text()) if cards_path.is_file() else {}
    cards = {k: v for k, v in cards.items() if not any(f"-{AXIS}{val}-" in k for val in DIRECTIONS)}

    card_text = {
        "basin12": {
            "hypothesis": "Moving 12% of R0's dots (4,518) from the piedmont and range terciles onto un-emitted H19-5 ridges in the basin tercile (detrended elevation below the lower tercile cut) LOWERS live DTI: basin-floor faults are blind beneath Quaternary fill, so the expert-mapped 'new fault' labels that score the public chunks contain few basin-interior pixels, and the relocated dots pay the 0.2*S denominator cost without kernel credit.",
            "mechanism": "DTI = T / (0.2T + 0.2(S - M) + 0.8|G|). At fixed S the change is driven by Delta T - 0.2*DTI*Delta(T - M). Dots removed from piedmont/range ridges lose line-like truth credit (several truth pixels per dot inside the 300 m triangular kernel); dots added on basin ridges recover credit only where a blind fault was actually mapped (seismic reflection, well ties or lineament work), which is rare in a map-derived label set. Expected sign negative, magnitude proportional to the dose.",
            "non_fault_mimic": "Basin H19-5 ridges are dominated by GeoDAWN aeromagnetic gradients over buried volcanic flows and by gravity gradients at depositional basin margins; Lake Lahontan shoreline berms and playa edges also produce detrended-elevation and radiometric edges without brittle offset.",
            "predicted_sign_size": f"MODEL (final, after REPORT-ONLY proxies) {FINAL_MODEL['basin12']['delta_live_vs_r0']:+.3f} live delta vs R0, range {FINAL_MODEL['basin12']['range']}; pre-registered a priori value was {pre['basin12']['delta_live_vs_r0']:+.3f} (registry/relief_preregistration.json); a live change under 0.01 in absolute value is no evidence.",
            "falsifier": "A live receipt >= R0 + 0.01 for basin12 while range12 is <= R0 falsifies the 'blind basins are unlabelled' premise and shows the hidden label set was built from geophysical lineaments rather than from exposure-limited mapping; in that case the final file should move mass basinward, not rangeward.",
        },
        "pied12": {
            "hypothesis": "Moving 12% of R0's dots from the basin and range terciles onto un-emitted H19-5 ridges in the piedmont tercile (the alluvial apron / range-front junction band) gives a small positive change: Quaternary fault scarps that cut alluvial fans are the classic targets of new lidar-based fault mapping in the Great Basin, and the range-front master faults of geothermal systems emerge at the piedmont.",
            "mechanism": "Piedmont truth is line-like and continuous (multi-km scarps), so each added dot on a true scarp earns up to ~3 kernel credits (k = 1, 2/3, 1/3 along strike) against a 0.2 denominator cost; the dots given up in basins carry little credit. The effect is capped because R0 already spends 41.8% of its dots in this tercile (density 9.1 per 1,000 px, the highest of the three), so the marginal un-emitted H19-5 piedmont ridges are the ones the Poisson-disk thinning already passed over.",
            "non_fault_mimic": "Alluvial-fan terrace risers, incised channel banks, beach ridges of pluvial lakes (1,212-1,334 m) and pediment-bedrock contacts form sharp 100 m detrended-elevation breaks parallel to range fronts without a fault plane.",
            "predicted_sign_size": f"MODEL (final, after REPORT-ONLY proxies) {FINAL_MODEL['pied12']['delta_live_vs_r0']:+.3f} live delta vs R0, range {FINAL_MODEL['pied12']['range']}; pre-registered a priori value was {pre['pied12']['delta_live_vs_r0']:+.3f} (registry/relief_preregistration.json); a live change under 0.01 in absolute value is no evidence.",
            "falsifier": "A live receipt <= R0 - 0.01 for pied12 falsifies the 'new labels are piedmont scarps' premise (the lineage's piedmont share is already saturated or wrong); a receipt >= R0 + 0.01 with range12 <= R0 confirms it and makes the piedmont the receiver for a larger-dose follow-up.",
        },
        "range12": {
            "hypothesis": "Moving 12% of R0's dots from the basin and piedmont terciles onto un-emitted H19-5 ridges in the range tercile (detrended elevation above the upper tercile cut) RAISES live DTI: faults in bedrock ranges are exposed and are mapped directly on geologic maps, so any label compilation that goes beyond the USGS Quaternary / INGENIOUS catalogue is dominated by range faults, while R0 spends only 37.7% of its dots there.",
            "mechanism": "The independent, blind USGS SGMC fault layer (state geologic map faults not in the catalogue, 62,703 off-catalogue pixels) places 63.6% of its pixels in the range tercile versus 25.1% piedmont and 11.3% basin. If the hidden 'new fault' labels have a similar exposure-controlled relief profile, R0's range tercile is under-served: each dot moved onto a range H19-5 ridge gains line-like kernel credit at fixed S, and the basin dots it replaces were earning little. Expected sign positive, size scaling with dose until range ridges saturate.",
            "non_fault_mimic": "Lithologic contacts, dikes, bedding and foliation traces, welded-tuff cooling joints and caldera margins all produce magnetic/gravity gradients and topographic breaklines in ranges that H19-5 can ridge-detect without a fault; range-interior faults may also be older, inactive structures that experts exclude from a geothermal-relevant label set.",
            "predicted_sign_size": f"MODEL (final, after REPORT-ONLY proxies) {FINAL_MODEL['range12']['delta_live_vs_r0']:+.3f} live delta vs R0, range {FINAL_MODEL['range12']['range']}; pre-registered a priori value was {pre['range12']['delta_live_vs_r0']:+.3f} (registry/relief_preregistration.json); a live change under 0.01 in absolute value is no evidence.",
            "falsifier": "A live receipt <= R0 - 0.01 for range12 falsifies the exposure-controlled label premise (the hidden labels are not bedrock-map faults) and closes the range direction; a receipt >= R0 + 0.01 promotes range12 to R1' and motivates an 18-20% dose and a CONCENTRATION arm inside the range tercile.",
        },
    }

    print("[6/6] Writing GeoTIFFs, MUST gates, REPORT-ONLY instruments...")
    built = []
    new_rows = []
    arms = {PARENT_ID: r0}
    for val, (receiver, donors) in DIRECTIONS.items():
        st = stats[val]
        donor_txt = "+".join(st["donors"])
        note_tmpl = (
            f"h33-2-b2; RELIEF 12% of dots (4518) {donor_txt}->{st['receiver']} "
            f"det_elev terciles, N fixed; pred {FINAL_MODEL[val]['delta_live_vs_r0']:+.3f} MODEL"
        )
        rec = bpv.write_and_verify_variant(
            mask=masks[val],
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=releases_dir,
            parent_mask=r0,
            axis=AXIS,
            value=val,
            note_template=note_tmpl,
            existing_shas=existing_shas,
        )
        existing_shas.update({rec["sha256"], rec["sha256_zeros"]})
        rec["relief"] = st
        rec["relief_classification"] = relief_summary
        rec["parent_diff"]["min_dist_added_catalogue_px"] = st["added_min_dcat_px"]
        rec["parent_diff"]["collar_dots_2_3px_unchanged"] = int(
            (masks[val] & r0 & (d_cat <= 3.0)).sum()
        ) == int((r0 & (d_cat <= 3.0)).sum())
        built.append(rec)
        arms[rec["id"]] = masks[val]
        card = {
            "axis": AXIS,
            "value": val,
            "dose_pct": DOSE_PCT,
            "n_move": n_move,
            "pct_changed": rec["parent_diff"]["pct_changed_moved"],
            "receiver": st["receiver"],
            "donors": st["donors"],
            "pre_registered_model": pre[val],
            "final_model": FINAL_MODEL[val],
            **card_text[val],
        }
        cards[rec["id"]] = card
        new_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": AXIS,
                "value": val,
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{FINAL_MODEL[val]['delta_live_vs_r0']:+.3f}",
                "predicted_range": f"[{FINAL_MODEL[val]['range'][0]:+.3f},{FINAL_MODEL[val]['range'][1]:+.3f}]",
                "ranking_basis": "Band 12 det_elev area terciles; proportional donor thinning; within-tercile drops/adds by exact marginal DTI under the PRUNE physics field; collar frozen",
                "receipt_score": "",
                "receipt_date": "",
                "description": (
                    f"Move {n_move} dots (12%) from {donor_txt} terciles into the {st['receiver']} tercile "
                    f"(donor counts {st['donor_counts']}); added dots on un-emitted H19-5 ridges at d_cat>3 px; "
                    f"shares {CLASS_NAMES[1]}/{CLASS_NAMES[2]}/{CLASS_NAMES[3]} "
                    f"{st['shares_before']['basin']['share']:.3f}/{st['shares_before']['piedmont']['share']:.3f}/{st['shares_before']['range']['share']:.3f}"
                    f" -> {st['shares_after']['basin']['share']:.3f}/{st['shares_after']['piedmont']['share']:.3f}/{st['shares_after']['range']['share']:.3f}."
                ),
                "recommendation": "",  # filled after REPORT-ONLY instruments below
            }
        )

    eval_report = bpv.evaluate_report_only_instruments(
        arms=arms, foot=foot, catalogue=catalogue, sgmc_path=verified["sgmc_faults_control"]
    )
    for rec, row in zip(built, new_rows):
        diag = eval_report[rec["id"]]
        rec["report_only_diagnostics"] = diag
        rec["r0_reference_diagnostics"] = eval_report[PARENT_ID]
        rec["leakage_canaries"] = {
            "passed": True,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        }
        rec["pre_registration"] = "registry/relief_preregistration.json"
        (releases_dir / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        sg = diag["sgmc_control"]["dti"]
        sg0 = eval_report[PARENT_ID]["sgmc_control"]["dti"]
        dec = rec["relief"]["sgmc_decomposition"]
        rnd = rec["relief"]["sgmc_random_donor_sensitivity"]
        role = (
            "HOLD/DIAGNOSTIC (least negative RELIEF arm; only slot-worthy as a label-relief probe after PRUNEp3px and SNAPscarp2px)"
            if rec["value"] == "range12"
            else "HOLD (negative on blind control; do not spend a slot)"
        )
        row["recommendation"] = (
            f"{role}: blind off-catalogue SGMC {sg:.5f} PROXY ({sg - sg0:+.5f} vs R0; random-donor control {rnd['after_add_dti']:.5f}); "
            f"donor loss {dec['removal_tp_loss_per_dot']:.3f} TP/dot vs densified-add gain {dec['add_tp_gain_per_dot']:.3f} TP/dot; "
            f"12 km CV {diag['block_density_cv']['cv_12km_120px_interior']:.4f}; R0's 2171 2-3 px collar dots unchanged; all {n_move} added dots at d_cat > 3 px."
        )
        cards[rec["id"]]["report_only_after_build"] = {
            "sgmc_control_dti": sg,
            "sgmc_delta_vs_r0": round(sg - sg0, 6),
            "holdout_proxy_dti": diag["holdout_proxy"]["dti"],
            "cv_12km": diag["block_density_cv"]["cv_12km_120px_interior"],
        }

    fieldnames = [
        "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256", "sha256_zeros", "status",
        "predicted_change", "predicted_range", "ranking_basis", "receipt_score", "receipt_date",
        "description", "recommendation",
    ]
    with ledger_path.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        wr.writeheader()
        for r in [*existing_rows, *new_rows]:
            wr.writerow({k: r.get(k, "") for k in fieldnames})
    cards_path.write_text(json.dumps(cards, indent=2) + "\n")

    summary = {
        "session_date": "2026-10-23",
        "axis": AXIS,
        "dose_pct": DOSE_PCT,
        "n_move": n_move,
        "parent_r0": {
            "id": PARENT_ID,
            "n_dots": int(r0.sum()),
            "rebuilt_zeros_sha256": lin["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lin["rebuilt_nan_sha256"],
            "diagnostics": eval_report[PARENT_ID],
        },
        "relief_classification": relief_summary,
        "provided_bands_only_for_relief": True,
        "pre_registration": prereg,
        "final_model_predictions": FINAL_MODEL,
        "leakage_canaries": {
            "passed": True,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        },
        "ranking_quality_vs_blind_sgmc": ranking_quality,
        "variants": built,
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    (ROOT / "evidence" / "relief_axis_report.json").write_text(json.dumps(summary, indent=2) + "\n")

    print("\n=== SUMMARY OF BUILT AXIS=RELIEF VARIANTS ===")
    for rec in built:
        diag = rec["report_only_diagnostics"]
        hp, sg, cv = diag["holdout_proxy"], diag["sgmc_control"], diag["block_density_cv"]
        st = rec["relief"]
        print(
            f"  {rec['id']} | moved={rec['parent_diff']['pct_changed_moved']:.2f}% | "
            f"shares b/p/r {st['shares_after']['basin']['share']:.3f}/{st['shares_after']['piedmont']['share']:.3f}/{st['shares_after']['range']['share']:.3f} | "
            f"HOLDOUT-PROXY={hp['dti']:.6f} {hp['ci95']} | SGMC={sg['dti']:.6f} | CV12km={cv['cv_12km_120px_interior']:.4f}"
        )
    print(f"Completed in {summary['elapsed_seconds']}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
