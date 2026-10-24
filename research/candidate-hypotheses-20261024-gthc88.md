# Pre-Implementation Candidate Geological Hypotheses (`GEMSDOE88` — 2026-10-24)

**Status:** Frozen before implementation and spatially-blocked holdout execution  
**Evaluator locked:** `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, $\alpha=0.2, \beta=0.8$, 300 m triangular kernel, 8 buffered whole-component folds across `seed=20` and `seed=21`, $N_{\text{all}}=22{,}893$ withheld fault pixels and $N_{\text{far}}=10{,}791$ withheld fault pixels at $d_{\text{vis}} > 10\text{ px}$)  
**Comparable Holdout Incumbent:** `H88-ADHR` (stored `HOLDOUT-DTI = 0.187888`, `[0.171698, 0.203260]`; recomputed paired control `HOLDOUT-DTI = 0.189634`, `[0.174971, 0.205481]`; far-subset $d_{\text{vis}} > 10\text{ px}$ `HOLDOUT-DTI = 0.114778`)  
**Experiment Budget:** $\le 3$ experiments or $\le 2$ hours (`PARALLEL-RUN PROTOCOL` Rule 6). Zero DrivenData submission slots spent during holdout validation.

---

## Diagnostic Motivation: Why `H88-ADHR` Starves the Blind Basin and Why `MRR-BPR-88`, `HALO-88`, `KTH-88`, and `MDC-88` Fell Short

Direct measurement of the withheld positive distance distribution $d_{\text{vis}}(x) = \text{EDT}(\neg \text{visible})$ across the 8 buffered whole-component holdout folds (`seed=20` and `seed=21`, $22{,}893$ withheld fault pixels) reveals four distinct structural regimes:

| Distance from Visible Catalogue $d_{\text{vis}}$ | Physical / Structural Regime | Seed 20 ($n=11{,}321$) | Seed 21 ($n=11{,}572$) | Pooled Share ($n=22{,}893$) |
| --- | --- | --- | --- | --- |
| $d_{\text{vis}} \le 6\text{ px}$ ($\le 600\text{ m}$) | Near-tip damage envelope & immediate step-over | `30.0%` (`3,395`) | `27.8%` (`3,213`) | **`28.9%`** (`6,608`) |
| $6 < d_{\text{vis}} \le 15\text{ px}$ ($0.6\text{–}1.5\text{ km}$) | Relay ramps, synthetic/antithetic splays, horse-tail tips | `43.2%` (`4,890`) | `40.4%` (`4,675`) | **`41.8%`** (`9,565`) |
| $15 < d_{\text{vis}} \le 25\text{ px}$ ($1.5\text{–}2.5\text{ km}$) | Piedmont bajada / range-front step-out structures | `16.3%` (`1,841`) | `15.3%` (`1,769`) | **`15.8%`** (`3,610`) |
| $d_{\text{vis}} > 25\text{ px}$ ($> 2.5\text{ km}$) | Blind intra-basin & unmapped Quaternary-cover faults | `10.6%` (`1,195`) | `16.6%` (`1,915`) | **`13.6%`** (`3,110`) |

In `H88-ADHR` (`src/gems88/adhr.py`), the catalogue-conditioned relay head $p_{\text{joint}}(x)$ and the label-blind physical head $p_{\text{phys}}(x)$ are combined with a **spatially constant** linear mixture $p_{\text{final}}(x) = 0.50\,p_{\text{joint}}(x) + 0.50\,p_{\text{phys}}(x)$ across the entire footprint. Because $p_{\text{joint}}(x)$ depends on visible-fault relay geometry (`X_vis22`) and damage-zone width ($d_{\text{vis}}/w$), it predicts $p_{\text{joint}}(x) \approx 0$ whenever $d_{\text{vis}}(x) > 20\text{ px}$. Consequently:
$$\forall x \text{ with } d_{\text{vis}}(x) > 25\text{ px}: \quad p_{\text{final}}(x) = 0.50 \cdot 0 + 0.50\,p_{\text{phys}}(x) = 0.50\,p_{\text{phys}}(x).$$
Halving the physical posterior in unmapped basins causes almost every genuine blind-basin fault to fall below the global Dinkelbach marginal threshold ($\text{bar} \approx 0.045$), leaving `H88-ADHR` with only `4.2%` of its production dots at $d_{\text{cat}} > 25\text{ px}$ (failing the `share_gt25 >= 0.35` fleet fingerprint screen) and suppressing far-basin (`d_vis > 10 px`) recall. Meanwhile, inspection of the restored external rasters in `data/external/` shows that `src/gems88/physics.py` left **14 high-coverage USGS GeoDAWN, 3DEP 10 m, 1 m LiDAR, and DOE GDR bands completely unread**.

---

## Candidate Geological Hypotheses (Ranked by Expected DTI Gain vs. Implementation Cost)

| Rank | Hypothesis ID & Name | Specific Layers & Bands | Expected DTI Gain | Implementation Cost | Sandbox Data Availability |
| --- | --- | --- | --- | --- | --- |
| **1** | **`GTHC-88`**: Geothermal Transtensional Hydrothermal-Conduit & Completeness-Regime Decomposition | Competition Bands `2, 5, 7, 8, 9, 11, 12, 13, 15, 17, 18, 19`; **unused** `geodawn_rad_u8.tif` Bands `3 (U), 4 (TC)`; **unused** `geodawn_extensions_u8.tif` Bands `2 (UK), 3 (UTh), 4 (TMI_up150)`; **unused** `dem10_chi_100m_u8.tif` Bands `1–4 (chan_n, knick_n, raised_n, valid_n)` + `dem10_chi_100m_i16.tif` Band `3 (ksn_max_m0.9)`; **unused** `topo_10m_derived_100m_u8.tif` Bands `3 (steep_frac), 4 (slope_std), 5 (relief_local), 7 (aspect_coherence)`; **unused** `lidar_scarp_features_u8.tif` Bands `2 (ex_mean), 6 (downface_max), 7 (upface_max), 8 (cross_max)`; **unused** `gdr_wellspring_in_footprint.csv` `geothermchalc_c`, `geothermcat_c` + `2m_temperature_probe_INGENIOUS_regional_data.zip` + `paleo_geothermal_regional.zip` | **High** (`+0.002 to +0.010` overall `HOLDOUT-DTI`; `+0.005 to +0.025` on $d_{\text{vis}}>10\text{ px}$ far subset) | **Low–Medium** (~6 min for 8 folds on 2 CPUs using disk `np.memmap`, `<550 MB` RSS) | **100% Obtainable & Hash-Verified in Workspace** (`scripts/restore_inputs.py`) |
| **2** | **`SWIR-CLAY-SINTER-88`**: Sentinel-2 / ASTER Shortwave-Infrared Argillic Clay-Cap & Opaline Sinter Lineaments | Sentinel-2 L2A Band 11 (`1610 nm`) / Band 12 (`2190 nm`) hydroxyl absorption ratio + ASTER TIR silica index + Competition Band 17 (`cond_surf`) & Band 19 (`det_elev_slope`) | **Medium–High** (`+0.003 to +0.008` in hydrothermally bleached basins) | **High** (cloud-free mosaic + atmospheric/vegetation masking across `373 x 329 km`) | **Blocked in Sandbox** — official AWS Open Data (`registry.opendata.aws/sentinel-2-l2a-cogs`) & USGS EarthExplorer (`earthexplorer.usgs.gov`) are outside the sandbox outbound allowlist |
| **3** | **`INSAR-LOS-STEP-88`**: Sentinel-1 Ascending/Descending InSAR Velocity Discontinuity Across Bajadas | ARIA / ASF Sentinel-1 secular LOS velocity maps (`asf.alaska.edu`) + Competition Geodetic Strain Bands `4, 7, 8` (`geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`) | **Medium–High** (`+0.003 to +0.007` on creeping/compacting intra-basin faults) | **High** (unwrapping artefact removal + tropospheric phase correction) | **Blocked in Sandbox** — official NASA/ASF (`asf.alaska.edu`) and COMET LiCSAR hosts are outside the sandbox outbound allowlist |
| **4** | **`MT-PHASE-SKEW-88`**: EarthScope USArray 3D Magnetotelluric Phase-Tensor Skew & Deep Feeder Columns | USGS / IRIS EarthScope USArray 3D MT resistivity impedance cubes (`5–15 km` depth slices, `sciencebase.gov` / `ds.iris.edu`) + Competition Band 17 (`cond_surf`) & Band 18 (`iso_grav_anom_hg`) | **Medium** (`+0.001 to +0.005` on deep-plumbed range-front conduits) | **Medium** (3D-to-2D upward admittance projection onto `100 m` grid) | **Blocked in Sandbox** — live ScienceBase (`sciencebase.gov`) and IRIS SPUD (`ds.iris.edu`) endpoints are outside the sandbox outbound allowlist |

---

## Detailed Specification of the 4 Candidate Hypotheses

### Hypothesis 1 (Rank 1 — Selected for Implementation & Holdout Validation): `GTHC-88` (Geothermal Transtensional Hydrothermal-Conduit & Completeness-Regime Decomposition)

1. **Specific Layers Involved:**
   - Competition 19-band GeoTIFF (`data/training_features.tif`, SHA-256 `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`): Bands 2 (`rtp`), 5 (`iso_grav_anom_slope`), 7 (`geod_shearrate`), 8 (`geod_dilaterate`), 9 (`tmi_vg`), 11 (`iso_grav_anom_vg`), 12 (`det_elev`), 13 (`iso_grav_anom`), 15 (`depth_to_base_surf`), 17 (`cond_surf`), 18 (`iso_grav_anom_hg`), 19 (`det_elev_slope`).
   - Previously unread USGS GeoDAWN radiometric & upward-continued magnetic channels: `data/external/geodawn_rad_u8.tif` (SHA-256 `c22420f7…`) Band 3 (`U`) and Band 4 (`TC`), plus `data/external/geodawn_extensions_u8.tif` (SHA-256 `a35a9c6d…`) Band 2 (`UK`), Band 3 (`UTh`), and Band 4 (`TMI_up150`).
   - Previously unread USGS 3DEP 10 m fluvial knickpoint & raised-channel density channels: `data/external/dem10_chi_100m_u8.tif` (SHA-256 `e8830ba6…`) Bands 1 (`chan_n`), 2 (`knick_n`), 3 (`raised_n`), 4 (`valid_n`), paired with `data/external/dem10_chi_100m_i16.tif` (SHA-256 `8897ba9c…`) Band 3 (`ksn_max_m0.9`) and Band 5 (`zmean_m`).
   - Previously unread USGS 3DEP 10 m sub-grid scarp geometry channels: `data/external/topo_10m_derived_100m_u8.tif` (SHA-256 `a6398d99…`) Band 3 (`steep_frac`), Band 4 (`slope_std`), Band 5 (`relief_local`), and Band 7 (`aspect_coherence`).
   - Previously unread 1 m LiDAR cross-scarp polarity channels: `data/external/lidar_scarp_features_u8.tif` (SHA-256 `d580bb8b…`) Band 2 (`ex_mean`), Band 6 (`downface_max`), Band 7 (`upface_max`), Band 8 (`cross_max`), and Band 12 (`valid`).
   - Previously unread DOE GDR chalcedony and Na-K-Ca cation geothermometers (`geothermchalc_c`, `geothermcat_c` in `data/external/gdr_wellspring_in_footprint.csv`, SHA-256 `122718e6…`, reading **only** coordinates and temperature/geothermometer columns, never `dist_known_fault_px`), fused with INGENIOUS 2 m temperature probes (`2m_temperature_probe_INGENIOUS_regional_data.zip`, SHA-256 `1301f70d…`) and paleo-geothermal sinter/travertine (`paleo_geothermal_regional.zip`, SHA-256 `faffcf69…`).

2. **Physical Signature & Mathematical Transforms (`GTHC_FEATURES`, 6 new channels):**
   - `gthc_uranium_redox_argillic_halo`: Z-scored GeoDAWN `U`, `UK`, and `UTh` radiometric redox anomalies multiplied by shallow electrical conductivity (`cond_surf`) and magnetite-destruction vertical magnetic trough (`-tmi_vg`). Captures uranium precipitation at reducing-to-oxidizing geothermal fluid boundaries and smectite/illite clay alteration along fault conduits.
   - `gthc_upward_mag_basement_admittance`: Vertical continuation contrast between shallow `tmi_vg` and the multi-scale Laplacian of 150 m upward-continued TMI (`TMI_up150`), co-aligned with cover-compensated horizontal gravity gradient (`iso_grav_anom_hg * log1p(depth_to_base_surf)`) and active geodetic transtensional strain rate ($\dot{\gamma}_{\text{shear}} \cdot \max(\dot{\epsilon}_{\text{dilat}}, 0)$).
   - `gthc_fluvial_knick_raised_incision`: 3DEP 10 m channel knickpoint fraction (`knick_n / max(chan_n, 1)`) + raised-channel fraction (`raised_n / max(valid_n, 1)`) weighted by channel steepness `ksn_max_m0.9` and attenuated inside Pleistocene Lake Lahontan (`1330 ± 35 m`) and Lake Bonneville (`1555 ± 35 m`) shoreline elevation bands.
   - `gthc_bajada_aspect_monocline`: 3DEP 10 m directional scarp organization (`aspect_coherence * steep_frac * log1p(relief_local) / (1 + slope_std / (slope_p90 + 1))`), isolating smooth, laterally coherent monoclinal warps on alluvial bajadas from rugged, isotropic bedrock outcrops.
   - `gthc_lidar_normal_polarity_asymmetry`: 1 m LiDAR normal-fault scarp polarity (`|downface_max - upface_max| * cross_max * ex_mean`) inside valid LiDAR swaths, measuring unidirectional Synthetic/Antithetic dip-slip step asymmetry across faulted fans.
   - `gthc_chalcedony_cation_updip_feeder`: Multi-geothermometer thermal anomaly combining quartz, chalcedony, and Na-K-Ca cation reservoir temperatures with 2 m temperature probe anomalies and sinter mounds, shifted upslope (`600 m` and `1.5 km`) along the unit topographic gradient $\hat{u} = \nabla z / \|\nabla z\|$ so the anomaly peaks at the range-front / piedmont structural feeder fault rather than in the downslope lateral outflow tongue.
   - **Completeness-Regime Decomposition (`SCRD`)**: Instead of `H88-ADHR`'s constant $0.50/0.50$ fusion weight, `GTHC-88` weights the catalogue-conditioned structural relay head $p_{\text{struct}}(x)$ and the 50-channel zero-catalogue physical conduit head $p_{\text{phys}}(x)$ using a spatially varying completeness gate $w_{\text{phys}}(d_{\text{vis}}, z_{\text{base}})$ that transitions smoothly from structural dominance in near-fault relay ramps ($d_{\text{vis}} \le 12\text{ px}$) to physical/hydrothermal conduit dominance in buried basins ($d_{\text{vis}} > 15\text{ px}$).

3. **Why It Catches Faults Missing from the USGS/INGENIOUS Catalogue:**
   - The USGS/INGENIOUS catalogue is compiled primarily from aerial-photo scarp mapping and exposed bedrock geology. In the Great Basin, $>40\%$ of geothermal systems (e.g., Bradys, Desert Peak, Soda Lake, Salt Wells, McGinness Hills, tungsten-piedmont blind systems) are hosted by concealed step-overs, accommodation zones, or intra-basin normal faults buried beneath Quaternary pluvial lake beds (`Lahontan`/`Bonneville`) and coalescing bajada fans where surface scarps are obliterated or subdued to `< 1 m` monoclinal warps. These blind faults still produce upward-continued basement gravity-magnetic admittance gradients, argillic/redox `U-Th-K` and `cond_surf` alteration halos, 10 m fluvial knickzones (`knick_n`, `raised_n`), and updip chalcedony/cation thermal plumes.

4. **Named Non-Fault Physical Mimic:**
   - Pleistocene pluvial Lake Lahontan (`~1330 m`) and Lake Bonneville (`~1555 m`) wave-cut shoreline terraces, beach ridges, and playa evaporite margins (which create non-tectonic topographic steps, high shallow electrical conductivity from saline pore fluids, and evaporitic uranium accumulation). Mitigated via explicit pluvial shoreline elevation attenuation and requirement of co-aligned deep potential-field admittance (`TMI_up150` + `iso_grav_anom_hg`).

5. **How It Differs from Existing Repo Methods:**
   - `physics.py` (`CGO-88` / `PHYS44`) never read `geodawn_rad_u8.tif` Bands 3–4 (`U, TC`), `geodawn_extensions_u8.tif` Bands 2–3 (`UK, UTh`), `dem10_chi_100m_u8.tif` (`chan_n, knick_n, raised_n`), `topo_10m_derived_100m_u8.tif` (`steep_frac, slope_std, relief_local, aspect_coherence`), `lidar_scarp_features_u8.tif` (`downface_max, upface_max, cross_max`), or `gdr_wellspring_in_footprint.csv` (`geothermchalc_c, geothermcat_c`).
   - `H88-ADHR` used a spatially invariant `0.50/0.50` fusion weight that halved physical probabilities in the blind basin ($d_{\text{vis}} > 25\text{ px}$) and placed `95.8%` of dots within $25\text{ px}$ of the catalogue. `GTHC-88` replaces spatially constant fusion with completeness-regime gating and stratified dual-domain allocation.

---

### Hypothesis 2 (Rank 2 — External Data Blocked in Sandbox): `SWIR-CLAY-SINTER-88`
- **Specific Layers Involved:** Copernicus Sentinel-2 L2A Band 11 (`1610 nm`) & Band 12 (`2190 nm`) and Terra ASTER TIR/SWIR bands, paired with Competition Band 17 (`cond_surf`) and Band 19 (`det_elev_slope`).
- **Physical Signature:** Anisotropic ridge filter on the hydroxyl/clay absorption index $\text{SWIR}_{\text{clay}} = (B_{11} - B_{12})/(B_{11} + B_{12})$ co-aligned with shallow electrical conductivity ridges.
- **Why It Catches Missing Faults:** Hydrothermal steam-heated acid-sulfate and argillic alteration (kaolinite, alunite, smectite, opaline sinter) bleaches surface soils along unmapped range-front and intra-basin fault traces even where mechanical fault scarps have been eroded flat.
- **Named Non-Fault Mimic:** Playas, evaporite salt flats, and hydrothermally altered Miocene volcaniclastics unrelated to Quaternary faulting.
- **Difference from Repo:** Uses optical/SWIR mineral spectroscopy rather than potential fields or DEM morphology.
- **Obtainability Check:** Requires fetching Sentinel-2 L2A / ASTER scenes from `https://registry.opendata.aws/sentinel-2-l2a-cogs/` or `https://earthexplorer.usgs.gov/`, which are blocked by the sandbox outbound firewall. Not viable in this sandbox without pre-staged imagery.

### Hypothesis 3 (Rank 3 — External Data Blocked in Sandbox): `INSAR-LOS-STEP-88`
- **Specific Layers Involved:** Sentinel-1 ascending/descending InSAR line-of-sight (LOS) secular velocity and coherence maps (`https://asf.alaska.edu/` / ARIA), combined with Competition Bands 4, 7, 8 (`geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`).
- **Physical Signature:** Directional Sobel step detector on ascending/descending LOS velocity difference $|\nabla(v_{\text{asc}} - v_{\text{desc}})|$ across low-slope alluvial fans (`det_elev_slope < 5°`).
- **Why It Catches Missing Faults:** Competition geodetic strain layers are interpolated from sparse GPS stations (`~15–30 km` spacing) and cannot resolve individual fault strands; InSAR resolves `100 m` phase steps caused by aseismic fault creep or differential aquifer compaction across buried intra-basin faults serving as hydraulic barriers.
- **Named Non-Fault Mimic:** Agricultural groundwater pumping bowls and seasonal playa clay swelling/subsidence.
- **Difference from Repo:** Replaces continuum GPS strain interpolation with satellite radar interferometric phase discontinuities.
- **Obtainability Check:** Requires downloading Sentinel-1 velocity rasters from `asf.alaska.edu`, which is outside the sandbox outbound allowlist.

### Hypothesis 4 (Rank 4 — External Data Blocked in Sandbox): `MT-PHASE-SKEW-88`
- **Specific Layers Involved:** USGS / EarthScope USArray 3D Magnetotelluric (MT) crustal electrical resistivity models (`https://www.sciencebase.gov/` / IRIS SPUD), combined with Competition Band 17 (`cond_surf`) and Band 18 (`iso_grav_anom_hg`).
- **Physical Signature:** Upward-projected MT phase-tensor skew angle ($\beta > 5^\circ$) and mid-crustal (`5–15 km`) conductivity anisotropy aligned with shallow horizontal gravity gradients.
- **Why It Catches Missing Faults:** Distinguishes deep-rooted, fluid-filled transtensional fault conduits cutting the brittle-ductile transition from shallow, dry bedrock fractures.
- **Named Non-Fault Mimic:** Graphitic Paleozoic marine shales (e.g., Roberts Mountains allochthon) and conductive clay-rich basin depocenters.
- **Difference from Repo:** Uses deep 3D magnetotelluric impedance tensors rather than shallow surface conductivity (`cond_surf`).
- **Obtainability Check:** Requires fetching MT impedance cubes from `sciencebase.gov` or `ds.iris.edu`, which are outside the sandbox outbound allowlist.

---

## Pre-Registered 3-Experiment Validation Plan for Rank 1 (`GTHC-88`)

Within our hard cap of **at most 3 experiments** (`PARALLEL-RUN PROTOCOL` Rule 6):
1. **Experiment 1 (`GTHC-88-PURE`)**: Evaluate the 50-channel zero-catalogue physical/hydrothermal stack (`44` `ALL_PHYS_FEATURES` + `6` `GTHC_FEATURES`) with out-of-fold LightGBM + HistGradientBoosting and $300\text{ m}$ ($3\text{ px}$) catalogue exclusion halo against `PHYS44` (`0.10725`) and `CGO-88` (`0.09042`) on the 8 buffered whole-component holdout folds (`seeds 20+21`).
2. **Experiment 2 (`GTHC-88-DUAL`)**: Evaluate the completeness-regime-gated fusion of the GTHC-augmented structural head and GTHC-augmented physical head against recomputed `H88-ADHR` (`0.189634` overall, `0.114778` far subset $d_{\text{vis}}>10\text{ px}$) on the exact same 8 buffered whole-component holdout folds (`seeds 20+21`, $N_{\text{all}}=22{,}893$, $N_{\text{far}}=10{,}791$).
3. **Experiment 3 (`GTHC-88-STRAT`)**: Evaluate the fingerprint-compliant stratified dual-domain allocation (`d > 3 px` collar + guaranteed far-basin discovery share `share_gt25 >= 0.36`) so that we measure both the unrestricted holdout DTI (`GTHC-88-DUAL`) and the fingerprint-constrained holdout DTI (`GTHC-88-STRAT`), verify single-feature leakage canaries ($\text{symmetric AUC} \le 0.90$ across all 50 physical channels), verify pre-placement (`|Spearman rho| <= 0.90`) and post-placement (`3-px overlap <= 0.70`) uniqueness against all 222+ registry rasters, and emit the portal-parity GeoTIFF, single-member ZIP, and JSON run card.
