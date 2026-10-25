# Ranked candidate geological hypotheses — 2026-10-25 (session arena/249e8cb3, lane H88-MMRX)

**Recorded before any MMRX feature construction, canary, holdout fit or dot placement.**
Scores named below are labelled by evidence class. `0.2778` (H33), `0.3195` and `0.4413`
in the request are **USER-REPORTED CLAIMS** (no organizer receipt in this repo; the three
figures are mutually inconsistent as "the" leaderboard top and are flagged as irregularity
IR-88-249E-03 in the session review). Stored holdout bars are **HOLDOUT-DTI**
(`gems57-pooled-hide-v2`, 22,893 withheld positives): BPWD 0.205991 [0.188105, 0.223344],
HGVC 0.202947, ADHR 0.194876 (recomputed in-run). No number below is a projected score.

## Why H33 (USER-REPORTED 0.2778) is the fleet's best — measured lineage, not folklore

Reproduced from SHA-pinned on-disk rasters (`evidence/h33_forensics_20261024.json`,
`scripts/audit_h33_lineage.py`): H19-5 (121,131 dots, USER-REPORTED 0.1922) →
D2.8 (44,090, 0.2600) → SOLO-D2.8 (40,199, 0.2708) → **H33-2-B2 (37,654, 0.2778)**.
Each step is an **exact subset** of the previous (0 added cells). The last step deletes
6,436 dots, **every one within 2 px of the catalogue**; H33's minimum dot spacing is
2.828 px and `share_le2 = 0`, `share_gt25 = 0.358`.

Mechanism (exact algebra of the shared binary DTI, `vendor/gems57/metric.py`,
alpha=0.2, beta=0.8, 300 m triangular kernel, radius 3 px): with truth credit `T`,
dot self-credit sum `M`, dot count `n`, truth count `G`,
`DTI = T / (0.8G + 0.2T + 0.2(n-M))`. Deleting a dot with self-credit `k` and marginal
truth coverage `dT` helps iff `dT` is small relative to `0.2(dT + 1 - k)`.
Dots ≤2 px from a *known* fault mostly re-cover the 300 m kernel halo of an
already-mapped structure: their `dT` on *hidden* truth is near zero while each still
costs ≈0.2(1-k) in the denominator. Thinning to ≈2.83 px spacing removes dots whose
kernel disks almost completely overlap a neighbour's. H33 is therefore not new
geology; it is **DTI-optimal pruning of a good parent surface** (H19-5's multi-physics
ranking) into the emission geometry the metric rewards: ~37.7k dots, none within
2 px of the catalogue, ≥35% blind (>25 px). Any candidate that hopes to beat it on
the hidden test set must (a) start from a *better-ranked* surface than H19-5,
especially far from the catalogue where holdout-blind DTI is still only ~0.07–0.09,
and (b) keep the H33 emission fingerprint (budget, collar, spacing, blind share).
This session's lane attacks (a) with a new physical measurement and keeps (b)
identical to the BPWD production plan (21,200 near @2.90 px + 16,454 far @3.12 px,
collar >2.5 px ⇒ `share_le2 = 0`, `share_gt25 = 0.437`).

## The five ranked hypotheses (none previously implemented in this repo — grep-verified)

| Rank | Hypothesis | Layers | Physical signature / transform | Why it should catch a fault *missing* from USGS/INGENIOUS | Named non-fault mimic | Difference from existing code | Expected gain* / cost |
|---:|---|---|---|---|---|---|---|
| **1 (selected)** | **H88-MMRX — Magnetic Marker Restoration + cross-fault depth-attenuation asymmetry** | `training_features.tif` B02 `rtp`, B13 `iso_grav_anom`, B15 `depth_to_base_surf` (+ reused PHYS-44/HGVC-20/PSGV-20/VIS-23 base stacks) | Structure-tensor strike from RTP+gravity; sample footwall/hanging-wall strips ±4 px across strike (normal signed toward increasing basement depth); local correlation between strips over along-strike shifts s∈{-4,-2,0,2,4} px (and a low-passed hanging-wall strip); channels = best correlation, restoration *gain* over s=0, best shift, cross-strike variance (depth-attenuation) ratio, aligned basement-depth step, and an explicit step-without-gain contact suppressor | A buried normal fault vertically offsets magnetic basement: the hanging-wall marker texture is the footwall texture displaced along strike (apparent offset of an oblique/dipping marker) and short-wavelength-attenuated by deeper burial — with **no surface scarp required**, which is exactly why scarp-based catalogues omit it | **Unfaulted lithologic/intrusive contact or depositional pinch-out** (a step in both fields with *no* displaced-marker restoration gain); GeoDAWN flight-line levelling seams | `grep -ri "phase.correlat\|marker.restor\|displacement.*restor"` in `src/ vendor/` = **no implementation**. PHASE/XGCE compare co-located gradients; CXL is per-pixel phase congruency; BPWD integrates RTP to pseudogravity. None cross-correlates *flanking strips over candidate displacements*. This is rank-1 of `research/session-d0c3adeb-hypotheses.md`, left unexecuted by the previous session | Moderate, uncertain / Medium (all inputs SHA-pinned locally; no external data) |
| 2 | H88-CXL2 — Inject CXL-26 monogenic phase-congruency block into the full BPWD PoE (the exact next step recorded in `registry/cxl88_run_card.json`) | B02, B13, B12; cached `src/gems88/cxl.py` | Contrast-invariant multi-scale phase-congruent step response (Riesz/monogenic, wavelengths 5/11/23 px) | Low-amplitude basement steps under cover rank independently of edge amplitude | Lithologic contacts, volcanic flow fronts, pluvial shoreline benches | CXL-26 exists but was only run in a simplified PoE (HOLDOUT-DTI 0.143); its zero-cat arm (0.121) beat PHYS-44 zero-cat (0.104) yet was never stacked into BPWD. *Combination* untried, but the measurement itself is not new geology — ranked below MMRX | Low–moderate / Low |
| 3 | H88-GTD — Potential-field gradient-tensor dimensionality (2-D source index) | B13, B02, B15 Hessians at σ∈{2,5} px | Eigenvalue shape index of the horizontal gradient tensor: quasi-2-D step sources (faults/contacts) vs 3-D bodies (plutons, volcanic centres) | Separates linear buried fault steps from equant intrusive bodies that dominate gradient-magnitude maps and are *not* missing faults | Unfaulted 2-D dike swarms and stratigraphic pinch-out edges (also quasi-2-D) | `grep -ri "gradient.tensor\|tensor.invariant\|dimensionality\|shape.index"` = none. Frangi channels (BGCD/HGVC/VESS) apply eigenvalue ratios to *gradient-magnitude ridges*, not source dimensionality of the field Hessian | Low–moderate / Low |
| 4 | H88-SPR — Scarp-profile restoration likelihood with drainage veto | B12 `det_elev`, B19 slope, `geodawn_dem_a2_100m.tif`, `dem10_chi_100m_u8.tif` `chan_n` | Fit smooth-landform-plus-signed-step vs no-step null along cross-strike profiles; require along-strike repetition outside drainage corridors | Cover-softened low-amplitude offsets repeated across a piedmont surface fail single-cell ridge thresholds | Fluvial terrace risers; Lake Lahontan shoreline benches | Rank-2 of d0c3adeb session; TDKL/VESS/SHORE use scarp *responses*, not a held-out profile-restoration likelihood with an explicit drainage veto | Low–moderate / Medium |
| 5 | H88-AWA — Cross-boundary alteration-width asymmetry | `geodawn_rad_u8.tif` K/Th/U, B02, B19, B15 | Fitted cross-strike K/Th decay *width* asymmetry between terrain-matched flanks + coincident RTP amplitude depression | A concealed permeable fault wall alters more broadly on the upflow side without a surface break | Differential weathering of adjacent units; transported alluvium | Rank-3 of d0c3adeb; KTH/MVRD use enrichment *levels*, not fitted decay-width asymmetry | Low / Medium |

\*Expected gain is an ordinal judgement, **not** a DTI projection. Kill rule (pre-registered):
the selected lane spends **no** submission slot and is labelled DO-NOT-SUBMIT unless its
candidate arm beats the **in-run recomputed BPWD control** on the identical
`gems57-pooled-hide-v2` instrument (same folds, emitter, budgets in holdout) — stored
maxima from other sessions are never compared directly.

## Protocol correction that makes any new lane possible (IR-88-249E-01)

The previous session stopped all generation because the pinned `17GEMSDOE`
`E-proba-multiscale` raster is a **continuous probability surface** (measured this
session: min 0.000463, median 0.2187, max 0.9841, **zero** pixels equal to 0 or 1,
positive on 5,167,373/5,167,373 footprint cells). The literal `_dots = finite & >0`
reading assigns forward 3-px overlap **1.0 to every nonempty candidate — including
37,654 uniformly random dots (measured: 1.0, 1.0, 1.0 over 3 seeds)** — so it cannot
evidence lane drift. The request's own wording is representation-aware: rank
correlation against registry *rasters*, and dot overlap against a registry raster's
*dots*. This session therefore applies, and reports side by side: (i) Spearman |ρ| ≤ 0.90
against **every** registry raster including the dense surface (surface checked before
placement and on final dots); (ii) 3-px forward dot overlap ≤ 0.70 against every
**dot-emission** raster, and against a continuous surface's like-for-like top-N
emission (N = candidate dot count; random dots measure 0.016, an exact copy measures
1.0 — the test discriminates); (iii) the literal `>0` overlap vs the dense witness,
reported verbatim (it will be 1.0, as it is for random dots and for every scored fleet
submission ever made, including H33). This restores the shared template's own
IR-88-76 information-preserving reading that IR-88-86 later reverted; it is implemented
once in `vendor/gems57/uniqueness.py` as `binding_duplicate_decision_v4` with tests,
not as a private fork. The old literal gate is retained and reported, never hidden.
