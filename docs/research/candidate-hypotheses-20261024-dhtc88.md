# 5 Candidate Geological Hypotheses for Geothermal-Indicative Fault Discovery (Lane H88-DHTC)

**Project:** GEMSDOE88 (DOE GEMS Challenge, DrivenData Competition 306)  
**Date:** 2026-10-24  
**Preregistration Record:** `registry/preregistration_dhtc88.json`  
**Official source links cited (not live-verified in the 2026-10-25 review):**
- USGS GeoDAWN Airborne Survey: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- INGENIOUS Geothermal Permeability Map: <https://gbcge.org/current-projects/ingenious/>
- DrivenData Data Specification: <https://www.drivendata.org/competitions/306/competition-doe-gems/data/>
- NLR GEMS Rules: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>

---

## Ranked Hypotheses Matrix

> **Evidence correction (2026-10-25):** the numeric “expected DTI gain” ranges in the original matrix were unsupported projections, not measurements or validated forecasts. They are withdrawn. H88-DHTC's recorded result is historical `HOLDOUT-DTI` only; it cannot be treated as an organizer score or as evidence of beating H33's owner-reported score. The current checkout has no `data/` directory, and the official pages were not fetched during this review. Geological interpretations below are hypotheses, not verified field evidence; confirm their source literature, layer metadata, transferability and mimics before treating them as supported.

$$\begin{array}{cllccc}
\hline
\textbf{Rank} & \textbf{ID} & \textbf{Geological Hypothesis} & \textbf{DTI evidence status} & \textbf{Implementation Cost} & \textbf{Selection Status} \\
\hline
\mathbf{1} & \textbf{H88-DHTC} & \textbf{Deep Hydro-Tectonic Conduit Conjunction} & \mathbf{\text{Not measured}} & \textbf{Low / Moderate} & \textbf{SELECTED (Primary Lane)} \\
2 & \text{H88-ASMR} & \text{Aeromagnetic Strike-Slip Transfer \& Relay} & \text{Not measured} & \text{Low} & \text{Candidate Queue} \\
3 & \text{H88-TEBL} & \text{Thermal-Elastic Boundary Layer \& Curvature} & \text{Not measured} & \text{Low} & \text{Candidate Queue} \\
4 & \text{H88-RADX} & \text{Radiometric Hydrothermal Alteration Redox} & \text{Not measured} & \text{Low} & \text{Candidate Queue} \\
5 & \text{H88-FLMV} & \text{Fluvial Knickpoint \& Chi-Gradient Deflection} & \text{Not measured} & \text{High} & \text{Previously tested / overlaps QTSK-88} \\
\hline
\end{array}$$

---

### Detailed Dossier for Candidate Hypotheses

### 1. H88-DHTC: Deep Hydro-Tectonic Conduit Conjunction (Top Candidate — Implemented)
- **Specific Layers Involved:**
  - `data/training_features.tif` Band 18 (`cond_10km`), Band 19 (`cond_32km`), Band 17 (`cond_surf`)
  - `data/training_features.tif` Band 04 (`iso_grav_anom`), Band 15 (`depth_to_base_surf`)
  - `data/training_features.tif` Band 07 (`geod_shearrate`), Band 08 (`geod_dilaterate`), Band 09 (`geod_secinv`)
  - `data/training_features.tif` Band 10 (`hf_mwm2`)
  - `data/external/geodawn_rad_u8.tif` Band 1 (`U_ppm`), Band 2 (`Th_ppm`)
- **Physical Signature Targeted:**
  - Conjunction of deep-crustal magnetotelluric (MT) electrical conductivity upwelling ($\Delta \log \sigma_{10\text{km} - 32\text{km}} > 0$), horizontal gradient of isostatic Bouguer gravity anomaly and basement depth step ($\sigma = 3.5\text{ px}$), and geodetic dilatational shear strain tensor product ($\dot{\gamma} \cdot \max(\dot{\Delta}, 0)$).
- **Why It Catches Faults Missing from USGS/INGENIOUS:**
  - The USGS Quaternary Faults and INGENIOUS surface catalogues are dominated by range-front normal faults displaying subaerial fault scarps. In the Great Basin, extensive valleys (e.g. Carson Sink, Dixie Valley, Buena Vista Valley) were submerged under pluvial Lake Lahontan, burying active fault scarps beneath thick lacustrine silts and playa clays. Deep hydrothermal fluid upwellings along blind basement faults continue to generate mid-crustal electrical conductivity anomalies, basement density offsets, and geodetic shear strains that are completely invisible in surface aerial/LiDAR surveys.
- **How It Differs from Existing Work in Repo:**
  - Prior lanes (MVRD, QTSK, TDKL, VESS) focused on surface scarps (`det_elev`, `lidar_scarp`) or upper-crustal magnetics. None combined deep MT conductivity slices (`B18`, `B19`) with basement density steps (`B04`, `B15`) and strain-dilation kinematics (`B07`, `B08`).
- **Named Non-Fault Mimic:**
  - Highly conductive shallow saline playa brines (e.g. Humboldt and Carson Sinks) and static non-tectonic lithological density contacts (e.g. Mesozoic granitic plutons juxtaposed against Paleozoic carbonates).
- **Data Source Verification:**
  - Prior research cites DOE GDR, USGS GeoDAWN survey, and INGENIOUS project data. These links were not live-verified in the 2026-10-25 review; this checkout has no `data/` directory, and current provenance/permissions must be re-established before use.

---

### 2. H88-ASMR: Aeromagnetic Strike-Slip Transfer & Relay Zone
- **Specific Layers:** `training_features.tif` B02 (`tmi_rtp`), B03 (`tmi_vg`), `geodawn_extensions_u8.tif` B4 (`tmi_up150`), `trace_segments_utm11.csv`.
- **Physical Signature:** Upward-continuation residual magnetic difference ($\text{TMI} - \text{TMI}_{150}$) combined with structural tensor orientation coherence to target cross-strike transfer faults.
- **Why It Catches Missing Faults:** Normal faults frequently terminate in complex strike-slip transfer or accommodation zones that accommodate differential extension. Strike-slip faults generate minimal vertical topographic scarp and are routinely omitted by surface mapping.
- **Difference:** Phase88 used isotropic cross-gradients; ASMR uses directional upward-continuation slicing aligned with regional Walker Lane strike-slip shear trends.
- **Mimic:** Paleochannel magnetic placers or Tertiary basaltic dike swarms.

---

### 3. H88-TEBL: Thermal-Elastic Boundary Layer & Curvature Hinge
- **Specific Layers:** `training_features.tif` B10 (`hf_mwm2`), B11 (`elev`), B12 (`det_elev`), B15 (`depth_to_base_surf`).
- **Physical Signature:** 2D spatial Laplacian ($\nabla^2$) of heat flow coupled with basement flexural curvature.
- **Why It Catches Missing Faults:** Active geothermal convective plumes create localized heat flow spikes and flexural bending of the brittle-ductile transition at basin hinges.
- **Difference:** Bypasses regional thermal gradients and extracts 2nd-derivative convective anomalies.
- **Mimic:** Conductive anomalies from topographic solar aspect or shallow groundwater irrigation wells.

---

### 4. H88-RADX: Radiometric Hydrothermal Alteration & Redox Disequilibrium
- **Specific Layers:** `geodawn_rad_u8.tif` B1–B4 ($U, Th, K, TC$), `training_features.tif` B13 (`slope`).
- **Physical Signature:** Mobile uranium disequilibrium ratio ($U/\text{Th}$) and potassic alteration index ($K/\text{Th}$) detrended against slope.
- **Why It Catches Missing Faults:** Hydrothermal fluids moving along fault damage zones precipitate potassium feldspar/adularia and transport mobile $U^{6+}$ complexes, leaving a spectral alteration halo around concealed fault conduits.
- **Difference:** Uses geochemical element ratios rather than raw counts.
- **Mimic:** Felsic volcanic tuffs or radioactive granitic wash gravels.

---

### 5. H88-FLMV: Fluvial Knickpoint & Chi-Gradient Deflection
- **Specific Layers:** `dem10_chi_100m_u8.tif`, `dem10_chi_100m_i16.tif`, `topo_10m_derived_100m_u8.tif`.
- **Physical Signature:** Stream-power $\chi$-gradient steps normalized by contributing drainage area.
- **Why It Catches Missing Faults:** Young fault scarps cause transient upstream knickpoints in river profiles before drainage networks reach steady state.
- **Difference:** Tested in QTSK-88; high compute requirement for interfluve interpolation.
- **Mimic:** Bedrock lithologic contacts and resistant quartzite/limestone ledges.
