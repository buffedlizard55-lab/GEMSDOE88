# Active GEMSDOE88 request — 2026-10-29

> **Record status:** This is a complete, scope-preserving restatement of the active request carried into the 2026-10-29 review, not a verbatim transcript. The original full owner prompt is preserved in `USER_PROMPT_20261027.md` and embedded in `README.md`; this file adds the current scope and standing corrections. Read both before each session.

## Goal and requested deliverables

Review the GEMSDOE88 repository. Summarize the highest submissions named for GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. For each site, identify the best historical submission in the supplied evidence, give a defensible score estimate only where the required evidence supports one, and decide uniqueness. Research why the GEMSDOE32 H33 result was reported at 0.2778, while separating measured geometry from unproven causality. Rank 3–5 geological hypotheses by expected benefit and cost, name the actual layers/signature/off-catalogue rationale/non-fault mimic, compare each with implemented code, and check source availability where relevant. Refresh the bounded current feed, update the executive submission guide, preserve this task in the README, complete three review/implementation passes, and prepare a pull request from this branch for `main`.

The desired deliverable is a genuinely new, unique, automated-validation-ready GeoTIFF—but only if the shared project gates authorize it. Do not fabricate a TIFF or call an archived file new. Do not select or spend a weekly competition slot; selection is a separate step.

## Binding evidence and generation protocol

- Never report a leaderboard projection as a score. A performance number must be labeled either `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% confidence interval, or `ORGANIZER-CONFIRMED` with a submission-page receipt. Preserve historical owner/user figures as unverified claims.
- Use the shared preflight and generation guard. If any registry raster has surface rank-correlation greater than 0.90, or more than 70% of the final dots lie within 3 px of its dots, stop. Check surface uniqueness before placement and final-dot uniqueness after placement. Apply the duplicate stop literally; do not invent an exception for a dense prior.
- If the pre-placement gate permits work, reuse cached features and `vendor/gems57` holdout/evaluator/writer tools. Hold out whole fault segments with a buffer; derive catalogue features from visible faults only; mask visible faults pixel-exactly; score pooled DTI with α=0.2, β=0.8, and a 300 m triangular kernel. Fix shared-tool defects upstream, never in a private fork.
- Test every feature alone. Symmetric AUC above 0.90 is leakage until disproven.
- End any experiment with a machine-readable JSON run card recording hypothesis, mechanism, named non-fault mimic, HOLDOUT-DTI and CI, uniqueness, raster SHA-256, validator output, portal name/note (each ≤140 characters), and promote/negative verdict. Negative results are deliverables.
- Stop after at most three experiments or two hours. No weekly-slot selection or spending. Do not begin feature construction, fitting, placement, or TIFF writing before the gate permits it.

## Scope corrections and safety boundaries

- Make `DOWNLOAD FOR RESEARCH` and `OK TO SUBMIT` unmistakably separate. An old file can be linked for research, but never copied or renamed as a new submission.
- The reported portal message “Predicted values must be in range [0, 1]” cannot be attributed without the actual uploaded bytes and receipt.
- The phrase “single method paragraph below” refers to no paragraph present in the available prompt. Do not invent a lane.
- Use trusted/official sources, record provenance and uncertainty, and do not claim fresh access to sources that were not fetched. The current public leaderboard, authenticated organizer data, submission quota, and current portal receipt may remain unknown.
- Keep three passes distinct: (1) requirements and preflight; (2) evidence/source and scientific review; (3) adversarial safety, automated tests, and publication checks. Verify changed code line by line.
- Core values: **Maximize P(Win)** and **Own the Outcome**. Report an unmet requirement plainly instead of generating a cosmetic artifact or overstating a result.

## Stop condition

If the shared preflight returns `DUPLICATE_STOP`, the unique-TIFF objective remains unmet. Record the negative decision and the evidence, do not generate any raster, do not run holdout or place dots, and do not use a private workaround. Any change to a blocking shared policy requires separate authorization and an upstream shared implementation before new candidate work.
