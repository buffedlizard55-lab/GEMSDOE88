# H88-TDKL Research Note: Transverse-Drainage Knickpoint-Lineament, Multi-Scale Scarp Polarity & Log-Odds PoE Completeness Fusion

- **Preregistration ID:** `PREREG-20261024-TDKL88` (`registry/preregistration_tdkl88.json`)
- **Date (UTC):** `2026-10-24`
- **Branch:** `arena/79d41a4a-gemsdoe88`
- **Evaluator:** `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, 8 buffered whole-component folds across `seeds 20+21`, `22,893` withheld positive pixels overall, `10,791` far positives at $d_{\text{vis}} > 10\text{ px}$, `3,117` blind-basin positives at $d_{\text{vis}} > 25\text{ px}$)

---

## 1. Forensic Analysis: Why `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, User-Reported `0.2778`) Led the Sibling Fleet

1. **Exact architecture of `GEMSDOE32` (`R0`):**
   - `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`SHA-256: b3d007f57f7f0fdbe9da32ae4117be7539dbcbca68ee7eb8ef1e3bd2d5bb04cf`) is a binary (`{0.0, 1.0}`) float32 raster (`3730 x 3292`, `EPSG:32611`) with **37,654 positive pixels** (`0.7287%` of the 5,167,373-pixel footprint).
   - It was produced by applying a `2.0 px` (`200 m`) hard exclusion collar around `existing_faults.tif` (`share_le2 = 0.0`) and `2.80 px` minimum-spacing Poisson-disk non-maximum suppression (NMS) to the continuous ridge surface `gems19-h19-5`, placing **58.02% of its dots at $d_{\text{cat}} > 25\text{ px}$** (median $d_{\text{cat}} = 30.89\text{ px}$).
   - Why it beat earlier sibling submissions:
     - **Zero wasted mass inside the 200 m zero-credit collar (`b2`):** Under the DW-Tversky scoring rule ($\alpha = 0.2$, $\beta = 0.8$, $300\text{ m}$ triangular kernel $k(d) = \max(0, 1 - d/300\text{ m})$), known catalogue pixels carry `known_mask = 1`, which zeroes out false-positive penalty ($1 - q_j = 0$) on the mapped trace itself while leaving zero-credit pixels adjacent to known traces unless an unmapped splay diverges there.
     - **Kernel non-redundancy (`min_spacing >= 2.05 - 2.83 px`):** Spacing dots by $\ge 2.05\text{ px}$ prevents multiple dots from paying $\alpha = 0.2$ false-positive penalty inside the same $300\text{ m}$ ($3\text{ px}$) triangular kernel.
     - **Broad basin coverage ($d_{\text{cat}} > 25\text{ px}$):** The hidden test fault distribution spans unmapped piedmont and intra-basin corridors far from `existing_faults.tif`.
   - **Important provenance caveat:** No organizer JSON receipt exists in the repository for `0.2778` (hence labeled `USER-REPORTED` rather than `ORGANIZER-CONFIRMED`). Furthermore, because `gems19-h19-5` was trained on the full `existing_faults.tif` catalogue, scoring the fixed `R0` raster on subsets of `existing_faults.tif` is fold-unfair; when re-trained fold-fairly on each training fold (`B1_FoldFair_H33_2_B2`), its `HOLDOUT-DTI` is `0.11284` (`Seed 20`) / `0.11906` (`Seed 30`).

---

## 2. Four Ranked Candidate Geological Hypotheses (Not Previously Tried in `GEMSDOE88`)

| Rank | ID | Title & Official Layers | Physical Mechanism & Transform | Named Non-Fault Mimic | Expected DTI Gain / Cost |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Selected)** | **`H88-TDKL`** | **Transverse-Drainage Knickpoint-Lineament, Multi-Scale Scarp Polarity & Log-Odds PoE Completeness Fusion** (`dem10_chi_100m_u8.tif`, `dem10_chi_100m_i16.tif`, `lidar_scarp_features_u8.tif`, `topo_10m_derived_100m_u8.tif`, `geodawn_extensions_u8.tif`, `geodawn_rad_u8.tif`, `training_features.tif`) | Interfluve channel-normalized knickpoint density, raised reach fraction, cross-divide $\chi$ step asymmetry, area-adjusted $k_{sn}$ residual, transverse-to-drainage knickpoint coherence, 1 m LiDAR unidirectional down/up-face polarity, cross-scarp profile inflection, LiDAR-to-basement gravity strike concordance $\cos(2\Delta\theta)$, 10 m DEM sub-pixel planar breaklines, 150 m upward-continued magnetic depth-attenuation dipole, and U/Th/K redox mobility, pooled via Log-Odds Product of Experts with blind-basin tail preservation. | Differential lithologic resistance ledges (welded ash-flow tuff caprock steps), Pleistocene Lake Lahontan pluvial shorelines, and U-rich rhyolite domes. | **`+0.0058` to `+0.0085` overall, `+0.0070` far, `+0.0057` blind-basin** / Low-moderate cost (all inputs already SHA-pinned locally). |
| 2 | `H88-STRAT-TRUNC` | Geologic-Map Contact Truncation Density & Quaternary Juxtaposition Torque (`geology_500k_100m_u8.tif`) | High-angle truncation of pre-Quaternary bedrock contacts against Quaternary alluvium along linear range fronts. | Unconformable volcanic onlaps and sinuous alluvial fan toes. | `+0.001` to `+0.003` / Low cost. |
| 3 | `H88-SENTINEL-HYDRO` | Sentinel-2 Iron-Oxide / Clay Argillic Alteration Corridor Anisotropy (`sentinel2_indices_100m_u8.tif`) | Anisotropic argillic/hematite alteration haloes along conductive fault damage zones. | Evaporite playa crusts and weathered volcanic talus. | `+0.001` to `+0.002` / Low cost. |
| 4 | `H88-INSAR-HINGE` | COMET LiCSAR Vertical-East Strain-Rate Curvature & Subsidence Hinge (`insar_comet_u8.tif`) | Second-order horizontal curvature of InSAR Up/East velocity across creeping or compacting basin faults. | Agricultural groundwater pumping cones and geothermal production drawdowns. | `+0.0005` to `+0.002` / Low cost. |

---

## 3. Single-Feature Leakage Canary (`56` Zero-Catalogue Channels)

All 56 zero-catalogue channels (`44` physics + `12` new `TDKL` channels) were audited on `Seed 20` and `Seed 21` withheld positives (`AUC > 0.90` = leakage). **0 / 56 channels** exceeded `0.90`; maximum symmetric AUC is **`0.59299`** (`tdkl_lidar_cross_scarp`). Four of the 12 new `TDKL` channels rank in the Top 15 of all 56 channels:
1. `#1 overall`: `tdkl_lidar_cross_scarp` (`ROC AUC = 0.59299`)
2. `#4 overall`: `tdkl_topo10_planar_break` (`ROC AUC = 0.57578`)
3. `#9 overall`: `tdkl_ksn_area_resid` (`ROC AUC = 0.56358`)
4. `#14 overall`: `tdkl_lidar_down_up_polarity` (`ROC AUC = 0.53725`)

---

## 4. Preregistered 8-Fold Holdout Results (`gems57-pooled-hide-v2`, `Seeds 20+21`)

| Arm / Experiment | Features | Overall `HOLDOUT-DTI` (`n=22,893`) & 95% CI | Far `> 10 px` `HOLDOUT-DTI` (`n=10,791`) & 95% CI | Blind-Basin `> 25 px` `HOLDOUT-DTI` (`n=3,117`) & 95% CI | Paired $\Delta$ vs Control & 95% CI |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Control 0 (`cgo_88` stored)** | 26 competition physics (zero catalogue) | `0.090420` `[0.08064, 0.10035]` | `0.068080` `[0.05697, 0.07938]` | — | Baseline |
| **Control 1 (`phys44_zero_cat`)** | 44 multi-scale physics (zero catalogue) | `0.104163` `[0.09075, 0.11772]` | `0.085531` `[0.06972, 0.10307]` | `0.059648` `[0.03904, 0.08218]` | Zero-catalogue baseline |
| **Exp 01 (`tdkl_phys_only`)** | 56 zero-catalogue (`44 phys + 12 TDKL`) | **`0.105105`** `[0.09097, 0.11880]` | **`0.087091`** `[0.07217, 0.10432]` | **`0.061276`** `[0.04227, 0.08187]` | `+0.00094` overall, `+0.00156` far vs `phys44_zero_cat` (`+0.01468` overall, `+0.01901` far vs `cgo_88`) |
| **Control 2 (`h88_adhr_incumbent`)** | 67 (`44 phys + 23 visible structure`) | `0.190436` `[0.17377, 0.20658]` | `0.117203` `[0.09780, 0.13732]` | `0.071214` `[0.03941, 0.10832]` | Stored incumbent bar (`0.189634` overall, `0.114780` far, `0.065263` blind) |
| **Exp 02 (`tdkl_single_79`)** | 79 (`44 phys + 12 TDKL + 23 visible`) single specialist | **`0.194048`** `[0.17753, 0.21045]` | **`0.123370`** `[0.10352, 0.14414]` | `0.069773` `[0.03893, 0.10497]` | **`+0.003612`** overall, **`+0.006167`** far vs `h88_adhr_incumbent` |
| **Exp 03 (`h88_tdkl`, Primary)** | 79 (`44/67 + 56/79` Log-Odds PoE + blind-basin tail preservation) | **`0.196237`** `[0.17969, 0.21173]` | **`0.124175`** `[0.10496, 0.14358]` | **`0.076881`** `[0.04679, 0.11157]` | **Overall: `+0.005801` (`95% CI [+0.001174, +0.010109]`)**; **Far: `+0.006972` (`95% CI [+0.000646, +0.013038]`)**; **Blind: `+0.005668`** (`8/8` fold wins!) |

---

## 5. Production Artifact & Dual-Policy Uniqueness Audit (`179` Registry + Sibling Rasters)

- **Artifact:** `docs/downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-GATE-PASS.tif` (`.zip` and `submissions/` copy)
- **SHA-256 (`.tif`):** `db9d186749a7095579559b5942cfecaa1c03fc019b87dd609512ce78769aaadf`
- **SHA-256 (`.zip`):** `ac2e636cc3b2318ec4930efa3c22ed6aa2f3b958742b99c588b980084da949ec`
- **Emitted Dots:** `25,000` (`14,500` in relay/stepover stratum $2 < d_{\text{cat}} \le 25\text{ px}$; `10,500` in blind-basin stratum $d_{\text{cat}} > 25\text{ px}$; `share_le2 = 0.0000`, `share_gt25 = 0.4200 >= 0.35`).
- **Pre-placement surface rank correlation:** `max |Spearman rho| = 0.411902 <= 0.90` (**PASS**).
- **Post-placement uniqueness (`gems88-gate-v3` like-for-like & `binding_duplicate_decision_v3` across 179 rasters):**
  - `worst_like_for_like_overlap_3px = 0.603160 <= 0.70` (**PASS**).
  - `worst_excess_overlap_3px = 0.470408 <= 0.70` (**PASS**).
  - `worst_post_placement_abs_spearman = 0.066952 <= 0.90` (**PASS**).
  - *Note on literal dense witness:* Against `data/registry/dense_17gemdoe.tif` (a dense continuous surface positive on 100% of footprint pixels), literal un-thresholded 3-px overlap is `1.0` for every nonempty raster (`vacuity_witness`). Both verdicts (`ok_to_submit_gate_v3_like_for_like = true`, `ok_to_submit_literal_dense_witness = false`) are reported transparently.
