# Ranked hypothesis queue — geothermal-indicative fault mapping

**Review date:** 2026-10-25
**Status:** research design only; no new experiment, feature read, or data download in this review.
**Ranking meaning:** priority for source/data feasibility review and testability, **not** an expected DTI or score ranking. No gain estimates are available. XGCE, the prior first choice, is blocked: its candidate HOLDOUT-DTI was not computed, its leakage diagnostic is not a spatially blocked canary, its pre-placement surface-rank check is absent, and the recorded literal duplicate gate is `1.0 > 0.70`. **Do not implement or submit XGCE unless the blocker is explicitly resolved under the current competition protocol.**

## Evidence boundaries and manual source review

All mechanisms below are hypotheses, not established local geology or validated fault detections. Names, band assignments, and transforms are taken from repository artifacts/code where noted; they were not checked against local raster metadata in this session because `data/` is absent. External links are pointers for a later manual review, not evidence that the data are currently available, licensed, or appropriate:

- USGS GeoDAWN airborne magnetic/radiometric data: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- INGENIOUS Great Basin project: <https://gbcge.org/current-projects/ingenious/>
- Competition data and task description: <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
- NLR competition rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- EPSG:32611 reference: <https://epsg.io/32611>

Before using any external layer, record its provider, exact product/version, coverage, resolution, units, license/permission, access date, and checksum; compare those to the official rules. None of those checks was completed here. Literature references or numerical geological claims should not be added until a reviewer has verified the citation and its applicability.

## Ranked matrix

| Rank | Hypothesis | Layers and proposed transforms | Off-catalogue rationale (untested) | Distinctness claim (limited) | Named mimics | Relative cost / gain |
|---|---|---|---|---|---|---|
| 1 | **XGCE — normalized gravity–magnetic cross-gradient with strain modulation** | Repository-listed gravity and magnetic horizontal/vertical gradients; normalized cross-product; basement-depth high-pass; dilation/shear modulation; proposed visible-fault exclusion and spacing. Exact feature availability and valid fold construction remain unverified. | Could emphasize buried or weakly expressed structural intersections away from mapped traces; this is a conjecture, not evidence of missed faults. | Initial code/repository scan suggests this exact composite differs from some earlier lanes; not a claim of global novelty. The archived artifact fails the binding literal duplicate rule and has no candidate score. | Lithologic contacts, pluton/caldera margins, inversion seams, edge artifacts, and drainage/fan boundaries. | Low–medium compute if approved inputs exist; **gain not measured and no projection offered**. Blocked. |
| 2 | **RADM — radiometric ratios with magnetic-low context** | Candidate K/Th and U/Th ratios with robust local detrending, optionally paired with a magnetic analytic-signal low. Radiometric source, units, masks, and coverage are not verified. | Alteration-related contrasts might occur beyond mapped surface traces; local evidence is required. | Initial repository scan did not identify this exact ratio combination; novelty is provisional. | Felsic units, weathering, transported sediment, moisture/soil effects, and radiometric calibration seams. | Medium; gain not measured. Data/license gate first. |
| 3 | **SLIP — stress-resolved dilation tendency** | Mapped or independently sourced stress orientation plus local structural orientation; resolve a documented stress tensor into a dilation-tendency score. Required stress inputs and uncertainty are unknown. | Could prioritize favorably oriented structures rather than simply high strain; not a validated local predictor. | A mechanics-based contrast may differ from scalar-gradient lanes; must confirm against the full repository. | Dikes, joints, modelled stress artifacts, and orientation uncertainty. | Medium–high; gain not measured. Requires trusted stress data and uncertainty propagation. |
| 4 | **THCL — deep/shallow conductivity contrast** | Candidate shallow/deep conductivity bands (if present and permitted), log/ratio contrast, then scale-aware basement-boundary context. Band names, units, and resolution need source verification. | A contrast may distinguish deep structure from shallow conductive cover; this is a proposed test only. | Differs conceptually from using an absolute conductivity score, but prior-lane comparison is incomplete. | Saline playa/brine, alteration, inversion smoothing, and depth-dependent resolution. | Medium; gain not measured. Do not proceed without input/units verification. |
| 5 | **CHIK — channel-profile and curvature-step conjunction** | A legally usable DEM and derived channel-profile/chi and curvature measures; compare cross-slope and along-channel signals at a declared scale. DEM availability, resolution, and permissions are unknown. | Persistent drainage-profile changes could provide an independent structural proxy; they can also be entirely geomorphic. | Potentially distinct from geophysical-only lanes; requires repository inventory. | Lithologic ledges, dams, incision history, fan transitions, and DEM artifacts. | High; gain not measured. External data gate first. |

## Mandatory gates before any implementation

1. **Resolve the binding duplicate stop first.** The recorded dense-witness certificate says every nonempty candidate support has literal forward overlap `1.0`; do not mask, rename, or replace the metric to evade it. No candidate placement or slot use while this rule blocks.
2. **Rank inputs from official/trusted source documentation.** Confirm exact product, access, permission, coverage, grid, units, missing-data handling, and reproducible checksums. The links above have not been opened/verified in this session.
3. **For any future candidate, reuse the shared cached stack, holdout/evaluator, uniqueness implementation, and submission writer.** Do not fork these for convenience. Withhold whole fault segments with the required buffer; construct every catalogue-derived feature from visible faults only; mask visible faults pixel-exactly; use the pooled DTI protocol (α=.2, β=.8, 300 m triangular kernel) and report the evaluator version, withheld-positive count, and 95% CI.
4. **Run every feature alone in spatially blocked folds.** Any symmetric AUC above `0.90` is leakage until disproven. Do not call catalogue-vs-random diagnostics a canary.
5. **Check continuous prediction-surface rank correlation before placement and candidate-dot proximity after placement against the complete registry.** Apply the user’s thresholds literally: if any correlation exceeds `0.90` or more than `70%` of dots are within 3 px of a registry raster, record the duplicate and stop.
6. **Cap work at three experiments or two hours, whichever comes first.** Write a JSON run card for each attempt, including negative results. Slot selection is separate; no slot is used without explicit authorization and all gates passing.

## Outcome

This queue is a proposal for later review, not an approval to implement. The current XGCE artifact is **OK TO DOWNLOAD FOR RESEARCH: YES** only as an archived file whose ZIP integrity/identity were checked; raster geospatial validation was not rerun here. **OK TO SUBMIT: NO — DO NOT SUBMIT.** No candidate HOLDOUT-DTI, organizer score, or estimated gain is available.
