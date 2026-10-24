# GEMSDOE88 review — 2026-10-24 (three passes)

## Executive decision

The newest artifact already in the repository is **MDPS-88** (`docs/downloads/gems88-mdps88-mix-29742dots-20261024-zeros-DO-NOT-SUBMIT.tif`, SHA-256 `bd64000f96e96f09202d61027fb5ef45cff53baed7591279cc7e971ba1e835cd`). It is **OK TO DOWNLOAD FOR RESEARCH; NOT OK TO SUBMIT**. It is pixel-distinct from the H33 raster, but it fails the user-specified literal geometric uniqueness rule because the final dots all lie within three pixels of the full-footprint positive `dense_17gemdoe.tif` witness. It also fails the scientific promotion rule: the far-regime holdout is below the stored ADHR reference and its paired interval against the fold-fair control crosses zero. No competition slot was spent; no `ORGANIZER-CONFIRMED` score exists.

The present task did not generate a second TIFF or run a fresh geological experiment. The existing file meets the research-download deliverable requirement, but it is expressly not a submission-ready file. Under the literal no-dense-exemption rule, every non-empty raster is geometrically blocked by the full-footprint witness; producing another non-empty file would not fix that.

## H33 and the reported 0.2778 — evidence-bounded explanation

- **`0.2778` is a USER-REPORTED submission score** from the supplied GEMSDOE32 record; there is no owner portal receipt in this checkout tying that number to a particular submission event. It is not labelled `ORGANIZER-CONFIRMED` here.
- The restored, SHA-pinned public raster for H33 has 37,654 positive cells and is a strict pixel subset of the D2.8 raster. The measured difference is 6,436 deleted cells; all deleted cells are within two pixels of the mapped-fault raster. This is directly auditable in `evidence/h33_forensics_20261024.json` and `research/session-20261024-audit-why-0.2778.md`.
- The plausible mechanism is a precision/coverage trade-off: removing redundant predictions very close to already-known faults can reduce false-positive cost while preserving more spatially distinct coverage. The recorded climb from D2.8 (`0.2600`) to H33 (`0.2778`) is consistent with that mechanism, but both numbers are USER-REPORTED claims and the pixel comparison alone does not prove causality.
- The GEMSDOE32 site’s claimed `0.2778` is not the competition’s current public top. The repository contains an **OFFICIAL-PUBLIC-LEADERBOARD-SNAPSHOT**, read 2026-10-24 at 07:19 UTC, of `0.4413`; it is dated, not live, and may now be stale. That number describes the public leaderboard, not this repository’s candidate and not a submission receipt.
- **Can this project demonstrate a score above `0.2778`? Not from current evidence.** The leaderboard is a different label population than the local hide-and-recover instrument. No local HOLDOUT-DTI result is a projection of public score. Beating the claim requires a real submission receipt; the user-requested holdout and uniqueness gates must still be passed first.

## Ranked next geological hypotheses

The rank ordering below is a research shortlist already documented in `research/candidate-hypotheses-20261024-mdc88.md`; gains are intentionally not repeated as estimates here because they are unvalidated model projections, not scores. All candidates use provided competition-stack bands and require no new external data to test. Their expected value is qualitative, not evidence of improvement.

| Rank | Hypothesis | Layers and physical signature | Why it may reveal an off-catalogue fault | Main non-fault mimic | Repo distinction | Cost / status |
|---:|---|---|---|---|---|---|
| 1 | **H-QTS: cover-thickness step / trans-tensional structure** | `depth_to_base_surf` (band 15), detrended elevation (band 12), its slope (band 19), isostatic gravity (band 13) and gravity-gradient band 18; multiscale cover-thickness gradient combined with disagreement between buried-basement and surface-gradient direction. | A buried basin-bounding displacement may create a basement/cover step with weak or absent surface scarp and no mapped trace. | Pluvial shorelines, alluvial-fan toes, lithologic boundaries and gravity interpolation seams. | New physical interaction/feature: vector discordance of buried-base and surface gradients; unlike MDPS's general multichannel classifier and prior single-field/crest scores. | Low–medium; next-step handoff, not run in this review. |
| 2 | **H-RTR: radiometric K-depletion / Th residual over covered traces** | Provided K/Th/U radiometric channels (bands 5–8) with local residualization and terrain conditioning. | Hydrothermal alteration can redistribute K and create a local residual even where a fault is buried or lacks a preserved scarp. | Felsic volcanic contacts, soil sorting, uranium roll fronts and survey leveling stripes. | Related to the already-tested K/Th step lane; proposed distinction is local background residual + terrain conditioning, so novelty is incremental and must be audited against KTH code before preregistration. | Low–medium; test only with single-feature canaries and visible-only buffered holdout. |
| 3 | **H-SSA: scale-selective strike agreement** | Potential-field gradients from RTP/magnetics/gravity, terrain lineaments and the DEM; compare orientation consistency across smoothing scales. | A structurally coherent concealed boundary may persist across scales even where individual source contrast is weak. | Pluton margins, volcanic-flow edges and flight-line artifacts. | Cross-scale agreement among independent fields, rather than existing single-scale orientation or crest amplitude. | Medium; confirm it is not a reimplementation of existing orientation/scale lanes before coding. |
| 4 | **H-CAL: conductivity–elevation anomaly ladder** | Provided conductivity surface, detrended elevation/relief and gravity context; separate local upflow-like anomalies from broad down-gradient outflow. | A covered conduit may express as a compact conductivity/elevation relation without a mapped surface fault. | Playa clays, irrigation, saline groundwater and basin-wide hydrologic gradients. | Joint conductivity–elevation regime ordering, distinct from standalone conductivity rank; overlap with earlier MDPS physics channels must be measured. | Medium; high risk of non-fault hydrogeochemical confounding. |
| 5 | **H-TRI: relay-ramp / triple-junction geometry** | Existing visible fault-segment graph plus multi-scale terrain and potential-field crest geometry. | Fault tips and relay zones can create gaps in mapped trace networks where concealed connecting structures are plausible. | Drainage junctions, fan distributaries and intersecting lithologic contacts. | Graph topology/relay geometry rather than scalar distance to faults or rasterized ridge density; must exclude held-out segment geometry. | High; depends on accurate graph construction and must derive fault features from visible traces only in holdout folds. |

**Top-candidate gate:** H-QTS is the lowest-cost distinctive candidate in the previous handoff. It was not run here. The user’s message refers to a single-method paragraph “below” but supplies no explicit paragraph; earlier runs in this checkout name several different lanes. The full training stack was also absent at session start (only validation rasters were restored), and the pinned mirror is not an independently authenticated organizer download. Do not silently choose a lane or treat the old handoff’s “cached” claim as proof that the current workspace has the data. Restore/verify the exact inputs and freeze one lane before the next H-QTS experiment.

## Review findings and changes

### Pass 1 — inspect prompt, latest artifact, site, gates, lineage

1. Read `PROMPT.md`, repository session notes, MDPS run card, MDPS independent byte audit, MDPS gate, README, landing page, executive summary, current-release compatibility record, and the site/test scripts.
2. Confirmed that the GitHub Pages landing page already exposes an easy GeoTIFF and one-file ZIP download, unique name/note archive fields, run card, and automated byte audit. The page correctly says the file is **not submit-ready**.
3. Found a material consistency defect: `scripts/check_site.py` asserted that the landing page’s first/latest candidate was PHASE-88 and KTH-88, while the visible landing page and executive summary identify MDPS-88. `readiness.py` also generated its status hash from the PHASE-88 legacy record, contradicting the MDPS status feed.
4. Found a uniqueness-policy mismatch: the MDPS v3 diagnostic called its sparse/like-for-like result a pass, while the literal user rule has no dense-raster exemption and measured final overlap is `1.0` with `dense_17gemdoe.tif`. This is a binding duplicate under the requested protocol.

### Pass 2 — fix current status and fail-closed gate

- Updated `scripts/check_site.py` to verify MDPS-88 as the latest experiment, bind the artifact, ZIP, run card, and independent audit to the same hashes, check the run-card holdout labels/CI and visible decision, and keep PHASE-88 explicitly archival.
- Changed `scripts/readiness.py` to derive its status from the MDPS-88 run card, gate, independent byte audit, and on-disk SHA-256; it no longer substitutes the PHASE-88 compatibility pointer for the latest experiment.
- Added the literal overlap rule to MDPS status/gate evidence: `1.0 > 0.70` against the full-footprint positive witness is a uniqueness failure. Kept the v3 sparse/like-for-like measurement as a non-binding diagnostic rather than deleting it.
- Updated the MDPS submission builder so future rebuilds fail closed on literal final-dot overlap and added tests for the dense witness, inclusive `0.70` boundary, missing measurements and NaN.
- Updated the overview and executive guide to say **pixel-distinct** rather than implying protocol uniqueness, explain the literal duplicate, and link the independent audit on both pages. Clarified that PHASE-88 is an archive/compatibility record.

### Pass 3 — rerun validators and tests

- `python scripts/restore_inputs.py --validation`: restored the hash-pinned validation rasters from public owner mirrors; it did not restore or authenticate the full training stack.
- `python scripts/validate_mdps88.py`: independent TIFF/ZIP byte audit passed. `--require-submit` exited **2**, as expected for a blocked file.
- `python scripts/readiness.py`: **BLOCKED**, with both holdout and literal uniqueness blockers; research download is allowed, submission is not.
- `python scripts/check_site.py`: passed after the changes and now verifies the actual latest artifact rather than stale KTH/PHASE pointers.
- Full local suite after the new literal-overlap tests: **300 passed, 23 skipped, 0 failed**. The skips are input-dependent tests; warnings are Rasterio pending deprecations. This is not proof of organizer acceptance.

## Irregularities / constraints to keep visible

1. The prompt contains incompatible reported “highest” values: `0.2778`, `0.3195` and `0.4413`. The repository classifies H33 as a USER-REPORTED claim and `0.4413` as a dated public leaderboard snapshot. They are not interchangeable.
2. A positive-everywhere registry raster makes the literal final-dot overlap gate impossible for every non-empty prediction. The candidate is blocked, not exempted. The policy is internally infeasible unless the user explicitly changes it; the agent must not silently waive it.
3. `data/` is gitignored. The user’s original DrivenData login-walled inputs are not independently authenticated here; the available input copies are SHA-pinned owner mirrors with data-use/redistribution caveats. Current local validation restored only the sample, catalogue and registry set.
4. Zero organizer receipts are present. No local holdout result can establish a public leaderboard score or guarantee a score above any entry.
5. The site contains a dated leaderboard snapshot and a live official link; there is no continuously running updater or account-authenticated feed. Treat the local snapshot as potentially stale.
6. The old MDC-88 handoff recommends H-QTS, while the user prompt omits the paragraph that would assign a single method lane. That mismatch remains unresolved. Do not run another lane until the lane/data contract is explicit and the full SHA-pinned inputs are present.

## Official verification links for manual review

These are source links already listed in the project; the current sandbox run independently verified local repository records and hashes, but did not fetch every external site anew.

- DrivenData problem, metric and submission format: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- DrivenData public leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- NLR/DOE competition rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- DrivenData reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
- USGS GeoDAWN survey: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- DOE GDR INGENIOUS submission: <https://gdr.openei.org/submissions/1391>
- USGS 3DEP: <https://www.usgs.gov/3d-elevation-program>
- EPSG:32611: <https://epsg.io/32611>
