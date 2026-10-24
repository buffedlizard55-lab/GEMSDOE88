# GEMSDOE88 repository review — 2026-10-24

## Executive decision

**Current action: HOLD; do not spend a competition slot.** The repository contains several novel, byte-unique research GeoTIFFs and the site clearly labels download vs. submission status. It does **not** currently contain the ignored competition inputs needed to independently reproduce a candidate, run the shared holdout, or certify a new release from this checkout. No fresh candidate raster or score was generated in this review.

The most recent top-level decision is the LBCAL hold (README and `docs/index.html`): its reported `HOLDOUT-DTI` is below the best comparable holdout run and the gate records `ok_to_submit: false`. The root `run_card.json` and the main hero on the website describe the earlier MRR-BPR negative run. These are dated historical artifacts, not contradictory evidence that a slot is cleared. Treat each candidate's run card and gate receipt as authoritative for that candidate; do not use a model projection or an old `ok_to_submit` field as a portfolio authorization.

## Review passes

### Pass 1 — implementation and site inspection

- Read `PROMPT.md`, `README.md`, `SLOT_PLAN.md`, `research/next-steps.md`, the dated MDC-88 handoff, current LBCAL/MRR run cards, gate reports, holdout reports, and the download/submission pages.
- `python scripts/check_site.py`: **PASS** (links, explicit negative decision, and research-download labeling).
- The main site and executive summary have one-click GeoTIFF/ZIP links, short submission name/note fields, an automated download-vs-submit decision, and upload instructions. Existing artifacts remain clearly `DO NOT SUBMIT` where required.
- The request's “single method paragraph below” is not supplied. The repository already records this ambiguity. MRR-BPR-88 is a completed negative lane, not permission to continue retuning it.

### Pass 2 — tests, data, and edge cases

A temporary ignored `.venv` was created for test tooling; no environment files or bulk data are tracked.

- `python -m pytest -q`: **275 passed, 30 skipped, 6 failed**. The six failures all require absent local competition inputs (`data/bridge/sample_submission.tif`, `data/bridge/existing_faults.tif`, or `.cache/data/*`). They fail at missing-file opens, before a new scientific experiment can run; they are not evidence that those six behaviors pass.
- `python scripts/audit_session_start.py`: **BLOCKED** at the same absent pinned `sample_submission.tif`.
- `python scripts/validate_current.py`: **BLOCKED** because `data/bridge/sample_submission.tif` is absent.
- `data/` is absent in this checkout. The competition/download data are intentionally gitignored. `registry/data_manifest.json` also flags public sibling-repository mirrors as `FLAGGED_DATA_USE_UNCHECKED`; do not treat their availability as a license or silently restore competition material from them.
- This means the supplied previous-session expectation that “everything needed is already restored and cached” is false for this checkout. It needs an authorized, hash-verified input restoration before the next holdout experiment.

### Pass 3 — requirement and integrity review

- No score here is newly computed. Existing performance numbers remain labeled `HOLDOUT-DTI`, `MODEL-PROJECTION`, `USER-REPORTED`, or `ORGANIZER-CONFIRMED` according to their evidence files. The reviewed repo contains no organizer-confirmed receipt.
- Fresh saved-byte spot check of the latest LBCAL research artifact: SHA-256 `0a44af1ed8090cf1be88e42b832e0cc4b3bd2263a01b13b45f873e0eb528991a`; one-band float32, EPSG:32611, shape 3730×3292, transform `(243350,100,0,4508550,0,-100)`, nodata unset, all finite, values exactly `{0,1}`, and 38,278 positive pixels. The one-member ZIP contains byte-identical TIFF data and independently reopens to an identical array. This validates the saved bytes and recorded grid metadata, **not** parity against a newly authenticated organizer template (the sample file is absent); the LBCAL gate also records a layout-parity difference. It remains a research-only file and is **not** authorized to submit.
- Existing candidate rasters are research artifacts, not an authorization to submit. A TIFF that parses and fits the recorded grid is not automatically scientifically competitive or eligible for a weekly slot.
- LBCAL's saved card reports `HOLDOUT-DTI 0.061566` [0.051910, 0.072787], `gems57-pooled-hide-v2`, seeds 20+30, 22,663 withheld positives; its same-seed comparator PROVCREST is 0.076277. Those values are from the archived run card, not recomputed in this review. The separate 0.18789 threshold in gate v3 is from a different split and is not a paired comparison.
- The LBCAL uniqueness receipts report a like-for-like maximum of 0.6485 and Spearman maximum 0.0288 after classifying dense rasters separately. That differs from the user's literal any-raster rule: the documented positive-everywhere 17GEMSDOE witness gives every nonempty raster 100% forward overlap. Thus LBCAL does **not** pass the literal rule. The gate-v3 representation-class result cannot override the written lane protocol without an explicit protocol amendment.
- A universal forward-overlap witness is documented in the registry. Any policy that changes its treatment must be an explicit protocol change, not a per-candidate exception. The user's stated literal rule therefore remains a stop condition wherever it is the selected gate.
- Current competition data access/authentication and redistribution permissions are not available here. The official portal must be the source of organizer bytes for a final template-parity check.

## Candidate hypotheses for the next experiment (ranked; not run)

These are research proposals drawn from the existing `research/candidate-hypotheses-20261024-mdc88.md` and prior handoffs, not newly measured results. The gain/cost ordering is qualitative; the earlier file's numeric expectations are **MODEL** estimates, not HOLDOUT-DTI and not leaderboard scores. The next candidate experiment must be preregistered in one lane and measured against the same blocked folds before any slot is considered.

| Rank | Hypothesis and inputs | Signature / why it could find off-catalogue faults | Named non-fault mimic | Difference from implemented methods | Cost / viability |
|---:|---|---|---|---|---|
| 1 | **H-QTS: cover-thickness/topography discordance.** Competition bands `depth_to_base_surf` (B15), `det_elev` (B12), `det_elev_slope` (B19), `iso_grav_anom` (B13) and gravity horizontal gradient (B18). | At σ=1, 3, 6 px, score basement-gradient strength times directional disagreement with surface-elevation gradient. Targets buried basement steps whose surface remains subdued, rather than a mapped surface break. | Alluvial-fan toe/onlap or bedrock-pediment contact; test radial fan geometry vs. a long linear feature. | Previous stacks include basement gradients and dip-offset gravity; they do not test the explicit orientation-disagreement term. | Low if the competition stack is lawfully present and hash-verified. **Top next test**, but blocked now by absent inputs. |
| 2 | **H-RTR: scale-matched radiometric residual ridge.** USGS GeoDAWN K/Th/U/TC and derived Th/K, U/K, U/Th, plus conductivity (B17). | Remove broad lithologic field, then ridge-filter a K-depletion / Th-residual contrast; a hydrothermal alteration halo could persist where surface morphology is muted and the fault is uncatalogued. | K-poor playa crust or young basalt flow; use depression morphology and magnetic amplitude as controls. | Existing lanes use raw/ratio radiometry; explicit scale-matched residual ridge is distinct. | Low–medium; requires verified radiometric rasters, which are absent here. Free official source documented in manifest: USGS GeoDAWN DOI <https://doi.org/10.5066/P93LGLVQ>. Obtainability and terms still need confirmation before use. |
| 3 | **H-SSA: cross-depth strike agreement.** RTP (B2), magnetic horizontal gradient (B3), gravity horizontal gradient (B18), and detrended elevation (B12). | Structure-tensor azimuths at matched scales; circular concentration tests whether a narrow lineament persists from topography through magnetic and gravity fields, potentially identifying covered structures without relying on amplitude. | Bedding/stratigraphic strike or coherent intrusive contact. | Existing fabric tests use paired magnetic orientations or single-modality edges; this tests orientation agreement across modalities. | Medium; input-only if provided bands are restored. |
| 4 | **H-CAL: elevation-conditioned conductivity residual.** Conductivity surface (B17), detrended elevation (B12), and DEM-derived local elevation; optionally official DOE GDR #1391 temperatures as an independent check. | Local regression removes the elevation trend from conductivity to separate a possible upflow/conduit anomaly from basin brine. | Conductive clay-rich Lahontan lake beds / shoreline facies. | Earlier work uses conductivity directly or point-temperature indicators; the conditional residual is distinct. | Medium; temperature data are external and must be confirmed available/authorized. DOE GDR record <https://gdr.openei.org/submissions/1391> is the stated source, not a verified download in this session. |
| 5 | **H-TRI: catalogue relay-ramp graph.** Visible-only fault segments, segment endpoints, strike, and spacing. | Build per-fold relay-pair/stepover graph and score predicted linking corridors, where untraced connector faults may occur between mapped strands. | Artificial map-sheet joins or digitization gaps. | Existing methods use component distance, local strike, and generic detached-component features, not a graph of paired relay geometries. | High; catalogue-derived and therefore must be rebuilt per fold from visible faults only, with leakage canaries. No new external data is intrinsically required, but the input catalogue is missing here. |

**Selection:** H-QTS is the economical next scientific test, but it is **not executable in this checkout** until the competition grid, labels/catalogue, and feature stack are restored through an authorized path and hash-checked. No external-data hypothesis is called viable merely because a URL is listed. The 1 m 3DEP LiDAR alternative in prior notes is not promoted here: the required area-specific tiles and source terms were not verified or obtained.

## Why H33's reported 0.2778 cannot be treated as confirmed

The repo's forensic note supports a plausible mechanism: H33 is reported to be a thinned descendant of the H19-5/D2.8 family, with many near-catalogue dots removed and off-catalogue coverage retained. Given the metric's false-positive penalty, reducing low-value near-catalogue predictions while preserving useful coverage could improve DTI. This is a mechanism consistent with the pixel lineage and the owner-reported value, not proof of causation or an independently confirmed competition score. The repo has no organizer receipt for H33. The leaderboard score of any new candidate cannot be inferred from the catalogue hide-and-recover holdout alone.

## Next actions / blockers

1. Preserve the current `DO NOT SUBMIT` decisions; spend zero weekly slots.
2. Resolve lawful input availability. Prefer an authenticated competition-data download or a source with explicit redistribution/use authorization; validate all hashes against the pinned manifest. Do not assume the sibling GitHub mirrors are permitted—the manifest explicitly flags uncertainty.
3. Re-run `scripts/audit_session_start.py` and the complete tests after the pinned bridge inputs and required external files are available. Fix any genuine code defects uncovered; missing-input failures should be made explicit in the developer workflow, not hidden by marking tests passed.
4. Start a fresh, preregistered H-QTS lane only if inputs are restored. Reuse the shared evaluator/writer and cached stack. Test each feature alone for leakage; apply surface-correlation and final-dot overlap checks before emission; require paired positive holdout evidence to beat the incumbent.
5. Update the site, README, run card, and ledger from that single candidate gate result. A separate portfolio selector and organizer upload/receipt remain outside automatic local validation.

## Source links

These are official project/agency or competition endpoints already listed by the project. They are provided for review; this session did not authenticate to the competition portal or independently fetch restricted files.

- DrivenData GEMS competition: <https://www.drivendata.org/competitions/306/competition-doe-gems/>
- DrivenData problem description and submission format: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- DrivenData leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- NLR official rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- DOE GDR / INGENIOUS submission 1391: <https://gdr.openei.org/submissions/1391>
- USGS GeoDAWN survey data record: <https://doi.org/10.5066/P93LGLVQ>
- Organizer reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
- USGS 3DEP elevation products: <https://www.usgs.gov/3d-elevation-program>

## Review-only run card

This card describes the **latest LBCAL candidate already in the repository** and records a fresh saved-byte check. It is not a new experiment; holdout and uniqueness figures are archived evidence, not recomputed here. HOLDOUT-DTI is not an organizer leaderboard score.

```json
{
  "schema": "gems88.repo-review.v1",
  "reviewed_utc": "2026-10-24",
  "review_type": "archived-candidate audit; no new experiment",
  "hypothesis": "Receipt-calibrated physical-feature density q localizes uncatalogued faults better than catalogue-only proxies.",
  "mechanism": "Fit q from 25 physical features using user-reported sibling leaderboard receipts, then greedily emit points under a per-sibling 3-px-halo cap.",
  "named_non_fault_process": "K-poor playa crust or young basalt flow mimicking radiometric alteration; candidate also risks learned sibling-raster geometry.",
  "experiment_run": false,
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": "gems57-pooled-hide-v2",
    "seeds": [20, 30],
    "withheld_positive_pixels": 22663,
    "dti": 0.061566,
    "ci95": [0.051910, 0.072787],
    "same_seed_best_comparator": "PROVCREST",
    "comparator_dti": 0.076277,
    "source": "registry/lbcal_run_card.json; archived, not recomputed in this review"
  },
  "correlation_overlap_vs_registry": {
    "saved_receipt_sparse_max_abs_spearman": 0.0336,
    "saved_receipt_sparse_max_forward_overlap_3px": 0.656,
    "strict_literal_overlap_with_positive_everywhere_17GEMSDOE": 1.0,
    "preplacement_surface_correlation": "not reported in the LBCAL card",
    "policy_note": "Like-for-like receipt classes exclude space-filling rasters; that is not a pass under the literal all-raster rule."
  },
  "raster_sha256": "0a44af1ed8090cf1be88e42b832e0cc4b3bd2263a01b13b45f873e0eb528991a",
  "validator_output": {
    "independent_saved_byte_check": "PASS: one-band float32; EPSG:32611; shape 3730x3292; transform (243350,100,0,4508550,0,-100); nodata unset; all finite; min 0; max 1; 38278 positive pixels",
    "zip_check": "PASS: exactly one TIFF; member bytes match saved TIFF; independent reopen decodes identically",
    "fresh_official_sample_comparison": "NOT RUN: data/bridge/sample_submission.tif absent",
    "portal_layout_parity": "saved gate says false",
    "no_nan_inside_footprint": true,
    "values_in_0_1": true,
    "crs_shape_transform_match_recorded_grid": true
  },
  "submission_name": "GEMSDOE88-LBCAL-0AEB6EED",
  "submission_note": "LBCAL receipt-calibrated q, 38278 dots, <=66% in sibling halos; HOLDOUT 0.0616; model-proj only, UNSCORED",
  "verdict": "negative",
  "verdict_reason": "Below the same-seed holdout comparator; literal all-raster uniqueness fails; portal layout parity is not confirmed.",
  "weekly_slots_used": 0,
  "organizer_confirmed_score": null
}
```
