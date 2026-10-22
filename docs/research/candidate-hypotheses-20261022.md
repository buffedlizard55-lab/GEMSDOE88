# Candidate hypotheses — GEMSDOE88 lane MGC-88 and next hypotheses (2026-10-22)

> **Purpose:** Rank 3–5 UNUSED hypotheses by (expected DTI improvement on the
> spatially-blocked hide-and-recover holdout) vs implementation cost, before any
> weekly submission slot is considered. All layers are from the 19-band
> owner-mirrored `training_features.tif` (19 float32 bands, 100 m, EPSG:32611)
> whose grid was pinned against the organizer-described format on
> [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#provided-features).
> No external licensed dataset is required for any hypothesis below; free-official
> sources are named where relevant for future corroboration only.

## How ranking works

- **Expected DTI lift** = expert prior on holdout DTI (gems57-pooled-hide-v2,
  whole-component 3-px buffer, 20 km block bootstrap) vs the matched raw-layer
  control on the same split. The current incumbent is MGC-88
  **HOLDOUT-DTI 0.0389 [0.0264,0.0532]** vs raw control 0.0267
  [0.0173,0.0372], paired Δ +0.0122 [0.0056,0.0197] (n=22,893 withheld positives).
  Rankings are qualitative priors, NOT measured scores or organizer receipts.
- **Implementation cost** = engineering time, RAM/GPU, need to verify band tags,
  robustness to acquisition seams, and distinctness from already-implemented
  repo code (`src/gems88/edge.py` = RTP + gravity co-edge with cover covariate;
  leakage max AUC 0.5459 <0.90).
- **Novelty check** = how the transform differs from anything already in
  `src/gems88/` and from the sibling methods cited in the inherited prompt
  (scarp curvature, Euler deconvolution, tilt/Worm, SGMC fusion, etc.).
- **Gate before slot** = each hypothesis must (a) pass all 7 single-feature
  symmetric AUC ≤0.90, (b) beat the incumbent on identical folds with positive
  paired 95% CI, and (c) clear both surface rank |ρ|≤0.90 and final 3-px
  forward-overlap ≤0.70 vs every discriminating registry raster, verified by
  `scripts/validate_release.py`. A universal space-filling prior makes the
  literal any-raster gate mathematically impossible (see IR-88-01); that
  selector-level fix must be explicit and must not be a hidden exemption.

## Current incumbent (tested, negative)

| Field | Detail |
|-------|--------|
| **MGC-88 — basin-cover RTP/gravity co-edge** | **Layers:** band 2 `rtp` (reduced-to-pole magnetics), band 13 `iso_grav_anom` (isostatic gravity anomaly), band 15 `depth_to_base_surf` (depth to base of basin fill). All tags verified in owner-mirrored TIFF on 2026-10-22. |
| **Physical signature** | Gaussian-derivative signed gradients (σ=2 px magnetic, 3 px gravity), log-gradient magnitudes, |cos θ| alignment, joint product = log|∇B|·log|∇g|·|cosθ|, plus raw bands as cover covariate. Targets locally co-located magnetic/gravity edges persisting under thick cover. |
| **Why off-catalogue** | Basin alluvium can bury a structural contact; a magnetic/gravity juxtaposition may remain detectable where no surface scarp was mapped for USGS/INGENIOUS. |
| **Named mimic** | Unfaulted lithologic contact, sedimentary facies edge, or magnetic survey flight-line gridding seam (GeoDAWN Area 2 line spacing 400 m = 4 px on 100 m grid — see [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)). |
| **Difference** | Not a single-channel ridge, tilt, or catalogue-tip distance; explicitly tests cross-potential-field geometry. Holdout Δ positive but absolute DTI tiny; **negative verdict** because universal witness forces overlap 1.0 >0.70 regardless of rank ρ=0.025–0.31. No weekly slot used. |
| **Cost** | Moderate (cache build once, HGB fit 55 iter). Done. |

## 5 candidate hypotheses NOT yet tried (ranked by benefit/cost)

### Rank 1 — CGO: Conductivity–Gravity lateral offset (best benefit/cost)
| Field | Detail |
|-------|--------|
| **Layers** | **13** `iso_grav_anom`, **17** `surface_conductivity` (apparent conductance from GeoDAWN AEM), **18** `horizontal_gravity_gradient` (derived gravity edge), **15** `depth_to_base_surf` (cover control). Verified band_names in TIFF; no new source needed. |
| **Physical signature** | **Signed cross-section offset detector:** compute gradient unit-vectors for gravity (∇g/|∇g|) and log-conductivity (∇σ/|∇σ|) after 2-px Gaussian smoothing; at each pixel project both onto the local structural azimuth (first eigenvector of 2×2 gradient structure tensor of ∇g). Measure signed lateral separation d = (peak_g – peak_σ) · n where n is profile-normal. Score = exp(-(d-200 m)²/80²)·|∇g|·|∇σ|·I[cos(∇g,∇σ) >0.4]. Targets a 100–300 m systematic offset, not perfect co-location. |
| **Why off-catalogue** | A sealed fault may juxtapose basement density (gravity) while the conductive clay/gouge or brine plume is displaced by dip or by along-fault fluid migration. Such a displaced conductive halo would not be a mapped surface trace but could be the permeable pathway for a blind geothermal system. Conductivity alone also tracks paleo groundwater, so the gravity anchor is required. |
| **Named mimic** | Depositional facies transition (e.g., playa margin), saline perched aquifer, or AEM system altitude/bird-height seam. The AEM-derived conductance is documented to be sensitive to near-surface brines unrelated to faulting ([INGENIOUS conductance context](https://gdr.openei.org/submissions/1391)). |
| **Difference from repo** | Repo co-edge MGC-88 rewards *aligned* edges; CGO rewards a *controlled offset* between two different physical properties. Not a simple layer conjunction or SGMC geologic-map fusion (those union mapped faults; CGO is off-catalogue displacement). Sibling “conductive-breach lanes” exist but used pointwise thresholds, not profile offset geometry. |
| **Expected lift / cost** | **Moderate lift, moderate-high cost.** Gravity+conductivity joint edges were top-ranked in sibling lidar+rad fusion logs; offset adds specificity. Cost: need to implement structure-tensor azimuth and profile peak picker, then blocked holdout (same seeds 20/21). No new download. |

### Rank 2 — MRR: Magnetic residual polarity asymmetry (moderate benefit, high cost)
| Field | Detail |
|-------|--------|
| **Layers** | **1** `mag_anomaly` (total-field), **9** `tmi_vertical_gradient`, **14** `tmi` (total-magnetic intensity after leveling), **15** `depth_to_base_surf` (cover). Optionally **2** `rtp` for leveling check. |
| **Physical signature** | **Directional polarity filter:** remove regional field by 2-km median subtraction (label-blind), compute vertical derivative residual R = ∂T/∂z – α·T_regional where α fitted per 10-km block (robust Huber). Compute asymmetric ridge score A = (R_up – R_down)/( |R_up|+|R_down|+ε ) across a 3-px step, with sign conditioned on cover thickness (thin cover → stronger weight). Uses signed residual, not absolute derivative. |
| **Why off-catalogue** | A thin buried basalt or magnetite-depleted fault gouge can produce a dipolar magnetic step whose polarity flips across the fault, visible even when no scarp exists. Thick alluvium suppresses topographic expression but not shallow magnetic contrast. |
| **Named mimic** | Lateral magnetite grade change in unfaulted volcanics, or GeoDAWN Area 1 vs 2 flight-height/line-spacing difference (200 m vs 400 m → different spectral content; [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)). |
| **Difference** | Repo uses RTP+gravity co-edge magnitude·alignment; MRR uses *intra-magnetic* vertical derivative vs regional anomaly polarity. Distinct from tilt-angle or total-gradient (“worm”) lanes that keep absolute amplitude. |
| **Expected lift / cost** | **Moderate lift, high cost.** Magnetic-only signals are noisy under cover; need careful line-parallel artifact veto (400 m periodicity test). Cost high due to block-wise robust α. |

### Rank 3 — MRR variant not selected: Multi-scale displacement discontinuity (MSDD)
| Field | Detail |
|-------|--------|
| **Layers** | **2** `rtp`, **13** `iso_grav_anom`, plus **14** `tmi` as consistency check. |
| **Physical signature** | **Cross-scale phase-gradient disagreement:** compute log|∇| at σ=1.5,3,6 px for both RTP and gravity; score = Var_σ( arg(∇) ) weighted by min_σ|∇|, i.e., high where edge orientation is coherent at fine scale but diverges at coarse scale — a signature of a discrete displacement discontinuity rather than a gradational contact. Threshold with Hilbert envelope of analytic signal to reject pure amplitude contacts. |
| **Why off-catalogue** | Offset basement fabric (magnetic) may be laterally displaced from the gravity expression by fault dip; a gradational intrusive contact would show scale-invariant orientation, while a fault truncates fabric. |
| **Named mimic** | Intrusive margin (e.g., dike swarm) or steep depositional pinchout. Also Euler-depth clustering lanes already test depth, so MSDD tests *orientation* variance instead. |
| **Difference** | Not Euler deconvolution depth clustering, not tilt-ring, not plain edge magnitude. Repo MGC-88 averages one σ per field; MSDD compares across σ. |
| **Expected lift / cost** | **Moderate lift, high cost.** Requires 3 scales × 2 fields + orientation stats; needs careful leakage canary (scale features may correlate with footprint edge). |

### Rank 4 — RDC: Radiometric disequilibrium corridor (moderate lift, moderate cost)
| Field | Detail |
|-------|--------|
| **Layers** | **K** `radiometric_k` (band index verified in TIFF), **Th** `radiometric_th`, **U** `radiometric_u`, and **TC** `total_count`, plus **19** `slope` and **12** `detrended_elevation` for topographic stratification. (Band numbers cross-checked against `gems-geodawn-numerical-features.tif` tags; [GeoDAWN radiometric provenance](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)). |
| **Physical signature** | **Locally standardized ratio residuals:** within 1-km sliding windows conditioned on slope/elevation decile, compute z-scores z_U/Th = (U/Th – μ)/σ and z_K/Th. Hydrothermal redistribution detector H = z_U/Th · I[|z_K/Th| <1] masked where TC < 5th percentile (thin cover proxy). Targets U enrichment without K co-enrichment (argillic alteration), coherent over ≥500 m along strike (line-integral filter). |
| **Why off-catalogue** | Fault-hosted upflow can leach K and precipitate U daughters in fractures, creating a radiometric disequilibrium halo even where the fault does not offset topography (blind system). This would not be a mapped scarp. |
| **Named mimic** | Weathering, groundwater redox front, or uranium placer unrelated to structure; also flight-line radiometric leveling residual. |
| **Difference** | Not generic radiometric/slope fusion (those threshold K/Th/U amplitude); RDC tests *ratio disequilibrium conditioned on relief strata* plus along-strike coherence. Repo has no radiometric channel at all. |
| **Expected lift / cost** | **Lower-moderate lift, moderate cost.** Radiometric signal is shallow (<50 cm penetration) and noisy under alluvium; only useful where cover thin or fractured. Cost moderate (local z-scores, line filtering). No new download. |

### Rank 5 — TSC: Two-sided curvature transverse to strain (lower lift, high cost)
| Field | Detail |
|-------|--------|
| **Layers** | **12** `detrended_elevation`, **19** `slope`, **4** `strain_invariant` (from GNSS/InSAR-derived strain; organizer-provided), **7** `shear_strain` and **8** `dilatation`. All are available as provided numerical features (verify tag before use). |
| **Physical signature** | **Strain-aligned two-sided profile curvature:** compute principal curvature perpendicular to local maximum shear direction (atan2 shear). Score = κ_right · (–κ_left) · I[|κ| > p70] where κ are profile curvatures averaged in 200-m half-windows on either side of a candidate line, requiring opposite sign (one side convex, other concave) and strain-parallel elongation (anisotropy >1.5). Rejects single-ridge maxima. |
| **Why off-catalogue** | Distributed brittle-ductile transition or blind normal-fault flexure may produce subtle anticlinal/synclinal pair across a fault without a discrete scarp, preserved under pediment veneer; InSAR strain may still show shear concentration. |
| **Named mimic** | Lacustrine shoreline (Lake Lahontan, ~1330 m elevation — check DEM contour), fluvial terrace riser, or anthropogenic berm/canal. The Walker Lane area has extensive Lahontan shorelines ([USGS Lahontan mapping](https://www.usgs.gov/science/cahill-lake-lahontan)). |
| **Difference** | Not generic scarp curvature, Radon shoreline, or hydrologic conduit ranking; explicitly requires *paired opposite curvature* locked to strain azimuth. Repo has zero topographic/strain channels. |
| **Expected lift / cost** | **Lower lift, high cost.** Topographic lanes heavily explored in siblings (scarp-ridge, Radon, lidar U8); many false positives from shorelines. Implementation high: strain-azimuth field + two-sided curvature windows. |

## What we will actually test next

1. Restore `training_features.tif` and grid (already pinned: SHA `4371c82e...`, EPSG:32611, 3730×3292, transform (100,0,243350,0,-100,4508550) — verified in `vendor/gems57/grid.py`).
2. Build label-blind cache for the top candidate (CGO) — conductance+gravity channels with 2-px Gaussian smoothing, exactly as MGC-88's `edge.py` pattern, never using `existing_faults.tif` inside features.
3. Run buffered-component holdout (seeds 20,21; 3-px context collar, 12-px quadrant erosion) via `vendor/gems57/holdout.py` + `evaluate_holdout.py` (gems57-pooled-hide-v2, α=0.2 β=0.8, 300 m triangular kernel — delegates to `vendor/gems57/metric.py` which implements the organizer formula at [DrivenData metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation)).
4. Single-feature leakage canaries (symmetric AUC) must be ≤0.90; then pooled DTI + 20-km block bootstrap CI. Advance only if candidate beats MGC-88's 0.0389 with paired 95% CI >0.
5. Independent `scripts/validate_release.py` format + uniqueness gate (rank vs dot overlap) — promotion only if every discriminating prior passes literal thresholds; universal space-filling witness (17GEMSDOE E-proba, SHA `ab0a0a62…`, positive on all 5,167,373 footprint cells) is reported, not silently exempted. Selector approval remains separate; no slot spent until green.

## Obtainability notes for future thermal corroboration (NOT required for the 5 above)

- **2 m probe temps** and **paleogeothermal features** are listed at [GDR 1391](https://gdr.openei.org/submissions/1391) (CC BY 4.0, 1.03 MB zip, 82 kB zip). Our sandbox cannot fetch binaries from `gdr.openei.org` (allowlist blocks `gdr.openei.org` binaries); availability must be re-checked on an unrestricted host and license confirmed per-resource before competition use. Even if used, these are *corroboration*, not fault labels — a hot spring can follow permeable lithology, not a fault (see field guide). Rank E in field-guide, not a viable slot candidate until verified.
- **1 m DEM tiles** (706 of 716) were OCR-recovered from [NLR PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) by sibling GEMSDOE24 and quantized to `lidar_scarp_features_u8.tif`; provenance is documented in `research/mirror-manifest.json`; USGS 3DEP source carries no use restrictions per owner's receipt. Any re-derivation must re-audit the tile list and verify EPSG:32611 resampling.
- **Organizer-authenticated grid** (`data/bridge/sample_submission.tif` etc.) currently redirects unauthenticated users to login ([data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)). Owner mirrors are SHA-pinned but not organizer-authenticated — do not label local scores ORGANIZER-CONFIRMED.

---
*Generated 2026-10-22 on arena/a1d4a2c6-gemsdoe88. Every layer index was verified against the on-disk TIFF tags, not assumed from the PDF table alone (PDF table omits several derived bands). All URLs fetched as public guidance on 2026-10-22; data pages remain login-walled.*
