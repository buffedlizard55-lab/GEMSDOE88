# SLOT_PLAN — one entity; at most 3 scored files per rolling week, one blind final file

**`2026-10-23` · AXIS = SPACING (3 built, all HOLD) + merged PR #34 PRUNE refill-mode.** All `15` manifest pins verified; R0 rebuilt byte-exactly (zeros `c55bafc4…`, NaN `baeae321…`, `37,654` dots). Ledger: **`38`** built rows (35 + 3 SPACING), **`0`** portal receipts. PR #34 varied the refill *mode* (spacing-locked vs unconstrained, the IR-88-37 confounder) without re-minting any radius (IR-88-46); this session built the only never-built Week-1-eligible axis on gate-clean `R1` (`TRACKB` is Phase 2 only), preregistered (`registry/spacing_preregistration.json`, kept unedited). No `(parent, axis, value)` or SHA-256 collision either way (IR-88-47).

**Budget/target:** `TOP_PUBLIC` `0.4413` is human-supplied for `2026-10-22` and `UNVERIFIED` here (the stop-audit declined to adopt it). Slots left this rolling week / total: **human must confirm** (`3/3` reported, `~18–21` to the deadline). Deadline `2026-12-03` is **human confirmation pending**. The human checks the [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) and [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf); nothing here is scraped. One blind final file; the primary and its `-zeros` twin are alternatives, never two slots.

## Session results — refill spacing (PR #34) and receiver geometry (SPACING)
| Arm | Edit | `N` | refill min NN | four-line field `MODEL` vs R0 | blind `SGMC` `PROXY` vs R0 |
|---|---|---:|---:|---:|---:|
| `p3norefill` `fb308615` | `300 m` collar, **no refill** | `35,483` | – | `0.270354` (−0.0157) | `0.093643` (−0.0024) |
| `p3space35` `49fff49b` | `300 m` collar, `2,171` refills `>=3.5 px` | `37,654` | `3.6056` | `0.274896` (−0.0112) | `0.101042` (+0.0050) |
| `p4space35` `07bd8182` | `400 m` collar, `3,825` refills `>=3.5 px` | `37,654` | `3.6056` | `0.263231` (−0.0228) | `0.102454` (+0.0064) |
| *densified `300 m` rebuild = `R1`* | constraint-free refill | `37,654` | `1.000` | `0.281537` (−0.0045) | `0.096083` (+0.00002) |

| SPACING arm (parent R1) | Receiver geometry | `w`-DTI `MODEL` vs R1 | blind `SGMC` `PROXY` vs R1 |
|---|---|---:|---:|
| `poisson28` `60f65400` | farthest-point (median `2.236 px`) | `−0.0026` | `0.096820` (+0.00074) |
| `strike` `bc8e6d1a` | along-strike `|cos| 1.000` | `−0.0059` | `0.095396` (−0.00069) |
| `lattice4px` `6c7e0b72` | 4 px lattice, phase frozen | `−0.0059` | `0.095292` (−0.00079) |

**Reading.** The purge alone loses on **both** instruments, so `R1`'s registered `MODEL +0.005` can only come from the refill. Spacing-locked refills then trade field credit for blind-fault alignment — a genuine instrument disagreement (their IR-88-44; SPACING reproduces it: `w`-DTI negative on all three arms while `SGMC` ordering matches prereg). Both sessions converge: ancestor-pool spaced refill (`+0.0050`) and H19-5-only maximal spacing (`+0.00074`) both beat densified placement, so **spacing/uniformity is the lever and spaced ancestor support amplifies it** (the `SUPPORT` proposal, partly executed by PR #34). The old `p3.7px/p4.3px` decline is *not* reproduced on `SGMC` by a spaced `400 m` refill, so part of that decline was a refill artefact. Evidence: `evidence/refill_spacing_comparison.json`, `evidence/spacing_axis_report.json`.

## Next three slots — conditional sequence, not three automatic uploads
| Order | File / predicted live change (`MODEL`) | What a receipt would change |
|---|---|---|
| 1 | `PRUNEp3px-6f7ae705`, `+0.005` vs R0 `CLAIM` | First restore the artifact privately, match its full recorded hash, and re-read/validate both twins. `>= +0.01`: the collar+refill package works → re-base later axes. `\|Δ\| < 0.01`: keep it as the gate-clean base **and** spend slot 2. `<= −0.01`: the purge is the culprit (`p3norefill` agrees) → close the collar family and move to `CONCENTRATION` on a gate-clean parent. |
| 2 | `PRUNEp3space35-49fff49b`, `+0.007` vs R0 `CLAIM` | Largest blind-control gain at `300 m` count-fixed gate-clean (`+0.0050`; `poisson28` is also above R0 but at one-seventh the magnitude — slot 2 is on effect size, IR-88-47). `>= slot1 + 0.01`: spacing is the mechanism → build `SUPPORT`/`TRACKB` on it. Within `±0.01`: spacing inert, keep `SGMC` as a weak prior only. `<= slot1 − 0.01`: the field `MODEL` was right, densified refill wins. |
| 3 | **Reserve** `PRUNEp4space35-07bd8182` (spacing dose) **or** `PRUNEp3.2px-f272cdae` (collar bracket) | Spend only on receipt-backed direction: `p4space35` after a positive slot 2 (tests whether alignment keeps paying as the collar widens); `p3.2px` after a positive slot 1 (tests the collar optimum). Otherwise preserve the slot. |

`p3norefill` is **diagnostic only** (never a slot). `p4space35` is `HOLD` until a positive `p3space35` receipt. All three SPACING arms are `HOLD` (sub-threshold diagnostics; `poisson28` is the declustered-parent candidate). `SNAPscarp2px-fae77ff4` is **`HOLD`** (inherited `min d_cat 2.2361 px`, non-PRUNE `>=3 px` rule). All `MASS` / `CONCENTRATION` / `RELIEF` / R0-`SNAP` rows stay `HOLD` for the same collar reason. Every upload awaits human confirmation of quota, exact-file dedupe against actual submission history, and a fresh disk validator receipt. A live difference **under `0.01` is no evidence**; public and private chunks may differ.

## Weeks to the provisional deadline
- **Oct 23–29:** receipts and quota resolved; the conditional three slots above.
- **Oct 30–Nov 5:** re-base the receipt-winning axis on the winning parent; run `CONCENTRATION b10px-m10` (`89ffd4f3`, highest `MODEL` in the inventory) only on a gate-clean parent. Do not mint parallel duplicates.
- **Nov 6–19:** combine two axes only after each has independent `>= 0.01` receipt evidence, naming the actual parent and recording spacing/refill confounding.
- **Nov 20–Dec 3:** confirm leading file, prepare Phase-2 `TRACKB` for geologist review, choose one blind final plus its fallback, and freshly validate both.

## Proposed better axes (not built this session)
1. **`SUPPORT`** — spaced new support from `H16-1`/`H19-4` (partly built already: the spaced refill borrows exactly this pool). *Mechanism:* spaced dots earn full line credit. *Confounder:* those thresholds were tuned on this lineage (their IR-88-45). *Falsifier:* no `SGMC` gain over `R1` at equal count. (SPACING prior: place `SUPPORT` receivers by farthest-point uniformity — `poisson28` beat lattice and along-strike pairwise.)
2. **`RANKFIELD`** — same spacing lock, but rank refills by a field neutral on the blind control (component length, or seeded random). *Confounder:* `SGMC` bedrock faults may differ from the hidden labels. *Falsifier:* `p3space35` and its random-rank twin within `0.01` live.
3. **`COVER_DEPTH`** — band 15 `depth_to_base_surf` terciles at fixed count. *Confounder:* smooth tens-of-km interpolation. *Falsifier:* `|Δ|<0.01` across all three depth terciles.
4. **`STRIKE_ALIGN`** — move only dots whose structure-tensor strike agrees with the local ridge within `±22°`. *Confounder:* aeolian/pluvial lineaments and tie-line ripples are strike-coherent too. *Falsifier:* no gain over the identical edit at a random `50%` strike agreement. (SPACING note: pure along-strike receiver geometry lost to uniformity here, so any revival needs a live receipt.)
5. **`TRACKB`** (Phase 2 only) — `>=1 km` strike-consistent traces from R0's longest ridge components, one evidence paragraph each.

**Evidence discipline:** `RECEIPT` (portal) > `CLAIM` > `PROXY` (local holdout / SGMC) > `MODEL`. Everything above except R0's `0.2778` is `PROXY` or `MODEL`; catalogue holdout and `SGMC` stay report-only and never gate promotion.
