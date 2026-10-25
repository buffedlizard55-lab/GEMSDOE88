# Integrated repository review — session 4a703178 (2026-10-25)

## Executive determination

**DO NOT SUBMIT.** No new GeoTIFF was generated, no geological experiment was run, and no weekly slot was used. Fresh execution reproduces the shared `DUPLICATE_STOP`: the SHA-pinned `17GEMSDOE` witness is positive on all **5,106,385 / 5,106,385** allowed pixels, so every nonempty candidate has literal overlap lower bound **1.0**, above the user's **0.70** stop threshold.

While this branch was under review, main merged PRs #181 and #182. Those changes independently revoked H88-CON88's unsupported equal-support clearance, quarantined its unchanged TIFF, made validation read-only, and published the canonical negative review. This branch integrated that work rather than competing with it. The authoritative correction receipt is [`evidence/con88_clearance_withdrawal_96f5f523.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/evidence/con88_clearance_withdrawal_96f5f523.json). CON88's top-N/equal-support overlap **0.693631** remains a historical diagnostic; binding literal overlap is **1.0**.

The package is safe to download **for research only** because it is machine-checked and visibly marked `DO-NOT-SUBMIT`. It is unsafe to upload to the competition. The unique-submission requirement remains **unmet**, rather than being simulated by renaming bytes or changing an approval boolean.

## Ranked hypotheses frozen before implementation

The request refers to a “single method paragraph,” but no identifiable method paragraph is present. No lane was invented. The source-reviewed conditional queue remains the three still-unimplemented proposals below. “Untried” means not found in this checkout's reviewed model source; it is not a worldwide-novelty claim. Expected potential is ordinal, not a projected score.

| Rank | Hypothesis and exact cached layers | Transform / off-catalogue mechanism | Named mimic and novelty | Expected potential / cost | Official/free availability and limitation |
|---|---|---|---|---|---|
| 1 | **H88-SPR — repeated scarp-profile restoration.** `training_features.tif` bands 12/19; `topo_10m_derived_100m_u8.tif` 8/9; `lidar_scarp_features_u8.tif` 3/10/11/12; `dem10_chi_100m_u8.tif` 1/4. | On independent along-strike swaths, compare smooth-landform-plus-signed-step with a no-step fit; require repeatable held-profile restoration away from drainage. A weak cover-softened piedmont offset may remain when no mapped trace seeds the surface. | Fluvial terrace risers and constant-elevation pluvial shoreline benches. Unlike LSC/TDKL/VESS/SHORE, this fits a cross-validated restoration likelihood; MMRX restored magnetic texture. | First; moderate but highly uncertain / medium. | Pinned local topographic/LiDAR caches are available and attributed to public official elevation products. The 100 m cache cannot support a sub-pixel-throw claim; current external permissions were not freshly authenticated. |
| 2 | **H88-AWA — terrain-matched alteration-width asymmetry.** `geodawn_rad_u8.tif` bands 1/2/3; `training_features.tif` bands 2/15/19. | Fit two-flank decay widths of terrain-matched within-band K/Th/U residuals and require repeated asymmetry plus local RTP depression. A covered permeable structure might broaden alteration on one wall without a scarp. | Differential weathering of adjacent units and K-rich transported alluvium. Unlike KTH/MVRD, this tests fitted width rather than another enrichment edge. | Second; low-to-moderate, uncertain / medium. | GeoDAWN is represented by a SHA-pinned cache attributed to free USGS public data. Values are quantized indices, not calibrated concentrations or valid physical ratios. |
| 3 | **H88-CBC — conductive basin-breach connectivity.** `training_features.tif` bands 12/13/15/17; `dem10_chi_100m_u8.tif` 1/4. | Compare narrow conductivity bridges across independently inferred basin saddles with smooth basin-fill and terrain-aligned drainage nulls; require a boundary-normal gravity change. A buried connection may lack a mapped surface trace. | Unfaulted permeable alluvial paleochannels and saline groundwater plumes. Unlike CTRA/DHTC, this tests topology-preserving cross-basin connectivity against an explicit drainage null. | Third; low, uncertain / medium-high. | Competition/shared model fields are pinned locally, but restored from owner mirrors rather than an authenticated organizer download. Coarse fields cannot prove a metre-scale conduit or geothermal vent. |

Full layer pins, transforms, falsification rules, implemented-family comparisons, and source boundaries are in [`registry/hypothesis_queue.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/registry/hypothesis_queue.json) and [`research/session-693b10af-hypotheses.md`](session-693b10af-hypotheses.md). The official reference-solution README at pinned commit `aebe92f…` documents CPU/CUDA/MPS operation but does not validate these geological mechanisms.

## Conditional rank-1 validation — not executed

If an authorized shared protocol first resolves the pre-placement contradiction, H88-SPR would:

1. Freeze at most three experiments / two hours and reuse the cached feature stack, shared `evaluate_holdout.py`, and shared `submission_writer.py`; no private fork.
2. Withhold whole fault segments with the shared buffer. Recompute every catalogue-conditioned feature from visible faults only, mask visible fault pixels exactly, and prevent hidden truth from affecting features, masks, normalization, or placement.
3. Rebuild pooled DTI with α=0.2, β=0.8 and the 300 m triangular kernel. Report only `HOLDOUT-DTI`, evaluator/version, withheld-positive count, and 95% confidence interval.
4. Run every feature alone as a leakage canary. Symmetric AUC above 0.90 is a stop until disproven; include profile-sign scramble and drainage/shoreline nulls.
5. Recompute the incumbent on identical folds and require a positive paired improvement. The historical record is H88-BPWD `HOLDOUT-DTI 0.205991 [0.188105, 0.223344]`, `gems57-pooled-hide-v2`, n=22,893; it is not a forecast or organizer score.
6. Before placement and on final dots, test full in-scope surface rank correlation (stop above 0.90) and literal 3-pixel overlap against every registry raster (stop above 0.70). Holdout improvement cannot override uniqueness.
7. Independently reopen TIFF and ZIP: one band, exact sample CRS/shape/transform, finite `[0,1]`, zero outside footprint and on visible catalogue, exactly one byte-identical TIFF member. Slot selection remains separate.

Step 0 fails, so none of these scientific steps was pretended to have run.

## H33's user-reported 0.2778: mechanism without overclaim

- **Verified construction:** pinned GEMSDOE32 records show H33-2-B2 starts from a 0.2708 base and removes every emitted dot within two pixels of the visible catalogue, leaving **37,654** positives and zero on-catalogue pixels. That source labels **0.2747 as a projection**, not an observed organizer score.
- **Metric mechanism:** triangular-kernel truth credit takes a local maximum, while predicted positive mass accumulates in the false-positive term with α=0.2. Removing a true false-positive lowers the denominator without reducing the numerator, so DTI rises algebraically. Spacing near the 300 m kernel scale can also limit redundant mass.
- **Geological interpretation:** pruning catalogue-adjacent dots reallocates budget off catalogue, which is consistent with targeting blind faults but does not prove remaining structures are faults.
- **Limits:** 0.2778 is user-reported; there is no organizer receipt. Shared ancestry, prior-result selection, and common inputs confound fleet correlations. The repository cannot infer hidden labels, establish causality, or guarantee transfer above 0.2778. No value here is labeled `ORGANIZER-CONFIRMED`.

## Integrated corrective state

- The canonical CON88 TIFF SHA-256 remains `e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68`; prediction bytes did not change.
- The canonical repacked ZIP SHA-256 is `73ee608ad9401e70bbaeb1b28104118086b554569ae5891146de6430f39bf9cb` and contains only the same negatively named TIFF.
- `scripts/con88_preflight.py` delegates to the shared generation guard. `scripts/validate_con88.py` is read-only; default validates research bytes and `--require-submit` exits 2.
- The old fixed-prediction/full-catalogue-collar “holdout” is explicitly unusable for promotion. Equal-support figures are diagnostic only.
- All **48/48** Pages TIFF/ZIP packages pass local research checks and **0/48** are protocol-eligible.

## Additional irregularity fixed by this session

**IR-88-4A703178-01 — startup-audit same-row alias and historical-evidence mutation.** One ledger entry may legitimately use the same SHA-256 in its primary and fallback columns. The old audit flattened both columns, mistook that same-row alias for cross-entry reuse, and rewrote a dated 2026-10-23 receipt with current counts. It now detects ownership across distinct row IDs and writes current output only to ignored `.cache/session-start-audit.json`. A regression test proves same-row aliases pass and the historical receipt's SHA-256 remains unchanged.

## Three successive passes

### Pass 1 — initial correction

Reproduced the pinned literal stop, traced the obsolete exception, quarantined the package, corrected records, and added focused tests without running a geological experiment. This work independently converged with the later-merged PR #181 correction.

### Pass 2 — integrate and review current main

Fetched current main, reviewed PRs #181/#182, merged them into this fixed Arena branch, and chose their canonical CON88 package, metadata, validator, site evidence, and correction receipt. Retained only additive work: the startup-audit fix, explicit historical CON88 narrative correction, diagnostic regression coverage, and this session's negative review. Duplicate correction evidence was removed.

### Pass 3 — final integrated verification

The post-merge full suite passed **905 passed / 23 skipped / 0 failed** with 70 dependency warnings in 256.44 seconds. The saved-byte audit reopened **48/48** Pages packages with **0** protocol-eligible; research-state input pins, canonical renderer, and normal/optimized site checks passed. The shared generation guard and `validate_con88.py --require-submit` each returned expected exit 2. Startup audit returned `STOP_NO_NEW_VARIANTS`, wrote only `.cache`, and left the dated receipt at SHA-256 `047ded08…2798`.

A fresh Chromium 153 audit at `2026-10-25T19:07:06.437Z` passed seven desktop/mobile/legacy cases, failed-fetch denial, no-JavaScript denial, and actual click-download SHA verification. The session receipt is `evidence/session_4a703178_browser_check.json`; it does not replace the canonical session 96f5f523 receipt or alter old evidence.

## Run card and outcome

The current session's single machine record is [`registry/session_4a703178_run_card.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/main/registry/session_4a703178_run_card.json). The canonical public status remains the already-merged session 96f5f523 negative review; this additive audit does not replace it with a competing clearance.

**Outcome:** `0/3` experiments, `0` new rasters, `0` slots, no organizer receipt, and no submission-ready TIFF. Maximize P(Win) by preserving the slot; Own the Outcome by keeping research download safety separate from submission permission.
