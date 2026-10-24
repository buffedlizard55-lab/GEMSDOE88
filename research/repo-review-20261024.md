# GEMSDOE88 repository review — 2026-10-24

## Executive decision

**Current release: KTH-88 — OK TO DOWNLOAD FOR RESEARCH; DO NOT SUBMIT.** The TIFF/ZIP has local format checks recorded as passing, but KTH-88 is below the stored same-split holdout incumbent and fails the binding literal 3-pixel registry-overlap rule. No candidate is eligible for submission, no organizer receipt exists, and no weekly slot was spent. This review generated no TIFF and ran no geological experiment.

KTH-88 `HOLDOUT-DTI` is **0.0526558**, 95% CI **[0.0459111, 0.0591507]**, with **22,893 withheld positives**, evaluator `gems57-pooled-hide-v2`; the same-split incumbent is **HOLDOUT-DTI 0.1878876**. No paired improvement CI is available. Pre-placement maximum `|Spearman ρ|=0.074729` across 222 raster records. Final overlap is **0.898816** with a GEMSDOE87 raster and **1.000** with the dense 17GEMSDOE witness (limit 0.70); stop. Feature-alone canaries max at symmetric AUC **0.509700**. The K/Th inputs are uncalibrated u8 indices, not measured elemental abundance.

## Follow-up review and remediation

At the start of this continuation, `docs/index.html` and `docs/executive-summary.html` still advertised the synthetic `gems88-hyp-psg-submission.tif` as OK TO SUBMIT, despite the KTH-88 current release JSON and run card being negative. `python scripts/check_site.py` failed at `index.html`. The repository also had a public MDC-88 subsite and publisher that could assert OK TO SUBMIT from a chance-corrected/like-for-like exception even though its own literal registry record showed `unique_literal: false` and overlap 1.0. The following changes now make those surfaces fail closed:

- Replaced the top-level landing page and executive guide with KTH-88's **research-download-only / DO NOT SUBMIT** decision, current format/holdout/overlap evidence, and future-only submission steps.
- Removed the seeded synthetic MAG-PSG TIFF, its mock builder, and `mock_data.py`. They created synthetic lines/faults, not a geophysical prediction.
- Strengthened `scripts/check_site.py` and `tests/test_release.py` to reject false submit-ready text, stale mock links/artifacts, and divergent nested sub-sites; all pages under `docs/` are now link-checked.
- Archived the MDC-88 pages as historical and explicitly negative under the literal all-registry rule; added `registry/kdmc_literal_reassessment.json`. The old `registry/kdmc_gate.json` remains as an historical record of the prior non-binding gate, not a current authorization.
- Retired `scripts/publish_kdmc_site.py`; it now exits nonzero and refuses to overwrite the current KTH site with the old MDC-88 banner.
- Put the current no-file-to-submit rule above legacy README tables and marked older like-for-like uniqueness conclusions as historical, not submission authorization; qualified the stored format audit because the sample grid is absent for a fresh recheck.
- Replaced the old shortlist with three new-to-run candidates and explicitly excluded ideas already implemented or discussed; updated the operating prompt in README/PROMPT.md and labelled an earlier research note as historical.

## Three review passes

### Pass 1 — inspect, implement, and verify the public decision

- Read the README/PROMPT, KTH-88 run card, current-release JSON, validation report, source notes, site assets, research notes, tests, and prior-branch history before changing files.
- Reconciled static landing/guide pages with the canonical KTH-88 JSON feed; both pages now have a visible static `DOWNLOAD FOR RESEARCH: YES · OK TO SUBMIT: NO · DO NOT SUBMIT` decision and no submit-ready button or instructions for KTH-88.
- Corrected the additional archived MDC-88 public sub-site so its historical chance-corrected gate cannot supersede the user's literal-overlap rule. Its original gate record is disclosed as history, not silently rewritten.
- `scripts/check_site.py`: **PASS**. It checks the current KTH hashes, both TIFF/ZIP links, static negative text, recursive local HTML links, the MDC-88 literal-rule reassessment, and absence of the synthetic MAG-PSG asset/generator/mock-data path.

### Pass 2 — tests, current release, and input-dependent checks

- Created an ignored local `.venv` and installed the repository's `requirements.txt`; no package files were added to Git.
- Full test suite: **279 passed, 36 skipped, 0 failed**; 47 Rasterio/Affine pending-deprecation warnings. Skips are input-dependent in this checkout.
- `scripts/validate_current.py`: **PASS** for saved KTH-88 TIFF/ZIP hashes and the stored independent validation record; format fields pass, holdout and uniqueness remain negative, and `ok_to_submit=false`.
- `scripts/readiness.py`: **BLOCKED** for the expected reasons: holdout point estimate below the stored incumbent and literal overlap above 0.70.
- `scripts/check_site.py`: **PASS** after the recursive site audit.
- `scripts/validate_kth88.py`: cannot complete because `data/bridge/sample_submission.tif` is absent. This review did not restore an owner-mirrored sample or registry and does not claim fresh comparison against the official private download. The repository's saved byte/hash audit is not a substitute for that missing input.

### Pass 3 — requirements, claims, and stop rules

- The complete task and standing constraints captured from the current project handoff are preserved in the README's **Canonical User Prompt and Standing Operating Constraints** section; `PROMPT.md` directs each session to reread it.
- H33's 0.2778 remains **USER-REPORTED**, not organizer-confirmed. The repository's dated leaderboard snapshot is not a receipt and was not freshly fetched in this follow-up. Holdout DTI is not a leaderboard projection. This work cannot demonstrate that it beats H33 or the public best.
- The KTH lane is stopped after its duplicate verdict. No experiment, training run, external-data fetch, new TIFF, submission selection, portal upload, or slot spend occurred.
- No official web pages or external source endpoints were freshly fetched during this follow-up. Existing official URLs are retained as source pointers and prior dated notes, not represented as newly verified. Competition training inputs are absent locally; no source availability, exact AOI coverage, or redistribution permission is newly claimed.

## H33: plausible mechanism and what cannot be claimed

The repository's SHA-pinned pixel lineage is consistent with H33 being a thinned descendant of the H19-5/D2.8 family: later versions remove many predictions close to mapped faults while retaining broader support. Because the distance-weighted Tversky metric penalizes false positives, dropping redundant catalogue-adjacent predictions could improve precision without sacrificing farther-off-catalogue coverage. The recorded 6,436 removed D2.8 pixels lying within two pixels of the mapped catalogue supports this mechanism; correlated lineage rasters do not establish causation or authenticate the reported live score.

`0.2778` remains a user report without an organizer receipt. The repository records a public leaderboard snapshot of 0.4413 dated 2026-10-24; it was not freshly fetched here and is not a score for this candidate. KTH-88's local HOLDOUT-DTI is below the stored incumbent and cannot be compared numerically with a leaderboard score. Therefore, **no claim that this work beats H33 or any leaderboard entry is supported**.

Evidence notes: [`h33-forensics-20261024.md`](h33-forensics-20261024.md) · [`evidence/h33_forensics_20261024.json`](../evidence/h33_forensics_20261024.json) · [official source pointers](../docs/sources.html).

## Current TIFF and run-card facts

- TIFF: `docs/downloads/gems88-kth-antisym-magtrough-20261024-bacdc27b-DO-NOT-SUBMIT.tif`
- TIFF SHA-256: `5c7f1cb7a8c37bb4c7f3ba6eef2d42f472a050c6b21436274e4ebc0c259fd7bf`
- ZIP SHA-256: `e21c8aac70fdcca59fedd5e4b9ee2d8148dc34b12ea6b158698eb7ff5f9e75ca`
- Historical saved-byte checks: one float32 band, 37,654 binary dots, values in `[0,1]`, and a single-member ZIP whose TIFF bytes match. CRS/shape/transform were recorded against the pinned sample in the saved audit; the sample grid is not present for a fresh recheck here.
- Name (archival only): `GEMSDOE88-KTH-BACDC27B`.
- Note (105/140; archival only): `K/Th antisymmetric radiometric step + RTP trough, 37654 dots; HOLDOUT-DTI 0.0527; UNSCORED; DO NOT SUBMIT`.
- Run card: [`registry/kth88_run_card.json`](../registry/kth88_run_card.json) · saved TIFF/ZIP audit: [`docs/data/kth88_validation.json`](../docs/data/kth88_validation.json) · registry scan: [`evidence/kth88_registry.json`](../evidence/kth88_registry.json).

## Ranked candidates for a separately assigned future lane

The current KTH lane is stopped; the list below is desk research and none is authorized or validated. The ranking is qualitative, not a numeric DTI projection. It treats “new” as **untried-to-run**, not new to repository notes or literature. Full layer/mechanism/mimic/difference and input caveats are in [`NEW_HYPOTHESES.md`](../NEW_HYPOTHESES.md).

1. **H-QTS: basement–surface directional discordance** — competition `depth_to_base_surf` (band 15), `det_elev` (band 12), optional slope/gravity layers; multiscale basement gradients discordant with smooth surface gradients. Possible blind basin faults; mimic: alluvial-fan toe onlap/lithologic contact. Qualitative medium–high gain potential / low–medium compute. Previously described in a note, not run as a standalone experiment.
2. **RTP–gravity frequency/azimuth admittance** — competition RTP band 2 and gravity band 13; local multiscale cross-spectral transfer ratio and cross-phase. Possible buried damage-zone changes; mimic: unfaulted intrusive contact. Qualitative medium potential / medium cost. Preregistered but unrun.
3. **Physical MAG-PSG phase-congruency ridges** — competition magnetic anomaly/RTP bands 1/2 and TMI band 14; documented pseudogravity transform under explicit field/magnetization assumptions, then multiscale phase congruency. Mimics: remanently magnetized dike/plug or leveling seam. Qualitative low–medium potential / medium–high cost. The former mock builder was not a physical experiment and has been removed.

No top candidate was validated because the competition inputs are absent locally, the current lane is stopped, and no new method lane was assigned. The external-source candidates previously discussed (vegetation, temperature, cross-drainage, InSAR/ComCat) and the implemented H88-H4 chi/ksn channels are not re-labelled as novel.

## Limitations and remaining work

1. Restore authorized, hash-verified official competition inputs in an environment with the required account/access; do not assume the owner mirror is authoritative or redistributable.
2. Obtain an explicit new lane assignment, then pre-register one candidate. Use shared `vendor/gems57` tools, whole-component buffered hide-and-recover, visible-fault-only catalogue features, pixel-exact masks, pooled DTI with α=0.2/β=0.8 and the 300 m triangular kernel, 95% CI and withheld-positive count.
3. Canary every feature alone, check surface Spearman correlation before placement, and check final 3-pixel overlap afterward. Stop at `|ρ| > 0.90` or >70% overlap with any one registry raster. Record the JSON run card, TIFF SHA-256, validator output, unique name/note ≤140 characters, and promote/negative verdict.
4. Re-fetch official rules/source pages and confirm data-use terms/AOI availability before claiming them checked. Obtain an organizer receipt before reporting a competition score.
5. Only after all candidate gates pass should a separate selector authorize a slot. No slot was spent in this review.
