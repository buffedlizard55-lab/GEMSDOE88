#!/usr/bin/env python3
"""AXIS=MASS on the gate-clean parent R1 (``PRUNEp3px``) — the R1 mass bracket.

Session choice (Brief v2 §5: "Do not prompt me over choosing an Axis for the
session, pick your own session"): **AXIS = MASS, parent = R1**.

Why this session, and why this parent:

* The R0 MASS family (``r10minus/r10plus/r10swap``) is the only axis build whose
  positive arm (``r10plus``) beat its parent on any instrument, but every R0
  child is parked at HOLD: R0 carries 1,611 dots strictly inside the literal
  3 px non-PRUNE collar (IR-88-43/47), so no non-PRUNE edit of R0 can be
  gate-clean. R1 = ``h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`` is the named
  gate-clean parent (min ``d_cat`` 3.1623 px, IR-88-33) and has NEVER had its
  mass curve measured.
* ``SLOT_PLAN.md`` names exactly this build for wk3-4: "(R1, MASS, r10plus) —
  the gate-clean form of MASS's only positive arm — as a separate single-axis
  session".
* The R1 analogue is not a re-run: R1's own 2,171 refills consumed the highest
  marginal candidates of the same ranking, so the next-ranked pool is strictly
  deeper. The R0 result therefore does not transfer by construction; it is a
  question.

Three arms at the brief's 10% dose (3,765 dots), one axis, one parent:

  * ``r10minus`` — drop the 3,765 lowest-ranked R1 dots        -> 33,889 dots
  * ``r10plus``  — add the 3,765 next-ranked un-emitted dots   -> 41,419 dots
  * ``r10swap``  — drop the 3,765 lowest + add the 3,765 next  -> 37,654 dots
                   (count-matched; isolates ranking from mass)

Ranking = the parent's own recorded recipe, re-run on the parent: exact
iterative marginal expected-DTI contribution under the pinned label-free
physical field ``w`` (``scripts/build_prune_variants.py::select_exact_marginal_dti_add``
/ ``_drop`` over ``vendor/gems57/metric.py``, alpha 0.2, beta 0.8, R = 3 px).

Predictions were preregistered in ``registry/preregistration_mass_r1.json``
BEFORE this script ran. No DrivenData / Dropbox / leaderboard contact; nothing
is submitted. The human owns every upload.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "scripts"), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_prune_variants as bpv  # noqa: E402
import build_snap_r1_variants as bsv  # noqa: E402
from gems57 import evaluate_holdout, grid as grid_mod, holdout as holdout_mod, metric  # noqa: E402

RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
CARDS_PATH = ROOT / "ledger" / "mechanism_cards.json"
PREREG = ROOT / "registry" / "preregistration_mass_r1.json"
REPORT = ROOT / "evidence" / "mass_r1_axis_report.json"

AXIS = "MASS"
VALUES = ("r10minus", "r10plus", "r10swap")
R1_ID = bsv.R1_ID
R1_SHA_NAN = bsv.R1_SHA_NAN
R1_SHA_ZEROS = bsv.R1_SHA_ZEROS
FRACTION = 0.10
N_PARENT = 37_654
N_DOSE = int(round(FRACTION * N_PARENT))  # 3,765

RANKING_BASIS = (
    "exact iterative marginal expected-DTI under the pinned label-free physical field w, "
    "re-run on R1 (the parent's own recorded ranking recipe: R1 was built by the same greedy)"
)

# Mechanism cards written for a structural geologist (Brief §5).
CARDS = {
    "r10minus": {
        "hypothesis": "R1 still carries dead mass at its bottom decile. R1 = R0's >3 px matrix plus 2,171 exact-marginal refills, so its 3,765 lowest-ranked dots are the dots the parent's OWN ranking ranked last: late refills and R0 dots that the corroboration field never liked. Deleting them raises DTI because every emitted dot is charged one unit of mass S in the denominator 0.2(T + S - M) + 0.8|G| whether or not it lands on a fault, while their kernel credit T is by construction the smallest in the file.",
        "mechanism": "Under the 300 m triangular kernel a dot pays only if its credit exceeds 0.2*DTI (about 0.056 at DTI 0.28). A dot whose nearest neighbour already covers its strand contributes S and almost no unique T. Because R1's refills were chosen by the same exact-marginal greedy that now ranks them, the bottom decile is measured, not assumed, to be the least productive 10% of the file; the greedy drop removes them in the order that costs the least T per unit of S removed.",
        "non_fault_mimic": "The ranking field w is built from potential-field and topographic derivatives. A genuine but blind, low-offset, or basin-masked fault has a weak magnetic/gravity signature, and GeoDAWN Area 2 was flown at 400 m line spacing (150-200 m above terrain, https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7), so its crest can sit a kernel radius off the trace. Pruning low-w dots therefore preferentially deletes blind faults - the population most likely to be in the new-fault label set - so a live loss is the expected outcome if w is a poor fault detector rather than a good one.",
        "predicted_sign_size": "Preregistered MODEL -0.004 live delta vs R1 (range -0.014 to +0.006), anchored on the R0 family's blind SGMC loss of -0.0081 for the identical edit, discounted because R1's bottom decile is ranked rather than geometric.",
        "falsifier": "A live gain of >= +0.01 falsifies dead mass at the bottom decile and says R0/R1 are still over-emitted, which would make continued mass reduction the cheapest lever on the gate-clean parent. A live loss of <= -0.01 retires the drop direction permanently on both parents. |delta| < 0.01 is no evidence.",
    },
    "r10plus": {
        "hypothesis": "The gate-clean parent is under-emitted. R0's marginal-decile test was the only MASS arm to beat its parent on the blind off-catalogue control (+0.0029 SGMC PROXY; +0.0107 w-field MODEL), and that gain was measured on a parent whose candidates were still unconstrained by a collar refill. R1 removed 1,611 dots at 2 < d_cat <= 3 px and re-spent them on the same H19-5 support elsewhere; if the collar purge left strand length unsampled, adding the next-ranked 3,765 dots recovers it.",
        "mechanism": "A truth pixel is credited by the BEST dot within 300 m, C_A(g) = max_x k(||g-x||), so the marginal dot pays only on strand length nobody covers. The added dots are the exact-marginal argmax at every step, i.e. they are placed where dT per unit dS is largest, subject to the strict >3 px collar. The measurement this arm delivers is the mean dT per added dot, which is a direct, label-free readout of how saturated R1 is.",
        "non_fault_mimic": "H19-5 is a multi-line ridge detector, so the un-emitted pool contains second-order structure (antithetic splays, relay ramps, step-faults the 2.8 px Poisson disk suppressed) alongside flight-line levelling artefacts, drainage incision, and lithologic contacts. The arm conflates 'add coverage' with 'add ridge artefacts', and 400 m flight-line spacing means the placement error is of order the kernel radius, so extra dots may land 100-200 m off a true trace.",
        "predicted_sign_size": "Preregistered MODEL +0.004 live delta vs R1 (range -0.008 to +0.016), deliberately below the R0 family's in-sample +0.0107 because R1 already consumed the 2,171 highest-marginal candidates of the same ranking.",
        "falsifier": "A live change below +0.01 (Brief's no-evidence floor) leaves mass increase unproven and, combined with the R0 result, retires MASS as a lever on both parents; the remaining slots then go to SNAP/spacing confirmation of R1. A gain >= +0.01 makes 41,419 dots the final-file candidate and licenses the 45,185-dot (r20plus) dose as the next single-axis build.",
    },
    "r10swap": {
        "hypothesis": "What is left on the table in R1 is ranking quality, not count. At a frozen 37,654 dots, replacing the 3,765 dots with the smallest exact marginal credit by the 3,765 best un-emitted candidates must move DTI through T alone, because S is unchanged by construction.",
        "mechanism": "S is frozen, so DTI changes only through T and M: the arm is the superposition of r10minus's denominator saving and r10plus's numerator gain. It isolates whether the parent's dot placement - BFS-anchored Poisson-disk thinning plus a greedy refill - is measurably worse than a pure w-ranked selection at the same dot budget.",
        "non_fault_mimic": "The swap is a pure ranking play and inherits every bias of w: TMI/gravity gradients favour basement-step and lithologic-contact lineaments, and the GDR-1391 geothermometry term is concentrated near known geothermal systems. If the new-fault labels are dominated by Quaternary scarps with little potential-field expression, the swap trades real scarps for geophysically loud but geologically dead lineaments - a live loss even where the w-model predicts a gain.",
        "predicted_sign_size": "Preregistered MODEL +0.002 live delta vs R1 (range -0.008 to +0.012): the midpoint of the other two arms, and the arm that would be preferred at equal score because it spends no extra denominator mass.",
        "falsifier": "A live change below +0.01 falsifies w-ranked reselection as a lever and says the parent's geometric placement is already as good as the corroboration field can rank - which redirects the remaining slots to SPACING/TRACKB rather than to any field-driven reselection.",
    },
}


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
    }


def evaluate_report_only_vs_reference(
    arms: dict[str, np.ndarray],
    foot: np.ndarray,
    catalogue: np.ndarray,
    sgmc_path: Path,
    reference: str,
) -> dict:
    """Same instruments as build_prune_variants.evaluate_report_only_instruments.

    The upstream helper hard-codes R0 as the paired-bootstrap reference; this session's
    parent is R1, so the paired deltas and CIs are re-derived against ``reference``.
    Report-only: none of these numbers can fail a gate (Brief §6).
    """
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)

    terms_by_arm: dict[str, np.ndarray] = {}
    for name, mask in arms.items():
        pred = mask.astype(np.float32)
        total = None
        for f in [*folds20, *folds30]:
            _, t = evaluate_holdout.evaluate(pred, f, foot)
            total = t if total is None else (total + t)
        terms_by_arm[name] = total

    primary_key = next(k for k in arms if k != reference)
    pooled = evaluate_holdout.pooled_summary(
        terms_by_arm, draws=1000, seed=520810, candidate=primary_key
    )

    sgmc_raw = rasterio.open(sgmc_path).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue
    from scipy.ndimage import binary_dilation

    sgmc_off = sgmc_off & ~binary_dilation(catalogue, iterations=3)

    active = np.any(np.stack([a.sum(axis=1) > 0 for a in terms_by_arm.values()]), axis=0)
    nb = int(active.sum())
    rng = np.random.default_rng(520810)
    picks = rng.integers(0, nb, size=(1000, nb))
    ref_boot = evaluate_holdout.from_terms(terms_by_arm[reference][active][picks].sum(axis=1))

    out = {}
    for name, mask in arms.items():
        s_hold = pooled["scores"][name]
        a_boot = evaluate_holdout.from_terms(terms_by_arm[name][active][picks].sum(axis=1))
        diff = a_boot - ref_boot
        sgmc_res = metric.dti_binary(mask, sgmc_off, valid=foot, known=catalogue)
        out[name] = {
            "n_dots": int(mask.sum()),
            "holdout_proxy": {
                "evidence_label": "PROXY",
                "evaluator_version": evaluate_holdout.VERSION,
                "dti": round(float(s_hold["dti"]), 6),
                "ci95": [round(float(x), 6) for x in s_hold["ci95"]],
                "withheld_positives": int(s_hold["withheld_positive_pixels"]),
                "paired_delta_vs_reference": round(
                    float(s_hold["dti"] - pooled["scores"][reference]["dti"]), 6
                ),
                "paired_delta_vs_reference_ci95": [
                    round(float(x), 6) for x in np.quantile(diff, [0.025, 0.975])
                ],
                "reference": reference,
            },
            "sgmc_control": {
                "evidence_label": "PROXY",
                "dti": round(float(sgmc_res["dti"]), 6),
                "n_sgmc_off_catalogue_px": int(sgmc_off.sum()),
                "tp": round(float(sgmc_res["tp"]), 2),
                "fp": round(float(sgmc_res["fp"]), 2),
            },
            "block_density_cv": {
                "cv_10km_100px_interior": round(bpv.compute_block_cv(mask, foot, 100), 4),
                "cv_12km_120px_interior": round(bpv.compute_block_cv(mask, foot, 120), 4),
            },
        }
    return out


def main() -> int:
    t0 = time.time()
    pre = _prereg()
    print("[1/7] Verifying SHA-256 manifest pins and rebuilding R0 byte-exactly ...")
    verified = bpv.verify_manifest()
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    assert int(r0.sum()) == N_PARENT
    assert lin["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS
    assert lin["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    print(f"      {len(verified)}/15 pins OK | R0 exact: {int(r0.sum()):,} dots")

    print("[2/7] Rebuilding the label-free field w and running the leakage canaries ...")
    w_field, canaries = bpv.build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    max_auc = max(canaries.values())
    print(f"      canaries: {len(canaries)} channels, max symmetric AUC = {max_auc:.4f}")
    if max_auc > 0.90:
        raise RuntimeError(f"Leakage canary tripped: symmetric AUC {max_auc:.4f} > 0.90")

    print("[3/7] Reconstructing the parent R1 = PRUNEp3px and asserting both published SHA-256 ...")
    r1 = bsv.reconstruct_r1(lin, w_field, verified)
    assert int(r1.sum()) == N_PARENT
    d_r1 = d_cat[r1]
    assert float(d_r1.min()) > 3.0, f"R1 collar violated: {d_r1.min()}"
    print(f"      R1 OK: {int(r1.sum()):,} dots, min d_cat = {d_r1.min():.4f} px")

    # (parent, axis, value) uniqueness: the only legal dedupe rule in Brief §6.
    if LEDGER.is_file():
        with LEDGER.open(newline="", encoding="utf-8") as f:
            prior = [
                r for r in csv.DictReader(f)
                if r.get("axis") == AXIS and r.get("parent") == R1_ID and r.get("value") in VALUES
            ]
        if prior:
            print(f"      note: replacing {len(prior)} prior (R1, MASS, *) row(s) this run")

    base_terms = bpv.weighted_expected_dti(r1, w_field)
    print(
        f"      R1 w-model: DTI={base_terms['dti']:.6f} T={base_terms['T']:.1f} "
        f"S={base_terms['S']:.0f} M={base_terms['M']:.1f}"
    )

    print(f"[4/7] Allocating 3 AXIS=MASS arms at the fixed 10% dose ({N_DOSE:,} dots) ...")
    # Never-emitted support, and MASS is not PRUNE: every added dot must be strictly >3 px out.
    cand_pool = h19_5 & ~r1 & (d_cat > 3.0)
    print(f"      candidate pool (H19-5 & ~R1 & d_cat>3px): {int(cand_pool.sum()):,} px")
    if int(cand_pool.sum()) < N_DOSE:
        raise RuntimeError("candidate pool smaller than the dose")

    t = time.time()
    m_minus = bpv.select_exact_marginal_dti_drop(base_mask=r1, drop_pool_mask=r1, w=w_field, n_drop=N_DOSE)
    print(f"      r10minus greedy drop done in {time.time() - t:.0f}s -> {int(m_minus.sum()):,} dots")

    t = time.time()
    m_plus = bpv.select_exact_marginal_dti_add(base_mask=r1, cand_mask=cand_pool, w=w_field, n_add=N_DOSE)
    print(f"      r10plus greedy add done in {time.time() - t:.0f}s -> {int(m_plus.sum()):,} dots")

    t = time.time()
    m_swap = bpv.select_exact_marginal_dti_add(base_mask=m_minus, cand_mask=cand_pool, w=w_field, n_add=N_DOSE)
    print(f"      r10swap greedy add done in {time.time() - t:.0f}s -> {int(m_swap.sum()):,} dots")

    # Arithmetic and gate preconditions, asserted before anything is written.
    assert int(m_minus.sum()) == N_PARENT - N_DOSE == 33_889
    assert int(m_plus.sum()) == N_PARENT + N_DOSE == 41_419
    assert int(m_swap.sum()) == N_PARENT
    assert not (r1 & ~m_minus & m_swap).any(), "swap must not re-add a dropped parent dot"
    assert not (m_plus & ~r1 & ~h19_5).any(), "added dots must be H19-5 support"
    assert not (m_plus & ~r1 & (d_cat <= 3.0)).any(), "added dot inside the 3 px collar"
    for name, m in (("r10minus", m_minus), ("r10plus", m_plus), ("r10swap", m_swap)):
        assert float(d_cat[m].min()) > 3.0, (name, float(d_cat[m].min()))
        assert int((m & catalogue).sum()) == 0, name

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
            "mean_dT_per_changed_dot": (
                round((tm["T"] - base_terms["T"]) / N_DOSE, 5) if name == "r10plus" else None
            ),
        }
        print(f"      w-model {name}: DTI={tm['dti']:.6f} (delta {w_model[name]['delta_vs_r1']:+.6f})")

    # REPORT-ONLY control (no release, no ledger row): does the exact-marginal RANKING
    # beat an equal-sized random draw from the same pool? An ADD arm mechanically raises
    # T and S together, so a positive arm is only evidence for the ranking if it beats
    # random receivers of the same size. Seeded, deterministic, never gated.
    rng = np.random.default_rng(bpv.SEED)
    pool_y, pool_x = np.nonzero(cand_pool)
    pick = rng.choice(pool_y.size, size=N_DOSE, replace=False)
    m_rand = r1.copy()
    m_rand[pool_y[pick], pool_x[pick]] = True
    assert int(m_rand.sum()) == N_PARENT + N_DOSE
    assert float(d_cat[m_rand].min()) > 3.0

    print("[4b/7] Random-donor control on the same pool (report-only) ...")
    rand_terms = bpv.weighted_expected_dti(m_rand, w_field)
    rand_report = evaluate_report_only_vs_reference(
        arms={R1_ID: r1, "random_add": m_rand},
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
        reference=R1_ID,
    )
    random_control = {
        "role": "REPORT-ONLY control: same pool, same count, random receivers (seed %d)" % bpv.SEED,
        "n_added": int(N_DOSE),
        "w_model_delta_vs_r1": round(rand_terms["dti"] - base_terms["dti"], 6),
        "sgmc_off_catalogue_dti": rand_report["random_add"]["sgmc_control"]["dti"],
        "r1_sgmc_off_catalogue_dti": rand_report[R1_ID]["sgmc_control"]["dti"],
        "sgmc_delta_vs_r1": round(
            rand_report["random_add"]["sgmc_control"]["dti"]
            - rand_report[R1_ID]["sgmc_control"]["dti"],
            6,
        ),
        "block_density_cv_12km": rand_report["random_add"]["block_density_cv"]["cv_12km_120px_interior"],
    }
    print(
        f"      random add: w-model {random_control['w_model_delta_vs_r1']:+.6f} | "
        f"SGMC {random_control['sgmc_off_catalogue_dti']:.6f} "
        f"(delta vs R1 {random_control['sgmc_delta_vs_r1']:+.6f})"
    )

    print("[5/7] Writing GeoTIFFs, re-reading from disk and enforcing the MUST gates ...")
    existing_rows: list[dict[str, str]] = []
    existing_shas: set[str] = {
        bpv.PARENT_SHA_ZEROS, bpv.PARENT_SHA_NAN, R1_SHA_NAN, R1_SHA_ZEROS
    }
    if LEDGER.is_file():
        with LEDGER.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if (
                    row.get("axis") == AXIS
                    and row.get("parent") == R1_ID
                    and row.get("value") in VALUES
                ):
                    continue  # idempotent re-run replaces only this session's arms
                existing_rows.append(row)
                if row.get("sha256"):
                    existing_shas.add(row["sha256"])
                if row.get("sha256_zeros"):
                    existing_shas.add(row["sha256_zeros"])

    for old_p in RELEASES.glob(f"{R1_ID}-MASS*"):
        old_p.unlink()

    arms = {
        "r10minus": (
            m_minus,
            "h33-2-b2 PRUNEp3px R1; MASS -3765 lowest exact-marginal dots, 100% >3px; pred {pred} MODEL",
        ),
        "r10plus": (
            m_plus,
            "h33-2-b2 PRUNEp3px R1; MASS +3765 next-ranked H19-5 dots >3px, 41419; pred {pred} MODEL",
        ),
        "r10swap": (
            m_swap,
            "h33-2-b2 PRUNEp3px R1; MASS swap 3765 lowest for 3765 next-ranked, count 37654; pred {pred} MODEL",
        ),
    }

    built: dict[str, dict] = {}
    for value, (mask, note_tmpl) in arms.items():
        # Form note carries the PREREGISTERED prediction, not the in-sample w-model number.
        pred = pre["arms"][[a["value"] for a in pre["arms"]].index(value)]["predicted_change"].split(":")[-1]
        rec = bpv.write_and_verify_variant(
            mask=mask,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=RELEASES,
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
        pd = rec["parent_diff"]
        print(
            f"      {rec['id']} | dots={rec['n_dots']:,} | changed={pd['pct_changed_moved']:.2f}% "
            f"(sym={pd['pct_changed_sym_diff']:.2f}%) | min_dcat={pd['min_dist_catalogue_px']:.4f}px"
        )

    print("[6/7] REPORT-ONLY instruments (holdout PROXY, SGMC control, block CV) ...")
    eval_arms: dict[str, np.ndarray] = {bpv.PARENT_ID: r0, R1_ID: r1}
    for value, (mask, _) in arms.items():
        eval_arms[built[value]["id"]] = mask
    eval_report = evaluate_report_only_vs_reference(
        arms=eval_arms,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
        reference=R1_ID,
    )

    print("[7/7] Writing ledger rows, mechanism cards and the axis report ...")
    cards = json.loads(CARDS_PATH.read_text()) if CARDS_PATH.is_file() else {}
    cards = {k: v for k, v in cards.items() if not k.startswith(f"{R1_ID}-MASS")}

    new_rows = []
    for value, (mask, _) in arms.items():
        rec = built[value]
        diag = eval_report[rec["id"]]
        r1d = eval_report[R1_ID]
        pre_arm = next(a for a in pre["arms"] if a["value"] == value)
        added = mask & ~r1
        removed = r1 & ~mask
        rec.update(
            {
                "preregistered_prediction": pre_arm["predicted_change"],
                "preregistered_range": pre_arm["predicted_range"],
                "w_model": w_model[value],
                "w_model_caveat": (
                    "IN-SAMPLE and optimistic: the same field w both ranks and scores the arm, "
                    "and w is a ~0.68-AUC proxy for fault presence (PROXY, never a score)."
                ),
                "r1_w_model": {
                    "dti": round(base_terms["dti"], 6),
                    "T": round(base_terms["T"], 3),
                    "S": float(base_terms["S"]),
                    "M": round(base_terms["M"], 3),
                },
                "r1_reference_diagnostics": r1d,
                "report_only_diagnostics": diag,
                "added_dot_saturation": _nearest_parent_distance(r1, added),
                "added_dots": {
                    "n": int(added.sum()),
                    "min_d_cat_px": round(float(d_cat[added].min()), 3) if added.any() else None,
                    "mean_d_cat_px": round(float(d_cat[added].mean()), 3) if added.any() else None,
                    "mean_w": round(float(w_field[added].mean()), 6) if added.any() else None,
                },
                "removed_dots": {
                    "n": int(removed.sum()),
                    "mean_d_cat_px": round(float(d_cat[removed].mean()), 3) if removed.any() else None,
                    "mean_w": round(float(w_field[removed].mean()), 6) if removed.any() else None,
                },
                "parent_dots_mean_w": round(float(w_field[r1].mean()), 6),
                "leakage_canaries": {
                    "passed": True,
                    "max_symmetric_auc": max_auc,
                    "channels": canaries,
                },
            }
        )
        (RELEASES / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")
        cards[rec["id"]] = {
            "parent": R1_ID,
            "axis": AXIS,
            "value": value,
            "preregistered_prediction": pre_arm["predicted_change"],
            "preregistered_range": pre_arm["predicted_range"],
            **CARDS[value],
            "post_build_w_model_delta": f"{w_model[value]['delta_vs_r1']:+.6f}",
            "post_build_report_only": {
                "holdout_proxy_delta_vs_R1": diag["holdout_proxy"]["paired_delta_vs_reference"],
                "holdout_proxy_ci95": diag["holdout_proxy"]["paired_delta_vs_reference_ci95"],
                "sgmc_off_catalogue_dti": diag["sgmc_control"]["dti"],
                "r1_sgmc_off_catalogue_dti": r1d["sgmc_control"]["dti"],
                "cv_12km": diag["block_density_cv"]["cv_12km_120px_interior"],
                "r1_cv_12km": r1d["block_density_cv"]["cv_12km_120px_interior"],
                "random_donor_sgmc_delta_vs_r1": random_control["sgmc_delta_vs_r1"],
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
                "predicted_range": pre_arm["predicted_range"],
                "ranking_basis": RANKING_BASIS,
                "receipt_score": "",
                "receipt_date": "",
                "description": (
                    pre_arm["operation"]
                    + f" from R1 (gate-clean parent, min d_cat 3.1623 px). "
                    + f"preregistered MODEL {pre_arm['predicted_change'].split(':')[-1]} (not a w-model fit); "
                    + f"post-build w-model delta "
                    + f"{w_model[value]['delta_vs_r1']:+.4f} (in-sample, optimistic); holdout PROXY "
                    + f"{hp['dti']:.5f} (delta vs R1 {hp['paired_delta_vs_reference']:+.5f}, "
                    + f"n={hp['withheld_positives']}); SGMC off-cat {diag['sgmc_control']['dti']:.5f} "
                    + f"vs R1 {r1d['sgmc_control']['dti']:.5f}; CV12km "
                    + f"{diag['block_density_cv']['cv_12km_120px_interior']:.4f} vs R1 "
                    + f"{r1d['block_density_cv']['cv_12km_120px_interior']:.4f}; "
                    + f"symmetric difference {rec['parent_diff']['pct_changed_sym_diff']:.2f}% of parent dots; "
                    + (
                        f"ranking premium over same-pool random receivers "
                        f"{diag['sgmc_control']['dti'] - random_control['sgmc_off_catalogue_dti']:+.5f} SGMC; "
                        if added.any()
                        else ""
                    )
                    + f"min d_cat {rec['parent_diff']['min_dist_catalogue_px']:.4f} px "
                    + f"({rec['parent_diff']['dots_le_3px']:,} dots <=3 px)."
                ),
                "recommendation": RECOMMENDATION[value],
            }
        )

    fieldnames = [
        "id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256", "sha256_zeros",
        "status", "predicted_change", "predicted_range", "ranking_basis", "receipt_score",
        "receipt_date", "description", "recommendation",
    ]
    with LEDGER.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for r in [*existing_rows, *new_rows]:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
    CARDS_PATH.write_text(json.dumps(cards, indent=2) + "\n")

    summary = {
        "schema": "gems88.mass-r1-axis-report.v1",
        "session_date": "2026-10-23",
        "axis": AXIS,
        "axis_note": pre["axis_selection"],
        "parent": {
            "id": R1_ID,
            "n_dots": N_PARENT,
            "zeros_sha256": R1_SHA_ZEROS,
            "nan_sha256": R1_SHA_NAN,
            "min_d_cat_px": round(float(d_r1.min()), 4),
            "reconstructed_and_sha_asserted": True,
            "w_model": {
                "dti": round(base_terms["dti"], 6),
                "T": round(base_terms["T"], 3),
                "S": float(base_terms["S"]),
                "M": round(base_terms["M"], 3),
                "W": round(base_terms["W"], 3),
            },
        },
        "r0_reference": {
            "id": bpv.PARENT_ID,
            "n_dots": int(r0.sum()),
            "zeros_sha256": lin["rebuilt_zeros_sha256"],
            "nan_sha256": lin["rebuilt_nan_sha256"],
            "dots_strictly_below_3px": int((r0 & (d_cat < 3.0)).sum()),
        },
        "verified_inputs": len(verified),
        "leakage_canaries": {"passed": True, "max_symmetric_auc": max_auc, "channels": canaries},
        "ranking_definition": pre["ranking_definition"],
        "dose": {"fraction": FRACTION, "n_dots": N_DOSE},
        "candidate_pool_px": int(cand_pool.sum()),
        "preregistered_predictions": {a["value"]: a["predicted_change"] for a in pre["arms"]},
        "w_model_deltas_vs_r1": w_model,
        "random_donor_control": random_control,
        "report_only": eval_report,
        "variants": [{k: v for k, v in built[name].items() if k != "leakage_canaries"} for name in arms],
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    REPORT.write_text(json.dumps(summary, indent=2) + "\n")

    print("\n=== SUMMARY OF BUILT AXIS=MASS (parent R1) VARIANTS ===")
    for value in arms:
        rec = built[value]
        diag = eval_report[rec["id"]]
        r1d = eval_report[R1_ID]
        hp, sg, cv = diag["holdout_proxy"], diag["sgmc_control"], diag["block_density_cv"]
        print(
            f"  {rec['id']} | dots={rec['n_dots']:,} | changed={rec['parent_diff']['pct_changed_moved']:.2f}% "
            f"| min_dcat={rec['parent_diff']['min_dist_catalogue_px']:.4f}px\n"
            f"      pred {pre_arm_pred(pre, value)} | w-model {w_model[value]['delta_vs_r1']:+.4f} | "
            f"holdout PROXY {hp['dti']:.6f} (dvs R1 {hp['paired_delta_vs_reference']:+.6f}) | "
            f"SGMC {sg['dti']:.6f} vs R1 {r1d['sgmc_control']['dti']:.6f} (+{sg['dti'] - r1d['sgmc_control']['dti']:+.6f}) | "
            f"CV12km {cv['cv_12km_120px_interior']:.4f} vs {r1d['block_density_cv']['cv_12km_120px_interior']:.4f}"
        )
    print(f"\nreport: {REPORT.relative_to(ROOT)}  |  elapsed {time.time() - t0:.0f}s")
    return 0


def pre_arm_pred(pre: dict, value: str) -> str:
    return next(a for a in pre["arms"] if a["value"] == value)["predicted_change"]


RECOMMENDATION = {
    "r10minus": (
        "HOLD as a lead, keep as the dose control: if it gains >= +0.01 live, R1 is over-emitted and the "
        "drop direction (not the add direction) is the final-file lever. Gate-clean (100% of dots >3 px)."
    ),
    "r10plus": (
        "SLOT CANDIDATE (2nd priority behind the R1 anchor): the gate-clean form of MASS's only "
        "instrument-positive arm. A live gain >= +0.01 makes 41,419 dots the final-file count; "
        "|delta| < 0.01 is no evidence and retires MASS on both parents."
    ),
    "r10swap": (
        "SLOT CANDIDATE (3rd priority): count-matched, so it isolates ranking quality from mass and spends "
        "no extra denominator mass. Preferred over r10plus at equal score."
    ),
}


if __name__ == "__main__":
    raise SystemExit(main())
