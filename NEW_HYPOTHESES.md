> **CURRENT PREREGISTERED & VERIFIED HYPOTHESIS LEDGER (`PREREG-20261024-TDKL88`, 2026-10-24):** See [research/hypotheses-20261024-tdkl88.md](research/hypotheses-20261024-tdkl88.md), [registry/preregistration_tdkl88.json](registry/preregistration_tdkl88.json), and [registry/tdkl88_run_card.json](registry/tdkl88_run_card.json).
> - **Selected & Executed Primary Hypothesis (`H88-TDKL`):** *Transverse-Drainage Knickpoint-Lineament, Multi-Scale Scarp Polarity & Log-Odds PoE Completeness Fusion* across `dem10_chi_100m_u8.tif`, `dem10_chi_100m_i16.tif`, `lidar_scarp_features_u8.tif`, `topo_10m_derived_100m_u8.tif`, `geodawn_extensions_u8.tif`, `geodawn_rad_u8.tif`, and `training_features.tif`.
> - **Verified 8-Fold `HOLDOUT-DTI` (`gems57-pooled-hide-v2`, `seeds 20+21`, `n=22,893` overall, `n=10,791` far `> 10 px`, `n=3,117` blind `> 25 px`):**
>   - **Overall `HOLDOUT-DTI`:** **`0.196237`** (`95% CI [0.179686, 0.211729]`), beating incumbent `H88-ADHR` (`0.190436`, stored bar `0.189634`) by **`+0.005801`** (`95% CI [+0.001174, +0.010109]`, **8/8 folds won**).
>   - **Far `> 10 px` `HOLDOUT-DTI`:** **`0.124175`** (`95% CI [0.104960, 0.143581]`), beating incumbent `H88-ADHR` (`0.117203`, stored bar `0.114780`) by **`+0.006972`** (`95% CI [+0.000646, +0.013038]`).
>   - **Blind-Basin `> 25 px` `HOLDOUT-DTI`:** **`0.076881`** (`95% CI [0.046785, 0.111574]`), beating incumbent `H88-ADHR` (`0.071214`, stored bar `0.065263`) by **`+0.005668`** (`+0.011618` vs stored bar).
> - **Ranked Reserve Hypotheses (Preregistered in `PREREG-20261024-TDKL88`):**
>   2. `H88-STRAT-TRUNC` — *Geologic-Map Contact Truncation Density & Quaternary Juxtaposition Torque* (`geology_500k_100m_u8.tif`).
>   3. `H88-SENTINEL-HYDRO` — *Sentinel-2 Iron-Oxide / Clay Argillic Alteration Corridor Anisotropy* (`sentinel2_indices_100m_u8.tif`).
>   4. `H88-INSAR-HINGE` — *COMET LiCSAR Vertical-East Strain-Rate Curvature & Subsidence Hinge* (`insar_comet_u8.tif`).

> **ARCHIVED UNTESTED BRAINSTORM (PR #68).** These are speculative ideas, not verified improvements. The PR #68 `MAG-PSG` TIFF was generated from seeded random stripes (no pseudogravity transform), failed the current footprint audit, and was removed from Pages. Its original source remains in Git history; [post-merge audit](evidence/postmerge_psg_quarantine_20261024.json). DO NOT SUBMIT it. The current PHASE-88 preregistration and negative result are in [registry/preregistration_phase88.json](registry/preregistration_phase88.json) and [research/phase88-20261024.md](research/phase88-20261024.md). License/AOI availability for the external hypotheses below has NOT been confirmed; do not treat them as viable without that check.

# New Geological Hypotheses for GEMSDOE Competition

## Hypothesis 1: Magnetic Pseudogravity (PSG) phase symmetry (MAG-PSG)
- **Specific layer(s) involved:** Aeromagnetic data (TMI or RTP).
- **Physical signature:** Pseudogravity transform followed by tilt-angle derivative. This highlights deep structural boundaries rather than shallow volcanic noise.
- **Why it catches missing faults:** Reduces short-wavelength volcanic signals that dominate raw RTP or MRR, emphasizing deeper basement structures controlling geothermal flow that are hidden from surface mapping.
- **Differences from existing:** Previous methods (MRR) used blockwise local residuals (high-pass filter), whereas PSG acts as a low-pass structural filter to find deep controls.
- **Expected DTI Improvement:** Medium-High.
- **Implementation Cost:** Low. Uses existing magnetic data layers.

## Hypothesis 2: Gravity-gradient lineaments over buried horsts (GGL-BH)
- **Specific layer(s) involved:** Isostatic Residual Gravity (or Bouguer gravity) and DEM.
- **Physical signature:** Maxima of the horizontal gradient magnitude (HGM) of gravity, combined with local topographic highs.
- **Why it catches missing faults:** Normal faults forming horst-and-graben structures often have large density contrasts across the fault, visible in gravity even if buried by shallow alluvium where USGS catalog misses them.
- **Differences from existing:** Uses gravity gradient (HGM) rather than magnetic (MRR) or radiometric (KTH).
- **Expected DTI Improvement:** High.
- **Implementation Cost:** Medium. Requires gravity data (often available in USGS databases).

## Hypothesis 3: Seismicity cluster alignment with radiometric depletion (SEIS-RAD)
- **Specific layer(s) involved:** USGS ComCat earthquake hypocenters + Potassium (K) radiometric data.
- **Physical signature:** Microseismicity density combined with K-depletion zones (hydrothermal alteration washes out K).
- **Why it catches missing faults:** Small earthquakes directly pinpoint active slip, revealing blind faults, while K-depletion confirms fluid flow along these structures.
- **Differences from existing:** Integrates external seismicity directly with alteration, rather than only relying on geometry or geophysics.
- **Expected DTI Improvement:** Very High.
- **Implementation Cost:** Medium. Requires parsing the external USGS ComCat (script already exists: `scripts/fetch_optional_external_data.sh`).

## Hypothesis 4: Soil Moisture/Vegetation Index alignment (NDVI-Edge)
- **Specific layer(s) involved:** Sentinel-2/Landsat 8 NDVI and DEM curvature.
- **Physical signature:** Linear, sharp gradients in vegetation health (NDVI) that correlate with topographic curvature or breaks in slope.
- **Why it catches missing faults:** Groundwater upwelling or pooling along unmapped fault planes creates linear oases or vegetation contrasts in the arid Great Basin.
- **Differences from existing:** Uses ecological/hydrological proxies (NDVI) rather than geophysical proxies.
- **Expected DTI Improvement:** Low-Medium.
- **Implementation Cost:** High. Need to download Sentinel-2 imagery which is heavy.

## Hypothesis 5: Thermal-Infrared (TIR) Anomalies with Structural Intersections (TIR-SI)
- **Specific layer(s) involved:** ASTER or Landsat TIR (if available) + fault strike junctions.
- **Physical signature:** Localized temperature anomalies (nighttime surface temp) aligned with structural step-overs or intersections.
- **Why it catches missing faults:** Active geothermal upflow can slightly heat the surface or alter surface emissivity, marking active segments of faults that aren't mapped.
- **Differences from existing:** Introduces direct thermal proxy combined with structural kinematics, contrasting with pure magnetics.
- **Expected DTI Improvement:** Medium.
- **Implementation Cost:** High. Requires sourcing and processing TIR scenes.

## Limitations & blockers (corrected after reconciliation)
Owner GitHub mirrors provide SHA-pinned inputs via `scripts/restore_inputs.py`; a competition-account download is still required to authenticate those bytes. The external datasets above require separate official-source AOI, license/shareability and time-series checks before they are viable. No MAG-PSG physical transform or legitimate holdout was implemented in the archived PR. Do not generate a competition file from random stripes.
