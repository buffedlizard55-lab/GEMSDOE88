# Five new geological hypotheses, ranked — written after MDC-88 (2026-10-24)

All five are **new**: none appears in `ledger/submissions.csv` (66 rows), in the seven closed brief
axes (`MASS`, `CONCENTRATION`, `SNAP`, `RELIEF`, `SPACING`, `PRUNE`, `TRACKB`), or in the two
unrun reserve cards (`MRR-88`, `MSDD-88`).  Each states the layers used, the physical signature and
transform, why it should catch an **off-catalogue** fault, how it differs from every lane already in
the repository, and a named non-fault process that produces the same signature.

Ranking is by **expected HOLDOUT-DTI gain per unit implementation cost**, with the gain anchored on
what the MDC-88 instrument actually measured this session: pooled `0.14885`
(95 % CI `[0.13318, 0.17413]`, 22,893 withheld positive pixels, 8 folds) for a 104-feature
zero-catalogue PU density packed at 2.83 px and 1 % of allowed cells, against `0.05535` for the same
allocator driven by uniform density.  **Geology is worth 2.69× geometry on this instrument**, so the
remaining headroom is in the density model, not in the allocator.

| # | Hypothesis | Expected HOLDOUT-DTI gain | Cost | Gain / cost |
|---|---|---|---|---|
| 1 | **H-QTS: Quaternary-cover thickness gradient as a trans-tensional step detector** | **+0.015 … +0.035** | low (1 session, provided bands only) | **highest** |
| 2 | **H-RTR: radiometric K-depletion / Th-residual ratio over covered traces** | +0.010 … +0.025 | low–medium | high |
| 3 | **H-SSA: scale-selective strike-azimuth agreement across magnetics, gravity and topography** | +0.008 … +0.020 | medium | medium |
| 4 | **H-CAL: conductivity–elevation anomaly ladder (upwelling vs outflow discrimination)** | +0.005 … +0.015 | medium | medium |
| 5 | **H-TRI: triple-junction / relay-ramp curvature density** | +0.004 … +0.012 | high (needs a trace-graph build) | lowest |

---

## 1. H-QTS — Quaternary-cover thickness gradient as a trans-tensional step detector

* **Layers.** Provided bands only: `depth_to_base_surf` (b15), `det_elev` (b12), `det_elev_slope`
  (b19), `iso_grav_anom` (b13) and its horizontal gradient (b18).
* **Physical signature and transform.** A concealed normal fault does not show as a scarp once the
  hanging wall is buried; it shows as a **step in the thickness of the unconsolidated fill**, i.e. a
  lineament in `∇(depth_to_base_surf)` that is *not* accompanied by a matching lineament in
  `∇(det_elev)`. The transform is the **decoupled thickness gradient**
  `D = |∇_σ z_base| · (1 − cos∠(∇_σ z_base, ∇_σ z_surface))` at σ = 1, 3 and 6 px, i.e. the part of
  the basin-floor relief whose direction *disagrees* with the modern topographic slope. MDC-88
  carries `g1_z_base`, `g3_z_base` and `zbase_x_ghg` but never the **directional disagreement**,
  which is the whole discriminant.
* **Why it catches an off-catalogue fault.** Faults mapped by field geologists are mapped where they
  break the surface. A buried fault with 10–40 m of post-faulting fill produces a sharp basement
  step and a smooth surface — exactly the cells this transform maximises and every surface-morphology
  lane minimises. This is the population the competition says is missing from the public database.
* **How it differs from existing lanes.** `RELIEF` (closed, negative) ranked *surface* relief;
  `H88-ADHR` used 60° dip back-projection of basement steps but conditioned on hydrothermal
  indicators; `CGO-88` used the raw gradients. None conditions on surface/basement **disagreement**.
* **Named non-fault mimic.** Buried **alluvial-fan toe onlap** against a bedrock pediment produces a
  basement step with no surface expression and no fault. Discriminated by fan-radial azimuth: the
  onlap step is convex-outward and radially symmetric about a canyon mouth, a fault step is linear
  over > 3 km. Carry `aspect_coherence` and a canyon-mouth distance covariate to price it.
* **Cost.** All inputs are already in the cached stack; ~10 new columns, one experiment.

## 2. H-RTR — radiometric K-depletion / Th-residual ratio over covered traces

* **Layers.** USGS GeoDAWN airborne radiometrics (`geodawn_rad_u8.tif`: K, Th, U, TC; CC0) and
  `geodawn_extensions_u8.tif` (ThK, UK, UTh), plus `cond_surf` (b17).
* **Physical signature and transform.** Rising geothermal fluid along a fault leaches potassium from
  the near-surface and leaves thorium (immobile) behind, so a covered conduit shows as a **negative
  K anomaly with a flat Th field**: `R = z(Th) − z(K)` high-pass filtered at 300–900 m and then
  ridge-filtered. MDC-88 carries the raw K, Th, U, TC and the ratio bands, but never the
  **scale-matched residual ridge**, and the raw bands are dominated by regional lithology.
* **Why it catches an off-catalogue fault.** Alteration haloes are 2–10× wider than the fault trace
  itself, so this signal survives burial and vegetation where the geomorphic signal does not.
* **How it differs.** `H88-ADHR` used GeoDAWN K/Th as flat features inside a 67-column fusion; no
  lane has built the differenced, band-pass, ridge-filtered residual.
* **Named non-fault mimic.** **Playa evaporite crusts and young basalt flows** are both K-poor and
  produce the same residual without any fault. Discriminated by `dem_abs` (playas occupy closed
  depressions) and by TMI amplitude (basalt is strongly magnetic). Both covariates are already in the
  stack.
* **Cost.** ~8 new columns; the GeoDAWN rasters are already restored and hash-pinned.

## 3. H-SSA — scale-selective strike-azimuth agreement

* **Layers.** `rtp` (b2), `tmi_hg` (b3), `iso_grav_anom_hg` (b18), `det_elev` (b12).
* **Physical signature and transform.** A fault is a structure that is coherent **through depth**, so
  its strike should agree between a shallow-sensitive field (topography), an intermediate field
  (magnetic horizontal gradient) and a deep field (gravity horizontal gradient). Compute the local
  structure-tensor orientation of each field at matched σ and emit the **circular concentration**
  `κ` of the three azimuths. Mimics are shallow-only or deep-only and score low κ.
* **Why it catches an off-catalogue fault.** It needs no amplitude at all, so it survives the
  amplitude normalisation that kills weak signals in a gradient-boosting model, and it is
  insensitive to the survey-levelling seams that contaminate magnetic amplitude.
* **How it differs.** `MSDD-88` (unrun reserve) proposed strike **dispersion** within one field;
  this is **agreement across fields at matched depth sensitivity**.
* **Named non-fault mimic.** A **tilted fault block's bedding strike** is coherent across all three
  fields without any fault at the measured location. Discriminated by requiring the κ ridge to be
  narrow (< 3 px) rather than a broad band.
* **Cost.** Structure tensors at three scales for four fields ≈ 12 columns plus a circular statistic.

## 4. H-CAL — conductivity–elevation anomaly ladder

* **Layers.** `cond_surf` (b17), `det_elev` (b12), `geodawn_dem_a2_100m.tif`, DOE GDR #1391 2 m
  temperature probes and thermal springs (CC BY 4.0).
* **Physical signature and transform.** Upflow zones sit at *topographic highs relative to the local
  water table* and produce a conductivity anomaly that is **elevation-anomalous**; outflow plumes sit
  low and are elevation-consistent. The transform is the residual of `cond_surf` after regressing on
  local elevation within a 5 km window — isolating conductivity that elevation cannot explain.
* **Why it catches an off-catalogue fault.** It separates the fault-hosted conduit from the basin
  brine that dominates raw conductivity, which is the main reason `cond_surf` alone is weak.
* **How it differs.** `H88-ADHR` advected GDR probes upslope; it never removed the elevation
  confound from the conductivity field itself.
* **Named non-fault mimic.** **Clay-rich lacustrine beds of Lake Lahontan** are conductive and
  elevation-anomalous along the former shoreline. Already priced by the `lahontan_band` feature.
* **Cost.** Local regression over 5.17 M cells at one scale; moderate.

## 5. H-TRI — triple-junction / relay-ramp curvature density

* **Layers.** Competition catalogue geometry + INGENIOUS `trace_segments_utm11.csv`.
* **Physical signature.** Unmapped faults concentrate where mapped segments **step, splay or
  terminate**: relay ramps between en-échelon normal faults host the highest density of unmapped
  connecting structures. Build the trace graph, find segment tips and overlapping pairs, and emit a
  relay-ramp occupancy field.
* **Why it catches an off-catalogue fault.** It targets the exact geometric niche field mappers skip.
* **How it differs.** `vendor/gems57/network.py` has `component_detached` and `local_strike` but no
  relay-pair detector; `H88-ADHR`'s "fold-visible relay width-law" used a width prior, not a graph.
* **Named non-fault mimic.** **Map-sheet boundaries** in the compiled catalogue create artificial
  segment terminations. Must be masked using the SGMC source-sheet polygons.
* **Cost.** Highest — needs a robust trace graph, and it is the only one of the five that is a
  **catalogue-derived feature**, so it re-introduces the leakage risk this lane deliberately removed
  and must be rebuilt per fold from the visible catalogue only.

---

## What this session's result implies for the next one

1. The allocator is **solved**: separation `2√2 px`, budget `1 %` of allowed cells, binary `{0,1}`.
   Re-tuning it is not worth a session — the ladder is unimodal with a flat top and both neighbours
   of the optimum are inside the CI.
2. All remaining headroom is in `ρ(x)`. The uniform-density control scores `0.05535`; a *perfect*
   density would score far above `0.14885`. **Hypothesis 1 (H-QTS) is the recommended next
   experiment** because it needs no new data, no new restore entry, and attacks the one population
   the competition explicitly describes (faults with no surface expression).
3. Do **not** re-open spacing. `IR-88-77` shows the sign is negative on the blocked holdout, and
   `IR-88-44` already closed it on the blind proxy.
4. Any lane that imposes a `d_catalogue >= 3 px` collar scores exactly `0.00000` on the hide-and-
   recover instrument. Report collar decisions on the off-catalogue proxy **and** disclose the
   `sgmc_logdist` circularity (65 % of the naive margin — `evidence/kdmc_experiment3b_sgmc_free.json`).
