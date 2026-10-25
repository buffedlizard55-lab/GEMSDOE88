#!/usr/bin/env python3
"""AXIS=CONCENTRATION on the gate-clean parent ``R1``: prior-weighted 1 km-block relocation.

Why this axis, why this parent
------------------------------
Brief v2 section 4.4 forbids positive mass closer than 3 px to the catalogue for
every non-PRUNE axis.  All four ledgered ``CONCENTRATION`` rows are parented on
``R0``, which keeps 1,611 dots strictly inside 3 px, so all four are ``HOLD``
under the hardened ``validate_variant.py`` and the axis has never had a
spendable arm.  ``R1 = h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`` is the same
37,654-dot lineage with only the ``<= 3 px`` collar purged and refilled
(IR-88-43), and it is rebuilt here from the pinned lineage with both published
SHA-256 values asserted before it is touched.

What is different from the R0 CONCENTRATION family
--------------------------------------------------
The R0 arms welded each receiver 8-adjacent (mean 1.04 px) to a surviving host
dot, i.e. they duplicated existing dots inside hot blocks.  The parent dot set
is already near-maximally packed at mutual distance 2.8 px on its own
121,131-px H19-5 support, so duplication is the only *on-support* move
available and it adds denominator mass without new coverage.  This family
requires every receiver to sit **>= 2.8 px from every surviving dot and from
every other receiver**, which forces the relocated mass off the saturated
support and into ground that was previously uncovered.  The treatment therefore
tests the km-scale prior *and* converts redundancy into coverage; the mirror arm
holds the coverage move fixed and flips only the prior.

Three arms (fixed count 37,654, deterministic, no RNG)
------------------------------------------------------
* ``phys10-m10``   -- 3,765 dots (10%) from the coldest to the hottest 1 km blocks.
* ``phys10-m20``   -- 7,531 dots (20%), same rule: dose.
* ``phys10-m10lo`` -- the SAME 3,765 donors into the COLDEST blocks: mirror control.

Prior: mean of robustly unit-scaled provided bands 3 (tmi_hg), 5 and 18
(iso_grav_anom_hg) gradients, averaged over each fully-inside 10 x 10 px
(1 km x 1 km) block -- the same construction as the ledgered R0 arm
``15pct-1km-grad``.  No label, no SGMC, no withheld pixel is used for any
ordering decision.

Everything below is a MUST gate per brief section 6; every proxy is REPORT ONLY.
"""
from __future__ import annotations

# Project-wide literal duplicate stop: execute before feature/model imports.
if __name__ == "__main__":
    import sys as _guard_sys
    from pathlib import Path as _GuardPath
    _guard_sys.path.insert(0, str(_GuardPath(__file__).resolve().parents[1]))
    from scripts.generation_guard import enforce_generation_preflight
    enforce_generation_preflight()


import csv
import json
import math
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

import build_prune_variants as bp
import build_spacing_variants as bsp

ROOT = bp.ROOT
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
REPORT = ROOT / "evidence" / "concentration_r1_axis_report.json"
PREREG = ROOT / "registry" / "preregistration_concentration_r1.json"

R1_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
R1_SHA_NAN = "6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9"
R1_SHA_ZEROS = "dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f"
N_DOTS = 37_654
N_PARENT_DOTS = N_DOTS
BLOCK_PX = 10
MIN_CATALOGUE_PX = 3.0
SPACING_PX = 2.8
PRIOR_BANDS = (3, 5, 18)
DATE = bp.FIXED_DATE

# value -> (move fraction, destination pole)
ARMS = {
    "phys10-m10": (0.10, "high"),
    "phys10-m20": (0.20, "high"),
    "phys10-m10lo": (0.10, "low"),
}
# value -> (preregistered MODEL prediction, range)
PREDICTIONS = {
    "phys10-m10": ("+0.005", "[-0.008,+0.018]"),
    "phys10-m20": ("+0.009", "[-0.012,+0.030]"),
    "phys10-m10lo": ("-0.005", "[-0.018,+0.008]"),
}

LEDGER_COLUMNS = [
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256", "sha256_zeros",
    "status", "predicted_change", "predicted_range", "ranking_basis", "receipt_score",
    "receipt_date", "description", "recommendation",
]

# Integer offsets strictly closer than the spacing lock; used both to build the
# survivor exclusion mask and to stamp each placed receiver.
SPACING_OFFSETS = tuple(
    (dy, dx)
    for dy in range(-2, 3)
    for dx in range(-2, 3)
    if dy * dy + dx * dx < SPACING_PX * SPACING_PX
)


# ---------------------------------------------------------------------------
# Prior and block lattice
# ---------------------------------------------------------------------------

def robust_unit(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Clip to the 10th-99th percentile of the valid pixels and rescale to [0, 1]."""
    vals = a[valid & np.isfinite(a)]
    if vals.size == 0:
        return np.zeros(a.shape, np.float32)
    lo, hi = np.percentile(vals, [10.0, 99.0])
    out = np.zeros(a.shape, np.float32)
    out[valid] = np.clip((a[valid] - lo) / max(float(hi - lo), 1e-12), 0.0, 1.0)
    return out


def structural_prior(features_path: Path, foot: np.ndarray) -> tuple[np.ndarray, list[str], dict]:
    """Label-free 1 km block prior: mean robust unit-scaled bands 3, 5, 18 gradients."""
    with rasterio.open(features_path) as ds:
        names = [ds.descriptions[i - 1] for i in (3, 5, 18)]
        nodata = ds.nodata
        units = []
        for idx in PRIOR_BANDS:
            a = np.where(foot, np.nan_to_num(ds.read(idx), nan=0.0), 0.0).astype(np.float32)
            bad = (~np.isfinite(a)) | (np.abs(a) > 1e20)
            if np.any(bad & foot):
                a[bad] = float(np.median(a[foot & ~bad]))
            a[~foot] = 0.0
            units.append(robust_unit(a, foot))
            del a, bad
    prior = np.mean(units, axis=0, dtype=np.float32)
    del units
    prior[~foot] = 0.0
    return prior, names, {"bands_1indexed": list(PRIOR_BANDS), "band_descriptions": names,
                          "construction": "mean of robust_unit(band) over bands 3,5,18; 10-99 pct clip"}


def block_tables(foot: np.ndarray, prior: np.ndarray) -> dict:
    """Per-block prior mean and validity on a 10 x 10 px (1 km) lattice."""
    H, W = foot.shape
    nbr, nbc = math.ceil(H / BLOCK_PX), math.ceil(W / BLOCK_PX)
    rr, cc = np.indices((H, W), sparse=True)
    block_id = ((rr // BLOCK_PX) * nbc + (cc // BLOCK_PX)).astype(np.int32)
    nblocks = nbr * nbc
    valid_count = np.bincount(block_id[foot], minlength=nblocks)
    prior_sum = np.bincount(block_id[foot], weights=prior[foot].astype(np.float64), minlength=nblocks)
    full = valid_count == BLOCK_PX * BLOCK_PX
    block_prior = np.full(nblocks, np.nan)
    block_prior[full] = prior_sum[full] / valid_count[full]
    return {
        "block_id": block_id,
        "nblocks": nblocks,
        "nbr": nbr,
        "nbc": nbc,
        "full": full,
        "block_prior": block_prior,
        "eligible": np.flatnonzero(full),
    }


def block_density_cv(mask: np.ndarray, foot: np.ndarray, block_px: int) -> dict:
    """Density CV over FULL interior blocks (all and occupied), as the brief asks."""
    H, W = foot.shape
    Hs, Ws = (H // block_px) * block_px, (W // block_px) * block_px
    fb = foot[:Hs, :Ws].reshape(Hs // block_px, block_px, Ws // block_px, block_px).sum(axis=(1, 3))
    ab = mask[:Hs, :Ws].reshape(Hs // block_px, block_px, Ws // block_px, block_px).sum(axis=(1, 3))
    interior = fb == block_px * block_px
    dens = ab[interior] / fb[interior]
    occ = dens[ab[interior] > 0]
    if dens.size == 0 or occ.size == 0:
        return {"block_px": block_px, "cv_all_full_blocks": float("nan"),
                "cv_occupied_full_blocks": float("nan"), "n_full_blocks": int(interior.sum()),
                "n_occupied_full_blocks": int(occ.size), "mean_dots_per_occupied_block": 0.0}
    return {
        "block_px": block_px,
        "cv_all_full_blocks": round(float(dens.std() / dens.mean()), 4),
        "cv_occupied_full_blocks": round(float(occ.std() / occ.mean()), 4),
        "n_full_blocks": int(interior.sum()),
        "n_occupied_full_blocks": int((ab[interior] > 0).sum()),
        "mean_dots_per_occupied_block": round(float(ab[interior].mean()), 4),
    }


# ---------------------------------------------------------------------------
# Donors
# ---------------------------------------------------------------------------

def choose_donors(
    parent: np.ndarray,
    prior: np.ndarray,
    tables: dict,
    n_drop: int,
    pole: str,
    keep_one_per_block: bool = True,
) -> np.ndarray:
    """Pick ``n_drop`` parent dots in the coldest blocks, lowest local prior first.

    A block never loses its last dot when ``keep_one_per_block`` is set, so a
    block that is emptied cannot be mistaken for a support decision.  Ordering
    terminates in (row, col): deterministic, no RNG.
    """
    py, px = np.nonzero(parent)
    bid = tables["block_id"][py, px]
    bpv = tables["block_prior"][bid]
    # Dots in non-full (edge) blocks inherit the global median prior: they are
    # the least informative donors and are visited last, not first.
    bpv = np.where(np.isfinite(bpv), bpv, np.nanmedian(bpv))
    dots_per_block = np.bincount(bid, minlength=tables["nblocks"])
    from scipy.spatial import cKDTree

    pts = np.column_stack([py, px]).astype(np.float64)
    nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    order = np.lexsort((px, py, -nn, prior[py, px], bpv))
    # For the mirror arm the donor set is identical (same dot ordering); only the
    # destination flips, so donors are chosen by the same cold-first rule.
    remaining = dots_per_block.copy()
    chosen: list[int] = []
    for i in order.tolist():
        if len(chosen) >= n_drop:
            break
        b = int(bid[i])
        if keep_one_per_block and remaining[b] <= 1:
            continue
        remaining[b] -= 1
        chosen.append(i)
    if len(chosen) < n_drop:
        raise RuntimeError(f"donor pool exhausted after {len(chosen)} of {n_drop}")
    donors = np.zeros_like(parent)
    donors[py[np.asarray(chosen)], px[np.asarray(chosen)]] = True
    return donors


# ---------------------------------------------------------------------------
# Receivers
# ---------------------------------------------------------------------------

def spacing_blocked_mask(points: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """True where a new dot would violate the ``SPACING_PX`` lock to ``points``."""
    blocked = np.zeros(shape, dtype=bool)
    H, W = shape
    for y, x in points:
        for dy, dx in SPACING_OFFSETS:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                blocked[yy, xx] = True
    return blocked


def receiver_candidates(
    target_blocks: np.ndarray,
    foot: np.ndarray,
    catalogue: np.ndarray,
    d_cat: np.ndarray,
    parent: np.ndarray,
    blocked: np.ndarray,
    prior: np.ndarray,
    tables: dict,
    pole: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Ordered candidate pixels: empty target blocks first, then by block and local prior."""
    H, W = foot.shape
    cand = np.zeros((H, W), dtype=bool)
    for b in target_blocks:
        br, bc = divmod(int(b), tables["nbc"])
        cand[br * BLOCK_PX:(br + 1) * BLOCK_PX, bc * BLOCK_PX:(bc + 1) * BLOCK_PX] = True
    cand &= foot & ~catalogue & (d_cat > MIN_CATALOGUE_PX) & ~parent & ~blocked
    cy, cx = np.nonzero(cand)
    bid = tables["block_id"][cy, cx]
    bpv = tables["block_prior"][bid]
    dots_in_block = np.bincount(tables["block_id"][np.nonzero(parent)], minlength=tables["nblocks"])
    occupied = dots_in_block[bid] > 0
    sign = -1.0 if pole == "high" else 1.0  # full-prior block first for 'high'
    order = np.lexsort((cx, cy, -prior[cy, cx], sign * bpv, occupied))
    return cy[order], cx[order]


def greedy_place(
    cand_y: np.ndarray,
    cand_x: np.ndarray,
    blocked: np.ndarray,
    d_cat: np.ndarray,
    n_place: int,
) -> np.ndarray:
    """Walk the ordered candidates, greedily placing ones still clear of the lock."""
    H, W = blocked.shape
    taken = blocked.copy()
    out = np.zeros_like(blocked)
    placed = 0
    for y, x in zip(cand_y.tolist(), cand_x.tolist()):
        if placed >= n_place:
            break
        if taken[y, x] or d_cat[y, x] <= MIN_CATALOGUE_PX:
            continue
        out[y, x] = True
        placed += 1
        for dy, dx in SPACING_OFFSETS:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W:
                taken[yy, xx] = True
    if placed < n_place:
        raise RuntimeError(f"receiver pool exhausted after {placed} of {n_place}")
    return out


# ---------------------------------------------------------------------------
# Mechanism cards
# ---------------------------------------------------------------------------

def mechanism_card(value: str, n_moved: int, pct: float, stats: dict) -> dict:
    mirror = value.endswith("lo")
    dest = "the *coldest*" if mirror else "the *hottest*"
    return {
        "hypothesis": (
            f"Relocating {n_moved:,} ({pct:.2f}%) of the parent's dots out of the coldest 1 km blocks and into "
            f"{dest} 1 km blocks, ranked by the provided TMI/gravity horizontal gradients, raises DTI because the "
            "parent's mass is already maximally packed on its own lineament support and therefore buys no new "
            "coverage, while the potential-field prior still ranks where unmapped traces are."
        ),
        "mechanism": (
            "DTI = T/(0.2T + 0.2(S-M) + 0.8|G|). |G| is fixed at 37,654, so the edit is a pure swap: each removed "
            "dot stops paying its 0.2*DTI denominator share, and each receiver pays 0.2*(1-DTI) at most. A dot "
            "placed in open ground with no truth within 300 m earns T = 0 and loses ~0.03 of DTI score; a dot that "
            "lands on an unmapped trace earns 0.5-1.0 and gains ~10-18x that. The >=2.8 px spacing lock keeps the "
            "receivers from collapsing back onto each other, which is the failure mode of the R0 family's "
            "1.04 px host-welded receivers."
        ),
        "non_fault_mimic": (
            "Lake Lahontan shoreline benches (~1212/1294/1334 m) and GeoDAWN 400 m flight-line corrugation both "
            "produce TMI and gravity-gradient edges at kilometre scale that are not faults, and hot-spring / vent "
            "clusters raise the prior without being fault pixels. The mirror arm quantifies this: if the prior were "
            "pure bench/flight-line artefact, the cold-block arm would match or beat the hot-block arm."
        ),
        "predicted_sign_and_size": (
            "MODEL +0.005 (10% dose) / +0.009 (20% dose) vs parent R1 on the live public chunks; mirror arm "
            "MODEL -0.005. Ranges are wide because the metric is dominated by unseen line-like truth and a "
            "|live delta| < 0.01 is no evidence."
        ),
        "falsifier": (
            "phys10-m20 <= phys10-m10 and |phys10-m10 - phys10-m10lo| < 0.003 on the blind control, or all three "
            "arms |live delta| < 0.01: then the km-scale potential-field prior carries no usable order "
            "information and CONCENTRATION closes on both parents."
        ),
        "confounder": (
            "Support widening is inseparable from the treatment: because the parent is saturated, hot-block "
            "receivers necessarily leave the H19-5 support. The mirror arm holds that constant and flips only the "
            "prior, so phys10-m10 - phys10-m10lo is the prior effect and phys10-m20 - phys10-m10 is the dose."
        ),
        "measured_after_build_REPORT_ONLY": stats,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def append_ledger_rows(rows: list[dict]) -> None:
    """Idempotently replace this family's rows; keep every other line byte-identical."""
    our = {(r["parent"], r["axis"], r["value"]) for r in rows}
    kept: list[str] = []
    header = None
    if LEDGER.is_file():
        raw = LEDGER.read_text().splitlines()
        header = raw[0] if raw else None
        for line in raw[1:]:
            if not line.strip():
                continue
            parsed = next(csv.reader([line]))
            if len(parsed) > 3 and (parsed[1], parsed[2], parsed[3]) in our:
                continue
            kept.append(line)
    if header is None:
        header = ",".join(LEDGER_COLUMNS)
    buf = [header, *kept]
    out = []
    import io

    sink = io.StringIO()
    writer = csv.DictWriter(sink, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
    for line in buf[1:]:
        parsed = next(csv.reader([line]))
        row = {k: (parsed[i] if i < len(parsed) else "") for i, k in enumerate(LEDGER_COLUMNS)}
        out.append(row)
    for r in rows:
        out.append({k: str(r.get(k, "")) for k in LEDGER_COLUMNS})
    writer.writeheader()
    for row in out:
        writer.writerow(row)
    LEDGER.write_text(sink.getvalue())


def main() -> int:
    t0 = time.time()
    print("[1/8] Verifying SHA-256 manifest pins...")
    verified = bp.verify_manifest()
    print(f"      Verified {len(verified)} pins.")

    print("[2/8] Rebuilding R0 from the pinned lineage (byte-exact)...")
    lin = bp.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat, h19, r0 = lin["foot"], lin["catalogue"], lin["d_cat"], lin["h19_5"], lin["r0"]
    print(f"      R0 {int(r0.sum()):,} dots | zeros={lin['rebuilt_zeros_sha256'][:12]}... | "
          f"nan={lin['rebuilt_nan_sha256'][:12]}...")

    print("[3/8] Building the label-free field w + leakage canaries...")
    w, canaries = bp.build_physical_field_and_canaries(verified, foot, catalogue, h19)
    print(f"      Canaries PASS (max sym AUC {max(canaries.values()):.5f}, trip line 0.90)")

    print("[4/8] Reconstructing parent R1 and asserting both published SHA-256 values...")
    r1 = bsp.reconstruct_r1(lin, w, verified["sample_submission"])
    print(f"      R1 {int(r1.sum()):,} dots | min d_cat {d_cat[r1].min():.4f} px | hashes match")

    print("[5/8] Label-free 1 km block prior (bands 3/5/18) ...")
    prior, band_names, prior_meta = structural_prior(verified["training_features"], foot)
    tables = block_tables(foot, prior)
    elig = tables["eligible"]
    ep = tables["block_prior"][elig]
    hi_cut = float(np.quantile(ep, 0.70))
    lo_cut = float(np.quantile(ep, 0.30))
    high_blocks = elig[ep >= hi_cut]
    low_blocks = elig[ep <= lo_cut]
    print(f"      eligible full 1 km blocks: {len(elig):,} | high set {len(high_blocks):,} "
          f"(cut {hi_cut:.4f}) | low set {len(low_blocks):,} (cut {lo_cut:.4f})")

    cv_before = {f"{b}px": block_density_cv(r1, foot, b) for b in (5, 10, 20, 50)}
    parent_pts = np.column_stack(np.nonzero(r1)).astype(np.float64)
    blocked_surv = spacing_blocked_mask(parent_pts.astype(int), foot.shape) | r1
    cands: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for pole, blocks in (("high", high_blocks), ("low", low_blocks)):
        cy, cx = receiver_candidates(blocks, foot, catalogue, d_cat, r1, blocked_surv,
                                     prior, tables, pole)
        cands[pole] = (cy, cx)
        print(f"      receiver candidates ({pole}-prior blocks): {len(cy):,}")

    print("[6/8] Allocating the three arms (shared low->high donors; mirror shares donors)...")
    donors_hi = choose_donors(r1, prior, tables, int(round(0.10 * N_PARENT_DOTS)), "high")
    survivors_hi = r1 & ~donors_hi
    n_hi = int(donors_hi.sum())
    donors_hi20 = choose_donors(r1, prior, tables, int(round(0.20 * N_PARENT_DOTS)), "high")
    survivors_hi20 = r1 & ~donors_hi20
    n_hi20 = int(donors_hi20.sum())
    print(f"      donors: 10% arm {n_hi:,} | 20% arm {n_hi20:,} (nested: "
          f"{int((donors_hi & ~donors_hi20).sum())} of the 10% set inside the 20% set)")

    built = []
    for value, (frac, pole) in ARMS.items():
        donors = donors_hi20 if frac == 0.20 else donors_hi
        survivors = r1 & ~donors
        n_move = int(donors.sum())
        surv_pts = np.column_stack(np.nonzero(survivors)).astype(int)
        blocked = spacing_blocked_mask(surv_pts, foot.shape) | survivors
        # candidates must also clear the surviving dots, not just the full parent
        cy, cx = cands[pole]
        mask = survivors.copy()
        placed = greedy_place(cy, cx, blocked, d_cat, n_move)
        mask |= placed
        assert int(mask.sum()) == N_DOTS
        # Hard structural checks before any file is written.
        land = mask & ~survivors
        assert not np.any(land & catalogue)
        assert d_cat[land].min() > MIN_CATALOGUE_PX
        from scipy.spatial import cKDTree

        sp = np.column_stack(np.nonzero(survivors)).astype(np.float64)
        ly, lx = np.nonzero(land)
        land_pts = np.column_stack([ly, lx]).astype(np.float64)
        d_surv = cKDTree(sp).query(land_pts, k=1)[0]
        d_receiver = cKDTree(land_pts).query(land_pts, k=2)[0][:, 1]
        don_pts = np.column_stack(np.nonzero(donors)).astype(np.float64)
        d_move = cKDTree(land_pts).query(don_pts, k=1)[0]
        assert d_surv.min() >= SPACING_PX - 1e-9, f"spacing lock violated: {d_surv.min()}"
        assert d_receiver.min() >= SPACING_PX - 1e-9, f"receiver spacing violated: {d_receiver.min()}"
        donor_bid = tables["block_id"][np.nonzero(donors)]
        rec_bid = tables["block_id"][ly, lx]
        stats = {
            "n_moved": n_move,
            "pct_of_parent_dots_moved": round(100.0 * n_move / N_PARENT_DOTS, 3),
            "n_receivers": int(land.sum()),
            "receivers_on_h19_5_support": int((land & h19).sum()),
            "receivers_off_h19_5_support_frac": round(float((~h19[ly, lx]).mean()), 4),
            "min_receiver_dist_to_survivor_px": round(float(d_surv.min()), 4),
            "min_receiver_to_receiver_px": round(float(d_receiver.min()), 4),
            "mean_donor_to_nearest_receiver_px": round(float(d_move.mean()), 4),
            "median_donor_to_nearest_receiver_px": round(float(np.median(d_move)), 4),
            "min_d_cat_px": round(float(d_cat[mask].min()), 4),
            "donor_block_prior_mean": round(float(np.nanmean(tables["block_prior"][donor_bid])), 6),
            "receiver_block_prior_mean": round(float(np.nanmean(tables["block_prior"][rec_bid])), 6),
            "block_cv_before": cv_before,
            "block_cv_after": {f"{b}px": block_density_cv(mask, foot, b) for b in (5, 10, 20, 50)},
            "nn_parent": bsp.nn_stats(r1),
            "nn_variant": bsp.nn_stats(mask),
        }
        built.append((value, mask, stats))
        print(f"      {value}: moved {n_move:,} ({stats['pct_of_parent_dots_moved']:.2f}%), "
              f"receivers on H19-5 support {stats['receivers_on_h19_5_support']:,}, "
              f"min d_cat {stats['min_d_cat_px']:.4f}")

    print("[7/8] Writing rasters through the hardened gate + disk re-read...")
    existing_shas = {bp.PARENT_SHA_ZEROS, bp.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS}
    # Idempotent rerun: this family's own rows must not count as collisions, but every
    # other row must (brief section 6: dedupe on exact hash).
    our_triples = {(R1_ID, "CONCENTRATION", v) for v in ARMS}
    if LEDGER.is_file():
        for row in csv.DictReader(LEDGER.open()):
            if (row.get("parent"), row.get("axis"), row.get("value")) in our_triples:
                continue
            for k in ("sha256", "sha256_zeros"):
                if row.get(k):
                    existing_shas.add(row[k])
    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    our_values = set(ARMS)
    cards = {k: v for k, v in cards.items()
             if not any(k.startswith(f"{R1_ID}-CONCENTRATION{v}-") for v in our_values)}
    for stale in RELEASES.glob(f"{R1_ID}-CONCENTRATION*"):
        our = any(f"-CONCENTRATION{v}-" in stale.name for v in our_values)
        if our:
            stale.unlink()

    notes = {
        "phys10-m10": "R1 6f7ae705; CONC 10% cold->hottest 1km blocks, >=2.8px spacing lock, 37654 dots; pred +0.005 MODEL",
        "phys10-m20": "R1 6f7ae705; CONC 20% cold->hottest 1km blocks, >=2.8px spacing lock, 37654 dots; pred +0.009 MODEL",
        "phys10-m10lo": "R1 6f7ae705; CONC 10% cold->COLDEST 1km blocks (mirror control), 37654 dots; pred -0.005 MODEL",
    }
    descriptions = {
        "phys10-m10": "Relocate 3,765 dots (10.00%) from the lowest-prior to the highest-prior 1 km (10 px) blocks on the TMI/gravity prior; every receiver >=2.8 px from all survivors; count fixed at 37,654.",
        "phys10-m20": "Same rule at 20.00% dose (7,531 dots), nested inside the 10% donor set, to test whether the prior effect is monotone in dose.",
        "phys10-m10lo": "Mirror control: the SAME 3,765 donors as phys10-m10, relocated into the lowest-prior 1 km blocks, holding support-widening and displacement magnitude constant.",
    }
    recommendations = {
        "phys10-m10": "HOLD-CONDITIONAL: gate-clean and spendable once a parent R1 receipt exists. Its value is that it makes CONCENTRATION testable at all (all four R0 rows are HOLD).",
        "phys10-m20": "HOLD-CONDITIONAL: dose arm; only interpretable against phys10-m10 on the same receipt pair.",
        "phys10-m10lo": "HOLD / mirror control: never a slot; it exists to separate the prior effect from support widening.",
    }
    ranking_basis = ("Mean robust-unit TMI/gravity gradient (provided bands 3,5,18) averaged over each fully "
                     "inside 10x10 px (1 km) block; donors = coldest blocks, lowest local prior first; receivers "
                     "= hottest (or coldest for the mirror) blocks, empty blocks first, local prior descending; "
                     ">=2.8 px spacing lock on every receiver. No label, no SGMC, no withheld pixel.")

    ledger_rows = []
    arms_for_instruments = {bp.PARENT_ID: r0, R1_ID: r1}
    for value, mask, stats in built:
        rec = bp.write_and_verify_variant(
            mask=mask, foot=foot, catalogue=catalogue, sample_path=verified["sample_submission"],
            releases_dir=RELEASES, parent_mask=r1, axis="CONCENTRATION", value=value,
            note_template=notes[value], existing_shas=existing_shas, parent_id=R1_ID,
            parent_sha_zeros=R1_SHA_ZEROS, parent_sha_nan=R1_SHA_NAN, date=DATE,
            min_catalogue_px=MIN_CATALOGUE_PX,
        )
        existing_shas.update({rec["sha256"], rec["sha256_zeros"]})
        arms_for_instruments[rec["id"]] = mask
        pred, pred_range = PREDICTIONS[value]
        rec["concentration_statistics"] = stats
        rec["prior"] = prior_meta
        rec["preregistration"] = "registry/preregistration_concentration_r1.json"
        rec["parent_rebuild_verified"] = {
            "R0_sha256_zeros": lin["rebuilt_zeros_sha256"],
            "R0_sha256_nan": lin["rebuilt_nan_sha256"],
            "R1_sha256_nan": R1_SHA_NAN, "R1_sha256_zeros": R1_SHA_ZEROS,
        }
        rec["leakage_canaries"] = {"passed": True, "max_symmetric_auc": max(canaries.values()),
                                   "channels": canaries}
        rec["predicted_change"] = f"MODEL:{pred} vs parent R1 (live, preregistered)"
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        cards[rec["id"]] = mechanism_card(value, stats["n_moved"], stats["pct_of_parent_dots_moved"], stats)
        ledger_rows.append({
            "id": rec["id"], "parent": R1_ID, "axis": "CONCENTRATION", "value": value,
            "n_dots": rec["n_dots"], "pct_changed": f"{stats['pct_of_parent_dots_moved']:.2f}",
            "sha256": rec["sha256"], "sha256_zeros": rec["sha256_zeros"], "status": "BUILT",
            "predicted_change": f"MODEL:{pred}", "predicted_range": pred_range,
            "ranking_basis": ranking_basis, "receipt_score": "", "receipt_date": "",
            "description": descriptions[value], "recommendation": recommendations[value],
        })
        print(f"      {rec['id']} | sha {rec['sha256'][:12]}... | note {rec['form_note_chars']} chars")

    print("[8/8] REPORT-ONLY instruments (blind SGMC, holdout, field w, block CV)...")
    ev = bp.evaluate_report_only_instruments(
        arms=arms_for_instruments, foot=foot, catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"])
    r1_sgmc = ev[R1_ID]["sgmc_control"]["dti"]
    w_parent = float(bp.weighted_expected_dti(r1, w)["dti"])
    report = {"schema": "gems88.concentration-r1-axis-report.v1", "parent": R1_ID,
              "r1_sgmc_PROXY": r1_sgmc, "r0_sgmc_PROXY": ev[bp.PARENT_ID]["sgmc_control"]["dti"],
              "w_weighted_dti_R1_MODEL": round(w_parent, 6), "arms": {}}
    for value, mask, stats in built:
        vid = next(r["id"] for r in ledger_rows if r["value"] == value)
        d = ev[vid]
        d["sgmc_delta_vs_R1_PROXY"] = round(d["sgmc_control"]["dti"] - r1_sgmc, 6)
        d["w_weighted_dti_MODEL"] = round(float(bp.weighted_expected_dti(mask, w)["dti"]), 6)
        d["w_delta_vs_R1_MODEL"] = round(d["w_weighted_dti_MODEL"] - w_parent, 6)
        d["holdout_note"] = ("Degenerate (0.000000) for every >3 px file: the 3 px kernel can earn no credit "
                             "on hidden catalogue pixels (IR-88-20). Reported for completeness only.")
        d["concentration_statistics"] = stats
        report["arms"][vid] = d
        print(f"      {value}: SGMC {d['sgmc_control']['dti']:.6f} "
              f"({d['sgmc_delta_vs_R1_PROXY']:+.6f} vs R1) | w-DTI delta {d['w_delta_vs_R1_MODEL']:+.6f}")
        cards[vid]["post_build_report_only"] = (
            f"Preregistered MODEL {PREDICTIONS[value][0]} is unchanged and is the prediction. Measured after "
            f"build (REPORT ONLY, never a gate): blind SGMC {d['sgmc_control']['dti']:.6f} PROXY "
            f"({d['sgmc_delta_vs_R1_PROXY']:+.6f} vs R1 {r1_sgmc:.6f}); w-weighted DTI "
            f"{d['w_delta_vs_R1_MODEL']:+.6f} MODEL. w is defined on H19-5 support and is structurally blind to "
            f"off-support placement (AUC 0.47, IR-88-38), so its sign is a confounder check, not evidence.")

    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")
    append_ledger_rows(ledger_rows)
    print(f"      report -> {REPORT.relative_to(ROOT)} | cards+ledger updated | {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
