# Repository correction and three-pass review — session 4a703178 (2026-10-25)

## Executive determination

**DO NOT SUBMIT.** No new GeoTIFF was generated, no geological experiment was run, and no weekly slot was used. The shared pre-placement gate reproduces `DUPLICATE_STOP`: the SHA-pinned `17GEMSDOE` witness is positive on all **5,106,385 / 5,106,385** allowed pixels, so every nonempty candidate has literal overlap lower bound **1.0**, above the user's **0.70** stop threshold.

The previous H88-CON88 exception was a policy error. Its top-N/equal-support overlap, **0.693631**, remains a useful historical diagnostic but is not the literal all-registry test the user specified. CON88's TIFF bytes and SHA-256 are unchanged; its TIFF and one-member ZIP are now visibly named `DO-NOT-SUBMIT`, all machine records say `ok_to_submit: false`, and the archived package is safe to download **for research only**. Correction receipt: [`evidence/con88_clearance_withdrawal_20261025.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/evidence/con88_clearance_withdrawal_20261025.json).

This is a valid negative outcome under the explicit stop rule. The requested genuinely unique submission TIFF remains **unmet**, rather than being simulated by renaming bytes or changing an approval boolean.

## Ranked hypotheses frozen before any implementation

The request refers to a “single method paragraph,” but no identifiable method paragraph is present. No lane was invented. The source-reviewed conditional queue therefore remains the three still-unimplemented proposals below. “Untried” means not found in this checkout's reviewed model source; it is not a worldwide-novelty claim. Expected potential is ordinal, not a projected score.

| Rank | Hypothesis and exact cached layers | Transform / off-catalogue mechanism | Named mimic and novelty | Expected potential / cost | Official/free availability and limitation |
|---|---|---|---|---|---|
| 1 | **H88-SPR — repeated scarp-profile restoration.** `training_features.tif` bands 12/19; `topo_10m_derived_100m_u8.tif` 8/9; `lidar_scarp_features_u8.tif` 3/10/11/12; `dem10_chi_100m_u8.tif` 1/4. | On independent along-strike swaths, compare smooth-landform-plus-signed-step with a no-step fit; require repeated held-profile restoration away from drainage. A weak cover-softened piedmont offset may remain when no mapped trace seeds the surface. | Fluvial terrace risers and constant-elevation pluvial shoreline benches. Unlike LSC/TDKL/VESS/SHORE, this fits a cross-validated restoration likelihood; MMRX restored magnetic texture. | First; moderate but highly uncertain / medium. | Pinned local topographic/LiDAR caches are available. They are attributed to public official elevation products, but the current sandbox could not freshly retrieve the external landing pages. The 100 m cache cannot support a sub-pixel-throw claim. |
| 2 | **H88-AWA — terrain-matched alteration-width asymmetry.** `geodawn_rad_u8.tif` bands 1/2/3; `training_features.tif` bands 2/15/19. | Fit two-flank decay widths of terrain-matched within-band K/Th/U residuals and require repeated asymmetry plus local RTP depression. A covered permeable structure might broaden alteration on one wall without a scarp. | Differential weathering of adjacent units and K-rich transported alluvium. Unlike KTH/MVRD, this tests fitted width rather than another enrichment edge. | Second; low-to-moderate, uncertain / medium. | GeoDAWN is represented by a SHA-pinned local cache attributed to USGS public data. Fresh license/landing-page retrieval was unavailable here. Values are quantized indices, not calibrated concentrations or valid physical ratios. |
| 3 | **H88-CBC — conductive basin-breach connectivity.** `training_features.tif` bands 12/13/15/17; `dem10_chi_100m_u8.tif` 1/4. | Compare narrow conductivity bridges across independently inferred basin saddles with smooth basin-fill and terrain-aligned drainage nulls; require a boundary-normal gravity change. A buried connection may lack a mapped surface trace. | Unfaulted permeable alluvial paleochannels and saline groundwater plumes. Unlike CTRA/DHTC, this tests topology-preserving cross-basin connectivity against an explicit drainage null. | Third; low, uncertain / medium-high. | Competition/shared model fields are locally pinned, but the restoration used owner mirrors rather than an authenticated DrivenData download. Coarse model fields cannot resolve metre-scale conduits or prove a geothermal vent. |

Full layers, hashes, transforms, falsification rules, implemented-family comparisons, and source boundary: [`registry/hypothesis_queue.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/registry/hypothesis_queue.json) and [`research/session-693b10af-hypotheses.md`](session-693b10af-hypotheses.md). The official DrivenData reference-solution README was freshly rechecked at pinned commit `aebe92f…`; it documents CPU/CUDA/MPS operation but does not validate these geological mechanisms. No new external data was fetched or introduced.

## Conditional validation plan for rank 1 — not executed

If and only if an authorized shared protocol can first clear the pre-placement contradiction, H88-SPR would use the required single lane:

1. Freeze at most three experiments / two hours and reuse the cached feature stack, shared `evaluate_holdout.py`, and shared `submission_writer.py`; no private evaluator or writer fork.
2. Withhold whole fault segments with the shared buffer. Derive every catalogue-conditioned feature from visible faults only, mask visible fault pixels exactly, and never let hidden truth affect features, masks, normalization, or placement.
3. Rebuild pooled DTI with α=0.2, β=0.8 and the 300 m triangular kernel on every fold. Report only `HOLDOUT-DTI`, evaluator/version, withheld-positive count, and 95% confidence interval.
4. Run every feature alone as a leakage canary; symmetric AUC above 0.90 is a stop until disproven. Include profile-sign scramble and drainage/shoreline nulls.
5. Recompute the incumbent on identical folds and require a positive paired improvement. The historical record is H88-BPWD `HOLDOUT-DTI 0.205991 [0.188105, 0.223344]`, `gems57-pooled-hide-v2`, n=22,893; this is not a forecast or organizer score.
6. Before placement and on final dots, test full in-scope surface rank correlation (stop above 0.90) and literal 3-pixel overlap against every registry raster (stop above 0.70). A holdout win cannot override uniqueness.
7. Reopen TIFF and ZIP independently: one band, exact sample CRS/shape/transform, finite values in `[0,1]`, zero outside footprint and on visible catalogue, exactly one byte-identical TIFF member. Slot selection remains a separate automated decision.

Step 0 fails today, so none of steps 1–7 was pretended to have run.

## PhD-level interpretation of H33's reported 0.2778

The evidence separates construction facts from causal interpretation:

- **Verified construction:** at pinned GEMSDOE32 source commit `012e17b…`, H33-2-B2 starts from a 0.2708 base and removes every emitted dot within two pixels of the visible catalogue. The result contains **37,654** positives and zero on-catalogue pixels. The same source labels **0.2747 as a model projection**, not an observed organizer score.
- **Metric mechanism:** with triangular-kernel truth credit, a nearby cluster does not add linearly because each truth location receives a local maximum, while predicted positive mass contributes to the false-positive term with α=0.2. Removing a dot that is truly a false positive lowers the denominator without reducing the numerator, so DTI rises algebraically. Spacing near the 300 m kernel scale can also reduce redundant false-positive mass.
- **Geological interpretation:** pruning catalogue-adjacent dots shifts allocation toward off-catalogue structures, but that is only consistent with discovering blind faults; it does not prove that those remaining structures are faults.
- **Limits:** 0.2778 is user-reported and no organizer receipt is present. Shared ancestry, selection on previous results, and common input fields confound fleet correlations. The repository cannot identify which removed dots were hidden-label false positives, attribute causality, or guarantee transfer above 0.2778. No value in this review is labeled `ORGANIZER-CONFIRMED`.

## CON88 revocation and automated package state

The audit fixed the exception once at shared boundaries:

- `scripts/con88_preflight.py` now delegates directly to `scripts/generation_guard.py` and exits 2 under normal, optimized, and module invocation.
- `scripts/validate_con88.py` is read-only. Its default mode validates a negative research archive; `--require-submit` exits 2. It can no longer rewrite clearance metadata.
- `scripts/audit_downloads.py`, `scripts/check_site.py`, Pages metadata, and tests contain no CON88 whitelist.
- `registry/con88_gates.json`, `run_card_con88.json`, adjacent artifact metadata, and the historical experiment ledger preserve measurements but say negative / `ok_to_submit=false`.
- The archived TIFF SHA-256 remains `e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68`. The repacked ZIP SHA-256 is `6d5dbf761a81d3ee2e3228da737ad1a2a76c732c5bec42867e00c50a364c864c` and contains only the same negatively named TIFF.
- All **48/48** Pages TIFF/ZIP packages pass research format/package checks; **0/48** are protocol-eligible.

The format check addresses the historical `[0,1]` class of errors (finite values, no hidden second band, correct grid) but cannot establish portal acceptance without the exact rejected upload and receipt.

## Other irregularities corrected

1. **IR-88-4A703178-01 — unauthorized CON88 equal-support exception:** revoked as above; scientific bytes and measurements preserved.
2. **IR-88-4A703178-02 — startup-audit false positive and historical mutation:** the audit had treated a single ledger row's identical primary/fallback hash aliases as cross-entry duplication and rewrote a dated 2026-10-23 receipt. It now detects owners across distinct row IDs and writes current runtime output only to ignored `.cache`; the historical receipt remains unchanged.
3. **IR-88-4A703178-03 — stale publication evidence/counts:** regenerated the complete 48-package audit, removed the lone positive inventory row, corrected the executive guide, and prepared a fresh current browser receipt rather than rewriting a historical receipt.

## Three successive passes

### Pass 1 — policy and implementation

Reproduced the pinned literal stop before any feature work; traced CON88's exception through preflight, validator, audits, metadata, Pages, and tests; quarantined the package without changing TIFF bytes; corrected shared code and negative records. Focused safety tests passed after regenerating the package audit.

### Pass 2 — adversarial review of pass 1

Reviewed direct, `-O`, and `-m` execution paths; added fail-closed tests for the compatibility preflight and `--require-submit`; verified ZIP member identity and read-only validation; removed every publication whitelist; fixed same-row ledger hash semantics and immutable historical output. The first integrated review correctly exposed stale audit/browser/count evidence rather than accepting it.

### Pass 3 — final integrated verification

The final full suite passed **883 passed / 23 skipped / 0 failed** with 64 dependency warnings in 243.98 seconds. Normal and optimized site guards passed. The saved-byte audit reopened **48/48** published packages with **0** eligible; research-state/input pins passed; renderer check passed; the shared generation guard and strict CON88 validator each produced their expected exit 2 negative decision. A fresh Chromium 153 audit passed seven desktop/mobile/legacy cases, fail-closed evidence-fetch and no-JavaScript cases, and actual click-download SHA verification. The current receipt is `evidence/session_4a703178_browser_check.json`; older receipts were not rewritten. The current startup audit reports `STOP_NO_NEW_VARIANTS` and writes only ignored runtime state; the dated 2026-10-23 receipt remains unchanged.

## Machine run card and outcome

The single current run card is [`registry/session_4a703178_run_card.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/registry/session_4a703178_run_card.json). It records: rank-1 proposal not run, named mimic, null holdout/CI with reason, literal overlap 1.0, no new raster SHA because no raster exists, automated negative validator output, a ≤140-character unique negative name/note, `promote: false`, and `verdict: negative`.

**Outcome:** `0/3` experiments, `0` new rasters, `0` slots, no organizer receipt, and no submission-ready TIFF. Maximize P(Win) by preserving the slot; Own the Outcome by exposing the contradiction and making the research archive unambiguously safe/unsafe.
