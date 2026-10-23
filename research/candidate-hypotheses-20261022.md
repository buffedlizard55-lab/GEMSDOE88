# Ranked Candidate Geological Hypotheses — Verified Line-by-Line Audit (2026-10-22 UTC)

## Forensic Audit & Retraction Notice for PR #6 Band-Tag Errors (`IR-88-07` .. `IR-88-09`)

Direct inspection of `data/training_features.tif` (`SHA-256: 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`, `19` bands, `3730 × 3292`, `EPSG:32611`) caught and corrected three factual errors introduced in an earlier draft of this file (PR #6):

1. **`IR-88-07` — Zero Radiometric Channels Inside `training_features.tif`:** `training_features.tif` contains **zero** gamma-ray spectrometry bands. Band 6 is `tc` (magnetic tilt/curvature angle in `[2.95, 88.57]`, with `12` additional in-footprint `NaN` cells beyond the `3,061` perimeter sentinel mask), Band 10 is `deq_n100a15` (microseismic distance metric), and Band 16 is `ieq_n100a15` (earthquake cluster distance metric). Real USGS GeoDAWN airborne gamma-ray spectrometry (`K`, `Th`, `U`, `TC` and ratios `ThK`, `UK`, `UTh`, `TMI_up150`) resides in the separate SHA-pinned external rasters `data/external/geodawn_rad_u8.tif` (`SHA-256: c22420f7...`) and `data/external/geodawn_extensions_u8.tif` (`SHA-256: a35a9c6d...`).
2. **`IR-88-08` — Exact 19 On-Disk Band Tags Verified:** Every band in `data/training_features.tif` is referenced exclusively by its verified on-disk `band_name` tag:
   - **Magnetic (6):** `1: mag_anom`, `2: rtp`, `3: tmi_hg`, `6: tc`, `9: tmi_vg`, `14: tmi`
   - **Gravity (4):** `5: iso_grav_anom_slope`, `11: iso_grav_anom_vg`, `13: iso_grav_anom`, `18: iso_grav_anom_hg`
   - **Geodetic Strain (3):** `4: geod_2ndinv`, `7: geod_shearrate`, `8: geod_dilaterate`
   - **Seismicity (2):** `10: deq_n100a15`, `16: ieq_n100a15`
   - **Subsurface Architecture & Conductance (2):** `15: depth_to_base_surf`, `17: cond_surf`
   - **Detrended Topography (2):** `12: det_elev`, `19: det_elev_slope`
3. **`IR-88-09` — Physical Meaning of `cond_surf` and `iso_grav_anom_hg`:** Band 17 (`cond_surf`, `[0.194, 4.969]`) is regional magnetotelluric (MT) shallow log-conductance rather than high-resolution airborne EM, and Band 18 (`iso_grav_anom_hg`, `[-15.44, +12.86]`) is a **signed** directional horizontal gravity component, whereas Band 5 (`iso_grav_anom_slope`, `[0.0014, 0.6517]`) is the unsigned horizontal gravity gradient magnitude.

---

## Five Novel Candidate Hypotheses Ranked Prior to Modeling

All five hypotheses below were ranked before running `Exp 02` (`CGO-88`) and `Exp 03` (`H88-ADHR`) under the strict **3-experiment / 2-hour** protocol cap (`Exp 01 = MGC-88` archived baseline + `Exp 02 = CGO-88` + `Exp 03 = H88-ADHR`).

---

### Rank 1 (Selected Primary Candidate — Executed as `Exp 03`): `H88-ADHR` — Andersonian 60° Dip-Projected Basement Steps + Upslope-Advected Hydrothermal Plumes + Paleoshoreline-Decontaminated Multi-Scale Geomorphology

- **Exact Verified Layers Involved:**
  1. All 19 verified bands of `data/training_features.tif` (`mag_anom` B1, `rtp` B2, `tmi_hg` B3, `geod_2ndinv` B4, `iso_grav_anom_slope` B5, `tc` B6, `geod_shearrate` B7, `geod_dilaterate` B8, `tmi_vg` B9, `deq_n100a15` B10, `iso_grav_anom_vg` B11, `det_elev` B12, `iso_grav_anom` B13, `tmi` B14, `depth_to_base_surf` B15, `ieq_n100a15` B16, `cond_surf` B17, `iso_grav_anom_hg` B18, `det_elev_slope` B19).
  2. Official DOE GDR #1391 INGENIOUS public CC BY 4.0 datasets (SHA-256 pinned in `scripts/restore_inputs.py`):
     - `2m_temperature_probe_INGENIOUS_regional_data.zip` (`3,800` shallow 2 m probe stations, background-corrected `F2mDAB` and `T2m`);
     - `paleo_geothermal_regional.zip` (`709` Quaternary sinter, travertine, and silicified fault-breccia deposits);
     - `gdr_wellspring_in_footprint.csv` (`temp_c` and `geothermquartz_c` silica geothermometry; `dist_known_fault_px` column **explicitly excluded** to prevent catalogue leakage);
     - `gdr_volcanic_vents_in_footprint.csv` (`21` Quaternary volcanic vents);
     - `trace_segments_utm11.csv` (`84,331` INGENIOUS slip-sense segments restricted strictly to `fold["visible"]`).
  3. Official USGS GeoDAWN CC0 radiometric & upward-continued magnetic rasters: `geodawn_rad_u8.tif` (`K`, `Th`, `U`, `TC`) and `geodawn_extensions_u8.tif` (`ThK`, `UK`, `UTh`, `TMI_up150`).
  4. Official USGS 3DEP 1 m LiDAR scarp stack (`lidar_scarp_features_u8.tif`, covering `75.3%` of footprint with explicit `NaN` missingness routing outside LiDAR) plus full-footprint 10 m 3DEP topographic & fluvial $\chi$-$k_{sn}$ stacks (`topo_10m_derived_100m_u8.tif`, `dem10_chi_100m_i16.tif`).
- **Physical Signature & Mathematical Transform:**
  1. **Andersonian 60° Hanging-Wall Up-Dip Projection:** Planar normal faults dipping $\delta \approx 60^\circ$ through Cenozoic fill of thickness $z_{\text{base}}(x) = \max(0, \text{B15})$ produce their maximum basement density/susceptibility contrast horizontally displaced down-dip into the hanging wall along $\hat{u}_{\text{hw}}(x) = -\nabla g_{\text{iso}} / (\|\nabla g_{\text{iso}}\| + \varepsilon)$ by $\Delta x(x) = \operatorname{clip}(z_{\text{base}}(x) / \tan 60^\circ, 0, 16\text{ px})$. Bilinear back-projection (`scipy.ndimage.map_coordinates`) maps buried gravity/magnetic steps (`B5`, `B11`, `B3`, `B9`) and half-depth clay-cap edges (`|\nabla \text{cond\_surf}|` B17) back onto the true surface fault trace.
  2. **Topographically Up-Gradient Hydrothermal Deconvolution:** Buoyant geothermal fluids ascending blind permeable faults flow laterally down the water table ($\approx -\nabla z_{\text{dem}}$), displacing 2 m thermal probe anomalies (`F2mDAB`), hot springs, and silica/travertine aprons `0.6–1.5 km` down-slope into valley floors. Back-advecting the composite thermal/sinter anomaly upslope along $+\nabla z_{\text{dem}} / \|\nabla z_{\text{dem}}\|$ localizes the blind range-front/piedmont feeder fault.
  3. **Dual-Head Continuous-Kernel Expectation (`p*(u)`, `m*(x)`) + Exact Dinkelbach Allocation:** Directly regresses exact continuous triangular self-credit $m^*(x) = \mathbb{E}[\max_{g \in G} \max(0, 1 - d(x, g)/3) \mid X]$ (eliminating the $2\times\text{–}3\times$ binary `d <= 3` FP inflation), blends fold-proper structural relay/bend/damage-zone predictions with a **pure label-blind multi-physics head (`Head_phys`) in far-basin regimes (`d_cat > 15 px`)**, and allocates binary `{0.0, 1.0}` dots via unmodified `vendor/gems57/emit.py::dinkelbach_allocate`.
- **Why It Catches Faults Missing from USGS/INGENIOUS Catalogue:** Simultaneously recovers **(a)** blind hydrothermal feeder faults sealed under zero-relief playas/alluvial fans (`F2mDAB` + sinter + 60° basement step), **(b)** subdued Holocene piedmont scarps across **both** the `75.3%` 1 m LiDAR footprint and the `24.7%` non-LiDAR Great Basin gap (`10 m` breaklines + $\chi$-$k_{sn}$), and **(c)** unmapped en echelon relay ramps and horse-tail splays (`relay_bend_anatomy`).
- **Named Non-Fault Geological / Survey Mimics & Rejection Filters:**
  1. **Pleistocene Lake Lahontan (`~1,330 m`) & Lake Bonneville (`~1,555 m`) paleoshorelines:** Sharp constant-elevation wave-cut benches lacking basement offset or $\Delta k_{sn}$ channel steepness jumps — explicitly penalized by contour-elevation shoreline features (`pluvial_shoreline_pen`).
  2. **Evaporite playas & lateral thermal outflow plumes:** High flat interior `cond_surf` and valley-floor springs with zero basement step — suppressed by using `|\nabla \text{cond\_surf}|` edges plus upslope hydraulic convergence.
- **How It Differs from All Prior Repo & Sibling Lanes:** No sibling run combines 60° hanging-wall basement back-projection, upslope-advected GDR #1391 `F2mDAB` + paleo-sinter conduits, Lahontan/Bonneville shoreline decontamination across both LiDAR and non-LiDAR domains, direct continuous-kernel $m^*(x)$ calibration, and variable-budget Dinkelbach stopping.

---

### Rank 2 (Executed as `Exp 02` Pure Label-Blind Physics Benchmark): `CGO-88` — Competition-Stack 60° Dip-Offset Conductivity–Gravity–Magnetic Step Detector

- **Exact Verified Layers Involved:** Strictly the 19 verified bands of `data/training_features.tif` — **zero** external layers and **zero** catalogue-proximity features.
- **Physical Signature & Transform:** Multi-scale (`0.2, 0.8 km`) RTP & gravity horizontal/vertical derivatives, 60° hanging-wall back-projected gravity/magnetic steps (`B15` `depth_to_base_surf`), `|\nabla \text{cond\_surf}|` clay-cap edge & gravity cross-gradient (`B17 × B13`), crustal strain (`B4, B7, B8`), microseismic proximity (`B10, B16`), and detrended piedmont curvature (`B12, B19`), calibrated out-of-fold onto continuous `(p*, m*)` and emitted via `dinkelbach_allocate`.
- **Why Missing from Catalogue:** Isolates pure competition-stack discovery of buried range-front and intrabasin basement steps without any reliance on proximity to existing mapped traces.
- **Named Non-Fault Mimic:** Closed saline playas (high flat `cond_surf`) and unfaulted Paleogene pluton/caldera margins.
- **Role in Protocol:** Direct clean upgrade of `README.md`'s pre-declared `Next session` hypothesis (`MGC-88` 3-band local baseline $\to$ `CGO-88` 19-band dip-projected label-blind physics $\to$ `H88-ADHR` full geothermal/geomorphic/relay synthesis).

---

### Rank 3 (Deferred Beyond 3-Experiment Cap): `H88-3` — Potassic Alteration & Upward-Continued Magnetic Demagnetization Trough (`K/eTh × ΔTMI_150m`)

- **Exact Verified Layers:** `data/external/geodawn_rad_u8.tif` (`K`, `Th`, `U`), `geodawn_extensions_u8.tif` (`ThK`, `TMI_up150`), and `training_features.tif` (`rtp` B2, `depth_to_base_surf` B15).
- **Physical Signature:** Hydrothermal fluid flow alters magnetite to pyrite/hematite (`rtp - TMI_up150` negative short-wavelength trough) while enriching potassium adularia/illite (`K/Th` high).
- **Named Non-Fault Mimic:** Unfaulted high-silica alkali rhyolite tuffs and potassic playa deflations (~30 cm gamma-ray skin depth). Key `K/Th` and `TMI_up150` channels are already incorporated inside `H88-ADHR`.

---

### Rank 4 (Deferred Beyond 3-Experiment Cap): `H88-4` — Standalone Cross-Divide Fluvial $\chi$ & Normalized Channel Steepness ($k_{sn}$) Disequilibrium

- **Exact Verified Layers:** `dem10_chi_100m_i16.tif` (`step_max_x1000`, `ksn_max_m0.9`, `log10_area_m2_x1000`, `zmean_m`) and `topo_10m_derived_100m_u8.tif`.
- **Physical Signature:** Footwall uplift creates aligned `ksn` knickzones across adjacent drainage basins paired with cross-divide $\chi$ steps across the `24.7%` non-LiDAR Great Basin gap.
- **Named Non-Fault Mimic:** Resistant welded-tuff or Paleozoic carbonate caprock ledges; already integrated inside `H88-ADHR`'s full-coverage geomorphology block.

---

### Rank 5 (Deferred Beyond 3-Experiment Cap): `H88-5` — Transtensional Strain-Deficit & Microseismic Cluster-Tip Accommodation

- **Exact Verified Layers:** `training_features.tif` (`geod_2ndinv` B4, `geod_shearrate` B7, `geod_dilaterate` B8, `deq_n100a15` B10, `ieq_n100a15` B16) and `trace_segments_utm11.csv`.
- **Physical Signature:** Excess GPS dilatation + shear rate beyond slip accommodated by mapped faults, localized by `deq_n100a15` microseismic lineaments in Walker Lane transfer zones.
- **Named Non-Fault Mimic:** ~25 km GPS kriging footprints and geothermal reinjection swarms; low standalone 100 m localization accuracy compared to `H88-ADHR`.
