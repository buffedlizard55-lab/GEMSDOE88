# GEMSDOE88 review — Arena session `2921f3de` (2026-10-29)

> ## Decision: **NO NEW TIFF — DO NOT SUBMIT**
>
> The shared preflight and generation guard were freshly rerun from the restored validation tier. Both return `DUPLICATE_STOP` (exit `2`) before feature construction, fitting, holdout, dot placement, or writing. The SHA-pinned dense witness covers **5,106,385 / 5,106,385 allowed pixels**; under the inherited literal support rule, every nonempty allowed dot set has `REGISTRY-MEASUREMENT: 3-px forward overlap = 1.0000 > 0.70`. This is a measured universal lower bound, not a sampled estimate. Session `2921f3de` made **0 experiments, 0 new rasters, and used 0 weekly slots**. No new TIF is available to download or submit. Existing archived research files remain research-only; do not copy or rename one as a new candidate.
>
> **Score:** no current leaderboard estimate is supportable for any focus-site row. The nine historical values are `USER-REPORTED`, not `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED`. No organizer submission receipt was obtained.
>
> **Current feed:** refreshed 2026-10-29 14:33 UTC; all nine focus-site HEADs changed relative to the pinned historical audit. The bounded first-README-path sample is `9/9 DUPLICATE_STOP` at overlap `1.0000`; `7/9` pass this repository's strict local format check and `2/9` fail due exterior NaNs. It is not a current-winner search, score check, or complete raster inventory.
>
> **Run card:** `registry/session_arena_2921f3de_run_card.json` (identical copies under `evidence/` and `docs/data/`). **Ranked conditional slate:** `session-arena-2921f3de-hypotheses-20261029.md`. No hypothesis was fitted; no candidate holdout, leakage canary, surface, dots, TIFF, score, or slot exists.

## 1. Executive summary — the nine named sites

The rows below identify the highest historical claims supplied for these sites and the corresponding immutable file links in the pinned 2026-10-26 audit. The values are **USER-REPORTED historical claims**, not estimates of current leaderboard performance. “New score estimate” is intentionally **NOT ESTIMABLE** in every row: no comparable candidate HOLDOUT-DTI, hidden labels, or organizer receipt links the historical file to a current score. The source files are linked for research identification only; none is recommended or cleared for upload.

| Site | Best historical file in the supplied/pinned evidence (research reference only) | Historical claim | Measured lineage / uniqueness finding | New score estimate | Download / submit decision |
|---|---|---:|---|---|---|
| GEMSDOE24 | [`h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/17496743a9695974370512db64d8140ea1ccfd2f/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | **USER-REPORTED 0.2477** | D1.5 thinning of the H19-5 ridge set; not an independent catalogue-free geological measurement. 3-px overlap is `1.0000` against the dense witness and H19-5. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |
| GEMSDOE25 | [`dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/88a29e094989b0e23916136e593474875d067656/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | **USER-REPORTED 0.2600** | D2.8 Poisson thinning; pixel-for-pixel duplicate support of GEMSDOE30's listed 44,090-dot file. Dense-witness overlap `1.0000`. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |
| GEMSDOE27 | [`topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/426426b402f90f4e0786990b4edd261d9dd48085/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | **USER-REPORTED 0.2449** | D1.5 set plus 1,259 catalogue-tip connectors; 3-px overlap `0.980645` with H19-5 and `1.0000` with the dense witness. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |
| GEMSDOE28 | [`h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/348ff086e29b9c48bb7104daacb647af31a184bf/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | **USER-REPORTED 0.2710** | Near-H33/D2.8 prune; `0.954727` of H28 dots fall within 3 px of H33 (forward, candidate denominator); reverse direction is `0.998752` of H33 dots near H28. Dense-witness overlap is `1.0000`. The earlier `0.2715` attribution was corrected in the pinned audit. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |
| GEMSDOE30 | [`d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif`](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/73db382d3c990d0aa0b5126997a67213cc56dee4/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | **USER-REPORTED 0.2600** | Exact 44,090-dot pixel-support duplicate of GEMSDOE25 D2.8; dense-witness overlap `1.0000`. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |
| GEMSDOE31 | [`h27-4-solo-d28-20261004-8acb75e1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/e6e85b357914068b3ba57ace0f899dde13f110a6/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | **USER-REPORTED 0.2708** | Exact 40,199-dot support match to GEMSDOE28's H27-4/SOLO file; dense-witness overlap `1.0000`. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |
| GEMSDOE32 | [`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/9e55d5d61cb748533691ed183b1b2f2e04643add/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | **USER-REPORTED 0.2778** — highest of the nine supplied claims | H33 is a 37,654-dot subset of D2.8 and SOLO-D2.8, not an independent surface; 3-px overlap `1.0000` with the dense witness and H19-5. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |
| GEMSDOE33 | [`h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif`](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/fded538406627b8d154a2fef5b5331f656d7e0f2/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | **USER-REPORTED 0.2632** | Not an exact H33 copy, but `99.71%` of dots are within 3 px of H19-5; dense-witness overlap `1.0000`. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |
| GEMSDOE36 | [`anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/4938a123133b4747079cc1c1c93a11e50c1376a7/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | **USER-REPORTED 0.2750** | Contains all 37,654 H33 dots plus 1,200 PINN additions; reported score is lower, but this is not a controlled causal comparison. Dense-witness overlap `1.0000`. | **NOT ESTIMABLE** | Research link only; **UNIQUE: NO · SUBMIT: NO** |

**Directional-overlap clarification:** the pinned pairwise audit reports `0.954727` for H28→H33 (the fraction of H28 dots within 3 px of H33) and `0.998752` for H33→H28 (the fraction of H33 dots within 3 px of H28). The older “99.88% overlap with H33” prose uses the reverse denominator; it is not inconsistent once direction is made explicit. Both exceed the user's 0.70 uniqueness limit. All nine also independently fail the universal dense-witness lower bound of `1.0000`.

**Executive answer:** no file in this table is an approved submission. The highest historical claim among the nine is H33's user-reported `0.2778`, but the score is unreceipted and the artifact fails the literal uniqueness rule. The “file to download” field is therefore a research-reference link, not an upload instruction. The new candidate filename, raster hash, and score are **none**.

### Current bounded README sample — not a winner search

At `2026-10-29T14:33:22Z`, the GitHub freshness feed observed **9 changed / 0 unchanged / 0 unknown** HEADs relative to the pinned historical audit. At `14:33:33Z`, the established sampler reopened the first qualifying bare `docs/downloads/` or `docs/research/` TIFF path in the first 16 KiB of each current README. These samples are not necessarily the current winner or newest file. Each measured `3-px` overlap is `1.0000` and each decision is `DUPLICATE_STOP`; scores were not measured.

| Site | Current sampled file at pinned HEAD | Strict local format | Registry overlap / score |
|---|---|---|---|
| GEMSDOE24 | `gems24-s3dep1-negative-10m-monoclinal-20261026-464fa34b4091-zeros.tif` | PASS | `1.0000`; score not measured |
| GEMSDOE25 | `gems25-h79-cthm-crustal-sgmc-b2-37654-20261027-e7ad8a4bf3ed-zeros.tif` | PASS | `1.0000`; score not measured |
| GEMSDOE27 | `gems27-h33-bss-complement-20261027-9ba8480691ed-allfinite.tif` | PASS | `1.0000`; score not measured |
| GEMSDOE28 | `gems28-s25-pcse-scarp-energy-k37654-20261028-4af5ddbb4b50-nan.tif` | FAIL: 7,111,787 exterior NaNs under this project's strict whole-array check | `1.0000`; score not measured |
| GEMSDOE30 | `GEMSDOE30-geothermal-corridor-offcat-d3-20261027T233111Z.tif` | FAIL: 7,111,787 exterior NaNs under this project's strict whole-array check | `1.0000`; score not measured |
| GEMSDOE31 | `gems31-h31cc-basement-step-37654d-20261028-zeros.tif` | PASS | `1.0000`; score not measured |
| GEMSDOE32 | `gemsdoe32-h51-ewsp-crack-poisson-axial28-37654-20261028T123000Z-bdf25d8c-zeros.tif` | PASS | `1.0000`; score not measured |
| GEMSDOE33 | `gemsdoe33-a33-r7-pcsup-37654-20261028-d1f9cca0af02-zeros.tif` | PASS | `1.0000`; score not measured |
| GEMSDOE36 | `gemsdoe36-s2d36-exp2-20261027-31189d084a83-zeros.tif` | PASS | `1.0000`; score not measured |

The two exterior-NaN diagnostics are local properties of these sampled files only. The actual TIFF and receipt behind the reported “Predicted values must be in range [0, 1]” portal message are unavailable, so the cause remains **unknown**. A local format failure is not evidence that either sampled file was uploaded or rejected.

## 2. GEMSDOE32 H33: what could explain 0.2778?

### Measured geometry (not a score explanation)

The immutable audit of the historical prediction supports these **REGISTRY-MEASUREMENTS**:

- D2.8 contains `44,090` positive cells; SOLO-D2.8 contains `40,199`; H33-2-B2 contains `37,654`.
- H33 is a support subset of both earlier predictions. Relative to D2.8, `6,436` cells are absent. The D2.8→SOLO pruning removed `3,891` cells at the immediate catalogue flank; SOLO→H33 removed a further `2,545` cells in the `1 < d_cat <= 2 px` collar. H33 has no dots within the audited two-pixel catalogue collar.
- The reported sequence `0.2600` (D2.8), `0.2708` (SOLO), `0.2778` (H33) is an owner/user-reported sequence, not a paired hidden-label experiment. H33's identity and pruning counts do not prove that those removals caused the reported score change.

### Plausible mechanism, explicitly unproven

A plausible explanation is that pruning catalogue-proximal, redundant dots reduced false-positive weight while preserving enough broad spatial coverage to retain hits in the metric's distance kernel. The project metric has a 300 m triangular kernel and weights FP at `0.2` and FN at `0.8`. Removing a redundant false-positive contribution could help; removing a prediction that would have covered a true hidden fault could hurt more. Thus “fewer points is better” is not a valid general rule. A catalogue buffer is not proof that an unlisted fault cannot be nearby, and the unknown hidden truths and organizer's weighted TP/FP/FN terms are unavailable here.

The H33-versus-D2.8 sequence is confounded by deterministic pruning and unknown labels; there is no controlled ablation or receipt tying `0.2778` to an organizer submission. GEMSDOE36's reported `0.2750` for H33 plus 1,200 PINN additions is consistent with an over-emission penalty, but different artifacts and score context are confounders. It does not establish a causal marginal penalty either. **Answer:** this collar-pruning/coverage trade-off is a reasonable hypothesis for the reported improvement, not a demonstrated explanation. No claim that this repo can beat H33 is supported by the available evidence.

## 3. Fresh gate, hypotheses, and source review

### Fresh shared gate

The rerun found witness SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, `5,106,385` allowed pixels, `0` uncovered allowed pixels, coverage `1.0`, and threshold `0.70`. The inherited support definition is finite prediction `>0`. `preflight_mtas88.py --gate-generation` returned expected exit `2`; `generation_guard.py` also returned expected exit `2`. No candidate surface existed to compute surface rank-correlation, and no dots existed for a new final-dot comparison. The universal dot-overlap lower bound alone is decisive. The generation gate was not weakened.

### Ranked slate

The three qualitative, conditional proposals are **H88-SPR** (moderate/highly uncertain, medium cost), **H88-AWA** (low-to-moderate/highly uncertain, medium cost), and **H88-CBC** (low/highly uncertain, medium-high cost). Their exact layers, predicted signatures, off-catalogue rationale, mimics, differences from existing code, and source availability are in `session-arena-2921f3de-hypotheses-20261029.md`. The source-bound queue audit passed metadata validation but reported `input_pins_checked: false`; the 19-band training raster and external feature caches are absent. The ranked slate is not a selected lane, an experiment, a holdout, or a score projection.

### Trusted-source boundary

The DrivenData official reference-solution repository README was freshly fetched through the GitHub API at commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`. It directs competitors to obtain data from the competition website and describes CPU-only and GPU setup; this does not authenticate the owner-mirror bytes. The current official DrivenData leaderboard, competition/data pages, NLR rules PDF, USGS GeoDAWN page, and DOE GDR record were not fetched in this session. The nine current GitHub README sample feeds are not an official score source.

A current GEMSDOE36 README at HEAD `e280188adbbe762e6b7ac6f3b8e105e8e7915026` states that the public leaderboard showed `0.4544` on 2026-10-28. The repository also preserves/request-references `0.3195`, `0.4413`, and `0.4437` observations with different dates/provenance. Those reports conflict and were not reconciled against the official live leaderboard. None is used as a current verified score or as a score for a focus-site artifact. See `knowledge/official-sources-20261029.md`.

## 4. Submission guide (automated gates; no human TIFF decision)

1. **First, run the unchanged shared gate.** Use `.venv/bin/python scripts/preflight_mtas88.py --gate-generation` and `.venv/bin/python scripts/generation_guard.py`. Exit `2` means `DUPLICATE_STOP`, not a retry request. Do not generate or place dots after that result.
2. **Restore only allowed inputs and verify provenance.** The validation tier can be restored with `bash scripts/download_competition_data.sh --validation`; those bytes are SHA-pinned owner mirrors, not authenticated organizer downloads. The full model cache is not present in this workspace.
3. **If and only if a separately authorized shared policy ever clears the pre-placement gate:** preregister one explicitly assigned method lane; use cached features and `vendor/gems57` tools; hold out whole fault segments with a buffer; derive catalogue features from visible faults only; exact-mask visible catalogue labels; run feature-alone leakage canaries; report pooled HOLDOUT-DTI with evaluator, withheld positives, and 95% CI; check surface uniqueness before placement and final-dot uniqueness afterward. Stop at three experiments or two hours. This session has no assigned method paragraph, and the current gate fails.
4. **Run format checks on the saved bytes, not a proposal.** Verify single-band GeoTIFF, no NaN inside the footprint, finite `[0,1]` predictions, exact CRS/shape/transform, exact footprint behavior, and package/hash binding. A local format PASS is not a score or organizer acceptance.
5. **Keep slot selection separate.** No file here says `OK TO SUBMIT`; no weekly slot was selected. Only after every automated gate and a separate selector approval could an operator upload the exact approved TIFF/name/note, check the current authenticated quota, and save the submission-page receipt. Only that receipt can support `ORGANIZER-CONFIRMED`.

The archived H88-TDKL/GTZ and other `DO-NOT-SUBMIT` artifacts may be downloaded **for research only** where their own cards allow it; they are not replacements for the requested new TIF. The current audited release and public guide continue to say **SUBMIT: NO**.

## 5. Three-pass review log

### Pass 1 — requirements, workspace, and gate reproduction

- Re-read the standing instructions, README current decision, active owner prompt, `PROMPT.md`, previous session review/run card, canonical release and shared generation/preflight code.
- Installed the pinned CPU Python requirements into `.venv` and restored the validation tier from SHA-pinned owner mirrors. The downloader explicitly confirms the full 19-band/external/190-sibling stack is not restored and the mirror is not organizer-authenticated.
- A first accidental `python` invocation used the system interpreter and failed with `ModuleNotFoundError: numpy`; no gate ran in that attempt. The correct `.venv/bin/python` invocation then ran preflight successfully and returned the expected duplicate stop, including the direct `0/5,106,385` uncovered-pixel proof.
- Freshly ran `generation_guard.py`; it also returned expected exit `2`. Neither run imported a candidate generator or emitted a surface, dots, or raster.
- **Timestamp irregularity:** the preflight JSON still contains `date_utc: 2026-10-25`. That stale metadata is not treated as this run's timestamp; the run card records that the exact preflight execution time was not emitted, while the independent feed and browser receipts retain their own timestamps.

### Pass 2 — evidence, hypothesis, and source challenge

- Ran `audit_research_state.py`: metadata PASS, proposals H88-SPR/AWA/CBC, evaluated historical lanes still retired, `input_pins_checked: false`, `generation_authorized: false`.
- Refreshed the GitHub HEAD snapshot and bounded current sampler at 14:33:22Z/14:33:33Z. All nine HEADs changed; all nine sampled files duplicate-stop; two have local exterior-NaN format failures; zero scores were measured. Preserved SHA-bound dated copies in `docs/data/` and `evidence/`.
- Rechecked the historical nine-site score table, exact-copy/nested lineage claims, H33 pruning counts and the current bounded sample. Kept score provenance as USER-REPORTED and did not infer an organizer receipt or a current winner from the sample.
- Retrieved the official DrivenData reference-solution README at its GitHub commit. Recorded that non-GitHub official pages and the live leaderboard were not refreshed; noted the conflicting historical leaderboard observations and the participant-reported 0.4544 figure as unverified.
- Ranked the three existing conditional hypotheses and listed their required layers, signatures, off-catalogue rationale, mimics, costs, code differences, and missing-source/cache limitations. No lane was invented for the absent “single method paragraph.”

### Pass 3 — adversarial requirements and automated verification

- Updated the current README decision and preserved the active scope brief; refreshed the machine-readable current feed and added immutable session-dated source copies.
- Added a session run card, three-pass review, ranked hypothesis note, and source audit. Kept all three run-card mirrors byte-identical; added an explicit pointer to the existing TDKL research-only bytes so a browser download receipt cannot be confused with a new artifact. No TIFF, holdout, feature fit, experiment, or slot was created.
- Updated the canonical Pages review pointer, made the per-site table state `NEW SCORE ESTIMATE: NOT ESTIMABLE`, and regenerated the decision pages only after binding the new negative run card.
- The first full test run exposed one integration issue: the new active card did not yet identify the archived research-download SHA expected by the existing publication guard. Added the exact pre-existing TDKL file/hash and kept `ok_to_submit: false`; the focused publication/session tests then passed, and the full suite was rerun.
- Final automated verification: `.venv/bin/python -m pytest -q` → **1,110 passed, 23 skipped, 115 warnings**; `focus_freshness.py --check`, `focus_current_samples.py --check`, `audit_research_state.py` metadata audit, `audit_downloads.py --check` (**51/51** research packages pass local checks, **0** protocol-eligible), `render_decision.py --check`, `check_site.py`, and `python -O scripts/check_site.py` all passed; `git diff --check` passed. A Chromium browser receipt at `2026-10-29T14:59:14.464Z` passed **7** desktop/mobile page checks, responsive focus-table checks, missing/partial/expired-feed fail-closed tests, and exact SHA verification of the existing TDKL research download. The session preflight and generation guard both returned the expected exit `2`. These are local integrity/UI checks, not organizer acceptance or current leaderboard verification.

### Core values and remaining work

**Maximize P(Win):** do not spend a submission slot on a file mathematically blocked by the literal uniqueness rule or on an unvalidated estimate. **Own the Outcome:** the urgent new unique-TIFF requirement remains unmet, so this report says so plainly rather than relabeling an archive or bypassing the guard.

A new raster remains prohibited until the user/rule owner authorizes a satisfiable shared uniqueness policy and the shared preflight passes. The current review makes no score estimate, no organizer-confirmed claim, and no submission selection.
