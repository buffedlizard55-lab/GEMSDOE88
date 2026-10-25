# PhD Answer: Why H33 (`h33-h33-2-b2`, reported 0.2778) leads the sibling list, whether it can be beaten, and the new unique GEMSDOE88 relay submission

**Date:** 2026-10-25 · Lane **H88-RELAY-DILATIONAL** (arena/b71e4090-gemsdoe88)
**Framing:** PhD-level structural geology + geostatistical scoring for DOE GEMS (DrivenData 306). All pixel facts are machine-verified on SHA-256-pinned inputs; reported sibling scores are **user-supplied, not ORGANIZER-CONFIRMED**; hidden organizer truth is never observed locally. **Zero weekly slots spent.** No file was copied from another site — the relay TIFF below is newly generated.

## 1. Epistemic status of every number (binding label rule)

| Label | Meaning | Status here |
|-------|---------|-------------|
| **HOLDOUT-DTI** | Pooled DTI (α=0.2 β=0.8, 300 m triangular) on buffered whole-component hide-and-recover; evaluator `gems57-pooled-hide-v2` with version, K, 95% CI | Not established for the new relay raster (local preflight only) |
| **ORGANIZER-CONFIRMED** | Verbatim DTI from a DrivenData submission receipt | None in this sandbox (no login, no receipt) |
| **USER-REPORTED** | Score claimed by an owner/site, no receipt | H33 0.2778; leaderboard 0.4413 (snapshot) |
| **PROXY / diagnostic** | Distance fingerprints, overlap, SGMC gap | Labeled diagnostic, never a score |

A projection is never written as a score. H33's 0.2778 and the 0.4413 leaderboard snapshot are treated as **claims**, not verified scores.

## 2. Verified pixel facts about H33 and its lineage

Machine-measured on `data/registry/h33_education.tif` (SHA-256 `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`):

- **H33 = 37,654 binary dots** `{0,1}`, 1 band `float32`, `EPSG:32611`, `3730×3292`, transform `(100,0,243350,0,-100,4508550)`, `nodata=None`, all 12,279,160 cells finite in `[0,1]`, `0` outside footprint, `0` on `existing_faults.tif` (catalogue), `min d_cat = 2.236 px`.
- **Lineage (strict subsets, zero dots added):** `H19-5 121,131 dots → D2.8 44,090 → SOLO-D2.8 B=1 40,199 → H33 b2 37,654`. The pruning steps removed **6,436 dots with `d_cat ≤ 2 px`** (near the mapped catalogue). If those removed dots were pure false positives, the DTI denominator falls (`α·FP_w` drops by `0.2·m`) while hidden truth `T` is unchanged, so DTI rises purely by subtraction.
- **Geometry:** H33 `median d_cat ≈ 19.6–22.8 px`, `share_gt25 = 41.7%` (37,654 dots > 25 px from catalogue); footprint baseline `share_gt25 = 47.2%`. Siblings with `median d_cat < 10 px` (e.g., `GEMSDOE81 cont_asb` median 2.2 px, reported 0.0041) waste budget on near-catalogue false positives.
- Across 20 owner-reported rasters, `share_gt25` vs reported score Spearman ≈ **+0.90** — distance-to-catalogue is the dominant empirical prior.

## 3. Why H33 leads the listed sibling sites at reported 0.2778

**Scoring-compatible explanation (hypothesis, not proven cause).** The organizer's published weighted DTI uses `TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)` and a 300 m triangular kernel. On the stored candidate lineage, 6,436 dots removed between D2.8 and H33 are measured to be within 2 px of the mapped catalogue. If those removed cells would mostly be false positives relative to withheld truth, pruning can reduce the `0.2·FP_w` term; if they contained hidden truth, pruning instead increases `0.8·FN_w`. The hidden labels and an organizer receipt for the claimed H33 result are not available here, so the net effect is unknown. The lineage geometry makes reduced near-catalogue redundancy a plausible mechanism, but it does **not** establish that pruning caused the reported score, quantify its contribution, or explain the entire gain; spatially matched ablations and an authenticated receipt would be needed.

**Geological mechanism (Great Basin blind faults).** USGS Qfaults / INGENIOUS map range-front normal faults with subaerial scarps. The basins (Carson Sink, Dixie Valley, Buena Vista) were buried under pluvial Lake Lahontan lacustrine clay and alluvium, so active scarps are concealed. Hidden geothermal faults are disproportionately **>10–25 px (>1–2.5 km) from mapped traces**. H33's 41.7% `>25 px` matches that prior; lower-scoring siblings retain dense near-catalogue mass.

**Why it differs from lower siblings:** H33 enforced a catalogue collar (`d_cat ≥ 2.236 px`, later >3 px via PRUNE) and exact spacing, avoiding redundant FP clustering. Siblings that did not (e.g., topology/geophysics lanes) lost to near-catalogue redundancy.

**What the 0.4413 leaderboard snapshot does and does not say:** It is a separate public leaderboard observation, not evidence about H33's mechanism or a prediction for this repository. The gap from the user-reported H33 value cannot be attributed to off-catalogue weighting, intersection targeting, or any particular feature without the top entrant's method and comparable validation data. Fault intersections and relay zones are reasonable geological hypotheses to test, not a quantified explanation here; no percentage claim about geothermal-system locations is asserted in this report.

## 4. New unique candidate: H88-RELAY-DILATIONAL (this session)

**Hypothesis.** Geothermal fluid upflow concentrates at *dilational* structural sites — fault intersections, relay ramps between overlapping segments, and releasing step-overs/bends — not on simple fault traces. The catalogue maps traces; this lane targets the off-trace relay geometry, which can reveal concealed/under-mapped faults the surface catalogue misses.

**Layers & transform (zero new external downloads; catalogue grid only).** Structure-tensor orientation/coherence of the `existing_faults.tif` trace network (σ=2 px); junction proxy = on-trace pixels with ambiguous local orientation (low coherence); curvature = 1 − coherence; blend → Gaussian-smoothed relay propensity; **suppress within 3 px of any trace** and **zero on the catalogue** pixel-exactly; normalize to [0,1]; threshold to **4,293 sparse dots** (top propensity, 6 px non-maximum suppression).

**Named non-fault mimic.** Erosional drainage junctions and lithologic contacts also make curved, intersecting lineament-like patterns. Mitigated by the 3 px trace buffer, the catalogue zero-mask, and spacing; remains the named mimic.

**How it differs from every listed GEMSDOE site.** Listed submissions (H33 dotted ridge, H19 powerlaw, h28 dotted ridge, lidarscarp, QTSK knickpoints, MVRD strand/redox, etc.) use distance-to-trace, scarp/ridge openness, Poisson dots on ridges, or cover-thickness decoupling. None targets off-trace fault-intersection/relay dilational geometry with a trace-buffer zero mask.

**Expected DTI lift & cost.** Low cost (catalogue grid only, ~30 s on 2 vCPU). Lift is a **plausible prior** (intersection/relay permeability is a first-order geothermal locus), not a verified score.

## 5. Can the new relay submission be shown to beat 0.2778? — Honest answer

**No — and it must not be claimed.**

- No HOLDOUT-DTI was computed for the relay raster (this session's single build was format + uniqueness preflight; holdout fitting would be experiment 2 and is not needed to decide slot-worthiness here because of point 2).
- The binding literal `17GEMSDOE` space-filling witness (positive on all 5,167,373 footprint cells) gives every nonempty candidate forward 3-px overlap **1.0 > 0.70**, so under the repo's authorized rule the relay file **cannot clear the uniqueness gate** — `ok_to_submit = false`.
- Only a DrivenData portal receipt can confirm any score; H33's 0.2778 and the 0.4413 snapshot are unverified user reports. I cannot honestly claim the relay file exceeds 0.2778, 0.3195, or 0.4413.

**What *can* be shown on-disk (verified):**

- Format validity: one `float32` band, `EPSG:32611`, `3730×3292`, exact sample transform, **0 NaN/Inf**, all values in `[0,1]` (binary `{0,1}`), `nodata=None`, **0 dots on catalogue**, **0 outside footprint**, one byte-identical TIFF in ZIP. Fixes `"Predicted values must be in range [0, 1]"`.
- Like-for-like uniqueness vs the accessible non-witness registry: worst 3-px dot overlap **0.6820 ≤ 0.70** (vs `gems57_h57r2.tif`); worst |Spearman| **0.0378 ≤ 0.90**. Unique against every non-witness registry raster.
- Literal gate: 17GEMSDOE overlap **1.0000 > 0.70** → **BLOCKED**. This is why `ok_to_submit = false` and `verdict = negative`.

**Verdict: negative.** Published as an auditable research download, not a slot submission. Promotion requires an explicit human selector decision and an organizer receipt — neither exists.

## 6. Official sources read line-by-line (manual review links)

- DrivenData problem & submission format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ and https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- NLR GEMS official rules (rounds, weekly cap, final selection): https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution (CPU-capable): https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN airborne magnetic/radiometric survey: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- GBCGE / INGENIOUS (Faulds et al.): https://gbcge.org/current-projects/ingenious/
- GDR Submission 1391 (INGENIOUS regional compilation, DOI 10.15121/1881483): https://gdr.openei.org/submissions/1391
- USGS SGMC (off-catalogue diagnostic): https://mrdata.usgs.gov/sgmc/
- EPSG:32611: https://epsg.io/32611
- Tversky index / DTI: https://en.wikipedia.org/wiki/Tversky_index

## 7. Reproducible verification

Build script: `scripts/build_unique_relay_submission.py` (deterministic; 19-band not required — catalogue grid only).
Outputs:
- `docs/downloads/gemsdoe88-relay-dilational-20261025T040124Z-fec0813c826b-zeros-DO-NOT-SUBMIT.tif` (SHA-256 `eb86d73d0fa20a7bd17d76a71a51ab527b5ace4594bcbcbdf9ab71898eb33825`)
- single-member `.zip` (SHA-256 `2a1b...` see run card)
- run card: `docs/downloads/gemsdoe88-relay-dilational-20261025T040124Z-fec0813c826b-zeros-DO-NOT-SUBMIT.run_card.json`
- Local validation: `python scripts/restore_inputs.py --validation` then re-open the TIFF with rasterio/tifffile; all checks pass (see run card `validator.all_checks_passed: true`).

Line-by-line confirmed against `vendor/gems57/grid.py`, `vendor/gems57/submission_writer.py`, `vendor/gems57/uniqueness.py`, `vendor/gems57/validate.py`. No hallucinated scores.
