# Ranked geological hypotheses — 2026-10-25 lane `H88-GZZC`

Read with [PROMPT.md](../PROMPT.md). **Maximize P(Win) · Own the Outcome.** This session’s method paragraph is **H88-GZZC: residual isostatic-gravity zero-contour buried density contact**. No weekly slot is spent.

Official sources (manual review):

- DrivenData 306 problem / format: [https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- About / data policy: [https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- Leaderboard (live; sandbox cannot scrape): [https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- NLR official rules PDF: [https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- Reference solution: [https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- CRS: [https://epsg.io/32611](https://epsg.io/32611)
- Metric (Tversky): [https://en.wikipedia.org/wiki/Tversky_index](https://en.wikipedia.org/wiki/Tversky_index)
- USGS GeoDAWN: [https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- USGS 3DEP: [https://www.usgs.gov/3d-elevation-program](https://www.usgs.gov/3d-elevation-program)
- INGENIOUS: [https://gbcge.org/current-projects/ingenious/](https://gbcge.org/current-projects/ingenious/)
- DOE GDR #1391: [https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)
- Gravity contact mapping: Jachens & Moring 1990 (USGS OFR 90-368); Blakely *Potential Theory in Gravity and Magnetic Applications* (1995).

## Why owner-reported H33 `0.2778` led sibling GEMSDOE sites, and whether we can beat it

**Label every number.** `0.2778` is **USER-REPORTED / [OWNER]** from [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) (`h33-h33-2-b2-…-zeros`). It is **not** `ORGANIZER-CONFIRMED` (no DrivenData receipt in this repository). The 2026-10-24 archived public snapshot `#1 = 0.4413` is also **not** this file’s score. Prompt text `0.3195` is stale relative to that snapshot.

On-disk nested lineage (recomputed, not causal proof): `H19-5 (121,131 dots) ⊃ D2.8 (44,090) ⊃ SOLO-D2.8 (40,199) ⊃ H33 (37,654)`. H33 **removes** 6,436 D2.8 dots, all ≤2 px from the mapped catalogue. That is consistent with DTI’s β=0.8 false-positive penalty plus a 300 m triangular kernel: thinning near-catalogue clumps raises precision more than it costs recall **on whatever hidden truth shares ridge geometry with the catalogue family**. It does **not** prove hidden-truth purity.

**Domain shift.** Local `HOLDOUT-DTI` recovers withheld *catalogue* traces. The portal scores *unmapped* geothermal-indicative faults. A catalogue-collared raster can be structurally near-zero on holdout (IR-88-20/35) and still be a legitimate discovery prior — or the reverse. Beating H33’s user-reported `0.2778` or live `#1` **cannot be shown** without an organizer receipt. This lane spends **0** slots.

## Ranked candidates (before any placement)

| Rank | ID | Layers | Physical signature | Why off-catalogue | Named non-fault mimic | Differs from this repo | Expected DTI / cost |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (selected)** | **H88-GZZC** residual isostatic-gravity **zero-contour buried contact** | `training_features.tif` B13 `iso_grav_anom`, B11/B18 `iso_grav_anom_vg/hg`, B5 slope, B19 `det_elev_slope`, B7/B8 geodetic shear/dilation, B15 `depth_to_base_surf` | 4 km Gaussian residual \(r=g-G_{40}\); contact ridge \(\\|\nabla r\\|\\exp(-r^2/2\\sigma_z^2)\); × \((1-s_{\\mathrm{slope}})^2\); × strain gate | USGS/INGENIOUS mappers trace **surface scarps**. Intra-basin and piedmont faults buried by post-faulting fill keep a density contact (alluvium vs basement) whose residual-gravity zero remains after scarps vanish | Unfaulted alluvial **onlap onto a bedrock pediment** (gravity step, no brittle offset) — penalized by requiring geodetic shear/dilation | Not magnetic tilt-zeros (`tiltzero`); not mag×grav **orthogonal** cross-grad (`XGCE`/`PHASE`); not basement-vs-slope **vector decoupling** (`QTS`); not conductivity curvature (`CTRA`); not K/Th (`KTH`) | Modest far-basin lift possible; **low cost** (pinned 19-band stack). Holdout may be structurally low because of the 3 px catalogue collar |
| 2 | **H88-PSGV** Baranov pseudogravity ↔ Bouguer phase dislocation | B2 `rtp`, B13 `iso_grav_anom` | 2-D FFT Baranov \(k_z/\\|k\\|\) mag→grav; analytic-signal phase mismatch | Magnetization vs density contacts diverge on hydrothermally demagnetized feeders that air-photo maps miss | Remanently magnetized Tertiary volcanics | Reserved next-step; MAG-PSG PR was random stripes (quarantined), not a real Baranov transform | Medium FFT cost; **not run** (budget: one lane) |
| 3 | **H88-BCSF** Okada Coulomb stress-transfer relays | fold-visible `trace_segments` + B7/B8 strain | 3-D elastic half-space ΔCFF at 60° normals | Tip/step-over damage zones lack mapped traces | Lithologic stiffness contrasts | Reserved; needs trace CSV geometry | Medium; **not run** |
| 4 | **H88-EUTh** eU/eTh residual lineaments | GeoDAWN radiometric U, Th | Hydrothermal U enrichment at constant Th | Alteration corridors off mapped scarps | U-rich tuff sheets | KTH used K/Th antisymmetric step, not U/Th | Needs rad bands; **not run** |
| 5 | **H88-S2TIR** pre-dawn TIR seepage | Landsat C2 / ECOSTRESS | Nighttime skin-temperature residual ridges | Diffuse heat along blind faults, no scarp | High-inertia basalt talus | Blocked: sandbox allowlist has no USGS EarthExplorer / LP DAAC | **Not viable here** |

## Lane (the method paragraph this session stays inside)

**H88-GZZC.** Clean sentinel-valued isostatic gravity; subtract a 4 km Neumann-normalized Gaussian regional field; extract the residual **zero contour** as \(\\|\nabla r\\|\\exp(-r^2/2\\sigma_z^2)\); down-weight high `det_elev_slope` (already-mapped scarps); modulate by geodetic shear and positive dilation; collar 3 px off `existing_faults.tif`; greedy spacing 3.2 px; dual-regime budget (near-ribbon 3–25 px and blind >25 px). Reuse `vendor/gems57` holdout, metric, uniqueness, and `src/gems88/portal_writer.py`. No private DTI fork. Catalogue features are **not** used (zero-catalogue surface).

If pre-placement Spearman vs any registry raster > 0.90, or final 3 px forward overlap > 0.70 vs **any** raster including `dense_17gemdoe.tif`, log duplicate and do not auto-submit.
