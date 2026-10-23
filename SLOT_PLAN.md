# SLOT_PLAN — One Entity, 3 Slots/Week, One Blind Final File by 2026-12-03

**Entity budget:** `1` competitor (`buffedlizard55-lab`), `3/3` live uploads left this rolling week (`2026-10-23`), `~18–21` total slots to `2026-12-03` (deadline and counts must be re-confirmed by the human on the competition page; IR-88-28), `TOP_PUBLIC = 0.4413` (`2026-10-22`, human-supplied), **ONE blind final file** judged on private Round 1 (`$50K`) and Round 2 (`$250K`) truth (https://www.drivendata.org/competitions/306/competition-doe-gems/). Parent **`R0 = h33-h33-2-b2`** (`37,654` dots, `0` within `2 px`, `2,171` in `2–3 px`, `0.2778` `CLAIM`, `0` receipts) rebuilt byte-for-byte (`zeros` `c55bafc4…`, `nan` `baeae321…`); gate-clean parent **`R1 = PRUNEp3px`** (`6f7ae705`, `min d_cat 3.162 px`) rebuilt and asserted before every R1 edit. The ledger holds **`26` built candidates** across `MASS` (`3`), `PRUNE` (`4`), `CONCENTRATION` (`4`), `SNAP` (`9`) and **`RELIEF` (`6`: three on `R1`, three on `R0`, built concurrently, IR-88-36)**, all distinct SHA-256 and distinct `(parent, axis, value)`.

## Session Findings (`AXIS = RELIEF`, band 12 `det_elev` area terciles, cuts `-142.8 m` / `+38.6 m`, `N` fixed, every moved dot at `d_cat > 3 px`)

| Arm (parent) | Change | Share basin/piedmont/range after | `SGMC` off-cat `PROXY` (parent) | `12 km` CV (parent) | Pred Δ live `MODEL` |
|---|---|---:|---:|---:|---:|
| `up2t10` (`R1`, `cffb5570`) | `10%` basin+piedmont → range | `17.5/34.7/47.8` | `0.09366` (`0.09608`) | `0.6467` (`0.5700`) | **`-0.002`** |
| `up2t15` (`R1`, `77588346`) | `15%` basin+piedmont → range | `16.0/31.2/52.8` | `0.09252` | `0.6909` | **`-0.004`** |
| `dn2t15` (`R1`, `ea75b7eb`) | `15%` piedmont+range → basin | `35.4/34.2/30.3` | `0.08490` | `0.6432` | **`-0.007`** |
| `range12` (`R0`, `30b15f5e`) | `12%` basin+piedmont → range | `16.5/33.7/49.7` | `0.09314` (`0.09606`) | `0.6517` (`0.5590`) | **`-0.003`** |
| `pied12` (`R0`, `bae3dfc6`) | `12%` basin+range → piedmont | `16.3/53.8/29.9` | `0.08752` | `0.5818` | **`-0.008`** |
| `basin12` (`R0`, `4cd2af90`) | `12%` piedmont+range → basin | `32.5/35.5/32.0` | `0.08664` | `0.6101` | **`-0.010`** |

**Reading.** Two independent builds on two parents agree: the up-section (range-front) direction is the least harmful — the sign the blind-fault relief prior predicts (off-catalogue USGS fault pixels sit `11 / 25 / 64%` in basin / piedmont / range while the catalogue is flat at `30 / 41 / 29%`) — but **every arm loses to its own parent**. The R0 family quantifies why: only `90` un-emitted H19-5 pixels in the whole footprint are `>= 2.8 px` from an R0 dot, so every count-fixed relocation trades a *spaced* dot (`0.11–0.16` TP per dot on SGMC) for a *densified* one `1–2 px` from a survivor (`0.04–0.07` TP); random-donor controls (`0.0884 / 0.0884 / 0.0937`) lose just as much, so this is a structural densification tax, not a ranking artefact, and no tercile is rich enough (range `1.4×` the per-candidate credit of basin/piedmont, `~2.3×` needed) to pay it. **Side finding:** the PRUNE physics field that ranks drops/refills (including `R1`'s `2,171` refills) has AUC `0.47` against SGMC-credited R0 dots — `R1`'s refill *quality* is unproven on a blind control even though its SGMC number held. R0-family MODEL values were pre-registered (`+0.006 / +0.003 / -0.008`) and revised after the proxies; both are in every card.

## Next 3 Slots in Order (Week 1 · `2026-10-23`) & Decision Tree

| Slot | Release ID | Axis / Value | Changed vs parent | `SGMC` `PROXY` | Pred `MODEL` | What the live receipt changes |
|---|---|---|---:|---:|---:|---|
| **1** | `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` | `PRUNE p3px` | `5.77%` | `0.09608` | **`+0.005`** | `>= R0 + 0.01`: promote as `R1`, re-base every later axis on it. `|Δ| < 0.01`: keep it as the gate-clean base anyway (only file with a literal `> 3 px` collar). `<= R0 - 0.01`: the `2–3 px` splays carry truth **and** the physics-field refill is suspect (AUC `0.47`) → `RANKFIELD` first. |
| **2** | `h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4` | `SNAP scarp2px` | `82.03%` | `0.09681` | **`+0.006`** | `>= R1 + 0.01`: `200 m` scarp re-centering is live; fuse with the slot-1 winner. `< +0.01`: close `SNAP` for good (two families, IR-88-31/32). |
| **3** | `h33-h33-2-b2-PRUNEp1px-20261023-0542a27c` | `PRUNE p1px` | `6.76%` | `0.09093` | **`-0.006`** | Brackets `1–2 px` flank toxicity when slots 1–2 are both within noise. **Do not spend a slot on `RELIEF` by default** — six arms on two parents are negative on every instrument. The only defensible exception is a deliberate *label-relief probe* with the gate-clean `up2t10` (`cffb5570`): `>= R1 + 0.01` despite the densification tax ⇒ hidden labels are strongly range-biased → build `SUPPORT` with range as receiver; `<= R1 - 0.01` or `|Δ| < 0.01` ⇒ close relief. |

All other `RELIEF` arms (`up2t15`, `dn2t15`, `range12`, `pied12`, `basin12`) are `HOLD` diagnostics with no distinct learning beyond `up2t10`.

## Weeks 2–6 (`2026-10-30 → 2026-12-03`)
- **Week 2 (slots 4–6):** re-base the receipt-winning axis on the gate-clean parent; run `CONCENTRATION b10px-m10` (`89ffd4f3`, highest `MODEL` in the inventory, `+0.011`) on that parent only if `R1` confirms (it inherits R0's collar otherwise); build and spend one slot on **`SUPPORT`** (below) if slot 1 is non-negative.
- **Weeks 3–4 (slots 7–12):** combine the two best confirmed axes (`Δ RECEIPT >= +0.01` each); start one further proposed axis.
- **Weeks 5–6 (slots 13–18):** confirm the composite twice on live chunks, prepare `TRACKB` for Phase 2, lock **ONE blind final file** plus a `-zeros.tif` fallback and re-validate both with `scripts/validate_variant.py`.

## Proposed Better Axes (mechanism · confounder · falsifier) — not built
1. **`SUPPORT` (spaced new support instead of densification; supersedes the `RELIEF-SPACING` control, which cannot be built from H19-5 at all):** the ancestors `H16-1` / `H19-4` contain `3,577` / `1,472` range-tercile ridge pixels `>= 2.8 px` from every R0 dot and `> 3 px` from the catalogue (SGMC self-credit `0.083–0.087`, equal to R0's own range dots). *Mechanism:* spaced adds earn the full line credit densified adds forfeit, so a `10%` range shift could flip from `-0.003` to positive. *Confounder:* ancestor thresholds were tuned on the same leaderboard lineage (`CLAIM 0.1855 / 0.1894`); their extra pixels may be the detector's noise tail. *Falsifier:* blind SGMC not above the parent for a spaced range-support arm, or live `< parent + 0.01`.
2. **`RANKFIELD` (replace the physics ranking):** rank drops/refills by a field neutral or positive on the blind control (H19-5 component length, or seeded uniform random) and re-emit `PRUNEp3px`. *Confounder:* SGMC bedrock faults may differ in kind from the hidden labels. *Falsifier:* no SGMC gain over `R1` at equal count.
3. **`COVER_DEPTH`** (band 15 `depth_to_base_surf` terciles at fixed count): concealed normal faults under thin cover still perturb potential fields. *Confounder:* the depth model is a smooth tens-of-km interpolation. *Falsifier:* live `|Δ| < 0.01` across all three depth terciles.
4. **`STRIKE_ALIGN`**: snap only dots whose structure-tensor strike agrees with the local H19-5 ridge within `±22°`. *Confounder:* aeolian/pluvial lineaments and GeoDAWN tie-line ripples are strike-coherent too. *Falsifier:* no gain over the identical edit at a random `50%` strike agreement.
5. **`TRACKB` (Phase 2):** strike-consistent `>= 1 km` traces from R0's longest range-tercile H19-5 components with one evidence paragraph each; not a weekly-slot candidate.

**Evidence discipline:** `RECEIPT` (portal) > `CLAIM` > `PROXY` > `MODEL`. Every number above is `PROXY` or `MODEL` except the R0 `CLAIM`; a live change under `0.01` on public chunks is **no evidence**, and public chunks are only a subset of the private truth that decides the prize.
