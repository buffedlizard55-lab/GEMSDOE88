# GEMSDOE88 repository review — 2026-10-24

## Executive decision

**Current artifact:** `docs/downloads/gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif`.

- **OK TO DOWNLOAD FOR RESEARCH: YES. OK TO SUBMIT: NO — DO NOT SUBMIT.** One-click file and single-TIFF ZIP are linked at the top of the website. The TIFF is byte/pixel-distinct, but fails the binding geometric uniqueness criterion: 89.8816% of dots are within 3 pixels of a GEMSDOE87 prior and 100% overlap a positive-everywhere 17GEMSDOE witness.
- **This review did not generate another TIFF or run another experiment.** KTH-88 is the latest committed candidate; its lane stopped after its first test on the duplicate gate. The current checkout has no local `data/` inputs. Do not create a cosmetic variant or quietly start another experiment in the KTH lane.
- **ORGANIZER-CONFIRMED score:** none; **weekly slots used: 0**.

The canonical experiment and saved audit are [`registry/kth88_run_card.json`](../registry/kth88_run_card.json), [`docs/data/kth88_validation.json`](../docs/data/kth88_validation.json), and [`evidence/kth88_registry.json`](../evidence/kth88_registry.json). The artifact is a valid local research download, not a submission recommendation or evidence of organizer acceptance.

## KTH-88 results — evidence labels

- **HOLDOUT-DTI** `0.0526558082`, 95% CI `[0.0459111125, 0.0591507023]`, 22,893 withheld positives, evaluator `gems57-pooled-hide-v2`.
- **HOLDOUT-DTI** same-split incumbent `0.1878876418`, 95% CI `[0.1716976485, 0.2032601221]`, 22,893 withheld positives, same evaluator. No paired incumbent CI was available; do not invent one.
- Feature-alone leakage canary maximum symmetric AUC: `0.5096995` (threshold 0.90; pass).
- Pre-placement max `|Spearman rho|` was `0.0747291` across 222 accessible rasters. Final max rho was `0.0193415`. Final 3-pixel overlap was `0.8988155` against a GEMSDOE87 raster and `1.0000` against the all-positive 17GEMSDOE witness. Binding duplicate gate fails.
- Saved validator evidence: one-band `float32`, 37,654 binary `{0,1}` dots; all values finite and in `[0,1]`; sample-grid CRS/shape/transform match; no nodata sentinel; no mass outside footprint; one-TIFF ZIP matches. TIFF SHA-256 `5c7f1cb7a8c37bb4c7f3ba6eef2d42f472a050c6b21436274e4ebc0c259fd7bf`; ZIP SHA-256 `e21c8aac70fdcca59fedd5e4b9ee2d8148dc34b12ea6b158698eb7ff5f9e75ca`.
- **Research name:** `GEMSDOE88-KTH-BACDC27B`. **Note (105/140):** `K/Th antisymmetric radiometric step + RTP trough, 37654 dots; HOLDOUT-DTI 0.0527; UNSCORED; DO NOT SUBMIT`.

These are **HOLDOUT-DTI** and local format/registry measurements—not an organizer score. The full run card records `organizer_confirmed: null` and zero slots spent.

## H33 and leaderboard interpretation

H33's `0.2778` in the user-provided GEMSDOE32 record remains **USER-REPORTED**, not receipt-authenticated in this checkout. The local pixel forensics describe a nested thinning lineage: H19-5 → D2.8 → SOLO → H33. H33 removes 6,436 D2.8 dots near mapped faults while preserving off-catalogue support. Because DTI penalizes false-positive mass, this geometry provides a plausible reason for a stronger reported score; it does not establish causality or guarantee a new raster will score better. KTH-88's hide-and-recover result is poor and cannot be represented as a public leaderboard result.

The prompt's `0.3195` “current high” conflicts with the dated official public-leaderboard snapshot stored in `docs/data/leaderboard.json`: it records `0.4413` at `2026-10-24T07:19:00Z`. This snapshot is not live and cannot prove today's standings after its timestamp. The public leader's number is not a score for any GEMSDOE88 raster. No candidate can be claimed to beat H33 or the public leader without an organizer receipt.

## Three untested geological hypotheses from the frozen KTH-88 preregistration

The lane's preregistration ranks four hypotheses. Rank 1, KTH-ANTISYMMETRIC-STEP, was tested once and is negative; after the duplicate the lane stopped. The following **three have not been run**. Their costs and expected gains are qualitative from the preregistration; no numeric prediction is presented as a score.

| Prereg rank | Hypothesis and specific layers | Physical signature and off-catalogue rationale | Named non-fault mimic | How it differs from implemented approaches | Cost / source feasibility |
|---|---|---|---|---|---|
| 2 | **CHI-ACROSS-SLOPE-STEP:** official-source 10 m DEM-derived chi/knickpoint and terrain steep-fraction layers. | Across-strike, elevation-normalized chi sign reversal coherent with knickpoint density; a buried scarp could reorganize catchments beyond mapped mountain-front traces. | Lithologic knickzone or base-level change. | Opposite-flank signed chi across drainage rather than a chi-step maximum or curvature-only feature. | Low computational cost, but needs verified DEM tiles/derivatives. Specific free official source: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). This sandbox cannot reach the source host and no tiles were restored; not currently obtainable here, so not viable until authorized data access and hashes are verified. |
| 3 | **RTP-GRAV-ADMITTANCE:** supplied RTP (competition band 2) and gravity anomaly (band 13). | Spatially varying magnetic-to-gravity gradient admittance jump, normalized by local lithology, could reveal buried basement damage where faults are not traced. | Unfaulted intrusive contact. | Gradient-admittance ratio across strike, distinct from MRR vertical-gradient residual regression and KTH radiometric contrast. | Medium computation; needs no new sensor, but depends on authorized competition feature data, absent locally and login-gated at the [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/). The public mirror manifest flags reuse/redistribution permission as unchecked. Not runnable until authorized inputs are restored. |
| 4 | **U-K-DISEQUILIBRIUM:** USGS GeoDAWN-derived K, U, and Th radiometric bands (K/Th, U/Th) and orientation-consistent 300 m ridge support. | Regional-detrended U/Th vs K/Th discordance may reflect fluid migration along fractures absent from the fault catalogue. | Unfaulted granitic pluton or atmospheric radon residual. | Joint K-and-U disequilibrium step, not K/Th antisymmetric step, radon-piedmont, or generic radiometric count. | Low computation, but requires official raw radiometry/scale metadata. GeoDAWN is the named official [USGS data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) (DOI `10.5066/P93LGLVQ`); the mirrored u8 derivative lacks calibrated elemental units and could not be authenticated to the raw archive here. Do not treat it as viable until source bytes and scale/offset are checked. |

**Selection and stop condition:** these are future-lane candidates only. KTH's registered experiment budget is one; it has been used, and its mandatory uniqueness rule failed. No further KTH experiment or slot is authorized in this review. The next action is input/source authorization and an explicit new-lane preregistration, not silent tuning.

## Source and integrity cautions

- The actual K/Th band values used by KTH-88 are owner-mirrored u8 indices with no physical unit scale/offset metadata. Their ratio is a proxy, not a calibrated elemental abundance ratio; the hydrothermal interpretation remains a hypothesis.
- `registry/data_manifest.json` flags owner mirrors of login-walled competition files with reuse terms unchecked. CI's public mirror restoration verifies hashes but does not establish organizer authentication or redistribution rights.
- The current local checkout omits `data/`; the PR workflow restores validation inputs from the pinned mirror and passed. Full repeatability on a clean, authorized machine still requires restoring the full stack and all registry rasters.
- The user-provided high-score numbers, archived public leaderboard snapshot, sibling-repo scores, model projections, and holdout DTI are different evidence classes. Only a submission-page receipt can supply **ORGANIZER-CONFIRMED** performance.

## Three-pass verification and irregularities

1. **Pass 1 — implementation review:** traced the current top-of-site KTH file, name/note, run card, validation JSON, and registry report; reconciled the repository review to the latest mainline KTH experiment. No new TIFF was emitted.
2. **Pass 2 — tests and edge cases:** local `pytest -q` reports 277 passed, 36 skipped, 0 failed; input-dependent checks skip explicitly when ignored local rasters are absent. The earlier mainline KTH workflow restored hash-pinned validation inputs and passed its pytest, site, KTH validator, readiness, current-release and gate-v3 checks; this branch's additional feed/readiness reconciliation still requires a fresh branch CI run. `python scripts/check_site.py` passes locally. Mirror permissions remain an open data-governance issue despite CI success.
3. **Pass 3 — final request check:** confirmed download is clearly labeled research-only, submit is explicitly blocked, uniqueness fails under the literal overlap threshold, no score is marked ORGANIZER-CONFIRMED, and zero slots were used. No leaderboard score is claimed for the generated KTH file.

### Official links for manual review

- [DrivenData GEMS competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description, metric, and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data page (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [NLR GEMS technical/rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
