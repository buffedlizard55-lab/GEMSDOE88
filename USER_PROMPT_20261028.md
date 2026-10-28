# User request recorded for future sessions — 2026-10-28

**Record type: condensed.** This file keeps the operative instructions of the 2026-10-28 request, quoted or closely paraphrased in the user's own terms, and the parallel-run protocol. The long GEMSDOE site-result list and the repeated link blocks are not reproduced. They are recorded as the user's claims in `docs/data/user_reported_results.csv` and in full in `USER_PROMPT_20261027.md`. User-supplied scores are claims, not organizer receipts. This request does not override the binding duplicate-stop rule. Read `README.md`, `PROMPT.md`, `AGENTS.md` first on every session.

## Operative instructions (quoted or closely paraphrased)

1. **Focus sites.** Review GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36. Give each site an executive summary that makes clear which submission to download and submit. Include a table with the file to download, an estimated score, and whether it is unique against the other listed GEMSDOE sites. "We should be able to estimate the score for a submission."
2. **Urgent.** "MUST GENERATE A UNIQUE TIF SUBMISSION … DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION … IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION."
3. **Explain H33.** Explain why GEMSDOE32's `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (user-reported 0.2778) scored highest, and whether a submission above 0.2778 is possible. Verify line by line, with no hallucinations.
4. **Parallel-run protocol** (the user's text, placeholders in brackets as written):
   - *Lane.* "Your lane is the single method paragraph below." (No lane paragraph was supplied; see IR-F9-07.) If the raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of dots fall within 3 px of one registry raster's dots, log a duplicate and stop. Check on the surface before placement and on the final dots.
   - *Reuse.* Use the cached feature stack, `evaluate_holdout.py` and `submission_writer.py`. Holdout is hide-and-recover with buffered whole-fault segments; catalogue features come only from visible faults; pooled DTI with α = 0.2, β = 0.8 and a 300 m triangular kernel. Fix shared tools once in the template; no private forks.
   - *Labels.* Every number must be labelled HOLDOUT-DTI (evaluator version, withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.
   - *Leakage canary.* Each feature alone on the holdout; AUC above [0.90] means leakage until proven otherwise.
   - *Run card.* One JSON card with hypothesis, mechanism, named non-fault mimic, holdout DTI and CI, correlation/overlap, raster SHA-256, validator output, submission name and note (≤140 characters), and verdict (promote or negative).
   - *Budget.* Stop after [3] experiments or [2] hours. Do not choose submissions; promotion is a separate selector step within the weekly cap.
5. **Leaderboard.** Link: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ — the user states "0.4413" as the current GEMSDOE high and "0.3195" as the highest right now. (Checked 2026-10-28: rank 1 = 0.4544; 0.4413 is absent from the top 50; 0.3195 is rank 26. See IR-F9-01/02.)
6. **Hypotheses.** Before implementing, generate 3–5 candidate hypotheses, each naming the layer(s), the physical signature, why it should catch a fault missing from the USGS/INGENIOUS catalogue, and how it differs from the repo. Rank by expected DTI improvement and cost. Validate the top candidate on the spatially blocked holdout before spending a submission slot. Name a free official source if new data is needed, and check it is obtainable.
7. **Verification.** "Work line by line verifying from official verified trusted sources, provide links for manual review … no manual input … flag any irregularities … no hallucinations."
8. **Core values** (Arena): *Maximize P(Win)* and *Own the Outcome*.
9. **README.** Put this prompt into the README and read it every session as the starting point.
10. **Submission site.** The site should generate a TIF that can be downloaded in one click, with an unique name and a short comment. The submission form error "Predicted values must be in range [0, 1]" must be explained and addressed. An executive-summary subpage explains how to submit.
11. **Scientific research.** Deep research into geothermal-vent discovery; store verified knowledge for reuse; find overlooked data sources; be contrarian but grounded.
12. **Pull request.** "Go ahead and create a pull request and then merge the pull request onto the main." Suggest the work still to do and the limitations.

## Session handling

- Branch `arena/557d884e-gemsdoe88` only. No new TIFF was generated (gate `DUPLICATE_STOP`; the protocol says to stop). Results: `research/session-focus9-20261028-review.md`, `registry/session_focus9_20261028_run_card.json`.
- Decisions returned to the owner: gate definition for the dense 17GEMSDOE witness (IR-F9-06), and the lane paragraph (IR-F9-07).
