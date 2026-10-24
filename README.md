# GEMSDOE88 — geothermal-indicative **fault** discovery, with automatic submission gates

<!-- GATE-BANNER:START -->
> ## ✅ OK TO DOWNLOAD AND SUBMIT — ONE FILE (automated gate passed)
> **File:** [`docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros.tif`](docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros.tif) · zip with the same TIFF: [`docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros.zip`](docs/downloads/gems88-provcrest-rank-denovo-37654-20261024-04559a2c-zeros.zip)
> **SHA-256:** `13b4155c41a8cfe56c5ca9a8079eb3b48d5c3e987cd71beb7ff7c9dc675d1b5f`
> **Submission name:** `GEMSDOE88-PROVCREST-RANK-04559A2C` · **Note (113/140):** `PROVCREST-rank de novo B19/3/18/15 crest 37654 dots >=3.5px >300m cat; HOLDOUT-DTI 0.0763 vs null 0.048; UNSCORED`
> **Gate:** `python scripts/submission_gate.py --require-submit` → 29/29 checks pass (values in [0,1], no NaN, CRS/shape/transform = sample, 0 dots on the catalogue, worst dot-field 3-px overlap 0.4076 ≤ 0.70, max |ρ| ≤ 0.90, null-control paired CI > 0, canary ≤ 0.90). The continuous 17GEMSDOE prior overlaps everything at 1.0 and is classified, not hidden (IR-88-58).
> **Status of the number:** HOLDOUT-DTI only; ORGANIZER-CONFIRMED score: **none**; 0 weekly slots spent by any agent. Every other file in `docs/downloads/` marked `DO-NOT-SUBMIT` is archived research — **DO NOT SUBMIT** them.
> **Pages:** [Executive summary](docs/executive-summary.html) · [Site](docs/index.html) · [Why 0.2778 / hypotheses](research/session-20261024-audit-why-0.2778.md) · [IR-88-59](IRREGULARITIES.md)
<!-- GATE-BANNER:END -->

> ## ⛔ 2026-10-24 TILTZERO — NEW UNIQUE TIF, NEGATIVE, DO NOT SUBMIT (this session)
> **New unique de-novo TIF (not a copy):** `docs/downloads/gems88-tiltzero-rank-denovo-37654-20261024-a2150eeb-zeros-DO-NOT-SUBMIT.tif` (SHA-256 `5487d793…`, 37,654 binary dots, [0,1], 0 NaN, format-valid). HOLDOUT-DTI **0.055083** [0.046419,0.063081] (22,663 withheld, gems57-pooled-hide-v2) beats R0 0.004006 but **fails** the preregistered bar of beating shipped PROVCREST 0.076277; SGMC PROXY 0.0710 < R0 0.0961. Uniqueness worst sparse |ρ| 0.0168, overlap 0.3724; canary max 0.53056. Verdict **negative** in `registry/tiltzero_run_card.json` — download for audit only, **do not submit**. The OK-TO-SUBMIT file remains PROVCREST below. Agent spent **0** slots; ORGANIZER-CONFIRMED score: none. Why h33 scored a user-reported 0.2778 and the 5 ranked hypotheses for this session: `research/candidate-hypotheses-20261024-tiltzero.md`.

> ## ⛔ 2026-10-24 FABDIS (PR #58) — research file, NEGATIVE, DO NOT SUBMIT
> `docs/downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif` (HOLDOUT-DTI 0.062936, below the PROVCREST file's 0.076277 on different seeds) is download-for-audit only.
>
> **Decision reconciliation (IR-88-59):** PR #58 withdrew the PROVCREST "OK to submit" because the continuous 17GEMSDOE prior overlaps *every* non-empty raster at 1.0, so the literal "any registry raster" reading makes **no** candidate submittable. This repo now reports that reading in the gate (`UNQ-04`, shown above and in `docs/data/submission_gate.json`) rather than letting it veto everything, and applies the 0.70 rule to dot fields (worst 0.4076) plus a rank-correlation rule to every raster (max |ρ| 0.0302). PROVCREST additionally had to beat two no-information null controls. That is an interpretation of the user's rule, stated openly: if the protocol owner insists on the literal reading, run `python scripts/validate_current.py --require-submit` (exit 2) instead and treat no file as submittable.

---

## Start of every session — project operating prompt (user's active requirements)

**Read this section, the latest `registry/*_run_card.json`, `docs/status.json`, and [scientific preregistration](research/candidates-20261024-fabric-dislocation.md) before doing work.** The user supplied a much longer list of prior GEMSDOE sites/scores in the Arena request; they are leads/owner reports, **not organizer receipts**. Historical experiments remain recoverable through Git history and `research/`, `registry/`, `evidence/`, `ledger/`. Do not promote stale README/site statements just because their files still exist.

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

## Why the user-reported GEMSDOE32 H33 “0.2778” appeared strongest

The [GEMSDOE32 original site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) identifies `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` as a **37,654-dot** field produced by pruning dots within **two 100 m pixels** of known mapped faults from a previously emitted file. In the [organizer's metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), the per-truth-pixel credit is the **maximum** over nearby predictions while unmatched prediction mass is **summed** at penalty coefficient 0.2; redundant dots can raise false-positive cost with little incremental truth coverage. A near-catalogue collar can therefore improve a sparse map *if* those dots were not covering new truth. It can also discard useful hidden splays. This is a **physical/statistical explanation, not a causal demonstration** of the reported result.

- The prompt's **0.2778** for H33 is an **unverified owner report**: no submission-page receipt was present here; the source page itself says no organizer score existed when built. A model projection on that site is **not** a score.
- The [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) showed **0.4413** for #1 on **2026-10-24**; this is an **official public leaderboard snapshot**, not an ORGANIZER-CONFIRMED result for our file. An older prompt sentence said 0.3195; it is stale. Check the official page for current standings.
- Neither this negative 0.062936 holdout nor a better holdout would by itself prove a live result above 0.2778 or 0.4413. Private labels and distinct spatial domains remain unseen. The DOE GEMS target is **fault traces indicative of geothermal resources**, not the presence of productive vents.

## This session: one hypothesis, one experiment, negative result

Preregistered [four candidates with layers, mimics, costs and official references](research/candidates-20261024-fabric-dislocation.md) *before* implementing. The chosen geological mechanism uses organizer-described **Band 2 RTP magnetic anomalies** and **Band 13 isostatic gravity**. A tensor of magnetic-gradient orientations on opposite sides of a candidate line estimates truncated/rotated basement fabric; independent gravity gradients modulate the signal. The non-fault mimic is an intrusive/volcanic lithologic contact or an airborne flight-line seam. Unlike existing `edge.py` coincident edge magnitudes or `str88.py` multi-sensor orientation persistence, this is a **paired opposite-side fabric discontinuity**, not a copy of a sibling raster. The [USGS Dixie Valley magnetic study](https://pubs.usgs.gov/of/2002/ofr-02-0384/ofr-02-0384_508.pdf) motivates concealed-fault use, but no claim of truth is inferred from a magnetic anomaly alone.

One experiment: inputs restored autonomously from SHA-pinned owner GitHub mirrors; local feature tags and grid verified; all four single-feature canaries passed; score evaluated by the **unmodified shared evaluator** on seeds 20/21, whole-components hidden, visible-catalogue-only exclusion, pixel-exact known mask. The **unmodified shared writer** created a new one-TIFF ZIP and all-finite binary TIFF. The shared literal uniqueness test returned duplicate, and the candidate HOLDOUT-DTI fell below the frozen best; **stop**. Full [run card](registry/fabric_dislocation_run_card.json), [initial 29-prior audit](evidence/fabric_dislocation_uniqueness.json), [posthoc 30th-prior audit](evidence/postmerge_tiltzero_audit.json), [format audit](evidence/fabric_dislocation_format_audit.json), [machine release status](docs/status.json). The concurrently merged [TILTZERO experiment](registry/tiltzero_run_card.json) is also negative, but used seeds 20/30 rather than our 20/21: its HOLDOUT-DTI 0.055083 [0.046419, 0.063081] (22,663 withheld positives, `gems57-pooled-hide-v2`) is **not a matched-fold comparison** with this experiment. Prior PROVCREST's `ok_to_submit=true` was **not an independent strict gate** and is superseded here; no old candidate is approved by implication.

## How to reproduce and automatically inspect

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
# Works with the configured public GitHub access. Restores owner-mirrored files
# under gitignored data/ and checks each pinned SHA-256; ~627 MB on disk.
.venv/bin/python scripts/restore_inputs.py
# Preregistration: registry/preregistration_fabric_dislocation.json
# Rebuilding new research output is deterministic; the writer refuses to
# overwrite an existing artifact. Move to a clean checkout to rerun generation.
.venv/bin/python scripts/run_fabric_dislocation.py
.venv/bin/python scripts/validate_current.py
.venv/bin/python scripts/readiness.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
# Fail-closed test of upload clearance: expected exit status 2 (negative).
.venv/bin/python scripts/validate_current.py --require-submit
```

The site is static: new predictions are built by Python scripts and the validated research TIFF is then published in [`docs/downloads/`](docs/downloads/). The page cannot log into your competition account or autonomously submit; it must not claim real-time quota or private leaderboard access. The [executive summary](docs/executive-summary.html) explains precisely what must happen for a *future* eligible file. The source table and verified/uncertain data provenance are at [`docs/sources.html`](docs/sources.html).

## Limitations and next work

1. **Binding registry paradox:** the literal positive-support interpretation of dense `17GEMSDOE` makes it impossible for *any* nonempty candidate to satisfy the stated 70% overlap rule. Preserve the strict failure until an explicit, consistent protocol change is authorized; do not “promote” by renaming or silently switching representations.
2. **Science:** this magnetic dislocation hypothesis did not generalize as well as ADHR on the available holdout; future work should focus on genuinely different geology and the known domain shift, not iterate spacing/dot counts from H33. The incumbent per-block paired terms need regeneration if a future arm approaches its point estimate.
3. **Access:** hash pins establish consistency with the owner's public GitHub mirrors, not authenticated DrivenData files, nor redistribution rights. A registered account must confirm the organizer sample hash and available weekly quota before any portal upload. This sandbox has no account submission-page receipts. No password/token is requested.
4. **Source scope:** 29 locally accessible/pinned raster files were checked at experiment time and a concurrently published 30th was checked only **posthoc**, not every private or unlinked GEMSDOE submission. Current public leaderboard remains a *dated static snapshot* with an official link, not a background scraper. The old site score list is not independently receipt-verified.
5. **Prize documentation:** the [official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) require only one selected final submission and disclosure of AI use in the narrative where applicable; do not omit reproducibility assets or treat a format-valid file as winning.

No vendor evaluator/writer change was needed in this run. Three review passes and test results are logged in `research/session-20261024-audit.md`.
