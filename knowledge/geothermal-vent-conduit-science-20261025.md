# Great Basin Geothermal Vent, Hydrothermal Alteration & Blind Fault Conduit Knowledge Base

**Compiled:** `2026-10-25` · **Scope:** Reusable physical, geochemical, and geophysical domain reference for DrivenData DOE GEMS (`EPSG:32611`, 100 m grid, Distance-Weighted Tversky Index $\alpha = 0.2, \beta = 0.8, R = 300\text{ m}$).

---

## 1. Structural Controls on Blind vs. Emergent Great Basin Geothermal Systems

Across the Great Basin extensional/transtensional province (Basin and Range + Walker Lane), **roughly 75% of known and undiscovered moderate-to-high-temperature ($>130\,^\circ\text{C}$) geothermal systems are "blind" (hidden)** — lacking active boiling hot springs or fumaroles at the surface because the water table lies beneath unsaturated alluvial fans or impermeable playa clay/evaporite seals ([DOE INGENIOUS GDR `#1391`](https://gdr.openei.org/submissions/1391); [USGS Quaternary Fault & Fold Database](https://www.usgs.gov/programs/earthquake-hazards/faults)).

Rather than occurring uniformly along the midpoints of long planar range-front normal faults (where clay-rich fault gouge often reduces cross-fault permeability), geothermal upflow concentrates at **localized 3D dilatational fracture-permeability sweet spots** where slip-tendency and dilation-tendency peak simultaneously:
1. **Extensional Accommodation Zones & Relay Ramps / Step-Overs** (`300 m–3 km` wide) bridging en-echelon normal fault segments, breached by dense networks of oblique cross-faults.
2. **Fault Intersections** between NNE-striking Basin-and-Range normal faults and NW/ENE-striking Walker Lane dextral/sinistral strike-slip or basement transfer structures.
3. **Horsetail Fault Terminations / Tip Damage Zones** where displacement gradients $\partial u / \partial x$ are steep and tensile wing cracks splay into basin fill.
4. **Piedmont Burial Hinges** (`depth_to_base_surf` $\approx 50\text{–}600\text{ m}$, `1.0–3.0 km` basinward of the topographic bedrock range front), where active slip steps out from the eroded mountain front onto concealed master Synthetic/Antithetic graben faults beneath bajada gravel aprons.

---

## 2. Four-Facies Thermodynamic Partitioning of Paleo-Geothermal Deposits (`Paleo_geothermal_final.csv`)

In `data/external/paleo_geothermal_regional.zip` (`Paleo_geothermal_final.csv`, `701` mapped deposits from [DOE GDR `#1391`](https://gdr.openei.org/submissions/1391)), lumping all deposits into a single positive kernel introduces two severe geological errors: (a) downslope displacement from lateral outflow aprons, and (b) non-hydrothermal pluvial lake carbonate mimics (`IR-88-116`). Thermodynamic phase separation partitions the `701` records into four distinct structural regimes:

| Facies Class | `Deposit_type` Categories in `Paleo_geothermal_final.csv` | In-Footprint Records | Structural Position Relative to Blind Feeder Fault | Physical & Geochemical Mechanism |
|---|---|---:|---|---|
| **I. Vertical Vapor-Chimney / Acid-Sulfate Core** | `Explosion craters` (11), `Sulfur` (6), `Sulfate crust` (2), `Silicified fault breccia` / `Silica veins` / `Silica-cemented alluvium` (6), `Argillic alteration` / `Alteration` (27) | `52` | **Directly above steep fault chimney (`0–400 m`)** | Subsurface boiling ($T \ge 150\text{–}240\,^\circ\text{C}$) exsolves buoyant $\text{H}_2\text{S} + \text{CO}_2 + \text{steam}$ that rises **vertically** through unsaturated fault breccia above the water table, oxidizing to $\text{H}_2\text{SO}_4$ (steam-heated kaolinite-alunite-sulfur alteration and hydrothermal phreatic explosion craters). |
| **II. High-Enthalpy Neutral-Chloride Sinter** | `Sinter`, `Siliceous sinter`, `Opaline sinter`, `Silicified sands` | `135` | **Near fault-intersection vent (`0–900 m`)** | Amorphous opal-A sinter precipitation requires high dissolved $\text{SiO}_2$ equilibrated with quartz at reservoir temperatures **$T_{\text{res}} > 175\,^\circ\text{C}$** and rapid cooling/evaporation at a focused fault discharge conduit. |
| **III. Lateral Bicarbonate Outflow Travertine** | `Travertine`, `Calcite veins`, `Carbonate-cemented alluvium` | `278` | **Down-hydraulic-gradient (`0.8–3.5 km` downslope of feeder fault)** | $\text{CO}_2$-rich thermal waters rising along range-front/piedmont faults flow laterally down the water-table gradient (`-\nabla z_smooth`), degassing $\text{CO}_2$ and precipitating $\text{CaCO}_3$ aprons basinward of the structural conduit; requires **up-hydraulic-gradient back-projection** (`+\nabla z_smooth`). |
| **IV. Pluvial Lake Shoreline Mimic (Contaminant)** | `Tufa` | `158` | **Non-fault mimic along `~1,330 m` Lahontan & `~1,555 m` Bonneville strandlines** | Ambient-temperature wave agitation and algal/microbial $\text{CaCO}_3$ precipitation where calcium-bearing lake waters met alkaline Pleistocene pluvial shorelines; **must receive zero positive weight and feed an explicit shoreline-mimic suppressor**. |

---

## 3. Multi-Polymorph Solute Geothermometry & Shallow 2-m Probe Peclet Physics

### 3.1 Quartz–Chalcedony–Cation Boiling & Mixing Phase Space (`gdr_wellspring_in_footprint.csv`)
The `27,092` well/spring observations in [DOE GDR `#1391`](https://gdr.openei.org/submissions/1391) (`dist_known_fault_px` quarantined and dropped on load to prevent catalogue leakage) provide measured discharge/wellbore temperature $T_{\text{meas}}$ alongside three solute geothermometers with **distinct kinetic re-equilibration rates**:
- **Alkali Cation (`geothermcat_c`, Na-K-Ca):** Slowest re-equilibration; preserves deep reservoir fault-root temperature $T_{\text{deep}}$ even after kilometers of lateral cooling or shallow cold-water dilution.
- **Quartz (`geothermquartz_c`):** Intermediate kinetic rate; tracks high-enthalpy ($>120\text{–}150\,^\circ\text{C}$) upflow conduits.
- **Chalcedony (`geothermchalc_c`):** Fastest re-equilibration; resets downward in warm ($60\text{–}120\,^\circ\text{C}$) shallow outflow aquifers.

Consequently:
- **Unmixed Blind Upflow Conduit:** High $T_{\text{qtz}} > 110\,^\circ\text{C}$, high thermal disequilibrium $(T_{\text{qtz}} - T_{\text{meas}})_+$, and small cation-quartz gap $|T_{\text{cat}} - T_{\text{qtz}}|$ localize a **vertical/sub-vertical blind thermal fault** beneath shallow cover.
- **Diluted Lateral Outflow Plume:** Large positive $(T_{\text{cat}} - T_{\text{chalc}})_+$ with $T_{\text{cat}} > 120\,^\circ\text{C}$ indicates cold-groundwater mixing in a lateral outflow tongue; advecting this signal **up-hydraulic-gradient** (`+\nabla z_smooth`) points back toward the concealed piedmont/range-front feeder fault.

### 3.2 Conductive Heat Flux & 1D Advective Peclet Curvature (`2m_temperature_probe_INGENIOUS_regional_data.zip`)
Shallow 2-meter temperature probe surveys (`3,800` stations across Great Basin basins in [DOE GDR `#1391`](https://gdr.openei.org/submissions/1391)) record temperatures at $z_1 = 1.0\text{ m}$, $z_{1.5} = 1.5\text{ m}$, and $z_2 = 2.0\text{ m}$ alongside seasonal drift base stations (`StCode == 'B'`).
For steady 1D vertical advective-conductive heat transport with upward Darcy/vapor velocity $v_z$ in vadose alluvium of thermal diffusivity $\kappa$:
$$\kappa \frac{\partial^2 T}{\partial z^2} - v_z \frac{\partial T}{\partial z} = 0 \implies -\frac{\partial^2 T}{\partial z^2} = -\frac{v_z}{\kappa}\frac{\partial T}{\partial z}$$
Wait — care with sign convention ($z$ positive downward from $1\text{ m}$ to $2\text{ m}$): with temperature increasing downward ($\partial T/\partial z > 0$) and fluid/vapor moving **upward** ($u_{\text{up}} = -v_z > 0$), the governing equation $\kappa T''(z) + u_{\text{up}} T'(z) = 0$ yields **$T''(z) = -(u_{\text{up}}/\kappa)\,T'(z) < 0$**, i.e., **downward concavity**:
$$-\frac{\partial^2 T}{\partial z^2} \approx \frac{2\,T_{1.5\text{m}} - T_{2.0\text{m}} - T_{1.0\text{m}}}{(0.5\text{ m})^2} > 0 \quad \text{simultaneously with} \quad \frac{\partial T}{\partial z} = T_{2.0\text{m}} - T_{1.0\text{m}} > 0.$$
Combining survey-area-debiased $\partial T/\partial z$ with positive Peclet concavity $-\partial^2 T/\partial z^2$ separates genuine **upward geothermal vapor/fluid advection above blind faults** from surface insolation/albedo transients.

---

## 4. Airborne Radiometric, Aeromagnetic & 3DEP Geomorphic Signatures of Altered Fault Conduits

1. **Airborne Gamma-Ray Spectrometry (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`, [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)):**
   Potassium-bearing hydrothermal fluids precipitate adularia and illite/sericite along permeable fault zones while thorium ($\text{Th}^{4+}$) remains geochemically immobile in resistate phases and uranium ($\text{U}^{6+}$) mobilizes across redox boundaries (`UK` in `geodawn_extensions_u8 B02`, `UTh` in `B03`). The **Efimov hydrothermal alteration F-parameter** $F = \text{K} \cdot (\text{U}/\text{Th}) / \text{Th} = \text{K}\cdot\text{U}/\text{Th}^2$ paired with **aeromagnetic magnetite destruction** (where sulfidation/oxidation converts ferrimagnetic magnetite to paramagnetic pyrite/hematite, creating a short-wavelength `RTP` trough relative to upward-continued `TMI_up150`) isolates hydrothermally altered fault damage zones from unaltered volcanic rocks.
2. **Upward-Continuation Structural Index & Gravity-Slope Ridges (`training_features.tif` `B05, B06, B11, B13, B15, B18`):**
   A sub-vertical crustal fault step (Euler structural index $N \approx 0$) retains high `TMI_up150 / tmi_hg` amplitude ratio under 150 m upward continuation and aligns with `B05 iso_grav_anom_slope` and gravity tilt zero-crossings ($\arctan(\text{B11}/\text{B18}) \approx 0$), whereas thin surficial lava flow margins ($N \approx 1.5\text{–}2$) decay rapidly with height and lack basement density steps.
3. **Cross-Modal 1 m LiDAR Strike Locking (`lidar_scarp_features_u8 B11`) & 10 m 3DEP Branch Piracy (`dem10_chi_100m_sig_i32.tif`):**
   - Subtle degraded piedmont fault scarps (`< 0.5 m` relief) exhibit axial strike alignment $\cos^2(\theta_{\text{LiDAR B11}} - \theta_{\text{sub}})$ with the underlying gravity/basement strike $\theta_{\text{sub}}$, whereas wave-cut shorelines and braided fan channels cut obliquely or concentrically across basement structure.
   - Across active upland/range-front faults, `dem10_chi_100m_sig_i32.tif` (`branch_signature_global_index_100m`, [USGS 3DEP 1/3 arc-second](https://www.usgs.gov/3d-elevation-program)) captures abrupt drainage-branch capture, shutter-ridge stream deflection, and cross-fault $\chi$-step disequilibria.
