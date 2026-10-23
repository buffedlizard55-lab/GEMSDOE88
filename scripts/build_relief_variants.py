#!/usr/bin/env python3
"""Build and validate controlled AXIS=RELIEF variants of parent ``R1 = PRUNEp3px``.

**Session brief v2 §5 (RELIEF):** "shift 10-15% of mass between basin / piedmont /
range-front terciles (relief from the detrended-elevation bands), count fixed."

Parent choice (logged in ``IRREGULARITIES.md`` as IR-RELIEF-01): the brief names R0 as
the parent, but ``R0`` itself carries 2,171 dots at ``2 < d_cat <= 3`` px, so *any*
non-PRUNE edit of R0 fails the §4.4 MUST gate "keep >= 3 px from catalogue pixels".
The variants are therefore built on ``R1 = h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705``,
the ledger's single-axis PRUNE edit of R0 whose rebuild is asserted byte-for-byte here
(``nan`` 6f7ae705…, ``zeros`` dc6f090d…). R1 is the gate-clean parent already named in
``SLOT_PLAN.md`` for week-2 RELIEF work.

Pipeline
--------
1. Verify every SHA-256 pin in ``registry/data_manifest.json``.
2. Rebuild R0 (``h33-h33-2-b2``, 37,654 dots) from the lineage recipe and assert both
   published SHA-256 twins.
3. Rebuild the label-free corroboration field ``w`` and re-run the leakage canaries
   (every channel must stay at symmetric AUC <= 0.90).
4. Rebuild R1 = PRUNEp3px and assert both published SHA-256 twins.
5. Terrain terciles from the **detrended elevation** band (``training_features`` band 12,
   ``det_elev``): tercile 0 = basin floor, 1 = piedmont, 2 = range front / range interior.
6. Emit three constant-mass (37,654 dots) RELIEF variants. Donors are the dots whose
   removal costs the least *exact* expected DTI under the label-free corroboration
   field ``w`` (restricted to the source terciles); receivers are the unused ridge-support
   cells in the target tercile with the largest exact marginal DTI gain under the same
   ``w``, every one of them at ``d_cat > 3 px``:

   ==========  =====================================================================
   ``up2t10``  move 10% (3,765) of dots from terciles 0+1 up-section into tercile 2
   ``up2t15``  move 15% (5,648) of dots from terciles 0+1 up-section into tercile 2
   ``dn2t15``  opposite sign control: 15% (5,648) from terciles 1+2 down into 0
   ==========  =====================================================================

7. MUST gates via :func:`build_prune_variants.write_and_verify_variant` (format parity,
   NaN outside + ``-zeros`` twin, zero catalogue mass, non-duplicate SHA-256, 3 px
   collar, re-read from disk), then REPORT-ONLY instruments (hide-and-recover holdout
   PROXY with 95% CI, SGMC off-catalogue control, block-density CV).
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "scripts", ROOT / "vendor", ROOT / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import build_prune_variants as bp  # noqa: E402
import build_snap_r1_variants as bsv  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"

R1_ID = bsv.R1_ID
R1_SHA_NAN = bsv.R1_SHA_NAN
R1_SHA_ZEROS = bsv.R1_SHA_ZEROS

# This module owns ONE of the two concurrently built RELIEF families (IR-88-38).
# A rerun replaces ONLY these values; the bracket family lives in
# scripts/build_relief_bracket_variants.py and must survive untouched.
OUR_VALUES = {"up2t10", "up2t15", "dn2t15"}

TERRAIN_BAND = 12                 # det_elev - "Detrended elevation"
TERRAIN_NAMES = {0: "basin", 1: "piedmont", 2: "range_front"}
MIN_CATALOGUE_PX = 3.0            # Brief §4.4 collar, enforced strictly
SEED = bp.SEED


# ---------------------------------------------------------------------------
# 1. Terrain terciles and the relief move
# ---------------------------------------------------------------------------


def terrain_terciles(det_elev: np.ndarray, foot: np.ndarray) -> tuple[np.ndarray, list[float]]:
    """Split the footprint into detrended-elevation terciles (equal area).

    Returns ``(cls, [q33, q67])`` where ``cls`` is -1 outside the footprint and
    0 / 1 / 2 = basin floor / piedmont / range front along the det_elev axis.
    """
    v = np.nan_to_num(det_elev[foot], nan=0.0, posinf=0.0, neginf=0.0)
    q33, q67 = (float(x) for x in np.quantile(v, [1.0 / 3.0, 2.0 / 3.0]))
    cls = np.full(det_elev.shape, -1, dtype=np.int8)
    cls[foot] = np.digitize(v, [q33, q67]).astype(np.int8)
    return cls, [q33, q67]


def relief_move(
    mask: np.ndarray,
    foot: np.ndarray,
    cls: np.ndarray,
    w: np.ndarray,
    d_cat: np.ndarray,
    ridge: np.ndarray,
    source_classes: tuple[int, ...],
    target_class: int,
    n_move: int,
    min_cat: float = MIN_CATALOGUE_PX,
) -> tuple[np.ndarray, dict]:
    """Move ``n_move`` dots out of ``source_classes`` into ``target_class``, count fixed.

    Both halves use the metric's own algebra against the **label-free** corroboration
    field ``w`` (the same field the parent's PRUNE refill used), so no catalogue,
    holdout or leaderboard information enters the choice of individual cells; only the
    *tercile constraint* is imposed by this axis:

    * **Donors** -- :func:`build_prune_variants.select_exact_marginal_dti_drop` with the
      drop pool restricted to dots whose terrain class is in ``source_classes``: the
      greedy sequence whose removal costs the least exact expected DTI under ``w``.
    * **Receivers** -- :func:`build_prune_variants.select_exact_marginal_dti_add` with
      the candidate pool restricted to ``target_class`` cells on the parent's multi-line
      ridge support, unused, and at ``d_cat > min_cat``: the greedy sequence with the
      largest exact marginal DTI gain under ``w``.

    Because a dot on an already-covered cell adds nothing to ``T`` while still adding
    ``alpha`` to the denominator, the marginal-gain objective spreads receivers into
    uncovered support by itself -- no ad-hoc spacing rule is needed. The dot count is
    invariant by construction.
    """
    if n_move <= 0:
        raise ValueError("n_move must be positive")
    H, W = mask.shape
    donor_pool = mask & foot & np.isin(cls, np.asarray(source_classes))
    if int(donor_pool.sum()) < n_move:
        raise ValueError(
            f"donor pool ({int(donor_pool.sum())}) smaller than requested move ({n_move})"
        )

    survivors = bp.select_exact_marginal_dti_drop(
        base_mask=mask, drop_pool_mask=donor_pool, w=w, n_drop=n_move
    )
    if int(survivors.sum()) != int(mask.sum()) - n_move:
        raise RuntimeError("relief drop removed the wrong number of dots")

    cand = foot & (cls == target_class) & ridge & ~survivors & (d_cat > min_cat)
    if int(cand.sum()) < n_move:
        raise ValueError(
            f"receiver pool ({int(cand.sum())}) smaller than requested move ({n_move}); "
            f"target class {target_class}"
        )

    new_mask = bp.select_exact_marginal_dti_add(
        base_mask=survivors, cand_mask=cand, w=w, n_add=n_move
    )
    if int(new_mask.sum()) != int(mask.sum()):
        raise RuntimeError("relief move changed the dot count")

    receivers = new_mask & ~survivors
    donors = mask & ~survivors
    d_before = np.bincount(cls[mask].astype(np.int64), minlength=3)
    d_after = np.bincount(cls[new_mask].astype(np.int64), minlength=3)

    ys, xs = np.nonzero(receivers)
    sy, sx = np.nonzero(survivors)
    tree = cKDTree(np.column_stack([sy, sx]))
    nn_dist, _ = tree.query(np.column_stack([ys, xs]), k=1)

    exp_parent = bp.weighted_expected_dti(mask, w)
    exp_variant = bp.weighted_expected_dti(new_mask, w)

    stats = {
        "n_move": int(n_move),
        "pct_moved_of_dots": round(100.0 * n_move / int(mask.sum()), 3),
        "source_classes": list(source_classes),
        "source_class_names": [TERRAIN_NAMES[int(c)] for c in source_classes],
        "target_class": int(target_class),
        "target_class_name": TERRAIN_NAMES[int(target_class)],
        "donor_w_mean": round(float(w[donors].mean()), 5),
        "donor_w_median": round(float(np.median(w[donors])), 5),
        "receiver_w_mean": round(float(w[receivers].mean()), 5),
        "receiver_w_median": round(float(np.median(w[receivers])), 5),
        "parent_w_mean": round(float(w[mask].mean()), 5),
        "variant_w_mean": round(float(w[new_mask].mean()), 5),
        "expected_dti_under_w_parent": round(float(exp_parent["dti"]), 6),
        "expected_dti_under_w_variant": round(float(exp_variant["dti"]), 6),
        "expected_dti_under_w_delta": round(float(exp_variant["dti"] - exp_parent["dti"]), 6),
        "class_counts_before": {TERRAIN_NAMES[i]: int(d_before[i]) for i in range(3)},
        "class_counts_after": {TERRAIN_NAMES[i]: int(d_after[i]) for i in range(3)},
        "class_share_before_pct": {
            TERRAIN_NAMES[i]: round(100.0 * float(d_before[i]) / int(mask.sum()), 2) for i in range(3)
        },
        "class_share_after_pct": {
            TERRAIN_NAMES[i]: round(100.0 * float(d_after[i]) / int(mask.sum()), 2) for i in range(3)
        },
        "donors_removed_per_class": {
            TERRAIN_NAMES[i]: int((donors & (cls == i)).sum()) for i in range(3)
        },
        "receiver_nn_dist_px_percentiles": {
            str(q): round(float(np.percentile(nn_dist, q)), 3) for q in (0, 5, 25, 50, 95)
        },
        "receivers_closer_than_2px": int((nn_dist < 2.0).sum()),
        "receiver_pool_size": int(cand.sum()),
        "min_dist_catalogue_px": round(float(d_cat[new_mask].min()), 4),
    }
    return new_mask, stats


# ---------------------------------------------------------------------------
# 2. Variant specification
# ---------------------------------------------------------------------------

SPECS = [
    (
        "up2t10",
        (0, 1),
        2,
        0.10,
        "-0.002",
        "[-0.008,+0.004]",
        "h33-2-b2 PRUNEp3px; RELIEF 10% basin+piedmont->range-front, count fixed; pred -0.002 MODEL",
        "Move 3765 dots (10.00%) out of det_elev terciles 0+1 (basin+piedmont) into tercile 2 (range front); donors = lowest exact-marginal-DTI cost, receivers = highest exact-marginal-DTI gain on unused ridge-support cells; count fixed at 37654; all receivers d_cat>3 px.",
        {
            "hypothesis": "A 10% up-section reallocation of dot mass raises live DTI if the private new-fault truth concentrates in the high-detrended-elevation (range-front) tercile the way the off-catalogue USGS fault control does; if instead the parent's dot coverage is already saturated there, the move costs coverage and loses slightly.",
            "mechanism": "The off-catalogue USGS SGMC control is 5.6x denser per footprint pixel in det_elev tercile 2 (63.6% of its 62,703 px) than in tercile 0 (11.3%), while the competition catalogue is flat across terciles (30.4/40.6/29.0). R1's mass sits between the two (20.4/41.8/37.8). Reallocating 10% up-section therefore trades covered basin/piedmont ground for range-front ground: at 15% dose this costs -0.007 expected DTI under the same label-free field the parent was refilled with and degrades the 12 km block-density CV from 0.570 to 0.691, i.e. the range front is already the saturated tercile, which is why the prediction is a small loss rather than a gain.",
            "non_fault_mimic": "High det_elev is partly bedrock ridge crest rather than fault-controlled range front; steep-slope cells carry strong TMI/gravity-gradient edges from lithological contacts and cooling joints, which the field rewards without any fault plane being present.",
            "predicted_sign_size": "MODEL predicted live delta -0.002 vs R1 (range -0.008 to +0.004). Read against up2t15 as a dose pair; |delta| < 0.01 on public chunks is not evidence.",
            "falsifier": "A live gain >= +0.01 vs R1 falsifies coverage saturation and shows the range-front tercile still has unfilled fault mass; a loss larger than up2t15's would break monotonicity and mark public-chunk noise.",
        },
    ),
    (
        "up2t15",
        (0, 1),
        2,
        0.15,
        "-0.004",
        "[-0.010,+0.002]",
        "h33-2-b2 PRUNEp3px; RELIEF 15% basin+piedmont->range-front, count fixed; pred -0.004 MODEL",
        "Move 5648 dots (15.00%) out of det_elev terciles 0+1 (basin+piedmont) into tercile 2 (range front); donors = lowest exact-marginal-DTI cost, receivers = highest exact-marginal-DTI gain on unused ridge-support cells; count fixed at 37654; all receivers d_cat>3 px.",
        {
            "hypothesis": "The full 15% dose carries the same up-section reallocation as up2t10 with more mass at risk: it is the cleanest test of whether the private truth's relief profile resembles the blind-fault control more than the catalogue's flat profile.",
            "mechanism": "Same mechanism as up2t10, at the brief's upper dose. Donors are chosen by exact marginal DTI cost under the label-free corroboration field w, receivers by exact marginal DTI gain inside the target tercile, so the only imposed difference is the tercile constraint. The measured outcome of that constraint is a -0.0069 expected-DTI-under-w change, a -0.0036 SGMC off-catalogue change and a 12 km block CV rise from 0.570 to 0.691: the parent is already dense where the range-front evidence is strong, so additional range-front dots are near-duplicates of existing ones.",
            "non_fault_mimic": "The 15% dose strips the basin and piedmont of 5,648 dots, including the concealed basin faults that Phase-2 expert-expanded labels are most likely to add; a mimic is losing real basin truth while buying lithological edges in the ranges.",
            "predicted_sign_size": "MODEL predicted live delta -0.004 vs R1 (range -0.010 to +0.002). Monotone ordering up2t15 < up2t10 < R1 < dn2t15 would confirm the saturation reading.",
            "falsifier": "Live change >= +0.01 vs R1 falsifies coverage saturation and would justify building the same move at 30-50% dose next week; a change at or below dn2t15's would falsify the relief prior outright.",
        },
    ),
    (
        "dn2t15",
        (1, 2),
        0,
        0.15,
        "-0.007",
        "[-0.014,-0.001]",
        "h33-2-b2 PRUNEp3px; RELIEF 15% piedmont+range-front->basin, count fixed; pred -0.007 MODEL",
        "Control: move 5648 dots (15.00%) out of det_elev terciles 1+2 (piedmont+range front) down into tercile 0 (basin floor); donors = lowest exact-marginal-DTI cost, receivers = highest exact-marginal-DTI gain on unused ridge-support cells; count fixed at 37654; all receivers d_cat>3 px.",
        {
            "hypothesis": "The mirror-image reallocation is the sign control: if the blind-fault relief prior is real, moving 15% of mass down-section loses more than moving it up-section. If basin-floor concealed faults dominate private truth, this variant wins instead.",
            "mechanism": "Tercile 0 holds the thinnest share of off-catalogue SGMC fault pixels per footprint pixel (11.3% of its pixels on 33.3% of the area), and potential-field plus scarp evidence there is weaker, so the same 15% of mass converts into fewer true fault pixels; the measured SGMC control falls from 0.09608 (R1) to 0.08490, the largest loss of the three variants. Holding the parent, the count, the collar and the ranking rule fixed makes the direction of the transfer the only difference from up2t15.",
            "non_fault_mimic": "det_elev is a local detrending, so 'basin' cells include low-relief piedmont ramps and Lake Lahontan shoreline benches that are not structural basins; a mimic is that the variant mostly exchanges two flavours of the same alluvial surface.",
            "predicted_sign_size": "MODEL predicted live delta -0.007 vs R1 (range -0.014 to -0.001). It is a sign control, not a slot candidate unless one of the up-section variants gains >= +0.01.",
            "falsifier": "A live gain >= +0.01 vs R1 falsifies the relief prior and points at concealed basin faults as the dominant private-truth reservoir, in which case the next build is a basin-directed reallocation at 30-50% dose.",
        },
    ),
]


# ---------------------------------------------------------------------------
# 3. Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("[1/6] Verifying SHA-256 manifest pins...")
    verified = bp.verify_manifest()
    print(f"      Verified {len(verified)} pinned inputs.")

    print("[2/6] Rebuilding R0 (h33-h33-2-b2) from the lineage recipe (byte-exact)...")
    lin = bp.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    print(
        f"      R0 OK: {int(lin['r0'].sum()):,} dots | zeros={lin['rebuilt_zeros_sha256'][:12]}... "
        f"| nan={lin['rebuilt_nan_sha256'][:12]}..."
    )

    print("[3/6] Rebuilding the label-free corroboration field and running leakage canaries...")
    w_field, canaries = bp.build_physical_field_and_canaries(
        verified, foot, catalogue, lin["h19_5"]
    )
    print(f"      Canaries PASS (max symmetric AUC = {max(canaries.values()):.5f} <= 0.90)")

    print("[4/6] Reconstructing parent R1 = PRUNEp3px and asserting its published SHA-256...")
    r1 = bsv.reconstruct_r1(lin, w_field, verified)

    print("[5/6] Building detrended-elevation terciles and the three RELIEF variants...")
    with rasterio.open(verified["training_features"]) as ds:
        det_elev = bsv.read_band(ds, TERRAIN_BAND, foot)
    cls, thresholds = terrain_terciles(det_elev, foot)
    del det_elev
    area = {TERRAIN_NAMES[i]: int(((cls == i) & foot).sum()) for i in range(3)}
    print(f"      band {TERRAIN_BAND} det_elev tercile thresholds: {thresholds[0]:.3f}, {thresholds[1]:.3f}")
    print(f"      footprint area per tercile: {area}")

    # Idempotent re-run: drop ONLY this family's previous RELIEF rows/files.
    ledger_rows: list[dict[str, str]] = []
    raw_kept_lines: list[str] = []
    fieldnames: list[str] = []
    header_line = ""
    existing_shas: set[str] = {
        bp.PARENT_SHA_ZEROS, bp.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS,
    }
    if LEDGER.is_file():
        with LEDGER.open("r", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                if row.get("axis") == "RELIEF" and row.get("parent") == R1_ID and row.get("value") in OUR_VALUES:
                    continue
                ledger_rows.append(row)
                for k in ("sha256", "sha256_zeros"):
                    if row.get(k):
                        existing_shas.add(row[k])
        with LEDGER.open("r", newline="") as fh:
            raw_lines = fh.read().splitlines()
        header_line = raw_lines[0] if raw_lines else ""
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if len(parsed) > 3 and parsed[2] == "RELIEF" and parsed[1] == R1_ID and parsed[3] in OUR_VALUES:
                continue
            raw_kept_lines.append(line)
    for _v in OUR_VALUES:
        for stale in RELEASES.glob(f"{R1_ID}-RELIEF{_v}-*"):
            if stale.suffix in (".tif", ".zip", ".json"):
                stale.unlink()

    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    cards = {k: v for k, v in cards.items()
             if not any(k.startswith(f"{R1_ID}-RELIEF{_v}-") for _v in OUR_VALUES)}
    arms = {bp.PARENT_ID: lin["r0"], R1_ID: r1}
    built = []

    for value, src_classes, tgt_class, frac, pred, pred_range, note, desc, card in SPECS:
        n_move = int(round(frac * int(r1.sum())))
        mask, stats = relief_move(
            mask=r1,
            foot=foot,
            cls=cls,
            w=w_field,
            d_cat=d_cat,
            ridge=lin["h19_5"],
            source_classes=src_classes,
            target_class=tgt_class,
            n_move=n_move,
        )
        if int(mask.sum()) != int(r1.sum()):
            raise RuntimeError("RELIEF changed the dot count")
        if float(d_cat[mask].min()) <= MIN_CATALOGUE_PX + 1e-6:
            raise RuntimeError(f"RELIEF produced a dot at {d_cat[mask].min():.3f} px from the catalogue")

        rec = bp.write_and_verify_variant(
            mask=mask,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
            parent_mask=r1,
            axis="RELIEF",
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
        rec["relief_statistics"] = stats
        rec["terrain_definition"] = {
            "band": TERRAIN_BAND,
            "band_name": "det_elev (Detrended elevation)",
            "tercile_thresholds": [round(x, 4) for x in thresholds],
            "classes": TERRAIN_NAMES,
            "footprint_area_px": area,
            "degree_of_freedom_independence": (
                "tercile assignment uses only the provided detrended-elevation band; "
                "no catalogue, holdout or leaderboard information enters the classification"
            ),
        }
        rec["parent_rebuild_verified"] = {
            "R0_sha256_zeros": bp.PARENT_SHA_ZEROS,
            "R0_sha256_nan": bp.PARENT_SHA_NAN,
            "R1_sha256_nan": R1_SHA_NAN,
            "R1_sha256_zeros": R1_SHA_ZEROS,
        }
        rec["leakage_canaries"] = {
            "passed": True,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        }
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        print(
            f"      {value}: moved {stats['n_move']:,} dots ({stats['pct_moved_of_dots']:.2f}%), "
            f"mean w {stats['donor_w_mean']:.4f} -> {stats['receiver_w_mean']:.4f} -> {rec['id']}"
        )
        cards[rec["id"]] = card
        arms[rec["id"]] = mask
        built.append((rec, stats, pred, pred_range, desc))

    print("[6/6] REPORT-ONLY diagnostics (holdout PROXY, SGMC off-catalogue control, block CV)...")
    eval_report = bp.evaluate_report_only_instruments(
        arms=arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )

    # The hide-and-recover holdout is near-degenerate at a 3 px collar (0.0000 vs 0.0040
    # for R0), so the SGMC off-catalogue control is the informative PROXY for ranking arms.
    best = max(
        ((r, s) for r, s, *_ in built),
        key=lambda rs: eval_report[rs[0]["id"]]["sgmc_control"]["dti"],
    )[0]["id"]

    for rec, stats, pred, pred_range, desc in built:
        rec["report_only_diagnostics"] = eval_report[rec["id"]]
        rec["report_only_caveat"] = {
            "holdout_proxy": (
                "hide-and-recover HOLDOUT-DTI is near-degenerate for this family: R0 scores "
                "0.004006, while R1 and all three RELIEF arms score 0.000000 with identical "
                "paired deltas, because every dot is >= 3 px from the withheld catalogue "
                "fold. It is reported for completeness and carries no ranking weight."
            ),
            "sgmc_control": (
                "The off-catalogue USGS SGMC control is the informative PROXY here; it is a "
                "blind-fault stand-in, not truth, and has historically anti-correlated with "
                "live receipts on some files."
            ),
            "expert_note": (
                "All three arms are predicted NEGATIVE by three independent report-only "
                "signals (expected DTI under the label-free field, SGMC control, 12 km block "
                "CV). They exist to measure the sign of the relief effect, not to win a slot."
            ),
        }
        rec["parent_reference_diagnostics"] = eval_report[R1_ID]
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        d = eval_report[rec["id"]]
        ledger_rows.append(
            {
                "id": rec["id"],
                "parent": R1_ID,
                "axis": "RELIEF",
                "value": rec["value"],
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{pred}",
                "predicted_range": pred_range,
                "ranking_basis": (
                    "det_elev terciles; donors = lowest exact-marginal-DTI drop cost in source "
                    f"terciles {list(stats['source_classes'])}, receivers = highest exact-marginal-"
                    f"DTI add gain on unused ridge cells in tercile {stats['target_class']}, "
                    "all receivers d_cat>3 px; fixed count 37654"
                ),
                "receipt_score": "",
                "receipt_date": "",
                "description": desc,
                "recommendation": (
                    f"{'PRIMARY DIAGNOSTIC (least negative PROXY)' if rec['id'] == best else 'DIAGNOSTIC/control'}: "
                    f"holdout PROXY {d['holdout_proxy']['dti']:.5f} "
                    f"(paired delta vs R0 {d['holdout_proxy']['paired_delta_vs_r0']:+.5f}), "
                    f"SGMC off-cat {d['sgmc_control']['dti']:.5f} vs parent R1 "
                    f"{eval_report[R1_ID]['sgmc_control']['dti']:.5f}, 12 km CV "
                    f"{d['block_density_cv']['cv_12km_120px_interior']:.4f}. "
                    "Predicted change is NEGATIVE: RELIEF does not earn a week-1 slot ahead of "
                    "R1/SNAPscarp; spend one only if the R1 and SNAP receipts are inconclusive. "
                    "PROXY and MODEL are never a score; a live |delta| < 0.01 vs R1 is no evidence."
                ),
            }
        )

    if fieldnames:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        for row in ledger_rows:
            if row.get("axis") == "RELIEF" and row.get("value") in OUR_VALUES:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        body = buf.getvalue().rstrip("\n")
        with LEDGER.open("w", newline="") as fh:
            fh.write(header_line + "\n")
            for line in raw_kept_lines:
                fh.write(line + "\n")
            if body:
                fh.write(body + "\n")
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")

    print("\nRELIEF REPORT-ONLY SUMMARY (PROXY, never a score)")
    for rec, stats, pred, pred_range, desc in built:
        d = eval_report[rec["id"]]
        print(
            f"  {rec['value']:7s} n={rec['n_dots']:,} moved={stats['pct_moved_of_dots']:.1f}% "
            f"holdout={d['holdout_proxy']['dti']:.5f}  SGMC={d['sgmc_control']['dti']:.5f}  "
            f"CV12km={d['block_density_cv']['cv_12km_120px_interior']:.4f}  pred={pred}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
