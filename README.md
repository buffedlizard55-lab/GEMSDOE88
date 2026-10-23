# GEMSDOE88 — DOE GEMS fault-discovery research

> **READ THIS FIRST EVERY SESSION — project operating brief (updated 2026-10-23, Experiment 3 of 3 complete).**
> **OK TO DOWNLOAD a real GeoTIFF for research: YES. OK TO SUBMIT IT INTO THE COMPETITION: NO (`DO NOT SUBMIT`).**
> Experiment 3 of 3 (**STR-88**: 18-channel zero-catalogue multi-physics Hessian crest + spin-2 axial strike consensus + exact-shell 300 m Dinkelbach allocation) raised pooled blocked holdout DTI from **0.0389** (`MGC-88`) to **0.0997 [0.0878, 0.1110]** (**2.56× lift**, unanimous `8/8` fold win) and passed all 18 leakage canaries (`max AUC_sym = 0.5955 <= 0.90`) and all 5 discrete sibling dot-overlap gates (`max = 0.4101 <= 0.70` vs `H33`, `GEMSDOE36`, `GEMSDOE70`, `GEMSDOE73`, `MGC-88`). Automated submission permission remains **NO** because literal overlap against the pinned `17GEMSDOE` universal positive-footprint prior is `1.0000 > 0.70` (`IR-88-01`). Zero weekly slots were spent.
>
> [Download STR-88 research `.tif` (DO NOT SUBMIT)](docs/downloads/gems88-str88-multiphysics-submod-37654-20261023-v1-DO-NOT-SUBMIT.tif) · [one-TIFF `.zip` (DO NOT SUBMIT)](docs/downloads/gems88-str88-multiphysics-submod-37654-20261023-v1-DO-NOT-SUBMIT.zip) · [archived Exp 1 MGC-88 `.tif`](docs/downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif) · [automated executive summary](docs/executive-summary.html) · [machine run card](registry/run_card.json) · [site](https://buffedlizard55-lab.github.io/GEMSDOE88/)

## Permanent user prompt: operational requirements

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

## Executive decision (current primary file — Experiment 3 of 3 `STR-88`)

| Gate | Actual automated result | Source of truth |
|---|---|---|
| Physical file / values | **PASS locally:** single-band `float32`, `EPSG:32611`, `3730×3292`, `100 m`, `nodata=None`, all `12,279,160` cells finite in `{0.0, 1.0}`, `37,654` off-catalogue dots (`min_spacing_px >= 2.85`), `0` outside footprint, `0` on mapped public faults | [STR-88 writer receipt](docs/downloads/gems88-str88-multiphysics-submod-37654-20261023-v1-DO-NOT-SUBMIT.json), [independent validator](scripts/validate_release.py) |
| Holdout (`gems57-pooled-hide-v2`, `n=22,893`) | **STR-88 Dinkelbach (Exp 3, active best):** **HOLDOUT-DTI `0.0997 [0.0878, 0.1110]`** (`8/8` folds won); **STR-88 Spaced** (2-px greedy NMS ablation): **`0.0765 [0.0638, 0.0883]`**; **MGC-88 (Exp 1, archived):** **`0.0389 [0.0262, 0.0523]`** (archived single-run receipt `[0.0264, 0.0532]`); **Raw 3-band control:** **`0.0267 [0.0176, 0.0378]`**; **CGO-88 (Exp 2, falsified):** **`0.0227 [0.0154, 0.0309]`** (pure) / **`0.0230 [0.0162, 0.0308]`** (joint). Paired Δ(STR-88 − MGC-88) = **`+0.0608 [+0.0445, +0.0757]`** (**2.56× lift**); paired Δ(STR-88 − Raw) = **`+0.0729 [+0.0583, +0.0868]`**. | [active holdout receipt](registry/holdout_result.json), [STR-88 full receipt](registry/str88_experiment_receipt.json), [archived MGC-88 receipt](registry/mgc88_holdout_result.json), [CGO-88 & 19-band receipt](registry/cgo88_holdout_and_band19_audit.json). Conditional proxy only, never a leaderboard estimate. |
| Leakage | **PASS:** 18/18 `STR-88` engineered channels `<= 0.5955 <= 0.90` (`topo_grad_300m = 0.5955`, `spin2_mp_persist_400m = 0.5844`, `topo_slope_100m = 0.5659`); 19/19 raw bands `<= 0.5642 <= 0.90`; 7/7 `MGC-88` channels `<= 0.5459 <= 0.90` | [STR-88 canary receipt](registry/leakage_canaries.json), [19-band & CGO-88 receipt](registry/cgo88_holdout_and_band19_audit.json) |
| Registry (`IR-88-01` & `IR-88-06` closed) | **Pre-placement surface (`IR-88-06` prospectively logged):** Spearman `|rho| <= 0.5836 <= 0.90` (`+0.0828` vs `H33`, `+0.0833` vs `GEMSDOE36`, `+0.0691` vs `GEMSDOE70`, `+0.0740` vs `GEMSDOE73`, `+0.0516` vs `MGC-88`, `+0.5836` vs `dense_prior`), with both `positive_support_overlap_3px` and `top_1pct_crest_overlap_3px` explicitly recorded. **Final dots (like-for-like discrete):** **PASS** across all 5 discrete sibling dot fields (`0.4044` vs `H33`, `0.4101` vs `GEMSDOE36`, `0.3439` vs `GEMSDOE70`, `0.3964` vs `GEMSDOE73`, `0.1634` vs `MGC-88`, all `<= 0.70`; `|rho| <= 0.0292`). **Final dots (literal protocol rule):** **FAIL** (`1.0000 > 0.70`) vs `17GEMSDOE` universal positive-footprint witness. | [witness certificate](registry/witness_certificate.json), [preplacement registry](registry/preplacement_registry.json), [final registry](registry/final_registry.json) |
| Portal and slot | **NOT approved (`ok_to_submit: false`, `verdict: "negative"`)**, no organizer-confirmed score, **0 weekly slots used**, **3/3 experiment budget complete**. | [run card](registry/run_card.json), [official leaderboard (2026-10-23 UTC: `#1 xiaofanhu 0.4413`, `#5 cutoff 0.3539`)](docs/data/leaderboard.json) |

- **Active research artifact (`STR-88`, Exp 3):**
  - **Unique name:** `gems88-str88-multiphysics-submod-37654-20261023-v1-DO-NOT-SUBMIT`
  - **Short note (`112/140` chars):** `GEMSDOE88 STR-88 zero-catalogue 18ch Hessian+spin2 HGB + 300m Dinkelbach 37654 dots; research-only DO-NOT-SUBMIT`
  - **TIFF SHA-256:** `f0d23e96105a0930a435172c8d522cebc4e238a5e72e76de25df8bdf5ee476bd` (`144,259` bytes)
  - **ZIP SHA-256:** `b999ac4403e3f7546a3296700d0bad6615d6a0539a3abd04a94b081e9069267a` (`110,778` bytes)
- **Archived Experiment 1 artifact (`MGC-88`):** `docs/downloads/gems88-mgc-crossgradient-37654-20261022-v1-DO-NOT-SUBMIT.tif` (`SHA-256: 3af5d290e7e0f362cd69bc2db416c8e7a2fe25a61189546218169a90e097730b`).

## Why `GEMSDOE32` (`H33`, user-reported `0.2778`) led ~55 older owner runs — and why `0.4413` is higher

The inherited request cites `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` at **0.2778** (user-reported; no DrivenData portal receipt attached). Pixel-level decoding across `D2.8`, `GEMS28-H27-4`, `GEMSDOE32` (`H33`), `GEMSDOE36`, `GEMSDOE70`, `GEMSDOE73`, and `existing_faults.tif` establishes:

1. **Exact 3-step pixel subset ancestry of `H33`:** `D2.8` (`44,090` dots, user-reported `0.2600`) $\to$ `GEMS28-H27-4` (`40,199` dots, $-3,891$ dots at $d \le 1\text{ px}$, `0.2708`) $\to$ `H33` (`37,654` dots, $-2,545$ dots at $1 < d \le 2\text{ px}$, total $-6,436$ at $d \le 2\text{ px}$, `0.2778`). Zero distant dots moved. Under [official DTI](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation) ($\alpha=0.2, \beta=0.8$, $300\text{ m}$ triangular kernel), $TP_w$ takes a **$\max$** within $300\text{ m}$ while $FP_w$ **sums** unmatched prediction mass: binary `{0, 1}` dots spaced at $\approx 2.85\text{ px}$ avoid self-cannibalizing kernel coverage, and deleting $d \le 2\text{ px}$ dots beside already-mapped catalogue segments trims redundant false-positive mass (`1,287.2` denominator units).
2. **Four regimes across ~55 user-reported runs:** (I) Sparse `{0, 1}` kernel-spaced multi-physics dot fields (`0.2478–0.2778`: `GEMSDOE32`, `GEMSDOE36`, `GEMSDOE28`, `GEMSDOE70`); (II) Dense/fractional surfaces (`0.1380` on `17GEMSDOE` due to $0.2\times FP_w$ bloat) or single-family physics (`0.1917` on `GEMSDOE73` pure Blakely–Simpson ridges); (III) Pure catalogue-halo / relay / tip models (`0.0053–0.0294`: `GEMSDOE45`, `57GEMSDOE`, `GEMSDOE69`), which collapse on live because USGS EarthMRI GeoDAWN + 3DEP lidar reveal blind intra-basin fault corridors kilometers from mapped bedrock traces; (IV) Over-thresholded pinpricks (`0.0000–0.0044`, dominated by $0.8\times FN_w$).
3. **Why `H33` plateaued `0.1635` below `#1` (`0.4413`, `#5` prize cutoff `0.3539`):** `H33` still relied heavily on catalogue-proximity weighting (starving blind alluvial basins), scalar gradients (firing on circular volcanic plugs and survey seams), and greedy disk NMS rather than fractional DTI optimization. **STR-88** addresses all three — eliminating catalogue-distance features, cancelling circular plugs via 400 m spin-2 integration, and allocating via exact 6-shell Bernoulli-max Dinkelbach optimization — lifting blocked holdout DTI 2.56× (`0.0389 -> 0.0997`), though live superiority over `0.2778` remains an untested hypothesis without an organizer portal receipt. Full synthesis and 5 ranked untried hypotheses: [`research/candidate-hypotheses-20261023.md`](research/candidate-hypotheses-20261023.md) and [`docs/research.html`](docs/research.html).

## End-to-end workflow (no manual input to project preflight)

Python 3.11+, `< 700 MiB` peak RAM (stream-cached `float32` memmaps), ~2 GB ignored `data/` disk, and outbound access to GitHub/PyPI. All 19 band tags and grid parameters in `data/training_features.tif` match Cell 5 of the official [`drivendataorg/gems-prize-reference-solution`](https://github.com/drivendataorg/gems-prize-reference-solution) notebook byte-for-byte ([verification receipt](evidence/official-reference-band-verification.json)).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/restore_inputs.py                  # pinned grid, 19-band features, dense witness, H33, GEMSDOE36/70/73
.venv/bin/python scripts/run_experiment.py                  # Exp 1 (MGC-88, archived baseline)
.venv/bin/python scripts/evaluate_cgo88.py                  # Exp 2 (CGO-88 falsification & 19-band audit)
.venv/bin/python scripts/run_str88_experiment.py            # Exp 3 (STR-88 18ch Hessian+spin2 + 300m Dinkelbach)
.venv/bin/python scripts/readiness.py                       # updates docs/status.json from independent validator
.venv/bin/python scripts/check_site.py                      # fail-closed HTML/link/DO-NOT-SUBMIT check
.venv/bin/python scripts/validate_release.py                # independent byte/format/ZIP/witness check
.venv/bin/python scripts/validate_release.py --require-submit # exits 2 automatically under IR-88-01
.venv/bin/python -m pytest -q
```

## Sources, provenance, limitations and next steps

- **Verified official sources (`2026-10-23 UTC`):** [DrivenData Problem, Metric & Format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [DrivenData About](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [Public Leaderboard (`#1 xiaofanhu 0.4413`, `#5 cutoff 0.3539`, `#50 SSR floor 0.2817`)](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [NLR Official Rules PDF (`FY26-96647`)](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [Organizer Reference Notebook (`aebe92f7...`)](https://github.com/drivendataorg/gems-prize-reference-solution), [DOE GDR Submission 1391 (`DOI: 10.15121/1881483`, CC BY 4.0)](https://gdr.openei.org/submissions/1391), [USGS GeoDAWN (`DOI: 10.5066/P93LGLVQ`, CC0)](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). Full ledger: [`docs/sources.html`](docs/sources.html).
- **Key limitations blocking live promotion right now:**
  1. **`IR-88-01` (Universal dense-prior overlap contradiction):** `17GEMSDOE`'s continuous probability raster is positive on all `5,167,373` valid footprint pixels, making the literal any-raster 3-px / 70% uniqueness rule mathematically impossible for any nonempty raster. Requires an explicit human protocol update restricting 3-px dot overlap to discrete dot fields (`support < 20%`, while keeping Spearman `|rho| <= 0.90` on all rasters, as already computed in `two_phase_summary`).
  2. **3-of-3 session experiment cap reached:** All three budgeted experiments (`MGC-88`, `CGO-88`, `STR-88`) have been executed cleanly without holdout tuning.
  3. **Known-catalogue holdout vs blind off-catalogue evaluation:** `HOLDOUT-DTI = 0.0997 [0.0878, 0.1110]` evaluates withheld USGS/INGENIOUS quadrants; multi-scale deep U-Net context (e.g., spatial receptive fields of `3–10 km` tracing continuous fault systems across gaps) is likely needed to bridge from ~`0.28` local-kernel/tree models toward the `0.3539–0.4413` prize tier.
  4. **Unauthenticated portal access:** Remaining weekly submission slots and official DrivenData download byte parity require an authenticated participant browser session (never share credentials in chat).
- **Recommended next steps for the next session:**
  1. Have the human selector review [`registry/str88_experiment_receipt.json`](registry/str88_experiment_receipt.json) and decide whether to adopt `two_phase_summary.like_for_like_reading` (`IR-88-01` resolution) for weekly slot eligibility.
  2. In a fresh 3-experiment session budget, test multi-kilometer structural receptive-field architectures (e.g., multi-scale dilated U-Net / directional Radon line-integral operators trained LOQO on the 18 baseline-invariant `STR-88` physical channels + untried Reserve Rank 2 `MRR-88` hydrothermal demagnetization troughs and Reserve Rank 3 `MSDD-88` scarp diffusion ratios) paired with `exact_bernoulli_self_credit` + `dinkelbach_allocate`.
  3. Authenticate `sample_submission.tif` directly from an authorized DrivenData download (`IR-88-02`) before spending any weekly feedback slot.

**Run card:** [JSON](registry/run_card.json) (`docs/run_card.json` / `docs/data/run-card.json`) is the canonical machine evidence (`verdict: "negative"`, `ok_to_download: true`, `ok_to_submit: false`).

<details>
<summary>Verbatim project prompt archive (reference starting brief)</summary>

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
