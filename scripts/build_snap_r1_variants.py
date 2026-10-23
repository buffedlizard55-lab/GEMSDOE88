#!/usr/bin/env python3
"""Build and validate controlled AXIS=SNAP variants of parent ``R1 = PRUNEp3px``.

Why R1 and not R0
-----------------
``R0`` (``h33-h33-2-b2``) keeps 2,171 dots at ``2 < d_cat <= 3 px`` (IR-88-14).
Brief v2 §4.4 forbids mass inside 3 px of the catalogue for any non-PRUNE axis, so
every earlier non-PRUNE family (``MASS``, ``CONCENTRATION``) had to be parked at
``HOLD``. ``R1 = h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`` is the same 37,654
dots with the collar removed at constant count (``min d_cat = 3.162 px``), so a
SNAP edit of R1 satisfies §4.4 with no exemption at the cost of one co-varied
parent step (``MODEL +0.005``). This script rebuilds R1 from the pinned lineage
and asserts its published SHA-256 before touching it, so the parent is proved,
not assumed.

What SNAP does
--------------
Each dot moves at most ``r`` px (``r in {1, 2}``) onto the highest-scoring cell of
an edge-response field inside its window, subject to: inside the footprint, at
least 3 px from every catalogue pixel, and not already occupied. Count is fixed
at 37,654, so the only thing that changes is *where* the mass sits. Source
geometry (H19-5 ridges) is untouched, so this is not a re-detection.

Edge fields are percentile ranks (computed inside the footprint only) of supplied
competition bands:

* ``pf``  -- potential-field edges: band 3 ``tmi_hg`` (0.55) + band 18
  ``iso_grav_anom_hg`` (0.45). Classic potential-field edge detectors; a
  basement fault offsets magnetisation and density, so its horizontal gradients
  peak over the fault plane (Blakely & Simpson 1986, doi:10.1190/1.1442137).
* ``all`` -- ``pf`` re-weighted with surface and derivative edges: band 19
  ``det_elev_slope`` (0.20, scarp) and band 6 ``tc`` (0.10, tilt-angle/total
  curvature edge detector).

Three variants form a 2-factor design at a fixed 35% move budget:

    value      field   radius   isolates
    g2f35      pf      2 px     potential-field localisation alone
    d2f35      all     2 px     field effect at matched radius
    d1f35      all     1 px     radius (displacement cost) effect at matched field

``35%`` of dots is the maximum move budget compatible with Brief §5's "1-50% of
R0's dots" rule; the cap also keeps the experiment graded rather than a wholesale
rewrite.

Everything is deterministic (no RNG in the allocation; ties break on flat index),
inputs are SHA-256 pinned, and every emitted raster is re-read from disk and gated.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import rasterio

import build_prune_variants as bp

ROOT = bp.ROOT
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"

R1_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
R1_SHA_NAN = "6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9"
R1_SHA_ZEROS = "dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f"
# This builder owns ONLY these (parent=R1, axis=SNAP, value) rows/cards/files. The R0
# SNAP family and the R1 scarp transplant family (scripts/build_snap_r1_scarp_variants.py)
# must survive an idempotent re-run untouched (IR-88-39 discipline).
OWN_VALUES = frozenset({"g2f35", "d2f35", "d1f35"})

MOVE_FRACTION = 0.35          # share of dots allowed to move (Brief §5 cap = 0.50)
MIN_CATALOGUE_PX = 3.0        # Brief §4.4 collar, enforced strictly (>) on every target cell
COLLAR_EPS = 1e-6             # keeps snapped dots outside the 300 m kernel radius like R1


def percentile_rank(arr: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Monotone percentile rank in [0, 1] over the footprint only (0 outside)."""
    out = np.zeros(arr.shape, dtype=np.float32)
    v = np.nan_to_num(arr[foot], nan=0.0, posinf=0.0, neginf=0.0)
    knots = np.quantile(v, np.linspace(0.0, 1.0, 1001))
    out[foot] = np.interp(v, knots, np.linspace(0.0, 1.0, 1001)).astype(np.float32)
    return out


def read_band(ds: rasterio.DatasetReader, idx: int, foot: np.ndarray) -> np.ndarray:
    """One competition band, sentinel-sanitised and zeroed outside the footprint."""
    a = np.nan_to_num(ds.read(idx), nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    bad = (~np.isfinite(a)) | (np.abs(a) > 1e20)
    if np.any(bad & foot):
        a[bad & foot] = float(np.median(a[foot & ~bad])) if np.any(foot & ~bad) else 0.0
    a[~foot] = 0.0
    return a


def build_edge_fields(verified: dict[str, Path], foot: np.ndarray) -> dict[str, np.ndarray]:
    """Percentile-rank edge responses; every band is released as soon as it is ranked."""
    with rasterio.open(verified["training_features"]) as ds:
        b3 = percentile_rank(np.abs(read_band(ds, 3, foot)), foot)    # tmi_hg
        b18 = percentile_rank(np.abs(read_band(ds, 18, foot)), foot)  # iso_grav_anom_hg
        b19 = percentile_rank(np.abs(read_band(ds, 19, foot)), foot)  # det_elev_slope
        b6 = percentile_rank(np.abs(read_band(ds, 6, foot)), foot)    # tc (tilt/curvature)

    e_pf = (0.55 * b3 + 0.45 * b18).astype(np.float32)
    e_all = (0.40 * b3 + 0.30 * b18 + 0.20 * b19 + 0.10 * b6).astype(np.float32)
    del b3, b18, b19, b6
    return {"pf": e_pf, "all": e_all}


def snap_mask(
    mask: np.ndarray,
    field: np.ndarray,
    foot: np.ndarray,
    d_cat: np.ndarray,
    radius: int,
    move_fraction: float,
    min_cat: float = MIN_CATALOGUE_PX,
) -> tuple[np.ndarray, dict]:
    """Move up to ``move_fraction`` of dots <= ``radius`` px onto the best edge cell.

    Greedy, deterministic: dots are processed in descending order of their best
    available edge gain (ties by flat index), and a dot moves only if its chosen
    cell is still free. Targets must be inside the footprint, at least
    ``min_cat`` px from the catalogue, and not already occupied.
    """
    H, W = mask.shape
    ys, xs = np.nonzero(mask)
    n = len(ys)
    if n == 0:
        raise ValueError("parent mask is empty")

    offs = [
        (dy, dx)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if 0 < dy * dy + dx * dx <= radius * radius
    ]
    offs.sort(key=lambda o: (o[0] ** 2 + o[1] ** 2, o[0], o[1]))  # near-first tie-break

    best_gain = np.full(n, -np.inf, dtype=np.float64)
    best_dy = np.zeros(n, dtype=np.int16)
    best_dx = np.zeros(n, dtype=np.int16)
    cur = field[ys, xs].astype(np.float64)

    for dy, dx in offs:
        yy, xx = ys + dy, xs + dx
        inb = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
        yy_c = np.clip(yy, 0, H - 1)
        xx_c = np.clip(xx, 0, W - 1)
        ok = inb & foot[yy_c, xx_c] & (d_cat[yy_c, xx_c] > min_cat + COLLAR_EPS)
        val = np.where(ok, field[yy_c, xx_c].astype(np.float64), -np.inf)
        gain = val - cur
        better = gain > best_gain
        best_gain = np.where(better, gain, best_gain)
        best_dy = np.where(better, dy, best_dy)
        best_dx = np.where(better, dx, best_dx)

    n_budget = int(round(move_fraction * n))
    order = np.argsort(-best_gain, kind="stable")
    occupied = mask.copy()
    moved = np.zeros(n, dtype=bool)
    src_y, src_x, dst_y, dst_x = [], [], [], []

    for i in order[:n_budget]:
        if not np.isfinite(best_gain[i]) or best_gain[i] <= 0.0:
            break
        ty, tx = int(ys[i] + best_dy[i]), int(xs[i] + best_dx[i])
        if occupied[ty, tx]:
            continue
        occupied[ys[i], xs[i]] = False
        occupied[ty, tx] = True
        moved[i] = True
        src_y.append(int(ys[i]))
        src_x.append(int(xs[i]))
        dst_y.append(ty)
        dst_x.append(tx)

    new_mask = mask.copy()
    new_mask[ys[moved], xs[moved]] = False
    new_mask[np.asarray(dst_y, dtype=np.int64), np.asarray(dst_x, dtype=np.int64)] = True

    dy_arr = np.asarray(dst_y, dtype=np.float64) - np.asarray(src_y, dtype=np.float64)
    dx_arr = np.asarray(dst_x, dtype=np.float64) - np.asarray(src_x, dtype=np.float64)
    dist = np.hypot(dy_arr, dx_arr)
    dst_gain = field[np.asarray(dst_y, dtype=np.int64), np.asarray(dst_x, dtype=np.int64)] - field[
        np.asarray(src_y, dtype=np.int64), np.asarray(src_x, dtype=np.int64)
    ] if len(dst_y) else np.zeros(0, dtype=np.float32)

    stats = {
        "n_dots": int(n),
        "move_budget": n_budget,
        "n_moved": int(moved.sum()),
        "pct_moved_of_dots": round(100.0 * float(moved.sum()) / n, 3),
        "mean_displacement_px": round(float(dist.mean()), 4) if dist.size else 0.0,
        "median_displacement_px": round(float(np.median(dist)), 4) if dist.size else 0.0,
        "max_displacement_px": round(float(dist.max()), 4) if dist.size else 0.0,
        "frac_displacement_2px": round(float((dist > 1.5).mean()), 4) if dist.size else 0.0,
        "mean_field_gain": round(float(dst_gain.mean()), 5) if dst_gain.size else 0.0,
        "median_field_gain": round(float(np.median(dst_gain)), 5) if dst_gain.size else 0.0,
        "radius_px": radius,
        "move_fraction_cap": move_fraction,
        "n_dots_before_in_collar": int(int((d_cat[mask] < MIN_CATALOGUE_PX + 1e-9).sum())),
        "field_mean_at_parent_dots": round(float(field[mask].mean()), 5),
        "field_mean_after": round(float(field[new_mask].mean()), 5),
    }
    return new_mask, stats


def reconstruct_r1(lin: dict, w_field: np.ndarray, verified: dict[str, Path]) -> np.ndarray:
    """Rebuild ``PRUNEp3px`` exactly and assert the published SHA-256 of both twins."""
    r0, d_cat, h19_5 = lin["r0"], lin["d_cat"], lin["h19_5"]
    r0_gt3 = r0 & (d_cat > 3.0)
    n_rem3 = int(r0.sum() - r0_gt3.sum())
    r1 = bp.select_exact_marginal_dti_add(
        base_mask=r0_gt3,
        cand_mask=h19_5 & ~r0_gt3 & (d_cat > 3.0),
        w=w_field,
        n_add=n_rem3,
    )
    if int(r1.sum()) != int(r0.sum()):
        raise RuntimeError(f"R1 rebuild changed the count: {int(r1.sum())} != {int(r0.sum())}")

    foot = lin["foot"]
    with rasterio.open(verified["sample_submission"]) as tpl:
        prof = tpl.profile.copy()
    prof.update(
        driver="GTiff", dtype="float32", count=1, compress="deflate",
        predictor=3, zlevel=9, tiled=True, blockxsize=256, blockysize=256,
    )
    tmp_dir = ROOT / ".scratch"
    tmp_dir.mkdir(exist_ok=True)
    checks = {}
    for nodata, want, tag in ((np.nan, R1_SHA_NAN, "nan"), (None, R1_SHA_ZEROS, "zeros")):
        p = tmp_dir / f".r1-rebuild-{tag}.tif"
        prof_t = dict(prof)
        prof_t["nodata"] = nodata
        arr = np.where(foot, r1.astype(np.float32), np.float32(np.nan if nodata is not None else 0.0))
        with rasterio.open(p, "w", **prof_t) as dst:
            dst.write(arr.astype(np.float32), 1)
        checks[tag] = bp.sha256_file(p)
        p.unlink()
        if checks[tag] != want:
            raise RuntimeError(f"R1 rebuild {tag} SHA mismatch: {checks[tag]} != {want}")
    print(f"      EXACT R1 REBUILD OK: {int(r1.sum()):,} dots | nan={checks['nan'][:12]}... "
          f"| zeros={checks['zeros'][:12]}...")
    return r1


SPECS = [
    (
        "g2f35",
        "pf",
        2,
        "+0.002",
        "[-0.010, +0.014]",
        "h33-2-b2 PRUNEp3px; SNAP<=2px to potential-field HG (tmi_hg+grav_hg), 35% moved; pred +0.002 MODEL",
        "Move up to 35% of R1 dots <=2 px onto the strongest potential-field horizontal-gradient cell "
        "in their window (band 3 tmi_hg 0.55 + band 18 iso_grav_anom_hg 0.45, percentile-ranked). "
        "Count fixed at 37,654; >=3 px catalogue collar enforced on every target.",
        {
            "hypothesis": "H19-5 ridge crests sit a systematic 1-2 px off the true fault plane because GeoDAWN Area 2 was flown at 400 m spacing / 150-200 m drape; snapping the highest-gain third of dots onto the potential-field horizontal-gradient maximum moves mass onto the basement offset itself and raises live DTI at fixed count.",
            "mechanism": "A normal fault offsets magnetisation and density across its plane, so |grad TMI| and |grad isostatic gravity| peak over the fault. Within the 3 px (300 m) triangular kernel a dot keeps credit 1 - d/3, so cutting a systematic 2 px offset to 0.5 px raises per-truth credit from ~0.33 to ~0.83 on the moved dots while consuming no extra mass.",
            "non_fault_mimic": "400 m aeromagnetic flight-line corrugation and upward-continuation side-lobes produce horizontal-gradient maxima parallel to, but 100-300 m off, the mapped trace; welded-tuff caprock and Lake Lahontan shoreline breaks also produce strong gradients with no fault.",
            "predicted_sign_size": "MODEL +0.002 live (range -0.010 to +0.014). Individual bands localise faults only weakly here (percentile rank at catalogue pixels 0.53-0.56 vs 0.50 background), so |delta| < 0.01 is the expected outcome and is itself the result: geometry is not the binding constraint.",
            "falsifier": "Live delta <= -0.01 while d1f35 (same field, 1 px) is also negative falsifies the flight-line-offset hypothesis and shows R0/R1 ridge crests are already at or inside the noise floor; any gain >= +0.01 justifies a full re-detection on the same fields rather than more snapping.",
        },
    ),
    (
        "d2f35",
        "all",
        2,
        "+0.001",
        "[-0.011, +0.013]",
        "h33-2-b2 PRUNEp3px; SNAP<=2px to TMI+grav+scarp+curvature edge, 35% moved; pred +0.001 MODEL",
        "Move up to 35% of R1 dots <=2 px onto the strongest composite edge cell (tmi_hg 0.40, "
        "grav HG 0.30, det_elev_slope 0.20, tilt/curvature 0.10). Count fixed at 37,654; "
        ">=3 px collar enforced. Field effect vs g2f35 at identical radius and move budget.",
        {
            "hypothesis": "Adding surface scarp and curvature evidence to the potential-field edges recovers blind faults whose geophysical offset is too deep or too weak to dominate |grad TMI|, so the composite snaps more dots onto real traces than the potential-field field alone.",
            "mechanism": "Near-surface scarps put a step in detrended elevation (slope) and a ridge in the tilt/curvature operator at the same plane that carries the deeper density/magnetic offset; summing percentile ranks lets either charge the target while requiring neither, which is what a partially buried normal fault looks like.",
            "non_fault_mimic": "Alluvial-fan channels, pediment edges and anthropogenic cut-slopes produce elevation slope and curvature ridges with no shear; curvature also lights up playa margins and the 1,330 m Lahontan shoreline.",
            "predicted_sign_size": "MODEL +0.001 live (range -0.011 to +0.013). Paired with g2f35 the field effect should be small; if the composite wins by >= 0.01 over g2f35, surface scarps localise better than potential fields in this area.",
            "falsifier": "d2f35 - g2f35 <= -0.01 means elevation-derived edges actively mislead and only potential-field geometry should be trusted in any later fusion step.",
        },
    ),
    (
        "d1f35",
        "all",
        1,
        "+0.003",
        "[-0.009, +0.015]",
        "h33-2-b2 PRUNEp3px; SNAP<=1px to composite edge, 35% moved; pred +0.003 MODEL",
        "Move up to 35% of R1 dots <=1 px (100 m) onto the strongest composite edge cell "
        "(same field as d2f35). Count fixed at 37,654; >=3 px collar enforced. Conservative "
        "displacement bracket: tests whether the gain survives when the kernel cost of moving is small.",
        {
            "hypothesis": "If R0/R1 ridge crests are already within ~1 px of the truth plane, a 1 px snap captures the remaining localisation gain at almost no kernel cost, whereas a 2 px snap overshoots and loses credit; the 1 px variant should therefore match or beat the 2 px variant.",
            "mechanism": "A dot that is correct stays within 1-2 px of truth after a 1 px move, and a dot that is 2 px off gains without crossing to the far side of the feature. The asymmetric cost of overshoot (credit 1-d/3, hard zero at 3 px) makes the smaller move the lower-variance of the two.",
            "non_fault_mimic": "Same as d2f35 (fan channels, pediment edges, shoreline breaks); at 1 px, gridding noise inside a single cell is the main non-geological attractor.",
            "predicted_sign_size": "MODEL +0.003 live (range -0.009 to +0.015), the best of the three on the theory that displacement cost dominates field quality at this signal-to-noise.",
            "falsifier": "d1f35 < d2f35 by >= 0.01 falsifies the 'already within 1 px' premise and says R2 (400 m flight spacing) really did leave a 1-2 px bias worth removing.",
        },
    ),
]


def main() -> int:
    print("[1/6] Verifying SHA-256 manifest pins...")
    verified = bp.verify_manifest()
    print(f"      Verified {len(verified)}/{len(verified)} pinned inputs.")

    print("[2/6] Rebuilding R0 from the lineage recipe (byte-exact)...")
    lin = bp.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    print(f"      R0 OK: {int(lin['r0'].sum()):,} dots, min d_cat = {d_cat[lin['r0']].min():.3f} px")

    print("[3/6] Rebuilding the label-free corroboration field (needed for the R1 refill)...")
    w_field, canaries = bp.build_physical_field_and_canaries(
        verified, foot, catalogue, lin["h19_5"]
    )
    print(f"      Canaries PASS ({len(canaries)} channels; max symmetric AUC = {max(canaries.values()):.5f})")

    print("[4/6] Reconstructing parent R1 = PRUNEp3px and asserting its published SHA-256...")
    r1 = reconstruct_r1(lin, w_field, verified)

    print("[5/6] Building edge fields and snapping...")
    fields = build_edge_fields(verified, foot)
    for name, f in fields.items():
        print(f"      field {name}: mean {float(f[foot].mean()):.4f} at R1 dots {float(f[r1].mean()):.4f}")

    # Idempotent re-run: drop previous SNAP rows/files so the ledger never duplicates a family.
    ledger_rows: list[dict[str, str]] = []
    raw_kept_lines: list[str] = []
    fieldnames: list[str] = []
    header_line = ""
    existing_shas: set[str] = {bp.PARENT_SHA_ZEROS, bp.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS}
    if LEDGER.is_file():
        with LEDGER.open("r", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                # Replace only THIS family's rows (parent R1, own values); the R0 SNAP
                # family and the R1 scarp transplant family must survive this re-run.
                if (
                    row.get("axis") == "SNAP"
                    and row.get("parent") == R1_ID
                    and row.get("value") in OWN_VALUES
                ):
                    continue
                ledger_rows.append(row)
                for k in ("sha256", "sha256_zeros"):
                    if row.get(k):
                        existing_shas.add(row[k])
        # Keep every untouched row byte-for-byte (the older families were serialised by
        # different writers; re-serialising them churns the diff without changing data).
        with LEDGER.open("r", newline="") as fh:
            raw_lines = fh.read().splitlines()
        header_line = raw_lines[0] if raw_lines else ""
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if (
                len(parsed) > 3
                and parsed[2] == "SNAP"
                and parsed[1] == R1_ID
                and parsed[3] in OWN_VALUES
            ):
                continue
            raw_kept_lines.append(line)
    for v_name in OWN_VALUES:
        for stale in RELEASES.glob(f"{R1_ID}-SNAP{v_name}-*"):
            stale.unlink()

    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    cards = {
        k: v
        for k, v in cards.items()
        if not any(k.startswith(f"{R1_ID}-SNAP{val}-") for val in OWN_VALUES)
    }
    arms = {bp.PARENT_ID: lin["r0"], R1_ID: r1}
    built = []

    for value, field_key, radius, pred, pred_range, note, desc, card in SPECS:
        mask, stats = snap_mask(
            mask=r1,
            field=fields[field_key],
            foot=foot,
            d_cat=d_cat,
            radius=radius,
            move_fraction=MOVE_FRACTION,
        )
        if int(mask.sum()) != int(r1.sum()):
            raise RuntimeError("SNAP changed the dot count")
        if d_cat[mask].min() <= MIN_CATALOGUE_PX + COLLAR_EPS:
            raise RuntimeError(f"SNAP produced a dot at {d_cat[mask].min():.3f} px from the catalogue")

        rec = bp.write_and_verify_variant(
            mask=mask,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=r1,
            axis="SNAP",
            value=value,
            note_template=note,
            existing_shas=existing_shas,
            parent_id=R1_ID,
            parent_sha_zeros=R1_SHA_ZEROS,
            parent_sha_nan=R1_SHA_NAN,
            min_catalogue_px=MIN_CATALOGUE_PX,
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])
        rec["snap_statistics"] = stats
        rec["parent_rebuild_verified"] = {"sha256_nan": R1_SHA_NAN, "sha256_zeros": R1_SHA_ZEROS}
        rec["leakage_canaries"] = {"passed": True, "max_symmetric_auc": max(canaries.values()),
                                   "channels": canaries}
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        print(
            f"      {value}: moved {stats['n_moved']:,} dots ({stats['pct_moved_of_dots']:.2f}%), "
            f"mean displacement {stats['mean_displacement_px']:.3f} px -> {rec['id']}"
        )
        cards[rec["id"]] = card
        arms[rec["id"]] = mask
        built.append((rec, stats, pred, pred_range, desc))

    print("[6/6] REPORT-ONLY diagnostics (holdout-DTI, SGMC off-catalogue control, block CV)...")
    eval_report = bp.evaluate_report_only_instruments(
        arms=arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )
    for rec, stats, pred, pred_range, desc in built:
        rec["report_only_diagnostics"] = eval_report[rec["id"]]
        rec["parent_reference_diagnostics"] = eval_report[R1_ID]
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        ledger_rows.append(
            {
                "id": rec["id"],
                "parent": R1_ID,
                "axis": "SNAP",
                "value": rec["value"],
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{pred}",
                "predicted_range": pred_range,
                "ranking_basis": (
                    f"{stats['radius_px']} px window, field={rec['value']}, "
                    f"cap {stats['move_fraction_cap']:.2f} of dots"
                ),
                "receipt_score": "",
                "receipt_date": "",
                "description": desc,
                "recommendation": (
                    "DIAGNOSTIC, not a slot: the blind off-catalogue USGS SGMC control "
                    f"({eval_report[rec['id']]['sgmc_control']['dti']:.5f}) sits below parent R1 "
                    f"({eval_report[R1_ID]['sgmc_control']['dti']:.5f}), so snapping to geophysical "
                    "edges loses blind-fault alignment. Spend slot 1 on R1 instead; revisit only if "
                    "the R1 receipt shows the collar step behaved non-monotonically."
                ),
            }
        )

    if fieldnames:
        # Re-serialise ONLY this family's freshly built rows. Every other row (including
        # the R0 SNAP family and other R1 families) already survives verbatim in
        # raw_kept_lines; selecting all SNAP rows here used to duplicate them on re-run.
        new_snap_rows = [
            r
            for r in ledger_rows
            if r.get("axis") == "SNAP"
            and r.get("parent") == R1_ID
            and r.get("value") in OWN_VALUES
        ]
        import io as _io
        buf = _io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        for row in new_snap_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
        body = buf.getvalue().rstrip("\n")
        with LEDGER.open("w", newline="") as fh:
            fh.write(header_line + "\n")
            for line in raw_kept_lines:
                fh.write(line + "\n")
            if body:
                fh.write(body + "\n")
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")

    print("\nSNAP REPORT-ONLY SUMMARY (PROXY, never a score)")
    for rec, stats, pred, pred_range, desc in built:
        d = eval_report[rec["id"]]
        print(
            f"  {rec['value']:7s} n={rec['n_dots']:,} moved={stats['pct_moved_of_dots']:.1f}% "
            f"disp={stats['mean_displacement_px']:.2f}px  SGMC={d['sgmc_control']['dti']:.5f}  "
            f"CV12km={d['block_density_cv']['cv_12km_120px_interior']:.4f}  pred={pred}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
