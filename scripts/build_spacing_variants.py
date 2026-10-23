#!/usr/bin/env python3
"""Build and validate controlled AXIS=SPACING variants of parent R1 = PRUNEp3px.

Preregistered in ``registry/spacing_preregistration.json`` (predictions fixed
before any variant PROXY was computed). Zero DrivenData/Dropbox contact.

Why R1 and not R0
-----------------
Brief v2 section 4.4 requires >=3 px from the catalogue for every non-PRUNE
axis. ``R0 = h33-h33-2-b2`` keeps 2,171 dots at ``2 < d_cat <= 3 px``, so a
SPACING edit of R0 would inherit an unspendable collar (IR-88-33 precedent).
R0 is additionally already perfect Poisson-disk 2.8 px spacing (min NN
2.8284 px), so it offers no spacing defect to repair. ``R1`` carries a
1,914-dot greedy-decluster spacing defect (min NN 1.0 px) and is gate-clean
(``min d_cat = 3.162 px``). This script rebuilds R1 from the pinned lineage
and asserts BOTH published SHA-256 values before touching it.

What SPACING does
-----------------
All three arms share ONE geometry-defined donor set (greedy minimal
decluster: 1,914 dots, 5.08%) and differ ONLY in receiver geometry on the
same 59,310-pixel pool (un-emitted H19-5 ridge pixels at d_cat > 3 px, donor
sites excluded), at strictly fixed count (37,654). No physics field, no band,
no label is used for any ranking decision:

  * poisson28:  greedy farthest-point completion (maximally uniform feasible set)
  * lattice4px: nearest-to-4px-lattice receivers (strand-agnostic regularity)
  * strike:     along-strike receivers (H19-5 structure-tensor alignment)

MUST gates per Brief section 6; hide-and-recover (degenerate for >3 px
files), SGMC control, block CV and leakage canaries are REPORT ONLY.
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
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score

import build_prune_variants as bp

ROOT = bp.ROOT
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
REPORT = ROOT / "evidence" / "spacing_axis_report.json"

R1_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
R1_SHA_NAN = "6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9"
R1_SHA_ZEROS = "dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f"
N_DOTS = 37_654
MIN_CATALOGUE_PX = 3.0
DECLUSTER_PX = 2.8
LATTICE_PX = 4
RECEIVER_EXCLUSION_PX = 1.5
N_DONORS_PINNED = 1_914  # geometry-determined from the pinned lineage; asserted

OUR_VALUES = {"poisson28", "lattice4px", "strike"}
# value, preregistered MODEL prediction vs R1, predicted range
VARIANTS = [
    ("poisson28", "+0.003", "[-0.005,+0.011]"),
    ("lattice4px", "-0.004", "[-0.013,+0.005]"),
    ("strike", "+0.000", "[-0.008,+0.008]"),
]

REFERENCES = [
    {"claim": "Competition DTI metric/format (supplied by human brief; not fetched by agent)",
     "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"},
    {"claim": "Organizer: known faults masked pixel-exactly; new-fault truth may lie within 300 m of known traces (supplied by human brief; not fetched)",
     "url": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516"},
    {"claim": "USGS GeoDAWN Area 2 acquisition (400 m lines, 150-200 m drape) context (supplied by human brief; not fetched)",
     "url": "https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7"},
    {"claim": "USGS SGMC source for the report-only off-catalogue control (manifest source_url)",
     "url": "https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d"},
]


# ---------------------------------------------------------------------------
# Spacing primitives (unit-tested in tests/test_spacing_axis.py)
# ---------------------------------------------------------------------------

DECLUSTER_OFFSETS = tuple(
    (dy, dx)
    for dy in range(-2, 3)
    for dx in range(-2, 3)
    if 0 < dy * dy + dx * dx < DECLUSTER_PX * DECLUSTER_PX
)


def greedy_declutter(parent_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Minimal greedy decluster: remove dots with a surviving neighbour <2.8 px.

    Dots are visited in ascending nearest-neighbour order (stable sort, so
    ties break row-major). Each visited dot still alive is removed iff any of
    the 20 sub-2.8-px neighbour offsets still holds a live dot. Returns
    (donor_mask, survivor_mask). Deterministic; no RNG.
    """
    parent = np.asarray(parent_mask, dtype=bool)
    H, W = parent.shape
    pts = np.column_stack(np.nonzero(parent)).astype(np.float64)
    if len(pts) == 0:
        return np.zeros_like(parent), parent.copy()
    nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    order = np.argsort(nn, kind="stable")
    alive = parent.copy()
    donors = np.zeros_like(parent)
    ys = pts[order, 0].astype(int)
    xs = pts[order, 1].astype(int)
    for y, x in zip(ys.tolist(), xs.tolist()):
        if not alive[y, x]:
            continue
        for dy, dx in DECLUSTER_OFFSETS:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and alive[yy, xx]:
                alive[y, x] = False
                donors[y, x] = True
                break
    return donors, alive


def h19_strike_field(h19: np.ndarray, sigma: float = 1.5) -> tuple[np.ndarray, np.ndarray]:
    """Along-structure angle + coherence of the H19-5 ridge support.

    Structure tensor of the Gaussian-smoothed binary support; the angle is the
    minor-eigenvector direction (along the ridge). Deterministic.
    """
    sm = gaussian_filter(np.asarray(h19, dtype=np.float32), sigma)
    gy, gx = np.gradient(sm)
    jxx = gaussian_filter(gx * gx, sigma)
    jyy = gaussian_filter(gy * gy, sigma)
    jxy = gaussian_filter(gx * gy, sigma)
    angle = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy) + np.pi / 2.0
    coh = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy**2) / np.maximum(jxx + jyy, 1e-12)
    return angle.astype(np.float32), coh.astype(np.float32)


def strike_alignment(
    cand_y: np.ndarray,
    cand_x: np.ndarray,
    angle: np.ndarray,
    surv_tree: cKDTree,
    surv_y: np.ndarray,
    surv_x: np.ndarray,
) -> np.ndarray:
    """|cos| between (candidate -> nearest survivor) and local strike (1 = along)."""
    _, idx = surv_tree.query(np.column_stack([cand_y, cand_x]).astype(np.float64), k=1)
    vec = np.arctan2(cand_y - surv_y[idx], cand_x - surv_x[idx])
    return np.abs(np.cos(vec - angle[cand_y, cand_x])).astype(np.float64)


def lattice_distance(cand_y: np.ndarray, cand_x: np.ndarray, period: int = LATTICE_PX) -> np.ndarray:
    """Euclidean distance to the nearest period-px lattice node (phase 0,0)."""
    dy = np.minimum(cand_y % period, period - (cand_y % period))
    dx = np.minimum(cand_x % period, period - (cand_x % period))
    return np.sqrt(dy * dy + dx * dx).astype(np.float64)


def poisson_farthest_point(
    cand_y: np.ndarray, cand_x: np.ndarray, d0: np.ndarray, n: int
) -> list[int]:
    """Greedy farthest-point picks: argmax distance to survivors+picked.

    ``d0`` is each candidate's distance to the survivor set. First-index
    tie-break (np.argmax). Deterministic; no RNG.
    """
    dmin = np.asarray(d0, dtype=np.float64).copy()
    avail = np.ones(len(cand_y), dtype=bool)
    chosen: list[int] = []
    for _ in range(n):
        masked = np.where(avail, dmin, -1.0)
        if masked.max() < 0:
            raise ValueError(f"pool exhausted after {len(chosen)} poisson picks (need {n})")
        b = int(np.argmax(masked))
        chosen.append(b)
        avail[b] = False
        dd = np.sqrt((cand_y - cand_y[b]) ** 2 + (cand_x - cand_x[b]) ** 2)
        dmin = np.minimum(dmin, dd)
    return chosen


def ranked_greedy_pick(
    order: np.ndarray,
    cand_y: np.ndarray,
    cand_x: np.ndarray,
    shape: tuple[int, int],
    n: int,
    exclusion_px: float = RECEIVER_EXCLUSION_PX,
) -> list[int]:
    """Walk ``order`` greedily, skipping candidates within exclusion of picked."""
    H, W = shape
    taken = np.zeros((H, W), dtype=bool)
    r = int(np.ceil(exclusion_px))
    chosen: list[int] = []
    for b in order.tolist():
        if len(chosen) >= n:
            break
        y, x = int(cand_y[b]), int(cand_x[b])
        y0, y1 = max(0, y - r), min(H, y + r + 1)
        x0, x1 = max(0, x - r), min(W, x + r + 1)
        win = taken[y0:y1, x0:x1]
        if win.any():
            wy, wx = np.nonzero(win)
            if np.any((wy + y0 - y) ** 2 + (wx + x0 - x) ** 2 < exclusion_px**2):
                continue
        chosen.append(b)
        taken[y, x] = True
    if len(chosen) < n:
        raise ValueError(f"pool exhausted after {len(chosen)} ranked picks (need {n})")
    return chosen


def nn_stats(mask: np.ndarray) -> dict:
    pts = np.column_stack(np.nonzero(mask)).astype(np.float64)
    nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    return {
        "min_nn_px": round(float(nn.min()), 4),
        "median_nn_px": round(float(np.median(nn)), 4),
        "mean_nn_px": round(float(nn.mean()), 4),
        "frac_nn_lt_2p8": round(float((nn < 2.8).mean()), 4),
    }


def spacing_shift_stats(
    parent: np.ndarray,
    variant: np.ndarray,
    h19: np.ndarray,
    surv_tree: cKDTree,
    angle: np.ndarray,
    surv_y: np.ndarray,
    surv_x: np.ndarray,
    w: np.ndarray,
) -> dict:
    """Post-allocation spacing diagnostics (REPORT ONLY; geometry + wDTI MODEL)."""
    donors = parent & ~variant
    receivers = variant & ~parent
    ry, rx = np.nonzero(receivers)
    d_rec, _ = surv_tree.query(np.column_stack([ry, rx]).astype(np.float64), k=1)
    lat = lattice_distance(ry, rx)
    ali = strike_alignment(ry, rx, angle, surv_tree, surv_y, surv_x)
    tree_v = cKDTree(np.column_stack(np.nonzero(variant)).astype(np.float64))
    d_don, _ = tree_v.query(np.column_stack(np.nonzero(donors)).astype(np.float64), k=1)

    def support_coverage(mask: np.ndarray) -> float:
        d = distance_transform_edt(~mask)
        return round(float(((d <= 3.0) & h19).sum() / max(int(h19.sum()), 1)), 4)

    w_before = round(float(bp.weighted_expected_dti(parent, w)["dti"]), 6)
    w_after = round(float(bp.weighted_expected_dti(variant, w)["dti"]), 6)
    return {
        "n_donors": int(donors.sum()),
        "n_receivers": int(receivers.sum()),
        "receiver_dist_to_survivor_px": {
            "median": round(float(np.median(d_rec)), 3),
            "frac_ge_2p8": round(float((d_rec >= 2.8).mean()), 4),
            "frac_le_1p5": round(float((d_rec <= 1.5).mean()), 4),
        },
        "receiver_lattice_dist_px": {
            "median": round(float(np.median(lat)), 3),
            "frac_on_node": round(float((lat == 0.0).mean()), 4),
        },
        "receiver_strike_align": {
            "median": round(float(np.median(ali)), 4),
            "frac_gt_0p9": round(float((ali > 0.9).mean()), 4),
        },
        "donor_dist_to_variant_after_px": {
            "median": round(float(np.median(d_don)), 3),
            "frac_gt_3": round(float((d_don > 3.0).mean()), 4),
        },
        "h19_support_within_3px_parent": support_coverage(parent),
        "h19_support_within_3px_variant": support_coverage(variant),
        "w_weighted_dti_before": w_before,
        "w_weighted_dti_after": w_after,
        "w_weighted_dti_delta_MODEL": round(w_after - w_before, 6),
    }


# ---------------------------------------------------------------------------
# Parent R1 reconstruction with published-hash assertion
# ---------------------------------------------------------------------------


def reconstruct_r1(lin: dict, w: np.ndarray, sample_path: Path) -> np.ndarray:
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
# Geometric-score leakage canary (REPORT ONLY; trip = stop and investigate)
# ---------------------------------------------------------------------------


def spacing_canary(
    foot: np.ndarray,
    catalogue: np.ndarray,
    surv_dist_field: np.ndarray,
    lattice_field: np.ndarray,
    strike_field: np.ndarray,
) -> dict[str, float]:
    """Symmetric AUC of the three spacing geometry fields on hidden positives.

    Mirrors the canary design in build_prune_variants (folds seeds 20/30,
    first-fold hidden positives, 100k footprint negatives, SEED=20261023).
    Spacing geometry is label-blind by construction; this only checks the
    >0.90 trip line from Brief section 6.
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
    for name, field in (
        ("spacing_survivor_distance", surv_dist_field.ravel().astype(np.float64)),
        ("spacing_lattice_distance", lattice_field.ravel().astype(np.float64)),
        ("spacing_strike_alignment", strike_field.ravel().astype(np.float64)),
    ):
        auc = float(roc_auc_score(y, field[idx]))
        sym = round(float(max(auc, 1.0 - auc)), 5)
        if sym > 0.90:
            raise RuntimeError(f"LEAKAGE CANARY TRIPPED on {name}: symmetric AUC {sym} > 0.90")
        out[name] = sym
    return out


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

    print("[3/7] Building parent corroboration field w + canaries (R1 rebuild + wDTI MODEL)...")
    w, canaries = bp.build_physical_field_and_canaries(verified, foot, catalogue, h19)
    print(f"      Canaries PASS ({len(canaries)} channels; max sym AUC = {max(canaries.values()):.5f})")

    print("[4/7] Reconstructing parent R1 and asserting published SHA-256 (both twins)...")
    r1 = reconstruct_r1(lin, w, verified["sample_submission"])
    print(f"      R1 OK: {int(r1.sum()):,} dots, min d_cat = {d_cat[r1].min():.4f} px, hashes match.")

    print("[5/7] Greedy decluster donors + H19-5 strike field + receiver pools...")
    donors, surv = greedy_declutter(r1)
    n_shift = int(donors.sum())
    if n_shift != N_DONORS_PINNED:
        raise RuntimeError(f"decluster donors {n_shift} != preregistered {N_DONORS_PINNED}; STOP")
    surv_pts = np.column_stack(np.nonzero(surv)).astype(np.float64)
    surv_tree = cKDTree(surv_pts)
    surv_min_nn = float(surv_tree.query(surv_pts, k=2)[0][:, 1].min())
    assert surv_min_nn >= DECLUSTER_PX, f"survivors min NN {surv_min_nn} < {DECLUSTER_PX}"
    angle, coh = h19_strike_field(h19)
    pool = h19 & ~r1 & (d_cat > 3.0)
    py, px = np.nonzero(pool)
    py64, px64 = py.astype(np.int64), px.astype(np.int64)
    d_pool, _ = surv_tree.query(np.column_stack([py64, px64]).astype(np.float64), k=1)
    lat_pool = lattice_distance(py64, px64)
    sy, sx = np.nonzero(surv)
    ali_pool = strike_alignment(py64, px64, angle, surv_tree, sy, sx)
    print(f"      donors={n_shift} ({100.0*n_shift/N_DOTS:.2f}%), survivors min NN={surv_min_nn:.4f} px, "
          f"pool={int(pool.sum())}, spaced slots(>=2.8px)={int((d_pool>=2.8).sum())}")

    print("      spacing geometry canary (label-blind check, REPORT ONLY)...")
    H, W = foot.shape
    fy, fx = np.nonzero(foot)
    fpts = np.column_stack([fy, fx]).astype(np.float64)
    surv_dist_field = np.zeros((H, W), dtype=np.float32)
    surv_dist_field[foot] = surv_tree.query(fpts, k=1)[0].astype(np.float32)
    rr, cc = np.mgrid[0:H, 0:W]
    lattice_field = np.where(
        foot,
        np.sqrt(np.minimum(rr % LATTICE_PX, LATTICE_PX - rr % LATTICE_PX) ** 2
                + np.minimum(cc % LATTICE_PX, LATTICE_PX - cc % LATTICE_PX) ** 2),
        0.0,
    ).astype(np.float32)
    _, f_nn = surv_tree.query(fpts, k=1)
    strike_field = np.zeros((H, W), dtype=np.float32)
    strike_field[foot] = np.abs(np.cos(
        np.arctan2(fy - sy[f_nn], fx - sx[f_nn]) - angle[fy, fx])).astype(np.float32)
    spacing_canaries = spacing_canary(foot, catalogue, surv_dist_field, lattice_field, strike_field)
    print(f"      spacing canaries {spacing_canaries} (trip line 0.90)")

    # Idempotent rerun: replace ONLY this family's ledger rows/files/cards.
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
            if row.get("axis") == "SPACING" and row.get("parent") == R1_ID and row.get("value") in OUR_VALUES:
                continue
            ledger_rows.append(row)
            for k in ("sha256", "sha256_zeros"):
                if row.get(k):
                    existing_shas.add(row[k])
        raw_lines = LEDGER.read_text().splitlines()
        header_line = raw_lines[0] if raw_lines else ""
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if len(parsed) > 3 and parsed[2] == "SPACING" and parsed[1] == R1_ID and parsed[3] in OUR_VALUES:
                continue
            raw_kept.append(line)
    for _v in OUR_VALUES:
        for stale in RELEASES.glob(f"{R1_ID}-SPACING{_v}-*"):
            stale.unlink()
    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    cards = {k: v for k, v in cards.items()
             if not any(k.startswith(f"{R1_ID}-SPACING{_v}-") for _v in OUR_VALUES)}

    print("[6/7] Allocating 3 SPACING variants (shared donors, geometry-only receivers)...")
    arms: dict[str, np.ndarray] = {bp.PARENT_ID: r0, R1_ID: r1}
    built = []
    parent_nn = nn_stats(r1)
    notes = {
        "poisson28": "R1(6f7ae705); SPACING poisson farthest-point 5.08% (1914) on H19-5, 37654, >3px; pred +0.003 MODEL",
        "lattice4px": "R1(6f7ae705); SPACING 4px-lattice receivers 5.08% (1914) on H19-5, 37654, >3px; pred -0.004 MODEL",
        "strike": "R1(6f7ae705); SPACING along-strike receivers 5.08% (1914) on H19-5, 37654, >3px; pred +0.000 MODEL",
    }
    ranking_basis = (
        "Geometry only, no physics field: shared greedy-decluster donors (1,914 dots with a "
        "surviving neighbour <2.8 px); receivers ranked on un-emitted H19-5 at d_cat>3 px by "
        "farthest-point distance (poisson28), 4 px lattice proximity phase (0,0) (lattice4px), or "
        "H19-5 structure-tensor along-strike |cos| (strike)"
    )
    receiver_sets: dict[str, set[int]] = {}
    for value, pred, pred_range in VARIANTS:
        if value == "poisson28":
            picks = poisson_farthest_point(py64, px64, d_pool, n_shift)
        elif value == "lattice4px":
            order = np.lexsort((px64, py64, lat_pool))
            picks = ranked_greedy_pick(order, py64, px64, (H, W), n_shift)
        else:
            order = np.lexsort((px64, py64, -ali_pool))
            picks = ranked_greedy_pick(order, py64, px64, (H, W), n_shift)
        receiver_sets[value] = set(picks)
        mask = surv.copy()
        mask[py[np.array(picks)], px[np.array(picks)]] = True
        assert int(mask.sum()) == N_DOTS
        stats = spacing_shift_stats(r1, mask, h19, surv_tree, angle, sy, sx, w)
        stats["nn_parent_R1"] = parent_nn
        stats["nn"] = nn_stats(mask)
        rec = bp.write_and_verify_variant(
            mask=mask, foot=foot, catalogue=catalogue,
            sample_path=verified["sample_submission"], releases_dir=RELEASES,
            parent_mask=r1, axis="SPACING", value=value,
            note_template=notes[value], existing_shas=existing_shas,
            parent_id=R1_ID, parent_sha_zeros=R1_SHA_ZEROS, parent_sha_nan=R1_SHA_NAN,
            date=bp.FIXED_DATE, min_catalogue_px=MIN_CATALOGUE_PX,
        )
        existing_shas.update({rec["sha256"], rec["sha256_zeros"]})
        rec["spacing_statistics"] = stats
        rec["spacing_definition"] = {
            "donors": "greedy minimal decluster (ascending NN, 20 sub-2.8px offsets), 1,914 dots",
            "receiver_pool": "H19-5 & ~R1 & d_cat>3 px (donor sites excluded)",
            "pool_px": int(pool.sum()),
            "preregistration": "registry/spacing_preregistration.json",
        }
        rec["parent_rebuild_verified"] = {"R0_sha256_zeros": lin["rebuilt_zeros_sha256"],
                                          "R0_sha256_nan": lin["rebuilt_nan_sha256"],
                                          "R1_sha256_nan": R1_SHA_NAN, "R1_sha256_zeros": R1_SHA_ZEROS}
        rec["leakage_canaries"] = {"passed": True,
                                   "max_symmetric_auc": max(max(canaries.values()),
                                                            max(spacing_canaries.values())),
                                   "channels": canaries, "spacing_geometry": spacing_canaries}
        rec["predicted_change"] = f"MODEL:{pred} vs parent R1 (live, preregistered)"
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        cards[rec["id"]] = mechanism_card(value, stats, pred, pred_range)
        arms[rec["id"]] = mask
        built.append((rec, stats, pred, pred_range))
        print(f"      {value}: donors={n_shift} wDTI delta={stats['w_weighted_dti_delta_MODEL']:+.6f} "
              f"-> {rec['id']}")
    ov = {f"{a}&{b}": len(receiver_sets[a] & receiver_sets[b])
          for a in OUR_VALUES for b in OUR_VALUES if a < b}
    print(f"      pairwise receiver overlap (of {n_shift}): {ov}")

    print("[7/7] REPORT-ONLY diagnostics (holdout [degenerate >3px], SGMC, block CV)...")
    eval_report = bp.evaluate_report_only_instruments(
        arms=arms, foot=foot, catalogue=catalogue, sgmc_path=verified["sgmc_faults_control"])
    r1_sgmc = eval_report[R1_ID]["sgmc_control"]["dti"]
    descriptions = {
        "poisson28": "Move 1,914 dots (5.08%) from greedy-decluster donors to farthest-point receivers on un-emitted H19-5 at d_cat>3 px (maximally uniform feasible set) at fixed 37,654.",
        "lattice4px": "Move 1,914 dots (5.08%) from greedy-decluster donors to 4 px lattice-anchored receivers on un-emitted H19-5 at d_cat>3 px (strand-agnostic regularity) at fixed 37,654.",
        "strike": "Move 1,914 dots (5.08%) from greedy-decluster donors to along-strike receivers on un-emitted H19-5 at d_cat>3 px (H19-5 structure-tensor |cos|) at fixed 37,654.",
    }
    recommendations = {
        "poisson28": ("HOLD-CONDITIONAL: preregistered MODEL +0.003 vs R1 stands as the experiment prediction. "
                      "Spend a live slot only as a deliberate spacing falsification experiment after the R1 collar "
                      "receipt lands; not an expected-score pick ahead of R1."),
        "lattice4px": ("HOLD / negative control: strand-agnostic regularity is expected to lose (MODEL -0.004). "
                       "Spend only if the human wants the spacing axis closed with receipts."),
        "strike": ("HOLD / line-continuity probe: centered at MODEL +0.000; informative in either direction "
                   "(a win licenses STRIKE_ALIGN, a loss closes anisotropic spacing)."),
    }
    for rec, stats, pred, pred_range in built:
        d = dict(eval_report[rec["id"]])
        d["sgmc_delta_vs_R1_PROXY"] = round(d["sgmc_control"]["dti"] - r1_sgmc, 6)
        d["holdout_note"] = ("Catalogue hide-and-recover is degenerate (0.0) for every >3 px file: "
                             "kernel R=3 px can earn no credit on hidden catalogue pixels (IR-88-20). "
                             "Reported for completeness, cannot rank R1 descendants.")
        rec["report_only_diagnostics"] = d
        cards[rec["id"]]["post_build_report_only"] = (
            f"A-priori preregistered prediction above is unchanged. Measured after build (REPORT ONLY, "
            f"never gates): parent-field w-weighted DTI delta {stats['w_weighted_dti_delta_MODEL']:+.6f} MODEL; "
            f"blind SGMC {d['sgmc_control']['dti']:.6f} PROXY ({d['sgmc_delta_vs_R1_PROXY']:+.6f} vs R1). "
            f"Receivers land at median {stats['receiver_dist_to_survivor_px']['median']:.2f} px from survivors "
            f"({stats['receiver_dist_to_survivor_px']['frac_ge_2p8']:.1%} >=2.8 px); H19-5 within-3px coverage "
            f"{stats['h19_support_within_3px_parent']} -> {stats['h19_support_within_3px_variant']}. "
            f"A live loss cannot cleanly falsify receiver geometry (donor removal forfeits coverage too), "
            f"whereas the pairwise arm ordering tests uniformity vs regularity vs line continuity directly."
        )
        rec["parent_reference_diagnostics"] = eval_report[R1_ID]
        rec["grandparent_reference_diagnostics"] = eval_report[bp.PARENT_ID]
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        ledger_rows.append({
            "id": rec["id"], "parent": R1_ID, "axis": "SPACING", "value": rec["value"],
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
        new_rows = [r for r in ledger_rows if r.get("axis") == "SPACING"
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
        "axis": "SPACING",
        "preregistration": "registry/spacing_preregistration.json",
        "git_sha": bp.git_sha(),
        "seed": bp.SEED,
        "build_script_sha256": bp.sha256_file(Path(__file__).resolve()),
        "elapsed_seconds": round(time.time() - t0, 2),
        "parent_R1": {
            "id": R1_ID, "n_dots": N_DOTS, "sha256_nan": R1_SHA_NAN, "sha256_zeros": R1_SHA_ZEROS,
            "min_d_cat_px": round(float(d_cat[r1].min()), 4), "nn": parent_nn,
            "diagnostics": eval_report[R1_ID],
        },
        "grandparent_R0": {
            "id": bp.PARENT_ID,
            "rebuilt_zeros_sha256": lin["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lin["rebuilt_nan_sha256"],
            "diagnostics": eval_report[bp.PARENT_ID],
        },
        "n_shift": n_shift,
        "receiver_pool_px": int(pool.sum()),
        "receiver_overlap": ov,
        "leakage_canaries": {"passed": True,
                             "max_symmetric_auc": max(max(canaries.values()), max(spacing_canaries.values())),
                             "channels": canaries, "spacing_geometry": spacing_canaries},
        "variants": [dict(r) for r, _s, _p, _pr in built],
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    print("\nSPACING SUMMARY (predictions MODEL vs R1; proxies never scores)")
    for rec, stats, pred, _pr in built:
        d = rec["report_only_diagnostics"]
        print(f"  {rec['value']:10s} pred={pred}  wDTI={stats['w_weighted_dti_delta_MODEL']:+.6f} MODEL  "
              f"SGMC={d['sgmc_control']['dti']:.6f} ({d['sgmc_delta_vs_R1_PROXY']:+.6f} vs R1) PROXY  "
              f"CV12km={d['block_density_cv']['cv_12km_120px_interior']:.4f}  -> {rec['id']}")
    return 0


def mechanism_card(value: str, stats: dict, pred: str, pred_range: str) -> dict:
    common = (f"Count fixed at 37,654 so DTI changes only through kernel credit T and self-credit M "
              f"(DTI = T/(0.2T+0.2(S-M)+0.8|G|), S constant). All three arms share the same 1,914 "
              f"greedy-decluster donors (dots with a surviving neighbour <2.8 px, removed in "
              f"ascending-NN order); survivors recover min NN 2.8284 px. Receivers are 1,914 un-emitted "
              f"H19-5 ridge pixels at d_cat>3 px, donor sites excluded. No band, no physics field, no "
              f"label ranks any dot: the arms differ ONLY in receiver geometry.")
    cards = {
        "poisson28": {
            "hypothesis": "For a structural geologist: the incumbent's 2,171 exact-marginal refills (IR-88-37) landed at min NN 1.0 px, bunching dots onto already-covered strands where their kernels overlap survivors almost completely. Returns accrue per unit of uncovered strand length (IR-88-41), and only 12-17% of H19-5 support per tercile is uncovered - so the maximally uniform feasible receiver set (greedy farthest-point, median 2.236 px from survivors) should recover the most uncovered strand length per moved dot and reverse the measured densification tax (densified adds earn 0.04-0.07 TP vs 0.11-0.16 TP for spaced dots, IR-88-38).",
            "mechanism": common + " Each farthest-point receiver maximises its distance to survivors and to already-placed receivers, so its 3 px triangular kernel overlaps existing coverage the least of any feasible H19-5 pixel. Donor removal forfeits little T (donors sit a median 2.236 px from a survivor whose kernel still covers the donor site), while receivers at >=2.8 px earn full fresh line credit wherever they touch uncovered strand.",
            "non_fault_mimic": "H19-5 ridge support includes non-fault lineaments (fan channels, shorelines, lithologic contacts); uniform coverage spends dots on mimics at exactly the same rate as on faults - this arm tests spacing, not discrimination, and cannot beat a parent whose spacing was already optimal.",
            "predicted_sign_size": f"MODEL predicted live delta {pred} vs parent R1 (range {pred_range}, preregistered in registry/spacing_preregistration.json before any PROXY was computed; |delta|<0.01 live is no evidence). Magnitude kept small because only 366/1,914 receivers reach >=2.8 px spacing - most remain partly densified.",
            "falsifier": "A live RECEIPT <= R1-0.01 falsifies uniformity-as-objective on saturated H19-5 support: either donor removal opened costlier holes than receivers filled, or the parent's exact-marginal refill positions (AUC 0.47, IR-88-38) were load-bearing despite their bunching. A RECEIPT >= R1+0.01 promotes poisson28 as the declustered parent for SUPPORT.",
            "references": REFERENCES,
        },
        "lattice4px": {
            "hypothesis": "Negative control, built to lose: if receiver geometry must follow strand topology to earn line credit, then strand-agnostic regularity - receivers pinned to a 4 px (400 m) square lattice at fixed phase (0,0), median lattice distance 0.0 px - should underperform both strand-aware arms while paying the identical donor-removal cost. It lands at median 1.0 px from survivors (fully densified) because lattice nodes fall where they fall, not where strands run.",
            "mechanism": common + " Lattice proximity ranking ignores H19-5 strand direction, strand tips, and coverage gaps alike; the 1.5 px receiver exclusion keeps the set grid-like rather than strand-like. Any kernel credit it earns comes from accidental strand coincidence, so its T per receiver measures the floor that strand-following geometry must beat.",
            "non_fault_mimic": "The 4 px = 400 m lattice period coincides exactly with the GeoDAWN Area 2 flight-line spacing (brief section 2), so a lattice arm can systematically couple to acquisition-geometry artefacts (leveling seams, line-parallel gridding ripple) if its fixed phase aligns with them - phase (0,0) was frozen in preregistration and never tuned, and any live win must survive a phase-shift control before being trusted.",
            "predicted_sign_size": f"MODEL predicted live delta {pred} vs parent R1 (range {pred_range}, preregistered; |delta|<0.01 live is no evidence). Deliberately the weakest arm: densified placement plus strand-ignorant targeting.",
            "falsifier": "A live RECEIPT >= R1+0.01 for the lattice arm (especially ahead of poisson28) overturns the uncovered-strand model and proves strand-agnostic regularity beats strand-following geometry - the mandatory follow-up is a lattice-phase control (same rule at phase (2,2)) to separate acquisition-geometry coupling from genuine regularity effects.",
            "references": REFERENCES,
        },
        "strike": {
            "hypothesis": "For a structural geologist: where truth is line-like, the marginal bar for a dot drops below the isolated-pixel 0.2*DTI threshold (brief section 2) because neighbours along the line share kernel credit - so receivers placed exactly along local H19-5 strike from their nearest survivor (median |cos| 1.000) should earn multi-pixel line credit T that uniform receivers at the same densification cannot. This arm measures whether line continuity beats uniformity when both are equally densified (median 1.0 px from survivors).",
            "mechanism": common + " The H19-5 structure-tensor strike field (sigma 1.5 px) orients every receiver along its strand; greedy |cos| ranking with 1.5 px exclusion extends strands and fills along-strike gaps rather than thickening strands across strike. Across-strike thickening (the poisson28 failure mode on saturated support) wastes kernel overlap laterally, while along-strike placement pushes coverage toward strand tips and relay gaps where new-fault truth concentrates.",
            "non_fault_mimic": "H19-5 strands bundle fault scarps with non-fault lineaments - fan-head trenches, shoreline benches, joint/foliation traces - and along-strike extension follows mimics exactly as faithfully as faults. At X-intersections the tensor strike is ambiguous (coherence drops), so receivers there follow an averaged direction that may match neither strand.",
            "predicted_sign_size": f"MODEL predicted live delta {pred} vs parent R1 (range {pred_range}, preregistered; |delta|<0.01 live is no evidence). Centered at zero because along-strike adjacency also risks the IR-88-32 bunching failure (adjacent dots on one strand open 4-6 px gaps elsewhere) - this arm measures which effect wins.",
            "falsifier": "A live RECEIPT >= R1+0.01 licenses STRIKE_ALIGN (structure-tensor strike agreement as a selector) over further spacing doses; a RECEIPT <= R1-0.01 with poisson28 neutral-or-better closes anisotropic spacing and confirms uniformity as the spacing objective.",
            "references": REFERENCES,
        },
    }
    return cards[value]


if __name__ == "__main__":
    raise SystemExit(main())
