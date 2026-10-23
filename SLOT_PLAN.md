# SLOT_PLAN — one entity; at most 3 scored files per rolling week, one blind final file

**`2026-10-23` · AXIS = PRUNE (refill mode, not a repeated radius).** All `15` manifest pins verified; R0 rebuilt byte-exactly (zeros `c55bafc4…`, NaN `baeae321…`, `37,654` dots). Ledger: **`35`** built rows, **`0`** portal receipts. The concurrent stop-audit (`evidence/session_20261023_prune_stop.json`, PR #33) settled the *radius* question — `1 px` and `3 px` exist and `2 px` is R0 — and this session did not re-mint any of them (IR-88-46): it varied the **refill mode**, which IR-88-37 recorded as an uncontrolled confounder in every earlier arm.

**Budget/target:** `TOP_PUBLIC` `0.4413` is human-supplied for `2026-10-22` and `UNVERIFIED` here (the stop-audit declined to adopt it). Slots left this rolling week / total: **human must confirm** (`3/3` reported, `~18–21` to the deadline). Deadline `2026-12-03` is **human confirmation pending**. The human checks the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) and [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf); nothing here is scraped. One blind final file; the primary and its `-zeros` twin are alternatives, never two slots.

## Session result — collar purge vs refill, same count, two instruments
| Arm | Edit | `N` | refill min NN | four-line field `MODEL` vs R0 | blind `SGMC` `PROXY` vs R0 |
|---|---|---:|---:|---:|---:|
| `p3norefill` `fb308615` | `300 m` collar, **no refill** | `35,483` | – | `0.270354` (−0.0157) | `0.093643` (−0.0024) |
| `p3space35` `49fff49b` | `300 m` collar, `2,171` refills `>=3.5 px` | `37,654` | `3.6056` | `0.274896` (−0.0112) | `0.101042` (+0.0050) |
| `p4space35` `07bd8182` | `400 m` collar, `3,825` refills `>=3.5 px` | `37,654` | `3.6056` | `0.263231` (−0.0228) | `0.102454` (+0.0064) |
| *densified `300 m` rebuild = `R1`* | constraint-free refill | `37,654` | `1.000` | `0.281537` (−0.0045) | `0.096083` (+0.00002) |

**Reading.** The purge alone loses on **both** instruments, so `R1`'s registered `MODEL +0.005` can only come from the refill. Spacing-locked refills then trade field credit (`−0.011`; `−0.023`) for blind-fault alignment (`+0.005`; `+0.006`) — a genuine instrument disagreement (IR-88-44), so no arm is promoted on agreement, because there is none. The old `p3.7px/p4.3px` decline is *not* reproduced on `SGMC` by a spaced `400 m` refill (`+0.0064` vs `−0.0016`), so part of that decline was a refill artefact. Evidence: `evidence/refill_spacing_comparison.json`.

## Next three slots — conditional sequence, not three automatic uploads
| Order | File / predicted live change (`MODEL`) | What a receipt would change |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705`, `+0.005` vs R0 `CLAIM` | First restore the artifact privately, match its full recorded hash, and re-read/validate both twins. `>= +0.01`: the collar+refill package works → re-base later axes. `\|Δ\| < 0.01`: keep it as the gate-clean base **and** spend slot 2. `<= −0.01`: the purge is the culprit (`p3norefill` agrees) → close the collar family and move to `CONCENTRATION` on a gate-clean parent. |
| 2 | `PRUNEp3space35-49fff49b`, `+0.007` vs R0 `CLAIM` | The only `300 m`, count-fixed, gate-clean file above R0 on the blind fault control, and a direct test of spacing. `>= slot1 + 0.01`: spacing is the mechanism → build `SUPPORT`/`TRACKB` on it. Within `±0.01`: spacing inert, keep `SGMC` as a weak prior only. `<= slot1 − 0.01`: the field `MODEL` was right, densified refill wins. |
| 3 | **Reserve** `PRUNEp4space35-07bd8182` (spacing dose) **or** `PRUNEp3.2px-f272cdae` (collar bracket) | Spend only on receipt-backed direction: `p4space35` after a positive slot 2 (tests whether alignment keeps paying as the collar widens); `p3.2px` after a positive slot 1 (tests the collar optimum). Otherwise preserve the slot. |

`p3norefill` is **diagnostic only** (never a slot). `p4space35` is `HOLD` until a positive `p3space35` receipt. `SNAPscarp2px-fae77ff4` is **`HOLD`** — its inherited `min d_cat` is `2.2361 px` with `2,171` dots inside `3 px`, so it breaks the non-PRUNE `>=3 px` rule despite its `SGMC` `0.096806` (IR-88-46). All `MASS` / `CONCENTRATION` / `RELIEF` / R0-`SNAP` rows stay `HOLD` for the same collar reason; the three PRUNE sweep arms (`p3.7px`, `p4.3px`) are not to be uploaded blind. Every upload awaits human confirmation of quota, exact-file dedupe against actual submission history, and a fresh disk validator receipt. A live difference **under `0.01` is no evidence**; public and private chunks may differ.

## Weeks to the provisional deadline
- **Oct 23–29:** receipts and quota resolved; the conditional three slots above.
- **Oct 30–Nov 5:** re-base the receipt-winning axis on the winning parent; run `CONCENTRATION b10px-m10` (`89ffd4f3`, highest `MODEL` in the inventory) only on a gate-clean parent. Do not mint parallel duplicates.
- **Nov 6–19:** combine two axes only after each has independent `>= 0.01` receipt evidence, naming the actual parent and recording spacing/refill confounding.
- **Nov 20–Dec 3:** confirm the leading file, prepare Phase-2 `TRACKB` for geologist review, choose one blind final plus its fallback, and freshly validate both.

## Proposed better axes (not built this session)
1. **`SUPPORT`** — spaced new support from `H16-1`/`H19-4` (partly built already: the spaced refill borrows exactly this pool). *Mechanism:* spaced dots earn full line credit. *Confounder:* those thresholds were tuned on this lineage (IR-88-45). *Falsifier:* no `SGMC` gain over `R1` at equal count.
2. **`RANKFIELD`** — same spacing lock, but rank refills by a field neutral on the blind control (component length, or seeded random). *Confounder:* `SGMC` bedrock faults may differ from the hidden labels. *Falsifier:* `p3space35` and its random-rank twin within `0.01` live.
3. **`COVER_DEPTH`** — band 15 `depth_to_base_surf` terciles at fixed count. *Confounder:* smooth tens-of-km interpolation. *Falsifier:* `|Δ|<0.01` across all three depth terciles.
4. **`STRIKE_ALIGN`** — move only dots whose structure-tensor strike agrees with the local ridge within `±22°`. *Confounder:* aeolian/pluvial lineaments and tie-line ripples are strike-coherent too. *Falsifier:* no gain over the identical edit at a random `50%` strike agreement.
5. **`TRACKB`** (Phase 2 only) — `>=1 km` strike-consistent traces from R0's longest ridge components, one evidence paragraph each.

**Evidence discipline:** `RECEIPT` (portal) > `CLAIM` > `PROXY` (local holdout / SGMC) > `MODEL`. Everything above except R0's `0.2778` is `PROXY` or `MODEL`; catalogue holdout and `SGMC` stay report-only and never gate promotion.
