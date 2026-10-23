# GEMSDOE88 Geological Synthesis, H33 Forensic Analysis & 5 Ranked Untried Hypotheses (2026-10-23)

## 1. Forensic Analysis: Why `GEMSDOE32` (`H33`, user-reported `0.2778`) Led ~55 Prior Submissions — and Why It Plateaued Below `0.4413`

### 1.1 Exact Three-Step Pixel Ancestry of `H33` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`)

Cross-referencing `docs/evidence/GEMSDOE32__INDEX.md`, `GEMSDOE28`, and byte-exact SHA-256 verification of `data/registry/h33_education.tif` (`c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) establishes a strict pixel-subset progression across three user-reported DrivenData receipts (all labeled **user-reported, unverified without private DrivenData submission receipt**):

| Stage | Submission Stem | Active Dots (`1.0`) | Exclusion Collar $d(\text{dot}, \text{catalogue})$ | Dots Removed | User-Reported DTI |
|---|---|---:|---|---:|---:|
| 1 | `GEMS28-H27-3-R1-SOLO-D2.8` | `44,090` | $B=0$ (off-catalogue $d > 0$) | baseline | `0.2600` |
| 2 | `GEMS28-H27-4-R1-SOLO-D2.8` | `40,199` | $B=1$ ($d > 1\text{ px} = 100\text{ m}$) | `-3,891` | `0.2708` (`+0.0108`) |
| 3 | `h33-h33-2-b2-...-zeros` (`GEMSDOE32`) | `37,654` | $B=2$ ($d > 2\text{ px} = 200\text{ m}$, $\min d = \sqrt{5} \approx 2.236\text{ px}$) | `-2,545` (`-6,436` total) | `0.2778` (`+0.0070`) |

### 1.2 Four Empirical Regimes Across All ~55 User-Reported Submissions vs Live Leaderboard (`0.4413`)

Live official DrivenData leaderboard fetch (`2026-10-23 UTC`, [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)):
- `#1 xiaofanhu`: **`0.4413`** (27 submissions)
- `#2 cfld__` / `#3 Batik Shirt Brothers`: **`0.3904`** (16 / 47 submissions)
- `#5 No Fault of Our Own` (Initial Round $5\times\$10\text{k}$ cutoff): **`0.3539`** (4 submissions)
- `#50 arnofault` (SSR table floor): **`0.2817`** (4 submissions)

Grouping the user's ~55 historical runs reveals four distinct mathematical and geological regimes:

1. **Regime I (`0.2478 – 0.2778` — Sparse binary `{0, 1}` kernel-spaced dots + multi-physics contact features):**
   - `GEMSDOE32` (`H33`, `37,654` dots, `0.2778`), `GEMSDOE36` (`anderson-geothermal-pinn`, `38,854` dots, `0.2750`), `GEMSDOE28` (`0.2708`), `37GEMSDOE` (`0.2683`), `GEMSDOE70` (`p5-dual-submod300-oof38k`, `37,654` dots, `0.2478`).
   - **Why DTI rewards `{0, 1}` kernel-spaced dots over dense rasters:** Under [official DTI](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ($\alpha = 0.2, \beta = 0.8$, triangular kernel $k(d) = \max(1 - d/300\text{ m}, 0)$):
     $$TP_w = \sum_{g \in G} \max_{p \in P} c(p) k(\|g-p\|), \qquad FP_w = \sum_{p \in P} c(p)\!\left(1 - \max_{g \in G} k(\|p-g\|)\right).$$
     Because $TP_w$ takes a **pointwise $\max$** over predictions within $300\text{ m}$ ($3\text{ px}$) while $FP_w$ **sums** $c(p)$ over every emitted pixel, emitting two adjacent pixels on the same fault ridge doubles $FP_w$ while adding nearly zero $TP_w$. Spacing binary `{0.0, 1.0}` dots by $\approx 2.85\text{ px}$ ($285\text{ m}$) captures near-maximal $300\text{ m}$ kernel coverage at $1/9\text{th}$ the false-positive tax.
   - **Why removing $0 < d \le 2\text{ px}$ catalogue-collar dots raised `0.2600 -> 0.2778`:** Public USGS/INGENIOUS traces already lie in `existing_faults.tif`; placing dots $100\text{–}200\text{ m}$ beside already-mapped segments spends $0.2\times 6,436 = 1,287.2$ denominator units on digitization jitter rather than genuinely unmapped fault strands.
2. **Regime II (`0.1380 – 0.1976` — Over-budget dot counts, soft fractional amplitudes, or partial feature sets):**
   - `GEMSDOE73` (`H73-MCSC` pure Blakely–Simpson ridges, `0.1917`), `42GEMSDOE` (`0.1976`), `GEMSDOE39` (`0.1951`), `17GEMSDOE` (`0.1380`, `5,167,373` positive footprint cells — massive $\alpha FP_w$ denominator inflation).
3. **Regime III (`0.0053 – 0.0680` — Pure catalogue-topology / relay-halo / tip-propagation models without independent geophysical crest confirmation):**
   - `GEMSDOE45` (`0.0106`), `57GEMSDOE` (`0.0254`), `60GEMSDOE` (`0.0156`), `GEMSDOE69` (`0.0053`), `GEMSDOE44` (`0.0294`).
   - **Root cause:** Pure catalogue proximity assumes hidden evaluation faults cluster exclusively at tips/relays of mapped traces. In reality, USGS EarthMRI GeoDAWN + 3DEP lidar exposed entire **blind intra-basin and range-front piedmont fault corridors** buried beneath Quaternary alluvium kilometers away from previously mapped bedrock traces.
4. **Regime IV (`0.0000 – 0.0044` — Ultra-sparse pinpricks or over-thresholded surfaces):**
   - When $|P| \ll |G|$, $\beta FN_w = 0.8 FN_w$ dominates the denominator and collapses DTI toward zero.

### 1.3 Why `H33` (`0.2778`) Still Trails `#1` (`0.4413`) by `0.1635` DTI

1. **Catalogue-distance dominance:** `H33`'s base score (`H27` family) still weighted mapped-trace proximity heavily, starving genuinely blind intra-basin structures (`d > 2 km` from `existing_faults.tif`) where `iso_grav_anom`, `rtp`, and `tmi_hg` carry the signal.
2. **Greedy disk NMS vs submodular 300 m DTI kernel allocation:** Fixed-radius greedy NMS ignores spatial variation in local fault density and ignores the fractional DTI trade-off between incremental expected kernel capture $\Delta \mathbb{E}[TP_w]$ and expected false-positive cost $\alpha(1 - m(x))$.
3. **Isotropic gradient magnitudes vs axial strike concordance:** Scalar slopes (`det_elev_slope`, `tmi_hg`, `iso_grav_anom_slope`) fire equally on circular volcanic plugs, caldera rims, and survey flight-line seams as on linear fault traces.

---

## 2. Official 19-Band Verification (`drivendataorg/gems-prize-reference-solution`)

All 19 GDAL band tags in `data/training_features.tif` (`SHA-256: 4371c82e...`) were verified byte-for-byte against Cell 5 of the official organizer reference notebook (`unet-mc-cv-reference-solution.ipynb`, commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`, receipt in `evidence/official-reference-band-verification.json`):
- Exact match (`True` on all 19 bands):
  1 `mag_anom`, 2 `rtp`, 3 `tmi_hg`, 4 `geod_2ndinv`, 5 `iso_grav_anom_slope`, 6 `tc`, 7 `geod_shearrate`, 8 `geod_dilaterate`, 9 `tmi_vg`, 10 `deq_n100a15`, 11 `iso_grav_anom_vg`, 12 `det_elev`, 13 `iso_grav_anom`, 14 `tmi`, 15 `depth_to_base_surf`, 16 `ieq_n100a15`, 17 `cond_surf`, 18 `iso_grav_anom_hg`, 19 `det_elev_slope`.
- **Irregularity `IR-88-07` preserved:** Both `data/training_features.tif` and the official notebook tag Band 6 `tc` as `"Tilt angle or total curvature - magnetic field derivative for edge detection (Category: magnetic_data)"`, whereas DrivenData `page/967/` (`gems_tc_tmi.png`) labels `tc` as GeoDAWN radiometric Total Count (`p01=7.71, p99=29.03`). We reference Band 6 strictly as `tc` and use only baseline-free spatial derivatives.

---

## 3. Five Ranked Untried Geological Hypotheses (Post-`MGC-88` Exp 1 & Post-`CGO-88` Exp 2)

Prior repo experiments used `2` of `3` budgeted experiments:
- **Exp 1 (`MGC-88`, accepted baseline):** 9-channel 3-band (`det_elev`, `rtp`, `iso_grav_anom`) cross-gradient + 2-px greedy NMS -> `HOLDOUT-DTI = 0.0389 [0.0264, 0.0532]`.
- **Exp 2 (`CGO-88`, falsified & rejected):** `cond_surf` (Band 17) + `iso_grav_anom` (Band 13) 200 m offset -> `HOLDOUT-DTI = 0.0227 [0.0154, 0.0309]` (`cond_surf` single-band `AUC_sym = 0.5038`; regional playa evaporite salinity drift).

Below are **5 untried geological hypotheses** ranked by expected holdout and live off-catalogue lift, data self-sufficiency, and falsifiability:

### Rank 1 (Selected for Experiment 3 of 3): `STR-88` — Zero-Catalogue Multi-Physics Curvilinear Hessian Crest + Spin-2 Axial Strike Consensus + Exact-Shell Submodular 300 m DTI Allocation
- **Exact layers (`training_features.tif` only; zero external downloads, zero catalogue features, zero `cond_surf`):**
  Bands `2` (`rtp`), `3` (`tmi_hg`), `5` (`iso_grav_anom_slope`), `6` (`tc`), `7` (`geod_shearrate`), `8` (`geod_dilaterate`), `9` (`tmi_vg`), `11` (`iso_grav_anom_vg`), `12` (`det_elev`), `13` (`iso_grav_anom`), `15` (`depth_to_base_surf`), `18` (`iso_grav_anom_hg`), `19` (`det_elev_slope`).
- **Physical transform (18 baseline-invariant channels + exact Bernoulli-max Dinkelbach allocator):**
  1. *Curvilinear Hessian crest operators* $\sigma^2 \max(0, -\lambda_-(\nabla^2 G_\sigma f))$ on `det_elev_slope` ($\sigma=2$), `iso_grav_anom_slope` ($\sigma=3$, Blakely–Simpson 1986 basement-step crest), and $\log(1+\text{tmi\_hg})$ ($\sigma=2$), plus Miller–Singh (1994) tilt magnitudes $|\arctan(\text{tmi\_vg}/(\text{tmi\_hg}+10^{-3}))|$ and $|\arctan(\text{iso\_grav\_anom\_vg}/(\text{iso\_grav\_anom\_hg}+10^{-6}))|$.
  2. *Spin-2 4-modality axial strike consensus* $(U, V) = \sum_{m \in \{\text{det\_elev}, \text{rtp}, \text{iso\_grav\_anom}, \text{tc}\}} w_m (\cos 2\theta_m, \sin 2\theta_m)$ pointwise norm and 400 m Gaussian-integrated norm $\sqrt{G_4(U)^2 + G_4(V)^2}$ (invariant to gradient sign flips across lithologic contacts; **integrates to zero around circular volcanic plugs/domes**).
  3. *Cover-bench & tectonic regime conditioning* via local 2.5 km high-pass `depth_to_base_surf` relief (`Band 15 - G_25(Band 15)`), $|\nabla G_4(\text{depth\_to\_base\_surf})|$, and dimensionless GPS extensional-to-total strain ratio `geod_dilaterate / (|geod_shearrate| + |geod_dilaterate| + 1e-9)`.
  4. *Prevalence-calibrated PU HGB + exact 6-shell Bernoulli-max self-credit + `vendor/gems57/emit.py::dinkelbach_allocate`* (`min_spacing_px=2.85`, `budget=37,654` on full Nevada).
- **Why it catches off-catalogue faults:** Buried range-front step-downs, piedmont scarps, and intra-basin accommodation zones lack mapped bedrock outcrops in USGS Qfaults, yet produce linear curvilinear crests in gravity/magnetic horizontal gradients and degraded 200–300 m topographic breaks whose axial strikes align across modalities. Conditioning on local `depth_to_base_surf` relief lets trees weight `det_elev_slope` crests on thin cover and `iso_grav_anom_slope` / `tmi_hg` tilt-zero crests beneath thick Cenozoic fill.
- **Named non-fault mimics & suppression:** (a) *Circular Tertiary volcanic plugs, cinder cones, and calderas* — suppressed analytically because $\int_0^{2\pi} e^{i 2\theta}\,d\theta = 0$ kills `spin2_mp_persist_400m`; (b) *Pleistocene Lake Lahontan shorelines & flight-line leveling seams* — lack 300 m gravity basement-step ridges and orthogonal spin-2 directors cancel; (c) *Playa salinity pans* — eliminated by excluding `cond_surf` and all raw regional DC levels.
- **How it differs from existing repo implementations:** Exp 1 (`MGC-88`) used only 3 raw bands (`det_elev`, `rtp`, `iso_grav_anom`), included raw regional smoothness, omitted `det_elev_slope`/`iso_grav_anom_slope`/`tmi_hg`/`tmi_vg`/`tc`/`depth_to_base_surf`/`geod_*`, used unweighted 1:2 HGB probabilities, and used greedy 2-px integer NMS instead of prevalence-calibrated exact-shell Dinkelbach 300 m DTI allocation. Exp 2 (`CGO-88`) tested `cond_surf`–gravity offset.

### Rank 2 (Untried Reserve): `MRR-88` — Magnetic Analytic-Signal / Tilt Depth-Ratio Demagnetization Corridor
- **Exact layers:** Bands `2` (`rtp`), `3` (`tmi_hg`), `9` (`tmi_vg`), `6` (`tc`), `15` (`depth_to_base_surf`).
- **Physical transform:** Local magnetic analytic-signal amplitude $A_{\text{mag}} = \sqrt{\text{tmi\_hg}^2 + \text{tmi\_vg}^2}$, Salem et al. (2007) tilt-depth proxy $z_{\text{tilt}} = |\nabla \theta_{\text{tilt}}|^{-1}$ along $|\theta_{\text{tilt}}| < 15^\circ$ zero-crossings, and hydrothermal magnetite-destruction trough detector $\sigma^2 \max(0, +\lambda_+(\nabla^2 G_2(\text{rtp})))$ paired with flanking `tmi_hg` crests.
- **Why it catches off-catalogue faults:** Oxidizing geothermal fluids circulating through blind Tertiary volcanic fault damage zones alter ferrimagnetic magnetite to paramagnetic hematite/clay, creating linear magnetic lows bounded by sharp tilt zero-crossings with zero surface scarp.
- **Named non-fault mimic:** Remanently reversed volcanic flow margins and powerline/pipeline magnetic cultural anomalies.
- **Difference from repo lanes:** Pure magnetic contact-depth + alteration-trough operator; neither `MGC-88`, `CGO-88`, nor `STR-88` computes Salem tilt-depth gradients or positive Hessian magnetic troughs.

### Rank 3 (Untried Reserve): `MSDD-88` — Multi-Scale Topographic Scarp Diffusion-Age Progression
- **Exact layers:** Bands `12` (`det_elev`), `19` (`det_elev_slope`), `15` (`depth_to_base_surf`), `5` (`iso_grav_anom_slope`).
- **Physical transform:** Scale-space slope spectrum $R_{1:3:6} = (|\nabla G_1(\text{det\_elev})|, |\nabla G_3(\text{det\_elev})|, |\nabla G_6(\text{det\_elev})|)$ modeling hillslope diffusion $\partial_t z = \kappa \nabla^2 z$ of degraded late-Pleistocene piedmont scarps, gated by cross-slope alluvial-fan curvature asymmetry and `iso_grav_anom_slope` backing.
- **Why it catches off-catalogue faults:** Subtle 0.5–2 m degraded alluvial fan scarps smoothed over $10^4\text{–}10^5$ yr are missed by 1:250,000 air-photo compilation (`existing_faults.tif`) yet retain diagnostic 100–600 m Gaussian slope ratios in 3DEP lidar-derived `det_elev`.
- **Named non-fault mimic:** Pleistocene pluvial shorelines, incised fan-head trenches, and highway embankments.
- **Difference from repo lanes:** Models multi-scale morphological diffusion decay across $\sigma \in \{1, 3, 6\}$ rather than single-scale cross-gradients.

### Rank 4 (Untried External-Data Option — Verified Obtainable with Caveats): `RDC-88` — USGS 3DEP Flow-Routing Cross-Drainage Beheaded/Deflected Channel Alignment
- **Exact layers & verified official external source:** Band `12` (`det_elev`), Band `19` (`det_elev_slope`), plus public USGS 3DEP 1/3 arc-second (~10 m) seamless DEM tiles on AWS Open Data (`https://prd-tnm.s3.amazonaws.com/`, public domain, verified obtainable without login; blocked in sandbox only by outbound host allowlist, requiring offline tile mirror if run inside sandbox).
- **Physical transform:** D8 drainage-network extraction and axial alignment of abrupt stream-azimuth deflections ($\Delta\psi \in [55^\circ, 110^\circ]$) and knickpoint steps across >=3 parallel piedmont washes along a shared strike corridor.
- **Why it catches off-catalogue faults:** Active oblique-normal and Walker Lane dextral faults systematically offset or pond ephemeral piedmont washes even when eolian silt erases the interfluve scarp.
- **Named non-fault mimic:** Resistant tilted volcanic hogbacks, irrigation canals, and railroad grade diversions.
- **Difference from repo lanes:** Uses hydrological network topology rather than local pixel convolution.

### Rank 5 (Untried External-Data Option — Verified Public on DOE GDR 1391): `SDT-88` — INGENIOUS Regional Slip & Dilation Tendency Resolvability Gate
- **Exact layers & verified official external source:** DOE Geothermal Data Repository Submission `1391` (*Great Basin Regional Dataset Compilation*, Faulds et al., UNR, `DOI: 10.15121/1881483`, CC BY 4.0, verified public at `https://gdr.openei.org/submissions/1391`), specifically USGS slip & dilation tendency resource (`DOI: 10.5066/P9YL58W6`) projected onto the local strike $\theta_{\text{mp}}(y,x)$ inferred from `STR-88` (`det_elev`, `rtp`, `iso_grav_anom`) plus Bands `7` (`geod_shearrate`), `8` (`geod_dilaterate`), `10` (`deq_n100a15`), `16` (`ieq_n100a15`).
- **Physical transform:** Resolves regional principal horizontal stress azimuth $S_{H\max}$ onto candidate fault strike $\theta_{\text{mp}}$ to weight normal/oblique orientations near optimal Mohr–Coulomb dilation/slip tendency ($\approx 0^\circ\text{–}35^\circ$ from $S_{H\max}$), gating geophysical crests by mechanical permeability potential.
- **Why it catches off-catalogue faults:** Geothermal-hosting permeable faults preferentially occupy critically stressed strike orientations relative to modern $S_{H\max}$, separating active dilational structural conduits from ancient Mesozoic thrust/intrusive contacts oriented unfavorably in the modern stress field.
- **Named non-fault mimic:** Critically oriented basaltic dike swarms and joint sets without shear offset.
- **Difference from repo lanes:** Introduces explicit directional stress-tensor mechanics on strike azimuth rather than isotropic scalar strain invariants.
