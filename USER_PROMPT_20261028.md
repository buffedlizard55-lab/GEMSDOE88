# User prompt supplement — 2026-10-28

This is the **session-specific supplement** to the long-form user request embedded in [`README.md`](README.md) and archived in [`USER_PROMPT_20261027.md`](USER_PROMPT_20261027.md). It records the new/updated asks and score claims from the 2026-10-28 message; it is **not represented as a verbatim replay** of the already-archived long prompt. Read all three files at session start.

## Current-session asks and operating constraints

- Review this repository and focus the executive comparison on **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36**. Show the file, score evidence, uniqueness status, and whether it is appropriate to download/submit. Do not describe an unverified score as a forecast or receipt.
- Analyze the reported GEMSDOE32 H33 result (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, user-supplied `0.2778`) and whether a higher score can be demonstrated. Do not copy its raster or claim a causal explanation without controlled evidence.
- The message contains two different claimed “current leaderboard” maxima: **USER-REPORTED CLAIM `0.3195`** and, earlier in the same message, **USER-REPORTED CLAIM `0.4413`**. These are not reconciled here and neither is a receipt for a GEMSDOE88 file. Check an allowed, authoritative live source before presenting either as current.
- Before a new experiment, rank **3–5 untested geological hypotheses**. For each, state the exact layers/bands, physical transform/signature, why it could detect an off-catalogue fault, how it differs from this repository's methods, a named non-fault mimic, relative DTI potential and implementation cost. If new external data are essential, name the free official source and verify availability before calling the idea viable.
- Follow the supplied parallel-run protocol: stay in one assigned method lane; check surface rank correlation before placement and final-dot overlap afterward; stop above `0.90` rank correlation or `0.70` three-pixel overlap with any registry raster. Reuse the cached stack, shared `evaluate_holdout.py`, and shared `submission_writer.py`; hold out whole buffered fault components, derive catalogue features from visible faults only, mask visible labels pixel-exactly, and use pooled DTI (`alpha=0.2`, `beta=0.8`, `300 m` triangular kernel). Test every feature alone for leakage (`AUC > 0.90` is leakage until resolved).
- Label performance only as **HOLDOUT-DTI** with evaluator version, withheld-positive count and 95% CI, or **ORGANIZER-CONFIRMED** copied from a submission-page receipt. A projection is not a score. End a run with a JSON card recording hypothesis, mechanism, named mimic, holdout result/CI, registry correlation/overlap, raster SHA-256, format validator checks, submission name and a note no longer than 140 characters, and `promote` or `negative` verdict. Stop at **3 experiments or 2 hours**; slot selection is separate.
- Make the submit/not-submit decision obvious; explain the submission workflow in the executive guide; perform three review passes; cite official/manual-review sources and expose irregularities; do not require human inspection to perform the project's local validation; make a PR and merge only if verified. Preserve Arena’s stated values **“Maximize P(Win)”** and **“Own the Outcome.”**

## Score claims supplied for the nine focus sites

Every value below is a **USER-REPORTED CLAIM** transcribed from the user's message, not a fresh leaderboard scrape, HOLDOUT-DTI, or ORGANIZER-CONFIRMED receipt. The “additional” figures are retained to avoid silently dropping lower or newer claims; they do not establish which artifact is the current repository winner.

| Site | User-supplied submission names / reported values |
| :--- | :--- |
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` — `0.2477`; `gems24-gvc1-negative-geothermal-lineament-submod-20261025-abe8e51c719d-zeros` — `0.0859` |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` — `0.2600`; `gems25-h66-mgd-flank-sapd3-0-k3p5-20261025-da617550a0e9-zeros` — `0.0742` |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` — `0.2449`; `gems27-h29-hydrothermal-piedmont-celf-20261025-511898747886-allfinite` — `0.2190`; `gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite` — `0.2250` |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` — `0.2710`; `h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan` — `0.2649`; `h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan` — `0.2707`; `h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan` — `0.2708`; `gems28-s18-mxtp-20261025-3e95505c011a-allfinite` — `0.0217`; `gems28-s21-puhgb-20261026-16bbf281ba9b-allfinite` — `0.0206` |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` — `0.2600`; `gems30-MSDB1-edge44090-20261025-e7856ec3f14a` — `0.1462` |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` — `0.2708` |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` — `0.2778` |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` — `0.2632`; `gemsdoe33-s33-seisdil-strain-seismicity-37654-20261026-3463540a7e02-zeros` — `0.0963` |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` — `0.2750`; `gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros` — `0.1647` |

The full prior score list, other repositories and primary/manual-review links remain in [`USER_PROMPT_20261027.md`](USER_PROMPT_20261027.md). This supplement does not convert any user claim into verified performance evidence.
