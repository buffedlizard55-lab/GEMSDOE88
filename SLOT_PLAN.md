# SLOT_PLAN — one entity; at most 3 scored files per rolling week; one blind final file

**2026-10-23 status:** all 15 pins and byte-exact R0 were verified (`N=37,654`; zeros `c55bafc4…`; NaN `baeae321…`). The reconciled ledger has **41 BUILT / 0 RECEIPT**. R0 `0.2778` is **CLAIM**, not a portal score. No agent accessed a portal or submitted a file.

## Non-negotiable gate context

- **Pure R0 SNAP is stopped:** `30` of R0's `1,611` `<3 px` dots have no `>=3 px` destination within a `<=2 px` SNAP. A farther move or refill changes the axis (`evidence/session_20261023_snap_clearance.json`; IR-88-47).
- The independent validator now rejects any non-PRUNE positive mass at catalogue distance `<3 px`. Historic R0 SNAP/CONCENTRATION/RELIEF arms with inherited collar mass remain HOLD.
- p1/p3/p4 PRUNE twins have an upstream fresh disk-validation receipt, but every human upload still requires an exact current-byte re-read.

## Two independent SPACING families — six BUILT, zero slot recommendations

| Parent / arms | Common edit | Registered `MODEL` / report-only reading | Decision |
|---|---|---|---|
| Gate-clean `R1`: `poisson28` `60f65400`, `lattice4px` `6c7e0b72`, `strike` `bc8e6d1a` | same `1,914` greedy-decluster donors (5.08%); receiver geometry only | `+0.003/−0.004/+0.000`; SGMC vs R1 `+0.00074/−0.00079/−0.00069` | HOLD; `poisson28` is maximally uniform feasible geometry, not a strict spacing lock. |
| R0: `lattice` `03d14f38`, `poisson` `80ede4fa`, `alongstrike` `5cb97402` | same `5,376` relocation: `1,611` forced collar repairs + `3,765` donors; ordering only | `−0.007/−0.003/+0.002`; SGMC vs R0 `−0.000165/−0.000325/−0.000222` | HOLD; shared collar repair and `sqrt(5)` guard make it lower-priority than the R1 family. |

All are `MODEL`/`PROXY`, never scores or gates. Strict matched-count spacing on H19-5 is infeasible; ancestor-supported PRUNE `p3space35` is a separate support/refill test. The R0 namespace is deliberately distinct: `spacing_r0_*` evidence/script/test paths preserve that family without overwriting R1's generic `spacing_*` records.

## Human-controlled conditional queue

| Order | Existing arm | Preconditions / receipt interpretation |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705` (`MODEL +0.005`) | Reconstruct/revalidate actual primary or zeros bytes. Gain `>=0.01` supports collar+refill; loss `<=−0.01` closes it; otherwise inconclusive. |
| 2 | `PRUNEp3space35-49fff49b` (`MODEL +0.007`) | Only after human quota/receipt review and fresh exact-byte validation. It tests spacing support by effect size, not a score. |
| 3 | Reserve `PRUNEp4space35-07bd8182` (`MODEL +0.002`) | Only after receipt-backed support for slot 2; otherwise conserve the slot. |

Neither SPACING family displaces this queue absent an explicit human decision to run a low-priority diagnostic. Primary and `-zeros` fallback are alternatives, never two slots.

## Before any human upload

1. Confirm current `TOP_PUBLIC` **with date**, rolling-week/total availability, deadline, data-use authorization, and actual upload history.
2. Match recorded SHA-256 and rerun `scripts/validate_variant.py` on the actual selected TIFF/twin.
3. Upload one file only; retain the verbatim receipt and populate `receipt_score` / `receipt_date`. A live `|Δ| < 0.01` is no evidence.
4. Choose the one blind final file independently. `RECEIPT > CLAIM > PROXY > MODEL`; no local diagnostic chooses it.
