# Repository review — d0c3adeb — 2026-10-25

> **Supersession notice (2026-10-25):** historical review only. The current three-pass review is `docs/research/repo-review-dea470d9-20261025.md`; it corrects queue status and data availability, marks prior HGVC clearance and rename/upload advice revoked, and preserves the literal preflight stop.

## Executive decision

**Research download: YES. Competition submission: NO — DO NOT SUBMIT. New protocol-unique TIFF: NOT GENERATED.**

The highest-urgency requested deliverable remains unmet, for a measured reason rather than a missing download. The SHA-pinned `17GEMSDOE` probability raster is positive on every allowed cell. Under the binding literal positive-support interpretation, any nonempty candidate has forward overlap **1.0**, exceeding **0.70**. A necessary-condition rejection before feature construction is stronger and cheaper than emitting another file and rediscovering the same failure. No candidate pixels were generated, copied, renamed or claimed as new. No competition slot was selected or spent.

This session continues the preceding stop/integrity handoff. The request provides no actual single-method paragraph. [Four conditional geological proposals](session-d0c3adeb-hypotheses.md) were recorded before implementation; none was fitted. Their priority labels are judgments, not projected scores.

## What was completed autonomously

- Restored the shared core input tier through pinned owner GitHub mirrors; ran the requested download/preparation commands. The feature TIFF is present locally; all core grids and band counts agree; nine existing shared physical planes load on CPU. This input-readiness smoke check is not construction of a novel hypothesis-specific feature or a scored geological experiment. Data placement is **not** the sole remaining blocker. A GPU is optional according to the freshly retrieved official reference README.
- Re-ran the existing shared pre-placement proof and existing artifact validator. The evaluator, holdout splitter, metric, submission writer and uniqueness implementation were **not forked or changed**.
- Added one orchestration guard to candidate-generation/experiment CLI entrypoints and the superseded publisher. The guard executes before feature/model imports. It delegates to the existing preflight; no dense-prior exemption, silent fallback, approval override or new metric exists. Missing/corrupt prerequisites exit with an audit error, not permission to continue.
- Reopened **all 41 published TIFFs**, with rasterio and tifffile; checked strict all-finite [0,1], reference CRS/shape/transform, footprint and catalogue support, and each one-file ZIP. Found and repaired two filename-only ZIP faults. **All TIFF bytes are unchanged**. All 41 now pass these local research-package checks. None is protocol eligible. No two published TIFFs have exactly identical normalized float32 values; that is **not** a full registry uniqueness pass.
- Replaced competing “current” site banners with one machine-rendered primary decision and a complete research-download inventory. Historical lane records remain in a closed archive, explicitly superseded. Added static-content consistency and fail-closed runtime checks rather than asking a human to inspect rasters.
- Recorded the complete supplied site/result list: **92 sites**, **115 distinct reported file/value pairs**, and four sites with no reported result. Results remain unverified user claims with request-line provenance; blanks are not converted to zeroes.

## H33: what actually changed, and why that can help

**The supplied 0.2778 is a USER-REPORTED CLAIM, not HOLDOUT-DTI and not ORGANIZER-CONFIRMED.** Neither this repository nor the freshly retrieved GEMSDOE32 build record supplies its submission-page receipt. The supplied 0.3195 and 0.4413 maxima are also not authenticated current standings in this session.

Fresh **REGISTRY-MEASUREMENTS**, not performance scores, reproduce:

| Raster | Positive cells | Geometric relationship |
|---|---:|---|
| H19-5 | 121,131 | Upstream support |
| D2.8 | 44,090 | Thinned support |
| SOLO-D2.8 | 40,199 | Near-catalogue pruning |
| H33-2-B2 | 37,654 | Exact subset of all three; no added cells |

H33 removes **6,436** D2.8 dots; every removed dot lies within **2 pixels** of the catalogue. Its nearest-neighbor minimum is **2.828427 pixels**. These results are reproducible with `python scripts/audit_h33_lineage.py`, and the inputs are hash-pinned. The educational comparison does not copy any ancestor into a new submission.

The owner build record explicitly identifies H33-2-B2 as collar pruning. A repository containing sophisticated geological hypotheses does not prove that those hypotheses generated a particular downloadable TIFF. Inspecting that artifact's build record and exact support matters more than its repository title.

For the **shared local binary DTI definition**, let `T` be truth-cell credit, `M` the sum of each dot's nearest-truth kernel credit, `n` the number of dots and `G` the number of truth cells:

```
D = 0.8 G + 0.2 T + 0.2 (n - M)
DTI = T / D
```

A deleted dot loses truth coverage `δT`, removes its own self-credit `k`, and changes the denominator to `D − 0.2(δT + 1 − k)`. Deletion helps only when the lost coverage is small enough relative to the reduced false-positive cost. Redundant dots can be expensive without adding much coverage; pruning can therefore improve the trade-off. Conversely, deleting a useful point can reduce the score, and hidden faults can run close to the public catalogue. There is **no proof that all H33 deletions were pure false positives**.

The shared metric's **code** keeps truth credit and dot self-credit separate. Its archived explanatory prose saying marginal truth credit must be no greater than a single dot's self-credit is not generally correct: one dot can cover multiple truth cells. This review does not change the pinned metric or use a private replacement; the limitation is recorded for a single upstream documentation correction. The exact algebra above is the basis of the interpretation, not a guessed hidden-label count.

**Can a new approach exceed H33?** It is possible in principle, but not established by these files or this review. Catalogue hide-and-recover performance is a proxy for previously unmapped faults; tuning repeatedly against it and then reading a maximum as a leaderboard forecast is not valid. A frozen, same-fold comparison with a paired physical-block CI and genuine off-catalogue generalization evidence is needed. There is no new model result or numerical forecast here.

## Scientific and workflow irregularities found

1. **Unsatisfiable uniqueness prerequisite.** The dense witness was already known, yet some later builders wrote TIFFs before checking it. `build_unique_relay_submission.py` wrote before its registry scan and had no executed holdout/canary. Its “pre-placement surface” comparison used final dots, not the continuous propensity. Generating another artifact by the same route would violate the supplied stop protocol. CLI execution is now stopped first.
2. **Fixed-raster evaluation is not hide-and-recover.** The SSA/GZZC-style builders exclude the *complete* catalogue before evaluating a fixed raster on withheld catalogue components. The withheld truth has already influenced that exclusion. With a kernel-width collar the resulting structural zero is expected; it is not evidence that the geology has zero predictive information. These archived numbers cannot clear or reject a new model under the requested fold-rebuilt protocol. No repaired scientific score is invented.
3. **Conflicting primary UI.** RELAY, SSA, VHGD, HGVC and MTAS banners all appeared as current, while the canonical manifest referred to TDKL. The primary panels now derive from the canonical manifest and audited bytes; historical claims stay below an explicit archive boundary. A generated-block equality check prevents a parallel lane from silently inserting another “current” panel.
4. **Unsafe ZIP extraction labels.** IBL and RELAY ZIPs contained byte-identical TIFFs but with old member names omitting DO-NOT-SUBMIT. Repacked those two ZIPs; updated their recorded ZIP hashes; preserved original/new hashes and unchanged TIFF hashes in `evidence/archive_repairs_20261025.json`.
5. **Data provenance overstated.** The downloader described user-provided Dropbox links as official, and preparation claimed official checksums and full train-to-submit readiness. It now uses disclosed pinned mirrors, fails on restore errors, checks all core grids, and states that input preparation is not generation or submission clearance.
6. **Historical source statements are not fresh verification.** The sandbox cannot access DrivenData, NLR, USGS, GDR, EPSG or Dropbox under its outbound allowlist. Earlier “fetched today” assertions are not adopted as new observations. Freshly retrieved GitHub evidence is separated from official links for later review.
7. **Unsupported geological/statistical inferences remain historical only.** Distance beyond the catalogue does not establish flat terrain or alluvial lithology. An owner-projection does not establish precision on hidden labels, hidden-positive counts, a required route to a target score, or organizer acceptance. Those interpretations are not used as present gates.

## Source-level verification

[Source ledger](session-d0c3adeb-sources.md) links every external authority used or needed and distinguishes freshly retrieved official code, owner records, local measurements and inaccessible official pages. The official notebook's alpha/beta are Tversky **training-loss** settings, not independent certification of the project's distance-weighted holdout. No current leaderboard, deadline, weekly allowance or authenticated organizer receipt was retrieved.

The exact prompt and supplied list are preserved in `USER_PROMPT_20261025.md` and embedded in README. The site exposes JSON/CSV request-line provenance instead of silently turning the user's result list into a verified leaderboard.

## Next steps, in order

1. Preserve the literal stop. A separately documented, authorized shared definition capable of distinguishing a continuous probability surface from a dot emission would be necessary before a nonempty candidate can become eligible. This session does **not** authorize that change or quietly apply top-N support.
2. Once the prerequisite is genuinely resolved, freeze one geological lane and a complete hash-bound registry snapshot. Reuse the cached stack and shared metric/writer. Build every catalogue-dependent field from visible faults per fold; run single-feature canaries before interpreting results.
3. Use a matched incumbent, paired physical-block intervals, withheld-label scrambling and a mechanism-specific non-fault null. Repeatedly optimized historical maxima do not constitute an untouched validation target. Stop at the stated experiment/time budget.
4. Verify organizer input identity, current rules/data permissions, available submission slots and eventual receipts in an authenticated, permitted network context. No credentials should be placed in chat or source control.
5. Only then can the separate selector authorize a slot. A static GitHub Pages website can serve and explain a file, but cannot securely perform account-authenticated submissions or heavy model training by itself.

**Maximize P(Win):** do not spend a scarce slot on a duplicate or an untested forecast. **Own the Outcome:** the unique-TIFF requirement is explicitly unmet, even though data placement, packaging and automated local validation are fixed.

## Concurrent-main integration (8e8bdf2)

Main advanced during review. Three **already-existing** research TIFFs (BGCD, executed MTAS, PRISM) and CXL's negative no-TIFF record were integrated; these are not experiments or new predictions made by this session. The saved-byte audit at that integration covered **38/38 TIFF/ZIP pairs**, all research-only. The canonical download remains the unchanged TDKL file, not a newly renamed candidate.

All five imported builders/runners now enter the same early duplicate-stop guard, bringing coverage to 76 CLI entrypoints at integration. The final alias audit also guards two historical rebuilders, four LBCAL feature/fitting helpers and the random-arm MASS diagnostic: 83 guarded CLI entrypoints before the second refresh. The unused CXL production script proposed treating the dense witness as nondiscriminating and potentially setting submission eligibility; this session does not authorize that deviation. The guard stops its execution before model imports. PRISM's full-catalogue-collared fixed-raster zero is subject to the same hide-and-recover validity problem as SSA/GZZC; its inherited card is an archival claim, not a new scientific result.

The remote overview contained nested duplicate `<main id="main">` elements and competing first-download panels. Those panels were not allowed to replace the canonical generated decision. Compact, closed historical records preserve all four lanes and link their original machine evidence; added BGCD byte/card checks were retained. The RELAY ZIP repair retains this review's audited bytes, and its metadata references follow main's negative-label sidecar rename.

Newly imported statements about live official sources or leaderboard positions are not fresh observations by this session. Its restricted-source ledger still governs what was actually retrieved. GitHub's REST quota was exhausted at 04:46 UTC; git fetching and a separate available GraphQL quota supported integration without requesting credentials.

### Second concurrent refresh (66218d7)

A second fetch imported the already-existing LSC and PSGV artifacts and evidence. Their two runners now enter the same early stop; that integrated tree had **85 guarded entrypoints** and **40/40 locally valid research TIFF/ZIP pairs**. All five imported TIFFs were generated in other sessions, and their original bytes remain unchanged. This review performed zero geological experiments and generated zero predictions. Added historical summaries stay inside the closed archive; LSC was not allowed to replace the canonical first decision. The earlier review's 596-pass result is preserved as an intermediate result; the post-refresh result is recorded separately in the run card.

### Third concurrent refresh and critical policy correction (e37c667)

PR #130 added the existing SEPA TIFF and a `decide_v4` path that waived dense-raster literal overlap, exempted a later near-copy by creation order, and marked an old HGVC artifact submit-ready before any selector authorization. These changes contradict this session's explicit any-registry rule. Its asserted HGVC approval was **revoked**, not adopted. The old TIFF, holdout numbers and measured diagnostic values remain unchanged. Corrected public/registry records point to the immutable original receipt and its SHA-256 via `evidence/session_d0c3adeb_protocol_correction.json`.

The legacy `decide_v4` name now delegates to the original literal `decide` implementation; no second approval policy exists. A hypothetical literal pass still cannot authorize an upload: the selector remains separate. The clearance-writing re-audit helper and the SEPA runner now stop before other imports; **87 entrypoints** are guarded. The SEPA standalone validator cannot return a positive submission flag from a corrupted historical card. Strict no-positive-clearance tests have no sanctioned exception.

The final audit includes **41 existing TIFF/ZIP pairs** (six imported from concurrent main), all research-only. This review still generated zero predictions and ran zero geological experiments. No last-minute main merge is treated as authorization to relax the user's constraints.

## Three-pass verification

See the [completion appendix](session-d0c3adeb-completion.md) for all three review passes, exact scope and the original-requirement acceptance matrix. The session run card records automated outcomes and explicitly unmet items. Passing software tests does not establish new scientific performance or organizer acceptance.
