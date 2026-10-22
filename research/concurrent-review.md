# Scientific review — 2026-10-22

## Scope and decision

The initial checkout had only `README.md` (`# GEMSDOE88`). There were no previous-session next steps, cached derived features, shared `evaluate_holdout.py`, shared `submission_writer.py`, segment split definitions, or comparison registry. The prompt references a single-method lane paragraph but supplies none. **No geological experiment was started:** selecting a lane would risk duplicating another parallel session. No competition slot was used.

Core inputs have now been restored autonomously through GitHub mirrors, including the feature raster. Their hashes match the pinned GEMSDOE32 manifest. This verifies mirror integrity, **not organizer provenance or redistribution permission**. Raw data stay ignored by Git. See `evidence/input-restoration.json`, `evidence/input-metadata.json`, and `research/mirror-manifest.json`.

## What GEMSDOE32 actually did

At [pinned source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/scripts/run_h33_validation.py#L111-L119), H33-2-B2 removes every dot within two pixels of the catalogue from a previous dotted emission. The [bundle manifest](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/evidence/h33_submission_bundles.json) describes the all-finite output, while [README](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/780a5a534269c79adfe6d1d7d5aadead161332aa/README.md) documents disagreements between surrogate instruments. These are owner repository records, **not official scoring receipts**.

**Interpretation, not demonstrated causation:** pruning catalogue-adjacent predictions can improve off-catalogue precision if those predictions otherwise contribute little recall. Dotted emission can reduce redundant predicted area around a distance-tolerant target. Both mechanisms depend on the actual evaluator and withheld target geometry. The two-pixel collar is not the same operation as the requested pixel-exact visible-fault mask. It must not be blindly imported into a segment-hidden holdout.

Why was this the highest supplied result? The prompt's result list is insufficient for a causal answer: candidates differ in multiple ways, hidden labels are unavailable, and there is no controlled organizer-scored ablation. Why can we not promise a better result? Local hide-and-recover evaluates known-fault recoverability, not directly the distribution of uncharted faults. Ranking gains can reverse under catalogue selection bias. Repeated tuning also overfits a holdout. Use frozen buffered segment folds, feature canaries and paired spatial-block bootstrap intervals before spending a slot; reserve an untouched outer audit split.

The supplied target scores are **user-reported, unverified**, not labeled ORGANIZER-CONFIRMED. The prompt also contains two different claims for the current leaderboard high. Neither is adopted as a current fact. No numeric HOLDOUT-DTI exists in this run. No projection is represented as a score.

## Candidate hypotheses — proposal only, before implementation

The following order is a **qualitative priority**, not a predicted DTI improvement. Layer availability is established by the restored raster's band descriptions, not by a new external download. Band descriptions themselves are metadata and are not independent verification of physical units. No claim of global novelty across the entire GEMSDOE family is made. Every method is new to this initially empty repo; the comparison to other lanes is preliminary and must be resolved before implementation.

| Priority / cost | Hypothesis and available layers | Transform / physical signature | Why potentially missing from catalogue | Named non-fault mimic / novelty caveat |
|---|---|---|---|---|
| First / medium | Buried structure with signed asymmetric edge profiles: `rtp`, `iso_grav_anom`, `depth_to_base_surf` | Sample signed cross-edge profiles normal to persistent gravity gradients; test a consistent magnetic profile offset with basement slope; reject symmetric isolated bumps | Tests subsurface contrasts with weak surface expression under cover; does not start from catalogue tips | Intrusive lithologic contact or basin depositional margin. Unlike simple ridge intersection, requires signed cross-edge profile ordering; possible overlap with basement/phase lanes needs registry check |
| Second / medium | Cross-scale conductivity-edge confinement: `cond_surf`, `depth_to_base_surf`, `iso_grav_anom_hg` | Contrast a narrow conductivity residual against broad sediment-depth trend and require a co-located gravity break | A concealed permeability boundary may lack a scarp or mapped trace | Saline aquifer/clay facies. Unlike thermal prune-and-augment, builds a label-free residual field; coarse conductivity resolution could invalidate it |
| Third / higher | Repeated topographic profile offset across independent catchments: `det_elev`, `det_elev_slope`, `rtp` | Measure coherent signed elevation-profile changes across separated drainage crossings, not valley alignment alone | Weak distributed offset can be missed between mapped scarps | River terraces, shoreline benches and lithologic contacts. Must distinguish this from H33 drainage-chain and Radon lanes |
| Fourth / medium | Magnetic texture discontinuity without amplitude ridge: `mag_anom`, `rtp`, `tmi_vg` | Local spectral/orientation-distribution change across an edge after removing broad trend | Fault juxtaposition may change texture while both sides have similar mean anomaly | Flight-line seams, volcanic flow margins. Unlike ridge amplitude, tests distributional change; seam-free magnetic lanes may already cover it |

These are geological hypotheses, not validated fault detectors. Fault evidence is not proof of a geothermal vent or commercial reservoir. No additional external dataset is needed to begin these proposals, but spatial resolution, units, and physical interpretation must first be checked. High-resolution replacements are **not asserted obtainable**: official USGS GeoDAWN/3DEP and GDR INGENIOUS sources are listed below for future acquisition in a network environment that permits them.

## Required experiment, when a lane is assigned

1. Identify and pin the shared template, feature-stack version, evaluator, writer, segment IDs and registry snapshot. Do not create private forks here.
2. Hide whole fault segments with spatial buffers. All catalogue-derived features must be recomputed from visible segments per fold. Suppress only visible fault pixels exactly during scoring. Choose buffer size from feature support plus evaluator radius, not from retrospective performance.
3. Check each feature alone with a spatial holdout AUC canary; above 0.90 is leakage until justified. Record negative controls and segmentation provenance. Single-feature AUC is not DTI.
4. Evaluate the pre-placement field against every registry raster on the same valid footprint using tie-aware Spearman correlation. Define registry surface representations before computing this. Correlation above 0.90 stops the run. Missing registry = unknown, never pass.
5. Use the shared writer/placement procedure and then test final rank correlation and directional fraction of candidate dots within three pixels of each registry's dots. Overlap above 70 percent stops the run. A unique file hash alone is insufficient.
6. Use shared pooled DTI with alpha 0.2, beta 0.8, a 300 m triangular kernel, withheld positive count, evaluator version and a spatial-block bootstrap 95 percent CI. Pool counts before calculating the index; do not average fold indices. Record paired improvement over the frozen baseline on the same folds. No current holdout best is provided here, so the promotion comparison is blocked.
7. Require an improved paired interval, format validation, complete nonduplicate registry comparison, and no unresolved canary before recommending promote. Promotion remains separate from selecting a real weekly slot. The weekly cap must come from a current submission-page receipt, not a remembered value.

## Sources and access boundaries

| Source | Authority / what was verified | Access in this session |
|---|---|---|
| [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) | Organizer repository; README and notebook retrieved. CPU training is supported; GPU is not strictly required. Notebook uses Tversky training loss; this does not verify the requested distance-tolerant evaluator. | Retrieved through GitHub API |
| [Competition description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Official rule/target authority; not fetched | Host outside sandbox allowlist |
| [Competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Official provenance authority; mirrors are not a substitute for authentication | Host outside allowlist; no login attempted |
| [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Official live score authority | Not fetched; current standings unverified |
| [Prize PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | User-supplied official-domain rule link | Not fetched; contents unverified |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Official geological data source | Not fetched; obtainability not established |
| [GDR INGENIOUS](https://gdr.openei.org/submissions/1391) | Official DOE repository source | Not fetched; obtainability not established |
| [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32/tree/780a5a534269c79adfe6d1d7d5aadead161332aa) | Owner code/manifest, not organizer verification | Inspected README, tree, H33 implementation and bundle/restore manifests |

The other linked GEMSDOE sites were not exhaustively audited in this run. GEMSDOE87's root listing contained only README. No claim of line-by-line verification of unavailable sources is made. Outbound hosts allowed here are GitHub/API/codeload, npm and PyPI; Dropbox, DrivenData, USGS and NLR are outside that list. No credentials were requested.

## Irregularities and next-session acceptance criteria

- Missing lane paragraph, template location, registry, segment folds and baseline: blocking scientific experiments.
- Restored `labels` and `existing_faults` have the same manifest hash. They are not independent validation truth. Treat them as one catalogue and hide entire segments.
- GEMSDOE32 uses live-score-calibrated surrogates and projections. Do not relabel these HOLDOUT-DTI or ORGANIZER-CONFIRMED.
- All-finite format checks do not establish predictive quality, originality, legality or organizer acceptance.
- No existing build scripts from the prompt were present. The asserted ready train-to-validation pipeline was not present in this checkout.
- The user's complete prompt has not been archived verbatim; README records an explicitly condensed operating brief. Do not misrepresent it as a full transcript.
- Next session must resolve the lane and shared tool pins, authenticate data/rules as feasible, and then run at most three experiments or two hours. The restored numerical feature stack can be reused; do not synthesize training truth.
