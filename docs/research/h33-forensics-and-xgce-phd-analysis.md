# Evidence-bounded review: reported H33 score 0.2778 and archived H88-XGCE

**Review date:** 2026-10-25
**Decision:** H88-XGCE is **OK TO DOWNLOAD FOR RESEARCH: YES** as an archived artifact; **OK TO SUBMIT: NO — DO NOT SUBMIT**. This review did not generate a raster, run an experiment, compute candidate HOLDOUT-DTI, use a slot, or independently validate TIFF geospatial metadata.

## Executive finding

H33 `0.2778` is an **owner-reported value**, not an organizer-confirmed score in this checkout; no submission receipt was located or verified. XGCE has no candidate HOLDOUT-DTI value or CI, so there is no evidence that it beats H33. The XGCE run card records literal dense-witness overlap `1.0 > 0.70`, which fails the binding duplicate rule. Code review also found that the purported `|ρ|=0.0092` is calculated from the emitted binary raster after placement, not the required pre-placement continuous surface. The raw-feature AUCs use catalogue positives against random negatives rather than spatially blocked withheld components; the masked emission surface uses full-catalogue distance. Its canary status is therefore **NOT VALIDATED / NOT PASSED**.

This is a review of repository evidence, not a geological interpretation of hidden faults or a live competition standings check.

## Three review passes

1. **Evidence/provenance:** separated owner-reported H33 and leaderboard values from locally recorded artifacts; identified the absent receipt and the fact that the incoming XGCE sidecar's raster checks were not rerun here.
2. **Methods/protocol:** inspected the XGCE builder and run card; confirmed no candidate holdout score, an invalid proxy-canary design, a post-placement rather than pre-placement Spearman calculation, and the recorded literal duplicate stop.
3. **Decision/presentation:** changed the public wording and metadata to distinguish research download from submission approval; removed unsupported projection/canary/uniqueness claims and made the fail-closed decision prominent.

## What is known, and how it is labeled

| Evidence label | Meaning here | Evidence / limit |
|---|---|---|
| **ORGANIZER-CONFIRMED** | Value copied from a competition receipt. | None found for H33 or XGCE in this checkout. |
| **OWNER-REPORTED** | User/repository-reported competition score, not independently confirmed here. | H33 `0.2778`; current leaderboard claims were not checked live. |
| **HOLDOUT-DTI** | Local pooled hide-and-recover result under a named evaluator, with withheld positives and CI. | See DHTC and other lane run cards for their own candidate results. They are not XGCE results or organizer scores. |
| **UNSCORED** | Candidate result not computed or lacking required evidence. | XGCE `overall=null`, `ci95=null`; no candidate HOLDOUT-DTI. |
| **PROXY / diagnostic** | A descriptive statistic or invalid shortcut, not a holdout or competition score. | Catalogue distance, sparse-registry overlap, raw catalogue-vs-random AUCs, and any expected-DTI projection. |
| **Projection** | An estimate without measured outcome. | The preregistered XGCE gain projection is withdrawn; do not quote it as a forecast or score. |

The local evaluator/metric definitions are in `vendor/gems57/metric.py`, `vendor/gems57/holdout.py`, and `vendor/gems57/evaluate_holdout.py`. This review did not rerun those evaluators.

## H33: what can and cannot be inferred

### Recorded raster history

`evidence/protocol_review_43d08c7a.json`, `registry/holdout_result.json`, and associated run cards preserve prior project measurements of the H33 raster and lineage. They report a sparse/binary raster with a catalogue-distance distribution different from denser sibling rasters. Those are historical repository measurements; raw `data/` and scientific dependencies were unavailable in this review, so the rasters were not re-opened or remeasured here.

### Plausible statistical mechanisms — not causal findings

The repository's DTI implementation weights false-negative and false-positive mass differently (`vendor/gems57/metric.py`). Reducing redundant predictions near visible faults could affect the false-positive term, while removing predictions that would have matched hidden truth could hurt recall. Raster geometry alone cannot determine which occurred for H33. The reported score change has no receipt or paired score decomposition here, so its cause is unknown.

Possible explanations such as sparsity, spacing, catalogue distance, or a different spatial prior are hypotheses only. The recorded association between catalogue distance and reported scores is vulnerable to shared lineage, selection effects, small sample size, and dependence among submissions. It does not establish that off-catalogue distance predicts hidden-truth correctness.

The geological idea that some targets may be concealed beneath cover is likewise a hypothesis. No local fault truth, burial depth, or geothermal relevance was independently established for XGCE in this review.

## XGCE: method and blockers

The archived builder lists gravity and magnetic gradient bands, basement-depth high-pass, dilation/shear modulation, and a catalogue-distance mask. This is a proposed feature recipe, not validation that these layers are currently available, correctly named, correctly scaled, or geologically diagnostic. Local data files are absent from this checkout.

### Holdout and leakage

- The run card has no candidate HOLDOUT-DTI or CI. Its `reference_catalogue_positive_pixels_overall` is not an XGCE withheld-positive count.
- The builder's raw feature diagnostic samples catalogue positives and random footprint negatives. It is not a spatially blocked, whole-segment holdout.
- The emitted `surface_norm` is masked using full-catalogue distance. That feature is not derived from fold-visible faults only; the builder excludes it from the raw-feature summary. Thus no valid all-feature leakage clearance exists.
- The current builder now records holdout as **NOT COMPUTED**, refuses to call a proxy a score, and checks the shared dense-witness certificate before feature loading or placement. The builder was not run in this review.

### Uniqueness and rank-correlation

- The recorded literal dense-witness forward overlap is `1.0`, exceeding the `0.70` limit. The binding decision is **FAIL-CLOSED / DUPLICATE — STOP**. Do not bypass this by changing filenames, masking, or substituting an overlap definition.
- The run card's sparse-inventory 3-px overlap `0.2037` is a recorded historical comparison only; it does not override the literal blocker.
- Code inspection shows the reported `|ρ|=0.0092` is computed using `spearmanr(emitted[footprint], prior[footprint])` after placement. It is not a pre-placement rank correlation of the continuous surface. That value is withdrawn as evidence for the required pre-placement check. The corrected run card marks that check absent and withholds uniqueness clearance.

### Artifact integrity versus raster validation

The archived TIFF SHA-256 and ZIP SHA-256 are recorded in `registry/xgce88_run_card.json` and the sidecar. In this review, both hashes were checked, ZIP integrity passed, and the ZIP's only TIFF member was byte-identical to the standalone TIFF. The sidecar contains historical local format/range metadata, but no rasterio/geospatial validation was rerun here. These byte checks do not prove grid alignment, range compliance, scientific validity, uniqueness, or organizer acceptance.

## Decision and remaining work

**H88-XGCE: download for research only; DO NOT SUBMIT.** No slot was spent. Do not claim it beats H33 or the leaderboard. A future lane must first resolve the binding literal duplicate stop under the actual competition protocol; until then, no placement or new experiment is authorized by this analysis. If the protocol is clarified, use the shared cached feature stack/evaluator/writer, build catalogue features from visible faults only, withhold whole segments with the prescribed buffer, run each feature alone in blocked folds, compute pre-placement surface-rank correlation, then check final dots against the full registry. Stop if any correlation exceeds `0.90` or more than `70%` of candidate dots fall within 3 px of a registry raster. Keep within three experiments or two hours, record negative results in JSON, and do not use a slot without separate authorization.

## Manual source-review links

The following official/trusted links were retained as review pointers but were **not opened or verified live in this session**. They are not evidence for local geology, layer availability, licensing, or current competition rules until manually reviewed:

- DrivenData competition data page: <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
- NLR GEMS rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- DrivenData reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
- USGS GeoDAWN data page: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- Great Basin Center for Geothermal Energy / INGENIOUS: <https://gbcge.org/current-projects/ingenious/>
- USGS State Geologic Map Compilation: <https://mrdata.usgs.gov/sgmc/>
- GDR regional compilation: <https://gdr.openei.org/submissions/1391>
