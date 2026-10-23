# SLOT PLAN — GEMS Prize (DrivenData #306)

> **Deadline:** 2026-12-03 (confirm on the competition page). **Quota:** 3 scored submissions / rolling week, 1 final blind pick. **Week claimed:** 2026-10-23. **Slots left this week:** 3/3 (0 scored uploads recorded). **Total to deadline:** ~21.
> **Evidence labels:** RECEIPT | CLAIM | PROXY | MODEL. A live change under 0.01 is no evidence.

## This session — AXIS = CONCENTRATION (next unbuilt axis in the default plan)

The brief left the axis blank for this session; MASS was already built last session (3 variants, still unsubmitted), so the next axis in the default wk1-2 order was taken. Parent **R0 = `h33-h33-2-b2`**, 37,654 dots, sha `c55bafc4…`, CLAIM 0.2778. Pins verified; R0's 37,654-pixel mask reproduced exactly (byte sha is not reproducible under this GDAL build — see IR-88-17).

**Design:** block = 10 px (1 km); prior = parent dot density smoothed over 2 blocks, normalised by in-footprint area; donors = coldest blocks first, most isolated first, **one dot left in every donor block** so the axis is not a disguised prune; receivers = allowed pixels (≥3 px from catalogue) welded ≤1.41 px to a *surviving* host dot in the hottest blocks, ≤2 per host; count fixed at 37,654; collar dots inherited untouched. No RNG.

| ID | Value | n | % moved | CV_occ (raw 1 km) | CV (5 km-smoothed) | Gini | PROXY Δ | Predicted Δ (MODEL) |
|---|---|---|---|---|---|---|---|---|
| `…-CONCb10px-m10-…-89ffd4f3` | 1 km × 10 % | 37,654 | 10.00 | 0.618 → 1.021 | 0.482 → 0.670 | 0.33 → 0.41 | +0.0000 | **+0.011** (−0.002…+0.030) |
| `…-CONCb10px-m20-…-c42cd475` | 1 km × 20 % | 37,654 | 20.00 | 0.618 → 1.257 | 0.482 → 0.791 | 0.33 → 0.46 | +0.0000 | **+0.020** (−0.006…+0.056) |
| `…-CONCb50px-m20-…-fae2a52f` | 5 km × 20 % | 37,654 | 20.00 | 0.703 → 1.359 | 0.903 → 1.065 | 0.39 → 0.60 | +0.0000 | **+0.006** (−0.012…+0.028) |

**Mechanism in one line:** with `n` fixed, `DTI = T/(0.2T + 0.2(n−M) + 0.8|G|)`, so a dot welded next to an already-covering dot costs `0.2(1−k) ≈ 0.07` while a dot in an empty km block costs the full `0.2`; the move is a bet that the parent's hottest traces are near new-fault truth (`m_add`), and it loses if the cold-tail donors were catching isolated blind faults (`t_rm`). Model calibration and the full scenario grid: `registry/concentration_projection.json`. The PROXY instrument has no power here (Δ = 0.0000, CI ±0.0001) because R0's 2 px collar already excluded the withheld strands — reported, never a gate (`registry/concentration_proxy.json`).

**CV warning:** the brief's 0.51–0.59 band is not reproducible from R0 under four block sizes × two estimators (R0 sits at 0.62 raw / 0.48 smoothed). These variants land at 1.02–1.36 raw. If that band is causal rather than an artefact, the predicted sign inverts — that is the cleanest test in the set.

## Next 3 slots, in order

1. **`…-CONCb10px-m20-…-c42cd475`** (20 %, 1 km). Largest predicted gain and the strongest dose, so it is the fastest way to learn whether the mechanism is real. *Result changes what:* Δ ≥ +0.01 → mechanism confirmed, spend wk3-4 on dose + fusion; Δ in (−0.01, +0.01) → the redundancy credit is sub-noise at this dose, close the axis; Δ ≤ −0.01 → recall loss from donors dominates, close the axis and keep R0's sparse tail.
2. **`…-CONCb10px-m10-…-89ffd4f3`** (10 %, 1 km). The slope, not the level: read it *with* slot 1 (m20 − m10 ≈ axis elasticity). Also the safest file in the set (smallest change, 90 % of R0's dots intact).
3. **`…-MASSm10minus-…-7132935e`** (33,889 dots, −10 %). An independent axis already built: does the parent pay for mass it does not need? Predicted −0.008 MODEL, and the 20 % dose is the falsifier. Only use if the CONCENTRATION pair is uninformative and a mass reading is still missing.

*If slot 1 lands within ±0.01:* swap slot 2 for `…-CONCb50px-m20-…-fae2a52f`, which asks whether the prior works at a scale where it is smooth; if slot 1 is ≤ −0.01, drop CONCENTRATION entirely and give the slot to PRUNE (2 px → 3 px collar, 2,171 dots, refill to count).

## Weeks to deadline (~7 weeks, 21 slots, one final blind file)

- **Wk1-2 (now → 11-05):** 3 CONCENTRATION doses (above), PRUNE 2→3 px, SNAP ≤2 px to the strongest edge response (needs a verified TMI/gravity gradient band the human supplies), RELIEF terciles. One build per (axis, value); check the ledger first.
- **Wk3-4:** fuse the best two axes at identical mass (e.g. best MASS + best CONCENTRATION), pre-registered before upload; hold 1–50 % change.
- **Wk5-6:** confirm the leader on the PROXY only as a sanity check, pick the final file plus a fallback, re-validate both formats, finish `AI_USE.md`, submit one blind file per Rules §3.4.

## Axis proposals for later sessions (not built — for review)

- **PROX (km-scale proximity prior).** Same relocation machinery, but the receiver prior is the smoothed *catalogue* density rather than parent density. Mechanism: new faults are step-overs/relays of mapped systems ([Faulds inventory](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/); organiser thread 11516). Confounder: the catalogue is masked at scoring, so the gain must come from *off-collar* pixels only. Falsifier: live Δ ≤ 0 means new-fault truth is not clustered around mapped systems at km scale — a useful negative for Phase 2.
- **DUPE (dot redundancy shed).** Remove dots that sit ≤1 px from another dot and refill in the same block. Mechanism: identical to this axis but applied inside blocks, and it is measurable without labels. Falsifier: if Δ ≤ 0 at fixed `n`, the metric's redundancy credit is exhausted and further concentration work is pointless.
- **TRACKB (Phase 2 only).** Strike-consistent ≥1 km traces from R0's top-ranked dots as GeoJSON + raster, with one evidence paragraph per trace. Not a weekly-slot candidate.
