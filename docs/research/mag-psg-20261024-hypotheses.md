# Ranked Hypotheses for MAG-PSG Session — 2026-10-24

All 5 hypotheses target **concealed/unmapped faults indicative of geothermal fluid pathways** (never vents), specify exact verified input layers, name concrete non-fault mimics, and check free official source licensing before implementation. Ranked by expected DTI improvement vs implementation cost; top validated on buffered holdout.

## Rank 1 (Implemented) MAG-PSG — Magnetic Pseudogravity Phase Symmetry (deep basement)
- **Exact layers:** `training_features.tif` B02 `rtp` (RTP magnetics), B13 `iso_grav_anom`, B15 `depth_to_base_surf`, B04 `geod_2ndinv`, B18 `iso_grav_anom_hg` (5 bands, SHA 4371c82e…, zero radiometric channels inside training_features — verified band tags in `research/candidate-hypotheses-20261022.md` IR-88-07..09)
- **Physical signature / transform:** Frequency-domain pseudogravity `ℱ⁻¹{ℱ(RTP)/|k|}` (1/|k| low-pass) converts dipolar magnetic field to monopole-like potential; tilt angle `θ = atan(VDR/THDR)` zero-contours mark deep density/susceptibility contacts. Combined with RTP demagnetization trough (hydrothermal alteration destroys magnetite) and pseudogravity THDR ridge. Weights stratified by `depth_to_base` (0–2500 m clipped) to emphasize deep basement vs shallow volcanic noise.
- **Why catches missing:** Blind range-front normal faults dipping 60° offset basement 100s m horizontally under alluvium; no LiDAR scarp. Pseudogravity enhances deep long-λ basement steps suppressed in raw RTP by short-λ volcanic noise.
- **Non-fault mimic:** Shallow Miocene volcanic caldera rims, reversed-polarity basalt flows, and GeoDAWN 400 m flight-line leveling seams (documented in https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) produce high-frequency RTP lows without basement offset.
- **Differs:** No prior uses spectral pseudogravity; MRR used spatial block regression, CGO raw gradients, KTH K/Th ratios. First frequency-domain lane.
- **Cost:** Low (no external download, uses only provided 19 bands)
- **Expected DTI Δ:** Model [+0.02, −0.01 to +0.05] — tested: HOLDOUT 0.00576 vs ADHR 0.18788 = negative deliverable, retires approach.

## Rank 2 (Next) GGL-BH — Gravity-gradient lineaments over buried horsts
- **Layers:** B13 `iso_grav_anom`, B18 `iso_grav_anom_hg`, B05 `iso_grav_anom_slope`, B12 `det_elev` (+ B15 depth)
- **Signature:** Maxima of horizontal gradient magnitude `|∇ iso_grav|` + detrended elevation relief coincidence; multi-scale Hessian ridge (σ 1.2–5.0 km)
- **Why missing:** Horst-and-graben normal faults have large density contrast even if buried by shallow alluvium where USGS catalogue misses them; gravity sees basement step under cover.
- **Mimic:** Closed playa evaporite margins, perched saline aquifers, Paleogene pluton contacts (no fault-related strain or conductivity edge)
- **Differs:** Uses gravity HGM not magnetic; conditions on relief decile to reject playa interiors vs prior single-channel curvature.
- **Cost:** Low (provided bands only)
- **Expected DTI:** High (0.02–0.08) — strong prior: basin-bounding faults are density-driven.

## Rank 3 SEIS-RAD — Seismicity cluster + radiometric K depletion
- **Layers:** B10 `deq_n100a15` + B16 `ieq_n100a15` (INGENIOUS seismic density), external `geodawn_rad_u8.tif` K, `geodawn_extensions_u8.tif` ThK (SHA c22420f7…, a35a9c6d…), B12/B19 topography
- **Signature:** Microseismicity density peaks within 300 m of K-depletion trough (hydrothermal illitization washes K) — co-location test via kernel cross-correlation.
- **Why missing:** Small earthquakes pinpoint active slip on blind faults; K washout confirms fluid flow along structure vs lithologic contact.
- **Mimic:** Felsic tuff K-high, U roll-front placers, quarry blasts, flight-line radiometric stripes.
- **Differs:** First to couple external USGS ComCat (free official source https://earthquake.usgs.gov/fdsnws/event/1/) directly with radiometric alteration; prior lanes used only geometry/geophysics.
- **Cost:** Medium (need ComCat fetch via `scripts/fetch_optional_external_data.sh`, license free; verify AOI coverage first)
- **Expected DTI:** Very High (0.03–0.10) — active fault signal.

## Rank 4 NDVI-Edge — Vegetation lineament proxy
- **Layers:** Sentinel-2 L2A NDVI/NDMI (external, free), B12 det_elev, B19 det_elev_slope, curvature
- **Signature:** Linear sharp NDVI gradient aligned with topographic curvature break (groundwater upwelling along fault plane creates oasis contrast in arid Great Basin)
- **Why missing:** Basin-fill faults pool groundwater, enhancing vegetation despite no geophysical anomaly.
- **Mimic:** Irrigation ditches, riparian corridors, fence lines, roads, wildfire scars.
- **Differs:** Ecological/hydrological proxy vs pure geophysical; uses multispectral optical not in competition stack.
- **Cost:** High (need Sentinel-2 download, cloud mask, seasonal composite; verify AOI availability in Copernicus Data Space free tier)
- **Expected DTI:** Low-Medium (0.01–0.03)

## Rank 5 TIR-SI — Thermal-infrared anomaly at structural intersections
- **Layers:** Landsat Collection 2 night-time LST or ASTER TIR (external), strike junction density from fault trace geometry
- **Signature:** Night-time surface temperature anomaly (+1–3 K emissivity-corrected) at step-overs/intersections of predicted lineaments
- **Why missing:** Active geothermal upflow heats surface/emissivity even when no hot spring, marking active segment.
- **Mimic:** Solar aspect, albedo, soil moisture, wildfire, urban heat.
- **Differs:** Introduces direct thermal proxy + kinematic prior vs pure magnetics/scumps.
- **Cost:** High (need Landsat TIR atmospheric correction; verify USGS EarthExplorer free access and AOI night-time coverage)
- **Expected DTI:** Medium (0.01–0.04)

## Obtainability checks (before proposing viable)

- All Rank 1–2 layers are in pinned `training_features.tif` and external `geodawn_rad_u8` already restored (16/16 external files, SHA verified).
- Rank 3 ComCat: free official FDSN WS `https://earthquake.usgs.gov/fdsnws/event/1/` — example query `starttime=2010-01-01&endtime=2024-01-01&minlatitude=37&maxlatitude=42&minlongitude=-120&maxlongitude=-114&minmag=1&format=geojson` is obtainable (no login). Must check AOI completeness before implementation.
- Ranks 4–5 Sentinel-2/Landsat: free via Copernicus Data Space / USGS EarthExplorer, but AOI scene coverage, cloud fraction, and competition shareability not verified here — flagged as blockers.

## Preregistration

Frozen before experiment in `registry/preregistration_mag_psg.json` (date 2026-10-24, lane MAG-PSG, N_DOTS 37654, 1 experiment, budget 3/2h, canary ±0.90, |ρ| ≤0.90, overlap ≤0.70). No second experiment attempted after negative holdout.

