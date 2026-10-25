# Five Ranked, Source-Verified Untried Geological Hypotheses — Session `587c7f22` (`2026-10-25`)

**Status: Conditional proposals only (`0` new experiments executed, `0` new TIFFs generated, `0` weekly slots spent).**
The user prompt supplies no single-method paragraph, and the unchanged shared preflight (`python scripts/preflight_mtas88.py --gate-generation` / `python scripts/generation_guard.py`) returns **`DUPLICATE_STOP`** (exit `2`) before feature construction because SHA-pinned `data/registry/dense_17gemdoe.tif` (`ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) has finite positive values (`> 0`) on `5,167,373` pixels covering **`5,106,385 / 5,106,385` (`100%`)** of allowed footprint cells (literal 3-px forward overlap `= 1.0000 > 0.70`). In addition, `GEMSDOE87`'s `gems87-bmtd-20261022-50041440adba-RESEARCH-DO-NOT-SUBMIT.tif` has `4,532,408` positive pixels (`0.891220 > 0.70` literal overlap on `H88-CON88`).

## 1. Pre-Coding Implementation Audit: Retiring `H88-CON88` Alongside Previously Evaluated Lanes

Before proposing any hypothesis, all `154` model/runner files across `src/gems88/*.py`, `vendor/gems57/*.py`, and `scripts/{run,build,generate}_*.py` (`source_snapshot` SHA-256 `062d23ee578ea5488049870d51be30cd75802f8e4f762ed42e9c792a47b42042`) were audited:

- **Retired in this session (`IR-88-587C7F22-01`):** **`H88-CON88`** (`scripts/run_con88_experiment.py`, PR `#158`) executed cross-fleet consensus voting (`GEMSDOE49`, `GEMSDOE70`, `H88-BPWD`) blended with a label-blind magnetic/gravity/topographic ridge (`HOLDOUT-DTI = 0.001714 [0.001325, 0.002143]`, evaluator `gems57-pooled-hide-v2`, `n = 60,988` withheld positives on 4 quadrant folds; fixed-TIF `HOLDOUT-DTI = 0.0000` vs same-fold `H33` `0.006697 [0.005990, 0.007368]`). Its unauthorized `ok_to_submit: true` equal-support clearance is withdrawn to `verdict: "negative"` ([withdrawal certificate](https://buffedlizard55-lab.github.io/GEMSDOE88/data/con88_clearance_withdrawal_20261025.json)) and recorded in `already_evaluated` in the [source-bound JSON queue](https://buffedlizard55-lab.github.io/GEMSDOE88/data/hypothesis_queue.json).
- **Previously retired and excluded:** `H88-MMRX` (`mmrx.py` magnetic-marker restoration), `H88-MTAS` (`mtas.py` cross-scale admittance), `H88-MFS` (`mfs88.py` multifractal gradient scaling), `H88-PGTD` (`pgtd88.py` harmonic Marussi tensor dimensionality), `H88-BPWD`/`PSGV` (`bpwd.py`/`psgv.py` Baranov pseudogravity + upward-continued worms), `H88-HGVC`/`VCAZ`/`VHGD`/`BGCD` (hydrothermal up-dip outflow, vapor-chimney/tufa partitioning, 2-m probe Peclet concavity, geothermometer disequilibrium), `H88-TDKL`/`QTSK`/`VESS`/`LSC`/`QTS` (in-channel knickpoints, vesselness, local scarp filters, cover-thickness decoupling), and `H88-SDTL` (`sdtl.py` stress slip/dilation tendency).

All **five** hypotheses below are verified unimplemented in this checkout and require **only SHA-pinned cached layers already restored on disk** (`0` unobtainable external downloads). Expected DTI upside is strictly ordinal/qualitative — **never a numerical score projection**.

---

## 2. Five Ranked Untried Geological Hypotheses (Expected Gain vs Implementation Cost)

| Rank | ID | Mechanism Summary | Cached Layers (Verified Band Tags on `3292×3730` `EPSG:32611` Grid) | Named Non-Fault Mimic | Qualitative Upside / Cost |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Pick)** | **`H88-SPR`** | Cross-validated along-strike scarp-profile throw restoration likelihood ratio vs zero-step fan/shoreline null | `training_features.tif` `B12 (det_elev)`, `B19 (det_elev_slope)`; `topo_10m_derived_100m_u8.tif` `B8 (hs_lineament)`, `B9 (dem_mean)`; `lidar_scarp_features_u8.tif` `B3 (step_max)`, `B10 (coh100)`, `B11 (strike)`, `B12 (valid)`; `dem10_chi_100m_u8.tif` `B1 (chan_n)`, `B4 (valid_n)` | Fluvial terrace risers (`chan_n > 0`) & constant-elevation Lake Lahontan wave-cut shoreline benches | **Moderate** (uncertain) / **Medium** (canonical queue #1) |
| **2** | **`H88-AWA`** | Terrain-matched cross-strike radiometric alteration decay-width asymmetry (`K`, `Th`, `U` flank half-widths around `rtp` troughs) | `geodawn_rad_u8.tif` `B1 (K)`, `B2 (Th)`, `B3 (U)` (quantized `uint8` survey codes); `training_features.tif` `B2 (rtp)`, `B15 (depth_to_base_surf)`, `B19 (det_elev_slope)` | Differential weathering across unfaulted felsic/mafic contacts & K-rich alluvial fan aprons | **Low–Moderate** (uncertain) / **Medium** (canonical queue #2) |
| **3** | **`H88-CBC`** | Saddle-constrained cross-basin electrical conductivity breach percolation vs axial paleochannel/playa brine null | `training_features.tif` `B12 (det_elev)`, `B13 (iso_grav_anom)`, `B15 (depth_to_base_surf)`, `B17 (cond_surf)`; `dem10_chi_100m_u8.tif` `B1 (chan_n)`, `B4 (valid_n)` | Unfaulted permeable axial paleochannels & closed-basin playa evaporite brine lenses | **Low** (coarse `cond_surf`) / **Medium–High** (canonical queue #3) |
| **4** | **`H88-DRP`** | Paired cross-divide $\chi$ / $k_{sn}$ polarity reversal across distinct headwater branch boundaries conditioned on basement gravity slope | `dem10_chi_100m_i16.tif` `B1 (step_max_x1000)`, `B2 (step_min_x1000)`, `B3 (ksn_max_m0.9)`, `B4 (log10_area_m2_x1000)`, `B5 (zmean_m)`; `dem10_chi_100m_sig_i32.tif` `B1 (branch_signature_global_index_100m)`; `training_features.tif` `B5 (iso_grav_anom_slope)`, `B15 (depth_to_base_surf)` | Unfaulted volcanic/sedimentary caprock erodibility divides & high-elevation (`zmean_m`) Pleistocene cirque headwalls | **Low–Moderate** (uncertain) / **Medium** (extended dossier #4) |
| **5** | **`H88-TMA`** | Cross-scale magnetic horizontal-gradient azimuth twist ($\Delta\theta$) separating surficial volcanic-clast fan clutter from deep basement strike | `training_features.tif` `B1 (mag_anom)`, `B2 (rtp)`, `B3 (tmi_hg)`, `B9 (tmi_vg)`, `B14 (tmi)`, `B18 (iso_grav_anom_hg)`; `geodawn_extensions_u8.tif` `B4 (TMI_up150)` | Unfaulted reversely magnetized Miocene feeder dikes & buried paleovalley basalt flows | **Low** (uncertain) / **Low–Medium** (extended dossier #5) |

---

### Detailed Specification of Each Hypothesis

#### Rank 1 (Selected Conditional Candidate): `H88-SPR` — Cross-Validated Along-Strike Scarp-Profile Restoration
- **Exact feature layers:** `data/training_features.tif` `B12 (det_elev)`, `B19 (det_elev_slope)`; `data/external/topo_10m_derived_100m_u8.tif` `B8 (hs_lineament)`, `B9 (dem_mean)`; `data/external/lidar_scarp_features_u8.tif` `B3 (step_max)`, `B10 (coh100)`, `B11 (strike)`, `B12 (valid)`; `data/external/dem10_chi_100m_u8.tif` `B1 (chan_n)`, `B4 (valid_n)`.
- **Physical signature & mathematical transform:** Along strike-oriented interfluve swaths (`strike` B11, gated by `valid > 0` and masked away from active drainage `chan_n > 0`), fit a smooth regional bajada polynomial $z_0(u)$ versus a faulted step-restoration model $z_1(u) = z_0(u) + \Delta h \, H_{\sigma}(u - u_0)$ on odd cross-strike profiles and evaluate the out-of-sample log-likelihood gain $\Delta \ell = \ell_1 - \ell_0$ on interleaved held-out swaths, requiring consistent throw sign ($\operatorname{sign}(\Delta h)$) and non-zero elevation transience ($\partial_s z(u_0) \neq 0$ on `dem_mean`) to reject horizontal shoreline contours.
- **Why it catches faults missing from USGS QFaults / INGENIOUS:** Low-slip (`< 0.1 mm/yr`), eolian-mantled or segmented intrabasin piedmont faults lack crisp aerial-photo scarps required by compilation mappers, yet preserve coherent decimetre-to-metre cumulative vertical surface offset across independent interfluves without referencing `existing_faults.tif`.
- **Named non-fault mimic:** Fluvial terrace risers (`chan_n > 0`) and constant-elevation Pleistocene pluvial Lake Lahontan shoreline benches (`dem_mean` contour-parallel steps).
- **Difference from repo methods:** `LSC`, `TDKL`, `VESS`, and `SHORE` apply local scarp amplitude filters, knickpoint products, or shoreline distance masks; `MMRX` restores magnetic texture horizontally; none fits cross-validated topographic throw restoration across independent strike swaths.

#### Rank 2: `H88-AWA` — Terrain-Matched Radiometric Alteration-Width Asymmetry
- **Exact feature layers:** `data/external/geodawn_rad_u8.tif` `B1 (K)`, `B2 (Th)`, `B3 (U)` (decoded via pinned manifest as quantized indices, never divided as physical concentrations); `data/training_features.tif` `B2 (rtp)`, `B15 (depth_to_base_surf)`, `B19 (det_elev_slope)`.
- **Physical signature & mathematical transform:** Across candidate `rtp` magnetic-destruction troughs, residualize `K`, `Th`, and `U` against slope (`det_elev_slope`) and basin cover (`depth_to_base_surf`) inside training folds only, then fit cross-strike half-Gaussian decay widths ($w_{+}, w_{-}$) on opposing walls to measure persistent hanging-wall vs footwall dispersion asymmetry $|w_{+} - w_{-}| / (w_{+} + w_{-})$.
- **Why it catches missing faults:** Blind hydrothermal range-front or intrabasin conduits sealed by colluvium lack geomorphic scarps, but permeable hanging-wall damage zones disperse argillic/potassic alteration broadly down-dip whereas clay-gouge footwalls truncate sharply.
- **Named non-fault mimic:** Differential weathering across unfaulted felsic-tuff/mafic-lava contacts and K-rich transported alluvial fan aprons.
- **Difference from repo methods:** `KTH`, `MVRD`, `BGCD`, and `VCAZ` use point radiometric levels or Efimov-style ratios; none fits asymmetric cross-strike spatial decay widths.

#### Rank 3: `H88-CBC` — Saddle-Constrained Cross-Basin Conductive Breach Connectivity
- **Exact feature layers:** `data/training_features.tif` `B12 (det_elev)`, `B13 (iso_grav_anom)`, `B15 (depth_to_base_surf)`, `B17 (cond_surf)`; `data/external/dem10_chi_100m_u8.tif` `B1 (chan_n)`, `B4 (valid_n)`.
- **Physical signature & mathematical transform:** Locate structural saddles separating `depth_to_base_surf` sub-basins and compute minimax path-conductivity percolation (`cond_surf`) across bedrock highs, requiring transverse `iso_grav_anom` step and penalizing paths coaxial with surface channels (`chan_n`) or closed playa floors (`det_elev` local minima).
- **Why it catches missing faults:** Deeply buried transverse accommodation and transfer faults (`depth_to_base_surf > 500 m`) never rupture Quaternary alluvium at the surface, so USGS QFaults omits them, yet smectite/brine fault damage zones create conductive bridges across basement saddles.
- **Named non-fault mimic:** Unfaulted permeable alluvial paleochannels and saline playa groundwater plumes.
- **Difference from repo methods:** `CTRA`, `DHTC`, and `GZZC` use local conductivity curvature or point thermal conjunctions; `GEODESIC_RELAY` bridges *visible catalogue tips*; `H88-CBC` tests zero-catalogue topological percolation across basement saddles.

#### Rank 4: `H88-DRP` — Paired Cross-Divide $\chi$ / $k_{sn}$ Polarity Reversal Across Accommodation Highs
- **Exact feature layers:** `data/external/dem10_chi_100m_i16.tif` `B1–B5 (step_max_x1000, step_min_x1000, ksn_max_m0.9, log10_area_m2_x1000, zmean_m)`; `data/external/dem10_chi_100m_sig_i32.tif` `B1 (branch_signature_global_index_100m)`; `data/training_features.tif` `B5 (iso_grav_anom_slope)`, `B15 (depth_to_base_surf)`.
- **Physical signature & mathematical transform:** Along watershed divides where adjacent pixels carry distinct `branch_signature_global_index_100m` IDs at low drainage area (`log10_area_m2_x1000`), compute cross-divide steepness contrast $\Delta k_{sn}$ and signed $\chi$-step polarity (`step_max_x1000 + step_min_x1000`) gated on co-directional `iso_grav_anom_slope`. Active relay-ramp back-tilting drives systematic divide migration without discrete scarps.
- **Why it catches missing faults:** Distributed relay ramps deform drainage divides aseismically or via micro-fracturing without creating aerial-photo scarps mapped in QFaults.
- **Named non-fault mimic:** Resistant volcanic caprock hogbacks and high-altitude (`zmean_m > 2500 m`) Pleistocene glacial cirque headwalls.
- **Difference from repo methods:** `TDKL`/`QTSK` measure *in-channel* knickpoints; `VCAZ` uses `branch_signature_global_index_100m` only as a scalar piracy indicator; none computes paired cross-divide $\Delta k_{sn}$ polarity across branch boundaries.

#### Rank 5: `H88-TMA` — Cross-Scale Magnetic Upward-Continuation Azimuth Rotation ($\Delta\theta$)
- **Exact feature layers:** `data/training_features.tif` `B1 (mag_anom)`, `B2 (rtp)`, `B3 (tmi_hg)`, `B9 (tmi_vg)`, `B14 (tmi)`, `B18 (iso_grav_anom_hg)`; `data/external/geodawn_extensions_u8.tif` `B4 (TMI_up150)`.
- **Physical signature & mathematical transform:** Compute the acute orientation twist $\Delta\theta = \arccos(|\hat{g}_{\text{shallow}} \cdot \hat{g}_{\text{deep}}|)$ between shallow magnetic gradient orientation (`tmi_hg` / `TMI_up150`) and 1–3 km upward-continued `rtp` + `iso_grav_anom_hg` strike, isolating linear deep basement corridors masked at the surface by oblique down-fan volcanic boulder detritus.
- **Why it catches missing faults:** Across Miocene volcanic ranges in GeoDAWN, strongly magnetized basalt/tuff clast fans generate high-amplitude down-slope magnetic stripes that obscure oblique basement faults in both field mapping and single-scale gradient detectors.
- **Named non-fault mimic:** Unfaulted reversely magnetized Miocene feeder dikes and buried paleovalley lava flows.
- **Difference from repo methods:** `BPWD`/`PSGV` align Baranov pseudogravity and upward-continued worms; `MTAS` tests topo-gravity admittance; `MFS` tests isotropic gradient decay; none isolates scale-space magnetic azimuth rotation ($\Delta\theta$).

---

## 3. Minimal Validation Experiment Design for Top Pick (`H88-SPR`) — Held at Pre-Placement Gate

1. **Prerequisite Gate (Currently Blocking):** Re-run `python scripts/generation_guard.py`. Unless the shared protocol contract is explicitly revised by the user/selector regarding saturated registry priors (`17GEMSDOE`, `GEMSDOE87:gems87-bmtd`), stop immediately with `0` experiments run.
2. **Minimal 1-Experiment Falsification Test (Only if Unblocked):**
   - Construct `6` zero-catalogue `H88-SPR` channels inside each fold of the shared buffered whole-component split (`vendor/gems57/evaluate_holdout.py`, evaluator `gems57-pooled-hide-v2`, `alpha=0.2, beta=0.8`, 300 m triangular kernel, `n = 22,893` withheld positives across `seeds 20+21`).
   - Run single-feature leakage canary (`max(AUC, 1-AUC) <= 0.90` mandatory; expect `< 0.65` for genuine zero-catalogue landform restoration) plus two mandatory null falsifiers: (a) cross-swath sign-scramble null and (b) contour-following shoreline synthetic step null.
   - Compare `BPWD + SPR` against fold-rebuilt incumbent `H88-BPWD` (`HOLDOUT-DTI = 0.205991 [0.188105, 0.223344]`) on identical folds, pixel-exact visible-catalogue masks, and dot budget. Reject immediately unless the paired physical-block 95% CI on $\Delta\text{DTI}$ is strictly positive (`> 0`) AND both pre-placement `|Spearman \rho| <= 0.90` and post-placement literal 3-px overlap `<= 0.70` pass across the complete restored registry (`data/registry` + `data/siblings` + `data/fleet` + `docs/downloads` + `submissions`).
   - Never spend a weekly submission slot without passing all gates AND a separate selector authorization within the authenticated portal quota.

## 4. Official Public Source Provenance

- **Freshly retrieved in session `587c7f22` (`github.com` allowlisted):**
  - [Official DrivenData GEMS Reference Solution README (`aebe92f7`)](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md) — confirms CPU (`--extra cpu` / `environment-cpu.yml`) and GPU (`cu126` / `cu130`) workflows.
  - [Pinned `GEMSDOE32` H33 Build Record (`012e17b2`)](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/registry/submission_build.json) — confirms `H33` (`c55bafc4...`) is a `37,654`-dot `d_cat <= 2 px` prune of the `40,199`-dot `0.2708` base with no organizer receipt in git.
- **Official reference URLs for manual review (outside sandbox network allowlist; not freshly fetched in this session):**
  - [DrivenData DOE GEMS Problem Page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [Submissions](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/)
  - [NLR / NREL Official Prize Rules PDF (`96647.pdf`)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
  - [USGS GeoDAWN Airborne Magnetic & Radiometric Survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
  - [DOE Geothermal Data Repository — INGENIOUS Regional Dataset (`#1391`)](https://gdr.openei.org/submissions/1391)
  - [USGS 3D Elevation Program (3DEP)](https://www.usgs.gov/3d-elevation-program)
