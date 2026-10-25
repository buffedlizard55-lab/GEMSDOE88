# 5 Candidate Geological Hypotheses for Geothermal-Indicative Fault Discovery — Lane H88-XGCE (2026-10-25)

**Project:** GEMSDOE88 (DOE GEMS Challenge, DrivenData Competition 306)
**Lane:** H88-XGCE — Cross-Gradient Orthogonal Conduit Extraction
**Date:** 2026-10-25
**Preregistration:** `registry/preregistration_xgce88.json` (frozen before any holdout access)
**Official Data Sources Verified (no new external download, all on disk):**
- USGS GeoDAWN airborne magnetic & radiometric: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS Great Basin Permeability: https://gbcge.org/current-projects/ingenious/
- DrivenData competition spec: https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- NLR GEMS Rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- EPSG:32611: https://epsg.io/32611
- Tversky/DTI definition: https://en.wikipedia.org/wiki/Tversky_index

---

## Ranked Matrix

| Rank | ID | Hypothesis | Relative research priority (not a score projection) | Cost | Status |
|------|----|------------|-------------------------|------|--------|
| **1** | **H88-XGCE** | **Cross-Gradient Orthogonal Conduit Extraction (gravity × magnetic intersections weighted by dilation)** | High-priority hypothesis; outcome unvalidated | **Low** | **SELECTED, but negative/UNSCORED** |
| 2 | H88-RADM | Radiometric Alteration Demagnetization Corridor (K/Th + U/Th + magnetic low) | Moderate-priority hypothesis; untested | Low | Queue |
| 3 | H88-SLIP | Slip & Dilation Tendency Orientation Filter (SHmax-resolved) | Moderate-priority hypothesis; untested | Low-Mod | Queue |
| 4 | H88-THCL | Thermal Conductivity Lateral Contrast (10 km vs 32 km MT) | Lower-priority hypothesis; partly overlaps tested DHTC | Low | Queue |
| 5 | H88-CHIK | Coupled Chi-Knickpoint + Curvature Step (10 m DEM fluvial) | Lower-priority hypothesis; overlaps TDKL/QTSK methods | High (external DEM tiling) | Queue |

---

### 1. H88-XGCE — Cross-Gradient Orthogonal Conduit Extraction (SELECTED)

- **Specific layers:** `training_features.tif` Band 3 `tmi_hg` (Total magnetic intensity horizontal gradient), Band 9 `tmi_vg` (vertical gradient), Band 18 `iso_grav_anom_hg` (isostatic gravity hg), Band 11 `iso_grav_anom_vg` (vg), Band 15 `depth_to_base_surf`, Band 8 `geod_dilaterate` (volumetric strain rate), Band 7 `geod_shearrate`, Band 5 `iso_grav_anom_slope`, Band 12 `det_elev` (for mask only).
- **Physical signature:** Normalized cross-gradient magnitude `|G_grav × G_mag| / (|G_grav||G_mag|+ε) = |sin Δθ|` plus gravity basement-step ridge magnitude. Orthogonal intersections where NW-striking Basin-and-Range normal faults are cross-cut by NE-striking Walker Lane transfer faults produce 90° gradient discordance; these damage-zone intersections have 10–100× permeability enhancement via fracture connectivity (Barton & Zoback 1994; Faulds et al. 2021).
- **Why it catches faults missing from USGS/INGENIOUS:** Catalogue mappers trace continuous linear scarps; intersections are often buried under Quaternary alluvium/fan confluences and lacustrine silts (Lahontan basin fill) with no single through-going scarp. Cross-gradient detects the basement density/magnetization offset even when surface expression is a broad fan, not a sharp scarp.
- **How it differs:** No prior GEMSDOE88 lane computes `grav × mag` cross-gradient. MGC-88 used raw cross-gradient without normalization; QTSK used cover-step + chi; DHTC used deep conductivity + basement step but not magnetic cross-cutting; VESS used Frangi vesselness; TDKL used knickpoints. XGCE uniquely isolates *orthogonal* intersections.
- **Named non-fault mimic:** Mesozoic granitic pluton margins (circular gravity/magnetic anomalies produce high cross-gradient on rims) and Tertiary volcanic caldera ring faults. Suppressed via 2.5 km high-pass on `depth_to_base_surf` and requiring dilatational strain > 0 (extensional quadrant).

### 2. H88-RADM — Radiometric Alteration Demagnetization Corridor

- **Layers:** `geodawn_rad_u8.tif` Bands U, Th, K, TC (radiometric), `training_features.tif` Bands 2 `rtp`, 3 `tmi_hg`, 12 `det_elev`, 13 `iso_grav_anom`.
- **Signature:** Potassic alteration index `K/Th` detrended by slope + uranium mobility `U/Th` + magnetic analytic-signal low bounded by tilt zero-crossings.
- **Why missing:** Hydrothermal K-feldspar/adularia halos are 200–500 m wide, below air-photo resolution, and do not create topographic scarp.
- **Difference:** No prior lane uses ratioed radiometric indices; prior lanes used raw magnetic or gravity only.
- **Mimic:** Felsic tuff outwash and granitic wash.

### 3. H88-SLIP — Slip & Dilation Tendency Orientation Filter

- **Layers:** `training_features.tif` Bands 7 `geod_shearrate`, 8 `geod_dilaterate`, 12 `det_elev`, 2 `rtp`, 4 `iso_grav_anom`, `trace_segments_utm11.csv` (regional SHmax azimuth proxy).
- **Signature:** Infer local strike from combined magnetic/topographic structure tensor, resolve regional `SHmax` onto strike to compute normalized dilation tendency `T_d = (σ1-σn)/ (σ1-σ3)` gating cross-gradient crests.
- **Why missing:** Permeable faults are those at ~30° to SHmax; unfavorably oriented faults are sealed. Mappers do not filter by stress.
- **Difference:** Introduces stress-tensor mechanics; prior lanes used scalar strain invariants only.
- **Mimic:** Critically oriented dike swarms without shear.

### 4. H88-THCL — Thermal Conductivity Lateral Contrast

- **Layers:** `training_features.tif` Bands 17 `cond_surf`, 18 `cond_10km`, 19 `cond_32km`, 15 `depth_to_base_surf`, 10 `hf_mwm2`.
- **Signature:** Normalized deep-shallow conductivity contrast `(logσ10 - logσ32) / (logσ10+logσ32)` sharpened by basement-step gradient.
- **Why missing:** MT inversion is smooth (5–10 km); gravity step localizes upwelling at basin margins under thick cover.
- **Difference:** DHTC used absolute conductivity upwelling, not contrast.
- **Mimic:** Shallow saline playa brines.

### 5. H88-CHIK — Coupled Chi-Knickpoint + Curvature Step

- **Layers:** `dem10_chi_100m_u8.tif`, `topo_10m_derived_100m_u8.tif` Band slope/curvature, `training_features.tif` Band 12 `det_elev`.
- **Signature:** Normalized χ-gradient steps across ≥3 parallel washes gated by cross-slope fan curvature asymmetry.
- **Why missing:** Ephemeral washes are erased by pluvial lake silts; knickpoints persist in longitudinal profiles.
- **Difference:** QTSK tested χ but with different normalization; CHIK adds area-normalized χ and interfluve curvature.
- **Mimic:** Resistant quartzite ledges.

---

## Selection Rationale

XGCE ranked first because: (a) orthogonal fault intersections are first-order geothermal loci (Faulds et al., GRC 2021: >70% of Nevada geothermal systems at stepovers/intersections); (b) uses only on-disk 19-band stack, no external DEM tiling (low cost, deterministic); (c) directly addresses the catalogue bias (mappers under-represent cross-cutting transfers); (d) cross-gradient `|sinΔθ|` is invariant to absolute amplitude, suppressing pluton rims via dilation gate; (e) prior holdout proxies show gravity/magnetic lineament density correlates with SGMC-off-catalogue recall (ρ≈0.52 in 19GEMSDOE early rasters).

All five are implementable without new login-gated downloads; external options (CHIK) require only already-restored 10 m DEM derivatives.
