# MDPS-88 session (2026-10-24): why 0.2778 won, whether it can be beaten, and five ranked hypotheses

Status labels used throughout: **ORGANIZER-CONFIRMED** = copied from a submission-page receipt
(none exist in this repo); **USER-REPORTED CLAIM** = number in the task prompt / sibling sites;
**REGISTRY-MEASUREMENT** = recomputed this session from SHA-256-verified on-disk rasters;
**HOLDOUT-DTI** = local hide-and-recover instrument only; **MODEL-PROJECTION** = never a score.

## 1. Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` scored 0.2778 (USER-REPORTED CLAIM)

Reproduced this session from restored, hash-pinned rasters (`scripts/restore_inputs.py`, all
SHA-256 pins pass; grid EPSG:32611, 3730×3292, transform (100,0,243350,0,−100,4508550),
footprint 5,167,373 px, catalogue 60,988 px):

| Step | File (provenance) | Dots | USER-REPORTED public DTI | Operation |
|---|---|---:|---:|---|
| H19-5 | `data/registry/gems19_h19_5.tif` | 121,131 | 0.1922 | multi-line corroborated ridge support (19GEMSDOE) |
| D2.8 | `data/registry/gems25_d28.tif` | 44,090 | 0.2600 | dotted thinning of H19-5 (subset, 0 added) |
| SOLO-D2.8 | `data/registry/gems28_h27_4.tif` | 40,199 | 0.2708 | removed 3,891 dots ≤1 px from catalogue (subset, 0 added) |
| H33 b2 | `data/registry/h33_education.tif` | 37,654 | 0.2778 | removed 2,545 more dots; **all 6,436 removed dots are ≤2 px from the catalogue** (subset, 0 added) |

Mechanism (DTI = T / (T + 0.2·FP + 0.8·FN), 300 m triangular kernel, `vendor/gems57/metric.py`):

1. **Support quality (H19-5).** The ridge support already sits where unmapped faults live:
   far from the catalogue (H33 median distance-to-catalogue 19.65 px = 1.97 km; 41.7% beyond
   25 px), on sloping range-front terrain (band-19 `det_elev_slope` dot-vs-footprint AUC 0.657;
   ~0% of dots in the bottom slope decile), enriched in magnetic horizontal gradient (AUC 0.574).
2. **Thinning to kernel-matched spacing (D2.8).** H33 nearest-neighbour spacing: min 2.83 px,
   median 3.0 px. With a 3 px kernel each truth pixel saturates at credit 1, so clustered dots
   add FP weight without TP. Removing 77,041 redundant dots raised the reported score 0.1922→0.2600.
3. **Catalogue collar (B=2).** Visible faults are masked pixel-exactly in live scoring (organizer
   thread 11516, as documented in `vendor/gems57/holdout.py`), and the hidden truth is faults
   *not already captured* by USGS/INGENIOUS. Dots within 2 px of a mapped trace therefore earn
   almost no TP while paying full FP. Deleting them is a pure denominator reduction:
   0.2600→0.2708→0.2778 with zero new geography.

Implied live quantities (INFERENCE under the pure-FP-removal assumption, rounded claims):
covered credit T ≈ 5,223; credit/dot ≈ 0.139; implied public truth |G| ≈ 13.2–14.1k px
(M/T 0.33–1.0), i.e. H33 covers only ~37–40% of public truth credit. Marginal-dot bar at
DTI 0.2778 is α·DTI/(1−α·DTI) = 0.0588 — very low, so the score is **coverage-limited, not
precision-limited**: ~60% of truth credit (β-weighted FN) is still on the table.

## 2. Can >0.2778 (and the 0.4413 leaderboard top, USER-REPORTED) be beaten?

Arithmetically yes, with a large required effect. At H33's dot count/geometry, 0.4413 needs
T ≈ 8.3k (+60% covered credit); at 20k well-placed dots it needs T ≈ 6.8k (credit/dot ≈ 0.34,
2.4× H33). Either way it requires (a) dots landing on true traces that H19-5's 100 m ridge
detector missed, and/or (b) tighter on-trace localization (kernel credit →1 per covered pixel).
The identifiable blind spot of the winning lineage is **low-relief basin/alluvium faults**: H33
dots essentially never occur on flat ground, yet buried range-front and intrabasin faults under
alluvium are the classic blind geothermal systems of the Great Basin (INGENIOUS play fairway
context: https://gbcge.org/current-projects/ingenious/). Those faults have no 100 m topographic
ridge, but do have (i) metre-scale scarps in 1 m LiDAR where young, (ii) gravity/magnetic steps
from offset basement, and (iii) drainage/χ disruptions. A submission that adds *that* support —
without re-adding collar FP or redundant clustering — is the credible route past 0.2778.
Whether any local instrument can *prove* it before a slot is spent is the holdout question
addressed below; the local far-subset holdout is informative but not a leaderboard guarantee.

## 3. Five candidate hypotheses not yet implemented as specified (ranked by expected DTI gain ÷ cost)

### H-A (rank 1, THIS SESSION'S LANE) — MDPS-88: matched-domain physics surface, distance-regime emission
- **Layers:** 44 label-blind physics columns already built by `src/gems88/physics.py` from
  `training_features.tif` bands 1–19 (RTP/TMI multi-scale gradients, 60° dip back-projections,
  gravity VG/HG steps, conductivity edges, strain, seismicity) + official-source externals
  (USGS 3DEP 1 m LiDAR scarp stack `lidar_scarp_features_u8.tif` 12 bands, 10 m topo
  `topo_10m_derived_100m_u8.tif`, χ/ksn `dem10_chi_100m_u8.tif`, GeoDAWN radiometrics
  `geodawn_rad_u8.tif` + extensions, GDR #1391 wells/vents/sinter). All restored SHA-verified;
  no new external download required.
- **Signature:** HistGradientBoosting PU ranker trained **only on isolated visible components**
  (no other component within 5 px; `src/gems88/halo.py::isolated_mask`) against far-basin
  background (d_vis > 8 px) — the labelled population that resembles unmapped basin faults —
  with emission split by distance regime: far head allocates at d_vis > 8 px (its training
  domain, fixing the documented FBMT train/allocate mismatch), near head (all-positive model)
  may spend ≤20% of dots at 2 < d_vis ≤ 8 px only above its 99th percentile (physics-snapped
  subparallel splays). Vendor Dinkelbach allocator, kernel-matched min-spacing 2.83 px, b2 collar.
- **Why it catches catalogue-missing faults:** unmapped faults are unmapped largely because they
  lack the high-relief range-front expression that dominates both the catalogue and naive
  all-positive training (covariate shift). Isolated mapped strands in basins are their closest
  labelled analogues; LiDAR scarps + gravity steps express buried faults that 100 m ridges miss.
- **Mimic (named non-fault process):** Pleistocene pluvial shoreline benches and fluvial terrace
  risers (constant-elevation scarps without brittle offset).
- **Differs from repo:** ADHR trains on all positives + catalogue-structure features (74% dots
  ≤10 px); FBMT trained far but allocated at d>3 px (negative); LBCAL fits leaderboard receipts
  (no per-fold physics training); PROVCREST is an untrained crest rule. None uses
  regime-matched allocation with a capped near tranche.
- **Expected:** far-subset HOLDOUT-DTI +0.01…+0.04 vs same-fold base (prior, untested). Cost: low–medium (feature stack + allocator already vendored).

### H-B (rank 2) — Triple-coincidence hydrothermal demagnetization (K-low ∧ magnetic trough ∧ scarp)
- **Layers:** GeoDAWN K, Th/K (`geodawn_rad_u8`, `geodawn_extensions_u8`), band 1/2/14 magnetics,
  LiDAR scarp bands. Signature: pixels simultaneously in K-depletion low, RTP local trough
  (hydrothermal magnetite destruction), and scarp-dipole high, as a *conjunction*, no classifier.
- **Why missing faults:** active upflow along blind faults alters wall rock (K leaching,
  demagnetization) even where no trace is mapped. **Mimic:** mafic lithologic units (low K,
  magnetic lows) with erosional scarps. **Differs:** KTH-88 used radiometric antisymmetry alone
  (HOLDOUT-DTI 0.0527, negative); the strict triple conjunction is untested. Expected: uncertain
  (negative prior from KTH). Cost: low.

### H-C (rank 3) — Directional χ-step lineaments transverse to drainage
- **Layers:** `dem10_chi_100m_*` (channel χ, knickpoints) + `det_elev` flow direction.
  Signature: aligned knickpoint/ksn jumps along lines **transverse** to local flow (fault-crossing
  drainage), scored by along-line coherence, not scalar χ magnitude (already a physics column).
- **Why missing faults:** young blind normal faults steepen crossing channels before a scarp is
  mappable at 100 m. **Mimic:** lithologic contacts / resistant beds crossing drainages.
  **Differs:** no directional/transverse coherence operator exists in `src/gems88`. Cost: medium.

### H-D (rank 4, NOT VIABLE THIS SESSION) — Phreatophyte/spring-line NDVI lineaments
- Sentinel-2 NDVI linear anomalies (groundwater upwelling along unmapped faults in arid basins).
  Free official source: Copernicus Data Space Ecosystem (https://dataspace.copernicus.eu/).
  **Obtainability check: FAIL in this sandbox** — outbound network is limited to
  github.com/codeload.github.com/api.github.com/registry.npmjs.org/pypi.org/files.pythonhosted.org,
  so the data cannot be fetched or hash-verified here. Not proposed as viable.

### H-E (rank 5, NOT VIABLE THIS SESSION) — InSAR creep-discontinuity lineaments
- Sentinel-1 LOS velocity-gradient discontinuities (aseismic creep localizes blind active faults).
  Free official source: COMET LiCS (https://comet.nerc.ac.uk/comet-lics-portal/). Same network
  blocker as H-D → **not viable here**; listed for the backlog only.

## 4. Frozen validation design (see registry/preregistration_mdps88.json)

Hide-and-recover exactly as the template specifies: `holdout.buffered_component_draw`
(whole 8-connected components, boundary 12 px, feature buffer 3 px), seeds 20+21 (8 folds,
22,893 withheld positives expected), catalogue-derived quantities (isolated mask, distance
regimes, masks) from **visible** faults only per fold, visible faults masked pixel-exactly,
pooled DTI via `evaluate_holdout` (`gems57-pooled-hide-v2`, α 0.2, β 0.8, 300 m kernel),
20 km block paired bootstrap. Primary endpoint: **far subset** (truth >10 px from visible),
the pre-registered live analogue in this repo. Leakage canary per feature (symmetric AUC ≤ 0.90)
before any fit is trusted. Stored references on the identical folds: ADHR HOLDOUT-DTI 0.18789
overall / 0.11478 far (UNPAIRED stored values from `docs/research/hypotheses-20261024.md`);
same-fold fold-fair control (base-283) is recomputed this session for the paired test.
Uniqueness: surface |Spearman| ≤ 0.90 and final 3 px overlap ≤ 0.70 (literal + vendor v3
chance-corrected excess both reported) vs every restored registry raster + every tracked
`docs/downloads/*.tif` candidate; space-filling priors (3 px halo = 100% of domain) bind on
rank correlation only, per `binding_duplicate_decision_v3`. Budget: ≤3 experiments / ≤2 h.
No slot is spent by this session; promotion to a weekly slot remains a separate human
selector step even if all gates pass.
