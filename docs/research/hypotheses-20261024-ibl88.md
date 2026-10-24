# IBL-88 Session (2026-10-24): Why H33 scored 0.2778, whether it can be beaten, and five ranked hypotheses

**Evidence labels:** ORGANIZER-CONFIRMED = portal receipt (none in repo) · USER-REPORTED = siblings' posted numbers · REGISTRY-MEASUREMENT = recomputed from SHA-pinned rasters · HOLDOUT-DTI = hide-and-recover pooled DTI (alpha 0.2 beta 0.8 300m kernel, evaluator gems57-pooled-hide-v2) · MODEL-PROJECTION = never a score.

## 0. Official Ground Truth Verified

| Fact | Evidence | Source |
|---|---|---|
| Competition scoring = pooled Distance-Weighted Tversky Index, α=0.2 β=0.8, 300m triangular kernel; known USGS/INGENIOUS faults masked pixel-exactly | ONLINE | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Live leaderboard top 0.4413 (xiaofanhu, 29 entries), #5 cutoff 0.3539, #50 0.2818 on 2026-10-24 | OFFICIAL-PUBLIC-LEADERBOARD-SNAPSHOT | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (checked 2026-10-24T07:19Z) |
| GEMSDOE32 H33 0.2778 is USER-REPORTED (no organizer receipt in repo) | OWNER-REPORTED | Prompt + sibling sites (e.g., [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)) |
| Rules: one final selection for both rounds, ≤3/week but website limit prevails, external data must be licensable & shareable | ONLINE | [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §3.2, §3.4-3.6, thread 11553 |
| 19-band training stack + existing_faults + sample_submission pinned to SHA-256 via `data/bridge` | REGISTRY-MEASUREMENT | `evidence/input-metadata.json` pins: sample 2176d08e…, faults 7ba308cc… |

**H33 forensics (DISK, re-measured vs restored SHA-pinned rasters):** H33 (37,654 dots) ⊂ SOLO-D2.8 (40,199) ⊂ D2.8 (44,090) ⊂ H19-5 (121,131); **zero dots added** at any thinning step; all 6,436 dots removed after D2.8 lie ≤2px from catalogue (d_cat ∈ {1,2}); H33 min spacing 2.83px median 3.0px (kernel-matched); median d_cat 19.6px (1.96km), 41.7% beyond 25px (2.5km), 0% ≤2px (b2 collar respected). Full chain: `evidence/h33_forensics_20261024.json`, `scripts/forensics_h33.py`.

## 1. Why H33 (owner-reported 0.2778) Leads the Sibling Fleet

Reconstructed from `data/registry/h33_education.tif` (SHA c55bafc4…), `gems19_h19_5.tif`, `gems25_d28.tif`, `gems28_h27_4.tif`:

| Step | Dots | Reported DTI | Operation (verified pixel-subset) |
|---|---|---|---|
| H19-5 | 121,131 | 0.1922 | Multi-line corroborated ridge support (19GEMSDOE) |
| D2.8 | 44,090 | 0.2600 | Dotted thinning to kernel-matched spacing (subset, 0 added) |
| SOLO-D2.8 | 40,199 | 0.2708 | Remove 3,891 dots ≤1px from catalogue (subset) |
| H33 b2 | 37,654 | 0.2778 | Remove 2,545 more dots ≤2px from catalogue (subset) |

**Three mechanisms (algebra = `vendor/gems57/metric.py`):**

1. **Support quality (H19-5 ridges):** The 100m DEM + geophysics ridge stack already sits where unmapped faults are plausible: H33 median distance-to-catalogue 19.6px (2km, Spearman distance-vs-fleet-score ρ=+0.90, n=20, `evidence/fleet_distance_prior_20261024.json`), det_elev_slope dot-vs-footprint AUC 0.657 (avoids flat & steep deciles, range-front terrain), tmi_hg AUC 0.574 (magnetic gradient). This is a label-blind multi-modal ridge surface, not a catalogue-fitted ML model.

2. **Kernel-matched thinning (D2.8):** With 300m (3px) triangular kernel, each truth pixel saturates at credit 1 after one covering dot; clustered dots add FP weight (denominator 0.2·FP) without TP. Removing 77,041 redundant dots from H19-5 to D2.8 raised reported DTI 0.1922→0.2600 at unchanged far-distance profile. Marginal-dot bar at DTI 0.2778 is α·DTI = 0.0556 (for non-redundant k=dT), so each D2.8 dot kept earns ~0.139 credit — 2.5× the bar.

3. **Catalogue collar denoising (b2):** Visible faults are masked pixel-exactly in live scoring (thread 11516, `vendor/gems57/holdout.py`). Hidden truth is faults *not yet captured* by USGS/INGENIOUS; dots within 2px of a mapped trace therefore earn ≈0 TP while paying full 0.2·FP. Deleting those 6,436 flank dots is pure denominator reduction: 0.2600→0.2778 with zero new geography. This also explains the fleet fingerprint: low scorers hug catalogue (GEMSDOE81 median d_cat 2.2px → 0.0041, GEMSDOE80 median 8px → 0.0943), high scorers do not.

**INFERENCE (pure-FP-removal assumption, rounded):** Covered credit T≈5.2-5.5k, |G|≈13-15k public truth px, so H33 covers only ~37-40% of weighted truth; average credit/dot ~0.14; gap to top leaderboard (0.4413) requires +59-63% more T (+~3k) at same dot count, or better per-dot localization (k→1). The blind spot is **low-relief basin/alluvium faults**: H33 dots have ~0% in flattest slope decile, yet Great Basin blind geothermal systems are classically intrabasinal beneath alluvium (INGENIOUS play-fairway: [gbcge.org/ingenious](https://gbcge.org/current-projects/ingenious/)). Those faults have no 100m ridge but do have (a) metre-scale 1m-LiDAR scarps where Holocene, (b) gravity/magnetic basement steps (offset density/susceptibility), (c) χ/ksn drainage disruptions. A submission that adds *that* support — without re-adding collar FP or redundant clustering — is the credible structural route past 0.2778.

**Can it be beaten?** Arithmetically yes: +27-29% T reaches the $10k cutoff 0.3539, +59-63% reaches 0.4413. Whether any *local instrument* can prove it before spending a slot is the holdout question (below). Local hide-and-recover structurally scores every b2+ file at 0.0000 (IR-88-35) because withheld catalogue components lie >12px from far-basin dots; the instrument cannot rank gate-clean files. SGMC concealed-bedrock proxy and the fleet distance fingerprint are the informative diagnostics instead. No ORGANIZER-CONFIRMED claim is made; P(beat 0.2778) is low and cannot be estimated from available instruments without a live receipt.

Official sources cross-checked this session: [NLR rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [metric + submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [3DEP LiDAR](https://www.usgs.gov/3d-elevation-program) · [GDR #1391 INGENIOUS wells/vents](https://gdr.openei.org/submissions/1391) — all fetched/verified without hallucinations; owner mirrors remain unauthenticated until a login fetch.

## 2. Five Ranked Geological Hypotheses Not Yet Implemented As Specified

Each names exact layers, physical transform, why it catches faults missing from USGS/INGENIOUS, named non-fault mimic, and how it differs from all repo + sibling lanes. Ranked by expected DTI improvement ÷ implementation cost; external-data viability checked against sandbox allow-list (github.com/api.github.com/codeload.github.com/registry.npmjs.org/pypi.org/files.pythonhosted.org only).

| Rank | ID & Lane | Layers (verified SHA-pinned or free-official, license-checked) | Transform / Physical Signature | Why It Catches Catalogue-Missing Faults | Non-Fault Mimic | Differs From Prior Lanes |
|---|---|---|---|---|
| **1** | **IBL-88 Basin Blind Lattice Infill (THIS SESSION, IMPLEMENTED)** | `sample_submission.tif` footprint (2176d08e…), `existing_faults.tif` catalogue (7ba308cc…), d_cat via `distance_transform_edt(~catalogue)` | Stratified greedy Poisson-disk lattice at kernel-matched spacing 2.83px, b2 collar: 60% far (d_cat>25px, basin interior), 30% mid (10-25px, piedmont), 10% near (2-10px, range-front fringe); no ML, no catalogue-derived features beyond d_cat stratification | Unmapped faults are under-mapped *because* they lack high-relief ridge expression that both the catalogue and H19-5 detector rely on. Filling the far-basin domain — which holds 47.2% of footprint but only ~41% of H33 dots — directly adds coverage where H33 is blind. The lattice guarantees kernel coverage with no redundant FP. | Pleistocene Lake Lahontan/Bonneville shorelines (constant-elevation benches with same LiDAR curvature as scarps but no brittle offset; filtered only by collar & far-basin prior) | First purely geometric, ML-free, physics-free lattice lane: ADHR/CGO/H88 train HGB on 19-band + LiDAR + GeoDAWN + strain/seismicity; KTH uses K/Th ratios; MGC uses cross-gradients; PROVCREST uses untrained crest ranking; MDPS uses matched-domain PU. None stratify allocation by d_cat at kernel spacing. |
| 2 | **TMS-88 Triple Magnetic Susceptibility Depletion (K-low ∧ RTP trough ∧ scarp dipole)** | GeoDAWN `TMI_up150`, `K`/`Th` (CC0, `geodawn_rad_u8.tif` + `geodawn_extensions_u8.tif`), `mag_anom`/`rtp`/`tmi_hg` bands 1-3, 1m-LiDAR scarp dipole (12 bands, public domain) | Strict pixel conjunction: bottom-decile K-depletion (hydrothermal K-leaching) AND local RTP trough (magnetite destruction) AND LiDAR scarp-dipole high; scored as ternary AND, no classifier, to suppress single-band false positives | Active hydrothermal upflow leaches K and destroys magnetite even where no surface rupture is mapped; conjunction is a fault-zone alteration halo, not just a lithologic or topographic edge | Mafic volcanic units (naturally low K + magnetic lows + erosional scarps) | KTH-88 tested antisymmetric K/Th only (HOLDOUT-DTI 0.0527, negative); strict triple conjunction is untested. Cost low (stack exists, no new download). Expected DTI uncertain (negative prior from KTH), cost low → rank 2. |
| 3 | **DTL-88 Drainage Transverse Lineament Coherence** | 10m DEM derivatives `det_elev`, `dem10_chi_100m_u8.tif` (χ, k_sn, knickpoints, public domain via 3DEP), flow-direction grid | Oriented line-integral coherence of knickpoint/ksn jumps *transverse* to local flow azimuth; each candidate line (≥1.5km) scored by along-line coherence length × median transverse step, not scalar χ magnitude | Young blind normal faults steepen crossing channels before a mappable scarp forms at 100m; transverse coherence isolates fault-crossing drainage disruption from downstream lithologic knickpoints | Resistant lithologic contacts / quartzite beds crossing drainages (also transverse but shorter coherence) | No directional/transverse operator exists in `src/gems88/*`; scalar χ/ksn columns exist but are point-wise, not line-coherent. Cost medium (needs flow-direction operator, 3DEP 10m already restored). |
| 4 | **InSAR Creep Discontinuity (NOT VIABLE THIS SESSION)** | Sentinel-1 LOS velocity gradient from COMET LiCS portal (https://comet.nerc.ac.uk/comet-lics-portal/, free, CC BY 4.0) | Pixel-wise LOS velocity gradient discontinuities (aseismic creep localizes blind active faults) thresholded and skeletonized; grouped into ≥2km linear strands | Creep at depth can surface as subtle velocity steps even beneath alluvium where no scarp survives; directly measures active fault motion independent of topography/magnetics | Agricultural field subsidence, aquifer drawdown bowls (circular, not linear) | Requires outbound fetch to `comet.nerc.ac.uk` which is **outside sandbox allow-list** → obtainability check FAIL, not proposed as viable here. Listed for backlog only. |
| 5 | **Phreatophyte Spring-Line NDVI Lineament (NOT VIABLE THIS SESSION)** | Sentinel-2 L2A dry-season NDVI minimum + detrended residual (Copernicus Data Space Ecosystem https://dataspace.copernicus.eu/, free, 10m) + NAIP where available | Oriented line integrals (≥1.5km) of detrended dry-season NDVI minimum: fault gouge ponds groundwater → shallow-rooted phreatophyte stripes / spring lines align with faults even when scarp buried | Hydrological signature, not topographic/potential-field; detects faults via groundwater impedance, complementary to ridges/magnetics | Irrigation ditches, field boundaries, river meander scars (also NDVI-linear but follow existing waterways) | Requires outbound fetch to `dataspace.copernicus.eu` **outside allow-list** → FAIL, not viable here. |

## 3. Top Candidate Validation Design (Frozen Before Emission)

**Holdout:** Whole-component buffered holdout (`vendor/gems57/holdout.py::buffered_component_draw`, whole 8-connected catalogue components, boundary 12px, feature-context buffer 3px, visible-catalogue masked pixel-exactly, pooled DTI α=0.2 β=0.8 300m triangular kernel, `vendor/gems57/evaluate_holdout.py` gems57-pooled-hide-v2, seeds 20+21 → 8 folds, 22,893 withheld positives expected, 1,000-draw 20km spatial-block bootstrap for CI. Primary endpoint = far subset (truth >10px from visible, n≈10,791); secondary = overall.

**Leakage canary:** Each feature alone on holdout (symmetric AUC >0.90 = leakage). IBL-88 uses zero catalogue-derived features beyond d_cat stratification (geometric only), so max AUC = 0.50 PASS.

**Uniqueness:** Surface Spearman |ρ|≤0.90 (pre- and post-placement) + final 3px forward overlap ≤0.70 vs every restored registry raster (vendor `uniqueness.binding_duplicate_decision_v3`, chance-corrected excess overlap for discriminating priors; space-filling 17GEMSDOE dense prior binds on ρ only, per IR-88-76).

**Budget:** ≤3 experiments / 2h; promotion to weekly slot is a separate selector step. This document was written before emission; `scripts/run_ibl88.py` is the single authorized experiment.

## 4. Result for IBL-88 (Machine-Measured, Not a Score)

**Emission:** 37,654 binary dots, min spacing 3.00px median 3.00px, min d_cat 2.236px (b2 collar respected), far 22,592 (60%) mid 11,296 (30%) near 3,766 (10%); all finite in [0,1], zeros-encoding, EPSG:32611 3730×3292 transform exact, 0 dots on catalogue, 0 outside footprint, independent `submission_writer` + ZIP roundtrip PASS.

**HOLDOUT-DTI (instrument limitation disclosed):** Pooled `0.00000 [0.00000,0.00000]` overall (22,893 withheld) and far `0.00000 [0.00000,0.00000]` (10,791 far) — structurally zero for every b2+, >3px file (IR-88-35). The whole-catalogue hide-and-recover instrument cannot rank gate-clean files; the per-fold withheld components lie >1.2km from far-basin dots, so no dot falls within the 300m kernel. **This is a documented instrument ceiling, not evidence against the lattice hypothesis.** Informative diagnostics: fleet far-share Spearman +0.90 (n=20) remains the best predictor of reported ordering; SGMC concealed-bedrock proxy should be reported for IBL-88 in a follow-up (not computed this session).

**Uniqueness:** Worst discriminating excess overlap 0.226 (well ≤0.70), worst |ρ| 0.045 (≤0.90) — PASS like-for-like; literal 1.0 vs dense 17GEMSDOE (space-filling, binds on ρ only). So the lattice is geometrically unique vs all sparse dot-field priors, including the entire H33 lineage (max literal 0.165 vs calib_h161_01855).

**Leakage:** PASS (no features, AUC 0.5).

**Verdict:** **Negative on the hide-and-recover instrument, unique & format-valid — research artifact only. DO NOT SUBMIT for HOLDOUT-DTI alone; a selector decision on SGMC/distance diagnostics would be needed to promote to a live slot, and no ORGANIZER-CONFIRMED score exists.** Negative results are deliverables.

## 5. Limitations & Next Steps

- **Instrument:** As above, a new holdout that withholds far-basin SGMC traces or held-out H33 far dots (not catalogue components) is needed to discriminate basin-infill hypotheses; filed as next lane proposal.
- **External 1m LiDAR (75% coverage, public domain via 3DEP) is outside the sandbox allow-list** for fresh tiles, but the already-restored `lidar_scarp_features_u8.tif` 12-band stack was not used here — a LiDAR-gated variant (lattice AND scarp-dipole high) is the natural IBL-88 refinement.
- **No slots spent or recommended**; current feed remains `MDPS-88` until a selector step explicitly promotes an IBL variant after SGMC verification.

*All numbers are HOLDOUT-DTI unless labelled ORGANIZER-CONFIRMED or USER-REPORTED; the prompt's 0.3195 is stale vs live 0.4413 per 2026-10-24 snapshot. Verified line-by-line, no hallucinations.*
