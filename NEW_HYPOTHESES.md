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

## Limitations & Blockers
**Current Limitation:** We are unable to download the core competition data directly from DrivenData (`training_features.tif`, `labels.tif`, `sample_submission.tif`) due to the requirement for authentication (❌ No DrivenData auth). Furthermore, the provided Dropbox links are blocked by the environment's firewall (only specific outbound connections are allowed, e.g., GitHub, PyPI, npm). 
**Required Access:** We need a machine with unrestricted internet access or valid DrivenData credentials injected as environment variables (or pre-downloaded data in the `data/` directory) to run the full training pipeline using `scripts/prepare_data.py`.
