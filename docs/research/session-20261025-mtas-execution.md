# Session 2026-10-25 (execution) — H88-MTAS: why H33 leads the fleet, and a tested negative

**One-line answer.** A brand-new, de-novo GeoTIFF *was* generated this session by executing the
frozen H88-MTAS preregistration end-to-end — and the automated gates say
**DOWNLOAD FOR RESEARCH: YES · SUBMIT: NO — DO NOT SUBMIT**. It is unique against every
obtainable *dot-field* registry raster, but its hide-and-recover score is at the
no-information level and the literal any-raster rule fires against two continuous
probability surfaces. Zero weekly slots were spent. Negative results are deliverables.

- **New file (one click):** [`docs/downloads/gems88-mtas88-admittance-37654dots-20261025-zeros-DO-NOT-SUBMIT.tif`](../docs/downloads/gems88-mtas88-admittance-37654dots-20261025-zeros-DO-NOT-SUBMIT.tif)
  · [one-TIFF ZIP](../docs/downloads/gems88-mtas88-admittance-37654dots-20261025-zeros-DO-NOT-SUBMIT.zip)
  · SHA-256 `2cb828939e11cf07e12be7917722f73816550ed4e297e2409b8674ac131479cc`
- **Prepared name (36/140):** `GEMSDOE88-MTAS88-ADMITTANCE-20261025`
- **Prepared note (91/140):** `MTAS88 grav-mag scale-admittance 37654d; HOLDOUT-DTI 0.0496 n=22893; UNSCORED DO-NOT-SUBMIT`
- **Machine run card:** [`registry/mtas88_experiment_run_card.json`](../registry/mtas88_experiment_run_card.json)
  · **Re-validate anytime:** `python scripts/validate_mtas88_experiment.py` (exit 0 research; `--require-submit` exit 2)

---

## 1. Why did H33 (`h33-h33-2-b2-…-zeros`, owner-reported 0.2778) beat ~90 sibling files?

Evidence classes first, because this repository labels every number. **0.2778 is an
owner/user-reported CLAIM** — there is no DrivenData receipt for it in this repo, so it is
*not* ORGANIZER-CONFIRMED. What *is* verified on disk (SHA-256
`c55bafc4…ab6fa9`, 37,654 dots, restored and re-measured this session as part of the
243-raster registry audit) is its geometry. Four mechanisms, in order of importance:

1. **The metric pays for coverage and barely charges for false alarms — until dots become
   redundant.** The official distance-weighted Tversky index (verified 2026-10-25 on the
   [official problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):
   α = 0.2 on FP, β = 0.8 on FN, triangular kernel R = 300 m) gives each truth pixel credit
   only from the *nearest* dot (`max` over the kernel). A second dot next to an existing one
   therefore earns ≈ 0 extra TP but still pays α·(1 − k) of FP. The lineage H19-5
   (121,131 px, CLAIM 0.1922) → D2.8 (44,090, CLAIM 0.2600) → SOLO (40,199, CLAIM 0.2708) →
   H33 (37,654, CLAIM 0.2778) is a strict-subset *thinning* chain (verified set inclusions in
   `evidence/h33_forensics_20261024.json`): each step mostly deleted redundant dots, and the
   reported score rose each time. Minimum dot spacing in H33 is 2.828 px ≈ the 300 m kernel
   scale — near-optimal tiling efficiency.
2. **Dots on/near the mapped catalogue are wasted budget.** The scored truth is *new*
   expert-mapped faults; already-mapped USGS/INGENIOUS traces are not the target. The 6,436
   dots deleted between D2.8 and H33 *all* lay ≤ 2 px from a mapped fault. Across the scored
   fleet, the share of dots far from the catalogue is the strongest known correlate of the
   reported ordering (Spearman ≈ +0.89…+0.90, descriptive, n = 13–20 owner-reported rasters;
   `evidence/fleet_distance_prior_20261024.json`). H33's median dot-to-catalogue distance is
   19.6 px and 35.8% of its dots are > 30 px away.
3. **It inherited a good support set.** The H19 multiline-corroborated ridge support already
   concentrated dots on geophysically/topographically corroborated lineaments; thinning kept
   the support and fixed the emission geometry. Most sibling failures are the opposite trade:
   sophisticated surfaces emitted as dense fields (redundancy tax) or catalogue-hugging dots
   (wasted near known faults).
4. **Break-even arithmetic.** At DTI ≈ 0.28 a new non-redundant dot only needs expected
   kernel credit k > α·DTI ≈ 0.056 to help; H33's inferred average dot credit (≈ 0.14 in the
   prior forensic audit) is ~2.6× break-even, while dense siblings dilute average credit
   below it.

**Can we beat 0.2778?** Context verified today: the public leaderboard #1 is **0.4413**
(xiaofanhu, 29 submissions; fetched 2026-10-25 from the
[official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)),
and #10 is already 0.3335 — so 0.2778 is a *fleet-internal* best, not a competitive score,
and the prompt's alternative "0.3195 is the highest score right now" figure is stale
(flagged below). Beating 0.2778 credibly requires a surface that (a) recovers withheld
faults well above the no-information null on spatially blocked holdout, (b) emits at
H33-like geometry (≈ 37–44k dots, ≥ 2.8 px spacing, 0% within 2 px of the catalogue,
≥ 35% beyond 25 px), and (c) is unlike every prior raster. This session's candidate
satisfies (c) and partially (b), and fails (a) decisively. **No raster in this repository
has an ORGANIZER-CONFIRMED score above 0.2778, and no projection in this repo (e.g. the
LBCAL receipt model's 0.356) is a score.**

## 2. Ranked candidate hypotheses (3–5, untried before this session) and the one tested

Carried from the frozen 2026-10-25 review (`evidence/repo_review_20261025.json`,
`research/candidate-hypotheses-20261025-mtas.md`); ranked by expected DTI gain ÷ cost.
All use only the restored cached stack — no new external data required.

| Rank | Lane | Layers | Physical signature | Why it catches a *missing* fault | Named mimic | Cost | Status |
|---|---|---|---|---|---|---|---|
| 1 | **H88-MTAS** | `rtp_grad_200m/800m`, `grav_grad_200m/800m`, `depth_to_base_log`, `det_elev_slope`, `geod_transtension` | Cross-scale admittance residual `max(0,(G200−G800)−(M200−M800))` gated by cover/low-slope/transtension | Buried basement step keeps short-scale gravity edge, magnetic edge smoothed/demagnetized; no scarp ⇒ unmapped | Unfaulted intrusive/volcanic contact; flight-line seams | Low–med | **TESTED HERE → negative** |
| 2 | H88-PRAN | `rad_k_over_th`, `det_elev_slope`, `topo10_curv_prof`, `depth_to_base_log` | Terrain-bin-matched radiometric K:Th residual with along-strike coherence | Alteration/soil signal persists over covered structure without scarp | K-rich transported alluvium; soil moisture | Low–med | Untried — next in queue |
| 3 | H88-FARC | `chi_step_max`, `ksn_jump_norm`, `topo10_hs_lineament`, `lidar_scarp_coh` | Repeated signed cross-channel χ/k_sn offsets vs catchment-matched null | Blind rupture offsets several independent drainages below per-scarp mapping confidence | Lithologic knickzones; base-level fall | Medium | Untried |
| 4 | H88-TCONS | `probe2m_dab_local`, `well_temp_anom`, `cond_edge_300m`, `depth_to_base_log` | Depth-conditioned temperature÷conductivity residual | Focused upflow along blind permeable fault diverges from regional conductive halo | Playa brines; permeable unfractured lithology | Medium | Untried (re-check GDR licence before sharing derivatives) |
| 5 | H88-FLAC | `rtp/grav_grad_200m`, `cond_edge_300m`, `geod_shearrate/dilaterate` | Multi-sensor edge persistence after flight-line-direction veto | True edge persists across sensors, not confined to E–W survey direction | Gridding/levelling artefacts; broad contacts | Low | Untried |

Difference from implemented lanes: MRR residualizes *within* magnetics; PHASE-88 tests
*angular* discordance; GTHC tests upward-continued *amplitude*; GZZC traces a gravity
*zero contour*. None computed the two-field **difference of scale responses**. That
difference is now measured — and it does not recover withheld faults.

## 3. What was run (exactly one budgeted experiment, no tuning after seeing scores)

Implementation: `src/gems88/mtas.py` + `scripts/run_mtas88_experiment.py`, reusing the
shared template only (`vendor/gems57` holdout/evaluator/metric/uniqueness/writer/validator;
shared `physics._grad_f32` + `edge.clean_band` column definitions). Inputs restored by
`scripts/restore_inputs.py --validation` + `restore_features()` + `scripts/restore_siblings.py`
(all SHA-256-pinned; `training_features.tif` = `4371c82e…23bc5`, 19 bands, band tags
asserted on disk).

| Check | Result (evidence class) |
|---|---|
| Leakage canaries, 14 features (7 inputs + 7 components), withheld positives vs off-catalogue cells | max symmetric AUC **0.5678** (`det_elev_slope`) ≤ 0.90 — PASS; composite `mtas_surface` 0.5127 ≈ chance |
| Pre-placement surface Spearman vs 243 registry rasters | worst \|ρ\| **0.1046** ≤ 0.90 — PASS (vs GEMSDOE87 BMTD surface) |
| **HOLDOUT-DTI** (`gems57-pooled-hide-v2`, seeds 20/21, 8 whole-component folds, 3 px buffer, 12 px boundary, 5×5-maxima dots ≤ 37,654/fold) | **0.049577**, 95% CI **[0.044659, 0.054417]**, **22,893** withheld positives — vs stored bar 0.187888 (descriptive, cross-scope): **−0.1383, FAIL**; also ≈ the 0.0479 no-information spaced-dot null measured in the PROVCREST audit |
| Production fingerprint (37,654 dots, catalogue excluded pixel-exactly per frozen rule) | share > 25 px **46.5%** (screen ≥ 35% ✓) but share ≤ 2 px **4.83%** (screen = 0 ✗) — screen FAIL; no post-hoc collar retune (budget = 1) |
| Final-dot uniqueness, like-for-like (241 dot-field rasters) | worst 3-px forward overlap **0.4232** ≤ 0.70 — PASS (below even that raster's 0.4376 chance halo); vs H33 itself **0.1734** |
| Final-dot uniqueness, literal any-raster | **1.0000 > 0.70 — FAIL** vs `17GEMSDOE` dense witness (halo 1.0) and 0.895 vs GEMSDOE87 BMTD (halo 0.904; chance-corrected excess −0.09). Only 2/243 registry rasters are continuous surfaces; both fire on *any* nonempty candidate (IR-88-60) |
| Saved-byte format (vendor validator + independent `validate_mtas88_experiment.py`, rasterio + tifffile) | 1 band float32, EPSG:32611, 3730×3292, exact sample transform, **0 NaN/Inf, values {0,1} ⊂ [0,1]**, nodata undeclared, 0 dots on catalogue/outside footprint, ZIP = exactly the TIFF — PASS. This file cannot trigger the portal's *"Predicted values must be in range [0, 1]"* on values; it is held for gate reasons, not format |

**Verdict: negative.** Scientific reading: gravity-minus-magnetic *scale discordance alone*
does not rank real faults above chance on hide-and-recover (per-fold DTI 0.039–0.064).
Hide-and-recover only tests catalogue-*like* faults, so a purely blind-fault signal could
in principle hide from this instrument — but with canary AUC ≈ 0.51 there is no positive
evidence for that either, and Maximize-P(Win) says do not spend a scarce weekly slot on an
unproven idea. The next queued lane is H88-PRAN under a fresh preregistration.

## 4. Irregularities flagged (verify line by line; no hallucinations)

- **IR-88-120 (stale prompt figure):** the session prompt states both 0.4413 and 0.3195 as
  "the highest score right now". The official leaderboard fetched 2026-10-25 shows #1 =
  **0.4413**; 0.3195 is stale and is not used anywhere as a target.
- **IR-88-60 (standing, re-confirmed):** the literal "> 70% of dots within 3 px of *any*
  registry raster" rule is vacuous against continuous probability surfaces (positive
  everywhere): measured here as 2 firings in 243 rasters, both continuous, both with halo
  coverage ≥ 0.90, both unavoidable by construction. It remains reported and binding for
  the submit decision (fail-closed), with the like-for-like dot-field reading reported
  beside it — never silently substituted.
- **Evidence class of 0.2778:** owner-reported CLAIM, not an organizer receipt held in this
  repo. All fleet scores in the prompt inherit that status unless a receipt is filed.
- **Provenance limit:** competition rasters are owner GitHub mirrors (SHA-pinned, internally
  consistent: sample grid 3730×3292 EPSG:32611 verified against the pinned hashes), not
  authenticated against a logged-in DrivenData download — this sandbox has no DrivenData
  credentials. Official data page for manual verification:
  https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- **Registry scope limit:** uniqueness is certified against 243 *obtainable* rasters
  (validation registry + fleet + GEMSDOE86/87/89–92 siblings + this repo's downloads), not
  an organizer-complete registry; the other ~80 sites were not enumerated byte-by-byte.
- **Organizer wording vs repo policy:** the official format text says data outside the
  bounds is "null or nan"; this repo's stricter all-finite zeros policy (0.0 outside the
  footprint, nodata undeclared) is a local precaution adopted after the owner's portal
  range error. Values are in [0, 1] either way; local PASS ≠ organizer acceptance.

## 5. Official sources used (fetched/verified 2026-10-25)

- Problem + metric + format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Leaderboard (#1 0.4413): https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Rules PDF (NLR 96647): https://docs.nlr.gov/docs/fy26osti/96647.pdf
- GeoDAWN (USGS): https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS (GDR 1391, CC BY 4.0): https://gdr.openei.org/submissions/1391
- EPSG:32611: https://epsg.io/32611 · Tversky index: https://en.wikipedia.org/wiki/Tversky_index

## 6. Limitations & what is needed next

1. **No DrivenData auth** → cannot authenticate mirror bytes against the organizer's current
   files, cannot submit programmatically, cannot obtain an ORGANIZER-CONFIRMED score.
   Selecting/uploading remains a human portfolio decision on the portal.
2. **Experiment budget spent** (1/1 preregistered MTAS experiment). PRAN needs its own
   preregistration, canaries, two-phase uniqueness, and must beat the holdout bar on
   *identical paired folds* before any slot discussion.
3. **A representation-aware uniqueness policy decision** (human/protocol level) is required
   before *any* future file can be "OK TO SUBMIT": under the current literal wording the
   answer is permanently NO for every conceivable raster, including H33 itself.
4. Free official data that would strengthen the next lanes without new purchases: USGS
   GeoDAWN grids (CC0/public domain), USGS 3DEP 1 m DEM derivatives, DOE GDR #1391
   (CC BY 4.0) — all already mirrored in the restore manifests with hashes.
