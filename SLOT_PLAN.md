# SLOT PLAN — MASS axis (parent h33-h33-2-b2, 20261023)

**Current date:** 2026-10-23 (trust UTC) | **Deadline:** 2026-12-03 17:00 ET | **Slots left this week:** 3/3 | **Total used:** 0/∞ (1 entity rule) | **TOP_PUBLIC:** 0.4413 xiaofanhu (2026-10-22 verified) | **Incumbent best receipt:** 0.2778 CLAIM (no receipt; organizer forum masked, private+expanded labels)

## Next 3 slots in order (this session's AXIS=MASS)

1. **Slot 1 — h33-h33-2-b2-MASSm10-20261023-06d99a7c | MASS_-10pct_drop_lowest_ranked** — Drop 10% lowest-ranked (n=31935, 15.2% changed). Mechanism: Tversky FP penalty 0.2*(S-M) dominates near-catalogue dots; predicted Δ=+0.003 (no evidence if <0.01). Falsifier: if live drops >0.01, dropped dots bridged relays. Go/no-go for mass reduction.

2. **Slot 2 — h33-h33-2-b2-MASSp10-20261023-8fe48581 | MASS_+10pct_add_next_ranked** — Add 10% next-ranked (n=39248, 15.8% changed). Mechanism: marginal gain must exceed 0.059; predicted Δ=-0.004. Falsifier: if live rises >0.01, ranking undervalues intermediate-distance blind corridors. Tests budget ceiling.

3. **Slot 3 — h33-h33-2-b2-MASSswap10-20261023-21cf4658 | MASS_swap10_replace_lowest_with_next** — Swap 10% (n=35483, 15.2% changed). Mechanism: constant S isolates ranking quality (ΔT denominator stable); predicted Δ=+0.002. Falsifier: if negative, candidate pool contaminated by flight-line artifacts. Purest ranking test.

## What each result teaches (decision tree)

- **If m10 > p10 and > swap:** mass reduction beneficial → next week test CONCENTRATION (move 10-20% from low-prior km blocks to high-prior blocks, block 2km, CV 0.51-0.59 target) with reduced mass baseline.
- **If p10 best:** our ranking underestimates distant blind faults → propose RELIEF axis (shift 10-15% mass across relief terciles, detrended-elev band) to capture piedmont/range-front geothermal step-overs.
- **If all Δ within ±0.01:** ranking ~random; treat as no evidence; pivot to SNAP (snap dots ≤2px to TMI/gravity gradient edges) + PRUNE (1/2/3px) combo wk3-4.

## Weeks to deadline (6 weeks left)

- **wk1-2 (now):** MASS, CONCENTRATION, SNAP, PRUNE, RELIEF (this plan covers MASS; next session pick CONCENTRATION 10%/15%/20% with 5km blocks, CV report).
- **wk3-4:** Combine two best axes (e.g., MASS+RELIEF or MASS+CONCENTRATION) at matched 38k dots; validate 3px exclusion, format, uniqueness (<0.70 overlap vs 134 genuine rasters).
- **wk5-6:** Confirm with blind HOLDOUT-DTI (n=22893, CI) but never gate; choose final + fallback (different mass/concentration), re-validate format (NaN outside / zeros fallback) and byte-read SHA; prepare disclosure (AI_USE.md).
- **Per-slot budget:** 1 change from parent that teaches us something; <0.01 = no evidence (private chunks differ); no label probing; licensed data only (USGS CC0, GDR CC BY 4.0).

## Mechanism cards (structural geologist)

- **MASS_m10:** Hypothesis: near-catalogue fringe dots are FP-dominated. Mechanism above. Mimic: alluvial fan apices. Predicted +0.003, falsifier as above.
- **MASS_p10:** Hypothesis: next-ranked mid-distance footwall flexures carry blind geothermal. Mechanism above. Mimic: lithologic contacts. Predicted -0.004.
- **MASS_swap10:** Hypothesis: ranking quality > mass effect. Mechanism above. Mimic: 400m flight-line corrugation. Predicted +0.002.

*Proposed better axes in next session:* RELIEF-stratified hydrothermal magnetite destruction trough (K/Th, U/Th) + LSCK (lidar scarp + chi knickpoint) — mechanisms documented in knowledge/field-guide.md; confounders (playa, Lahontan benches) and falsifiers (no DTI gain with shoreline veto) recorded separately.
