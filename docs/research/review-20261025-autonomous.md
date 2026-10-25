# Repository review — 2026-10-25 (corrected queue and evidence reconciliation)

## Executive decision

**New unique submission TIFF: not generated. Existing research TIFF: safe to download for research only. Submission: NO — DO NOT SUBMIT. Weekly slots used: 0.**

The pre-placement duplicate gate is mathematically blocking under the supplied literal protocol. The hash-pinned `17GEMSDOE` witness covers all **5,106,385 allowed cells**. Any nonempty candidate in that domain therefore has forward overlap **1.0 > 0.70**. This is a sufficient counterexample, not an inventory-wide uniqueness clearance. We did not bypass the gate, fit a candidate, construct a holdout prediction, place dots, or make a new TIFF. The exact machine record is [`docs/data/repo_review_20261025.json`](../data/repo_review_20261025.json), mirrored at [`evidence/repo_review_20261025.json`](../../evidence/repo_review_20261025.json).

The existing canonical research download is [`gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif`](../downloads/gems88-tdkl88-poe-25000dots-20261024-zeros-DO-NOT-SUBMIT.tif). **Download for research: YES. Submit: NO.** Its local format/ZIP audit is separate from the duplicate gate, a current score, organizer acceptance, or slot authorization. It is not a new artifact.

## Three review passes

### Pass 1 — reproduce the fail-closed boundary

- Restored and SHA-verified the 28 validation-tier owner-mirror files. Full training, external, and sibling inputs were not restored; these owner mirrors are not authenticated against current organizer downloads.
- Installed the pinned project requirements in the ignored `.venv`.
- Ran `scripts/preflight_mtas88.py --gate-generation`. It returned the expected exit **2 / `DUPLICATE_STOP`** from the full-support witness. No fit or raster generation followed.
- Re-ran the read-only H33 lineage inspection against hash-pinned local rasters. It matched the saved report after dropping its run timestamp.

### Pass 2 — reconcile the record and correct the candidate queue

The repository contains conflicting same-date MTAS records. `registry/mtas88_run_card.json` and `evidence/mtas88_preflight_20261025.json` record a pre-placement duplicate stop and no experiment. Separately, `registry/mtas88_experiment_run_card.json`, `evidence/mtas88_experiment_20261025.json`, `research/session-20261025-mtas-execution.md`, and the matching research TIFF/ZIP document an executed experiment. We preserve both histories; the archived execution artifacts mean **MTAS is not untried**. The active queue and tests previously called it `UNTESTED` and ranked it first; those are corrected below.

The existing MTAS experiment is negative and not organizer-confirmed. Its archived result is **HOLDOUT-DTI 0.049577** (evaluator `gems57-pooled-hide-v2`, **22,893** withheld positives, 95% CI **[0.044659, 0.054417]**). This is evidence about the historical MTAS lane only; it is not a score for the newly selected FARC proposal.

### Pass 3 — release checks

The complete suite, both review-report copies, canonical render, site checks (including optimized Python), format audit, compile checks, and whitespace checks were rerun after the corrections. Exact outcomes are recorded in the review summary at the end of this file and in the machine review card. No new experiment, TIFF, score, organizer receipt, or slot approval was produced.

## H33 `0.2778`: what the evidence supports

`0.2778` remains a **USER-REPORTED CLAIM**, not a `HOLDOUT-DTI` result from this checkout and not `ORGANIZER-CONFIRMED`: there is no submission-page receipt here. The archived GEMSDOE32 build record calls a separate `0.2747` value a model projection, not an organizer score. Neither value is promoted by this review.

The read-only raster audit measures lineage geometry, not hidden-label performance:

- Positive support is nested through **121,131 → 44,090 → 40,199 → 37,654** pixels (`H19-5 → D2.8 → SOLO-D2.8 → H33`).
- D2.8 to H33 removes **6,436** predictions; every removed pixel is within two catalogue pixels. H33 itself has no positive pixel within two catalogue pixels, and its median catalogue distance is **19.6469 px**.
- The GEMSDOE32 owner record's estimate is not a competition receipt. The value reported in the request cannot be independently verified from the material available here.

The official distance-weighted Tversky structure offers a plausible, limited explanation for why pruning could help: `DTI = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w)`, where each truth cell receives its maximum triangular-kernel prediction credit within 300 m. Removing predictions that are redundant or have little marginal truth credit can reduce false-positive burden while retaining much of the covered truth. But the deleted dots are only known to be near the *visible catalogue*; this does not show they were false positives for hidden faults, nor does geometric thinning prove causality. Visible catalogue faults must be masked **exactly**, not by an invented buffer. A real improvement over the reported H33 value is possible in principle, but it has not been demonstrated or guaranteed here.

The highest stored full-fold local reference in the inspected cards is historical **HOLDOUT-DTI 0.205991** (95% CI **[0.188105, 0.223344]**, evaluator `gems57-pooled-hide-v2`, **22,893** withheld positives; `registry/bpwd88_run_card.json`). It is not a live leaderboard result. It cannot be compared to H33's user-reported number as if the scopes were paired. No FARC comparison was run.

## Four ranked, genuinely unexecuted repo-local hypotheses

These are the current queue in `src/gems88/review.py` and the machine review. “Unexecuted” means no matching implementation/run card/experiment was found in this repository after the review; it does **not** establish novelty across every sibling checkout. Rankings of value and cost are qualitative planning judgments, not predicted scores. All layer names are from the repository's feature definitions; local owner-mirror provenance and current organizer availability are not authenticated by this review.

| Rank | Hypothesis and named layers | Physical signature and missing-fault rationale | Non-fault mimics | Difference from existing repo methods | Expected value / cost; external data |
|---:|---|---|---|---|---|
| **1** | **H88-FARC** — `chi_step_max`, `ksn_jump_norm`, `topo10_hs_lineament`, `lidar_scarp_coh`, `det_elev_slope` | Replicated, signed channel-profile breaks across separate catchments, normalized within catchment/channel-order strata and compared with a slope-matched pseudo-crest null. A blind rupture could perturb channels and low-relief surfaces without producing a catalogue-grade scarp. | Lithologic knickzones, inherited drainage capture, regional base-level change, or climate-driven incision. | QTSK/TDKL characterize local knickwave magnitude or scarp polarity. FARC's proposed discriminator is cross-catchment replication against a matched null; no exact FARC implementation/run card was found. | **Medium potential / medium cost** (qualitative, unmeasured). No new external data proposed; cached DEM-derived channels only. Verify restored mirror identity before fitting. |
| **2** | **H88-TCONS** — `probe2m_dab_local`, `well_temp_anom`, `cond_edge_300m`, `depth_to_base_log` | Depth-conditioned temperature-to-conductivity residual, then spatial coherence along a blind structure. Focused fluid flow could generate a geothermal signal without an exposed scarp. | Lake-brine conductivity, groundwater circulation, or permeable but unfractured lithology. | DHTC combines deep heat/MT and basement structure; TCONS proposes head-/depth-matched negative controls to isolate a conditional residual. No exact TCONS experiment was found. | **Medium potential, high uncertainty / high cost.** No new data proposed beyond the cached stack. Verify the official [DOE GDR INGENIOUS page](https://gdr.openei.org/submissions/1391), acquisition, provenance, and derivative rights before use or sharing. |
| **3** | **H88-PRAN** — `rad_k_over_th`, `det_elev_slope`, `topo10_curv_prof`, `depth_to_base_log` | Terrain-bin-matched K:Th radiometric residual with along-strike persistence, not a global radiometric high. Alteration or soil redistribution could persist above a covered structure. | K-rich transported alluvium, parent-rock boundaries, and soil-moisture effects. | MVRD combines radiometry with scarp fields; PRAN proposes a terrain-conditioned null and along-strike persistence. No exact PRAN experiment was found. | **Low-to-medium potential / low-to-medium cost.** No new data proposed; uses cached GeoDAWN-derived radiometry and terrain. Verify mirror provenance and redistribution rights first. |
| **4** | **H88-FLAC** — `rtp_grad_200m`, `grav_grad_200m`, `cond_edge_300m`, `geod_shearrate`, `geod_dilaterate` | Cross-sensor edge persistence with a preregistered survey-line-direction artifact veto. Independent support could identify a concealed structure without a strong surface scarp. | Tie-line leveling, gridding seams, or a broad lithologic contact aligned with acquisition direction. | MGC/XGCE compare cross-field edge geometry; FLAC's proposed distinction is an explicit acquisition-direction null and local continuity test. No exact FLAC experiment was found. | **Low potential / low cost.** No new raster proposed. GeoDAWN acquisition metadata is an official manual-review link, not freshly fetched evidence. |

**Top candidate status:** FARC is ranked first because it uses existing geomorphic channels, has moderate implementation cost, and tests repeatability rather than a single edge; its geological specificity remains uncertain and the matched-null test is essential. It was **not fit, canary-tested, or scored**. There is no `HOLDOUT-DTI`, evaluator output, withheld-positive count, or CI for FARC. The blocked holdout fields in the machine card are null by design.

## Download, submission, and automated validation

- **Existing TDKL TIFF/ZIP:** local format validation passed; **download for research: yes; submit: no**. The README/site label the artifact `DO-NOT-SUBMIT`.
- **New unique FARC TIFF:** **not generated**, so there is no new filename, hash, validator output, or download link to submit. The blocked name in the machine record is explicitly `NO_FILE_NOT_FOR_PORTAL`.
- **Automated tests:** saved-byte format checks do not clear the independent dense-witness uniqueness rule. No claim of organizer acceptance, live quota, or weekly slot approval is made.

## Official references and freshness limits

The machine review retains links to the official [DrivenData problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [pinned reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR INGENIOUS](https://gdr.openei.org/submissions/1391), and [EPSG:32611](https://epsg.io/32611). The non-GitHub official sources were **not re-fetched in this replay** because their hosts are outside the session's outbound allowlist. The source statuses in the machine report are inherited from the prior dated audit, not live source verification. No DrivenData login, current quota, submission receipt, or organizer data download was available.

## Verification record

- Final `.venv/bin/python -m pytest -q`: **682 passed, 23 skipped, 61 warnings**. The remaining warnings are Rasterio's upstream `PendingDeprecationWarning`; no test failed.
- `.venv/bin/python scripts/audit_downloads.py --check`: **44/44** research TIFF/ZIP pairs passed local format checks; **0** were protocol-eligible.
- `scripts/review_repo_20261025.py --require-submit` and `scripts/preflight_mtas88.py --gate-generation`: both returned the expected **exit 2 / `DUPLICATE_STOP`**. The FARC holdout is null, no candidate was fit or placed, and no slot was approved.
- `scripts/render_decision.py --check`, `scripts/check_site.py`, and `python -O scripts/check_site.py`: PASS. The site now displays the four unexecuted candidates, FARC's blocked status, and the MTAS record conflict. `compileall` and `git diff --check` passed.
- The read-only H33 lineage recheck matched its saved report after dropping the timestamp. It measures raster geometry only.
- The pre-existing browser receipt is valid only for its earlier page hashes. Four HTML pages were changed; **no new interactive-browser run or screenshot was performed**, so the prior receipt is not represented as current visual QA. The current verification is the reproducible static site guard (normal and optimized Python).
- No new experiment, TIFF, holdout result, organizer receipt, or slot approval was produced during the review work.

## Next steps

1. Do not spend a weekly slot or upload any archived TIFF.
2. Resolve the dense-support witness versus candidate dot-set protocol contradiction through a documented **shared** policy/template decision; do not introduce a private exemption.
3. Authenticate input identity, availability, and licensing/redistribution rights before proposing new data.
4. If and only if the pre-placement policy gate is resolved, preregister FARC; test each feature alone for leakage (`AUC > 0.90` is a stop until disproven); recompute catalogue-derived features from visible faults only and mask visible faults exactly.
5. Use the shared `evaluate_holdout.py` and `submission_writer.py`; hold out whole fault segments with a buffer, derive catalogue features from visible faults only, and mask visible faults exactly. Test every feature alone for leakage (`symmetric AUC > 0.90` is a stop until disproven). Use pooled DTI with `alpha=0.2`, `beta=0.8`, and a 300 m triangular kernel. Close each run with the requested JSON run card; cap work at three experiments or two hours.
6. Label every model result `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI. Compare paired folds against the recorded incumbent; the top idea must demonstrate improvement over the current holdout best before any separate weekly-slot decision.
7. Apply the parallel-run protocol: before placement, stop if a registry surface has rank correlation `>0.90`; after placement, stop if `>70%` of candidate dots fall within 3 px of any registry raster. Run final-dot uniqueness as well. Do not bypass a failed gate.
8. Only after scientific, uniqueness, format, source-rights, and separate selector gates pass should a new TIFF/slot decision be considered. Only a submission-page receipt can support `ORGANIZER-CONFIRMED`.
