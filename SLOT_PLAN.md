# SLOT_PLAN — one entity; at most 3 scored files per rolling week; one blind final file

**2026-10-23 reconciled status:** all 15 pins and byte-exact R0 passed (`N=37,654`; zeros `c55bafc4…`; NaN `baeae321…`). The ledger has **44 BUILT / 0 RECEIPT** rows across 7 axes; all exact `(parent, axis, value)` and primary/zeros hashes are unique. R0 `0.2778` is **CLAIM**, not a portal score. No agent accessed a portal or submitted a file.

## Non-negotiable gate context

- Pure R0 SNAP is stopped: `30` of R0's `1,611` `<3 px` dots lack a legal `>=3 px` destination within a 2-px SNAP. The current validator rejects every non-PRUNE positive pixel at `<3 px`; historic R0 non-PRUNE descendants that inherit collar mass remain HOLD.
- Primary and `-zeros` fallback files are alternatives, never two slots. A `MODEL`, SGMC, hide/recover value, or `CLAIM` is never a score or promotion gate.
- The human alone confirms current TOP_PUBLIC/date, quota, deadline, provenance authorization, actual upload history, selected exact bytes, receipt, and blind final file.

## TRACKB — Phase 2 only, no default weekly slot

| Parent / arms | Controlled distinction | Report-only reading | Decision |
|---|---|---|---|
| Gate-clean `R1`: `traceext10` `05256d87`, `speckle10minus` `3360100c`, `tracespine10` `a3a183d1` | Same 3,765-dot dose: spaced tip/relay extension vs pure isolated-speckle cut vs 100 m continuous-spine control, grounded in tracked `1,259` `>=1 km` GeoJSON traces | SGMC `0.09462 / 0.08666 / 0.08700` vs R1 `0.096083`; `traceext10` recovers far more than spine infill but remains below R1 | Phase-2 **HOLD**. It does not enter the weekly queue unless a human independently decides otherwise. See IR-88-49. |

## Two independent SPACING families — six BUILT, zero slot recommendations

| Parent / arms | Common edit | Registered `MODEL` / report-only reading | Decision |
|---|---|---|---|
| Gate-clean `R1`: `poisson28` `60f65400`, `lattice4px` `6c7e0b72`, `strike` `bc8e6d1a` | Same `1,914` greedy-decluster donors (5.08%); receiver geometry only | `+0.003/−0.004/+0.000`; SGMC vs R1 `+0.00074/−0.00079/−0.00069` | HOLD; `poisson28` is maximally uniform feasible geometry, not a strict spacing lock. |
| R0: `lattice` `03d14f38`, `poisson` `80ede4fa`, `alongstrike` `5cb97402` | Same `5,376` relocations: `1,611` collar repairs + `3,765` donors; ordering only | `−0.007/−0.003/+0.002`; SGMC vs R0 `−0.000165/−0.000325/−0.000222` | HOLD; shared repair and `sqrt(5)` guard make it lower-priority than the R1 family. |

R1 keeps generic `spacing_*` paths. R0 keeps explicit `spacing_r0_*` code/evidence paths, so concurrent work cannot overwrite either lineage. All report-only evidence remains diagnostic only.

## Human-controlled conditional queue

| Order | Existing arm | Preconditions / receipt interpretation |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705` (`MODEL +0.005`) | Reconstruct/revalidate the actual selected primary or zeros twin. Gain `>=0.01` supports collar+refill; loss `<=−0.01` closes it; otherwise inconclusive. |
| 2 | `PRUNEp3space35-49fff49b` (`MODEL +0.007`) | Only after human quota/receipt review and fresh exact-byte validation. It tests spacing support by effect size, not a score. |
| 3 | Reserve `PRUNEp4space35-07bd8182` (`MODEL +0.002`) | Only after receipt-backed support for slot 2; otherwise conserve the slot. |

`TRACE_ADD_ONLY` is a proposal, not a build: future spaced `>=2.8 px` trace-tip adds on R1 or `p3space35` should avoid dropping singleton donors and require a separate named parent/axis/value. Its falsifier is no `>=0.01` receipt-backed gain at matched collar (IR-88-49).

## Before any human upload

1. Confirm current TOP_PUBLIC **with date**, rolling-week/total availability, deadline, data-use authorization, and actual upload history.
2. Match recorded SHA-256 and rerun `scripts/validate_variant.py` on the actual selected TIFF/twin.
3. Upload one file only; retain the verbatim receipt and populate `receipt_score` / `receipt_date`. A live `|Δ| < 0.01` is no evidence.
4. Choose the one blind final file independently. `RECEIPT > CLAIM > PROXY > MODEL`; no local diagnostic chooses it.
