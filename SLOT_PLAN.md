# Slot plan — 2026-10-23

**Entity/quota:** one entity, at most 3 scored submissions per rolling week; **slots left: UNSUPPLIED**.  
**Target:** `TOP_PUBLIC = UNSUPPLIED` (human must enter a dated leaderboard value). R0 `0.2778` is **CLAIM**.  
**Deadline:** `2026-12-03` is **UNCONFIRMED**; the human must confirm it manually on the competition page.

## Reconciled build inventory

This branch built one PRUNE3 variant. A concurrent branch merged three MASS variants before this PR; all four are now in `ledger/submissions.csv`, so **no further variant is built in this session**. The MASS files retain the parent's 2 px collar and are **HOLD—not eligible under the current 3 px non-PRUNE gate**. Exact hashes are deduped; rank-correlation and dot-overlap thresholds are not promotion gates.

## Next three slots, in order

1. **BUILT — PRUNE3 fixed-count falsifier:** `h33-h33-2-b2-prune3-20261023-01d57649` (NaN twin **or** `-zeros` twin, never both). **MODEL −0.003**; both report-only proxies are negative. Spend this slot only if the human values a near-catalogue falsification test despite that prediction.
   - Receipt `>=+0.01`: falsifies the small-loss mechanism; prioritize a deeper-collar controlled edit and investigate why both proxies missed.
   - Receipt `<=-0.01`: retire deeper pruning; prioritize collar relaxation. `|delta|<0.01`: **no evidence**; do not infer a mechanism or combine axes from it.
2. **PROPOSED, not built — COLLAR-RELAX1 (or PRUNE4 only after a >=+0.01 PRUNE3 receipt):** at fixed count, exchange 5% of R0's lowest exact-marginal-credit far dots for H19-5 support at `1<d_cat<=2 px`.
   - **Mechanism:** new splays can lie inside 300 m of known traces. **Confounder:** masked known traces make nearby false positives expensive; exact-credit ranking can overfit SGMC/catalogue proxies. **Falsifier:** a `<=-0.01` receipt; `<0.01` absolute is no evidence.
3. **PROPOSED, not built — MARGINAL-CREDIT5:** exchange the bottom 5% of R0 dots by exact marginal DTI gain against an independent, fold-visible fault prior with the highest-credit legal unselected support.
   - **Mechanism:** maximize realized triangular-kernel credit at fixed mass, including redundancy through `T` and `M`. **Confounder:** the prior's weak/unstable live correlation and any spacing drift. **Falsifier:** no `>=+0.01` receipt after one controlled test; do not iterate on smaller changes.

SNAP is unscheduled because 30 dots cannot satisfy both `<=2 px` movement and the non-PRUNE `>=3 px` exclusion. Do not spend slots on exact PRUNE1/PRUNE2/R0 repeats, the non-compliant MASS artifacts, or another account for feedback.

## Weeks to the deadline

- **Week 1 (Oct 23–29):** slot 1 above only after the human supplies slot availability and accepts the predicted-negative falsifier; otherwise hold all slots.
- **Week 2 (Oct 30–Nov 5):** build the conditional slot-2 axis only in a new authorized experiment budget and after reconciling all concurrent ledgers; do not repeat an existing `(parent,axis,value)` pair.
- **Weeks 3–4 (Nov 6–19):** combine at most the two axes with independent receipt evidence `>=0.01`; never combine sub-0.01 movements.
- **Weeks 5–6 (Nov 20–Dec 3):** confirm the leading file and a fallback, choose the single final file blind, and re-run byte/format validation on both. Preserve one week for reproducibility and AI-disclosure checks.
