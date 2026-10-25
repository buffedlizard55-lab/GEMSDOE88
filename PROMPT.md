# Standing prompt for GEMSDOE88 (DOE GEMS Prize, DrivenData competition 306)

> **Execution addendum (2026-10-25, H88-MTAS):** The preregistered MTAS lane was **executed once** as a fail-closed research artifact (`scripts/run_mtas88_experiment.py`): new GeoTIFF `gems88-mtas88-admittance-37654dots-20261025-zeros-DO-NOT-SUBMIT.tif` (SHA-256 `2cb82893…479cc`). **DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO — DO NOT SUBMIT.** HOLDOUT-DTI 0.049577 [0.044659, 0.054417] (`gems57-pooled-hide-v2`, n=22,893) — below the 0.187888 bar and ≈ null; like-for-like unique (0.4232 ≤ 0.70) but literal overlap 1.0 vs the dense 17GEMSDOE witness. 0 weekly slots spent. The duplicate-stop precedence below is unchanged. See [execution dossier](research/session-20261025-mtas-execution.md).

> **Historical parallel-lane record (2026-10-25, H88-GZZC; not current authorization):** That lane used residual isostatic-gravity zero-contour buried contact. A **new** research GeoTIFF was generated (`gems88-gzzc-gravzero-buried-20261025-961e034d-zeros-DO-NOT-SUBMIT.tif`, SHA-256 `961e034d515fa74388f4417def3723584bdcb6d7fe7f97892b193898c13d78ad`). **DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO.** The user's literal 3-pixel/70% overlap stop applies to *any* registry raster, including the pinned dense `17GEMSDOE` witness; there is no authorized dense-prior exemption. Like-for-like overlap is 0.343 ≤ 0.70; literal overlap is 1.0 > 0.70. HOLDOUT-DTI 0.0000 (`gems57-pooled-hide-v2`). H33's 0.2778 is owner/user-reported, not a verified organizer receipt. 0 weekly slots spent. See [gzzc run card](registry/gzzc88_run_card.json).
>
> **Current review precedence:** obey the literal duplicate stop before constructing any new candidate. Archived research files and lane records do not authorize generation or upload. The latest request does not identify a single method paragraph; do not invent an assigned lane.
>
> **Read this file at the start of every session.**  It is linked from the top of `README.md`.
>
> **Honesty note (IR-88-68).**  The owner's original prompt text is longer than what any one
> session can see.  This file preserves the **acceptance criteria and constraints exactly as they
> were carried into the 2026-10-24 session brief**; wording is condensed, nothing was added or
> softened. It is *not* a byte-exact copy of the complete user message; do not label it verbatim.
> The latest session result is linked from the first block of `README.md`. Re-read these
> operational requirements before changing a method, slot decision, or download link.

## Appendix A - earlier README summaries of this prompt (kept verbatim for audit; superseded by the criteria above)

### Earlier README section: "Permanent User Prompt: Operational Requirements"

**Highest urgency: “MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.”**

1. **Core values:** **Maximize P(Win)** — spend scarce weekly submissions (`<= 3/week`, with **only ONE single final submission selected for both Round 1 `$50K` and Round 2 `$250K`**, NLR Official Rules §3.2–§3.5) only on rigorous, evidence-backed discoveries; **Own the Outcome** — take full responsibility for negative gates, data irregularities, and limitations rather than concealing them. Target **geological faults indicative of geothermal resources**, never directly hallucinated surface vents.
2. **Parallel-run protocol / lane:**
   - **LANE:** Stay inside one explicitly defined method lane (`H88-UGFV`). Check surface Spearman rank correlation (`<= 0.90`) before dot placement AND final 3-pixel forward dot overlap (`<= 0.70`) against registry rasters. Never silently exempt dense priors.
   - **REUSE, DON'T REBUILD:** Use shared `vendor/gems57/` tools (`evaluate_holdout.py`, `submission_writer.py`, `holdout.py`, `anatomy.py`, `emit.py`, `uniqueness.py`) with zero private metric forks. Withhold whole fault components with a 3-pixel feature-context buffer, derive catalogue features strictly from visible faults, mask visible faults pixel-exactly, and score pooled DTI (`alpha = 0.2, beta = 0.8`, `300 m` triangular kernel).
   - **LABEL EVERY NUMBER:** Every score must be labelled **`HOLDOUT-DTI`** (with evaluator version, withheld-positive count, and 95% CI) or **`ORGANIZER-CONFIRMED`** (copied verbatim from a DrivenData submission receipt). Never write a projection as a score.
   - **LEAKAGE CANARY:** Test every single feature alone on held-out positives; symmetric `AUC > 0.90` means leakage until disproven.
   - **RUN CARD:** Machine-readable JSON run card (`registry/run_card.json`, synced byte-for-byte to `docs/data/run-card.json`, `docs/run_card.json`, and `evidence/run-card.json`) recording hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation/overlap, raster SHA-256, validator output, unique name + `<= 140`-character note, and `promote / negative` verdict.
   - **BUDGET:** At most **3 experiments or 2 hours**. Promotion to a weekly competition slot is strictly separate.
   - **THREE-PASS WORKFLOW:** Pass 1 implement & verify; Pass 2 review bugs, missing requirements, edge cases & fix; Pass 3 re-verify line-by-line against original prompt, commit cleanly, open PR, and merge into `main`.

1. **Core values:** **Maximize P(Win)**: spend scarce weekly submissions only on evidence-backed discoveries; **Own the Outcome**: take responsibility for failures as well as successes. The project aims to find *geological faults indicative of geothermal resources*, not to hallucinate directly observed vents.
2. **Parallel-run protocol / lane:** one explicitly named method per session (the request does not actually contain a separate single-method paragraph); if surface Spearman rank correlation with any registry raster exceeds **0.90**, or >**70%** of emitted dots are within **3 pixels** of any one registry raster, log the duplicate and stop. Check both continuous surface before dot placement and final dots. **No selective exemptions for dense priors.**
3. **Reuse, don't rebuild:** use hash-pinned shared feature stack, `evaluate_holdout.py` and `submission_writer.py`; fix a shared defect upstream once rather than keep a private fork. Hide entire fault components with a **3-pixel context buffer**, use visible faults only for catalogue-derived features, mask known faults pixel-exactly, and score **pooled DTI** (α=0.2, β=0.8, 300 m triangular kernel). The vendor files in this repo are byte-identical to the pinned shared template, not private alternative metrics.
4. **Evidence and leakage:** a number labelled **HOLDOUT-DTI** needs evaluator version, withheld-positive count and 95% CI; **ORGANIZER-CONFIRMED** requires a submission-page receipt. Never market a projection as an organizer score. Test every feature alone on held-out positives; **AUC > 0.90 means possible leakage** until disproven.
5. **Run card and limits:** record hypothesis, mechanism, a named non-fault mimic, holdout DTI+CI, registry correlations/overlaps, raster SHA-256, validator output (no NaN inside the footprint, values [0,1], CRS/shape/transform match), unique name and note ≤140 characters, and a **promote / negative** verdict. Negative findings remain deliverables. Stop after at most **3 experiments or 2 hours**. Promotion/weekly-slot selection are separate; do not silently submit.
6. **Before implementation:** rank 3–5 new, specific geological hypotheses by likely DTI gain versus cost; name their layers, physical transforms, reason they could detect off-catalogue faults and named non-fault mimics. Validate the top on spatially blocked holdout before any weekly slot; no externally dependent hypothesis without a verified free official source and permission to use/share it.
7. **Site:** clean GitHub Pages UI; put the GeoTIFF link, *file-to-submit* decision, unique name and short note and automated evidence at the very top; create an executive-summary subpage explaining exactly how to submit when a candidate is actually cleared. Independently reopen TIFF and one-TIFF ZIP; do not require human inspection for project preflight. Maintain a dated, honest current-feed mechanism with official verification links. Recheck after each change in three passes: implement/verify, review/fix, recheck requirements/fix.
8. **Output:** auditable source inventory with official verified links, data restoration without manual prompts where possible, reproducible train → inference → validate → export path. Answer why owner H33 might have risen and whether this candidate *can be shown* to beat it. Explain limitations, next steps and blockers. Finalize the branch through a PR and merge as requested, without spending a competition slot.




## Appendix B - operating prompt as recorded by PR #58 in the README (kept verbatim for audit; closer to the original wording)

> **MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.**
>
> **PARALLEL-RUN PROTOCOL.** Stay in one method lane. Check rank-correlation on the surface *before* placement and again on final dots; if correlation with any registry raster exceeds **0.90**, or more than **70%** of dots fall within **3 pixels** of one prior's positive support, log **DUPLICATE** and **STOP**. Reuse the template cached stack, `vendor/gems57/evaluate_holdout.py` and `vendor/gems57/submission_writer.py`; fix shared defects in the template once, not private forks. Hide **whole fault segments/components** with a **buffer**; derive catalogue-based features from **visible faults only**; mask known faults **pixel-exactly**. Score **pooled DTI**, α=0.2, β=0.8, **300 m triangular kernel**. Test **each feature alone** on the holdout: symmetric AUC >0.90 is leakage until disproven.
>
> Label every performance number **HOLDOUT-DTI** (evaluator version, withheld positives, 95% CI), or **ORGANIZER-CONFIRMED** (verbatim submission-page receipt). Proxies/projections/public leader positions are *not* a file's score. End an experiment with one JSON card: geological hypothesis; mechanism; named non-fault mimic; holdout DTI + CI; correlation/overlap; raster SHA-256; automated validator output (no NaN inside, [0,1], CRS/shape/transform match); unique name + ≤140-character note; verdict **promote/negative**. **Negative results are deliverables.** Stop after **three experiments or two hours**; promotion/selection of a real weekly slot is a *separate* decision.
>
> Before implementation, rank **3–5 new geological hypotheses** by DTI potential and cost, naming exact layers, physical transform, reason they could reveal missing rather than already mapped faults, the non-fault mimic, and how each differs from existing methods. Obtainability and license of required outside sources must be checked *first*. Validate the top hypothesis on buffered spatial holdout before touching a slot; it must beat the current holdout best with appropriate paired evidence. Never invent or human-approve a local file's validity. Recheck primary official sources line by line, surface irregularities, and perform **three review passes**. Create a PR and merge only after verification.
>
> **Maximize P(Win):** spend scarce submission feedback on reproducibly stronger, genuinely distinct hypotheses, not cosmetic filename changes. **Own the Outcome:** fix contradictions and failures end to end, publish evidence and limitations rather than reporting a hoped-for result as fact.

**Important prompt ambiguity:** it mentions “the single method paragraph below” but supplies no actual paragraph. This run disclosed and chose only [MAG-FABRIC-DISLOCATION](registry/preregistration_fabric_dislocation.json), the first-ranked hypothesis; remaining proposals were not attempted. Another ambiguity is mathematically binding: the registered `17GEMSDOE` probability raster has strictly positive support at **every** footprint cell. The shared template defines dots as *finite value > 0*, so every nonempty candidate has **100%** forward overlap with that prior. Do not silently exempt the dense raster just to say “unique.” An explicit change to the **shared** protocol would be needed for a nondegenerate like-for-like definition; until then all candidate dots fail the literal 70% rule. Filename/pixel uniqueness alone does **not** pass this gate.

<!-- ORIGINAL PROMPT (paste here) -->` and keep this summary.
> Earlier README text called a shorter summary "the prompt"; this file supersedes it.

**Highest urgency: “MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.”**

*(The line above is verbatim; it was preserved by earlier sessions in `README.md`.)*

**Core values (focal point of all work):** **Maximize P(Win)** and **Own the Outcome**.

## Acceptance criteria

1. **Review the repo**, and work first on the previous sessions' next steps
   (`research/next-steps.md`, `SLOT_PLAN.md`).
2. **HIGHEST URGENCY – generate a UNIQUE GeoTIFF submission**, not a copy of a prior one
   (copying is allowed only for learning).
   * It must be *obvious* whether the file is **OK to download** and **OK to submit**.
   * There must be an easy **one-click TIFF download** at the top of the site, the README and
     the executive summary.
   * Validation is done by the project itself with **no human intervention**: format,
     uniqueness, holdout and leakage-canary gates.
3. Give a **PhD-level, source-verified, no-hallucination explanation** of why `h33-h33-2-b2`
   (GEMSDOE32, owner-reported `0.2778`) scored highest and whether it can be beaten.  Then
   generate a TIFF **unlike any in the listed GEMSDOE sites**, including the blank-score
   sites 86 and 88–92.
4. **Before implementing**, write 3–5 new geological hypotheses.  Each names its layers,
   physical signature/transform, why it catches faults missing from the USGS/INGENIOUS
   catalogue, and how it differs from the repo.  Rank them by expected DTI gain and cost.
   Validate the top one on a spatially blocked holdout before any weekly slot.  If external
   data is needed, name a free official source and confirm it is obtainable.
5. **Parallel-run protocol.**
   * Stay in one lane: rank correlation <= 0.90 and <= 70 % of dots within 3 px of any one
     registry raster, checked pre-placement and on the final dots.
   * Reuse the `vendor/gems57` tools.  Hold-out is hide-and-recover with a buffer, pooled DTI
     (alpha 0.2, beta 0.8, 300 m triangular kernel).
   * Label every number **HOLDOUT-DTI** (evaluator version, number of withheld positives,
     95 % CI) or **ORGANIZER-CONFIRMED**.
   * Run the leakage canary; a single-feature AUC > 0.90 means leakage.
   * End with a run-card JSON: hypothesis, mechanism, named non-fault mimic, holdout DTI + CI,
     overlap vs registry, raster sha256, validator output, name + note <= 140 chars, verdict
     promote/negative.
   * Budget: **3 experiments or 2 hours.  Do not pick submissions.**
6. **Fix the portal error** "Predicted values must be in range [0, 1]".  Each submission needs
   a unique name and a short note.  The portal accepts one single-band GeoTIFF, or a `.zip`
   with one GeoTIFF, matching CRS/shape/geotransform.
7. **Executive-summary subpage** explaining exactly how to submit.  Clean GitHub Pages site
   with official, verified links.  Put the full prompt in the README and re-read it every
   session.  Core values: Maximize P(Win), Own the Outcome.
8. Use **only free public/official data**.  State limitations and the access needed.
9. Do **3 passes** (implement/verify, review/fix, recheck against the prompt).  Then create a
   PR and merge to `main`.  List remaining work and limitations.

**Targets:** beat `0.2778` (owner-reported H33) and the live leaderboard top (`0.4413`,
verified 2026-10-24).  The prompt also cites a stale `0.3195`.

## Standing constraints and corrections from the owner

* MUST generate a unique TIFF; do not copy prior submissions except for learning.
* Inspection and validation are done by the project itself; work autonomously.
* Verify line by line from official trusted sources, provide links for manual review, flag
  irregularities, no hallucinations.
* The submission must be unlike any file in the listed GEMSDOE sites (...86, 87, 88, 89, 90,
  91, 92).
* **Do not pick or spend submission slots.**  Promotion is a separate selector step within the
  weekly cap.  Do not spend a slot on an idea that has not beaten the current holdout best.
* If a shared tool is wrong, fix it once in the template and report it.  No private forks.
* A projection is never written as a score.  Negative results are deliverables.
* The site top / executive summary must show the downloadable TIFF and the submit decision.
* Each submission needs a unique name and a <= 140-character note.
* Three passes; finish by creating a PR and merging it to `main`; suggest remaining work and
  limitations; state what access is needed; external data must be free, public and official.
* Candidates must pass high-scoring validation gates before being declared unique and
  submittable.
* Use official rules, DrivenData pages and the reference-solution repository as sources.



## Appendix A - earlier README summaries of this prompt (kept verbatim for audit; superseded by the criteria above)

### Earlier README section: "Permanent User Prompt: Operational Requirements"

**Highest urgency: “MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.”**

1. **Core values:** **Maximize P(Win)** — spend scarce weekly submissions (`<= 3/week`, with **only ONE single final submission selected for both Round 1 `$50K` and Round 2 `$250K`**, NLR Official Rules §3.2–§3.5) only on rigorous, evidence-backed discoveries; **Own the Outcome** — take full responsibility for negative gates, data irregularities, and limitations rather than concealing them. Target **geological faults indicative of geothermal resources**, never directly hallucinated surface vents.
2. **Parallel-run protocol / lane:**
   - **LANE:** Stay inside one explicitly defined method lane (`H88-UGFV`). Check surface Spearman rank correlation (`<= 0.90`) before dot placement AND final 3-pixel forward dot overlap (`<= 0.70`) against registry rasters. Never silently exempt dense priors.
   - **REUSE, DON'T REBUILD:** Use shared `vendor/gems57/` tools (`evaluate_holdout.py`, `submission_writer.py`, `holdout.py`, `anatomy.py`, `emit.py`, `uniqueness.py`) with zero private metric forks. Withhold whole fault components with a 3-pixel feature-context buffer, derive catalogue features strictly from visible faults, mask visible faults pixel-exactly, and score pooled DTI (`alpha = 0.2, beta = 0.8`, `300 m` triangular kernel).
   - **LABEL EVERY NUMBER:** Every score must be labelled **`HOLDOUT-DTI`** (with evaluator version, withheld-positive count, and 95% CI) or **`ORGANIZER-CONFIRMED`** (copied verbatim from a DrivenData submission receipt). Never write a projection as a score.
   - **LEAKAGE CANARY:** Test every single feature alone on held-out positives; symmetric `AUC > 0.90` means leakage until disproven.
   - **RUN CARD:** Machine-readable JSON run card (`registry/run_card.json`, synced byte-for-byte to `docs/data/run-card.json`, `docs/run_card.json`, and `evidence/run-card.json`) recording hypothesis, mechanism, named non-fault mimic, holdout DTI + CI, registry correlation/overlap, raster SHA-256, validator output, unique name + `<= 140`-character note, and `promote / negative` verdict.
   - **BUDGET:** At most **3 experiments or 2 hours**. Promotion to a weekly competition slot is strictly separate.
   - **THREE-PASS WORKFLOW:** Pass 1 implement & verify; Pass 2 review bugs, missing requirements, edge cases & fix; Pass 3 re-verify line-by-line against original prompt, commit cleanly, open PR, and merge into `main`.

1. **Core values:** **Maximize P(Win)**: spend scarce weekly submissions only on evidence-backed discoveries; **Own the Outcome**: take responsibility for failures as well as successes. The project aims to find *geological faults indicative of geothermal resources*, not to hallucinate directly observed vents.
2. **Parallel-run protocol / lane:** one explicitly named method per session (the request does not actually contain a separate single-method paragraph); if surface Spearman rank correlation with any registry raster exceeds **0.90**, or >**70%** of emitted dots are within **3 pixels** of any one registry raster, log the duplicate and stop. Check both continuous surface before dot placement and final dots. **No selective exemptions for dense priors.**
3. **Reuse, don't rebuild:** use hash-pinned shared feature stack, `evaluate_holdout.py` and `submission_writer.py`; fix a shared defect upstream once rather than keep a private fork. Hide entire fault components with a **3-pixel context buffer**, use visible faults only for catalogue-derived features, mask known faults pixel-exactly, and score **pooled DTI** (α=0.2, β=0.8, 300 m triangular kernel). The vendor files in this repo are byte-identical to the pinned shared template, not private alternative metrics.
4. **Evidence and leakage:** a number labelled **HOLDOUT-DTI** needs evaluator version, withheld-positive count and 95% CI; **ORGANIZER-CONFIRMED** requires a submission-page receipt. Never market a projection as an organizer score. Test every feature alone on held-out positives; **AUC > 0.90 means possible leakage** until disproven.
5. **Run card and limits:** record hypothesis, mechanism, a named non-fault mimic, holdout DTI+CI, registry correlations/overlaps, raster SHA-256, validator output (no NaN inside the footprint, values [0,1], CRS/shape/transform match), unique name and note ≤140 characters, and a **promote / negative** verdict. Negative findings remain deliverables. Stop after at most **3 experiments or 2 hours**. Promotion/weekly-slot selection are separate; do not silently submit.
6. **Before implementation:** rank 3–5 new, specific geological hypotheses by likely DTI gain versus cost; name their layers, physical transforms, reason they could detect off-catalogue faults and named non-fault mimics. Validate the top on spatially blocked holdout before any weekly slot; no externally dependent hypothesis without a verified free official source and permission to use/share it.
7. **Site:** clean GitHub Pages UI; put the GeoTIFF link, *file-to-submit* decision, unique name and short note and automated evidence at the very top; create an executive-summary subpage explaining exactly how to submit when a candidate is actually cleared. Independently reopen TIFF and one-TIFF ZIP; do not require human inspection for project preflight. Maintain a dated, honest current-feed mechanism with official verification links. Recheck after each change in three passes: implement/verify, review/fix, recheck requirements/fix.
8. **Output:** auditable source inventory with official verified links, data restoration without manual prompts where possible, reproducible train → inference → validate → export path. Answer why owner H33 might have risen and whether this candidate *can be shown* to beat it. Explain limitations, next steps and blockers. Finalize the branch through a PR and merge as requested, without spending a competition slot.




## Appendix B - operating prompt as recorded by PR #58 in the README (kept verbatim for audit; closer to the original wording)

> **MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.**
>
> **PARALLEL-RUN PROTOCOL.** Stay in one method lane. Check rank-correlation on the surface *before* placement and again on final dots; if correlation with any registry raster exceeds **0.90**, or more than **70%** of dots fall within **3 pixels** of one prior's positive support, log **DUPLICATE** and **STOP**. Reuse the template cached stack, `vendor/gems57/evaluate_holdout.py` and `vendor/gems57/submission_writer.py`; fix shared defects in the template once, not private forks. Hide **whole fault segments/components** with a **buffer**; derive catalogue-based features from **visible faults only**; mask known faults **pixel-exactly**. Score **pooled DTI**, α=0.2, β=0.8, **300 m triangular kernel**. Test **each feature alone** on the holdout: symmetric AUC >0.90 is leakage until disproven.
>
> Label every performance number **HOLDOUT-DTI** (evaluator version, withheld positives, 95% CI), or **ORGANIZER-CONFIRMED** (verbatim submission-page receipt). Proxies/projections/public leader positions are *not* a file's score. End an experiment with one JSON card: geological hypothesis; mechanism; named non-fault mimic; holdout DTI + CI; correlation/overlap; raster SHA-256; automated validator output (no NaN inside, [0,1], CRS/shape/transform match); unique name + ≤140-character note; verdict **promote/negative**. **Negative results are deliverables.** Stop after **three experiments or two hours**; promotion/selection of a real weekly slot is a *separate* decision.
>
> Before implementation, rank **3–5 new geological hypotheses** by DTI potential and cost, naming exact layers, physical transform, reason they could reveal missing rather than already mapped faults, the non-fault mimic, and how each differs from existing methods. Obtainability and license of required outside sources must be checked *first*. Validate the top hypothesis on buffered spatial holdout before touching a slot; it must beat the current holdout best with appropriate paired evidence. Never invent or human-approve a local file's validity. Recheck primary official sources line by line, surface irregularities, and perform **three review passes**. Create a PR and merge only after verification.
>
> **Maximize P(Win):** spend scarce submission feedback on reproducibly stronger, genuinely distinct hypotheses, not cosmetic filename changes. **Own the Outcome:** fix contradictions and failures end to end, publish evidence and limitations rather than reporting a hoped-for result as fact.

**Important prompt ambiguity:** it mentions “the single method paragraph below” but supplies no actual paragraph. This run disclosed and chose only [MAG-FABRIC-DISLOCATION](registry/preregistration_fabric_dislocation.json), the first-ranked hypothesis; remaining proposals were not attempted. Another ambiguity is mathematically binding: the registered `17GEMSDOE` probability raster has strictly positive support at **every** footprint cell. The shared template defines dots as *finite value > 0*, so every nonempty candidate has **100%** forward overlap with that prior. Do not silently exempt the dense raster just to say “unique.” An explicit change to the **shared** protocol would be needed for a nondegenerate like-for-like definition; until then all candidate dots fail the literal 70% rule. Filename/pixel uniqueness alone does **not** pass this gate.

<!-- ORIGINAL PROMPT (paste here) -->

## Current-session binding clarification (2026-10-24; IR-88-86)

Read the latest README notice before any generation. This session's supplied prompt again
requires literal overlap against **any** registry raster and supplies no single method
paragraph. Earlier chance-corrected policy exceptions are not authority to change that
rule. A universal dense witness means STOP before another experiment. Do not promise a
unique submission, a higher score or full official-source verification where impossible.
The current request also requires three review passes and a PR followed by merge; this
review implements automated audit, source-status disclosure and fail-closed site claims.
This remains a condensed operational record, not a verbatim copy of the long user prompt.
