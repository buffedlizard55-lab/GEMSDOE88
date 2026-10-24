# GEMSDOE88 Standing Operational Prompt & Parallel-Run Protocol

> **Standing instruction:** Re-read this entire prompt at the start of every session before making any changes or running any experiments. Also surfaced at the top of [`README.md`](README.md).

## Operational Mandate & Arena Core Values

Review the GitHub repository carefully. Work on the next steps from the previous sessions first. Put this prompt in the `README.md` file to make sure we re-read this prompt for every session as our operational prompt, and ensure our work reflects **Arena Core Values**:

- **Maximize P(Win):** Bias for action, move with urgency and high agency, embrace calculated risks and pivot fast, pursue truth via rigorous metrics and data, first-principles over consensus, aim high, think big.
- **Own the Outcome:** Act like an owner, extreme ownership, think cross-functionally, deliver results not excuses, elevate the bar, sweat the details, stay gritty, pick up the trash.

### PhD-Level Benchmark Questions (Answered & Updated Each Session)

1. Out of sibling sites `GEMSDOE16`, `GEMSDOE29`, `GEMSDOE31`, `GEMSDOE32`, `GEMSDOE34`, `GEMSDOE35`, `GEMSDOE36`, `GEMSDOE37`, `GEMSDOE40`, why did `GEMSDOE32` score the highest (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`: user-reported `0.2778`)? Answer at a PhD level.
2. Can we beat `0.2778`? And can we beat the live DrivenData public leaderboard high (`0.4413` on `2026-10-24`, superseding the earlier `0.3195` prompt figure)? Answer at a PhD level without hallucinating projections as scores.

### Highest-Urgency Competition Deliverable

- **Highest urgency:** We **MUST** generate a unique `.tif` submission (and single-TIFF `.zip`) for the DrivenData DOE GEMS competition:
  - Competition overview: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/966/>
  - Problem description & metric: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
  - Public leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- Do **not** copy any previous submission except read-only for learning and education. Generate a unique TIF file unlike any raster across `GEMSDOE..GEMSDOE92`.
- Work autonomously with zero manual input; restore/download competition data into `data/` and verify the full `train -> inference -> validate` pipeline works end to end.
- **Portal error prevention (`"Predicted values must be in range [0, 1]"`):** Validate every submission file automatically so all predicted values are strictly finite in `[0, 1]`, no `NaN` occurs inside the active footprint, outside-footprint cells carry finite `0.0` (or sample-compatible values) with no undeclared `NaN` range failure, and CRS (`EPSG:32611`), shape (`3730 x 3292`), and geotransform (`[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]`) match `sample_submission.tif`.

---

## PARALLEL-RUN PROTOCOL (Read Before Writing Code)

You are one of several agents working this competition in parallel. Past runs wasted submissions by rediscovering the same feature blend and reporting optimistic CV numbers. Follow these rules strictly:

1. **LANE.** Stay inside the method family defined for this session. Do not fall back to generic GBDT blending on the default raster stack. If your raster's Spearman rank-correlation with any registry raster exceeds `[0.90]` (checked on the pre-placement score surface), or more than `[70%]` of your dots fall within `3 px` of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check both your score surface before placement AND your final dots.
2. **SHARED TOOLS, NOT REWRITES.** Use the repo's existing holdout evaluator (`vendor/gems57/evaluate_holdout.py`), submission writer (`vendor/gems57/submission_writer.py`), and cached feature stack. Do not write your own metric, splitter, or GeoTIFF writer. If you find a defect in shared code, fix it once in the template — do not keep a private fork. Holdout is **hide-and-recover**: withhold whole fault segments with a buffer, derive every catalogue feature from the remaining faults only, mask those remaining faults pixel-exactly as the organizer does, and score pooled DTI (`alpha=0.2`, `beta=0.8`, `300 m` triangular kernel).
3. **EVIDENCE LABELS.** Label every number either `HOLDOUT-DTI` (give evaluator version, withheld positive count, and `95% CI`) or `ORGANIZER-CONFIRMED` (copied from a submission receipt). Never write a "projected" or "expected" leaderboard score. Do not cite a sibling repo's score unless an organizer receipt is attached.
4. **LEAKAGE CANARY.** Test each feature alone on the holdout first. Anything above `[0.90]` AUC is leakage until proven otherwise — check for distance-to-all-faults or unmasked fault density.
5. **DELIVERABLE.** End with a JSON run card: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation/overlap, raster `sha256`, validator output (no `NaN` inside footprint, values in `[0, 1]`, CRS/shape/transform match), unique submission name and `<=140`-character note, and verdict: `promote` or `negative`. A clean negative result is a valid deliverable; a dressed-up duplicate is not.
6. **BUDGET.** Stop after `[3]` experiments or `[2]` hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

---

## Scientific Method, Validation Gates, Sources & 3-Pass Workflow

1. **Hypothesis Preregistration First:** Before implementing anything, generate and rank **3–5 new candidate geological hypotheses** by expected DTI improvement and implementation cost. For each:
   - Name the specific input layers and exact physical signature/transform;
   - Explain why it catches concealed or unmapped faults missing from the USGS / INGENIOUS fault catalogues;
   - Name the specific **non-fault geological or survey mimic** that could trigger false positives;
   - State explicitly how it differs from everything already tried in `GEMSDOE88` and sibling repos;
   - Verify whether any additional public datasets are freely obtainable from official trusted sources (`USGS`, `DOE GDR`, `NBMG`, `OpenTopography`, `ASF/OPERA`).
2. **Holdout Gate Before Any Slot:** Validate the top candidate on a spatially-blocked holdout before recommending a weekly submission slot. Never spend a weekly slot on an idea that has not beaten the holdout best (or without explicit human selector sign-off on any binding uniqueness/slot policy).
3. **High-Visibility Automated Validation Gates:** Make it immediately obvious at the top of `README.md`, `docs/index.html`, and `docs/executive-summary.html` whether the TIF is **OK to download** and **OK to submit**, backed by automated deterministic scripts with zero manual intervention, plus a unique submission filename and `<=140`-char portal note.
4. **Trusted Sources & Irregularity Log:** Organize all data and literature from verified official trusted sources with working links on `docs/sources.html` and `docs/research.html` for manual review. Flag every data, metric, registry, or claim irregularity in `IRREGULARITIES.md`. Zero hallucinations; verify line by line.
5. **Mandatory 3-Pass Review + PR Merge:**
   - **Pass 1:** Implement the solution end-to-end and verify everything works.
   - **Pass 2:** Review all changes carefully for bugs, missing requirements, frozen-archive test regressions, broken links, or edge cases, and fix everything found.
   - **Pass 3:** Re-check the entire implementation line-by-line against this prompt and fix any remaining issues, then commit cleanly (no large binary caches in git), open a pull request, merge onto `main`, and report remaining work and limitations.
