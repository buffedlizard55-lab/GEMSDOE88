# GEMSDOE88 three-pass research and repository review — session 75aeb674

**Review date:** 2026-10-26 UTC
**Branch:** `arena/75aeb674-gemsdoe88`
**Scope:** GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36; GEMSDOE88’s current pre-placement gate, source/data pins, run cards, release/status feed, and the requested H33/score assessment.

## Executive decision

**`DUPLICATE_STOP`; no submission file was produced.** The prescribed preflight exits `2` before constructing features or placing dots. The pinned raster `data/registry/dense_17gemdoe.tif` (SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) covers all `5,106,385` allowed off-catalogue pixels. Under the repository’s literal support rule (`finite prediction > 0`) and the required pixel-exact visible-fault mask, **every permitted nonempty candidate has a measured lower bound of 100% 3-pixel overlap** with that witness, above the frozen `70%` limit. This is a registry measurement, not a performance score. There is no policy authorization to exempt the dense raster.

The full locally pinned training/external stack has now been restored; `scripts/audit_research_state.py --check-inputs` passes. That does not override the duplicate stop. This session ran **zero experiments**, performed **zero feature fits/canaries/holdout evaluations**, placed **zero dots**, wrote **zero new TIFFs**, and used **zero weekly slots**. Thus there is no new `HOLDOUT-DTI`, no candidate raster SHA-256, and no submission receipt.

The full evidence is in:

- [negative run card](../registry/session_75aeb674_run_card.json) (mirrored to [`docs/data/`](../docs/data/session_75aeb674_run_card.json));
- [current focus-site `main` head recheck](../evidence/focus_sites_current_head_recheck_20261026.json);
- [official public leaderboard observation](../evidence/official_public_leaderboard_20261026.json);
- [three ranked untested proposals](session-75aeb674-hypotheses.md).

### Current public leaderboard versus the prompt’s quoted high

I fetched the official [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) on 2026-10-26. It showed **rank #1 `xiaofanhu`, public best DW-Tversky `0.4437`** (`31` submissions displayed; page activity text “1h 39min ago”). Evidence class: **`OFFICIAL-PUBLIC-LEADERBOARD-OBSERVATION`**—a live public standings observation, **not** a `HOLDOUT-DTI` result and not an artifact-linked submission-page receipt for GEMSDOE88 or a focus-site raster. The prompt’s `0.4413` and older `0.3195` claims do not describe the top row on this retrieved page; the live board may change later.

The focus-site top claim remains **GEMSDOE32 `0.2778` (`USER-REPORTED CLAIM`)**. Its artifact SHA is verifiable, but its score is not: the current GEMSDOE32 Round-6 card labels the champion `0.2778` `OWNER-REPORT; no receipt in repo`; the current R6 artifact is explicitly marked never submitted and no organizer score exists for it. Do not compare that claim to a holdout number or call it organizer-confirmed.

## Nine strongest reported files: artifact and lineage review

**Every value in the `reported value` column is a `USER-REPORTED CLAIM`, not `HOLDOUT-DTI` and not `ORGANIZER-CONFIRMED`.** The old pixel audit is at [`docs/data/focus_sites_20261026.json`](../docs/data/focus_sites_20261026.json). This session freshly queried each current `main` tree and SHA-256 verified that all nine historical champion TIFFs are still byte-for-byte present at those current heads. Therefore the old champion pixel/set-lineage findings remain applicable to those *same nine files*, even though the earlier audit’s repository-head metadata is now stale. The refreshed heads, exact current paths and Git blob identifiers are captured in [`focus_sites_current_head_recheck_20261026.json`](../evidence/focus_sites_current_head_recheck_20261026.json).

| Site | Strongest reported value¹ and artifact family | Forensic finding on the reported artifact | Fresh current-head / score caveat |
|---|---|---|---|
| GEMSDOE24 | `0.2477` — H19-5 `D1.5` thinning | 60,069 dots; an H19-5 ridge-thinning parent, with 1.0000 3-px overlap against the local dense witness in the prior pixel audit. | Current `main` adds [CRP1](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/17496743a9695974370512db64d8140ea1ccfd2f/docs/data/crp1_run_card.json), [DPRF1](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/17496743a9695974370512db64d8140ea1ccfd2f/docs/data/dprf1_run_card.json), [TNR1](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/17496743a9695974370512db64d8140ea1ccfd2f/docs/data/tnr1_run_card.json) and [TRSG1](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/17496743a9695974370512db64d8140ea1ccfd2f/docs/data/trsg1_run_card.json) cards; the retrieved cards are negative / not cleared and give no organizer receipt. |
| GEMSDOE25 | `0.2600` — H19-5 `D2.8` thinning | 44,090 dots; exact positive-pixel duplicate of the GEMSDOE30 `D2.8` file. | Current [H71](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/88a29e094989b0e23916136e593474875d067656/registry/run_card_h71_2026-10-26.json) is negative; [APFL](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/88a29e094989b0e23916136e593474875d067656/registry/run_card_apfl_2026-10-26.json) is research/testing-only, without slot approval. |
| GEMSDOE27 | `0.2449` — `T-v2` links on the `D1.5` set | 61,328 dots; the advertised `0.2715` GEMSDOE28-prefixed filename does not exist. The stored matching file belongs to GEMSDOE27, has the same SHA as this `0.2449` file, and is byte-identical across the two repositories. | A new [H31-S10 local run card](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/426426b402f90f4e0786990b4edd261d9dd48085/evidence/h31_s10_run_card_2026-10-26.json) says `promote`/`ok_to_submit: true` under GEMSDOE27’s local process. That is not a score receipt or a clearance under GEMSDOE88’s stricter all-registry gate. |
| GEMSDOE28 | `0.2710` — H36-1 rung30 blind candidate | 37,660 dots; the prompt’s `0.2715` is the misattribution above. The historical pixel audit found 99.88% 3-px proximity to H33-2-B2. | Current [S20](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/348ff086e29b9c48bb7104daacb647af31a184bf/docs/data/run_card_s20_2026-10-26.json) / [NCHC](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/348ff086e29b9c48bb7104daacb647af31a184bf/docs/data/run_card_s20_nchc.json) candidates are negative. The current [GEMSDOE28 README](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/348ff086e29b9c48bb7104daacb647af31a184bf/README.md) repeats `0.2708` as a USER-REPORTED H27-4 value; it is not a receipt. An [older H28 static-page snapshot](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/33cc5942220f1440531d7184889c5c6f5d2f0a3e/docs/index.html#L77-L80) labels H27-4 `UNSCORED`, so the owner records conflict by version. |
| GEMSDOE30 | `0.2600` — D2.8 Poisson set | 44,090 dots; exact duplicate of GEMSDOE25’s `0.2600` artifact. | Current `main` contains an older [G30-S19 lane card](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/73db382d3c990d0aa0b5126997a67213cc56dee4/docs/research/2026-10-25/lane-g30s19-run-card.json) whose top-level `promote` wording conflicts with its own duplicate-stop scope and incomplete registry note; the separate [2026-10-26 review card](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/73db382d3c990d0aa0b5126997a67213cc56dee4/docs/research/review-2026-10-26/run-card.json) records no new experiment. Neither is an organizer score. |
| GEMSDOE31 | `0.2708` — H27-4 SOLO-D2.8 copy | 40,199 dots; exact positive-pixel set match to GEMSDOE28’s H27-4 SOLO file; itself a subset of D2.8 with the catalogue-flank cells removed. | The current [score ledger](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/e6e85b357914068b3ba57ace0f899dde13f110a6/registry/score_claims.json) has `official_score_receipts: []`. It records `0.2708` as user-reported/unverified; current GEMSDOE28 README repeats the value for H27-4, while GEMSDOE31’s imported owner-mirror note cites an older H28 page version that called the file UNSCORED. This is a versioned owner-record discrepancy, not organizer confirmation. Current [H31-S](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/e6e85b357914068b3ba57ace0f899dde13f110a6/evidence/h31s/run_card.json) is negative. [H31-J](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/e6e85b357914068b3ba57ace0f899dde13f110a6/evidence/h31j/run_card.json)’s local “promote” wording coexists with a failed literal shared-registry check and `ok_to_submit: false`—not final clearance. |
| GEMSDOE32 | `0.2778` — H33-2-B2 | 37,654 binary dots; exact subset of H27-4 SOLO-D2.8 after removing 2,545 cells in the 100–200 m catalogue collar; the historical audit found no dots inside 200 m of the catalogue. | Highest *reported* focus-site claim, not a verified score. The [current release review](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/9e55d5d61cb748533691ed183b1b2f2e04643add/evidence/current_release_review.json) and [A8A card](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/9e55d5d61cb748533691ed183b1b2f2e04643add/evidence/arena8a_run_card.json) are negative/no-authorization; Round 6 was not submitted. |
| GEMSDOE33 | `0.2632` — H33D analog tip/step-over | 41,865 dots; 99.71% 3-px overlap with H19-5 in the earlier exact geometry audit. | Current [A33-R2](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/fded538406627b8d154a2fef5b5331f656d7e0f2/evidence/a33_r2_run_card_20261026.json) is marked duplicate; [G33](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/fded538406627b8d154a2fef5b5331f656d7e0f2/evidence/run_card_g33_20261026.json) is negative. No receipt found in the reviewed run cards. |
| GEMSDOE36 | `0.2750` — Anderson geothermal PINN set | 38,854 dots; exact superset of H33-2-B2 (37,654 base dots plus 1,200 additions); the reported score is below H33’s claim. | Current [ATVR36](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/4938a123133b4747079cc1c1c93a11e50c1376a7/evidence/atvr36_run_card_20261026.json) is `DO_NOT_SUBMIT`; no organizer receipt was present in the retrieved card. |

¹ `USER-REPORTED CLAIM` for every number in this table. No historical focus-site artifact was accompanied by an artifact-linked submission-page receipt in the reviewed records.

### Current-head reconciliation and scope limit

All nine source repositories advanced from the heads recorded in the prior pixel audit. The GitHub compare inventory contains **65 changed download/research TIFF paths** across those nine current heads (including NaN/zero variants and research artifacts); the refreshed JSON records each path and Git blob SHA. The nine original champion TIFF bytes were independently fetched from current `main` and matched the old SHA-256 values exactly. That makes the historical champion comparison current for those exact files.

This is **not** a fresh all-to-all spatial correlation scan of every one of the 65 newly changed rasters. The latest sibling run cards use different local evaluators, partial registry scopes, and in some cases contradictory local `promote` labels; treating those as a single comparable score/uniqueness register would be misleading. For GEMSDOE88 generation, the universal 17GEMSDOE support witness is already a decisive fail-closed counterexample for every candidate allowed by the assigned mask, so no candidate surface or dots were built. A separate, fully authorized revision of the binding scope would be needed before a new surface/dot novelty scan could be meaningful.

## GEMSDOE31 current score-ledger reconciliation

I read the current `GEMSDOE31` `registry/score_claims.json`, `registry/user_reported_scores.json`, `registry/current_run.json`, `registry/h31s_current_run.json`, `docs/data/submissions.json`, `evidence/h31j/run_card.json` and `evidence/h31s/run_card.json` from the current `main` head.

- `registry/score_claims.json` explicitly reports an empty official-receipt list. The `0.2708` H27-4 claim is user-reported and unverified; current GEMSDOE28 README repeats it for H27-4, while the H31 ledger cites an older H28 snapshot that called the artifact `UNSCORED`. Record this as a versioned owner-source discrepancy; it does not establish a submission-page receipt or organizer-confirmed score.
- The current `docs/data/submissions.json` says no file is approved for competition submission and no organizer receipt exists; the active research recommendation is null.
- Current H31-S has a negative run card, with both discrete and literal shared-registry uniqueness marked failed. Current MAGREST is also negative.
- H31-J’s card uses local “scientifically promoted” wording but says its literal shared-registry phase failed, `ok_to_submit` is false, and separate human slot selection is pending. Do not shorten that to “approved.”

These are provenance/governance findings, not leaderboard measurements. This structured reconciliation is also summarized in the current-head evidence JSON.

## Why H33 may have appeared to score well—and what is not known

The H33-2-B2 construction is a useful *mechanistic explanation candidate*, not a causal score audit:

1. **The metric rewards recovery strongly.** The official challenge metric uses a triangular 300 m distance kernel with `alpha = 0.2` on false-positive mass and `beta = 0.8` on false-negative mass. At the 100 m grid, predictions within three pixels can receive partial credit. This can favor broad blind-fault coverage over a more precise but low-recall map.
2. **The geometry is thinned and catalogue-pruned.** The reported H33 file contains 37,654 dots and is an exact subset of the H27-4 SOLO-D2.8 point set, removing the 2,545 100–200 m collar points. Thinning can reduce redundant nearby predictions; excluding the known-fault collar can avoid wasting prediction mass on already mapped faults.
3. **Regional lineaments can transfer.** A H19-5-derived ridge/lineament set may align with real but unlabelled structures and H33’s broad off-catalogue coverage. That is a plausible geology/geometry mechanism, not proof that every ridge is a fault or that this mechanism caused a specific public score.
4. **The official kernel tolerates spatial offset.** A near miss inside the kernel radius can still earn partial true-positive credit. This can help a coarse lineament geometry under the challenge metric even when it does not locate the fault centerline precisely.
5. **The false-positive and mimic risks remain material.** Dense ridges, pluvial shorelines, terrace risers, lithologic contacts, and survey artifacts can resemble faults. Extra dots away from any hidden fault still pay false-positive cost. The old pattern may be a geometry/metric interaction rather than better geological discrimination.

The official metric equations in [`vendor/gems57/metric.py`](../vendor/gems57/metric.py) distinguish truth-side saturation (`TPw`) from dot-side false-positive mass; a cluster of dots does not become free merely because several predictions are close to one truth. Nothing in the retrieved records establishes H33’s exact organizer score. The H33 `0.2778` value remains `USER-REPORTED CLAIM`; no score attribution, hidden labels, or causal decomposition can be inferred from the TIFF alone.

### Can GEMSDOE88 demonstrably beat H33 or the public leader?

**Not from the evidence available under the current gate.** The active queue’s first conditional idea is H88-SPR, followed by H88-AWA and H88-CBC (details in the hypothesis report). H88-SPR is a scientifically plausible, source-bound test but has no experiment, holdout result, score projection, or candidate artifact in this session. No honest statement that it will exceed H33’s user-reported value or the official public leader can be made. The official public leaderboard value is not a comparable local holdout score, and the H33 user-reported value is not a verified receipt.

The limiting factor is not missing local data now: full pins were restored and checked. It is the unmodified literal uniqueness rule. A permitted nonempty output necessarily fails before placement. **Do not bypass or silently reinterpret it to force a TIFF into existence.**

## Sources checked

- [Official DrivenData challenge page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — objective, hidden GeoDAWN-region test faults, DTI definition/kernel, raster grid/format, and rules for licensed/shareable external data.
- [Official DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — dynamic public standings; snapshot evidence stored in [`evidence/official_public_leaderboard_20261026.json`](../evidence/official_public_leaderboard_20261026.json).
- [Official reference solution README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/main/README.md) — baseline reference, not evidence that a particular raster is accepted or scored.
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI `10.5066/P93LGLVQ`, CC0 — survey context only.
- [GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/) and [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391), DOI `10.15121/1881483`, CC-BY — data-compilation metadata; does not authenticate locally mirrored bytes.
- [Hanks et al. (1984), USGS publication record](https://www.usgs.gov/publications/modification-wave-cut-and-faulting-controlled-landforms), DOI `10.1029/JB089iB07p05771` — scarp-profile ambiguity and wave-cut shoreline mimics.

## Three review passes and acceptance checklist

### Pass 1 — implementation/inventory and reproducibility

- Read the request copy, repository instructions, active status/release manifests, source-bound hypothesis queue, preflight/generation guard, shared metric/writer and current release card.
- Restored the full training plus external input stack with `scripts/restore_inputs.py`; `scripts/audit_research_state.py --check-inputs` passed against the pinned mirrors.
- Ran the shared preflight before any feature construction; it returned `DUPLICATE_STOP` (expected exit `2`). No feature, model, holdout, dot, or TIFF generation occurred.
- Queried current GitHub `main` heads for all nine sites; exact-SHA rechecked all historical champion files; reviewed current run-card and score-ledger paths. The previous pixel table is now tied to unchanged bytes, while new files are clearly marked outside its pairwise pixel scope.

### Pass 2 — adversarial review and irregularities

- Checked reported scores separately from holdout numbers and public leader standings. No focus-site historical score was promoted to `ORGANIZER-CONFIRMED`.
- Reconciled the user’s `0.4413` leaderboard claim against the retrieved official public page (`0.4437` at observation time); the public row is not tied to any local artifact.
- Found the GEMSDOE28 `0.2715` filename/site mismatch; a versioned source discrepancy around the GEMSDOE31 `0.2708` claim (current H28 README repeats it as user-reported for H27-4, while H31's imported older H28 snapshot labels that artifact `UNSCORED`); and local `promote` wording at GEMSDOE27/30/31 that does not override missing receipts, incomplete local scopes, or explicit literal-gate failures.
- Confirmed the original nine reported champion rasters’ current-main SHA-256 values match the prior audit. Did not overclaim an all-to-all scan of 65 changed current-head rasters.

### Pass 3 — line-by-line prompt and verification

- Kept the single-method-lane and pre-placement requirements: no method was executed because no lane was assigned and the universal duplicate gate blocks first.
- Did not copy the H33 raster, construct candidate features, fit a model, perform a holdout, place dots, write a new TIFF, or spend a slot. The run card marks all candidate-raster/holdout fields not run/null.
- Ranked three genuinely different, repository-unimplemented geological hypotheses with layers, signatures, off-catalogue rationale, mimics, repo differences, relative potential and cost; no numerical score projections.
- Verified the current public leaderboard and the cited official geology/data sources. Explicitly separated owner mirrors from authenticated official downloads/license proof.
- Refreshed the machine-readable negative run card and `docs/status.json` review pointer; no site candidate banner or TIFF release was added.

## Verification results

The following are review/test counts, not model scores:

- Full test suite: **923 passed, 23 skipped, 70 warnings**.
- `scripts/audit_research_state.py --check-inputs`: **PASS** after full input restore.
- `scripts/preflight_mtas88.py --gate-generation`: **DUPLICATE_STOP**, expected exit `2`.
- `scripts/generation_guard.py` (normal and optimized Python): expected exit `2`, fail-closed.
- `scripts/audit_downloads.py --check`: 50 archived TIFFs audited, 0 protocol-eligible.
- `scripts/audit_submissions_dir.py`: 21 packages pass local format/package checks, 0 protocol-eligible.
- Focus-site historical audit (normal/optimized Python): pass for its pinned evidence; `--require-submit` denies as expected. Current-head SHA reconciliation is separately stored in the refreshed JSON.
- `scripts/audit_literal_protocol.py`, `scripts/render_decision.py --check`, and `scripts/check_site.py` (normal and optimized Python): pass.
- Fresh headless browser receipt [`evidence/session_75aeb674_browser_check.json`](../evidence/session_75aeb674_browser_check.json): **PASS** for seven page/view combinations, no overflow or console errors, fail-closed fetch, no-JavaScript negative banner, and matching archive TIFF request/click SHA-256. This is presentation/download verification—not model or organizer-score evidence.

## Download, submission and run-card status

- **New TIFF:** none; `raster_sha256: null`.
- **Candidate validator:** not run because no candidate raster exists. The separate pre-existing H88-TDKL educational file remains format-valid only: `docs/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif`, SHA-256 `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`; it is **research download only, not slot-approved, and not the requested new unique submission**.
- **Internal audit identifier:** `GEMSDOE88-75AEB674-NO-FILE` (not for the portal).
- **Internal short note:** “No TIF built: DUPLICATE_STOP (registry covers allowed grid); no HOLDOUT-DTI; UNSCORED; DO NOT SUBMIT” (within the 140-character limit; not for the portal).
- **HOLDOUT-DTI:** `NOT_RUN_PREPLACEMENT_DUPLICATE_STOP`; evaluator if unblocked `gems57-pooled-hide-v2`; withheld-positive count and 95% CI are null because there was no prediction.
- **Organizer-confirmed score:** null; no submission-page receipt exists for this session.
- **Decision:** `DUPLICATE_STOP`; `ok_to_download_for_research: true` only for existing clearly quarantined research artifacts; `ok_to_submit: false`; `0` experiments; `0` new rasters; `0` weekly slots.

**Next safe action:** do not run H88-SPR/AWA/CBC unless the user/selector explicitly revises the scope of the binding all-registry rule and authorizes a fresh lane. Any such policy revision must be explicit and must retain the holdout, leakage, mask, current-head registry, writer, and validator gates. Do not silently exempt the dense witness.
