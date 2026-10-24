# Session review — 2026-10-24 (no organizer slot)

## Decision first

**No new submission is authorized.** Downloadable research-only TIFFs and their automated checks are linked at [the executive guide](../docs/executive-summary.html). In particular, MDPS-88 is format-valid but fails its scientific promotion gate; PHASE-88 additionally breaches the literal overlap threshold. Do not upload either file. No organizer receipt exists for either. This review does **not** claim to have generated a fresh lane candidate, performed a new blocked holdout, or obtained an organizer score.

The requested “single method paragraph below” is absent from the supplied prompt. Choosing a new method on its behalf would defeat the parallel lane constraint. The existing preregistered [PHASE-88 experiment](../registry/preregistration_phase88.json) has already used that lane; changing the method or emitting a novel but untested TIFF merely to satisfy a filename requirement would not satisfy the promotion protocol. Moreover, the [PHASE-88 run card](../registry/phase88_run_card.json) documents a dense registry witness that makes the literal >70% within-3-pixel rule impossible for any nonempty candidate. This is a **gate inconsistency to resolve in the selector**, not permission to silently exclude that witness. A different file hash is not evidence of scientific uniqueness.

## What the 0.2778 figure can and cannot show

The 0.2778 attributed to H33 is **USER-REPORTED**, not a receipt independently retrieved this session. The [on-disk lineage audit](../evidence/h33_forensics_20261024.json) counts 37,654 H33 dots and measures their distances to the mapped catalogue; the series of user-reported scores rises from H19-5 (0.1922), through D2.8 (0.2600), to H33 (0.2778). That is consistent with sparse, well-spaced off-catalogue emission and a favorable precision/recall trade-off under a distance-tolerant metric. It does **not** isolate a causal geological feature, prove an unbiased predictor, or establish that a new model can exceed 0.2778. The prompt itself supplies incompatible leaderboard maxima (0.4413 and 0.3195); neither is independently verified here. Local HOLDOUT-DTI is not a leaderboard estimate.

## Candidate queue (untested suggestions, not submission approvals)

The three existing [PHASE-88 preregistered hypotheses](../registry/preregistration_phase88.json) give the full layers, signatures, missing-catalogue rationale, non-fault mimics, and differences from prior methods. Ranking by expected improvement is *uncertain*, since only rank 1 was tested and negative:

| Priority | Hypothesis and layers | Physical signature / missing-catalogue rationale | Non-fault mimic | Difference / cost |
| --- | --- | --- | --- | --- |
| 1 (already tested, negative) | PHASE-88; RTP magnetic band 2 + isostatic gravity band 13 | Gradient-vector directional disagreement across buried basement offsets; concealed structure may lack a surface trace | Intrusive contacts, remanence, flight-line/interpolation seams | Cross-field disagreement rather than co-edge agreement; medium cost |
| 2 (untested) | Radiometric-relief quadrature; K/Th + detrended DEM band 12 | Signed quadrature across a ridge could indicate alteration without an obvious scarp | Potassic tuff contact / soil sorting | Quadrature, not K/Th step or anomaly count; low cost |
| 3 (untested) | Shear-gravity decoupling; strain invariant + gravity slope | Strain ridge offset from density edge could expose recently active buried displacement | Regional inversion smoothing / lithologic contact | Angular decoupling, not raw strain-weighted emission; low cost |

All three rely on the pinned competition feature stack, not a new third-party dataset; however, its owner mirror is SHA-pinned, **not independently authenticated against an organizer download**. Any later candidate needs individual-feature leakage canaries, buffered whole-segment holdout with visible-only catalogue features, complete registry screening before and after placement, and written-byte validation. Neither the other two hypotheses nor any supposed score improvement is established here.

## Sources and limits

Official references for manual review: [DrivenData competition/problem and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [official reference code](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN survey description](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf). Network policy in this session allows GitHub and package registries, not direct independent retrieval of DrivenData, USGS, or NLR pages. Links are review targets, **not** claims that these pages were live-checked in this session. The local environment initially lacked rasterio and restored inputs. Existing measurements are cited to repository evidence rather than represented as new experiments.

Next selector actions: clarify the missing lane paragraph and whether dense all-positive registry rasters are in scope; obtain organizer-authenticated reference raster/receipt when access permits; require a candidate to beat the incumbent on identical holdout folds with paired confidence bounds before approving any upload. A GitHub Pages static site cannot autonomously submit to a signed-in third-party portal.
