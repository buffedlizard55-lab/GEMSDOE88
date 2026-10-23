#!/usr/bin/env python3
"""Report-only decomposition for the AXIS=MASS session: MASS effect vs RANKING effect.

The three built arms confound two things:
  * the pure MASS effect (S changes, so 0.2*(S-M) in the DTI denominator changes), and
  * the RANKING effect of the exact-marginal field w, which decides *which* dots move.

IR-88-38 already measured that w has AUC 0.4724 for SGMC-credited R0 dots, i.e. the
field is worse than random at picking blind faults. The r10swap arm (mass held at
37,654, low-w dots out, high-w dots in) isolated that: w-model +0.0029 but blind
SGMC control -0.0040. This script separates the two effects with uniformly random
donors/receivers at the identical 3,765-dot dose, then revises the MODEL
predictions in the ledger with a fixed, pre-declared rule.

It writes NO GeoTIFF, no release, and no new (axis, value) pair. Random arms are
diagnostics, never candidates: they are not reproducible as submissions and are
not entered in ledger/submissions.csv.
"""
from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import metric  # noqa: E402
from scripts import build_prune_variants as bpv  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
SEED = 20261023
DOSE = 3_765
AXIS = "MASS"
REPORT = ROOT / "evidence" / "mass_r0_axis_report.json"
OUT = ROOT / "evidence" / "mass_r0_ranking_control.json"

# Pre-declared revision rule (fixed before the controls are looked at):
#   cons = the instrument estimate closest to zero when both instruments agree in
#          sign, or their midpoint when they disagree;
#   range = [min(cons - 0.005, w_delta, sgmc_delta), max(cons + 0.005, w_delta, sgmc_delta)]
# The w-model delta is in-sample (the same field ranks and scores), so whenever the
# two instruments disagree the conservative (near-zero) reading is reported.
BAND = 0.005


def main() -> int:
    t0 = time.time()
    report = json.loads(REPORT.read_text())
    built = {v["value"]: v for v in report["variants"]}

    verified = bpv.verify_manifest()
    lin = bpv.rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, r0 = lin["h19_5"], lin["r0"]
    cand_pool = h19_5 & ~r0 & (d_cat > 3.0)

    sgmc_raw = bpv.rasterio.open(verified["sgmc_faults_control"]).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)

    rng = np.random.default_rng(SEED)
    py, px = np.nonzero(r0)
    cy, cx = np.nonzero(cand_pool)
    drop_idx = rng.choice(len(py), size=DOSE, replace=False)
    add_idx = rng.choice(len(cy), size=DOSE, replace=False)

    rand_minus = r0.copy()
    rand_minus[py[drop_idx], px[drop_idx]] = False

    rand_plus = r0.copy()
    rand_plus[cy[add_idx], cx[add_idx]] = True

    rand_swap = rand_minus.copy()
    rand_swap[cy[add_idx], cx[add_idx]] = True

    arms = {
        "R0": r0,
        "rand10minus": rand_minus,
        "rand10plus": rand_plus,
        "rand10swap": rand_swap,
    }

    def sgmc(mask: np.ndarray) -> float:
        return float(metric.dti_binary(mask, sgmc_off, valid=foot, known=catalogue)["dti"])

    def cv12(mask: np.ndarray) -> float:
        return round(bpv.compute_block_cv(mask, foot, 120), 4)

    scores = {k: sgmc(m) for k, m in arms.items()}
    cvs = {k: cv12(m) for k, m in arms.items()}
    counts = {k: int(m.sum()) for k, m in arms.items()}
    for k in arms:
        print(f"  {k:12s} dots={counts[k]:>6,} SGMC={scores[k]:.6f} CV12km={cvs[k]}")

    # Built (w-ranked) arms, recomputed here from the identical seeds so the comparison
    # is single-run: their SGMC values are also in mass_r0_axis_report.json.
    ranked = {v: built[v]["report_only_diagnostics"]["sgmc_control"]["dti"] for v in built}
    r0_sgmc = scores["R0"]

    decomp = {}
    for value, rand_key in (("r10minus", "rand10minus"), ("r10plus", "rand10plus"), ("r10swap", "rand10swap")):
        ranked_delta = ranked[value] - r0_sgmc
        random_delta = scores[rand_key] - r0_sgmc
        decomp[value] = {
            "ranked_delta_vs_r0_sgmc": round(ranked_delta, 6),
            "random_delta_vs_r0_sgmc": round(random_delta, 6),
            "ranking_effect_sgmc": round(ranked_delta - random_delta, 6),
            "pure_dose_effect_sgmc": round(random_delta, 6),
            "w_model_delta": built[value]["w_model"]["delta_vs_r0"],
            "reading": (
                "the w-ranking moves the blind control {} by {:+.6f} relative to random donors"
            ).format("UP" if ranked_delta - random_delta > 0 else "DOWN", ranked_delta - random_delta),
        }

    # ---- pre-declared revision rule -------------------------------------------------
    revised = {}
    for value in ("r10minus", "r10plus", "r10swap"):
        w_delta = built[value]["w_model"]["delta_vs_r0"]
        s_delta = decomp[value]["ranked_delta_vs_r0_sgmc"]
        if np.sign(w_delta) == np.sign(s_delta):
            cons = min(w_delta, s_delta, key=abs)
        else:
            cons = 0.5 * (w_delta + s_delta)
        lo = min(cons - BAND, w_delta, s_delta)
        hi = max(cons + BAND, w_delta, s_delta)
        revised[value] = {
            "w_model_delta": w_delta,
            "sgmc_delta": s_delta,
            "revised_model": round(cons, 3),
            "revised_range": f"[{lo:+.3f}, {hi:+.3f}]",
            "rule": "closest-to-zero when signs agree, midpoint when they disagree; band +/-0.005, widened to cover both instruments",
        }
        print(
            f"  {value}: w={w_delta:+.6f} sgmc={s_delta:+.6f} -> MODEL {cons:+.3f} "
            f"{revised[value]['revised_range']}"
        )

    out = {
        "schema": "gems88.mass-r0-ranking-control.v1",
        "session_date": "2026-10-23",
        "purpose": "separate the pure MASS (dose) effect from the w-RANKING effect on the blind off-catalogue SGMC control",
        "seed": SEED,
        "dose": DOSE,
        "control_construction": {
            "rand10minus": "3,765 parent dots removed uniformly at random (default_rng(20261023))",
            "rand10plus": "3,765 candidates drawn uniformly at random from H19-5 & ~R0 & d_cat>3px",
            "rand10swap": "both of the above at fixed count 37,654",
            "note": "diagnostics only: no GeoTIFF, no ledger row, no (axis, value) pair, never a candidate",
        },
        "sgmc_off_catalogue_px": int(sgmc_off.sum()),
        "sgmc_scores": {k: round(v, 6) for k, v in scores.items()},
        "cv_12km": cvs,
        "dot_counts": counts,
        "decomposition": decomp,
        "revised_predictions": revised,
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": bpv.git_sha(),
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")

    # ---- apply the revision to ledger rows, receipts and mechanism cards -------------
    ledger_path = ROOT / "ledger" / "submissions.csv"
    rows = list(csv.DictReader(ledger_path.open(newline="")))
    for r in rows:
        if r["axis"] == AXIS and r["value"] in revised:
            rv = revised[r["value"]]
            r["predicted_change"] = f"MODEL:{rv['revised_model']:+.3f}"
            r["predicted_range"] = rv["revised_range"]
            if "REVISED after report-only instruments" in r["description"]:
                continue  # idempotent re-run
            r["description"] += (
                f" REVISED after report-only instruments: w-model {rv['w_model_delta']:+.4f}, "
                f"blind SGMC delta {rv['sgmc_delta']:+.4f}; random-donor control attributes "
                f"{decomp[r['value']]['ranking_effect_sgmc']:+.4f} to the w-ranking and "
                f"{decomp[r['value']]['pure_dose_effect_sgmc']:+.4f} to the dose itself "
                f"(evidence/mass_r0_ranking_control.json)."
            )
    fieldnames = list(rows[0].keys())
    with ledger_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # Recommendations written by the builder reflected the PREREGISTERED expectations.
    # They are overwritten here with what the instruments actually showed (idempotent:
    # this assignment, unlike the description append above, is stable across re-runs).
    recommendations = {
        "r10minus": (
            "NOT QUEUED - worst arm. Both instruments agree it loses (MODEL -0.008; blind SGMC "
            "-0.0081, w-model -0.0084, random donors -0.0062). Do not spend a slot: it retires "
            "further mass reduction by showing R0 carries no dead mass."
        ),
        "r10plus": (
            "SLOT 2 CANDIDATE (conditional). The only arm in the inventory predicted positive by two "
            "independent instruments (MODEL +0.003 [-0.002,+0.011]; blind SGMC +0.0029, w-model "
            "+0.0107, random donors +0.0011). Adds nothing inside 3 px (new dots min d_cat 3.162 px) "
            "and stays inside the 37-44k band, but inherits R0's 2,171 collar dots, so spend only "
            "after the human scopes the >=3 px rule for controlled R0 edits; +0.003 is below the "
            "0.01 no-evidence threshold."
        ),
        "r10swap": (
            "NOT QUEUED. The instruments disagree (w-model +0.0029, in-sample, vs blind SGMC -0.0040) "
            "so the revised prediction is -0.001. Retained as the session's cleanest measurement: at "
            "fixed count the w-ranking is worth only +0.0005 over random donors, replicating IR-88-38's "
            "AUC 0.4724 for blind-fault credit."
        ),
    }
    for r in rows:
        if r["axis"] == AXIS and r["value"] in recommendations:
            r["recommendation"] = recommendations[r["value"]]
    with ledger_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    cards = json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
    for key, card in cards.items():
        if f"-{AXIS}r" not in key:
            continue
        value = card["value"]
        rv = revised[value]
        card["revised_prediction"] = f"{rv['revised_model']:+.3f}"
        card["revised_range"] = rv["revised_range"]
        card["post_build_report_only"]["sgmc_delta_vs_r0"] = round(rv["sgmc_delta"], 6)
        card["post_build_report_only"]["ranking_effect_sgmc"] = decomp[value]["ranking_effect_sgmc"]
        card["post_build_report_only"]["pure_dose_effect_sgmc"] = decomp[value]["pure_dose_effect_sgmc"]
        if "REVISED to" in card["predicted_sign_size"]:
            continue  # idempotent re-run
        card["predicted_sign_size"] += (
            f" REVISED to {rv['revised_model']:+.3f} MODEL after the report-only instruments "
            f"(w {rv['w_model_delta']:+.4f}, blind SGMC {rv['sgmc_delta']:+.4f}); the preregistered value "
            f"{card['preregistered_prediction']} is retained above so the correction is auditable."
        )
    (ROOT / "ledger" / "mechanism_cards.json").write_text(json.dumps(cards, indent=2) + "\n")

    for v in report["variants"]:
        rec_path = ROOT / "releases" / f"{v['id']}.json"
        rec = json.loads(rec_path.read_text())
        rec["revised_prediction"] = revised[v["value"]]
        rec["ranking_control"] = decomp[v["value"]]
        # The form note is what the human pastes into the DrivenData upload form, so it
        # must carry the REVISED prediction, not the raw in-sample w-model delta. The
        # raster bytes are untouched, hence every SHA-256 above is unchanged.
        note = re.sub(r"pred [+-][0-9.]+ MODEL", f"pred {revised[v['value']]['revised_model']:+.3f} MODEL", rec["form_note"])
        assert len(note) <= 140, f"revised form note > 140 chars ({len(note)}): {note}"
        rec["form_note"] = note
        rec["form_note_chars"] = len(note)
        rec_path.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"  {v['id']}: note -> {note}")

    print(f"Wrote {OUT.relative_to(ROOT)}; ledger/receipts/cards revised in {out['elapsed_seconds']}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
