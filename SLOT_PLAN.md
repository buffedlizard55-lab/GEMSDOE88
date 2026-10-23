# SLOT_PLAN — One Entity, 3 Slots/Week, One Blind Final File by 2026-12-03

**Entity budget:** `1` competitor (`buffedlizard55-lab`), `3/3` live uploads left this rolling week (human-confirmed `2026-10-23`; re-check before uploading), `~18–21` total slots to `2026-12-03` (deadline not portal-verified; IR-88-28), `TOP_PUBLIC = 0.4413` (`2026-10-22`, human-supplied), **ONE blind final file** (https://www.drivendata.org/competitions/306/competition-doe-gems/). **Ledger now `23` BUILT rows** (`MASS 3`, `CONCENTRATION 4`, `PRUNE 4`, `SNAP 9`, `RELIEF 3`), all distinct SHA-256, **zero RECEIPTs**: `R0 0.2778` remains `CLAIM`. Every delta below is `MODEL` (prediction) or `PROXY` (local instrument), never a score; `|live delta| < 0.01` is no evidence.

## Session Finding (`AXIS = RELIEF` on Gate-Clean `R1 = PRUNEp3px`, 12% Dose, `N = 37,654`)

Preregistered in `registry/relief_preregistration.json` before any variant PROXY was computed; parent `R1` rebuilt byte-exact (`6f7ae705…`/`dc6f090d…`) from the byte-exact `R0`. Terciles are footprint quantiles of **Band 12 `det_elev`** (`T1 basin <= -142.8 m`, `T2 piedmont`, `T3 range > +38.6 m`); Band 19/local-relief basin terciles hold `<1.1%` of parent dots and only `279–450` refill candidates, so a 10–15% shift on them is infeasible without a new detector (IR-88-34). Each arm moves exactly `4,518 (12.00%)` dots, donors lowest exact-marginal-loss and receivers highest exact-marginal-gain under the parent's own field `w`, all `d_cat > 3 px`, count fixed.

| Arm (sha8) | Shares basin/piedmont/range | Prereg `MODEL` vs `R1` | `w`-DTI `MODEL` Δ | SGMC `PROXY` (Δ vs `R1 0.09608`) | 12 km CV | Verdict |
|---|---|---:|---:|---:|---:|---|
| `rng2bas12` (`56093882`) | `32.4/41.7/25.8` | `+0.008` | `-0.0070` | `0.08502 (-0.0111)` | `0.605` | HOLD-conditional |
| `rng2pmt12` (`52717cf5`) | `20.4/53.7/25.8` | `+0.002` | `-0.0050` | `0.08581 (-0.0103)` | `0.584` | HOLD-conditional bracket |
| `bas2rng12` (`f4c6dc18`) | `8.4/41.7/49.8` | `-0.010` | `-0.0112` | `0.09390 (-0.0022)` | `0.672` | HOLD reverse bracket |

- **Why all three lose locally — kernel saturation, measured not assumed (IR-88-35):** `99.6–99.9%` of receivers land `<=2.8 px` from a survivor (median `1.41 px`; basin H19-5 within-3 px support coverage `82.6% -> 82.9%` for `+4,518` dots), while `~62%` of donor sites end `>3 px` from the nearest survivor (range coverage `87.8% -> 80.3%`). Marginal returns are per unit of *uncovered strand length*, not per unit area, so the preregistered area-density ratio (basin `2.41` vs range `1.24`) is the wrong state variable for interstitial H19-5 receivers. A live loss on `rng2bas12` therefore cannot cleanly falsify the basin hypothesis; a gain `>= +0.01` despite saturation would be strong support. Holdout-DTI is degenerate `0.0` for every `>3 px` file (IR-88-20); SGMC/holdout/`w`-DTI stay REPORT ONLY.
- **RELIEF does not displace the slot order.** Its remaining live value is *information* (purchasing the relief direction), not expected score.

## Next 3 Slots in Order & Decision Tree

| Slot | Release ID | Pred Δ (`MODEL`) | What the RECEIPT changes |
|---|---|---:|---|
| **1** | `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` (`PRUNE <=3 px`, `5.77%` chg vs R0) | `+0.005` vs R0 | **If `>= R0+0.01`:** R1 is the parent for all composites. **If `<= R0-0.01`:** 2–3 px splays carry net truth; revert to R0-line parents and re-scope every R1 descendant (RELIEF/SNAP) as confounded. |
| **2** | `h33-h33-2-b2-SNAPscarp2px-20261023-fae77ff4` (`SNAP <=2 px`, spacing-locked; `82.03%` chg; inherits R0's `2,171` 2–3 px dots — human must accept the Brief §4.4 tension) | `+0.006` vs R0 | **If `>= parent+0.01`:** spacing-locked scarp snap is real — next build is spacing-locked SNAP on whichever parent Slot 1 crowns. **If `< +0.01`:** SNAP closes (agrees with the R1 SNAP family, IR-88-31). |
| **3 (conditional)** | Slot 1 inconclusive → `PRUNEp1px-20261023-0542a27c` (brackets the collar). Slot 1 decisive **and** human wants the relief direction closed → `…-RELIEFrng2bas12-20261023-56093882` as an information purchase (prereg `+0.008` vs R1; local instruments predict the opposite). Otherwise bank the slot. | `-0.006` / `+0.008` | `rng2bas12 >= R1+0.01` revives basinward allocation and licenses `RELIEF-UNCOVERED` (below); `<= R1-0.01` closes relief reallocation from interstitial pools for good. |

## Weeks 2–6 (`2026-10-30 -> 2026-12-03`) & Proposed Axes (propose here, do not build this session)

- **Week 2:** act on Slot 1–3 receipts only. Re-base the strongest surviving single-axis winner; rebuild `CONCENTRATION` on a `>3 px`-clean parent if Slot 1 crowns R1 (its R0 arms carry the collar).
- **Weeks 3–4 — combine only axes with `RECEIPT >= +0.01`. Proposed orthogonal axes, in priority order:**
  1. **`RELIEF-UNCOVERED` (new, from IR-88-35):** per-tercile spacing-preserved re-thinning of H19-5 (tercile-specific `dot_thin` radii) so receivers occupy *uncovered* strand length (`>3 px` from survivors) instead of interstitial pixels. *Mechanism:* removes the saturation confound that dominates this session's arms. *Confounder:* mixes SPACING with RELIEF — must be built as its own (axis, value) with matched spacing in the untouched tercile. *Falsifier:* uncovered-receiver fraction still `<10%` of adds, or live `< parent+0.01` with coverage now controlled.
  2. **`DIP_OFFSET_ASYM`:** updip ($60^\circ$) back-projection of hanging-wall gravity/basement gradients by $\Delta x = z_{\text{base}}\cot 60^\circ$ (`100–600 m`) toward the footwall scarp (Faulds & Hinz 2015, https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11072.pdf). *Confounder:* basalt caprock margins, Lahontan shorelines. *Falsifier:* `< +0.01` over the snapped/un-snapped parent it edits.
  3. **`RELAY_TIP_STRESS`:** anisotropic tip aperture (`1.5 px` along terminal strike, `3.2 px` flank-normal) replacing the isotropic collar at fault tips/step-overs (Pollard & Segall 1987, https://doi.org/10.1016/B978-0-12-066266-1.50009-0). *Confounder:* E-W GeoDAWN tie-line artefacts crossing tips. *Falsifier:* `< +0.01` over the isotropic-collar parent.
- **Weeks 5–6:** confirm the best composite once, build `TRACKB` (`>=1 km` strike-consistent GeoJSON + raster for Phase 2 expert review), lock **ONE blind final file + `-zeros` fallback**, re-validate both formats from disk, stop building.
