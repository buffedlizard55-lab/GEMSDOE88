# GEMSDOE88 — auditable GEMS fault-discovery workbench

> **Submission status: NOT READY — no candidate GeoTIFF is available in this checkout.** Do not download or submit an artifact from this repository. There is no competition data, feature stack, registry raster, holdout evaluator, template writer, or generated TIF here. A score, validation result, or submission-ready claim cannot be made from this checkout.

## Read this brief at the start of every session

The goal is to improve the probability of finding *previously unmapped faults relevant to geothermal systems* in the DOE GEMS competition, while preserving scientific validity and a completely auditable path from data to submission. Build a clean, accessible, self-updating project with a prominent executive summary and an easy-to-download **only-if-validated** single-band GeoTIFF. Never imply that a file is safe to submit until its format, values, holdout evidence, and uniqueness gates all pass.

### Standing rules

1. **Respect the declared experiment lane.** Do not drift into another method. Compare a candidate to available registry rasters before placement and again on the final prediction. Stop and record a negative/duplicate result if Spearman rank correlation exceeds 0.90 or more than 70% of candidate dots lie within 3 pixels of any registry dot set.
2. **Reuse shared tooling.** Use the shared feature cache, hide-and-recover spatially blocked holdout evaluator, and official-format writer when they are present. Withhold whole fault segments plus buffer; derive catalogue-based features only from visible faults; mask visible faults pixel-exactly; score pooled DTI with alpha 0.2, beta 0.8, and a 300 m triangular kernel. Fix shared bugs in the shared implementation, not in private forks.
3. **Do not confuse evidence types.** Every claimed score must be explicitly marked either `HOLDOUT-DTI` (including evaluator version, withheld-positive count, and 95% CI) or `ORGANIZER-CONFIRMED` (with a submission receipt). A projection is not a score. Owner-reported and leaderboard values without receipts are not organizer-confirmed.
4. **Leakage canary.** Score each feature alone on the same holdout before trusting it. AUC above 0.90 is a leakage warning until independently explained.
5. **Promotion gate.** No weekly slot is spent unless a candidate beats the current holdout best and passes the uniqueness and format gates. The slot selector is separate; do not choose a submission in an experiment/build step.
6. **Experiment budget.** Stop at three experiments or two hours, whichever comes first. A negative, well-documented result is a deliverable.
7. **Truthful deliverables.** Never copy a prior submission as a new result. Prior artifacts may be studied for education and auditing only. Never fabricate scores, source verification, downloaded data, or validation.
8. **Own the outcome / maximize P(Win).** Make evidence-led decisions; flag irreproducible claims, data-access gaps, inconsistencies, and anything that should be reviewed.

### Required run card (one JSON object at the end of each experiment report)

`hypothesis`; `mechanism`; `named_non_fault_mimic`; `holdout_dti_and_95ci` (or null with reason); `withheld_positive_count` (or null); `correlation_overlap_vs_registry` (or null with reason); `raster_sha256` (or null); `validator_output` (no NaN inside footprint, values in [0,1], CRS/shape/transform match); `submission_name`; `submission_note` (at most 140 characters); and `verdict` (`promote` or `negative`).

## Current repository inventory and review

The initial checkout contained only this README. In particular, it did **not** contain the requested cached features, `evaluate_holdout.py`, `submission_writer.py`, competition input rasters, labels, registry rasters, or any TIFF. No new candidate was run, and no submission TIFF was generated. See [the review and research memo](docs/review-and-research.md), the [submission instructions](executive-summary.html), the [status page](index.html), and [`run-card.json`](run-card.json).

The available validation command is deliberately a *format gate*, not a model or holdout evaluator:

```bash
python -m pip install -r requirements-validation.txt
python scripts/validate_submission.py --prediction CANDIDATE.tif --reference sample_submission.tif
```

It checks one-band GeoTIFF, CRS, dimensions, transform, and finite prediction values in [0,1]. It cannot establish scientific merit, uniqueness, leakage-free holdout performance, or competition acceptance. Those require the missing data and shared evaluator. `sample_submission.tif` must be obtained through the competition data page after authentication; do not create a substitute reference grid.

## Official sources for manual review

These URLs are carried forward from the project brief; external pages were not independently fetched in this environment. Access and current content must be checked before a future scientific claim relies on them.

- [Competition overview and problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition about page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Competition data page (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Competition leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DOE GEMS submission guidance PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN airborne magnetic and radiometric data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GDR / INGENIOUS public data submission](https://gdr.openei.org/submissions/1391)
- [EPSG:32611](https://epsg.io/32611)
- [Tversky index](https://en.wikipedia.org/wiki/Tversky_index) (background only; the competition specification takes precedence)

## Limitations and next step

This checkout cannot train, evaluate, or emit a valid competition raster without the authenticated competition files and the shared project code. The blocker is explicit, not hidden. The next owner action is to provide those authorized inputs into the agreed `data/`/cache locations or restore the shared template repository/code into this project. Then reproduce the official grid, run the shared holdout and leakage canary, test uniqueness against registry rasters, and only then build and validate a candidate. Do not upload anything until the status at the top changes with a reproducible evidence record.
