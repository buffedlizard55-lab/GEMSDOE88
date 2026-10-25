# Session SDTL-88 — 2026-10-25 — H33 forensic answer, ranked hypotheses, executed lane, results

Branch `arena/47d7da6a-gemsdoe88`. Every number below is labelled **HOLDOUT-DTI** (evaluator `gems57-pooled-hide-v2`, withheld positives, 95% CI), **REGISTRY-MEASUREMENT** (local raster comparison) or **USER-REPORTED** (a score pasted into the request; no organizer receipt is held by this repository). Nothing here is ORGANIZER-CONFIRMED.

## 1. Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` scored 0.2778 (USER-REPORTED) — and whether it can be beaten

### 1.1 What the file is (REGISTRY-MEASUREMENT, hash-pinned)

`scripts/audit_h33_lineage.py` and `evidence/h33_lineage_recheck.json` reopen the pinned rasters:

| Raster | Positive cells | Relationship |
|---|---:|---|
| H19-5 (`19GEMSDOE`, power-law-budget multi-line corroborated lineament surface) | 121,131 | upstream support |
| D2.8 (`GEMSDOE25`, dots spaced 2.8 px along H19-5) | 44,090 | thinned support |
| H33-2-B2 (`GEMSDOE32`) | 37,654 | exact subset of D2.8: the 6,436 D2.8 dots that lie **≤ 2 px from the catalogue** are removed; nearest-neighbour spacing 2.83 px |

The owner's build record (`GEMSDOE32/registry/submission_build.json`) describes it as collar pruning of D2.8. The USER-REPORTED lineage is H19-5 0.1922 → D2.8 0.2600 → H33 0.2778.

### 1.2 Why that geometry is close to metric-optimal (metric algebra, `vendor/gems57/metric.py`)

With `T` = truth coverage credit, `n` dots, `M` = summed dot self-credit, `G` = hidden truth cells:

```
DTI = T / (0.8·G + 0.2·(T + n − M))
```

1. **Binary dots at 1.0.** Scaling every dot's value by `s` scales `T`, `n`, `M` by `s`; `DTI(s)` is increasing in `s`, so for any chosen dot set full intensity is optimal. All strong registry files are binary.
2. **2.8 px tiling.** The 300 m triangular kernel means one dot credits every truth cell within 3 px (credit `1 − d/3`). A continuous 1-px-wide line of length `L` costs `0.2·L` in the denominator; dots every 2.8 px cost `0.2·L/2.8` and still leave ≥ 0.53 credit at the mid-points. That is why `dotted` versions of the same surface jumped 0.19 → 0.26 (USER-REPORTED).
3. **Collar pruning.** Organizer thread 11516 (recorded in `knowledge/official-sources-20261024.md`): the known-fault mask is pixel-exact, so a dot 1–2 px from a mapped trace is *not* masked — it is a false positive unless a new fault lies there. Removing the 6,436 collar dots removed ~15% of the FP charge while (per the USER-REPORTED delta +0.0178) losing little coverage. The exact marginal rule is: a non-redundant dot helps iff its realised credit `k > 0.2·DTI ≈ 0.056`; collar dots rarely clear that bar because the new faults in the hidden set are, by construction, *not* the already-mapped traces.
4. **Habitat.** H19-5 is a multi-line-corroborated topographic/geophysical lineament surface. Its dots land where terrain and potential-field edges agree — the structural fabric of range fronts and piedmonts where INGENIOUS experts mapped new strands.

### 1.3 Can it be beaten?

Yes in principle, and the public leaderboard (USER-REPORTED 0.4413 top, 0.3195 earlier) proves a better habitat map exists. The algebra says the only levers are (a) placing dots where `P(new fault within 3 px)` is higher — a better habitat model — and (b) choosing `n` so the last dot still clears `k > 0.2·DTI`. H33 already exploits (b) and the dot geometry; the remaining gain is scientific: a habitat feature that discriminates *unmapped active* faults from generic lineaments. That is the lane executed below. No projection of its portal score is made.

**Known limitation of the project instrument (IR-88-125):** hide-and-recover on the public catalogue rewards near-catalogue continuations that the portal has punished (GEMSDOE81 `cont-poisson buf2` 0.0041 USER-REPORTED) and scores the portal-best H33 at 0.0039 because H33 removes everything within 2 px of the catalogue. The lane below therefore (i) uses no catalogue-distance feature in either arm and (ii) reports the far (>10 px) sub-population separately.

## 2. Candidate hypotheses not previously implemented in this repository (ranked before implementation)

Novelty was checked by grepping `src/`, `vendor/`, `scripts/` and `research/` for the mechanism keywords (zero hits for "slip tendency", "dilation tendency", "sinuosity", "fan apex", "wind gap"). "Expected DTI improvement" is an ordinal judgment, not a score.

| Rank | Hypothesis | Layers | Physical signature / transform | Why it targets faults *missing* from the catalogue | Differs from repo | Expected gain / cost |
|---|---|---|---|---|---|---|
| 1 | **SDTL — stress-field slip/dilation-tendency lineaments** (executed) | `det_elev` (b12), `tc` (b6), `geod_shearrate` (b7), `geod_dilaterate` (b8), visible catalogue | Structure-tensor fabric orientation/coherence at 300 m, 600 m, 1 km; `Td ∝ coh·cos²(θ−θ_f)`, Riedel `coh·cos²(θ−θ_f∓30°)`, with `θ_f` the 30 km circular-mean strike of visible faults and the regime from the geodetic shear fraction | Active (optimally oriented, critically stressed) faults break the youngest alluvium and leave fresh scarps that LiDAR mapping finds; misoriented lineaments are inactive, degraded and already captured (or ignored) by the geologic maps | HGVC's axial coherence compares gravity-vs-RTP orientation agreement; ADHR uses segment strike of nearby traces; neither applies the Morris/Ferrill stress-tendency criterion to terrain fabric | moderate / low (features in <1 min, reuses PHYS-44 + shared fitters) |
| 2 | **Mountain-front sinuosity & fan-apex alignment** | `det_elev`, `det_elev_slope`, 10 m topo derivatives (cached), `depth_to_base_surf` | Extract the bedrock–piedmont junction (slope-break contour), compute sinuosity `Smf` in 5 km windows and the alignment of alluvial-fan apices along it; low `Smf` + aligned apices = active range-front fault | Range-front faults with low sinuosity are active (Bull & McFadden 1977); segments missing from the catalogue are typically the ones under young fans | `piedmont_transition` is a scalar; no sinuosity or apex extraction exists | moderate / medium (junction extraction needs careful thresholding) |
| 3 | **Wind-gap / beheaded-channel detection** | 10 m chi/ksn (cached), `det_elev` | Channels whose chi-profile is truncated at a topographic saddle (flow reversal) indicate transverse uplift along a growing fault; pair saddles with downstream ksn jumps | Growing blind/young faults defeat drainages before producing a mappable scarp | `chi_step_max`, `ksn_jump_norm` exist but no saddle/beheading topology | low–moderate / medium-high |
| 4 | **Basin-tilt asymmetry (transverse topographic symmetry factor)** | `det_elev`, 10 m slope, `depth_to_base_surf` | Per-catchment `T = Da/Dd` (Cox 1994) and asymmetry factor; hinge lines where tilt sense reverses = fault | Hanging-wall tilt from blind normal faults is a basin-scale signal that surface mapping misses | no catchment delineation exists in the repo | low / high (basin delineation on 3730×3292 grid) |
| 5 | **Expert-effort prior (INGENIOUS field focus areas)** | GDR 1391 2 m probe & paleo-geothermal site clusters (cached CSV/ZIP) | Kernel density of field-site locations as a *sampling-effort* covariate | New expert labels can only exist where experts mapped; FP dots far from any mapping effort are pure cost | DHTC/HGVC use probes as thermal signals, not as a survey-effort prior | potentially large on the portal, **unvalidatable with hide-and-recover** (catalogue is everywhere); needs a receipt-based instrument — flagged, not executed |

Rank 1 was executed because it is the only one that is (a) physically specific to *active* faulting, (b) cheap, and (c) testable with the shared hide-and-recover protocol without new external data.

## 3. Executed lane: H88-SDTL

Preregistration: `registry/preregistration_sdtl88.json` (frozen before any fit). Code: `src/gems88/sdtl.py`, `scripts/run_sdtl88_experiment.py`, `scripts/build_sdtl88_submission.py`. Shared, unchanged: split (`holdout.buffered_component_draw`, seeds 20/21, 3 px buffer, whole components), fitters (`adhr._fit_dual_expectation_models`), allocator (`emit.dinkelbach_allocate`, 2.05 px spacing), evaluator (`evaluate_holdout.evaluate` / `pooled_summary`), writer (`submission_writer.write_submission`).

Sanity check of the favourable-strike field: median axial strike N17°E (image angle −72.7° from +x with y down), i.e. perpendicular to a WNW σ3, consistent with the Basin-and-Range extension direction reported for the central/western Great Basin (Zoback 1989; Faulds & Hinz 2015).

### 3.1 Leakage canary (HOLDOUT-DTI instrument, seed 20, 4 fold regions)

See `evidence/sdtl88_canaries.json`. Max single-feature symmetric AUC **0.599** (`sdtl_td_terrain_300`), limit 0.90 → **PASS**. All 12 features in 0.52–0.60.

### 3.2 Holdout results

All numbers **HOLDOUT-DTI**, evaluator `gems57-pooled-hide-v2`, 8 folds (quadrants × seeds 20/21), 22,893 withheld positive pixels pooled, 1,000-draw 20 km block bootstrap; `evidence/sdtl88_holdout.json`. **No arm uses a catalogue-distance feature**, so the comparable repo baseline is the zero-catalogue lane (~0.117), not the 0.19–0.20 catalogue-feature lanes.

| Arm | pooled DTI | 95 % CI | far >10 px subset |
|---|---:|---|---|
| candidate_sdtl (PHYS-44 + 12 SDTL) | 0.096662 | [0.084097, 0.108443] | 0.082130 [0.066652, 0.098188] |
| control_phys44 (PHYS-44 only) | 0.085628 | [0.074471, 0.097234] | 0.069122 [0.055176, 0.081959] |
| ablation_sdtl (SDTL only) | 0.078720 | [0.067435, 0.088819] | 0.063164 [0.051542, 0.075300] |

Paired delta candidate − control: **+0.011034** [+0.002215, +0.020167]; candidate − ablation +0.017942 [+0.007293, +0.028070]; folds won vs control **7/8** (lost seed 20 SW by 0.0026). Preregistered rule (delta > 0, CI low > 0, ≥ 5/8) → **met**. Runtime 1741 s on 2 vCPU.

Per fold (candidate / control / ablation):

| seed | quadrant | withheld | candidate | control | ablation |
|---|---|---:|---:|---:|---:|
| 20 | NW | 1,923 | 0.0770 | 0.0645 | 0.0808 |
| 20 | NE | 2,367 | 0.0859 | 0.0594 | 0.0807 |
| 20 | SW | 3,781 | 0.0840 | 0.0866 | 0.0587 |
| 20 | SE | 3,250 | 0.1159 | 0.1083 | 0.0969 |
| 21 | NW | 1,918 | 0.0763 | 0.0698 | 0.0524 |
| 21 | NE | 2,361 | 0.0839 | 0.0730 | 0.0650 |
| 21 | SW | 3,813 | 0.0904 | 0.0854 | 0.0660 |
| 21 | SE | 3,480 | 0.1455 | 0.1169 | 0.1110 |

Interpretation: the stress-tendency features add information *on top of* the 44-channel physics stack in 7/8 folds and the gain is larger on the far (>10 px) subset (+0.013) than overall (+0.011), i.e. it is not a near-catalogue artefact. The ablation arm (SDTL alone) is below the control, so the features are complementary, not a replacement. The absolute level (~0.10) is a property of the zero-catalogue-feature instrument and says nothing about the portal score; see IR-88-SDTL-02.

## 4. Protocol correction IR-88-SDTL-01 (shared fix, versioned)

See `IRREGULARITIES.md` → IR-88-SDTL-01 and `vendor/gems57/uniqueness.py::binding_duplicate_decision_v5`. Thresholds (0.90 / 0.70 / 3 px) are unchanged; what changed is the definition of a *continuous* registry raster's "dots" (its top-n cells at the candidate's dot count). Prior run cards keep their literal readings; nothing historical was relabelled.

## 5. Sources (for manual review; hosts outside the sandbox allow-list were not fetched this session)

- Competition, rules, metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ · https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- GeoDAWN: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and · INGENIOUS GDR: https://gdr.openei.org/submissions/1391
- Morris, Ferrill & Henderson 1996, *Geology* 24:275 (slip tendency) · Ferrill et al. 1999, *GSA Today* 9(5) (dilation tendency) · Faulds & Hinz 2015, WGC (favourable structural settings) · Siler et al. 2019, *Geosphere* 15, doi:10.1130/GES02032.1 · Bigün & Granlund 1987 (structure tensor) · Bull & McFadden 1977 (mountain-front sinuosity) · Cox 1994 (transverse topographic symmetry)
- Pinned inputs: `research/mirror-manifest.json` (owner mirrors, SHA-256 verified locally; not organizer-authenticated)
