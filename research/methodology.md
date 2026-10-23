# GEMSDOE88 Methodology & Mathematical Formulation (`H88-ADHR`)

## 1. Scientific Objective & Domain Physics
The DOE GEMS Prize asks models to discover **previously unmapped geological faults indicative of geothermal fluid pathways** across the Great Basin (`3730 × 3292` grid at `100 m` resolution in `EPSG:32611`), NOT surface hot vents or already-mapped traces in `existing_faults.tif` (`60,988` positive cells).

Three physical separation mechanisms explain why concealed geothermal faults are missed by surface-only Quaternary catalogues:
1. **60° Normal-Fault Hanging-Wall Basement Offset (`Δx = z_base / tan 60°`):** Extensional Basin-and-Range normal faults dip at `δ ≈ 60°` beneath Cenozoic basin fill of thickness `z_base` (`depth_to_base_surf`, band 15). Maximal horizontal density (`horiz_grav_grad`, band 18) and magnetic (`rtp`, band 2) gradients therefore occur `Δx = z_base / tan 60°` down-dip inside the basin hanging wall rather than directly underneath the surface trace. Back-projecting `|∇g|` and `|∇RTP|` across the topographic slope vector `−∇h_reg / ‖∇h_reg‖` recovers the range-front fault trace.
2. **Upslope Advection of Shallow Geothermal Plumes (`DOE GDR #1391`, CC BY 4.0):** Meteoric hydraulic gradients advect hot fluids laterally down alluvial fans from permeable range-front fault conduits toward valley floors, creating displaced `2 m` temperature probe (`F2mDAB`) anomalies, paleo-sinter terraces, and clay alteration caps (`|∇ log(cond_surf)|`, band 17). Directional upslope kernels along `+∇h_reg` reconnect shallow outflow plumes to their structural feeder trace.
3. **Pleistocene Paleoshoreline Decontamination:** Wave-cut benches of Pleistocene Lake Lahontan (`~1,330 m`) and Lake Bonneville (`~1,555 m`) mimic fault scarps in `1 m` and `10 m` DEMs (`IR-88-SHORELINE`), whereas tectonic scarps cut across elevation contours and coincide with stream steepness (`k_sn`) knickzones and basement gravity steps.

## 2. Latent Mapping Completeness & Calibrated Dual Expectation
In Positive-Unlabeled spatial fault discovery, unlabelled pixels in unmapped basins are **missing-not-at-random** with respect to catalogue completeness $M(x) \in \{0, 1\}$. Conditioning exclusively on visible-catalogue geometry $X_{\text{vis}}$ (`M = 1`) suppresses true isolated faults in unmapped basins (`M = 0`).

Let $p_{\text{joint}}(x) = P(F_x = 1 \mid X_{\text{phys}}, X_{\text{vis}})$ and $p_{\text{phys}}(x) = P(F_x = 1 \mid X_{\text{phys}})$ denote the calibrated 67-feature structural+physical and 44-feature pure-physical probabilities normalized to total fold expectation $k_{\text{target}}$, with corresponding continuous `300 m` triangular-kernel self-credits $m_{\text{joint}}(x), m_{\text{phys}}(x) \in [p(x), 1]$ preserving $\mathbb{E}[\sum_x \max_{g} K(d(x, g))]$ separately from $\mathbb{E}[\sum_x y_x]$ (avoiding Jensen's inequality attenuation on log-odds product-of-experts).

Marginalizing over latent mapping completeness $\pi_{\text{unmapped}} = 0.50$:
$$p^*(x) = (1 - \pi_{\text{unmapped}})\,p_{\text{joint}}(x) + \pi_{\text{unmapped}}\,p_{\text{phys}}(x), \qquad m^*(x) = (1 - \pi_{\text{unmapped}})\,m_{\text{joint}}(x) + \pi_{\text{unmapped}}\,m_{\text{phys}}(x).$$

In full-domain production (`fit_and_emit_production_adhr`), $p_{\text{phys}}(x)$ and $m_{\text{phys}}(x)$ are predicted strictly **out-of-fold across the 4 spatial quadrants** (`fit on 3 quadrants -> predict on held-out 4th quadrant`), preventing smooth regional fields (`gravity`, `strain`, `magnetics`) from memorizing `200–1,000 m` halos around `existing_faults.tif`.

## 3. Exact Dinkelbach Fractional-Programming Binary Allocation
Given calibrated $(p^*, m^*)$, discrete binary predictions $S \subseteq \Omega_{\text{allowed}}$ (`d_cat > 2.0 px`) maximize the expected Distance-Weighted Tversky Index (`α = 0.2`, `β = 0.8`, `300 m` triangular kernel $K(r) = \max(0, 1 - r/3)$) via iterative Dinkelbach linearization (`vendor/gems57/emit.py::dinkelbach_allocate`, `min_spacing_px = 2.05`), admitting a pixel only while its marginal expected truth coverage exceeds the exact fractional supergradient bar $0.2 \cdot c^{(t)}$.
