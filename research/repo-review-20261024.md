# GEMSDOE88 repository review — 2026-10-24

## Decision

**KTH-88 is the latest candidate. Download for research: YES. Submit: NO.** Its HOLDOUT-DTI is 0.052656 (95% CI 0.045911–0.059151; 22,893 withheld positives), well below the same-split incumbent 0.187888, and its final dots violate the literal uniqueness limit: overlap 0.89882 with a GEMSDOE87 raster and 1.000 with the dense 17GEMSDOE witness (limit 0.70). The feature-alone canary max symmetric AUC is 0.5097. The format-only audit passes; this does not override scientific/uniqueness failures or authorize a slot. **Keep the negative verdict. Do not spend a slot.** No organizer receipt exists.

The K/Th inputs are uncalibrated u8 indices, not measured elemental abundance. The grid/input provenance is owner-mirrored and not independently authenticated to the private organizer download. This review performed no new experiment, raster generation, submission selection, or portal upload. Existing experiment count: one in the KTH lane; no additional experiment was attempted.

## Review passes

### Pass 1 — prompt, implementation, evidence, and website

- Re-read `PROMPT.md` and reviewed the latest KTH run card, preregistration, independent TIFF/ZIP audit, registry evidence, readiness/current validators, workflow gates, README, research overview, and submission guide.
- Confirmed that the landing page and executive guide identify KTH-88 as current, show research-download and submit decisions separately, provide TIFF/ZIP links and archival name/note, and label the candidate **DO NOT SUBMIT**.
- Corrected current-feed drift inherited from the concurrent `main` update: `docs/data/current_release.json`, `docs/status.json`, readiness, and `validate_current.py` now bind to KTH-88, not the older fabric-dislocation TIFF. Updated the site research dossier, source references, and submission guide to keep older candidates historical.
- `scripts/check_site.py`: **PASS** after reconciliation. Local links resolve; the KTH artifact, negative run card, current release hashes, and visible safety decision agree.

### Pass 2 — full tests and byte-level validators

- Restored the SHA-pinned validation inputs using the existing validation-only restoration path; no new feature input or candidate was created.
- Full suite: **290 passed, 23 skipped**. Rasterio emitted 47 pending-deprecation warnings; no test failed.
- `scripts/validate_kth88.py`: **PASS for research download / format only**. It independently reopens the saved TIFF and ZIP, confirms the ZIP has exactly one byte-identical TIFF, checks the sample grid and local format, and verifies saved hashes. Its `--require-submit` mode correctly exits 2.
- `scripts/validate_current.py`: reports KTH-88 and its current file/ZIP hashes; `--require-submit` correctly exits 2. `scripts/readiness.py` reports `BLOCKED`, not slot approval. `scripts/validate_release.py` remains a historical MRR gate and its `--require-submit` also exits 2; it is not the latest-candidate authority.
- Final site/current consistency check passed. `docs/status.json` and `docs/data/current_release.json` now carry the KTH hash `5c7f1cb7…c259fd7bf`.

### Pass 3 — requirements, leakage, uniqueness, and claims

- KTH's pre-placement maximum absolute Spearman correlation is 0.07473 across 222 reachable rasters, below the 0.90 screen. Final dot overlap fails the binding 0.70 rule; the observed 0.89882 overlap with a GEMSDOE87 raster independently suffices to stop, and the dense witness overlap is 1.0. Do not waive this as a file-byte distinction.
- All three individual feature canaries are below symmetric AUC 0.90. Keep the exact `HOLDOUT-DTI` label, evaluator version, withheld-positive count, and CI attached to any performance mention. The incumbent comparison has no paired improvement CI. Do not call it a leaderboard score or projection.
- H33's 0.2778 remains **USER-REPORTED**, not organizer-confirmed. Raster lineage is compatible with thinning near-catalogue dots while retaining broader coverage, a plausible metric mechanism but not proof of score causation. The public leaderboard snapshot checked 2026-10-24 had a listed top public score 0.4413; it is not a private receipt for H33 or this repository.
- Official source pages document competition metric/format, rules, and public source descriptions. Private labels, authenticated organizer template/data, a KTH organizer receipt, exact AOI availability for supplemental data, and all relevant reuse permissions were not established here. The source inventory discloses these limits.
- The requested “single method paragraph below” is not specified in the supplied prompt. No new lane was silently selected. The next experiment remains blocked until an explicit method-lane instruction and authorized/hash-pinned inputs are supplied; the three-experiment/two-hour cap, visible-fault-only holdout features, exact mask, buffered component holdout, and before/after uniqueness checks remain binding.

## Current artifact and run-card facts

- File: `docs/downloads/gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif`
- SHA-256: `5c7f1cb7a8c37bb4c7f3ba6eef2d42f472a050c6b21436274e4ebc0c259fd7bf`
- Positive dots: 37,654; one float32 band; format check is a local-format result only.
- Submission name (archival only): `GEMSDOE88-KTH-BACDC27B`
- Note (105/140; archival only): `K/Th antisymmetric radiometric step + RTP trough, 37654 dots; HOLDOUT-DTI 0.0527; UNSCORED; DO NOT SUBMIT`
- Run card: `registry/kth88_run_card.json`; validation: `docs/data/kth88_validation.json`; registry evidence: `evidence/kth88_registry.json`; scientific dossier: `research/kth88-20261024.md`.
- Slot use: 0. `ORGANIZER-CONFIRMED`: none. Verdict: negative / stop.

## Ranked future geological hypotheses — proposals only, not run

The ordering is qualitative potential/cost, not a score, model projection, or authorization. First resolve the unspecified method paragraph and select only one lane. Verify source availability and terms before use.

| Rank | Hypothesis / physical signal | Named non-fault mimic | Cost / gate before work |
|---:|---|---|---|
| 1 | Seasonal hydro-vegetation lineaments from Sentinel-2 L2A NDVI/NDMI/NDWI persistence and oriented continuity | Irrigation, riparian corridors, canals, roads, playa moisture | High; exact AOI coverage and shareability not verified |
| 2 | Persistent multi-season thermal corridors using Landsat Collection 2 surface-temperature anomalies | Solar aspect, emissivity, irrigation, wildfire, cloud/shadow, urban heat | High; exact AOI retrieval and reuse conditions unverified |
| 3 | Cross-catchment drainage deflection from DEM channel-azimuth shifts, signed offsets, and aligned knickpoints | Caprock, lithologic contact, fan avulsion, shoreline, roads | Medium-high; confirm exact 3DEP tiles; use a statistic distinct from existing generic terrain features |
| 4 | Cross-depth strike agreement between RTP, magnetic/gravity gradients, and detrended elevation structure tensors | Bedding/stratigraphic strike or coherent intrusive contact | Medium; use authenticated provided inputs and ensure distinction from prior fabric methods |
| 5 | InSAR deformation discontinuities using Sentinel-1 ascending/descending displacement gradients and coherence breaks | Groundwater/mining subsidence, reinjection, decorrelation, atmospheric delay | Very high; time-series density, account access, and terms unverified |

Every proposal needs a preregistration, a named mimic, per-feature leakage canaries, buffered whole-fault hide-and-recover using visible-fault-only catalogue features, exact masking, and a same-protocol HOLDOUT-DTI with 95% CI before any submission decision. No candidate is selected here.

## Verified source links and limits

- [DrivenData competition description and data page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — snapshot checked 2026-10-24 only
- [NLR official competition rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) · [USGS Landsat Collection 2 Surface Temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)
- [AWS Sentinel-2 L2A COG registry](https://registry.opendata.aws/sentinel-2-l2a-cogs/) · [Alaska Satellite Facility](https://asf.alaska.edu/)

The public descriptions were checked in the review context; this does not establish exact scene/tile availability, permission to redistribute, or authenticated private competition access. No external supplemental layer was used to build KTH-88.
