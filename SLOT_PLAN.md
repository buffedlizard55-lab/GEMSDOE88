# SLOT_PLAN — One Entity, 3 Slots/Week, One Blind Final File by 2026-12-03

**Entity budget:** `1` competitor (`buffedlizard55-lab`), `3/3` live uploads left this rolling week (`2026-10-23`), `~18-21` total slots to `2026-12-03`, `TOP_PUBLIC = 0.4413` (`2026-10-22`, human-supplied), and **ONE blind final file** judged on private Round 1 (`$50K`) & Round 2 (`$250K`) truth (https://www.drivendata.org/competitions/306/competition-doe-gems/). Parent **`R0 = h33-h33-2-b2`** (`37,654` dots, `0` within `2 px`, `2,171` in `2-3 px`, `0.2778` `CLAIM`) rebuilt byte-for-byte (`zeros` `c55bafc4...`, `nan` `baeae321...`); gate-clean parent **`R1 = H33-2-b2-PRUNEp3px`** (`6f7ae705`, `min d_cat 3.162 px`) rebuilt and asserted before every `RELIEF` edit.

## This Session (`AXIS = RELIEF`, parent `R1`, `N = 37,654`, band 12 `det_elev` terciles)

Terciles are equal-area thirds of the footprint (`det_elev` thresholds `-142.832`, `38.588`): **basin** (lowest), **piedmont**, **range front**. Donors are removed by *exact marginal DTI cost*, receivers added by *exact marginal DTI gain* on unused ridge-support cells inside the target tercile, every receiver at `d_cat > 3 px`.

| Arm | Change | Tercile share basin/piedmont/front | `SGMC` off-cat `PROXY` (parent `0.09608`) | exp. DTI under `w` | `12 km` CV (parent `0.5700`) | Pred `MODEL` vs `R1` |
|---|---|---:|---:|---:|---:|---:|
| `up2t10` (`cffb5570`) | `10.00%` up-section | `17.5/34.7/47.8` | `0.09366` (`-0.0024`) | `-0.0025` | `0.6467` | **`-0.002`** |
| `up2t15` (`77588346`) | `15.00%` up-section | `16.0/31.2/52.8` | `0.09252` (`-0.0036`) | `-0.0069` | `0.6909` | **`-0.004`** |
| `dn2t15` (`ea75b7eb`) | `15.00%` down-section (control) | `35.4/34.2/30.3` | `0.08490` (`-0.0112`) | `-0.0073` | `0.6432` | **`-0.007`** |

**Reading.** Three independent report-only instruments agree that the *up-section* direction is less harmful than the down-section one (`up2t15` beats `dn2t15` by `+0.0076` `SGMC`), which is the sign the blind-fault relief prior predicts (off-catalogue USGS fault pixels are `5.6x` denser per pixel in the range-front tercile than in the basin tercile, while the competition catalogue is flat across terciles at `30.4/40.6/29.0%`). But **every arm loses to its own parent**: `3,579` of `5,648` `up2t15` receivers land within `2 px` of a surviving dot and the `12 km` block CV rises `0.570 -> 0.691`. The parent already saturates the well-evidenced range front, so at fixed count the reallocation buys near-duplicate coverage. `RELIEF` is therefore **a measured negative axis, not a slot candidate**, and no live slot should be spent on it while `R1` and `SNAPscarp2px` receipts are missing.

## Next 3 Slots in Order (`2026-10-23`) & Decision Tree

| Slot | Release ID | Axis / Value | Changed vs parent | `SGMC` `PROXY` | Pred `MODEL` | What the live receipt changes |
|---|---|---|---:|---:|---:|---|
| **1** | `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` | `PRUNE` `p3px` | `5.77%` | `0.09608` | **`+0.005`** | **`>= R0 + 0.01`:** promote as `R1`, make it the base for every later axis. **`|delta| < 0.01`:** keep it as the gate-clean base anyway (it is the only file with a literal `> 3 px` collar). |
| **2** | `h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4` | `SNAP` `scarp2px` | `82.03%` | `0.09681` | **`+0.006`** | **`>= R1 + 0.01`:** geometry is live after all; fuse with `R1`. **`<= R1 - 0.01`:** close `SNAP` (IR-88-31 already retired it on `R1`-based arms). |
| **3** | `h33-h33-2-b2-PRUNEp1px-20261023-0542a27c` | `PRUNE` `p1px` | `6.76%` | `0.09093` | **`-0.006`** | Brackets `1-2 px` flank toxicity if Slots 1-2 are both within noise. **Do not** use Slot 3 on `RELIEF`: it is predicted negative on three instruments and would only retire the axis. |

## Weeks 2-6 (`2026-10-30 -> 2026-12-03`)

- **Week 2 (Slots 4-6):** re-base `CONCENTRATION` (`b10px-m10`, `b10px-m20`) on the receipt-winning gate-clean parent; keep count fixed and the `> 3 px` collar strict. `CONCENTRATION` remains the highest `MODEL` in the inventory (`+0.011/+0.020`) but has never been gate-clean.
- **Weeks 3-4 (Slots 7-12):** combine the two confirmed winners (`RECEIPT delta >= +0.01`), then spend one slot on the best proposed axis below.
- **Weeks 5-6 (Slots 13-18):** confirm the composite on live chunks, prepare `TRACKB` (`>= 1 km` strike-consistent GeoJSON + raster, one evidence paragraph per trace) for Phase 2, lock **ONE blind final file** plus a `-zeros.tif` fallback, and re-validate both formats.

## Proposed Axes (mechanism / confounder / falsifier) — not built this session

1. **`RELIEF-SPACING`** (the missing control for this session): the same tercile transfer with receivers forced `>= 2.8 px` apart and `>= 2.8 px` from survivors, accepting lower-corroboration cells to buy *new* coverage. *Mechanism:* distinguishes "range front is saturated" (current result) from "the up-move was wasted on duplicates". *Confounder:* off-ridge cells score `p_phys ~ 0.7-1.0` but carry no ridge support. *Falsifier:* no live gain over `R1` while `up2t15` also gains nothing.
2. **`COVER_DEPTH`** (`depth_to_base_surf`, band 15): reweight mass by basement-depth terciles at fixed count. *Mechanism:* concealed normal faults under thin cover still perturb potential fields; deep basins suppress the signal. *Confounder:* the depth-to-basement model is itself a smooth regional interpolation with tens-of-km resolution. *Falsifier:* live `|delta| < 0.01` across all three depth terciles.
3. **`STRIKE_ALIGN`**: snap only the dots whose local structure-tensor strike agrees with the local `H19-5` ridge within `+/- 22 deg`, leaving cross-strike dots alone. *Mechanism:* separates along-strike smearing (real faults) from across-strike gradient drift (hanging-wall offset, IR-88-32). *Confounder:* aeolian/pluvial lineaments and GeoDAWN tie-line ripples are also strike-coherent. *Falsifier:* no gain when compared with the identical edit at a random `50%` strike agreement.

**Evidence discipline:** `RECEIPT` (portal) > `CLAIM` > `PROXY` > `MODEL`. Every number above is `PROXY` or `MODEL` except the R0 `CLAIM`. A live change under `0.01` on public chunks is **no evidence**; public chunks are a subset of the private truth that decides the prize.
