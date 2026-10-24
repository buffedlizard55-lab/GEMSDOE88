# GEMSDOE88 repository review — 2026-10-24

## Executive decision

**Existing research artifact:** `docs/downloads/gems88-mrr-bpr-blockresid-dinkelbach-20261024-v1-DO-NOT-SUBMIT.tif`.

- **OK TO DOWNLOAD FOR RESEARCH: YES** per the saved format-audit receipt and writer/run-card hashes.
- **OK TO SUBMIT: NO — DO NOT SUBMIT.** The file fails both the paired holdout promotion condition and the literal all-raster overlap rule. No weekly slot was used.
- **This review did not generate a new candidate TIFF.** The checkout has no `data/` inputs (they are gitignored); without the official sample/labels/registry and cached feature stack, the required like-for-like holdout, canaries, pre-placement correlation, and final overlap checks cannot be recomputed. Producing a cosmetically changed or guessed raster would violate the protocol.
- **ORGANIZER-CONFIRMED score:** none. Reported public scores and model projections are not organizer receipts.

The current machine-readable evidence is [`registry/run_card.json`](../registry/run_card.json), [`docs/data/current_release.json`](../docs/data/current_release.json), and the bound format audit linked below. The file is a distinct TIFF by SHA/pixels among the 21 locally enumerated registry rasters, but that does **not** pass the user-defined duplicate gate: the 17GEMSDOE witness is positive across every allowed cell, so its measured forward overlap is 1.0. Do not describe this artifact as eligible to submit.

## Results and what they do (and do not) establish

- **HOLDOUT-DTI** `0.1852558211`, 95% CI `[0.1715190223, 0.1999647712]`, 22,893 withheld positives, evaluator `gems57-pooled-hide-v2`.
- Paired recomputed incumbent: `0.1896338558`; paired delta `-0.0043780347`, 95% CI `[-0.0079022116, -0.0006230905]`. The full paired CI is negative, so the preregistered “beat incumbent” rule fails.
- Four MRR features individually passed the leakage threshold: maximum symmetric AUC `0.532607` (threshold 0.90).
- Pre-placement maximum absolute Spearman rho was `0.468709`; final sparse-prior 3-pixel forward overlap was `0.684178`; the binding all-raster result was `1.0` against the all-positive 17GEMSDOE surface.
- Saved format receipt says one float32 band, exact expected grid, finite values in `[0,1]`, with 36,033 binary positive dots. This is a receipt-level verification; because the ignored sample TIFF is absent here, this review did not independently recompute sample-grid equality.

These values are **HOLDOUT-DTI** evidence, not leaderboard scores. No score is ORGANIZER-CONFIRMED.

## H33 score interpretation and leaderboard discrepancy

The local forensic report treats H33 `0.2778` as an **owner-reported claim**, not a receipt-authenticated score. It identifies the documented sequence as a nested thinning/spacing lineage: H19-5 → D2.8 → SOLO → H33, with H33 removing 6,436 dots from D2.8 and the removed support reported within 2 pixels of mapped faults. This is consistent with reducing redundant near-catalogue predictions while retaining broader off-catalogue support; it is not proof that this mechanism caused the reported public score. The holdout evaluator does not reproduce that ranking: its score for H33 is near zero in the saved analysis, an explicit domain-shift warning.

The prompt's `0.3195` “current high” conflicts with the repository's saved `OFFICIAL-PUBLIC-LEADERBOARD-SNAPSHOT`: its source URL is the official DrivenData leaderboard, its timestamp is `2026-10-24T07:19:00Z`, and it records top public DTI `0.4413`. The snapshot is not live and cannot establish the current standings now. The correct action is to show the timestamp/source and let the page label it stale after its configured 24-hour interval, rather than assert either number as live. Neither `0.2778` nor `0.3195` is an organizer receipt for this repository's TIFF.

## Ranked untested hypotheses (cost vs likely gain)

This is a research shortlist, not a claim of validated improvement. No experiment was run in this review. Ranking is based on transfer plausibility, implementation cost, and the negative/diagnostic evidence already in the repository; each must beat the same blocked-holdout incumbent before a selector considers a slot.

| Rank | Hypothesis and layers/signature | Why it could recover off-catalogue faults | Named non-fault mimic | Difference from tested repo methods | Cost / feasibility |
|---|---|---|---|---|---|
| 1 | **Matched-domain FBMT correction (N1):** existing 44-channel competition + external physics stack; isolated-fault training, define both training and allocation domain at visible-fault distance >8 px. | Avoid emitting predictions in the 3–8 px zone excluded from training; tests whether the previous FBMT loss was a train/test support mismatch, not evidence against far-basin transfer. | Lahontan/Bonneville shoreline benches or lithologic contacts that create broad relief/gradient responses. | Previous FBMT used an 8-px unlabeled training zone but allocated from >3 px; this variant changes only the domain mask, unlike MRR's magnetic residual features. | Low; no new data beyond pinned feature/cache inputs. Not runnable in this checkout because inputs are absent. |
| 2 | **Out-of-fold ADHR production (N2/N3):** cached 44-channel physics/topography features and visible catalogue; train quadrant/block OOF models, stitch predictions, then run the shared exact DTI allocator. | Prior audit reports that in-sample production concentrates predictions close to the training catalogue; OOF emissions better match the spatially held-out setting and can generalize to untraced structures. | Range-front relief and erosional scarps without active faulting. | Changes production leakage/transfer design, not the feature family or density objective; addresses the recorded in-sample vs OOF discrepancy. | Medium; requires full cached stack, labels, folds, and exact shared evaluator. Missing locally. |
| 3 | **NDVI spring/phreatophyte lineaments (NDVI-SL):** Sentinel-2 L2A seasonal NDVI/NDWI and detrended vegetation-moisture residual; oriented line-integrals over ≥1.5 km. | Hydrothermal discharge and shallow groundwater along buried faults may produce vegetation/moisture lineaments where LiDAR scarps and potential-field edges are weak. | Irrigation pivots/canals, roads, riparian corridors, playa moisture boundaries. | Adds a hydrologic optical sensor not represented in the existing topographic/potential-field stacks. | High and currently blocked: Sentinel-2 is the specific official free source; registry pointer `https://registry.opendata.aws/sentinel-2-l2a-cogs/` and Copernicus terms `https://dataspace.copernicus.eu/`. This sandbox's outbound allowlist does not permit AWS data hosts, so data obtainability could not be confirmed from this environment; do not start until access/permissions are verified. |
| 4 | **Slip/dilation tendency strike gating (SDT):** fault-strike estimates from existing ridge features plus USGS Great Basin stress/slip-tendency release; apply a resolved regional stress orientation gate. | Favor fault orientations compatible with regional stress where the morphology/geophysics is ambiguous; potentially suppress non-tectonic lineaments and expose subtle compatible structures. | Folded bedding, intrusive contacts, and drainage lineaments that happen to have favored orientation. | Adds stress-kinematic orientation selection rather than another raster evidence stack. | Medium; USGS ScienceBase product is cited in `docs/research/hypotheses-20261024.md` (DOI `10.5066/P9YL58W6` should be checked against current source metadata before use). Its host is outside this sandbox's outbound allowlist, so availability was not independently rechecked here. |

**Source-data caution:** competition sample/labels and external stack files are intentionally not committed; `registry/data_manifest.json` flags owner-mirrored competition content because redistribution permission is unchecked. Official competition entry point (login may be required for download): <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>. Do not treat public mirrors as organizer-authenticated sources.

## Irregularities and prioritized fixes

1. **Stale executive decision block (fixed in this review):** the home page and submission guide previously put LBCAL first while their hero/run card described MRR-BPR-88. Both now show one current candidate and its negative gate.
2. **Machine-readable feed drift (fixed in this review):** `docs/data/current_release.json` described fabric-dislocation while the canonical current run card was MRR-BPR-88. It now carries the current MRR artifact/hash/status and distinct `HOLDOUT-DTI` evidence.
3. **Input-dependent verification:** the full validator and six tests fail locally because ignored `data/bridge`, `data/registry`, and cached sample files are missing. This is a real reproducibility limitation, not a passing validation. CI attempts restoration via public sibling-repository mirrors; the manifest itself flags their redistribution terms as unchecked. Obtain authenticated official files or documented reuse permission before relying on mirrors.
4. **No reliable current score claim:** local leaderboard JSON is timestamped, not live; leaderboard score and H33 claims must remain clearly labeled and linked to the timestamped snapshot/receipt status.
5. **Submission protocol is intentionally gated:** the valid file must not be uploaded; obtaining a higher leaderboard result cannot be inferred from holdout DTI or a model projection.

## Verification record (three passes)

1. **Pass 1 — implementation:** reviewed status/run-card/site links and reconciled README, public page top sections, and machine-readable current-release feed to the canonical MRR card. No new raster was emitted.
2. **Pass 2 — tests and edge cases:** `scripts/check_site.py` passed. After installing declared Python dependencies in ignored `.venv`, local `pytest -q` reported **275 passed, 36 skipped, 0 failed**; the data-dependent tests skip explicitly when ignored TIFFs are absent. All three release/readiness CLIs were checked and return structured blocked status (exit 2) instead of an unhandled traceback without `data/bridge`. Separately, the GitHub Actions PR run **40110821026** completed successfully: hash-pinned validation-input restoration, full pytest step, site audit, readiness, independent current-release audit, gate-v3 audit, and clean generated-file diff all passed. CI uses public sibling-repository mirrors; their redistribution terms remain flagged as unchecked, and the mirrored bytes are not independently organizer-authenticated.
3. **Pass 3 — final request check:** verified the downloadable artifact file, ZIP, current card, name/note and hash are linked; both web pages clearly say download-for-research yes and submit no. Checked the branch remains `arena/ab92461f-gemsdoe88`. No new hypothesis was evaluated and no competition slot was spent.

## Next actions

1. Resolve official competition input access or documented mirror-use permission; restore hash-pinned `sample_submission.tif`, `existing_faults.tif`, full stack and registry witness, then rerun `scripts/validate_release.py` and the tests.
2. In a newly declared method lane, pre-register the matched-domain FBMT test (or explicitly choose a different ranked candidate) and stop at 3 experiments/2 hours. Run feature-alone canaries and both uniqueness phases before placement/artifact publication.
3. Generate a new TIFF only after the experiment passes the full holdout/uniqueness/format gates. Current artifact remains negative and is **not** a substitute.
4. Check the official competition page for current rules and live leaderboard; upload only after separate selector authorization. Record only a portal receipt as ORGANIZER-CONFIRMED.

## Manual-review source links

- [DrivenData competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [NLR GEMS technical/rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN official data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [Sentinel-2 COG public data registry](https://registry.opendata.aws/sentinel-2-l2a-cogs/)
- [USGS ScienceBase DOI 10.5066/P9YL58W6](https://doi.org/10.5066/P9YL58W6)
- [Shared reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
