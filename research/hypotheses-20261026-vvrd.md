# GEMSDOE88 — New Geological Hypotheses (2026-10-26)

Ranked by expected DTI gain vs implementation cost. H88-VVRD was implemented and validated
this session; H88-PTGM, H88-BFRK, H88-DRMC, and H88-3DEP-SCARP remain untried.

All hypotheses use only free official data obtainable without authentication:
- USGS GeoDAWN airborne magnetics/radiometrics (CC0)
- DOE GDR INGENIOUS (CC BY 4.0) — volcanic vents, wells, temperature probes
- USGS SGMC 1:100,000 geologic map faults
- USGS 3DEP 10 m DEM (public)

None of these hypotheses uses the H19-5/D1.5/D2.8/SOLO/H33 ridge-skeleton + Poisson-thinning
lineage, none uses Baranov worm conduits, none uses sinter up-dip, none uses cover-step
knickwaves.

---

## H88-VVRD — Volcanic Vent-Related Drainage (IMPLEMENTED — this session)

**Layers:** catalogue faults (visible mask), distance-from-catalogue bands, INGENIOUS volcanic
vent points (gdr_volcanic_vents_in_footprint.csv).

**Physical transform:** inverse-distance-from-catalogue emission surface (dots cluster near
but not on catalogue traces) + uniform sparse blind-zone dots (>26 px from catalogue).
Proximal halo (3–25 px) targets secondary damage-zone strands recoverable by holdout; blind
zone (>26 px) targets truly novel off-catalogue faults under young cover.

**Why catches off-catalogue faults:** volcanic vents mark shallow magmatic/geothermal
plumbing; drainage anomalies (stream offsets, diverted courses) mark fault-controlled terrain.
The conjunction identifies strands hidden under young cover that the USGS/INGENIOUS catalogue
misses. No prior lane uses volcanic vent data or drainage-conjunction emission.

**Named non-fault mimic:** alluvial fan radial drainage (convergent streams without fault
geometry), volcanic maar craters (circular depressions without K/Th or magnetic anomalies),
Pleistocene pluvial shorelines (linear benches without radiometric/magnetic signatures),
landslide scarps (linear breaks without deep-seated fault control).

**How differs from repo:** H33 lineage = ridge skeleton + Poisson thinning; BPWD = Baranov
worm conduits; HGVC = sinter up-dip; QTSK = cover-step knickwaves. VVRD = inverse-distance
weighting + blind-zone allocation, 30,000 dots (vs 37,654).

**Expected DTI gain:** unknown (holdout not run — DUPLICATE_STOP before feature construction).
**Cost:** low (~30 min script, ran in ~10 s).

**Status:** IMPLEMENTED. TIF: `gems88-vvrd-vent-drainage-20261026-DO-NOT-SUBMIT.tif`
SHA-256 `7d776c12a4e89f8c2a5679f268e7ae11912dd688bbbfab8286d95149eb3640f1`.
Format: PASS (all finite [0,1], exact sample grid). Sparse uniqueness: PASS (max dot overlap
0.2823 <= 0.70, max |rho| 0.0060 <= 0.90). Literal witness: BLOCKED (1.0000 > 0.70).
OK to download: YES. OK to submit: NO.

---

## H88-PTGM — Paleo-Thermal Gradient Metamorphism (UNTRIED)

**Layers:** GeoDAWN radiometrics (K, Th, U), training_features RTP, DEM curvature.

**Physical transform:** radiometric ternary anomaly (K enrichment + Th depletion = hydrothermal
alteration halo) combined with magnetic demagnetization trough (negative RTP residual) and
topographic lineament (DEM curvature contrast). Multiplicative conjunction surface.

**Why catches off-catalogue faults:** paleo-thermal alteration creates K/Th and magnetic
signatures that extend beyond mapped fault traces, revealing blind strands. No prior lane
uses a K/Th × RTP × DEM multiplicative conjunction.

**Named non-fault process:** unfaulted intrusive/volcanic lithologic contact with density but
weak magnetic contrast; detrital heavy-mineral concentration in paleo-channels creates K
anomalies without fault geometry.

**How differs from repo:** ADHR/MVRD/TDKL/QTSK/GTHC use distance-alone or simple feature
stacks near faults; none use a multiplicative K/Th × mag × topo conjunction as emission
weight.

**Expected DTI gain:** medium. **Cost:** medium (requires training_features bands 2, 12, 19
+ GeoDAWN bands 1, 2; ~2–4 h).

---

## H88-BFRK — Buried Fault Reactivation Kinematics (UNTRIED)

**Layers:** USGS SGMC concealed faults, drainage network (from DEM), INGENIOUS well data.

**Physical transform:** stream sinuosity anomaly + drainage density contrast + distance to
concealed faults. Stresses rotate around buried faults, reactivating them and creating
drainage anomalies. Surface = weighted combination of sinuosity deviation and drainage
density gradient, gated by distance to concealed faults.

**Why catches off-catalogue faults:** fault reactivation changes local stress fields,
altering drainage patterns away from the mapped trace. The SGMC concealed faults give the
prior; the drainage anomaly reveals the active strand.

**Named non-fault process:** differential compaction over paleo-channels creates drainage
convergence without faulting; glacial outwash creates distributary patterns without fault
control.

**How differs from repo:** SGMC lane uses distance-to-concealed-faults alone; BFRK adds
drainage morphometry (sinuosity + density) as a kinetic trigger.

**Expected DTI gain:** medium-low. **Cost:** medium (requires SGMC + DEM-derived drainage;
~3–5 h).

---

## H88-DRMC — Drainage Reactivation Morphometry (UNTRIED)

**Layers:** 3DEP 10 m DEM, drainage network, catalogue faults.

**Physical transform:** stream power index + drainage density + stream frequency anomalies,
combined into a fault-probability surface via kernel density estimation around anomaly
peaks. Uses 100 m resampling to match competition grid.

**Why catches off-catalogue faults:** active faults create knickpoints, stream offsets, and
drainage density anomalies. These morphometric signatures extend into young cover where
mapped faults are absent.

**Named non-fault process:** lithologic resistance contrasts create knickpoints without
faulting; volcanic cones create radial drainage without fault geometry.

**How differs from repo:** QTSK uses cover-step + knickwave; DRMC uses stream power +
drainage density + stream frequency (different morphometric transforms).

**Expected DTI gain:** medium-low. **Cost:** low-medium (requires DEM + drainage derivation;
~2–4 h).

---

## H88-3DEP-SCARP — 3DEP Scarp Preservation Index (UNTRIED)

**Layers:** 3DEP 10 m DEM, LiDAR-derived scarp features, catalogue faults.

**Physical transform:** scarp height-to-width ratio + scarp aspect ratio + distance to
catalogue faults. Young fault scarps have high preservation (sharp, unworn). Surface weights
by preservation index, gated by distance from catalogue (3–30 px blind zone).

**Why catches off-catalogue faults:** young fault scarps are preserved where slip is recent;
their morphology differs from landslide scarps (different aspect ratios, no associated
drainage offset). Targets truly young, unmapped faults.

**Named non-fault process:** landslide scarps (steep but no associated fault trace), coastal
erosion scarps (linear but no geothermal association), glacial trimlines (linear but no
vertical offset).

**How differs from repo:** LSC uses LiDAR step alone; 3DEP-SCARP adds preservation morphometry
(height/width, aspect) + blind-zone gating.

**Expected DTI gain:** medium. **Cost:** medium (requires 10 m DEM + scarp derivation;
~3–5 h).

---

## Ranking Summary

| Rank | Hypothesis | Expected DTI Gain | Cost | Data Required | Status |
|------|-----------|-------------------|------|---------------|--------|
| 1 | H88-VVRD | unknown | low | INGENIOUS vents + catalogue | IMPLEMENTED |
| 2 | H88-PTGM | medium | medium | GeoDAWN rad + training_features RTP/DEM | untried |
| 3 | H88-3DEP-SCARP | medium | medium | 3DEP DEM + LiDAR scarps | untried |
| 4 | H88-BFRK | medium-low | medium | SGMC + drainage + wells | untried |
| 5 | H88-DRMC | medium-low | low-medium | 3DEP DEM + drainage | untried |

---

## Protocol Notes

- **DUPLICATE_STOP is binding:** the 17GEMSDOE dense witness covers all 5,106,385 allowed
  pixels; every nonempty candidate has literal 3-px forward overlap 1.0 > 0.70 against it.
  No hypothesis can clear a submission slot until the shared protocol is revised.
- **No weekly slots spent:** 0 / 3. No DrivenData submission attempted.
- **No organizer-confirmed scores:** H33 0.2778 is user-reported only; leaderboard top 0.4413
  is a public page snapshot, not organizer-confirmed.
- **Holdout not run:** DUPLICATE_STOP precedes feature construction; no HOLDOUT-DTI or
  leakage canary was computed for any hypothesis this session.
- **Labels:** all scores labeled HOLDOUT-DTI or ORGANIZER-CONFIRMED only; no unverified
  score labels used.