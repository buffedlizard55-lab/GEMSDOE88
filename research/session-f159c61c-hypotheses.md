# H88 — Five New Geological Hypotheses for Session f159c61c (2026-10-27)

> **Lane-invariant requirement.** Each hypothesis below is **PROPOSED_UNTESTED** for this session: no holdout was run, no TIFF was promoted, `DUPLICATE_STOP` remains binding. No numerical DTI projection is claimed. Expected DTI improvement is qualitative (+ small/medium/large **uncertain**) relative to the saturated H33 pruning lineage (`0.2778` USER-REPORTED, not an organizer receipt). All use SHA-pinned local inputs only unless explicitly flagged as requiring free external government data. Each has been grep-verified against `src/gems88/` and all 92 GEMSDOE sites — none duplicates an already-evaluated lane.

## Ranked Hypotheses

### 1. H88-KPSF — Knickpoint Polarity-Sum Fault vs Fluvial Autogenic Null
- **Lane title:** Knickpoint Polarity-Sum Fault (KPSF)
- **Specific layer(s) involved:**
  - `data/training_features.tif` bands **B12 `det_elev`** + **B19 `det_elev_slope`** (100 m DEM elevation and slope)
  - `data/external/dem10_chi_100m_u8.tif` bands **B01 `chan_n`** + **B04 `valid_n`** (channel network and valid mask) + `data/external/dem10_chi_100m_i16.tif` `chi` channel
  - `data/external/lidar_scarp_features_u8.tif` bands **B03 `step_max`**, **B10 `coh100`**, **B11 `strike`**, **B12 `valid`** (1 m LiDAR-derived scarp indices, where `lsc_coverage > 0`)
  - `data/external/topo_10m_derived_100m_u8.tif` bands **B08 `hs_lineament`**, **B09 `dem_mean`** (10 m topo hillshade lineament and DEM mean resampled to 100 m)

- **Physical signature being targeted:** Signed knickpoint polarity-sum along chi-ordered channels: fit concave `chi`-elevation profiles per drainage basin, detect paired positive-plus-negative knickpoints (upstream-facing step `+Δz` immediately followed by downstream-facing step `-Δz`) aligned orthogonal to basin axis within 300 m. Score = sum of signed step amplitudes weighted by channel steepness `k_sn` anomaly, requiring spatial repeat across ≥2 independent tributaries draining same interfluve.

- **Why it should catch a fault missing from USGS/INGENIOUS catalogue rather than one already in it:** USGS/INGENIOUS fault traces are dominated by range-front scarps and piedmont fault segments mapped from surface geomorphology and prior field maps. A buried blind fault beneath alluvium or a recently abandoned splay off the main trace may produce no continuous scarp but still offset active channel long-profiles at multiple crossings, generating polarity-sum knickpoint pairs invisible on hillshade alone. Existing catalogue features are excluded by `dist_known_fault_px` buffering (≥2.8 px) during surface construction — no mapped trace seeds the surface. This complements H33's ridge-thinning logic which saturates at B2.

- **How it differs from anything already implemented:** LSC-88 uses isolated LiDAR step height; TDKL uses knickpoint + polarity Poisson emission but not chi-profile inversion or polarity-sum; SHORE-EVEN conditions on shoreline isohypses not fluvial chi. No prior lane fits `chi`-concave equilibrium profiles and tests polarity-sum vs an autogenic fluvial null (lithologic knickpoints, debris-flow fans). TDkl/Provcrest use product-of-experts ranking, not chi-restoration likelihood.

- **Named non-fault process that could mimic it:** Lithologic contacts (resistant bedrock sills) and Pleistocene Lake Lahontan shoreline notches that generate single-polarity knickpoints without fault offset; also anthropogenic diversions.

- **Rank rationale:** Expected DTI improvement **+ Medium (uncertain)** — channel network covers 68% of footprint per `manifest.json`, knickpoints are independent of potential-field pluton confounders. Implementation cost **Medium** (cached inputs only, chi decoding requires manifest lookup, profile fitting per basin).

---

### 2. H88-BASS — Basement Antithetic Strain-Softening Corridor
- **Specific layer(s) involved:**
  - `data/training_features.tif` bands **B13 `iso_grav_anom`** (complete Bouguer), **B15 `depth_to_base_surf`** (depth-to-basement from gravity inversion), **B17 `cond_surf`** (apparent conductivity), **B18 `base_edge`** (basement edge indicator)
  - `data/external/topo_10m_derived_100m_u8.tif` band **B01 `slope_10m`** and **B02 `curvature_10m`**
  - `data/bridge/existing_faults.tif` buffered distance transform (used only for masking, not as feature)

- **Physical signature:** Basement antithetic graben-doublet: narrow (200–600 m) symmetric Bouguer gravity trough (`Δg ≈ -2 to -5 mGal`) coinciding with local basement depth depression and conductivity high, with paired antithetic dips inferred from opposing curvature signs on 10 m DEM. Target is a buried graben floor (down-dropped block) bounded by two sub-parallel normal faults 400–1200 m apart — a classic Basin-and-Range intra-basin accommodation structure.

- **Why blind:** Such intra-basin grabens are below seismic resolution and have no surface scarp (alluvium thickness 200–800 m per B15). USGS catalogue maps only the bounding range-front faults, not intrabasinal second-order structures. Excluding `d_cat ≤ 25 px` (2500 m) collar around catalogue during training forces detection in true blind basins (`frac_gt25 ≈ 40%` of H33's dots, monotonic score driver per session-d634de37 forensic).

- **Difference:** GTHC-88 uses basement edge steps (single boundary), not paired antithetic troughs; TMA uses magnetic azimuth rotation; BPWD uses pseudogravity worms (2D FFT upward continuation). No prior lane fits symmetric double-edge gravity curvature. MVRD uses redox-strand, not basement depth doublet.

- **Non-fault mimic:** Paleochannel incised-valley fill (U-shaped Bouguer low without bounding faults) and volcanic caldera ring-fractures.

- **Rank:** **+ Medium-Large (uncertain)** — intrabasinal faults are the known under-represented class (Siler et al. 2019 GRL). Cost **Medium-High** (requires 2D curvature tensor fitting, basement inversion validation).

---

### 3. H88-CURV — Cross-Scale Magnetic Curvature Tensor Fault Node
- **Specific layer(s) involved:**
  - `data/training_features.tif` bands **B01 `mag_tilt`**, **B02 `mag_rtp`**, **B03 `mag_as`**, **B06 `mag_worm`**, **B07 `mag_tilt_zero`** (magnetic transforms at 100 m)
  - `data/training_features.tif` band **B09 `rad_K`**, **B11 `rad_Th`** (radiometric K, Th channels, quantized U8 indices — treated as rank features, not physical ratios)
  - `data/external/geodawn_rad_u8.tif` bands 1–3 (K,Th,U) for cross-validation

- **Physical signature:** Normalized magnetic curvature tensor eigenvalues: compute Hessian of RTP field, extract plan-curvature `k_plan = (λ1·λ2)/(λ1²+λ2²)` and profile curvature, require orthogonal curvature sign flip (ridge-to-valley) persistent across 200 m and 800 m upward-continuation scales (Guspi multi-scale operator). Fault indicator = 2D lineament where `k_plan` crosses zero with co-located RTP-analytic signal ridge, and radiometric K shows no coincident intrusive high.

- **Why blind:** Deeply buried faults (depth > 500 m to magnetic source, B16) produce no surface scarp but retain magnetic susceptibility contrast across basement offset; USGS catalogue misses faults under basalt cover (Lunar Crater volcanic field) and thick alluvium. Potential-field gradients are the only signal in blind zones.

- **Difference:** BPWD uses Baranov pseudogravity + worm back-projection but not curvature tensor invariants; HGVC uses tilt-gradient vorticity; PGTD uses harmonic tensor dimension; MFS uses multifractal spectra. None compute `k_plan` zero-crossings multi-scale.

- **Non-fault mimic:** Dike swarms (magnetic lineaments with curvature but no through-going fault) and cultural magnetic noise (fences, pipelines) — distinguished by requiring 800 m persistence.

- **Rank:** **+ Small-Medium (uncertain)** — curvature is noise-sensitive, requires careful continuation taper. Cost **Medium** (cached inputs only, FFT derivatives).

---

### 4. H88-LGOF — LiDAR-Gap Geothermal Outflow Fingerprint (Isotonic Transfer)
- **Specific layer(s) involved:**
  - `data/external/lidar_scarp_features_u8.tif` band **B12 `valid`** (binary coverage mask: 75.37% covered, 24.63% gap)
  - `data/training_features.tif` bands **B12 `det_elev`**, **B13 `iso_grav_anom`**, **B15 `depth_to_base_surf`**, **B17 `cond_surf`**
  - DOE GDR 1391 resources: `2m_temperature_probe_INGENIOUS_regional_data.zip` (1.03 MB, CC BY 4.0) and `gdr_wellspring_in_footprint.csv` (well/spring locations)
  - `data/external/topo_10m_derived_100m_u8.tif` band **B08 `hs_lineament`**

- **Physical signature:** Isotonic-calibrated LiDAR-gap transfer: in LSC-covered cells (75%), learn mapping `f: (B12,B13,B15,B17) → LSC_step_score` via isotonic regression (monotone, no leakage). Transfer `f` to 24.63% LiDAR-gap cells to predict subsurface scarp likelihood from potential-field proxies. Independently, compute hydraulic outflow finger: downslope `MFD` flow accumulation from predicted blind-fault lineament, require coincidence of predicted fault + thermal probe temperature anomaly >2σ within 500 m downslope.

- **Why blind:** LiDAR gap coincides with basin interiors (alluvium, playas) where blind faults are most likely — current LiDAR-only detectors (LSC-88) cannot see there. Gap transfer exploits that basin-fill faults still have gravity/conductivity expression. Hydraulic outflow back-projection adds independent thermal corroboration not used in prior lanes.

- **Difference:** LSC-88 thresholds LiDAR directly; TDKL combines LiDAR+knickpoint but not gap transfer; CTRA uses conductivity curvature not hydraulic flow; VESS uses vapor-vent proximity not outflow. No prior lane does isotonic gap-transfer + outflow back-projection.

- **Non-fault mimic:** Groundwater discharge along unfaulted permeable alluvial fans (produces thermal anomaly without fault offset) — vetoed by requiring gravity-bounding.

- **Rank:** **+ Medium (uncertain), high implementation value** — directly addresses 24.63% data-gap bias. Cost **Medium-High** (requires 2 m probe data licensing check, isotonic calibration, flow routing).

---

### 5. H88-3DEP-INSAR — USGS 3DEP 1 m DEM + NASA OPERA InSAR Joint Graben Doublet
- **Specific layer(s) involved:**
  - **External free public data (CC0 + open):**
    - USGS 3DEP 1 m DEM tiles via `1m_DEM_links.csv` (competition-provided, https://www.usgs.gov/3d-elevation-program) — 1 m lidar-derived elevation COGs, UTM 11N, `CC0` public domain
    - NASA OPERA `DISP-S1` InSAR displacement velocity (Sentinel-1, https://www.jpl.nasa.gov/missions/opera, open) — line-of-sight velocity gradient
    - DOE GDR 1391 3D MT resistivity volumes (if available, CC BY 4.0)
  - `data/training_features.tif` band **B15 `depth_to_base_surf`** for basin context masking

- **Physical signature:** Directional wavelet-packet antithetic graben-doublet on 1 m DEM: apply 2D Morlet wavelet-packet decomposition to 1 m DEM, detect sub-meter scarplets (5–30 cm throw) as coherent wavelet coefficients with opposite polarity on paired lineaments 100–800 m apart, oriented antithetically (conjugate normal faults). Require persistent InSAR velocity gradient step (≥1 mm/yr LOS across doublet) indicating active interseismic creep or poroelastic deformation — distinguishing tectonic scarps from terrace risers.

- **Why blind:** USGS/INGENIOUS catalogue resolution is ~100 m (field maps, 10 m DEM hillshade); sub-meter scarplets in basin alluvium are below detection but resolvable in 1 m LiDAR and InSAR. Current lanes use 100 m cache only (10 m resampled to 100 m), losing sub-pixel faulting. Basin-center faults in thick alluvium have subtle surface expression only visible at ≤1 m.

- **Difference:** No prior lane uses 1 m 3DEP or InSAR — all use 100 m cached features. 3DEP-SCARP proposal in prior session hypothesized 1 m wavelet but not joint InSAR antithetic velocity gating. This adds InSAR line-of-sight strain as independent kinematic confirmation.

- **Non-fault mimic:** Fluvial terrace risers (single-polarity steps following paleochannel contours, not antithetic pairs) and InSAR atmospheric artifacts (turbulent tropospheric delay mimicking velocity steps) — filtered by requiring antithetic pair + basin-normal gravity signal.

- **Rank:** **+ Large (uncertain), highest long-term ceiling** — but **External data required** (3DEP COG tiling ~2 TB for study area, OPERA DISP-S1 requires Earthdata auth, host is outside sandbox allowlist: `BLOCKED` here). Cost **High** (external fetch, tera-scale tiling, InSAR atmospheric correction, wavelet inversion). Flagged before proposing as viable per protocol: obtainable via `https://apps.nationalmap.gov/downloader` (3DEP) and `https://cmr.earthdata.nasa.gov` / `https://asf.alaska.edu` (OPERA) — free, public, but not retrievable in this sandbox egress policy.

---

## Ranking Summary

| Rank | ID | Expected DTI improvement (uncertain) | Implementation cost | External data | Falsification |
|------|----|--------------------------------------|---------------------|---------------|---------------|
| 1 | H88-KPSF | + Medium | Medium | No | Reject if knickpoint polarity-sum vanishes when drainage-masked or matches lithologic-sill null |
| 2 | H88-BASS | + Medium-Large | Medium-High | No | Reject if gravity trough matches paleochannel depth without bounding fault curvature |
| 3 | H88-CURV | + Small-Medium | Medium | No | Reject if curvature persistence <2 scales or coincides with K-intrusive |
| 4 | H88-LGOF | + Medium | Medium-High | No (local probe CSV is already mirrored) | Reject if isotonic transfer AUC ≤0.5 on held-out LSC-covered folds or thermal anomaly explains lithology |
| 5 | H88-3DEP-INSAR | + Large | High | **Yes — 3DEP + OPERA** | Reject if 1 m scarplet vanishes under InSAR atmospheric correction or appears only on terrace risers |

> **Validation gate before weekly slot (per protocol):** The top candidate (H88-KPSF) must be validated on the spatially-blocked holdout (`gems57-pooled-hide-v2`, 8-fold hide-and-recover with whole-fault-segment withholding + buffer, catalogue features derived only from visible faults, visible faults pixel-masked, pooled DTI α=0.2 β=0.8 300 m triangular kernel). Each feature-alone leakage canary must score AUC ≤0.90. Only if paired HOLDOUT-DTI delta vs same-fold incumbent is >0 with 95% CI not crossing zero does the lane advance to selector. Budget 3 experiments / 2 h. This dossier is **not** a submission.

## Source Verification (line-by-line, no hallucinations)

- Competition metric DTI α=0.2 β=0.8 300 m triangular: [DrivenData Mathematical Representation](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#mathematical-representation)
- Submission format EPSG:32611 3730×3292 100 m: [NLR FY26 Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) and [DrivenData Reference Solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- GeoDAWN survey CC0, 200/400 m line spacing: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)
- GDR 1391 2 m probe CC BY 4.0: [GDR 1391](https://gdr.openei.org/submissions/1391) and direct zip link verified OFFICIAL-READ
- USGS 3DEP 1 m program CC0: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) and competition `1m_DEM_links.csv`
- NASA OPERA DISP-S1: [JPL OPERA](https://www.jpl.nasa.gov/missions/opera) (requires Earthdata auth, BLOCKED in sandbox per egress allowlist)
- LiDAR coverage 75.37% / gap 24.63%: measured from `lidar_scarp_features_u8.tif` valid mask via `scripts/restore_inputs.py` manifest (local byte-check, not organizer-authenticated)

