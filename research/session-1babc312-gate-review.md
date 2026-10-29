# GEMSDOE88 review — session `1babc312` (2026-10-29)

> ## Decision: **NO NEW TIFF — DO NOT SUBMIT**
>
> - **No TIFF was generated, no experiment was run, no weekly slot was spent.** `scripts/generation_guard.py` and `scripts/preflight_mtas88.py --gate-generation` both exit `2` (`DUPLICATE_STOP`, `ok_to_submit: false`) on freshly restored inputs (reproduced 2026-10-29 17:58 UTC).
> - **The unique-TIFF requirement is blocked by one policy question, not by missing code.** The literal uniqueness rule, as the repo implements it, counts every positive cell of the witness raster as a "dot". The witness is a continuous probability surface, so every candidate overlaps it at 1.0000. This has been raised before (see IR-88-SDTL-01 and IR-88-B4DFA10C-08 below). It needs your decision. See **Decision required** below.

## Evidence (reproduced in this session)

Inputs restored with `PYTHON=.venv/bin/python bash scripts/download_competition_data.sh --validation` (17 of 17 core files, SHA-pinned owner GitHub mirrors, **not** an authenticated DrivenData download). Every check below was run on those bytes.

| # | Check | Result | Command / source |
|---|---|---|---|
| 1 | Witness `data/registry/dense_17gemdoe.tif` SHA-256 | `ab0a0a62…3872be` (matches pin) | `scripts/preflight_mtas88.py` |
| 2 | Witness shape / CRS / transform | `3730 × 3292`, `float32`, `EPSG:32611`, 100 m pixels | `rasterio` read |
| 3 | Witness finite cells / cells `> 0` | `5,167,373` / `5,167,373` (100%) | `rasterio` read |
| 4 | Witness value range (finite) | min `0.00046258`, max `0.98411570`; **not** binary | `rasterio` read |
| 5 | Organizer sample `sample_submission.tif` NaN cells | `7,111,787` NaN; finite cells `5,167,373`; finite values exactly in `{0, 1}` | `rasterio` read |
| 6 | Sample footprint == witness footprint | `True` (identical finite mask) | `rasterio` read |
| 7 | Sample `== 1` cells == `existing_faults.tif == 1` cells | `True` (60,988 cells) | `rasterio` read |
| 8 | "Allowed" cells = footprint minus known faults | `5,106,385` | `rasterio` read |
| 9 | Witness `> 0` on allowed cells | `5,106,385 / 5,106,385` | `rasterio` read |
| 10 | Preflight `universal_overlap_blocker` | `true`; `covered_allowed_fraction 1.0`; overlap limit `0.7` | `preflight_mtas88.py` JSON |

Consequence (check 9 + the literal rule): any nonempty candidate has forward 3-px overlap `1.0000 > 0.70` with the witness, so every candidate fails before feature construction.

## Irregularities for review

1. **Witness is a surface, not a dot set.** The literal rule `finite prediction > 0` turns a continuous 17GEMSDOE probability field into "dots" on 100% of its footprint (checks 3–4). A gate that every nonempty file fails by construction does not measure uniqueness; it measures the witness's support. The repo's own comment (`vendor/gems57/uniqueness.py`, `equal_support_dots`) says the same.
2. **The repo has already tried a fix and reverted it.** `binding_duplicate_decision_v5` (IR-88-SDTL-01) defined dense-surface dots as the top-n cells. It was then superseded by a literal-only v5 because "the user did not authorize replacing literal dot overlap" (IR-88-B4DFA10C-08). The change is reproducible in `vendor/gems57/uniqueness.py` but is not binding.
3. **Local checker is stricter than the organizer's own sample.** The organizer's `sample_submission.tif` has NaN outside its footprint (check 5). The repo's strict format check rejects exterior NaN. Whether the portal accepts NaN outside the footprint is **not established** here. The user's reported `"Predicted values must be in range [0, 1]"` error is therefore still unexplained; the repo's sampled exterior-NaN files are not proven to be its cause.
4. **Data provenance.** All inputs are pinned owner-GitHub mirrors (`restore_inputs.py`). They are not an authenticated DrivenData download and their redistribution terms have not been checked. DrivenData (`/data/`, `/submissions/`, `/leaderboard/`) is not on this sandbox's allowed-host list, so the current leaderboard, quota and submission receipts were not fetched.
5. **The `0.2778` H33 claim, the `0.4413` leaderboard value, and every site score in the prompt remain USER-REPORTED CLAIMS.** No `HOLDOUT-DTI` and no `ORGANIZER-CONFIRMED` number exists for any candidate, so no score estimate is supported.

## Decision required (from you)

The repo cannot produce a unique, submittable file under the rule as written. Choose one of these; I will not pick for you because the rule is yours and prior sessions recorded that it was not authorized to change.

- **A — Keep the literal rule (current default).** Result: no TIFF can be generated. Nothing is submitted. The next step is a new contest-level idea that is not a dense-surface continuation.
- **B — Authorize a dense-surface dot definition.** Witness "dots" = its top-`n` cells, where `n` equals the candidate's dot count (the IR-88-SDTL-01 construction). The rank-correlation test (`|rho| <= 0.90` against every registry raster) and the literal dot-overlap test on every sparse registry raster stay binding. If authorized, the next step is a new, pre-registered candidate with buffered hide-and-recover holdout (3 experiments, 2 hours), two-phase uniqueness on surface and final dots, and a validator. A passing file would still need your separate weekly-slot decision.
- **C — Ask the competition organizers** (DrivenData) whether NaN outside the footprint and the 0/1 dot format are accepted, and what the `[0, 1]` error means. This is a manual step that needs a logged-in account; the sandbox cannot do it.

## Verification boundaries

- Official reference links for manual review: [competition problem/format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [rules](https://www.drivendata.org/competitions/306/competition-doe-gems/), [data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [NLR format PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- Not fetched this session: DrivenData pages (not on the allowed-host list), current site HEADs and TIFFs (see the 14:56 `PARTIAL` feed in `research/session-5aeeb70b-review.md`).
- Per-site executive table (nine sites, file, claim class, uniqueness, estimate, submit flag) is kept in [`research/session-5aeeb70b-review.md`](session-5aeeb70b-review.md). Nothing in this session changes that table.

## Core values

**Maximize P(Win):** a file that fails the agreed uniqueness rule cannot win a slot, and a score forecast without holdout evidence would mislead. **Own the Outcome:** the decision that unblocks the TIFF is stated as a concrete question, with the three options and their consequences, so the next session can start immediately.
