# Slot plan — 2026-10-23 (reconciled: PRUNE3 + MASS audit + CONCENTRATION)

**Entity/quota:** one entity, at most 3 scored submissions per rolling week; **slots left: UNSUPPLIED**.
**Target:** `TOP_PUBLIC = UNSUPPLIED` (human must enter a dated leaderboard value). R0 `0.2778` is **CLAIM**.
**Deadline:** `2026-12-03` is **UNCONFIRMED**; confirm manually on the competition page.
**Evidence labels:** RECEIPT | CLAIM | PROXY | MODEL. A live change under 0.01 is no evidence.

## Reconciled inventory — 7 built candidates, none submitted

| Pair `(parent, axis, value)` | n | changed | Predicted Δ (MODEL) | Gate status |
|---|---|---|---|---|
| `prune3` (2 px → ≤3 px + fixed-count H19 BFS refill) | 37,654 | 2,171 (5.77 %) | −0.003 `[-0.010,+0.003]` | **eligible**: every dot `d_cat>3` |
| `CONC b10px-m10` (1 km, 10 % coldest→hottest) | 37,654 | 3,765 (10.0 %) | +0.011 `[-0.002,+0.030]` | **HOLD**: inherits 2 px collar |
| `CONC b10px-m20` (1 km, 20 %) | 37,654 | 7,531 (20.0 %) | +0.020 `[-0.006,+0.056]` | **HOLD**: inherits 2 px collar |
| `CONC b50px-m20` (5 km, 20 %) | 37,654 | 7,531 (20.0 %) | +0.006 `[-0.012,+0.028]` | **HOLD**: inherits 2 px collar |
| `MASSm10minus` / `m20minus` / `m10plus` | 33,889 / 30,123 / 41,419 | 10 / 20 / 10 % | +0.004 / +0.001 / −0.010 (audited) | **HOLD**: 2 px collar + ranking is not the parent's |

No exact `(parent, axis, value)` pair and no SHA-256 repeats across the seven. Dedupe is on exact hash and repeated pairs only; rank-correlation and dot-overlap thresholds are **not** gates (brief §6).

**The gate question decides the slot order.** Under the literal reading of hard constraint 4 (`≥3 px` from the catalogue unless `AXIS=PRUNE`), only PRUNE3-class files are eligible — and no controlled edit of R0 can ever qualify, because R0 itself, the 0.2778 incumbent, carries 2,171 dots at `2<d_cat≤3`. CONCENTRATION does not add mass inside the collar (receivers require `d_cat>3`) but it cannot remove the inherited dots without becoming a second axis. That choice is the human's; both branches of the plan are written below.

## Next three slots, in order

1. **PRUNE3 — `h33-h33-2-b2-prune3-20261023-01d57649`** (the only gate-compliant file; MODEL −0.003, both report-only proxies negative). Its information value is the near-catalogue falsification test, not its predicted score.
   - Receipt ≥ +0.01 → the collar-loss mechanism is falsified; prioritise a deeper-collar controlled edit and investigate why the proxies missed it.
   - Receipt ≤ −0.01 → retire deeper pruning; prioritise collar *relaxation*.
   - |Δ| < 0.01 → no evidence; do not combine axes on it.
2. **CONCENTRATION 1 km × 20 % — `…-CONCb10px-m20-20261023-c42cd475`** *only if* the human scopes the literal 3 px gate away from controlled R0 edits; otherwise **skip**. Highest MODEL gain in the inventory (+0.020) and the strongest dose, so one slot resolves the mechanism.
   - Receipt ≥ +0.01 → mechanism confirmed (fixed-count mass relocation pays through the `M` term); spend wk3-4 on dose + fusion.
   - |Δ| < 0.01 → the redundancy credit is sub-noise at 10–20 %; close the axis, do not fuse.
   - Receipt ≤ −0.01 → the cold-tail donors were catching isolated blind faults; close the axis and keep R0's sparse tail.
3. **CONCENTRATION 1 km × 10 % — `…-CONCb10px-m10-20261023-89ffd4f3`** (same conditional) to read the dose slope against slot 2. If slot 2 lands inside ±0.01, swap in `…-CONCb50px-m20-…-fae2a52f` (5 km scale) instead; if slot 2 is ≤ −0.01, drop the axis and give the slot to the proposed COLLAR-RELAX1.

## Risks carried by the CONCENTRATION bet (stated, not hidden)

- The brief's 0.51–0.59 block-CV band is not reproducible from R0 (raw 1 km: 0.618; 5 km-smoothed: 0.482). The variants land at 1.02–1.36 raw. If that band is causal, the predicted sign inverts (IRREGULARITIES item 11).
- The projection is calibrated on two owner-reported CLAIMs and on one unknown quantity — how close R0's hottest traces really are to new-fault truth. At `m_add ≤ 0.15` and donor recall loss `t_rm ≥ 0.02` the projection turns negative (full grid: `registry/concentration_projection.json`).
- The catalogue hide-and-recover PROXY has **no power** here (Δ 0.0000, CI ±0.0001) because R0's 2 px collar already excluded the withheld strands. It is reported, never used as a gate.

## Proposed next axes (not built — one per future session)

1. **COLLAR-RELAX1** (from the PRUNE3 branch): at fixed count, exchange 5 % of R0's lowest exact-marginal-credit far dots for H19-5 support at `1<d_cat≤2 px`. Mechanism: new splays can lie inside 300 m of known traces. Confounder: masked known traces make nearby false positives expensive. Falsifier: receipt ≤ −0.01.
2. **PROX** (km-scale proximity prior): same relocation machinery as CONCENTRATION, but the receiver prior is smoothed *catalogue* density rather than parent density. Mechanism: new faults are step-overs/relays of mapped systems. Confounder: only off-collar pixels can pay. Falsifier: Δ ≤ 0 → new-fault truth is not clustered around mapped systems at km scale.
3. **SPACING bar-matched coverage** (from the PRUNE3 branch): re-space an R0 spine at 4 px, hold count, refill onto supported ground. Mechanism: the 2.83 px credit bar may reward coverage per unit mass over redundant dense tracing. Falsifier: ≤ −0.01 versus the 2 px control.
4. **DUPE** (redundancy shed, same machinery as CONCENTRATION but inside blocks): remove dots within 1 px of another dot, refill in the same block. Falsifier: Δ ≤ 0 at fixed `n` means the metric's redundancy credit is exhausted.
5. **TRACKB** (Phase 2 only): strike-consistent ≥1 km traces as GeoJSON + raster with one evidence paragraph per trace. Not a weekly-slot candidate.

## Weeks to the deadline

- **Week 1 (Oct 23–29):** resolve the gate question, then slot 1 (PRUNE3) and, if scoped, slot 2 (CONC 1 km ×20 %). Never upload both twins of one file.
- **Week 2 (Oct 30–Nov 5):** slot 3 from the conditional above; build at most one proposed axis in a new experiment budget after reconciling all ledgers.
- **Weeks 3–4 (Nov 6–19):** combine at most **two** axes that each have an independent receipt ≥ 0.01; never combine sub-0.01 movements.
- **Weeks 5–6 (Nov 20–Dec 3):** pick the leader plus a fallback, re-validate both locally, finish the AI disclosure, and submit one final file blind (NLR Rules §3.4).
