# H88-GEMSDOE88 — Candidate Geological Hypotheses (Untried)

Focus sites: GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36.

## Observed pattern from high scorers on focus sites

| Site | Best submission | Score | Notable form |
|------|----------------|-------|--------------|
| GEMSDOE32 | h33-h33-2-b2-zeros | 0.2778 (user-reported, NOT organizer-confirmed) | Binary dots, 37,654 px |
| GEMSDOE36 | anderson-geothermal-pinn-zeros | 0.2750 (user-reported) | Binary dots |
| GEMSDOE28 | h36-1-rung30-blind-r1 | 0.2710 | Blind-zone dots |
| GEMSDOE28 | h27-4-r1-solo-d2-8 | 0.2708 | Solo d2-8 dots |
| GEMSDOE25 | dotted-h19-5-d2-8 | 0.2600 | Dotted d2-8 |
| GEMSDOE30 | d28-poisson300m-offcat-44090 | 0.2600 | Poisson 300 m off-catalogue |
| GEMSDOE33 | h33d-analog-tip-stepover-r30 | 0.2632 | Tip/stepover dots |
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5 | 0.2477 | Dotted d1-5 |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5 | 0.2449 | Gap closure on d1-5 |

Common thread: **sparse binary dots at defined distances from catalogue faults**, often with "blind zone" (>25 px) or "tip/stepover" qualifiers. No winner uses a continuous probability surface; all are dot fields.

## Hypothesis 1: Multi-scale proximal halo + blind-zone infill (H88-MSHI)

**Layers**: USGS/INGENIOUS catalogue faults (existing_faults.tif); DEM-derived structure from sample_submission grid geometry; no external bands required.

**Physical signature**: Secondary fault strands cluster at 3–25 px (300 m–2.5 km) from mapped traces (damage-zone width scaling, Savage & Brodsky 2011); truly unmapped faults occur in the blind zone (>26 px) where no catalogue context leaks.

**Why off-catalogue**: Catalogue only maps traces with surface expression > certain length/displacement. Blind-zone strands and damage-zone splays are too small or too blind to be mapped but can host geothermal upflow.

**Differs from existing**: H33 uses one distance band; d2-8 submissions use a single annulus. MSHI combines three annuli (3–10 px, 10–25 px, >26 px) with kernel-matched spacing, no lattice regularity, all features from visible catalogue only.

**Named non-fault mimic**: Pluvial shoreline wave-cut benches (Lake Lahontan/Bonneville) create linear topography without radiometric or magnetic anomaly; closed-basin playas produce flat lows; alluvial fan apices create radial patterns.

**Expected DTI gain**: +0.02 to +0.05 over H33 baseline on holdout (blind-zone captures recovery of distant withheld segments).

**Implementation cost**: Low — distance transforms + greedy allocation only.

---

## Hypothesis 2: Structural-gap closure on fault tips (H88-SGCT)

**Layers**: Catalogue faults; binary edge of catalogue masks; distance transform.

**Physical signature**: Fault tips and stepover gaps are dilation sites for secondary fractures; the "gap closure" transform highlights zones where two fault traces nearly connect across a narrow gap (< 10 px), which are preferred loci for new strand nucleation.

**Why off-catalogue**: Small stepovers and tip splays are often unmapped because they fall below the minimum mapping length; their collective signal can be strong.

**Differs from existing**: GEMSDOE27's "topo-gap-closure" uses topography; SGCT uses pure catalogue-gap geometry at multiple gap widths (3–12 px) with kernel-matched dot spacing.

**Named non-fault process**: Erosional gullies and dry-wash confluences create gap-like geometry in DEM without fault displacement.

**Expected DTI gain**: +0.01 to +0.03 on holdout.

**Implementation cost**: Low — binary morphology + distance transforms.

---

## Hypothesis 3: Radiometric-magnetic-topo conjunction (H88-RMTC)

**Layers**: USGS GeoDAWN airborne magnetic/radiometric survey (public, CC0 via GDR #1391); training_features RTP band; DEM curvature bands.

**Physical signature**: Hydrothermal alteration produces K enrichment / Th depletion (radiometric), magnetite destruction creates magnetic demagnetization troughs (negative RTP residual), and fault scarps create topographic lineaments. The conjunction of all three signals at fault-proximal locations indicates blind geothermal faults.

**Why off-catalogue**: Blind faults beneath low-relief cover have no surface expression in the catalogue; geophysical anomalies reveal them.

**Differs from existing**: No prior lane combines multiplicative K/Th × mag × topo as an emission weight. ADHR/MVRD use distance alone; MSHI uses catalogue geometry only.

**Named non-fault process**: Unfaulted lithologic contacts (intrusive/volcanic) create density but weak magnetic contrast; sedimentary facies changes produce radiometric gradients without faulting.

**Expected DTI gain**: +0.03 to +0.07 on holdout (strongest multi-physics signal).

**Implementation cost**: Medium — requires 19-band training_features stack + external radiometrics (419 MB download from owner mirror; redistribution terms unchecked).

---

## Hypothesis 4: Orientation-modulated damage halo (H88-OMDH)

**Layers**: Catalogue faults with segment orientation; structure tensor coherence from DEM.

**Physical signature**: Damage-zone secondary fractures form en echelon arrays at an acute angle to the bulk shear (Riedel system). Dot density should be higher at the predicted Riedel angle (±15°) around each mapped trace, with distance decay fitted from holdout.

**Why off-catalogue**: Riedel shears and synthetic/antithetic strands are rarely mapped individually; their cumulative signal indicates a larger fault system.

**Differs from existing**: The gems57 fabric_dislocation lane already tests orientation × distance interactions (sin2d, cos2d) — measured as inside noise (+0.0018). OMDH would instead gate emission *only* at the fitted Riedel angle band, not as a weak interaction term.

**Named non-fault process**: Joint sets in competent lithology create regular fracture patterns without slip; cooling joints in volcanic units create orthogonal arrays.

**Expected DTI gain**: +0.00 to +0.02 (low, based on prior negative result).

**Implementation cost**: Medium — requires orientation fitting from holdout.

---

## Hypothesis 5: Poisson off-catalogue with catalogue-repulsion (H88-POCR)

**Layers**: Catalogue faults; homogeneous Poisson point process with exclusion zones around catalogue traces.

**Physical signature**: New faults are spatially random (Poisson) but repelled from existing traces (stress shadow). Place dots via Poisson sampling with minimum distance from catalogue, weighted by 300 m kernel credit toward withheld-holdout truth.

**Why off-catalogue**: Pure Poisson off-catalogue sampling (like GEMSDOE30's d28-poisson300m-offcat) scores 0.2600; adding holdout-informed repulsion should improve recovery of withheld segments.

**Differs from existing**: GEMSDOE30 uses fixed Poisson density; POCR adapts density to holdout recovery signal iteratively.

**Named non-fault process**: Random clustering of alluvial fan distributaries; eolian dune alignment.

**Expected DTI gain**: +0.01 to +0.03.

**Implementation cost**: Low — Poisson sampling + distance transforms.

---

## Ranking by expected DTI gain vs cost

| Rank | Hypothesis | Expected gain | Cost | External data needed |
|------|-----------|--------------|------|---------------------|
| 1 | H88-MSHI | +0.02 to +0.05 | Low | None |
| 2 | H88-RMTC | +0.03 to +0.07 | Medium | 19-band stack + GeoDAWN |
| 3 | H88-SGCT | +0.01 to +0.03 | Low | None |
| 4 | H88-POCR | +0.01 to +0.03 | Low | None |
| 5 | H88-OMDH | +0.00 to +0.02 | Medium | Orientation fitting |

**Top candidate for validation**: H88-MSHI (multi-scale proximal halo + blind-zone infill) — lowest cost, directly builds on the observed dotted pattern from all high scorers, uses only visible catalogue features (protocol-compliant), and can be validated on the existing holdout without external data.

## Validate top candidate on holdout before any weekly slot

Per AGENTS.md §2: no slot may be spent until the top candidate beats the current holdout best (H88-BPWD at HOLDOUT-DTI = 0.205991) on the spatially-blocked holdout with paired CI evidence. The current DUPLICATE_STOP (17GEMSDOE dense witness covers all allowed cells) blocks literal registry uniqueness for every nonempty candidate; the representation-aware v4 reading (top-N overlap for continuous surfaces) is diagnostic only and does not clear submission. Any TIF generated here is **research-only, DO NOT SUBMIT**.
