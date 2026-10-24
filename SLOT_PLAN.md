# Slot Plan — Current Automated Decision

**Updated 2026-10-24. No competition slot is authorized or recommended by the current run.**

| Candidate | Evidence | Scientific gate | Registry gate | Slot decision |
|---|---|---|---|---|
| `GEMSDOE88-MRR-BPR-20261024-DO-NOT-SUBMIT` | Candidate **HOLDOUT-DTI `0.185256`**, 95% CI `[0.171519,0.199965]`, `n=22,893`, evaluator `gems57-pooled-hide-v2`; paired incumbent `0.189634`; paired delta `-0.004378`, 95% CI `[-0.007902,-0.000623]` | **FAIL** — confidently below paired incumbent | **FAIL under binding literal rule** — 17GEMSDOE forward overlap `1.0000 > 0.70`; sparse-only diagnostic max `0.684178` passes | **DO NOT SUBMIT; 0 slots used** |

## Why no conditional MRR slot exists

The preregistered promotion rule required candidate HOLDOUT-DTI to exceed the recomputed incumbent, with a paired CI not crossing zero. The observed CI is entirely negative. A valid TIFF and like-for-like sparse-raster uniqueness therefore cannot rescue the method. The all-positive registry witness independently forces the literal gate to fail for this and every nonempty raster; no exemption is authorized.

## Historical candidate plans

Earlier PRUNE, H88-ADHR, GHMD, and UGFV slot suggestions remain research history only. They are not current authorizations, have no ORGANIZER-CONFIRMED receipt in this repository, and are subject to the same binding literal any-raster gate. In particular, PRUNE's high exact overlap with H33 was already recorded as disqualifying under the current user rule. Do not upload an older file merely because MRR-BPR-88 is negative.

## Preconditions for any future weekly slot

1. A newly preregistered, genuinely different method must beat the current paired holdout incumbent on the identical whole-component folds, with a positive paired 95% CI.
2. Every feature-alone leakage canary must remain at or below symmetric AUC `0.90`.
3. Surface `|Spearman rho| <= 0.90` before placement and final 3-pixel forward overlap `<= 0.70` against every registry raster under the currently authorized rule.
4. Independent format validation must pass on the saved TIFF and one-member ZIP, including all-finite values in `[0,1]`.
5. An authenticated organizer template byte check and a separate explicit human portfolio-selector decision are required.
6. After a manual upload only, log the receipt as ORGANIZER-CONFIRMED. Never treat MODEL, PROXY, HOLDOUT-DTI, or H33's reported `0.2778` as a portal receipt.
