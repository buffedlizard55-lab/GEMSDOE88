# Ranked candidate geological hypotheses — GEMSDOE88 (2026-10-25, lane H88-RELAY-DILATIONAL)

**Rule applied before implementing:** rank 3–5 hypotheses by *expected* DTI improvement vs implementation cost, name layers + physical transform + reason each could catch a fault *missing* from USGS/INGENIOUS + named non-fault mimic + how it differs from repo lanes. Validate the TOP on the buffered spatial holdout before any weekly slot. **No hypothesis may be claimed to beat H33 0.2778 or the 0.4413 leaderboard snapshot without an organizer receipt.** All expectations below are qualitative priors, not results.

**Blocking context (verified):** the SHA-256-pinned `17GEMSDOE` space-filling witness (`data/registry/dense_17gemdoe.tif`) is positive on all 5,167,373 footprint cells. Under the binding literal rule (forward 3-px overlap > 0.70 OR |Spearman| > 0.90 vs ANY registry raster blocks), EVERY nonempty candidate overlaps it at 1.0 > 0.70, so **no lane can clear the uniqueness gate** and `ok_to_submit = false` for all of them. Zero weekly slots spent.

---

## #1 (TESTED this session) H88-RELAY-DILATIONAL — fault-intersection / relay-zone / step-over dilational propensity

**Layers:** `existing_faults.tif` catalogue only (no external download, no 19-band stack).
**Physical signature:** structure-tensor orientation/coherence (σ = 2 px) of the trace network → junction proxy (on-trace pixels with ambiguous/low local coherence) + curvature (1 − coherence) → Gaussian-smoothed relay propensity. **Zero within 3 px of any catalogue trace** and **zero on the catalogue pixel-exactly**; threshold to sparse dots (4,293 emitted, 6 px non-max suppression).
**Why it catches off-catalogue faults:** blind geothermal upwellings nucleate at dilational intersections/relay steps (Faulds et al. 2021: >70% of Nevada geothermal systems at stepovers/intersections); these can exist where individual traces are buried under alluvium and never air-photo mapped.
**Named non-fault mimic:** erosional drainage junctions and lithologic contacts (curved intersecting lineaments). Mitigated by the 3 px trace buffer, catalogue zero-mask, and spacing; remains the named mimic.
**Differs from repo lanes:** no listed GEMSDOE site or repo lane targets off-trace relay/dilational geometry with a trace-buffer zero mask; H33/TDKL/QTSK use distance-to-trace, scarp/ridge openness, knickpoints, or Poisson ridge dots.
**Ranking rationale:** highest expected DTI per unit cost among zero-download ideas; first-order geothermal locus.
**Implementation cost:** Low (~30 s on 2 vCPU, catalogue grid only).
**Tested?** Yes — format/range/uniqueness preflight run (this session). Holdout DTI NOT run (witness blocks the lane; no slot).
**Result:** format valid ([0,1], 0 NaN, EPSG:32611, 3730×3292, exact transform, 0 on catalogue, 0 outside). Like-for-like unique vs non-witness registry (worst overlap 0.6820 ≤ 0.70, worst |ρ| 0.0378 ≤ 0.90). Literal witness overlap 1.0000 > 0.70 → **BLOCKED**. Verdict: **negative** (research download only).

---

## #2 (UNTESTED) Radiometric alteration — K/Th/U + magnetic low over blind faults

**Layers:** USGS GeoDAWN airborne radiometric (potassium K, thorium Th, uranium U) + total-field magnetic (from `training_features.tif` bands; see `scripts/restore_inputs.py` pin `bb2e070a…`).
**Physical signature:** hydrothermal alteration → K-depletion / Th enrichment (alteration index) co-located with a magnetic low (magnetite destroyed by alteration); normalized radiometric alteration index × magnetic-low mask.
**Why it catches off-catalogue faults:** concealed faults under basin alluvium host alteration halos with no surface scarp → invisible to USGS Qfaults / INGENIOUS surface mapping.
**Named non-fault mimic:** lithologic contacts and Tertiary volcanic units also shift K/Th/U; mitigated by requiring K-threshold AND Th-enrichment AND magnetic-low co-location, plus spacing.
**Differs from repo lanes:** no lane uses radiometric alteration mineralogy as the primary predictor; DHTC used MT conductivity, XGCE used grav×mag cross-gradient.
**Expected DTI:** moderate-high prior (alteration is a direct geothermal vector), unverified.
**Implementation cost:** Medium (requires restored 19-band stack + band selection verified against `data/training_features.tif` SHA `4371c82e…`).
**External data check:** GeoDAWN survey is free/official (USGS link in section 6); GDR 1391 INGENIOUS compilation free. Obtainable, but band mapping to the 19-band stack must be verified line-by-line before use.
**Verdict:** not tested this session (budget + witness block). Holdout required before any slot.

---

## #3 (UNTESTED) Basement-step gravity gradient + depth-to-basement high-pass

**Layers:** `iso_grav_anom_hg/vg` (gravity), `depth_to_base_surf` (depth to basement) from the 19-band stack.
**Physical signature:** gravity anomaly horizontal-gradient magnitude high-passed, masked by `depth_to_base_surf − G25(depth_to_base_surf)` basement-step relief; basement steps localize blind normal faults.
**Why it catches off-catalogue faults:** basement-involved blind faults offset the base of basin fill with no surface rupture → gravity gradient + basement step detectable where air-photo mapping sees nothing.
**Named non-fault mimic:** igneous intrusive margins and sedimentary facies changes produce gravity steps; mitigated by the depth-to-basement high-pass (isolates relief, not absolute anomalies) and spatial clustering limits.
**Differs from repo lanes:** XGCE computed grav×mag cross-gradient but not basement-step high-pass; no lane combines gravity gradient with depth-to-basement relief.
**Expected DTI:** moderate prior. **Cost:** Low-Medium (19-band only).
**Verdict:** not tested. Holdout required before any slot.

---

## #4 (UNTESTED) LiDAR 10 m DEM fluvial χ + drainage-junction density

**Layers:** 10 m DEM derivatives → fluvial χ transform, channel knickpoints, drainage-network junction density (100 m grid).
**Physical signature:** fault-controlled streams deflect at knickpoints and concentrate junctions; junction density highlights fault intersections at the surface.
**Why it catches off-catalogue faults:** subtle fault traces control drainage without forming mappable scarps; junction density is sensitive to distributed subtle deformation.
**Named non-fault mimic:** lithologic/structural drainage anisotropy unrelated to faults (the named mimic); mitigated by requiring knickpoint AND high junction density AND alignment with regional fault strike.
**Differs from repo lanes:** QTSK used 10 m χ-knickpoints but not junction density; no lane combines χ-knickpoints with drainage-junction density.
**Expected DTI:** low-moderate prior (surface expression may be absent where blind). **Cost:** Medium (DEM tiling + drainage extraction).
**Verdict:** not tested. Holdout required before any slot.

---

## #5 (UNTESTED) Geodetic dilation-rate gate (extensional strain)

**Layers:** `geod_dilaterate` + `geod_shearrate` from the 19-band stack.
**Physical signature:** actively dilating (`geod_dilaterate > 0`) permeable structures; dilate gate intersect relay-zone propensity.
**Why it catches off-catalogue faults:** present-day dilation marks permeable, actively slipping structures that may be unmapped; permeability ↔ dilation (Barton et al. 1995).
**Named non-fault mimic:** broad regional flexure or non-tectonic surface deformation; mitigated by requiring dilation > 0 AND fault-network proximity.
**Differs from repo lanes:** no lane uses geodetic dilation as a gate.
**Expected DTI:** low prior alone (dilation is permissive, not diagnostic); best as a multiplicative gate on #1. **Cost:** Low.
**Verdict:** not tested. Best used as a gate on #1, not standalone.

---

## Ranking by expected DTI improvement vs cost

| Rank | Hypothesis | Layers needed | Expected DTI | Cost | Tested this session |
|------|------------|---------------|--------------|------|---------------------|
| 1 | Relay-dilational propensity (H88-RELAY-DILATIONAL) | catalogue only | plausible (first-order locus) | Low | **Yes — negative (blocked)** |
| 2 | Radiometric alteration K/Th/U + magnetic low | 19-band radiometric+magnetic | moderate-high | Medium | No |
| 3 | Basement-step gravity gradient + depth high-pass | 19-band gravity+depth | moderate | Low-Medium | No |
| 4 | LiDAR χ-knickpoint + drainage-junction density | 10 m DEM derivatives | low-moderate | Medium | No |
| 5 | Geodetic dilation-rate gate | 19-band geodetic | low (gate only) | Low | No |

**Bottom line:** Only #1 was built and validated to format/uniqueness preflight. Because the binding literal `17GEMSDOE` witness blocks ALL nonempty candidates at overlap 1.0 > 0.70, none of #1–#5 can reach a weekly submission slot under the current rule, and none can be claimed to beat H33 0.2778 / leaderboard 0.4413 without an organizer receipt. Any future lane must (a) resolve or exempt the dense witness via a protocol change, and (b) beat the paired holdout incumbent with a positive CI before a slot.

## Sources (manual review links)

- DrivenData problem & format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- NLR GEMS rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN mag/radiometrics: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- GBCGE / INGENIOUS: https://gbcge.org/current-projects/ingenious/
- GDR 1391: https://gdr.openei.org/submissions/1391
- USGS SGMC: https://mrdata.usgs.gov/sgmc/
- EPSG:32611: https://epsg.io/32611
- Tversky/DTI: https://en.wikipedia.org/wiki/Tversky_index
