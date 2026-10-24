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

- This checkout lacks ignored template/registry inputs, so the local full suite was **277 passed, 36 skipped** (0 failed; 47 Rasterio pending-deprecation warnings). Input-dependent checks skip explicitly in this clean checkout. Local `scripts/validate_current.py` re-hashes KTH's saved TIFF/ZIP and agrees with the saved independent format audit; this is not a fresh grid/portal validation.
- The already-merged PR #67 mainline workflow restored SHA-pinned validation inputs and reported **290 passed, 23 skipped**, with `scripts/validate_kth88.py` research-format validation, site, readiness, current-release and expected-negative slot checks passing. Those checks validate a research download, not portal acceptance. Fresh CI for this branch's merge reconciliation also passed: test run `40112495118` and preflight `40112498287` both succeeded.
- `scripts/readiness.py` reports `BLOCKED`, not slot approval. `scripts/validate_release.py` is a historical MRR gate and is not the latest-candidate authority.
- Final local site/current consistency check passed. `docs/status.json` and `docs/data/current_release.json` bind to the KTH hash `5c7f1cb7…c259fd7bf`.

### Pass 3 — requirements, leakage, uniqueness, and claims

- KTH's pre-placement maximum absolute Spearman correlation is 0.07473 across 222 reachable rasters, below the 0.90 screen. Final dot overlap fails the binding 0.70 rule; the observed 0.89882 overlap with a GEMSDOE87 raster independently suffices to stop, and the dense witness overlap is 1.0. Do not waive this as a file-byte distinction.
- All three individual feature canaries are below symmetric AUC 0.90. Keep the exact `HOLDOUT-DTI` label, evaluator version, withheld-positive count, and CI attached to any performance mention. The incumbent comparison has no paired improvement CI. Do not call it a leaderboard score or projection.
- H33's 0.2778 remains **USER-REPORTED**, not organizer-confirmed. Local pixel forensics in [`research/h33-forensics-20261024.md`](h33-forensics-20261024.md) show a strict thinning chain (H19-5 → D2.8 → SOLO → H33): H33 removes 6,436 D2.8 dots, all within 2 pixels of mapped faults, while retaining the off-catalogue support. Under distance-weighted Tversky this could reduce false-positive mass without abandoning broader coverage, a plausible mechanism—not proof that the reported score is correct or that thinning alone caused it. The dated official leaderboard snapshot records top public DTI 0.4413 at 2026-10-24T07:19Z; it is now a historical snapshot, not H33's receipt or this repository's score.
- Official source pages document competition metric/format, rules, and public source descriptions. Private labels, authenticated organizer template/data, a KTH organizer receipt, exact AOI availability for supplemental data, and all relevant reuse permissions were not established here. The source inventory discloses these limits.
- The requested “single method paragraph below” is not specified in the supplied prompt. No new lane was silently selected. The next experiment remains blocked until an explicit method-lane instruction and authorized/hash-pinned inputs are supplied; the three-experiment/two-hour cap, visible-fault-only holdout features, exact mask, buffered component holdout, and before/after uniqueness checks remain binding.

## Current artifact and run-card facts

- File: `docs/downloads/gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif`
- SHA-256: `5c7f1cb7a8c37bb4c7f3ba6eef2d42f472a050c6b21436274e4ebc0c259fd7bf`
- Positive dots: 37,654; one float32 band; saved audit checks `[0,1]`, finite values, footprint, sample CRS/shape/transform, and a byte-identical one-TIFF ZIP. This is a local-format result only, not portal acceptance. TIFF SHA-256 is recorded above; ZIP SHA-256: `e21c8aac70fdcca59fedd5e4b9ee2d8148dc34b12ea6b158698eb7ff5f9e75ca`.
- Pre-placement max `|Spearman ρ|=0.074729` over 222 reachable rasters; final max `|ρ|=0.019341`. 3-pixel overlap is 0.898816 with a GEMSDOE87 prior and 1.000 with dense 17GEMSDOE. These exact overlap tests fail the binding geometric uniqueness rule.
- Submission name (archival only): `GEMSDOE88-KTH-BACDC27B`
- Note (105/140; archival only): `K/Th antisymmetric radiometric step + RTP trough, 37654 dots; HOLDOUT-DTI 0.0527; UNSCORED; DO NOT SUBMIT`
- Run card: `registry/kth88_run_card.json`; validation: `docs/data/kth88_validation.json`; registry evidence: `evidence/kth88_registry.json`; scientific dossier: `research/kth88-20261024.md`.
- Slot use: 0. `ORGANIZER-CONFIRMED`: none. Verdict: negative / stop.

## Ranked future geological hypotheses — proposals only, not run

The KTH-88 preregistration ranks four method hypotheses. Rank 1 (KTH-ANTISYMMETRIC-STEP) was run once and failed holdout/uniqueness; the three genuinely untested preregistered alternatives below are ranked 2–4. Expected gain is uncertain and qualitative; none has a score or projection. The KTH lane's one-experiment budget is spent and its duplicate stop is binding, so these are future-lane candidates only—not authorization to continue the lane.

| Prereg rank | Hypothesis / specific layers and physical transform | Why it may detect off-catalogue faults | Named non-fault mimic | Cost and official-source/input feasibility |
|---:|---|---|---|---|
| 2 | **CHI-ACROSS-SLOPE-STEP:** official-source 10 m DEM-derived chi/knickpoint and terrain steep-fraction layers; across-strike, elevation-normalized chi sign reversal coherent with knickpoint density. | A buried scarp could reorganize upstream catchments beyond mapped mountain-front traces. This is opposite-flank signed chi, not chi-step maxima or curvature alone. | Lithologic knickzone or base-level change. | Low compute; specific free official source is [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). Exact AOI tiles/derivatives were not obtained or validated from this sandbox; not viable until availability, license, and hashes are checked. |
| 3 | **RTP-GRAV-ADMITTANCE:** competition RTP band 2 and gravity anomaly band 13; spatially-varying magnetic-to-gravity gradient admittance jump normalized by local lithology. | Buried basement damage may disrupt both fields where surface fault traces are absent. It differs from MRR vertical-gradient residual regression and KTH radiometric contrast. | Unfaulted intrusive contact. | Medium compute; no new sensor, but competition inputs are absent locally and the [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) is login-gated. The manifest flags mirror reuse/redistribution terms unchecked; require authorized hash-verified inputs first. |
| 4 | **U-K-DISEQUILIBRIUM:** official USGS GeoDAWN K, U, and Th radiometric bands; regional-detrended U/Th versus K/Th discordance on orientation-consistent 300 m ridges. | Fluid migration could enrich uranium relative to thorium along fractures missing from the catalogue. It is joint K-and-U disequilibrium, not KTH's antisymmetric K/Th step, radon-piedmont, or generic count intensity. | Unfaulted granitic pluton or atmospheric radon residual. | Low compute; specific free official source is the [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI `10.5066/P93LGLVQ`. Official raw data/scale metadata were not authenticated here; mirrored u8 indices are uncalibrated. Verify raw bytes, scale/offset, and use permission before considering it viable. |

Every future experiment still requires fresh preregistration, feature-alone leakage canaries, buffered whole-component hide-and-recover using visible-fault-only catalogue features and exact masks, shared evaluator with HOLDOUT-DTI+95% CI, pre-placement rank correlation and final 3-pixel overlap. A separate selector decision is required before any slot. No proposal above was implemented in this review.

## Verified source links and limits

- [DrivenData competition description and data page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — snapshot checked 2026-10-24 only
- [NLR official competition rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) · [USGS Landsat Collection 2 Surface Temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)
- [AWS Sentinel-2 L2A COG registry](https://registry.opendata.aws/sentinel-2-l2a-cogs/) · [Alaska Satellite Facility](https://asf.alaska.edu/)

These are trusted official source pointers retained for review; no fresh external-page fetch was performed in this restricted run. This does not establish exact scene/tile availability, permission to redistribute, or authenticated private competition access. No external supplemental layer was used to build KTH-88. Treat each external-data proposal as blocked until source availability, exact AOI coverage, and use/redistribution terms are independently confirmed.
