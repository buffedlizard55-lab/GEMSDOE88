# GEMSDOE88 repository review and release correction — 2026-10-24 UTC

## Executive decision

**Current file:** `docs/downloads/gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif`

**OK to download for research:** YES. **OK to submit:** NO. **Weekly slot:** none selected or spent. **Organizer receipt:** none.

KTH-88 is byte-format-valid locally, but it failed the same-split holdout comparison and the binding all-raster uniqueness screen. Its **HOLDOUT-DTI** is 0.0526558082 (95% CI [0.0459111125, 0.0591507023], 22,893 withheld positives, evaluator `gems57-pooled-hide-v2`), against a stored same-split **HOLDOUT-DTI** incumbent of 0.1878876418. Final dots have 0.89882 forward overlap within 3 px of one GEMSDOE87 raster and 1.000 against the dense 17GEMSDOE witness, exceeding the 0.70 limit. The file is therefore **not unique under the requested geometric rule** and not slot-approved. Its SHA-256 is `5c7f1cb7a8c37bb4c7f3ba6eef2d42f472a050c6b21436274e4ebc0c259fd7bf`.

This review produced **no new scientific candidate TIFF**, ran **zero new method experiments**, selected **zero competition slots**, and made no portal upload. It corrected the public MAG-PSG mock claim and a separate stale MDC-88 clearance. The synthetic TIFF is quarantined at `evidence/simulated/mag-psg-synthetic-mock-20261024.tif` (SHA-256 `43b3e936cc4adfe3a93e3a7a95c443a7260f1f3a8c2c778ec4d5fbb1f1131d4e`); it is artificial strokes, not a pseudogravity computation, geological experiment, or candidate. The old MDC-88 site said “OK TO SUBMIT: YES” under a chance-corrected gate even though that record's own literal check reports duplicate=true and overlap 1.0 against the dense 17GEMSDOE raster. Its download was withdrawn and the bytes moved unchanged to `evidence/archive/mdc88/`; `docs/mdc88/status.json` now mirrors `registry/kdmc_gate_literal_reassessment.json` and says research archive only / DO NOT SUBMIT.

## H33's reported 0.2778: what local evidence supports

The value **0.2778 is USER-REPORTED**, not copied from an organizer submission receipt. The local, SHA-pinned forensics (`scripts/forensics_h33.py`, `evidence/h33_forensics_20261024.json`) establish a strict subset lineage: H19-5 → D2.8 → SOLO-D2.8 → H33, with no added positive pixels. D2.8 has 44,090 dots; H33 has 37,654. The 6,436 pixels removed from D2.8 in the later thinning are all within two pixels of the mapped catalogue. H33's median nearest-neighbor spacing is 3.0 pixels, close to the scoring kernel's three-pixel support; its median distance from mapped faults is about 19.65 pixels, versus 15 pixels for D2.8.

These facts make a pruning explanation plausible: under the distance-weighted Tversky formula, redundant dots near already-known traces may add false-positive cost while contributing little additional truth coverage. The measurements do **not** prove those removed dots were false positives, do not prove causation, and cannot verify the reported public score. The lineage variants are correlated, and the holdout labels are not the organizer's undisclosed expert-new-fault labels.

The official public leaderboard snapshot checked on 2026-10-24 at 07:19 UTC showed a top public DW-Tversky of **0.4413**, above H33's owner-reported 0.2778. A public snapshot is not an owner receipt or private score. The current KTH HOLDOUT-DTI is not comparable to a public leaderboard score; **no local evidence demonstrates that a new candidate can beat H33 or the leaderboard**.

Detailed pixel and score-arithmetic caveats: [`research/h33-forensics-20261024.md`](h33-forensics-20261024.md) and [`evidence/h33_forensics_20261024.json`](../evidence/h33_forensics_20261024.json).

## Ranked, genuinely untried fault-discovery hypotheses

Ranking is a qualitative research prior balancing potential discovery value and cost; it is not a score, projection, or promise. The methods below are absent from the implemented GEMS88 model features identified during review. No result is claimed for any of them.

| Rank | Hypothesis, layers and transform | Physical signature / off-catalogue rationale | Named non-fault mimic | Novelty vs repository | Cost and source availability |
|---:|---|---|---|---|---|
| **1** | **Hydro-vegetation persistence:** Sentinel-2 L2A red/NIR/SWIR reflectance; cloud-masked seasonal NDVI, NDMI and NDWI anomalies; oriented line-integral and cross-season persistence at the competition grid. | Blind permeable faults may focus shallow discharge and phreatophyte growth into narrow persistent moisture/vegetation corridors without a mapped scarp or potential-field edge. | Irrigation, canals, riparian drains, seasonal wetlands, playa salinity/moisture margins, roads. | No multiseason optical vegetation/wetness time series or temporal line-persistence feature is present in the identified GEMS88 stack or method code. | **Potential high / cost high.** Sentinel-2 L2A is listed as public/free/open by the AWS Open Data Registry, with anonymous S3 listing. Exact AOI scenes, cloud-free seasonal coverage, derived-data sharing terms and local retrieval were not verified. The imagery endpoints are outside this sandbox's host allowlist. **Not viable to run here yet.** |
| **2** | **Persistent thermal corridors:** Landsat Collection 2 Level-2 surface temperature with QA mask; multiyear seasonal median/anomaly and strike-coherent line persistence. | Repeated thermal expression could identify shallow geothermal discharge or alteration along blind faults that lack a reliable scarp. | Emissivity/albedo contacts, aspect heating, irrigation, wildfire, urban heat, cloud/shadow artifacts. | Existing code has point thermal/geothermal cues, but no multiyear Landsat surface-temperature persistence raster. | **Potential medium-high / cost high.** USGS documents global Level-2 surface-temperature products and its no-cost/open Landsat policy. Exact repeat-season scene coverage and challenge sharing remain unverified; cloud processing/storage may incur cost. Not viable in this checkout yet. |
| **3** | **Groundwater head compartments:** USGS Water Data for the Nation groundwater-level time series, well location/depth and aquifer metadata; remove seasonal/pumping trends and estimate repeatable head offsets and inter-well hydraulic-lag coherence. | A blind fault may form a conduit or barrier, leaving a persistent hydraulic head step or lag boundary beyond mapped fault traces. | Pumping, irrigation, seasonal recharge, screened-interval differences, aquifer contact, measurement-datum changes. | The repository contains point well/spring inventory cues, not time-series groundwater heads or a fault-compartment statistic. | **Potential medium / cost very high.** USGS groundwater records and services are public. Legacy NWISWeb pages are being migrated to Water Data for the Nation; exact in-footprint well density, record length, units and challenge sharing were not audited. A public national catalog does not prove local viability. |
| **4** | **Calibrated U–K disequilibrium:** raw official GeoDAWN K, U and Th grids with calibration/flight metadata; regionally detrended U/Th versus K/Th discordance on orientation-consistent ~300 m ridges. | Hydrothermal fluid migration can redistribute K and U relative to relatively immobile Th along faults absent from the catalogue. | Unfaulted granitoid/intrusive contact, soil cover, radon-background residual, survey leveling seam. | KTH-88 used an antisymmetric K/Th step from uncalibrated u8 indices. Calibrated U/Th discordance is untried and distinct, though sensor/method-adjacent. | **Potential medium-low / cost medium.** Official USGS GeoDAWN release is CC0 1.0, DOI `10.5066/P93LGLVQ`. Raw product, scale/offset, exact footprint and authorization were not authenticated; mirrored u8 layers are not adequate. Not viable without official raw bytes. |
| **5** | **Persistent InSAR discontinuities:** Sentinel-1 ascending/descending displacement and coherence time series; remove broad atmospheric/topographic terms and require geometry-consistent narrow gradients. | Persistent creep or fluid-pressure deformation may reveal blind faults in low-relief basins with weak optical/topographic expression. | Groundwater/mining subsidence, reinjection, atmospheric delay, vegetation decorrelation, snow/moisture change. | No satellite InSAR time series or ascending/descending displacement-consistency feature is implemented; existing strain/seismicity channels are different modalities. | **Potential uncertain / cost very high.** NASA/ASF distributes Sentinel-1 and offers free processing, but Earthdata login and an ASF EULA are required. Exact scene geometry, coherent time series, sharing terms and local retrieval are unverified. |

### Top-candidate validation status — BLOCKED, not passed

The rank-1 hydro-vegetation idea has **not** been scored or validated. A public Sentinel-2 catalog is not proof of cloud-free, exact-area time-series coverage or permission to share derived data with the competition. The competition feature stack is absent from this checkout. In addition, the prompt's referenced “single method paragraph below” is missing; the repository's frozen MAG-FABRIC-DISLOCATION lane already ran and stopped on a duplicate. Choosing a different lane silently would violate the single-lane rule.

Consequently there is no honest feature-alone leakage canary, buffered whole-component holdout, HOLDOUT-DTI confidence interval, registry surface audit, or candidate TIFF for rank 1. No weekly slot was touched. The holdout requirement remains pending the missing lane and authenticated/authorized inputs; this report does not call a hypothesis validated.

The strict final overlap rule also has a structural issue: the positive-everywhere 17GEMSDOE raster makes the literal forward overlap 1.0 for every nonempty candidate. That witness is preserved and not exempted. Under the exact rule as written, no nonempty raster can clear that final overlap threshold.

## Three review passes and repository correction

### Pass 1 — prompt, evidence, and claims

- Re-read `PROMPT.md`, README, current run card/feed, KTH TIFF/ZIP validation, registry evidence, H33 pixel forensics, method notes and public site pages.
- Found the public landing page and executive guide falsely described a synthetic MAG-PSG raster as a “new unique submission” and said it was OK to submit. The generator itself used artificial strokes and explicitly noted data limits.
- Confirmed the canonical current release is KTH-88, not MAG-PSG. The latest KTH run card reports research-download true, submit false, negative verdict, and duplicate overlap; no organizer receipt is available.
- Audited nested public pages and found `docs/mdc88/` still advertised submission clearance. `registry/kdmc_gate.json` records the same inconsistency: top-level chance-corrected `ok_to_submit: true`, but `uniqueness_literal.duplicate: true`, `stop_required: true`, and final overlap 1.0 against `data/registry/dense_17gemdoe.tif`. A distinct pre-placement surface screen is not documented for that historical candidate.

### Pass 2 — correction and implementation

- Removed the mock TIFF from `docs/downloads/` and preserved it under `evidence/simulated/` with its original SHA-256 and a machine-readable quarantine manifest.
- Renamed/reworked the generator to `scripts/build_synthetic_psg_demo.py`: it makes only a tagged I/O demo under `evidence/simulated/` and no longer calls the scientific submission writer.
- Rebuilt the landing page and executive guide so the KTH-88 file is offered for research only, the upload decision is explicitly NO, and future submission steps are conditional on all gates plus a separate selector authorization.
- Updated research and source pages with five genuinely untried proposals, H33 evidence, official source pointers and exact-area/access/permission limitations. Marked older pre-KTH review notes as superseded.
- Updated `validate_current.release_report()` and `docs/data/current_release.json` to carry a deterministic release date, candidate identifier, evidence class, explicit download/submit label and null organizer confirmation. The page JavaScript now fails closed against this feed plus the byte-bound audit.
- Added regression tests and strengthened `scripts/check_site.py` to recurse through nested public pages, reject re-publication of the synthetic mock, and forbid false submit-ready claims.
- Replaced both MDC-88 Pages views with a clear negative archive status, mirrored the strict literal reassessment into `registry/kdmc_gate_literal_reassessment.json` and `docs/mdc88/status.json`, and moved the original MDC-88 TIFF/ZIP/metadata unchanged out of `docs/downloads/` into `evidence/archive/mdc88/`. Updated the KTH registry evidence path without changing its measured raster hash.
- Retired `scripts/publish_kdmc_site.py` as a no-write command that exits 2; it can no longer render the old green banner or recopy the artifact. The archive and page explicitly distinguish format validity, research download, and submission approval.

### Pass 3 — verification and negative gate

- The first full test run caught one missing literal `DO NOT SUBMIT` label on the source page. That was corrected before final verification.
- Final `.venv/bin/python -m pytest -q`: **293 passed, 23 skipped, 0 failed**; 47 third-party Rasterio pending-deprecation warnings.
- `.venv/bin/python scripts/check_site.py`: PASS; recursively audits all public HTML pages, and the regression test confirms the MDC-88 publisher exits 2 without writing or copying files.
- `.venv/bin/python scripts/validate_kth88.py` and `scripts/validate_current.py`: PASS; current KTH-88 TIFF/ZIP hashes, format, current feed, 222-raster registry comparison, and negative status agree.
- `.venv/bin/python scripts/validate_artifact.py evidence/archive/mdc88/gemsdoe88-mdc88-pu-concentration-2p83px-20261024T0740Z-zeros.tif --template data/bridge/sample_submission.tif`: archived MDC-88 bytes remain format-valid; this is format only, not submission approval.
- `.venv/bin/python scripts/readiness.py`: `BLOCKED`, with HOLDOUT and UNIQUENESS blockers.
- `.venv/bin/python scripts/validate_current.py --require-submit` and `scripts/validate_kth88.py --require-submit`: both exit **2** as expected. No upload was attempted.

## Current feed, download decision, and integrity references

- Dated current release: [`docs/data/current_release.json`](../docs/data/current_release.json), candidate KTH-88, date `2026-10-24`, `ok_to_download: true`, `ok_to_submit: false`, `organizer_confirmed: null`.
- Dated official public leaderboard snapshot: [`docs/data/leaderboard.json`](../docs/data/leaderboard.json), checked 2026-10-24 07:19 UTC, top 0.4413. The static snapshot is not continuously scraped.
- Current TIFF/ZIP validation: [`docs/data/kth88_validation.json`](../docs/data/kth88_validation.json); run card: [`registry/kth88_run_card.json`](../registry/kth88_run_card.json); full final registry evidence: [`evidence/kth88_registry.json`](../evidence/kth88_registry.json).
- Quarantined mock: [`evidence/simulated/README.md`](../evidence/simulated/README.md); former public filename is no longer present under `docs/downloads/`.
- Current public pages: [`docs/index.html`](../docs/index.html), [`docs/executive-summary.html`](../docs/executive-summary.html), [`docs/research.html`](../docs/research.html), and [`docs/sources.html`](../docs/sources.html).
- Superseded MDC-88 status: [`registry/kdmc_gate_literal_reassessment.json`](../registry/kdmc_gate_literal_reassessment.json), mirrored at [`docs/mdc88/status.json`](../docs/mdc88/status.json); the prior TIFF/ZIP/metadata bytes are preserved at [`evidence/archive/mdc88/README.md`](../evidence/archive/mdc88/README.md) but no longer linked as Pages downloads.

## Official sources reviewed

- [DrivenData problem, scoring metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [NLR official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [USGS Landsat Collection 2 surface temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)
- [AWS Open Data Registry Sentinel-2](https://registry.opendata.aws/sentinel-2/) and [Sentinel-2 COG/STAC registry](https://registry.opendata.aws/sentinel-2-l2a-cogs/)
- [USGS Water Data for the Nation](https://waterdata.usgs.gov/) · [NWIS Mapper](https://www.usgs.gov/tools/national-water-information-system-nwis-mapper) · [Groundwater Levels Service](https://nwis.waterservices.usgs.gov/docs/groundwater-levels/)
- [NASA Earthdata Sentinel-1](https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/sentinel-1) · [ASF DAAC access tools](https://www.earthdata.nasa.gov/centers/asf-daac/data-access-tools)

Primary-source descriptions verify that official datasets exist and describe broad access/terms. They do not establish the exact scene/tile/well coverage, candidate data quality, organizer permission to share derivatives, private leaderboard results, or account receipts. Do not call a proposal viable until those checks are performed on the authorized inputs.
