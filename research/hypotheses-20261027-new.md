# New geological hypotheses — 2026-10-27 (session arena/2ebdfb7b-gemsdoe88)

**Context:** This session generated a unique format-valid GeoTIFF
(`docs/downloads/gemsdoe88-relay-dilational-20261027T171403Z-fec0813c826b-zeros.tif`,
SHA-256 `eb86d73d0fa20a7bd17d76a71a51ab527b5ace4594bcbcbdf9ab71898eb33825`,
4,293 binary dots, all finite in [0,1], EPSG:32611, 3730×3292, exact sample
geotransform) under lane **H88-RELAY-DILATIONAL-UNIQUE**. It is **format-valid
and OK to download**, but **NOT OK to submit** under the binding literal
`17GEMSDOE` space-filling witness (overlap 1.0000 > 0.70); no weekly slot was
spent and no organizer score exists. The hypotheses below are **untried** (not
in `registry/hypothesis_queue.json` already_evaluated and not previously
implemented in this repo). They are ranked by expected DTI improvement vs
implementation cost. All use only cached/stack layers or free official sources.

---

## H88-XGM — Cross-gradient of RTP magnetic residual × iso-gravity anomaly

**Rank:** 1 — highest expected DTI lift per unit cost.

**Layers involved:**
- `data/training_features.tif` band 2 = `rtp` (Reduced-to-Pole magnetic residual)
- `data/training_features.tif` band 13 = `iso_grav_anom` (isostatic gravity residual)

**Physical signature targeted:** Cross-gradient magnitude
`|| ∇rtp × ∇grav ||` is large where magnetic and density property contrasts are
orthogonal — i.e. at faulted lithologic/structural contacts where one property
changes across the fault but the other does not, or where they change in
different directions. A simple edge of *either* field alone fires on
unfaulted intrusive contacts and sedimentary density boundaries; the cross
product specifically isolates **fault-related juxtaposition surfaces** that the
catalogue may have missed (especially blind or cover-buried segments with no
surface scarp). This targets *concealed* faults rather than re-mapping traces.

**Why it catches faults missing from USGS/INGENIOUS:** The catalogue maps
subaerial range-front normal faults with scarps. Blind faults beneath pluvial
Lake Lahontan lacustrine clay/alluvium have no surface expression but still
juxtapose contrasting magnetic and density blocks at depth. Cross-gradient
highlights the contact without requiring a scarp.

**Named non-fault mimic:** Unfaulted intrusive contacts where magnetite and
density both contrast (co-located edge → low cross-gradient, correctly
suppressed); folding-related density/magnetic layering (broad, low-gradient).

**How it differs from existing methods:**
- H88-MMRX restores magnetic marker texture (single-field, self-similarity).
- H88-CTRA uses conductivity curvature + thermal conjunction.
- H88-AWA tests radiometric K/Th/U decay-width asymmetry.
- None computes a two-field cross-gradient between magnetic residual and
  gravity anomaly.

**Expected DTI improvement:** Moderate-to-high (structural-contact prior).
**Cost:** Low — cached bands only, ~1 minute on 2 vCPU.
**Falsification:** Reject if cross-gradient maxima align with mapped catalogue
traces >80% (then it is re-mapping known faults) or if leakage canary single
feature AUC > 0.90.

---

## H88-RAD — GeoDAWN radiometric K/(Th+U) hydrothermal-alteration ratio edge

**Rank:** 2 — moderate expected lift, low cost.

**Layers involved:**
- `data/external/geodawn_rad_u8.tif` bands 1, 2, 3 = K, Th, U (quantized U8 indices, NOT calibrated concentrations)

**Physical signature targeted:** Hydrothermal alteration in the Great Basin
commonly produces potassium enrichment (K-high, argillic/potassic alteration)
or potassium leaching with Th/U enrichment. Compute the ratio proxy
`K / (Th + U + eps)` on the quantized indices, then a Canny/Sobel edge
magnitude at 300 m scale. High-ratio edges mark **alteration halos adjacent to
concealed fault conduits**. Because we use quantized code values (not divided
into physical concentrations), this is a relative spatial pattern test, not a
geochemical claim.

**Why it catches faults missing from USGS/INGENIOUS:** Alteration can be
broader and more diffuse than the mapped fault trace, extending into cover.
A ratio edge can highlight the halo of a blind fault that has no discrete
surface scarp in the catalogue.

**Named non-fault mimic:** Differential weathering of adjacent rock units;
K-rich transported alluvium; radiometric quantization/saturation artifacts.

**How it differs from existing methods:**
- H88-AWA tests *relative fitted decay width* of K/Th/U residuals across two
  flanks, not a raw ratio edge.
- No existing lane computes K/(Th+U) ratio-edge propensity.

**Expected DTI improvement:** Low-to-moderate (alteration-halo prior).
**Cost:** Low — external band only, quantized, ~1 minute.
**Falsification:** Reject if a terrain/parent-material-matched null reproduces
the ratio edge, or if the signal is quantization-band dependent.

---

## H88-SEIS — USGS ANSS seismicity cluster rate + b-value anomaly proxy

**Rank:** 3 — potentially high lift but requires external data.

**Layers involved (free official source):**
- USGS ANSS ComCat earthquake catalog (https://earthquake.usgs.gov/fdsnws/event/1/) — free, public, official
- Derived raster: seismicity cluster density (events/km² over sliding window) and b-value proxy (M≥3 vs M≥2 ratio) on the 100 m grid

**Physical signature targeted:** Active fault zones concentrate seismicity,
especially at fault intersections, dilational jogs, and releasing step-overs.
A spatial cluster-rate anomaly (more small events than background) marks
**currently creeping or locked fault segments** that may not appear on the
Quaternary fault catalogue (which only maps faults with surface evidence in
the last ~1.6 Ma).

**Why it catches faults missing from USGS/INGENIOUS:** Qfaults requires
surface expression of Quaternary movement. Blind or recently activated faults
beneath basin fill may be seismically active but unmapped. Seismicity clusters
directly image the active structure.

**Named non-fault mimic:** Volcanic swarms, induced seismicity, aftershock
clusters unrelated to the target fault system.

**How it differs from existing methods:** No existing lane uses seismicity.
All current lanes use geophysical/remote-sensing static layers.

**Obtainability check:** USGS ComCat is free and public via FDSN web service;
no license restriction for challenge use (must be shareable with organizers
per NLR rules). Confirmed obtainable before proposing as viable.
**Expected DTI improvement:** Uncertain (depends on catalog completeness).
**Cost:** Medium — requires downloading catalog, rasterizing, spatial join.

---

## H88-LAHONTAN — Post-Lake-Lahontan fault-activity decoupling from shoreline benches

**Rank:** 4 — low-to-moderate lift, low cost.

**Layers involved:**
- `data/external/dem10_chi_100m_u8.tif` bands 1, 4 = `chan_n`, `valid_n` (drainage network)
- `data/external/topo_10m_derived_100m_u8.tif` (topographic position, curvature)
- `data/training_features.tif` band 12 = `det_elev` (detrended elevation)

**Physical signature targeted:** Lake Lahontan pluvial shoreline benches
(~1,300–1,400 m elevation) are regionally extensive, laterally continuous,
and *undeformed*. A fault that cuts or offsets a shoreline bench is
post-Lahontan (active within the last ~15–20 ka) and thus likely a
concealed/under-mapped geothermal structure. Compute `detrended_elevation
residual` within ±200 m of mapped shoreline bench elevation, then detect
bench-offset lineaments via local elevation discontinuity + drainage
deflection. Suppress pixels on catalogue traces.

**Why it catches faults missing from USGS/INGENIOUS:** The catalogue maps
range-front scarps but may miss intra-basin faults that only cut lacustrine
deposits. Shoreline-bench offsets reveal young blind faults.

**Named non-fault mimic:** Fluvial terrace risers, alluvial fan boundaries,
differential compaction of lacustrine clay.

**How it differs from existing methods:**
- H88-SPR (rank 1 in queue) fits landform-plus-step profiles on swaths but does
  not specifically target Lahontan shoreline-bench decoupling.
- SHORE/TDKL use shoreline context and knickpoints but not bench-elevation
  decoupling.

**Expected DTI improvement:** Low-to-moderate (young-fault prior).
**Cost:** Low — cached bands only.
**Falsification:** Reject if bench offsets are equally explained by alluvial
fan construction or if no elevation discontinuity exceeds noise.

---

## H88-COND — Near-surface conductive heat-flow proxy × structural position

**Rank:** 5 — low expected lift, low cost.

**Layers involved:**
- `data/training_features.tif` band 17 = `cond_surf` (near-surface conductivity)
- `data/training_features.tif` band 15 = `depth_to_base_surf`
- Structure-tensor orientation/coherence of `existing_faults.tif` trace network (catalogue grid only)

**Physical signature targeted:** Faults that act as fluid conduits produce
local conductive anomalies near the surface (hydrothermal upflow raises
near-surface thermal conductivity signature). Combine `cond_surf` high values
with off-trace structural position (distance from catalogue > 3 px, on relay /
bend geometry from structure tensor). This targets **blind conduit faults**
rather than surface traces.

**Why it catches faults missing from USGS/INGENIOUS:** Blind faults with no
surface scarp can still channel geothermal fluids, producing a near-surface
conductive anomaly. Conductivity + off-trace structure reveals them.

**Named non-fault mimic:** Clay-rich lacustrine deposits (high conductivity,
no fault); saline groundwater plumes; conductive alluvial fans.

**How it differs from existing methods:**
- H88-CBC tests cross-basin conductivity connectivity against a drainage null
  (coarse-field topology).
- CTRA uses conductivity curvature + thermal conjunction.
- None combines near-surface conductivity with off-trace structural position.

**Expected DTI improvement:** Low (conductivity is a weak, indirect proxy).
**Cost:** Low — cached bands only.
**Falsification:** Reject if cond_surf highs correlate with clay/lacustrine
mask > 70% (then it is mapping lithology, not faults).

---

## Ranking summary

| Rank | ID | Expected DTI lift | Cost | External data needed | Free official source |
|------|----|-------------------|------|---------------------|---------------------|
| 1 | H88-XGM | Moderate-to-high | Low | No | — |
| 2 | H88-RAD | Low-to-moderate | Low | No | — |
| 3 | H88-SEIS | Uncertain | Medium | Yes | USGS ANSS ComCat (FDSN) |
| 4 | H88-LAHONTAN | Low-to-moderate | Low | No | — |
| 5 | H88-COND | Low | Low | No | — |

**Recommendation:** Validate H88-XGM first on the spatially-buffered
hide-and-recover holdout (pooled DTI, α=0.2, β=0.8, 300 m triangular kernel)
before any weekly slot. It must beat the current holdout best with paired
evidence; otherwise the verdict is negative. No slot is spent in this session.