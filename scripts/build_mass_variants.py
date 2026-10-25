#!/usr/bin/env python3
"""AXIS=MASS on parent R0 (h33-h33-2-b2) — the exact-marginal-ranked arms.

Session choice (Brief v2 §5: "Do not prompt me over choosing an Axis for the
session, pick your own session"): **AXIS = MASS**.

Why MASS: every MASS row already in ledger/submissions.csv (m10minus, m10plus,
m20minus) was ranked by an ad-hoc score ``0.6*clip(d_catalogue_px/50,0,1) +
0.4*uniform(seed)``, and the PR17 audit recorded that those arms were 89.4% /
85.2% a catalogue-collar extension, not a mass test. No (MASS, value) pair in
the ledger uses the parent's OWN ranking, which is exactly what Brief §5 asks
for ("by the parent's own ranking (rebuild the ranking from the recorded recipe
if it is not stored)"). R0 = dot_thin(H19-5, 2.8) & (d_cat > 2 px) is a purely
geometric Poisson-disk thinning and stores no per-dot score, so the ranking is
rebuilt as the one the parent lineage itself adopted from GEMSDOE32 onward:
**exact iterative marginal expected-DTI contribution under the pinned,
canary-clean, label-free physical corroboration field w** (vendor/gems57/metric.py
via scripts/build_prune_variants.py::select_exact_marginal_dti_add / _drop).

Three arms at the brief-mandated 10% dose (3,765 dots):
  * r10minus — drop the 3,765 lowest-ranked parent dots            -> 33,889 dots
  * r10plus  — add the 3,765 next-ranked un-emitted dots           -> 41,419 dots
  * r10swap  — drop the 3,765 lowest + add the 3,765 next-ranked   -> 37,654 dots
               (count-matched; isolates ranking quality from mass)

Predictions were preregistered in registry/mass_r0_preregistration.json BEFORE
this script computed anything. No DrivenData / Dropbox contact; nothing is
submitted. The human owns every upload.
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
import time
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from scripts import build_prune_variants as bpv  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
FIXED_DATE = "20261023"
SEED = 20261023
AXIS = "MASS"
FRACTION = 0.10
PREREG = ROOT / "registry" / "mass_r0_preregistration.json"

# Mechanism cards written for a structural geologist (Brief §5).
CARDS = {
    "r10minus": {
        "hypothesis": "R0 carries dead mass. The 37,654-dot Poisson-disk thinning of H19-5 at 2.8 px was selected for SPACING, not for evidence, so roughly a tenth of those dots sit on aeromagnetic ridge crests that no independent physical channel corroborates. Deleting the 3,765 dots whose removal costs the least kernel credit T while still removing one unit of mass S raises DTI, because DTI = T / (0.2T + 0.2(S-M) + 0.8|G|) penalises every emitted dot through S whether or not it lands on a fault.",
        "mechanism": "Under the 300 m triangular kernel a dot only pays if its credit exceeds 0.2*DTI (about 0.056 at DTI 0.28). Dots that (a) already lie within 300 m of a stronger neighbour on the same strand, or (b) sit on a ridge that the TMI horizontal-gradient, isostatic-gravity gradient, and GDR-1391 geothermometry channels all fail to support, contribute S but almost no T. Removing them shrinks the denominator 0.2(T + S - M) + 0.8|G| immediately and shrinks T only by the third-order residual credit they uniquely held.",
        "non_fault_mimic": "The corroboration field w is built from potential-field and topographic derivatives. A genuine but deeply buried, low-offset, or sediment-masked fault carries a weak magnetic and gravity expression, and 400 m GeoDAWN flight-line spacing (Area 2) can place its ridge crest up to a kernel radius off the true trace. Pruning 'low-w' dots therefore preferentially deletes blind and low-slip faults — precisely the population most likely to be in the new-fault label set — so a live score DROP is the expected outcome if w is a poor fault detector rather than a good one.",
        "predicted_sign_size": "Preregistered MODEL +0.003 vs R0 (range -0.008 to +0.014). The w-field in-sample delta is reported alongside; it is optimistic because w both ranks and scores.",
        "falsifier": "A live change less than +0.01 (or any negative change) falsifies the dead-mass hypothesis under the brief's no-evidence rule and shows that R0's dot count is already at or below the point where further deletion removes more true credit than wasted mass. A gain of >= +0.01 would make continued mass reduction the cheapest available lever and would imply the 2.8 px thinning is evidence-blind.",
    },
    "r10plus": {
        "hypothesis": "Adding mass does not help: the un-emitted H19-5 support is kernel-saturated. Every un-emitted H19-5 pixel survived the 2.8 px dot-thinning, which means it lies within 280 m of an already-emitted dot — inside the 300 m triangular kernel that already credits that strand — so a new dot there raises S by one and T by almost nothing, and DTI falls.",
        "mechanism": "The kernel credits a truth pixel by the BEST dot within 300 m, C_A(g) = max_x k(||g-x||). Once a strand is sampled every 280 m, the marginal dot on that strand has near-zero dT. The exact marginal-gain greedy therefore spends its 3,765 additions on whatever residual w it can still find — strand tips, step-over gaps, and low-w flanks — and the mean dT per added dot is the direct measurement of how saturated the parent field is.",
        "non_fault_mimic": "H19-5 is a multi-line ridge detector, so the un-emitted pool also contains genuine second-order features: antithetic splays, relay ramps, and range-front step-faults that the 2.8 px disk suppressed. If those carry real new-fault labels, additions pay. Conversely, ridge crests produced by flight-line levelling artefacts, drainage incision, and lithologic contacts are also in the pool and pay nothing, so the arm conflates 'add coverage' with 'add ridge artefacts'.",
        "predicted_sign_size": "Preregistered MODEL -0.008 vs R0 (range -0.018 to +0.002). A large negative result retires mass increase as a lever and supports the read that GEMSDOE76-81's 0.00-0.19 lanes failed from weak signals, not from too few dots.",
        "falsifier": "A live gain >= +0.01 falsifies saturation and proves the parent field has substantial unsampled strand length at 100 m resolution, which would re-open count as the primary lever and make the 2.8 px thinning the binding constraint rather than the corroboration field.",
    },
    "r10swap": {
        "hypothesis": "Ranking quality, not mass, is what is left on the table. At a fixed 37,654 dots, replacing the 3,765 dots with the smallest exact marginal credit by the 3,765 best un-emitted candidates must move DTI through T alone: S is unchanged, so a gain means the parent's geometric thinning is measurably worse than a w-ranked selection at the same dot budget.",
        "mechanism": "S is frozen, so DTI changes only through T and M. The dropped dots are chosen to minimise lost T; the added dots are chosen to maximise gained T on cells the parent never sampled (d_cat > 3 px, outside R0). The arm is the superposition of r10minus's denominator saving and r10plus's numerator gain, and its outcome is the product of how redundant the worst decile is and how much uncovered credit the best decile can reach.",
        "non_fault_mimic": "The swap is a pure w-ranking play, so it inherits every bias of w: TMI/gravity gradients favour basement-step and lithologic-contact lineaments, and the GDR-1391 geothermometry term is concentrated near known geothermal systems. If the new-fault labels are dominated by Quaternary scarps with little potential-field expression, the swap will systematically trade real scarps for geophysically loud but geologically dead lineaments — a live loss even though the w-model predicts a gain.",
        "predicted_sign_size": "Preregistered MODEL +0.006 vs R0 (range -0.006 to +0.018). Best of the three on the w-model but bounded by w's ~0.68-AUC ceiling and by saturation of the un-emitted pool.",
        "falsifier": "A live change below +0.01 falsifies w-ranked reselection as a lever and says the parent's geometric thinning is already as good as the corroboration field can rank — which would redirect the remaining slots to SPACING/TRACKB rather than to any field-driven reselection.",
    },
}

RANKING_BASIS = (
    "exact iterative marginal expected-DTI under the pinned label-free physical field w "
    "(parent's own ranking, rebuilt: R0 stores no per-dot score)"
)


def _prereg() -> dict:
    return json.loads(PREREG.read_text(encoding="utf-8"))


def _nearest_parent_distance(parent_mask: np.ndarray, added_mask: np.ndarray) -> dict:
    """Distance from each added dot to the nearest parent dot (saturation diagnostic)."""
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


def main() -> int:
    t0 = time.time()
    pre = _prereg()
    print("[1/6] Verifying SHA-256 manifest pins and rebuilding parent R0 ...")
    verified = bpv.verify_manifest()
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    n_parent = int(r0.sum())
    assert n_parent == 37_654, n_parent
    assert lin["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS
    assert lin["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    print(
        f"      {len(verified)} pins OK | EXACT R0 REBUILD OK: {n_parent:,} dots | "
        f"zeros={lin['rebuilt_zeros_sha256'][:12]}... | nan={lin['rebuilt_nan_sha256'][:12]}..."
    )
    print(f"      inherited R0 dots at 2 < d_cat <= 3 px: {int((r0 & (d_cat <= 3.0)).sum()):,}")

    print("[2/6] Rebuilding physical corroboration field w and running leakage canaries ...")
    w_field, canaries = bpv.build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    max_auc = max(canaries.values())
    print(f"      canaries: {len(canaries)} channels, max symmetric AUC = {max_auc:.4f}")
    if max_auc > 0.90:
        raise RuntimeError(f"Leakage canary tripped: symmetric AUC {max_auc:.4f} > 0.90")

    base_terms = bpv.weighted_expected_dti(r0, w_field)
    print(
        f"      R0 w-model: DTI={base_terms['dti']:.6f} T={base_terms['T']:.1f} "
        f"S={base_terms['S']:.0f} M={base_terms['M']:.1f} W={base_terms['W']:.1f}"
    )

    n_dose = int(round(FRACTION * n_parent))
    print(f"[3/6] Allocating 3 AXIS=MASS arms at a fixed 10% dose ({n_dose:,} dots) ...")

    # Pool of never-emitted parent-field candidates, fully compliant with Brief §4.4
    # (>=3 px from the catalogue; MASS is not PRUNE, so no new sub-3 px mass).
    cand_pool = h19_5 & ~r0 & (d_cat > 3.0)
    print(f"      candidate pool (H19-5 & ~R0 & d_cat>3px): {int(cand_pool.sum()):,} px")

    t = time.time()
    m_minus = bpv.select_exact_marginal_dti_drop(
        base_mask=r0, drop_pool_mask=r0, w=w_field, n_drop=n_dose
    )
    print(f"      r10minus greedy drop done in {time.time() - t:.0f}s -> {int(m_minus.sum()):,} dots")

    t = time.time()
    m_plus = bpv.select_exact_marginal_dti_add(
        base_mask=r0, cand_mask=cand_pool, w=w_field, n_add=n_dose
    )
    print(f"      r10plus greedy add done in {time.time() - t:.0f}s -> {int(m_plus.sum()):,} dots")

    t = time.time()
    m_swap = bpv.select_exact_marginal_dti_add(
        base_mask=m_minus, cand_mask=cand_pool, w=w_field, n_add=n_dose
    )
    print(f"      r10swap greedy add done in {time.time() - t:.0f}s -> {int(m_swap.sum()):,} dots")

    assert int(m_minus.sum()) == n_parent - n_dose == 33_889
    assert int(m_plus.sum()) == n_parent + n_dose == 41_419
    assert int(m_swap.sum()) == n_parent == 37_654
    assert not (m_swap & ~m_minus & r0).any(), "swap must not re-add dropped parent dots"

    # w-model (in-sample, optimistic) deltas -> MODEL numbers for the ledger
    w_model = {}
    for name, mask in (("r10minus", m_minus), ("r10plus", m_plus), ("r10swap", m_swap)):
        tm = bpv.weighted_expected_dti(mask, w_field)
        w_model[name] = {
            "dti": round(tm["dti"], 6),
            "delta_vs_r0": round(tm["dti"] - base_terms["dti"], 6),
            "T": round(tm["T"], 3),
            "S": float(tm["S"]),
            "M": round(tm["M"], 3),
            "denom": round(tm["denom"], 3),
        }
    for k, v in w_model.items():
        print(f"      w-model {k}: DTI={v['dti']:.6f} (delta {v['delta_vs_r0']:+.6f})")

    print("[4/6] Writing GeoTIFFs, re-reading from disk and enforcing MUST gates ...")
    ledger_path = ROOT / "ledger" / "submissions.csv"
    existing_rows: list[dict[str, str]] = []
    existing_shas: set[str] = {bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN}
    if ledger_path.is_file():
        with ledger_path.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("axis") == AXIS and row.get("value") in CARDS:
                    continue  # idempotent re-run replaces only this session's arms
                existing_rows.append(row)
                if row.get("sha256"):
                    existing_shas.add(row["sha256"])
                if row.get("sha256_zeros"):
                    existing_shas.add(row["sha256_zeros"])

    releases_dir = ROOT / "releases"
    for old_p in releases_dir.glob(f"{PARENT_ID}-MASSr*"):
        old_p.unlink()

    arms = {
        "r10minus": (m_minus, "-", "h33-2-b2; MASS -3765 lowest exact-marginal dots (37654->33889); pred {pred} MODEL"),
        "r10plus": (m_plus, "+", "h33-2-b2; MASS +3765 next-ranked un-emitted dots, d_cat>3px (37654->41419); pred {pred} MODEL"),
        "r10swap": (m_swap, "=", "h33-2-b2; MASS swap 3765 lowest for 3765 next-ranked, count fixed 37654; pred {pred} MODEL"),
    }

    built: dict[str, dict] = {}
    for value, (mask, sign, note_tmpl) in arms.items():
        pred = f"{w_model[value]['delta_vs_r0']:+.3f}"
        rec = bpv.write_and_verify_variant(
            mask=mask,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=releases_dir,
            parent_mask=r0,
            axis=AXIS,
            value=value,
            note_template=note_tmpl.format(pred=pred, sha8="{sha8}"),
            existing_shas=existing_shas,
            pct_basis="max",
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])
        built[value] = rec
        print(
            f"      {rec['id']} | dots={rec['n_dots']:,} | moved={rec['parent_diff']['pct_changed_moved']:.2f}% "
            f"(sym={rec['parent_diff']['pct_changed_sym_diff']:.2f}%) | min_dcat={rec['parent_diff']['min_dist_catalogue_px']:.4f}px"
        )

    print("[5/6] REPORT-ONLY diagnostics (catalogue holdout PROXY, SGMC control, block CV) ...")
    eval_arms: dict[str, np.ndarray] = {PARENT_ID: r0}
    for value, (mask, _, _) in arms.items():
        eval_arms[built[value]["id"]] = mask
    eval_report = bpv.evaluate_report_only_instruments(
        arms=eval_arms, foot=foot, catalogue=catalogue, sgmc_path=verified["sgmc_faults_control"]
    )

    print("[6/6] Writing ledger rows, mechanism cards and evidence ...")
    cards = (
        json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
        if (ROOT / "ledger" / "mechanism_cards.json").is_file()
        else {}
    )
    cards = {k: v for k, v in cards.items() if "-MASSr" not in k}

    new_rows = []
    for value, (mask, _, _) in arms.items():
        rec = built[value]
        diag = eval_report[rec["id"]]
        r0d = eval_report[PARENT_ID]
        added = mask & ~r0
        removed = r0 & ~mask
        extra = {
            "preregistered_prediction": pre["arms"][value]["preregistered_prediction"],
            "preregistered_range": pre["arms"][value]["preregistered_range"],
            "w_model": w_model[value],
            "w_model_caveat": (
                "IN-SAMPLE and optimistic: the same field w both ranks and scores the arm, "
                "and w is a ~0.68-AUC proxy for fault presence (PROXY, never a score)."
            ),
            "r0_w_model": {
                "dti": round(base_terms["dti"], 6),
                "T": round(base_terms["T"], 3),
                "S": float(base_terms["S"]),
                "M": round(base_terms["M"], 3),
            },
            "r0_reference_diagnostics": r0d,
            "report_only_diagnostics": diag,
            "saturation_diagnostic_added_dots": _nearest_parent_distance(r0, added),
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
            "parent_dots_mean_w": round(float(w_field[r0].mean()), 6),
            "leakage_canaries": {
                "passed": True,
                "max_symmetric_auc": max_auc,
                "channels": canaries,
            },
        }
        rec.update(extra)
        (releases_dir / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        cards[rec["id"]] = {
            "parent": PARENT_ID,
            "axis": AXIS,
            "value": value,
            "preregistered_prediction": pre["arms"][value]["preregistered_prediction"],
            "preregistered_range": pre["arms"][value]["preregistered_range"],
            **CARDS[value],
            "post_build_w_model_delta": f"{w_model[value]['delta_vs_r0']:+.6f}",
            "post_build_report_only": {
                "holdout_proxy_delta_vs_r0": diag["holdout_proxy"]["paired_delta_vs_r0"],
                "holdout_proxy_ci95": diag["holdout_proxy"]["paired_delta_vs_r0_ci95"],
                "sgmc_off_catalogue_dti": diag["sgmc_control"]["dti"],
                "r0_sgmc_off_catalogue_dti": r0d["sgmc_control"]["dti"],
                "cv_12km": diag["block_density_cv"]["cv_12km_120px_interior"],
                "r0_cv_12km": r0d["block_density_cv"]["cv_12km_120px_interior"],
            },
        }
        hp = diag["holdout_proxy"]
        new_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": AXIS,
                "value": value,
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{w_model[value]['delta_vs_r0']:+.3f}",
                "predicted_range": pre["arms"][value]["preregistered_range"],
                "ranking_basis": RANKING_BASIS,
                "receipt_score": "",
                "receipt_date": "",
                "description": (
                    pre["arms"][value]["operation"]
                    + f" | preregistered {pre['arms'][value]['preregistered_prediction']} MODEL; "
                    + f"post-build w-model delta {w_model[value]['delta_vs_r0']:+.4f} (in-sample, optimistic); "
                    + f"holdout PROXY {hp['dti']:.5f} (delta {hp['paired_delta_vs_r0']:+.5f}, "
                    + f"n={hp['withheld_positives']}); SGMC off-cat {diag['sgmc_control']['dti']:.5f} "
                    + f"vs R0 {r0d['sgmc_control']['dti']:.5f}; CV12km {diag['block_density_cv']['cv_12km_120px_interior']:.4f} "
                    + f"vs R0 {r0d['block_density_cv']['cv_12km_120px_interior']:.4f}; "
                    + f"min d_cat {rec['parent_diff']['min_dist_catalogue_px']:.4f} px "
                    + f"({rec['parent_diff']['dots_le_3px']:,} dots <=3 px, all inherited from R0)."
                ),
                "recommendation": RECOMMENDATION[value],
            }
        )

    fieldnames = [
        "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256", "sha256_zeros",
        "status", "predicted_change", "predicted_range", "ranking_basis", "receipt_score",
        "receipt_date", "description", "recommendation",
    ]
    with ledger_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for r in [*existing_rows, *new_rows]:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
    (ROOT / "ledger" / "mechanism_cards.json").write_text(json.dumps(cards, indent=2) + "\n")

    summary = {
        "schema": "gems88.mass-r0-axis-report.v1",
        "session_date": "2026-10-23",
        "axis": AXIS,
        "parent": {
            "id": PARENT_ID,
            "n_dots": n_parent,
            "rebuilt_zeros_sha256": lin["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lin["rebuilt_nan_sha256"],
            "dots_at_2_to_3px": int((r0 & (d_cat <= 3.0)).sum()),
            "min_d_cat_px": round(float(d_cat[r0].min()), 4),
            "w_model": {
                "dti": round(base_terms["dti"], 6),
                "T": round(base_terms["T"], 3),
                "S": float(base_terms["S"]),
                "M": round(base_terms["M"], 3),
                "W": round(base_terms["W"], 3),
            },
        },
        "verified_inputs": len(verified),
        "leakage_canaries": {"passed": True, "max_symmetric_auc": max_auc, "channels": canaries},
        "ranking_definition": pre["ranking_definition"],
        "dose": {"fraction": FRACTION, "n_dots": n_dose},
        "candidate_pool_px": int(cand_pool.sum()),
        "preregistered_predictions": {k: v["preregistered_prediction"] for k, v in pre["arms"].items()},
        "w_model_deltas": w_model,
        "report_only": {k: eval_report[k] for k in eval_report},
        "variants": [
            {k: v for k, v in built[name].items() if k != "leakage_canaries"} for name in arms
        ],
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    (ROOT / "evidence" / "mass_r0_axis_report.json").write_text(json.dumps(summary, indent=2) + "\n")

    print("\n=== SUMMARY OF BUILT AXIS=MASS VARIANTS ===")
    for value in arms:
        rec = built[value]
        diag = eval_report[rec["id"]]
        r0d = eval_report[PARENT_ID]
        hp, sg, cv = diag["holdout_proxy"], diag["sgmc_control"], diag["block_density_cv"]
        print(
            f"  {rec['id']} | dots={rec['n_dots']:,} | moved={rec['parent_diff']['pct_changed_moved']:.2f}% "
            f"(sym={rec['parent_diff']['pct_changed_sym_diff']:.2f}%) | min_dcat={rec['parent_diff']['min_dist_catalogue_px']:.4f}px\n"
            f"      prereg={pre['arms'][value]['preregistered_prediction']} MODEL | w-model delta "
            f"{w_model[value]['delta_vs_r0']:+.6f} | HOLDOUT-DTI={hp['dti']:.5f} {hp['ci95']} "
            f"(delta {hp['paired_delta_vs_r0']:+.5f}, n={hp['withheld_positives']}) | SGMC={sg['dti']:.5f} "
            f"(R0 {r0d['sgmc_control']['dti']:.5f}) | CV12km={cv['cv_12km_120px_interior']:.4f} "
            f"(R0 {r0d['block_density_cv']['cv_12km_120px_interior']:.4f})"
        )
    print(f"  [R0 reference] dots=37,654 | min_dcat={float(d_cat[r0].min()):.4f}px | "
          f"HOLDOUT-DTI={eval_report[PARENT_ID]['holdout_proxy']['dti']:.5f}")
    print(f"Completed in {summary['elapsed_seconds']}s.")
    return 0


RECOMMENDATION = {
    "r10minus": (
        "HOLD-CONDITIONAL: drops 10% of the parent at a real (not collar-confounded) ranking; "
        "the only MASS arm whose prediction survives a sceptical reading of w. Upload only as the "
        "second slot after a receipt separates 'R0 carries dead mass' from 'w under-ranks blind faults'."
    ),
    "r10plus": (
        "DIAGNOSTIC, not a slot: the saturation test. A receipt here is worth its slot only if the "
        "human wants mass increase retired with evidence; both the preregistered prediction and the "
        "saturation geometry are negative."
    ),
    "r10swap": (
        "SLOT-WORTHY CANDIDATE: count stays in the 37-44k band every good file occupies, all new dots "
        "are >=3 px from the catalogue, and it is the only arm that improves selection without changing "
        "mass. Spend a slot only after confirming quota and after the human has a receipt for R0 or R1 "
        "to compare against; a live |delta| < 0.01 vs R0 is no evidence."
    ),
}


if __name__ == "__main__":
    raise SystemExit(main())
