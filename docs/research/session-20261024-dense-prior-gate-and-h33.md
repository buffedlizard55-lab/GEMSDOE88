# 2026-10-24 session note: why the uniqueness gate is stuck, why 0.2778-style files score, and what is still missing

Status: research note. **No file in this note is OK to submit.** No weekly slot was used. Every number is either a
machine record (cited) or an official-page statement (linked). Nothing here is an organizer score.

## 1. What the official metric rewards (verified on the official page)

Source: [competition page 967, "Performance metric" and "Submission format"](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) (read 2026-10-24).

- Predictions are **pixel-wise probabilities or confidence scores between 0 and 1**; `p(x) in [0,1]`.
- The score is a distance-weighted Tversky index with **alpha 0.2 (false positives) and beta 0.8 (false negatives)**, triangular kernel `k(d)=max(1-d/R,0)`, `R = 300 m = 3 px`.
- `FP_w = sum over x with p(x)>0 of p(x) * [1 - max_g k(d(x,g))]`. So a cell with tiny `p` still costs `p`, and a cell far from every truth costs its full `p`. **Dense low-probability mass is expensive.**
- `FN_w = sum over g of [1 - max_x p(x) k(d(x,g))]`. Each true fault is penalised by how little coverage a nearby high-`p` cell gives it.
- Labels: the page says the new test faults "are not contained within the current public USGS database". Dots that sit on the catalogue are therefore false positives unless they lie within the kernel of a new fault. That is the mechanism behind any "move dots off the catalogue" lever.

Consequence: a continuous probability surface is a legitimate submission type, and it is also expensive when it covers most of the map. This matters for the gate question below.

## 2. Why the literal uniqueness rule is degenerate here (measured)

- `data/registry/dense_17gemdoe.tif`: 5,167,373 finite positive cells; values `0.00046`–`0.984`; median of positives `0.219` (repo measurement, this session).
- The shared rule `vendor/gems57/uniqueness.py::_dots` counts every finite cell `> 0` as a dot. So **every candidate has forward 3-px overlap 1.0** with this raster, and the 0.70 gate cannot be passed by any candidate.
- Rank correlation is not the problem: the recorded Spearman between PHASE-88 and the witness is `0.006411` (`evidence/phase88_final_uniqueness.json`, witness row).
- Diagnostic (not a rule change): `scripts/diagnose_dense_prior_topn.py` redefines the witness's dots as its top-N cells, N = candidate count. All 14 published TIFFs pass 0.70 (max `0.130052`, MDC-88). Output: `evidence/dense_prior_topn_diagnostic.json`.
- **Decision for the selector:** whether a dense prior counts as "dots". Options are (a) keep the literal rule, which no candidate can ever pass; (b) adopt a top-N like-for-like definition for dense priors, written into the shared gate once. Even under (b), every candidate still fails the holdout bar, so (b) alone authorizes nothing.

## 3. Why the 0.2778 file (GEMSDOE32, user-reported) plausibly scored high

Repo claim, checked against the rasters (dot counts only; the score itself is user-reported, not an organizer receipt):

| file | dots | source |
|---|---|---|
| `data/registry/gems19_h19_5.tif` (H19-5 ridge) | 121,131 | counted this session |
| `data/registry/gems25_d28.tif` (D2.8 kernel-spaced) | 44,090 | counted this session |
| `data/registry/h33_education.tif` (H33 = GEMSDOE32 file, 0.2778 user-reported) | 37,654 | counted this session |

So the lineage is nested thinning: 121k → 44k (kernel-matched spacing) → 37.6k (a 2 px catalogue collar that the official site text reports as removing 6,436 dots; 44,090 − 6,436 = 37,654, which checks). Section 1's formula is consistent with both steps: thinning reduces FP mass, and dots on catalogue cells are FPs under labels that exclude the catalogue. This is a consistency argument, not a tested effect; the repo's own canary and holdout do not isolate it. The **named non-fault mimic** is the same signal: unmapped scarps or lithologic contacts along the catalogue edge would look like the same "off-catalogue ridge" pattern. The repo's holdout cannot separate these (its own canary notes this). Full lineage and forensics: [`research/session-20261024-audit-why-0.2778.md`](session-20261024-audit-why-0.2778.md) and [`research/h33-forensics-20261024.md`](h33-forensics-20261024.md).

## 4. Holdout versus leaderboard (what we can and cannot say)

- Official public leaderboard, checked 2026-10-24: **#1 `0.4413`**, #2 `0.3916`, #20 `0.3273` ([leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)). The `0.3195` figure in the request is not in the first chunk I read, so it is unverified.
- Our HOLDOUT-DTI (`gems57-pooled-hide-v2`, 22,893 withheld positives) is a local hide-and-recover estimate on the catalogue. **No evidence in this repo maps it to the leaderboard.** Treat it as a ranking aid, not a predicted score.

## 5. Candidate status (from one table, `docs/data/candidate_matrix.json`)

Best local HOLDOUT-DTI is MRR-BPR-88 `0.185256` [0.171519, 0.199965], paired Δ vs the stored bar `-0.004378` [-0.007902, -0.000623]: below the bar. MDC-88 is next at `0.148850`. The stored bar is `0.187888` [0.171698, 0.203260], and the repo itself says that bar is currently unverifiable from a clean checkout (IR-88-75). Nothing beats it with a CI above zero.

## 6. What would change the outcome (in order)

1. A **new idea that beats the bar** on the paired holdout, with leakage canaries ≤ 0.90. Nothing in this repo does that yet.
2. A selector decision on the dense-prior definition (section 2). This is required before any file can be submitted, but it does not make a file submittable by itself.
3. Organizer receipts. None exist. Every score here remains HOLDOUT-DTI or user-reported.
