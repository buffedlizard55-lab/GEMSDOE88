> **Historical first-pass review:** this file predates the reconciliation of separate H88-MTAS pre-placement and execution records. Its five-hypothesis queue and “MTAS not fitted” statements are not current status. The corrected queue has four unexecuted proposals and excludes MTAS; see [current review](../docs/research/review-20261025-autonomous.md) and [v2 machine card](../evidence/repo_review_20261025.json).

# GEMSDOE88 repository review — 2026-10-25

## Executive decision

**Repository review: PASS with critical project blocker. New unique competition TIFF: NOT GENERATED. Submission: DO NOT SUBMIT.** The shared pre-placement check independently demonstrates that the SHA-pinned 17GEMSDOE registry witness covers every allowed pixel. Under the repository's binding literal overlap test, every nonempty prediction must therefore overlap that witness by 1.0, greater than the 0.70 limit. Generating a TIFF anyway would violate the stop rule and could not produce a compliant artifact.

The 0.2778 value attributed to H33 in the request is retained as a **USER-REPORTED claim**, not a HOLDOUT-DTI measurement and not ORGANIZER-CONFIRMED evidence. On-disk lineage supports a plausible explanation—H33 is a pruned subset of earlier point sets, reducing redundant emissions—but does not prove the hidden-label cause, validate that score, or establish a route to beat it. No projection is presented as a score.

## Review passes

### Pass 1 — Read and verify the project contract

- Read `README.md`, `PROMPT.md`, `USER_PROMPT_20261025.md`, `AGENTS.md`, the current run card, and submission/download guidance.
- Confirmed the workspace starts without the ignored `.venv/` and `data/` inputs. Installed the declared `requirements.txt` packages and restored the SHA-pinned validation-tier inputs using `scripts/restore_inputs.py --validation` (GitHub owner mirrors; not an authenticated DrivenData download).
- Ran the first-pass `scripts/review_repo_20261025.py`; that historical machine review returned `DUPLICATE_STOP` and contained a five-row queue. A later reconciliation corrected its queue because the separate MTAS execution archive proves that lane was run.

### Pass 2 — Audit the code paths and actual artifacts

- Re-ran `scripts/preflight_mtas88.py --gate-generation`: **exit 2, expected**, with a computed saturation certificate: 5,106,385 allowed pixels, all 5,106,385 directly covered, zero uncovered, universal blocker true. No feature construction, fitting, placement, or writing occurred.
- Ran `scripts/audit_downloads.py --check`: **43/43** published TIFF/ZIP packages pass local saved-byte checks; **0** pass the binding protocol uniqueness gate. This is a format/package audit, not portal acceptance.
- Ran `scripts/render_decision.py --check`, `python -O scripts/check_site.py`, and the ordinary site guard: **PASS**. The canonical Pages decision stays fail-closed. One early parallel invocation raced with preflight's atomic evidence refresh and transiently observed incomplete JSON; the sequential rerun passed. No code change was needed for that transient.
- Confirmed the existing TDKL research file is labeled `DO-NOT-SUBMIT` and its card marks format validity separately from submission approval. It is not represented as a new candidate.

### Pass 3 — Full tests and requirement-by-requirement recheck

- `.venv/bin/python -m pytest -q -ra`: **630 passed, 23 skipped, 0 failed** (61 upstream Rasterio/Affine pending-deprecation warnings). The skips are documented, data-conditional legacy artifact/rebuild checks; they are not submission clearance.
- Rechecked the user-facing priorities: README contains the recorded prompt and startup instructions; download-vs-submit distinction is explicit; automated `[0,1]`/grid/ZIP checks are present; H33's score is not misclassified; the requested new unique TIFF remains unmet because the binding gate is mathematically unsatisfiable for nonempty candidates.
- No evaluator, holdout splitter, metric, submission writer, or uniqueness implementation was forked or modified. No experiment or weekly slot was used.

## Scientific interpretation and ranked next work

The highest-scoring H33 example cannot be attributed confidently to a geological transform from its reported score alone. The repository's measured lineage indicates point-set thinning and near-catalogue pruning. Under a metric that rewards covered truth cells but also penalizes emitted false-positive points, removing redundant points can improve the precision/coverage balance if their lost truth coverage is small. This is a mechanistic explanation, not causal proof; withheld truth is unavailable for retrospective confirmation, and the supplied score lacks a submission receipt here.

The five hypotheses already recorded in `evidence/repo_review_20261025.json` are the MTAS cross-scale gravity/magnetic residual, terrain-matched radiometric residual, replicated drainage-offset statistic, depth-conditioned thermal/conductivity residual, and flight-line-confound-controlled edge persistence. They use local cached layers and are ranked by qualitative gain-to-cost, not numerical score projections. None is tested in this review. The required next experiment is **not** to choose one while the stop rule remains binding; first resolve the universal-witness contradiction through an explicitly authorized, shared protocol change, then re-run full registry surface and final-dot checks and the required buffered holdout/canaries.

## Official review links and source limits

The repository's pinned source ledger (`knowledge/official-sources-20261025.md` and `evidence/repo_review_20261025.json`) records prior retrieval/verification status. These pages were **not live-refetched in this review**, because the current outbound host policy does not permit those domains except GitHub. Links for manual/source-owner review:

- [DrivenData problem statement and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [competition data page (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) · [DrivenData reference solution on GitHub](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b)
- [USGS GeoDAWN official data page](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [DOE Geothermal Data Repository INGENIOUS record](https://gdr.openei.org/submissions/1391) · [EPSG:32611 CRS reference](https://epsg.io/32611)
- [GEMSDOE32 site named for the H33 result](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) · [Pinned H33 raster lineage/build record in its repository](https://github.com/buffedlizard55-lab/GEMSDOE32)

The H33 explanation remains conditional: thinning/collar removal can reduce redundant false-positive cost under the metric, but the claimed 0.2778 cannot be explained causally or exceeded with confidence absent an organizer receipt and access to hidden truth. No numeric projection is made.

## Findings and limitations

1. **Critical — no eligible new candidate under the current literal policy.** The dense witness creates a universal uniqueness veto. This is correctly fail-closed in the current gate; do not bypass it by removing the witness, changing the threshold, relabeling outputs, or invoking historical approval records.
2. **Important — startup prerequisites are local/ignored.** A fresh clone needs dependencies and restored validation inputs. The restore succeeds from hash-pinned owner GitHub mirrors, but those bytes are not authenticated current organizer downloads and no organizer data-use/redistribution authorization is inferred.
3. **Important — local validation is not organizer acceptance.** This environment has no authenticated DrivenData submission receipt. Current account quota, live challenge status, and an upload's historical range error cannot be verified here.
4. **Scientific boundary — no new score.** No MTAS HOLDOUT-DTI or canary exists. Archived holdout scores belong to their named historical lanes and must not be reused as evidence for a new raster. H33's 0.2778 and prompt-supplied leaderboard snapshots remain claims unless supported by the appropriate receipt/page capture.
5. **Historical content.** The README's collapsed archive contains session-era banners, including older `OK TO DOWNLOAD AND SUBMIT` language. Its archive warning says those entries do not override the current stop, and the generated landing-page/guide guard passes. Future edits should preserve clear historical labeling and avoid promoting any archived banner above the canonical decision.

## Reproducible checks

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/restore_inputs.py --validation
.venv/bin/python scripts/review_repo_20261025.py
.venv/bin/python scripts/preflight_mtas88.py --gate-generation  # expected exit 2
.venv/bin/python scripts/audit_downloads.py --check
.venv/bin/python scripts/render_decision.py --check
.venv/bin/python -O scripts/check_site.py
.venv/bin/python -m pytest -q -ra
```

## Negative run card

```json
{
  "hypothesis": "H88-MTAS: test a cross-scale gravity/RTP gradient residual for concealed basement discontinuities beneath low-relief cover.",
  "mechanism": "A short-scale gravity edge may persist where the RTP edge is diffuse or attenuated; test only after the pre-placement stop is resolved.",
  "named_non_fault_process": "An unfaulted intrusive or volcanic lithologic contact with density contrast but weak magnetic contrast; survey-line leveling seams are an additional confounder.",
  "holdout_dti": {
    "evidence_class": "HOLDOUT-DTI",
    "evaluator_version": "gems57-pooled-hide-v2",
    "withheld_positive_pixels": null,
    "score": null,
    "ci95": null,
    "status": "NOT RUN — pre-placement duplicate stop"
  },
  "correlation_overlap_vs_registry": {
    "surface_rank_correlation": null,
    "final_dot_rank_correlation": null,
    "final_dot_overlap_3px": null,
    "universal_lower_bound_overlap_3px": 1.0,
    "binding_overlap_limit": 0.70,
    "witness_sha256": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
  },
  "raster_sha256": null,
  "validator_output": {
    "new_raster": "NOT GENERATED",
    "no_nan_inside_footprint": null,
    "values_in_0_1": null,
    "crs_shape_transform_match": null,
    "archived_research_artifact_status": "separately audited; research only; DO NOT SUBMIT"
  },
  "submission_name": "GEMSDOE88-MTAS-PREFLIGHT-20261025-NO-FILE",
  "submission_note": "MTAS pre-placement duplicate: registry covers all allowed cells; no TIFF built; UNSCORED; DO NOT SUBMIT",
  "verdict": "negative"
}
```
