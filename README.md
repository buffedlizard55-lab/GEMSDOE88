# GEMSDOE88 — geothermal-indicative fault discovery

> ## Current automated decision — 2026-10-24
> **OK TO DOWNLOAD FOR RESEARCH: YES. OK TO SUBMIT: NO — DO NOT SUBMIT.**
>
> ### [⬇ Download current research GeoTIFF](docs/downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.tif) · [single-TIFF ZIP](docs/downloads/gems88-fabric-dislocation-20261024-621b097b-DO-NOT-SUBMIT.zip)
>
> - **Candidate name (archival):** `GEMSDOE88-FABDIS-621B097B-DO-NOT-SUBMIT`
> - **Short note (archival, under 140 characters):** `FAB88 RTP fabric-dislocation research raster; HOLDOUT-DTI 0.062936; 22,893 positives; DO NOT SUBMIT`
> - **TIFF SHA-256:** `1bbb20e60ce5633a979e2bea8e1216105325b78c4ca93ca4380ea3f533e774ae`
> - **Format validator:** PASS — single-band float32 GeoTIFF; EPSG:32611; `3730×3292`; exact mirrored sample transform; finite values in `[0,1]`; no NaN inside the footprint; zero mass outside. Validation is format-only.
> - **HOLDOUT-DTI:** `0.062936`, evaluator `gems57-pooled-hide-v2`, `22,893` withheld positives, 95% CI `[0.054201, 0.072122]`. Stored incumbent: **HOLDOUT-DTI** `0.187888` on the same evaluator. The run card contains no paired incumbent terms; do not infer a paired significance result.
> - **Leakage canary:** maximum symmetric single-feature AUC `0.551449`, below the preregistered `0.90` warning threshold.
> - **Uniqueness:** final dot overlap is `1.0` against the all-positive 17GEMSDOE witness, exceeding the strict `0.70` ceiling. The literal rule is impossible for any non-empty raster while that positive-everywhere raster remains in scope. No exemption has been authorized.
> - **Slots/receipt:** `0` slots used; no ORGANIZER-CONFIRMED score; no submission has been made.
>
> **Do not upload this TIFF or ZIP.** The downloadable file is a new research artifact, but it is a duplicate under the required literal overlap test and did not beat the stored holdout best. It has not been proven unique against every private or unlinked competition submission.

**Live site:** [`docs/index.html`](docs/index.html) · **Exact submission guide:** [`docs/executive-summary.html`](docs/executive-summary.html) · **Complete standing prompt:** [`PROMPT.md`](PROMPT.md) · **Current run card:** [`registry/fabric_dislocation_run_card.json`](registry/fabric_dislocation_run_card.json) · **Current saved-byte audit:** [`docs/data/current_release.json`](docs/data/current_release.json).

## Project mission and operating values

The GEMS Prize asks for predictions of **geological faults indicative of geothermal resources**, not direct prediction of vents. The project develops reproducible geological hypotheses, evaluates them with spatially blocked hide-and-recover HOLDOUT-DTI, and emits a competition-format GeoTIFF only when automated validators pass. The human/portfolio selector decides whether to spend a competition slot; this software never logs in, uploads, or selects a submission.

**Maximize P(Win)** by preferring evidence-backed, genuinely distinct candidates over speculative leaderboard chasing. **Own the Outcome** by reporting negative results, repairing inconsistencies, and separating local holdout estimates from organizer receipts.

## What we learned about H33 (`h33-h33-2-b2`)

The local forensic report (`research/h33-forensics-20261024.md`; source measurements in `evidence/h33_forensics_20261024.json`) finds a strict subset lineage: H19-5 → D2.8 → SOLO-D2.8 → H33 only removes dots. Measured geometry shows that removed D2.8 dots were concentrated close to the known-fault catalogue, while H33's spacing is near the official metric's 300 m support radius. This is consistent with the metric's max-credit behavior: nearby redundant predictions can add false-positive cost without proportionate additional true-positive credit. The numerical score attribution is an inference from user-reported results, not a causal experiment.

**H33 `0.2778` is USER-REPORTED in the repo, not ORGANIZER-CONFIRMED.** The official [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) currently displays `0.4413` at the top (checked 2026-10-24), so `0.2778` is not the competition's current highest public score. The leaderboard is linked live; this project does not automatically scrape it. A model projection or holdout result is never a public score.

The official [competition description and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) specify expert-labeled faults missing from public fault inventories, a single-band GeoTIFF prediction, values in `[0,1]`, a 300 m triangular distance kernel, and Tversky weights α=0.2 / β=0.8. See the [official NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).

## Current hypothesis and why this session stopped

The latest preregistered method lane in `registry/preregistration_fabric_dislocation.json` tests whether a paired-side RTP magnetic fabric rotation, corroborated by gravity-gradient energy, can expose basement-fault offsets without a mapped trace. Its named non-fault mimics are intrusive/volcanic lithologic contacts and airborne magnetic flight-line seams. This lane already has a completed experiment and a de-novo TIFF; rebuilding it or privately forking the evaluator/writer would violate the reuse-and-stop protocol.

Its results are negative: the TIFF is format-valid, but **HOLDOUT-DTI** is below the stored incumbent, while a positive-everywhere registry raster guarantees a `1.0` final overlap. The experiment reports a pre-placement maximum `|ρ|=0.062661`; post-placement uniqueness still fails. Thus there is no scientifically and procedurally eligible submission. The next step is a protocol/registry policy decision plus the next authorized, preregistered lane—not a filename change, an upload, or another run of this failed method.

Prior candidate hypotheses, their physical rationale, mimics, costs, and data-access limitations are collected in [`research/hypotheses-20261024.md`](research/hypotheses-20261024.md), [`research/candidate-hypotheses-20261023.md`](research/candidate-hypotheses-20261023.md), and [`research/review.md`](research/review.md). The leading genuinely new-data proposal, dry-season Sentinel-2 phreatophyte/spring lineaments, is **not runnable in this sandbox** because the required data endpoints are outside the permitted network access and the competition data account is not authenticated. Do not call it validated or a viable experiment until source access and the challenge-sharing license are checked.

## One-click project workflow

1. Read the complete standing prompt in [`PROMPT.md`](PROMPT.md) at session start; preserve **Maximize P(Win)** and **Own the Outcome**.
2. Inspect the current verdict and its source card above; verify the `.tif` SHA-256 before relying on it.
3. Run the static site guard, readiness gate, and independent current release gate:

   ```bash
   python scripts/check_site.py
   python scripts/readiness.py
   python scripts/validate_current.py
   python scripts/validate_current.py --require-submit  # expected exit 2: no submission is approved
   ```

4. For a future approved candidate, follow [`docs/SUBMIT.md`](docs/SUBMIT.md) and [`docs/executive-summary.html`](docs/executive-summary.html). This current TIFF is explicitly **DO NOT SUBMIT**.

## Data access, reproducibility, and limitations

- The current TIFF's format was independently checked against a SHA-pinned owner mirror of the competition sample; this is **not** an authenticated organizer download.
- The full competition `training_features.tif`, `labels.tif`, and DEM link list require DrivenData access; the account was not authenticated here. The 19-band training stack is not present in this checkout, so the latest experiment cannot be retrained from scratch in this session.
- Registry inventory is the SHA-pinned accessible public mirror plus locally tracked candidate rasters, not a complete view of private/unlinked submissions. The 17GEMSDOE positive-everywhere witness itself makes literal all-raster dot overlap equal `1.0` for every non-empty prediction; this policy conflict must be resolved explicitly, not bypassed.
- The hidden labels, public/private leaderboard partition, full organizer submission set, and upload receipts are not available locally. The competition's official [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) requires team authentication. No agent used a submission slot.
- Competition-provided and supplemental data must have an appropriate license that permits use and sharing with the sponsor. See the official competition page and rules before adding any data.

## Trusted source links

| Source | What we use it for |
|---|---|
| [DrivenData problem, metric and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Official fault-discovery task, available features, DTI and submission requirements. |
| [Live DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Current public scores; any copied score is date-stamped and distinguished from local holdout. |
| [DrivenData data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Authenticated competition inputs; not accessible without team login. |
| [Official NLR challenge rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Eligibility, submission, and prize-round rules. |
| [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | Official baseline and reproducibility reference. |
| [USGS GeoDAWN data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Official survey context for magnetic/radiometric features. |
| [INGENIOUS project](https://gbcge.org/current-projects/ingenious/) | Project context for geothermal-system data. |
| [EPSG:32611](https://epsg.io/32611) | UTM Zone 11N CRS reference. |

## Three-pass review record

- **Pass 1 — implementation/current state:** resolved the actual current artifact from the machine run card and independently reopened its TIFF against the restored sample. The latest completed method lane already emitted the research-only TIFF.
- **Pass 2 — bug review:** found the site, README, and `readiness.py` describing older LBCAL/MRR candidates while `validate_current.py` and `docs/data/current_release.json` identified fabric-dislocation. Reconciled the landing page, submission guide, and README to the current canonical artifact; updated readiness to derive status from the same validator.
- **Pass 3 — requirement recheck:** re-run the site link/status checks, current-format audit, readiness, complete tests, and diff review. The scientific and literal uniqueness blockers remain; the correct result is **negative**, not a claim of a winning submission.

## Standing operating requirements

The carried-forward operating prompt and acceptance criteria from [`PROMPT.md`](PROMPT.md) are reproduced below and must be re-read at the start of every session. This is the repository's consolidated working brief, **not a byte-exact transcript of every historical user message** (as disclosed in `PROMPT.md` / IR-88-68).

---

# Standing prompt for GEMSDOE88 (DOE GEMS Prize, DrivenData competition 306)

> **Read this file at the start of every session.**  It is linked from the top of `README.md`.
>
> **Honesty note (IR-88-68).**  The owner's original prompt text is longer than what any one
> session can see.  This file preserves the **acceptance criteria and constraints exactly as they
> were carried into the 2026-10-24 session brief**; wording is condensed, nothing was added or
> softened.  It is *not* a byte-exact copy.  If byte-exact preservation matters, paste the
> original below the marker `

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
