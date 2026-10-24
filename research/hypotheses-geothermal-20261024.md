# GEMSDOE88 — new geological hypotheses (2026-10-24)

**Lane under test:** `GEO-THERMAL-88` — measured geothermal water temperature × young fault-scarp corridor dots.
**Source discipline:** every external layer below is a pinned, free, official source whose SHA-256 is verified before use (see `registry/data_manifest.json`). No DrivenData login-walled file is re-distributed.

## Why H33 (0.2778, owner-reported) is high and whether it can be beaten

H33 is a strict pure-subtraction lineage: H19-5 (121,131 dots) ⊃ D1.5 (60,069) ⊃ D2.8 (44,090) ⊃ SOLO-D2.8 (40,199) ⊃ H33 (37,654). Every step removes dots, and every dot removed after D2.8 lies within 2 px of the mapped catalogue. Under the pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel), a removed pure false positive always *raises* DTI (denominator falls by exactly 0.2 per removed dot, numerator unchanged). Two independent lineage steps imply a public positive pool |G| ≈ 13–15 k px and mean credit per remaining dot ≈ 0.14 vs break-even 0.0556 at DTI 0.2778 — i.e. H33's dots are ~2.6× above break-even. Its dots are spaced ~one kernel radius apart (median NN spacing 3.0 px), which is what the max-vs-sum DTI structure rewards.

Caveat: 0.2778 is **owner-reported, not ORGANIZER-CONFIRMED**; no authenticated DrivenData receipt exists in this repo. Live leaderboard #50 is 0.2818, so 0.2778 would sit below rank 50; the live top is 0.4413. H33 can be beaten only by (a) more dots above break-even credit, or (b) dots hitting truth the holdout/leaderboard actually rewards, with fewer redundant below-break-even dots. The repo's hide-and-recover holdout scores H33 at ~0.004 — it does **not** predict the leaderboard — so holdout is a leakage/exclusion screen here, not a selector.

## Candidate hypotheses (ranked by expected DTI gain vs implementation cost)

### H1 — GEO-THERMAL-88: geothermal well/spring temperature-density × young-scarp corridor dots  (TOP CANDIDATE)

*Layers:* GDR INGENIOUS well & spring temperature/chemistry CSV (`gdr_wellspring_in_footprint.csv`, DOE GDR submission 1391, CC BY 4.0) — pixel row/col + `temp_c` + `dist_known_fault_px`; USGS 3DEP 1 m lidar-derived scarp amplitude (`lidar_scarp_features_u8.tif` band `ex_max`, public domain 17 U.S.C. §105); cached 19-band GEODAWN stack for context (`depth_to_base_surf` thin-cover favorability, `tmi_vg`/`rtp` magnetic).
*Physical signature:* kernel-density of **measured hot geothermal water** (temp-weighted kernels at Hot well/spring pixels), gated to high-amplitude young scarps and thin sedimentary cover, emitted as sparse dots ~one kernel radius (3 px / 300 m) apart.
*Why it catches faults missing from USGS/INGENIOUS:* Blind geothermal systems can surface as hot springs and young scarps without any mapped Quaternary fault trace in the catalogue. Measured water temperature is a direct geothermal indicator, not a fault proxy; every lane already shipped (H33 ridge topography, MRR magnetics, PROVCREST crest ranking, KTH radiometrics, LBCAL receipt calibration) lacks a measured hydrothermal layer.
*Named non-fault mimic:* sinter/travertine spring mounds and relict Pleistocene Lake Lahontan shoreline scarps — look thermal/scarpy but are not active geothermal faults.
*Difference from repo:* first lane whose primary positioning layer is measured geothermal water chemistry/temperature rather than geophysics or topography.
*Expected DTI gain:* moderate (targets a different truth class than catalogue-adjacent dots); *cost:* low — all inputs already pinned and restored.

### H2 — DEM curvature + stream-power knickpoint corridors (not built)

*Layers:* `det_elev_slope`, `curv_prof_absmax` (band 19/12) from cached stack; `dem10_chi_100m_u8.tif` knickpoints.
*Signature:* planar + profile curvature extrema coincident with chi-knickpoints along piedmont range-front drainages.
*Rationale:* fault scarps knickpend drainages; curvature isolates the edge without magnetic/radiometric assumptions.
*Mimic:* volcanic flow fronts, alluvial fan toes, landslide scarps.
*Cost:* medium; expected gain: low-moderate (partially overlaps H33's topography lane).

### H3 — Conductivity-surface × gravity-gradient conduit (not built)

*Layers:* `cond_surf` (band 17), `iso_grav_anom_vg` (band 11), `depth_to_base_surf` (band 15).
*Signature:* high electrical conductivity + vertical gravity gradient over thin cover = fluid-filled fracture zone beneath basin fill.
*Rationale:* geothermal upflows are conductive; gravity gradients mark density contrasts at fault offsets.
*Mimic:* conductive clay-rich lacustrine sediments, saline playa brines.
*Cost:* medium; expected gain: moderate; untested in repo.

### H4 — Earthquake-density swarm clusters off catalogue (not built)

*Layers:* `ieq_n100a15` earthquake density (band 16), `deq_n100a15` distance to earthquake (band 10).
*Signature:* tight earthquake swarm clusters >3 px from mapped faults = active blind faulting.
*Rationale:* seismicity locates active structures the catalogue misses.
*Mimic:* volcanic swarms, aftershock clusters on mapped faults, induced seismicity near wells.
*Cost:* low; expected gain: low-moderate; partially redundant with H1's fault-proximity exclusion.

### H5 — Radiometric K/Th antisymmetric step + RTP trough (ALREADY TRIED: KTH-88)

Already implemented as KTH-88: negative on holdout (0.0527), fails binding uniqueness (89.88% overlap with GEMSDOE87; 100% with 17GEMSDOE dense witness). Not re-tested.

## Selection

**H1 (GEO-THERMAL-88) is validated first.** It is the only candidate using measured geothermal water temperature — the most direct surface indicator of the geothermal resource the competition ultimately rewards — and every input is a pinned free official source. If H1's holdout DTI does not beat the paired incumbent with a positive paired CI, or its uniqueness gate fails, the verdict is `negative` and no weekly slot is spent (per budget: ≤3 experiments, ≤2 hours; promotion is a separate selector decision).

## Sources (official, free, pinned)

- DOE Geothermal Data Repository submission 1391 (INGENIOUS well & spring temperature/chemistry): https://gdr.openei.org/submissions/1391 — CC BY 4.0; pinned SHA-256 in `registry/data_manifest.json`.
- USGS 3DEP 1 m DEM-derived lidar scarp features: https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/ — US public domain (17 U.S.C. §105); pinned SHA-256 in manifest.
- USGS SGMC 1:2,500,000-scale geologic faults (control only, not used to rank candidates): https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d — US public domain; manifest marks it REPORT-ONLY.
- GeoDAWN airborne magnetic/radiometric survey: https://doi.org/10.5066/P93LGLVQ — US public domain; basis of cached 19-band stack.
- Competition metric/submission format: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- NLR Official Rules: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index
