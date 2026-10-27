# Repository review — 2026-10-27, Arena session `850f9a2c`

## Decision and scope

**No new candidate was generated, no experiment/holdout was run, and no competition slot was used. SUBMIT: NO — DO NOT SUBMIT.** This is the required negative result, not a prediction that any candidate would score well. The user's reported H33 `0.2778` and leaderboard `0.3195` are not copied from submission receipts in this checkout and therefore remain **USER-REPORTED**, not ORGANIZER-CONFIRMED. Nothing in this review establishes that a new method can beat either figure.

This review did not change model, writer, evaluator, guard, website decision, or selection policy. It records a reproducible status review and the reason further scientific work cannot legally start under the unchanged protocol.

## Reproduction (local)

- Environment installed from the repository's pinned `requirements.txt` / `requirements-constraints.txt` in `.venv`; Rasterio is pinned to 1.4.4.
- `python scripts/restore_inputs.py --validation` restored SHA-checked validation inputs and registry witnesses from pinned GitHub commits. This did **not** retrieve or authenticate organizer-login data.
- `.venv/bin/python scripts/generation_guard.py` emitted `DUPLICATE_STOP`; the guard's own exit status is `2`. Its pre-placement proof identifies `data/registry/dense_17gemdoe.tif`, SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`, with all `5,106,385 / 5,106,385` allowed cells covered. Under the repo's literal support rule, every nonempty candidate has 3-pixel overlap `1.0`, greater than `0.70`. No candidate surface or dots were constructed.
- `.venv/bin/python scripts/audit_session_start.py` did not complete: its historical byte-rebuild audit needs `data/training_features.tif`, absent after the validation-tier restore. This is recorded as an audit limitation, not a pass. Full restore would bring large owner-mirror features and is not needed to reproduce the pre-placement stop.
- `.venv/bin/python scripts/check_site.py` and `.venv/bin/python scripts/render_decision.py --check` passed before validation inputs were restored; those scripts check repository/site decision consistency, not remote Pages deployment or contest acceptance.

## Nine named sites and highest-claim interpretation

The highest listed historical value is GEMSDOE32 H33-2-B2 at **USER-REPORTED 0.2778**. The provided list also reports nearby values for GEMSDOE28 (`0.2710`), GEMSDOE31 (`0.2708`), GEMSDOE36 (`0.2750`), GEMSDOE25 (`0.2600`), GEMSDOE30 (`0.2600`), GEMSDOE24 (`0.2477`), GEMSDOE27 (`0.2449`) and GEMSDOE33 (`0.2632`). These are claims in the supplied prompt, not receipts. The repository's prior byte-level H33 forensic review says the H33 raster is geometrically a subset of D2.8: the D2.8-only 6,436 cells lie within two pixels of the mapped catalogue. That geometry makes removal of likely redundant near-catalogue predictions a plausible mechanism under a tolerance-based asymmetric DTI, but does not prove why hidden-label scoring produced 0.2778 or establish the score's authenticity.

The current available cross-org audit (`evidence/focus_and_crossorg_20261027_audit.json`, checked 2026-10-27 17:49:20Z) says none of the nine focus sites authorizes a submission and none of the 12 cross-org sites authorizes one. Its sampled new candidate bytes all have overlap 1.0 against the dense witness. This is a dated sample, not a complete census or an organizer score feed. The root executive table and linked audit should be used for per-site historical detail; do not elevate a user-claimed score to a recommendation to submit.

## Candidate hypotheses and decision

The local source-bound queue in `registry/hypothesis_queue.json` already ranks three source-reviewed but untested ideas. Their scientific novelty is only relative to this checkout, and their scores are unknown. Expected DTI improvement cannot responsibly be ranked numerically from unreceipted leaderboard values. Qualitatively:

| Priority | Hypothesis / cached layers | Mechanism and off-catalogue rationale | Important non-fault mimic | Cost / status |
| --- | --- | --- | --- | --- |
| 1 | H88-SPR: detrended elevation/slope, cached fine-topography and scarp/drainage derivatives | Test repeatable signed-step profile restoration across independent swaths, without catalogue-seeded surface construction; may reveal unmapped scarps. | Fluvial terrace risers and pluvial shoreline benches. | Medium; no external layer proposed; queued, not authorized or tested. |
| 2 | H88-AWA: cached radiometric K/Th/U codes, RTP magnetic field, basement depth and slope | Test terrain-matched cross-strike alteration-width asymmetry rather than absolute enrichment. | Lithologic boundaries, weathering and transported alluvium; quantized codes may not represent concentration ratios. | Medium; careful quantization controls required; queued, not authorized or tested. |
| 3 | H88-CBC: detrended elevation, isostatic gravity, basement depth, conductivity and drainage | Test narrow cross-boundary connectivity plus gravity change against a smooth basin-fill null for structures without surface traces. | Saline alluvial paleochannels. | Medium-high; coarse data limit resolution; queued, not authorized or tested. |

The shared guard stops all three before feature construction, so none can be validated on holdout in compliance with the protocol. Do not circumvent the guard, do not emit an empty or manipulated TIFF, and do not use a local holdout score as a leaderboard estimate. A representation-aware registry rule would require an explicit shared-protocol/selector decision and independent validation, not a private exception.

## Three-pass review

1. **Implementation/repo pass:** read the session contract and current README/prompt; traced model/experiment entrypoint restrictions, prior executive evidence, current queue and latest dated cross-org/focus audit. Existing documentation already contains the human prompt and submission guide; no redundant prompt copy was added.
2. **Bug/assumption pass:** installed the pinned runtime after finding the base interpreter lacked NumPy; restored only validation-tier inputs; reproduced the guard stop. Confirmed the start audit's failure is due to missing full training feature input, not a successful verification. Kept claimed scores separate from receipt-confirmed scores and separated holdout from leaderboard evidence.
3. **Requirement pass:** no candidate TIFF, new holdout, feature canary, surface correlation or final-dot measurement is claimed; no submission slot is selected or used. The requested high-scoring downloadable TIFF cannot be responsibly produced under the binding duplicate gate. The current README, rendered executive guide and fail-closed gates already state this; changes are restricted to this review artifact.

## Limitations and actionable next work

1. A separate selector/protocol authority must decide whether/how a continuous dense probability raster is represented for dot-overlap checks. Until then the literal `>70%` gate makes every nonempty candidate fail before placement.
2. Run the full pinned restore and byte-exact historical audit only after that decision makes scientific experimentation meaningful; training data mirrors are not authenticated organizer downloads and the DrivenData data page needs user-authenticated access outside this sandbox.
3. If authorized, freeze one queue hypothesis and protocol, execute feature-by-feature leakage canaries, then whole-component buffered hide-and-recover against the same-fold incumbent using the shared evaluator; enforce the 3-experiment / 2-hour limit.
4. Refresh the nine focus repositories' current HEADs and raster bytes before asserting present-day winners/uniqueness. The date-stamped audit is not a continuously updating feed or full live census.
5. Verify the current organizer leaderboard, weekly slot cap and any uploaded result only through authorized competition page access and preserve the submission receipt. No such receipt or quota was accessible here.

### Sources (repository-pinned or official references)

- Shared duplicate gate and evidence: `scripts/generation_guard.py`; `vendor/gems57/uniqueness.py`; `evidence/focus_and_crossorg_20261027_audit.json`; `registry/session_92002f70_run_card.json`.
- Hypothesis inventory: `registry/hypothesis_queue.json` (proposal status, not empirical validation).
- H33 forensics: `research/session-92002f70-review.md` and `evidence/h33_lineage_recheck.json`.
- Competition / official project reference: [DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/), [DOE/USGS GEMS technical report](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [DOE Geothermal Data Repository entry 1391](https://gdr.openei.org/submissions/1391), [USGS GeoDAWN data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution). These are links for traceability; no claim is made that those external pages were retrieved during this session.
