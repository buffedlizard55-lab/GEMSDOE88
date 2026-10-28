# Three-pass repository review — 2026-10-27, session `8630fb23`

## Executive decision

**No new TIFF was generated. Do not submit any GEMSDOE88 file from this session.** The urgent unique-submission goal is not met, but the parallel-run protocol forbids proceeding: the pinned dense `17GEMSDOE` registry raster covers every allowed submission pixel, so every nonempty allowed dot set has literal 3-pixel forward overlap `1.0000`, above the binding `0.70` stop threshold. The shared preflight was run before any feature/model work and returned `DUPLICATE_STOP` (expected exit code `2`). No holdout, leakage canary, placement, writer, or weekly slot was used.

**No high-score estimate is defensible.** The numbers supplied for historical sibling submissions are `USER-REPORTED CLAIMS`, not `HOLDOUT-DTI` measurements or `ORGANIZER-CONFIRMED` receipts. A local holdout score would describe a hide-and-recover method experiment, not the hidden-label score of a fixed sibling TIFF. This report therefore does not invent leaderboard projections or designate a file to submit.

## Focus-site executive table

The table reports the best value *listed in the supplied prompt* for each focus site and the corresponding artifact in the prior pinned audit. Each value is explicitly a **USER-REPORTED CLAIM; no organizer receipt is present**. “Not unique” below means the historical file violates the user’s literal `>70%` three-pixel registry-overlap criterion; it does not imply all pairs are byte-identical. No row is an upload recommendation.

| Site | Highest listed historical file | Reported value and status | Measured relation in pinned audit | Current decision |
|---|---|---|---|---|
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | [`h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan`](https://github.com/buffedlizard55-lab/GEMSDOE24/blob/17496743a9695974370512db64d8140ea1ccfd2f/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | `0.2477` — USER-REPORTED CLAIM | 3-px overlap: H19-5 `1.0000`; dense 17GEMSDOE `1.0000` | **Not unique; DO NOT SUBMIT** |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | [`dotted-h19-5-d2-8-20261002-e56ea318af89-nan`](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/88a29e094989b0e23916136e593474875d067656/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | `0.2600` — USER-REPORTED CLAIM | H19-5 `1.0000`; dense 17GEMSDOE `1.0000`; exact duplicate of GEMSDOE30 D2.8 raster | **Not unique; DO NOT SUBMIT** |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | [`topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan`](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/426426b402f90f4e0786990b4edd261d9dd48085/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | `0.2449` — USER-REPORTED CLAIM | H19-5 `0.980645`; dense 17GEMSDOE `1.0000` | **Not unique; DO NOT SUBMIT** |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | [`h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan`](https://github.com/buffedlizard55-lab/GEMSDOE28/blob/348ff086e29b9c48bb7104daacb647af31a184bf/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | `0.2710` — USER-REPORTED CLAIM | H19-5 `1.0000`; dense 17GEMSDOE `1.0000`; 3-px overlap with H33-2-B2 `0.9988` | **Not unique; DO NOT SUBMIT** |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | [`d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca`](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/73db382d3c990d0aa0b5126997a67213cc56dee4/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | `0.2600` — USER-REPORTED CLAIM | H19-5 `1.0000`; dense 17GEMSDOE `1.0000`; exact duplicate of GEMSDOE25 D2.8 raster | **Not unique; DO NOT SUBMIT** |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | [`h27-4-solo-d28-20261004-8acb75e1-nan`](https://github.com/buffedlizard55-lab/GEMSDOE31/blob/e6e85b357914068b3ba57ace0f899dde13f110a6/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | `0.2708` — USER-REPORTED CLAIM | H19-5 `1.0000`; dense 17GEMSDOE `1.0000`; exact duplicate of GEMSDOE28 SOLO-D2.8 | **Not unique; DO NOT SUBMIT** |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | [`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/9e55d5d61cb748533691ed183b1b2f2e04643add/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | `0.2778` — USER-REPORTED CLAIM; highest of the nine listed claims | H19-5 `1.0000`; dense 17GEMSDOE `1.0000`; exact subset of SOLO-D2.8 | **Not unique; DO NOT SUBMIT** |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | [`h33d-analog-tip-stepover-r30-20261004-cb490425926e`](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/fded538406627b8d154a2fef5b5331f656d7e0f2/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | `0.2632` — USER-REPORTED CLAIM | H19-5 `0.99711`; dense 17GEMSDOE `1.0000` | **Not unique; DO NOT SUBMIT** |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | [`anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros`](https://github.com/buffedlizard55-lab/GEMSDOE36/blob/4938a123133b4747079cc1c1c93a11e50c1376a7/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | `0.2750` — USER-REPORTED CLAIM | H19-5 `0.977506`; dense 17GEMSDOE `1.0000`; includes all H33-2-B2 dots plus 1,200 additional pixels | **Not unique; DO NOT SUBMIT** |

The source of the names, SHA-256 values, pixel counts, and historical overlap results is the pinned [nine-site audit](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/arena/8630fb23-gemsdoe88/docs/data/focus_sites_20261026.json), which contains **zero organizer receipts**. The archived current table is not a live ranking.

### Freshness warning: the current sibling revisions have moved

A fresh public GitHub API HEAD-only check at `2026-10-27T23:43:57Z` found **all 9/9** focus repositories had changed since the pinned winner audit. The machine snapshot is [focus-freshness.json](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/arena/8630fb23-gemsdoe88/docs/data/session_8630fb23_focus_freshness.json). This confirms staleness only; it does **not** inspect current TIFF bytes, rank current submissions, establish current scores, or establish submission approval. Consequently, this review can name the highest *historical user-reported claims* above, but cannot responsibly claim which file is the current best on any live site. The new commits should be re-audited if and only if the shared pre-placement policy blocker is resolved.

## H33-2-B2: what the evidence does and does not say

The best listed focus-site claim is GEMSDOE32 H33-2-B2 (`0.2778`, **USER-REPORTED CLAIM**, not organizer-confirmed). The pinned audit identifies its geometry as 37,654 binary dots obtained by removing the 6,436 H19-5/D2.8 dots within two pixels of the existing-fault catalogue from the 44,090-dot D2.8 set. It is therefore a collar-pruned member of the D2.8 ridge-thinning family, not an independently established new physical discovery model. The set relation and pixel counts are forensic raster facts; the score and its cause are not.

A plausible explanation is that collar pruning removed redundant or weakly credited predictions close to already mapped traces while retaining a broad ridge-based candidate set. Under a distance-tolerant asymmetric metric, reducing low-value prediction mass can improve the precision/recall balance. But the hidden expert labels are unavailable here: some removed locations could also have received partial credit, and score differences across the historical submissions are not controlled, same-fold experiments. Therefore **we cannot establish why H33 received the claimed score, and we cannot assert that a new candidate would beat it**. It also does not establish a geothermal vent: the prediction target is fault location, and a geophysical/topographic anomaly is not by itself a verified vent.

The user-provided `0.3195` and `0.4413` leaderboard maxima conflict as “current” values and neither was freshly retrieved from the organizer here. They remain unverified user claims in this review; the competition leaderboard and submission page were not accessible from this environment. No leaderboard projection is offered.

## Candidate hypotheses ranked before any implementation

The existing source-bound queue ranks these three proposals. They are **untested proposals**, not measured score gains. The binding pre-placement stop takes precedence; none was fit, scored, or emitted in this session.

| Rank | Hypothesis; cached layers | Target signature and off-catalogue rationale | Difference from implemented work; non-fault mimic | Qualitative potential / cost |
|---|---|---|---|---|
| 1 | **H88-SPR**, detrended elevation and slope (training-feature bands 12, 19), 10 m-derived topography, cached LiDAR scarp/profile, and channel indices | Fit smooth-landform-plus-signed-step versus no-step profiles across independent along-strike swaths. A repeated weak step beneath cover could be absent from the mapped catalogue without being seeded by catalogue distance. | Existing scarp/knickpoint methods use scarp responses or polarity; this would test cross-validated profile restoration against drainage and shoreline controls. Mimics: fluvial terrace risers and pluvial shoreline benches. | Highest relative research priority; moderate, highly uncertain potential; medium cost. No numerical DTI estimate. |
| 2 | **H88-AWA**, quantized GeoDAWN K/Th/U indices, RTP magnetics, basement-depth and detrended-slope bands | Test terrain-matched, cross-strike radiometric residual decay-width asymmetry together with a local RTP depression; the hypothesized alteration pattern need not have a mapped surface trace. | Existing radiometric/magnetic methods emphasize levels or edges, not fitted two-flank decay widths. Mimics: differential weathering, lithologic contrasts, and K-rich transported alluvium. Quantized indices must not be mislabeled as calibrated concentrations. | Lower relative priority; low-to-moderate, uncertain potential; medium cost. No numerical DTI estimate. |
| 3 | **H88-CBC**, detrended elevation, isostatic gravity, basement depth, conductivity, and drainage/channel indices | Test conductivity connectivity across independently inferred basin-boundary saddles with a boundary-normal gravity change, against a smooth basin-fill null; a buried connection could lack a mapped surface trace. | Existing conductivity/thermal conjunctions do not test this topology-preserving basin-breach contrast. Mimics: permeable alluvial paleochannels and saline groundwater plumes. Coarse fields cannot resolve metre-scale conduits. | Lowest relative priority; low, uncertain potential; medium-high cost. No numerical DTI estimate. |

These proposals are sourced to [`registry/hypothesis_queue.json`](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/arena/8630fb23-gemsdoe88/registry/hypothesis_queue.json). That queue is explicit that generation is unauthorized. The full feature stack is not present in this checkout (`data/training_features.tif` is absent); only validation-tier grid and registry inputs were restored. Even if those features were restored, this session’s duplicate stop would still prohibit a feature run under the unchanged rule.

## Why no TIFF or experiment was produced

1. `scripts/restore_inputs.py --validation` restored the hash-pinned sample grid, catalogue, and core registry witnesses; it did not fetch the 19-band training feature TIFF.
2. `scripts/preflight_mtas88.py --gate-generation` recomputed the shared witness certificate on pinned bytes: `5,106,385 / 5,106,385` allowed pixels covered, `0` uncovered, bound overlap `1.0000 > 0.70`; it returned `DUPLICATE_STOP` (exit `2`).
3. Under the supplied literal rule this is universal for every nonempty allowed dot set. No alternative threshold, top-k reinterpretation, subset exception, renamed TIFF, or private evaluator/writer was introduced.
4. The saved H88-TDKL artifact remains a historical research-only download with `-DO-NOT-SUBMIT`; a local `[0,1]` and grid-format pass is not submission clearance. This session did not create a new TIF or modify the existing raster bytes.

**Needed to continue:** an explicit policy decision through the appropriate shared protocol/template process about whether a continuous full-footprint probability raster counts as a “dot” for the overlap rule. This agent did not change that user-supplied rule. If it is formally revised, rerun full surface and final-dot checks against the whole registry, preregister one lane, restore the SHA-pinned feature stack, run visible-only buffered whole-segment holdout and every single-feature leakage canary, then compare paired pooled DTI against the same-fold incumbent. Promotion to a portal slot remains a separate selector action. Also required for an actual organizer claim: authenticated DrivenData data/leaderboard/submission access and a submission-page receipt; no credentials were accessed or requested.

## Sources and scope

- Competition problem/format: [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) and [rules](https://www.drivendata.org/competitions/306/competition-doe-gems/).
- Competition data (login-gated in the prior project audit): [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/).
- Reference implementation: [DrivenData GEMS prize reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- Survey context: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), and [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391).
- Grid CRS reference: [EPSG:32611](https://epsg.io/32611).

These are links for manual review, not a claim that their pages or data terms were fetched during this turn. This session directly queried only the public GitHub API for focus-repository HEADs. See the project’s [source audit](https://github.com/buffedlizard55-lab/GEMSDOE88/blob/arena/8630fb23-gemsdoe88/docs/sources.html) for which sources were previously fetched versus merely listed.

## Three verification passes

1. **Repository and prompt review:** read `README.md`, `PROMPT.md`, `AGENTS.md`, `USER_PROMPT_20261027.md`, the current queue, and latest review/audit records; checked branch and working tree; refreshed the nine-site GitHub HEAD-only feed. All nine revisions differed from the older pinned audit.
2. **Method/protocol review:** restored validation-tier inputs and ran the shared pre-placement gate before any feature work. The universal witness stop reproduced, so no candidate, holdout, canary, or submission slot was used. Also confirmed the full feature stack is absent; `audit_session_start.py` therefore cannot complete its full-input historical rebuild check in this checkout.
3. **Software/regression review:** `pytest`: **1,010 passed, 23 skipped**; normal and optimized `check_site.py`, `render_decision.py --check`, and `audit_research_state.py` passed. The current and candidate release validators pass file-format/audit checks but report `ok_to_submit: false`; their `--require-submit` modes correctly return expected denial exit `2`. These software tests do not establish leaderboard performance or current organizer acceptance.

---

```json
{
  "schema": "gems88.session-run-card.v1",
  "session": "8630fb23",
  "checked_at_utc": "2026-10-27T23:43:57Z",
  "hypothesis": "H88-SPR is the conditional first-choice proposal in the source-bound queue; it was not tested.",
  "mechanism": "Fit smooth-landform-plus-signed-step versus no-step profiles across independent along-strike swaths using cached topographic and LiDAR-derived features; no feature surface was built.",
  "named_non_fault_process": "Fluvial terrace risers and constant-elevation pluvial shoreline benches.",
  "holdout_dti": {
    "evidence_class": "NOT_RUN_PREPLACEMENT_DUPLICATE_STOP",
    "evaluator_version": "gems57-pooled-hide-v2 (not run this session)",
    "withheld_positive_pixels": null,
    "dti": null,
    "ci95": null
  },
  "correlation_overlap_vs_registry": {
    "surface_rank_correlation": null,
    "final_dot_rank_correlation": null,
    "measured_candidate_dot_overlap_3px": null,
    "preplacement_bound_overlap_3px": 1.0,
    "witness": "data/registry/dense_17gemdoe.tif",
    "witness_sha256": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
    "allowed_pixels": 5106385,
    "uncovered_allowed_pixels": 0,
    "overlap_limit": 0.70
  },
  "raster_sha256": null,
  "validator_output": {
    "status": "NOT_RUN_NO_NEW_RASTER",
    "no_nan_inside_footprint": null,
    "values_in_0_1": null,
    "crs_match": null,
    "shape_match": null,
    "transform_match": null
  },
  "submission_name": null,
  "submission_note": "No eligible TIFF generated; no file to submit. DO NOT SUBMIT.",
  "submission_note_length": 59,
  "verdict": "negative",
  "new_experiments": 0,
  "new_tiffs": 0,
  "weekly_slots_used": 0,
  "organizer_confirmed_score": null
}
```
