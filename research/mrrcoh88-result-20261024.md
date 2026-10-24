# MRR-COH-88 result — 2026-10-24

> **DOWNLOAD FOR RESEARCH: YES · OK TO SUBMIT: NO · DO NOT SUBMIT.**
>
> The new GeoTIFF passes saved-byte format and expanded-registry uniqueness checks. It fails the binding scientific gate: HOLDOUT-DTI `0.07700055` does not exceed the same-split stored best `0.18788764`. No slot was used and no organizer receipt exists.

## Evidence classification

| Quantity | Evidence class | Value |
|---|---|---:|
| MRR-COH-88 pooled score | **HOLDOUT-DTI**, `gems57-pooled-hide-v2`, 22,893 withheld positives | `0.07700055`, 95% CI `[0.06912859, 0.08486633]` |
| Same-split stored best | **HOLDOUT-DTI**, same evaluator and withheld-positive count | `0.18788764`, 95% CI `[0.17169765, 0.20326012]` |
| H33 historical value | **OWNER-REPORTED**; no receipt stored here | `0.2778` |
| MRR-COH model projection | None used as a score or gate | — |
| MRR-COH portal result | **ORGANIZER-CONFIRMED** | none |

A local holdout estimate, an owner report, and an organizer receipt are not interchangeable.

## Preregistered hypothesis and transform

The ranking and method contract were frozen in [`registry/preregistration_mrrcoh88.json`](../registry/preregistration_mrrcoh88.json) and [`candidate-hypotheses-20261024-mrrcoh.md`](candidate-hypotheses-20261024-mrrcoh.md) before feature construction or scoring.

**Hypothesis.** A narrow, strike-persistent demagnetized damage corridor can remain beneath volcanic or alluvial cover after its surface scarp is buried or erased, and therefore be absent from the surface-trace catalogue.

**Exact supplied layers.** Bands 1 `mag_anom`, 2 `rtp`, 3 `tmi_hg`, 9 `tmi_vg`, 14 `tmi`, and 15 `depth_to_base_surf` from the hash-pinned 19-band competition stack.

**Signature.** Remove the broad local 10 km affine relation `tmi_vg ~ 1 + tmi + mag_anom`; derive residual amplitude/trough/depth/cross-gradient channels; add 200–600 m axial coherence, fine/coarse orientation persistence, coherent trough strength, and a high-horizontal-gradient suppression term.

**Named non-fault mimics.** Linear Tertiary dikes, reversely magnetized basalt-flow margins, and aeromagnetic flight-line leveling seams.

**Novelty relative to accessible work.** Prior MRR-BPR used residual amplitude, trough, depth, and cross-gradient but not residual orientation persistence. STR-88 and fabric-dislocation work used orientations on raw fields. The selected lane uses exactly eight catalogue-blind magnetic channels and strict spatial OOF prediction.

## Leakage and holdout protocol

- Two seeds (`20`, `21`) and four quadrants yield eight folds.
- Whole connected fault components are withheld with a 3-pixel context buffer and 12-pixel boundary exclusion.
- The eight image channels do not read the fault catalogue.
- Training labels come only from visible faults in the other spatial quadrants.
- Visible fault pixels are masked exactly in scoring; production also requires catalogue clearance strictly greater than 3 pixels.
- Every feature was tested alone on the Seed-20 hidden-component task. All `8/8` pass; maximum symmetric ROC AUC is `0.54056272`, well below the leakage stop `0.90`.
- Pooled DTI uses `α=0.2`, `β=0.8`, a 300 m triangular kernel, 20 km block bootstrap, and 1,000 draws.
- Fold HOLDOUT-DTI spans approximately `0.05798`–`0.10161`.

No post-result tuning or second MRR-COH experiment was run.

## Artifact and independent validation

- TIFF: `docs/downloads/gems88-mrrcoh-persistent-demag-oof-20261024-43173dots-5fe6cdd8982f-DO-NOT-SUBMIT.tif`
- TIFF SHA-256: `98d8ecc539af4d1743b480c9fe1fc9165488076ba61fa82be4ee9fa2ccea0e24`
- ZIP SHA-256: `37959f896f95511a66241b0fe0a34c854bed203426be021bcd4624f0b7c02d7e`
- Positive pixels: `43,173`
- Format: one float32 band, finite everywhere, range `[0,1]`, no nodata sentinel, exact pinned CRS/shape/transform, zero outside footprint
- ZIP: exactly one member whose bytes equal the standalone TIFF

The runner used the shared writer. `scripts/validate_current.py` independently reopens both saved files, validates sample-grid parity, rehashes all 224 registry paths, and recomputes every final saved-byte registry comparison. No visual inspection or human input is a validation dependency.

## Two-phase uniqueness result

The expanded accessible index contains 224 SHA-pinned path entries from restored registry, fleet, sibling, and local published outputs. Private, unlinked, inaccessible, and later-created rasters remain outside scope.

| Gate | Limit | Result |
|---|---:|---:|
| Pre-placement max `|Spearman ρ|` | `0.90` | `0.18358174` |
| Final max `|Spearman ρ|` | `0.90` | `0.01695859` |
| Final literal forward overlap among dot fields, within 3 px | `0.70` | `0.45873578` |
| Final max chance-corrected excess overlap | `0.70` | `0.13015695` |
| Identical file or decoded prediction | none | none |

The all-representation literal maximum is `1.0`. This is retained in evidence because a positive-everywhere continuous prior covers every possible candidate dot. It is constant and cannot diagnose copied dot placement. Under the shared representation-aware policy, literal overlap binds for dot fields, chance-corrected excess overlap binds for discriminating dense support, and rank correlation binds for every raster. The current artifact is unique under that disclosed policy.

## Why H33 may have reached owner-reported 0.2778

The conclusion is mechanistic and forensic, not organizer-confirmed:

1. **Kernel de-redundancy.** In the owner-reported lineage, thinning roughly 121,000 ridge pixels to 44,090 changes typical nearest-neighbour spacing from about 1 pixel to 3 pixels while median distance to the catalogue stays near 15 pixels. The associated claims rise from about `0.1922` to `0.2600`.
2. **Move away from mapped traces.** The next thinning step retains 37,654 H33 pixels, raises median catalogue distance from `15.0` to `19.7` pixels, and drops the share within 3 pixels of mapped faults from `19.5%` to `5.8%`. The reported value rises from `0.2600` to `0.2778`.
3. **Metric compatibility.** At 100 m pixels, 3-pixel spacing reduces redundant use of the 300 m triangular kernel. Removing emitted mass with little hidden-fault credit reduces weighted false-positive mass in the Tversky denominator (`α=0.2`, `β=0.8`).
4. **Descriptive association.** Across 13 restored claim-linked rasters, Spearman correlation between median catalogue distance and claimed score is `0.891`. The sample is small and lineage selection/live-feedback confounding is severe; this does not identify a causal effect.
5. **Non-comparability.** H33 was built from the full catalogue and scores about `0.004` on the hide-and-recover instrument by construction. Its local holdout behavior cannot validate or refute the owner-reported live value.

Thus strict thinning, kernel spacing, and removal of near-catalogue/low-yield mass plausibly explain the report. Missing recipe ablations and the missing portal receipt prevent causal or ORGANIZER-CONFIRMED conclusions.

## Can this candidate likely beat H33?

**No.** MRR-COH-88's holdout point estimate (`0.0770`) and 95% upper bound (`0.0849`) are both far below the comparable local incumbent (`0.1879`). Nothing in this experiment supports extrapolation above the unverified H33 report (`0.2778`). This is a negative candidate conclusion, not proof that H33 itself had that score and not proof that every future hypothesis must fail.

## Provenance and limitations

- Competition inputs are exact SHA-pinned bytes restored from owner-hosted GitHub mirrors. They were not authenticated through an organizer login, and redistribution terms remain unresolved.
- The selected lane required no new external data. Unselected ranks 4–5 name free official USGS 3DEP and GeoDAWN sources, but exact AOI/calibration bytes were unavailable under the run's host restrictions; they were explicitly not treated as implementation-ready.
- Catalogue hide-and-recover labels are a proxy for undisclosed organizer truth. Real unmapped faults can appear as local false positives.
- Eight folds do not span every geologic domain shift.
- The accessible registry cannot include unknown private submissions.
- No upload, slot consumption, or organizer acceptance occurred.

## Decision and next work

Preserve MRR-COH-88 as a unique, reproducible negative research artifact. Do not tune it after the preregistered result and do not upload it. If another experiment is authorized, RTP-GRAV-ADMITTANCE-88 is the next ranked unrun hypothesis, but it requires a fresh frozen lane and the same canary, buffered-component holdout, two-phase uniqueness, saved-byte format, and separate-selector gates.

Canonical machine result: [`registry/mrrcoh88_run_card.json`](../registry/mrrcoh88_run_card.json).

## Three-pass review record

1. **Implement/verify:** complete — preregistration, features, leakage canaries, eight-fold holdout, strict-quadrant production, TIFF/ZIP writer, format audit, and 224-raster uniqueness audit.
2. **Review/fix:** complete — replaced stale KTH/MAG-PSG public status, made the current validator MRR-COH-aware, aligned the public ranking to the frozen preregistration, separated selector approval from scientific promotion, and added independent 224-row remeasurement.
3. **Requirement recheck/fix:** complete — restored-input and sibling pins passed; `298` tests passed (`22` data-conditional skips); current TIFF/ZIP plus all 224 final registry comparisons were independently recomputed; site/readiness checks passed; both current and historical `--require-submit` gates exited `2` as expected.
