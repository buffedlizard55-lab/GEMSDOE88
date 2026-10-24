#!/usr/bin/env python3
"""AXIS=MASS on gate-clean parent R1 (PRUNEp3px-6f7ae705) - the queued MASS-on-R1 session.

SLOT_PLAN.md (2026-10-23) proposes exactly this build: "MASS-on-R1 - the same 10%
exact-marginal add on gate-clean R1; the gate-clean form of MASS's only positive
arm - as a separate single-axis session". The six ledgered MASS rows all have
parent R0 (h33-h33-2-b2); no (R1, MASS, value) pair exists, so every pair here is
new and the experiment is a controlled single-axis edit of one named parent.

Sequence (fail-closed):
  1. verify all 15 manifest SHA-256 pins and byte-exactly rebuild R0 (both SHAs).
  2. rebuild the label-free physical corroboration field w and the 15-channel
     leakage canaries (symmetric AUC <= 0.90 or stop).
  3. re-derive R1 from its recorded recipe and assert BOTH recorded GeoTIFF
     SHA-256 values (6f7ae705... / dc6f090d...) before editing a single dot.
  4. three arms at the brief-mandated 10% dose (3,765 dots), same exact iterative
     marginal expected-DTI ranking as the R0 MASS session and as R1's own refill:
       r10minus - drop the 3,765 lowest-ranked R1 dots          -> 33,889 dots
       r10plus  - add the 3,765 next-ranked un-emitted dots      -> 41,419 dots
                  (H19-5 support, d_cat > 3 px, never in R1)
       r10swap  - drop the 3,765 lowest + add 3,765 next-ranked  -> 37,654 dots
     Every arm stays 100% at d_cat >= 3.1623 px (R1's own minimum) with zero
     catalogue mass: MASS is not PRUNE, so no sub-3 px mass is ever created.
  5. write NaN/zeros twins + zips, re-read from disk, enforce every MUST gate,
     run the report-only instruments (catalogue hide-and-recover PROXY, blind
     SGMC control, 10/12 km block-density CV), append three ledger rows.

Predictions were frozen in registry/mass_r1_preregistration.json BEFORE this
script computes anything. No DrivenData / Dropbox contact; nothing is submitted.
"""
from __future__ import annotations

import csv
import json
import tempfile
import time
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_variants as bpv  # noqa: E402

R0_ID = "h33-h33-2-b2"
R1_ID = "h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705"
R1_SHA_NAN = "6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9"
R1_SHA_ZEROS = "dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f"
FIXED_DATE = "20261023"
SEED = 20261023
AXIS = "MASS"
FRACTION = 0.10
PREREG = ROOT / "registry" / "mass_r1_preregistration.json"

CARDS = {
    "r10minus": {
        "hypothesis": "R1 still carries removable dead mass even after its PRUNE<=3 px refill. R1 began as the 2.8 px Poisson-disk thinning of H19-5; 35,483 of its dots are geometric thinnings, selected for spacing rather than evidence, and only 2,171 refill dots were ever ranked by expected DTI. Deleting the 3,765 dots whose removal costs the least kernel credit T while still removing one unit of mass S should raise DTI, because DTI = T / (0.2T + 0.2(S-M) + 0.8|G|) charges every emitted dot through S whether or not it covers a fault.",
        "mechanism": "Under the 300 m triangular kernel a dot only pays if its credit exceeds about 0.2*DTI (~0.056 at DTI 0.28). Dots that already have a stronger neighbour on the same strand within 300 m, or sit on ridges that the TMI horizontal-gradient, isostatic-gravity gradient and GDR-1391 geothermometry channels do not corroborate, add S but almost no unique T. The exact marginal greedy drop removes the dots with the smallest T-loss per unit S, shrinking the denominator immediately and T only by the third-order residual credit each uniquely held.",
        "non_fault_mimic": "The corroboration field w is built from potential-field and topographic derivatives. A genuinely blind, low-offset or sediment-masked fault has a weak magnetic and gravity expression, and GeoDAWN Area 2's 400 m flight-line spacing can put its ridge crest up to a kernel radius off the true trace. Dropping 'low-w' dots therefore preferentially deletes blind faults - exactly the new-fault population - so a live DROP is the expected outcome if w is a weak fault detector (its blind AUC for SGMC-credited dots is 0.4724, IR-88-38) rather than a strong one.",
        "predicted_sign_size": "Preregistered MODEL -0.007 vs R1 (range -0.016 to +0.004). On R0 the identical 10% drop measured -0.0084 w-model and -0.0081 blind SGMC; the random-donor control put the pure -10% dose effect at -0.0062. R1 has no sub-3 px collar dead mass left to shed, so the arm cannot beat the R0 read; it tests whether the gate-clean parent behaves any differently.",
        "falsifier": "A live change >= +0.01 vs R1 falsifies the saturation reading and reopens mass reduction as a lever on the gate-clean parent, implying the geometric thinning left removable redundancy even after the PRUNE refill. A live change <= -0.01 confirms deletion destroys real coverage and closes the minus arm; |delta| < 0.01 is no evidence.",
    },
    "r10plus": {
        "hypothesis": "Adding mass is nearly saturated but still marginally positive on a gate-clean parent: the un-emitted H19-5 support at d_cat > 3 px still contains strand tips, step-over gaps and second-order splays that no R1 dot covers, and on R0 the add arm was MASS's only blind-positive arm (+0.0029 SGMC, +0.0107 w-model). R1's 2,171-dot refill consumed the best 2,171 cells of that pool first, so the residual 3,765 picks are weaker but not worthless.",
        "mechanism": "Kernel credit at a truth cell g is the BEST dot within 300 m, C_A(g) = max_x k(||g-x||). Once a strand is sampled every 280 m by the 2.8 px thinning, a new dot on that strand has near-zero marginal dT and raises S by one; the exact greedy add therefore spends its budget on whatever residual w remains - uncovered tips and relay gaps - and the mean dT per added dot directly measures how saturated R1 is. Unlike the R0 add arm, every dot here is born >3 px from the catalogue, so the arm is submission-eligible under the hardened gate with no waiver.",
        "non_fault_mimic": "H19-5 is a multi-line ridge detector, so the pool also contains flight-line levelling artefacts, drainage-incision ridges and lithologic contacts that carry no new-fault labels. If those dominate the residual pool after the refill skimmed the best cells, the added dots pay nothing while costing S, and the arm conflates 'add coverage' with 'add ridge artefacts'. The 400 m flight-line uncertainty also means some apparent step-overs are positional noise, not real relay structures.",
        "predicted_sign_size": "Preregistered MODEL +0.005 vs R1 (range -0.005 to +0.016), roughly half the R0 add arm's +0.0107 w-model because R1's refill already removed the top 2,171 candidates from the same pool and the random-receiver pure dose effect was only +0.0011. This is the queued gate-clean form of MASS's only positive arm.",
        "falsifier": "A live loss <= -0.01 falsifies the residual-coverage hypothesis and retires mass increase on both parents, supporting the reading that the 0.00-0.19 physical-signal lanes failed from weak signals rather than too few dots. A gain >= +0.01 proves substantial unsampled strand length remains and reopens count as a lever on the gate-clean parent; |delta| < 0.01 is no evidence.",
    },
    "r10swap": {
        "hypothesis": "At fixed 37,654 dots, selection quality is the only thing left on the table: replacing the 3,765 lowest-credit R1 dots with the 3,765 best un-emitted >3 px candidates must move DTI through T alone, because S is frozen. If the exact-marginal ranking carries information beyond the geometric thinning, the swap beats R1 without changing mass or violating any collar.",
        "mechanism": "With S fixed at 37,654, DTI changes only through T and M. Dropped dots minimise lost T by the exact marginal drop rule; added dots maximise gained T on cells R1 never sampled. The arm is the superposition of r10minus's denominator saving and r10plus's numerator gain, and its sign is the product of how redundant R1's worst decile is and how much uncovered credit the depleted pool still reaches. Because R1 is itself an exact-marginal product (its refill was ranked the same way), this also tests whether a second w-ranked pass adds anything after the first.",
        "non_fault_mimic": "A pure w-ranking play inherits every bias of w: TMI/gravity gradients favour basement steps and lithologic contacts, and the GDR-1391 term concentrates near known geothermal systems. If new-fault labels are dominated by Quaternary scarps with little potential-field expression, the swap systematically trades real scarps for geophysically loud but geologically dead lineaments - a live loss even where the w-model predicts a gain. The R0 swap already showed this pattern: +0.0029 w-model but -0.0040 blind SGMC.",
        "predicted_sign_size": "Preregistered MODEL +0.001 vs R1 (range -0.009 to +0.011). The random-donor control bounds the w-ranking effect at about +/-0.0018 and w's blind AUC is 0.4724, so the honest expectation is approximately zero; the arm's value is the diagnostic, not an expected gain.",
        "falsifier": "A live change below +0.01 falsifies w-ranked reselection as a slot-worthy lever and says a geometric thinning plus one exact-marginal refill already extracts everything w can rank; redirect remaining slots to spacing/geometry axes. A gain >= +0.01 would show a second ranking pass still finds real fault coverage at fixed count.",
    },
}

RANKING_BASIS = (
    "exact iterative marginal expected-DTI under the pinned label-free physical field w "
    "(same ranking that built R1's own PRUNE refill; R1 stores no per-dot score)"
)


def _prereg() -> dict:
    return json.loads(PREREG.read_text(encoding="utf-8"))


def _nearest_parent_distance(parent_mask: np.ndarray, added_mask: np.ndarray) -> dict:
    py, px = np.nonzero(parent_mask)
    ay, ax = np.nonzero(added_mask)
    if len(ay) == 0:
        return {"n_added": 0}
    tree = cKDTree(np.column_stack([py, px]))
    d, _ = tree.query(np.column_stack([ay, ax]))
    return {
        "n_added": int(len(ay)),
        "mean_px": round(float(d.mean()), 3),
        "median_px": round(float(np.median(d)), 3),
        "p90_px": round(float(np.quantile(d, 0.90)), 3),
        "frac_within_3px_of_a_parent_dot": round(float((d <= 3.0).mean()), 4),
        "frac_within_kernel_radius_3px": round(float((d <= 3.0).mean()), 4),
    }


def _rederive_r1(verified: dict, lin: dict, w_field: np.ndarray) -> np.ndarray:
    """Re-run the recorded PRUNEp3px recipe and assert both recorded R1 hashes."""
    r0, h19_5, d_cat, foot, catalogue = (
        lin["r0"], lin["h19_5"], lin["d_cat"], lin["foot"], lin["catalogue"]
    )
    r0_gt3 = r0 & (d_cat > 3.0)
    n_remove = int(r0.sum() - r0_gt3.sum())
    assert n_remove == 2171, n_remove
    r1 = bpv.select_exact_marginal_dti_add(
        base_mask=r0_gt3,
        cand_mask=h19_5 & ~r0_gt3 & (d_cat > 3.0),
        w=w_field,
        n_add=n_remove,
    )
    assert int(r1.sum()) == 37_654
    assert int((r1 & catalogue).sum()) == 0
    assert float(d_cat[r1].min()) == 3.1622776601683795
    # Byte-exact assertion against BOTH recorded R1 GeoTIFFs before any edit.
    import rasterio
    prof_nan = rasterio_open_profile(verified["sample_submission"])
    prof_zeros = rasterio_open_profile(verified["sample_submission"], nodata_none=True)
    with tempfile.TemporaryDirectory() as td:
        p_nan = Path(td) / "r1_nan.tif"
        p_zeros = Path(td) / "r1_zeros.tif"
        with rasterio.open(p_nan, "w", **prof_nan) as dst:
            dst.write(np.where(foot, r1.astype(np.float32), np.nan).astype(np.float32), 1)
        with rasterio.open(p_zeros, "w", **prof_zeros) as dst:
            dst.write(np.where(foot, r1.astype(np.float32), 0.0).astype(np.float32), 1)
        got_nan = bpv.sha256_file(p_nan)
        got_zeros = bpv.sha256_file(p_zeros)
    assert got_nan == R1_SHA_NAN, f"R1 NaN re-derivation mismatch: {got_nan}"
    assert got_zeros == R1_SHA_ZEROS, f"R1 zeros re-derivation mismatch: {got_zeros}"
    return r1


def rasterio_open_profile(sample_path: Path, *, nodata_none: bool = False) -> dict:
    import rasterio
    with rasterio.open(sample_path) as tpl:
        prof = tpl.profile.copy()
    prof.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        compress="deflate",
        predictor=3,
        zlevel=9,
        tiled=True,
        blockxsize=256,
        blockysize=256,
        nodata=np.nan if not nodata_none else None,
    )
    return prof


def main() -> int:
    t0 = time.time()
    pre = _prereg()
    print("[1/7] Verifying SHA-256 manifest pins and rebuilding parent R0 ...")
    verified = bpv.verify_manifest()
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    assert int(r0.sum()) == 37_654
    assert lin["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS
    assert lin["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    print(
        f"      {len(verified)} pins OK | EXACT R0 REBUILD OK: 37,654 dots | "
        f"zeros={lin['rebuilt_zeros_sha256'][:12]}... nan={lin['rebuilt_nan_sha256'][:12]}..."
    )

    print("[2/7] Rebuilding physical corroboration field w and leakage canaries ...")
    w_field, canaries = bpv.build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    max_auc = max(canaries.values())
    print(f"      canaries: {len(canaries)} channels, max symmetric AUC = {max_auc:.4f}")
    if max_auc > 0.90:
        raise RuntimeError(f"Leakage canary tripped: symmetric AUC {max_auc:.4f} > 0.90")

    print("[3/7] Re-deriving R1 (PRUNEp3px) and asserting both recorded SHA-256 values ...")
    r1 = _rederive_r1(verified, lin, w_field)
    n_parent = int(r1.sum())
    print(f"      EXACT R1 RE-DERIVATION OK: {n_parent:,} dots | nan={R1_SHA_NAN[:12]}... zeros={R1_SHA_ZEROS[:12]}...")

    base_terms = bpv.weighted_expected_dti(r1, w_field)
    print(
        f"      R1 w-model: DTI={base_terms['dti']:.6f} T={base_terms['T']:.1f} "
        f"S={base_terms['S']:.0f} M={base_terms['M']:.1f}"
    )

    n_dose = int(round(FRACTION * n_parent))
    assert n_dose == 3_765
    print(f"[4/7] Allocating 3 AXIS=MASS arms at a fixed 10% dose ({n_dose:,} dots) on R1 ...")
    cand_pool = h19_5 & ~r1 & (d_cat > 3.0)
    print(f"      candidate pool (H19-5 & ~R1 & d_cat>3px): {int(cand_pool.sum()):,} px")

    t = time.time()
    m_minus = bpv.select_exact_marginal_dti_drop(
        base_mask=r1, drop_pool_mask=r1, w=w_field, n_drop=n_dose
    )
    print(f"      r10minus greedy drop done in {time.time() - t:.0f}s -> {int(m_minus.sum()):,} dots")

    t = time.time()
    m_plus = bpv.select_exact_marginal_dti_add(
        base_mask=r1, cand_mask=cand_pool, w=w_field, n_add=n_dose
    )
    print(f"      r10plus greedy add done in {time.time() - t:.0f}s -> {int(m_plus.sum()):,} dots")

    t = time.time()
    m_swap = bpv.select_exact_marginal_dti_add(
        base_mask=m_minus, cand_mask=cand_pool, w=w_field, n_add=n_dose
    )
    print(f"      r10swap greedy add done in {time.time() - t:.0f}s -> {int(m_swap.sum()):,} dots")

    assert int(m_minus.sum()) == 33_889
    assert int(m_plus.sum()) == 41_419
    assert int(m_swap.sum()) == 37_654
    assert not (m_swap & ~m_minus & r1).any(), "swap must not re-add dropped R1 dots"
    r1_min = float(d_cat[r1].min())  # sqrt(10) = 3.16227766..., recorded as 3.1623
    for name, mask in (("r10minus", m_minus), ("r10plus", m_plus), ("r10swap", m_swap)):
        assert int((mask & catalogue).sum()) == 0, name
        assert float(d_cat[mask].min()) >= r1_min - 1e-9, (name, float(d_cat[mask].min()))
        added = mask & ~r1
        if added.any():
            assert float(d_cat[added].min()) > 3.0, name

    w_model = {}
    for name, mask in (("r10minus", m_minus), ("r10plus", m_plus), ("r10swap", m_swap)):
        tm = bpv.weighted_expected_dti(mask, w_field)
        w_model[name] = {
            "dti": round(tm["dti"], 6),
            "delta_vs_r1": round(tm["dti"] - base_terms["dti"], 6),
            "T": round(tm["T"], 3),
            "S": float(tm["S"]),
            "M": round(tm["M"], 3),
            "denom": round(tm["denom"], 3),
        }
        print(f"      w-model {name}: DTI={tm['dti']:.6f} (delta vs R1 {tm['dti'] - base_terms['dti']:+.6f})")

    print("[5/7] Writing GeoTIFFs, re-reading from disk and enforcing MUST gates ...")
    ledger_path = ROOT / "ledger" / "submissions.csv"
    existing_rows: list[dict[str, str]] = []
    existing_shas: set[str] = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS}
    if ledger_path.is_file():
        with ledger_path.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("parent") == R1_ID and row.get("axis") == AXIS and row.get("value") in CARDS:
                    continue  # idempotent re-run replaces only this session's arms
                existing_rows.append(row)
                if row.get("sha256"):
                    existing_shas.add(row["sha256"])
                if row.get("sha256_zeros"):
                    existing_shas.add(row["sha256_zeros"])

    releases_dir = ROOT / "releases"
    for old_p in releases_dir.glob(f"{R1_ID}-MASSr*"):
        old_p.unlink()

    arms = {
        "r10minus": (m_minus, "R1 PRUNEp3px 6f7ae705; MASS -3765 lowest exact-marginal dots (37654->33889); pred {pred} MODEL"),
        "r10plus": (m_plus, "R1 PRUNEp3px 6f7ae705; MASS +3765 next-ranked un-emitted dots d_cat>3px (37654->41419); pred {pred} MODEL"),
        "r10swap": (m_swap, "R1 PRUNEp3px 6f7ae705; MASS swap 3765 lowest for 3765 next-ranked, fixed 37654; pred {pred} MODEL"),
    }

    built: dict[str, dict] = {}
    for value, (mask, note_tmpl) in arms.items():
        pred = f"{w_model[value]['delta_vs_r1']:+.3f}"
        rec = bpv.write_and_verify_variant(
            mask=mask,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=releases_dir,
            parent_mask=r1,
            axis=AXIS,
            value=value,
            note_template=note_tmpl.format(pred=pred, sha8="{sha8}"),
            existing_shas=existing_shas,
            parent_id=R1_ID,
            parent_sha_zeros=R1_SHA_ZEROS,
            parent_sha_nan=R1_SHA_NAN,
            min_catalogue_px=3.0,
            pct_basis="max",
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])
        built[value] = rec
        print(
            f"      {rec['id']} | dots={rec['n_dots']:,} | moved={rec['parent_diff']['pct_changed_moved']:.2f}% "
            f"(sym={rec['parent_diff']['pct_changed_sym_diff']:.2f}%) | min_dcat={rec['parent_diff']['min_dist_catalogue_px']:.4f}px"
        )

    print("[6/7] REPORT-ONLY diagnostics (catalogue holdout PROXY, SGMC control, block CV) ...")
    eval_arms: dict[str, np.ndarray] = {R0_ID: r0, R1_ID: r1}
    for value, (mask, _) in arms.items():
        eval_arms[built[value]["id"]] = mask
    eval_report = bpv.evaluate_report_only_instruments(
        arms=eval_arms, foot=foot, catalogue=catalogue, sgmc_path=verified["sgmc_faults_control"]
    )

    print("[7/7] Writing ledger rows, mechanism cards and evidence ...")
    cards_path = ROOT / "ledger" / "mechanism_cards.json"
    cards = json.loads(cards_path.read_text()) if cards_path.is_file() else {}
    cards = {k: val for k, val in cards.items() if not k.startswith(f"{R1_ID}-MASSr")}

    new_rows = []
    for value, (mask, _) in arms.items():
        rec = built[value]
        diag = eval_report[rec["id"]]
        r1d = eval_report[R1_ID]
        r0d = eval_report[R0_ID]
        added = mask & ~r1
        removed = r1 & ~mask
        extra = {
            "preregistered_prediction": pre["arms"][value]["preregistered_prediction"],
            "preregistered_range": pre["arms"][value]["preregistered_range"],
            "w_model": w_model[value],
            "w_model_caveat": (
                "IN-SAMPLE and optimistic: the same field w both ranks and scores the arm, "
                "and w is a ~0.68-AUC proxy for catalogue faults but 0.4724 blind AUC for "
                "SGMC-credited dots (IR-88-38). PROXY, never a score."
            ),
            "r1_w_model": {
                "dti": round(base_terms["dti"], 6),
                "T": round(base_terms["T"], 3),
                "S": float(base_terms["S"]),
                "M": round(base_terms["M"], 3),
            },
            "r1_reference_diagnostics": r1d,
            "r0_reference_diagnostics": r0d,
            "report_only_diagnostics": diag,
            "sgmc_delta_vs_r1": round(diag["sgmc_control"]["dti"] - r1d["sgmc_control"]["dti"], 6),
            "saturation_diagnostic_added_dots": _nearest_parent_distance(r1, added),
            "removed_dots": {
                "n": int(removed.sum()),
                "mean_d_cat_px": round(float(d_cat[removed].mean()), 3) if removed.any() else None,
                "mean_w": round(float(w_field[removed].mean()), 6) if removed.any() else None,
            },
            "added_dots": {
                "n": int(added.sum()),
                "min_d_cat_px": round(float(d_cat[added].min()), 3) if added.any() else None,
                "mean_d_cat_px": round(float(d_cat[added].mean()), 3) if added.any() else None,
                "mean_w": round(float(w_field[added].mean()), 6) if added.any() else None,
            },
            "parent_dots_mean_w": round(float(w_field[r1].mean()), 6),
            "leakage_canaries": {"passed": True, "max_symmetric_auc": max_auc, "channels": canaries},
        }
        rec.update(extra)
        (releases_dir / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        cards[rec["id"]] = {
            "parent": R1_ID,
            "axis": AXIS,
            "value": value,
            "preregistered_prediction": pre["arms"][value]["preregistered_prediction"],
            "preregistered_range": pre["arms"][value]["preregistered_range"],
            **CARDS[value],
            "post_build_w_model_delta_vs_r1": f"{w_model[value]['delta_vs_r1']:+.6f}",
            "post_build_report_only": {
                "sgmc_off_catalogue_dti": diag["sgmc_control"]["dti"],
                "r1_sgmc_off_catalogue_dti": r1d["sgmc_control"]["dti"],
                "sgmc_delta_vs_r1": round(diag["sgmc_control"]["dti"] - r1d["sgmc_control"]["dti"], 6),
                "r0_sgmc_off_catalogue_dti": r0d["sgmc_control"]["dti"],
                "cv_12km": diag["block_density_cv"]["cv_12km_120px_interior"],
                "r1_cv_12km": r1d["block_density_cv"]["cv_12km_120px_interior"],
            },
        }
        hp = diag["holdout_proxy"]
        new_rows.append(
            {
                "id": rec["id"],
                "parent": R1_ID,
                "axis": AXIS,
                "value": value,
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{w_model[value]['delta_vs_r1']:+.3f}",
                "predicted_range": pre["arms"][value]["preregistered_range"],
                "ranking_basis": RANKING_BASIS,
                "receipt_score": "",
                "receipt_date": "",
                "description": (
                    pre["arms"][value]["operation"]
                    + f" | preregistered {pre['arms'][value]['preregistered_prediction']} MODEL vs R1; "
                    + f"post-build w-model delta {w_model[value]['delta_vs_r1']:+.4f} (in-sample, optimistic); "
                    + f"SGMC off-cat {diag['sgmc_control']['dti']:.5f} vs R1 {r1d['sgmc_control']['dti']:.5f} "
                    + f"(delta {diag['sgmc_control']['dti'] - r1d['sgmc_control']['dti']:+.5f}, "
                    + f"R0 {r0d['sgmc_control']['dti']:.5f}); holdout PROXY {hp['dti']:.5f} "
                    + f"(delta vs R0 {hp['paired_delta_vs_r0']:+.5f}, n={hp['withheld_positives']}); "
                    + f"CV12km {diag['block_density_cv']['cv_12km_120px_interior']:.4f} "
                    + f"vs R1 {r1d['block_density_cv']['cv_12km_120px_interior']:.4f}; "
                    + f"min d_cat {rec['parent_diff']['min_dist_catalogue_px']:.4f} px, 100% of dots >3 px."
                ),
                "recommendation": RECOMMENDATION[value],
            }
        )

    fieldnames = [
        "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256", "sha256_zeros",
        "status", "predicted_change", "predicted_range", "ranking_basis", "receipt_score",
        "receipt_date", "description", "recommendation",
    ]
    with ledger_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for r in [*existing_rows, *new_rows]:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
    cards_path.write_text(json.dumps(cards, indent=2) + "\n")

    summary = {
        "schema": "gems88.mass-r1-axis-report.v1",
        "session_date": "2026-10-23",
        "axis": AXIS,
        "parent": {
            "id": R1_ID,
            "n_dots": n_parent,
            "rederived_nan_sha256": R1_SHA_NAN,
            "rederived_zeros_sha256": R1_SHA_ZEROS,
            "sha_asserted_before_edit": True,
            "min_d_cat_px": round(float(d_cat[r1].min()), 4),
            "w_model": {
                "dti": round(base_terms["dti"], 6),
                "T": round(base_terms["T"], 3),
                "S": float(base_terms["S"]),
                "M": round(base_terms["M"], 3),
                "W": round(base_terms["W"], 3),
            },
        },
        "r0_reference": {
            "id": R0_ID,
            "rebuilt_zeros_sha256": lin["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lin["rebuilt_nan_sha256"],
        },
        "verified_inputs": len(verified),
        "leakage_canaries": {"passed": True, "max_symmetric_auc": max_auc, "channels": canaries},
        "ranking_definition": pre["ranking_definition"],
        "dose": {"fraction": FRACTION, "n_dots": n_dose},
        "candidate_pool_px": int(cand_pool.sum()),
        "preregistered_predictions": {k: v["preregistered_prediction"] for k, v in pre["arms"].items()},
        "w_model_deltas_vs_r1": w_model,
        "report_only": eval_report,
        "variants": [{k: v for k, v in built[name].items() if k != "leakage_canaries"} for name in arms],
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    (ROOT / "evidence" / "mass_r1_axis_report.json").write_text(json.dumps(summary, indent=2) + "\n")

    print("\n=== SUMMARY OF BUILT AXIS=MASS-on-R1 VARIANTS ===")
    for value in arms:
        rec = built[value]
        diag = eval_report[rec["id"]]
        r1d = eval_report[R1_ID]
        hp, sg, cv = diag["holdout_proxy"], diag["sgmc_control"], diag["block_density_cv"]
        print(
            f"  {rec['id']} | dots={rec['n_dots']:,} | moved={rec['parent_diff']['pct_changed_moved']:.2f}% "
            f"(sym={rec['parent_diff']['pct_changed_sym_diff']:.2f}%) | min_dcat={rec['parent_diff']['min_dist_catalogue_px']:.4f}px\n"
            f"      prereg={pre['arms'][value]['preregistered_prediction']} MODEL vs R1 | w-model delta "
            f"{w_model[value]['delta_vs_r1']:+.6f} | SGMC={sg['dti']:.5f} (R1 {r1d['sgmc_control']['dti']:.5f}, "
            f"delta {sg['dti'] - r1d['sgmc_control']['dti']:+.5f}) | HOLDOUT-DTI={hp['dti']:.5f} "
            f"{hp['ci95']} | CV12km={cv['cv_12km_120px_interior']:.4f} (R1 {r1d['block_density_cv']['cv_12km_120px_interior']:.4f})"
        )
    print(f"  [R1 reference] dots=37,654 | min_dcat={float(d_cat[r1].min()):.4f}px | "
          f"SGMC={eval_report[R1_ID]['sgmc_control']['dti']:.5f}")
    print(f"Completed in {summary['elapsed_seconds']}s.")
    return 0


RECOMMENDATION = {
    "r10minus": (
        "DIAGNOSTIC/HOLD: the R0-parent read (-0.0081 blind SGMC at the same dose) says deletion costs "
        "real coverage; upload only if a receipt on R1 or r10plus motivates a mass-decrease bracket."
    ),
    "r10plus": (
        "SLOT-WORTHY CANDIDATE: the gate-clean form of MASS's only blind-positive arm (R0 r10plus +0.0029 "
        "SGMC), 100% of dots >3 px with no waiver. Spend only after human quota/TOP_PUBLIC confirmation and "
        "a same-parent receipt to pair against; a live |delta| < 0.01 vs R1 is no evidence."
    ),
    "r10swap": (
        "DIAGNOSTIC/HOLD: count-matched ranking-quality test with a near-zero prior (+0.001 MODEL) bounded "
        "by w's 0.4724 blind AUC; promote only on a >=0.01 live gain, which would justify a second ranking pass."
    ),
}


if __name__ == "__main__":
    raise SystemExit(main())
