# GEMSDOE88 — DOE GEMS fault-discovery research

> **READ THIS FIRST EVERY SESSION — project operating brief.**
> **OK TO DOWNLOAD a real GeoTIFF for research: YES. OK TO SUBMIT IT INTO THE COMPETITION: NO.**
> It passes automatic local format validation but **fails the user's literal registry uniqueness rule**. The experiment's scientific verdict is **negative**. No weekly slot was spent. There is no organizer receipt for this file.
>
> [Download research-only `.tif` (DO NOT SUBMIT)](docs/downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif) · [one-TIFF `.zip` (DO NOT SUBMIT)](docs/downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.zip) · [automated executive summary](docs/executive-summary.html) · [machine run card](registry/run_card.json) · [three-pass repo review (2026-10-23)](research/review-20261023.md) · [site](https://buffedlizard55-lab.github.io/GEMSDOE88/)

## Permanent user prompt: operational requirements (read before every session)

**Highest urgency: “MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.”**

Other binding parts of the project request (retained as the starting brief, not silently discarded):

1. **Core values:** **Maximize P(Win)**: spend scarce weekly submissions only on evidence-backed discoveries; **Own the Outcome**: take responsibility for failures as well as successes. The project aims to find *geological faults indicative of geothermal resources*, not to hallucinate directly observed vents.
2. **Parallel-run protocol / lane:** one explicitly named method per session (the request does not actually contain a separate single-method paragraph); if surface Spearman rank correlation with any registry raster exceeds **0.90**, or >**70%** of emitted dots are within **3 pixels** of any one registry raster, log the duplicate and stop. Check both continuous surface before dot placement and final dots. **No selective exemptions for dense priors.**
3. **Reuse, don't rebuild:** use hash-pinned shared feature stack, `evaluate_holdout.py` and `submission_writer.py`; fix a shared defect upstream once rather than keep a private fork. Hide entire fault components with a **3-pixel context buffer**, use visible faults only for catalogue-derived features, mask known faults pixel-exactly, and score **pooled DTI** (α=0.2, β=0.8, 300 m triangular kernel). The vendor files in this repo are byte-identical to the pinned shared template, not private alternative metrics.
4. **Evidence and leakage:** a number labelled **HOLDOUT-DTI** needs evaluator version, withheld-positive count and 95% CI; **ORGANIZER-CONFIRMED** requires a submission-page receipt. Never market a projection as an organizer score. Test every feature alone on held-out positives; **AUC > 0.90 means possible leakage** until disproven.
5. **Run card and limits:** record hypothesis, mechanism, a named non-fault mimic, holdout DTI+CI, registry correlations/overlaps, raster SHA-256, automated validation (no NaN inside the footprint, values [0,1], CRS/shape/transform match), unique name and note ≤140 characters, and a **promote / negative** verdict. Negative findings remain deliverables. Stop after at most **3 experiments or 2 hours**. Promotion/weekly-slot selection are separate; do not silently submit.
6. **Before implementation:** rank 3–5 new, specific geological hypotheses by likely DTI gain versus cost; name their layers, physical transforms, reason they could detect off-catalogue faults and named non-fault mimics. Validate the top on spatially blocked holdout before any weekly slot; no externally dependent hypothesis without a verified free official source and permission to use/share it.
7. **Site:** clean GitHub Pages UI; put the GeoTIFF link, *file-to-submit* decision, unique name and short note and automated evidence at the very top; create an executive-summary subpage explaining exactly how to submit when a candidate is actually cleared. Independently reopen TIFF and one-TIFF ZIP; do not require human inspection for project preflight. Maintain a dated, honest current-feed mechanism with official verification links. Recheck after each change in three passes: implement/verify, review/fix, recheck requirements/fix.
8. **Output:** auditable source inventory with official verified links, data restoration without manual prompts where possible, reproducible train → inference → validate → export path. Answer why owner H33 might have risen and whether this candidate *can be shown* to beat it. Explain limitations, next steps and blockers. Finalize the branch through a PR and merge as requested, without spending a competition slot.

**Verbatim parallel-run protocol retained for future sessions (original values):**

> 1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.
>
> 2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.
>
> 3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.
>
> 4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.
>
> 5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.
>
> 6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.
>
> **Three-pass request:** Pass 1 implement and verify; Pass 2 review bugs, missing requirements and edge cases and fix; Pass 3 recheck against the original request, improve reliability and fix anything remaining.

**The original user message also supplied an extensive historical list of GEMSDOE sibling websites and reported numerical scores. These are unverified owner/user reports, *not* organizer receipts; they are research leads, not training targets or authenticated scores.** In particular, [GEMSDOE32 H33](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html), [GEMSDOE70](https://buffedlizard55-lab.github.io/GEMSDOE70/docs/index.html), [GEMSDOE78](https://buffedlizard55-lab.github.io/GEMSDOE78/docs/index.html), and [GEMSDOE80](https://buffedlizard55-lab.github.io/GEMSDOE80/) were checked for methodological context. The official public leaderboard, not the older **0.3195** remark, was headed by **0.4413** at the dated 2026-10-22 check ([official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), **not** a GEMSDOE88 organizer receipt).

**Logical incompatibility, flagged rather than hidden:** the HIGHEST-URGENCY requirement for a *registry-unique and approved* submission cannot be met under the simultaneous literal any-raster overlap rule: the pinned prior from [17GEMSDOE](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif) is positive at **all 5,167,373** valid footprint cells. Hence every nonempty in-footprint raster overlaps it at **100%**, above the mandatory **70%** threshold. Our TIFF is independently generated and byte-/pixel-distinct from H33, but **not unique under the demanded rule**. Downloading for research is okay; submitting is not. We will not invent a green light or exempt that prior without a changed protocol.

## Executive decision (current file)

| Gate | Actual automated result | Source of truth |
|---|---|---|
| Physical file / values | PASS locally: single-band float32, EPSG:32611, 3730×3292, 100 m, no NaN/inf anywhere, all values in [0,1], zeros outside, 0 on mapped public faults | [on-disk receipt](docs/downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.json), [independent validator](scripts/validate_release.py) |
| Holdout | **MGC-88 (Exp 1, incumbent):** **HOLDOUT-DTI 0.0389 [0.0264, 0.0532]**, evaluator `gems57-pooled-hide-v2`, 22,893 withheld positives; matched raw-layer control **HOLDOUT-DTI 0.0267 [0.0173, 0.0372]**, same evaluator/n; paired Δ **+0.0122 [0.0056, 0.0197]**. **CGO-88 (Exp 2, 200 m conductivity-gravity offset):** **HOLDOUT-DTI 0.0227 [0.0154, 0.0309]** (pure) and **0.0230 [0.0162, 0.0308]** (joint), failing to beat MGC-88 (paired Δ **−0.0162 [−0.0281, −0.0073]** pure; **−0.0158 [−0.0286, −0.0061]** joint) | [MGC-88 holdout receipt](registry/holdout_result.json), [CGO-88 & 19-band audit receipt](registry/cgo88_holdout_and_band19_audit.json). Conditional proxy only, never a leaderboard estimate. |
| Leakage | 7/7 MGC-88 features tested (max symmetric AUC 0.5459 < 0.90); all 19 raw bands in `training_features.tif` tested on disk (max symmetric AUC 0.5642 on `det_elev_slope` < 0.90) | [MGC-88 canary receipt](registry/leakage_canaries.json), [19-band & CGO-88 receipt](registry/cgo88_holdout_and_band19_audit.json) |
| Registry | **REGISTRY-MEASUREMENT:** reconstructed MGC-88 surface re-emits a pixel-identical TIFF. Before placement, surface-support overlap = 0.1519 vs H33 and 1.0000 vs dense prior; abs(Spearman ρ)=0.0251 vs H33 and 0.3056 vs dense prior. **Final** 3-px dot overlap = 0.2115 vs H33 and 1.0000 vs dense prior (>0.70). The literal rule blocks submission; no exhaustive sibling-registry scan is claimed. | [surface reconstruction receipt](registry/preplacement_surface_reaudit.json), [witness certificate](registry/witness_certificate.json), [final dots](registry/final_registry.json) |
| Portal and slot | **NOT approved**, no organizer-confirmed score, **0 slots used**. DrivenData's data and submissions pages redirect unauthenticated readers to login. | [run card](registry/run_card.json), [official data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) |

**Unique research artifact name:** `gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT`. **Research note (122/140 chars; not for the portal):** `MGC88 basin-cover RTP/gravity aligned-edge HGB, 2px-spaced 37654 dots; research only: universal overlap gate blocks upload`. **SHA-256:** `3af5d290e7e0f362cd69bc2db416c8e7a2fe25a61189546218169a90e097730b`.

## Why H33 could look strong — and what the evidence does not establish

The supplied prompt reports **0.2778** for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`. Treat that number as **USER-REPORTED, NOT ORGANIZER-CONFIRMED**: at GitHub `GEMSDOE32` main commit [`780a5a534269c79adfe6d1d7d5aadead161332aa`](https://github.com/buffedlizard55-lab/GEMSDOE32/commit/780a5a534269c79adfe6d1d7d5aadead161332aa), its [page source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/docs/index.html) still says `UNSCORED`, and [`registry/submission_build.json`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/registry/submission_build.json) has null score fields plus a **projected** `0.2747` explicitly labelled a model, not a score. A later portal result is possible, but no submission-page receipt was available here; therefore the prompt's number cannot be certified.

We downloaded the versioned owner rasters for *forensic pixel comparison only*; none was reused as the GEMSDOE88 output. H33's 37,654 positive pixels are an exact subset both of the 44,090-dot H25 D2.8 raster ([GEMSDOE32 at the pinned commit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif)) and of the 40,199-dot H27-4 base ([GEMSDOE28 at commit `94b027bed628422b7b39b485cb918a3fc15e5364`](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/94b027bed628422b7b39b485cb918a3fc15e5364/docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif)). Relative to H25 D2.8, exactly **6,436** pixels were removed; relative to H27-4, exactly **2,545** were removed. In both comparisons every removed pixel lies within **2 pixels** of the owner-mirrored known-fault raster, and no retained H33 dot lies within that distance. These pixel facts reproduce the build rule recorded in the pinned H33 manifest; fault geometry is still an owner mirror, not independently organizer-authenticated.

A plausible explanation is *risk-controlled thinning of a strong inherited spatial prior*, not a wholly new geological detector. Under the official DTI formula, removing predicted mass can reduce the unmatched-prediction term, but can also remove kernel credit near genuinely new faults. The net effect depends on hidden labels. That mechanism can explain why a sparse pruned version might improve on its unpruned parent; it does **not** prove that it caused 0.2778. The project's own MGC-88 result is only **HOLDOUT-DTI 0.0389 [0.0264, 0.0532]** (`gems57-pooled-hide-v2`, 22,893 withheld positives), not a live estimate and not comparable to an unverified owner score. We have **not demonstrated** a submission above 0.2778 or the dated public-leaderboard snapshot of 0.4413.

See [scientific analysis, alternative hypotheses and irregularities](docs/research.html) and the [2026-10-23 three-pass repo review](research/review-20261023.md). Beware a sibling H33 write-up's nonuniversal marginal-credit threshold: for a nonredundant unit dot with marginal and self-credit `k` and `α+β=1`, exact algebra gives `k > α × DTI`, not `α × DTI/(1−β × DTI)`.

## End-to-end workflow (no manual input to project preflight)

Python 3.11+, ~1 GB ignored owner-mirror/cache disk, CPU sufficient for this measured run (~84 s here), and outbound access to GitHub/PyPI. Raw owner-mirrored features (~419 MB) and grid are restored automatically; sponsor-authenticated files require the official login. The `data/` directory stays ignored.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/restore_inputs.py               # pinned owner-hosted features, grid, two prior witnesses
.venv/bin/python scripts/run_experiment.py                # refuses existing outputs; clean replay stops at surface-uniqueness gate
.venv/bin/python scripts/evaluate_cgo88.py                # 19-band on-disk audit & CGO-88 blocked holdout comparison
.venv/bin/python scripts/validate_release.py              # independent byte re-read; FORMAT PASS, uniqueness FAIL
.venv/bin/python scripts/validate_release.py --require-submit # exits 2 here: automatic STOP
.venv/bin/python -m pytest -q
```

The tracked TIF is the archived product of the historical completed run. The current runner refuses to overwrite it; a clean replay of the same frozen method now halts before dot placement because the continuous surface fails the literal dense-prior overlap gate. This review deterministically reconstructed that surface and re-emitted a pixel-identical TIF without retuning; see [the surface audit](registry/preplacement_surface_reaudit.json). For any other rerun, use a disposable checkout and remove only that experiment's generated outputs; never touch this repo's `.git` directory. [Input restore pins](scripts/restore_inputs.py), [shared evaluator](vendor/gems57/evaluate_holdout.py), [shared writer](vendor/gems57/submission_writer.py), [automated reviewer](scripts/validate_release.py), [experiment source](scripts/run_experiment.py). The writer rejects invalid prediction values instead of silently clipping. The validator reads the actual saved bytes and independently checks ZIP contents and literal overlap. No human inspector decides status.

[A scheduled Pages workflow](.github/workflows/pages.yml) is configured to publish `docs/` after re-reading the artifact against a pinned grid/witness, testing the code and attempting an official public leaderboard refresh every six hours. If the repository still uses legacy branch-root Pages mode, the root `index.html` safely redirects visitors to `docs/`; live deployment must be checked after merge. When the leaderboard fetch or markup validation fails, the date stays old and the UI marks it **stale**; the workflow does **not** push a different Git branch. CI performs the same tests on pull requests. The current site shows no ready-to-submit file.

**Concurrent-main integration:** three earlier PRs landed while this branch was open. Their pre-experiment “no TIFF” run/status cards were archived; their source dossiers and synthetic gate tests were retained, and both CI suites now use the current negative decision. See the [conflict-resolution audit](research/integration-20261022.md), [historical card](research/pre-experiment-run-card.json) and [template pin lineage](research/previous-template-pin.json). `registry/run_card.json` and its public `docs/run_card.json` mirror are the current evidence, not the older `evidence/run-card.json`.

## Sources, provenance, limits and next steps

- [Competition problem, metric & GeoTIFF requirements](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [About](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [data tab (login required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [NLR official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN CC0 release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution). All were accessed as public guidance on 2026-10-22; the score page and data tab cannot be read unauthenticated. [Full classified source table](docs/sources.html).
- The feature TIFF and sample/fault labels are SHA-pinned copies stored by this **same owner's sibling GitHub repositories**, not independently organizer-authenticated; the sample's nonzero values contradict the public description of a total-absence example. We use only its grid and finite footprint. No extra third-party dataset was trained on, and no external data license beyond the organizer-provided competition inputs was inferred.
- **Next session first:** read this brief, `registry/run_card.json`, and [the 2026-10-23 review](research/review-20261023.md); do not overwrite the current receipts or silently retune this stopped lane. The runner now records rank correlation and positive-support 3-px overlap on the continuous surface before dot placement and refuses to overwrite any existing artifact. Resolve the mathematically impossible literal overlap requirement at the protocol/selector level **only with explicit authorization**, not a hidden exemption. Obtain organizer-authenticated grid/receipts via authorized access if available (never request credentials in chat). Establish a comparable holdout best on identical folds, define an explicitly scoped new lane, update the dated feed, and consider a separate selector only if every automatic gate is green within the portal's current weekly cap. Recheck the sample TIFF semantics against an authorized organizer download.
- A local format PASS is not a guarantee of portal acceptance. The earlier user-reported “Predicted values must be in range [0, 1]” error lacks the original failed file; do not assert its cause. Every published pixel is independently confirmed finite and 0 or 1, and the output has no nodata tag. The site does **not** expose the research TIFF as ready for upload.

**Run card:** [JSON](registry/run_card.json) is the final machine evidence, with a negative verdict. No projection or owner anecdote is labelled an organizer-confirmed score.

<details>
<summary>Core prompt excerpt (not a full verbatim transcript)</summary>

```text
Review the repo.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt. Read the entire prompt. A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.

PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this same prompt.

1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.

2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.

3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.

4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.

5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.

6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:
https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html
h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778
Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?
Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition. Must be unique submission unlike any within the GEMSDOE sites above. Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score: 0.4413

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use. It should solve the problem of having to manually check everything ourselves and having an up to date current feed.

Our Core Values: Maximize P(Win) / Own the Outcome.
Run this task through multiple passes (Pass 1, Pass 2, Pass 3).
Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.
```
</details>
