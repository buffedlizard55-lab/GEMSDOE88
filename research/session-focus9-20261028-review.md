# Focus-site review and submission status — GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 (`2026-10-28`)

**Branch:** `arena/557d884e-gemsdoe88` · **Slots used:** 0 · **Experiments run:** 0 · **New TIFF generated:** none · **organizer-confirmed scores:** 0

## 1. Executive summary

| Question | Answer |
|---|---|
| Which file should I download and submit? | **None.** No file is cleared. Every candidate in the repo is research-only (`SUBMIT: NO — DO NOT SUBMIT`). |
| Is there a unique submission? | **No.** The binding uniqueness gate is vacuous (section 4): every nonempty candidate fails it, including the nine top files below. |
| Which site has the highest reported score? | **GEMSDOE32**, `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, **0.2778 — USER-REPORTED**. Its bytes match the pinned H33 raster. |
| Estimated score for any file? | **No estimate exists.** There is no HOLDOUT-DTI for these nine files and no organizer receipt. The only numbers are user-reported. |
| Can we beat 0.2778? | **Not demonstrated.** Section 3 gives the metric identity that defines the target, and the test that would have to pass. |
| Why is submission blocked? | The gate can't tell candidates apart (section 4). Changing it is an owner decision, not something to do silently. Two decisions are requested at the end. |
| Top of leaderboard today | **0.4544** (rank 1, `xiaofanhu`), not 0.4413 or 0.3195 as the prompt says (section 6, IR-F9-01/02). |

### Per-site table (live files, verified this session)

Columns: the user-named submission, its user-reported score, the live file to download, dots, and independent unique/overlap checks. "Overlap" = fraction of this file's dots within 3 px of an H19-5 dot, using my probe (`scripts/audit_focus_top_files.py`). The gate limit is 0.70. "Unique?" applies the user's 0.70 rule against H19-5, the largest registry raster in the lineage.

| Site | Top user-named submission | Score (USER-REPORTED) | Download (live, `docs/downloads/`) | Dots | Overlap vs H19-5 | Unique? | Estimated HOLDOUT-DTI | OK to download / submit? |
|---|---|---|---|---|---|---|---|---|
| **GEMSDOE32** | `h33-h33-2-b2-…-e5eb6e7e-zeros` | **0.2778** | [`gemsdoe32-…-e5eb6e7e-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) · sha `c55bafc4…` (= pinned H33) | 37,654 | 1.0000 | **NO** | none (see §3) | **Research download only · SUBMIT: NO** |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-…-9b9ea4e6-zeros` | 0.2750 | [`…-9b9ea4e6-zeros.tif`](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/main/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) · sha `e1589102…` | 38,854 | 0.9775 | **NO** | none | Research only · SUBMIT: NO |
| GEMSDOE28 | `h36-1-rung30-blind-r1-…-b531dae0a36f-nan` | 0.2710 | [`gems28-h36-1-…-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/main/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) · sha `5556aa14…` | 37,660 | 1.0000 | **NO** | none | Research only · SUBMIT: NO |
| GEMSDOE31 | `h27-4-solo-d28-…-8acb75e1-nan` | 0.2708 | [`gemsdoe31-h27-4-solo-d28-…-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/main/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) · sha `07b6db44…` | 40,199 | 1.0000 | **NO** | none | Research only · SUBMIT: NO |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-…-cb490425926e` | 0.2632 | [`…-cb490425926e-nanoutside.tif`](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/main/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e-nanoutside.tif) · sha `bc3af2a5…` | 41,865 | 0.9971 | **NO** | none | Research only · SUBMIT: NO |
| GEMSDOE25 | `dotted-h19-5-d2-8-…-e56ea318af89-nan` | 0.2600 | [`…-e56ea318af89-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/main/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) · sha `91eae1ca…` | 44,090 | 1.0000 | **NO** | none | Research only · SUBMIT: NO |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-…-91eae1ca` | 0.2600 | [`…-91eae1ca-nanoutside.tif`](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/main/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca-nanoutside.tif) · sha `5f963b8b…` | 44,090 | 1.0000 | **NO** | none | Research only · SUBMIT: NO |
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-…-989f59505db1-nan` | 0.2477 | [`gems24-h25-1-…-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/main/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) · sha `68d0e2e4…` | 60,069 | 1.0000 | **NO** | none | Research only · SUBMIT: NO |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-…-5512495c6bd1-nan` | 0.2449 | [`…-5512495c6bd1-nan.tif`](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/main/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) · sha `33003374…` | 61,328 | 0.9806 | **NO** | none | Research only · SUBMIT: NO |

Every row: 3-px overlap with the dense `17GEMSDOE` witness is **1.0000** (the witness is positive on every allowed cell, §4). Every row is a 0/1 float32 raster on the official grid, with NaN or zero outside the footprint and no NaN inside it (`evidence/focus_top_files_20261028.json`).

**"Estimated score" column, stated plainly:** no estimate for these files is possible yet. The only HOLDOUT-DTI values in the repo belong to other files (for example BPWD, `0.205991 [0.188105, 0.223344]`, evaluator `gems57-pooled-hide-v2`, 22,893 withheld positives, cited from the README). H33-lineage files cannot be fairly holdout-scored as they stand, because their pruning rule uses the full catalogue. AGENTS.md rule 5 forbids that protocol. The public figures are user-reported and unreceipted.

**Two encodings and one format risk (IR-F9-04).** The owner repos publish each top file in two encodings: NaN outside the study footprint (matching the official sample: 7,111,787 NaN cells), or zero outside it. The official page says data outside the bounds "is null or nan". The zero-outside versions are in range and scoring-neutral by the formula, but they do not match the official template. If a file is ever submitted, use the NaN-outside encoding.

## 2. What the official sources say (retrieved 2026-10-28)

- **Submission format** — [Competition page 967, "Submission format"](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): GeoTIFF; EPSG:32611; 100 m; same bounds as the training data; "data outside the bounds is null or nan"; a single float32 layer; "values between 0 and 1". The sample file is the official template (`sample_submission.tif`, NaN outside the footprint).
- **Metric** — same page, "Performance metric": distance-weighted Tversky index, α = 0.2, β = 0.8, triangular kernel with R = 300 m (3 px). The page's worked example gives TP_w = 3.00, FP_w = 1.89, FN_w = 2.00 and TI_w = 0.60; the repo's `vendor/gems57/metric.py` reproduces 0.60 (test `test_official_worked_example_reproduces`).
- **Cap** — [Official Rules PDF, §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf): "three submissions per week". In the rules text I retrieved (preface, §1 and §2–§3.2; chunk 1 and chunks 3–6 were not read), I found no uniqueness or overlap rule. The 0.70 / 0.90 limits are the owner's internal protocol, not the organiser's, as far as I could verify.
- **Existing-fault caveat** — same competition page: "portions of the existing fault data may be misaligned from the true location of the surface fault". This matters for section 3.
- **Leaderboard** — [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), captured 2026-10-28, top 50 in `evidence/leaderboard_snapshot_20261028.json`: #1 0.4544, #26 0.3195, #50 0.2874. The leaderboard column is "Best public DW-Tversky" and is not the private or final score.
- **Reference solution** — [drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) (single commit `aebe92f`). Its README describes a notebook baseline. I did not diff its metric code against the repo's line by line this session; that comparison is listed in §8 as open.

## 3. Why H33 (GEMSDOE32) scored highest, and whether we can beat 0.2778

### 3a. Measured facts (independent recomputation, `evidence/gate_vacuity_20261028.json`)

- H33 has **37,654 dots**, all inside the footprint, binary, 0 NaN inside.
- **H33 is an exact subset** of SOLO-D2.8 (GEMSDOE28, 40,199 dots), D2.8 (GEMSDOE25, 44,090), H19-5 (GEMSDOE19, 121,131) and GEMSDOE36 (38,854): 37,654 / 37,654 inside each. It is the same lineage with dots removed, not a new geometry.
- **Distance to the mapped catalogue:** H33 has **0** dots within 2 px (200 m) of a mapped fault (minimum 224 m). SOLO-D2.8 has 2,545 there; D2.8 has 6,436. H33 = SOLO-D2.8 minus those 2,545 dots.
- **Reported ladder (USER-REPORTED, not receipted):** D2.8 0.2600 → SOLO-D2.8 0.2708 (+0.0108) → **H33 0.2778** (+0.0070, from removing the near-collar dots) → GEMSDOE36 0.2750 (−0.0028, from adding 1,200 PINN dots to H33).

### 3b. The metric identity that determines the answer

For this metric FN_w = |G| − TP_w exactly (TP_w is defined as the sum over truth pixels of the per-pixel maximum, and FN_w is its complement). So

**DTI = TP_w / (0.2·TP_w + 0.2·FP_w + 0.8·|G|).**

Removing one dot changes (TP_w, FP_w) by (−t, −f), where t is the credit only that dot supplies and f is its false-positive cost. Removing it improves the score iff **t/(t+f) < 0.2 · DTI**. So a dot is worth keeping when its share of credit exceeds α·DTI. At DTI ≈ 0.28 that threshold is ≈ 0.056. If a dot's credit when it hits is about 0.5 (an assumption, not measured), that means keeping it needs roughly a 10% chance of landing within about 1–2 px of a hidden fault.

This identity and the removal rule are verified exactly on random scenes against the shared vendor metric (`tests/test_focus9_metric_identity_20261028.py`, 3 passed). The test checks the identity to 1e-12 and the removal decision for every dot in 12 random scenes.

### 3c. Why pruning near the catalogue helped (and why that is not yet established)

- Under the identity, the near-collar pruning helps only if dots within 1–2 px of a mapped fault have a hit probability below ~0.056 (≈10% if average kernel credit is ≈0.5, an assumption). The organiser states hidden faults are the ones "not contained within the current public USGS database". So near-collar dots may be less likely to hit. That is the plausible mechanism.
- The same page also says existing fault data "may be misaligned". A dot 200 m from a mapped trace could sit on the true fault. Then removing it costs true positives. The sign of the near-collar effect depends on a hit rate nobody has measured.
- **Named non-fault process that could mimic the gain:** catalogue-digitisation and mapping-density effects. Where traces were digitised densely, a catalogue-distance pruning rule removes dots from exactly the areas with the most mapping, so the public gain may reflect where the public split's labels fall, not a physical rule. The +0.0070 has no confidence interval, and the public split is only part of the hidden labels.
- A repo record says an earlier collar-based holdout (CON88) was negative (`0.0017` vs `0.2060`, with an H33 calibration caveat). I did not re-run it. I'm citing the README record, not re-measuring it.

### 3d. Can we beat 0.2778?

Not with anything measured in this session. Concretely, the next scientifically valid step is a **visible-only** catalogue-collar pruning of D2.8, tested with buffered whole-component hide-and-recover, compared with D2.8 and SOLO-D2.8 on the same folds, with a leakage canary per feature and at most three experiments. That protocol needs a lane definition (decision 2 below). It also needs a fair estimate of the hit rate by catalogue distance. Until the holdout is run, the honest statement is: H33's public gain is plausible and unverified, and no candidate is known to beat it.

## 4. The binding gate is vacuous (verified, not just recorded)

- `data/registry/dense_17gemdoe.tif` is a continuous probability surface (SHA `ab0a0a62…`). It is **positive on all 5,106,385 of the allowed cells** (min 0.00046). Any nonempty dot set therefore has **100% of its dots within 3 px of a nonzero witness cell**, so the literal test returns 1.0 for every candidate. `scripts/preflight_mtas88.py --gate-generation` returns `DUPLICATE_STOP` (exit 2) for this reason. The repo already logged this as IR-88-222254A5-01 ("selector decision required").
- A **shadow** diagnostic (not the gate, not clearance): if the witness is read as its top-K cells (K = 37,654), the overlap with H33 is 0.3386, with D2.8 0.6567 and with H19-5 **0.7108**. So even with a non-vacuous reading, a top-K candidate of that size would still fail the 0.70 limit against H19-5. The gate needs a definition, not only a rewording.
- I found no such gate in the official competition page or in the rules text I retrieved (preface, §1, §2–§3.2). It is the owner's internal protocol (the parallel-run text), so the owner should decide how to read it.

I did not generate a TIFF. The owner's protocol says to stop on a duplicate, and I have no authority to reinterpret the gate.

## 5. Reproduction (commands and results)

| Command | Result |
|---|---|
| `python -m venv .venv && pip install -r requirements.txt` | exit 0 (numpy 2.3.4, rasterio 1.4.4, scipy 1.16.2) |
| `bash scripts/download_competition_data.sh --validation` | exit 0, 10 owner mirrors restored with SHA checks (validation tier) |
| `scripts/audit_downloads.py --check` | exit 0 (49 research TIFFs, 1 additional, 0 protocol-eligible) |
| `scripts/render_decision.py --check` | exit 0 |
| `scripts/check_site.py` | exit 0 |
| `scripts/preflight_mtas88.py --gate-generation` | **exit 2, DUPLICATE_STOP** (expected; not bypassed) |
| `scripts/audit_focus_top_files.py` | exit 0; 9 sites via api.github.com; 20 files downloaded and reopened (`evidence/focus_top_files_20261028.json`) |
| `scripts/audit_gate_vacuity_20261028.py` | exit 0; witness positive on 1.0000 of allowed cells; subset and top-K rows (`evidence/gate_vacuity_20261028.json`) |
| `pytest tests/test_focus9_metric_identity_20261028.py` | 3 passed |

Independent checks on bytes: GEMSDOE32 zeros variant sha `c55bafc4…` equals pinned `data/registry/h33_education.tif`. GEMSDOE36 zeros variant sha `e1589102…` equals pinned `gems36_anderson_pinn.tif`. GEMSDOE30 nan-outside dot set is identical to the pinned GEMSDOE25 D2.8 dot set (44,090 / 44,090). GEMSDOE32 nan variant has the same dot set as pinned H33 (37,654 / 37,654). These are the four byte or set checks in this session; the rest of the table relies on the same downloader and reopener.

## 6. Irregularities for review (flagged, not resolved)

| ID | Irregularity | Evidence |
|---|---|---|
| **IR-F9-01** | The prompt says the current GEMSDOE high is **0.4413**. It is not in the top 50 on the live leaderboard. Rank 1 is **0.4544**. | [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), `evidence/leaderboard_snapshot_20261028.json` |
| **IR-F9-02** | The prompt says 0.3195 is "the highest score right now". It is rank 26 (`kpomazi`). | same |
| **IR-F9-03** | Live owner repos have changed since the 2026-10-26 audit. File names now differ from the prompt (e.g. `gemsdoe32-…-e5eb6e7e-zeros.tif`, `gemsdoe31-h27-4-solo-d28-…-nan.tif`, `gemsdoe30-…-nanoutside.tif`). Some sites publish two encodings. The prompt's score attaches to a name, not to bytes. | `evidence/focus_top_files_20261028.json` |
| **IR-F9-04** | The zero-outside encoding differs from the official template's NaN outside the footprint. It is scoring-neutral by the formula. | official page; §1 |
| **IR-F9-05** | The reported portal error "Predicted values must be in range [0, 1]" is **not reproduced** by any of the nine live top files: all values are in [0, 1] and no NaN lies inside the footprint. The cause is unknown; the error text may come from a different file, a wrapper, or an encoding the portal reads differently. | `evidence/focus_top_files_20261028.json` |
| **IR-F9-06** | The uniqueness gate is vacuous (§4). Already logged as IR-88-222254A5-01; re-measured here. | `evidence/gate_vacuity_20261028.json` |
| **IR-F9-07** | The protocol refers to "the single method paragraph below" (the lane). No lane paragraph was supplied, and bracketed placeholders such as "[0.90]", "[70%]" and "[3]" remain. | prompt text |
| **IR-F9-08** | The repo's `dti_binary` says the organiser masks mapped catalogue faults from scoring, citing "organiser thread 11516". That claim is not in the official rules or competition page I retrieved. It is unverified. | `vendor/gems57/metric.py`, docstring |
| **IR-F9-09** | No organizer receipt exists for any score in the prompt. All nine scores are USER-REPORTED. | `docs/data/user_reported_results.csv` |
| **IR-F9-10** | GEMSDOE25 and GEMSDOE30 are the same dot set (44,090 / 44,090). That is why they share a score. Their names and filenames differ. | §5 |

## 7. Decisions needed from the owner (requested at the end of this turn)

1. **Gate definition.** How should the dense `17GEMSDOE` witness be read? (a) keep the literal rule (no candidate can clear; the status quo); (b) exclude continuous witnesses from the dot-overlap test and keep rank correlation as a diagnostic; (c) use the witness's top-K cells as its dots; (d) something else. AGENTS.md says the dense prior must not be discarded without written authorisation. This session has not authorised any change.
2. **Lane.** Provide the lane paragraph (the "single method paragraph" the protocol refers to), or choose the default: the visible-only H33-collar holdout in §3d.

Submitting is always the owner's action. Nothing in this repo can submit to DrivenData.

## 8. Open items (not done this session)

- Line-by-line diff of `vendor/gems57/metric.py` against the reference notebook in `drivendataorg/gems-prize-reference-solution` (not fetched).
- Visible-only collar-pruning holdout (§3d). Blocked on decision 2.
- Full 19-band training features and the 190-sibling uniqueness stack (`restore_inputs.py` and `restore_siblings.py`). Not restored; only the validation tier was.
- The live "current" GitHub state of all 90+ listed sites. Only the nine focus sites were checked.

## 9. Sources (retrieved 2026-10-28 unless stated)

- Competition problem description and submission format — https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Public leaderboard — https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Official rules (NLR PDF, September 2026) — https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution (README and commit `aebe92f`) — https://github.com/drivendataorg/gems-prize-reference-solution
- Owner repositories (live `docs/downloads`, via api.github.com) — https://github.com/buffedlizard55-lab/GEMSDOE24 … GEMSDOE36 (nine sites)
- EPSG:32611 — https://epsg.io/32611
- Tversky index — https://en.wikipedia.org/wiki/Tversky_index
- Machine evidence: `evidence/focus_top_files_20261028.json`, `evidence/gate_vacuity_20261028.json`, `evidence/leaderboard_snapshot_20261028.json`; run card `registry/session_focus9_20261028_run_card.json`.

## 10. Three review passes (record)

- **Pass 1 — implement and verify.** Restored the validation tier with SHA checks; built the environment; pulled the live leaderboard and official pages; checked each of the nine top files by name and hash; reproduced the gate (exit 2) and the subset relations; wrote the two read-only audits and one metric test.
- **Pass 2 — bugs and assumptions.** Corrected: (a) the contents API omits files above 1 MB, so two focus files had failed silently (`ERROR`), fixed by using the git blob API and recording every TIFF variant; (b) the run card's note length (74 stated, 81 actual); (c) my claim about the rules text was wider than what I had read (chunk 1 not read), now scoped; (d) "10% chance" depends on an assumed kernel credit, now labelled as an assumption. Overlap numbers were computed with my own probe and are labelled as such; they are not the repo's gate.
- **Pass 3 — against the request.** Each part of the request is answered or explicitly blocked: executive summary and table (§1); why H33 scored highest (§3a–c); whether a higher score is achievable (§3d, not demonstrated); unique TIFF (not generated; blocked by a vacuous gate, §4, with the decision requested); estimated score (none exists, stated plainly); official sources (§2, `knowledge/official-sources-20261028.md`); irregularities (§6); the prompt record (`USER_PROMPT_20261028.md`, condensed and disclosed). Full test suite: 1106 passed, 23 skipped; CI-equivalent guard scripts all pass.
