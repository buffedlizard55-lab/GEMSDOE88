# Three-pass repository review — 2026-10-25, session 693b10af

## Decision first

**Download archived research: YES. Submit to the competition: NO — DO NOT SUBMIT.**

**No new protocol-unique TIFF was generated. This highest-priority requirement remains unmet.** No historical TIFF was copied, renamed, or presented as a new submission. No weekly slot was used. This review did not fit a new model, construct proposed features, run a new canary/holdout, or claim an organizer score.

The existing canonical [research TIFF](https://buffedlizard55-lab.github.io/GEMSDOE88/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif) and [one-TIFF ZIP](https://buffedlizard55-lab.github.io/GEMSDOE88/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.zip) remain for education/audit only. On GitHub, use the same paths under `docs/`. Their immutable identities remain in `docs/data/current_release.json`. A strict local format pass does not authorize a competition slot.

Machine record: [negative run card](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_693b10af_run_card.json). Current proposals: [four ranked hypotheses](session-693b10af-hypotheses.md). The complete human request remains embedded in README and recorded in `USER_PROMPT_20261025.md`; the same full request was reissued for this session. It contains no actual single-method paragraph, so this is explicitly a software/evidence review, not an invented active geological lane.

## Binding pre-placement result

The shared `scripts/generation_guard.py` was run on restored, SHA-pinned inputs **before** any proposed feature construction, fit, placement or prediction export. It returned **DUPLICATE_STOP, exit 2**. The pinned witness is:

- [17GEMSDOE source at the immutable restored commit](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif).
- SHA-256: `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`.
- **REGISTRY-MEASUREMENT**, not a performance score: all **5,106,385** allowed pixels are directly in its positive support; uncovered allowed pixels = **0**.

For every nonempty allowed candidate dot set D, the literal forward overlap is therefore `|D|/|D| = 1.0`, exceeding the requested `0.70` limit even without the 3-pixel halo. This sufficient proof precedes construction of any surface. Surface/final-dot rank correlations and final-dot overlap are **not measured for a nonexistent candidate** and are null in the run card, not invented zeros. The mathematical lower bound is not an exhaustive fleet scan or clearance.

The conflict is in the project protocol, not a claim that an organizer prohibits dense probability rasters. A representation-aware alternative might be a reasonable proposal, but this session does **not** authorize it. No prior is removed or exempted; no private evaluator/writer is introduced; the shared core evaluator, holdout and submission writer are unchanged.

## What this review actually repaired

### 1. Unsupported legacy GHMD clearance and organizer label

At the starting commit, `run_card.json`, `docs/data/run_card.json` and `evidence/run_card.json` still said **promote** and called the unreceipted H33 user claim organizer-confirmed. A unit test explicitly required that false label. The evidence copy also referenced pre-quarantine filenames and a different historical ZIP hash.

Correction **IR-88-693B10AF-01**:

- All three copies now agree byte for byte, are explicitly historical, `verdict=negative`, `ok_to_submit=false`, and cannot authorize a slot.
- Organizer-confirmed values are null; the supplied H33 figure remains a labeled **USER-REPORTED CLAIM**, not a fabricated receipt.
- Original discriminating-only uniqueness measurements remain historical diagnostics; binding uniqueness is false and the literal overlap stop is explicit.
- Original metadata hashes, source commit, former flags and submission identities are preserved in `evidence/ghmd88_clearance_withdrawal_20261025.json` for audit. Original experimental measurements are **not** recast as fresh science.
- The legacy generator can no longer recreate the false organizer label/promotion, even though its existing shared guard already prevents execution. Its success message no longer says all gates passed.
- **No TIFF or ZIP bytes changed.** Independent saved-byte audits remain separate from this metadata correction.

### 2. An executed method was still recommended as untested

Correction **IR-88-693B10AF-02**: MMRX magnetic-marker restoration is already implemented and has a negative run card in this checkout. MTAS and MFS are also historical evaluated mechanisms. The primary site and `NEW_HYPOTHESES.md` no longer recommend them as fresh, never-run ideas.

`registry/hypothesis_queue.json` now distinguishes those evaluated records from **four still-unrun precise variants**: SPR profile restoration, AWA alteration-width asymmetry, GTD potential-field source dimensionality, and CBC conductive basin-breach connectivity. SPR is a conditional research first choice, **not** a selected submission or authority to bypass the stop. The proposals name exact restored layers, physical contrasts, off-catalogue rationale, implementation differences, non-fault mimics, uncertainty, cost and falsification tests.

`python scripts/audit_research_state.py` checks the source fingerprint, retired run-card pins, published queue copy and withdrawn legacy metadata/artifact identities. `--check-inputs` also hashes all required restored inputs; `--require-submit` must exit 2 after a successful metadata audit. This source fingerprint detects code drift, **not** semantic/worldwide novelty or geological truth. The old dated review is explicitly labeled a historical hypothesis/source-access replay; invoking it does not freshly fetch official pages or prove its old proposals are still untried.

### 3. Floating dependencies broke reproducibility

Correction **IR-88-693B10AF-03**:

- The first unconstrained install selected NumPy 2.4.6 and was rejected by pip's artifact-hash check: expected `89cd468399cfd2504718f0ba50e410dca55a170b61a02ad92bb18c8a65186e93`, received `7d8752d8655996304f8250980aea9f4f8135cc7d3b72c996f936a3adf8e2f793`. Its cause was **not established**. No hash check was disabled and the rejected wheel was not installed.
- A verified exact-version install using NumPy 2.3.4 succeeded. The first full test run found **792 passed, 1 failed, 23 skipped**. The failure was the historical byte-exact R0 rebuild under Rasterio 1.4.3: decoded lineage equality passed, but encoded TIFF SHA-256 differed.
- Installing Rasterio **1.4.4**, with bundled **GDAL 3.10.3**, made the unchanged byte-exact test pass. No pinned raster hash, expected result, template, writer or metric was relaxed.
- `requirements.txt` now loads `requirements-constraints.txt`, recording the tested Python 3.11/Linux x86_64 CPU package versions including transitive dependencies. CI/deployment cache keys include both files. Normal pip/PyPI integrity verification remains enabled. This is not a guarantee of cross-platform native-library or GPU bitwise reproducibility; other platforms need their own verified environment.
- All existing CI/deploy paths run the new read-only research-state audit and verify that it cannot clear a submission.

## Data placement and artifact validation

The requested `bash scripts/download_competition_data.sh` and `python scripts/prepare_data.py` ran autonomously on CPU. The full shared restoration tier succeeded: the 19-band feature raster and shared external inputs are available locally, the three core SHA pins and grids match, and the existing nine shared feature planes load. **Data placement is not the sole remaining blocker.** This is a SHA-pinned owner mirror, not an authenticated DrivenData download or newly verified redistribution permission. No training was authorized by preparation.

The existing saved-byte download audit reopened **46 TIFF/ZIP pairs** (45 main downloads plus one historical variant): **46 pass local research checks, 0 are protocol-eligible**. It verifies all-finite [0,1], single band, exact sample CRS/shape/transform, footprint/catalogue zeros, decoder agreement, self-contained raster containers and byte-identical one-TIFF ZIPs. The canonical research TIFF SHA remains `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`.

These checks address the locally testable causes of “Predicted values must be in range [0, 1]”. They do **not** establish that an unauthenticated remote portal accepted any file. Static GitHub Pages serves saved results/downloads; it cannot itself run training or authenticate an upload.

## H33: a defensible answer, not a post-hoc story

**The supplied 0.2778 is a USER-REPORTED CLAIM, not ORGANIZER-CONFIRMED and not a new HOLDOUT-DTI measurement.** The [freshly retrieved owner build record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) explicitly says its live estimate is a model projection, not a score. It identifies H33-2-B2 as the 40,199-dot SOLO base with every dot within two catalogue pixels deleted, leaving 37,654.

A fresh **read-only, pinned-byte geometry audit** confirms the nested support chain:

| Raster | Positive pixels (REGISTRY-MEASUREMENT) | Added pixels relative to parent |
|---|---:|---:|
| H19-5 | 121,131 | Not applicable |
| D2.8 | 44,090 | 0 |
| SOLO-D2.8 | 40,199 | 0 |
| H33 | 37,654 | 0 |

Between D2.8 and H33, all **6,436** removed dots are within two pixels of the catalogue. The immediate SOLO-to-H33 subtraction is **2,545** dots. H33's minimum nearest-neighbor distance is about **2.8284 px**; its median catalogue distance is about **19.6469 px**. These are geometry, not estimates of fault accuracy.

The shared distance-weighted Tversky implementation supplies a plausible precision/coverage mechanism. For fixed truth G, let `S = TP / (beta*|G| + (1-beta)*TP + alpha*FP)`. If deleting predictions loses truth credit t and removes weighted false-positive mass f, with positive denominators, deletion improves S **if and only if**:

`t * [1 - (1-beta)*S] < alpha*S*f`.

For the project instrument, `alpha=0.2`, `beta=0.8`, and a 300 m triangular kernel. Redundant nearby dots can incur additive false-positive mass while adding little saturating truth coverage. A catalogue collar can suppress rediscovery of known structures. **But t and f on hidden organizer truth are unknown**, and a collar can remove a genuinely missing nearby fault. One dot may cover several truth pixels; its marginal benefit is not universally bounded by its own self-credit. A fixed 37,654-dot budget or 2.8-pixel spacing is not thereby proven globally optimal.

Therefore H33's ancestry and the metric are **consistent with**, but do not causally prove, the supplied improvement. Beating the supplied H33 figure—or the conflicting 0.3195/0.4413 “current high” claims—is **not established here**. A mapped-catalogue hide-and-recover result is a proxy, not a forecast for expert-mapped uncatalogued faults. Repeatedly selecting among many methods on the same folds creates portfolio-level selection bias not covered by an ordinary per-candidate confidence interval. A genuinely different physical contrast, null controls, matched-fold incumbent and untouched audit partition are more defensible than another renamed/pruned ancestor.

## Claim-level source/access ledger

| Claim | Primary/review link | What this session actually verified |
|---|---|---|
| Official reference supports CPU and GPU; data download separate | [Pinned official README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) | GitHub commit and content retrieved. Content SHA-256 `cfa4d55559c9128313beb9417eae7e0a94c31677132afb1120f9e86222804239`. No baseline U-Net was trained here. |
| H33 identity and collar pruning | [Pinned owner build record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) | Retrieved via GitHub. SHA-256 `0d7c5c3fb0079410e0d519fac45a36b37dc6136f2e42d5c6b2468a29397c478a`; geometry recomputed from pinned mirrors. Owner evidence, not a submission receipt. |
| New-candidate stop | [Pinned 17GEMSDOE witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif) | Restored by git; SHA, exact grid and direct positive support recomputed through the shared preflight. |
| Target, format and metric authority | [Competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Official review links **not fetched this session**. These hosts are outside the sandbox allowlist; no authenticated organizer data/labels were acquired. |
| Current ranking/quota/receipt | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [submissions](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/) | **Not verified.** No slot or receipt. Historical public snapshots elsewhere in the repository are not this session's live retrieval. |
| Rules and timing | [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Not retrieved through this session's allowed hosts. Current deadlines, eligibility, AI disclosure and account allowance are not certified here. |
| Primary geological data | [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [GDR INGENIOUS](https://gdr.openei.org/submissions/1391) · [3DEP](https://www.usgs.gov/3d-elevation-program) | Review/provenance links only. Existing mirrored derivatives and manifests were hashed locally; primary availability and component-level terms were not freshly checked. |
| CPU package identities | [NumPy 2.3.4](https://pypi.org/project/numpy/2.3.4/) · [Rasterio 1.4.4](https://pypi.org/project/rasterio/1.4.4/) | Exact versions installed with pip artifact verification enabled; package/encoder versions and constraints recorded. This is software reproducibility evidence, not a geological claim. |

The supplied-site inventory remains **92 sites and 115 distinct file/value claims** with request-line provenance (`docs/data/user_reported_results.csv` and `.json`); missing entries stay unknown, never zero. **All 92 sites were not freshly scraped**. No claim is upgraded to a receipt. GitHub authentication works; no credential request is needed. Access to GitHub does not imply access to DrivenData, USGS, GDR, NLR or arbitrary scientific literature hosts.

## Three-pass verification record

**Pass 1 — implement and verify:** read the standing request/contract and current evidence; restore and prepare shared data; run the shared preflight before modeling; audit all 46 archived packages; retrieve official reference and H33 owner source; reproduce H33 geometry; identify and correct the false legacy clearance, stale queue and dependency mismatch. Targeted regression suite: **50 passed** after the encoder correction.

**Pass 2 — review and fix: COMPLETE.** The first integrated suite exposed two old tests that still treated the previous browser receipt as current (826 passed, 2 failed, 23 skipped). Preserved both prior receipts without changing their measurements, made active-receipt checks follow `docs/status.json`, and ran a fresh seven-case Chromium desktop/mobile audit. Review also found the Research page still recommending executed MMRX; its queue now renders from the same audited manifest as Overview, with drift/metadata regression tests. Malformed SHA/band/rank records and removal of known evaluated methods fail closed. A completely fresh constrained virtual environment installed all 31 distributions, passed `pip check`, and passed the unchanged byte-exact parent-R0 rebuild. The subsequent full suite passed **828 / 0 failed / 23 skipped** (165.62 s); one additional software-receipt regression is included in the final pass.

Browser evidence verifies seven responsive cases, no horizontal overflow or page errors, one visible H1, closed archives, the first TIFF link and its actual click-downloaded SHA-256. Both disabled JavaScript and failed evidence fetches remain negative. The minimal sandbox lacked NSS/NSPR; the optional browser runner now extracts the exact npm package’s bundled libraries instead of requiring an unverified system download. No new scientific result is claimed. [Fresh browser receipt](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_693b10af_browser_check.json) · [fresh CPU install receipt](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_693b10af_cpu_reproduction.json).

**Pass 3 — whole-request recheck: COMPLETE locally, including parallel-main integration. Final combined suite: 855 passed, 0 failed, 23 skipped, 64 warnings, 177.49 seconds in a fresh constrained CPU environment.** Pre-integration suite: **829 passed, 0 failed, 23 skipped**, 68 warnings, 164.26 seconds. A final source-snapshot edge-case review then added recursive package coverage and root-bounded source reads (four additional cases, unchanged 150-file source pin); the fresh constrained environment passed **833 / 0 failed / 23 skipped** in 168.13 seconds. Skips concern historical gitignored/unrestored variant or bridge rasters; they were not rebuilt to evade the guard. Warnings are recorded, not silently counted as additional tests. All 46 published TIFF/ZIP pairs were separately reopened. The read-only workflow/guard matrix completed **47 checks**, including **23 expected submission/generation rejections at exit 2**, normal and optimized Python site/metadata guards, independent archived-byte validators, full required-input SHA checks, historical replay and deterministic readiness checks. [Gate receipt](https://buffedlizard55-lab.github.io/GEMSDOE88/data/session_693b10af_gate_check.json).

The complete request was re-read; README’s normalized full-request embedding exactly equals `USER_PROMPT_20261025.md` (SHA-256 of stripped text `fc0affe0d1eed0dc42c4541dc01113be064c55589090c9dd693d8da82a706b60`). Shared evaluator/holdout/writer/vendor bytes are unchanged. No candidate generation, new geological experiment or portal action occurred. Software review passes are complete; **the entire scientific/submission request is not satisfied**. This local evidence is not a remote CI claim; PR/check/merge status is authoritative on GitHub. Parallel `main` changes at `15b1d00` were integrated on the same Arena branch and the combined suite above passed. Their atomic fail-closed preparation receipts, surplus-argument rejection, exact Rasterio pin, independent review cards and scratch-incident documentation are preserved. The alternate GTD-first proposal is linked as a historical parallel judgment, not a second active queue. No new source/feature implementation arrived, so the reviewed 150-file fingerprint is unchanged—not blindly refreshed. Full shared preparation was repeated successfully; a second fresh constrained install/unchanged byte-exact rebuild, all 47 workflow checks and the seven-case actual-download browser audit were rerun after integration.

| Requested outcome | Final scope |
|---|---|
| New unique, submission-ready TIFF | **UNMET** — binding pre-generation stop; no old file relabeled |
| New top-candidate holdout/canaries and demonstrated win over H33 | **NOT RUN / NOT ESTABLISHED** |
| 3–5 ranked, specific untried hypotheses | **Four**, with exact layers, physical contrasts, mimics, cost, falsification and conditional validation plan |
| H33 scientific explanation | Pinned ancestry measured; metric trade-off explained; hidden-truth causality and receipt explicitly unknown |
| Autonomous data placement | **PASS**, shared owner-mirror CPU tier, not organizer-authenticated data or training approval |
| No-human format inspection, top download, executive guide | **PASS for archived research only**; actual browser download matches pinned bytes |
| Source/knowledge audit, full request preservation, irregularities | Recorded, with official-host and 92-site retrieval limits explicit |
| Three implementation/review passes | **COMPLETE**, local evidence above; negative scientific outcome retained |
| Competition slot/upload | **Zero**, no authority inferred from file correctness |

## Final parallel integration addendum

The PR also integrates `main` through `696c1140a1bb2dd60ea832146c86b6fde853b6e4`. The combined **855/23** result includes fresh footprint/catalogue-pin regression coverage, the SDTL parser-warning correction, repaired submission instructions, and independent integrity/dual-decoder checks of **20** additional `submissions/` TIFF/ZIP pairs. These are repository-archive pairs, not 20 new or independent predictions; the published Pages inventory remains 46 pairs. The IBL ZIP naming repair and its original/new hash receipt are inherited from the parallel review, not a new prediction from this session. Scientific model/feature/evaluator implementations remain unchanged. The later metadata-only generator-alias integration and reviewed source-pin update are described below.

The H33 read-only geometry audit was repeated after the new reference-pin checks; the run card contains its fresh result and retains the initial audit timestamp. The historical five-proposal parallel record and its claimed public-source access are preserved in their own reports, not silently substituted for the active four-entry audited queue. Its regression now verifies historical proposal preservation **and** current source-bound state instead of freezing a prior recommendation as permanently current. Parallel [dated public-source snapshot](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/696c1140a1bb2dd60ea832146c86b6fde853b6e4/evidence/leaderboard_official_snapshot_838cc402_20261025.json) is inherited evidence, **not** this session’s independent retrieval, account authentication or artifact-specific organizer receipt. Original host-access limits remain explicit.

The final parallel withdrawal integration is through `8dc9670e1dd15253ade1828a3311f0c9e322d2b6`. It independently corrected the same unsupported GHMD promotion/organizer label. Compatible historical-verdict, supersession and user-claim aliases are retained together with this review’s stronger binding uniqueness stop and byte-identical mirrors. The correction receipt preserves the preceding canonical and parallel metadata hashes as well as the original starting-commit evidence. Its TIFF/ZIP identities are unchanged. The only changed file in the reviewed 150-file corpus was the legacy generator’s metadata aliases; that exact diff was reviewed before updating the source pin. Both old/new pins are retained in the queue history. The final full suite after this integration is **855 passed / 23 skipped**, 64 warnings, 177.49 s.

## Delivery

Code/evidence delivery: [PR #164](https://github.com/buffedlizard55-lab/GEMSDOE88/pull/164) from the fixed Arena branch into `main`. The PR’s live checks and merge record are authoritative. Remote Actions were observed queued, not passed. Attempts to cancel only this branch’s superseded queued runs returned HTTP 403 (`Resource not accessible by integration`); none was canceled. This connection’s Actions control permission is limited, while git/PR access works. This report and run card are a local verification snapshot, not a mutable remote-CI or organizer-acceptance claim.

## Next session priorities

1. Resolve the shared literal-support contradiction explicitly **before** any candidate construction. No revised rule is approved here. The urgent new unique-TIFF deliverable remains unmet until the contract admits a nonempty candidate.
2. Under a valid shared contract, preregister one SPR variant and its terrace/shoreline/drainage nulls. Recompute the same-fold incumbent and leakage tests with the shared tools, preserve an untouched spatial audit partition, require paired improvement, then perform both uniqueness phases. Do not spend a slot just because a file passes numeric checks.
3. Establish organizer-authenticated input identity and permitted derivative distribution; verify current contest timing, quota and receipts in an authorized environment. Do not ask for or store credentials in chat or Git.
4. Keep dependencies and native encoders reproducible; preserve strict byte/hash checks rather than making tests pass by relaxing them. Keep source-bound proposal state current as parallel lanes merge.
5. Keep bulk data, caches, wheels, browser binaries/screenshots and raw logs ignored. The changes here contain only code, documents and small hash-bound metadata, not a new candidate or trained model.

**Maximize P(Win):** avoid repeated unvalidated theories and scarce-slot waste. **Own the Outcome:** repair actual evidence bugs, preserve negative findings, and state the unmet submission requirement plainly.

## Late PGTD integration

While PR #164 was being verified, main advanced to `3c2531250409b5f70469ce211ba67bec4526c88c` (PRs #165/#168). This is a substantive source change, not a permissible blind fingerprint refresh. It adds the evaluated PGTD harmonic-tensor family and a negative archived TIFF. Its CLI printed a negative preflight but proceeded into model code. This review replaced that bypass with the mandatory shared enforcement before imports and added real CLI/optimized/module regression tests. No peer run is recast as compliant or as an experiment by this session.

GTD is now retired against the actual PGTD run card, leaving three precise unrun proposals (SPR, AWA, CBC). MMRX’s repaired metadata pin was reviewed; the full queue history preserves the earlier source fingerprints. The parallel executed-lane reader missed PGTD’s `sha256_tif` field; it is now recognized and tested. The alternative 78cfb743 proposal interface remains a labeled parallel snapshot, not a competing primary selector. Physical novelty still requires semantic review, not just matching IDs.

The shared literal-v4 compatibility hardening from PR #165 is retained with its documented upstream/patch provenance; shared evaluator, holdout and writer bytes are unchanged. The inherited PGTD tensor’s physical unit/pixel-spacing/scaling consistency is not certified by a format pass or its name. No tensor physics or model was changed or re-evaluated here. Its byte novelty is not protocol uniqueness: its own negative card reports a literal stop and additional discriminating duplicates.

The peer artifact is preserved in a closed historical section, without an active “unique TIFF” banner. All **47** Pages packages (46 main + one variant) were independently reopened with two decoders; all pass local research format checks, **0** are submission-eligible. The separate 20 `submissions/` archive pairs remain negative research. The full source/input audit passed after the reviewed 152-file source update. Final integration test/browser receipts follow below when completed; earlier measured counts above describe their explicitly dated integration stages.

Final-integration full testing caught four freshness/history failures (865 passed, 4 failed, 23 skipped): stale README/SUBMIT package totals, the gate receipt test’s former 47/23 constants after expanding to 53/26, and a historical b4dfa10c test incorrectly equating its frozen 46-package record with the new 47-package live inventory. Corrected the current counts; preserved the original historical audit bytes under a SHA-verified snapshot rather than rewriting that session’s numbers; added a production guide-count freshness guard and negative regression. The final passing rerun is recorded below.

### Final late-integration verification

Final code through `3c2531250409b5f70469ce211ba67bec4526c88c`, including the PGTD stop fix and history/freshness regressions: **869 passed / 0 failed / 23 skipped**, 64 warnings, **205.00 s**, in the same separately fresh-installed constrained CPU environment (requirements unchanged). All **53** workflow/guard checks passed, including **26** expected exit-2 denials and normal/optimized checks. All **96** candidate entrypoints enforce the shared guard before imports; real normal/optimized/module PGTD invocations stop without writes. Seven responsive/legacy browser cases, 14-source fingerprints, actual HTTP/click SHA verification, failed-fetch and no-JavaScript negative behavior passed. The full input/source audit passes at **152 files**, SHA-256 `625401b58740ab4243f187311e45d58c7430425e6638fc51a02d3f7d7f7b8a8a`. The original b4dfa10c 46-package audit is preserved byte-for-byte under its original SHA; its numbers were not rewritten to claim the later 47th peer artifact. Final focused record regressions passed 66 tests before the full rerun.

Remote Actions/deployment remain explicitly unverified; queued is not passed. No geological experiment, new candidate TIFF, holdout score or slot was produced by session 693b10af. Scientific acceptance remains negative.
