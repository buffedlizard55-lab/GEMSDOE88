# Candidate hypotheses — GEMSDOE88 lane MGC-88, CGO-88 holdout test, and 19-band audit (2026-10-22)

> **Purpose:** Rank 3–5 geological hypotheses by expected DTI improvement on the
> spatially-blocked hide-and-recover holdout vs implementation cost before any
> weekly submission slot is considered, and validate the top untried candidate
> (**CGO-88**) on the spatially-blocked holdout set.
> Every layer index and `band_name` tag below is verified directly against the
> 19-band on-disk `data/training_features.tif` (`SHA-256: 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`,
> 19 `float32` bands, 100 m, `EPSG:32611`) and recorded in
> [`registry/cgo88_holdout_and_band19_audit.json`](../registry/cgo88_holdout_and_band19_audit.json).

## How ranking and validation work

- **Holdout protocol (`gems57-pooled-hide-v2`):** whole 8-connected fault components
  withheld in 4 eroded quadrants across 2 deterministic seed draws (`seeds=(20, 21)`,
  `22,893` withheld positive pixels), 3-px feature-context collar, 12-px quadrant
  boundary erosion, visible-only training outside the test quadrant, pixel-exact
  masking of visible faults, pooled DTI ($\alpha=0.2$, $\beta=0.8$, 300 m triangular
  kernel), and 1,000-draw paired 20 km spatial-block bootstrap 95% CIs
  ([DrivenData metric specification](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation)).
- **Current holdout best (incumbent `MGC-88`, Experiment 1 of 3):**
  **HOLDOUT-DTI `0.0389 [0.0264, 0.0532]`** (`gems57-pooled-hide-v2`, `n=22,893`
  withheld positives) vs matched raw-layer control **HOLDOUT-DTI `0.0267 [0.0173, 0.0372]`**,
  paired $\Delta = +0.0122\ [0.0056, 0.0197]$.
- **Top candidate tested in Experiment 2 of 3 (`CGO-88`):**
  - Pure `CGO-88` (`iso_grav_anom`, `depth_to_base_surf`, `cond_surf`, `iso_grav_anom_hg`, `log_gravity_edge`, `log_cond_edge`, `cgo_offset_200m`, `cgo_signed_asym`):
    **HOLDOUT-DTI `0.0227 [0.0154, 0.0309]`** (`gems57-pooled-hide-v2`, `n=22,893`),
    paired $\Delta$ vs `MGC-88` = **`-0.0162 [-0.0281, -0.0073]`**.
  - Joint `MGC-88 + CGO-88` (all 12 channels):
    **HOLDOUT-DTI `0.0230 [0.0162, 0.0308]`** (`gems57-pooled-hide-v2`, `n=22,893`),
    paired $\Delta$ vs `MGC-88` = **`-0.0158 [-0.0286, -0.0061]`**.
  - **Outcome:** `CGO-88` is **falsified on the spatially-blocked holdout** and does
    not beat the current holdout best (`MGC-88` `0.0389`). Per the protocol rule
    (*"do not spend a submission slot on an idea that hasn't beaten the current holdout best"*),
    `CGO-88` is rejected and `MGC-88` remains the unbeaten holdout incumbent (still
    blocked from competition upload by the 100% literal overlap with the universal
    positive-footprint witness `dense_17gemdoe.tif`, `IR-88-01`).

## Complete 19-band on-disk verification and single-feature leakage canaries

All 19 bands in `data/training_features.tif` were read on disk (`scripts/evaluate_cgo88.py`).
Notice two critical facts verified directly from the GeoTIFF metadata (`IR-88-07`):
1. The exact `band_name` tags are `mag_anom`, `rtp`, `tmi_hg`, `geod_2ndinv`,
   `iso_grav_anom_slope`, `tc`, `geod_shearrate`, `geod_dilaterate`, `tmi_vg`,
   `deq_n100a15`, `iso_grav_anom_vg`, `det_elev`, `iso_grav_anom`, `tmi`,
   `depth_to_base_surf`, `ieq_n100a15`, `cond_surf`, `iso_grav_anom_hg`, and
   `det_elev_slope`.
2. The 19-band `training_features.tif` contains **zero** radiometric K, Th, or U
   bands, and Band 6 (`tc`) carries the embedded TIFF description
   `tc - Tilt angle or total curvature - magnetic field derivative for edge detection`
   (not radiometric total count). Radiometric K/Th/U/TC grids belong to the external
   [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
   (DOI `10.5066/P93LGLVQ`, CC0; mirrored in `GEMSDOE24` as `data/external/geodawn_rad_u8.tif`).

| Band | Verified `band_name` tag | Embedded TIFF description | p01 | p50 | p99 | Holdout symmetric AUC |
|---:|---|---|---:|---:|---:|---:|
| 1 | `mag_anom` | Magnetic anomaly - deviation from expected Earth's magnetic field | -288.82 | -57.66 | 312.24 | 0.5069 |
| 2 | `rtp` | Reduced to pole magnetic data - magnetic anomaly corrected for latitude effects | -460.46 | -137.28 | 394.57 | 0.5224 |
| 3 | `tmi_hg` | Total magnetic intensity horizontal gradient - rate of change in horizontal direction | 0.66 | 13.15 | 188.49 | 0.5162 |
| 4 | `geod_2ndinv` | Geodetic second invariant - measure of strain rate tensor magnitude | 1.75 | 19.96 | 57.79 | 0.5028 |
| 5 | `iso_grav_anom_slope` | Isostatic gravity anomaly slope - gradient of gravity after isostatic correction | 0.0158 | 0.1023 | 0.3671 | 0.5425 |
| 6 | `tc` | Tilt angle or total curvature - magnetic field derivative for edge detection | 7.71 | 18.48 | 29.03 | 0.5608 |
| 7 | `geod_shearrate` | Geodetic shear rate - rate of angular deformation from GPS/InSAR | 0.00 | 9.70 | 38.50 | 0.5051 |
| 8 | `geod_dilaterate` | Geodetic dilatation rate - rate of volumetric strain (expansion/contraction) | -9.60 | 5.50 | 27.00 | 0.5241 |
| 9 | `tmi_vg` | Total magnetic intensity vertical gradient - rate of change in vertical direction | -0.688 | -0.0088 | 0.785 | 0.5130 |
| 10 | `deq_n100a15` | Distance to earthquake (n=100km radius, a=15° azimuth parameters) | 118.30 | 623.00 | 50237.20 | 0.5124 |
| 11 | `iso_grav_anom_vg` | Isostatic gravity anomaly vertical gradient - vertical rate of change | -4.32 | -0.073 | 4.23 | 0.5084 |
| 12 | `det_elev` | Detrended elevation - topography with regional trends removed | -466.17 | -75.49 | 707.18 | 0.5127 |
| 13 | `iso_grav_anom` | Isostatic gravity anomaly - gravity after compensating for topographic mass | -32.79 | -7.28 | 12.87 | 0.5127 |
| 14 | `tmi` | Total magnetic intensity - total strength of magnetic field | -427.64 | -124.77 | 354.02 | 0.5051 |
| 15 | `depth_to_base_surf` | Depth to basement surface - thickness of sedimentary cover | 1.22 | 315.89 | 3403.74 | 0.5131 |
| 16 | `ieq_n100a15` | Earthquake intensity or density (n=100km radius, a=15° parameters) | 263.90 | 755.80 | 5091.36 | 0.5064 |
| 17 | `cond_surf` | Conductivity surface - electrical conductivity of subsurface | 1.17 | 2.89 | 4.49 | 0.5038 |
| 18 | `iso_grav_anom_hg` | Isostatic gravity anomaly horizontal gradient - horizontal rate of change | -5.18 | 0.035 | 5.40 | 0.5180 |
| 19 | `det_elev_slope` | Detrended elevation slope - gradient of elevation after detrending | 0.069 | 3.73 | 32.82 | 0.5642 |

All 19 single-band symmetric AUCs are $\le 0.5642$ (well below the $0.90$ leakage canary limit).

## Current incumbent (Experiment 1 of 3 — tested, unbeaten on holdout, blocked by registry witness)

| Field | Detail |
|-------|--------|
| **MGC-88 — basin-cover RTP/gravity co-edge** | **Layers:** Band 2 `rtp`, Band 13 `iso_grav_anom`, Band 15 `depth_to_base_surf`. |
| **Physical signature** | Footprint-weighted Gaussian-derivative signed gradients ($\sigma=2\text{ px}$ magnetic, $3\text{ px}$ gravity), $\log(1+|\nabla|)$ magnitudes, $|\cos \theta|$ alignment, and joint co-edge product $\log(1+|\nabla B|)\cdot\log(1+|\nabla g|)\cdot|\cos\theta|$, conditioned on `depth_to_base_surf`. |
| **Why off-catalogue** | Basin alluvium buries surface fault scarps while preserving subsurface density and magnetization juxtapositions across basement-involved faults. |
| **Named mimic** | Unfaulted lithologic contact, sedimentary facies boundary, or magnetic survey flight-line gridding seam (GeoDAWN Area 2 spacing $400\text{ m} = 4\text{ px}$ on 100 m grid — [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)). |
| **Holdout & gate status** | **HOLDOUT-DTI `0.0389 [0.0264, 0.0532]`** vs raw control **`0.0267 [0.0173, 0.0372]`**, paired $\Delta = +0.0122\ [0.0056, 0.0197]$ (`gems57-pooled-hide-v2`, `n=22,893`). Max canary symmetric AUC `0.5459 <= 0.90`. Verdict: **negative** (`DO NOT SUBMIT`) because the universal positive-footprint witness (`dense_17gemdoe.tif`, `SHA-256: ab0a0a62...`) forces 3-px forward dot overlap = `1.0000 > 0.70`. |

## 5 candidate geological hypotheses ranked by expected DTI lift vs implementation cost

### Rank 1 — CGO-88: Conductivity–Gravity 200 m lateral offset (tested in Experiment 2 of 3 — falsified on holdout)
| Field | Detail |
|-------|--------|
| **Layers** | **Band 13** `iso_grav_anom`, **Band 17** `cond_surf`, **Band 18** `iso_grav_anom_hg`, **Band 15** `depth_to_base_surf` (plus **Band 2** `rtp` in the joint ablation). All tags verified on disk in `data/training_features.tif`. |
| **Physical signature** | **Cross-strike 200 m offset co-edge (`cgo_offset_200m`, `cgo_signed_asym`):** compute footprint-weighted Gaussian gradients $\mathbf{g} = \nabla G_{\sigma=3}(\text{iso\_grav\_anom})$ and $\mathbf{c} = \nabla G_{\sigma=2}(\text{cond\_surf})$ with unit normals $\hat{\mathbf{n}}_g, \hat{\mathbf{n}}_c$. Step $\pm 2\text{ px}$ ($\pm 200\text{ m}$) perpendicular to gravity strike along $\pm\hat{\mathbf{n}}_g$, evaluate strike-aligned conductivity edge $\log(1+|\mathbf{c}(\mathbf{x}\pm 2\hat{\mathbf{n}}_g)|)\cdot|\hat{\mathbf{n}}_g(\mathbf{x})\cdot\hat{\mathbf{n}}_c(\mathbf{x}\pm 2\hat{\mathbf{n}}_g)|$, multiply by $\log(1+|\mathbf{g}(\mathbf{x})|)$, and record both maximum offset response and hanging-wall/footwall signed asymmetry. |
| **Why off-catalogue** | A dipping concealed fault zone can displace the conductive clay gouge or geothermal brine plume $100\text{--}300\text{ m}$ down-dip from the footwall basement gravity step, creating an off-catalogue fluid conduit without a surface scarp. |
| **Named mimic** | Playa margin / evaporite facies transition, perched saline groundwater aquifer, or AEM bird-height/processing seam ([DOE GDR 1391 INGENIOUS context](https://gdr.openei.org/submissions/1391)). |
| **Difference from repo** | `MGC-88` tests zero-offset magnetic/gravity co-location; `CGO-88` tests a $200\text{ m}$ cross-strike lateral offset between gravity (`iso_grav_anom`) and electrical conductivity (`cond_surf`). |
| **Blocked holdout result** | **Tested (`scripts/evaluate_cgo88.py`, [`registry/cgo88_holdout_and_band19_audit.json`](../registry/cgo88_holdout_and_band19_audit.json)):** All 12 leakage canaries passed ($\max \text{AUC}_{\text{sym}} = 0.5459 \le 0.90$; `cgo_offset_200m` $\text{AUC}_{\text{sym}} = 0.5114$, `cgo_signed_asym` $= 0.5017$). Pure `CGO-88` scored **HOLDOUT-DTI `0.0227 [0.0154, 0.0309]`** and joint `MGC-88 + CGO-88` scored **HOLDOUT-DTI `0.0230 [0.0162, 0.0308]`** (`gems57-pooled-hide-v2`, `n=22,893`), both significantly below `MGC-88` **`0.0389 [0.0264, 0.0532]`** (paired $\Delta = -0.0162\ [-0.0281, -0.0073]$ pure; $-0.0158\ [-0.0286, -0.0061]$ joint). Because `cond_surf` reflects broad playa/basin salinity ($\text{AUC}_{\text{sym}} = 0.5038$), tree splits overfit regional basin conductance across quadrants. **Verdict: negative / rejected on holdout.** |

### Rank 2 — MRR: Magnetic residual & tilt-curvature polarity asymmetry (moderate benefit, high cost, unrun)
| Field | Detail |
|-------|--------|
| **Layers** | **Band 1** `mag_anom`, **Band 3** `tmi_hg`, **Band 6** `tc` (magnetic tilt angle / total curvature), **Band 9** `tmi_vg`, **Band 14** `tmi`, **Band 15** `depth_to_base_surf`. Verified in `data/training_features.tif`; no external source required. |
| **Physical signature** | **Directional polarity & tilt-curvature step filter:** remove 2 km regional median from `mag_anom` (label-blind), compute vertical-gradient residual $R = \text{tmi\_vg} - \alpha\cdot T_{\text{reg}}$, and measure across-strike signed step asymmetry $(R_{+3\text{px}} - R_{-3\text{px}})/(|R_{+3\text{px}}|+|R_{-3\text{px}}|+\epsilon)$ gated by magnetic tilt/curvature `tc` (`Band 6`, $\text{AUC}_{\text{sym}} = 0.5608$) and `depth_to_base_surf`. |
| **Why off-catalogue** | Magnetite destruction by hydrothermal alteration along a buried fault or a thin displaced volcanic horizon creates an asymmetric dipolar magnetic step and `tc` break even where alluvial fans erase surface scarps. |
| **Named mimic** | Unfaulted volcanic flow margin, remanent magnetization reversal, or GeoDAWN Area 1 vs Area 2 flight-line spacing transition ($200\text{ m}$ vs $400\text{ m}$ — [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)). |
| **Difference from repo** | Uses intra-magnetic vertical/horizontal gradient asymmetry and Band 6 `tc` rather than `MGC-88`'s single-scale RTP/gravity co-edge or `CGO-88`'s conductivity offset. |

### Rank 3 — MSDD: Multi-scale gravity/magnetic displacement discontinuity (moderate benefit, high cost, unrun)
| Field | Detail |
|-------|--------|
| **Layers** | **Band 2** `rtp`, **Band 5** `iso_grav_anom_slope` ($\text{AUC}_{\text{sym}} = 0.5425$), **Band 11** `iso_grav_anom_vg`, **Band 13** `iso_grav_anom`, **Band 18** `iso_grav_anom_hg`. Verified in `data/training_features.tif`. |
| **Physical signature** | **Cross-scale gradient orientation variance:** compute $\nabla G_\sigma$ at $\sigma \in \{1.5, 3.0, 6.0\}\text{ px}$ for both `rtp` and `iso_grav_anom`, weighting circular variance of gradient azimuth across scales by $\min_\sigma \log(1+|\nabla|)$ and `iso_grav_anom_slope`. |
| **Why off-catalogue** | Discrete brittle fault truncation produces scale-dependent azimuth twisting at stepovers and terminations, whereas gradational intrusive contacts maintain scale-invariant orientation. |
| **Named mimic** | Intrusive dike margin or steep paleo-erosional buttress unconformity. |
| **Difference from repo** | Tests multi-scale orientation variance across $\sigma \in \{1.5, 3, 6\}\text{ px}$ rather than `MGC-88`'s fixed single-scale ($\sigma=2,3\text{ px}$) cosine alignment. |

### Rank 4 — TSC: Strain-locked two-sided topographic slope/curvature break (lower-moderate benefit, high cost, unrun)
| Field | Detail |
|-------|--------|
| **Layers** | **Band 12** `det_elev`, **Band 19** `det_elev_slope` ($\text{AUC}_{\text{sym}} = 0.5642$, highest of all 19 bands), **Band 4** `geod_2ndinv`, **Band 7** `geod_shearrate`, **Band 8** `geod_dilaterate`. Verified in `data/training_features.tif`. |
| **Physical signature** | **Strain-conditioned inflection pair:** compute directional second derivative of `det_elev` normal to `det_elev_slope` ridges, requiring opposite-signed profile curvature across a $200\text{ m}$ step weighted by geodetic dilatation/shear (`geod_dilaterate` $\text{AUC}_{\text{sym}} = 0.5241$, `geod_shearrate`, `geod_2ndinv`). |
| **Why off-catalogue** | Active distributed transtension/normal faulting across piedmont slopes produces subtle paired convex/concavescarps aligned with geodetic strain rate that were missed where discrete surface rupture traces were not mapped. |
| **Named mimic** | Pleistocene Lake Lahontan shoreline terraces, fluvial terrace risers, or road/canal embankments. |
| **Difference from repo** | `MGC-88` and `CGO-88` use zero topographic or geodetic strain bands; `TSC` couples `det_elev` / `det_elev_slope` inflection geometry with GPS/InSAR strain invariants (`geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`). |

### Rank 5 — RDC: External GeoDAWN radiometric disequilibrium corridor (external-data dependent, unrun)
| Field | Detail |
|-------|--------|
| **Layers & external source** | Requires external [USGS GeoDAWN radiometric grids](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) (K, Th, U, TC; DOI `10.5066/P93LGLVQ`, CC0; owner-mirrored in `GEMSDOE24` as `data/external/geodawn_rad_u8.tif`, `SHA-256: c22420f75999030d7cc65c9e31e50d232ea6158423bca051613a18a8b20ba682` — see [`research/mirror-manifest.json`](mirror-manifest.json)) combined with provided **Band 12** `det_elev` and **Band 19** `det_elev_slope`. **Not present inside the 19-band `training_features.tif` (`IR-88-07`).** |
| **Physical signature** | **Relief-stratified U/Th and K/Th ratio residuals:** within 1 km windows stratified by `det_elev` and `det_elev_slope` deciles, compute standardized $z_{\text{U/Th}}$ and $z_{\text{K/Th}}$ residuals to isolate linear hydrothermal alteration corridors along fractures. |
| **Why off-catalogue** | Epithermal fluid upflow and argillic alteration can leach K or enrich U along fracture zones lacking a topographic scarp. |
| **Named mimic** |Felsic volcanic tuff outcrops, playa evaporite/uranium placers, or flight-line radiometric leveling seams. |
| **Difference & obtainability** | Uses external CC0 USGS GeoDAWN radiometric channels rather than the 19 provided bands; ranked 5th because radiometric gamma-ray penetration is $<50\text{ cm}$ and requires external raster ingestion. |

## Summary of experimental budget and next steps

1. **Experiment 1 (`MGC-88`):** **HOLDOUT-DTI `0.0389 [0.0264, 0.0532]`** vs raw control **`0.0267 [0.0173, 0.0372]`** (`gems57-pooled-hide-v2`, `n=22,893`). Remains the unbeaten holdout best in this repository.
2. **Experiment 2 (`CGO-88`):** **HOLDOUT-DTI `0.0227 [0.0154, 0.0309]`** (pure) and **`0.0230 [0.0162, 0.0308]`** (joint with `MGC-88`), failing to beat `MGC-88` (paired $\Delta = -0.0162\ [-0.0281, -0.0073]$ pure; $-0.0158\ [-0.0286, -0.0061]$ joint). Rejected on holdout; no new submission artifact promoted.
3. **Remaining budget:** 1 experiment remaining (`experiment_budget_used_total = 2` of `3`). Any future session must first resolve the protocol-level universal positive-footprint witness (`dense_17gemdoe.tif`, `IR-88-01`) with explicit selector authorization before any nonempty candidate can pass the literal 3-px / 70% registry overlap gate.
