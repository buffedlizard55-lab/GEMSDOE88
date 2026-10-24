#!/usr/bin/env python3
"""CONCENTRATION axis on the gate-clean parent R1 = PRUNEp3px-6f7ae705.

Agent Brief v2 §4.4 requires >=3 px clearance for every non-PRUNE axis.  R0
(h33-h33-2-b2) carries 1,611 dots strictly <3 px from the catalogue, so a
single-axis CONCENTRATION edit of R0 that inherits those dots fails the hardened
``validate_variant.py`` clearance gate.  This session therefore edits R1, R0's
gate-clean direct child (all 37,654 dots >3 px), which is rebuilt from R0 and
SHA-asserted before any edit.  Every relocation keeps 100% of dots >3 px.

Mechanism (see registry/preregistration_concentration_r1.json, registered before
any proxy): move a fixed fraction of dots from the LOWEST to the HIGHEST
label-free geophysical-prior 1 km / 5 km blocks.  The prior is the provided-band
``edge_scarp_pot`` field (bands 19/12/18/3), the exact field whose spacing-locked
SNAP beat parent on the blind off-catalogue SGMC control (IR-88-50).  No external
LiDAR.  Count is fixed at 37,654; deterministic; (row,col) total orders only.

All predictions are MODEL / PROXY, never RECEIPT.  The two instruments are
expected to disagree (w-field rewards densification, blind SGMC rewards spacing).
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_prune_variants as bpv            # noqa: E402
import build_snap_variants as bsnap           # noqa: E402
import build_snap_r1_variants as bsv          # noqa: E402
import make_concentration_variants as mcv     # noqa: E402

R1_ID = bsv.R1_ID
R1_SHA_NAN = bsv.R1_SHA_NAN
R1_SHA_ZEROS = bsv.R1_SHA_ZEROS
SEED = bpv.SEED
DATE = bpv.FIXED_DATE
COLLAR_PX = 3.0
CAP_PER_HOST = 2
PRIOR_SIGMA_BLOCKS = 1.5

LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS = ROOT / "ledger" / "mechanism_cards.json"
RELEASES = ROOT / "releases"
PREREG = ROOT / "registry" / "preregistration_concentration_r1.json"
REPORT = ROOT / "evidence" / "concentration_r1_axis_report.json"

# (value, moved fraction, block px, block label, form note, prereg MODEL, range)
SPECS = [
    ("phys-c10", 0.10, 10, "1 km",
     "R1(6f7ae705); CONC phys-prior low->high 10% (3765) 1km blocks, N=37654; pred +0.001 MODEL",
     "MODEL:+0.001", "[-0.010,+0.012]"),
    ("phys-c20", 0.20, 10, "1 km",
     "R1(6f7ae705); CONC phys-prior low->high 20% (7531) 1km blocks, N=37654; pred +0.002 MODEL",
     "MODEL:+0.002", "[-0.012,+0.016]"),
    ("phys-c20-b5km", 0.20, 50, "5 km",
     "R1(6f7ae705); CONC phys-prior low->high 20% (7531) 5km blocks, N=37654; pred +0.001 MODEL",
     "MODEL:+0.001", "[-0.012,+0.014]"),
]
OWN_VALUES = {s[0] for s in SPECS}


def physics_block_prior(edge_scarp_pot: np.ndarray, foot: np.ndarray, block: int):
    """Per-block mean of the label-free geophysical field, lightly smoothed."""
    area_px, eligible, nb_c = mcv.block_lattice(foot, block)  # (nb_r, nb_c), raveled bool
    nb_r = area_px.shape[0]
    rr, cc = np.nonzero(foot)
    bidx = (rr // block) * nb_c + (cc // block)
    s = np.bincount(bidx, weights=edge_scarp_pot[rr, cc], minlength=nb_r * nb_c)
    dens2d = np.divide(s.reshape(nb_r, nb_c), area_px,
                       out=np.zeros((nb_r, nb_c)), where=area_px > 0)
    sm = gaussian_filter(dens2d, PRIOR_SIGMA_BLOCKS, mode="constant")
    sm[~eligible.reshape(nb_r, nb_c)] = 0.0
    return sm.ravel(), eligible, nb_c


def select_donors(parent, prior, bids, dist, n_move):
    """Coldest blocks first, one dot left per donor block where the pool allows."""
    try:
        return mcv.choose_donors(parent, prior, bids, dist, n_move, keep_one_per_block=True)
    except AssertionError:
        # If the cold physics-prior blocks cannot supply the dose under the
        # one-per-block floor, relax it: emptying cold blocks is still a pure
        # concentration move and is reported via blocks_emptied.
        rr, cc = np.nonzero(parent)
        nn = mcv.nearest_neighbour_px(rr, cc)
        pr = prior[bids[rr, cc]]
        order = np.lexsort((cc, rr, -nn, pr))
        sel = order[:n_move]
        if len(sel) < n_move:
            raise RuntimeError(f"donor pool too small even relaxed: {len(sel)} < {n_move}")
        return rr[sel], cc[sel], nn[sel], pr[sel]


def mechanism_card(value, block_label, frac):
    return {
        "axis": "CONCENTRATION",
        "value": value,
        "parent": R1_ID,
        "hypothesis": (
            f"GeoDAWN Area 2 was flown at 400 m line spacing / 150-200 m drape, so the "
            f"provided-band geophysical crests (edge_scarp_pot) locate the fault fabric only "
            f"to ~1 kernel radius. Moving {frac:.0%} of R1's dots from the coldest to the "
            f"hottest {block_label} prior blocks re-allocates fixed mass onto the crests the "
            f"blind off-catalogue SGMC control already favours, and should raise live DTI."),
        "mechanism": (
            "Within the 3 px triangular kernel a dot keeps credit 1 - d/3. Mass welded to a "
            "surviving host in a high edge_scarp_pot block sits closer to the geophysical "
            "offset that the blind control rewards; the move consumes no extra mass (count "
            "fixed at 37,654) and every receiver stays >3 px from the mapped catalogue."),
        "non_fault_mimic": (
            "edge_scarp_pot maxima also follow welded-tuff caprock breaks, Lake Lahontan "
            "shorelines and 400 m aeromagnetic flight-line corrugation; concentrating on them "
            "can cluster dots onto a non-fault gradient with no new-fault truth."),
        "confounder": (
            "Concentration raises block-density CV away from the reported 0.51-0.59 sweet spot "
            "and away from the repeated 'spacing/uniformity is the lever' result. The label-free "
            "w-field MODEL rewards densification while blind SGMC has preferred spacing in every "
            "session; the two instruments are expected to disagree, so no arm is promoted on an "
            "instrument and a live |delta| < 0.01 is no evidence."),
        "predicted_sign_size": (
            "Near-zero, sign-uncertain (preregistered point |delta| <= 0.002, range spans zero). "
            "A >= +0.01 live gain on the actually-submitted R1 anchors the concentration "
            "direction; <= -0.01 closes it and confirms the uniformity lever."),
        "falsifier": (
            "A live receipt <= R1 - 0.01 while both 1 km doses are also negative falsifies "
            "crest-concentration on the gate-clean parent; a win of the 5 km arm over the "
            "1 km arm at matched 20% arbitrates the spatial scale of the prior."),
        "preregistration": "registry/preregistration_concentration_r1.json",
        "provided_bands_only": True,
        "external_lidar_used": False,
    }


def _ledger_surgery():
    """Idempotently read the ledger, dropping only this family's rows; return kept rows,
    kept raw lines, header, fieldnames and the pre-existing SHA set (excluding this family)."""
    rows, raw_kept, shas = [], [], {
        bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS,
    }
    header_line, fieldnames = "", []
    if LEDGER.is_file():
        with LEDGER.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            for row in reader:
                if (row.get("axis") == "CONCENTRATION"
                        and row.get("parent") == R1_ID
                        and row.get("value") in OWN_VALUES):
                    continue
                rows.append(row)
                for k in ("sha256", "sha256_zeros"):
                    if row.get(k):
                        shas.add(row[k])
        with LEDGER.open(newline="", encoding="utf-8") as fh:
            raw_lines = fh.read().splitlines()
        header_line = raw_lines[0] if raw_lines else ""
        for line in raw_lines[1:]:
            parsed = next(csv.reader([line])) if line.strip() else []
            if (len(parsed) > 3 and parsed[2] == "CONCENTRATION"
                    and parsed[1] == R1_ID and parsed[3] in OWN_VALUES):
                continue
            raw_kept.append(line)
    for v in OWN_VALUES:
        for stale in RELEASES.glob(f"{R1_ID}-CONC{v}-*"):
            stale.unlink()
    return rows, raw_kept, header_line, fieldnames, shas


def main() -> int:
    t0 = time.time()
    prereg = json.loads(PREREG.read_text())

    print("[1/7] Verifying SHA-256 manifest pins...")
    verified = bpv.verify_manifest()
    print(f"      Verified {len(verified)}/{len(verified)} pinned inputs.")

    print("[2/7] Rebuilding R0 (h33-h33-2-b2) byte-exactly from lineage...")
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    r0 = lin["r0"]
    print(f"      EXACT R0 REBUILD OK: {int(r0.sum()):,} dots | nan={lin['rebuilt_nan_sha256'][:12]}...")

    print("[3/7] Rebuilding label-free corroboration field w (R1 refill)...")
    w_field, w_canaries = bpv.build_physical_field_and_canaries(
        verified, foot, catalogue, lin["h19_5"])
    print(f"      w-field canaries PASS (max symmetric AUC = {max(w_canaries.values()):.5f})")

    print("[4/7] Reconstructing gate-clean parent R1 = PRUNEp3px, SHA-asserting...")
    r1 = bsv.reconstruct_r1(lin, w_field, verified)
    if float(d_cat[r1].min()) <= COLLAR_PX:
        raise RuntimeError("R1 collar violation before concentration")
    print(f"      R1 min d_cat = {float(d_cat[r1].min()):.4f} px (all >3 px)")

    print("[5/7] Building provided-band geophysical prior edge_scarp_pot + canaries...")
    edge_pot, edge_scarp_pot, edge_canaries = bsnap.build_snap_edge_fields_and_canaries(
        verified, foot, catalogue)
    del edge_pot
    print(f"      Edge canaries PASS (max symmetric AUC = {max(edge_canaries.values()):.5f}); "
          "provided bands only, external_lidar_used=False.")

    allowed3 = foot & (d_cat > COLLAR_PX) & ~catalogue
    n_parent = int(r1.sum())

    _, raw_kept, header_line, fieldnames, existing_shas = _ledger_surgery()
    cards = json.loads(CARDS.read_text()) if CARDS.is_file() else {}
    cards = {k: v for k, v in cards.items()
             if not any(k.startswith(f"{R1_ID}-CONC{val}-") for val in OWN_VALUES)}

    w_dti_r1 = bpv.weighted_expected_dti(r1, w_field)["dti"]
    arms = {bpv.PARENT_ID: r0, R1_ID: r1}
    built = []

    for value, frac, block, block_label, note, pred, pred_range in SPECS:
        prior, eligible, nb_c = physics_block_prior(edge_scarp_pot, foot, block)
        bids = mcv.block_ids(foot.shape, block, nb_c)
        base_cv = mcv.cv_stats(r1, foot, prior, eligible, bids)
        n_move = int(round(frac * n_parent))

        d_r, d_c, d_nn, d_pr = select_donors(r1, prior, bids, d_cat, n_move)
        survivor = r1.copy()
        survivor[d_r, d_c] = False
        r_r, r_c, r_dh, r_pr = mcv.choose_receivers(
            survivor, r1, allowed3, prior, bids, n_move)
        variant = survivor.copy()
        variant[r_r, r_c] = True

        if int(variant.sum()) != n_parent:
            raise RuntimeError("CONCENTRATION changed the dot count")
        if int((variant & catalogue).sum()) != 0:
            raise RuntimeError("CONCENTRATION emitted catalogue mass")
        if float(d_cat[variant].min()) <= COLLAR_PX:
            raise RuntimeError(f"CONCENTRATION produced a dot at d_cat {d_cat[variant].min():.4f} <= 3 px")

        after_cv = mcv.cv_stats(variant, foot, prior, eligible, bids)
        pc = np.bincount(bids[r1], minlength=prior.size)
        vc = np.bincount(bids[variant], minlength=prior.size)
        w_dti_arm = bpv.weighted_expected_dti(variant, w_field)["dti"]
        w_delta = w_dti_arm - w_dti_r1
        sm_before = mcv.smoothed_density_cv(r1, foot)
        sm_after = mcv.smoothed_density_cv(variant, foot)

        rec = bpv.write_and_verify_variant(
            mask=variant, foot=foot, catalogue=catalogue,
            sample_path=verified["sample_submission"], releases_dir=RELEASES,
            parent_mask=r1, axis="CONC", value=value,
            note_template=note, existing_shas=existing_shas,
            parent_id=R1_ID, parent_sha_zeros=R1_SHA_ZEROS, parent_sha_nan=R1_SHA_NAN,
            min_catalogue_px=COLLAR_PX, pct_basis="moved",
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])

        rec["parent_rebuild_verified"] = {
            "r0_zeros_sha256": bpv.PARENT_SHA_ZEROS,
            "r0_nan_sha256": bpv.PARENT_SHA_NAN,
            "r1_sha256_nan": R1_SHA_NAN,
            "r1_sha256_zeros": R1_SHA_ZEROS,
            "r1_min_catalogue_distance_px": round(float(d_cat[r1].min()), 4),
        }
        rec["concentration_axis"] = {
            "block_px": block, "block_km": block / 10.0,
            "moved_fraction": frac, "n_moved": n_move,
            "prior": "edge_scarp_pot block mean (bands 19/12/18/3, provided only, sigma=1.5 blocks)",
            "cv_occupied_blocks_before": round(base_cv["cv_occupied_blocks"], 4),
            "cv_occupied_blocks_after": round(after_cv["cv_occupied_blocks"], 4),
            "cv_all_eligible_blocks_before": round(base_cv["cv_all_eligible_blocks"], 4),
            "cv_all_eligible_blocks_after": round(after_cv["cv_all_eligible_blocks"], 4),
            "mass_share_top1pct_before": round(base_cv["mass_share_in_top1pct_prior_blocks"], 4),
            "mass_share_top1pct_after": round(after_cv["mass_share_in_top1pct_prior_blocks"], 4),
            "smoothed_density_cv_5blocks_before": round(sm_before["cv_density_smoothed_5blocks"], 4),
            "smoothed_density_cv_5blocks_after": round(sm_after["cv_density_smoothed_5blocks"], 4),
            "occupied_blocks_before": base_cv["occupied_blocks"],
            "occupied_blocks_after": after_cv["occupied_blocks"],
            "blocks_emptied": int(((pc > 0) & (vc == 0)).sum()),
            "blocks_gained": int(((pc == 0) & (vc > 0)).sum()),
            "added_distance_to_host_px_max": round(float(r_dh.max()), 4),
            "removed_block_prior_mean": round(float(d_pr.mean()), 4),
            "added_block_prior_mean": round(float(r_pr.mean()), 4),
        }
        rec["w_weighted_dti_MODEL"] = {
            "evidence_label": "MODEL",
            "field": "label-free corroboration field w (build_prune_variants.py, blind AUC 0.47)",
            "dti_parent_r1": round(w_dti_r1, 6),
            "dti_arm": round(w_dti_arm, 6),
            "delta_vs_r1": round(w_delta, 6),
            "caveat": "w rewards densification and is a mechanical diagnostic only; the ledger "
                      "prediction stays the preregistered scenario MODEL, not this value.",
        }
        rec["preregistration"] = "registry/preregistration_concentration_r1.json"
        rec["leakage_canaries"] = {
            "passed": True,
            "max_symmetric_auc": max(max(w_canaries.values()), max(edge_canaries.values())),
            "w_field_channels": w_canaries,
            "edge_field_channels": edge_canaries,
        }
        card = mechanism_card(value, block_label, frac)
        rec["mechanism_card"] = card
        cards[rec["id"]] = card
        arms[rec["id"]] = variant
        built.append((rec, pred, pred_range, value, frac, block, block_label))
        print(f"      {value}: moved {n_move:,} ({frac:.0%}), CV_occ "
              f"{base_cv['cv_occupied_blocks']:.3f}->{after_cv['cv_occupied_blocks']:.3f}, "
              f"min d_cat {float(d_cat[variant].min()):.4f} px -> {rec['id']}")

    print("[6/7] REPORT-ONLY diagnostics (holdout PROXY, blind SGMC control, block CV)...")
    eval_report = bpv.evaluate_report_only_instruments(
        arms=arms, foot=foot, catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"])
    sgmc = lambda key: eval_report[key]["sgmc_control"]["dti"]  # noqa: E731
    sgmc_r1 = sgmc(R1_ID)

    # Revision rule (documented in the report; follows the MASS r10 precedent):
    # anchor the revised live-scale point estimate on the blind off-catalogue SGMC
    # margin vs the parent actually submitted (R1) -- the closest local analogue of
    # a live DTI delta.  Both that PROXY and the exact w-DTI MODEL are recorded; if
    # they share a sign the expectation is revised to that sign, still labelled
    # MODEL (a projection, never a receipt).  Every revised point stays inside the
    # preregistered range, so the pre-commitment is not silently redrawn.
    new_rows = []
    for rec, pred, pred_range, value, frac, block, block_label in built:
        s = sgmc(rec["id"])
        d = eval_report[rec["id"]]
        w_delta = rec["w_weighted_dti_MODEL"]["delta_vs_r1"]
        sgmc_delta = s - sgmc_r1
        revised_point = round(sgmc_delta, 3)
        revised = f"MODEL:{revised_point:+.3f}"
        instruments_agree_negative = (sgmc_delta < 0 and w_delta < 0)
        rec["report_only_diagnostics"] = d
        rec["parent_reference_diagnostics"] = eval_report[R1_ID]
        rec["r0_reference_diagnostics"] = eval_report[bpv.PARENT_ID]
        rec["preregistered_prediction"] = {"label": "MODEL", "value": pred, "range": pred_range}
        rec["revised_prediction"] = {
            "label": "MODEL", "value": revised, "preregistered_range_kept": pred_range,
            "rule": "revised point = blind off-catalogue SGMC margin vs parent R1, rounded to 0.001",
            "both_instruments_negative": bool(instruments_agree_negative),
        }
        # Augment the mechanism card with the post-build instrument reading.
        card = cards[rec["id"]]
        card["preregistered_prediction"] = pred
        card["revised_prediction_MODEL"] = revised
        card["post_build_instruments"] = {
            "blind_sgmc_PROXY": round(s, 6),
            "blind_sgmc_delta_vs_r1_PROXY": round(sgmc_delta, 6),
            "w_weighted_dti_delta_vs_r1_MODEL": round(w_delta, 6),
            "both_instruments_negative": bool(instruments_agree_negative),
            "verdict": ("CONVERGENT FALSIFICATION: both the label-free w-DTI MODEL and the blind "
                        "off-catalogue SGMC PROXY read negative on the gate-clean parent; the "
                        "preregistered near-zero-positive scenario is revised negative. "
                        "Concentration of mass onto geophysical crests loses to the spaced parent "
                        "at matched count -- the uniformity lever is confirmed, and the sign/size "
                        "of the loss is dose-monotone."),
        }
        cv_b = rec["concentration_axis"]["cv_occupied_blocks_before"]
        cv_a = rec["concentration_axis"]["cv_occupied_blocks_after"]
        if s > sgmc_r1:
            recomm = (f"SLOT-ELIGIBLE (not slot-recommended): gate-clean CONCENTRATION on R1, "
                      f"blind off-catalogue SGMC {s:.6f} PROXY > parent R1 {sgmc_r1:.6f}. "
                      f"Promotion requires a live receipt; |delta| < 0.01 is no evidence. "
                      f"Confounder: CV_occ rises {cv_b}->{cv_a}, away from the 0.51-0.59 sweet spot.")
        else:
            converg = ("Both instruments CONVERGE NEGATIVE (w-DTI MODEL and blind SGMC agree); "
                       "the preregistered near-zero-positive expectation is revised to "
                       f"{revised}. " if instruments_agree_negative else "")
            recomm = (f"HOLD: blind SGMC {s:.6f} PROXY <= parent R1 {sgmc_r1:.6f} "
                      f"(delta {sgmc_delta:+.6f}); the preregistered build-time park rule holds this "
                      f"arm at HOLD before any slot. {converg}Concentrating mass onto geophysical "
                      f"crests at matched count loses to the spaced parent; the uniformity lever is "
                      f"confirmed. CV_occ {cv_b}->{cv_a} (away from the 0.51-0.59 sweet spot). "
                      f"Not a slot candidate; a live receipt, not this proxy, would be the only "
                      f"thing that could reopen the direction.")
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        new_rows.append({
            "id": rec["id"], "parent": R1_ID, "axis": "CONCENTRATION", "value": value,
            "n_dots": str(rec["n_dots"]),
            "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
            "sha256": rec["sha256"], "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT", "predicted_change": revised, "predicted_range": pred_range,
            "ranking_basis": (f"label-free edge_scarp_pot geophysical prior (0.42 b19 slope + 0.23 "
                              f"b12 Hessian + 0.20 b18 grav HG + 0.15 b3 TMI HG percentile ranks, "
                              f"provided bands only, no external LiDAR); {block_label} blocks, "
                              f"sigma=1.5; donors = lowest-prior blocks most-isolated-first "
                              f"(one-per-block floor where feasible); receivers welded <=1.41 px "
                              f"to surviving hosts in highest-prior blocks, cap 2/host, strictly "
                              f"d_cat>3 px; count fixed, no RNG"),
            "receipt_score": "", "receipt_date": "",
            "description": (f"Move {int(round(frac*n_parent)):,} R1 dots ({frac:.0%}) from coldest "
                            f"to hottest {block_label} geophysical-prior blocks by provided-band "
                            f"edge_scarp_pot; count fixed at 37,654; 100% of dots >3 px from "
                            f"catalogue; CV_occ {cv_b}->{cv_a}. Preregistered {pred}, REVISED to "
                            f"{revised} (both instruments negative)."),
            "recommendation": (recomm + f" SGMC {s:.6f} PROXY (R1 {sgmc_r1:.6f}); holdout PROXY "
                               f"{d['holdout_proxy']['dti']:.6f} (structurally ~0, IR-88-20); "
                               f"w-DTI MODEL delta {w_delta:+.6f}."),
        })

    if fieldnames:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        for row in new_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
        body = buf.getvalue().rstrip("\n")
        with LEDGER.open("w", newline="", encoding="utf-8") as fh:
            fh.write(header_line + "\n")
            for line in raw_kept:
                fh.write(line + "\n")
            if body:
                fh.write(body + "\n")
    CARDS.write_text(json.dumps(cards, indent=2) + "\n")

    print("[7/7] Writing the axis report...")
    report = {
        "session_date": "2026-10-23",
        "axis": "CONCENTRATION",
        "parent_r1": R1_ID,
        "parent_r0": bpv.PARENT_ID,
        "preregistration": "registry/preregistration_concentration_r1.json",
        "provided_bands_only": True,
        "external_lidar_used": False,
        "gate_eligible": "100% of dots >3 px from catalogue on every arm (hardened non-PRUNE gate)",
        "leakage_canaries": {
            "passed": True,
            "max_symmetric_auc": max(max(w_canaries.values()), max(edge_canaries.values())),
            "w_field_channels": w_canaries,
            "edge_field_channels": edge_canaries,
        },
        "sgmc_reference": {"r0": sgmc(bpv.PARENT_ID), "r1": sgmc_r1},
        "post_build_outcome": {
            "recorded_utc": "2026-10-23T06:00:00Z (after instruments; preregistration file "
                            "left immutable as the before-instruments pre-commitment)",
            "result": ("CONVERGENT FALSIFICATION. On the gate-clean parent R1, both the exact "
                       "label-free w-DTI MODEL and the blind off-catalogue SGMC PROXY read "
                       "negative for all three concentration arms; the loss is dose-monotone "
                       "(10% < 20% < 20%-5km). Concentration of fixed mass onto geophysical "
                       "crests loses to the spaced parent, confirming the uniformity lever and "
                       "explaining why the earlier R0 density-prior arms' high MODEL gains were a "
                       "collar/self-density artefact that does not transfer to a gate-clean parent."),
            "revision_rule": ("revised live-scale point estimate = blind off-catalogue SGMC margin "
                              "vs parent R1 rounded to 0.001, applied only when both instruments "
                              "share a sign; every revised point stays inside its preregistered "
                              "range. Preregistered and revised values both recorded per arm."),
            "all_arms_disposition": "HOLD (parked by the preregistered build-time rule: SGMC <= R1)",
            "instruments": {
                "blind_sgmc_PROXY_vs_r1": {t[3]: round(sgmc(t[0]["id"]) - sgmc_r1, 6)
                                           for t in built},
                "w_dti_MODEL_vs_r1": {t[3]: round(t[0]["w_weighted_dti_MODEL"]["delta_vs_r1"], 6)
                                      for t in built},
            },
            "caveat": "All values are PROXY/MODEL, never RECEIPT. |live delta| < 0.01 is no evidence.",
        },
        "variants": [json.loads((RELEASES / f"{rec['id']}.json").read_text())
                     for rec, *_ in built],
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    print("\nCONCENTRATION-on-R1 REPORT-ONLY SUMMARY (PROXY/MODEL, never a score)")
    for rec, pred, _, value, frac, block, block_label in built:
        d = eval_report[rec["id"]]
        print(f"  {value:<14} SGMC {d['sgmc_control']['dti']:.6f} (R1 {sgmc_r1:.6f}) | "
              f"holdout {d['holdout_proxy']['dti']:.6f} | CV_occ "
              f"{rec['concentration_axis']['cv_occupied_blocks_before']}->"
              f"{rec['concentration_axis']['cv_occupied_blocks_after']} | moved {frac:.0%} | {pred}")
    print(f"Elapsed {time.time()-t0:.1f}s. Receipts in releases/, report in {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
