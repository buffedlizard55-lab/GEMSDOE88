#!/usr/bin/env python3
"""MODEL projection of the live effect of the CONCENTRATION variants.

The projection is pure metric algebra (the same equations as
``vendor/gems57/metric.py``), evaluated on a scenario grid.  It is a MODEL:
no ground truth is touched, and the two inputs it calibrates on are CLAIMs, not
receipts.

Calibration
-----------
The ledger's thinning lineage contains two files whose off-catalogue geometry is
pixel-identical (README forensic note IR-88-08): ``D2.8`` = 44,090 dots at
CLAIM 0.2600 and ``H33`` = 37,654 dots at CLAIM 0.2778, the difference being
6,436 dots inside the catalogue collar, which earn no truth credit.  Writing
``DTI = T / (0.2 T + 0.2 (n - M) + 0.8 |G|)`` and holding ``T``, ``M`` and
``|G|`` fixed across the two files, the pair solves for ``T`` and for the
denominator of H33.  Those two numbers then convert any assumed change in the
add/remove credits into a projected DTI change.

One relocation contributes
``d_D = 0.2 * (t_add - t_rm + m_rm - m_add)`` to the denominator and
``t_add - t_rm`` to the numerator, where ``t_*`` are marginal *truth* credits
and ``m_*`` are the dots' own kernel self-credits ``max_g k``.  Because the dot
count is fixed, every dot moved out of a zero-credit location relieves 0.2 of
penalty weight and every dot moved next to an existing (already covering) dot
costs only 0.2 (1 - m_add).

Scenarios span the only genuinely unknown quantity: how close the parent's
hottest traces actually are to new-fault truth (``m_add``), and how much recall
is lost from the donors (``t_rm``).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "registry" / "concentration_projection.json"

ALPHA, BETA = 0.2, 0.8
N_R0 = 37_654
N_D28 = 44_090
DTI_R0 = 0.2778          # CLAIM (no receipt)
DTI_D28 = 0.2600         # CLAIM (no receipt)
N_NEAR = N_D28 - N_R0    # dots inside the 2 px collar of D2.8


def calibrate() -> dict:
    # 1/DTI grows as collar dots are added, so the *increase* is the positive margin
    inv = 1.0 / DTI_D28 - 1.0 / DTI_R0
    T = ALPHA * N_NEAR / inv
    D = T / DTI_R0
    # D = alpha*T + alpha*(n - M) + beta*|G|  ->  beta*|G| - alpha*M
    betaG_minus_alphaM = D - ALPHA * T - ALPHA * (N_R0 - 0.0)
    return {
        "T_R0_CLAM": T,
        "D_R0_CLAM": D,
        "betaG_minus_alphaM": betaG_minus_alphaM,
        "G_if_M_zero": betaG_minus_alphaM / BETA,
        "coverage_T_over_G_if_M_zero": T / (betaG_minus_alphaM / BETA),
        "n_near_collar": N_NEAR,
        "sensitivity_dDTI_per_unit_dD": -T / D**2,
    }


def project(n_moved: int, m_add: float, t_add_ratio: float, m_rm: float, t_rm: float,
            cal: dict) -> dict:
    """Exact DTI before/after for one relocation scenario (M held at 0 baseline)."""
    T0, D0 = cal["T_R0_CLAM"], cal["D_R0_CLAM"]
    t_add = t_add_ratio * m_add          # only partial credit: hosts already cover
    dT = n_moved * (t_add - t_rm)
    dD = ALPHA * (dT + n_moved * (m_rm - m_add))
    T1, D1 = T0 + dT, D0 + dD
    return {
        "delta_T": dT, "delta_D": dD,
        "DTI_before": T0 / D0, "DTI_after": T1 / D1,
        "delta_DTI": T1 / D1 - T0 / D0,
    }


def main() -> int:
    cal = calibrate()
    variants = json.loads((ROOT / "registry" / "concentration_report.json").read_text())["variants"]
    out = {
        "evidence_class": "MODEL",
        "caveat": ("Projection, not a score. Calibrated on two owner-reported CLAIMs "
                   "(0.2778 and 0.2600) and on the README's pixel-identity finding; the "
                   "private-chunk score can differ, and a live change under 0.01 is not evidence."),
        "algebra": "DTI = T / (alpha*T + alpha*(n - M) + beta*|G|), alpha=0.2, beta=0.8",
        "calibration": cal,
        "scenario_axes": {
            "m_add": "self-credit of a receiver welded 1 px from a surviving host dot",
            "t_add_ratio": "fraction of m_add that becomes *new* truth credit (redundancy)",
            "m_rm": "self-credit of a donor (cold-block, collar-free dot)",
            "t_rm": "truth credit lost per donor (recall cost of the sparse tail)",
        },
        "variants": {},
    }
    # Scenario grid over the two genuinely unknown quantities.  ``m_add_base`` is
    # the self-credit a receiver would have if it were welded next to the
    # *best* (1 km, hottest-block) hosts; each variant scales it by the ratio of
    # its receivers' mean block prior to that variant's, so the 5 km variant is
    # projected as the weaker bet it is.
    ref_prior = max(v["diff_stats"]["added_block_prior_mean"].__float__() for v in variants.values())
    scenarios = [(m, 0.20, 0.02, t) for m in (0.15, 0.30, 0.45, 0.60) for t in (0.00, 0.02, 0.05)]
    for vid, v in variants.items():
        n = v["diff_stats"]["n_moved"]
        scale = v["diff_stats"]["added_block_prior_mean"] / ref_prior
        rows = []
        for m_base, ratio, m_rm, t_rm in scenarios:
            r = project(n, m_base * scale, ratio, m_rm, t_rm, cal)
            rows.append({"m_add_base": m_base, "m_add": m_base * scale,
                         "t_add_ratio": ratio, "m_rm": m_rm, "t_rm": t_rm, **r})
        deltas = [r["delta_DTI"] for r in rows]
        point = [r for r in rows if r["m_add_base"] == 0.30 and r["t_rm"] == 0.02][0]
        out["variants"][vid] = {
            "n_moved": n,
            "prior_scale_vs_hottest": float(scale),
            "point_estimate": point["delta_DTI"],
            "range_scenarios": [min(deltas), max(deltas)],
            "scenarios": rows,
        }
        print(f"{vid:58s} n={n:5d} scale {scale:.2f} point {point['delta_DTI']:+.4f} "
              f"range [{min(deltas):+.4f}, {max(deltas):+.4f}]")
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("calibration:", {k: round(v, 4) for k, v in cal.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
