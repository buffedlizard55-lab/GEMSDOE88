# SLOT_PLAN — One Entity, 3 Slots/Week, One Blind Final File by 2026-12-03

**Budget:** `1` entity · `3/3` live uploads left this rolling week (`2026-10-23`, human must reconfirm) · `~18–21` slots to `2026-12-03` (human must reconfirm, IR-88-28) · **ONE blind final file** for Round 1 ($50K) and Round 2 ($250K) · `TOP_PUBLIC = 0.4413` (`2026-10-22`, human-supplied, `UNVERIFIED` here) · **`0` receipts in `ledger/submissions.csv`**.
**Parent** `R0 = h33-h33-2-b2` (`37,654` dots, `0` at `<=2 px`, `2,171` at `2–3 px`, `0.2778` `CLAIM`, rebuilt byte-exact `c55bafc4…`/`baeae321…`). **Gate-clean parent** `R1 = PRUNEp3px` (`6f7ae705`, `min d_cat 3.1623 px`, `N` fixed).

## Session `2026-10-23` — `AXIS = PRUNE`, spacing-locked (non-densifying) refill
Agent-chosen: every non-PRUNE child of R0 inherits the `2,171`-dot collar and breaks the literal `>=3 px` rule; and every existing PRUNE arm refills with no spacing constraint (`min NN 1.0 px`, IR-88-37), so *collar* and *refill* were confounded. These three arms separate them (`scripts/build_prune_spaced_variants.py`, prereg `registry/prune_spaced_preregistration.json`).

| Arm | Edit | `N` | CvR min NN | Four-line field `MODEL` vs R0 | Blind `SGMC` `PROXY` vs R0 |
|---|---|---:|---:|---:|---:|
| `p3norefill` `fb308615` | cut `2,171` collar dots, **no refill** | `35,483` | `2.83` | `0.270354` (**−0.0157**) | `0.093643` (**−0.0024**) |
| `p3space35` `49fff49b` | cut `2,171`, refill `2,171` at `>=3.5 px` | `37,654` | `3.61` | `0.274896` (**−0.0112**) | `0.101042` (**+0.0050**) |
| `p4space35` `07bd8182` | cut `3,825` (`10.16%`), refill `3,825` at `>=3.5 px` | `37,654` | `3.61` | `0.263231` (**−0.0228**) | `0.102454` (**+0.0064**) |
| *densified `300 m` rebuild = `R1`* | cut `2,171`, constrained-free refill | `37,654` | `1.00` | `0.281537` (−0.0045) | `0.096083` (+0.00002) |
| *densified `400 m` rebuild = `p4px`* | cut `3,825`, constraint-free refill | `37,654` | `1.00` | `0.273708` (−0.0124) | `0.094465` (−0.0016) |

**What this teaches.** (1) The collar purge alone is negative on **both** instruments → `R1`'s MODEL `+0.005` can only be the refill, not the removal. (2) Locking the refill's spacing buys blind-fault alignment (`SGMC` `+0.005…+0.006`) and costs label-free field credit (`−0.011…−0.023`): **the two instruments disagree**, so neither arm may be promoted without a receipt (IR-88-44). (3) The `p3.7px/p4.3px` decline in the old sweep is not reproduced by a spaced refill at `400 m` on `SGMC` (`+0.0064` vs `−0.0016`), so that decline was partly a refill artefact. Evidence: `evidence/refill_spacing_comparison.json`.

## Next 3 Slots (in order) and what each receipt changes
| Slot | File | Why this file | Receipt decision rule |
|---|---|---|---|
| **1** | `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` (`R1`) | Only file that is gate-clean, count-fixed and already the base of the RELIEF/SNAP families | `>= R0+0.01` → promote as `R1`, re-base later axes. `|Δ|<0.01` → keep as gate-clean base **and** spend slot 2 on `p3space35`. `<= R0−0.01` → the purge is the culprit (`p3norefill` says so) → close the collar family, go to `CONCENTRATION` on `R0`. |
| **2** | `h33-h33-2-b2-PRUNEp3space35-20261023-49fff49b` | Highest blind `SGMC` of any `300 m` file and the only arm that tests spacing directly | `>= R1+0.01` → spacing is the mechanism, build `SUPPORT`/`TRACKB` on it. Within `±0.01` of `R1` → spacing is inert, retire it, keep `SGMC` as a weak prior only. `<= R1−0.01` → the field MODEL was right, densified refill wins. |
| **3** | `h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4` (or `PRUNEp3.2px` `f272cdae` if slot 1 was ≥ `+0.01`) | `SNAPscarp2px` is the only other file above R0 on the blind control (`0.096806`); `p3.2px` brackets the collar upward | `SNAPscarp >= R1+0.01` → fuse scarp re-centring with the winning collar. Otherwise `SNAP` closes for good (two families, IR-88-31/32). |

`p4space35` is `HOLD`: 4th in line, only after a **positive** `p3space35` receipt (it is the spacing dose, not a fresh question). Nothing else in the 35-row ledger may be uploaded blind; `MASS`/`CONCENTRATION`/`RELIEF`/`SNAP` on `R0` inherit the collar and stay `HOLD`.

## Weeks to the deadline
- **Wk 2 (slots 4–6):** re-base the winning axis on the receipt-winning parent; run `CONCENTRATION b10px-m10` (`89ffd4f3`, highest MODEL in the inventory, `+0.011`) only on a gate-clean parent.
- **Wk 3–4 (slots 7–12):** combine the two axes with `Δ RECEIPT >= +0.01` each; pre-register one new axis (`SUPPORT` or `RANKFIELD`).
- **Wk 5–6 (slots 13–18):** confirm the composite twice, prepare `TRACKB` for Phase 2, lock ONE final file plus its `-zeros.tif` fallback and re-validate both.

## Proposed better axes (not built this session)
1. **`SUPPORT`** — spaced new support from `H16-1`/`H19-4` (now partly built: the spaced refill borrows this pool). *Mechanism:* spaced dots earn full line credit. *Confounder:* ancestor thresholds were tuned on this same lineage. *Falsifier:* no `SGMC` gain over `R1` at equal count.
2. **`RANKFIELD`** — replace the four-line ranking with a field neutral on the blind control (component length or seeded random) under the same spacing lock. *Confounder:* `SGMC` bedrock faults may differ from hidden labels. *Falsifier:* `p3space35` vs its random-rank twin within `0.01` live.
3. **`COVER_DEPTH`** — band 15 `depth_to_base_surf` terciles at fixed count. *Confounder:* smooth tens-of-km interpolation. *Falsifier:* `|Δ|<0.01` across all three terciles.
4. **`STRIKE_ALIGN`** — move only dots whose structure-tensor strike agrees with the local ridge within `±22°`. *Confounder:* aeolian/pluvial lineaments and tie-line ripples are strike-coherent too. *Falsifier:* no gain over the same edit at random `50%` agreement.
5. **`TRACKB`** (Phase 2 only) — `>=1 km` strike-consistent traces from R0's longest ridge components, one evidence paragraph each.

**Evidence discipline:** `RECEIPT` > `CLAIM` > `PROXY` > `MODEL`. Everything above except R0's `0.2778` (`CLAIM`) is `PROXY`/`MODEL`; a live change under `0.01` on public chunks is **no evidence**.
