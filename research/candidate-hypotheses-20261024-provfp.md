# Candidate Geological Hypotheses — 2026-10-24 (PROVFP lane)

All scores cited from this repository's ledger are labelled by evidence class.
`0.2778` (R0/h33) and `0.4413` (public leader, 2026-10-22 snapshot) are **CLAIM /
UNVERIFIED** — no portal receipt exists in `ledger/submissions.csv` (64 rows, 0 receipts).
No number below is a live score.

## Ranked candidates (expected HOLDOUT-DTI gain vs implementation cost)

| Rank | Hypothesis (layer(s) + physical signature) | Why it should catch a fault *missing* from the USGS/INGENIOUS catalogue | Difference from anything in this repo | Cost |
|---|---|---|---|---|
| **1 (THIS LANE)** | **PROV-CREST de-novo emission.** Organizer-provided `training_features.tif` Band 19 `det_elev_slope` → Hessian ridge of `\|∇slope\|` (piedmont slope-break), Band 3 `tmi_hg` → Hessian crest (magnetic contact), Band 18 `iso_grav_anom_hg` → Hessian crest (gravity contact), Band 15 `depth_to_base_surf` → Hessian ridge of `\|∇depth\|` (basement step). Composite crest (0.45/0.20/0.20/0.15, percentile-ranked) → 1-D directional NMS crest pixels → **de-novo** selection of exactly 37,654 dots at ≥3.5 px spacing, >3.0 px from the *visible* catalogue only. | The four transforms respond to a fault's topographic/magnetic/gravity/basement expression whether or not a mapper traced it. Catalogue-derived features (distance-to-catalogue, ancestor ridge supports H19-5/H19-4/H16-1) cannot express a wholly unmapped strand; these band transforms can, because they are computed from geophysics/topography alone, never from the catalogue. | `p3space35prov` (IR-88-56) used this crest field only for **2,171 refill dots (5.77%)** welded onto R0 survivors — 94.2% of that raster is copied R0. ADHR/MGC used external GDR/LiDAR + catalogue-derived relay features. No prior raster emits 100% of its dots de novo from provided-band crests alone (zero sibling supports, zero external data, zero R0 dots by construction). | Low: reuses `bpv._hessian_ridge`, `bpv._percentile_rank`, `bpd.directional_crest_1d`, vendor metric/holdout/writer. |
| 2 | **PROV-CREST-FP / RANDORDER**: same crest pool, score-blind selection (greedy farthest-point maximin, or its cheap seeded random-order falsifier) instead of crest-score ranking. Tests IR-88-55's "novelty radius, not field ranking" finding at de-novo scale. | Geometric isolation along crest lines may place dots on unmapped strand segments that score ranking (which clusters near known hubs, cf. `w` blind AUC 0.4724) misses. | `p3space35fp` applied farthest-point to only 2,171 refills on a sibling support; never de novo, never on provided-band crests. Exact maximin for 37,654 picks over the full crest pool is O(n·pool) and over budget, so this session preregisters the seeded **random-order** control (Experiment 2, same holdout) and leaves exact FP for a future capped-pool test. | Medium (FP) / Low (randorder control, used here). |
| 3 | `p4space35fp` PRUNE combo (400 m collar × farthest-point refill on R0). | Extends the best blind-SGMC PRUNE ladder (`p4space35 0.102454 PROXY`, `p3space35fp 0.101947 PROXY`). | Proposed in `SLOT_PLAN.md`, not built. **Rejected for this lane**: it copies 89.8% of R0's dots, so its 3-px dot-overlap vs the R0 registry raster is ≈0.90 ≫ 0.70 — it fails the parallel-run uniqueness gate as a "unique submission" and the user's do-not-copy requirement. It remains a valid *controlled experiment*, not a unique de-novo submission. | Low, but lane-ineligible. |
| 4 | Hydrothermal alteration / 2 m temperature-probe advection (GDR #1391). | Hot upflow along unmapped permeable faults leaves thermal/sinter anomalies off-catalogue. | Already implemented as ADHR Exp 03 (`HOLDOUT-DTI 0.18789`, archived `DO-NOT-SUBMIT`); re-running it would not be unique. Named non-fault mimic: laterally displaced valley-floor outflow plumes. | High (external data already cached, but not novel). |
| 5 | LiDAR/10 m DEM scarp + χ–ksn breaklines. | Sub-100 m scarps of young unmapped faults. | Already implemented (ADHR shoreline-clean scarps; GEMSDOE47/64 LiDAR lanes, live CLAIMs ≤0.1461). LiDAR coverage is partial-footprint, so it cannot alone supply 37,654 footprint-wide dots. | High, partial coverage. |

**Non-fault mimic for Rank 1/2 (named, preregistered):** unfaulted coalescing
alluvial-fan bajada toe inflections and incised fluvial terrace risers produce
Band-19 slope-break crests, and Tertiary volcanic flow margins / pluton-roof
contacts produce Band-3/18 gradient crests, without brittle fault permeability.

## Validation gate (before any submission slot)
Top candidate is validated on the template's buffered whole-component
hide-and-recover holdout (`vendor/gems57/holdout.py:buffered_component_draw`,
seeds 20+30; `vendor/gems57/evaluate_holdout.py`, pooled DTI α=0.2, β=0.8,
300 m triangular kernel): whole components withheld with a 3 px feature buffer,
every catalogue-derived quantity (the >3 px collar) derived **only from visible
faults**, visible faults masked pixel-exactly. Final-dot collar against the full
catalogue is applied only for the shipped file, exactly as the holdout arms apply
it against visible faults. A candidate that does not beat the R0 control on this
holdout (paired 95% CI) is labelled `verdict: negative` and is **not** promoted,
per protocol. Leakage canary: every crest channel alone must have symmetric
AUC ≤ 0.90 on withheld positives or the build fails closed.
