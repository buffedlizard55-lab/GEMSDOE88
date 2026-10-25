# Session 0ab98cd1 — fail-closed CON88 withdrawal, H33 analysis, and three-pass review

**Date:** 2026-10-25
**Branch:** `arena/0ab98cd1-gemsdoe88`
**Decision:** **`DUPLICATE_STOP` · `ok_to_submit: false` · DO NOT SUBMIT**
**Budget:** 0/3 geological experiments; 0 new candidate TIFFs; 0 weekly slots

## Executive determination

The urgent request for a genuinely protocol-unique competition GeoTIFF cannot be completed honestly under the supplied rules. The SHA-pinned `17GEMSDOE` registry raster is positive on all 5,106,385 allowed cells. Therefore every nonempty candidate has literal forward overlap 1.0, above the 0.70 stop limit, before a surface, feature, dot set, or TIFF is constructed. The request also contains no actual single-method paragraph, so this review did not invent a lane.

The previous H88-CON88 clearance was a fail-open contradiction. It replaced the literal rule with an equal-support top-N diagnostic for dense rasters and promoted a file despite (a) literal overlap 1.0 and (b) a recorded candidate HOLDOUT-DTI far below the project incumbent. Correction `IR-88-0AB98CD1-01` withdraws that clearance across generation, validators, cards, publication audit, site, README, prompt, and package labels. The exact TIFF prediction bytes remain unchanged at SHA-256 `e830b58e9568dff9cd120a890b250a168cabd8501783b63b796b4090ed7e8d68`; only the safety filename, ZIP wrapper/member, sidecar, and decision surfaces changed.

**One-click research download (unsafe):** [`gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif`](https://buffedlizard55-lab.github.io/GEMSDOE88/downloads/gems88-con88-consensus-ridge-37654dots-20261025T161406Z-zeros-DO-NOT-SUBMIT.tif). It passes local format checks but fails scientific and literal-uniqueness promotion. Do not upload it.

## Why the owner-reported H33 `0.2778` may have performed well

`0.2778` is a **USER-REPORTED** result. No submission-page receipt in this repository links that number to the measured H33 bytes, so it is not `ORGANIZER-CONFIRMED`.

The on-disk geometry supports a mechanistic—but not causal—explanation:

1. **H33 is an emission-subtraction lineage, not an independent model.** The 37,654 H33 dots are a strict subset of SOLO-D2.8, D2.8, and H19-5. Relative to D2.8, 6,436 dots were removed and every removed dot lay within two pixels of the mapped catalogue. No dot was added after H19-5.
2. **Catalogue-collar removal can improve the denominator.** The shared DTI uses
   `TPw / (TPw + 0.2·FPw + 0.8·FNw)` with a 300 m triangular kernel. Catalogue pixels are excluded from the scored target. If collar emissions contribute no marginal hidden-truth credit, deleting them reduces the weighted false-positive term without reducing `TPw`. That is a valid algebraic precision lever; the unobserved hidden labels are required to establish that the deleted dots really were false positives.
3. **Kernel-scale spacing limits redundant emissions.** H33's minimum nearest-neighbour spacing is 2.828 px, close to the three-pixel/300 m kernel radius. Truth credit is a per-truth-pixel maximum, whereas false-positive burden is accumulated per emitted dot. Spacing can therefore preserve coverage while avoiding several dots competing for the same truth credit.
4. **It allocates budget away from known structure.** Median catalogue distance is 19.647 px. The historical fleet association between far-from-catalogue support and user-reported score is consistent with a blind-fault search objective. It is observational, selected after many submissions, and not proof that distance itself causes performance.
5. **The local holdout does not validate the public claim.** H33's fixed raster scores HOLDOUT-DTI 0.006697 [0.005990, 0.007368] on the recorded 60,988-positive instrument. That mismatch suggests catalogue hide-and-recover and the organizer's hidden blind-fault distribution are not exchangeable for this sparse emission lineage. It does not validate H33; it limits what can be inferred locally.

The defensible conclusion is that H33 may have won through **emission geometry and false-positive subtraction**, not a newly demonstrated geological detector. Ancestry and correlation do not establish causation, and the score claim remains unreceipted.

## Can a new approach be shown likely to beat H33?

**No, not from current evidence.** CON88's consensus/ridge mechanism is plausible, but plausibility is not a promotion gate:

- fixed-TIFF HOLDOUT-DTI is 0.0;
- historical per-fold re-emission HOLDOUT-DTI is 0.001714 [0.001325, 0.002143], evaluator `gems57-pooled-hide-v2`, n=60,988;
- the project incumbent record is 0.205991 [0.188105, 0.223344], n=22,893 (historical, not a fair same-fold superiority test, but orders of magnitude above CON88);
- literal final-dot overlap is 1.0 > 0.70 against the universal witness;
- no organizer receipt, current quota, or authenticated portal acceptance is available.

A score above `0.2778` would be an unsupported projection. The correct result is negative: no approach in this review can be shown likely to beat H33, and no weekly slot should be spent.

## Ranked untried geological hypotheses before any future implementation

These are conditional, source-bound proposals—not experiments, predicted scores, or generation permission. All are blocked by the literal preflight. “Expected DTI improvement” is stated directionally because assigning a number without a holdout run would violate the evidence-label rule.

### 1. H88-SPR — repeated scarp-profile restoration against drainage/shoreline null

- **Exact layers:** `data/training_features.tif` bands 12/19 (`det_elev`, `det_elev_slope`); `data/external/topo_10m_derived_100m_u8.tif` bands 8/9 (`hs_lineament`, `dem_mean`); `data/external/lidar_scarp_features_u8.tif` bands 3/10/11/12 (`step_max`, `coh100`, `strike`, `valid`); `data/external/dem10_chi_100m_u8.tif` bands 1/4 (`chan_n`, `valid_n`).
- **Transform/signature:** on independent along-strike swaths, compare smooth-landform-plus-signed-step restoration with a no-step profile; require repeated polarity/coherence away from channels, while decoding validity and saturation from the pinned manifests.
- **Missing-fault rationale:** a weak, cover-softened piedmont offset can repeat along strike while falling below mapping thresholds. No mapped trace seeds the score.
- **Named non-fault mimic:** fluvial terrace risers and constant-elevation pluvial shoreline benches.
- **Difference from repository work:** LSC/TDKL/VESS/SHORE use responses, polarity, knickpoints, or shoreline context; none fits a held-swath landform-restoration likelihood. MMRX restores magnetic texture, not topography.
- **Expected DTI improvement:** highest directional potential of the remaining queue, conditional on adding far/blind credit and beating drainage/shoreline nulls; no numerical projection.
- **Cost:** medium; cached inputs only.

### 2. H88-AWA — terrain-matched radiometric alteration-width asymmetry

- **Exact layers:** `data/external/geodawn_rad_u8.tif` bands 1/2/3 (quantized K/Th/U indices); `data/training_features.tif` bands 2/15/19 (`rtp`, `depth_to_base_surf`, `det_elev_slope`).
- **Transform/signature:** fit within-band, terrain-matched cross-strike residual decay widths on both flanks and require repeated asymmetry with a local RTP depression. Quantized code values must not be divided or described as calibrated concentrations.
- **Missing-fault rationale:** a covered permeable structure may create asymmetric wall-rock weathering/alteration without a visible scarp.
- **Named non-fault mimic:** differential weathering of adjacent lithologies and K-rich transported alluvium.
- **Difference from repository work:** KTH/MVRD use enrichment, redox, or edge responses; AWA tests fitted relative decay width rather than another radiometric high.
- **Expected DTI improvement:** low-to-moderate directional potential if parent-material matching rejects broad lithologic false positives; no numerical projection.
- **Cost:** medium; quantization, saturation, and background fitting are material risks.

### 3. H88-CBC — conductive basin-breach connectivity against paleochannel null

- **Exact layers:** `data/training_features.tif` bands 12/13/15/17 (`det_elev`, `iso_grav_anom`, `depth_to_base_surf`, `cond_surf`); `data/external/dem10_chi_100m_u8.tif` bands 1/4 (`chan_n`, `valid_n`).
- **Transform/signature:** compare narrow conductivity connectivity across independently inferred basin-boundary saddles with a smooth basin-fill null; require a boundary-normal gravity discontinuity and explicitly test terrain-aligned drainage.
- **Missing-fault rationale:** a buried cross-basin structural pathway can lack a mapped surface trace.
- **Named non-fault mimic:** unfaulted alluvial paleochannels and saline groundwater plumes.
- **Difference from repository work:** CTRA/DHTC use conductivity curvature and thermal conjunctions; CBC tests topology-preserving cross-boundary connectivity against an explicit drainage null.
- **Expected DTI improvement:** low and uncertain; only plausible if the topology test adds far-field credit beyond coarse conductivity false positives; no numerical projection.
- **Cost:** medium-high; coarse modeled fields limit identifiability.

A future authorized run must freeze one lane and at most three experiments, rebuild catalogue-derived features from visible faults within each whole-segment buffered fold, mask visible faults pixel-exactly, run every feature-alone AUC canary (symmetric AUC >0.90 stops), reproduce the incumbent on identical folds, and require a positive paired physical-block improvement before full registry and slot selection.

## Source and provenance boundary

- **Freshly verified through the GitHub API:** [DrivenData's official reference solution README at commit `aebe92f`](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md), Git blob `a8814f99c395d12a8e1c3731c738e61d7dca06b5`, content SHA-256 `cfa4d55559c9128313beb9417eae7e0a94c31677132afb1120f9e86222804239`. It documents a separate competition-data download and CPU/GPU environments; it does not certify H33, CON88, or the proposed geology.
- **Manual official review targets, not freshly retrieved in this environment:** [competition problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [submission portal](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR 1391](https://gdr.openei.org/submissions/1391), and [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). Their hosts were outside this session's allowed network; current terms, timing, quota, and authenticated bytes are not asserted.
- Restored data came from SHA-pinned owner mirrors, not an authenticated organizer download. Local manifests establish byte identity and layer descriptions, not organizer provenance or geological truth.
- All reported H33/leaderboard values without an actual submission receipt remain owner/user/public claims, never `ORGANIZER-CONFIRMED` candidate scores.

## Corrections implemented

1. Withdrew CON88 promotion in `run_card_con88.json`, `registry/con88_gates.json`, public mirrors, README, PROMPT, submission guide, standalone page, report, sidecar, and downloadable names.
2. Replaced the CON88 generation exception with delegation to `scripts/generation_guard.py`; retained equal-support only as a diagnostic.
3. Rewrote `validate_con88.py` to validate an archived research package and fail `--require-submit` with exit 2.
4. Removed the CON88 publication-audit/site exceptions; every served TIFF and ZIP must now contain `DO-NOT-SUBMIT` and every audit row must remain `ok_to_submit: false`.
5. Preserved exact TIFF bytes; rebuilt only the negatively named one-TIFF ZIP and recorded old/new hashes in `evidence/con88_clearance_withdrawal_20261025.json`.
6. Added regression coverage for shared preflight delegation, literal gate precedence, holdout failure, negative naming, current-surface consistency, and real-browser coverage of `con88.html`.

## Three review passes

### Pass 1 — reproduce and repair

- Restored the SHA-pinned validation tier and reproduced generation guard/preflight exit 2 with `DUPLICATE_STOP`.
- Initial full suite: **871 passed, 3 failed, 23 skipped**. Two failures were stale active-browser evidence hashes; one regression test attempted a no-op replacement of an obsolete `47/47` inventory token.
- Audited and corrected the fail-open CON88 path without constructing features or writing a GeoTIFF.

### Pass 2 — adversarial review and recheck

- Focused correction suite: **248 passed**, 14 warnings, 55.22 s; fresh real-browser audit passed eight desktop/mobile cases including the independently reachable CON88 page and actual TIFF-click SHA verification.
- The integrated full suite then found six additional presentation/test-harness regressions: **875 passed, 6 failed, 23 skipped**. Repairs restored the exact README inventory language, retained `IR-88-B4DFA10C-08` continuity in the current guide, and gave isolated site-guard fixtures the newly mandatory root decision surfaces.
- Full SHA-pinned training/external owner-mirror tier was restored and prepared; nine shared feature planes loaded. `audit_research_state.py --check-inputs` passed. This was data validation only—no feature construction for a proposed hypothesis, model fit, or raster generation.

### Pass 3 — clean final recheck

- Full suite: **881 passed, 0 failed, 23 skipped, 64 warnings** in 208.05 s.
- Saved-byte audit: **48/48** public TIFF/ZIP pairs pass research-package checks; **0** are protocol-eligible. CON88 TIFF SHA remained unchanged; its negatively named ZIP contains exactly the same TIFF bytes.
- Canonical renderer, research-state input-pin audit, normal and optimized site guards all passed.
- Fresh browser receipt: **8/8** responsive cases pass with no overflow/errors; JavaScript-disabled and failed-evidence-fetch states stay negative; downloaded/clicked canonical TIFF bytes match SHA-256.
- Shared generation guard and preflight each exited **2** with `DUPLICATE_STOP`; CON88 archive validation exited 0 for research integrity and `--require-submit` exited **2**. No experiment or slot was used.

## Limitations, access needed, and next work

1. The literal uniqueness contract is unsatisfiable while an all-positive registry witness is included. Only the rule owner can explicitly revise the shared contract; this review authorizes no dense-prior, creation-order, or equal-support exemption.
2. If the contract becomes satisfiable, preregister H88-SPR first and reserve an untouched spatial audit partition because many methods have reused the same folds.
3. Obtain authenticated competition data/provenance, current official rules/timing, actual account quota, and a submission receipt through authorized portal access. Do not infer any of these from a local format pass.
4. A new artifact must beat the same-fold incumbent with paired confidence, pass every canary and literal registry check, and then pass a separate slot selector. Until then, **DO NOT SUBMIT**.
