# SLOT_PLAN — One Entity, 3 Slots/Week, One Blind Final File by 2026-12-03

**Entity budget:** `1` competitor (`buffedlizard55-lab`), `<= 3` live uploads/rolling week, **6 weeks left (`2026-10-23 -> 2026-12-03`, max `18` public slots)**, **ONE blind final file** scored on Round 1 (`$50K`) private chunks and re-scored in Round 2 (`$250K`) against expert-expanded labels (https://www.drivendata.org/competitions/306/competition-doe-gems/).
**Parent `R0 = h33-h33-2-b2`:** `37,654` dots, `0` within `2 px` of the catalogue, `2,171` in the `2–3 px` collar, `0.2778` `CLAIM` (no receipt). Pinned `c55bafc4...`; the dot mask re-derives exactly in this sandbox, the GeoTIFF container bytes do not (`IRREGULARITIES.md` IR-88-22).

## Session `2026-10-23b` — AXIS = SNAP: built, PROXY-negative, `HOLD`

No AXIS was assigned by the human (IR-88-21/23); SNAP is the last unbuilt axis of the brief's default order, so it was built. Three variants of `R0`, each differing **only** in how far and onto which edge field a dot may move. Count held at `37,654`; every destination required `d_cat > 3 px`.

| Release (`releases/…`) | Rule | Moved | Mean disp. | Edge pct | Collar left | SGMC `PROXY` | Δ SGMC vs `R0` | Pred. live `MODEL` |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `…-SNAPw2E1-20261023-01cf9e98` | `<=2 px` to max `\|∇rtp\|+\|∇igrav\|`, `σ=1 px` | `35,771` (95.0%) | `1.82 px` | `0.564→0.655` | `644` | `0.08810` | **`-0.00796`** | `-0.002` |
| `…-SNAPw2S2-20261023-60ced8c7` | `<=2 px`, `σ=2 px` edge, gain `>=0.25 z` | `19,617` (52.1%) | `1.90 px` | `0.565→0.629` | `1,565` | `0.09211` | **`-0.00396`** | `-0.001` |
| `…-SNAPw2E2-20261023-861cd355` | `<=2 px` on organizer bands 3/9/18 | `35,725` (94.9%) | `1.81 px` | `0.568→0.658` | `579` | `0.08811` | **`-0.00795`** | `-0.002` |

`R0` reference: SGMC `0.09606`, collar `2,171`, `12 km` CV `0.5590`. All three sit inside the reported `0.51–0.59` CV band (`0.5575–0.5582`) and pass every MUST-pass gate (`scripts/validate_variant.py` PASS on primary and zeros files).

**What it teaches (PROXY, never a score):**
1. Edge capture is real but weak: mean edge percentile rises ~`+0.07–0.09`, yet blind off-catalogue SGMC DTI **falls** in every arm — the ~200 dots lost from within `300 m` of a blind USGS fault cost more than the percentile gain buys.
2. Half the loss is pixel noise: the `σ=2 px`, gain-gated arm moves half as many dots and loses half as much.
3. Operator choice is irrelevant (`w2E1` vs `w2E2` differ by `0.00002`): the effect is *displacement off the parent's ridge geometry*, not which derivative band is used.
4. Useful side effect: a SNAP pass clears `70–73%` of the `2–3 px` collar at constant count.

**Decision:** all three `HOLD`; predicted change `-0.002 … -0.001` is far below the `0.01` evidence bar. Do not spend a slot unless the human wants the axis retired with a live receipt.

## Next 3 slots

| Slot | File | Why | What the result changes |
|---|---|---|---|
| **1** | `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` (`6f7ae705…`) | Only candidate already satisfying the literal `>=3 px` collar (`min d_cat 3.162 px`) at constant count; best blind SGMC of the PRUNE sweep (`0.09608`). | `>= R0 + 0.01` promotes it to `R1` and every later axis inherits a gate-clean parent; `< R0` retires the 300 m side-lobe argument. |
| **2** | `CONCENTRATION b10px-m20` **re-based on** `PRUNEp3px` | Existing `c42cd475` inherits `R0`'s collar and is `HOLD`; re-based it is gate-clean and carries the largest positive projection (`MODEL +0.020`). | Positive → concentration becomes the fusion partner for the final file; flat → the `0.51–0.59` CV band is descriptive, not causal. |
| **3** | best of slots 1–2, re-validated (or `RELIEF` on `R1`) | Reserve/confirm slot. | Locks the blind final candidate and its fallback. |

## Weeks 2–6
`CONCENTRATION` on `R1` (slots 4–6) → one structural axis from the list below per week (7–12), keeping an axis only if `Δ RECEIPT >= +0.01` → weeks 5–6 fuse the winners, re-validate format on both final and fallback, and lock the single blind file.

## Proposed better axes (mechanism · confounder · falsifier) — not built
1. **`SNAP_COHERENCE`** — move a dot `<=2 px` only along the local edge **normal** and only when it sits on the edge flank, preserving along-strike position. *Mechanism:* flight-line drape blurs only the across-strike offset. *Confounder:* fan-surface contacts parallel to range fronts. *Falsifier:* `<= +0.01` live vs `R0`.
2. **`CV_MATCHED_WELD`** — combine the `PRUNEp3px` collar with a density re-weld so `12 km` CV lands in `0.51–0.59` and the collar stays clean. *Mechanism:* tests whether the CV band is causal rather than a by-product of mass. *Confounder:* CV was read off 37–44k-dot files, so mass and CV stay partly confounded. *Falsifier:* no live gain at matched mass.
3. **`TRACKB`** (Phase 2 only) — strike-consistent `>=1 km` traces from `R0`'s top dots as GeoJSON + raster with one evidence paragraph each; not a weekly-slot candidate.
