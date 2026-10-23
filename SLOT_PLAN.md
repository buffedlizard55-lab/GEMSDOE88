# SLOT PLAN — GEMS Prize (DrivenData #306) — Entity week tracking

> **Deadline:** 2026-12-03 17:00 ET (confirm on competition page). **Quota:** 3 scored submissions / rolling week, 1 final blind pick. **Week claimed:** 2026-10-23. **Slots left this week:** 3/3 (0 scored uploads this roll). **Total slots to deadline:** ~21 (7 weeks ×3).

## This session (AXIS=MASS) — built 2026-10-23

Parent **R0 = h33-h33-2-b2 (GEMSDOE32)**: 37,654 unit-mass dots, 0 within 2 px of catalogue, `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`. Claimed 0.2778 CLAIM (no receipt in ledger/). Verified grid SHA: sample_submission `2176d08e...`, existing_faults `7ba308cc...`.

| ID | Axis | Value | n_dots | % changed | sha8 | Predicted live Δ | Status |
|---|---|---|---|---|---|---|---|
| h33-h33-2-b2-MASSm10minus-20261023-7132935e | MASS | m10minus (drop lowest 10%) | 33,889 | 10.00% | 7132935e | -0.008 | BUILT |
| h33-h33-2-b2-MASSm10plus-20261023-82673b57 | MASS | m10plus (add next 10%) | 41,419 | 10.00% | 82673b57 | +0.004 | BUILT |
| h33-h33-2-b2-MASSm20minus-20261023-6c73303c | MASS | m20minus (drop lowest 20%) | 30,123 | 20.00% | 6c73303c | -0.018 | BUILT |

All 3 keep ≥2 px from catalogue (parent's 2 px rule) and 0 on catalogue. Inside footprint values {0,1}, outside NaN (plus -zeros fallback). Re-read verified.

**Mechanism summary:** Rank = 0.6·norm(dist_>2px/50)+0.4·rand(seed88) on parent; candidate pool ranked identically on allowed_2px (seed90). Marginal DTI threshold ~0.056 at DTI 0.28. Low tail dominated by Lahontan benches + E-W flight-line corrugation mimics.

## Next 3 slots in order (default wk1-2 plan)

1. **Slot 1 — MASSm10minus (33,889)** — Least risky mass elasticity probe. If Δ ≥+0.01 live, parent over-dense → advance to MASSm20minus/m30minus; if Δ ≤-0.01, parent near-optimal mass, pivot to CONCENTRATION. Falsifier in `ledger/mechanism_cards.json`.

2. **Slot 2 — MASSm10plus (41,419)** — Tests tip-relay undersampling. If Δ ≥+0.01, add logic validated → next combine MASS+PRUNE; if Δ ≤-0.015, added dots are outflow/pluton noise, abandon add path, try CONCENTRATION.

3. **Slot 3 — CONCENTRATION 15% (1 km blocks, CV report)** — Move 15% dots from lowest-prior to highest-prior 10 px (1 km) blocks (prior = parent density + physics tip-beam). Report CV before/after (H33 CV ~0.55; best files 0.51-0.59). If CV→0.58 and Δ>+0.01, evidence for km-scale geothermal focus; if CV→0.70 and Δ<0, over-concentration penalty.

## Weeks to deadline (7 weeks, 21 slots max, 1 final blind)

- **Wk1-2 (now → 11-05):** MASS (3 variants above), CONCENTRATION (m10/m15/m20, same count, block CV 0.51-0.59), SNAP (≤2 px snap to edge/scarp, mean displacement report, count fixed), PRUNE (≤1/≤2/≤3 px, refill count), RELIEF (basin/piedmont/range-front tercile shifts 10-15%, count fixed). Each (AXIS,value) built once; check ledger.

- **Wk3-4:** Combine two best axes by live Δ (e.g., best MASS + best CONCENTRATION). Pre-register fusion (e.g., MASSm10minus + CONC15) at identical mass, keep 1-50% change budget.

- **Wk5-6:** Confirm leader on private-like holdout (PROXY, never gate), pick final + fallback, re-validate format of both (CRS EPSG:32611 3730×3292 float32 [0,1] NaN outside), disclose AI_USE.md, submit single blind file per Rules §3.4.

> Evidence labels: RECEIPT (submission-page receipt) | CLAIM (owner-reported) | PROXY (local holdout) | MODEL (projection). Treat Δ<0.01 live as no evidence (public chunks only).
