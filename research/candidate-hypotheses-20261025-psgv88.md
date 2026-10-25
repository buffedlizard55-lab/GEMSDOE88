# GEMSDOE88 — 2026-10-25 session: why H33 (0.2778, owner-reported) leads, and the H88-PSGV lane

Branch `arena/ea90f040-gemsdoe88` · Preregistration `registry/preregistration_psgv88.json` (frozen before any new canary/holdout/production computation).
Evidence tags: **[ONLINE]** read this session · **[DISK]** measured from SHA-pinned files in this repo · **[OWNER]** owner-reported, no organizer receipt in repo · **[INFERENCE]** derived under stated assumption.

## 1. PhD forensic answer: why/how did `h33-h33-2-b2` reach 0.2778, and can it be beaten?

### What is verified

- **Live leaderboard (this session, 2026-10-25): #1 = 0.4413** (`xiaofanhu`, 29 submissions), #5 (Round-1 top-5 cut) = **0.3539**, ranks 6–20 plateau at 0.327–0.342. **[ONLINE]** https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ — the prompt's `0.3195` figure is stale; `0.4413` is confirmed live. H33's 0.2778 would sit **below rank 50** (stored snapshot #50 = 0.2818, `docs/data/leaderboard.json`). **[DISK]**
- **0.2778 is [OWNER], not ORGANIZER-CONFIRMED.** No DrivenData receipt for H33 exists in this repository; the sandbox has no competition-account access. Every fleet score in the prompt table carries the same status unless a receipt is pasted. Numbers below therefore explain the *reported ordering*, not a certified organizer score.
- **Metric (verified in code):** pooled distance-weighted Tversky, `DTI = TP_w/(TP_w + 0.2·FP_w + 0.8·FN_w)`, triangular kernel `k(d)=max(1−d/3px,0)` (300 m at 100 m/px), known-fault pixels masked. **[DISK]** `vendor/gems57/metric.py` (SHA-pinned template, brute-force-tested); competition spec https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ ; Tversky index https://en.wikipedia.org/wiki/Tversky_index .
- **H33 is a pure subtraction.** H33 (37,654 dots) ⊂ SOLO-D2.8 (40,199) ⊂ D2.8 (44,090) ⊂ H19-5 (121,131 dots); no step adds a dot. All 6,436 dots removed after D2.8 lie within 2 px of the catalogue; H33's minimum catalogue distance is 2.236 px, median 19.6 px, 41.7% beyond 25 px. Nearest-neighbour spacing: min 2.83 px, median 3.0 px. **[DISK]** `scripts/forensics_h33.py` → `evidence/h33_forensics_20261024.json`, dossier `research/h33-forensics-20261024.md`.

### The mechanism (algebra, checkable line by line)

For a binary dot set: `T = Σ_truth max_dot k` (a **max** per truth pixel — redundant neighbouring dots add ≈0), `M = Σ_dots max_truth k`, `FP_w = n − M`, so `DTI = T / (0.8|G| + 0.2(T + n − M))` (`vendor/gems57/metric.py`). Removing one dot with marginal truth credit `dT` and self-credit `q` changes the denominator by `−0.2(dT + 1 − q)` and the numerator by `−dT`; the removal **raises** DTI iff `dT < 0.2·DTI·(dT + 1 − q)`. For a pure false positive (`dT=q=0`) removal *always* helps (denominator −0.2). Break-even for a non-redundant dot at DTI 0.2778 is `k = 0.2×0.2778 = 0.0556`.

Reported chain: H19-5 0.1922 → D1.5 0.2477 → D2.8 0.2600 → SOLO 0.2708 → **H33 0.2778** **[OWNER]**. Because every step only deletes dots, each gain is attributable to the deleted dots being below the bar above. Under the pure-FP assumption the two collar steps independently imply `T ≈ 5.1–5.5k` and public truth `|G| ≈ 13–15k` px (agreement within 8%): H33 captures ≈36% of available credit at ≈0.14 mean value per dot — i.e. H33 is limited by **precision** (~10–15% of dots earn credit) as much as by recall. **[INFERENCE]** `evidence/h33_forensics_20261024.json:lineage_arithmetic_INFERENCE`.

Corroborating fleet fingerprint: across 20 on-disk rasters with owner-reported scores, the share of dots >25 px from the catalogue correlates with reported score at Spearman **+0.90**; catalogue-huggers collapse (median 2.2 px → 0.0041). H33 is not far-biased (footprint baseline 47.2% beyond 25 px vs H33 41.7%) — it simply **does not hug**. This is a necessary screen, not a selector (random dots with H33's distance profile also pass it). **[DISK]** `evidence/fleet_distance_prior_20261024.json`.

### Can 0.2778 be beaten? What would it take?

At fixed dot count, reaching the top-5 cut (0.3539) needs **+27–29% more truth credit T**; reaching #1 (0.4413) needs **+59–63%**. **[INFERENCE]** (same arithmetic as above). Continuing H33-style subtraction (wider collars) is the only lever with controlled lineage support and is expected to be small; every independent surface in the 92-site fleet tops out at 0.23–0.28 **[OWNER]**. Hide-and-recover HOLDOUT-DTI does **not** rank-order public scores in the top regime (fixed H33 scores 0.0039 on the holdout by construction, `docs/data/literal_protocol_audit.json`), so **no submission slot should be spent on holdout evidence alone** — the holdout is used here only as a leakage/regression discipline, exactly as the parallel-run protocol requires. Honest probability statement: P(new unique raster > 0.2778 public) is low and not estimable from available instruments; P(> 0.3539) is lower. The rational play under *Maximize P(Win)* is to (a) keep H33's three proven geometric properties (kernel-spaced lattice, >2 px collar, non-hugging distance profile with ≥35% beyond 25 px), and (b) add a physically independent measurement that can raise per-dot credit in covered basins — which is what the lane below tests, with a pre-registered kill rule.

## 2. Five untried candidate hypotheses (ranked by expected DTI gain ÷ cost)

All five were checked against `src/gems88/`, `scripts/`, `vendor/gems57/` and prior dossiers by text search this session; "untried" means no legitimate implementation exists in this repo (queued/reserve mentions are noted).

| Rank | ID | Layers | Physical signature | Why it catches catalogue-missing faults | Difference from repo | Mimic | Cost |
|---|---|---|---|---|---|---|---|
| **1 (SELECTED)** | **H88-PSGV** | `training_features.tif` B02 `rtp`, B13 `iso_grav_anom`, B15 `depth_to_base_surf` | FFT Baranov pseudogravity `ĝ_psg=Ĥ_hp·RTP̂/|k|`; gravity-on-pseudogravity regression residual + tilt-phase dislocation `|sin Δtilt|` | Hydrothermal magnetite destruction kills the magnetic contrast but not the basement density offset → discordance ridge under unscarped valley fill | `phase88.py` used spatial cross-gradients; XGCE used ∇grav×∇mag; GTHC used upward-continued amplitude. None computes the Poisson-integrated field. PR #68 "MAG-PSG" was quarantined random stripes (no FFT). | Reversely magnetized basalt (Q>1), non-magnetic sediment density contrasts | Low–Med (one padded rFFT pair; on-disk inputs only) |
| 2 | H88-BCSF | `trace_segments_utm11.csv` (fold-visible only), B07/B08 strain, B04 2nd invariant | Okada elastic half-space Coulomb stress-change lobes (ΔCFS) off visible segment tips/stepovers | Relay/stepover splays nucleate in predictable ΔCFS lobes before a through-going scarp exists | Reserve in HGVC prereg, never run; all repo structural features are geometric (distance/strike), none elastic | Aseismic creep segments with stress shadows | Med |
| 3 | H88-SPI | B02 `rtp`, B14 `tmi`, B03/B09 gradients | Source Parameter Imaging: local-wavenumber depth `z=1/k_local` from analytic-signal derivatives; lateral depth-gradient ridges | A blind fault juxtaposes magnetic basement at two depths; depth step persists under cover with weak amplitude edge | Fleet Euler deconvolution (GEMSDOE40, 0.035–0.098 [OWNER]) solves a different (windowed least-squares) problem; no SPI in repo | Dipping dike with along-strike depth change | Low |
| 4 | H88-RADM-CLR | `geodawn_rad_u8.tif` (U/Th/K/TC), B12 `det_elev`, B19 slope | Compositional log-ratio (clr) radiometric residuals after terrain regression + directional crest | K-metasomatism / U-mobility halos (200–500 m) mark upflow without a scarp | `physics.py` has one raw `rad_k_over_th` ratio; XGCE queued RADM unrun; no clr/directional implementation | Felsic tuff outwash, granitic wash | Low |
| 5 | H88-FANSCALE | `topo_10m_derived_100m_u8.tif`, `dem10_chi_100m_*`, B12 | Alluvial-fan slope–contributing-area scaling break (fan-head trenching exponent change) | Active piedmont uplift steepens fan heads systematically across many small catchments; no single scarp needed | Shore-hinge/TDKL used shoreline/knickpoint geometry, not fan scaling laws | Climate-driven (pluvial–interpluvial) fan entrenchment | Med–High |

**Rejected as non-viable here (named source checked):** pre-dawn thermal-infrared seepage (NASA ECOSTRESS / Landsat Collection 2 Surface Temperature, https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature) — free and official, but requires Earthdata/USGS login and hosts outside this sandbox's outbound allowlist (`github.com`, `pypi.org`, `registry.npmjs.org` only for bash). It is therefore **not** proposed as viable in this session, per protocol. InSAR coherence (Copernicus Sentinel-1 via ASF) fails for the same reason.

## 3. Validation contract (top candidate, pre-registered)

- Canary first: every feature alone (PHYS-44 + HGVC-20 + PSGV-8 + VIS-23 = 95) vs withheld positives; symmetric AUC > 0.90 ⇒ leakage stop.
- Holdout: unmodified `gems57-pooled-hide-v2` (whole-component hide, 3 px buffer, 12 px boundary, seeds 20+21, 8 folds, n=22,893), catalogue features from visible faults only, visible faults masked pixel-exactly, pooled DTI (α=0.2, β=0.8, 300 m triangular).
- Kill rule: candidate must exceed the stored HGVC record **HOLDOUT-DTI 0.202947 [0.185869, 0.219790]** (`registry/hgvc88_run_card.json`) to be selector-eligible; otherwise `verdict=negative`, research-only TIFF. Budget: 3 experiments, 0 slots spent by the agent in all cases; promotion remains a separate human selector step.
- Uniqueness: pre-placement surface Spearman and final-dot 3 px overlap vs the full restored registry (`registry_paths.registry_list`), reporting **both** literal (>0 support) and like-for-like (top-N effective dots for dense continuous surfaces) numbers. The 17GEMSDOE space-filling witness (`data/registry/dense_17gemdoe.tif`, SHA `ab0a0a62…`, positive on all 5,106,385 allowed cells) forces literal overlap 1.0 for *every* nonempty raster including random dots (vacuity witness in `evidence/hgvc88_uniqueness.json`); this defect in the shared support definition is flagged as an irregularity rather than silently exempted — see run card for the binding decision under gate v3 / IR-88-86.

## Official sources (manual review)

- Competition + leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/ · https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ · format/metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Rules PDF (NLR 96647): https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution (pinned commit `aebe92f7`, verified this session): https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and · INGENIOUS: https://gbcge.org/current-projects/ingenious/ · GDR #1391: https://gdr.openei.org/submissions/1391
- CRS EPSG:32611: https://epsg.io/32611 · Baranov (1957) pseudogravity: https://doi.org/10.1190/1.1438369
- H33 source site: https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html (score [OWNER], see §1)

## 4. Results (executed 2026-10-25, 3/3 experiments, 0 slots spent) — NEGATIVE

Instrument reproduction first: in-run controls match the stored HGVC run **exactly** (`phys44_zero_cat` HOLDOUT-DTI 0.104163; `h88_adhr_incumbent` 0.194876, per-fold identical to 6 dp), so the PSGV contrast is measured on a verified instrument. Canary: **95/95 features ≤ 0.90** (max `d2` 0.770155; PSGV-8 max 0.543734) — no leakage. Global gravity-on-pseudogravity slope = 0.1359 (standardized fields).

| Arm (HOLDOUT-DTI, `gems57-pooled-hide-v2`, n=22,893) | PSGV lane | Stored HGVC equivalent | Δ |
|---|---:|---:|---:|
| Exp01 zero-catalogue specialist | 0.114842 [0.101544, 0.128215] | 0.113767 | +0.001075 |
| Exp02 single joint | 0.198172 [0.180907, 0.215551] | 0.197582 | +0.000590 |
| **Exp03 PoE candidate** | **0.202494 [0.185513, 0.219885]** | **0.202947 [0.185869, 0.219790]** | **−0.000453** |
| Exp03 far >10 px (n=10,791) | 0.127990 [0.108923, 0.148425] | 0.132800 | −0.004810 |
| Exp03 blind >25 px (n=3,117) | 0.070697 [0.040274, 0.107570] | 0.078959 | −0.008262 |

Paired vs in-run ADHR: **+0.007618 [0.002942, 0.011997], 8/8 folds won** (HGVC margin was +0.008071). Per-fold vs stored HGVC Exp03: 3/8 folds won. **Kill rule triggered:** 0.202494 does not exceed 0.202947 → `verdict=negative`; no retuning (budget exhausted exactly as pre-registered). Interpretation: pseudogravity discordance is ≈neutral overall and mildly harmful in the far/blind strata it was designed to help — on the catalogue-recovery holdout, demagnetization discordance carries no information beyond the HGVC stack. (The holdout under-represents truly blind demagnetized faults by construction; that speculation is explicitly **not** used to promote.)

Production (strict OOF, 37,654 dots, SHA-256 `c38f17fc924ec1fed1efa55b2819d70e911d4416f88a796d7dd50d9c8e3f21e3`): portal format PASS (all 12,279,160 cells finite in {0,1}, `nodata=None`, 0 on catalogue, 0 outside footprint; fingerprint `share_le2=0`, `share_gt25=0.4290`, median 19.21 px). Uniqueness (241 pinned registry rasters, 136 distinct dot sets): pre-placement surface max |ρ| = 0.227641 ≤ 0.90, **but final-dot forward 3-px overlap vs H88-HGVC = 0.7976 > 0.70** (independently recomputed by EDT: 0.797551; vs H33 0.4420, vs TDKL 0.3886) — the candidate **drifted into the HGVC lane** (protocol #1 duplicate stop, a genuine sparse blocker independent of the dense-witness issue). Literal overlap vs the continuous 17GEMSDOE witness = 1.0000 (vacuity witness: random dots also 1.0000; like-for-like 0.0190). Machine verdict: **OK TO DOWNLOAD: YES · OK TO SUBMIT: NO — DO NOT SUBMIT** (`scripts/validate_psgv88.py` exit 0; `--require-submit` exit 2). ORGANIZER-CONFIRMED score: none. Live leaderboard re-read 2026-10-25: #1 0.4413, #5 0.3539.

Known inherited property (not a PSGV defect): two-stratum allocation permits 1-px nearest neighbours across the 25-px stratum boundary (HGVC production has the identical minimum; medians 4.0 vs 4.12 px). Production OOF first attempt was OOM-killed (exit 137) on the 3.8 GiB sandbox and completed on cached rerun; no numbers changed (holdout loaded from saved evidence).
