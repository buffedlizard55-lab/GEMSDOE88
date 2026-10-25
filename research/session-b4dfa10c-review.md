# GEMSDOE88: three-pass repository review — 2026-10-25, b4dfa10c

## Executive decision

**Download the existing audited research TIFF: YES. Submit it: NO — DO NOT SUBMIT. No new protocol-unique competition TIFF was generated.** The highest-urgency new-submission requirement remains **unmet**, not silently replaced with an old file or a new filename.

- [Existing H88-TDKL research TIFF](https://buffedlizard55-lab.github.io/GEMSDOE88/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif) · [one-TIFF ZIP](https://buffedlizard55-lab.github.io/GEMSDOE88/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.zip). The [website](https://buffedlizard55-lab.github.io/GEMSDOE88/) and executive guide present the same negative submission decision.
- TIFF SHA-256: `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`.
- [Canonical negative run card](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/registry/session_b4dfa10c_run_card.json), mirrored to `docs/data/session_b4dfa10c_run_card.json` and `evidence/session_b4dfa10c_run_card.json`.
- [Four ranked, untried geological proposals](session-b4dfa10c-hypotheses.md). The leading conditional proposal is repeatable magnetic-marker restoration, not a renamed MTAS/BPWD experiment.
- **Zero** geological experiments, new candidate TIFFs, or weekly submission slots in this review. Tiny synthetic rasters used for software regression tests are not competition predictions.

## Why generation stopped

The exact current request says to stop if more than 70% of candidate dots are within 3 pixels of **any** registry raster. The inherited support definition is `isfinite(value) & (value > 0)`. A fresh shared preflight from pinned inputs measured:

| Registry measurement — not a performance score | Result |
|---|---:|
| Allowed footprint pixels excluding the catalogue | 5,106,385 |
| Allowed pixels directly on the witness's positive support | 5,106,385 |
| Uncovered allowed pixels | 0 |
| Universal forward-overlap lower bound for any nonempty candidate | 1.0 |
| Binding overlap limit | 0.70 |

The witness is [this immutable 17GEMSDOE probability raster](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif), SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`. It is not the sparse F-ensemble file named in the user's results list, but it is already in the binding registry. One in-scope counterexample is sufficient to disprove eligibility; this is **not** an exhaustive uniqueness clearance across all 92 sites.

Because every possible allowed candidate pixel is already on that support, constructing a surface or dots cannot change the outcome. No surface correlation or final-dot correlation is invented for an unbuilt candidate. Empty/all-zero output, renaming a previous file, hiding the witness, changing a threshold, or importing an internal builder would not fulfill the request. The mathematical conflict requires an explicit, versioned **shared protocol** decision before further modeling; this review does not authorize an exception.

## Pass 1 — reproduce, implement, verify

1. Read the standing requirements, complete recorded request, README, and session contract. The full request is already embedded in README; it was retained without another competing decision banner. The request supplies no actual single-method paragraph, so no assigned geological lane is invented.
2. Installed the repository requirements into an ignored virtual environment. Ran `bash scripts/download_competition_data.sh`: all pinned core/shared external input groups restored; `prepare_data.py` verified hashes, the 19-band core grid, and loading of the nine shared feature planes on CPU. The core stack is 418,912,844 bytes, shape 3730×3292, EPSG:32611, transform `(100, 0, 243350, 0, -100, 4508550)`. These are **owner-mirror identity checks**, not authenticated organizer provenance, data-use permission, or authorization to train.
3. Re-ran `preflight_mtas88.py --gate-generation`; it returned the expected exit 2, `DUPLICATE_STOP`. No candidate feature construction, fitting, holdout evaluation, placement, or submission writing followed.
4. Baseline suite on the restored input tier: **651 passed, 23 skipped**. This is a software-test result, not HOLDOUT-DTI. Optional lane-specific caches/inputs remain absent; skipped tests are not certified passes.
5. Reproduced two genuine false-positive format checks using tiny synthetic files, then fixed the **existing** `scripts/validate_artifact.py` rather than adding a private validator:
   - **Second raster hidden behind a valid first page.** A TIFF with a valid georeferenced first page and a second smaller page containing `-123` was accepted as `format_valid=true` and `research_download_ok=true`. `rasterio.count == 1` and agreement with `tifffile.imread` were insufficient: both inspected the first raster. Format audit v2 rejects GDAL subdatasets representing multiple full-resolution rasters. It also rejects an ambiguous multi-raster template. Ordinary internal reduced-resolution overviews remain allowed.
   - **Sidecar-only georeferencing.** A TIFF with no embedded CRS/geotransform passed locally because an adjacent `.tif.aux.xml` supplied them. Its one-TIFF ZIP omitted that sidecar, so the packaged bytes had no CRS and the wrong transform. Format audit v2 requires the candidate and template to be self-contained datasets; it does not accept external mask/georeferencing/overview dependencies. This is a conservative **project** policy, not a newly asserted organizer rule.
6. Added a package-inventory check to the existing `audit_downloads.py`. TIFF-driven enumeration previously omitted orphan ZIPs, uppercase `.ZIP` files, and nested download artifacts. It now fails on those, on missing ZIPs, or when `.tif` and `.tiff` would share one ZIP. The site guard also rejects unrecorded packages and published artifacts outside the two declared flat audited directories. The existing `research-variants` collar package is now included: **43 main downloads + 1 historical variant = 44/44** passing research packages, **0** protocol-eligible files, and no exact decoded-float32 duplicate groups. No variant was moved, regenerated, or added to the modeling registry. Main `tiff_count=43` remains compatible with historical records; schema v2 adds explicit additional/total counts.
7. Corrected the archived README HGVC paragraph that still instructed users to rename a `DO-NOT-SUBMIT` file and upload it, and that incorrectly advertised `--require-submit` exit 0. The corrected text states revocation and expected exit 2. Historical measurements and immutable correction evidence remain available; no TIFF bytes were changed.
8. Updated the evidence-rendered overview/executive guide, not a lane-local banner. The direct research download stays first; format correctness, protocol uniqueness, scientific evidence, and weekly-slot approval remain separate.
9. Found independently reachable `docs/mdc88` pages still advertising upload clearance and broken nested download links despite a false submit boolean. Replaced them through the shared renderer with explicit archived, negative notices and canonical links; corrected the stale ready-status string and portal-acceptance description. Historical candidate, holdout, gate measurements and timestamps were verified unchanged against the base commit. The original status digest and immutable source link remain in the correction receipt.

## Pass 2 — bug and edge-case review

Regression coverage includes additional pages containing valid values, negative values or NaN; same-sized and differently sized pages; ambiguous templates; external PAM georeferencing; a standalone in-memory read of the packaged TIFF; valid internal overviews; normal and optimized-Python CLI rejection; all published TIFF metadata; orphan/uppercase/missing/colliding/nested package paths; and invalid-inventory fail-closed behavior before stale preflight evidence can be reused. Additional regressions cover both publication directories, all saved-manifest fields (including variant SHA/ZIP/total/witness), unrecorded variant pairs, negative legacy status, nested local links, and tampered published bytes under normal and optimized Python.

The canonical format validator, numeric check, public package audit and site guard share the same fix. No private metric, writer, dense-prior exemption, creation-order exception, or submission selector was introduced. Existing successful `validate_artifact` receipts keep their result shape; the stricter subdataset/dependency tests are included by its `strict_audit` result. All archived artifact hashes remain unchanged.

During review, main advanced through PRs #140–144. Incorporated main commit `4e3e9f6721ef8eeb9319f93126d3895260100d1a` on this fixed session branch (local integration commit `8aa5f81`). Reconciled both independently added inventory checks into **one** policy: retain main's `publication_inventory` API and symlink/dangling-link restrictions, extend coverage to both publication directories, and retain both regression sets. Test fixtures now copy published bytes instead of relying on symlinks that the real policy intentionally forbids. No main work or binary was discarded. The concurrent guide corrections forbidding human/boolean overrides were retained.

The imported earlier browser receipt is preserved as a dated historical record, not rehashed to pretend it describes changed pages. A **fresh** Chromium 153 run binds seven desktop/mobile cases, legacy pages/status and current audit bytes in `evidence/session_b4dfa10c_browser_check.json`; it also fetched the canonical research TIFF over HTTP and matched its SHA. Browser binaries, screenshots, logs and synthetic test data remain ignored.

The original rejected upload was not supplied for byte-level investigation, so this review cannot identify its specific range-error cause. Negative values, nonfinite values, and nodata sentinels are plausible failure classes; a strict all-pixel finite/range audit detects them without clipping. A passing local audit is still not a submission-page acceptance receipt.

## Pass 3 — full recheck

**Completed after integration: 757 passed, 23 skipped, 63 warnings, 250.94 seconds.** The 23 skips concern optional historical/local-only rasters and unavailable lane-specific caches. They are not passes, and their regeneration is not authorized under the duplicate stop. A pre-integration full run also passed 727/23; the restored-input pre-edit baseline was 651/23. These are software-test counts, not performance scores.

| Recheck | Observed result |
|---|---|
| `.venv/bin/python -m pytest -q -ra` | **757 passed / 23 skipped** after integration |
| Final focused container/inventory/UI, request-provenance, run-card and historical-evidence recheck | **183 passed** after the final evidence update (earlier post-integration focused run: 172) |
| `scripts/audit_downloads.py --check` | **44/44** saved-byte TIFF/ZIP pairs, including the historical variant; eligible **0**, exact decoded-float32 duplicate groups `[]` |
| `scripts/render_decision.py --check` | PASS: canonical overview/guide and both legacy corrections match evidence |
| `scripts/check_site.py` and `python -O scripts/check_site.py` | Both PASS; full inventory, exact published hashes, nested links and negative statuses checked |
| Shared `scripts/generation_guard.py` and `preflight_mtas88.py --gate-generation` | Expected exit **2**, `DUPLICATE_STOP`; no features fitted or candidate emitted |
| `validate_current.py --require-submit`, `validate_release.py --require-submit`, `review_repo_20261025.py --require-submit` | Each expected exit **2**; no upload or weekly slot cleared |
| Chromium 153 desktop/mobile (390/1440 px) | **7/7** cases pass, no horizontal overflow/page errors; failed audit fetch remains negative; actual research download HTTP 200 and exact SHA match |
| Published TIFF/ZIP bytes and shared evaluator/writer | Unchanged; no new competition TIFF, experiment or submission slot |

The mirrored run card records exact command/exit evidence and local log hashes; large/raw logs remain ignored. Software verification PASS does **not** mean all requested deliverables are met. **UNMET:** new unique submission TIFF, new top-hypothesis holdout/canaries, demonstrated improvement beyond H33, organizer acceptance and live account quota. No new scientific score is claimed.

## H33: why the supplied result might be better, and what cannot be concluded

**The supplied 0.2778 is a user-reported claim, not ORGANIZER-CONFIRMED and not a HOLDOUT-DTI result.** A fresh GitHub read of GEMSDOE32's [owner build record at commit 012e17b2](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) identifies H33-2-B2 as the 40,199-dot H27-4 base with every dot within 2 pixels of the catalogue removed, leaving 37,654. That record explicitly describes its live estimate as a model projection, not an organizer score; it is not a receipt proving the user's later claim.

A fresh read-only pinned-byte lineage audit independently confirms:

- H19-5: 121,131 dots; D2.8: 44,090; SOLO: 40,199; H33: 37,654. H33 is a subset of all three, not a new set of discoveries.
- All 6,436 dots removed between D2.8 and H33 lie within 2 pixels of the known catalogue. The immediate SOLO-to-H33 subtraction removes 2,545 dots.
- H33 has no positive pixel within 2 pixels of the catalogue, minimum nearest-neighbor spacing about 2.8284 pixels, and median catalogue distance about 19.6469 pixels. These are **raster geometry measurements**, not a geological precision estimate.

The shared distance-weighted Tversky implementation offers a plausible mechanism: truth coverage is saturating, while false-positive prediction mass is additive. Removing redundant dots can reduce the false-positive term without proportionally reducing truth coverage. With `S = TP / (TP + alpha*FP + beta*FN)`, fixed hidden truth, and `FN = |G| - TP`, deleting dots improves S only when the lost coverage `dTP` satisfies:

`dTP * (1 - (1 - beta)*S) < alpha*S*dFP`.

Here `alpha=0.2`, `beta=0.8`, and `dFP` is the removed weighted false-positive mass. This is a conditional algebraic statement, **not measured hidden-truth evidence**: both losses are unknown for organizer truth. One dot can cover several truth pixels; no incorrect bound equating marginal coverage with its own self-credit is assumed. A catalogue collar could also remove a genuinely missing nearby fault. The sequence of user-reported scores is not a randomized causal experiment.

**Can a new method beat 0.2778 or the claimed 0.4413 leaderboard value? Not demonstrated here.** Neither a local holdout maximum nor a receipt-fit projection proves that. The prompt also calls 0.3195 the current maximum; those are conflicting snapshots/claims, not one verified current leaderboard. No current leaderboard, timing, or account quota was fetched in this network-restricted session.

The scientifically useful next step is a genuinely different off-catalogue mechanism, matched-fold incumbent and null controls, and an untouched audit partition—not another cosmetic emission or an assertion that H33's thinning is universally optimal. Repeatedly choosing among many lanes on the same holdout creates selection bias even when each individual fold is leak-free; ordinary per-candidate intervals do not account for that portfolio-wide search.

## Claim-level source/access ledger

| Claim / source | Link for review | What was actually verified this session |
|---|---|---|
| Official baseline supports CPU/GPU; separate competition-data download | [Pinned official README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) | GitHub API commit and content retrieved. GPU is faster, not mandatory. This is the official reference repository, not a competition receipt. |
| Official notebook uses U-Net/Monte Carlo patch splits and Tversky training weights | [Pinned notebook](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb) | Raw notebook retrieved via GitHub and cells inspected. Training-loss weights 0.2/0.8 are visible. The notebook loss is not declared equivalent to the shared triangular distance evaluator. |
| H33 build identity and collar pruning | [Pinned owner build record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) | API content inspected and then rechecked using a pinned GitHub GraphQL Blob after REST throttling; content SHA-256 `0d7c5c3fb0079410e0d519fac45a36b37dc6136f2e42d5c6b2468a29397c478a`. Mirrored raster SHA verified locally. Owner-authored, not organizer confirmation. |
| Universal overlap blocker | [Pinned witness](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif) | Restored via git; SHA, grid and direct allowed-domain support recomputed by the shared preflight. |
| Competition target, format and metric authority | [Official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Authoritative review links, **not fetched this session**. Local grid/format checks use pinned owner mirrors; no organizer-authenticated download is claimed. |
| Current ranking/account/quota | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [submissions](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/) | **Not verified.** No authenticated DrivenData connection, no receipt, no slot consumed. User figures are preserved as claims in the existing 92-site/115-result inventory. |
| Rules, licensing, primary geological data and literature | [NLR rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [GDR INGENIOUS](https://gdr.openei.org/submissions/1391) · [3DEP](https://www.usgs.gov/3d-elevation-program) · [EPSG reference](https://epsg.io/32611) | Official/provenance review links **outside the permitted hosts**. No fresh verification of their scientific assertions, current availability, terms, or dataset permissions. No new externally dependent hypothesis was presented as viable. |

Additional GitHub REST requests temporarily reached the shared account's rate limit (HTTP 403, remaining 0); the limit subsequently reset, and a successful pinned-Blob GraphQL recheck confirmed the H33 build content. This was **not an authentication failure**. No password/token/2FA was requested, logged, or added to the repository.

**Integration/source irregularity:** a concurrently imported review says it observed a public leaderboard value of 0.4413. Its historical record is retained, but that is not a fresh retrieval or submission-page receipt by this session; README now labels that scope. An archived suggestion of a v4-style dense-prior change is not approval: the binding shared literal gate is unchanged. The existing inventory preserves 92 sites/115 distinct user-reported file/value claims; **all 92 sites were not freshly scraped** here. New primary geological data and their current licenses were not independently retrieved.

## Next session priorities and limitations

1. Resolve the **shared** overlap-policy conflict explicitly. A representation-aware proposal may be sensible for continuous versus binary rasters, but no such revision is approved here. Until then, stop before modeling rather than spending more compute on predictably ineligible rasters.
2. After a valid shared contract exists, freeze the H88-MMR restoration test or another one-lane proposal and run feature-alone leakage, matched-fold hide-and-recover and null controls. Preserve at least one untouched spatial partition for final portfolio selection; do not optimize a leaderboard forecast using user-reported figures.
3. In an authorized environment, establish organizer input identity and permitted use/redistribution; confirm current rules, competition timing, account quota, and a real submission receipt. GitHub access is not DrivenData access. Never commit credentials.
4. Keep data, feature caches, synthetic rasters, browser binaries/screenshots and raw test logs ignored; only small hash-bound JSON evidence receipts are published. This review restored the shared input tier, not every historic lane-specific cache or a trained U-Net. Static GitHub Pages serves saved results and download links; it does not execute training or authenticate contest uploads.
5. Retain strict saved-byte package validation and the new container/inventory regressions. No human inspector is needed to decide these local checks; the automation still cannot infer hidden-label performance or grant an unverified contest slot.

**Maximize P(Win):** protect scarce feedback from duplicates and unvalidated theories. **Own the Outcome:** repair actual acceptance bugs, preserve negative evidence, and state the unmet unique-TIFF requirement plainly.
