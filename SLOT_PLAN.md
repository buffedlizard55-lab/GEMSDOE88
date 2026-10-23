# SLOT_PLAN — Single Entity · 3 Slots/Week · One Blind Final File by `2026-12-03`

**Entity:** `buffedlizard55-lab` (1 competitor, `<= 3` live uploads per rolling week, **ONE** blind final file scored on both Phases — https://www.drivendata.org/competitions/306/competition-doe-gems/). **Deadline:** `2026-12-03` → **6 weeks / up to 18 public slots** from `2026-10-23`.
**Unfilled by the human (still blank, do not invent):** `TOP_PUBLIC` + date, `receipt_score` for `R0` (`0.2778` is a `CLAIM`), slots used this rolling week.

## Where the evidence actually stands

| Fact | Value | Label |
| :--- | :--- | :--- |
| `R0 = h33-h33-2-b2` live score | `0.2778` | **CLAIM** (no receipt) |
| `R0` rebuilt from pinned lineage on `2026-10-23` | byte-identical, `37,654` dots | verified |
| `R0` dots inside `2 < d_cat <= 3 px` | `2,171` | verified (IR-88-14) |
| `R1 = PRUNEp3px` (collar cut at constant count) | `min d_cat = 3.162 px`, `MODEL +0.005` | BUILT |
| SNAP on `R1` (this session, 3 variants) | blind `SGMC` `0.09198 / 0.09246 / 0.09505` vs `R1` `0.09608` | **PROXY** → negative (IR-88-24) |

Two readings of the ledger matter for the plan. First, the whole climb `0.1922 -> 0.2477 -> 0.2600 -> 0.2708 -> 0.2778` is one lineage edited five times, so the remaining headroom is inside that lineage, not in a new detector. Second, every lane that swapped the field for a single physical signal scored `0.00-0.19`; the dots are the asset.

## The next three slots, in order

**Slot 1 — `R1 = h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705`** (`releases/…-6f7ae705.tif`, note `h33-2-b2; PRUNE <=3px held at 37654 (-2171 in 2-3px, +2171 exact marginal gain >3px); pred +0.005 MODEL`).
*Question:* is the 300 m collar real, or was the `0.2600 -> 0.2708 -> 0.2778` climb just mass reduction?
*What each outcome changes:* `>= R0 + 0.01` → the collar is confirmed and `R1` becomes the parent for every later axis. Within `+/- 0.01` → inconclusive (public-chunk noise), keep `R0` as the reference and stop spending slots on collar radius. `<= R0 - 0.01` → the collar thesis is dead; the `2-3 px` dots were carrying truth and the remaining plan shifts entirely to `CONCENTRATION`.
*Why first:* it is the only built file that satisfies Brief §4.4 with no exemption, and every later non-PRUNE axis needs a compliant parent anyway.

**Slot 2 — `CONCENTRATION` on `R1`** (`b10px` = 1 km blocks, `m10`; **not built yet** — the existing `CONC*` files are `R0`-based and `HOLD`).
*Question:* does moving 10% of the mass from the coldest to the hottest 1 km block actually buy the `MODEL +0.011` that the `R0`-based projection claims, once `R1` has removed the collar confound?
*What each outcome changes:* `>= +0.01` → concentration is real; fuse it with `R1` for the final file and spend slot 3 on the `m20` bracket. `|delta| < 0.01` → the block-density story is a null; the final file should stay a collar-corrected `R1` and effort moves to Phase-2 traces.
*Guardrail:* report block-density CV before/after; the best historical files sit at `0.51-0.59`, and the `R0`-based `m10` build overshot to `1.02`.

**Slot 3 — confirm or fuse.** If slots 1 and 2 both clear `+0.01`, upload `R1 + CONCENTRATION m10` (one change further along the same lineage) as the confirm step. If only one clears, re-upload the better one only if the human wants a noise estimate — otherwise **bank the slot** and hold it for the final file. Do not spend it on `SNAP`: its blind control is negative.

## Weeks 2-6 (after the three slots above)

- **Weeks 2-3:** build and test `RELIEF` (basin / piedmont / range-front terciles from the detrended-elevation bands, count fixed) and `TRACKB` traces. `RELIEF` is the last untested axis with a mechanism that predicts a *positive* sign; `TRACKB` is the Phase-2 deliverable that the expanded expert labels reward but is not a weekly-slot candidate.
- **Weeks 4-5:** fuse only axes with a `RECEIPT >= +0.01`. Any axis under `0.01` live is no evidence on public chunks — do not stack nulls and call it a model.
- **Week 6 (by `2026-12-03`):** choose **one** blind final file and one fallback, re-validate the format of both against `sample_submission.tif`, and freeze. The final file must be the one with the best *mechanism* as well as the best number, because Phase 2 rescores against expert-expanded labels that no public chunk reveals.

## Proposed better axes (mechanism · confounder · falsifier — not built this session)

1. **`KERNEL_MATCH`** — re-weight dot spacing to the 3 px triangular kernel so neighbouring dots stop cannibalising the same truth credit (`M` saturates per dot while `T` saturates per truth cell). *Confounder:* none geological; this is a pure metric-geometry effect and therefore the cleanest remaining test. *Falsifier:* no gain at fixed count after the top-10% redundant dots are dropped and re-spent.
2. **`TERMINATION_FAN`** — concentrate mass at fault tips and step-overs, where new faults are most likely to be mapped first (Faulds et al. on relay ramps). *Confounder:* fan-apron and shoreline edges mimic tip splays. *Falsifier:* `< +0.01` live over isotropic dots at the same count.
3. **`LIDAR_GATED_DENSIFY`** — allow only LiDAR-covered sub-areas to take extra dots, since the 1 m scarps localise better than 400 m aeromagnetics. *Confounder:* LiDAR coverage correlates with basin-floor infrastructure. *Falsifier:* gain vanishes when matched on block density.
