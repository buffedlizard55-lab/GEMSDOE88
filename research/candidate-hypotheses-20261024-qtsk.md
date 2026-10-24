# Preregistered Candidate Geological Hypotheses — Session `2026-10-24` (`H88-QTSK`)

**Timestamp (UTC):** `2026-10-24T21:20:00Z` (written and frozen prior to model implementation or holdout execution)  
**Branch:** `arena/14b2260c-gemsdoe88`  
**Evaluator & Holdout Split:** `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, buffered whole-component holdout on seeds `20` and `21`, `3 px` hide buffer, `12 px` quadrant boundary buffer, `22,893` withheld positive pixels across `8` folds, `20 km` spatial block bootstrap `B=400`, `95% CI`)  
**Incumbent `HOLDOUT-DTI` Bar:** `H88-ADHR` stored `0.187888` (`[0.168077, 0.214364]`), paired recomputation on identical `gems57-pooled-hide-v2` folds `0.189634` (`[0.168989, 0.211618]`).  
**Fleet Empirical Blind-Basin Screen (`gems88-gate-v3`):** `share_le2 == 0.0` and `share_gt25 >= 0.35` (derived from `H33 = 0.2778` forensics where `share_gt25 = 41.7%` and `Spearman rho(share_gt25, public DTI) = +0.90` across 20 owner-reported runs).

---

## 1. Root-Cause Diagnosis of Prior Sessions (Why Every Prior Candidate Failed Either Holdout or Uniqueness/Fingerprint)

A line-by-line audit of `src/gems88/physics.py`, `src/gems88/adhr.py`, `evidence/existing_candidates_gate_20261024.json`, and all 223 registry/sibling rasters reveals two coupled bottlenecks:

1. **The Near-Catalogue Ribbon Pigeonhole & Blind-Basin Starvation Bottleneck (`adhr._fuse_log_odds`):**
   - In `gems57-pooled-hide-v2` (`n = 22,893` withheld whole-component pixels), **86.4%** of withheld pixels lie inside `2 < d_vis <= 25 px` (`~1.05M` active pixels), while **only 13.6%** (`3,117` pixels) lie in `d_vis > 25 px` (`~2.44M` active pixels — `51.2%` of the footprint).
   - `adhr._fuse_log_odds` normalizes both `P_poe(X_phys, X_vis)` and `P_phys(X_phys)` to equal total mass `k_target` and takes a **spatially constant** `50/50` convex average (`pi_unmapped = 0.50`). Because `P_poe` concentrates its mass inside the narrow `2 < d <= 10 px` structural corridor (`0.05–0.40`/px) while `P_phys` spreads across `5.17M` pixels (`0.002–0.015`/px), Dinkelbach (`min_spacing_px = 2.05`, gain cutoff `~0.2 * DTI`) places **95.8%** of `H88-ADHR`'s `35,894` dots within `25 px` (`share_gt25 = 4.23% < 35%`).
   - Worse, because `2 < d_cat <= 10 px` comprises only `~420,000` pixels across the entire study area, any two models packing `~35,000` `3 px`-radius disks into that ribbon inevitably approach or breach the `0.70` 3-px dot-overlap ceiling (`ADHR` vs `GHMD` is already `0.6796`).
2. **Digitization-Jitter Flank Self-Cannibalization (`adhr._fit_dual_expectation_models`) & Unopened Geomorphic Rasters:**
   - `adhr._fit_dual_expectation_models` includes **all** pixels with `0 < y_kern <= 1` (`0 <= d < 3 px`) in `near_idx` (`weight = 1.0`) while `yc_tr` labels only the `1 px` polyline (`d == 0`) as `1` and **every pixel at `1 <= d < 3 px` (`~220,000` flank pixels!) as `y = 0`**. Because mapped Quaternary fault polylines have `±100–200 m` (`1–2 px`) cartographic digitization error (the exact reason DrivenData uses a `300 m` triangular kernel) and `100–300 m` physical scarp/potential-field widths, labelling `1 <= d <= 2 px` pixels as `y = 0` forces `HistGradientBoostingClassifier` to suppress sharp physical crests.
   - Simultaneously, `src/gems88/physics.py` **never opened** `data/external/dem10_chi_100m_u8.tif` (`chan_n`, `knick_n`, `raised_n`, `valid_n`), **never opened** `lidar_scarp_features_u8.tif` Bands 6–8 (`downface_max`, `upface_max`, `cross_max`), **never opened** `topo_10m_derived_100m_u8.tif` Bands 3, 4, 7 (`steep_frac`, `slope_std`, `aspect_coherence`), and never computed the decoupled Quaternary cover-thickness step (`next-steps-20261024-mdc88.md` #1).

---

## 2. Five Ranked New Candidate Geological Hypotheses

| Rank | ID | Short Name | Expected `HOLDOUT-DTI` / Blind-Basin Gain | Compute / Eng Cost | Data Status | Selected? |
|---:|---|---|---|---|---|---|
| **1** | **`H88-QTSK`** | **Decoupled Quaternary Cover-Thickness Steps + Tectonic Fluvial $\chi$-Knickpoint & Scarp-Polarity Wavefronts** | **High** (`+0.025..+0.055` pure-physics; positive paired delta target vs `ADHR` + `>=35%` blind-basin recall) | **Low–Med** (`~35 s` feature build, single 8-fold pass `~14 min`) | **100% SHA-verified in `data/`** (`training_features`, `dem10_chi_u8/i16`, `lidar_scarp`, `topo_10m`) | **YES — Active Lane (`Exp 1–3`)** |
| **2** | `H88-GCA` | Multi-Wavenumber Isostatic Gravity–MT Conductance Spectral Admittance Jump | Moderate (`+0.012..+0.025`) | Low–Med (`~4 min` 2D FFT bandpass) | 100% in `data/training_features.tif` (`Bands 6, 13, 17`) | Deferred |
| **3** | `H88-MHD` | Upward-Continued Potential-Field Horizontal-Gradient "Worm" Lateral Migration ($\partial\mathbf{x}/\partial z \to 0^+$) | Moderate (`+0.010..+0.022`) | Medium (`5` continuation heights + ridge tracker) | 100% in `data/training_features.tif` (`Bands 2, 13`) + `geodawn_extensions` | Deferred |
| **4** | `H88-EQR` | Sentinel-Clean Geodetic Coulomb Stress Rate + Relocated 3D ANSS ComCat Hypocentral Plane Updip Projection | Low–Mod (`+0.006..+0.015`) | Med–High (external earthquake catalog ingest) | Bands `4,7,8,10,16` local; ANSS ComCat API blocked by sandbox host allowlist | Deferred (network host gate) |
| **5** | `H88-OPERA` | NASA/ASF OPERA Sentinel-1 LOS Subsidence Gradient Across Hydraulic Fault-Gouge Aquitards | Mod–High (`+0.015..+0.035` in unconsolidated basins) | High (`multi-GB` DISP-S1 tiles) | Official free NASA/ASF DAAC source; blocked by sandbox host allowlist | Deferred (network host gate) |

---

### Detailed Specification of Each Hypothesis

#### Hypothesis 1 (Rank #1 — SELECTED): `H88-QTSK` — Decoupled Quaternary Cover-Thickness Steps + Tectonic Fluvial $\chi$-Knickpoint & Scarp-Polarity Wavefronts
- **Input Layers & Physical Transforms (14 new zero-catalogue channels appended to 44-col `X_phys`):**
  1. **Decoupled Quaternary Cover-Thickness Steps (`Band 15 depth_to_base_surf`, `Band 12 det_elev`, `Band 13 iso_grav_anom`):**
     $$D_\sigma(\mathbf{x}) = \|\nabla_\sigma z_{\text{base}}(\mathbf{x})\| \cdot \Bigl(1 - \bigl|\cos\angle\bigl(\nabla_\sigma z_{\text{base}}(\mathbf{x}), \nabla_\sigma z_{\text{det}}(\mathbf{x})\bigr)\bigr|\Bigr), \quad \sigma \in \{1, 3, 6\}\text{ px}$$
     paired with basement Hessian positive ridge curvature $\lambda_+(\log(1 + z_{\text{base}}))$ at $\sigma = 2\text{ px}$ minus surface $\det\_\text{elev}$ curvature, and signed half-graben density-step concordance $(-\nabla_3 g_{\text{iso}} \cdot \nabla_3 z_{\text{base}}) / (\|\nabla_3 z_{\text{base}}\| + \epsilon)$.
  2. **Tectonic Fluvial $\chi$-Knickpoint & Raised-Footwall Wavefronts (`dem10_chi_100m_u8.tif` Bands 1–4 `chan_n, knick_n, raised_n, valid_n`; `dem10_chi_100m_i16.tif` Bands 1, 2, 4 `step_max, step_min, log10_area_m2`):**
     - Cross-drainage smoothed knickpoint rate $\text{knick\_n} / (\text{chan\_n} + 1)$ (`Perron & Royden, 2013`);
     - Across-slope gradient of uplifted channel fraction $\|\nabla_\sigma(\text{raised\_n} / (\text{valid\_n} + 1))\|$ ($\sigma = 2\text{ px}$), pinpointing the footwall-to-hanging-wall base-level break;
     - Headwater-gated bipolar $\chi$-step contrast $\frac{\text{step\_max} - |\text{step\_min}|}{1000} \cdot \sigma\!\bigl(\frac{6.5 - \log_{10} A}{0.8}\bigr)$, passing range-front piedmont fans while suppressing trunk axial rivers.
  3. **1 m LiDAR Scarp Facing-Polarity & 10 m Planar Facet Continuity (`lidar_scarp_features_u8.tif` Bands 6, 7, 8, 12 `downface_max, upface_max, cross_max, valid`; `topo_10m_derived_100m_u8.tif` Bands 3, 4, 7 `steep_frac, slope_std, aspect_coherence`):**
     - Signed scarp facing polarity $\frac{\text{downface\_max} - \text{upface\_max}}{\text{downface\_max} + \text{upface\_max} + 8}$ where `valid > 0` (`-2.0` sentinel outside 3DEP 1 m coverage);
     - Antithetic graben index $\sqrt{\text{cross\_max} \cdot \max(\text{downface\_max}, \text{upface\_max})}$;
     - 10 m DEM planar triangular-facet coherence $\frac{\text{steep\_frac} \cdot \text{aspect\_coherence}}{\text{slope\_std} + 8}$, providing uniform planar-scarp detection across the **24.6% 3DEP 1 m LiDAR coverage gap**.
  4. **Cross-Depth Spin-2 Strike Persistence, Elevation-Detrended MT Upflow & Transtensional Basement Dilation (`Bands 2, 4, 8, 12, 15, 17` + `topo10 dem_mean`):**
     - Spin-2 structure-tensor strike concentration $\kappa \in [0, 1]$ across shallow topography (`det_elev`), intermediate crustal magnetics (`rtp`), and basement depth (`depth_to_base_surf`);
     - Local `5 km` elevation-detrended shallow MT conductance anomaly (separating elevated range-front clay caps from valley-bottom playas);
     - Geodetic dilatational-shear basement-step coupling $\operatorname{asinh}(\text{geod\_dilaterate}) \cdot \log(1 + \text{geod\_2ndinv}) \cdot \log(1 + \|\nabla_3 z_{\text{base}}\|)$.
- **Why It Catches Faults Missing from USGS/INGENIOUS Catalogues:**
  1. Intra-basin and piedmont faults buried under Holocene sheetwash/playa fill have zero surface scarp (`det_elev` flat) yet preserve sharp `100–600 m` decoupled basement-fill thickness steps (`D_sigma`) with matching negative isostatic gravity steps.
  2. Active faults inside the **24.6% 3DEP 1 m LiDAR void** across central/northern Nevada were missed on legacy aerial photos, but 10 m DEM stream-profile $\chi$ analysis (`knick_n`, `raised_n`) and planar facet coherence (`steep_frac * aspect_coherence`) resolve their transient incision wavefronts across adjacent catchments.
- **Named Non-Fault Mimics & Mitigations:**
  1. *Buried fluvial paleochannels and Miocene volcanic pinchouts:* Produce $|\nabla z_{\text{base}}|$ without consistent unilateral negative isostatic gravity drop or transtensional strain; suppressed by signed gravity concordance and cross-depth spin-2 strike concentration.
  2. *Lithologic caprock ledges, incised axial trunk rivers (Humboldt/Truckee/Carson), Lake Lahontan (`1330 m` / `1555 m`) shorelines, and symmetric two-walled arroyos:* Suppressed by drainage-area headwater gating ($\log_{10} A$), `physics.py`'s Lahontan shoreline penalty, and LiDAR scarp facing asymmetry (`downface_max - upface_max` $\approx 0$ on symmetric gullies).
- **How It Differs from Everything Already in `GEMSDOE88` & Siblings:**
  - Opens `dem10_chi_100m_u8.tif` (`chan_n, knick_n, raised_n`) and `lidar_scarp_features_u8.tif` Bands 6–8 (`downface_max, upface_max, cross_max`) and `topo_10m` Bands 3, 4, 7 for the **first time in repo history**.
  - Implements the previously untested #1 handoff hypothesis `H-QTS` (`next-steps-20261024-mdc88.md`).
  - Fixes `adhr._fit_dual_expectation_models`'s `1–2 px` flank self-cannibalization (`exclude 0 < d <= 2.0 px` ambiguous digitization collar from `clf` hard negatives inside `train_regions`).
  - Directly tests constant-prior fusion (`Exp 2`) vs radial mapping-incompleteness stratification (`Exp 3`) on identical OOF models.

#### Hypothesis 2 (Rank #2): `H88-GCA` — Multi-Wavenumber Gravity–MT Conductance Spectral Admittance Jump
- **Layers & Transform:** 2D radially bandpassed cross-spectrum between `Band 17 (cond_surf)` and `Band 13 (iso_grav_anom)` + `Band 6 (tc)` across short (`0.4–2.0 km`) vs intermediate (`3–10 km`) wavelengths, isolating narrow subvertical conductive fluid/clay gouge zones cutting dense footwall blocks (`Bedrosian et al., 2018`, DOI `10.5066/P9TWT2LU`).
- **Why Unmapped:** Catches non-magnetic carbonate-hosted faults in eastern Nevada lacking magnetic contrast and topographic expression.
- **Non-Fault Mimic:** Stratiform Paleozoic graphitic/pyritic black shales (`Woodruff / Pilot Shale`) and saline playa margins.
- **Novelty vs Repo:** Uses wavenumber-domain admittance phase/coherence rather than spatial scalar products (`physics.py` col 12) or isotropic conductivity ridges (`COND-SURF-ANISO-RIDGE`).

#### Hypothesis 3 (Rank #3): `H88-MHD` — Potential-Field Upward-Continuation "Worm" Lateral Migration Inversion
- **Layers & Transform:** Upward continuation of `Band 2 (rtp)` and `Band 13 (iso_grav_anom)` across $z \in \{100, 200, 400, 800, 1600\}\text{ m}$, tracking horizontal-gradient crest trajectories $\mathbf{x}_{\text{worm}}(z)$ and extrapolating linear regression $\mathbf{x}(z \to 0^+)$ back to the buried bedrock piercing trace (`Hornby et al., 1999`; `Archibald et al., 1999`).
- **Why Unmapped:** Resolves the true surface-piercing trace of dipping (`40°–70°`) concealed faults rather than placing dots `0.5–1.5 km` downdip over the hanging-wall gravity midpoint.
- **Non-Fault Mimic:** Tilted ash-flow tuff caldera margins, pluton roof contacts, and GeoDAWN Area-2 `22°` drape-clearance breaks over steep relief (`Glen & Earney, 2024`).
- **Novelty vs Repo:** `ADHR` assumed a fixed `60°` shift from `depth_to_base_surf`; `UPWARD-CONT-PERSIST` only tested zero-offset vertical persistence without lateral migration inversion.

#### Hypothesis 4 (Rank #4): `H88-EQR` — Geodetic Coulomb Stress Rate + Relocated 3D ComCat Microseismic Plane Projection
- **Layers & Transform:** `Bands 4, 7, 8, 10, 16` (`geod_2ndinv, shearrate, dilaterate, deq_n100a15, ieq_n100a15` with `-3.4e38` sentinel masking) fused with 3D RANSAC plane fits to USGS ANSS ComCat / Nevada Seismological Lab relocated microearthquakes projected updip to DEM elevation.
- **Why Unmapped:** Active blind transfer/accommodation zones in the Walker Lane and Central Nevada Seismic Belt illuminate in 3D microseismicity without Holocene surface scarps.
- **Non-Fault Mimic:** Geothermal plant injection clusters, open-pit mine blasts, and `R=100 km` circular ring truncations in `Bands 10 & 16` (`IR-88-10`).
- **Novelty vs Repo:** Replaces isotropic earthquake distance logs (`physics.py` col 25) with 3D plane-to-DEM intersections.

#### Hypothesis 5 (Rank #5): `H88-OPERA` — NASA/ASF OPERA Sentinel-1 LOS Velocity Gradient Across Fault-Zone Hydraulic Barriers
- **Layers & Transform:** Official NASA/JPL OPERA North America `DISP-S1` (`30 m` Sentinel-1 LOS velocity, resampled to `100 m` `EPSG:32611`) directional across-bajada gradient paired with dry-season Landsat groundwater-barrier vegetation steps (`Bense et al., 2013`).
- **Why Unmapped:** Unconsolidated Quaternary fault cores form clay-smear aquitards that step seasonal poroelastic head change across `100 m` fault traces invisible to gravity, magnetics, and LiDAR.
- **Non-Fault Mimic:** Agricultural pumping/field boundaries, railroad/highway embankments, and playa halite crusts.
- **Novelty vs Repo:** First poroelastic InSAR deformation-step formulation; documented for unrestricted network runners because sandbox outbound access is restricted to `github.com`, `pypi.org`, and `registry.npmjs.org`.

---

## 3. Official Public Data Source Audit (`2026-10-24`)

| Official Dataset | Agency / Persistent Identifier | License | Obtainability in Sandbox | Role in `H88-QTSK` |
|---|---|---|---|---|
| INGENIOUS Great Basin Regional Compilation (`training_features.tif` source layers, 2m probes, paleo-geothermal, well/spring geochemistry, volcanic vents) | DOE GDR `#1391` (`Ayling et al., 2022`, DOI `10.15121/1881483`) | CC-BY-4.0 | **Restored & SHA-256 verified** in `data/` | Core 19-band physics + hydrothermal upflow |
| USGS GeoDAWN Airborne Magnetic, Radiometric & LiDAR/DEM Compilation | USGS Data Release (`Glen & Earney, 2024`, DOI `10.5066/P93LGLVQ`) | CC0 1.0 Public Domain | **Restored & SHA-256 verified** (`geodawn_dem_a2_100m.tif`, `geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`, `lidar_scarp_features_u8.tif`) | New LiDAR scarp facing polarity (`Bands 6–8`) + DEM |
| USGS 3DEP 10 m National Elevation Dataset (`topo_10m` & `dem10_chi` stream-profile $\chi$ grids) | USGS 3DEP (`https://www.usgs.gov/3d-elevation-program`) | CC0 1.0 Public Domain | **Restored & SHA-256 verified** (`topo_10m_derived_100m_u8.tif`, `dem10_chi_100m_i16.tif`, `dem10_chi_100m_u8.tif`) | New `knick_n`, `raised_n`, bipolar $\chi$-step, 10 m planar facet coherence |
| USGS Quaternary Fault & Fold Database / INGENIOUS Fault Slip & Dilation Tendency | USGS (`Siler, 2022`, DOI `10.5066/P9YL58W6`) | CC0 1.0 Public Domain | `existing_faults.tif` restored; fold-visible strictly masked in holdout | Supervision + fold-visible relay geometry only |
| USGS ANSS ComCat / OpenTopography / NASA ASF OPERA DISP-S1 | `earthquake.usgs.gov`, `opentopography.org`, `asf.alaska.edu` | Public Domain / CC-BY | Live HTTP blocked by sandbox allowlist (`github.com`, `pypi.org`, `npmjs.org` only) | Documented for Hypotheses #4–#5 |

---

## 4. Preregistered 3-Experiment Protocol Within Lane `H88-QTSK` (Strict Cap: `<= 3` Experiments, `< 2` Hours)

All three experiments share the **single `H88-QTSK` method family**, run in **one paired 8-fold evaluation pass** on `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, seeds `20` and `21`, `3 px` hide buffer, `12 px` quadrant buffer, `22,893` withheld positive pixels), and are preceded by an automated **single-feature leakage canary** (`symmetric AUC <= 0.90` required for every individual feature; abort immediately if any feature exceeds `0.90`):

1. **Paired Control (`H88-ADHR` Incumbent, `0` new design DOF):** Exact unmodified `adhr.predict_adhr_fold` on `X_phys (44)` + `X_v22 + d_over_w`, establishing the exact paired per-fold and `20 km` block-bootstrap baseline (`0.189634`, stored `0.187888`).
2. **Experiment 1 (`H88-QTSK-PHYS` — Zero-Catalogue 58-Channel Blind Discovery):** De-jittered dual-expectation (`exclude 0 < d <= 2.0 px` ambiguous flank collar from `clf` hard negatives inside `train_regions`) on `[X_phys (44), X_qtsk (14)]` (`58` strictly label-blind physical-geomorphic features, **zero catalogue inputs**) + exact Dinkelbach `{0, 1}` (`min_spacing_px = 2.05`). Tests pure physical fault-discovery lift over `CGO-88 (0.09042)`, `PHYS44 (0.10725)`, and `MDC-88 (0.14885)`.
3. **Experiment 2 (`H88-QTSK-DUAL` — Full De-Jittered `QTSK` + Fold-Visible Relay Fusion):** Fuses the de-jittered `[X_phys, X_qtsk, X_v22, d_over_w]` structural head with the de-jittered `[X_phys, X_qtsk]` blind head via `_fuse_log_odds` + axial strike-continuity smoothing (`1 px` along local multi-field structure-tensor strike) + exact Dinkelbach `{0, 1}`. Tests direct head-to-head `HOLDOUT-DTI` superiority over `H88-ADHR` (`n = 22,893`). Immediately audited against all `223` registry/sibling rasters for both pre-placement `|rho| <= 0.90` and 3-px dot overlap `<= 0.70`.
4. **Experiment 3 (`H88-QTSK-STRAT` — Completeness-Stratified Dual-Regime Allocation):** Uses the **exact same OOF dual-head posteriors from Experiment 2** (zero extra tree fits), replacing spatially constant `pi_unmapped = 0.50` with separate near-relay (`2.24 < d_vis <= 25 px`, `60%` dot budget) and blind-basin (`d_vis > 25 px`, `40%` dot budget) Dinkelbach fractional allocation (`min_spacing_px = 2.65`, `k_total ≈ 37,654` calibrated to the empirical `H33` budget, derived strictly from `fold["visible"]` in holdout and `grid.catalogue` in production). Tests simultaneous satisfaction of **223-raster like-for-like uniqueness (`<= 0.70` 3-px overlap, `<= 0.90` `|rho|`)**, **fleet blind-basin fingerprint (`share_le2 == 0`, `share_gt25 >= 0.35`)**, and **blind-basin `d_vis > 25 px` `HOLDOUT-DTI` (`n = 3,117`) + overall `HOLDOUT-DTI` (`n = 22,893`)**.

### Frozen Promotion & Emission Decision Rule
- **Emission Selection (among `Exp 1..3`, without tuning post-hoc):**
  - Emit the highest-`HOLDOUT-DTI` arm that **passes 223-raster uniqueness** (`max pre-placement |rho| <= 0.90` AND `max like-for-like 3-px dot overlap <= 0.70`) AND **passes the `share_le2 == 0` / `share_gt25 >= 0.35` blind-basin screen**; if `Exp 2` beats `H88-ADHR` (`paired 95% CI > 0`) AND passes 223-raster uniqueness (`<= 0.70`), compare `Exp 2` vs `Exp 3` transparently in the run card and emit the strictly non-duplicate arm with complete diagnostics on both.
- **Weekly-Slot Verdict Rule (`promote` vs `negative`):**
  - Under the repo's binding literal all-registry rule (`binding-literal-all-registry-v1`), `17GEMSDOE` (`5,167,373` positive footprint cells) forces literal forward 3-px overlap `= 1.0000 > 0.70` for **every** nonempty raster, AND Protocol Rule 6 states *"Do not pick submissions: promotion to a real slot is a separate selector step."* Furthermore, a weekly slot may only be recommended if a candidate **both** beats the overall `H88-ADHR` holdout bar (`paired 95% CI > 0`) **and** clears all uniqueness/fingerprint/portal gates. Any failure on any gate is reported honestly as `verdict: "negative"` (`DO NOT SUBMIT` without human selector override), never dressed up.
