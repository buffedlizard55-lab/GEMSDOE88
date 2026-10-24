# Five candidate hypotheses — 2026-10-24 — H88-VESS lane (ranked before any scoring)

> Evidence labels: every performance number below is either **HOLDOUT-DTI**
> (`gems57-pooled-hide-v2`, evaluator, withheld count and CI stated where used),
> **ORGANIZER-CONFIRMED** (portal receipt — none exists for any GEMSDOE88 file),
> or a **MODEL** expectation (never a score). Live scores quoted for other sites
> are user-reported claims from the brief, not receipts in this repo.
> Why H33 (`h33-h33-2-b2-…-zeros`, CLAIM 0.2778) led the owner's fleet is
> documented in `research/session-20261024-audit-why-0.2778.md`: kernel
> de-redundancy (nearest-dot spacing 1.0 → 3.0 px) plus moving mass away from
> mapped faults (median distance-to-catalogue 14.6 → 19.7 px). It still sits
> below public rank 50 (`#50 = 0.2818`, `#1 = 0.4413`, official leaderboard
> snapshot `docs/data/leaderboard.json`, 2026-10-24,
> https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
> No local holdout can demonstrate beating 0.2778 (CLAIM) or 0.4413: the hidden
> positives are not the withheld catalogue pixels. Only a portal receipt can
> settle that, and this session spends **0** weekly slots.

## Ranked candidates

| Rank | Hypothesis (layers + physical signature) | Why it should catch a fault *missing* from USGS/INGENIOUS | Named non-fault mimic | Differs from repo lanes | Expected gain (MODEL) | Cost |
|---:|---|---|---|---|---|---|
| 1 (SELECTED) | **H88-VESS — Frangi/Sato vesselness of potential-field gradient magnitude.** Layers: `training_features.tif` B13 `iso_grav_anom`, B2 `rtp`, B15 `depth_to_base_surf`, B12 `det_elev` (tags verified on disk this session). Transform: gradient-magnitude field `|∇f|` per field, then scale-normalised Hessian vesselness at σ=1.5, 3.5 px: eigenvalues λ1,λ2 (|λ1|≤|λ2|), `Rb=|λ1|/|λ2|`, `S=√(λ1²+λ2²)`, `V=exp(-Rb²/2β²)(1-exp(-S²/2c²))`, β=0.5, c=90th pct of S, bright-ridge only (λ2<0); plus cross-field min/geometric-mean at σ=3.5, gravity–basement signed step concordance, and structure-tensor orientation coherence of the joint gradient field (12 channels, zero catalogue access). | A buried basement fault is a *continuous curvilinear edge* in gravity, magnetics and basement depth even where Quaternary cover removes any surface scarp (so no mapper traced it). Vesselness rewards line-likeness (Rb→0) and suppresses equant blobs (Rb→1): lithologic plutons and volcanic centres that fool per-pixel gradient thresholds. Requiring the same line in ≥3 independent fields at two scales targets through-going crustal structure, not a single-field contact. | Unfaulted lithologic contacts / dike swarms (line-like in one field only — suppressed by cross-field min/geomean); Tertiary basalt flow margins (magnetic line, no gravity/basement step — suppressed by polarity + cross-field terms). | `STR-88`/`PROVCREST` used raw Hessian *crests* and spin-2 consensus in a GBDT; `MVRD` used analytic-signal/tilt products; `TDKL` used knickpoint/LiDAR polarity. No lane has used the Frangi ratio `Rb`, the structureness gate `S`, bright-ridge sign gating, or cross-field vesselness min/geomean. Vesselness channels are *added* to the 44 physics + 12 TDKL channels (PoE fusion), not used alone. | +0.002 to +0.008 HOLDOUT-DTI over TDKL PoE (MODEL) | Low: 4 provided bands, no downloads |
| 2 | **Geothermometer-discordance upflow lineaments.** Layers: DOE GDR #1391 well/spring CSV (`data/external/gdr_wellspring_in_footprint.csv`, SHA-pinned, CC BY 4.0 per `registry/data_manifest.json`; source https://gdr.openei.org/submissions/1391): `temp_c`, quartz/chalcedony/cation geothermometers. Transform: spatial discordance `T_quartz − T_chalcedony` residual after elevation/distance-to-spring regression, splatted along-strike with anisotropic (2.5×0.55 px) kernel. | Deep upflow along blind faults mixes to give systematically discordant geothermometers away from mapped traces. | Shallow groundwater mixing in valley wells unrelated to faults; sparse, clustered sampling (springs are not a uniform grid). | Physics stack uses only `well_temp_anom`/`well_geotherm_qtz` proximity splats; discordance *between* geothermometers is unread. | +0.001 to +0.004, high variance (MODEL) | Medium: sparse points, mixing model unvalidated |
| 3 | **Paleo-shoreline (Lake Lahontan) contour-offset detector.** Layers: `topo_10m_derived_100m_u8.tif` B9 `dem_mean`, B12 `det_elev`. Transform: distance-to-1330 m contour field; signed offset/disruption of the contour (contour-parallel gradient of contour distance) as fault-offset proxy. | Post-Lahontan normal faulting vertically offsets the ~15 ka shoreline; a displaced shoreline contour marks a young fault even where the scarp itself is buried by fan deposits. | Wave-cut erosion notches and fan-head trenches displace contours without faulting; valid only near one elevation band (~2–5% of footprint). | Shoreline terms in prior lanes are only *penalties* (`pluvial_shoreline_pen`); nobody has used contour *offset* as a positive signal. | +0.000 to +0.002, tiny area (MODEL) | Low–medium |
| 4 | **Radiometric U-series disequilibrium front curvature.** Layers: USGS GeoDAWN radiometrics `geodawn_rad_u8.tif` + `geodawn_extensions_u8.tif` (DOI 10.5066/P93LGLVQ, US public domain). Transform: second derivative (curvature) of eU/eTh along its gradient direction — a mobility *front* detector rather than a ratio level. | Hydrothermal U mobilisation precipitates at redox fronts pinned by blind fault conduits; the front is a curved boundary, not a high-ratio blob. | Felsic rhyolite domes and placer aprons create ratio highs without fronts; surficial caliche. | `TDKL`/`MVRD` used U/Th *levels* and redox mobility indices; front curvature is unused. Overlaps VESS machinery (Hessian), so deferred to keep this lane single-method. | +0.001 to +0.003 (MODEL) | Low |
| 5 | **InSAR LOS step / strain-vorticity lineaments.** Layers: NASA OPERA Sentinel-1 LOS velocity (https://www.earthdata.nasa.gov) or EarthScope strain (https://www.unavco.org), plus B4/B7/B8 geodetic bands. Transform: LOS velocity-gradient tensor vorticity and across-line step. | Creeping or hydraulically loaded blind faults partition interseismic strain. | Aquifer-compaction subsidence bowls (Basin groundwater pumping) mimic steps. | No lane uses satellite LOS time series. **Not viable this session:** `earthdata.nasa.gov`/`unavco.org` are outside the sandbox outbound allowlist (github.com, pypi.org, registry.npmjs.org, drivendata.org only in practice), so obtainability cannot be verified here; named here only as a future, source-verified option. | Unknown | Blocked (external data unverifiable in sandbox) |

## Selected lane and frozen decision rule (preregistered)

- **Lane:** `H88-VESS` only. 12 zero-catalogue vesselness channels
  (`src/gems88/vess.py`, schema `vess88-12ch-v1`) pooled with the existing
  44 physics + 12 TDKL channels via the shared log-odds Product-of-Experts
  machinery (`tdkl._poe_pool`, `adhr._fuse_log_odds`,
  `emit.dinkelbach_allocate`) — reuse, no private metric fork.
- **Evaluator (shared, unmodified):** `vendor/gems57/evaluate_holdout.py`
  (`gems57-pooled-hide-v2`), whole-component buffered holdout seeds 20+21,
  8 folds, pooled DTI α=0.2, β=0.8, 300 m triangular kernel; visible faults
  masked pixel-exactly; catalogue features from visible faults only.
- **Leakage canary:** every VESS/TDKL/physics feature alone vs withheld
  positives; symmetric AUC > 0.90 ⇒ leakage, stop.
- **Uniqueness (parallel-run protocol):** pre-placement surface Spearman
  |ρ| ≤ 0.90 and final 3 px forward dot overlap ≤ 0.70 against registry
  rasters. The literal all-raster reading (any raster, dense witnesses
  included) is also reported; the 17GEMSDOE dense witness is positive on
  100% of the footprint, so the literal reading is unsatisfiable by any
  non-empty candidate (vacuity witness in `vendor/gems57/uniqueness.py`) —
  it is disclosed, never silently exempted.
- **Fingerprint:** `share_le2 == 0`, `share_gt25 >= 0.35`
  (`src/gems88/gate.py`).
- **Promotion bar:** paired HOLDOUT-DTI Δ vs the recomputed H88-ADHR
  incumbent in the same folds must be > 0 with 95% CI excluding 0, **and**
  the point estimate must exceed the stored TDKL bar 0.196237
  (HOLDOUT-DTI, `gems57-pooled-hide-v2`, n=22,893). Anything else is a
  negative deliverable. Promotion to a weekly slot is a separate human
  selector step regardless (0 slots spent by agents).
- **Budget:** ≤ 3 experiments, ≤ 2 h. Experiments: (1) extra-channels
  physics-only PoE arm, (2) single combined 90-channel arm, (3) PoE
  specialist arm (`h88_vess`) — controls (phys44, ADHR incumbent) are not
  experiments.

## Irregularities found while reusing the TDKL lane (flagged, not replicated)

- **IR-88-107 (new):** `scripts/run_tdkl88_experiment.py:147` reads
  `src.read(14)` (`tmi`) into a variable named `det_elev` and derives
  `scarp_fields` from it; every other lane script reads B12 (`det_elev`).
  TDKL's internal holdout is self-consistent, but its scarp features are
  magnetic, not topographic. This session reads B12 explicitly.
- **IR-88-108 (new):** the same script picks its sense-of-slip CSV with
  `next((ROOT/"data/external").glob("*.csv"))` — filesystem order, not a
  named file. This session uses `trace_segments_utm11.csv` by name.
