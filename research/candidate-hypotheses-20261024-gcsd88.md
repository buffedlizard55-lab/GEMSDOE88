# GEMSDOE88 PhD Geological Dossier & Holdout Validation Report — `H88-GCSD` (`2026-10-24`)

**Preregistration ID:** `PREREG-20261024-GCSD88` (`registry/preregistration_gcsd88.json`)  
**Evaluator:** `gems57-pooled-hide-v2` (`vendor/gems57/evaluate_holdout.py`, unmodified, $\alpha = 0.2, \beta = 0.8$, $300\text{ m}$ triangular kernel, seeds `20+21`, `8` outer spatial folds, `n = 22,893` withheld positive pixels)  
**Primary Result (`H88-GCSD`):** **`HOLDOUT-DTI = 0.201610`** (`95% CI [0.184052, 0.218447]`, `n = 22,893`) — **#1 all-time in `GEMSDOE88`**, beating `H88-VESS` (`0.200941`), `H88-MVRD` (`0.197314`), `H88-TDKL` (`0.196237`), `H88-SAR-CSD` (`0.192936`), `H88-QTSK` (`0.192759`), `H88-GTHC` (`0.190971`), and `H88-ADHR` (`0.187888` / `0.190436` / `0.194876`).  
**Far-Field Recovery (`d_vis > 10 px`, `n = 10,791`):** **`HOLDOUT-DTI = 0.134220`** (`95% CI [0.113711, 0.155764]`) — **#1 all-time in `GEMSDOE88`**.  
**Blind-Basin Recovery (`d_vis > 25 px`, `n = 3,117`):** **`HOLDOUT-DTI = 0.089196`** (`95% CI [0.057226, 0.127536]`).  
**Paired Improvement vs Same-Run `H88-ADHR` (`0.194876`):** **`+0.006734`** (`95% CI [+0.001337, +0.011897]`, strictly positive `95% CI` excluding zero; `+0.013722` vs B14 `H88-ADHR` `0.187888`; `+0.011174` vs stored `H88-ADHR` `0.190436`; `+0.005373` vs `H88-TDKL` `0.196237`; `+0.000669` vs `H88-VESS` `0.200941`).  
**Like-for-Like Uniqueness (`<= 250k` dots across 270 registry/sibling rasters):** **`PASS`** (`worst_like_for_like_overlap_3px = 0.61163 <= 0.70`, `unique_like_for_like = true`; pre-placement surface `max |Spearman rho| = 0.224549 <= 0.90`).  
**Literal Dense-Witness Rule (`17GEMSDOE:dense_17gemdoe.tif`, `5,167,373` positive pixels):** `1.0000 > 0.70` (`unique_literal = false` $\implies$ **`OK TO DOWNLOAD = true`, `OK TO SUBMIT = false / DO NOT SUBMIT`**, `verdict = "negative"`, `weekly_slots_used = 0`).

---

## 1. Forensic Analysis: Why `GEMSDOE32` (`H33 = 0.2778`) Scored Highest Among Sibling Sites — and How to Surpass `0.2778`

### 1.1 Exact Nested Subset Chain Across the 10 Sibling Sites
Pixel-level forensic inspection of the restored sibling submissions shows that the four scored submissions (`0.1922`, `0.2600`, `0.2778`, `0.2449`) are not four distinct geological models; the first three form a **strictly nested pixel-subset chain** of a single surface `H19-5` (`h19-5-b2-20261004T201053Z-019a01b2-zeros.tif`):

$$\text{H19-5 } (121{,}419\text{ dots},\, 0.1922) \;\supset\; \text{D2.8 } (44{,}090\text{ dots},\, 0.2600) \;\supset\; \text{SOLO } (38{,}440\text{ dots}) \;\supset\; \text{H33 } (37{,}654\text{ dots},\, 0.2778)$$

1. **`H19-5` $\to$ `D2.8` (`+0.0678` public DTI, `0.1922` $\to$ `0.2600`):** Enforcing a minimum inter-dot spacing of $r_{\min} = \sqrt{8} \approx 2.83\text{ px}$ ($283\text{ m}$, matching the $300\text{ m}$ triangular kernel radius $K(d) = \max(0, 1 - d/300\text{ m})$) removed $77{,}329$ redundant neighboring dots. Under the asymmetric DTI denominator:
   $$\text{DTI} = \frac{\sum_{g \in G} K(d(g, P))}{\sum_{g \in G} K(d(g, P)) + \alpha \sum_{p \in P} (1 - K(d(p, G))) + \beta \sum_{g \in G} (1 - K(d(g, P)))}, \quad \alpha = 0.2,\; \beta = 0.8$$
   coverage $\text{TP} = \sum_{g \in G} K(d(g, P))$ depends **only on the nearest predicted dot** $p \in P$ to each ground-truth pixel $g \in G$, whereas false-positive penalty $\alpha\,\text{FP} = 0.2 \sum_{p \in P} (1 - K(d(p, G)))$ accumulates **additively across every emitted dot** $p \in P$. Packing multiple dots within $2.83\text{ px}$ yields zero additional $\text{TP}$ while multiplying $\alpha\,\text{FP}$.
2. **`D2.8` $\to$ `H33` (`+0.0178` public DTI, `0.2600` $\to$ `0.2778`):** Deleting $5{,}650$ dots within $d_{\text{cat}} \le 2\text{ px}$ ($200\text{ m}$) of the public catalogue `existing_faults.tif` (`D2.8` $\to$ `SOLO`) plus $786$ isolated 1-dot fragments (`SOLO` $\to$ `H33`) eliminated pure false-positive penalty on already-mapped fault traces (which the organizer evaluation masks out of $G$).
3. **Why `H28` (`GEMSDOE47`, `0.2449`) Regressed by `-0.0329` DTI vs `H33` (`0.2778`):** `H28` (`42,846` dots) replaced the zero-catalogue multi-physics surface with a $5\text{ km}$ distance-decay envelope around `existing_faults.tif`, collapsing deep-basin ($d_{\text{cat}} > 25\text{ px}$) dot allocation from **$41.7\%$ (`15,693` dots in `H33`) down to $2.0\%$ (`869` dots in `H28`)** and concentrating $74.8\%$ of its dots within $10\text{ px}$ ($1\text{ km}$) of already-mapped faults.

| Sibling Submission | Public DTI (Evidence Class) | Emitted Dots | $d_{\text{cat}} \le 2\text{ px}$ | $2 < d_{\text{cat}} \le 10\text{ px}$ | $10 < d_{\text{cat}} \le 25\text{ px}$ | $d_{\text{cat}} > 25\text{ px}$ (`share_gt25`) | Median NN Spacing |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `H19-5` (`GEMSDOE23`) | `0.1922` (`USER-REPORTED`) | `121,419` | `12.6%` | `26.8%` | `22.7%` | `37.9%` (`46,018`) | `1.41 px` |
| `D2.8` (`GEMSDOE29`) | `0.2600` (`USER-REPORTED`) | `44,090` | `12.8%` | `24.1%` | `23.6%` | `39.5%` (`17,415`) | `3.16 px` |
| **`H33` (`GEMSDOE32`)** | **`0.2778` (`USER-REPORTED`)** | **`37,654`** | **`0.0%`** | **`28.2%`** | **`30.1%`** | **`41.7%` (`15,693`)** | **`3.16 px`** |
| `H28` (`GEMSDOE47`) | `0.2449` (`USER-REPORTED`) | `42,846` | `0.0%` | `74.8%` | `23.2%` | `2.0%` (`869`) | `3.00 px` |
| **`H88-GCSD` (This Work)** | **`0.201610` (`HOLDOUT-DTI`)** | **`30,000`** | **`0.0%`** | **`24.0%` (`7,200`)** | **`31.0%` (`9,300`)** | **`45.0%` (`13,500`)** | **`3.16 px`** |

### 1.2 Why `H33` Hit a Ceiling at `0.2778` (vs `0.3195` / `0.4413` Public Leaderboard Top) — and How `H88-GCSD` Advances Both Axes
`H33` (`0.2778`) used only linear Sobel gradients of the 19 competition bands without:
1. **Fluid-geochemical & hydrothermal upflow physics** (`T_quartz - T_chalcedony` disequilibrium, flash-cooling surplus, $2\text{ m}$ shallow temperature probes, and siliceous sinter terraces back-projected up-dip onto basement steps),
2. **Elevation- and playa-detrended electrical conductivity clay-cap edges** concordant with magnetite-destructive RTP troughs,
3. **Reliability-weighted Tri-Specialist Log-Odds Product-of-Experts (`PoE`)** combining base physical/structural (`44/67`-ch), geomorphic-vesselness (`68/91`-ch), and hydrothermal-seismic-strike (`80/103`-ch) specialists while gating out the Northern Nevada (`NE` quadrant) seismic-distance sentinel zone (`deq_n100a15 ~ 4.96e6`, `IR-88-82`), and
4. **4-Quadrant Out-Of-Fold (`OOF`) Three-Stratum Dinkelbach Allocation** (`min_spacing_px = 2.85`, `3 < d_cat <= 10 px`: `7,200` dots; `10 < d_cat <= 25 px`: `9,300` dots; `d_cat > 25 px`: `13,500` dots [`share_gt25 = 45.0%`]), which simultaneously preserves `H33`'s deep-basin discovery budget (`45.0%` vs `41.7%`) and eliminates near-catalogue ribbon crowding (`worst_like_for_like_overlap_3px = 0.61163 <= 0.70`).

---

## 2. Five Candidate Geological Hypotheses (Ranked by Expected DTI Improvement & Implementation Cost)

| Rank | ID | Hypothesis Title | Specific Layers Verified | Expected Holdout DTI Gain | Implementation Cost | Status |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- |
| **1** | **`H88-GCSD`** | **Geothermometer-Discordance Upflow, Elevation-Detrended Clay-Cap Conductivity, Critical-Seismic Transtension & Multi-Modal Spin-2 Strike Coherence** | `gdr_wellspring_in_footprint.csv` (`temp_c`, `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`), `2m_temperature_probe_INGENIOUS_regional_data.zip`, `paleo_geothermal_regional.zip`, `training_features.tif` B2/3/4/6/7/8/9/10/11/12/13/15/16/17/18/19, `lidar_scarp_features_u8.tif` B4/5/8/9/10/11/12, `geodawn_dem_a2_100m.tif` | **`+0.0067` vs `H88-ADHR` (`0.201610`, #1 all-time)** | **Low–Medium** (100% local SHA-pinned inputs) | **Implemented & Validated (`HOLDOUT-DTI = 0.201610`)** |
| **2** | `H88-STRAT-TRUNC` | Geologic-Map Contact Truncation Density & Quaternary Juxtaposition Torque | `USGS_SGMC_NV_UT_ID_CA_OR.zip` ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)), `training_features.tif` B12/B13/B15 | `+0.001` to `+0.004` | Low | Reserve (zero compute spent) |
| **3** | `H88-BGP-3D` | 3D Parker–Oldenburg Iterative Gravity Basement Inversion & Listric Detachment Curvature | `training_features.tif` B11 (`iso_grav_anom_vg`), B13 (`iso_grav_anom`), B15 (`depth_to_base_surf`), B18 (`iso_grav_anom_hg`) | `+0.001` to `+0.003` | Medium | Reserve (zero compute spent) |
| **4** | `H88-INSAR-COH` | Sentinel-1 InSAR Interseismic LOS Velocity Gradient & Phase-Coherence Loss Step | Sentinel-1 A/B/C ascending/descending LOS velocity & coherence ([ASF DAAC](https://search.asf.alaska.edu/), [COMET-LiCSAR](https://comet.nerc.ac.uk/COMET-LiCS-portal/)) | Unscored (external data blocked in sandbox) | Blocked by sandbox network allowlist | Documented for out-of-sandbox execution |
| **5** | `H88-ECOSTRESS-TIR` | NASA ECOSTRESS / USGS Landsat C2 Pre-Dawn Thermal-Inertia & Evaporative-Cooling Lineaments | Landsat C2 L2 Surface Temperature ([USGS Landsat ST](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)), [NASA ECOSTRESS](https://ecostress.jpl.nasa.gov/) | Unscored (external data blocked in sandbox) | Blocked by sandbox network allowlist | Documented for out-of-sandbox execution |

### 2.1 Detailed Specification of Each Hypothesis

#### Hypothesis 1 (`H88-GCSD` — Selected & Validated): Geothermometer-Discordance Upflow, Elevation-Detrended Clay-Cap Conductivity, Critical-Seismic Transtension & Multi-Modal Spin-2 Strike Coherence
- **(a) Specific Layers Involved:**
  1. `data/external/gdr_wellspring_in_footprint.csv` (`10,977` wells/springs from DOE GDR #1391: surface discharge `temp_c`, quartz geothermometer `geothermquartz_c`, chalcedony geothermometer `geothermchalc_c`, Na-K-Ca cation geothermometer `geothermcat_c`).
  2. `data/external/2m_temperature_probe_INGENIOUS_regional_data.zip` (`2,487` shallow $2\text{ m}$ temperature probe stations from DOE GDR #1391) and `data/external/paleo_geothermal_regional.zip` (`289` sinter/travertine/silicified deposits).
  3. `data/training_features.tif` verified bands: B2 (`rtp`), B3 (`tmi_hg`), B4 (`geod_2ndinv`), B6 (`tc`), B7 (`geod_shearrate`), B8 (`geod_dilaterate`), B9 (`tmi_vg`), B10 (`deq_n100a15`), B11 (`iso_grav_anom_vg`), B12 (`det_elev`), B13 (`iso_grav_anom`), B15 (`depth_to_base_surf`), B16 (`ieq_n100a15`), B17 (`cond_surf`), B18 (`iso_grav_anom_hg`), B19 (`det_elev_slope`).
  4. `data/external/lidar_scarp_features_u8.tif` bands: B4 (`lapneg_max`), B5 (`lappos_max`), B8 (`cross_max`), B9 (`relief`), B10 (`coh100`), B11 (`strike`), B12 (`valid`), and `data/geodawn_dem_a2_100m.tif`.
- **(b) Physical Signature Targeted (12 Zero-Catalogue Channels in `src/gems88/gcsd.py`):**
  1. `gcsd_qtz_flash_surplus`: Flash/conductive cooling surplus $\max(T_{\text{qtz}}, T_{\text{cat}}) - T_{\text{discharge}}$ — isolates concealed upflow conduits where deep fluids ($>110\text{--}180^\circ\text{C}$) cool conductively beneath Quaternary alluvium before emerging as lukewarm springs.
  2. `gcsd_geotherm_diseq`: Multi-equilibrium chemical disequilibrium $(T_{\text{qtz}} - T_{\text{chalc}}) + 0.5(T_{\text{cat}} - T_{\text{qtz}})$ combined with shallow $2\text{ m}$ temperature probe anomalies — captures rapid vertical ascent along permeable fault-intersection conduits that outpaces silica re-equilibration.
  3. `gcsd_updip_feeder_couple`: Anisotropic up-dip back-projection of the composite hydrothermal + sinter plume along $+\nabla(\text{depth\_to\_base\_surf})$ (`6 px` and `14 px` basinward offsets) gated by basement-step gradient magnitude $|\nabla z_{\text{base}}|$ — maps basinward-drifted thermal plumes back onto their structural range-front/piedmont feeder fault step.
  4. `gcsd_cond_elev_resid`: Elevation- and playa-detrended electrical conductivity residual $[\log(1+\sigma_{\text{cond}})_{\sigma=1.5} - \log(1+\sigma_{\text{cond}})_{\sigma=18.0}] \times (1 - 0.80\,P_{\text{playa}})$ — isolates linear illite–smectite hydrothermal clay-cap alteration zones while cancelling closed-basin evaporite playas.
  5. `gcsd_cond_demag_concord`: Spatial product of local conductivity gradient $|\nabla \log(1+\sigma_{\text{cond}})|$ and Hessian trough curvature $\lambda_+(\text{RTP})$ of Reduced-to-Pole magnetics — targets hydrothermal alteration corridors where acidic fluids simultaneously form conductive smectite clay and destroy primary magnetite into non-magnetic pyrite/hematite.
  6. `gcsd_seismic_crit_shear`: Sentinel-cleaned microseismic proximity $\mathbb{I}(0 \le \text{deq} < 1.2\times 10^5)\,e^{-\text{deq}/15\text{ km}} + 0.35\log(1 + \text{ieq}/50)$ coupled with transtensional shear-dilatation rate $\log(1+\dot{\gamma}_{\text{shear}})\,\sigma(\dot{\epsilon}_{\text{dilat}})$ — captures critically stressed, actively dilating fracture networks (Barton et al., 1995) while masking the `4.96e6` fill sentinel in B10 (`IR-88-82`).
  7. `gcsd_multimodal_spin2_coh`: 4-modality spin-2 axial strike coherence $\|\sum_{m \in \{\text{grav, rtp, zbase, elev}\}} w_m (\cos 2\theta_m, \sin 2\theta_m)\| / \sum_m w_m$ — measures invariant axial alignment across gravity, magnetics, basement depth, and detrended elevation regardless of step polarity reversal across horst/graben boundaries.
  8. `gcsd_grav_zbase_admittance`: Cross-gradient admittance $-\nabla(\text{iso\_grav}) \cdot \nabla(z_{\text{base}})$ modulated by vertical gravity gradient $|\text{iso\_grav\_vg}|$ — isolates true density-contrasted structural basement steps from intra-basement pluton boundaries.
  9. `gcsd_tilt_contact_sharpness`: Salem et al. (2007) magnetic tilt-angle zero-crossing sharpness $\exp(-z_{\text{tc}}^2/2)\,\log(1+|\text{tmi\_vg}|)\,\log(1+\text{tmi\_hg})$ — pinpoints the vertical projection of buried fault contacts.
  10. `gcsd_bajada_hinge_asymmetry`: Piedmont bajada (`zbase` $\in [100, 650]\text{ m}$) 1 m LiDAR Laplacian dipole $|\text{lapneg} - \text{lappos}|/(\text{lapneg} + \text{lappos} + 6)$ suppressed along Pleistocene Lake Lahontan/Bonneville highstand elevations (`1330 m` and `1555 m`).
  11. `gcsd_lidar_multimodal_strike`: Cosine double-angle alignment $\text{coh}_{100}\cos 2(\theta_{\text{LiDAR}} - \theta_{\text{crustal}})\log(1 + \text{cross\_max}/8)$ between 1 m LiDAR micro-scarps and the 4-modality crustal strike tensor.
  12. `gcsd_mimic_playa_volc_pen`: Explicit non-fault mimic penalty combining flat saline playa conductivity ($\text{slope} \approx 0, \text{det\_elev} \le 0, \text{cond\_surf high}$), circular volcanic vent edifices (`gdr_volcanic_vents_in_footprint.csv`), and pluvial shoreline contours.
- **(c) Why It Catches Faults Missing from `existing_faults.tif`:** Over $75\%$ of Known Geothermal Resource Areas (KGRAs) in the Great Basin (Faulds et al., 2016, 2021; INGENIOUS dataset) are **blind geothermal systems** concealed beneath unconsolidated Quaternary alluvial fans and playas where surface fault scarps were buried or eroded prior to field mapping. Even when a fault has zero surface topographic expression, upwelling thermal fluids, silica/cation disequilibrium, smectite clay-cap conductivity combined with magnetite destruction, and basement gravity admittance persist through the alluvial cover.
- **(d) How It Differs from All Prior `GEMSDOE88` Lanes:**
  - `H88-GTHC` used only raw `temp_c` and `geothermquartz_c` point splats without chemical disequilibrium ($T_{\text{qtz}} - T_{\text{chalc}}$), without up-dip back-projection onto basement steps, without $2\text{ m}$ temperature probes or paleo-sinter deposits, and without `cond_surf` clay-cap / RTP demagnetization coupling.
  - `H88-TDKL` and `H88-VESS` used zero geothermal/geochemical data, zero `cond_surf` (B17), zero `deq_n100a15`/`ieq_n100a15` (B10/B16), and suffered from `IR-88-112` (`84.55%` 3-px dot overlap because of in-sample near-catalogue ribbon packing).

#### Hypothesis 2 (`H88-STRAT-TRUNC` — Reserve): Geologic-Map Contact Truncation Density & Quaternary Juxtaposition Torque
- **(a) Layers Involved:** `data/external/USGS_SGMC_NV_UT_ID_CA_OR.zip` ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/) State Geologic Map Compilation lithologic polygons) + `training_features.tif` B12, B13, B15.
- **(b) Physical Signature:** Spatial density of high-angle terminations where pre-Quaternary bedrock lithologic contacts end abruptly against Quaternary alluvium ($Q_a$) along a linear strike concordant with $\nabla(\text{iso\_grav\_anom})$.
- **(c) Why It Catches Unmapped Faults:** Lithologic map polygon boundaries were mapped by bedrock stratigraphers even where range-front or intra-basin fault traces were omitted from structural fault compilations because Quaternary talus covered the fault plane.
- **(d) Difference from Prior Repo Work:** `physics.py` used scalar bedrock rigidity contrast across cells; it never extracted pre-Quaternary contact-truncation endpoints against Quaternary cover or their strike torque against basement gravity steps.

#### Hypothesis 3 (`H88-BGP-3D` — Reserve): 3D Parker–Oldenburg Iterative Gravity Basement Inversion & Listric Detachment Curvature
- **(a) Layers Involved:** `training_features.tif` B11 (`iso_grav_anom_vg`), B13 (`iso_grav_anom`), B15 (`depth_to_base_surf`), B18 (`iso_grav_anom_hg`).
- **(b) Physical Signature:** Discrepancy between 2D Fourier downward-continued gravity-interface step curvature and the smooth regional `depth_to_base_surf` surface, isolating steep listric growth-fault rollovers and antithetic hanging-wall blocks.
- **(c) Why It Catches Unmapped Faults:** Intrabasin synthetic/antithetic growth faults accommodated entirely within Mio-Pliocene basin fill lack surface scarps (`det_elev_slope ~ 0`) but produce sharp short-wavelength vertical gravity-gradient curvature anomalies.
- **(d) Difference from Prior Repo Work:** All prior lanes treated B13 and B15 in the spatial domain with first/second Gaussian derivatives; none computed wavenumber-domain Parker–Oldenburg interface residuals.

#### Hypothesis 4 (`H88-INSAR-COH` — Blocked in Sandbox): Sentinel-1 InSAR Interseismic LOS Velocity Gradient & Phase-Coherence Loss Step
- **(a) Layers & Verified Official Free Sources:** Copernicus Sentinel-1 A/B/C ascending/descending Line-of-Sight (LOS) surface deformation velocity and interferometric coherence maps via NASA/ASF DAAC ([https://search.asf.alaska.edu/](https://search.asf.alaska.edu/)) and COMET-LiCSAR ([https://comet.nerc.ac.uk/COMET-LiCS-portal/](https://comet.nerc.ac.uk/COMET-LiCS-portal/)).
- **(b) Physical Signature:** Sub-kilometer step gradients in interseismic LOS velocity ($|\nabla v_{\text{LOS}}| > 1.5\text{ mm/yr/km}$) co-located with linear phase-decorrelation ribbons caused by aseismic fault-zone creep and differential hydro-compaction across fault-bounded aquifer compartments.
- **(c) Why It Catches Unmapped Faults:** Band 7/8 (`geod_shearrate`, `geod_dilaterate`) are interpolated from sparse GPS stations ($20\text{--}50\text{ km}$ spacing) and cannot resolve individual $100\text{ m}$ fault traces; $20\text{--}100\text{ m}$ InSAR resolves active creeping and hydrologically compartmentalized blind faults directly across flat basin floors.
- **(d) Sandbox Availability:** Blocked by the sandbox outbound allowlist (`github.com`, `pypi.org`, `registry.npmjs.org`); documented for out-of-sandbox execution.

#### Hypothesis 5 (`H88-ECOSTRESS-TIR` — Blocked in Sandbox): NASA ECOSTRESS / USGS Landsat C2 Pre-Dawn Thermal-Inertia & Evaporative-Cooling Lineaments
- **(a) Layers & Verified Official Free Sources:** NASA/JPL ECOSTRESS L2 Land Surface Temperature & Emissivity ([https://ecostress.jpl.nasa.gov/](https://ecostress.jpl.nasa.gov/)) and USGS Landsat Collection 2 Level-2 Surface Temperature ([https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature)).
- **(b) Physical Signature:** Linear pre-dawn apparent thermal inertia (ATI) ridges and daytime evaporative-cooling troughs along fault-controlled phreatophyte alignments and shallow diffusive geothermal heat-flux corridors ($70\text{--}100\text{ m}$ resolution).
- **(c) Why It Catches Unmapped Faults:** Well/spring catalogues (`gdr_wellspring_in_footprint.csv`) only sample discrete drilled or discharging points ($10,977$ locations); satellite TIR images the continuous linear thermal/moisture trace connecting blind upflow zones between sparse wells.
- **(d) Sandbox Availability:** Blocked by the sandbox outbound allowlist; documented for out-of-sandbox execution.

---

## 3. Experimental Validation on the 8-Fold Spatially-Blocked Holdout (`gems57-pooled-hide-v2`)

### 3.1 Single-Feature Leakage Canary (`80` Zero-Catalogue Channels)
All `80` zero-catalogue channels (`44` `PHYS-44` + `12` `TDKL-12` + `12` `VESS-12` + `12` `GCSD-12`) were tested individually on the withheld holdout folds (`seeds 20, 21`) prior to model trust:
- **Overall maximum symmetric AUC (`80` channels):** **`0.59299 <= 0.90`** (`tdkl_lidar_cross_scarp`, `PASS`).
- **`GCSD-12` single-feature AUCs (`seed = 20`):**
  - `gcsd_seismic_crit_shear`: `roc_auc = 0.55437` (`sym_auc = 0.55437`)
  - `gcsd_grav_zbase_admittance`: `roc_auc = 0.54334` (`sym_auc = 0.54334`)
  - `gcsd_bajada_hinge_asymmetry`: `roc_auc = 0.53588` (`sym_auc = 0.53588`)
  - `gcsd_mimic_playa_volc_pen`: `roc_auc = 0.46477 < 0.50` (`sym_auc = 0.53523`, confirming negative correlation with true faults as designed for a non-fault mimic penalty!)
  - `gcsd_cond_elev_resid`: `roc_auc = 0.52979` (`sym_auc = 0.52979`)
  - `gcsd_tilt_contact_sharpness`: `roc_auc = 0.52601` (`sym_auc = 0.52601`)
  - `gcsd_lidar_multimodal_strike`: `roc_auc = 0.47821` (`sym_auc = 0.52179`)
  - `gcsd_cond_demag_concord`: `roc_auc = 0.51861` (`sym_auc = 0.51861`)
  - `gcsd_updip_feeder_couple`: `roc_auc = 0.51368` (`sym_auc = 0.51368`)
  - `gcsd_multimodal_spin2_coh`: `roc_auc = 0.50905` (`sym_auc = 0.50905`)
  - `gcsd_qtz_flash_surplus`: `roc_auc = 0.50470` (`sym_auc = 0.50470`)
  - `gcsd_geotherm_diseq`: `roc_auc = 0.50279` (`sym_auc = 0.50279`)

### 3.2 Pooled 8-Fold Holdout Progression Across All `GEMSDOE88` Lanes

| Model / Lane | Evidence Class | Overall `HOLDOUT-DTI` (`n = 22,893`) | 95% Block-Bootstrap CI | Far `> 10 px` (`n = 10,791`) | Blind `> 25 px` (`n = 3,117`) | Prod `share_gt25` | Worst Like-for-Like 3-px Overlap |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Control 1: phys44_zero_cat` | `HOLDOUT-DTI` | `0.104163` | `[0.090747, 0.117718]` | `0.095452` | `0.068027` | — | — |
| `Exp 01: gcsd_phys_only` (80-ch zero-cat) | `HOLDOUT-DTI` | **`0.106596`** | `[0.092307, 0.120321]` | **`0.097745`** | `0.067241` | — | — |
| `H88-ADHR` (B14 baseline) | `HOLDOUT-DTI` | `0.187888` | `[0.171698, 0.203260]` | `0.114780` | `0.065263` | `4.20%` | `0.4150` |
| `H88-ADHR` (stored canonical) | `HOLDOUT-DTI` | `0.190436` | `[0.174298, 0.205941]` | `0.114780` | `0.065263` | `4.20%` | `0.4150` |
| `H88-GTHC` (Exp 02 / Exp 03) | `HOLDOUT-DTI` | `0.190971` / `0.170718` | `[0.174802, 0.206324]` | `0.119069` | `0.068964` | `36.71%` | `0.5882` |
| `H88-QTSK` (Exp 02 / Exp 03) | `HOLDOUT-DTI` | `0.192759` / `0.151511` | `[0.176444, 0.208469]` | `0.120955` | `0.077160` | `46.40%` | `0.6251` |
| `H88-SAR-CSD` (Exp 02 / Exp 03) | `HOLDOUT-DTI` | `0.192936` / `0.151589` | `[0.176484, 0.208461]` | `0.121192` | `0.075776` | `38.72%` | `0.6464` |
| `Control 2: h88_adhr_incumbent` (B12 fix) | `HOLDOUT-DTI` | `0.194876` | `[0.177933, 0.210764]` | `0.125735` | `0.076483` | `4.20%` | `0.4150` |
| `H88-TDKL` (Exp 03 PoE, 25k dots) | `HOLDOUT-DTI` | `0.196237` | `[0.179686, 0.211729]` | `0.124175` | `0.076881` | `42.00%` | `0.5566` (`0.728` post-merge) |
| `H88-MVRD` (25k dots) | `HOLDOUT-DTI` | `0.197314` | `[0.181121, 0.213008]` | — | — | `2.87%` (FAIL) | `0.9462` (FAIL) |
| `H88-VESS` (Exp 03 PoE, 25k dots) | `HOLDOUT-DTI` | `0.200941` | `[0.183602, 0.217576]` | `0.131922` | `0.090449` | `42.00%` | `0.8455` (**FAIL** vs TDKL) |
| **`Exp 03: H88-GCSD` (Tri-PoE, 30k dots)** | **`HOLDOUT-DTI`** | **`0.201610`** | **`[0.184052, 0.218447]`** | **`0.134220`** | **`0.089196`** | **`45.00%` (PASS)** | **`0.6116` (PASS `<= 0.70`)** |

---

## 4. Production GeoTIFF & Automatic Fail-Closed Gate Audit

- **Artifact:** `docs/downloads/gems88-gcsd88-poe-30000dots-20261024-zeros-DO-NOT-SUBMIT.tif` (`126,264` bytes, SHA-256 `99be29e97a6af830cbc3f72995e9a2c07d1f7f1542f0fab15947faf3559039f5`)
- **ZIP Archive:** `docs/downloads/gems88-gcsd88-poe-30000dots-20261024-zeros-DO-NOT-SUBMIT.zip` (`115,375` bytes, SHA-256 `9be649a0867c4d9a7b685c35c0d8335be3cbdde1616faec70752b3b966823832`)
- **Format & `[0, 1]` Range Checks:** Single-band `float32`, `EPSG:32611`, `3730 x 3292`, `transform = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)`, `nodata = None`, `n_nan = 0`, `n_inf = 0`, `min = 0.0`, `max = 1.0`, `30,000` positive pixels (`0` outside footprint, `0` within `3.0 px` of `existing_faults.tif`).
- **Why `OK TO DOWNLOAD = true` and `OK TO SUBMIT = false` (`DO NOT SUBMIT`):**
  1. Every format/range check, leakage canary (`0.59299 <= 0.90`), holdout bar (`0.201610 > 0.200941`, paired $\Delta = +0.006734$, `95% CI [+0.001337, +0.011897]`), H33-parity basin fingerprint (`share_gt25 = 45.0% >= 35%`, `share_le2 = 0.0%`), pre-placement surface correlation (`0.224549 <= 0.90`), and **like-for-like 3-px dot overlap (`0.61163 <= 0.70` across all sparse/like-for-like rasters in the 270-raster corpus)** **PASS**.
  2. Under the binding literal reading of Protocol Rule 1, the registry contains the full-footprint dense witness `17GEMSDOE:dense_17gemdoe.tif` (`5,167,373` positive pixels = 100% of the active footprint, plus `GEMSDOE87`'s `501,196`-pixel research surface), against which **any** in-footprint submission has literal forward 3-px overlap `1.0000 > 0.70` (`IR-88-100`). Furthermore, beating `H33` (`0.2778`, `USER-REPORTED`) on hidden organizer test faults cannot be proven on catalogue hide-and-recover (`n = 22,893`). Therefore the automatic validator (`python scripts/validate_gcsd88.py --require-submit`) fails closed with exit code `2` (`OK TO DOWNLOAD = true`, `OK TO SUBMIT = false`, `weekly_slots_used = 0`).
