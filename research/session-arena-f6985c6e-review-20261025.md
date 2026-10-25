# Workspace audit — `arena/f6985c6e-gemsdoe88` — 2026-10-25

## Decision

**No new TIFF was generated. Do not submit any file from this audit.** The required shared preflight did not complete in this checkout: `scripts/generation_guard.py` failed closed with `AUDIT_ERROR` because NumPy is unavailable, before loading the registry witness or entering feature/model code. The checkout also has no `data/` directory. Separately, the latest checked-in duplicate-stop evidence records a SHA-pinned full-footprint witness that directly covers every allowed pixel; under the repository's literal overlap definition, a nonempty candidate cannot satisfy the 70% limit. That historical, pinned proof is documented below, but this turn did **not** remeasure it.

This distinction matters: the new preflight attempt is an **environment/import failure**, not a fresh `DUPLICATE_STOP` measurement. The prior duplicate-stop record is evidence in the repository, not a successful result from this run. No candidate surface, model, holdout, dot placement, raster, upload, or weekly-slot decision was made here.

## Three review passes

### Pass 1 — inspect task contract and repository

- Read `README.md`, `PROMPT.md`, `USER_PROMPT_20261025.md`, `AGENTS.md`, and the latest review records before acting. The full user request is already preserved in the README and `USER_PROMPT_20261025.md`.
- Confirmed the working branch is `arena/f6985c6e-gemsdoe88` and the initial worktree was clean.
- The primary website and root `index.html` explicitly distinguish archived research downloads from a submission-approved file. The canonical status is `BLOCKED`, the current release labels the TDKL TIFF **“OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT”**, and it says no new TIFF was generated.
- Inspected the H33 owner build record at immutable GitHub commit [`fcb6674b4589c71db66560e71201072adf687931`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/fcb6674b4589c71db66560e71201072adf687931/registry/submission_build.json). Its SHA-256 is `0d7c5c3fb0079410e0d519fac45a36b37dc6136f2e42d5c6b2468a29397c478a`. It identifies H33-2-B2 as a 37,654-dot subset made by removing all 2,545 dots within 2 pixels (200 m) of the catalogue from a 40,199-dot H27-4 base; its stated rule removes the 6,436 points within 2 pixels from the 44,090-dot D2.8 parent. The record itself labels its `0.2747` value a **projection**, says **“NO ORGANISER SCORE EXISTS”**, and contains no submission-page receipt. The user's `0.2778` is therefore retained as **USER-REPORTED**, not independently established as an organizer score. The record suggests a plausible precision/coverage mechanism (remove near-catalogue redundancy), but cannot prove why the reported value occurred on hidden truth.

### Pass 2 — check execution safety, scientific prerequisites, and integrity

- Invoked `python scripts/generation_guard.py` before any builder or feature module. It exited nonzero with `AUDIT_ERROR: ModuleNotFoundError: No module named 'numpy'`; its output states generation was not allowed and zero rasters/experiments/slots were produced. No bypass was attempted.
- Tried to prepare an ignored local virtual environment with `python -m venv .venv` and install the declared requirements. Installation stopped at a package-hash mismatch for the NumPy wheel. Two downloads reported different SHA-256 digests for the same wheel URL, neither matching pip's expected digest. **This is an environment integrity warning, not a finding of malicious tampering.** No hash check was disabled and no package was installed.
- `data/` is absent in this checkout; the exact pinned preflight cannot be freshly executed without dependencies and inputs. Existing evidence `evidence/mtas88_preflight_20261025.json` records a prior `REGISTRY-MEASUREMENT`: the witness `17GEMSDOE` (`SHA-256 ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) directly covers 5,106,385 of 5,106,385 allowed cells. Its recorded universal lower bound is 1.0 against the 0.70 limit. This prior record suffices to explain the fail-closed project decision, but is not relabelled as a fresh measurement here. Surface correlation and an emitted candidate's final-dot overlap are **not measured** because no candidate exists.
- Confirmed a material historical-data irregularity: the machine hypothesis queue in `docs/data/repo_review_20261025.json` still ranks H88-MTAS as `UNTESTED`, while the repository separately archives a generated MTAS TIFF and a run card with a holdout result. The later review `research/session-fd5f1d8b-review.md` already flags this stale-queue conflict. Do not treat the old queue's rank/status as a current experiment authorization or evidence that MTAS remains untried.
- The immutable H33 build record's explicit “no organizer score” statement conflicts with any interpretation of the user-listed `0.2778` as a verified receipt. The evidence available here cannot resolve that conflict; only an organizer submission-page receipt can.

### Pass 3 — static verification and request reconciliation

- Python standard-library parsing succeeded for **309** repository Python source/test files and JSON parsing succeeded for **616** JSON files (including this run card); zero parse errors. This is syntax/serialization validation only, not unit-test execution.
- The full pytest suite, raster validators, site checks, artifact audit, and fresh holdout were **not run** because required dependencies and input rasters were unavailable. No score or validation pass is inferred from static parsing.
- The request requires a single lane paragraph but supplies no actual paragraph. No lane was invented. Four conditional ideas already recorded in `research/candidate-hypotheses-20261025-mtas.md` are geological hypotheses, not new discoveries or clearance: terrain-matched K:Th radiometry (`PRAN`), cross-catchment replicated drainage offsets (`FARC`), depth-conditioned temperature/conductivity residual (`TCONS`), and multi-sensor flight-line artifact rejection (`FLAC`). Their named mimics, layers, and methodological differences are in that file. The old MTAS entry is excluded from the untried queue because execution records conflict and a negative run is archived.
- No holdout was run: no feature-only leakage canaries, no withheld-positive count or confidence interval, and no comparison against the current holdout best are claimed. No feature stack, evaluator, writer, metric, or cached artifact was changed.
- No unique TIFF meeting the stated literal registry rule could be produced from the evidence available; the urgent “new eligible submission” requirement remains **UNMET**. Existing downloads remain clearly research-only. Zero competition slots were used.

## H33 interpretation and leaderboard question

H33 is best understood from its owner build record as an **emission/pruning change**, not evidence that the many geological models in GEMSDOE32 produced the selected raster. The exact recorded operation removes support close to the catalogue, reducing a 40,199-dot base to 37,654 dots; the H33 record calls the 0.2747 figure a model projection and expressly states no organizer score exists. Fewer redundant predictions can improve a precision-weighted distance score if they contribute little unique truth coverage, but may hurt if they were near hidden faults. The owner record alone does not measure that trade-off against the organizer's hidden truth.

Whether a new method beats `0.2778` is **NOT ESTABLISHED**. The cited H33 value is not authenticated here, no new candidate holdout was run, and leaderboard maxima supplied in the prompt are not fresh organizer evidence. Do not translate a local holdout, a projected score, or an archived user-reported result into an organizer-confirmed score.

## Sources for manual review and access boundary

- [Official DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [submissions page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/), and [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — linked for review; not authenticated or fetched in this audit.
- [Official NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR INGENIOUS record](https://gdr.openei.org/submissions/1391), and [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) — linked for review; no new external dataset was downloaded or proposed as currently obtainable in this session.
- [Official DrivenData reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution) — its repository identity was checked through GitHub's API. This is not evidence that local owner-mirrored data equals current organizer downloads, or that a GPU is required.
- [H33 owner build record, pinned commit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/fcb6674b4589c71db66560e71201072adf687931/registry/submission_build.json) — directly retrieved through GitHub API, SHA-256 recorded above; owner-authored, not an organizer receipt.

## Follow-up in order

1. Resolve the dependency integrity mismatch through a trusted package-index/cache path; do **not** ignore hashes. Then restore the pinned validation inputs via the repository's documented process.
2. Re-run `scripts/generation_guard.py`. Expect the recorded duplicate stop if the verified witness remains saturated; do not invoke a builder when it does.
3. Reconcile the stale hypothesis queue and MTAS timeline in the existing evidence chain without rewriting historical run records. If the literal overlap contract is still binding, stop before models/holdout/placement.
4. Only after an authorized shared-rule resolution, freeze one genuinely untried lane and test it with the shared buffered hide-and-recover evaluator, visible-only catalogue-derived features, pixel-exact visible mask, per-feature leakage canaries, same-fold incumbent, and paired spatial-block confidence interval.
5. Authenticate organizer inputs/rules and obtain a real submission-page receipt before claiming official validation or score. A separate selector must still approve any weekly slot.

**Outcome:** a negative, reproducible workspace audit—not a submission. No new TIFF was copied, renamed, built, or represented as eligible.
